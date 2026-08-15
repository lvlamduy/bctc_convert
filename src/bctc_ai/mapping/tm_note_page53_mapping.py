"""Hierarchy-safe item mapping for MBB consolidated TM page 53."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.schema.registry import SchemaItem
from bctc_ai.tables.tm_note_page53 import ParsedTMPage53, TMPage53LogicalRow

TM_PAGE53_MAPPING_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page53-v1.yaml")
TM_PAGE53_SCHEMA_TOTAL = 1_713
TM_PAGE53_SCOPE_SCHEMA_COUNT = 44
TM_PAGE53_MAPPED_SCHEMA_COUNT = 44
TM_PAGE53_STRUCTURAL_MAPPED_SCHEMA_COUNT = 8
TM_PAGE53_VALUE_BEARING_MAPPED_SCHEMA_COUNT = 36
TM_PAGE53_UNASSESSED_SCHEMA_COUNT = 1_669
TM_PAGE53_SOURCE_ROW_COUNT = 14
TM_PAGE53_STRUCTURAL_SOURCE_ROW_COUNT = 2
TM_PAGE53_NUMERIC_SOURCE_ROW_COUNT = 12
TM_PAGE53_FINANCIAL_SLOT_COUNT = 72
TM_PAGE53_VALUE_COUNT = 68
TM_PAGE53_DASH_COUNT = 4
TM_PAGE53_ASSIGNMENT_COUNT = 72
TM_PAGE53_VALIDATION_CHECK_COUNT = 36
TM_PAGE53_VALIDATION_PASS_COUNT = 30
TM_PAGE53_VALIDATION_NOT_TESTABLE_COUNT = 6

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCOPE_IDS = set(range(5762, 5806))
_STRUCTURAL_IDS = {5762, 5763, 5764, 5771, 5778, 5785, 5792, 5799}
_VALUE_IDS = _SCOPE_IDS - _STRUCTURAL_IDS
_AXIS_KEYS = ("NORTH", "CENTRAL", "SOUTH", "OTHER", "ELIMINATION", "TOTAL")
_METRIC_KEYS = (
    "ASSETS",
    "LIABILITIES",
    "FIXED_ASSETS",
    "REVENUE",
    "EXPENSE",
    "PROFIT_BEFORE_TAX",
)
_EXPECTED_AXIS_PARENT_IDS = {
    "NORTH": 5764,
    "CENTRAL": 5771,
    "SOUTH": 5778,
    "OTHER": 5785,
    "ELIMINATION": 5792,
    "TOTAL": 5799,
}
_EXPECTED_METRIC_TARGET_IDS = {
    "ASSETS": (5765, 5772, 5779, 5786, 5793, 5800),
    "LIABILITIES": (5766, 5773, 5780, 5787, 5794, 5801),
    "FIXED_ASSETS": (5767, 5774, 5781, 5788, 5795, 5802),
    "REVENUE": (5768, 5775, 5782, 5789, 5796, 5803),
    "EXPENSE": (5769, 5776, 5783, 5790, 5797, 5804),
    "PROFIT_BEFORE_TAX": (5770, 5777, 5784, 5791, 5798, 5805),
}
_EXPECTED_TOTAL_FORMULAS = {
    5800: (5765, 5772, 5779, 5786, 5793),
    5801: (5766, 5773, 5780, 5787, 5794),
    5802: (5767, 5774, 5781, 5788, 5795),
    5803: (5768, 5775, 5782, 5789, 5796),
    5804: (5769, 5776, 5783, 5790, 5797),
    5805: (5770, 5777, 5784, 5791, 5798),
}
_EXPECTED_PBT_FORMULAS = {
    5770: (5768, 5769),
    5777: (5775, 5776),
    5784: (5782, 5783),
    5791: (5789, 5790),
    5798: (5796, 5797),
    5805: (5803, 5804),
}
_SCHEMA_SCOPE_SHA256 = "8b3873b35f2d7b35fc74fbe67ebd9593c315148e91630313bef320b58a7d14ee"
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text_as_item_selector",
    "numeric_value_magnitude_as_item_selector",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
    "accounting_equation_result_as_extracted_value",
    "page54_value_as_page53_item_selector",
    "page54_value_as_page53_imputation",
    "schema_id_outside_page53_scope",
}


class TMPage53MappingError(ValueError):
    pass


class TMPage53SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    UNASSESSED = "UNASSESSED"


class TMPage53SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"


@dataclass(frozen=True)
class TMPage53StructuralTarget:
    source_role: str
    report_norm_id: int


@dataclass(frozen=True)
class TMPage53ExternalTotal:
    period_role: str
    metric_key: str
    value: Decimal
    owner_scope: str


@dataclass(frozen=True)
class TMPage53MappingPolicy:
    source_path: Path
    document: str
    page_number: int
    page_tag: str
    report_scope: str
    mapping_authority_scope: str
    source_table_policy: str
    source_table_policy_sha256: str
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    upstream_ocr_sha256: str
    schema_workbook_sha256: str
    schema_total: int
    scope_schema_ids: tuple[int, ...]
    schema_scope_sha256: str
    structural_targets: tuple[TMPage53StructuralTarget, ...]
    axis_parent_ids: tuple[tuple[str, int], ...]
    metric_target_ids: tuple[tuple[str, tuple[int, ...]], ...]
    total_formulas: tuple[tuple[int, tuple[int, ...]], ...]
    pbt_formulas: tuple[tuple[int, tuple[int, ...]], ...]
    external_page54_totals: tuple[TMPage53ExternalTotal, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage53SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage53SourceDisposition:
    row_id: str
    ordinal: int
    source_role: str
    metric_key: str | None
    period_role: str | None
    period_type: str | None
    status: str
    report_norm_ids: tuple[int, ...]
    observations: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    period_starts: tuple[str | None, ...]
    period_ends: tuple[str | None, ...]
    period_roles: tuple[str | None, ...]
    period_types: tuple[str | None, ...]
    unit: str
    unit_multiplier: int
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage53MappedAssignment:
    source_row_id: str
    source_role: str
    metric_key: str
    period_role: str
    period_type: str
    cell_index: int
    axis_key: str
    report_norm_id: int
    observation: str
    value: Decimal | None
    period_start: str
    period_end: str
    unit: str
    unit_multiplier: int
    mapping_basis: str


@dataclass(frozen=True)
class TMPage53ValidationCheck:
    check_id: str
    check_kind: str
    period_role: str
    metric_key: str
    axis_key: str | None
    status: str
    expected_value: Decimal | None
    observed_value: Decimal | None
    residual: Decimal | None
    target_report_norm_id: int
    external_owner_scope: str | None
    reason: str


@dataclass(frozen=True)
class TMPage53MappingResult:
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
    structural_mapped_schema_count: int
    value_bearing_mapped_schema_count: int
    not_observed_schema_count: int
    not_applicable_schema_count: int
    ambiguous_schema_count: int
    unresolved_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    structural_source_row_count: int
    numeric_source_row_count: int
    source_question_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_assignment_count: int
    validation_check_count: int
    validation_pass_count: int
    validation_not_testable_count: int
    schema_dispositions: tuple[TMPage53SchemaDisposition, ...]
    source_dispositions: tuple[TMPage53SourceDisposition, ...]
    mapped_assignments: tuple[TMPage53MappedAssignment, ...]
    validation_checks: tuple[TMPage53ValidationCheck, ...]
    total_formulas_validation_only: tuple[tuple[int, tuple[int, ...]], ...]
    pbt_formulas_validation_only: tuple[tuple[int, tuple[int, ...]], ...]
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    upstream_ocr_sha256: str
    schema_workbook_sha256: str
    schema_projection_sha256: str
    policy_sha256: str
    mapping_inputs: tuple[str, ...]


def _positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TMPage53MappingError(f"invalid positive TM page-53 field: {field}")
    return value


def _int_list(value: Any, field: str) -> tuple[int, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise TMPage53MappingError(f"TM page-53 {field} is invalid")
    result = tuple(value)
    if len(set(result)) != len(result):
        raise TMPage53MappingError(f"TM page-53 {field} contains duplicates")
    return result


def _ordered_int_mapping(value: Any, field: str) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, dict) or any(
        not isinstance(key, str) or not key or isinstance(item, bool) or not isinstance(item, int)
        for key, item in value.items()
    ):
        raise TMPage53MappingError(f"TM page-53 {field} is invalid")
    return tuple((key, item) for key, item in value.items())


def _ordered_list_mapping(value: Any, field: str) -> tuple[tuple[str, tuple[int, ...]], ...]:
    if not isinstance(value, dict):
        raise TMPage53MappingError(f"TM page-53 {field} is invalid")
    return tuple((str(key), _int_list(items, field)) for key, items in value.items())


def _formula_mapping(value: Any, field: str) -> tuple[tuple[int, tuple[int, ...]], ...]:
    if not isinstance(value, dict):
        raise TMPage53MappingError(f"TM page-53 {field} is invalid")
    result = []
    for key, items in value.items():
        if isinstance(key, bool) or not isinstance(key, int):
            raise TMPage53MappingError(f"TM page-53 {field} target is invalid")
        result.append((key, _int_list(items, field)))
    return tuple(result)


def load_tm_page53_mapping_policy(path: Path) -> TMPage53MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage53MappingError(f"cannot load TM page-53 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE53_GEOGRAPHIC_SEGMENT_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 53
        or payload.get("page_tag") != "page-0053"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage53MappingError("TM page-53 mapping identity drifted")
    hashes = tuple(
        payload.get(field)
        for field in (
            "source_table_policy_sha256",
            "source_pdf_sha256",
            "source_render_sha256",
            "source_ocr_sha256",
            "upstream_ocr_sha256",
            "schema_workbook_sha256",
        )
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage53MappingError("TM page-53 mapping hashes are invalid")
    table_policy = payload.get("source_table_policy")
    candidate_roots = (path.resolve().parents[2], Path.cwd().resolve())
    table_paths = tuple(
        root / table_policy
        for root in candidate_roots
        if isinstance(table_policy, str) and (root / table_policy).is_file()
    )
    if (
        table_policy != "config/tables/tm-note-page53-v1.yaml"
        or not table_paths
        or sha256_file(table_paths[0]) != hashes[0]
    ):
        raise TMPage53MappingError("TM page-53 table policy binding drifted")
    if (
        _positive_int(payload, "schema_total") != TM_PAGE53_SCHEMA_TOTAL
        or payload.get("scope_schema_ids") != [{"start": 5762, "end": 5805}]
        or payload.get("scope_schema_total") != TM_PAGE53_SCOPE_SCHEMA_COUNT
        or payload.get("schema_scope_sha256") != _SCHEMA_SCOPE_SHA256
    ):
        raise TMPage53MappingError("TM page-53 schema scope drifted")
    raw_structural = payload.get("structural_targets")
    if not isinstance(raw_structural, list) or len(raw_structural) != 2:
        raise TMPage53MappingError("TM page-53 structural targets are invalid")
    structural = tuple(
        TMPage53StructuralTarget(
            source_role=str(record.get("source_role")),
            report_norm_id=_positive_int(record, "report_norm_id"),
        )
        for record in raw_structural
        if isinstance(record, dict)
    )
    if tuple((item.source_role, item.report_norm_id) for item in structural) != (
        ("SEGMENT_REPORT_ROOT", 5762),
        ("GEOGRAPHIC_SEGMENT_TITLE", 5763),
    ):
        raise TMPage53MappingError("TM page-53 structural target order drifted")
    axis_parent_ids = _ordered_int_mapping(payload.get("axis_parent_ids"), "axis parents")
    metric_target_ids = _ordered_list_mapping(payload.get("metric_target_ids"), "metric targets")
    total_formulas = _formula_mapping(
        payload.get("total_formulas_validation_only"), "total formulas"
    )
    pbt_formulas = _formula_mapping(payload.get("pbt_formulas_validation_only"), "PBT formulas")
    if (
        dict(axis_parent_ids) != _EXPECTED_AXIS_PARENT_IDS
        or tuple(key for key, _ in axis_parent_ids) != _AXIS_KEYS
    ):
        raise TMPage53MappingError("TM page-53 axis parent targets drifted")
    if (
        dict(metric_target_ids) != _EXPECTED_METRIC_TARGET_IDS
        or tuple(key for key, _ in metric_target_ids) != _METRIC_KEYS
    ):
        raise TMPage53MappingError("TM page-53 metric targets drifted")
    if (
        dict(total_formulas) != _EXPECTED_TOTAL_FORMULAS
        or dict(pbt_formulas) != _EXPECTED_PBT_FORMULAS
    ):
        raise TMPage53MappingError("TM page-53 validation formulas drifted")
    raw_external = payload.get("external_page54_totals_validation_only")
    if not isinstance(raw_external, list) or len(raw_external) != 12:
        raise TMPage53MappingError("TM page-53 external total validations are incomplete")
    external = []
    for record in raw_external:
        if not isinstance(record, dict):
            raise TMPage53MappingError("TM page-53 external total record is invalid")
        value = record.get("value")
        if isinstance(value, bool) or not isinstance(value, int):
            raise TMPage53MappingError("TM page-53 external total value is invalid")
        external.append(
            TMPage53ExternalTotal(
                period_role=str(record.get("period_role")),
                metric_key=str(record.get("metric_key")),
                value=Decimal(value),
                owner_scope=str(record.get("owner_scope")),
            )
        )
    if tuple((item.period_role, item.metric_key) for item in external) != tuple(
        (role, metric) for role in ("CURRENT", "COMPARATIVE") for metric in _METRIC_KEYS
    ) or any(item.owner_scope != "page-0054" for item in external):
        raise TMPage53MappingError("TM page-53 external total order drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage53MappingError("TM page-53 forbidden mapping inputs drifted")
    return TMPage53MappingPolicy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=53,
        page_tag="page-0053",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=str(payload.get("mapping_authority_scope", "")),
        source_table_policy=table_policy,
        source_table_policy_sha256=str(hashes[0]),
        source_pdf_sha256=str(hashes[1]),
        source_render_sha256=str(hashes[2]),
        source_ocr_sha256=str(hashes[3]),
        upstream_ocr_sha256=str(hashes[4]),
        schema_workbook_sha256=str(hashes[5]),
        schema_total=TM_PAGE53_SCHEMA_TOTAL,
        scope_schema_ids=tuple(range(5762, 5806)),
        schema_scope_sha256=_SCHEMA_SCOPE_SHA256,
        structural_targets=structural,
        axis_parent_ids=axis_parent_ids,
        metric_target_ids=metric_target_ids,
        total_formulas=total_formulas,
        pbt_formulas=pbt_formulas,
        external_page54_totals=tuple(external),
        forbidden_mapping_inputs=tuple(str(value) for value in forbidden),
        policy_sha256=sha256_file(path),
    )


def _schema_projection_hash(items: tuple[SchemaItem, ...]) -> str:
    payload = [
        (
            item.schema_id,
            item.display_order,
            item.canonical_name,
            item.parent_id,
            tuple(item.children),
        )
        for item in items
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _schema_scope_hash(schema_by_id: dict[int, SchemaItem]) -> str:
    payload = [
        (schema_id, schema_by_id[schema_id].canonical_name, schema_by_id[schema_id].parent_id)
        for schema_id in sorted(_SCOPE_IDS)
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validate_schema_branch(schema_by_id: dict[int, SchemaItem]) -> None:
    if _schema_scope_hash(schema_by_id) != _SCHEMA_SCOPE_SHA256:
        raise TMPage53MappingError("TM page-53 schema scope hash drifted")
    if schema_by_id[5762].parent_id != 1259 or tuple(schema_by_id[5762].children) != (
        5763,
        5806,
    ):
        raise TMPage53MappingError("TM page-53 segment root hierarchy drifted")
    axis_ids = tuple(_EXPECTED_AXIS_PARENT_IDS.values())
    if schema_by_id[5763].parent_id != 5762 or tuple(schema_by_id[5763].children) != axis_ids:
        raise TMPage53MappingError("TM page-53 geographic root hierarchy drifted")
    for axis_id in axis_ids:
        expected_children = tuple(range(axis_id + 1, axis_id + 7))
        if tuple(schema_by_id[axis_id].children) != expected_children or any(
            schema_by_id[child].parent_id != axis_id for child in expected_children
        ):
            raise TMPage53MappingError(f"TM page-53 axis hierarchy drifted: {axis_id}")
    display_orders = tuple(
        schema_by_id[schema_id].display_order for schema_id in sorted(_SCOPE_IDS)
    )
    if display_orders != tuple(range(display_orders[0], display_orders[0] + 44)):
        raise TMPage53MappingError("TM page-53 display-order branch is not contiguous")


def _source_disposition(
    row: TMPage53LogicalRow,
    report_norm_ids: tuple[int, ...],
    *,
    unit: str,
    unit_multiplier: int,
) -> TMPage53SourceDisposition:
    return TMPage53SourceDisposition(
        row_id=row.row_id,
        ordinal=row.ordinal,
        source_role=row.source_role,
        metric_key=row.metric_key,
        period_role=row.period_role,
        period_type=row.period_type,
        status=TMPage53SourceStatus.MAPPED_AUTOMATIC_SCOPED.value,
        report_norm_ids=report_norm_ids,
        observations=tuple(cell.observation.value for cell in row.row.cells),
        values=tuple(cell.value for cell in row.row.cells),
        period_starts=tuple(
            value.isoformat() if value is not None else None for value in row.cell_period_starts
        ),
        period_ends=tuple(
            value.isoformat() if value is not None else None for value in row.cell_period_ends
        ),
        period_roles=row.cell_period_roles,
        period_types=row.cell_period_types,
        unit=unit,
        unit_multiplier=unit_multiplier,
        question_required=False,
        reason=(
            "visible structural hierarchy and fixed axis/metric transposition uniquely bind this "
            "page-53 source row; values, equations, and page-54 totals never select an item"
        ),
    )


def _validations(
    parsed: ParsedTMPage53,
    policy: TMPage53MappingPolicy,
) -> tuple[TMPage53ValidationCheck, ...]:
    numeric = {
        (row.period_role, row.metric_key): row
        for row in parsed.rows
        if row.metric_key is not None and row.period_role is not None
    }
    targets = dict(policy.metric_target_ids)
    checks = []
    for role in ("CURRENT", "COMPARATIVE"):
        for metric in _METRIC_KEYS:
            row = numeric[(role, metric)]
            components = row.row.cells[:5]
            observed = row.row.cells[5].value
            if observed is None:
                raise TMPage53MappingError("TM page-53 printed total is absent")
            dash_component = any(cell.observation is ObservationKind.DASH for cell in components)
            expected = (
                None if dash_component else sum((cell.value for cell in components), Decimal(0))
            )
            status = (
                "NOT_TESTABLE_DASH_IS_NOT_ZERO"
                if dash_component
                else ("PASS" if expected == observed else "FAIL")
            )
            checks.append(
                TMPage53ValidationCheck(
                    check_id=f"SEGMENT_TOTAL_{role}_{metric}",
                    check_kind="SEGMENT_SUM_VALIDATION_ONLY",
                    period_role=role,
                    metric_key=metric,
                    axis_key="TOTAL",
                    status=status,
                    expected_value=expected,
                    observed_value=observed,
                    residual=None if expected is None else observed - expected,
                    target_report_norm_id=targets[metric][5],
                    external_owner_scope=None,
                    reason=(
                        "the printed total is checked after mapping against four regions plus the "
                        "printed elimination value; an equation containing a DASH is explicitly "
                        "not testable because DASH is not zero"
                    ),
                )
            )
    for role in ("CURRENT", "COMPARATIVE"):
        revenue = numeric[(role, "REVENUE")]
        expense = numeric[(role, "EXPENSE")]
        pbt = numeric[(role, "PROFIT_BEFORE_TAX")]
        for index, axis_key in enumerate(_AXIS_KEYS):
            revenue_value = revenue.row.cells[index].value
            expense_value = expense.row.cells[index].value
            if revenue_value is None or expense_value is None:
                raise TMPage53MappingError("TM page-53 PBT validation operand is absent")
            expected = revenue_value - expense_value
            observed = pbt.row.cells[index].value
            dash_observed = pbt.row.cells[index].observation is ObservationKind.DASH
            status = (
                "NOT_TESTABLE_DASH_IS_NOT_ZERO"
                if dash_observed
                else ("PASS" if observed == expected else "FAIL")
            )
            checks.append(
                TMPage53ValidationCheck(
                    check_id=f"PBT_SUBTRACTION_{role}_{axis_key}",
                    check_kind="PBT_SUBTRACTION_VALIDATION_ONLY",
                    period_role=role,
                    metric_key="PROFIT_BEFORE_TAX",
                    axis_key=axis_key,
                    status=status,
                    expected_value=expected,
                    observed_value=observed,
                    residual=None if observed is None else observed - expected,
                    target_report_norm_id=targets["PROFIT_BEFORE_TAX"][index],
                    external_owner_scope=None,
                    reason=(
                        "printed PBT is checked as printed revenue less printed expense after mapping; "
                        "a printed DASH result is explicitly not testable even when the two printed "
                        "numeric operands happen to be equal"
                    ),
                )
            )
    for external in policy.external_page54_totals:
        row = numeric[(external.period_role, external.metric_key)]
        observed = row.row.cells[5].value
        if observed is None:
            raise TMPage53MappingError("TM page-53 total for page-54 validation is absent")
        checks.append(
            TMPage53ValidationCheck(
                check_id=f"PAGE54_PARALLEL_TOTAL_{external.period_role}_{external.metric_key}",
                check_kind="EXTERNAL_PAGE54_TOTAL_VALIDATION_ONLY",
                period_role=external.period_role,
                metric_key=external.metric_key,
                axis_key="TOTAL",
                status="PASS" if observed == external.value else "FAIL",
                expected_value=external.value,
                observed_value=observed,
                residual=observed - external.value,
                target_report_norm_id=targets[external.metric_key][5],
                external_owner_scope=external.owner_scope,
                reason=(
                    "the independently owned page-54 parallel total is equality evidence only and "
                    "never selects or populates a page-53 item"
                ),
            )
        )
    return tuple(checks)


def reconcile_tm_page53_items(
    parsed: ParsedTMPage53,
    *,
    schema: Sequence[SchemaItem],
    policy: TMPage53MappingPolicy,
    source_pdf_path: Path,
    schema_workbook_path: Path,
) -> TMPage53MappingResult:
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
        or parsed.upstream_ocr_sha256 != policy.upstream_ocr_sha256
    ):
        raise TMPage53MappingError("TM page-53 parser/mapping identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage53MappingError("TM page-53 source PDF hash drifted")
    if sha256_file(schema_workbook_path) != policy.schema_workbook_sha256:
        raise TMPage53MappingError("TM page-53 schema workbook hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != TM_PAGE53_SCHEMA_TOTAL:
        raise TMPage53MappingError("TM page-53 schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if set(policy.scope_schema_ids) != _SCOPE_IDS:
        raise TMPage53MappingError("TM page-53 policy scope IDs drifted")
    _validate_schema_branch(schema_by_id)

    structural_by_role = {
        target.source_role: target.report_norm_id for target in policy.structural_targets
    }
    axis_parent_ids = dict(policy.axis_parent_ids)
    metric_target_ids = dict(policy.metric_target_ids)
    if tuple(axis.axis_key for axis in parsed.axes) != _AXIS_KEYS:
        raise TMPage53MappingError("TM page-53 parsed axes drifted")
    expected_roles = (
        "SEGMENT_REPORT_ROOT",
        "GEOGRAPHIC_SEGMENT_TITLE",
        *(f"{role}_{metric}" for role in ("CURRENT", "COMPARATIVE") for metric in _METRIC_KEYS),
    )
    if tuple(row.source_role for row in parsed.rows) != expected_roles:
        raise TMPage53MappingError("TM page-53 source row order drifted")

    source_by_schema: dict[int, list[str]] = {schema_id: [] for schema_id in _SCOPE_IDS}
    source_dispositions = []
    assignments = []
    for row in parsed.rows:
        if row.metric_key is None:
            target = structural_by_role.get(row.source_role)
            if target is None:
                raise TMPage53MappingError("TM page-53 structural row target is absent")
            report_norm_ids = (target,)
            source_by_schema[target].append(row.row_id)
        else:
            report_norm_ids = metric_target_ids[row.metric_key]
            if len(report_norm_ids) != len(parsed.axes):
                raise TMPage53MappingError("TM page-53 numeric target width drifted")
            for index, (axis, schema_id, cell) in enumerate(
                zip(parsed.axes, report_norm_ids, row.row.cells, strict=True)
            ):
                start = row.cell_period_starts[index]
                end = row.cell_period_ends[index]
                role = row.cell_period_roles[index]
                period_type = row.cell_period_types[index]
                if (
                    start is None
                    or end is None
                    or role is None
                    or period_type is None
                    or row.metric_key is None
                ):
                    raise TMPage53MappingError("TM page-53 assignment period is absent")
                if cell.observation not in {
                    ObservationKind.VALUE,
                    ObservationKind.ZERO,
                    ObservationKind.DASH,
                }:
                    raise TMPage53MappingError("TM page-53 assignment observation drifted")
                source_by_schema[schema_id].append(row.row_id)
                assignments.append(
                    TMPage53MappedAssignment(
                        source_row_id=row.row_id,
                        source_role=row.source_role,
                        metric_key=row.metric_key,
                        period_role=role,
                        period_type=period_type,
                        cell_index=index,
                        axis_key=axis.axis_key,
                        report_norm_id=schema_id,
                        observation=cell.observation.value,
                        value=cell.value,
                        period_start=start.isoformat(),
                        period_end=end.isoformat(),
                        unit=axis.canonical_unit,
                        unit_multiplier=axis.unit_multiplier,
                        mapping_basis=(
                            "VISIBLE_METRIC_ROW_X_FIXED_GEOGRAPHIC_AXIS_TRANSPOSE_TO_FROZEN_SCHEMA"
                        ),
                    )
                )
        source_dispositions.append(
            _source_disposition(
                row,
                report_norm_ids,
                unit=parsed.axes[0].canonical_unit,
                unit_multiplier=parsed.axes[0].unit_multiplier,
            )
        )
    for axis in parsed.axes:
        source_by_schema[axis_parent_ids[axis.axis_key]].extend(
            f"{parsed.page_tag}:line-{index:04d}" for index in axis.header_line_indices
        )
    if any(not source_by_schema[schema_id] for schema_id in _SCOPE_IDS):
        raise TMPage53MappingError("TM page-53 mapped schema item lacks source provenance")

    checks = _validations(parsed, policy)
    if (
        len(checks) != TM_PAGE53_VALIDATION_CHECK_COUNT
        or sum(check.status == "PASS" for check in checks) != TM_PAGE53_VALIDATION_PASS_COUNT
        or sum(check.status.startswith("NOT_TESTABLE") for check in checks)
        != TM_PAGE53_VALIDATION_NOT_TESTABLE_COUNT
        or any(
            check.status == "FAIL"
            or (check.status == "PASS" and check.residual != 0)
            or (check.status.startswith("NOT_TESTABLE") and check.residual is not None)
            for check in checks
        )
    ):
        raise TMPage53MappingError("TM page-53 accounting validation failed")
    schema_dispositions = tuple(
        TMPage53SchemaDisposition(
            report_norm_id=item.schema_id,
            display_order=item.display_order,
            canonical_name=item.canonical_name,
            status=(
                TMPage53SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
                if item.schema_id in _SCOPE_IDS
                else TMPage53SchemaStatus.UNASSESSED.value
            ),
            source_ids=tuple(dict.fromkeys(source_by_schema.get(item.schema_id, ()))),
            reason=(
                "page 53 is the unique scoped owner of this exact structural or value-bearing item"
                if item.schema_id in _SCOPE_IDS
                else "outside the page-53 owned schema branch"
            ),
        )
        for item in tm_schema
    )
    result = TMPage53MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=53,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="PAGE53_IDS_5762_5805_MAPPED_WITH_PRINTED_VALUES_DASHES_AND_VALIDATION",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=TM_PAGE53_SCOPE_SCHEMA_COUNT,
        mapped_schema_count=TM_PAGE53_MAPPED_SCHEMA_COUNT,
        structural_mapped_schema_count=TM_PAGE53_STRUCTURAL_MAPPED_SCHEMA_COUNT,
        value_bearing_mapped_schema_count=TM_PAGE53_VALUE_BEARING_MAPPED_SCHEMA_COUNT,
        not_observed_schema_count=0,
        not_applicable_schema_count=0,
        ambiguous_schema_count=0,
        unresolved_schema_count=0,
        unassessed_schema_count=TM_PAGE53_UNASSESSED_SCHEMA_COUNT,
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=len(source_dispositions),
        structural_source_row_count=sum(item.metric_key is None for item in source_dispositions),
        numeric_source_row_count=sum(item.metric_key is not None for item in source_dispositions),
        source_question_row_count=0,
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_assignment_count=len(assignments),
        validation_check_count=len(checks),
        validation_pass_count=sum(check.status == "PASS" for check in checks),
        validation_not_testable_count=sum(
            check.status.startswith("NOT_TESTABLE") for check in checks
        ),
        schema_dispositions=schema_dispositions,
        source_dispositions=tuple(source_dispositions),
        mapped_assignments=tuple(assignments),
        validation_checks=checks,
        total_formulas_validation_only=policy.total_formulas,
        pbt_formulas_validation_only=policy.pbt_formulas,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        upstream_ocr_sha256=policy.upstream_ocr_sha256,
        schema_workbook_sha256=policy.schema_workbook_sha256,
        schema_projection_sha256=_schema_projection_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS_AND_GEOMETRY",
            "VISIBLE_PAGE53_AXIS_AND_METRIC_ORDER",
            "ROW_LOCAL_SNAPSHOT_OR_DURATION_PERIOD_BINDING",
            "PIXEL_BACKED_DASH_STATUS_WITHOUT_ZERO_COERCION",
            "FROZEN_TM_SCHEMA_IDS_5762_THROUGH_5805_NAME_ORDER_AND_HIERARCHY",
            "ACCOUNTING_FORMULAS_AS_POST_MAPPING_VALIDATION_ONLY",
            "PAGE54_TOTALS_AS_EXTERNAL_VALIDATION_ONLY_NOT_MAPPING_OR_IMPUTATION",
        ),
    )
    return validate_tm_page53_mapping_result(result)


def validate_tm_page53_mapping_result(
    result: TMPage53MappingResult,
) -> TMPage53MappingResult:
    if (
        result.schema_item_count != TM_PAGE53_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE53_SCOPE_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE53_MAPPED_SCHEMA_COUNT
        or result.structural_mapped_schema_count != TM_PAGE53_STRUCTURAL_MAPPED_SCHEMA_COUNT
        or result.value_bearing_mapped_schema_count != TM_PAGE53_VALUE_BEARING_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != 0
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != 0
        or result.unresolved_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE53_UNASSESSED_SCHEMA_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE53_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE53_SOURCE_ROW_COUNT
        or result.structural_source_row_count != TM_PAGE53_STRUCTURAL_SOURCE_ROW_COUNT
        or result.numeric_source_row_count != TM_PAGE53_NUMERIC_SOURCE_ROW_COUNT
        or result.source_question_row_count != 0
        or result.financial_slot_count != TM_PAGE53_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE53_VALUE_COUNT
        or result.dash_count != TM_PAGE53_DASH_COUNT
        or result.mapped_assignment_count != TM_PAGE53_ASSIGNMENT_COUNT
        or result.validation_check_count != TM_PAGE53_VALIDATION_CHECK_COUNT
        or result.validation_pass_count != TM_PAGE53_VALIDATION_PASS_COUNT
        or result.validation_not_testable_count != TM_PAGE53_VALIDATION_NOT_TESTABLE_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage53MappingError("TM page-53 mapping denominator drifted")
    if result.status_reconciled_schema_count + result.unassessed_schema_count != (
        result.schema_item_count
    ):
        raise TMPage53MappingError("TM page-53 schema statuses do not reconcile")
    mapped = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage53SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    unassessed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage53SchemaStatus.UNASSESSED.value
    }
    if (
        mapped != _SCOPE_IDS
        or len(unassessed) != TM_PAGE53_UNASSESSED_SCHEMA_COUNT
        or mapped & unassessed
        or any(
            not item.source_ids
            for item in result.schema_dispositions
            if item.report_norm_id in _SCOPE_IDS
        )
        or any(
            item.source_ids
            for item in result.schema_dispositions
            if item.report_norm_id not in _SCOPE_IDS
        )
    ):
        raise TMPage53MappingError("TM page-53 schema disposition partition drifted")
    if (
        any(
            item.status != TMPage53SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in result.source_dispositions
        )
        or any(item.question_required for item in result.source_dispositions)
        or tuple(item.source_role for item in result.source_dispositions[:2])
        != ("SEGMENT_REPORT_ROOT", "GEOGRAPHIC_SEGMENT_TITLE")
        or tuple(item.report_norm_ids for item in result.source_dispositions[:2])
        != ((5762,), (5763,))
    ):
        raise TMPage53MappingError("TM page-53 source dispositions drifted")
    assignment_ids = {item.report_norm_id for item in result.mapped_assignments}
    dash_assignments = tuple(
        item for item in result.mapped_assignments if item.observation == ObservationKind.DASH.value
    )
    if (
        assignment_ids != _VALUE_IDS
        or any(
            sum(item.report_norm_id == schema_id for item in result.mapped_assignments) != 2
            for schema_id in _VALUE_IDS
        )
        or len(dash_assignments) != 4
        or {item.report_norm_id for item in dash_assignments} != {5795, 5798}
        or any(
            item.value is not None or item.axis_key != "ELIMINATION" for item in dash_assignments
        )
        or sum(
            item.observation == ObservationKind.VALUE.value for item in result.mapped_assignments
        )
        != 68
    ):
        raise TMPage53MappingError("TM page-53 mapped assignments drifted")
    kinds = tuple(check.check_kind for check in result.validation_checks)
    if (
        kinds.count("SEGMENT_SUM_VALIDATION_ONLY") != 12
        or kinds.count("PBT_SUBTRACTION_VALIDATION_ONLY") != 12
        or kinds.count("EXTERNAL_PAGE54_TOTAL_VALIDATION_ONLY") != 12
        or sum(
            check.status == "PASS"
            for check in result.validation_checks
            if check.check_kind == "SEGMENT_SUM_VALIDATION_ONLY"
        )
        != 8
        or sum(
            check.status.startswith("NOT_TESTABLE")
            for check in result.validation_checks
            if check.check_kind == "SEGMENT_SUM_VALIDATION_ONLY"
        )
        != 4
        or sum(
            check.status == "PASS"
            for check in result.validation_checks
            if check.check_kind == "PBT_SUBTRACTION_VALIDATION_ONLY"
        )
        != 10
        or sum(
            check.status.startswith("NOT_TESTABLE")
            for check in result.validation_checks
            if check.check_kind == "PBT_SUBTRACTION_VALIDATION_ONLY"
        )
        != 2
        or any(
            check.status != "PASS" or check.residual != 0
            for check in result.validation_checks
            if check.check_kind == "EXTERNAL_PAGE54_TOTAL_VALIDATION_ONLY"
        )
        or any(
            check.status == "FAIL"
            or (check.status == "PASS" and check.residual != 0)
            or (check.status.startswith("NOT_TESTABLE") and check.residual is not None)
            for check in result.validation_checks
        )
        or any(
            check.external_owner_scope != "page-0054"
            for check in result.validation_checks
            if check.check_kind == "EXTERNAL_PAGE54_TOTAL_VALIDATION_ONLY"
        )
    ):
        raise TMPage53MappingError("TM page-53 validation result drifted")
    if (
        dict(result.total_formulas_validation_only) != _EXPECTED_TOTAL_FORMULAS
        or dict(result.pbt_formulas_validation_only) != _EXPECTED_PBT_FORMULAS
    ):
        raise TMPage53MappingError("TM page-53 validation formula result drifted")
    return result


__all__ = [
    "TM_PAGE53_MAPPING_POLICY_RELATIVE_PATH",
    "TMPage53MappedAssignment",
    "TMPage53MappingError",
    "TMPage53MappingPolicy",
    "TMPage53MappingResult",
    "TMPage53SchemaDisposition",
    "TMPage53SchemaStatus",
    "TMPage53SourceDisposition",
    "TMPage53SourceStatus",
    "TMPage53ValidationCheck",
    "load_tm_page53_mapping_policy",
    "reconcile_tm_page53_items",
    "validate_tm_page53_mapping_result",
]
