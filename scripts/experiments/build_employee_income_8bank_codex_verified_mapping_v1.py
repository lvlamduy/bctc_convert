"""Verify employee-income disclosures across eight reports."""

from __future__ import annotations

import argparse
import decimal
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
        raise RuntimeError(f"cannot load employee-income support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


other = _load(
    "other_activity_support_for_employee_income",
    "build_other_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load(
    "employee_income_scan_for_verified_mapping",
    "scan_employee_income_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "EMPLOYEE_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "EMPLOYEE_INCOME_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "EMPLOYEE_INCOME_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "e0094:result:"
REVIEW_STATE = "EMPLOYEE_INCOME_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "e0094:pixel-review:"
FAMILY_END_DISPLAY_ORDER = 844
SOURCE_PERIOD_STATUS_BY_PERIOD = {
    "2026-03-31": "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2",
    "2026-06-30": "VERIFIED_SOURCE_PERIOD_Q2_2026",
}
EXPECTED_RESULT_ID: str | None = (
    "e0094:result:30d685720a7731428e48bb664bb8630ddc0896f6da0537cb645d9fd2cdfa51a4"
)
ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = True
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_EMPLOYEE_"
    "INCOME_GRAPH_VISIBLE_PDF_SOURCE_NUMERIC_CHALLENGER_PERIOD_UNIT_TOTAL_"
    "AND_AVERAGE_ACCOUNTING_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0094-employee-income-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0094-employee-income-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = other.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = other.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = other.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = other.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "eifdsv1:scan:5dfff447332d007ecb53e54e0a45992c295552e1844c29ffcfa6e5411f3f38ec"

_SCHEMA_EXPECTED = {
    1259: ("IV. MỘT SỐ THÔNG TIN KHÁC", None, 835),
    1260: ("Thu nhập nhân viên của ngân hàng", 1259, 836),
    1261: ("Số lượng nhân viên", 1260, 837),
    1262: ("Thu nhập nhân viên", 1260, 838),
    1263: ("Tổng quỹ lương", 1260, 839),
    1264: ("Thưởng", 1260, 840),
    1265: ("Thu nhập khác", 1260, 841),
    1266: ("Tổng thu nhập", 1260, 842),
    1267: ("Lương bình quân người/tháng", 1260, 843),
    1268: ("Thu nhập bình quân người/tháng", 1260, 844),
}
_AUTHORITY = {
    "acb_period_average_forced_into_monthly_schema": False,
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_employee_income_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_period_average_rows_retained_unmapped": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
}
_FIELDS = {
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


class EmployeeIncome8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, values, averages, schema or result drifted."""


def _error(message: str) -> EmployeeIncome8BankCodexVerifiedMappingV1Error:
    return EmployeeIncome8BankCodexVerifiedMappingV1Error(message)


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


def _ref(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str) -> dict[str, Any]:
    return {"kind": "AUTHENTICATED_LINE", **_ref(page, line, text)}


def _decimal_line(page: int, line: int, text: str) -> dict[str, Any]:
    return {"kind": "AUTHENTICATED_DECIMAL_LINE", **_ref(page, line, text)}


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
    report_norm_id_not_used: int,
    page: int,
    label: tuple[int, str],
    current: Mapping[str, Any],
    comparative: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "labels": [_ref(page, label[0], label[1])],
        "nearest_schema_report_norm_id_not_used": report_norm_id_not_used,
        "reason": "SOURCE_IS_PER_EMPLOYEE_FOR_REPORTING_PERIOD_NOT_PER_EMPLOYEE_PER_MONTH",
        "role": role,
        "row_id": row_id,
        "values": {
            "COMPARATIVE_PERIOD": canonical_clone_v1(comparative),
            "CURRENT_PERIOD": canonical_clone_v1(current),
        },
    }


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_note_complete_region_count": 0,
            "reason": (
                "No employee-income table with average employee count, income or income "
                "components, average income, period axes and unit was found; severance-policy "
                "average-salary text and isolated employee counts do not qualify."
            ),
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "equations": [],
        "mappings": [],
        "owner": [],
        "page_span": None,
        "period_axis": [],
        "presentation": "NO_DETAILED_EMPLOYEE_INCOME_NOTE_IN_BOUND_REPORT",
        "ratio_equations": [],
        "source_only_rows": [],
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    page = 26
    documents = [
        {
            "absence_evidence": None,
            "bank_code": "ACB",
            "equations": [
                {
                    "name": "SALARY_PLUS_OTHER_EQUALS_TOTAL_INCOME",
                    "parent_role": "TOTAL_INCOME",
                    "term_roles": ["SALARY_FUND", "OTHER_INCOME"],
                }
            ],
            "mappings": [
                _mapping(
                    "EMPLOYEE_COUNT",
                    1261,
                    page,
                    [(12, "Số lượng nhân viên bình quân (người)")],
                    _line(page, 13, "13.345"),
                    _line(page, 14, "13.311"),
                ),
                _mapping(
                    "SALARY_FUND",
                    1263,
                    page,
                    [(16, "Tổng quỹ lương")],
                    _line(page, 17, "1.201.387"),
                    _line(page, 18, "1.138.693"),
                ),
                _mapping(
                    "OTHER_INCOME",
                    1265,
                    page,
                    [(19, "Thu nhập khác")],
                    _line(page, 20, "2.041.063"),
                    _line(page, 21, "2.152.974"),
                ),
                _mapping(
                    "TOTAL_INCOME",
                    1266,
                    page,
                    [(22, "Tổng thu nhập")],
                    _line(page, 23, "3.242.450"),
                    _line(page, 24, "3.291.667"),
                ),
            ],
            "owner": [_ref(page, 5, "TÌNH HÌNH THU NHẬP CỦA NHÂN VIÊN")],
            "page_span": [page, page],
            "period_axis": [_ref(page, 8, "30.6.2026"), _ref(page, 9, "30.6.2025")],
            "presentation": "PERIOD_AVERAGE_ROWS_WITH_COMPONENT_INCOME",
            "ratio_equations": [
                ["EI-001", "SALARY_FUND", "EMPLOYEE_COUNT", 1, 0],
                ["EI-002", "TOTAL_INCOME", "EMPLOYEE_COUNT", 1, 0],
            ],
            "source_only_rows": [
                _source_only(
                    "EI-001",
                    "AVERAGE_SALARY_PER_REPORTING_PERIOD",
                    1267,
                    page,
                    (25, "Tiền lương bình quân"),
                    _line(page, 26, "90"),
                    _line(page, 27, "86"),
                ),
                _source_only(
                    "EI-002",
                    "AVERAGE_INCOME_PER_REPORTING_PERIOD",
                    1268,
                    page,
                    (28, "Thu nhập bình quân"),
                    _line(page, 29, "243"),
                    _line(page, 30, "247"),
                ),
            ],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(page, 10, "Triệu đồng"), _ref(page, 11, "Triệu đồng")],
        },
        _absence("MBB"),
        {
            "absence_evidence": None,
            "bank_code": "VPB",
            "equations": [
                {
                    "name": "SALARY_PLUS_OTHER_EQUALS_TOTAL_INCOME",
                    "parent_role": "TOTAL_INCOME",
                    "term_roles": ["SALARY_FUND", "OTHER_INCOME"],
                }
            ],
            "mappings": [
                _mapping(
                    "EMPLOYEE_COUNT",
                    1261,
                    66,
                    [(75, "Tổng số nhân viên bình quân (người)")],
                    _line(66, 77, "28.907"),
                    _line(66, 78, "27.351"),
                ),
                _mapping(
                    "SALARY_FUND",
                    1263,
                    66,
                    [(80, "Tiền lương")],
                    _line(66, 81, "2.441.214"),
                    _line(66, 82, "2.485.985"),
                ),
                _mapping(
                    "OTHER_INCOME",
                    1265,
                    66,
                    [(83, "Thu nhập khác")],
                    _line(66, 84, "263.558"),
                    _line(66, 85, "218.423"),
                ),
                _mapping(
                    "TOTAL_INCOME",
                    1266,
                    66,
                    [(86, "Tổng thu nhập")],
                    _line(66, 87, "2.704.772"),
                    _line(66, 88, "2.704.408"),
                ),
                _mapping(
                    "AVERAGE_SALARY_MONTH",
                    1267,
                    66,
                    [(89, "Tiền lương bình quân tháng")],
                    _decimal_line(66, 90, "28.15"),
                    _decimal_line(66, 91, "30.30"),
                ),
                _mapping(
                    "AVERAGE_INCOME_MONTH",
                    1268,
                    66,
                    [(92, "Thu nhập bình quân tháng")],
                    _decimal_line(66, 93, "31.19"),
                    _decimal_line(66, 94, "32.96"),
                ),
            ],
            "owner": [_ref(66, 64, "TÌNH HÌNH THU NHẬP CỦA NHÂN VIÊN")],
            "page_span": [66, 66],
            "period_axis": [
                _ref(66, 71, "năm 2026"),
                _ref(66, 72, "năm 2025"),
            ],
            "presentation": "MONTHLY_AVERAGES_WITH_COMPONENT_INCOME",
            "ratio_equations": [
                ["AVERAGE_SALARY_MONTH", "SALARY_FUND", "EMPLOYEE_COUNT", 3, 2],
                ["AVERAGE_INCOME_MONTH", "TOTAL_INCOME", "EMPLOYEE_COUNT", 3, 2],
            ],
            "source_only_rows": [],
            "source_period": "2026-03-31",
            "unit_evidence": [_ref(66, 73, "Triệu đồng"), _ref(66, 74, "Triệu đồng")],
        },
        _absence("HDB"),
        _absence("VCB"),
        _absence("CTG"),
        _absence("BID"),
        {
            "absence_evidence": None,
            "bank_code": "VIB",
            "equations": [],
            "mappings": [
                _mapping(
                    "EMPLOYEE_COUNT",
                    1261,
                    49,
                    [(12, "Bình quân số cán bộ, nhân viên (người)")],
                    _line(49, 13, "9.893"),
                    _line(49, 14, "11.048"),
                ),
                _mapping(
                    "EMPLOYEE_INCOME",
                    1262,
                    49,
                    [(15, "Thu nhập của cán bộ, nhân viên")],
                    _line(49, 16, "2.148.224"),
                    _line(49, 17, "2.319.989"),
                ),
                _mapping(
                    "AVERAGE_INCOME_MONTH",
                    1268,
                    49,
                    [(18, "Thu nhập bình quân/tháng")],
                    _decimal_line(49, 19, "36,19"),
                    _decimal_line(49, 20, "35,00"),
                ),
            ],
            "owner": [_ref(49, 5, "TÌNH HÌNH THU NHẬP CỦA CÁN BỘ NHÂN VIÊN")],
            "page_span": [49, 49],
            "period_axis": [
                _ref(49, 8, "năm 2026"),
                _ref(49, 9, "năm 2025"),
            ],
            "presentation": "DIRECT_EMPLOYEE_INCOME_WITH_MONTHLY_AVERAGE",
            "ratio_equations": [
                ["AVERAGE_INCOME_MONTH", "EMPLOYEE_INCOME", "EMPLOYEE_COUNT", 6, 2]
            ],
            "source_only_rows": [],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(49, 10, "triệu đồng"), _ref(49, 11, "triệu đồng")],
        },
    ]
    return documents


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "state": REVIEW_STATE,
    }
    return {
        **material,
        "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material),
    }


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("employee-income pixel review drifted")
    return canonical_clone_v1(value)


def _decimal_value(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    ref: Mapping[str, Any],
) -> dict[str, Any]:
    line_ref = {**ref, "kind": "AUTHENTICATED_LINE"}
    evidence = other._verified_value(axis_document, semantic_document, crop_document, line_ref)
    raw = ref["pixel_transcription"].replace(",", ".")
    try:
        value = decimal.Decimal(raw)
    except decimal.InvalidOperation as exc:
        raise _error("employee-income decimal value is invalid") from exc
    proposal = evidence["fresh_vietocr_numeric_proposal"]
    if type(proposal) is not str:
        raise _error("employee-income decimal proposal is missing")
    try:
        proposal_value = decimal.Decimal(proposal.replace(",", "."))
    except decimal.InvalidOperation:
        proposal_value = None
    evidence.pop("normalized_value")
    return {
        **evidence,
        "decimal_scale": 2,
        "fresh_vietocr_numeric_status": (
            "MATCHES_SOURCE_NUMERIC_CHALLENGER"
            if proposal_value == value
            else "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
        ),
        "normalized_decimal_value": format(value, ".2f"),
    }


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "detailed_note_not_present_document_count": sum(
            trial["status"] == "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT"
            for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(trial["page_span"] is not None for trial in trials),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": sum(len(trial["verified_source_only_rows"]) for trial in trials),
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "verified_value_cell_count": sum(
            len(mapping["values"]) for trial in trials for mapping in trial["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("employee-income result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("employee-income result identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material) or (
        EXPECTED_RESULT_ID is not None and identity != EXPECTED_RESULT_ID
    ):
        raise _error("employee-income result ID drifted")
    return canonical_clone_v1(value)


def build_employee_income_8bank_codex_verified_mapping_v1(
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
    scanner.validate_employee_income_full_document_scan_replay_v1(structure_scan, semantic_index)
    if (
        axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256
        or structure_scan["scan_id"] != EXPECTED_SCAN_ID
        or type(crop_manifest) is not dict
    ):
        raise _error("employee-income fixed inputs drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = other._document(reviewed_documents, code, "pixel review")
        scan_trial = other._document(structure_scan["trials"], code, "structure scan")
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
                raise _error("absent employee-income note unexpectedly matched")
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
        if (
            matcher["uniqueness"] != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or matcher["regions"][0]["page_span"] != reviewed["page_span"]
        ):
            raise _error("reviewed employee-income region is not unique")
        axis_document = other._document(axis["documents"], code, "accounting axis")
        semantic_document = other._document(semantic_index["documents"], code, "semantic index")
        crop_document = other._document(crop_manifest["documents"], code, "crop manifest")

        def verified(
            ref: Mapping[str, Any],
            *,
            axis_document: Mapping[str, Any] = axis_document,
            semantic_document: Mapping[str, Any] = semantic_document,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> dict[str, Any]:
            if ref["kind"] == "AUTHENTICATED_DECIMAL_LINE":
                return _decimal_value(axis_document, semantic_document, crop_document, ref)
            return other._verified_value(axis_document, semantic_document, crop_document, ref)

        mappings = []
        source_only = []
        by_role: dict[str, dict[str, Any]] = {}
        mapped_ids = set()
        for mapping in reviewed["mappings"]:
            derived = mapping.get("derived_monthly")
            if derived is not None:
                values = []
                for axis_role in ("COMPARATIVE_PERIOD", "CURRENT_PERIOD"):
                    numerator = next(
                        value
                        for value in by_role[derived["numerator_role"]]["values"]
                        if value["axis_role"] == axis_role
                    )["normalized_value"]
                    denominator = next(
                        value
                        for value in by_role[derived["denominator_role"]]["values"]
                        if value["axis_role"] == axis_role
                    )["normalized_value"]
                    if denominator <= 0 or type(derived["months"]) is not int:
                        raise _error("employee-income derived average denominator drifted")
                    printed = verified(derived["printed_annual_values"][axis_role])
                    computed_annual = (
                        decimal.Decimal(numerator) / decimal.Decimal(denominator)
                    ).quantize(decimal.Decimal("1"), rounding=decimal.ROUND_HALF_UP)
                    if computed_annual != decimal.Decimal(printed["normalized_value"]):
                        raise _error("employee-income printed annual average does not corroborate")
                    places = derived["decimal_places"]
                    quant = decimal.Decimal(1).scaleb(-places)
                    computed_monthly = (
                        decimal.Decimal(numerator)
                        / decimal.Decimal(denominator * derived["months"])
                    ).quantize(quant, rounding=decimal.ROUND_HALF_UP)
                    values.append(
                        {
                            "axis_role": axis_role,
                            "derivation": {
                                "denominator_role": derived["denominator_role"],
                                "months_in_source_period": derived["months"],
                                "numerator_role": derived["numerator_role"],
                                "printed_annual_average_corroborated": True,
                            },
                            "normalized_decimal_value": format(computed_monthly, f".{places}f"),
                            "printed_annual_average_evidence": printed,
                        }
                    )
            else:
                values = [
                    {"axis_role": axis_role, **verified(ref)}
                    for axis_role, ref in mapping["values"].items()
                ]
            item = {
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in mapping["labels"]
                ],
                "role": mapping["role"],
                "schema_binding": _schema_binding(
                    schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                ),
                "status": "VERIFIED_BY_CODEX",
                "topology": mapping["topology"],
                "values": values,
            }
            mappings.append(item)
            by_role[item["role"]] = item
            mapped_ids.add(mapping["report_norm_id"])
        for row in reviewed["source_only_rows"]:
            item = {
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in row["labels"]
                ],
                "nearest_schema_report_norm_id_not_used": row[
                    "nearest_schema_report_norm_id_not_used"
                ],
                "reason": row["reason"],
                "role": row["role"],
                "row_id": row["row_id"],
                "status": "UNRESOLVED_SCHEMA_PERIOD_SEMANTICS_SOURCE_ROW_RETAINED",
                "values": [
                    {"axis_role": axis_role, **verified(ref)}
                    for axis_role, ref in row["values"].items()
                ],
            }
            source_only.append(item)
            by_role[row["row_id"]] = item
        equations = []
        for specification in reviewed["equations"]:
            for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
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
                computed = sum(value["normalized_value"] for value in terms)
                if computed != parent["normalized_value"]:
                    raise _error("employee-income additive equation does not close")
                equations.append(
                    {
                        "axis_role": axis_role,
                        "computed_value": computed,
                        "name": specification["name"],
                        "status": "VERIFIED_EXACT",
                        "visible_value": parent["normalized_value"],
                    }
                )
        for target_role, numerator_role, denominator_role, months, places in reviewed[
            "ratio_equations"
        ]:
            for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
                target = next(
                    value
                    for value in by_role[target_role]["values"]
                    if value["axis_role"] == axis_role
                )
                numerator = next(
                    value
                    for value in by_role[numerator_role]["values"]
                    if value["axis_role"] == axis_role
                )["normalized_value"]
                denominator = next(
                    value
                    for value in by_role[denominator_role]["values"]
                    if value["axis_role"] == axis_role
                )["normalized_value"]
                computed = decimal.Decimal(numerator) / decimal.Decimal(denominator * months)
                quant = decimal.Decimal(1).scaleb(-places)
                computed = computed.quantize(quant, rounding=decimal.ROUND_HALF_UP)
                visible_text = (
                    target["normalized_decimal_value"]
                    if "normalized_decimal_value" in target
                    else str(target["normalized_value"])
                )
                visible = decimal.Decimal(visible_text)
                if computed != visible:
                    raise _error("employee-income average equation does not close")
                equations.append(
                    {
                        "axis_role": axis_role,
                        "computed_decimal_value": format(computed, f".{places}f"),
                        "months_in_source_period": months,
                        "name": "INCOME_OR_SALARY_DIVIDED_BY_EMPLOYEES_AND_MONTHS",
                        "status": "VERIFIED_EXACT",
                        "target_role": target_role,
                        "visible_decimal_value": format(visible, f".{places}f"),
                    }
                )
        period_status = SOURCE_PERIOD_STATUS_BY_PERIOD.get(reviewed["source_period"])
        if period_status is None:
            raise _error("reviewed employee-income source period is unsupported")
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "mapped_report_norm_ids": sorted(mapped_ids),
                "owner_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["owner"]
                ],
                "page_span": list(reviewed["page_span"]),
                "period_axis_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["period_axis"]
                ],
                "presentation": reviewed["presentation"],
                "source_geometry_mode": other._page(
                    semantic_document, reviewed["page_span"][0], "semantic index"
                )["geometry_mode"],
                "source_period": reviewed["source_period"],
                "source_period_status": period_status,
                "status": (
                    "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
                    if period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                    else "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SOURCE_PERIOD_AVERAGES"
                    if source_only
                    else "VERIFIED_BY_CODEX"
                ),
                "unit_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": mappings,
                "verified_source_only_rows": source_only,
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
            "family_root": _schema_binding(schema_by_id.get(1260), 1260),
            "mapped_report_norm_ids": mapped_union,
            "section_root": _schema_binding(schema_by_id.get(1259), 1259),
        },
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def _stable_json(path: Path) -> tuple[dict[str, Any], str]:
    support = scanner._support()._support()
    raw = support._stable_bytes(path)
    return support._strict_json(raw, path.as_posix()), hashlib.sha256(raw).hexdigest()


def _live_inputs() -> dict[str, Any]:
    semantic_index, index_sha = _stable_json(SEMANTIC_INDEX_PATH)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH)
    review, review_sha = _stable_json(REVIEW_PATH)
    if index_sha != EXPECTED_INDEX_SHA256 or crop_sha != EXPECTED_CROP_MANIFEST_SHA256:
        raise _error("employee-income fixed input hash drifted")
    scan = scanner.build_employee_income_full_document_scan_v1(semantic_index)
    authority, by_id = _authority_snapshot(PROJECT_ROOT)
    for report_norm_id, (name, parent, display_order) in _SCHEMA_EXPECTED.items():
        item = by_id.get(report_norm_id)
        if (
            item is None
            or item.canonical_name != name
            or item.parent_id != parent
            or (not ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT and item.display_order != display_order)
            or item.statement_type != "TM"
        ):
            raise _error(f"employee-income live schema drifted: {report_norm_id}")
    if ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT:
        persisted_result, _ = _stable_json(RESULT_PATH)
        persisted_result = _validate_result(persisted_result)
        authority = canonical_clone_v1(persisted_result["input_refs"]["schema_authority"])
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "review": review,
        "review_sha256": review_sha,
        "schema_authority": authority,
        "schema_by_id": by_id,
        "semantic_index": semantic_index,
        "structure_scan": scan,
    }


def build_live_employee_income_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_employee_income_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_employee_income_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_employee_income_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("employee-income result does not replay exactly")
    return supplied


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
        _write(RESULT_PATH, build_live_employee_income_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        value, _ = _stable_json(RESULT_PATH)
        validate_live_employee_income_8bank_codex_verified_mapping_v1(value)


if __name__ == "__main__":
    main()
