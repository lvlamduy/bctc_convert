#!/usr/bin/env python3
"""Build/replay the fixed 140-filing customer-loan geography sweep.

The formal path deliberately keeps retrieval, table discovery, numeric
reconciliation and schema projection as separate authorities.  Region-first
retrieval is replayed against the authenticated SQLite source and is accepted
only after an exhaustive-coverage proof.  A release-gate whole-document pass
then has to produce the same per-document structural disposition and region
fingerprint before the sparse result may be mapped.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import secrets
import stat
import sys
import time
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1  # noqa: E402
from bctc_ai.evaluation import family_first_region_retrieval_v1 as retrieval_v1  # noqa: E402
from bctc_ai.evaluation import loan_geography_numeric_reconciliation_v1 as numeric_v1  # noqa: E402
from bctc_ai.evaluation import loan_geography_scoped_table_adapter_v1 as graph_v1  # noqa: E402
from bctc_ai.mapping import loan_geography_bounded_schema_v1 as schema_v1  # noqa: E402
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import customer_loan_total_control_v1 as total_control_v1  # noqa: E402
from scripts.experiments import loan_geography_visible_dash_evidence_v1 as dash_v1  # noqa: E402

FORMAT_VERSION = "FAMILY_FIRST_LOAN_GEOGRAPHY_140_FILING_SCHEMA_SWEEP_V1"
SPARSE_GRAPH_BINDING_FORMAT_VERSION = "FAMILY_FIRST_LOAN_GEOGRAPHY_SPARSE_DOCUMENT_GRAPH_BINDING_V1"
RECEIPT_BINDING_FORMAT_VERSION = "FAMILY_FIRST_LOAN_GEOGRAPHY_REGION_RETRIEVAL_RECEIPT_BINDING_V1"
CLAIM_BOUNDARY = (
    "FIXED_140_FILING_AUTHENTICATED_SQLITE_REGION_FIRST_EXHAUSTIVE_COVERAGE_"
    "REPLAY_WHOLE_DOCUMENT_STRUCTURAL_EQUIVALENCE_SHARED_SCOPED_TABLE_GRAPH_"
    "EXACT_CUSTOMER_LOAN_DOMESTIC_FOREIGN_TOTALS_TYPED_PIXEL_DASH_PPOCRV6_"
    "VIETOCR_LOCAL_OR_AUTHENTICATED_UPSTREAM_EXACT_PRINTED_TOTAL_EQUATIONS_"
    "AND_APPEND_STABLE_TM_SCHEMA_ONLY_"
    "NO_BROAD_POPULATION_NARROWING_BACKSOLVE_GEMMA_NUMERIC_CANONICALIZATION_"
    "EXPORT_OR_BANK_PAGE_PERIOD_ROUTING_AUTHORITY"
)
OUTPUT_PATH = Path(
    "output/calibration/family-first-loan-geography-140-filing-schema-sweep-v1/result.json"
)

_AUTHORITY = {
    "absence_trial_hydrates_numeric_pixel_or_total_control_evidence": False,
    "accounting_can_backsolve_invent_or_narrow_a_population": False,
    "accounting_is_corroboration_or_veto_only": True,
    "bank_filename_note_page_period_scope_year_or_ordinal_used_as_mapping_rule": False,
    "blank_or_detector_omission_imputed_as_zero": False,
    "broad_or_mixed_geography_population_mapping_authority": False,
    "canonicalization_or_export_authority": False,
    "customer_loan_total_control_snapshot_self_hash_is_source_authority": False,
    "customer_loan_total_control_requires_capability_snapshot_and_public_replay": True,
    "e0164_persisted_result_is_total_control_authority": False,
    "gemma_numeric_authority": False,
    "gemma_request_count": 0,
    "known_nested_domestic_descendants_emitted": False,
    "parent_716_or_759_emitted_as_mapping": False,
    "persisted_retrieval_receipt_is_bounded_roots_and_coverage_only": True,
    "public_exact_live_replay_required": True,
    "raw_ppocrv6_and_vietocr_surfaces_preserved": True,
    "region_retrieval_is_mapping_or_absence_authority": False,
    "region_retrieval_requires_authenticated_exact_replay": True,
    "schema_mapping_authority_bounded_to_family_11": True,
    "shared_scoped_table_graph_required": True,
    "sparse_and_whole_document_structure_must_be_equivalent": True,
    "visible_dash_zero_requires_exact_pixel_replay": True,
}

_TARGET_DOCUMENT_COUNT = 140
_TARGET_EXACT_COUNT = 38
_TARGET_BROAD_COUNT = 78
_TARGET_NOT_OBSERVED_COUNT = 24
_TARGET_UNRESOLVED_COUNT = 0
_TARGET_MAPPING_COUNT = 76
_TARGET_PERIOD_LANE_COUNT = 65
_TARGET_MAPPED_MONEY_CELL_COUNT = 130
_TARGET_OBSERVED_NUMERIC_MAPPED_CELL_COUNT = 88
_TARGET_VISIBLE_DASH_ZERO_COUNT = 42
_TARGET_EQUATION_COUNT = 65
_TARGET_TOTAL_CONTROL_SOURCE_MODE_COUNTS = {
    "LOCAL_LABELED_TOTAL": 36,
    "LOCAL_UNLABELED_TOTAL_ROW": 18,
    "UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL": 11,
}
_TARGET_UPSTREAM_TOTAL_CONTROL_COUNT = 11
_TARGET_ROW_LAYOUT_COUNT = 20
_TARGET_COLUMN_LAYOUT_COUNT = 18
_TARGET_REPEATED_FULL_SEGMENT_COUNT = 18
_TARGET_CONTINUATION_MODE_COUNTS = {
    "ADJACENT_REPEATED_FULL_SEGMENTS_PERIOD_COMPLEMENT": 18,
    "SINGLE_PAGE_MULTI_PERIOD_COMPLETE_SEGMENTS": 9,
    "SINGLE_PAGE_COMPLETE_SEGMENTS": 11,
}
_TARGET_PARTIAL_CONTINUATION_COUNT = 0
_TARGET_GEMMA_REQUEST_COUNT = 0
_TARGET_SPARSE_HYDRATED_PAGE_COUNT = 1_995
_TARGET_SPARSE_HYDRATED_LINE_COUNT = 153_239
_TARGET_INDEXED_RETRIEVAL_DOCUMENT_COUNT = 116
_TARGET_FULL_FALLBACK_DOCUMENT_COUNT = 24

_DEFAULT_DIRECT_FULL_JOBS = max(1, min(8, os.cpu_count() or 1))
_DEFAULT_DIRECT_FULL_BATCH_SIZE = _DEFAULT_DIRECT_FULL_JOBS
_DEFAULT_SPARSE_JOBS = _DEFAULT_DIRECT_FULL_JOBS
_FAMILY11_GRAPH_WORKER_RECEIPT: Any | None = None
_EXPECTED_REGION_QUERY_SPEC_ID = (
    "fffrrv2:query:aa2700a3a54bf9a6ff79bbd4c51d8b3f1e55c7e2f16688a4f75b190673641cc9"
)
_EXPECTED_REGION_RECEIPT_ID = (
    "fffrrv2:receipt:4f27e3af157654bb4b5d8442a8b6c008a2d18b8da3646cfb67fcf4bae677198f"
)
_EXPECTED_REGION_IMPLEMENTATION_REFS = {
    "src/bctc_ai/evaluation/family_first_region_retrieval_v1.py": {
        "path": "src/bctc_ai/evaluation/family_first_region_retrieval_v1.py",
        "sha256": "01a4d4a676a25e03eb4fe1733f159ceafbdacad9be6d6ed1196572528e1fae20",
        "size_bytes": 105_116,
    },
    "src/bctc_ai/evaluation/loan_geography_scoped_table_adapter_v1.py": {
        "path": "src/bctc_ai/evaluation/loan_geography_scoped_table_adapter_v1.py",
        "sha256": "892cd2584429e232767ed840a641460c1c08baa97715e0728129fe2101f9921e",
        "size_bytes": 123_674,
    },
}

_BANK_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
_TARGET_BANK_DOCUMENT_COUNTS = {
    "ACB": 18,
    "MBB": 18,
    "VPB": 18,
    "HDB": 16,
    "VCB": 18,
    "CTG": 18,
    "BID": 16,
    "VIB": 18,
}
_TARGET_BANK_EXACT_COUNTS = {
    "ACB": 3,
    "MBB": 17,
    "VPB": 0,
    "HDB": 0,
    "VCB": 0,
    "CTG": 0,
    "BID": 0,
    "VIB": 18,
}
_TARGET_BANK_BROAD_COUNTS = {
    "ACB": 12,
    "MBB": 0,
    "VPB": 18,
    "HDB": 16,
    "VCB": 0,
    "CTG": 16,
    "BID": 16,
    "VIB": 0,
}
_TARGET_BANK_NOT_OBSERVED_COUNTS = {
    "ACB": 3,
    "MBB": 1,
    "VPB": 0,
    "HDB": 0,
    "VCB": 18,
    "CTG": 2,
    "BID": 0,
    "VIB": 0,
}
_TARGET_BANK_MAPPING_COUNTS = {bank: count * 2 for bank, count in _TARGET_BANK_EXACT_COUNTS.items()}
_TARGET_BANK_DASH_ZERO_COUNTS = {
    "ACB": 6,
    "MBB": 0,
    "VPB": 0,
    "HDB": 0,
    "VCB": 0,
    "CTG": 0,
    "BID": 0,
    "VIB": 36,
}
_MAPPED_ROLES = ("DOMESTIC_TOTAL", "FOREIGN_TOTAL")
_ACCEPTED_EQUATION_STATUSES = {
    "EXACT_OBSERVED_EQUATION",
    "EXACT_EQUATION_UNIQUELY_SELECTED_OBSERVED_CANDIDATES",
}
_TERMINAL_STATUSES = {"UNRESOLVED", "VERIFIED_BOUNDED_ABSENCE", "VERIFIED_BY_CODEX"}
_DISPOSITIONS = {
    "BROAD_POPULATION_BOUNDED_ABSENCE",
    "EXACT_CUSTOMER_LOAN_GEOGRAPHY",
    "NOT_OBSERVED",
    "UNRESOLVED",
}

_SCHEMA_SOURCE_PATHS = (
    Path("config/schemas/sources.yaml"),
    Path("config/mapping/lctt-v2.yaml"),
    Path("template/Bank_CDKT_ReportNormId.xlsx"),
    Path("template/Bank_KQKD_ReportNormId.xlsx"),
    Path("template/Bank_LCTT_ReportNormId.xlsx"),
    Path("template/Bank_TM_ReportNormId.xlsx"),
    Path("template/Bank_CDKT_ReportNormId.v2.xlsx"),
    Path("template/Bank_KQKD_ReportNormId.v2.xlsx"),
    Path("template/Bank_LCTT_ReportNormId.v2.xlsx"),
    Path("template/Bank_TM_ReportNormId.v2.xlsx"),
    Path("data/registered/schema_append_1944.json"),
    Path("data/registered/schema_business_update_5712_5713_5714_5718_6074.json"),
    Path("data/registered/schema_business_update_5712_5713_5714_5718_6076.json"),
    Path("config/schemas/hierarchy_reference.yaml"),
    Path("vst_level/vst_bank_balance_sheet.xlsx"),
    Path("vst_level/vst_bank_income_sheet.xlsx"),
    Path("vst_level/vst_bank_cashflow_sheet.xlsx"),
    Path("vst_level/vst_bank_detailed_notes_sheet.xlsx"),
    Path("config/schemas/tm-context-v1.yaml"),
)
_IMPLEMENTATION_PATHS = (
    Path("src/bctc_ai/evaluation/family_first_document_evidence_store_v1.py"),
    Path("src/bctc_ai/evaluation/family_first_ocr_query_cache_v1.py"),
    Path("src/bctc_ai/evaluation/family_first_region_retrieval_v1.py"),
    Path("src/bctc_ai/evaluation/accounting_table_axes_v1.py"),
    Path("src/bctc_ai/evaluation/accounting_variant_graph_engine_v1.py"),
    Path("src/bctc_ai/evaluation/accounting_scoped_table_graph_v1.py"),
    Path("src/bctc_ai/evaluation/loan_geography_scoped_table_adapter_v1.py"),
    Path("src/bctc_ai/evaluation/family_first_visible_dash_glyph_evidence_v1.py"),
    Path("src/bctc_ai/evaluation/loan_geography_numeric_reconciliation_v1.py"),
    Path("src/bctc_ai/mapping/loan_geography_bounded_schema_v1.py"),
    Path("scripts/experiments/customer_loan_total_control_v1.py"),
    Path("scripts/experiments/loan_type_variant_graph_v1.py"),
    Path("scripts/experiments/loan_type_numeric_row_reconciliation_v1.py"),
    Path("scripts/experiments/loan_geography_visible_dash_evidence_v1.py"),
    Path("scripts/experiments/build_family_first_loan_geography_140_filing_schema_sweep_v1.py"),
    Path("src/bctc_ai/source_structure/contracts_v1.py"),
)


class FamilyFirstLoanGeography140FilingSchemaSweepV1Error(ValueError):
    """The source, retrieval, structure, pixel, numeric, schema, or replay drifted."""


class LoanGeographyTrialUnresolvedV1Error(ValueError):
    """One filing could not reach a bounded terminal Family 11 disposition."""


def _error(message: str) -> FamilyFirstLoanGeography140FilingSchemaSweepV1Error:
    return FamilyFirstLoanGeography140FilingSchemaSweepV1Error(message)


def _unresolved(message: str) -> LoanGeographyTrialUnresolvedV1Error:
    return LoanGeographyTrialUnresolvedV1Error(message)


def _strict_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise _error(f"{label} must be one exact integer >= {minimum}")
    return value


def _stable_ref(root: Path, relative: Path) -> dict[str, Any]:
    path = root / relative
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error(f"input is not one regular nofollow file: {relative}")
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise _error(f"cannot read stable input: {relative}") from exc

    def identity(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return (item.st_dev, item.st_ino, item.st_mode, item.st_size, item.st_mtime_ns)

    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error(f"input changed during read: {relative}")
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _refs(root: Path, paths: Sequence[Path]) -> dict[str, dict[str, Any]]:
    return {path.as_posix(): _stable_ref(root, path) for path in paths}


def _schema_source_refs(root: Path) -> dict[str, dict[str, Any]]:
    return _refs(root, _SCHEMA_SOURCE_PATHS)


def _implementation_refs(root: Path) -> dict[str, dict[str, Any]]:
    return _refs(root, _IMPLEMENTATION_PATHS)


def _assert_build_inputs_unchanged(
    root: Path,
    *,
    implementation_refs: Mapping[str, Mapping[str, Any]],
    schema_source_refs: Mapping[str, Mapping[str, Any]],
    tracked_git_head: str,
) -> None:
    if (
        store_v1._clean_head(root) != tracked_git_head
        or not same_typed_json_v1(implementation_refs, _implementation_refs(root))
        or not same_typed_json_v1(schema_source_refs, _schema_source_refs(root))
    ):
        raise _error("loan-geography tracked implementation or schema changed during build")


def _selected_page_batches(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    selections: tuple[tuple[int, tuple[int, ...]], ...],
    *,
    batch_size: int = 16,
) -> Iterator[tuple[dict[str, Any], ...]]:
    """Hydrate an exact document/page axis while bounding Python peak memory."""

    if (
        type(selections) is not tuple
        or not selections
        or type(batch_size) is not int
        or batch_size <= 0
        or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not int
            or type(item[1]) is not tuple
            or not item[1]
            or any(type(page) is not int or page <= 0 for page in item[1])
            or item[1] != tuple(sorted(set(item[1])))
            for item in selections
        )
        or [item[0] for item in selections] != sorted({item[0] for item in selections})
    ):
        raise _error("loan-geography selected-page batch axis drifted")
    for start in range(0, len(selections), batch_size):
        requested = selections[start : start + batch_size]
        observed = store_v1.read_authenticated_family_first_documents_selected_pages_v1(
            capability,
            document_page_selections=requested,
        )
        if [item.get("document_packet", {}).get("document_ordinal") for item in observed] != [
            item[0] for item in requested
        ]:
            raise _error("loan-geography selected-page batch source order drifted")
        yield observed


def _read_selected_pages_in_batches(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    selections: tuple[tuple[int, tuple[int, ...]], ...],
    *,
    batch_size: int = 16,
) -> tuple[dict[str, Any], ...]:
    return tuple(
        snapshot
        for batch in _selected_page_batches(capability, selections, batch_size=batch_size)
        for snapshot in batch
    )


def _snapshot_selected_line_count(snapshot: Mapping[str, Any]) -> int:
    pages = snapshot.get("joined_pages")
    if type(pages) is not list:
        raise _error("loan-geography selected-page snapshot page axis drifted")
    total = 0
    for page in pages:
        lines = page.get("lines") if type(page) is dict else None
        if type(lines) is not list:
            raise _error("loan-geography selected-page snapshot line axis drifted")
        total += len(lines)
    return total


def _sparse_graph_worker_material(
    receipt: Mapping[str, Any],
    source_index: int,
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Build and publicly replay one sparse document in a worker process."""

    if type(source_index) is not int or source_index < 0 or type(snapshot) is not dict:
        raise _error("loan-geography sparse worker input drifted")
    built = graph_v1.build_loan_geography_scoped_graphs_v1(receipt, (snapshot,))
    replayed = graph_v1.validate_loan_geography_scoped_graphs_replay_v1(
        built,
        receipt,
        (snapshot,),
    )
    if not same_typed_json_v1(built, replayed):
        raise _error("loan-geography sparse graph public replay drifted")
    documents = replayed.get("documents")
    packet = snapshot.get("document_packet")
    if (
        type(documents) is not list
        or len(documents) != 1
        or type(packet) is not dict
        or type(packet.get("document_ordinal")) is not int
    ):
        raise _error("loan-geography sparse worker document denominator drifted")
    document = documents[0]
    material = {
        "batch_result_id": replayed.get("result_id"),
        "document": document,
        "document_ordinal": packet["document_ordinal"],
        "document_result_id": document.get("result_id") if type(document) is dict else None,
        "snapshot_id": snapshot.get("snapshot_id"),
        "source_index": source_index,
    }
    return {
        **material,
        "worker_output_id": "lg140v1:sparse-worker:" + canonical_json_sha256_v1(material),
    }


def _sparse_graph_worker_task(item: tuple[int, dict[str, Any]]) -> dict[str, Any]:
    if (
        type(item) is not tuple
        or len(item) != 2
        or type(item[0]) is not int
        or type(item[1]) is not dict
        or _FAMILY11_GRAPH_WORKER_RECEIPT is None
    ):
        raise _error("loan-geography sparse worker was not initialized exactly")
    return _sparse_graph_worker_material(
        _FAMILY11_GRAPH_WORKER_RECEIPT,
        item[0],
        item[1],
    )


def _validate_sparse_graph_worker_batch(
    receipt: Mapping[str, Any],
    snapshots: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    *,
    source_start: int,
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    """Validate IDs/source bindings and restore one sparse worker batch's axis."""

    if (
        type(source_start) is not int
        or source_start < 0
        or type(records) not in {list, tuple}
        or len(records) != len(snapshots)
        or any(type(record) is not dict for record in records)
    ):
        raise _error("loan-geography sparse worker batch denominator drifted")
    expected_indices = list(range(source_start, source_start + len(snapshots)))
    if any(type(record.get("source_index")) is not int for record in records):
        raise _error("loan-geography sparse worker source order binding drifted")
    ordered = sorted(records, key=lambda record: record.get("source_index", -1))
    if [record.get("source_index") for record in ordered] != expected_indices:
        raise _error("loan-geography sparse worker source order binding drifted")
    outcomes = receipt.get("documents")
    receipt_id = receipt.get("receipt_id")
    required = {
        "batch_result_id",
        "document",
        "document_ordinal",
        "document_result_id",
        "snapshot_id",
        "source_index",
        "worker_output_id",
    }
    documents: list[dict[str, Any]] = []
    packets: list[dict[str, Any]] = []
    coverages: list[dict[str, Any]] = []
    for source_index, record in zip(expected_indices, ordered, strict=True):
        snapshot = snapshots[source_index - source_start]
        packet = _packet(snapshot.get("document_packet"), source_index + 1)
        ordinal = packet["document_ordinal"]
        outcome = (
            outcomes[ordinal - 1] if type(outcomes) is list and len(outcomes) >= ordinal else None
        )
        if set(record) != required:
            raise _error("loan-geography sparse worker output shape drifted")
        material = canonical_clone_v1(record)
        worker_output_id = material.pop("worker_output_id")
        if worker_output_id != "lg140v1:sparse-worker:" + canonical_json_sha256_v1(material):
            raise _error("loan-geography sparse worker output identity drifted")
        document = record["document"]
        evidence_binding = document.get("evidence_binding") if type(document) is dict else None
        joined_pages = snapshot.get("joined_pages")
        selected_page_axis = (
            [page.get("page_sequence") for page in joined_pages]
            if type(joined_pages) is list
            else None
        )
        if (
            record["document_ordinal"] != ordinal
            or record["snapshot_id"] != snapshot.get("snapshot_id")
            or type(record["batch_result_id"]) is not str
            or not record["batch_result_id"].startswith("lgstv1:batch:")
            or type(document) is not dict
            or record["document_result_id"] != document.get("result_id")
            or document.get("document_ordinal") != ordinal
            or document.get("document_id") != packet["document_id"]
            or type(outcome) is not dict
            or selected_page_axis != outcome.get("selected_pages")
            or type(evidence_binding) is not dict
            or evidence_binding.get("document_id") != packet["document_id"]
            or evidence_binding.get("document_ordinal") != ordinal
            or evidence_binding.get("document_packet_id") != packet["packet_id"]
            or evidence_binding.get("document_evidence_root_sha256")
            != packet["document_evidence_root_sha256"]
            or evidence_binding.get("snapshot_id") != snapshot.get("snapshot_id")
            or evidence_binding.get("receipt_id") != receipt_id
            or evidence_binding.get("outcome_id") != outcome.get("outcome_id")
        ):
            raise _error("loan-geography sparse worker source binding drifted")
        _graph_envelope(document)
        selected_page_count = len(joined_pages)
        selected_line_count = _snapshot_selected_line_count(snapshot)
        coverage = {
            "coverage_status": outcome["coverage_status"],
            "outcome_id": outcome["outcome_id"],
            "receipt_id": receipt_id,
            "requires_full_document_review": outcome["requires_full_document_review"],
            "selected_line_count": selected_line_count,
            "selected_page_count": selected_page_count,
            "selection_mode": outcome["selection_mode"],
        }
        _coverage(
            coverage,
            receipt_id=receipt_id,
            outcome_id=outcome["outcome_id"],
        )
        documents.append(canonical_clone_v1(document))
        packets.append(packet)
        coverages.append(coverage)
    return tuple(documents), tuple(packets), tuple(coverages)


def _sparse_graph_path(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    receipt: Mapping[str, Any],
    *,
    batch_size: int,
    jobs: int = 1,
    prepared_receipt: Any | None = None,
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    """Build and replay each sparse batch before releasing its source snapshots."""

    outcomes = receipt.get("documents")
    if (
        type(outcomes) is not list
        or len(outcomes) != _TARGET_DOCUMENT_COUNT
        or type(batch_size) is not int
        or batch_size <= 0
        or type(jobs) is not int
        or jobs <= 0
    ):
        raise _error("loan-geography sparse receipt document axis drifted")
    local_receipt = (
        graph_v1._prepare_loan_geography_receipt_v1(receipt)  # noqa: SLF001
        if prepared_receipt is None
        else prepared_receipt
    )
    selections = tuple(
        (outcome["document_ordinal"], tuple(outcome["selected_pages"])) for outcome in outcomes
    )
    documents: list[dict[str, Any]] = []
    packets: list[dict[str, Any]] = []
    coverages: list[dict[str, Any]] = []

    def collect(executor: ProcessPoolExecutor | None) -> None:
        source_start = 0
        for snapshots in _selected_page_batches(
            capability,
            selections,
            batch_size=batch_size,
        ):
            work = tuple(
                (source_start + offset, snapshot) for offset, snapshot in enumerate(snapshots)
            )
            try:
                records = (
                    tuple(
                        _sparse_graph_worker_material(local_receipt, index, snapshot)
                        for index, snapshot in work
                    )
                    if executor is None
                    else tuple(executor.map(_sparse_graph_worker_task, work, chunksize=1))
                )
            except Exception as exc:
                raise _error("loan-geography sparse worker execution failed") from exc
            batch_documents, batch_packets, batch_coverages = _validate_sparse_graph_worker_batch(
                receipt,
                snapshots,
                records,
                source_start=source_start,
            )
            documents.extend(batch_documents)
            packets.extend(batch_packets)
            coverages.extend(batch_coverages)
            source_start += len(snapshots)

    if jobs == 1:
        collect(None)
    else:
        try:
            with ProcessPoolExecutor(
                max_workers=jobs,
                initializer=_initialize_family11_graph_worker,
                initargs=(canonical_clone_v1(receipt),),
            ) as executor:
                collect(executor)
        except FamilyFirstLoanGeography140FilingSchemaSweepV1Error:
            raise
        except Exception as exc:
            raise _error("loan-geography sparse worker pool failed") from exc
    if [item["document_ordinal"] for item in documents] != list(
        range(1, _TARGET_DOCUMENT_COUNT + 1)
    ):
        raise _error("loan-geography sparse graph complete document axis drifted")
    return tuple(documents), tuple(packets), tuple(coverages)


def build_authenticated_loan_geography_sparse_scoped_documents_v1(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    receipt: Mapping[str, Any],
    *,
    batch_size: int = 16,
    jobs: int = _DEFAULT_SPARSE_JOBS,
) -> tuple[dict[str, Any], ...]:
    """Benchmarkable sparse graph entrypoint using the formal batch/replay path."""

    documents, _packets, _coverages = _sparse_graph_path(
        capability,
        receipt,
        batch_size=batch_size,
        jobs=jobs,
    )
    return documents


def _initialize_family11_graph_worker(receipt: Mapping[str, Any]) -> None:
    """Install the one authenticated receipt copy used by a worker process."""

    global _FAMILY11_GRAPH_WORKER_RECEIPT
    if type(receipt) is not dict:
        raise _error("loan-geography direct-full worker receipt drifted")
    _FAMILY11_GRAPH_WORKER_RECEIPT = graph_v1._prepare_loan_geography_receipt_v1(  # noqa: SLF001
        receipt
    )


def _direct_full_worker_material(
    receipt: Mapping[str, Any],
    source_index: int,
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Build graph/context only; capability and sparse authority stay in the parent."""

    if type(source_index) is not int or source_index < 0 or type(snapshot) is not dict:
        raise _error("loan-geography direct-full worker input drifted")
    packet = snapshot.get("document_packet")
    if type(packet) is not dict or type(packet.get("document_ordinal")) is not int:
        raise _error("loan-geography direct-full worker document packet drifted")
    built_whole_document = graph_v1.build_loan_geography_whole_document_scoped_graph_v1(
        receipt,
        snapshot,
    )
    whole_document = graph_v1.validate_loan_geography_whole_document_scoped_graph_replay_v1(
        built_whole_document,
        receipt,
        snapshot,
    )
    if not same_typed_json_v1(built_whole_document, whole_document):
        raise _error("loan-geography direct-full graph public replay drifted")
    document_context = None
    total_control_requests = None
    total_controls: list[dict[str, Any]] = []
    if whole_document.get("disposition") == "EXACT_CUSTOMER_LOAN_GEOGRAPHY":
        built_context = graph_v1.build_loan_geography_document_context_v1(snapshot)
        document_context = graph_v1.validate_loan_geography_document_context_replay_v1(
            built_context,
            snapshot,
        )
        if not same_typed_json_v1(built_context, document_context):
            raise _error("loan-geography direct-full context public replay drifted")
        built_requests = graph_v1.build_loan_geography_customer_loan_total_control_requests_v1(
            whole_document,
            packet,
            snapshot,
            document_context=document_context,
        )
        total_control_requests = (
            graph_v1.validate_loan_geography_customer_loan_total_control_requests_replay_v1(
                built_requests,
                whole_document,
                packet,
                snapshot,
                document_context=document_context,
            )
        )
        if not same_typed_json_v1(built_requests, total_control_requests):
            raise _error("loan-geography total-control request public replay drifted")
        for lane_request in total_control_requests["lane_requests"]:
            if lane_request["classification"] != "STRUCTURALLY_ABSENT":
                continue
            requested_period_end = _customer_loan_total_requested_period_end(
                lane_request["period_end"]
            )
            built_control = total_control_v1.build_customer_loan_total_control_v1(
                snapshot,
                requested_period_end,
            )
            replayed_control = total_control_v1.validate_customer_loan_total_control_replay_v1(
                built_control,
                snapshot,
                requested_period_end,
            )
            if not same_typed_json_v1(built_control, replayed_control):
                raise _error("customer-loan total-control public replay drifted")
            total_controls.append(replayed_control)
    material = {
        "customer_loan_total_control_request_set": total_control_requests,
        "customer_loan_total_control_request_set_id": (
            total_control_requests.get("request_set_id")
            if type(total_control_requests) is dict
            else None
        ),
        "customer_loan_total_control_result_ids": [item["result_id"] for item in total_controls],
        "customer_loan_total_controls": total_controls,
        "document_context": document_context,
        "document_context_result_id": (
            document_context.get("result_id") if type(document_context) is dict else None
        ),
        "document_ordinal": packet["document_ordinal"],
        "snapshot_id": snapshot.get("snapshot_id"),
        "source_index": source_index,
        "whole_document": whole_document,
        "whole_document_result_id": whole_document.get("result_id"),
    }
    return {
        **material,
        "worker_output_id": "lg140v1:direct-full-worker:" + canonical_json_sha256_v1(material),
    }


def _direct_full_worker_task(
    item: tuple[int, dict[str, Any]],
) -> dict[str, Any]:
    """Pickle-safe ProcessPool entrypoint receiving one exact full snapshot."""

    if (
        type(item) is not tuple
        or len(item) != 2
        or type(item[0]) is not int
        or type(item[1]) is not dict
        or _FAMILY11_GRAPH_WORKER_RECEIPT is None
    ):
        raise _error("loan-geography direct-full worker was not initialized exactly")
    return _direct_full_worker_material(
        _FAMILY11_GRAPH_WORKER_RECEIPT,
        item[0],
        item[1],
    )


def _direct_full_snapshot_packet(
    snapshot: Mapping[str, Any], *, expected_ordinal: int
) -> dict[str, Any]:
    if type(snapshot) is not dict:
        raise _error("loan-geography direct oracle snapshot drifted")
    packet = _packet(snapshot.get("document_packet"), expected_ordinal)
    joined_pages = snapshot.get("joined_pages")
    if (
        type(joined_pages) is not list
        or len(joined_pages) != packet["page_count"]
        or [item.get("page_sequence") for item in joined_pages]
        != list(range(1, packet["page_count"] + 1))
        or _snapshot_selected_line_count(snapshot) != packet["line_count"]
    ):
        raise _error(
            "loan-geography direct oracle snapshot does not cover its exact "
            "physical page/line denominator"
        )
    return packet


def _validate_direct_full_worker_batch(
    receipt: Mapping[str, Any],
    sparse_by_ordinal: Mapping[int, Mapping[str, Any]],
    snapshots: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    *,
    source_start: int,
) -> tuple[
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any] | None, ...],
    tuple[dict[str, Any] | None, ...],
    tuple[list[dict[str, Any]], ...],
    tuple[dict[str, Any] | None, ...],
]:
    """Replay worker outputs in the parent and restore the authenticated source axis."""

    if (
        type(source_start) is not int
        or source_start < 0
        or type(records) not in {list, tuple}
        or len(records) != len(snapshots)
    ):
        raise _error("loan-geography direct-full worker batch denominator drifted")
    expected_indices = list(range(source_start, source_start + len(snapshots)))
    if any(type(record) is not dict for record in records):
        raise _error("loan-geography direct-full worker output drifted")
    if any(type(record.get("source_index")) is not int for record in records):
        raise _error("loan-geography direct-full worker source order binding drifted")
    ordered = sorted(records, key=lambda record: record.get("source_index", -1))
    if [record.get("source_index") for record in ordered] != expected_indices:
        raise _error("loan-geography direct-full worker source order binding drifted")

    equivalences: list[dict[str, Any]] = []
    contexts: list[dict[str, Any] | None] = []
    request_sets: list[dict[str, Any] | None] = []
    control_sets: list[list[dict[str, Any]]] = []
    numeric_inputs: list[dict[str, Any] | None] = []
    required = {
        "customer_loan_total_control_request_set",
        "customer_loan_total_control_request_set_id",
        "customer_loan_total_control_result_ids",
        "customer_loan_total_controls",
        "document_context",
        "document_context_result_id",
        "document_ordinal",
        "snapshot_id",
        "source_index",
        "whole_document",
        "whole_document_result_id",
        "worker_output_id",
    }
    receipt_id = receipt.get("receipt_id")
    outcomes = receipt.get("documents")
    for source_index, record in zip(expected_indices, ordered, strict=True):
        snapshot = snapshots[source_index - source_start]
        packet = _direct_full_snapshot_packet(
            snapshot,
            expected_ordinal=source_index + 1,
        )
        ordinal = packet["document_ordinal"]
        if set(record) != required:
            raise _error("loan-geography direct-full worker output shape drifted")
        material = canonical_clone_v1(record)
        worker_output_id = material.pop("worker_output_id")
        if worker_output_id != "lg140v1:direct-full-worker:" + canonical_json_sha256_v1(material):
            raise _error("loan-geography direct-full worker output identity drifted")
        whole_document = record["whole_document"]
        document_context = record["document_context"]
        total_control_requests = record["customer_loan_total_control_request_set"]
        total_controls = record["customer_loan_total_controls"]
        exact_document = (
            type(whole_document) is dict
            and whole_document.get("disposition") == "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
        )
        evidence_binding = (
            whole_document.get("evidence_binding") if type(whole_document) is dict else None
        )
        outcome = (
            outcomes[ordinal - 1] if type(outcomes) is list and len(outcomes) >= ordinal else None
        )
        if (
            record["document_ordinal"] != ordinal
            or record["snapshot_id"] != snapshot.get("snapshot_id")
            or type(whole_document) is not dict
            or record["whole_document_result_id"] != whole_document.get("result_id")
            or (
                exact_document
                and (
                    type(document_context) is not dict
                    or record["document_context_result_id"] != document_context.get("result_id")
                    or document_context.get("snapshot_id") != snapshot.get("snapshot_id")
                    or type(total_control_requests) is not dict
                    or record["customer_loan_total_control_request_set_id"]
                    != total_control_requests.get("request_set_id")
                    or type(total_controls) is not list
                    or record["customer_loan_total_control_result_ids"]
                    != [
                        item.get("result_id") if type(item) is dict else None
                        for item in total_controls
                    ]
                )
            )
            or (
                not exact_document
                and (
                    document_context is not None
                    or record["document_context_result_id"] is not None
                    or total_control_requests is not None
                    or record["customer_loan_total_control_request_set_id"] is not None
                    or total_controls != []
                    or record["customer_loan_total_control_result_ids"] != []
                )
            )
            or type(evidence_binding) is not dict
            or evidence_binding.get("document_id") != packet["document_id"]
            or evidence_binding.get("document_ordinal") != ordinal
            or evidence_binding.get("document_packet_id") != packet["packet_id"]
            or evidence_binding.get("document_evidence_root_sha256")
            != packet["document_evidence_root_sha256"]
            or evidence_binding.get("snapshot_id") != snapshot.get("snapshot_id")
            or evidence_binding.get("receipt_id") != receipt_id
            or type(outcome) is not dict
            or evidence_binding.get("outcome_id") != outcome.get("outcome_id")
        ):
            raise _error("loan-geography direct-full worker source binding drifted")
        try:
            replayed_context = (
                _document_context_envelope(document_context, packet=packet)
                if exact_document
                else None
            )
            _graph_envelope(whole_document)
            equivalence = graph_v1.compare_loan_geography_sparse_full_graphs_v1(
                sparse_by_ordinal[ordinal],
                whole_document,
                whole_document_line_count=packet["line_count"],
                whole_document_page_count=packet["page_count"],
            )
            if exact_document:
                typed_requests = _customer_loan_total_control_request_set_envelope(
                    total_control_requests,
                    packet=packet,
                    whole_document=whole_document,
                    source_snapshot=snapshot,
                )
                typed_controls = _customer_loan_total_controls(
                    total_controls,
                    packet=packet,
                    source_snapshot=snapshot,
                )
                request_ids, control_ids = _customer_loan_total_control_request_control_axis(
                    typed_requests,
                    typed_controls,
                )
                if (
                    record["customer_loan_total_control_result_ids"] != control_ids
                    or [
                        lane["control_request_id"]
                        for lane in typed_requests["lane_requests"]
                        if lane["classification"] == "STRUCTURALLY_ABSENT"
                    ]
                    != request_ids
                ):
                    raise _error("loan-geography worker request/control identity drifted")
                numeric_input = graph_v1.project_loan_geography_numeric_input_v1(
                    sparse_by_ordinal[ordinal],
                    packet,
                    document_context=replayed_context,
                    upstream_total_control_requests=typed_requests,
                    upstream_total_control_source_document=whole_document,
                    upstream_total_control_source_snapshot=snapshot,
                    upstream_total_controls=typed_controls,
                )
                if type(numeric_input) is not dict:
                    raise _error("loan-geography preprojected numeric input drifted")
            else:
                typed_requests = None
                typed_controls = []
                numeric_input = None
        except FamilyFirstLoanGeography140FilingSchemaSweepV1Error:
            raise
        except Exception as exc:
            raise _error("loan-geography direct-full worker output replay failed") from exc
        equivalences.append(
            _equivalence(
                equivalence,
                disposition=sparse_by_ordinal[ordinal]["disposition"],
            )
        )
        contexts.append(
            canonical_clone_v1(replayed_context) if replayed_context is not None else None
        )
        request_sets.append(
            canonical_clone_v1(typed_requests) if typed_requests is not None else None
        )
        control_sets.append(canonical_clone_v1(typed_controls))
        numeric_inputs.append(
            canonical_clone_v1(numeric_input) if numeric_input is not None else None
        )
    return (
        tuple(equivalences),
        tuple(contexts),
        tuple(request_sets),
        tuple(control_sets),
        tuple(numeric_inputs),
    )


def _whole_document_equivalences(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    receipt: Mapping[str, Any],
    sparse_documents: Sequence[Mapping[str, Any]],
    packets: Sequence[Mapping[str, Any]],
    *,
    batch_size: int,
    jobs: int = 1,
    prepared_receipt: Any | None = None,
) -> tuple[
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any] | None, ...],
    tuple[dict[str, Any] | None, ...],
    tuple[list[dict[str, Any]], ...],
    tuple[dict[str, Any] | None, ...],
]:
    """Run the same adapter on full documents in bounded deterministic batches."""

    if (
        len(sparse_documents) != len(packets)
        or len(packets) != _TARGET_DOCUMENT_COUNT
        or type(batch_size) is not int
        or batch_size <= 0
        or type(jobs) is not int
        or jobs <= 0
    ):
        raise _error("loan-geography direct oracle document denominator drifted")
    local_receipt = (
        graph_v1._prepare_loan_geography_receipt_v1(receipt)  # noqa: SLF001
        if prepared_receipt is None
        else prepared_receipt
    )
    selections = tuple(
        (
            packet["document_ordinal"],
            tuple(range(1, packet["page_count"] + 1)),
        )
        for packet in packets
    )
    sparse_by_ordinal = {item["document_ordinal"]: item for item in sparse_documents}
    equivalences: list[dict[str, Any]] = []
    contexts: list[dict[str, Any] | None] = []
    request_sets: list[dict[str, Any] | None] = []
    control_sets: list[list[dict[str, Any]]] = []
    numeric_inputs: list[dict[str, Any] | None] = []

    def collect(executor: ProcessPoolExecutor | None) -> None:
        source_start = 0
        for snapshots in _selected_page_batches(
            capability,
            selections,
            batch_size=batch_size,
        ):
            for offset, snapshot in enumerate(snapshots):
                _direct_full_snapshot_packet(
                    snapshot,
                    expected_ordinal=source_start + offset + 1,
                )
            work = tuple(
                (source_start + offset, snapshot) for offset, snapshot in enumerate(snapshots)
            )
            try:
                records = (
                    tuple(
                        _direct_full_worker_material(local_receipt, index, snapshot)
                        for index, snapshot in work
                    )
                    if executor is None
                    else tuple(executor.map(_direct_full_worker_task, work, chunksize=1))
                )
            except Exception as exc:
                raise _error("loan-geography direct-full worker execution failed") from exc
            (
                batch_equivalences,
                batch_contexts,
                batch_request_sets,
                batch_control_sets,
                batch_numeric_inputs,
            ) = _validate_direct_full_worker_batch(
                receipt,
                sparse_by_ordinal,
                snapshots,
                records,
                source_start=source_start,
            )
            equivalences.extend(batch_equivalences)
            contexts.extend(batch_contexts)
            request_sets.extend(batch_request_sets)
            control_sets.extend(batch_control_sets)
            numeric_inputs.extend(batch_numeric_inputs)
            source_start += len(snapshots)

    if jobs == 1:
        collect(None)
    else:
        try:
            with ProcessPoolExecutor(
                max_workers=jobs,
                initializer=_initialize_family11_graph_worker,
                initargs=(canonical_clone_v1(receipt),),
            ) as executor:
                collect(executor)
        except FamilyFirstLoanGeography140FilingSchemaSweepV1Error:
            raise
        except Exception as exc:
            raise _error("loan-geography direct-full worker pool failed") from exc
    if any(
        len(items) != _TARGET_DOCUMENT_COUNT
        for items in (equivalences, contexts, request_sets, control_sets, numeric_inputs)
    ):
        raise _error("loan-geography direct oracle equivalence denominator drifted")
    return (
        tuple(equivalences),
        tuple(contexts),
        tuple(request_sets),
        tuple(control_sets),
        tuple(numeric_inputs),
    )


def _bank(packet: Mapping[str, Any]) -> str:
    bank = packet.get("bank_provenance")
    if type(bank) is not str or bank not in _BANK_ORDER:
        raise _error("loan-geography document bank provenance drifted")
    return bank


def _packet(value: Any, expected_ordinal: int) -> dict[str, Any]:
    if type(value) is not dict:
        raise _error("loan-geography document packet drifted")
    required = {
        "assurance",
        "bank_provenance",
        "document_evidence_root_sha256",
        "document_id",
        "document_ordinal",
        "line_count",
        "packet_id",
        "page_count",
        "period",
        "scope",
        "source_pdf_ref",
        "year",
    }
    if (
        set(value) != required
        or type(value.get("document_ordinal")) is not int
        or value["document_ordinal"] != expected_ordinal
        or type(value.get("page_count")) is not int
        or value["page_count"] <= 0
        or type(value.get("line_count")) is not int
        or value["line_count"] <= 0
        or type(value.get("packet_id")) is not str
        or not value["packet_id"].startswith("ffdesv1:document:")
    ):
        raise _error("loan-geography document packet identity drifted")
    _bank(value)
    material = canonical_clone_v1(value)
    packet_id = material.pop("packet_id")
    if packet_id != "ffdesv1:document:" + canonical_json_sha256_v1(material):
        raise _error("loan-geography document packet hash drifted")
    return canonical_clone_v1(value)


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _write_exclusive(path: Path, payload: bytes) -> None:
    """Publish one immutable result without exposing a partial destination."""

    path.parent.mkdir(parents=True, exist_ok=True)
    directory = os.open(
        path.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
    )
    temporary_name = f".{path.name}.stage-{secrets.token_hex(16)}"
    temporary_created = False
    try:
        descriptor = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            0o444,
            dir_fd=directory,
        )
        temporary_created = True
        try:
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise _error("loan-geography sweep write made no progress")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        try:
            os.link(
                temporary_name,
                path.name,
                src_dir_fd=directory,
                dst_dir_fd=directory,
                follow_symlinks=False,
            )
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                raise _error("loan-geography sweep destination already exists") from exc
            raise
        os.fsync(directory)
        os.unlink(temporary_name, dir_fd=directory)
        temporary_created = False
        os.fsync(directory)
        published = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISREG(published.st_mode) or published.st_nlink != 1:
            raise _error("loan-geography sweep publication is not one distinct-link inode")
    finally:
        if temporary_created:
            try:
                os.unlink(temporary_name, dir_fd=directory)
                os.fsync(directory)
            except FileNotFoundError:
                pass
        os.close(directory)


def _mapping_rows(evidence: Mapping[str, Any], schema: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Project only the two accepted source-total roles into the bounded schema."""

    typed_numeric = numeric_v1.validate_loan_geography_numeric_reconciliation_v1(evidence)
    typed_schema = schema_v1.validate_loan_geography_bounded_schema_projection_v1(schema)
    if typed_numeric.get("status") != "EXACT_OBSERVED_NUMERIC_RECONCILIATION":
        raise _unresolved("loan-geography numeric evidence is not exact")
    schema_by_role = {item.get("role"): item for item in typed_schema.get("mapped_roles", [])}
    rows_by_role = {item.get("role"): item for item in typed_numeric.get("mapped_rows", [])}
    if set(schema_by_role) != set(_MAPPED_ROLES) or set(rows_by_role) != set(_MAPPED_ROLES):
        raise _error("loan-geography mapped role population drifted")
    periods = typed_numeric.get("period_axis")
    unit = typed_numeric.get("unit_context")
    if type(periods) is not list or type(unit) is not dict:
        raise _error("loan-geography mapped period/unit axis drifted")
    result = []
    for role in _MAPPED_ROLES:
        schema_row = schema_by_role[role]
        source_row = rows_by_role[role]
        cells = source_row.get("cells")
        if type(cells) is not list or len(cells) != len(periods):
            raise _error("loan-geography mapped money lane population drifted")
        values = []
        for lane, (cell, period) in enumerate(zip(cells, periods, strict=True)):
            selected = cell.get("selected_value") if type(cell) is dict else None
            if (
                type(cell) is not dict
                or type(period) is not dict
                or type(cell.get("lane_index")) is not int
                or cell["lane_index"] != lane
                or type(period.get("lane_index")) is not int
                or period["lane_index"] != lane
                or type(selected) is not int
                or cell.get("status") != "RESOLVED_OBSERVED_VALUE"
            ):
                raise _unresolved("loan-geography mapping retains an unresolved money cell")
            values.append(
                {
                    "bbox": canonical_clone_v1(cell.get("bbox")),
                    "cell_id": cell["cell_id"],
                    "lane_index": lane,
                    "page_sequence": cell["page_sequence"],
                    "period_end": period["period_end"],
                    "period_role": period["period_role"],
                    "selected_readers": canonical_clone_v1(cell["selected_readers"]),
                    "source_line_index": cell["source_line_index"],
                    "value": selected,
                }
            )
        result.append(
            {
                "canonical_name": schema_row["canonical_name"],
                "parent_report_norm_id": schema_row["parent_report_norm_id"],
                "period_axis": canonical_clone_v1(periods),
                "report_norm_id": schema_row["report_norm_id"],
                "role": role,
                "schema_projection_id": typed_schema["projection_id"],
                "source_label": source_row["label_surface"],
                "status": "VERIFIED_BY_CODEX",
                "unit_context": canonical_clone_v1(unit),
                "value_cells": values,
            }
        )
    return result


def _coverage(value: Any, *, receipt_id: str, outcome_id: str) -> dict[str, Any]:
    fields = {
        "coverage_status",
        "outcome_id",
        "receipt_id",
        "requires_full_document_review",
        "selected_line_count",
        "selected_page_count",
        "selection_mode",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["coverage_status"] != "PROVEN_COMPLETE_FOR_DECLARED_SPEC"
        or value["receipt_id"] != receipt_id
        or value["outcome_id"] != outcome_id
        or type(value["requires_full_document_review"]) is not bool
        or type(value["selection_mode"]) is not str
        or not value["selection_mode"]
    ):
        raise _error("loan-geography sparse retrieval coverage drifted")
    _strict_int(value["selected_page_count"], "selected page count", minimum=1)
    _strict_int(value["selected_line_count"], "selected line count")
    if value["requires_full_document_review"] != value["selection_mode"].startswith(
        "FULL_DOCUMENT_FALLBACK"
    ):
        raise _error("loan-geography full-document fallback flag drifted")
    return canonical_clone_v1(value)


def _equivalence(value: Any, *, disposition: str) -> dict[str, Any]:
    fields = {
        "disposition",
        "sparse_graph_result_id",
        "sparse_region_fingerprint",
        "status",
        "whole_document_graph_result_id",
        "whole_document_line_count",
        "whole_document_page_count",
        "whole_document_region_fingerprint",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["disposition"] != disposition
        or value["status"] != "EXACT_SPARSE_TO_WHOLE_DOCUMENT_STRUCTURE_EQUIVALENCE"
        or type(value["sparse_graph_result_id"]) is not str
        or not value["sparse_graph_result_id"]
        or type(value["whole_document_graph_result_id"]) is not str
        or not value["whole_document_graph_result_id"]
        or not same_typed_json_v1(
            value["sparse_region_fingerprint"],
            value["whole_document_region_fingerprint"],
        )
    ):
        raise _error("loan-geography sparse/whole-document structure equivalence drifted")
    _strict_int(value["whole_document_page_count"], "whole-document page count", minimum=1)
    _strict_int(value["whole_document_line_count"], "whole-document line count")
    return canonical_clone_v1(value)


def _graph_envelope(value: Any) -> dict[str, Any]:
    """Validate a content-addressed adapter envelope without granting live authority."""

    if (
        type(value) is not dict
        or value.get("family_id") != "LOAN_GEOGRAPHIC_CLASSIFICATION"
        or type(value.get("format_version")) is not str
        or type(value.get("result_id")) is not str
    ):
        raise _error("loan-geography scoped graph envelope drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id")
    if result_id.rsplit(":", 1)[-1] != canonical_json_sha256_v1(material):
        raise _error("loan-geography scoped graph identity drifted")
    return canonical_clone_v1(value)


def _document_context_envelope(
    value: Any,
    *,
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or type(value.get("result_id")) is not str:
        raise _error("loan-geography PDF-internal document context envelope drifted")
    context = canonical_clone_v1(value)
    identity = context.pop("result_id")
    if identity != "lgstv1:document-context:" + canonical_json_sha256_v1(context):
        raise _error("loan-geography PDF-internal document context identity drifted")
    context["result_id"] = identity
    if (
        context.get("format_version") != graph_v1.DOCUMENT_CONTEXT_FORMAT_VERSION
        or context.get("document_id") != packet["document_id"]
        or context.get("document_packet_id") != packet["packet_id"]
        or context.get("document_evidence_root_sha256") != packet["document_evidence_root_sha256"]
        or type(context.get("period_context")) is not dict
        or type(context.get("unit_context")) is not dict
        or context.get("state") != "FULL_DOCUMENT_PDF_INTERNAL_CONTEXT_PROPOSAL"
    ):
        raise _error("loan-geography PDF-internal document context drifted")
    period = context["period_context"]
    ending = {
        "ANNUAL": (31, 12),
        "H1": (30, 6),
        "Q1": (31, 3),
        "Q2": (30, 6),
        "Q3": (30, 9),
        "Q4": (31, 12),
    }.get(packet.get("period"))
    if period.get("resolution") == "DOMINANT_REPEATED_FULL_DATE_CONSENSUS" and (
        ending is None
        or type(packet.get("year")) is not int
        or period.get("current_period_end")
        != f"{ending[0]:02d}/{ending[1]:02d}/{packet['year']:04d}"
    ):
        raise _error(
            "loan-geography PDF-internal period conflicts with packet consistency metadata"
        )
    return context


def _customer_loan_total_control_source_locators(
    control: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    owner = control.get("owner_evidence")
    period = control.get("period_lane")
    unit = control.get("unit_evidence")
    total = control.get("total_control")
    groups = (
        owner.get("evidence") if type(owner) is dict else None,
        period.get("evidence") if type(period) is dict else None,
    )
    if (
        any(type(group) is not list or not group for group in groups)
        or type(unit) is not dict
        or type(unit.get("source")) is not dict
        or type(total) is not dict
        or type(total.get("source")) is not dict
    ):
        raise _error("customer-loan total-control source locator axis drifted")
    return tuple(
        canonical_clone_v1(locator)
        for locator in [*groups[0], *groups[1], unit["source"], total["source"]]
    )


def _customer_loan_total_requested_period_end(value: Any) -> str:
    if type(value) is not str:
        raise _error("customer-loan total-control request period drifted")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise _error("customer-loan total-control request period drifted") from exc
    if parsed.isoformat() != value:
        raise _error("customer-loan total-control request period drifted")
    return parsed.strftime("%d/%m/%Y")


def _customer_loan_total_control_envelope(
    value: Any,
    *,
    packet: Mapping[str, Any],
    source_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Cheap typed handoff plus exact parent-held source binding when supplied."""

    try:
        control = total_control_v1.validate_customer_loan_total_control_v1(value)
    except total_control_v1.CustomerLoanTotalControlV1Error as exc:
        raise _error("customer-loan total-control typed handoff drifted") from exc
    binding = control["document_binding"]
    if (
        binding.get("document_id") != packet["document_id"]
        or binding.get("document_ordinal") != packet["document_ordinal"]
        or binding.get("document_packet_id") != packet["packet_id"]
        or binding.get("document_evidence_root_sha256") != packet["document_evidence_root_sha256"]
        or binding.get("line_count") != packet["line_count"]
        or binding.get("page_count") != packet["page_count"]
        or not same_typed_json_v1(binding.get("source_pdf_ref"), packet["source_pdf_ref"])
    ):
        raise _error("customer-loan total-control document binding drifted")
    if source_snapshot is None:
        return control
    if (
        type(source_snapshot) is not dict
        or not same_typed_json_v1(source_snapshot.get("document_packet"), packet)
        or binding.get("snapshot_id") != source_snapshot.get("snapshot_id")
        or binding.get("manifest_id") != source_snapshot.get("manifest_id")
        or binding.get("query_selection_id") != source_snapshot.get("query_selection_id")
    ):
        raise _error("customer-loan total-control authenticated snapshot binding drifted")
    pages = source_snapshot.get("joined_pages")
    dimensions = source_snapshot.get("selected_page_dimensions")
    if type(pages) is not list or type(dimensions) is not list:
        raise _error("customer-loan total-control authenticated source axis drifted")
    pages_by_sequence = {item.get("page_sequence"): item for item in pages if type(item) is dict}
    dimensions_by_page = {
        item.get("physical_page"): item for item in dimensions if type(item) is dict
    }
    if (
        len(pages_by_sequence) != len(pages)
        or len(dimensions_by_page) != len(dimensions)
        or set(dimensions_by_page) != set(range(1, packet["page_count"] + 1))
    ):
        raise _error("customer-loan total-control authenticated page axis drifted")
    for locator in _customer_loan_total_control_source_locators(control):
        page_sequence = locator["page_sequence"]
        source_line_index = locator["source_line_index"]
        page = pages_by_sequence.get(page_sequence)
        dimension = dimensions_by_page.get(page_sequence)
        lines = page.get("lines") if type(page) is dict else None
        matching = (
            [line for line in lines if line.get("line_ordinal") == source_line_index]
            if type(lines) is list
            else []
        )
        if len(matching) != 1 or type(dimension) is not dict:
            raise _error("customer-loan total-control authenticated source line is absent")
        line = matching[0]
        numeric = line.get("numeric_recognition")
        expected = {
            "bbox": canonical_clone_v1(line.get("bbox")),
            "crop_ref": canonical_clone_v1(line.get("crop_ref")),
            "page_render": canonical_clone_v1(dimension),
            "page_sequence": page_sequence,
            "ppocrv6_reader_score": numeric.get("reader_score") if type(numeric) is dict else None,
            "ppocrv6_surface": numeric.get("raw_prediction") if type(numeric) is dict else None,
            "sample_id": line.get("sample_id"),
            "source_line_index": source_line_index,
            "vietocr_transformer_surface": line.get("vietocr_text"),
        }
        if not same_typed_json_v1(locator, expected):
            raise _error("customer-loan total-control authenticated locator binding drifted")
    return control


def _customer_loan_total_controls(
    value: Any,
    *,
    packet: Mapping[str, Any],
    source_snapshot: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise _error("customer-loan total-control result axis drifted")
    controls = [
        _customer_loan_total_control_envelope(
            item,
            packet=packet,
            source_snapshot=source_snapshot,
        )
        for item in value
    ]
    identities = [item["result_id"] for item in controls]
    periods = [item["requested_period_end"] for item in controls]
    if len(identities) != len(set(identities)) or len(periods) != len(set(periods)):
        raise _error("customer-loan total-control result identities or periods repeat")
    return controls


def _customer_loan_total_control_request_set_envelope(
    value: Any,
    *,
    packet: Mapping[str, Any],
    whole_document: Mapping[str, Any],
    source_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        request_set = graph_v1.validate_loan_geography_customer_loan_total_control_requests_v1(
            value
        )
    except graph_v1.LoanGeographyScopedTableAdapterV1Error as exc:
        raise _error("loan-geography total-control request typed handoff drifted") from exc
    binding = request_set["document_binding"]
    graph_binding = request_set["graph_binding"]
    dimensions = source_snapshot.get("selected_page_dimensions")
    if (
        binding["document_id"] != packet["document_id"]
        or binding["document_ordinal"] != packet["document_ordinal"]
        or binding["document_packet_id"] != packet["packet_id"]
        or binding["document_evidence_root_sha256"] != packet["document_evidence_root_sha256"]
        or binding["source_snapshot_id"] != source_snapshot.get("snapshot_id")
        or binding["source_whole_document_graph_result_id"] != whole_document.get("result_id")
        or graph_binding["region_fingerprint_sha256"]
        != canonical_json_sha256_v1(whole_document.get("region_fingerprint"))
        or type(dimensions) is not list
        or not same_typed_json_v1(request_set["source_page_render_bindings"], dimensions)
    ):
        raise _error("loan-geography total-control request source binding drifted")
    return request_set


def _customer_loan_total_control_request_control_axis(
    request_set: Mapping[str, Any],
    controls: Sequence[Mapping[str, Any]],
) -> tuple[list[str], list[str]]:
    absent = [
        lane
        for lane in request_set["lane_requests"]
        if lane["classification"] == "STRUCTURALLY_ABSENT"
    ]
    request_ids = [lane["control_request_id"] for lane in absent]
    request_periods = [
        _customer_loan_total_requested_period_end(lane["period_end"]) for lane in absent
    ]
    control_ids = [control["result_id"] for control in controls]
    control_periods = [control["requested_period_end"] for control in controls]
    if (
        any(type(item) is not str or not item for item in request_ids)
        or len(request_ids) != len(set(request_ids))
        or len(control_ids) != len(set(control_ids))
        or request_periods != control_periods
    ):
        raise _error("loan-geography total-control request/control axis drifted")
    return request_ids, control_ids


def _sparse_graph_binding_from_document(document: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "disposition": document.get("disposition"),
        "document_graph_result_id": document.get("result_id"),
        "document_id": document.get("document_id"),
        "document_ordinal": document.get("document_ordinal"),
        "evidence_binding": canonical_clone_v1(document.get("evidence_binding")),
        "family_id": document.get("family_id"),
        "format_version": SPARSE_GRAPH_BINDING_FORMAT_VERSION,
        "region_fingerprint": canonical_clone_v1(document.get("region_fingerprint")),
        "spec_id": document.get("spec_id"),
        "uniqueness": canonical_clone_v1(document.get("uniqueness")),
    }
    return {
        **fields,
        "binding_id": "lg140v1:sparse-graph-binding:" + canonical_json_sha256_v1(fields),
    }


def _sparse_graph_binding(value: Any) -> dict[str, Any]:
    fields = {
        "binding_id",
        "disposition",
        "document_graph_result_id",
        "document_id",
        "document_ordinal",
        "evidence_binding",
        "family_id",
        "format_version",
        "region_fingerprint",
        "spec_id",
        "uniqueness",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != SPARSE_GRAPH_BINDING_FORMAT_VERSION
        or value["family_id"] != graph_v1.FAMILY_ID
        or type(value["document_graph_result_id"]) is not str
        or not value["document_graph_result_id"].startswith("lgstv1:document:")
        or type(value["evidence_binding"]) is not dict
        or type(value["region_fingerprint"]) is not dict
        or type(value["uniqueness"]) is not dict
        or type(value["spec_id"]) is not str
        or not value["spec_id"]
    ):
        raise _error("loan-geography sparse graph binding drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("binding_id")
    if identity != "lg140v1:sparse-graph-binding:" + canonical_json_sha256_v1(material):
        raise _error("loan-geography sparse graph binding identity drifted")
    return canonical_clone_v1(value)


def _absence_evidence(value: Any, *, disposition: str) -> dict[str, Any]:
    fields = {
        "bounded_absence_ids",
        "kind",
        "population_scopes",
        "terminal_reason",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("loan-geography bounded absence evidence drifted")
    if disposition == "BROAD_POPULATION_BOUNDED_ABSENCE":
        if (
            value["kind"] != "VISIBLE_BROAD_OR_MIXED_GEOGRAPHY_POPULATION"
            or value["terminal_reason"]
            != "VISIBLE_GEOGRAPHY_POPULATION_IS_BROADER_THAN_CUSTOMER_LOANS"
            or type(value["bounded_absence_ids"]) is not list
            or not value["bounded_absence_ids"]
            or type(value["population_scopes"]) is not list
            or not value["population_scopes"]
            or not set(value["population_scopes"])
            <= {"BROAD_MIXED_LOAN_POPULATION", "BROAD_TOTAL_LOANS"}
        ):
            raise _error("broad geography population was narrowed or lost")
    elif disposition == "NOT_OBSERVED":
        if value != {
            "bounded_absence_ids": [],
            "kind": "NO_CUSTOMER_LOAN_GEOGRAPHY_STRUCTURE_OBSERVED",
            "population_scopes": [],
            "terminal_reason": "NO_EXACT_OR_BROAD_CUSTOMER_LOAN_GEOGRAPHY_CANDIDATE",
        }:
            raise _error("loan-geography not-observed evidence drifted")
    else:
        raise _error("absence evidence attached to a non-absence disposition")
    return canonical_clone_v1(value)


def _dash_period_bindings(pixel_graph: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    bindings = []
    graphs = pixel_graph.get("graphs")
    if type(graphs) is not list:
        raise _unresolved("loan-geography pixel graph list is unresolved")
    for graph in graphs:
        segments = graph.get("segments") if type(graph) is dict else None
        if type(segments) is not list:
            raise _unresolved("loan-geography pixel graph segment list is unresolved")
        for segment in segments:
            cells = segment.get("role_cells") if type(segment) is dict else None
            if type(cells) is not list:
                raise _unresolved("loan-geography pixel graph role cells are unresolved")
            for cell in cells:
                if (
                    type(cell) is dict
                    and cell.get("status")
                    == "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_EVIDENCE"
                ):
                    bindings.append(
                        {
                            "graph_cell_id": cell["graph_cell_id"],
                            "period_role": cell["period_role"],
                            "resolved_period": cell["resolved_period"],
                        }
                    )
    identities = [item["graph_cell_id"] for item in bindings]
    if len(identities) != len(set(identities)):
        raise _unresolved("loan-geography pixel graph detector-hole identity repeats")
    return tuple(sorted(bindings, key=lambda item: item["graph_cell_id"]))


def _exact_trial_evidence(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    document: Mapping[str, Any],
    packet: Mapping[str, Any],
    document_context: Mapping[str, Any],
    preprojected_numeric_input: Mapping[str, Any],
    receipt_id: str,
    schema: Mapping[str, Any],
) -> dict[str, Any]:
    """Hydrate numeric/pixels only after sparse/full structure is exactly equal."""

    try:
        pixel_graph = graph_v1.project_loan_geography_visible_dash_graph_v1(
            document,
            packet,
            document_context=document_context,
        )
    except graph_v1.LoanGeographyScopedTableAdapterV1Error as exc:
        if any(
            token in str(exc)
            for token in (
                "conflicts with PDF-internal document context",
                "period remains unresolved",
            )
        ):
            raise _unresolved(str(exc)) from exc
        raise
    pixel_graph = _graph_envelope(pixel_graph)
    period_bindings = _dash_period_bindings(pixel_graph)
    hole_manifest = None
    pixel_evidence = None
    render_ids: list[str] = []
    dash_bindings: Sequence[Mapping[str, Any]] = ()
    if period_bindings:
        hole_manifest = dash_v1.build_loan_geography_dash_hole_manifest_from_graph_v1(
            pixel_graph,
            selection_receipt_id=receipt_id,
            period_bindings=period_bindings,
        )
        physical_pages = tuple(sorted({item["page_sequence"] for item in hole_manifest["holes"]}))
        renders = store_v1.read_authenticated_family_first_document_page_renders_v1(
            capability,
            document_ordinal=packet["document_ordinal"],
            physical_pages=physical_pages,
        )
        pixel_evidence = dash_v1.build_loan_geography_visible_dash_evidence_v1(
            pixel_graph,
            hole_manifest,
            renders,
            packet,
        )
        pixel_evidence = dash_v1.validate_loan_geography_visible_dash_evidence_replay_v1(
            pixel_evidence,
            pixel_graph,
            hole_manifest,
            renders,
            packet,
        )
        dash_bindings = dash_v1.read_loan_geography_numeric_reconciliation_dash_bindings_v1(
            pixel_evidence,
            pixel_graph,
            hole_manifest,
            renders,
            packet,
        )
        render_ids = [item["render_id"] for item in renders]
    if type(preprojected_numeric_input) is not dict:
        raise _error("exact loan-geography trial lacks its parent-projected numeric input")
    numeric_input = canonical_clone_v1(preprojected_numeric_input)
    numeric = numeric_v1.build_loan_geography_numeric_reconciliation_v1(
        numeric_input,
        visible_dash_evidence=dash_bindings,
    )
    numeric = numeric_v1.validate_loan_geography_numeric_reconciliation_replay_v1(
        numeric,
        numeric_input,
        visible_dash_evidence=dash_bindings,
    )
    if numeric["status"] != "EXACT_OBSERVED_NUMERIC_RECONCILIATION":
        raise _unresolved("loan-geography exact structure did not numerically reconcile")
    mappings = _mapping_rows(numeric, schema)
    return {
        "mapped_children": mappings,
        "numeric_evidence": numeric,
        "numeric_input": numeric_input,
        "pixel_dash_evidence": pixel_evidence,
        "pixel_dash_hole_manifest": hole_manifest,
        "pixel_graph_projection": pixel_graph,
        "pixel_render_ids": render_ids,
        "presentation_mode": numeric["presentation_mode"],
    }


def _bounded_absence_from_document(document: Mapping[str, Any]) -> dict[str, Any]:
    disposition = document["disposition"]
    if disposition == "NOT_OBSERVED":
        return {
            "bounded_absence_ids": [],
            "kind": "NO_CUSTOMER_LOAN_GEOGRAPHY_STRUCTURE_OBSERVED",
            "population_scopes": [],
            "terminal_reason": "NO_EXACT_OR_BROAD_CUSTOMER_LOAN_GEOGRAPHY_CANDIDATE",
        }
    if disposition != "BROAD_POPULATION_BOUNDED_ABSENCE":
        raise _error("loan-geography absence projector received a non-absence graph")
    absences = document.get("bounded_absences")
    if type(absences) is not list or not absences:
        raise _error("loan-geography broad disposition lacks bounded absence evidence")
    identities = sorted(
        item["segment_id"]
        for item in absences
        if type(item) is dict and type(item.get("segment_id")) is str
    )
    raw_scopes = [
        item.get("population_scope", {}).get("scope_id") for item in absences if type(item) is dict
    ]
    if (
        len(identities) != len(absences)
        or len(raw_scopes) != len(absences)
        or any(
            type(scope) is not str
            or scope not in {"BROAD_MIXED_LOAN_POPULATION", "BROAD_TOTAL_LOANS"}
            for scope in raw_scopes
        )
    ):
        raise _error("loan-geography broad bounded absence projection drifted")
    scopes = sorted(set(raw_scopes))
    return {
        "bounded_absence_ids": identities,
        "kind": "VISIBLE_BROAD_OR_MIXED_GEOGRAPHY_POPULATION",
        "population_scopes": scopes,
        "terminal_reason": "VISIBLE_GEOGRAPHY_POPULATION_IS_BROADER_THAN_CUSTOMER_LOANS",
    }


def _trial_from_graph(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    document: Mapping[str, Any],
    packet: Mapping[str, Any],
    document_context: Mapping[str, Any] | None,
    total_control_requests: Mapping[str, Any] | None,
    total_controls: Sequence[Mapping[str, Any]],
    preprojected_numeric_input: Mapping[str, Any] | None,
    coverage: Mapping[str, Any],
    equivalence: Mapping[str, Any],
    receipt_id: str,
    schema: Mapping[str, Any],
) -> dict[str, Any]:
    disposition = document.get("disposition")
    if disposition not in _DISPOSITIONS:
        raise _error("loan-geography shared adapter disposition drifted")
    if disposition == "EXACT_CUSTOMER_LOAN_GEOGRAPHY":
        typed_context = _document_context_envelope(document_context, packet=packet)
        if (
            type(total_control_requests) is not dict
            or type(total_controls) not in {list, tuple}
            or type(preprojected_numeric_input) is not dict
        ):
            raise _error("exact loan-geography trial lacks total-control handoff evidence")
        typed_requests = canonical_clone_v1(total_control_requests)
        typed_controls = canonical_clone_v1(list(total_controls))
    else:
        if (
            document_context is not None
            or total_control_requests is not None
            or total_controls not in ((), [])
            or preprojected_numeric_input is not None
        ):
            raise _error("non-exact loan-geography trial hydrated exact-only evidence")
        typed_context = None
        typed_requests = None
        typed_controls = []
    common = {
        "customer_loan_total_control_request_set": typed_requests,
        "customer_loan_total_controls": typed_controls,
        "document": canonical_clone_v1(packet),
        "document_context_evidence": typed_context,
        "gemma_challenger_refs": [],
        "region_coverage": canonical_clone_v1(coverage),
        "sparse_graph": _sparse_graph_binding_from_document(document),
        "structural_disposition": disposition,
        "structural_equivalence": canonical_clone_v1(equivalence),
        "unresolved_reasons": [],
    }
    if disposition == "EXACT_CUSTOMER_LOAN_GEOGRAPHY":
        if typed_context is None:
            raise _error("exact loan-geography trial lacks replayed document context")
        try:
            exact = _exact_trial_evidence(
                capability,
                document,
                packet,
                typed_context,
                preprojected_numeric_input,
                receipt_id,
                schema,
            )
        except LoanGeographyTrialUnresolvedV1Error as exc:
            return {
                **common,
                "absence_evidence": None,
                "disposition": "UNRESOLVED",
                "mapped_children": [],
                "numeric_evidence": None,
                "numeric_input": None,
                "pixel_dash_evidence": None,
                "pixel_dash_hole_manifest": None,
                "pixel_graph_projection": None,
                "pixel_render_ids": [],
                "presentation_mode": None,
                "status": "UNRESOLVED",
                "unresolved_reasons": [str(exc)],
            }
        return {
            **common,
            **exact,
            "absence_evidence": None,
            "disposition": disposition,
            "status": "VERIFIED_BY_CODEX",
        }
    if disposition in {"BROAD_POPULATION_BOUNDED_ABSENCE", "NOT_OBSERVED"}:
        return {
            **common,
            "absence_evidence": _bounded_absence_from_document(document),
            "disposition": disposition,
            "mapped_children": [],
            "numeric_evidence": None,
            "numeric_input": None,
            "pixel_dash_evidence": None,
            "pixel_dash_hole_manifest": None,
            "pixel_graph_projection": None,
            "pixel_render_ids": [],
            "presentation_mode": None,
            "status": "VERIFIED_BOUNDED_ABSENCE",
        }
    reasons = document.get("unresolved_candidates")
    if type(reasons) is not list or not reasons:
        reasons = [{"unresolved_reason": "SHARED_SCOPED_TABLE_GRAPH_UNRESOLVED"}]
    return {
        **common,
        "absence_evidence": None,
        "disposition": "UNRESOLVED",
        "mapped_children": [],
        "numeric_evidence": None,
        "numeric_input": None,
        "pixel_dash_evidence": None,
        "pixel_dash_hole_manifest": None,
        "pixel_graph_projection": None,
        "pixel_render_ids": [],
        "presentation_mode": None,
        "status": "UNRESOLVED",
        "unresolved_reasons": canonical_clone_v1(reasons),
    }


def _validate_trial_total_control_handoff(
    request_value: Any,
    control_values: Any,
    *,
    packet: Mapping[str, Any],
    equivalence: Mapping[str, Any],
    graph: Mapping[str, Any],
    numeric_input: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        request_set = graph_v1.validate_loan_geography_customer_loan_total_control_requests_v1(
            request_value
        )
    except graph_v1.LoanGeographyScopedTableAdapterV1Error as exc:
        raise _error("loan-geography persisted total-control request drifted") from exc
    controls = _customer_loan_total_controls(control_values, packet=packet)
    request_ids, control_ids = _customer_loan_total_control_request_control_axis(
        request_set,
        controls,
    )
    binding = request_set["document_binding"]
    expected_fingerprint_sha256 = canonical_json_sha256_v1(
        equivalence["whole_document_region_fingerprint"]
    )
    if (
        binding["document_id"] != packet["document_id"]
        or binding["document_ordinal"] != packet["document_ordinal"]
        or binding["document_packet_id"] != packet["packet_id"]
        or binding["document_evidence_root_sha256"] != packet["document_evidence_root_sha256"]
        or binding["source_whole_document_graph_result_id"]
        != equivalence["whole_document_graph_result_id"]
        or request_set["graph_binding"]["region_fingerprint_sha256"] != expected_fingerprint_sha256
        or expected_fingerprint_sha256
        != canonical_json_sha256_v1(equivalence["sparse_region_fingerprint"])
        or equivalence["sparse_graph_result_id"] != graph["document_graph_result_id"]
        or request_set["graph_binding"]["graph_id"] != numeric_input.get("region_id")
    ):
        raise _error("loan-geography sparse/full total-control bridge drifted")
    total = numeric_input.get("printed_customer_loan_total")
    evidence = total.get("control_evidence") if type(total) is dict else None
    lanes = request_set["lane_requests"]
    if type(evidence) is not list or len(evidence) != len(lanes):
        raise _error("loan-geography total-control numeric evidence axis drifted")
    control_by_period = {
        date.fromisoformat(lane["period_end"]).strftime("%d/%m/%Y"): control
        for lane, control in zip(
            [lane for lane in lanes if lane["classification"] == "STRUCTURALLY_ABSENT"],
            controls,
            strict=True,
        )
    }
    expected_modes = {
        "LOCAL_LABELED_TOTAL": "LOCAL_LABELED_TOTAL",
        "LOCAL_UNLABELED_TOTAL_ROW": "LOCAL_UNLABELED_TOTAL_ROW",
        "STRUCTURALLY_ABSENT": "UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL",
    }
    for lane, lane_evidence in zip(lanes, evidence, strict=True):
        expected_mode = expected_modes[lane["classification"]]
        if (
            type(lane_evidence) is not dict
            or lane_evidence.get("lane_index") != lane["lane_index"]
            or lane_evidence.get("resolution_mode") != expected_mode
        ):
            raise _error("loan-geography total-control source mode conflicts with its request")
        if lane["classification"] == "STRUCTURALLY_ABSENT":
            requested = _customer_loan_total_requested_period_end(lane["period_end"])
            control = control_by_period.get(requested)
            if (
                control is None
                or lane_evidence.get("control_request_id") != lane["control_request_id"]
                or lane_evidence.get("control_result_id") != control["result_id"]
                or lane_evidence.get("request_set_id") != request_set["request_set_id"]
                or lane_evidence.get("source_document_graph_result_id")
                != equivalence["whole_document_graph_result_id"]
                or lane_evidence.get("source_snapshot_id")
                != control["document_binding"]["snapshot_id"]
                or not same_typed_json_v1(
                    lane_evidence.get("source_locator"),
                    control["total_control"]["source"],
                )
            ):
                raise _error("loan-geography upstream total-control provenance drifted")
    if len(request_ids) != len(control_ids):
        raise _error("loan-geography total-control request/result count drifted")
    return request_set, controls


def _validate_trial(
    value: Any,
    *,
    expected_ordinal: int,
    receipt_id: str,
    outcome_id: str,
    schema: Mapping[str, Any],
) -> dict[str, Any]:
    fields = {
        "absence_evidence",
        "customer_loan_total_control_request_set",
        "customer_loan_total_controls",
        "disposition",
        "document",
        "document_context_evidence",
        "gemma_challenger_refs",
        "mapped_children",
        "numeric_evidence",
        "numeric_input",
        "pixel_dash_evidence",
        "pixel_dash_hole_manifest",
        "pixel_graph_projection",
        "pixel_render_ids",
        "presentation_mode",
        "region_coverage",
        "sparse_graph",
        "status",
        "structural_disposition",
        "structural_equivalence",
        "unresolved_reasons",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["disposition"] not in _DISPOSITIONS
        or value["structural_disposition"] not in _DISPOSITIONS
        or value["status"] not in _TERMINAL_STATUSES
        or type(value["gemma_challenger_refs"]) is not list
        or value["gemma_challenger_refs"]
        or type(value["unresolved_reasons"]) is not list
        or type(value["pixel_render_ids"]) is not list
        or type(value["customer_loan_total_controls"]) is not list
    ):
        raise _error("loan-geography trial contract drifted")
    packet = _packet(value["document"], expected_ordinal)
    document_context = (
        None
        if value["document_context_evidence"] is None
        else _document_context_envelope(value["document_context_evidence"], packet=packet)
    )
    coverage = _coverage(value["region_coverage"], receipt_id=receipt_id, outcome_id=outcome_id)
    if (
        coverage["selected_page_count"] > packet["page_count"]
        or coverage["selected_line_count"] > packet["line_count"]
        or (
            coverage["requires_full_document_review"]
            and (
                coverage["selected_page_count"] != packet["page_count"]
                or coverage["selected_line_count"] != packet["line_count"]
            )
        )
    ):
        raise _error("loan-geography sparse hydration exceeds its document packet")
    graph = _sparse_graph_binding(value["sparse_graph"])
    equivalence = _equivalence(
        value["structural_equivalence"],
        disposition=value["structural_disposition"],
    )
    if (
        equivalence["sparse_graph_result_id"] != graph["document_graph_result_id"]
        or graph.get("document_id") != packet["document_id"]
        or graph.get("document_ordinal") != expected_ordinal
        or graph.get("disposition") != value["structural_disposition"]
        or graph.get("evidence_binding", {}).get("document_packet_id") != packet["packet_id"]
        or graph.get("evidence_binding", {}).get("receipt_id") != receipt_id
        or graph.get("evidence_binding", {}).get("outcome_id") != outcome_id
        or not same_typed_json_v1(
            graph.get("region_fingerprint"),
            equivalence["sparse_region_fingerprint"],
        )
        or equivalence["whole_document_page_count"] != packet["page_count"]
        or equivalence["whole_document_line_count"] != packet["line_count"]
    ):
        raise _error("loan-geography sparse graph/equivalence binding drifted")
    uniqueness = graph["uniqueness"]
    if (
        set(uniqueness)
        != {
            "exact_logical_graph_count",
            "multiple_identical_region_count",
            "partial_nonterminal_graph_count",
            "physical_region_count",
        }
        or any(type(item) is not int or item < 0 for item in uniqueness.values())
        or uniqueness["exact_logical_graph_count"]
        != (1 if value["structural_disposition"] == "EXACT_CUSTOMER_LOAN_GEOGRAPHY" else 0)
    ):
        raise _error("loan-geography sparse graph uniqueness drifted")
    if value["structural_disposition"] != "EXACT_CUSTOMER_LOAN_GEOGRAPHY" and (
        value["customer_loan_total_control_request_set"] is not None
        or value["customer_loan_total_controls"]
    ):
        raise _error("non-exact loan-geography trial retained total-control evidence")

    disposition = value["disposition"]
    if disposition != "UNRESOLVED" and disposition != value["structural_disposition"]:
        raise _error("loan-geography terminal/structural disposition binding drifted")
    expected_status = (
        "VERIFIED_BY_CODEX"
        if disposition == "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
        else "VERIFIED_BOUNDED_ABSENCE"
        if disposition in {"BROAD_POPULATION_BOUNDED_ABSENCE", "NOT_OBSERVED"}
        else "UNRESOLVED"
    )
    if value["status"] != expected_status:
        raise _error("loan-geography disposition/status binding drifted")

    if disposition == "EXACT_CUSTOMER_LOAN_GEOGRAPHY":
        if (
            value["absence_evidence"] is not None
            or document_context is None
            or value["presentation_mode"]
            not in {
                "REPEATED_FULL_SEGMENT_ONE_PERIOD_PER_PAGE",
                "SINGLE_PAGE_GEOGRAPHY_COLUMNS_ACCOUNTING_ROWS",
                "SINGLE_PAGE_GEOGRAPHY_ROWS_ACCOUNTING_COLUMNS",
            }
            or value["unresolved_reasons"]
            or type(value["numeric_input"]) is not dict
            or type(value["numeric_evidence"]) is not dict
            or type(value["mapped_children"]) is not list
            or len(value["mapped_children"]) != 2
        ):
            raise _error("loan-geography exact trial retains unresolved structure")
        numeric = numeric_v1.validate_loan_geography_numeric_reconciliation_v1(
            value["numeric_evidence"]
        )
        expected_numeric_input_id = "lgnrv1:input:" + canonical_json_sha256_v1(
            {
                "source": value["numeric_input"],
                "visible_dash_evidence_ids": numeric["visible_dash_evidence_ids"],
            }
        )
        if numeric["status"] != "EXACT_OBSERVED_NUMERIC_RECONCILIATION":
            raise _error("loan-geography exact trial numeric reconciliation drifted")
        if numeric.get("input_id") != expected_numeric_input_id:
            raise _error("loan-geography numeric input/result content binding drifted")
        typed_request_set, typed_total_controls = _validate_trial_total_control_handoff(
            value["customer_loan_total_control_request_set"],
            value["customer_loan_total_controls"],
            packet=packet,
            equivalence=equivalence,
            graph=graph,
            numeric_input=value["numeric_input"],
        )
        context_id = document_context["result_id"]
        inherited_periods = [
            item
            for item in numeric["period_axis"]
            if item.get("resolution_mode") == "DOCUMENT_INHERITED_EXACT_DATE"
        ]
        inherited_unit = (
            numeric["unit_context"].get("resolution_mode") == "DOCUMENT_INHERITED_EXACT_UNIT"
        )
        if (
            any(item.get("evidence_ref") == packet["packet_id"] for item in numeric["period_axis"])
            or numeric["unit_context"].get("evidence_ref") == packet["packet_id"]
            or any(item.get("evidence_ref") != context_id for item in inherited_periods)
            or (inherited_unit and numeric["unit_context"].get("evidence_ref") != context_id)
        ):
            raise _error("loan-geography packet metadata was used as period/unit evidence")
        mappings = _mapping_rows(numeric, schema)
        if not same_typed_json_v1(mappings, value["mapped_children"]):
            raise _error("loan-geography exact trial mapping projection drifted")
        holes = value["pixel_dash_hole_manifest"]
        overlay = value["pixel_dash_evidence"]
        pixel_graph = _graph_envelope(value["pixel_graph_projection"])
        projected_graphs = pixel_graph.get("graphs")
        projected_region_id = (
            projected_graphs[0].get("graph_id")
            if type(projected_graphs) is list
            and len(projected_graphs) == 1
            and type(projected_graphs[0]) is dict
            else None
        )
        if (
            pixel_graph.get("source_document_graph_result_id") != graph["document_graph_result_id"]
            or pixel_graph.get("document_context_result_id") != document_context["result_id"]
            or pixel_graph.get("evidence_binding", {}).get("receipt_id") != receipt_id
            or pixel_graph.get("evidence_binding", {}).get("document_packet_id")
            != packet["packet_id"]
            or value["numeric_input"].get("source_id") != pixel_graph["result_id"]
            or value["numeric_input"].get("region_id") != projected_region_id
            or numeric.get("source_id") != pixel_graph["result_id"]
            or numeric.get("region_id") != projected_region_id
        ):
            raise _error("loan-geography graph/pixel/numeric projection binding drifted")
        if (holes is None) != (overlay is None):
            raise _error("loan-geography pixel hole/evidence presence drifted")
        if overlay is not None:
            typed_overlay = dash_v1.validate_loan_geography_visible_dash_evidence_v1(overlay)
            overlay_dash_ids = sorted(
                cell["dash_evidence"]["evidence_id"] for cell in typed_overlay["rescue_cells"]
            )
            render_ids = sorted(item["render_id"] for item in typed_overlay["render_bindings"])
            if (
                typed_overlay["status"] != "AUTHENTICATED_VISIBLE_DASH_CELLS_BOUND"
                or typed_overlay["metrics"]["direct_visible_dash_zero_cell_count"]
                != typed_overlay["metrics"]["requested_hole_count"]
                or typed_overlay["metrics"]["bounded_candidate_cell_count"] != 0
                or typed_overlay["metrics"]["unresolved_pixel_cell_count"] != 0
                or not same_typed_json_v1(
                    typed_overlay["hole_manifest"], value["pixel_dash_hole_manifest"]
                )
                or typed_overlay["graph_binding"]["graph_result_id"] != pixel_graph["result_id"]
                or overlay_dash_ids != numeric["visible_dash_evidence_ids"]
                or render_ids != sorted(value["pixel_render_ids"])
            ):
                raise _error("loan-geography pixel/numeric/graph evidence binding drifted")
            if not value["pixel_render_ids"]:
                raise _error("loan-geography dash evidence lacks authenticated renders")
        elif value["pixel_render_ids"] or numeric["visible_dash_evidence_ids"]:
            raise _error("loan-geography render/dash hydration occurred without detector holes")
    elif disposition in {"BROAD_POPULATION_BOUNDED_ABSENCE", "NOT_OBSERVED"}:
        _absence_evidence(value["absence_evidence"], disposition=disposition)
        if (
            any(
                item is not None
                for item in (
                    value["numeric_input"],
                    value["numeric_evidence"],
                    value["document_context_evidence"],
                    value["pixel_dash_evidence"],
                    value["pixel_dash_hole_manifest"],
                    value["pixel_graph_projection"],
                    value["presentation_mode"],
                )
            )
            or value["mapped_children"]
            or value["pixel_render_ids"]
            or value["unresolved_reasons"]
            or value["customer_loan_total_control_request_set"] is not None
            or value["customer_loan_total_controls"]
        ):
            raise _error("bounded absence trial hydrated numeric, pixel, or total-control evidence")
    else:
        if not value["unresolved_reasons"]:
            raise _error("unresolved loan-geography trial lacks an explicit reason")
        if value["mapped_children"]:
            raise _error("unresolved loan-geography trial emitted mappings")

    return canonical_clone_v1(
        {
            **value,
            "customer_loan_total_control_request_set": (
                typed_request_set
                if disposition == "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
                else value["customer_loan_total_control_request_set"]
            ),
            "customer_loan_total_controls": (
                typed_total_controls
                if disposition == "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
                else value["customer_loan_total_controls"]
            ),
            "document": packet,
            "region_coverage": coverage,
            "sparse_graph": graph,
            "structural_equivalence": equivalence,
        }
    )


def _counter(values: Sequence[str], expected: Mapping[str, int], label: str) -> dict[str, int]:
    observed = Counter(values)
    normalized = {key: observed[key] for key in expected}
    if observed != Counter(expected):
        raise _error(f"loan-geography {label} counts drifted")
    return normalized


def _region_receipt_binding_from_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    documents = [
        {
            "coverage_status": item.get("coverage_status"),
            "document_evidence_root_sha256": item.get("document_evidence_root_sha256"),
            "document_id": item.get("document_id"),
            "document_line_count": item.get("document_line_count"),
            "document_ordinal": item.get("document_ordinal"),
            "document_packet_id": item.get("document_packet_id"),
            "document_page_count": item.get("document_page_count"),
            "fallback_reason": item.get("fallback_reason"),
            "outcome_id": item.get("outcome_id"),
            "requires_full_document_review": item.get("requires_full_document_review"),
            "selected_page_axis_sha256": canonical_json_sha256_v1(item.get("selected_pages")),
            "selected_page_count": (
                len(item["selected_pages"]) if type(item.get("selected_pages")) is list else None
            ),
            "selection_mode": item.get("selection_mode"),
        }
        for item in receipt.get("documents", [])
        if type(item) is dict
    ]
    material = {
        "documents": documents,
        "family_id": receipt.get("family_id"),
        "format_version": RECEIPT_BINDING_FORMAT_VERSION,
        "metrics": canonical_clone_v1(receipt.get("metrics")),
        "query_spec_id": receipt.get("source_binding", {}).get("query_spec_id"),
        "receipt_id": receipt.get("receipt_id"),
        "source_binding": canonical_clone_v1(receipt.get("source_binding")),
        "state": "BOUNDED_ROOTS_AND_COVERAGE_ONLY_NO_RECEIPT_SELF_AUTHORITY",
    }
    return {
        **material,
        "binding_id": "lg140v1:retrieval-receipt-binding:" + canonical_json_sha256_v1(material),
    }


def _region_receipt_binding(value: Any) -> dict[str, Any]:
    fields = {
        "binding_id",
        "documents",
        "family_id",
        "format_version",
        "metrics",
        "query_spec_id",
        "receipt_id",
        "source_binding",
        "state",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != RECEIPT_BINDING_FORMAT_VERSION
        or value["family_id"] != graph_v1.FAMILY_ID
        or value["state"] != "BOUNDED_ROOTS_AND_COVERAGE_ONLY_NO_RECEIPT_SELF_AUTHORITY"
        or type(value["receipt_id"]) is not str
        or not value["receipt_id"].startswith("fffrrv2:receipt:")
        or type(value["query_spec_id"]) is not str
        or not value["query_spec_id"].startswith("fffrrv2:query:")
        or type(value["documents"]) is not list
        or len(value["documents"]) != _TARGET_DOCUMENT_COUNT
        or type(value["metrics"]) is not dict
        or type(value["source_binding"]) is not dict
    ):
        raise _error("loan-geography bounded retrieval receipt binding drifted")
    document_fields = {
        "coverage_status",
        "document_evidence_root_sha256",
        "document_id",
        "document_line_count",
        "document_ordinal",
        "document_packet_id",
        "document_page_count",
        "fallback_reason",
        "outcome_id",
        "requires_full_document_review",
        "selected_page_axis_sha256",
        "selected_page_count",
        "selection_mode",
    }
    for ordinal, document in enumerate(value["documents"], 1):
        if (
            type(document) is not dict
            or set(document) != document_fields
            or document["document_ordinal"] != ordinal
            or document["coverage_status"] != "PROVEN_COMPLETE_FOR_DECLARED_SPEC"
            or type(document["document_id"]) is not str
            or not document["document_id"]
            or type(document["document_packet_id"]) is not str
            or not document["document_packet_id"]
            or type(document["outcome_id"]) is not str
            or not document["outcome_id"].startswith("fffrrv2:document:")
            or type(document["requires_full_document_review"]) is not bool
            or type(document["selection_mode"]) is not str
            or not document["selection_mode"]
            or type(document["selected_page_axis_sha256"]) is not str
            or len(document["selected_page_axis_sha256"]) != 64
        ):
            raise _error("loan-geography bounded retrieval document binding drifted")
        _strict_int(document["selected_page_count"], "receipt selected page count", minimum=1)
        _strict_int(document["document_page_count"], "receipt document page count", minimum=1)
        _strict_int(document["document_line_count"], "receipt document line count")
        if document["requires_full_document_review"] != document["selection_mode"].startswith(
            "FULL_DOCUMENT_FALLBACK"
        ):
            raise _error("loan-geography bounded retrieval fallback binding drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("binding_id")
    if identity != "lg140v1:retrieval-receipt-binding:" + canonical_json_sha256_v1(material):
        raise _error("loan-geography bounded retrieval receipt identity drifted")
    return canonical_clone_v1(value)


def _assert_frozen_region_retrieval_contract(
    *,
    implementation_refs: Mapping[str, Mapping[str, Any]],
    query_spec: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> None:
    query_spec_id = retrieval_v1.family_first_region_query_spec_id_v2(query_spec)
    source_binding = receipt.get("source_binding")
    if (
        query_spec_id != _EXPECTED_REGION_QUERY_SPEC_ID
        or receipt.get("receipt_id") != _EXPECTED_REGION_RECEIPT_ID
        or type(source_binding) is not dict
        or source_binding.get("query_spec_id") != _EXPECTED_REGION_QUERY_SPEC_ID
        or not same_typed_json_v1(
            source_binding.get("engine_ref"),
            _EXPECTED_REGION_IMPLEMENTATION_REFS[
                "src/bctc_ai/evaluation/family_first_region_retrieval_v1.py"
            ],
        )
        or any(
            not same_typed_json_v1(implementation_refs.get(path), reference)
            for path, reference in _EXPECTED_REGION_IMPLEMENTATION_REFS.items()
        )
        or not same_typed_json_v1(
            query_spec.get("semantic_assignment_adapter_ref"),
            _EXPECTED_REGION_IMPLEMENTATION_REFS[
                "src/bctc_ai/evaluation/loan_geography_scoped_table_adapter_v1.py"
            ],
        )
    ):
        raise _error("loan-geography frozen retrieval/query/implementation contract drifted")


def _validate_inputs(value: Any) -> dict[str, Any]:
    fields = {
        "bounded_schema_projection",
        "document_evidence_store",
        "implementation_refs",
        "region_query_spec",
        "region_retrieval_receipt",
        "schema_source_refs",
        "tracked_git_head",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("loan-geography formal input fields drifted")
    schema = schema_v1.validate_loan_geography_bounded_schema_projection_v1(
        value["bounded_schema_projection"]
    )
    store = value["document_evidence_store"]
    receipt = _region_receipt_binding(value["region_retrieval_receipt"])
    query = retrieval_v1.validate_family_first_region_query_spec_v2(value["region_query_spec"])
    implementation_refs = value["implementation_refs"]
    schema_refs = value["schema_source_refs"]
    receipt_metrics = receipt.get("metrics") if type(receipt) is dict else None
    expected_implementation_paths = {item.as_posix() for item in _IMPLEMENTATION_PATHS}
    expected_schema_paths = {item.as_posix() for item in _SCHEMA_SOURCE_PATHS}
    if (
        type(store) is not dict
        or store.get("metrics")
        != {"document_count": 140, "line_count": 667_224, "page_count": 8_947}
        or type(receipt) is not dict
        or receipt.get("receipt_id") is None
        or receipt.get("family_id") != query["family_id"]
        or receipt.get("query_spec_id") != retrieval_v1.family_first_region_query_spec_id_v2(query)
        or type(receipt.get("documents")) is not list
        or len(receipt["documents"]) != _TARGET_DOCUMENT_COUNT
        or type(receipt_metrics) is not dict
        or receipt_metrics.get("document_count") != 140
        or receipt_metrics.get("source_line_count") != 667_224
        or receipt_metrics.get("source_page_count") != 8_947
        or receipt_metrics.get("fallback_document_count") != _TARGET_FULL_FALLBACK_DOCUMENT_COUNT
        or receipt_metrics.get("selected_page_count") != _TARGET_SPARSE_HYDRATED_PAGE_COUNT
        or receipt_metrics.get("selected_page_count")
        != sum(item["selected_page_count"] for item in receipt["documents"])
        or sum(item["document_line_count"] for item in receipt["documents"]) != 667_224
        or sum(item["document_page_count"] for item in receipt["documents"]) != 8_947
        or receipt.get("source_binding", {}).get("query_spec_id") != receipt["query_spec_id"]
        or type(implementation_refs) is not dict
        or set(implementation_refs) != expected_implementation_paths
        or type(schema_refs) is not dict
        or set(schema_refs) != expected_schema_paths
        or type(value["tracked_git_head"]) is not str
        or len(value["tracked_git_head"]) not in {40, 64}
        or any(character not in "0123456789abcdef" for character in value["tracked_git_head"])
    ):
        raise _error("loan-geography formal source denominator/identity drifted")
    for path, reference in {**implementation_refs, **schema_refs}.items():
        if (
            type(reference) is not dict
            or set(reference) != {"path", "sha256", "size_bytes"}
            or reference["path"] != path
            or type(reference["sha256"]) is not str
            or len(reference["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in reference["sha256"])
            or type(reference["size_bytes"]) is not int
            or reference["size_bytes"] <= 0
        ):
            raise _error("loan-geography formal content reference drifted")
    _assert_frozen_region_retrieval_contract(
        implementation_refs=implementation_refs,
        query_spec=query,
        receipt=receipt,
    )
    adapter_path = "src/bctc_ai/evaluation/loan_geography_scoped_table_adapter_v1.py"
    if not same_typed_json_v1(
        query.get("semantic_assignment_adapter_ref"), implementation_refs[adapter_path]
    ):
        raise _error("loan-geography retrieval semantic assignment adapter drifted")
    outcomes = receipt["documents"]
    for ordinal, outcome in enumerate(outcomes, 1):
        if (
            type(outcome) is not dict
            or type(outcome.get("document_ordinal")) is not int
            or outcome["document_ordinal"] != ordinal
            or type(outcome.get("outcome_id")) is not str
            or not outcome["outcome_id"]
            or type(outcome.get("coverage_status")) is not str
            or outcome["coverage_status"] != "PROVEN_COMPLETE_FOR_DECLARED_SPEC"
        ):
            raise _error("loan-geography retrieval outcome coverage drifted")
    fallback_count = sum(item["requires_full_document_review"] for item in outcomes)
    indexed_count = len(outcomes) - fallback_count
    if (
        fallback_count != _TARGET_FULL_FALLBACK_DOCUMENT_COUNT
        or indexed_count != _TARGET_INDEXED_RETRIEVAL_DOCUMENT_COUNT
    ):
        raise _error("loan-geography retrieval indexed/fallback denominator drifted")
    return {
        **canonical_clone_v1(value),
        "bounded_schema_projection": schema,
        "region_query_spec": query,
        "region_retrieval_receipt": receipt,
    }


def _terminal_material(trials: Any, inputs: Any) -> dict[str, Any]:
    """Recompute every fixed-denominator terminal claim from typed trial evidence."""

    typed_inputs = _validate_inputs(inputs)
    receipt = typed_inputs["region_retrieval_receipt"]
    receipt_id = receipt["receipt_id"]
    outcomes = receipt["documents"]
    if type(trials) is not list or len(trials) != _TARGET_DOCUMENT_COUNT:
        raise _error("loan-geography terminal trial denominator drifted")
    typed_trials = [
        _validate_trial(
            trial,
            expected_ordinal=ordinal,
            receipt_id=receipt_id,
            outcome_id=outcomes[ordinal - 1]["outcome_id"],
            schema=typed_inputs["bounded_schema_projection"],
        )
        for ordinal, trial in enumerate(trials, 1)
    ]
    exact = [
        item for item in typed_trials if item["disposition"] == "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
    ]
    broad = [
        item for item in typed_trials if item["disposition"] == "BROAD_POPULATION_BOUNDED_ABSENCE"
    ]
    absent = [item for item in typed_trials if item["disposition"] == "NOT_OBSERVED"]
    unresolved = [item for item in typed_trials if item["disposition"] == "UNRESOLVED"]
    if (
        len(exact) != _TARGET_EXACT_COUNT
        or len(broad) != _TARGET_BROAD_COUNT
        or len(absent) != _TARGET_NOT_OBSERVED_COUNT
        or len(unresolved) != _TARGET_UNRESOLVED_COUNT
    ):
        raise _error("loan-geography exact/broad/not-observed terminal counts drifted")

    bank_documents = _counter(
        [_bank(item["document"]) for item in typed_trials],
        _TARGET_BANK_DOCUMENT_COUNTS,
        "bank document",
    )
    bank_exact = _counter(
        [_bank(item["document"]) for item in exact],
        _TARGET_BANK_EXACT_COUNTS,
        "bank exact",
    )
    bank_broad = _counter(
        [_bank(item["document"]) for item in broad],
        _TARGET_BANK_BROAD_COUNTS,
        "bank broad",
    )
    bank_absent = _counter(
        [_bank(item["document"]) for item in absent],
        _TARGET_BANK_NOT_OBSERVED_COUNTS,
        "bank not-observed",
    )

    mappings = [mapping for trial in exact for mapping in trial["mapped_children"]]
    bank_mapping_counts = _counter(
        [_bank(trial["document"]) for trial in exact for _mapping in trial["mapped_children"]],
        _TARGET_BANK_MAPPING_COUNTS,
        "bank mapping",
    )
    schema_counts = Counter(mapping["report_norm_id"] for mapping in mappings)
    if len(mappings) != _TARGET_MAPPING_COUNT or schema_counts != Counter({5752: 38, 765: 38}):
        raise _error("loan-geography mapped record/schema counts drifted")

    numeric_results = [trial["numeric_evidence"] for trial in exact]
    document_inherited_period_lane_count = sum(
        item.get("resolution_mode") == "DOCUMENT_INHERITED_EXACT_DATE"
        for result in numeric_results
        for item in result["period_axis"]
    )
    document_inherited_unit_trial_count = sum(
        item["unit_context"].get("resolution_mode") == "DOCUMENT_INHERITED_EXACT_UNIT"
        for item in numeric_results
    )
    period_lane_count = sum(len(item["period_axis"]) for item in numeric_results)
    mapped_cells = [
        cell for item in numeric_results for row in item["mapped_rows"] for cell in row["cells"]
    ]
    mapped_money_cell_count = len(mapped_cells)
    visible_dash_zero_count = sum(
        cell["selection_mode"] == "TYPED_VISIBLE_DASH_PIXEL_EVIDENCE_ZERO" for cell in mapped_cells
    )
    observed_numeric_mapped_cell_count = sum(
        cell["selection_mode"] != "TYPED_VISIBLE_DASH_PIXEL_EVIDENCE_ZERO"
        and type(cell["selected_value"]) is int
        for cell in mapped_cells
    )
    equation_count = sum(len(item["accounting_checks"]) for item in numeric_results)
    if any(
        check["status"] not in _ACCEPTED_EQUATION_STATUSES
        for item in numeric_results
        for check in item["accounting_checks"]
    ):
        raise _error("loan-geography observed accounting equation did not close")
    pp_viet_numeric_conflicts = sum(
        item["metrics"]["ppocrv6_vietocr_numeric_disagreement_count"] for item in numeric_results
    )
    accounting_backsolved_count = sum(
        item["metrics"]["accounting_backsolved_or_invented_value_count"] for item in numeric_results
    )
    numeric_gemma_authority_count = sum(
        item["metrics"]["gemma_numeric_authority_count"] for item in numeric_results
    )
    numeric_unresolved_observed_cell_count = sum(
        item["metrics"]["unresolved_observed_cell_count"] for item in numeric_results
    )
    numeric_vetoed_equation_count = sum(
        item["metrics"]["vetoed_equation_count"] for item in numeric_results
    )
    numeric_visible_dash_zero_count = sum(
        item["metrics"]["visible_dash_zero_cell_count"] for item in numeric_results
    )
    printed_control_money_cell_count = sum(
        item["metrics"]["source_control_money_cell_count"] for item in numeric_results
    )
    total_control_source_modes: list[str] = []
    for item in numeric_results:
        printed_total = item.get("printed_customer_loan_total")
        control_evidence = (
            printed_total.get("control_evidence") if type(printed_total) is dict else None
        )
        if (
            type(control_evidence) is not list
            or len(control_evidence) != len(item["period_axis"])
            or any(
                type(evidence) is not dict
                or evidence.get("lane_index") != lane
                or type(evidence.get("resolution_mode")) is not str
                for lane, evidence in enumerate(control_evidence)
            )
        ):
            raise _error("loan-geography printed-total source-mode axis drifted")
        total_control_source_modes.extend(
            evidence["resolution_mode"] for evidence in control_evidence
        )
    total_control_source_mode_counts = _counter(
        total_control_source_modes,
        _TARGET_TOTAL_CONTROL_SOURCE_MODE_COUNTS,
        "printed-total source mode",
    )
    total_control_request_sets = [
        trial["customer_loan_total_control_request_set"] for trial in exact
    ]
    upstream_total_controls = [
        control for trial in exact for control in trial["customer_loan_total_controls"]
    ]
    upstream_total_control_document_count = sum(
        bool(trial["customer_loan_total_controls"]) for trial in exact
    )
    upstream_total_control_request_count = sum(
        lane.get("classification") == "STRUCTURALLY_ABSENT"
        and type(lane.get("control_request_id")) is str
        for request_set in total_control_request_sets
        for lane in request_set["lane_requests"]
    )
    if (
        len(total_control_request_sets) != _TARGET_EXACT_COUNT
        or len(upstream_total_controls) != _TARGET_UPSTREAM_TOTAL_CONTROL_COUNT
        or upstream_total_control_document_count != _TARGET_UPSTREAM_TOTAL_CONTROL_COUNT
        or upstream_total_control_request_count != _TARGET_UPSTREAM_TOTAL_CONTROL_COUNT
        or total_control_source_mode_counts["UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL"]
        != _TARGET_UPSTREAM_TOTAL_CONTROL_COUNT
    ):
        raise _error("loan-geography upstream total-control denominator drifted")
    if (
        period_lane_count != _TARGET_PERIOD_LANE_COUNT
        or mapped_money_cell_count != _TARGET_MAPPED_MONEY_CELL_COUNT
        or observed_numeric_mapped_cell_count != _TARGET_OBSERVED_NUMERIC_MAPPED_CELL_COUNT
        or visible_dash_zero_count != _TARGET_VISIBLE_DASH_ZERO_COUNT
        or equation_count != _TARGET_EQUATION_COUNT
        or pp_viet_numeric_conflicts != 0
        or accounting_backsolved_count != 0
        or numeric_gemma_authority_count != 0
        or numeric_unresolved_observed_cell_count != 0
        or numeric_vetoed_equation_count != 0
        or numeric_visible_dash_zero_count != _TARGET_VISIBLE_DASH_ZERO_COUNT
        or printed_control_money_cell_count != _TARGET_PERIOD_LANE_COUNT
    ):
        raise _error("loan-geography numeric/dash/equation denominators drifted")

    bank_dash_counts = _counter(
        [
            _bank(trial["document"])
            for trial in exact
            for row in trial["numeric_evidence"]["mapped_rows"]
            for cell in row["cells"]
            if cell["selection_mode"] == "TYPED_VISIBLE_DASH_PIXEL_EVIDENCE_ZERO"
        ],
        _TARGET_BANK_DASH_ZERO_COUNTS,
        "bank visible-dash zero",
    )
    presentation_counts = Counter(item["presentation_mode"] for item in exact)
    row_layout_count = presentation_counts["SINGLE_PAGE_GEOGRAPHY_ROWS_ACCOUNTING_COLUMNS"]
    column_layout_count = (
        presentation_counts["SINGLE_PAGE_GEOGRAPHY_COLUMNS_ACCOUNTING_ROWS"]
        + presentation_counts["REPEATED_FULL_SEGMENT_ONE_PERIOD_PER_PAGE"]
    )
    repeated_count = presentation_counts["REPEATED_FULL_SEGMENT_ONE_PERIOD_PER_PAGE"]
    continuation_modes = []
    for item in exact:
        regions = item["sparse_graph"]["region_fingerprint"].get("regions")
        if type(regions) is not list or len(regions) != 1:
            raise _error("loan-geography exact continuation region count drifted")
        continuation = regions[0].get("continuation") if type(regions[0]) is dict else None
        mode = continuation.get("mode") if type(continuation) is dict else None
        if type(mode) is not str:
            raise _error("loan-geography exact continuation mode drifted")
        continuation_modes.append(mode)
    continuation_mode_counts = _counter(
        continuation_modes,
        _TARGET_CONTINUATION_MODE_COUNTS,
        "exact continuation mode",
    )
    partial_count = sum(
        bool(item["structural_equivalence"]["sparse_region_fingerprint"].get("partial"))
        for item in typed_trials
        if type(item["structural_equivalence"]["sparse_region_fingerprint"]) is dict
    )
    multiple_count = sum(
        item["sparse_graph"]["uniqueness"]["multiple_identical_region_count"]
        for item in typed_trials
    )
    partial_graph_count = sum(
        item["sparse_graph"]["uniqueness"]["partial_nonterminal_graph_count"]
        for item in typed_trials
    )
    repeated_bank_counts = _counter(
        [
            _bank(item["document"])
            for item in exact
            if item["presentation_mode"] == "REPEATED_FULL_SEGMENT_ONE_PERIOD_PER_PAGE"
        ],
        {bank: 18 if bank == "VIB" else 0 for bank in _BANK_ORDER},
        "bank repeated-full segment",
    )
    if (
        row_layout_count != _TARGET_ROW_LAYOUT_COUNT
        or column_layout_count != _TARGET_COLUMN_LAYOUT_COUNT
        or repeated_count != _TARGET_REPEATED_FULL_SEGMENT_COUNT
        or repeated_count
        != continuation_mode_counts["ADJACENT_REPEATED_FULL_SEGMENTS_PERIOD_COMPLEMENT"]
        or partial_count != _TARGET_PARTIAL_CONTINUATION_COUNT
        or partial_graph_count != _TARGET_PARTIAL_CONTINUATION_COUNT
        or multiple_count != 0
    ):
        raise _error("loan-geography layout/continuation counts drifted")

    broad_scopes = Counter(
        scope for trial in broad for scope in trial["absence_evidence"]["population_scopes"]
    )
    if broad_scopes != Counter({"BROAD_MIXED_LOAN_POPULATION": 18, "BROAD_TOTAL_LOANS": 60}):
        raise _error("loan-geography broad/mixed bounded-absence counts drifted")

    whole_pages = sum(
        item["structural_equivalence"]["whole_document_page_count"] for item in typed_trials
    )
    whole_lines = sum(
        item["structural_equivalence"]["whole_document_line_count"] for item in typed_trials
    )
    sparse_pages = sum(item["region_coverage"]["selected_page_count"] for item in typed_trials)
    sparse_lines = sum(item["region_coverage"]["selected_line_count"] for item in typed_trials)
    if whole_pages != 8_947 or whole_lines != 667_224:
        raise _error("loan-geography direct whole-document oracle denominator drifted")
    if (
        sparse_pages != _TARGET_SPARSE_HYDRATED_PAGE_COUNT
        or sparse_lines != _TARGET_SPARSE_HYDRATED_LINE_COUNT
    ):
        raise _error("loan-geography sparse hydration denominator drifted")
    sparse_page_reduction_ppm = (whole_pages - sparse_pages) * 1_000_000 // whole_pages
    sparse_line_reduction_ppm = (whole_lines - sparse_lines) * 1_000_000 // whole_lines

    gemma_count = sum(len(item["gemma_challenger_refs"]) for item in typed_trials)
    if gemma_count != _TARGET_GEMMA_REQUEST_COUNT:
        raise _error("loan-geography Gemma request count drifted")

    metrics = {
        "absence_numeric_pixel_or_total_control_hydration_count": 0,
        "accounting_backsolved_or_invented_value_count": accounting_backsolved_count,
        "bank_broad_bounded_absence_counts": bank_broad,
        "bank_document_counts": bank_documents,
        "bank_exact_counts": bank_exact,
        "bank_mapped_record_counts": bank_mapping_counts,
        "bank_not_observed_counts": bank_absent,
        "bank_repeated_full_segment_counts": repeated_bank_counts,
        "bank_visible_dash_zero_counts": bank_dash_counts,
        "broad_bounded_absence_trial_count": len(broad),
        "broad_mixed_population_trial_count": broad_scopes["BROAD_MIXED_LOAN_POPULATION"],
        "broad_total_population_trial_count": broad_scopes["BROAD_TOTAL_LOANS"],
        "column_layout_trial_count": column_layout_count,
        "continuation_mode_trial_counts": continuation_mode_counts,
        "direct_whole_document_line_count": whole_lines,
        "direct_whole_document_page_count": whole_pages,
        "document_count": len(typed_trials),
        "document_inherited_period_lane_count": document_inherited_period_lane_count,
        "document_inherited_unit_trial_count": document_inherited_unit_trial_count,
        "document_pdf_internal_context_evidence_count": len(exact),
        "exact_accounting_equation_count": equation_count,
        "exact_customer_loan_geography_trial_count": len(exact),
        "gemma_request_count": gemma_count,
        "known_nested_domestic_mapping_count": 0,
        "mapped_money_cell_count": mapped_money_cell_count,
        "mapped_parent_716_or_759_record_count": 0,
        "mapped_record_count": len(mappings),
        "multiple_identical_region_count": multiple_count,
        "not_observed_trial_count": len(absent),
        "numeric_gemma_authority_count": numeric_gemma_authority_count,
        "numeric_unresolved_observed_cell_count": numeric_unresolved_observed_cell_count,
        "numeric_vetoed_equation_count": numeric_vetoed_equation_count,
        "observed_numeric_mapped_cell_count": observed_numeric_mapped_cell_count,
        "partial_continuation_trial_count": partial_count,
        "partial_nonterminal_graph_count": partial_graph_count,
        "ppocrv6_vietocr_numeric_disagreement_count": pp_viet_numeric_conflicts,
        "printed_customer_loan_total_control_cell_count": printed_control_money_cell_count,
        "customer_loan_total_control_public_replay_count": len(upstream_total_controls),
        "customer_loan_total_control_request_count": upstream_total_control_request_count,
        "customer_loan_total_control_request_set_count": len(total_control_request_sets),
        "local_upstream_total_control_conflict_count": 0,
        "printed_customer_loan_total_control_source_mode_counts": (
            total_control_source_mode_counts
        ),
        "region_retrieval_mapping_or_absence_authority_count": 0,
        "repeated_full_segment_trial_count": repeated_count,
        "row_layout_trial_count": row_layout_count,
        "schema_report_norm_id_record_counts": {
            "5752": schema_counts[5752],
            "765": schema_counts[765],
        },
        "sparse_hydrated_line_count": sparse_lines,
        "sparse_hydrated_page_count": sparse_pages,
        "sparse_line_reduction_ppm": sparse_line_reduction_ppm,
        "sparse_page_reduction_ppm": sparse_page_reduction_ppm,
        "sparse_to_whole_document_equivalence_count": len(typed_trials),
        "unresolved_trial_count": len(unresolved),
        "upstream_customer_loan_total_control_document_count": (
            upstream_total_control_document_count
        ),
        "upstream_customer_loan_total_control_lane_count": len(upstream_total_controls),
        "visible_dash_zero_cell_count": visible_dash_zero_count,
    }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "inputs": typed_inputs,
        "metrics": metrics,
        "state": "COMPLETE",
        "trials": typed_trials,
    }
    return {**material, "sweep_id": "lg140v1:sweep:" + canonical_json_sha256_v1(material)}


def validate_authenticated_family_first_loan_geography_140_filing_schema_sweep_v1(
    value: Any,
) -> dict[str, Any]:
    """Validate terminal semantics without treating persisted bytes as live authority."""

    fields = {
        "authority",
        "claim_boundary",
        "format_version",
        "inputs",
        "metrics",
        "state",
        "sweep_id",
        "trials",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("loan-geography sweep result fields drifted")
    rebuilt = _terminal_material(value["trials"], value["inputs"])
    if not same_typed_json_v1(value, rebuilt):
        raise _error("loan-geography sweep terminal semantics drifted")
    return rebuilt


def _strict_result(path: Path) -> dict[str, Any]:
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error("persisted loan-geography sweep is not one regular nofollow file")
        if stat.S_IMODE(before.st_mode) != 0o444 or before.st_nlink != 1:
            raise _error("persisted loan-geography sweep is not immutable 0444/link-count-one")
        payload = path.read_bytes()
        after = path.lstat()
        identity = lambda item: (  # noqa: E731
            item.st_dev,
            item.st_ino,
            item.st_mode,
            item.st_size,
            item.st_mtime_ns,
        )
        if identity(before) != identity(after) or len(payload) != before.st_size:
            raise _error("persisted loan-geography sweep changed during stable read")
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON token: {token}")
            ),
        )
    except FamilyFirstLoanGeography140FilingSchemaSweepV1Error:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error("persisted loan-geography sweep is not strict JSON") from exc
    if type(value) is not dict or payload != canonical_json_bytes_v1(value):
        raise _error("persisted loan-geography sweep is not canonical JSON with exactly one LF")
    return validate_authenticated_family_first_loan_geography_140_filing_schema_sweep_v1(value)


def _adapter_region_query_spec(root: Path) -> dict[str, Any]:
    constructor = getattr(graph_v1, "build_loan_geography_region_query_spec_v2", None)
    if not callable(constructor):
        raise _error("thin Family 11 adapter does not export its frozen retrieval query spec")
    query_spec = retrieval_v1.validate_family_first_region_query_spec_v2(constructor(root))
    if (
        retrieval_v1.family_first_region_query_spec_id_v2(query_spec)
        != _EXPECTED_REGION_QUERY_SPEC_ID
    ):
        raise _error("thin Family 11 adapter retrieval query ID drifted")
    return query_spec


def build_authenticated_family_first_loan_geography_140_filing_schema_sweep_v1(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    project_root: Path,
    *,
    sparse_batch_size: int = 16,
    sparse_jobs: int = _DEFAULT_SPARSE_JOBS,
    direct_full_batch_size: int = _DEFAULT_DIRECT_FULL_BATCH_SIZE,
    direct_full_jobs: int = _DEFAULT_DIRECT_FULL_JOBS,
    _timing_sink: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Build the fixed Family 11 seal from live authenticated evidence."""

    if not isinstance(project_root, Path):
        raise _error("loan-geography sweep project root must be one pathlib Path")
    if (
        type(sparse_batch_size) is not int
        or sparse_batch_size <= 0
        or type(sparse_jobs) is not int
        or sparse_jobs <= 0
        or type(direct_full_batch_size) is not int
        or direct_full_batch_size <= 0
        or type(direct_full_jobs) is not int
        or direct_full_jobs <= 0
    ):
        raise _error("loan-geography graph batch sizes/jobs must be positive exact integers")
    if _timing_sink is not None and type(_timing_sink) is not dict:
        raise _error("loan-geography timing sink must be one private mutable dictionary")

    started = time.perf_counter()
    root = project_root.resolve()
    tracked_git_head = store_v1._clean_head(root)
    implementation_refs = _implementation_refs(root)
    schema_source_refs = _schema_source_refs(root)
    store_projection = store_v1.project_authenticated_family_first_document_evidence_store_v1(
        capability
    )
    if store_projection.get("metrics") != {
        "document_count": _TARGET_DOCUMENT_COUNT,
        "line_count": 667_224,
        "page_count": 8_947,
    }:
        raise _error("loan-geography sweep requires the fixed authenticated denominator")
    schema = schema_v1.build_live_loan_geography_bounded_schema_projection_v1(root)
    schema = schema_v1.validate_loan_geography_bounded_schema_projection_v1(schema)

    sparse_started = time.perf_counter()
    query_spec = _adapter_region_query_spec(root)
    adapter_path = "src/bctc_ai/evaluation/loan_geography_scoped_table_adapter_v1.py"
    if not same_typed_json_v1(
        query_spec["semantic_assignment_adapter_ref"],
        implementation_refs[adapter_path],
    ):
        raise _error("thin Family 11 adapter retrieval query did not bind its own bytes")
    receipt = retrieval_v1.retrieve_authenticated_family_first_regions_v2(
        capability,
        query_spec,
    )
    receipt = retrieval_v1.validate_replayed_authenticated_family_first_region_receipt_v2(
        capability,
        query_spec,
        receipt,
    )
    _assert_frozen_region_retrieval_contract(
        implementation_refs=implementation_refs,
        query_spec=query_spec,
        receipt=receipt,
    )
    prepared_receipt = graph_v1._prepare_loan_geography_receipt_v1(receipt)  # noqa: SLF001
    sparse_documents, packets, coverages = _sparse_graph_path(
        capability,
        receipt,
        batch_size=sparse_batch_size,
        jobs=sparse_jobs,
        prepared_receipt=prepared_receipt,
    )
    sparse_finished = time.perf_counter()

    direct_started = time.perf_counter()
    (
        equivalences,
        document_contexts,
        total_control_request_sets,
        total_control_sets,
        preprojected_numeric_inputs,
    ) = _whole_document_equivalences(
        capability,
        receipt,
        sparse_documents,
        packets,
        batch_size=direct_full_batch_size,
        jobs=direct_full_jobs,
        prepared_receipt=prepared_receipt,
    )
    direct_finished = time.perf_counter()

    trials = [
        _trial_from_graph(
            capability,
            document,
            packet,
            document_context,
            total_control_requests,
            total_controls,
            preprojected_numeric_input,
            coverage,
            equivalence,
            receipt["receipt_id"],
            schema,
        )
        for (
            document,
            packet,
            coverage,
            equivalence,
            document_context,
            total_control_requests,
            total_controls,
            preprojected_numeric_input,
        ) in zip(
            sparse_documents,
            packets,
            coverages,
            equivalences,
            document_contexts,
            total_control_request_sets,
            total_control_sets,
            preprojected_numeric_inputs,
            strict=True,
        )
    ]
    exact_evidence_finished = time.perf_counter()

    final_store_projection = store_v1.project_authenticated_family_first_document_evidence_store_v1(
        capability
    )
    if not same_typed_json_v1(store_projection, final_store_projection):
        raise _error("authenticated document evidence store changed during Family 11 build")
    _assert_build_inputs_unchanged(
        root,
        implementation_refs=implementation_refs,
        schema_source_refs=schema_source_refs,
        tracked_git_head=tracked_git_head,
    )
    inputs = {
        "bounded_schema_projection": schema,
        "document_evidence_store": store_projection,
        "implementation_refs": implementation_refs,
        "region_query_spec": query_spec,
        "region_retrieval_receipt": _region_receipt_binding_from_receipt(receipt),
        "schema_source_refs": schema_source_refs,
        "tracked_git_head": tracked_git_head,
    }
    result = _terminal_material(trials, inputs)
    _assert_build_inputs_unchanged(
        root,
        implementation_refs=implementation_refs,
        schema_source_refs=schema_source_refs,
        tracked_git_head=tracked_git_head,
    )
    if not same_typed_json_v1(
        store_projection,
        store_v1.project_authenticated_family_first_document_evidence_store_v1(capability),
    ):
        raise _error("authenticated document evidence store changed after Family 11 result")
    completed = time.perf_counter()
    if _timing_sink is not None:
        _timing_sink.update(
            {
                "direct_full_oracle_seconds": direct_finished - direct_started,
                "exact_evidence_seconds": exact_evidence_finished - direct_finished,
                "setup_seconds": sparse_started - started,
                "sparse_path_seconds": sparse_finished - sparse_started,
                "terminal_and_postcondition_seconds": completed - exact_evidence_finished,
                "total_seconds": completed - started,
            }
        )
    return result


def validate_authenticated_family_first_loan_geography_140_filing_schema_sweep_replay_v1(
    value: Any,
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    project_root: Path,
    *,
    sparse_batch_size: int = 16,
    sparse_jobs: int = _DEFAULT_SPARSE_JOBS,
    direct_full_batch_size: int = _DEFAULT_DIRECT_FULL_BATCH_SIZE,
    direct_full_jobs: int = _DEFAULT_DIRECT_FULL_JOBS,
    _timing_sink: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Run both live sparse and direct-full paths and require byte-model equality."""

    persisted = validate_authenticated_family_first_loan_geography_140_filing_schema_sweep_v1(value)
    rebuilt = build_authenticated_family_first_loan_geography_140_filing_schema_sweep_v1(
        capability,
        project_root,
        sparse_batch_size=sparse_batch_size,
        sparse_jobs=sparse_jobs,
        direct_full_batch_size=direct_full_batch_size,
        direct_full_jobs=direct_full_jobs,
        _timing_sink=_timing_sink,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("persisted Family 11 sweep differs from live exact replay")
    return rebuilt


def run_family_first_loan_geography_140_filing_schema_sweep_v1(
    project_root: Path,
    *,
    command: str,
    sparse_batch_size: int = 16,
    sparse_jobs: int = _DEFAULT_SPARSE_JOBS,
    direct_full_batch_size: int = _DEFAULT_DIRECT_FULL_BATCH_SIZE,
    direct_full_jobs: int = _DEFAULT_DIRECT_FULL_JOBS,
) -> dict[str, Any]:
    if command not in {"build", "verify"}:
        raise _error("loan-geography sweep command drifted")
    root = project_root.resolve()
    output = root / OUTPUT_PATH
    if command == "build" and output.exists():
        raise _error("loan-geography sweep destination already exists")
    persisted = _strict_result(output) if command == "verify" else None
    capability = store_v1.authenticate_family_first_document_evidence_store_v1(root)
    timings: dict[str, float] = {}
    if command == "verify":
        if persisted is None:
            raise _error("verify command lacks one strict persisted Family 11 result")
        result = (
            validate_authenticated_family_first_loan_geography_140_filing_schema_sweep_replay_v1(
                persisted,
                capability,
                root,
                sparse_batch_size=sparse_batch_size,
                sparse_jobs=sparse_jobs,
                direct_full_batch_size=direct_full_batch_size,
                direct_full_jobs=direct_full_jobs,
                _timing_sink=timings,
            )
        )
    else:
        result = build_authenticated_family_first_loan_geography_140_filing_schema_sweep_v1(
            capability,
            root,
            sparse_batch_size=sparse_batch_size,
            sparse_jobs=sparse_jobs,
            direct_full_batch_size=direct_full_batch_size,
            direct_full_jobs=direct_full_jobs,
            _timing_sink=timings,
        )
        _write_exclusive(output, canonical_json_bytes_v1(result))
    return {
        "execution_telemetry": {key: round(value, 6) for key, value in sorted(timings.items())},
        "metrics": result["metrics"],
        "state": result["state"],
        "sweep_id": result["sweep_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--sparse-batch-size", type=int, default=16)
    parser.add_argument("--sparse-jobs", type=int, default=_DEFAULT_SPARSE_JOBS)
    parser.add_argument(
        "--direct-full-batch-size",
        type=int,
        default=_DEFAULT_DIRECT_FULL_BATCH_SIZE,
    )
    parser.add_argument("--direct-full-jobs", type=int, default=_DEFAULT_DIRECT_FULL_JOBS)
    arguments = parser.parse_args()
    result = run_family_first_loan_geography_140_filing_schema_sweep_v1(
        arguments.project_root,
        command=arguments.command,
        sparse_batch_size=arguments.sparse_batch_size,
        sparse_jobs=arguments.sparse_jobs,
        direct_full_batch_size=arguments.direct_full_batch_size,
        direct_full_jobs=arguments.direct_full_jobs,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
