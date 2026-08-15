"""Verify the purchased-debt note family in all eight fixed bank PDFs.

The complete-PDF matcher is bank blind.  This bounded post-scan stage binds
the four unique source regions to independently reviewed PDF pixels, their
period/unit axes, first/last/next-family boundaries, accounting equations and
the live TM schema interval 800..5739.  ACB, VCB, CTG and BID are retained as
bounded not-observed outcomes for the supplied reports.

Fresh VietOCR Transformer proposals are semantic anchors only.  Visible PDF
pixels are the numeric source of truth.  A DASH is zero only when the fixed
pixel review records the visible DASH in the bound render.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "PurchasedDebt8BankCodexVerifiedMappingV1Error",
    "build_live_purchased_debt_8bank_codex_verified_mapping_v1",
    "build_purchased_debt_8bank_codex_verified_mapping_v1",
    "validate_purchased_debt_8bank_codex_verified_mapping_replay_v1",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load purchased-debt support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


support = _load_module(
    "trading_securities_support_for_purchased_debt_v1",
    "build_trading_securities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "purchased_debt_scan_for_codex_verified_mapping_v1",
    "scan_purchased_debt_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "PURCHASED_DEBT_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "PURCHASED_DEBT_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_SHARED_PURCHASED_DEBT_GRAPH_"
    "FIRST_LAST_NEXT_FAMILY_BOUNDARY_HORIZONTAL_VERTICAL_HYBRID_LAYOUT_"
    "VISIBLE_PDF_PIXEL_PERIOD_UNIT_DASH_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_"
    "NO_EXPORT_CANONICALIZATION_OR_OPTIONAL_BRANCH_MAPPING_AUTHORITY"
)
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
REVIEW_PATH = Path("docs/experiments/E-0066-purchased-debt-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0066-purchased-debt-8bank-codex-verified-mapping-v1.json")
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_SCAN_ID = "pdfdsv1:scan:6ebf6df34d69223bf45f696a054d71bc1b3edaf34c52ba3ae10b8e7898e025fd"
REVIEW_SHA256 = "e851895bb9fa622dfa0a1b7921eeeb1a3357c54c256ae96e5411f3c12050d8ec"

_CHECKS = [
    "COMPLETE_PDF_REGION_ENUMERATION",
    "FIRST_LAST_AND_NEXT_FAMILY_BOUNDARY",
    "HORIZONTAL_VERTICAL_OR_HYBRID_LAYOUT",
    "PERIOD_UNIT_AND_REPORT_SCOPE",
    "VISIBLE_PIXEL_LABEL_DIGITS_DASH_AND_SIGN",
    "BALANCE_NET_AND_PRINCIPAL_INTEREST_EQUATIONS",
    "OPTIONAL_BRANCH_NOT_ADDED_TO_CORE",
    "LIVE_TM_SCHEMA_PARENT_CHILD_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_coerced_to_zero": False,
    "dash_coerced_to_zero_only_when_visible_in_pdf": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "historical_or_optional_branch_mapped_into_current_core": False,
    "mapping_decided_by_text_similarity_alone": False,
    "source_order_and_cluster_boundaries_required": True,
    "visible_pdf_pixels_used_for_numeric_truth": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "dash_zero_requires_visible_pixel": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_four_unique_purchased_debt_regions": True,
    "not_observed_is_bounded_to_supplied_pdf": True,
    "optional_quality_provision_movement_or_historical_mapping_authority": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_refs",
    "metrics",
    "result_id",
    "state",
    "trials",
}
_SCHEMA_EXPECTED = {
    800: ("Hoạt động mua nợ", 560, 260),
    801: ("Mua nợ bằng VNĐ", 800, 261),
    802: ("Mua nợ bằng ngoại tệ", 800, 262),
    803: ("Dự phòng rủi ro", 800, 263),
    5738: ("Nợ gốc đã mua", 800, 264),
    5739: ("Lãi của khoản nợ đã mua", 800, 265),
    804: ("Chứng khoán đầu tư", 560, 266),
}
_VERIFIED_CODES = {"MBB", "VPB", "HDB", "VIB"}
_NOT_OBSERVED_CODES = {"ACB", "VCB", "CTG", "BID"}


class PurchasedDebt8BankCodexVerifiedMappingV1Error(ValueError):
    """The scan, pixel review, accounting, or live schema drifted."""


def _error(message: str) -> PurchasedDebt8BankCodexVerifiedMappingV1Error:
    return PurchasedDebt8BankCodexVerifiedMappingV1Error(message)


def _line(line_index: int, pixel_transcription: str) -> dict[str, Any]:
    return {"line_index": line_index, "pixel_transcription": pixel_transcription}


def _dash(pixel_region_bbox: Sequence[int]) -> dict[str, Any]:
    return {
        "line_index": None,
        "pixel_region_bbox": list(pixel_region_bbox),
        "pixel_transcription": "-",
    }


def _row(
    role: str,
    report_norm_id: int,
    label_line: int,
    label_pixel: str,
    current: Mapping[str, Any],
    comparative: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "label": _line(label_line, label_pixel),
        "report_norm_id": report_norm_id,
        "role": role,
        "values": [
            {"period_role": "CURRENT", **canonical_clone_v1(current)},
            {"period_role": "COMPARATIVE", **canonical_clone_v1(comparative)},
        ],
    }


def _period(
    role: str, period: str, heading: Sequence[tuple[int, str]], unit: tuple[int, str]
) -> dict[str, Any]:
    return {
        "heading": [_line(index, text) for index, text in heading],
        "period": period,
        "period_role": role,
        "unit": _line(unit[0], unit[1]),
    }


def _boundary(
    first: tuple[int, int, str],
    last: tuple[int, int, str],
    next_family: tuple[int, int, str],
) -> dict[str, Any]:
    def item(value: tuple[int, int, str]) -> dict[str, Any]:
        return {
            "line_index": value[1],
            "page_sequence": value[0],
            "pixel_transcription": value[2],
        }

    return {
        "first_item": item(first),
        "last_item": item(last),
        "next_family_boundary": item(next_family),
    }


def _optional_equation(
    role: str,
    page_sequence: int,
    render_sha256: str,
    addends: Sequence[Mapping[str, Any]],
    total: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "addends": [canonical_clone_v1(item) for item in addends],
        "page_sequence": page_sequence,
        "render_sha256": render_sha256,
        "role": role,
        "total": canonical_clone_v1(total),
    }


def _checks(verified: bool) -> dict[str, str]:
    if verified:
        return {check: "PASS" for check in _CHECKS}
    return {
        check: "PASS_COMPLETE_PDF_NEGATIVE_ENUMERATION"
        if check == "COMPLETE_PDF_REGION_ENUMERATION"
        else "NOT_APPLICABLE_NOT_OBSERVED"
        for check in _CHECKS
    }


def _absent(code: str) -> dict[str, Any]:
    return {
        "bank_code": code,
        "checks": _checks(False),
        "disposition": "NOT_OBSERVED_IN_BOUND_SOURCE_SCOPE",
        "family_boundary": None,
        "layout": None,
        "optional_equations": [],
        "pages": [],
    }


def _page_review(
    page_sequence: int,
    render_sha256: str,
    layout: str,
    periods: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    balance_net: Sequence[Mapping[str, Any]],
    detail_total: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "balance_net": [canonical_clone_v1(item) for item in balance_net],
        "detail_total": [canonical_clone_v1(item) for item in detail_total],
        "layout": layout,
        "page_sequence": page_sequence,
        "period_axes": [canonical_clone_v1(item) for item in periods],
        "render_sha256": render_sha256,
        "rows": [canonical_clone_v1(item) for item in rows],
    }


def _review_documents() -> list[dict[str, Any]]:
    mbb_render = "0db13918f14d088bce98cec6b51ecfe7d5d14e82a4c4057bc7d3b99f34abf107"
    vpb_render = "63d63e817c1724bdf93ad9c4143a32c553cd69d84d2eae801a6f9a142809043d"
    hdb_render = "fbb5d76db54e1bef2fdbe86d01c394955383ab3f91ad19664288bf7a5ccbbf0c"
    vib_render = "598220f8e5066a31bbe846dba642e70bdc1730ff2f1b12d0d89194234c3d095e"
    documents = {code: _absent(code) for code in _NOT_OBSERVED_CODES}
    documents["MBB"] = {
        "bank_code": "MBB",
        "checks": _checks(True),
        "disposition": "VERIFIED_UNIQUE_COMPLETE_PURCHASED_DEBT_REGION",
        "family_boundary": _boundary(
            (35, 1, "Hoạt động mua nợ"),
            (35, 22, "Lãi của khoản nợ đã mua"),
            (35, 26, "Chứng khoán đầu tư"),
        ),
        "layout": "ROWS_BY_ITEM_COLUMNS_BY_EXACT_DATE_AND_UNIT",
        "optional_equations": [],
        "pages": [
            _page_review(
                35,
                mbb_render,
                "TWO_DATE_COLUMNS_SHARED_ROW_AXIS",
                [
                    _period("CURRENT", "2026-06-30", [(2, "30/06/2026")], (4, "Triệu đồng")),
                    _period("COMPARATIVE", "2025-12-31", [(3, "31/12/2025")], (5, "Triệu đồng")),
                ],
                [
                    _row(
                        "PURCHASE_VND",
                        801,
                        6,
                        "Mua nợ bằng VND",
                        _line(7, "2.247.703"),
                        _line(8, "2.465.314"),
                    ),
                    _row(
                        "PROVISION",
                        803,
                        9,
                        "Dự phòng rủi ro",
                        _line(10, "(21.636)"),
                        _line(11, "(21.419)"),
                    ),
                    _row(
                        "PRINCIPAL",
                        5738,
                        19,
                        "Nợ gốc đã mua",
                        _line(20, "2.247.703"),
                        _line(21, "2.465.314"),
                    ),
                    _row(
                        "INTEREST",
                        5739,
                        22,
                        "Lãi của khoản nợ đã mua",
                        _dash([1180, 650, 1235, 690]),
                        _dash([1420, 650, 1475, 690]),
                    ),
                ],
                [_line(12, "2.226.067"), _line(13, "2.443.895")],
                [_line(23, "2.247.703"), _line(24, "2.465.314")],
            )
        ],
    }
    documents["VPB"] = {
        "bank_code": "VPB",
        "checks": _checks(True),
        "disposition": "VERIFIED_UNIQUE_COMPLETE_PURCHASED_DEBT_REGION",
        "family_boundary": _boundary(
            (46, 5, "HOẠT ĐỘNG MUA NỢ"),
            (46, 30, "Lãi của khoản nợ đã mua và chênh lệch giá mua nợ"),
            (47, 5, "CHỨNG KHOÁN ĐẦU TƯ"),
        ),
        "layout": "ROWS_BY_ITEM_SPLIT_DATE_HEADER_COLUMNS_WITH_OPTIONAL_QUALITY_AND_MOVEMENT",
        "optional_equations": [
            _optional_equation(
                "CURRENT_PROVISION_MOVEMENT_CHECK_ONLY",
                46,
                vpb_render,
                [_line(59, "10.212"), _line(62, "(3.322)")],
                _line(65, "6.890"),
            ),
            _optional_equation(
                "COMPARATIVE_PROVISION_MOVEMENT_CHECK_ONLY",
                46,
                vpb_render,
                [_line(60, "6.044"), _line(63, "(405)")],
                _line(66, "5.639"),
            ),
        ],
        "pages": [
            _page_review(
                46,
                vpb_render,
                "TWO_DATE_COLUMNS_SPLIT_HEADER_LINES_AND_OPTIONAL_TABLES_BELOW",
                [
                    _period(
                        "CURRENT",
                        "2026-03-31",
                        [(6, "Ngày 31 tháng 3"), (8, "năm 2026")],
                        (10, "Triệu đồng"),
                    ),
                    _period(
                        "COMPARATIVE",
                        "2025-12-31",
                        [(7, "Ngày 31 tháng 12"), (9, "năm 2025")],
                        (11, "Triệu đồng"),
                    ),
                ],
                [
                    _row(
                        "PURCHASE_VND",
                        801,
                        12,
                        "Mua nợ bằng VND",
                        _line(13, "918.704"),
                        _line(14, "1.361.635"),
                    ),
                    _row(
                        "PROVISION",
                        803,
                        15,
                        "Dự phòng rủi ro",
                        _line(16, "(6.890)"),
                        _line(17, "(10.212)"),
                    ),
                    _row(
                        "PRINCIPAL",
                        5738,
                        27,
                        "Nợ gốc đã mua",
                        _line(28, "914.059"),
                        _line(29, "1.356.908"),
                    ),
                    _row(
                        "INTEREST",
                        5739,
                        30,
                        "Lãi của khoản nợ đã mua và chênh lệch giá mua nợ",
                        _line(31, "4.645"),
                        _line(32, "4.727"),
                    ),
                ],
                [_line(18, "911.814"), _line(19, "1.351.423")],
                [_line(33, "918.704"), _line(34, "1.361.635")],
            )
        ],
    }
    documents["HDB"] = {
        "bank_code": "HDB",
        "checks": _checks(True),
        "disposition": "VERIFIED_UNIQUE_COMPLETE_PURCHASED_DEBT_REGION",
        "family_boundary": _boundary(
            (29, 6, "Hoạt động mua nợ"),
            (29, 29, "Lãi của khoản nợ đã mua"),
            (29, 43, "Chứng khoán đầu tư"),
        ),
        "layout": "ROWS_BY_ITEM_COLUMNS_BY_RELATIVE_PERIOD_WITH_OPTIONAL_FX_AND_QUALITY",
        "optional_equations": [],
        "pages": [
            _page_review(
                29,
                hdb_render,
                "TWO_RELATIVE_PERIOD_COLUMNS_SHARED_ROW_AXIS",
                [
                    _period("CURRENT", "2026-06-30", [(7, "Số cuối kỳ")], (9, "Triệu VND")),
                    _period("COMPARATIVE", "2025-12-31", [(8, "Số đầu kỳ")], (10, "Triệu VND")),
                ],
                [
                    _row(
                        "PURCHASE_VND",
                        801,
                        11,
                        "Mua nợ bằng VND",
                        _line(12, "18.619.677"),
                        _line(13, "23.925.869"),
                    ),
                    _row(
                        "PURCHASE_FX",
                        802,
                        14,
                        "Mua nợ bằng ngoại tệ",
                        _line(15, "539.007"),
                        _dash([1450, 350, 1510, 390]),
                    ),
                    _row(
                        "PROVISION",
                        803,
                        16,
                        "Dự phòng rủi ro",
                        _line(17, "(143.690)"),
                        _line(18, "(179.444)"),
                    ),
                    _row(
                        "PRINCIPAL",
                        5738,
                        26,
                        "Nợ gốc đã mua",
                        _line(27, "19.158.684"),
                        _line(28, "23.925.869"),
                    ),
                    _row(
                        "INTEREST",
                        5739,
                        29,
                        "Lãi của khoản nợ đã mua",
                        _dash([1180, 625, 1245, 665]),
                        _dash([1450, 625, 1510, 665]),
                    ),
                ],
                [_line(19, "19.014.994"), _line(20, "23.746.425")],
                [_line(30, "19.158.684"), _line(31, "23.925.869")],
            )
        ],
    }
    documents["VIB"] = {
        "bank_code": "VIB",
        "checks": _checks(True),
        "disposition": "VERIFIED_UNIQUE_COMPLETE_PURCHASED_DEBT_REGION",
        "family_boundary": _boundary(
            (35, 33, "HOẠT ĐỘNG MUA NỢ"),
            (35, 67, "Lãi của khoản nợ đã mua"),
            (36, 5, "CHỨNG KHOÁN ĐẦU TƯ SẴN SÀNG ĐỂ BÁN"),
        ),
        "layout": "HISTORICAL_ACQUISITION_BLOCK_THEN_CURRENT_TWO_DATE_COLUMN_BALANCE_AND_DETAIL",
        "optional_equations": [
            _optional_equation(
                "HISTORICAL_2017_ACQUISITION_CHECK_ONLY",
                35,
                vib_render,
                [_line(40, "1.147.463"), _line(42, "3.426"), _line(44, "(18.940)")],
                _line(45, "1.131.949"),
            )
        ],
        "pages": [
            _page_review(
                35,
                vib_render,
                "HISTORICAL_VERTICAL_BLOCK_PLUS_TWO_DATE_COLUMNS_FOR_CURRENT_BALANCE",
                [
                    _period("CURRENT", "2026-06-30", [(47, "30/06/2026")], (49, "triệu đồng")),
                    _period("COMPARATIVE", "2025-12-31", [(48, "31/12/2025")], (50, "triệu đồng")),
                ],
                [
                    _row(
                        "PURCHASE_VND",
                        801,
                        51,
                        "Mua nợ bằng VND",
                        _line(52, "3.533"),
                        _line(53, "4.366"),
                    ),
                    _row(
                        "PROVISION",
                        803,
                        54,
                        "Dự phòng rủi ro",
                        _line(55, "(27)"),
                        _line(56, "(34)"),
                    ),
                    _row(
                        "PRINCIPAL",
                        5738,
                        64,
                        "Nợ gốc đã mua",
                        _line(65, "3.605"),
                        _line(66, "4.477"),
                    ),
                    _row(
                        "INTEREST",
                        5739,
                        67,
                        "Lãi của khoản nợ đã mua",
                        _line(68, "20"),
                        _line(69, "20"),
                    ),
                ],
                [_line(57, "3.506"), _line(58, "4.332")],
                [_line(70, "3.625"), _line(71, "4.497")],
            )
        ],
    }
    return [documents[code] for code in EXPECTED_DOCUMENT_ORDER]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "review_checks": list(_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": "E-0066",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0066:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex purchased-debt pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(documents: Any, code: str, label: str) -> dict[str, Any]:
    return support._document_by_code(documents, code, label)


def _page(document: Mapping[str, Any], page: int, label: str) -> dict[str, Any]:
    return support._page_by_number(document, page, label)


def _line_at(page: Mapping[str, Any], index: int) -> Mapping[str, Any]:
    lines = page.get("lines")
    if type(lines) is not list or not (0 <= index < len(lines)):
        raise _error("pixel-review source line locator drifted")
    line = lines[index]
    if type(line) is not dict or line.get("source_line_index") != index:
        raise _error("pixel-review source line axis drifted")
    return line


def _render(
    manifest_document: Mapping[str, Any], page_number: int, expected: str
) -> dict[str, Any]:
    manifest_page = _page(manifest_document, page_number, "crop manifest")
    render = manifest_page.get("render_binding")
    if type(render) is not dict or render.get("sha256") != expected:
        raise _error("pixel-review render binding drifted")
    return canonical_clone_v1(render)


def _render_dimensions(render_ref: Mapping[str, Any]) -> tuple[int, int]:
    width = render_ref.get("pixel_width")
    height = render_ref.get("pixel_height")
    if type(width) is int and type(height) is int and width > 0 and height > 0:
        return width, height
    path = render_ref.get("path")
    if type(path) is not str:
        raise _error("DASH render has no authenticated dimensions or fixed path")
    payload = support._stable_bytes(Path(path))
    if hashlib.sha256(payload).hexdigest() != render_ref["sha256"]:
        raise _error("DASH render bytes drifted")
    with Image.open(PROJECT_ROOT / Path(path)) as image:
        image.load()
        return image.width, image.height


def _event(
    semantic_document: Mapping[str, Any],
    manifest_document: Mapping[str, Any],
    page_number: int,
    spec: Mapping[str, Any],
    render_sha256: str,
) -> dict[str, Any]:
    pixel = spec.get("pixel_transcription")
    if type(pixel) is not str or not pixel:
        raise _error("pixel transcription must be one nonempty string")
    render_ref = _render(manifest_document, page_number, render_sha256)
    index = spec.get("line_index")
    if index is None:
        bbox = spec.get("pixel_region_bbox")
        if (
            pixel != "-"
            or type(bbox) is not list
            or len(bbox) != 4
            or any(type(item) is not int for item in bbox)
        ):
            raise _error("pixel-only DASH evidence drifted")
        width, height = _render_dimensions(render_ref)
        if not (0 <= bbox[0] < bbox[2] <= width and 0 <= bbox[1] < bbox[3] <= height):
            raise _error("pixel-only DASH bbox is outside the authenticated render")
        return {
            "crop_ref": None,
            "independent_pixel_transcription": pixel,
            "page_sequence": page_number,
            "pixel_region_bbox": list(bbox),
            "render_ref": render_ref,
            "semantic_proposal": None,
            "source_bbox_raw_pixels": None,
            "source_line_index": None,
        }
    if type(index) is not int:
        raise _error("pixel-review line index must be exact int or null DASH")
    semantic_page = _page(semantic_document, page_number, "semantic index")
    line = _line_at(semantic_page, index)
    crop_ref = line.get("crop_ref")
    text = line.get("vietocr_text")
    bbox = line.get("source_bbox_raw_pixels")
    if type(crop_ref) is not dict or type(text) is not str or type(bbox) is not list:
        raise _error("semantic line evidence drifted")
    return {
        "crop_ref": canonical_clone_v1(crop_ref),
        "independent_pixel_transcription": pixel,
        "page_sequence": page_number,
        "pixel_region_bbox": None,
        "render_ref": render_ref,
        "semantic_proposal": text,
        "source_bbox_raw_pixels": list(bbox),
        "source_line_index": index,
    }


def _money_evidence(
    semantic_document: Mapping[str, Any],
    manifest_document: Mapping[str, Any],
    page_number: int,
    spec: Mapping[str, Any],
    render_sha256: str,
) -> dict[str, Any]:
    value = _event(semantic_document, manifest_document, page_number, spec, render_sha256)
    normalized = support._money(value["independent_pixel_transcription"])
    semantic = value["semantic_proposal"]
    semantic_value = None
    if semantic is not None:
        try:
            semantic_value = support._money(semantic)
        except Exception:
            semantic_value = None
    return {
        **value,
        "normalized_value": normalized,
        "semantic_numeric_agrees": semantic_value == normalized,
        "source_cell_status": "DASH"
        if normalized == 0 and value["independent_pixel_transcription"] == "-"
        else "VALUE",
    }


def _label_evidence(
    semantic_document: Mapping[str, Any],
    manifest_document: Mapping[str, Any],
    page_number: int,
    spec: Mapping[str, Any],
    render_sha256: str,
) -> dict[str, Any]:
    return _event(semantic_document, manifest_document, page_number, spec, render_sha256)


def _boundary_evidence(
    semantic_document: Mapping[str, Any],
    manifest_document: Mapping[str, Any],
    boundary: Mapping[str, Any],
) -> dict[str, Any]:
    result = {}
    for key in ("first_item", "last_item", "next_family_boundary"):
        spec = boundary[key]
        page_number = spec["page_sequence"]
        render = _page(manifest_document, page_number, "crop manifest").get("render_binding")
        if type(render) is not dict or type(render.get("sha256")) is not str:
            raise _error("family-boundary render binding drifted")
        result[key] = _event(
            semantic_document, manifest_document, page_number, spec, render["sha256"]
        )
    return result


def _schema_binding(item: Any, expected_id: int) -> dict[str, Any]:
    name, parent, order = _SCHEMA_EXPECTED[expected_id]
    if (
        item.schema_id != expected_id
        or item.canonical_name != name
        or item.parent_id != parent
        or item.display_order != order
    ):
        raise _error(f"live TM schema item {expected_id} drifted")
    return {
        "canonical_name": name,
        "display_order": order,
        "parent_report_norm_id": parent,
        "report_norm_id": expected_id,
    }


def _equation(role: str, addends: Sequence[int], total: int) -> dict[str, Any]:
    computed = sum(addends)
    if computed != total:
        raise _error(f"visible purchased-debt accounting equation does not close: {role}")
    return {
        "addends": list(addends),
        "computed_total": computed,
        "role": role,
        "visible_total": total,
    }


def _trial(
    code: str,
    ordinal: int,
    review_document: Mapping[str, Any],
    scan_trial: Mapping[str, Any],
    semantic_index: Mapping[str, Any],
    crop_manifest: Mapping[str, Any],
    schema_bindings: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    semantic_document = _document(semantic_index["documents"], code, "semantic index")
    manifest_document = _document(crop_manifest["documents"], code, "crop manifest")
    matcher_result = scan_trial["matcher_result"]
    if review_document["disposition"] == "NOT_OBSERVED_IN_BOUND_SOURCE_SCOPE":
        if matcher_result["status"] != "UNRESOLVED_NO_COMPLETE_REGION":
            raise _error("not-observed PDF unexpectedly contains one complete family region")
        return {
            "bank_provenance": code,
            "document_ordinal": ordinal,
            "family_boundary": None,
            "layout": None,
            "optional_check_equations": [],
            "page_evidence": [],
            "source_pdf": canonical_clone_v1(semantic_document["source_pdf"]),
            "status": "NOT_OBSERVED_IN_BOUND_SOURCE_SCOPE",
            "structural_scan_result_id": matcher_result["result_id"],
            "verified_accounting_equations": [],
            "verified_mappings": [],
        }
    if matcher_result["status"] != "ACCEPTED_UNIQUE_VARIANT_GRAPH":
        raise _error("pixel-verified purchased-debt region is not unique in complete PDF")
    boundary = _boundary_evidence(
        semantic_document, manifest_document, review_document["family_boundary"]
    )
    page_evidence = []
    values_by_id: dict[int, list[dict[str, Any]]] = {}
    equations = []
    for page_review in review_document["pages"]:
        page_number = page_review["page_sequence"]
        render_sha = page_review["render_sha256"]
        periods = []
        for period in page_review["period_axes"]:
            periods.append(
                {
                    "heading": [
                        _label_evidence(
                            semantic_document,
                            manifest_document,
                            page_number,
                            item,
                            render_sha,
                        )
                        for item in period["heading"]
                    ],
                    "period": period["period"],
                    "period_role": period["period_role"],
                    "unit": _label_evidence(
                        semantic_document,
                        manifest_document,
                        page_number,
                        period["unit"],
                        render_sha,
                    ),
                }
            )
        rows = []
        row_values: dict[str, list[int]] = {}
        for row in page_review["rows"]:
            label = _label_evidence(
                semantic_document,
                manifest_document,
                page_number,
                row["label"],
                render_sha,
            )
            values = [
                {
                    "period_role": value["period_role"],
                    **_money_evidence(
                        semantic_document,
                        manifest_document,
                        page_number,
                        value,
                        render_sha,
                    ),
                }
                for value in row["values"]
            ]
            row_values[row["role"]] = [value["normalized_value"] for value in values]
            values_by_id[row["report_norm_id"]] = canonical_clone_v1(values)
            rows.append(
                {
                    "label": label,
                    "report_norm_id": row["report_norm_id"],
                    "role": row["role"],
                    "values": values,
                }
            )
        balance_net = [
            _money_evidence(semantic_document, manifest_document, page_number, item, render_sha)
            for item in page_review["balance_net"]
        ]
        detail_total = [
            _money_evidence(semantic_document, manifest_document, page_number, item, render_sha)
            for item in page_review["detail_total"]
        ]
        for index, period_role in enumerate(("CURRENT", "COMPARATIVE")):
            currency_addends = [row_values["PURCHASE_VND"][index]]
            if "PURCHASE_FX" in row_values:
                currency_addends.append(row_values["PURCHASE_FX"][index])
            currency_addends.append(row_values["PROVISION"][index])
            equations.append(
                _equation(
                    f"{period_role}_BALANCE_GROSS_CURRENCY_PLUS_PROVISION_EQUALS_NET",
                    currency_addends,
                    balance_net[index]["normalized_value"],
                )
            )
            equations.append(
                _equation(
                    f"{period_role}_PRINCIPAL_PLUS_INTEREST_EQUALS_DETAIL_TOTAL",
                    [
                        row_values["PRINCIPAL"][index],
                        row_values["INTEREST"][index],
                    ],
                    detail_total[index]["normalized_value"],
                )
            )
        semantic_page = _page(semantic_document, page_number, "semantic index")
        page_evidence.append(
            {
                "balance_net": balance_net,
                "detail_total": detail_total,
                "geometry_mode": semantic_page["geometry_mode"],
                "layout": page_review["layout"],
                "page_sequence": page_number,
                "period_axes": periods,
                "render_ref": _render(manifest_document, page_number, render_sha),
                "rows": rows,
                "source_projection": canonical_clone_v1(semantic_page["source_projection"]),
            }
        )
    optional_equations = []
    for optional in review_document["optional_equations"]:
        addends = [
            _money_evidence(
                semantic_document,
                manifest_document,
                optional["page_sequence"],
                item,
                optional["render_sha256"],
            )
            for item in optional["addends"]
        ]
        total = _money_evidence(
            semantic_document,
            manifest_document,
            optional["page_sequence"],
            optional["total"],
            optional["render_sha256"],
        )
        optional_equations.append(
            {
                **_equation(
                    optional["role"],
                    [item["normalized_value"] for item in addends],
                    total["normalized_value"],
                ),
                "mapping_authority": False,
                "source_addends": addends,
                "source_total": total,
            }
        )
    mappings = [
        {
            **canonical_clone_v1(schema_bindings[report_norm_id]),
            "source_values": canonical_clone_v1(values),
            "status": "VERIFIED_BY_CODEX",
        }
        for report_norm_id, values in values_by_id.items()
    ]
    return {
        "bank_provenance": code,
        "document_ordinal": ordinal,
        "family_boundary": boundary,
        "layout": review_document["layout"],
        "optional_check_equations": optional_equations,
        "page_evidence": page_evidence,
        "source_pdf": canonical_clone_v1(semantic_document["source_pdf"]),
        "status": "VERIFIED_BY_CODEX",
        "structural_scan_result_id": matcher_result["result_id"],
        "verified_accounting_equations": equations,
        "verified_mappings": mappings,
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) + len(trial["optional_check_equations"])
            for trial in trials
        ),
        "core_accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "dash_cell_verified_as_zero_count": sum(
            value["source_cell_status"] == "DASH"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["source_values"]
        ),
        "document_count": len(trials),
        "document_not_observed_count": sum(
            trial["status"] == "NOT_OBSERVED_IN_BOUND_SOURCE_SCOPE" for trial in trials
        ),
        "document_verified_count": sum(trial["status"] == "VERIFIED_BY_CODEX" for trial in trials),
        "mapped_value_cell_count": sum(
            len(mapping["source_values"])
            for trial in trials
            for mapping in trial["verified_mappings"]
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "optional_check_equation_count": sum(
            len(trial["optional_check_equations"]) for trial in trials
        ),
        "unresolved_mapping_count": 0,
    }


def build_purchased_debt_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_authority: Any,
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    """Build exact bounded purchased-debt mappings from replayed inputs."""

    checked_review = _review(review)
    if structure_scan.get("scan_id") != EXPECTED_SCAN_ID:
        raise _error("fixed complete-PDF purchased-debt scan identity drifted")
    if type(semantic_index) is not dict or type(crop_manifest) is not dict:
        raise _error("semantic index and crop manifest must be exact objects")
    if type(schema_authority) is not dict or type(schema_by_id) is not dict:
        raise _error("live TM schema authority drifted")
    schema_bindings = {
        report_norm_id: _schema_binding(schema_by_id[report_norm_id], report_norm_id)
        for report_norm_id in _SCHEMA_EXPECTED
    }
    if (
        schema_by_id[800].children != [801, 802, 803, 5738, 5739]
        or schema_by_id[5739].next_id != 804
        or schema_by_id[804].previous_id != 5739
    ):
        raise _error("purchased-debt first/last/next schema boundary drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        review_document = next(
            item for item in checked_review["documents"] if item["bank_code"] == code
        )
        scan_trial = next(
            item for item in structure_scan["trials"] if item["document_provenance"] == code
        )
        trials.append(
            _trial(
                code,
                ordinal,
                review_document,
                scan_trial,
                semantic_index,
                crop_manifest,
                schema_bindings,
            )
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest_sha256": crop_manifest_sha256,
            "pixel_review_id": checked_review["review_id"],
            "pixel_review_sha256": review_sha256,
            "purchased_debt_scan_id": structure_scan["scan_id"],
            "semantic_axis_sha256": structure_scan["input_semantic_axis_sha256"],
            "tm_schema_projection_sha256": schema_authority["tm_schema_projection_sha256"],
        },
        "metrics": _metrics(trials),
        "state": "CODEX_VERIFIED_PURCHASED_DEBT_MAPPING_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0066:result:" + canonical_json_sha256_v1(material)}
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("purchased-debt verified result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "CODEX_VERIFIED_PURCHASED_DEBT_MAPPING_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("purchased-debt verified identity, authority or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("bank_provenance") != code
            or trial.get("status")
            not in {"VERIFIED_BY_CODEX", "NOT_OBSERVED_IN_BOUND_SOURCE_SCOPE"}
        ):
            raise _error("purchased-debt verified trial identity drifted")
        if trial["status"] == "VERIFIED_BY_CODEX":
            expected_ids = {801, 803, 5738, 5739}
            if code == "HDB":
                expected_ids.add(802)
            if {
                mapping.get("report_norm_id") for mapping in trial["verified_mappings"]
            } != expected_ids or any(
                mapping.get("status") != "VERIFIED_BY_CODEX"
                for mapping in trial["verified_mappings"]
            ):
                raise _error("verified purchased-debt mapping shape drifted")
        elif (
            trial["verified_mappings"]
            or trial["verified_accounting_equations"]
            or trial["optional_check_equations"]
            or trial["page_evidence"]
            or trial["family_boundary"] is not None
        ):
            raise _error("not-observed purchased-debt trial was promoted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0066:result:" + canonical_json_sha256_v1(material):
        raise _error("purchased-debt verified result identity drifted")
    return canonical_clone_v1(value)


def _stable_json(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    payload = support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _live_inputs() -> tuple[Any, Any, Any, Any, Any, Any, str, str]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, manifest_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_purchased_debt_full_document_scan_v1(semantic_index)
    if not REVIEW_SHA256:
        raise _error("fixed purchased-debt review SHA is not sealed")
    review, review_sha = _stable_json(REVIEW_PATH, REVIEW_SHA256)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        manifest_sha,
        review_sha,
    )


def build_live_purchased_debt_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay every fixed input and derive the bounded result."""

    (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        manifest_sha,
        review_sha,
    ) = _live_inputs()
    return build_purchased_debt_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=manifest_sha,
        review_sha256=review_sha,
    )


def validate_purchased_debt_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild one persisted result from all fixed live inputs."""

    persisted = _validate_result(value)
    rebuilt = build_live_purchased_debt_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("verified purchased-debt result does not replay exactly")
    return rebuilt


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        REVIEW_PATH.write_bytes(canonical_json_bytes_v1(_review_blueprint()))
        return
    result = build_live_purchased_debt_8bank_codex_verified_mapping_v1()
    if args.write_result:
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    _main()
