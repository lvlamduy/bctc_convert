"""Verify the eight-bank investment-property movement family."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from io import BytesIO
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image

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
    "intangible_fixed_assets_support_for_investment_property",
    "build_intangible_fixed_assets_8bank_codex_verified_mapping_v1.py",
)
base = foundation.base
scanner = _load_module(
    "investment_property_scan_for_verified_mapping",
    "scan_investment_property_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "INVESTMENT_PROPERTY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "INVESTMENT_PROPERTY_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_SHARED_INVESTMENT_"
    "PROPERTY_VARIANT_GRAPH_VISIBLE_PIXEL_UPSTREAM_PPOCRV6_NUMERIC_CHALLENGER_"
    "VISIBLE_DASH_ZERO_CURRENT_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_"
    "NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0072-investment-property-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path(
    "docs/experiments/E-0072-investment-property-8bank-codex-verified-mapping-v1.json"
)
EXPECTED_PERSISTED_RESULT = (
    "2831f70486cdd624a222158f0aaffdb1340e378264fa31d688e4f435136b935d",
    58_162,
)
SCHEMA_SNAPSHOT_RESULT_PATH = RESULT_PATH
EXPECTED_SCHEMA_SNAPSHOT_RESULT = EXPECTED_PERSISTED_RESULT
_RESULT_STATE = "INVESTMENT_PROPERTY_8BANK_CODEX_VERIFICATION_COMPLETE"
_RESULT_ID_PREFIX = "e0072:result:"
_REVIEW_STATE = "CODEX_VISIBLE_PDF_REVIEW_COMPLETE"
_REVIEW_ID_PREFIX = "e0072:review:"
_SOURCE_PERIOD_STATUS = "VERIFIED_SOURCE_PERIOD_Q2_2026"
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "ipfdsv1:scan:620f1f6c9d376020dc1b21632a9fd8f6b6641582f8083cb35ef31b086c31f29f"
_DASH_RGB_SHA256 = "b3934a8c8abfe8e5d6a3a80fbd72c9ec99f6402c02c104b4303b464a78b093ef"

_REVIEW_CHECKS = (
    "COMPLETE_PDF_UNIQUE_CURRENT_REGION_OR_BOUND_REPORT_ABSENCE",
    "OWNER_PRECEDES_COST_DEPRECIATION_AND_CARRYING_BRANCHES",
    "CURRENT_AND_COMPARATIVE_SAME_PAGE_REGIONS_PARTITIONED_BY_PERIOD",
    "ASSET_CLASS_COLUMNS_AND_TOTAL_COLUMN_BOUND",
    "MILLION_VND_UNIT_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "UPSTREAM_PPOCRV6_NUMERIC_CHALLENGER",
    "DASH_CELL_NORMALIZED_TO_ACCOUNTING_ZERO",
    "OPENING_PLUS_MOVEMENTS_EQUALS_CLOSING",
    "COST_MINUS_DEPRECIATION_EQUALS_CARRYING_VALUE",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
)
_REVIEW_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "comparison_period_used_as_mapping_authority": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_PPOCRV6_CHALLENGER",
    "old_ocr_used_as_semantic_anchor": False,
    "visible_dash_means_accounting_zero": True,
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
    "mapping_authority_bounded_to_reviewed_investment_property_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "upstream_ppocrv6_text_used_only_as_numeric_challenger": True,
    "visible_dash_normalized_to_zero": True,
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
    "asset_class_axes",
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

_SCHEMA_EXPECTED = {
    942: ("Tăng, giảm bất động sản đầu tư", 560),
    943: ("Nguyên giá", 942),
    944: ("Số dư đầu kỳ", 943),
    6002: ("Tổng tăng nguyên giá bất động sản đầu tư trong kỳ", 943),
    945: ("+ Mua trong kỳ", 6002),
    946: ("+ Đầu tư XDCB hoàn thành", 6002),
    947: ("+ Chuyển từ TSCĐ hữu hình", 6002),
    948: ("+ Chuyển từ chi phí xây dựng CBDD", 6002),
    949: ("+ Tăng do hợp nhất kinh doanh", 6002),
    950: ("+ Tăng khác", 6002),
    951: ("+ Phân loại lại", 6002),
    6003: ("Tổng giảm nguyên giá bất động sản đầu tư trong kỳ", 943),
    952: ("+ Thanh lý, nhượng bán (*)", 6003),
    953: ("+ Trích lập quỹ", 6003),
    954: ("+ Giảm khác (*)", 6003),
    6004: ("Tăng/(Giảm) khác nguyên giá bất động sản đầu tư trong kỳ", 943),
    955: ("Số dư cuối kỳ", 943),
    956: ("Giá trị hao mòn luỹ kế", 942),
    957: ("Số dư đầu kỳ", 956),
    6005: ("Tổng tăng hao mòn bất động sản đầu tư trong kỳ", 956),
    958: ("+ Khấu hao trong kỳ", 6005),
    959: ("+ Chuyển từ TSCĐ hữu hình", 6005),
    960: ("+ Tăng khác", 6005),
    961: ("+ Phân loại lại", 956),
    962: ("+ Thanh lý, nhượng bán (*)", 956),
    963: ("+ Trích lập quỹ", 956),
    964: ("+ Giảm khác (*)", 956),
    6006: ("Tăng/(Giảm) khác hao mòn bất động sản đầu tư trong kỳ", 956),
    965: ("Số dư cuối kỳ", 956),
    5972: ("Giá trị còn lại", 942),
    5973: ("Số dư đầu kỳ", 5972),
    5974: ("Số dư cuối kỳ", 5972),
}
_MAPPED_SCHEMA_IDS = frozenset({944, 6002, 6004, 955, 957, 6005, 965, 5973, 5974})
_BOUNDARIES = {
    "ACB": (
        (19, "gop von dau tu dai han", "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        (20, "cac khoan no chinh phu", "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC"),
    ),
    "VPB": (
        (50, "tai san co dinh vo hinh", "TÀI SẢN CỐ ĐỊNH VÔ HÌNH"),
        (51, "tai san co khac", "TÀI SẢN CÓ KHÁC"),
    ),
    "HDB": (
        (30, "gop von dau tu dai han", "Góp vốn, đầu tư dài hạn"),
        (30, "cac khoan no chinh phu", "Các khoản nợ Chính phủ và NHNN"),
    ),
    "VCB": (
        (33, "gop von dau tu dai han", "Góp vốn đầu tư dài hạn"),
        (34, "cac khoan no chinh phu", "Các khoản nợ Chính phủ và Ngân hàng Nhà nước"),
    ),
    "CTG": (
        (40, "gop von dau tu dai han", "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        (41, "cac khoan no chinh phu", "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN"),
    ),
    "BID": (
        (24, "gop von dau tu dai han", "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        (24, "cac khoan no chinh phu", "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG TRUNG ƯƠNG"),
    ),
    "VIB": (
        (38, "tai san co dinh vo hinh", "TÀI SẢN CỐ ĐỊNH VÔ HÌNH"),
        (39, "tai san co khac", "TÀI SẢN CÓ KHÁC"),
    ),
}


class InvestmentProperty8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, numeric challenger, accounting or schema drifted."""


def _error(message: str) -> InvestmentProperty8BankCodexVerifiedMappingV1Error:
    return InvestmentProperty8BankCodexVerifiedMappingV1Error(message)


def _iso_period_end(value: Any) -> list[int]:
    if type(value) is not str:
        raise _error("reviewed source period must be one ISO date")
    try:
        year, month, day = (int(part) for part in value.split("-"))
    except (TypeError, ValueError):
        raise _error("reviewed source period must be one ISO date") from None
    if not (1900 <= year <= 2200 and 1 <= month <= 12 and 1 <= day <= 31):
        raise _error("reviewed source period is outside the supported date domain")
    return [year, month, day]


def _value(line_index: int, pixel_transcription: str) -> dict[str, Any]:
    return {
        "line_index": line_index,
        "pixel_bbox": None,
        "pixel_transcription": pixel_transcription,
        "ppocr_rotated_line_index": None,
    }


def _dash_value(pixel_bbox: Sequence[int]) -> dict[str, Any]:
    return {
        "line_index": None,
        "pixel_bbox": list(pixel_bbox),
        "pixel_transcription": "-",
        "ppocr_rotated_line_index": None,
    }


def _grid_dash_value(
    row_label_line_index: int, column_value_anchor_line_index: int
) -> dict[str, Any]:
    """Describe a dash by its row and right-aligned value column, not fixed pixels."""

    return {
        "column_value_anchor_line_index": column_value_anchor_line_index,
        "line_index": None,
        "pixel_transcription": "-",
        "ppocr_rotated_line_index": None,
        "row_label_line_index": row_label_line_index,
    }


def _aggregate_value(components: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Describe a controlled sum of independently visible source cells."""

    if not components:
        raise _error("aggregate value requires at least one visible component")
    return {
        "aggregate_components": [canonical_clone_v1(component) for component in components],
        "aggregation": "SUM",
        "line_index": None,
        "pixel_transcription": None,
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
    return {"multiplier": multiplier, "value": value}


def _equation(
    name: str, components: Sequence[dict[str, Any]], total: dict[str, Any]
) -> dict[str, Any]:
    return {"components": list(components), "name": name, "total": total}


def _absent_doc(bank_code: str, reason: str) -> dict[str, Any]:
    return {
        "absence_reason": reason,
        "asset_class_axes": [],
        "bank_code": bank_code,
        "branch_bindings": [],
        "checks": {check: "NOT_APPLICABLE" for check in _REVIEW_CHECKS},
        "comparative_control": None,
        "disposition": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
        "equations": [],
        "mappings": [],
        "owner_line_index": None,
        "owner_pixel_transcription": None,
        "page_sequence": None,
        "source_period": None,
        "unit_authority": None,
    }


def _review_documents() -> list[dict[str, Any]]:
    cost_open = _value(15, "255.126")
    cost_increase = _dash_value((1360, 490, 1500, 517))
    cost_other = _value(19, "(4.971)")
    cost_close = _value(23, "250.155")
    dep_open = _value(28, "32.313")
    dep_increase = _value(32, "3.056")
    dep_close = _value(36, "35.369")
    carry_open = _value(41, "222.813")
    carry_close = _value(45, "214.786")
    mbb = {
        "absence_reason": None,
        "asset_class_axes": [
            {"line_index": 3, "pixel_transcription": "Nhà cửa,"},
            {"line_index": 5, "pixel_transcription": "vật kiến trúc"},
            {"line_index": 4, "pixel_transcription": "Quyền sử dụng"},
            {"line_index": 6, "pixel_transcription": "đất có thời hạn"},
            {"line_index": 7, "pixel_transcription": "Tổng cộng"},
        ],
        "bank_code": "MBB",
        "branch_bindings": [
            {"line_index": 11, "pixel_transcription": "Nguyên giá", "role": "COST"},
            {
                "line_index": 24,
                "pixel_transcription": "Giá trị hao mòn",
                "role": "ACCUMULATED_DEPRECIATION",
            },
            {
                "line_index": 37,
                "pixel_transcription": "Giá trị còn lại",
                "role": "CARRYING_VALUE",
            },
        ],
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "comparative_control": {
            "period_header_line_index": 46,
            "pixel_transcription": (
                "Tình hình về bất động sản đầu tư cho kỳ kết thúc ngày 31 tháng 12 năm 2025 như sau"
            ),
            "source_period": "2025-12-31",
        },
        "disposition": "VERIFIED_INVESTMENT_PROPERTY_MOVEMENT_NOTE",
        "equations": [
            _equation(
                "CURRENT_COST_ROLLFORWARD_TOTAL",
                [_term(cost_open), _term(cost_increase), _term(cost_other)],
                cost_close,
            ),
            _equation(
                "CURRENT_DEPRECIATION_ROLLFORWARD_TOTAL",
                [_term(dep_open), _term(dep_increase)],
                dep_close,
            ),
            _equation(
                "OPENING_COST_LESS_DEPRECIATION_EQUALS_CARRYING",
                [_term(cost_open), _term(dep_open, -1)],
                carry_open,
            ),
            _equation(
                "CLOSING_COST_LESS_DEPRECIATION_EQUALS_CARRYING",
                [_term(cost_close), _term(dep_close, -1)],
                carry_close,
            ),
            _equation(
                "OPENING_COST_ASSET_CLASS_SUM",
                [_term(_value(13, "55.806")), _term(_value(14, "199.320"))],
                cost_open,
            ),
            _equation(
                "CLOSING_COST_ASSET_CLASS_SUM",
                [_term(_value(21, "50.835")), _term(_value(22, "199.320"))],
                cost_close,
            ),
            _equation(
                "OPENING_DEPRECIATION_ASSET_CLASS_SUM",
                [_term(_value(26, "7.825")), _term(_value(27, "24.488"))],
                dep_open,
            ),
            _equation(
                "INCREASE_DEPRECIATION_ASSET_CLASS_SUM",
                [_term(_value(30, "500")), _term(_value(31, "2.556"))],
                dep_increase,
            ),
            _equation(
                "CLOSING_DEPRECIATION_ASSET_CLASS_SUM",
                [_term(_value(34, "8.325")), _term(_value(35, "27.044"))],
                dep_close,
            ),
            _equation(
                "OPENING_CARRYING_ASSET_CLASS_SUM",
                [_term(_value(39, "47.981")), _term(_value(40, "174.832"))],
                carry_open,
            ),
            _equation(
                "CLOSING_CARRYING_ASSET_CLASS_SUM",
                [_term(_value(43, "42.510")), _term(_value(44, "172.276"))],
                carry_close,
            ),
        ],
        "mappings": [
            _mapping(
                944,
                "COST_OPENING_TOTAL",
                [(11, "Nguyên giá"), (12, "Số dư đầu kỳ")],
                cost_open,
                topology="OWNER_COST_OPENING_TOTAL_COLUMN",
            ),
            _mapping(
                6002,
                "COST_INCREASE_TOTAL",
                [(11, "Nguyên giá"), (16, "Tăng trong kỳ")],
                cost_increase,
                topology="OWNER_COST_INCREASE_VISIBLE_DASH_TOTAL_COLUMN",
            ),
            _mapping(
                6004,
                "COST_OTHER_NET_TOTAL",
                [(11, "Nguyên giá"), (17, "Tăng/(Giảm) khác trong kỳ")],
                cost_other,
                topology="OWNER_COST_OTHER_NET_TOTAL_COLUMN",
            ),
            _mapping(
                955,
                "COST_ENDING_TOTAL",
                [(11, "Nguyên giá"), (20, "Số dư cuối kỳ")],
                cost_close,
                topology="OWNER_COST_ENDING_TOTAL_COLUMN",
            ),
            _mapping(
                957,
                "DEPRECIATION_OPENING_TOTAL",
                [(24, "Giá trị hao mòn"), (25, "Số dư đầu kỳ")],
                dep_open,
                topology="OWNER_DEPRECIATION_OPENING_TOTAL_COLUMN",
            ),
            _mapping(
                6005,
                "DEPRECIATION_INCREASE_TOTAL",
                [(24, "Giá trị hao mòn"), (29, "Tăng trong kỳ")],
                dep_increase,
                topology="OWNER_DEPRECIATION_INCREASE_TOTAL_COLUMN",
            ),
            _mapping(
                965,
                "DEPRECIATION_ENDING_TOTAL",
                [(24, "Giá trị hao mòn"), (33, "Số dư cuối kỳ")],
                dep_close,
                topology="OWNER_DEPRECIATION_ENDING_TOTAL_COLUMN",
            ),
            _mapping(
                5973,
                "CARRYING_OPENING_TOTAL",
                [(37, "Giá trị còn lại"), (38, "Số dư đầu kỳ")],
                carry_open,
                topology="OWNER_CARRYING_OPENING_TOTAL_COLUMN",
            ),
            _mapping(
                5974,
                "CARRYING_ENDING_TOTAL",
                [(37, "Giá trị còn lại"), (42, "Số dư cuối kỳ")],
                carry_close,
                topology="OWNER_CARRYING_ENDING_TOTAL_COLUMN",
            ),
        ],
        "owner_line_index": 1,
        "owner_pixel_transcription": "Bất động sản đầu tư",
        "page_sequence": 41,
        "source_period": "2026-06-30",
        "unit_authority": "VISIBLE_PAGE_MILLION_VND_TOTAL_COLUMN",
    }
    absent_reason = (
        "Complete-PDF fresh VietOCR plus adjacent-family boundary replay found no detailed "
        "investment-property movement region in this bound report; statement or accounting-policy "
        "mentions are retained only as negative controls."
    )
    return [
        _absent_doc("ACB", absent_reason),
        mbb,
        _absent_doc("VPB", absent_reason),
        _absent_doc("HDB", absent_reason),
        _absent_doc("VCB", absent_reason),
        _absent_doc("CTG", absent_reason),
        _absent_doc("BID", absent_reason),
        _absent_doc("VIB", absent_reason),
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "authority": canonical_clone_v1(_REVIEW_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "state": _REVIEW_STATE,
    }
    return {**material, "review_id": _REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("investment-property pixel review drifted")
    return canonical_clone_v1(expected)


def _pinned_schema_family() -> tuple[dict[str, Any], dict[str, Any]]:
    payload = base.support._stable_bytes(SCHEMA_SNAPSHOT_RESULT_PATH)
    if (hashlib.sha256(payload).hexdigest(), len(payload)) != EXPECTED_SCHEMA_SNAPSHOT_RESULT:
        raise _error("pinned investment-property result identity drifted")
    persisted = base.support._strict_json(payload, SCHEMA_SNAPSHOT_RESULT_PATH.as_posix())
    input_refs = persisted.get("input_refs")
    snapshot_authority = input_refs.get("schema_authority") if type(input_refs) is dict else None
    snapshot_family = persisted.get("schema_family")
    if type(snapshot_authority) is not dict or type(snapshot_family) is not dict:
        raise _error("pinned investment-property schema snapshot drifted")
    items = snapshot_family.get("items")
    if (
        snapshot_family.get("first_report_norm_id") != 942
        or snapshot_family.get("last_report_norm_id") != 5974
        or type(items) is not list
        or [item.get("report_norm_id") for item in items if type(item) is dict]
        != list(_SCHEMA_EXPECTED)
        or snapshot_family.get("schema_authority") != snapshot_authority
    ):
        raise _error("pinned investment-property family snapshot drifted")
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
            raise _error(f"live investment-property schema binding drifted: {schema_id}")
    if type(schema_authority) is not dict:
        raise _error("live investment-property schema authority drifted")
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


def _verified_dash_value(crop_page: Mapping[str, Any], value: Mapping[str, Any]) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value)
        != {
            "line_index",
            "pixel_bbox",
            "pixel_transcription",
            "ppocr_rotated_line_index",
        }
        or value["line_index"] is not None
        or value["ppocr_rotated_line_index"] is not None
        or value["pixel_transcription"] != "-"
        or type(value["pixel_bbox"]) is not list
        or len(value["pixel_bbox"]) != 4
        or any(type(item) is not int for item in value["pixel_bbox"])
    ):
        raise _error("visible dash review fields drifted")
    render_ref = crop_page.get("render_binding")
    payload = base._artifact_bytes(render_ref, "investment-property source render")
    with Image.open(BytesIO(payload)) as image:
        rgb = image.convert("RGB")
        left, top, right, bottom = value["pixel_bbox"]
        if not (0 <= left < right <= rgb.width and 0 <= top < bottom <= rgb.height):
            raise _error("visible dash bbox is outside the authenticated render")
        crop = rgb.crop((left, top, right, bottom))
    digest = hashlib.sha256(
        crop.width.to_bytes(4, "big") + crop.height.to_bytes(4, "big") + crop.tobytes()
    ).hexdigest()
    if digest != _DASH_RGB_SHA256:
        raise _error("visible dash pixel crop drifted")
    return {
        "fresh_vietocr_proposal": None,
        "normalized_pixel_transcription": "-",
        "normalized_semantic_proposal": None,
        "normalized_value": 0,
        "pixel_bbox": list(value["pixel_bbox"]),
        "pixel_rgb_sha256": digest,
        "pixel_transcription": "-",
        "rotated_ppocrv6_challenger": None,
        "rotated_ppocrv6_challenger_line_index": None,
        "rotated_ppocrv6_challenger_score": None,
        "rotated_ppocrv6_challenger_status": "NOT_APPLICABLE_VISIBLE_DASH_CELL",
        "semantic_text_source": "NO_LINE_AXIS_VISIBLE_DASH_CELL",
        "source_crop_ref": None,
        "source_line_index": None,
        "source_numeric_challenger": None,
        "source_numeric_challenger_status": "VISIBLE_DASH_HAS_NO_PPOCR_LINE_GEOMETRY",
        "source_render_ref": canonical_clone_v1(render_ref),
    }


def _verified_grid_dash_value(
    axis_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value)
        != {
            "column_value_anchor_line_index",
            "line_index",
            "pixel_transcription",
            "ppocr_rotated_line_index",
            "row_label_line_index",
        }
        or value["line_index"] is not None
        or value["ppocr_rotated_line_index"] is not None
        or value["pixel_transcription"] != "-"
        or type(value["row_label_line_index"]) is not int
        or type(value["column_value_anchor_line_index"]) is not int
    ):
        raise _error("geometry-derived dash review fields drifted")
    row = base._axis_line(axis_page, value["row_label_line_index"])
    column = base._axis_line(axis_page, value["column_value_anchor_line_index"])
    row_bbox = row["bbox"]
    column_bbox = column["bbox"]
    row_height = row_bbox[3] - row_bbox[1]
    column_width = column_bbox[2] - column_bbox[0]
    right = column_bbox[2] + max(row_height // 3, 4)
    width = max(column_width * 2, row_height * 4)
    bbox = [right - width, row_bbox[1] - 4, right, row_bbox[3] + 4]
    render_ref = crop_page.get("render_binding")
    payload = base._artifact_bytes(render_ref, "investment-property source render")
    with Image.open(BytesIO(payload)) as image:
        grayscale = image.convert("L")
        if not (
            0 <= bbox[0] < bbox[2] <= grayscale.width and 0 <= bbox[1] < bbox[3] <= grayscale.height
        ):
            raise _error("geometry-derived dash bbox is outside the authenticated render")
        crop = grayscale.crop(tuple(bbox))
        dark = [
            (x, y)
            for y in range(crop.height)
            for x in range(crop.width)
            if crop.getpixel((x, y)) < 160
        ]
        if not dark:
            raise _error("geometry-derived dash cell has no visible mark")
        mark_width = max(x for x, _ in dark) - min(x for x, _ in dark) + 1
        mark_height = max(y for _, y in dark) - min(y for _, y in dark) + 1
        if not (
            3 <= mark_width <= row_height and 1 <= mark_height <= 8 and mark_width >= mark_height
        ):
            raise _error("geometry-derived dash cell is not one short horizontal mark")
        rgb = crop.convert("RGB")
    digest = hashlib.sha256(
        rgb.width.to_bytes(4, "big") + rgb.height.to_bytes(4, "big") + rgb.tobytes()
    ).hexdigest()
    return {
        "fresh_vietocr_proposal": None,
        "normalized_pixel_transcription": "-",
        "normalized_semantic_proposal": None,
        "normalized_value": 0,
        "pixel_bbox": bbox,
        "pixel_rgb_sha256": digest,
        "pixel_transcription": "-",
        "rotated_ppocrv6_challenger": None,
        "rotated_ppocrv6_challenger_line_index": None,
        "rotated_ppocrv6_challenger_score": None,
        "rotated_ppocrv6_challenger_status": "NOT_APPLICABLE_VISIBLE_DASH_CELL",
        "semantic_text_source": "NO_LINE_AXIS_GEOMETRY_DERIVED_VISIBLE_DASH_CELL",
        "source_crop_ref": None,
        "source_line_index": None,
        "source_numeric_challenger": None,
        "source_numeric_challenger_status": "VISIBLE_DASH_HAS_NO_PPOCR_LINE_GEOMETRY",
        "source_render_ref": canonical_clone_v1(render_ref),
    }


def _verified_value(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_texts: Sequence[str],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if "aggregate_components" in value:
        if (
            type(value) is not dict
            or set(value)
            != {
                "aggregate_components",
                "aggregation",
                "line_index",
                "pixel_transcription",
                "ppocr_rotated_line_index",
            }
            or value["aggregation"] != "SUM"
            or value["line_index"] is not None
            or value["pixel_transcription"] is not None
            or value["ppocr_rotated_line_index"] is not None
            or type(value["aggregate_components"]) is not list
            or not value["aggregate_components"]
        ):
            raise _error("controlled aggregate review fields drifted")
        components = [
            _verified_value(axis_page, semantic_page, crop_page, source_texts, component)
            for component in value["aggregate_components"]
        ]
        normalized_value = sum(component["normalized_value"] for component in components)
        return {
            "aggregate_components": components,
            "aggregation": "SUM",
            "fresh_vietocr_proposal": None,
            "normalized_pixel_transcription": " + ".join(
                component["normalized_pixel_transcription"] for component in components
            ),
            "normalized_semantic_proposal": None,
            "normalized_value": normalized_value,
            "pixel_bbox": None,
            "pixel_rgb_sha256": None,
            "pixel_transcription": " + ".join(
                component["pixel_transcription"] for component in components
            ),
            "rotated_ppocrv6_challenger": None,
            "rotated_ppocrv6_challenger_line_index": None,
            "rotated_ppocrv6_challenger_score": None,
            "rotated_ppocrv6_challenger_status": "COMPONENTS_INDEPENDENTLY_VERIFIED",
            "semantic_text_source": "CONTROLLED_SUM_OF_VISIBLE_SOURCE_CELLS",
            "source_crop_ref": None,
            "source_line_index": None,
            "source_numeric_challenger": " + ".join(
                str(component["source_numeric_challenger"]) for component in components
            ),
            "source_numeric_challenger_status": "COMPONENTS_INDEPENDENTLY_VERIFIED",
            "source_render_ref": canonical_clone_v1(crop_page.get("render_binding")),
        }
    if value.get("line_index") is None:
        if "row_label_line_index" in value:
            return _verified_grid_dash_value(axis_page, crop_page, value)
        return _verified_dash_value(crop_page, value)
    normalized = {
        "line_index": value["line_index"],
        "pixel_transcription": value["pixel_transcription"],
        "ppocr_rotated_line_index": value["ppocr_rotated_line_index"],
    }
    return base._verified_value(axis_page, semantic_page, source_texts, normalized, {}, {})


def _value_key(value: Mapping[str, Any]) -> tuple[Any, ...]:
    if "aggregate_components" in value:
        return (
            "AGGREGATE_SUM",
            *(_value_key(component) for component in value["aggregate_components"]),
        )
    if "row_label_line_index" in value:
        return (
            "GRID_DASH",
            value["row_label_line_index"],
            value["column_value_anchor_line_index"],
        )
    return (
        (
            "LINE",
            value["line_index"],
        )
        if value["line_index"] is not None
        else ("DASH", *value["pixel_bbox"])
    )


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_count": sum(len(trial["equations"]) for trial in trials),
        "confirmed_bound_report_absence_count": sum(
            trial["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "mapping_verified_count": sum(len(trial["mappings"]) for trial in trials),
        "open_review_item_count": 0,
        "verified_present_document_count": sum(bool(trial["mappings"]) for trial in trials),
        "visible_dash_zero_mapping_count": sum(
            mapping["value"]["normalized_pixel_transcription"] == "-"
            for trial in trials
            for mapping in trial["mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("investment-property result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != _RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("investment-property result identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        expected_fields = (
            _ABSENT_TRIAL_FIELDS
            if trial.get("disposition") == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
            else _PRESENT_TRIAL_FIELDS
        )
        if (
            type(trial) is not dict
            or set(trial) != expected_fields
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
        ):
            raise _error("investment-property trial identity drifted")
        if any(mapping.get("final_status") != "VERIFIED_BY_CODEX" for mapping in trial["mappings"]):
            raise _error("investment-property mapping status drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("investment-property metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != _RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("investment-property result identity drifted")
    return canonical_clone_v1(value)


def build_investment_property_8bank_codex_verified_mapping_v1(
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
        comparison = reviewed["comparative_control"]
        expected_comparison_periods = (
            [] if comparison is None else [_iso_period_end(comparison["source_period"])]
        )
        if (
            len(regions) != 1
            or regions[0]["owner"]["page_sequence"] != reviewed["page_sequence"]
            or regions[0]["owner"]["source_line_index"] != reviewed["owner_line_index"]
            or regions[0]["period_end"] != _iso_period_end(reviewed["source_period"])
            or [item["period_end"] for item in regions[0]["comparison_controls"]]
            != expected_comparison_periods
        ):
            raise _error("reviewed current region does not match whole-PDF period selection")
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
        asset_class_axes = [
            base._semantic_evidence(
                axis_page,
                semantic_page,
                item["line_index"],
                item["pixel_transcription"],
                {},
            )
            for item in reviewed["asset_class_axes"]
        ]
        mappings = []
        values_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
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
            verified = _verified_value(
                axis_page, semantic_page, crop_page, source_texts, mapping["value"]
            )
            values_by_key[_value_key(mapping["value"])] = verified
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
                verified = values_by_key.get(_value_key(term["value"])) or _verified_value(
                    axis_page, semantic_page, crop_page, source_texts, term["value"]
                )
                computed += term["multiplier"] * verified["normalized_value"]
                terms.append(
                    {
                        "multiplier": term["multiplier"],
                        "source_line_index": verified["source_line_index"],
                        "value": verified["normalized_value"],
                    }
                )
            total = values_by_key.get(_value_key(equation["total"])) or _verified_value(
                axis_page, semantic_page, crop_page, source_texts, equation["total"]
            )
            if computed != total["normalized_value"]:
                raise _error(f"accounting equation does not close: {equation['name']}")
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "status": "CORROBORATED_EXACT",
                    "terms": terms,
                    "visible_total": total["normalized_value"],
                    "visible_total_source_line_index": total["source_line_index"],
                }
            )
        comparison_output = None
        if comparison is not None:
            comparison_evidence = base._semantic_evidence(
                axis_page,
                semantic_page,
                comparison["period_header_line_index"],
                comparison["pixel_transcription"],
                {},
            )
            comparison_output = {
                "disposition": "EXCLUDED_COMPARATIVE_PERIOD_SAME_PAGE",
                "period_header_evidence": comparison_evidence,
                "source_period": comparison["source_period"],
            }
        trials.append(
            {
                "absence_reason": None,
                "asset_class_axes": asset_class_axes,
                "branch_evidence": branch_evidence,
                "comparative_control": comparison_output,
                "disposition": reviewed["disposition"],
                "document_ordinal": ordinal,
                "document_provenance": code,
                "equations": equations,
                "mappings": mappings,
                "owner_evidence": owner_evidence,
                "page_sequence": reviewed["page_sequence"],
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": _SOURCE_PERIOD_STATUS,
                "structure_graph_id": matcher_result["result_id"],
                "unit_authority": reviewed["unit_authority"],
                "visible_page_render_binding": canonical_clone_v1(crop_page["render_binding"]),
            }
        )
    schema_family = _schema_family(schema_authority, schema_by_id)
    snapshot_schema_authority, _ = _pinned_schema_family()
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest_sha256": EXPECTED_CROP_MANIFEST_SHA256,
            "pixel_review_id": review["review_id"],
            "schema_authority": snapshot_schema_authority,
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "schema_family": schema_family,
        "state": _RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": _RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_investment_property_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_authority: Any,
    schema_by_id: Mapping[int, Any],
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_investment_property_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("investment-property verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str) -> dict[str, Any]:
    payload = base.support._stable_bytes(path)
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    return base.support._strict_json(payload, path.as_posix())


def _live_inputs() -> tuple[Any, ...]:
    semantic_index = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_investment_property_full_document_scan_v1(semantic_index)
    if structure_scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("live investment-property structure scan identity drifted")
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return (
        semantic_index,
        crop_manifest,
        structure_scan,
        _review_blueprint(),
        schema_authority,
        schema_by_id,
    )


def build_live_investment_property_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_investment_property_8bank_codex_verified_mapping_v1(*_live_inputs())


def validate_live_investment_property_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    return validate_investment_property_8bank_codex_verified_mapping_replay_v1(
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
    result = build_live_investment_property_8bank_codex_verified_mapping_v1()
    if args.write_result:
        _write(RESULT_PATH, result)
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    main()
