"""Verify detailed other-activity income, expense, and net notes."""

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
        raise RuntimeError(f"cannot load other-activity support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


operating = _load(
    "operating_expense_support_for_other_activity",
    "build_operating_expense_8bank_codex_verified_mapping_v1.py",
)
movement = _load(
    "provision_movement_support_for_other_activity",
    "build_provision_movement_8bank_codex_verified_mapping_v1.py",
)
scanner = _load(
    "other_activity_scan_for_verified_mapping",
    "scan_other_activity_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "OTHER_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "OTHER_ACTIVITY_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "OTHER_ACTIVITY_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "e0090:result:"
REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "e0090:pixel-review:"
REVIEW_RUN_ID = "E-0090"
ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = True
SCHEMA_FAMILY_END_DISPLAY_ORDER = 807
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_DETAILED_"
    "OTHER_ACTIVITY_GRAPH_VISIBLE_PDF_PADDLEOCR_OR_NATIVE_"
    "NUMERIC_CHALLENGER_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_"
    "UNMAPPED_SOURCE_ROWS_RETAINED_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0090-other-activity-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0090-other-activity-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = operating.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = operating.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = operating.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "oafdsv1:scan:b4afc265d586e05728eab9cd1f42c3185650939259e8ff0845b921fae455e2e4"
EXPECTED_RESULT_ID = "e0090:result:85652f29f00e2db0b2030057a3e1478a91082adc31021e70ef638684412a321e"

_SCHEMA_EXPECTED = {
    1142: (
        "II. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG KẾT QUẢ KINH DOANH",
        None,
        684,
    ),
    6029: ("Lãi thuần từ hoạt động kinh doanh khác", 1142, 788),
    6030: ("Thu nhập/(Chi phí) khác", 6029, 789),
    1229: ("Thu nhập từ hoạt động khác", 1142, 790),
    1230: ("Nợ xấu đã được xử lý", 1229, 791),
    1231: ("Chuyển nhượng, thanh lý tài sản", 1229, 792),
    1232: ("Công cụ phái sinh khác", 1229, 793),
    1233: ("Thanh lý Quyền sử dụng đất và TSCĐ khác", 1229, 794),
    1234: ("Thu hồi nợ xấu,nợ đã xử lý, nợ đã xóa sổ trước đây", 1229, 795),
    1235: ("Thu từ hoạt động kinh doanh bất động sản", 1229, 796),
    1236: ("Thu từ hoạt động ủy thác", 1229, 797),
    1237: ("Thu từ nghiệp vụ mua bán nợ", 1229, 798),
    1238: ("Hoàn nhập dự phòng", 1229, 799),
    1239: ("Khác", 1229, 800),
    1240: ("Chi phí từ hoạt động khác", 1142, 801),
    1241: ("Công cụ phái sinh khác", 1240, 802),
    1242: ("Chuyển nhượng, thanh lý tài sản", 1240, 803),
    1243: ("Chi từ nghiệp vụ mua bán nợ", 1240, 804),
    1244: ("Chi công tác xã hội", 1240, 805),
    1245: ("Chi phí thu hồi nợ", 1240, 806),
    1246: ("Khác", 1240, 807),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "dash_zero_policy_applied_only_to_visible_dash": True,
    "detailed_note_absence_bounded_to_bound_report": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_other_activity_rows": True,
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
    "only_visible_dash_interpreted_as_zero": True,
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


class OtherActivity8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, numbers, equation, or schema evidence drifted."""


def _error(message: str) -> OtherActivity8BankCodexVerifiedMappingV1Error:
    return OtherActivity8BankCodexVerifiedMappingV1Error(message)


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
    current: Mapping[str, Any],
    comparative: Mapping[str, Any],
    topology: str = "DIRECT_OR_WRAPPED_LABEL_TWO_PERIOD_LANES",
) -> dict[str, Any]:
    return {
        "labels": [_ref(page, line, text) for line, text in labels],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {
            "COMPARATIVE_PERIOD": canonical_clone_v1(comparative),
            "CURRENT_PERIOD": canonical_clone_v1(current),
        },
    }


def _source_only(
    row_id: str,
    role: str,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: Mapping[str, Any],
    comparative: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "labels": [_ref(page, line, text) for line, text in labels],
        "reason": reason,
        "role": role,
        "row_id": row_id,
        "values": {
            "COMPARATIVE_PERIOD": canonical_clone_v1(comparative),
            "CURRENT_PERIOD": canonical_clone_v1(current),
        },
    }


def _equation(name: str, parent: str, terms: Sequence[str]) -> dict[str, Any]:
    return {"name": name, "parent_role": parent, "term_roles": list(terms)}


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_note_complete_region_count": 0,
            "reason": (
                "No Arabic-numbered detailed other-activity note with period/unit axes, "
                "either gross income/expense children or net-only components, and a trailing "
                "net total was found in the bound report; statement aggregates, segment "
                "reports, and policy text do not qualify."
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
        "presentation": "NO_DETAILED_OTHER_ACTIVITY_NOTE_IN_BOUND_REPORT",
        "source_only_rows": [],
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    documents = [_absence("ACB")]

    page = 47
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "MBB",
            "equations": [
                _equation(
                    "NET_COMPONENTS_EQUAL_TRAILING_NET_TOTAL",
                    "TOTAL",
                    ["DEBT_RECOVERY", "NET_DERIVATIVE", "NET_OTHER"],
                )
            ],
            "graph_roles": ["DEBT_RECOVERY", "NET_DERIVATIVE", "NET_OTHER"],
            "mappings": [
                _mapping(
                    "TOTAL",
                    6029,
                    page,
                    [(72, "Lãi thuần từ hoạt động kinh doanh khác")],
                    _line(page, 88, "2.160.309"),
                    _line(page, 89, "2.543.007"),
                    "TRAILING_UNLABELED_NET_TOTAL",
                ),
                _mapping(
                    "DEBT_RECOVERY",
                    1234,
                    page,
                    [(79, "Thu từ các khoản nợ đã xử lý")],
                    _line(page, 80, "1.565.193"),
                    _line(page, 81, "2.018.285"),
                ),
                _mapping(
                    "NET_DERIVATIVE",
                    1232,
                    page,
                    [(82, "Lãi từ các công cụ tài chính phái sinh khác")],
                    _line(page, 83, "87.835"),
                    _line(page, 84, "147.712"),
                ),
                _mapping(
                    "NET_OTHER",
                    6030,
                    page,
                    [(85, "Thu nhập/(chi phí) khác")],
                    _line(page, 86, "507.281"),
                    _line(page, 87, "377.010"),
                ),
            ],
            "owner": [_ref(page, 72, "Lãi thuần từ hoạt động kinh doanh khác")],
            "page_span": [page, page],
            "period_axis": [
                _ref(page, 73, "Từ 01/01/2026"),
                _ref(page, 75, "đến 30/06/2026"),
                _ref(page, 74, "Từ 01/01/2025"),
                _ref(page, 76, "đến 30/06/2025"),
            ],
            "presentation": "NET_ONLY_OPTIONAL_COMPONENTS_THEN_TRAILING_TOTAL",
            "source_only_rows": [],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 77, "Triệu đồng"), _ref(page, 78, "Triệu đồng")],
        }
    )

    page = 64
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VPB",
            "equations": [
                _equation(
                    "INCOME_CHILDREN_EQUAL_INCOME_PARENT",
                    "INCOME",
                    [
                        "INCOME_DERIVATIVE",
                        "DEBT_RECOVERY",
                        "INCOME_ASSET_DISPOSAL",
                        "INCOME_DEBT_SALE",
                        "INCOME_CONTRACT_PENALTY",
                        "INCOME_OTHER",
                    ],
                ),
                _equation(
                    "EXPENSE_CHILDREN_EQUAL_EXPENSE_PARENT",
                    "EXPENSE",
                    ["EXPENSE_DERIVATIVE", "EXPENSE_ASSET_DISPOSAL", "EXPENSE_OTHER"],
                ),
                _equation("INCOME_PLUS_EXPENSE_EQUALS_NET", "TOTAL", ["INCOME", "EXPENSE"]),
            ],
            "graph_roles": [
                "INCOME_PARENT",
                "INCOME_DERIVATIVE",
                "DEBT_RECOVERY",
                "INCOME_ASSET_DISPOSAL",
                "INCOME_DEBT_SALE",
                "INCOME_CONTRACT_PENALTY",
                "INCOME_OTHER",
                "EXPENSE_PARENT",
                "EXPENSE_DERIVATIVE",
                "EXPENSE_ASSET_DISPOSAL",
                "EXPENSE_OTHER",
            ],
            "mappings": [
                _mapping(
                    "TOTAL",
                    6029,
                    page,
                    [(5, "LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC")],
                    _line(page, 52, "1.481.931"),
                    _line(page, 53, "1.070.820"),
                    "TRAILING_UNLABELED_NET_TOTAL",
                ),
                _mapping(
                    "INCOME",
                    1229,
                    page,
                    [(16, "Thu nhập từ hoạt động khác")],
                    _line(page, 17, "2.364.329"),
                    _line(page, 18, "2.128.736"),
                ),
                _mapping(
                    "INCOME_DERIVATIVE",
                    1232,
                    page,
                    [(19, "Thu từ các công cụ tài chính phái sinh khác")],
                    _line(page, 20, "891.919"),
                    _line(page, 21, "967.205"),
                ),
                _mapping(
                    "DEBT_RECOVERY",
                    1234,
                    page,
                    [(22, "Thu từ nợ đã xử lý rủi ro")],
                    _line(page, 23, "873.240"),
                    _line(page, 24, "855.635"),
                ),
                _mapping(
                    "INCOME_ASSET_DISPOSAL",
                    1231,
                    page,
                    [
                        (25, "Thu từ thanh lý tài sản cố định"),
                        (28, "Thu từ thanh lý tài sản khác"),
                    ],
                    _sum(page, [(26, "603"), (29, "7.417")]),
                    _sum(page, [(27, "8.182"), (30, "37.563")]),
                    "CONTROLLED_SUM_OF_TWO_VISIBLE_ASSET_DISPOSAL_ROWS",
                ),
                _mapping(
                    "INCOME_DEBT_SALE",
                    1237,
                    page,
                    [(31, "Thu từ hoạt động bán nợ")],
                    _line(page, 32, "7.000"),
                    _line(page, 33, "29.508"),
                ),
                _mapping(
                    "INCOME_OTHER",
                    1239,
                    page,
                    [(37, "Thu nhập khác")],
                    _line(page, 38, "584.109"),
                    _line(page, 39, "230.634"),
                ),
                _mapping(
                    "EXPENSE",
                    1240,
                    page,
                    [(40, "Chi phí cho hoạt động khác")],
                    _line(page, 41, "(882.398)"),
                    _line(page, 42, "(1.057.916)"),
                ),
                _mapping(
                    "EXPENSE_DERIVATIVE",
                    1241,
                    page,
                    [(43, "Chi về các công cụ tài chính phái sinh khác")],
                    _line(page, 44, "(826.487)"),
                    _line(page, 45, "(997.781)"),
                ),
                _mapping(
                    "EXPENSE_ASSET_DISPOSAL",
                    1242,
                    page,
                    [(46, "Chi về thanh lý tài sản khác")],
                    _line(page, 47, "(4.036)"),
                    _line(page, 48, "(33.626)"),
                ),
                _mapping(
                    "EXPENSE_OTHER",
                    1246,
                    page,
                    [(49, "Chi khác")],
                    _line(page, 50, "(51.875)"),
                    _line(page, 51, "(26.509)"),
                ),
            ],
            "owner": [_ref(page, 5, "LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC")],
            "page_span": [page, page],
            "period_axis": [
                _ref(page, 6, "Cho kỳ kế toán"),
                _ref(page, 8, "3 tháng kết thúc"),
                _ref(page, 10, "ngày 31 tháng 3"),
                _ref(page, 12, "năm 2026"),
                _ref(page, 7, "Cho kỳ kế toán"),
                _ref(page, 9, "3 tháng kết thúc"),
                _ref(page, 11, "ngày 31 tháng 3"),
                _ref(page, 13, "năm 2025"),
            ],
            "presentation": "Q1_GROSS_INCOME_EXPENSE_CHILDREN_THEN_TRAILING_NET_TOTAL",
            "source_only_rows": [
                _source_only(
                    "OACT-001",
                    "INCOME_CONTRACT_PENALTY",
                    page,
                    [(34, "Thu từ phạt vi phạm hợp đồng")],
                    _line(page, 35, "41"),
                    _line(page, 36, "9"),
                    "No distinct other-activity income schema leaf exists for contract-violation penalties.",
                )
            ],
            "source_period": "2026-03-31",
            "unit_evidence": [_ref(page, 14, "Triệu đồng"), _ref(page, 15, "Triệu đồng")],
        }
    )

    documents.extend([_absence("HDB"), _absence("VCB"), _absence("CTG"), _absence("BID")])

    page = 46
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VIB",
            "equations": [
                _equation(
                    "INCOME_CHILDREN_EQUAL_INCOME_PARENT",
                    "INCOME",
                    ["INCOME_DERIVATIVE", "DEBT_RECOVERY", "INCOME_OTHER"],
                ),
                _equation(
                    "EXPENSE_CHILDREN_EQUAL_EXPENSE_PARENT",
                    "EXPENSE",
                    ["EXPENSE_DERIVATIVE", "EXPENSE_OTHER"],
                ),
                _equation("INCOME_PLUS_EXPENSE_EQUALS_NET", "TOTAL", ["INCOME", "EXPENSE"]),
            ],
            "graph_roles": [
                "INCOME_PARENT",
                "INCOME_DERIVATIVE",
                "DEBT_RECOVERY",
                "INCOME_OTHER",
                "EXPENSE_PARENT",
                "EXPENSE_DERIVATIVE",
                "EXPENSE_OTHER",
                "NET_TOTAL",
            ],
            "mappings": [
                _mapping(
                    "TOTAL",
                    6029,
                    page,
                    [(79, "Lãi thuần từ hoạt động khác")],
                    _line(page, 80, "714.841"),
                    _line(page, 81, "860.321"),
                    "TRAILING_LABELED_NET_TOTAL",
                ),
                _mapping(
                    "INCOME",
                    1229,
                    page,
                    [(58, "Thu nhập từ hoạt động khác")],
                    _line(page, 59, "1.093.801"),
                    _line(page, 60, "1.087.595"),
                ),
                _mapping(
                    "INCOME_DERIVATIVE",
                    1232,
                    page,
                    [(61, "Thu từ các công cụ tài chính phái sinh khác")],
                    _line(page, 62, "189.858"),
                    _line(page, 63, "176.698"),
                ),
                _mapping(
                    "DEBT_RECOVERY",
                    1234,
                    page,
                    [(64, "Thu hồi nợ đã xử lý rủi ro")],
                    _line(page, 65, "788.229"),
                    _line(page, 66, "843.793"),
                ),
                _mapping(
                    "INCOME_OTHER",
                    1239,
                    page,
                    [(67, "Thu nhập khác")],
                    _line(page, 68, "115.714"),
                    _line(page, 69, "67.104"),
                ),
                _mapping(
                    "EXPENSE",
                    1240,
                    page,
                    [(70, "Chi phí hoạt động khác")],
                    _line(page, 71, "(378.960)"),
                    _line(page, 72, "(227.274)"),
                ),
                _mapping(
                    "EXPENSE_DERIVATIVE",
                    1241,
                    page,
                    [(73, "Chi cho các công cụ tài chính phái sinh khác")],
                    _line(page, 74, "(289.495)"),
                    _line(page, 75, "(172.752)"),
                ),
                _mapping(
                    "EXPENSE_OTHER",
                    1246,
                    page,
                    [(76, "Chi phí khác")],
                    _line(page, 77, "(89.465)"),
                    _line(page, 78, "(54.522)"),
                ),
            ],
            "owner": [_ref(page, 51, "LÃI THUẦN TỪ HOẠT ĐỘNG KHÁC")],
            "page_span": [page, page],
            "period_axis": [
                _ref(page, 52, "6 tháng đầu"),
                _ref(page, 54, "năm 2026"),
                _ref(page, 53, "6 tháng đầu"),
                _ref(page, 55, "năm 2025"),
            ],
            "presentation": "GROSS_INCOME_EXPENSE_CHILDREN_THEN_LABELED_NET_TOTAL",
            "source_only_rows": [],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 56, "triệu đồng"), _ref(page, 57, "triệu đồng")],
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
    return {**material, "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex other-activity pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    return operating._document(items, code, label)


def _page(document: Mapping[str, Any], page: int, label: str) -> dict[str, Any]:
    return operating._page(document, page, label)


def _semantic_evidence(
    axis_document: Mapping[str, Any], semantic_document: Mapping[str, Any], ref: Mapping[str, Any]
) -> dict[str, Any]:
    return operating._semantic_evidence(axis_document, semantic_document, ref)


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
    return {
        "accounting_equation_verified_count": sum(
            len(t["verified_accounting_equations"]) for t in trials
        ),
        "authenticated_pixel_dash_zero_count": sum(
            value.get("source_numeric_challenger_status")
            == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
            for trial in trials
            for group in (trial["verified_mappings"], trial["verified_source_only_rows"])
            for row in group
            for value in row["values"]
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
            for trial in trials
            for group in (trial["verified_mappings"], trial["verified_source_only_rows"])
            for row in group
            for value in row["values"]
        ),
        "mapping_verified_count": sum(len(t["verified_mappings"]) for t in trials),
        "open_source_row_count": sum(len(t["verified_source_only_rows"]) for t in trials),
        "q1_source_period_caveat_document_count": sum(
            t["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" for t in trials
        ),
        "verified_value_cell_count": sum(
            len(row["values"]) for t in trials for row in t["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("other-activity result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("other-activity result identity or metrics drifted")
    allowed = {
        "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT_AND_UNRESOLVED_SCHEMA_ROWS",
        "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SCHEMA_ROWS",
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
            or any(
                item.get("status") != "UNRESOLVED_SCHEMA_GAP_SOURCE_ROW_RETAINED"
                for item in trial.get("verified_source_only_rows", [])
            )
        ):
            raise _error("other-activity trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("other-activity result identity drifted")
    return canonical_clone_v1(value)


def _source_period_status(source_period: str) -> str:
    if source_period == "2025-12-31":
        return "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
    return (
        "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
        if source_period == "2026-03-31"
        else "VERIFIED_SOURCE_PERIOD_Q2_2026"
    )


def _verified_value(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    ref: Mapping[str, Any],
) -> dict[str, Any]:
    page_number = ref["page_sequence"]
    crop_page = _page(crop_document, page_number, "crop manifest")
    if ref["kind"] == "AUTHENTICATED_CONTROLLED_SUM":
        components = ref.get("components")
        if (
            type(components) is not list
            or len(components) < 2
            or any(item.get("page_sequence") != page_number for item in components)
        ):
            raise _error("other-activity controlled-sum reference drifted")
        evidence = [
            _verified_value(axis_document, semantic_document, crop_document, item)
            for item in components
        ]
        proposals = [item["fresh_vietocr_numeric_proposal"] for item in evidence]
        parsed_proposals = []
        for proposal in proposals:
            try:
                parsed_proposals.append(
                    operating.income.foundation.support._money(proposal)
                    if proposal is not None
                    else None
                )
            except ValueError:
                parsed_proposals.append(None)
        return {
            "component_evidence": evidence,
            "fresh_vietocr_numeric_proposal": (
                sum(item for item in parsed_proposals if item is not None)
                if all(item is not None for item in parsed_proposals)
                else None
            ),
            "fresh_vietocr_numeric_status": (
                "MATCHES_SOURCE_NUMERIC_CHALLENGER"
                if all(
                    item["fresh_vietocr_numeric_status"] == "MATCHES_SOURCE_NUMERIC_CHALLENGER"
                    for item in evidence
                )
                else "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            ),
            "normalized_value": sum(item["normalized_value"] for item in evidence),
            "page_sequence": page_number,
            "pixel_transcription": " + ".join(item["pixel_transcription"] for item in evidence),
            "source_line_index": None,
            "source_numeric_challenger": " + ".join(
                item["source_numeric_challenger"]
                if item["source_numeric_challenger"] is not None
                else item["pixel_transcription"]
                for item in evidence
            ),
            "source_numeric_challenger_status": (
                "CONTROLLED_SUM_OF_AUTHENTICATED_SOURCE_NUMERIC_LINES"
            ),
        }
    if ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH":
        render = movement._render_bytes(crop_document, crop_page)
        movement._verify_pixel_binding(
            {"bbox_raw_pixels": ref["bbox_raw_pixels"], "rgb_sha256": ref["pixel_rgb_sha256"]},
            render,
        )
        return {
            "fresh_vietocr_numeric_proposal": None,
            "fresh_vietocr_numeric_status": "NO_SEMANTIC_LINE_FOR_VISIBLE_DASH",
            "normalized_value": 0,
            "page_sequence": page_number,
            "pixel_bbox": list(ref["bbox_raw_pixels"]),
            "pixel_rgb_sha256": ref["pixel_rgb_sha256"],
            "pixel_transcription": "-",
            "render_ref": canonical_clone_v1(crop_page["render_binding"]),
            "source_line_index": None,
            "source_numeric_challenger": None,
            "source_numeric_challenger_status": "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE",
        }
    if ref["kind"] != "AUTHENTICATED_LINE":
        raise _error("other-activity value reference kind drifted")
    axis_page = _page(axis_document, page_number, "accounting axis")
    semantic_page = _page(semantic_document, page_number, "semantic index")
    source_texts = operating.income.foundation.support._source_line_axis(crop_page)
    evidence = operating.income.foundation.support._source_value(
        axis_page,
        semantic_page,
        crop_page,
        source_texts,
        {"line_index": ref["line_index"], "pixel_transcription": ref["pixel_transcription"]},
    )
    try:
        proposal = operating.income.foundation.support._money(
            evidence["fresh_vietocr_numeric_proposal"]
        )
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


def build_other_activity_8bank_codex_verified_mapping_v1(
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
    scanner.validate_other_activity_full_document_scan_replay_v1(structure_scan, semantic_index)
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
                raise _error("absent detailed other-activity note unexpectedly matched")
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
                    "verified_source_only_rows": [],
                }
            )
            continue
        if not same_typed_json_v1(
            matcher["uniqueness"], {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        ) or not same_typed_json_v1(matcher["regions"][0]["page_span"], reviewed["page_span"]):
            raise _error("reviewed region is not the unique whole-PDF other-activity graph")
        if matcher["regions"][0]["layout"]["observed_roles"] != reviewed["graph_roles"]:
            raise _error("reviewed other-activity graph role axis drifted")
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
                cache[key] = _verified_value(axis_document, semantic_document, crop_document, ref)
            return canonical_clone_v1(cache[key])

        verified_mappings = []
        verified_source_only = []
        by_role: dict[str, dict[str, Any]] = {}
        mapped_ids = set()
        for mapping in reviewed["mappings"]:
            item = {
                "label_evidence": [
                    _semantic_evidence(axis_document, semantic_document, label)
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
        for row in reviewed["source_only_rows"]:
            item = {
                "label_evidence": [
                    _semantic_evidence(axis_document, semantic_document, label)
                    for label in row["labels"]
                ],
                "reason": row["reason"],
                "role": row["role"],
                "row_id": row["row_id"],
                "status": "UNRESOLVED_SCHEMA_GAP_SOURCE_ROW_RETAINED",
                "values": [
                    {"axis_role": axis_role, **verified(ref)}
                    for axis_role, ref in row["values"].items()
                ],
            }
            verified_source_only.append(item)
            by_role[item["role"]] = item
        equations = []
        for specification in reviewed["equations"]:
            for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
                parent = next(
                    v
                    for v in by_role[specification["parent_role"]]["values"]
                    if v["axis_role"] == axis_role
                )
                terms = [
                    next(v for v in by_role[role]["values"] if v["axis_role"] == axis_role)
                    for role in specification["term_roles"]
                ]
                computed = sum(item["normalized_value"] for item in terms)
                if computed != parent["normalized_value"]:
                    raise _error(
                        f"other-activity equation does not close for {code}/{specification['name']}/{axis_role}"
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
        period_status = _source_period_status(reviewed["source_period"])
        has_open = bool(verified_source_only)
        status = (
            "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT_AND_UNRESOLVED_SCHEMA_ROWS"
            if period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" and has_open
            else "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SCHEMA_ROWS"
            if has_open
            else "VERIFIED_BY_CODEX"
        )
        page_number = reviewed["page_span"][0]
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "mapped_report_norm_ids": sorted(mapped_ids),
                "owner_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["owner"]
                ],
                "page_span": list(reviewed["page_span"]),
                "period_axis_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["period_axis"]
                ],
                "presentation": reviewed["presentation"],
                "source_geometry_mode": _page(semantic_document, page_number, "semantic index")[
                    "geometry_mode"
                ],
                "source_period": reviewed["source_period"],
                "source_period_status": period_status,
                "status": status,
                "unit_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
                "verified_source_only_rows": verified_source_only,
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
            "family_end_display_order": SCHEMA_FAMILY_END_DISPLAY_ORDER,
            "family_roots": [
                _schema_binding(schema_by_id.get(report_norm_id), report_norm_id)
                for report_norm_id in (6029, 1229, 1240)
            ],
            "mapped_report_norm_ids": mapped_union,
            "schema_gap_source_row_count": sum(len(t["verified_source_only_rows"]) for t in trials),
            "section_root": _schema_binding(schema_by_id.get(1142), 1142),
        },
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_other_activity_8bank_codex_verified_mapping_replay_v1(
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
    rebuilt = build_other_activity_8bank_codex_verified_mapping_v1(
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
        raise _error("other-activity verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = operating.income.foundation.support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = operating.income.foundation.support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _live_inputs() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_other_activity_full_document_scan_v1(SEMANTIC_INDEX_PATH)
    review, review_sha = _stable_json(REVIEW_PATH)
    historical_result, _ = _stable_json(RESULT_PATH)
    historical_result = _validate_result(historical_result)
    if historical_result.get("result_id") != EXPECTED_RESULT_ID:
        raise _error("fixed historical other-activity result identity drifted")
    schema_authority = canonical_clone_v1(historical_result["input_refs"]["schema_authority"])
    _live_schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
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


def build_live_other_activity_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_other_activity_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_other_activity_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    return validate_other_activity_8bank_codex_verified_mapping_replay_v1(value, **_live_inputs())


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
        _write(RESULT_PATH, build_live_other_activity_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_other_activity_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
