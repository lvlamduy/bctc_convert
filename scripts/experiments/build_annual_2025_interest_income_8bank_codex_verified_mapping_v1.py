"""Verify annual-2025 interest-income disclosures across eight banks."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_INTEREST_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_INTEREST_INCOME_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_INTEREST_INCOME_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025ii8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_INTEREST_INCOME_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025ii8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0134"
REVIEW_PATH = Path(
    "docs/experiments/E-0134-annual-2025-interest-income-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0134-annual-2025-interest-income-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "iifdsv1:scan:25adcbe29779a892faa54918bcdc5cf980003f2042726af62020a1a04034ff0e"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "BANK_BLIND_INTEREST_INCOME_GRAPH_VISIBLE_PDF_UPSTREAM_PPOCRV6_AND_BOUND_"
    "PIXEL_DASH_NUMERIC_CHALLENGER_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_"
    "ONLY_NO_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "optional_income_rows_required_in_every_bank": False,
    "reporting_period_dates_derived_from_pdf": True,
    "source_subtotals_and_children_double_counted": False,
    "visible_bound_dash_normalized_to_zero": True,
    "whole_pdf_uniqueness_replayed": True,
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
_SCHEMA_EXPECTED = {
    1142: (
        "II. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG KẾT QUẢ KINH DOANH",
        None,
        686,
    ),
    1143: ("Thu nhập lãi và các khoản thu nhập tương tự", 1142, 687),
    1144: ("Thu lãi tiền gửi", 1143, 688),
    1145: ("Thu lãi cho vay khách hàng", 1143, 689),
    6075: ("Thu nhập lãi cho vay khách hàng và các TCTD khác", 1143, 690),
    1146: ("Thu lãi từ kinh doanh, đầu tư chứng khoán", 1143, 691),
    1147: ("Thu nhập lãi cho thuê tài chính", 1143, 692),
    6076: ("Thu phí nghiệp vụ thư tín dụng (L/C)", 1143, 693),
    1148: ("Thu phí từ nghiệp vụ bảo lãnh", 1143, 694),
    1149: ("Thu nhập lãi từ nghiệp vụ mua bán nợ", 1143, 695),
    1150: ("Thu khác từ hoạt động tín dụng", 1143, 696),
}
_EXPECTED_IDS = {
    "ACB": {1143, 1144, 1145, 1146, 1147, 1148, 1150},
    "MBB": {1143, 1144, 1146, 1148, 1149, 1150, 6075},
    "VPB": {1143, 1144, 1145, 1146, 1148, 1149, 1150},
    "HDB": {1143, 1144, 1145, 1146, 1148, 1149, 1150, 6076},
    "VCB": {1143, 1144, 1145, 1146, 1147, 1148, 1150},
    "CTG": {1143, 1144, 1145, 1146, 1147, 1148, 1150},
    "BID": {1143, 1144, 1145, 1146, 1147, 1148, 1150},
    "VIB": {1143, 1144, 1145, 1146, 1148},
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 28,
    "document_count": 8,
    "document_unique_region_count": 8,
    "fresh_vietocr_numeric_disagreement_count": 0,
    "mapping_verified_count": 55,
    "open_source_row_count": 0,
    "q1_source_period_caveat_document_count": 0,
    "terminal_source_numeric_challenger_document_count": 0,
    "verified_value_cell_count": 110,
}


class Annual2025InterestIncome8BankError(ValueError):
    """Annual interest-income evidence, accounting, schema or replay drifted."""


def _error(message: str) -> Annual2025InterestIncome8BankError:
    return Annual2025InterestIncome8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_interest_income_8bank_codex_verified_mapping_v1.py"
    )
    spec = importlib.util.spec_from_file_location("annual_2025_interest_income_base", path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load interest-income support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ref(base: ModuleType, page: int, value: tuple[int, str] | Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is tuple:
        return base._value(page, value[0], value[1])
    return dict(value)


def _map(
    base: ModuleType,
    report_norm_id: int,
    role: str,
    page: int,
    label: tuple[int, str],
    current: tuple[int, str] | Mapping[str, Any],
    comparative: tuple[int, str] | Mapping[str, Any],
    *,
    topology: str = "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
) -> dict[str, Any]:
    return base._mapping(
        report_norm_id,
        role,
        base._label(page, label[0], label[1]),
        _ref(base, page, current),
        _ref(base, page, comparative),
        topology=topology,
    )


def _detail(
    base: ModuleType,
    page: int,
    name: str,
    current_terms: Sequence[tuple[int, str]],
    current_total: tuple[int, str],
    comparative_terms: Sequence[tuple[int, str]],
    comparative_total: tuple[int, str],
) -> dict[str, Any]:
    def value(item: tuple[int, str]) -> dict[str, Any]:
        return base._value(page, item[0], item[1])

    return base._detail_equation(
        name,
        [value(item) for item in current_terms],
        value(current_total),
        [value(item) for item in comparative_terms],
        value(comparative_total),
    )


def _doc(
    base: ModuleType,
    code: str,
    page: int,
    owner: tuple[int, str],
    periods: Sequence[tuple[int, str]],
    units: Sequence[tuple[int, str]],
    mappings: Sequence[dict[str, Any]],
    details: Sequence[dict[str, Any]] = (),
    *,
    presentation: str = "TRAILING_UNLABELED_PARENT_TOTAL",
) -> dict[str, Any]:
    return base._doc(
        code,
        page,
        owner[0],
        owner[1],
        [base._label(page, line, text) for line, text in periods],
        [base._label(page, line, text) for line, text in units],
        mappings,
        details,
        source_period="2025-12-31",
        presentation=presentation,
    )


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    documents = []

    page = 67
    documents.append(
        _doc(
            base,
            "ACB",
            page,
            (5, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
            [(6, "Năm 2025"), (7, "Năm 2024")],
            [(8, "Triệu VND"), (9, "Triệu VND")],
            [
                _map(
                    base,
                    1143,
                    "TOTAL_INTEREST_INCOME",
                    page,
                    (5, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
                    (34, "58.755.829"),
                    (35, "50.902.749"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _map(
                    base,
                    1144,
                    "DEPOSIT_INTEREST",
                    page,
                    (10, "Thu lãi tiền gửi"),
                    (11, "4.903.200"),
                    (12, "3.898.576"),
                ),
                _map(
                    base,
                    1145,
                    "CUSTOMER_LOAN_INTEREST",
                    page,
                    (13, "Thu lãi cho vay"),
                    (14, "46.685.953"),
                    (15, "42.297.000"),
                ),
                _map(
                    base,
                    1146,
                    "SECURITIES_INTEREST",
                    page,
                    (16, "Thu lãi từ kinh doanh, đầu tư chứng khoán nợ:"),
                    (17, "5.639.469"),
                    (18, "3.374.338"),
                ),
                _map(
                    base,
                    1148,
                    "GUARANTEE_FEE_INTEREST",
                    page,
                    (25, "Thu phí từ nghiệp vụ bảo lãnh"),
                    (26, "422.454"),
                    (27, "305.215"),
                ),
                _map(
                    base,
                    1147,
                    "FINANCE_LEASE_INTEREST",
                    page,
                    (28, "Thu lãi cho thuê tài chính"),
                    (29, "218.791"),
                    (30, "187.401"),
                ),
                _map(
                    base,
                    1150,
                    "OTHER_CREDIT_INCOME",
                    page,
                    (31, "Thu khác từ hoạt động tín dụng"),
                    (32, "885.962"),
                    (33, "840.219"),
                ),
            ],
            [
                _detail(
                    base,
                    page,
                    "SECURITIES_PARENT_EQUALS_TRADING_PLUS_INVESTMENT",
                    [(20, "19.265"), (23, "5.620.204")],
                    (17, "5.639.469"),
                    [(21, "246.817"), (24, "3.127.521")],
                    (18, "3.374.338"),
                )
            ],
        )
    )

    page = 72
    documents.append(
        _doc(
            base,
            "MBB",
            page,
            (15, "Thu nhập lãi và các khoản thu nhập tương tự"),
            [(11, "Năm 2025"), (12, "Năm 2024")],
            [(13, "triệu đồng"), (14, "triệu đồng")],
            [
                _map(
                    base,
                    1143,
                    "TOTAL_INTEREST_INCOME",
                    page,
                    (15, "Thu nhập lãi và các khoản thu nhập tương tự"),
                    (16, "89.088.116"),
                    (17, "69.061.893"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _map(
                    base,
                    1144,
                    "DEPOSIT_INTEREST",
                    page,
                    (18, "Thu nhập lãi tiền gửi"),
                    (19, "3.211.718"),
                    (20, "1.942.451"),
                ),
                _map(
                    base,
                    6075,
                    "CUSTOMER_AND_OTHER_CREDIT_INSTITUTION_LOAN_INTEREST",
                    page,
                    (21, "Thu nhập lãi cho vay khách hàng và các TCTD khác"),
                    (22, "70.324.550"),
                    (23, "54.446.408"),
                ),
                _map(
                    base,
                    1146,
                    "SECURITIES_INTEREST",
                    page,
                    (24, "Thu nhập lãi từ chứng khoán nợ"),
                    (25, "12.242.063"),
                    (26, "10.116.084"),
                ),
                _map(
                    base,
                    1149,
                    "PURCHASED_DEBT_INTEREST",
                    page,
                    (27, "Thu nhập lãi từ nghiệp vụ mua bán nợ"),
                    (28, "192.822"),
                    (29, "119.924"),
                ),
                _map(
                    base,
                    1148,
                    "GUARANTEE_FEE_INTEREST",
                    page,
                    (30, "Thu từ nghiệp vụ bảo lãnh"),
                    (31, "2.026.771"),
                    (32, "1.511.556"),
                ),
                _map(
                    base,
                    1150,
                    "OTHER_CREDIT_INCOME",
                    page,
                    (33, "Thu khác từ hoạt động tín dụng"),
                    (34, "1.090.192"),
                    (35, "925.470"),
                ),
            ],
            presentation="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
        )
    )

    page = 68
    documents.append(
        _doc(
            base,
            "VPB",
            page,
            (5, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
            [(6, "Năm 2025"), (7, "Năm 2024"), (8, "(Trình bày lại)")],
            [(9, "Triệu đồng"), (10, "Triệu đồng")],
            [
                _map(
                    base,
                    1143,
                    "TOTAL_INTEREST_INCOME",
                    page,
                    (5, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
                    (37, "101.258.954"),
                    (38, "81.033.640"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _map(
                    base,
                    1144,
                    "DEPOSIT_INTEREST",
                    page,
                    (11, "Thu nhập lãi tiền gửi"),
                    (12, "3.221.971"),
                    (13, "1.388.049"),
                ),
                _map(
                    base,
                    1145,
                    "CUSTOMER_LOAN_INTEREST",
                    page,
                    (15, "Thu nhập lãi cho vay"),
                    (16, "90.824.012"),
                    (17, "72.024.111"),
                ),
                _map(
                    base,
                    1146,
                    "SECURITIES_INTEREST",
                    page,
                    (18, "Thu lãi từ kinh doanh, đầu tư chứng khoán"),
                    (19, "3.395.551"),
                    (20, "4.033.498"),
                ),
                _map(
                    base,
                    1148,
                    "GUARANTEE_FEE_INTEREST",
                    page,
                    (27, "Thu từ nghiệp vụ bảo lãnh"),
                    (28, "480.810"),
                    (29, "272.195"),
                ),
                _map(
                    base,
                    1149,
                    "PURCHASED_DEBT_INTEREST",
                    page,
                    (31, "Thu nhập lãi từ nghiệp vụ mua nợ"),
                    (32, "85.102"),
                    (33, "93.528"),
                ),
                _map(
                    base,
                    1150,
                    "OTHER_CREDIT_INCOME",
                    page,
                    (34, "Thu khác từ hoạt động tín dụng"),
                    (35, "3.251.508"),
                    (36, "3.222.259"),
                ),
            ],
            [
                _detail(
                    base,
                    page,
                    "SECURITIES_PARENT_EQUALS_TRADING_PLUS_INVESTMENT",
                    [(22, "968.582"), (25, "2.426.969")],
                    (19, "3.395.551"),
                    [(23, "765.184"), (26, "3.268.314")],
                    (20, "4.033.498"),
                )
            ],
        )
    )

    page = 49
    hdb_comparative_purchased_debt_dash = base._dash(
        page,
        [1473, 1398, 1497, 1415],
        "5b9b1268d293cfd2980052f48a7a316adcdb778a5e029ce0aedbaa8f5c9125f5",
    )
    documents.append(
        _doc(
            base,
            "HDB",
            page,
            (52, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
            [(53, "Năm nay"), (54, "Năm trước")],
            [(55, "Triệu VND"), (56, "Triệu VND")],
            [
                _map(
                    base,
                    1143,
                    "TOTAL_INTEREST_INCOME",
                    page,
                    (52, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
                    (83, "67.992.416"),
                    (84, "57.995.528"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _map(
                    base,
                    1145,
                    "CUSTOMER_LOAN_INTEREST",
                    page,
                    (57, "Thu nhập lãi cho vay"),
                    (58, "48.091.197"),
                    (59, "42.802.465"),
                ),
                _map(
                    base,
                    1144,
                    "DEPOSIT_INTEREST",
                    page,
                    (60, "Thu nhập lãi từ tiền gửi"),
                    (61, "2.789.194"),
                    (62, "1.571.993"),
                ),
                _map(
                    base,
                    1146,
                    "SECURITIES_INTEREST",
                    page,
                    (63, "Thu lãi từ đầu tư chứng khoán Nợ"),
                    (64, "3.652.698"),
                    (65, "3.637.261"),
                ),
                _map(
                    base,
                    6076,
                    "LETTER_OF_CREDIT_FEE_INCOME",
                    page,
                    (72, "Thu phí nghiệp vụ L/C"),
                    (73, "1.623.794"),
                    (74, "3.123.610"),
                ),
                _map(
                    base,
                    1148,
                    "GUARANTEE_FEE_INTEREST",
                    page,
                    (75, "Thu phí từ nghiệp vụ bảo lãnh"),
                    (76, "285.527"),
                    (77, "129.299"),
                ),
                _map(
                    base,
                    1149,
                    "PURCHASED_DEBT_INTEREST",
                    page,
                    (78, "Thu lãi từ nghiệp vụ mua bán nợ"),
                    (79, "277.429"),
                    hdb_comparative_purchased_debt_dash,
                ),
                _map(
                    base,
                    1150,
                    "OTHER_CREDIT_INCOME",
                    page,
                    (80, "Thu khác từ hoạt động tín dụng"),
                    (81, "11.272.577"),
                    (82, "6.730.900"),
                ),
            ],
            [
                _detail(
                    base,
                    page,
                    "SECURITIES_PARENT_EQUALS_INVESTMENT_PLUS_TRADING",
                    [(67, "3.635.429"), (70, "17.269")],
                    (64, "3.652.698"),
                    [(68, "2.954.066"), (71, "683.195")],
                    (65, "3.637.261"),
                )
            ],
        )
    )

    page = 57
    documents.append(
        _doc(
            base,
            "VCB",
            page,
            (65, "Thu nhập lãi và các khoản thu nhập tương tự"),
            [(66, "2025"), (67, "2024")],
            [(68, "Triệu VND"), (69, "Triệu VND")],
            [
                _map(
                    base,
                    1143,
                    "TOTAL_INTEREST_INCOME",
                    page,
                    (65, "Thu nhập lãi và các khoản thu nhập tương tự"),
                    (94, "105.216.484"),
                    (95, "93.654.841"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _map(
                    base,
                    1145,
                    "CUSTOMER_LOAN_INTEREST",
                    page,
                    (70, "Thu nhập lãi từ cho vay khách hàng"),
                    (71, "86.623.782"),
                    (72, "78.644.966"),
                ),
                _map(
                    base,
                    1144,
                    "DEPOSIT_INTEREST",
                    page,
                    (73, "Thu nhập từ lãi tiền gửi"),
                    (74, "9.559.609"),
                    (75, "6.259.170"),
                ),
                _map(
                    base,
                    1146,
                    "SECURITIES_INTEREST",
                    page,
                    (76, "Thu nhập lãi từ kinh doanh, đầu tư chứng khoán nợ:"),
                    (77, "7.175.219"),
                    (78, "6.779.504"),
                ),
                _map(
                    base,
                    1147,
                    "FINANCE_LEASE_INTEREST",
                    page,
                    (85, "Thu nhập lãi cho thuê tài chính"),
                    (86, "547.426"),
                    (87, "508.012"),
                ),
                _map(
                    base,
                    1148,
                    "GUARANTEE_FEE_INTEREST",
                    page,
                    (88, "Thu phí từ nghiệp vụ bảo lãnh"),
                    (89, "629.012"),
                    (90, "448.407"),
                ),
                _map(
                    base,
                    1150,
                    "OTHER_CREDIT_INCOME",
                    page,
                    (91, "Thu khác từ hoạt động tín dụng"),
                    (92, "681.436"),
                    (93, "1.014.782"),
                ),
            ],
            [
                _detail(
                    base,
                    page,
                    "SECURITIES_PARENT_EQUALS_INVESTMENT_PLUS_TRADING",
                    [(80, "6.906.057"), (83, "269.162")],
                    (77, "7.175.219"),
                    [(81, "6.645.173"), (84, "134.331")],
                    (78, "6.779.504"),
                )
            ],
        )
    )

    page = 57
    documents.append(
        _doc(
            base,
            "CTG",
            page,
            (33, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
            [(34, "Năm tài chính kết thúc ngày"), (35, "31.12.2025"), (36, "31.12.2024")],
            [(37, "Triệu đồng"), (38, "Triệu đồng")],
            [
                _map(
                    base,
                    1143,
                    "TOTAL_INTEREST_INCOME",
                    page,
                    (33, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
                    (63, "143.142.328"),
                    (64, "124.460.685"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _map(
                    base,
                    1144,
                    "DEPOSIT_INTEREST",
                    page,
                    (39, "Thu nhập lãi tiền gửi"),
                    (40, "9.712.168"),
                    (41, "5.897.711"),
                ),
                _map(
                    base,
                    1145,
                    "CUSTOMER_LOAN_INTEREST",
                    page,
                    (42, "Thu nhập lãi cho vay"),
                    (43, "120.450.631"),
                    (44, "107.967.839"),
                ),
                _map(
                    base,
                    1146,
                    "SECURITIES_INTEREST",
                    page,
                    (45, "Thu lãi từ kinh doanh, đầu tư chứng khoán Nợ"),
                    (46, "8.909.530"),
                    (47, "7.116.454"),
                ),
                _map(
                    base,
                    1148,
                    "GUARANTEE_FEE_INTEREST",
                    page,
                    (54, "Thu phí từ nghiệp vụ bảo lãnh"),
                    (55, "1.813.595"),
                    (56, "1.827.000"),
                ),
                _map(
                    base,
                    1147,
                    "FINANCE_LEASE_INTEREST",
                    page,
                    (57, "Thu nhập lãi cho thuê tài chính"),
                    (58, "433.607"),
                    (59, "472.013"),
                ),
                _map(
                    base,
                    1150,
                    "OTHER_CREDIT_INCOME",
                    page,
                    (60, "Thu nhập khác từ hoạt động tín dụng"),
                    (61, "1.822.797"),
                    (62, "1.179.668"),
                ),
            ],
            [
                _detail(
                    base,
                    page,
                    "SECURITIES_PARENT_EQUALS_TRADING_PLUS_INVESTMENT",
                    [(49, "7.871"), (52, "8.901.659")],
                    (46, "8.909.530"),
                    [(50, "27.080"), (53, "7.089.374")],
                    (47, "7.116.454"),
                )
            ],
        )
    )

    page = 54
    documents.append(
        _doc(
            base,
            "BID",
            page,
            (69, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
            [(73, "Năm nay"), (70, "Năm trước"), (74, "(Trình bày lại)")],
            [(75, "Triệu VND"), (76, "Triệu VND")],
            [
                _map(
                    base,
                    1143,
                    "TOTAL_INTEREST_INCOME",
                    page,
                    (69, "THU NHẬP LÃI VÀ CÁC KHOẢN THU NHẬP TƯƠNG TỰ"),
                    (101, "154.992.934"),
                    (102, "138.283.813"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _map(
                    base,
                    1144,
                    "DEPOSIT_INTEREST",
                    page,
                    (77, "Thu nhập lãi tiền gửi"),
                    (78, "6.486.201"),
                    (79, "4.691.354"),
                ),
                _map(
                    base,
                    1145,
                    "CUSTOMER_LOAN_INTEREST",
                    page,
                    (80, "Thu nhập lãi cho vay khách hàng"),
                    (81, "132.545.677"),
                    (82, "120.238.625"),
                ),
                _map(
                    base,
                    1146,
                    "SECURITIES_INTEREST",
                    page,
                    (83, "Thu lãi từ kinh doanh, đầu tư chứng khoán Nợ"),
                    (84, "11.858.415"),
                    (85, "9.001.302"),
                ),
                _map(
                    base,
                    1148,
                    "GUARANTEE_FEE_INTEREST",
                    page,
                    (92, "Thu từ nghiệp vụ bảo lãnh"),
                    (93, "2.257.051"),
                    (94, "2.240.068"),
                ),
                _map(
                    base,
                    1147,
                    "FINANCE_LEASE_INTEREST",
                    page,
                    (95, "Thu nhập lãi cho thuê tài chính"),
                    (96, "454.765"),
                    (97, "381.721"),
                ),
                _map(
                    base,
                    1150,
                    "OTHER_CREDIT_INCOME",
                    page,
                    (98, "Thu khác từ hoạt động tín dụng"),
                    (99, "1.390.825"),
                    (100, "1.730.743"),
                ),
            ],
            [
                _detail(
                    base,
                    page,
                    "SECURITIES_PARENT_EQUALS_TRADING_PLUS_INVESTMENT",
                    [(87, "438.819"), (90, "11.419.596")],
                    (84, "11.858.415"),
                    [(88, "335.663"), (91, "8.665.639")],
                    (85, "9.001.302"),
                )
            ],
        )
    )

    page = 50
    documents.append(
        _doc(
            base,
            "VIB",
            page,
            (31, "Thu nhập lãi và các khoản thu nhập tương tự"),
            [(27, "2025"), (28, "2024")],
            [(29, "triệu đồng"), (30, "triệu đồng")],
            [
                _map(
                    base,
                    1143,
                    "TOTAL_INTEREST_INCOME",
                    page,
                    (31, "Thu nhập lãi và các khoản thu nhập tương tự"),
                    (32, "36.324.009"),
                    (33, "32.442.938"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _map(
                    base,
                    1144,
                    "DEPOSIT_INTEREST",
                    page,
                    (34, "Thu nhập lãi tiền gửi"),
                    (35, "1.789.305"),
                    (36, "1.090.191"),
                ),
                _map(
                    base,
                    1145,
                    "CUSTOMER_LOAN_INTEREST",
                    page,
                    (37, "Thu nhập lãi cho vay"),
                    (38, "31.721.288"),
                    (39, "28.688.072"),
                ),
                _map(
                    base,
                    1146,
                    "SECURITIES_INTEREST",
                    page,
                    (40, "Thu lãi từ kinh doanh, đầu tư chứng khoán"),
                    (41, "2.727.112"),
                    (42, "2.616.090"),
                ),
                _map(
                    base,
                    1148,
                    "GUARANTEE_FEE_INTEREST",
                    page,
                    (43, "Thu phí từ nghiệp vụ bảo lãnh"),
                    (44, "86.304"),
                    (45, "48.585"),
                ),
            ],
            presentation="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
        )
    )
    return documents


def _configure(base: ModuleType) -> None:
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.REVIEW_RUN_ID = REVIEW_RUN_ID
    base.FAMILY_END_DISPLAY_ORDER = 696
    base.CLAIM_BOUNDARY = CLAIM_BOUNDARY
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base._REVIEW_SAFETY = dict(_REVIEW_SAFETY)
    base._AUTHORITY = dict(_AUTHORITY)
    base._SCHEMA_EXPECTED = dict(_SCHEMA_EXPECTED)
    base._review_documents = lambda: _review_documents(base)
    base._source_period_status = lambda source_period: (
        "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        if source_period == "2025-12-31"
        else (_ for _ in ()).throw(_error("annual interest-income period drifted"))
    )


def _assert_result(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual interest-income result metrics drifted")
    dash_values = []
    for trial in value.get("trials", []):
        actual = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        if actual != _EXPECTED_IDS[trial["document_provenance"]]:
            raise _error("annual interest-income mapped schema set drifted")
        if trial["source_period_status"] != (
            "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        ):
            raise _error("annual interest-income source period status drifted")
        dash_values.extend(
            cell
            for mapping in trial["verified_mappings"]
            for cell in mapping["values"]
            if cell["fresh_vietocr_numeric_status"] == "NO_VIETOCR_LINE_FOR_VISIBLE_DASH"
        )
    if len(dash_values) != 1 or dash_values[0]["normalized_value"] != 0:
        raise _error("annual interest-income authenticated dash denominator drifted")
    return value


def build_annual_2025_interest_income_pixel_review_blueprint_v1() -> dict[str, Any]:
    base = _load_base()
    _configure(base)
    return base._review_blueprint()


def build_live_annual_2025_interest_income_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    base = _load_base()
    _configure(base)
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review = base._review_blueprint()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    scan = base.scanner.build_interest_income_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    result = base.build_interest_income_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    replayed = base.validate_interest_income_8bank_codex_verified_mapping_replay_v1(
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
    if args.write_review:
        value = build_annual_2025_interest_income_pixel_review_blueprint_v1()
    else:
        value = build_live_annual_2025_interest_income_8bank_codex_verified_mapping_v1()
        print(value["result_id"])
    output.write_bytes(canonical_json_bytes_v1(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
