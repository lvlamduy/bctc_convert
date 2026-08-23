#!/usr/bin/env python3
"""Build/replay the fixed 140-filing customer-loan maturity schema sweep."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import secrets
import stat
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1  # noqa: E402
from bctc_ai.evaluation import loan_maturity_numeric_reconciliation_v1 as numeric_v1  # noqa: E402
from bctc_ai.mapping import loan_maturity_bounded_schema_v1 as schema_v1  # noqa: E402
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import (  # noqa: E402
    loan_maturity_additional_population_evidence_v1 as additional_v1,
)
from scripts.experiments import (  # noqa: E402
    loan_maturity_numeric_conflict_evidence_v1 as conflict_v1,
)
from scripts.experiments import loan_maturity_variant_graph_v2 as graph_v2  # noqa: E402
from scripts.experiments.loan_type_missing_cell_evidence_v1 import _matcher_pages  # noqa: E402

FORMAT_VERSION = "FAMILY_FIRST_LOAN_MATURITY_140_FILING_SCHEMA_SWEEP_V1"
CLAIM_BOUNDARY = (
    "FIXED_140_FILING_AUTHENTICATED_SQLITE_SHORTLIST_COMPLETE_DOCUMENT_UNIQUE_"
    "LOAN_MATURITY_GRAPH_BOUND_PPOCRV6_VIETOCR_TYPED_VISIBLE_DASH_AND_TWO_"
    "STATELESS_HOSTED_GEMMA4_CHALLENGER_EXACT_PRINTED_ACCOUNTING_APPEND_STABLE_"
    "BOUNDED_LIVE_TM_SCHEMA_MAPPING_ONLY_NO_BACKSOLVE_OCR_REPLAY_"
    "CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
OUTPUT_PATH = Path(
    "output/calibration/family-first-loan-maturity-140-filing-schema-sweep-v1/result.json"
)
CHALLENGER_PATH = Path(
    "docs/experiments/E-0170-family-first-loan-maturity-hosted-gemma4-numeric-challenger-v1.json"
)
_IMPLEMENTATION_PATHS = (
    Path("src/bctc_ai/evaluation/family_first_document_evidence_store_v1.py"),
    Path("src/bctc_ai/evaluation/family_first_ocr_query_cache_v1.py"),
    Path("src/bctc_ai/evaluation/loan_maturity_numeric_reconciliation_v1.py"),
    Path("src/bctc_ai/mapping/loan_maturity_bounded_schema_v1.py"),
    Path("scripts/experiments/loan_maturity_variant_graph_v2.py"),
    Path("scripts/experiments/loan_maturity_numeric_conflict_evidence_v1.py"),
    Path("scripts/experiments/loan_maturity_additional_population_evidence_v1.py"),
    Path("scripts/experiments/build_family_first_loan_maturity_140_filing_schema_sweep_v1.py"),
)
_AUTHORITY = {
    "accounting_can_backsolve_or_invent_a_value": False,
    "accounting_is_corroboration_or_veto_only": True,
    "bank_filename_note_page_period_or_document_ordinal_used_as_mapping_rule": False,
    "blank_or_detector_omission_imputed_as_zero": False,
    "canonicalization_or_export_authority": False,
    "complete_document_unique_topology_required": True,
    "evidence_hydration_is_sqlite_page_shortlisted": True,
    "gemma4_used_as_sole_numeric_authority": False,
    "parent_716_or_752_emitted_as_mapping": False,
    "public_exact_live_replay_required": True,
    "raw_ppocrv6_and_vietocr_surfaces_preserved": True,
    "schema_mapping_authority_bounded_to_family_9": True,
    "visible_dash_zero_requires_authenticated_pixel_evidence": True,
}
_ROLES = ("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM")
_ROLE_IDS = {"SHORT_TERM": 753, "MEDIUM_TERM": 754, "LONG_TERM": 755}
_TARGET_DOCUMENT_COUNT = 140
_TARGET_CORE_MAPPING_COUNT = 420
_TARGET_MARGIN_MAPPING_COUNT = 18
_TARGET_MAPPING_COUNT = 438
_TARGET_MAPPED_MONEY_CELL_COUNT = 876
_TARGET_PERCENT_CHILD_CELL_COUNT = 108
_TARGET_PERCENT_TOTAL_CELL_COUNT = 36
_TARGET_LAYOUT_COUNTS = {
    "MONEY,MONEY": 122,
    "MONEY,PERCENT,MONEY,PERCENT": 18,
}
_TARGET_TOTAL_VARIANT_COUNTS = {
    "CORE_TOTAL_ONLY": 116,
    "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL": 12,
    "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL": 6,
    "LEADING_CORE_ADDITIONAL_POPULATION_GRAND_TOTAL": 6,
}
_TARGET_RAW_TOTAL_VARIANT_COUNTS = {
    "CORE_TOTAL_ONLY": 116,
    "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL": 13,
    "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL": 5,
    "LEADING_CORE_ADDITIONAL_POPULATION_GRAND_TOTAL": 6,
}
_TARGET_OWNER_COUNTS = {
    "SAME_PAGE_NEAREST_PRECEDING": 97,
    "IMMEDIATE_PRECEDING_PAGE": 37,
    "POST_BRANCH_TABLE_PARENT": 6,
}
_TARGET_PERIOD_COUNTS = {
    "LOCAL_EXACT_DATES": 100,
    "LOCAL_SPLIT_DATES": 22,
    "LOCAL_RELATIVE_PERIOD_ROLES": 12,
    "LOCAL_RELATIVE_YEAR_END_ROLES": 4,
    "LOCAL_UNAMBIGUOUS_MONTH_DAY_YEAR": 1,
    "BOUND_SOURCE_EXACT_DATE_CHALLENGER": 1,
}
_TARGET_BRANCH_COUNTS = {
    "TIME_WORDING": 54,
    "ORIGINAL_TERM_WORDING": 50,
    "INITIAL_TERM_WORDING": 12,
    "TERM_WORDING": 14,
    "TENOR_WORDING": 10,
}
_TARGET_EXPLICIT_BRANCH_COUNTS = {
    "TIME_WORDING": 54,
    "ORIGINAL_TERM_WORDING": 44,
    "INITIAL_TERM_WORDING": 11,
    "TERM_WORDING": 12,
    "TENOR_WORDING": 10,
}
_TARGET_IMPLIED_BRANCH_COUNTS = {
    "ORIGINAL_TERM_WORDING": 6,
    "INITIAL_TERM_WORDING": 1,
    "TERM_WORDING": 2,
}
_TARGET_UNIT_COUNTS = {
    "LOCAL_PER_LANE": 128,
    "INHERITED_DOCUMENT_MONEY_UNIT": 12,
}
_TARGET_BANK_MAPPING_COUNTS = {
    "ACB": 54,
    "MBB": 63,
    "VPB": 63,
    "HDB": 48,
    "VCB": 54,
    "CTG": 54,
    "BID": 48,
    "VIB": 54,
}
_TARGET_OBSERVED_EQUATION_COUNTS = {
    "CORE_ONLY_MONEY": 232,
    "DIRECT_CORE_ROWS_PLUS_MARGIN_MONEY": 24,
    "CORE_SUBTOTAL_AND_MARGIN_MONEY": 24,
    "CORE_AND_ADDITIONAL_GRAND_MONEY": 24,
    "ADDITIONAL_PARENT_BREAKDOWN_MONEY": 12,
    "PERCENTAGE": 36,
}
_EXPECTED_CHALLENGER_FORMAT = (
    "FAMILY_FIRST_LOAN_MATURITY_HOSTED_GEMMA4_NUMERIC_CHALLENGER_EVALUATION_V1"
)
_EXPECTED_CHALLENGER_SAMPLE = "sample-000077378"
_EXPECTED_CONTROL_SAMPLE = "sample-000077384"


class FamilyFirstLoanMaturity140FilingSchemaSweepV1Error(ValueError):
    """The store, shortlist, graph, numeric evidence, schema, or replay drifted."""


class LoanMaturityTrialUnresolvedV1Error(ValueError):
    """One filing lacks observed evidence required for a verified mapping."""


def _error(message: str) -> FamilyFirstLoanMaturity140FilingSchemaSweepV1Error:
    return FamilyFirstLoanMaturity140FilingSchemaSweepV1Error(message)


def _unresolved(message: str) -> LoanMaturityTrialUnresolvedV1Error:
    return LoanMaturityTrialUnresolvedV1Error(message)


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
    identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_size,
        item.st_mtime_ns,
    )
    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error(f"input changed during read: {relative}")
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _implementation_refs(root: Path) -> dict[str, dict[str, Any]]:
    return {path.as_posix(): _stable_ref(root, path) for path in _IMPLEMENTATION_PATHS}


def _assert_implementation_refs_unchanged(
    root: Path, expected: Mapping[str, Mapping[str, Any]]
) -> None:
    observed = _implementation_refs(root)
    if not same_typed_json_v1(expected, observed):
        raise _error("maturity implementation changed during formal build")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_challenger(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    reference = _stable_ref(root, CHALLENGER_PATH)
    payload = (root / CHALLENGER_PATH).read_bytes()
    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON token: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error("E-0170 is not strict UTF-8 JSON") from exc
    validated = conflict_v1.validate_loan_maturity_hosted_gemma4_challenger_v1(value, root)
    if (
        validated.get("format_version") != _EXPECTED_CHALLENGER_FORMAT
        or validated.get("target_observation", {}).get("sample_id") != _EXPECTED_CHALLENGER_SAMPLE
        or validated.get("total_control_observation", {}).get("sample_id")
        != _EXPECTED_CONTROL_SAMPLE
    ):
        raise _error("E-0170 target/control population drifted")
    if not same_typed_json_v1(_stable_ref(root, CHALLENGER_PATH), reference):
        raise _error("E-0170 changed during validated read")
    return canonical_clone_v1(validated), reference


def _candidate_pages(scan: Mapping[str, Any], packet: Mapping[str, Any]) -> tuple[int, ...]:
    regions = scan.get("regions")
    uniqueness = scan.get("uniqueness")
    if (
        scan.get("status") != "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
        or type(regions) is not list
        or len(regions) != 1
        or type(uniqueness) is not dict
        or scan.get("metrics", {}).get("complete_region_count") != 1
    ):
        raise _unresolved("complete-document maturity topology is not unique")
    region = regions[0]
    anchor = region.get("minimal_unique_anchor")
    if (
        type(anchor) is not dict
        or anchor.get("combination_size") != 2
        or anchor.get("pair_before_triple_search") is not True
    ):
        raise _unresolved("maturity topology lacks the minimal pair-first uniqueness proof")
    pages = {
        match.get("page_sequence")
        for match in region.get("child_matches", [])
        if type(match) is dict
    }
    parent = region.get("parent_match")
    if type(parent) is dict:
        pages.add(parent.get("page_sequence"))
    start = region.get("page_sequence")
    end = region.get("cluster_end_page_sequence_inclusive")
    if type(start) is int and type(end) is int and start <= end:
        pages.update(range(start, end + 1))
    if any(type(page) is not int or page <= 0 for page in pages) or not pages:
        raise _unresolved("maturity topology has no exact candidate page axis")
    first = min(pages)
    if first > 1:
        pages.add(first - 1)
    page_count = packet.get("page_count")
    if type(page_count) is not int or any(page > page_count for page in pages):
        raise _error("maturity topology candidate page lies outside document packet")
    return tuple(sorted(pages))


def _expanded_matcher_pages(
    selected_pages: Sequence[Mapping[str, Any]], *, page_count: int
) -> list[dict[str, Any]]:
    by_page = {page.get("page_sequence"): page for page in selected_pages}
    if len(by_page) != len(selected_pages):
        raise _error("selected maturity page axis repeats a page")
    matcher_selected = {page["page_sequence"]: page for page in _matcher_pages(selected_pages)}
    return [
        matcher_selected.get(
            page,
            {"lines": [], "page_sequence": page, "primary_numeric_authority": True},
        )
        for page in range(1, page_count + 1)
    ]


def _hydrate_graph(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    packet: Mapping[str, Any],
    scan: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Hydrate the target/owner pages, expanding backwards only for a unit anchor."""

    selected = set(_candidate_pages(scan, packet))
    while True:
        snapshot = store_v1.read_authenticated_family_first_document_selected_pages_v1(
            capability,
            document_ordinal=packet["document_ordinal"],
            selected_pages=tuple(sorted(selected)),
        )
        matcher = _expanded_matcher_pages(snapshot["joined_pages"], page_count=packet["page_count"])
        base = graph_v2.build_loan_maturity_variant_graph_from_topology_scan_v2(matcher, scan)
        graph = base["graphs"][0] if len(base.get("graphs", [])) == 1 else None
        if graph is None or graph.get("unit_scope", {}).get("mode") != "UNRESOLVED":
            return base, snapshot
        target = min(match["page_sequence"] for match in scan["regions"][0]["child_matches"])
        prior = min(selected) - 1
        if prior <= 0 or prior >= target or prior in selected:
            return base, snapshot
        selected.add(prior)


def _line_lookup(
    joined_pages: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, int], dict[str, Any]]:
    result = {}
    for page in joined_pages:
        page_sequence = page.get("page_sequence")
        for line in page.get("lines", []):
            key = (page_sequence, line.get("line_ordinal"))
            if (
                type(page_sequence) is not int
                or type(key[1]) is not int
                or key in result
                or type(line) is not dict
            ):
                raise _error("selected joined line identity drifted")
            result[key] = line
    return result


def _source_cell(
    raw: Mapping[str, Any],
    *,
    role: str,
    page_sequence: int,
    lookup: Mapping[tuple[int, int], Mapping[str, Any]],
    missing_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    lane = raw.get("lane_index")
    lane_type = raw.get("lane_type")
    line_index = raw.get("source_line_index")
    if type(lane) is not int or type(lane_type) is not str:
        raise _unresolved("maturity graph cell lacks one typed lane")
    if line_index is None:
        if (
            missing_evidence is None
            or raw.get("status") != "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_EVIDENCE"
        ):
            raise _unresolved("maturity graph retains one unbound numeric cell")
        evidence = missing_evidence.get("dash_evidence")
        if type(evidence) is not dict:
            raise _unresolved("maturity detector hole has no typed dash evidence")
        return {
            "bbox": None,
            "cell_id": f"{role}:lane-{lane}:pixel:{evidence['evidence_id']}",
            "crop_sha256": None,
            "lane_index": lane,
            "lane_type": lane_type,
            "ppocrv6_score": None,
            "ppocrv6_surface": None,
            "sample_id": None,
            "source_line_index": None,
            "vietocr_surface": None,
        }
    if type(line_index) is not int or line_index < 0:
        raise _unresolved("maturity graph source-line locator drifted")
    line = lookup.get((page_sequence, line_index))
    numeric = line.get("numeric_recognition") if line is not None else None
    crop = line.get("crop_ref") if line is not None else None
    if (
        type(line) is not dict
        or line.get("bbox") != raw.get("bbox")
        or line.get("vietocr_text") != raw.get("semantic_surface")
        or type(numeric) is not dict
        or numeric.get("raw_prediction") != raw.get("surface")
        or type(crop) is not dict
    ):
        raise _unresolved("maturity graph cell differs from selected authenticated line")
    return {
        "bbox": canonical_clone_v1(line["bbox"]),
        "cell_id": f"{role}:lane-{lane}:{line['sample_id']}",
        "crop_sha256": crop["sha256"],
        "lane_index": lane,
        "lane_type": lane_type,
        "ppocrv6_score": float(numeric["reader_score"]),
        "ppocrv6_surface": numeric["raw_prediction"],
        "sample_id": line["sample_id"],
        "source_line_index": line_index,
        "vietocr_surface": line["vietocr_text"],
    }


def _source_row(
    raw: Mapping[str, Any],
    *,
    role: str,
    page_sequence: int,
    lookup: Mapping[tuple[int, int], Mapping[str, Any]],
    lane_types: Sequence[str],
    missing_by_lane: Mapping[int, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    values = raw.get("values", raw.get("vector"))
    if type(values) is not list or len(values) != len(lane_types):
        raise _unresolved(f"maturity {role} row lacks its complete typed vector")
    cells = []
    for lane, value in enumerate(values):
        if value.get("lane_index") != lane or value.get("lane_type") != lane_types[lane]:
            raise _unresolved(f"maturity {role} typed vector order drifted")
        cells.append(
            _source_cell(
                value,
                role=role,
                page_sequence=page_sequence,
                lookup=lookup,
                missing_evidence=(missing_by_lane or {}).get(lane),
            )
        )
    nested_label = raw.get("label")
    label = None
    if nested_label is not None:
        if type(nested_label) is not dict:
            raise _unresolved(f"maturity {role} nested source label drifted")
        label = nested_label.get("surface")
        indices = nested_label.get("source_line_indices")
        label_page = nested_label.get("page_sequence")
        label_bbox = nested_label.get("bbox")
        if (
            type(label) is not str
            or not label.strip()
            or type(indices) is not list
            or not indices
            or any(type(index) is not int or index < 0 for index in indices)
            or len(indices) != len(set(indices))
            or label_page != page_sequence
            or type(label_bbox) is not list
            or len(label_bbox) != 4
        ):
            raise _unresolved(f"maturity {role} nested source label is incomplete")
        lines = [lookup.get((page_sequence, index)) for index in indices]
        if any(type(line) is not dict for line in lines):
            raise _unresolved(f"maturity {role} label is absent from selected evidence")
        typed_lines = [line for line in lines if type(line) is dict]
        observed_bbox = [
            min(line["bbox"][0] for line in typed_lines),
            min(line["bbox"][1] for line in typed_lines),
            max(line["bbox"][2] for line in typed_lines),
            max(line["bbox"][3] for line in typed_lines),
        ]
        vietocr_surface = " ".join(line["vietocr_text"].strip() for line in typed_lines).strip()
        ppocrv6_surface = " ".join(
            line["numeric_recognition"]["raw_prediction"].strip() for line in typed_lines
        ).strip()
        if observed_bbox != label_bbox or label not in {vietocr_surface, ppocrv6_surface}:
            raise _unresolved(f"maturity {role} label differs from selected evidence")
    else:
        label = raw.get("label_surface")
        if type(label) is not str or not label.strip():
            if role not in {"CORE_SUBTOTAL", "GRAND_TOTAL"}:
                raise _unresolved(f"maturity {role} lacks its observed source label")
            label = role
    return {"cells": cells, "label_surface": label, "role": role}


def _challenge_control_row(
    challenger: Mapping[str, Any],
    *,
    role: str,
    source_role: str,
    page_sequence: int,
    lookup: Mapping[tuple[int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    controls = [
        item
        for item in challenger["accounting_effect"]["printed_control_cells"]
        if item.get("role") == source_role
    ]
    if len(controls) != 2 or [item.get("lane_index") for item in controls] != [0, 1]:
        raise _unresolved(f"E-0170 lacks the two {source_role} control cells")
    cells = []
    for item in controls:
        lane = item["lane_index"]
        line = lookup.get((page_sequence, item["source_line_index"]))
        numeric = line.get("numeric_recognition") if line is not None else None
        crop = line.get("crop_ref") if line is not None else None
        if (
            type(line) is not dict
            or line.get("sample_id") != item["sample_id"]
            or type(numeric) is not dict
            or numeric.get("raw_prediction") != item["surface"]
            or type(crop) is not dict
        ):
            raise _unresolved("E-0170 printed control differs from selected line evidence")
        cells.append(
            {
                "bbox": canonical_clone_v1(line["bbox"]),
                "cell_id": f"{role}:lane-{lane}:{line['sample_id']}",
                "crop_sha256": crop["sha256"],
                "lane_index": lane,
                "lane_type": "MONEY",
                "ppocrv6_score": float(numeric["reader_score"]),
                "ppocrv6_surface": numeric["raw_prediction"],
                "sample_id": line["sample_id"],
                "source_line_index": line["line_ordinal"],
                "vietocr_surface": line["vietocr_text"],
            }
        )
    return {"cells": cells, "label_surface": source_role, "role": role}


def _numeric_source(
    base: Mapping[str, Any],
    joined_pages: Sequence[Mapping[str, Any]],
    *,
    challenger: Mapping[str, Any] | None,
    conflict_overlay: Mapping[str, Any] | None,
    additional_overlay: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len(base.get("graphs", [])) != 1:
        raise _unresolved("maturity numeric adapter requires one unique graph")
    graph = base["graphs"][0]
    rows = graph.get("rows")
    lane_types = graph.get("unit_scope", {}).get("lane_types")
    if (
        type(rows) is not list
        or [row.get("role") for row in rows] != list(_ROLES)
        or type(lane_types) is not list
        or tuple(lane_types) not in {("MONEY", "MONEY"), ("MONEY", "PERCENT", "MONEY", "PERCENT")}
    ):
        raise _unresolved("maturity graph rows or typed lane axis is incomplete")
    page_sequence = rows[0].get("label", {}).get("page_sequence")
    if type(page_sequence) is not int:
        raise _unresolved("maturity graph value page is absent")
    lookup = _line_lookup(joined_pages)
    core_rows = [
        _source_row(
            row,
            role=role,
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
        )
        for role, row in zip(_ROLES, rows, strict=True)
    ]
    accounting = graph.get("accounting")
    if type(accounting) is not dict:
        raise _unresolved("maturity graph accounting population is absent")
    subtotal_rows = accounting.get("core_total_rows", [])
    grand_rows = accounting.get("grand_total_rows", [])
    margin = graph.get("margin")
    additional = graph.get("additional_source_populations", [])
    source_margin = None
    source_subtotal = None
    source_grand = None
    source_additional = None
    dash_bindings: list[dict[str, Any]] = []

    if conflict_overlay is not None:
        if (
            challenger is None
            or conflict_overlay.get("base_result_id") != base.get("result_id")
            or conflict_overlay.get("status")
            != "NUMERIC_EXACT_WITH_TWO_HOSTED_GEMMA4_CONSENSUS_RESCUE"
            or margin is None
            or additional
        ):
            raise _unresolved("E-0170 conflict overlay does not bind this maturity graph")
        source_margin = _source_row(
            margin,
            role="MARGIN_AND_SECURITIES_ADVANCE",
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
        )
        source_subtotal = _challenge_control_row(
            challenger,
            role="CORE_SUBTOTAL",
            source_role="CORE_TOTAL",
            page_sequence=page_sequence,
            lookup=lookup,
        )
        source_grand = _challenge_control_row(
            challenger,
            role="GRAND_TOTAL",
            source_role="GRAND_TOTAL",
            page_sequence=page_sequence,
            lookup=lookup,
        )
    elif additional_overlay is not None:
        if (
            additional_overlay.get("base_result_id") != base.get("result_id")
            or additional_overlay.get("status") != "AUTHENTICATED_PIXEL_DASH_AND_ACCOUNTING_EXACT"
            or len(additional) != 1
            or margin is not None
            or len(subtotal_rows) != 1
        ):
            raise _unresolved("pixel-dash overlay does not bind this maturity graph")
        population = additional[0]
        overlay_evidence: dict[tuple[str, int], Mapping[str, Any]] = {}
        role_map = {
            "ADDITIONAL_PARENT": "ADDITIONAL_POPULATION_PARENT",
            "ADDITIONAL_SHORT_BREAKDOWN": "ADDITIONAL_SHORT_TERM",
        }
        for raw in additional_overlay.get("evidence", []):
            role = role_map.get(raw.get("role")) if type(raw) is dict else None
            lane = raw.get("lane_index") if type(raw) is dict else None
            if role is None or type(lane) is not int or (role, lane) in overlay_evidence:
                raise _unresolved("pixel-dash overlay evidence role/lane drifted")
            overlay_evidence[(role, lane)] = raw
        parent_missing = {
            lane: evidence
            for (role, lane), evidence in overlay_evidence.items()
            if role == "ADDITIONAL_POPULATION_PARENT"
        }
        child_missing = {
            lane: evidence
            for (role, lane), evidence in overlay_evidence.items()
            if role == "ADDITIONAL_SHORT_TERM"
        }
        source_parent = _source_row(
            population,
            role="ADDITIONAL_POPULATION_PARENT",
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
            missing_by_lane=parent_missing,
        )
        source_child = _source_row(
            population["breakdown"],
            role="ADDITIONAL_SHORT_TERM",
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
            missing_by_lane=child_missing,
        )
        source_additional = {"breakdown_rows": [source_child], "parent": source_parent}
        source_subtotal = _source_row(
            subtotal_rows[0],
            role="CORE_SUBTOTAL",
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
        )
        grand = population.get("grand_total")
        if type(grand) is not dict:
            raise _unresolved("additional population printed grand total is absent")
        source_grand = _source_row(
            grand,
            role="GRAND_TOTAL",
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
        )
        dash_bindings = [canonical_clone_v1(additional_overlay)]
    elif additional:
        if len(additional) != 1 or margin is not None or len(subtotal_rows) != 1:
            raise _unresolved("visible additional population structure is ambiguous")
        population = additional[0]
        source_parent = _source_row(
            population,
            role="ADDITIONAL_POPULATION_PARENT",
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
        )
        source_child = _source_row(
            population["breakdown"],
            role="ADDITIONAL_SHORT_TERM",
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
        )
        source_additional = {"breakdown_rows": [source_child], "parent": source_parent}
        source_subtotal = _source_row(
            subtotal_rows[0],
            role="CORE_SUBTOTAL",
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
        )
        grand = population.get("grand_total")
        if type(grand) is not dict:
            raise _unresolved("visible additional population printed grand total is absent")
        source_grand = _source_row(
            grand,
            role="GRAND_TOTAL",
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
        )
    elif margin is not None:
        if len(grand_rows) != 1 or additional:
            raise _unresolved("margin maturity graph lacks one printed grand total")
        source_margin = _source_row(
            margin,
            role="MARGIN_AND_SECURITIES_ADVANCE",
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
        )
        if subtotal_rows:
            if len(subtotal_rows) != 1:
                raise _unresolved("margin maturity graph has multiple core subtotals")
            source_subtotal = _source_row(
                subtotal_rows[0],
                role="CORE_SUBTOTAL",
                page_sequence=page_sequence,
                lookup=lookup,
                lane_types=lane_types,
            )
        source_grand = _source_row(
            grand_rows[0],
            role="GRAND_TOTAL",
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
        )
    else:
        if len(subtotal_rows) != 1 or grand_rows or additional:
            raise _unresolved("core-only maturity graph lacks one unambiguous subtotal")
        source_subtotal = _source_row(
            subtotal_rows[0],
            role="CORE_SUBTOTAL",
            page_sequence=page_sequence,
            lookup=lookup,
            lane_types=lane_types,
        )

    source = {
        "additional_population": source_additional,
        "core_rows": core_rows,
        "core_subtotal": source_subtotal,
        "family_id": graph_v2.FAMILY_ID,
        "format_version": numeric_v1.INPUT_FORMAT_VERSION,
        "grand_total": source_grand,
        "lane_types": canonical_clone_v1(lane_types),
        "margin": source_margin,
        "period_axis": canonical_clone_v1(graph["period_axis"]),
        "source_id": base["result_id"],
    }
    return source, dash_bindings


def _mapping_rows(
    evidence: Mapping[str, Any],
    graph: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> list[dict[str, Any]]:
    role_nodes = {item["role"]: item for item in schema["mapped_roles"]}
    money_lanes = [
        index for index, lane_type in enumerate(evidence["lane_types"]) if lane_type == "MONEY"
    ]
    periods = graph.get("period_axis", {}).get("periods")
    if len(money_lanes) != 2 or type(periods) is not list or len(periods) != 2:
        raise _unresolved("maturity mapping requires two observed money periods")
    source_rows = list(evidence["core_rows"])
    if evidence.get("margin") is not None:
        source_rows.append(evidence["margin"])
    mappings = []
    for row in source_rows:
        role = row["role"]
        node = role_nodes.get(role)
        if node is None:
            raise _error("numeric maturity role is outside bounded schema projection")
        cells = [row["cells"][lane] for lane in money_lanes]
        if any(
            cell.get("status") != "RESOLVED_OBSERVED_VALUE"
            or type(cell.get("selected_value")) is not int
            for cell in cells
        ):
            raise _unresolved("mapped maturity row retains an unresolved money value")
        mappings.append(
            {
                "canonical_name": node["canonical_name"],
                "period_axis": canonical_clone_v1(periods),
                "report_norm_id": node["report_norm_id"],
                "role": role,
                "schema_projection_id": schema["projection_id"],
                "source_label": row["label_surface"],
                "status": "VERIFIED_BY_CODEX",
                "value_cells": canonical_clone_v1(cells),
                "values": [cell["selected_value"] for cell in cells],
            }
        )
    expected = [753, 754, 755] + ([5747] if evidence.get("margin") is not None else [])
    if [mapping["report_norm_id"] for mapping in mappings] != expected:
        raise _error("bounded maturity mapping identity/order drifted")
    return mappings


def _resolved_total_variant(
    evidence: Mapping[str, Any],
    graph: Mapping[str, Any],
    conflict_overlay: Mapping[str, Any] | None,
) -> str:
    if evidence.get("status") != "EXACT_OBSERVED_NUMERIC_RECONCILIATION":
        raise _error("resolved total variant requires exact numeric evidence")
    margin = evidence.get("margin")
    subtotal = evidence.get("core_subtotal")
    grand = evidence.get("grand_total")
    additional = evidence.get("additional_population")
    if additional is not None:
        if margin is not None or subtotal is None or grand is None:
            raise _error("resolved additional-population total structure drifted")
        resolved = "LEADING_CORE_ADDITIONAL_POPULATION_GRAND_TOTAL"
    elif margin is not None:
        if grand is None:
            raise _error("resolved margin total structure lacks its grand total")
        resolved = (
            "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL"
            if subtotal is not None
            else "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL"
        )
    else:
        if subtotal is None or grand is not None:
            raise _error("resolved core-only total structure drifted")
        resolved = "CORE_TOTAL_ONLY"

    graph_variant = graph.get("accounting", {}).get("variant")
    if resolved != graph_variant:
        reasons = graph.get("unresolved_reasons")
        if (
            resolved != "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL"
            or graph_variant != "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL"
            or reasons != ["CORE_PLUS_MARGIN_GRAND_TOTAL_NOT_CORROBORATED"]
            or type(conflict_overlay) is not dict
            or conflict_overlay.get("status")
            != "NUMERIC_EXACT_WITH_TWO_HOSTED_GEMMA4_CONSENSUS_RESCUE"
        ):
            raise _error("resolved total variant differs from its structural graph")
    return resolved


def _unresolved_trial(
    packet: Mapping[str, Any],
    scan: Mapping[str, Any],
    reasons: Sequence[str],
) -> dict[str, Any]:
    return {
        "additional_population_evidence": None,
        "challenger_conflict_evidence": None,
        "document": canonical_clone_v1(packet),
        "graph_result": None,
        "mapped_children": [],
        "numeric_evidence": None,
        "numeric_input": None,
        "selected_page_snapshot_id": None,
        "selected_pages": [],
        "status": "UNRESOLVED_FAIL_CLOSED",
        "topology_scan_id": scan.get("scan_id"),
        "unresolved_reasons": sorted(set(reasons)),
    }


def _trial(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    packet: Mapping[str, Any],
    scan: Mapping[str, Any],
    schema: Mapping[str, Any],
    challenger: Mapping[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    try:
        base, snapshot = _hydrate_graph(capability, packet, scan)
        if len(base.get("graphs", [])) != 1:
            raise _unresolved("maturity graph is not one unique structural region")
        graph = base["graphs"][0]
        if base.get("uniqueness") != {
            "complete_region_count": 1,
            "minimal_role_combination_proved": True,
        }:
            raise _unresolved("maturity graph lost its pair-first uniqueness proof")
        joined = snapshot["joined_pages"]
        challenge_document = challenger["document"]
        challenge_applies = packet.get("document_id") == challenge_document["document_id"]
        if challenge_applies:
            challenger = conflict_v1.validate_loan_maturity_hosted_gemma4_challenger_v1(
                challenger, document_packet=packet
            )
        if challenge_applies and (
            not same_typed_json_v1(
                packet.get("source_pdf_ref"), challenge_document.get("source_pdf_ref")
            )
            or challenge_document["physical_page"] not in {page["page_sequence"] for page in joined}
        ):
            raise _unresolved("E-0170 document/page does not bind the shortlisted filing")

        conflict_overlay = None
        additional_overlay = None
        reasons = graph.get("unresolved_reasons")
        if base.get("status") == "ACCEPTED_VARIANT_GRAPH":
            if reasons:
                raise _error("accepted maturity graph retains unresolved reasons")
        elif reasons == ["CORE_PLUS_MARGIN_GRAND_TOTAL_NOT_CORROBORATED"]:
            if not challenge_applies:
                raise _unresolved("numeric conflict has no exact E-0170 document binding")
            conflict_overlay = conflict_v1.build_loan_maturity_numeric_conflict_evidence_v1(
                base,
                joined,
                challenger,
                project_root,
                document_packet=packet,
            )
            conflict_v1.validate_loan_maturity_numeric_conflict_evidence_replay_v1(
                conflict_overlay,
                base,
                joined,
                challenger,
                project_root,
                document_packet=packet,
            )
        elif reasons == ["ADDITIONAL_POPULATION_VISIBLE_DASH_EVIDENCE_REQUIRED"]:
            page_sequence = graph["rows"][0]["label"]["page_sequence"]
            renders = store_v1.read_authenticated_family_first_document_page_renders_v1(
                capability,
                document_ordinal=packet["document_ordinal"],
                physical_pages=(page_sequence,),
            )
            if len(renders) != 1:
                raise _unresolved("additional-population page render is not unique")
            additional_overlay = (
                additional_v1.build_loan_maturity_additional_population_evidence_v1(
                    base,
                    joined,
                    renders[0],
                    document_ordinal=packet["document_ordinal"],
                )
            )
            additional_v1.validate_loan_maturity_additional_population_evidence_replay_v1(
                additional_overlay,
                base,
                joined,
                renders[0],
                document_ordinal=packet["document_ordinal"],
            )
            if additional_overlay["status"] != "AUTHENTICATED_PIXEL_DASH_AND_ACCOUNTING_EXACT":
                raise _unresolved("additional-population pixel/accounting overlay is unresolved")
        else:
            raise _unresolved(
                "maturity graph retains an unsupported veto: "
                + ",".join(reasons if type(reasons) is list else [str(reasons)])
            )

        source, dash_bindings = _numeric_source(
            base,
            joined,
            challenger=challenger if conflict_overlay is not None else None,
            conflict_overlay=conflict_overlay,
            additional_overlay=additional_overlay,
        )
        challenge_overlays = [challenger] if conflict_overlay is not None else []
        numeric = numeric_v1.build_loan_maturity_numeric_reconciliation_v1(
            source,
            challenger_overlays=challenge_overlays,
            visible_dash_evidence=dash_bindings,
        )
        numeric_v1.validate_loan_maturity_numeric_reconciliation_replay_v1(
            numeric,
            source,
            challenger_overlays=challenge_overlays,
            visible_dash_evidence=dash_bindings,
        )
        if numeric["status"] != "EXACT_OBSERVED_NUMERIC_RECONCILIATION":
            raise _unresolved(";".join(numeric["unresolved_reasons"]))
        mappings = _mapping_rows(numeric, graph, schema)
    except LoanMaturityTrialUnresolvedV1Error as exc:
        return _unresolved_trial(packet, scan, [str(exc)])
    return {
        "additional_population_evidence": canonical_clone_v1(additional_overlay),
        "challenger_conflict_evidence": canonical_clone_v1(conflict_overlay),
        "document": canonical_clone_v1(packet),
        "graph_result": canonical_clone_v1(base),
        "mapped_children": mappings,
        "numeric_evidence": canonical_clone_v1(numeric),
        "numeric_input": canonical_clone_v1(source),
        "resolved_total_variant": _resolved_total_variant(numeric, graph, conflict_overlay),
        "selected_page_snapshot_id": snapshot["snapshot_id"],
        "selected_pages": [page["page_sequence"] for page in snapshot["joined_pages"]],
        "status": "VERIFIED_BY_CODEX",
        "topology_scan_id": scan["scan_id"],
        "unresolved_reasons": [],
    }


def _counter(values: Sequence[str], expected: Mapping[str, int], label: str) -> dict[str, int]:
    observed = Counter(values)
    if dict(observed) != dict(expected):
        raise _error(f"maturity terminal {label} distribution drifted: {dict(observed)}")
    return {key: observed[key] for key in expected}


def _equation_bucket(trial: Mapping[str, Any], check: Mapping[str, Any]) -> str:
    variant = trial.get("resolved_total_variant")
    equation = check.get("equation_id")
    if check.get("lane_type") == "PERCENT":
        return "PERCENTAGE"
    if variant == "CORE_TOTAL_ONLY":
        return "CORE_ONLY_MONEY"
    if variant == "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL":
        return "DIRECT_CORE_ROWS_PLUS_MARGIN_MONEY"
    if variant == "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL":
        return "CORE_SUBTOTAL_AND_MARGIN_MONEY"
    if variant == "LEADING_CORE_ADDITIONAL_POPULATION_GRAND_TOTAL":
        return (
            "ADDITIONAL_PARENT_BREAKDOWN_MONEY"
            if type(equation) is str and equation.startswith("ADDITIONAL_BREAKDOWN_EQUAL_PARENT")
            else "CORE_AND_ADDITIONAL_GRAND_MONEY"
        )
    raise _error("maturity accounting equation belongs to an unknown presentation variant")


def _terminal_material(
    trials: Sequence[Mapping[str, Any]], inputs: Mapping[str, Any]
) -> dict[str, Any]:
    if type(trials) not in {list, tuple} or len(trials) != _TARGET_DOCUMENT_COUNT:
        raise _error("maturity terminal sweep requires exactly 140 trials")
    unresolved = [trial for trial in trials if trial.get("status") != "VERIFIED_BY_CODEX"]
    if unresolved:
        raise _error("maturity sweep retains one or more fail-closed unresolved trials")

    mappings = [mapping for trial in trials for mapping in trial["mapped_children"]]
    core_count = sum(mapping.get("report_norm_id") in {753, 754, 755} for mapping in mappings)
    margin_count = sum(mapping.get("report_norm_id") == 5747 for mapping in mappings)
    parent_mapping_count = sum(mapping.get("report_norm_id") in {716, 752} for mapping in mappings)
    money_cell_count = sum(len(mapping.get("value_cells", [])) for mapping in mappings)
    if (
        core_count != _TARGET_CORE_MAPPING_COUNT
        or margin_count != _TARGET_MARGIN_MAPPING_COUNT
        or len(mappings) != _TARGET_MAPPING_COUNT
        or parent_mapping_count != 0
        or money_cell_count != _TARGET_MAPPED_MONEY_CELL_COUNT
    ):
        raise _error("maturity terminal bounded mapping/cell counts drifted")

    layouts = []
    raw_variants = []
    variants = []
    owners = []
    periods = []
    branches = []
    explicit_branches = []
    implied_branches = []
    units = []
    bank_mapping_counts: Counter[str] = Counter()
    equation_counts: Counter[str] = Counter()
    percentage_children = 0
    percentage_totals = 0
    computed_unprinted = 0
    additional_population_count = 0
    additional_source_row_count = 0
    additional_source_cell_count = 0
    visible_dash_count = 0
    challenger_conflicts = 0
    challenger_controls = 0
    continuation_count = 0
    minimal_pair_count = 0
    shortlisted_page_count = 0
    variant_divergences = []
    for trial in trials:
        base = trial["graph_result"]
        graph = base["graphs"][0]
        evidence = trial["numeric_evidence"]
        if evidence.get("status") != "EXACT_OBSERVED_NUMERIC_RECONCILIATION":
            raise _error("verified maturity trial lacks exact numeric evidence")
        if base.get("uniqueness", {}).get("minimal_role_combination_proved") is True:
            minimal_pair_count += 1
        continuation_count += graph.get("continuation_page_count", 0)
        shortlisted_page_count += len(trial["selected_pages"])
        layouts.append(",".join(evidence["lane_types"]))
        raw_variant = graph["accounting"]["variant"]
        resolved_variant = _resolved_total_variant(
            evidence, graph, trial.get("challenger_conflict_evidence")
        )
        if trial.get("resolved_total_variant") != resolved_variant:
            raise _error("persisted resolved total variant differs from numeric evidence")
        raw_variants.append(raw_variant)
        variants.append(resolved_variant)
        if raw_variant != resolved_variant:
            conflict = trial.get("challenger_conflict_evidence")
            source_totals = conflict.get("source_totals") if type(conflict) is dict else None
            conflict_checks = conflict.get("accounting_checks") if type(conflict) is dict else None
            money_checks = [
                check
                for check in evidence["accounting_checks"]
                if check.get("lane_type") == "MONEY"
            ]
            expected_controls = {
                ("CORE_TOTAL", 0),
                ("CORE_TOTAL", 1),
                ("GRAND_TOTAL", 0),
                ("GRAND_TOTAL", 1),
            }
            if (
                base.get("status") != "UNRESOLVED"
                or graph.get("unresolved_reasons")
                != ["CORE_PLUS_MARGIN_GRAND_TOTAL_NOT_CORROBORATED"]
                or type(conflict) is not dict
                or conflict.get("challenge_evaluation_id")
                != inputs.get("hosted_gemma4_challenger_evaluation_id")
                or type(source_totals) is not list
                or len(source_totals) != 4
                or {(item.get("role"), item.get("lane_index")) for item in source_totals}
                != expected_controls
                or type(conflict_checks) is not list
                or len(conflict_checks) != 4
                or any(check.get("status") != "CORROBORATED_EXACT" for check in conflict_checks)
                or len(money_checks) != 4
                or any(
                    check.get("status") != "CORROBORATED_EXACT_OBSERVED_EQUATION"
                    for check in money_checks
                )
            ):
                raise _error("raw/resolved total divergence lacks exact E-0170 evidence")
            variant_divergences.append(
                {
                    "challenge_evaluation_id": conflict["challenge_evaluation_id"],
                    "conflict_result_id": conflict["result_id"],
                    "document_id": trial["document"]["document_id"],
                    "graph_result_id": base["result_id"],
                    "numeric_source_id": evidence["source_id"],
                    "raw_variant": raw_variant,
                    "resolved_variant": resolved_variant,
                }
            )
        owners.append(graph["owner"]["mode"])
        periods.append(graph["period_axis"]["mode"])
        branch = graph["branch"]
        branches.append(branch["variant"])
        if branch.get("resolution") == "EXPLICIT_PARENT":
            explicit_branches.append(branch["variant"])
        elif branch.get("resolution") == "IMPLIED_BY_REQUIRED_CHILD_CLUSTER":
            implied_branches.append(branch["variant"])
        else:
            raise _error("maturity branch resolution provenance drifted")
        units.append(graph["unit_scope"]["mode"])
        bank = trial["document"]["bank_provenance"]
        bank_mapping_counts[bank] += len(trial["mapped_children"])
        percentage_children += evidence["metrics"]["percentage_child_cell_count"]
        percentage_totals += evidence["metrics"]["percentage_total_control_cell_count"]
        computed_unprinted += evidence["metrics"]["computed_unprinted_core_identity_count"]
        additional_population_count += evidence["metrics"]["source_additional_population_count"]
        visible_dash_count += evidence["metrics"]["visible_dash_zero_cell_count"]
        additional = evidence.get("additional_population")
        if additional is not None:
            source_rows = [additional["parent"], *additional["breakdown_rows"]]
            additional_source_row_count += len(source_rows)
            additional_source_cell_count += sum(len(row["cells"]) for row in source_rows)
        for check in evidence["accounting_checks"]:
            if check.get("status") != "CORROBORATED_EXACT_OBSERVED_EQUATION":
                raise _error("verified maturity trial retains one non-exact required equation")
            equation_counts[_equation_bucket(trial, check)] += 1
        conflict = trial.get("challenger_conflict_evidence")
        if conflict is not None:
            challenger_conflicts += 1
            if conflict.get("target_resolution", {}).get("sample_id") != (
                _EXPECTED_CHALLENGER_SAMPLE
            ):
                raise _error("E-0170 conflict target is not exact")
            challenger_controls += sum(
                item.get("sample_id") == _EXPECTED_CONTROL_SAMPLE
                for item in conflict.get("source_totals", [])
            )

    layout_counts = _counter(layouts, _TARGET_LAYOUT_COUNTS, "typed-lane")
    raw_variant_counts = _counter(raw_variants, _TARGET_RAW_TOTAL_VARIANT_COUNTS, "raw-total-mode")
    variant_counts = _counter(variants, _TARGET_TOTAL_VARIANT_COUNTS, "resolved-total-mode")
    owner_counts = _counter(owners, _TARGET_OWNER_COUNTS, "owner")
    period_counts = _counter(periods, _TARGET_PERIOD_COUNTS, "period")
    branch_counts = _counter(branches, _TARGET_BRANCH_COUNTS, "branch")
    explicit_branch_counts = _counter(
        explicit_branches, _TARGET_EXPLICIT_BRANCH_COUNTS, "explicit-branch"
    )
    implied_branch_counts = _counter(
        implied_branches, _TARGET_IMPLIED_BRANCH_COUNTS, "implied-branch"
    )
    unit_counts = _counter(units, _TARGET_UNIT_COUNTS, "unit")
    if dict(bank_mapping_counts) != _TARGET_BANK_MAPPING_COUNTS:
        raise _error(f"maturity terminal bank mapping counts drifted: {dict(bank_mapping_counts)}")
    if dict(equation_counts) != _TARGET_OBSERVED_EQUATION_COUNTS:
        raise _error(
            f"maturity terminal observed equation decomposition drifted: {dict(equation_counts)}"
        )
    if (
        percentage_children != _TARGET_PERCENT_CHILD_CELL_COUNT
        or percentage_totals != _TARGET_PERCENT_TOTAL_CELL_COUNT
        or sum(equation_counts.values()) != 352
        or computed_unprinted != 24
        or additional_population_count != 6
        or additional_source_row_count != 12
        or additional_source_cell_count != 24
        or visible_dash_count != 8
        or challenger_conflicts != 1
        or challenger_controls != 1
        or len(variant_divergences) != 1
        or continuation_count != 0
        or minimal_pair_count != _TARGET_DOCUMENT_COUNT
    ):
        raise _error("maturity terminal percentage/source/challenger/continuation gates drifted")

    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "inputs": canonical_clone_v1(inputs),
        "metrics": {
            "additional_source_population_count": additional_population_count,
            "additional_source_population_money_cell_count": additional_source_cell_count,
            "additional_source_population_row_count": additional_source_row_count,
            "bank_mapped_record_counts": dict(_TARGET_BANK_MAPPING_COUNTS),
            "branch_variant_trial_counts": branch_counts,
            "explicit_parent_branch_variant_trial_counts": explicit_branch_counts,
            "computed_unprinted_core_identity_count": computed_unprinted,
            "continuation_page_count": continuation_count,
            "document_count": _TARGET_DOCUMENT_COUNT,
            "hosted_gemma4_challenged_full_page_count": 1,
            "hosted_gemma4_conflict_cell_count": challenger_conflicts,
            "hosted_gemma4_control_cell_count": challenger_controls,
            "hosted_gemma4_stateless_request_count": 2,
            "mapped_core_record_count": core_count,
            "mapped_margin_record_count": margin_count,
            "mapped_money_cell_count": money_cell_count,
            "mapped_parent_716_or_752_record_count": parent_mapping_count,
            "mapped_record_count": len(mappings),
            "minimal_pair_unique_trial_count": minimal_pair_count,
            "implied_parent_branch_variant_trial_counts": implied_branch_counts,
            "numeric_exact_trial_count": _TARGET_DOCUMENT_COUNT,
            "observed_accounting_equation_count": sum(equation_counts.values()),
            "observed_accounting_equation_counts": dict(_TARGET_OBSERVED_EQUATION_COUNTS),
            "owner_mode_trial_counts": owner_counts,
            "percentage_child_cell_count": percentage_children,
            "percentage_total_control_cell_count": percentage_totals,
            "period_mode_trial_counts": period_counts,
            "raw_resolved_total_variant_divergence_count": len(variant_divergences),
            "raw_total_variant_trial_counts": raw_variant_counts,
            "shortlisted_page_hydration_count": shortlisted_page_count,
            "structure_unique_trial_count": _TARGET_DOCUMENT_COUNT,
            "total_variant_trial_counts": variant_counts,
            "typed_lane_axis_trial_counts": layout_counts,
            "unit_scope_trial_counts": unit_counts,
            "unresolved_trial_count": 0,
            "verified_trial_count": _TARGET_DOCUMENT_COUNT,
            "visible_dash_zero_cell_count": visible_dash_count,
        },
        "state": "COMPLETE",
        "trials": canonical_clone_v1(trials),
        "variant_divergences": variant_divergences,
    }
    return {
        **material,
        "sweep_id": "lm140v1:sweep:" + canonical_json_sha256_v1(material),
    }


def build_authenticated_family_first_loan_maturity_140_filing_schema_sweep_v1(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    project_root: Path,
    *,
    topology_jobs: int = 12,
) -> dict[str, Any]:
    """Build all 140 mappings from direct topology scans and shortlisted evidence."""

    if not isinstance(project_root, Path):
        raise _error("maturity sweep project root must be one pathlib Path")
    root = project_root.resolve()
    implementation_refs = _implementation_refs(root)
    store_projection = store_v1.project_authenticated_family_first_document_evidence_store_v1(
        capability
    )
    if store_projection["metrics"]["document_count"] != _TARGET_DOCUMENT_COUNT:
        raise _error("maturity sweep requires the fixed 140-filing denominator")
    scans = store_v1.recompute_authenticated_family_first_topology_scans_v1(
        capability, graph_v2.LOAN_MATURITY_TOPOLOGY_SPEC_V2, jobs=topology_jobs
    )
    if len(scans) != _TARGET_DOCUMENT_COUNT:
        raise _error("direct maturity topology scan denominator drifted")
    challenger, challenger_ref = _strict_challenger(root)
    schema = schema_v1.build_live_loan_maturity_bounded_schema_projection_v1(root)
    schema_v1.validate_loan_maturity_bounded_schema_projection_v1(schema)
    packets = [
        store_v1.read_authenticated_family_first_document_packet_v1(
            capability, document_ordinal=ordinal
        )
        for ordinal in range(1, _TARGET_DOCUMENT_COUNT + 1)
    ]
    trials = [
        _trial(capability, packet, scan, schema, challenger, root)
        for packet, scan in zip(packets, scans, strict=True)
    ]
    challenge_documents = [
        packet
        for packet in packets
        if packet["document_id"] == challenger["document"]["document_id"]
    ]
    if len(challenge_documents) != 1:
        raise _error("E-0170 document does not occur exactly once in the authenticated store")
    final_store_projection = store_v1.project_authenticated_family_first_document_evidence_store_v1(
        capability
    )
    if not same_typed_json_v1(store_projection, final_store_projection):
        raise _error("authenticated document evidence store changed during formal build")
    _assert_implementation_refs_unchanged(root, implementation_refs)
    inputs = {
        "bounded_schema_projection": schema,
        "document_evidence_store": store_projection,
        "hosted_gemma4_challenger": challenger_ref,
        "hosted_gemma4_challenger_evaluation_id": challenger["evaluation_id"],
        "implementation_refs": implementation_refs,
        "topology_scan_ids": [scan["scan_id"] for scan in scans],
        "topology_spec_sha256": hashlib.sha256(
            canonical_json_bytes_v1(graph_v2.LOAN_MATURITY_TOPOLOGY_SPEC_V2)
        ).hexdigest(),
    }
    return _terminal_material(trials, inputs)


def validate_authenticated_family_first_loan_maturity_140_filing_schema_sweep_replay_v1(
    value: Any,
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    project_root: Path,
    *,
    topology_jobs: int = 12,
) -> dict[str, Any]:
    expected = build_authenticated_family_first_loan_maturity_140_filing_schema_sweep_v1(
        capability, project_root, topology_jobs=topology_jobs
    )
    if not same_typed_json_v1(value, expected):
        raise _error("maturity 140-filing schema sweep does not replay exactly")
    return expected


def _strict_result(path: Path) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON token: {token}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error("persisted maturity sweep is not strict JSON") from exc
    if type(value) is not dict or payload != canonical_json_bytes_v1(value) + b"\n":
        raise _error("persisted maturity sweep is not canonical JSON plus LF")
    material = canonical_clone_v1(value)
    identity = material.pop("sweep_id", None)
    if identity != "lm140v1:sweep:" + canonical_json_sha256_v1(material):
        raise _error("persisted maturity sweep self-identity drifted")
    return value


def _write_exclusive(path: Path, payload: bytes) -> None:
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
                count = os.write(descriptor, view)
                if count <= 0:
                    raise _error("maturity sweep write made no progress")
                view = view[count:]
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
                raise _error("maturity sweep destination already exists") from exc
            raise
        os.fsync(directory)
        os.unlink(temporary_name, dir_fd=directory)
        temporary_created = False
        os.fsync(directory)
    finally:
        if temporary_created:
            try:
                os.unlink(temporary_name, dir_fd=directory)
                os.fsync(directory)
            except FileNotFoundError:
                pass
        os.close(directory)


def run_family_first_loan_maturity_140_filing_schema_sweep_v1(
    project_root: Path, *, command: str, topology_jobs: int = 12
) -> dict[str, Any]:
    if command not in {"build", "verify"}:
        raise _error("maturity sweep command drifted")
    root = project_root.resolve()
    output = root / OUTPUT_PATH
    if command == "build" and output.exists():
        raise _error("maturity sweep destination already exists")
    persisted = _strict_result(output) if command == "verify" else None
    capability = store_v1.authenticate_family_first_document_evidence_store_v1(root)
    result = build_authenticated_family_first_loan_maturity_140_filing_schema_sweep_v1(
        capability, root, topology_jobs=topology_jobs
    )
    if command == "build":
        _write_exclusive(output, canonical_json_bytes_v1(result) + b"\n")
    elif not same_typed_json_v1(persisted, result):
        raise _error("persisted maturity sweep differs from live exact replay")
    return {"metrics": result["metrics"], "state": result["state"], "sweep_id": result["sweep_id"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--topology-jobs", type=int, default=12)
    arguments = parser.parse_args()
    result = run_family_first_loan_maturity_140_filing_schema_sweep_v1(
        arguments.project_root,
        command=arguments.command,
        topology_jobs=arguments.topology_jobs,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
