"""Source-scoped item and cell mapping for MBB consolidated TM page 43."""

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
from bctc_ai.tables.tm_note_page43 import ParsedTMPage43
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind

TM_PAGE43_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page43-v1.yaml")
TM_PAGE43_SCHEMA_TOTAL = 1_712
TM_PAGE43_RECONCILED_SCHEMA_COUNT = 131
TM_PAGE43_MAPPED_SCHEMA_COUNT = 34
TM_PAGE43_AMBIGUOUS_SCHEMA_COUNT = 0
TM_PAGE43_NOT_OBSERVED_COUNT = 97
TM_PAGE43_UNASSESSED_COUNT = 1_581
TM_PAGE43_SOURCE_ROW_COUNT = 29
TM_PAGE43_MAPPED_SOURCE_COUNT = 24
TM_PAGE43_SOURCE_ONLY_COUNT = 5
TM_PAGE43_PARTIAL_SOURCE_COUNT = 6
TM_PAGE43_FINANCIAL_SLOT_COUNT = 50
TM_PAGE43_VALUE_COUNT = 44
TM_PAGE43_DASH_COUNT = 6
TM_PAGE43_MAPPED_SOURCE_SLOT_COUNT = 42
TM_PAGE43_MAPPED_VALUE_ASSIGNMENT_COUNT = 38
TM_PAGE43_MAPPED_DASH_ASSIGNMENT_COUNT = 8
TM_PAGE43_MAPPED_STATUS_ASSIGNMENT_COUNT = 46
TM_PAGE43_ACCOUNTING_CHECK_COUNT = 16
TM_PAGE43_ACCOUNTING_PASS_COUNT = 14
TM_PAGE43_ACCOUNTING_NOT_TESTABLE_COUNT = 2
TM_PAGE43_DUPLICATE_CHECK_COUNT = 10

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
}
_SCOPED_IDS = set(range(631, 716)) | set(range(1055, 1100)) | {5977}
_MAPPED_IDS = {
    631,
    660,
    661,
    662,
    663,
    674,
    675,
    676,
    677,
    688,
    689,
    690,
    691,
    702,
    703,
    704,
    705,
    1055,
    1056,
    1057,
    1058,
    1059,
    1060,
    1061,
    1062,
    1066,
    1067,
    1068,
    1069,
    1075,
    1089,
    1092,
    1093,
    5977,
}
_AMBIGUOUS_IDS: set[int] = set()
_MULTI_ID_CELL_PAIRS = {
    (660, 661),
    (674, 675),
    (688, 689),
    (702, 703),
}
_EXPECTED_REUSED_CELLS = {
    ("DERIVATIVES", 3, 0): (660, 661),
    ("DERIVATIVES", 3, 1): (688, 689),
    ("DERIVATIVES", 7, 0): (674, 675),
    ("DERIVATIVES", 7, 1): (702, 703),
}
_TABLE_WIDTHS = {
    "DEPOSIT_TYPE": 2,
    "DEPOSIT_CUSTOMER": 2,
    "DERIVATIVES": 3,
    "TRUST_FUNDING": 2,
}


class TMPage43MappingError(ValueError):
    pass


class TMPage43RuleDisposition(StrEnum):
    FIXED_ROW = "FIXED_ROW"
    FIXED_CELLS_WITH_SOURCE_ONLY_MEASURE = "FIXED_CELLS_WITH_SOURCE_ONLY_MEASURE"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"


class TMPage43SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage43SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    PARTIALLY_MAPPED_AUTOMATIC_SCOPED = "PARTIALLY_MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"


class TMPage43CellStatus(StrEnum):
    MAPPED_VALUE_AUTOMATIC_SCOPED = "MAPPED_VALUE_AUTOMATIC_SCOPED"
    MAPPED_DASH_AUTOMATIC_SCOPED = "MAPPED_DASH_AUTOMATIC_SCOPED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    STRUCTURAL_BLANK = "STRUCTURAL_BLANK"


@dataclass(frozen=True)
class TMPage43RowRule:
    table_key: str
    ordinal: int
    visible_label_anchor: str | None
    expected_row_kind: str
    expected_observations: tuple[str, ...]
    disposition: TMPage43RuleDisposition
    row_report_norm_ids: tuple[int, ...]
    cell_report_norm_ids: tuple[tuple[int, ...], ...]
    source_only_cell_indices: tuple[int, ...]
    candidate_report_norm_ids: tuple[int, ...]

    @property
    def identity(self) -> tuple[str, int]:
        return self.table_key, self.ordinal

    @property
    def mapped_report_norm_ids(self) -> tuple[int, ...]:
        return tuple(
            dict.fromkeys(
                [
                    *self.row_report_norm_ids,
                    *(item for cell in self.cell_report_norm_ids for item in cell),
                ]
            )
        )


@dataclass(frozen=True)
class TMPage43MappingPolicy:
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
    rows: tuple[TMPage43RowRule, ...]
    ambiguous_schema_ids: tuple[int, ...]
    not_observed_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage43SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage43CellDisposition:
    cell_index: int
    axis_id: str
    observation: str
    raw_text: str
    value: Decimal | None
    period_end: str | None
    period_role: str | None
    measure_role: str
    unit: str
    unit_multiplier: int
    status: str
    report_norm_ids: tuple[int, ...]
    report_norm_id_roles: tuple[str, ...]
    canonical_names: tuple[str, ...]
    visual_cell_evidence: VisualCellEvidence | None
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage43SourceDisposition:
    row_id: str
    table_key: str
    ordinal: int
    visible_label: str
    row_kind: str
    source_role: str
    status: str
    row_report_norm_ids: tuple[int, ...]
    mapped_report_norm_ids: tuple[int, ...]
    canonical_names: tuple[str, ...]
    candidate_report_norm_ids: tuple[int, ...]
    candidate_canonical_names: tuple[str, ...]
    visible_label_similarity: float | None
    observations: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    period_ends: tuple[str | None, ...]
    period_roles: tuple[str | None, ...]
    measure_roles: tuple[str, ...]
    unit: str
    unit_multiplier: int
    cell_dispositions: tuple[TMPage43CellDisposition, ...]
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage43MappedAssignment:
    report_norm_id: int
    canonical_name: str
    mapping_role: str
    row_id: str
    cell_index: int
    axis_id: str
    observation: str
    value: Decimal | None
    period_end: str
    period_role: str
    measure_role: str
    unit: str
    unit_multiplier: int
    visual_cell_evidence: VisualCellEvidence | None


@dataclass(frozen=True)
class TMPage43AccountingCheck:
    check_id: str
    axis_role: str
    status: str
    expected_value: Decimal | None
    observed_value: Decimal | None
    residual: Decimal | None
    reason: str


@dataclass(frozen=True)
class TMPage43DuplicateCheck:
    check_id: str
    axis_role: str
    primary_value: Decimal
    duplicate_value: Decimal
    residual: Decimal
    status: str


@dataclass(frozen=True)
class TMPage43MappingResult:
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
    partially_mapped_source_row_count: int
    source_question_row_count: int
    ambiguous_source_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_source_slot_count: int
    mapped_value_assignment_count: int
    mapped_dash_assignment_count: int
    mapped_status_assignment_count: int
    accounting_check_count: int
    accounting_pass_count: int
    accounting_not_testable_count: int
    duplicate_check_count: int
    duplicate_pass_count: int
    schema_dispositions: tuple[TMPage43SchemaDisposition, ...]
    source_dispositions: tuple[TMPage43SourceDisposition, ...]
    mapped_assignments: tuple[TMPage43MappedAssignment, ...]
    accounting_checks: tuple[TMPage43AccountingCheck, ...]
    duplicate_checks: tuple[TMPage43DuplicateCheck, ...]
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
        raise TMPage43MappingError(f"invalid positive TM page-43 field: {field}")
    return value


def _ids(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(payload, list)
        or (not payload and not allow_empty)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload)
    ):
        raise TMPage43MappingError(f"TM page-43 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMPage43MappingError(f"TM page-43 {field} contains duplicates")
    return result


def load_tm_page43_mapping_policy(path: Path) -> TMPage43MappingPolicy:
    """Load exact row/cell mapping authority and complete scoped statuses."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage43MappingError(f"cannot load TM page-43 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE43_SCOPED_MULTI_AXIS_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 43
        or payload.get("page_tag") != "page-0043"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage43MappingError("TM page-43 mapping policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage43MappingError("TM page-43 mapping source hashes are invalid")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 < float(threshold) <= 1
    ):
        raise TMPage43MappingError("TM page-43 mapping similarity threshold is invalid")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE43_SOURCE_ROW_COUNT:
        raise TMPage43MappingError("TM page-43 mapping row denominator drifted")
    valid_observations = {observation.value for observation in ObservationKind}
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage43MappingError("TM page-43 mapping row is invalid")
        table_key = record.get("table_key")
        width = _TABLE_WIDTHS.get(str(table_key))
        ordinal = record.get("ordinal")
        label = record.get("visible_label_anchor")
        row_kind = record.get("expected_row_kind")
        observations = record.get("expected_observations")
        try:
            disposition = TMPage43RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMPage43MappingError("TM page-43 rule disposition is invalid") from exc
        row_ids = _ids(record.get("row_report_norm_ids"), "row ReportNormIds", allow_empty=True)
        raw_cell_ids = record.get("cell_report_norm_ids")
        if not isinstance(raw_cell_ids, list) or width is None or len(raw_cell_ids) != width:
            raise TMPage43MappingError("TM page-43 cell ReportNormIds are invalid")
        cell_ids = tuple(
            _ids(value, "cell ReportNormIds", allow_empty=True) for value in raw_cell_ids
        )
        source_only = _ids(
            record.get("source_only_cell_indices"), "source-only cell indices", allow_empty=True
        )
        candidates = _ids(
            record.get("candidate_report_norm_ids"), "candidate ReportNormIds", allow_empty=True
        )
        if (
            not isinstance(table_key, str)
            or width is None
            or isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal <= 0
            or (label is not None and not isinstance(label, str))
            or row_kind not in {kind.value for kind in TMNoteRowKind}
            or not isinstance(observations, list)
            or len(observations) != width
            or any(value not in valid_observations for value in observations)
            or any(index < 0 or index >= width for index in source_only)
        ):
            raise TMPage43MappingError("TM page-43 mapping row identity is invalid")
        if disposition is TMPage43RuleDisposition.FIXED_ROW:
            if len(row_ids) != 1 or any(cell_ids) or source_only or candidates:
                raise TMPage43MappingError("TM page-43 fixed-row rule is malformed")
        elif disposition is TMPage43RuleDisposition.FIXED_CELLS_WITH_SOURCE_ONLY_MEASURE:
            if row_ids or not any(cell_ids) or source_only != (2,) or candidates:
                raise TMPage43MappingError("TM page-43 fixed-cell rule is malformed")
            if any(cell_ids[index] for index in source_only):
                raise TMPage43MappingError("TM page-43 source-only measure received an ID")
        elif disposition is TMPage43RuleDisposition.AMBIGUOUS_MAPPING:
            if row_ids or any(cell_ids) or not candidates or not source_only:
                raise TMPage43MappingError("TM page-43 ambiguous rule is malformed")
        elif row_ids or any(cell_ids) or candidates:
            raise TMPage43MappingError("TM page-43 source-only rule selects a ReportNormId")
        rows.append(
            TMPage43RowRule(
                table_key=table_key,
                ordinal=ordinal,
                visible_label_anchor=retrieval_key(label) if label is not None else None,
                expected_row_kind=row_kind,
                expected_observations=tuple(observations),
                disposition=disposition,
                row_report_norm_ids=row_ids,
                cell_report_norm_ids=cell_ids,
                source_only_cell_indices=source_only,
                candidate_report_norm_ids=candidates,
            )
        )
    if len({row.identity for row in rows}) != len(rows):
        raise TMPage43MappingError("TM page-43 rule identities are duplicated")
    fixed_ids = {item for row in rows for item in row.mapped_report_norm_ids}
    ambiguous = _ids(payload.get("ambiguous_schema_ids"), "ambiguous schema IDs", allow_empty=True)
    not_observed = _ids(payload.get("not_observed_schema_ids"), "not-observed IDs")
    if fixed_ids != _MAPPED_IDS:
        raise TMPage43MappingError("TM page-43 fixed ReportNormIds drifted")
    multi_id_pairs = {cell for row in rows for cell in row.cell_report_norm_ids if len(cell) > 1}
    if multi_id_pairs != _MULTI_ID_CELL_PAIRS or any(
        len(cell) > 2 for row in rows for cell in row.cell_report_norm_ids
    ):
        raise TMPage43MappingError("TM page-43 aggregate/child reuse pairs drifted")
    reused_cells = {
        (row.table_key, row.ordinal, cell_index): cell
        for row in rows
        for cell_index, cell in enumerate(row.cell_report_norm_ids)
        if len(cell) > 1
    }
    if reused_cells != _EXPECTED_REUSED_CELLS:
        raise TMPage43MappingError("TM page-43 aggregate/child reuse locations drifted")
    if set(ambiguous) != _AMBIGUOUS_IDS:
        raise TMPage43MappingError("TM page-43 ambiguous ReportNormIds drifted")
    if (
        len(not_observed) != TM_PAGE43_NOT_OBSERVED_COUNT
        or fixed_ids & set(not_observed)
        or set(ambiguous) & set(not_observed)
        or fixed_ids | set(ambiguous) | set(not_observed) != _SCOPED_IDS
    ):
        raise TMPage43MappingError("TM page-43 complete scoped statuses drifted")
    candidate_ids = {item for row in rows for item in row.candidate_report_norm_ids}
    if candidate_ids != set(ambiguous):
        raise TMPage43MappingError("TM page-43 ambiguous source/schema linkage drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage43MappingError("TM page-43 forbidden mapping inputs drifted")
    document = payload.get("document")
    mapping_scope = payload.get("mapping_authority_scope")
    if not isinstance(document, str) or not isinstance(mapping_scope, str) or not mapping_scope:
        raise TMPage43MappingError("TM page-43 mapping scope is invalid")
    return TMPage43MappingPolicy(
        source_path=path,
        document=document,
        page_number=43,
        page_tag="page-0043",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=mapping_scope,
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        schema_total=_positive_int(payload, "schema_total"),
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


def _mapping_roles(report_norm_ids: tuple[int, ...]) -> tuple[str, ...]:
    if not report_norm_ids:
        return ()
    if len(report_norm_ids) == 1:
        return ("DIRECT_VISIBLE_ROW_OR_MEASURE",)
    if report_norm_ids not in _MULTI_ID_CELL_PAIRS:
        raise TMPage43MappingError("TM page-43 unauthorized multi-ID cell projection")
    return (
        "AGGREGATE_MEASURE_TOTAL_FROM_COMBINED_VISIBLE_ROW",
        "PRIMARY_ONLY_VISIBLE_CURRENCY_DERIVATIVE_CHILD",
    )


def _schema_hash(items: tuple[SchemaItem, ...]) -> str:
    payload = [(item.schema_id, item.display_order, item.canonical_name) for item in items]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode("utf-8")).hexdigest()


def _dash_evidence_hash(parsed: ParsedTMPage43) -> str:
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


def _value(parsed: ParsedTMPage43, table_key: str, ordinal: int, axis: int) -> Decimal:
    row = next(row for row in parsed.rows if row.table_key == table_key and row.ordinal == ordinal)
    value = row.row.cells[axis].value
    if value is None:
        raise TMPage43MappingError("TM page-43 numeric validation received a non-value cell")
    return value


def _validation(
    parsed: ParsedTMPage43,
) -> tuple[tuple[TMPage43AccountingCheck, ...], tuple[TMPage43DuplicateCheck, ...]]:
    accounting = []

    def equation(
        check_id: str,
        table_key: str,
        components: tuple[int, ...],
        total: int,
        axis: int,
        axis_role: str,
    ) -> None:
        expected = sum(
            (_value(parsed, table_key, ordinal, axis) for ordinal in components), Decimal(0)
        )
        observed = _value(parsed, table_key, total, axis)
        residual = observed - expected
        accounting.append(
            TMPage43AccountingCheck(
                check_id=check_id,
                axis_role=axis_role,
                status="PASS" if residual == 0 else "FAIL",
                expected_value=expected,
                observed_value=observed,
                residual=residual,
                reason="visible values combined without blank/dash coercion",
            )
        )

    for axis, role in enumerate(("CURRENT", "COMPARATIVE")):
        equation("DEMAND_EQUALS_VND_PLUS_FX", "DEPOSIT_TYPE", (4, 5), 3, axis, role)
        equation("TERM_EQUALS_VND_PLUS_FX", "DEPOSIT_TYPE", (7, 8), 6, axis, role)
        equation("MARGIN_EQUALS_VND_PLUS_FX", "DEPOSIT_TYPE", (11, 12), 10, axis, role)
        equation(
            "DEPOSIT_TOTAL_EQUALS_FOUR_VISIBLE_CLASSES",
            "DEPOSIT_TYPE",
            (3, 6, 9, 10),
            13,
            axis,
            role,
        )
        equation(
            "CUSTOMER_CLASSES_EQUAL_VISIBLE_TOTAL",
            "DEPOSIT_CUSTOMER",
            (2, 3),
            4,
            axis,
            role,
        )
    for total, components, role in (
        (3, (4, 5), "CURRENT"),
        (7, (8, 9), "COMPARATIVE"),
    ):
        equation(
            "DERIVATIVE_LIABILITY_TOTAL_EQUALS_FORWARD_PLUS_SWAP",
            "DERIVATIVES",
            components,
            total,
            1,
            role,
        )
        equation(
            "DERIVATIVE_NET_TOTAL_EQUALS_FORWARD_PLUS_SWAP",
            "DERIVATIVES",
            components,
            total,
            2,
            role,
        )
    for total, components, role in (
        (3, (4, 5), "CURRENT"),
        (7, (8, 9), "COMPARATIVE"),
    ):
        rows = [
            next(
                item
                for item in parsed.rows
                if item.table_key == "DERIVATIVES" and item.ordinal == ordinal
            )
            for ordinal in (total, *components)
        ]
        if any(row.row.cells[0].observation is not ObservationKind.DASH for row in rows):
            raise TMPage43MappingError("TM page-43 derivative asset rollup dash status drifted")
        accounting.append(
            TMPage43AccountingCheck(
                check_id="DERIVATIVE_ASSET_TOTAL_EQUALS_FORWARD_PLUS_SWAP",
                axis_role=role,
                status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
                expected_value=None,
                observed_value=None,
                residual=None,
                reason="aggregate and child cells are visible DASH statuses, not numeric zeros",
            )
        )
    duplicates = []

    def duplicate(
        check_id: str,
        axis_role: str,
        primary: Decimal,
        repeated: Decimal,
    ) -> None:
        residual = repeated - primary
        duplicates.append(
            TMPage43DuplicateCheck(
                check_id=check_id,
                axis_role=axis_role,
                primary_value=primary,
                duplicate_value=repeated,
                residual=residual,
                status="PASS" if residual == 0 else "FAIL",
            )
        )

    for axis, role in enumerate(("CURRENT", "COMPARATIVE")):
        duplicate(
            "DEPOSIT_TOTAL_REPEATS_ACROSS_TWO_ANALYSES",
            role,
            _value(parsed, "DEPOSIT_TYPE", 13, axis),
            _value(parsed, "DEPOSIT_CUSTOMER", 4, axis),
        )
    for ordinal, role in (
        (3, "CURRENT"),
        (4, "CURRENT"),
        (5, "CURRENT"),
        (7, "COMPARATIVE"),
        (8, "COMPARATIVE"),
        (9, "COMPARATIVE"),
    ):
        duplicate(
            "DERIVATIVE_LIABILITY_EQUALS_VISIBLE_NET",
            f"{role}:ROW_{ordinal:04d}",
            _value(parsed, "DERIVATIVES", ordinal, 1),
            _value(parsed, "DERIVATIVES", ordinal, 2),
        )
    for axis, role in enumerate(("CURRENT", "COMPARATIVE")):
        duplicate(
            "TRUST_FUNDING_DETAIL_EQUALS_VISIBLE_TOTAL",
            role,
            _value(parsed, "TRUST_FUNDING", 2, axis),
            _value(parsed, "TRUST_FUNDING", 3, axis),
        )
    return tuple(accounting), tuple(duplicates)


def reconcile_tm_page43_items(
    parsed: ParsedTMPage43,
    *,
    schema: list[SchemaItem],
    policy: TMPage43MappingPolicy,
    source_pdf_path: Path,
) -> TMPage43MappingResult:
    """Apply only policy-authorized page-43 row/cell mappings and abstentions."""

    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
    ):
        raise TMPage43MappingError("TM page-43 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage43MappingError("TM page-43 source PDF hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE43_SCHEMA_TOTAL:
        raise TMPage43MappingError("TM schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    referenced = (
        {item for row in policy.rows for item in row.mapped_report_norm_ids}
        | {item for row in policy.rows for item in row.candidate_report_norm_ids}
        | set(policy.ambiguous_schema_ids)
        | set(policy.not_observed_schema_ids)
    )
    if not referenced <= set(schema_by_id):
        raise TMPage43MappingError("TM page-43 policy references unknown ReportNormIds")
    parsed_by_identity = {(row.table_key, row.ordinal): row for row in parsed.rows}
    if tuple(parsed_by_identity) != tuple(rule.identity for rule in policy.rows):
        raise TMPage43MappingError("TM page-43 parsed row order drifted from policy")
    table_by_key = {table.table_key: table for table in parsed.tables}
    source_dispositions = []
    assignments = []
    source_rows_by_schema: dict[int, list[str]] = {}
    ambiguous_rows_by_schema: dict[int, list[str]] = {}
    for rule in policy.rows:
        row = parsed_by_identity[rule.identity]
        table = table_by_key[row.table_key]
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if (
            row.row_kind.value != rule.expected_row_kind
            or observations != rule.expected_observations
        ):
            raise TMPage43MappingError(f"TM page-43 row status drifted: {row.row_id}")
        if rule.visible_label_anchor is None:
            if row.row.label:
                raise TMPage43MappingError(f"TM page-43 expected unlabeled total: {row.row_id}")
            similarity = None
        else:
            similarity = _similarity(row.row.label, rule.visible_label_anchor)
            if similarity < policy.minimum_visible_label_similarity:
                raise TMPage43MappingError(f"TM page-43 label anchor failed: {row.row_id}")
        mapped_ids = rule.mapped_report_norm_ids
        for report_norm_id in mapped_ids:
            source_rows_by_schema.setdefault(report_norm_id, []).append(row.row_id)
        for report_norm_id in rule.candidate_report_norm_ids:
            ambiguous_rows_by_schema.setdefault(report_norm_id, []).append(row.row_id)
        if mapped_ids and rule.source_only_cell_indices:
            source_status = TMPage43SourceStatus.PARTIALLY_MAPPED_AUTOMATIC_SCOPED.value
            question_required = True
            reason = (
                "fixed page-43 cell mappings passed; the visible net measure has no schema identity"
            )
        elif mapped_ids:
            source_status = TMPage43SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            question_required = False
            reason = "fixed page-43 note hierarchy, row order and visible-label rule passed"
        elif rule.disposition is TMPage43RuleDisposition.AMBIGUOUS_MAPPING:
            source_status = TMPage43SourceStatus.AMBIGUOUS_MAPPING.value
            question_required = True
            reason = "visible personal-deposit row is narrower than candidate schema identity 1089"
        elif rule.disposition is TMPage43RuleDisposition.SOURCE_ONLY_QUESTION:
            source_status = TMPage43SourceStatus.SOURCE_ONLY_QUESTION.value
            question_required = True
            reason = "visible source row has no exact schema identity and remains an open question"
        else:
            source_status = TMPage43SourceStatus.SOURCE_ONLY_VALIDATION.value
            question_required = False
            reason = "duplicate or structural source row retained for provenance/validation only"
        cells = []
        for cell_index, (cell, axis) in enumerate(zip(row.row.cells, table.axes, strict=True)):
            cell_report_ids = (
                rule.row_report_norm_ids
                if row.row_kind is TMNoteRowKind.NUMERIC and rule.row_report_norm_ids
                else rule.cell_report_norm_ids[cell_index]
            )
            cell_mapping_roles = _mapping_roles(cell_report_ids)
            if cell_report_ids:
                if cell.observation is ObservationKind.DASH:
                    cell_status = TMPage43CellStatus.MAPPED_DASH_AUTOMATIC_SCOPED.value
                elif cell.observation in {ObservationKind.VALUE, ObservationKind.ZERO}:
                    cell_status = TMPage43CellStatus.MAPPED_VALUE_AUTOMATIC_SCOPED.value
                else:
                    raise TMPage43MappingError("TM page-43 mapped cell has no financial status")
                cell_question = False
                cell_reason = "fixed row/measure mapping passed independently of cell magnitude"
            elif cell_index in rule.source_only_cell_indices:
                if rule.disposition is TMPage43RuleDisposition.AMBIGUOUS_MAPPING:
                    cell_status = TMPage43CellStatus.AMBIGUOUS_MAPPING.value
                    cell_reason = "candidate 1089 is broader than the visible personal-only row"
                elif rule.disposition is TMPage43RuleDisposition.SOURCE_ONLY_VALIDATION:
                    cell_status = TMPage43CellStatus.SOURCE_ONLY_VALIDATION.value
                    cell_reason = "duplicate cell retained without duplicate export"
                else:
                    cell_status = TMPage43CellStatus.SOURCE_ONLY_QUESTION.value
                    cell_reason = "visible cell has no exact target schema measure/item"
                cell_question = (
                    rule.disposition is not TMPage43RuleDisposition.SOURCE_ONLY_VALIDATION
                )
            elif row.row_kind is TMNoteRowKind.LABEL_ONLY:
                cell_status = TMPage43CellStatus.STRUCTURAL_BLANK.value
                cell_question = False
                cell_reason = "structural schema/source row has no financial cell"
            else:
                cell_status = TMPage43CellStatus.SOURCE_ONLY_VALIDATION.value
                cell_question = False
                cell_reason = "duplicate numeric cell retained for validation only"
            period = row.cell_period_ends[cell_index]
            period_role = row.cell_period_roles[cell_index]
            cells.append(
                TMPage43CellDisposition(
                    cell_index=cell_index,
                    axis_id=axis.axis_id,
                    observation=cell.observation.value,
                    raw_text=cell.raw_text,
                    value=cell.value,
                    period_end=period.isoformat() if period is not None else None,
                    period_role=period_role,
                    measure_role=row.cell_measure_roles[cell_index],
                    unit=axis.canonical_unit,
                    unit_multiplier=axis.unit_multiplier,
                    status=cell_status,
                    report_norm_ids=cell_report_ids,
                    report_norm_id_roles=cell_mapping_roles,
                    canonical_names=tuple(
                        schema_by_id[report_norm_id].canonical_name
                        for report_norm_id in cell_report_ids
                    ),
                    visual_cell_evidence=row.visual_cell_evidence[cell_index],
                    question_required=cell_question,
                    reason=cell_reason,
                )
            )
            if cell_report_ids:
                if period is None or period_role is None:
                    raise TMPage43MappingError("TM page-43 mapped financial cell has no period")
                for report_norm_id, mapping_role in zip(
                    cell_report_ids, cell_mapping_roles, strict=True
                ):
                    assignments.append(
                        TMPage43MappedAssignment(
                            report_norm_id=report_norm_id,
                            canonical_name=schema_by_id[report_norm_id].canonical_name,
                            mapping_role=mapping_role,
                            row_id=row.row_id,
                            cell_index=cell_index,
                            axis_id=axis.axis_id,
                            observation=cell.observation.value,
                            value=cell.value,
                            period_end=period.isoformat(),
                            period_role=period_role,
                            measure_role=row.cell_measure_roles[cell_index],
                            unit=axis.canonical_unit,
                            unit_multiplier=axis.unit_multiplier,
                            visual_cell_evidence=row.visual_cell_evidence[cell_index],
                        )
                    )
        source_dispositions.append(
            TMPage43SourceDisposition(
                row_id=row.row_id,
                table_key=row.table_key,
                ordinal=row.ordinal,
                visible_label=row.row.label,
                row_kind=row.row_kind.value,
                source_role=row.source_role,
                status=source_status,
                row_report_norm_ids=rule.row_report_norm_ids,
                mapped_report_norm_ids=mapped_ids,
                canonical_names=tuple(
                    schema_by_id[report_norm_id].canonical_name for report_norm_id in mapped_ids
                ),
                candidate_report_norm_ids=rule.candidate_report_norm_ids,
                candidate_canonical_names=tuple(
                    schema_by_id[report_norm_id].canonical_name
                    for report_norm_id in rule.candidate_report_norm_ids
                ),
                visible_label_similarity=similarity,
                observations=observations,
                values=tuple(cell.value for cell in row.row.cells),
                period_ends=tuple(
                    period.isoformat() if period is not None else None
                    for period in row.cell_period_ends
                ),
                period_roles=row.cell_period_roles,
                measure_roles=row.cell_measure_roles,
                unit=table.axes[0].canonical_unit,
                unit_multiplier=table.axes[0].unit_multiplier,
                cell_dispositions=tuple(cells),
                question_required=question_required,
                reason=reason,
            )
        )
    accounting, duplicates = _validation(parsed)
    if (
        len(accounting) != TM_PAGE43_ACCOUNTING_CHECK_COUNT
        or sum(check.status == "PASS" for check in accounting) != TM_PAGE43_ACCOUNTING_PASS_COUNT
        or sum(check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in accounting)
        != TM_PAGE43_ACCOUNTING_NOT_TESTABLE_COUNT
        or any(check.status == "FAIL" for check in accounting)
        or len(duplicates) != TM_PAGE43_DUPLICATE_CHECK_COUNT
        or any(check.status != "PASS" for check in duplicates)
    ):
        raise TMPage43MappingError("TM page-43 accounting or duplicate validation failed")
    not_observed = set(policy.not_observed_schema_ids)
    ambiguous = set(policy.ambiguous_schema_ids)
    schema_dispositions = []
    for item in tm_schema:
        if item.schema_id in source_rows_by_schema:
            status = TMPage43SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_ids = tuple(dict.fromkeys(source_rows_by_schema[item.schema_id]))
            reason = "page-43 fixed row/cell mapping passed with visible period/unit/scope"
        elif item.schema_id in ambiguous:
            status = TMPage43SchemaStatus.AMBIGUOUS_MAPPING.value
            source_ids = tuple(dict.fromkeys(ambiguous_rows_by_schema[item.schema_id]))
            reason = "visible personal-only label is compatible with but narrower than this item"
        elif item.schema_id in not_observed:
            status = TMPage43SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            source_ids = ()
            reason = "item belongs to the fully assessed page-43 branches but was not visible"
        else:
            status = TMPage43SchemaStatus.UNASSESSED.value
            source_ids = ()
            reason = "outside the page-43 schema branches assessed by this mapping"
        schema_dispositions.append(
            TMPage43SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status,
                source_row_ids=source_ids,
                reason=reason,
            )
        )
    assignment_keys = [
        (
            item.report_norm_id,
            item.period_end,
            item.measure_role,
            item.observation,
            item.value,
        )
        for item in assignments
    ]
    if len(assignment_keys) != len(set(assignment_keys)):
        raise TMPage43MappingError("TM page-43 mapped assignments are duplicated")
    mapped_source_slots = sum(
        bool(cell.report_norm_ids)
        for source in source_dispositions
        for cell in source.cell_dispositions
    )
    result = TMPage43MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=43,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="SCOPED_PAGE43_MULTI_AXIS_MAPPING_WITH_EXPLICIT_SOURCE_ONLY_MEASURES",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=len(source_rows_by_schema)
        + len(not_observed)
        + len(ambiguous),
        mapped_schema_count=len(source_rows_by_schema),
        not_observed_schema_count=len(not_observed),
        not_applicable_schema_count=0,
        ambiguous_schema_count=len(ambiguous),
        unassessed_schema_count=len(tm_schema)
        - len(source_rows_by_schema)
        - len(not_observed)
        - len(ambiguous),
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            bool(item.mapped_report_norm_ids) for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status
            in {
                TMPage43SourceStatus.SOURCE_ONLY_VALIDATION.value,
                TMPage43SourceStatus.SOURCE_ONLY_QUESTION.value,
            }
            for item in source_dispositions
        ),
        partially_mapped_source_row_count=sum(
            item.status == TMPage43SourceStatus.PARTIALLY_MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        source_question_row_count=sum(item.question_required for item in source_dispositions),
        ambiguous_source_row_count=sum(
            item.status == TMPage43SourceStatus.AMBIGUOUS_MAPPING.value
            for item in source_dispositions
        ),
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_source_slot_count=mapped_source_slots,
        mapped_value_assignment_count=sum(
            item.observation in {ObservationKind.VALUE.value, ObservationKind.ZERO.value}
            for item in assignments
        ),
        mapped_dash_assignment_count=sum(
            item.observation == ObservationKind.DASH.value for item in assignments
        ),
        mapped_status_assignment_count=len(assignments),
        accounting_check_count=len(accounting),
        accounting_pass_count=sum(check.status == "PASS" for check in accounting),
        accounting_not_testable_count=sum(
            check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in accounting
        ),
        duplicate_check_count=len(duplicates),
        duplicate_pass_count=sum(check.status == "PASS" for check in duplicates),
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        mapped_assignments=tuple(assignments),
        accounting_checks=accounting,
        duplicate_checks=duplicates,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        dash_pixel_evidence_sha256=_dash_evidence_hash(parsed),
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS",
            "VISIBLE_PAGE43_NOTE_ROW_COLUMN_AND_PERIOD_ORDER",
            "SOURCE_RENDER_SHA256",
            "CONSTRAINED_PIXEL_DASH_EVIDENCE_FOR_STATUS_ONLY",
            "TM_SCHEMA_ID_NAME_DISPLAY_ORDER",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
        ),
    )
    return validate_tm_page43_mapping_result(result)


def validate_tm_page43_mapping_result(
    result: TMPage43MappingResult,
) -> TMPage43MappingResult:
    if (
        result.schema_item_count != TM_PAGE43_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE43_RECONCILED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE43_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE43_NOT_OBSERVED_COUNT
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != TM_PAGE43_AMBIGUOUS_SCHEMA_COUNT
        or result.unassessed_schema_count != TM_PAGE43_UNASSESSED_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE43_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE43_MAPPED_SOURCE_COUNT
        or result.source_only_row_count != TM_PAGE43_SOURCE_ONLY_COUNT
        or result.partially_mapped_source_row_count != TM_PAGE43_PARTIAL_SOURCE_COUNT
        or result.source_question_row_count != 6
        or result.ambiguous_source_row_count != 0
        or result.financial_slot_count != TM_PAGE43_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE43_VALUE_COUNT
        or result.dash_count != TM_PAGE43_DASH_COUNT
        or result.mapped_source_slot_count != TM_PAGE43_MAPPED_SOURCE_SLOT_COUNT
        or result.mapped_value_assignment_count != TM_PAGE43_MAPPED_VALUE_ASSIGNMENT_COUNT
        or result.mapped_dash_assignment_count != TM_PAGE43_MAPPED_DASH_ASSIGNMENT_COUNT
        or result.mapped_status_assignment_count != TM_PAGE43_MAPPED_STATUS_ASSIGNMENT_COUNT
        or result.accounting_check_count != TM_PAGE43_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_PAGE43_ACCOUNTING_PASS_COUNT
        or result.accounting_not_testable_count != TM_PAGE43_ACCOUNTING_NOT_TESTABLE_COUNT
        or result.duplicate_check_count != TM_PAGE43_DUPLICATE_CHECK_COUNT
        or result.duplicate_pass_count != TM_PAGE43_DUPLICATE_CHECK_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage43MappingError("TM page-43 mapping result denominator drifted")
    if (
        result.mapped_schema_count
        + result.ambiguous_schema_count
        + result.not_observed_schema_count
        + result.unassessed_schema_count
        != result.schema_item_count
    ):
        raise TMPage43MappingError("TM page-43 schema statuses do not reconcile")
    if (
        result.mapped_source_row_count
        + result.ambiguous_source_row_count
        + result.source_only_row_count
        != result.source_row_count
    ):
        raise TMPage43MappingError("TM page-43 source-row statuses do not reconcile")
    mapped_ids = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage43SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    ambiguous_ids = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage43SchemaStatus.AMBIGUOUS_MAPPING.value
    }
    if mapped_ids != _MAPPED_IDS or ambiguous_ids != _AMBIGUOUS_IDS:
        raise TMPage43MappingError("TM page-43 mapped/ambiguous ReportNormIds drifted")
    reused_assignments: dict[tuple[str, int], list[TMPage43MappedAssignment]] = {}
    for assignment in result.mapped_assignments:
        if assignment.mapping_role != "DIRECT_VISIBLE_ROW_OR_MEASURE":
            reused_assignments.setdefault((assignment.row_id, assignment.cell_index), []).append(
                assignment
            )
    expected_reused = {
        ("page-0043:derivatives:row-0003", 0): (660, 661),
        ("page-0043:derivatives:row-0003", 1): (688, 689),
        ("page-0043:derivatives:row-0007", 0): (674, 675),
        ("page-0043:derivatives:row-0007", 1): (702, 703),
    }
    if {
        key: tuple(item.report_norm_id for item in value)
        for key, value in reused_assignments.items()
    } != expected_reused:
        raise TMPage43MappingError("TM page-43 intentional shared-cell projection drifted")
    for group in reused_assignments.values():
        if (
            tuple(item.mapping_role for item in group)
            != (
                "AGGREGATE_MEASURE_TOTAL_FROM_COMBINED_VISIBLE_ROW",
                "PRIMARY_ONLY_VISIBLE_CURRENCY_DERIVATIVE_CHILD",
            )
            or len({item.observation for item in group}) != 1
            or len({item.value for item in group}) != 1
            or len({item.period_end for item in group}) != 1
            or len({item.row_id for item in group}) != 1
            or len({item.cell_index for item in group}) != 1
        ):
            raise TMPage43MappingError("TM page-43 shared-cell provenance was not retained exactly")
    dash_cells = [
        cell
        for source in result.source_dispositions
        for cell in source.cell_dispositions
        if cell.observation == ObservationKind.DASH.value
    ]
    if len(dash_cells) != 6 or any(cell.visual_cell_evidence is None for cell in dash_cells):
        raise TMPage43MappingError("TM page-43 DASH status lost its pixel evidence")
    if any(cell.value is not None for cell in dash_cells):
        raise TMPage43MappingError("TM page-43 DASH was coerced to a numeric value")
    net_cells = [
        cell
        for source in result.source_dispositions
        if source.table_key == "DERIVATIVES" and source.row_kind == TMNoteRowKind.NUMERIC.value
        for cell in source.cell_dispositions
        if cell.measure_role == "NET_CARRYING"
    ]
    if len(net_cells) != 6 or any(
        cell.status != TMPage43CellStatus.SOURCE_ONLY_QUESTION.value
        or cell.report_norm_ids
        or not cell.question_required
        for cell in net_cells
    ):
        raise TMPage43MappingError("TM page-43 net measure escaped source-only abstention")
    return result


__all__ = [
    "TM_PAGE43_POLICY_RELATIVE_PATH",
    "TMPage43AccountingCheck",
    "TMPage43CellDisposition",
    "TMPage43CellStatus",
    "TMPage43DuplicateCheck",
    "TMPage43MappedAssignment",
    "TMPage43MappingError",
    "TMPage43MappingPolicy",
    "TMPage43MappingResult",
    "TMPage43SchemaDisposition",
    "TMPage43SchemaStatus",
    "TMPage43SourceDisposition",
    "TMPage43SourceStatus",
    "load_tm_page43_mapping_policy",
    "reconcile_tm_page43_items",
    "validate_tm_page43_mapping_result",
]
