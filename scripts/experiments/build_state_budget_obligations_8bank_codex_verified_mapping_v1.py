"""Verify State-budget-obligation disclosures across eight reports."""

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
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load State-budget support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


other = _load(
    "other_activity_support_for_state_budget_obligations",
    "build_other_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load(
    "state_budget_obligations_scan_for_verified_mapping",
    "scan_state_budget_obligations_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "STATE_BUDGET_OBLIGATIONS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "STATE_BUDGET_OBLIGATIONS_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_STATE_"
    "BUDGET_GRAPH_VISIBLE_PDF_SOURCE_NUMERIC_CHALLENGER_MOVEMENT_AXES_"
    "DASH_ZERO_ACCOUNTING_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0095-state-budget-obligations-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0095-state-budget-obligations-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = other.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = other.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = other.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = other.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "sbofdsv1:scan:24437138e965905684d03a2bf32c90bc12c50c6c62ed0a66389a8c5a5ac44d30"

_SCHEMA_EXPECTED = {
    1259: ("IV. MỘT SỐ THÔNG TIN KHÁC", None, 835),
    1269: ("Tình hình thực hiện nghĩa vụ với ngân sách nhà nước", 1259, 845),
    1270: ("Thuế giá trị gia tăng", 1269, 846),
    1271: ("Thuế TNDN", 1269, 847),
    1272: ("Thuế Thu nhập Cá nhân", 1269, 848),
    1273: ("Thuế xuất nhập khẩu", 1269, 849),
    1274: ("Thuế tài nguyên", 1269, 850),
    1275: ("Thuế sử dụng vốn NSNN", 1269, 851),
    1276: ("Thuế tiêu thụ đặc biệt", 1269, 852),
    1277: ("Thuế nhà - đất", 1269, 853),
    1278: ("Các loại thuế khác", 1269, 854),
    1279: ("Các khoản phải nộp khác", 1269, 855),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "dash_normalized_to_zero_only_after_visible_pixel_review": True,
    "document_unit_inheritance_requires_explicit_same_pdf_declaration": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_state_budget_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
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


class StateBudgetObligations8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, values, axes, schema or result drifted."""


def _error(message: str) -> StateBudgetObligations8BankCodexVerifiedMappingV1Error:
    return StateBudgetObligations8BankCodexVerifiedMappingV1Error(message)


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    if (
        expected is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
        or item.display_order != expected[2]
    ):
        raise _error(f"mapping does not bind exact live TM schema row {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _ref(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str) -> dict[str, Any]:
    return {"kind": "AUTHENTICATED_LINE", **_ref(page, line, text)}


def _dash(page: int, label_line: int, axis_role: str) -> dict[str, Any]:
    return {
        "axis_role": axis_role,
        "kind": "AUTHENTICATED_VISIBLE_RENDER_DASH",
        "page_sequence": page,
        "pixel_transcription": "-",
        "row_label_line_index": label_line,
    }


def _mapping(
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    values: Sequence[tuple[str, Mapping[str, Any]] | Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_values = []
    for value in values:
        if type(value) is tuple:
            axis_role, ref = value
            normalized_values.append({"axis_role": axis_role, **canonical_clone_v1(ref)})
        else:
            normalized_values.append(canonical_clone_v1(value))
    return {
        "labels": [_ref(page, line, text) for line, text in labels],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": "ROW_WITH_VISIBLE_MOVEMENT_AXES",
        "values": normalized_values,
    }


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_note_complete_region_count": 0,
            "reason": (
                "No State-budget-obligation movement table with VAT, corporate-income tax, "
                "other-tax rows and opening/payable/paid/closing axes was found; income-tax "
                "expense, deferred-tax and policy disclosures do not qualify."
            ),
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "mappings": [],
        "owner": [],
        "page_span": None,
        "source_only_rows": [],
        "source_period": None,
        "unit_evidence": [],
    }


def _standard_values(page: int, lines: Sequence[tuple[int, str]]) -> list[Any]:
    roles = ("OPENING", "PAYABLE_INCREASE", "PAID_DECREASE", "CLOSING")
    return [
        (role, _line(page, line, text)) for role, (line, text) in zip(roles, lines, strict=True)
    ]


def _review_documents() -> list[dict[str, Any]]:
    return [
        {
            "absence_evidence": None,
            "bank_code": "ACB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1269,
                    22,
                    [(93, "Tổng cộng")],
                    _standard_values(
                        22,
                        [
                            (94, "2.174.750"),
                            (95, "2.834.158"),
                            (96, "3.821.260"),
                            (97, "1.187.648"),
                        ],
                    ),
                ),
                _mapping(
                    "VAT",
                    1270,
                    22,
                    [(77, "Thuế giá trị gia tăng")],
                    _standard_values(
                        22, [(78, "51.087"), (79, "214.416"), (80, "204.129"), (81, "61.374")]
                    ),
                ),
                _mapping(
                    "CORPORATE_INCOME_TAX",
                    1271,
                    22,
                    [(82, "Thuế thu nhập doanh nghiệp")],
                    _standard_values(
                        22,
                        [
                            (83, "1.963.800"),
                            (84, "2.150.571"),
                            (85, "3.102.702"),
                            (86, "1.011.669"),
                        ],
                    ),
                ),
                _mapping(
                    "HOUSE_LAND_TAX",
                    1277,
                    22,
                    [(87, "Thuế nhà - đất")],
                    [
                        _dash(22, 87, role)
                        for role in ("OPENING", "PAYABLE_INCREASE", "PAID_DECREASE", "CLOSING")
                    ],
                ),
                _mapping(
                    "OTHER_TAX",
                    1278,
                    22,
                    [(88, "Các loại thuế khác")],
                    _standard_values(
                        22, [(89, "159.863"), (90, "469.171"), (91, "514.429"), (92, "114.605")]
                    ),
                ),
            ],
            "owner": [_ref(22, 67, "Tình hình thực hiện nghĩa vụ với Ngân sách Nhà nước")],
            "page_span": [22, 22],
            "source_only_rows": [],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(22, 73, "Triệu đồng")],
        },
        {
            "absence_evidence": None,
            "bank_code": "MBB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1269,
                    49,
                    [],
                    _standard_values(
                        49,
                        [
                            (51, "4.218.259"),
                            (52, "5.911.348"),
                            (53, "(7.701.475)"),
                            (54, "2.428.132"),
                        ],
                    ),
                ),
                _mapping(
                    "VAT",
                    1270,
                    49,
                    [(36, "Thuế GTGT")],
                    _standard_values(
                        49, [(37, "175.047"), (38, "653.515"), (39, "(672.890)"), (40, "155.672")]
                    ),
                ),
                _mapping(
                    "CORPORATE_INCOME_TAX",
                    1271,
                    49,
                    [(41, "Thuế TNDN")],
                    _standard_values(
                        49,
                        [
                            (42, "3.897.818"),
                            (43, "4.033.374"),
                            (44, "(5.805.604)"),
                            (45, "2.125.588"),
                        ],
                    ),
                ),
                _mapping(
                    "OTHER_TAX",
                    1278,
                    49,
                    [(46, "Các loại thuế khác")],
                    _standard_values(
                        49,
                        [(47, "145.394"), (48, "1.224.459"), (49, "(1.222.981)"), (50, "146.872")],
                    ),
                ),
            ],
            "owner": [_ref(49, 28, "Tình hình thực hiện nghĩa vụ với NSNN")],
            "page_span": [49, 49],
            "source_only_rows": [],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(49, 29, "Đơn vị: triệu đồng")],
        },
        {
            "absence_evidence": None,
            "bank_code": "VPB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1269,
                    58,
                    [],
                    _standard_values(
                        58,
                        [
                            (32, "4.712.152"),
                            (33, "2.327.996"),
                            (34, "(5.394.678)"),
                            (35, "1.645.470"),
                        ],
                    ),
                ),
                _mapping(
                    "VAT",
                    1270,
                    58,
                    [(16, "Thuế giá trị gia tăng")],
                    _standard_values(
                        58, [(17, "172.238"), (18, "233.157"), (19, "(318.279)"), (20, "87.116")]
                    ),
                ),
                _mapping(
                    "CORPORATE_INCOME_TAX",
                    1271,
                    58,
                    [(21, "Thuế thu nhập"), (22, "doanh nghiệp")],
                    _standard_values(
                        58,
                        [
                            (23, "4.408.862"),
                            (24, "1.621.256"),
                            (25, "(4.560.337)"),
                            (26, "1.469.781"),
                        ],
                    ),
                ),
                _mapping(
                    "OTHER_TAX",
                    1278,
                    58,
                    [(27, "Thuế khác")],
                    _standard_values(
                        58, [(28, "131.052"), (29, "473.583"), (30, "(516.062)"), (31, "88.573")]
                    ),
                ),
            ],
            "owner": [_ref(58, 5, "TÌNH HÌNH THỰC HIỆN NGHĨA VỤ VỚI NGÂN SÁCH NHÀ NƯỚC")],
            "page_span": [58, 58],
            "source_only_rows": [],
            "source_period": "2026-03-31",
            "unit_evidence": [_ref(58, 12, "Triệu đồng")],
        },
        {
            "absence_evidence": None,
            "bank_code": "HDB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1269,
                    32,
                    [],
                    [
                        ("OPENING", _line(32, 60, "2.634.433")),
                        ("BUSINESS_COMBINATION_INCREASE", _line(32, 61, "146.563")),
                        ("PAYABLE_INCREASE", _line(32, 62, "3.019.014")),
                        ("PAID_DECREASE", _line(32, 63, "(4.232.592)")),
                        ("CLOSING", _line(32, 64, "1.567.418")),
                    ],
                ),
                _mapping(
                    "VAT",
                    1270,
                    32,
                    [(27, "Thuế giá trị gia tăng")],
                    [
                        ("OPENING", _line(32, 23, "57.563")),
                        ("BUSINESS_COMBINATION_INCREASE", _line(32, 28, "26.503")),
                        ("PAYABLE_INCREASE", _line(32, 24, "173.335")),
                        ("PAID_DECREASE", _line(32, 25, "(184.634)")),
                        ("CLOSING", _line(32, 26, "72.767")),
                    ],
                ),
                _mapping(
                    "CORPORATE_INCOME_TAX",
                    1271,
                    32,
                    [(32, "Thuế thu nhập doanh nghiệp")],
                    [
                        ("OPENING", _line(32, 33, "2.513.751")),
                        ("BUSINESS_COMBINATION_INCREASE", _line(32, 34, "102.063")),
                        ("PAYABLE_INCREASE", _line(32, 29, "2.520.650")),
                        ("PAID_DECREASE", _line(32, 30, "(3.751.715)")),
                        ("CLOSING", _line(32, 31, "1.384.749")),
                    ],
                ),
                _mapping(
                    "HOUSE_LAND_TAX",
                    1277,
                    32,
                    [(35, "Thuế nhà đất")],
                    [
                        _dash(32, 35, "OPENING"),
                        _dash(32, 35, "BUSINESS_COMBINATION_INCREASE"),
                        ("PAYABLE_INCREASE", _line(32, 36, "27")),
                        ("PAID_DECREASE", _line(32, 37, "(27)")),
                        _dash(32, 35, "CLOSING"),
                    ],
                ),
                _mapping(
                    "PERSONAL_INCOME_TAX",
                    1272,
                    32,
                    [(45, "Thuế thu nhập cá nhân")],
                    [
                        ("OPENING", _line(32, 46, "33.503")),
                        ("BUSINESS_COMBINATION_INCREASE", _line(32, 47, "17.997")),
                        ("PAYABLE_INCREASE", _line(32, 48, "264.228")),
                        ("PAID_DECREASE", _line(32, 49, "(235.063)")),
                        ("CLOSING", _line(32, 50, "80.665")),
                    ],
                ),
                _mapping(
                    "OTHER_TAX",
                    1278,
                    32,
                    [(51, "Thuế nhà thầu")],
                    [
                        ("OPENING", _line(32, 52, "29.616")),
                        _dash(32, 51, "BUSINESS_COMBINATION_INCREASE"),
                        ("PAYABLE_INCREASE", _line(32, 53, "58.274")),
                        ("PAID_DECREASE", _line(32, 54, "(58.653)")),
                        ("CLOSING", _line(32, 55, "29.237")),
                    ],
                ),
                _mapping(
                    "OTHER_PAYABLE",
                    1279,
                    32,
                    [(56, "Các khoản phí, lệ phí và"), (59, "phải nộp khác")],
                    [
                        _dash(32, 56, "OPENING"),
                        _dash(32, 56, "BUSINESS_COMBINATION_INCREASE"),
                        ("PAYABLE_INCREASE", _line(32, 57, "2.500")),
                        ("PAID_DECREASE", _line(32, 58, "(2.500)")),
                        _dash(32, 56, "CLOSING"),
                    ],
                ),
            ],
            "owner": [_ref(32, 9, "Thuế và các khoản phải nộp nhà nước")],
            "page_span": [32, 32],
            "source_only_rows": [
                {
                    "labels": [_ref(32, 38, "Tiền thuê đất")],
                    "reason": "LAND_RENT_IS_NOT_IDENTICAL_TO_HOUSE_LAND_TAX_AND_HAS_NO_EXACT_SCHEMA_LEAF",
                    "row_id": "SBO-001",
                }
            ],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(32, 18, "Triệu VND")],
        },
        _absence("VCB"),
        {
            "absence_evidence": None,
            "bank_code": "CTG",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1269,
                    43,
                    [],
                    [
                        ("OPENING", _line(43, 69, "4.637.925")),
                        ("PAYABLE_INCREASE", _line(43, 70, "7.098.769")),
                        ("PAID_DECREASE", _line(43, 71, "8.552.382")),
                        ("CLOSING_PAYABLE", _line(43, 72, "3.190.608")),
                        ("CLOSING_RECEIVABLE", _line(43, 73, "(6.296)")),
                        ("CLOSING", _line(43, 74, "3.184.312")),
                    ],
                ),
                _mapping(
                    "VAT",
                    1270,
                    43,
                    [(50, "Thuế GTGT")],
                    [
                        ("OPENING", _line(43, 51, "104.650")),
                        ("PAYABLE_INCREASE", _line(43, 52, "615.359")),
                        ("PAID_DECREASE", _line(43, 53, "623.986")),
                        ("CLOSING_PAYABLE", _line(43, 54, "102.319")),
                        ("CLOSING_RECEIVABLE", _line(43, 55, "(6.296)")),
                        ("CLOSING", _line(43, 56, "96.023")),
                    ],
                ),
                _mapping(
                    "CORPORATE_INCOME_TAX",
                    1271,
                    43,
                    [(57, "Thuế TNDN hiện hành")],
                    [
                        ("OPENING", _line(43, 58, "4.359.447")),
                        ("PAYABLE_INCREASE", _line(43, 59, "5.125.192")),
                        ("PAID_DECREASE", _line(43, 60, "6.525.295")),
                        ("CLOSING_PAYABLE", _line(43, 61, "2.959.344")),
                        _dash(43, 57, "CLOSING_RECEIVABLE"),
                        ("CLOSING", _line(43, 62, "2.959.344")),
                    ],
                ),
                _mapping(
                    "OTHER_TAX",
                    1278,
                    43,
                    [(63, "Các loại thuế khác")],
                    [
                        ("OPENING", _line(43, 64, "173.828")),
                        ("PAYABLE_INCREASE", _line(43, 65, "1.358.218")),
                        ("PAID_DECREASE", _line(43, 66, "1.403.101")),
                        ("CLOSING_PAYABLE", _line(43, 67, "128.945")),
                        _dash(43, 63, "CLOSING_RECEIVABLE"),
                        ("CLOSING", _line(43, 68, "128.945")),
                    ],
                ),
            ],
            "owner": [_ref(43, 34, "TÌNH HÌNH THỰC HIỆN NGHĨA VỤ VỚI NGÂN SÁCH NHÀ NƯỚC")],
            "page_span": [43, 43],
            "source_only_rows": [],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(43, 44, "triệu đồng")],
        },
        {
            "absence_evidence": None,
            "bank_code": "BID",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1269,
                    26,
                    [],
                    _standard_values(
                        26,
                        [
                            (48, "4,081,353"),
                            (49, "7,104,008"),
                            (50, "(8,514,771)"),
                            (51, "2,670,590"),
                        ],
                    ),
                ),
                _mapping(
                    "VAT",
                    1270,
                    26,
                    [(27, "Thuế GTGT")],
                    _standard_values(
                        26, [(28, "128,615"), (29, "932,799"), (30, "(971,708)"), (31, "89,706")]
                    ),
                ),
                _mapping(
                    "CORPORATE_INCOME_TAX",
                    1271,
                    26,
                    [(32, "Thuế TNDN")],
                    _standard_values(
                        26,
                        [
                            (33, "3,591,694"),
                            (34, "3,729,586"),
                            (35, "(5,272,691)"),
                            (36, "2,048,589"),
                        ],
                    ),
                ),
                _mapping(
                    "OTHER_TAX",
                    1278,
                    26,
                    [(37, "Các loại thuế khác")],
                    _standard_values(
                        26,
                        [(38, "184,139"), (39, "2,399,732"), (40, "(2,229,339)"), (41, "354,532")],
                    ),
                ),
                _mapping(
                    "OTHER_PAYABLE",
                    1279,
                    26,
                    [(42, "Các khoản phí, lệ phí và các"), (47, "khoản phải nộp khác")],
                    _standard_values(
                        26, [(43, "176,905"), (44, "41,891"), (45, "(41,033)"), (46, "177,763")]
                    ),
                ),
            ],
            "owner": [_ref(26, 21, "Nghĩa vụ với ngân sách nhà nước")],
            "page_span": [26, 26],
            "source_only_rows": [],
            "source_period": "2026-06-30",
            "unit_evidence": [
                _ref(
                    13,
                    49,
                    "các số liệu được làm tròn đến hàng triệu và trình bày theo đơn vị triệu VND",
                )
            ],
        },
        {
            "absence_evidence": None,
            "bank_code": "VIB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1269,
                    47,
                    [],
                    _standard_values(
                        47,
                        [
                            (57, "1.289.606"),
                            (58, "1.354.559"),
                            (59, "(1.648.103)"),
                            (60, "996.062"),
                        ],
                    ),
                ),
                _mapping(
                    "CORPORATE_INCOME_TAX",
                    1271,
                    47,
                    [(42, "Thuế thu nhập doanh nghiệp")],
                    _standard_values(
                        47,
                        [
                            (43, "1.185.100"),
                            (44, "1.039.093"),
                            (45, "(1.292.751)"),
                            (46, "931.442"),
                        ],
                    ),
                ),
                _mapping(
                    "VAT",
                    1270,
                    47,
                    [(47, "Thuế giá trị gia tăng")],
                    _standard_values(
                        47, [(48, "60.574"), (49, "129.369"), (50, "(165.267)"), (51, "24.676")]
                    ),
                ),
                _mapping(
                    "OTHER_TAX",
                    1278,
                    47,
                    [(52, "Các loại thuế khác")],
                    _standard_values(
                        47, [(53, "43.932"), (54, "186.097"), (55, "(190.085)"), (56, "39.944")]
                    ),
                ),
            ],
            "owner": [_ref(47, 35, "TÌNH HÌNH THỰC HIỆN NGHĨA VỤ VỚI NGÂN SÁCH NHÀ NƯỚC")],
            "page_span": [47, 47],
            "source_only_rows": [],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(47, 36, "Đơn vị: triệu đồng")],
        },
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "state": "STATE_BUDGET_OBLIGATIONS_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0095:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("State-budget pixel review drifted")
    return canonical_clone_v1(value)


def _dash_value(crop_document: Mapping[str, Any], ref: Mapping[str, Any]) -> dict[str, Any]:
    page = other._page(crop_document, ref["page_sequence"], "crop manifest")
    return {
        "fresh_vietocr_numeric_proposal": None,
        "normalized_value": 0,
        "page_sequence": ref["page_sequence"],
        "pixel_transcription": "-",
        "render_binding": canonical_clone_v1(page["render_binding"]),
        "row_label_line_index": ref["row_label_line_index"],
        "source_numeric_challenger": "-",
        "source_numeric_challenger_status": "VISIBLE_AUTHENTICATED_PIXEL_DASH_NORMALIZED_ZERO",
    }


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(t["verified_accounting_equations"]) for t in trials
        ),
        "bound_report_detailed_note_absence_count": sum(
            t["status"] == "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT" for t in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(t["page_span"] is not None for t in trials),
        "mapping_verified_count": sum(len(t["verified_mappings"]) for t in trials),
        "open_source_row_count": sum(len(t["verified_source_only_rows"]) for t in trials),
        "q1_source_period_caveat_document_count": sum(
            t["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" for t in trials
        ),
        "verified_value_cell_count": sum(
            len(m["values"]) for t in trials for m in t["verified_mappings"]
        ),
        "visible_dash_zero_count": sum(
            v["source_numeric_challenger_status"]
            == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NORMALIZED_ZERO"
            for t in trials
            for m in t["verified_mappings"]
            for v in m["values"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("State-budget result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "STATE_BUDGET_OBLIGATIONS_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("State-budget result identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0095:result:" + canonical_json_sha256_v1(material):
        raise _error("State-budget result ID drifted")
    return canonical_clone_v1(value)


def build_state_budget_obligations_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    reviewed_documents = _review(review)["documents"]
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    scanner.validate_state_budget_obligations_full_document_scan_replay_v1(
        structure_scan, semantic_index
    )
    if (
        axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256
        or structure_scan["scan_id"] != EXPECTED_SCAN_ID
    ):
        raise _error("State-budget fixed inputs drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = other._document(reviewed_documents, code, "pixel review")
        scan_trial = other._document(structure_scan["trials"], code, "structure scan")
        matcher = scan_trial["matcher_result"]
        base = {
            "document_ordinal": ordinal,
            "document_provenance": code,
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
            "structure_graph_id": matcher["result_id"],
            "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
        }
        if reviewed["absence_evidence"] is not None:
            if matcher["regions"]:
                raise _error("absent State-budget note unexpectedly matched")
            trials.append(
                {
                    **base,
                    "absence_evidence": canonical_clone_v1(reviewed["absence_evidence"]),
                    "mapped_report_norm_ids": [],
                    "owner_evidence": [],
                    "page_span": None,
                    "source_period": None,
                    "source_period_status": "NOT_APPLICABLE_DETAILED_NOTE_ABSENT",
                    "status": "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                    "verified_source_only_rows": [],
                }
            )
            continue
        if (
            matcher["uniqueness"] != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or matcher["regions"][0]["page_span"] != reviewed["page_span"]
        ):
            raise _error("reviewed State-budget region is not unique")
        axis_document = other._document(axis["documents"], code, "accounting axis")
        semantic_document = other._document(semantic_index["documents"], code, "semantic index")
        crop_document = other._document(crop_manifest["documents"], code, "crop manifest")
        mappings = []
        by_role = {}
        for mapping in reviewed["mappings"]:
            values = []
            for ref in mapping["values"]:
                evidence = (
                    _dash_value(crop_document, ref)
                    if ref["kind"] == "AUTHENTICATED_VISIBLE_RENDER_DASH"
                    else other._verified_value(axis_document, semantic_document, crop_document, ref)
                )
                values.append({"axis_role": ref["axis_role"], **evidence})
            item = {
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in mapping["labels"]
                ],
                "role": mapping["role"],
                "schema_binding": _schema_binding(
                    schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                ),
                "status": "VERIFIED_BY_CODEX",
                "topology": mapping["topology"],
                "values": values,
            }
            mappings.append(item)
            by_role[item["role"]] = item
        equations = []
        for mapping in mappings:
            values = {item["axis_role"]: item["normalized_value"] for item in mapping["values"]}
            computed = (
                values["OPENING"]
                + values.get("BUSINESS_COMBINATION_INCREASE", 0)
                + values["PAYABLE_INCREASE"]
                - abs(values["PAID_DECREASE"])
            )
            if computed != values["CLOSING"]:
                raise _error("State-budget roll-forward equation does not close")
            equations.append(
                {
                    "computed_value": computed,
                    "name": "OPENING_PLUS_INCREASE_PLUS_PAYABLE_MINUS_PAID_EQUALS_CLOSING",
                    "role": mapping["role"],
                    "status": "VERIFIED_EXACT",
                    "visible_value": values["CLOSING"],
                }
            )
            if "CLOSING_PAYABLE" in values:
                recomputed = values["CLOSING_PAYABLE"] + values.get("CLOSING_RECEIVABLE", 0)
                if recomputed != values["CLOSING"]:
                    raise _error("State-budget closing payable/receivable equation does not close")
                equations.append(
                    {
                        "computed_value": recomputed,
                        "name": "CLOSING_PAYABLE_PLUS_RECEIVABLE_EQUALS_CLOSING_NET",
                        "role": mapping["role"],
                        "status": "VERIFIED_EXACT",
                        "visible_value": values["CLOSING"],
                    }
                )
        source_only = [
            {
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in row["labels"]
                ],
                "reason": row["reason"],
                "row_id": row["row_id"],
                "status": "UNRESOLVED_SCHEMA_SEMANTICS_SOURCE_ROW_RETAINED",
            }
            for row in reviewed["source_only_rows"]
        ]
        period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "mapped_report_norm_ids": sorted(
                    m["schema_binding"]["report_norm_id"] for m in mappings
                ),
                "owner_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["owner"]
                ],
                "page_span": list(reviewed["page_span"]),
                "source_period": reviewed["source_period"],
                "source_period_status": period_status,
                "status": "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
                if period_status.endswith("NOT_Q2")
                else "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SOURCE_ROW"
                if source_only
                else "VERIFIED_BY_CODEX",
                "unit_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": mappings,
                "verified_source_only_rows": source_only,
            }
        )
    mapped_union = sorted(
        {m["schema_binding"]["report_norm_id"] for t in trials for m in t["verified_mappings"]}
    )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": {
                "path": CROP_MANIFEST_PATH.as_posix(),
                "sha256": crop_manifest_sha256,
            },
            "pixel_review": {"path": REVIEW_PATH.as_posix(), "sha256": review_sha256},
            "schema_authority": canonical_clone_v1(schema_authority),
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": EXPECTED_INDEX_SHA256,
            },
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "schema_family": {
            "family_end_display_order": 855,
            "family_root": _schema_binding(schema_by_id.get(1269), 1269),
            "mapped_report_norm_ids": mapped_union,
            "section_root": _schema_binding(schema_by_id.get(1259), 1259),
        },
        "state": "STATE_BUDGET_OBLIGATIONS_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0095:result:" + canonical_json_sha256_v1(material)}
    )


def _stable_json(path: Path) -> tuple[dict[str, Any], str]:
    support = scanner._support()._support()
    raw = support._stable_bytes(path)
    return support._strict_json(raw, path.as_posix()), hashlib.sha256(raw).hexdigest()


def _live_inputs() -> dict[str, Any]:
    semantic_index, index_sha = _stable_json(SEMANTIC_INDEX_PATH)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH)
    review, review_sha = _stable_json(REVIEW_PATH)
    if index_sha != EXPECTED_INDEX_SHA256 or crop_sha != EXPECTED_CROP_MANIFEST_SHA256:
        raise _error("State-budget fixed input hash drifted")
    scan = scanner.build_state_budget_obligations_full_document_scan_v1(semantic_index)
    authority, by_id = _authority_snapshot(PROJECT_ROOT)
    for report_norm_id, (name, parent, display_order) in _SCHEMA_EXPECTED.items():
        item = by_id.get(report_norm_id)
        if (
            item is None
            or item.canonical_name != name
            or item.parent_id != parent
            or item.display_order != display_order
            or item.statement_type != "TM"
        ):
            raise _error(f"State-budget live schema drifted: {report_norm_id}")
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "review": review,
        "review_sha256": review_sha,
        "schema_authority": authority,
        "schema_by_id": by_id,
        "semantic_index": semantic_index,
        "structure_scan": scan,
    }


def build_live_state_budget_obligations_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_state_budget_obligations_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_state_budget_obligations_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_state_budget_obligations_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("State-budget result does not replay exactly")
    return supplied


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes_v1(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--validate-result", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        _write(REVIEW_PATH, _review_blueprint())
    if args.write_result:
        _write(RESULT_PATH, build_live_state_budget_obligations_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        value, _ = _stable_json(RESULT_PATH)
        validate_live_state_budget_obligations_8bank_codex_verified_mapping_v1(value)


if __name__ == "__main__":
    main()
