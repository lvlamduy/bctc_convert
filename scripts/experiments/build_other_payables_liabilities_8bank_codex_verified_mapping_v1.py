"""Verify other-payables/liabilities rows across the fixed eight-PDF corpus.

The complete-PDF matcher is bank blind.  This bounded review binds each unique
region to visible PDF pixels, fresh VietOCR semantic anchors, the independent
source numeric challenger, exact accounting equations and the live TM schema.
Source rows without an exact schema equivalent remain explicit UNRESOLVED
entries even when their values are already included in a verified source
parent or family total.
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

__all__ = [
    "FORMAT_VERSION",
    "OtherPayablesLiabilities8BankCodexVerifiedMappingV1Error",
    "build_live_other_payables_liabilities_8bank_codex_verified_mapping_v1",
    "build_other_payables_liabilities_8bank_codex_verified_mapping_v1",
    "validate_live_other_payables_liabilities_8bank_codex_verified_mapping_v1",
    "validate_other_payables_liabilities_8bank_codex_verified_mapping_replay_v1",
]

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
    "government_nhnn_support_for_other_payables",
    "build_government_nhnn_liabilities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "other_payables_scan_for_verified_mapping",
    "scan_other_payables_liabilities_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "OTHER_PAYABLES_LIABILITIES_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "OTHER_PAYABLES_LIABILITIES_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "OTHER_PAYABLES_LIABILITIES_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "e0077:result:"
REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "e0077:pixel-review:"
REVIEW_RUN_ID = "E-0077"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_OTHER_PAYABLES_"
    "OWNER_INTERNAL_EXTERNAL_OPTIONAL_CHILD_VISIBLE_PDF_PIXEL_SOURCE_NUMERIC_"
    "CHALLENGER_DASH_ZERO_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_UNMAPPED_SOURCE_"
    "ROWS_RETAINED_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0077-other-payables-liabilities-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0077-other-payables-liabilities-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "oplifdsv1:scan:380813cede8fd9b841e30ef8ced746181b3158744f2963b5516dab9a39130e28"

_REVIEW_CHECKS = (
    "COMPLETE_PDF_UNIQUE_REGION",
    "OWNER_PRECEDES_INTERNAL_AND_EXTERNAL_PAYABLE_BRANCHES",
    "OPTIONAL_EMPLOYEE_TAX_OTHER_RISK_WELFARE_AND_INTERMEDIATE_BRANCHES",
    "CURRENT_AND_COMPARATIVE_PERIOD_AXIS",
    "LOCAL_OR_DOCUMENT_INHERITED_MILLION_VND_UNIT",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "SOURCE_NUMERIC_CHALLENGER_OR_AUTHENTICATED_PIXEL_DASH",
    "SOURCE_PARENT_CHILD_AND_PRINTED_TOTAL_EQUATIONS_RECONCILE",
    "OVERLAPPING_SOURCE_PARENTS_AND_DETAILS_NOT_DOUBLE_COUNTED",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
)
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "dash_visible_in_authenticated_pixels_normalized_to_zero": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_SOURCE_NUMERIC_CHALLENGER_OR_BOUND_DASH_CROP",
    "old_ocr_used_as_semantic_anchor": False,
    "optional_children_required_in_every_bank": False,
    "source_parent_and_detail_double_counted": False,
    "source_rows_without_equivalent_schema_forced_into_nearest_item": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_other_report_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "dash_zero_semantics_require_visible_authenticated_pixel_crop": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_other_payables_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_parent_and_detail_double_counted": False,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_retained": True,
    "upstream_source_text_used_only_as_numeric_challenger": True,
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
_SCHEMA_EXPECTED = {
    1118: ("Các khoản phải trả và công nợ khác", 560, 631),
    1119: ("Các khoản phải trả nội bộ", 1118, 632),
    1120: ("Các khoản phải trả nhân viên", 1118, 633),
    1121: ("Các khoản phải trả nội bộ khác", 1118, 634),
    1122: ("Các khoản phải trả bên ngoài", 1118, 635),
    1123: ("Thuế và các khoản phải nộp Nhà nước", 1118, 636),
    1124: ("Các khoản phải trả khác", 1118, 637),
    1125: ("Dự phòng rủi ro khác", 1118, 638),
    1126: ("Quỹ khen thưởng, phúc lợi", 1118, 639),
    1127: ("Khác", 1118, 640),
}


class OtherPayablesLiabilities8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixel, numeric, accounting or schema evidence drifted."""


def _error(message: str) -> OtherPayablesLiabilities8BankCodexVerifiedMappingV1Error:
    return OtherPayablesLiabilities8BankCodexVerifiedMappingV1Error(message)


def _label(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str, multiplier: int = 1) -> dict[str, Any]:
    return {
        "kind": "AUTHENTICATED_LINE",
        "line_index": line,
        "multiplier": multiplier,
        "page_sequence": page,
        "pixel_transcription": text,
    }


def _dash(page: int, bbox: Sequence[int], pixel_rgb_sha256: str) -> dict[str, Any]:
    return {
        "bbox": list(bbox),
        "kind": "AUTHENTICATED_RENDER_PIXEL_DASH",
        "multiplier": 1,
        "page_sequence": page,
        "pixel_rgb_sha256": pixel_rgb_sha256,
        "pixel_transcription": "-",
    }


def _mapping(
    report_norm_id: int,
    role: str,
    labels: Sequence[dict[str, Any]],
    values: Mapping[str, Sequence[dict[str, Any]]],
    topology: str,
) -> dict[str, Any]:
    return {
        "labels": list(labels),
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {key: list(items) for key, items in values.items()},
    }


def _equation(
    name: str, period_role: str, terms: Sequence[dict[str, Any]], total: dict[str, Any]
) -> dict[str, Any]:
    return {"name": name, "period_role": period_role, "terms": list(terms), "total": total}


def _unmapped(
    item_id: str,
    labels: Sequence[dict[str, Any]],
    values: Mapping[str, Sequence[dict[str, Any]]],
    reason: str,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "labels": list(labels),
        "reason": reason,
        "status": "UNRESOLVED",
        "values": {key: list(items) for key, items in values.items()},
    }


def _doc(
    code: str,
    page: int,
    owner_line: int,
    owner_text: str,
    periods: Sequence[dict[str, Any]],
    units: Sequence[dict[str, Any]],
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[dict[str, Any]],
    unmapped: Sequence[dict[str, Any]] = (),
    *,
    source_period: str = "2026-06-30",
    presentation: str = "OWNER_THEN_FLEXIBLE_CHILD_ROWS_AND_TWO_PERIOD_VALUE_LANES",
    unit_authority: str = "VISIBLE_PAGE_MILLION_VND",
) -> dict[str, Any]:
    return {
        "bank_code": code,
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": (
            "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS" if unmapped else "VERIFIED_BY_CODEX"
        ),
        "equations": list(equations),
        "mappings": list(mappings),
        "owner": _label(page, owner_line, owner_text),
        "page_span": [page, page],
        "period_axis": list(periods),
        "presentation": presentation,
        "source_period": source_period,
        "unit_authority": unit_authority,
        "unit_evidence": list(units),
        "unmapped_source_rows": list(unmapped),
    }


def _two_period_mapping(
    report_norm_id: int,
    role: str,
    page: int,
    label_line: int,
    label_text: str,
    current_line: int,
    current_text: str,
    comparative_line: int,
    comparative_text: str,
    topology: str,
    extra_labels: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    return _mapping(
        report_norm_id,
        role,
        [_label(page, label_line, label_text), *extra_labels],
        {
            "CURRENT": [_line(page, current_line, current_text)],
            "COMPARATIVE": [_line(page, comparative_line, comparative_text)],
        },
        topology,
    )


def _two_period_unmapped(
    item_id: str,
    page: int,
    label_line: int,
    label_text: str,
    current_line: int,
    current_text: str,
    comparative_line: int,
    comparative_text: str,
    reason: str,
    extra_labels: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    return _unmapped(
        item_id,
        [_label(page, label_line, label_text), *extra_labels],
        {
            "CURRENT": [_line(page, current_line, current_text)],
            "COMPARATIVE": [_line(page, comparative_line, comparative_text)],
        },
        reason,
    )


def _root_mapping(
    page: int,
    owner_line: int,
    owner_text: str,
    current: tuple[int, str],
    comparative: tuple[int, str],
) -> dict[str, Any]:
    return _two_period_mapping(
        1118,
        "FAMILY_TOTAL",
        page,
        owner_line,
        owner_text,
        current[0],
        current[1],
        comparative[0],
        comparative[1],
        "PRINTED_TOTAL_AFTER_COMPLETE_SOURCE_FAMILY",
    )


def _review_documents() -> list[dict[str, Any]]:
    acb_risk_current = _dash(
        22,
        [1240, 1478, 1305, 1508],
        "be72f5a32b005a84e71c1aa2dcaf9018f71279d3f7bcebe385a06ce11aa00e04",
    )
    acb_risk_comparative = _dash(
        22,
        [1470, 1478, 1535, 1508],
        "3aaa245677f353050af7dbcddaf76fcf891b6e80a58b44cb683724fd5ac9e25e",
    )
    return [
        _doc(
            "ACB",
            22,
            41,
            "12. CÁC KHOẢN NỢ KHÁC:",
            [_label(22, 42, "30.6.2026"), _label(22, 43, "31.12.2025")],
            [_label(22, 44, "Triệu đồng"), _label(22, 45, "Triệu đồng")],
            [
                _root_mapping(22, 41, "CÁC KHOẢN NỢ KHÁC", (62, "23.520.322"), (63, "24.861.054")),
                _two_period_mapping(
                    1119,
                    "INTERNAL_PAYABLE",
                    22,
                    46,
                    "Các khoản phải trả nội bộ",
                    47,
                    "870.967",
                    48,
                    "941.203",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _two_period_mapping(
                    1122,
                    "EXTERNAL_PAYABLE",
                    22,
                    49,
                    "Các khoản phải trả bên ngoài",
                    50,
                    "14.922.440",
                    51,
                    "15.893.525",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _mapping(
                    1125,
                    "OTHER_RISK_PROVISION",
                    [_label(22, 61, "Dự phòng rủi ro khác")],
                    {"CURRENT": [acb_risk_current], "COMPARATIVE": [acb_risk_comparative]},
                    "VISIBLE_DASH_VALUE_NORMALIZED_TO_ZERO",
                ),
                _two_period_mapping(
                    1126,
                    "WELFARE_FUND",
                    22,
                    55,
                    "Quỹ khen thưởng phúc lợi",
                    56,
                    "900.564",
                    57,
                    "817.424",
                    "DIRECT_CHILD_OF_OWNER",
                ),
            ],
            [
                _equation(
                    "VISIBLE_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        _line(22, 47, "870.967"),
                        _line(22, 50, "14.922.440"),
                        _line(22, 53, "5.384.145"),
                        _line(22, 56, "900.564"),
                        _line(22, 59, "1.442.206"),
                        acb_risk_current,
                    ],
                    _line(22, 62, "23.520.322"),
                ),
                _equation(
                    "VISIBLE_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        _line(22, 48, "941.203"),
                        _line(22, 51, "15.893.525"),
                        _line(22, 54, "5.667.622"),
                        _line(22, 57, "817.424"),
                        _line(22, 60, "1.541.280"),
                        acb_risk_comparative,
                    ],
                    _line(22, 63, "24.861.054"),
                ),
            ],
            [
                _two_period_unmapped(
                    "OPL-001",
                    22,
                    52,
                    "Thu nhập chưa thực hiện",
                    53,
                    "5.384.145",
                    54,
                    "5.667.622",
                    "NO_EXACT_SCHEMA_LEAF; VALUE_REMAINS_INCLUDED_IN_VERIFIED_FAMILY_TOTAL",
                ),
                _two_period_unmapped(
                    "OPL-002",
                    22,
                    58,
                    "Quỹ phát triển khoa học và công nghệ",
                    59,
                    "1.442.206",
                    60,
                    "1.541.280",
                    "NO_EXACT_SCHEMA_LEAF; VALUE_REMAINS_INCLUDED_IN_VERIFIED_FAMILY_TOTAL",
                ),
            ],
        ),
        _doc(
            "MBB",
            44,
            28,
            "Các khoản phải trả và công nợ khác",
            [_label(44, 29, "30/06/2026"), _label(44, 30, "31/12/2025")],
            [_label(44, 31, "Triệu đồng"), _label(44, 32, "Triệu đồng")],
            [
                _root_mapping(
                    44,
                    28,
                    "Các khoản phải trả và công nợ khác",
                    (39, "48.645.739"),
                    (40, "51.785.481"),
                ),
                _two_period_mapping(
                    1119,
                    "INTERNAL_PAYABLE",
                    44,
                    33,
                    "Các khoản phải trả nội bộ",
                    34,
                    "7.143.121",
                    35,
                    "5.413.942",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _two_period_mapping(
                    1122,
                    "EXTERNAL_PAYABLE",
                    44,
                    36,
                    "Các khoản phải trả bên ngoài",
                    37,
                    "41.502.618",
                    38,
                    "46.371.539",
                    "DIRECT_CHILD_OF_OWNER",
                ),
            ],
            [
                _equation(
                    "INTERNAL_PLUS_EXTERNAL_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [_line(44, 34, "7.143.121"), _line(44, 37, "41.502.618")],
                    _line(44, 39, "48.645.739"),
                ),
                _equation(
                    "INTERNAL_PLUS_EXTERNAL_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [_line(44, 35, "5.413.942"), _line(44, 38, "46.371.539")],
                    _line(44, 40, "51.785.481"),
                ),
            ],
        ),
        _doc(
            "VPB",
            57,
            41,
            "23.2 Các khoản phải trả và công nợ khác",
            [
                _label(57, 42, "Ngày 31 tháng 3"),
                _label(57, 44, "năm 2026"),
                _label(57, 43, "Ngày 31 tháng 12"),
                _label(57, 45, "năm 2025"),
            ],
            [_label(57, 46, "Triệu đồng"), _label(57, 47, "Triệu đồng")],
            [
                _root_mapping(
                    57,
                    41,
                    "Các khoản phải trả và công nợ khác",
                    (88, "32.967.238"),
                    (89, "33.454.600"),
                ),
                _two_period_mapping(
                    1119,
                    "INTERNAL_PAYABLE",
                    57,
                    48,
                    "Các khoản phải trả nội bộ",
                    49,
                    "289.628",
                    50,
                    "1.467.547",
                    "SOURCE_PARENT_EQUAL_TO_ITS_EMPLOYEE_CHILD",
                ),
                _two_period_mapping(
                    1120,
                    "EMPLOYEE_PAYABLE",
                    57,
                    51,
                    "Phải trả nhân viên",
                    52,
                    "289.628",
                    53,
                    "1.467.547",
                    "ONLY_CHILD_OF_INTERNAL_PAYABLE_PARENT",
                ),
                _two_period_mapping(
                    1122,
                    "EXTERNAL_PAYABLE",
                    57,
                    54,
                    "Các khoản phải trả bên ngoài",
                    55,
                    "32.677.610",
                    56,
                    "31.987.053",
                    "SOURCE_PARENT_WITH_OPTIONAL_DETAIL_ROWS; DETAILS_NOT_ADDED_AGAIN_TO_ROOT",
                ),
                _two_period_mapping(
                    1123,
                    "TAX_PAYABLE",
                    57,
                    69,
                    "Thuế và các khoản phải trả ngân sách Nhà nước",
                    71,
                    "1.645.470",
                    72,
                    "4.712.152",
                    "DETAIL_WITHIN_SOURCE_EXTERNAL_PARENT",
                    [_label(57, 70, "minh số 24")],
                ),
                _two_period_mapping(
                    1124,
                    "OTHER_PAYABLE",
                    57,
                    85,
                    "Các khoản phải trả khác",
                    86,
                    "3.633.927",
                    87,
                    "2.780.153",
                    "DETAIL_WITHIN_SOURCE_EXTERNAL_PARENT",
                ),
            ],
            [
                _equation(
                    "EMPLOYEE_TO_INTERNAL_PARENT",
                    "CURRENT",
                    [_line(57, 52, "289.628")],
                    _line(57, 49, "289.628"),
                ),
                _equation(
                    "EMPLOYEE_TO_INTERNAL_PARENT",
                    "COMPARATIVE",
                    [_line(57, 53, "1.467.547")],
                    _line(57, 50, "1.467.547"),
                ),
                _equation(
                    "EXTERNAL_DETAIL_TO_EXTERNAL_PARENT",
                    "CURRENT",
                    [
                        _line(57, 58, "1.290.178"),
                        _line(57, 61, "1.530.742"),
                        _line(57, 64, "2.638.696"),
                        _line(57, 67, "940.785"),
                        _line(57, 71, "1.645.470"),
                        _line(57, 74, "1.915.520"),
                        _line(57, 77, "38.298"),
                        _line(57, 80, "17.036.991"),
                        _line(57, 83, "2.007.003"),
                        _line(57, 86, "3.633.927"),
                    ],
                    _line(57, 55, "32.677.610"),
                ),
                _equation(
                    "EXTERNAL_DETAIL_TO_EXTERNAL_PARENT",
                    "COMPARATIVE",
                    [
                        _line(57, 59, "1.275.354"),
                        _line(57, 62, "1.316.346"),
                        _line(57, 65, "2.538.021"),
                        _line(57, 68, "531.714"),
                        _line(57, 72, "4.712.152"),
                        _line(57, 75, "3.359.249"),
                        _line(57, 78, "19.000"),
                        _line(57, 81, "14.582.889"),
                        _line(57, 84, "872.175"),
                        _line(57, 87, "2.780.153"),
                    ],
                    _line(57, 56, "31.987.053"),
                ),
                _equation(
                    "INTERNAL_PLUS_EXTERNAL_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [_line(57, 49, "289.628"), _line(57, 55, "32.677.610")],
                    _line(57, 88, "32.967.238"),
                ),
                _equation(
                    "INTERNAL_PLUS_EXTERNAL_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [_line(57, 50, "1.467.547"), _line(57, 56, "31.987.053")],
                    _line(57, 89, "33.454.600"),
                ),
            ],
            [
                _two_period_unmapped(
                    "OPL-003",
                    57,
                    57,
                    "Các khoản khách hàng trả trước",
                    58,
                    "1.290.178",
                    59,
                    "1.275.354",
                    "NO_EXACT_SCHEMA_LEAF; INCLUDED_ONLY_IN_SOURCE_EXTERNAL_PARENT",
                ),
                _two_period_unmapped(
                    "OPL-004",
                    57,
                    60,
                    "Doanh thu chờ phân bổ",
                    61,
                    "1.530.742",
                    62,
                    "1.316.346",
                    "NO_EXACT_SCHEMA_LEAF; INCLUDED_ONLY_IN_SOURCE_EXTERNAL_PARENT",
                ),
                _two_period_unmapped(
                    "OPL-005",
                    57,
                    63,
                    "Dự phòng nghiệp vụ bảo hiểm",
                    64,
                    "2.638.696",
                    65,
                    "2.538.021",
                    "INSURANCE_PROVISION_IS_NOT_OTHER_RISK_PROVISION; INCLUDED_ONLY_IN_SOURCE_EXTERNAL_PARENT",
                ),
                _two_period_unmapped(
                    "OPL-006",
                    57,
                    66,
                    "Các khoản treo chờ chuyển tiền",
                    67,
                    "940.785",
                    68,
                    "531.714",
                    "NO_EXACT_SCHEMA_LEAF; INCLUDED_ONLY_IN_SOURCE_EXTERNAL_PARENT",
                ),
                _two_period_unmapped(
                    "OPL-007",
                    57,
                    73,
                    "Phải trả hoạt động thanh toán thẻ",
                    74,
                    "1.915.520",
                    75,
                    "3.359.249",
                    "NO_EXACT_SCHEMA_LEAF; INCLUDED_ONLY_IN_SOURCE_EXTERNAL_PARENT",
                ),
                _two_period_unmapped(
                    "OPL-008",
                    57,
                    76,
                    "Phải trả nhà cung cấp",
                    77,
                    "38.298",
                    78,
                    "19.000",
                    "NO_EXACT_SCHEMA_LEAF; INCLUDED_ONLY_IN_SOURCE_EXTERNAL_PARENT",
                ),
                _two_period_unmapped(
                    "OPL-009",
                    57,
                    79,
                    "Phải trả các khoản vay khách hàng của VPBankS",
                    80,
                    "17.036.991",
                    81,
                    "14.582.889",
                    "BANKS_SUBSIDIARY_CUSTOMER_LOAN_PAYABLE_HAS_NO_EXACT_SCHEMA_LEAF",
                ),
                _two_period_unmapped(
                    "OPL-010",
                    57,
                    82,
                    "Tiền giữ hộ và đợi thanh toán",
                    83,
                    "2.007.003",
                    84,
                    "872.175",
                    "NO_EXACT_SCHEMA_LEAF; INCLUDED_ONLY_IN_SOURCE_EXTERNAL_PARENT",
                ),
            ],
            source_period="2026-03-31",
            presentation="BROAD_OTHER_LIABILITIES_OWNER_THEN_NESTED_EXACT_FAMILY_WITH_EXTERNAL_DETAIL_ROWS",
        ),
        _doc(
            "HDB",
            31,
            89,
            "11. Các khoản nợ khác",
            [_label(31, 90, "Số cuối kỳ"), _label(31, 91, "Số đầu kỳ")],
            [_label(31, 92, "Triệu VND"), _label(31, 93, "Triệu VND")],
            [
                _root_mapping(
                    31, 89, "Các khoản nợ khác", (103, "22.772.095"), (104, "21.314.230")
                ),
                _two_period_mapping(
                    1119,
                    "INTERNAL_PAYABLE",
                    31,
                    94,
                    "Các khoản phải trả nội bộ",
                    95,
                    "506.245",
                    96,
                    "1.003.098",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _two_period_mapping(
                    1122,
                    "EXTERNAL_PAYABLE",
                    31,
                    97,
                    "Các khoản phải trả cho bên ngoài",
                    98,
                    "22.178.895",
                    99,
                    "20.249.179",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _two_period_mapping(
                    1126,
                    "WELFARE_FUND",
                    31,
                    100,
                    "Quỹ khen thưởng, phúc lợi",
                    101,
                    "86.955",
                    102,
                    "61.953",
                    "DIRECT_CHILD_OF_OWNER",
                ),
            ],
            [
                _equation(
                    "VISIBLE_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        _line(31, 95, "506.245"),
                        _line(31, 98, "22.178.895"),
                        _line(31, 101, "86.955"),
                    ],
                    _line(31, 103, "22.772.095"),
                ),
                _equation(
                    "VISIBLE_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        _line(31, 96, "1.003.098"),
                        _line(31, 99, "20.249.179"),
                        _line(31, 102, "61.953"),
                    ],
                    _line(31, 104, "21.314.230"),
                ),
            ],
        ),
        _doc(
            "VCB",
            35,
            79,
            "13. Các khoản phải trả và công nợ khác",
            [_label(35, 80, "30/6/2026"), _label(35, 81, "31/12/2025")],
            [_label(35, 82, "Triệu VND"), _label(35, 83, "Triệu VND")],
            [
                _root_mapping(
                    35,
                    79,
                    "Các khoản phải trả và công nợ khác",
                    (94, "23.180.379"),
                    (95, "21.339.972"),
                ),
                _two_period_mapping(
                    1119,
                    "INTERNAL_PAYABLE",
                    35,
                    85,
                    "Các khoản phải trả nội bộ",
                    86,
                    "6.911.495",
                    87,
                    "5.618.852",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _two_period_mapping(
                    1122,
                    "EXTERNAL_PAYABLE",
                    35,
                    88,
                    "Các khoản phải trả bên ngoài",
                    89,
                    "12.658.858",
                    90,
                    "10.489.441",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _two_period_mapping(
                    1126,
                    "WELFARE_FUND",
                    35,
                    91,
                    "Quỹ khen thưởng, phúc lợi",
                    92,
                    "3.610.026",
                    93,
                    "5.231.679",
                    "DIRECT_CHILD_OF_OWNER",
                ),
            ],
            [
                _equation(
                    "VISIBLE_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        _line(35, 86, "6.911.495"),
                        _line(35, 89, "12.658.858"),
                        _line(35, 92, "3.610.026"),
                    ],
                    _line(35, 94, "23.180.379"),
                ),
                _equation(
                    "VISIBLE_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        _line(35, 87, "5.618.852"),
                        _line(35, 90, "10.489.441"),
                        _line(35, 93, "5.231.679"),
                    ],
                    _line(35, 95, "21.339.972"),
                ),
            ],
        ),
        _doc(
            "CTG",
            43,
            4,
            "11. CÁC KHOẢN NỢ KHÁC",
            [_label(43, 5, "30/06/2026"), _label(43, 6, "31/12/2025")],
            [_label(43, 7, "triệu đồng"), _label(43, 8, "triệu đồng")],
            [
                _root_mapping(43, 4, "CÁC KHOẢN NỢ KHÁC", (32, "58.757.716"), (33, "55.851.516")),
                _two_period_mapping(
                    1119,
                    "INTERNAL_PAYABLE",
                    43,
                    15,
                    "Các khoản phải trả nội bộ",
                    16,
                    "4.012.344",
                    17,
                    "6.033.105",
                    "CHILD_OF_SOURCE_PAYABLE_SUBTOTAL",
                ),
                _two_period_mapping(
                    1122,
                    "EXTERNAL_PAYABLE",
                    43,
                    18,
                    "Các khoản phải trả bên ngoài",
                    19,
                    "19.109.862",
                    20,
                    "17.129.874",
                    "CHILD_OF_SOURCE_PAYABLE_SUBTOTAL",
                ),
                _two_period_mapping(
                    1125,
                    "OTHER_RISK_PROVISION",
                    43,
                    21,
                    "Dự phòng rủi ro khác",
                    22,
                    "2.575.679",
                    23,
                    "2.844.970",
                    "SOURCE_PARENT_CORROBORATED_BY_NON_ADDITIVE_DETAIL",
                    [
                        _label(43, 24, "Dự phòng rủi ro khác (dự phòng rủi ro"),
                        _label(43, 25, "hoạt động, ... không bao gồm dự phòng khác"),
                        _label(43, 28, "đối với tài sản có nội bảng"),
                    ],
                ),
                _two_period_mapping(
                    1126,
                    "WELFARE_FUND",
                    43,
                    29,
                    "Quỹ khen thưởng, phúc lợi",
                    30,
                    "1.934.411",
                    31,
                    "3.183.018",
                    "DIRECT_CHILD_OF_OWNER",
                ),
            ],
            [
                _equation(
                    "INTERNAL_PLUS_EXTERNAL_TO_PAYABLE_SUBTOTAL",
                    "CURRENT",
                    [_line(43, 16, "4.012.344"), _line(43, 19, "19.109.862")],
                    _line(43, 13, "23.122.206"),
                ),
                _equation(
                    "INTERNAL_PLUS_EXTERNAL_TO_PAYABLE_SUBTOTAL",
                    "COMPARATIVE",
                    [_line(43, 17, "6.033.105"), _line(43, 20, "17.129.874")],
                    _line(43, 14, "23.162.979"),
                ),
                _equation(
                    "RISK_DETAIL_EQUALS_NON_ADDITIVE_PARENT",
                    "CURRENT",
                    [_line(43, 26, "2.575.679")],
                    _line(43, 22, "2.575.679"),
                ),
                _equation(
                    "RISK_DETAIL_EQUALS_NON_ADDITIVE_PARENT",
                    "COMPARATIVE",
                    [_line(43, 27, "2.844.970")],
                    _line(43, 23, "2.844.970"),
                ),
                _equation(
                    "VISIBLE_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        _line(43, 10, "31.125.420"),
                        _line(43, 13, "23.122.206"),
                        _line(43, 22, "2.575.679"),
                        _line(43, 30, "1.934.411"),
                    ],
                    _line(43, 32, "58.757.716"),
                ),
                _equation(
                    "VISIBLE_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        _line(43, 11, "26.660.549"),
                        _line(43, 14, "23.162.979"),
                        _line(43, 23, "2.844.970"),
                        _line(43, 31, "3.183.018"),
                    ],
                    _line(43, 33, "55.851.516"),
                ),
            ],
            [
                _two_period_unmapped(
                    "OPL-011",
                    43,
                    9,
                    "Các khoản lãi, phí phải trả",
                    10,
                    "31.125.420",
                    11,
                    "26.660.549",
                    "NO_EXACT_SCHEMA_LEAF; VALUE_REMAINS_INCLUDED_IN_VERIFIED_FAMILY_TOTAL",
                ),
            ],
        ),
        _doc(
            "BID",
            26,
            5,
            "11. CÁC KHOẢN PHẢI TRẢ VÀ CÔNG NỢ KHÁC",
            [_label(26, 6, "30/06/2026"), _label(26, 7, "31/12/2025")],
            [],
            [
                _root_mapping(
                    26,
                    5,
                    "CÁC KHOẢN PHẢI TRẢ VÀ CÔNG NỢ KHÁC",
                    (17, "18,849,797"),
                    (18, "25,940,546"),
                ),
                _two_period_mapping(
                    1119,
                    "INTERNAL_PAYABLE",
                    26,
                    8,
                    "Các khoản phải trả nội bộ",
                    9,
                    "3,384,326",
                    10,
                    "6,860,518",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _two_period_mapping(
                    1122,
                    "EXTERNAL_PAYABLE",
                    26,
                    11,
                    "Các khoản phải trả bên ngoài",
                    12,
                    "14,466,739",
                    13,
                    "16,019,587",
                    "DIRECT_CHILD_OF_OWNER",
                ),
                _two_period_mapping(
                    1126,
                    "WELFARE_FUND",
                    26,
                    14,
                    "Quỹ khen thưởng phúc lợi",
                    15,
                    "998,732",
                    16,
                    "3,060,441",
                    "DIRECT_CHILD_OF_OWNER",
                ),
            ],
            [
                _equation(
                    "VISIBLE_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        _line(26, 9, "3,384,326"),
                        _line(26, 12, "14,466,739"),
                        _line(26, 15, "998,732"),
                    ],
                    _line(26, 17, "18,849,797"),
                ),
                _equation(
                    "VISIBLE_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        _line(26, 10, "6,860,518"),
                        _line(26, 13, "16,019,587"),
                        _line(26, 16, "3,060,441"),
                    ],
                    _line(26, 18, "25,940,546"),
                ),
            ],
            unit_authority="DOCUMENT_LEVEL_MILLION_VND_INHERITANCE",
        ),
        _doc(
            "VIB",
            43,
            29,
            "22. CÁC KHOẢN NỢ KHÁC",
            [_label(43, 30, "30/06/2026"), _label(43, 31, "31/12/2025")],
            [_label(43, 32, "triệu đồng"), _label(43, 33, "triệu đồng")],
            [
                _root_mapping(43, 29, "CÁC KHOẢN NỢ KHÁC", (76, "10.302.946"), (77, "10.946.659")),
                _two_period_mapping(
                    1119,
                    "INTERNAL_PAYABLE",
                    43,
                    37,
                    "Các khoản phải trả nội bộ",
                    38,
                    "453.874",
                    39,
                    "431.458",
                    "SOURCE_PARENT_WITH_OPTIONAL_DETAIL_ROWS",
                ),
                _two_period_mapping(
                    1120,
                    "EMPLOYEE_PAYABLE",
                    43,
                    40,
                    "Phải trả cán bộ, nhân viên",
                    41,
                    "128.268",
                    42,
                    "233.527",
                    "DETAIL_WITHIN_SOURCE_INTERNAL_PARENT",
                ),
                _two_period_mapping(
                    1121,
                    "INTERNAL_OTHER",
                    43,
                    49,
                    "Phải trả nội bộ khác",
                    50,
                    "53.309",
                    51,
                    "32.390",
                    "DETAIL_WITHIN_SOURCE_INTERNAL_PARENT",
                ),
                _two_period_mapping(
                    1122,
                    "EXTERNAL_PAYABLE",
                    43,
                    52,
                    "Các khoản phải trả bên ngoài",
                    53,
                    "2.944.023",
                    54,
                    "6.162.377",
                    "SOURCE_PARENT_WITH_OPTIONAL_DETAIL_ROWS",
                ),
                _two_period_mapping(
                    1123,
                    "TAX_PAYABLE",
                    43,
                    55,
                    "Thuế và các khoản phải nộp Nhà nước",
                    56,
                    "996.062",
                    57,
                    "1.289.606",
                    "DETAIL_WITHIN_SOURCE_EXTERNAL_PARENT",
                ),
                _two_period_mapping(
                    1124,
                    "OTHER_PAYABLE",
                    43,
                    70,
                    "Các khoản phải trả khác",
                    71,
                    "474.026",
                    72,
                    "241.951",
                    "DETAIL_WITHIN_SOURCE_EXTERNAL_PARENT",
                ),
                _two_period_mapping(
                    1126,
                    "WELFARE_FUND",
                    43,
                    43,
                    "Quỹ khen thưởng, phúc lợi",
                    44,
                    "152.225",
                    45,
                    "158.925",
                    "DETAIL_WITHIN_SOURCE_INTERNAL_PARENT",
                ),
            ],
            [
                _equation(
                    "INTERNAL_DETAIL_TO_INTERNAL_PARENT",
                    "CURRENT",
                    [
                        _line(43, 41, "128.268"),
                        _line(43, 44, "152.225"),
                        _line(43, 47, "120.072"),
                        _line(43, 50, "53.309"),
                    ],
                    _line(43, 38, "453.874"),
                ),
                _equation(
                    "INTERNAL_DETAIL_TO_INTERNAL_PARENT",
                    "COMPARATIVE",
                    [
                        _line(43, 42, "233.527"),
                        _line(43, 45, "158.925"),
                        _line(43, 48, "6.616"),
                        _line(43, 51, "32.390"),
                    ],
                    _line(43, 39, "431.458"),
                ),
                _equation(
                    "EXTERNAL_DETAIL_TO_EXTERNAL_PARENT",
                    "CURRENT",
                    [
                        _line(43, 56, "996.062"),
                        _line(43, 59, "35.918"),
                        _line(43, 62, "191.546"),
                        _line(43, 65, "652.161"),
                        _line(43, 68, "594.310"),
                        _line(43, 71, "474.026"),
                    ],
                    _line(43, 53, "2.944.023"),
                ),
                _equation(
                    "EXTERNAL_DETAIL_TO_EXTERNAL_PARENT",
                    "COMPARATIVE",
                    [
                        _line(43, 57, "1.289.606"),
                        _line(43, 60, "20.875"),
                        _line(43, 63, "620.546"),
                        _line(43, 66, "248.948"),
                        _line(43, 69, "3.740.451"),
                        _line(43, 72, "241.951"),
                    ],
                    _line(43, 54, "6.162.377"),
                ),
                _equation(
                    "INTEREST_INTERNAL_EXTERNAL_UNEARNED_TO_TOTAL",
                    "CURRENT",
                    [
                        _line(43, 35, "6.886.558"),
                        _line(43, 38, "453.874"),
                        _line(43, 53, "2.944.023"),
                        _line(43, 74, "18.491"),
                    ],
                    _line(43, 76, "10.302.946"),
                ),
                _equation(
                    "INTEREST_INTERNAL_EXTERNAL_UNEARNED_TO_TOTAL",
                    "COMPARATIVE",
                    [
                        _line(43, 36, "4.298.773"),
                        _line(43, 39, "431.458"),
                        _line(43, 54, "6.162.377"),
                        _line(43, 75, "54.051"),
                    ],
                    _line(43, 77, "10.946.659"),
                ),
            ],
            [
                _two_period_unmapped(
                    "OPL-012",
                    43,
                    34,
                    "Các khoản lãi, phí phải trả",
                    35,
                    "6.886.558",
                    36,
                    "4.298.773",
                    "NO_EXACT_SCHEMA_LEAF; VALUE_REMAINS_INCLUDED_IN_VERIFIED_FAMILY_TOTAL",
                ),
                _two_period_unmapped(
                    "OPL-013",
                    43,
                    46,
                    "Phải trả cổ tức cho cổ đông",
                    47,
                    "120.072",
                    48,
                    "6.616",
                    "NO_EXACT_SCHEMA_LEAF; INCLUDED_ONLY_IN_SOURCE_INTERNAL_PARENT",
                ),
                _two_period_unmapped(
                    "OPL-014",
                    43,
                    58,
                    "Tiền giữ hộ và đợi thanh toán",
                    59,
                    "35.918",
                    60,
                    "20.875",
                    "NO_EXACT_SCHEMA_LEAF; INCLUDED_ONLY_IN_SOURCE_EXTERNAL_PARENT",
                ),
                _two_period_unmapped(
                    "OPL-015",
                    43,
                    61,
                    "Phải trả thanh toán giữa các TCTD",
                    62,
                    "191.546",
                    63,
                    "620.546",
                    "NO_EXACT_SCHEMA_LEAF; INCLUDED_ONLY_IN_SOURCE_EXTERNAL_PARENT",
                ),
                _two_period_unmapped(
                    "OPL-016",
                    43,
                    64,
                    "Phải trả chuyển tiền chờ thanh toán",
                    65,
                    "652.161",
                    66,
                    "248.948",
                    "NO_EXACT_SCHEMA_LEAF; INCLUDED_ONLY_IN_SOURCE_EXTERNAL_PARENT",
                ),
                _two_period_unmapped(
                    "OPL-017",
                    43,
                    67,
                    "Các khoản chờ thanh toán khác",
                    68,
                    "594.310",
                    69,
                    "3.740.451",
                    "NO_EXACT_SCHEMA_LEAF; INCLUDED_ONLY_IN_SOURCE_EXTERNAL_PARENT",
                ),
                _two_period_unmapped(
                    "OPL-018",
                    43,
                    73,
                    "Doanh thu chờ phân bổ",
                    74,
                    "18.491",
                    75,
                    "54.051",
                    "NO_EXACT_SCHEMA_LEAF; VALUE_REMAINS_INCLUDED_IN_VERIFIED_FAMILY_TOTAL",
                ),
            ],
            presentation="BROAD_OWNER_WITH_INTEREST_INTERNAL_AND_EXTERNAL_PARENTS_AND_NESTED_DETAIL_ROWS",
        ),
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
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
        raise _error("Codex other-payables pixel review differs from the fixed ledger")
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


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "authenticated_pixel_dash_zero_count": sum(
            component["source_numeric_challenger_status"]
            == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
            for component in value["components"]
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["complete_region_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": sum(len(trial["unmapped_source_rows"]) for trial in trials),
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "verified_value_cell_count": sum(
            len(value["components"])
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
    }


def _source_period_status(source_period: str) -> str:
    if source_period == "2026-03-31":
        return "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
    if source_period == "2026-06-30":
        return "VERIFIED_SOURCE_PERIOD_Q2_2026"
    raise _error("reviewed other-payables source period is not admitted")


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("other-payables result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("other-payables result identity or metrics drifted")
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
            }
            or any(
                row.get("status") != "VERIFIED_BY_CODEX"
                for row in trial.get("verified_mappings", [])
            )
            or any(
                row.get("status") != "UNRESOLVED" for row in trial.get("unmapped_source_rows", [])
            )
        ):
            raise _error("other-payables trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("other-payables result identity drifted")
    return canonical_clone_v1(value)


def build_other_payables_liabilities_8bank_codex_verified_mapping_v1(
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
    """Build the exact eight-bank bounded other-payables mapping result."""

    reviewed_documents = _review(review)["documents"]
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or structure_scan.get("state") != "FULL_DOCUMENT_OTHER_PAYABLES_LIABILITIES_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("fixed semantic axis, crop manifest or structure scan identity drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(reviewed_documents, code, "pixel review")
        scan_trial = _document(structure_scan["trials"], code, "structure scan")
        axis_document = _document(axis["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        matcher = scan_trial["matcher_result"]
        if (
            not same_typed_json_v1(
                matcher["uniqueness"],
                {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"},
            )
            or matcher["regions"][0]["owner"]["page_sequence"] != reviewed["owner"]["page_sequence"]
            or matcher["regions"][0]["owner"]["source_line_index"]
            != reviewed["owner"]["line_index"]
            or not same_typed_json_v1(matcher["regions"][0]["page_span"], reviewed["page_span"])
        ):
            raise _error("reviewed region is not the unique whole-PDF other-payables graph")
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
        ) -> dict[str, Any]:
            key = canonical_json_sha256_v1(ref)
            if key not in value_cache:
                axis_page, semantic_page, crop_page, source_texts = context(ref["page_sequence"])
                if ref["kind"] == "AUTHENTICATED_LINE":
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
                elif ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH":
                    value_cache[key] = {
                        **foundation._pixel_dash_value(crop_page, ref),
                        "page_sequence": ref["page_sequence"],
                    }
                else:
                    raise _error("reviewed numeric evidence kind drifted")
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
            for period_role in ("CURRENT", "COMPARATIVE"):
                components = [verified(item) for item in mapping["values"][period_role]]
                values.append(
                    {
                        "aggregation": "DIRECT_VISIBLE_VALUE"
                        if len(components) == 1
                        else "SUM_OF_VISIBLE_SOURCE_ROWS",
                        "components": components,
                        "normalized_value": sum(item["normalized_value"] for item in components),
                        "period_role": period_role,
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
            if computed != total["normalized_value"]:
                raise _error(
                    f"other-payables accounting equation does not close: {equation['name']}"
                )
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "period_role": equation["period_role"],
                    "status": "VERIFIED_EXACT",
                    "terms": terms,
                    "visible_total": total["normalized_value"],
                    "visible_total_page_sequence": equation["total"]["page_sequence"],
                    "visible_total_source_line_index": total["source_line_index"],
                }
            )
        unmapped_rows = []
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
            unmapped_rows.append(
                {
                    "item_id": row["item_id"],
                    "label_evidence": labels,
                    "reason": row["reason"],
                    "status": "UNRESOLVED",
                    "values": [
                        {
                            "components": [verified(ref) for ref in row["values"][period_role]],
                            "period_role": period_role,
                        }
                        for period_role in ("CURRENT", "COMPARATIVE")
                    ],
                }
            )
        owner_page, owner_semantic_page, _, _ = context(reviewed["owner"]["page_sequence"])
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
        if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2":
            status = "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
        trials.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "owner_evidence": _semantic_evidence(
                    owner_page, owner_semantic_page, reviewed["owner"]
                ),
                "page_span": reviewed["page_span"],
                "period_axis_evidence": period_evidence,
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "status": status,
                "structure_graph_id": matcher["result_id"],
                "unit_authority": reviewed["unit_authority"],
                "unit_evidence": unit_evidence,
                "unmapped_source_rows": unmapped_rows,
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )
    schema_family = {
        "family_end_display_order": max(
            _schema_binding(schema_by_id.get(item), item)["display_order"]
            for item in _SCHEMA_EXPECTED
        ),
        "family_root": _schema_binding(schema_by_id.get(1118), 1118),
        "mapped_report_norm_ids": sorted(
            {
                mapping["schema_binding"]["report_norm_id"]
                for trial in trials
                for mapping in trial["verified_mappings"]
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
        },
        "metrics": _metrics(trials),
        "schema_family": schema_family,
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_other_payables_liabilities_8bank_codex_verified_mapping_replay_v1(
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
    rebuilt = build_other_payables_liabilities_8bank_codex_verified_mapping_v1(
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
        raise _error("other-payables verified mapping does not replay exactly")
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


def build_live_other_payables_liabilities_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_other_payables_liabilities_full_document_scan_v1(semantic_index)
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_other_payables_liabilities_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_other_payables_liabilities_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_other_payables_liabilities_full_document_scan_v1(semantic_index)
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_other_payables_liabilities_8bank_codex_verified_mapping_replay_v1(
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
        _write(RESULT_PATH, build_live_other_payables_liabilities_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        value, _ = _stable_json(RESULT_PATH)
        validate_live_other_payables_liabilities_8bank_codex_verified_mapping_v1(value)
    if not (args.write_review or args.write_result or args.validate_result):
        raise SystemExit("choose --write-review, --write-result or --validate-result")


if __name__ == "__main__":
    main()
