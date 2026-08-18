"""Verify annual-2025 service-activity disclosures across eight banks.

The annual profile reuses the service-activity evidence and mapping core.  Its
V2 family graph adds only two generic presentations: a net-service owner, or
ordered income/expense sibling parents when the detailed note omits that owner.
All complete PDFs are scanned.  Numeric values come from the authenticated
source axis; fresh VietOCR remains text/proposal evidence.  Source rows that
combine consulting with trust/agency are retained as schema gaps and still
participate in the exact parent equations.
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
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_SERVICE_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_SERVICE_ACTIVITY_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_SERVICE_ACTIVITY_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025sa8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_SERVICE_ACTIVITY_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025sa8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0137"
OPEN_SOURCE_TRIAL_STATUS = "VERIFIED_BY_CODEX_WITH_SOURCE_SCHEMA_GAPS"
REVIEW_PATH = Path(
    "docs/experiments/E-0137-annual-2025-service-activity-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0137-annual-2025-service-activity-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = (
    "annual2025safdsv1:scan:a5e08047897ae18951ccb67081faf483e3653873c6a2060a9577566207909c3f"
)

_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 48,
    "authenticated_pixel_dash_zero_count": 0,
    "detailed_note_not_present_document_count": 0,
    "document_count": 8,
    "document_unique_region_count": 8,
    "fresh_vietocr_numeric_disagreement_count": 2,
    "mapping_verified_count": 101,
    "open_source_row_count": 2,
    "q1_source_period_caveat_document_count": 0,
    "source_only_value_cell_count": 4,
    "verified_value_cell_count": 202,
}
_EXPECTED_PAGES = {
    "ACB": [67, 67],
    "MBB": [72, 72],
    "VPB": [69, 69],
    "HDB": [50, 50],
    "VCB": [58, 58],
    "CTG": [58, 58],
    "BID": [55, 55],
    "VIB": [50, 50],
}
_EXPECTED_REPORT_NORM_IDS = {
    "ACB": {1157, 1158, 1159, 1160, 1166, 1167, 1168, 1169, 1170, 1174, 5989},
    "MBB": {
        1157,
        1158,
        1159,
        1160,
        1163,
        1164,
        1166,
        1167,
        1168,
        1169,
        1171,
        1172,
        1174,
        5986,
        5988,
        5989,
        6022,
        6024,
        6025,
    },
    "VPB": {
        1157,
        1158,
        1164,
        1166,
        1167,
        1168,
        1171,
        1174,
        5986,
        5987,
        5989,
        6021,
        6023,
        6024,
    },
    "HDB": {1157, 1158, 1164, 1166, 1167, 1168, 1171, 1174, 5989, 6024},
    "VCB": {1157, 1158, 1159, 1163, 1166, 1167, 1168, 1169, 1172, 1173, 1174, 5989},
    "CTG": {1157, 1164, 1166, 1167, 1171, 1174, 5989, 6021, 6023},
    "BID": {1157, 1158, 1159, 1163, 1164, 1166, 1167, 1168, 1169, 1171, 1172, 1173, 1174, 5989},
    "VIB": {1157, 1158, 1164, 1166, 1167, 1168, 1170, 1171, 1172, 1173, 1174, 5989},
}

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_SERVICE_ACTIVITY_V2_GRAPH_VISIBLE_PDF_UPSTREAM_"
    "PPOCRV6_NUMERIC_CHALLENGER_PERIOD_UNIT_ACCOUNTING_LIVE_TM_SCHEMA_"
    "AND_EXPLICIT_COMBINED_SOURCE_SCHEMA_GAPS_ONLY_NO_CANONICALIZATION_"
    "EXPORT_OR_PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "income_expense_sibling_without_net_owner_supported": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_service_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_combined_rows_silently_narrowed_or_split": False,
    "text_similarity_alone_used_for_mapping": False,
    "whole_pdf_uniqueness_replayed": True,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "positive_expense_magnitude_silently_treated_as_income": False,
    "source_combined_consulting_trust_agency_split": False,
    "whole_pdf_uniqueness_replayed": True,
}
_SCHEMA_EXPECTED = {
    1157: ("Thu nhập từ hoạt động dịch vụ", 1142, 704),
    6021: ("Thu từ dịch vụ thanh toán và ngân quỹ", 1157, 705),
    1158: ("Dịch vụ thanh toán và tiền mặt", 1157, 706),
    1159: ("Dịch vụ ngân quỹ, bảo lãnh", 1157, 707),
    1160: ("Dịch vụ chứng khoán", 1157, 708),
    6022: ("Thu từ xử lý nợ, thẩm định giá và khai thác tài sản", 1157, 711),
    1163: ("Thu từ nghiệp vụ ủy thác và đại lý", 1157, 712),
    1164: ("Hoạt động bảo hiểm", 1157, 713),
    5986: ("Thu từ dịch vụ tư vấn", 1157, 715),
    1166: ("Các dịch vụ khác", 1157, 716),
    1167: ("Chi phí từ hoạt động dịch vụ", 1142, 717),
    6023: ("Chi về dịch vụ thanh toán và ngân quỹ", 1167, 718),
    1168: ("Dịch vụ thanh toán", 1167, 719),
    1169: ("Dịch vụ ngân quỹ, bảo lãnh", 1167, 720),
    1170: ("Dịch vụ môi giới chứng khoán", 1167, 721),
    6024: ("Chi phí hoa hồng môi giới", 1170, 722),
    6025: ("Chi về hoạt động môi giới chứng khoán", 1170, 723),
    1171: ("Hoạt động bảo hiểm", 1167, 724),
    1172: ("Chi về dịch vụ ủy thác và đại lý", 1167, 725),
    1173: ("Chi về dịch vụ viễn thông, nghiệp vụ ủy thác và đại lý", 1167, 726),
    5987: ("Chi về dịch vụ tư vấn", 1167, 727),
    5988: ("Chi về xử lý nợ, thẩm định giá và khai thác tài sản", 1167, 728),
    1174: ("Chi phí hoạt động khác", 1167, 729),
    5989: ("Lãi thuần từ hoạt động dịch vụ", 1142, 730),
}


class Annual2025ServiceActivity8BankError(ValueError):
    """Annual service structure, numeric, accounting, or schema evidence drifted."""


def _error(message: str) -> Annual2025ServiceActivity8BankError:
    return Annual2025ServiceActivity8BankError(message)


def _load(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual service support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_base() -> ModuleType:
    return _load(
        "annual_2025_service_activity_base",
        "build_service_activity_8bank_codex_verified_mapping_v1.py",
    )


def _load_matcher() -> ModuleType:
    return _load("annual_2025_service_activity_matcher", "service_activity_variant_graph_v1.py")


def _ref(base: ModuleType, item: tuple[int, int, str]) -> dict[str, Any]:
    page, line, text = item
    return base._line(page, line, text)


def _label(base: ModuleType, item: tuple[int, int, str]) -> dict[str, Any]:
    page, line, text = item
    return base._label(page, line, text)


def _mapped(
    base: ModuleType,
    report_norm_id: int,
    role: str,
    label: tuple[int, int, str],
    current: tuple[int, int, str],
    comparative: tuple[int, int, str],
    *,
    topology: str = "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
) -> dict[str, Any]:
    return base._mapping(
        report_norm_id,
        role,
        _label(base, label),
        _ref(base, current),
        _ref(base, comparative),
        topology=topology,
    )


def _source_only(
    base: ModuleType,
    gap_id: str,
    role: str,
    label: tuple[int, int, str],
    current: tuple[int, int, str],
    comparative: tuple[int, int, str],
) -> dict[str, Any]:
    return {
        "gap_id": gap_id,
        "label": _label(base, label),
        "reason": "NO_EXACT_SCHEMA_LEAF_FOR_COMBINED_CONSULTING_TRUST_AND_AGENCY_ROW",
        "role": role,
        "topology": "DIRECT_VISIBLE_COMBINED_SOURCE_ROW_TWO_PERIOD_LANES",
        "values": {
            "COMPARATIVE_PERIOD": _ref(base, comparative),
            "CURRENT_PERIOD": _ref(base, current),
        },
    }


def _doc(
    base: ModuleType,
    code: str,
    page: int,
    owner: tuple[int, int, str],
    periods: Sequence[tuple[int, int, str]],
    units: Sequence[tuple[int, int, str]],
    rows: Sequence[dict[str, Any]],
    presentation: str,
    *,
    source_only_rows: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    document = base._doc(
        code,
        page,
        owner[1],
        owner[2],
        [_label(base, item) for item in periods],
        [_label(base, item) for item in units],
        rows,
        presentation,
        source_period="2025-12-31",
    )
    document["owner"] = _label(base, owner)
    document["source_only_rows"] = list(source_only_rows)
    return document


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    documents = []

    p = 67
    documents.append(
        _doc(
            base,
            "ACB",
            p,
            (p, 57, "THU NHẬP TỪ HOẠT ĐỘNG DỊCH VỤ"),
            [(p, 58, "Năm 2025"), (p, 59, "Năm 2024")],
            [(p, 60, "Triệu VND"), (p, 61, "Triệu VND")],
            [
                _mapped(
                    base,
                    1157,
                    "INCOME_PARENT",
                    (p, 57, "THU NHẬP TỪ HOẠT ĐỘNG DỊCH VỤ"),
                    (p, 74, "5.196.123"),
                    (p, 75, "5.464.958"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _mapped(
                    base,
                    1158,
                    "INCOME_PAYMENT",
                    (p, 62, "Dịch vụ thanh toán"),
                    (p, 63, "3.023.052"),
                    (p, 64, "3.228.334"),
                ),
                _mapped(
                    base,
                    1159,
                    "INCOME_TREASURY",
                    (p, 65, "Dịch vụ ngân quỹ"),
                    (p, 66, "9.012"),
                    (p, 67, "10.202"),
                ),
                _mapped(
                    base,
                    1160,
                    "INCOME_SECURITIES",
                    (p, 68, "Dịch vụ chứng khoán"),
                    (p, 69, "456.850"),
                    (p, 70, "386.178"),
                ),
                _mapped(
                    base,
                    1166,
                    "INCOME_OTHER",
                    (p, 71, "Các dịch vụ khác"),
                    (p, 72, "1.707.209"),
                    (p, 73, "1.840.244"),
                ),
                _mapped(
                    base,
                    1167,
                    "EXPENSE_PARENT",
                    (p, 78, "CHI PHÍ HOẠT ĐỘNG DỊCH VỤ"),
                    (p, 97, "2.049.383"),
                    (p, 98, "2.226.173"),
                    topology="TRAILING_UNLABELED_POSITIVE_MAGNITUDE_PARENT_TOTAL",
                ),
                _mapped(
                    base,
                    1168,
                    "EXPENSE_PAYMENT",
                    (p, 85, "Dịch vụ thanh toán"),
                    (p, 86, "1.489.934"),
                    (p, 87, "1.572.616"),
                ),
                _mapped(
                    base,
                    1169,
                    "EXPENSE_TREASURY",
                    (p, 88, "Dịch vụ ngân quỹ"),
                    (p, 89, "29.633"),
                    (p, 90, "25.936"),
                ),
                _mapped(
                    base,
                    1170,
                    "EXPENSE_SECURITIES",
                    (p, 91, "Dịch vụ chứng khoán"),
                    (p, 92, "148.470"),
                    (p, 93, "126.888"),
                ),
                _mapped(
                    base,
                    1174,
                    "EXPENSE_OTHER",
                    (p, 94, "Các dịch vụ khác"),
                    (p, 95, "381.346"),
                    (p, 96, "500.733"),
                ),
                _mapped(
                    base,
                    5989,
                    "NET_SERVICE_ACTIVITY",
                    (10, 34, "Lãi thuần từ hoạt động dịch vụ"),
                    (10, 35, "3.146.740"),
                    (10, 36, "3.238.785"),
                    topology="CROSS_PAGE_CONSOLIDATED_INCOME_STATEMENT_RECONCILIATION",
                ),
            ],
            "ORDERED_INCOME_EXPENSE_SIBLING_NOTES_WITH_CROSS_PAGE_STATEMENT_NET",
        )
    )

    p = 72
    documents.append(
        _doc(
            base,
            "MBB",
            p,
            (p, 55, "LÃI THUẦN TỪ HOẠT ĐỘNG DỊCH VỤ"),
            [(p, 56, "Năm 2025"), (p, 57, "Năm 2024")],
            [(p, 58, "triệu đồng"), (p, 59, "triệu đồng")],
            [
                _mapped(
                    base,
                    1157,
                    "INCOME_PARENT",
                    (p, 60, "Thu nhập từ hoạt động dịch vụ"),
                    (p, 61, "18.062.236"),
                    (p, 62, "14.602.602"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _mapped(
                    base,
                    1158,
                    "INCOME_PAYMENT",
                    (p, 63, "Thu từ dịch vụ thanh toán"),
                    (p, 64, "4.577.142"),
                    (p, 65, "3.350.501"),
                ),
                _mapped(
                    base,
                    1160,
                    "INCOME_BROKERAGE",
                    (p, 66, "Thu từ hoạt động môi giới chứng khoán"),
                    (p, 67, "923.466"),
                    (p, 68, "628.155"),
                ),
                _mapped(
                    base,
                    6022,
                    "INCOME_DEBT_VALUATION",
                    (p, 70, "Thu từ xử lý nợ, thẩm định giá và khai thác tài sản"),
                    (p, 71, "427.267"),
                    (p, 72, "494.094"),
                ),
                _mapped(
                    base,
                    1164,
                    "INCOME_INSURANCE",
                    (p, 73, "Thu từ kinh doanh, dịch vụ bảo hiểm và doanh thu"),
                    (p, 75, "9.331.198"),
                    (p, 76, "8.443.178"),
                    topology="TWO_LINE_SOURCE_LABEL_CONTINUES_WITH_PRIMARY_INSURANCE_FEES",
                ),
                _mapped(
                    base,
                    5986,
                    "INCOME_CONSULTING",
                    (p, 77, "Thu từ dịch vụ tư vấn"),
                    (p, 78, "1.000.100"),
                    (p, 79, "280.325"),
                ),
                _mapped(
                    base,
                    1163,
                    "INCOME_TRUST_AGENCY",
                    (p, 80, "Thu từ dịch vụ đại lý nhận ủy thác"),
                    (p, 81, "15.708"),
                    (p, 82, "27.002"),
                ),
                _mapped(
                    base,
                    1159,
                    "INCOME_TREASURY",
                    (p, 83, "Thu từ dịch vụ ngân quỹ"),
                    (p, 84, "8.452"),
                    (p, 85, "8.520"),
                ),
                _mapped(
                    base,
                    1166,
                    "INCOME_OTHER",
                    (p, 86, "Thu phí khác"),
                    (p, 87, "1.778.903"),
                    (p, 88, "1.370.827"),
                ),
                _mapped(
                    base,
                    1167,
                    "EXPENSE_PARENT",
                    (p, 89, "Chi phí hoạt động dịch vụ"),
                    (p, 90, "(11.483.555)"),
                    (p, 91, "(10.234.353)"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _mapped(
                    base,
                    1168,
                    "EXPENSE_PAYMENT",
                    (p, 92, "Chi về dịch vụ thanh toán"),
                    (p, 93, "(2.684.406)"),
                    (p, 94, "(2.253.715)"),
                ),
                _mapped(
                    base,
                    6024,
                    "EXPENSE_BROKERAGE_COMMISSION",
                    (p, 95, "Chi phí hoa hồng môi giới"),
                    (p, 96, "(1.682.627)"),
                    (p, 97, "(1.046.664)"),
                ),
                _mapped(
                    base,
                    5988,
                    "EXPENSE_DEBT_VALUATION",
                    (p, 98, "Chi về xử lý nợ, thẩm định giá và khai thác tài sản"),
                    (p, 99, "(326.970)"),
                    (p, 100, "(440.761)"),
                ),
                _mapped(
                    base,
                    1171,
                    "EXPENSE_INSURANCE",
                    (p, 101, "Chi về hoạt động kinh doanh bảo hiểm"),
                    (p, 102, "(6.276.805)"),
                    (p, 103, "(6.174.019)"),
                ),
                _mapped(
                    base,
                    6025,
                    "EXPENSE_SECURITIES_BROKERAGE",
                    (p, 104, "Chi về hoạt động môi giới chứng khoán"),
                    (p, 105, "(225.951)"),
                    (p, 106, "(146.539)"),
                ),
                _mapped(
                    base,
                    1172,
                    "EXPENSE_TRUST_AGENCY",
                    (p, 107, "Chi về nghiệp vụ ủy thác và đại lý"),
                    (p, 108, "(22.894)"),
                    (p, 109, "(18.063)"),
                ),
                _mapped(
                    base,
                    1169,
                    "EXPENSE_TREASURY",
                    (p, 110, "Chi về hoạt động ngân quỹ"),
                    (p, 111, "(40.374)"),
                    (p, 112, "(31.790)"),
                ),
                _mapped(
                    base,
                    1174,
                    "EXPENSE_OTHER",
                    (p, 113, "Chi khác"),
                    (p, 114, "(223.528)"),
                    (p, 115, "(122.802)"),
                ),
                _mapped(
                    base,
                    5989,
                    "NET_SERVICE_ACTIVITY",
                    (p, 116, "Lãi thuần từ hoạt động dịch vụ"),
                    (p, 117, "6.578.681"),
                    (p, 118, "4.368.249"),
                ),
            ],
            "LEADING_INCOME_AND_EXPENSE_TOTALS_LABELLED_TRAILING_NET",
        )
    )

    p = 69
    documents.append(
        _doc(
            base,
            "VPB",
            p,
            (p, 5, "LÃI THUẦN TỪ HOẠT ĐỘNG DỊCH VỤ"),
            [(p, 6, "Năm 2025"), (p, 7, "Năm 2024")],
            [(p, 9, "Triệu đồng"), (p, 10, "Triệu đồng")],
            [
                _mapped(
                    base,
                    1157,
                    "INCOME_PARENT",
                    (p, 11, "Thu nhập từ hoạt động dịch vụ"),
                    (p, 12, "15.030.415"),
                    (p, 13, "12.279.665"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _mapped(
                    base,
                    6021,
                    "INCOME_PAYMENT_TREASURY",
                    (p, 14, "Thu từ dịch vụ thanh toán và ngân quỹ"),
                    (p, 15, "2.119.913"),
                    (p, 16, "3.484.132"),
                ),
                _mapped(
                    base,
                    5986,
                    "INCOME_CONSULTING",
                    (p, 18, "Thu từ dịch vụ tư vấn"),
                    (p, 19, "974.406"),
                    (p, 20, "139.026"),
                ),
                _mapped(
                    base,
                    1164,
                    "INCOME_INSURANCE",
                    (p, 21, "Thu từ kinh doanh và dịch vụ bảo hiểm"),
                    (p, 22, "5.905.108"),
                    (p, 23, "4.150.911"),
                ),
                _mapped(
                    base,
                    1158,
                    "INCOME_CARD",
                    (p, 24, "Thu phí liên quan đến các loại thẻ"),
                    (p, 25, "2.249.087"),
                    (p, 26, "2.446.882"),
                ),
                _mapped(
                    base,
                    1166,
                    "INCOME_OTHER",
                    (p, 27, "Thu khác"),
                    (p, 28, "3.781.901"),
                    (p, 29, "2.058.714"),
                ),
                _mapped(
                    base,
                    1167,
                    "EXPENSE_PARENT",
                    (p, 30, "Chi phí hoạt động dịch vụ"),
                    (p, 31, "(7.648.752)"),
                    (p, 32, "(7.075.337)"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _mapped(
                    base,
                    6023,
                    "EXPENSE_PAYMENT_TREASURY",
                    (p, 33, "Chi về dịch vụ thanh toán và ngân quỹ"),
                    (p, 34, "(1.390.462)"),
                    (p, 35, "(2.135.183)"),
                ),
                _mapped(
                    base,
                    5987,
                    "EXPENSE_CONSULTING",
                    (p, 36, "Chi dịch vụ tư vấn"),
                    (p, 37, "(6.198)"),
                    (p, 38, "(73)"),
                ),
                _mapped(
                    base,
                    1171,
                    "EXPENSE_INSURANCE",
                    (p, 39, "Chi về dịch vụ bảo hiểm"),
                    (p, 40, "(2.128.179)"),
                    (p, 41, "(1.035.286)"),
                ),
                _mapped(
                    base,
                    6024,
                    "EXPENSE_BROKERAGE_COMMISSION",
                    (p, 42, "Hoa hồng môi giới"),
                    (p, 43, "(784.060)"),
                    (p, 44, "(447.900)"),
                ),
                _mapped(
                    base,
                    1168,
                    "EXPENSE_CARD",
                    (p, 45, "Chi cho hoạt động thẻ"),
                    (p, 46, "(1.322.247)"),
                    (p, 47, "(1.259.668)"),
                ),
                _mapped(
                    base,
                    1174,
                    "EXPENSE_OTHER",
                    (p, 48, "Chi khác"),
                    (p, 49, "(2.017.606)"),
                    (p, 50, "(2.197.227)"),
                ),
                _mapped(
                    base,
                    5989,
                    "NET_SERVICE_ACTIVITY",
                    (p, 5, "LÃI THUẦN TỪ HOẠT ĐỘNG DỊCH VỤ"),
                    (p, 51, "7.381.663"),
                    (p, 52, "5.204.328"),
                    topology="TRAILING_UNLABELED_NET_TOTAL",
                ),
            ],
            "LEADING_INCOME_AND_EXPENSE_TOTALS_UNLABELLED_TRAILING_NET",
        )
    )

    p = 50
    documents.append(
        _doc(
            base,
            "HDB",
            p,
            (p, 8, "LÃI THUẦN TỪ HOẠT ĐỘNG DỊCH VỤ"),
            [(p, 10, "Năm nay"), (p, 9, "Năm trước")],
            [(p, 12, "Triệu VND"), (p, 13, "Triệu VND")],
            [
                _mapped(
                    base,
                    1157,
                    "INCOME_PARENT",
                    (p, 14, "Thu nhập từ hoạt động dịch vụ"),
                    (p, 15, "5.697.854"),
                    (p, 16, "3.648.913"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _mapped(
                    base,
                    1158,
                    "INCOME_PAYMENT",
                    (p, 17, "Thu từ dịch vụ thanh toán"),
                    (p, 18, "1.910.707"),
                    (p, 19, "1.879.608"),
                ),
                _mapped(
                    base,
                    1164,
                    "INCOME_INSURANCE",
                    (p, 20, "Thu từ dịch vụ đại lý bảo hiểm"),
                    (p, 21, "1.348.300"),
                    (p, 22, "1.082.915"),
                ),
                _mapped(
                    base,
                    1166,
                    "INCOME_OTHER",
                    (p, 23, "Thu dịch vụ khác"),
                    (p, 24, "2.438.847"),
                    (p, 25, "686.390"),
                ),
                _mapped(
                    base,
                    1167,
                    "EXPENSE_PARENT",
                    (p, 26, "Chi phí cho hoạt động dịch vụ"),
                    (p, 27, "(1.571.814)"),
                    (p, 28, "(1.879.045)"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _mapped(
                    base,
                    1168,
                    "EXPENSE_PAYMENT",
                    (p, 29, "Chi về dịch vụ thanh toán"),
                    (p, 30, "(1.233.252)"),
                    (p, 31, "(1.126.024)"),
                ),
                _mapped(
                    base,
                    1171,
                    "EXPENSE_INSURANCE",
                    (p, 32, "Chi về dịch vụ đại lý bảo hiểm"),
                    (p, 33, "(106.017)"),
                    (p, 34, "(473.808)"),
                ),
                _mapped(
                    base,
                    6024,
                    "EXPENSE_BROKERAGE_COMMISSION",
                    (p, 35, "Chi phí hoa hồng môi giới"),
                    (p, 36, "(129.255)"),
                    (p, 37, "(205.804)"),
                ),
                _mapped(
                    base,
                    1174,
                    "EXPENSE_OTHER",
                    (p, 38, "Chi dịch vụ khác"),
                    (p, 39, "(103.290)"),
                    (p, 40, "(73.409)"),
                ),
                _mapped(
                    base,
                    5989,
                    "NET_SERVICE_ACTIVITY",
                    (p, 8, "LÃI THUẦN TỪ HOẠT ĐỘNG DỊCH VỤ"),
                    (p, 41, "4.126.040"),
                    (p, 42, "1.769.868"),
                    topology="TRAILING_UNLABELED_NET_TOTAL",
                ),
            ],
            "LEADING_TOTALS_GENERIC_EXPENSE_PREPOSITION_UNLABELLED_TRAILING_NET",
        )
    )

    p = 58
    documents.append(
        _doc(
            base,
            "VCB",
            p,
            (p, 27, "Lãi thuần từ hoạt động dịch vụ"),
            [(p, 28, "2025"), (p, 29, "2024")],
            [(p, 30, "Triệu VND"), (p, 31, "Triệu VND")],
            [
                _mapped(
                    base,
                    1157,
                    "INCOME_PARENT",
                    (p, 32, "Thu nhập từ hoạt động dịch vụ"),
                    (p, 45, "11.854.532"),
                    (p, 46, "13.143.005"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _mapped(
                    base,
                    1158,
                    "INCOME_PAYMENT",
                    (p, 33, "Thu từ dịch vụ thanh toán"),
                    (p, 34, "7.662.079"),
                    (p, 35, "7.484.538"),
                ),
                _mapped(
                    base,
                    1159,
                    "INCOME_TREASURY",
                    (p, 36, "Thu từ dịch vụ ngân quỹ"),
                    (p, 37, "60.780"),
                    (p, 38, "52.334"),
                ),
                _mapped(
                    base,
                    1163,
                    "INCOME_TRUST_AGENCY",
                    (p, 39, "Thu từ nghiệp vụ ủy thác và đại lý"),
                    (p, 40, "42.761"),
                    (p, 41, "13.983"),
                ),
                _mapped(
                    base,
                    1166,
                    "INCOME_OTHER",
                    (p, 42, "Thu từ dịch vụ khác"),
                    (p, 43, "4.088.912"),
                    (p, 44, "5.592.150"),
                ),
                _mapped(
                    base,
                    1167,
                    "EXPENSE_PARENT",
                    (p, 47, "Chi phí hoạt động dịch vụ"),
                    (p, 65, "(8.384.665)"),
                    (p, 66, "(8.006.444)"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _mapped(
                    base,
                    1168,
                    "EXPENSE_PAYMENT",
                    (p, 49, "Chi cho dịch vụ thanh toán"),
                    (p, 50, "(5.942.823)"),
                    (p, 51, "(6.155.303)"),
                ),
                _mapped(
                    base,
                    1169,
                    "EXPENSE_TREASURY",
                    (p, 53, "Chi cho dịch vụ ngân quỹ"),
                    (p, 54, "(137.360)"),
                    (p, 55, "(141.478)"),
                ),
                _mapped(
                    base,
                    1173,
                    "EXPENSE_TELECOM",
                    (p, 56, "Chi cho dịch vụ viễn thông"),
                    (p, 57, "(185.917)"),
                    (p, 58, "(184.262)"),
                ),
                _mapped(
                    base,
                    1172,
                    "EXPENSE_TRUST_AGENCY",
                    (p, 59, "Chi cho nghiệp vụ ủy thác và đại lý"),
                    (p, 60, "(314)"),
                    (p, 61, "(21.910)"),
                ),
                _mapped(
                    base,
                    1174,
                    "EXPENSE_OTHER",
                    (p, 62, "Chi cho dịch vụ khác"),
                    (p, 63, "(2.118.251)"),
                    (p, 64, "(1.503.491)"),
                ),
                _mapped(
                    base,
                    5989,
                    "NET_SERVICE_ACTIVITY",
                    (p, 27, "Lãi thuần từ hoạt động dịch vụ"),
                    (p, 67, "3.469.867"),
                    (p, 68, "5.136.561"),
                    topology="TRAILING_UNLABELED_NET_TOTAL",
                ),
            ],
            "TRAILING_INCOME_AND_EXPENSE_TOTALS_UNLABELLED_TRAILING_NET",
        )
    )

    p = 58
    documents.append(
        _doc(
            base,
            "CTG",
            p,
            (p, 5, "LÃI THUẦN TỪ HOẠT ĐỘNG DỊCH VỤ"),
            [(p, 7, "31.12.2025"), (p, 8, "31.12.2024")],
            [(p, 9, "Triệu đồng"), (p, 10, "Triệu đồng")],
            [
                _mapped(
                    base,
                    1157,
                    "INCOME_PARENT",
                    (p, 11, "Thu nhập từ hoạt động dịch vụ"),
                    (p, 12, "12.351.055"),
                    (p, 13, "12.232.801"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _mapped(
                    base,
                    6021,
                    "INCOME_PAYMENT_TREASURY",
                    (p, 14, "Thu từ dịch vụ thanh toán và ngân quỹ"),
                    (p, 15, "4.385.529"),
                    (p, 16, "4.308.911"),
                ),
                _mapped(
                    base,
                    1164,
                    "INCOME_INSURANCE",
                    (p, 20, "Thu từ dịch vụ bảo hiểm"),
                    (p, 21, "3.966.517"),
                    (p, 22, "3.373.007"),
                ),
                _mapped(
                    base,
                    1166,
                    "INCOME_OTHER",
                    (p, 23, "Thu từ dịch vụ khác"),
                    (p, 24, "3.033.619"),
                    (p, 25, "3.589.470"),
                ),
                _mapped(
                    base,
                    1167,
                    "EXPENSE_PARENT",
                    (p, 26, "Chi phí hoạt động dịch vụ"),
                    (p, 27, "(6.022.104)"),
                    (p, 28, "(5.536.813)"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _mapped(
                    base,
                    6023,
                    "EXPENSE_PAYMENT_TREASURY",
                    (p, 29, "Chi về dịch vụ thanh toán và ngân quỹ"),
                    (p, 30, "(2.945.091)"),
                    (p, 31, "(3.096.956)"),
                ),
                _mapped(
                    base,
                    1171,
                    "EXPENSE_INSURANCE",
                    (p, 35, "Chi về dịch vụ bảo hiểm"),
                    (p, 36, "(1.961.041)"),
                    (p, 37, "(1.433.124)"),
                ),
                _mapped(
                    base,
                    1174,
                    "EXPENSE_OTHER",
                    (p, 38, "Chi về dịch vụ khác"),
                    (p, 39, "(806.214)"),
                    (p, 40, "(811.575)"),
                ),
                _mapped(
                    base,
                    5989,
                    "NET_SERVICE_ACTIVITY",
                    (p, 41, "Lãi thuần"),
                    (p, 42, "6.328.951"),
                    (p, 43, "6.695.988"),
                ),
            ],
            "LEADING_TOTALS_WITH_COMBINED_CONSULTING_TRUST_AGENCY_SOURCE_ROWS",
            source_only_rows=[
                _source_only(
                    base,
                    "SA-CTG-001",
                    "INCOME_COMBINED_CONSULTING_TRUST_AGENCY",
                    (p, 17, "Thu từ dịch vụ tư vấn, ủy thác và đại lý"),
                    (p, 18, "965.390"),
                    (p, 19, "961.413"),
                ),
                _source_only(
                    base,
                    "SA-CTG-002",
                    "EXPENSE_COMBINED_CONSULTING_TRUST_AGENCY",
                    (p, 32, "Chi về dịch vụ tư vấn, ủy thác và đại lý"),
                    (p, 33, "(309.758)"),
                    (p, 34, "(195.158)"),
                ),
            ],
        )
    )

    p = 55
    documents.append(
        _doc(
            base,
            "BID",
            p,
            (p, 24, "LÃI THUẦN TỪ HOẠT ĐỘNG DỊCH VỤ"),
            [(p, 26, "Năm nay"), (p, 25, "Năm trước")],
            [(p, 28, "Triệu VND"), (p, 29, "Triệu VND")],
            [
                _mapped(
                    base,
                    1157,
                    "INCOME_PARENT",
                    (p, 30, "Thu nhập từ hoạt động dịch vụ"),
                    (p, 31, "13.151.480"),
                    (p, 32, "13.465.588"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _mapped(
                    base,
                    1158,
                    "INCOME_PAYMENT",
                    (p, 33, "Hoạt động thanh toán"),
                    (p, 34, "3.765.217"),
                    (p, 35, "4.296.410"),
                ),
                _mapped(
                    base,
                    1159,
                    "INCOME_TREASURY",
                    (p, 36, "Hoạt động ngân quỹ"),
                    (p, 37, "198.968"),
                    (p, 38, "146.076"),
                ),
                _mapped(
                    base,
                    1163,
                    "INCOME_TRUST_AGENCY",
                    (p, 39, "Dịch vụ đại lý"),
                    (p, 40, "117.472"),
                    (p, 41, "84.779"),
                ),
                _mapped(
                    base,
                    1164,
                    "INCOME_INSURANCE",
                    (p, 42, "Hoạt động bảo hiểm"),
                    (p, 43, "4.439.813"),
                    (p, 44, "4.308.502"),
                ),
                _mapped(
                    base,
                    1166,
                    "INCOME_OTHER",
                    (p, 45, "Dịch vụ khác"),
                    (p, 46, "4.630.010"),
                    (p, 47, "4.629.821"),
                ),
                _mapped(
                    base,
                    1167,
                    "EXPENSE_PARENT",
                    (p, 48, "Chi phí hoạt động dịch vụ"),
                    (p, 49, "(6.227.252)"),
                    (p, 50, "(6.388.732)"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _mapped(
                    base,
                    1168,
                    "EXPENSE_PAYMENT",
                    (p, 51, "Hoạt động thanh toán"),
                    (p, 52, "(745.138)"),
                    (p, 53, "(1.093.745)"),
                ),
                _mapped(
                    base,
                    1169,
                    "EXPENSE_TREASURY",
                    (p, 54, "Hoạt động ngân quỹ"),
                    (p, 55, "(289.602)"),
                    (p, 56, "(231.163)"),
                ),
                _mapped(
                    base,
                    1173,
                    "EXPENSE_TELECOM",
                    (p, 57, "Bưu điện, viễn thông"),
                    (p, 58, "(211.685)"),
                    (p, 59, "(195.278)"),
                ),
                _mapped(
                    base,
                    1172,
                    "EXPENSE_TRUST_AGENCY",
                    (p, 60, "Dịch vụ đại lý"),
                    (p, 61, "(991)"),
                    (p, 62, "(873)"),
                ),
                _mapped(
                    base,
                    1171,
                    "EXPENSE_INSURANCE",
                    (p, 63, "Hoạt động bảo hiểm"),
                    (p, 64, "(2.573.876)"),
                    (p, 65, "(2.177.199)"),
                ),
                _mapped(
                    base,
                    1174,
                    "EXPENSE_OTHER",
                    (p, 66, "Dịch vụ khác"),
                    (p, 67, "(2.405.960)"),
                    (p, 68, "(2.690.474)"),
                ),
                _mapped(
                    base,
                    5989,
                    "NET_SERVICE_ACTIVITY",
                    (p, 69, "Lãi thuần từ hoạt động dịch vụ"),
                    (p, 70, "6.924.228"),
                    (p, 71, "7.076.856"),
                ),
            ],
            "LEADING_INCOME_AND_EXPENSE_TOTALS_LABELLED_TRAILING_NET",
        )
    )

    p = 50
    documents.append(
        _doc(
            base,
            "VIB",
            p,
            (p, 65, "LÃI THUẦN TỪ HOẠT ĐỘNG DỊCH VỤ"),
            [(p, 66, "2025"), (p, 67, "2024")],
            [(p, 68, "triệu đồng"), (p, 69, "triệu đồng")],
            [
                _mapped(
                    base,
                    1157,
                    "INCOME_PARENT",
                    (p, 70, "Thu nhập từ hoạt động dịch vụ"),
                    (p, 71, "4.200.762"),
                    (p, 72, "3.202.927"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _mapped(
                    base,
                    1158,
                    "INCOME_PAYMENT",
                    (p, 73, "Dịch vụ thanh toán"),
                    (p, 74, "2.875.794"),
                    (p, 75, "2.401.066"),
                ),
                _mapped(
                    base,
                    1164,
                    "INCOME_INSURANCE",
                    (p, 76, "Dịch vụ đại lý bảo hiểm"),
                    (p, 77, "993.178"),
                    (p, 78, "447.037"),
                ),
                _mapped(
                    base,
                    1166,
                    "INCOME_OTHER",
                    (p, 79, "Dịch vụ khác"),
                    (p, 80, "331.790"),
                    (p, 81, "354.824"),
                ),
                _mapped(
                    base,
                    1167,
                    "EXPENSE_PARENT",
                    (p, 84, "Chi phí hoạt động dịch vụ"),
                    (p, 82, "(2.095.421)"),
                    (p, 83, "(1.437.468)"),
                    topology="LEADING_PARENT_TOTAL_VALUE_BEFORE_PROVIDER_LABEL_ORDER",
                ),
                _mapped(
                    base,
                    1168,
                    "EXPENSE_PAYMENT",
                    (p, 85, "Dịch vụ thanh toán"),
                    (p, 86, "(1.513.742)"),
                    (p, 87, "(960.341)"),
                ),
                _mapped(
                    base,
                    1173,
                    "EXPENSE_TELECOM",
                    (p, 88, "Cước phí bưu điện về mạng viễn thông"),
                    (p, 89, "(84.787)"),
                    (p, 90, "(135.448)"),
                ),
                _mapped(
                    base,
                    1172,
                    "EXPENSE_TRUST_AGENCY",
                    (p, 91, "Dịch vụ ủy thác và đại lý"),
                    (p, 92, "(66.043)"),
                    (p, 93, "(48.853)"),
                ),
                _mapped(
                    base,
                    1171,
                    "EXPENSE_INSURANCE",
                    (p, 94, "Dịch vụ đại lý bảo hiểm"),
                    (p, 95, "(140.519)"),
                    (p, 96, "(56.682)"),
                ),
                _mapped(
                    base,
                    1170,
                    "EXPENSE_BROKERAGE",
                    (p, 97, "Dịch vụ môi giới"),
                    (p, 98, "(192.221)"),
                    (p, 99, "(176.270)"),
                ),
                _mapped(
                    base,
                    1174,
                    "EXPENSE_OTHER",
                    (p, 102, "Dịch vụ khác"),
                    (p, 100, "(98.109)"),
                    (p, 101, "(59.874)"),
                    topology="SAME_ROW_GEOMETRY_VALUE_BEFORE_PROVIDER_LABEL_ORDER",
                ),
                _mapped(
                    base,
                    5989,
                    "NET_SERVICE_ACTIVITY",
                    (p, 105, "Lãi thuần từ hoạt động dịch vụ"),
                    (p, 103, "2.105.341"),
                    (p, 104, "1.765.459"),
                    topology="SAME_ROW_GEOMETRY_VALUE_BEFORE_PROVIDER_LABEL_ORDER",
                ),
            ],
            "MIXED_PROVIDER_ORDER_LEADING_TOTALS_LABELLED_TRAILING_NET",
        )
    )
    return documents


def _annual_scan(base: ModuleType, semantic_index: Mapping[str, Any]) -> dict[str, Any]:
    matcher = _load_matcher()
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    trials = []
    for document in axis["documents"]:
        result = matcher.build_service_activity_variant_graph_document_v2(
            base.scanner._matcher_pages(document)
        )
        trials.append(
            {
                "document_provenance": document["document_provenance"],
                "matcher_result": result,
                "source_pdf_sha256": document["source_pdf"]["sha256"],
            }
        )
    material = {
        "format_version": "ANNUAL_2025_SERVICE_ACTIVITY_8DOCUMENT_STRUCTURE_SCAN_V1",
        "input_semantic_axis_sha256": axis["semantic_axis_sha256"],
        "state": "ANNUAL_2025_SERVICE_ACTIVITY_STRUCTURE_SCAN_COMPLETE",
        "trials": trials,
    }
    return {
        **material,
        "scan_id": "annual2025safdsv1:scan:" + canonical_json_sha256_v1(material),
    }


def _annual_metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    source_only = [row for trial in trials for row in trial["verified_source_only_rows"]]
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "authenticated_pixel_dash_zero_count": 0,
        "detailed_note_not_present_document_count": 0,
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            value["fresh_vietocr_numeric_status"] == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            for trial in trials
            for group in (trial["verified_mappings"], trial["verified_source_only_rows"])
            for row in group
            for value in row["values"]
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": len(source_only),
        "q1_source_period_caveat_document_count": 0,
        "source_only_value_cell_count": sum(len(row["values"]) for row in source_only),
        "verified_value_cell_count": sum(
            len(row["values"]) for trial in trials for row in trial["verified_mappings"]
        ),
    }


def _configure(base: ModuleType, scan_id: str) -> None:
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.REVIEW_RUN_ID = REVIEW_RUN_ID
    base.OPEN_SOURCE_TRIAL_STATUS = OPEN_SOURCE_TRIAL_STATUS
    base.ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = False
    base.CLAIM_BOUNDARY = CLAIM_BOUNDARY
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = scan_id
    base._REVIEW_SAFETY = dict(_REVIEW_SAFETY)
    base._AUTHORITY = dict(_AUTHORITY)
    base._SCHEMA_EXPECTED = dict(_SCHEMA_EXPECTED)
    base._review_documents = lambda: _review_documents(base)
    base._metrics = _annual_metrics
    base._source_period_status = lambda source_period: (
        "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        if source_period == "2025-12-31"
        else (_ for _ in ()).throw(_error("annual service-activity period drifted"))
    )


def _assert_result(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual service-activity exact metrics drifted")
    for trial, code in zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True):
        expected_status = OPEN_SOURCE_TRIAL_STATUS if code == "CTG" else "VERIFIED_BY_CODEX"
        mapped_ids = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        if (
            trial["document_provenance"] != code
            or trial["status"] != expected_status
            or trial["page_span"] != _EXPECTED_PAGES[code]
            or mapped_ids != _EXPECTED_REPORT_NORM_IDS[code]
            or len(trial["verified_accounting_equations"]) != 6
            or trial["source_period_status"]
            != "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        ):
            raise _error("annual service-activity trial closure drifted")
    ctg = next(trial for trial in value["trials"] if trial["document_provenance"] == "CTG")
    if [row["gap_id"] for row in ctg["verified_source_only_rows"]] != [
        "SA-CTG-001",
        "SA-CTG-002",
    ]:
        raise _error("annual service-activity CTG combined-row gaps drifted")
    return value


def _inputs() -> tuple[ModuleType, dict[str, Any], dict[str, Any], dict[str, Any]]:
    base = _load_base()
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, _ = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    scan = _annual_scan(base, semantic_index)
    if EXPECTED_SCAN_ID and scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("annual service-activity structure scan identity drifted")
    _configure(base, scan["scan_id"])
    return base, semantic_index, crop_manifest, scan


def build_annual_2025_service_activity_pixel_review_blueprint_v1() -> dict[str, Any]:
    base, _semantic_index, _crop_manifest, _scan = _inputs()
    return base._review_blueprint()


def build_live_annual_2025_service_activity_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    base, semantic_index, crop_manifest, scan = _inputs()
    review = base._review_blueprint()
    crop_sha = hashlib.sha256(canonical_json_bytes_v1(crop_manifest)).hexdigest()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    result = base.build_service_activity_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    replayed = base.validate_service_activity_8bank_codex_verified_mapping_replay_v1(
        result,
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    return _assert_result(replayed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or (REVIEW_PATH if args.write_review else RESULT_PATH)
    value = (
        build_annual_2025_service_activity_pixel_review_blueprint_v1()
        if args.write_review
        else build_live_annual_2025_service_activity_8bank_codex_verified_mapping_v1()
    )
    output.write_bytes(canonical_json_bytes_v1(value))
    if not args.write_review:
        print(value["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
