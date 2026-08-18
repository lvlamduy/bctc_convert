"""Verify annual-2025 trading-securities activity across eight banks.

The annual profile reuses the existing whole-document, bank-blind trading-
securities graph and its independent numeric challenger.  The provision row is
an optional child: when it is printed it participates in the net equation;
when it is absent, income plus expense must close the visible net exactly.
Investment-securities activity remains a distinct negative-control family.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_TRADING_SECURITIES_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_TRADING_SECURITIES_ACTIVITY_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_TRADING_SECURITIES_ACTIVITY_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025tsa8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_TRADING_SECURITIES_ACTIVITY_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025tsa8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0139"
REVIEW_PATH = Path(
    "docs/experiments/E-0139-annual-2025-trading-securities-activity-8bank-"
    "codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0139-annual-2025-trading-securities-activity-8bank-"
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
EXPECTED_SCAN_ID = "tsafdsv1:scan:839d5f074d2d489970452ee37f9502f2a18e506faf5b3763e3c4abcbeeb7bfdf"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_TRADING_SECURITIES_ACTIVITY_GRAPH_VISIBLE_PDF_"
    "UPSTREAM_PPOCRV6_NUMERIC_CHALLENGER_PERIOD_UNIT_OPTIONAL_PROVISION_"
    "ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_CANONICALIZATION_EXPORT_OR_"
    "PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "investment_securities_activity_relabelled_as_trading_activity": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_seven_reviewed_annual_trading_regions": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_label_alone_used_to_select_provision_family": False,
    "text_similarity_alone_used_for_mapping": False,
    "whole_pdf_uniqueness_replayed": True,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "investment_securities_region_used_as_trading_region": False,
    "mapping_decided_by_text_similarity_alone": False,
    "optional_provision_row_required_in_every_bank": False,
    "source_label_caveat_hidden": False,
    "visible_pdf_pixels_reviewed": True,
    "whole_pdf_uniqueness_replayed": True,
}
_SCHEMA_EXPECTED = {
    1188: ("Lãi thuần từ hoạt động mua bán chứng khoán kinh doanh", 1142, 746),
    1189: ("Thu nhập do mua bán chứng khoán kinh doanh", 1188, 747),
    1190: ("Chi phí mua bán chứng khoán kinh doanh", 1188, 748),
    1191: ("(Trích lập)/Hoàn nhập dự phòng giảm giá chứng khoán kinh doanh", 1188, 749),
}
_EXPECTED_PAGES = {
    "ACB": [68, 68],
    "MBB": [73, 73],
    "VPB": [70, 70],
    "HDB": [50, 50],
    "VCB": [59, 59],
    "CTG": [58, 58],
    "BID": [56, 56],
    "VIB": None,
}
_EXPECTED_REPORT_NORM_IDS = {
    "ACB": {1188, 1189, 1190, 1191},
    "MBB": {1188, 1189, 1190, 1191},
    "VPB": {1188, 1189, 1190, 1191},
    "HDB": {1188, 1189, 1190},
    "VCB": {1188, 1189, 1190, 1191},
    "CTG": {1188, 1189, 1190, 1191},
    "BID": {1188, 1189, 1190, 1191},
    "VIB": set(),
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 14,
    "authenticated_pixel_dash_zero_count": 0,
    "detailed_note_not_present_document_count": 1,
    "document_count": 8,
    "document_unique_region_count": 7,
    "fresh_vietocr_numeric_disagreement_count": 0,
    "mapping_verified_count": 27,
    "open_source_row_count": 0,
    "q1_source_period_caveat_document_count": 0,
    "source_label_caveat_mapping_count": 0,
    "verified_value_cell_count": 54,
}


class Annual2025TradingSecuritiesActivity8BankError(ValueError):
    """Annual trading-securities structure, numbers, equations or schema drifted."""


def _error(message: str) -> Annual2025TradingSecuritiesActivity8BankError:
    return Annual2025TradingSecuritiesActivity8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_trading_securities_activity_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_trading_securities_activity_base"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual trading-securities support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    trailing = "INCOME_EXPENSE_OPTIONAL_PROVISION_THEN_NET_TWO_PERIOD_LANES"
    documents = [
        base._mapped_document(
            "ACB",
            68,
            "2025-12-31",
            trailing,
            [(68, 34, "Năm 2025"), (68, 35, "Năm 2024")],
            [(68, 36, "Triệu VND"), (68, 37, "Triệu VND")],
            base._four_rows(
                68,
                (
                    33,
                    "LÃI THUẦN TỪ HOẠT ĐỘNG MUA BÁN CHỨNG KHOÁN KINH DOANH",
                    48,
                    "474.316",
                    49,
                    "200.357",
                ),
                (38, "Thu nhập từ mua bán chứng khoán kinh doanh", 39, "677.875", 40, "408.677"),
                (41, "Chi phí về mua bán chứng khoán kinh doanh", 42, "(188.020)", 43, "(206.803)"),
                (
                    44,
                    "Trích lập dự phòng rủi ro chứng khoán kinh doanh",
                    base._line(68, 46, "(15.539)"),
                    base._line(68, 47, "(1.517)"),
                ),
                trailing,
            ),
        ),
        base._mapped_document(
            "MBB",
            73,
            "2025-12-31",
            "WRAPPED_PROVISION_LABEL_AND_LABELLED_NET",
            [(73, 38, "Năm 2025"), (73, 39, "Năm 2024")],
            [(73, 40, "triệu đồng"), (73, 41, "triệu đồng")],
            base._four_rows(
                73,
                (37, "LÃI THUẦN TỪ MUA BÁN CHỨNG KHOÁN KINH DOANH", 53, "668.384", 54, "1.756.022"),
                (
                    42,
                    "Thu nhập từ mua bán chứng khoán kinh doanh",
                    43,
                    "1.048.998",
                    44,
                    "2.553.518",
                ),
                (45, "Chi phí về mua bán chứng khoán kinh doanh", 46, "(341.400)", 47, "(797.929)"),
                (
                    48,
                    "(Trích lập)/hoàn nhập dự phòng rủi ro chứng",
                    base._line(73, 50, "(39.214)"),
                    base._line(73, 51, "433"),
                ),
                "WRAPPED_PROVISION_LABEL_AND_LABELLED_NET",
            ),
        ),
        base._mapped_document(
            "VPB",
            70,
            "2025-12-31",
            trailing,
            [(70, 6, "Năm 2025"), (70, 7, "Năm 2024")],
            [(70, 8, "Triệu đồng"), (70, 9, "Triệu đồng")],
            base._four_rows(
                70,
                (5, "LÃI THUẦN TỪ MUA BÁN CHỨNG KHOÁN KINH DOANH", 21, "1.566.648", 22, "360.956"),
                (10, "Thu nhập từ mua bán chứng khoán kinh doanh", 11, "1.962.291", 12, "680.929"),
                (13, "Chi phí về mua bán chứng khoán kinh doanh", 14, "(293.127)", 15, "(330.688)"),
                (
                    16,
                    "(Trích lập)/Hoàn nhập dự phòng chứng khoán",
                    base._line(70, 18, "(102.516)"),
                    base._line(70, 19, "10.715"),
                ),
                trailing,
            ),
        ),
    ]

    hdb_topology = "INCOME_EXPENSE_THEN_UNLABELLED_NET_WITHOUT_PROVISION_ROW"
    documents.append(
        base._mapped_document(
            "HDB",
            50,
            "2025-12-31",
            hdb_topology,
            [(50, 77, "Năm nay"), (50, 78, "Năm trước")],
            [(50, 79, "Triệu VND"), (50, 80, "Triệu VND")],
            [
                base._mapping(
                    "NET_TRADING_SECURITIES",
                    1188,
                    (76, "Lãi thuần từ hoạt động mua bán chứng khoán kinh doanh"),
                    base._line(50, 87, "639.460"),
                    base._line(50, 88, "68.929"),
                    hdb_topology,
                    page=50,
                ),
                base._mapping(
                    "INCOME_TRADING_SECURITIES",
                    1189,
                    (81, "Thu nhập từ mua bán chứng khoán kinh doanh"),
                    base._line(50, 82, "673.417"),
                    base._line(50, 83, "412.368"),
                    hdb_topology,
                    page=50,
                ),
                base._mapping(
                    "EXPENSE_TRADING_SECURITIES",
                    1190,
                    (84, "Chi phí về mua bán chứng khoán kinh doanh"),
                    base._line(50, 85, "(33.957)"),
                    base._line(50, 86, "(343.439)"),
                    hdb_topology,
                    page=50,
                ),
            ],
        )
    )
    documents.extend(
        [
            base._mapped_document(
                "VCB",
                59,
                "2025-12-31",
                trailing,
                [(59, 51, "2025"), (59, 52, "2024")],
                [(59, 53, "Triệu VND"), (59, 54, "Triệu VND")],
                base._four_rows(
                    59,
                    (
                        50,
                        "Lãi thuần từ mua bán chứng khoán kinh doanh",
                        65,
                        "171.160",
                        66,
                        "62.123",
                    ),
                    (
                        55,
                        "Thu nhập từ mua bán chứng khoán kinh doanh",
                        56,
                        "268.659",
                        57,
                        "128.338",
                    ),
                    (
                        58,
                        "Chi phí về mua bán chứng khoán kinh doanh",
                        59,
                        "(62.366)",
                        60,
                        "(49.912)",
                    ),
                    (
                        61,
                        "Trích lập chi phí dự phòng giảm giá chứng khoán kinh",
                        base._line(59, 63, "(35.133)"),
                        base._line(59, 64, "(16.303)"),
                    ),
                    trailing,
                ),
            ),
            base._mapped_document(
                "CTG",
                58,
                "2025-12-31",
                "LABELLED_NET_AND_PROVISION_ROW",
                [
                    (58, 80, "Năm tài chính kết thúc ngày"),
                    (58, 81, "31.12.2025"),
                    (58, 82, "31.12.2024"),
                ],
                [(58, 83, "Triệu đồng"), (58, 84, "Triệu đồng")],
                base._four_rows(
                    58,
                    (
                        79,
                        "LÃI THUẦN TỪ MUA BÁN CHỨNG KHOÁN KINH DOANH",
                        95,
                        "703.793",
                        96,
                        "91.829",
                    ),
                    (
                        85,
                        "Thu nhập từ mua bán chứng khoán kinh doanh",
                        86,
                        "664.621",
                        87,
                        "125.760",
                    ),
                    (
                        88,
                        "Chi phí từ mua bán chứng khoán kinh doanh",
                        89,
                        "(50.013)",
                        90,
                        "(30.339)",
                    ),
                    (
                        91,
                        "Dự phòng rủi ro chứng khoán kinh doanh",
                        base._line(58, 92, "89.185"),
                        base._line(58, 93, "(3.592)"),
                    ),
                    "LABELLED_NET_AND_PROVISION_ROW",
                ),
            ),
            base._mapped_document(
                "BID",
                56,
                "2025-12-31",
                "INNER_TRADING_OWNER_UNDER_SHARED_TRADING_AND_INVESTMENT_UMBRELLA",
                [(56, 7, "Năm nay"), (56, 8, "Năm trước")],
                [(56, 9, "Triệu VND"), (56, 10, "Triệu VND")],
                base._four_rows(
                    56,
                    (
                        6,
                        "Lãi thuần từ mua bán chứng khoán kinh doanh",
                        21,
                        "718.634",
                        22,
                        "284.513",
                    ),
                    (
                        11,
                        "Thu nhập từ mua bán chứng khoán kinh doanh",
                        12,
                        "1.115.281",
                        13,
                        "460.118",
                    ),
                    (
                        14,
                        "Chi phí về mua bán chứng khoán kinh doanh",
                        15,
                        "(404.247)",
                        16,
                        "(167.502)",
                    ),
                    (
                        17,
                        "Hoàn nhập/(Trích lập) dự phòng chứng khoán kinh",
                        base._line(56, 18, "7.600"),
                        base._line(56, 19, "(8.103)"),
                    ),
                    "INNER_TRADING_OWNER_UNDER_SHARED_TRADING_AND_INVESTMENT_UMBRELLA",
                ),
            ),
            base._absent(
                "VIB",
                [51],
                "The complete bound annual report contains investment-securities activity but no detailed trading-securities income/expense graph; investment activity is a distinct family control and this is only a bounded-report absence.",
            ),
        ]
    )
    return documents


def _configure(base: ModuleType, scan_id: str) -> None:
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.REVIEW_RUN_ID = REVIEW_RUN_ID
    base.ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = False
    base.SCHEMA_FAMILY_END_DISPLAY_ORDER = 750
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
    base._source_period_status = lambda source_period: (
        "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        if source_period == "2025-12-31"
        else (_ for _ in ()).throw(_error("annual trading-securities source period drifted"))
    )


def _inputs() -> tuple[ModuleType, dict[str, Any], dict[str, Any], dict[str, Any]]:
    base = _load_base()
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, _ = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    scan = base.scanner.build_trading_securities_activity_full_document_scan_v1(semantic_index)
    if scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("annual trading-securities structure scan identity drifted")
    _configure(base, scan["scan_id"])
    return base, semantic_index, crop_manifest, scan


def _assert_result(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual trading-securities exact metrics drifted")
    for trial, code in zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True):
        mapped_ids = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        expected_status = (
            "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" if code == "VIB" else "VERIFIED_BY_CODEX"
        )
        expected_equations = 0 if code == "VIB" else 2
        if (
            trial["document_provenance"] != code
            or trial["status"] != expected_status
            or trial["page_span"] != _EXPECTED_PAGES[code]
            or mapped_ids != _EXPECTED_REPORT_NORM_IDS[code]
            or len(trial["verified_accounting_equations"]) != expected_equations
            or trial["source_period_status"]
            != (
                "NOT_APPLICABLE_NO_DETAILED_NOTE"
                if code == "VIB"
                else "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
            )
        ):
            raise _error("annual trading-securities trial closure drifted")
    return value


def build_annual_2025_trading_securities_activity_pixel_review_blueprint_v1() -> dict[str, Any]:
    base, _semantic_index, _crop_manifest, _scan = _inputs()
    return base._review_blueprint()


def build_live_annual_2025_trading_securities_activity_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    base, semantic_index, crop_manifest, scan = _inputs()
    review = base._review_blueprint()
    crop_sha = hashlib.sha256(canonical_json_bytes_v1(crop_manifest)).hexdigest()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    result = base.build_trading_securities_activity_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    replayed = base.validate_trading_securities_activity_8bank_codex_verified_mapping_replay_v1(
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
        build_annual_2025_trading_securities_activity_pixel_review_blueprint_v1()
        if args.write_review
        else build_live_annual_2025_trading_securities_activity_8bank_codex_verified_mapping_v1()
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes_v1(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
