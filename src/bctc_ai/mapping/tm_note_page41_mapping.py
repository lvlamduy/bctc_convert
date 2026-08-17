"""Total-column-only schema mapping and validation for MBB TM page 41."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
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
from bctc_ai.schema.registry import UNIVERSAL_TM_SCHEMA_ITEM_COUNT, SchemaItem
from bctc_ai.tables.tm_note_page41 import ParsedTMPage41
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind

TM_PAGE41_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page41-v1.yaml")
TM_PAGE41_SCHEMA_TOTAL = UNIVERSAL_TM_SCHEMA_ITEM_COUNT
TM_PAGE41_RECONCILED_SCHEMA_COUNT = 32
TM_PAGE41_MAPPED_SCHEMA_COUNT = 15
TM_PAGE41_UNRESOLVED_SCHEMA_COUNT = 0
TM_PAGE41_NOT_OBSERVED_COUNT = 17
TM_PAGE41_UNASSESSED_COUNT = TM_PAGE41_SCHEMA_TOTAL - TM_PAGE41_RECONCILED_SCHEMA_COUNT
TM_PAGE41_SOURCE_ROW_COUNT = 25
TM_PAGE41_MAPPED_SOURCE_COUNT = 25
TM_PAGE41_PARTIAL_SOURCE_COUNT = 19
TM_PAGE41_SOURCE_ONLY_COUNT = 0
TM_PAGE41_SOURCE_QUESTION_COUNT = 0
TM_PAGE41_CONTEXT_SOURCE_COUNT = 0
TM_PAGE41_FINANCIAL_SLOT_COUNT = 57
TM_PAGE41_VALUE_COUNT = 51
TM_PAGE41_DASH_COUNT = 6
TM_PAGE41_MAPPED_VALUE_COUNT = 18
TM_PAGE41_CLASS_AXIS_SLOT_COUNT = 38
TM_PAGE41_CLASS_AXIS_VALUE_COUNT = 33
TM_PAGE41_ACCOUNTING_CHECK_COUNT = 52
TM_PAGE41_ACCOUNTING_PASS_COUNT = 43
TM_PAGE41_ACCOUNTING_NOT_TESTABLE_COUNT = 9

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCOPED_IDS = set(range(942, 966)) | {5972, 5973, 5974} | set(range(6002, 6007))
_MAPPED_IDS = {
    942,
    943,
    944,
    955,
    956,
    957,
    965,
    5972,
    5973,
    5974,
    *range(6002, 6007),
}
_UNRESOLVED_IDS: set[int] = set()
_NOT_OBSERVED_IDS = {*range(945, 955), 958, 959, 960, 961, 962, 963, 964}
_QUESTION_IDS: tuple[str, ...] = ()
_EXPECTED_FIXED_COUNTS = Counter(
    {
        943: 2,
        944: 2,
        955: 2,
        956: 2,
        957: 2,
        965: 2,
        5972: 2,
        5973: 2,
        5974: 2,
        6002: 2,
        6003: 1,
        6004: 1,
        6005: 2,
        6006: 1,
    }
)
_VISIBLE_LABEL_ANCHORS = {
    "GROSS_COST_SECTION": "nguyen gia",
    "GROSS_OPENING": "so du dau ky",
    "GROSS_INCREASE": "tang trong ky",
    "GROSS_OTHER": "tang giam khac trong ky",
    "GROSS_DECREASE": "giam trong ky",
    "GROSS_CLOSING": "so du cuoi ky",
    "ACCUMULATED_DEPRECIATION_SECTION": "gia tri hao mon",
    "DEPRECIATION_OPENING": "so du dau ky",
    "DEPRECIATION_INCREASE": "tang trong ky",
    "DEPRECIATION_OTHER": "tang giam khac trong ky",
    "DEPRECIATION_CLOSING": "so du cuoi ky",
    "NET_BOOK_VALUE_SECTION": "gia tri con lai",
    "NET_OPENING": "so du dau ky",
    "NET_CLOSING": "so du cuoi ky",
}
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "class_axis_value_export_to_total_schema",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
    "cross_panel_value_as_item_selector",
}


class TMPage41MappingError(ValueError):
    pass


class TMPage41RuleDisposition(StrEnum):
    FIXED_STRUCTURAL = "FIXED_STRUCTURAL"
    FIXED_TOTAL_CELL = "FIXED_TOTAL_CELL"
    SOURCE_ONLY_CONTEXT = "SOURCE_ONLY_CONTEXT"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"


class TMPage41AssignmentPeriod(StrEnum):
    PANEL_DURATION = "PANEL_DURATION"
    OPENING_SNAPSHOT = "OPENING_SNAPSHOT"
    CLOSING_SNAPSHOT = "CLOSING_SNAPSHOT"


class TMPage41SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    UNRESOLVED = "UNRESOLVED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage41SourceStatus(StrEnum):
    MAPPED_STRUCTURAL_SCOPED = "MAPPED_STRUCTURAL_SCOPED"
    PARTIAL_TOTAL_COLUMN_MAPPING = "PARTIAL_TOTAL_COLUMN_MAPPING"
    SOURCE_ONLY_CONTEXT = "SOURCE_ONLY_CONTEXT"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"


@dataclass(frozen=True)
class TMPage41RowRule:
    panel_key: str
    section_key: str
    row_key: str
    expected_row_kind: str
    expected_observations: tuple[str, ...]
    disposition: TMPage41RuleDisposition
    report_norm_id: int | None
    total_cell_index: int | None
    candidate_report_norm_ids: tuple[int, ...]
    question_group_ids: tuple[str, ...]
    assignment_period: TMPage41AssignmentPeriod

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.panel_key, self.section_key, self.row_key


@dataclass(frozen=True)
class TMPage41MappingPolicy:
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
    note_title_report_norm_id: int
    rows: tuple[TMPage41RowRule, ...]
    unresolved_schema_ids: tuple[int, ...]
    not_observed_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage41CellAssignment:
    cell_index: int | None
    axis_role: str | None
    report_norm_id: int
    canonical_name: str
    observation: str | None
    value: Decimal | None
    period_start: str | None
    period_end: str | None
    period_type: str | None


@dataclass(frozen=True)
class TMPage41SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_refs: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage41SourceDisposition:
    row_id: str
    panel_key: str
    section_key: str
    row_key: str
    visible_label: str
    row_kind: str
    source_role: str
    status: str
    mapped_assignments: tuple[TMPage41CellAssignment, ...]
    candidate_report_norm_ids: tuple[int, ...]
    candidate_canonical_names: tuple[str, ...]
    visible_label_similarity: float
    observations: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    axis_roles: tuple[str, ...]
    period_start: str
    period_end: str
    period_type: str
    unit: str
    unit_multiplier: int
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    question_group_ids: tuple[str, ...]
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage41AccountingCheck:
    check_id: str
    panel_key: str
    axis_role: str
    status: str
    expected_value: Decimal | None
    observed_value: Decimal | None
    residual: Decimal | None
    reason: str


@dataclass(frozen=True)
class TMPage41MappingResult:
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
    unresolved_schema_count: int
    not_observed_schema_count: int
    not_applicable_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    partial_source_row_count: int
    source_only_row_count: int
    source_question_row_count: int
    context_source_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_value_count: int
    class_axis_slot_count: int
    class_axis_value_count: int
    accounting_check_count: int
    accounting_pass_count: int
    accounting_not_testable_count: int
    accounting_fail_count: int
    question_group_ids: tuple[str, ...]
    note_title_assignment: TMPage41CellAssignment
    schema_dispositions: tuple[TMPage41SchemaDisposition, ...]
    source_dispositions: tuple[TMPage41SourceDisposition, ...]
    accounting_checks: tuple[TMPage41AccountingCheck, ...]
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
        raise TMPage41MappingError(f"invalid positive TM page-41 field: {field}")
    return value


def _ids(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(payload, list)
        or (not payload and not allow_empty)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload)
    ):
        raise TMPage41MappingError(f"TM page-41 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMPage41MappingError(f"TM page-41 {field} contains duplicates")
    return result


def load_tm_page41_mapping_policy(path: Path) -> TMPage41MappingPolicy:
    """Load the total-column-only page-41 mapping authority."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage41MappingError(f"cannot load TM page-41 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE41_TOTAL_COLUMN_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 41
        or payload.get("page_tag") != "page-0041"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage41MappingError("TM page-41 mapping policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage41MappingError("TM page-41 mapping hashes are invalid")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 < float(threshold) <= 1
    ):
        raise TMPage41MappingError("TM page-41 mapping threshold is invalid")
    note_title_id = payload.get("note_title_report_norm_id")
    if note_title_id != 942:
        raise TMPage41MappingError("TM page-41 note-title mapping drifted")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE41_SOURCE_ROW_COUNT:
        raise TMPage41MappingError("TM page-41 mapping row denominator drifted")
    valid_observations = {item.value for item in ObservationKind}
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage41MappingError("TM page-41 mapping row is invalid")
        try:
            disposition = TMPage41RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMPage41MappingError("TM page-41 rule disposition is invalid") from exc
        panel_key = record.get("panel_key")
        section_key = record.get("section_key")
        row_key = record.get("row_key")
        row_kind = record.get("expected_row_kind")
        observations = record.get("expected_observations")
        report_norm_id = record.get("report_norm_id")
        total_cell_index = record.get("total_cell_index")
        candidates = _ids(
            record.get("candidate_report_norm_ids"), "candidate IDs", allow_empty=True
        )
        questions = record.get("question_group_ids")
        expected_assignment_period = {
            5973: TMPage41AssignmentPeriod.OPENING_SNAPSHOT,
            5974: TMPage41AssignmentPeriod.CLOSING_SNAPSHOT,
        }.get(report_norm_id, TMPage41AssignmentPeriod.PANEL_DURATION)
        try:
            assignment_period = TMPage41AssignmentPeriod(
                str(record.get("assignment_period", "PANEL_DURATION"))
            )
        except ValueError as exc:
            raise TMPage41MappingError("TM page-41 assignment period is invalid") from exc
        if (
            panel_key not in {"Q1_2026", "FY_2025"}
            or not isinstance(section_key, str)
            or not section_key
            or not isinstance(row_key, str)
            or row_key not in _VISIBLE_LABEL_ANCHORS
            or row_kind not in {kind.value for kind in TMNoteRowKind}
            or not isinstance(observations, list)
            or len(observations) != 3
            or any(value not in valid_observations for value in observations)
            or not isinstance(questions, list)
            or len(set(questions)) != len(questions)
            or questions
            or assignment_period is not expected_assignment_period
        ):
            raise TMPage41MappingError("TM page-41 mapping row identity is invalid")
        if disposition is TMPage41RuleDisposition.FIXED_STRUCTURAL:
            malformed = (
                isinstance(report_norm_id, bool)
                or not isinstance(report_norm_id, int)
                or total_cell_index is not None
                or candidates
                or questions
                or row_kind != TMNoteRowKind.LABEL_ONLY.value
            )
        elif disposition is TMPage41RuleDisposition.FIXED_TOTAL_CELL:
            malformed = (
                isinstance(report_norm_id, bool)
                or not isinstance(report_norm_id, int)
                or total_cell_index != 2
                or candidates
                or questions
                or row_kind != TMNoteRowKind.NUMERIC.value
            )
        else:
            malformed = (
                report_norm_id is not None
                or total_cell_index is not None
                or (
                    disposition is TMPage41RuleDisposition.SOURCE_ONLY_CONTEXT
                    and (candidates or questions)
                )
                or (disposition is TMPage41RuleDisposition.SOURCE_ONLY_QUESTION and not questions)
            )
        if malformed:
            raise TMPage41MappingError("TM page-41 mapping rule is malformed")
        rows.append(
            TMPage41RowRule(
                panel_key=panel_key,
                section_key=section_key,
                row_key=row_key,
                expected_row_kind=row_kind,
                expected_observations=tuple(observations),
                disposition=disposition,
                report_norm_id=report_norm_id,
                total_cell_index=total_cell_index,
                candidate_report_norm_ids=candidates,
                question_group_ids=tuple(questions),
                assignment_period=assignment_period,
            )
        )
    if len({row.identity for row in rows}) != len(rows):
        raise TMPage41MappingError("TM page-41 mapping identities are duplicated")
    fixed_counts = Counter(rule.report_norm_id for rule in rows if rule.report_norm_id is not None)
    if fixed_counts != _EXPECTED_FIXED_COUNTS:
        raise TMPage41MappingError("TM page-41 fixed row mappings drifted")
    unresolved = _ids(payload.get("unresolved_schema_ids"), "unresolved IDs", allow_empty=True)
    not_observed = _ids(payload.get("not_observed_schema_ids"), "not-observed IDs")
    candidate_ids = {candidate for row in rows for candidate in row.candidate_report_norm_ids}
    if (
        set(unresolved) != _UNRESOLVED_IDS
        or set(not_observed) != _NOT_OBSERVED_IDS
        or candidate_ids != _UNRESOLVED_IDS
        or _MAPPED_IDS | set(unresolved) | set(not_observed) != _SCOPED_IDS
    ):
        raise TMPage41MappingError("TM page-41 scoped schema statuses drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage41MappingError("TM page-41 forbidden mapping inputs drifted")
    document = payload.get("document")
    mapping_scope = payload.get("mapping_authority_scope")
    if not isinstance(document, str) or not isinstance(mapping_scope, str) or not mapping_scope:
        raise TMPage41MappingError("TM page-41 mapping scope is invalid")
    return TMPage41MappingPolicy(
        source_path=path,
        document=document,
        page_number=41,
        page_tag="page-0041",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=mapping_scope,
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        schema_total=_positive_int(payload, "schema_total"),
        minimum_visible_label_similarity=float(threshold),
        note_title_report_norm_id=note_title_id,
        rows=tuple(rows),
        unresolved_schema_ids=unresolved,
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


def _dash_evidence_hash(parsed: ParsedTMPage41) -> str:
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


def _row(parsed: ParsedTMPage41, panel_key: str, row_key: str) -> Any:
    return next(row for row in parsed.rows if row.panel_key == panel_key and row.row_key == row_key)


def _assignment_period(panel: Any, rule: TMPage41RowRule) -> tuple[str, str, str]:
    if rule.assignment_period is TMPage41AssignmentPeriod.OPENING_SNAPSHOT:
        if rule.row_key != "NET_OPENING":
            raise TMPage41MappingError(
                "TM page-41 opening snapshot is not bound to the visible opening row"
            )
        snapshot = panel.period_start.isoformat()
        return snapshot, snapshot, "SNAPSHOT"
    if rule.assignment_period is TMPage41AssignmentPeriod.CLOSING_SNAPSHOT:
        if rule.row_key != "NET_CLOSING":
            raise TMPage41MappingError(
                "TM page-41 closing snapshot is not bound to the visible closing row"
            )
        snapshot = panel.period_end.isoformat()
        return snapshot, snapshot, "SNAPSHOT"
    return panel.period_start.isoformat(), panel.period_end.isoformat(), "DURATION_PANEL"


def _check(
    *,
    check_id: str,
    panel_key: str,
    axis_role: str,
    expected: Decimal | None,
    observed: Decimal | None,
    dash_present: bool,
    reason: str,
) -> TMPage41AccountingCheck:
    if dash_present:
        return TMPage41AccountingCheck(
            check_id=check_id,
            panel_key=panel_key,
            axis_role=axis_role,
            status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
            expected_value=None,
            observed_value=observed,
            residual=None,
            reason="visible DASH is an observation status and cannot be coerced to zero",
        )
    if expected is None or observed is None:
        raise TMPage41MappingError("TM page-41 finite accounting operands drifted")
    residual = observed - expected
    return TMPage41AccountingCheck(
        check_id=check_id,
        panel_key=panel_key,
        axis_role=axis_role,
        status="PASS" if residual == 0 else "FAIL",
        expected_value=expected,
        observed_value=observed,
        residual=residual,
        reason=reason,
    )


def _accounting_checks(parsed: ParsedTMPage41) -> tuple[TMPage41AccountingCheck, ...]:
    checks = []
    numeric_rows = [row for row in parsed.rows if row.row_kind is TMNoteRowKind.NUMERIC]
    for row in numeric_rows:
        first, second, total = row.row.cells
        dash_present = any(
            cell.observation is ObservationKind.DASH for cell in (first, second, total)
        )
        expected = (
            None
            if dash_present or first.value is None or second.value is None
            else first.value + second.value
        )
        checks.append(
            _check(
                check_id=f"ROW_TOTAL_EQUALS_CLASSES_{row.row_key}",
                panel_key=row.panel_key,
                axis_role="TOTAL",
                expected=expected,
                observed=total.value,
                dash_present=dash_present,
                reason="visible class values sum to the visible total column",
            )
        )
    for panel in parsed.panels:
        rollforwards = (
            (
                "GROSS",
                "GROSS_OPENING",
                ("GROSS_INCREASE", "GROSS_OTHER")
                if panel.panel_key == "Q1_2026"
                else ("GROSS_INCREASE", "GROSS_DECREASE"),
                "GROSS_CLOSING",
            ),
            (
                "DEPRECIATION",
                "DEPRECIATION_OPENING",
                ("DEPRECIATION_INCREASE",)
                if panel.panel_key == "Q1_2026"
                else ("DEPRECIATION_INCREASE", "DEPRECIATION_OTHER"),
                "DEPRECIATION_CLOSING",
            ),
        )
        for family, opening_key, movement_keys, closing_key in rollforwards:
            opening = _row(parsed, panel.panel_key, opening_key)
            movements = tuple(_row(parsed, panel.panel_key, key) for key in movement_keys)
            closing = _row(parsed, panel.panel_key, closing_key)
            for axis_index, axis in enumerate(panel.axes):
                operands = [
                    opening.row.cells[axis_index],
                    *(movement.row.cells[axis_index] for movement in movements),
                ]
                dash_present = any(cell.observation is ObservationKind.DASH for cell in operands)
                expected = (
                    None
                    if dash_present or any(cell.value is None for cell in operands)
                    else sum((cell.value for cell in operands), Decimal(0))
                )
                checks.append(
                    _check(
                        check_id=f"{family}_ROLLFORWARD",
                        panel_key=panel.panel_key,
                        axis_role=axis.semantic_role,
                        expected=expected,
                        observed=closing.row.cells[axis_index].value,
                        dash_present=dash_present,
                        reason="visible opening and movement values roll to the visible closing value",
                    )
                )
        for suffix in ("OPENING", "CLOSING"):
            gross = _row(parsed, panel.panel_key, f"GROSS_{suffix}")
            depreciation = _row(parsed, panel.panel_key, f"DEPRECIATION_{suffix}")
            net = _row(parsed, panel.panel_key, f"NET_{suffix}")
            for axis_index, axis in enumerate(panel.axes):
                gross_value = gross.row.cells[axis_index].value
                depreciation_value = depreciation.row.cells[axis_index].value
                expected = (
                    None
                    if gross_value is None or depreciation_value is None
                    else gross_value - depreciation_value
                )
                checks.append(
                    _check(
                        check_id=f"NET_BOOK_VALUE_{suffix}",
                        panel_key=panel.panel_key,
                        axis_role=axis.semantic_role,
                        expected=expected,
                        observed=net.row.cells[axis_index].value,
                        dash_present=False,
                        reason="visible gross cost minus accumulated depreciation equals net book value",
                    )
                )
    current = parsed.panels[0]
    previous = parsed.panels[1]
    for family in ("GROSS", "DEPRECIATION", "NET"):
        current_opening = _row(parsed, current.panel_key, f"{family}_OPENING")
        previous_closing = _row(parsed, previous.panel_key, f"{family}_CLOSING")
        for axis_index, axis in enumerate(current.axes):
            checks.append(
                _check(
                    check_id=f"CROSS_PANEL_{family}_CLOSE_EQUALS_NEXT_OPEN",
                    panel_key="FY_2025_TO_Q1_2026",
                    axis_role=axis.semantic_role,
                    expected=previous_closing.row.cells[axis_index].value,
                    observed=current_opening.row.cells[axis_index].value,
                    dash_present=False,
                    reason="visible FY2025 closing value equals visible Q1/2026 opening value",
                )
            )
    return tuple(checks)


def _source_reason(rule: TMPage41RowRule) -> str:
    if rule.disposition is TMPage41RuleDisposition.FIXED_STRUCTURAL:
        return "visible section heading fixes the scoped parent identity in both panels"
    if rule.disposition is TMPage41RuleDisposition.FIXED_TOTAL_CELL:
        return (
            "only the visible TOTAL cell maps; both asset-class cells remain source-only; "
            "net equations are validation-only"
        )
    if rule.disposition is TMPage41RuleDisposition.SOURCE_ONLY_CONTEXT:
        return "net-book-value heading has no native schema item and remains provenance"
    if "Q042" in rule.question_group_ids:
        return "visible gross movement is an aggregate over multiple schema causes"
    if "Q043" in rule.question_group_ids:
        return "visible depreciation movement is an aggregate over multiple schema causes"
    return "visible net-book-value row has no native schema item and remains validation provenance"


def reconcile_tm_page41_items(
    parsed: ParsedTMPage41,
    *,
    schema: list[SchemaItem],
    policy: TMPage41MappingPolicy,
    source_pdf_path: Path,
) -> TMPage41MappingResult:
    """Reconcile IDs 942-965 while mapping only fixed TOTAL-column cells."""

    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
    ):
        raise TMPage41MappingError("TM page-41 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage41MappingError("TM page-41 source PDF hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE41_SCHEMA_TOTAL:
        raise TMPage41MappingError("TM schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if not _SCOPED_IDS <= set(schema_by_id):
        raise TMPage41MappingError("TM page-41 policy references unknown ReportNormIds")
    parsed_by_identity = {(row.panel_key, row.section_key, row.row_key): row for row in parsed.rows}
    if tuple(parsed_by_identity) != tuple(rule.identity for rule in policy.rows):
        raise TMPage41MappingError("TM page-41 parsed row order drifted from policy")
    if (
        _similarity(parsed.note_title, "bat dong san dau tu")
        < policy.minimum_visible_label_similarity
    ):
        raise TMPage41MappingError("TM page-41 note title no longer supports ID 942")
    source_refs_by_schema: dict[int, list[str]] = {
        942: [
            f"{policy.page_tag}:note-title:lines-"
            + "-".join(f"{index:04d}" for index in parsed.note_title_line_indices)
        ]
    }
    candidate_refs: dict[int, list[str]] = {item: [] for item in policy.unresolved_schema_ids}
    source_dispositions = []
    for rule in policy.rows:
        row = parsed_by_identity[rule.identity]
        panel = next(panel for panel in parsed.panels if panel.panel_key == row.panel_key)
        period_start, period_end, period_type = _assignment_period(panel, rule)
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if (
            row.row_kind.value != rule.expected_row_kind
            or observations != rule.expected_observations
        ):
            raise TMPage41MappingError(f"TM page-41 row status drifted: {row.row_id}")
        similarity = _similarity(row.row.label, _VISIBLE_LABEL_ANCHORS[row.row_key])
        if similarity < policy.minimum_visible_label_similarity:
            raise TMPage41MappingError(f"TM page-41 visible label drifted: {row.row_id}")
        assignments = []
        if rule.disposition is TMPage41RuleDisposition.FIXED_STRUCTURAL:
            assert rule.report_norm_id is not None
            item = schema_by_id[rule.report_norm_id]
            assignments.append(
                TMPage41CellAssignment(
                    cell_index=None,
                    axis_role=None,
                    report_norm_id=item.schema_id,
                    canonical_name=item.canonical_name,
                    observation=None,
                    value=None,
                    period_start=period_start,
                    period_end=period_end,
                    period_type=period_type,
                )
            )
            source_refs_by_schema.setdefault(item.schema_id, []).append(row.row_id)
            status = TMPage41SourceStatus.MAPPED_STRUCTURAL_SCOPED.value
        elif rule.disposition is TMPage41RuleDisposition.FIXED_TOTAL_CELL:
            assert rule.report_norm_id is not None and rule.total_cell_index == 2
            cell = row.row.cells[rule.total_cell_index]
            axis = panel.axes[rule.total_cell_index]
            if axis.semantic_role != "TOTAL" or cell.observation not in {
                ObservationKind.VALUE,
                ObservationKind.ZERO,
                ObservationKind.DASH,
            }:
                raise TMPage41MappingError(
                    "TM page-41 fixed mapping is not a visible VALUE/ZERO/DASH TOTAL cell"
                )
            if cell.observation is ObservationKind.DASH and (
                cell.value is not None or row.visual_cell_evidence[rule.total_cell_index] is None
            ):
                raise TMPage41MappingError("TM page-41 mapped DASH lost pixel provenance")
            item = schema_by_id[rule.report_norm_id]
            assignments.append(
                TMPage41CellAssignment(
                    cell_index=rule.total_cell_index,
                    axis_role=axis.semantic_role,
                    report_norm_id=item.schema_id,
                    canonical_name=item.canonical_name,
                    observation=cell.observation.value,
                    value=cell.value,
                    period_start=period_start,
                    period_end=period_end,
                    period_type=period_type,
                )
            )
            source_refs_by_schema.setdefault(item.schema_id, []).append(
                f"{row.row_id}:cell-{rule.total_cell_index + 1:04d}"
            )
            status = TMPage41SourceStatus.PARTIAL_TOTAL_COLUMN_MAPPING.value
        elif rule.disposition is TMPage41RuleDisposition.SOURCE_ONLY_CONTEXT:
            status = TMPage41SourceStatus.SOURCE_ONLY_CONTEXT.value
        else:
            status = TMPage41SourceStatus.SOURCE_ONLY_QUESTION.value
        for candidate in rule.candidate_report_norm_ids:
            candidate_refs[candidate].append(row.row_id)
        source_dispositions.append(
            TMPage41SourceDisposition(
                row_id=row.row_id,
                panel_key=row.panel_key,
                section_key=row.section_key,
                row_key=row.row_key,
                visible_label=row.row.label,
                row_kind=row.row_kind.value,
                source_role=row.source_role,
                status=status,
                mapped_assignments=tuple(assignments),
                candidate_report_norm_ids=rule.candidate_report_norm_ids,
                candidate_canonical_names=tuple(
                    schema_by_id[item].canonical_name for item in rule.candidate_report_norm_ids
                ),
                visible_label_similarity=similarity,
                observations=observations,
                values=tuple(cell.value for cell in row.row.cells),
                axis_roles=tuple(axis.semantic_role for axis in panel.axes),
                period_start=period_start,
                period_end=period_end,
                period_type=period_type,
                unit=panel.axes[0].canonical_unit,
                unit_multiplier=panel.axes[0].unit_multiplier,
                visual_cell_evidence=row.visual_cell_evidence,
                question_group_ids=rule.question_group_ids,
                question_required=bool(rule.question_group_ids),
                reason=_source_reason(rule),
            )
        )
    if set(source_refs_by_schema) != _MAPPED_IDS:
        raise TMPage41MappingError("TM page-41 exact fixed ID set drifted")
    if any(not refs for refs in candidate_refs.values()):
        raise TMPage41MappingError("TM page-41 unresolved item lost its visible aggregate refs")
    checks = _accounting_checks(parsed)
    if (
        len(checks) != TM_PAGE41_ACCOUNTING_CHECK_COUNT
        or sum(check.status == "PASS" for check in checks) != TM_PAGE41_ACCOUNTING_PASS_COUNT
        or sum(check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in checks)
        != TM_PAGE41_ACCOUNTING_NOT_TESTABLE_COUNT
        or any(check.status == "FAIL" for check in checks)
    ):
        raise TMPage41MappingError("TM page-41 accounting validation drifted")
    unresolved = set(policy.unresolved_schema_ids)
    not_observed = set(policy.not_observed_schema_ids)
    schema_dispositions = []
    for item in tm_schema:
        if item.schema_id in source_refs_by_schema:
            status = TMPage41SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            refs = tuple(source_refs_by_schema[item.schema_id])
            reason = "source-scoped page-41 title, section, or TOTAL cell passed fixed authority"
        elif item.schema_id in unresolved:
            status = TMPage41SchemaStatus.UNRESOLVED.value
            refs = tuple(candidate_refs[item.schema_id])
            reason = "visible aggregate movement does not identify the schema component cause"
        elif item.schema_id in not_observed:
            status = TMPage41SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            refs = ()
            reason = "item belongs to assessed IDs 942-965 but was not explicitly visible"
        else:
            status = TMPage41SchemaStatus.UNASSESSED.value
            refs = ()
            reason = "outside the page-41 branch assessed by this mapping"
        schema_dispositions.append(
            TMPage41SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status,
                source_refs=refs,
                reason=reason,
            )
        )
    mapped_values = sum(
        assignment.value is not None
        for source in source_dispositions
        for assignment in source.mapped_assignments
    )
    mapped_statuses = {
        TMPage41SourceStatus.MAPPED_STRUCTURAL_SCOPED.value,
        TMPage41SourceStatus.PARTIAL_TOTAL_COLUMN_MAPPING.value,
    }
    note_item = schema_by_id[policy.note_title_report_norm_id]
    result = TMPage41MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=41,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="SCOPED_PAGE41_TOTAL_COLUMN_MAPPING_WITH_UNIVERSAL_AGGREGATE_ITEMS",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=(
            len(source_refs_by_schema) + len(unresolved) + len(not_observed)
        ),
        mapped_schema_count=len(source_refs_by_schema),
        unresolved_schema_count=len(unresolved),
        not_observed_schema_count=len(not_observed),
        not_applicable_schema_count=0,
        unassessed_schema_count=(
            len(tm_schema) - len(source_refs_by_schema) - len(unresolved) - len(not_observed)
        ),
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            source.status in mapped_statuses for source in source_dispositions
        ),
        partial_source_row_count=sum(
            source.status == TMPage41SourceStatus.PARTIAL_TOTAL_COLUMN_MAPPING.value
            for source in source_dispositions
        ),
        source_only_row_count=sum(
            source.status not in mapped_statuses for source in source_dispositions
        ),
        source_question_row_count=sum(source.question_required for source in source_dispositions),
        context_source_row_count=sum(
            source.status == TMPage41SourceStatus.SOURCE_ONLY_CONTEXT.value
            for source in source_dispositions
        ),
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_value_count=mapped_values,
        class_axis_slot_count=sum(
            2 for row in parsed.rows if row.row_kind is TMNoteRowKind.NUMERIC
        ),
        class_axis_value_count=sum(
            cell.observation is ObservationKind.VALUE
            for row in parsed.rows
            if row.row_kind is TMNoteRowKind.NUMERIC
            for cell in row.row.cells[:2]
        ),
        accounting_check_count=len(checks),
        accounting_pass_count=sum(check.status == "PASS" for check in checks),
        accounting_not_testable_count=sum(
            check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in checks
        ),
        accounting_fail_count=sum(check.status == "FAIL" for check in checks),
        question_group_ids=_QUESTION_IDS,
        note_title_assignment=TMPage41CellAssignment(
            cell_index=None,
            axis_role=None,
            report_norm_id=note_item.schema_id,
            canonical_name=note_item.canonical_name,
            observation=None,
            value=None,
            period_start=None,
            period_end=None,
            period_type=None,
        ),
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        accounting_checks=checks,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        dash_pixel_evidence_sha256=_dash_evidence_hash(parsed),
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS",
            "VISIBLE_PAGE41_PANEL_SECTION_ROW_AND_CLASS_AXES",
            "VISIBLE_TOTAL_COLUMN_ROLE",
            "SOURCE_RENDER_SHA256",
            "CONSTRAINED_PIXEL_DASH_EVIDENCE_FOR_STATUS_ONLY",
            "TM_SCHEMA_ID_NAME_ORDER",
            "ACCOUNTING_AND_CROSS_PANEL_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
        ),
    )
    return validate_tm_page41_mapping_result(result)


def validate_tm_page41_mapping_result(
    result: TMPage41MappingResult,
) -> TMPage41MappingResult:
    """Fail closed if page-41 coverage, source, or DASH denominators drift."""

    if (
        result.schema_item_count != TM_PAGE41_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE41_RECONCILED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE41_MAPPED_SCHEMA_COUNT
        or result.unresolved_schema_count != TM_PAGE41_UNRESOLVED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE41_NOT_OBSERVED_COUNT
        or result.not_applicable_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE41_UNASSESSED_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE41_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE41_MAPPED_SOURCE_COUNT
        or result.partial_source_row_count != TM_PAGE41_PARTIAL_SOURCE_COUNT
        or result.source_only_row_count != TM_PAGE41_SOURCE_ONLY_COUNT
        or result.source_question_row_count != TM_PAGE41_SOURCE_QUESTION_COUNT
        or result.context_source_row_count != TM_PAGE41_CONTEXT_SOURCE_COUNT
        or result.financial_slot_count != TM_PAGE41_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE41_VALUE_COUNT
        or result.dash_count != TM_PAGE41_DASH_COUNT
        or result.mapped_value_count != TM_PAGE41_MAPPED_VALUE_COUNT
        or result.class_axis_slot_count != TM_PAGE41_CLASS_AXIS_SLOT_COUNT
        or result.class_axis_value_count != TM_PAGE41_CLASS_AXIS_VALUE_COUNT
        or result.accounting_check_count != TM_PAGE41_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_PAGE41_ACCOUNTING_PASS_COUNT
        or result.accounting_not_testable_count != TM_PAGE41_ACCOUNTING_NOT_TESTABLE_COUNT
        or result.accounting_fail_count != 0
        or result.question_group_ids != _QUESTION_IDS
        or not result.mapping_authority_granted
    ):
        raise TMPage41MappingError("TM page-41 mapping result denominator drifted")
    if (
        result.mapped_schema_count
        + result.unresolved_schema_count
        + result.not_observed_schema_count
        + result.unassessed_schema_count
        != result.schema_item_count
    ):
        raise TMPage41MappingError("TM page-41 schema statuses do not reconcile")
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage41SchemaStatus}
    }
    if (
        by_status[TMPage41SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] != _MAPPED_IDS
        or by_status[TMPage41SchemaStatus.UNRESOLVED.value] != _UNRESOLVED_IDS
        or by_status[TMPage41SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] != _NOT_OBSERVED_IDS
    ):
        raise TMPage41MappingError("TM page-41 exact schema status sets drifted")
    dash_cells = [
        evidence
        for source in result.source_dispositions
        for observation, evidence in zip(
            source.observations, source.visual_cell_evidence, strict=True
        )
        if observation == ObservationKind.DASH.value
    ]
    if len(dash_cells) != TM_PAGE41_DASH_COUNT or any(item is None for item in dash_cells):
        raise TMPage41MappingError("TM page-41 DASH status lost pixel evidence")
    if any(
        assignment.axis_role not in {None, "TOTAL"}
        for source in result.source_dispositions
        for assignment in source.mapped_assignments
    ):
        raise TMPage41MappingError("TM page-41 class-axis value escaped mapping authority")
    return result


__all__ = [
    "TM_PAGE41_POLICY_RELATIVE_PATH",
    "TMPage41AccountingCheck",
    "TMPage41MappingError",
    "TMPage41MappingPolicy",
    "TMPage41MappingResult",
    "TMPage41SchemaDisposition",
    "TMPage41SchemaStatus",
    "TMPage41SourceDisposition",
    "TMPage41SourceStatus",
    "load_tm_page41_mapping_policy",
    "reconcile_tm_page41_items",
    "validate_tm_page41_mapping_result",
]
