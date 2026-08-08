"""Source-scoped TM mapping for MBB page 36."""

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
from bctc_ai.evaluation.word_box_rows import VisualCellEvidence
from bctc_ai.schema.registry import SchemaItem
from bctc_ai.tables.tm_note_page36 import ParsedTMPage36
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind

TM_PAGE36_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page36-v1.yaml")
TM_PAGE36_SCHEMA_TOTAL = 1_613
TM_PAGE36_RECONCILED_SCHEMA_COUNT = 39
TM_PAGE36_MAPPED_SCHEMA_COUNT = 8
TM_PAGE36_NOT_OBSERVED_COUNT = 31
TM_PAGE36_UNASSESSED_COUNT = 1_574
TM_PAGE36_SOURCE_ROW_COUNT = 14
TM_PAGE36_MAPPED_SOURCE_COUNT = 8
TM_PAGE36_SOURCE_ONLY_COUNT = 6
TM_PAGE36_FINANCIAL_SLOT_COUNT = 26
TM_PAGE36_VALUE_COUNT = 26
TM_PAGE36_DASH_COUNT = 0
TM_PAGE36_MAPPED_VALUE_COUNT = 16
TM_PAGE36_ACCOUNTING_CHECK_COUNT = 8
TM_PAGE36_ACCOUNTING_PASS_COUNT = 8
TM_PAGE36_DUPLICATE_CHECK_COUNT = 4

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "accounting_equation_result_as_item_selector",
}
_SCOPED_IDS = set(range(829, 868))
_MAPPED_IDS = {829, 831, 832, 833, 848, 849, 862, 867}


class TMPage36MappingError(ValueError):
    pass


class TMPage36RuleDisposition(StrEnum):
    FIXED = "FIXED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"


class TMPage36SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage36SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"


@dataclass(frozen=True)
class TMPage36RowRule:
    table_key: str
    ordinal: int
    visible_label_anchor: str | None
    expected_row_kind: str
    expected_observations: tuple[str, ...]
    disposition: TMPage36RuleDisposition
    report_norm_id: int | None
    candidate_report_norm_ids: tuple[int, ...]

    @property
    def identity(self) -> tuple[str, int]:
        return self.table_key, self.ordinal


@dataclass(frozen=True)
class TMPage36MappingPolicy:
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
    rows: tuple[TMPage36RowRule, ...]
    not_observed_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage36SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage36SourceDisposition:
    row_id: str
    table_key: str
    ordinal: int
    visible_label: str
    row_kind: str
    source_role: str
    status: str
    report_norm_id: int | None
    canonical_name: str | None
    candidate_report_norm_ids: tuple[int, ...]
    candidate_canonical_names: tuple[str, ...]
    visible_label_similarity: float | None
    observations: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    period_ends: tuple[str, ...]
    unit: str
    unit_multiplier: int
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage36AccountingCheck:
    check_id: str
    axis_role: str
    status: str
    expected_value: Decimal
    observed_value: Decimal
    residual: Decimal
    reason: str


@dataclass(frozen=True)
class TMPage36DuplicateCheck:
    check_id: str
    axis_role: str
    primary_value: Decimal
    duplicate_value: Decimal
    residual: Decimal
    status: str


@dataclass(frozen=True)
class TMPage36MappingResult:
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
    accounting_check_count: int
    accounting_pass_count: int
    duplicate_check_count: int
    duplicate_pass_count: int
    schema_dispositions: tuple[TMPage36SchemaDisposition, ...]
    source_dispositions: tuple[TMPage36SourceDisposition, ...]
    accounting_checks: tuple[TMPage36AccountingCheck, ...]
    duplicate_checks: tuple[TMPage36DuplicateCheck, ...]
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    schema_projection_sha256: str
    policy_sha256: str
    mapping_inputs: tuple[str, ...]


def _positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TMPage36MappingError(f"invalid positive TM page-36 field: {field}")
    return value


def _ids(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(payload, list)
        or (not payload and not allow_empty)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload)
    ):
        raise TMPage36MappingError(f"TM page-36 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMPage36MappingError(f"TM page-36 {field} contains duplicates")
    return result


def load_tm_page36_mapping_policy(path: Path) -> TMPage36MappingPolicy:
    """Load and validate page-36 fixed-row mapping authority."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage36MappingError(f"cannot load TM page-36 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE36_SCOPED_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 36
        or payload.get("page_tag") != "page-0036"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage36MappingError("TM page-36 mapping policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage36MappingError("TM page-36 mapping source hashes are invalid")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 < float(threshold) <= 1
    ):
        raise TMPage36MappingError("TM page-36 mapping similarity threshold is invalid")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE36_SOURCE_ROW_COUNT:
        raise TMPage36MappingError("TM page-36 mapping row denominator drifted")
    valid_observations = {observation.value for observation in ObservationKind}
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage36MappingError("TM page-36 mapping row is invalid")
        table_key = record.get("table_key")
        ordinal = record.get("ordinal")
        label = record.get("visible_label_anchor")
        row_kind = record.get("expected_row_kind")
        observations = record.get("expected_observations")
        report_norm_id = record.get("report_norm_id")
        try:
            disposition = TMPage36RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMPage36MappingError("TM page-36 rule disposition is invalid") from exc
        candidates = _ids(
            record.get("candidate_report_norm_ids"), "candidate ReportNormIds", allow_empty=True
        )
        if (
            not isinstance(table_key, str)
            or not table_key
            or isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal <= 0
            or (label is not None and not isinstance(label, str))
            or row_kind not in {kind.value for kind in TMNoteRowKind}
            or not isinstance(observations, list)
            or len(observations) != 2
            or any(value not in valid_observations for value in observations)
        ):
            raise TMPage36MappingError("TM page-36 mapping row identity is invalid")
        if disposition is TMPage36RuleDisposition.FIXED:
            if (
                isinstance(report_norm_id, bool)
                or not isinstance(report_norm_id, int)
                or candidates
            ):
                raise TMPage36MappingError("fixed TM page-36 mapping rule is malformed")
        elif report_norm_id is not None:
            raise TMPage36MappingError("source-only TM page-36 row cannot select a ReportNormId")
        rows.append(
            TMPage36RowRule(
                table_key=table_key,
                ordinal=ordinal,
                visible_label_anchor=retrieval_key(label) if label is not None else None,
                expected_row_kind=row_kind,
                expected_observations=tuple(observations),
                disposition=disposition,
                report_norm_id=report_norm_id,
                candidate_report_norm_ids=candidates,
            )
        )
    if len({row.identity for row in rows}) != len(rows):
        raise TMPage36MappingError("TM page-36 rule identities are duplicated")
    fixed_ids = {
        row.report_norm_id for row in rows if row.disposition is TMPage36RuleDisposition.FIXED
    }
    if fixed_ids != _MAPPED_IDS:
        raise TMPage36MappingError("TM page-36 fixed ReportNormIds drifted")
    not_observed = _ids(payload.get("not_observed_schema_ids"), "not-observed IDs")
    if (
        len(not_observed) != TM_PAGE36_NOT_OBSERVED_COUNT
        or fixed_ids & set(not_observed)
        or fixed_ids | set(not_observed) != _SCOPED_IDS
    ):
        raise TMPage36MappingError("TM page-36 complete branch statuses drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage36MappingError("TM page-36 forbidden mapping inputs drifted")
    document = payload.get("document")
    mapping_scope = payload.get("mapping_authority_scope")
    if not isinstance(document, str) or not isinstance(mapping_scope, str) or not mapping_scope:
        raise TMPage36MappingError("TM page-36 mapping scope is invalid")
    return TMPage36MappingPolicy(
        source_path=path,
        document=document,
        page_number=36,
        page_tag="page-0036",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=mapping_scope,
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        schema_total=_positive_int(payload, "schema_total"),
        minimum_visible_label_similarity=float(threshold),
        rows=tuple(rows),
        not_observed_schema_ids=not_observed,
        forbidden_mapping_inputs=tuple(str(value) for value in forbidden),
        policy_sha256=sha256_file(path),
    )


def _similarity(visible: str, anchor: str) -> float:
    key = retrieval_key(visible)
    if not key or not anchor:
        return 0.0
    if key in anchor or anchor in key:
        return 1.0
    return ratio(key, anchor) / 100


def _schema_hash(items: tuple[SchemaItem, ...]) -> str:
    payload = [(item.schema_id, item.display_order, item.canonical_name) for item in items]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode("utf-8")).hexdigest()


def _value(parsed: ParsedTMPage36, table_key: str, ordinal: int, axis: int) -> Decimal:
    row = next(row for row in parsed.rows if row.table_key == table_key and row.ordinal == ordinal)
    value = row.row.cells[axis].value
    if value is None:
        raise TMPage36MappingError("TM page-36 numeric validation received a non-value cell")
    return value


def _validation(
    parsed: ParsedTMPage36,
) -> tuple[tuple[TMPage36AccountingCheck, ...], tuple[TMPage36DuplicateCheck, ...]]:
    same_table_equations = (
        ("HTM_GROSS_EQUALS_THREE_VISIBLE_DEBT_CLASSES", "HTM_SECURITIES", (2, 3, 4), 5),
        ("HTM_NET_EQUALS_GROSS_PLUS_PROVISION", "HTM_SECURITIES", (5, 6), 7),
        ("LONG_TERM_NET_EQUALS_GROSS_PLUS_PROVISION", "LONG_TERM_NET", (1, 3), 4),
    )
    accounting = []
    for check_id, table_key, components, total in same_table_equations:
        table = next(table for table in parsed.tables if table.table_key == table_key)
        for axis_index, axis in enumerate(table.axes):
            expected = sum(
                (_value(parsed, table_key, ordinal, axis_index) for ordinal in components),
                Decimal(0),
            )
            observed = _value(parsed, table_key, total, axis_index)
            residual = observed - expected
            accounting.append(
                TMPage36AccountingCheck(
                    check_id=check_id,
                    axis_role=axis.current_or_comparative,
                    status="PASS" if residual == 0 else "FAIL",
                    expected_value=expected,
                    observed_value=observed,
                    residual=residual,
                    reason="visible numeric values combined only as post-mapping validation",
                )
            )
    detail = next(table for table in parsed.tables if table.table_key == "LONG_TERM_DETAIL")
    for axis_index, axis in enumerate(detail.axes):
        expected = _value(parsed, "LONG_TERM_DETAIL", 1, axis_index) + _value(
            parsed, "LONG_TERM_DETAIL", 2, axis_index
        )
        observed = _value(parsed, "LONG_TERM_NET", 1, axis_index)
        residual = observed - expected
        accounting.append(
            TMPage36AccountingCheck(
                check_id="LONG_TERM_GROSS_EQUALS_TWO_VISIBLE_DETAILS",
                axis_role=axis.current_or_comparative,
                status="PASS" if residual == 0 else "FAIL",
                expected_value=expected,
                observed_value=observed,
                residual=residual,
                reason="visible numeric values combined only as post-mapping validation",
            )
        )
    duplicates = []
    for axis_index, axis in enumerate(detail.axes):
        primary = _value(parsed, "LONG_TERM_NET", 1, axis_index)
        for check_id, table_key, ordinal in (
            ("LONG_TERM_MAIN_SUBTOTAL_DUPLICATES_PRIMARY_GROSS", "LONG_TERM_NET", 2),
            ("LONG_TERM_DETAIL_TOTAL_DUPLICATES_PRIMARY_GROSS", "LONG_TERM_DETAIL", 3),
        ):
            duplicate = _value(parsed, table_key, ordinal, axis_index)
            residual = duplicate - primary
            duplicates.append(
                TMPage36DuplicateCheck(
                    check_id=check_id,
                    axis_role=axis.current_or_comparative,
                    primary_value=primary,
                    duplicate_value=duplicate,
                    residual=residual,
                    status="PASS" if residual == 0 else "FAIL",
                )
            )
    return tuple(accounting), tuple(duplicates)


def _source_only_reason(rule: TMPage36RowRule) -> str:
    if rule.identity == ("HTM_SECURITIES", 1):
        return "structural heading retained as provenance; numeric net row is the primary ID 829"
    if rule.identity in {("LONG_TERM_NET", 2), ("LONG_TERM_DETAIL", 3)}:
        return (
            "visible duplicate of primary ID 867 retained for validation without duplicate export"
        )
    if rule.identity == ("LONG_TERM_NET", 3):
        return "visible long-term-investment provision has no dedicated item in scoped IDs 829-867"
    return (
        "visible detail decomposes ID 867, but the scoped schema has no distinct child item; "
        "retained source-only to avoid duplicate target export"
    )


def reconcile_tm_page36_items(
    parsed: ParsedTMPage36,
    *,
    schema: list[SchemaItem],
    policy: TMPage36MappingPolicy,
    source_pdf_path: Path,
) -> TMPage36MappingResult:
    """Map fixed primary rows and reconcile the entire visible 829-867 branch."""

    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
    ):
        raise TMPage36MappingError("TM page-36 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage36MappingError("TM page-36 source PDF hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE36_SCHEMA_TOTAL:
        raise TMPage36MappingError("TM schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    referenced = (
        {rule.report_norm_id for rule in policy.rows if rule.report_norm_id is not None}
        | {candidate for rule in policy.rows for candidate in rule.candidate_report_norm_ids}
        | set(policy.not_observed_schema_ids)
    )
    if not referenced <= set(schema_by_id):
        raise TMPage36MappingError("TM page-36 policy references unknown ReportNormIds")
    parsed_by_identity = {(row.table_key, row.ordinal): row for row in parsed.rows}
    if tuple(parsed_by_identity) != tuple(rule.identity for rule in policy.rows):
        raise TMPage36MappingError("TM page-36 parsed row order drifted from policy")
    source_dispositions = []
    source_rows_by_schema: dict[int, list[str]] = {}
    for rule in policy.rows:
        row = parsed_by_identity[rule.identity]
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if (
            row.row_kind.value != rule.expected_row_kind
            or observations != rule.expected_observations
        ):
            raise TMPage36MappingError(f"TM page-36 row status drifted: {row.row_id}")
        if rule.visible_label_anchor is None:
            if row.row.label:
                raise TMPage36MappingError(f"TM page-36 expected unlabeled total: {row.row_id}")
            similarity = None
        else:
            similarity = _similarity(row.row.label, rule.visible_label_anchor)
            if similarity < policy.minimum_visible_label_similarity:
                raise TMPage36MappingError(f"TM page-36 label anchor failed: {row.row_id}")
        if rule.disposition is TMPage36RuleDisposition.FIXED:
            assert rule.report_norm_id is not None
            item = schema_by_id[rule.report_norm_id]
            status = TMPage36SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            canonical = item.canonical_name
            source_rows_by_schema.setdefault(item.schema_id, []).append(row.row_id)
            question_required = False
            reason = "fixed page-36 hierarchy/order and visible-label rule passed"
        else:
            canonical = None
            question_required = rule.disposition is TMPage36RuleDisposition.SOURCE_ONLY_QUESTION
            status = (
                TMPage36SourceStatus.SOURCE_ONLY_QUESTION.value
                if question_required
                else TMPage36SourceStatus.SOURCE_ONLY_VALIDATION.value
            )
            reason = _source_only_reason(rule)
        table = next(table for table in parsed.tables if table.table_key == row.table_key)
        source_dispositions.append(
            TMPage36SourceDisposition(
                row_id=row.row_id,
                table_key=row.table_key,
                ordinal=row.ordinal,
                visible_label=row.row.label,
                row_kind=row.row_kind.value,
                source_role=row.source_role,
                status=status,
                report_norm_id=rule.report_norm_id,
                canonical_name=canonical,
                candidate_report_norm_ids=rule.candidate_report_norm_ids,
                candidate_canonical_names=tuple(
                    schema_by_id[candidate].canonical_name
                    for candidate in rule.candidate_report_norm_ids
                ),
                visible_label_similarity=similarity,
                observations=observations,
                values=tuple(cell.value for cell in row.row.cells),
                period_ends=tuple(axis.period_end.isoformat() for axis in table.axes),
                unit=table.axes[0].canonical_unit,
                unit_multiplier=table.axes[0].unit_multiplier,
                visual_cell_evidence=row.visual_cell_evidence,
                question_required=question_required,
                reason=reason,
            )
        )
    accounting, duplicates = _validation(parsed)
    if (
        len(accounting) != TM_PAGE36_ACCOUNTING_CHECK_COUNT
        or any(check.status != "PASS" for check in accounting)
        or len(duplicates) != TM_PAGE36_DUPLICATE_CHECK_COUNT
        or any(check.status != "PASS" for check in duplicates)
    ):
        raise TMPage36MappingError("TM page-36 accounting or duplicate validation failed")
    not_observed = set(policy.not_observed_schema_ids)
    schema_dispositions = []
    for item in tm_schema:
        if item.schema_id in source_rows_by_schema:
            status = TMPage36SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_ids = tuple(source_rows_by_schema[item.schema_id])
            reason = "one primary page-36 row passed its source-scoped fixed mapping"
        elif item.schema_id in not_observed:
            status = TMPage36SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            source_ids = ()
            reason = "item belongs to fully assessed IDs 829-867 but was not visible"
        else:
            status = TMPage36SchemaStatus.UNASSESSED.value
            source_ids = ()
            reason = "outside the page-36 branch assessed by this mapping"
        schema_dispositions.append(
            TMPage36SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status,
                source_row_ids=source_ids,
                reason=reason,
            )
        )
    mapped_values = sum(
        observation in {ObservationKind.VALUE.value, ObservationKind.ZERO.value}
        for item in source_dispositions
        if item.status == TMPage36SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        for observation in item.observations
    )
    result = TMPage36MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=36,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="SCOPED_PAGE36_MAPPING_WITH_OPEN_SOURCE_QUESTIONS",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=len(source_rows_by_schema) + len(not_observed),
        mapped_schema_count=len(source_rows_by_schema),
        not_observed_schema_count=len(not_observed),
        not_applicable_schema_count=0,
        ambiguous_schema_count=0,
        unassessed_schema_count=len(tm_schema) - len(source_rows_by_schema) - len(not_observed),
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMPage36SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status != TMPage36SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        source_question_row_count=sum(item.question_required for item in source_dispositions),
        ambiguous_source_row_count=sum(
            bool(item.candidate_report_norm_ids)
            and item.status == TMPage36SourceStatus.SOURCE_ONLY_QUESTION.value
            for item in source_dispositions
        ),
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_value_count=mapped_values,
        accounting_check_count=len(accounting),
        accounting_pass_count=sum(check.status == "PASS" for check in accounting),
        duplicate_check_count=len(duplicates),
        duplicate_pass_count=sum(check.status == "PASS" for check in duplicates),
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        accounting_checks=accounting,
        duplicate_checks=duplicates,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS",
            "VISIBLE_PAGE36_NOTE_AND_LOCAL_ROW_ORDER",
            "SOURCE_RENDER_SHA256",
            "TM_SCHEMA_ID_NAME_ORDER",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
        ),
    )
    return validate_tm_page36_mapping_result(result)


def validate_tm_page36_mapping_result(
    result: TMPage36MappingResult,
) -> TMPage36MappingResult:
    """Fail closed if any page-36 business denominator drifts."""

    if (
        result.schema_item_count != TM_PAGE36_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE36_RECONCILED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE36_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE36_NOT_OBSERVED_COUNT
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE36_UNASSESSED_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE36_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE36_MAPPED_SOURCE_COUNT
        or result.source_only_row_count != TM_PAGE36_SOURCE_ONLY_COUNT
        or result.source_question_row_count != 3
        or result.ambiguous_source_row_count != 2
        or result.financial_slot_count != TM_PAGE36_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE36_VALUE_COUNT
        or result.dash_count != TM_PAGE36_DASH_COUNT
        or result.mapped_value_count != TM_PAGE36_MAPPED_VALUE_COUNT
        or result.accounting_check_count != TM_PAGE36_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_PAGE36_ACCOUNTING_PASS_COUNT
        or result.duplicate_check_count != TM_PAGE36_DUPLICATE_CHECK_COUNT
        or result.duplicate_pass_count != TM_PAGE36_DUPLICATE_CHECK_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage36MappingError("TM page-36 mapping result denominator drifted")
    if (
        result.mapped_schema_count
        + result.not_observed_schema_count
        + result.unassessed_schema_count
        != result.schema_item_count
    ):
        raise TMPage36MappingError("TM page-36 schema statuses do not reconcile")
    mapped_ids = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage36SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    if mapped_ids != _MAPPED_IDS:
        raise TMPage36MappingError("TM page-36 mapped ReportNormIds drifted")
    return result


__all__ = [
    "TM_PAGE36_POLICY_RELATIVE_PATH",
    "TMPage36AccountingCheck",
    "TMPage36DuplicateCheck",
    "TMPage36MappingError",
    "TMPage36MappingPolicy",
    "TMPage36MappingResult",
    "TMPage36SchemaDisposition",
    "TMPage36SchemaStatus",
    "TMPage36SourceDisposition",
    "TMPage36SourceStatus",
    "load_tm_page36_mapping_policy",
    "reconcile_tm_page36_items",
    "validate_tm_page36_mapping_result",
]
