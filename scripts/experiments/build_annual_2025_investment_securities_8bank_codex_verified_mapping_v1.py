"""Verify investment-securities disclosures in eight annual-2025 bank PDFs.

The annual profile reuses the bank-blind complete-PDF variant graph.  It binds
the eight unique regions to visible pixels, fresh VietOCR semantic anchors,
PaddleOCR6 numeric challengers, exact annual periods, units, accounting
equations and the live TM schema.  Source rows that combine concepts are kept
as one source value and are mapped or aggregated only under an explicitly
approved combined semantic; they are never split into invented components.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
)

__all__ = [
    "Annual2025InvestmentSecurities8BankError",
    "build_annual_2025_investment_securities_pixel_review_blueprint_v1",
    "build_live_annual_2025_investment_securities_8bank_codex_verified_mapping_v1",
    "validate_annual_2025_investment_securities_8bank_codex_verified_mapping_replay_v1",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_INVESTMENT_SECURITIES_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_INVESTMENT_SECURITIES_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_INVESTMENT_SECURITIES_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025is8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_INVESTMENT_SECURITIES_CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025is8bcv1:pixel-review:"
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0121-annual-2025-investment-securities-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0121-annual-2025-investment-securities-8bank-codex-verified-mapping-v1.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_SCAN_ID = "isfdsv1:scan:51d4135dc7529576a427d8e035e31dbea0110b83e605b093b516099985bdb57e"
EXPECTED_REVIEW_SHA256 = "e93aef874b462348d0da21e8a88cd23a787e35f81274b568029889c66bb94f17"
EXPECTED_DOCUMENT_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")

_EXPECTED_IDS = {
    "ACB": {807, 808, 809, 815, 816, 825, 827, 831, 832, 848},
    "MBB": {806, 807, 808, 809, 824, 825, 826, 827, 831, 832, 833, 848, 849, 851, 852},
    "VPB": {806, 807, 5740, 808, 809, 812, 815, 824, 825, 826, 827, 854, 860},
    "HDB": {806, 807, 808, 809, 812, 815, 824, 825, 827, 828, 830, 831, 833, 849, 851},
    "VCB": {807, 808, 810, 824, 831, 832, 833, 834, 848, 849, 851, 852, 854},
    "CTG": {
        806,
        807,
        808,
        809,
        812,
        815,
        824,
        825,
        827,
        828,
        831,
        832,
        833,
        848,
        849,
        852,
        854,
        860,
        861,
    },
    "BID": {
        806,
        807,
        808,
        809,
        812,
        814,
        815,
        816,
        825,
        826,
        827,
        828,
        830,
        831,
        832,
        833,
        848,
        849,
        851,
        852,
        854,
    },
    "VIB": {807, 808, 809, 824, 833, 848},
}

_CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "GENERIC_INVESTMENT_SECURITIES_WHOLE_PDF_UNIQUENESS_EXPLICIT_OR_IMPLICIT_"
    "OWNER_AFS_HTM_PROVISION_QUALITY_VAMC_VISIBLE_PIXEL_PPOCRV6_NUMERIC_"
    "CHALLENGER_EXACT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "dash_zero_requires_visible_pixel": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "independent_pdf_pixel_and_ppocrv6_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_eight_unique_annual_investment_regions": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "quality_listing_or_provision_movement_double_count_authority": False,
    "source_combined_rows_split_without_printed_values": False,
    "text_similarity_alone_used_for_mapping": False,
}
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_coerced_to_zero": False,
    "dash_coerced_to_zero_only_when_visible_in_pdf": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gross_and_net_rows_conflated": False,
    "mapping_decided_by_text_similarity_alone": False,
    "source_order_and_cluster_boundaries_required": True,
    "visible_pdf_pixels_and_ppocrv6_used_for_numeric_truth": True,
    "whole_pdf_uniqueness_replayed": True,
}


class Annual2025InvestmentSecurities8BankError(ValueError):
    """The annual investment graph, pixels, numbers or schema drifted."""


def _error(message: str) -> Annual2025InvestmentSecurities8BankError:
    return Annual2025InvestmentSecurities8BankError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    line = base._line
    dash = base._dash
    row = base._row
    period = base._period
    page = base._page_review
    boundary = base._boundary
    equation = base._equation_spec
    document = base._base_document

    acb = "0d2ec1abcde0cb6cf6d4bb7acd44680e0ab261581ddebb56b1534ca6706feb4d"
    mbb54 = "bff8e9dbff90c73a720eb7599a481e61a264a67dcc16b838404983a8c2c478a6"
    mbb55 = "8360c45da95547a3938a9d56ee42142ee4cd18e3c21d8d15745609140b664b63"
    vpb50 = "8874cc96dc62fd7cbdb8f35243c8e1241fb1d075d01f2f879687aa55d54b60ee"
    vpb51 = "baba328ae6c72862624eecd0a47fdd9c57d265e503921c70e47b8f1c90622d96"
    vpb52 = "ee6ed891466217af7ffcc1cf08fae4594d9255f75a50d887e144413654ec4edc"
    hdb = "548718289b9148db34e90938512495b68f4f2fbed7395d66bae3b25dbc4fd690"
    vcb42 = "4dda359f77705a511f06c434b7d653341a92a53e9779f190cb8dcd4ca003f137"
    vcb43 = "2449fb562202e6468063f29e33dfae84283e995e9137a5d64503a29390a1385b"
    ctg45 = "365b078a425b1c6a22c64669978af04f777fca5f9e5b6301ce703f179d285484"
    ctg46 = "6fd0866c098c33f33d4227444bbb7ec1bf161f154dc1a104f5acbaaa3ffd92e2"
    bid = "6c18364b284ed947a3b30ad5103a17d756233b7a72e8a1668a824019d2f54b8c"
    vib40 = "31e7c3a92bf012ed0aa0da07f9b2e70d89555d166c0afb745aca8e5c199b07ce"
    vib41 = "71465bcc4b666c7867d5ac4df0157e181936b5df1eeb44eca1402e3f2cc7930e"

    docs: dict[str, dict[str, Any]] = {}
    docs["ACB"] = document(
        "ACB",
        boundary(
            (52, 5, "CHỨNG KHOÁN ĐẦU TƯ"),
            (53, 42, "12.171.766"),
            (54, 5, "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        ),
        "AFS_AND_HTM_WITH_NET_AFS_TOTAL_AND_OPTIONAL_SOURCE_DASHES",
        [
            page(
                52,
                acb,
                "ROWS_BY_BRANCH_COLUMNS_BY_ANNUAL_DATE",
                period(
                    "2025-12-31",
                    [(8, "31.12.2025")],
                    (10, "Triệu VND"),
                    "2024-12-31",
                    [(9, "31.12.2024")],
                    (11, "Triệu VND"),
                ),
                [
                    row(
                        "AFS_GOVERNMENT",
                        807,
                        14,
                        "Chứng khoán Chính phủ (i)",
                        line(15, "39.410.741"),
                        line(16, "32.850.096"),
                    ),
                    row(
                        "AFS_TCTD",
                        808,
                        17,
                        "Chứng khoán nợ do các TCTD khác trong nước phát hành (i)",
                        line(18, "91.803.872"),
                        line(19, "76.055.720"),
                    ),
                    row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        20,
                        "Chứng khoán nợ do các TCKT trong nước phát hành",
                        line(21, "1.500.000"),
                        dash([1485, 666, 1538, 699]),
                    ),
                    row(
                        "AFS_EQUITY_DOMESTIC_TCKT",
                        815,
                        23,
                        "Chứng khoán vốn do các TCKT trong nước phát hành",
                        dash([1280, 750, 1338, 786]),
                        line(24, "12.661"),
                    ),
                    row(
                        "AFS_EQUITY_FOREIGN",
                        816,
                        25,
                        "Chứng khoán vốn nước ngoài",
                        line(26, "64.226"),
                        dash([1484, 781, 1538, 818]),
                    ),
                    row(
                        "AFS_PROVISION",
                        825,
                        27,
                        "Dự phòng rủi ro chứng khoán sẵn sàng để bán",
                        line(29, "(11.250)"),
                        dash([1484, 878, 1538, 917]),
                    ),
                    row(
                        "AFS_GENERAL_PROVISION",
                        827,
                        28,
                        "Dự phòng chung",
                        line(29, "(11.250)"),
                        dash([1484, 878, 1538, 917]),
                    ),
                    row(
                        "HTM_GOVERNMENT",
                        831,
                        36,
                        "Chứng khoán Chính phủ (i)",
                        line(37, "10.896.527"),
                        line(38, "11.171.766"),
                    ),
                    row(
                        "HTM_TCTD",
                        832,
                        39,
                        "Chứng khoán nợ do các TCTD khác trong nước phát hành (i)",
                        line(40, "500.000"),
                        line(41, "1.000.000"),
                    ),
                    row(
                        "HTM_GROSS",
                        848,
                        42,
                        "Tổng chứng khoán đầu tư giữ đến ngày đáo hạn",
                        line(44, "11.396.527"),
                        line(45, "12.171.766"),
                    ),
                ],
            )
        ],
        [
            equation(
                "ACB_CURRENT_AFS_NET",
                52,
                acb,
                [
                    line(15, "39.410.741"),
                    line(18, "91.803.872"),
                    line(21, "1.500.000"),
                    dash([1280, 750, 1338, 786]),
                    line(26, "64.226"),
                    line(29, "(11.250)"),
                ],
                line(31, "132.767.589"),
            ),
            equation(
                "ACB_COMPARATIVE_AFS_NET",
                52,
                acb,
                [
                    line(16, "32.850.096"),
                    line(19, "76.055.720"),
                    dash([1485, 666, 1538, 699]),
                    line(24, "12.661"),
                    dash([1484, 781, 1538, 818]),
                    dash([1484, 878, 1538, 917]),
                ],
                line(32, "108.918.477"),
            ),
            equation(
                "ACB_CURRENT_HTM_GROSS",
                52,
                acb,
                [line(37, "10.896.527"), line(40, "500.000")],
                line(44, "11.396.527"),
            ),
            equation(
                "ACB_COMPARATIVE_HTM_GROSS",
                52,
                acb,
                [line(38, "11.171.766"), line(41, "1.000.000")],
                line(45, "12.171.766"),
            ),
        ],
    )

    docs["MBB"] = document(
        "MBB",
        boundary(
            (54, 37, "CHỨNG KHOÁN ĐẦU TƯ"), (56, 64, "483.083"), (57, 10, "GÓP VỐN, ĐẦU TƯ DÀI HẠN")
        ),
        "FOUR_PAGE_FAMILY_AFS_HTM_AND_PROVISION_MOVEMENT",
        [
            page(
                54,
                mbb54,
                "AFS_DIRECT_AND_COMBINED_ISSUER_ROWS",
                period(
                    "2025-12-31",
                    [(40, "31/12/2025")],
                    (42, "triệu đồng"),
                    "2024-12-31",
                    [(41, "31/12/2024")],
                    (43, "triệu đồng"),
                ),
                [
                    row(
                        "AFS_DEBT",
                        806,
                        44,
                        "Chứng khoán nợ",
                        line(54, "221.512.464"),
                        line(55, "205.507.956"),
                    ),
                    row(
                        "AFS_GOVERNMENT",
                        807,
                        45,
                        "Trái phiếu Chính phủ và trái phiếu Chính phủ bảo lãnh",
                        line(46, "63.880.125"),
                        line(47, "70.456.485"),
                    ),
                    row(
                        "AFS_TCTD",
                        808,
                        48,
                        "Chứng khoán nợ do các TCTD trong nước phát hành",
                        line(49, "135.852.313"),
                        line(50, "103.565.847"),
                    ),
                    row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        51,
                        "Trái phiếu do các TCKT trong nước phát hành",
                        line(52, "21.780.026"),
                        line(53, "31.485.624"),
                    ),
                    row(
                        "AFS_GROSS",
                        824,
                        39,
                        "Chứng khoán đầu tư sẵn sàng để bán",
                        line(54, "221.512.464"),
                        line(55, "205.507.956"),
                    ),
                ],
            ),
            page(
                55,
                mbb55,
                "HTM_AND_PROVISION_ROWS",
                period(
                    "2025-12-31",
                    [(36, "31/12/2025")],
                    (39, "triệu đồng"),
                    "2024-12-31",
                    [(37, "31/12/2024")],
                    (40, "triệu đồng"),
                ),
                [
                    row(
                        "AFS_PROVISION",
                        825,
                        42,
                        "Dự phòng rủi ro chứng khoán đầu tư sẵn sàng để bán",
                        line(43, "163.351"),
                        line(44, "242.638"),
                    ),
                    row(
                        "AFS_GENERAL_PROVISION",
                        827,
                        46,
                        "Dự phòng chung chứng khoán đầu tư sẵn sàng để bán",
                        line(47, "163.351"),
                        line(48, "232.291"),
                    ),
                    row(
                        "AFS_PRICE_PROVISION",
                        826,
                        50,
                        "Dự phòng giảm giá chứng khoán đầu tư sẵn sàng để bán",
                        dash([1190, 1210, 1268, 1252]),
                        line(51, "10.347"),
                    ),
                    row(
                        "HTM_GOVERNMENT",
                        831,
                        18,
                        "Trái phiếu Chính phủ",
                        line(19, "269.099"),
                        line(20, "269.654"),
                    ),
                    row(
                        "HTM_TCTD",
                        832,
                        21,
                        "Chứng khoán nợ do các TCTD trong nước phát hành",
                        line(22, "2.395.896"),
                        line(23, "2.385.376"),
                    ),
                    row(
                        "HTM_DOMESTIC_TCKT",
                        833,
                        24,
                        "Trái phiếu do các TCKT trong nước phát hành",
                        line(25, "1.630.130"),
                        line(26, "1.957.474"),
                    ),
                    row(
                        "HTM_GROSS",
                        848,
                        12,
                        "Chứng khoán đầu tư giữ đến ngày đáo hạn",
                        line(27, "4.295.125"),
                        line(28, "4.612.504"),
                    ),
                    row(
                        "HTM_PROVISION",
                        849,
                        53,
                        "Dự phòng rủi ro chứng khoán đầu tư giữ đến ngày đáo hạn",
                        line(55, "69.388"),
                        line(56, "240.445"),
                    ),
                    row(
                        "HTM_GENERAL_PROVISION",
                        851,
                        57,
                        "Dự phòng chung",
                        line(58, "19.388"),
                        line(59, "13.810"),
                    ),
                    row(
                        "HTM_SPECIFIC_PROVISION",
                        852,
                        60,
                        "Dự phòng cụ thể",
                        line(61, "50.000"),
                        line(62, "226.635"),
                    ),
                ],
            ),
        ],
        [
            equation(
                "MBB_CURRENT_AFS_GROSS",
                54,
                mbb54,
                [line(46, "63.880.125"), line(49, "135.852.313"), line(52, "21.780.026")],
                line(54, "221.512.464"),
            ),
            equation(
                "MBB_COMPARATIVE_AFS_GROSS",
                54,
                mbb54,
                [line(47, "70.456.485"), line(50, "103.565.847"), line(53, "31.485.624")],
                line(55, "205.507.956"),
            ),
            equation(
                "MBB_CURRENT_AFS_PROVISION",
                55,
                mbb55,
                [line(47, "163.351"), dash([1190, 1210, 1268, 1252])],
                line(43, "163.351"),
            ),
            equation(
                "MBB_COMPARATIVE_AFS_PROVISION",
                55,
                mbb55,
                [line(48, "232.291"), line(51, "10.347")],
                line(44, "242.638"),
            ),
            equation(
                "MBB_CURRENT_HTM_GROSS",
                55,
                mbb55,
                [line(19, "269.099"), line(22, "2.395.896"), line(25, "1.630.130")],
                line(27, "4.295.125"),
            ),
            equation(
                "MBB_COMPARATIVE_HTM_GROSS",
                55,
                mbb55,
                [line(20, "269.654"), line(23, "2.385.376"), line(26, "1.957.474")],
                line(28, "4.612.504"),
            ),
            equation(
                "MBB_CURRENT_HTM_PROVISION",
                55,
                mbb55,
                [line(58, "19.388"), line(61, "50.000")],
                line(55, "69.388"),
            ),
            equation(
                "MBB_COMPARATIVE_HTM_PROVISION",
                55,
                mbb55,
                [line(59, "13.810"), line(62, "226.635")],
                line(56, "240.445"),
            ),
        ],
    )

    docs["VPB"] = document(
        "VPB",
        boundary(
            (50, 5, "CHỨNG KHOÁN ĐẦU TƯ"),
            (52, 55, "17.053.399"),
            (52, 57, "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        ),
        "AFS_VAMC_PROVISION_AND_QUALITY_ACROSS_THREE_PAGES",
        [
            page(
                50,
                vpb50,
                "AFS_WITH_GOVERNMENT_GUARANTEE_SUBSET",
                period(
                    "2025-12-31",
                    [(8, "Ngày 31 tháng 12"), (11, "năm 2025")],
                    (13, "Triệu đồng"),
                    "2024-12-31",
                    [(9, "Ngày 31 tháng 12"), (12, "năm 2024")],
                    (14, "Triệu đồng"),
                ),
                [
                    row(
                        "AFS_DEBT",
                        806,
                        15,
                        "Chứng khoán nợ",
                        line(16, "63.730.573"),
                        line(17, "51.842.071"),
                    ),
                    row(
                        "AFS_GOVERNMENT",
                        807,
                        18,
                        "Chứng khoán Chính phủ, chính quyền địa phương",
                        line(19, "37.452.901"),
                        line(20, "33.571.973"),
                    ),
                    row(
                        "AFS_TCTD",
                        808,
                        21,
                        "Chứng khoán nợ do các tổ chức tín dụng khác trong nước phát hành",
                        line(22, "23.472.758"),
                        line(23, "10.303.355"),
                    ),
                    row(
                        "AFS_GOVERNMENT_GUARANTEED_SUBSET",
                        5740,
                        25,
                        "Trong đó: Trái phiếu được Chính phủ bảo lãnh",
                        line(26, "1.185.637"),
                        line(27, "1.216.699"),
                    ),
                    row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        28,
                        "Chứng khoán nợ do các tổ chức kinh tế trong nước phát hành",
                        line(29, "2.804.914"),
                        line(30, "7.966.743"),
                    ),
                    row(
                        "AFS_EQUITY",
                        812,
                        32,
                        "Chứng khoán vốn",
                        line(33, "732.357"),
                        line(34, "15.357"),
                    ),
                    row(
                        "AFS_EQUITY_DOMESTIC_TCKT",
                        815,
                        35,
                        "Chứng khoán vốn do các tổ chức kinh tế trong nước phát hành",
                        line(36, "732.357"),
                        line(37, "15.357"),
                    ),
                    row(
                        "AFS_GROSS",
                        824,
                        7,
                        "Chứng khoán đầu tư sẵn sàng để bán",
                        line(39, "64.462.930"),
                        line(40, "51.857.428"),
                    ),
                    row(
                        "AFS_PROVISION",
                        825,
                        41,
                        "Dự phòng rủi ro chứng khoán đầu tư sẵn sàng để bán",
                        line(43, "(28.864)"),
                        line(44, "(67.301)"),
                    ),
                    row(
                        "AFS_GENERAL_PROVISION",
                        827,
                        45,
                        "Dự phòng chung",
                        line(46, "(21.037)"),
                        line(47, "(59.751)"),
                    ),
                    row(
                        "AFS_PRICE_PROVISION",
                        826,
                        48,
                        "Dự phòng giảm giá",
                        line(49, "(7.827)"),
                        line(50, "(7.550)"),
                    ),
                ],
            ),
            page(
                51,
                vpb51,
                "VAMC_FACE_VALUE_WITH_CURRENT_DASH",
                period(
                    "2025-12-31",
                    [(8, "Ngày 31 tháng 12"), (11, "năm 2025")],
                    (13, "Triệu đồng"),
                    "2024-12-31",
                    [(9, "Ngày 31 tháng 12"), (12, "năm 2024")],
                    (14, "Triệu đồng"),
                ),
                [
                    row(
                        "VAMC_FACE_VALUE",
                        860,
                        15,
                        "Mệnh giá trái phiếu đặc biệt VAMC",
                        dash([1100, 600, 1195, 642]),
                        line(16, "992.927"),
                    ),
                ],
            ),
            page(
                52,
                vpb52,
                "QUALITY_ALTERNATE_VIEW_NOT_ADDED_TO_AFS",
                period(
                    "2025-12-31",
                    [(39, "Ngày 31 tháng 12"), (41, "năm 2025")],
                    (43, "Triệu đồng"),
                    "2024-12-31",
                    [(40, "Ngày 31 tháng 12"), (42, "năm 2024")],
                    (44, "Triệu đồng"),
                ),
                [
                    row(
                        "QUALITY_STANDARD",
                        854,
                        45,
                        "Nợ đủ tiêu chuẩn",
                        line(46, "25.092.035"),
                        line(47, "14.997.399"),
                    ),
                ],
            ),
        ],
        [
            equation(
                "VPB_CURRENT_AFS_DEBT",
                50,
                vpb50,
                [line(19, "37.452.901"), line(22, "23.472.758"), line(29, "2.804.914")],
                line(16, "63.730.573"),
            ),
            equation(
                "VPB_COMPARATIVE_AFS_DEBT",
                50,
                vpb50,
                [line(20, "33.571.973"), line(23, "10.303.355"), line(30, "7.966.743")],
                line(17, "51.842.071"),
            ),
            equation(
                "VPB_CURRENT_AFS_GROSS",
                50,
                vpb50,
                [line(16, "63.730.573"), line(33, "732.357")],
                line(39, "64.462.930"),
            ),
            equation(
                "VPB_COMPARATIVE_AFS_GROSS",
                50,
                vpb50,
                [line(17, "51.842.071"), line(34, "15.357")],
                line(40, "51.857.428"),
            ),
            equation(
                "VPB_CURRENT_AFS_PROVISION",
                50,
                vpb50,
                [line(46, "(21.037)"), line(49, "(7.827)")],
                line(43, "(28.864)"),
            ),
            equation(
                "VPB_COMPARATIVE_AFS_PROVISION",
                50,
                vpb50,
                [line(47, "(59.751)"), line(50, "(7.550)")],
                line(44, "(67.301)"),
            ),
            equation(
                "VPB_CURRENT_AFS_NET",
                50,
                vpb50,
                [line(39, "64.462.930"), line(43, "(28.864)")],
                line(51, "64.434.066"),
            ),
            equation(
                "VPB_COMPARATIVE_AFS_NET",
                50,
                vpb50,
                [line(40, "51.857.428"), line(44, "(67.301)")],
                line(52, "51.790.127"),
            ),
        ],
    )

    docs["HDB"] = document(
        "HDB",
        boundary(
            (39, 35, "CHỨNG KHOÁN ĐẦU TƯ"), (40, 139, "92.850"), (41, 8, "GÓP VỐN, ĐẦU TƯ DÀI HẠN")
        ),
        "AFS_HTM_RELATIVE_ANNUAL_AXES_WITH_OPTIONAL_EQUITY_AND_NHNN_BILL",
        [
            page(
                39,
                hdb,
                "AFS_THEN_HTM_ROWS",
                period(
                    "2025-12-31",
                    [(38, "Số cuối năm")],
                    (40, "Triệu VND"),
                    "2024-12-31",
                    [(39, "Số đầu năm")],
                    (41, "Triệu VND"),
                ),
                [
                    row(
                        "AFS_DEBT",
                        806,
                        42,
                        "Chứng khoán Nợ",
                        line(43, "72.904.811"),
                        line(44, "31.180.589"),
                    ),
                    row(
                        "AFS_GOVERNMENT",
                        807,
                        45,
                        "Chứng khoán Chính phủ",
                        line(46, "19.704.580"),
                        line(47, "18.783.841"),
                    ),
                    row(
                        "AFS_TCTD",
                        808,
                        48,
                        "Chứng khoán Nợ do các TCTD khác trong nước phát hành",
                        line(49, "36.288.479"),
                        line(50, "6.771.743"),
                    ),
                    row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        51,
                        "Chứng khoán Nợ do các TCKT trong nước phát hành",
                        line(52, "16.911.752"),
                        line(53, "5.625.005"),
                    ),
                    row(
                        "AFS_EQUITY",
                        812,
                        54,
                        "Chứng khoán Vốn",
                        dash([1135, 1344, 1225, 1378]),
                        line(55, "226.935"),
                    ),
                    row(
                        "AFS_EQUITY_DOMESTIC_TCKT",
                        815,
                        56,
                        "Chứng khoán Vốn do các TCKT trong nước phát hành",
                        dash([1135, 1378, 1225, 1412]),
                        line(57, "226.935"),
                    ),
                    row(
                        "AFS_GROSS",
                        824,
                        58,
                        "Chứng khoán đầu tư sẵn sàng để bán",
                        line(59, "72.904.811"),
                        line(60, "31.407.524"),
                    ),
                    row(
                        "AFS_PROVISION",
                        825,
                        61,
                        "Dự phòng rủi ro chứng khoán đầu tư sẵn sàng để bán",
                        line(62, "(126.838)"),
                        line(63, "(86.850)"),
                    ),
                    row(
                        "AFS_GENERAL_PROVISION",
                        827,
                        64,
                        "Dự phòng chung",
                        line(65, "(126.838)"),
                        line(66, "(41.850)"),
                    ),
                    row(
                        "AFS_SPECIFIC_PROVISION",
                        828,
                        67,
                        "Dự phòng cụ thể",
                        dash([1125, 1510, 1225, 1548]),
                        line(68, "(45.000)"),
                    ),
                    row(
                        "HTM_DEBT",
                        830,
                        78,
                        "Chứng khoán Nợ",
                        line(79, "4.039.836"),
                        line(80, "17.436.610"),
                    ),
                    row(
                        "HTM_DOMESTIC_TCKT",
                        833,
                        86,
                        "Chứng khoán Nợ do các TCKT trong nước phát hành",
                        line(87, "814.015"),
                        line(88, "800.020"),
                    ),
                    row(
                        "HTM_PROVISION",
                        849,
                        89,
                        "Dự phòng rủi ro chứng khoán đầu tư nắm giữ đến ngày đáo hạn",
                        line(90, "(6.105)"),
                        line(91, "(6.000)"),
                    ),
                    row(
                        "HTM_GENERAL_PROVISION",
                        851,
                        93,
                        "Dự phòng chung",
                        line(94, "(6.105)"),
                        line(95, "(6.000)"),
                    ),
                ],
            ),
        ],
        [
            equation(
                "HDB_CURRENT_AFS_DEBT",
                39,
                hdb,
                [line(46, "19.704.580"), line(49, "36.288.479"), line(52, "16.911.752")],
                line(43, "72.904.811"),
            ),
            equation(
                "HDB_COMPARATIVE_AFS_DEBT",
                39,
                hdb,
                [line(47, "18.783.841"), line(50, "6.771.743"), line(53, "5.625.005")],
                line(44, "31.180.589"),
            ),
            equation(
                "HDB_CURRENT_AFS_GROSS",
                39,
                hdb,
                [line(43, "72.904.811"), dash([1135, 1344, 1225, 1378])],
                line(59, "72.904.811"),
            ),
            equation(
                "HDB_COMPARATIVE_AFS_GROSS",
                39,
                hdb,
                [line(44, "31.180.589"), line(55, "226.935")],
                line(60, "31.407.524"),
            ),
            equation(
                "HDB_CURRENT_AFS_PROVISION",
                39,
                hdb,
                [line(65, "(126.838)"), dash([1125, 1510, 1225, 1548])],
                line(62, "(126.838)"),
            ),
            equation(
                "HDB_COMPARATIVE_AFS_PROVISION",
                39,
                hdb,
                [line(66, "(41.850)"), line(68, "(45.000)")],
                line(63, "(86.850)"),
            ),
            equation(
                "HDB_CURRENT_AFS_NET",
                39,
                hdb,
                [line(59, "72.904.811"), line(62, "(126.838)")],
                line(69, "72.777.973"),
            ),
            equation(
                "HDB_COMPARATIVE_AFS_NET",
                39,
                hdb,
                [line(60, "31.407.524"), line(63, "(86.850)")],
                line(70, "31.320.674"),
            ),
            equation(
                "HDB_CURRENT_HTM_DEBT",
                39,
                hdb,
                [dash([1135, 1780, 1222, 1815]), line(84, "3.225.821"), line(87, "814.015")],
                line(79, "4.039.836"),
            ),
            equation(
                "HDB_COMPARATIVE_HTM_DEBT",
                39,
                hdb,
                [line(82, "13.250.000"), line(85, "3.386.590"), line(88, "800.020")],
                line(80, "17.436.610"),
            ),
            equation(
                "HDB_CURRENT_HTM_NET",
                39,
                hdb,
                [line(79, "4.039.836"), line(90, "(6.105)")],
                line(96, "4.033.731"),
            ),
            equation(
                "HDB_COMPARATIVE_HTM_NET",
                39,
                hdb,
                [line(80, "17.436.610"), line(91, "(6.000)")],
                line(97, "17.430.610"),
            ),
        ],
    )

    docs["VCB"] = document(
        "VCB",
        boundary(
            (42, 8, "Chứng khoán đầu tư"),
            (43, 66, "76.958.971"),
            (44, 9, "Góp vốn, đầu tư dài hạn"),
        ),
        "SUMMARY_THEN_DETAILED_AFS_HTM_PROVISION_AND_QUALITY",
        [
            page(
                42,
                vcb42,
                "AFS_AND_HTM_TWO_DATE_COLUMNS",
                period(
                    "2025-12-31",
                    [(9, "31/12/2025")],
                    (11, "Triệu VND"),
                    "2024-12-31",
                    [(10, "31/12/2024")],
                    (12, "Triệu VND"),
                ),
                [
                    row(
                        "AFS_GOVERNMENT",
                        807,
                        30,
                        "Trái phiếu Chính phủ",
                        line(31, "60.984.052"),
                        line(32, "38.999.507"),
                    ),
                    row(
                        "AFS_TCTD",
                        808,
                        33,
                        "Chứng khoán nợ do các TCTD khác trong nước phát hành",
                        line(34, "77.174.749"),
                        line(35, "44.048.000"),
                    ),
                    row(
                        "AFS_FOREIGN",
                        810,
                        36,
                        "Chứng khoán nợ nước ngoài",
                        line(37, "4.922.016"),
                        line(38, "3.752.394"),
                    ),
                    row(
                        "AFS_GROSS",
                        824,
                        39,
                        "Tổng chứng khoán đầu tư sẵn sàng để bán",
                        line(40, "143.080.817"),
                        line(41, "86.799.901"),
                    ),
                    row(
                        "HTM_GOVERNMENT",
                        831,
                        49,
                        "Trái phiếu Chính phủ",
                        line(50, "11.688.254"),
                        line(51, "44.748.703"),
                    ),
                    row(
                        "HTM_TCTD",
                        832,
                        52,
                        "Chứng khoán nợ do các TCTD khác trong nước phát hành",
                        line(53, "1.252.443"),
                        line(54, "25.687.225"),
                    ),
                    row(
                        "HTM_DOMESTIC_TCKT",
                        833,
                        55,
                        "Chứng khoán nợ do các TCKT trong nước phát hành",
                        line(56, "7.524.850"),
                        line(57, "9.157.500"),
                    ),
                    row(
                        "HTM_FOREIGN",
                        834,
                        58,
                        "Chứng khoán nợ nước ngoài",
                        line(59, "1.919.415"),
                        line(60, "1.236.112"),
                    ),
                    row(
                        "HTM_GROSS",
                        848,
                        48,
                        "Chứng khoán đầu tư giữ đến ngày đáo hạn",
                        line(61, "22.384.962"),
                        line(62, "80.829.540"),
                    ),
                    row(
                        "HTM_PROVISION",
                        849,
                        63,
                        "Dự phòng rủi ro chứng khoán đầu tư giữ đến ngày đáo hạn",
                        line(64, "(3.361.615)"),
                        line(65, "(246.092)"),
                    ),
                ],
            ),
            page(
                43,
                vcb43,
                "HTM_PROVISION_COMPONENTS_AND_QUALITY",
                period(
                    "2025-12-31",
                    [(10, "31/12/2025")],
                    (12, "Triệu VND"),
                    "2024-12-31",
                    [(11, "31/12/2024")],
                    (13, "Triệu VND"),
                ),
                [
                    row(
                        "HTM_GENERAL_PROVISION",
                        851,
                        15,
                        "Dự phòng chung cho trái phiếu doanh nghiệp chưa niêm yết",
                        line(16, "54.742"),
                        line(17, "67.341"),
                    ),
                    row(
                        "HTM_SPECIFIC_PROVISION",
                        852,
                        18,
                        "Dự phòng cụ thể cho trái phiếu doanh nghiệp chưa niêm yết",
                        line(19, "3.306.873"),
                        line(20, "178.751"),
                    ),
                    row(
                        "QUALITY_STANDARD",
                        854,
                        58,
                        "Nợ đủ tiêu chuẩn",
                        line(59, "72.210.377"),
                        line(60, "76.780.220"),
                    ),
                ],
            ),
        ],
        [
            equation(
                "VCB_CURRENT_AFS_GROSS",
                42,
                vcb42,
                [line(31, "60.984.052"), line(34, "77.174.749"), line(37, "4.922.016")],
                line(40, "143.080.817"),
            ),
            equation(
                "VCB_COMPARATIVE_AFS_GROSS",
                42,
                vcb42,
                [line(32, "38.999.507"), line(35, "44.048.000"), line(38, "3.752.394")],
                line(41, "86.799.901"),
            ),
            equation(
                "VCB_CURRENT_HTM_GROSS",
                42,
                vcb42,
                [
                    line(50, "11.688.254"),
                    line(53, "1.252.443"),
                    line(56, "7.524.850"),
                    line(59, "1.919.415"),
                ],
                line(61, "22.384.962"),
            ),
            equation(
                "VCB_COMPARATIVE_HTM_GROSS",
                42,
                vcb42,
                [
                    line(51, "44.748.703"),
                    line(54, "25.687.225"),
                    line(57, "9.157.500"),
                    line(60, "1.236.112"),
                ],
                line(62, "80.829.540"),
            ),
            equation(
                "VCB_CURRENT_HTM_PROVISION",
                43,
                vcb43,
                [line(16, "54.742"), line(19, "3.306.873")],
                line(22, "3.361.615"),
            ),
            equation(
                "VCB_COMPARATIVE_HTM_PROVISION",
                43,
                vcb43,
                [line(17, "67.341"), line(20, "178.751")],
                line(23, "246.092"),
            ),
            equation(
                "VCB_CURRENT_HTM_NET",
                42,
                vcb42,
                [line(61, "22.384.962"), line(64, "(3.361.615)")],
                line(67, "19.023.347"),
            ),
            equation(
                "VCB_COMPARATIVE_HTM_NET",
                42,
                vcb42,
                [line(62, "80.829.540"), line(65, "(246.092)")],
                line(68, "80.583.448"),
            ),
            equation(
                "VCB_CURRENT_COMBINED_NET",
                42,
                vcb42,
                [line(40, "143.080.817"), line(67, "19.023.347")],
                line(20, "162.104.164"),
            ),
            equation(
                "VCB_COMPARATIVE_COMBINED_NET",
                42,
                vcb42,
                [line(41, "86.799.901"), line(68, "80.583.448")],
                line(21, "167.383.349"),
            ),
        ],
    )

    docs["CTG"] = document(
        "CTG",
        boundary(
            (45, 5, "CHỨNG KHOÁN ĐẦU TƯ"), (46, 90, "531.639"), (47, 5, "GÓP VỐN, ĐẦU TƯ DÀI HẠN")
        ),
        "AFS_HTM_VAMC_QUALITY_AND_PROVISION_MOVEMENT",
        [
            page(
                45,
                ctg45,
                "AFS_THEN_HTM_WITH_SEPARATE_VAMC",
                period(
                    "2025-12-31",
                    [(6, "31.12.2025")],
                    (8, "Triệu đồng"),
                    "2024-12-31",
                    [(7, "31.12.2024")],
                    (9, "Triệu đồng"),
                ),
                [
                    row(
                        "AFS_DEBT",
                        806,
                        43,
                        "Chứng khoán nợ",
                        line(44, "203.166.496"),
                        line(45, "188.180.862"),
                    ),
                    row(
                        "AFS_GOVERNMENT",
                        807,
                        46,
                        "Chứng khoán Chính phủ, chính quyền địa phương",
                        line(47, "101.533.661"),
                        line(48, "80.284.569"),
                    ),
                    row(
                        "AFS_TCTD",
                        808,
                        49,
                        "Chứng khoán nợ do các TCTD khác trong nước phát hành",
                        line(50, "99.697.917"),
                        line(51, "104.824.865"),
                    ),
                    row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        52,
                        "Chứng khoán nợ do các TCKT trong nước phát hành",
                        line(53, "1.934.918"),
                        line(54, "3.071.428"),
                    ),
                    row(
                        "AFS_EQUITY",
                        812,
                        55,
                        "Chứng khoán vốn",
                        line(56, "438.615"),
                        line(57, "376.615"),
                    ),
                    row(
                        "AFS_EQUITY_DOMESTIC_TCKT",
                        815,
                        58,
                        "Chứng khoán vốn do các TCKT trong nước phát hành",
                        line(59, "438.615"),
                        line(60, "376.615"),
                    ),
                    row(
                        "AFS_GROSS",
                        824,
                        38,
                        "Chứng khoán đầu tư sẵn sàng để bán",
                        line(61, "203.605.111"),
                        line(62, "188.557.477"),
                    ),
                    row(
                        "AFS_PROVISION",
                        825,
                        63,
                        "Dự phòng rủi ro chứng khoán đầu tư sẵn sàng để bán",
                        line(64, "(113.762)"),
                        line(65, "(134.036)"),
                    ),
                    row(
                        "AFS_GENERAL_PROVISION",
                        827,
                        66,
                        "Dự phòng chung",
                        line(67, "(13.762)"),
                        line(68, "(22.182)"),
                    ),
                    row(
                        "AFS_SPECIFIC_PROVISION",
                        828,
                        69,
                        "Dự phòng cụ thể",
                        line(70, "(100.000)"),
                        line(71, "(111.854)"),
                    ),
                    row(
                        "HTM_GOVERNMENT",
                        831,
                        84,
                        "Chứng khoán Chính phủ, chính quyền địa phương",
                        line(85, "183.000"),
                        line(86, "61.248"),
                    ),
                    row(
                        "HTM_TCTD",
                        832,
                        87,
                        "Chứng khoán nợ do các TCTD khác trong nước phát hành",
                        line(88, "8.000.000"),
                        line(89, "26.000.000"),
                    ),
                    row(
                        "HTM_DOMESTIC_TCKT",
                        833,
                        90,
                        "Chứng khoán nợ do các TCKT trong nước phát hành",
                        line(91, "386.748"),
                        line(92, "463.335"),
                    ),
                    row(
                        "HTM_GROSS",
                        848,
                        75,
                        "Chứng khoán đầu tư giữ đến ngày đáo hạn",
                        line(82, "8.569.748"),
                        line(83, "26.524.583"),
                    ),
                    row(
                        "HTM_PROVISION",
                        849,
                        93,
                        "Dự phòng rủi ro chứng khoán đầu tư giữ đến ngày đáo hạn",
                        line(95, "(386.748)"),
                        line(96, "(452.149)"),
                    ),
                    row(
                        "HTM_SPECIFIC_PROVISION",
                        852,
                        97,
                        "Dự phòng cụ thể",
                        line(98, "(386.748)"),
                        line(99, "(452.149)"),
                    ),
                ],
            ),
            page(
                46,
                ctg46,
                "VAMC_AND_QUALITY",
                period(
                    "2025-12-31",
                    [(8, "31.12.2025")],
                    (10, "Triệu đồng"),
                    "2024-12-31",
                    [(9, "31.12.2024")],
                    (11, "Triệu đồng"),
                ),
                [
                    row(
                        "VAMC_FACE_VALUE",
                        860,
                        12,
                        "Mệnh giá trái phiếu đặc biệt",
                        line(13, "237.170"),
                        line(14, "111.278"),
                    ),
                    row(
                        "VAMC_PROVISION",
                        861,
                        15,
                        "Dự phòng trái phiếu đặc biệt",
                        line(16, "(31.129)"),
                        dash([1410, 483, 1515, 522]),
                    ),
                    row(
                        "QUALITY_STANDARD",
                        854,
                        28,
                        "Nợ đủ tiêu chuẩn",
                        line(29, "93.814.932"),
                        line(30, "121.532.324"),
                    ),
                ],
            ),
        ],
        [
            equation(
                "CTG_CURRENT_AFS_DEBT",
                45,
                ctg45,
                [line(47, "101.533.661"), line(50, "99.697.917"), line(53, "1.934.918")],
                line(44, "203.166.496"),
            ),
            equation(
                "CTG_COMPARATIVE_AFS_DEBT",
                45,
                ctg45,
                [line(48, "80.284.569"), line(51, "104.824.865"), line(54, "3.071.428")],
                line(45, "188.180.862"),
            ),
            equation(
                "CTG_CURRENT_AFS_GROSS",
                45,
                ctg45,
                [line(44, "203.166.496"), line(56, "438.615")],
                line(61, "203.605.111"),
            ),
            equation(
                "CTG_COMPARATIVE_AFS_GROSS",
                45,
                ctg45,
                [line(45, "188.180.862"), line(57, "376.615")],
                line(62, "188.557.477"),
            ),
            equation(
                "CTG_CURRENT_AFS_PROVISION",
                45,
                ctg45,
                [line(67, "(13.762)"), line(70, "(100.000)")],
                line(64, "(113.762)"),
            ),
            equation(
                "CTG_COMPARATIVE_AFS_PROVISION",
                45,
                ctg45,
                [line(68, "(22.182)"), line(71, "(111.854)")],
                line(65, "(134.036)"),
            ),
            equation(
                "CTG_CURRENT_AFS_NET",
                45,
                ctg45,
                [line(61, "203.605.111"), line(64, "(113.762)")],
                line(72, "203.491.349"),
            ),
            equation(
                "CTG_COMPARATIVE_AFS_NET",
                45,
                ctg45,
                [line(62, "188.557.477"), line(65, "(134.036)")],
                line(73, "188.423.441"),
            ),
            equation(
                "CTG_CURRENT_HTM_GROSS",
                45,
                ctg45,
                [line(85, "183.000"), line(88, "8.000.000"), line(91, "386.748")],
                line(82, "8.569.748"),
            ),
            equation(
                "CTG_COMPARATIVE_HTM_GROSS",
                45,
                ctg45,
                [line(86, "61.248"), line(89, "26.000.000"), line(92, "463.335")],
                line(83, "26.524.583"),
            ),
            equation(
                "CTG_CURRENT_HTM_NET",
                45,
                ctg45,
                [line(82, "8.569.748"), line(95, "(386.748)")],
                line(100, "8.183.000"),
            ),
            equation(
                "CTG_COMPARATIVE_HTM_NET",
                45,
                ctg45,
                [line(83, "26.524.583"), line(96, "(452.149)")],
                line(101, "26.072.434"),
            ),
            equation(
                "CTG_CURRENT_VAMC_NET",
                46,
                ctg46,
                [line(13, "237.170"), line(16, "(31.129)")],
                line(17, "206.041"),
            ),
            equation(
                "CTG_COMPARATIVE_VAMC_NET",
                46,
                ctg46,
                [line(14, "111.278"), dash([1410, 483, 1515, 522])],
                line(18, "111.278"),
            ),
        ],
    )

    docs["BID"] = document(
        "BID",
        boundary(
            (44, 4, "CHỨNG KHOÁN ĐẦU TƯ"), (45, 44, "48.827"), (45, 46, "GÓP VỐN, ĐẦU TƯ DÀI HẠN")
        ),
        "AFS_HTM_QUALITY_AND_PROVISION_MOVEMENT_WITH_LOCAL_UNIT",
        [
            page(
                44,
                bid,
                "AFS_AND_HTM_WITH_TWO_DATE_COLUMNS",
                period(
                    "2025-12-31",
                    [(7, "Số cuối năm")],
                    (9, "Triệu VND"),
                    "2024-12-31",
                    [(8, "Số đầu năm")],
                    (10, "Triệu VND"),
                ),
                [
                    row(
                        "AFS_DEBT",
                        806,
                        11,
                        "Chứng khoán Nợ",
                        line(12, "171.829.517"),
                        line(13, "157.827.472"),
                    ),
                    row(
                        "AFS_GOVERNMENT",
                        807,
                        14,
                        "Chứng khoán Chính phủ",
                        line(15, "26.481.588"),
                        line(16, "25.345.755"),
                    ),
                    row(
                        "AFS_TCTD",
                        808,
                        17,
                        "Chứng khoán Nợ do các TCTD khác trong nước phát hành",
                        line(18, "145.347.929"),
                        line(19, "129.376.717"),
                    ),
                    row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        21,
                        "Chứng khoán Nợ do các TCKT trong nước phát hành",
                        dash([1140, 570, 1240, 604]),
                        line(22, "3.105.000"),
                    ),
                    row(
                        "AFS_EQUITY",
                        812,
                        23,
                        "Chứng khoán Vốn",
                        line(24, "52.919"),
                        line(25, "91.356"),
                    ),
                    row(
                        "AFS_EQUITY_TCTD",
                        814,
                        26,
                        "Chứng khoán Vốn do các TCTD khác trong nước phát hành",
                        line(27, "23.064"),
                        line(28, "23.064"),
                    ),
                    row(
                        "AFS_EQUITY_DOMESTIC_TCKT",
                        815,
                        30,
                        "Chứng khoán Vốn do các TCKT trong nước phát hành",
                        line(31, "23.491"),
                        line(32, "62.188"),
                    ),
                    row(
                        "AFS_EQUITY_FOREIGN",
                        816,
                        34,
                        "Chứng khoán Vốn nước ngoài",
                        line(35, "6.364"),
                        line(36, "6.104"),
                    ),
                    row(
                        "AFS_PROVISION",
                        825,
                        37,
                        "Dự phòng rủi ro chứng khoán đầu tư sẵn sàng để bán",
                        line(38, "(22.832)"),
                        line(39, "(204.481)"),
                    ),
                    row(
                        "AFS_PRICE_PROVISION",
                        826,
                        41,
                        "Dự phòng giảm giá",
                        line(42, "(22.832)"),
                        line(43, "(27.369)"),
                    ),
                    row(
                        "AFS_GENERAL_PROVISION",
                        827,
                        44,
                        "Dự phòng chung",
                        dash([1140, 941, 1240, 978]),
                        line(45, "(21.862)"),
                    ),
                    row(
                        "AFS_SPECIFIC_PROVISION",
                        828,
                        46,
                        "Dự phòng cụ thể",
                        dash([1140, 973, 1240, 1011]),
                        line(47, "(155.250)"),
                    ),
                    row(
                        "HTM_DEBT",
                        830,
                        56,
                        "Chứng khoán Nợ",
                        line(57, "113.629.492"),
                        line(58, "121.120.044"),
                    ),
                    row(
                        "HTM_GOVERNMENT",
                        831,
                        59,
                        "Chứng khoán Chính phủ",
                        line(60, "98.925.286"),
                        line(61, "105.526.937"),
                    ),
                    row(
                        "HTM_TCTD",
                        832,
                        62,
                        "Chứng khoán Nợ do các TCTD khác trong nước phát hành",
                        line(63, "11.238.206"),
                        line(64, "13.526.349"),
                    ),
                    row(
                        "HTM_DOMESTIC_TCKT",
                        833,
                        68,
                        "Chứng khoán Nợ do các TCKT trong nước phát hành",
                        line(69, "3.466.000"),
                        line(70, "2.066.758"),
                    ),
                    row(
                        "HTM_GROSS",
                        848,
                        51,
                        "Chứng khoán đầu tư giữ đến ngày đáo hạn",
                        line(57, "113.629.492"),
                        line(58, "121.120.044"),
                    ),
                    row(
                        "HTM_PROVISION",
                        849,
                        71,
                        "Dự phòng rủi ro chứng khoán đầu tư giữ đến ngày đáo hạn",
                        line(72, "(25.995)"),
                        line(73, "(996.283)"),
                    ),
                    row(
                        "HTM_GENERAL_PROVISION",
                        851,
                        75,
                        "Dự phòng chung",
                        line(76, "(25.995)"),
                        line(77, "(9.525)"),
                    ),
                    row(
                        "HTM_SPECIFIC_PROVISION",
                        852,
                        78,
                        "Dự phòng cụ thể",
                        dash([1135, 1552, 1242, 1590]),
                        line(79, "(986.758)"),
                    ),
                    row(
                        "QUALITY_STANDARD",
                        854,
                        92,
                        "Nợ đủ tiêu chuẩn",
                        line(93, "149.670.316"),
                        line(95, "129.430.000"),
                    ),
                ],
            ),
        ],
        [
            equation(
                "BID_CURRENT_AFS_DEBT",
                44,
                bid,
                [line(15, "26.481.588"), line(18, "145.347.929"), dash([1140, 570, 1240, 604])],
                line(12, "171.829.517"),
            ),
            equation(
                "BID_COMPARATIVE_AFS_DEBT",
                44,
                bid,
                [line(16, "25.345.755"), line(19, "129.376.717"), line(22, "3.105.000")],
                line(13, "157.827.472"),
            ),
            equation(
                "BID_CURRENT_AFS_EQUITY",
                44,
                bid,
                [line(27, "23.064"), line(31, "23.491"), line(35, "6.364")],
                line(24, "52.919"),
            ),
            equation(
                "BID_COMPARATIVE_AFS_EQUITY",
                44,
                bid,
                [line(28, "23.064"), line(32, "62.188"), line(36, "6.104")],
                line(25, "91.356"),
            ),
            equation(
                "BID_CURRENT_AFS_PROVISION",
                44,
                bid,
                [line(42, "(22.832)"), dash([1140, 941, 1240, 978]), dash([1140, 973, 1240, 1011])],
                line(38, "(22.832)"),
            ),
            equation(
                "BID_COMPARATIVE_AFS_PROVISION",
                44,
                bid,
                [line(43, "(27.369)"), line(45, "(21.862)"), line(47, "(155.250)")],
                line(39, "(204.481)"),
            ),
            equation(
                "BID_CURRENT_AFS_NET",
                44,
                bid,
                [line(12, "171.829.517"), line(24, "52.919"), line(38, "(22.832)")],
                line(48, "171.859.604"),
            ),
            equation(
                "BID_COMPARATIVE_AFS_NET",
                44,
                bid,
                [line(13, "157.827.472"), line(25, "91.356"), line(39, "(204.481)")],
                line(49, "157.714.347"),
            ),
            equation(
                "BID_CURRENT_HTM_GROSS",
                44,
                bid,
                [line(60, "98.925.286"), line(63, "11.238.206"), line(69, "3.466.000")],
                line(57, "113.629.492"),
            ),
            equation(
                "BID_COMPARATIVE_HTM_GROSS",
                44,
                bid,
                [line(61, "105.526.937"), line(64, "13.526.349"), line(70, "2.066.758")],
                line(58, "121.120.044"),
            ),
            equation(
                "BID_CURRENT_HTM_PROVISION",
                44,
                bid,
                [line(76, "(25.995)"), dash([1135, 1552, 1242, 1590])],
                line(72, "(25.995)"),
            ),
            equation(
                "BID_COMPARATIVE_HTM_PROVISION",
                44,
                bid,
                [line(77, "(9.525)"), line(79, "(986.758)")],
                line(73, "(996.283)"),
            ),
            equation(
                "BID_CURRENT_HTM_NET",
                44,
                bid,
                [line(57, "113.629.492"), line(72, "(25.995)")],
                line(80, "113.603.497"),
            ),
            equation(
                "BID_COMPARATIVE_HTM_NET",
                44,
                bid,
                [line(58, "121.120.044"), line(73, "(996.283)")],
                line(81, "120.123.761"),
            ),
        ],
    )

    docs["VIB"] = document(
        "VIB",
        boundary(
            (40, 49, "CHỨNG KHOÁN ĐẦU TƯ SẴN SÀNG ĐỂ BÁN"),
            (41, 27, "43.880"),
            (41, 29, "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        ),
        "IMPLICIT_AFS_OWNER_WITH_CONTROLLED_TCTD_AGGREGATION_AND_HTM",
        [
            page(
                40,
                vib40,
                "AFS_COMPONENT_ROWS",
                period(
                    "2025-12-31",
                    [(51, "31/12/2025")],
                    (53, "triệu đồng"),
                    "2024-12-31",
                    [(52, "31/12/2024")],
                    (54, "triệu đồng"),
                ),
                [
                    row(
                        "AFS_GOVERNMENT",
                        807,
                        56,
                        "Trái phiếu Chính phủ",
                        line(57, "10.793.007"),
                        line(58, "9.933.479"),
                    ),
                    row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        66,
                        "Trái phiếu do các TCKT trong nước phát hành",
                        dash([1135, 1810, 1225, 1850]),
                        line(67, "550.000"),
                    ),
                    row(
                        "AFS_GROSS",
                        824,
                        49,
                        "CHỨNG KHOÁN ĐẦU TƯ SẴN SÀNG ĐỂ BÁN",
                        line(68, "51.149.531"),
                        line(69, "50.345.812"),
                    ),
                ],
            ),
            page(
                41,
                vib41,
                "HTM_SINGLE_DOMESTIC_TCKT_ROW",
                period(
                    "2025-12-31",
                    [(6, "31/12/2025")],
                    (8, "triệu đồng"),
                    "2024-12-31",
                    [(7, "31/12/2024")],
                    (9, "triệu đồng"),
                ),
                [
                    row(
                        "HTM_DOMESTIC_TCKT",
                        833,
                        11,
                        "Trái phiếu do Công ty TNHH Mua bán nợ Việt Nam phát hành",
                        dash([1160, 454, 1272, 493]),
                        line(10, "42.380"),
                    ),
                    row(
                        "HTM_GROSS",
                        848,
                        5,
                        "CHỨNG KHOÁN ĐẦU TƯ GIỮ ĐẾN NGÀY ĐÁO HẠN",
                        dash([1160, 454, 1272, 493]),
                        line(10, "42.380"),
                    ),
                ],
            ),
        ],
        [
            equation(
                "VIB_CURRENT_AFS_GROSS",
                40,
                vib40,
                [
                    line(57, "10.793.007"),
                    line(60, "12.104.102"),
                    line(64, "28.252.422"),
                    dash([1135, 1810, 1225, 1850]),
                ],
                line(68, "51.149.531"),
            ),
            equation(
                "VIB_COMPARATIVE_AFS_GROSS",
                40,
                vib40,
                [
                    line(58, "9.933.479"),
                    line(61, "12.712.080"),
                    line(65, "27.150.253"),
                    line(67, "550.000"),
                ],
                line(69, "50.345.812"),
            ),
        ],
    )
    return [docs[code] for code in EXPECTED_DOCUMENT_ORDER]


def _install_controlled_aggregations(base: ModuleType) -> None:
    original_trial = base._trial

    def annual_trial(
        code: str,
        ordinal: int,
        review_document: Mapping[str, Any],
        scan_trial: Mapping[str, Any],
        semantic_index: Mapping[str, Any],
        crop_manifest: Mapping[str, Any],
        schema_bindings: Mapping[int, Mapping[str, Any]],
    ) -> dict[str, Any]:
        trial = original_trial(
            code,
            ordinal,
            review_document,
            scan_trial,
            semantic_index,
            crop_manifest,
            schema_bindings,
        )
        if code not in {"HDB", "VIB"}:
            return trial
        semantic_document = base.support._document(
            semantic_index["documents"], code, "semantic index"
        )
        manifest_document = base.support._document(
            crop_manifest["documents"], code, "crop manifest"
        )
        if code == "HDB":
            page_sequence = 39
            render_sha = "548718289b9148db34e90938512495b68f4f2fbed7395d66bae3b25dbc4fd690"
            report_norm_id = 831
            aggregation = "SUM_OF_NHNN_BILL_AND_GOVERNMENT_SECURITIES_ROWS_PER_PERIOD"
            source_status = "AGGREGATED_NHNN_BILL_AND_GOVERNMENT_SECURITIES_VALUES"
            period_specs = (
                (
                    "CURRENT",
                    (base._dash([1135, 1780, 1222, 1815]), base._line(84, "3.225.821")),
                ),
                (
                    "COMPARATIVE",
                    (base._line(82, "13.250.000"), base._line(85, "3.386.590")),
                ),
            )
            label_specs = (
                base._line(81, "Tín phiếu NHNN"),
                base._line(83, "Chứng khoán Chính phủ"),
            )
        else:
            page_sequence = 40
            render_sha = "31e7c3a92bf012ed0aa0da07f9b2e70d89555d166c0afb745aca8e5c199b07ce"
            report_norm_id = 808
            aggregation = "SUM_OF_TCTD_BOND_AND_CERTIFICATE_ROWS_PER_PERIOD"
            source_status = "AGGREGATED_TWO_VISIBLE_TCTD_VALUES"
            period_specs = (
                ("CURRENT", (base._line(60, "12.104.102"), base._line(64, "28.252.422"))),
                (
                    "COMPARATIVE",
                    (base._line(61, "12.712.080"), base._line(65, "27.150.253")),
                ),
            )
            label_specs = (
                base._line(59, "Trái phiếu do các TCTD khác trong nước phát hành"),
                base._line(63, "Chứng chỉ tiền gửi do các TCTD khác trong nước phát hành"),
            )
        periods = []
        for period_role, specs in period_specs:
            components = [
                base.support._money_evidence(
                    semantic_document,
                    manifest_document,
                    page_sequence,
                    spec,
                    render_sha,
                )
                for spec in specs
            ]
            periods.append(
                {
                    "component_source_values": components,
                    "normalized_value": sum(item["normalized_value"] for item in components),
                    "period_role": period_role,
                    "source_cell_status": source_status,
                }
            )
        trial["verified_mappings"].append(
            {
                **canonical_clone_v1(schema_bindings[report_norm_id]),
                "aggregation": aggregation,
                "component_source_labels": [
                    base.support._label_evidence(
                        semantic_document,
                        manifest_document,
                        page_sequence,
                        spec,
                        render_sha,
                    )
                    for spec in label_specs
                ],
                "source_values": periods,
                "status": "VERIFIED_BY_CODEX",
            }
        )
        trial["verified_mappings"].sort(key=lambda item: item["report_norm_id"])
        return trial

    base._trial = annual_trial


def _base() -> ModuleType:
    base = _load_module(
        "annual_2025_investment_securities_base_v1",
        "scripts/experiments/build_investment_securities_8bank_codex_verified_mapping_v1.py",
    )
    numeric = _load_module(
        "annual_2025_investment_numeric_challenger_v1",
        "scripts/experiments/build_annual_2025_purchased_debt_8bank_codex_verified_mapping_v1.py",
    )
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.CLAIM_BOUNDARY = _CLAIM_BOUNDARY
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base.REVIEW_SHA256 = EXPECTED_REVIEW_SHA256
    base._RESULT_STATE = RESULT_STATE
    base._RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base._REVIEW_STATE = REVIEW_STATE
    base._REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base._REVIEW_RUN_ID = "annual-2025-investment-securities-eight-bank-pixel-review-2026-08-17"
    base.scanner.MATCHER_VARIANT_PROFILE = "ANNUAL_2025_V1"
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    base._REVIEW_SAFETY = canonical_clone_v1(_REVIEW_SAFETY)
    base._EXPECTED_IDS = {code: set(ids) for code, ids in _EXPECTED_IDS.items()}
    base._review_documents = lambda: _review_documents(base)
    numeric._install_primary_numeric_challenger(base.support)
    _install_controlled_aggregations(base)
    return base


def build_annual_2025_investment_securities_pixel_review_blueprint_v1() -> dict[str, Any]:
    """Return the fixed independent annual visible-page review."""

    return _base()._review_blueprint()


def build_live_annual_2025_investment_securities_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    """Replay every fixed annual input and build the bounded result."""

    try:
        return _base().build_live_investment_securities_8bank_codex_verified_mapping_v1()
    except Annual2025InvestmentSecurities8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def validate_annual_2025_investment_securities_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild the annual investment-securities result."""

    try:
        return _base().validate_investment_securities_8bank_codex_verified_mapping_replay_v1(value)
    except Annual2025InvestmentSecurities8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        REVIEW_PATH.write_bytes(
            canonical_json_bytes_v1(
                build_annual_2025_investment_securities_pixel_review_blueprint_v1()
            )
        )
        return 0
    result = build_live_annual_2025_investment_securities_8bank_codex_verified_mapping_v1()
    if args.verify:
        persisted = json.loads((PROJECT_ROOT / RESULT_PATH).read_text(encoding="utf-8"))
        validate_annual_2025_investment_securities_8bank_codex_verified_mapping_replay_v1(persisted)
        return 0
    if args.write_result:
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
