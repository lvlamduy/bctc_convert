"""Verify the entrusted/investment-risk capital disclosure across eight banks.

The upstream matcher scans every page without using bank, page, filename, or
note-number routing.  This bounded review then binds the three unique detailed
notes to fresh VietOCR anchors, visible pixels, the original numeric axis,
period/unit topology, exact repeated-total equations, and the live TM schema.
Five reports that move directly from customer deposits to the next liability
family are recorded as bounded-report absences rather than corpus-wide absence
claims.
"""

from __future__ import annotations

import argparse
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

__all__ = [
    "FORMAT_VERSION",
    "EntrustedInvestmentRiskCapital8BankCodexVerifiedMappingV1Error",
    "build_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1",
    "build_live_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1",
    "validate_entrusted_investment_risk_capital_8bank_codex_verified_mapping_replay_v1",
    "validate_live_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1",
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
    "government_nhnn_mapping_support_for_entrusted_capital",
    "build_government_nhnn_liabilities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "entrusted_capital_scan_for_verified_mapping",
    "scan_entrusted_investment_risk_capital_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "ENTRUSTED_INVESTMENT_RISK_CAPITAL_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ENTRUSTED_INVESTMENT_RISK_CAPITAL_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_GENERIC_ENTRUSTED_"
    "INVESTMENT_RISK_CAPITAL_OWNER_CHILD_PERIOD_UNIT_BOUNDARY_PLUS_INDEPENDENT_"
    "VISIBLE_PIXEL_UPSTREAM_NUMERIC_CHALLENGER_ACCOUNTING_AND_LIVE_TM_SCHEMA_"
    "ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0075-entrusted-investment-risk-capital-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0075-entrusted-investment-risk-capital-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "eircfds1:scan:949001913526778b1e26031c3d698a8dcd8724105603573e3549fc87005118e5"
_RESULT_STATE = "ENTRUSTED_INVESTMENT_RISK_CAPITAL_8BANK_CODEX_VERIFICATION_COMPLETE"
_RESULT_ID_PREFIX = "e0075:result:"
_REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
_REVIEW_ID_PREFIX = "e0075:pixel-review:"
_REVIEW_RUN_ID = "E-0075"
_EXPECTED_COMPLETE_REGION_COUNT = 3
_FAMILY_DISPLAY_ORDER_RANGE = [603, 610]

_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_OR_BOUND_ABSENCE",
    "OWNER_PRECEDES_DETAIL_CHILDREN",
    "CUSTOMER_DEPOSIT_TO_NEXT_FAMILY_BOUNDARY_FOR_ABSENCE",
    "CURRENT_AND_COMPARATIVE_PERIOD_AXES_VISIBLE",
    "MILLION_VND_UNIT_AXIS_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_AND_SIGN",
    "UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_CHALLENGER",
    "REPEATED_TOTAL_ACCOUNTING_WHERE_PRINTED",
    "SMALL_UNLISTED_SOURCE_CLASS_USES_SCHEMA_OTHER",
    "LIVE_TM_SCHEMA_PARENT_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "bounded_report_absence_promoted_to_corpus_wide_absence": False,
    "comparison_period_used_as_mapping_authority": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_NUMERIC_CHALLENGER",
    "old_ocr_used_as_semantic_anchor": False,
    "small_unlisted_source_class_may_map_to_explicit_other_leaf": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "bounded_report_family_absence_authority": True,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_entrusted_capital_rows": True,
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
_SCHEMA_EXPECTED = {
    1092: (
        "Vốn nhận tài trợ, ủy thác đầu tư, cho vay các tổ chức tín dụng chịu rủi ro",
        560,
        603,
    ),
    1093: ("Vốn nhận của các tổ chức, cá nhân", 1092, 604),
    1099: ("Khác", 1092, 610),
}


class EntrustedInvestmentRiskCapital8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, numeric evidence, accounting, or schema drifted."""


def _error(message: str) -> EntrustedInvestmentRiskCapital8BankCodexVerifiedMappingV1Error:
    return EntrustedInvestmentRiskCapital8BankCodexVerifiedMappingV1Error(message)


def _label(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _value(page: int, line: int, text: str) -> dict[str, Any]:
    return {
        "kind": "AUTHENTICATED_LINE",
        "line_index": line,
        "multiplier": 1,
        "page_sequence": page,
        "pixel_transcription": text,
    }


def _mapping(
    report_norm_id: int,
    role: str,
    labels: Sequence[dict[str, Any]],
    current: Sequence[dict[str, Any]],
    comparative: Sequence[dict[str, Any]],
    topology: str,
) -> dict[str, Any]:
    return {
        "labels": list(labels),
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {"COMPARATIVE": list(comparative), "CURRENT": list(current)},
    }


def _equation(
    name: str, period_role: str, terms: Sequence[dict[str, Any]], total: dict[str, Any]
) -> dict[str, Any]:
    return {"name": name, "period_role": period_role, "terms": list(terms), "total": total}


def _present(
    code: str,
    page: int,
    owner_line: int,
    owner_text: str,
    periods: Sequence[dict[str, Any]],
    units: Sequence[dict[str, Any]],
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[dict[str, Any]],
    *,
    source_period: str = "2026-06-30",
) -> dict[str, Any]:
    return {
        "bank_code": code,
        "boundary_evidence": [],
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": "VERIFIED_BY_CODEX",
        "equations": list(equations),
        "mappings": list(mappings),
        "owner": _label(page, owner_line, owner_text),
        "page_span": [page, page],
        "period_axis": list(periods),
        "source_period": source_period,
        "unit_evidence": list(units),
    }


def _absent(code: str, preceding: dict[str, Any], following: dict[str, Any]) -> dict[str, Any]:
    checks = {check: "NOT_APPLICABLE" for check in _REVIEW_CHECKS}
    checks["COMPLETE_PDF_UNIQUE_REGION_OR_BOUND_ABSENCE"] = "PASS_BOUND_REPORT_ABSENCE"
    checks["CUSTOMER_DEPOSIT_TO_NEXT_FAMILY_BOUNDARY_FOR_ABSENCE"] = "PASS"
    return {
        "bank_code": code,
        "boundary_evidence": [preceding, following],
        "checks": checks,
        "disposition": "NOT_OBSERVED_IN_BOUND_REPORT",
        "equations": [],
        "mappings": [],
        "owner": None,
        "page_span": [preceding["page_sequence"], following["page_sequence"]],
        "period_axis": [],
        "source_period": "2026-06-30",
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    documents = [
        _absent(
            "ACB",
            _label(21, 5, "TIỀN GỬI CỦA KHÁCH HÀNG"),
            _label(21, 74, "11. PHÁT HÀNH GIẤY TỜ CÓ GIÁ"),
        ),
        _present(
            "MBB",
            43,
            81,
            "Vốn tài trợ ủy thác đầu tư, cho vay TCTD chịu rủi ro",
            [_label(43, 82, "30/06/2026"), _label(43, 83, "31/12/2025")],
            [_label(43, 84, "Triệu đồng"), _label(43, 85, "Triệu đồng")],
            [
                _mapping(
                    1092,
                    "FAMILY_TOTAL",
                    [_label(43, 81, "Vốn tài trợ ủy thác đầu tư, cho vay TCTD chịu rủi ro")],
                    [_value(43, 89, "2.287.529")],
                    [_value(43, 90, "3.912.833")],
                    "UNLABELED_TOTAL_AFTER_SOLE_VISIBLE_CHILD",
                ),
                _mapping(
                    1093,
                    "ORGANIZATION_OR_INDIVIDUAL",
                    [_label(43, 86, "Vốn nhận của tổ chức, cá nhân khác")],
                    [_value(43, 87, "2.287.529")],
                    [_value(43, 88, "3.912.833")],
                    "OWNER_CHILD",
                ),
            ],
            [
                _equation(
                    "SOLE_CHILD_TO_PRINTED_TOTAL",
                    "CURRENT",
                    [_value(43, 87, "2.287.529")],
                    _value(43, 89, "2.287.529"),
                ),
                _equation(
                    "SOLE_CHILD_TO_PRINTED_TOTAL",
                    "COMPARATIVE",
                    [_value(43, 88, "3.912.833")],
                    _value(43, 90, "3.912.833"),
                ),
            ],
        ),
        _present(
            "VPB",
            56,
            5,
            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TỔ CHỨC TÍN DỤNG CHỊU RỦI RO",
            [
                _label(56, 6, "Ngày 31 tháng 3"),
                _label(56, 8, "năm 2026"),
                _label(56, 7, "Ngày 31 tháng 12"),
                _label(56, 9, "năm 2025"),
            ],
            [_label(56, 10, "Triệu đồng"), _label(56, 11, "Triệu đồng")],
            [
                _mapping(
                    1092,
                    "FAMILY_TOTAL",
                    [
                        _label(
                            56,
                            5,
                            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TỔ CHỨC TÍN DỤNG CHỊU RỦI RO",
                        )
                    ],
                    [_value(56, 16, "38.296")],
                    [_value(56, 17, "16.394")],
                    "UNLABELED_TOTAL_AFTER_SOLE_VISIBLE_CHILD",
                ),
                _mapping(
                    1099,
                    "OTHER_SMALL_ODA_SOURCE",
                    [
                        _label(56, 12, "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng VND từ"),
                        _label(56, 13, "Dự án Hỗ trợ phát triển chính thức (ODA)"),
                    ],
                    [_value(56, 14, "38.296")],
                    [_value(56, 15, "16.394")],
                    "OWNER_SMALL_UNLISTED_CHILD_TO_EXPLICIT_OTHER",
                ),
            ],
            [
                _equation(
                    "SOLE_CHILD_TO_PRINTED_TOTAL",
                    "CURRENT",
                    [_value(56, 14, "38.296")],
                    _value(56, 16, "38.296"),
                ),
                _equation(
                    "SOLE_CHILD_TO_PRINTED_TOTAL",
                    "COMPARATIVE",
                    [_value(56, 15, "16.394")],
                    _value(56, 17, "16.394"),
                ),
            ],
            source_period="2026-03-31",
        ),
        _absent(
            "HDB",
            _label(31, 28, "Tiền gửi của khách hàng"),
            _label(31, 60, "Phát hành giấy tờ có giá thông thường"),
        ),
        _absent(
            "VCB",
            _label(35, 8, "11. Tiền gửi của khách hàng"),
            _label(35, 40, "12. Phát hành giấy tờ có giá"),
        ),
        _absent(
            "CTG",
            _label(42, 4, "9. TIỀN GỬI CỦA KHÁCH HÀNG"),
            _label(42, 47, "10. PHÁT HÀNH GIẤY TỜ CÓ GIÁ"),
        ),
        _absent(
            "BID",
            _label(25, 37, "9. TIỀN GỬI CỦA KHÁCH HÀNG"),
            _label(25, 78, "10. PHÁT HÀNH GIẤY TỜ CÓ GIÁ"),
        ),
        _present(
            "VIB",
            42,
            97,
            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO",
            [_label(42, 98, "30/06/2026"), _label(42, 99, "31/12/2025")],
            [_label(42, 100, "triệu đồng"), _label(42, 101, "triệu đồng")],
            [
                _mapping(
                    1092,
                    "FAMILY_TOTAL",
                    [_label(42, 97, "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RỦI RO")],
                    [_value(42, 104, "2.722")],
                    [_value(42, 105, "3.306")],
                    "SOLE_VISIBLE_CHILD_DEFINES_FAMILY_TOTAL",
                ),
                _mapping(
                    1099,
                    "OTHER_SMALL_NHNN_HOUSING_PROGRAMME",
                    [
                        _label(
                            42, 102, "Vốn nhận ủy thác từ NHNN theo Chương trình cho vay hỗ trợ"
                        ),
                        _label(42, 103, "nhà ở Nghị quyết số 02/NQ-CP do Chính phủ ban hành ngày"),
                        _label(42, 106, "7 tháng 1 năm 2013"),
                    ],
                    [_value(42, 104, "2.722")],
                    [_value(42, 105, "3.306")],
                    "OWNER_SMALL_UNLISTED_CHILD_TO_EXPLICIT_OTHER",
                ),
            ],
            [],
        ),
    ]
    if [item["bank_code"] for item in documents] != list(EXPECTED_DOCUMENT_ORDER):
        raise _error("review bank order drifted")
    return documents


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": _REVIEW_RUN_ID,
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": _REVIEW_STATE,
    }
    return {**material, "review_id": _REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex entrusted-capital pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    try:
        return foundation._document(items, code, label)
    except Exception as exc:
        raise _error(f"{label} document axis drifted: {exc}") from exc


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    try:
        return foundation._page(document, page_sequence, label)
    except Exception as exc:
        raise _error(f"{label} page axis drifted: {exc}") from exc


def _semantic_evidence(
    axis_page: Mapping[str, Any], semantic_page: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any]:
    try:
        return foundation._semantic_evidence(axis_page, semantic_page, item)
    except Exception as exc:
        raise _error(f"semantic/pixel evidence drifted: {exc}") from exc


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
        "bounded_report_absence_count": sum(
            trial["status"] == "NOT_OBSERVED_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["complete_region_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": sum(
            trial.get("source_period_status") == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "verified_document_count": sum(
            trial["status"].startswith("VERIFIED_BY_CODEX") for trial in trials
        ),
        "verified_value_cell_count": sum(
            len(value["components"])
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
    }


def _source_period_status(source_period: str) -> str:
    return (
        "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
        if source_period == "2026-03-31"
        else "VERIFIED_SOURCE_PERIOD_Q2_2026"
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("entrusted-capital result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != _RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("entrusted-capital result identity or metrics drifted")
    valid_statuses = {
        "NOT_OBSERVED_IN_BOUND_REPORT",
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
            or trial.get("status") not in valid_statuses
            or any(
                row.get("status") != "VERIFIED_BY_CODEX"
                for row in trial.get("verified_mappings", [])
            )
        ):
            raise _error("entrusted-capital trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != _RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("entrusted-capital result identity drifted")
    return canonical_clone_v1(value)


def build_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1(
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
    """Build the exact bounded eight-bank family result."""

    reviewed_documents = _review(review)["documents"]
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or structure_scan.get("metrics", {}).get("complete_region_count")
        != _EXPECTED_COMPLETE_REGION_COUNT
    ):
        raise _error("fixed semantic axis or structure scan identity drifted")
    trials: list[dict[str, Any]] = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(reviewed_documents, code, "pixel review")
        scan_trial = _document(structure_scan["trials"], code, "structure scan")
        axis_document = _document(axis["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        matcher = scan_trial["matcher_result"]
        if reviewed["disposition"] == "NOT_OBSERVED_IN_BOUND_REPORT":
            if matcher["regions"] or matcher["uniqueness"] != {
                "complete_region_count": 0,
                "status": "NOT_UNIQUE_FULL_MATCH",
            }:
                raise _error(f"{code} bounded absence contradicts complete-PDF scan")
            boundary = []
            for item in reviewed["boundary_evidence"]:
                axis_page = _page(axis_document, item["page_sequence"], "accounting axis")
                semantic_page = _page(semantic_document, item["page_sequence"], "semantic index")
                boundary.append(
                    {
                        "page_sequence": item["page_sequence"],
                        **_semantic_evidence(axis_page, semantic_page, item),
                    }
                )
            trials.append(
                {
                    "bound_report_absence_evidence": boundary,
                    "document_ordinal": ordinal,
                    "document_provenance": code,
                    "page_span": reviewed["page_span"],
                    "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                    "source_period": reviewed["source_period"],
                    "source_period_status": "VERIFIED_SOURCE_PERIOD_Q2_2026",
                    "status": "NOT_OBSERVED_IN_BOUND_REPORT",
                    "structure_graph_id": matcher["result_id"],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                    "whole_document_absence_scope": "THIS_BOUND_PDF_ONLY",
                    "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
                }
            )
            continue
        if (
            matcher["uniqueness"] != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or len(matcher["regions"]) != 1
            or matcher["regions"][0]["owner"]["page_sequence"] != reviewed["owner"]["page_sequence"]
            or matcher["regions"][0]["owner"]["source_line_index"]
            != reviewed["owner"]["line_index"]
        ):
            raise _error(f"{code} reviewed region is not the unique whole-PDF graph")
        page_sequence = reviewed["owner"]["page_sequence"]
        axis_page = _page(axis_document, page_sequence, "accounting axis")
        semantic_page = _page(semantic_document, page_sequence, "semantic index")
        crop_page = _page(crop_document, page_sequence, "crop manifest")
        try:
            source_texts = foundation.support._source_line_axis(crop_page)
        except Exception as exc:
            raise _error(f"{code} source line axis drifted: {exc}") from exc

        def evidence(
            item: Mapping[str, Any],
            *,
            page_sequence: int = page_sequence,
            axis_page: Mapping[str, Any] = axis_page,
            semantic_page: Mapping[str, Any] = semantic_page,
        ) -> dict[str, Any]:
            if item["page_sequence"] != page_sequence:
                raise _error("review evidence escaped the unique one-page region")
            return {
                "page_sequence": page_sequence,
                **_semantic_evidence(axis_page, semantic_page, item),
            }

        value_cache: dict[str, dict[str, Any]] = {}

        def verified(
            ref: Mapping[str, Any],
            *,
            value_cache: dict[str, dict[str, Any]] = value_cache,
            axis_page: Mapping[str, Any] = axis_page,
            semantic_page: Mapping[str, Any] = semantic_page,
            crop_page: Mapping[str, Any] = crop_page,
            source_texts: Sequence[str] = source_texts,
            page_sequence: int = page_sequence,
            code: str = code,
        ) -> dict[str, Any]:
            key = canonical_json_sha256_v1(ref)
            if key not in value_cache:
                try:
                    if ref["kind"] == "AUTHENTICATED_LINE":
                        item = foundation.support._source_value(
                            axis_page,
                            semantic_page,
                            crop_page,
                            source_texts,
                            {
                                "line_index": ref["line_index"],
                                "pixel_transcription": ref["pixel_transcription"],
                            },
                        )
                    elif ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH":
                        item = foundation._pixel_dash_value(crop_page, ref)
                    elif ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_NUMBER":
                        item = foundation._pixel_number_value(crop_page, ref)
                    else:
                        raise _error("reviewed numeric evidence kind drifted")
                except Exception as exc:
                    raise _error(f"{code} source numeric evidence drifted: {exc}") from exc
                value_cache[key] = {**item, "page_sequence": page_sequence}
            return canonical_clone_v1(value_cache[key])

        verified_mappings = []
        for mapping in reviewed["mappings"]:
            values = []
            for period_role in ("CURRENT", "COMPARATIVE"):
                components = [verified(item) for item in mapping["values"][period_role]]
                values.append(
                    {
                        "aggregation": (
                            "DIRECT_VISIBLE_VALUE"
                            if len(components) == 1
                            else "SUM_OF_VISIBLE_SOURCE_ROWS"
                        ),
                        "components": components,
                        "normalized_value": sum(item["normalized_value"] for item in components),
                        "period_role": period_role,
                    }
                )
            verified_mappings.append(
                {
                    "label_evidence": [evidence(item) for item in mapping["labels"]],
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
            terms = [verified(item) for item in equation["terms"]]
            total = verified(equation["total"])
            computed = sum(item["normalized_value"] for item in terms)
            if computed != total["normalized_value"]:
                raise _error(f"{code} entrusted-capital accounting equation does not close")
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "period_role": equation["period_role"],
                    "status": "VERIFIED_EXACT",
                    "term_source_line_indices": [item["source_line_index"] for item in terms],
                    "visible_total": total["normalized_value"],
                    "visible_total_source_line_index": total["source_line_index"],
                }
            )
        period_status = _source_period_status(reviewed["source_period"])
        trials.append(
            {
                "bound_report_absence_evidence": [],
                "document_ordinal": ordinal,
                "document_provenance": code,
                "owner_evidence": evidence(reviewed["owner"]),
                "page_span": reviewed["page_span"],
                "period_axis_evidence": [evidence(item) for item in reviewed["period_axis"]],
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": period_status,
                "status": (
                    "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
                    if period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                    else "VERIFIED_BY_CODEX"
                ),
                "structure_graph_id": matcher["result_id"],
                "unit_evidence": [evidence(item) for item in reviewed["unit_evidence"]],
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
                "visible_page_render_binding": canonical_clone_v1(crop_page["render_binding"]),
                "whole_document_absence_scope": None,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )
    schema_family = {
        "family_display_order_range": list(_FAMILY_DISPLAY_ORDER_RANGE),
        "family_root": _schema_binding(schema_by_id.get(1092), 1092),
        "mapped_report_norm_ids": sorted(
            {
                row["schema_binding"]["report_norm_id"]
                for trial in trials
                for row in trial["verified_mappings"]
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
        "state": _RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": _RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_entrusted_investment_risk_capital_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    review: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    structure_scan = scanner.build_entrusted_investment_risk_capital_full_document_scan_v1(
        semantic_index
    )
    rebuilt = build_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1(
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
        raise _error("entrusted-capital verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    try:
        return foundation._stable_json(path, expected_sha256)
    except Exception as exc:
        raise _error(f"fixed JSON drifted: {path}: {exc}") from exc


def build_live_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review, review_sha = _stable_json(REVIEW_PATH)
    structure_scan = scanner.build_entrusted_investment_risk_capital_full_document_scan_v1(
        semantic_index
    )
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    result = build_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    return validate_entrusted_investment_risk_capital_8bank_codex_verified_mapping_replay_v1(
        result,
        semantic_index,
        crop_manifest,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_entrusted_investment_risk_capital_8bank_codex_verified_mapping_replay_v1(
        value,
        semantic_index,
        crop_manifest,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def _write(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes_v1(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    if args.write_review and args.validate is not None:
        parser.error("--write-review and --validate are mutually exclusive")
    if args.write_review:
        _write(args.output, _review_blueprint())
        return
    if args.validate is not None:
        value, _ = _stable_json(args.validate)
        result = validate_live_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1(
            value
        )
        sys.stdout.write(result["result_id"] + "\n")
        return
    result = build_live_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1()
    _write(args.output, result)
    sys.stdout.write(result["result_id"] + "\n")


if __name__ == "__main__":
    main()
