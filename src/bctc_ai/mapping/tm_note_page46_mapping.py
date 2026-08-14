"""Source-scoped item mapping for the two KQKD notes on MBB TM page 46."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
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
from bctc_ai.tables.tm_note_page46 import ParsedTMPage46

TM_PAGE46_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page46-v1.yaml")
TM_PAGE46_SCHEMA_TOTAL = 1_710
TM_PAGE46_RECONCILED_SCHEMA_COUNT = 43
TM_PAGE46_MAPPED_SCHEMA_COUNT = 33
TM_PAGE46_AMBIGUOUS_SCHEMA_COUNT = 0
TM_PAGE46_NOT_OBSERVED_COUNT = 10
TM_PAGE46_UNASSESSED_COUNT = 1_667
TM_PAGE46_SOURCE_ROW_COUNT = 38
TM_PAGE46_MAPPED_SOURCE_COUNT = 32
TM_PAGE46_AMBIGUOUS_SOURCE_COUNT = 0
TM_PAGE46_SOURCE_ONLY_COUNT = 6
TM_PAGE46_QUESTION_SOURCE_COUNT = 0
TM_PAGE46_FINANCIAL_SLOT_COUNT = 62
TM_PAGE46_VALUE_COUNT = 60
TM_PAGE46_DASH_COUNT = 2
TM_PAGE46_MAPPED_VALUE_COUNT = 60
TM_PAGE46_DERIVED_ASSIGNMENT_COUNT = 2
TM_PAGE46_ACCOUNTING_CHECK_COUNT = 12
TM_PAGE46_ACCOUNTING_PASS_COUNT = 10
TM_PAGE46_ACCOUNTING_NOT_TESTABLE_COUNT = 2

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ADDITIONAL_SCOPED_IDS = {5985, 5986, 5987, 5988, 5989, *range(6021, 6026)}
_SCOPED_IDS = set(range(1142, 1175)) | _ADDITIONAL_SCOPED_IDS
_MAPPED_IDS = {
    1142,
    1143,
    1144,
    1145,
    1146,
    1148,
    1149,
    1150,
    1151,
    1152,
    1153,
    1154,
    1156,
    1157,
    1160,
    1163,
    1164,
    1166,
    1167,
    1170,
    1171,
    1172,
    1174,
    5985,
    5986,
    5987,
    5988,
    5989,
    *range(6021, 6026),
}
_AMBIGUOUS_IDS: set[int] = set()
_NOT_OBSERVED_IDS = {1147, 1155, 1158, 1159, 1161, 1162, 1165, 1168, 1169, 1173}
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
    "accounting_equation_result_as_extracted_value",
}


class TMPage46MappingError(ValueError):
    pass


class TMPage46RuleDisposition(StrEnum):
    FIXED = "FIXED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"


class TMPage46SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage46SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"


@dataclass(frozen=True)
class TMPage46RowRule:
    table_key: str
    ordinal: int
    visible_label_anchor: str | None
    expected_row_kind: str
    expected_observations: tuple[str, ...]
    disposition: TMPage46RuleDisposition
    report_norm_id: int | None
    candidate_report_norm_ids: tuple[int, ...]

    @property
    def identity(self) -> tuple[str, int]:
        return self.table_key, self.ordinal


@dataclass(frozen=True)
class TMPage46MappingPolicy:
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
    scoped_schema_id_start: int
    scoped_schema_id_end: int
    additional_scoped_schema_ids: tuple[int, ...]
    minimum_visible_label_similarity: float
    rows: tuple[TMPage46RowRule, ...]
    ambiguous_schema_ids: tuple[int, ...]
    not_observed_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage46SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage46SourceDisposition:
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
    period_starts: tuple[str | None, ...]
    period_ends: tuple[str | None, ...]
    period_roles: tuple[str | None, ...]
    unit: str
    unit_multiplier: int
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage46AccountingCheck:
    check_id: str
    axis_role: str
    status: str
    expected_value: Decimal | None
    observed_value: Decimal | None
    residual: Decimal | None
    reason: str


@dataclass(frozen=True)
class TMPage46DerivedAssignment:
    report_norm_id: int
    canonical_name: str
    component_report_norm_ids: tuple[int, ...]
    component_row_ids: tuple[str, ...]
    component_values: tuple[Decimal, ...]
    observation: str
    value: Decimal
    period_start: str
    period_end: str
    period_role: str
    period_type: str
    unit: str
    unit_multiplier: int
    mapping_basis: str


@dataclass(frozen=True)
class TMPage46MappingResult:
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
    ambiguous_schema_count: int
    not_observed_schema_count: int
    not_applicable_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    ambiguous_source_row_count: int
    source_only_row_count: int
    source_question_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_value_count: int
    derived_assignment_count: int
    accounting_check_count: int
    accounting_pass_count: int
    accounting_not_testable_count: int
    schema_dispositions: tuple[TMPage46SchemaDisposition, ...]
    source_dispositions: tuple[TMPage46SourceDisposition, ...]
    derived_assignments: tuple[TMPage46DerivedAssignment, ...]
    accounting_checks: tuple[TMPage46AccountingCheck, ...]
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    dash_pixel_evidence_sha256: str
    schema_projection_sha256: str
    policy_sha256: str
    mapping_inputs: tuple[str, ...]


def _positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TMPage46MappingError(f"invalid positive TM page-46 field: {field}")
    return value


def _ids(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(payload, list)
        or (not payload and not allow_empty)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload)
    ):
        raise TMPage46MappingError(f"TM page-46 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMPage46MappingError(f"TM page-46 {field} contains duplicates")
    return result


def load_tm_page46_mapping_policy(path: Path) -> TMPage46MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage46MappingError(f"cannot load TM page-46 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE46_SCOPED_DURATION_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 46
        or payload.get("page_tag") != "page-0046"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage46MappingError("TM page-46 mapping policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage46MappingError("TM page-46 mapping source hashes are invalid")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 <= threshold <= 1
    ):
        raise TMPage46MappingError("TM page-46 mapping similarity threshold is invalid")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE46_SOURCE_ROW_COUNT:
        raise TMPage46MappingError("TM page-46 mapping row denominator drifted")
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage46MappingError("TM page-46 mapping row is invalid")
        table_key = record.get("table_key")
        ordinal = record.get("ordinal")
        anchor = record.get("visible_label_anchor")
        row_kind = record.get("expected_row_kind")
        raw_observations = record.get("expected_observations")
        report_norm_id = record.get("report_norm_id")
        if (
            table_key not in {"NET_INTEREST", "NET_SERVICE"}
            or isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal <= 0
            or (anchor is not None and not isinstance(anchor, str))
            or row_kind not in {"NUMERIC", "LABEL_ONLY"}
            or not isinstance(raw_observations, list)
            or len(raw_observations) != 2
            or any(value not in {"VALUE", "DASH", "BLANK"} for value in raw_observations)
            or (
                report_norm_id is not None
                and (isinstance(report_norm_id, bool) or not isinstance(report_norm_id, int))
            )
        ):
            raise TMPage46MappingError("TM page-46 mapping row fields are invalid")
        try:
            disposition = TMPage46RuleDisposition(record.get("disposition"))
        except ValueError as exc:
            raise TMPage46MappingError("TM page-46 row disposition is invalid") from exc
        candidates = _ids(
            record.get("candidate_report_norm_ids"),
            "candidate ReportNormIds",
            allow_empty=True,
        )
        if disposition is TMPage46RuleDisposition.FIXED:
            if report_norm_id is None or candidates:
                raise TMPage46MappingError("TM page-46 fixed row binding is invalid")
        elif report_norm_id is not None:
            raise TMPage46MappingError("TM page-46 non-fixed row cannot carry a ReportNormId")
        if disposition is TMPage46RuleDisposition.AMBIGUOUS_MAPPING and not candidates:
            raise TMPage46MappingError("TM page-46 ambiguous row has no candidates")
        if disposition is not TMPage46RuleDisposition.AMBIGUOUS_MAPPING and candidates:
            raise TMPage46MappingError("TM page-46 non-ambiguous row has candidates")
        rows.append(
            TMPage46RowRule(
                table_key=table_key,
                ordinal=ordinal,
                visible_label_anchor=(retrieval_key(anchor) if anchor is not None else None),
                expected_row_kind=row_kind,
                expected_observations=tuple(raw_observations),
                disposition=disposition,
                report_norm_id=report_norm_id,
                candidate_report_norm_ids=candidates,
            )
        )
    identities = tuple(rule.identity for rule in rows)
    expected_identities = tuple(
        [("NET_INTEREST", ordinal) for ordinal in range(1, 18)]
        + [("NET_SERVICE", ordinal) for ordinal in range(1, 22)]
    )
    if identities != expected_identities:
        raise TMPage46MappingError("TM page-46 mapping row order drifted")
    ambiguous = _ids(payload.get("ambiguous_schema_ids"), "ambiguous schema IDs", allow_empty=True)
    not_observed = _ids(payload.get("not_observed_schema_ids"), "not-observed schema IDs")
    fixed_ids = {rule.report_norm_id for rule in rows if rule.report_norm_id is not None}
    candidate_ids = {candidate for rule in rows for candidate in rule.candidate_report_norm_ids}
    if (
        fixed_ids | {1170} != _MAPPED_IDS
        or set(ambiguous) != _AMBIGUOUS_IDS
        or candidate_ids != _AMBIGUOUS_IDS
        or set(not_observed) != _NOT_OBSERVED_IDS
        or fixed_ids | {1170} | set(ambiguous) | set(not_observed) != _SCOPED_IDS
    ):
        raise TMPage46MappingError("TM page-46 scoped schema partition drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage46MappingError("TM page-46 forbidden mapping inputs drifted")
    start = _positive_int(payload, "scoped_schema_id_start")
    end = _positive_int(payload, "scoped_schema_id_end")
    if (start, end) != (1142, 1174):
        raise TMPage46MappingError("TM page-46 scoped schema bounds drifted")
    additional_scoped_ids = _ids(
        payload.get("additional_scoped_schema_ids"), "additional scoped schema IDs"
    )
    if set(additional_scoped_ids) != _ADDITIONAL_SCOPED_IDS:
        raise TMPage46MappingError("TM page-46 additional scoped schema IDs drifted")
    return TMPage46MappingPolicy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=46,
        page_tag="page-0046",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=str(payload.get("mapping_authority_scope", "")),
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        schema_total=_positive_int(payload, "schema_total"),
        scoped_schema_id_start=start,
        scoped_schema_id_end=end,
        additional_scoped_schema_ids=additional_scoped_ids,
        minimum_visible_label_similarity=float(threshold),
        rows=tuple(rows),
        ambiguous_schema_ids=ambiguous,
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


def _dash_evidence_hash(parsed: ParsedTMPage46) -> str:
    records = []
    for row in parsed.rows:
        for evidence in row.visual_cell_evidence:
            if evidence is None:
                continue
            record = asdict(evidence)
            record.pop("source_image_path")
            records.append(record)
    return hashlib.sha256(
        json.dumps(records, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _value(parsed: ParsedTMPage46, table_key: str, ordinal: int, axis: int) -> Decimal:
    row = next(row for row in parsed.rows if row.table_key == table_key and row.ordinal == ordinal)
    value = row.row.cells[axis].value
    if value is None:
        raise TMPage46MappingError("TM page-46 accounting validation received a non-value cell")
    return value


def _validation(parsed: ParsedTMPage46) -> tuple[TMPage46AccountingCheck, ...]:
    equations = (
        ("NET_INTEREST_INCOME_TOTAL", "NET_INTEREST", (4, 5, 6, 7, 8, 9), 10),
        ("NET_INTEREST_EXPENSE_TOTAL", "NET_INTEREST", (12, 13, 14, 15), 16),
        ("NET_INTEREST_NET", "NET_INTEREST", (10, 16), 17),
        ("NET_SERVICE_INCOME_TOTAL", "NET_SERVICE", (3, 4, 5, 6, 7, 8, 9), 10),
        ("NET_SERVICE_NET", "NET_SERVICE", (10, 20), 21),
    )
    checks = []
    for check_id, table_key, components, total in equations:
        table = next(table for table in parsed.tables if table.table_key == table_key)
        for axis_index, axis in enumerate(table.axes):
            expected = sum(
                (_value(parsed, table_key, ordinal, axis_index) for ordinal in components),
                Decimal(0),
            )
            observed = _value(parsed, table_key, total, axis_index)
            residual = observed - expected
            checks.append(
                TMPage46AccountingCheck(
                    check_id=check_id,
                    axis_role=axis.current_or_comparative,
                    status="PASS" if residual == 0 else "FAIL",
                    expected_value=expected,
                    observed_value=observed,
                    residual=residual,
                    reason="visible VALUE cells combined without blank/dash coercion",
                )
            )
    service = next(table for table in parsed.tables if table.table_key == "NET_SERVICE")
    consulting = service.rows[13]
    for axis_index, axis in enumerate(service.axes):
        if consulting.row.cells[axis_index].observation is not ObservationKind.DASH:
            raise TMPage46MappingError("TM page-46 consulting status drifted from visible DASH")
        checks.append(
            TMPage46AccountingCheck(
                check_id="NET_SERVICE_EXPENSE_TOTAL",
                axis_role=axis.current_or_comparative,
                status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
                expected_value=None,
                observed_value=_value(parsed, "NET_SERVICE", 20, axis_index),
                residual=None,
                reason="visible DASH is an observation status and cannot be coerced to zero",
            )
        )
    return tuple(checks)


def reconcile_tm_page46_items(
    parsed: ParsedTMPage46,
    *,
    schema: list[SchemaItem],
    policy: TMPage46MappingPolicy,
    source_pdf_path: Path,
) -> TMPage46MappingResult:
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
    ):
        raise TMPage46MappingError("TM page-46 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage46MappingError("TM page-46 source PDF hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE46_SCHEMA_TOTAL:
        raise TMPage46MappingError("TM page-46 schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if not _SCOPED_IDS <= set(schema_by_id):
        raise TMPage46MappingError("TM page-46 scoped ReportNormIds are absent")
    parsed_by_identity = {(row.table_key, row.ordinal): row for row in parsed.rows}
    if tuple(parsed_by_identity) != tuple(rule.identity for rule in policy.rows):
        raise TMPage46MappingError("TM page-46 parsed row order drifted from policy")
    source_dispositions = []
    source_rows_by_schema: dict[int, list[str]] = {}
    for rule in policy.rows:
        row = parsed_by_identity[rule.identity]
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if (
            row.row_kind.value != rule.expected_row_kind
            or observations != rule.expected_observations
        ):
            raise TMPage46MappingError(f"TM page-46 row status drifted: {row.row_id}")
        if rule.visible_label_anchor is None:
            if row.row.label:
                raise TMPage46MappingError(f"TM page-46 expected unlabeled total: {row.row_id}")
            similarity = None
        else:
            similarity = _similarity(row.row.label, rule.visible_label_anchor)
            if similarity < policy.minimum_visible_label_similarity:
                raise TMPage46MappingError(f"TM page-46 label anchor failed: {row.row_id}")
        if rule.disposition is TMPage46RuleDisposition.FIXED:
            assert rule.report_norm_id is not None
            item = schema_by_id[rule.report_norm_id]
            status = TMPage46SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            canonical = item.canonical_name
            source_rows_by_schema.setdefault(item.schema_id, []).append(row.row_id)
            question_required = False
            reason = "fixed page-46 note/section hierarchy and visible-label rule passed"
        elif rule.disposition is TMPage46RuleDisposition.SOURCE_ONLY_VALIDATION:
            status = TMPage46SourceStatus.SOURCE_ONLY_VALIDATION.value
            canonical = None
            question_required = False
            reason = "visible structural duplicate retained as source provenance without export"
        elif rule.disposition is TMPage46RuleDisposition.SOURCE_ONLY_QUESTION:
            status = TMPage46SourceStatus.SOURCE_ONLY_QUESTION.value
            canonical = None
            question_required = True
            reason = "visible source row has no sufficiently specific supplied schema identity"
        else:
            status = TMPage46SourceStatus.AMBIGUOUS_MAPPING.value
            canonical = None
            question_required = True
            reason = "visible source row cannot be split or aggregated across candidate identities safely"
        source_dispositions.append(
            TMPage46SourceDisposition(
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
                visual_cell_evidence=row.visual_cell_evidence,
                question_required=question_required,
                reason=reason,
            )
        )

    brokerage_components = (
        parsed_by_identity[("NET_SERVICE", 15)],
        parsed_by_identity[("NET_SERVICE", 18)],
    )
    if tuple(
        next(
            rule for rule in policy.rows if rule.identity == ("NET_SERVICE", ordinal)
        ).report_norm_id
        for ordinal in (15, 18)
    ) != (6024, 6025):
        raise TMPage46MappingError("TM page-46 brokerage component bindings drifted")
    derived_assignments = []
    for axis_index, axis in enumerate(parsed.axes):
        component_values = tuple(
            _value(parsed, "NET_SERVICE", ordinal, axis_index) for ordinal in (15, 18)
        )
        derived_assignments.append(
            TMPage46DerivedAssignment(
                report_norm_id=1170,
                canonical_name=schema_by_id[1170].canonical_name,
                component_report_norm_ids=(6024, 6025),
                component_row_ids=tuple(row.row_id for row in brokerage_components),
                component_values=component_values,
                observation=ObservationKind.VALUE.value,
                value=sum(component_values, Decimal(0)),
                period_start=axis.period_start.isoformat(),
                period_end=axis.period_end.isoformat(),
                period_role=axis.current_or_comparative,
                period_type=axis.period_type,
                unit=axis.canonical_unit,
                unit_multiplier=axis.unit_multiplier,
                mapping_basis="DERIVED_SUM_OF_EXPLICIT_PRINTED_CHILDREN_6024_6025",
            )
        )
    source_rows_by_schema[1170] = [row.row_id for row in brokerage_components]
    accounting = _validation(parsed)
    if (
        len(accounting) != TM_PAGE46_ACCOUNTING_CHECK_COUNT
        or sum(check.status == "PASS" for check in accounting) != TM_PAGE46_ACCOUNTING_PASS_COUNT
        or sum(check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in accounting)
        != TM_PAGE46_ACCOUNTING_NOT_TESTABLE_COUNT
        or any(check.status == "FAIL" for check in accounting)
    ):
        raise TMPage46MappingError("TM page-46 accounting validation failed")
    ambiguous = set(policy.ambiguous_schema_ids)
    not_observed = set(policy.not_observed_schema_ids)
    schema_dispositions = []
    for item in tm_schema:
        if item.schema_id == 1170:
            status = TMPage46SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_ids = tuple(source_rows_by_schema[item.schema_id])
            reason = (
                "derived aggregate with explicit provenance from separately preserved "
                "printed children 6024 and 6025"
            )
        elif item.schema_id in source_rows_by_schema:
            status = TMPage46SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_ids = tuple(source_rows_by_schema[item.schema_id])
            reason = "one fixed page-46 source row passed source-scoped mapping"
        elif item.schema_id in ambiguous:
            status = TMPage46SchemaStatus.AMBIGUOUS_MAPPING.value
            source_ids = tuple(
                source.row_id
                for source in source_dispositions
                if item.schema_id in source.candidate_report_norm_ids
            )
            reason = "one or more visible rows are compatible but mapping/splitting is unresolved"
        elif item.schema_id in not_observed:
            status = TMPage46SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            source_ids = ()
            reason = "item belongs to the fully assessed page-46 scope but was not visible"
        else:
            status = TMPage46SchemaStatus.UNASSESSED.value
            source_ids = ()
            reason = "outside the exact page-46 schema scope"
        schema_dispositions.append(
            TMPage46SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status,
                source_row_ids=source_ids,
                reason=reason,
            )
        )
    result = TMPage46MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=46,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="SCOPED_PAGE46_UNIVERSAL_DURATION_MAPPING_WITH_EXPLICIT_DERIVATION",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=len(_SCOPED_IDS),
        mapped_schema_count=len(source_rows_by_schema),
        ambiguous_schema_count=len(ambiguous),
        not_observed_schema_count=len(not_observed),
        not_applicable_schema_count=0,
        unassessed_schema_count=len(tm_schema) - len(_SCOPED_IDS),
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMPage46SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        ambiguous_source_row_count=sum(
            item.status == TMPage46SourceStatus.AMBIGUOUS_MAPPING.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status
            in {
                TMPage46SourceStatus.SOURCE_ONLY_VALIDATION.value,
                TMPage46SourceStatus.SOURCE_ONLY_QUESTION.value,
            }
            for item in source_dispositions
        ),
        source_question_row_count=sum(item.question_required for item in source_dispositions),
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_value_count=sum(
            observation in {ObservationKind.VALUE.value, ObservationKind.ZERO.value}
            for item in source_dispositions
            if item.status == TMPage46SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for observation in item.observations
        ),
        derived_assignment_count=len(derived_assignments),
        accounting_check_count=len(accounting),
        accounting_pass_count=sum(check.status == "PASS" for check in accounting),
        accounting_not_testable_count=sum(
            check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in accounting
        ),
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        derived_assignments=tuple(derived_assignments),
        accounting_checks=accounting,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        dash_pixel_evidence_sha256=_dash_evidence_hash(parsed),
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS",
            "VISIBLE_PAGE46_NOTE_SECTION_AND_LOCAL_ROW_ORDER",
            "SOURCE_RENDER_SHA256",
            "CONSTRAINED_PIXEL_DASH_EVIDENCE_FOR_STATUS_ONLY",
            "TM_SCHEMA_ID_NAME_ORDER",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
            "EXPLICIT_1170_SUM_OF_PRINTED_6024_6025_CHILDREN_WITH_PROVENANCE",
        ),
    )
    return validate_tm_page46_mapping_result(result)


def validate_tm_page46_mapping_result(
    result: TMPage46MappingResult,
) -> TMPage46MappingResult:
    if (
        result.schema_item_count != TM_PAGE46_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE46_RECONCILED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE46_MAPPED_SCHEMA_COUNT
        or result.ambiguous_schema_count != TM_PAGE46_AMBIGUOUS_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE46_NOT_OBSERVED_COUNT
        or result.not_applicable_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE46_UNASSESSED_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE46_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE46_MAPPED_SOURCE_COUNT
        or result.ambiguous_source_row_count != TM_PAGE46_AMBIGUOUS_SOURCE_COUNT
        or result.source_only_row_count != TM_PAGE46_SOURCE_ONLY_COUNT
        or result.source_question_row_count != TM_PAGE46_QUESTION_SOURCE_COUNT
        or result.financial_slot_count != TM_PAGE46_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE46_VALUE_COUNT
        or result.dash_count != TM_PAGE46_DASH_COUNT
        or result.mapped_value_count != TM_PAGE46_MAPPED_VALUE_COUNT
        or result.derived_assignment_count != TM_PAGE46_DERIVED_ASSIGNMENT_COUNT
        or result.accounting_check_count != TM_PAGE46_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_PAGE46_ACCOUNTING_PASS_COUNT
        or result.accounting_not_testable_count != TM_PAGE46_ACCOUNTING_NOT_TESTABLE_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage46MappingError("TM page-46 mapping result denominator drifted")
    if (
        result.mapped_schema_count
        + result.ambiguous_schema_count
        + result.not_observed_schema_count
        + result.unassessed_schema_count
        != result.schema_item_count
    ):
        raise TMPage46MappingError("TM page-46 schema statuses do not reconcile")
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMPage46SchemaStatus)
    }
    if (
        by_status[TMPage46SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] != _MAPPED_IDS
        or by_status[TMPage46SchemaStatus.AMBIGUOUS_MAPPING.value] != _AMBIGUOUS_IDS
        or by_status[TMPage46SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] != _NOT_OBSERVED_IDS
    ):
        raise TMPage46MappingError("TM page-46 exact schema partition drifted")
    dash_rows = [
        item for item in result.source_dispositions if item.observations == ("DASH", "DASH")
    ]
    if (
        len(dash_rows) != 1
        or dash_rows[0].status != TMPage46SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        or dash_rows[0].report_norm_id != 5987
        or any(evidence is None for evidence in dash_rows[0].visual_cell_evidence)
        or any(value is not None for value in dash_rows[0].values)
    ):
        raise TMPage46MappingError("TM page-46 mapped DASH status lost pixel evidence")
    if [
        (
            item.report_norm_id,
            item.component_report_norm_ids,
            item.component_values,
            item.value,
            item.period_role,
            item.mapping_basis,
        )
        for item in result.derived_assignments
    ] != [
        (
            1170,
            (6024, 6025),
            (Decimal("-539743"), Decimal("-59748")),
            Decimal("-599491"),
            "CURRENT",
            "DERIVED_SUM_OF_EXPLICIT_PRINTED_CHILDREN_6024_6025",
        ),
        (
            1170,
            (6024, 6025),
            (Decimal("-232408"), Decimal("-32105")),
            Decimal("-264513"),
            "COMPARATIVE",
            "DERIVED_SUM_OF_EXPLICIT_PRINTED_CHILDREN_6024_6025",
        ),
    ] or any(not item.component_row_ids for item in result.derived_assignments):
        raise TMPage46MappingError("TM page-46 explicit ID1170 derivation drifted")
    return result


__all__ = [
    "TM_PAGE46_POLICY_RELATIVE_PATH",
    "TMPage46AccountingCheck",
    "TMPage46DerivedAssignment",
    "TMPage46MappingError",
    "TMPage46MappingPolicy",
    "TMPage46MappingResult",
    "TMPage46SchemaDisposition",
    "TMPage46SchemaStatus",
    "TMPage46SourceDisposition",
    "TMPage46SourceStatus",
    "load_tm_page46_mapping_policy",
    "reconcile_tm_page46_items",
    "validate_tm_page46_mapping_result",
]
