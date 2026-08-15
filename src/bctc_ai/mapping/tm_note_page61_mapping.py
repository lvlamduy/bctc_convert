"""Hierarchy-safe mapping for MBB consolidated TM page 61 exchange rates."""

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
from bctc_ai.tables.tm_note_page61 import ParsedTMPage61

TM_PAGE61_MAPPING_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page61-v1.yaml")
TM_PAGE61_SCHEMA_TOTAL = 1_714
TM_PAGE61_SCOPE_SCHEMA_COUNT = 11
TM_PAGE61_MAPPED_SCHEMA_COUNT = 11
TM_PAGE61_STRUCTURAL_MAPPED_SCHEMA_COUNT = 1
TM_PAGE61_VALUE_BEARING_MAPPED_SCHEMA_COUNT = 10
TM_PAGE61_NOT_OBSERVED_SCHEMA_COUNT = 0
TM_PAGE61_UNASSESSED_SCHEMA_COUNT = 1_703
TM_PAGE61_SOURCE_ROW_COUNT = 10
TM_PAGE61_FINANCIAL_SLOT_COUNT = 20
TM_PAGE61_VALUE_COUNT = 20
TM_PAGE61_ASSIGNMENT_COUNT = 20

TM_PAGE61_SCOPE_IDS = frozenset(range(5935, 5946))
TM_PAGE61_MAPPED_SCHEMA_IDS = TM_PAGE61_SCOPE_IDS
TM_PAGE61_NOT_OBSERVED_SCHEMA_IDS: frozenset[int] = frozenset()

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ROOT_ID = 5935
_ROOT_PARENT_ID = 1259
_CURRENCY_KEYS = ("USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "SGD", "THB", "SEK")
_CURRENCY_TARGET_IDS = {code: 5936 + index for index, code in enumerate(_CURRENCY_KEYS)}
_ROOT_CHILDREN = tuple(_CURRENCY_TARGET_IDS.values())
_PERIOD_CONTRACT = (
    ("CURRENT", "SNAPSHOT", "2026-03-31", "2026-03-31", "2026-03-31"),
    ("PRIOR", "SNAPSHOT", "2025-12-31", "2025-12-31", "2025-12-31"),
)
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text_as_item_selector",
    "numeric_value_magnitude_as_item_selector",
    "historical_or_mongodb_values",
    "human_review_answers",
    "vnd_million_multiplier",
    "decimal_comma_loss_or_integer_rounding",
    "period_axis_swapping",
    "schema_id_outside_page61_scope",
    "page60_value_as_page61_item_selector",
    "page60_value_as_page61_imputation",
    "accounting_equation_result_as_item_selector",
    "accounting_equation_result_as_extracted_value",
}


class TMPage61MappingError(ValueError):
    pass


class TMPage61SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    UNASSESSED = "UNASSESSED"


@dataclass(frozen=True)
class TMPage61MappingPolicy:
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
    schema_projection_sha256: str
    schema_total: int
    scope_schema_ids: tuple[int, ...]
    schema_scope_sha256: str
    root_report_norm_id: int
    currency_target_ids: tuple[tuple[str, int], ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage61SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage61SourceDisposition:
    row_id: str
    ordinal: int
    currency_code: str
    status: str
    report_norm_id: int
    observations: tuple[str, ...]
    raw_values: tuple[str, ...]
    values: tuple[Decimal, ...]
    period_starts: tuple[str, ...]
    period_ends: tuple[str, ...]
    period_roles: tuple[str, ...]
    period_types: tuple[str, ...]
    unit: str
    unit_multiplier: int
    unit_denominator: str
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage61MappedAssignment:
    source_row_id: str
    currency_code: str
    cell_index: int
    report_norm_id: int
    observation: str
    raw_value: str
    value: Decimal
    period_start: str
    period_end: str
    period_role: str
    period_type: str
    unit: str
    unit_multiplier: int
    unit_denominator: str
    mapping_basis: str


@dataclass(frozen=True)
class TMPage61MappingResult:
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
    source_question_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_assignment_count: int
    validation_check_count: int
    validation_pass_count: int
    validation_not_testable_count: int
    schema_dispositions: tuple[TMPage61SchemaDisposition, ...]
    source_dispositions: tuple[TMPage61SourceDisposition, ...]
    mapped_assignments: tuple[TMPage61MappedAssignment, ...]
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
        raise TMPage61MappingError(f"invalid positive TM page-61 field: {field}")
    return value


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
        (
            schema_id,
            schema_by_id[schema_id].canonical_name,
            schema_by_id[schema_id].parent_id,
            tuple(schema_by_id[schema_id].children),
        )
        for schema_id in sorted(TM_PAGE61_SCOPE_IDS)
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_tm_page61_mapping_policy(path: Path) -> TMPage61MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage61MappingError(f"cannot load TM page-61 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE61_EXCHANGE_RATE_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("document") != "MBB_CONSOLIDATED_Q1_2026"
        or payload.get("page_number") != 61
        or payload.get("page_tag") != "page-0061"
        or payload.get("report_scope") != "CONSOLIDATED"
        or payload.get("mapping_authority_scope")
        != "MBB_CONSOLIDATED_Q1_2026_PAGE61_IDS_5935_5945_ONLY"
    ):
        raise TMPage61MappingError("TM page-61 mapping identity drifted")
    hash_fields = (
        "source_table_policy_sha256",
        "source_pdf_sha256",
        "source_render_sha256",
        "source_ocr_sha256",
        "upstream_ocr_sha256",
        "schema_workbook_sha256",
        "schema_projection_sha256",
        "schema_scope_sha256",
    )
    hashes = tuple(payload.get(field) for field in hash_fields)
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage61MappingError("TM page-61 mapping hashes are invalid")
    table_policy = payload.get("source_table_policy")
    if table_policy != "config/tables/tm-note-page61-v1.yaml":
        raise TMPage61MappingError("TM page-61 source table policy path drifted")
    table_path = (path.parents[2] / str(table_policy)).resolve()
    if not table_path.is_file() or sha256_file(table_path) != hashes[0]:
        raise TMPage61MappingError("TM page-61 source table policy hash drifted")
    if (
        payload.get("schema_total") != TM_PAGE61_SCHEMA_TOTAL
        or payload.get("scope_schema_ids") != [{"start": 5935, "end": 5945}]
        or payload.get("scope_schema_total") != TM_PAGE61_SCOPE_SCHEMA_COUNT
        or payload.get("root_report_norm_id") != _ROOT_ID
    ):
        raise TMPage61MappingError("TM page-61 schema denominator/scope drifted")
    raw_targets = payload.get("currency_target_ids")
    if not isinstance(raw_targets, dict) or tuple(raw_targets) != _CURRENCY_KEYS:
        raise TMPage61MappingError("TM page-61 currency target order drifted")
    targets = tuple((str(key), value) for key, value in raw_targets.items())
    if (
        any(isinstance(value, bool) or not isinstance(value, int) for _, value in targets)
        or dict(targets) != _CURRENCY_TARGET_IDS
    ):
        raise TMPage61MappingError("TM page-61 currency targets drifted")
    if payload.get("hierarchy_contract") != {
        "parent_report_norm_id": _ROOT_PARENT_ID,
        "root_children": list(_ROOT_CHILDREN),
        "leaf_children": [],
    }:
        raise TMPage61MappingError("TM page-61 hierarchy contract drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage61MappingError("TM page-61 forbidden inputs drifted")
    return TMPage61MappingPolicy(
        source_path=path,
        document=str(payload["document"]),
        page_number=_positive_int(payload, "page_number"),
        page_tag=str(payload["page_tag"]),
        report_scope=str(payload["report_scope"]),
        mapping_authority_scope=str(payload["mapping_authority_scope"]),
        source_table_policy=str(table_policy),
        source_table_policy_sha256=str(hashes[0]),
        source_pdf_sha256=str(hashes[1]),
        source_render_sha256=str(hashes[2]),
        source_ocr_sha256=str(hashes[3]),
        upstream_ocr_sha256=str(hashes[4]),
        schema_workbook_sha256=str(hashes[5]),
        schema_projection_sha256=str(hashes[6]),
        schema_total=TM_PAGE61_SCHEMA_TOTAL,
        scope_schema_ids=tuple(sorted(TM_PAGE61_SCOPE_IDS)),
        schema_scope_sha256=str(hashes[7]),
        root_report_norm_id=_ROOT_ID,
        currency_target_ids=targets,
        forbidden_mapping_inputs=tuple(str(item) for item in forbidden),
        policy_sha256=sha256_file(path),
    )


def _validate_schema_branch(schema_by_id: dict[int, SchemaItem]) -> None:
    root = schema_by_id[_ROOT_ID]
    if root.parent_id != _ROOT_PARENT_ID or tuple(root.children) != _ROOT_CHILDREN:
        raise TMPage61MappingError("TM page-61 exchange-rate root hierarchy drifted")
    for code, schema_id in _CURRENCY_TARGET_IDS.items():
        item = schema_by_id[schema_id]
        if item.parent_id != _ROOT_ID or item.children or item.canonical_name != code:
            raise TMPage61MappingError(f"TM page-61 currency hierarchy drifted: {code}")


def reconcile_tm_page61_items(
    parsed: ParsedTMPage61,
    *,
    schema: Sequence[SchemaItem],
    policy: TMPage61MappingPolicy,
    source_pdf_path: Path,
    schema_workbook_path: Path,
) -> TMPage61MappingResult:
    if (
        policy.mapping_authority_scope != "MBB_CONSOLIDATED_Q1_2026_PAGE61_IDS_5935_5945_ONLY"
        or policy.root_report_norm_id != _ROOT_ID
        or dict(policy.currency_target_ids) != _CURRENCY_TARGET_IDS
        or set(policy.forbidden_mapping_inputs) != _REQUIRED_FORBIDDEN
    ):
        raise TMPage61MappingError("TM page-61 mapping policy target drifted")
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
        or parsed.upstream_ocr_sha256 != policy.upstream_ocr_sha256
    ):
        raise TMPage61MappingError("TM page-61 parser/mapping identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage61MappingError("TM page-61 source PDF hash drifted")
    if sha256_file(schema_workbook_path) != policy.schema_workbook_sha256:
        raise TMPage61MappingError("TM page-61 schema workbook hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != TM_PAGE61_SCHEMA_TOTAL or len(tm_schema) != policy.schema_total:
        raise TMPage61MappingError("TM page-61 schema denominator drifted")
    projection_hash = _schema_projection_hash(tm_schema)
    if projection_hash != policy.schema_projection_sha256:
        raise TMPage61MappingError("TM page-61 full schema projection drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if (
        set(policy.scope_schema_ids) != TM_PAGE61_SCOPE_IDS
        or _schema_scope_hash(schema_by_id) != policy.schema_scope_sha256
    ):
        raise TMPage61MappingError("TM page-61 owned schema scope drifted")
    _validate_schema_branch(schema_by_id)
    if (
        tuple(row.currency_code for row in parsed.rows) != _CURRENCY_KEYS
        or tuple(
            (
                period.period_role,
                period.period_type,
                period.period_start.isoformat(),
                period.period_end.isoformat(),
                period.visible_date.isoformat(),
            )
            for period in parsed.periods
        )
        != _PERIOD_CONTRACT
        or {
            (period.canonical_unit, period.unit_multiplier, period.unit_denominator)
            for period in parsed.periods
        }
        != {("VND", 1, "ONE_UNIT_OF_ROW_CURRENCY")}
    ):
        raise TMPage61MappingError("TM page-61 parsed currency/period/unit order drifted")

    targets = dict(policy.currency_target_ids)
    source_by_schema: dict[int, list[str]] = {schema_id: [] for schema_id in TM_PAGE61_SCOPE_IDS}
    source_by_schema[_ROOT_ID].append(f"{parsed.page_tag}:line-{parsed.table.title_line_index:04d}")
    assignments: list[TMPage61MappedAssignment] = []
    source_dispositions: list[TMPage61SourceDisposition] = []
    for row in parsed.rows:
        row_period_contract = tuple(
            (
                role,
                period_type,
                start.isoformat(),
                end.isoformat(),
                parsed.periods[index].visible_date.isoformat(),
            )
            for index, (role, period_type, start, end) in enumerate(
                zip(
                    row.cell_period_roles,
                    row.cell_period_types,
                    row.cell_period_starts,
                    row.cell_period_ends,
                    strict=True,
                )
            )
        )
        if row_period_contract != _PERIOD_CONTRACT:
            raise TMPage61MappingError("TM page-61 row/header period alignment drifted")
        schema_id = targets[row.currency_code]
        source_by_schema[schema_id].append(row.row_id)
        for index, (period, cell) in enumerate(zip(parsed.periods, row.row.cells, strict=True)):
            if (
                cell.observation is not ObservationKind.VALUE
                or cell.value is None
                or "," not in cell.raw_text
                or cell.value.as_tuple().exponent != -2
                or row.cell_unit_denominators[index] != "ONE_UNIT_OF_ROW_CURRENCY"
            ):
                raise TMPage61MappingError("TM page-61 decimal-comma VALUE assignment drifted")
            assignments.append(
                TMPage61MappedAssignment(
                    source_row_id=row.row_id,
                    currency_code=row.currency_code,
                    cell_index=index,
                    report_norm_id=schema_id,
                    observation=cell.observation.value,
                    raw_value=cell.raw_text,
                    value=cell.value,
                    period_start=row.cell_period_starts[index].isoformat(),
                    period_end=row.cell_period_ends[index].isoformat(),
                    period_role=row.cell_period_roles[index],
                    period_type=row.cell_period_types[index],
                    unit=period.canonical_unit,
                    unit_multiplier=period.unit_multiplier,
                    unit_denominator=row.cell_unit_denominators[index],
                    mapping_basis=(
                        "VISIBLE_PAGE61_CURRENCY_ROW_X_FIXED_SNAPSHOT_PERIOD_TO_FROZEN_SCHEMA"
                    ),
                )
            )
        source_dispositions.append(
            TMPage61SourceDisposition(
                row_id=row.row_id,
                ordinal=row.ordinal,
                currency_code=row.currency_code,
                status=TMPage61SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value,
                report_norm_id=schema_id,
                observations=tuple(cell.observation.value for cell in row.row.cells),
                raw_values=tuple(cell.raw_text for cell in row.row.cells),
                values=tuple(cell.value for cell in row.row.cells if cell.value is not None),
                period_starts=tuple(value.isoformat() for value in row.cell_period_starts),
                period_ends=tuple(value.isoformat() for value in row.cell_period_ends),
                period_roles=row.cell_period_roles,
                period_types=row.cell_period_types,
                unit="VND",
                unit_multiplier=1,
                unit_denominator="ONE_UNIT_OF_ROW_CURRENCY",
                question_required=False,
                reason=(
                    "visible currency code uniquely binds both printed period values; decimal-comma "
                    "precision, period axes, and native VND-per-currency-unit semantics are preserved"
                ),
            )
        )
    if any(not source_by_schema[schema_id] for schema_id in TM_PAGE61_SCOPE_IDS):
        raise TMPage61MappingError("TM page-61 mapped item lacks source provenance")
    schema_dispositions = tuple(
        TMPage61SchemaDisposition(
            report_norm_id=item.schema_id,
            display_order=item.display_order,
            canonical_name=item.canonical_name,
            status=(
                TMPage61SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
                if item.schema_id in TM_PAGE61_SCOPE_IDS
                else TMPage61SchemaStatus.UNASSESSED.value
            ),
            source_ids=tuple(dict.fromkeys(source_by_schema.get(item.schema_id, ()))),
            reason=(
                "page 61 is the unique scoped owner of this exchange-rate structural or currency item"
                if item.schema_id in TM_PAGE61_SCOPE_IDS
                else "outside the page-61 owned exchange-rate schema scope"
            ),
        )
        for item in tm_schema
    )
    result = TMPage61MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=61,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="PAGE61_EXCHANGE_RATE_SCOPE_RECONCILED_MAPPED",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=TM_PAGE61_SCOPE_SCHEMA_COUNT,
        mapped_schema_count=TM_PAGE61_MAPPED_SCHEMA_COUNT,
        structural_mapped_schema_count=TM_PAGE61_STRUCTURAL_MAPPED_SCHEMA_COUNT,
        value_bearing_mapped_schema_count=TM_PAGE61_VALUE_BEARING_MAPPED_SCHEMA_COUNT,
        not_observed_schema_count=0,
        not_applicable_schema_count=0,
        ambiguous_schema_count=0,
        unresolved_schema_count=0,
        unassessed_schema_count=TM_PAGE61_UNASSESSED_SCHEMA_COUNT,
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=len(source_dispositions),
        source_question_row_count=0,
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_assignment_count=len(assignments),
        validation_check_count=0,
        validation_pass_count=0,
        validation_not_testable_count=0,
        schema_dispositions=schema_dispositions,
        source_dispositions=tuple(source_dispositions),
        mapped_assignments=tuple(assignments),
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        upstream_ocr_sha256=policy.upstream_ocr_sha256,
        schema_workbook_sha256=policy.schema_workbook_sha256,
        schema_projection_sha256=projection_hash,
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_CURRENCY_LABELS_AND_GEOMETRY",
            "VISIBLE_PAGE61_CURRENCY_ROW_AND_FIXED_SNAPSHOT_PERIOD_ORDER",
            "VISIBLE_NATIVE_VND_PER_ONE_UNIT_OF_ROW_CURRENCY",
            "DECIMAL_COMMA_PRECISION_PRESERVED_WITHOUT_INTEGER_ROUNDING",
            "FROZEN_TM_SCHEMA_SCOPE_IDS_5935_THROUGH_5945",
            "PAGE60_AS_DISJOINT_INDEPENDENT_OWNER",
        ),
    )
    return validate_tm_page61_mapping_result(result)


def validate_tm_page61_mapping_result(result: TMPage61MappingResult) -> TMPage61MappingResult:
    if (
        result.schema_item_count != TM_PAGE61_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE61_SCOPE_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE61_MAPPED_SCHEMA_COUNT
        or result.structural_mapped_schema_count != TM_PAGE61_STRUCTURAL_MAPPED_SCHEMA_COUNT
        or result.value_bearing_mapped_schema_count != TM_PAGE61_VALUE_BEARING_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != 0
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != 0
        or result.unresolved_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE61_UNASSESSED_SCHEMA_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE61_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE61_SOURCE_ROW_COUNT
        or result.source_question_row_count != 0
        or result.financial_slot_count != TM_PAGE61_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE61_VALUE_COUNT
        or result.dash_count != 0
        or result.mapped_assignment_count != TM_PAGE61_ASSIGNMENT_COUNT
        or result.validation_check_count != 0
        or result.validation_pass_count != 0
        or result.validation_not_testable_count != 0
        or not result.mapping_authority_granted
    ):
        raise TMPage61MappingError("TM page-61 mapping denominator drifted")
    mapped = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage61SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    unassessed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage61SchemaStatus.UNASSESSED.value
    }
    if (
        result.status_reconciled_schema_count + result.unassessed_schema_count
        != result.schema_item_count
        or mapped != TM_PAGE61_MAPPED_SCHEMA_IDS
        or len(unassessed) != TM_PAGE61_UNASSESSED_SCHEMA_COUNT
        or mapped | unassessed != {item.report_norm_id for item in result.schema_dispositions}
        or any(
            not item.source_ids
            for item in result.schema_dispositions
            if item.report_norm_id in mapped
        )
        or any(
            item.source_ids
            for item in result.schema_dispositions
            if item.report_norm_id not in mapped
        )
        or any(item.question_required for item in result.source_dispositions)
    ):
        raise TMPage61MappingError("TM page-61 disposition partition drifted")
    if (
        {item.report_norm_id for item in result.mapped_assignments}
        != set(_CURRENCY_TARGET_IDS.values())
        or {item.observation for item in result.mapped_assignments} != {ObservationKind.VALUE.value}
        or {
            (item.unit, item.unit_multiplier, item.unit_denominator)
            for item in result.mapped_assignments
        }
        != {("VND", 1, "ONE_UNIT_OF_ROW_CURRENCY")}
        or {item.period_role for item in result.mapped_assignments} != {"CURRENT", "PRIOR"}
        or {item.period_type for item in result.mapped_assignments} != {"SNAPSHOT"}
        or {
            (item.period_role, item.period_type, item.period_start, item.period_end)
            for item in result.mapped_assignments
        }
        != {
            ("CURRENT", "SNAPSHOT", "2026-03-31", "2026-03-31"),
            ("PRIOR", "SNAPSHOT", "2025-12-31", "2025-12-31"),
        }
        or sum(item.period_role == "CURRENT" for item in result.mapped_assignments) != 10
        or sum(item.period_role == "PRIOR" for item in result.mapped_assignments) != 10
        or any(
            "," not in item.raw_value or item.value.as_tuple().exponent != -2
            for item in result.mapped_assignments
        )
    ):
        raise TMPage61MappingError("TM page-61 assignment partition drifted")
    return result


__all__ = [
    "TM_PAGE61_MAPPING_POLICY_RELATIVE_PATH",
    "TM_PAGE61_MAPPED_SCHEMA_IDS",
    "TM_PAGE61_NOT_OBSERVED_SCHEMA_IDS",
    "TM_PAGE61_SCOPE_IDS",
    "TMPage61MappedAssignment",
    "TMPage61MappingError",
    "TMPage61MappingPolicy",
    "TMPage61MappingResult",
    "TMPage61SchemaDisposition",
    "TMPage61SchemaStatus",
    "TMPage61SourceDisposition",
    "load_tm_page61_mapping_policy",
    "reconcile_tm_page61_items",
    "validate_tm_page61_mapping_result",
]
