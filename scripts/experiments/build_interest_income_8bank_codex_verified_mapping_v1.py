"""Verify interest-income disclosures across the fixed eight reports.

The whole-document graph locates one unique region in every report without
bank/page routing.  This stage binds visible labels, the fresh VietOCR semantic
proposal, the independent PaddleOCR/source numeric challenger, two accounting
periods, local monetary units, exact subtotal equations and the live TM schema.
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

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
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


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


foundation = _load_module(
    "government_nhnn_support_for_interest_income",
    "build_government_nhnn_liabilities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "interest_income_scan_for_verified_mapping",
    "scan_interest_income_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "INTEREST_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "INTEREST_INCOME_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_INTEREST_"
    "INCOME_GRAPH_VISIBLE_PDF_LABEL_PADDLEOCR_SOURCE_NUMERIC_CHALLENGER_"
    "PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_CANONICALIZATION_"
    "EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0079-interest-income-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0079-interest-income-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "iifdsv1:scan:04759af3c6fc86368c37a8616102d96ff0bab94dd5bef5a9abc178cabad5eb20"

_SCHEMA_EXPECTED = {
    1142: (
        "II. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG KẾT QUẢ KINH DOANH",
        None,
        681,
    ),
    1143: ("Thu nhập lãi và các khoản thu nhập tương tự", 1142, 682),
    1144: ("Thu lãi tiền gửi", 1143, 683),
    1145: ("Thu lãi cho vay khách hàng", 1143, 684),
    1146: ("Thu lãi từ kinh doanh, đầu tư chứng khoán", 1143, 685),
    1147: ("Thu nhập lãi cho thuê tài chính", 1143, 686),
    1148: ("Thu phí từ nghiệp vụ bảo lãnh", 1143, 687),
    1149: ("Thu nhập lãi từ nghiệp vụ mua bán nợ", 1143, 688),
    1150: ("Thu khác từ hoạt động tín dụng", 1143, 689),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_interest_income_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_numeric_challenger_and_accounting_closure_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "vietocr_numeric_disagreement_is_retained_not_silently_repaired": True,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "optional_income_rows_required_in_every_bank": False,
    "paddleocr_source_axis_used_as_semantic_anchor": False,
    "source_subtotals_and_children_double_counted": False,
    "vietocr_used_as_numeric_truth": False,
    "whole_pdf_uniqueness_replayed": True,
}
_RESULT_FIELDS = {
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


class InterestIncome8BankCodexVerifiedMappingV1Error(ValueError):
    """The fixed structure, pixel, numeric, equation or schema evidence drifted."""


def _error(message: str) -> InterestIncome8BankCodexVerifiedMappingV1Error:
    return InterestIncome8BankCodexVerifiedMappingV1Error(message)


def _label(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _value(page: int, line: int, text: str, multiplier: int = 1) -> dict[str, Any]:
    return {
        "line_index": line,
        "multiplier": multiplier,
        "page_sequence": page,
        "pixel_transcription": text,
    }


def _mapping(
    report_norm_id: int,
    role: str,
    label: dict[str, Any],
    current: dict[str, Any],
    comparative: dict[str, Any],
    *,
    topology: str = "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
) -> dict[str, Any]:
    return {
        "label": label,
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {"COMPARATIVE_PERIOD": comparative, "CURRENT_PERIOD": current},
    }


def _detail_equation(
    name: str,
    current_terms: Sequence[dict[str, Any]],
    current_total: dict[str, Any],
    comparative_terms: Sequence[dict[str, Any]],
    comparative_total: dict[str, Any],
) -> dict[str, Any]:
    return {
        "COMPARATIVE_PERIOD": {"terms": list(comparative_terms), "total": comparative_total},
        "CURRENT_PERIOD": {"terms": list(current_terms), "total": current_total},
        "name": name,
    }


def _doc(
    code: str,
    page: int,
    owner_line: int,
    owner_text: str,
    period_axis: Sequence[dict[str, Any]],
    units: Sequence[dict[str, Any]],
    mappings: Sequence[dict[str, Any]],
    details: Sequence[dict[str, Any]] = (),
    *,
    source_period: str = "2026-06-30",
    presentation: str = "TRAILING_UNLABELED_PARENT_TOTAL",
) -> dict[str, Any]:
    return {
        "bank_code": code,
        "detail_equations": list(details),
        "mappings": list(mappings),
        "owner": _label(page, owner_line, owner_text),
        "page_span": [page, page],
        "period_axis": list(period_axis),
        "presentation": presentation,
        "source_period": source_period,
        "unit_evidence": list(units),
    }


def _review_documents() -> list[dict[str, Any]]:
    p = 24
    acb = _doc(
        "ACB",
        p,
        6,
        "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ",
        [_label(p, 9, "30.6.2026"), _label(p, 10, "30.6.2025")],
        [_label(p, 11, "Triệu đồng"), _label(p, 12, "Triệu đồng")],
        [
            _mapping(
                1143,
                "TOTAL_INTEREST_INCOME",
                _label(p, 6, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
                _value(p, 37, "37.300.500"),
                _value(p, 38, "27.626.001"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1144,
                "DEPOSIT_INTEREST",
                _label(p, 13, "Thu lãi tiền gửi"),
                _value(p, 14, "3.221.424"),
                _value(p, 15, "2.311.759"),
            ),
            _mapping(
                1145,
                "CUSTOMER_LOAN_INTEREST",
                _label(p, 16, "Thu lãi cho vay"),
                _value(p, 17, "29.319.165"),
                _value(p, 18, "21.997.501"),
            ),
            _mapping(
                1146,
                "SECURITIES_INTEREST",
                _label(p, 19, "Thu lãi từ kinh doanh, đầu tư chứng khoán nợ"),
                _value(p, 20, "3.848.256"),
                _value(p, 21, "2.551.480"),
            ),
            _mapping(
                1148,
                "GUARANTEE_FEE_INTEREST",
                _label(p, 28, "Thu phí từ nghiệp vụ bảo lãnh"),
                _value(p, 29, "261.625"),
                _value(p, 30, "198.814"),
            ),
            _mapping(
                1147,
                "FINANCE_LEASE_INTEREST",
                _label(p, 31, "Thu lãi cho thuê tài chính"),
                _value(p, 32, "133.914"),
                _value(p, 33, "103.701"),
            ),
            _mapping(
                1150,
                "OTHER_CREDIT_INCOME",
                _label(p, 34, "Thu khác từ hoạt động tín dụng"),
                _value(p, 35, "516.116"),
                _value(p, 36, "462.746"),
            ),
        ],
        [
            _detail_equation(
                "SECURITIES_PARENT_EQUALS_TRADING_PLUS_INVESTMENT",
                [_value(p, 23, "42.539"), _value(p, 26, "3.805.717")],
                _value(p, 20, "3.848.256"),
                [_value(p, 24, "3.350"), _value(p, 27, "2.548.130")],
                _value(p, 21, "2.551.480"),
            )
        ],
    )

    p = 46
    mbb = _doc(
        "MBB",
        p,
        10,
        "Thu nhập lãi và các khoản thu nhập tương tự",
        [
            _label(p, 4, "Từ 01/01/2026"),
            _label(p, 6, "đến 30/06/2026"),
            _label(p, 5, "Từ 01/01/2025"),
            _label(p, 7, "đến 30/06/2025"),
        ],
        [_label(p, 8, "Triệu đồng"), _label(p, 9, "Triệu đồng")],
        [
            _mapping(
                1143,
                "TOTAL_INTEREST_INCOME",
                _label(p, 10, "Thu nhập lãi và các khoản thu nhập tương tự"),
                _value(p, 29, "62.988.909"),
                _value(p, 30, "40.689.438"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1144,
                "DEPOSIT_INTEREST",
                _label(p, 11, "Thu nhập lãi tiền gửi"),
                _value(p, 12, "3.578.772"),
                _value(p, 13, "1.064.315"),
            ),
            _mapping(
                1145,
                "CUSTOMER_LOAN_INTEREST",
                _label(p, 14, "Thu nhập lãi cho vay"),
                _value(p, 15, "49.763.911"),
                _value(p, 16, "31.875.381"),
            ),
            _mapping(
                1146,
                "SECURITIES_INTEREST",
                _label(p, 17, "Thu lãi từ đầu tư chứng khoán nợ"),
                _value(p, 18, "7.542.929"),
                _value(p, 19, "6.093.026"),
            ),
            _mapping(
                1148,
                "GUARANTEE_FEE_INTEREST",
                _label(p, 20, "Thu phí từ nghiệp vụ bảo lãnh"),
                _value(p, 21, "1.271.984"),
                _value(p, 22, "928.736"),
            ),
            _mapping(
                1149,
                "PURCHASED_DEBT_INTEREST",
                _label(p, 23, "Thu lãi từ nghiệp vụ mua bán nợ"),
                _value(p, 24, "118.517"),
                _value(p, 25, "73.816"),
            ),
            _mapping(
                1150,
                "OTHER_CREDIT_INCOME",
                _label(p, 26, "Thu các hoạt động tín dụng khác"),
                _value(p, 27, "712.796"),
                _value(p, 28, "654.164"),
            ),
        ],
    )

    p = 62
    vpb = _doc(
        "VPB",
        p,
        5,
        "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ",
        [
            _label(p, 8, "3 tháng kết thúc"),
            _label(p, 10, "ngày 31 tháng 3"),
            _label(p, 12, "năm 2026"),
            _label(p, 9, "3 tháng kết thúc"),
            _label(p, 11, "ngày 31 tháng 3"),
            _label(p, 13, "năm 2025"),
        ],
        [_label(p, 15, "Triệu đồng"), _label(p, 16, "Triệu đồng")],
        [
            _mapping(
                1143,
                "TOTAL_INTEREST_INCOME",
                _label(p, 5, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
                _value(p, 41, "31.549.594"),
                _value(p, 42, "22.211.069"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1144,
                "DEPOSIT_INTEREST",
                _label(p, 17, "Thu nhập lãi tiền gửi"),
                _value(p, 18, "1.233.322"),
                _value(p, 19, "756.144"),
            ),
            _mapping(
                1145,
                "CUSTOMER_LOAN_INTEREST",
                _label(p, 20, "Thu nhập lãi cho vay"),
                _value(p, 21, "28.113.425"),
                _value(p, 22, "20.200.701"),
            ),
            _mapping(
                1146,
                "SECURITIES_INTEREST",
                _label(p, 23, "Thu lãi từ kinh doanh, đầu tư chứng khoán"),
                _value(p, 24, "1.133.562"),
                _value(p, 25, "506.822"),
            ),
            _mapping(
                1148,
                "GUARANTEE_FEE_INTEREST",
                _label(p, 32, "Thu từ nghiệp vụ bảo lãnh"),
                _value(p, 33, "129.505"),
                _value(p, 34, "76.190"),
            ),
            _mapping(
                1149,
                "PURCHASED_DEBT_INTEREST",
                _label(p, 35, "Thu nhập lãi từ nghiệp vụ mua nợ"),
                _value(p, 36, "26.828"),
                _value(p, 37, "21.381"),
            ),
            _mapping(
                1150,
                "OTHER_CREDIT_INCOME",
                _label(p, 38, "Thu khác từ hoạt động tín dụng"),
                _value(p, 39, "912.952"),
                _value(p, 40, "649.831"),
            ),
        ],
        [
            _detail_equation(
                "SECURITIES_PARENT_EQUALS_TRADING_PLUS_INVESTMENT",
                [_value(p, 27, "534.608"), _value(p, 30, "598.954")],
                _value(p, 24, "1.133.562"),
                [_value(p, 28, "130.292"), _value(p, 31, "376.530")],
                _value(p, 25, "506.822"),
            )
        ],
        source_period="2026-03-31",
    )

    p = 34
    hdb = _doc(
        "HDB",
        p,
        40,
        "Thu nhập lãi và các khoản thu nhập tương tự",
        [_label(p, 42, "Kỳ này"), _label(p, 43, "Kỳ trước")],
        [_label(p, 44, "Triệu VND"), _label(p, 45, "Triệu VND")],
        [
            _mapping(
                1143,
                "TOTAL_INTEREST_INCOME",
                _label(p, 40, "Thu nhập lãi và các khoản thu nhập tương tự"),
                _value(p, 71, "43.585.120"),
                _value(p, 72, "32.981.425"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1144,
                "DEPOSIT_INTEREST",
                _label(p, 46, "Thu nhập lãi tiền gửi"),
                _value(p, 47, "2.660.461"),
                _value(p, 48, "1.085.005"),
            ),
            _mapping(
                1145,
                "CUSTOMER_LOAN_INTEREST",
                _label(p, 50, "Thu nhập lãi cho vay"),
                _value(p, 51, "29.786.363"),
                _value(p, 52, "22.826.744"),
            ),
            _mapping(
                1146,
                "SECURITIES_INTEREST",
                _label(p, 53, "Thu lãi từ kinh doanh, đầu tư chứng khoán nợ"),
                _value(p, 54, "2.818.929"),
                _value(p, 55, "1.599.433"),
            ),
            _mapping(
                1148,
                "GUARANTEE_FEE_INTEREST",
                _label(p, 62, "Thu phí từ nghiệp vụ bảo lãnh"),
                _value(p, 63, "113.977"),
                _value(p, 64, "110.772"),
            ),
            _mapping(
                1149,
                "PURCHASED_DEBT_INTEREST",
                _label(p, 65, "Thu lãi từ nghiệp vụ mua bán nợ"),
                _value(p, 66, "886.327"),
                _value(p, 67, "9"),
            ),
            _mapping(
                1150,
                "OTHER_CREDIT_INCOME",
                _label(p, 68, "Thu khác từ hoạt động tín dụng"),
                _value(p, 69, "7.319.063"),
                _value(p, 70, "7.359.462"),
            ),
        ],
        [
            _detail_equation(
                "SECURITIES_PARENT_EQUALS_INVESTMENT_PLUS_TRADING",
                [_value(p, 57, "2.818.548"), _value(p, 60, "381")],
                _value(p, 54, "2.818.929"),
                [_value(p, 58, "1.581.527"), _value(p, 61, "17.906")],
                _value(p, 55, "1.599.433"),
            )
        ],
    )

    p = 38
    vcb = _doc(
        "VCB",
        p,
        37,
        "Thu nhập lãi và các khoản thu nhập tương tự",
        [
            _label(p, 40, "từ 1/1/2026"),
            _label(p, 42, "đến 30/6/2026"),
            _label(p, 41, "từ 1/1/2025"),
            _label(p, 43, "đến 30/6/2025"),
        ],
        [_label(p, 45, "Triệu VND"), _label(p, 46, "Triệu VND")],
        [
            _mapping(
                1143,
                "TOTAL_INTEREST_INCOME",
                _label(p, 37, "Thu nhập lãi và các khoản thu nhập tương tự"),
                _value(p, 73, "68.564.743"),
                _value(p, 74, "49.792.403"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1145,
                "CUSTOMER_LOAN_INTEREST",
                _label(p, 47, "Thu nhập lãi cho vay khách hàng"),
                _value(p, 48, "57.547.257"),
                _value(p, 49, "40.729.173"),
            ),
            _mapping(
                1144,
                "DEPOSIT_INTEREST",
                _label(p, 50, "Thu nhập lãi tiền gửi"),
                _value(p, 51, "6.388.648"),
                _value(p, 52, "4.611.448"),
            ),
            _mapping(
                1146,
                "SECURITIES_INTEREST",
                _label(p, 53, "Thu nhập lãi từ kinh doanh, đầu tư chứng khoán nợ"),
                _value(p, 54, "3.540.451"),
                _value(p, 55, "3.480.157"),
            ),
            _mapping(
                1147,
                "FINANCE_LEASE_INTEREST",
                _label(p, 62, "Thu từ cho thuê tài chính"),
                _value(p, 63, "341.970"),
                _value(p, 64, "265.637"),
            ),
            _mapping(
                1148,
                "GUARANTEE_FEE_INTEREST",
                _label(p, 65, "Thu phí từ nghiệp vụ bảo lãnh"),
                _value(p, 66, "477.330"),
                _value(p, 67, "316.238"),
            ),
            _mapping(
                1150,
                "OTHER_CREDIT_INCOME",
                _label(p, 68, "Thu khác từ hoạt động tín dụng"),
                _value(p, 69, "269.087"),
                _value(p, 70, "389.750"),
            ),
        ],
        [
            _detail_equation(
                "SECURITIES_PARENT_EQUALS_INVESTMENT_PLUS_TRADING",
                [_value(p, 57, "3.425.442"), _value(p, 60, "115.009")],
                _value(p, 54, "3.540.451"),
                [_value(p, 58, "3.389.621"), _value(p, 61, "90.536")],
                _value(p, 55, "3.480.157"),
            )
        ],
    )

    p = 45
    ctg = _doc(
        "CTG",
        p,
        6,
        "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ",
        [
            _label(p, 9, "từ 01/01/2026 đến"),
            _label(p, 11, "hết 30/06/2026"),
            _label(p, 10, "từ 01/01/2025 đến"),
            _label(p, 12, "hết 30/06/2025"),
        ],
        [_label(p, 13, "triệu đồng"), _label(p, 14, "triệu đồng")],
        [
            _mapping(
                1143,
                "TOTAL_INTEREST_INCOME",
                _label(p, 6, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
                _value(p, 39, "88.591.342"),
                _value(p, 40, "67.560.615"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1144,
                "DEPOSIT_INTEREST",
                _label(p, 15, "Thu nhập lãi tiền gửi"),
                _value(p, 16, "6.542.683"),
                _value(p, 17, "4.339.491"),
            ),
            _mapping(
                1145,
                "CUSTOMER_LOAN_INTEREST",
                _label(p, 18, "Thu nhập lãi cho vay khách hàng"),
                _value(p, 19, "74.729.778"),
                _value(p, 20, "56.853.480"),
            ),
            _mapping(
                1146,
                "SECURITIES_INTEREST",
                _label(p, 21, "Thu lãi từ kinh doanh, đầu tư chứng khoán nợ"),
                _value(p, 22, "4.764.510"),
                _value(p, 23, "4.425.211"),
            ),
            _mapping(
                1148,
                "GUARANTEE_FEE_INTEREST",
                _label(p, 30, "Thu phí từ nghiệp vụ bảo lãnh"),
                _value(p, 31, "1.303.862"),
                _value(p, 32, "921.231"),
            ),
            _mapping(
                1147,
                "FINANCE_LEASE_INTEREST",
                _label(p, 33, "Thu nhập lãi cho thuê tài chính"),
                _value(p, 34, "263.846"),
                _value(p, 35, "210.656"),
            ),
            _mapping(
                1150,
                "OTHER_CREDIT_INCOME",
                _label(p, 36, "Thu khác từ hoạt động tín dụng"),
                _value(p, 37, "986.663"),
                _value(p, 38, "810.546"),
            ),
        ],
        [
            _detail_equation(
                "SECURITIES_PARENT_EQUALS_TRADING_PLUS_INVESTMENT",
                [_value(p, 25, "28.219"), _value(p, 28, "4.736.291")],
                _value(p, 22, "4.764.510"),
                [_value(p, 26, "2.525"), _value(p, 29, "4.422.686")],
                _value(p, 23, "4.425.211"),
            )
        ],
    )

    p = 28
    bid = _doc(
        "BID",
        p,
        59,
        "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ",
        [
            _label(p, 60, "Từ 01/01/2026 đến"),
            _label(p, 62, "30/06/2026"),
            _label(p, 61, "Từ 01/01/2025 đến"),
            _label(p, 63, "30/06/2025"),
        ],
        [_label(p, 58, "Đơn vị: Triệu VND")],
        [
            _mapping(
                1143,
                "TOTAL_INTEREST_INCOME",
                _label(p, 59, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
                _value(p, 88, "92,619,993"),
                _value(p, 89, "72,813,400"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1144,
                "DEPOSIT_INTEREST",
                _label(p, 64, "Thu nhập lãi tiền gửi"),
                _value(p, 65, "4,461,808"),
                _value(p, 66, "2,995,111"),
            ),
            _mapping(
                1145,
                "CUSTOMER_LOAN_INTEREST",
                _label(p, 67, "Thu nhập lãi cho vay khách hàng"),
                _value(p, 68, "79,469,774"),
                _value(p, 69, "62,790,795"),
            ),
            _mapping(
                1146,
                "SECURITIES_INTEREST",
                _label(p, 70, "Thu lãi từ kinh doanh, đầu tư chứng khoán nợ"),
                _value(p, 71, "6,479,082"),
                _value(p, 72, "4,973,626"),
            ),
            _mapping(
                1148,
                "GUARANTEE_FEE_INTEREST",
                _label(p, 79, "Thu phí từ nghiệp vụ bảo lãnh"),
                _value(p, 80, "1,254,775"),
                _value(p, 81, "1,123,354"),
            ),
            _mapping(
                1147,
                "FINANCE_LEASE_INTEREST",
                _label(p, 82, "Thu nhập lãi cho thuê tài chính"),
                _value(p, 83, "310,724"),
                _value(p, 84, "215,278"),
            ),
            _mapping(
                1150,
                "OTHER_CREDIT_INCOME",
                _label(p, 85, "Thu khác từ hoạt động tín dụng"),
                _value(p, 86, "643,830"),
                _value(p, 87, "715,236"),
            ),
        ],
        [
            _detail_equation(
                "SECURITIES_PARENT_EQUALS_TRADING_PLUS_INVESTMENT",
                [_value(p, 74, "633,993"), _value(p, 77, "5,845,089")],
                _value(p, 71, "6,479,082"),
                [_value(p, 75, "126,852"), _value(p, 78, "4,846,774")],
                _value(p, 72, "4,973,626"),
            )
        ],
    )

    p = 45
    vib = _doc(
        "VIB",
        p,
        33,
        "Thu nhập lãi và các khoản thu nhập tương tự",
        [
            _label(p, 27, "6 tháng đầu"),
            _label(p, 29, "năm 2026"),
            _label(p, 28, "6 tháng đầu"),
            _label(p, 30, "năm 2025"),
        ],
        [_label(p, 31, "triệu đồng"), _label(p, 32, "triệu đồng")],
        [
            _mapping(
                1143,
                "TOTAL_INTEREST_INCOME",
                _label(p, 33, "Thu nhập lãi và các khoản thu nhập tương tự"),
                _value(p, 34, "21.983.358"),
                _value(p, 35, "17.094.586"),
                topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
            ),
            _mapping(
                1144,
                "DEPOSIT_INTEREST",
                _label(p, 36, "Thu nhập lãi tiền gửi"),
                _value(p, 37, "1.293.978"),
                _value(p, 38, "759.027"),
            ),
            _mapping(
                1145,
                "CUSTOMER_LOAN_INTEREST",
                _label(p, 39, "Thu nhập lãi cho vay"),
                _value(p, 40, "19.113.488"),
                _value(p, 41, "14.940.553"),
            ),
            _mapping(
                1146,
                "SECURITIES_INTEREST",
                _label(p, 42, "Thu lãi từ kinh doanh, đầu tư chứng khoán"),
                _value(p, 43, "1.510.903"),
                _value(p, 44, "1.357.506"),
            ),
            _mapping(
                1148,
                "GUARANTEE_FEE_INTEREST",
                _label(p, 45, "Thu phí từ nghiệp vụ bảo lãnh"),
                _value(p, 46, "64.989"),
                _value(p, 47, "37.500"),
            ),
        ],
        presentation="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
    )
    return [acb, mbb, vpb, hdb, vcb, ctg, bid, vib]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "reviewer": {"kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW", "review_run_id": "E-0079"},
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0079:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex interest-income pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    if type(items) is not list:
        raise _error(f"{label} document axis drifted")
    matches = [
        item
        for item in items
        if type(item) is dict and item.get("document_provenance", item.get("bank_code")) == code
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one exact document {code}")
    return matches[0]


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    return foundation._page(document, page_sequence, label)


def _semantic_evidence(
    axis_page: Mapping[str, Any], semantic_page: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any]:
    line_index = item["line_index"]
    axis_line = foundation.support._axis_line(axis_page, line_index)
    semantic_line = semantic_page["lines"][line_index]
    if (
        semantic_line.get("source_line_index") != line_index
        or semantic_line.get("vietocr_text") != axis_line["vietocr_text"]
        or type(item["pixel_transcription"]) is not str
    ):
        raise _error("semantic/pixel evidence axis drifted")
    return {
        "crop_ref": canonical_clone_v1(semantic_line["crop_ref"]),
        "fresh_vietocr_proposal": axis_line["vietocr_text"],
        "line_index": line_index,
        "normalized_fresh_vietocr": normalize_vietnamese_anchor_v1(axis_line["vietocr_text"]),
        "normalized_pixel_transcription": normalize_vietnamese_anchor_v1(
            item["pixel_transcription"]
        ),
        "pixel_transcription": item["pixel_transcription"],
        "source_bbox_raw_pixels": list(axis_line["bbox"]),
    }


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


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            value["fresh_vietocr_numeric_status"] == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "terminal_source_numeric_challenger_document_count": sum(
            trial["source_geometry_mode"]
            == "TERMINAL_EXPERIMENT_LOCAL_PROVIDER_LINE_GEOMETRY_ONLY_V1"
            for trial in trials
        ),
        "verified_value_cell_count": sum(
            len(mapping["values"]) for trial in trials for mapping in trial["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("interest-income result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "INTEREST_INCOME_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("interest-income result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status")
            not in {"VERIFIED_BY_CODEX", "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"}
            or any(
                mapping.get("status") != "VERIFIED_BY_CODEX"
                for mapping in trial.get("verified_mappings", [])
            )
        ):
            raise _error("interest-income trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0079:result:" + canonical_json_sha256_v1(material):
        raise _error("interest-income result identity drifted")
    return canonical_clone_v1(value)


def build_interest_income_8bank_codex_verified_mapping_v1(
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
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or structure_scan.get("state") != "FULL_DOCUMENT_INTEREST_INCOME_STRUCTURE_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("fixed semantic axis, crop manifest, or structure scan drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(reviewed_documents, code, "pixel review")
        scan_trial = _document(structure_scan["trials"], code, "structure scan")
        axis_document = _document(axis["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        matcher = scan_trial["matcher_result"]
        if not same_typed_json_v1(
            matcher["uniqueness"], {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        ) or not same_typed_json_v1(matcher["regions"][0]["page_span"], reviewed["page_span"]):
            raise _error("reviewed region is not the unique whole-PDF interest-income graph")
        page_number = reviewed["page_span"][0]
        axis_page = _page(axis_document, page_number, "accounting axis")
        semantic_page = _page(semantic_document, page_number, "semantic index")
        crop_page = _page(crop_document, page_number, "crop manifest")
        source_texts = foundation.support._source_line_axis(crop_page)
        value_cache: dict[str, dict[str, Any]] = {}

        def verified(
            ref: Mapping[str, Any],
            *,
            value_cache: dict[str, dict[str, Any]] = value_cache,
            axis_page: Mapping[str, Any] = axis_page,
            semantic_page: Mapping[str, Any] = semantic_page,
            crop_page: Mapping[str, Any] = crop_page,
            source_texts: Sequence[str] = source_texts,
        ) -> dict[str, Any]:
            key = canonical_json_sha256_v1(ref)
            if key not in value_cache:
                evidence = foundation.support._source_value(
                    axis_page,
                    semantic_page,
                    crop_page,
                    source_texts,
                    {
                        "line_index": ref["line_index"],
                        "pixel_transcription": ref["pixel_transcription"],
                    },
                )
                try:
                    proposal_value = foundation.support._money(
                        evidence["fresh_vietocr_numeric_proposal"]
                    )
                except ValueError:
                    proposal_value = None
                value_cache[key] = {
                    **evidence,
                    "fresh_vietocr_numeric_status": (
                        "MATCHES_SOURCE_NUMERIC_CHALLENGER"
                        if proposal_value == evidence["normalized_value"]
                        else "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
                    ),
                    "page_sequence": ref["page_sequence"],
                }
            return canonical_clone_v1(value_cache[key])

        verified_mappings = []
        by_id: dict[int, dict[str, Any]] = {}
        for mapping in reviewed["mappings"]:
            label = _semantic_evidence(axis_page, semantic_page, mapping["label"])
            values = [
                {"axis_role": axis_role, **verified(ref)}
                for axis_role, ref in mapping["values"].items()
            ]
            result_mapping = {
                "label_evidence": label,
                "role": mapping["role"],
                "schema_binding": _schema_binding(
                    schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                ),
                "status": "VERIFIED_BY_CODEX",
                "topology": mapping["topology"],
                "values": values,
            }
            verified_mappings.append(result_mapping)
            by_id[mapping["report_norm_id"]] = result_mapping
        parent = by_id[1143]
        children = [mapping for rid, mapping in by_id.items() if rid != 1143]
        equations = []
        for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
            terms = [
                next(value for value in mapping["values"] if value["axis_role"] == axis_role)
                for mapping in children
            ]
            total = next(value for value in parent["values"] if value["axis_role"] == axis_role)
            computed = sum(term["normalized_value"] for term in terms)
            if computed != total["normalized_value"]:
                raise _error(
                    f"interest-income parent equation does not close for {code}/{axis_role}"
                )
            equations.append(
                {
                    "axis_role": axis_role,
                    "computed_value": computed,
                    "name": "PARENT_TOTAL_EQUALS_DIRECT_VISIBLE_CHILDREN",
                    "status": "VERIFIED_EXACT",
                    "term_report_norm_ids": [
                        mapping["schema_binding"]["report_norm_id"] for mapping in children
                    ],
                    "visible_total": total["normalized_value"],
                }
            )
        for detail in reviewed["detail_equations"]:
            for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
                equation = detail[axis_role]
                terms = [verified(ref) for ref in equation["terms"]]
                total = verified(equation["total"])
                computed = sum(term["normalized_value"] for term in terms)
                if computed != total["normalized_value"]:
                    raise _error(
                        f"interest-income detail equation does not close: {detail['name']}"
                    )
                equations.append(
                    {
                        "axis_role": axis_role,
                        "computed_value": computed,
                        "name": detail["name"],
                        "status": "VERIFIED_EXACT",
                        "term_source_line_indices": [term["source_line_index"] for term in terms],
                        "visible_total": total["normalized_value"],
                        "visible_total_source_line_index": total["source_line_index"],
                    }
                )
        source_period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        trials.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "owner_evidence": _semantic_evidence(axis_page, semantic_page, reviewed["owner"]),
                "page_span": reviewed["page_span"],
                "period_axis_evidence": [
                    _semantic_evidence(axis_page, semantic_page, item)
                    for item in reviewed["period_axis"]
                ],
                "presentation": reviewed["presentation"],
                "source_geometry_mode": semantic_page["geometry_mode"],
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "status": (
                    "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
                    if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                    else "VERIFIED_BY_CODEX"
                ),
                "structure_graph_id": matcher["result_id"],
                "unit_evidence": [
                    _semantic_evidence(axis_page, semantic_page, item)
                    for item in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
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
            "family_end_display_order": 689,
            "family_root": _schema_binding(schema_by_id.get(1143), 1143),
            "mapped_report_norm_ids": sorted(
                {
                    mapping["schema_binding"]["report_norm_id"]
                    for trial in trials
                    for mapping in trial["verified_mappings"]
                }
            ),
            "section_root": _schema_binding(schema_by_id.get(1142), 1142),
        },
        "state": "INTEREST_INCOME_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0079:result:" + canonical_json_sha256_v1(material)}
    )


def validate_interest_income_8bank_codex_verified_mapping_replay_v1(
    value: Any,
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
    supplied = _validate_result(value)
    rebuilt = build_interest_income_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_manifest_sha256,
        review_sha256=review_sha256,
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("interest-income verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = foundation.support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = foundation.support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def build_live_interest_income_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_interest_income_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_interest_income_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_interest_income_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_interest_income_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_interest_income_8bank_codex_verified_mapping_replay_v1(
        value,
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


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
        _write(RESULT_PATH, build_live_interest_income_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_interest_income_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
