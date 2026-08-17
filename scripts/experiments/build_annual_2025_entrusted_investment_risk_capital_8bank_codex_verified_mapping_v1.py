"""Verify annual-2025 entrusted/investment-risk capital across eight banks."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_ENTRUSTED_INVESTMENT_RISK_CAPITAL_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_ENTRUSTED_INVESTMENT_RISK_CAPITAL_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_ENTRUSTED_INVESTMENT_RISK_CAPITAL_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025eirc8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_ENTRUSTED_INVESTMENT_RISK_CAPITAL_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025eirc8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0130"
REVIEW_PATH = Path(
    "docs/experiments/E-0130-annual-2025-entrusted-investment-risk-capital-8bank-"
    "codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0130-annual-2025-entrusted-investment-risk-capital-8bank-"
    "codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = "eircfds1:scan:c6f727d6e85012067e9e16f84c31b14d0f8068e17db7994d6428cd201f39e8e8"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "BANK_BLIND_ENTRUSTED_INVESTMENT_RISK_CAPITAL_OWNER_RECEIVED_SOURCE_"
    "OPTIONAL_CURRENCY_PROGRAMME_PERIOD_UNIT_VISIBLE_PIXEL_UPSTREAM_PPOCRV6_"
    "ACCOUNTING_USER_APPROVED_OTHER_AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)
_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION",
    "OWNER_PRECEDES_OPTIONAL_RECEIVED_SOURCE_CHILDREN",
    "PAIR_FIRST_GENERIC_VARIANT_GRAPH",
    "CURRENT_2025_AND_COMPARATIVE_2024_AXES",
    "VISIBLE_LOCAL_MILLION_VND_UNIT",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "UPSTREAM_PPOCRV6_OR_AUTHENTICATED_PIXEL_DASH_NUMERIC_CHALLENGER",
    "OPTIONAL_CURRENCY_AND_PROGRAMME_CHILDREN",
    "PARENT_CHILD_OR_REPEATED_TOTAL_ACCOUNTING",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_PPOCRV6_AND_ACCOUNTING",
    "reporting_period_dates_derived_from_pdf": True,
    "source_rows_without_exact_schema_may_use_explicit_other": True,
    "visible_bound_dash_normalized_to_zero": True,
    "unbound_visible_dash_promoted_to_zero": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "bounded_report_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "independent_pdf_pixel_and_upstream_ppocrv6_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_entrusted_capital_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reporting_period_dates_derived_from_pdf": True,
    "text_similarity_alone_used_for_mapping": False,
}
_SCHEMA_EXPECTED = {
    1092: (
        "Vốn nhận tài trợ, ủy thác đầu tư, cho vay các tổ chức tín dụng chịu rủi ro",
        560,
        603,
    ),
    1093: ("Vốn nhận của các tổ chức, cá nhân", 1092, 604),
    1094: ("Trong đó: + Bằng tiền VNĐ", 1092, 605),
    1095: ("+ Bằng ngoại tệ", 1092, 606),
    1096: ("Vốn nhận trực tiếp của các tổ chức quốc tế", 1092, 607),
    1097: ("Trong đó: + Bằng tiền VNĐ", 1092, 608),
    1098: ("+ Bằng ngoại tệ", 1092, 609),
    1099: ("Khác", 1092, 610),
}
_EXPECTED_IDS = {
    "ACB": {1092, 1096, 1097, 1098},
    "MBB": {1092, 1094},
    "VPB": {1092, 1099},
    "HDB": {1092, 1095},
    "VCB": {1092, 1094},
    "CTG": {1092, 1094, 1095},
    "BID": {1092, 1094, 1099},
    "VIB": {1092, 1099},
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 8,
    "bounded_report_absence_count": 0,
    "document_count": 8,
    "document_unique_region_count": 8,
    "mapping_verified_count": 20,
    "open_source_row_count": 0,
    "q1_source_period_caveat_document_count": 0,
    "verified_document_count": 8,
    "verified_value_cell_count": 40,
}


class Annual2025EntrustedInvestmentRiskCapital8BankError(ValueError):
    """Annual entrusted-capital evidence, accounting, schema or replay drifted."""


def _error(message: str) -> Annual2025EntrustedInvestmentRiskCapital8BankError:
    return Annual2025EntrustedInvestmentRiskCapital8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT / "scripts/experiments/"
        "build_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1.py"
    )
    spec = importlib.util.spec_from_file_location("annual_2025_entrusted_capital_base", path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load entrusted-capital support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    label, v, m, e = base._label, base._value, base._mapping, base._equation
    dash = base.foundation._dash(
        53,
        [1148, 1587, 1176, 1609],
        "0c4389692e0d96850eefbbeb97804015cec29dabbd3c6472db69f3bae39a1e0a",
    )
    documents = [
        base._present(
            "ACB",
            63,
            5,
            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TỔ CHỨC TÍN DỤNG CHỊU RỦI RO",
            [label(63, 6, "31.12.2025"), label(63, 7, "31.12.2024")],
            [label(63, 8, "Triệu VND"), label(63, 9, "Triệu VND")],
            [
                m(
                    1092,
                    "FAMILY_TOTAL",
                    [
                        label(
                            63,
                            5,
                            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TỔ CHỨC TÍN DỤNG CHỊU RỦI RO",
                        )
                    ],
                    [v(63, 18, "19.079")],
                    [v(63, 19, "28.008")],
                    "VISIBLE_UNLABELED_TOTAL",
                ),
                m(
                    1096,
                    "DIRECT_INTERNATIONAL_ORGANIZATION",
                    [
                        label(63, 10, "Vốn nhận từ Ngân hàng Hợp tác Quốc tế Nhật Bản bằng"),
                        label(63, 14, "Vốn nhận từ Ngân hàng Hợp tác Quốc tế Nhật Bản bằng"),
                    ],
                    [v(63, 18, "19.079")],
                    [v(63, 19, "28.008")],
                    "SUM_OF_VISIBLE_CURRENCY_CHILDREN",
                ),
                m(
                    1097,
                    "DIRECT_INTERNATIONAL_ORGANIZATION_VND",
                    [
                        label(63, 10, "Vốn nhận từ Ngân hàng Hợp tác Quốc tế Nhật Bản bằng"),
                        label(63, 11, "Đồng Việt Nam (i)"),
                    ],
                    [v(63, 12, "8.320")],
                    [v(63, 13, "15.832")],
                    "OWNER_CURRENCY_CHILD",
                ),
                m(
                    1098,
                    "DIRECT_INTERNATIONAL_ORGANIZATION_FOREIGN_CURRENCY",
                    [
                        label(63, 14, "Vốn nhận từ Ngân hàng Hợp tác Quốc tế Nhật Bản bằng"),
                        label(63, 15, "ngoại tệ (ii)"),
                    ],
                    [v(63, 16, "10.759")],
                    [v(63, 17, "12.176")],
                    "OWNER_CURRENCY_CHILD",
                ),
            ],
            [
                e(
                    "CURRENCY_CHILDREN_TO_VISIBLE_TOTAL",
                    "CURRENT",
                    [v(63, 12, "8.320"), v(63, 16, "10.759")],
                    v(63, 18, "19.079"),
                ),
                e(
                    "CURRENCY_CHILDREN_TO_VISIBLE_TOTAL",
                    "COMPARATIVE",
                    [v(63, 13, "15.832"), v(63, 17, "12.176")],
                    v(63, 19, "28.008"),
                ),
            ],
            source_period="2025-12-31",
        ),
        base._present(
            "MBB",
            66,
            56,
            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO",
            [label(66, 57, "31/12/2025"), label(66, 58, "31/12/2024")],
            [label(66, 59, "triệu đồng"), label(66, 60, "triệu đồng")],
            [
                m(
                    1092,
                    "FAMILY_TOTAL",
                    [label(66, 56, "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO")],
                    [v(66, 62, "3.912.833")],
                    [v(66, 63, "2.793.453")],
                    "SOLE_VISIBLE_CHILD_DEFINES_TOTAL",
                ),
                m(
                    1094,
                    "VND_RECEIVED_SOURCE",
                    [label(66, 61, "Vốn tài trợ, ủy thác đầu tư, cho vay bằng VND")],
                    [v(66, 62, "3.912.833")],
                    [v(66, 63, "2.793.453")],
                    "OWNER_CURRENCY_CHILD",
                ),
            ],
            [],
            source_period="2025-12-31",
        ),
        base._present(
            "VPB",
            62,
            5,
            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TỔ CHỨC TÍN DỤNG CHỊU RỦI RO",
            [
                label(62, 6, "Ngày 31 tháng 12"),
                label(62, 8, "năm 2025"),
                label(62, 7, "Ngày 31 tháng 12"),
                label(62, 9, "năm 2024"),
            ],
            [label(62, 10, "Triệu đồng"), label(62, 11, "Triệu đồng")],
            [
                m(
                    1092,
                    "FAMILY_TOTAL",
                    [
                        label(
                            62,
                            5,
                            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TỔ CHỨC TÍN DỤNG CHỊU RỦI RO",
                        )
                    ],
                    [v(62, 14, "16.394")],
                    [v(62, 15, "10.894")],
                    "SOLE_VISIBLE_CHILD_DEFINES_TOTAL",
                ),
                m(
                    1099,
                    "OTHER_ODA_SOURCE",
                    [
                        label(62, 12, "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng"),
                        label(62, 13, "VND từ Dự án Hỗ trợ phát triển chính thức (ODA)"),
                    ],
                    [v(62, 14, "16.394")],
                    [v(62, 15, "10.894")],
                    "OWNER_SMALL_UNLISTED_CHILD_TO_EXPLICIT_OTHER",
                ),
            ],
            [],
            source_period="2025-12-31",
        ),
        base._present(
            "HDB",
            45,
            83,
            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO",
            [label(45, 84, "Số cuối năm"), label(45, 85, "Số đầu năm")],
            [label(45, 86, "Triệu VND"), label(45, 87, "Triệu VND")],
            [
                m(
                    1092,
                    "FAMILY_TOTAL",
                    [label(45, 83, "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO")],
                    [v(45, 100, "2.721.952")],
                    [v(45, 101, "2.788.443")],
                    "VISIBLE_UNLABELED_TOTAL",
                ),
                m(
                    1095,
                    "FOREIGN_CURRENCY_RECEIVED_SOURCE",
                    [label(45, 88, "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng ngoại tệ")],
                    [v(45, 100, "2.721.952")],
                    [v(45, 101, "2.788.443")],
                    "SUM_OF_VISIBLE_PROGRAMME_CHILDREN",
                ),
            ],
            [
                e(
                    "PROGRAMME_CHILDREN_TO_FOREIGN_CURRENCY_TOTAL",
                    "CURRENT",
                    [v(45, 90, "2.672.116"), v(45, 94, "49.221"), v(45, 98, "615")],
                    v(45, 100, "2.721.952"),
                ),
                e(
                    "PROGRAMME_CHILDREN_TO_FOREIGN_CURRENCY_TOTAL",
                    "COMPARATIVE",
                    [v(45, 91, "2.736.762"), v(45, 95, "50.991"), v(45, 99, "690")],
                    v(45, 101, "2.788.443"),
                ),
            ],
            source_period="2025-12-31",
        ),
        base._present(
            "VCB",
            53,
            57,
            "Vốn tài trợ, ủy thác đầu tư, cho vay tổ chức tín dụng chịu rủi ro",
            [label(53, 58, "31/12/2025"), label(53, 59, "31/12/2024")],
            [label(53, 60, "Triệu VND"), label(53, 61, "Triệu VND")],
            [
                m(
                    1092,
                    "FAMILY_TOTAL",
                    [
                        label(
                            53,
                            57,
                            "Vốn tài trợ, ủy thác đầu tư, cho vay tổ chức tín dụng chịu rủi ro",
                        )
                    ],
                    [dash],
                    [v(53, 63, "529")],
                    "SOLE_VISIBLE_CHILD_DEFINES_TOTAL",
                ),
                m(
                    1094,
                    "VND_RECEIVED_SOURCE",
                    [label(53, 62, "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng VND")],
                    [dash],
                    [v(53, 63, "529")],
                    "OWNER_CURRENCY_CHILD",
                ),
            ],
            [],
            source_period="2025-12-31",
        ),
        base._present(
            "CTG",
            53,
            6,
            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO",
            [label(53, 7, "31.12.2025"), label(53, 8, "31.12.2024")],
            [label(53, 9, "Triệu đồng"), label(53, 10, "Triệu đồng")],
            [
                m(
                    1092,
                    "FAMILY_TOTAL",
                    [label(53, 6, "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO")],
                    [v(53, 17, "2.113.898")],
                    [v(53, 18, "2.179.950")],
                    "VISIBLE_UNLABELED_TOTAL",
                ),
                m(
                    1094,
                    "VND_RECEIVED_SOURCE",
                    [label(53, 11, "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng VND")],
                    [v(53, 12, "360.147")],
                    [v(53, 13, "402.575")],
                    "OWNER_CURRENCY_CHILD",
                ),
                m(
                    1095,
                    "FOREIGN_CURRENCY_RECEIVED_SOURCE",
                    [label(53, 14, "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng ngoại tệ")],
                    [v(53, 15, "1.753.751")],
                    [v(53, 16, "1.777.375")],
                    "OWNER_CURRENCY_CHILD",
                ),
            ],
            [
                e(
                    "CURRENCY_CHILDREN_TO_VISIBLE_TOTAL",
                    "CURRENT",
                    [v(53, 12, "360.147"), v(53, 15, "1.753.751")],
                    v(53, 17, "2.113.898"),
                ),
                e(
                    "CURRENCY_CHILDREN_TO_VISIBLE_TOTAL",
                    "COMPARATIVE",
                    [v(53, 13, "402.575"), v(53, 16, "1.777.375")],
                    v(53, 18, "2.179.950"),
                ),
            ],
            source_period="2025-12-31",
        ),
        base._present(
            "BID",
            51,
            96,
            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO",
            [label(51, 99, "Số cuối năm"), label(51, 100, "Số đầu năm")],
            [label(51, 101, "Triệu VND"), label(51, 102, "Triệu VND")],
            [
                m(
                    1092,
                    "FAMILY_TOTAL",
                    [label(51, 96, "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO")],
                    [v(51, 111, "12.043.069")],
                    [v(51, 112, "11.981.467")],
                    "VISIBLE_UNLABELED_TOTAL",
                ),
                m(
                    1094,
                    "VND_RECEIVED_SOURCE",
                    [label(51, 104, "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng VND")],
                    [v(51, 105, "7.968.760")],
                    [v(51, 106, "8.456.010")],
                    "OWNER_CURRENCY_CHILD",
                ),
                m(
                    1099,
                    "OTHER_GOLD_AND_FOREIGN_CURRENCY_COMBINED",
                    [
                        label(51, 107, "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng vàng"),
                        label(51, 110, "và ngoại tệ"),
                    ],
                    [v(51, 108, "4.074.309")],
                    [v(51, 109, "3.525.457")],
                    "COMBINED_SOURCE_CONCEPT_TO_EXPLICIT_OTHER_WITHOUT_SPLIT",
                ),
            ],
            [
                e(
                    "VISIBLE_CHILDREN_TO_TOTAL",
                    "CURRENT",
                    [v(51, 105, "7.968.760"), v(51, 108, "4.074.309")],
                    v(51, 111, "12.043.069"),
                ),
                e(
                    "VISIBLE_CHILDREN_TO_TOTAL",
                    "COMPARATIVE",
                    [v(51, 106, "8.456.010"), v(51, 109, "3.525.457")],
                    v(51, 112, "11.981.467"),
                ),
            ],
            source_period="2025-12-31",
        ),
        base._present(
            "VIB",
            47,
            97,
            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO",
            [label(47, 98, "31/12/2025"), label(47, 99, "31/12/2024")],
            [label(47, 100, "triệu đồng"), label(47, 101, "triệu đồng")],
            [
                m(
                    1092,
                    "FAMILY_TOTAL",
                    [label(47, 97, "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO")],
                    [v(47, 104, "3.306")],
                    [v(47, 105, "5.368")],
                    "SOLE_VISIBLE_CHILD_DEFINES_TOTAL",
                ),
                m(
                    1099,
                    "OTHER_NHNN_HOUSING_PROGRAMME",
                    [
                        label(47, 102, "Vốn nhận ủy thác từ NHNN theo Chương trình cho vay"),
                        label(47, 103, "hỗ trợ nhà ở Nghị quyết số 02/NQ-CP do Chính phủ"),
                        label(47, 106, "ban hành ngày 7 tháng 1 năm 2013"),
                    ],
                    [v(47, 104, "3.306")],
                    [v(47, 105, "5.368")],
                    "OWNER_SMALL_UNLISTED_CHILD_TO_EXPLICIT_OTHER",
                ),
            ],
            [],
            source_period="2025-12-31",
        ),
    ]
    return documents


def _configure(base: ModuleType) -> None:
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.CLAIM_BOUNDARY = CLAIM_BOUNDARY
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base._RESULT_STATE = RESULT_STATE
    base._RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base._REVIEW_STATE = REVIEW_STATE
    base._REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base._REVIEW_RUN_ID = REVIEW_RUN_ID
    base._EXPECTED_COMPLETE_REGION_COUNT = 8
    base._FAMILY_DISPLAY_ORDER_RANGE = [603, 610]
    base._REVIEW_CHECKS = list(_REVIEW_CHECKS)
    base._REVIEW_SAFETY = dict(_REVIEW_SAFETY)
    base._AUTHORITY = dict(_AUTHORITY)
    base._SCHEMA_EXPECTED = dict(_SCHEMA_EXPECTED)
    base._review_documents = lambda: _review_documents(base)
    base._source_period_status = lambda source_period: (
        "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        if source_period == "2025-12-31"
        else "INVALID_ANNUAL_SOURCE_PERIOD"
    )


def _assert_result(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual entrusted-capital result metrics drifted")
    for trial in value.get("trials", []):
        actual = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        if actual != _EXPECTED_IDS[trial["document_provenance"]]:
            raise _error("annual entrusted-capital mapped schema set drifted")
        if trial["source_period_status"] != (
            "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        ):
            raise _error("annual entrusted-capital period status drifted")
    return value


def build_annual_2025_entrusted_investment_risk_capital_pixel_review_blueprint_v1() -> dict[
    str, Any
]:
    base = _load_base()
    _configure(base)
    return base._review_blueprint()


def build_live_annual_2025_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1() -> (
    dict[str, Any]
):
    base = _load_base()
    _configure(base)
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review = base._review_blueprint()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    scan = base.scanner.build_entrusted_investment_risk_capital_full_document_scan_v1(
        semantic_index
    )
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    result = base.build_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    replayed = (
        base.validate_entrusted_investment_risk_capital_8bank_codex_verified_mapping_replay_v1(
            result,
            semantic_index,
            crop_manifest,
            review,
            schema_authority,
            schema_by_id,
            crop_manifest_sha256=crop_sha,
            review_sha256=review_sha,
        )
    )
    return _assert_result(replayed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    if args.write_review:
        args.output.write_bytes(
            canonical_json_bytes_v1(
                build_annual_2025_entrusted_investment_risk_capital_pixel_review_blueprint_v1()
            )
        )
    else:
        result = build_live_annual_2025_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1()
        args.output.write_bytes(canonical_json_bytes_v1(result))
        print(result["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
