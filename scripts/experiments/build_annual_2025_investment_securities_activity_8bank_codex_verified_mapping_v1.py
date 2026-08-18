"""Verify annual-2025 investment-securities activity across eight banks.

The annual profile reuses one complete-PDF, bank-blind variant graph.  A
provision schema row may be printed as one source row or as several visible
sub-rows; in the latter case every source value is independently challenged
before the components are summed.  Trading-securities regions remain a
distinct negative-control family.
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
FORMAT_VERSION = "ANNUAL_2025_INVESTMENT_SECURITIES_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_INVESTMENT_SECURITIES_ACTIVITY_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_INVESTMENT_SECURITIES_ACTIVITY_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025isa8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_INVESTMENT_SECURITIES_ACTIVITY_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025isa8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0140"
REVIEW_PATH = Path(
    "docs/experiments/E-0140-annual-2025-investment-securities-activity-8bank-"
    "codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0140-annual-2025-investment-securities-activity-8bank-"
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
EXPECTED_SCAN_ID = "isafdsv1:scan:451a592d412a6a68690363105a25ae0f013cdee7a97a9bbb4a92b40b435471c3"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_INVESTMENT_SECURITIES_ACTIVITY_GRAPH_VISIBLE_PDF_"
    "UPSTREAM_PPOCRV6_NUMERIC_CHALLENGER_PERIOD_UNIT_OPTIONAL_MULTIROW_"
    "PROVISION_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_CANONICALIZATION_"
    "EXPORT_OR_PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_eight_reviewed_annual_investment_regions": True,
    "multirow_provision_aggregated_only_after_component_verification": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "trading_activity_relabelled_as_investment_activity": False,
    "whole_pdf_uniqueness_replayed": True,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "multirow_provision_collapsed_without_visible_component_checks": False,
    "optional_provision_row_required_in_every_bank": False,
    "trading_securities_region_used_as_investment_region": False,
    "visible_pdf_pixels_reviewed": True,
    "whole_pdf_uniqueness_replayed": True,
}
_SCHEMA_EXPECTED = {
    1193: ("Lãi thuần từ hoạt động mua bán chứng khoán đầu tư", 1142, 751),
    1194: ("Thu nhập do mua bán chứng khoán đầu tư", 1193, 752),
    1195: ("Chi phí mua bán chứng khoán đầu tư", 1193, 753),
    1196: ("(Trích lập)/Hoàn nhập dự phòng giảm giá chứng khoán đầu tư", 1193, 754),
    6028: ("(Trích lập)/Hoàn nhập dự phòng giảm giá góp vốn, đầu tư dài hạn", 1193, 755),
}
_EXPECTED_PAGES = {
    "ACB": [68, 68],
    "MBB": [73, 73],
    "VPB": [70, 70],
    "HDB": [50, 50],
    "VCB": [59, 59],
    "CTG": [59, 59],
    "BID": [56, 56],
    "VIB": [51, 51],
}
_EXPECTED_REPORT_NORM_IDS = {
    "ACB": {1193, 1194, 1195, 1196},
    "MBB": {1193, 1194, 1195, 1196, 6028},
    "VPB": {1193, 1194, 1195, 1196},
    "HDB": {1193, 1194, 1195, 1196},
    "VCB": {1193, 1194, 1195},
    "CTG": {1193, 1194, 1195, 1196},
    "BID": {1193, 1194, 1195, 1196},
    "VIB": {1193, 1194, 1195, 1196},
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 16,
    "authenticated_pixel_dash_zero_count": 5,
    "detailed_note_not_present_document_count": 0,
    "document_count": 8,
    "document_unique_region_count": 8,
    "fresh_vietocr_numeric_disagreement_count": 0,
    "mapping_verified_count": 32,
    "open_source_row_count": 0,
    "q1_source_period_caveat_document_count": 0,
    "verified_source_numeric_component_count": 70,
    "verified_value_cell_count": 64,
}


class Annual2025InvestmentSecuritiesActivity8BankError(ValueError):
    """Annual investment-securities structure, pixels or equations drifted."""


def _error(message: str) -> Annual2025InvestmentSecuritiesActivity8BankError:
    return Annual2025InvestmentSecuritiesActivity8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_investment_securities_activity_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_investment_securities_activity_base"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual investment-securities support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _aggregate_provision(
    base: ModuleType,
    page: int,
    label: tuple[int, str],
    extra_labels: list[tuple[int, str]],
    current: list[dict[str, Any]],
    comparative: list[dict[str, Any]],
    topology: str,
) -> dict[str, Any]:
    mapping = base._mapping(
        "PROVISION_INVESTMENT_SECURITIES",
        label,
        current[0],
        comparative[0],
        topology,
        page=page,
    )
    mapping["component_labels"] = [base._ref(page, line, text) for line, text in extra_labels]
    mapping["values"] = {"COMPARATIVE_PERIOD": comparative, "CURRENT_PERIOD": current}
    return mapping


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    topology = "INCOME_EXPENSE_OPTIONAL_SINGLE_OR_MULTIROW_PROVISION_THEN_NET_TWO_PERIOD_LANES"
    documents = [
        base._mapped_document(
            "ACB",
            68,
            "2025-12-31",
            topology,
            [(68, 52, "Năm 2025"), (68, 53, "Năm 2024")],
            [(68, 54, "Triệu VND"), (68, 55, "Triệu VND")],
            base._rows(
                68,
                topology,
                owner=(
                    51,
                    "LÃI THUẦN TỪ HOẠT ĐỘNG MUA BÁN CHỨNG KHOÁN ĐẦU TƯ",
                    base._line(68, 64, "396.784"),
                    base._line(68, 65, "450.312"),
                ),
                income=(
                    56,
                    "Thu nhập từ mua bán chứng khoán đầu tư",
                    base._line(68, 57, "450.276"),
                    base._line(68, 58, "457.630"),
                ),
                expense=(
                    59,
                    "Chi phí về mua bán chứng khoán đầu tư",
                    base._line(68, 60, "(42.242)"),
                    base._line(68, 61, "(7.318)"),
                ),
                provision=(
                    62,
                    "Trích lập dự phòng chung cho chứng khoán đầu tư",
                    base._line(68, 63, "(11.250)"),
                    base._dash(
                        68,
                        [1518, 1725, 1537, 1738],
                        "ddfebfed6ce00b353965a8767ed9f5ff6b9a5ae926c4f9404f356fbd23d14076",
                    ),
                ),
            ),
        ),
        base._mapped_document(
            "MBB",
            73,
            "2025-12-31",
            "OPTIONAL_LONG_TERM_AND_SECURITIES_PROVISIONS_THEN_LABELLED_NET",
            [(73, 57, "Năm 2025"), (73, 58, "Năm 2024")],
            [(73, 59, "triệu đồng"), (73, 60, "triệu đồng")],
            base._rows(
                73,
                "OPTIONAL_LONG_TERM_AND_SECURITIES_PROVISIONS_THEN_LABELLED_NET",
                owner=(
                    56,
                    "LÃI THUẦN TỪ MUA BÁN CHỨNG KHOÁN ĐẦU TƯ",
                    base._line(73, 76, "1.590.093"),
                    base._line(73, 77, "2.803.105"),
                ),
                income=(
                    61,
                    "Thu nhập từ mua bán chứng khoán đầu tư",
                    base._line(73, 62, "1.658.738"),
                    base._line(73, 63, "3.136.652"),
                ),
                expense=(
                    64,
                    "Chi phí về mua bán chứng khoán đầu tư",
                    base._line(73, 65, "(334.832)"),
                    base._line(73, 66, "(297.115)"),
                ),
                provision=(
                    70,
                    "Hoàn nhập/(trích lập) dự phòng rủi ro chứng khoán đầu tư",
                    base._line(73, 72, "250.344"),
                    base._line(73, 73, "(7.625)"),
                ),
                other=(
                    67,
                    "Hoàn nhập/(trích lập) dự phòng rủi ro đầu tư dài hạn",
                    base._line(73, 68, "15.843"),
                    base._line(73, 69, "(28.807)"),
                ),
            ),
        ),
    ]

    vp_topology = "AFS_AND_HTM_PROVISION_COMPONENTS_SUM_TO_ONE_SCHEMA_PROVISION"
    vp_rows = base._rows(
        70,
        vp_topology,
        owner=(
            24,
            "LÃI THUẦN TỪ MUA BÁN CHỨNG KHOÁN ĐẦU TƯ",
            base._line(70, 42, "4.456"),
            base._line(70, 43, "469.667"),
        ),
        income=(
            29,
            "Thu nhập từ mua bán chứng khoán đầu tư",
            base._line(70, 30, "53.812"),
            base._line(70, 31, "415.080"),
        ),
        expense=(
            32,
            "Chi phí về mua bán chứng khoán đầu tư",
            base._line(70, 33, "(87.793)"),
            base._line(70, 34, "(96.353)"),
        ),
    )
    vp_rows.append(
        _aggregate_provision(
            base,
            70,
            (35, "Hoàn nhập dự phòng chứng khoán đầu tư sẵn sàng để bán"),
            [(39, "Hoàn nhập dự phòng chứng khoán giữ đến ngày đáo hạn")],
            [
                base._line(70, 37, "38.437"),
                base._dash(
                    70,
                    [1168, 1065, 1188, 1080],
                    "d369b4b3f0461803dc2c7be4477788a81c47761366c16ac2c4b430af8b8e51b3",
                ),
            ],
            [base._line(70, 38, "142.915"), base._line(70, 41, "8.025")],
            vp_topology,
        )
    )
    documents.append(
        base._mapped_document(
            "VPB",
            70,
            "2025-12-31",
            vp_topology,
            [(70, 25, "Năm 2025"), (70, 26, "Năm 2024")],
            [(70, 27, "Triệu đồng"), (70, 28, "Triệu đồng")],
            vp_rows,
        )
    )

    documents.extend(
        [
            base._mapped_document(
                "HDB",
                50,
                "2025-12-31",
                topology,
                [(50, 91, "Năm nay"), (50, 92, "Năm trước")],
                [(50, 93, "Triệu VND"), (50, 94, "Triệu VND")],
                base._rows(
                    50,
                    topology,
                    owner=(
                        90,
                        "LÃI THUẦN TỪ HOẠT ĐỘNG MUA BÁN CHỨNG KHOÁN ĐẦU TƯ",
                        base._line(50, 105, "855.910"),
                        base._line(50, 106, "68.253"),
                    ),
                    income=(
                        95,
                        "Thu nhập từ mua bán chứng khoán đầu tư",
                        base._line(50, 96, "951.994"),
                        base._line(50, 97, "297.870"),
                    ),
                    expense=(
                        98,
                        "Chi phí về mua bán chứng khoán đầu tư",
                        base._line(50, 99, "(55.991)"),
                        base._line(50, 100, "(221.039)"),
                    ),
                    provision=(
                        102,
                        "Trích lập dự phòng chứng khoán đầu tư",
                        base._line(50, 103, "(40.093)"),
                        base._line(50, 104, "(8.578)"),
                    ),
                ),
            ),
            base._mapped_document(
                "VCB",
                59,
                "2025-12-31",
                "INCOME_EXPENSE_THEN_UNLABELLED_NET_WITHOUT_PROVISION_ROW",
                [(59, 68, "2025"), (59, 69, "2024")],
                [(59, 70, "Triệu VND"), (59, 71, "Triệu VND")],
                base._rows(
                    59,
                    "INCOME_EXPENSE_THEN_UNLABELLED_NET_WITHOUT_PROVISION_ROW",
                    owner=(
                        67,
                        "Lãi thuần từ mua bán chứng khoán đầu tư",
                        base._line(59, 78, "3.616"),
                        base._line(59, 79, "3.444"),
                    ),
                    income=(
                        72,
                        "Thu nhập từ mua bán chứng khoán đầu tư",
                        base._line(59, 73, "6.316"),
                        base._line(59, 74, "5.685"),
                    ),
                    expense=(
                        75,
                        "Chi phí về mua bán chứng khoán đầu tư",
                        base._line(59, 76, "(2.700)"),
                        base._line(59, 77, "(2.241)"),
                    ),
                ),
            ),
            base._mapped_document(
                "CTG",
                59,
                "2025-12-31",
                topology,
                [
                    (59, 6, "Năm tài chính kết thúc ngày"),
                    (59, 7, "31.12.2025"),
                    (59, 8, "31.12.2024"),
                ],
                [(59, 9, "Triệu đồng"), (59, 10, "Triệu đồng")],
                base._rows(
                    59,
                    topology,
                    owner=(
                        5,
                        "LÃI/(LỖ) THUẦN TỪ MUA BÁN CHỨNG KHOÁN ĐẦU TƯ",
                        base._line(59, 22, "152.570"),
                        base._line(59, 23, "(288.044)"),
                    ),
                    income=(
                        11,
                        "Thu nhập từ mua bán chứng khoán đầu tư",
                        base._line(59, 12, "69.110"),
                        base._line(59, 13, "50.560"),
                    ),
                    expense=(
                        14,
                        "Chi phí từ mua bán chứng khoán đầu tư",
                        base._line(59, 15, "(3.128)"),
                        base._line(59, 16, "(2.360)"),
                    ),
                    provision=(
                        17,
                        "Dự phòng rủi ro chứng khoán đầu tư",
                        base._line(59, 18, "86.588"),
                        base._line(59, 19, "(336.244)"),
                    ),
                ),
            ),
            base._mapped_document(
                "BID",
                56,
                "2025-12-31",
                "NESTED_INVESTMENT_OWNER_UNDER_COMBINED_SECURITIES_UMBRELLA",
                [(56, 25, "Năm nay"), (56, 26, "Năm trước")],
                [(56, 27, "Triệu VND"), (56, 28, "Triệu VND")],
                base._rows(
                    56,
                    "NESTED_INVESTMENT_OWNER_UNDER_COMBINED_SECURITIES_UMBRELLA",
                    owner=(
                        24,
                        "Lãi thuần từ mua bán chứng khoán đầu tư",
                        base._line(56, 39, "2.262.126"),
                        base._line(56, 40, "4.900.330"),
                    ),
                    income=(
                        29,
                        "Thu nhập từ mua bán chứng khoán đầu tư",
                        base._line(56, 30, "1.111.389"),
                        base._line(56, 31, "5.235.457"),
                    ),
                    expense=(
                        32,
                        "Chi phí về mua bán chứng khoán đầu tư",
                        base._line(56, 33, "(1.202)"),
                        base._line(56, 34, "(29.421)"),
                    ),
                    provision=(
                        35,
                        "Hoàn nhập/(Trích lập) dự phòng rủi ro chứng khoán đầu tư",
                        base._line(56, 36, "1.151.939"),
                        base._line(56, 37, "(305.706)"),
                    ),
                ),
            ),
        ]
    )

    vib_topology = (
        "AFS_HTM_GENERAL_AND_HTM_SPECIFIC_PROVISION_COMPONENTS_SUM_TO_ONE_SCHEMA_PROVISION"
    )
    vib_rows = base._rows(
        51,
        vib_topology,
        owner=(
            32,
            "LÃI THUẦN TỪ MUA BÁN CHỨNG KHOÁN ĐẦU TƯ",
            base._line(51, 55, "79.774"),
            base._line(51, 56, "247.967"),
        ),
        income=(
            37,
            "Thu nhập từ mua bán chứng khoán đầu tư",
            base._line(51, 38, "546.473"),
            base._line(51, 39, "421.004"),
        ),
        expense=(
            40,
            "Chi phí về mua bán chứng khoán đầu tư",
            base._line(51, 41, "(468.199)"),
            base._line(51, 42, "(139.451)"),
        ),
    )
    vib_rows.append(
        _aggregate_provision(
            base,
            51,
            (43, "Hoàn nhập dự phòng chung cho chứng khoán sẵn sàng để bán"),
            [
                (47, "Hoàn nhập dự phòng chung chứng khoán đầu tư giữ đến ngày đáo hạn"),
                (50, "Trích lập dự phòng cụ thể cho chứng khoán đầu tư giữ đến ngày đáo hạn"),
            ],
            [
                base._line(51, 45, "1.500"),
                base._dash(
                    51,
                    [1199, 1110, 1220, 1125],
                    "a77924676c6d3af21ceff2e5894908b8ac0bbe1bc9533c5da42dad85b1a2187f",
                ),
                base._dash(
                    51,
                    [1199, 1170, 1220, 1186],
                    "36935dc1ef8e06b83cc1cccd4ac911183b8181601d39910428eb844d6bc1c15e",
                ),
            ],
            [
                base._dash(
                    51,
                    [1437, 1044, 1456, 1060],
                    "9cb6eb2927757469d872ec24e37eecd5d28fd651365c7936ce3577374ce6a8a3",
                ),
                base._line(51, 49, "318"),
                base._line(51, 51, "(33.904)"),
            ],
            vib_topology,
        )
    )
    documents.append(
        base._mapped_document(
            "VIB",
            51,
            "2025-12-31",
            vib_topology,
            [(51, 33, "2025"), (51, 34, "2024")],
            [(51, 35, "triệu đồng"), (51, 36, "triệu đồng")],
            vib_rows,
        )
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
    base.SCHEMA_FAMILY_END_DISPLAY_ORDER = 756
    base.INCLUDE_COMPONENT_METRICS = True
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
        else (_ for _ in ()).throw(_error("annual investment-securities source period drifted"))
    )


def _inputs() -> tuple[ModuleType, dict[str, Any], dict[str, Any], dict[str, Any]]:
    base = _load_base()
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, _ = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    scan = base.scanner.build_investment_securities_activity_full_document_scan_v1(semantic_index)
    if scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("annual investment-securities structure scan identity drifted")
    _configure(base, scan["scan_id"])
    return base, semantic_index, crop_manifest, scan


def _assert_result(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual investment-securities exact metrics drifted")
    by_bank: dict[str, dict[str, Any]] = {}
    for trial, code in zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True):
        mapped_ids = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        if (
            trial["document_provenance"] != code
            or trial["status"] != "VERIFIED_BY_CODEX"
            or trial["page_span"] != _EXPECTED_PAGES[code]
            or mapped_ids != _EXPECTED_REPORT_NORM_IDS[code]
            or len(trial["verified_accounting_equations"]) != 2
            or trial["source_period_status"]
            != "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        ):
            raise _error("annual investment-securities trial closure drifted")
        by_bank[code] = trial

    def provision_values(code: str) -> dict[str, dict[str, Any]]:
        mapping = next(
            row
            for row in by_bank[code]["verified_mappings"]
            if row["schema_binding"]["report_norm_id"] == 1196
        )
        return {item["axis_role"]: item for item in mapping["values"]}

    vp = provision_values("VPB")
    vib = provision_values("VIB")
    if (
        vp["CURRENT_PERIOD"]["normalized_value"] != 38_437
        or vp["COMPARATIVE_PERIOD"]["normalized_value"] != 150_940
        or len(vp["CURRENT_PERIOD"]["components"]) != 2
        or vib["CURRENT_PERIOD"]["normalized_value"] != 1_500
        or vib["COMPARATIVE_PERIOD"]["normalized_value"] != -33_586
        or len(vib["CURRENT_PERIOD"]["components"]) != 3
    ):
        raise _error("annual investment-securities component aggregation drifted")
    return value


def build_annual_2025_investment_securities_activity_pixel_review_blueprint_v1() -> dict[str, Any]:
    base, _semantic_index, _crop_manifest, _scan = _inputs()
    return base._review_blueprint()


def build_live_annual_2025_investment_securities_activity_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    base, semantic_index, crop_manifest, scan = _inputs()
    review = base._review_blueprint()
    crop_sha = hashlib.sha256(canonical_json_bytes_v1(crop_manifest)).hexdigest()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    result = base.build_investment_securities_activity_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    replayed = base.validate_investment_securities_activity_8bank_codex_verified_mapping_replay_v1(
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
        build_annual_2025_investment_securities_activity_pixel_review_blueprint_v1()
        if args.write_review
        else build_live_annual_2025_investment_securities_activity_8bank_codex_verified_mapping_v1()
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes_v1(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
