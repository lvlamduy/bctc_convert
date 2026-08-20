#!/usr/bin/env python3
"""Verify the annual-2025 consolidated segment-report family for eight banks.

The matcher scans every page and joins ordinary, continued and rotated pages
using only report text, table topology and page geometry.  Bank codes and page
numbers are evidence locators after matching; they are never routing rules.

Mapping is deliberately narrower than source extraction.  It binds only
source axes whose accounting meaning is identical to the live TM 5762--5848
hierarchy.  Broader or narrower axes remain source-only.  Numeric truth comes
from reviewed page pixels (with the authenticated VietOCR/rotated crops used
for location), never from Transformer text alone.  Root 5750, related-party
transactions, is outside this experiment by explicit project-owner direction.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import stat
import sys
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
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
ROTATED_CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-rotated-vietocr-rescue-v1/"
    "crop_manifest.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-"
    "codex-verified-mapping-v1.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-"
    "codex-pixel-review-v1.json"
)

EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_ROTATED_CROP_MANIFEST_SHA256 = (
    "680c5981dcf0fba79b969fb33d14f15b418956d390cd541443475a4435289e45"
)
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_PERIOD_PROJECTION_ID = (
    "fdvrpcv1:projection:fd732522c67ec0fa927696bf1b17721f1ce16c34a083618e2bb4ebf7acb6d0d3"
)
EXPECTED_ROTATED_PROJECTION_ID = (
    "fdrrv1:projection:6ef48add635631c2ee6d96b309002fcbc79c2b9576351b7f5afc4463ab3a2fc7"
)

FORMAT_VERSION = "ANNUAL_2025_CONSOLIDATED_SEGMENT_REPORT_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_CONSOLIDATED_SEGMENT_REPORT_8BANK_CODEX_PIXEL_REVIEW_V1"
STATE = "ANNUAL_2025_CONSOLIDATED_SEGMENT_REPORT_CODEX_VERIFICATION_COMPLETE"
RESULT_PREFIX = "annual2025csr8bcv1:result:"
REVIEW_PREFIX = "annual2025csr8bcv1:pixel-review:"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDF_FRESH_VIETOCR_"
    "WHOLE_DOCUMENT_UNIQUE_SEGMENT_REPORT_ORDINARY_CONTINUATION_ROTATED_TABLE_"
    "GEOGRAPHIC_AND_BUSINESS_BRANCH_EXACT_AXIS_PERIOD_UNIT_PIXEL_ACCOUNTING_"
    "LIVE_TM_5762_5848_SUPPORTED_ROWS_ONLY_RELATED_PARTY_5750_SKIPPED_NO_"
    "CANONICAL_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_treated_as_zero": False,
    "broader_or_narrower_source_axis_forced_into_schema": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_rows_5762_through_5848": True,
    "public_exact_replay_required": True,
    "related_party_root_5750_mapped": False,
    "related_party_root_5750_skipped_by_project_owner": True,
    "rotated_page_rescue_used_only_as_authenticated_locator": True,
    "text_similarity_alone_used_for_mapping": False,
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

_EXPECTED_REGIONS = {
    "ACB": [95, 96, 97, 98, 99],
    "MBB": [83, 84, 85, 86, 87, 88, 89, 90],
    "VPB": [95, 96, 97],
    "HDB": [60, 61],
    "VCB": [71, 72],
    "CTG": [81, 82, 83, 84],
    "BID": [36, 37, 38],
    "VIB": [61, 62],
}

_GEO_AXIS_PARENT = {
    "NORTH": 5764,
    "CENTRAL": 5771,
    "SOUTH": 5778,
    "OTHER": 5785,
    "ELIMINATION": 5792,
    "TOTAL": 5799,
}
_BUSINESS_AXIS_PARENT = {
    "BANK": 5807,
    "SECURITIES_FUND": 5814,
    "INSURANCE": 5821,
    "DEBT_ASSET": 5828,
    "ELIMINATION": 5835,
    "TOTAL": 5842,
}
_METRIC_OFFSET = {
    "ASSETS": 1,
    "LIABILITIES": 2,
    "FIXED_ASSETS": 3,
    "REVENUE": 4,
    "EXPENSE": 5,
    "PROFIT_BEFORE_TAX": 6,
}
_EXPECTED_SCHEMA_NAMES = {
    5762: "Báo cáo bộ phận hợp nhất",
    5763: "Báo cáo bộ phận hợp nhất theo khu vực địa lý",
    5764: "Miền Bắc",
    5771: "Miền Trung",
    5778: "Miền Nam",
    5785: "Khu vực khác",
    5792: "Loại trừ/Phân loại",
    5799: "Tổng cộng",
    5806: "Báo cáo bộ phận hợp nhất theo khu vực kinh doanh",
    5807: "Tài chính Ngân hàng",
    5814: "Chứng khoán Quản lý quỹ",
    5821: "Bảo hiểm",
    5828: "Quản lý nợ và Khai thác tài sản",
    5835: "Loại trừ/Phân loại",
    5842: "Tổng cộng",
}


class Annual2025ConsolidatedSegmentReport8BankError(ValueError):
    """The annual segment-report evidence, schema or equation drifted."""


def _error(message: str) -> Annual2025ConsolidatedSegmentReport8BankError:
    return Annual2025ConsolidatedSegmentReport8BankError(message)


def _load_rotated_rescue() -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments/build_full_document_rotated_vietocr_rescue_v1.py"
    name = "annual_2025_segment_rotated_rescue_v1"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual rotated rescue: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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
    line = _page(_document(index, bank), page_number)["lines"][line_index]
    if type(line) is not dict or line.get("source_line_index") != line_index:
        raise _error(f"{bank} p{page_number} line locator drifted")
    return {
        "crop_ref": canonical_clone_v1(line["crop_ref"]),
        "source_bbox_raw_pixels": canonical_clone_v1(line["source_bbox_raw_pixels"]),
        "source_line_index": line_index,
        "vietocr_text": line["vietocr_text"],
    }


def _render_ref(manifest: Mapping[str, Any], bank: str, page_number: int) -> dict[str, Any]:
    binding = _page(_document(manifest, bank), page_number).get("render_binding")
    if type(binding) is not dict:
        raise _error(f"{bank} p{page_number} render binding drifted")
    return canonical_clone_v1(binding)


def _rotated_samples(projection: Mapping[str, Any]) -> dict[tuple[int, int, int], dict[str, Any]]:
    samples = projection.get("samples")
    if type(samples) is not list:
        raise _error("rotated semantic samples drifted")
    by_key: dict[tuple[int, int, int], dict[str, Any]] = {}
    for item in samples:
        if type(item) is not dict:
            raise _error("rotated semantic sample is not an object")
        key = (item["document_ordinal"], item["physical_page"], item["source_line_index"])
        if key in by_key:
            raise _error("rotated semantic sample locator duplicated")
        by_key[key] = item
    return by_key


def _rotated_event(
    rotated_by_key: Mapping[tuple[int, int, int], Mapping[str, Any]],
    document_ordinal: int,
    page_number: int,
    line_index: int,
) -> dict[str, Any]:
    item = rotated_by_key.get((document_ordinal, page_number, line_index))
    if item is None:
        raise _error("rotated semantic locator drifted")
    return {
        "mean_decoded_character_probability": item["mean_decoded_character_probability"],
        "semantic_text": item["semantic_text"],
        "source_crop_sha256": item["source_crop_sha256"],
        "source_line_index": line_index,
    }


def _page_texts(page: Mapping[str, Any]) -> list[str]:
    lines = page.get("lines")
    if type(lines) is not list:
        raise _error("scan line collection drifted")
    return [_normalize(item["vietocr_text"]) for item in lines]


def _vertical_page(page: Mapping[str, Any]) -> bool:
    lines = page["lines"]
    tall = 0
    for line in lines:
        x1, y1, x2, y2 = line["source_bbox_raw_pixels"]
        tall += (y2 - y1) > 2 * max(1, x2 - x1)
    return tall >= max(5, len(lines) // 2)


def _scan_document(
    document: Mapping[str, Any], rotated_projection: Mapping[str, Any]
) -> dict[str, Any]:
    """Locate the unique segment region with text, topology and rotation rules."""

    ordinal = document["document_ordinal"]
    rotated_text: dict[int, list[str]] = {}
    for item in rotated_projection["samples"]:
        if item["document_ordinal"] == ordinal:
            rotated_text.setdefault(item["physical_page"], []).append(
                _normalize(item["semantic_text"])
            )
    infos = []
    for page in document["pages"]:
        number = page["physical_page"]
        ordinary = _page_texts(page)
        combined = ordinary + rotated_text.get(number, [])
        joined = " ".join(combined)
        segment_positions = [
            index for index, text in enumerate(ordinary) if "bao cao bo phan" in text
        ]
        concentration_positions = [
            index for index, text in enumerate(ordinary) if "muc do tap trung" in text
        ]
        boundary_after_header = bool(
            segment_positions
            and concentration_positions
            and min(concentration_positions) > min(segment_positions)
        )
        segment_after_boundary = bool(
            segment_positions
            and concentration_positions
            and max(segment_positions) > min(concentration_positions)
        )
        direct = (
            "bao cao bo phan" in joined
            or "thong tin bao cao bo phan" in joined
            or (
                joined.count("bo phan") >= 2
                and "linh vuc kinh doanh" in joined
                and "khu vuc dia ly" in joined
            )
        )
        if boundary_after_header and not segment_after_boundary:
            direct = False
        axes = sum(
            token in joined
            for token in (
                "mien bac",
                "mien trung",
                "mien nam",
                "tong cong",
                "tai chinh ngan hang",
                "hoat dong ngan hang",
                "bao hiem",
                "loai tru",
                "dieu chinh",
            )
        )
        metrics = sum(
            token in joined
            for token in (
                "tai san",
                "no phai tra",
                "loi nhuan truoc thue",
                "ket qua kinh doanh bo phan",
                "doanh thu",
                "chi phi",
            )
        )
        infos.append(
            {
                "direct": direct,
                "physical_page": number,
                "table": axes >= 3 and metrics >= 2,
                "vertical": _vertical_page(page),
            }
        )
    groups: list[list[int]] = []
    by_page = {item["physical_page"]: item for item in infos}
    for item in infos:
        if not item["direct"]:
            continue
        number = item["physical_page"]
        bridge_ok = (
            groups
            and number <= groups[-1][-1] + 3
            and all(
                by_page[mid]["vertical"] or by_page[mid]["direct"]
                for mid in range(groups[-1][-1] + 1, number)
            )
        )
        if bridge_ok:
            groups[-1].extend(range(groups[-1][-1] + 1, number + 1))
        else:
            groups.append([number])
    for group in groups:
        while by_page.get(group[-1] + 1, {}).get("vertical"):
            group.append(group[-1] + 1)
    groups = [group for group in groups if any(by_page[number]["table"] for number in group)]
    return {
        "candidate_page_groups": groups,
        "page_count_scanned": len(infos),
        "scan_id": "annual2025csrscanv1:scan:"
        + canonical_json_sha256_v1(
            {"candidate_page_groups": groups, "page_count_scanned": len(infos)}
        ),
        "status": "UNIQUE_COMPLETE_REGION" if len(groups) == 1 else "UNRESOLVED_SCAN",
    }


def _scan_all(
    index: Mapping[str, Any], rotated_projection: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    scans = {
        bank: _scan_document(_document(index, bank), rotated_projection)
        for bank in EXPECTED_DOCUMENT_ORDER
    }
    observed = {
        bank: scan["candidate_page_groups"][0] if len(scan["candidate_page_groups"]) == 1 else []
        for bank, scan in scans.items()
    }
    if observed != _EXPECTED_REGIONS:
        raise _error(f"whole-PDF segment-report candidate vector drifted: {observed}")
    return scans


def _row(
    bank: str,
    branch: str,
    page: int,
    period_role: str,
    period_end: str,
    metric: str,
    cells: Sequence[tuple[str, str | None, int | None]],
    *,
    equation: bool = True,
    evidence_mode: str = "FULL_DOCUMENT_VIETOCR_PIXEL_BOUND",
) -> dict[str, Any]:
    return {
        "bank": bank,
        "branch": branch,
        "cells": [list(item) for item in cells],
        "equation": equation,
        "evidence_mode": evidence_mode,
        "metric": metric,
        "page": page,
        "period_end": period_end,
        "period_role": period_role,
    }


def _numeric_blueprint() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    add = rows.append
    # ACB geographic assets/liabilities.  Several PP-OCR lines contain three
    # cells; axis headers plus column geometry disambiguate the reviewed pixels.
    add(
        _row(
            "ACB",
            "GEOGRAPHIC",
            99,
            "CURRENT",
            "2025-12-31",
            "ASSETS",
            (
                ("NORTH", "140.219.594", 20),
                ("CENTRAL", "90.839.097", 21),
                ("SOUTH", "1.003.485.154", 22),
                ("ELIMINATION", "(208.693.718)", 22),
                ("TOTAL", "1.025.850.127", 22),
            ),
        )
    )
    add(
        _row(
            "ACB",
            "GEOGRAPHIC",
            99,
            "CURRENT",
            "2025-12-31",
            "LIABILITIES",
            (
                ("NORTH", "137.095.693", 24),
                ("CENTRAL", "89.410.455", 25),
                ("SOUTH", "900.466.263", 26),
                ("ELIMINATION", "(195.642.003)", 26),
                ("TOTAL", "931.330.408", 27),
            ),
        )
    )
    add(
        _row(
            "ACB",
            "GEOGRAPHIC",
            99,
            "COMPARATIVE",
            "2024-12-31",
            "ASSETS",
            (
                ("NORTH", "118.489.977", 48),
                ("CENTRAL", "83.630.526", 49),
                ("SOUTH", "824.808.130", 50),
                ("ELIMINATION", "(162.922.930)", 50),
                ("TOTAL", "864.005.703", 51),
            ),
        )
    )
    add(
        _row(
            "ACB",
            "GEOGRAPHIC",
            99,
            "COMPARATIVE",
            "2024-12-31",
            "LIABILITIES",
            (
                ("NORTH", "115.621.691", 53),
                ("CENTRAL", "82.275.095", 54),
                ("SOUTH", "738.010.161", 55),
                ("ELIMINATION", "(155.362.922)", 55),
                ("TOTAL", "780.544.025", 56),
            ),
        )
    )

    # MBB business branch, current and comparative.
    for period_role, period_end, profit_page, balance_page, profit, assets, fixed, liabilities in (
        (
            "CURRENT",
            "2025-12-31",
            83,
            84,
            (
                ("BANK", "31.139.240", 103),
                ("SECURITIES_FUND", "1.540.665", 105),
                ("INSURANCE", "626.189", 106),
                ("DEBT_ASSET", "962.264", 107),
                ("TOTAL", "34.268.358", 108),
            ),
            (
                ("BANK", "1.590.458.621", 29),
                ("SECURITIES_FUND", "31.478.443", 30),
                ("INSURANCE", "27.073.013", 31),
                ("DEBT_ASSET", "2.250.753", 32),
                ("ELIMINATION", "(35.496.903)", 33),
                ("TOTAL", "1.615.763.927", 34),
            ),
            (
                ("BANK", "5.026.150", 42),
                ("SECURITIES_FUND", "132.990", 43),
                ("INSURANCE", "397.833", 44),
                ("DEBT_ASSET", "59.574", 45),
                ("TOTAL", "5.616.547", 46),
            ),
            (
                ("BANK", "1.454.652.920", 55),
                ("SECURITIES_FUND", "22.819.473", 56),
                ("INSURANCE", "22.405.488", 57),
                ("DEBT_ASSET", "848.676", 58),
                ("ELIMINATION", "(26.985.155)", 59),
                ("TOTAL", "1.473.741.402", 60),
            ),
        ),
        (
            "COMPARATIVE",
            "2024-12-31",
            85,
            86,
            (
                ("BANK", "26.760.926", 103),
                ("SECURITIES_FUND", "1.002.025", 104),
                ("INSURANCE", "417.932", 105),
                ("DEBT_ASSET", "648.445", 106),
                ("TOTAL", "28.829.328", 107),
            ),
            (
                ("BANK", "1.111.192.632", 29),
                ("SECURITIES_FUND", "22.729.848", 30),
                ("INSURANCE", "23.113.662", 31),
                ("DEBT_ASSET", "1.950.940", 32),
                ("ELIMINATION", "(30.186.020)", 33),
                ("TOTAL", "1.128.801.062", 34),
            ),
            (
                ("BANK", "4.858.928", 43),
                ("SECURITIES_FUND", "166.443", 44),
                ("INSURANCE", "353.749", 45),
                ("DEBT_ASSET", "51.296", 46),
                ("TOTAL", "5.430.416", 47),
            ),
            (
                ("BANK", "998.651.487", 56),
                ("SECURITIES_FUND", "15.235.258", 57),
                ("INSURANCE", "18.999.635", 58),
                ("DEBT_ASSET", "797.055", 59),
                ("ELIMINATION", "(21.941.954)", 60),
                ("TOTAL", "1.011.741.481", 61),
            ),
        ),
    ):
        add(
            _row(
                "MBB", "BUSINESS", profit_page, period_role, period_end, "PROFIT_BEFORE_TAX", profit
            )
        )
        add(_row("MBB", "BUSINESS", balance_page, period_role, period_end, "ASSETS", assets))
        add(_row("MBB", "BUSINESS", balance_page, period_role, period_end, "FIXED_ASSETS", fixed))
        add(
            _row(
                "MBB", "BUSINESS", balance_page, period_role, period_end, "LIABILITIES", liabilities
            )
        )

    # MBB geographic branch.  Foreign is an equation component but not forced
    # into the broader schema axis "Khu vực khác".
    for period_role, period_end, profit_page, balance_page, profit, assets, fixed, liabilities in (
        (
            "CURRENT",
            "2025-12-31",
            87,
            88,
            (
                ("NORTH", "22.998.270", 101),
                ("CENTRAL", "2.120.016", 102),
                ("SOUTH", "9.110.383", 103),
                ("FOREIGN_SOURCE_ONLY", "39.689", 104),
                ("TOTAL", "34.268.358", 105),
            ),
            (
                ("NORTH", "1.172.468.605", 26),
                ("CENTRAL", "73.486.567", 27),
                ("SOUTH", "391.719.355", 28),
                ("FOREIGN_SOURCE_ONLY", "13.586.303", 29),
                ("ELIMINATION", "(35.496.903)", 30),
                ("TOTAL", "1.615.763.927", 31),
            ),
            (
                ("NORTH", "4.970.480", 39),
                ("CENTRAL", "78.441", 40),
                ("SOUTH", "204.175", 41),
                ("FOREIGN_SOURCE_ONLY", "363.451", 42),
                ("TOTAL", "5.616.547", 43),
            ),
            (
                ("NORTH", "1.032.999.587", 52),
                ("CENTRAL", "71.795.670", 53),
                ("SOUTH", "384.462.199", 54),
                ("FOREIGN_SOURCE_ONLY", "11.469.101", 55),
                ("ELIMINATION", "(26.985.155)", 56),
                ("TOTAL", "1.473.741.402", 57),
            ),
        ),
        (
            "COMPARATIVE",
            "2024-12-31",
            89,
            90,
            (
                ("NORTH", "23.139.579", 101),
                ("CENTRAL", "1.461.056", 102),
                ("SOUTH", "4.202.760", 103),
                ("FOREIGN_SOURCE_ONLY", "25.933", 104),
                ("TOTAL", "28.829.328", 105),
            ),
            (
                ("NORTH", "790.548.293", 26),
                ("CENTRAL", "55.154.822", 27),
                ("SOUTH", "302.676.568", 28),
                ("FOREIGN_SOURCE_ONLY", "10.607.399", 29),
                ("ELIMINATION", "(30.186.020)", 30),
                ("TOTAL", "1.128.801.062", 31),
            ),
            (
                ("NORTH", "4.992.950", 39),
                ("CENTRAL", "47.907", 40),
                ("SOUTH", "153.718", 41),
                ("FOREIGN_SOURCE_ONLY", "235.841", 42),
                ("TOTAL", "5.430.416", 43),
            ),
            (
                ("NORTH", "671.599.607", 52),
                ("CENTRAL", "53.988.390", 53),
                ("SOUTH", "299.554.504", 54),
                ("FOREIGN_SOURCE_ONLY", "8.540.935", 55),
                ("ELIMINATION", "(21.941.955)", 56),
                ("TOTAL", "1.011.741.481", 57),
            ),
        ),
    ):
        add(
            _row(
                "MBB",
                "GEOGRAPHIC",
                profit_page,
                period_role,
                period_end,
                "PROFIT_BEFORE_TAX",
                profit,
            )
        )
        add(_row("MBB", "GEOGRAPHIC", balance_page, period_role, period_end, "ASSETS", assets))
        add(_row("MBB", "GEOGRAPHIC", balance_page, period_role, period_end, "FIXED_ASSETS", fixed))
        add(
            _row(
                "MBB",
                "GEOGRAPHIC",
                balance_page,
                period_role,
                period_end,
                "LIABILITIES",
                liabilities,
            )
        )

    # VPB business branch.  Finance-company and securities axes remain source-only.
    add(
        _row(
            "VPB",
            "BUSINESS",
            96,
            "CURRENT",
            "2025-12-31",
            "PROFIT_BEFORE_TAX",
            (
                ("BANK", "26.364.164", 105),
                ("FINANCE_COMPANY_SOURCE_ONLY", "611.472", 106),
                ("DEBT_ASSET", "8.703", 107),
                ("SECURITIES_SOURCE_ONLY", "4.475.585", 108),
                ("INSURANCE", "638.441", 109),
                ("ELIMINATION", "(1.473.416)", 110),
                ("TOTAL", "30.624.949", 111),
            ),
        )
    )
    add(
        _row(
            "VPB",
            "BUSINESS",
            96,
            "CURRENT",
            "2025-12-31",
            "ASSETS",
            (
                ("BANK", "1.170.921.217", 131),
                ("FINANCE_COMPANY_SOURCE_ONLY", "70.162.593", 132),
                ("DEBT_ASSET", "149.012", 133),
                ("SECURITIES_SOURCE_ONLY", "73.017.077", 134),
                ("INSURANCE", "7.664.503", 135),
                ("ELIMINATION", "(61.764.806)", 136),
                ("TOTAL", "1.260.149.596", 137),
            ),
        )
    )
    add(
        _row(
            "VPB",
            "BUSINESS",
            96,
            "CURRENT",
            "2025-12-31",
            "FIXED_ASSETS",
            (
                ("BANK", "1.711.510", 117),
                ("FINANCE_COMPANY_SOURCE_ONLY", "221.686", 118),
                ("SECURITIES_SOURCE_ONLY", "40.343", 119),
                ("INSURANCE", "55.147", 120),
                ("ELIMINATION", "138", 121),
                ("TOTAL", "2.028.824", 122),
            ),
        )
    )
    add(
        _row(
            "VPB",
            "BUSINESS",
            96,
            "CURRENT",
            "2025-12-31",
            "LIABILITIES",
            (
                ("BANK", "1.013.493.769", 161),
                ("FINANCE_COMPANY_SOURCE_ONLY", "58.987.323", 162),
                ("DEBT_ASSET", "1.260", 163),
                ("SECURITIES_SOURCE_ONLY", "39.186.036", 164),
                ("INSURANCE", "5.237.368", 165),
                ("ELIMINATION", "(37.031.789)", 166),
                ("TOTAL", "1.079.873.967", 167),
            ),
        )
    )

    # HDB geographic assets and liabilities; foreign remains source-only.
    add(
        _row(
            "HDB",
            "GEOGRAPHIC",
            61,
            "CURRENT",
            "2025-12-31",
            "ASSETS",
            (
                ("NORTH", "221.093.551", 68),
                ("CENTRAL", "65.618.324", 69),
                ("SOUTH", "656.684.158", 70),
                ("FOREIGN_SOURCE_ONLY", "1.164", 71),
                ("ELIMINATION", "(12.293.252)", 72),
                ("TOTAL", "931.103.945", 73),
            ),
        )
    )
    add(
        _row(
            "HDB",
            "GEOGRAPHIC",
            61,
            "CURRENT",
            "2025-12-31",
            "LIABILITIES",
            (
                ("NORTH", "208.903.649", 75),
                ("CENTRAL", "63.873.865", 76),
                ("SOUTH", "592.330.832", 77),
                ("FOREIGN_SOURCE_ONLY", "3.329", 78),
                ("ELIMINATION", "(12.293.252)", 79),
                ("TOTAL", "852.818.423", 80),
            ),
        )
    )

    # VCB geographic and business PBT.  Combined Central/Highlands, foreign,
    # non-bank finance, securities and other are equation-only source axes.
    add(
        _row(
            "VCB",
            "GEOGRAPHIC",
            71,
            "CURRENT",
            "2025-12-31",
            "PROFIT_BEFORE_TAX",
            (
                ("NORTH", "17.605.239", 159),
                ("CENTRAL_HIGHLANDS_SOURCE_ONLY", "6.150.072", 160),
                ("SOUTH", "20.187.170", 161),
                ("FOREIGN_SOURCE_ONLY", "77.970", 162),
                ("ELIMINATION", "(814)", 163),
                ("TOTAL", "44.019.637", 164),
            ),
        )
    )
    add(
        _row(
            "VCB",
            "BUSINESS",
            72,
            "CURRENT",
            "2025-12-31",
            "PROFIT_BEFORE_TAX",
            (
                ("BANK", "43.026.634", 155),
                ("NON_BANK_FINANCE_SOURCE_ONLY", "97.676", 156),
                ("SECURITIES_SOURCE_ONLY", "761.807", 157),
                ("OTHER_SOURCE_ONLY", "134.334", 158),
                ("ELIMINATION", "(814)", 159),
                ("TOTAL", "44.019.637", 160),
            ),
        )
    )

    # CTG geographic current and comparative.  Comparative liability
    # elimination is independently read from pixels as (5.341.026), correcting
    # the VietOCR proposal (6.341.026); the printed total closes exactly.
    for period_role, period_end, pbt, assets, liabilities in (
        (
            "CURRENT",
            "2025-12-31",
            (
                ("NORTH", "24.425.848", 22),
                ("SOUTH", "12.979.465", 23),
                ("OTHER", "5.735.170", 24),
                ("ELIMINATION", "303.326", 25),
                ("TOTAL", "43.443.809", 26),
            ),
            (
                ("NORTH", "1.802.387.498", 49),
                ("SOUTH", "699.765.098", 50),
                ("OTHER", "274.102.058", 51),
                ("ELIMINATION", "(8.555.354)", 52),
                ("TOTAL", "2.767.699.300", 53),
            ),
            (
                ("NORTH", "1.641.258.028", 56),
                ("SOUTH", "686.785.633", 57),
                ("OTHER", "266.814.453", 58),
                ("ELIMINATION", "(6.813.819)", 59),
                ("TOTAL", "2.588.044.295", 60),
            ),
        ),
        (
            "COMPARATIVE",
            "2024-12-31",
            (
                ("NORTH", "13.079.675", 77),
                ("SOUTH", "12.953.682", 78),
                ("OTHER", "5.422.109", 79),
                ("ELIMINATION", "308.459", 80),
                ("TOTAL", "31.763.925", 81),
            ),
            (
                ("NORTH", "1.497.983.716", 103),
                ("SOUTH", "654.673.282", 104),
                ("OTHER", "240.300.240", 105),
                ("ELIMINATION", "(7.569.506)", 106),
                ("TOTAL", "2.385.387.732", 107),
            ),
            (
                ("NORTH", "1.367.019.848", 110),
                ("SOUTH", "641.600.790", 111),
                ("OTHER", "233.603.412", 112),
                ("ELIMINATION", "(5.341.026)", 113),
                ("TOTAL", "2.236.883.024", 114),
            ),
        ),
    ):
        add(_row("CTG", "GEOGRAPHIC", 84, period_role, period_end, "PROFIT_BEFORE_TAX", pbt))
        add(_row("CTG", "GEOGRAPHIC", 84, period_role, period_end, "ASSETS", assets))
        add(_row("CTG", "GEOGRAPHIC", 84, period_role, period_end, "LIABILITIES", liabilities))

    # BID business table is rotated.  The authenticated rescue supplies exact
    # crop locators; finance lease, securities and other remain source-only.
    add(
        _row(
            "BID",
            "BUSINESS",
            37,
            "CURRENT",
            "2025-12-31",
            "PROFIT_BEFORE_TAX",
            (
                ("BANK", "28.631.155", 160),
                ("FINANCE_LEASE_SOURCE_ONLY", "42.050", 135),
                ("INSURANCE", "550.530", 113),
                ("SECURITIES_SOURCE_ONLY", "434.482", 89),
                ("OTHER_SOURCE_ONLY", "12.618", 65),
                ("ELIMINATION", "759.295", 45),
                ("TOTAL", "30.430.130", 22),
            ),
            evidence_mode="ROTATED_VIETOCR_PIXEL_BOUND",
        )
    )
    add(
        _row(
            "BID",
            "BUSINESS",
            37,
            "CURRENT",
            "2025-12-31",
            "ASSETS",
            (
                ("BANK", "3.320.294.997", 161),
                ("FINANCE_LEASE_SOURCE_ONLY", "7.600.316", 136),
                ("INSURANCE", "10.092.706", 114),
                ("SECURITIES_SOURCE_ONLY", "16.580.746", 90),
                ("OTHER_SOURCE_ONLY", "133.671", 66),
                ("ELIMINATION", "(23.876.716)", 46),
                ("TOTAL", "3.330.825.720", 23),
            ),
            evidence_mode="ROTATED_VIETOCR_PIXEL_BOUND",
        )
    )
    add(
        _row(
            "BID",
            "BUSINESS",
            37,
            "CURRENT",
            "2025-12-31",
            "LIABILITIES",
            (
                ("BANK", "3.153.021.386", 162),
                ("FINANCE_LEASE_SOURCE_ONLY", "6.488.488", 137),
                ("INSURANCE", "6.709.612", 115),
                ("SECURITIES_SOURCE_ONLY", "11.363.126", 91),
                ("OTHER_SOURCE_ONLY", "18.241", 67),
                ("ELIMINATION", "(20.328.035)", 47),
                ("TOTAL", "3.157.272.818", 24),
            ),
            evidence_mode="ROTATED_VIETOCR_PIXEL_BOUND",
        )
    )

    # VIB geographic current and comparative.  Central fixed-asset cells are
    # blank, not dashes, and are neither zeroed nor used in an exact equation.
    for period_role, period_end, page, pbt, assets, fixed, liabilities in (
        (
            "CURRENT",
            "2025-12-31",
            61,
            (
                ("NORTH", "3.871.992", 76),
                ("CENTRAL", "845.771", 77),
                ("SOUTH", "4.386.853", 78),
                ("TOTAL", "9.104.616", 79),
            ),
            (
                ("NORTH", "107.514.559", 98),
                ("CENTRAL", "33.493.460", 99),
                ("SOUTH", "415.090.422", 100),
                ("TOTAL", "556.098.441", 101),
            ),
            (
                ("NORTH", "1.114", 89),
                ("CENTRAL_BLANK_SOURCE_ONLY", None, None),
                ("SOUTH", "845.745", 90),
                ("TOTAL", "846.859", 91),
            ),
            (
                ("NORTH", "163.662.716", 120),
                ("CENTRAL", "20.285.711", 121),
                ("SOUTH", "325.245.275", 122),
                ("TOTAL", "509.193.702", 123),
            ),
        ),
        (
            "COMPARATIVE",
            "2024-12-31",
            62,
            (
                ("NORTH", "3.780.527", 72),
                ("CENTRAL", "846.277", 73),
                ("SOUTH", "4.377.498", 74),
                ("TOTAL", "9.004.302", 75),
            ),
            (
                ("NORTH", "81.174.891", 94),
                ("CENTRAL", "31.584.133", 95),
                ("SOUTH", "380.399.346", 96),
                ("TOTAL", "493.158.370", 97),
            ),
            (
                ("NORTH", "1.609", 85),
                ("CENTRAL_BLANK_SOURCE_ONLY", None, None),
                ("SOUTH", "793.660", 86),
                ("TOTAL", "795.269", 87),
            ),
            (
                ("NORTH", "151.366.463", 116),
                ("CENTRAL", "19.599.813", 117),
                ("SOUTH", "280.330.285", 118),
                ("TOTAL", "451.296.561", 119),
            ),
        ),
    ):
        add(_row("VIB", "GEOGRAPHIC", page, period_role, period_end, "PROFIT_BEFORE_TAX", pbt))
        add(_row("VIB", "GEOGRAPHIC", page, period_role, period_end, "ASSETS", assets))
        add(
            _row(
                "VIB",
                "GEOGRAPHIC",
                page,
                period_role,
                period_end,
                "FIXED_ASSETS",
                fixed,
                equation=False,
            )
        )
        add(_row("VIB", "GEOGRAPHIC", page, period_role, period_end, "LIABILITIES", liabilities))
    return rows


_STRUCTURE = {
    "ACB": {
        "branches": ("GEOGRAPHIC", "BUSINESS"),
        "geo_axes": ("NORTH", "CENTRAL", "SOUTH", "ELIMINATION", "TOTAL"),
        "business_axes": ("BANK", "ELIMINATION", "TOTAL"),
    },
    "MBB": {
        "branches": ("GEOGRAPHIC", "BUSINESS"),
        "geo_axes": ("NORTH", "CENTRAL", "SOUTH", "ELIMINATION", "TOTAL"),
        "business_axes": (
            "BANK",
            "SECURITIES_FUND",
            "INSURANCE",
            "DEBT_ASSET",
            "ELIMINATION",
            "TOTAL",
        ),
    },
    "VPB": {
        "branches": ("BUSINESS",),
        "geo_axes": (),
        "business_axes": ("BANK", "INSURANCE", "DEBT_ASSET", "ELIMINATION", "TOTAL"),
    },
    "HDB": {
        "branches": ("GEOGRAPHIC",),
        "geo_axes": ("NORTH", "CENTRAL", "SOUTH", "ELIMINATION", "TOTAL"),
        "business_axes": (),
    },
    "VCB": {
        "branches": ("GEOGRAPHIC", "BUSINESS"),
        "geo_axes": ("NORTH", "SOUTH", "ELIMINATION", "TOTAL"),
        "business_axes": ("BANK", "ELIMINATION", "TOTAL"),
    },
    "CTG": {
        "branches": ("GEOGRAPHIC", "BUSINESS"),
        "geo_axes": ("NORTH", "SOUTH", "OTHER", "ELIMINATION", "TOTAL"),
        "business_axes": ("BANK", "ELIMINATION", "TOTAL"),
    },
    "BID": {
        "branches": ("GEOGRAPHIC", "BUSINESS"),
        "geo_axes": (),
        "business_axes": ("BANK", "INSURANCE", "ELIMINATION", "TOTAL"),
    },
    "VIB": {
        "branches": ("GEOGRAPHIC",),
        "geo_axes": ("NORTH", "CENTRAL", "SOUTH", "TOTAL"),
        "business_axes": (),
    },
}

_OPEN_ITEMS = {
    "ACB": (
        (95, "Cho thuê tài chính", "SOURCE_BUSINESS_AXIS_NOT_PRESENT_IN_5807_5842"),
        (
            95,
            "Chứng khoán / Quản lý quỹ",
            "TWO_SOURCE_AXES_REQUIRE_CONTROLLED_AGGREGATION_TO_COMBINED_SCHEMA_AXIS",
        ),
        (
            95,
            "Kết quả kinh doanh bộ phận",
            "SOURCE_LABEL_DOES_NOT_EXPLICITLY_ESTABLISH_PROFIT_BEFORE_TAX",
        ),
    ),
    "MBB": (
        (87, "Nước ngoài", "SOURCE_GEOGRAPHIC_AXIS_IS_NOT_IDENTICAL_TO_KHU_VUC_KHAC"),
        (
            83,
            "Thu nhập / Chi phí",
            "INTERNAL_ELIMINATION_REVENUE_EXPENSE_RECONCILIATION_NOT_INCLUDED_IN_BOUNDED_REVIEW",
        ),
    ),
    "VPB": (
        (96, "Hoạt động công ty tài chính", "SOURCE_BUSINESS_AXIS_NOT_PRESENT_IN_5807_5842"),
        (96, "Hoạt động chứng khoán", "SOURCE_AXIS_NARROWER_THAN_CHUNG_KHOAN_QUAN_LY_QUY"),
    ),
    "HDB": (
        (61, "Nước ngoài", "SOURCE_GEOGRAPHIC_AXIS_IS_NOT_IDENTICAL_TO_KHU_VUC_KHAC"),
        (
            61,
            "Kết quả kinh doanh bộ phận",
            "SOURCE_LABEL_DOES_NOT_EXPLICITLY_ESTABLISH_PROFIT_BEFORE_TAX",
        ),
    ),
    "VCB": (
        (71, "Miền Trung và Tây Nguyên", "SOURCE_AXIS_BROADER_THAN_MIEN_TRUNG"),
        (71, "Nước ngoài", "SOURCE_GEOGRAPHIC_AXIS_NOT_PRESENT_IN_SCHEMA"),
        (
            72,
            "Dịch vụ tài chính phi ngân hàng / Chứng khoán / Khác",
            "SOURCE_BUSINESS_AXES_NOT_IDENTICAL_TO_LIVE_SCHEMA_AXES",
        ),
    ),
    "CTG": (
        (
            82,
            "Dịch vụ tài chính phi ngân hàng / Khác",
            "SOURCE_BUSINESS_AXES_NOT_IDENTICAL_TO_LIVE_SCHEMA_AXES",
        ),
        (
            82,
            "Bảng bộ phận kinh doanh xoay",
            "SUPPORTED_AXIS_NUMBERS_NOT_PROMOTED_WITHOUT_FULL_PIXEL_ROW_RECONCILIATION",
        ),
    ),
    "BID": (
        (
            37,
            "Cho thuê tài chính / Chứng khoán / Khác",
            "SOURCE_BUSINESS_AXES_NOT_IDENTICAL_TO_LIVE_SCHEMA_AXES",
        ),
        (
            38,
            "Trong nước / Nước ngoài",
            "SOURCE_GEOGRAPHIC_AXES_NOT_EQUIVALENT_TO_NORTH_CENTRAL_SOUTH_SCHEMA",
        ),
    ),
    "VIB": ((61, "Tài sản cố định — Miền Trung", "VISIBLE_CELL_IS_BLANK_NOT_DASH_AND_NOT_ZERO"),),
}


def _schema_snapshot(schema_by_id: Mapping[int, Any]) -> dict[str, Any]:
    rows = []
    for report_norm_id in range(5762, 5849):
        item = schema_by_id.get(report_norm_id)
        if item is None or item.statement_type != "TM" or "CONSOLIDATED" not in item.scope:
            raise _error(f"live TM segment row {report_norm_id} drifted")
        if report_norm_id in _EXPECTED_SCHEMA_NAMES and (
            item.canonical_name != _EXPECTED_SCHEMA_NAMES[report_norm_id]
        ):
            raise _error(f"live TM segment label {report_norm_id} drifted")
        rows.append(
            {
                "canonical_name": item.canonical_name,
                "display_order": item.display_order,
                "hierarchy_level": item.hierarchy_level,
                "parent_report_norm_id": item.parent_id,
                "report_norm_id": report_norm_id,
            }
        )
    if schema_by_id[5762].children != [5763, 5806]:
        raise _error("live TM segment root children drifted")
    return {"rows": rows}


def _schema_row(schema: Mapping[str, Any], report_norm_id: int) -> dict[str, Any]:
    return canonical_clone_v1(
        next(item for item in schema["rows"] if item["report_norm_id"] == report_norm_id)
    )


def _structure_bindings(schema: Mapping[str, Any], bank: str) -> list[dict[str, Any]]:
    record = _STRUCTURE[bank]
    ids = [5762]
    if "GEOGRAPHIC" in record["branches"]:
        ids.append(5763)
    if "BUSINESS" in record["branches"]:
        ids.append(5806)
    ids.extend(_GEO_AXIS_PARENT[item] for item in record["geo_axes"])
    ids.extend(_BUSINESS_AXIS_PARENT[item] for item in record["business_axes"])
    if len(ids) != len(set(ids)):
        raise _error("structure binding IDs duplicated")
    return [
        {
            **_schema_row(schema, report_norm_id),
            "status": "VERIFIED_BY_CODEX",
            "topology": "OWNER_BRANCH_AXIS_ORDER_GEOMETRY_PERIOD_UNIT",
        }
        for report_norm_id in ids
    ]


def _mapped_id(branch: str, axis: str, metric: str) -> int | None:
    parents = _GEO_AXIS_PARENT if branch == "GEOGRAPHIC" else _BUSINESS_AXIS_PARENT
    parent = parents.get(axis)
    return None if parent is None else parent + _METRIC_OFFSET[metric]


def _build_rows(
    index: Mapping[str, Any],
    manifest: Mapping[str, Any],
    rotated_by_key: Mapping[tuple[int, int, int], Mapping[str, Any]],
    schema: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    by_bank = {bank: [] for bank in EXPECTED_DOCUMENT_ORDER}
    for raw in _numeric_blueprint():
        bank = raw["bank"]
        document_ordinal = _document(index, bank)["document_ordinal"]
        cells = []
        mapped_values = []
        for axis, pixel_value, line_index in raw["cells"]:
            if pixel_value is None:
                evidence = None
                normalized = None
                source_status = "BLANK"
            elif raw["evidence_mode"] == "ROTATED_VIETOCR_PIXEL_BOUND":
                evidence = _rotated_event(rotated_by_key, document_ordinal, raw["page"], line_index)
                normalized = _money(pixel_value)
                source_status = "VALUE"
            else:
                evidence = _event(index, bank, raw["page"], line_index)
                normalized = _money(pixel_value)
                source_status = "VALUE"
            report_norm_id = _mapped_id(raw["branch"], axis, raw["metric"])
            cell = {
                "axis_key": axis,
                "evidence": evidence,
                "normalized_value": normalized,
                "pixel_transcription": pixel_value,
                "report_norm_id": report_norm_id,
                "source_cell_status": source_status,
            }
            cells.append(cell)
            if report_norm_id is not None:
                mapped_values.append(
                    {
                        **_schema_row(schema, report_norm_id),
                        "axis_key": axis,
                        "evidence": canonical_clone_v1(evidence),
                        "metric_key": raw["metric"],
                        "normalized_value": normalized,
                        "period_end": raw["period_end"],
                        "period_role": raw["period_role"],
                        "physical_page": raw["page"],
                        "pixel_transcription": pixel_value,
                        "source_cell_status": source_status,
                        "status": "VERIFIED_BY_CODEX",
                    }
                )
        total = next((item for item in cells if item["axis_key"] == "TOTAL"), None)
        if total is None or total["normalized_value"] is None:
            raise _error("numeric row lacks total")
        if raw["equation"]:
            components = [item["normalized_value"] for item in cells if item["axis_key"] != "TOTAL"]
            if (
                any(value is None for value in components)
                or sum(components) != total["normalized_value"]
            ):
                raise _error(
                    f"{bank} {raw['branch']} {raw['metric']} {raw['period_role']} does not close"
                )
            equation = {
                "component_values": components,
                "computed_total": sum(components),
                "name": "ALL_VISIBLE_SOURCE_AXES_EQUAL_PRINTED_TOTAL",
                "status": "CORROBORATED_EXACT",
                "visible_total": total["normalized_value"],
            }
        else:
            equation = {
                "name": "NOT_TESTABLE_BLANK_COMPONENT_NOT_COERCED_TO_ZERO",
                "status": "NOT_TESTABLE",
            }
        by_bank[bank].append(
            {
                "branch": raw["branch"],
                "cells": cells,
                "evidence_mode": raw["evidence_mode"],
                "metric_key": raw["metric"],
                "period_end": raw["period_end"],
                "period_role": raw["period_role"],
                "physical_page": raw["page"],
                "render_ref": _render_ref(manifest, bank, raw["page"]),
                "verified_accounting_equation": equation,
                "verified_numeric_assignments": mapped_values,
            }
        )
    return by_bank


def _build_payload() -> tuple[dict[str, Any], dict[str, Any]]:
    index = _fixed_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    manifest = _fixed_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    if hashlib.sha256(_stable_bytes(ROTATED_CROP_MANIFEST_PATH)).hexdigest() != (
        EXPECTED_ROTATED_CROP_MANIFEST_SHA256
    ):
        raise _error("annual rotated crop manifest drifted")
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
    rotated_support = _load_rotated_rescue()
    rotated_support._activate_profile("annual-2025")
    rotated = rotated_support.read_verified_full_document_rotated_vietocr_rescue_v1()
    if rotated["projection_id"] != EXPECTED_ROTATED_PROJECTION_ID:
        raise _error("annual rotated projection drifted")
    scans = _scan_all(index, rotated)
    _, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    schema = _schema_snapshot(schema_by_id)
    rows_by_bank = _build_rows(index, manifest, _rotated_samples(rotated), schema)
    trials = []
    structure_count = 0
    numeric_count = 0
    equation_count = 0
    source_only_count = 0
    blank_count = 0
    open_count = 0
    for bank in EXPECTED_DOCUMENT_ORDER:
        document = _document(index, bank)
        structure = _structure_bindings(schema, bank)
        numeric_rows = rows_by_bank[bank]
        assignments = [
            assignment for row in numeric_rows for assignment in row["verified_numeric_assignments"]
        ]
        source_only_count += sum(
            cell["report_norm_id"] is None and cell["source_cell_status"] == "VALUE"
            for row in numeric_rows
            for cell in row["cells"]
        )
        blank_count += sum(
            cell["source_cell_status"] == "BLANK" for row in numeric_rows for cell in row["cells"]
        )
        equations = [
            row["verified_accounting_equation"]
            for row in numeric_rows
            if row["verified_accounting_equation"]["status"] == "CORROBORATED_EXACT"
        ]
        open_items = [
            {"physical_page": page, "reason": reason, "source_label": label, "status": "UNRESOLVED"}
            for page, label, reason in _OPEN_ITEMS[bank]
        ]
        detailed_geo = "GEOGRAPHIC" in _STRUCTURE[bank]["branches"]
        detailed_business = "BUSINESS" in _STRUCTURE[bank]["branches"]
        trial = {
            "bank_code": bank,
            "bounded_absences": {
                "detailed_business_report": (
                    None if detailed_business else "NOT_OBSERVED_IN_BOUND_ANNUAL_REPORT"
                ),
                "detailed_geographic_report": (
                    None if detailed_geo else "NOT_OBSERVED_IN_BOUND_ANNUAL_REPORT"
                ),
            },
            "document_ordinal": document["document_ordinal"],
            "evidence_page_sequence": _EXPECTED_REGIONS[bank],
            "open_source_items": open_items,
            "scan": canonical_clone_v1(scans[bank]),
            "source_pdf_sha256": document["source_pdf"]["sha256"],
            "status": "VERIFIED_BY_CODEX_WITH_EXPLICIT_SOURCE_ONLY_VARIANTS",
            "verified_numeric_assignments": assignments,
            "verified_numeric_rows": numeric_rows,
            "verified_structure_bindings": structure,
        }
        trials.append(trial)
        structure_count += len(structure)
        numeric_count += len(assignments)
        equation_count += len(equations)
        open_count += len(open_items)
    metrics = {
        "accounting_equation_verified_count": equation_count,
        "blank_cell_preserved_count": blank_count,
        "detailed_business_report_absence_count": 2,
        "detailed_geographic_report_absence_count": 1,
        "document_count": 8,
        "document_unique_region_count": 8,
        "numeric_assignment_verified_count": numeric_count,
        "related_party_family_processed_count": 0,
        "source_only_equation_component_count": source_only_count,
        "source_only_open_item_count": open_count,
        "structure_binding_verified_count": structure_count,
    }
    review_material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": REVIEW_FORMAT,
        "review_checks": {
            "all_eight_complete_pdfs_scanned": True,
            "all_matched_segment_renders_opened": True,
            "blank_cells_not_coerced_to_zero": True,
            "broader_or_narrower_axes_retained_source_only": True,
            "current_and_comparative_periods_derived_from_pdf": True,
            "related_party_root_5750_skipped_by_project_owner": True,
            "rotated_tables_replayed_with_authenticated_rescue": True,
            "supported_numeric_rows_close_to_printed_totals": True,
        },
        "reviewer": {"kind": "CODEX_INDEPENDENT_SOURCE_REVIEW"},
        "trials": canonical_clone_v1(trials),
    }
    review = {
        **review_material,
        "review_id": REVIEW_PREFIX + canonical_json_sha256_v1(review_material),
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
            "period_projection_id": periods["projection_id"],
            "rotated_crop_manifest": {
                "path": ROTATED_CROP_MANIFEST_PATH.as_posix(),
                "sha256": EXPECTED_ROTATED_CROP_MANIFEST_SHA256,
            },
            "rotated_projection_id": rotated["projection_id"],
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": EXPECTED_INDEX_SHA256,
            },
        },
        "metrics": metrics,
        "schema_family": {
            "first_report_norm_id": 5762,
            "last_report_norm_id": 5848,
            "root": _schema_row(schema, 5762),
        },
        "state": STATE,
        "trials": trials,
    }
    result = {**material, "result_id": RESULT_PREFIX + canonical_json_sha256_v1(material)}
    return result, review


def _validate_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("annual segment-report result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["state"] != STATE
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or value["metrics"].get("related_party_family_processed_count") != 0
    ):
        raise _error("annual segment-report identity or authority drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_PREFIX + canonical_json_sha256_v1(material):
        raise _error("annual segment-report result identity drifted")
    return canonical_clone_v1(value)


def build_live_annual_2025_consolidated_segment_report_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    """Build the live, exact annual consolidated segment-report result."""

    result, _review = _build_payload()
    return _validate_shape(result)


def validate_annual_2025_consolidated_segment_report_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Validate shape and exact-rebuild the result from fixed live evidence."""

    persisted = _validate_shape(value)
    expected, _review = _build_payload()
    if not same_typed_json_v1(persisted, expected):
        raise _error("annual segment-report result does not exact-replay")
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
    persisted_review = _strict_json(_stable_bytes(REVIEW_PATH), REVIEW_PATH.as_posix())
    expected, expected_review = _build_payload()
    if not same_typed_json_v1(persisted_review, expected_review):
        raise _error("annual segment-report pixel review does not exact-replay")
    validate_annual_2025_consolidated_segment_report_8bank_codex_verified_mapping_replay_v1(
        persisted
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("annual segment-report persisted result drifted")
    print(persisted["result_id"])


if __name__ == "__main__":
    _main()
