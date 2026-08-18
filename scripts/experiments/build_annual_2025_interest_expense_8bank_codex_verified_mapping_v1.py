"""Verify annual-2025 interest-expense disclosures across eight banks."""

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
FORMAT_VERSION = "ANNUAL_2025_INTEREST_EXPENSE_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_INTEREST_EXPENSE_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_INTEREST_EXPENSE_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025ie8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_INTEREST_EXPENSE_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025ie8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0135"
REVIEW_PATH = Path(
    "docs/experiments/E-0135-annual-2025-interest-expense-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0135-annual-2025-interest-expense-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "iefdsv1:scan:5df0e7a69b91d1b782cd58a3911c31234f4ff8f7f18c816566fceea4371f5b46"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "BANK_BLIND_INTEREST_EXPENSE_GRAPH_VISIBLE_PDF_UPSTREAM_PPOCRV6_NUMERIC_"
    "CHALLENGER_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_"
    "CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "document_period_or_unit_inheritance_recorded_explicitly": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "source_children_and_parent_total_double_counted": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "finance_lease_interest_not_observed_in_bound_regions": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_interest_expense_rows": True,
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
    1151: ("Chi phí lãi và các khoản tương tự chi phí lãi", 1142, 697),
    1152: ("Trả lãi tiền gửi", 1151, 698),
    1153: ("Trả lãi tiền vay", 1151, 699),
    1154: ("Trả lãi phát hành giấy tờ có giá", 1151, 700),
    1155: ("Trả lãi tiền thuê tài chính", 1151, 701),
    1156: ("Chi phí khác cho hoạt động tín dụng", 1151, 702),
}
_EXPECTED_IDS = {
    code: {1151, 1152, 1153, 1154, 1156}
    for code in (
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    )
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 16,
    "document_count": 8,
    "document_unique_region_count": 8,
    "fresh_vietocr_numeric_disagreement_count": 0,
    "mapping_verified_count": 40,
    "open_source_row_count": 0,
    "q1_source_period_caveat_document_count": 0,
    "verified_value_cell_count": 80,
}


class Annual2025InterestExpense8BankError(ValueError):
    """Annual interest-expense evidence, accounting, schema or replay drifted."""


def _error(message: str) -> Annual2025InterestExpense8BankError:
    return Annual2025InterestExpense8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_interest_expense_8bank_codex_verified_mapping_v1.py"
    )
    spec = importlib.util.spec_from_file_location("annual_2025_interest_expense_base", path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load interest-expense support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _map(
    base: ModuleType,
    report_norm_id: int,
    role: str,
    page: int,
    label: tuple[int, str],
    current: tuple[int, str],
    comparative: tuple[int, str],
    *,
    topology: str = "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
) -> dict[str, Any]:
    return base._mapping(
        report_norm_id,
        role,
        base._label(page, label[0], label[1]),
        base._value(page, current[0], current[1]),
        base._value(page, comparative[0], comparative[1]),
        topology=topology,
    )


def _doc(
    base: ModuleType,
    code: str,
    page: int,
    owner: tuple[int, str],
    periods: list[tuple[int, str]],
    units: list[tuple[int, str]],
    mappings: list[dict[str, Any]],
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
            (37, "CHI PHÍ LÃI VÀ CÁC KHOẢN CHI PHÍ TƯƠNG TỰ"),
            [(38, "Năm 2025"), (39, "Năm 2024")],
            [(40, "Triệu VND"), (41, "Triệu VND")],
            [
                _map(
                    base,
                    1151,
                    "TOTAL_INTEREST_EXPENSE",
                    page,
                    (37, "CHI PHÍ LÃI VÀ CÁC KHOẢN CHI PHÍ TƯƠNG TỰ"),
                    (54, "31.850.134"),
                    (55, "23.108.047"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _map(
                    base,
                    1152,
                    "DEPOSIT_INTEREST",
                    page,
                    (42, "Trả lãi tiền gửi"),
                    (43, "23.385.497"),
                    (44, "18.675.100"),
                ),
                _map(
                    base,
                    1153,
                    "BORROWING_INTEREST",
                    page,
                    (45, "Trả lãi tiền vay"),
                    (46, "2.010.956"),
                    (47, "590.978"),
                ),
                _map(
                    base,
                    1154,
                    "ISSUED_PAPER_INTEREST",
                    page,
                    (48, "Trả lãi phát hành giấy tờ có giá"),
                    (49, "5.852.679"),
                    (50, "3.798.383"),
                ),
                _map(
                    base,
                    1156,
                    "OTHER_CREDIT_EXPENSE",
                    page,
                    (51, "Chi phí hoạt động tín dụng khác"),
                    (52, "601.002"),
                    (53, "43.586"),
                ),
            ],
        )
    )

    page = 72
    documents.append(
        _doc(
            base,
            "MBB",
            page,
            (36, "Chi phí lãi và các chi phí tương tự"),
            [(11, "Năm 2025"), (12, "Năm 2024")],
            [(13, "triệu đồng"), (14, "triệu đồng")],
            [
                _map(
                    base,
                    1151,
                    "TOTAL_INTEREST_EXPENSE",
                    page,
                    (36, "Chi phí lãi và các chi phí tương tự"),
                    (37, "(37.477.999)"),
                    (38, "(27.909.674)"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _map(
                    base,
                    1152,
                    "DEPOSIT_INTEREST",
                    page,
                    (39, "Chi phí lãi tiền gửi"),
                    (40, "(25.799.919)"),
                    (41, "(18.432.473)"),
                ),
                _map(
                    base,
                    1153,
                    "BORROWING_INTEREST",
                    page,
                    (42, "Chi phí lãi tiền vay"),
                    (43, "(2.637.325)"),
                    (44, "(1.988.997)"),
                ),
                _map(
                    base,
                    1154,
                    "ISSUED_PAPER_INTEREST",
                    page,
                    (45, "Chi phí lãi phát hành giấy tờ có giá"),
                    (46, "(8.708.408)"),
                    (47, "(6.559.439)"),
                ),
                _map(
                    base,
                    1156,
                    "OTHER_CREDIT_EXPENSE",
                    page,
                    (48, "Chi phí hoạt động tín dụng khác"),
                    (49, "(332.347)"),
                    (50, "(928.765)"),
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
            (40, "CHI PHÍ LÃI VÀ CÁC KHOẢN CHI PHÍ TƯƠNG TỰ"),
            [(41, "Năm 2025"), (42, "Năm 2024")],
            [(43, "Triệu đồng"), (44, "Triệu đồng")],
            [
                _map(
                    base,
                    1151,
                    "TOTAL_INTEREST_EXPENSE",
                    page,
                    (40, "CHI PHÍ LÃI VÀ CÁC KHOẢN CHI PHÍ TƯƠNG TỰ"),
                    (57, "42.596.241"),
                    (58, "31.031.238"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _map(
                    base,
                    1152,
                    "DEPOSIT_INTEREST",
                    page,
                    (45, "Trả lãi tiền gửi"),
                    (46, "28.898.469"),
                    (47, "21.300.529"),
                ),
                _map(
                    base,
                    1153,
                    "BORROWING_INTEREST",
                    page,
                    (48, "Trả lãi tiền vay"),
                    (49, "7.144.730"),
                    (50, "5.503.601"),
                ),
                _map(
                    base,
                    1154,
                    "ISSUED_PAPER_INTEREST",
                    page,
                    (51, "Trả lãi phát hành giấy tờ có giá"),
                    (52, "5.290.040"),
                    (53, "3.201.546"),
                ),
                _map(
                    base,
                    1156,
                    "OTHER_CREDIT_EXPENSE",
                    page,
                    (54, "Chi phí hoạt động tín dụng khác"),
                    (55, "1.263.002"),
                    (56, "1.025.562"),
                ),
            ],
        )
    )

    page = 49
    documents.append(
        _doc(
            base,
            "HDB",
            page,
            (86, "CHI PHÍ LÃI VÀ CÁC CHI PHÍ TƯƠNG TỰ"),
            [(87, "Năm nay"), (88, "Năm trước")],
            [(89, "Triệu VND"), (90, "Triệu VND")],
            [
                _map(
                    base,
                    1151,
                    "TOTAL_INTEREST_EXPENSE",
                    page,
                    (86, "CHI PHÍ LÃI VÀ CÁC CHI PHÍ TƯƠNG TỰ"),
                    (107, "33.246.226"),
                    (108, "27.138.452"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _map(
                    base,
                    1152,
                    "DEPOSIT_INTEREST",
                    page,
                    (91, "Chi phí lãi tiền gửi"),
                    (92, "26.150.925"),
                    (93, "20.578.179"),
                ),
                _map(
                    base,
                    1153,
                    "BORROWING_INTEREST",
                    page,
                    (95, "Chi phí lãi tiền vay"),
                    (96, "1.673.463"),
                    (97, "2.984.870"),
                ),
                _map(
                    base,
                    1154,
                    "ISSUED_PAPER_INTEREST",
                    page,
                    (98, "Chi phí lãi phát hành giấy tờ có giá"),
                    (99, "5.195.023"),
                    (100, "3.531.995"),
                ),
                _map(
                    base,
                    1156,
                    "OTHER_CREDIT_EXPENSE",
                    page,
                    (102, "Chi phí hoạt động tín dụng khác"),
                    (103, "226.815"),
                    (104, "43.408"),
                ),
            ],
        )
    )

    page = 58
    documents.append(
        _doc(
            base,
            "VCB",
            page,
            (8, "Chi phí lãi và các chi phí tương tự"),
            [(9, "2025"), (10, "2024")],
            [(11, "Triệu VND"), (12, "Triệu VND")],
            [
                _map(
                    base,
                    1151,
                    "TOTAL_INTEREST_EXPENSE",
                    page,
                    (8, "Chi phí lãi và các chi phí tương tự"),
                    (25, "46.445.074"),
                    (26, "38.249.106"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _map(
                    base,
                    1152,
                    "DEPOSIT_INTEREST",
                    page,
                    (13, "Chi phí lãi tiền gửi"),
                    (14, "44.117.305"),
                    (15, "36.034.158"),
                ),
                _map(
                    base,
                    1153,
                    "BORROWING_INTEREST",
                    page,
                    (16, "Chi phí lãi tiền vay"),
                    (17, "1.008.149"),
                    (18, "795.798"),
                ),
                _map(
                    base,
                    1154,
                    "ISSUED_PAPER_INTEREST",
                    page,
                    (19, "Chi phí lãi phát hành giấy tờ có giá"),
                    (20, "1.159.929"),
                    (21, "1.346.846"),
                ),
                _map(
                    base,
                    1156,
                    "OTHER_CREDIT_EXPENSE",
                    page,
                    (22, "Chi phí khác cho hoạt động tín dụng"),
                    (23, "159.691"),
                    (24, "72.304"),
                ),
            ],
        )
    )

    page = 57
    documents.append(
        _doc(
            base,
            "CTG",
            page,
            (66, "CHI PHÍ LÃI VÀ CÁC KHOẢN CHI PHÍ TƯƠNG TỰ"),
            [(67, "Năm tài chính kết thúc ngày"), (68, "31.12.2025"), (69, "31.12.2024")],
            [(70, "Triệu đồng"), (71, "Triệu đồng")],
            [
                _map(
                    base,
                    1151,
                    "TOTAL_INTEREST_EXPENSE",
                    page,
                    (66, "CHI PHÍ LÃI VÀ CÁC KHOẢN CHI PHÍ TƯƠNG TỰ"),
                    (84, "76.689.083"),
                    (85, "62.057.891"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _map(
                    base,
                    1152,
                    "DEPOSIT_INTEREST",
                    page,
                    (72, "Lãi tiền gửi"),
                    (73, "64.179.992"),
                    (74, "52.868.897"),
                ),
                _map(
                    base,
                    1153,
                    "BORROWING_INTEREST",
                    page,
                    (75, "Lãi tiền vay"),
                    (76, "1.723.242"),
                    (77, "2.477.779"),
                ),
                _map(
                    base,
                    1154,
                    "ISSUED_PAPER_INTEREST",
                    page,
                    (78, "Lãi phát hành giấy tờ có giá"),
                    (79, "10.311.699"),
                    (80, "6.493.137"),
                ),
                _map(
                    base,
                    1156,
                    "OTHER_CREDIT_EXPENSE",
                    page,
                    (81, "Chi phí hoạt động tín dụng khác"),
                    (82, "474.150"),
                    (83, "218.078"),
                ),
            ],
        )
    )

    page = 55
    documents.append(
        _doc(
            base,
            "BID",
            page,
            (4, "CHI PHÍ LÃI VÀ CÁC CHI PHÍ TƯƠNG TỰ"),
            [(5, "Năm nay"), (6, "Năm trước")],
            [(7, "Triệu VND"), (8, "Triệu VND")],
            [
                _map(
                    base,
                    1151,
                    "TOTAL_INTEREST_EXPENSE",
                    page,
                    (4, "CHI PHÍ LÃI VÀ CÁC CHI PHÍ TƯƠNG TỰ"),
                    (21, "91.697.828"),
                    (22, "80.280.835"),
                    topology="TRAILING_UNLABELED_PARENT_TOTAL",
                ),
                _map(
                    base,
                    1152,
                    "DEPOSIT_INTEREST",
                    page,
                    (9, "Trả lãi tiền gửi"),
                    (10, "77.801.603"),
                    (11, "67.389.302"),
                ),
                _map(
                    base,
                    1153,
                    "BORROWING_INTEREST",
                    page,
                    (12, "Trả lãi tiền vay"),
                    (13, "2.628.733"),
                    (14, "2.449.569"),
                ),
                _map(
                    base,
                    1154,
                    "ISSUED_PAPER_INTEREST",
                    page,
                    (15, "Trả lãi phát hành giấy tờ có giá"),
                    (16, "11.070.107"),
                    (17, "9.749.844"),
                ),
                _map(
                    base,
                    1156,
                    "OTHER_CREDIT_EXPENSE",
                    page,
                    (18, "Chi phí hoạt động tín dụng khác"),
                    (19, "197.385"),
                    (20, "692.120"),
                ),
            ],
        )
    )

    page = 50
    documents.append(
        _doc(
            base,
            "VIB",
            page,
            (46, "Chi phí lãi và các chi phí tương tự"),
            [(27, "2025"), (28, "2024")],
            [(29, "triệu đồng"), (30, "triệu đồng")],
            [
                _map(
                    base,
                    1151,
                    "TOTAL_INTEREST_EXPENSE",
                    page,
                    (46, "Chi phí lãi và các chi phí tương tự"),
                    (47, "(20.231.849)"),
                    (48, "(15.692.526)"),
                    topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
                ),
                _map(
                    base,
                    1152,
                    "DEPOSIT_INTEREST",
                    page,
                    (49, "Trả lãi tiền gửi"),
                    (50, "(16.759.963)"),
                    (51, "(12.696.554)"),
                ),
                _map(
                    base,
                    1153,
                    "BORROWING_INTEREST",
                    page,
                    (52, "Trả lãi tiền vay"),
                    (53, "(1.891.535)"),
                    (54, "(1.849.522)"),
                ),
                _map(
                    base,
                    1154,
                    "ISSUED_PAPER_INTEREST",
                    page,
                    (57, "Trả lãi phát hành giấy tờ có giá"),
                    (55, "(1.553.581)"),
                    (56, "(1.112.775)"),
                    topology="SAME_ROW_GEOMETRY_VALUE_BEFORE_PROVIDER_LABEL_ORDER",
                ),
                _map(
                    base,
                    1156,
                    "OTHER_CREDIT_EXPENSE",
                    page,
                    (60, "Chi phí hoạt động tín dụng khác"),
                    (58, "(26.770)"),
                    (59, "(33.675)"),
                    topology="SAME_ROW_GEOMETRY_VALUE_BEFORE_PROVIDER_LABEL_ORDER",
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
    base.FAMILY_END_DISPLAY_ORDER = 702
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
        else (_ for _ in ()).throw(_error("annual interest-expense period drifted"))
    )


def _assert_result(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error(f"annual interest-expense result metrics drifted: {value.get('metrics')!r}")
    for trial in value.get("trials", []):
        actual = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        if actual != _EXPECTED_IDS[trial["document_provenance"]]:
            raise _error("annual interest-expense mapped schema set drifted")
        if trial["source_period_status"] != (
            "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        ):
            raise _error("annual interest-expense source period status drifted")
    return value


def build_annual_2025_interest_expense_pixel_review_blueprint_v1() -> dict[str, Any]:
    base = _load_base()
    _configure(base)
    return base._review_blueprint()


def build_live_annual_2025_interest_expense_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    base = _load_base()
    _configure(base)
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review = base._review_blueprint()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    scan = base.scanner.build_interest_expense_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    result = base.build_interest_expense_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    replayed = base.validate_interest_expense_8bank_codex_verified_mapping_replay_v1(
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
        value = build_annual_2025_interest_expense_pixel_review_blueprint_v1()
    else:
        value = build_live_annual_2025_interest_expense_8bank_codex_verified_mapping_v1()
        print(value["result_id"])
    output.write_bytes(canonical_json_bytes_v1(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
