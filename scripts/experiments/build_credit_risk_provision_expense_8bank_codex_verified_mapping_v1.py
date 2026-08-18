"""Verify detailed credit-risk provision expense notes in the fixed reports."""

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
        raise RuntimeError(f"cannot load provision-expense support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


operating = _load(
    "operating_expense_support_for_credit_risk_provision_expense",
    "build_operating_expense_8bank_codex_verified_mapping_v1.py",
)
movement = _load(
    "provision_movement_support_for_credit_risk_provision_expense",
    "build_provision_movement_8bank_codex_verified_mapping_v1.py",
)
scanner = _load(
    "credit_risk_provision_expense_scan_for_verified_mapping",
    "scan_credit_risk_provision_expense_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "CREDIT_RISK_PROVISION_EXPENSE_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "CREDIT_RISK_PROVISION_EXPENSE_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "CREDIT_RISK_PROVISION_EXPENSE_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "e0089:result:"
REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "e0089:pixel-review:"
REVIEW_RUN_ID = "E-0089"
ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = True
SCHEMA_FAMILY_END_DISPLAY_ORDER = 787
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_DETAILED_"
    "CREDIT_RISK_PROVISION_EXPENSE_GRAPH_VISIBLE_PDF_PADDLEOCR_OR_NATIVE_"
    "NUMERIC_CHALLENGER_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_"
    "UNMAPPED_SOURCE_ROWS_RETAINED_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0089-credit-risk-provision-expense-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0089-credit-risk-provision-expense-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = operating.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = operating.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = operating.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "crpefdsv1:scan:d3a6ee7d5ce97dbd8237c6b938c553c2a5e94c62fc9cde994baef6ec7be7017f"
EXPECTED_RESULT_ID = "e0089:result:dd1a86d9db53e3bc656b66177700b3c92000a30d0336f1cda7f600ba8edd2710"

_SCHEMA_EXPECTED = {
    1142: (
        "II. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG KẾT QUẢ KINH DOANH",
        None,
        684,
    ),
    1221: ("Chi phí dự phòng rủi ro tín dụng", 1142, 777),
    6032: ("Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay TCTD", 1221, 778),
    6031: ("Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay khách hàng", 1221, 781),
    1224: ("Trích lập dự phòng chung cho vay khách hàng", 1221, 782),
    1225: ("Trích lập dự phòng cụ thể cho vay khách hàng", 1221, 783),
    6033: ("Chi phí/(Hoàn nhập) dự phòng mua nợ", 1221, 784),
    1226: ("Trích lập dự phòng trái phiếu đặc biệt VAMC", 1221, 785),
    1227: ("Hoàn nhập dự phòng rủi ro cho các cam kết ngoại bảng", 1221, 786),
    1228: ("Dự phòng khác", 1221, 787),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "dash_zero_policy_applied_only_to_visible_dash": True,
    "detailed_note_absence_bounded_to_bound_report": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_provision_expense_rows": True,
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


class CreditRiskProvisionExpense8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, numbers, equation, or schema evidence drifted."""


def _error(message: str) -> CreditRiskProvisionExpense8BankCodexVerifiedMappingV1Error:
    return CreditRiskProvisionExpense8BankCodexVerifiedMappingV1Error(message)


def _ref(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str) -> dict[str, Any]:
    return {"kind": "AUTHENTICATED_LINE", **_ref(page, line, text)}


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
                "No Arabic-numbered detailed credit-risk provision-expense note with "
                "period/unit axes, at least two component rows, and a trailing total was "
                "found in the bound report; statement aggregate and policy text do not qualify."
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
        "presentation": "NO_DETAILED_PROVISION_EXPENSE_NOTE_IN_BOUND_REPORT",
        "source_only_rows": [],
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    documents = [_absence("ACB")]

    page = 49
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "MBB",
            "equations": [
                _equation(
                    "VISIBLE_COMPONENTS_EQUAL_TRAILING_TOTAL",
                    "TOTAL",
                    ["CUSTOMER", "INTERBANK", "PURCHASED_DEBT", "OTHER_RISK", "COMMITMENT"],
                )
            ],
            "graph_roles": [
                "CUSTOMER_LOAN_PROVISION",
                "INTERBANK_PROVISION",
                "PURCHASED_DEBT_PROVISION",
                "OTHER_RISK_PROVISION",
                "COMMITMENT_PROVISION",
            ],
            "mappings": [
                _mapping(
                    "TOTAL",
                    1221,
                    page,
                    [(0, "9. Chi phí/(hoàn nhập) dự phòng rủi ro")],
                    _line(page, 25, "7.701.901"),
                    _line(page, 26, "7.772.631"),
                    "TRAILING_UNLABELED_TOTAL",
                ),
                _mapping(
                    "CUSTOMER",
                    6031,
                    page,
                    [(7, "Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay"), (8, "khách hàng")],
                    _line(page, 9, "7.695.570"),
                    _line(page, 10, "7.712.497"),
                ),
                _mapping(
                    "INTERBANK",
                    6032,
                    page,
                    [(11, "Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay"), (12, "TCTD")],
                    _line(page, 13, "2.729"),
                    _line(page, 14, "1.785"),
                ),
                _mapping(
                    "PURCHASED_DEBT",
                    6033,
                    page,
                    [(15, "Chi phí/(Hoàn nhập) dự phòng mua nợ")],
                    _line(page, 16, "217"),
                    _line(page, 17, "78.417"),
                ),
                _mapping(
                    "OTHER_RISK",
                    1228,
                    page,
                    [(18, "Chi phí/(Hoàn nhập) dự phòng các khoản rủi"), (19, "ro khác")],
                    _dash(
                        page,
                        [1188, 558, 1202, 568],
                        "f373b143e21eb533b4afa21608becb14d8b3cda663cb75859dab874325995192",
                    ),
                    _line(page, 20, "(19.982)"),
                ),
                _mapping(
                    "COMMITMENT",
                    1227,
                    page,
                    [(21, "Chi phí/(Hoàn nhập) dự phòng với các cam"), (22, "kết đưa ra")],
                    _line(page, 23, "3.385"),
                    _line(page, 24, "(86)"),
                ),
            ],
            "owner": [_ref(page, 0, "9. Chi phí/(hoàn nhập) dự phòng rủi ro")],
            "page_span": [page, page],
            "period_axis": [
                _ref(page, 1, "Từ 01/01/2026"),
                _ref(page, 3, "đến 30/06/2026"),
                _ref(page, 2, "Từ 01/01/2025"),
                _ref(page, 4, "đến 30/06/2025"),
            ],
            "presentation": "WRAPPED_OPTIONAL_COMPONENT_ROWS_THEN_TRAILING_TOTAL",
            "source_only_rows": [],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 5, "Triệu đồng"), _ref(page, 6, "Triệu đồng")],
        }
    )

    page = 66
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VPB",
            "equations": [
                _equation(
                    "VISIBLE_COMPONENTS_EQUAL_TRAILING_TOTAL",
                    "TOTAL",
                    ["CUSTOMER", "MARGIN", "PURCHASED_DEBT", "VAMC"],
                )
            ],
            "graph_roles": [
                "CUSTOMER_LOAN_PROVISION",
                "MARGIN_LOAN_PROVISION",
                "PURCHASED_DEBT_PROVISION",
                "VAMC_PROVISION",
            ],
            "mappings": [
                _mapping(
                    "TOTAL",
                    1221,
                    page,
                    [(5, "CHI PHÍ DỰ PHÒNG RỦI RO TÍN DỤNG")],
                    _line(page, 32, "7.669.094"),
                    _line(page, 33, "6.677.305"),
                    "TRAILING_UNLABELED_TOTAL",
                ),
                _mapping(
                    "CUSTOMER",
                    6031,
                    page,
                    [
                        (17, "Chi phí dự phòng rủi ro cho vay khách hàng (Thuyết"),
                        (18, "minh số 11)"),
                    ],
                    _line(page, 19, "7.672.416"),
                    _line(page, 20, "6.607.686"),
                ),
                _mapping(
                    "PURCHASED_DEBT",
                    6033,
                    page,
                    [
                        (25, "Hoàn nhập dự phòng rủi ro hoạt động mua nợ"),
                        (26, "(Thuyết minh số 12)"),
                    ],
                    _line(page, 27, "(3.322)"),
                    _line(page, 28, "(405)"),
                ),
                _mapping(
                    "VAMC",
                    1226,
                    page,
                    [(29, "Chi phí dự phòng trái phiếu VAMC")],
                    _line(page, 30, "-"),
                    _line(page, 31, "40.656"),
                ),
            ],
            "owner": [_ref(page, 5, "CHI PHÍ DỰ PHÒNG RỦI RO TÍN DỤNG")],
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
            "presentation": "Q1_OPTIONAL_COMPONENT_ROWS_THEN_TRAILING_TOTAL",
            "source_only_rows": [
                _source_only(
                    "CRPE-001",
                    "MARGIN",
                    page,
                    [
                        (21, "Chi phí dự phòng cho vay giao dịch ký quỹ và"),
                        (22, "ứng trước (Thuyết minh số 11)"),
                    ],
                    _line(page, 23, "-"),
                    _line(page, 24, "29.368"),
                    "No distinct income-statement-note schema leaf exists for margin-loan and customer-advance provision expense.",
                )
            ],
            "source_period": "2026-03-31",
            "unit_evidence": [_ref(page, 15, "Triệu đồng"), _ref(page, 16, "Triệu đồng")],
        }
    )

    documents.extend([_absence("HDB"), _absence("VCB"), _absence("CTG"), _absence("BID")])

    page = 47
    documents.append(
        {
            "absence_evidence": None,
            "bank_code": "VIB",
            "equations": [
                _equation(
                    "GENERAL_PLUS_SPECIFIC_EQUALS_CUSTOMER", "CUSTOMER", ["GENERAL", "SPECIFIC"]
                ),
                _equation(
                    "VISIBLE_COMPONENTS_EQUAL_TRAILING_TOTAL",
                    "TOTAL",
                    ["CUSTOMER", "PURCHASED_DEBT", "TRADE_FINANCE"],
                ),
            ],
            "graph_roles": [
                "CUSTOMER_LOAN_PROVISION",
                "GENERAL_PROVISION",
                "SPECIFIC_PROVISION",
                "PURCHASED_DEBT_PROVISION",
                "NONADDITIVE_DETAIL",
                "TRADE_FINANCE_RECEIVABLE_PROVISION",
            ],
            "mappings": [
                _mapping(
                    "TOTAL",
                    1221,
                    page,
                    [(5, "CHI PHÍ DỰ PHÒNG RỦI RO TÍN DỤNG")],
                    _line(page, 32, "2.485.817"),
                    _line(page, 33, "1.056.969"),
                    "TRAILING_UNLABELED_TOTAL",
                ),
                _mapping(
                    "CUSTOMER",
                    6031,
                    page,
                    [(12, "Biến động dự phòng rủi ro cho vay khách hàng")],
                    _line(page, 13, "2.485.863"),
                    _line(page, 14, "1.057.227"),
                ),
                _mapping(
                    "GENERAL",
                    1224,
                    page,
                    [(15, "Trích lập dự phòng chung")],
                    _line(page, 16, "117.980"),
                    _line(page, 17, "238.937"),
                ),
                _mapping(
                    "SPECIFIC",
                    1225,
                    page,
                    [(18, "Trích lập dự phòng cụ thể")],
                    _line(page, 19, "2.367.883"),
                    _line(page, 20, "818.290"),
                ),
                _mapping(
                    "PURCHASED_DEBT",
                    6033,
                    page,
                    [(21, "Biến động dự phòng rủi ro hoạt động mua nợ")],
                    _line(page, 22, "(46)"),
                    _line(page, 23, "(14)"),
                ),
            ],
            "owner": [_ref(page, 5, "CHI PHÍ DỰ PHÒNG RỦI RO TÍN DỤNG")],
            "page_span": [page, page],
            "period_axis": [
                _ref(page, 6, "6 tháng đầu"),
                _ref(page, 8, "năm 2026"),
                _ref(page, 7, "6 tháng đầu"),
                _ref(page, 9, "năm 2025"),
            ],
            "presentation": "PARENT_WITH_GENERAL_SPECIFIC_CHILDREN_AND_OPTIONAL_OTHER_COMPONENTS",
            "source_only_rows": [
                _source_only(
                    "CRPE-002",
                    "TRADE_FINANCE",
                    page,
                    [
                        (27, "Biến động dự phòng rủi ro các khoản phải thu từ hoạt động"),
                        (28, "tài trợ thương mại"),
                    ],
                    _dash(
                        page,
                        [1214, 772, 1227, 782],
                        "2db03a2964a616e95803f8b7bf5e04cbc98187eb9d9fd81a563e73711dc32b5d",
                    ),
                    _line(page, 29, "(244)"),
                    "No distinct income-statement-note schema leaf exists for provision expense on trade-finance receivables.",
                )
            ],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 10, "triệu đồng"), _ref(page, 11, "triệu đồng")],
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
        raise _error("Codex provision-expense pixel review differs from the fixed ledger")
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


def _source_evidence_values(row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    values = list(row["values"])
    for component in row.get("source_components", []):
        values.extend(component["values"])
    return values


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
            for value in _source_evidence_values(row)
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
            for value in _source_evidence_values(row)
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
        raise _error("provision-expense result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("provision-expense result identity or metrics drifted")
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
            raise _error("provision-expense trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("provision-expense result identity drifted")
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
        raise _error("provision-expense value reference kind drifted")
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


def build_credit_risk_provision_expense_8bank_codex_verified_mapping_v1(
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
    scanner.validate_credit_risk_provision_expense_full_document_scan_replay_v1(
        structure_scan, semantic_index
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
                raise _error("absent detailed provision-expense note unexpectedly matched")
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
            raise _error("reviewed region is not the unique whole-PDF provision-expense graph")
        if matcher["regions"][0]["layout"]["observed_roles"] != reviewed["graph_roles"]:
            raise _error("reviewed provision-expense graph role axis drifted")
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
            aggregate_components = mapping.get("aggregation_components")
            if aggregate_components is not None:
                if type(aggregate_components) is not list or len(aggregate_components) < 2:
                    raise _error("controlled catchall aggregate requires at least two source rows")
                verified_components = []
                for component in aggregate_components:
                    verified_components.append(
                        {
                            "label_evidence": [
                                _semantic_evidence(axis_document, semantic_document, label)
                                for label in component["labels"]
                            ],
                            "role": component["role"],
                            "values": [
                                {"axis_role": axis_role, **verified(ref)}
                                for axis_role, ref in component["values"].items()
                            ],
                        }
                    )
                aggregate_values = []
                for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
                    component_values = [
                        next(
                            value
                            for value in component["values"]
                            if value["axis_role"] == axis_role
                        )
                        for component in verified_components
                    ]
                    aggregate_values.append(
                        {
                            "axis_role": axis_role,
                            "derivation": "SUM_OF_VISIBLE_VERIFIED_SOURCE_COMPONENTS",
                            "normalized_value": sum(
                                value["normalized_value"] for value in component_values
                            ),
                            "source_component_count": len(component_values),
                            "source_component_roles": [
                                component["role"] for component in verified_components
                            ],
                        }
                    )
                item = {
                    "label_evidence": [
                        evidence
                        for component in verified_components
                        for evidence in component["label_evidence"]
                    ],
                    "role": mapping["role"],
                    "schema_binding": _schema_binding(
                        schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                    ),
                    "source_components": verified_components,
                    "status": "VERIFIED_BY_CODEX",
                    "topology": mapping["topology"],
                    "values": aggregate_values,
                }
                verified_mappings.append(item)
                by_role[item["role"]] = item
                mapped_ids.add(mapping["report_norm_id"])
                continue
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
                        f"provision-expense equation does not close for {code}/{specification['name']}/{axis_role}"
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
            "family_root": _schema_binding(schema_by_id.get(1221), 1221),
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


def validate_credit_risk_provision_expense_8bank_codex_verified_mapping_replay_v1(
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
    rebuilt = build_credit_risk_provision_expense_8bank_codex_verified_mapping_v1(
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
        raise _error("provision-expense verified mapping does not replay exactly")
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
    structure_scan = scanner.build_live_credit_risk_provision_expense_full_document_scan_v1(
        SEMANTIC_INDEX_PATH
    )
    review, review_sha = _stable_json(REVIEW_PATH)
    historical_result, _ = _stable_json(RESULT_PATH)
    historical_result = _validate_result(historical_result)
    if historical_result.get("result_id") != EXPECTED_RESULT_ID:
        raise _error("fixed historical provision-expense result identity drifted")
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


def build_live_credit_risk_provision_expense_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_credit_risk_provision_expense_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_credit_risk_provision_expense_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    return validate_credit_risk_provision_expense_8bank_codex_verified_mapping_replay_v1(
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
            RESULT_PATH, build_live_credit_risk_provision_expense_8bank_codex_verified_mapping_v1()
        )
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_credit_risk_provision_expense_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
