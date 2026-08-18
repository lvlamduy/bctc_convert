"""Verify cash-and-cash-equivalent disclosures across eight reports."""

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


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load cash-equivalents support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


other = _load(
    "other_activity_support_for_cash_equivalents",
    "build_other_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load(
    "cash_equivalents_scan_for_verified_mapping",
    "scan_cash_equivalents_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "CASH_EQUIVALENTS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "CASH_EQUIVALENTS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "CASH_EQUIVALENTS_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "e0092:result:"
REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "e0092:pixel-review:"
REVIEW_RUN_ID = "E-0092"
VARIANT_PROFILE = "HISTORICAL_BASELINE_V1"
FAMILY_END_DISPLAY_ORDER = 830
SOURCE_PERIOD_STATUS_BY_PERIOD = {
    "2026-03-31": "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2",
    "2026-06-30": "VERIFIED_SOURCE_PERIOD_Q2_2026",
}
EXPECTED_RESULT_ID: str | None = (
    "e0092:result:bf97e1e636c1029dd8c41d424dabde0ecbb507c4230a53a8a5ccfd12b70dfb75"
)
ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = True
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_CASH_"
    "EQUIVALENTS_GRAPH_VISIBLE_PDF_PADDLEOCR_OR_NATIVE_NUMERIC_CHALLENGER_"
    "PERIOD_UNIT_PRINTED_TOTAL_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_BLANK_NOT_"
    "ZERO_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0092-cash-equivalents-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0092-cash-equivalents-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = other.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = other.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = other.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = other.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "cefdsv1:scan:72f4f33a83e1c9a3642059ba5c0d2704e7aeea2324ab09a6e9eb08dfabac8134"

_SCHEMA_EXPECTED = {
    1247: (
        "III. THÔNG TIN BỔ SUNG CHO MỘT SỐ KHOẢN MỤC TRÌNH BÀY TRONG LƯU CHUYỂN TIỀN TỆ",
        None,
        823,
    ),
    1248: ("Tiền và các khoản tương đương tiền", 1247, 824),
    1249: ("Tiền mặt và các khoản tương đương tiền tại quỹ", 1248, 825),
    1250: ("Tiền gửi tại NHNN", 1248, 826),
    1251: ("Tiền, ngoại hối gửi tại các TCTD khác", 1248, 827),
    1252: ("+ Không kỳ hạn", 1248, 828),
    1253: ("+ Có kỳ hạn không quá 3 tháng", 1248, 829),
    1254: (
        "Chứng khoán có thời hạn thu hồi hoặc đáo hạn không quá 3 tháng kể từ ngày mua",
        1248,
        830,
    ),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "canonicalization_or_export_authority": False,
    "cash_flow_or_policy_text_alone_used_as_mapping_evidence": False,
    "complete_pdf_scanned_for_every_document": True,
    "detailed_note_absence_bounded_to_bound_report": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_cash_equivalent_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_numeric_challenger_and_accounting_closure_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "partial_optional_row_axes_retained": True,
    "source_parent_and_children_double_counted": False,
    "unmapped_source_rows_retained": True,
    "vietocr_used_as_numeric_truth": False,
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


class CashEquivalents8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, numbers, equations, or schema drifted."""


def _error(message: str) -> CashEquivalents8BankCodexVerifiedMappingV1Error:
    return CashEquivalents8BankCodexVerifiedMappingV1Error(message)


def _ref(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str) -> dict[str, Any]:
    return {"kind": "AUTHENTICATED_LINE", **_ref(page, line, text)}


def _sum(page: int, items: Sequence[tuple[int, str]]) -> dict[str, Any]:
    return {
        "components": [_line(page, line, text) for line, text in items],
        "kind": "AUTHENTICATED_CONTROLLED_SUM",
        "page_sequence": page,
    }


def _dash(page: int, bbox: Sequence[int], rgb_sha256: str) -> dict[str, Any]:
    return {
        "bbox_raw_pixels": list(bbox),
        "kind": "AUTHENTICATED_RENDER_PIXEL_DASH",
        "page_sequence": page,
        "pixel_rgb_sha256": rgb_sha256,
        "pixel_transcription": "-",
    }


def _mapping(
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    values: Mapping[str, Mapping[str, Any]],
    *,
    blank_axes: Sequence[str] = (),
    topology: str = "DIRECT_OR_WRAPPED_LABEL_MEANINGFUL_PERIOD_LANES",
) -> dict[str, Any]:
    return {
        "blank_axes": list(blank_axes),
        "labels": [_ref(page, line, text) for line, text in labels],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": canonical_clone_v1(values),
    }


def _both(
    page: int, current_line: int, current: str, comparative_line: int, comparative: str
) -> dict[str, Any]:
    return {
        "COMPARATIVE_PERIOD": _line(page, comparative_line, comparative),
        "CURRENT_PERIOD": _line(page, current_line, current),
    }


def _equation(
    name: str,
    parent: str,
    terms: Sequence[str],
    axes: Sequence[str] = ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"),
) -> dict[str, Any]:
    return {
        "axes": list(axes),
        "name": name,
        "parent_role": parent,
        "term_roles": list(terms),
    }


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_note_complete_region_count": 0,
            "reason": (
                "No cash-equivalent component table with cash, central-bank, interbank, "
                "period/unit axes and a printed total was found in the bound report; cash-flow "
                "beginning/ending balances and accounting-policy prose do not qualify."
            ),
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "equations": [],
        "graph_roles": [],
        "mappings": [],
        "owner": [],
        "page_span": None,
        "period_axis": [],
        "presentation": "NO_DETAILED_CASH_EQUIVALENTS_COMPONENT_TABLE_IN_BOUND_REPORT",
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    page = 8
    documents = [
        {
            "absence_evidence": None,
            "bank_code": "ACB",
            "equations": [
                _equation(
                    "CURRENT_COMPONENTS_EQUAL_PRINTED_CASH_EQUIVALENTS",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_GENERAL"],
                    ["CURRENT_PERIOD"],
                ),
                _equation(
                    "COMPARATIVE_COMPONENTS_EQUAL_PRINTED_CASH_EQUIVALENTS",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_GENERAL", "SECURITIES"],
                    ["COMPARATIVE_PERIOD"],
                ),
            ],
            "graph_roles": [
                "INTERBANK_GENERAL",
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "SECURITIES_UP_TO_3_MONTHS",
            ],
            "mappings": [
                _mapping(
                    "TOTAL",
                    1248,
                    page,
                    [(50, "VII TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN TẠI NGÀY"), (51, "30 THÁNG 6")],
                    {
                        "CURRENT_PERIOD": _sum(
                            page, [(55, "6.151.699"), (58, "5.827.087"), (61, "104.554.257")]
                        ),
                        "COMPARATIVE_PERIOD": _sum(
                            page,
                            [
                                (56, "6.666.091"),
                                (59, "5.439.937"),
                                (62, "111.528.971"),
                                (64, "1.455.373"),
                            ],
                        ),
                    },
                    topology="CONTROLLED_CHILD_SUM_CORROBORATED_BY_COMBINED_PRINTED_TOTAL_ROW",
                ),
                _mapping(
                    "CASH",
                    1249,
                    page,
                    [(54, "Tiền mặt, vàng bạc, đá quý")],
                    _both(page, 55, "6.151.699", 56, "6.666.091"),
                ),
                _mapping(
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(57, "Tiền gửi thanh toán tại Ngân hàng Nhà nước")],
                    _both(page, 58, "5.827.087", 59, "5.439.937"),
                ),
                _mapping(
                    "INTERBANK_GENERAL",
                    1251,
                    page,
                    [(60, "Tiền gửi tại các tổ chức tín dụng khác")],
                    _both(page, 61, "104.554.257", 62, "111.528.971"),
                ),
                _mapping(
                    "SECURITIES",
                    1254,
                    page,
                    [(63, "Chứng khoán đầu tư")],
                    {"COMPARATIVE_PERIOD": _line(page, 64, "1.455.373")},
                    blank_axes=["CURRENT_PERIOD"],
                ),
            ],
            "owner": [_ref(page, 53, "Tiền và các khoản tương đương tiền gồm có:")],
            "page_span": [page, page],
            "period_axis": [
                _ref(page, 5, "Lũy kế từ đầu năm đến"),
                _ref(page, 6, "cuối Quý II"),
                _ref(page, 7, "Năm 2026"),
                _ref(page, 8, "Năm 2025"),
            ],
            "presentation": "CASH_FLOW_TOTAL_BEFORE_COMPONENTS_WITH_ONE_COMPARATIVE_ONLY_SECURITIES_ROW",
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 9, "Triệu đồng"), _ref(page, 10, "Triệu đồng")],
        }
    ]
    page = 50
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "MBB",
            "equations": [
                _equation(
                    "COMPONENTS_EQUAL_TOTAL", "TOTAL", ["CASH", "CENTRAL_BANK", "INTERBANK_TERM"]
                )
            ],
            "graph_roles": [
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "INTERBANK_TERM_UP_TO_3_MONTHS",
            ],
            "mappings": [
                _mapping(
                    "TOTAL",
                    1248,
                    page,
                    [(67, "Tiền và các khoản tương đương tiền")],
                    _both(page, 83, "187.350.187", 84, "239.259.989"),
                    topology="TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    "CASH",
                    1249,
                    page,
                    [(74, "Tiền và các khoản tương đương tiền tại quỹ")],
                    _both(page, 75, "5.051.244", 76, "4.965.786"),
                ),
                _mapping(
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(77, "Tiền gửi tại Ngân hàng Nhà nước")],
                    _both(page, 78, "27.350.120", 79, "68.475.175"),
                ),
                _mapping(
                    "INTERBANK_TERM",
                    1253,
                    page,
                    [(80, "Tiền gửi tại TCTD kỳ hạn gốc không quá 3 tháng")],
                    _both(page, 81, "154.948.823", 82, "165.819.028"),
                ),
            ],
            "owner": [_ref(page, 67, "Tiền và các khoản tương đương tiền")],
            "page_span": [page, page],
            "period_axis": [_ref(page, 70, "30/06/2026"), _ref(page, 71, "31/12/2025")],
            "presentation": "DETAIL_NOTE_COMBINED_TERM_INTERBANK_THEN_TRAILING_TOTAL",
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 72, "Triệu đồng"), _ref(page, 73, "Triệu đồng")],
        }
    )
    page = 66
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VPB",
            "equations": [
                _equation(
                    "COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_DEMAND", "INTERBANK_TERM", "SECURITIES"],
                )
            ],
            "graph_roles": [
                "INTERBANK_GENERAL",
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "INTERBANK_DEMAND",
                "INTERBANK_TERM_UP_TO_3_MONTHS",
                "SECURITIES_UP_TO_3_MONTHS",
            ],
            "mappings": [
                _mapping(
                    "TOTAL",
                    1248,
                    page,
                    [(35, "TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
                    _both(page, 61, "208.224.915", 62, "151.497.743"),
                    topology="TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    "CASH",
                    1249,
                    page,
                    [(44, "Tiền mặt, vàng bạc, đá quý")],
                    _both(page, 45, "4.065.152", 46, "2.671.682"),
                ),
                _mapping(
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(47, "Tiền gửi tại Ngân hàng Nhà nước Việt Nam")],
                    _both(page, 48, "14.817.329", 49, "7.191.513"),
                ),
                _mapping(
                    "INTERBANK_DEMAND",
                    1252,
                    page,
                    [(50, "Tiền gửi thanh toán tại các TCTD khác")],
                    _both(page, 51, "12.126.080", 52, "13.219.040"),
                ),
                _mapping(
                    "INTERBANK_TERM",
                    1253,
                    page,
                    [
                        (53, "Tiền gửi tại các TCTD khác có kỳ hạn không quá ba"),
                        (54, "tháng kể từ ngày gửi"),
                    ],
                    _both(page, 55, "175.716.998", 56, "126.415.875"),
                ),
                _mapping(
                    "SECURITIES",
                    1254,
                    page,
                    [
                        (57, "Chứng khoán có thời hạn thu hồi hoặc đáo hạn"),
                        (58, "không quá ba tháng kể từ ngày mua"),
                    ],
                    _both(page, 59, "1.499.356", 60, "1.999.633"),
                ),
            ],
            "owner": [_ref(page, 35, "TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
            "page_span": [page, page],
            "period_axis": [
                _ref(page, 38, "Ngày 31 tháng 3"),
                _ref(page, 40, "năm 2026"),
                _ref(page, 39, "Ngày 31 tháng 3"),
                _ref(page, 41, "năm 2025"),
            ],
            "presentation": "Q1_DEMAND_TERM_AND_SECURITIES_SPLIT_THEN_TRAILING_TOTAL",
            "source_period": "2026-03-31",
            "unit_evidence": [_ref(page, 42, "Triệu đồng"), _ref(page, 43, "Triệu đồng")],
        }
    )
    documents.append(_absence("HDB"))
    page = 40
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VCB",
            "equations": [
                _equation(
                    "CURRENT_COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_GENERAL", "SECURITIES"],
                    ["CURRENT_PERIOD"],
                ),
                _equation(
                    "COMPARATIVE_COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_GENERAL"],
                    ["COMPARATIVE_PERIOD"],
                ),
            ],
            "graph_roles": [
                "INTERBANK_GENERAL",
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "SECURITIES_UP_TO_3_MONTHS",
            ],
            "mappings": [
                _mapping(
                    "TOTAL",
                    1248,
                    page,
                    [(55, "21. Tiền và các khoản tương đương tiền")],
                    _both(page, 74, "672.039.664", 75, "541.688.802"),
                    topology="TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    "CASH",
                    1249,
                    page,
                    [(61, "Tiền mặt, vàng bạc, đá quý")],
                    _both(page, 62, "14.602.142", 63, "15.542.769"),
                ),
                _mapping(
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(64, "Tiền gửi tại Ngân hàng nhà nước Việt Nam")],
                    _both(page, 65, "73.064.279", 66, "37.445.504"),
                ),
                _mapping(
                    "INTERBANK_GENERAL",
                    1251,
                    page,
                    [
                        (67, "Tiền, vàng gửi tại và cho vay các tổ chức tín dụng khác với kỳ hạn"),
                        (68, "gốc không quá 3 tháng"),
                    ],
                    _both(page, 69, "583.421.016", 70, "488.700.529"),
                ),
                _mapping(
                    "SECURITIES",
                    1254,
                    page,
                    [
                        (71, "Chứng khoán có thời hạn thu hồi hoặc đáo hạn không quá 3 tháng"),
                        (72, "kể từ ngày mua"),
                    ],
                    {"CURRENT_PERIOD": _line(page, 73, "952.227")},
                    blank_axes=["COMPARATIVE_PERIOD"],
                ),
            ],
            "owner": [_ref(page, 55, "21. Tiền và các khoản tương đương tiền")],
            "page_span": [page, page],
            "period_axis": [_ref(page, 56, "30/6/2026"), _ref(page, 57, "31/12/2025")],
            "presentation": "COMBINED_INTERBANK_WITH_ONE_CURRENT_ONLY_SECURITIES_ROW",
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 58, "Triệu VND"), _ref(page, 59, "Triệu VND")],
        }
    )
    page = 47
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "CTG",
            "equations": [
                _equation(
                    "COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_DEMAND", "INTERBANK_TERM", "SECURITIES"],
                )
            ],
            "graph_roles": [
                "INTERBANK_GENERAL",
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "INTERBANK_DEMAND",
                "SECURITIES_UP_TO_3_MONTHS",
            ],
            "mappings": [
                _mapping(
                    "TOTAL",
                    1248,
                    page,
                    [(65, "20. TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
                    _both(page, 89, "542.422.671", 90, "451.745.475"),
                    topology="TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    "CASH",
                    1249,
                    page,
                    [(72, "Tiền mặt và các khoản tương đương tiền tại quỹ")],
                    _both(page, 73, "12.998.380", 74, "12.583.484"),
                ),
                _mapping(
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(75, "Tiền gửi tại NHNN")],
                    _both(page, 76, "18.553.436", 77, "35.225.543"),
                ),
                _mapping(
                    "INTERBANK_DEMAND",
                    1252,
                    page,
                    [(78, "Tiền, ngoại hối gửi không kỳ hạn tại các TCTD khác")],
                    _both(page, 79, "316.065.795", 80, "308.518.041"),
                ),
                _mapping(
                    "INTERBANK_TERM",
                    1253,
                    page,
                    [
                        (81, "Tiền, ngoại hối gửi có kỳ hạn tại các TCTD khác có thời"),
                        (84, "gian đáo hạn không quá 3 tháng"),
                    ],
                    _both(page, 82, "194.064.504", 83, "95.235.407"),
                ),
                _mapping(
                    "SECURITIES",
                    1254,
                    page,
                    [
                        (85, "Chứng khoán có thời hạn thu hồi hoặc đáo hạn không"),
                        (88, "quá 3 tháng kể từ ngày mua"),
                    ],
                    _both(page, 86, "740.556", 87, "183.000"),
                ),
            ],
            "owner": [_ref(page, 65, "20. TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
            "page_span": [page, page],
            "period_axis": [_ref(page, 68, "30/06/2026"), _ref(page, 69, "31/12/2025")],
            "presentation": "DEMAND_TERM_AND_SECURITIES_SPLIT_THEN_TRAILING_TOTAL",
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 70, "triệu đồng"), _ref(page, 71, "triệu đồng")],
        }
    )
    documents.append(_absence("BID"))
    page = 45
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VIB",
            "equations": [
                _equation(
                    "COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_DEMAND", "INTERBANK_TERM"],
                )
            ],
            "graph_roles": [
                "INTERBANK_GENERAL",
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "INTERBANK_DEMAND",
                "INTERBANK_TERM_UP_TO_3_MONTHS",
            ],
            "mappings": [
                _mapping(
                    "TOTAL",
                    1248,
                    page,
                    [(5, "TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
                    _both(page, 23, "69.246.458", 24, "48.710.307"),
                    topology="TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    "CASH",
                    1249,
                    page,
                    [(10, "Tiền mặt và vàng")],
                    _both(page, 11, "2.382.079", 12, "1.843.449"),
                ),
                _mapping(
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(13, "Tiền gửi tại NHNN")],
                    _both(page, 14, "5.125.275", 15, "5.200.726"),
                ),
                _mapping(
                    "INTERBANK_DEMAND",
                    1252,
                    page,
                    [(16, "Tiền gửi không kỳ hạn tại các TCTD khác")],
                    _both(page, 17, "1.046.844", 18, "1.666.132"),
                ),
                _mapping(
                    "INTERBANK_TERM",
                    1253,
                    page,
                    [
                        (19, "Tiền gửi có kỳ hạn tại các TCTD khác với kỳ hạn không quá 3"),
                        (20, "tháng"),
                    ],
                    _both(page, 21, "60.692.260", 22, "40.000.000"),
                ),
            ],
            "owner": [_ref(page, 5, "TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
            "page_span": [page, page],
            "period_axis": [_ref(page, 6, "30/06/2026"), _ref(page, 7, "30/06/2025")],
            "presentation": "DEMAND_TERM_SPLIT_THEN_TRAILING_TOTAL",
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 8, "triệu đồng"), _ref(page, 9, "triệu đồng")],
        }
    )
    if [item["bank_code"] for item in documents] != list(EXPECTED_DOCUMENT_ORDER):
        raise _error("review document order drifted")
    return documents


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
    return {
        **material,
        "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material),
    }


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex cash-equivalents pixel review differs from fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    return other._document(items, code, label)


def _page(document: Mapping[str, Any], page: int, label: str) -> dict[str, Any]:
    return other._page(document, page, label)


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    if (
        expected is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
        or (not ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT and item.display_order != expected[2])
    ):
        raise _error(f"mapping does not bind exact live TM schema row {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": expected[2],
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    values = [
        value for trial in trials for row in trial["verified_mappings"] for value in row["values"]
    ]
    return {
        "accounting_equation_verified_count": sum(
            len(t["verified_accounting_equations"]) for t in trials
        ),
        "blank_optional_axis_count": sum(
            len(row["blank_axes"]) for t in trials for row in t["verified_mappings"]
        ),
        "detailed_note_not_present_document_count": sum(
            t["status"] == "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT" for t in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            t["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for t in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            value.get("fresh_vietocr_numeric_status") == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            for value in values
        ),
        "mapping_verified_count": sum(len(t["verified_mappings"]) for t in trials),
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": sum(
            t["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" for t in trials
        ),
        "verified_value_cell_count": len(values),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("cash-equivalents result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("cash-equivalents result identity or metrics drifted")
    allowed = {
        "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT",
    }
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status") not in allowed
            or any(
                item.get("status") != "VERIFIED_BY_CODEX"
                for item in trial.get("verified_mappings", [])
            )
        ):
            raise _error("cash-equivalents trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material) or (
        EXPECTED_RESULT_ID is not None and identity != EXPECTED_RESULT_ID
    ):
        raise _error("cash-equivalents result identity drifted")
    return canonical_clone_v1(value)


def build_cash_equivalents_8bank_codex_verified_mapping_v1(
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
    scanner.validate_cash_equivalents_full_document_scan_replay_v1(
        structure_scan, semantic_index, variant_profile=VARIANT_PROFILE
    )
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
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
            "structure_graph_id": matcher["result_id"],
            "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
        }
        if reviewed["absence_evidence"] is not None:
            if matcher["regions"]:
                raise _error("absent detailed cash-equivalents table unexpectedly matched")
            trials.append(
                {
                    **base,
                    "absence_evidence": canonical_clone_v1(reviewed["absence_evidence"]),
                    "mapped_report_norm_ids": [],
                    "owner_evidence": [],
                    "page_span": None,
                    "period_axis_evidence": [],
                    "presentation": reviewed["presentation"],
                    "source_geometry_mode": None,
                    "source_period": None,
                    "source_period_status": "NOT_APPLICABLE_DETAILED_NOTE_ABSENT",
                    "status": "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                }
            )
            continue
        if not same_typed_json_v1(
            matcher["uniqueness"],
            {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"},
        ):
            raise _error("reviewed region is not the unique whole-PDF cash-equivalents graph")
        region = matcher["regions"][0]
        if not same_typed_json_v1(region["page_span"], reviewed["page_span"]):
            raise _error("reviewed cash-equivalents page span drifted")
        if region["layout"]["observed_roles"] != reviewed["graph_roles"]:
            raise _error("reviewed cash-equivalents graph role axis drifted")
        axis_document = _document(axis["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        cache: dict[str, dict[str, Any]] = {}

        def verified(
            ref: Mapping[str, Any],
            *,
            cache: dict[str, dict[str, Any]] = cache,
            axis_document: Mapping[str, Any] = axis_document,
            semantic_document: Mapping[str, Any] = semantic_document,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> dict[str, Any]:
            key = canonical_json_sha256_v1(ref)
            if key not in cache:
                cache[key] = other._verified_value(
                    axis_document, semantic_document, crop_document, ref
                )
            return canonical_clone_v1(cache[key])

        verified_mappings = []
        by_role: dict[str, dict[str, Any]] = {}
        mapped_ids = set()
        for mapping in reviewed["mappings"]:
            item = {
                "blank_axes": list(mapping["blank_axes"]),
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, label)
                    for label in mapping["labels"]
                ],
                "role": mapping["role"],
                "schema_binding": _schema_binding(
                    schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                ),
                "status": "VERIFIED_BY_CODEX",
                "topology": mapping["topology"],
                "values": [
                    {"axis_role": axis_role, **verified(ref)}
                    for axis_role, ref in mapping["values"].items()
                ],
            }
            verified_mappings.append(item)
            by_role[item["role"]] = item
            mapped_ids.add(mapping["report_norm_id"])
        equations = []
        for specification in reviewed["equations"]:
            for axis_role in specification["axes"]:
                parent = next(
                    value
                    for value in by_role[specification["parent_role"]]["values"]
                    if value["axis_role"] == axis_role
                )
                terms = [
                    next(
                        value
                        for value in by_role[role]["values"]
                        if value["axis_role"] == axis_role
                    )
                    for role in specification["term_roles"]
                ]
                computed = sum(item["normalized_value"] for item in terms)
                if computed != parent["normalized_value"]:
                    raise _error(
                        f"cash-equivalents equation does not close for {code}/{specification['name']}/{axis_role}"
                    )
                equations.append(
                    {
                        "axis_role": axis_role,
                        "computed_value": computed,
                        "name": specification["name"],
                        "parent_role": specification["parent_role"],
                        "status": "VERIFIED_EXACT",
                        "term_roles": list(specification["term_roles"]),
                        "visible_total": parent["normalized_value"],
                    }
                )
        period_status = SOURCE_PERIOD_STATUS_BY_PERIOD.get(reviewed["source_period"])
        if period_status is None:
            raise _error("reviewed cash-equivalents source period is unsupported")
        page_number = reviewed["page_span"][0]
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "mapped_report_norm_ids": sorted(mapped_ids),
                "owner_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["owner"]
                ],
                "page_span": list(reviewed["page_span"]),
                "period_axis_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["period_axis"]
                ],
                "presentation": reviewed["presentation"],
                "source_geometry_mode": _page(semantic_document, page_number, "semantic index")[
                    "geometry_mode"
                ],
                "source_period": reviewed["source_period"],
                "source_period_status": period_status,
                "status": (
                    "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
                    if period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                    else "VERIFIED_BY_CODEX"
                ),
                "unit_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
            }
        )
    mapped_union = sorted(
        {
            item["schema_binding"]["report_norm_id"]
            for trial in trials
            for item in trial["verified_mappings"]
        }
    )
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
        },
        "metrics": _metrics(trials),
        "schema_family": {
            "family_end_display_order": FAMILY_END_DISPLAY_ORDER,
            "family_root": _schema_binding(schema_by_id.get(1248), 1248),
            "mapped_report_norm_ids": mapped_union,
            "schema_gap_source_row_count": 0,
            "section_root": _schema_binding(schema_by_id.get(1247), 1247),
        },
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_cash_equivalents_8bank_codex_verified_mapping_replay_v1(
    value: Any, **inputs: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_cash_equivalents_8bank_codex_verified_mapping_v1(**inputs)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("cash-equivalents verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = other.operating.income.foundation.support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = other.operating.income.foundation.support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _live_inputs() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_cash_equivalents_full_document_scan_v1(
        SEMANTIC_INDEX_PATH, variant_profile=VARIANT_PROFILE
    )
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    if ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT:
        # E-0092 is a fixed historical receipt.  Later additive TM-schema
        # revisions must not silently rewrite its already authenticated input
        # authority.  The exact persisted result ID pins this snapshot, while
        # current schema rows are still independently checked above.
        persisted_result, _ = _stable_json(RESULT_PATH)
        persisted_result = _validate_result(persisted_result)
        schema_authority = canonical_clone_v1(persisted_result["input_refs"]["schema_authority"])
    return {
        "semantic_index": semantic_index,
        "crop_manifest": crop_manifest,
        "structure_scan": structure_scan,
        "review": review,
        "schema_authority": schema_authority,
        "schema_by_id": schema_by_id,
        "crop_manifest_sha256": crop_sha,
        "review_sha256": review_sha,
    }


def build_live_cash_equivalents_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_cash_equivalents_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_cash_equivalents_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    return validate_cash_equivalents_8bank_codex_verified_mapping_replay_v1(value, **_live_inputs())


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
        _write(RESULT_PATH, build_live_cash_equivalents_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_cash_equivalents_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
