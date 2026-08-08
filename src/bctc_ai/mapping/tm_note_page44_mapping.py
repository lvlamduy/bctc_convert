"""Source-scoped row/cell mapping and dash-safe validation for MBB TM page 44."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal
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
from bctc_ai.tables.tm_note_page44 import ParsedTMPage44
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind

TM_PAGE44_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page44-v1.yaml")
TM_PAGE44_SCHEMA_TOTAL = 1_613
TM_PAGE44_RECONCILED_SCHEMA_COUNT = 42
TM_PAGE44_MAPPED_SCHEMA_COUNT = 11
TM_PAGE44_AMBIGUOUS_SCHEMA_COUNT = 5
TM_PAGE44_UNRESOLVED_SCHEMA_COUNT = 10
TM_PAGE44_NOT_OBSERVED_COUNT = 16
TM_PAGE44_UNASSESSED_COUNT = 1_571
TM_PAGE44_SOURCE_ROW_COUNT = 24
TM_PAGE44_MAPPED_SOURCE_COUNT = 10
TM_PAGE44_PARTIAL_SOURCE_COUNT = 2
TM_PAGE44_SOURCE_ONLY_COUNT = 14
TM_PAGE44_SOURCE_QUESTION_COUNT = 13
TM_PAGE44_CONTEXT_SOURCE_COUNT = 3
TM_PAGE44_FINANCIAL_SLOT_COUNT = 60
TM_PAGE44_VALUE_COUNT = 51
TM_PAGE44_DASH_COUNT = 9
TM_PAGE44_MAPPED_VALUE_COUNT = 17
TM_PAGE44_NARRATIVE_FACT_COUNT = 5
TM_PAGE44_NARRATIVE_VALUE_COUNT = 7
TM_PAGE44_ACCOUNTING_CHECK_COUNT = 22
TM_PAGE44_ACCOUNTING_PASS_COUNT = 14
TM_PAGE44_ACCOUNTING_NOT_TESTABLE_COUNT = 8

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCOPED_IDS = set(range(1100, 1142))
_MAPPED_IDS = {1100, 1101, 1109, 1112, 1118, 1119, 1122, 1128, 1129, 1131, 1141}
_AMBIGUOUS_IDS = {1102, 1103, 1104, 1110, 1111}
_UNRESOLVED_IDS = {1130, *range(1132, 1141)}
_NOT_OBSERVED_IDS = {
    1105,
    1106,
    1107,
    1108,
    1113,
    1114,
    1115,
    1116,
    1117,
    1120,
    1121,
    1123,
    1124,
    1125,
    1126,
    1127,
}
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
}


class TMPage44MappingError(ValueError):
    pass


class TMPage44RuleDisposition(StrEnum):
    FIXED_ROW = "FIXED_ROW"
    FIXED_STRUCTURAL = "FIXED_STRUCTURAL"
    PARTIAL_FIXED_CELLS = "PARTIAL_FIXED_CELLS"
    SOURCE_ONLY_CONTEXT = "SOURCE_ONLY_CONTEXT"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"


class TMPage44SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    UNRESOLVED = "UNRESOLVED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage44SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    MAPPED_STRUCTURAL_SCOPED = "MAPPED_STRUCTURAL_SCOPED"
    PARTIAL_CELL_MAPPING = "PARTIAL_CELL_MAPPING"
    SOURCE_ONLY_CONTEXT = "SOURCE_ONLY_CONTEXT"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"


@dataclass(frozen=True)
class TMPage44FixedCellRule:
    cell_index: int
    report_norm_id: int


@dataclass(frozen=True)
class TMPage44RowRule:
    table_key: str
    ordinal: int
    visible_label_anchor: str | None
    expected_row_kind: str
    expected_observations: tuple[str, ...]
    disposition: TMPage44RuleDisposition
    report_norm_id: int | None
    fixed_cells: tuple[TMPage44FixedCellRule, ...]
    candidate_report_norm_ids: tuple[int, ...]
    question_group_id: str | None

    @property
    def identity(self) -> tuple[str, int]:
        return self.table_key, self.ordinal


@dataclass(frozen=True)
class TMPage44MappingPolicy:
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
    rows: tuple[TMPage44RowRule, ...]
    ambiguous_schema_ids: tuple[int, ...]
    unresolved_schema_ids: tuple[int, ...]
    not_observed_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage44CellAssignment:
    cell_index: int | None
    axis_role: str | None
    report_norm_id: int
    canonical_name: str
    observation: str | None
    value: Decimal | None


@dataclass(frozen=True)
class TMPage44SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_refs: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage44SourceDisposition:
    row_id: str
    table_key: str
    ordinal: int
    visible_label: str
    row_kind: str
    source_role: str
    status: str
    mapped_assignments: tuple[TMPage44CellAssignment, ...]
    candidate_report_norm_ids: tuple[int, ...]
    candidate_canonical_names: tuple[str, ...]
    visible_label_similarity: float | None
    observations: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    axis_roles: tuple[str, ...]
    period_starts: tuple[str, ...]
    period_ends: tuple[str, ...]
    period_types: tuple[str, ...]
    unit: str
    unit_multiplier: int
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    question_group_id: str | None
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage44AccountingCheck:
    check_id: str
    axis_role: str
    status: str
    expected_value: Decimal | None
    observed_value: Decimal
    residual: Decimal | None
    reason: str


@dataclass(frozen=True)
class TMPage44NarrativeDiagnostic:
    diagnostic_id: str
    question_group_id: str
    share_count: Decimal
    par_value_vnd: Decimal
    implied_capital_vnd_million: Decimal
    stated_capital_vnd_million: Decimal
    exact_residual_vnd_million: Decimal
    rounded_implied_capital_vnd_million: Decimal
    status: str
    reason: str


@dataclass(frozen=True)
class TMPage44MappingResult:
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
    narrative_fact_count: int
    narrative_value_count: int
    accounting_check_count: int
    accounting_pass_count: int
    accounting_not_testable_count: int
    accounting_fail_count: int
    question_group_ids: tuple[str, ...]
    schema_dispositions: tuple[TMPage44SchemaDisposition, ...]
    source_dispositions: tuple[TMPage44SourceDisposition, ...]
    accounting_checks: tuple[TMPage44AccountingCheck, ...]
    narrative_diagnostic: TMPage44NarrativeDiagnostic
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
        raise TMPage44MappingError(f"invalid positive TM page-44 field: {field}")
    return value


def _ids(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(payload, list)
        or (not payload and not allow_empty)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload)
    ):
        raise TMPage44MappingError(f"TM page-44 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMPage44MappingError(f"TM page-44 {field} contains duplicates")
    return result


def load_tm_page44_mapping_policy(path: Path) -> TMPage44MappingPolicy:
    """Load fixed row/cell mapping authority for page 44."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage44MappingError(f"cannot load TM page-44 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE44_SCOPED_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 44
        or payload.get("page_tag") != "page-0044"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage44MappingError("TM page-44 mapping policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage44MappingError("TM page-44 mapping source hashes are invalid")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 < float(threshold) <= 1
    ):
        raise TMPage44MappingError("TM page-44 mapping similarity threshold is invalid")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE44_SOURCE_ROW_COUNT:
        raise TMPage44MappingError("TM page-44 mapping row denominator drifted")
    valid_observations = {observation.value for observation in ObservationKind}
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage44MappingError("TM page-44 mapping row is invalid")
        try:
            disposition = TMPage44RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMPage44MappingError("TM page-44 rule disposition is invalid") from exc
        table_key = record.get("table_key")
        ordinal = record.get("ordinal")
        label = record.get("visible_label_anchor")
        row_kind = record.get("expected_row_kind")
        observations = record.get("expected_observations")
        report_norm_id = record.get("report_norm_id")
        question = record.get("question_group_id")
        candidates = _ids(
            record.get("candidate_report_norm_ids"), "candidate ReportNormIds", allow_empty=True
        )
        raw_cells = record.get("fixed_cells")
        if not isinstance(raw_cells, list):
            raise TMPage44MappingError("TM page-44 fixed-cell rules are invalid")
        fixed_cells = []
        for cell in raw_cells:
            if not isinstance(cell, dict):
                raise TMPage44MappingError("TM page-44 fixed-cell record is invalid")
            cell_index = cell.get("cell_index")
            cell_id = cell.get("report_norm_id")
            if (
                isinstance(cell_index, bool)
                or not isinstance(cell_index, int)
                or not 0 <= cell_index < 4
                or isinstance(cell_id, bool)
                or not isinstance(cell_id, int)
            ):
                raise TMPage44MappingError("TM page-44 fixed-cell identity is invalid")
            fixed_cells.append(TMPage44FixedCellRule(cell_index, cell_id))
        if (
            not isinstance(table_key, str)
            or not table_key
            or isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal <= 0
            or (label is not None and not isinstance(label, str))
            or row_kind not in {kind.value for kind in TMNoteRowKind}
            or not isinstance(observations, list)
            or len(observations) not in {2, 4}
            or any(value not in valid_observations for value in observations)
            or (question is not None and question not in {"Q050", "Q051"})
        ):
            raise TMPage44MappingError("TM page-44 mapping row identity is invalid")
        if disposition in {
            TMPage44RuleDisposition.FIXED_ROW,
            TMPage44RuleDisposition.FIXED_STRUCTURAL,
        }:
            if (
                isinstance(report_norm_id, bool)
                or not isinstance(report_norm_id, int)
                or fixed_cells
                or candidates
                or question is not None
            ):
                raise TMPage44MappingError("fixed TM page-44 row rule is malformed")
        elif disposition is TMPage44RuleDisposition.PARTIAL_FIXED_CELLS:
            if report_norm_id is not None or not fixed_cells or candidates or question != "Q051":
                raise TMPage44MappingError("partial TM page-44 row rule is malformed")
        elif report_norm_id is not None or fixed_cells:
            raise TMPage44MappingError("source-only TM page-44 row cannot select a fixed mapping")
        rows.append(
            TMPage44RowRule(
                table_key=table_key,
                ordinal=ordinal,
                visible_label_anchor=retrieval_key(label) if label is not None else None,
                expected_row_kind=row_kind,
                expected_observations=tuple(observations),
                disposition=disposition,
                report_norm_id=report_norm_id,
                fixed_cells=tuple(fixed_cells),
                candidate_report_norm_ids=candidates,
                question_group_id=question,
            )
        )
    if len({row.identity for row in rows}) != len(rows):
        raise TMPage44MappingError("TM page-44 rule identities are duplicated")
    fixed_ids = {rule.report_norm_id for rule in rows if rule.report_norm_id is not None} | {
        cell.report_norm_id for rule in rows for cell in rule.fixed_cells
    }
    if fixed_ids != _MAPPED_IDS or sum(len(rule.fixed_cells) for rule in rows) != 3:
        raise TMPage44MappingError("TM page-44 fixed ReportNormIds drifted")
    ambiguous = _ids(payload.get("ambiguous_schema_ids"), "ambiguous IDs")
    unresolved = _ids(payload.get("unresolved_schema_ids"), "unresolved IDs")
    not_observed = _ids(payload.get("not_observed_schema_ids"), "not-observed IDs")
    if (
        set(ambiguous) != _AMBIGUOUS_IDS
        or set(unresolved) != _UNRESOLVED_IDS
        or set(not_observed) != _NOT_OBSERVED_IDS
        or fixed_ids | set(ambiguous) | set(unresolved) | set(not_observed) != _SCOPED_IDS
    ):
        raise TMPage44MappingError("TM page-44 scoped schema statuses drifted")
    candidate_ids = {candidate for rule in rows for candidate in rule.candidate_report_norm_ids}
    if candidate_ids != _AMBIGUOUS_IDS:
        raise TMPage44MappingError("TM page-44 maturity candidates drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage44MappingError("TM page-44 forbidden mapping inputs drifted")
    document = payload.get("document")
    mapping_scope = payload.get("mapping_authority_scope")
    if not isinstance(document, str) or not isinstance(mapping_scope, str) or not mapping_scope:
        raise TMPage44MappingError("TM page-44 mapping scope is invalid")
    return TMPage44MappingPolicy(
        source_path=path,
        document=document,
        page_number=44,
        page_tag="page-0044",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=mapping_scope,
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        schema_total=_positive_int(payload, "schema_total"),
        minimum_visible_label_similarity=float(threshold),
        rows=tuple(rows),
        ambiguous_schema_ids=ambiguous,
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


def _dash_evidence_hash(parsed: ParsedTMPage44) -> str:
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


def _row(parsed: ParsedTMPage44, table_key: str, ordinal: int) -> Any:
    return next(row for row in parsed.rows if row.table_key == table_key and row.ordinal == ordinal)


def _numeric(parsed: ParsedTMPage44, table_key: str, ordinal: int, axis: int) -> Decimal:
    value = _row(parsed, table_key, ordinal).row.cells[axis].value
    if value is None:
        raise TMPage44MappingError("TM page-44 numeric validation received a non-value cell")
    return value


def _accounting_checks(parsed: ParsedTMPage44) -> tuple[TMPage44AccountingCheck, ...]:
    checks = []
    snapshot_equations = (
        ("BOND_TOTAL_EQUALS_VISIBLE_MATURITY_BUCKETS", "PAPER_ISSUANCE", (3, 4), 2),
        ("CERTIFICATE_TOTAL_EQUALS_VISIBLE_MATURITY_BUCKETS", "PAPER_ISSUANCE", (6, 7), 5),
        ("PAPER_TOTAL_EQUALS_BOND_PLUS_CERTIFICATE", "PAPER_ISSUANCE", (2, 5), 8),
        ("OTHER_PAYABLE_TOTAL_EQUALS_INTERNAL_PLUS_EXTERNAL", "OTHER_PAYABLES", (2, 3), 4),
    )
    for check_id, table_key, components, total in snapshot_equations:
        table = next(table for table in parsed.tables if table.table_key == table_key)
        for axis_index, axis in enumerate(table.axes):
            expected = sum(
                (_numeric(parsed, table_key, ordinal, axis_index) for ordinal in components),
                Decimal(0),
            )
            observed = _numeric(parsed, table_key, total, axis_index)
            residual = observed - expected
            checks.append(
                TMPage44AccountingCheck(
                    check_id=check_id,
                    axis_role=axis.semantic_role,
                    status="PASS" if residual == 0 else "FAIL",
                    expected_value=expected,
                    observed_value=observed,
                    residual=residual,
                    reason="visible finite values combined only as post-mapping validation",
                )
            )
    equity = next(table for table in parsed.tables if table.table_key == "EQUITY_MOVEMENT")
    for row in equity.rows[2:]:
        begin, increase, decrease, ending = row.row.cells
        if any(cell.observation is ObservationKind.DASH for cell in (increase, decrease)):
            checks.append(
                TMPage44AccountingCheck(
                    check_id=f"EQUITY_ROW_ROLLFORWARD_{row.ordinal:04d}",
                    axis_role="ROW_ROLLFORWARD",
                    status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
                    expected_value=None,
                    observed_value=ending.value,
                    residual=None,
                    reason="visible DASH is an observation status and cannot be coerced to zero",
                )
            )
        else:
            if any(cell.value is None for cell in (begin, increase, decrease, ending)):
                raise TMPage44MappingError("TM page-44 equity rollforward value drifted")
            expected = begin.value + increase.value + decrease.value
            residual = ending.value - expected
            checks.append(
                TMPage44AccountingCheck(
                    check_id=f"EQUITY_ROW_ROLLFORWARD_{row.ordinal:04d}",
                    axis_role="ROW_ROLLFORWARD",
                    status="PASS" if residual == 0 else "FAIL",
                    expected_value=expected,
                    observed_value=ending.value,
                    residual=residual,
                    reason="visible finite values combined only as post-mapping validation",
                )
            )
    total = equity.rows[-1]
    components = equity.rows[2:-1]
    for axis_index, axis in enumerate(equity.axes):
        cells = [row.row.cells[axis_index] for row in components]
        observed = total.row.cells[axis_index].value
        if observed is None:
            raise TMPage44MappingError("TM page-44 equity column total drifted")
        if any(cell.observation is ObservationKind.DASH for cell in cells):
            checks.append(
                TMPage44AccountingCheck(
                    check_id=f"EQUITY_COLUMN_TOTAL_{axis.semantic_role}",
                    axis_role=axis.semantic_role,
                    status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
                    expected_value=None,
                    observed_value=observed,
                    residual=None,
                    reason="visible DASH components cannot be coerced to zero for a column sum",
                )
            )
        else:
            if any(cell.value is None for cell in cells):
                raise TMPage44MappingError("TM page-44 equity column component drifted")
            expected = sum((cell.value for cell in cells), Decimal(0))
            residual = observed - expected
            checks.append(
                TMPage44AccountingCheck(
                    check_id=f"EQUITY_COLUMN_TOTAL_{axis.semantic_role}",
                    axis_role=axis.semantic_role,
                    status="PASS" if residual == 0 else "FAIL",
                    expected_value=expected,
                    observed_value=observed,
                    residual=residual,
                    reason="visible finite values combined only as post-mapping validation",
                )
            )
    return tuple(checks)


def _narrative_diagnostic(parsed: ParsedTMPage44) -> TMPage44NarrativeDiagnostic:
    facts = {fact.fact_id: fact for fact in parsed.narrative_facts}
    share_count = facts["ISSUED_SHARE_COUNT"].values[0]
    par_value = facts["PAR_VALUE"].values[0]
    stated = facts["STATED_CHARTER_CAPITAL"].values[0]
    implied = share_count * par_value / Decimal(1_000_000)
    rounded = implied.quantize(Decimal(1), rounding=ROUND_HALF_UP)
    residual = stated - implied
    status = "PASS_ROUNDED_TO_NEAREST_MILLION" if rounded == stated else "FAIL"
    return TMPage44NarrativeDiagnostic(
        diagnostic_id="ISSUED_SHARES_TIMES_PAR_EQUALS_STATED_CAPITAL_AFTER_ROUNDING",
        question_group_id="Q052",
        share_count=share_count,
        par_value_vnd=par_value,
        implied_capital_vnd_million=implied,
        stated_capital_vnd_million=stated,
        exact_residual_vnd_million=residual,
        rounded_implied_capital_vnd_million=rounded,
        status=status,
        reason="three visible narrative facts retained source-only; diagnostic does not map schema",
    )


def _source_reason(rule: TMPage44RowRule) -> str:
    if rule.disposition is TMPage44RuleDisposition.SOURCE_ONLY_CONTEXT:
        return "visible section/note title retained as source context without duplicate mapping"
    if rule.question_group_id == "Q050":
        return "visible maturity bucket boundaries do not align one-to-one with schema buckets"
    if rule.disposition is TMPage44RuleDisposition.PARTIAL_FIXED_CELLS:
        return (
            "only cells with exact row-axis semantics are mapped; orthogonal grid cells remain open"
        )
    return "equity component-by-movement grid is orthogonal to schema movement-category rows"


def reconcile_tm_page44_items(
    parsed: ParsedTMPage44,
    *,
    schema: list[SchemaItem],
    policy: TMPage44MappingPolicy,
    source_pdf_path: Path,
) -> TMPage44MappingResult:
    """Reconcile scoped IDs 1100-1141 using only visible row/cell semantics."""

    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
    ):
        raise TMPage44MappingError("TM page-44 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage44MappingError("TM page-44 source PDF hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE44_SCHEMA_TOTAL:
        raise TMPage44MappingError("TM schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    referenced = (
        {rule.report_norm_id for rule in policy.rows if rule.report_norm_id is not None}
        | {cell.report_norm_id for rule in policy.rows for cell in rule.fixed_cells}
        | {candidate for rule in policy.rows for candidate in rule.candidate_report_norm_ids}
        | set(policy.ambiguous_schema_ids)
        | set(policy.unresolved_schema_ids)
        | set(policy.not_observed_schema_ids)
    )
    if not referenced <= set(schema_by_id):
        raise TMPage44MappingError("TM page-44 policy references unknown ReportNormIds")
    parsed_by_identity = {(row.table_key, row.ordinal): row for row in parsed.rows}
    if tuple(parsed_by_identity) != tuple(rule.identity for rule in policy.rows):
        raise TMPage44MappingError("TM page-44 parsed row order drifted from policy")
    source_dispositions = []
    source_refs_by_schema: dict[int, list[str]] = {}
    ambiguous_refs: dict[int, list[str]] = {item: [] for item in policy.ambiguous_schema_ids}
    for rule in policy.rows:
        row = parsed_by_identity[rule.identity]
        table = next(table for table in parsed.tables if table.table_key == row.table_key)
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if (
            row.row_kind.value != rule.expected_row_kind
            or observations != rule.expected_observations
        ):
            raise TMPage44MappingError(f"TM page-44 row status drifted: {row.row_id}")
        if rule.visible_label_anchor is None:
            if row.row.label:
                raise TMPage44MappingError(f"TM page-44 expected unlabeled total: {row.row_id}")
            similarity = None
        else:
            similarity = _similarity(row.row.label, rule.visible_label_anchor)
            if similarity < policy.minimum_visible_label_similarity:
                raise TMPage44MappingError(f"TM page-44 label anchor failed: {row.row_id}")
        assignments = []
        if rule.disposition in {
            TMPage44RuleDisposition.FIXED_ROW,
            TMPage44RuleDisposition.FIXED_STRUCTURAL,
        }:
            assert rule.report_norm_id is not None
            item = schema_by_id[rule.report_norm_id]
            if rule.disposition is TMPage44RuleDisposition.FIXED_STRUCTURAL:
                assignments.append(
                    TMPage44CellAssignment(
                        cell_index=None,
                        axis_role=None,
                        report_norm_id=item.schema_id,
                        canonical_name=item.canonical_name,
                        observation=None,
                        value=None,
                    )
                )
                source_refs_by_schema.setdefault(item.schema_id, []).append(row.row_id)
                status = TMPage44SourceStatus.MAPPED_STRUCTURAL_SCOPED.value
            else:
                for cell_index, (cell, axis) in enumerate(
                    zip(row.row.cells, table.axes, strict=True)
                ):
                    if cell.observation not in {ObservationKind.VALUE, ObservationKind.ZERO}:
                        raise TMPage44MappingError("fixed page-44 row contains a non-value cell")
                    assignments.append(
                        TMPage44CellAssignment(
                            cell_index=cell_index,
                            axis_role=axis.semantic_role,
                            report_norm_id=item.schema_id,
                            canonical_name=item.canonical_name,
                            observation=cell.observation.value,
                            value=cell.value,
                        )
                    )
                    source_refs_by_schema.setdefault(item.schema_id, []).append(
                        f"{row.row_id}:cell-{cell_index + 1:04d}"
                    )
                status = TMPage44SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            reason = "fixed visible page-44 hierarchy, row label/order, and axis binding passed"
        elif rule.disposition is TMPage44RuleDisposition.PARTIAL_FIXED_CELLS:
            for fixed in rule.fixed_cells:
                cell = row.row.cells[fixed.cell_index]
                axis = table.axes[fixed.cell_index]
                if cell.observation not in {ObservationKind.VALUE, ObservationKind.ZERO}:
                    raise TMPage44MappingError("partial page-44 mapping selected a non-value cell")
                item = schema_by_id[fixed.report_norm_id]
                assignments.append(
                    TMPage44CellAssignment(
                        cell_index=fixed.cell_index,
                        axis_role=axis.semantic_role,
                        report_norm_id=item.schema_id,
                        canonical_name=item.canonical_name,
                        observation=cell.observation.value,
                        value=cell.value,
                    )
                )
                source_refs_by_schema.setdefault(item.schema_id, []).append(
                    f"{row.row_id}:cell-{fixed.cell_index + 1:04d}"
                )
            status = TMPage44SourceStatus.PARTIAL_CELL_MAPPING.value
            reason = _source_reason(rule)
        elif rule.disposition is TMPage44RuleDisposition.SOURCE_ONLY_CONTEXT:
            status = TMPage44SourceStatus.SOURCE_ONLY_CONTEXT.value
            reason = _source_reason(rule)
        else:
            status = TMPage44SourceStatus.SOURCE_ONLY_QUESTION.value
            reason = _source_reason(rule)
        for candidate in rule.candidate_report_norm_ids:
            ambiguous_refs[candidate].append(row.row_id)
        source_dispositions.append(
            TMPage44SourceDisposition(
                row_id=row.row_id,
                table_key=row.table_key,
                ordinal=row.ordinal,
                visible_label=row.row.label,
                row_kind=row.row_kind.value,
                source_role=row.source_role,
                status=status,
                mapped_assignments=tuple(assignments),
                candidate_report_norm_ids=rule.candidate_report_norm_ids,
                candidate_canonical_names=tuple(
                    schema_by_id[candidate].canonical_name
                    for candidate in rule.candidate_report_norm_ids
                ),
                visible_label_similarity=similarity,
                observations=observations,
                values=tuple(cell.value for cell in row.row.cells),
                axis_roles=tuple(axis.semantic_role for axis in table.axes),
                period_starts=tuple(axis.period_start.isoformat() for axis in table.axes),
                period_ends=tuple(axis.period_end.isoformat() for axis in table.axes),
                period_types=tuple(axis.period_type for axis in table.axes),
                unit=table.axes[0].canonical_unit,
                unit_multiplier=table.axes[0].unit_multiplier,
                visual_cell_evidence=row.visual_cell_evidence,
                question_group_id=rule.question_group_id,
                question_required=rule.question_group_id is not None,
                reason=reason,
            )
        )
    checks = _accounting_checks(parsed)
    if (
        len(checks) != TM_PAGE44_ACCOUNTING_CHECK_COUNT
        or sum(check.status == "PASS" for check in checks) != TM_PAGE44_ACCOUNTING_PASS_COUNT
        or sum(check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in checks)
        != TM_PAGE44_ACCOUNTING_NOT_TESTABLE_COUNT
        or any(check.status == "FAIL" for check in checks)
    ):
        raise TMPage44MappingError("TM page-44 accounting validation drifted")
    diagnostic = _narrative_diagnostic(parsed)
    if diagnostic.status != "PASS_ROUNDED_TO_NEAREST_MILLION":
        raise TMPage44MappingError("TM page-44 narrative capital diagnostic failed")
    unresolved_refs = tuple(
        row.row_id for row in parsed.rows if row.table_key == "EQUITY_MOVEMENT" and row.ordinal >= 3
    )
    schema_dispositions = []
    ambiguous = set(policy.ambiguous_schema_ids)
    unresolved = set(policy.unresolved_schema_ids)
    not_observed = set(policy.not_observed_schema_ids)
    for item in tm_schema:
        if item.schema_id in source_refs_by_schema:
            status = TMPage44SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_refs = tuple(source_refs_by_schema[item.schema_id])
            reason = "one source-scoped page-44 row or cell passed fixed mapping authority"
        elif item.schema_id in ambiguous:
            status = TMPage44SchemaStatus.AMBIGUOUS_MAPPING.value
            source_refs = tuple(ambiguous_refs[item.schema_id])
            reason = "visible maturity boundary is compatible with multiple schema buckets"
        elif item.schema_id in unresolved:
            status = TMPage44SchemaStatus.UNRESOLVED.value
            source_refs = unresolved_refs
            reason = (
                "visible component-by-movement grid does not expose this movement category total"
            )
        elif item.schema_id in not_observed:
            status = TMPage44SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            source_refs = ()
            reason = "item belongs to fully assessed IDs 1100-1141 but was not visible"
        else:
            status = TMPage44SchemaStatus.UNASSESSED.value
            source_refs = ()
            reason = "outside the page-44 branch assessed by this mapping"
        schema_dispositions.append(
            TMPage44SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status,
                source_refs=source_refs,
                reason=reason,
            )
        )
    mapped_values = sum(
        assignment.value is not None
        for source in source_dispositions
        for assignment in source.mapped_assignments
    )
    mapped_source_statuses = {
        TMPage44SourceStatus.MAPPED_AUTOMATIC_SCOPED.value,
        TMPage44SourceStatus.MAPPED_STRUCTURAL_SCOPED.value,
        TMPage44SourceStatus.PARTIAL_CELL_MAPPING.value,
    }
    result = TMPage44MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=44,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="SCOPED_PAGE44_ROW_CELL_MAPPING_WITH_OPEN_BUCKET_AND_GRID_QUESTIONS",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=(
            len(source_refs_by_schema) + len(ambiguous) + len(unresolved) + len(not_observed)
        ),
        mapped_schema_count=len(source_refs_by_schema),
        ambiguous_schema_count=len(ambiguous),
        unresolved_schema_count=len(unresolved),
        not_observed_schema_count=len(not_observed),
        not_applicable_schema_count=0,
        unassessed_schema_count=(
            len(tm_schema)
            - len(source_refs_by_schema)
            - len(ambiguous)
            - len(unresolved)
            - len(not_observed)
        ),
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            source.status in mapped_source_statuses for source in source_dispositions
        ),
        partial_source_row_count=sum(
            source.status == TMPage44SourceStatus.PARTIAL_CELL_MAPPING.value
            for source in source_dispositions
        ),
        source_only_row_count=sum(
            source.status not in mapped_source_statuses for source in source_dispositions
        ),
        source_question_row_count=sum(source.question_required for source in source_dispositions),
        context_source_row_count=sum(
            source.status == TMPage44SourceStatus.SOURCE_ONLY_CONTEXT.value
            for source in source_dispositions
        ),
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_value_count=mapped_values,
        narrative_fact_count=len(parsed.narrative_facts),
        narrative_value_count=parsed.narrative_value_count,
        accounting_check_count=len(checks),
        accounting_pass_count=sum(check.status == "PASS" for check in checks),
        accounting_not_testable_count=sum(
            check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in checks
        ),
        accounting_fail_count=sum(check.status == "FAIL" for check in checks),
        question_group_ids=("Q050", "Q051", "Q052"),
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        accounting_checks=checks,
        narrative_diagnostic=diagnostic,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        dash_pixel_evidence_sha256=_dash_evidence_hash(parsed),
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS",
            "VISIBLE_PAGE44_NOTE_ROW_AND_CELL_AXES",
            "SOURCE_RENDER_SHA256",
            "CONSTRAINED_PIXEL_DASH_EVIDENCE_FOR_STATUS_ONLY",
            "TM_SCHEMA_ID_NAME_ORDER",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
            "NARRATIVE_FACTS_AS_SOURCE_ONLY_PROVENANCE",
        ),
    )
    return validate_tm_page44_mapping_result(result)


def validate_tm_page44_mapping_result(
    result: TMPage44MappingResult,
) -> TMPage44MappingResult:
    """Fail closed if any page-44 coverage or observation denominator drifts."""

    if (
        result.schema_item_count != TM_PAGE44_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE44_RECONCILED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE44_MAPPED_SCHEMA_COUNT
        or result.ambiguous_schema_count != TM_PAGE44_AMBIGUOUS_SCHEMA_COUNT
        or result.unresolved_schema_count != TM_PAGE44_UNRESOLVED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE44_NOT_OBSERVED_COUNT
        or result.not_applicable_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE44_UNASSESSED_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE44_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE44_MAPPED_SOURCE_COUNT
        or result.partial_source_row_count != TM_PAGE44_PARTIAL_SOURCE_COUNT
        or result.source_only_row_count != TM_PAGE44_SOURCE_ONLY_COUNT
        or result.source_question_row_count != TM_PAGE44_SOURCE_QUESTION_COUNT
        or result.context_source_row_count != TM_PAGE44_CONTEXT_SOURCE_COUNT
        or result.financial_slot_count != TM_PAGE44_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE44_VALUE_COUNT
        or result.dash_count != TM_PAGE44_DASH_COUNT
        or result.mapped_value_count != TM_PAGE44_MAPPED_VALUE_COUNT
        or result.narrative_fact_count != TM_PAGE44_NARRATIVE_FACT_COUNT
        or result.narrative_value_count != TM_PAGE44_NARRATIVE_VALUE_COUNT
        or result.accounting_check_count != TM_PAGE44_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_PAGE44_ACCOUNTING_PASS_COUNT
        or result.accounting_not_testable_count != TM_PAGE44_ACCOUNTING_NOT_TESTABLE_COUNT
        or result.accounting_fail_count != 0
        or result.question_group_ids != ("Q050", "Q051", "Q052")
        or not result.mapping_authority_granted
    ):
        raise TMPage44MappingError("TM page-44 mapping result denominator drifted")
    if (
        result.mapped_schema_count
        + result.ambiguous_schema_count
        + result.unresolved_schema_count
        + result.not_observed_schema_count
        + result.unassessed_schema_count
        != result.schema_item_count
    ):
        raise TMPage44MappingError("TM page-44 schema statuses do not reconcile")
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage44SchemaStatus}
    }
    if (
        by_status[TMPage44SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] != _MAPPED_IDS
        or by_status[TMPage44SchemaStatus.AMBIGUOUS_MAPPING.value] != _AMBIGUOUS_IDS
        or by_status[TMPage44SchemaStatus.UNRESOLVED.value] != _UNRESOLVED_IDS
        or by_status[TMPage44SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] != _NOT_OBSERVED_IDS
    ):
        raise TMPage44MappingError("TM page-44 exact schema status sets drifted")
    dash_cells = [
        evidence
        for source in result.source_dispositions
        for observation, evidence in zip(
            source.observations, source.visual_cell_evidence, strict=True
        )
        if observation == ObservationKind.DASH.value
    ]
    if len(dash_cells) != TM_PAGE44_DASH_COUNT or any(item is None for item in dash_cells):
        raise TMPage44MappingError("TM page-44 DASH status lost pixel evidence")
    return result


__all__ = [
    "TM_PAGE44_POLICY_RELATIVE_PATH",
    "TMPage44AccountingCheck",
    "TMPage44MappingError",
    "TMPage44MappingPolicy",
    "TMPage44MappingResult",
    "TMPage44NarrativeDiagnostic",
    "TMPage44SchemaDisposition",
    "TMPage44SchemaStatus",
    "TMPage44SourceDisposition",
    "TMPage44SourceStatus",
    "load_tm_page44_mapping_policy",
    "reconcile_tm_page44_items",
    "validate_tm_page44_mapping_result",
]
