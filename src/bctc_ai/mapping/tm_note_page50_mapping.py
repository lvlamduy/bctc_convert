"""Source-scoped ReportNormId reconciliation for MBB TM page 50."""

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
from bctc_ai.tables.tm_note_page50 import ParsedTMPage50

TM_PAGE50_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page50-v1.yaml")
TM_PAGE50_SCHEMA_TOTAL = 1_712
TM_PAGE50_RECONCILED_SCHEMA_COUNT = 23
TM_PAGE50_MAPPED_SCHEMA_COUNT = 19
TM_PAGE50_NOT_OBSERVED_COUNT = 4
TM_PAGE50_UNASSESSED_COUNT = 1_689
TM_PAGE50_SOURCE_ROW_COUNT = 23
TM_PAGE50_MAPPED_SOURCE_COUNT = 19
TM_PAGE50_SOURCE_ONLY_COUNT = 4
TM_PAGE50_SCHEMA_GAP_SOURCE_COUNT = 0
TM_PAGE50_QUESTION_SOURCE_COUNT = 0
TM_PAGE50_FINANCIAL_SLOT_COUNT = 38
TM_PAGE50_VALUE_COUNT = 37
TM_PAGE50_DASH_COUNT = 1
TM_PAGE50_MAPPED_VALUE_COUNT = 37
TM_PAGE50_NARRATIVE_RECORD_COUNT = 3
TM_PAGE50_NARRATIVE_QUANTITY_COUNT = 1
TM_PAGE50_VALIDATION_CHECK_COUNT = 10
TM_PAGE50_VALIDATION_PASS_COUNT = 9
TM_PAGE50_VALIDATION_NOT_TESTABLE_COUNT = 1

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TAX_IDS = tuple(range(5723, 5738))
_SCOPED_IDS = set(range(1247, 1255)) | set(_TAX_IDS)
_MAPPED_IDS = {1248, 1249, 1250, 1253, *_TAX_IDS}
_NOT_OBSERVED_IDS = {1247, 1251, 1252, 1254}
_EXPECTED_FIXED_ROW_IDS = {
    ("TAX_EXPENSE", 2): 5723,
    ("TAX_EXPENSE", 3): 5724,
    ("TAX_EXPENSE", 4): 5725,
    ("TAX_EXPENSE", 5): 5726,
    ("TAX_EXPENSE", 6): 5727,
    ("TAX_RECONCILIATION", 2): 5728,
    ("TAX_RECONCILIATION", 4): 5729,
    ("TAX_RECONCILIATION", 5): 5730,
    ("TAX_RECONCILIATION", 6): 5731,
    ("TAX_RECONCILIATION", 7): 5732,
    ("TAX_RECONCILIATION", 8): 5733,
    ("TAX_RECONCILIATION", 9): 5734,
    ("TAX_RECONCILIATION", 10): 5735,
    ("TAX_RECONCILIATION", 11): 5736,
    ("TAX_RECONCILIATION", 12): 5737,
    ("CASH_EQUIVALENTS", 2): 1249,
    ("CASH_EQUIVALENTS", 3): 1250,
    ("CASH_EQUIVALENTS", 4): 1253,
    ("CASH_EQUIVALENTS", 5): 1248,
}
_TAX_PARENT_BY_ID = {
    5723: 5727,
    5724: 5723,
    5725: 5727,
    5726: 5725,
    5727: 1142,
    5728: 5731,
    5729: 5731,
    5730: 5731,
    5731: 1142,
    5732: 5737,
    5733: 5737,
    5734: 5737,
    5735: 5737,
    5736: 5737,
    5737: 1142,
}
_TAX_LEVEL_BY_ID = {
    5723: 2,
    5724: 3,
    5725: 2,
    5726: 3,
    5727: 1,
    5728: 2,
    5729: 2,
    5730: 2,
    5731: 1,
    5732: 2,
    5733: 2,
    5734: 2,
    5735: 2,
    5736: 2,
    5737: 1,
}
_TAX_CHILDREN_BY_ID = {
    5723: (5724,),
    5724: (),
    5725: (5726,),
    5726: (),
    5727: (5723, 5725),
    5728: (),
    5729: (),
    5730: (),
    5731: (5728, 5729, 5730),
    5732: (),
    5733: (),
    5734: (),
    5735: (),
    5736: (),
    5737: (5732, 5733, 5734, 5735, 5736),
}
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
    "narrative_tax_rate_as_schema_value",
    "tax_row_as_preexisting_non_page50_schema_id",
    "schema_id_outside_page50_scope",
}


class TMPage50MappingError(ValueError):
    pass


class TMPage50RuleDisposition(StrEnum):
    FIXED = "FIXED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    SOURCE_ONLY_SCHEMA_GAP = "SOURCE_ONLY_SCHEMA_GAP"


class TMPage50SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage50SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    SOURCE_ONLY_SCHEMA_GAP = "SOURCE_ONLY_SCHEMA_GAP"


@dataclass(frozen=True)
class TMPage50RowRule:
    table_key: str
    ordinal: int
    visible_label_anchor: str | None
    expected_row_kind: str
    expected_observations: tuple[str, ...]
    disposition: TMPage50RuleDisposition
    report_norm_id: int | None
    question_required: bool

    @property
    def identity(self) -> tuple[str, int]:
        return self.table_key, self.ordinal


@dataclass(frozen=True)
class TMPage50MappingPolicy:
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
    scoped_schema_ids: tuple[int, ...]
    minimum_visible_label_similarity: float
    rows: tuple[TMPage50RowRule, ...]
    not_observed_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage50SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage50SourceDisposition:
    row_id: str
    table_key: str
    ordinal: int
    visible_label: str
    row_kind: str
    source_role: str
    status: str
    report_norm_id: int | None
    canonical_name: str | None
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
class TMPage50ValidationCheck:
    check_id: str
    axis_role: str
    status: str
    expected_value: Decimal | None
    observed_value: Decimal
    residual: Decimal | None
    reason: str


@dataclass(frozen=True)
class TMPage50MappingResult:
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
    source_only_schema_gap_count: int
    source_question_row_count: int
    ambiguous_source_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_value_count: int
    narrative_record_count: int
    narrative_quantity_count: int
    validation_check_count: int
    validation_pass_count: int
    validation_not_testable_count: int
    schema_dispositions: tuple[TMPage50SchemaDisposition, ...]
    source_dispositions: tuple[TMPage50SourceDisposition, ...]
    validation_checks: tuple[TMPage50ValidationCheck, ...]
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
        raise TMPage50MappingError(f"invalid positive TM page-50 field: {field}")
    return value


def _ids(payload: Any, field: str) -> tuple[int, ...]:
    if (
        not isinstance(payload, list)
        or not payload
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload)
    ):
        raise TMPage50MappingError(f"TM page-50 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMPage50MappingError(f"TM page-50 {field} contains duplicates")
    return result


def load_tm_page50_mapping_policy(path: Path) -> TMPage50MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage50MappingError(f"cannot load TM page-50 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE50_SCOPED_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 50
        or payload.get("page_tag") != "page-0050"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage50MappingError("TM page-50 mapping identity drifted")
    hashes = tuple(
        payload.get(field)
        for field in ("source_pdf_sha256", "source_render_sha256", "source_ocr_sha256")
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage50MappingError("TM page-50 mapping hashes are invalid")
    schema_total = _positive_int(payload, "schema_total")
    scoped = _ids(payload.get("scoped_schema_ids"), "scoped_schema_ids")
    not_observed = _ids(payload.get("not_observed_schema_ids"), "not_observed_schema_ids")
    if (
        schema_total != TM_PAGE50_SCHEMA_TOTAL
        or set(scoped) != _SCOPED_IDS
        or set(not_observed) != _NOT_OBSERVED_IDS
    ):
        raise TMPage50MappingError("TM page-50 exact schema scope drifted")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 <= threshold <= 1
    ):
        raise TMPage50MappingError("TM page-50 label threshold is invalid")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE50_SOURCE_ROW_COUNT:
        raise TMPage50MappingError("TM page-50 row rules are incomplete")
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage50MappingError("TM page-50 row rule is invalid")
        try:
            disposition = TMPage50RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMPage50MappingError("TM page-50 disposition is invalid") from exc
        observations = record.get("expected_observations")
        if (
            not isinstance(observations, list)
            or len(observations) != 2
            or any(value not in {"VALUE", "ZERO", "DASH", "BLANK"} for value in observations)
        ):
            raise TMPage50MappingError("TM page-50 observations are invalid")
        table_key = record.get("table_key")
        ordinal = record.get("ordinal")
        anchor = record.get("visible_label_anchor")
        row_kind = record.get("expected_row_kind")
        report_norm_id = record.get("report_norm_id")
        question = record.get("question_required")
        if (
            not isinstance(table_key, str)
            or not table_key
            or isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal <= 0
            or (anchor is not None and (not isinstance(anchor, str) or not anchor))
            or row_kind not in {"NUMERIC", "LABEL_ONLY"}
            or (report_norm_id is not None and not isinstance(report_norm_id, int))
            or not isinstance(question, bool)
        ):
            raise TMPage50MappingError("TM page-50 row rule fields are invalid")
        normalized_anchor = retrieval_key(anchor) if anchor is not None else None
        if disposition is TMPage50RuleDisposition.FIXED:
            if report_norm_id not in _MAPPED_IDS or question:
                raise TMPage50MappingError("TM page-50 fixed mapping rule drifted")
        elif report_norm_id is not None:
            raise TMPage50MappingError("TM page-50 source-only rule has a ReportNormId")
        if question:
            raise TMPage50MappingError("TM page-50 has no genuine ambiguity requiring user review")
        rows.append(
            TMPage50RowRule(
                table_key=table_key,
                ordinal=ordinal,
                visible_label_anchor=normalized_anchor,
                expected_row_kind=row_kind,
                expected_observations=tuple(str(value) for value in observations),
                disposition=disposition,
                report_norm_id=report_norm_id,
                question_required=question,
            )
        )
    if len({row.identity for row in rows}) != len(rows):
        raise TMPage50MappingError("TM page-50 row-rule identities are duplicated")
    fixed_id_sequence = tuple(
        row.report_norm_id for row in rows if row.disposition is TMPage50RuleDisposition.FIXED
    )
    fixed_ids = set(fixed_id_sequence)
    fixed_rows = {
        row.identity: row.report_norm_id
        for row in rows
        if row.disposition is TMPage50RuleDisposition.FIXED
    }
    if (
        len(fixed_id_sequence) != len(_MAPPED_IDS)
        or fixed_ids != _MAPPED_IDS
        or fixed_rows != _EXPECTED_FIXED_ROW_IDS
        or fixed_ids | set(not_observed) != set(scoped)
    ):
        raise TMPage50MappingError("TM page-50 schema partition drifted")
    if (
        sum(row.disposition is TMPage50RuleDisposition.SOURCE_ONLY_SCHEMA_GAP for row in rows)
        != TM_PAGE50_SCHEMA_GAP_SOURCE_COUNT
    ):
        raise TMPage50MappingError("TM page-50 schema-gap denominator drifted")
    if (
        sum(row.disposition is TMPage50RuleDisposition.SOURCE_ONLY_VALIDATION for row in rows)
        != TM_PAGE50_SOURCE_ONLY_COUNT
    ):
        raise TMPage50MappingError("TM page-50 structural source-only denominator drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage50MappingError("TM page-50 forbidden mapping inputs drifted")
    return TMPage50MappingPolicy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=50,
        page_tag="page-0050",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=str(payload.get("mapping_authority_scope", "")),
        source_pdf_sha256=str(hashes[0]),
        source_render_sha256=str(hashes[1]),
        source_ocr_sha256=str(hashes[2]),
        schema_total=schema_total,
        scoped_schema_ids=scoped,
        minimum_visible_label_similarity=float(threshold),
        rows=tuple(rows),
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
    payload = [(item.schema_id, item.display_order, item.canonical_name) for item in items]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validate_tax_schema_hierarchy(items: tuple[SchemaItem, ...]) -> None:
    ordered_ids = tuple(item.schema_id for item in items)
    insertion = ordered_ids.index(1246)
    if ordered_ids[insertion : insertion + len(_TAX_IDS) + 2] != (
        1246,
        *_TAX_IDS,
        1247,
    ):
        raise TMPage50MappingError("TM page-50 tax schema order/anchors drifted")
    by_id = {item.schema_id: item for item in items}
    if not {*_TAX_IDS, 1142} <= set(by_id):
        raise TMPage50MappingError("TM page-50 tax hierarchy items are absent")
    tax_items = tuple(by_id[schema_id] for schema_id in _TAX_IDS)
    hierarchy_is_attached = any(
        item.parent_id is not None or item.hierarchy_level is not None or item.children
        for item in tax_items
    )
    if not hierarchy_is_attached:
        return
    for schema_id in _TAX_IDS:
        item = by_id[schema_id]
        if (
            item.parent_id != _TAX_PARENT_BY_ID[schema_id]
            or item.hierarchy_level != _TAX_LEVEL_BY_ID[schema_id]
            or tuple(item.children) != _TAX_CHILDREN_BY_ID[schema_id]
        ):
            raise TMPage50MappingError(
                f"TM page-50 tax hierarchy drifted for ReportNormId {schema_id}"
            )
    if not {5727, 5731, 5737} <= set(by_id[1142].children):
        raise TMPage50MappingError("TM page-50 tax roots are not attached to ReportNormId 1142")


def _dash_evidence_hash(parsed: ParsedTMPage50) -> str:
    payload = [
        asdict(evidence)
        for row in parsed.rows
        for evidence in row.visual_cell_evidence
        if evidence is not None
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _row(parsed: ParsedTMPage50, table_key: str, ordinal: int):
    return next(row for row in parsed.rows if (row.table_key, row.ordinal) == (table_key, ordinal))


def _value(parsed: ParsedTMPage50, table_key: str, ordinal: int, axis: int) -> Decimal:
    value = _row(parsed, table_key, ordinal).row.cells[axis].value
    if value is None:
        raise TMPage50MappingError(f"TM page-50 expected a finite value: {table_key}/{ordinal}")
    return value


def _sum_check(
    *,
    check_id: str,
    axis_role: str,
    expected: Decimal,
    observed: Decimal,
    reason: str,
) -> TMPage50ValidationCheck:
    return TMPage50ValidationCheck(
        check_id=check_id,
        axis_role=axis_role,
        status="PASS" if expected == observed else "FAIL",
        expected_value=expected,
        observed_value=observed,
        residual=observed - expected,
        reason=reason,
    )


def _validation(parsed: ParsedTMPage50) -> tuple[TMPage50ValidationCheck, ...]:
    checks = []
    for axis, role in enumerate(("CURRENT", "COMPARATIVE")):
        checks.append(
            _sum_check(
                check_id=f"TAX_EXPENSE_SUM_{role}",
                axis_role=role,
                expected=_value(parsed, "TAX_EXPENSE", 2, axis)
                + _value(parsed, "TAX_EXPENSE", 4, axis),
                observed=_value(parsed, "TAX_EXPENSE", 6, axis),
                reason="visible current and deferred tax components sum to tax expense",
            )
        )
        checks.append(
            _sum_check(
                check_id=f"ESTIMATED_TAXABLE_INCOME_{role}",
                axis_role=role,
                expected=_value(parsed, "TAX_RECONCILIATION", 2, axis)
                + _value(parsed, "TAX_RECONCILIATION", 4, axis)
                + _value(parsed, "TAX_RECONCILIATION", 5, axis),
                observed=_value(parsed, "TAX_RECONCILIATION", 6, axis),
                reason="visible accounting profit and adjustments reconcile to taxable income",
            )
        )
        component_rows = tuple(
            _row(parsed, "TAX_RECONCILIATION", ordinal).row.cells[axis]
            for ordinal in (7, 8, 9, 10, 11)
        )
        tax_total = _value(parsed, "TAX_RECONCILIATION", 12, axis)
        if any(cell.observation is ObservationKind.DASH for cell in component_rows):
            checks.append(
                TMPage50ValidationCheck(
                    check_id=f"TAX_RECONCILIATION_SUM_{role}",
                    axis_role=role,
                    status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
                    expected_value=None,
                    observed_value=tax_total,
                    residual=None,
                    reason="visible DASH is unknown/not stated and is not coerced to zero",
                )
            )
        else:
            expected = sum(
                (cell.value for cell in component_rows if cell.value is not None), Decimal(0)
            )
            checks.append(
                _sum_check(
                    check_id=f"TAX_RECONCILIATION_SUM_{role}",
                    axis_role=role,
                    expected=expected,
                    observed=tax_total,
                    reason="five visible tax components sum to the printed tax expense",
                )
            )
        checks.append(
            _sum_check(
                check_id=f"CASH_EQUIVALENTS_SUM_{role}",
                axis_role=role,
                expected=sum(
                    (_value(parsed, "CASH_EQUIVALENTS", ordinal, axis) for ordinal in (2, 3, 4)),
                    Decimal(0),
                ),
                observed=_value(parsed, "CASH_EQUIVALENTS", 5, axis),
                reason="three visible cash-equivalent components sum to the unlabeled total",
            )
        )
        checks.append(
            _sum_check(
                check_id=f"CROSS_NOTE_TAX_TOTAL_{role}",
                axis_role=role,
                expected=_value(parsed, "TAX_EXPENSE", 6, axis),
                observed=_value(parsed, "TAX_RECONCILIATION", 12, axis),
                reason="the independently printed totals in notes 11.1 and 11.2 agree",
            )
        )
    return tuple(checks)


def reconcile_tm_page50_items(
    parsed: ParsedTMPage50,
    *,
    schema: list[SchemaItem],
    policy: TMPage50MappingPolicy,
    source_pdf_path: Path,
) -> TMPage50MappingResult:
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
    ):
        raise TMPage50MappingError("TM page-50 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage50MappingError("TM page-50 source PDF hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE50_SCHEMA_TOTAL:
        raise TMPage50MappingError("TM page-50 schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if not _SCOPED_IDS <= set(schema_by_id):
        raise TMPage50MappingError("TM page-50 scoped ReportNormIds are absent")
    _validate_tax_schema_hierarchy(tm_schema)
    parsed_by_identity = {(row.table_key, row.ordinal): row for row in parsed.rows}
    if tuple(parsed_by_identity) != tuple(rule.identity for rule in policy.rows):
        raise TMPage50MappingError("TM page-50 parsed row order drifted from policy")
    source_dispositions = []
    source_rows_by_schema: dict[int, list[str]] = {}
    for rule in policy.rows:
        row = parsed_by_identity[rule.identity]
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if (
            row.row_kind.value != rule.expected_row_kind
            or observations != rule.expected_observations
        ):
            raise TMPage50MappingError(f"TM page-50 row status drifted: {row.row_id}")
        if rule.visible_label_anchor is None:
            if row.row.label:
                raise TMPage50MappingError(f"TM page-50 expected unlabeled total: {row.row_id}")
            similarity = None
        else:
            similarity = _similarity(row.row.label, rule.visible_label_anchor)
            if similarity < policy.minimum_visible_label_similarity:
                raise TMPage50MappingError(f"TM page-50 label anchor failed: {row.row_id}")
        if rule.disposition is TMPage50RuleDisposition.FIXED:
            assert rule.report_norm_id is not None
            item = schema_by_id[rule.report_norm_id]
            status = TMPage50SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            canonical = item.canonical_name
            source_rows_by_schema.setdefault(item.schema_id, []).append(row.row_id)
            reason = "fixed page-50 note-11/12 hierarchy, row order and visible-label rule passed"
        elif rule.disposition is TMPage50RuleDisposition.SOURCE_ONLY_SCHEMA_GAP:
            status = TMPage50SourceStatus.SOURCE_ONLY_SCHEMA_GAP.value
            canonical = None
            reason = (
                "visible income-tax row retained with values and axes; active TM v2 has no "
                "corresponding schema item, so it is eligible for the next automatic ADD batch"
            )
        else:
            status = TMPage50SourceStatus.SOURCE_ONLY_VALIDATION.value
            canonical = None
            reason = "visible title/section row retained as provenance without schema export"
        source_dispositions.append(
            TMPage50SourceDisposition(
                row_id=row.row_id,
                table_key=row.table_key,
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
                visual_cell_evidence=row.visual_cell_evidence,
                question_required=rule.question_required,
                reason=reason,
            )
        )
    checks = _validation(parsed)
    if (
        len(checks) != TM_PAGE50_VALIDATION_CHECK_COUNT
        or sum(check.status == "PASS" for check in checks) != TM_PAGE50_VALIDATION_PASS_COUNT
        or sum(check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in checks)
        != TM_PAGE50_VALIDATION_NOT_TESTABLE_COUNT
        or any(check.status == "FAIL" for check in checks)
    ):
        raise TMPage50MappingError("TM page-50 accounting validation failed")
    not_observed = set(policy.not_observed_schema_ids)
    schema_dispositions = []
    for item in tm_schema:
        if item.schema_id in source_rows_by_schema:
            status = TMPage50SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_ids = tuple(source_rows_by_schema[item.schema_id])
            reason = "one fixed page-50 note-11/12 source row passed source-scoped mapping"
        elif item.schema_id in not_observed:
            status = TMPage50SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            source_ids = ()
            reason = "item belongs to the fully assessed page-50 scope but was not visible"
        else:
            status = TMPage50SchemaStatus.UNASSESSED.value
            source_ids = ()
            reason = "outside the exact page-50 schema scope"
        schema_dispositions.append(
            TMPage50SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status,
                source_row_ids=source_ids,
                reason=reason,
            )
        )
    result = TMPage50MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=50,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="SCOPED_PAGE50_TAX_AND_CASH_MAPPING_WITH_COMPLETE_ITEM_COVERAGE",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=len(_SCOPED_IDS),
        mapped_schema_count=len(source_rows_by_schema),
        not_observed_schema_count=len(not_observed),
        not_applicable_schema_count=0,
        ambiguous_schema_count=0,
        unassessed_schema_count=len(tm_schema) - len(_SCOPED_IDS),
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMPage50SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status
            in {
                TMPage50SourceStatus.SOURCE_ONLY_VALIDATION.value,
                TMPage50SourceStatus.SOURCE_ONLY_SCHEMA_GAP.value,
            }
            for item in source_dispositions
        ),
        source_only_schema_gap_count=sum(
            item.status == TMPage50SourceStatus.SOURCE_ONLY_SCHEMA_GAP.value
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
            if item.status == TMPage50SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for observation in item.observations
        ),
        narrative_record_count=len(parsed.narratives),
        narrative_quantity_count=parsed.narrative_quantity_count,
        validation_check_count=len(checks),
        validation_pass_count=sum(check.status == "PASS" for check in checks),
        validation_not_testable_count=sum(
            check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in checks
        ),
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        validation_checks=checks,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        dash_pixel_evidence_sha256=_dash_evidence_hash(parsed),
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS",
            "VISIBLE_PAGE50_NOTE_SECTION_AND_LOCAL_ROW_ORDER",
            "SOURCE_RENDER_SHA256",
            "CONSTRAINED_PIXEL_DASH_EVIDENCE_FOR_STATUS_ONLY",
            "VISIBLE_TABLE_LOCAL_PERIOD_UNIT_SCOPE_BINDING",
            "TM_SCHEMA_ID_NAME_ORDER",
            "AUTHORIZED_PAGE50_TAX_SCHEMA_HIERARCHY",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
            "NARRATIVE_TAX_RATE_AS_PROVENANCE_ONLY",
        ),
    )
    return validate_tm_page50_mapping_result(result)


def validate_tm_page50_mapping_result(result: TMPage50MappingResult) -> TMPage50MappingResult:
    if (
        result.schema_item_count != TM_PAGE50_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE50_RECONCILED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE50_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE50_NOT_OBSERVED_COUNT
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE50_UNASSESSED_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE50_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE50_MAPPED_SOURCE_COUNT
        or result.source_only_row_count != TM_PAGE50_SOURCE_ONLY_COUNT
        or result.source_only_schema_gap_count != TM_PAGE50_SCHEMA_GAP_SOURCE_COUNT
        or result.source_question_row_count != TM_PAGE50_QUESTION_SOURCE_COUNT
        or result.ambiguous_source_row_count != 0
        or result.financial_slot_count != TM_PAGE50_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE50_VALUE_COUNT
        or result.dash_count != TM_PAGE50_DASH_COUNT
        or result.mapped_value_count != TM_PAGE50_MAPPED_VALUE_COUNT
        or result.narrative_record_count != TM_PAGE50_NARRATIVE_RECORD_COUNT
        or result.narrative_quantity_count != TM_PAGE50_NARRATIVE_QUANTITY_COUNT
        or result.validation_check_count != TM_PAGE50_VALIDATION_CHECK_COUNT
        or result.validation_pass_count != TM_PAGE50_VALIDATION_PASS_COUNT
        or result.validation_not_testable_count != TM_PAGE50_VALIDATION_NOT_TESTABLE_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage50MappingError("TM page-50 mapping result denominator drifted")
    if (
        result.mapped_schema_count
        + result.not_observed_schema_count
        + result.unassessed_schema_count
        != result.schema_item_count
    ):
        raise TMPage50MappingError("TM page-50 schema statuses do not reconcile")
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMPage50SchemaStatus)
    }
    if (
        by_status[TMPage50SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] != _MAPPED_IDS
        or by_status[TMPage50SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] != _NOT_OBSERVED_IDS
    ):
        raise TMPage50MappingError("TM page-50 exact schema partition drifted")
    dash_rows = [
        item for item in result.source_dispositions if item.observations == ("DASH", "VALUE")
    ]
    if (
        len(dash_rows) != 1
        or dash_rows[0].status != TMPage50SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        or dash_rows[0].report_norm_id != 5734
        or dash_rows[0].values != (None, Decimal(1_854))
        or dash_rows[0].visual_cell_evidence[0] is None
        or dash_rows[0].visual_cell_evidence[1] is not None
    ):
        raise TMPage50MappingError("TM page-50 DASH evidence drifted")
    if any(item.question_required for item in result.source_dispositions):
        raise TMPage50MappingError("TM page-50 user-question partition drifted")
    return result


__all__ = [
    "TM_PAGE50_POLICY_RELATIVE_PATH",
    "TMPage50MappingError",
    "TMPage50MappingPolicy",
    "TMPage50MappingResult",
    "TMPage50SchemaDisposition",
    "TMPage50SchemaStatus",
    "TMPage50SourceDisposition",
    "TMPage50SourceStatus",
    "TMPage50ValidationCheck",
    "load_tm_page50_mapping_policy",
    "reconcile_tm_page50_items",
    "validate_tm_page50_mapping_result",
]
