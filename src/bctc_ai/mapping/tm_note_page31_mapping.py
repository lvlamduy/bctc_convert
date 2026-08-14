"""Source-scoped item mapping and accounting validation for MBB TM page 31."""

from __future__ import annotations

import hashlib
import json
import re
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
from bctc_ai.tables.tm_note_word_box import ParsedTMPage31, TMNoteRowKind

TM_PAGE31_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page31-v1.yaml")
TM_PAGE31_SCHEMA_TOTAL = 1_710
TM_PAGE31_SOURCE_ROW_COUNT = 33
TM_PAGE31_MAPPED_SCHEMA_COUNT = 30
TM_PAGE31_MAPPED_SOURCE_COUNT = 29
TM_PAGE31_SOURCE_ONLY_COUNT = 4
TM_PAGE31_NOT_OBSERVED_COUNT = 12
TM_PAGE31_NOT_APPLICABLE_COUNT = 23
TM_PAGE31_ASSESSED_SCHEMA_COUNT = 65
TM_PAGE31_UNASSESSED_SCHEMA_COUNT = 1_645
TM_PAGE31_ACCOUNTING_CHECK_COUNT = 14
TM_PAGE31_MAPPED_VALUE_COUNT = 48
TM_PAGE31_MAPPED_VALUE_ASSIGNMENT_COUNT = 50
TM_PAGE31_EXTRACTED_VALUE_COUNT = 56
TM_PAGE31_STRUCTURAL_BLANK_ROW_COUNT = 5

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "accounting_equation_result_as_item_selector",
}


class TMPage31MappingError(ValueError):
    pass


class TMPage31RuleDisposition(StrEnum):
    FIXED = "FIXED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


class TMPage31SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    SCHEMA_ITEM_NOT_APPLICABLE = "SCHEMA_ITEM_NOT_APPLICABLE"
    UNASSESSED = "UNASSESSED"


class TMPage31SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


@dataclass(frozen=True)
class TMPage31RowRule:
    table_key: str
    ordinal: int
    visible_label_anchor: str | None
    expected_row_kind: str
    disposition: TMPage31RuleDisposition
    report_norm_id: int | None
    additional_report_norm_ids: tuple[int, ...]
    assignment_roles: tuple[str, ...]

    @property
    def identity(self) -> tuple[str, int]:
        return self.table_key, self.ordinal


@dataclass(frozen=True)
class TMPage31MappingPolicy:
    source_path: Path
    document: str
    page_number: int
    page_tag: str
    report_scope: str
    mapping_authority_scope: str
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    schema_total: int
    minimum_visible_label_similarity: float
    rows: tuple[TMPage31RowRule, ...]
    not_observed_schema_ids: tuple[int, ...]
    not_applicable_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage31SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage31SourceDisposition:
    row_id: str
    table_key: str
    ordinal: int
    visible_label: str
    row_kind: str
    source_role: str
    status: str
    report_norm_id: int | None
    canonical_name: str | None
    report_norm_ids: tuple[int, ...]
    canonical_names: tuple[str, ...]
    assignment_roles: tuple[str, ...]
    visible_label_similarity: float | None
    observations: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    period_ends: tuple[str, ...]
    unit: str
    unit_multiplier: int
    reason: str


@dataclass(frozen=True)
class TMPage31AccountingCheck:
    check_id: str
    axis_role: str
    expected_value: Decimal
    observed_value: Decimal
    residual: Decimal
    status: str


@dataclass(frozen=True)
class TMPage31MappingResult:
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
    not_observed_schema_count: int
    not_applicable_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    source_only_row_count: int
    numeric_source_row_count: int
    structural_blank_source_row_count: int
    extracted_value_count: int
    mapped_value_count: int
    mapped_value_assignment_count: int
    accounting_check_count: int
    accounting_pass_count: int
    schema_dispositions: tuple[TMPage31SchemaDisposition, ...]
    source_dispositions: tuple[TMPage31SourceDisposition, ...]
    accounting_checks: tuple[TMPage31AccountingCheck, ...]
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    schema_projection_sha256: str
    policy_sha256: str
    mapping_inputs: tuple[str, ...]


def _positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TMPage31MappingError(f"invalid positive TM page-31 field: {field}")
    return value


def _schema_ids(payload: Any, field: str) -> tuple[int, ...]:
    if not isinstance(payload, list) or any(
        isinstance(value, bool) or not isinstance(value, int) for value in payload
    ):
        raise TMPage31MappingError(f"TM page-31 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMPage31MappingError(f"TM page-31 {field} contains duplicates")
    return result


def load_tm_page31_mapping_policy(path: Path) -> TMPage31MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage31MappingError(f"cannot load TM page-31 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE31_SCOPED_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 31
        or payload.get("page_tag") != "page-0031"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage31MappingError("TM page-31 mapping policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage31MappingError("TM page-31 mapping source hashes are invalid")
    minimum_similarity = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(minimum_similarity, bool)
        or not isinstance(minimum_similarity, (int, float))
        or not 0 < float(minimum_similarity) <= 1
    ):
        raise TMPage31MappingError("TM page-31 mapping similarity threshold is invalid")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE31_SOURCE_ROW_COUNT:
        raise TMPage31MappingError("TM page-31 mapping row denominator drifted")
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage31MappingError("TM page-31 mapping row is invalid")
        table_key = record.get("table_key")
        ordinal = record.get("ordinal")
        visible_label_anchor = record.get("visible_label_anchor")
        expected_row_kind = record.get("expected_row_kind")
        report_norm_id = record.get("report_norm_id")
        additional_report_norm_ids = _schema_ids(
            record.get("additional_report_norm_ids", []),
            "additional ReportNormIds",
        )
        raw_assignment_roles = record.get("assignment_roles", [])
        if not isinstance(raw_assignment_roles, list) or any(
            not isinstance(value, str) or not value for value in raw_assignment_roles
        ):
            raise TMPage31MappingError("TM page-31 assignment roles are invalid")
        assignment_roles = tuple(raw_assignment_roles)
        try:
            disposition = TMPage31RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMPage31MappingError("TM page-31 row disposition is invalid") from exc
        if (
            not isinstance(table_key, str)
            or not table_key
            or isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal <= 0
            or (visible_label_anchor is not None and not isinstance(visible_label_anchor, str))
            or expected_row_kind not in {kind.value for kind in TMNoteRowKind}
        ):
            raise TMPage31MappingError("TM page-31 mapping row identity is invalid")
        if disposition is TMPage31RuleDisposition.FIXED:
            if isinstance(report_norm_id, bool) or not isinstance(report_norm_id, int):
                raise TMPage31MappingError("fixed TM page-31 row has no ReportNormId")
            if report_norm_id in additional_report_norm_ids:
                raise TMPage31MappingError("TM page-31 row repeats a ReportNormId assignment")
            if additional_report_norm_ids and len(assignment_roles) != (
                1 + len(additional_report_norm_ids)
            ):
                raise TMPage31MappingError("TM page-31 multi-ID assignment roles drifted")
            if not additional_report_norm_ids and assignment_roles:
                raise TMPage31MappingError("TM page-31 scalar row has unexpected assignment roles")
        elif report_norm_id is not None or additional_report_norm_ids or assignment_roles:
            raise TMPage31MappingError("source-only TM page-31 row cannot select a ReportNormId")
        rows.append(
            TMPage31RowRule(
                table_key=table_key,
                ordinal=ordinal,
                visible_label_anchor=(
                    retrieval_key(visible_label_anchor)
                    if visible_label_anchor is not None
                    else None
                ),
                expected_row_kind=expected_row_kind,
                disposition=disposition,
                report_norm_id=report_norm_id,
                additional_report_norm_ids=additional_report_norm_ids,
                assignment_roles=assignment_roles,
            )
        )
    if len({row.identity for row in rows}) != len(rows):
        raise TMPage31MappingError("TM page-31 mapping row identities are duplicated")
    fixed_ids = tuple(
        schema_id
        for row in rows
        if row.disposition is TMPage31RuleDisposition.FIXED
        for schema_id in (row.report_norm_id, *row.additional_report_norm_ids)
    )
    if len(fixed_ids) != TM_PAGE31_MAPPED_SCHEMA_COUNT or len(set(fixed_ids)) != len(fixed_ids):
        raise TMPage31MappingError("TM page-31 fixed ReportNormId set drifted")
    multi_id_rows = [row for row in rows if row.additional_report_norm_ids]
    if (
        len(multi_id_rows) != 1
        or multi_id_rows[0].identity != ("LOAN_TYPE", 8)
        or (multi_id_rows[0].report_norm_id, *multi_id_rows[0].additional_report_norm_ids)
        != (1944, 5745)
        or multi_id_rows[0].assignment_roles != ("LEGACY_GLOBAL_PRIMARY", "CONTEXT_BRANCH_MEMBER")
    ):
        raise TMPage31MappingError("TM page-31 dual-assignment contract drifted")
    not_observed = _schema_ids(payload.get("not_observed_schema_ids"), "not-observed IDs")
    not_applicable = _schema_ids(payload.get("not_applicable_schema_ids"), "not-applicable IDs")
    if len(not_observed) != TM_PAGE31_NOT_OBSERVED_COUNT or len(not_applicable) != 23:
        raise TMPage31MappingError("TM page-31 explicit schema-status denominator drifted")
    if set(fixed_ids) & (set(not_observed) | set(not_applicable)) or set(not_observed) & set(
        not_applicable
    ):
        raise TMPage31MappingError("TM page-31 schema status sets overlap")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage31MappingError("TM page-31 forbidden mapping inputs drifted")
    mapping_scope = payload.get("mapping_authority_scope")
    document = payload.get("document")
    if not isinstance(mapping_scope, str) or not mapping_scope or not isinstance(document, str):
        raise TMPage31MappingError("TM page-31 mapping scope is invalid")
    return TMPage31MappingPolicy(
        source_path=path,
        document=document,
        page_number=31,
        page_tag="page-0031",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=mapping_scope,
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        schema_total=_positive_int(payload, "schema_total"),
        minimum_visible_label_similarity=float(minimum_similarity),
        rows=tuple(rows),
        not_observed_schema_ids=not_observed,
        not_applicable_schema_ids=not_applicable,
        forbidden_mapping_inputs=tuple(str(value) for value in forbidden),
        policy_sha256=sha256_file(path),
    )


def _label_similarity(visible: str, anchor: str) -> float:
    visible_key = retrieval_key(visible)
    if not visible_key or not anchor:
        return 0.0
    if visible_key in anchor or anchor in visible_key:
        return 1.0
    return ratio(visible_key, anchor) / 100


def _schema_projection_sha256(items: tuple[SchemaItem, ...]) -> str:
    payload = [
        {
            "report_norm_id": item.schema_id,
            "display_order": item.display_order,
            "canonical_name": item.canonical_name,
        }
        for item in items
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _accounting_checks(parsed: ParsedTMPage31) -> tuple[TMPage31AccountingCheck, ...]:
    rows = {(row.table_key, row.ordinal): row for row in parsed.rows}

    def value(table_key: str, ordinal: int, axis_index: int) -> Decimal:
        observed = rows[(table_key, ordinal)].row.cells[axis_index].value
        if observed is None:
            raise TMPage31MappingError("TM page-31 accounting row contains a blank value")
        return observed

    equations = (
        ("SECURITIES_CHILDREN_TO_GROSS", "SECURITIES", (2, 3, 5, 6), 7),
        ("SECURITIES_GROSS_PLUS_PROVISION_TO_NET", "SECURITIES", (7, 8), 9),
        ("LOAN_TYPE_CHILDREN_TO_SUBTOTAL", "LOAN_TYPE", (2, 3, 4, 5, 6), 7),
        ("LOAN_TYPE_SUBTOTAL_PLUS_MARGIN_TO_GRAND_TOTAL", "LOAN_TYPE", (7, 8), 9),
        ("LOAN_QUALITY_GROUPS_TO_GRAND_TOTAL", "LOAN_QUALITY", (2, 4, 5, 6, 7), 8),
        ("LOAN_MATURITY_BUCKETS_TO_SUBTOTAL", "LOAN_MATURITY", (2, 3, 4), 5),
        ("LOAN_MATURITY_SUBTOTAL_PLUS_MARGIN_TO_GRAND_TOTAL", "LOAN_MATURITY", (5, 6), 7),
    )
    result = []
    for check_id, table_key, component_ordinals, total_ordinal in equations:
        table = next(table for table in parsed.tables if table.table_key == table_key)
        for axis_index, axis in enumerate(table.axes):
            expected = sum(
                (value(table_key, ordinal, axis_index) for ordinal in component_ordinals),
                Decimal(0),
            )
            observed = value(table_key, total_ordinal, axis_index)
            residual = observed - expected
            result.append(
                TMPage31AccountingCheck(
                    check_id=check_id,
                    axis_role=axis.current_or_comparative,
                    expected_value=expected,
                    observed_value=observed,
                    residual=residual,
                    status="PASS" if residual == 0 else "FAIL",
                )
            )
    return tuple(result)


def reconcile_tm_page31_items(
    parsed: ParsedTMPage31,
    *,
    schema: list[SchemaItem],
    policy: TMPage31MappingPolicy,
    source_pdf_path: Path,
    source_render_path: Path,
) -> TMPage31MappingResult:
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
    ):
        raise TMPage31MappingError("TM page-31 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage31MappingError("TM page-31 source PDF hash drifted")
    if sha256_file(source_render_path) != policy.source_render_sha256:
        raise TMPage31MappingError("TM page-31 source render hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"), key=lambda x: x.display_order
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE31_SCHEMA_TOTAL:
        raise TMPage31MappingError("TM schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    classified_ids = (
        {
            schema_id
            for rule in policy.rows
            if rule.disposition is TMPage31RuleDisposition.FIXED
            for schema_id in (rule.report_norm_id, *rule.additional_report_norm_ids)
        }
        | set(policy.not_observed_schema_ids)
        | set(policy.not_applicable_schema_ids)
    )
    if not classified_ids <= set(schema_by_id):
        raise TMPage31MappingError("TM page-31 policy references unknown ReportNormIds")
    parsed_by_identity = {(row.table_key, row.ordinal): row for row in parsed.rows}
    if tuple(parsed_by_identity) != tuple(rule.identity for rule in policy.rows):
        raise TMPage31MappingError("TM page-31 parsed row order drifted from mapping policy")

    source_dispositions = []
    source_rows_by_schema: dict[int, list[str]] = {}
    for rule in policy.rows:
        row = parsed_by_identity[rule.identity]
        if row.row_kind.value != rule.expected_row_kind:
            raise TMPage31MappingError(f"TM page-31 row kind drifted: {row.row_id}")
        if rule.visible_label_anchor is None:
            if row.row.label:
                raise TMPage31MappingError(f"TM page-31 expected an unlabeled total: {row.row_id}")
            similarity = None
        else:
            similarity = _label_similarity(row.row.label, rule.visible_label_anchor)
            if similarity < policy.minimum_visible_label_similarity:
                raise TMPage31MappingError(
                    f"TM page-31 visible label is below its fixed anchor: {row.row_id}"
                )
        if rule.disposition is TMPage31RuleDisposition.FIXED:
            assert rule.report_norm_id is not None
            mapped_ids = (rule.report_norm_id, *rule.additional_report_norm_ids)
            items = tuple(schema_by_id[schema_id] for schema_id in mapped_ids)
            item = items[0]
            status = TMPage31SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            canonical_name = item.canonical_name
            canonical_names = tuple(mapped.canonical_name for mapped in items)
            assignment_roles = rule.assignment_roles or ("PRIMARY",)
            for schema_id in mapped_ids:
                source_rows_by_schema.setdefault(schema_id, []).append(row.row_id)
            reason = (
                "authorized legacy-global plus context-branch dual assignment with one source-cell provenance"
                if len(mapped_ids) > 1
                else "fixed source-page hierarchy/order and visible-label rule passed"
            )
        else:
            mapped_ids = ()
            status = TMPage31SourceStatus.SOURCE_ONLY_VALIDATION.value
            canonical_name = None
            canonical_names = ()
            assignment_roles = ()
            reason = (
                "repeated total, subtotal, or duplicate MBS amount retained for validation only"
            )
        table = next(item for item in parsed.tables if item.table_key == row.table_key)
        source_dispositions.append(
            TMPage31SourceDisposition(
                row_id=row.row_id,
                table_key=row.table_key,
                ordinal=row.ordinal,
                visible_label=row.row.label,
                row_kind=row.row_kind.value,
                source_role=row.source_role,
                status=status,
                report_norm_id=rule.report_norm_id,
                canonical_name=canonical_name,
                report_norm_ids=mapped_ids,
                canonical_names=canonical_names,
                assignment_roles=assignment_roles,
                visible_label_similarity=similarity,
                observations=tuple(cell.observation.value for cell in row.row.cells),
                values=tuple(cell.value for cell in row.row.cells),
                period_ends=tuple(axis.period_end.isoformat() for axis in table.axes),
                unit=table.axes[0].canonical_unit,
                unit_multiplier=table.axes[0].unit_multiplier,
                reason=reason,
            )
        )

    checks = _accounting_checks(parsed)
    if len(checks) != TM_PAGE31_ACCOUNTING_CHECK_COUNT or any(
        check.status != "PASS" for check in checks
    ):
        raise TMPage31MappingError("TM page-31 accounting validation did not pass 14/14 checks")
    schema_dispositions = []
    not_observed = set(policy.not_observed_schema_ids)
    not_applicable = set(policy.not_applicable_schema_ids)
    for item in tm_schema:
        if item.schema_id in source_rows_by_schema:
            status = TMPage31SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_row_ids = tuple(source_rows_by_schema[item.schema_id])
            reason = "one primary page-31 source row passed the scoped fixed mapping rule"
        elif item.schema_id in not_observed:
            status = TMPage31SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            source_row_ids = ()
            reason = (
                "schema item belongs to the complete visible page-31 branch but no row was observed"
            )
        elif item.schema_id in not_applicable:
            status = TMPage31SchemaStatus.SCHEMA_ITEM_NOT_APPLICABLE.value
            source_row_ids = ()
            reason = "alternative organization-based securities classification was not the PDF presentation"
        else:
            status = TMPage31SchemaStatus.UNASSESSED.value
            source_row_ids = ()
            reason = "outside the page-31 branches assessed by this source-scoped mapping"
        schema_dispositions.append(
            TMPage31SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status,
                source_row_ids=source_row_ids,
                reason=reason,
            )
        )
    mapped_value_count = sum(
        observation in {ObservationKind.VALUE.value, ObservationKind.ZERO.value}
        for item in source_dispositions
        if item.status == TMPage31SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        for observation in item.observations
    )
    mapped_value_assignment_count = sum(
        observation in {ObservationKind.VALUE.value, ObservationKind.ZERO.value}
        for item in source_dispositions
        for _schema_id in item.report_norm_ids
        for observation in item.observations
    )
    result = TMPage31MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=policy.page_number,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="SCOPED_PAGE31_MAPPING_WITH_COMPLETE_ACCOUNTING_VALIDATION",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=len(classified_ids),
        mapped_schema_count=len(source_rows_by_schema),
        not_observed_schema_count=len(not_observed),
        not_applicable_schema_count=len(not_applicable),
        unassessed_schema_count=len(tm_schema) - len(classified_ids),
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMPage31SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status == TMPage31SourceStatus.SOURCE_ONLY_VALIDATION.value
            for item in source_dispositions
        ),
        numeric_source_row_count=parsed.numeric_row_count,
        structural_blank_source_row_count=parsed.label_only_row_count,
        extracted_value_count=parsed.numeric_cell_count,
        mapped_value_count=mapped_value_count,
        mapped_value_assignment_count=mapped_value_assignment_count,
        accounting_check_count=len(checks),
        accounting_pass_count=sum(check.status == "PASS" for check in checks),
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        accounting_checks=checks,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        schema_projection_sha256=_schema_projection_sha256(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS",
            "VISIBLE_PAGE31_NOTE_AND_SUBTABLE_ORDER",
            "SOURCE_RENDER_SHA256",
            "TM_SCHEMA_ID_NAME_ORDER",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
        ),
    )
    return validate_tm_page31_mapping_result(result)


def validate_tm_page31_mapping_result(
    result: TMPage31MappingResult,
) -> TMPage31MappingResult:
    if (
        result.schema_item_count != TM_PAGE31_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE31_ASSESSED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE31_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE31_NOT_OBSERVED_COUNT
        or result.not_applicable_schema_count != TM_PAGE31_NOT_APPLICABLE_COUNT
        or result.unassessed_schema_count != TM_PAGE31_UNASSESSED_SCHEMA_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE31_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE31_MAPPED_SOURCE_COUNT
        or result.source_only_row_count != TM_PAGE31_SOURCE_ONLY_COUNT
        or result.numeric_source_row_count != 28
        or result.structural_blank_source_row_count != TM_PAGE31_STRUCTURAL_BLANK_ROW_COUNT
        or result.extracted_value_count != TM_PAGE31_EXTRACTED_VALUE_COUNT
        or result.mapped_value_count != TM_PAGE31_MAPPED_VALUE_COUNT
        or result.mapped_value_assignment_count != TM_PAGE31_MAPPED_VALUE_ASSIGNMENT_COUNT
        or result.accounting_check_count != TM_PAGE31_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_PAGE31_ACCOUNTING_CHECK_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage31MappingError("TM page-31 mapping result denominator drifted")
    if (
        result.mapped_schema_count
        + result.not_observed_schema_count
        + result.not_applicable_schema_count
        + result.unassessed_schema_count
        != result.schema_item_count
    ):
        raise TMPage31MappingError("TM page-31 schema statuses do not reconcile")
    mapped_ids = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage31SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    if (
        len(mapped_ids) != TM_PAGE31_MAPPED_SCHEMA_COUNT
        or not {
            1944,
            5745,
            5746,
            5747,
        }
        <= mapped_ids
    ):
        raise TMPage31MappingError("TM page-31 mapped ReportNormId set drifted")
    dual = [item for item in result.source_dispositions if len(item.report_norm_ids) > 1]
    if (
        len(dual) != 1
        or dual[0].report_norm_ids != (1944, 5745)
        or dual[0].assignment_roles != ("LEGACY_GLOBAL_PRIMARY", "CONTEXT_BRANCH_MEMBER")
    ):
        raise TMPage31MappingError("TM page-31 dual-assignment result drifted")
    if any(check.residual != 0 or check.status != "PASS" for check in result.accounting_checks):
        raise TMPage31MappingError("TM page-31 accounting residual is non-zero")
    return result


__all__ = [
    "TM_PAGE31_POLICY_RELATIVE_PATH",
    "TMPage31AccountingCheck",
    "TMPage31MappingError",
    "TMPage31MappingPolicy",
    "TMPage31MappingResult",
    "TMPage31SchemaDisposition",
    "TMPage31SchemaStatus",
    "TMPage31SourceDisposition",
    "TMPage31SourceStatus",
    "load_tm_page31_mapping_policy",
    "reconcile_tm_page31_items",
    "validate_tm_page31_mapping_result",
]
