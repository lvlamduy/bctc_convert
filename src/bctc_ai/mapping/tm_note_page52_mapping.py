"""Hierarchy-safe promoted-schema mapping for MBB consolidated TM page 52."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.schema.registry import SchemaItem
from bctc_ai.tables.tm_note_page52 import ParsedTMPage52

TM_PAGE52_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page52-v1.yaml")
TM_PAGE52_SCHEMA_TOTAL = 1_717
TM_PAGE52_SCOPE_SCHEMA_COUNT = 19
TM_PAGE52_SCHEMA_RECONCILED_COUNT = 19
TM_PAGE52_MAPPED_SCHEMA_COUNT = 14
TM_PAGE52_VALUE_BEARING_MAPPED_SCHEMA_COUNT = 10
TM_PAGE52_NOT_OBSERVED_SCHEMA_COUNT = 5
TM_PAGE52_SCHEMA_UNASSESSED_COUNT = 1_698
TM_PAGE52_SOURCE_ROW_COUNT = 6
TM_PAGE52_MAPPED_SOURCE_ROW_COUNT = 5
TM_PAGE52_SOURCE_ONLY_ROW_COUNT = 1
TM_PAGE52_FINANCIAL_SLOT_COUNT = 12
TM_PAGE52_VALUE_COUNT = 12
TM_PAGE52_DASH_COUNT = 0
TM_PAGE52_MAPPED_ASSIGNMENT_COUNT = 12
TM_PAGE52_NARRATIVE_RECORD_COUNT = 3
TM_PAGE52_NARRATIVE_QUANTITY_COUNT = 3
TM_PAGE52_VALIDATION_CHECK_COUNT = 6
TM_PAGE52_VALIDATION_PASS_COUNT = 6
TM_PAGE52_VALIDATION_NOT_TESTABLE_COUNT = 0

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EXISTING_BRANCH_IDS = set(range(759, 766))
_PROMOTED_IDS = set(range(5750, 5762))
_SCOPED_IDS = _EXISTING_BRANCH_IDS | _PROMOTED_IDS
_NOT_OBSERVED_IDS = set(range(760, 765))
_MAPPED_IDS = _SCOPED_IDS - _NOT_OBSERVED_IDS
_VALUE_BEARING_MAPPED_IDS = {765, 5750, 5751, 5752, 5754, 5755, 5757, 5758, 5760, 5761}
_STRUCTURAL_ONLY_MAPPED_IDS = _MAPPED_IDS - _VALUE_BEARING_MAPPED_IDS
_EXTERNAL_OWNER_IDS = {716, 1055, 1295}
_SCHEMA_SCOPE_SHA256 = "75b34cbba52c86f642a6fe03dd2af7bfd3ee18d918e2cd6e47ad1aa480343146"
_EXPECTED_FORMULAS = {
    5750: (5751,),
    759: (5752, 765),
    5753: (5754, 5755),
    5756: (5757, 5758),
    5759: (5760, 5761),
}
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
    "accounting_equation_result_as_extracted_value",
    "narrative_quantity_as_schema_value",
    "schema_id_outside_page52_scope",
    "silent_mapping_to_semantically_adjacent_existing_item",
}


class TMPage52MappingError(ValueError):
    pass


class TMPage52RuleDisposition(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


class TMPage52SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage52SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


@dataclass(frozen=True)
class TMPage52RowRule:
    table_key: str
    ordinal: int
    visible_label_anchor: str
    expected_row_kind: str
    expected_source_role: str
    expected_observations: tuple[str, ...]
    disposition: TMPage52RuleDisposition
    report_norm_ids: tuple[int, ...]
    question_required: bool


@dataclass(frozen=True)
class TMPage52StructuralRule:
    structural_key: str
    source_kind: str
    axis_key: str
    report_norm_id: int
    disposition: str
    owner_scope: str


@dataclass(frozen=True)
class TMPage52StructuralDisposition:
    structural_key: str
    source_kind: str
    axis_key: str
    status: str
    report_norm_id: int
    canonical_name: str
    owner_scope: str
    source_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage52ExternalOwnerValidationRule:
    validation_key: str
    axis_key: str
    owner_report_norm_ids: tuple[int, ...]
    owner_scopes: tuple[str, ...]
    owner_values: tuple[Decimal, ...]
    target_report_norm_id: int


@dataclass(frozen=True)
class TMPage52MappingPolicy:
    source_path: Path
    document: str
    page_number: int
    page_tag: str
    report_scope: str
    mapping_authority_scope: str
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    upstream_ocr_sha256: str
    schema_workbook_sha256: str
    schema_total: int
    scope_schema_ids: tuple[int, ...]
    schema_scope_sha256: str
    minimum_visible_label_similarity: float
    rows: tuple[TMPage52RowRule, ...]
    structural_mappings: tuple[TMPage52StructuralRule, ...]
    validation_formulas: tuple[tuple[int, tuple[int, ...]], ...]
    external_owner_validations: tuple[TMPage52ExternalOwnerValidationRule, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage52SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage52SourceDisposition:
    row_id: str
    table_key: str
    ordinal: int
    visible_label: str
    row_kind: str
    source_role: str
    status: str
    report_norm_ids: tuple[int, ...]
    visible_label_similarity: float
    observations: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    period_starts: tuple[str | None, ...]
    period_ends: tuple[str | None, ...]
    period_roles: tuple[str | None, ...]
    unit: str
    unit_multiplier: int
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage52MappedAssignment:
    source_row_id: str
    table_key: str
    source_role: str
    cell_index: int
    report_norm_id: int
    observation: str
    value: Decimal
    period_start: str
    period_end: str
    period_role: str
    unit: str
    unit_multiplier: int
    mapping_basis: str


@dataclass(frozen=True)
class TMPage52ValidationCheck:
    check_id: str
    axis_role: str
    status: str
    expected_value: Decimal
    observed_value: Decimal | None
    residual: Decimal | None
    target_report_norm_id: int
    external_owner_report_norm_ids: tuple[int, ...]
    external_owner_scopes: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage52MappingResult:
    statement_type: str
    document: str
    page_number: int
    page_tag: str
    report_scope: str
    status: str
    mapping_authority_scope: str
    mapping_authority_granted: bool
    schema_item_count: int
    status_reconciled_schema_count: int
    mapped_schema_count: int
    value_bearing_mapped_schema_count: int
    not_observed_schema_count: int
    not_applicable_schema_count: int
    ambiguous_schema_count: int
    unresolved_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    source_only_row_count: int
    source_question_row_count: int
    ambiguous_source_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_assignment_count: int
    narrative_record_count: int
    narrative_quantity_count: int
    validation_check_count: int
    validation_pass_count: int
    validation_not_testable_count: int
    schema_dispositions: tuple[TMPage52SchemaDisposition, ...]
    source_dispositions: tuple[TMPage52SourceDisposition, ...]
    structural_dispositions: tuple[TMPage52StructuralDisposition, ...]
    mapped_assignments: tuple[TMPage52MappedAssignment, ...]
    validation_checks: tuple[TMPage52ValidationCheck, ...]
    validation_formulas: tuple[tuple[int, tuple[int, ...]], ...]
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    upstream_ocr_sha256: str
    schema_workbook_sha256: str
    schema_projection_sha256: str
    policy_sha256: str
    mapping_inputs: tuple[str, ...]


def _positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TMPage52MappingError(f"invalid positive TM page-52 field: {field}")
    return value


def _int_list(value: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise TMPage52MappingError(f"TM page-52 {field} is invalid")
    return tuple(value)


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise TMPage52MappingError(f"TM page-52 {field} is invalid")
    return tuple(value)


def _load_formulas(value: Any) -> tuple[tuple[int, tuple[int, ...]], ...]:
    if not isinstance(value, dict):
        raise TMPage52MappingError("TM page-52 validation formulas are invalid")
    formulas = []
    for target, terms in value.items():
        if isinstance(target, bool) or not isinstance(target, int):
            raise TMPage52MappingError("TM page-52 formula target is invalid")
        formulas.append((target, _int_list(terms, "formula terms")))
    return tuple(formulas)


def load_tm_page52_mapping_policy(path: Path) -> TMPage52MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage52MappingError(f"cannot load TM page-52 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE52_PROMOTED_SCHEMA_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 52
        or payload.get("page_tag") != "page-0052"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage52MappingError("TM page-52 mapping identity drifted")
    hash_fields = (
        "source_pdf_sha256",
        "source_render_sha256",
        "source_ocr_sha256",
        "upstream_ocr_sha256",
        "schema_workbook_sha256",
    )
    hashes = tuple(payload.get(field) for field in hash_fields)
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage52MappingError("TM page-52 mapping hashes are invalid")
    schema_total = _positive_int(payload, "schema_total")
    if schema_total != TM_PAGE52_SCHEMA_TOTAL:
        raise TMPage52MappingError("TM page-52 schema denominator drifted")
    if (
        payload.get("scope_schema_ids")
        != [{"start": 759, "end": 765}, {"start": 5750, "end": 5761}]
        or payload.get("scope_schema_total") != TM_PAGE52_SCOPE_SCHEMA_COUNT
        or payload.get("schema_scope_sha256") != _SCHEMA_SCOPE_SHA256
    ):
        raise TMPage52MappingError("TM page-52 schema scope drifted")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 <= threshold <= 1
    ):
        raise TMPage52MappingError("TM page-52 label threshold is invalid")

    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE52_SOURCE_ROW_COUNT:
        raise TMPage52MappingError("TM page-52 row rules are incomplete")
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage52MappingError("TM page-52 row rule is invalid")
        try:
            disposition = TMPage52RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMPage52MappingError("TM page-52 row disposition is invalid") from exc
        ordinal = record.get("ordinal")
        anchor = record.get("visible_label_anchor")
        question = record.get("question_required")
        if (
            isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal <= 0
            or not isinstance(anchor, str)
            or not isinstance(question, bool)
            or question
        ):
            raise TMPage52MappingError("TM page-52 row rule fields are invalid")
        rows.append(
            TMPage52RowRule(
                table_key=str(record.get("table_key", "")),
                ordinal=ordinal,
                visible_label_anchor=retrieval_key(anchor),
                expected_row_kind=str(record.get("expected_row_kind", "")),
                expected_source_role=str(record.get("expected_source_role", "")),
                expected_observations=_string_list(
                    record.get("expected_observations"), "expected observations"
                ),
                disposition=disposition,
                report_norm_ids=_int_list(
                    record.get("report_norm_ids"),
                    "report_norm_ids",
                    allow_empty=True,
                ),
                question_required=False,
            )
        )
    expected_row_keys = (
        ("RELATED_PARTY_BALANCES", 1),
        ("RELATED_PARTY_BALANCES", 2),
        ("RELATED_PARTY_BALANCES", 3),
        ("GEOGRAPHIC_CONCENTRATION", 1),
        ("GEOGRAPHIC_CONCENTRATION", 2),
        ("GEOGRAPHIC_CONCENTRATION", 3),
    )
    if tuple((row.table_key, row.ordinal) for row in rows) != expected_row_keys:
        raise TMPage52MappingError("TM page-52 row order drifted")
    if tuple(row.report_norm_ids for row in rows) != (
        (5750,),
        (5751, 5751),
        (5750, 5750),
        (),
        (5752, 5754, 5757, 5760),
        (765, 5755, 5758, 5761),
    ):
        raise TMPage52MappingError("TM page-52 promoted row targets drifted")

    raw_structural = payload.get("structural_mappings")
    if not isinstance(raw_structural, list) or len(raw_structural) != 7:
        raise TMPage52MappingError("TM page-52 structural mappings are incomplete")
    structural = []
    for record in raw_structural:
        if not isinstance(record, dict):
            raise TMPage52MappingError("TM page-52 structural mapping is invalid")
        structural.append(
            TMPage52StructuralRule(
                structural_key=str(record.get("structural_key", "")),
                source_kind=str(record.get("source_kind", "")),
                axis_key=str(record.get("axis_key", "")),
                report_norm_id=_positive_int(record, "report_norm_id"),
                disposition=str(record.get("disposition", "")),
                owner_scope=str(record.get("owner_scope", "")),
            )
        )
    if tuple(item.report_norm_id for item in structural) != (
        716,
        759,
        1055,
        5753,
        1295,
        5756,
        5759,
    ) or {(item.report_norm_id, item.disposition, item.owner_scope) for item in structural} != {
        (716, "EXTERNAL_OWNER_VALIDATION", "page-0031"),
        (759, "MAPPED_AUTOMATIC_SCOPED", "page-0052"),
        (1055, "EXTERNAL_OWNER_VALIDATION", "page-0043"),
        (5753, "MAPPED_AUTOMATIC_SCOPED", "page-0052"),
        (1295, "EXTERNAL_OWNER_VALIDATION", "page-0051"),
        (5756, "MAPPED_AUTOMATIC_SCOPED", "page-0052"),
        (5759, "MAPPED_AUTOMATIC_SCOPED", "page-0052"),
    }:
        raise TMPage52MappingError("TM page-52 structural ownership drifted")

    formulas = _load_formulas(payload.get("validation_formulas"))
    if dict(formulas) != _EXPECTED_FORMULAS:
        raise TMPage52MappingError("TM page-52 validation formulas drifted")

    raw_external = payload.get("external_owner_validations")
    if not isinstance(raw_external, list) or len(raw_external) != 4:
        raise TMPage52MappingError("TM page-52 external-owner validations are incomplete")
    external = []
    for record in raw_external:
        if not isinstance(record, dict):
            raise TMPage52MappingError("TM page-52 external-owner validation is invalid")
        ids = _int_list(record.get("owner_report_norm_ids"), "owner_report_norm_ids")
        scopes = _string_list(record.get("owner_scopes"), "owner_scopes")
        values = _int_list(record.get("owner_values"), "owner_values")
        if not (len(ids) == len(scopes) == len(values)):
            raise TMPage52MappingError("TM page-52 external-owner axes are not parallel")
        external.append(
            TMPage52ExternalOwnerValidationRule(
                validation_key=str(record.get("validation_key", "")),
                axis_key=str(record.get("axis_key", "")),
                owner_report_norm_ids=ids,
                owner_scopes=scopes,
                owner_values=tuple(Decimal(value) for value in values),
                target_report_norm_id=_positive_int(record, "target_report_norm_id"),
            )
        )
    if tuple(item.axis_key for item in external) != (
        "CUSTOMER_LOANS",
        "CUSTOMER_DEPOSITS",
        "LC_COMMITMENTS",
        "SECURITIES",
    ) or tuple(item.target_report_norm_id for item in external) != (759, 5753, 5756, 5759):
        raise TMPage52MappingError("TM page-52 external validation order drifted")

    row_mapped_ids = {
        schema_id
        for row in rows
        if row.disposition is TMPage52RuleDisposition.MAPPED_AUTOMATIC_SCOPED
        for schema_id in row.report_norm_ids
    }
    structural_mapped_ids = {
        item.report_norm_id for item in structural if item.disposition == "MAPPED_AUTOMATIC_SCOPED"
    }
    if row_mapped_ids | structural_mapped_ids != _MAPPED_IDS:
        raise TMPage52MappingError("TM page-52 mapped target partition drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage52MappingError("TM page-52 forbidden mapping inputs drifted")
    return TMPage52MappingPolicy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=52,
        page_tag="page-0052",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=str(payload.get("mapping_authority_scope", "")),
        source_pdf_sha256=str(hashes[0]),
        source_render_sha256=str(hashes[1]),
        source_ocr_sha256=str(hashes[2]),
        upstream_ocr_sha256=str(hashes[3]),
        schema_workbook_sha256=str(hashes[4]),
        schema_total=schema_total,
        scope_schema_ids=tuple(sorted(_SCOPED_IDS)),
        schema_scope_sha256=_SCHEMA_SCOPE_SHA256,
        minimum_visible_label_similarity=float(threshold),
        rows=tuple(rows),
        structural_mappings=tuple(structural),
        validation_formulas=formulas,
        external_owner_validations=tuple(external),
        forbidden_mapping_inputs=tuple(str(value) for value in forbidden),
        policy_sha256=sha256_file(path),
    )


def _similarity(visible: str, anchor: str) -> float:
    if not anchor:
        return 1.0 if not retrieval_key(visible) else 0.0
    normalized = retrieval_key(visible)
    if anchor in normalized:
        return 1.0
    return ratio(normalized, anchor) / 100.0


def _schema_hash(items: tuple[SchemaItem, ...]) -> str:
    payload = [
        (
            item.schema_id,
            item.display_order,
            item.canonical_name,
            item.parent_id,
            tuple(item.children),
        )
        for item in items
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _schema_scope_hash(schema_by_id: dict[int, SchemaItem]) -> str:
    payload = [
        (
            schema_id,
            schema_by_id[schema_id].canonical_name,
            schema_by_id[schema_id].parent_id,
            tuple(schema_by_id[schema_id].children),
        )
        for schema_id in sorted(_SCOPED_IDS)
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validate_schema_context(schema_by_id: dict[int, SchemaItem]) -> None:
    if schema_by_id[1259].parent_id is not None:
        raise TMPage52MappingError("TM page-52 root parent 1259 drifted")
    if schema_by_id[1294].parent_id != 1259 or schema_by_id[1304].parent_id != 1294:
        raise TMPage52MappingError("TM page-52 insertion anchor hierarchy drifted")
    root_children = tuple(schema_by_id[1259].children)
    if not all(schema_id in root_children for schema_id in (1294, 5750, 5759, 5762, 1305)):
        raise TMPage52MappingError("TM page-52 promoted root siblings are absent")
    root_positions = tuple(root_children.index(schema_id) for schema_id in (1294, 5750, 5759, 5762))
    if root_positions != tuple(range(root_positions[0], root_positions[0] + 4)):
        raise TMPage52MappingError("TM page-52 promoted root order drifted")
    local_chain = (1304, 5750, 5751, 5759, 5760, 5761, 5762)
    if any(
        schema_by_id[current_id].display_order + 1 != schema_by_id[next_id].display_order
        for current_id, next_id in zip(local_chain[:-1], local_chain[1:], strict=True)
    ):
        raise TMPage52MappingError("TM page-52 promoted display-order chain drifted")
    if (
        schema_by_id[716].parent_id != 560
        or schema_by_id[759].parent_id != 716
        or tuple(schema_by_id[759].children) != (5752, 765)
        or schema_by_id[5752].parent_id != 759
        or tuple(schema_by_id[5752].children) != tuple(range(760, 765))
        or any(schema_by_id[schema_id].parent_id != 5752 for schema_id in range(760, 765))
        or schema_by_id[765].parent_id != 759
    ):
        raise TMPage52MappingError("TM page-52 loan geographic hierarchy drifted")
    if (
        schema_by_id[1055].parent_id != 560
        or tuple(schema_by_id[1055].children) != (1056, 1075, 5753)
        or schema_by_id[5753].parent_id != 1055
        or tuple(schema_by_id[5753].children) != (5754, 5755)
        or any(schema_by_id[schema_id].parent_id != 5753 for schema_id in (5754, 5755))
    ):
        raise TMPage52MappingError("TM page-52 customer-deposit hierarchy drifted")
    if (
        schema_by_id[1295].parent_id != 1294
        or tuple(schema_by_id[1295].children) != (5756,)
        or schema_by_id[5756].parent_id != 1295
        or tuple(schema_by_id[5756].children) != (5757, 5758)
        or any(schema_by_id[schema_id].parent_id != 5756 for schema_id in (5757, 5758))
    ):
        raise TMPage52MappingError("TM page-52 L/C hierarchy drifted")
    if (
        schema_by_id[5750].parent_id != 1259
        or tuple(schema_by_id[5750].children) != (5751,)
        or schema_by_id[5751].parent_id != 5750
        or schema_by_id[5759].parent_id != 1259
        or tuple(schema_by_id[5759].children) != (5760, 5761)
        or any(schema_by_id[schema_id].parent_id != 5759 for schema_id in (5760, 5761))
    ):
        raise TMPage52MappingError("TM page-52 promoted root hierarchy drifted")


def _value(parsed: ParsedTMPage52, table: int, row: int, axis: int) -> Decimal:
    value = parsed.tables[table - 1].rows[row - 1].row.cells[axis].value
    if value is None:
        raise TMPage52MappingError("TM page-52 validation expected a finite value")
    return value


def _validation(
    parsed: ParsedTMPage52, policy: TMPage52MappingPolicy
) -> tuple[TMPage52ValidationCheck, ...]:
    checks = []
    for axis, role in enumerate(("CURRENT", "COMPARATIVE")):
        expected = _value(parsed, 1, 2, axis)
        observed = _value(parsed, 1, 3, axis)
        checks.append(
            TMPage52ValidationCheck(
                check_id=f"RELATED_PARTY_PRINTED_TOTAL_{role}",
                axis_role=role,
                status="PASS" if expected == observed else "FAIL",
                expected_value=expected,
                observed_value=observed,
                residual=observed - expected,
                target_report_norm_id=5750,
                external_owner_report_norm_ids=(),
                external_owner_scopes=(),
                reason=(
                    "the directly mapped detail ID 5751 reconciles to the directly mapped printed "
                    "total ID 5750 after mapping"
                ),
            )
        )
    for axis, owner_rule in enumerate(policy.external_owner_validations):
        expected = _value(parsed, 2, 2, axis) + _value(parsed, 2, 3, axis)
        observed = sum(owner_rule.owner_values, Decimal(0))
        checks.append(
            TMPage52ValidationCheck(
                check_id=f"GEOGRAPHIC_{owner_rule.axis_key}_EXTERNAL_OWNER_CURRENT",
                axis_role="CURRENT",
                status="PASS" if expected == observed else "FAIL",
                expected_value=expected,
                observed_value=observed,
                residual=observed - expected,
                target_report_norm_id=owner_rule.target_report_norm_id,
                external_owner_report_norm_ids=owner_rule.owner_report_norm_ids,
                external_owner_scopes=owner_rule.owner_scopes,
                reason=(
                    "the two directly mapped page-52 geography children exactly cross-validate "
                    f"immutable primary-owner values {owner_rule.owner_report_norm_ids} from "
                    f"{owner_rule.owner_scopes}; external values are validation-only"
                ),
            )
        )
    return tuple(checks)


def reconcile_tm_page52_items(
    parsed: ParsedTMPage52,
    *,
    schema: Sequence[SchemaItem],
    policy: TMPage52MappingPolicy,
    source_pdf_path: Path,
    schema_workbook_path: Path,
) -> TMPage52MappingResult:
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
        or parsed.upstream_ocr_sha256 != policy.upstream_ocr_sha256
    ):
        raise TMPage52MappingError("TM page-52 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage52MappingError("TM page-52 source PDF hash drifted")
    if sha256_file(schema_workbook_path) != policy.schema_workbook_sha256:
        raise TMPage52MappingError("TM page-52 schema workbook hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE52_SCHEMA_TOTAL:
        raise TMPage52MappingError("TM page-52 schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if (
        tuple(sorted(_SCOPED_IDS)) != policy.scope_schema_ids
        or _schema_scope_hash(schema_by_id) != policy.schema_scope_sha256
    ):
        raise TMPage52MappingError("TM page-52 owned schema branch drifted")
    _validate_schema_context(schema_by_id)
    parsed_rows = tuple(row for table in parsed.tables for row in table.rows)
    if tuple((row.table_key, row.ordinal) for row in parsed_rows) != tuple(
        (rule.table_key, rule.ordinal) for rule in policy.rows
    ):
        raise TMPage52MappingError("TM page-52 parsed row order drifted from policy")

    source_by_schema: dict[int, list[str]] = {schema_id: [] for schema_id in _MAPPED_IDS}
    axis_by_key = dict(
        zip(
            ("CUSTOMER_LOANS", "CUSTOMER_DEPOSITS", "LC_COMMITMENTS", "SECURITIES"),
            parsed.tables[1].axes,
            strict=True,
        )
    )
    structural_dispositions = []
    for rule in policy.structural_mappings:
        axis = axis_by_key[rule.axis_key]
        source_ids = tuple(
            f"{parsed.page_tag}:line-{index:04d}" for index in axis.header_line_indices
        )
        if rule.source_kind == "GEOGRAPHIC_CONTEXT":
            source_ids = tuple(
                dict.fromkeys(
                    (
                        *source_ids,
                        *(
                            f"{parsed.page_tag}:line-{index:04d}"
                            for index in parsed.tables[1].title_line_indices
                        ),
                        *(
                            f"{parsed.page_tag}:line-{index:04d}"
                            for row in parsed.tables[1].rows[1:]
                            for index in row.label_line_indices
                        ),
                    )
                )
            )
        if rule.disposition == "MAPPED_AUTOMATIC_SCOPED":
            source_by_schema[rule.report_norm_id].extend(source_ids)
            reason = "page 52 uniquely owns this promoted geographic-analysis structure"
        else:
            reason = (
                f"aggregate ID {rule.report_norm_id} remains owned by {rule.owner_scope}; "
                "the page-52 header is validation provenance only"
            )
        structural_dispositions.append(
            TMPage52StructuralDisposition(
                structural_key=rule.structural_key,
                source_kind=rule.source_kind,
                axis_key=rule.axis_key,
                status=rule.disposition,
                report_norm_id=rule.report_norm_id,
                canonical_name=schema_by_id[rule.report_norm_id].canonical_name,
                owner_scope=rule.owner_scope,
                source_ids=source_ids,
                reason=reason,
            )
        )

    source_dispositions = []
    assignments = []
    for rule, row in zip(policy.rows, parsed_rows, strict=True):
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if (
            row.row_kind.value != rule.expected_row_kind
            or row.source_role != rule.expected_source_role
            or observations != rule.expected_observations
        ):
            raise TMPage52MappingError(f"TM page-52 row status drifted: {row.row_id}")
        similarity = _similarity(row.row.label, rule.visible_label_anchor)
        if similarity < policy.minimum_visible_label_similarity:
            raise TMPage52MappingError(f"TM page-52 label anchor failed: {row.row_id}")
        if rule.disposition is TMPage52RuleDisposition.SOURCE_ONLY_VALIDATION:
            if rule.report_norm_ids or row.row_kind.value != "LABEL_ONLY":
                raise TMPage52MappingError("TM page-52 source-only binding drifted")
            status = TMPage52SourceStatus.SOURCE_ONLY_VALIDATION.value
        elif row.row_kind.value == "LABEL_ONLY":
            if len(rule.report_norm_ids) != 1:
                raise TMPage52MappingError("TM page-52 structural row target drifted")
            source_by_schema[rule.report_norm_ids[0]].append(row.row_id)
            status = TMPage52SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        else:
            if len(rule.report_norm_ids) != len(row.row.cells):
                raise TMPage52MappingError("TM page-52 numeric target width drifted")
            for index, (schema_id, cell) in enumerate(
                zip(rule.report_norm_ids, row.row.cells, strict=True)
            ):
                start = row.cell_period_starts[index]
                end = row.cell_period_ends[index]
                role = row.cell_period_roles[index]
                if (
                    schema_id not in _VALUE_BEARING_MAPPED_IDS
                    or cell.observation not in {ObservationKind.VALUE, ObservationKind.ZERO}
                    or cell.value is None
                    or start is None
                    or end is None
                    or role is None
                ):
                    raise TMPage52MappingError("TM page-52 mapped cell binding drifted")
                source_by_schema[schema_id].append(row.row_id)
                assignments.append(
                    TMPage52MappedAssignment(
                        source_row_id=row.row_id,
                        table_key=row.table_key,
                        source_role=row.source_role,
                        cell_index=index,
                        report_norm_id=schema_id,
                        observation=cell.observation.value,
                        value=cell.value,
                        period_start=start.isoformat(),
                        period_end=end.isoformat(),
                        period_role=role,
                        unit=parsed.tables[0].axes[0].canonical_unit,
                        unit_multiplier=parsed.tables[0].axes[0].unit_multiplier,
                        mapping_basis=(
                            "VISIBLE_PAGE52_ROW_X_FIXED_PERIOD_OR_GEOGRAPHIC_AXIS_TO_FROZEN_SCHEMA"
                        ),
                    )
                )
            status = TMPage52SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        source_dispositions.append(
            TMPage52SourceDisposition(
                row_id=row.row_id,
                table_key=row.table_key,
                ordinal=row.ordinal,
                visible_label=row.row.label,
                row_kind=row.row_kind.value,
                source_role=row.source_role,
                status=status,
                report_norm_ids=rule.report_norm_ids,
                visible_label_similarity=similarity,
                observations=observations,
                values=tuple(cell.value for cell in row.row.cells),
                period_starts=tuple(
                    value.isoformat() if value is not None else None
                    for value in row.cell_period_starts
                ),
                period_ends=tuple(
                    value.isoformat() if value is not None else None
                    for value in row.cell_period_ends
                ),
                period_roles=row.cell_period_roles,
                unit=parsed.tables[0].axes[0].canonical_unit,
                unit_multiplier=parsed.tables[0].axes[0].unit_multiplier,
                question_required=False,
                reason=(
                    "each visible page-52 cell has one hierarchy-safe promoted-schema target; "
                    "external aggregate owners never select or populate page-52 items"
                ),
            )
        )

    if any(not source_by_schema[schema_id] for schema_id in _MAPPED_IDS):
        raise TMPage52MappingError("TM page-52 mapped item lacks source provenance")
    checks = _validation(parsed, policy)
    if (
        len(checks) != TM_PAGE52_VALIDATION_CHECK_COUNT
        or sum(check.status == "PASS" for check in checks) != TM_PAGE52_VALIDATION_PASS_COUNT
        or any(check.status == "FAIL" or check.residual != 0 for check in checks)
    ):
        raise TMPage52MappingError("TM page-52 accounting validation failed")

    schema_dispositions = []
    for item in tm_schema:
        source_ids = tuple(dict.fromkeys(source_by_schema.get(item.schema_id, ())))
        if item.schema_id in _MAPPED_IDS:
            status = TMPage52SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            reason = "page 52 is the unique owner of this promoted hierarchy-safe schema item"
        elif item.schema_id in _NOT_OBSERVED_IDS:
            status = TMPage52SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            reason = (
                "fully assessed regional child under domestic loans, but no distinct source row is "
                "printed in this disclosure"
            )
        else:
            status = TMPage52SchemaStatus.UNASSESSED.value
            reason = (
                "outside page-52 scope; primary-owner aggregates remain validation-only and all "
                "other schema items remain unassessed"
            )
        schema_dispositions.append(
            TMPage52SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status,
                source_row_ids=source_ids,
                reason=reason,
            )
        )
    result = TMPage52MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=52,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="PAGE52_PROMOTED_IDS_MAPPED_NO_ADDITIONS_NO_OPEN_QUESTIONS",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=TM_PAGE52_SCHEMA_RECONCILED_COUNT,
        mapped_schema_count=TM_PAGE52_MAPPED_SCHEMA_COUNT,
        value_bearing_mapped_schema_count=TM_PAGE52_VALUE_BEARING_MAPPED_SCHEMA_COUNT,
        not_observed_schema_count=TM_PAGE52_NOT_OBSERVED_SCHEMA_COUNT,
        not_applicable_schema_count=0,
        ambiguous_schema_count=0,
        unresolved_schema_count=0,
        unassessed_schema_count=TM_PAGE52_SCHEMA_UNASSESSED_COUNT,
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMPage52SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status == TMPage52SourceStatus.SOURCE_ONLY_VALIDATION.value
            for item in source_dispositions
        ),
        source_question_row_count=0,
        ambiguous_source_row_count=0,
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_assignment_count=len(assignments),
        narrative_record_count=len(parsed.narratives),
        narrative_quantity_count=parsed.narrative_quantity_count,
        validation_check_count=len(checks),
        validation_pass_count=sum(check.status == "PASS" for check in checks),
        validation_not_testable_count=0,
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        structural_dispositions=tuple(structural_dispositions),
        mapped_assignments=tuple(assignments),
        validation_checks=checks,
        validation_formulas=policy.validation_formulas,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        upstream_ocr_sha256=policy.upstream_ocr_sha256,
        schema_workbook_sha256=policy.schema_workbook_sha256,
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS_AND_GEOMETRY",
            "VISIBLE_PAGE52_NOTE_ROW_AND_MATRIX_COLUMN_ORDER",
            "VISIBLE_AND_CONTEXT_BOUND_PERIOD_UNIT_SCOPE",
            "FROZEN_TM_SCHEMA_ID_NAME_ORDER_AND_HIERARCHY",
            "OWNED_PAGE52_SCHEMA_IDS_759_THROUGH_765_AND_5750_THROUGH_5761",
            "DISJOINT_PRIMARY_OWNER_SCOPES_FOR_IDS_716_1055_1295",
            "EXTERNAL_OWNER_VALUES_AS_VALIDATION_ONLY_NOT_SELECTION_OR_IMPUTATION",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
            "NARRATIVE_PERCENTAGES_AS_PROVENANCE_ONLY",
        ),
    )
    return validate_tm_page52_mapping_result(result)


def validate_tm_page52_mapping_result(
    result: TMPage52MappingResult,
) -> TMPage52MappingResult:
    if (
        result.schema_item_count != TM_PAGE52_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE52_SCHEMA_RECONCILED_COUNT
        or result.mapped_schema_count != TM_PAGE52_MAPPED_SCHEMA_COUNT
        or result.value_bearing_mapped_schema_count != TM_PAGE52_VALUE_BEARING_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE52_NOT_OBSERVED_SCHEMA_COUNT
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != 0
        or result.unresolved_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE52_SCHEMA_UNASSESSED_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE52_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE52_MAPPED_SOURCE_ROW_COUNT
        or result.source_only_row_count != TM_PAGE52_SOURCE_ONLY_ROW_COUNT
        or result.source_question_row_count != 0
        or result.ambiguous_source_row_count != 0
        or result.financial_slot_count != TM_PAGE52_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE52_VALUE_COUNT
        or result.dash_count != TM_PAGE52_DASH_COUNT
        or result.mapped_assignment_count != TM_PAGE52_MAPPED_ASSIGNMENT_COUNT
        or result.narrative_record_count != TM_PAGE52_NARRATIVE_RECORD_COUNT
        or result.narrative_quantity_count != TM_PAGE52_NARRATIVE_QUANTITY_COUNT
        or result.validation_check_count != TM_PAGE52_VALIDATION_CHECK_COUNT
        or result.validation_pass_count != TM_PAGE52_VALIDATION_PASS_COUNT
        or result.validation_not_testable_count != TM_PAGE52_VALIDATION_NOT_TESTABLE_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage52MappingError("TM page-52 mapping result denominator drifted")
    if result.status_reconciled_schema_count + result.unassessed_schema_count != (
        result.schema_item_count
    ):
        raise TMPage52MappingError("TM page-52 schema statuses do not reconcile")
    mapped = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage52SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    not_observed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage52SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    }
    unassessed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage52SchemaStatus.UNASSESSED.value
    }
    if (
        mapped != _MAPPED_IDS
        or not_observed != _NOT_OBSERVED_IDS
        or len(unassessed) != TM_PAGE52_SCHEMA_UNASSESSED_COUNT
        or mapped | not_observed | unassessed
        != {item.report_norm_id for item in result.schema_dispositions}
        or any(
            not item.source_row_ids
            for item in result.schema_dispositions
            if item.report_norm_id in _MAPPED_IDS
        )
        or any(
            item.source_row_ids
            for item in result.schema_dispositions
            if item.report_norm_id not in _MAPPED_IDS
        )
        or not _EXTERNAL_OWNER_IDS <= unassessed
    ):
        raise TMPage52MappingError("TM page-52 schema partition drifted")
    structural = {
        item.report_norm_id: (item.status, item.owner_scope)
        for item in result.structural_dispositions
    }
    if structural != {
        716: ("EXTERNAL_OWNER_VALIDATION", "page-0031"),
        759: ("MAPPED_AUTOMATIC_SCOPED", "page-0052"),
        1055: ("EXTERNAL_OWNER_VALIDATION", "page-0043"),
        5753: ("MAPPED_AUTOMATIC_SCOPED", "page-0052"),
        1295: ("EXTERNAL_OWNER_VALIDATION", "page-0051"),
        5756: ("MAPPED_AUTOMATIC_SCOPED", "page-0052"),
        5759: ("MAPPED_AUTOMATIC_SCOPED", "page-0052"),
    } or any(not item.source_ids for item in result.structural_dispositions):
        raise TMPage52MappingError("TM page-52 structural ownership result drifted")
    if (
        tuple(item.status for item in result.source_dispositions)
        != (
            "MAPPED_AUTOMATIC_SCOPED",
            "MAPPED_AUTOMATIC_SCOPED",
            "MAPPED_AUTOMATIC_SCOPED",
            "SOURCE_ONLY_VALIDATION",
            "MAPPED_AUTOMATIC_SCOPED",
            "MAPPED_AUTOMATIC_SCOPED",
        )
        or any(item.question_required for item in result.source_dispositions)
        or tuple(item.report_norm_ids for item in result.source_dispositions)
        != (
            (5750,),
            (5751, 5751),
            (5750, 5750),
            (),
            (5752, 5754, 5757, 5760),
            (765, 5755, 5758, 5761),
        )
    ):
        raise TMPage52MappingError("TM page-52 source disposition result drifted")
    if (
        len(result.mapped_assignments) != 12
        or {item.report_norm_id for item in result.mapped_assignments} != _VALUE_BEARING_MAPPED_IDS
        or any(
            item.observation != ObservationKind.VALUE.value for item in result.mapped_assignments
        )
        or {(item.unit, item.unit_multiplier) for item in result.mapped_assignments}
        != {("VND", 1_000_000)}
    ):
        raise TMPage52MappingError("TM page-52 assignment result drifted")
    if (
        tuple(check.check_id for check in result.validation_checks)
        != (
            "RELATED_PARTY_PRINTED_TOTAL_CURRENT",
            "RELATED_PARTY_PRINTED_TOTAL_COMPARATIVE",
            "GEOGRAPHIC_CUSTOMER_LOANS_EXTERNAL_OWNER_CURRENT",
            "GEOGRAPHIC_CUSTOMER_DEPOSITS_EXTERNAL_OWNER_CURRENT",
            "GEOGRAPHIC_LC_COMMITMENTS_EXTERNAL_OWNER_CURRENT",
            "GEOGRAPHIC_SECURITIES_EXTERNAL_OWNER_CURRENT",
        )
        or tuple(check.expected_value for check in result.validation_checks)
        != (
            Decimal(37_248_180),
            Decimal(40_201_646),
            Decimal(1_120_562_481),
            Decimal(905_918_332),
            Decimal(71_763_365),
            Decimal(268_484_730),
        )
        or tuple(check.target_report_norm_id for check in result.validation_checks)
        != (5750, 5750, 759, 5753, 5756, 5759)
        or any(
            check.status != "PASS"
            or check.observed_value != check.expected_value
            or check.residual != 0
            for check in result.validation_checks
        )
        or dict(result.validation_formulas) != _EXPECTED_FORMULAS
    ):
        raise TMPage52MappingError("TM page-52 validation result drifted")
    return result


__all__ = [
    "TM_PAGE52_POLICY_RELATIVE_PATH",
    "TMPage52MappedAssignment",
    "TMPage52MappingError",
    "TMPage52MappingPolicy",
    "TMPage52MappingResult",
    "TMPage52SchemaDisposition",
    "TMPage52SchemaStatus",
    "TMPage52SourceDisposition",
    "TMPage52SourceStatus",
    "TMPage52StructuralDisposition",
    "TMPage52ValidationCheck",
    "load_tm_page52_mapping_policy",
    "reconcile_tm_page52_items",
    "validate_tm_page52_mapping_result",
]
