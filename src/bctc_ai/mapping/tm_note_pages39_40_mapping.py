"""Scoped ReportNormId reconciliation for MBB Note 11 on PDF pages 39-40."""

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

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.schema.registry import SchemaItem
from bctc_ai.tables.tm_note_pages39_40 import (
    ParsedTMNotePages3940,
    TMIntangibleLogicalRow,
)
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind

TM_NOTE_PAGES3940_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-pages39-40-v1.yaml")
TM_NOTE_PAGES3940_SCHEMA_TOTAL = 1_710
TM_NOTE_PAGES3940_RECONCILED_COUNT = 39
TM_NOTE_PAGES3940_MAPPED_SCHEMA_COUNT = 18
TM_NOTE_PAGES3940_UNRESOLVED_SCHEMA_COUNT = 0
TM_NOTE_PAGES3940_NOT_OBSERVED_COUNT = 21
TM_NOTE_PAGES3940_UNASSESSED_COUNT = 1_671
TM_NOTE_PAGES3940_SOURCE_ROW_COUNT = 30
TM_NOTE_PAGES3940_MAPPED_SOURCE_COUNT = 30
TM_NOTE_PAGES3940_UNRESOLVED_SOURCE_COUNT = 0
TM_NOTE_PAGES3940_SOURCE_ONLY_COUNT = 0
TM_NOTE_PAGES3940_PARTIAL_SOURCE_COUNT = 24
TM_NOTE_PAGES3940_SLOT_COUNT = 96
TM_NOTE_PAGES3940_VALUE_COUNT = 79
TM_NOTE_PAGES3940_DASH_COUNT = 17
TM_NOTE_PAGES3940_MAPPED_SLOT_COUNT = 24
TM_NOTE_PAGES3940_UNRESOLVED_SLOT_COUNT = 0
TM_NOTE_PAGES3940_SOURCE_ONLY_SLOT_COUNT = 72
TM_NOTE_PAGES3940_ACCOUNTING_CHECK_COUNT = 56
TM_NOTE_PAGES3940_ACCOUNTING_PASS_COUNT = 39
TM_NOTE_PAGES3940_ACCOUNTING_NOT_TESTABLE_COUNT = 17
TM_NOTE_PAGES3940_DUPLICATE_CHECK_COUNT = 12

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCOPED_IDS = set(range(913, 942)) | set(range(5967, 5972)) | set(range(5997, 6002))
_MAPPED_IDS = {
    913,
    914,
    915,
    925,
    928,
    929,
    930,
    941,
    *range(5967, 5972),
    *range(5997, 6002),
}
_FORMER_COMPONENT_IDS = {
    916,
    917,
    918,
    919,
    920,
    927,
    931,
    932,
    933,
    934,
    935,
    936,
    937,
    938,
    939,
    940,
}
_UNRESOLVED_IDS: set[int] = set()
_NOT_OBSERVED_IDS = _FORMER_COMPONENT_IDS | {921, 922, 923, 924, 926}
_FIXED_SCHEMA_NAMES = {
    913: "tang giam tai san co dinh vo hinh",
    914: "nguyen gia",
    915: "so du dau ky",
    925: "thanh ly nhuong ban",
    928: "so du cuoi ky",
    929: "gia tri hao mon luy ke",
    930: "so du dau ky",
    941: "so du cuoi ky",
    5967: "chenh lech ty gia",
    5968: "chenh lech ty gia",
    5969: "gia tri con lai",
    5970: "so du dau ky",
    5971: "so du cuoi ky",
}
_EXPECTED_ASSIGNMENT_KEYS = {
    ("page-0039", 915),
    ("page-0039", 928),
    ("page-0039", 930),
    ("page-0039", 941),
    ("page-0040", 915),
    ("page-0040", 925),
    ("page-0040", 928),
    ("page-0040", 930),
    ("page-0040", 941),
    ("page-0039", 5967),
    ("page-0039", 5968),
    ("page-0039", 5970),
    ("page-0039", 5971),
    ("page-0040", 5967),
    ("page-0040", 5968),
    ("page-0040", 5970),
    ("page-0040", 5971),
    ("page-0039", 5997),
    ("page-0039", 5999),
    ("page-0040", 5997),
    ("page-0040", 5998),
    ("page-0040", 5999),
    ("page-0040", 6000),
    ("page-0040", 6001),
}
_QUESTION_KEYS: set[str] = set()
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "class_axis_value_as_report_norm_mapping",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
}


class TMNotePages3940MappingError(ValueError):
    pass


class TMNotePages3940RuleDisposition(StrEnum):
    FIXED_STRUCTURAL = "FIXED_STRUCTURAL"
    FIXED_TOTAL_CELL = "FIXED_TOTAL_CELL"
    UNRESOLVED_MAPPING = "UNRESOLVED_MAPPING"
    SOURCE_ONLY_SCHEMA_GAP = "SOURCE_ONLY_SCHEMA_GAP"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


class TMNotePages3940AssignmentPeriod(StrEnum):
    PANEL_DURATION = "PANEL_DURATION"
    OPENING_SNAPSHOT = "OPENING_SNAPSHOT"
    CLOSING_SNAPSHOT = "CLOSING_SNAPSHOT"


class TMNotePages3940SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    UNRESOLVED = "UNRESOLVED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMNotePages3940SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    UNRESOLVED = "UNRESOLVED"
    SOURCE_ONLY_SCHEMA_GAP = "SOURCE_ONLY_SCHEMA_GAP"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


class TMNotePages3940CellStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    UNRESOLVED = "UNRESOLVED"
    SOURCE_ONLY_CLASS_AXIS = "SOURCE_ONLY_CLASS_AXIS"
    SOURCE_ONLY_SCHEMA_GAP = "SOURCE_ONLY_SCHEMA_GAP"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


@dataclass(frozen=True)
class TMNotePages3940SourceRule:
    page_tag: str
    row_key: str
    disposition: TMNotePages3940RuleDisposition
    report_norm_ids: tuple[int, ...]
    mapped_cell_index: int | None
    candidate_report_norm_ids: tuple[int, ...]
    question_key: str | None
    assignment_period: TMNotePages3940AssignmentPeriod


@dataclass(frozen=True)
class TMNotePages3940QuestionSpec:
    question_key: str
    page_tags: tuple[str, ...]


@dataclass(frozen=True)
class TMNotePages3940MappingPolicy:
    source_path: Path
    document: str
    scope: str
    source_table_policy: str
    mapping_authority_scope: str
    schema_total: int
    scope_schema_ids: tuple[int, ...]
    title_report_norm_id: int
    fixed_mapped_ids: tuple[int, ...]
    unresolved_ids: tuple[int, ...]
    not_observed_ids: tuple[int, ...]
    source_rules: tuple[TMNotePages3940SourceRule, ...]
    question_groups: tuple[TMNotePages3940QuestionSpec, ...]
    forbidden_mapping_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMNotePages3940SchemaDisposition:
    report_norm_id: int
    canonical_name: str
    status: str
    reason: str


@dataclass(frozen=True)
class TMNotePages3940SourceDisposition:
    row_id: str
    page_tag: str
    row_key: str
    visible_label: str
    status: str
    mapped_report_norm_ids: tuple[int, ...]
    candidate_report_norm_ids: tuple[int, ...]
    partially_mapped: bool
    question_key: str | None
    reason: str


@dataclass(frozen=True)
class TMNotePages3940CellDisposition:
    row_id: str
    page_tag: str
    row_key: str
    cell_index: int
    axis_role: str
    observation: str
    value: Decimal | None
    status: str
    report_norm_id: int | None
    candidate_report_norm_ids: tuple[int, ...]
    reason: str


@dataclass(frozen=True)
class TMNotePages3940MappedAssignment:
    report_norm_id: int
    canonical_name: str
    row_id: str
    page_tag: str
    row_key: str
    cell_index: int
    axis_role: str
    observation: str
    value: Decimal
    period_role: str
    period_start: str
    period_end: str
    period_type: str
    unit: str
    unit_multiplier: int
    scope: str
    source_row_ids: tuple[str, ...]
    source_bbox: tuple[float, float, float, float]
    mapping_basis: str


@dataclass(frozen=True)
class TMNotePages3940AccountingCheck:
    check_id: str
    page_tag: str
    check_kind: str
    status: str
    expected: Decimal | None
    observed: Decimal | None
    residual: Decimal | None
    source_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMNotePages3940DuplicateCheck:
    check_id: str
    axis_role: str
    earlier_value: Decimal
    later_value: Decimal
    residual: Decimal
    status: str


@dataclass(frozen=True)
class TMNotePages3940Question:
    question_key: str
    page_tags: tuple[str, ...]
    row_ids: tuple[str, ...]
    candidate_report_norm_ids: tuple[int, ...]
    visible_values: tuple[str, ...]
    current_status: str


@dataclass(frozen=True)
class TMNotePages3940MappingResult:
    schema_item_count: int
    status_reconciled_schema_count: int
    mapped_schema_count: int
    unresolved_schema_count: int
    not_observed_schema_count: int
    not_applicable_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    unresolved_source_row_count: int
    source_only_row_count: int
    partially_mapped_source_row_count: int
    question_source_row_count: int
    question_group_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_source_slot_count: int
    unresolved_source_slot_count: int
    source_only_slot_count: int
    mapped_value_assignment_count: int
    mapped_dash_assignment_count: int
    accounting_check_count: int
    accounting_pass_count: int
    accounting_not_testable_count: int
    duplicate_check_count: int
    duplicate_pass_count: int
    mapping_authority_scope: str
    mapping_authority_granted: bool
    schema_dispositions: tuple[TMNotePages3940SchemaDisposition, ...]
    source_dispositions: tuple[TMNotePages3940SourceDisposition, ...]
    cell_dispositions: tuple[TMNotePages3940CellDisposition, ...]
    mapped_assignments: tuple[TMNotePages3940MappedAssignment, ...]
    accounting_checks: tuple[TMNotePages3940AccountingCheck, ...]
    duplicate_checks: tuple[TMNotePages3940DuplicateCheck, ...]
    questions: tuple[TMNotePages3940Question, ...]
    mapping_policy_sha256: str
    source_pdf_sha256: str
    source_ocr_sha256: tuple[str, ...]
    source_render_sha256: tuple[str, ...]
    dash_pixel_evidence_sha256: str


def _ids(value: Any, field: str, *, allow_empty: bool = True) -> tuple[int, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise TMNotePages3940MappingError(f"TM pages39-40 {field} is invalid")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise TMNotePages3940MappingError(f"TM pages39-40 {field} contains a non-ID")
    result = tuple(int(item) for item in value)
    if len(set(result)) != len(result):
        raise TMNotePages3940MappingError(f"TM pages39-40 {field} contains duplicates")
    return result


def load_tm_note_pages39_40_mapping_policy(path: Path) -> TMNotePages3940MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNotePages3940MappingError(
            f"cannot load TM pages39-40 mapping policy: {path}"
        ) from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGES39_40_TOTAL_COLUMN_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNotePages3940MappingError("TM pages39-40 mapping policy identity drifted")
    schema_scope = payload.get("scope_schema_ids")
    if not isinstance(schema_scope, dict) or schema_scope != {
        "start": 913,
        "end": 941,
        "total": 29,
    }:
        raise TMNotePages3940MappingError("TM pages39-40 schema scope drifted")
    additional_scope = _ids(
        payload.get("additional_scope_schema_ids"), "additional scope IDs", allow_empty=False
    )
    fixed = _ids(payload.get("fixed_mapped_ids"), "fixed IDs", allow_empty=False)
    unresolved = _ids(payload.get("unresolved_ids"), "unresolved IDs", allow_empty=True)
    not_observed = _ids(payload.get("not_observed_ids"), "not-observed IDs", allow_empty=False)
    title_id = payload.get("title_report_norm_id")
    if (
        payload.get("schema_total") != TM_NOTE_PAGES3940_SCHEMA_TOTAL
        or set(additional_scope) != set(range(5967, 5972)) | set(range(5997, 6002))
        or title_id != 913
        or set(fixed) != _MAPPED_IDS
        or set(unresolved) != _UNRESOLVED_IDS
        or set(not_observed) != _NOT_OBSERVED_IDS
        or set(fixed) | set(unresolved) | set(not_observed) != _SCOPED_IDS
    ):
        raise TMNotePages3940MappingError("TM pages39-40 schema reconciliation sets drifted")
    raw_rules = payload.get("source_rules")
    if not isinstance(raw_rules, list) or len(raw_rules) != TM_NOTE_PAGES3940_SOURCE_ROW_COUNT:
        raise TMNotePages3940MappingError("TM pages39-40 source-rule denominator drifted")
    rules = []
    for record in raw_rules:
        if not isinstance(record, dict):
            raise TMNotePages3940MappingError("TM pages39-40 source rule is invalid")
        try:
            disposition = TMNotePages3940RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMNotePages3940MappingError("TM pages39-40 rule disposition is invalid") from exc
        page_tag = record.get("page_tag")
        row_key = record.get("row_key")
        mapped_cell_index = record.get("mapped_cell_index")
        question_key = record.get("question_key")
        report_norm_ids = _ids(record.get("report_norm_ids"), "rule fixed IDs")
        candidate_ids = _ids(record.get("candidate_report_norm_ids"), "rule candidate IDs")
        expected_assignment_period = {
            (5970,): TMNotePages3940AssignmentPeriod.OPENING_SNAPSHOT,
            (5971,): TMNotePages3940AssignmentPeriod.CLOSING_SNAPSHOT,
        }.get(report_norm_ids, TMNotePages3940AssignmentPeriod.PANEL_DURATION)
        try:
            assignment_period = TMNotePages3940AssignmentPeriod(
                str(record.get("assignment_period", "PANEL_DURATION"))
            )
        except ValueError as exc:
            raise TMNotePages3940MappingError(
                "TM pages39-40 rule assignment period is invalid"
            ) from exc
        if (
            page_tag not in {"page-0039", "page-0040"}
            or not isinstance(row_key, str)
            or not row_key
            or (mapped_cell_index is not None and mapped_cell_index != 3)
            or (question_key is not None and question_key not in _QUESTION_KEYS)
            or assignment_period is not expected_assignment_period
        ):
            raise TMNotePages3940MappingError("TM pages39-40 rule identity is invalid")
        if disposition is TMNotePages3940RuleDisposition.FIXED_STRUCTURAL:
            valid = len(report_norm_ids) == 1 and mapped_cell_index is None and not candidate_ids
        elif disposition is TMNotePages3940RuleDisposition.FIXED_TOTAL_CELL:
            valid = len(report_norm_ids) == 1 and mapped_cell_index == 3 and not candidate_ids
        elif disposition is TMNotePages3940RuleDisposition.UNRESOLVED_MAPPING:
            valid = (
                not report_norm_ids
                and mapped_cell_index is None
                and bool(candidate_ids)
                and bool(question_key)
            )
        else:
            valid = not report_norm_ids and mapped_cell_index is None and not candidate_ids
        if not valid:
            raise TMNotePages3940MappingError("TM pages39-40 rule authority is invalid")
        rules.append(
            TMNotePages3940SourceRule(
                page_tag=page_tag,
                row_key=row_key,
                disposition=disposition,
                report_norm_ids=report_norm_ids,
                mapped_cell_index=mapped_cell_index,
                candidate_report_norm_ids=candidate_ids,
                question_key=question_key,
                assignment_period=assignment_period,
            )
        )
    identities = {(rule.page_tag, rule.row_key) for rule in rules}
    if len(identities) != len(rules):
        raise TMNotePages3940MappingError("TM pages39-40 source rules are duplicated")
    fixed_from_rules = {item for rule in rules for item in rule.report_norm_ids} | {title_id}
    candidates_from_rules = {item for rule in rules for item in rule.candidate_report_norm_ids}
    if fixed_from_rules != _MAPPED_IDS or candidates_from_rules != _UNRESOLVED_IDS:
        raise TMNotePages3940MappingError("TM pages39-40 rule/schema coverage drifted")
    raw_questions = payload.get("question_groups")
    if not isinstance(raw_questions, list) or len(raw_questions) != len(_QUESTION_KEYS):
        raise TMNotePages3940MappingError("TM pages39-40 question groups drifted")
    questions = []
    for record in raw_questions:
        if not isinstance(record, dict):
            raise TMNotePages3940MappingError("TM pages39-40 question record is invalid")
        key = record.get("question_key")
        page_tags = record.get("page_tags")
        if (
            key not in _QUESTION_KEYS
            or not isinstance(page_tags, list)
            or not page_tags
            or any(tag not in {"page-0039", "page-0040"} for tag in page_tags)
        ):
            raise TMNotePages3940MappingError("TM pages39-40 question identity is invalid")
        questions.append(TMNotePages3940QuestionSpec(key, tuple(str(tag) for tag in page_tags)))
    if {question.question_key for question in questions} != _QUESTION_KEYS:
        raise TMNotePages3940MappingError("TM pages39-40 question keys drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNotePages3940MappingError("TM pages39-40 forbidden inputs drifted")
    table_policy = payload.get("source_table_policy")
    authority = payload.get("mapping_authority_scope")
    if (
        table_policy != "config/tables/tm-note-pages39-40-v1.yaml"
        or authority != "VISIBLE_NOTE_TITLE_SECTION_LABELS_AND_TOTAL_COLUMN_FIXED_ROWS_ONLY"
    ):
        raise TMNotePages3940MappingError("TM pages39-40 mapping authority drifted")
    return TMNotePages3940MappingPolicy(
        source_path=path,
        document=str(payload.get("document", "")),
        scope="CONSOLIDATED",
        source_table_policy=table_policy,
        mapping_authority_scope=authority,
        schema_total=TM_NOTE_PAGES3940_SCHEMA_TOTAL,
        scope_schema_ids=tuple(range(913, 942)),
        title_report_norm_id=title_id,
        fixed_mapped_ids=fixed,
        unresolved_ids=unresolved,
        not_observed_ids=not_observed,
        source_rules=tuple(rules),
        question_groups=tuple(questions),
        forbidden_mapping_inputs=tuple(str(value) for value in forbidden),
    )


def _schema_index(schema: list[SchemaItem]) -> dict[int, SchemaItem]:
    tm_schema = [item for item in schema if item.statement_type == "TM"]
    index = {item.schema_id: item for item in tm_schema}
    if len(tm_schema) != TM_NOTE_PAGES3940_SCHEMA_TOTAL or len(index) != len(tm_schema):
        raise TMNotePages3940MappingError("TM schema denominator or uniqueness drifted")
    if not _SCOPED_IDS <= set(index):
        raise TMNotePages3940MappingError("TM pages39-40 schema branch is incomplete")
    for schema_id, expected in _FIXED_SCHEMA_NAMES.items():
        key = retrieval_key(index[schema_id].canonical_name).replace(".", "")
        if expected not in key:
            raise TMNotePages3940MappingError(
                f"TM pages39-40 fixed schema name drifted: {schema_id} {key}"
            )
    return index


def _row_index(parsed: ParsedTMNotePages3940) -> dict[tuple[str, str], TMIntangibleLogicalRow]:
    result = {(row.page_tag, row.row_key): row for row in parsed.rows}
    if len(result) != len(parsed.rows):
        raise TMNotePages3940MappingError("TM pages39-40 parsed row identities are duplicated")
    return result


def _bbox_tuple(row: TMIntangibleLogicalRow, cell_index: int) -> tuple[float, float, float, float]:
    bbox = row.value_bboxes[cell_index]
    if bbox is None:
        raise TMNotePages3940MappingError("TM pages39-40 mapped cell lacks source bbox")
    return (bbox.x0, bbox.y0, bbox.x1, bbox.y1)


def _assignment_period(
    row: TMIntangibleLogicalRow,
    rule: TMNotePages3940SourceRule,
) -> tuple[str, str, str]:
    if rule.assignment_period is TMNotePages3940AssignmentPeriod.OPENING_SNAPSHOT:
        if row.row_key != "NET_OPEN":
            raise TMNotePages3940MappingError(
                "TM pages39-40 opening snapshot is not bound to the visible opening row"
            )
        snapshot = row.period_start.isoformat()
        return snapshot, snapshot, "SNAPSHOT"
    if rule.assignment_period is TMNotePages3940AssignmentPeriod.CLOSING_SNAPSHOT:
        if row.row_key != "NET_CLOSE":
            raise TMNotePages3940MappingError(
                "TM pages39-40 closing snapshot is not bound to the visible closing row"
            )
        snapshot = row.period_end.isoformat()
        return snapshot, snapshot, "SNAPSHOT"
    return row.period_start.isoformat(), row.period_end.isoformat(), row.period_type


def _cell_text(row: TMIntangibleLogicalRow) -> str:
    values = []
    for cell in row.row.cells:
        values.append("DASH" if cell.observation is ObservationKind.DASH else str(cell.value))
    return f"{row.page_tag}:{row.row_key}:[{','.join(values)}]"


def _equation(
    *,
    check_id: str,
    page_tag: str,
    check_kind: str,
    terms: tuple[tuple[TMIntangibleLogicalRow, int, int], ...],
    target: tuple[TMIntangibleLogicalRow, int],
) -> TMNotePages3940AccountingCheck:
    cells = [(row.row.cells[cell_index], sign) for row, cell_index, sign in terms]
    target_cell = target[0].row.cells[target[1]]
    source_rows = []
    for row in [*(row for row, _cell_index, _sign in terms), target[0]]:
        if row.row_id not in {item.row_id for item in source_rows}:
            source_rows.append(row)
    source_ids = tuple(source_id for row in source_rows for source_id in row.row.source_row_ids)
    if any(cell.observation is ObservationKind.DASH for cell, _sign in cells) or (
        target_cell.observation is ObservationKind.DASH
    ):
        return TMNotePages3940AccountingCheck(
            check_id=check_id,
            page_tag=page_tag,
            check_kind=check_kind,
            status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
            expected=None,
            observed=None,
            residual=None,
            source_row_ids=source_ids,
            reason="at least one visible component is DASH; no zero coercion or imputation",
        )
    if any(cell.value is None for cell, _sign in cells) or target_cell.value is None:
        raise TMNotePages3940MappingError("TM pages39-40 equation received a blank cell")
    expected = sum((cell.value * sign for cell, sign in cells), Decimal(0))
    observed = target_cell.value
    residual = observed - expected
    return TMNotePages3940AccountingCheck(
        check_id=check_id,
        page_tag=page_tag,
        check_kind=check_kind,
        status="PASS" if residual == 0 else "FAIL",
        expected=expected,
        observed=observed,
        residual=residual,
        source_row_ids=source_ids,
        reason="visible finite values only; DASH never contributes numeric zero",
    )


def _validation(
    parsed: ParsedTMNotePages3940,
) -> tuple[
    tuple[TMNotePages3940AccountingCheck, ...],
    tuple[TMNotePages3940DuplicateCheck, ...],
]:
    by_key = _row_index(parsed)
    checks = []
    for page_tag in ("page-0039", "page-0040"):
        numeric_rows = [
            row
            for row in parsed.rows
            if row.page_tag == page_tag and row.row_kind is TMNoteRowKind.NUMERIC
        ]
        for row in numeric_rows:
            checks.append(
                _equation(
                    check_id=f"{page_tag}:row-total:{row.row_key.lower()}",
                    page_tag=page_tag,
                    check_kind="ROW_TOTAL",
                    terms=tuple((row, index, 1) for index in range(3)),
                    target=(row, 3),
                )
            )
        gross_terms = (
            "GROSS_OPEN",
            "GROSS_INCREASE",
            *(("GROSS_LIQUIDATION", "GROSS_OTHER") if page_tag == "page-0040" else ()),
            "GROSS_FX",
        )
        accum_terms = (
            "ACCUM_OPEN",
            "ACCUM_INCREASE",
            *(("ACCUM_DECREASE", "ACCUM_OTHER") if page_tag == "page-0040" else ()),
            "ACCUM_FX",
        )
        for axis_index in range(4):
            checks.append(
                _equation(
                    check_id=f"{page_tag}:gross-rollforward:axis-{axis_index + 1}",
                    page_tag=page_tag,
                    check_kind="GROSS_ROLLFORWARD",
                    terms=tuple((by_key[(page_tag, key)], axis_index, 1) for key in gross_terms),
                    target=(by_key[(page_tag, "GROSS_CLOSE")], axis_index),
                )
            )
            checks.append(
                _equation(
                    check_id=f"{page_tag}:accum-rollforward:axis-{axis_index + 1}",
                    page_tag=page_tag,
                    check_kind="ACCUM_ROLLFORWARD",
                    terms=tuple((by_key[(page_tag, key)], axis_index, 1) for key in accum_terms),
                    target=(by_key[(page_tag, "ACCUM_CLOSE")], axis_index),
                )
            )
            checks.append(
                _equation(
                    check_id=f"{page_tag}:net-open:axis-{axis_index + 1}",
                    page_tag=page_tag,
                    check_kind="NET_OPEN",
                    terms=(
                        (by_key[(page_tag, "GROSS_OPEN")], axis_index, 1),
                        (by_key[(page_tag, "ACCUM_OPEN")], axis_index, -1),
                    ),
                    target=(by_key[(page_tag, "NET_OPEN")], axis_index),
                )
            )
            checks.append(
                _equation(
                    check_id=f"{page_tag}:net-close:axis-{axis_index + 1}",
                    page_tag=page_tag,
                    check_kind="NET_CLOSE",
                    terms=(
                        (by_key[(page_tag, "GROSS_CLOSE")], axis_index, 1),
                        (by_key[(page_tag, "ACCUM_CLOSE")], axis_index, -1),
                    ),
                    target=(by_key[(page_tag, "NET_CLOSE")], axis_index),
                )
            )
    duplicates = []
    for family in ("GROSS", "ACCUM", "NET"):
        earlier = by_key[("page-0040", f"{family}_CLOSE")]
        later = by_key[("page-0039", f"{family}_OPEN")]
        for axis_index, axis_role in enumerate(
            (
                "FINITE_LAND_USE_RIGHTS",
                "COMPUTER_SOFTWARE",
                "OTHER_INTANGIBLE_ASSETS",
                "TOTAL",
            )
        ):
            earlier_cell = earlier.row.cells[axis_index]
            later_cell = later.row.cells[axis_index]
            if earlier_cell.value is None or later_cell.value is None:
                raise TMNotePages3940MappingError("TM pages39-40 cross-panel value is absent")
            residual = later_cell.value - earlier_cell.value
            duplicates.append(
                TMNotePages3940DuplicateCheck(
                    check_id=f"cross-panel:{family.lower()}:axis-{axis_index + 1}",
                    axis_role=axis_role,
                    earlier_value=earlier_cell.value,
                    later_value=later_cell.value,
                    residual=residual,
                    status="PASS" if residual == 0 else "FAIL",
                )
            )
    return tuple(checks), tuple(duplicates)


def _dash_hash(parsed: ParsedTMNotePages3940) -> str:
    records = []
    for row in parsed.rows:
        for cell_index, (cell, evidence) in enumerate(
            zip(row.row.cells, row.visual_cell_evidence, strict=True)
        ):
            if cell.observation is ObservationKind.DASH:
                if cell.value is not None or evidence is None:
                    raise TMNotePages3940MappingError("TM pages39-40 dash provenance is incomplete")
                records.append(
                    {
                        "row_id": row.row_id,
                        "cell_index": cell_index,
                        "evidence": asdict(evidence),
                    }
                )
    payload = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def reconcile_tm_note_pages39_40_items(
    parsed: ParsedTMNotePages3940,
    *,
    schema: list[SchemaItem],
    policy: TMNotePages3940MappingPolicy,
    source_pdf_path: Path,
) -> TMNotePages3940MappingResult:
    if parsed.mapping_authority or parsed.scope != policy.scope:
        raise TMNotePages3940MappingError("TM pages39-40 parser authority or scope drifted")
    if sha256_file(source_pdf_path) != parsed.source_pdf_sha256:
        raise TMNotePages3940MappingError("TM pages39-40 source PDF hash drifted")
    index = _schema_index(schema)
    rows = _row_index(parsed)
    rules = {(rule.page_tag, rule.row_key): rule for rule in policy.source_rules}
    if set(rows) != set(rules):
        raise TMNotePages3940MappingError("TM pages39-40 parser/mapping row scope differs")
    source_dispositions = []
    cell_dispositions = []
    assignments = []
    for identity, row in rows.items():
        rule = rules[identity]
        if rule.disposition in {
            TMNotePages3940RuleDisposition.FIXED_STRUCTURAL,
            TMNotePages3940RuleDisposition.FIXED_TOTAL_CELL,
        }:
            source_status = TMNotePages3940SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            mapped_ids = rule.report_norm_ids
            source_reason = "visible fixed section label or exact total-column row"
        elif rule.disposition is TMNotePages3940RuleDisposition.UNRESOLVED_MAPPING:
            source_status = TMNotePages3940SourceStatus.UNRESOLVED.value
            mapped_ids = ()
            source_reason = "visible aggregate does not identify one component ReportNormId"
        elif rule.disposition is TMNotePages3940RuleDisposition.SOURCE_ONLY_SCHEMA_GAP:
            source_status = TMNotePages3940SourceStatus.SOURCE_ONLY_SCHEMA_GAP.value
            mapped_ids = ()
            source_reason = "visible quantitative concept has no exact schema item in 913-941"
        else:
            source_status = TMNotePages3940SourceStatus.SOURCE_ONLY_VALIDATION.value
            mapped_ids = ()
            source_reason = "visible row retained for accounting validation without export mapping"
        partial = rule.disposition is TMNotePages3940RuleDisposition.FIXED_TOTAL_CELL
        source_dispositions.append(
            TMNotePages3940SourceDisposition(
                row_id=row.row_id,
                page_tag=row.page_tag,
                row_key=row.row_key,
                visible_label=row.row.label,
                status=source_status,
                mapped_report_norm_ids=mapped_ids,
                candidate_report_norm_ids=rule.candidate_report_norm_ids,
                partially_mapped=partial,
                question_key=rule.question_key,
                reason=source_reason,
            )
        )
        if row.row_kind is TMNoteRowKind.LABEL_ONLY:
            continue
        for cell_index, cell in enumerate(row.row.cells):
            axis_role = parsed.pages[0].axes[cell_index].semantic_role
            report_norm_id = None
            candidates: tuple[int, ...] = ()
            if rule.disposition is TMNotePages3940RuleDisposition.FIXED_TOTAL_CELL:
                if cell_index == 3:
                    cell_status = TMNotePages3940CellStatus.MAPPED_AUTOMATIC_SCOPED.value
                    report_norm_id = rule.report_norm_ids[0]
                    reason = "exact visible label and total-column axis"
                else:
                    cell_status = TMNotePages3940CellStatus.SOURCE_ONLY_CLASS_AXIS.value
                    reason = (
                        "asset-class axis retained as provenance; schema row receives total only"
                    )
            elif rule.disposition is TMNotePages3940RuleDisposition.UNRESOLVED_MAPPING:
                cell_status = TMNotePages3940CellStatus.UNRESOLVED.value
                candidates = rule.candidate_report_norm_ids
                reason = "aggregate visible row cannot be split across component schema IDs"
            elif rule.disposition is TMNotePages3940RuleDisposition.SOURCE_ONLY_SCHEMA_GAP:
                cell_status = TMNotePages3940CellStatus.SOURCE_ONLY_SCHEMA_GAP.value
                reason = "no exact schema item"
            else:
                cell_status = TMNotePages3940CellStatus.SOURCE_ONLY_VALIDATION.value
                reason = "accounting validation observation only"
            cell_dispositions.append(
                TMNotePages3940CellDisposition(
                    row_id=row.row_id,
                    page_tag=row.page_tag,
                    row_key=row.row_key,
                    cell_index=cell_index,
                    axis_role=axis_role,
                    observation=cell.observation.value,
                    value=cell.value,
                    status=cell_status,
                    report_norm_id=report_norm_id,
                    candidate_report_norm_ids=candidates,
                    reason=reason,
                )
            )
            if report_norm_id is not None:
                if (
                    cell.observation not in {ObservationKind.VALUE, ObservationKind.ZERO}
                    or cell.value is None
                ):
                    raise TMNotePages3940MappingError("TM pages39-40 mapped total is not finite")
                period_start, period_end, period_type = _assignment_period(row, rule)
                assignments.append(
                    TMNotePages3940MappedAssignment(
                        report_norm_id=report_norm_id,
                        canonical_name=index[report_norm_id].canonical_name,
                        row_id=row.row_id,
                        page_tag=row.page_tag,
                        row_key=row.row_key,
                        cell_index=cell_index,
                        axis_role=axis_role,
                        observation=cell.observation.value,
                        value=cell.value,
                        period_role=row.period_role,
                        period_start=period_start,
                        period_end=period_end,
                        period_type=period_type,
                        unit="VND",
                        unit_multiplier=1_000_000,
                        scope=parsed.scope,
                        source_row_ids=row.row.source_row_ids,
                        source_bbox=_bbox_tuple(row, cell_index),
                        mapping_basis="VISIBLE_FIXED_LABEL_AND_TOTAL_COLUMN_ONLY",
                    )
                )
    accounting, duplicates = _validation(parsed)
    if (
        len(accounting) != TM_NOTE_PAGES3940_ACCOUNTING_CHECK_COUNT
        or sum(check.status == "PASS" for check in accounting)
        != TM_NOTE_PAGES3940_ACCOUNTING_PASS_COUNT
        or sum(check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in accounting)
        != TM_NOTE_PAGES3940_ACCOUNTING_NOT_TESTABLE_COUNT
        or any(check.status == "FAIL" for check in accounting)
        or len(duplicates) != TM_NOTE_PAGES3940_DUPLICATE_CHECK_COUNT
        or any(check.status != "PASS" for check in duplicates)
    ):
        raise TMNotePages3940MappingError("TM pages39-40 accounting validation drifted")
    schema_dispositions = []
    for schema_id in sorted(index):
        if schema_id in _MAPPED_IDS:
            status = TMNotePages3940SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            reason = "visible fixed Note 11 title/section or exact total-column row"
        elif schema_id in _UNRESOLVED_IDS:
            status = TMNotePages3940SchemaStatus.UNRESOLVED.value
            reason = "visible aggregate may contain this schema component but is not split"
        elif schema_id in _NOT_OBSERVED_IDS:
            status = TMNotePages3940SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            reason = "no corresponding visible row in either Note 11 panel"
        else:
            status = TMNotePages3940SchemaStatus.UNASSESSED.value
            reason = "outside the explicitly reconciled 913-941 branch"
        schema_dispositions.append(
            TMNotePages3940SchemaDisposition(
                report_norm_id=schema_id,
                canonical_name=index[schema_id].canonical_name,
                status=status,
                reason=reason,
            )
        )
    questions = []
    for question_spec in policy.question_groups:
        question_rows = [
            row
            for identity, row in rows.items()
            if rules[identity].question_key == question_spec.question_key
        ]
        candidate_ids = sorted(
            {
                item
                for row in question_rows
                for item in rules[(row.page_tag, row.row_key)].candidate_report_norm_ids
            }
        )
        statuses = {
            item.status
            for item in source_dispositions
            if item.question_key == question_spec.question_key
        }
        questions.append(
            TMNotePages3940Question(
                question_key=question_spec.question_key,
                page_tags=question_spec.page_tags,
                row_ids=tuple(row.row_id for row in question_rows),
                candidate_report_norm_ids=tuple(candidate_ids),
                visible_values=tuple(_cell_text(row) for row in question_rows),
                current_status="+".join(sorted(statuses)),
            )
        )
    result = TMNotePages3940MappingResult(
        schema_item_count=len(schema_dispositions),
        status_reconciled_schema_count=TM_NOTE_PAGES3940_RECONCILED_COUNT,
        mapped_schema_count=TM_NOTE_PAGES3940_MAPPED_SCHEMA_COUNT,
        unresolved_schema_count=TM_NOTE_PAGES3940_UNRESOLVED_SCHEMA_COUNT,
        not_observed_schema_count=TM_NOTE_PAGES3940_NOT_OBSERVED_COUNT,
        not_applicable_schema_count=0,
        unassessed_schema_count=TM_NOTE_PAGES3940_UNASSESSED_COUNT,
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMNotePages3940SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        unresolved_source_row_count=sum(
            item.status == TMNotePages3940SourceStatus.UNRESOLVED.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status
            in {
                TMNotePages3940SourceStatus.SOURCE_ONLY_SCHEMA_GAP.value,
                TMNotePages3940SourceStatus.SOURCE_ONLY_VALIDATION.value,
            }
            for item in source_dispositions
        ),
        partially_mapped_source_row_count=sum(
            item.partially_mapped for item in source_dispositions
        ),
        question_source_row_count=sum(
            item.question_key is not None for item in source_dispositions
        ),
        question_group_count=len(questions),
        financial_slot_count=len(cell_dispositions),
        extracted_value_count=sum(
            item.observation == ObservationKind.VALUE.value for item in cell_dispositions
        ),
        dash_count=sum(
            item.observation == ObservationKind.DASH.value for item in cell_dispositions
        ),
        mapped_source_slot_count=sum(
            item.status == TMNotePages3940CellStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in cell_dispositions
        ),
        unresolved_source_slot_count=sum(
            item.status == TMNotePages3940CellStatus.UNRESOLVED.value for item in cell_dispositions
        ),
        source_only_slot_count=sum(
            item.status
            in {
                TMNotePages3940CellStatus.SOURCE_ONLY_CLASS_AXIS.value,
                TMNotePages3940CellStatus.SOURCE_ONLY_SCHEMA_GAP.value,
                TMNotePages3940CellStatus.SOURCE_ONLY_VALIDATION.value,
            }
            for item in cell_dispositions
        ),
        mapped_value_assignment_count=sum(
            item.observation == ObservationKind.VALUE.value for item in assignments
        ),
        mapped_dash_assignment_count=sum(
            item.observation == ObservationKind.DASH.value for item in assignments
        ),
        accounting_check_count=len(accounting),
        accounting_pass_count=sum(check.status == "PASS" for check in accounting),
        accounting_not_testable_count=sum(
            check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in accounting
        ),
        duplicate_check_count=len(duplicates),
        duplicate_pass_count=sum(check.status == "PASS" for check in duplicates),
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        cell_dispositions=tuple(cell_dispositions),
        mapped_assignments=tuple(assignments),
        accounting_checks=accounting,
        duplicate_checks=duplicates,
        questions=tuple(questions),
        mapping_policy_sha256=sha256_file(policy.source_path),
        source_pdf_sha256=parsed.source_pdf_sha256,
        source_ocr_sha256=tuple(page.source_sha256 for page in parsed.pages),
        source_render_sha256=tuple(page.source_render_sha256 for page in parsed.pages),
        dash_pixel_evidence_sha256=_dash_hash(parsed),
    )
    return validate_tm_note_pages39_40_mapping_result(result)


def validate_tm_note_pages39_40_mapping_result(
    result: TMNotePages3940MappingResult,
) -> TMNotePages3940MappingResult:
    if (
        result.schema_item_count != TM_NOTE_PAGES3940_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_NOTE_PAGES3940_RECONCILED_COUNT
        or result.mapped_schema_count != TM_NOTE_PAGES3940_MAPPED_SCHEMA_COUNT
        or result.unresolved_schema_count != TM_NOTE_PAGES3940_UNRESOLVED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_NOTE_PAGES3940_NOT_OBSERVED_COUNT
        or result.not_applicable_schema_count != 0
        or result.unassessed_schema_count != TM_NOTE_PAGES3940_UNASSESSED_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_NOTE_PAGES3940_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_NOTE_PAGES3940_MAPPED_SOURCE_COUNT
        or result.unresolved_source_row_count != TM_NOTE_PAGES3940_UNRESOLVED_SOURCE_COUNT
        or result.source_only_row_count != TM_NOTE_PAGES3940_SOURCE_ONLY_COUNT
        or result.partially_mapped_source_row_count != TM_NOTE_PAGES3940_PARTIAL_SOURCE_COUNT
        or result.question_source_row_count != 0
        or result.question_group_count != 0
        or result.financial_slot_count != TM_NOTE_PAGES3940_SLOT_COUNT
        or result.extracted_value_count != TM_NOTE_PAGES3940_VALUE_COUNT
        or result.dash_count != TM_NOTE_PAGES3940_DASH_COUNT
        or result.mapped_source_slot_count != TM_NOTE_PAGES3940_MAPPED_SLOT_COUNT
        or result.unresolved_source_slot_count != TM_NOTE_PAGES3940_UNRESOLVED_SLOT_COUNT
        or result.source_only_slot_count != TM_NOTE_PAGES3940_SOURCE_ONLY_SLOT_COUNT
        or result.mapped_value_assignment_count != TM_NOTE_PAGES3940_MAPPED_SLOT_COUNT
        or result.mapped_dash_assignment_count != 0
        or result.accounting_check_count != TM_NOTE_PAGES3940_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_NOTE_PAGES3940_ACCOUNTING_PASS_COUNT
        or result.accounting_not_testable_count != TM_NOTE_PAGES3940_ACCOUNTING_NOT_TESTABLE_COUNT
        or result.duplicate_check_count != TM_NOTE_PAGES3940_DUPLICATE_CHECK_COUNT
        or result.duplicate_pass_count != TM_NOTE_PAGES3940_DUPLICATE_CHECK_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMNotePages3940MappingError("TM pages39-40 result denominator drifted")
    if (
        result.mapped_schema_count
        + result.unresolved_schema_count
        + result.not_observed_schema_count
        != result.status_reconciled_schema_count
        or result.status_reconciled_schema_count + result.unassessed_schema_count
        != result.schema_item_count
        or result.mapped_source_row_count
        + result.unresolved_source_row_count
        + result.source_only_row_count
        != result.source_row_count
        or result.mapped_source_slot_count
        + result.unresolved_source_slot_count
        + result.source_only_slot_count
        != result.financial_slot_count
    ):
        raise TMNotePages3940MappingError("TM pages39-40 reconciliation arithmetic drifted")
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMNotePages3940SchemaStatus)
    }
    if (
        by_status[TMNotePages3940SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] != _MAPPED_IDS
        or by_status[TMNotePages3940SchemaStatus.UNRESOLVED.value] != _UNRESOLVED_IDS
        or by_status[TMNotePages3940SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value]
        != _NOT_OBSERVED_IDS
    ):
        raise TMNotePages3940MappingError("TM pages39-40 exact schema sets drifted")
    assignment_keys = {(item.page_tag, item.report_norm_id) for item in result.mapped_assignments}
    if assignment_keys != _EXPECTED_ASSIGNMENT_KEYS or len(assignment_keys) != len(
        result.mapped_assignments
    ):
        raise TMNotePages3940MappingError("TM pages39-40 assignments are duplicated or incomplete")
    if any(
        item.cell_index != 3
        or item.axis_role != "TOTAL"
        or item.mapping_basis != "VISIBLE_FIXED_LABEL_AND_TOTAL_COLUMN_ONLY"
        for item in result.mapped_assignments
    ):
        raise TMNotePages3940MappingError("TM pages39-40 class-axis mapping authority leaked")
    if any(check.status == "FAIL" for check in result.accounting_checks) or any(
        check.status != "PASS" or check.residual != 0 for check in result.duplicate_checks
    ):
        raise TMNotePages3940MappingError("TM pages39-40 validation failed")
    if {question.question_key for question in result.questions} != _QUESTION_KEYS:
        raise TMNotePages3940MappingError("TM pages39-40 question coverage drifted")
    if not all(
        _SHA256.fullmatch(value)
        for value in (
            result.mapping_policy_sha256,
            result.source_pdf_sha256,
            *result.source_ocr_sha256,
            *result.source_render_sha256,
            result.dash_pixel_evidence_sha256,
        )
    ):
        raise TMNotePages3940MappingError("TM pages39-40 evidence hash is invalid")
    return result


__all__ = [
    "TM_NOTE_PAGES3940_POLICY_RELATIVE_PATH",
    "TMNotePages3940CellStatus",
    "TMNotePages3940MappingError",
    "TMNotePages3940MappingPolicy",
    "TMNotePages3940MappingResult",
    "TMNotePages3940SchemaStatus",
    "TMNotePages3940SourceStatus",
    "load_tm_note_pages39_40_mapping_policy",
    "reconcile_tm_note_pages39_40_items",
    "validate_tm_note_pages39_40_mapping_result",
]
