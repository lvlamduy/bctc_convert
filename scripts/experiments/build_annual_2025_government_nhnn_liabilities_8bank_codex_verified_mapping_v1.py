"""Verify annual-2025 Government/SBV liabilities across eight banks.

The complete-PDF graph locates one region per report without routing on bank,
page, note number or filename.  The page/line coordinates below are the fixed
post-selection evidence ledger.  Rows whose visible dash or exact schema leaf
is not authenticated remain explicit ``UNRESOLVED`` evidence.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1, canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_GOVERNMENT_NHNN_LIABILITIES_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_GOVERNMENT_NHNN_LIABILITIES_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_GOVERNMENT_NHNN_LIABILITIES_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025gn8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_GOVERNMENT_NHNN_LIABILITIES_CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025gn8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0128"
REVIEW_PATH = Path(
    "docs/experiments/E-0128-annual-2025-government-nhnn-liabilities-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0128-annual-2025-government-nhnn-liabilities-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "gnlfdsv1:scan:f9ec664962fd3ef21b580ccf5052ce10c345b19b5fc895b170dfd197b766a1af"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "BANK_BLIND_GOVERNMENT_NHNN_LIABILITY_VARIANT_GRAPH_VISIBLE_PDF_PIXEL_"
    "UPSTREAM_PPOCRV6_NUMERIC_AXIS_PERIOD_UNIT_PARENT_CHILD_CURRENCY_TENOR_"
    "AND_ACCOUNTING_ONLY_UNMAPPED_OR_UNBOUND_DASH_ROWS_RETAINED_NO_EXPORT_AUTHORITY"
)
_REVIEW_CHECKS = (
    "COMPLETE_PDF_UNIQUE_REGION",
    "OWNER_CHILD_SIBLING_AND_OPTIONAL_BRANCH_TOPOLOGY",
    "AGGREGATE_LOAN_TREASURY_CURRENCY_TENOR_REPO_VARIANTS",
    "CURRENT_2025_AND_COMPARATIVE_2024_SNAPSHOT_AXES",
    "VISIBLE_LOCAL_MILLION_VND_UNIT",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "UPSTREAM_PPOCRV6_NUMERIC_CHALLENGER",
    "OPTIONAL_CHILDREN_NOT_REQUIRED_FOR_REGION_LOCATION",
    "PARENT_CHILD_AND_FAMILY_TOTAL_ACCOUNTING",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
    "UNMAPPED_OR_UNBOUND_DASH_ROWS_RETAINED_WITHOUT_FORCED_EQUIVALENCE",
)
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_PPOCRV6_AND_ACCOUNTING",
    "reporting_period_dates_derived_from_pdf": True,
    "source_rows_without_equivalent_schema_forced_into_nearest_item": False,
    "unbound_visible_dash_promoted_to_zero": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_other_report_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "independent_pdf_pixel_and_upstream_ppocrv6_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_government_nhnn_liability_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reporting_period_dates_derived_from_pdf": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_retained": True,
}
_EXPECTED_IDS = {
    "ACB": {1024, 1027, 1035, 1036, 6070},
    "MBB": {1024, 1035, 6070},
    "VPB": {1024, 1033, 1035, 1036, 6070},
    "HDB": {1024, 1039},
    "VCB": {1024, 1025, 1033, 1035, 1036, 1037, 6070},
    "CTG": {1024, 1025, 1026, 1033, 1035, 1036, 6070},
    "BID": {1024, 1025, 1026, 1035, 1036, 1037, 6070, 6071, 6072},
    "VIB": {1024, 1026, 6070},
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 43,
    "annual_source_period_document_count": 8,
    "confirmed_bound_report_absence_count": 0,
    "document_count": 8,
    "document_unique_region_count": 8,
    "mapping_verified_count": 41,
    "open_source_row_count": 8,
    "verified_value_cell_count": 85,
}


class Annual2025GovernmentNHNNLiabilities8BankError(ValueError):
    """Annual Government/SBV evidence, accounting, schema or replay drifted."""


def _error(message: str) -> Annual2025GovernmentNHNNLiabilities8BankError:
    return Annual2025GovernmentNHNNLiabilities8BankError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual Government/SBV support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _open_row(
    base: ModuleType,
    item_id: str,
    page: int,
    label_line: int,
    label_text: str,
    current: Sequence[tuple[int, str]],
    comparative: Sequence[tuple[int, str]],
    reason: str,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "label": base._label(page, label_line, label_text),
        "reason": reason,
        "status": "UNRESOLVED",
        "values": {
            "COMPARATIVE": [base._line(page, line, text) for line, text in comparative],
            "CURRENT": [base._line(page, line, text) for line, text in current],
        },
    }


def _doc(
    base: ModuleType,
    code: str,
    page: int,
    owner_line: int,
    owner_text: str,
    period_lines: Sequence[tuple[int, str]],
    unit_lines: Sequence[tuple[int, str]],
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[dict[str, Any]],
    unresolved: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    return base._doc(
        code,
        page,
        owner_line,
        owner_text,
        [base._label(page, line, text) for line, text in period_lines],
        [base._label(page, line, text) for line, text in unit_lines],
        mappings,
        equations,
        unresolved,
        source_period="2025-12-31",
        unit_authority="VISIBLE_LOCAL_MILLION_VND_CURRENT_2025_AND_COMPARATIVE_2024",
    )


def _acb(base: ModuleType) -> dict[str, Any]:
    d, r, e = base._direct, base._line, base._equation
    mappings = [
        d(
            1024,
            "FAMILY_TOTAL",
            60,
            58,
            "Tổng các khoản nợ Chính phủ và Ngân hàng Nhà nước",
            r(60, 59, "32.976.139"),
            r(60, 60, "7.954.853"),
            "VISIBLE_LABELED_TOTAL",
        ),
        d(
            6070,
            "CENTRAL_BANK_LOAN",
            60,
            48,
            "Vay Ngân hàng nhà nước",
            r(60, 50, "31.152.220"),
            r(60, 51, "7.948.357"),
        ),
        d(
            1027,
            "PLEDGED_SECURITIES_LOAN",
            60,
            49,
            "Vay cầm cố các giấy tờ có giá",
            r(60, 50, "31.152.220"),
            r(60, 51, "7.948.357"),
        ),
        d(
            1035,
            "TREASURY_PAYMENT_DEPOSIT",
            60,
            52,
            "Tiền gửi của Kho bạc Nhà nước",
            r(60, 54, "18.758"),
            r(60, 55, "6.496"),
        ),
        d(
            1036,
            "TREASURY_PAYMENT_DEPOSIT_VND",
            60,
            53,
            "Tiền gửi không kỳ hạn bằng Đồng Việt Nam",
            r(60, 54, "18.758"),
            r(60, 55, "6.496"),
        ),
    ]
    equations = [
        e(
            "PLEDGED_LOAN_EQUALS_CENTRAL_BANK_LOAN",
            "CURRENT",
            [r(60, 50, "31.152.220")],
            r(60, 50, "31.152.220"),
        ),
        e(
            "PLEDGED_LOAN_EQUALS_CENTRAL_BANK_LOAN",
            "COMPARATIVE",
            [r(60, 51, "7.948.357")],
            r(60, 51, "7.948.357"),
        ),
        e(
            "VND_CHILD_EQUALS_TREASURY_DEPOSIT",
            "CURRENT",
            [r(60, 54, "18.758")],
            r(60, 54, "18.758"),
        ),
        e(
            "VND_CHILD_EQUALS_TREASURY_DEPOSIT",
            "COMPARATIVE",
            [r(60, 55, "6.496")],
            r(60, 55, "6.496"),
        ),
        e(
            "LOAN_TREASURY_REPO_TO_FAMILY_TOTAL",
            "CURRENT",
            [r(60, 50, "31.152.220"), r(60, 54, "18.758"), r(60, 57, "1.805.161")],
            r(60, 59, "32.976.139"),
        ),
        e(
            "NONZERO_LOAN_AND_TREASURY_TO_FAMILY_TOTAL",
            "COMPARATIVE",
            [r(60, 51, "7.948.357"), r(60, 55, "6.496")],
            r(60, 60, "7.954.853"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-GN-001",
            60,
            56,
            "Giao dịch bán và mua lại trái phiếu Chính phủ với KBNN",
            [(57, "1.805.161")],
            [],
            "The comparative cell is a visible dash, but no authenticated numeric-line bbox binds that dash; the repo row remains open rather than silently treating a blank axis as zero.",
        ),
    ]
    return _doc(
        base,
        "ACB",
        60,
        43,
        "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC",
        [(44, "31.12.2025"), (45, "31.12.2024")],
        [(46, "Triệu VND"), (47, "Triệu VND")],
        mappings,
        equations,
        unresolved,
    )


def _mbb(base: ModuleType) -> dict[str, Any]:
    d, r, e = base._direct, base._line, base._equation
    mappings = [
        d(
            1024,
            "FAMILY_TOTAL",
            63,
            48,
            "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC",
            r(63, 63, "47.474.800"),
            r(63, 64, "8.156.285"),
            "UNLABELED_TOTAL_AFTER_CHILDREN",
        ),
        d(
            6070,
            "CENTRAL_BANK_LOAN",
            63,
            59,
            "Các khoản nợ NHNNVN",
            r(63, 60, "47.433.567"),
            r(63, 61, "8.078.823"),
        ),
        d(
            1035,
            "TREASURY_DEPOSIT",
            63,
            56,
            "Tiền gửi của Kho bạc Nhà nước",
            r(63, 57, "41.233"),
            r(63, 58, "77.462"),
        ),
    ]
    equations = [
        e(
            "LOAN_PLUS_TREASURY_TO_FAMILY_TOTAL",
            "CURRENT",
            [r(63, 60, "47.433.567"), r(63, 57, "41.233")],
            r(63, 63, "47.474.800"),
        ),
        e(
            "LOAN_PLUS_TREASURY_TO_FAMILY_TOTAL",
            "COMPARATIVE",
            [r(63, 61, "8.078.823"), r(63, 58, "77.462")],
            r(63, 64, "8.156.285"),
        ),
    ]
    return _doc(
        base,
        "MBB",
        63,
        48,
        "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC",
        [(50, "31/12/2025"), (51, "31/12/2024")],
        [(53, "triệu đồng"), (54, "triệu đồng")],
        mappings,
        equations,
        [],
    )


def _vpb(base: ModuleType) -> dict[str, Any]:
    d, r, e = base._direct, base._line, base._equation
    mappings = [
        d(
            1024,
            "FAMILY_TOTAL",
            58,
            33,
            "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
            r(58, 52, "15.305"),
            r(58, 53, "5.713"),
            "UNLABELED_TOTAL_AFTER_CHILDREN",
        ),
        d(
            6070,
            "CENTRAL_BANK_LOAN",
            58,
            40,
            "Vay Ngân hàng Nhà nước Việt Nam",
            r(58, 41, "1.752"),
            r(58, 42, "3.360"),
        ),
        d(1033, "OTHER_LOAN", 58, 43, "Vay khác", r(58, 44, "1.752"), r(58, 45, "3.360")),
        d(
            1035,
            "TREASURY_DEPOSIT",
            58,
            46,
            "Tiền gửi của Kho bạc Nhà nước",
            r(58, 47, "13.553"),
            r(58, 48, "2.353"),
        ),
        d(
            1036,
            "TREASURY_DEPOSIT_VND",
            58,
            49,
            "Tiền gửi của Kho bạc nhà nước bằng VND",
            r(58, 50, "13.553"),
            r(58, 51, "2.353"),
        ),
    ]
    equations = [
        e(
            "OTHER_LOAN_EQUALS_CENTRAL_BANK_LOAN",
            "CURRENT",
            [r(58, 44, "1.752")],
            r(58, 41, "1.752"),
        ),
        e(
            "OTHER_LOAN_EQUALS_CENTRAL_BANK_LOAN",
            "COMPARATIVE",
            [r(58, 45, "3.360")],
            r(58, 42, "3.360"),
        ),
        e(
            "VND_CHILD_EQUALS_TREASURY_DEPOSIT",
            "CURRENT",
            [r(58, 50, "13.553")],
            r(58, 47, "13.553"),
        ),
        e(
            "VND_CHILD_EQUALS_TREASURY_DEPOSIT",
            "COMPARATIVE",
            [r(58, 51, "2.353")],
            r(58, 48, "2.353"),
        ),
        e(
            "LOAN_PLUS_TREASURY_TO_FAMILY_TOTAL",
            "CURRENT",
            [r(58, 41, "1.752"), r(58, 47, "13.553")],
            r(58, 52, "15.305"),
        ),
        e(
            "LOAN_PLUS_TREASURY_TO_FAMILY_TOTAL",
            "COMPARATIVE",
            [r(58, 42, "3.360"), r(58, 48, "2.353")],
            r(58, 53, "5.713"),
        ),
    ]
    return _doc(
        base,
        "VPB",
        58,
        33,
        "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
        [(34, "Ngày 31 tháng 12"), (36, "năm 2025"), (35, "Ngày 31 tháng 12"), (37, "năm 2024")],
        [(38, "Triệu đồng"), (39, "Triệu đồng")],
        mappings,
        equations,
        [],
    )


def _hdb(base: ModuleType) -> dict[str, Any]:
    d, r, e = base._direct, base._line, base._equation
    mappings = [
        d(
            1024,
            "FAMILY_TOTAL",
            44,
            31,
            "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN",
            r(44, 51, "11.425.972"),
            r(44, 52, "15.434"),
            "UNLABELED_TOTAL_AFTER_CHILDREN",
        ),
        d(
            1039,
            "OTHER_LIABILITY",
            44,
            42,
            "Các khoản nợ khác",
            r(44, 43, "7.727"),
            r(44, 44, "15.433"),
        ),
    ]
    equations = [
        e(
            "OTHER_LIABILITY_CHILDREN_TO_PARENT",
            "CURRENT",
            [r(44, 46, "2.752"), r(44, 49, "4.975")],
            r(44, 43, "7.727"),
        ),
        e(
            "OTHER_LIABILITY_CHILDREN_TO_PARENT",
            "COMPARATIVE",
            [r(44, 47, "8.377"), r(44, 50, "7.056")],
            r(44, 44, "15.433"),
        ),
        e(
            "NONZERO_LOAN_TREASURY_OTHER_TO_FAMILY_TOTAL",
            "CURRENT",
            [r(44, 39, "11.418.077"), r(44, 37, "168"), r(44, 43, "7.727")],
            r(44, 51, "11.425.972"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-GN-002",
            44,
            38,
            "Vay NHNN",
            [(39, "11.418.077")],
            [],
            "The comparative cell is a visible dash without a bound numeric-line bbox; retain the broad central-bank loan row until the dash geometry is authenticated.",
        ),
        _open_row(
            base,
            "A2025-GN-003",
            44,
            40,
            "Vay chiết khấu các giấy tờ có giá",
            [(41, "11.418.077")],
            [],
            "The comparative cell is a visible dash without a bound numeric-line bbox; the exact 1026 mapping remains open.",
        ),
        _open_row(
            base,
            "A2025-GN-004",
            44,
            36,
            "Tiền gửi của Kho bạc Nhà nước",
            [(37, "168")],
            [],
            "The comparative value 1 is visible in the PDF but missing from the authenticated line axis, so the Treasury row is not promoted from a one-sided value.",
        ),
    ]
    return _doc(
        base,
        "HDB",
        44,
        31,
        "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN",
        [(32, "Số cuối năm"), (33, "Số đầu năm")],
        [(34, "Triệu VND"), (35, "Triệu VND")],
        mappings,
        equations,
        unresolved,
    )


def _vcb(base: ModuleType) -> dict[str, Any]:
    m, d, r, label, e = base._mapping, base._direct, base._line, base._label, base._equation
    mappings = [
        d(
            1024,
            "FAMILY_TOTAL",
            52,
            26,
            "Các khoản nợ Chính phủ và Ngân hàng Nhà nước",
            r(52, 56, "160.128.325"),
            r(52, 57, "78.237.337"),
            "UNLABELED_TOTAL_AFTER_CHILDREN",
        ),
        d(
            6070,
            "CENTRAL_BANK_LOAN",
            52,
            32,
            "Vay Ngân hàng nhà nước",
            r(52, 33, "24.127.159"),
            r(52, 34, "587.278"),
        ),
        d(
            1025,
            "CREDIT_FILE_LOAN",
            52,
            35,
            "Vay theo hồ sơ tín dụng",
            r(52, 36, "355.322"),
            r(52, 37, "535.580"),
        ),
        d(1033, "OTHER_LOAN", 52, 40, "Vay khác", r(52, 41, "22.905"), r(52, 42, "51.698")),
        d(
            1035,
            "TREASURY_DEPOSIT",
            52,
            44,
            "Tiền gửi của Kho bạc Nhà nước",
            r(52, 45, "136.001.166"),
            r(52, 46, "77.650.059"),
        ),
        m(
            1036,
            "TREASURY_DEPOSIT_VND",
            [
                label(52, 47, "Tiền gửi không kỳ hạn bằng VND"),
                label(52, 53, "Tiền gửi có kỳ hạn bằng VND"),
            ],
            [r(52, 48, "490.536"), r(52, 54, "134.625.000")],
            [r(52, 49, "412.215"), r(52, 55, "76.665.000")],
            "SUM_OF_VND_TREASURY_DEPOSIT_ROWS",
        ),
        d(
            1037,
            "TREASURY_DEPOSIT_FOREIGN_CURRENCY",
            52,
            50,
            "Tiền gửi không kỳ hạn bằng ngoại tệ",
            r(52, 51, "885.630"),
            r(52, 52, "572.844"),
        ),
    ]
    equations = [
        e(
            "LOAN_CHILDREN_TO_CENTRAL_BANK_LOAN",
            "CURRENT",
            [r(52, 36, "355.322"), r(52, 39, "23.748.932"), r(52, 41, "22.905")],
            r(52, 33, "24.127.159"),
        ),
        e(
            "NONZERO_LOAN_CHILDREN_TO_CENTRAL_BANK_LOAN",
            "COMPARATIVE",
            [r(52, 37, "535.580"), r(52, 42, "51.698")],
            r(52, 34, "587.278"),
        ),
        e(
            "TREASURY_CURRENCY_ROWS_TO_PARENT",
            "CURRENT",
            [r(52, 48, "490.536"), r(52, 54, "134.625.000"), r(52, 51, "885.630")],
            r(52, 45, "136.001.166"),
        ),
        e(
            "TREASURY_CURRENCY_ROWS_TO_PARENT",
            "COMPARATIVE",
            [r(52, 49, "412.215"), r(52, 55, "76.665.000"), r(52, 52, "572.844")],
            r(52, 46, "77.650.059"),
        ),
        e(
            "LOAN_PLUS_TREASURY_TO_FAMILY_TOTAL",
            "CURRENT",
            [r(52, 33, "24.127.159"), r(52, 45, "136.001.166")],
            r(52, 56, "160.128.325"),
        ),
        e(
            "LOAN_PLUS_TREASURY_TO_FAMILY_TOTAL",
            "COMPARATIVE",
            [r(52, 34, "587.278"), r(52, 46, "77.650.059")],
            r(52, 57, "78.237.337"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-GN-005",
            52,
            38,
            "Vay cầm cố GTCG",
            [(39, "23.748.932")],
            [],
            "The comparative cell is a visible dash without an authenticated numeric-line bbox; ReportNormId 1027 remains open for this row.",
        )
    ]
    return _doc(
        base,
        "VCB",
        52,
        26,
        "Các khoản nợ Chính phủ và Ngân hàng Nhà nước",
        [(28, "31/12/2025"), (29, "31/12/2024")],
        [(30, "Triệu VND"), (31, "Triệu VND")],
        mappings,
        equations,
        unresolved,
    )


def _ctg(base: ModuleType) -> dict[str, Any]:
    m, d, r, label, e = base._mapping, base._direct, base._line, base._label, base._equation
    mappings = [
        m(
            1024,
            "FAMILY_TOTAL",
            [label(51, 5, "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC VIỆT NAM")],
            [r(51, 28, "141.627.156"), r(51, 32, "2.965.201")],
            [r(51, 29, "154.284.104")],
            "CONTROLLED_SUM_OF_PRINTED_SUBTOTAL_AND_OPTIONAL_REPO",
        ),
        d(
            6070,
            "CENTRAL_BANK_LOAN",
            51,
            10,
            "Các khoản vay từ NHNN",
            r(51, 11, "7.001.815"),
            r(51, 12, "9.512.869"),
        ),
        d(
            1026,
            "DISCOUNT_LOAN",
            51,
            13,
            "Vay chiết khấu các giấy tờ có giá",
            r(51, 14, "6.695.302"),
            r(51, 15, "9.017.858"),
        ),
        d(
            1025,
            "CREDIT_FILE_LOAN",
            51,
            16,
            "Vay theo hồ sơ tín dụng",
            r(51, 17, "299.555"),
            r(51, 18, "488.053"),
        ),
        d(
            1033,
            "OTHER_LOAN",
            51,
            19,
            "Vay hỗ trợ các doanh nghiệp Nhà nước",
            r(51, 20, "6.958"),
            r(51, 21, "6.958"),
        ),
        d(
            1035,
            "TREASURY_DEPOSIT",
            51,
            22,
            "Tiền gửi của Kho bạc Nhà nước",
            r(51, 23, "134.625.341"),
            r(51, 24, "144.771.235"),
        ),
        d(
            1036,
            "TREASURY_DEPOSIT_VND",
            51,
            25,
            "Bằng VND",
            r(51, 26, "134.625.341"),
            r(51, 27, "144.771.235"),
        ),
    ]
    equations = [
        e(
            "LOAN_CHILDREN_TO_CENTRAL_BANK_LOAN",
            "CURRENT",
            [r(51, 14, "6.695.302"), r(51, 17, "299.555"), r(51, 20, "6.958")],
            r(51, 11, "7.001.815"),
        ),
        e(
            "LOAN_CHILDREN_TO_CENTRAL_BANK_LOAN",
            "COMPARATIVE",
            [r(51, 15, "9.017.858"), r(51, 18, "488.053"), r(51, 21, "6.958")],
            r(51, 12, "9.512.869"),
        ),
        e(
            "VND_CHILD_EQUALS_TREASURY_DEPOSIT",
            "CURRENT",
            [r(51, 26, "134.625.341")],
            r(51, 23, "134.625.341"),
        ),
        e(
            "VND_CHILD_EQUALS_TREASURY_DEPOSIT",
            "COMPARATIVE",
            [r(51, 27, "144.771.235")],
            r(51, 24, "144.771.235"),
        ),
        e(
            "LOAN_PLUS_TREASURY_TO_PRINTED_SUBTOTAL",
            "CURRENT",
            [r(51, 11, "7.001.815"), r(51, 23, "134.625.341")],
            r(51, 28, "141.627.156"),
        ),
        e(
            "LOAN_PLUS_TREASURY_TO_PRINTED_SUBTOTAL",
            "COMPARATIVE",
            [r(51, 12, "9.512.869"), r(51, 24, "144.771.235")],
            r(51, 29, "154.284.104"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-GN-006",
            51,
            30,
            "Giao dịch bán và mua lại trái phiếu Chính phủ với Kho bạc Nhà nước",
            [(32, "2.965.201")],
            [],
            "The comparative cell is a visible dash without an authenticated numeric-line bbox; the repo source row remains open while the family total retains its controlled nonzero aggregation.",
        )
    ]
    return _doc(
        base,
        "CTG",
        51,
        5,
        "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
        [(6, "31.12.2025"), (7, "31.12.2024")],
        [(8, "Triệu đồng"), (9, "Triệu đồng")],
        mappings,
        equations,
        unresolved,
    )


def _bid(base: ModuleType) -> dict[str, Any]:
    d, r, e = base._direct, base._line, base._equation
    mappings = [
        d(
            1024,
            "FAMILY_TOTAL",
            50,
            35,
            "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG TRUNG ƯƠNG",
            r(50, 85, "218.825.525"),
            r(50, 86, "168.388.958"),
            "UNLABELED_TOTAL_AFTER_CHILDREN",
        ),
        d(
            6070,
            "CENTRAL_BANK_LOAN",
            50,
            40,
            "Vay từ Ngân hàng Trung ương",
            r(50, 41, "76.126.007"),
            r(50, 42, "16.410.184"),
        ),
        d(
            1025,
            "CREDIT_FILE_LOAN",
            50,
            50,
            "Vay theo hồ sơ tín dụng",
            r(50, 51, "1.567.354"),
            r(50, 52, "3.306.529"),
        ),
        d(
            1026,
            "DISCOUNT_LOAN",
            50,
            53,
            "Vay chiết khấu các giấy tờ có giá Ngân hàng Trung ương",
            r(50, 54, "74.409.153"),
            r(50, 55, "12.942.477"),
        ),
        d(
            6072,
            "MINISTRY_OF_FINANCE_DEPOSIT",
            50,
            57,
            "Tiền gửi của Bộ Tài chính",
            r(50, 58, "6.834.201"),
            r(50, 59, "6.713.235"),
        ),
        d(
            1035,
            "TREASURY_PAYMENT_DEPOSIT",
            50,
            66,
            "Tiền gửi thanh toán của Kho bạc Nhà nước",
            r(50, 67, "1.240.317"),
            r(50, 68, "1.359.539"),
        ),
        d(
            1036,
            "TREASURY_PAYMENT_DEPOSIT_VND",
            50,
            72,
            "Bằng VND",
            r(50, 73, "246.331"),
            r(50, 74, "771.913"),
        ),
        d(
            1037,
            "TREASURY_PAYMENT_DEPOSIT_FOREIGN_CURRENCY",
            50,
            76,
            "Bằng ngoại tệ",
            r(50, 77, "993.986"),
            r(50, 78, "587.626"),
        ),
        d(
            6071,
            "TREASURY_TERM_DEPOSIT",
            50,
            79,
            "Tiền gửi có kỳ hạn của Kho bạc Nhà nước",
            r(50, 80, "134.625.000"),
            r(50, 81, "143.906.000"),
        ),
    ]
    equations = [
        e(
            "CENTRAL_BANK_LOAN_COMPONENTS",
            "CURRENT",
            [r(50, 44, "149.500"), r(50, 51, "1.567.354"), r(50, 54, "74.409.153")],
            r(50, 41, "76.126.007"),
        ),
        e(
            "CENTRAL_BANK_LOAN_COMPONENTS",
            "COMPARATIVE",
            [
                r(50, 45, "149.500"),
                r(50, 48, "11.678"),
                r(50, 52, "3.306.529"),
                r(50, 55, "12.942.477"),
            ],
            r(50, 42, "16.410.184"),
        ),
        e(
            "MINISTRY_DEPOSIT_CURRENCIES",
            "CURRENT",
            [r(50, 61, "3.673.637"), r(50, 64, "3.160.564")],
            r(50, 58, "6.834.201"),
        ),
        e(
            "MINISTRY_DEPOSIT_CURRENCIES",
            "COMPARATIVE",
            [r(50, 62, "3.653.671"), r(50, 65, "3.059.564")],
            r(50, 59, "6.713.235"),
        ),
        e(
            "TREASURY_PAYMENT_CURRENCIES",
            "CURRENT",
            [r(50, 73, "246.331"), r(50, 77, "993.986")],
            r(50, 67, "1.240.317"),
        ),
        e(
            "TREASURY_PAYMENT_CURRENCIES",
            "COMPARATIVE",
            [r(50, 74, "771.913"), r(50, 78, "587.626")],
            r(50, 68, "1.359.539"),
        ),
        e(
            "TREASURY_TERM_VND_EQUALS_PARENT",
            "CURRENT",
            [r(50, 83, "134.625.000")],
            r(50, 80, "134.625.000"),
        ),
        e(
            "TREASURY_TERM_VND_EQUALS_PARENT",
            "COMPARATIVE",
            [r(50, 84, "143.906.000")],
            r(50, 81, "143.906.000"),
        ),
        e(
            "LOAN_FINANCE_TREASURY_TO_FAMILY_TOTAL",
            "CURRENT",
            [
                r(50, 41, "76.126.007"),
                r(50, 58, "6.834.201"),
                r(50, 67, "1.240.317"),
                r(50, 80, "134.625.000"),
            ],
            r(50, 85, "218.825.525"),
        ),
        e(
            "LOAN_FINANCE_TREASURY_TO_FAMILY_TOTAL",
            "COMPARATIVE",
            [
                r(50, 42, "16.410.184"),
                r(50, 59, "6.713.235"),
                r(50, 68, "1.359.539"),
                r(50, 81, "143.906.000"),
            ],
            r(50, 86, "168.388.958"),
        ),
    ]
    unresolved = [
        _open_row(
            base,
            "A2025-GN-007",
            50,
            43,
            "Nhận vốn từ NHNN để tạm ứng cho Ban Xử lý nợ cho vay đặc biệt Ngân hàng TMCP Nam Đô",
            [(44, "149.500")],
            [(45, "149.500")],
            "This distinct special-loan source component has no exact 1025-1033 leaf; it remains source evidence used only in the parent accounting equation.",
        ),
        _open_row(
            base,
            "A2025-GN-008",
            50,
            47,
            "Vay thực hiện dự án hiện đại hóa ngân hàng và Hệ thống Thanh toán của Ngân hàng bằng ngoại tệ",
            [],
            [(48, "11.678")],
            "The current cell is a visible dash and the project-specific source component has no exact 1025-1033 leaf; it remains open.",
        ),
    ]
    return _doc(
        base,
        "BID",
        50,
        35,
        "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG TRUNG ƯƠNG",
        [(36, "Số cuối năm"), (37, "Số đầu năm")],
        [(38, "Triệu VND"), (39, "Triệu VND")],
        mappings,
        equations,
        unresolved,
    )


def _vib(base: ModuleType) -> dict[str, Any]:
    d, r, e = base._direct, base._line, base._equation
    mappings = [
        d(
            1024,
            "FAMILY_TOTAL",
            45,
            5,
            "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN",
            r(45, 16, "10.980.813"),
            r(45, 17, "18.586.891"),
            "UNLABELED_TOTAL_AFTER_CHILDREN",
        ),
        d(
            6070,
            "CENTRAL_BANK_LOAN",
            45,
            10,
            "Vay NHNN",
            r(45, 11, "10.980.813"),
            r(45, 12, "18.586.891"),
        ),
        d(
            1026,
            "DISCOUNT_REDISCOUNT_LOAN",
            45,
            13,
            "Vay chiết khấu, tái chiết khấu các giấy tờ có giá",
            r(45, 14, "10.980.813"),
            r(45, 15, "18.586.891"),
        ),
    ]
    equations = [
        e(
            "DISCOUNT_LOAN_EQUALS_CENTRAL_BANK_LOAN",
            "CURRENT",
            [r(45, 14, "10.980.813")],
            r(45, 11, "10.980.813"),
        ),
        e(
            "DISCOUNT_LOAN_EQUALS_CENTRAL_BANK_LOAN",
            "COMPARATIVE",
            [r(45, 15, "18.586.891")],
            r(45, 12, "18.586.891"),
        ),
        e(
            "CENTRAL_BANK_LOAN_EQUALS_FAMILY_TOTAL",
            "CURRENT",
            [r(45, 11, "10.980.813")],
            r(45, 16, "10.980.813"),
        ),
        e(
            "CENTRAL_BANK_LOAN_EQUALS_FAMILY_TOTAL",
            "COMPARATIVE",
            [r(45, 12, "18.586.891")],
            r(45, 17, "18.586.891"),
        ),
    ]
    return _doc(
        base,
        "VIB",
        45,
        5,
        "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN",
        [(6, "31/12/2025"), (7, "31/12/2024")],
        [(8, "triệu đồng"), (9, "triệu đồng")],
        mappings,
        equations,
        [],
    )


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    return [
        _acb(base),
        _mbb(base),
        _vpb(base),
        _hdb(base),
        _vcb(base),
        _ctg(base),
        _bid(base),
        _vib(base),
    ]


def _annual_metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "annual_source_period_document_count": sum(
            trial["source_period"] == "2025-12-31" for trial in trials
        ),
        "confirmed_bound_report_absence_count": sum(
            trial["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["complete_region_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": sum(len(trial["unmapped_source_rows"]) for trial in trials),
        "verified_value_cell_count": sum(
            len(value["components"])
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
    }


def _configure_base() -> ModuleType:
    base = _load_module(
        "annual_2025_government_nhnn_mapping_base",
        "scripts/experiments/build_government_nhnn_liabilities_8bank_codex_verified_mapping_v1.py",
    )
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
    base._REVIEW_CHECKS = tuple(_REVIEW_CHECKS)
    base._REVIEW_SAFETY = canonical_clone_v1(_REVIEW_SAFETY)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    base._SCHEMA_EXPECTED.update(
        {
            1024: ("Các khoản nợ Chính phủ và Ngân hàng Nhà nước", 560),
            6070: ("Vay Ngân hàng Nhà nước", 1024),
            1025: ("Vay theo hồ sơ tín dụng", 6070),
            1026: ("Vay chiết khấu, tái chiết khấu giấy tờ có giá", 6070),
            1027: ("Vay cầm cố các giấy tờ có giá", 6070),
            1033: ("Vay khác", 6070),
            1035: ("Tiền gửi thanh toán của Kho bạc NN", 1024),
            1036: ("Trong đó: + Bằng tiền VNĐ", 1035),
            1037: ("+ Bằng ngoại tệ", 1035),
            6071: ("Tiền gửi có kỳ hạn của Kho bạc Nhà nước", 1024),
            6072: ("Tiền gửi của Bộ Tài chính", 1024),
            1039: ("Các khoản nợ khác", 1024),
        }
    )
    base._review_documents = lambda: _review_documents(base)
    base._metrics = _annual_metrics
    base._source_period_status = lambda source_period: (
        "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        if source_period == "2025-12-31"
        else (_ for _ in ()).throw(_error("annual Government/SBV source period drifted"))
    )
    return base


def _validate_expected_coverage(value: dict[str, Any]) -> dict[str, Any]:
    trials = value.get("trials")
    if type(trials) is not list or len(trials) != 8:
        raise _error("annual Government/SBV trial denominator drifted")
    if any(
        trial.get("source_period") != "2025-12-31"
        or trial.get("source_period_status")
        != "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        or trial.get("whole_document_uniqueness", {}).get("complete_region_count") != 1
        or trial.get("status") == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
        for trial in trials
    ):
        raise _error("annual Government/SBV source period or unique-region coverage drifted")
    for trial in trials:
        actual = {
            mapping["schema_binding"]["report_norm_id"] for mapping in trial["verified_mappings"]
        }
        if actual != _EXPECTED_IDS[trial["document_provenance"]]:
            raise _error(
                f"annual Government/SBV schema coverage drifted: {trial['document_provenance']}"
            )
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual Government/SBV metrics drifted")
    return value


def build_annual_2025_government_nhnn_liabilities_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _configure_base()._review_blueprint()


def build_live_annual_2025_government_nhnn_liabilities_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    try:
        return _validate_expected_coverage(
            _configure_base().build_live_government_nhnn_liabilities_8bank_codex_verified_mapping_v1()
        )
    except Annual2025GovernmentNHNNLiabilities8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def validate_annual_2025_government_nhnn_liabilities_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    try:
        return _validate_expected_coverage(
            _configure_base().validate_live_government_nhnn_liabilities_8bank_codex_verified_mapping_v1(
                value
            )
        )
    except Annual2025GovernmentNHNNLiabilities8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    base = _configure_base()
    if args.write_review:
        base._write(REVIEW_PATH, base._review_blueprint())
    result = build_live_annual_2025_government_nhnn_liabilities_8bank_codex_verified_mapping_v1()
    if args.write_result:
        base._write(RESULT_PATH, result)
    elif args.verify:
        payload = base.support._stable_bytes(RESULT_PATH)
        persisted = base.support._strict_json(payload, RESULT_PATH.as_posix())
        validate_annual_2025_government_nhnn_liabilities_8bank_codex_verified_mapping_replay_v1(
            persisted
        )
        print(persisted["result_id"])
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
