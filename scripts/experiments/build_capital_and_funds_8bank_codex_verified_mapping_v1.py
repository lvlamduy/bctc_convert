"""Verify the bounded capital-and-funds disclosure across eight reports.

The whole-document matcher is bank blind and already proves one unique region
per report.  This stage binds the six readable portrait tables to visible PDF
labels, the independent source numeric challenger, accounting equations, and
the live TM schema.  BID and VIB remain explicit structural-only outcomes:
their rotated VietOCR rescue is semantic-anchor evidence, never numeric truth.
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
    "government_nhnn_support_for_capital_and_funds",
    "build_government_nhnn_liabilities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "capital_and_funds_scan_for_verified_mapping",
    "scan_capital_and_funds_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "CAPITAL_AND_FUNDS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "CAPITAL_AND_FUNDS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "CAPITAL_AND_FUNDS_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "e0078:result:"
REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "e0078:pixel-review:"
REVIEW_RUN_ID = "E-0078"
STRUCTURE_SCAN_STATE = "FULL_DOCUMENT_CAPITAL_AND_FUNDS_SCAN_COMPLETE"
FAMILY_END_DISPLAY_ORDER = 672
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_AND_ROTATED_VIETOCR_BANK_BLIND_"
    "CAPITAL_FUNDS_GRAPH_VISIBLE_PDF_LABEL_SOURCE_NUMERIC_CHALLENGER_PERIOD_"
    "UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_ROTATED_NUMERIC_ROWS_UNRESOLVED_"
    "NO_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0078-capital-and-funds-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "caffdsv1:scan:cb3aec79185072a97f4ab5d62322a74cd523652461c90790bee4b1b2f102668c"

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
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_six_source_numeric_readable_tables": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "rotated_rescue_used_for_semantic_structure_only": True,
    "source_numeric_challenger_and_accounting_closure_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_retained": True,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "bid_or_vib_rotated_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "optional_equity_columns_required_in_every_bank": False,
    "source_subtotals_and_children_double_counted": False,
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
_ALTERNATE_VALUE_VERIFIER: Any = None
_EXTRA_INPUT_REFS: dict[str, Any] = {}


class CapitalAndFunds8BankCodexVerifiedMappingV1Error(ValueError):
    """The fixed structure, pixel, numeric, equation, or schema evidence drifted."""


def _error(message: str) -> CapitalAndFunds8BankCodexVerifiedMappingV1Error:
    return CapitalAndFunds8BankCodexVerifiedMappingV1Error(message)


def _label(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str, multiplier: int = 1) -> dict[str, Any]:
    return {
        "line_index": line,
        "multiplier": multiplier,
        "page_sequence": page,
        "pixel_transcription": text,
    }


def _mapping(
    report_norm_id: int,
    role: str,
    labels: Sequence[dict[str, Any]],
    values: Mapping[str, Sequence[dict[str, Any]]],
    topology: str = "EQUITY_COLUMN_CROSSED_WITH_VISIBLE_MOVEMENT_ROW",
) -> dict[str, Any]:
    return {
        "labels": list(labels),
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {axis: list(refs) for axis, refs in values.items()},
    }


def _equation(
    name: str,
    axis_role: str,
    terms: Sequence[dict[str, Any]],
    total: dict[str, Any],
) -> dict[str, Any]:
    return {"axis_role": axis_role, "name": name, "terms": list(terms), "total": total}


def _open(
    item_id: str,
    source_label: str,
    reason: str,
    labels: Sequence[dict[str, Any]] = (),
    values: Mapping[str, Sequence[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "labels": list(labels),
        "reason": reason,
        "source_label": source_label,
        "status": "UNRESOLVED",
        "values": {axis: list(refs) for axis, refs in (values or {}).items()},
    }


def _doc(
    code: str,
    page_span: tuple[int, int],
    owner: dict[str, Any] | None,
    heading: dict[str, Any] | None,
    period_axis: Sequence[dict[str, Any]],
    unit_evidence: Sequence[dict[str, Any]],
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[dict[str, Any]],
    unresolved: Sequence[dict[str, Any]],
    *,
    source_period: str = "2026-06-30",
    presentation: str = "EQUITY_COLUMNS_WITH_OPENING_MOVEMENTS_AND_CLOSING_ROWS",
) -> dict[str, Any]:
    structural_only = not mappings
    return {
        "bank_code": code,
        "disposition": (
            "STRUCTURE_VERIFIED_NUMERIC_MAPPING_UNRESOLVED"
            if structural_only
            else ("VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS" if unresolved else "VERIFIED_BY_CODEX")
        ),
        "equations": list(equations),
        "heading": heading,
        "mappings": list(mappings),
        "owner": owner,
        "page_span": list(page_span),
        "period_axis": list(period_axis),
        "presentation": presentation,
        "source_period": source_period,
        "unit_evidence": list(unit_evidence),
        "unmapped_source_rows": list(unresolved),
    }


def _review_documents() -> list[dict[str, Any]]:
    p = 23
    acb = _doc(
        "ACB",
        (23, 24),
        _label(p, 20, "VỐN CHỦ SỞ HỮU"),
        _label(p, 37, "Tình hình thay đổi vốn chủ sở hữu"),
        [_label(p, 44, "1.1.2026"), _label(p, 47, "30.6.2026")],
        [_label(p, 38, "Đơn vị: Triệu đồng")],
        [
            _mapping(
                1129,
                "OPENING_TOTAL",
                [_label(p, 39, "Số dư"), _label(p, 44, "1.1.2026")],
                {"OPENING": [_line(p, 75, "94.519.719")]},
                "PRINTED_OPENING_TOTAL",
            ),
            _mapping(
                6019,
                "INCREASE_TOTAL",
                [_label(p, 40, "Tăng"), _label(p, 45, "trong kỳ")],
                {"INCREASE": [_line(p, 76, "15.290.520")]},
                "PRINTED_INCREASE_TOTAL",
            ),
            _mapping(
                6020,
                "DECREASE_TOTAL",
                [_label(p, 41, "Giảm"), _label(p, 46, "trong kỳ")],
                {"DECREASE": [_line(p, 77, "(10.495.721)")]},
                "PRINTED_SIGNED_DECREASE_TOTAL",
            ),
            _mapping(
                1141,
                "CLOSING_TOTAL",
                [_label(p, 42, "Số dư"), _label(p, 47, "30.6.2026")],
                {"CLOSING": [_line(p, 78, "99.314.518")]},
                "PRINTED_CLOSING_TOTAL",
            ),
            _mapping(
                5984,
                "CHARTER_CAPITAL",
                [_label(p, 48, "Vốn điều lệ")],
                {"OPENING": [_line(p, 49, "51.366.566")], "CLOSING": [_line(p, 50, "51.366.566")]},
            ),
            _mapping(
                6011,
                "SHARE_PREMIUM",
                [_label(p, 51, "Thặng dư vốn cổ phần")],
                {"OPENING": [_line(p, 52, "271.779")], "CLOSING": [_line(p, 53, "271.779")]},
            ),
            _mapping(
                6012,
                "OTHER_CAPITAL",
                [_label(p, 54, "Vốn khác")],
                {"INCREASE": [_line(p, 55, "6.677.654")], "CLOSING": [_line(p, 56, "6.677.654")]},
            ),
            _mapping(
                6014,
                "FINANCIAL_RESERVE",
                [_label(p, 57, "Quỹ dự phòng tài chính")],
                {"OPENING": [_line(p, 58, "10.575.595")], "CLOSING": [_line(p, 59, "10.575.595")]},
            ),
            _mapping(
                6013,
                "CAPITAL_RESERVE",
                [_label(p, 60, "Quỹ dự trữ bổ sung vốn điều lệ")],
                {"OPENING": [_line(p, 61, "6.519.540")], "CLOSING": [_line(p, 62, "6.519.540")]},
            ),
            _mapping(
                6015,
                "OTHER_FUNDS",
                [_label(p, 63, "Quỹ khác")],
                {"OPENING": [_line(p, 64, "487.926")], "CLOSING": [_line(p, 65, "487.926")]},
            ),
            _mapping(
                6016,
                "FX_DIFFERENCE",
                [_label(p, 66, "Chênh lệch tỷ giá hối đoái")],
                {"DECREASE": [_line(p, 67, "(122.407)")], "CLOSING": [_line(p, 68, "(122.407)")]},
            ),
            _mapping(
                6017,
                "RETAINED_EARNINGS",
                [_label(p, 69, "Lợi nhuận chưa phân phối")],
                {
                    "OPENING": [_line(p, 70, "25.298.313")],
                    "INCREASE": [_line(p, 71, "8.612.866")],
                    "DECREASE": [_line(p, 72, "(10.373.314)")],
                    "CLOSING": [_line(p, 73, "23.537.865")],
                },
            ),
        ],
        [
            _equation(
                "EQUITY_COLUMNS_TO_OPENING_TOTAL",
                "OPENING",
                [
                    _line(p, 49, "51.366.566"),
                    _line(p, 52, "271.779"),
                    _line(p, 58, "10.575.595"),
                    _line(p, 61, "6.519.540"),
                    _line(p, 64, "487.926"),
                    _line(p, 70, "25.298.313"),
                ],
                _line(p, 75, "94.519.719"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_INCREASE_TOTAL",
                "INCREASE",
                [_line(p, 55, "6.677.654"), _line(p, 71, "8.612.866")],
                _line(p, 76, "15.290.520"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_DECREASE_TOTAL",
                "DECREASE",
                [_line(p, 67, "(122.407)"), _line(p, 72, "(10.373.314)")],
                _line(p, 77, "(10.495.721)"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_CLOSING_TOTAL",
                "CLOSING",
                [
                    _line(p, 50, "51.366.566"),
                    _line(p, 53, "271.779"),
                    _line(p, 56, "6.677.654"),
                    _line(p, 59, "10.575.595"),
                    _line(p, 62, "6.519.540"),
                    _line(p, 65, "487.926"),
                    _line(p, 68, "(122.407)"),
                    _line(p, 73, "23.537.865"),
                ],
                _line(p, 78, "99.314.518"),
            ),
        ],
        [],
    )

    p = 44
    mbb = _doc(
        "MBB",
        (44, 45),
        _label(p, 41, "Vốn và quỹ của Tổ chức tín dụng"),
        _label(p, 42, "Báo cáo thay đổi vốn và các quỹ hợp nhất"),
        [_label(p, 50, "Dư đầu"), _label(p, 51, "Dư cuối")],
        [_label(p, 46, "Đơn vị: triệu đồng")],
        [
            _mapping(
                1129,
                "OPENING_TOTAL",
                [_label(p, 50, "Dư đầu")],
                {"OPENING": [_line(p, 94, "142.022.525")]},
                "PRINTED_OPENING_TOTAL",
            ),
            _mapping(
                6019,
                "INCREASE_TOTAL",
                [_label(p, 52, "Tăng")],
                {"INCREASE": [_line(p, 95, "23.217.390")]},
                "PRINTED_INCREASE_TOTAL",
            ),
            _mapping(
                6020,
                "DECREASE_TOTAL",
                [_label(p, 47, "Trích lập"), _label(p, 48, "Sử dụng"), _label(p, 53, "Giảm")],
                {"DECREASE": [_line(p, 96, "(8.477.271)")]},
                "PRINTED_SIGNED_DECREASE_TOTAL",
            ),
            _mapping(
                1141,
                "CLOSING_TOTAL",
                [_label(p, 51, "Dư cuối")],
                {"CLOSING": [_line(p, 97, "156.762.644")]},
                "PRINTED_CLOSING_TOTAL",
            ),
            _mapping(
                5984,
                "CHARTER_CAPITAL",
                [_label(p, 54, "Vốn điều lệ")],
                {"OPENING": [_line(p, 55, "80.549.999")], "CLOSING": [_line(p, 56, "80.549.999")]},
            ),
            _mapping(
                6011,
                "SHARE_PREMIUM",
                [_label(p, 57, "Thặng dư vốn cổ phần")],
                {"OPENING": [_line(p, 58, "1.304.334")], "CLOSING": [_line(p, 59, "1.304.334")]},
            ),
            _mapping(
                6012,
                "OTHER_CAPITAL",
                [_label(p, 60, "Vốn khác")],
                {"OPENING": [_line(p, 61, "2.111.211")], "CLOSING": [_line(p, 62, "2.111.211")]},
            ),
            _mapping(
                6013,
                "CAPITAL_RESERVE",
                [_label(p, 63, "Quỹ dự trữ bổ sung vốn"), _label(p, 64, "điều lệ")],
                {
                    "OPENING": [_line(p, 65, "6.972.588")],
                    "INCREASE": [_line(p, 66, "2.745.820")],
                    "CLOSING": [_line(p, 67, "9.718.408")],
                },
            ),
            _mapping(
                6014,
                "FINANCIAL_RESERVE",
                [_label(p, 68, "Quỹ dự phòng tài chính")],
                {
                    "OPENING": [_line(p, 69, "11.513.914")],
                    "INCREASE": [_line(p, 70, "2.459.690")],
                    "DECREASE": [_line(p, 71, "(88)")],
                    "CLOSING": [_line(p, 72, "13.973.516")],
                },
            ),
            _mapping(
                6015,
                "OTHER_FUNDS",
                [_label(p, 73, "Quỹ khác")],
                {
                    "OPENING": [_line(p, 74, "904.382")],
                    "INCREASE": [_line(p, 75, "685.087")],
                    "DECREASE": [_line(p, 76, "(133.701)")],
                    "CLOSING": [_line(p, 77, "1.455.768")],
                },
            ),
            _mapping(
                6016,
                "FX_DIFFERENCE",
                [_label(p, 78, "Chênh lệch tỷ giá hối đoái")],
                {
                    "OPENING": [_line(p, 79, "202.211")],
                    "INCREASE": [_line(p, 80, "687")],
                    "CLOSING": [_line(p, 81, "202.898")],
                },
            ),
            _mapping(
                6017,
                "RETAINED_EARNINGS",
                [_label(p, 82, "Lợi nhuận chưa phân phối")],
                {
                    "OPENING": [_line(p, 83, "32.577.391")],
                    "INCREASE": [_line(p, 84, "15.744.575")],
                    "DECREASE": [_line(p, 85, "(8.301.117)")],
                    "CLOSING": [_line(p, 86, "40.020.849")],
                },
            ),
            _mapping(
                6018,
                "NON_CONTROLLING_INTEREST",
                [_label(p, 87, "Lợi ích cổ đông không"), _label(p, 88, "kiểm soát")],
                {
                    "OPENING": [_line(p, 89, "5.886.495")],
                    "INCREASE": [_line(p, 90, "1.581.531")],
                    "DECREASE": [_line(p, 91, "(42.365)")],
                    "CLOSING": [_line(p, 92, "7.425.661")],
                },
            ),
        ],
        [
            _equation(
                "EQUITY_COLUMNS_TO_OPENING_TOTAL",
                "OPENING",
                [
                    _line(p, i, text)
                    for i, text in [
                        (55, "80.549.999"),
                        (58, "1.304.334"),
                        (61, "2.111.211"),
                        (65, "6.972.588"),
                        (69, "11.513.914"),
                        (74, "904.382"),
                        (79, "202.211"),
                        (83, "32.577.391"),
                        (89, "5.886.495"),
                    ]
                ],
                _line(p, 94, "142.022.525"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_INCREASE_TOTAL",
                "INCREASE",
                [
                    _line(p, i, text)
                    for i, text in [
                        (66, "2.745.820"),
                        (70, "2.459.690"),
                        (75, "685.087"),
                        (80, "687"),
                        (84, "15.744.575"),
                        (90, "1.581.531"),
                    ]
                ],
                _line(p, 95, "23.217.390"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_DECREASE_TOTAL",
                "DECREASE",
                [
                    _line(p, 71, "(88)"),
                    _line(p, 76, "(133.701)"),
                    _line(p, 85, "(8.301.117)"),
                    _line(p, 91, "(42.365)"),
                ],
                _line(p, 96, "(8.477.271)"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_CLOSING_TOTAL",
                "CLOSING",
                [
                    _line(p, i, text)
                    for i, text in [
                        (56, "80.549.999"),
                        (59, "1.304.334"),
                        (62, "2.111.211"),
                        (67, "9.718.408"),
                        (72, "13.973.516"),
                        (77, "1.455.768"),
                        (81, "202.898"),
                        (86, "40.020.849"),
                        (92, "7.425.661"),
                    ]
                ],
                _line(p, 97, "156.762.644"),
            ),
        ],
        [],
    )

    p = 60
    vp_headers = {
        5984: [_label(p, 21, "Vốn điều lệ")],
        6011: [_label(p, 14, "Thặng dư"), _label(p, 22, "vốn cổ phần")],
        6013: [_label(p, 9, "Quỹ dự trữ"), _label(p, 15, "bổ sung"), _label(p, 23, "vốn điều lệ")],
        6014: [_label(p, 10, "Quỹ dự phòng"), _label(p, 16, "tài chính")],
        6017: [_label(p, 12, "Lợi nhuận"), _label(p, 19, "chưa phân"), _label(p, 27, "phối")],
        6018: [
            _label(p, 8, "Lợi ích của"),
            _label(p, 13, "cổ đông"),
            _label(p, 20, "không kiểm"),
            _label(p, 28, "soát"),
        ],
    }
    vpb = _doc(
        "VPB",
        (60, 61),
        _label(p, 5, "VỐN VÀ CÁC QUỸ"),
        _label(p, 7, "Báo cáo tình hình thay đổi vốn chủ sở hữu"),
        [
            _label(p, 102, "Tại ngày 31 tháng 12"),
            _label(p, 103, "năm 2025"),
            _label(p, 143, "Tại ngày 31 tháng 3"),
            _label(p, 144, "năm 2026"),
        ],
        [_label(p, i, "Triệu đồng") for i in range(30, 39)],
        [
            _mapping(
                1129,
                "OPENING_TOTAL",
                [_label(p, 102, "Tại ngày 31 tháng 12"), _label(p, 103, "năm 2025")],
                {"OPENING": [_line(p, 112, "180.275.629")]},
                "PRINTED_OPENING_TOTAL",
            ),
            _mapping(
                1141,
                "CLOSING_TOTAL",
                [_label(p, 143, "Tại ngày 31 tháng 3"), _label(p, 144, "năm 2026")],
                {"CLOSING": [_line(p, 153, "186.604.801")]},
                "PRINTED_CLOSING_TOTAL",
            ),
            *[
                _mapping(
                    schema_id,
                    role,
                    vp_headers[schema_id],
                    {
                        "OPENING": [_line(p, opening, opening_text)],
                        "CLOSING": [_line(p, closing, closing_text)],
                    },
                )
                for schema_id, role, opening, opening_text, closing, closing_text in [
                    (5984, "CHARTER_CAPITAL", 104, "79.339.236", 145, "79.339.236"),
                    (6011, "SHARE_PREMIUM", 105, "23.992.546", 146, "23.992.546"),
                    (6013, "CAPITAL_RESERVE", 106, "5.948.642", 147, "5.959.060"),
                    (6014, "FINANCIAL_RESERVE", 107, "12.584.514", 148, "12.584.514"),
                    (6017, "RETAINED_EARNINGS", 110, "45.969.647", 151, "52.157.601"),
                    (6018, "NON_CONTROLLING_INTEREST", 111, "12.372.286", 152, "12.503.086"),
                ]
            ],
        ],
        [
            _equation(
                "EQUITY_COLUMNS_TO_OPENING_TOTAL",
                "OPENING",
                [
                    _line(p, i, text)
                    for i, text in [
                        (104, "79.339.236"),
                        (105, "23.992.546"),
                        (106, "5.948.642"),
                        (107, "12.584.514"),
                        (108, "68.758"),
                        (110, "45.969.647"),
                        (111, "12.372.286"),
                    ]
                ],
                _line(p, 112, "180.275.629"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_CLOSING_TOTAL",
                "CLOSING",
                [
                    _line(p, i, text)
                    for i, text in [
                        (145, "79.339.236"),
                        (146, "23.992.546"),
                        (147, "5.959.060"),
                        (148, "12.584.514"),
                        (149, "68.758"),
                        (151, "52.157.601"),
                        (152, "12.503.086"),
                    ]
                ],
                _line(p, 153, "186.604.801"),
            ),
        ],
        [
            _open(
                "CAF-001",
                "Quỹ đầu tư phát triển",
                "NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL",
                [_label(p, 11, "Quỹ đầu tư"), _label(p, 17, "phát triển")],
                {"OPENING": [_line(p, 108, "68.758")], "CLOSING": [_line(p, 149, "68.758")]},
            ),
            _open(
                "CAF-002",
                "Cổ phiếu quỹ",
                "NO_EXACT_EQUITY_BALANCE_LEAF; VISIBLE_DASHES_ARE_NOT_NEEDED_FOR_TOTAL_CLOSURE",
                [_label(p, 18, "Cổ phiếu"), _label(p, 26, "quỹ")],
            ),
        ],
        source_period="2026-03-31",
        presentation="EQUITY_COLUMNS_WITH_Q1_OPENING_AND_CLOSING_ROWS",
    )

    p = 33
    hdb = _doc(
        "HDB",
        (33, 34),
        _label(p, 7, "Vốn chủ sở hữu"),
        _label(p, 9, "Báo cáo tình hình thay đổi vốn chủ sở hữu"),
        [
            _label(p, 96, "Tại ngày 31 tháng 12 năm 2025"),
            _label(p, 134, "Tại ngày 30 tháng 06 năm 2026"),
        ],
        [_label(p, i, "Triệu VND") for i in range(41, 51)],
        [
            _mapping(
                1129,
                "OPENING_TOTAL",
                [_label(p, 96, "Tại ngày 31 tháng 12 năm 2025")],
                {"OPENING": [_line(p, 105, "78.285.522")]},
                "PRINTED_OPENING_TOTAL",
            ),
            _mapping(
                1141,
                "CLOSING_TOTAL",
                [_label(p, 134, "Tại ngày 30 tháng 06 năm 2026")],
                {"CLOSING": [_line(p, 144, "90.226.345")]},
                "PRINTED_CLOSING_TOTAL",
            ),
            _mapping(
                5984,
                "CHARTER_CAPITAL",
                [_label(p, 20, "Vốn điều"), _label(p, 30, "lệ")],
                {"OPENING": [_line(p, 97, "50.052.763")], "CLOSING": [_line(p, 135, "50.052.763")]},
            ),
            _mapping(
                6011,
                "SHARE_PREMIUM",
                [_label(p, 13, "Thặng dư"), _label(p, 21, "vốn"), _label(p, 31, "cổ phần")],
                {"OPENING": [_line(p, 98, "1.274.874")], "CLOSING": [_line(p, 136, "1.274.857")]},
            ),
            _mapping(
                6013,
                "CAPITAL_RESERVE",
                [
                    _label(p, 14, "Quỹ dự trữ"),
                    _label(p, 23, "bổ sung"),
                    _label(p, 33, "vốn điều lệ"),
                ],
                {"OPENING": [_line(p, 99, "3.058.795")], "CLOSING": [_line(p, 137, "3.058.795")]},
            ),
            _mapping(
                6014,
                "FINANCIAL_RESERVE",
                [_label(p, 15, "Quỹ"), _label(p, 24, "dự phòng"), _label(p, 34, "tài chính")],
                {"OPENING": [_line(p, 100, "6.909.251")], "CLOSING": [_line(p, 138, "6.909.251")]},
            ),
            _mapping(
                6015,
                "OTHER_FUNDS",
                [_label(p, 25, "Các"), _label(p, 35, "quỹ khác")],
                {"OPENING": [_line(p, 101, "83.312")], "CLOSING": [_line(p, 139, "103.336")]},
            ),
            _mapping(
                6016,
                "FX_DIFFERENCE",
                [
                    _label(p, 11, "Chênh"),
                    _label(p, 17, "lệch tỷ"),
                    _label(p, 27, "giá hối"),
                    _label(p, 37, "đoái"),
                ],
                {"CLOSING": [_line(p, 141, "(11.673)")]},
            ),
            _mapping(
                6017,
                "RETAINED_EARNINGS",
                [_label(p, 18, "Lợi nhuận"), _label(p, 28, "chưa"), _label(p, 38, "phân phối")],
                {
                    "OPENING": [_line(p, 103, "14.191.046")],
                    "CLOSING": [_line(p, 142, "24.460.192")],
                },
            ),
            _mapping(
                6018,
                "NON_CONTROLLING_INTEREST",
                [
                    _label(p, 12, "Lợi ích"),
                    _label(p, 19, "cổ đông"),
                    _label(p, 29, "không"),
                    _label(p, 39, "kiểm soát"),
                ],
                {"OPENING": [_line(p, 104, "2.715.392")], "CLOSING": [_line(p, 143, "4.378.735")]},
            ),
        ],
        [
            _equation(
                "EQUITY_COLUMNS_TO_OPENING_TOTAL",
                "OPENING",
                [
                    _line(p, i, text)
                    for i, text in [
                        (97, "50.052.763"),
                        (98, "1.274.874"),
                        (99, "3.058.795"),
                        (100, "6.909.251"),
                        (101, "83.312"),
                        (102, "89"),
                        (103, "14.191.046"),
                        (104, "2.715.392"),
                    ]
                ],
                _line(p, 105, "78.285.522"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_CLOSING_TOTAL",
                "CLOSING",
                [
                    _line(p, i, text)
                    for i, text in [
                        (135, "50.052.763"),
                        (136, "1.274.857"),
                        (137, "3.058.795"),
                        (138, "6.909.251"),
                        (139, "103.336"),
                        (140, "89"),
                        (141, "(11.673)"),
                        (142, "24.460.192"),
                        (143, "4.378.735"),
                    ]
                ],
                _line(p, 144, "90.226.345"),
            ),
        ],
        [
            _open(
                "CAF-003",
                "Cổ phiếu quỹ",
                "NO_EXACT_EQUITY_BALANCE_LEAF; EMPTY_SOURCE_COLUMN_NOT_PROMOTED_TO_ZERO",
                [_label(p, 22, "Cổ phiếu"), _label(p, 32, "quỹ")],
            ),
            _open(
                "CAF-004",
                "Quỹ đầu tư xây dựng cơ bản",
                "NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL",
                [_label(p, 16, "đầu tư"), _label(p, 26, "xây dựng"), _label(p, 36, "cơ bản")],
                {"OPENING": [_line(p, 102, "89")], "CLOSING": [_line(p, 140, "89")]},
            ),
        ],
    )

    p = 36
    vcb = _doc(
        "VCB",
        (36, 37),
        _label(p, 7, "Vốn và các quỹ"),
        _label(p, 9, "Báo cáo tình hình thay đổi vốn chủ sở hữu"),
        [_label(p, 44, "Số dư tại ngày 1/1/2026"), _label(p, 105, "Số dư tại ngày 30/6/2026")],
        [_label(p, i, "Triệu VND") for i in range(39, 44)],
        [
            _mapping(
                1129,
                "OPENING_TOTAL",
                [_label(p, 44, "Số dư tại ngày 1/1/2026")],
                {"OPENING": [_line(p, 56, "224.558.726")]},
                "PRINTED_OPENING_TOTAL",
            ),
            _mapping(
                1141,
                "CLOSING_TOTAL",
                [_label(p, 105, "Số dư tại ngày 30/6/2026")],
                {"CLOSING": [_line(p, 116, "248.490.506")]},
                "PRINTED_CLOSING_TOTAL",
            ),
            _mapping(
                5984,
                "CHARTER_CAPITAL",
                [_label(p, 15, "Vốn"), _label(p, 25, "điều lệ")],
                {"OPENING": [_line(p, 46, "83.556.751")], "CLOSING": [_line(p, 106, "83.556.751")]},
            ),
            _mapping(
                6011,
                "SHARE_PREMIUM",
                [_label(p, 12, "Thặng dư"), _label(p, 19, "vốn cổ"), _label(p, 27, "phần")],
                {"OPENING": [_line(p, 47, "4.995.389")], "CLOSING": [_line(p, 107, "4.995.389")]},
            ),
            _mapping(
                6012,
                "OTHER_CAPITAL",
                [_label(p, 20, "Vốn khác")],
                {"OPENING": [_line(p, 48, "809.837")], "CLOSING": [_line(p, 108, "2.791.359")]},
            ),
            _mapping(
                6013,
                "CAPITAL_RESERVE",
                [
                    _label(p, 10, "Quỹ dự trữ"),
                    _label(p, 21, "Quỹ dự"),
                    _label(p, 26, "trữ bổ"),
                    _label(p, 32, "sung vốn"),
                    _label(p, 38, "điều lệ"),
                ],
                {"OPENING": [_line(p, 49, "17.549.294")], "CLOSING": [_line(p, 109, "17.513.082")]},
            ),
            _mapping(
                6014,
                "FINANCIAL_RESERVE",
                [_label(p, 16, "Quỹ dự"), _label(p, 28, "phòng tài"), _label(p, 35, "chính")],
                {"OPENING": [_line(p, 50, "21.613.908")], "CLOSING": [_line(p, 110, "21.520.608")]},
            ),
            _mapping(
                6016,
                "FX_DIFFERENCE",
                [_label(p, 13, "Chênh"), _label(p, 22, "lệch tỷ giá"), _label(p, 33, "hối đoái")],
                {"OPENING": [_line(p, 53, "(918.676)")], "CLOSING": [_line(p, 113, "(928.270)")]},
            ),
            _mapping(
                6017,
                "RETAINED_EARNINGS",
                [
                    _label(p, 11, "Lợi nhuận"),
                    _label(p, 18, "sau thuế"),
                    _label(p, 31, "chưa phân"),
                    _label(p, 37, "phối"),
                ],
                {
                    "OPENING": [_line(p, 54, "87.822.642")],
                    "CLOSING": [_line(p, 114, "109.894.677")],
                },
            ),
            _mapping(
                6018,
                "NON_CONTROLLING_INTEREST",
                [
                    _label(p, 14, "Lợi ích cổ"),
                    _label(p, 23, "đông không"),
                    _label(p, 34, "kiểm soát"),
                ],
                {"OPENING": [_line(p, 55, "71.521")], "CLOSING": [_line(p, 115, "85.009")]},
            ),
        ],
        [
            _equation(
                "RESERVE_COLUMNS_TO_RESERVE_SUBTOTAL",
                "OPENING",
                [_line(p, 49, "17.549.294"), _line(p, 50, "21.613.908"), _line(p, 51, "9.058.060")],
                _line(p, 52, "48.221.262"),
            ),
            _equation(
                "RESERVE_COLUMNS_TO_RESERVE_SUBTOTAL",
                "CLOSING",
                [
                    _line(p, 109, "17.513.082"),
                    _line(p, 110, "21.520.608"),
                    _line(p, 111, "9.061.901"),
                ],
                _line(p, 112, "48.095.591"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_OPENING_TOTAL",
                "OPENING",
                [
                    _line(p, i, text)
                    for i, text in [
                        (46, "83.556.751"),
                        (47, "4.995.389"),
                        (48, "809.837"),
                        (52, "48.221.262"),
                        (53, "(918.676)"),
                        (54, "87.822.642"),
                        (55, "71.521"),
                    ]
                ],
                _line(p, 56, "224.558.726"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_CLOSING_TOTAL",
                "CLOSING",
                [
                    _line(p, i, text)
                    for i, text in [
                        (106, "83.556.751"),
                        (107, "4.995.389"),
                        (108, "2.791.359"),
                        (112, "48.095.591"),
                        (113, "(928.270)"),
                        (114, "109.894.677"),
                        (115, "85.009"),
                    ]
                ],
                _line(p, 116, "248.490.506"),
            ),
        ],
        [
            _open(
                "CAF-005",
                "Quỹ đầu tư phát triển",
                "NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_RESERVE_SUBTOTAL_AND_EQUITY_TOTAL",
                [_label(p, 17, "Quỹ đầu tư"), _label(p, 29, "phát triển")],
                {"OPENING": [_line(p, 51, "9.058.060")], "CLOSING": [_line(p, 111, "9.061.901")]},
            )
        ],
    )

    p = 43
    ctg = _doc(
        "CTG",
        (43, 44),
        _label(p, 75, "VỐN VÀ QUỸ CỦA TỔ CHỨC TÍN DỤNG"),
        _label(p, 76, "Báo cáo tình hình thay đổi vốn chủ sở hữu"),
        [_label(p, 78, "Số dư đầu kỳ"), _label(p, 80, "Số dư cuối kỳ")],
        [_label(p, 77, "Đơn vị: Triệu đồng")],
        [
            _mapping(
                1129,
                "OPENING_TOTAL",
                [_label(p, 78, "Số dư đầu kỳ")],
                {"OPENING": [_line(p, 122, "179.655.005")]},
                "PRINTED_OPENING_TOTAL",
            ),
            _mapping(
                6019,
                "INCREASE_TOTAL",
                [_label(p, 79, "Phát sinh trong năm"), _label(p, 81, "Tăng")],
                {"INCREASE": [_line(p, 123, "21.339.046")]},
                "PRINTED_INCREASE_TOTAL",
            ),
            _mapping(
                6020,
                "DECREASE_TOTAL_MAGNITUDE",
                [_label(p, 79, "Phát sinh trong năm"), _label(p, 82, "Giảm")],
                {"DECREASE_MAGNITUDE": [_line(p, 124, "779.749")]},
                "PRINTED_POSITIVE_DECREASE_MAGNITUDE",
            ),
            _mapping(
                1141,
                "CLOSING_TOTAL",
                [_label(p, 80, "Số dư cuối kỳ")],
                {"CLOSING": [_line(p, 125, "200.214.302")]},
                "PRINTED_CLOSING_TOTAL",
            ),
            _mapping(
                5984,
                "CHARTER_CAPITAL",
                [_label(p, 83, "Vốn góp/Vốn điều lệ")],
                {"OPENING": [_line(p, 84, "77.669.446")], "CLOSING": [_line(p, 85, "77.669.446")]},
            ),
            _mapping(
                6011,
                "SHARE_PREMIUM",
                [_label(p, 86, "Thặng dư vốn cổ phần")],
                {
                    "OPENING": [_line(p, 87, "8.974.666")],
                    "DECREASE_MAGNITUDE": [_line(p, 88, "10")],
                    "CLOSING": [_line(p, 89, "8.974.656")],
                },
            ),
            _mapping(
                6016,
                "FX_DIFFERENCE",
                [_label(p, 92, "Chênh lệch tỷ giá hối đoái")],
                {
                    "OPENING": [_line(p, 93, "362.748")],
                    "DECREASE_MAGNITUDE": [_line(p, 94, "16.173")],
                    "CLOSING": [_line(p, 95, "346.575")],
                },
            ),
            _mapping(
                6014,
                "FINANCIAL_RESERVE",
                [_label(p, 100, "Quỹ dự phòng tài chính")],
                {
                    "OPENING": [_line(p, 101, "18.016.694")],
                    "DECREASE_MAGNITUDE": [_line(p, 102, "1.546")],
                    "CLOSING": [_line(p, 103, "18.015.148")],
                },
            ),
            _mapping(
                6013,
                "CAPITAL_RESERVE",
                [_label(p, 104, "Quỹ dự trữ bổ sung vốn điều lệ")],
                {
                    "OPENING": [_line(p, 105, "13.089.194")],
                    "CLOSING": [_line(p, 106, "13.089.194")],
                },
            ),
            _mapping(
                6017,
                "RETAINED_EARNINGS",
                [_label(p, 108, "Lợi nhuận sau thuế chưa phân phối")],
                {
                    "OPENING": [_line(p, 109, "58.212.794")],
                    "INCREASE": [_line(p, 110, "20.657.039")],
                    "DECREASE_MAGNITUDE": [_line(p, 111, "725.723")],
                    "CLOSING": [_line(p, 112, "78.144.110")],
                },
            ),
            _mapping(
                6018,
                "NON_CONTROLLING_INTEREST",
                [_label(p, 113, "Lợi ích của cổ đông không kiểm soát")],
                {
                    "OPENING": [_line(p, 114, "1.206.433")],
                    "INCREASE": [_line(p, 115, "86.492")],
                    "DECREASE_MAGNITUDE": [_line(p, 116, "35.170")],
                    "CLOSING": [_line(p, 117, "1.257.755")],
                },
            ),
            _mapping(
                6012,
                "OTHER_CAPITAL",
                [_label(p, 118, "Vốn chủ sở hữu khác")],
                {
                    "OPENING": [_line(p, 119, "1.574.563")],
                    "INCREASE": [_line(p, 120, "595.515")],
                    "CLOSING": [_line(p, 121, "2.170.078")],
                },
            ),
        ],
        [
            _equation(
                "EQUITY_COLUMNS_TO_OPENING_TOTAL",
                "OPENING",
                [
                    _line(p, i, text)
                    for i, text in [
                        (84, "77.669.446"),
                        (87, "8.974.666"),
                        (93, "362.748"),
                        (97, "548.467"),
                        (101, "18.016.694"),
                        (105, "13.089.194"),
                        (109, "58.212.794"),
                        (114, "1.206.433"),
                        (119, "1.574.563"),
                    ]
                ],
                _line(p, 122, "179.655.005"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_INCREASE_TOTAL",
                "INCREASE",
                [_line(p, 110, "20.657.039"), _line(p, 115, "86.492"), _line(p, 120, "595.515")],
                _line(p, 123, "21.339.046"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_DECREASE_TOTAL_MAGNITUDE",
                "DECREASE_MAGNITUDE",
                [
                    _line(p, i, text)
                    for i, text in [
                        (88, "10"),
                        (94, "16.173"),
                        (98, "1.127"),
                        (102, "1.546"),
                        (111, "725.723"),
                        (116, "35.170"),
                    ]
                ],
                _line(p, 124, "779.749"),
            ),
            _equation(
                "EQUITY_COLUMNS_TO_CLOSING_TOTAL",
                "CLOSING",
                [
                    _line(p, i, text)
                    for i, text in [
                        (85, "77.669.446"),
                        (89, "8.974.656"),
                        (95, "346.575"),
                        (99, "547.340"),
                        (103, "18.015.148"),
                        (106, "13.089.194"),
                        (112, "78.144.110"),
                        (117, "1.257.755"),
                        (121, "2.170.078"),
                    ]
                ],
                _line(p, 125, "200.214.302"),
            ),
        ],
        [
            _open(
                "CAF-006",
                "Cổ phiếu quỹ",
                "NO_EXACT_EQUITY_BALANCE_LEAF; EMPTY_SOURCE_ROW_NOT_PROMOTED_TO_ZERO",
                [_label(p, 90, "Cổ phiếu quỹ")],
            ),
            _open(
                "CAF-007",
                "Chênh lệch đánh giá lại tài sản",
                "NO_EXACT_SCHEMA_BALANCE_COLUMN; EMPTY_SOURCE_ROW_NOT_PROMOTED_TO_ZERO",
                [_label(p, 91, "Chênh lệch đánh giá lại tài sản")],
            ),
            _open(
                "CAF-008",
                "Quỹ đầu tư phát triển",
                "NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL",
                [_label(p, 96, "Quỹ đầu tư phát triển")],
                {
                    "OPENING": [_line(p, 97, "548.467")],
                    "DECREASE_MAGNITUDE": [_line(p, 98, "1.127")],
                    "CLOSING": [_line(p, 99, "547.340")],
                },
            ),
        ],
    )

    bid = _doc(
        "BID",
        (27, 28),
        None,
        None,
        [],
        [],
        [],
        [],
        [
            _open(
                "CAF-009",
                "Báo cáo tình hình thay đổi vốn chủ sở hữu",
                "ROTATED_SOURCE_NUMERIC_CHALLENGER_NOT_RELIABLE; UNIQUE_STRUCTURE_VERIFIED_BUT_NUMERIC_MAPPING_DEFERRED",
            )
        ],
        presentation="ROTATED_EQUITY_TABLE_STRUCTURE_ONLY",
    )
    vib = _doc(
        "VIB",
        (44, 45),
        None,
        None,
        [],
        [],
        [],
        [],
        [
            _open(
                "CAF-010",
                "Báo cáo tình hình thay đổi vốn chủ sở hữu",
                "ROTATED_SOURCE_NUMERIC_CHALLENGER_NOT_RELIABLE; UNIQUE_STRUCTURE_VERIFIED_BUT_NUMERIC_MAPPING_DEFERRED",
            )
        ],
        presentation="ROTATED_EQUITY_TABLE_STRUCTURE_ONLY",
    )
    return [acb, mbb, vpb, hdb, vcb, ctg, bid, vib]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": REVIEW_RUN_ID,
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": REVIEW_STATE,
    }
    return {**material, "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex capital-and-funds pixel review differs from the fixed ledger")
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


def _source_period_status(source_period: str) -> str:
    return (
        "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
        if source_period == "2026-03-31"
        else "VERIFIED_SOURCE_PERIOD_Q2_2026"
    )


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(t["verified_accounting_equations"]) for t in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            t["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for t in trials
        ),
        "mapping_verified_count": sum(len(t["verified_mappings"]) for t in trials),
        "numeric_mapping_unresolved_document_count": sum(
            t["status"] == "STRUCTURE_VERIFIED_NUMERIC_MAPPING_UNRESOLVED" for t in trials
        ),
        "open_source_row_count": sum(len(t["unmapped_source_rows"]) for t in trials),
        "q1_source_period_caveat_document_count": sum(
            t["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" for t in trials
        ),
        "rotated_structural_document_count": sum(
            t["rotated_rescue_line_count"] > 0
            and t["status"] == "STRUCTURE_VERIFIED_NUMERIC_MAPPING_UNRESOLVED"
            for t in trials
        ),
        "verified_value_cell_count": sum(
            len(v["components"])
            for t in trials
            for m in t["verified_mappings"]
            for v in m["values"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("capital-and-funds result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("capital-and-funds result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status")
            not in {
                "VERIFIED_BY_CODEX",
                "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS",
                "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT",
                "STRUCTURE_VERIFIED_NUMERIC_MAPPING_UNRESOLVED",
            }
            or any(
                row.get("status") != "VERIFIED_BY_CODEX"
                for row in trial.get("verified_mappings", [])
            )
            or any(
                row.get("status") != "UNRESOLVED" for row in trial.get("unmapped_source_rows", [])
            )
        ):
            raise _error("capital-and-funds trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("capital-and-funds result identity drifted")
    return canonical_clone_v1(value)


def build_capital_and_funds_8bank_codex_verified_mapping_v1(
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
        or structure_scan.get("state") != STRUCTURE_SCAN_STATE
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
            raise _error("reviewed region is not the unique whole-PDF capital-and-funds graph")
        page_cache: dict[int, tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]] = {}

        def context(
            page_sequence: int,
            *,
            page_cache: dict[
                int, tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]
            ] = page_cache,
            axis_document: Mapping[str, Any] = axis_document,
            semantic_document: Mapping[str, Any] = semantic_document,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
            if page_sequence not in page_cache:
                axis_page = _page(axis_document, page_sequence, "accounting axis")
                semantic_page = _page(semantic_document, page_sequence, "semantic index")
                crop_page = _page(crop_document, page_sequence, "crop manifest")
                page_cache[page_sequence] = (
                    axis_page,
                    semantic_page,
                    crop_page,
                    foundation.support._source_line_axis(crop_page),
                )
            return page_cache[page_sequence]

        value_cache: dict[str, dict[str, Any]] = {}

        def verified(
            ref: Mapping[str, Any],
            *,
            value_cache: dict[str, dict[str, Any]] = value_cache,
            context: Any = context,
            document_ordinal: int = ordinal,
            document_provenance: str = code,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> dict[str, Any]:
            key = canonical_json_sha256_v1(ref)
            if key not in value_cache:
                if "evidence_axis" in ref:
                    if not callable(_ALTERNATE_VALUE_VERIFIER):
                        raise _error("alternate numeric evidence axis is not configured")
                    evidence = _ALTERNATE_VALUE_VERIFIER(
                        document_ordinal,
                        document_provenance,
                        crop_document,
                        ref,
                    )
                else:
                    axis_page, semantic_page, crop_page, source_texts = context(
                        ref["page_sequence"]
                    )
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
                value_cache[key] = {**evidence, "page_sequence": ref["page_sequence"]}
            return canonical_clone_v1(value_cache[key])

        verified_mappings = []
        for mapping in reviewed["mappings"]:
            labels = []
            for item in mapping["labels"]:
                axis_page, semantic_page, _, _ = context(item["page_sequence"])
                labels.append(
                    {
                        "page_sequence": item["page_sequence"],
                        **_semantic_evidence(axis_page, semantic_page, item),
                    }
                )
            values = []
            for axis_role, refs in mapping["values"].items():
                components = [verified(ref) for ref in refs]
                values.append(
                    {
                        "aggregation": "DIRECT_VISIBLE_VALUE"
                        if len(components) == 1
                        else "SUM_OF_VISIBLE_SOURCE_ROWS",
                        "axis_role": axis_role,
                        "components": components,
                        "normalized_value": sum(
                            component["normalized_value"] for component in components
                        ),
                    }
                )
            verified_mappings.append(
                {
                    "label_evidence": labels,
                    "role": mapping["role"],
                    "schema_binding": _schema_binding(
                        schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                    ),
                    "status": "VERIFIED_BY_CODEX",
                    "topology": mapping["topology"],
                    "values": values,
                }
            )
        equations = []
        for equation in reviewed["equations"]:
            terms = []
            computed = 0
            for ref in equation["terms"]:
                evidence = verified(ref)
                computed += ref["multiplier"] * evidence["normalized_value"]
                terms.append(
                    {
                        "multiplier": ref["multiplier"],
                        "page_sequence": ref["page_sequence"],
                        "source_line_index": evidence["source_line_index"],
                        "value": evidence["normalized_value"],
                    }
                )
            total = verified(equation["total"])
            expected_total = equation["total"]["multiplier"] * total["normalized_value"]
            if computed != expected_total:
                raise _error(f"capital-and-funds equation does not close: {equation['name']}")
            equations.append(
                {
                    "axis_role": equation["axis_role"],
                    "computed_value": computed,
                    "name": equation["name"],
                    "status": "VERIFIED_EXACT",
                    "terms": terms,
                    "visible_total": expected_total,
                    "visible_total_page_sequence": equation["total"]["page_sequence"],
                    "visible_total_source_line_index": total["source_line_index"],
                }
            )
        unresolved = []
        for row in reviewed["unmapped_source_rows"]:
            labels = []
            for item in row["labels"]:
                axis_page, semantic_page, _, _ = context(item["page_sequence"])
                labels.append(
                    {
                        "page_sequence": item["page_sequence"],
                        **_semantic_evidence(axis_page, semantic_page, item),
                    }
                )
            unresolved.append(
                {
                    "item_id": row["item_id"],
                    "label_evidence": labels,
                    "reason": row["reason"],
                    "source_label": row["source_label"],
                    "status": "UNRESOLVED",
                    "values": [
                        {"axis_role": axis_role, "components": [verified(ref) for ref in refs]}
                        for axis_role, refs in row["values"].items()
                    ],
                }
            )
        if reviewed["owner"] is None:
            owner_evidence = canonical_clone_v1(matcher["regions"][0]["owner"])
            heading_evidence = next(
                (
                    canonical_clone_v1(event)
                    for event in matcher["regions"][0]["events"]
                    if event["role"] == "STATEMENT_OF_CHANGES"
                ),
                None,
            )
        else:
            owner_axis, owner_semantic, _, _ = context(reviewed["owner"]["page_sequence"])
            owner_evidence = _semantic_evidence(owner_axis, owner_semantic, reviewed["owner"])
            if reviewed["heading"] is None:
                heading_evidence = None
            else:
                heading_axis, heading_semantic, _, _ = context(reviewed["heading"]["page_sequence"])
                heading_evidence = _semantic_evidence(
                    heading_axis, heading_semantic, reviewed["heading"]
                )
        period_evidence = []
        for item in reviewed["period_axis"]:
            axis_page, semantic_page, _, _ = context(item["page_sequence"])
            period_evidence.append(
                {
                    "page_sequence": item["page_sequence"],
                    **_semantic_evidence(axis_page, semantic_page, item),
                }
            )
        unit_evidence = []
        for item in reviewed["unit_evidence"]:
            axis_page, semantic_page, _, _ = context(item["page_sequence"])
            unit_evidence.append(
                {
                    "page_sequence": item["page_sequence"],
                    **_semantic_evidence(axis_page, semantic_page, item),
                }
            )
        source_period_status = _source_period_status(reviewed["source_period"])
        status = reviewed["disposition"]
        if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" and status.startswith(
            "VERIFIED_BY_CODEX"
        ):
            status = "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
        trials.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "heading_evidence": heading_evidence,
                "owner_evidence": owner_evidence,
                "page_span": reviewed["page_span"],
                "period_axis_evidence": period_evidence,
                "rotated_rescue_line_count": scan_trial["rotated_rescue_line_count"],
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "status": status,
                "structure_graph_id": matcher["result_id"],
                "unit_evidence": unit_evidence,
                "unmapped_source_rows": unresolved,
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )
    schema_family = {
        "family_end_display_order": FAMILY_END_DISPLAY_ORDER,
        "family_root": _schema_binding(schema_by_id.get(1128), 1128),
        "mapped_report_norm_ids": sorted(
            {
                m["schema_binding"]["report_norm_id"]
                for trial in trials
                for m in trial["verified_mappings"]
            }
        ),
    }
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
            **canonical_clone_v1(_EXTRA_INPUT_REFS),
        },
        "metrics": _metrics(trials),
        "schema_family": schema_family,
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_capital_and_funds_8bank_codex_verified_mapping_replay_v1(
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
    rebuilt = build_capital_and_funds_8bank_codex_verified_mapping_v1(
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
        raise _error("capital-and-funds verified mapping does not replay exactly")
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


def build_live_capital_and_funds_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_capital_and_funds_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_capital_and_funds_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_capital_and_funds_8bank_codex_verified_mapping_v1(value: Any) -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_capital_and_funds_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_capital_and_funds_8bank_codex_verified_mapping_replay_v1(
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
        _write(RESULT_PATH, build_live_capital_and_funds_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        value, _ = _stable_json(RESULT_PATH)
        validate_live_capital_and_funds_8bank_codex_verified_mapping_v1(value)
    if not (args.write_review or args.write_result or args.validate_result):
        raise SystemExit("choose --write-review, --write-result or --validate-result")


if __name__ == "__main__":
    main()
