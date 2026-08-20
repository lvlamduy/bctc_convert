#!/usr/bin/env python3
"""Verify annual-2025 securities geography for eight consolidated banks.

The matcher scans every page without bank/page/note routing.  It accepts only
the intersection of a geographic-concentration owner, domestic/foreign axes,
and a securities axis.  Geographic and business segment reports are retained
as negative controls.  Mapping is bounded to live TM rows 5759--5761 and every
current-period total is independently reconciled to the already verified gross
trading and investment-securities populations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_reporting_period_contexts_v1,
    validate_full_document_vietocr_reporting_period_contexts_replay_v1,
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
TRADING_RESULT_PATH = Path(
    "docs/experiments/E-0110-annual-2025-trading-securities-8bank-codex-verified-mapping-v1.json"
)
INVESTMENT_RESULT_PATH = Path(
    "docs/experiments/E-0121-annual-2025-investment-securities-8bank-codex-verified-mapping-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0160-annual-2025-securities-geography-8bank-codex-verified-mapping-v1.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0160-annual-2025-securities-geography-8bank-codex-pixel-review-v1.json"
)

EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_TRADING_SHA256 = "c1772bbb283cec02d7b2044795020a198391936299d63b23db766ed93cddbf28"
EXPECTED_INVESTMENT_SHA256 = "92a524848d90a2d5644f3043d0464bd28b9ebc9bfe1b2e2899879d9cdbaee40d"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_PERIOD_PROJECTION_ID = (
    "fdvrpcv1:projection:fd732522c67ec0fa927696bf1b17721f1ce16c34a083618e2bb4ebf7acb6d0d3"
)

FORMAT_VERSION = "ANNUAL_2025_SECURITIES_GEOGRAPHY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_SECURITIES_GEOGRAPHY_8BANK_CODEX_PIXEL_REVIEW_V1"
STATE = "ANNUAL_2025_SECURITIES_GEOGRAPHY_CODEX_VERIFICATION_COMPLETE"
RESULT_PREFIX = "annual2025sg8bcv1:result:"
REVIEW_PREFIX = "annual2025sg8bcv1:pixel-review:"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDF_FRESH_VIETOCR_"
    "BANK_BLIND_SECURITIES_GEOGRAPHIC_CONCENTRATION_GRAPH_ROW_OR_COLUMN_LAYOUT_"
    "CONTINUATION_PERIOD_UNIT_PIXEL_DASH_GROSS_OWNER_POPULATION_LIVE_TM_SCHEMA_"
    "EXACT_EQUATIONS_SUPPORTED_ROWS_ONLY_NO_RELATED_PARTY_CANONICAL_OR_EXPORT_"
    "AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_treated_as_zero": False,
    "bounded_report_absence_authority": True,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "dash_is_zero_only_after_visible_pixel_binding": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gross_trading_and_investment_populations_reconciled": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_rows_5759_through_5761": True,
    "public_exact_replay_required": True,
    "related_party_family_mapped": False,
    "segment_reports_used_as_negative_controls": True,
    "text_similarity_alone_used_for_mapping": False,
}
_EXPECTED_PAGES = {
    "ACB": [77],
    "MBB": [91],
    "VPB": [81],
    "HDB": [60],
    "VCB": [],
    "CTG": [],
    "BID": [63],
    "VIB": [59, 60],
}
_LAYOUTS = {
    "ACB": "GEOGRAPHY_ROWS_SECURITIES_COLUMN_TWO_PERIOD_BLOCKS",
    "MBB": "GEOGRAPHY_ROWS_SECURITIES_COLUMN_TWO_PERIOD_BLOCKS",
    "VPB": "SECURITIES_ROW_GEOGRAPHY_COLUMNS_ONE_PERIOD",
    "HDB": "GEOGRAPHY_ROWS_SECURITIES_COLUMN_ONE_PERIOD",
    "BID": "GEOGRAPHY_ROWS_SECURITIES_COLUMN_ONE_PERIOD_NO_PRINTED_TOTAL",
    "VIB": "SECURITIES_ROW_GEOGRAPHY_COLUMNS_ADJACENT_PERIOD_PAGES",
}
_SCHEMA = {
    "ROOT": (5759, "Kinh doanh và đầu tư chứng khoán", 1259),
    "DOMESTIC": (5760, "+ Trong nước", 5759),
    "FOREIGN": (5761, "+ Nước ngoài", 5759),
}
_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_refs",
    "metrics",
    "result_id",
    "schema_family",
    "state",
    "trials",
}


class Annual2025SecuritiesGeography8BankError(ValueError):
    """The annual securities-geography evidence, schema or equation drifted."""


def _error(message: str) -> Annual2025SecuritiesGeography8BankError:
    return Annual2025SecuritiesGeography8BankError(message)


def _stable_bytes(relative: Path) -> bytes:
    path = PROJECT_ROOT / relative
    if path.is_symlink():
        raise _error(f"fixed artifact is a symlink: {relative}")
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise _error(f"fixed artifact is not regular: {relative}")
    payload = path.read_bytes()
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise _error(f"fixed artifact changed while reading: {relative}")
    return payload


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
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc


def _fixed_json(relative: Path, expected_sha256: str) -> dict[str, Any]:
    payload = _stable_bytes(relative)
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed artifact SHA-256 drifted: {relative}")
    value = _strict_json(payload, relative.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed artifact root is not one object: {relative}")
    return value


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    plain = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


def _document(value: Mapping[str, Any], bank: str) -> dict[str, Any]:
    documents = value.get("documents")
    if type(documents) is not list:
        raise _error("semantic document collection drifted")
    matches = [item for item in documents if type(item) is dict and item.get("bank_code") == bank]
    if len(matches) != 1:
        raise _error(f"semantic index must contain one {bank} document")
    return matches[0]


def _page(document: Mapping[str, Any], number: int) -> dict[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error("semantic page collection drifted")
    matches = [item for item in pages if type(item) is dict and item.get("physical_page") == number]
    if len(matches) != 1:
        raise _error(f"semantic document must contain one page {number}")
    return matches[0]


def _event(
    index: Mapping[str, Any], bank: str, page_number: int, line_index: int
) -> dict[str, Any]:
    page = _page(_document(index, bank), page_number)
    lines = page.get("lines")
    if type(lines) is not list or not 0 <= line_index < len(lines):
        raise _error(f"{bank} p{page_number} line locator drifted")
    line = lines[line_index]
    if type(line) is not dict or line.get("source_line_index") != line_index:
        raise _error("semantic line axis drifted")
    return {
        "crop_ref": canonical_clone_v1(line["crop_ref"]),
        "source_bbox_raw_pixels": canonical_clone_v1(line["source_bbox_raw_pixels"]),
        "source_line_index": line_index,
        "vietocr_text": line["vietocr_text"],
    }


def _events(
    index: Mapping[str, Any], bank: str, page_number: int, line_indices: Sequence[int]
) -> list[dict[str, Any]]:
    return [_event(index, bank, page_number, item) for item in line_indices]


def _render_ref(manifest: Mapping[str, Any], bank: str, page_number: int) -> dict[str, Any]:
    page = _page(_document(manifest, bank), page_number)
    binding = page.get("render_binding")
    if type(binding) is not dict:
        raise _error("render binding drifted")
    return canonical_clone_v1(binding)


def _scan_document(document: Mapping[str, Any]) -> dict[str, Any]:
    """Find complete securities-geography pages without provenance routing."""

    pages = document.get("pages")
    if type(pages) is not list:
        raise _error("scan page collection drifted")
    candidates: list[int] = []
    near_segment_pages: list[int] = []
    for page in pages:
        lines = page.get("lines")
        if type(lines) is not list:
            raise _error("scan line collection drifted")
        surfaces = [_normalize(line["vietocr_text"]) for line in lines]
        joined = " ".join(surfaces)
        geographic_owner = "muc do tap trung" in joined and "khu vuc dia ly" in joined
        geography_axes = "trong nuoc" in joined and "nuoc ngoai" in joined
        security_axis = (
            "kinh doanh" in joined
            and "dau" in joined
            and "tu" in joined
            and ("chung khoan" in joined or "khoan" in joined)
        ) or "chung khoan dau tu" in joined
        segment_surface = "bao cao bo phan" in joined and (
            "khu vuc dia ly" in joined or "linh vuc kinh doanh" in joined
        )
        number = page.get("physical_page")
        if type(number) is not int:
            raise _error("scan physical page drifted")
        if geographic_owner and geography_axes and security_axis:
            candidates.append(number)
        elif segment_surface and security_axis:
            near_segment_pages.append(number)
    groups: list[list[int]] = []
    for number in candidates:
        if groups and number == groups[-1][-1] + 1:
            groups[-1].append(number)
        else:
            groups.append([number])
    status = (
        "UNIQUE_COMPLETE_REGION"
        if len(groups) == 1
        else ("BOUNDED_REPORT_ABSENCE" if not groups else "UNRESOLVED_MULTIPLE_REGIONS")
    )
    return {
        "candidate_page_groups": groups,
        "complete_page_count": len(candidates),
        "near_segment_negative_control_pages": near_segment_pages,
        "page_count_scanned": len(pages),
        "scan_id": "annual2025sgscanv1:scan:"
        + canonical_json_sha256_v1(
            {
                "candidate_page_groups": groups,
                "near_segment_negative_control_pages": near_segment_pages,
                "page_count_scanned": len(pages),
            }
        ),
        "status": status,
    }


def _scan_all(index: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    scans = {bank: _scan_document(_document(index, bank)) for bank in EXPECTED_DOCUMENT_ORDER}
    if {bank: sum(scan["candidate_page_groups"], []) for bank, scan in scans.items()} != (
        _EXPECTED_PAGES
    ):
        raise _error("whole-PDF securities-geography candidate vector drifted")
    return scans


def _cell(
    index: Mapping[str, Any],
    bank: str,
    page_number: int,
    role: str,
    label_index: int,
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
    else:
        value_event = _event(index, bank, page_number, value_index)
        dash_bbox = None
    return {
        "dash_pixel_bbox": None if dash_bbox is None else list(dash_bbox),
        "label_event": _event(index, bank, page_number, label_index),
        "pixel_value": pixel_value,
        "role": role,
        "value_event": value_event,
    }


def _period(
    index: Mapping[str, Any],
    manifest: Mapping[str, Any],
    bank: str,
    page_number: int,
    period_role: str,
    period_end: str,
    heading_indices: Sequence[int],
    security_indices: Sequence[int],
    domestic: Mapping[str, Any],
    foreign: Mapping[str, Any],
    *,
    total_index: int | None,
    total_pixel_value: str | None,
) -> dict[str, Any]:
    return {
        "cells": [canonical_clone_v1(domestic), canonical_clone_v1(foreign)],
        "heading_events": _events(index, bank, page_number, heading_indices),
        "period_end": period_end,
        "period_role": period_role,
        "physical_page": page_number,
        "render_ref": _render_ref(manifest, bank, page_number),
        "security_axis_events": _events(index, bank, page_number, security_indices),
        "total_event": (
            None if total_index is None else _event(index, bank, page_number, total_index)
        ),
        "total_pixel_value": total_pixel_value,
    }


def _review_blueprint(
    index: Mapping[str, Any], manifest: Mapping[str, Any], scans: Mapping[str, Any]
) -> dict[str, Any]:
    records: dict[str, list[dict[str, Any]]] = {}
    records["ACB"] = [
        _period(
            index,
            manifest,
            "ACB",
            77,
            "CURRENT",
            "2025-12-31",
            (5, 6),
            (10, 17, 24),
            _cell(index, "ACB", 77, "DOMESTIC", 34, "150.819.498", value_index=41),
            _cell(index, "ACB", 77, "FOREIGN", 43, "64.226", value_index=48),
            total_index=56,
            total_pixel_value="150.883.724",
        ),
        _period(
            index,
            manifest,
            "ACB",
            77,
            "COMPARATIVE",
            "2024-12-31",
            (5, 58),
            (62, 69, 76),
            _cell(index, "ACB", 77, "DOMESTIC", 86, "125.119.331", value_index=93),
            _cell(
                index,
                "ACB",
                77,
                "FOREIGN",
                95,
                "-",
                value_index=None,
                dash_bbox=(1830, 1116, 1991, 1152),
            ),
            total_index=107,
            total_pixel_value="125.119.331",
        ),
    ]
    records["MBB"] = [
        _period(
            index,
            manifest,
            "MBB",
            91,
            "CURRENT",
            "2025-12-31",
            (10, 11),
            (17, 22),
            _cell(index, "MBB", 91, "DOMESTIC", 29, "230.449.032", value_index=35),
            _cell(index, "MBB", 91, "FOREIGN", 36, "51.179", value_index=40),
            total_index=46,
            total_pixel_value="230.500.211",
        ),
        _period(
            index,
            manifest,
            "MBB",
            91,
            "COMPARATIVE",
            "2024-12-31",
            (10, 47),
            (53, 58),
            _cell(index, "MBB", 91, "DOMESTIC", 65, "217.995.033", value_index=71),
            _cell(index, "MBB", 91, "FOREIGN", 72, "57.261", value_index=75),
            total_index=82,
            total_pixel_value="218.052.294",
        ),
    ]
    records["VPB"] = [
        _period(
            index,
            manifest,
            "VPB",
            81,
            "CURRENT",
            "2025-12-31",
            (5, 6, 7),
            (32,),
            _cell(index, "VPB", 81, "DOMESTIC", 9, "88.595.317", value_index=33),
            _cell(
                index,
                "VPB",
                81,
                "FOREIGN",
                10,
                "-",
                value_index=None,
                dash_bbox=(1103, 755, 1255, 794),
            ),
            total_index=34,
            total_pixel_value="88.595.317",
        )
    ]
    records["HDB"] = [
        _period(
            index,
            manifest,
            "HDB",
            60,
            "CURRENT",
            "2025-12-31",
            (8, 9),
            (13, 18, 23),
            _cell(index, "HDB", 60, "DOMESTIC", 29, "77.435.184", value_index=34),
            _cell(
                index,
                "HDB",
                60,
                "FOREIGN",
                35,
                "-",
                value_index=None,
                dash_bbox=(1350, 592, 1494, 626),
            ),
            total_index=41,
            total_pixel_value="77.435.184",
        )
    ]
    records["BID"] = [
        _period(
            index,
            manifest,
            "BID",
            63,
            "CURRENT",
            "2025-12-31",
            (4, 5),
            (9, 12, 14),
            _cell(index, "BID", 63, "DOMESTIC", 22, "313.930.664", value_index=27),
            _cell(index, "BID", 63, "FOREIGN", 28, "1.765.075", value_index=32),
            total_index=None,
            total_pixel_value=None,
        )
    ]
    records["VIB"] = [
        _period(
            index,
            manifest,
            "VIB",
            59,
            "CURRENT",
            "2025-12-31",
            (5, 6, 11),
            (31,),
            _cell(index, "VIB", 59, "DOMESTIC", 7, "51.149.531", value_index=32),
            _cell(
                index,
                "VIB",
                59,
                "FOREIGN",
                8,
                "-",
                value_index=None,
                dash_bbox=(1098, 682, 1249, 718),
            ),
            total_index=33,
            total_pixel_value="51.149.531",
        ),
        _period(
            index,
            manifest,
            "VIB",
            60,
            "COMPARATIVE",
            "2024-12-31",
            (5, 6, 13),
            (35,),
            _cell(index, "VIB", 60, "DOMESTIC", 7, "50.388.192", value_index=36),
            _cell(
                index,
                "VIB",
                60,
                "FOREIGN",
                8,
                "-",
                value_index=None,
                dash_bbox=(1098, 777, 1249, 813),
            ),
            total_index=37,
            total_pixel_value="50.388.192",
        ),
    ]
    banks = []
    for bank in EXPECTED_DOCUMENT_ORDER:
        if bank in records:
            banks.append(
                {
                    "bank_code": bank,
                    "layout": _LAYOUTS[bank],
                    "periods": records[bank],
                    "scan": canonical_clone_v1(scans[bank]),
                    "status": "PIXEL_REVIEW_COMPLETE",
                }
            )
        else:
            banks.append(
                {
                    "bank_code": bank,
                    "bounded_report_disposition": (
                        "NO_COMPLETE_SECURITIES_GEOGRAPHIC_CONCENTRATION_REGION"
                    ),
                    "scan": canonical_clone_v1(scans[bank]),
                    "status": "CONFIRMED_NOT_OBSERVED_IN_BOUND_REPORT",
                }
            )
    material = {
        "banks": banks,
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": REVIEW_FORMAT,
        "review_checks": {
            "all_eight_complete_pdfs_scanned": True,
            "all_six_candidate_renders_opened": True,
            "domestic_foreign_period_unit_total_and_owner_populations_checked": True,
            "related_party_family_skipped": True,
            "segment_reports_retained_as_negative_controls": True,
        },
        "reviewer": {"kind": "CODEX_INDEPENDENT_SOURCE_REVIEW"},
    }
    return {**material, "review_id": REVIEW_PREFIX + canonical_json_sha256_v1(material)}


def _money(value: str) -> int:
    token = value.strip().replace(" ", "")
    if token in {"-", "–", "—"}:
        return 0
    negative = token.startswith("(") and token.endswith(")")
    if negative:
        token = token[1:-1]
    compact = token.replace(".", "").replace(",", "")
    if not compact.isdigit():
        raise _error(f"reviewed monetary token drifted: {value}")
    parsed = int(compact)
    return -parsed if negative else parsed


def _trial(items: Any, bank: str, *keys: str) -> dict[str, Any]:
    if type(items) is not list:
        raise _error("external verified trial collection drifted")
    matches = [
        item for item in items if type(item) is dict and any(item.get(key) == bank for key in keys)
    ]
    if len(matches) != 1:
        raise _error(f"external verified result must contain one {bank} trial")
    return matches[0]


def _trading_gross(result: Mapping[str, Any], bank: str) -> int:
    trial = _trial(result.get("trials"), bank, "document_provenance")
    mappings = trial.get("verified_mappings")
    if type(mappings) is not list:
        raise _error("trading mapping collection drifted")
    by_id = {
        item["report_norm_id"]: item["normalized_value"]
        for item in mappings
        if type(item) is dict
        and type(item.get("report_norm_id")) is int
        and type(item.get("normalized_value")) is int
    }
    if 611 in by_id:
        return by_id[611]
    if 626 in by_id:
        return by_id[626]
    return sum(by_id.get(item, 0) for item in (594, 600, 606))


def _investment_gross(result: Mapping[str, Any], bank: str) -> int:
    trial = _trial(result.get("trials"), bank, "bank_provenance")
    equations = trial.get("verified_accounting_equations")
    if type(equations) is not list:
        raise _error("investment equation collection drifted")
    result_value = 0
    for family in ("AFS", "HTM", "VAMC"):
        gross_role = f"{bank}_CURRENT_{family}_GROSS"
        net_role = f"{bank}_CURRENT_{family}_NET"
        gross = next(
            (
                item.get("computed_total")
                for item in equations
                if type(item) is dict and item.get("role") == gross_role
            ),
            None,
        )
        if type(gross) is int:
            result_value += gross
            continue
        net = next(
            (item for item in equations if type(item) is dict and item.get("role") == net_role),
            None,
        )
        if net is None:
            continue
        addends = net.get("source_addends")
        positives = (
            [item.get("normalized_value") for item in addends] if type(addends) is list else []
        )
        positives = [item for item in positives if type(item) is int and item > 0]
        value = sum(positives) if positives else net.get("computed_total")
        if type(value) is not int:
            raise _error(f"{bank} {family} gross population could not be derived")
        result_value += value
    return result_value


def _schema_snapshot(schema_by_id: Mapping[int, Any]) -> dict[str, Any]:
    rows = []
    for role, (report_norm_id, canonical_name, parent_id) in _SCHEMA.items():
        item = schema_by_id.get(report_norm_id)
        if (
            item is None
            or item.canonical_name != canonical_name
            or item.parent_id != parent_id
            or item.statement_type != "TM"
            or "CONSOLIDATED" not in item.scope
        ):
            raise _error(f"live TM securities-geography row {report_norm_id} drifted")
        rows.append(
            {
                "canonical_name": canonical_name,
                "display_order": item.display_order,
                "hierarchy_level": item.hierarchy_level,
                "report_norm_id": report_norm_id,
                "schema_parent_report_norm_id": parent_id,
                "semantic_role": role,
            }
        )
    if schema_by_id[5759].children != [5760, 5761]:
        raise _error("live TM securities-geography first/last boundary drifted")
    return {"rows": rows}


def _mapping(
    schema_rows: Mapping[str, Any], role: str, review_periods: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    row = next(item for item in schema_rows["rows"] if item["semantic_role"] == role)
    values = []
    label_event = None
    for period in review_periods:
        cell = next(item for item in period["cells"] if item["role"] == role)
        label_event = label_event or cell["label_event"]
        values.append(
            {
                "dash_pixel_bbox": canonical_clone_v1(cell["dash_pixel_bbox"]),
                "normalized_value": _money(cell["pixel_value"]),
                "period_end": period["period_end"],
                "period_role": period["period_role"],
                "pixel_transcription": cell["pixel_value"],
                "source_cell_status": "DASH" if cell["pixel_value"] == "-" else "VALUE",
                "value_event": canonical_clone_v1(cell["value_event"]),
            }
        )
    return {
        **canonical_clone_v1(row),
        "label_event": canonical_clone_v1(label_event),
        "status": "VERIFIED_BY_CODEX",
        "topology": "GEOGRAPHIC_OWNER_SECURITIES_AXIS_DOMESTIC_FOREIGN_PERIOD_GEOMETRY",
        "values": values,
    }


def _build_payload() -> tuple[dict[str, Any], dict[str, Any]]:
    index = _fixed_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    manifest = _fixed_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    trading = _fixed_json(TRADING_RESULT_PATH, EXPECTED_TRADING_SHA256)
    investment = _fixed_json(INVESTMENT_RESULT_PATH, EXPECTED_INVESTMENT_SHA256)
    if index.get("metrics", {}).get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256:
        raise _error("annual semantic axis drifted")
    periods = validate_full_document_vietocr_reporting_period_contexts_replay_v1(
        project_full_document_vietocr_reporting_period_contexts_v1(index), index
    )
    if periods["projection_id"] != EXPECTED_PERIOD_PROJECTION_ID:
        raise _error("annual period projection drifted")
    for item in periods["contexts"]:
        context = item["reporting_period_context"]
        if (
            context["current_period_end"] != "31/12/2025"
            or context["balance_comparative_period_end"] != "31/12/2024"
        ):
            raise _error("annual reporting period context drifted")
    scans = _scan_all(index)
    review = _review_blueprint(index, manifest, scans)
    _, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    schema = _schema_snapshot(schema_by_id)
    trials = []
    mapped_bank_count = 0
    equation_count = 0
    mapping_count = 0
    value_count = 0
    dash_count = 0
    for review_bank in review["banks"]:
        bank = review_bank["bank_code"]
        document = _document(index, bank)
        if review_bank["status"] != "PIXEL_REVIEW_COMPLETE":
            trials.append(
                {
                    "bounded_report_disposition": review_bank["bounded_report_disposition"],
                    "document_ordinal": document["document_ordinal"],
                    "document_provenance": bank,
                    "scan": canonical_clone_v1(scans[bank]),
                    "source_pdf_sha256": document["source_pdf"]["sha256"],
                    "status": "NOT_OBSERVED_IN_BOUND_REPORT",
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                }
            )
            continue
        mapped_bank_count += 1
        mappings = [
            _mapping(schema, "DOMESTIC", review_bank["periods"]),
            _mapping(schema, "FOREIGN", review_bank["periods"]),
        ]
        mapping_count += 2
        value_count += sum(len(item["values"]) for item in mappings)
        dash_count += sum(
            value["source_cell_status"] == "DASH" for item in mappings for value in item["values"]
        )
        gross_owner = _trading_gross(trading, bank) + _investment_gross(investment, bank)
        equations = []
        for period in review_bank["periods"]:
            domestic = _money(period["cells"][0]["pixel_value"])
            foreign = _money(period["cells"][1]["pixel_value"])
            computed = domestic + foreign
            table_total = (
                computed
                if period["total_pixel_value"] is None
                else _money(period["total_pixel_value"])
            )
            if computed != table_total:
                raise _error(f"{bank} geographic securities equation does not close")
            equations.append(
                {
                    "components": {"DOMESTIC": domestic, "FOREIGN": foreign},
                    "computed_total": computed,
                    "name": "DOMESTIC_PLUS_FOREIGN_EQUALS_SECURITIES_TOTAL",
                    "period_end": period["period_end"],
                    "status": "CORROBORATED_EXACT",
                    "visible_or_derived_total": table_total,
                }
            )
            if period["period_role"] == "CURRENT":
                if computed != gross_owner:
                    raise _error(f"{bank} geographic total differs from verified gross population")
                equations.append(
                    {
                        "components": {
                            "INVESTMENT_SECURITIES_GROSS": _investment_gross(investment, bank),
                            "TRADING_SECURITIES_GROSS": _trading_gross(trading, bank),
                        },
                        "computed_total": gross_owner,
                        "name": "TRADING_PLUS_INVESTMENT_GROSS_EQUALS_GEOGRAPHIC_TOTAL",
                        "period_end": period["period_end"],
                        "status": "CORROBORATED_EXACT",
                        "visible_or_derived_total": computed,
                    }
                )
        equation_count += len(equations)
        trials.append(
            {
                "document_ordinal": document["document_ordinal"],
                "document_provenance": bank,
                "evidence_page_sequence": _EXPECTED_PAGES[bank],
                "layout": review_bank["layout"],
                "scan": canonical_clone_v1(scans[bank]),
                "source_pdf_sha256": document["source_pdf"]["sha256"],
                "status": "VERIFIED_BY_CODEX",
                "verified_accounting_equations": equations,
                "verified_mappings": mappings,
            }
        )
    metrics = {
        "accounting_equation_verified_count": equation_count,
        "bounded_report_absence_document_count": 2,
        "dash_cell_verified_as_zero_count": dash_count,
        "document_count": 8,
        "document_unique_region_count": mapped_bank_count,
        "mapping_verified_count": mapping_count,
        "verified_value_cell_count": value_count,
    }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": {
                "path": CROP_MANIFEST_PATH.as_posix(),
                "sha256": EXPECTED_CROP_MANIFEST_SHA256,
            },
            "investment_securities_result": {
                "path": INVESTMENT_RESULT_PATH.as_posix(),
                "result_id": investment["result_id"],
                "sha256": EXPECTED_INVESTMENT_SHA256,
            },
            "period_projection_id": periods["projection_id"],
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": EXPECTED_INDEX_SHA256,
            },
            "trading_securities_result": {
                "path": TRADING_RESULT_PATH.as_posix(),
                "result_id": trading["result_id"],
                "sha256": EXPECTED_TRADING_SHA256,
            },
        },
        "metrics": metrics,
        "schema_family": canonical_clone_v1(
            next(item for item in schema["rows"] if item["semantic_role"] == "ROOT")
        ),
        "state": STATE,
        "trials": trials,
    }
    return (
        {**material, "result_id": RESULT_PREFIX + canonical_json_sha256_v1(material)},
        review,
    )


def _validate_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("annual securities-geography result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["state"] != STATE
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
    ):
        raise _error("annual securities-geography identity or authority drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_PREFIX + canonical_json_sha256_v1(material):
        raise _error("annual securities-geography result identity drifted")
    return canonical_clone_v1(value)


def build_live_annual_2025_securities_geography_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Build the live, exact annual securities-geography result."""

    result, _review = _build_payload()
    return _validate_shape(result)


def validate_annual_2025_securities_geography_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Validate shape and exact-rebuild the result from live fixed evidence."""

    persisted = _validate_shape(value)
    expected, _review = _build_payload()
    if not same_typed_json_v1(persisted, expected):
        raise _error("annual securities-geography result does not exact-replay")
    return persisted


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.build == args.verify:
        raise SystemExit("choose exactly one of --build or --verify")
    if args.build:
        result, review = _build_payload()
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(_validate_shape(result)))
        REVIEW_PATH.write_bytes(canonical_json_bytes_v1(review))
        print(result["result_id"])
        return
    persisted = _strict_json(_stable_bytes(RESULT_PATH), RESULT_PATH.as_posix())
    review = _strict_json(_stable_bytes(REVIEW_PATH), REVIEW_PATH.as_posix())
    expected_result, expected_review = _build_payload()
    if not same_typed_json_v1(review, expected_review):
        raise _error("annual securities-geography pixel review does not exact-replay")
    validate_annual_2025_securities_geography_8bank_codex_verified_mapping_replay_v1(persisted)
    if not same_typed_json_v1(persisted, expected_result):
        raise _error("annual securities-geography persisted result drifted")
    print(persisted["result_id"])


if __name__ == "__main__":
    _main()
