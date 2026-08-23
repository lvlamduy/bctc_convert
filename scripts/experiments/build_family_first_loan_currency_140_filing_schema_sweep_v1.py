#!/usr/bin/env python3
"""Build/replay the bounded 140-filing customer-loan currency sweep."""

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
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import accounting_family_column_context_v1 as column_v1  # noqa: E402
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_v1  # noqa: E402
from bctc_ai.evaluation import accounting_hierarchical_table_closure_v1 as closure_v1  # noqa: E402
from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1  # noqa: E402
from bctc_ai.evaluation import loan_currency_numeric_reconciliation_v1 as numeric_v1  # noqa: E402
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (  # noqa: E402
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.mapping import loan_currency_bounded_schema_v1 as schema_v1  # noqa: E402
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import loan_currency_variant_graph_v2 as graph_v2  # noqa: E402
from scripts.experiments import loan_currency_visible_dash_evidence_v1 as dash_v1  # noqa: E402

FORMAT_VERSION = "FAMILY_FIRST_LOAN_CURRENCY_140_FILING_SCHEMA_SWEEP_V1"
CLAIM_BOUNDARY = (
    "FIXED_140_FILING_AUTHENTICATED_SQLITE_COMPLETE_DOCUMENT_UNIQUE_LOAN_"
    "CURRENCY_GRAPH_FULL_AXIS_FOR_TEN_POSITIVES_ONLY_PPOCRV6_VIETOCR_EXACT_"
    "PIXEL_DASH_AND_BOUNDED_PIXEL_PEER_APPEND_STABLE_SCHEMA_MAPPING_NO_"
    "BANK_PAGE_YEAR_ORDINAL_ROUTING_BACKSOLVE_OCR_OR_EXPORT_AUTHORITY"
)
OUTPUT_PATH = Path(
    "output/calibration/family-first-loan-currency-140-filing-schema-sweep-v1/result.json"
)
_IMPLEMENTATION_PATHS = (
    Path("src/bctc_ai/evaluation/family_first_document_evidence_store_v1.py"),
    Path("src/bctc_ai/evaluation/family_first_ocr_query_cache_v1.py"),
    Path("src/bctc_ai/evaluation/accounting_family_topology_v1.py"),
    Path("src/bctc_ai/evaluation/accounting_family_row_axis_v1.py"),
    Path("src/bctc_ai/evaluation/accounting_family_column_context_v1.py"),
    Path("src/bctc_ai/evaluation/accounting_hierarchical_table_closure_v1.py"),
    Path("src/bctc_ai/evaluation/family_first_visible_dash_glyph_evidence_v1.py"),
    Path("src/bctc_ai/evaluation/loan_currency_numeric_reconciliation_v1.py"),
    Path("src/bctc_ai/mapping/loan_currency_bounded_schema_v1.py"),
    Path("scripts/experiments/loan_currency_variant_graph_v2.py"),
    Path("scripts/experiments/loan_currency_visible_dash_evidence_v1.py"),
    Path("scripts/experiments/build_family_first_loan_currency_140_filing_schema_sweep_v1.py"),
)
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
_AUTHORITY = {
    "absence_trial_hydrates_numeric_or_page_evidence": False,
    "accounting_can_backsolve_or_invent_a_value": False,
    "accounting_is_corroboration_or_veto_only": True,
    "bank_filename_note_page_period_year_or_document_ordinal_used_as_mapping_rule": False,
    "blank_or_detector_omission_imputed_as_zero": False,
    "canonicalization_or_export_authority": False,
    "complete_document_unique_topology_required": True,
    "full_joined_axis_hydrated_only_for_positive_trials": True,
    "gemma_used": False,
    "parent_716_or_756_emitted_as_mapping": False,
    "packet_period_metadata_is_corroboration_not_inference": True,
    "public_exact_live_replay_required": True,
    "raw_ppocrv6_and_vietocr_surfaces_preserved": True,
    "schema_mapping_authority_bounded_to_family_10": True,
    "shared_hierarchical_derived_values_used_as_numeric_source": False,
    "visible_dash_zero_requires_exact_pixel_replay": True,
}
_TARGET_DOCUMENT_COUNT = 140
_TARGET_PRESENCE_COUNT = 10
_TARGET_ABSENCE_COUNT = 130
_TARGET_MAPPING_COUNT = 20
_TARGET_MAPPED_MONEY_CELL_COUNT = 40
_TARGET_EQUATION_COUNT = 36
_TARGET_FULL_AXIS_PAGE_COUNT = 822
_TARGET_FULL_AXIS_NONEMPTY_PAGE_COUNT = 818
_TARGET_FULL_AXIS_ZERO_LINE_PAGE_COUNT = 4
_TARGET_FULL_AXIS_LINE_COUNT = 63_028
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
_TARGET_BANK_PRESENCE_COUNTS = {
    "ACB": 6,
    "MBB": 0,
    "VPB": 0,
    "HDB": 4,
    "VCB": 0,
    "CTG": 0,
    "BID": 0,
    "VIB": 0,
}
_TARGET_BANK_ABSENCE_COUNTS = {
    bank: _TARGET_BANK_DOCUMENT_COUNTS[bank] - _TARGET_BANK_PRESENCE_COUNTS[bank]
    for bank in _BANK_ORDER
}
_TARGET_BANK_MAPPING_COUNTS = {
    "ACB": 12,
    "MBB": 0,
    "VPB": 0,
    "HDB": 8,
    "VCB": 0,
    "CTG": 0,
    "BID": 0,
    "VIB": 0,
}
_TARGET_OWNER_COUNTS = {"PRECEDING_SECTION_OWNER": 6, "POST_BRANCH_VISIBLE_CORE_OWNER": 4}
_TARGET_PERIOD_COUNTS = {
    "LOCAL_EXACT_DATES": 6,
    "LOCAL_RELATIVE_YEAR_END_ROLES": 2,
    "LOCAL_RELATIVE_PERIOD_ROLES": 2,
}
_TARGET_UNIT_COUNTS = {"LOCAL_MILLION_VND": 10}
_MAPPED_ROLES = ("VND_LOANS", "FOREIGN_CURRENCY_AND_GOLD_LOANS")
_ADDITIONAL_ROLES = (
    "DEFERRED_LC_PRE_2024_GROUP",
    "DEFERRED_LC_VND",
    "DEFERRED_LC_FOREIGN",
)
_ABSENCE_STATUS = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
_PRESENCE_STATUS = "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
_PINNED_FROZEN_SHA256 = {
    "src/bctc_ai/evaluation/loan_currency_numeric_reconciliation_v1.py": (
        "c64754815c16fd51dc4b338109175aec9e779216242faf1d11fb92494c340f6f"
    ),
    "src/bctc_ai/mapping/loan_currency_bounded_schema_v1.py": (
        "65261d0876ef53ec25a84f1024bffb9ae28acfae2c3cb4e3b32e297ae5ab13e3"
    ),
    "scripts/experiments/loan_currency_variant_graph_v2.py": (
        "2f5140d5ece05fa524e380a13970372fb78d2a18a6da6c0ad973ecda22d78ae5"
    ),
    "scripts/experiments/loan_currency_visible_dash_evidence_v1.py": (
        "f73bd31e8245c092625cacec5539e02a005716cf0533f041820943ed4128d948"
    ),
}


class FamilyFirstLoanCurrency140FilingSchemaSweepV1Error(ValueError):
    """The store, graph, pixel evidence, numeric closure, schema, or replay drifted."""


class LoanCurrencyTrialUnresolvedV1Error(ValueError):
    """One positive filing lacks evidence required for a verified mapping."""


def _error(message: str) -> FamilyFirstLoanCurrency140FilingSchemaSweepV1Error:
    return FamilyFirstLoanCurrency140FilingSchemaSweepV1Error(message)


def _unresolved(message: str) -> LoanCurrencyTrialUnresolvedV1Error:
    return LoanCurrencyTrialUnresolvedV1Error(message)


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


def _schema_source_refs(root: Path) -> dict[str, dict[str, Any]]:
    return {path.as_posix(): _stable_ref(root, path) for path in _SCHEMA_SOURCE_PATHS}


def _assert_implementation_refs_unchanged(
    root: Path, expected: Mapping[str, Mapping[str, Any]]
) -> None:
    if not same_typed_json_v1(expected, _implementation_refs(root)):
        raise _error("loan-currency implementation changed during formal build")


def _candidate_region(scan: Mapping[str, Any], packet: Mapping[str, Any]) -> dict[str, Any]:
    regions = scan.get("regions")
    metrics = scan.get("metrics")
    if (
        scan.get("status") != _PRESENCE_STATUS
        or type(regions) is not list
        or len(regions) != 1
        or type(metrics) is not dict
        or metrics.get("complete_region_count") != 1
        or metrics.get("near_region_count") != 0
    ):
        raise _unresolved("complete-document loan-currency topology is not unique")
    region = regions[0]
    anchor = region.get("minimal_unique_anchor")
    if (
        type(region) is not dict
        or region.get("parent_resolution") != "EXPLICIT_PARENT"
        or region.get("continuation_page_count") != 0
        or type(anchor) is not dict
        or anchor.get("combination_size") != 2
        or anchor.get("pair_before_triple_search") is not True
    ):
        raise _unresolved("loan-currency region lacks its explicit pair-first uniqueness proof")
    start = region.get("page_sequence")
    end = region.get("cluster_end_page_sequence_inclusive")
    if type(start) is not int or start <= 0 or end != start or start > packet.get("page_count", 0):
        raise _unresolved("loan-currency region is not one bound source page")
    roles = {item.get("role") for item in region.get("child_matches", [])}
    if not set(_MAPPED_ROLES) <= roles:
        raise _unresolved("loan-currency region lacks both required classified children")
    return canonical_clone_v1(region)


def _line_lookup(pages: Sequence[Mapping[str, Any]]) -> dict[tuple[int, int], dict[str, Any]]:
    result = {}
    for page in pages:
        page_sequence = page.get("page_sequence")
        if type(page_sequence) is not int:
            raise _error("loan-currency joined page identity drifted")
        for line in page.get("lines", []):
            index = line.get("line_ordinal") if type(line) is dict else None
            key = (page_sequence, index)
            if type(index) is not int or key in result:
                raise _error("loan-currency joined line identity repeats")
            result[key] = line
    return result


def _owner_binding(
    row_axis: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    region = row_axis["topology_region"]
    core_rows = [row for row in row_axis["rows"] if row.get("role") == "CORE_TOTAL_GROUP"]
    if len(core_rows) == 1:
        label = core_rows[0]["label_match"]
        mode = "POST_BRANCH_VISIBLE_CORE_OWNER"
        indices = label.get("source_line_indices", [label.get("source_line_index")])
        page_sequence = label.get("page_sequence")
    elif core_rows:
        raise _unresolved("loan-currency owner core population repeats")
    else:
        parent = region["parent_match"]
        page_sequence = parent["page_sequence"]
        parent_bbox = parent.get("_bbox")
        if (
            type(parent_bbox) is not list
            or len(parent_bbox) != 4
            or any(type(item) is not int for item in parent_bbox)
        ):
            raise _unresolved("loan-currency branch geometry is absent")
        page = next((item for item in pages if item["page_sequence"] == page_sequence), None)
        if page is None:
            raise _unresolved("loan-currency preceding owner page is absent")
        core_spec = next(
            item
            for item in graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2["children"]
            if item["role"] == "CORE_TOTAL_GROUP"
        )
        aliases = {
            normalize_vietnamese_anchor_v1(alias)
            for matcher in core_spec["matchers"]
            for alias in matcher["aliases"]
        }
        candidates = [
            line
            for line in page["lines"]
            if type(line.get("bbox")) is list
            and len(line["bbox"]) == 4
            and line["bbox"][3] <= parent_bbox[1]
            and any(
                normalize_vietnamese_anchor_v1(line["vietocr_text"]).startswith(alias)
                for alias in aliases
            )
        ]
        if not candidates:
            raise _unresolved("loan-currency explicit branch lacks its customer-loan owner")
        ranked = sorted(
            candidates,
            key=lambda item: (
                parent_bbox[1] - item["bbox"][3],
                abs((item["bbox"][0] + item["bbox"][2]) - (parent_bbox[0] + parent_bbox[2])),
                item["sample_id"],
            ),
        )
        if len(ranked) > 1 and (
            parent_bbox[1] - ranked[0]["bbox"][3] == parent_bbox[1] - ranked[1]["bbox"][3]
        ):
            raise _unresolved("loan-currency preceding owner geometry is tied")
        owner = ranked[0]
        indices = [owner["line_ordinal"]]
        mode = "PRECEDING_SECTION_OWNER"
    if (
        type(indices) is not list
        or not indices
        or any(type(index) is not int for index in indices)
        or type(page_sequence) is not int
    ):
        raise _unresolved("loan-currency owner source indices drifted")
    lookup = _line_lookup(pages)
    lines = [lookup.get((page_sequence, index)) for index in indices]
    if any(type(line) is not dict for line in lines):
        raise _unresolved("loan-currency owner is absent from authenticated evidence")
    typed = [line for line in lines if type(line) is dict]
    material = {
        "mode": mode,
        "page_sequence": page_sequence,
        "role": "CUSTOMER_LOANS_OWNER",
        "sample_ids": [line["sample_id"] for line in typed],
        "source_line_indices": indices,
        "surface": " ".join(line["vietocr_text"].strip() for line in typed).strip(),
    }
    return {**material, "owner_binding_id": "lc140v1:owner:" + canonical_json_sha256_v1(material)}


def _period_mode(
    context: Mapping[str, Any], lookup: Mapping[tuple[int, int], Mapping[str, Any]]
) -> str:
    axis = context.get("period_axis")
    if type(axis) is not list or len(axis) != 2:
        raise _unresolved("loan-currency period axis is not two columns")
    statuses = {item.get("projection_status") for item in axis}
    surfaces = []
    for item in axis:
        locations = item.get("evidence_locations")
        if (
            type(locations) is not list
            or not locations
            or any(
                type(location) is not dict
                or type(location.get("page_sequence")) is not int
                or type(location.get("source_line_index")) is not int
                for location in locations
            )
        ):
            raise _unresolved("loan-currency relative period lacks local PDF evidence")
        lines = [
            lookup.get((location.get("page_sequence"), location.get("source_line_index")))
            for location in locations
            if type(location) is dict
        ]
        if len(lines) != len(locations) or any(type(line) is not dict for line in lines):
            raise _unresolved("loan-currency relative period evidence is not authenticated")
        surfaces.append(
            normalize_vietnamese_anchor_v1(
                " ".join(line["vietocr_text"] for line in lines if type(line) is dict)
            )
        )
    if statuses == {"LOCAL_EXACT_DATES_PROJECTED_TO_BODY_COLUMN"}:
        return "LOCAL_EXACT_DATES"
    joined = " | ".join(surfaces)
    if "cuoi nam" in joined and "dau nam" in joined:
        return "LOCAL_RELATIVE_YEAR_END_ROLES"
    if "cuoi ky" in joined and "dau ky" in joined:
        return "LOCAL_RELATIVE_PERIOD_ROLES"
    raise _unresolved("loan-currency document-bound relative period roles are ambiguous")


def _packet_period_corroborates_pdf_axis(
    packet: Mapping[str, Any], period_axis: Sequence[Mapping[str, Any]]
) -> bool:
    """Corroborate, never derive, the PDF-selected current balance date."""

    if type(period_axis) is not list or len(period_axis) != 2:
        return False
    current = period_axis[0].get("resolved_period")
    if type(current) is not str:
        return False
    parts = current.split("/")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        return False
    day, month, year = (int(part) for part in parts)
    expected_month_day = {
        "Q1": (31, 3),
        "H1": (30, 6),
        "Q3": (30, 9),
        "ANNUAL": (31, 12),
    }.get(packet.get("period"))
    return (
        type(packet.get("year")) is int
        and year == packet["year"]
        and expected_month_day is not None
        and (day, month) == expected_month_day
    )


def _bound_column_context(
    context: Mapping[str, Any], pages: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    if (
        context.get("status") != "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
        or context.get("metrics")
        != {"column_count": 2, "period_column_count": 2, "unit_column_count": 2}
        or context.get("unresolved_reasons") != []
    ):
        raise _unresolved("loan-currency period/unit context is not exact")
    period_axis = context["period_axis"]
    unit_axis = context["unit_axis"]
    if (
        type(period_axis) is not list
        or type(unit_axis) is not list
        or len(period_axis) != 2
        or len(unit_axis) != 2
        or any(type(item) is not dict for item in period_axis)
        or any(type(item) is not dict for item in unit_axis)
        or any(type(item.get("column_ordinal")) is not int for item in period_axis)
        or any(type(item.get("column_ordinal")) is not int for item in unit_axis)
        or [item.get("column_ordinal") for item in period_axis] != [0, 1]
        or [item.get("column_ordinal") for item in unit_axis] != [0, 1]
        or any(
            item.get("unit_kind") != "MONEY"
            or item.get("currency") != "VND"
            or type(item.get("magnitude_power10")) is not int
            or item.get("magnitude_power10") != 6
            or not str(item.get("projection_status", "")).startswith("LOCAL_EXPLICIT_UNIT_")
            for item in unit_axis
        )
    ):
        raise _unresolved("loan-currency local two-lane million-VND axis drifted")
    lookup = _line_lookup(pages)
    mode = _period_mode(context, lookup)
    for item in unit_axis:
        locations = item.get("evidence_locations")
        if type(locations) is not list or not locations:
            raise _unresolved("loan-currency unit lacks local PDF evidence")
        for location in locations:
            if (
                type(location) is not dict
                or type(location.get("page_sequence")) is not int
                or type(location.get("source_line_index")) is not int
                or type(lookup.get((location["page_sequence"], location["source_line_index"])))
                is not dict
            ):
                raise _unresolved("loan-currency unit evidence is not authenticated")
    period = {
        "column_context_id": context["column_context_id"],
        "mode": mode,
        "periods": canonical_clone_v1(period_axis),
        "semantics": "BALANCE_COMPARATIVE",
    }
    unit = {
        "column_context_id": context["column_context_id"],
        "mode": "LOCAL_MILLION_VND",
        "units": canonical_clone_v1(unit_axis),
    }
    return period, unit, mode, "LOCAL_MILLION_VND"


def _observed_cell(
    value: Mapping[str, Any],
    *,
    role: str,
    lane: int,
    lookup: Mapping[tuple[int, int], Mapping[str, Any]],
    packet_id: str,
) -> dict[str, Any]:
    page = value.get("page_sequence")
    line_index = value.get("line_ordinal")
    line = lookup.get((page, line_index))
    numeric = line.get("numeric_recognition") if type(line) is dict else None
    crop = line.get("crop_ref") if type(line) is dict else None
    bbox = line.get("bbox") if type(line) is dict else None
    score = numeric.get("reader_score") if type(numeric) is dict else None
    raw_prediction = numeric.get("raw_prediction") if type(numeric) is dict else None
    vietocr = line.get("vietocr_text") if type(line) is dict else None
    sample = line.get("sample_id") if type(line) is dict else None
    crop_sha = crop.get("sha256") if type(crop) is dict else None
    if (
        type(page) is not int
        or type(line_index) is not int
        or type(line) is not dict
        or type(numeric) is not dict
        or type(crop) is not dict
        or type(lane) is not int
        or lane not in {0, 1}
        or type(bbox) is not list
        or len(bbox) != 4
        or any(type(item) is not int or item < 0 for item in bbox)
        or not (bbox[0] < bbox[2] and bbox[1] < bbox[3])
        or bbox != value.get("bbox")
        or type(sample) is not str
        or not sample
        or sample != value.get("sample_id")
        or type(raw_prediction) is not str
        or raw_prediction != value.get("raw_prediction")
        or type(vietocr) is not str
        or type(score) is not float
        or not 0 <= score <= 1
        or type(crop_sha) is not str
        or len(crop_sha) != 64
        or any(character not in "0123456789abcdef" for character in crop_sha)
    ):
        raise _unresolved("loan-currency row-axis value differs from authenticated source line")
    identity = {
        "lane_index": lane,
        "packet_id": packet_id,
        "role": role,
        "sample_id": line["sample_id"],
    }
    return {
        "bbox": canonical_clone_v1(bbox),
        "cell_id": "lc140v1:cell:" + canonical_json_sha256_v1(identity),
        "crop_sha256": crop_sha,
        "lane_index": lane,
        "lane_type": "MONEY",
        "page_sequence": page,
        "ppocrv6_score": score,
        "ppocrv6_surface": raw_prediction,
        "sample_id": sample,
        "source_line_index": line_index,
        "vietocr_surface": vietocr,
    }


def _missing_pixel_cell(cell: Mapping[str, Any], *, lane: int) -> dict[str, Any]:
    if (
        type(lane) is not int
        or lane not in {0, 1}
        or type(cell.get("column_ordinal")) is not int
        or cell.get("column_ordinal") != lane
        or type(cell.get("page_sequence")) is not int
        or type(cell.get("cell_id")) is not str
        or type(cell.get("region_png_ref")) is not dict
    ):
        raise _unresolved("loan-currency missing cell lacks exact pixel evidence binding")
    return {
        "bbox": canonical_clone_v1(cell["recognition_raw_pixel_bbox"]),
        "cell_id": cell["cell_id"],
        "crop_sha256": cell["region_png_ref"]["sha256"],
        "lane_index": lane,
        "lane_type": "MONEY",
        "page_sequence": cell["page_sequence"],
        "ppocrv6_score": None,
        "ppocrv6_surface": None,
        "sample_id": None,
        "source_line_index": None,
        "vietocr_surface": None,
    }


def _numeric_row(
    row: Mapping[str, Any],
    *,
    output_role: str,
    lookup: Mapping[tuple[int, int], Mapping[str, Any]],
    packet_id: str,
    rescue_by_key: Mapping[tuple[str, int], Mapping[str, Any]],
) -> dict[str, Any]:
    source_role = row.get("role")
    values = row.get("values")
    label = row.get("label_match")
    if type(source_role) is not str or type(values) is not list or type(label) is not dict:
        raise _unresolved("loan-currency numeric row structure drifted")
    observed = {value.get("column_ordinal"): value for value in values if type(value) is dict}
    if any(type(lane) is not int for lane in observed) or len(observed) != len(values):
        raise _unresolved("loan-currency numeric row lane identity repeats")
    cells = []
    for lane in range(2):
        if lane in observed:
            cells.append(
                _observed_cell(
                    observed[lane],
                    role=output_role,
                    lane=lane,
                    lookup=lookup,
                    packet_id=packet_id,
                )
            )
        else:
            rescue = rescue_by_key.get((source_role, lane))
            if rescue is None:
                raise _unresolved(f"loan-currency {source_role} lane {lane} is not observed")
            cells.append(_missing_pixel_cell(rescue, lane=lane))
    return {
        "cells": cells,
        "label_surface": label["surface"],
        "role": output_role,
    }


def _trailing_row(
    row: Mapping[str, Any],
    *,
    output_role: str,
    label_surface: str,
    lookup: Mapping[tuple[int, int], Mapping[str, Any]],
    packet_id: str,
) -> dict[str, Any]:
    values = row.get("values")
    if (
        row.get("status") != "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
        or type(values) is not list
        or any(type(value) is not dict for value in values)
        or any(type(value.get("column_ordinal")) is not int for value in values)
        or [value.get("column_ordinal") for value in values] != [0, 1]
    ):
        raise _unresolved("loan-currency trailing printed total row drifted")
    return {
        "cells": [
            _observed_cell(
                value,
                role=output_role,
                lane=lane,
                lookup=lookup,
                packet_id=packet_id,
            )
            for lane, value in enumerate(values)
        ],
        "label_surface": label_surface,
        "role": output_role,
    }


def _numeric_source(
    packet: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    row_axis: Mapping[str, Any],
    context: Mapping[str, Any],
    closure: Mapping[str, Any],
    owner: Mapping[str, Any],
    overlay: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], str, str]:
    pages = snapshot["joined_pages"]
    lookup = _line_lookup(pages)
    period, unit, period_mode, unit_mode = _bound_column_context(context, pages)
    rows = {row["role"]: row for row in row_axis["rows"]}
    if len(rows) != len(row_axis["rows"]):
        raise _unresolved("loan-currency row roles repeat")
    rescue_cells = [] if overlay is None else overlay["rescue_cells"]
    rescue_by_key = {(cell["role"], cell["column_ordinal"]): cell for cell in rescue_cells}
    if len(rescue_by_key) != len(rescue_cells):
        raise _unresolved("loan-currency pixel rescue role/lane repeats")
    mapped = [
        _numeric_row(
            rows[role],
            output_role=role,
            lookup=lookup,
            packet_id=packet["packet_id"],
            rescue_by_key=rescue_by_key,
        )
        for role in _MAPPED_ROLES
    ]
    trailing = row_axis.get("trailing_value_rows")
    if type(trailing) is not list or len(trailing) != 1:
        raise _unresolved("loan-currency source lacks one unique printed total row")
    additional_present = any(role in rows for role in _ADDITIONAL_ROLES)
    if additional_present:
        if not all(role in rows for role in ("CORE_TOTAL_GROUP", *_ADDITIONAL_ROLES)):
            raise _unresolved("loan-currency additional population is structurally incomplete")
        core = _numeric_row(
            rows["CORE_TOTAL_GROUP"],
            output_role="CORE_TOTAL",
            lookup=lookup,
            packet_id=packet["packet_id"],
            rescue_by_key=rescue_by_key,
        )
        additional = {
            "breakdown_rows": [
                _numeric_row(
                    rows[role],
                    output_role=role,
                    lookup=lookup,
                    packet_id=packet["packet_id"],
                    rescue_by_key=rescue_by_key,
                )
                for role in _ADDITIONAL_ROLES[1:]
            ],
            "parent": _numeric_row(
                rows[_ADDITIONAL_ROLES[0]],
                output_role=_ADDITIONAL_ROLES[0],
                lookup=lookup,
                packet_id=packet["packet_id"],
                rescue_by_key=rescue_by_key,
            ),
        }
        grand = _trailing_row(
            trailing[0],
            output_role="GRAND_TOTAL",
            label_surface="Dòng tổng cộng nhìn thấy không có nhãn riêng",
            lookup=lookup,
            packet_id=packet["packet_id"],
        )
    else:
        if "CORE_TOTAL_GROUP" in rows or any(role in rows for role in _ADDITIONAL_ROLES):
            raise _unresolved("loan-currency core-only presentation has a partial group")
        core = _trailing_row(
            trailing[0],
            output_role="CORE_TOTAL",
            label_surface="Dòng tổng dư nợ nhìn thấy không có nhãn riêng",
            lookup=lookup,
            packet_id=packet["packet_id"],
        )
        additional = None
        grand = None
    source_material = {
        "column_context_id": context["column_context_id"],
        "hierarchical_closure_id": closure["closure_id"],
        "owner_binding_id": owner["owner_binding_id"],
        "packet_id": packet["packet_id"],
        "pixel_overlay_evidence_id": None if overlay is None else overlay["evidence_id"],
        "row_axis_id": row_axis["row_axis_id"],
        "snapshot_id": snapshot["snapshot_id"],
    }
    source = {
        "additional_population": additional,
        "core_total": core,
        "family_id": graph_v2.FAMILY_ID,
        "format_version": numeric_v1.INPUT_FORMAT_VERSION,
        "grand_total": grand,
        "lane_types": ["MONEY", "MONEY"],
        "mapped_rows": mapped,
        "period_axis": period,
        "source_id": "lc140v1:source:" + canonical_json_sha256_v1(source_material),
        "unit_context": unit,
    }
    return source, period_mode, unit_mode


def _full_positive_snapshot(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    packet: Mapping[str, Any],
    region: Mapping[str, Any],
) -> dict[str, Any]:
    target_page = region["page_sequence"]
    snapshot = store_v1.read_authenticated_family_first_document_evidence_snapshot_v1(
        capability,
        document_ordinal=packet["document_ordinal"],
        selected_pages=(target_page,),
    )
    pages = snapshot.get("joined_pages")
    if (
        not same_typed_json_v1(snapshot.get("document_packet"), packet)
        or type(pages) is not list
        or not pages
        or [page.get("page_sequence") for page in pages]
        != sorted(page.get("page_sequence") for page in pages)
        or len({page.get("page_sequence") for page in pages}) != len(pages)
        or sum(len(page.get("lines", [])) for page in pages) != packet["line_count"]
        or len(pages) > packet["page_count"]
        or not any(
            page.get("page_sequence") == target_page and type(page.get("page_width")) is int
            for page in pages
        )
        or any(
            page.get("page_sequence") != target_page and page.get("page_width") is not None
            for page in pages
        )
    ):
        raise _unresolved("loan-currency positive full-axis snapshot drifted")
    return snapshot


def _structural_work(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    packet: Mapping[str, Any],
    scan: Mapping[str, Any],
) -> dict[str, Any]:
    region = _candidate_region(scan, packet)
    snapshot = _full_positive_snapshot(capability, packet, region)
    pages = snapshot["joined_pages"]
    try:
        row_axis = row_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
            pages,
            graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2,
            scan,
            region,
        )
        context = column_v1._build_accounting_family_column_context_from_authenticated_row_axis_v1(
            row_axis,
            pages,
            graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2,
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=["MONEY", "MONEY"],
        )
        closure = (
            closure_v1._build_accounting_hierarchical_table_closure_from_authenticated_row_axis_v1(
                row_axis,
                pages,
                graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2,
                graph_v2.LOAN_CURRENCY_HIERARCHY_SPEC_V2,
            )
        )
    except (ValueError, RuntimeError) as exc:
        raise _unresolved("loan-currency shared structural graph cannot replay") from exc
    if (
        row_axis.get("topology_scan_id") != scan["scan_id"]
        or context.get("row_axis_id") != row_axis.get("row_axis_id")
        or closure.get("row_axis_id") != row_axis.get("row_axis_id")
        or closure.get("metrics", {}).get("derived_role_count") != 0
    ):
        raise _unresolved("loan-currency structural packet identities or no-derive gate drifted")
    owner = _owner_binding(row_axis, pages)
    overlay = None
    renders: tuple[dict[str, Any], ...] = ()
    replay_material: tuple[dict[str, Any], ...] = ()
    missing = row_axis.get("metrics", {}).get("missing_lane_count")
    if missing:
        target = region["page_sequence"]
        renders = store_v1.read_authenticated_family_first_document_page_renders_v1(
            capability,
            document_ordinal=packet["document_ordinal"],
            physical_pages=(target,),
        )
        overlay = dash_v1.build_loan_currency_visible_dash_evidence_v1(
            row_axis, scan, pages, renders, packet
        )
        dash_v1.validate_loan_currency_visible_dash_evidence_replay_v1(
            overlay, row_axis, scan, pages, renders, packet
        )
        replay_material = dash_v1.read_loan_currency_dash_cell_replay_material_v1(
            overlay, row_axis, scan, pages, renders, packet
        )
        if len(replay_material) != missing:
            raise _unresolved("loan-currency pixel replay material does not close detector holes")
    elif row_axis.get("status") != "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY":
        raise _unresolved("loan-currency row axis is incomplete without a detector hole")
    return {
        "closure": closure,
        "column_context": context,
        "document": canonical_clone_v1(packet),
        "owner_binding": owner,
        "pixel_overlay": overlay,
        "region": region,
        "render_snapshots": renders,
        "replay_material": replay_material,
        "row_axis": row_axis,
        "snapshot": snapshot,
        "topology_scan": canonical_clone_v1(scan),
    }


def _direct_dash_binding(material: Mapping[str, Any]) -> dict[str, Any]:
    if material.get("admission_class") != "DIRECT_VISIBLE_HORIZONTAL_DASH":
        raise _error("loan-currency direct dash projection received a non-direct mark")
    return {
        "cell_id": material["cell_id"],
        "crop_png_bytes": bytes(material["crop_png_bytes"]),
        "evidence": canonical_clone_v1(material["evidence"]),
        "lane_index": material["lane_index"],
        "lane_type": material["lane_type"],
        "page_sequence": material["page_sequence"],
        "region_id": material["region_id"],
        "role": material["role"],
    }


def _mapping_rows(evidence: Mapping[str, Any], schema: Mapping[str, Any]) -> list[dict[str, Any]]:
    nodes = {item["role"]: item for item in schema["mapped_roles"]}
    periods = evidence.get("period_axis", {}).get("periods")
    if type(periods) is not list or len(periods) != 2:
        raise _unresolved("loan-currency mapping period axis drifted")
    mappings = []
    for row in evidence["mapped_rows"]:
        node = nodes.get(row["role"])
        cells = row.get("cells")
        if (
            node is None
            or type(cells) is not list
            or len(cells) != 2
            or any(
                cell.get("status") != "RESOLVED_OBSERVED_VALUE"
                or type(cell.get("selected_value")) is not int
                for cell in cells
            )
        ):
            raise _unresolved("loan-currency bounded mapping retains an unresolved child")
        mappings.append(
            {
                "canonical_name": node["canonical_name"],
                "period_axis": canonical_clone_v1(periods),
                "report_norm_id": node["report_norm_id"],
                "role": row["role"],
                "schema_projection_id": schema["projection_id"],
                "source_label": row["label_surface"],
                "status": "VERIFIED_BY_CODEX",
                "value_cells": canonical_clone_v1(cells),
                "values": [cell["selected_value"] for cell in cells],
            }
        )
    if [item["report_norm_id"] for item in mappings] != [757, 758]:
        raise _error("loan-currency bounded schema identities/order drifted")
    return mappings


def _absence_trial(packet: Mapping[str, Any], scan: Mapping[str, Any]) -> dict[str, Any]:
    if (
        scan.get("status") != _ABSENCE_STATUS
        or scan.get("regions") != []
        or scan.get("metrics", {}).get("complete_region_count") != 0
        or scan.get("metrics", {}).get("near_region_count") != 0
    ):
        raise _error("loan-currency bounded absence topology drifted")
    return {
        "column_context": None,
        "document": canonical_clone_v1(packet),
        "hierarchical_closure": None,
        "mapped_children": [],
        "numeric_evidence": None,
        "numeric_input": None,
        "owner_binding": None,
        "pixel_dash_evidence": None,
        "row_axis": None,
        "source_hydration": None,
        "status": "VERIFIED_BOUNDED_ABSENCE",
        "topology_scan_id": scan["scan_id"],
        "unresolved_reasons": [],
    }


def _presence_trial(
    work: Mapping[str, Any],
    schema: Mapping[str, Any],
    pair_bindings: Sequence[Mapping[str, Any]],
    replay_by_cell: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    packet = work["document"]
    overlay = work["pixel_overlay"]
    source, period_mode, unit_mode = _numeric_source(
        packet,
        work["snapshot"],
        work["row_axis"],
        work["column_context"],
        work["closure"],
        work["owner_binding"],
        overlay,
    )
    current_material = work["replay_material"]
    direct = [
        _direct_dash_binding(item)
        for item in current_material
        if item["admission_class"] == "DIRECT_VISIBLE_HORIZONTAL_DASH"
    ]
    candidate_ids = {
        item["cell_id"]
        for item in current_material
        if item["admission_class"] == "BOUNDED_CENTERED_HIGH_FILL_HORIZONTAL_MARK_CANDIDATE"
    }
    paired = []
    for pair in pair_bindings:
        candidate_id = pair["candidate_cell_id"]
        if candidate_id not in candidate_ids:
            continue
        candidate = replay_by_cell.get(candidate_id)
        peer = replay_by_cell.get(pair["peer_cell_id"])
        if candidate is None or peer is None:
            raise _unresolved("loan-currency bounded pixel pair lost replay material")
        paired.append(
            {
                "candidate": candidate,
                "pair_binding": canonical_clone_v1(pair),
                "peer": peer,
            }
        )
    if len(paired) != len(candidate_ids):
        raise _unresolved("loan-currency bounded pixel candidate lacks one exact peer")
    numeric = numeric_v1.build_loan_currency_numeric_reconciliation_v1(
        source,
        bounded_dash_peer_evidence=paired,
        visible_dash_evidence=direct,
    )
    numeric_v1.validate_loan_currency_numeric_reconciliation_replay_v1(
        numeric,
        source,
        bounded_dash_peer_evidence=paired,
        visible_dash_evidence=direct,
    )
    if numeric["status"] != "EXACT_OBSERVED_NUMERIC_RECONCILIATION":
        raise _unresolved(";".join(numeric["unresolved_reasons"]))
    mappings = _mapping_rows(numeric, schema)
    snapshot = work["snapshot"]
    packet_page_count = packet["page_count"]
    joined_page_count = len(snapshot["joined_pages"])
    return {
        "column_context": canonical_clone_v1(work["column_context"]),
        "document": canonical_clone_v1(packet),
        "hierarchical_closure": canonical_clone_v1(work["closure"]),
        "mapped_children": mappings,
        "numeric_evidence": canonical_clone_v1(numeric),
        "numeric_input": canonical_clone_v1(source),
        "owner_binding": canonical_clone_v1(work["owner_binding"]),
        "period_mode": period_mode,
        "pixel_dash_evidence": canonical_clone_v1(overlay),
        "row_axis": canonical_clone_v1(work["row_axis"]),
        "source_hydration": {
            "full_joined_axis_line_count": packet["line_count"],
            "full_joined_axis_nonempty_page_count": joined_page_count,
            "packet_page_count": packet_page_count,
            "registered_zero_line_page_count": packet_page_count - joined_page_count,
            "render_ids": [item["render_id"] for item in work["render_snapshots"]],
            "selected_region_page": work["region"]["page_sequence"],
            "snapshot_id": snapshot["snapshot_id"],
        },
        "status": "VERIFIED_BY_CODEX",
        "topology_scan_id": work["topology_scan"]["scan_id"],
        "unit_mode": unit_mode,
        "unresolved_reasons": [],
    }


def _counter(values: Sequence[str], expected: Mapping[str, int], label: str) -> dict[str, int]:
    observed = Counter(values)
    normalized = {key: observed[key] for key in expected}
    if normalized != dict(expected) or set(observed) - set(expected):
        raise _error(f"loan-currency terminal {label} distribution drifted: {dict(observed)}")
    return normalized


def _validate_owner_binding(value: Any) -> dict[str, Any]:
    fields = {
        "mode",
        "owner_binding_id",
        "page_sequence",
        "role",
        "sample_ids",
        "source_line_indices",
        "surface",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["mode"] not in _TARGET_OWNER_COUNTS
        or value["role"] != "CUSTOMER_LOANS_OWNER"
        or type(value["page_sequence"]) is not int
        or value["page_sequence"] <= 0
        or type(value["sample_ids"]) is not list
        or not value["sample_ids"]
        or any(type(item) is not str or not item for item in value["sample_ids"])
        or type(value["source_line_indices"]) is not list
        or len(value["source_line_indices"]) != len(value["sample_ids"])
        or any(type(item) is not int or item < 0 for item in value["source_line_indices"])
        or type(value["surface"]) is not str
        or not value["surface"]
    ):
        raise _error("loan-currency owner binding contract drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("owner_binding_id")
    if identity != "lc140v1:owner:" + canonical_json_sha256_v1(material):
        raise _error("loan-currency owner binding identity drifted")
    return canonical_clone_v1(value)


def _validate_implementation_inputs(inputs: Mapping[str, Any]) -> None:
    refs = inputs.get("implementation_refs")
    if type(refs) is not dict or set(refs) != {path.as_posix() for path in _IMPLEMENTATION_PATHS}:
        raise _error("loan-currency implementation reference axis drifted")
    for path, reference in refs.items():
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
            raise _error("loan-currency implementation reference drifted")
    for path, digest in _PINNED_FROZEN_SHA256.items():
        if refs[path]["sha256"] != digest:
            raise _error(f"frozen loan-currency dependency drifted: {path}")


def _validate_inputs(value: Any) -> dict[str, Any]:
    fields = {
        "bounded_dash_peer_binding_ids",
        "bounded_schema_projection",
        "document_evidence_store",
        "evaluation_spec_sha256",
        "hierarchy_spec_sha256",
        "implementation_refs",
        "positive_document_packet_ids",
        "topology_scan_ids",
        "topology_spec_sha256",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("loan-currency terminal input fields drifted")
    schema_v1.validate_loan_currency_bounded_schema_projection_v1(
        value["bounded_schema_projection"]
    )
    store = value["document_evidence_store"]
    if (
        type(store) is not dict
        or set(store)
        != {"authority", "format_version", "input_indices", "manifest_id", "metrics", "state"}
        or type(store["metrics"]) is not dict
        or store["metrics"]
        != {
            "document_count": _TARGET_DOCUMENT_COUNT,
            "line_count": 667_224,
            "page_count": 8_947,
        }
        or store["format_version"] != store_v1.FORMAT_VERSION
        or store["authority"] != store_v1._AUTHORITY
        or store["state"] != "FULL_AUDIT_DOCUMENT_EVIDENCE_ROOTS_SEALED"
        or type(store["manifest_id"]) is not str
        or not store["manifest_id"].startswith("ffdesv1:manifest:")
        or type(store["input_indices"]) is not dict
        or set(store["input_indices"])
        != {"numeric_axis_sha256", "numeric_receipt_id", "semantic_index_id"}
    ):
        raise _error("loan-currency authenticated store projection drifted")
    indices = store["input_indices"]
    if (
        type(indices["numeric_axis_sha256"]) is not str
        or len(indices["numeric_axis_sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in indices["numeric_axis_sha256"])
        or type(indices["numeric_receipt_id"]) is not str
        or not indices["numeric_receipt_id"]
        or type(indices["semantic_index_id"]) is not str
        or not indices["semantic_index_id"]
    ):
        raise _error("loan-currency authenticated store index identity drifted")
    expected_hashes = {
        "topology_spec_sha256": canonical_json_sha256_v1(graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2),
        "hierarchy_spec_sha256": canonical_json_sha256_v1(graph_v2.LOAN_CURRENCY_HIERARCHY_SPEC_V2),
        "evaluation_spec_sha256": canonical_json_sha256_v1(
            graph_v2.LOAN_CURRENCY_EVALUATION_SPEC_V2
        ),
    }
    if any(value[key] != digest for key, digest in expected_hashes.items()):
        raise _error("loan-currency graph specification identity drifted")
    if (
        type(value["topology_scan_ids"]) is not list
        or len(value["topology_scan_ids"]) != _TARGET_DOCUMENT_COUNT
        or any(
            type(item) is not str or not item.startswith("aftv1:scan:")
            for item in value["topology_scan_ids"]
        )
        or type(value["positive_document_packet_ids"]) is not list
        or len(value["positive_document_packet_ids"]) != _TARGET_PRESENCE_COUNT
        or len(set(value["positive_document_packet_ids"])) != _TARGET_PRESENCE_COUNT
        or any(type(item) is not str or not item for item in value["positive_document_packet_ids"])
        or type(value["bounded_dash_peer_binding_ids"]) is not list
        or value["bounded_dash_peer_binding_ids"] != sorted(value["bounded_dash_peer_binding_ids"])
        or len(value["bounded_dash_peer_binding_ids"]) != 2
        or len(set(value["bounded_dash_peer_binding_ids"])) != 2
        or any(
            type(item) is not str or not item.startswith("lcdashv1:pair:")
            for item in value["bounded_dash_peer_binding_ids"]
        )
    ):
        raise _error("loan-currency scan/positive/pixel-pair input axis drifted")
    _validate_implementation_inputs(value)
    return canonical_clone_v1(value)


def _validate_presence_trial(trial: Mapping[str, Any], schema: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "column_context",
        "document",
        "hierarchical_closure",
        "mapped_children",
        "numeric_evidence",
        "numeric_input",
        "owner_binding",
        "period_mode",
        "pixel_dash_evidence",
        "row_axis",
        "source_hydration",
        "status",
        "topology_scan_id",
        "unit_mode",
        "unresolved_reasons",
    }
    if (
        type(trial) is not dict
        or set(trial) != fields
        or trial["status"] != "VERIFIED_BY_CODEX"
        or trial["unresolved_reasons"] != []
        or type(trial["topology_scan_id"]) is not str
        or not trial["topology_scan_id"]
    ):
        raise _error("loan-currency verified trial contract drifted")
    try:
        row_axis = row_v1._validate_result(trial["row_axis"])
        context = column_v1._validate_result(trial["column_context"])
        closure = closure_v1._validate_result(trial["hierarchical_closure"])
        numeric = numeric_v1.validate_loan_currency_numeric_reconciliation_v1(
            trial["numeric_evidence"]
        )
        overlay = (
            None
            if trial["pixel_dash_evidence"] is None
            else dash_v1.validate_loan_currency_visible_dash_evidence_v1(
                trial["pixel_dash_evidence"]
            )
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("loan-currency verified trial nested evidence drifted") from exc
    owner = _validate_owner_binding(trial["owner_binding"])
    region = row_axis.get("topology_region")
    anchor = region.get("minimal_unique_anchor") if type(region) is dict else None
    if (
        row_axis.get("topology_scan_id") != trial["topology_scan_id"]
        or context.get("row_axis_id") != row_axis.get("row_axis_id")
        or closure.get("row_axis_id") != row_axis.get("row_axis_id")
        or closure.get("metrics", {}).get("derived_role_count") != 0
        or type(region) is not dict
        or region.get("continuation_page_count") != 0
        or type(anchor) is not dict
        or anchor.get("combination_size") != 2
        or anchor.get("pair_before_triple_search") is not True
        or owner["page_sequence"] != region.get("page_sequence")
    ):
        raise _error("loan-currency verified structural identities drifted")
    if (
        numeric.get("status") != "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
        or numeric.get("unresolved_reasons") != []
        or not same_typed_json_v1(numeric_v1._source_from_result(numeric), trial["numeric_input"])
        or not same_typed_json_v1(_mapping_rows(numeric, schema), trial["mapped_children"])
    ):
        raise _error("loan-currency verified numeric/mapping replay drifted")
    numeric_source = trial["numeric_input"]
    if (
        numeric_source.get("period_axis", {}).get("column_context_id")
        != context.get("column_context_id")
        or numeric_source.get("period_axis", {}).get("periods") != context.get("period_axis")
        or numeric_source.get("unit_context", {}).get("column_context_id")
        != context.get("column_context_id")
        or numeric_source.get("unit_context", {}).get("units") != context.get("unit_axis")
        or trial["period_mode"] != numeric_source.get("period_axis", {}).get("mode")
        or trial["unit_mode"] != numeric_source.get("unit_context", {}).get("mode")
        or not _packet_period_corroborates_pdf_axis(trial["document"], context.get("period_axis"))
    ):
        raise _error("loan-currency verified period/unit binding drifted")
    hydration = trial["source_hydration"]
    if (
        type(hydration) is not dict
        or set(hydration)
        != {
            "full_joined_axis_line_count",
            "full_joined_axis_nonempty_page_count",
            "packet_page_count",
            "registered_zero_line_page_count",
            "render_ids",
            "selected_region_page",
            "snapshot_id",
        }
        or type(hydration["full_joined_axis_line_count"]) is not int
        or hydration["full_joined_axis_line_count"] != trial["document"]["line_count"]
        or type(hydration["packet_page_count"]) is not int
        or hydration["packet_page_count"] != trial["document"]["page_count"]
        or type(hydration["full_joined_axis_nonempty_page_count"]) is not int
        or type(hydration["registered_zero_line_page_count"]) is not int
        or hydration["full_joined_axis_nonempty_page_count"]
        + hydration["registered_zero_line_page_count"]
        != hydration["packet_page_count"]
        or type(hydration["selected_region_page"]) is not int
        or hydration["selected_region_page"] != region["page_sequence"]
        or type(hydration["snapshot_id"]) is not str
        or not hydration["snapshot_id"]
        or type(hydration["render_ids"]) is not list
        or any(type(item) is not str or not item for item in hydration["render_ids"])
    ):
        raise _error("loan-currency positive full-axis hydration binding drifted")
    overlay_id = None if overlay is None else overlay["evidence_id"]
    expected_source_material = {
        "column_context_id": context["column_context_id"],
        "hierarchical_closure_id": closure["closure_id"],
        "owner_binding_id": owner["owner_binding_id"],
        "packet_id": trial["document"]["packet_id"],
        "pixel_overlay_evidence_id": overlay_id,
        "row_axis_id": row_axis["row_axis_id"],
        "snapshot_id": hydration["snapshot_id"],
    }
    if numeric_source["source_id"] != "lc140v1:source:" + canonical_json_sha256_v1(
        expected_source_material
    ):
        raise _error("loan-currency numeric source provenance identity drifted")
    if overlay is None:
        if hydration["render_ids"] or row_axis.get("metrics", {}).get("missing_lane_count") != 0:
            raise _error("loan-currency no-overlay trial retains a pixel hole or render")
    else:
        render_ids = [item["render_id"] for item in overlay["render_bindings"]]
        if (
            overlay["base_row_axis_id"] != row_axis["row_axis_id"]
            or overlay["topology_scan_id"] != trial["topology_scan_id"]
            or overlay["document_binding"]["packet_id"] != trial["document"]["packet_id"]
            or overlay["column_context_binding"]["column_context_id"]
            != context["column_context_id"]
            or hydration["render_ids"] != render_ids
            or len(render_ids) != 1
            or len(overlay["rescue_cells"]) != row_axis.get("metrics", {}).get("missing_lane_count")
        ):
            raise _error("loan-currency pixel overlay provenance drifted")
    return canonical_clone_v1(trial)


def _terminal_material(
    trials: Sequence[Mapping[str, Any]], inputs: Mapping[str, Any]
) -> dict[str, Any]:
    if type(trials) not in {list, tuple} or len(trials) != _TARGET_DOCUMENT_COUNT:
        raise _error("loan-currency terminal sweep requires exactly 140 trials")
    typed_inputs = _validate_inputs(inputs)
    schema = typed_inputs["bounded_schema_projection"]
    presence_trials = []
    absence_trials = []
    bank_documents = []
    for ordinal, trial in enumerate(trials, 1):
        if type(trial) is not dict or type(trial.get("document")) is not dict:
            raise _error("loan-currency terminal trial/document contract drifted")
        try:
            packet = store_v1._packet(trial["document"], ordinal)
        except ValueError as exc:
            raise _error("loan-currency terminal document packet drifted") from exc
        bank_documents.append(packet["bank_provenance"])
        if trial.get("status") == "VERIFIED_BY_CODEX":
            presence_trials.append(_validate_presence_trial(trial, schema))
            continue
        absence_fields = {
            "column_context",
            "document",
            "hierarchical_closure",
            "mapped_children",
            "numeric_evidence",
            "numeric_input",
            "owner_binding",
            "pixel_dash_evidence",
            "row_axis",
            "source_hydration",
            "status",
            "topology_scan_id",
            "unresolved_reasons",
        }
        if (
            set(trial) != absence_fields
            or trial.get("status") != "VERIFIED_BOUNDED_ABSENCE"
            or trial.get("unresolved_reasons") != []
            or trial.get("mapped_children") != []
            or any(
                trial.get(field) is not None
                for field in (
                    "column_context",
                    "hierarchical_closure",
                    "numeric_evidence",
                    "numeric_input",
                    "owner_binding",
                    "pixel_dash_evidence",
                    "row_axis",
                    "source_hydration",
                )
            )
            or type(trial.get("topology_scan_id")) is not str
            or not trial["topology_scan_id"]
        ):
            raise _error("loan-currency bounded absence trial drifted")
        absence_trials.append(canonical_clone_v1(trial))
    if (
        len(presence_trials) != _TARGET_PRESENCE_COUNT
        or len(absence_trials) != _TARGET_ABSENCE_COUNT
    ):
        raise _error("loan-currency presence/absence denominator drifted")
    if [trial["topology_scan_id"] for trial in trials] != typed_inputs["topology_scan_ids"]:
        raise _error("loan-currency trial/topology source-order binding drifted")
    if [trial["document"]["packet_id"] for trial in presence_trials] != typed_inputs[
        "positive_document_packet_ids"
    ]:
        raise _error("loan-currency positive packet binding drifted")

    mappings = [item for trial in presence_trials for item in trial["mapped_children"]]
    numeric_results = [trial["numeric_evidence"] for trial in presence_trials]
    mapped_id_counts = Counter(item["report_norm_id"] for item in mappings)
    if (
        len(mappings) != _TARGET_MAPPING_COUNT
        or mapped_id_counts != Counter({757: 10, 758: 10})
        or any(item["report_norm_id"] in {716, 756} for item in mappings)
        or sum(len(item["value_cells"]) for item in mappings) != _TARGET_MAPPED_MONEY_CELL_COUNT
    ):
        raise _error("loan-currency terminal bounded mapping counts drifted")

    bank_document_counts = _counter(bank_documents, _TARGET_BANK_DOCUMENT_COUNTS, "bank-document")
    bank_presence_counts = _counter(
        [trial["document"]["bank_provenance"] for trial in presence_trials],
        _TARGET_BANK_PRESENCE_COUNTS,
        "bank-presence",
    )
    bank_absence_counts = _counter(
        [trial["document"]["bank_provenance"] for trial in absence_trials],
        _TARGET_BANK_ABSENCE_COUNTS,
        "bank-absence",
    )
    bank_mapping_counts = Counter()
    for trial in presence_trials:
        bank_mapping_counts[trial["document"]["bank_provenance"]] += len(trial["mapped_children"])
    normalized_bank_mappings = {bank: bank_mapping_counts[bank] for bank in _BANK_ORDER}
    if normalized_bank_mappings != _TARGET_BANK_MAPPING_COUNTS:
        raise _error("loan-currency terminal bank mapping distribution drifted")

    owners = _counter(
        [trial["owner_binding"]["mode"] for trial in presence_trials],
        _TARGET_OWNER_COUNTS,
        "owner",
    )
    periods = _counter(
        [trial["period_mode"] for trial in presence_trials],
        _TARGET_PERIOD_COUNTS,
        "period",
    )
    units = _counter(
        [trial["unit_mode"] for trial in presence_trials],
        _TARGET_UNIT_COUNTS,
        "unit",
    )
    equation_count = sum(len(result["accounting_checks"]) for result in numeric_results)
    if equation_count != _TARGET_EQUATION_COUNT or any(
        check.get("status") != "CORROBORATED_EXACT_OBSERVED_EQUATION"
        for result in numeric_results
        for check in result["accounting_checks"]
    ):
        raise _error("loan-currency terminal observed accounting equations drifted")

    additional_trials = [
        trial
        for trial in presence_trials
        if trial["numeric_evidence"]["additional_population"] is not None
    ]
    overlays = [
        trial["pixel_dash_evidence"]
        for trial in presence_trials
        if trial["pixel_dash_evidence"] is not None
    ]
    rescue_counts = Counter(len(overlay["rescue_cells"]) for overlay in overlays)
    direct_pixel_count = sum(
        cell["admission_class"] == "DIRECT_VISIBLE_HORIZONTAL_DASH"
        for overlay in overlays
        for cell in overlay["rescue_cells"]
    )
    candidate_pixel_count = sum(
        cell["admission_class"] == "BOUNDED_CENTERED_HIGH_FILL_HORIZONTAL_MARK_CANDIDATE"
        for overlay in overlays
        for cell in overlay["rescue_cells"]
    )
    direct_zero_count = sum(
        result["metrics"]["direct_visible_dash_zero_cell_count"] for result in numeric_results
    )
    paired_zero_count = sum(
        result["metrics"]["bounded_paired_dash_zero_cell_count"] for result in numeric_results
    )
    pair_ids = sorted(
        reference["pair_binding"]["pair_binding_id"]
        for result in numeric_results
        for reference in result["bounded_dash_pair_evidence_refs"]
    )
    if (
        len(additional_trials) != 4
        or len(overlays) != 4
        or rescue_counts != Counter({1: 2, 3: 2})
        or direct_pixel_count != 6
        or candidate_pixel_count != 2
        or direct_zero_count != 6
        or paired_zero_count != 2
        or pair_ids != typed_inputs["bounded_dash_peer_binding_ids"]
    ):
        raise _error("loan-currency terminal additional/pixel evidence counts drifted")

    hydration = [trial["source_hydration"] for trial in presence_trials]
    full_pages = sum(item["packet_page_count"] for item in hydration)
    nonempty_pages = sum(item["full_joined_axis_nonempty_page_count"] for item in hydration)
    zero_pages = sum(item["registered_zero_line_page_count"] for item in hydration)
    full_lines = sum(item["full_joined_axis_line_count"] for item in hydration)
    if (
        full_pages != _TARGET_FULL_AXIS_PAGE_COUNT
        or nonempty_pages != _TARGET_FULL_AXIS_NONEMPTY_PAGE_COUNT
        or zero_pages != _TARGET_FULL_AXIS_ZERO_LINE_PAGE_COUNT
        or full_lines != _TARGET_FULL_AXIS_LINE_COUNT
    ):
        raise _error("loan-currency positive full-axis hydration denominator drifted")

    raw_conflicts = sum(
        result["metrics"]["ppocrv6_vietocr_raw_surface_disagreement_count"]
        for result in numeric_results
    )
    numeric_conflicts = sum(
        result["metrics"]["ppocrv6_vietocr_numeric_disagreement_count"]
        for result in numeric_results
    )
    additional_rows = sum(
        result["metrics"]["source_only_additional_row_count"] for result in numeric_results
    )
    additional_cells = sum(
        result["metrics"]["source_only_additional_money_cell_count"] for result in numeric_results
    )
    source_control_rows = sum(
        result["metrics"]["source_control_row_count"] for result in numeric_results
    )
    source_control_cells = sum(
        result["metrics"]["source_control_money_cell_count"] for result in numeric_results
    )
    minimal_pairs = sum(
        trial["row_axis"]["topology_region"]["minimal_unique_anchor"]["combination_size"] == 2
        for trial in presence_trials
    )
    if (
        raw_conflicts != 2
        or numeric_conflicts != 1
        or additional_rows != 12
        or additional_cells != 24
        or source_control_rows != 14
        or source_control_cells != 28
        or minimal_pairs != _TARGET_PRESENCE_COUNT
    ):
        raise _error("loan-currency terminal conflict/source/minimal-pair counts drifted")

    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "inputs": typed_inputs,
        "metrics": {
            "absence_numeric_hydration_count": 0,
            "additional_source_population_document_count": len(additional_trials),
            "additional_source_population_money_cell_count": additional_cells,
            "additional_source_population_row_count": additional_rows,
            "bounded_absence_trial_count": len(absence_trials),
            "bounded_paired_dash_zero_cell_count": paired_zero_count,
            "direct_visible_dash_zero_cell_count": direct_zero_count,
            "document_count": len(trials),
            "full_axis_positive_document_count": len(presence_trials),
            "full_axis_positive_joined_line_count": full_lines,
            "full_axis_positive_nonempty_page_count": nonempty_pages,
            "full_axis_positive_packet_page_count": full_pages,
            "full_axis_positive_registered_zero_line_page_count": zero_pages,
            "mapped_money_cell_count": _TARGET_MAPPED_MONEY_CELL_COUNT,
            "mapped_parent_716_or_756_record_count": 0,
            "mapped_record_count": len(mappings),
            "minimal_unique_two_anchor_region_count": minimal_pairs,
            "numeric_exact_trial_count": len(presence_trials),
            "observed_accounting_equation_count": equation_count,
            "pixel_overlay_document_count": len(overlays),
            "pixel_render_replay_count": sum(
                len(trial["source_hydration"]["render_ids"]) for trial in presence_trials
            ),
            "ppocrv6_vietocr_numeric_disagreement_count": numeric_conflicts,
            "ppocrv6_vietocr_raw_surface_disagreement_count": raw_conflicts,
            "schema_report_norm_id_record_counts": {
                "757": mapped_id_counts[757],
                "758": mapped_id_counts[758],
            },
            "source_control_money_cell_count": source_control_cells,
            "source_control_row_count": source_control_rows,
            "structure_unique_trial_count": len(presence_trials),
            "typed_lane_axis_trial_counts": {"MONEY,MONEY": len(presence_trials)},
            "unresolved_trial_count": 0,
            "verified_trial_count": len(trials),
            "visible_dash_detector_hole_count": direct_pixel_count + candidate_pixel_count,
            "visible_dash_rescue_cell_count_distribution": {
                "1": rescue_counts[1],
                "3": rescue_counts[3],
            },
            "visible_dash_zero_cell_count": direct_zero_count + paired_zero_count,
            "bank_document_counts": bank_document_counts,
            "bank_presence_counts": bank_presence_counts,
            "bank_bounded_absence_counts": bank_absence_counts,
            "bank_mapped_record_counts": normalized_bank_mappings,
            "owner_mode_trial_counts": owners,
            "period_mode_trial_counts": periods,
            "unit_scope_trial_counts": units,
        },
        "state": "COMPLETE",
        "trials": canonical_clone_v1(trials),
    }
    return {**material, "sweep_id": "lc140v1:sweep:" + canonical_json_sha256_v1(material)}


def validate_authenticated_family_first_loan_currency_140_filing_schema_sweep_v1(
    value: Any,
) -> dict[str, Any]:
    """Validate content identities and terminal semantics without granting live authority."""

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
        raise _error("loan-currency sweep result fields drifted")
    rebuilt = _terminal_material(value["trials"], value["inputs"])
    if not same_typed_json_v1(value, rebuilt):
        raise _error("loan-currency sweep terminal semantics drifted")
    return rebuilt


def build_authenticated_family_first_loan_currency_140_filing_schema_sweep_v1(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    project_root: Path,
    *,
    topology_jobs: int = 12,
    _timing_sink: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Build the fixed denominator from direct topology and bounded live evidence."""

    if not isinstance(project_root, Path):
        raise _error("loan-currency sweep project root must be one pathlib Path")
    if _timing_sink is not None and type(_timing_sink) is not dict:
        raise _error("loan-currency timing sink must be one private mutable dictionary")
    build_started = time.perf_counter()
    root = project_root.resolve()
    tracked_git_head = store_v1._clean_head(root)
    implementation_refs = _implementation_refs(root)
    schema_source_refs = _schema_source_refs(root)
    for path, digest in _PINNED_FROZEN_SHA256.items():
        if implementation_refs[path]["sha256"] != digest:
            raise _error(f"frozen loan-currency dependency drifted: {path}")
    store_projection = store_v1.project_authenticated_family_first_document_evidence_store_v1(
        capability
    )
    if store_projection.get("metrics") != {
        "document_count": _TARGET_DOCUMENT_COUNT,
        "line_count": 667_224,
        "page_count": 8_947,
    }:
        raise _error("loan-currency sweep requires the fixed authenticated denominator")
    setup_finished = time.perf_counter()
    scans = store_v1.recompute_authenticated_family_first_topology_scans_v1(
        capability, graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2, jobs=topology_jobs
    )
    if len(scans) != _TARGET_DOCUMENT_COUNT:
        raise _error("direct loan-currency topology scan denominator drifted")
    topology_finished = time.perf_counter()
    packets = [
        store_v1.read_authenticated_family_first_document_packet_v1(
            capability, document_ordinal=ordinal
        )
        for ordinal in range(1, _TARGET_DOCUMENT_COUNT + 1)
    ]
    schema = schema_v1.build_live_loan_currency_bounded_schema_projection_v1(root)
    schema_v1.validate_loan_currency_bounded_schema_projection_v1(schema)
    schema_finished = time.perf_counter()

    entries: list[tuple[str, Mapping[str, Any]]] = []
    works = []
    for packet, scan in zip(packets, scans, strict=True):
        if scan.get("status") == _PRESENCE_STATUS:
            work = _structural_work(capability, packet, scan)
            works.append(work)
            entries.append(("PRESENCE", work))
        elif scan.get("status") == _ABSENCE_STATUS:
            entries.append(("ABSENCE", _absence_trial(packet, scan)))
        else:
            raise _unresolved("loan-currency complete-document topology remains ambiguous")
    if len(works) != _TARGET_PRESENCE_COUNT:
        raise _error("loan-currency direct topology presence count drifted")
    overlays = [work["pixel_overlay"] for work in works if work["pixel_overlay"] is not None]
    pair_bindings = dash_v1.build_loan_currency_bounded_dash_peer_bindings_v1(overlays)
    replay_by_cell = {}
    for work in works:
        for item in work["replay_material"]:
            cell_id = item["cell_id"]
            if cell_id in replay_by_cell:
                raise _error("loan-currency corpus pixel replay cell identities repeat")
            replay_by_cell[cell_id] = item
    trials = [
        _presence_trial(item, schema, pair_bindings, replay_by_cell)
        if disposition == "PRESENCE"
        else canonical_clone_v1(item)
        for disposition, item in entries
    ]
    positives_finished = time.perf_counter()

    inputs = {
        "bounded_dash_peer_binding_ids": sorted(item["pair_binding_id"] for item in pair_bindings),
        "bounded_schema_projection": schema,
        "document_evidence_store": store_projection,
        "evaluation_spec_sha256": canonical_json_sha256_v1(
            graph_v2.LOAN_CURRENCY_EVALUATION_SPEC_V2
        ),
        "hierarchy_spec_sha256": canonical_json_sha256_v1(graph_v2.LOAN_CURRENCY_HIERARCHY_SPEC_V2),
        "implementation_refs": implementation_refs,
        "positive_document_packet_ids": [work["document"]["packet_id"] for work in works],
        "topology_scan_ids": [scan["scan_id"] for scan in scans],
        "topology_spec_sha256": canonical_json_sha256_v1(graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2),
    }
    result = _terminal_material(trials, inputs)
    post_result_store = store_v1.project_authenticated_family_first_document_evidence_store_v1(
        capability
    )
    if (
        not same_typed_json_v1(store_projection, post_result_store)
        or store_v1._clean_head(root) != tracked_git_head
        or not same_typed_json_v1(schema_source_refs, _schema_source_refs(root))
    ):
        raise _error("loan-currency store, tracked root, or schema source changed during build")
    _assert_implementation_refs_unchanged(root, implementation_refs)
    completed = time.perf_counter()
    if _timing_sink is not None:
        _timing_sink.update(
            {
                "direct_topology_seconds": topology_finished - setup_finished,
                "live_schema_projection_seconds": schema_finished - topology_finished,
                "positive_evidence_numeric_seconds": positives_finished - schema_finished,
                "setup_seconds": setup_finished - build_started,
                "terminal_and_postcondition_seconds": completed - positives_finished,
                "total_seconds": completed - build_started,
            }
        )
    return result


def validate_authenticated_family_first_loan_currency_140_filing_schema_sweep_replay_v1(
    value: Any,
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    project_root: Path,
    *,
    topology_jobs: int = 12,
) -> dict[str, Any]:
    """Rebuild from the same live store/PDF pixels and require exact equality."""

    persisted = validate_authenticated_family_first_loan_currency_140_filing_schema_sweep_v1(value)
    rebuilt = build_authenticated_family_first_loan_currency_140_filing_schema_sweep_v1(
        capability, project_root, topology_jobs=topology_jobs
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-currency 140-filing schema sweep does not replay exactly")
    return rebuilt


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_result(path: Path) -> dict[str, Any]:
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error("persisted loan-currency sweep is not one regular nofollow file")
        if stat.S_IMODE(before.st_mode) != 0o444:
            raise _error("persisted loan-currency sweep mode is not immutable 0444")
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
            raise _error("persisted loan-currency sweep changed during stable read")
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON token: {token}")
            ),
        )
    except FamilyFirstLoanCurrency140FilingSchemaSweepV1Error:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error("persisted loan-currency sweep is not strict JSON") from exc
    if type(value) is not dict or payload != canonical_json_bytes_v1(value) + b"\n":
        raise _error("persisted loan-currency sweep is not canonical JSON plus LF")
    return validate_authenticated_family_first_loan_currency_140_filing_schema_sweep_v1(value)


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
                    raise _error("loan-currency sweep write made no progress")
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
                raise _error("loan-currency sweep destination already exists") from exc
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


def run_family_first_loan_currency_140_filing_schema_sweep_v1(
    project_root: Path, *, command: str, topology_jobs: int = 12
) -> dict[str, Any]:
    if command not in {"build", "verify"}:
        raise _error("loan-currency sweep command drifted")
    root = project_root.resolve()
    output = root / OUTPUT_PATH
    if command == "build" and output.exists():
        raise _error("loan-currency sweep destination already exists")
    persisted = _strict_result(output) if command == "verify" else None
    capability = store_v1.authenticate_family_first_document_evidence_store_v1(root)
    stage_timings: dict[str, float] = {}
    result = build_authenticated_family_first_loan_currency_140_filing_schema_sweep_v1(
        capability, root, topology_jobs=topology_jobs, _timing_sink=stage_timings
    )
    if command == "build":
        _write_exclusive(output, canonical_json_bytes_v1(result) + b"\n")
    elif not same_typed_json_v1(persisted, result):
        raise _error("persisted loan-currency sweep differs from live exact replay")
    return {
        "execution_telemetry": {
            key: round(value, 6) for key, value in sorted(stage_timings.items())
        },
        "metrics": result["metrics"],
        "state": result["state"],
        "sweep_id": result["sweep_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--topology-jobs", type=int, default=12)
    arguments = parser.parse_args()
    print(
        json.dumps(
            run_family_first_loan_currency_140_filing_schema_sweep_v1(
                arguments.project_root,
                command=arguments.command,
                topology_jobs=arguments.topology_jobs,
            ),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
