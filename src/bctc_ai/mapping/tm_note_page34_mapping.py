"""Source-scoped mapping of page 34 Note 6 overall specific/general axes."""

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

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.evaluation.word_box_rows import VisualCellEvidence
from bctc_ai.schema.registry import UNIVERSAL_TM_SCHEMA_ITEM_COUNT, SchemaItem
from bctc_ai.tables.tm_note_page34 import ParsedTMPage34, TMPage34LogicalRow

TM_PAGE34_MAPPING_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page34-v1.yaml")
TM_PAGE34_SCHEMA_TOTAL = UNIVERSAL_TM_SCHEMA_ITEM_COUNT
TM_PAGE34_RECONCILED_SCHEMA_COUNT = 17
TM_PAGE34_MAPPED_SCHEMA_COUNT = 15
TM_PAGE34_AMBIGUOUS_SCHEMA_COUNT = 0
TM_PAGE34_NOT_OBSERVED_SCHEMA_COUNT = 2
TM_PAGE34_UNASSESSED_SCHEMA_COUNT = TM_PAGE34_SCHEMA_TOTAL - TM_PAGE34_RECONCILED_SCHEMA_COUNT
TM_PAGE34_SOURCE_ROW_COUNT = 11
TM_PAGE34_MAPPED_SOURCE_ROW_COUNT = 11
TM_PAGE34_AMBIGUOUS_SOURCE_ROW_COUNT = 0
TM_PAGE34_PARTIALLY_MAPPED_SOURCE_ROW_COUNT = 11
TM_PAGE34_FINANCIAL_SLOT_COUNT = 99
TM_PAGE34_VALUE_COUNT = 80
TM_PAGE34_DASH_COUNT = 19
TM_PAGE34_MAPPED_STATUS_ASSIGNMENT_COUNT = 22
TM_PAGE34_MAPPED_VALUE_ASSIGNMENT_COUNT = 20
TM_PAGE34_MAPPED_DASH_ASSIGNMENT_COUNT = 2
TM_PAGE34_AMBIGUOUS_SLOT_COUNT = 0
TM_PAGE34_SOURCE_ONLY_SLOT_COUNT = 77
TM_PAGE34_ACCOUNTING_CHECK_COUNT = 84
TM_PAGE34_ACCOUNTING_PASS_COUNT = 46
TM_PAGE34_ACCOUNTING_NOT_TESTABLE_COUNT = 38
TM_PAGE34_DUPLICATE_CHECK_COUNT = 9

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCOPED_IDS = set(range(783, 800))
_MAPPED_IDS = {783, 784, 785, 786, 787, 788, 790, 791, 792, 793, 794, 795, 796, 798, 799}
_AMBIGUOUS_IDS: set[int] = set()
_NOT_OBSERVED_IDS = {789, 797}
_MAPPING_AXES = {"OVERALL_SPECIFIC", "OVERALL_GENERAL"}
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
}
_EXPECTED_FIXED_CELL_IDS = {
    ("Q1_2026", 1): {"OVERALL_SPECIFIC": 793, "OVERALL_GENERAL": 785},
    ("Q1_2026", 2): {"OVERALL_SPECIFIC": 794, "OVERALL_GENERAL": 786},
    ("Q1_2026", 3): {"OVERALL_SPECIFIC": 795, "OVERALL_GENERAL": 787},
    ("Q1_2026", 4): {"OVERALL_SPECIFIC": 796, "OVERALL_GENERAL": 788},
    ("Q1_2026", 5): {"OVERALL_SPECIFIC": 799, "OVERALL_GENERAL": 791},
    ("FY_2025", 1): {"OVERALL_SPECIFIC": 793, "OVERALL_GENERAL": 785},
    ("FY_2025", 2): {"OVERALL_SPECIFIC": 794, "OVERALL_GENERAL": 786},
    ("FY_2025", 3): {"OVERALL_SPECIFIC": 795, "OVERALL_GENERAL": 787},
    ("FY_2025", 4): {"OVERALL_SPECIFIC": 798, "OVERALL_GENERAL": 790},
    ("FY_2025", 5): {"OVERALL_SPECIFIC": 796, "OVERALL_GENERAL": 788},
    ("FY_2025", 6): {"OVERALL_SPECIFIC": 799, "OVERALL_GENERAL": 791},
}
_EXPECTED_AMBIGUOUS_CELLS: dict[tuple[str, int], dict[str, tuple[int, ...]]] = {}


class TMPage34MappingError(ValueError):
    pass


class TMPage34RuleDisposition(StrEnum):
    FIXED_OVERALL_AXES = "FIXED_OVERALL_AXES"
    AMBIGUOUS_OVERALL_AXES = "AMBIGUOUS_OVERALL_AXES"


class TMPage34SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage34SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"


class TMPage34CellStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    SOURCE_ONLY_GEOGRAPHIC_OR_COMBINED_AXIS = "SOURCE_ONLY_GEOGRAPHIC_OR_COMBINED_AXIS"


@dataclass(frozen=True)
class TMPage34StructuralRule:
    evidence_role: str
    axis_role: str | None
    report_norm_id: int
    visible_label_anchor: str


@dataclass(frozen=True)
class TMPage34RowRule:
    panel_key: str
    ordinal: int
    row_role: str
    visible_label_anchor: str
    expected_observations: tuple[str, ...]
    disposition: TMPage34RuleDisposition
    axis_report_norm_ids: tuple[tuple[str, int], ...]
    axis_candidate_report_norm_ids: tuple[tuple[str, tuple[int, ...]], ...]

    @property
    def identity(self) -> tuple[str, int]:
        return self.panel_key, self.ordinal

    @property
    def fixed_by_axis(self) -> dict[str, int]:
        return dict(self.axis_report_norm_ids)

    @property
    def candidates_by_axis(self) -> dict[str, tuple[int, ...]]:
        return dict(self.axis_candidate_report_norm_ids)


@dataclass(frozen=True)
class TMPage34MappingPolicy:
    source_path: Path
    document: str
    page_number: int
    page_tag: str
    note_number: str
    report_scope: str
    mapping_authority_scope: str
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    schema_total: int
    scoped_schema_ids: tuple[int, ...]
    minimum_visible_label_similarity: float
    structural_mappings: tuple[TMPage34StructuralRule, ...]
    rows: tuple[TMPage34RowRule, ...]
    ambiguous_schema_ids: tuple[int, ...]
    not_observed_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage34StructuralMapping:
    report_norm_id: int
    canonical_name: str
    evidence_role: str
    axis_role: str | None
    source_evidence_id: str
    visible_label: str
    source_line_ids: tuple[str, ...]
    bbox: BoundingBox
    visible_label_similarity: float
    mapping_role: str


@dataclass(frozen=True)
class TMPage34SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_evidence_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage34CellDisposition:
    row_id: str
    cell_index: int
    axis_role: str
    status: str
    report_norm_ids: tuple[int, ...]
    candidate_report_norm_ids: tuple[int, ...]
    raw_ocr_texts: tuple[str, ...]
    observation: str
    value: Decimal | None
    period_start: str
    period_end: str
    period_type: str
    period_role: str
    unit: str
    unit_multiplier: int
    source_line_ids: tuple[str, ...]
    value_bbox: BoundingBox | None
    raw_ocr_bboxes: tuple[BoundingBox, ...]
    visual_cell_evidence: VisualCellEvidence | None
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage34SourceDisposition:
    row_id: str
    panel_key: str
    ordinal: int
    row_role: str
    visible_label: str
    status: str
    visible_label_similarity: float
    observations: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    period_start: str
    period_end: str
    period_type: str
    period_role: str
    source_line_ids: tuple[str, ...]
    label_bbox: BoundingBox
    cell_dispositions: tuple[TMPage34CellDisposition, ...]
    candidate_report_norm_ids: tuple[int, ...]
    candidate_canonical_names: tuple[str, ...]
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage34MappedAssignment:
    report_norm_id: int
    canonical_name: str
    row_id: str
    panel_key: str
    cell_index: int
    axis_role: str
    mapping_role: str
    raw_ocr_texts: tuple[str, ...]
    observation: str
    value: Decimal | None
    period_start: str
    period_end: str
    period_type: str
    period_role: str
    unit: str
    unit_multiplier: int
    source_line_ids: tuple[str, ...]
    label_bbox: BoundingBox
    value_bbox: BoundingBox | None
    raw_ocr_bboxes: tuple[BoundingBox, ...]
    visual_cell_evidence: VisualCellEvidence | None


@dataclass(frozen=True)
class TMPage34AccountingCheck:
    check_id: str
    panel_key: str
    row_role: str
    axis_role: str
    status: str
    expected_value: Decimal | None
    observed_value: Decimal | None
    residual: Decimal | None
    reason: str


@dataclass(frozen=True)
class TMPage34DuplicateCheck:
    check_id: str
    axis_role: str
    comparative_close: Decimal
    current_open: Decimal
    residual: Decimal
    status: str


@dataclass(frozen=True)
class TMPage34MappingResult:
    statement_type: str
    document: str
    page_number: int
    page_tag: str
    note_number: str
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
    unresolved_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    ambiguous_source_row_count: int
    source_only_row_count: int
    source_question_row_count: int
    partially_mapped_source_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_status_assignment_count: int
    mapped_value_assignment_count: int
    mapped_dash_assignment_count: int
    ambiguous_source_slot_count: int
    source_only_slot_count: int
    accounting_check_count: int
    accounting_pass_count: int
    accounting_not_testable_count: int
    duplicate_check_count: int
    duplicate_pass_count: int
    structural_mappings: tuple[TMPage34StructuralMapping, ...]
    schema_dispositions: tuple[TMPage34SchemaDisposition, ...]
    source_dispositions: tuple[TMPage34SourceDisposition, ...]
    mapped_assignments: tuple[TMPage34MappedAssignment, ...]
    accounting_checks: tuple[TMPage34AccountingCheck, ...]
    duplicate_checks: tuple[TMPage34DuplicateCheck, ...]
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
        raise TMPage34MappingError(f"invalid positive TM page34 field: {field}")
    return value


def _ids(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(payload, list)
        or (not payload and not allow_empty)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload)
    ):
        raise TMPage34MappingError(f"TM page34 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMPage34MappingError(f"TM page34 {field} contains duplicates")
    return result


def _axis_id_map(payload: Any, field: str) -> tuple[tuple[str, int], ...]:
    if not isinstance(payload, dict):
        raise TMPage34MappingError(f"TM page34 {field} is invalid")
    result = []
    for axis, report_norm_id in payload.items():
        if (
            axis not in _MAPPING_AXES
            or isinstance(report_norm_id, bool)
            or not isinstance(report_norm_id, int)
        ):
            raise TMPage34MappingError(f"TM page34 {field} entry is invalid")
        result.append((axis, report_norm_id))
    return tuple(result)


def _axis_candidate_map(payload: Any) -> tuple[tuple[str, tuple[int, ...]], ...]:
    if not isinstance(payload, dict):
        raise TMPage34MappingError("TM page34 axis candidate map is invalid")
    result = []
    for axis, candidates in payload.items():
        if axis not in _MAPPING_AXES:
            raise TMPage34MappingError("TM page34 candidate axis exceeds mapping authority")
        result.append((axis, _ids(candidates, "axis candidate IDs")))
    return tuple(result)


def load_tm_page34_mapping_policy(path: Path) -> TMPage34MappingPolicy:
    """Load the pinned overall-axis mapping and complete 783–799 reconciliation."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage34MappingError(f"cannot load TM page34 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE34_SCOPED_OVERALL_AXES_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 34
        or payload.get("page_tag") != "page-0034"
        or payload.get("note_number") != "6"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage34MappingError("TM page34 mapping policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage34MappingError("TM page34 mapping source hashes are invalid")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 < threshold <= 1
    ):
        raise TMPage34MappingError("TM page34 mapping label threshold is invalid")
    scoped = _ids(payload.get("scoped_schema_ids"), "scoped schema IDs")
    ambiguous = _ids(
        payload.get("ambiguous_schema_ids"),
        "ambiguous schema IDs",
        allow_empty=True,
    )
    not_observed = _ids(payload.get("not_observed_schema_ids"), "not-observed schema IDs")
    raw_structural = payload.get("structural_mappings")
    if not isinstance(raw_structural, list) or len(raw_structural) != 3:
        raise TMPage34MappingError("TM page34 structural mappings are incomplete")
    structural = []
    for record in raw_structural:
        if not isinstance(record, dict):
            raise TMPage34MappingError("TM page34 structural mapping is invalid")
        evidence_role = record.get("evidence_role")
        axis_role = record.get("axis_role")
        report_norm_id = record.get("report_norm_id")
        anchor = record.get("visible_label_anchor")
        if (
            evidence_role not in {"NOTE_TITLE", "AXIS_HEADER"}
            or (axis_role is not None and axis_role not in _MAPPING_AXES)
            or isinstance(report_norm_id, bool)
            or not isinstance(report_norm_id, int)
            or not isinstance(anchor, str)
            or not retrieval_key(anchor)
        ):
            raise TMPage34MappingError("TM page34 structural mapping fields are invalid")
        structural.append(
            TMPage34StructuralRule(
                evidence_role=evidence_role,
                axis_role=axis_role,
                report_norm_id=report_norm_id,
                visible_label_anchor=retrieval_key(anchor),
            )
        )
    if tuple((item.evidence_role, item.axis_role, item.report_norm_id) for item in structural) != (
        ("NOTE_TITLE", None, 783),
        ("AXIS_HEADER", "OVERALL_GENERAL", 784),
        ("AXIS_HEADER", "OVERALL_SPECIFIC", 792),
    ):
        raise TMPage34MappingError("TM page34 structural mapping locations drifted")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE34_SOURCE_ROW_COUNT:
        raise TMPage34MappingError("TM page34 mapping row denominator drifted")
    valid_observations = {observation.value for observation in ObservationKind}
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage34MappingError("TM page34 mapping row is invalid")
        try:
            disposition = TMPage34RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMPage34MappingError("TM page34 row disposition is invalid") from exc
        observations = record.get("expected_observations")
        fixed = _axis_id_map(record.get("axis_report_norm_ids"), "axis ReportNormIds")
        candidates = _axis_candidate_map(record.get("axis_candidate_report_norm_ids"))
        if (
            not isinstance(record.get("panel_key"), str)
            or isinstance(record.get("ordinal"), bool)
            or not isinstance(record.get("ordinal"), int)
            or record["ordinal"] <= 0
            or not isinstance(record.get("row_role"), str)
            or not isinstance(record.get("visible_label_anchor"), str)
            or not retrieval_key(record["visible_label_anchor"])
            or not isinstance(observations, list)
            or len(observations) != 9
            or any(value not in valid_observations for value in observations)
        ):
            raise TMPage34MappingError("TM page34 row identity/status is invalid")
        if disposition is TMPage34RuleDisposition.FIXED_OVERALL_AXES:
            valid = set(dict(fixed)) == _MAPPING_AXES and not candidates
        else:
            valid = not fixed and set(dict(candidates)) == _MAPPING_AXES
        if not valid:
            raise TMPage34MappingError("TM page34 fixed/ambiguous axis rule is malformed")
        rows.append(
            TMPage34RowRule(
                panel_key=record["panel_key"],
                ordinal=record["ordinal"],
                row_role=record["row_role"],
                visible_label_anchor=retrieval_key(record["visible_label_anchor"]),
                expected_observations=tuple(str(value) for value in observations),
                disposition=disposition,
                axis_report_norm_ids=fixed,
                axis_candidate_report_norm_ids=candidates,
            )
        )
    if len({row.identity for row in rows}) != len(rows):
        raise TMPage34MappingError("TM page34 row identities are duplicated")
    fixed_locations = {
        row.identity: row.fixed_by_axis
        for row in rows
        if row.disposition is TMPage34RuleDisposition.FIXED_OVERALL_AXES
    }
    ambiguous_locations = {
        row.identity: row.candidates_by_axis
        for row in rows
        if row.disposition is TMPage34RuleDisposition.AMBIGUOUS_OVERALL_AXES
    }
    fixed_ids = {item.report_norm_id for item in structural} | {
        report_norm_id for row in rows for _axis, report_norm_id in row.axis_report_norm_ids
    }
    candidate_ids = {
        candidate
        for row in rows
        for _axis, candidates in row.axis_candidate_report_norm_ids
        for candidate in candidates
    }
    if (
        fixed_locations != _EXPECTED_FIXED_CELL_IDS
        or ambiguous_locations != _EXPECTED_AMBIGUOUS_CELLS
        or set(scoped) != _SCOPED_IDS
        or fixed_ids != _MAPPED_IDS
        or set(ambiguous) != _AMBIGUOUS_IDS
        or candidate_ids != _AMBIGUOUS_IDS
        or set(not_observed) != _NOT_OBSERVED_IDS
        or fixed_ids | set(ambiguous) | set(not_observed) != _SCOPED_IDS
    ):
        raise TMPage34MappingError("TM page34 explicit schema or cell locations drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage34MappingError("TM page34 forbidden mapping inputs drifted")
    mapping_scope = payload.get("mapping_authority_scope")
    document = payload.get("document")
    if not isinstance(mapping_scope, str) or not mapping_scope or not isinstance(document, str):
        raise TMPage34MappingError("TM page34 mapping scope/document is invalid")
    return TMPage34MappingPolicy(
        source_path=path,
        document=document,
        page_number=34,
        page_tag="page-0034",
        note_number="6",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=mapping_scope,
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        schema_total=_positive_int(payload, "schema_total"),
        scoped_schema_ids=scoped,
        minimum_visible_label_similarity=float(threshold),
        structural_mappings=tuple(structural),
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


def _dash_evidence_hash(parsed: ParsedTMPage34) -> str:
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


def _row(parsed: ParsedTMPage34, panel_key: str, role: str) -> TMPage34LogicalRow:
    matches = [row for row in parsed.rows if row.panel_key == panel_key and row.row_role == role]
    if len(matches) != 1:
        raise TMPage34MappingError(f"TM page34 validation row not unique: {panel_key}/{role}")
    return matches[0]


def _not_testable(
    check_id: str, panel_key: str, row_role: str, axis_role: str
) -> TMPage34AccountingCheck:
    return TMPage34AccountingCheck(
        check_id=check_id,
        panel_key=panel_key,
        row_role=row_role,
        axis_role=axis_role,
        status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
        expected_value=None,
        observed_value=None,
        residual=None,
        reason="visible DASH is an observation status and cannot be coerced to numeric zero",
    )


def _accounting_validation(parsed: ParsedTMPage34) -> tuple[TMPage34AccountingCheck, ...]:
    checks = []
    equations = (
        ("DOMESTIC_COMBINED_EQUALS_SPECIFIC_PLUS_GENERAL", 0, 1, 2, "DOMESTIC_COMBINED"),
        ("FOREIGN_COMBINED_EQUALS_SPECIFIC_PLUS_GENERAL", 3, 4, 5, "FOREIGN_COMBINED"),
        ("OVERALL_COMBINED_EQUALS_SPECIFIC_PLUS_GENERAL", 6, 7, 8, "OVERALL_COMBINED"),
        ("OVERALL_SPECIFIC_EQUALS_DOMESTIC_PLUS_FOREIGN", 0, 3, 6, "OVERALL_SPECIFIC"),
        ("OVERALL_GENERAL_EQUALS_DOMESTIC_PLUS_FOREIGN", 1, 4, 7, "OVERALL_GENERAL"),
        ("OVERALL_COMBINED_EQUALS_DOMESTIC_PLUS_FOREIGN", 2, 5, 8, "OVERALL_COMBINED"),
    )
    for row in parsed.rows:
        for check_id, left_index, right_index, total_index, axis_role in equations:
            cells = (
                row.row.cells[left_index],
                row.row.cells[right_index],
                row.row.cells[total_index],
            )
            if any(cell.observation is ObservationKind.DASH for cell in cells):
                checks.append(_not_testable(check_id, row.panel_key, row.row_role, axis_role))
                continue
            values = tuple(cell.value for cell in cells)
            if any(value is None for value in values):
                raise TMPage34MappingError("TM page34 row equation lost a value")
            expected = values[0] + values[1]
            observed = values[2]
            residual = observed - expected
            checks.append(
                TMPage34AccountingCheck(
                    check_id=check_id,
                    panel_key=row.panel_key,
                    row_role=row.row_role,
                    axis_role=axis_role,
                    status="PASS" if residual == 0 else "FAIL",
                    expected_value=expected,
                    observed_value=observed,
                    residual=residual,
                    reason="visible geography/measure components compared without DASH coercion",
                )
            )
    for panel in parsed.panels:
        opening = _row(parsed, panel.panel_key, "OPENING")
        closing = _row(parsed, panel.panel_key, "CLOSING")
        movements = [row for row in panel.rows if row.row_role not in {"OPENING", "CLOSING"}]
        for axis_index, axis in enumerate(panel.axes):
            cells = (
                opening.row.cells[axis_index],
                *(row.row.cells[axis_index] for row in movements),
                closing.row.cells[axis_index],
            )
            check_id = "OPENING_PLUS_VISIBLE_MOVEMENTS_EQUALS_CLOSING"
            if any(cell.observation is ObservationKind.DASH for cell in cells):
                checks.append(
                    _not_testable(check_id, panel.panel_key, "ROLLFORWARD", axis.axis_role)
                )
                continue
            values = tuple(cell.value for cell in cells)
            if any(value is None for value in values):
                raise TMPage34MappingError("TM page34 rollforward lost a value")
            expected = values[0] + sum(values[1:-1], Decimal(0))
            observed = values[-1]
            residual = observed - expected
            checks.append(
                TMPage34AccountingCheck(
                    check_id=check_id,
                    panel_key=panel.panel_key,
                    row_role="ROLLFORWARD",
                    axis_role=axis.axis_role,
                    status="PASS" if residual == 0 else "FAIL",
                    expected_value=expected,
                    observed_value=observed,
                    residual=residual,
                    reason="opening plus every visible movement compared with visible closing",
                )
            )
    return tuple(checks)


def _cross_panel_validation(parsed: ParsedTMPage34) -> tuple[TMPage34DuplicateCheck, ...]:
    comparative_close = _row(parsed, "FY_2025", "CLOSING")
    current_open = _row(parsed, "Q1_2026", "OPENING")
    axes = next(panel.axes for panel in parsed.panels if panel.panel_key == "Q1_2026")
    checks = []
    for axis_index, axis in enumerate(axes):
        left = comparative_close.row.cells[axis_index].value
        right = current_open.row.cells[axis_index].value
        if left is None or right is None:
            raise TMPage34MappingError("TM page34 cross-panel check lost a value")
        residual = right - left
        checks.append(
            TMPage34DuplicateCheck(
                check_id="FY2025_CLOSE_EQUALS_Q1_2026_OPEN",
                axis_role=axis.axis_role,
                comparative_close=left,
                current_open=right,
                residual=residual,
                status="PASS" if residual == 0 else "FAIL",
            )
        )
    return tuple(checks)


def reconcile_tm_page34_items(
    parsed: ParsedTMPage34,
    *,
    schema: list[SchemaItem],
    policy: TMPage34MappingPolicy,
    source_pdf_path: Path,
) -> TMPage34MappingResult:
    """Map only overall specific/general cells; retain all other visible dimensions."""

    if (
        parsed.page_number != policy.page_number
        or parsed.page_tag != policy.page_tag
        or parsed.note_number != policy.note_number
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
    ):
        raise TMPage34MappingError("TM page34 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage34MappingError("TM page34 source PDF hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE34_SCHEMA_TOTAL:
        raise TMPage34MappingError("TM schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if not _SCOPED_IDS <= set(schema_by_id):
        raise TMPage34MappingError("TM page34 policy references unknown ReportNormIds")
    parsed_by_identity = {(row.panel_key, row.ordinal): row for row in parsed.rows}
    if tuple(parsed_by_identity) != tuple(rule.identity for rule in policy.rows):
        raise TMPage34MappingError("TM page34 parsed row order drifted from mapping policy")

    structural_mappings = []
    source_evidence_by_schema: dict[int, list[str]] = {}
    for rule in policy.structural_mappings:
        if rule.evidence_role == "NOTE_TITLE":
            visible = parsed.note_title_text
            line_indices = parsed.note_title_line_indices
            bbox = parsed.note_title_bbox
            evidence_id = f"{parsed.page_tag}:note-title"
        else:
            assert rule.axis_role is not None
            matching_axes = [
                axis
                for panel in parsed.panels
                for axis in panel.axes
                if axis.axis_role == rule.axis_role
            ]
            if len(matching_axes) != 2:
                raise TMPage34MappingError("TM page34 repeated structural axis header is absent")
            visible = matching_axes[0].raw_measure_text
            line_indices = tuple(
                line_index for axis in matching_axes for line_index in axis.measure_line_indices
            )
            bbox = BoundingBox(
                min(axis.header_bbox.x0 for axis in matching_axes),
                min(axis.header_bbox.y0 for axis in matching_axes),
                max(axis.header_bbox.x1 for axis in matching_axes),
                max(axis.header_bbox.y1 for axis in matching_axes),
            )
            evidence_id = f"{parsed.page_tag}:axis-header:{rule.axis_role.casefold()}"
        similarity = _similarity(visible, rule.visible_label_anchor)
        if similarity < policy.minimum_visible_label_similarity:
            raise TMPage34MappingError("TM page34 structural visible-label anchor failed")
        source_evidence_by_schema.setdefault(rule.report_norm_id, []).append(evidence_id)
        structural_mappings.append(
            TMPage34StructuralMapping(
                report_norm_id=rule.report_norm_id,
                canonical_name=schema_by_id[rule.report_norm_id].canonical_name,
                evidence_role=rule.evidence_role,
                axis_role=rule.axis_role,
                source_evidence_id=evidence_id,
                visible_label=visible,
                source_line_ids=tuple(
                    f"{parsed.page_tag}:line-{index:04d}" for index in line_indices
                ),
                bbox=bbox,
                visible_label_similarity=similarity,
                mapping_role="DIRECT_VISIBLE_NOTE_OR_OVERALL_MEASURE_HEADER",
            )
        )

    ambiguous_evidence_by_schema: dict[int, list[str]] = {
        report_norm_id: [] for report_norm_id in policy.ambiguous_schema_ids
    }
    source_dispositions = []
    mapped_assignments = []
    for rule in policy.rows:
        row = parsed_by_identity[rule.identity]
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if row.row_role != rule.row_role or observations != rule.expected_observations:
            raise TMPage34MappingError(f"TM page34 row identity/status drifted: {row.row_id}")
        similarity = _similarity(row.row.label, rule.visible_label_anchor)
        if similarity < policy.minimum_visible_label_similarity:
            raise TMPage34MappingError(f"TM page34 visible row label failed: {row.row_id}")
        panel = next(panel for panel in parsed.panels if panel.panel_key == row.panel_key)
        fixed_by_axis = rule.fixed_by_axis
        candidates_by_axis = rule.candidates_by_axis
        if rule.disposition is TMPage34RuleDisposition.FIXED_OVERALL_AXES:
            source_status = TMPage34SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            question_required = False
            reason = "only the two pinned OVERALL specific/general source cells are mapped"
            for report_norm_id in fixed_by_axis.values():
                source_evidence_by_schema.setdefault(report_norm_id, []).append(row.row_id)
        else:
            source_status = TMPage34SourceStatus.AMBIGUOUS_MAPPING.value
            question_required = True
            reason = (
                "audit-adjustment row is visible, but correspondence to generic schema "
                "'Điều chỉnh khác' remains ambiguous"
            )
        cell_dispositions = []
        row_candidate_ids = []
        for cell_index, (axis, cell) in enumerate(zip(panel.axes, row.row.cells, strict=True)):
            if axis.axis_role in fixed_by_axis:
                report_norm_id = fixed_by_axis[axis.axis_role]
                status = TMPage34CellStatus.MAPPED_AUTOMATIC_SCOPED.value
                report_norm_ids = (report_norm_id,)
                candidate_ids: tuple[int, ...] = ()
                cell_question = False
                cell_reason = "pinned OVERALL specific/general row-axis mapping"
            elif axis.axis_role in candidates_by_axis:
                status = TMPage34CellStatus.AMBIGUOUS_MAPPING.value
                report_norm_ids = ()
                candidate_ids = candidates_by_axis[axis.axis_role]
                row_candidate_ids.extend(candidate_ids)
                cell_question = True
                cell_reason = reason
                evidence_id = f"{row.row_id}:cell-{cell_index:04d}"
                for report_norm_id in candidate_ids:
                    ambiguous_evidence_by_schema[report_norm_id].append(evidence_id)
            else:
                status = TMPage34CellStatus.SOURCE_ONLY_GEOGRAPHIC_OR_COMBINED_AXIS.value
                report_norm_ids = ()
                candidate_ids = ()
                cell_question = False
                cell_reason = (
                    "domestic/foreign or combined-total axis retained for provenance/equations; "
                    "mapping authority is limited to OVERALL specific/general"
                )
            source_line_ids = tuple(
                f"{parsed.page_tag}:line-{index:04d}"
                for index in row.value_line_indices[cell_index]
            )
            disposition = TMPage34CellDisposition(
                row_id=row.row_id,
                cell_index=cell_index,
                axis_role=axis.axis_role,
                status=status,
                report_norm_ids=report_norm_ids,
                candidate_report_norm_ids=candidate_ids,
                raw_ocr_texts=row.cell_raw_ocr_texts[cell_index],
                observation=cell.observation.value,
                value=cell.value,
                period_start=row.period_start.isoformat(),
                period_end=row.period_end.isoformat(),
                period_type=row.period_type,
                period_role=row.period_role,
                unit=axis.canonical_unit,
                unit_multiplier=axis.unit_multiplier,
                source_line_ids=source_line_ids,
                value_bbox=row.value_bboxes[cell_index],
                raw_ocr_bboxes=row.raw_ocr_value_bboxes[cell_index],
                visual_cell_evidence=row.visual_cell_evidence[cell_index],
                question_required=cell_question,
                reason=cell_reason,
            )
            cell_dispositions.append(disposition)
            if report_norm_ids:
                report_norm_id = report_norm_ids[0]
                mapped_assignments.append(
                    TMPage34MappedAssignment(
                        report_norm_id=report_norm_id,
                        canonical_name=schema_by_id[report_norm_id].canonical_name,
                        row_id=row.row_id,
                        panel_key=row.panel_key,
                        cell_index=cell_index,
                        axis_role=axis.axis_role,
                        mapping_role="OVERALL_SPECIFIC_OR_GENERAL_DIRECT_VISIBLE_CELL",
                        raw_ocr_texts=row.cell_raw_ocr_texts[cell_index],
                        observation=cell.observation.value,
                        value=cell.value,
                        period_start=row.period_start.isoformat(),
                        period_end=row.period_end.isoformat(),
                        period_type=row.period_type,
                        period_role=row.period_role,
                        unit=axis.canonical_unit,
                        unit_multiplier=axis.unit_multiplier,
                        source_line_ids=source_line_ids,
                        label_bbox=row.label_bbox,
                        value_bbox=row.value_bboxes[cell_index],
                        raw_ocr_bboxes=row.raw_ocr_value_bboxes[cell_index],
                        visual_cell_evidence=row.visual_cell_evidence[cell_index],
                    )
                )
        source_dispositions.append(
            TMPage34SourceDisposition(
                row_id=row.row_id,
                panel_key=row.panel_key,
                ordinal=row.ordinal,
                row_role=row.row_role,
                visible_label=row.row.label,
                status=source_status,
                visible_label_similarity=similarity,
                observations=observations,
                values=tuple(cell.value for cell in row.row.cells),
                period_start=row.period_start.isoformat(),
                period_end=row.period_end.isoformat(),
                period_type=row.period_type,
                period_role=row.period_role,
                source_line_ids=row.row.source_row_ids,
                label_bbox=row.label_bbox,
                cell_dispositions=tuple(cell_dispositions),
                candidate_report_norm_ids=tuple(row_candidate_ids),
                candidate_canonical_names=tuple(
                    schema_by_id[report_norm_id].canonical_name
                    for report_norm_id in row_candidate_ids
                ),
                question_required=question_required,
                reason=reason,
            )
        )

    accounting = _accounting_validation(parsed)
    duplicates = _cross_panel_validation(parsed)
    if (
        len(accounting) != TM_PAGE34_ACCOUNTING_CHECK_COUNT
        or sum(check.status == "PASS" for check in accounting) != TM_PAGE34_ACCOUNTING_PASS_COUNT
        or sum(check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in accounting)
        != TM_PAGE34_ACCOUNTING_NOT_TESTABLE_COUNT
        or any(check.status == "FAIL" for check in accounting)
        or len(duplicates) != TM_PAGE34_DUPLICATE_CHECK_COUNT
        or any(check.status != "PASS" for check in duplicates)
    ):
        raise TMPage34MappingError("TM page34 accounting/cross-panel validation failed")

    ambiguous_ids = set(policy.ambiguous_schema_ids)
    not_observed_ids = set(policy.not_observed_schema_ids)
    schema_dispositions = []
    for item in tm_schema:
        if item.schema_id in source_evidence_by_schema:
            schema_status = TMPage34SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_ids = tuple(source_evidence_by_schema[item.schema_id])
            schema_reason = (
                "fixed title/header or OVERALL specific/general row-axis evidence mapped"
            )
        elif item.schema_id in ambiguous_ids:
            schema_status = TMPage34SchemaStatus.AMBIGUOUS_MAPPING.value
            source_ids = tuple(ambiguous_evidence_by_schema[item.schema_id])
            schema_reason = (
                "visible audit adjustment may correspond to generic adjustment schema item"
            )
        elif item.schema_id in not_observed_ids:
            schema_status = TMPage34SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            source_ids = ()
            schema_reason = "assessed decrease item is not a visible row in either page34 panel"
        else:
            schema_status = TMPage34SchemaStatus.UNASSESSED.value
            source_ids = ()
            schema_reason = "outside the page34 Note 6 schema scope assessed by this batch"
        schema_dispositions.append(
            TMPage34SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=schema_status,
                source_evidence_ids=source_ids,
                reason=schema_reason,
            )
        )
    all_cells = tuple(cell for source in source_dispositions for cell in source.cell_dispositions)
    result = TMPage34MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=34,
        page_tag=policy.page_tag,
        note_number=policy.note_number,
        report_scope=policy.report_scope,
        status="SCOPED_PAGE34_OVERALL_AXES_MAPPING_USER_CONFIRMED",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=len(_SCOPED_IDS),
        mapped_schema_count=len(source_evidence_by_schema),
        ambiguous_schema_count=len(ambiguous_ids),
        not_observed_schema_count=len(not_observed_ids),
        not_applicable_schema_count=0,
        unresolved_schema_count=0,
        unassessed_schema_count=len(tm_schema) - len(_SCOPED_IDS),
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            source.status == TMPage34SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for source in source_dispositions
        ),
        ambiguous_source_row_count=sum(
            source.status == TMPage34SourceStatus.AMBIGUOUS_MAPPING.value
            for source in source_dispositions
        ),
        source_only_row_count=0,
        source_question_row_count=sum(source.question_required for source in source_dispositions),
        partially_mapped_source_row_count=sum(
            any(
                cell.status == TMPage34CellStatus.MAPPED_AUTOMATIC_SCOPED.value
                for cell in source.cell_dispositions
            )
            and any(
                cell.status == TMPage34CellStatus.SOURCE_ONLY_GEOGRAPHIC_OR_COMBINED_AXIS.value
                for cell in source.cell_dispositions
            )
            for source in source_dispositions
        ),
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_status_assignment_count=len(mapped_assignments),
        mapped_value_assignment_count=sum(
            assignment.observation in {ObservationKind.VALUE.value, ObservationKind.ZERO.value}
            for assignment in mapped_assignments
        ),
        mapped_dash_assignment_count=sum(
            assignment.observation == ObservationKind.DASH.value
            for assignment in mapped_assignments
        ),
        ambiguous_source_slot_count=sum(
            cell.status == TMPage34CellStatus.AMBIGUOUS_MAPPING.value for cell in all_cells
        ),
        source_only_slot_count=sum(
            cell.status == TMPage34CellStatus.SOURCE_ONLY_GEOGRAPHIC_OR_COMBINED_AXIS.value
            for cell in all_cells
        ),
        accounting_check_count=len(accounting),
        accounting_pass_count=sum(check.status == "PASS" for check in accounting),
        accounting_not_testable_count=sum(
            check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in accounting
        ),
        duplicate_check_count=len(duplicates),
        duplicate_pass_count=sum(check.status == "PASS" for check in duplicates),
        structural_mappings=tuple(structural_mappings),
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        mapped_assignments=tuple(mapped_assignments),
        accounting_checks=accounting,
        duplicate_checks=duplicates,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        dash_pixel_evidence_sha256=_dash_evidence_hash(parsed),
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS_AND_NINE_AXIS_GEOMETRY",
            "VISIBLE_PAGE34_NOTE_PANEL_AND_ROW_ORDER",
            "OVERALL_SPECIFIC_GENERAL_AXES_ONLY",
            "CONSTRAINED_PIXEL_DASH_EVIDENCE_FOR_STATUS_ONLY",
            "VISIBLE_PERIOD_SCOPE_AND_UNIT",
            "TM_SCHEMA_ID_NAME_ORDER",
            "GEOGRAPHIC_MEASURE_AND_ROLLFORWARD_EQUATIONS_AS_VALIDATION_ONLY",
        ),
    )
    return validate_tm_page34_mapping_result(result)


def validate_tm_page34_mapping_result(result: TMPage34MappingResult) -> TMPage34MappingResult:
    """Enforce exact source, schema, cell-authority, and validation denominators."""

    if (
        result.schema_item_count != TM_PAGE34_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE34_RECONCILED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE34_MAPPED_SCHEMA_COUNT
        or result.ambiguous_schema_count != TM_PAGE34_AMBIGUOUS_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE34_NOT_OBSERVED_SCHEMA_COUNT
        or result.not_applicable_schema_count != 0
        or result.unresolved_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE34_UNASSESSED_SCHEMA_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE34_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE34_MAPPED_SOURCE_ROW_COUNT
        or result.ambiguous_source_row_count != TM_PAGE34_AMBIGUOUS_SOURCE_ROW_COUNT
        or result.source_only_row_count != 0
        or result.source_question_row_count != 0
        or result.partially_mapped_source_row_count != TM_PAGE34_PARTIALLY_MAPPED_SOURCE_ROW_COUNT
        or result.financial_slot_count != TM_PAGE34_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE34_VALUE_COUNT
        or result.dash_count != TM_PAGE34_DASH_COUNT
        or result.mapped_status_assignment_count != TM_PAGE34_MAPPED_STATUS_ASSIGNMENT_COUNT
        or result.mapped_value_assignment_count != TM_PAGE34_MAPPED_VALUE_ASSIGNMENT_COUNT
        or result.mapped_dash_assignment_count != TM_PAGE34_MAPPED_DASH_ASSIGNMENT_COUNT
        or result.ambiguous_source_slot_count != TM_PAGE34_AMBIGUOUS_SLOT_COUNT
        or result.source_only_slot_count != TM_PAGE34_SOURCE_ONLY_SLOT_COUNT
        or result.accounting_check_count != TM_PAGE34_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_PAGE34_ACCOUNTING_PASS_COUNT
        or result.accounting_not_testable_count != TM_PAGE34_ACCOUNTING_NOT_TESTABLE_COUNT
        or result.duplicate_check_count != TM_PAGE34_DUPLICATE_CHECK_COUNT
        or result.duplicate_pass_count != TM_PAGE34_DUPLICATE_CHECK_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage34MappingError("TM page34 mapping result denominator drifted")
    if (
        result.mapped_schema_count
        + result.ambiguous_schema_count
        + result.not_observed_schema_count
        != result.status_reconciled_schema_count
        or result.status_reconciled_schema_count + result.unassessed_schema_count
        != result.schema_item_count
        or result.mapped_source_row_count + result.ambiguous_source_row_count
        != result.source_row_count
        or result.mapped_status_assignment_count
        + result.ambiguous_source_slot_count
        + result.source_only_slot_count
        != result.financial_slot_count
    ):
        raise TMPage34MappingError("TM page34 status counts do not reconcile")
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMPage34SchemaStatus)
    }
    if (
        by_status[TMPage34SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] != _MAPPED_IDS
        or by_status[TMPage34SchemaStatus.AMBIGUOUS_MAPPING.value] != _AMBIGUOUS_IDS
        or by_status[TMPage34SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] != _NOT_OBSERVED_IDS
    ):
        raise TMPage34MappingError("TM page34 schema status sets drifted")
    if any(
        assignment.axis_role not in _MAPPING_AXES for assignment in result.mapped_assignments
    ) or len({(item.row_id, item.cell_index) for item in result.mapped_assignments}) != len(
        result.mapped_assignments
    ):
        raise TMPage34MappingError("TM page34 mapping exceeded overall-axis authority")
    mapped_dashes = [
        item for item in result.mapped_assignments if item.observation == ObservationKind.DASH.value
    ]
    if len(mapped_dashes) != 2 or any(
        item.value is not None or item.visual_cell_evidence is None for item in mapped_dashes
    ):
        raise TMPage34MappingError("TM page34 mapped DASH status lost visual provenance")
    ambiguous_cells = [
        cell
        for source in result.source_dispositions
        for cell in source.cell_dispositions
        if cell.status == TMPage34CellStatus.AMBIGUOUS_MAPPING.value
    ]
    if ambiguous_cells:
        raise TMPage34MappingError("TM page34 retains a resolved ambiguity")
    audit_assignments = [
        item
        for item in result.mapped_assignments
        if item.panel_key == "FY_2025" and item.report_norm_id in {790, 798}
    ]
    if [
        (item.axis_role, item.report_norm_id, item.value, item.period_end)
        for item in audit_assignments
    ] != [
        ("OVERALL_SPECIFIC", 798, Decimal("33942"), "2025-12-31"),
        ("OVERALL_GENERAL", 790, Decimal("-1444"), "2025-12-31"),
    ]:
        raise TMPage34MappingError("TM page34 audit-adjustment mapping drifted")
    if any(
        cell.report_norm_ids or cell.question_required
        for source in result.source_dispositions
        for cell in source.cell_dispositions
        if cell.axis_role
        in {
            "DOMESTIC_SPECIFIC",
            "DOMESTIC_GENERAL",
            "DOMESTIC_COMBINED",
            "FOREIGN_SPECIFIC",
            "FOREIGN_GENERAL",
            "FOREIGN_COMBINED",
            "OVERALL_COMBINED",
        }
    ):
        raise TMPage34MappingError("TM page34 geography/combined axes leaked into export")
    if any(check.status == "FAIL" for check in result.accounting_checks) or any(
        check.status != "PASS" for check in result.duplicate_checks
    ):
        raise TMPage34MappingError("TM page34 validation contains a failure")
    return result


__all__ = [
    "TM_PAGE34_MAPPING_POLICY_RELATIVE_PATH",
    "TMPage34AccountingCheck",
    "TMPage34CellStatus",
    "TMPage34DuplicateCheck",
    "TMPage34MappedAssignment",
    "TMPage34MappingError",
    "TMPage34MappingPolicy",
    "TMPage34MappingResult",
    "TMPage34SchemaStatus",
    "TMPage34SourceStatus",
    "load_tm_page34_mapping_policy",
    "reconcile_tm_page34_items",
    "validate_tm_page34_mapping_result",
]
