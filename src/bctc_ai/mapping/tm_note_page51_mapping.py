"""Source-scoped ReportNormId reconciliation for MBB TM page 51."""

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
from bctc_ai.tables.tm_note_page51 import ParsedTMPage51

TM_PAGE51_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page51-v1.yaml")
TM_PAGE51_SCHEMA_TOTAL = 1_710
TM_PAGE51_RECONCILED_SCHEMA_COUNT = 15
TM_PAGE51_MAPPED_SCHEMA_COUNT = 10
TM_PAGE51_VALUE_BEARING_MAPPED_SCHEMA_COUNT = 9
TM_PAGE51_NOT_OBSERVED_COUNT = 5
TM_PAGE51_UNASSESSED_COUNT = 1_695
TM_PAGE51_SOURCE_ROW_COUNT = 11
TM_PAGE51_MAPPED_SOURCE_COUNT = 9
TM_PAGE51_SOURCE_ONLY_COUNT = 2
TM_PAGE51_QUESTION_SOURCE_COUNT = 0
TM_PAGE51_FINANCIAL_SLOT_COUNT = 18
TM_PAGE51_VALUE_COUNT = 18
TM_PAGE51_DASH_COUNT = 0
TM_PAGE51_MAPPED_VALUE_COUNT = 18
TM_PAGE51_NARRATIVE_RECORD_COUNT = 7
TM_PAGE51_MAPPED_NARRATIVE_COUNT = 1
TM_PAGE51_NARRATIVE_QUANTITY_COUNT = 2
TM_PAGE51_VALIDATION_CHECK_COUNT = 4
TM_PAGE51_VALIDATION_PASS_COUNT = 2
TM_PAGE51_VALIDATION_NOT_TESTABLE_COUNT = 2

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCOPED_IDS = {*range(1294, 1305), *range(5741, 5745)}
_VALUE_MAPPED_IDS = {1295, 1296, 1300, 1301, 1304, 5741, 5742, 5743, 5744}
_STRUCTURAL_MAPPED_IDS = {1294}
_MAPPED_IDS = _VALUE_MAPPED_IDS | _STRUCTURAL_MAPPED_IDS
_NOT_OBSERVED_IDS = {1297, 1298, 1299, 1302, 1303}
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
    "narrative_quantity_as_schema_value",
    "narrative_text_except_exact_structural_heading",
    "derived_1302_value_as_observed_source",
    "schema_id_outside_page51_scope",
}
_EXPECTED_PARENTS = {
    1294: 1259,
    1295: 1294,
    1296: 1294,
    1297: 1294,
    1298: 1294,
    1299: 1294,
    1300: 1294,
    1301: 1294,
    1302: 1301,
    1303: 1294,
    1304: 1294,
    5741: 1301,
    5742: 1301,
    5743: 1302,
    5744: 1302,
}
_EXPECTED_CHILDREN = {
    1294: (1295, 1296, 1297, 1298, 1299, 1300, 1301, 1303, 1304),
    1301: (5741, 5742, 1302),
    1302: (5743, 5744),
}


class TMPage51MappingError(ValueError):
    pass


class TMPage51RuleDisposition(StrEnum):
    FIXED = "FIXED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


class TMPage51SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage51SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


@dataclass(frozen=True)
class TMPage51RowRule:
    ordinal: int
    visible_label_anchor: str
    expected_row_kind: str
    expected_observations: tuple[str, ...]
    disposition: TMPage51RuleDisposition
    report_norm_id: int | None
    question_required: bool


@dataclass(frozen=True)
class TMPage51StructuralRule:
    semantic_role: str
    visible_label_anchor: str
    report_norm_id: int


@dataclass(frozen=True)
class TMPage51MappingPolicy:
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
    schema_total: int
    scoped_schema_ids: tuple[int, ...]
    minimum_visible_label_similarity: float
    rows: tuple[TMPage51RowRule, ...]
    structural_mappings: tuple[TMPage51StructuralRule, ...]
    not_observed_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage51SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage51SourceDisposition:
    row_id: str
    ordinal: int
    visible_label: str
    row_kind: str
    source_role: str
    status: str
    report_norm_id: int | None
    canonical_name: str | None
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
class TMPage51NarrativeDisposition:
    narrative_id: str
    semantic_role: str
    visible_text: str
    status: str
    report_norm_id: int | None
    canonical_name: str | None
    visible_label_similarity: float | None
    quantity_count: int
    mapping_approved: bool
    reason: str


@dataclass(frozen=True)
class TMPage51ValidationCheck:
    check_id: str
    axis_role: str
    status: str
    expected_value: Decimal
    observed_value: Decimal | None
    residual: Decimal | None
    reason: str


@dataclass(frozen=True)
class TMPage51MappingResult:
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
    mapped_value_count: int
    narrative_record_count: int
    mapped_narrative_record_count: int
    narrative_quantity_count: int
    validation_check_count: int
    validation_pass_count: int
    validation_not_testable_count: int
    schema_dispositions: tuple[TMPage51SchemaDisposition, ...]
    source_dispositions: tuple[TMPage51SourceDisposition, ...]
    narrative_dispositions: tuple[TMPage51NarrativeDisposition, ...]
    validation_checks: tuple[TMPage51ValidationCheck, ...]
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    upstream_ocr_sha256: str
    schema_projection_sha256: str
    policy_sha256: str
    mapping_inputs: tuple[str, ...]


def _positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TMPage51MappingError(f"invalid positive TM page-51 field: {field}")
    return value


def _ids(payload: Any, field: str) -> tuple[int, ...]:
    if (
        not isinstance(payload, list)
        or not payload
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload)
    ):
        raise TMPage51MappingError(f"TM page-51 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMPage51MappingError(f"TM page-51 {field} contains duplicates")
    return result


def load_tm_page51_mapping_policy(path: Path) -> TMPage51MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage51MappingError(f"cannot load TM page-51 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE51_SCOPED_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 51
        or payload.get("page_tag") != "page-0051"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage51MappingError("TM page-51 mapping identity drifted")
    hashes = tuple(
        payload.get(field)
        for field in (
            "source_pdf_sha256",
            "source_render_sha256",
            "source_ocr_sha256",
            "upstream_ocr_sha256",
        )
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage51MappingError("TM page-51 mapping hashes are invalid")
    schema_total = _positive_int(payload, "schema_total")
    scoped = _ids(payload.get("scoped_schema_ids"), "scoped_schema_ids")
    not_observed = _ids(payload.get("not_observed_schema_ids"), "not_observed_schema_ids")
    if set(scoped) != _SCOPED_IDS or set(not_observed) != _NOT_OBSERVED_IDS:
        raise TMPage51MappingError("TM page-51 exact schema scope drifted")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 <= threshold <= 1
    ):
        raise TMPage51MappingError("TM page-51 label threshold is invalid")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE51_SOURCE_ROW_COUNT:
        raise TMPage51MappingError("TM page-51 row rules are incomplete")
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage51MappingError("TM page-51 row rule is invalid")
        try:
            disposition = TMPage51RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMPage51MappingError("TM page-51 disposition is invalid") from exc
        ordinal = record.get("ordinal")
        anchor = record.get("visible_label_anchor")
        row_kind = record.get("expected_row_kind")
        observations = record.get("expected_observations")
        report_norm_id = record.get("report_norm_id")
        question = record.get("question_required")
        if (
            isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal <= 0
            or not isinstance(anchor, str)
            or not retrieval_key(anchor)
            or row_kind not in {"NUMERIC", "LABEL_ONLY"}
            or not isinstance(observations, list)
            or len(observations) != 2
            or any(value not in {"VALUE", "ZERO", "DASH", "BLANK"} for value in observations)
            or (report_norm_id is not None and not isinstance(report_norm_id, int))
            or not isinstance(question, bool)
        ):
            raise TMPage51MappingError("TM page-51 row rule fields are invalid")
        if disposition is TMPage51RuleDisposition.FIXED:
            if report_norm_id not in _VALUE_MAPPED_IDS or question:
                raise TMPage51MappingError("TM page-51 fixed mapping rule drifted")
        elif report_norm_id is not None or question:
            raise TMPage51MappingError("TM page-51 source-only rule drifted")
        rows.append(
            TMPage51RowRule(
                ordinal=ordinal,
                visible_label_anchor=retrieval_key(anchor),
                expected_row_kind=row_kind,
                expected_observations=tuple(str(value) for value in observations),
                disposition=disposition,
                report_norm_id=report_norm_id,
                question_required=question,
            )
        )
    if tuple(row.ordinal for row in rows) != tuple(range(1, TM_PAGE51_SOURCE_ROW_COUNT + 1)):
        raise TMPage51MappingError("TM page-51 row-rule order drifted")
    raw_structural = payload.get("structural_mappings")
    if not isinstance(raw_structural, list) or len(raw_structural) != 1:
        raise TMPage51MappingError("TM page-51 structural mapping is incomplete")
    structural = []
    for record in raw_structural:
        if not isinstance(record, dict):
            raise TMPage51MappingError("TM page-51 structural mapping is invalid")
        role = record.get("semantic_role")
        anchor = record.get("visible_label_anchor")
        schema_id = record.get("report_norm_id")
        if (
            role != "CONTINGENT_LIABILITIES_HEADING"
            or not isinstance(anchor, str)
            or not retrieval_key(anchor)
            or schema_id != 1294
        ):
            raise TMPage51MappingError("TM page-51 structural mapping drifted")
        structural.append(
            TMPage51StructuralRule(
                semantic_role=role,
                visible_label_anchor=retrieval_key(anchor),
                report_norm_id=schema_id,
            )
        )
    fixed_ids = {
        row.report_norm_id for row in rows if row.disposition is TMPage51RuleDisposition.FIXED
    }
    if fixed_ids != _VALUE_MAPPED_IDS or fixed_ids | {1294} | set(not_observed) != set(scoped):
        raise TMPage51MappingError("TM page-51 schema partition drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage51MappingError("TM page-51 forbidden mapping inputs drifted")
    return TMPage51MappingPolicy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=51,
        page_tag="page-0051",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=str(payload.get("mapping_authority_scope", "")),
        source_pdf_sha256=str(hashes[0]),
        source_render_sha256=str(hashes[1]),
        source_ocr_sha256=str(hashes[2]),
        upstream_ocr_sha256=str(hashes[3]),
        schema_total=schema_total,
        scoped_schema_ids=scoped,
        minimum_visible_label_similarity=float(threshold),
        rows=tuple(rows),
        structural_mappings=tuple(structural),
        not_observed_schema_ids=not_observed,
        forbidden_mapping_inputs=tuple(str(value) for value in forbidden),
        policy_sha256=sha256_file(path),
    )


def _similarity(visible: str, anchor: str) -> float:
    left = retrieval_key(visible)
    if anchor in left:
        return 1.0
    return ratio(left, anchor) / 100.0


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


def _value(parsed: ParsedTMPage51, ordinal: int, axis: int) -> Decimal:
    row = parsed.rows[ordinal - 1]
    value = row.row.cells[axis].value
    if value is None:
        raise TMPage51MappingError(f"TM page-51 expected a finite value: row {ordinal}")
    return value


def _validation(parsed: ParsedTMPage51) -> tuple[TMPage51ValidationCheck, ...]:
    checks = []
    for axis, role in enumerate(("CURRENT", "COMPARATIVE")):
        expected_fx = sum((_value(parsed, ordinal, axis) for ordinal in (5, 6, 7, 8)), Decimal(0))
        observed_fx = _value(parsed, 4, axis)
        checks.append(
            TMPage51ValidationCheck(
                check_id=f"FX_COMMITMENT_TOTAL_{role}",
                axis_role=role,
                status="PASS" if expected_fx == observed_fx else "FAIL",
                expected_value=expected_fx,
                observed_value=observed_fx,
                residual=observed_fx - expected_fx,
                reason=(
                    "four visible foreign-exchange commitment components reconcile to the "
                    "printed ID 1301 total"
                ),
            )
        )
        expected_swap = _value(parsed, 7, axis) + _value(parsed, 8, axis)
        checks.append(
            TMPage51ValidationCheck(
                check_id=f"SWAP_COMMITMENT_TOTAL_{role}",
                axis_role=role,
                status="NOT_TESTABLE_TARGET_NOT_OBSERVED",
                expected_value=expected_swap,
                observed_value=None,
                residual=None,
                reason=(
                    "ID 1302 is a schema aggregate of the two visible swap components, but the "
                    "PDF prints no standalone ID 1302 value; no derived value is promoted"
                ),
            )
        )
    return tuple(checks)


def _validate_hierarchy(schema_by_id: dict[int, SchemaItem]) -> None:
    for schema_id, parent_id in _EXPECTED_PARENTS.items():
        if schema_by_id[schema_id].parent_id != parent_id:
            raise TMPage51MappingError(
                f"TM page-51 hierarchy parent drifted: {schema_id}->{schema_by_id[schema_id].parent_id}"
            )
    for schema_id, children in _EXPECTED_CHILDREN.items():
        if tuple(schema_by_id[schema_id].children) != children:
            raise TMPage51MappingError(
                f"TM page-51 hierarchy children drifted: {schema_id}->{schema_by_id[schema_id].children}"
            )


def reconcile_tm_page51_items(
    parsed: ParsedTMPage51,
    *,
    schema: Sequence[SchemaItem],
    policy: TMPage51MappingPolicy,
    source_pdf_path: Path,
) -> TMPage51MappingResult:
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
        or parsed.upstream_ocr_sha256 != policy.upstream_ocr_sha256
    ):
        raise TMPage51MappingError("TM page-51 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage51MappingError("TM page-51 source PDF hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE51_SCHEMA_TOTAL:
        raise TMPage51MappingError("TM page-51 schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if not _SCOPED_IDS <= set(schema_by_id):
        raise TMPage51MappingError("TM page-51 scoped ReportNormIds are absent")
    _validate_hierarchy(schema_by_id)
    if tuple(row.ordinal for row in parsed.rows) != tuple(rule.ordinal for rule in policy.rows):
        raise TMPage51MappingError("TM page-51 parsed row order drifted from policy")
    source_dispositions = []
    source_rows_by_schema: dict[int, list[str]] = {}
    for rule, row in zip(policy.rows, parsed.rows, strict=True):
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if (
            row.row_kind.value != rule.expected_row_kind
            or observations != rule.expected_observations
        ):
            raise TMPage51MappingError(f"TM page-51 row status drifted: {row.row_id}")
        similarity = _similarity(row.row.label, rule.visible_label_anchor)
        if similarity < policy.minimum_visible_label_similarity:
            raise TMPage51MappingError(f"TM page-51 label anchor failed: {row.row_id}")
        if rule.disposition is TMPage51RuleDisposition.FIXED:
            assert rule.report_norm_id is not None
            item = schema_by_id[rule.report_norm_id]
            status = TMPage51SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            canonical = item.canonical_name
            source_rows_by_schema.setdefault(item.schema_id, []).append(row.row_id)
            reason = "fixed page-51 hierarchy, row order and visible-label rule passed"
        else:
            status = TMPage51SourceStatus.SOURCE_ONLY_VALIDATION.value
            canonical = None
            reason = (
                "visible section/note title retained as source provenance without a value export"
            )
        source_dispositions.append(
            TMPage51SourceDisposition(
                row_id=row.row_id,
                ordinal=row.ordinal,
                visible_label=row.row.label,
                row_kind=row.row_kind.value,
                source_role=row.source_role,
                status=status,
                report_norm_id=rule.report_norm_id,
                canonical_name=canonical,
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
                unit=parsed.axes[0].canonical_unit,
                unit_multiplier=parsed.axes[0].unit_multiplier,
                question_required=rule.question_required,
                reason=reason,
            )
        )
    structural_by_role = {record.semantic_role: record for record in policy.structural_mappings}
    narrative_dispositions = []
    for narrative in parsed.narratives:
        rule = structural_by_role.get(narrative.semantic_role)
        if rule is None:
            narrative_dispositions.append(
                TMPage51NarrativeDisposition(
                    narrative_id=narrative.narrative_id,
                    semantic_role=narrative.semantic_role,
                    visible_text=narrative.raw_text,
                    status="SOURCE_ONLY_NARRATIVE",
                    report_norm_id=None,
                    canonical_name=None,
                    visible_label_similarity=None,
                    quantity_count=len(narrative.quantities),
                    mapping_approved=False,
                    reason="qualitative narrative retained outside the financial schema-value path",
                )
            )
            continue
        similarity = _similarity(narrative.raw_text, rule.visible_label_anchor)
        item = schema_by_id[rule.report_norm_id]
        if similarity < policy.minimum_visible_label_similarity:
            raise TMPage51MappingError("TM page-51 exact structural heading anchor failed")
        source_rows_by_schema.setdefault(item.schema_id, []).append(narrative.narrative_id)
        narrative_dispositions.append(
            TMPage51NarrativeDisposition(
                narrative_id=narrative.narrative_id,
                semantic_role=narrative.semantic_role,
                visible_text=narrative.raw_text,
                status="MAPPED_AUTOMATIC_STRUCTURAL_NO_VALUE",
                report_norm_id=item.schema_id,
                canonical_name=item.canonical_name,
                visible_label_similarity=similarity,
                quantity_count=len(narrative.quantities),
                mapping_approved=True,
                reason="exact visible structural heading maps to ID 1294 without inventing a value",
            )
        )
    checks = _validation(parsed)
    if (
        len(checks) != TM_PAGE51_VALIDATION_CHECK_COUNT
        or sum(check.status == "PASS" for check in checks) != TM_PAGE51_VALIDATION_PASS_COUNT
        or sum(check.status == "NOT_TESTABLE_TARGET_NOT_OBSERVED" for check in checks)
        != TM_PAGE51_VALIDATION_NOT_TESTABLE_COUNT
        or any(check.status == "FAIL" for check in checks)
    ):
        raise TMPage51MappingError("TM page-51 accounting validation failed")
    not_observed = set(policy.not_observed_schema_ids)
    schema_dispositions = []
    for item in tm_schema:
        if item.schema_id in source_rows_by_schema:
            status = TMPage51SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_ids = tuple(source_rows_by_schema[item.schema_id])
            reason = "fixed page-51 source row or exact structural heading passed scoped mapping"
        elif item.schema_id in not_observed:
            status = TMPage51SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            source_ids = ()
            reason = "item belongs to the fully assessed page-51 scope but has no standalone row"
        else:
            status = TMPage51SchemaStatus.UNASSESSED.value
            source_ids = ()
            reason = "outside the exact page-51 schema scope"
        schema_dispositions.append(
            TMPage51SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status,
                source_row_ids=source_ids,
                reason=reason,
            )
        )
    result = TMPage51MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=51,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="SCOPED_PAGE51_MAPPING_COMPLETE_NO_OPEN_QUESTIONS",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=len(_SCOPED_IDS),
        mapped_schema_count=len(source_rows_by_schema),
        value_bearing_mapped_schema_count=len(_VALUE_MAPPED_IDS),
        not_observed_schema_count=len(not_observed),
        not_applicable_schema_count=0,
        ambiguous_schema_count=0,
        unassessed_schema_count=len(tm_schema) - len(_SCOPED_IDS),
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMPage51SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status == TMPage51SourceStatus.SOURCE_ONLY_VALIDATION.value
            for item in source_dispositions
        ),
        source_question_row_count=sum(item.question_required for item in source_dispositions),
        ambiguous_source_row_count=0,
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_value_count=sum(
            observation in {ObservationKind.VALUE.value, ObservationKind.ZERO.value}
            for item in source_dispositions
            if item.status == TMPage51SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for observation in item.observations
        ),
        narrative_record_count=len(parsed.narratives),
        mapped_narrative_record_count=sum(
            item.status == "MAPPED_AUTOMATIC_STRUCTURAL_NO_VALUE" for item in narrative_dispositions
        ),
        narrative_quantity_count=parsed.narrative_quantity_count,
        validation_check_count=len(checks),
        validation_pass_count=sum(check.status == "PASS" for check in checks),
        validation_not_testable_count=sum(
            check.status == "NOT_TESTABLE_TARGET_NOT_OBSERVED" for check in checks
        ),
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        narrative_dispositions=tuple(narrative_dispositions),
        validation_checks=checks,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        upstream_ocr_sha256=policy.upstream_ocr_sha256,
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS",
            "VISIBLE_PAGE51_SECTION_NOTE_AND_LOCAL_ROW_ORDER",
            "SOURCE_RENDER_SHA256",
            "VISIBLE_TABLE_LOCAL_PERIOD_UNIT_SCOPE_BINDING",
            "TM_SCHEMA_ID_NAME_ORDER_AND_HIERARCHY",
            "EXACT_VISIBLE_STRUCTURAL_HEADING_FOR_ID_1294",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
            "NARRATIVE_PERCENTAGES_AS_PROVENANCE_ONLY",
        ),
    )
    return validate_tm_page51_mapping_result(result)


def validate_tm_page51_mapping_result(result: TMPage51MappingResult) -> TMPage51MappingResult:
    if (
        result.schema_item_count != TM_PAGE51_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE51_RECONCILED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE51_MAPPED_SCHEMA_COUNT
        or result.value_bearing_mapped_schema_count != TM_PAGE51_VALUE_BEARING_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE51_NOT_OBSERVED_COUNT
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE51_UNASSESSED_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE51_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE51_MAPPED_SOURCE_COUNT
        or result.source_only_row_count != TM_PAGE51_SOURCE_ONLY_COUNT
        or result.source_question_row_count != TM_PAGE51_QUESTION_SOURCE_COUNT
        or result.ambiguous_source_row_count != 0
        or result.financial_slot_count != TM_PAGE51_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE51_VALUE_COUNT
        or result.dash_count != TM_PAGE51_DASH_COUNT
        or result.mapped_value_count != TM_PAGE51_MAPPED_VALUE_COUNT
        or result.narrative_record_count != TM_PAGE51_NARRATIVE_RECORD_COUNT
        or result.mapped_narrative_record_count != TM_PAGE51_MAPPED_NARRATIVE_COUNT
        or result.narrative_quantity_count != TM_PAGE51_NARRATIVE_QUANTITY_COUNT
        or result.validation_check_count != TM_PAGE51_VALIDATION_CHECK_COUNT
        or result.validation_pass_count != TM_PAGE51_VALIDATION_PASS_COUNT
        or result.validation_not_testable_count != TM_PAGE51_VALIDATION_NOT_TESTABLE_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage51MappingError("TM page-51 mapping result denominator drifted")
    if (
        result.mapped_schema_count
        + result.not_observed_schema_count
        + result.unassessed_schema_count
        != result.schema_item_count
    ):
        raise TMPage51MappingError("TM page-51 schema statuses do not reconcile")
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMPage51SchemaStatus)
    }
    if (
        by_status[TMPage51SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] != _MAPPED_IDS
        or by_status[TMPage51SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] != _NOT_OBSERVED_IDS
    ):
        raise TMPage51MappingError("TM page-51 exact schema partition drifted")
    structural = [
        item
        for item in result.narrative_dispositions
        if item.status == "MAPPED_AUTOMATIC_STRUCTURAL_NO_VALUE"
    ]
    if (
        len(structural) != 1
        or structural[0].report_norm_id != 1294
        or structural[0].quantity_count != 0
        or not structural[0].mapping_approved
    ):
        raise TMPage51MappingError("TM page-51 structural mapping drifted")
    if any(item.question_required for item in result.source_dispositions):
        raise TMPage51MappingError("TM page-51 user-question partition drifted")
    return result


__all__ = [
    "TM_PAGE51_POLICY_RELATIVE_PATH",
    "TMPage51MappingError",
    "TMPage51MappingPolicy",
    "TMPage51MappingResult",
    "TMPage51NarrativeDisposition",
    "TMPage51SchemaDisposition",
    "TMPage51SchemaStatus",
    "TMPage51SourceDisposition",
    "TMPage51SourceStatus",
    "TMPage51ValidationCheck",
    "load_tm_page51_mapping_policy",
    "reconcile_tm_page51_items",
    "validate_tm_page51_mapping_result",
]
