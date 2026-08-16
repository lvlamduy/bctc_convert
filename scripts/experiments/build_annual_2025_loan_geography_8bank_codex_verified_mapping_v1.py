"""Verify annual-2025 customer-loan geographic disclosures for eight banks.

The shared matcher scans every page and accepts row- or column-oriented tables
only when the accounting axis is exactly customer loans.  This bounded builder
then binds the three unique annual regions to visible pixels, the independently
verified customer-loan owner totals, exact domestic/foreign arithmetic and the
live TM schema.  Broader loan-population tables remain bounded-report absences
for this narrower family; they are never silently relabelled.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    _authority_snapshot,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "Annual2025LoanGeography8BankError",
    "build_live_annual_2025_loan_geography_8bank_codex_verified_mapping_v1",
    "validate_annual_2025_loan_geography_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_LOAN_GEOGRAPHY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_LOAN_GEOGRAPHY_8BANK_CODEX_PIXEL_REVIEW_V1"
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
LOAN_TYPE_RESULT_PATH = Path(
    "docs/experiments/E-0112-annual-2025-loan-type-8bank-codex-verified-mapping-v1.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0117-annual-2025-loan-geography-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0117-annual-2025-loan-geography-8bank-codex-verified-mapping-v1.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_LOAN_TYPE_RESULT_SHA256 = (
    "fdc81e117e5e5e3c89ab6949964d119a6568991963c1b2a805236fed6944f789"
)
EXPECTED_SCAN_ID = "lgfdsv1:scan:4166c011c5b4956ffdb56d74dca27eb3bc595579984232bf93e867ae085ad9de"
EXPECTED_REVIEW_SHA256 = "6ec02e64726d2c1d41aac82d3455842357a4668a05abaa55e266076f7b5d752f"
EXPECTED_DOCUMENT_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
_MAPPED_BANKS = ("ACB", "MBB", "VIB")
_EXPECTED_SEGMENT_PAGES = {"ACB": [77], "MBB": [91], "VIB": [59, 60]}
_EXPECTED_REVIEW_PAGES = {"ACB": [77, 77], "MBB": [91, 91], "VIB": [59, 60]}
_EXPECTED_LAYOUTS = {
    "ACB": "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS",
    "MBB": "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS",
    "VIB": "GEOGRAPHY_COLUMNS_ACCOUNTING_FAMILY_ROWS",
}
_ABSENCE_DISPOSITIONS = {
    "VPB": "VERIFIED_ONLY_BROADER_MIXED_LOAN_GEOGRAPHY_PRESENT",
    "HDB": "VERIFIED_ONLY_BROADER_TOTAL_LOAN_GEOGRAPHY_PRESENT",
    "VCB": "VERIFIED_NO_CUSTOMER_LOAN_GEOGRAPHY_IN_BOUND_REPORT",
    "CTG": "VERIFIED_NO_CUSTOMER_LOAN_GEOGRAPHY_IN_BOUND_REPORT",
    "BID": "VERIFIED_ONLY_BROADER_TOTAL_LOAN_GEOGRAPHY_PRESENT",
}
_EXPECTED_NEAR_COUNTS = {"VPB": 1, "HDB": 1, "VCB": 0, "CTG": 0, "BID": 1}
_SCHEMA_ROWS = {
    759: ("Phân tích theo khu vực địa lý", 716, 212),
    5752: ("+ Trong nước", 759, 213),
    765: ("+ Nước ngoài", 759, 219),
}
_EXPECTED_SCHEMA_SNAPSHOT = {
    "rows": [
        {
            "canonical_name": canonical_name,
            "display_order": display_order,
            "parent_id": parent_id,
            "report_norm_id": report_norm_id,
        }
        for report_norm_id, (canonical_name, parent_id, display_order) in _SCHEMA_ROWS.items()
    ]
}
_CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "SHARED_CUSTOMER_LOAN_GEOGRAPHY_GRAPH_ROW_OR_COLUMN_LAYOUT_WHOLE_PDF_"
    "UNIQUENESS_VISIBLE_PIXEL_DASH_SIGN_PERIOD_UNIT_OWNER_TOTAL_LIVE_TM_SCHEMA_"
    "AND_EXACT_ACCOUNTING_ONLY_NO_BROAD_LOAN_NARROWING_EXPORT_OR_PRODUCTION_"
    "AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "bounded_report_absence_authority": True,
    "broad_corpus_absence_authority": False,
    "broad_total_or_mixed_loan_axis_narrowed_to_customer_loans": False,
    "canonicalization_or_export_authority": False,
    "dash_zero_requires_visible_pixel": True,
    "fresh_vietocr_used_for_semantic_anchors": True,
    "gemma_json_structure_proposal_used_as_mapping_authority": False,
    "independent_visible_pixels_and_owner_totals_used_for_numbers": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
}


class Annual2025LoanGeography8BankError(ValueError):
    """The annual geography review, graph, owner, schema or result drifted."""


def _error(message: str) -> Annual2025LoanGeography8BankError:
    return Annual2025LoanGeography8BankError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _strict_json(payload: bytes, label: str) -> Any:
    def reject_constant(value: str) -> None:
        raise _error(f"{label} contains non-finite JSON: {value}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _error(f"{label} contains duplicate key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(
            payload,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _error(f"{label} is not strict UTF-8 JSON") from error


def _fixed_bytes(path: Path, expected_sha256: str) -> bytes:
    absolute = path if path.is_absolute() else PROJECT_ROOT / path
    before = absolute.stat()
    payload = absolute.read_bytes()
    after = absolute.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise _error(f"fixed artifact changed while reading: {path}")
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed artifact SHA-256 drifted: {path}")
    return payload


def _document(value: Mapping[str, Any], bank: str) -> dict[str, Any]:
    documents = value.get("documents")
    if type(documents) is not list:
        raise _error("document collection drifted")
    matches = [item for item in documents if type(item) is dict and item.get("bank_code") == bank]
    if len(matches) != 1:
        raise _error(f"expected one {bank} document")
    return matches[0]


def _page(document: Mapping[str, Any], physical_page: int) -> dict[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error("document page collection drifted")
    matches = [
        item for item in pages if type(item) is dict and item.get("physical_page") == physical_page
    ]
    if len(matches) != 1:
        raise _error(f"expected one physical page {physical_page}")
    return matches[0]


def _event(
    semantic_index: Mapping[str, Any], bank: str, locator: tuple[int, int]
) -> dict[str, Any]:
    physical_page, source_line_index = locator
    page = _page(_document(semantic_index, bank), physical_page)
    lines = page.get("lines")
    if type(lines) is not list or not 0 <= source_line_index < len(lines):
        raise _error(f"{bank} review locator drifted")
    line = lines[source_line_index]
    if type(line) is not dict or line.get("source_line_index") != source_line_index:
        raise _error(f"{bank} review line axis drifted")
    crop_ref = line.get("crop_ref")
    if type(crop_ref) is not dict:
        raise _error(f"{bank} review crop ref drifted")
    return {
        "bbox": canonical_clone_v1(line["source_bbox_raw_pixels"]),
        "crop_ref": canonical_clone_v1(crop_ref),
        "physical_page": physical_page,
        "source_line_index": source_line_index,
        "vietocr_text": line["vietocr_text"],
    }


def _events(
    semantic_index: Mapping[str, Any], bank: str, locators: Sequence[tuple[int, int]]
) -> list[dict[str, Any]]:
    return [_event(semantic_index, bank, locator) for locator in locators]


def _render_ref(manifest: Mapping[str, Any], bank: str, physical_page: int) -> dict[str, Any]:
    page = _page(_document(manifest, bank), physical_page)
    binding = page.get("render_binding")
    if type(binding) is not dict:
        raise _error(f"{bank} page render binding drifted")
    return canonical_clone_v1(binding)


def _review_cell(
    semantic_index: Mapping[str, Any],
    bank: str,
    physical_page: int,
    role: str,
    label_index: int,
    pixel_label: str,
    pixel_value: str,
    *,
    value_index: int | None,
    dash_bbox: Sequence[int] | None = None,
) -> dict[str, Any]:
    if value_index is None:
        if (
            pixel_value != "-"
            or type(dash_bbox) not in {list, tuple}
            or len(dash_bbox) != 4
            or any(type(item) is not int for item in dash_bbox)
        ):
            raise _error("pixel-only dash review drifted")
        value_event = None
        transformer_value = None
    else:
        value_event = _event(semantic_index, bank, (physical_page, value_index))
        transformer_value = value_event["vietocr_text"]
        dash_bbox = None
    return {
        "dash_pixel_bbox": None if dash_bbox is None else list(dash_bbox),
        "label_event": _event(semantic_index, bank, (physical_page, label_index)),
        "pixel_label": pixel_label,
        "pixel_value": pixel_value,
        "role": role,
        "transformer_value": transformer_value,
        "value_event": value_event,
    }


def _review_period(
    semantic_index: Mapping[str, Any],
    manifest: Mapping[str, Any],
    bank: str,
    physical_page: int,
    period: str,
    period_index: int,
    heading_indices: Sequence[int],
    loan_axis_indices: Sequence[int],
    unit_index: int,
    domestic: Mapping[str, Any],
    foreign: Mapping[str, Any],
    total_index: int,
    total_pixel_value: str,
) -> dict[str, Any]:
    return {
        "cells": [canonical_clone_v1(domestic), canonical_clone_v1(foreign)],
        "heading_events": _events(
            semantic_index, bank, [(physical_page, index) for index in heading_indices]
        ),
        "loan_axis_events": _events(
            semantic_index, bank, [(physical_page, index) for index in loan_axis_indices]
        ),
        "period": period,
        "period_event": _event(semantic_index, bank, (physical_page, period_index)),
        "physical_page": physical_page,
        "render_ref": _render_ref(manifest, bank, physical_page),
        "total_event": _event(semantic_index, bank, (physical_page, total_index)),
        "total_pixel_value": total_pixel_value,
        "unit_event": _event(semantic_index, bank, (physical_page, unit_index)),
    }


def _mapped_reviews(
    semantic_index: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    acb = [
        _review_period(
            semantic_index,
            manifest,
            "ACB",
            77,
            "2025-12-31",
            6,
            (5,),
            (12, 19),
            27,
            _review_cell(
                semantic_index,
                "ACB",
                77,
                "DOMESTIC",
                34,
                "Trong nước",
                "686.777.352",
                value_index=36,
            ),
            _review_cell(
                semantic_index,
                "ACB",
                77,
                "FOREIGN",
                43,
                "Nước ngoài",
                "-",
                value_index=None,
                dash_bbox=[780, 684, 945, 720],
            ),
            51,
            "686.777.352",
        ),
        _review_period(
            semantic_index,
            manifest,
            "ACB",
            77,
            "2024-12-31",
            58,
            (5,),
            (64, 71),
            79,
            _review_cell(
                semantic_index,
                "ACB",
                77,
                "DOMESTIC",
                86,
                "Trong nước",
                "580.686.248",
                value_index=88,
            ),
            _review_cell(
                semantic_index,
                "ACB",
                77,
                "FOREIGN",
                95,
                "Nước ngoài",
                "-",
                value_index=None,
                dash_bbox=[778, 1117, 942, 1152],
            ),
            102,
            "580.686.248",
        ),
    ]
    mbb = [
        _review_period(
            semantic_index,
            manifest,
            "MBB",
            91,
            "2025-12-31",
            11,
            (10,),
            (13, 18),
            23,
            _review_cell(
                semantic_index,
                "MBB",
                91,
                "DOMESTIC",
                29,
                "Trong nước",
                "1.074.688.741",
                value_index=30,
            ),
            _review_cell(
                semantic_index,
                "MBB",
                91,
                "FOREIGN",
                36,
                "Nước ngoài",
                "9.330.629",
                value_index=37,
            ),
            41,
            "1.084.019.370",
        ),
        _review_period(
            semantic_index,
            manifest,
            "MBB",
            91,
            "2024-12-31",
            47,
            (10,),
            (49, 54),
            59,
            _review_cell(
                semantic_index,
                "MBB",
                91,
                "DOMESTIC",
                65,
                "Trong nước",
                "769.363.498",
                value_index=66,
            ),
            _review_cell(
                semantic_index,
                "MBB",
                91,
                "FOREIGN",
                72,
                "Nước ngoài",
                "7.294.348",
                value_index=73,
            ),
            77,
            "776.657.846",
        ),
    ]
    vib = [
        _review_period(
            semantic_index,
            manifest,
            "VIB",
            59,
            "2025-12-31",
            11,
            (5, 6),
            (25,),
            10,
            _review_cell(
                semantic_index,
                "VIB",
                59,
                "DOMESTIC",
                7,
                "Trong nước",
                "381.972.016",
                value_index=26,
            ),
            _review_cell(
                semantic_index,
                "VIB",
                59,
                "FOREIGN",
                8,
                "Nước ngoài",
                "-",
                value_index=None,
                dash_bbox=[1097, 618, 1249, 653],
            ),
            27,
            "381.972.016",
        ),
        _review_period(
            semantic_index,
            manifest,
            "VIB",
            60,
            "2024-12-31",
            13,
            (5, 6),
            (29,),
            10,
            _review_cell(
                semantic_index,
                "VIB",
                60,
                "DOMESTIC",
                7,
                "Trong nước",
                "324.009.713",
                value_index=30,
            ),
            _review_cell(
                semantic_index,
                "VIB",
                60,
                "FOREIGN",
                8,
                "Nước ngoài",
                "-",
                value_index=None,
                dash_bbox=[1097, 701, 1249, 735],
            ),
            31,
            "324.009.713",
        ),
    ]
    return {
        "ACB": {
            "bank_code": "ACB",
            "layout": _EXPECTED_LAYOUTS["ACB"],
            "next_family_boundary_event": _event(semantic_index, "ACB", (78, 4)),
            "periods": acb,
            "status": "PIXEL_REVIEW_COMPLETE",
        },
        "MBB": {
            "bank_code": "MBB",
            "layout": _EXPECTED_LAYOUTS["MBB"],
            "next_family_boundary_event": _event(semantic_index, "MBB", (92, 9)),
            "periods": mbb,
            "status": "PIXEL_REVIEW_COMPLETE",
        },
        "VIB": {
            "bank_code": "VIB",
            "layout": _EXPECTED_LAYOUTS["VIB"],
            "next_family_boundary_event": _event(semantic_index, "VIB", (61, 4)),
            "periods": vib,
            "status": "PIXEL_REVIEW_COMPLETE",
        },
    }


def _absence_review(
    semantic_index: Mapping[str, Any], manifest: Mapping[str, Any], bank: str
) -> dict[str, Any]:
    locators = {
        "VPB": (81, (5, 6), (15, 16), 9, 10),
        "HDB": (60, (8, 9), (14, 19, 42), 29, 35),
        "BID": (63, (4, 5), (6, 10), 22, 28),
    }
    near = None
    if bank in locators:
        physical_page, heading, axis, domestic, foreign = locators[bank]
        near = {
            "domestic_event": _event(semantic_index, bank, (physical_page, domestic)),
            "foreign_event": _event(semantic_index, bank, (physical_page, foreign)),
            "heading_events": _events(
                semantic_index, bank, [(physical_page, index) for index in heading]
            ),
            "loan_axis_events": _events(
                semantic_index, bank, [(physical_page, index) for index in axis]
            ),
            "physical_page": physical_page,
            "render_ref": _render_ref(manifest, bank, physical_page),
        }
    return {
        "bank_code": bank,
        "bounded_report_disposition": _ABSENCE_DISPOSITIONS[bank],
        "near_broader_region": near,
        "report_norm_ids_not_observed": [759, 5752, 765],
        "status": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
    }


def _review_blueprint(
    semantic_index: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    mapped = _mapped_reviews(semantic_index, manifest)
    banks = [
        mapped[bank] if bank in mapped else _absence_review(semantic_index, manifest, bank)
        for bank in EXPECTED_DOCUMENT_ORDER
    ]
    material = {
        "banks": banks,
        "claim_boundary": _CLAIM_BOUNDARY,
        "format_version": REVIEW_FORMAT,
        "review_checks": {
            "all_eight_complete_pdfs_scanned": True,
            "mapped_full_pages_opened": True,
            "owner_children_period_unit_dash_total_and_accounting_checked": True,
            "broader_loan_axes_not_narrowed": True,
            "gemma_full_page_json_is_structure_challenger_only": True,
        },
        "reviewer": {"kind": "CODEX_INDEPENDENT_SOURCE_REVIEW"},
    }
    return {**material, "review_id": "e0117:pixel-review:" + canonical_json_sha256_v1(material)}


def _validate_review(
    value: Any, semantic_index: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    expected = _review_blueprint(semantic_index, manifest)
    if not same_typed_json_v1(value, expected):
        raise _error("annual geography pixel review differs from exact reviewed sources")
    return canonical_clone_v1(expected)


def _money(value: str) -> int:
    token = value.strip().replace(" ", "")
    if token in {"-", "–", "—"}:
        return 0
    negative = token.startswith("(") and token.endswith(")")
    if negative:
        token = token[1:-1]
    compact = token.replace(".", "").replace(",", "")
    if not compact.isdigit():
        raise _error(f"reviewed money is not exact: {value}")
    parsed = int(compact)
    return -parsed if negative else parsed


def _compatible_text(left: str, right: str) -> bool:
    return normalize_vietnamese_anchor_v1(left) == normalize_vietnamese_anchor_v1(right)


def _scan_trial(scan: Mapping[str, Any], bank: str) -> dict[str, Any]:
    matches = [
        trial
        for trial in scan["trials"]
        if type(trial) is dict and trial.get("document_provenance") == bank
    ]
    if len(matches) != 1:
        raise _error(f"annual scan must contain one {bank} trial")
    return matches[0]


def _review_bank(review: Mapping[str, Any], bank: str) -> dict[str, Any]:
    matches = [item for item in review["banks"] if item.get("bank_code") == bank]
    if len(matches) != 1:
        raise _error(f"annual review must contain one {bank} record")
    return matches[0]


def _owner_totals(loan_type_result: Mapping[str, Any]) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    trials = loan_type_result.get("trials")
    if type(trials) is not list:
        raise _error("annual loan-type result trials drifted")
    for trial in trials:
        bank = trial.get("bank_provenance")
        total = trial.get("source_only_total")
        values = total.get("values") if type(total) is dict else None
        if type(bank) is not str or type(values) is not list:
            raise _error("annual loan-type owner total drifted")
        money = [
            item.get("normalized_numeric_value")
            for item in values
            if type(item) is dict and item.get("lane_type") == "MONEY"
        ]
        if len(money) != 2 or any(type(item) is not int for item in money):
            raise _error(f"{bank} annual owner total must have two exact money lanes")
        result[bank] = money
    if set(result) != set(EXPECTED_DOCUMENT_ORDER):
        raise _error("annual loan-type owner total bank set drifted")
    return result


def _schema_snapshot(schema_by_id: Mapping[int, Any]) -> dict[str, Any]:
    rows = []
    for report_norm_id, (canonical_name, parent_id, display_order) in _SCHEMA_ROWS.items():
        item = schema_by_id.get(report_norm_id)
        if (
            item is None
            or item.canonical_name != canonical_name
            or item.parent_id != parent_id
            or item.display_order != display_order
            or item.statement_type != "TM"
            or "CONSOLIDATED" not in item.scope
        ):
            raise _error(f"live TM geography row {report_norm_id} drifted")
        rows.append(
            {
                "canonical_name": canonical_name,
                "display_order": display_order,
                "parent_id": parent_id,
                "report_norm_id": report_norm_id,
            }
        )
    if schema_by_id[759].children != [5752, 765] or schema_by_id[765].next_id != 766:
        raise _error("live TM geography first/last/next boundary drifted")
    return {"rows": rows}


def _mapped_trial(
    bank: str,
    scan_trial: Mapping[str, Any],
    review: Mapping[str, Any],
    owner_totals: Mapping[str, Sequence[int]],
) -> dict[str, Any]:
    matcher = scan_trial["matcher_result"]
    if matcher["status"] != "ACCEPTED_UNIQUE_VARIANT_GRAPH" or len(matcher["regions"]) != 1:
        raise _error(f"{bank} must have exactly one annual geography graph")
    region = matcher["regions"][0]
    segments = region["segments"]
    pages = [segment["heading_match"]["page_sequence"] for segment in segments]
    if pages != _EXPECTED_SEGMENT_PAGES[bank] or any(
        segment["layout"] != _EXPECTED_LAYOUTS[bank] for segment in segments
    ):
        raise _error(f"{bank} annual geography graph pages or layout drifted")
    first_period = review["periods"][0]
    first_segment = segments[0]
    pixel_axis = " ".join(event["vietocr_text"] for event in first_period["loan_axis_events"])
    if (
        not _compatible_text(first_segment["loan_axis"]["surface"], pixel_axis)
        or not _compatible_text(first_segment["domestic"]["surface"], "Trong nước")
        or not _compatible_text(first_segment["foreign"]["surface"], "Nước ngoài")
    ):
        raise _error(f"{bank} annual geography structural anchors drifted")
    role_values: dict[str, list[dict[str, Any]]] = {"DOMESTIC": [], "FOREIGN": []}
    equations = []
    disagreements = []
    for axis, period in enumerate(review["periods"]):
        values: dict[str, int] = {}
        for cell in period["cells"]:
            value = _money(cell["pixel_value"])
            values[cell["role"]] = value
            role_values[cell["role"]].append(
                {
                    "period": period["period"],
                    "pixel_value": cell["pixel_value"],
                    "normalized_value": value,
                    "source_cell_status": "DASH" if cell["pixel_value"] == "-" else "VALUE",
                    "value_event": canonical_clone_v1(cell["value_event"]),
                    "dash_pixel_bbox": canonical_clone_v1(cell["dash_pixel_bbox"]),
                }
            )
            if (
                cell["transformer_value"] is not None
                and cell["transformer_value"] != cell["pixel_value"]
            ):
                disagreements.append(
                    [period["period"], cell["role"], cell["transformer_value"], cell["pixel_value"]]
                )
        computed = values["DOMESTIC"] + values["FOREIGN"]
        total = _money(period["total_pixel_value"])
        if computed != total or total != owner_totals[bank][axis]:
            raise _error(f"{bank} annual geography/owner total equation does not close")
        if period["total_event"]["vietocr_text"] != period["total_pixel_value"]:
            disagreements.append(
                [
                    period["period"],
                    "TOTAL",
                    period["total_event"]["vietocr_text"],
                    period["total_pixel_value"],
                ]
            )
        equations.append(
            {
                "computed_total": computed,
                "customer_loan_owner_total": owner_totals[bank][axis],
                "domestic": values["DOMESTIC"],
                "foreign": values["FOREIGN"],
                "period": period["period"],
                "visible_total": total,
            }
        )
    mapped_items = []
    for role, report_norm_id in (("DOMESTIC", 5752), ("FOREIGN", 765)):
        mapped_items.append(
            {
                "canonical_name": _SCHEMA_ROWS[report_norm_id][0],
                "report_norm_id": report_norm_id,
                "role": role,
                "source_values": canonical_clone_v1(role_values[role]),
                "status": "VERIFIED_BY_CODEX",
            }
        )
    return {
        "accounting_equations": equations,
        "bank_code": bank,
        "graph_id": region["region_id"],
        "layout": review["layout"],
        "mapped_items": mapped_items,
        "next_family_boundary_event": canonical_clone_v1(review["next_family_boundary_event"]),
        "physical_pages": [period["physical_page"] for period in review["periods"]],
        "status": "VERIFIED_BY_CODEX",
        "transformer_disagreements": disagreements,
    }


def _absence_trial(
    bank: str, scan_trial: Mapping[str, Any], review: Mapping[str, Any]
) -> dict[str, Any]:
    matcher = scan_trial["matcher_result"]
    expected_near = _EXPECTED_NEAR_COUNTS[bank]
    if (
        matcher["status"] != "UNRESOLVED_NO_COMPLETE_REGION"
        or matcher["regions"] != []
        or matcher["metrics"]["near_region_count"] != expected_near
        or len(matcher["near_regions"]) != expected_near
    ):
        raise _error(f"{bank} bounded-report geography absence conflicts with full scan")
    if expected_near:
        near = matcher["near_regions"][0]
        if near["axis_scope"] == "EXACT_CUSTOMER_LOANS":
            raise _error(f"{bank} broad geography negative control became exact")
    return {
        "bank_code": bank,
        "bounded_report_disposition": review["bounded_report_disposition"],
        "matcher_result_id": matcher["result_id"],
        "near_broader_region": canonical_clone_v1(review["near_broader_region"]),
        "near_region_count": expected_near,
        "report_norm_ids_not_observed": [759, 5752, 765],
        "status": "VERIFIED_NOT_OBSERVED_IN_BOUND_REPORT",
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    mapped = [trial for trial in trials if trial["status"] == "VERIFIED_BY_CODEX"]
    return {
        "accounting_equation_count": sum(len(trial["accounting_equations"]) for trial in mapped),
        "bounded_report_absence_count": sum(
            trial["status"] == "VERIFIED_NOT_OBSERVED_IN_BOUND_REPORT" for trial in trials
        ),
        "broad_scope_negative_control_count": sum(
            trial.get("near_region_count") == 1 for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_mapping_region_count": len(mapped),
        "mapped_item_verified_by_codex_count": sum(len(trial["mapped_items"]) for trial in mapped),
        "mapped_money_value_cell_count": sum(
            len(item["source_values"]) for trial in mapped for item in trial["mapped_items"]
        ),
        "transformer_numeric_disagreement_count": sum(
            len(trial["transformer_disagreements"]) for trial in mapped
        ),
        "unresolved_mapping_count": 0,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    fields = {
        "authority",
        "claim_boundary",
        "format_version",
        "input_refs",
        "metrics",
        "result_id",
        "schema_snapshot",
        "state",
        "trials",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("annual geography result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != _CLAIM_BOUNDARY
        or value["state"] != "ANNUAL_2025_LOAN_GEOGRAPHY_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or [trial.get("bank_code") for trial in value["trials"]] != list(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["schema_snapshot"], _EXPECTED_SCHEMA_SNAPSHOT)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual geography result identity, order, schema or metrics drifted")
    for trial in value["trials"]:
        bank = trial["bank_code"]
        if bank in _MAPPED_BANKS:
            if (
                trial["status"] != "VERIFIED_BY_CODEX"
                or trial["physical_pages"] != _EXPECTED_REVIEW_PAGES[bank]
                or [item.get("report_norm_id") for item in trial["mapped_items"]] != [5752, 765]
                or len(trial["accounting_equations"]) != 2
            ):
                raise _error(f"{bank} mapped geography result shape drifted")
        elif (
            trial["status"] != "VERIFIED_NOT_OBSERVED_IN_BOUND_REPORT"
            or trial["report_norm_ids_not_observed"] != [759, 5752, 765]
            or trial["near_region_count"] != _EXPECTED_NEAR_COUNTS[bank]
        ):
            raise _error(f"{bank} geography absence result shape drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id")
    if result_id != "annual2025lg8bcv1:result:" + canonical_json_sha256_v1(material):
        raise _error("annual geography result identity drifted")
    return canonical_clone_v1(value)


def build_annual_2025_loan_geography_8bank_codex_verified_mapping_v1(
    semantic_index: Mapping[str, Any],
    manifest: Mapping[str, Any],
    scan: Mapping[str, Any],
    review: Mapping[str, Any],
    loan_type_result: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    review_sha256: str,
) -> dict[str, Any]:
    if (
        scan.get("scan_id") != EXPECTED_SCAN_ID
        or scan.get("input_semantic_axis_sha256") != EXPECTED_AXIS_SHA256
    ):
        raise _error("annual geography scan identity drifted")
    checked_review = _validate_review(review, semantic_index, manifest)
    if review_sha256 != EXPECTED_REVIEW_SHA256:
        raise _error("annual geography review SHA-256 drifted")
    owners = _owner_totals(loan_type_result)
    schema = _schema_snapshot(schema_by_id)
    trials = []
    for bank in EXPECTED_DOCUMENT_ORDER:
        scan_trial = _scan_trial(scan, bank)
        bank_review = _review_bank(checked_review, bank)
        trials.append(
            _mapped_trial(bank, scan_trial, bank_review, owners)
            if bank in _MAPPED_BANKS
            else _absence_trial(bank, scan_trial, bank_review)
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": _CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "annual_loan_type_result_sha256": EXPECTED_LOAN_TYPE_RESULT_SHA256,
            "crop_manifest_sha256": EXPECTED_CROP_MANIFEST_SHA256,
            "pixel_review_path": REVIEW_PATH.as_posix(),
            "pixel_review_sha256": review_sha256,
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "schema_snapshot": schema,
        "state": "ANNUAL_2025_LOAN_GEOGRAPHY_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {
            **material,
            "result_id": "annual2025lg8bcv1:result:" + canonical_json_sha256_v1(material),
        }
    )


def _live_inputs() -> tuple[Any, Any, Any, Any, Any, Mapping[int, Any]]:
    semantic = _strict_json(
        _fixed_bytes(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256), "annual semantic index"
    )
    manifest = _strict_json(
        _fixed_bytes(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256), "annual crop manifest"
    )
    scanner = _load_module(
        "annual_2025_loan_geography_scan_for_verified_mapping",
        "scripts/experiments/scan_loan_geography_full_document_vietocr_v1.py",
    )
    scan = scanner.build_loan_geography_full_document_scan_v1(semantic)
    review = _strict_json(
        _fixed_bytes(REVIEW_PATH, EXPECTED_REVIEW_SHA256), "annual geography pixel review"
    )
    loan_type_result = _strict_json(
        _fixed_bytes(LOAN_TYPE_RESULT_PATH, EXPECTED_LOAN_TYPE_RESULT_SHA256),
        "annual loan-type verified result",
    )
    _authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return semantic, manifest, scan, review, loan_type_result, schema_by_id


def build_live_annual_2025_loan_geography_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Rebuild the annual geography result from every live bounded authority."""

    semantic, manifest, scan, review, loan_type_result, schema_by_id = _live_inputs()
    return build_annual_2025_loan_geography_8bank_codex_verified_mapping_v1(
        semantic,
        manifest,
        scan,
        review,
        loan_type_result,
        schema_by_id,
        review_sha256=EXPECTED_REVIEW_SHA256,
    )


def validate_annual_2025_loan_geography_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild a persisted annual geography result from fixed inputs."""

    persisted = _validate_result(value)
    rebuilt = build_live_annual_2025_loan_geography_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("annual geography verified result does not replay exactly")
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    if args.write_review:
        semantic = _strict_json(
            _fixed_bytes(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256), "annual semantic index"
        )
        manifest = _strict_json(
            _fixed_bytes(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256),
            "annual crop manifest",
        )
        payload = canonical_json_bytes_v1(_review_blueprint(semantic, manifest))
        path = PROJECT_ROOT / REVIEW_PATH
        if path.exists() and path.read_bytes() != payload:
            raise _error("refusing to overwrite a different annual geography review")
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        print(hashlib.sha256(payload).hexdigest())
        return 0
    if args.validate is not None:
        path = args.validate if args.validate.is_absolute() else PROJECT_ROOT / args.validate
        validate_annual_2025_loan_geography_8bank_codex_verified_mapping_replay_v1(
            _strict_json(path.read_bytes(), "persisted annual geography result")
        )
        return 0
    result = build_live_annual_2025_loan_geography_8bank_codex_verified_mapping_v1()
    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    payload = canonical_json_bytes_v1(result)
    if output.exists() and output.read_bytes() != payload:
        raise _error("refusing to overwrite a different annual geography result")
    if not output.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
