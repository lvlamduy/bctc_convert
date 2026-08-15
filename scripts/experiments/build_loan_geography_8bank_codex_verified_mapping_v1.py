"""Verify exact customer-loan geography rows and retain broader tables unresolved.

The complete-PDF matcher is bank blind.  This bounded post-scan step binds its
two exact customer-loan regions and five broader-loan near regions to visible
PDF pixels, the customer-loan owner totals already verified in E-0054, and the
live TM schema.  A geographic segment report is retained as a negative control.
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
    "LoanGeography8BankCodexVerifiedMappingV1Error",
    "build_live_loan_geography_8bank_codex_verified_mapping_v1",
    "build_loan_geography_8bank_codex_verified_mapping_v1",
    "validate_loan_geography_8bank_codex_verified_mapping_replay_v1",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


support = _load_module(
    "trading_securities_support_for_loan_geography_v1",
    "build_trading_securities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "loan_geography_scan_for_codex_verified_mapping_v1",
    "scan_loan_geography_full_document_vietocr_v1.py",
)
loan_type = _load_module(
    "loan_type_verified_mapping_for_geography_scope_v1",
    "build_loan_type_8bank_codex_verified_mapping_v1.py",
)

FORMAT_VERSION = "LOAN_GEOGRAPHY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "LOAN_GEOGRAPHY_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_SHARED_GEOGRAPHIC_CONCENTRATION_"
    "GRAPH_FIRST_LAST_NEXT_BOUNDARY_ROW_OR_COLUMN_LAYOUT_EXACT_CUSTOMER_LOAN_"
    "SCOPE_VISIBLE_PDF_PIXEL_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_"
    "CANONICALIZATION_OR_BROAD_LOAN_NARROWING_AUTHORITY"
)
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
REVIEW_PATH = Path("docs/experiments/E-0065-loan-geography-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0065-loan-geography-8bank-codex-verified-mapping-v1.json")
LOAN_TYPE_RESULT_PATH = Path(
    "docs/experiments/E-0054-loan-type-8bank-codex-verified-mapping-v2.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_LOAN_TYPE_RESULT_SHA256 = (
    "91af12c4b5f2da88fee4dd3d65805bc6e6751fb3d39fc86853c9cc995afd7d76"
)
EXPECTED_SCAN_ID = "lgfdsv1:scan:a70800f6323f46f5717dbc941b16f1db8ebd848ec05bb15f51b6373baa7f0b83"
REVIEW_SHA256 = "318f86c977c967564635dd43d39166d126be14517c88866196059e477bc906c7"

_CHECKS = [
    "COMPLETE_PDF_REGION_ENUMERATION",
    "FIRST_LAST_AND_NEXT_FAMILY_BOUNDARY",
    "HORIZONTAL_VERTICAL_OR_HYBRID_LAYOUT",
    "EXACT_CUSTOMER_LOAN_SCOPE",
    "PERIOD_UNIT_AND_REPORT_SCOPE",
    "VISIBLE_PIXEL_LABEL_DIGITS_DASH_AND_SIGN",
    "CUSTOMER_LOAN_OWNER_TOTAL_SCOPE_EQUATION",
    "LIVE_TM_SCHEMA_PARENT_CHILD_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_coerced_to_zero": False,
    "broad_total_loan_axis_narrowed_to_customer_loans": False,
    "dash_coerced_to_zero_only_when_visible_in_pdf": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "segment_report_promoted_to_loan_geography": False,
    "source_order_and_cluster_boundaries_required": True,
    "visible_pdf_pixels_used_for_numeric_truth": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_loan_population_mapping_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_preserved_as_verified_source_value": True,
    "customer_loan_scope_must_equal_verified_owner_total": True,
    "dash_zero_requires_visible_pixel": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_exact_mbb_and_vib_geography_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "segment_report_mapping_authority": False,
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
    759: ("Phân tích theo khu vực địa lý", 716, 212),
    5752: ("+ Trong nước", 759, 213),
    760: ("+ Thành phố Hồ Chí Minh", 5752, 214),
    761: ("+ Đồng bằng sông Cửu Long", 5752, 215),
    762: ("+ Miền Trung và Tây nguyên", 5752, 216),
    763: ("+ Miền Bắc", 5752, 217),
    764: ("+ Miền Đông nam bộ", 5752, 218),
    765: ("+ Nước ngoài", 759, 219),
    766: ("Phân tích theo loại hình doanh nghiệp", 716, 220),
}


class LoanGeography8BankCodexVerifiedMappingV1Error(ValueError):
    """The scan, pixel review, owner scope, accounting, or schema drifted."""


def _error(message: str) -> LoanGeography8BankCodexVerifiedMappingV1Error:
    return LoanGeography8BankCodexVerifiedMappingV1Error(message)


def _line(line_index: int, pixel_transcription: str) -> dict[str, Any]:
    return {"line_index": line_index, "pixel_transcription": pixel_transcription}


def _dash(pixel_region_bbox: Sequence[int]) -> dict[str, Any]:
    return {
        "line_index": None,
        "pixel_region_bbox": list(pixel_region_bbox),
        "pixel_transcription": "-",
    }


def _cell(
    role: str,
    label_line: int,
    label_pixel: str,
    value: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "label": _line(label_line, label_pixel),
        "role": role,
        "value": canonical_clone_v1(value),
    }


def _page_review(
    page_sequence: int,
    source_period: str,
    render_sha256: str,
    heading_lines: Sequence[tuple[int, str]],
    loan_axis_lines: Sequence[tuple[int, str]],
    domestic: Mapping[str, Any],
    foreign: Mapping[str, Any],
    *,
    total: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "cells": [canonical_clone_v1(domestic), canonical_clone_v1(foreign)],
        "heading": [_line(index, text) for index, text in heading_lines],
        "loan_axis": [_line(index, text) for index, text in loan_axis_lines],
        "page_sequence": page_sequence,
        "render_sha256": render_sha256,
        "source_period": source_period,
        "total": canonical_clone_v1(total),
    }


def _checks(exact: bool, *, segment: bool = False) -> dict[str, str]:
    result = {check: "PASS" for check in _CHECKS}
    if not exact:
        result["EXACT_CUSTOMER_LOAN_SCOPE"] = (
            "PASS_SEGMENT_REPORT_NEGATIVE_CONTROL"
            if segment
            else "FAIL_BROADER_THAN_CUSTOMER_LOANS"
        )
        result["LIVE_TM_SCHEMA_PARENT_CHILD_AND_DISPLAY_ORDER"] = "NOT_APPLICABLE"
    return result


def _boundary(
    first: tuple[int, int, str],
    last: tuple[int, int, str],
    next_family: tuple[int, int, str],
) -> dict[str, Any]:
    return {
        "first_item": {
            "line_index": first[1],
            "page_sequence": first[0],
            "pixel_transcription": first[2],
        },
        "last_item": {
            "line_index": last[1],
            "page_sequence": last[0],
            "pixel_transcription": last[2],
        },
        "next_family_boundary": {
            "line_index": next_family[1],
            "page_sequence": next_family[0],
            "pixel_transcription": next_family[2],
        },
    }


def _comparison(period: str, geography: str, customer: str, relation: str) -> dict[str, Any]:
    geography_value = support._money(geography)
    customer_value = support._money(customer)
    return {
        "customer_loan_owner_total": customer,
        "difference": geography_value - customer_value,
        "geography_loan_population_total": geography,
        "period": period,
        "relation": relation,
    }


def _review_documents() -> list[dict[str, Any]]:
    return [
        {
            "bank_code": "ACB",
            "checks": _checks(False),
            "disposition": "UNRESOLVED_BROAD_TOTAL_LOANS_SCOPE",
            "family_boundary": _boundary(
                (27, 28, "4. MỨC ĐỘ TẬP TRUNG CỦA TÀI SẢN, CÔNG NỢ VÀ CÁC KHOẢN MỤC NGOẠI BẢNG"),
                (27, 59, "dụng khác."),
                (28, 23, "1. Rủi ro thị trường:"),
            ),
            "layout": "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS",
            "pages": [
                _page_review(
                    27,
                    "2026-06-30",
                    "e29ea2d92f45acdaf25ee37e17908b7f1ba6bdddf8d0a986231e977f72dfd18a",
                    [
                        (
                            28,
                            "4. MỨC ĐỘ TẬP TRUNG CỦA TÀI SẢN, CÔNG NỢ VÀ CÁC KHOẢN MỤC NGOẠI BẢNG",
                        ),
                        (29, "THEO KHU VỰC ĐỊA LÝ:"),
                    ],
                    [(36, "Tổng dư nợ"), (42, "cho vay")],
                    _cell("DOMESTIC", 47, "Trong nước", _line(48, "752.152.143")),
                    _cell("FOREIGN", 53, "Nước ngoài", _dash([499, 1235, 682, 1275])),
                    total=None,
                )
            ],
            "scope_comparisons": [
                _comparison("2026-06-30", "752.152.143", "745.759.303", "BROADER")
            ],
        },
        {
            "bank_code": "MBB",
            "checks": _checks(True),
            "disposition": "VERIFIED_EXACT_CUSTOMER_LOAN_GEOGRAPHY",
            "family_boundary": _boundary(
                (
                    52,
                    39,
                    "Mức độ tập trung theo khu vực địa lý của các tài sản, công nợ và các khoản mục ngoại bảng",
                ),
                (52, 57, "9.295.704"),
                (53, 0, "4. Báo cáo bộ phận hợp nhất:"),
            ),
            "layout": "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS",
            "pages": [
                _page_review(
                    52,
                    "2026-06-30",
                    "b79de15809dbce28631aff2064f2107a4995e83e4fb17223afcff6b8aad99d39",
                    [
                        (
                            39,
                            "Mức độ tập trung theo khu vực địa lý của các tài sản, công nợ và các khoản mục ngoại",
                        ),
                        (40, "bảng"),
                    ],
                    [(43, "Tổng dư nợ cho"), (47, "vay khách hàng")],
                    _cell("DOMESTIC", 51, "Trong nước", _line(52, "1.218.258.773")),
                    _cell("FOREIGN", 56, "Nước ngoài", _line(57, "9.295.704")),
                    total=None,
                )
            ],
            "scope_comparisons": [
                _comparison("2026-06-30", "1.227.554.477", "1.227.554.477", "EXACT")
            ],
        },
        {
            "bank_code": "VPB",
            "checks": _checks(False),
            "disposition": "UNRESOLVED_BROAD_MIXED_LOAN_POPULATION_SCOPE",
            "family_boundary": _boundary(
                (73, 5, "MỨC ĐỘ TẬP TRUNG THEO KHU VỰC ĐỊA LÝ CỦA CÁC TÀI SẢN, CÔNG NỢ VÀ CÁC"),
                (73, 18, "1.047.765.320"),
                (73, 35, "44."),
            ),
            "layout": "GEOGRAPHY_COLUMNS_ACCOUNTING_FAMILY_ROWS",
            "pages": [
                _page_review(
                    73,
                    "2026-03-31",
                    "6bc1b48a317a42b5fd73a6f31a18e41e9d593b8bff9be24000addd12cbfa4ea1",
                    [
                        (5, "MỨC ĐỘ TẬP TRUNG THEO KHU VỰC ĐỊA LÝ CỦA CÁC TÀI SẢN, CÔNG NỢ VÀ CÁC"),
                        (6, "KHOẢN MỤC NGOẠI BẢNG"),
                    ],
                    [
                        (14, "Tổng dư nợ cho vay khách hàng, mua"),
                        (15, "nợ và cấp tín dụng cho các TCTD khác"),
                    ],
                    _cell("DOMESTIC", 8, "Trong nước", _line(16, "1.047.710.441")),
                    _cell("FOREIGN", 9, "Nước ngoài", _line(17, "54.879")),
                    total=_line(18, "1.047.765.320"),
                )
            ],
            "scope_comparisons": [
                _comparison("2026-03-31", "1.047.765.320", "1.040.917.216", "BROADER")
            ],
        },
        {
            "bank_code": "HDB",
            "checks": _checks(False),
            "disposition": "UNRESOLVED_BROAD_TOTAL_LOANS_SCOPE",
            "family_boundary": _boundary(
                (
                    37,
                    50,
                    "Mức độ tập trung của tài sản, nợ phải trả và các khoản mục ngoại bảng theo vùng",
                ),
                (37, 83, "Bao gồm cho vay TCTD khác và cho vay khách hàng."),
                (37, 86, "VIII. QUẢN LÝ RỦI RO TÀI CHÍNH"),
            ),
            "layout": "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS",
            "pages": [
                _page_review(
                    37,
                    "2026-06-30",
                    "5cdb727055421456b294b6b5743f54e678ec134b75cf12f87f6f2062d2e92f76",
                    [
                        (
                            50,
                            "Mức độ tập trung của tài sản, nợ phải trả và các khoản mục ngoại bảng theo vùng",
                        )
                    ],
                    [(54, "Tổng dư nợ"), (59, "cho vay")],
                    _cell("DOMESTIC", 69, "Trong nước", _line(70, "670.440.170")),
                    _cell("FOREIGN", 75, "Nước ngoài", _dash([558, 1468, 704, 1499])),
                    total=_line(77, "670.440.170"),
                )
            ],
            "scope_comparisons": [
                _comparison("2026-06-30", "670.440.170", "659.000.255", "BROADER")
            ],
        },
        {
            "bank_code": "VCB",
            "checks": _checks(False, segment=True),
            "disposition": "UNRESOLVED_SEGMENT_REPORT_NEGATIVE_CONTROL_NO_LOAN_GEOGRAPHY",
            "family_boundary": _boundary(
                (42, 7, "23. Báo cáo bộ phận"),
                (42, 169, "vị trong ngân hàng"),
                (43, 7, "(b) Báo cáo bộ phận theo lĩnh vực kinh doanh"),
            ),
            "layout": "GEOGRAPHIC_SEGMENT_REPORT_INCOME_EXPENSE_MATRIX",
            "pages": [],
            "scope_comparisons": [],
        },
        {
            "bank_code": "CTG",
            "checks": _checks(False),
            "disposition": "UNRESOLVED_BROAD_TOTAL_LOANS_SCOPE",
            "family_boundary": _boundary(
                (49, 4, "23. MỨC ĐỘ TẬP TRUNG THEO KHU VỰC ĐỊA LÝ CỦA CÁC TÀI SẢN, CÔNG"),
                (49, 34, "2.112.949.308"),
                (49, 39, "24. GIẢI TRÌNH BIẾN ĐỘNG LỢI NHUẬN"),
            ),
            "layout": "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS",
            "pages": [
                _page_review(
                    49,
                    "2026-06-30",
                    "701b49322ab93cc97bf23563e03d0a22f7adfcb7ce7c3d1f8159c8589bf572ce",
                    [
                        (4, "23. MỨC ĐỘ TẬP TRUNG THEO KHU VỰC ĐỊA LÝ CỦA CÁC TÀI SẢN, CÔNG"),
                        (5, "NỢ VÀ CÁC KHOẢN MỤC NGOẠI BẢNG"),
                    ],
                    [(10, "Tổng dư nợ"), (14, "cho vay")],
                    _cell("DOMESTIC", 23, "Trong nước", _line(24, "2.100.648.720")),
                    _cell("FOREIGN", 29, "Nước ngoài", _line(30, "12.300.588")),
                    total=_line(34, "2.112.949.308"),
                )
            ],
            "scope_comparisons": [
                _comparison("2026-06-30", "2.112.949.308", "2.092.707.758", "BROADER")
            ],
        },
        {
            "bank_code": "BID",
            "checks": _checks(False),
            "disposition": "UNRESOLVED_BROAD_TOTAL_LOANS_SCOPE",
            "family_boundary": _boundary(
                (31, 5, "21. MỨC ĐỘ TẬP TRUNG THEO KHU VỰC ĐỊA LÝ CỦA CÁC TÀI SẢN, CÔNG NỢ VÀ CÁC"),
                (31, 28, "2.514.484.193"),
                (31, 33, "22. CHÍNH SÁCH QUẢN LÝ RỦI RO LIÊN QUAN ĐẾN CÔNG CỤ TÀI CHÍNH"),
            ),
            "layout": "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS",
            "pages": [
                _page_review(
                    31,
                    "2026-06-30",
                    "737fdccaccaee88b575795df12c22c4b7609c0283c2e446352bfd2d28a2020e7",
                    [
                        (
                            5,
                            "21. MỨC ĐỘ TẬP TRUNG THEO KHU VỰC ĐỊA LÝ CỦA CÁC TÀI SẢN, CÔNG NỢ VÀ CÁC",
                        ),
                        (6, "KHOẢN MỤC NGOẠI BẢNG"),
                    ],
                    [(8, "Tổng dư nợ"), (13, "cho vay")],
                    _cell("DOMESTIC", 17, "Trong nước", _line(18, "2.483.971.187")),
                    _cell("FOREIGN", 23, "Nước ngoài", _line(24, "30.513.006")),
                    total=_line(28, "2.514.484.193"),
                )
            ],
            "scope_comparisons": [
                _comparison("2026-06-30", "2.514.484.193", "2.501.807.043", "BROADER")
            ],
        },
        {
            "bank_code": "VIB",
            "checks": _checks(True),
            "disposition": "VERIFIED_EXACT_CUSTOMER_LOAN_GEOGRAPHY",
            "family_boundary": _boundary(
                (
                    53,
                    5,
                    "MỨC ĐỘ TẬP TRUNG CỦA TÀI SẢN, NỢ PHẢI TRẢ VÀ CÁC CAM KẾT NGOẠI BẢNG THEO KHU",
                ),
                (54, 27, "381.972.016"),
                (55, 4, "43."),
            ),
            "layout": "GEOGRAPHY_COLUMNS_ACCOUNTING_FAMILY_ROWS_TWO_PAGE_PERIOD_CONTINUATION",
            "pages": [
                _page_review(
                    53,
                    "2026-06-30",
                    "17877bd8503d4cd0607288d9e37e38925bef869530067f3da2e8add10ca5ca2d",
                    [
                        (
                            5,
                            "MỨC ĐỘ TẬP TRUNG CỦA TÀI SẢN, NỢ PHẢI TRẢ VÀ CÁC CAM KẾT NGOẠI BẢNG THEO KHU",
                        ),
                        (6, "VỰC ĐỊA LÝ"),
                    ],
                    [(25, "Cho vay khách hàng")],
                    _cell("DOMESTIC", 7, "Trong nước", _line(26, "397.083.447")),
                    _cell("FOREIGN", 8, "Nước ngoài", _dash([1102, 655, 1237, 684])),
                    total=_line(27, "397.083.447"),
                ),
                _page_review(
                    54,
                    "2025-12-31",
                    "9b762f4ab5bb30f4e7f912201b3bc05bcf3b0f1fd40f088eb082680fae963064",
                    [
                        (
                            5,
                            "MỨC ĐỘ TẬP TRUNG CỦA TÀI SẢN, NỢ PHẢI TRẢ VÀ CÁC CAM KẾT NGOẠI BẢNG THEO KHU",
                        ),
                        (6, "VỰC ĐỊA LÝ (tiếp theo)"),
                    ],
                    [(25, "Cho vay khách hàng")],
                    _cell("DOMESTIC", 7, "Trong nước", _line(26, "381.972.016")),
                    _cell("FOREIGN", 8, "Nước ngoài", _dash([1101, 655, 1236, 684])),
                    total=_line(27, "381.972.016"),
                ),
            ],
            "scope_comparisons": [
                _comparison("2026-06-30", "397.083.447", "397.083.447", "EXACT"),
                _comparison("2025-12-31", "381.972.016", "381.972.016", "EXACT"),
            ],
        },
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0065:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex loan-geography pixel review differs from the fixed ledger")
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


def _boundary_evidence(
    semantic_document: Mapping[str, Any],
    manifest_document: Mapping[str, Any],
    boundary: Mapping[str, Any],
) -> dict[str, Any]:
    result = {}
    for key in ("first_item", "last_item", "next_family_boundary"):
        spec = boundary[key]
        page_number = spec["page_sequence"]
        manifest_page = _page(manifest_document, page_number, "crop manifest")
        render = manifest_page.get("render_binding")
        if type(render) is not dict or type(render.get("sha256")) is not str:
            raise _error("boundary render binding drifted")
        result[key] = _event(
            semantic_document,
            manifest_document,
            page_number,
            spec,
            render["sha256"],
        )
    return result


def _money_evidence(
    semantic_document: Mapping[str, Any],
    manifest_document: Mapping[str, Any],
    page_review: Mapping[str, Any],
    cell: Mapping[str, Any],
) -> dict[str, Any]:
    value = _event(
        semantic_document,
        manifest_document,
        page_review["page_sequence"],
        cell["value"],
        page_review["render_sha256"],
    )
    normalized = support._money(value["independent_pixel_transcription"])
    semantic = value["semantic_proposal"]
    if semantic is not None and support._money(semantic) != normalized:
        raise _error("fresh VietOCR numeric proposal and visible pixel transcription disagree")
    return {
        **value,
        "normalized_value": normalized,
        "source_cell_status": "DASH"
        if normalized == 0 and value["independent_pixel_transcription"] == "-"
        else "VALUE",
    }


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


def _loan_totals(value: Mapping[str, Any]) -> dict[tuple[str, str], int]:
    totals: dict[tuple[str, str], int] = {}
    for trial in value.get("trials", []):
        code = trial.get("bank_provenance")
        source_total = trial.get("source_only_total")
        values = source_total.get("values") if type(source_total) is dict else None
        if type(code) is not str or type(values) is not list:
            raise _error("verified loan-type owner total axis drifted")
        money_values = [
            item for item in values if type(item) is dict and item.get("lane_type") == "MONEY"
        ]
        if not money_values:
            raise _error("verified loan-type owner has no money value")
        totals[(code, "CURRENT")] = support._money(
            money_values[0]["independent_pixel_transcription"]
        )
        if len(money_values) > 1:
            totals[(code, "COMPARATIVE")] = support._money(
                money_values[1]["independent_pixel_transcription"]
            )
    return totals


def _trial(
    code: str,
    ordinal: int,
    review_document: Mapping[str, Any],
    scan_trial: Mapping[str, Any],
    semantic_index: Mapping[str, Any],
    crop_manifest: Mapping[str, Any],
    owner_totals: Mapping[tuple[str, str], int],
    schema_bindings: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    semantic_document = _document(semantic_index["documents"], code, "semantic index")
    manifest_document = _document(crop_manifest["documents"], code, "crop manifest")
    boundary = _boundary_evidence(
        semantic_document, manifest_document, review_document["family_boundary"]
    )
    exact = review_document["disposition"] == "VERIFIED_EXACT_CUSTOMER_LOAN_GEOGRAPHY"
    page_evidence = []
    values_by_role: dict[str, list[dict[str, Any]]] = {"DOMESTIC": [], "FOREIGN": []}
    equations = []
    for page_review in review_document["pages"]:
        heading = [
            _event(
                semantic_document,
                manifest_document,
                page_review["page_sequence"],
                item,
                page_review["render_sha256"],
            )
            for item in page_review["heading"]
        ]
        loan_axis = [
            _event(
                semantic_document,
                manifest_document,
                page_review["page_sequence"],
                item,
                page_review["render_sha256"],
            )
            for item in page_review["loan_axis"]
        ]
        cells = []
        for cell in page_review["cells"]:
            label = _event(
                semantic_document,
                manifest_document,
                page_review["page_sequence"],
                cell["label"],
                page_review["render_sha256"],
            )
            value = _money_evidence(semantic_document, manifest_document, page_review, cell)
            values_by_role[cell["role"]].append(
                {"period": page_review["source_period"], **canonical_clone_v1(value)}
            )
            cells.append({"label": label, "role": cell["role"], "value": value})
        total = None
        if page_review["total"] is not None:
            total_event = _event(
                semantic_document,
                manifest_document,
                page_review["page_sequence"],
                page_review["total"],
                page_review["render_sha256"],
            )
            total = {
                **total_event,
                "normalized_value": support._money(total_event["independent_pixel_transcription"]),
            }
        domestic = next(
            item["value"]["normalized_value"] for item in cells if item["role"] == "DOMESTIC"
        )
        foreign = next(
            item["value"]["normalized_value"] for item in cells if item["role"] == "FOREIGN"
        )
        visible_total = total["normalized_value"] if total is not None else domestic + foreign
        if domestic + foreign != visible_total:
            raise _error("domestic plus foreign does not close to visible geography total")
        equations.append(
            {
                "computed_total": domestic + foreign,
                "domestic": domestic,
                "foreign": foreign,
                "period": page_review["source_period"],
                "visible_or_derived_total": visible_total,
            }
        )
        page_evidence.append(
            {
                "cells": cells,
                "geometry_mode": _page(
                    semantic_document, page_review["page_sequence"], "semantic index"
                )["geometry_mode"],
                "heading": heading,
                "loan_axis": loan_axis,
                "page_sequence": page_review["page_sequence"],
                "render_ref": _render(
                    manifest_document,
                    page_review["page_sequence"],
                    page_review["render_sha256"],
                ),
                "source_projection": canonical_clone_v1(
                    _page(
                        semantic_document,
                        page_review["page_sequence"],
                        "semantic index",
                    )["source_projection"]
                ),
                "source_period": page_review["source_period"],
                "total": total,
            }
        )
    scope_equations = []
    for index, comparison in enumerate(review_document["scope_comparisons"]):
        period_key = "CURRENT" if index == 0 else "COMPARATIVE"
        owner = owner_totals[(code, period_key)]
        geography = support._money(comparison["geography_loan_population_total"])
        customer = support._money(comparison["customer_loan_owner_total"])
        if owner != customer or geography - customer != comparison["difference"]:
            raise _error("geography/customer-loan scope comparison drifted")
        if comparison["relation"] == "EXACT" and geography != customer:
            raise _error("exact customer-loan geography scope does not equal owner total")
        if comparison["relation"] == "BROADER" and geography <= customer:
            raise _error("broad geography population is not broader than customer loans")
        scope_equations.append(canonical_clone_v1(comparison))
    matcher_result = scan_trial["matcher_result"]
    if exact:
        if matcher_result["status"] != "ACCEPTED_UNIQUE_VARIANT_GRAPH":
            raise _error("pixel-verified exact geography region is not unique in the complete PDF")
    elif matcher_result["status"] != "UNRESOLVED_NO_COMPLETE_REGION":
        raise _error("unresolved geography review unexpectedly has one exact graph")
    mappings = []
    if exact:
        for role, report_norm_id in (("DOMESTIC", 5752), ("FOREIGN", 765)):
            mappings.append(
                {
                    **canonical_clone_v1(schema_bindings[report_norm_id]),
                    "role": role,
                    "source_values": canonical_clone_v1(values_by_role[role]),
                    "status": "VERIFIED_BY_CODEX",
                }
            )
    return {
        "bank_provenance": code,
        "document_ordinal": ordinal,
        "family_boundary": boundary,
        "layout": review_document["layout"],
        "page_evidence": page_evidence,
        "scope_equations": scope_equations,
        "source_pdf": canonical_clone_v1(semantic_document["source_pdf"]),
        "status": "VERIFIED_BY_CODEX" if exact else "UNRESOLVED",
        "structural_scan_result_id": matcher_result["result_id"],
        "unresolved_reason": None if exact else review_document["disposition"],
        "verified_accounting_equations": equations,
        "verified_mappings": mappings,
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"])
            for trial in trials
            if trial["status"] == "VERIFIED_BY_CODEX"
        ),
        "broad_scope_unresolved_document_count": sum(
            trial["unresolved_reason"]
            in {
                "UNRESOLVED_BROAD_TOTAL_LOANS_SCOPE",
                "UNRESOLVED_BROAD_MIXED_LOAN_POPULATION_SCOPE",
            }
            for trial in trials
        ),
        "document_count": len(trials),
        "document_verified_count": sum(trial["status"] == "VERIFIED_BY_CODEX" for trial in trials),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "mapped_value_cell_count": sum(
            len(mapping["source_values"])
            for trial in trials
            for mapping in trial["verified_mappings"]
        ),
        "segment_report_negative_control_count": sum(
            trial["unresolved_reason"]
            == "UNRESOLVED_SEGMENT_REPORT_NEGATIVE_CONTROL_NO_LOAN_GEOGRAPHY"
            for trial in trials
        ),
        "unresolved_document_count": sum(trial["status"] == "UNRESOLVED" for trial in trials),
    }


def build_loan_geography_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    loan_type_result: Any,
    schema_authority: Any,
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    loan_type_result_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    """Build the bounded exact mappings from independently replayed inputs."""

    checked_review = _review(review)
    if structure_scan.get("scan_id") != EXPECTED_SCAN_ID:
        raise _error("fixed complete-PDF loan-geography scan identity drifted")
    if type(semantic_index) is not dict or type(crop_manifest) is not dict:
        raise _error("semantic index and crop manifest must be exact objects")
    if type(schema_authority) is not dict or type(schema_by_id) is not dict:
        raise _error("live TM schema authority drifted")
    schema_bindings = {
        report_norm_id: _schema_binding(schema_by_id[report_norm_id], report_norm_id)
        for report_norm_id in _SCHEMA_EXPECTED
    }
    if schema_by_id[759].children != [5752, 765] or schema_by_id[765].next_id != 766:
        raise _error("loan-geography first/last/next schema boundary drifted")
    owner_totals = _loan_totals(loan_type_result)
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
                owner_totals,
                schema_bindings,
            )
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest_sha256": crop_manifest_sha256,
            "loan_geography_scan_id": structure_scan["scan_id"],
            "loan_type_verified_result_sha256": loan_type_result_sha256,
            "pixel_review_id": checked_review["review_id"],
            "pixel_review_sha256": review_sha256,
            "semantic_axis_sha256": structure_scan["input_semantic_axis_sha256"],
            "tm_schema_projection_sha256": schema_authority["tm_schema_projection_sha256"],
        },
        "metrics": _metrics(trials),
        "state": "CODEX_VERIFIED_LOAN_GEOGRAPHY_MAPPING_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0065:result:" + canonical_json_sha256_v1(material)}
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("loan-geography verified result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "CODEX_VERIFIED_LOAN_GEOGRAPHY_MAPPING_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("loan-geography verified identity, authority or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("bank_provenance") != code
            or trial.get("status") not in {"VERIFIED_BY_CODEX", "UNRESOLVED"}
        ):
            raise _error("loan-geography verified trial identity drifted")
        if trial["status"] == "VERIFIED_BY_CODEX":
            if (
                trial["unresolved_reason"] is not None
                or len(trial["verified_mappings"]) != 2
                or any(
                    mapping.get("status") != "VERIFIED_BY_CODEX"
                    or mapping.get("report_norm_id") not in {5752, 765}
                    for mapping in trial["verified_mappings"]
                )
            ):
                raise _error("verified geography mapping shape drifted")
        elif trial["verified_mappings"] or type(trial["unresolved_reason"]) is not str:
            raise _error("unresolved geography trial was promoted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0065:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-geography verified result identity drifted")
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


def _live_inputs() -> tuple[Any, Any, Any, Any, Any, Any, Any, str, str, str]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, manifest_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_loan_geography_full_document_scan_v1(semantic_index)
    review, review_sha = _stable_json(REVIEW_PATH, REVIEW_SHA256)
    loan_type_result, loan_type_sha = _stable_json(
        LOAN_TYPE_RESULT_PATH, EXPECTED_LOAN_TYPE_RESULT_SHA256
    )
    loan_type._validate_result(loan_type_result)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        loan_type_result,
        schema_authority,
        schema_by_id,
        manifest_sha,
        review_sha,
        loan_type_sha,
    )


def build_live_loan_geography_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay every fixed input and derive the bounded result."""

    (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        loan_type_result,
        schema_authority,
        schema_by_id,
        manifest_sha,
        review_sha,
        loan_type_sha,
    ) = _live_inputs()
    return build_loan_geography_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        loan_type_result,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=manifest_sha,
        loan_type_result_sha256=loan_type_sha,
        review_sha256=review_sha,
    )


def validate_loan_geography_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild a persisted result from all fixed live inputs."""

    persisted = _validate_result(value)
    rebuilt = build_live_loan_geography_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("verified loan-geography result does not replay exactly")
    return rebuilt


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        REVIEW_PATH.write_bytes(canonical_json_bytes_v1(_review_blueprint()))
        return
    result = build_live_loan_geography_8bank_codex_verified_mapping_v1()
    if args.write_result:
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    _main()
