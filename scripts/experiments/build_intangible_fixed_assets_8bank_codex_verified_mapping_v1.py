"""Verify and map the eight-bank intangible fixed-asset movement family."""

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


base = _load_module(
    "tangible_fixed_assets_support_for_intangible_mapping",
    "build_tangible_fixed_assets_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "intangible_fixed_assets_scan_for_verified_mapping",
    "scan_intangible_fixed_assets_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "INTANGIBLE_FIXED_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "INTANGIBLE_FIXED_ASSETS_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_SHARED_INTANGIBLE_FIXED_"
    "ASSET_VARIANT_GRAPH_VISIBLE_PIXEL_UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_"
    "CHALLENGER_CURRENT_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_"
    "EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0071-intangible-fixed-assets-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0071-intangible-fixed-assets-8bank-codex-verified-mapping-v1.json"
)
EXPECTED_PERSISTED_RESULT = (
    "d3e5d1a5609108379f3bf2618178e1b8a738e00ef7171b0615fd5bf459e2f172",
    91_222,
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "ifafdsv1:scan:8f3ecf325f3d0496a3cd29648eea33be4d7ab7c27308e1f1955a189a88754980"

_REVIEW_CHECKS = (
    "COMPLETE_PDF_UNIQUE_REGION_OR_BOUND_REPORT_ABSENCE",
    "OWNER_PRECEDES_COST_AMORTIZATION_AND_CARRYING_BRANCHES",
    "OPTIONAL_MOVEMENT_ROWS_AND_ASSET_CLASS_COLUMNS",
    "CURRENT_REPORTING_PERIOD_SELECTED_COMPARATIVE_EXCLUDED",
    "MILLION_VND_UNIT_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_CHALLENGER",
    "OPENING_PLUS_MOVEMENTS_EQUALS_CLOSING",
    "COST_MINUS_AMORTIZATION_EQUALS_CARRYING_VALUE",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
)
_REVIEW_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "comparison_period_used_as_mapping_authority": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_PPOCRV6_OR_NATIVE_CHALLENGER",
    "old_ocr_used_as_semantic_anchor": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_other_report_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_intangible_fixed_asset_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "upstream_ppocrv6_or_native_text_used_only_as_numeric_challenger": True,
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
_ABSENT_TRIAL_FIELDS = {
    "absence_reason",
    "boundary_evidence",
    "boundary_pages",
    "disposition",
    "document_ordinal",
    "document_provenance",
    "equations",
    "mappings",
    "source_pdf_sha256",
    "source_period",
    "source_period_status",
    "structure_graph_id",
}
_PRESENT_TRIAL_FIELDS = {
    "absence_reason",
    "branch_evidence",
    "comparative_control",
    "disposition",
    "document_ordinal",
    "document_provenance",
    "equations",
    "mappings",
    "owner_evidence",
    "page_sequence",
    "source_pdf_sha256",
    "source_period",
    "source_period_status",
    "structure_graph_id",
    "unit_authority",
    "visible_page_render_binding",
}

# 6069 is the source-evidence-driven family leaf introduced by this checkpoint.
_SCHEMA_EXPECTED = {
    913: ("Tăng, giảm tài sản cố định vô hình", 560),
    914: ("Nguyên giá", 913),
    915: ("Số dư đầu kỳ", 914),
    5997: ("Tổng tăng nguyên giá TSCĐ vô hình trong kỳ", 914),
    916: ("+ Mua trong kỳ", 5997),
    917: ("+ Đầu tư XDCB hoàn thành", 5997),
    918: ("+ Chuyển từ chi phí xây dựng CBDD", 5997),
    919: ("+ Tăng do hợp nhất kinh doanh", 5997),
    920: ("+ Tăng khác", 5997),
    6068: ("Tổng giảm nguyên giá TSCĐ vô hình trong kỳ", 914),
    921: ("+ Chuyển sang BĐS đầu tư (*)", 6068),
    922: ("+ Chuyển sang công cụ dụng cụ", 6068),
    923: ("+ Chuyển sang chi phí chờ phân bổ", 6068),
    924: ("+ Phân loại lại", 6068),
    925: ("+ Thanh lý. nhượng bán (*)", 6068),
    926: ("+ Trích lập quỹ", 6068),
    927: ("+ Giảm khác (*)", 6068),
    5998: ("Tăng/(Giảm) khác nguyên giá TSCĐ vô hình trong kỳ", 914),
    5967: ("+ Chênh lệch tỷ giá", 914),
    928: ("Số dư cuối kỳ", 914),
    929: ("Giá trị hao mòn luỹ kế", 913),
    930: ("Số dư đầu kỳ", 929),
    5999: ("Tổng tăng hao mòn TSCĐ vô hình trong kỳ", 929),
    931: ("+ Khấu hao trong kỳ", 5999),
    932: ("+ Tăng do hợp nhất kinh doanh", 5999),
    933: ("+ Tăng khác", 5999),
    6000: ("Tổng giảm hao mòn TSCĐ vô hình trong kỳ", 929),
    934: ("+ Chuyển sang BĐS đầu tư (*)", 6000),
    935: ("+ Chuyển sang công cụ dụng cụ", 6000),
    936: ("+ Chuyển sang chi phí chờ phân bổ", 6000),
    937: ("+ Phân loại lại", 6000),
    938: ("+ Thanh lý. nhượng bán (*)", 6000),
    939: ("+ Trích lập quỹ", 6000),
    940: ("+ Giảm khác (*)", 6000),
    6001: ("Tăng/(Giảm) khác hao mòn TSCĐ vô hình trong kỳ", 929),
    5968: ("+ Chênh lệch tỷ giá", 929),
    941: ("Số dư cuối kỳ", 929),
    5969: ("Giá trị còn lại", 913),
    5970: ("Số dư đầu kỳ", 5969),
    5971: ("Số dư cuối kỳ", 5969),
    6069: ("Nguyên giá TSCĐ vô hình đã hao mòn hết nhưng vẫn còn sử dụng", 913),
}
_MAPPED_SCHEMA_IDS = frozenset(
    {915, 5997, 916, 920, 925, 5967, 928, 930, 5999, 931, 6000, 5968, 941, 5970, 5971, 6069}
)
_BOUNDARIES = {
    "ACB": (
        (19, "cac khoan dau tu dai han khac", "CÁC KHOẢN ĐẦU TƯ DÀI HẠN KHÁC"),
        (20, "cac khoan no chinh phu", "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC"),
    ),
    "HDB": (
        (30, "gop von dau tu dai han", "Góp vốn, đầu tư dài hạn"),
        (31, "vay cac tctd khac", "Vay các TCTD khác"),
    ),
    "VCB": (
        (33, "gop von dau tu dai han", "Góp vốn đầu tư dài hạn"),
        (34, "cac khoan no chinh phu", "Các khoản nợ Chính phủ và Ngân hàng Nhà nước"),
    ),
    "CTG": (
        (40, "chung khoan dau tu", "CHỨNG KHOÁN ĐẦU TƯ"),
        (41, "cac khoan no chinh phu", "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN"),
    ),
    "BID": (
        (24, "gop von dau tu dai han", "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        (25, "tien gui va vay cac tctd khac", "TIỀN GỬI VÀ VAY CÁC TCTD KHÁC"),
    ),
}


class IntangibleFixedAssets8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, numeric challenger, accounting or schema drifted."""


def _error(message: str) -> IntangibleFixedAssets8BankCodexVerifiedMappingV1Error:
    return IntangibleFixedAssets8BankCodexVerifiedMappingV1Error(message)


def _value(line_index: int, pixel_transcription: str) -> dict[str, Any]:
    return {
        "line_index": line_index,
        "pixel_transcription": pixel_transcription,
        "ppocr_rotated_line_index": None,
    }


def _mapping(
    report_norm_id: int,
    role: str,
    label_refs: Sequence[tuple[int, str]],
    value: dict[str, Any],
    *,
    topology: str,
) -> dict[str, Any]:
    return {
        "label_refs": [
            {"line_index": line_index, "pixel_transcription": text}
            for line_index, text in label_refs
        ],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "value": value,
    }


def _term(value: dict[str, Any], multiplier: int = 1) -> dict[str, Any]:
    if multiplier not in {-1, 1}:
        raise _error("accounting equation multiplier must be +1 or -1")
    return {"multiplier": multiplier, "value": value}


def _equation(
    name: str, components: Sequence[dict[str, Any]], total: dict[str, Any]
) -> dict[str, Any]:
    return {"components": list(components), "name": name, "total": total}


def _present_doc(
    bank_code: str,
    page_sequence: int,
    owner_line_index: int,
    owner_pixel_transcription: str,
    source_period: str,
    branch_bindings: Sequence[tuple[str, int, str]],
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[dict[str, Any]],
    *,
    comparative_control_page: int | None = None,
) -> dict[str, Any]:
    return {
        "bank_code": bank_code,
        "branch_bindings": [
            {"line_index": index, "pixel_transcription": text, "role": role}
            for role, index, text in branch_bindings
        ],
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "comparative_control_page": comparative_control_page,
        "disposition": "VERIFIED_INTANGIBLE_FIXED_ASSET_MOVEMENT_NOTE",
        "equations": list(equations),
        "mappings": list(mappings),
        "owner_line_index": owner_line_index,
        "owner_pixel_transcription": owner_pixel_transcription,
        "page_sequence": page_sequence,
        "source_period": source_period,
        "unit_authority": "VISIBLE_PAGE_MILLION_VND",
    }


def _absent_doc(bank_code: str, reason: str) -> dict[str, Any]:
    return {
        "bank_code": bank_code,
        "branch_bindings": [],
        "checks": {check: "NOT_APPLICABLE" for check in _REVIEW_CHECKS},
        "comparative_control_page": None,
        "disposition": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
        "equations": [],
        "mappings": [],
        "owner_line_index": None,
        "owner_pixel_transcription": None,
        "page_sequence": None,
        "source_period": None,
        "unit_authority": None,
        "absence_reason": reason,
    }


def _review_documents() -> list[dict[str, Any]]:
    mbb = {
        "cost_open": _value(16, "5.684.904"),
        "cost_increase": _value(20, "256.637"),
        "cost_disposal": _value(23, "(11.925)"),
        "cost_fx": _value(26, "(32)"),
        "cost_close": _value(31, "5.929.584"),
        "dep_open": _value(37, "3.873.890"),
        "dep_increase": _value(42, "254.331"),
        "dep_decrease": _value(45, "(10.344)"),
        "dep_fx": _value(48, "119"),
        "dep_close": _value(53, "4.117.996"),
        "carry_open": _value(59, "1.811.014"),
        "carry_close": _value(64, "1.811.588"),
    }
    vpb = {
        "cost_open": _value(21, "2.205.181"),
        "cost_purchase": _value(25, "2.427"),
        "cost_other": _value(29, "29.765"),
        "cost_close": _value(33, "2.237.373"),
        "dep_open": _value(38, "1.655.626"),
        "dep_increase": _value(42, "41.919"),
        "dep_close": _value(46, "1.697.545"),
        "carry_open": _value(51, "549.555"),
        "carry_close": _value(55, "539.828"),
        "fully_amortized": _value(59, "1.219.881"),
    }
    vib = {
        "cost_open": _value(18, "843.503"),
        "cost_purchase": _value(21, "252.445"),
        "cost_disposal": _value(24, "(46.285)"),
        "cost_close": _value(28, "1.049.663"),
        "dep_open": _value(33, "545.559"),
        "dep_increase": _value(36, "41.878"),
        "dep_close": _value(40, "587.437"),
        "carry_open": _value(44, "297.944"),
        "carry_close": _value(47, "462.226"),
        "fully_amortized": _value(55, "314.667"),
    }
    return [
        _absent_doc(
            "ACB",
            "OTHER_LONG_TERM_INVESTMENTS_END_THEN_GOVERNMENT_LIABILITIES_NO_INTANGIBLE_NOTE",
        ),
        _present_doc(
            "MBB",
            39,
            0,
            "Tài sản cố định vô hình",
            "2026-06-30",
            [
                ("COST", 11, "Nguyên giá"),
                ("ACCUMULATED_AMORTIZATION", 32, "Giá trị hao mòn lũy kế"),
                ("CARRYING_VALUE", 54, "Giá trị còn lại"),
            ],
            [
                _mapping(
                    915,
                    "COST_OPENING",
                    [(12, "Số dư đầu kỳ")],
                    mbb["cost_open"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    5997,
                    "COST_TOTAL_INCREASE",
                    [(17, "Tăng trong kỳ")],
                    mbb["cost_increase"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    925,
                    "COST_DISPOSAL",
                    [(21, "Thanh lý trong kỳ")],
                    mbb["cost_disposal"],
                    topology="COST_DECREASE_CHILD",
                ),
                _mapping(
                    5967,
                    "COST_FOREIGN_EXCHANGE",
                    [(24, "Chênh lệch tỷ giá")],
                    mbb["cost_fx"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    928,
                    "COST_ENDING",
                    [(27, "Số dư cuối kỳ")],
                    mbb["cost_close"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    930,
                    "AMORTIZATION_OPENING",
                    [(33, "Số dư đầu kỳ")],
                    mbb["dep_open"],
                    topology="AMORTIZATION_CHILD",
                ),
                _mapping(
                    5999,
                    "AMORTIZATION_TOTAL_INCREASE",
                    [(38, "Tăng trong kỳ")],
                    mbb["dep_increase"],
                    topology="AMORTIZATION_CHILD",
                ),
                _mapping(
                    6000,
                    "AMORTIZATION_TOTAL_DECREASE",
                    [(43, "Giảm trong kỳ")],
                    mbb["dep_decrease"],
                    topology="AMORTIZATION_CHILD",
                ),
                _mapping(
                    5968,
                    "AMORTIZATION_FOREIGN_EXCHANGE",
                    [(46, "Chênh lệch tỷ giá")],
                    mbb["dep_fx"],
                    topology="AMORTIZATION_CHILD",
                ),
                _mapping(
                    941,
                    "AMORTIZATION_ENDING",
                    [(49, "Số dư cuối kỳ")],
                    mbb["dep_close"],
                    topology="AMORTIZATION_CHILD",
                ),
                _mapping(
                    5970,
                    "CARRYING_OPENING",
                    [(55, "Số dư đầu kỳ")],
                    mbb["carry_open"],
                    topology="CARRYING_CHILD",
                ),
                _mapping(
                    5971,
                    "CARRYING_ENDING",
                    [(60, "Số dư cuối kỳ")],
                    mbb["carry_close"],
                    topology="CARRYING_CHILD",
                ),
            ],
            [
                _equation(
                    "COST_ROLLFORWARD",
                    [
                        _term(mbb[k])
                        for k in ("cost_open", "cost_increase", "cost_disposal", "cost_fx")
                    ],
                    mbb["cost_close"],
                ),
                _equation(
                    "AMORTIZATION_ROLLFORWARD",
                    [_term(mbb[k]) for k in ("dep_open", "dep_increase", "dep_decrease", "dep_fx")],
                    mbb["dep_close"],
                ),
                _equation(
                    "OPENING_COST_MINUS_AMORTIZATION",
                    [_term(mbb["cost_open"]), _term(mbb["dep_open"], -1)],
                    mbb["carry_open"],
                ),
                _equation(
                    "ENDING_COST_MINUS_AMORTIZATION",
                    [_term(mbb["cost_close"]), _term(mbb["dep_close"], -1)],
                    mbb["carry_close"],
                ),
            ],
            comparative_control_page=40,
        ),
        _present_doc(
            "VPB",
            50,
            7,
            "Tài sản cố định vô hình",
            "2026-03-31",
            [
                ("COST", 17, "Nguyên giá"),
                ("ACCUMULATED_AMORTIZATION", 34, "Giá trị hao mòn lũy kế"),
                ("CARRYING_VALUE", 47, "Giá trị còn lại"),
            ],
            [
                _mapping(
                    915,
                    "COST_OPENING",
                    [(18, "Số dư đầu kỳ")],
                    vpb["cost_open"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    916,
                    "COST_PURCHASE",
                    [(22, "Mua trong kỳ")],
                    vpb["cost_purchase"],
                    topology="COST_INCREASE_CHILD",
                ),
                _mapping(
                    920,
                    "COST_OTHER_INCREASE",
                    [(26, "Tăng khác")],
                    vpb["cost_other"],
                    topology="COST_INCREASE_CHILD",
                ),
                _mapping(
                    928,
                    "COST_ENDING",
                    [(30, "Số dư cuối kỳ")],
                    vpb["cost_close"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    930,
                    "AMORTIZATION_OPENING",
                    [(35, "Số dư đầu kỳ")],
                    vpb["dep_open"],
                    topology="AMORTIZATION_CHILD",
                ),
                _mapping(
                    931,
                    "AMORTIZATION_INCREASE",
                    [(39, "Trích khấu hao trong kỳ")],
                    vpb["dep_increase"],
                    topology="AMORTIZATION_INCREASE_CHILD",
                ),
                _mapping(
                    941,
                    "AMORTIZATION_ENDING",
                    [(43, "Số dư cuối kỳ")],
                    vpb["dep_close"],
                    topology="AMORTIZATION_CHILD",
                ),
                _mapping(
                    5970,
                    "CARRYING_OPENING",
                    [(48, "Số dư đầu kỳ")],
                    vpb["carry_open"],
                    topology="CARRYING_CHILD",
                ),
                _mapping(
                    5971,
                    "CARRYING_ENDING",
                    [(52, "Số dư cuối kỳ")],
                    vpb["carry_close"],
                    topology="CARRYING_CHILD",
                ),
                _mapping(
                    6069,
                    "FULLY_AMORTIZED_STILL_IN_USE",
                    [
                        (
                            56,
                            "Nguyên giá tài sản cố định vô hình đã khấu hao hết nhưng vẫn còn sử dụng",
                        )
                    ],
                    vpb["fully_amortized"],
                    topology="FAMILY_DISCLOSURE_CHILD",
                ),
            ],
            [
                _equation(
                    "COST_ROLLFORWARD",
                    [_term(vpb[k]) for k in ("cost_open", "cost_purchase", "cost_other")],
                    vpb["cost_close"],
                ),
                _equation(
                    "AMORTIZATION_ROLLFORWARD",
                    [_term(vpb[k]) for k in ("dep_open", "dep_increase")],
                    vpb["dep_close"],
                ),
                _equation(
                    "OPENING_COST_MINUS_AMORTIZATION",
                    [_term(vpb["cost_open"]), _term(vpb["dep_open"], -1)],
                    vpb["carry_open"],
                ),
                _equation(
                    "ENDING_COST_MINUS_AMORTIZATION",
                    [_term(vpb["cost_close"]), _term(vpb["dep_close"], -1)],
                    vpb["carry_close"],
                ),
            ],
        ),
        _absent_doc(
            "HDB",
            "OTHER_LONG_TERM_INVESTMENTS_THEN_GOVERNMENT_OR_INTERBANK_LIABILITIES_NO_INTANGIBLE_NOTE",
        ),
        _absent_doc(
            "VCB",
            "OTHER_LONG_TERM_INVESTMENTS_END_THEN_GOVERNMENT_LIABILITIES_NO_INTANGIBLE_NOTE",
        ),
        _absent_doc(
            "CTG",
            "INVESTMENT_SECURITIES_END_THEN_GOVERNMENT_LIABILITIES_NO_INTANGIBLE_NOTE",
        ),
        _absent_doc(
            "BID",
            "OTHER_LONG_TERM_INVESTMENTS_THEN_INTERBANK_LIABILITIES_NO_INTANGIBLE_NOTE",
        ),
        _present_doc(
            "VIB",
            38,
            5,
            "TÀI SẢN CỐ ĐỊNH VÔ HÌNH",
            "2026-06-30",
            [
                ("COST", 14, "Nguyên giá"),
                ("ACCUMULATED_AMORTIZATION", 29, "Hao mòn lũy kế"),
                ("CARRYING_VALUE", 41, "Giá trị còn lại"),
            ],
            [
                _mapping(
                    915,
                    "COST_OPENING",
                    [(15, "Tại ngày 1/1/2026")],
                    vib["cost_open"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    916,
                    "COST_PURCHASE",
                    [(19, "Mua trong kỳ")],
                    vib["cost_purchase"],
                    topology="COST_INCREASE_CHILD",
                ),
                _mapping(
                    925,
                    "COST_DISPOSAL",
                    [(22, "Thanh lý")],
                    vib["cost_disposal"],
                    topology="COST_DECREASE_CHILD",
                ),
                _mapping(
                    928,
                    "COST_ENDING",
                    [(25, "Tại ngày 30/06/2026")],
                    vib["cost_close"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    930,
                    "AMORTIZATION_OPENING",
                    [(30, "Tại ngày 1/1/2026")],
                    vib["dep_open"],
                    topology="AMORTIZATION_CHILD",
                ),
                _mapping(
                    931,
                    "AMORTIZATION_INCREASE",
                    [(34, "Hao mòn trong kỳ")],
                    vib["dep_increase"],
                    topology="AMORTIZATION_INCREASE_CHILD",
                ),
                _mapping(
                    941,
                    "AMORTIZATION_ENDING",
                    [(37, "Tại ngày 30/06/2026")],
                    vib["dep_close"],
                    topology="AMORTIZATION_CHILD",
                ),
                _mapping(
                    5970,
                    "CARRYING_OPENING",
                    [(42, "Tại ngày 1/1/2026")],
                    vib["carry_open"],
                    topology="CARRYING_CHILD",
                ),
                _mapping(
                    5971,
                    "CARRYING_ENDING",
                    [(45, "Tại ngày 30/06/2026")],
                    vib["carry_close"],
                    topology="CARRYING_CHILD",
                ),
                _mapping(
                    6069,
                    "FULLY_AMORTIZED_STILL_IN_USE",
                    [(53, "Nguyên giá TSCĐ vô hình đã hao mòn hết nhưng vẫn còn"), (54, "sử dụng")],
                    vib["fully_amortized"],
                    topology="FAMILY_DISCLOSURE_CHILD",
                ),
            ],
            [
                _equation(
                    "COST_ROLLFORWARD",
                    [_term(vib[k]) for k in ("cost_open", "cost_purchase", "cost_disposal")],
                    vib["cost_close"],
                ),
                _equation(
                    "AMORTIZATION_ROLLFORWARD",
                    [_term(vib[k]) for k in ("dep_open", "dep_increase")],
                    vib["dep_close"],
                ),
                _equation(
                    "OPENING_COST_MINUS_AMORTIZATION",
                    [_term(vib["cost_open"]), _term(vib["dep_open"], -1)],
                    vib["carry_open"],
                ),
                _equation(
                    "ENDING_COST_MINUS_AMORTIZATION",
                    [_term(vib["cost_close"]), _term(vib["dep_close"], -1)],
                    vib["carry_close"],
                ),
            ],
        ),
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "authority": canonical_clone_v1(_REVIEW_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "state": "CODEX_VISIBLE_PDF_REVIEW_COMPLETE",
    }
    return {
        **material,
        "review_id": "e0071:review:" + canonical_json_sha256_v1(material),
    }


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("intangible-fixed-assets pixel review drifted")
    return canonical_clone_v1(expected)


def _pinned_schema_family() -> tuple[dict[str, Any], dict[str, Any]]:
    payload = base.support._stable_bytes(RESULT_PATH)
    if (hashlib.sha256(payload).hexdigest(), len(payload)) != EXPECTED_PERSISTED_RESULT:
        raise _error("pinned intangible-fixed-assets result identity drifted")
    persisted = base.support._strict_json(payload, RESULT_PATH.as_posix())
    input_refs = persisted.get("input_refs")
    snapshot_authority = input_refs.get("schema_authority") if type(input_refs) is dict else None
    snapshot_family = persisted.get("schema_family")
    if type(snapshot_authority) is not dict or type(snapshot_family) is not dict:
        raise _error("pinned intangible-fixed-assets schema snapshot drifted")
    items = snapshot_family.get("items")
    if (
        snapshot_family.get("first_report_norm_id") != 913
        or snapshot_family.get("last_report_norm_id") != 6069
        or type(items) is not list
        or [item.get("report_norm_id") for item in items if type(item) is dict]
        != list(_SCHEMA_EXPECTED)
        or snapshot_family.get("schema_authority") != snapshot_authority
    ):
        raise _error("pinned intangible-fixed-assets family snapshot drifted")
    return canonical_clone_v1(snapshot_authority), canonical_clone_v1(snapshot_family)


def _schema_family(schema_authority: Any, schema_by_id: Mapping[int, Any]) -> dict[str, Any]:
    for schema_id, (name, parent_id) in _SCHEMA_EXPECTED.items():
        item = schema_by_id.get(schema_id)
        if (
            item is None
            or item.statement_type != "TM"
            or item.canonical_name != name
            or item.parent_id != parent_id
        ):
            raise _error(f"live intangible-fixed-assets schema binding drifted: {schema_id}")
    if type(schema_authority) is not dict:
        raise _error("live intangible-fixed-assets schema authority drifted")
    _, snapshot_family = _pinned_schema_family()
    return snapshot_family


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    if (
        report_norm_id not in _MAPPED_SCHEMA_IDS
        or expected is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
    ):
        raise _error(f"live TM schema binding drifted for ReportNormId {report_norm_id}")
    _, snapshot = _pinned_schema_family()
    pinned = next(
        (raw for raw in snapshot["items"] if raw["report_norm_id"] == report_norm_id),
        None,
    )
    if type(pinned) is not dict:
        raise _error(f"pinned TM schema binding is absent for ReportNormId {report_norm_id}")
    return {
        "canonical_name": pinned["canonical_name"],
        "display_order": pinned["display_order"],
        "hierarchy_level": pinned["hierarchy_level"],
        "report_norm_id": pinned["report_norm_id"],
        "schema_parent_report_norm_id": pinned["parent_report_norm_id"],
    }


def _boundary_evidence(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    entries: Sequence[tuple[int, str, str]],
) -> list[dict[str, Any]]:
    evidence = []
    for page_sequence, phrase, pixel_text in entries:
        axis_page = base._page(axis_document, page_sequence, "accounting axis")
        semantic_page = base._page(semantic_document, page_sequence, "semantic index")
        crop_page = base._page(crop_document, page_sequence, "crop manifest")
        candidates = [
            line
            for line in axis_page["lines"]
            if phrase in normalize_vietnamese_anchor_v1(line["vietocr_text"])
        ]
        if not candidates:
            raise _error("visible family-boundary anchor was not found")
        line = min(
            candidates, key=lambda item: (len(item["vietocr_text"]), item["source_line_index"])
        )
        evidence.append(
            {
                "anchor": base._semantic_evidence(
                    axis_page, semantic_page, line["source_line_index"], pixel_text, {}
                ),
                "page_sequence": page_sequence,
                "render_binding": canonical_clone_v1(crop_page["render_binding"]),
            }
        )
    return evidence


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_count": sum(len(trial["equations"]) for trial in trials),
        "confirmed_bound_report_absence_count": sum(
            trial["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "mapping_verified_count": sum(len(trial["mappings"]) for trial in trials),
        "open_review_item_count": 0,
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "verified_present_document_count": sum(bool(trial["mappings"]) for trial in trials),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("intangible-fixed-assets result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "INTANGIBLE_FIXED_ASSETS_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or type(value["schema_family"]) is not dict
    ):
        raise _error("intangible-fixed-assets result identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict:
            raise _error("intangible-fixed-assets trial must be one exact object")
        expected_fields = (
            _ABSENT_TRIAL_FIELDS
            if trial.get("disposition") == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
            else _PRESENT_TRIAL_FIELDS
        )
        if (
            set(trial) != expected_fields
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or type(trial.get("mappings")) is not list
            or type(trial.get("equations")) is not list
        ):
            raise _error("intangible-fixed-assets trial identity drifted")
        for mapping in trial["mappings"]:
            if mapping.get("final_status") != "VERIFIED_BY_CODEX":
                raise _error("intangible-fixed-assets mapping status drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("intangible-fixed-assets metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0071:result:" + canonical_json_sha256_v1(material):
        raise _error("intangible-fixed-assets result identity drifted")
    return canonical_clone_v1(value)


def build_intangible_fixed_assets_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_authority: Any,
    schema_by_id: Mapping[int, Any],
) -> dict[str, Any]:
    reviewed_documents = _review(review)["documents"]
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
    ):
        raise _error("fixed semantic axis or structure scan identity drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = base._document(reviewed_documents, code, "pixel review")
        scan_trial = base._document(structure_scan.get("trials"), code, "structure scan")
        axis_document = base._document(axis.get("documents"), code, "accounting axis")
        semantic_document = base._document(semantic_index.get("documents"), code, "semantic index")
        crop_document = base._document(crop_manifest.get("documents"), code, "crop manifest")
        matcher_result = scan_trial["matcher_result"]
        if reviewed["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT":
            if matcher_result["regions"] or reviewed["mappings"] or reviewed["equations"]:
                raise _error(f"absence review conflicts with complete region for {code}")
            entries = _BOUNDARIES[code]
            trials.append(
                {
                    "absence_reason": reviewed["absence_reason"],
                    "boundary_evidence": _boundary_evidence(
                        axis_document, semantic_document, crop_document, entries
                    ),
                    "boundary_pages": [entry[0] for entry in entries],
                    "disposition": reviewed["disposition"],
                    "document_ordinal": ordinal,
                    "document_provenance": code,
                    "equations": [],
                    "mappings": [],
                    "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                    "source_period": None,
                    "source_period_status": "NOT_APPLICABLE_FAMILY_NOT_PRESENT",
                    "structure_graph_id": matcher_result["result_id"],
                }
            )
            continue
        regions = matcher_result["regions"]
        if (
            len(regions) != 1
            or regions[0]["owner"]["page_sequence"] != reviewed["page_sequence"]
            or regions[0]["owner"]["source_line_index"] != reviewed["owner_line_index"]
        ):
            raise _error(f"reviewed current-period region does not match whole-PDF scan for {code}")
        axis_page = base._page(axis_document, reviewed["page_sequence"], "accounting axis")
        semantic_page = base._page(semantic_document, reviewed["page_sequence"], "semantic index")
        crop_page = base._page(crop_document, reviewed["page_sequence"], "crop manifest")
        source_texts = base.support._source_line_axis(crop_page)
        owner_evidence = base._semantic_evidence(
            axis_page,
            semantic_page,
            reviewed["owner_line_index"],
            reviewed["owner_pixel_transcription"],
            {},
        )
        branch_evidence = [
            {
                "role": branch["role"],
                **base._semantic_evidence(
                    axis_page,
                    semantic_page,
                    branch["line_index"],
                    branch["pixel_transcription"],
                    {},
                ),
            }
            for branch in reviewed["branch_bindings"]
        ]
        mappings = []
        values_by_line: dict[int, dict[str, Any]] = {}
        for mapping in reviewed["mappings"]:
            labels = [
                base._semantic_evidence(
                    axis_page,
                    semantic_page,
                    label["line_index"],
                    label["pixel_transcription"],
                    {},
                )
                for label in mapping["label_refs"]
            ]
            verified = base._verified_value(
                axis_page, semantic_page, source_texts, mapping["value"], {}, {}
            )
            values_by_line[mapping["value"]["line_index"]] = verified
            mappings.append(
                {
                    "final_status": "VERIFIED_BY_CODEX",
                    "label_evidence": labels,
                    "report_norm_id": mapping["report_norm_id"],
                    "role": mapping["role"],
                    "schema_binding": _schema_binding(
                        schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                    ),
                    "topology": mapping["topology"],
                    "value": verified,
                }
            )
        equations = []
        for equation in reviewed["equations"]:
            terms = []
            computed = 0
            for term in equation["components"]:
                line_index = term["value"]["line_index"]
                verified = values_by_line.get(line_index) or base._verified_value(
                    axis_page, semantic_page, source_texts, term["value"], {}, {}
                )
                computed += term["multiplier"] * verified["normalized_value"]
                terms.append(
                    {
                        "multiplier": term["multiplier"],
                        "source_line_index": line_index,
                        "value": verified["normalized_value"],
                    }
                )
            total_line = equation["total"]["line_index"]
            total = values_by_line.get(total_line) or base._verified_value(
                axis_page, semantic_page, source_texts, equation["total"], {}, {}
            )
            if computed != total["normalized_value"]:
                raise _error(f"accounting equation does not close for {code}: {equation['name']}")
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "status": "CORROBORATED_EXACT",
                    "terms": terms,
                    "visible_total": total["normalized_value"],
                    "visible_total_source_line_index": total_line,
                }
            )
        comparative_page = reviewed["comparative_control_page"]
        comparative_control = None
        if comparative_page is not None:
            comparative_crop_page = base._page(crop_document, comparative_page, "crop manifest")
            comparative_control = {
                "disposition": "EXCLUDED_COMPARATIVE_PERIOD",
                "page_sequence": comparative_page,
                "render_binding": canonical_clone_v1(comparative_crop_page["render_binding"]),
                "source_period": "2025-12-31",
            }
        source_period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        trials.append(
            {
                "absence_reason": None,
                "branch_evidence": branch_evidence,
                "comparative_control": comparative_control,
                "disposition": reviewed["disposition"],
                "document_ordinal": ordinal,
                "document_provenance": code,
                "equations": equations,
                "mappings": mappings,
                "owner_evidence": owner_evidence,
                "page_sequence": reviewed["page_sequence"],
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "structure_graph_id": matcher_result["result_id"],
                "unit_authority": reviewed["unit_authority"],
                "visible_page_render_binding": canonical_clone_v1(crop_page["render_binding"]),
            }
        )
    schema_family = _schema_family(schema_authority, schema_by_id)
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest_sha256": EXPECTED_CROP_MANIFEST_SHA256,
            "pixel_review_id": review["review_id"],
            "schema_authority": canonical_clone_v1(schema_family["schema_authority"]),
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "schema_family": schema_family,
        "state": "INTANGIBLE_FIXED_ASSETS_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0071:result:" + canonical_json_sha256_v1(material)}
    )


def validate_intangible_fixed_assets_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_authority: Any,
    schema_by_id: Mapping[int, Any],
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_intangible_fixed_assets_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("intangible-fixed-assets verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str) -> dict[str, Any]:
    payload = base.support._stable_bytes(path)
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    return base.support._strict_json(payload, path.as_posix())


def _live_inputs() -> tuple[Any, ...]:
    semantic_index = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_intangible_fixed_assets_full_document_scan_v1(semantic_index)
    if structure_scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("live intangible-fixed-assets structure scan identity drifted")
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return (
        semantic_index,
        crop_manifest,
        structure_scan,
        _review_blueprint(),
        schema_authority,
        schema_by_id,
    )


def build_live_intangible_fixed_assets_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_intangible_fixed_assets_8bank_codex_verified_mapping_v1(*_live_inputs())


def validate_live_intangible_fixed_assets_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    return validate_intangible_fixed_assets_8bank_codex_verified_mapping_replay_v1(
        value, *_live_inputs()
    )


def _write(path: Path, value: Any) -> None:
    payload = canonical_json_bytes_v1(value)
    if path.exists() and path.read_bytes() != payload:
        raise _error(f"refusing to replace a different artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    args = parser.parse_args()
    review = _review_blueprint()
    if args.write_review:
        _write(REVIEW_PATH, review)
    result = build_live_intangible_fixed_assets_8bank_codex_verified_mapping_v1()
    if args.write_result:
        _write(RESULT_PATH, result)
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    main()
