"""Amount-axis-only ReportNormId mapping for MBB TM loan analyses on pages 32-33."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.schema.registry import SchemaItem
from bctc_ai.tables.tm_note_pages32_33 import (
    ParsedTMNotePages3233,
    TMLoanAnalysisLogicalRow,
)
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind

TM_NOTE_PAGES3233_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-pages32-33-v1.yaml")
TM_NOTE_PAGES3233_SCHEMA_TOTAL = 1_713
TM_NOTE_PAGES3233_RECONCILED_COUNT = 48
TM_NOTE_PAGES3233_MAPPED_SCHEMA_COUNT = 36
TM_NOTE_PAGES3233_AMBIGUOUS_SCHEMA_COUNT = 0
TM_NOTE_PAGES3233_NOT_OBSERVED_COUNT = 12
TM_NOTE_PAGES3233_UNASSESSED_COUNT = 1_665
TM_NOTE_PAGES3233_SOURCE_ROW_COUNT = 46
TM_NOTE_PAGES3233_MAPPED_SOURCE_COUNT = 37
TM_NOTE_PAGES3233_AMBIGUOUS_SOURCE_COUNT = 0
TM_NOTE_PAGES3233_SOURCE_ONLY_COUNT = 9
TM_NOTE_PAGES3233_PARTIAL_SOURCE_COUNT = 35
TM_NOTE_PAGES3233_SLOT_COUNT = 176
TM_NOTE_PAGES3233_VALUE_COUNT = 174
TM_NOTE_PAGES3233_ZERO_COUNT = 2
TM_NOTE_PAGES3233_MAPPED_SLOT_COUNT = 70
TM_NOTE_PAGES3233_AMBIGUOUS_SLOT_COUNT = 0
TM_NOTE_PAGES3233_SOURCE_ONLY_SLOT_COUNT = 106
TM_NOTE_PAGES3233_ASSIGNMENT_COUNT = 68
TM_NOTE_PAGES3233_PERCENTAGE_CHECK_COUNT = 88
TM_NOTE_PAGES3233_HIERARCHY_CHECK_COUNT = 36
TM_NOTE_PAGES3233_DUPLICATE_CHECK_COUNT = 16

_SCOPED_IDS = (
    set(range(727, 746))
    | set(range(756, 759))
    | set(range(766, 783))
    | set(range(5719, 5723))
    | {5748, 5749, 6058, 6059, 6060}
)
_MAPPED_IDS = {
    727,
    728,
    729,
    730,
    731,
    732,
    733,
    734,
    735,
    736,
    737,
    738,
    740,
    741,
    742,
    743,
    766,
    767,
    769,
    770,
    771,
    772,
    773,
    776,
    778,
    779,
    780,
    781,
    782,
    5719,
    5720,
    5721,
    5722,
    5748,
    5749,
    6058,
}
_AMBIGUOUS_IDS: set[int] = set()
_NOT_OBSERVED_IDS = {
    739,
    744,
    745,
    756,
    757,
    758,
    768,
    774,
    775,
    777,
    6059,
    6060,
}
_SCHEMA_SCOPE_SHA256 = "ca7bb0e111ba1e832a133c11458f47fc2f536b47b2523320ea430ccde6de317d"
_QUESTION_KEYS: set[str] = set()
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "percentage_axis_as_report_norm_mapping",
    "historical_or_mongodb_values",
    "human_review_answers",
    "accounting_equation_result_as_item_selector",
}


class TMNotePages3233MappingError(ValueError):
    pass


class TMNotePages3233RuleDisposition(StrEnum):
    FIXED_STRUCTURAL = "FIXED_STRUCTURAL"
    FIXED_AMOUNT_AXES = "FIXED_AMOUNT_AXES"
    FIXED_CATCH_ALL_COMPONENT = "FIXED_CATCH_ALL_COMPONENT"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    SOURCE_ONLY_SUBTOTAL = "SOURCE_ONLY_SUBTOTAL"
    SOURCE_ONLY_FOREIGN_BRANCH = "SOURCE_ONLY_FOREIGN_BRANCH"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


class TMNotePages3233SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMNotePages3233SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    SOURCE_ONLY_SUBTOTAL = "SOURCE_ONLY_SUBTOTAL"
    SOURCE_ONLY_FOREIGN_BRANCH = "SOURCE_ONLY_FOREIGN_BRANCH"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


class TMNotePages3233CellStatus(StrEnum):
    MAPPED_AMOUNT = "MAPPED_AMOUNT"
    SOURCE_ONLY_PERCENTAGE = "SOURCE_ONLY_PERCENTAGE"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    SOURCE_ONLY_SUBTOTAL = "SOURCE_ONLY_SUBTOTAL"
    SOURCE_ONLY_FOREIGN_BRANCH = "SOURCE_ONLY_FOREIGN_BRANCH"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


@dataclass(frozen=True)
class TMNotePages3233SourceRule:
    page_tag: str
    row_key: str
    disposition: TMNotePages3233RuleDisposition
    report_norm_ids: tuple[int, ...]
    candidate_report_norm_ids: tuple[int, ...]
    question_key: str | None


@dataclass(frozen=True)
class TMNotePages3233MappingPolicy:
    source_path: Path
    document: str
    scope: str
    source_table_policy: str
    mapping_authority_scope: str
    schema_total: int
    scope_schema_ids: tuple[int, ...]
    schema_scope_sha256: str
    fixed_mapped_ids: tuple[int, ...]
    ambiguous_ids: tuple[int, ...]
    not_observed_ids: tuple[int, ...]
    source_rules: tuple[TMNotePages3233SourceRule, ...]
    question_groups: tuple[str, ...]
    forbidden_mapping_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMNotePages3233SchemaDisposition:
    report_norm_id: int
    canonical_name: str
    status: str
    reason: str


@dataclass(frozen=True)
class TMNotePages3233SourceDisposition:
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
class TMNotePages3233CellDisposition:
    row_id: str
    page_tag: str
    row_key: str
    cell_index: int
    measure_role: str
    period_role: str
    observation: str
    value: Decimal | None
    status: str
    report_norm_id: int | None
    candidate_report_norm_ids: tuple[int, ...]
    reason: str


@dataclass(frozen=True)
class TMNotePages3233MappedAssignment:
    report_norm_id: int
    canonical_name: str
    row_id: str
    page_tag: str
    row_key: str
    cell_index: int
    measure_role: str
    observation: str
    value: Decimal
    period_role: str
    period_end: str
    period_type: str
    unit: str
    unit_multiplier: int
    scope: str
    source_row_ids: tuple[str, ...]
    source_bbox: tuple[float, float, float, float]
    mapping_basis: str


@dataclass(frozen=True)
class TMNotePages3233PercentageCheck:
    check_id: str
    page_tag: str
    row_key: str
    period_role: str
    amount: Decimal
    denominator: Decimal
    reported_percentage: Decimal
    calculated_percentage: Decimal
    absolute_delta: Decimal
    status: str


@dataclass(frozen=True)
class TMNotePages3233HierarchyCheck:
    check_id: str
    page_tag: str
    target_row_key: str
    cell_index: int
    measure_role: str
    period_role: str
    expected: Decimal
    observed: Decimal
    residual: Decimal
    status: str


@dataclass(frozen=True)
class TMNotePages3233CatchAllCheck:
    check_id: str
    report_norm_id: int
    period_role: str
    component_row_keys: tuple[str, ...]
    component_values: tuple[Decimal, ...]
    aggregated_value: Decimal
    status: str


@dataclass(frozen=True)
class TMNotePages3233DuplicateCheck:
    check_id: str
    left_row_id: str
    right_row_id: str
    cell_index: int
    observed_left: Decimal
    observed_right: Decimal
    residual: Decimal
    status: str


@dataclass(frozen=True)
class TMNotePages3233Question:
    question_key: str
    row_ids: tuple[str, ...]
    candidate_report_norm_ids: tuple[int, ...]
    visible_values: tuple[str, ...]


@dataclass(frozen=True)
class TMNotePages3233MappingResult:
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
    partially_mapped_source_row_count: int
    question_source_row_count: int
    question_group_count: int
    financial_slot_count: int
    extracted_value_count: int
    zero_count: int
    mapped_source_slot_count: int
    ambiguous_source_slot_count: int
    source_only_slot_count: int
    mapped_assignment_count: int
    percentage_check_count: int
    percentage_pass_count: int
    hierarchy_check_count: int
    hierarchy_pass_count: int
    catch_all_check_count: int
    catch_all_pass_count: int
    duplicate_check_count: int
    duplicate_pass_count: int
    mapping_authority_scope: str
    mapping_authority_granted: bool
    schema_dispositions: tuple[TMNotePages3233SchemaDisposition, ...]
    source_dispositions: tuple[TMNotePages3233SourceDisposition, ...]
    cell_dispositions: tuple[TMNotePages3233CellDisposition, ...]
    mapped_assignments: tuple[TMNotePages3233MappedAssignment, ...]
    percentage_checks: tuple[TMNotePages3233PercentageCheck, ...]
    hierarchy_checks: tuple[TMNotePages3233HierarchyCheck, ...]
    catch_all_checks: tuple[TMNotePages3233CatchAllCheck, ...]
    duplicate_checks: tuple[TMNotePages3233DuplicateCheck, ...]
    questions: tuple[TMNotePages3233Question, ...]
    mapping_policy_sha256: str
    source_pdf_sha256: str
    source_ocr_sha256: tuple[str, ...]
    source_render_sha256: tuple[str, ...]
    axis_binding_sha256: str


def _ids(value: Any, field: str, *, allow_empty: bool = True) -> tuple[int, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise TMNotePages3233MappingError(f"TM pages32-33 {field} is invalid")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise TMNotePages3233MappingError(f"TM pages32-33 {field} contains a non-ID")
    result = tuple(int(item) for item in value)
    if len(set(result)) != len(result):
        raise TMNotePages3233MappingError(f"TM pages32-33 {field} contains duplicates")
    return result


def load_tm_note_pages32_33_mapping_policy(path: Path) -> TMNotePages3233MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNotePages3233MappingError(f"cannot load TM pages32-33 mapping: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGES32_33_AMOUNT_AXIS_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNotePages3233MappingError("TM pages32-33 mapping identity drifted")
    scopes = payload.get("scope_schema_ids")
    if scopes != [
        {"start": 727, "end": 745},
        {"start": 756, "end": 758},
        {"start": 766, "end": 782},
        {"ids": [5719, 5720, 5721, 5722, 5748, 5749, 6058, 6059, 6060]},
    ]:
        raise TMNotePages3233MappingError("TM pages32-33 schema scopes drifted")
    fixed = _ids(payload.get("fixed_mapped_ids"), "fixed IDs", allow_empty=False)
    ambiguous = _ids(payload.get("ambiguous_ids"), "ambiguous IDs")
    not_observed = _ids(payload.get("not_observed_ids"), "not-observed IDs", allow_empty=False)
    if (
        payload.get("schema_total") != TM_NOTE_PAGES3233_SCHEMA_TOTAL
        or payload.get("scope_schema_total") != TM_NOTE_PAGES3233_RECONCILED_COUNT
        or payload.get("schema_scope_sha256") != _SCHEMA_SCOPE_SHA256
        or set(fixed) != _MAPPED_IDS
        or set(ambiguous) != _AMBIGUOUS_IDS
        or set(not_observed) != _NOT_OBSERVED_IDS
        or set(fixed) | set(ambiguous) | set(not_observed) != _SCOPED_IDS
    ):
        raise TMNotePages3233MappingError("TM pages32-33 schema reconciliation sets drifted")
    raw_rules = payload.get("source_rules")
    if not isinstance(raw_rules, list) or len(raw_rules) != TM_NOTE_PAGES3233_SOURCE_ROW_COUNT:
        raise TMNotePages3233MappingError("TM pages32-33 source rule denominator drifted")
    rules = []
    for record in raw_rules:
        if not isinstance(record, dict):
            raise TMNotePages3233MappingError("TM pages32-33 source rule is invalid")
        try:
            disposition = TMNotePages3233RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMNotePages3233MappingError("TM pages32-33 rule disposition is invalid") from exc
        page_tag = record.get("page_tag")
        row_key = record.get("row_key")
        question_key = record.get("question_key")
        report_norm_ids = _ids(record.get("report_norm_ids"), "rule fixed IDs")
        candidates = _ids(record.get("candidate_report_norm_ids"), "rule candidate IDs")
        if (
            page_tag not in {"page-0032", "page-0033"}
            or not isinstance(row_key, str)
            or not row_key
            or (question_key is not None and question_key not in _QUESTION_KEYS)
        ):
            raise TMNotePages3233MappingError("TM pages32-33 rule identity is invalid")
        if disposition in {
            TMNotePages3233RuleDisposition.FIXED_STRUCTURAL,
            TMNotePages3233RuleDisposition.FIXED_AMOUNT_AXES,
            TMNotePages3233RuleDisposition.FIXED_CATCH_ALL_COMPONENT,
        }:
            valid = len(report_norm_ids) == 1 and not candidates and question_key is None
        elif disposition is TMNotePages3233RuleDisposition.AMBIGUOUS_MAPPING:
            valid = not report_norm_ids and bool(candidates) and bool(question_key)
        else:
            valid = not report_norm_ids and not candidates
        if not valid:
            raise TMNotePages3233MappingError("TM pages32-33 rule authority is invalid")
        rules.append(
            TMNotePages3233SourceRule(
                page_tag=page_tag,
                row_key=row_key,
                disposition=disposition,
                report_norm_ids=report_norm_ids,
                candidate_report_norm_ids=candidates,
                question_key=question_key,
            )
        )
    if len({(rule.page_tag, rule.row_key) for rule in rules}) != len(rules):
        raise TMNotePages3233MappingError("TM pages32-33 source rules are duplicated")
    if {item for rule in rules for item in rule.report_norm_ids} != _MAPPED_IDS or {
        item for rule in rules for item in rule.candidate_report_norm_ids
    } != _AMBIGUOUS_IDS:
        raise TMNotePages3233MappingError("TM pages32-33 source/schema coverage drifted")
    question_groups = payload.get("question_groups")
    if (
        not isinstance(question_groups, list)
        or set(question_groups) != _QUESTION_KEYS
        or len(question_groups) != len(_QUESTION_KEYS)
    ):
        raise TMNotePages3233MappingError("TM pages32-33 question groups drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNotePages3233MappingError("TM pages32-33 forbidden inputs drifted")
    table_policy = payload.get("source_table_policy")
    authority = payload.get("mapping_authority_scope")
    if (
        table_policy != "config/tables/tm-note-pages32-33-v1.yaml"
        or authority != "VISIBLE_FIXED_LABELS_TO_AMOUNT_AXES_ONLY"
    ):
        raise TMNotePages3233MappingError("TM pages32-33 mapping authority drifted")
    return TMNotePages3233MappingPolicy(
        source_path=path,
        document=str(payload.get("document", "")),
        scope="CONSOLIDATED",
        source_table_policy=table_policy,
        mapping_authority_scope=authority,
        schema_total=TM_NOTE_PAGES3233_SCHEMA_TOTAL,
        scope_schema_ids=tuple(sorted(_SCOPED_IDS)),
        schema_scope_sha256=_SCHEMA_SCOPE_SHA256,
        fixed_mapped_ids=fixed,
        ambiguous_ids=ambiguous,
        not_observed_ids=not_observed,
        source_rules=tuple(rules),
        question_groups=tuple(str(value) for value in question_groups),
        forbidden_mapping_inputs=tuple(str(value) for value in forbidden),
    )


def _schema_index(schema: list[SchemaItem]) -> dict[int, SchemaItem]:
    tm_schema = [item for item in schema if item.statement_type == "TM"]
    index = {item.schema_id: item for item in tm_schema}
    if len(tm_schema) != TM_NOTE_PAGES3233_SCHEMA_TOTAL or len(index) != len(tm_schema):
        raise TMNotePages3233MappingError("TM schema denominator or uniqueness drifted")
    branch = [(item_id, index[item_id].canonical_name) for item_id in sorted(_SCOPED_IDS)]
    digest = hashlib.sha256(
        json.dumps(branch, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if digest != _SCHEMA_SCOPE_SHA256:
        raise TMNotePages3233MappingError("TM pages32-33 schema branch hash drifted")
    return index


def _row_index(parsed: ParsedTMNotePages3233) -> dict[tuple[str, str], TMLoanAnalysisLogicalRow]:
    result = {(row.page_tag, row.row_key): row for row in parsed.rows}
    if len(result) != len(parsed.rows):
        raise TMNotePages3233MappingError("TM pages32-33 parsed row identities are duplicated")
    return result


def _page_axes(parsed: ParsedTMNotePages3233, page_tag: str):
    matches = [page.axes for page in parsed.pages if page.page_tag == page_tag]
    if len(matches) != 1:
        raise TMNotePages3233MappingError("TM pages32-33 page axes are unresolved")
    return matches[0]


def _percentage_checks(
    parsed: ParsedTMNotePages3233,
) -> tuple[TMNotePages3233PercentageCheck, ...]:
    rows = _row_index(parsed)
    checks = []
    for page_tag in ("page-0032", "page-0033"):
        denominator = rows[(page_tag, "GRAND_TOTAL")]
        for row in (item for item in parsed.rows if item.page_tag == page_tag):
            if row.row_kind is not TMNoteRowKind.NUMERIC:
                continue
            for amount_index, percentage_index, role in (
                (0, 1, "CURRENT"),
                (2, 3, "COMPARATIVE"),
            ):
                amount = row.row.cells[amount_index].value
                total = denominator.row.cells[amount_index].value
                reported = row.row.cells[percentage_index].value
                if amount is None or total is None or reported is None:
                    raise TMNotePages3233MappingError("TM percentage check received a blank")
                calculated = (amount * 100 / total).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                delta = abs(reported - calculated)
                checks.append(
                    TMNotePages3233PercentageCheck(
                        check_id=f"{page_tag}:percentage:{row.row_key.lower()}:{role.lower()}",
                        page_tag=page_tag,
                        row_key=row.row_key,
                        period_role=role,
                        amount=amount,
                        denominator=total,
                        reported_percentage=reported,
                        calculated_percentage=calculated,
                        absolute_delta=delta,
                        status="PASS" if delta <= Decimal("0.01") else "FAIL",
                    )
                )
    return tuple(checks)


def _hierarchy_checks(
    parsed: ParsedTMNotePages3233,
) -> tuple[TMNotePages3233HierarchyCheck, ...]:
    rows = _row_index(parsed)
    groups = {
        ("page-0032", "TCKT_TOTAL"): (
            "STATE_COMPANY",
            "STATE_OWNED_100",
            "STATE_OWNED_OVER_50",
            "TNHH_OTHER",
            "STATE_JSC_OVER_50",
            "JSC_OTHER",
            "PARTNERSHIP",
            "FOREIGN_INVESTED",
            "COOPERATIVE",
        ),
        ("page-0032", "PERSONAL_TOTAL"): ("HOUSEHOLD_PERSONAL",),
        ("page-0032", "OTHER_TOTAL"): ("ADMIN_ENTITY", "OTHER_ECONOMIC"),
        ("page-0032", "FOREIGN_BRANCH_TOTAL"): ("FOREIGN_BUSINESS", "FOREIGN_PERSONAL"),
        ("page-0032", "BANK_SUBTOTAL"): (
            "TCKT_TOTAL",
            "PERSONAL_TOTAL",
            "OTHER_TOTAL",
            "FOREIGN_BRANCH_TOTAL",
        ),
        ("page-0032", "GRAND_TOTAL"): ("BANK_SUBTOTAL", "MARGIN_MBS"),
        ("page-0033", "BANK_SUBTOTAL"): (
            "AGRICULTURE",
            "MINING",
            "MANUFACTURING",
            "UTILITIES",
            "WATER_WASTE",
            "CONSTRUCTION",
            "WHOLESALE_RETAIL",
            "TRANSPORT_STORAGE",
            "ACCOMMODATION_FOOD",
            "INFORMATION_COMMUNICATION",
            "FINANCIAL_INSURANCE",
            "REAL_ESTATE",
            "PROFESSIONAL_SCIENCE",
            "ADMIN_SUPPORT",
            "EDUCATION",
            "HEALTH_SOCIAL",
            "ARTS_RECREATION",
            "OTHER_SERVICES",
            "HOUSEHOLD_EMPLOYMENT",
            "FOREIGN_BRANCH",
        ),
        ("page-0033", "GRAND_TOTAL"): ("BANK_SUBTOTAL", "MARGIN_MBS"),
    }
    checks = []
    for (page_tag, target_key), component_keys in groups.items():
        target = rows[(page_tag, target_key)]
        axes = _page_axes(parsed, page_tag)
        for cell_index, axis in enumerate(axes):
            observed = target.row.cells[cell_index].value
            values = [rows[(page_tag, key)].row.cells[cell_index].value for key in component_keys]
            if observed is None or any(value is None for value in values):
                raise TMNotePages3233MappingError("TM hierarchy check received a blank")
            expected = sum((value for value in values if value is not None), Decimal(0))
            residual = observed - expected
            checks.append(
                TMNotePages3233HierarchyCheck(
                    check_id=f"{page_tag}:hierarchy:{target_key.lower()}:axis-{cell_index + 1}",
                    page_tag=page_tag,
                    target_row_key=target_key,
                    cell_index=cell_index,
                    measure_role=axis.measure_role,
                    period_role=axis.period_role,
                    expected=expected,
                    observed=observed,
                    residual=residual,
                    status="PASS" if residual == 0 else "FAIL",
                )
            )
    schema_766_components = (
        "STATE_COMPANY",
        "STATE_OWNED_100",
        "STATE_OWNED_OVER_50",
        "TNHH_OTHER",
        "STATE_JSC_OVER_50",
        "JSC_OTHER",
        "PARTNERSHIP",
        "FOREIGN_INVESTED",
        "COOPERATIVE",
        "HOUSEHOLD_PERSONAL",
        "ADMIN_ENTITY",
        "OTHER_ECONOMIC",
        "FOREIGN_BRANCH_TOTAL",
    )
    schema_766_components = (*schema_766_components, "MARGIN_MBS")
    target = rows[("page-0032", "GRAND_TOTAL")]
    for cell_index, axis in enumerate(_page_axes(parsed, "page-0032")):
        observed = target.row.cells[cell_index].value
        values = [
            rows[("page-0032", key)].row.cells[cell_index].value for key in schema_766_components
        ]
        if observed is None or any(value is None for value in values):
            raise TMNotePages3233MappingError("TM schema ID 766 rollup received a blank")
        expected = sum((value for value in values if value is not None), Decimal(0))
        residual = observed - expected
        checks.append(
            TMNotePages3233HierarchyCheck(
                check_id=f"page-0032:schema-rollup:766:axis-{cell_index + 1}",
                page_tag="page-0032",
                target_row_key="GRAND_TOTAL",
                cell_index=cell_index,
                measure_role=axis.measure_role,
                period_role=axis.period_role,
                expected=expected,
                observed=observed,
                residual=residual,
                status="PASS" if residual == 0 else "FAIL",
            )
        )
    return tuple(checks)


def _duplicate_checks(
    parsed: ParsedTMNotePages3233,
) -> tuple[TMNotePages3233DuplicateCheck, ...]:
    rows = _row_index(parsed)
    pairs = (
        ("BANK_SUBTOTAL", "BANK_SUBTOTAL"),
        ("MARGIN_MBS", "MARGIN_MBS"),
        ("GRAND_TOTAL", "GRAND_TOTAL"),
        ("FOREIGN_BRANCH_TOTAL", "FOREIGN_BRANCH"),
    )
    checks = []
    for left_key, right_key in pairs:
        left = rows[("page-0032", left_key)]
        right = rows[("page-0033", right_key)]
        for cell_index in range(4):
            left_value = left.row.cells[cell_index].value
            right_value = right.row.cells[cell_index].value
            if left_value is None or right_value is None:
                raise TMNotePages3233MappingError("TM duplicate check received a blank")
            residual = right_value - left_value
            checks.append(
                TMNotePages3233DuplicateCheck(
                    check_id=f"duplicate:{left_key.lower()}:{cell_index + 1}",
                    left_row_id=left.row_id,
                    right_row_id=right.row_id,
                    cell_index=cell_index,
                    observed_left=left_value,
                    observed_right=right_value,
                    residual=residual,
                    status="PASS" if residual == 0 else "FAIL",
                )
            )
    return tuple(checks)


def _visible_values(row: TMLoanAnalysisLogicalRow) -> str:
    return f"{row.page_tag}:{row.row_key}:[{','.join(str(cell.value) for cell in row.row.cells)}]"


def _axis_hash(parsed: ParsedTMNotePages3233) -> str:
    records = [
        (
            page.page_tag,
            axis.ordinal,
            axis.measure_role,
            axis.period_role,
            axis.period_end.isoformat(),
            axis.canonical_unit,
            axis.unit_multiplier,
            axis.axis_right_edge,
        )
        for page in parsed.pages
        for axis in page.axes
    ]
    return hashlib.sha256(
        json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _catch_all_assignments(
    parsed: ParsedTMNotePages3233,
    schema_index: dict[int, SchemaItem],
) -> tuple[
    tuple[TMNotePages3233MappedAssignment, ...],
    tuple[TMNotePages3233CatchAllCheck, ...],
]:
    rows = _row_index(parsed)
    components = (
        rows[("page-0032", "OTHER_ECONOMIC")],
        rows[("page-0032", "FOREIGN_BRANCH_TOTAL")],
    )
    axes = _page_axes(parsed, "page-0032")
    assignments = []
    checks = []
    for cell_index in (0, 2):
        axis = axes[cell_index]
        values = tuple(row.row.cells[cell_index].value for row in components)
        if any(value is None for value in values):
            raise TMNotePages3233MappingError("TM ID 782 aggregate component is blank")
        component_values = tuple(value for value in values if value is not None)
        aggregated = sum(component_values, Decimal(0))
        bboxes = tuple(row.value_bboxes[cell_index] for row in components)
        if any(bbox is None for bbox in bboxes):
            raise TMNotePages3233MappingError("TM ID 782 aggregate component lacks bbox")
        concrete_bboxes = tuple(bbox for bbox in bboxes if bbox is not None)
        source_bbox = (
            min(bbox.x0 for bbox in concrete_bboxes),
            min(bbox.y0 for bbox in concrete_bboxes),
            max(bbox.x1 for bbox in concrete_bboxes),
            max(bbox.y1 for bbox in concrete_bboxes),
        )
        assignments.append(
            TMNotePages3233MappedAssignment(
                report_norm_id=782,
                canonical_name=schema_index[782].canonical_name,
                row_id="page-0032:loan-analysis:aggregate-report-norm-0782",
                page_tag="page-0032",
                row_key="OTHER_ECONOMIC+FOREIGN_BRANCH_TOTAL",
                cell_index=cell_index,
                measure_role=axis.measure_role,
                observation=ObservationKind.VALUE.value,
                value=aggregated,
                period_role=axis.period_role,
                period_end=axis.period_end.isoformat(),
                period_type=axis.period_type,
                unit=axis.canonical_unit,
                unit_multiplier=axis.unit_multiplier,
                scope=parsed.scope,
                source_row_ids=tuple(
                    source_id for row in components for source_id in row.row.source_row_ids
                ),
                source_bbox=source_bbox,
                mapping_basis=(
                    "USER_CONFIRMED_ID_782_CATCH_ALL_SUM_OF_OTHER_ECONOMIC_AND_FOREIGN_BRANCH_TOTAL"
                ),
            )
        )
        checks.append(
            TMNotePages3233CatchAllCheck(
                check_id=f"page-0032:catch-all:782:{axis.period_role.casefold()}",
                report_norm_id=782,
                period_role=axis.period_role,
                component_row_keys=("OTHER_ECONOMIC", "FOREIGN_BRANCH_TOTAL"),
                component_values=component_values,
                aggregated_value=aggregated,
                status="PASS",
            )
        )
    return tuple(assignments), tuple(checks)


def reconcile_tm_note_pages32_33_items(
    parsed: ParsedTMNotePages3233,
    *,
    schema: list[SchemaItem],
    policy: TMNotePages3233MappingPolicy,
    source_pdf_path: Path,
) -> TMNotePages3233MappingResult:
    if parsed.mapping_authority or parsed.scope != policy.scope:
        raise TMNotePages3233MappingError("TM pages32-33 parser authority or scope drifted")
    if sha256_file(source_pdf_path) != parsed.source_pdf_sha256:
        raise TMNotePages3233MappingError("TM pages32-33 source PDF hash drifted")
    schema_index = _schema_index(schema)
    rows = _row_index(parsed)
    rules = {(rule.page_tag, rule.row_key): rule for rule in policy.source_rules}
    if set(rows) != set(rules):
        raise TMNotePages3233MappingError("TM pages32-33 parser/mapping row scopes differ")
    source_dispositions = []
    cell_dispositions = []
    assignments = []
    for identity, row in rows.items():
        rule = rules[identity]
        if rule.disposition in {
            TMNotePages3233RuleDisposition.FIXED_STRUCTURAL,
            TMNotePages3233RuleDisposition.FIXED_AMOUNT_AXES,
            TMNotePages3233RuleDisposition.FIXED_CATCH_ALL_COMPONENT,
        }:
            source_status = TMNotePages3233SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            mapped_ids = rule.report_norm_ids
            reason = (
                "user-confirmed source component of the ID 782 catch-all aggregate"
                if rule.disposition is TMNotePages3233RuleDisposition.FIXED_CATCH_ALL_COMPONENT
                else "visible fixed label; numeric authority is limited to amount axes"
            )
        elif rule.disposition is TMNotePages3233RuleDisposition.AMBIGUOUS_MAPPING:
            source_status = TMNotePages3233SourceStatus.AMBIGUOUS_MAPPING.value
            mapped_ids = ()
            reason = "visible label is narrower than or compatible with multiple schema concepts"
        else:
            source_status = TMNotePages3233SourceStatus(rule.disposition.value).value
            mapped_ids = ()
            reason = (
                "visible subtotal, duplicate or foreign-branch row retained without export mapping"
            )
        partial = rule.disposition in {
            TMNotePages3233RuleDisposition.FIXED_AMOUNT_AXES,
            TMNotePages3233RuleDisposition.FIXED_CATCH_ALL_COMPONENT,
        }
        source_dispositions.append(
            TMNotePages3233SourceDisposition(
                row_id=row.row_id,
                page_tag=row.page_tag,
                row_key=row.row_key,
                visible_label=row.row.label,
                status=source_status,
                mapped_report_norm_ids=mapped_ids,
                candidate_report_norm_ids=rule.candidate_report_norm_ids,
                partially_mapped=partial,
                question_key=rule.question_key,
                reason=reason,
            )
        )
        if row.row_kind is TMNoteRowKind.LABEL_ONLY:
            continue
        axes = _page_axes(parsed, row.page_tag)
        for cell_index, (cell, axis) in enumerate(zip(row.row.cells, axes, strict=True)):
            report_norm_id = None
            candidates: tuple[int, ...] = ()
            if rule.disposition in {
                TMNotePages3233RuleDisposition.FIXED_AMOUNT_AXES,
                TMNotePages3233RuleDisposition.FIXED_CATCH_ALL_COMPONENT,
            }:
                if axis.measure_role == "AMOUNT":
                    cell_status = TMNotePages3233CellStatus.MAPPED_AMOUNT.value
                    report_norm_id = rule.report_norm_ids[0]
                    cell_reason = (
                        "user-confirmed ID 782 catch-all aggregate component"
                        if rule.disposition
                        is TMNotePages3233RuleDisposition.FIXED_CATCH_ALL_COMPONENT
                        else "fixed visible label projected to amount axis"
                    )
                else:
                    cell_status = TMNotePages3233CellStatus.SOURCE_ONLY_PERCENTAGE.value
                    cell_reason = "percentage retained for validation/provenance only"
            elif rule.disposition is TMNotePages3233RuleDisposition.AMBIGUOUS_MAPPING:
                cell_status = TMNotePages3233CellStatus.AMBIGUOUS_MAPPING.value
                candidates = rule.candidate_report_norm_ids
                cell_reason = "mapping ambiguity applies to both amount and percentage observations"
            else:
                cell_status = TMNotePages3233CellStatus(rule.disposition.value).value
                cell_reason = "source-only observation"
            cell_dispositions.append(
                TMNotePages3233CellDisposition(
                    row_id=row.row_id,
                    page_tag=row.page_tag,
                    row_key=row.row_key,
                    cell_index=cell_index,
                    measure_role=axis.measure_role,
                    period_role=axis.period_role,
                    observation=cell.observation.value,
                    value=cell.value,
                    status=cell_status,
                    report_norm_id=report_norm_id,
                    candidate_report_norm_ids=candidates,
                    reason=cell_reason,
                )
            )
            if (
                report_norm_id is not None
                and rule.disposition is TMNotePages3233RuleDisposition.FIXED_AMOUNT_AXES
            ):
                if cell.value is None or cell.observation not in {
                    ObservationKind.VALUE,
                    ObservationKind.ZERO,
                }:
                    raise TMNotePages3233MappingError("TM mapped amount is not finite")
                bbox = row.value_bboxes[cell_index]
                if bbox is None:
                    raise TMNotePages3233MappingError("TM mapped amount lacks source bbox")
                assignments.append(
                    TMNotePages3233MappedAssignment(
                        report_norm_id=report_norm_id,
                        canonical_name=schema_index[report_norm_id].canonical_name,
                        row_id=row.row_id,
                        page_tag=row.page_tag,
                        row_key=row.row_key,
                        cell_index=cell_index,
                        measure_role=axis.measure_role,
                        observation=cell.observation.value,
                        value=cell.value,
                        period_role=axis.period_role,
                        period_end=axis.period_end.isoformat(),
                        period_type=axis.period_type,
                        unit=axis.canonical_unit,
                        unit_multiplier=axis.unit_multiplier,
                        scope=parsed.scope,
                        source_row_ids=row.row.source_row_ids,
                        source_bbox=(bbox.x0, bbox.y0, bbox.x1, bbox.y1),
                        mapping_basis="VISIBLE_FIXED_LABEL_TO_AMOUNT_AXIS_ONLY",
                    )
                )
    catch_all_assignments, catch_all_checks = _catch_all_assignments(parsed, schema_index)
    assignments.extend(catch_all_assignments)
    percentage = _percentage_checks(parsed)
    hierarchy = _hierarchy_checks(parsed)
    duplicates = _duplicate_checks(parsed)
    if (
        len(percentage) != TM_NOTE_PAGES3233_PERCENTAGE_CHECK_COUNT
        or any(check.status != "PASS" for check in percentage)
        or len(hierarchy) != TM_NOTE_PAGES3233_HIERARCHY_CHECK_COUNT
        or any(check.status != "PASS" for check in hierarchy)
        or len(catch_all_checks) != 2
        or any(check.status != "PASS" for check in catch_all_checks)
        or len(duplicates) != TM_NOTE_PAGES3233_DUPLICATE_CHECK_COUNT
        or any(check.status != "PASS" for check in duplicates)
    ):
        raise TMNotePages3233MappingError("TM pages32-33 validation failed")
    schema_dispositions = []
    for schema_id in sorted(schema_index):
        if schema_id in _MAPPED_IDS:
            status = TMNotePages3233SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            reason = "fixed visible label with amount-axis period/unit/scope binding"
        elif schema_id in _AMBIGUOUS_IDS:
            status = TMNotePages3233SchemaStatus.AMBIGUOUS_MAPPING.value
            reason = "one or more visible rows remain compatible but not exact"
        elif schema_id in _NOT_OBSERVED_IDS:
            status = TMNotePages3233SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            reason = "fully assessed branch item has no visible row on pages 32-33"
        else:
            status = TMNotePages3233SchemaStatus.UNASSESSED.value
            reason = "outside the two explicitly reconciled branches"
        schema_dispositions.append(
            TMNotePages3233SchemaDisposition(
                report_norm_id=schema_id,
                canonical_name=schema_index[schema_id].canonical_name,
                status=status,
                reason=reason,
            )
        )
    questions = []
    for question_key in policy.question_groups:
        question_rows = [
            row for identity, row in rows.items() if rules[identity].question_key == question_key
        ]
        questions.append(
            TMNotePages3233Question(
                question_key=question_key,
                row_ids=tuple(row.row_id for row in question_rows),
                candidate_report_norm_ids=tuple(
                    sorted(
                        {
                            item
                            for row in question_rows
                            for item in rules[(row.page_tag, row.row_key)].candidate_report_norm_ids
                        }
                    )
                ),
                visible_values=tuple(_visible_values(row) for row in question_rows),
            )
        )
    result = TMNotePages3233MappingResult(
        schema_item_count=len(schema_dispositions),
        status_reconciled_schema_count=TM_NOTE_PAGES3233_RECONCILED_COUNT,
        mapped_schema_count=TM_NOTE_PAGES3233_MAPPED_SCHEMA_COUNT,
        ambiguous_schema_count=TM_NOTE_PAGES3233_AMBIGUOUS_SCHEMA_COUNT,
        not_observed_schema_count=TM_NOTE_PAGES3233_NOT_OBSERVED_COUNT,
        not_applicable_schema_count=0,
        unassessed_schema_count=TM_NOTE_PAGES3233_UNASSESSED_COUNT,
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMNotePages3233SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        ambiguous_source_row_count=sum(
            item.status == TMNotePages3233SourceStatus.AMBIGUOUS_MAPPING.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status
            in {
                TMNotePages3233SourceStatus.SOURCE_ONLY_SUBTOTAL.value,
                TMNotePages3233SourceStatus.SOURCE_ONLY_FOREIGN_BRANCH.value,
                TMNotePages3233SourceStatus.SOURCE_ONLY_VALIDATION.value,
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
        zero_count=sum(
            item.observation == ObservationKind.ZERO.value for item in cell_dispositions
        ),
        mapped_source_slot_count=sum(
            item.status == TMNotePages3233CellStatus.MAPPED_AMOUNT.value
            for item in cell_dispositions
        ),
        ambiguous_source_slot_count=sum(
            item.status == TMNotePages3233CellStatus.AMBIGUOUS_MAPPING.value
            for item in cell_dispositions
        ),
        source_only_slot_count=sum(
            item.status
            in {
                TMNotePages3233CellStatus.SOURCE_ONLY_PERCENTAGE.value,
                TMNotePages3233CellStatus.SOURCE_ONLY_SUBTOTAL.value,
                TMNotePages3233CellStatus.SOURCE_ONLY_FOREIGN_BRANCH.value,
                TMNotePages3233CellStatus.SOURCE_ONLY_VALIDATION.value,
            }
            for item in cell_dispositions
        ),
        mapped_assignment_count=len(assignments),
        percentage_check_count=len(percentage),
        percentage_pass_count=sum(check.status == "PASS" for check in percentage),
        hierarchy_check_count=len(hierarchy),
        hierarchy_pass_count=sum(check.status == "PASS" for check in hierarchy),
        catch_all_check_count=len(catch_all_checks),
        catch_all_pass_count=sum(check.status == "PASS" for check in catch_all_checks),
        duplicate_check_count=len(duplicates),
        duplicate_pass_count=sum(check.status == "PASS" for check in duplicates),
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        cell_dispositions=tuple(cell_dispositions),
        mapped_assignments=tuple(assignments),
        percentage_checks=percentage,
        hierarchy_checks=hierarchy,
        catch_all_checks=catch_all_checks,
        duplicate_checks=duplicates,
        questions=tuple(questions),
        mapping_policy_sha256=sha256_file(policy.source_path),
        source_pdf_sha256=parsed.source_pdf_sha256,
        source_ocr_sha256=tuple(page.source_sha256 for page in parsed.pages),
        source_render_sha256=tuple(page.source_render_sha256 for page in parsed.pages),
        axis_binding_sha256=_axis_hash(parsed),
    )
    return validate_tm_note_pages32_33_mapping_result(result)


def validate_tm_note_pages32_33_mapping_result(
    result: TMNotePages3233MappingResult,
) -> TMNotePages3233MappingResult:
    if (
        result.schema_item_count != TM_NOTE_PAGES3233_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_NOTE_PAGES3233_RECONCILED_COUNT
        or result.mapped_schema_count != TM_NOTE_PAGES3233_MAPPED_SCHEMA_COUNT
        or result.ambiguous_schema_count != TM_NOTE_PAGES3233_AMBIGUOUS_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_NOTE_PAGES3233_NOT_OBSERVED_COUNT
        or result.not_applicable_schema_count != 0
        or result.unassessed_schema_count != TM_NOTE_PAGES3233_UNASSESSED_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_NOTE_PAGES3233_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_NOTE_PAGES3233_MAPPED_SOURCE_COUNT
        or result.ambiguous_source_row_count != TM_NOTE_PAGES3233_AMBIGUOUS_SOURCE_COUNT
        or result.source_only_row_count != TM_NOTE_PAGES3233_SOURCE_ONLY_COUNT
        or result.partially_mapped_source_row_count != TM_NOTE_PAGES3233_PARTIAL_SOURCE_COUNT
        or result.question_source_row_count != 0
        or result.question_group_count != 0
        or result.financial_slot_count != TM_NOTE_PAGES3233_SLOT_COUNT
        or result.extracted_value_count != TM_NOTE_PAGES3233_VALUE_COUNT
        or result.zero_count != TM_NOTE_PAGES3233_ZERO_COUNT
        or result.mapped_source_slot_count != TM_NOTE_PAGES3233_MAPPED_SLOT_COUNT
        or result.ambiguous_source_slot_count != TM_NOTE_PAGES3233_AMBIGUOUS_SLOT_COUNT
        or result.source_only_slot_count != TM_NOTE_PAGES3233_SOURCE_ONLY_SLOT_COUNT
        or result.mapped_assignment_count != TM_NOTE_PAGES3233_ASSIGNMENT_COUNT
        or result.percentage_check_count != TM_NOTE_PAGES3233_PERCENTAGE_CHECK_COUNT
        or result.percentage_pass_count != TM_NOTE_PAGES3233_PERCENTAGE_CHECK_COUNT
        or result.hierarchy_check_count != TM_NOTE_PAGES3233_HIERARCHY_CHECK_COUNT
        or result.hierarchy_pass_count != TM_NOTE_PAGES3233_HIERARCHY_CHECK_COUNT
        or result.catch_all_check_count != 2
        or result.catch_all_pass_count != 2
        or result.duplicate_check_count != TM_NOTE_PAGES3233_DUPLICATE_CHECK_COUNT
        or result.duplicate_pass_count != TM_NOTE_PAGES3233_DUPLICATE_CHECK_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMNotePages3233MappingError("TM pages32-33 result denominator drifted")
    if (
        result.mapped_schema_count
        + result.ambiguous_schema_count
        + result.not_observed_schema_count
        != result.status_reconciled_schema_count
        or result.status_reconciled_schema_count + result.unassessed_schema_count
        != result.schema_item_count
        or result.mapped_source_row_count
        + result.ambiguous_source_row_count
        + result.source_only_row_count
        != result.source_row_count
        or result.mapped_source_slot_count
        + result.ambiguous_source_slot_count
        + result.source_only_slot_count
        != result.financial_slot_count
    ):
        raise TMNotePages3233MappingError("TM pages32-33 reconciliation arithmetic drifted")
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMNotePages3233SchemaStatus)
    }
    if (
        by_status[TMNotePages3233SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] != _MAPPED_IDS
        or by_status[TMNotePages3233SchemaStatus.AMBIGUOUS_MAPPING.value] != _AMBIGUOUS_IDS
        or by_status[TMNotePages3233SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value]
        != _NOT_OBSERVED_IDS
    ):
        raise TMNotePages3233MappingError("TM pages32-33 exact schema sets drifted")
    assignment_keys = {
        (item.report_norm_id, item.period_end, item.measure_role)
        for item in result.mapped_assignments
    }
    if len(assignment_keys) != len(result.mapped_assignments) or any(
        item.measure_role != "AMOUNT"
        or item.cell_index not in {0, 2}
        or item.unit != "VND"
        or item.unit_multiplier != 1_000_000
        or item.mapping_basis
        not in {
            "VISIBLE_FIXED_LABEL_TO_AMOUNT_AXIS_ONLY",
            ("USER_CONFIRMED_ID_782_CATCH_ALL_SUM_OF_OTHER_ECONOMIC_AND_FOREIGN_BRANCH_TOTAL"),
        }
        for item in result.mapped_assignments
    ):
        raise TMNotePages3233MappingError("TM pages32-33 percentage mapping or duplication leaked")
    if any(
        check.status != "PASS" or check.absolute_delta > Decimal("0.01")
        for check in result.percentage_checks
    ) or any(check.status != "PASS" or check.residual != 0 for check in result.hierarchy_checks):
        raise TMNotePages3233MappingError("TM pages32-33 accounting validation drifted")
    if any(check.status != "PASS" or check.residual != 0 for check in result.duplicate_checks):
        raise TMNotePages3233MappingError("TM pages32-33 duplicate validation drifted")
    if {question.question_key for question in result.questions} != _QUESTION_KEYS:
        raise TMNotePages3233MappingError("TM pages32-33 question coverage drifted")
    if [
        (
            check.report_norm_id,
            check.period_role,
            check.component_row_keys,
            check.component_values,
            check.aggregated_value,
            check.status,
        )
        for check in result.catch_all_checks
    ] != [
        (
            782,
            "CURRENT",
            ("OTHER_ECONOMIC", "FOREIGN_BRANCH_TOTAL"),
            (Decimal("586508"), Decimal("8815772")),
            Decimal("9402280"),
            "PASS",
        ),
        (
            782,
            "COMPARATIVE",
            ("OTHER_ECONOMIC", "FOREIGN_BRANCH_TOTAL"),
            (Decimal("608368"), Decimal("9330629")),
            Decimal("9938997"),
            "PASS",
        ),
    ]:
        raise TMNotePages3233MappingError("TM ID 782 catch-all aggregate drifted")
    catch_all_assignments = [
        item for item in result.mapped_assignments if item.report_norm_id == 782
    ]
    if [
        (item.period_role, item.value, item.row_key, item.mapping_basis)
        for item in catch_all_assignments
    ] != [
        (
            "CURRENT",
            Decimal("9402280"),
            "OTHER_ECONOMIC+FOREIGN_BRANCH_TOTAL",
            "USER_CONFIRMED_ID_782_CATCH_ALL_SUM_OF_OTHER_ECONOMIC_AND_FOREIGN_BRANCH_TOTAL",
        ),
        (
            "COMPARATIVE",
            Decimal("9938997"),
            "OTHER_ECONOMIC+FOREIGN_BRANCH_TOTAL",
            "USER_CONFIRMED_ID_782_CATCH_ALL_SUM_OF_OTHER_ECONOMIC_AND_FOREIGN_BRANCH_TOTAL",
        ),
    ] or any(len(item.source_row_ids) < 2 for item in catch_all_assignments):
        raise TMNotePages3233MappingError("TM ID 782 emitted more than one target per period")
    return result


__all__ = [
    "TM_NOTE_PAGES3233_POLICY_RELATIVE_PATH",
    "TMNotePages3233CellStatus",
    "TMNotePages3233MappingError",
    "TMNotePages3233MappingPolicy",
    "TMNotePages3233MappingResult",
    "TMNotePages3233SchemaStatus",
    "TMNotePages3233SourceStatus",
    "load_tm_note_pages32_33_mapping_policy",
    "reconcile_tm_note_pages32_33_items",
    "validate_tm_note_pages32_33_mapping_result",
]
