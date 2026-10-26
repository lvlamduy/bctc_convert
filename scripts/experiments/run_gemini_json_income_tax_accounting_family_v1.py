#!/usr/bin/env python3
"""Database-first Family 39 diagnostics, independent replay and fresh persistence.

This runner does not invoke extraction providers or claim terminal/final PDF
acceptance. NOT_OBSERVED/UNRESOLVED and every source-only row remain visible.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/experiments")]

import f39_registered_section_caption_pdf_auth_v1 as section_caption_pdf_auth  # noqa: E402
import run_gemini_json_multitable_hierarchical_accounting_family_v1 as generic  # noqa: E402
from f39_registered_part_period_pdf_auth_v1 import (  # noqa: E402
    authenticate_registered_part_period_pdf_v1,
    recheck_registered_part_period_pdf_v1,
)

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (  # noqa: E402
    _PERIOD_INVENTORY_DEPENDENCY_PATHS,
    DEFAULT_PART_PERIOD_COMMON204_REGISTRY_PATH,
    DEFAULT_PART_PERIOD_CONTEXT_REGISTRY_PATH,
    DEFAULT_SECTION_CAPTION_AUTH_ENVELOPE_PATH,
    FAMILY_ID,
    _approved_registered_part_period_loader_v1,
    _checked_registered_part_period_catalog_v1,
    _load_registered_section_caption_auth_envelope_v1,
    _prepare_income_tax_evaluation_records_v1,
    _registered_part_period_source_view_v1,
    build_gemini_json_income_tax_region_query_receipt_v1,
    compile_gemini_json_income_tax_family_specs_v1,
    evaluate_gemini_json_income_tax_family_cluster_v1,
    income_tax_document_period_evaluation_scope_v1,
    recover_gemini_json_income_tax_query_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    _source_table,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (  # noqa: E402
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (  # noqa: E402
    ingest_gemini_accounting_family_sweep_v1,
    load_gemini_accounting_family_sweep_v1,
    record_gemini_accounting_family_export_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import (  # noqa: E402
    validate_current_document_manifest_selection_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    load_page_json_versions_v1 as load_page_json_versions_v1,  # Original API for diagnostic comparison only.
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    query_selected_multitable_hierarchical_family_regions_v1,
)
from bctc_ai.storage.gemini_income_tax_raw_money_census_v1 import (  # noqa: E402
    IncomeTaxOriginalCensusSourceV1,
    load_income_tax_original_document_census_v1,
    open_income_tax_original_census_source_v1,
)
from bctc_ai.storage.gemini_income_tax_source_page_loader_v1 import (  # noqa: E402
    load_income_tax_source_page_json_versions_v1,
)

SHARED_PINS = {
    "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py": "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2",
    "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py": "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5",
}
SPEC_PATHS = {
    name: ROOT / ("config/families/tm-income-tax-" + suffix + "-v1.json")
    for name, suffix in (
        ("topology", "topology"),
        ("evaluation", "evaluation"),
        ("schema", "schema-binding"),
        ("adapter", "adapter"),
        ("repair", "source-repair"),
    )
}
PAGE_SCOPE_PATH = ROOT / "data/registered/gemini_json_first_27bank_vietnamese_page_scope_v2.json"
PAGE_SCOPE_SHA = "72431fa5e6bd5679a0c9701296da9a5b037b34ec2734da50c9b6bbefacec16be"
PAGE_SCOPE_ID = "gjfvietnamesev2:c8df0220081d5bcef4b4b6051be971430a126591cfbffb40ae8662f8951e5906"
PREFIX_CONCLUSION = "VIETNAMESE_PREFIX_EXCLUDES_NON_VIETNAMESE_APPENDIX"
RENDER_BINDINGS_PATH = ROOT / "config/families/tm-income-tax-source-repair-render-bindings-v1.json"
RENDER_BINDINGS_SHA = "a714e256ad3b508fba5b331e27551433824b8db14d84ea9cade28a296b7cf249"
ORIGINAL_REPAIR_SPEC_SHA = "9aac4e448b82ee0078c007ca06a36f0e3f11c2b4f694266a1211929f16228ea4"
RENDER_PROFILES = {
    "DECLARED_MATRIX_2_RGB_PNG": (2, 2),
    "EXISTING_RENDERING_PDF_MATRIX_300_DPI_OVER_72_RGB_PNG": (300 / 72, 300 / 72),
}


class RunGeminiJsonIncomeTaxV1Error(RuntimeError):
    """An authenticated Family-39 diagnostic/replay/storage proof failed."""


def require(condition: Any, message: str) -> None:
    if not condition:
        raise RunGeminiJsonIncomeTaxV1Error(message)


def _write_income_tax_sweep_once_v1(path: Path, sweep: dict[str, Any]) -> None:
    """Publish our validated sweep in the store's exact two-LF representation.

    Never copy caller/DB bytes or replace an existing output. If publication
    fails, retain the exclusively created artifact for fail-closed inspection.
    """
    payload = canonical_json_bytes_v1(sweep) + b"\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as stream:
        require(stream.write(payload) == len(payload), "Income-tax sweep output write was incomplete")
        stream.flush()
        os.fsync(stream.fileno())


def _json(path: Path) -> dict[str, Any]:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key: " + str(path))
            result[key] = value
        return result

    value = json.loads(path.read_bytes(), object_pairs_hook=pairs)
    require(type(value) is dict, "One JSON object required: " + str(path))
    return value


def _safe_path(path: Path) -> Path:
    require(path.is_absolute() and ".." not in path.parts, "Explicit safe absolute path required")
    for part in (path, *path.parents):
        require(not part.is_symlink(), "Symlink authority/output path prohibited")
    return path


def _assert_shared_pins_v1() -> None:
    for path, digest in SHARED_PINS.items():
        require(generic._sha256(ROOT / path) == digest, "Frozen shared pin differs: " + path)


def _compile_specs_v1():
    specs = {name: _json(path) for name, path in SPEC_PATHS.items()}
    compiled = compile_gemini_json_income_tax_family_specs_v1(
        specs["topology"], specs["evaluation"], specs["schema"], specs["adapter"], specs["repair"]
    )
    return specs, compiled


def _page_scope_v1(path):
    _safe_path(path)
    require(generic._sha256(path) == PAGE_SCOPE_SHA, "Registered language scope bytes differ")
    scope = _json(path)
    require(
        scope["scope_id"] == PAGE_SCOPE_ID
        and scope["format_version"] == "GEMINI_JSON_FIRST_VIETNAMESE_PAGE_SCOPE_V2",
        "Registered language scope identity differs",
    )
    rows = {row["relative_path"]: row for row in scope["documents"]}
    require(len(rows) == len(scope["documents"]), "Duplicate language scope source")
    return rows


def _check_page_scope_v1(document, physical_count, scope_rows):
    """Keep source physical pages separate from the immutable selected prefix."""
    source = document["manifest"]["document"]
    selected = len(document["ids"])
    row = scope_rows.get(source["source_logical_name"])
    if row is not None:
        require(
            row["source_sha256"] == source["source_sha256"]
            and row["source_page_count"] == physical_count
            and row["included_last_physical_page"] == selected
            and row["review_conclusion"] in {PREFIX_CONCLUSION, "FULL_DOCUMENT_VIETNAMESE"},
            "Registered language scope source/count/conclusion differs",
        )
    if selected != physical_count:
        require(
            row is not None
            and row["review_conclusion"] == PREFIX_CONCLUSION
            and 0 < selected < physical_count,
            "Selected/physical page difference lacks exact prefix authorization",
        )
    return {
        "selected_page_count": selected,
        "source_physical_page_count": physical_count,
        "excluded_non_vietnamese_appendix_page_count": physical_count - selected,
        "language_prefix_authorization": row if selected != physical_count else None,
        "language_scope_id": PAGE_SCOPE_ID,
    }


@contextmanager
def _authenticated_source_v1(path: Path, reference: dict[str, Any]):
    """Read original bytes without copying a multi-GB store; detect any mutation."""
    _safe_path(path)
    generic._assert_no_sqlite_sidecars(path)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        identity = generic._file_identity(os.fstat(descriptor))

        def check():
            generic._assert_no_sqlite_sidecars(path)
            require(
                generic._file_identity(os.fstat(descriptor))
                == identity
                == generic._file_identity(os.stat(path, follow_symlinks=False))
                and os.fstat(descriptor).st_size == reference["size_bytes"]
                and generic._fd_sha256(descriptor) == reference["sha256"],
                "Source SQLite bytes/identity changed",
            )

        check()
        try:
            yield path
        finally:
            check()
    finally:
        os.close(descriptor)


def _documents_v1(index: dict[str, Any], root: Path):
    """Authenticate source, immutable manifest/selection and ordered frontier."""
    result, all_ids = [], []
    current_year = datetime.now(UTC).year
    for document in index["documents"]:
        logical = document["relative_path"]
        years = [int(p) for p in Path(logical).parts if p.isdigit() and len(p) == 4]
        require(
            len(years) == 1 and 2025 <= years[0] <= current_year,
            "2024/non-current source prohibited",
        )
        manifest_path = generic._content_ref(root, document["document_manifest_ref"])
        manifest = _json(manifest_path)
        selection = validate_current_document_manifest_selection_v1(
            _json(generic._content_ref(root, document["selection_ref"]))
        )
        material = {k: v for k, v in manifest.items() if k != "document_manifest_id"}
        source = {
            "source_logical_name": logical,
            "source_sha256": document["source_sha256"],
            "source_size_bytes": document["source_size_bytes"],
        }
        source_id = "gfpstorev1:document:" + canonical_json_sha256_v1(source)
        pages = manifest["pages"]
        require(
            manifest["document_manifest_id"]
            == document["document_manifest_id"]
            == "gfdmv1:manifest:" + canonical_json_sha256_v1(material)
            and same_typed_json_v1(manifest["document"], {**source, "document_id": source_id})
            and manifest["page_count"] == document["page_count"] == len(pages)
            and canonical_json_sha256_v1(pages) == document["page_json_frontier_sha256"],
            "Immutable source/manifest frontier differs",
        )
        require(
            selection["selection_id"] == document["selection_id"]
            and selection["document_manifest_id"] == manifest["document_manifest_id"]
            and generic._content_ref(manifest_path.parent.parent, selection["document_manifest_ref"])
            == manifest_path
            and selection["source_sha256"] == source["source_sha256"],
            "Selected manifest binding differs",
        )
        physical = [p["physical_page"] for p in pages]
        ids = [p["page_json_version_id"] for p in pages]
        require(
            physical == list(range(1, len(pages) + 1)) and len(set(ids)) == len(ids),
            "Selected page frontier is noncontiguous/duplicate",
        )
        result.append(
            {"index_document": document, "manifest": manifest, "selection": selection, "ids": ids}
        )
        all_ids.extend(ids)
    require(
        len(all_ids) == len(set(all_ids)) == index["summary"]["page_count"],
        "Selected corpus page denominator differs",
    )
    return result, all_ids


def _diagnostic_documents_v1(documents, *, document_limit=None, document_ordinals=None):
    require(document_limit is None or document_ordinals is None, "Choose only one diagnostic subset")
    if document_limit is not None:
        require(type(document_limit) is int and 0 < document_limit <= len(documents), "Invalid bounded document limit")
        ordinals = list(range(1, document_limit + 1))
    elif document_ordinals is not None:
        require(
            type(document_ordinals) is list and bool(document_ordinals)
            and all(type(value) is int and 1 <= value <= len(documents) for value in document_ordinals)
            and document_ordinals == sorted(set(document_ordinals)),
            "Diagnostic document ordinals must be unique, ascending and in the immutable index",
        )
        ordinals = document_ordinals
    else:
        return documents, None
    return [documents[ordinal - 1] for ordinal in ordinals], ordinals


def base_cluster_cache_key_v1(records, compiled, implementation_refs):
    """Complete ordered source/JSON/context/spec/implementation key; no filename routing."""
    return canonical_json_sha256_v1(
        {
            "records": records,
            "compiled_specs": compiled,
            "implementation_refs": list(implementation_refs),
            "family_id": FAMILY_ID,
            "cache_format": "F39_BASE_CLUSTER_CACHE_V1",
        }
    )


class BaseClusterCache:
    """Optional append-only content cache; never used by authoritative cold replay."""

    def __init__(self, path: Path | None):
        self.connection = None
        if path is not None:
            _safe_path(path)
            self.connection = sqlite3.connect(path)
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS f39_base_cluster_cache (cache_key TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL, content BLOB NOT NULL)"
            )
            self.connection.commit()

    def get_or_build(self, key, build):
        if self.connection is not None:
            row = self.connection.execute(
                "SELECT content_sha256,content FROM f39_base_cluster_cache WHERE cache_key=?",
                (key,),
            ).fetchone()
            if row is not None:
                require(
                    sha256(row[1]).hexdigest() == row[0], "Base-cluster cache content hash differs"
                )
                value = json.loads(row[1])
                require(
                    canonical_json_bytes_v1(value) == row[1], "Base-cluster cache is noncanonical"
                )
                return value, True
        value = build()
        if self.connection is not None:
            raw = canonical_json_bytes_v1(value)
            self.connection.execute(
                "INSERT INTO f39_base_cluster_cache VALUES (?,?,?)",
                (key, sha256(raw).hexdigest(), raw),
            )
            self.connection.commit()
        return value, False

    def close(self):
        if self.connection is not None:
            self.connection.close()


def _records_v1(document, loaded, ordinal):
    source = document["manifest"]["document"]
    source_material = {
        k: source[k] for k in ("source_logical_name", "source_sha256", "source_size_bytes")
    }
    document_id = "gfpstorev1:document:" + canonical_json_sha256_v1(source_material)
    require(source.get("document_id", document_id) == document_id, "Source document ID differs")
    axis_document = {
        "document_id": document_id,
        "document_ordinal": ordinal,
        "source_logical_name": source["source_logical_name"],
        "source_sha256": source["source_sha256"],
    }
    require(len(loaded) == len(document["ids"]), "Selected JSON rows omitted")
    records = []
    for selected_ordinal, (receipt, page) in enumerate(
        zip(loaded, document["manifest"]["pages"], strict=True), 1
    ):
        require(
            receipt["page_json_version_id"] == page["page_json_version_id"]
            and receipt["physical_page"] == page["physical_page"]
            and receipt["source_logical_name"] == source["source_logical_name"]
            and receipt["source_sha256"] == source["source_sha256"],
            "Selected JSON/source/physical page differs",
        )
        records.append(
            {
                **axis_document,
                "page_json_version_id": receipt["page_json_version_id"],
                "physical_page": receipt["physical_page"],
                "selected_page_ordinal": selected_ordinal,
                "page_json": receipt["page_json"],
            }
        )
    return axis_document, records


def _trial_v1(cluster, records, compiled):
    candidates, mappings, reasons, selected = [], [], [], None
    status = cluster["status"]
    if status == READY:
        regions = cluster["component_regions"]
        candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
            regions=regions,
            page_json_by_version={r["page_json_version_id"]: r["page_json"] for r in records},
            selected_page_axis=[{k: v for k, v in r.items() if k != "page_json"} for r in records],
            compiled_specs=compiled,
            query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
                regions, cluster=cluster
            ),
        )
        candidates = [candidate]
        status = candidate["status"]
        if status == READY:
            mappings, selected = candidate["mappings"], candidate["candidate_id"]
        else:
            reasons = candidate["reasons"]
    elif status == UNRESOLVED:
        reasons = cluster["reasons"]
    else:
        require(status == NOT_OBSERVED, "Unknown family query disposition")
    return {
        "document_ordinal": cluster["document_ordinal"],
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
        "candidate_count": len(candidates),
        "candidates": candidates,
        "mappings": mappings,
        "reasons": reasons,
        "selected_candidate_id": selected,
        "status": status,
    }


def _evaluate_stream_v1(
    database, documents, compiled, *, cache=None, implementation_refs=(), independent_base=None,
    original_census_source=None, raw_census_sink=None, original_document_callback=None,
    original_document_records_callback=None,
):
    # Legacy internal fixture/replay calls may supply neither capability. They
    # make no authenticated raw-denominator claim. The official run always
    # supplies the owned source context and a per-document sink together.
    require((original_census_source is None) == (raw_census_sink is None),
            "Original census source and sink must be supplied together")
    require(raw_census_sink is None or callable(raw_census_sink), "Raw census sink must be callable")
    require(original_census_source is None or type(original_census_source) is IncomeTaxOriginalCensusSourceV1,
            "An owned authenticated original census source is required")
    require(original_document_callback is None or original_census_source is not None
            and callable(original_document_callback), "Original document callback requires an authenticated source")
    require(original_document_records_callback is None or original_census_source is not None
            and callable(original_document_records_callback), "Original records callback requires an authenticated source")
    require(original_document_callback is None or original_document_records_callback is None,
            "Original two- and three-argument callbacks are mutually exclusive")
    source_documents = None if original_census_source is None else original_census_source.document_authorities
    source_positions = {} if source_documents is None else {
        item["manifest"]["document_manifest_id"]: (ordinal, item)
        for ordinal, item in enumerate(source_documents, 1)
    }
    doc_axis, page_axis, clusters, trials, source_replay_receipts = [], [], [], [], []
    timing = {
        "selected_json_load_seconds": 0.0,
        "base_cluster_seconds": 0.0,
        "family_evaluation_seconds": 0.0,
        "selected_json_sql_rows": 0,
        "selected_json_sql_payload_bytes": 0,
        "selected_json_api_calls": 0,
        "base_cache_hits": 0,
        "peak_document_selected_pages": 0,
        "sql_total_statements_claimed": False,
        "document_period_inventory_cache": {
            "requests": 0, "hits": 0, "builds": 0, "disabled_requests": 0,
            "key_seconds": 0.0, "build_seconds": 0.0, "clone_seconds": 0.0,
            "dependency_checks": 0, "dependency_check_seconds": 0.0,
            "peak_entries": 0, "peak_stored_bytes": 0,
        },
    }
    bases = (
        None
        if independent_base is None
        else {
            d["document_ordinal"]: d["cluster"] for d in independent_base["candidate_dispositions"]
        }
    )
    for ordinal, document in enumerate(documents, 1):
        started = time.perf_counter()
        census = None
        if original_census_source is None:
            loaded = load_income_tax_source_page_json_versions_v1(
                database, page_json_version_ids=document["ids"]
            )
            axis, records = _records_v1(document, loaded, ordinal)
        else:
            selected = source_positions.get(document["manifest"]["document_manifest_id"])
            require(selected is not None and same_typed_json_v1(document, selected[1]),
                    "Stream document differs from authenticated original corpus authority")
            bundle = load_income_tax_original_document_census_v1(
                original_census_source, corpus_document_ordinal=selected[0], run_document_ordinal=ordinal,
            )
            loaded, axis, records, census = (bundle[key] for key in ("loaded", "axis_document", "records", "census"))
        original_hashes = tuple(canonical_json_sha256_v1(value) for value in (document, loaded, records, census))
        if census is not None:
            raw_census_sink(census)
            if original_document_callback is not None:
                original_document_callback(document, loaded)
            if original_document_records_callback is not None:
                original_document_records_callback(document, loaded, records)
            require(original_hashes == tuple(canonical_json_sha256_v1(value) for value in (document, loaded, records, census)),
                    "Original source/census changed in a document callback")
        source_replay_receipts.extend(r["source_json_replay_receipt"] for r in loaded)
        timing["selected_json_load_seconds"] += time.perf_counter() - started
        timing["selected_json_api_calls"] += 1
        timing["selected_json_sql_rows"] += len(loaded)
        timing["selected_json_sql_payload_bytes"] += sum(
            len(canonical_json_bytes_v1(r["page_json"])) + 1 for r in loaded
        )
        timing["peak_document_selected_pages"] = max(
            timing["peak_document_selected_pages"], len(records)
        )
        doc_axis.append(axis)
        page_axis.extend({k: v for k, v in r.items() if k != "page_json"} for r in records)
        started = time.perf_counter()
        if bases is not None:
            base_cluster, hit = bases[ordinal], False
        else:

            def build(records=records):
                return coalesce_gemini_json_multitable_hierarchical_document_v1(
                    page_records=records, compiled_specs=compiled
                )

            if cache is None:
                base_cluster, hit = build(), False
            else:
                key = base_cluster_cache_key_v1(records, compiled, implementation_refs)
                base_cluster, hit = cache.get_or_build(key, build)
        timing["base_cache_hits"] += int(hit)
        timing["base_cluster_seconds"] += time.perf_counter() - started
        started = time.perf_counter()
        with income_tax_document_period_evaluation_scope_v1(enabled=independent_base is None) as period_metrics:
            cluster = recover_gemini_json_income_tax_query_cluster_v1(
                page_records=records, base_cluster=base_cluster, compiled_specs=compiled
            )
            clusters.append(cluster)
            trials.append(_trial_v1(cluster, records, compiled))
        require(original_hashes == tuple(canonical_json_sha256_v1(value) for value in (document, loaded, records, census)),
                "Family evaluation changed original source/census objects")
        for key, value in period_metrics.items():
            if key.startswith("peak_"):
                timing["document_period_inventory_cache"][key] = max(timing["document_period_inventory_cache"][key], value)
            else:
                timing["document_period_inventory_cache"][key] += value
        timing["family_evaluation_seconds"] += time.perf_counter() - started
    indexed = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=doc_axis,
        selected_page_axis=page_axis,
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed, compiled_specs=compiled
    )
    validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1(
        trials=trials, indexed_query_evidence=indexed, compiled_specs=compiled
    )
    timing["source_json_replay_receipt_axis_sha256"] = canonical_json_sha256_v1(source_replay_receipts)
    timing["exact_original_source_json_replay_page_count"] = sum(
        r["classification"] == "EXACT_REPLAY" for r in source_replay_receipts
    )
    timing["lossless_original_source_json_replay_receipts"] = [
        r for r in source_replay_receipts if r["classification"] != "EXACT_REPLAY"
    ]
    return indexed, trials, timing


def replay_income_tax_trials_from_source_v1(
    *, source_page_database, selected_page_json_version_ids, compiled_specs, indexed_query_evidence,
    replay_metrics=None,
):
    """Independent storage query, fresh per-document JSON, no cache access."""
    require(replay_metrics is None or type(replay_metrics) is dict and not replay_metrics,
            "Cold replay metrics sink must be a fresh empty object")
    specs, family_compiled = _compile_specs_v1()
    require(
        same_typed_json_v1(
            compiled_specs,
            compile_gemini_json_flat_family_specs_v1(
                specs["topology"], specs["evaluation"], specs["schema"]
            ),
        ),
        "Cold replay declarative specs differ",
    )
    base = query_selected_multitable_hierarchical_family_regions_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
    )
    # This legacy compatibility replay has no owned original/PDF admission.
    # It must not become a storage bypass for an actually registered caption.
    envelope, _reference = _load_registered_section_caption_auth_envelope_v1()
    require(not any(document["document_id"] == source["document_id"]
                    or document["source_logical_name"] == source["pdf_source"]["logical_name"]
                    or document["source_sha256"] == source["pdf_source"]["sha256"]
                    for document in base["selected_document_axis"]
                    for source in envelope["clone_registry"]["sources"]),
            "Registered caption source requires the owned original-source replay adapter")
    documents = []
    for document in base["selected_document_axis"]:
        pages = [
            p
            for p in base["selected_page_axis"]
            if p["document_ordinal"] == document["document_ordinal"]
        ]
        source = {k: document[k] for k in ("source_logical_name", "source_sha256")}
        # Document IDs are authenticated by the independent storage query. Size
        # is recovered from its exact stored identity, not guessed from content.
        with sqlite3.connect(f"file:{source_page_database}?mode=ro", uri=True) as connection:
            row = connection.execute(
                "SELECT source_size_bytes FROM document WHERE document_id=?",
                (document["document_id"],),
            ).fetchone()
        require(row is not None, "Cold replay source document absent")
        source["source_size_bytes"] = row[0]
        documents.append(
            {
                "manifest": {"document": source, "pages": pages},
                "ids": [p["page_json_version_id"] for p in pages],
            }
        )
    indexed, trials, _timing = _evaluate_stream_v1(
        source_page_database, documents, family_compiled, independent_base=base
    )
    require(
        same_typed_json_v1(indexed, indexed_query_evidence),
        "Cold replay indexed source query differs",
    )
    if replay_metrics is not None:
        replay_metrics.update(json.loads(canonical_json_bytes_v1(_timing)))
    return trials


def _write_raw_census_document_v1(output_dir, census):
    """Write a provisional original denominator once, never an acceptance result."""
    output_dir = _safe_path(Path(output_dir))
    require(output_dir.is_dir(), "Existing fresh run output directory required")
    binding = census["source_binding"]
    run_ordinal, source_ordinal = binding["run_document_ordinal"], binding["corpus_document_ordinal"]
    require(all(type(value) is int and value > 0 for value in (run_ordinal, source_ordinal)),
            "Raw census source/run ordinals invalid")
    directory = _safe_path(output_dir / "raw-census")
    directory.mkdir(mode=0o700, exist_ok=True)
    path = directory / f"document-{run_ordinal:04d}-source-{source_ordinal:04d}.json"
    require(not path.exists(), "Raw census output already exists")
    with path.open("xb") as stream:
        stream.write(canonical_json_bytes_v1(census))
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = {
        "document_ordinal": run_ordinal, "corpus_document_ordinal": source_ordinal,
        "census_id": census["census_id"], "counts": json.loads(canonical_json_bytes_v1(census["counts"])),
        "census_ref": generic._file_ref(path),
    }
    _read_raw_census_ref_v1(descriptor)
    return descriptor


def _read_raw_census_ref_v1(descriptor):
    """Check retained bytes only; hashes and self-IDs are not source approval."""
    require(type(descriptor) is dict and set(descriptor) == {
        "document_ordinal", "corpus_document_ordinal", "census_id", "counts", "census_ref",
    }, "Raw census descriptor fields differ")
    ref = descriptor["census_ref"]
    require(type(ref) is dict and set(ref) == {"path", "sha256", "size_bytes"}
            and type(ref["path"]) is str and type(ref["sha256"]) is str and len(ref["sha256"]) == 64
            and all(character in "0123456789abcdef" for character in ref["sha256"])
            and type(ref["size_bytes"]) is int and ref["size_bytes"] > 0, "Raw census file ref differs")
    path = _safe_path(Path(ref["path"]))
    require(path.is_file() and path.resolve(strict=True) == path and path.suffix == ".json"
            and path.parent.name == "raw-census", "Canonical raw-census JSON file required")
    raw = path.read_bytes()
    require(len(raw) == ref["size_bytes"] and sha256(raw).hexdigest() == ref["sha256"],
            "Raw census artifact bytes differ")
    census = _json(path)
    require(raw == canonical_json_bytes_v1(census), "Raw census artifact is not canonical")
    material = {key: value for key, value in census.items() if key != "census_id"}
    binding = census["source_binding"]
    require(census["format_version"] == "F39_AUTHENTICATED_ORIGINAL_RAW_MONEY_CELL_CENSUS_V1"
            and census["census_id"] == descriptor["census_id"]
            == "f39rawcellv1:census:" + canonical_json_sha256_v1(material)
            and type(descriptor["document_ordinal"]) is int and descriptor["document_ordinal"] > 0
            and type(descriptor["corpus_document_ordinal"]) is int and descriptor["corpus_document_ordinal"] > 0
            and binding["run_document_ordinal"] == descriptor["document_ordinal"]
            and binding["corpus_document_ordinal"] == descriptor["corpus_document_ordinal"]
            and same_typed_json_v1(census["counts"], descriptor["counts"])
            and census["relevance"] == "UNASSESSED_NO_FAMILY_OWNER_ROLE_LANE_OR_ACCEPTANCE_DECISION"
            and census["family_acceptance_claimed"] is False and census["dispositions_classified"] is False
            and census["source_values_modified"] is False and census["pdf_bytes_or_visuals_verified"] is False,
            "Raw census retention identity/boundary differs")
    return raw, census


def _raw_census_summary_v1(census_refs):
    require(type(census_refs) is list and bool(census_refs), "One raw census per selected document required")
    require([item["document_ordinal"] for item in census_refs] == list(range(1, len(census_refs) + 1))
            and len({item["corpus_document_ordinal"] for item in census_refs}) == len(census_refs)
            and len({item["census_ref"]["path"] for item in census_refs}) == len(census_refs),
            "Raw census document/file axis duplicated or incomplete")
    counts = {}
    for item in census_refs:
        _raw, census = _read_raw_census_ref_v1(item)
        for key, value in census["counts"].items():
            require(type(value) is int and value >= 0, "Invalid raw census denominator count")
            counts[key] = counts.get(key, 0) + value
    return {
        "format_version": "F39_ORIGINAL_RAW_MONEY_DENOMINATOR_SUMMARY_V1",
        "status": "PASS_RETAINED_RAW_CENSUS_BYTES_NOT_SOURCE_AUTHENTICATION_OR_ACCEPTANCE",
        "document_count": len(census_refs), "counts": counts,
        "document_census_refs": json.loads(canonical_json_bytes_v1(census_refs)),
        "relevance": "UNASSESSED_NO_FAMILY_OWNER_ROLE_LANE_OR_ACCEPTANCE_DECISION",
        "all_raw_family_coverage_acceptance_claimed": False, "family_acceptance_claimed": False,
        "dispositions_classified": False, "raw_cells_normalized_or_repaired": False,
    }


def _authenticate_registered_part_catalog_pdf_v1(document, loaded, original_records, compiled, source_pdf_root):
    """Select from actual original bundle; fresh PDF proof remains separate.

    Call only inside the owned original-source context. Neither this selection
    nor its private compiled view authenticates arbitrary caller objects/DB.
    """
    before = canonical_json_sha256_v1([document, loaded, original_records, compiled])
    require(type(original_records) is list and bool(original_records), "Actual original page records required")
    view = _registered_part_period_source_view_v1(original_records, compiled_specs=compiled)
    reference = view["registry_ref"]
    context_ids = list(dict.fromkeys(item["context_id"] for item in view["contexts"]))
    receipts = []
    if reference is not None:
        catalog = _checked_registered_part_period_catalog_v1(compiled)
        matches = [item for item in catalog if same_typed_json_v1(item["registry_ref"], reference)]
        require(len(matches) == 1, "Original part registry is not one unique approved catalog entry")
        # Compatibility-only private clone; global compiled remains byteequal.
        private_compiled = json.loads(canonical_json_bytes_v1(compiled))
        private_compiled["income_tax_part_period_registry"] = json.loads(canonical_json_bytes_v1(matches[0]["registry"]))
        private_compiled["income_tax_part_period_registry_ref"] = json.loads(canonical_json_bytes_v1(reference))
        receipts = authenticate_registered_part_period_pdf_v1(
            document, loaded, private_compiled, source_pdf_root,
            registry_loader=_approved_registered_part_period_loader_v1(reference),
        )
    require([item["context_id"] for item in receipts] == context_ids,
            "Fresh part PDF authentication omitted/added an original selected context")
    require(before == canonical_json_sha256_v1([document, loaded, original_records, compiled]),
            "Part catalog PDF authentication changed original source/global compiled inputs")
    return {"document_source": json.loads(canonical_json_bytes_v1(document["manifest"]["document"])),
            "runtime_document_ordinal": original_records[0]["document_ordinal"],
            "original_records_sha256": canonical_json_sha256_v1(original_records),
            "registry_ref": reference, "source_variant_selection": view["source_variant_selection"],
            "context_ids": context_ids, "receipts": receipts}


def _recheck_registered_part_catalog_pdf_v1(bundles, documents, compiled):
    """Late fixed-loader rechecks only; not caller-proof admission."""
    before = canonical_json_sha256_v1([bundles, documents, compiled])
    catalog = _checked_registered_part_period_catalog_v1(compiled)
    require(type(bundles) is list and len(bundles) == len(documents),
            "Part PDF original document-selection axis is incomplete")
    groups, seen = [[] for _ in catalog], set()
    for ordinal, (bundle, document) in enumerate(zip(bundles, documents, strict=True), 1):
        require(type(bundle) is dict and set(bundle) == {
            "document_source", "runtime_document_ordinal", "original_records_sha256", "registry_ref",
            "source_variant_selection", "context_ids", "receipts",
        } and same_typed_json_v1(bundle["document_source"], document["manifest"]["document"])
            and type(bundle["runtime_document_ordinal"]) is int and bundle["runtime_document_ordinal"] == ordinal,
            "Part PDF original source/run-document axis differs")
        require(type(bundle["original_records_sha256"]) is str and len(bundle["original_records_sha256"]) == 64,
                "Part PDF original record hash missing")
        require(type(bundle["context_ids"]) is list and type(bundle["receipts"]) is list
                and [item["context_id"] for item in bundle["receipts"]] == bundle["context_ids"],
                "Part PDF selected context receipt axis differs")
        reference = bundle["registry_ref"]
        if reference is None:
            require(bundle["context_ids"] == [] and bundle["source_variant_selection"] is None,
                    "Unrelated part document acquired a selected context")
            source = bundle["document_source"]
            require(not any(source.get("document_id") == context["document_id"]
                            or source["source_logical_name"] == context["pdf_source"]["logical_name"]
                            or source["source_sha256"] == context["pdf_source"]["sha256"]
                            for item in catalog for context in item["registry"]["contexts"]),
                    "Applicable part source has an empty authentication axis")
            continue
        positions = [position for position, item in enumerate(catalog)
                     if same_typed_json_v1(item["registry_ref"], reference)]
        require(len(positions) == 1, "Part PDF registry axis is not independently approved")
        position = positions[0]
        proof = bundle["source_variant_selection"]
        require(type(proof) is dict and same_typed_json_v1(proof.get("registry_ref"), reference)
                and proof.get("declared_span_selection", {}).get("status") == "EXACT_DECLARED_SOURCE_SPAN_SELECTION_NOT_APPROVAL"
                and proof["declared_span_selection"].get("selected_registry_position") == position
                and proof["declared_span_selection"].get("selected_context_ids") == bundle["context_ids"],
                "Part PDF original variant selection detached from approved registry")
        source = bundle["document_source"]
        expected = [context["context_id"] for context in catalog[position]["registry"]["contexts"]
                    if context["pdf_source"]["logical_name"] == source["source_logical_name"]
                    and context["pdf_source"]["sha256"] == source["source_sha256"]
                    and context["pdf_source"]["size_bytes"] == source["source_size_bytes"]]
        require(bundle["context_ids"] == expected and not seen.intersection(expected),
                "Part PDF selected original context axis is incomplete/duplicate")
        seen.update(expected)
        groups[position].extend(bundle["receipts"])
    # Both files independently fresh-read even when the group has no contexts.
    for item, receipts in zip(catalog, groups, strict=True):
        recheck_registered_part_period_pdf_v1(
            receipts, registry_loader=_approved_registered_part_period_loader_v1(item["registry_ref"]),
        )
    require(before == canonical_json_sha256_v1([bundles, documents, compiled]),
            "Part catalog authentication inputs changed during late callback")


def _authenticate_section_caption_admission_v1(document, loaded, original_records, compiled, source_pdf_root):
    """Fresh admission from the SAME owned ORIGINAL bundle used for PART.

    This internal helper is called only inside the actual original-source
    context. No receipt argument, cached approval, or caller boolean admits a
    correction. The returned metadata remains provisional until owner exit.
    """
    before = canonical_json_sha256_v1([document, loaded, original_records, compiled])
    expected_module = ROOT / "scripts/experiments/f39_registered_section_caption_pdf_auth_v1.py"
    require(Path(section_caption_pdf_auth.__file__).resolve() == expected_module
            and Path(section_caption_pdf_auth.__spec__.origin).resolve() == expected_module,
            "Caption authentication actual module origin differs")
    require(type(original_records) is list and bool(original_records), "Actual original caption record axis required")
    _axis, reconstructed = _records_v1(document, loaded, original_records[0]["document_ordinal"])
    require(same_typed_json_v1(reconstructed, original_records),
            "Caption admission differs from the actual original loaded bundle")
    _evaluation, _old13, projection = _prepare_income_tax_evaluation_records_v1(
        original_records, compiled_specs=compiled)
    # The fresh independently pinned projection identifies applicability, not a
    # caller approval flag. Unrelated documents retain an explicit EMPTY axis;
    # do not rehash every original page through the pixel helper unnecessarily.
    receipts = (section_caption_pdf_auth.authenticate_registered_section_caption_pdf_v1(
        document, loaded, compiled, source_pdf_root, original_records=original_records,
        registry_loader=_load_registered_section_caption_auth_envelope_v1,
    ) if projection["ordered_caption_repair_ids"] else [])
    original_sha = canonical_json_sha256_v1(original_records)
    # Official selected records are already in their authenticated physical/
    # selected order. Do not relabel an unordered caller digest as canonical.
    require(projection["original_records_object_canonical_sha256"] == original_sha,
            "Caption admission original raw/canonical record axes differ")
    require(before == canonical_json_sha256_v1([document, loaded, original_records, compiled]),
            "Caption admission changed original source/global compiled inputs")
    return {
        "document_source": json.loads(canonical_json_bytes_v1(document["manifest"]["document"])),
        "runtime_document_ordinal": original_records[0]["document_ordinal"],
        "original_records_sha256": original_sha,
        "projection_receipt": projection,
        "receipts": receipts,
    }


def _recheck_section_caption_admission_v1(bundles, documents, compiled, *, indexed_query_evidence):
    """Check a complete fresh internal axis against every indexed R/N/U.

    This is a late barrier, NOT admission of caller-created bundles. The only
    official producer above freshly reads original source and authenticates
    PDF/whole-page/crop evidence. All lower callbacks finish before the enclosing
    held-FD and post-code/authority/PDF/census checks.
    """
    before = canonical_json_sha256_v1([bundles, documents, compiled, indexed_query_evidence])
    envelope, reference = _load_registered_section_caption_auth_envelope_v1()
    require(same_typed_json_v1(compiled.get("income_tax_section_caption_auth_envelope"), envelope)
            and same_typed_json_v1(compiled.get("income_tax_section_caption_auth_envelope_ref"), reference),
            "Caption compiled approval differs from fresh fixed authority")
    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled)
    dispositions = evidence["candidate_dispositions"]
    require(type(bundles) is list and len(bundles) == len(documents) == len(dispositions),
            "Caption complete original document admission axis differs")
    expected_pages, seen = [], set()
    for ordinal, (bundle, document, disposition) in enumerate(zip(bundles, documents, dispositions, strict=True), 1):
        source = document["manifest"]["document"]
        identity = {key: source[key] for key in ("source_logical_name", "source_sha256", "source_size_bytes")}
        document_id = "gfpstorev1:document:" + canonical_json_sha256_v1(identity)
        require(source.get("document_id", document_id) == document_id and document_id not in seen,
                "Caption selected original document identity differs/duplicates")
        seen.add(document_id)
        axis = {"document_id": document_id, "document_ordinal": ordinal,
                "source_logical_name": source["source_logical_name"], "source_sha256": source["source_sha256"]}
        require(type(bundle) is dict and set(bundle) == {
            "document_source", "runtime_document_ordinal", "original_records_sha256", "projection_receipt", "receipts",
        } and same_typed_json_v1(bundle["document_source"], source)
            and type(bundle["runtime_document_ordinal"]) is int and bundle["runtime_document_ordinal"] == ordinal
            and same_typed_json_v1(evidence["selected_document_axis"][ordinal - 1], axis)
            and all(disposition[key] == value for key, value in axis.items()),
            "Caption admission selected source/run-document axis differs")
        pages = [{**axis, "page_json_version_id": page["page_json_version_id"],
                  "physical_page": page["physical_page"], "selected_page_ordinal": selected}
                 for selected, page in enumerate(document["manifest"]["pages"], 1)]
        require(document["ids"] == [page["page_json_version_id"] for page in pages],
                "Caption immutable selected page/VID axis differs")
        expected_pages.extend(pages)
        pdf = {"logical_name": source["source_logical_name"], "sha256": source["source_sha256"],
               "size_bytes": source["source_size_bytes"]}
        registered = []
        for candidate in envelope["clone_registry"]["sources"]:
            matches = (candidate["document_id"] == document_id,
                       candidate["pdf_source"]["logical_name"] == pdf["logical_name"],
                       candidate["pdf_source"]["sha256"] == pdf["sha256"])
            if any(matches):
                require(all(matches) and same_typed_json_v1(candidate["pdf_source"], pdf),
                        "Caption selected and registered PDF identity partially match")
                registered.append(candidate)
        require(len(registered) <= 1, "Caption source registration is ambiguous")
        expected_ids = [repair["repair_id"] for item in registered for repair in item["repairs"]]
        projection, receipts = bundle["projection_receipt"], bundle["receipts"]
        require(type(receipts) is list and all(type(item) is dict for item in receipts)
                and [item.get("repair_id") for item in receipts] == expected_ids,
                "Caption complete ordered repair axis missing/extra/reordered")
        require(type(projection) is dict
                and same_typed_json_v1(disposition["cluster"].get("income_tax_section_caption_projection_receipt"), projection)
                and same_typed_json_v1(projection.get("source_page_axis"), pages)
                and projection.get("envelope_ref") == reference
                and projection.get("ordered_caption_repair_ids") == expected_ids
                and projection.get("original_records_object_canonical_sha256") == bundle["original_records_sha256"]
                and projection.get("source_database_pdf_or_pixels_authenticated") is False
                and projection.get("permission_grants") == {
                    key: False for key in ("scope", "entity", "unit", "period", "source_value", "acceptance", "export")},
                "Caption full indexed projection detached from original admission")
        clones = projection.get("ordered_caption_clone_receipts")
        require(type(clones) is list and len(clones) == (1 if expected_ids else 0),
                "Caption empty/nonempty pure clone axis differs")
        for receipt in receipts:
            require(receipt.get("document_id") == document_id
                    and type(receipt.get("runtime_document_ordinal")) is int
                    and receipt["runtime_document_ordinal"] == ordinal
                    and same_typed_json_v1(receipt.get("pdf_source"), pdf)
                    and receipt.get("loaded_original_records_object_sha256") == bundle["original_records_sha256"]
                    and same_typed_json_v1(receipt.get("pure_clone_replay_receipt"), clones[0])
                    and clones[0]["evaluation_records_object_canonical_sha256"]
                    == projection["caption_stage_records_object_canonical_sha256"],
                    "Caption actual source/PDF pure clone differs from indexed original projection")
        # Per-document recheck preserves registered ordering even if a future
        # approved source catalog has a different source order. Empty axes are
        # explicit declarations, never borrowed warm approval tokens.
        section_caption_pdf_auth.recheck_registered_section_caption_pdf_v1(
            receipts, registry_loader=_load_registered_section_caption_auth_envelope_v1)
    require(same_typed_json_v1(evidence["selected_page_axis"], expected_pages),
            "Caption complete original selected page denominator differs")
    require(before == canonical_json_sha256_v1([bundles, documents, compiled, indexed_query_evidence]),
            "Caption admission inputs changed during late callbacks")


def _make_authenticated_source_replay_adapter_v1(
    *, database, database_ref, artifact_root, corpus_index_ref, documents, expected_census_refs,
    source_pdf_root=None, implementation_refs=(), authority_refs=(), expected_caption_admission_axis=None,
    expected_source_label_discrepancy_axis=None,
):
    """Bind an independent cold pass to original authority and warm raw bytes.

    The returned Python function is defined in this runner, satisfying the
    generic store's implementation-origin fence without changing shared code.
    No returned trial escapes the fresh source context's successful exit.
    """
    document_bytes = canonical_json_bytes_v1(documents)
    census_ref_bytes = canonical_json_bytes_v1(expected_census_refs)
    implementation_bytes = canonical_json_bytes_v1(list(implementation_refs))
    authority_bytes = canonical_json_bytes_v1(list(authority_refs))
    expected_caption_bytes = (None if expected_caption_admission_axis is None else
                              canonical_json_bytes_v1(expected_caption_admission_axis))
    expected_negative_bytes = (None if expected_source_label_discrepancy_axis is None else
                               canonical_json_bytes_v1(expected_source_label_discrepancy_axis))
    database_ref_bytes, index_ref_bytes = map(canonical_json_bytes_v1, (database_ref, corpus_index_ref))
    database, artifact_root = Path(database), Path(artifact_root)
    source_pdf_root = None if source_pdf_root is None else Path(source_pdf_root)

    def replay(*, source_page_database, selected_page_json_version_ids, compiled_specs, indexed_query_evidence):
        require(Path(source_page_database) == database, "Cold raw census source database path differs")
        expected_implementations = json.loads(implementation_bytes)
        expected_authorities = json.loads(authority_bytes)
        require(expected_implementations == [generic._file_ref(Path(ref["path"])) for ref in expected_implementations],
                "Cold replay implementation bytes changed before source open")
        require(expected_authorities == [generic._file_ref(Path(ref["path"])) for ref in expected_authorities],
                "Cold replay immutable authority bytes changed before source open")
        cold_documents, refs = json.loads(document_bytes), json.loads(census_ref_bytes)
        require(len(cold_documents) == len(refs)
                and list(selected_page_json_version_ids) == [item for document in cold_documents for item in document["ids"]],
                "Cold raw census selected document/page axis differs")
        if expected_caption_bytes is None:
            envelope, _reference = _load_registered_section_caption_auth_envelope_v1()
            require(not any(source.get("document_id") == registered["document_id"]
                            or source["source_logical_name"] == registered["pdf_source"]["logical_name"]
                            or source["source_sha256"] == registered["pdf_source"]["sha256"]
                            for document in cold_documents for source in [document["manifest"]["document"]]
                            for registered in envelope["clone_registry"]["sources"]),
                    "Applicable caption cold replay requires the complete warm admission axis")
        before = _raw_census_summary_v1(refs)
        specs, family_compiled = _compile_specs_v1()
        require(same_typed_json_v1(compiled_specs, compile_gemini_json_flat_family_specs_v1(
            specs["topology"], specs["evaluation"], specs["schema"],
        )), "Cold replay declarative specs differ")
        seen, part_pdf_receipts, part_pdf_bundles, caption_admissions, negative_admissions = [], [], [], [], []

        def authenticate_original(document, loaded, original_records):
            # Independent cold authentication, never a warm approval token.
            # A missing PDF root is permitted only for nonapplicable sources.
            negative_admissions.append(_authenticate_source_label_discrepancies_v1(
                document, original_records, source_pdf_root))
            bundle = _authenticate_registered_part_catalog_pdf_v1(
                document, loaded, original_records, family_compiled, source_pdf_root,
            )
            part_pdf_bundles.append(bundle)
            part_pdf_receipts.extend(bundle["receipts"])
            caption_admissions.append(_authenticate_section_caption_admission_v1(
                document, loaded, original_records, family_compiled, source_pdf_root))

        def compare(census):
            ordinal = census["source_binding"]["run_document_ordinal"]
            require(type(ordinal) is int and ordinal == len(seen) + 1 and ordinal <= len(refs),
                    "Cold raw census order/denominator differs")
            expected_raw, _expected = _read_raw_census_ref_v1(refs[ordinal - 1])
            require(canonical_json_bytes_v1(census) == expected_raw,
                    "Cold original raw MONEY census differs from warm source bytes")
            seen.append(refs[ordinal - 1]["census_id"])

        with open_income_tax_original_census_source_v1(
            database, database_ref=json.loads(database_ref_bytes), artifact_root=artifact_root,
            corpus_index_ref=json.loads(index_ref_bytes),
        ) as source:
            base = query_selected_multitable_hierarchical_family_regions_v1(
                database, selected_page_json_version_ids=selected_page_json_version_ids, compiled_specs=family_compiled,
            )
            indexed, trials, _timing = _evaluate_stream_v1(
                database, cold_documents, family_compiled, independent_base=base,
                original_census_source=source, raw_census_sink=compare,
                original_document_records_callback=authenticate_original,
            )
            require(same_typed_json_v1(indexed, indexed_query_evidence), "Cold replay indexed source query differs")
            require(len(seen) == len(refs), "Cold raw census omitted a document")
            require(same_typed_json_v1(_raw_census_summary_v1(refs), before), "Warm census files changed during cold replay")
            _recheck_registered_part_catalog_pdf_v1(part_pdf_bundles, cold_documents, family_compiled)
            _recheck_section_caption_admission_v1(
                caption_admissions, cold_documents, family_compiled, indexed_query_evidence=indexed)
            require(expected_caption_bytes is not None or not any(bundle["receipts"] for bundle in caption_admissions),
                    "Nonempty fresh caption authentication requires the complete warm admission axis")
            require(expected_caption_bytes is None or canonical_json_bytes_v1(caption_admissions) == expected_caption_bytes,
                    "Cold fresh caption admission axis differs from warm original authentication")
            require(expected_negative_bytes is not None or not any(negative_admissions),
                    "Applicable negative source observation requires the complete warm PDF admission axis")
            require(expected_negative_bytes is None or canonical_json_bytes_v1(negative_admissions) == expected_negative_bytes,
                    "Cold fresh negative-label pixel authentication differs from warm source evidence")
        require(same_typed_json_v1(_raw_census_summary_v1(refs), before), "Warm census files changed at cold source close")
        # The original owned context has exited successfully. Hold a fresh
        # readonly FD across every later callback; no trial reaches the store
        # until this barrier's final actual DB bytes/identity check succeeds.
        with _authenticated_source_v1(database, json.loads(database_ref_bytes)):
            _recheck_registered_part_catalog_pdf_v1(part_pdf_bundles, cold_documents, family_compiled)
            _recheck_section_caption_admission_v1(
                caption_admissions, cold_documents, family_compiled, indexed_query_evidence=indexed)
            require(expected_caption_bytes is None or canonical_json_bytes_v1(caption_admissions) == expected_caption_bytes,
                    "Cold caption admission axis changed during final callbacks")
            require(expected_implementations == [generic._file_ref(Path(ref["path"])) for ref in expected_implementations],
                    "Cold replay implementation bytes changed during final PDF callbacks")
            require(expected_authorities == [generic._file_ref(Path(ref["path"])) for ref in expected_authorities],
                    "Cold replay immutable authority bytes changed during final PDF callbacks")
            # Official runs always provide a PDF root. Legacy nonapplicable
            # fixture calls may omit it; that omission grants no PDF proof.
            # Check ALL selected PDFs, not only the registered PART subset.
            if source_pdf_root is not None:
                for document in cold_documents:
                    source = document["manifest"]["document"]
                    path = _safe_path(source_pdf_root / source["source_logical_name"])
                    require(path.is_file() and path.stat().st_size == source["source_size_bytes"]
                            and generic._sha256(path) == source["source_sha256"],
                            "Cold source PDF changed during final PDF callbacks: " + str(path))
            require(same_typed_json_v1(_raw_census_summary_v1(refs), before),
                    "Warm census files changed during final cold PDF callbacks")
            require(expected_negative_bytes is None or canonical_json_bytes_v1(negative_admissions) == expected_negative_bytes,
                    "Cold negative-label admission axis changed during final PDF callbacks")
        return trials

    return replay


def _store_raw_money_censuses_v1(results_database, *, family_run_id, census_refs):
    """Persist/reload exact raw denominators after authenticated cold replay.

    This family-local table adds no semantic acceptance or generic-store schema
    migration. A fresh insertion is mandatory; existing census rows are never
    replaced. Each BLOB is materialized/reloaded one document at a time.
    """
    summary = _raw_census_summary_v1(census_refs)
    with closing(sqlite3.connect(results_database)) as connection, connection:
        connection.execute("PRAGMA foreign_keys=ON")
        family = connection.execute("SELECT family_id FROM family_run WHERE family_run_id=?", (family_run_id,)).fetchone()
        require(family == (FAMILY_ID,), "Raw census store family run absent/different")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS f39_raw_money_census_v1 ("
            "family_run_id TEXT NOT NULL,document_ordinal INTEGER NOT NULL,corpus_document_ordinal INTEGER NOT NULL,"
            "census_id TEXT NOT NULL,census_sha256 TEXT NOT NULL,census_bytes BLOB NOT NULL,source_ref_json BLOB NOT NULL,"
            "PRIMARY KEY(family_run_id,document_ordinal),UNIQUE(family_run_id,corpus_document_ordinal),"
            "FOREIGN KEY(family_run_id,document_ordinal) REFERENCES family_trial(family_run_id,document_ordinal))"
        )
        require(connection.execute("SELECT COUNT(*) FROM f39_raw_money_census_v1 WHERE family_run_id=?", (family_run_id,)).fetchone() == (0,),
                "Raw census store already contains this family run")
        trial_count = connection.execute("SELECT COUNT(*) FROM family_trial WHERE family_run_id=?", (family_run_id,)).fetchone()[0]
        require(trial_count == len(census_refs), "Raw census store/trial denominator differs")
        for item in census_refs:
            raw, census = _read_raw_census_ref_v1(item)
            source = census["source_binding"]["document_source_axis"]
            trial = connection.execute(
                "SELECT source_logical_name,source_sha256 FROM family_trial WHERE family_run_id=? AND document_ordinal=?",
                (family_run_id, item["document_ordinal"]),
            ).fetchone()
            require(trial == (source["source_logical_name"], source["source_sha256"]), "Stored trial/raw census source identity differs")
            connection.execute("INSERT INTO f39_raw_money_census_v1 VALUES (?,?,?,?,?,?,?)", (
                family_run_id, item["document_ordinal"], item["corpus_document_ordinal"], item["census_id"],
                sha256(raw).hexdigest(), raw, canonical_json_bytes_v1(item["census_ref"]),
            ))
        require(same_typed_json_v1(summary, _raw_census_summary_v1(census_refs)),
                "Raw census files changed before persistence commit")
    # Reload from a separately opened read-only connection after commit/close,
    # not from the insertion transaction's own uncommitted view.
    with closing(sqlite3.connect(Path(results_database).as_uri() + "?mode=ro", uri=True)) as connection:
        connection.execute("PRAGMA query_only=ON")
        require(connection.execute("PRAGMA query_only").fetchone() == (1,), "Raw census reload is not query-only")
        require(connection.execute("SELECT COUNT(*) FROM f39_raw_money_census_v1 WHERE family_run_id=?", (family_run_id,)).fetchone()
                == (len(census_refs),), "Persisted raw census document denominator differs")
        for item in census_refs:
            raw, _census = _read_raw_census_ref_v1(item)
            row = connection.execute(
                "SELECT corpus_document_ordinal,census_id,census_sha256,census_bytes,source_ref_json "
                "FROM f39_raw_money_census_v1 WHERE family_run_id=? AND document_ordinal=?",
                (family_run_id, item["document_ordinal"]),
            ).fetchone()
            require(row == (item["corpus_document_ordinal"], item["census_id"], sha256(raw).hexdigest(), raw,
                            canonical_json_bytes_v1(item["census_ref"])), "Stored raw census BLOB does not reload exactly")
        require(connection.execute("PRAGMA quick_check").fetchall() == [("ok",)]
                and connection.execute("PRAGMA foreign_key_check").fetchall() == [], "Raw census results SQLite integrity failed")
    require(same_typed_json_v1(summary, _raw_census_summary_v1(census_refs)), "Raw census files changed during persistence")
    return {"table": "f39_raw_money_census_v1", "document_count": len(census_refs),
            "exact_per_document_blob_reload": True, "family_acceptance_claimed": False}


def _validate_repair_render_bindings_v1(value, compiled):
    """An additive metadata correction cannot replace any registered source evidence."""
    require(
        type(value) is dict
        and set(value) == {
            "format_version", "family_id", "classification", "base_git_commit",
            "original_source_repair_spec_sha256", "original_render_contract",
            "diagnostic_ref", "correction_scope", "family_terminal_claimed", "bindings",
        }
        and value["format_version"] == "INCOME_TAX_REGISTERED_SOURCE_REPAIR_RENDER_BINDINGS_V1"
        and value["family_id"] == FAMILY_ID
        and value["classification"] == "REGISTERED_RENDER_PROFILE_METADATA_ERROR"
        and value["base_git_commit"] == "8efd618b6c77f0cdbb402a440e7ba3b3549184f1"
        and value["original_source_repair_spec_sha256"] == ORIGINAL_REPAIR_SPEC_SHA
        and value["family_terminal_claimed"] is False,
        "Registered render bindings identity/scope differs",
    )
    original = _json(SPEC_PATHS["repair"])
    require(
        generic._sha256(SPEC_PATHS["repair"]) == ORIGINAL_REPAIR_SPEC_SHA
        and same_typed_json_v1(value["original_render_contract"], original["render_contract"])
        and same_typed_json_v1(compiled["income_tax_source_repairs"], original["repairs"])
        and compiled["income_tax_source_repair_spec_sha256"] == canonical_json_sha256_v1(original),
        "Original registered repair specification differs",
    )
    bindings = value["bindings"]
    require(
        type(bindings) is list
        and all(type(b) is dict and set(b) == {"repair_id", "profile"} for b in bindings)
        and [b["repair_id"] for b in bindings] == [r["repair_id"] for r in original["repairs"]]
        and all(type(b["profile"]) is str and b["profile"] in RENDER_PROFILES for b in bindings),
        "Registered render bindings repair frontier/profile differs",
    )
    return {b["repair_id"]: RENDER_PROFILES[b["profile"]] for b in bindings}


def _repair_render_bindings_v1(compiled):
    _safe_path(RENDER_BINDINGS_PATH)
    require(
        generic._sha256(RENDER_BINDINGS_PATH) == RENDER_BINDINGS_SHA,
        "Registered render bindings bytes differ",
    )
    return _validate_repair_render_bindings_v1(_json(RENDER_BINDINGS_PATH), compiled)


def _authenticate_repairs_v1(document, loaded, compiled, pdf_path):
    """Replay registered source pixels and literal pre-repair rows, never infer values."""
    import fitz
    from PIL import Image

    source = document["manifest"]["document"]
    repairs = [
        r
        for r in compiled["income_tax_source_repairs"]
        if r["pdf_source"]["sha256"] == source["source_sha256"]
    ]
    if not repairs:
        return []
    profiles = _repair_render_bindings_v1(compiled)
    by_id = {r["page_json_version_id"]: r for r in loaded}
    checked, rendered = [], {}
    with fitz.open(pdf_path) as pdf:
        for repair in repairs:
            require(
                same_typed_json_v1(
                    repair["pdf_source"],
                    {
                        "logical_name": source["source_logical_name"],
                        "sha256": source["source_sha256"],
                        "size_bytes": source["source_size_bytes"],
                    },
                ),
                "Repair PDF source binding differs",
            )
            locator = repair["locator"]
            page = by_id.get(locator["page_json_version_id"])
            require(
                page is not None and page["physical_page"] == locator["physical_page"],
                "Repair page is not selected",
            )
            _, table = _source_table(
                page["page_json"], section_id=locator["section_id"], table_id=locator["table_id"]
            )
            require(1 <= locator["row_ordinal"] <= len(table["rows"]), "Repair row locator absent")
            row = table["rows"][locator["row_ordinal"] - 1]
            before = (
                row["values_exact"][repair["column_ordinal"] - 1]
                if repair["repair_kind"] == "MONEY_CELL_PDF_VISIBLE_DASH"
                else {
                    k: row[k]
                    for k in ("hierarchy_path_exact", "label_exact", "row_kind", "values_exact")
                }
            )
            require(
                same_typed_json_v1(before, repair["before_exact"]),
                "Repair before-exact source differs",
            )
            physical = locator["physical_page"]
            matrix = profiles[repair["repair_id"]]
            render_key = (physical, matrix)
            if render_key not in rendered:
                require(1 <= physical <= len(pdf), "Repair physical page outside PDF")
                pix = pdf[physical - 1].get_pixmap(
                    matrix=fitz.Matrix(*matrix), colorspace=fitz.csRGB, alpha=False
                )
                rendered[render_key] = pix.tobytes("png")
            raw = rendered[render_key]
            with Image.open(BytesIO(raw)) as image:
                rgb = image.convert("RGB")
                visual = repair["visual_evidence"]
                actual = {
                    "sha256": sha256(raw).hexdigest(),
                    "width_pixels": rgb.width,
                    "height_pixels": rgb.height,
                }
                require(
                    same_typed_json_v1(actual, visual["page_render"])
                    and sha256(rgb.crop(tuple(visual["crop_bbox_pixels"])).tobytes()).hexdigest()
                    == visual["crop_rgb_sha256"],
                    "Repair PDF render/crop differs",
                )
            checked.append(repair["repair_id"])
    return checked


def _authenticate_source_label_discrepancies_v1(document, original_records, source_pdf_root):
    from bctc_ai.evaluation import gemini_json_income_tax_source_label_discrepancy_v1 as negative_labels

    if not negative_labels.registered_negative_source_label_observation_axis_v1(original_records):
        return []
    require(source_pdf_root is not None, "Registered source-label discrepancy requires original PDF pixels")
    source = document["manifest"]["document"]
    return negative_labels.authenticate_registered_negative_source_labels_v1(
        document_source=source, original_records=original_records,
        pdf_path=_safe_path(Path(source_pdf_root) / source["source_logical_name"]),
    )


def run(args):
    require(args.repo_root.resolve() == ROOT, "Runner checkout differs from explicit repo root")
    _assert_shared_pins_v1()
    for path in (
        args.repo_root,
        args.corpus_index,
        args.artifact_root,
        args.source_page_database,
        args.source_pdf_root,
        args.output_dir,
        args.results_database,
    ):
        _safe_path(path)
    require(
        not args.output_dir.exists()
        and not args.results_database.exists()
        and args.results_database.parent == args.output_dir,
        "Fresh output directory and contained results DB required",
    )
    authorities = [
        args.repo_root,
        args.artifact_root,
        args.source_pdf_root,
        args.corpus_index.parent,
        args.source_page_database.parent,
    ]
    require(
        not any(
            args.output_dir == p
            or args.output_dir.is_relative_to(p)
            or p.is_relative_to(args.output_dir)
            for p in authorities
        ),
        "Output overlaps source authority",
    )
    if args.base_cluster_cache is not None:
        _safe_path(args.base_cluster_cache)
        require(
            not any(args.base_cluster_cache.is_relative_to(p) for p in authorities)
            and args.base_cluster_cache != args.results_database,
            "Cache overlaps source/results authority",
        )
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    documents, selected_ids = _documents_v1(index, args.artifact_root)
    scope_path = getattr(args, "source_page_scope", PAGE_SCOPE_PATH)
    scope_rows = _page_scope_v1(scope_path)
    document_limit = getattr(args, "document_limit", None)
    documents, diagnostic_ordinals = _diagnostic_documents_v1(
        documents, document_limit=document_limit,
        document_ordinals=getattr(args, "document_ordinals", None),
    )
    specs, compiled = _compile_specs_v1()
    _repair_render_bindings_v1(compiled)
    implementation_paths = [
        Path(__file__).resolve(),
        ROOT / "scripts/experiments/f39_registered_part_period_pdf_auth_v1.py",
        ROOT / "scripts/experiments/f39_registered_section_caption_pdf_auth_v1.py",
        ROOT / DEFAULT_SECTION_CAPTION_AUTH_ENVELOPE_PATH,
        ROOT / DEFAULT_PART_PERIOD_CONTEXT_REGISTRY_PATH,
        ROOT / DEFAULT_PART_PERIOD_COMMON204_REGISTRY_PATH,
        ROOT / "src/bctc_ai/evaluation/gemini_json_income_tax_family_v1.py",
        ROOT / "config/families/tm-income-tax-source-label-discrepancies-v1.json",
        *(ROOT / p for p in SHARED_PINS),
        *SPEC_PATHS.values(),
        RENDER_BINDINGS_PATH,
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_income_tax_source_page_loader_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_income_tax_raw_money_census_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_current_corpus_manifest_index_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_current_document_manifest_selection_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_financial_page_json_v1.py",
        ROOT / "src/bctc_ai/source_structure/contracts_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        scope_path,
    ]
    implementation_paths = list(dict.fromkeys([
        *implementation_paths,
        *(ROOT / "src/bctc_ai" / relative for relative in _PERIOD_INVENTORY_DEPENDENCY_PATHS),
    ]))
    implementation_refs = [generic._file_ref(p) for p in implementation_paths]
    authority_paths = [args.corpus_index]
    for document in documents:
        authority_paths.extend(
            generic._content_ref(args.artifact_root, document["index_document"][name])
            for name in ("document_manifest_ref", "selection_ref")
        )
    authority_refs = [generic._file_ref(p) for p in authority_paths]
    require(args.corpus_index.is_relative_to(args.artifact_root), "Corpus index must be inside explicit artifact root")
    corpus_index_ref = {**generic._file_ref(args.corpus_index),
                        "path": args.corpus_index.relative_to(args.artifact_root).as_posix()}
    pdf_checked, repair_ids, census_refs, part_pdf_receipts, part_pdf_bundles, caption_admissions = [], [], [], [], [], []
    negative_label_admissions = []
    args.output_dir.mkdir(mode=0o700)
    cache = BaseClusterCache(args.base_cluster_cache)

    def retain_original_census(census):
        census_refs.append(_write_raw_census_document_v1(args.output_dir, census))

    def authenticate_original_document(document, loaded, original_records):
        # The bundle's one original loader result is shared with pixel repair
        # authentication. Never reload JSON just to inspect registered repairs.
        source = document["manifest"]["document"]
        path = _safe_path(args.source_pdf_root / source["source_logical_name"])
        require(path.is_file() and path.stat().st_size == source["source_size_bytes"]
                and generic._sha256(path) == source["source_sha256"],
                "Source PDF missing/hash/byte mismatch: " + str(path))
        import fitz

        with fitz.open(path) as source_pdf:
            coverage = _check_page_scope_v1(document, len(source_pdf), scope_rows)
        pdf_checked.append({**source, **coverage, "status": "PASS_BYTES_ONLY_NOT_VISUAL_AUDIT"})
        repair_ids.extend(_authenticate_repairs_v1(document, loaded, compiled, path))
        negative_label_admissions.append(_authenticate_source_label_discrepancies_v1(
            document, original_records, args.source_pdf_root))
        bundle = _authenticate_registered_part_catalog_pdf_v1(
            document, loaded, original_records, compiled, args.source_pdf_root,
        )
        part_pdf_bundles.append(bundle)
        part_pdf_receipts.extend(bundle["receipts"])
        caption_admissions.append(_authenticate_section_caption_admission_v1(
            document, loaded, original_records, compiled, args.source_pdf_root))

    try:
        with open_income_tax_original_census_source_v1(
            args.source_page_database, database_ref=index["database_ref"],
            artifact_root=args.artifact_root, corpus_index_ref=corpus_index_ref,
        ) as original_source:
            require(same_typed_json_v1(original_source.corpus_index, index), "Original census corpus index differs")
            indexed, trials, timing = _evaluate_stream_v1(
                args.source_page_database, documents, compiled, cache=cache, implementation_refs=implementation_refs,
                original_census_source=original_source, raw_census_sink=retain_original_census,
                original_document_records_callback=authenticate_original_document,
            )
            sweep = build_gemini_json_flat_family_sweep_v1(
                corpus_manifest_index_id=index["corpus_manifest_index_id"],
                topology_spec=specs["topology"],
                evaluation_spec=specs["evaluation"],
                schema_binding_spec=specs["schema"],
                trials=trials,
                indexed_query_evidence=indexed,
            )
            validate_gemini_json_flat_family_sweep_v1(sweep)
            observation = validate_source_observation_mapping_contract_v1(sweep)
            require(
                sweep["metrics"]["document_count"] == len(documents),
                "Sweep document denominator differs",
            )
            for source in pdf_checked:
                path = _safe_path(args.source_pdf_root / source["source_logical_name"])
                require(
                    path.stat().st_size == source["source_size_bytes"]
                    and generic._sha256(path) == source["source_sha256"],
                    "Source PDF bytes changed during replay: " + str(path),
                )
            _recheck_registered_part_catalog_pdf_v1(part_pdf_bundles, documents, compiled)
            _recheck_section_caption_admission_v1(
                caption_admissions, documents, compiled, indexed_query_evidence=indexed)
    finally:
        cache.close()
    _assert_shared_pins_v1()
    warm_census_bytes = canonical_json_bytes_v1(_raw_census_summary_v1(census_refs))
    # Authentication callbacks after owned-source exit are provisional until
    # both the fresh held DB descriptor and every post-callback input pass.
    with _authenticated_source_v1(args.source_page_database, index["database_ref"]):
        _recheck_registered_part_catalog_pdf_v1(part_pdf_bundles, documents, compiled)
        _recheck_section_caption_admission_v1(
            caption_admissions, documents, compiled, indexed_query_evidence=indexed)
        require(implementation_refs == [generic._file_ref(p) for p in implementation_paths],
                "Implementation bytes changed during warm final PDF callbacks")
        require(authority_refs == [generic._file_ref(p) for p in authority_paths],
                "Immutable authority bytes changed during warm final PDF callbacks")
        for document in documents:
            source = document["manifest"]["document"]
            path = _safe_path(args.source_pdf_root / source["source_logical_name"])
            require(path.is_file() and path.stat().st_size == source["source_size_bytes"]
                    and generic._sha256(path) == source["source_sha256"],
                    "Source PDF changed during warm final PDF callbacks: " + str(path))
        require(warm_census_bytes == canonical_json_bytes_v1(_raw_census_summary_v1(census_refs)),
                "Original census files changed during warm final PDF callbacks")
    require(
        implementation_refs == [generic._file_ref(p) for p in implementation_paths],
        "Family/spec/storage bytes changed during run",
    )
    require(
        authority_refs == [generic._file_ref(p) for p in authority_paths],
        "Index/immutable manifest/selection bytes changed during run",
    )
    # Acceptance barrier: all warm results/files above were provisional. Only
    # successful source-context exit plus source/code rechecks may hand a sweep
    # to persistence. The generic store invokes another independently owned
    # source context through this runner-file closure before inserting trials.
    raw_census = _raw_census_summary_v1(census_refs)
    require(raw_census["document_count"] == len(documents)
            and raw_census["counts"]["pages"] == len(indexed["selected_page_axis"]),
            "Original raw census selected denominator differs")
    raw_census.update(status="PASS_AUTHENTICATED_ORIGINAL_RAW_DENOMINATOR_NOT_ACCEPTANCE",
                      source_context_successfully_exited=True)
    raw_census_store = None
    if diagnostic_ordinals is None:
        replay_adapter = _make_authenticated_source_replay_adapter_v1(
            database=args.source_page_database, database_ref=index["database_ref"],
            artifact_root=args.artifact_root, corpus_index_ref=corpus_index_ref,
            documents=documents, expected_census_refs=census_refs,
            source_pdf_root=args.source_pdf_root,
            implementation_refs=implementation_refs, authority_refs=authority_refs,
            expected_caption_admission_axis=caption_admissions,
            expected_source_label_discrepancy_axis=negative_label_admissions,
        )
        started = time.perf_counter()
        stored = ingest_gemini_accounting_family_sweep_v1(
            args.results_database, sweep=sweep, corpus_index_ref=generic._file_ref(args.corpus_index),
            implementation_refs=implementation_refs, run_kind="EXPERIMENTAL",
            source_page_database=args.source_page_database, selected_page_json_version_ids=selected_ids,
            corpus_artifact_root=args.artifact_root, source_replay_adapter=replay_adapter,
            source_replay_adapter_ref=generic._file_ref(Path(__file__).resolve()),
        )
        timing["cold_source_replay_and_persistence_seconds"] = time.perf_counter() - started
        raw_census_store = _store_raw_money_censuses_v1(
            args.results_database, family_run_id=stored["family_run_id"], census_refs=census_refs,
        )
        reloaded = load_gemini_accounting_family_sweep_v1(args.results_database, stored["family_run_id"])
        require(same_typed_json_v1(reloaded, sweep), "Persisted sweep does not reload exactly")
        validate_source_observation_mapping_contract_v1(reloaded)
    _assert_shared_pins_v1()
    require(implementation_refs == [generic._file_ref(p) for p in implementation_paths]
            and authority_refs == [generic._file_ref(p) for p in authority_paths],
            "Family/source authority bytes changed during cold replay/persistence")
    for source in pdf_checked:
        path = _safe_path(args.source_pdf_root / source["source_logical_name"])
        require(path.stat().st_size == source["source_size_bytes"] and generic._sha256(path) == source["source_sha256"],
                "Source PDF changed before output handoff")
    require(same_typed_json_v1(raw_census["document_census_refs"], census_refs), "Raw census reference axis changed")
    _raw_census_summary_v1(census_refs)
    with _authenticated_source_v1(args.source_page_database, index["database_ref"]):
        _recheck_registered_part_catalog_pdf_v1(part_pdf_bundles, documents, compiled)
        _recheck_section_caption_admission_v1(
            caption_admissions, documents, compiled, indexed_query_evidence=indexed)
        require(implementation_refs == [generic._file_ref(p) for p in implementation_paths]
                and authority_refs == [generic._file_ref(p) for p in authority_paths],
                "Implementation/immutable authority bytes changed during output PDF callbacks")
        for document in documents:
            source = document["manifest"]["document"]
            path = _safe_path(args.source_pdf_root / source["source_logical_name"])
            require(path.is_file() and path.stat().st_size == source["source_size_bytes"]
                    and generic._sha256(path) == source["source_sha256"],
                    "Source PDF changed during output PDF callbacks: " + str(path))
        require(warm_census_bytes == canonical_json_bytes_v1(_raw_census_summary_v1(census_refs)),
                "Original census files changed during output PDF callbacks")
    # Existing immutable diagnostic/audit metadata retains actual pixel/source
    # admission. SQLite's exact sweep/index already retains V3 pure projection.
    # This is NOT an additional SQLite authentication BLOB/table.
    caption_admission = {
        "format_version": "INCOME_TAX_RUN_LINKED_CAPTION_ADMISSION_AXIS_V1",
        "status": "RETAINED_FRESH_ORIGINAL_SOURCE_ADMISSION_NOT_FAMILY_ACCEPTANCE",
        "query_evidence_id": indexed["query_evidence_id"],
        "indexed_query_evidence_sha256": canonical_json_sha256_v1(indexed),
        "document_admission_axis": json.loads(canonical_json_bytes_v1(caption_admissions)),
        "document_admission_axis_sha256": canonical_json_sha256_v1(caption_admissions),
        "document_count": len(documents),
        "all_indexed_dispositions_joined": True,
        "actual_pixel_authentication_retained_in": "IMMUTABLE_RUN_AUDIT_OR_BOUNDED_DIAGNOSTIC",
        "sqlite_retains_pure_projection_and_indexed_query": diagnostic_ordinals is None,
        "additional_sqlite_authentication_blob_claimed": False,
        "independent_cold_full_admission_axis_exact": diagnostic_ordinals is None,
        "family_acceptance_claimed": False,
    }
    if diagnostic_ordinals is not None:
        material = {
            "format_version": "INCOME_TAX_BOUNDED_DIAGNOSTIC_V1",
            "family_id": FAMILY_ID,
            "declared_corpus_manifest_index_id": index["corpus_manifest_index_id"],
            "complete_corpus_execution": False,
            "evaluated_corpus_document_ordinals": diagnostic_ordinals,
            "persistence_performed": False,
            "independent_cold_source_replay_performed": False,
            "terminal_or_final_acceptance_claimed": False,
            "pdf_visual_residual_audit": "REQUIRED_NOT_PERFORMED",
            "metrics": sweep["metrics"],
            "trials": trials,
            "indexed_query_evidence": indexed,
            "timing": timing,
            "source_observation_contract": observation,
            "original_raw_money_census": raw_census,
            "pdf_source_byte_bindings": pdf_checked,
            "authenticated_repair_ids": repair_ids,
            "registered_part_period_pdf_authentication": part_pdf_receipts,
            "registered_section_caption_admission": caption_admission,
            "registered_source_label_discrepancy_admission_axis": negative_label_admissions,
            "implementation_refs": implementation_refs,
            "immutable_input_refs": authority_refs,
        }
        material["diagnostic_id"] = "gjitfarunv1:bounded:" + canonical_json_sha256_v1(material)
        generic._write_once(args.output_dir / "income-tax-bounded-diagnostic.json", material)
        return {
            "disposition": "SUCCEEDED_BOUNDED_DIAGNOSTIC_NOT_ACCEPTANCE",
            "diagnostic_id": material["diagnostic_id"],
            "metrics": sweep["metrics"],
            "timing": timing,
            "persistence_performed": False,
            "diagnostic_ref": generic._file_ref(args.output_dir / "income-tax-bounded-diagnostic.json"),
        }
    output = args.output_dir / "income-tax-sweep.json"
    _write_income_tax_sweep_once_v1(output, sweep)
    export = record_gemini_accounting_family_export_v1(
        args.results_database, family_run_id=stored["family_run_id"], output_path=output
    )
    audit = {
        "family_id": FAMILY_ID,
        "format_version": "INCOME_TAX_OFFLINE_DIAGNOSTIC_AUDIT_V1",
        "run_kind": "EXPERIMENTAL",
        "sweep_id": sweep["sweep_id"],
        "family_run_id": stored["family_run_id"],
        "metrics": sweep["metrics"],
        "timing": timing,
        "source_observation_contract": observation,
        "original_raw_money_census": raw_census,
        "original_raw_money_census_store": raw_census_store,
        "pdf_source_byte_bindings": pdf_checked,
        "authenticated_repair_ids": repair_ids,
        "registered_part_period_pdf_authentication": part_pdf_receipts,
        "registered_section_caption_admission": caption_admission,
        "registered_source_label_discrepancy_admission_axis": negative_label_admissions,
        "registered_part_period_cold_authentication": "FRESH_PER_APPLICABLE_SOURCE_IN_COLD_REPLAY_ADAPTER",
        "selected_page_ids_sha256": canonical_json_sha256_v1(selected_ids),
        "implementation_refs": implementation_refs,
        "immutable_input_refs": authority_refs,
        "cold_source_replay": "PASS_EXACT_INDEPENDENT_STORAGE_QUERY_NO_CACHE",
        "results_reload": "PASS_EXACT",
        "pdf_visual_residual_audit": "REQUIRED_NOT_PERFORMED",
        "terminal_or_final_acceptance_claimed": False,
        "provider_calls_performed": False,
        "cache_is_acceptance_authority": False,
        "residuals": [
            {
                k: t[k]
                for k in (
                    "document_ordinal",
                    "source_logical_name",
                    "source_sha256",
                    "status",
                    "reasons",
                )
            }
            for t in trials
            if t["status"] != READY
        ],
    }
    audit["audit_id"] = "gjitfarunv1:audit:" + canonical_json_sha256_v1(audit)
    generic._write_once(args.output_dir / "income-tax-audit.json", audit)
    return {
        "disposition": "SUCCEEDED_DIAGNOSTIC_NOT_TERMINAL",
        "sweep_id": sweep["sweep_id"],
        "family_run_id": stored["family_run_id"],
        "metrics": sweep["metrics"],
        "output_ref": export,
        "audit_id": audit["audit_id"],
        "audit_ref": generic._file_ref(args.output_dir / "income-tax-audit.json"),
        "timing": timing,
    }


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "repo-root",
        "corpus-index",
        "source-page-database",
        "artifact-root",
        "source-pdf-root",
        "output-dir",
        "results-database",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--base-cluster-cache", type=Path)
    parser.add_argument("--source-page-scope", type=Path, default=PAGE_SCOPE_PATH)
    subset = parser.add_mutually_exclusive_group()
    subset.add_argument(
        "--document-limit",
        type=int,
        help="Evaluate the first N documents only; no persistence, cold replay or corpus acceptance claim",
    )
    subset.add_argument(
        "--document-ordinals", type=int, nargs="+",
        help="Evaluate these ascending immutable-index positions only; diagnostic without persistence or corpus acceptance",
    )
    return parser


def main():
    require(
        sys.platform.startswith("linux")
        and sys.version_info[:2] == (3, 12)
        and sys.dont_write_bytecode,
        "Linux Python3.12-B required",
    )
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
