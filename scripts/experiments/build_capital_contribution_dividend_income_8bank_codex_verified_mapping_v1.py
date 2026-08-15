"""Verify capital-contribution, share and dividend income in eight reports."""

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
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_module(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


foundation = _load_module(
    "investment_activity_support_for_contribution_dividend_mapping",
    "build_investment_securities_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "contribution_dividend_scan_for_verified_mapping",
    "scan_capital_contribution_dividend_income_full_document_vietocr_v1.py",
)
support = foundation.support

FORMAT_VERSION = "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_ARABIC_"
    "NUMBERED_CAPITAL_CONTRIBUTION_SHARE_AND_DIVIDEND_INCOME_NOTE_VISIBLE_"
    "PDF_LABEL_PADDLEOCR_OR_NATIVE_SOURCE_NUMERIC_CHALLENGER_PERIOD_UNIT_"
    "ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_CANONICALIZATION_EXPORT_OR_"
    "PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0087-capital-contribution-dividend-income-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0087-capital-contribution-dividend-income-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = foundation.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = foundation.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = foundation.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = foundation.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "ccdifdsv1:scan:fcd44c4af997ffdb70e65fa3d941a8fd23e0e199e48a101c1abe74ede53e92c6"

_SCHEMA_EXPECTED = {
    1198: ("Thu nhập từ góp vốn, mua cổ phần và thu nhập cổ tức", 1142, 754),
    1199: ("Cổ tức nhận được trong kỳ từ góp vốn, mua cổ phần", 1198, 755),
    1200: ("Trong đó: + Từ chứng khoán Vốn kinh doanh", 1198, 756),
    1201: ("+ Từ chứng khoán Vốn đầu tư", 1198, 757),
    1202: ("+ Từ góp vốn, đầu tư dài hạn", 1198, 758),
    1203: (
        "Phân chia lãi/lỗ theo phương pháp vốn CSH của các khoản đầu tư vào các công ty liên doanh, liên kết",
        1198,
        759,
    ),
    1204: ("Các khoản thu nhập khác", 1198, 760),
}
_ROLE_TO_SCHEMA = {
    "ROOT": 1198,
    "DIRECT_DIVIDEND": 1199,
    "TRADING_EQUITY_DIVIDEND": 1200,
    "INVESTMENT_EQUITY_DIVIDEND": 1201,
    "LONG_TERM_CAPITAL_DIVIDEND": 1202,
    "EQUITY_METHOD": 1203,
    "OTHER_INCOME": 1204,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_seven_reviewed_detailed_notes": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "statement_aggregate_relabelled_as_detailed_note": False,
    "text_similarity_alone_used_for_mapping": False,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "dash_normalized_to_zero_only_with_visible_or_native_source_binding": True,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "optional_children_required_in_every_bank": False,
    "paddleocr_or_native_source_axis_used_as_semantic_anchor": False,
    "statement_aggregate_used_as_detailed_note": False,
    "vietocr_used_as_numeric_truth": False,
    "visible_pdf_pixels_reviewed": True,
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


class CapitalContributionDividendIncome8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, numbers, equations, or TM schema drifted."""


def _error(message: str) -> CapitalContributionDividendIncome8BankCodexVerifiedMappingV1Error:
    return CapitalContributionDividendIncome8BankCodexVerifiedMappingV1Error(message)


def _ref(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str) -> dict[str, Any]:
    return {"kind": "AUTHENTICATED_LINE", **_ref(page, line, text)}


def _dash(page: int, bbox: Sequence[int], pixel_rgb_sha256: str) -> dict[str, Any]:
    return {
        "bbox": list(bbox),
        "kind": "AUTHENTICATED_RENDER_PIXEL_DASH",
        "page_sequence": page,
        "pixel_rgb_sha256": pixel_rgb_sha256,
        "pixel_transcription": "-",
    }


def _mapping(
    role: str,
    label: Sequence[tuple[int, int, str]],
    current: dict[str, Any],
    comparative: dict[str, Any],
    graph_child_role: str | None,
    topology: str,
) -> dict[str, Any]:
    return {
        "graph_child_role": graph_child_role,
        "label": [_ref(page, line, text) for page, line, text in label],
        "report_norm_id": _ROLE_TO_SCHEMA[role],
        "role": role,
        "topology": topology,
        "values": {"COMPARATIVE_PERIOD": comparative, "CURRENT_PERIOD": current},
    }


def _mapped_document(
    code: str,
    page: int,
    source_period: str,
    presentation: str,
    period_lines: Sequence[tuple[int, int, str]],
    unit_lines: Sequence[tuple[int, int, str]],
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[tuple[str, Sequence[str], str]],
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "equations": [
            {"equation": name, "term_roles": list(terms), "total_role": total}
            for total, terms, name in equations
        ],
        "mappings": list(mappings),
        "page_span": [page, page],
        "period_axis": [_ref(p, line, text) for p, line, text in period_lines],
        "presentation": presentation,
        "source_period": source_period,
        "unit_evidence": [_ref(p, line, text) for p, line, text in unit_lines],
    }


def _review_documents() -> list[dict[str, Any]]:
    standard = "OPTIONAL_DIVIDEND_SOURCE_EQUITY_METHOD_OR_OTHER_CHILDREN_THEN_TOTAL"
    return [
        _mapped_document(
            "ACB",
            25,
            "2026-06-30",
            standard,
            [(25, 20, "Đến"), (25, 21, "Đến"), (25, 22, "30.6.2026"), (25, 23, "30.6.2025")],
            [(25, 24, "Triệu đồng"), (25, 25, "Triệu đồng")],
            [
                _mapping(
                    "ROOT",
                    [(25, 19, "THU NHẬP TỪ GÓP VỐN, MUA CỔ PHẦN")],
                    _line(25, 35, "68.059"),
                    _line(25, 36, "61.727"),
                    None,
                    standard,
                ),
                _mapping(
                    "TRADING_EQUITY_DIVIDEND",
                    [(25, 26, "Từ chứng khoán vốn kinh doanh")],
                    _line(25, 27, "43.587"),
                    _line(25, 28, "32.291"),
                    "TRADING_EQUITY_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "INVESTMENT_EQUITY_DIVIDEND",
                    [(25, 29, "Từ chứng khoán vốn đầu tư")],
                    _line(25, 30, "1.329"),
                    _line(25, 31, "2.762"),
                    "INVESTMENT_EQUITY_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    [(25, 32, "Từ góp vốn, đầu tư dài hạn")],
                    _line(25, 33, "23.143"),
                    _line(25, 34, "26.674"),
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
        _mapped_document(
            "MBB",
            48,
            "2026-06-30",
            "COLLAPSED_PARENT_ROW_THEN_IDENTICAL_TRAILING_TOTAL",
            [
                (48, 2, "Từ 01/01/2026"),
                (48, 3, "Từ 01/01/2025"),
                (48, 4, "đến 30/06/2026"),
                (48, 5, "đến 30/06/2025"),
            ],
            [(48, 6, "Triệu đồng"), (48, 7, "Triệu đồng")],
            [
                _mapping(
                    "ROOT",
                    [(48, 8, "Thu nhập từ góp vốn, mua cổ phần")],
                    _line(48, 11, "24.376"),
                    _line(48, 12, "27.214"),
                    "COLLAPSED_PARENT",
                    "COLLAPSED_PARENT_ROW_THEN_IDENTICAL_TRAILING_TOTAL",
                )
            ],
            [],
        ),
        _mapped_document(
            "VPB",
            64,
            "2026-03-31",
            "SINGLE_DIRECT_DIVIDEND_CHILD_THEN_IDENTICAL_TOTAL",
            [
                (64, 56, "Cho kỳ kế toán"),
                (64, 57, "Cho kỳ kế toán"),
                (64, 58, "3 tháng kết thúc"),
                (64, 59, "3 tháng kết thúc"),
                (64, 60, "ngày 31 tháng 3"),
                (64, 61, "ngày 31 tháng 3"),
                (64, 62, "năm 2026"),
                (64, 63, "năm 2025"),
            ],
            [(64, 64, "Triệu đồng"), (64, 65, "Triệu đồng")],
            [
                _mapping(
                    "ROOT",
                    [(64, 55, "THU NHẬP TỪ GÓP VỐN MUA CỔ PHẦN")],
                    _line(64, 69, "30.625"),
                    _line(64, 70, "-"),
                    None,
                    "SINGLE_DIRECT_DIVIDEND_CHILD_THEN_IDENTICAL_TOTAL",
                ),
                _mapping(
                    "DIRECT_DIVIDEND",
                    [(64, 66, "Cổ tức nhận được từ góp vốn, mua cổ phần")],
                    _line(64, 67, "30.625"),
                    _line(64, 68, "-"),
                    "DIRECT_DIVIDEND",
                    "SINGLE_DIRECT_DIVIDEND_CHILD_THEN_IDENTICAL_TOTAL",
                ),
            ],
            [("ROOT", ["DIRECT_DIVIDEND"], "DIRECT_DIVIDEND_EQUALS_TOTAL")],
        ),
        _mapped_document(
            "HDB",
            35,
            "2026-06-30",
            standard,
            [(35, 26, "Kỳ này"), (35, 27, "Kỳ trước")],
            [(35, 28, "Triệu VND"), (35, 29, "Triệu VND")],
            [
                _mapping(
                    "ROOT",
                    [(35, 25, "Thu nhập từ góp vốn, mua cổ phần")],
                    _line(35, 41, "1.168.079"),
                    _line(35, 42, "96.218"),
                    None,
                    standard,
                ),
                _mapping(
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    [(35, 30, "Cổ tức nhận trong kỳ từ góp vốn đầu tư dài hạn")],
                    _line(35, 31, "4.329"),
                    _line(35, 32, "4.896"),
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "TRADING_EQUITY_DIVIDEND",
                    [(35, 33, "Cổ tức nhận trong kỳ từ chứng khoán vốn kinh doanh")],
                    _line(35, 34, "1.352"),
                    _dash(
                        35,
                        (1496, 797, 1507, 807),
                        "ca7323346e29566afcbc63d0a2074b904cbf74de9b7e8f4753cd491590e493f0",
                    ),
                    "TRADING_EQUITY_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "EQUITY_METHOD",
                    [
                        (35, 35, "Phân chia lãi lỗ theo phương pháp vốn chủ sở hữu của các"),
                        (35, 38, "khoản đầu tư vào công ty liên kết"),
                    ],
                    _line(35, 36, "193.245"),
                    _line(35, 37, "91.322"),
                    "EQUITY_METHOD",
                    standard,
                ),
                _mapping(
                    "OTHER_INCOME",
                    [(35, 39, "Thu nhập từ hợp nhất kinh doanh")],
                    _line(35, 40, "969.153"),
                    _dash(
                        35,
                        (1496, 897, 1507, 907),
                        "266ec8f72c87fa24c0396b77c5c1c7f56c37636d32d6f6717cc92d77ca99ec5a",
                    ),
                    "OTHER_INCOME",
                    standard,
                ),
            ],
            [
                (
                    "ROOT",
                    [
                        "LONG_TERM_CAPITAL_DIVIDEND",
                        "TRADING_EQUITY_DIVIDEND",
                        "EQUITY_METHOD",
                        "OTHER_INCOME",
                    ],
                    "OPTIONAL_CHILDREN_EQUAL_TOTAL",
                )
            ],
        ),
        _mapped_document(
            "VCB",
            39,
            "2026-06-30",
            standard,
            [
                (39, 54, "Giai đoạn"),
                (39, 55, "Giai đoạn"),
                (39, 56, "từ 1/1/2026"),
                (39, 57, "từ 1/1/2025"),
                (39, 58, "đến 30/6/2026"),
                (39, 59, "đến 30/6/2025"),
            ],
            [(39, 60, "Triệu VND"), (39, 61, "Triệu VND")],
            [
                _mapping(
                    "ROOT",
                    [(39, 53, "Thu nhập từ góp vốn, mua cổ phần")],
                    _line(39, 76, "117.507"),
                    _line(39, 77, "106.195"),
                    None,
                    standard,
                ),
                _mapping(
                    "DIRECT_DIVIDEND",
                    [(39, 63, "Cổ tức nhận được trong kỳ từ góp vốn, mua cổ phần")],
                    _line(39, 64, "22.952"),
                    _line(39, 65, "21.806"),
                    "DIRECT_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    [(39, 66, "Từ góp vốn, đầu tư dài hạn")],
                    _line(39, 67, "21.157"),
                    _line(39, 68, "20.490"),
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "TRADING_EQUITY_DIVIDEND",
                    [(39, 69, "Từ chứng khoán vốn kinh doanh")],
                    _line(39, 70, "1.795"),
                    _line(39, 71, "1.316"),
                    "TRADING_EQUITY_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "EQUITY_METHOD",
                    [
                        (39, 72, "Phân chia lãi theo phương pháp vốn chủ sở hữu của các khoản"),
                        (39, 73, "đầu tư vào các công ty liên doanh, liên kết"),
                    ],
                    _line(39, 74, "94.555"),
                    _line(39, 75, "84.389"),
                    "EQUITY_METHOD",
                    standard,
                ),
            ],
            [
                (
                    "DIRECT_DIVIDEND",
                    ["LONG_TERM_CAPITAL_DIVIDEND", "TRADING_EQUITY_DIVIDEND"],
                    "DIVIDEND_SUBSOURCES_EQUAL_DIRECT_DIVIDEND",
                ),
                (
                    "ROOT",
                    ["DIRECT_DIVIDEND", "EQUITY_METHOD"],
                    "DIRECT_DIVIDEND_PLUS_EQUITY_METHOD_EQUALS_TOTAL",
                ),
            ],
        ),
        _mapped_document(
            "CTG",
            46,
            "2026-06-30",
            standard,
            [
                (46, 26, "Giai đoạn tài chính"),
                (46, 27, "Giai đoạn tài chính"),
                (46, 28, "từ 01/01/2026 đến"),
                (46, 29, "từ 01/01/2025 đến"),
                (46, 30, "hết 30/06/2026"),
                (46, 31, "hết 30/06/2025"),
            ],
            [(46, 32, "triệu đồng"), (46, 33, "triệu đồng")],
            [
                _mapping(
                    "ROOT",
                    [(46, 25, "THU NHẬP TỪ GÓP VỐN, MUA CỔ PHẦN")],
                    _line(46, 44, "197.840"),
                    _line(46, 45, "240.219"),
                    None,
                    standard,
                ),
                _mapping(
                    "DIRECT_DIVIDEND",
                    [(46, 34, "Thu từ chứng khoán Vốn")],
                    _line(46, 35, "10.576"),
                    _line(46, 36, "9.504"),
                    "COMBINED_EQUITY_SECURITIES_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    [(46, 37, "Thu từ góp vốn, đầu tư dài hạn")],
                    _line(46, 38, "32.935"),
                    _line(46, 39, "28.245"),
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "EQUITY_METHOD",
                    [
                        (46, 40, "Phân chia lãi/lỗ theo phương pháp vốn CSH của các"),
                        (46, 43, "khoản đầu tư vào các công ty liên doanh, liên kết"),
                    ],
                    _line(46, 41, "154.329"),
                    _line(46, 42, "202.470"),
                    "EQUITY_METHOD",
                    standard,
                ),
            ],
            [
                (
                    "ROOT",
                    ["DIRECT_DIVIDEND", "LONG_TERM_CAPITAL_DIVIDEND", "EQUITY_METHOD"],
                    "THREE_INCOME_COMPONENTS_EQUAL_TOTAL",
                )
            ],
        ),
        _mapped_document(
            "BID",
            29,
            "2026-06-30",
            "DOCUMENT_UNIT_INHERITED_OPTIONAL_CHILDREN_THEN_TOTAL",
            [
                (29, 58, "Từ 01/01/2026 đến"),
                (29, 59, "Từ 01/01/2025 đến"),
                (29, 60, "30/06/2026"),
                (29, 61, "30/06/2025"),
            ],
            [(28, 58, "Đơn vị: Triệu VND")],
            [
                _mapping(
                    "ROOT",
                    [(29, 57, "THU NHẬP TỪ GÓP VỐN, MUA CỔ PHẦN")],
                    _line(29, 78, "363,094"),
                    _line(29, 79, "235,537"),
                    None,
                    "DOCUMENT_UNIT_INHERITED_OPTIONAL_CHILDREN_THEN_TOTAL",
                ),
                _mapping(
                    "DIRECT_DIVIDEND",
                    [
                        (29, 62, "Cổ tức nhận được; lãi được chia trong kỳ từ góp vốn, mua"),
                        (29, 63, "cổ phần"),
                    ],
                    _line(29, 64, "55,547"),
                    _line(29, 65, "18,391"),
                    "DIRECT_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "TRADING_EQUITY_DIVIDEND",
                    [(29, 66, "Từ chứng khoán Vốn kinh doanh")],
                    _line(29, 67, "20,946"),
                    _line(29, 68, "16,913"),
                    "TRADING_EQUITY_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "INVESTMENT_EQUITY_DIVIDEND",
                    [(29, 69, "Từ chứng khoán Vốn đầu tư")],
                    _dash(
                        29,
                        (1137, 1663, 1148, 1674),
                        "55700070fdbcb5eb2b7a28b966b5df2f99e4a7928dfc5e23594b03f6c7463210",
                    ),
                    _line(29, 70, "176"),
                    "INVESTMENT_EQUITY_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    [(29, 71, "Từ góp vốn, đầu tư dài hạn")],
                    _line(29, 72, "34,601"),
                    _line(29, 73, "1,302"),
                    "LONG_TERM_CAPITAL_DIVIDEND",
                    standard,
                ),
                _mapping(
                    "EQUITY_METHOD",
                    [
                        (29, 74, "Phân chia lãi/lỗ theo phương pháp vốn CSH của các khoản"),
                        (29, 77, "đầu tư vào các công ty liên doanh, liên kết"),
                    ],
                    _line(29, 75, "307,547"),
                    _line(29, 76, "217,146"),
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
        ),
        {
            "absence_evidence": {
                "complete_pdf_pages_scanned": True,
                "detailed_note_graph_match_count": 0,
                "negative_control_pages": [8],
                "reason": "The report contains only the income-statement aggregate, without an Arabic-numbered two-period detailed note and child graph.",
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
        },
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "reviewer": {"kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW", "review_run_id": "E-0087"},
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0087:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex contribution/dividend pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    return foundation._document(items, code, label)


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    return foundation._page(document, page_sequence, label)


def _semantic_evidence(
    axis_document: Mapping[str, Any], semantic_document: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any]:
    return foundation._semantic_evidence(axis_document, semantic_document, item)


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
    values = [
        value
        for trial in trials
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
    ]
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "authenticated_dash_zero_count": sum(
            value.get("pixel_transcription") == "-" and value.get("normalized_value") == 0
            for value in values
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
            for value in values
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "verified_value_cell_count": len(values),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("contribution/dividend result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"]
        != "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("contribution/dividend result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status")
            not in {
                "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
                "VERIFIED_BY_CODEX",
                "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT",
            }
            or any(
                mapping.get("status") != "VERIFIED_BY_CODEX"
                for mapping in trial.get("verified_mappings", [])
            )
        ):
            raise _error("contribution/dividend trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0087:result:" + canonical_json_sha256_v1(material):
        raise _error("contribution/dividend result identity drifted")
    return canonical_clone_v1(value)


def _verified_value(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    ref: Mapping[str, Any],
) -> dict[str, Any]:
    page_number = ref["page_sequence"]
    crop_page = _page(crop_document, page_number, "crop manifest")
    if ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH":
        return foundation.foundation._pixel_dash_value(crop_page, ref)
    if ref["kind"] != "AUTHENTICATED_LINE":
        raise _error("contribution/dividend value reference kind drifted")
    axis_page = _page(axis_document, page_number, "accounting axis")
    semantic_page = _page(semantic_document, page_number, "semantic index")
    source_texts = support._source_line_axis(crop_page)
    evidence = support._source_value(
        axis_page,
        semantic_page,
        crop_page,
        source_texts,
        {"line_index": ref["line_index"], "pixel_transcription": ref["pixel_transcription"]},
    )
    try:
        proposal = support._money(evidence["fresh_vietocr_numeric_proposal"])
    except ValueError:
        proposal = None
    return {
        **evidence,
        "fresh_vietocr_numeric_status": (
            "MATCHES_SOURCE_NUMERIC_CHALLENGER"
            if proposal == evidence["normalized_value"]
            else "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
        ),
        "page_sequence": page_number,
    }


def _equations(
    by_role: Mapping[str, Mapping[str, Any]], plans: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    result = []
    for plan in plans:
        for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):

            def value(role: str, *, axis_role: str = axis_role) -> int:
                matches = [
                    item for item in by_role[role]["values"] if item["axis_role"] == axis_role
                ]
                if len(matches) != 1:
                    raise _error("equation mapping does not contain one period value")
                return matches[0]["normalized_value"]

            terms = [value(role) for role in plan["term_roles"]]
            total = value(plan["total_role"])
            computed = sum(terms)
            if computed != total:
                raise _error(
                    f"contribution/dividend equation does not close: {plan['equation']} {axis_role}"
                )
            result.append(
                {
                    "computed_value": computed,
                    "equation": plan["equation"],
                    "period_role": axis_role,
                    "status": "CORROBORATED_EXACT",
                    "term_report_norm_ids": [_ROLE_TO_SCHEMA[role] for role in plan["term_roles"]],
                    "term_values": terms,
                    "total_report_norm_id": _ROLE_TO_SCHEMA[plan["total_role"]],
                }
            )
    return result


def build_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1(
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
    axis_projection = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    scanner.validate_capital_contribution_dividend_income_full_document_scan_replay_v1(
        structure_scan, semantic_index
    )
    if (
        axis_projection.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or type(crop_manifest) is not dict
    ):
        raise _error("fixed semantic axis, crop manifest, or structure scan drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(reviewed_documents, code, "pixel review")
        scan_trial = _document(structure_scan["trials"], code, "structure scan")
        matcher = scan_trial["matcher_result"]
        base = {
            "document_ordinal": ordinal,
            "document_provenance": code,
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
            "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
        }
        if reviewed["absence_evidence"] is not None:
            if matcher["uniqueness"]["status"] == "UNIQUE_FULL_MATCH":
                raise _error("absent detailed contribution/dividend note unexpectedly matched")
            trials.append(
                {
                    **base,
                    "absence_evidence": canonical_clone_v1(reviewed["absence_evidence"]),
                    "page_span": None,
                    "period_evidence": [],
                    "presentation": reviewed["presentation"],
                    "source_period_status": "NOT_APPLICABLE_NO_DETAILED_NOTE",
                    "status": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                }
            )
            continue
        if not same_typed_json_v1(
            matcher["uniqueness"], {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        ) or not same_typed_json_v1(matcher["regions"][0]["page_span"], reviewed["page_span"]):
            raise _error("reviewed region is not the unique whole-PDF contribution/dividend graph")
        expected_graph_roles = sorted(
            mapping["graph_child_role"]
            for mapping in reviewed["mappings"]
            if mapping["graph_child_role"] is not None
        )
        if not same_typed_json_v1(
            matcher["regions"][0]["layout"]["child_roles"], expected_graph_roles
        ):
            raise _error("reviewed child roles differ from whole-PDF contribution/dividend graph")
        axis_document = _document(axis_projection["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        verified_mappings = []
        for mapping in reviewed["mappings"]:
            values = [
                {
                    "axis_role": axis_role,
                    **_verified_value(axis_document, semantic_document, crop_document, ref),
                }
                for axis_role, ref in mapping["values"].items()
            ]
            verified_mappings.append(
                {
                    "label_evidence": [
                        _semantic_evidence(axis_document, semantic_document, item)
                        for item in mapping["label"]
                    ],
                    "role": mapping["role"],
                    "schema_binding": _schema_binding(
                        schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                    ),
                    "status": "VERIFIED_BY_CODEX",
                    "topology": mapping["topology"],
                    "values": values,
                }
            )
        equations = _equations(
            {item["role"]: item for item in verified_mappings}, reviewed["equations"]
        )
        source_period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "page_span": list(reviewed["page_span"]),
                "period_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["period_axis"]
                ],
                "presentation": reviewed["presentation"],
                "source_period_status": source_period_status,
                "status": "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
                if source_period_status.endswith("NOT_Q2")
                else "VERIFIED_BY_CODEX",
                "unit_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest_sha256": crop_manifest_sha256,
            "pixel_review_sha256": review_sha256,
            "schema_authority": canonical_clone_v1(schema_authority),
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "schema_family": {
            "family_end_display_order": 760,
            "family_root_report_norm_id": 1198,
            "mapped_report_norm_ids": sorted(_SCHEMA_EXPECTED),
        },
        "state": "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0087:result:" + canonical_json_sha256_v1(material)}
    )


def validate_capital_contribution_dividend_income_8bank_codex_verified_mapping_replay_v1(
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
    rebuilt = build_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1(
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
        raise _error("contribution/dividend verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _live_inputs() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_capital_contribution_dividend_income_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "review": review,
        "review_sha256": review_sha,
        "schema_authority": schema_authority,
        "schema_by_id": schema_by_id,
        "semantic_index": semantic_index,
        "structure_scan": structure_scan,
    }


def build_live_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    return build_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1(
        **_live_inputs()
    )


def validate_live_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    return validate_capital_contribution_dividend_income_8bank_codex_verified_mapping_replay_v1(
        value, **_live_inputs()
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
        _write(
            RESULT_PATH,
            build_live_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1(),
        )
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
