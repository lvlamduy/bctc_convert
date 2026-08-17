#!/usr/bin/env python3
"""Verify annual-2025 capital-and-funds balances across eight banks."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_CAPITAL_AND_FUNDS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_CAPITAL_AND_FUNDS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_CAPITAL_AND_FUNDS_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025caf8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_CAPITAL_AND_FUNDS_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025caf8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0133"
STRUCTURE_SCAN_STATE = "ANNUAL_2025_CAPITAL_AND_FUNDS_SCAN_COMPLETE"
FAMILY_END_DISPLAY_ORDER = 672
REVIEW_PATH = Path(
    "docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json"
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
    "a2025caffdsv1:scan:146159e597cf9aed4a3adb86fdfcc83a71ee78c474adb37fb89023115dc8d32a"
)

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_AND_"
    "GEOMETRY_SELECTED_ROTATED_VIETOCR_BANK_BLIND_CAPITAL_FUNDS_OWNER_"
    "OPTIONAL_CHANGE_HEADING_DYNAMIC_BALANCE_DATES_EQUITY_COLUMNS_VISIBLE_"
    "PIXELS_UPSTREAM_PPOCRV6_ACCOUNTING_AND_LIVE_TM_SCHEMA_FIVE_NUMERIC_"
    "READABLE_TABLES_THREE_ROTATED_TABLES_STRUCTURE_ONLY_NO_EXPORT_AUTHORITY"
)
_REVIEW_SAFETY = {
    "bank_filename_note_page_or_year_used_as_graph_rule": False,
    "fresh_or_rotated_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "optional_equity_columns_required_in_every_bank": False,
    "rotated_numeric_rows_promoted_without_independent_challenger": False,
    "source_subtotals_and_children_double_counted": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_page_or_year_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "independent_pdf_pixel_and_upstream_ppocrv6_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_five_source_numeric_readable_tables": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reporting_period_dates_derived_from_pdf": True,
    "rotated_rescue_used_for_semantic_structure_only": True,
    "source_numeric_challenger_and_accounting_closure_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_retained": True,
}
_SCHEMA_EXPECTED = {
    1128: ("Vốn và các quỹ", 560, 646),
    5984: ("Vốn điều lệ của Ngân hàng", 1128, 649),
    6011: ("Thặng dư vốn cổ phần", 1128, 650),
    6012: ("Vốn khác", 1128, 651),
    6013: ("Quỹ dự trữ bổ sung vốn điều lệ", 1128, 652),
    6014: ("Quỹ dự phòng tài chính", 1128, 653),
    6015: ("Quỹ khác", 1128, 654),
    6016: ("Chênh lệch tỷ giá hối đoái", 1128, 655),
    6017: ("Lợi nhuận chưa phân phối", 1128, 656),
    6018: ("Lợi ích cổ đông không kiểm soát", 1128, 657),
    1129: ("Số dư đầu kỳ", 1128, 658),
    6019: ("Trích lập/Tăng", 1128, 659),
    6020: ("Sử dụng/Giảm", 1128, 667),
    1141: ("Số dư cuối kỳ", 1128, 672),
}
_EXPECTED_IDS = {
    "ACB": {1129, 1141, 5984, 6011, 6013, 6014, 6015, 6017},
    "MBB": {1129, 1141, 5984, 6011, 6012, 6013, 6014, 6015, 6016, 6017, 6018},
    "VPB": {1129, 1141, 5984, 6011, 6013, 6014, 6017, 6018},
    "HDB": {1129, 1141, 5984, 6011, 6013, 6014, 6015, 6017, 6018},
    "VCB": {1129, 1141, 5984, 6011, 6012, 6013, 6014, 6016, 6017, 6018},
    "CTG": set(),
    "BID": set(),
    "VIB": set(),
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 12,
    "document_count": 8,
    "document_unique_region_count": 8,
    "mapping_verified_count": 46,
    "numeric_mapping_unresolved_document_count": 3,
    "open_source_row_count": 7,
    "q1_source_period_caveat_document_count": 0,
    "rotated_structural_document_count": 3,
    "verified_value_cell_count": 82,
}


class Annual2025CapitalAndFunds8BankError(ValueError):
    """Annual capital evidence, accounting, schema, or replay drifted."""


def _error(message: str) -> Annual2025CapitalAndFunds8BankError:
    return Annual2025CapitalAndFunds8BankError(message)


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual capital support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_base() -> ModuleType:
    return _load_module(
        "annual_2025_capital_and_funds_mapping_base_v1",
        "build_capital_and_funds_8bank_codex_verified_mapping_v1.py",
    )


def _load_scanner() -> ModuleType:
    return _load_module(
        "annual_2025_capital_and_funds_mapping_scanner_v1",
        "scan_annual_2025_capital_and_funds_full_document_vietocr_v1.py",
    )


def _balance_mapping(
    base: ModuleType,
    report_norm_id: int,
    role: str,
    page: int,
    labels: list[tuple[int, str]],
    opening: tuple[int, str],
    closing: tuple[int, str],
) -> dict[str, Any]:
    return base._mapping(
        report_norm_id,
        role,
        [base._label(page, line, text) for line, text in labels],
        {
            "OPENING": [base._line(page, opening[0], opening[1])],
            "CLOSING": [base._line(page, closing[0], closing[1])],
        },
        "EQUITY_COLUMN_CROSSED_WITH_VISIBLE_ANNUAL_OPENING_AND_CLOSING_ROWS",
    )


def _total_mapping(
    base: ModuleType,
    report_norm_id: int,
    role: str,
    page: int,
    label: tuple[int, str],
    value: tuple[int, str],
    axis: str,
) -> dict[str, Any]:
    return base._mapping(
        report_norm_id,
        role,
        [base._label(page, label[0], label[1])],
        {axis: [base._line(page, value[0], value[1])]},
        f"PRINTED_ANNUAL_{axis}_TOTAL",
    )


def _annual_doc(
    base: ModuleType,
    code: str,
    page_span: tuple[int, int],
    owner: tuple[int, int, str] | None,
    heading: tuple[int, int, str] | None,
    period: list[tuple[int, int, str]],
    units: list[tuple[int, int, str]],
    mappings: list[dict[str, Any]],
    equations: list[dict[str, Any]],
    unresolved: list[dict[str, Any]],
    presentation: str,
) -> dict[str, Any]:
    label = base._label
    return base._doc(
        code,
        page_span,
        None if owner is None else label(*owner),
        None if heading is None else label(*heading),
        [label(*item) for item in period],
        [label(*item) for item in units],
        mappings,
        equations,
        unresolved,
        source_period="2025-12-31",
        presentation=presentation,
    )


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    label, line, equation, opened = base._label, base._line, base._equation, base._open
    p = 65
    acb_columns = [
        (5984, "CHARTER_CAPITAL", [(15, "Vốn điều lệ")], (58, "44.666.579"), (86, "51.366.566")),
        (
            6011,
            "SHARE_PREMIUM",
            [(7, "Thặng dư"), (10, "vốn cổ"), (16, "phần")],
            (59, "271.779"),
            (87, "271.779"),
        ),
        (
            6013,
            "CAPITAL_RESERVE",
            [(8, "Quỹ dự trữ"), (11, "bổ sung"), (17, "vốn điều lệ")],
            (60, "5.067.603"),
            (88, "6.519.540"),
        ),
        (
            6014,
            "FINANCIAL_RESERVE",
            [(9, "Quỹ dự"), (12, "phòng"), (18, "tài chính")],
            (61, "9.268.852"),
            (89, "10.575.595"),
        ),
        (
            6015,
            "OTHER_FUNDS",
            [(13, "Các quỹ"), (19, "khác (i)")],
            (62, "453.113"),
            (90, "487.926"),
        ),
        (
            6017,
            "RETAINED_EARNINGS",
            [(14, "Lợi nhuận"), (20, "chưa phân phối")],
            (63, "23.733.752"),
            (91, "25.298.313"),
        ),
    ]
    acb = _annual_doc(
        base,
        "ACB",
        (65, 66),
        (p, 5, "VỐN CHỦ SỞ HỮU"),
        (p, 6, "Tình hình tăng giảm vốn chủ sở hữu"),
        [(p, 57, "Tại ngày 31 tháng 12 năm 2024"), (p, 85, "Tại ngày 31 tháng 12 năm 2025")],
        [(p, 22, "Triệu VND")],
        [
            _total_mapping(
                base,
                1129,
                "OPENING_TOTAL",
                p,
                (57, "Tại ngày 31 tháng 12 năm 2024"),
                (64, "83.461.678"),
                "OPENING",
            ),
            _total_mapping(
                base,
                1141,
                "CLOSING_TOTAL",
                p,
                (85, "Tại ngày 31 tháng 12 năm 2025"),
                (92, "94.519.719"),
                "CLOSING",
            ),
            *[
                _balance_mapping(base, schema_id, role, p, labels, opening, closing)
                for schema_id, role, labels, opening, closing in acb_columns
            ],
        ],
        [
            equation(
                "EQUITY_COLUMNS_TO_OPENING_TOTAL",
                "OPENING",
                [
                    line(p, i, text)
                    for i, text in [
                        (58, "44.666.579"),
                        (59, "271.779"),
                        (60, "5.067.603"),
                        (61, "9.268.852"),
                        (62, "453.113"),
                        (63, "23.733.752"),
                    ]
                ],
                line(p, 64, "83.461.678"),
            ),
            equation(
                "EQUITY_COLUMNS_TO_CLOSING_TOTAL",
                "CLOSING",
                [
                    line(p, i, text)
                    for i, text in [
                        (86, "51.366.566"),
                        (87, "271.779"),
                        (88, "6.519.540"),
                        (89, "10.575.595"),
                        (90, "487.926"),
                        (91, "25.298.313"),
                    ]
                ],
                line(p, 92, "94.519.719"),
            ),
        ],
        [],
        "ANNUAL_EQUITY_COLUMNS_WITH_PRIOR_CLOSE_OPENING_MOVEMENTS_AND_CURRENT_CLOSE",
    )

    p = 69
    mbb_columns = [
        (5984, "CHARTER_CAPITAL", [(23, "Vốn điều lệ")], (44, "53.063.241"), (112, "80.549.999")),
        (
            6011,
            "SHARE_PREMIUM",
            [(17, "Thặng dư"), (24, "vốn cổ phần")],
            (45, "1.304.334"),
            (113, "1.304.334"),
        ),
        (6012, "OTHER_CAPITAL", [(25, "Vốn khác")], (46, "1.928.258"), (114, "2.111.211")),
        (
            6014,
            "FINANCIAL_RESERVE",
            [(12, "Quỹ dự"), (18, "phòng"), (26, "tài chính")],
            (47, "9.294.156"),
            (115, "11.513.914"),
        ),
        (
            6013,
            "CAPITAL_RESERVE",
            [(13, "Quỹ dự trữ"), (19, "bổ sung vốn"), (27, "điều lệ")],
            (48, "4.735.002"),
            (116, "6.972.588"),
        ),
        (6015, "OTHER_FUNDS", [(28, "Quỹ khác")], (49, "967.689"), (117, "904.382")),
        (
            6016,
            "FX_DIFFERENCE",
            [(14, "Chênh lệch"), (20, "tỷ giá"), (29, "hối đoái")],
            (50, "137.797"),
            (118, "202.211"),
        ),
        (
            6017,
            "RETAINED_EARNINGS",
            [(15, "Lợi nhuận"), (21, "chưa"), (30, "phân phối")],
            (51, "40.718.224"),
            (119, "32.577.391"),
        ),
        (
            6018,
            "NON_CONTROLLING_INTEREST",
            [(16, "Lợi ích cổ"), (22, "đông không"), (31, "kiểm soát")],
            (52, "4.910.880"),
            (120, "5.886.495"),
        ),
    ]
    mbb = _annual_doc(
        base,
        "MBB",
        (69, 70),
        (p, 8, "VỐN VÀ CÁC QUỸ"),
        (p, 10, "Báo cáo tình hình thay đổi vốn chủ sở hữu"),
        [(p, 43, "Tại ngày 1 tháng 1 năm 2025"), (p, 111, "Tại ngày 31 tháng 12 năm 2025")],
        [(p, 33, "triệu đồng")],
        [
            _total_mapping(
                base,
                1129,
                "OPENING_TOTAL",
                p,
                (43, "Tại ngày 1 tháng 1 năm 2025"),
                (53, "117.059.581"),
                "OPENING",
            ),
            _total_mapping(
                base,
                1141,
                "CLOSING_TOTAL",
                p,
                (111, "Tại ngày 31 tháng 12 năm 2025"),
                (121, "142.022.525"),
                "CLOSING",
            ),
            *[
                _balance_mapping(base, schema_id, role, p, labels, opening, closing)
                for schema_id, role, labels, opening, closing in mbb_columns
            ],
        ],
        [
            equation(
                "EQUITY_COLUMNS_TO_OPENING_TOTAL",
                "OPENING",
                [
                    line(p, i, text)
                    for i, text in [
                        (44, "53.063.241"),
                        (45, "1.304.334"),
                        (46, "1.928.258"),
                        (47, "9.294.156"),
                        (48, "4.735.002"),
                        (49, "967.689"),
                        (50, "137.797"),
                        (51, "40.718.224"),
                        (52, "4.910.880"),
                    ]
                ],
                line(p, 53, "117.059.581"),
            ),
            equation(
                "EQUITY_COLUMNS_TO_CLOSING_TOTAL",
                "CLOSING",
                [
                    line(p, i, text)
                    for i, text in [
                        (112, "80.549.999"),
                        (113, "1.304.334"),
                        (114, "2.111.211"),
                        (115, "11.513.914"),
                        (116, "6.972.588"),
                        (117, "904.382"),
                        (118, "202.211"),
                        (119, "32.577.391"),
                        (120, "5.886.495"),
                    ]
                ],
                line(p, 121, "142.022.525"),
            ),
        ],
        [],
        "ANNUAL_EQUITY_COLUMNS_WITH_EXPLICIT_OPENING_MOVEMENTS_AND_CLOSING",
    )

    p = 66
    vpb_columns = [
        (5984, "CHARTER_CAPITAL", [(20, "Vốn điều lệ")], (65, "79.339.236"), (94, "79.339.236")),
        (
            6011,
            "SHARE_PREMIUM",
            [(13, "Thặng dư"), (21, "vốn cổ phần")],
            (66, "23.992.546"),
            (95, "23.992.546"),
        ),
        (
            6013,
            "CAPITAL_RESERVE",
            [(9, "Quỹ dự trữ"), (14, "bổ sung"), (22, "vốn điều lệ")],
            (67, "3.812.475"),
            (96, "5.948.642"),
        ),
        (
            6014,
            "FINANCIAL_RESERVE",
            [(10, "Quỹ dự"), (15, "phòng tài"), (23, "chính")],
            (68, "10.684.381"),
            (97, "12.584.514"),
        ),
        (
            6017,
            "RETAINED_EARNINGS",
            [(11, "Lợi nhuận"), (18, "chưa phân"), (26, "phối")],
            (70, "24.007.579"),
            (99, "45.969.647"),
        ),
        (
            6018,
            "NON_CONTROLLING_INTEREST",
            [(8, "Lợi ích của"), (12, "cổ đông"), (19, "không kiểm"), (27, "soát")],
            (71, "5.370.287"),
            (100, "12.372.286"),
        ),
    ]
    vpb = _annual_doc(
        base,
        "VPB",
        (66, 67),
        (p, 5, "VỐN VÀ CÁC QUỸ"),
        (p, 7, "Báo cáo tình hình thay đổi vốn chủ sở hữu"),
        [(p, 64, "Tại ngày 31 tháng 12 năm 2024"), (p, 93, "Tại ngày 31 tháng 12 năm 2025")],
        [(p, 29, "Triệu đồng")],
        [
            _total_mapping(
                base,
                1129,
                "OPENING_TOTAL",
                p,
                (64, "Tại ngày 31 tháng 12 năm 2024"),
                (72, "147.275.262"),
                "OPENING",
            ),
            _total_mapping(
                base,
                1141,
                "CLOSING_TOTAL",
                p,
                (93, "Tại ngày 31 tháng 12 năm 2025"),
                (101, "180.275.629"),
                "CLOSING",
            ),
            *[
                _balance_mapping(base, schema_id, role, p, labels, opening, closing)
                for schema_id, role, labels, opening, closing in vpb_columns
            ],
        ],
        [
            equation(
                "EQUITY_COLUMNS_TO_OPENING_TOTAL",
                "OPENING",
                [
                    line(p, i, text)
                    for i, text in [
                        (65, "79.339.236"),
                        (66, "23.992.546"),
                        (67, "3.812.475"),
                        (68, "10.684.381"),
                        (69, "68.758"),
                        (70, "24.007.579"),
                        (71, "5.370.287"),
                    ]
                ],
                line(p, 72, "147.275.262"),
            ),
            equation(
                "EQUITY_COLUMNS_TO_CLOSING_TOTAL",
                "CLOSING",
                [
                    line(p, i, text)
                    for i, text in [
                        (94, "79.339.236"),
                        (95, "23.992.546"),
                        (96, "5.948.642"),
                        (97, "12.584.514"),
                        (98, "68.758"),
                        (99, "45.969.647"),
                        (100, "12.372.286"),
                    ]
                ],
                line(p, 101, "180.275.629"),
            ),
        ],
        [
            opened(
                "A2025-CAF-001",
                "Quỹ đầu tư phát triển",
                "NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL",
                [label(p, 16, "Quỹ đầu tư"), label(p, 24, "phát triển")],
                {"OPENING": [line(p, 69, "68.758")], "CLOSING": [line(p, 98, "68.758")]},
            )
        ],
        "ANNUAL_EQUITY_COLUMNS_WITH_OPTIONAL_DEVELOPMENT_FUND_AND_TREASURY_COLUMN",
    )

    p = 48
    hdb_columns = [
        (5984, "CHARTER_CAPITAL", [(17, "Vốn điều lệ")], (85, "35.101.423"), (131, "50.052.763")),
        (
            6011,
            "SHARE_PREMIUM",
            [(11, "Thặng dư"), (18, "Vốn"), (27, "cổ phần")],
            (86, "535.956"),
            (132, "1.274.874"),
        ),
        (
            6013,
            "CAPITAL_RESERVE",
            [(12, "Quỹ dự trữ"), (20, "bổ sung"), (29, "vốn điều lệ")],
            (88, "1.977.623"),
            (133, "3.058.795"),
        ),
        (
            6014,
            "FINANCIAL_RESERVE",
            [(13, "Quỹ"), (21, "dự phòng"), (30, "tài chính")],
            (89, "4.206.805"),
            (134, "6.909.251"),
        ),
        (6015, "OTHER_FUNDS", [(22, "Các"), (31, "quỹ khác")], (90, "128.774"), (135, "83.312")),
        (
            6017,
            "RETAINED_EARNINGS",
            [(15, "Lợi nhuận"), (24, "chưa"), (33, "phân phối")],
            (92, "12.953.881"),
            (137, "14.191.046"),
        ),
        (
            6018,
            "NON_CONTROLLING_INTEREST",
            [(16, "Lợi ích cổ"), (25, "đông không"), (34, "kiểm soát")],
            (93, "2.166.158"),
            (138, "2.715.392"),
        ),
    ]
    hdb = _annual_doc(
        base,
        "HDB",
        (48, 49),
        (p, 8, "VỐN CHỦ SỞ HỮU"),
        (p, 10, "Báo cáo tình hình thay đổi vốn chủ sở hữu"),
        [(p, 84, "Tại ngày 31 tháng 12 năm 2024"), (p, 130, "Tại ngày 31 tháng 12 năm 2025")],
        [(p, 36, "Triệu VND")],
        [
            _total_mapping(
                base,
                1129,
                "OPENING_TOTAL",
                p,
                (84, "Tại ngày 31 tháng 12 năm 2024"),
                (94, "56.657.261"),
                "OPENING",
            ),
            _total_mapping(
                base,
                1141,
                "CLOSING_TOTAL",
                p,
                (130, "Tại ngày 31 tháng 12 năm 2025"),
                (139, "78.285.522"),
                "CLOSING",
            ),
            *[
                _balance_mapping(base, schema_id, role, p, labels, opening, closing)
                for schema_id, role, labels, opening, closing in hdb_columns
            ],
        ],
        [
            equation(
                "EQUITY_COLUMNS_TO_OPENING_TOTAL",
                "OPENING",
                [
                    line(p, i, text)
                    for i, text in [
                        (85, "35.101.423"),
                        (86, "535.956"),
                        (87, "(413.448)"),
                        (88, "1.977.623"),
                        (89, "4.206.805"),
                        (90, "128.774"),
                        (91, "89"),
                        (92, "12.953.881"),
                        (93, "2.166.158"),
                    ]
                ],
                line(p, 94, "56.657.261"),
            ),
            equation(
                "EQUITY_COLUMNS_TO_CLOSING_TOTAL",
                "CLOSING",
                [
                    line(p, i, text)
                    for i, text in [
                        (131, "50.052.763"),
                        (132, "1.274.874"),
                        (133, "3.058.795"),
                        (134, "6.909.251"),
                        (135, "83.312"),
                        (136, "89"),
                        (137, "14.191.046"),
                        (138, "2.715.392"),
                    ]
                ],
                line(p, 139, "78.285.522"),
            ),
        ],
        [
            opened(
                "A2025-CAF-002",
                "Cổ phiếu quỹ",
                "NO_EXACT_EQUITY_BALANCE_LEAF; CLOSING_BLANK_NOT_PROMOTED_TO_ZERO",
                [label(p, 19, "Cổ phiếu"), label(p, 28, "quỹ")],
                {"OPENING": [line(p, 87, "(413.448)")]},
            ),
            opened(
                "A2025-CAF-003",
                "Vốn đầu tư xây dựng cơ bản",
                "NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL",
                [label(p, 14, "Vốn đầu tư"), label(p, 23, "xây dựng"), label(p, 32, "cơ bản")],
                {"OPENING": [line(p, 91, "89")], "CLOSING": [line(p, 136, "89")]},
            ),
        ],
        "ANNUAL_EQUITY_COLUMNS_WITH_OPTIONAL_TREASURY_AND_CONSTRUCTION_CAPITAL",
    )

    p = 56
    vcb_columns = [
        (
            5984,
            "CHARTER_CAPITAL",
            [(11, "Vốn"), (19, "điều lệ")],
            (64, "55.890.913"),
            (138, "83.556.751"),
        ),
        (
            6011,
            "SHARE_PREMIUM",
            [(12, "Thặng dư"), (20, "vốn cổ"), (29, "phần")],
            (65, "4.995.389"),
            (139, "4.995.389"),
        ),
        (6012, "OTHER_CAPITAL", [(13, "Vốn"), (21, "khác")], (66, "809.837"), (140, "809.837")),
        (
            6013,
            "CAPITAL_RESERVE",
            [(22, "Quỹ dự trữ"), (30, "bổ sung"), (36, "vốn điều lệ")],
            (67, "14.092.273"),
            (141, "17.549.294"),
        ),
        (
            6014,
            "FINANCIAL_RESERVE",
            [(23, "Quỹ"), (31, "dự phòng"), (37, "tài chính")],
            (68, "21.603.058"),
            (142, "21.613.908"),
        ),
        (
            6016,
            "FX_DIFFERENCE",
            [(15, "Chênh"), (26, "lệch tỷ"), (33, "giá hối"), (39, "đoái")],
            (71, "(968.292)"),
            (145, "(918.676)"),
        ),
        (
            6017,
            "RETAINED_EARNINGS",
            [(16, "Lợi nhuận"), (27, "chưa"), (34, "phân phối")],
            (72, "98.332.086"),
            (146, "87.822.642"),
        ),
        (
            6018,
            "NON_CONTROLLING_INTEREST",
            [(17, "Lợi ích của"), (28, "cổ đông"), (35, "không kiểm"), (40, "soát")],
            (73, "96.261"),
            (147, "71.521"),
        ),
    ]
    vcb = _annual_doc(
        base,
        "VCB",
        (56, 57),
        (p, 8, "Vốn chủ sở hữu"),
        (p, 10, "Tình hình thay đổi vốn chủ sở hữu"),
        [(p, 63, "Số dư tại ngày 1/1/2025"), (p, 137, "Số dư tại ngày 31/12/2025")],
        [(p, 41, "Triệu"), (p, 52, "VND")],
        [
            _total_mapping(
                base,
                1129,
                "OPENING_TOTAL",
                p,
                (63, "Số dư tại ngày 1/1/2025"),
                (74, "196.209.168"),
                "OPENING",
            ),
            _total_mapping(
                base,
                1141,
                "CLOSING_TOTAL",
                p,
                (137, "Số dư tại ngày 31/12/2025"),
                (148, "224.558.726"),
                "CLOSING",
            ),
            *[
                _balance_mapping(base, schema_id, role, p, labels, opening, closing)
                for schema_id, role, labels, opening, closing in vcb_columns
            ],
        ],
        [
            equation(
                "RESERVE_COLUMNS_TO_RESERVE_SUBTOTAL",
                "OPENING",
                [line(p, 67, "14.092.273"), line(p, 68, "21.603.058"), line(p, 69, "1.357.643")],
                line(p, 70, "37.052.974"),
            ),
            equation(
                "RESERVE_COLUMNS_TO_RESERVE_SUBTOTAL",
                "CLOSING",
                [line(p, 141, "17.549.294"), line(p, 142, "21.613.908"), line(p, 143, "9.058.060")],
                line(p, 144, "48.221.262"),
            ),
            equation(
                "EQUITY_COLUMNS_TO_OPENING_TOTAL",
                "OPENING",
                [
                    line(p, i, text)
                    for i, text in [
                        (64, "55.890.913"),
                        (65, "4.995.389"),
                        (66, "809.837"),
                        (70, "37.052.974"),
                        (71, "(968.292)"),
                        (72, "98.332.086"),
                        (73, "96.261"),
                    ]
                ],
                line(p, 74, "196.209.168"),
            ),
            equation(
                "EQUITY_COLUMNS_TO_CLOSING_TOTAL",
                "CLOSING",
                [
                    line(p, i, text)
                    for i, text in [
                        (138, "83.556.751"),
                        (139, "4.995.389"),
                        (140, "809.837"),
                        (144, "48.221.262"),
                        (145, "(918.676)"),
                        (146, "87.822.642"),
                        (147, "71.521"),
                    ]
                ],
                line(p, 148, "224.558.726"),
            ),
        ],
        [
            opened(
                "A2025-CAF-004",
                "Quỹ đầu tư phát triển",
                "NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_RESERVE_SUBTOTAL_AND_EQUITY_TOTAL",
                [label(p, 24, "Quỹ đầu"), label(p, 32, "tư phát"), label(p, 38, "triển")],
                {"OPENING": [line(p, 69, "1.357.643")], "CLOSING": [line(p, 143, "9.058.060")]},
            )
        ],
        "ANNUAL_NESTED_RESERVE_COLUMNS_WITH_SPLIT_UNIT_HEADER",
    )

    structural = [
        (
            "CTG",
            (55, 56),
            "A2025-CAF-005",
            "ROTATED_SOURCE_NUMERIC_CHALLENGER_NOT_RELIABLE; UNIQUE_STRUCTURE_VERIFIED_BUT_NUMERIC_MAPPING_DEFERRED",
        ),
        (
            "BID",
            (53, 54),
            "A2025-CAF-006",
            "ROTATED_SOURCE_NUMERIC_CHALLENGER_NOT_RELIABLE; UNIQUE_STRUCTURE_VERIFIED_BUT_NUMERIC_MAPPING_DEFERRED",
        ),
        (
            "VIB",
            (49, 50),
            "A2025-CAF-007",
            "ROTATED_SOURCE_NUMERIC_CHALLENGER_NOT_RELIABLE; UNIQUE_STRUCTURE_VERIFIED_BUT_NUMERIC_MAPPING_DEFERRED",
        ),
    ]
    structural_docs = [
        _annual_doc(
            base,
            code,
            span,
            None,
            None,
            [],
            [],
            [],
            [],
            [opened(item_id, "Báo cáo tình hình thay đổi vốn chủ sở hữu", reason)],
            "ROTATED_ANNUAL_EQUITY_TABLE_STRUCTURE_ONLY",
        )
        for code, span, item_id, reason in structural
    ]
    return [acb, mbb, vpb, hdb, vcb, *structural_docs]


def _adapt_structure_scan(scan: dict[str, Any]) -> dict[str, Any]:
    trials = []
    for trial in scan["trials"]:
        matcher = canonical_clone_v1(trial["base_matcher_result"])
        matcher["regions"] = [canonical_clone_v1(trial["selected_region"])]
        matcher["uniqueness"] = {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        trials.append(
            {
                "document_ordinal": trial["document_ordinal"],
                "document_provenance": trial["document_provenance"],
                "matcher_result": matcher,
                "rotated_rescue_line_count": trial["rotated_rescue_line_count"],
            }
        )
    return {"scan_id": scan["scan_id"], "state": STRUCTURE_SCAN_STATE, "trials": trials}


def _configure(base: ModuleType) -> None:
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.REVIEW_RUN_ID = REVIEW_RUN_ID
    base.STRUCTURE_SCAN_STATE = STRUCTURE_SCAN_STATE
    base.FAMILY_END_DISPLAY_ORDER = FAMILY_END_DISPLAY_ORDER
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
        "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_OPENING_AND_CLOSING_BALANCES"
        if source_period == "2025-12-31"
        else (_ for _ in ()).throw(_error("annual capital period drifted"))
    )


def _assert_result(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual capital result metrics drifted")
    for trial in value.get("trials", []):
        actual = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        if actual != _EXPECTED_IDS[trial["document_provenance"]]:
            raise _error("annual capital mapped schema set drifted")
        if trial["source_period_status"] != (
            "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_OPENING_AND_CLOSING_BALANCES"
        ):
            raise _error("annual capital source period status drifted")
    return value


def build_annual_2025_capital_and_funds_pixel_review_blueprint_v1() -> dict[str, Any]:
    base = _load_base()
    _configure(base)
    return base._review_blueprint()


def build_live_annual_2025_capital_and_funds_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    base = _load_base()
    scanner = _load_scanner()
    _configure(base)
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review = base._review_blueprint()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    annual_scan = scanner.build_annual_2025_capital_and_funds_full_document_scan_v1()
    scan = _adapt_structure_scan(annual_scan)
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    result = base.build_capital_and_funds_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    replayed = base.validate_capital_and_funds_8bank_codex_verified_mapping_replay_v1(
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
        build_annual_2025_capital_and_funds_pixel_review_blueprint_v1()
        if args.write_review
        else build_live_annual_2025_capital_and_funds_8bank_codex_verified_mapping_v1()
    )
    output.write_bytes(canonical_json_bytes_v1(value))
    if not args.write_review:
        print(value["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
