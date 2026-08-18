"""Verify annual-2025 capital-contribution and dividend income in eight banks."""

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
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025ccdi8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_CAPITAL_CONTRIBUTION_DIVIDEND_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025ccdi8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0142"
OPEN_SOURCE_TRIAL_STATUS = "VERIFIED_BY_CODEX_WITH_SOURCE_SCHEMA_GAPS"
REVIEW_PATH = Path(
    "docs/experiments/E-0142-annual-2025-capital-contribution-dividend-income-8bank-"
    "codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0142-annual-2025-capital-contribution-dividend-income-8bank-"
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
EXPECTED_SCAN_ID = "ccdifdsv1:scan:73d61fc938e0b6fce1b9dafce072b890297962aeb309472725e0d670fa41808e"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_CAPITAL_CONTRIBUTION_SHARE_DIVIDEND_AND_OTHER_"
    "INCOME_GRAPH_VISIBLE_PDF_UPSTREAM_PPOCRV6_NUMERIC_CHALLENGER_"
    "AUTHENTICATED_PIXEL_DASH_PERIOD_UNIT_ACCOUNTING_LIVE_TM_SCHEMA_AND_"
    "ONE_EXPLICIT_COMBINED_SECURITIES_SOURCE_GAP_ONLY_NO_CANONICALIZATION_"
    "EXPORT_OR_PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "combined_securities_source_row_split_into_trading_or_investment": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_seven_reviewed_annual_detailed_notes": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "statement_aggregate_relabelled_as_detailed_note": False,
    "text_similarity_alone_used_for_mapping": False,
    "whole_pdf_uniqueness_replayed": True,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "dash_normalized_to_zero_only_with_visible_authenticated_pixel_binding": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "source_combined_securities_row_silently_narrowed_or_split": False,
    "statement_aggregate_used_as_detailed_note": False,
    "visible_pdf_pixels_reviewed": True,
    "whole_pdf_uniqueness_replayed": True,
}
_SCHEMA_EXPECTED = {
    1198: ("Thu nhập từ góp vốn, mua cổ phần và thu nhập cổ tức", 1142, 758),
    1199: ("Cổ tức nhận được trong kỳ từ góp vốn, mua cổ phần", 1198, 759),
    1200: ("Trong đó: + Từ chứng khoán Vốn kinh doanh", 1198, 760),
    1201: ("+ Từ chứng khoán Vốn đầu tư", 1198, 761),
    1202: ("+ Từ góp vốn, đầu tư dài hạn", 1198, 762),
    1203: (
        "Phân chia lãi/lỗ theo phương pháp vốn CSH của các khoản đầu tư vào các công ty liên doanh, liên kết",
        1198,
        763,
    ),
    1204: ("Các khoản thu nhập khác", 1198, 764),
}
_EXPECTED_PAGES = {
    "ACB": [69, 69],
    "MBB": [74, 74],
    "VPB": [71, 71],
    "HDB": [51, 51],
    "VCB": [60, 60],
    "CTG": [59, 59],
    "BID": [56, 56],
    "VIB": None,
}
_EXPECTED_REPORT_NORM_IDS = {
    "ACB": {1198, 1200, 1201, 1202},
    "MBB": {1198, 1199, 1204},
    "VPB": {1198, 1199},
    "HDB": {1198, 1202, 1203},
    "VCB": {1198, 1199, 1200, 1202, 1203, 1204},
    "CTG": {1198, 1199, 1202, 1203},
    "BID": {1198, 1199, 1200, 1201, 1202, 1203},
    "VIB": set(),
}
_EXPECTED_EQUATION_COUNTS = {
    "ACB": 2,
    "MBB": 2,
    "VPB": 2,
    "HDB": 2,
    "VCB": 4,
    "CTG": 4,
    "BID": 4,
    "VIB": 0,
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 20,
    "authenticated_dash_zero_count": 4,
    "detailed_note_not_present_document_count": 1,
    "document_count": 8,
    "document_unique_region_count": 7,
    "fresh_vietocr_numeric_disagreement_count": 0,
    "mapping_verified_count": 28,
    "open_source_row_count": 1,
    "q1_source_period_caveat_document_count": 0,
    "source_only_value_cell_count": 2,
    "verified_value_cell_count": 56,
}


class Annual2025CapitalContributionDividendIncome8BankError(ValueError):
    """Annual contribution/dividend structure, pixels, numbers or schema drifted."""


def _error(message: str) -> Annual2025CapitalContributionDividendIncome8BankError:
    return Annual2025CapitalContributionDividendIncome8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT / "scripts/experiments/"
        "build_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_capital_contribution_dividend_income_base"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual contribution/dividend support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _mapping(
    base: ModuleType,
    role: str,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: dict[str, Any],
    comparative: dict[str, Any],
    graph_child_role: str | None,
    topology: str,
) -> dict[str, Any]:
    return base._mapping(
        role,
        [(page, line, text) for line, text in labels],
        current,
        comparative,
        graph_child_role,
        topology,
    )


def _source_only(
    base: ModuleType,
    page: int,
    label: tuple[int, str],
    current: dict[str, Any],
    comparative: dict[str, Any],
    topology: str,
) -> dict[str, Any]:
    return {
        "gap_id": "CCDI-CTG-001",
        "graph_child_role": "COMBINED_EQUITY_SECURITIES_DIVIDEND",
        "label": [base._ref(page, label[0], label[1])],
        "reason": (
            "The source prints one combined 'Từ chứng khoán vốn' amount; the live schema "
            "has separate trading- and investment-equity leaves, so the printed amount is "
            "retained source-only and is not split or narrowed."
        ),
        "role": "COMBINED_EQUITY_SECURITIES_DIVIDEND_SOURCE_ONLY",
        "topology": topology,
        "values": {"COMPARATIVE_PERIOD": comparative, "CURRENT_PERIOD": current},
    }


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    standard = "OPTIONAL_DIVIDEND_SOURCE_EQUITY_METHOD_OR_OTHER_CHILDREN_THEN_TOTAL"
    documents = [
        base._mapped_document(
            "ACB",
            69,
            "2025-12-31",
            standard,
            [(69, 35, "Năm 2025"), (69, 36, "Năm 2024")],
            [(69, 37, "Triệu VND"), (69, 38, "Triệu VND")],
            [
                _mapping(
                    base,
                    "ROOT",
                    69,
                    [(34, "THU NHẬP TỪ GÓP VỐN, MUA CỔ PHẦN")],
                    base._line(69, 48, "119.175"),
                    base._line(69, 49, "36.214"),
                    None,
                    standard,
                ),
                _mapping(
                    base,
                    "TRADING_EQUITY_DIVIDEND",
                    69,
                    [(40, "Từ chứng khoán vốn kinh doanh")],
                    base._line(69, 41, "61.307"),
                    base._line(69, 42, "24.439"),
                    "TRADING_EQUITY_DIVIDEND",
                    standard,
                ),
                _mapping(
                    base,
                    "INVESTMENT_EQUITY_DIVIDEND",
                    69,
                    [(43, "Từ chứng khoán vốn đầu tư")],
                    base._line(69, 44, "3.937"),
                    base._dash(
                        69,
                        (1523, 1420, 1534, 1429),
                        "2498f3690410b708a1c9ba887d1e38062a6f7d17f78436e2e572a6bfd789e4ba",
                    ),
                    "INVESTMENT_EQUITY_DIVIDEND",
                    standard,
                ),
                _mapping(
                    base,
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    69,
                    [(45, "Từ các khoản góp vốn, đầu tư dài hạn")],
                    base._line(69, 46, "53.931"),
                    base._line(69, 47, "11.775"),
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    standard,
                ),
            ],
            [
                (
                    "ROOT",
                    [
                        "TRADING_EQUITY_DIVIDEND",
                        "INVESTMENT_EQUITY_DIVIDEND",
                        "LONG_TERM_CAPITAL_DIVIDEND",
                    ],
                    "THREE_DIVIDEND_SOURCES_EQUAL_TOTAL",
                )
            ],
        ),
        base._mapped_document(
            "MBB",
            74,
            "2025-12-31",
            "DIVIDEND_AND_DISPOSAL_GAIN_THEN_COLLAPSED_PARENT_TOTAL",
            [(74, 41, "Năm 2025"), (74, 42, "Năm 2024")],
            [(74, 43, "triệu đồng"), (74, 44, "triệu đồng")],
            [
                _mapping(
                    base,
                    "ROOT",
                    74,
                    [(50, "Thu nhập từ góp vốn, mua cổ phần")],
                    base._line(74, 51, "174.344"),
                    base._line(74, 52, "52.643"),
                    "COLLAPSED_PARENT",
                    "DIVIDEND_AND_DISPOSAL_GAIN_THEN_COLLAPSED_PARENT_TOTAL",
                ),
                _mapping(
                    base,
                    "DIRECT_DIVIDEND",
                    74,
                    [(45, "Thu từ cổ tức, lợi tức")],
                    base._line(74, 46, "59.336"),
                    base._line(74, 47, "52.643"),
                    "DIRECT_DIVIDEND",
                    standard,
                ),
                _mapping(
                    base,
                    "OTHER_INCOME",
                    74,
                    [(48, "Lãi từ việc bán các khoản góp vốn, mua cổ phần")],
                    base._line(74, 49, "115.008"),
                    base._dash(
                        74,
                        (1462, 1081, 1473, 1090),
                        "6ff1fd45991174ddfec6fc94cf00a8697bdb86de89b69613baa61e666824d5f5",
                    ),
                    "OTHER_INCOME",
                    standard,
                ),
            ],
            [("ROOT", ["DIRECT_DIVIDEND", "OTHER_INCOME"], "CHILDREN_EQUAL_TOTAL")],
        ),
        base._mapped_document(
            "VPB",
            71,
            "2025-12-31",
            "SINGLE_DIRECT_DIVIDEND_CHILD_THEN_IDENTICAL_TOTAL",
            [(71, 53, "Năm 2025"), (71, 54, "Năm 2024")],
            [(71, 55, "Triệu đồng"), (71, 56, "Triệu đồng")],
            [
                _mapping(
                    base,
                    "ROOT",
                    71,
                    [(52, "THU NHẬP TỪ GÓP VỐN MUA CỔ PHẦN")],
                    base._line(71, 60, "35.161"),
                    base._line(71, 61, "12.801"),
                    None,
                    "SINGLE_DIRECT_DIVIDEND_CHILD_THEN_IDENTICAL_TOTAL",
                ),
                _mapping(
                    base,
                    "DIRECT_DIVIDEND",
                    71,
                    [(57, "Cổ tức nhận được từ góp vốn, mua cổ phần")],
                    base._line(71, 58, "35.161"),
                    base._line(71, 59, "12.801"),
                    "DIRECT_DIVIDEND",
                    "SINGLE_DIRECT_DIVIDEND_CHILD_THEN_IDENTICAL_TOTAL",
                ),
            ],
            [("ROOT", ["DIRECT_DIVIDEND"], "DIRECT_DIVIDEND_EQUALS_TOTAL")],
        ),
        base._mapped_document(
            "HDB",
            51,
            "2025-12-31",
            standard,
            [(51, 48, "Năm nay"), (51, 49, "Năm trước")],
            [(51, 50, "Triệu VND"), (51, 51, "Triệu VND")],
            [
                _mapping(
                    base,
                    "ROOT",
                    51,
                    [(47, "THU NHẬP TỪ GÓP VỐN, MUA CỔ PHẦN")],
                    base._line(51, 58, "319.472"),
                    base._line(51, 59, "71.664"),
                    None,
                    standard,
                ),
                _mapping(
                    base,
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    51,
                    [(52, "Cổ tức nhận trong năm từ góp vốn, đầu tư dài hạn")],
                    base._line(51, 53, "8.521"),
                    base._dash(
                        51,
                        (1479, 1025, 1488, 1034),
                        "41ea01b1493278f687e6fe198d2e14cbb63c9be41b8aca78cd2c7bf90bb4b4d0",
                    ),
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    standard,
                ),
                _mapping(
                    base,
                    "EQUITY_METHOD",
                    51,
                    [
                        (54, "Phân chia lãi lỗ theo phương pháp vốn chủ sở hữu của"),
                        (57, "các khoản đầu tư vào công ty liên kết"),
                    ],
                    base._line(51, 55, "310.951"),
                    base._line(51, 56, "71.664"),
                    "EQUITY_METHOD",
                    standard,
                ),
            ],
            [
                (
                    "ROOT",
                    ["LONG_TERM_CAPITAL_DIVIDEND", "EQUITY_METHOD"],
                    "OPTIONAL_CHILDREN_EQUAL_TOTAL",
                )
            ],
        ),
        base._mapped_document(
            "VCB",
            60,
            "2025-12-31",
            standard,
            [(60, 48, "2025"), (60, 49, "2024")],
            [(60, 50, "Triệu VND"), (60, 51, "Triệu VND")],
            [
                _mapping(
                    base,
                    "ROOT",
                    60,
                    [(46, "Thu nhập từ góp vốn, mua cổ phần")],
                    base._line(60, 69, "281.862"),
                    base._line(60, 70, "307.179"),
                    None,
                    standard,
                ),
                _mapping(
                    base,
                    "DIRECT_DIVIDEND",
                    60,
                    [
                        (52, "Cổ tức nhận được từ các khoản góp vốn, mua cổ phần"),
                        (53, "(Thuyết minh 33(a))"),
                    ],
                    base._line(60, 54, "118.576"),
                    base._line(60, 55, "160.709"),
                    "DIRECT_DIVIDEND",
                    standard,
                ),
                _mapping(
                    base,
                    "TRADING_EQUITY_DIVIDEND",
                    60,
                    [(56, "Từ chứng khoán vốn kinh doanh")],
                    base._line(60, 57, "2.814"),
                    base._line(60, 58, "5.141"),
                    "TRADING_EQUITY_DIVIDEND",
                    standard,
                ),
                _mapping(
                    base,
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    60,
                    [(59, "Từ góp vốn, đầu tư dài hạn")],
                    base._line(60, 60, "115.762"),
                    base._line(60, 61, "155.568"),
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    standard,
                ),
                _mapping(
                    base,
                    "EQUITY_METHOD",
                    60,
                    [
                        (62, "Phân chia lãi theo phương pháp vốn chủ sở hữu của các"),
                        (63, "khoản đầu tư vào các công ty liên doanh, liên kết"),
                        (64, "(Thuyết minh 33(a))"),
                    ],
                    base._line(60, 65, "163.286"),
                    base._line(60, 66, "145.723"),
                    "EQUITY_METHOD",
                    standard,
                ),
                _mapping(
                    base,
                    "OTHER_INCOME",
                    60,
                    [(67, "Thu nhập từ thanh lý các khoản đầu tư góp vốn, mua cổ phần")],
                    base._dash(
                        60,
                        (1179, 1626, 1191, 1635),
                        "8fa9bb2dcdb167540b2cf028fe8c75f858d809f9af6893884ad792a4418bba3b",
                    ),
                    base._line(60, 68, "747"),
                    "OTHER_INCOME",
                    standard,
                ),
            ],
            [
                (
                    "DIRECT_DIVIDEND",
                    ["TRADING_EQUITY_DIVIDEND", "LONG_TERM_CAPITAL_DIVIDEND"],
                    "DIVIDEND_SUBSOURCES_EQUAL_DIRECT_DIVIDEND",
                ),
                (
                    "ROOT",
                    ["DIRECT_DIVIDEND", "EQUITY_METHOD", "OTHER_INCOME"],
                    "DIVIDEND_EQUITY_METHOD_AND_OTHER_EQUAL_TOTAL",
                ),
            ],
        ),
    ]
    ctg_topology = "COMBINED_SECURITIES_SOURCE_CHILD_RETAINED_WITHOUT_SCHEMA_SPLIT"
    ctg = base._mapped_document(
        "CTG",
        59,
        "2025-12-31",
        ctg_topology,
        [(59, 64, "Năm tài chính kết thúc ngày"), (59, 65, "31.12.2025"), (59, 66, "31.12.2024")],
        [(59, 67, "Triệu đồng"), (59, 68, "Triệu đồng")],
        [
            _mapping(
                base,
                "ROOT",
                59,
                [(63, "THU NHẬP TỪ GÓP VỐN, MUA CỔ PHẦN")],
                base._line(59, 82, "440.367"),
                base._line(59, 83, "390.648"),
                None,
                ctg_topology,
            ),
            _mapping(
                base,
                "DIRECT_DIVIDEND",
                59,
                [(69, "Cổ tức nhận được trong năm từ góp vốn, mua cổ phần")],
                base._line(59, 70, "71.352"),
                base._line(59, 71, "20.539"),
                "DIRECT_DIVIDEND",
                ctg_topology,
            ),
            _mapping(
                base,
                "LONG_TERM_CAPITAL_DIVIDEND",
                59,
                [(75, "Từ góp vốn, đầu tư dài hạn")],
                base._line(59, 76, "55.529"),
                base._line(59, 77, "7.255"),
                "LONG_TERM_CAPITAL_DIVIDEND",
                ctg_topology,
            ),
            _mapping(
                base,
                "EQUITY_METHOD",
                59,
                [
                    (78, "Phân chia lãi theo phương pháp vốn chủ sở hữu của các"),
                    (79, "khoản đầu tư vào công ty liên doanh"),
                ],
                base._line(59, 80, "369.015"),
                base._line(59, 81, "370.109"),
                "EQUITY_METHOD",
                ctg_topology,
            ),
        ],
        [
            (
                "DIRECT_DIVIDEND",
                [
                    "COMBINED_EQUITY_SECURITIES_DIVIDEND_SOURCE_ONLY",
                    "LONG_TERM_CAPITAL_DIVIDEND",
                ],
                "COMBINED_SECURITIES_AND_LONG_TERM_EQUAL_DIRECT_DIVIDEND",
            ),
            (
                "ROOT",
                ["DIRECT_DIVIDEND", "EQUITY_METHOD"],
                "DIRECT_DIVIDEND_PLUS_EQUITY_METHOD_EQUALS_TOTAL",
            ),
        ],
    )
    ctg["source_only_rows"] = [
        _source_only(
            base,
            59,
            (72, "Từ chứng khoán vốn"),
            base._line(59, 73, "15.823"),
            base._line(59, 74, "13.284"),
            ctg_topology,
        )
    ]
    documents.append(ctg)
    documents.append(
        base._mapped_document(
            "BID",
            56,
            "2025-12-31",
            "WRAPPED_DIRECT_DIVIDEND_LABEL_WITH_INTERLEAVED_VALUE_LINES",
            [(56, 82, "Năm nay"), (56, 83, "Năm trước")],
            [(56, 84, "Triệu VND"), (56, 85, "Triệu VND")],
            [
                _mapping(
                    base,
                    "ROOT",
                    56,
                    [(81, "THU NHẬP TỪ GÓP VỐN, MUA CỔ PHẦN")],
                    base._line(56, 103, "1.097.172"),
                    base._line(56, 104, "445.742"),
                    None,
                    standard,
                ),
                _mapping(
                    base,
                    "DIRECT_DIVIDEND",
                    56,
                    [
                        (86, "Cổ tức nhận được; lãi được chia trong năm từ góp"),
                        (89, "vốn, mua cổ phần"),
                    ],
                    base._line(56, 87, "112.395"),
                    base._line(56, 88, "26.104"),
                    "DIRECT_DIVIDEND",
                    standard,
                ),
                _mapping(
                    base,
                    "TRADING_EQUITY_DIVIDEND",
                    56,
                    [(90, "Từ chứng khoán vốn kinh doanh")],
                    base._line(56, 91, "42.295"),
                    base._line(56, 92, "24.220"),
                    "TRADING_EQUITY_DIVIDEND",
                    standard,
                ),
                _mapping(
                    base,
                    "INVESTMENT_EQUITY_DIVIDEND",
                    56,
                    [(93, "Từ chứng khoán vốn đầu tư")],
                    base._line(56, 94, "1.655"),
                    base._line(56, 95, "371"),
                    "INVESTMENT_EQUITY_DIVIDEND",
                    standard,
                ),
                _mapping(
                    base,
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    56,
                    [(96, "Từ góp vốn, đầu tư dài hạn")],
                    base._line(56, 97, "68.445"),
                    base._line(56, 98, "1.513"),
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    standard,
                ),
                _mapping(
                    base,
                    "EQUITY_METHOD",
                    56,
                    [
                        (99, "Phân chia lãi theo phương pháp vốn chủ sở hữu các"),
                        (102, "khoản đầu tư vào các công ty liên doanh, liên kết"),
                    ],
                    base._line(56, 100, "984.777"),
                    base._line(56, 101, "419.638"),
                    "EQUITY_METHOD",
                    standard,
                ),
            ],
            [
                (
                    "DIRECT_DIVIDEND",
                    [
                        "TRADING_EQUITY_DIVIDEND",
                        "INVESTMENT_EQUITY_DIVIDEND",
                        "LONG_TERM_CAPITAL_DIVIDEND",
                    ],
                    "THREE_DIVIDEND_SOURCES_EQUAL_DIRECT_DIVIDEND",
                ),
                (
                    "ROOT",
                    ["DIRECT_DIVIDEND", "EQUITY_METHOD"],
                    "DIRECT_DIVIDEND_PLUS_EQUITY_METHOD_EQUALS_TOTAL",
                ),
            ],
        )
    )
    documents.append(
        {
            "absence_evidence": {
                "complete_pdf_pages_scanned": True,
                "detailed_note_graph_match_count": 0,
                "negative_control_pages": [11],
                "reason": (
                    "The report prints only the income-statement aggregate on page 11; it "
                    "does not contain an Arabic-numbered two-period detailed note with the "
                    "capital-contribution/dividend child graph."
                ),
                "source_scope_absence_only": True,
            },
            "bank_code": "VIB",
            "equations": [],
            "mappings": [],
            "page_span": None,
            "period_axis": [],
            "presentation": "STATEMENT_AGGREGATE_ONLY_NO_DETAILED_NOTE",
            "source_period": None,
            "unit_evidence": [],
        }
    )
    return documents


def _annual_metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    source_only = [row for trial in trials for row in trial.get("verified_source_only_rows", [])]
    all_values = [
        value
        for trial in trials
        for group in (trial["verified_mappings"], trial.get("verified_source_only_rows", []))
        for row in group
        for value in row["values"]
    ]
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "authenticated_dash_zero_count": sum(
            value.get("pixel_transcription") == "-" and value.get("normalized_value") == 0
            for value in all_values
        ),
        "detailed_note_not_present_document_count": sum(
            trial["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            value.get("fresh_vietocr_numeric_status") == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            for value in all_values
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
    base.SCHEMA_FAMILY_END_DISPLAY_ORDER = 764
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
        else (_ for _ in ()).throw(_error("annual contribution/dividend period drifted"))
    )


def _inputs() -> tuple[ModuleType, dict[str, Any], dict[str, Any], dict[str, Any]]:
    base = _load_base()
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, _ = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    scan = base.scanner.build_capital_contribution_dividend_income_full_document_scan_v1(
        semantic_index
    )
    if scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("annual contribution/dividend structure scan identity drifted")
    _configure(base, scan["scan_id"])
    return base, semantic_index, crop_manifest, scan


def _assert_result(value: dict[str, Any]) -> dict[str, Any]:
    if not same_typed_json_v1(value.get("metrics"), _EXPECTED_METRICS):
        raise _error("annual contribution/dividend exact metrics drifted")
    for trial, code in zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True):
        mapped_ids = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        expected_status = (
            "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
            if code == "VIB"
            else (OPEN_SOURCE_TRIAL_STATUS if code == "CTG" else "VERIFIED_BY_CODEX")
        )
        expected_period = (
            "NOT_APPLICABLE_NO_DETAILED_NOTE"
            if code == "VIB"
            else "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        )
        if (
            trial["document_provenance"] != code
            or trial["status"] != expected_status
            or trial["page_span"] != _EXPECTED_PAGES[code]
            or mapped_ids != _EXPECTED_REPORT_NORM_IDS[code]
            or len(trial["verified_accounting_equations"]) != _EXPECTED_EQUATION_COUNTS[code]
            or trial["source_period_status"] != expected_period
        ):
            raise _error("annual contribution/dividend trial closure drifted")
    ctg = next(trial for trial in value["trials"] if trial["document_provenance"] == "CTG")
    if [row["gap_id"] for row in ctg["verified_source_only_rows"]] != ["CCDI-CTG-001"]:
        raise _error("annual contribution/dividend CTG combined-row gap drifted")
    return value


def _build_with_inputs(
    base: ModuleType,
    semantic_index: dict[str, Any],
    crop_manifest: dict[str, Any],
    scan: dict[str, Any],
) -> dict[str, Any]:
    review = base._review_blueprint()
    crop_sha = hashlib.sha256(canonical_json_bytes_v1(crop_manifest)).hexdigest()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    result = base.build_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1(
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
        base.validate_capital_contribution_dividend_income_8bank_codex_verified_mapping_replay_v1(
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
    )
    return _assert_result(replayed)


def build_annual_2025_capital_contribution_dividend_income_pixel_review_blueprint_v1() -> dict[
    str, Any
]:
    base, _semantic_index, _crop_manifest, _scan = _inputs()
    return base._review_blueprint()


def build_live_annual_2025_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1() -> (
    dict[str, Any]
):
    return _build_with_inputs(*_inputs())


def validate_live_annual_2025_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    rebuilt = build_live_annual_2025_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(value, rebuilt):
        raise _error("annual contribution/dividend result does not replay exactly")
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or (REVIEW_PATH if args.write_review else RESULT_PATH)
    value = (
        build_annual_2025_capital_contribution_dividend_income_pixel_review_blueprint_v1()
        if args.write_review
        else build_live_annual_2025_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1()
    )
    output.write_bytes(canonical_json_bytes_v1(value))
    if not args.write_review:
        print(value["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
