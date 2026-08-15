"""Hierarchy-safe mapping for MBB consolidated TM page 58 currency risk."""

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
from bctc_ai.tables.tm_note_page58 import ParsedTMPage58

TM_PAGE58_MAPPING_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page58-v1.yaml")
TM_PAGE58_SCHEMA_TOTAL = 1_712
TM_PAGE58_SCOPE_SCHEMA_COUNT = 139
TM_PAGE58_MAPPED_SCHEMA_COUNT = 77
TM_PAGE58_STRUCTURAL_MAPPED_SCHEMA_COUNT = 5
TM_PAGE58_VALUE_BEARING_MAPPED_SCHEMA_COUNT = 72
TM_PAGE58_NOT_OBSERVED_SCHEMA_COUNT = 62
TM_PAGE58_UNASSESSED_SCHEMA_COUNT = 1_573
TM_PAGE58_SOURCE_ROW_COUNT = 20
TM_PAGE58_MAPPED_SOURCE_ROW_COUNT = 18
TM_PAGE58_SOURCE_ONLY_ROW_COUNT = 2
TM_PAGE58_FINANCIAL_SLOT_COUNT = 72
TM_PAGE58_VALUE_COUNT = 63
TM_PAGE58_DASH_COUNT = 9
TM_PAGE58_ASSIGNMENT_COUNT = 72
TM_PAGE58_VALIDATION_CHECK_COUNT = 34
TM_PAGE58_VALIDATION_PASS_COUNT = 26
TM_PAGE58_VALIDATION_NOT_TESTABLE_COUNT = 8

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_AXIS_KEYS = (
    "USD",
    "EUR",
    "OTHER_FOREIGN_CURRENCIES",
    "TOTAL",
)
_METRIC_KEYS = (
    "CASH_AND_PRECIOUS_METALS",
    "SBV_DEPOSITS",
    "INTERBANK_ASSETS",
    "DERIVATIVE_ASSETS",
    "CUSTOMER_LOANS",
    "INVESTMENT_SECURITIES",
    "LONG_TERM_INVESTMENTS",
    "FIXED_ASSETS_AND_INVESTMENT_PROPERTY",
    "OTHER_ASSETS",
    "TOTAL_ASSETS",
    "INTERBANK_LIABILITIES",
    "CUSTOMER_DEPOSITS",
    "DERIVATIVE_LIABILITIES",
    "OTHER_LIABILITIES",
    "TOTAL_LIABILITIES",
    "ON_BALANCE_CURRENCY_POSITION",
    "OFF_BALANCE_CURRENCY_POSITION",
    "COMBINED_CURRENCY_POSITION",
)
_ASSET_DETAIL_METRICS = _METRIC_KEYS[:9]
_LIABILITY_DETAIL_METRICS = _METRIC_KEYS[10:14]
_ROOT_ID = 1352
_AXIS_PARENT_IDS = {
    "USD": 1379,
    "EUR": 1353,
    "OTHER_FOREIGN_CURRENCIES": 1431,
    "TOTAL": 1457,
}
_METRIC_TARGET_IDS = {
    "CASH_AND_PRECIOUS_METALS": (1381, 1355, 1433, 1459),
    "SBV_DEPOSITS": (1382, 1356, 1434, 1460),
    "INTERBANK_ASSETS": (1383, 1357, 1435, 1461),
    "DERIVATIVE_ASSETS": (1385, 1359, 1437, 1463),
    "CUSTOMER_LOANS": (1386, 1360, 1438, 1464),
    "INVESTMENT_SECURITIES": (1387, 1361, 1439, 1465),
    "LONG_TERM_INVESTMENTS": (1388, 1362, 1440, 1466),
    "FIXED_ASSETS_AND_INVESTMENT_PROPERTY": (5851, 5849, 5853, 5855),
    "OTHER_ASSETS": (1391, 1365, 1443, 1469),
    "TOTAL_ASSETS": (1380, 1354, 1432, 1458),
    "INTERBANK_LIABILITIES": (1395, 1369, 1447, 1473),
    "CUSTOMER_DEPOSITS": (1396, 1370, 1448, 1474),
    "DERIVATIVE_LIABILITIES": (1397, 1371, 1449, 1475),
    "OTHER_LIABILITIES": (1400, 1374, 1452, 1478),
    "TOTAL_LIABILITIES": (5852, 5850, 5854, 5856),
    "ON_BALANCE_CURRENCY_POSITION": (1402, 1376, 1454, 1480),
    "OFF_BALANCE_CURRENCY_POSITION": (1403, 1377, 1455, 1481),
    "COMBINED_CURRENCY_POSITION": (1404, 1378, 1456, 1482),
}
_SCOPE_IDS = set(range(1352, 1483)) | set(range(5849, 5857))
_VALUE_IDS = {schema_id for ids in _METRIC_TARGET_IDS.values() for schema_id in ids}
_STRUCTURAL_IDS = {_ROOT_ID, *_AXIS_PARENT_IDS.values()}
_MAPPED_IDS = _VALUE_IDS | _STRUCTURAL_IDS
_NOT_OBSERVED_IDS = _SCOPE_IDS - _MAPPED_IDS
_EXPECTED_NOT_OBSERVED_IDS = set(range(1405, 1431)) | {
    1358,
    1363,
    1364,
    1366,
    1367,
    1368,
    1372,
    1373,
    1375,
    1384,
    1389,
    1390,
    1392,
    1393,
    1394,
    1398,
    1399,
    1401,
    1436,
    1441,
    1442,
    1444,
    1445,
    1446,
    1450,
    1451,
    1453,
    1462,
    1467,
    1468,
    1470,
    1471,
    1472,
    1476,
    1477,
    1479,
}
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text_as_item_selector",
    "numeric_value_magnitude_as_item_selector",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
    "accounting_equation_result_as_extracted_value",
    "schema_id_outside_page58_scope",
    "page57_value_as_page58_item_selector",
    "page57_value_as_page58_imputation",
}
_EXPECTED_HIERARCHY_CONTRACT = {
    "combined_fixed_assets_and_investment_property": {
        "role": "PARENT_OF_TWO_EXISTING_COMPONENTS",
        "reparent_existing_components": True,
    },
    "total_liabilities": {
        "role": "CHILD_OF_LIABILITIES_AND_EQUITY_HEADER",
        "contains_existing_liability_subtree": True,
    },
}
_EXPECTED_VALIDATION_CONTRACT = [
    {
        "kind": "ROW_TOTAL_VALIDATION_ONLY",
        "checks": 18,
        "pass": 14,
        "not_testable_dash": 4,
    },
    {
        "kind": "ASSET_COMPOSITION_VALIDATION_ONLY",
        "checks": 4,
        "pass": 0,
        "not_testable_dash": 4,
    },
    {
        "kind": "LIABILITY_COMPOSITION_VALIDATION_ONLY",
        "checks": 4,
        "pass": 4,
        "not_testable_dash": 0,
    },
    {
        "kind": "ON_BALANCE_POSITION_VALIDATION_ONLY",
        "checks": 4,
        "pass": 4,
        "not_testable_dash": 0,
    },
    {
        "kind": "COMBINED_POSITION_VALIDATION_ONLY",
        "checks": 4,
        "pass": 4,
        "not_testable_dash": 0,
    },
]

if (
    len(_SCOPE_IDS) != TM_PAGE58_SCOPE_SCHEMA_COUNT
    or len(_MAPPED_IDS) != TM_PAGE58_MAPPED_SCHEMA_COUNT
    or len(_VALUE_IDS) != TM_PAGE58_VALUE_BEARING_MAPPED_SCHEMA_COUNT
    or _NOT_OBSERVED_IDS != _EXPECTED_NOT_OBSERVED_IDS
    or len(_NOT_OBSERVED_IDS) != TM_PAGE58_NOT_OBSERVED_SCHEMA_COUNT
):
    raise AssertionError("TM page-58 static scope partition drifted")


class TMPage58MappingError(ValueError):
    pass


class TMPage58SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage58SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_CONTEXT = "SOURCE_ONLY_CONTEXT"


@dataclass(frozen=True)
class TMPage58MappingPolicy:
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
    root_report_norm_id: int
    axis_parent_ids: tuple[tuple[str, int], ...]
    metric_target_ids: tuple[tuple[str, tuple[int, ...]], ...]
    not_observed_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage58SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage58SourceDisposition:
    row_id: str
    ordinal: int
    source_role: str
    metric_key: str | None
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
class TMPage58MappedAssignment:
    source_row_id: str
    source_role: str
    metric_key: str
    cell_index: int
    axis_key: str
    report_norm_id: int
    observation: str
    value: Decimal | None
    period_start: str
    period_end: str
    period_role: str
    period_type: str
    unit: str
    unit_multiplier: int
    mapping_basis: str


@dataclass(frozen=True)
class TMPage58ValidationCheck:
    check_id: str
    check_kind: str
    axis_key: str | None
    metric_key: str | None
    status: str
    expected_value: Decimal | None
    observed_value: Decimal | None
    residual: Decimal | None
    target_report_norm_id: int
    reason: str


@dataclass(frozen=True)
class TMPage58MappingResult:
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
    source_only_row_count: int
    source_question_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_assignment_count: int
    validation_check_count: int
    validation_pass_count: int
    validation_not_testable_count: int
    schema_dispositions: tuple[TMPage58SchemaDisposition, ...]
    source_dispositions: tuple[TMPage58SourceDisposition, ...]
    mapped_assignments: tuple[TMPage58MappedAssignment, ...]
    validation_checks: tuple[TMPage58ValidationCheck, ...]
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
        raise TMPage58MappingError(f"invalid positive TM page-58 field: {field}")
    return value


def _int_list(value: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise TMPage58MappingError(f"TM page-58 {field} is invalid")
    result = tuple(value)
    if len(set(result)) != len(result):
        raise TMPage58MappingError(f"TM page-58 {field} contains duplicates")
    return result


def _ordered_int_mapping(value: Any, field: str) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, dict) or any(
        not isinstance(key, str) or not key or isinstance(item, bool) or not isinstance(item, int)
        for key, item in value.items()
    ):
        raise TMPage58MappingError(f"TM page-58 {field} is invalid")
    return tuple((key, item) for key, item in value.items())


def _ordered_list_mapping(value: Any, field: str) -> tuple[tuple[str, tuple[int, ...]], ...]:
    if not isinstance(value, dict):
        raise TMPage58MappingError(f"TM page-58 {field} is invalid")
    return tuple((str(key), _int_list(items, field)) for key, items in value.items())


def _expanded_ids(value: Any, field: str) -> tuple[int, ...]:
    if not isinstance(value, dict):
        raise TMPage58MappingError(f"TM page-58 {field} is invalid")
    raw_ranges = value.get("ranges")
    raw_ids = value.get("ids")
    if not isinstance(raw_ranges, list) or not isinstance(raw_ids, list):
        raise TMPage58MappingError(f"TM page-58 {field} axes are invalid")
    ids = list(_int_list(raw_ids, field, allow_empty=True))
    for record in raw_ranges:
        if not isinstance(record, dict):
            raise TMPage58MappingError(f"TM page-58 {field} range is invalid")
        start = _positive_int(record, "start")
        end = _positive_int(record, "end")
        if end < start:
            raise TMPage58MappingError(f"TM page-58 {field} range is reversed")
        ids.extend(range(start, end + 1))
    if len(set(ids)) != len(ids):
        raise TMPage58MappingError(f"TM page-58 {field} contains duplicates")
    return tuple(sorted(ids))


def load_tm_page58_mapping_policy(path: Path) -> TMPage58MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage58MappingError(f"cannot load TM page-58 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE58_CURRENCY_RISK_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 58
        or payload.get("page_tag") != "page-0058"
        or payload.get("report_scope") != "CONSOLIDATED"
        or payload.get("document") != "MBB_CONSOLIDATED_Q1_2026"
        or payload.get("mapping_authority_scope")
        != "MBB_CONSOLIDATED_Q1_2026_PAGE58_IDS_1352_1482_AND_5849_5856_ONLY"
    ):
        raise TMPage58MappingError("TM page-58 mapping identity drifted")
    hash_fields = (
        "source_table_policy_sha256",
        "source_pdf_sha256",
        "source_render_sha256",
        "source_ocr_sha256",
        "upstream_ocr_sha256",
        "schema_workbook_sha256",
        "schema_scope_sha256",
    )
    hashes = tuple(payload.get(field) for field in hash_fields)
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage58MappingError("TM page-58 mapping hashes are invalid")
    table_policy = payload.get("source_table_policy")
    if not isinstance(table_policy, str) or table_policy != "config/tables/tm-note-page58-v1.yaml":
        raise TMPage58MappingError("TM page-58 source table policy path drifted")
    table_path = (path.parents[2] / table_policy).resolve()
    if not table_path.is_file() or sha256_file(table_path) != hashes[0]:
        raise TMPage58MappingError("TM page-58 source table policy hash drifted")
    if (
        payload.get("schema_total") != TM_PAGE58_SCHEMA_TOTAL
        or payload.get("scope_schema_ids")
        != [{"start": 1352, "end": 1482}, {"start": 5849, "end": 5856}]
        or payload.get("scope_schema_total") != TM_PAGE58_SCOPE_SCHEMA_COUNT
        or payload.get("root_report_norm_id") != _ROOT_ID
    ):
        raise TMPage58MappingError("TM page-58 schema denominator/scope drifted")
    axis_parent_ids = _ordered_int_mapping(payload.get("axis_parent_ids"), "axis parents")
    metric_target_ids = _ordered_list_mapping(payload.get("metric_target_ids"), "metric targets")
    not_observed_ids = _expanded_ids(
        payload.get("not_observed_schema_ids"), "not-observed schema IDs"
    )
    if tuple(key for key, _ in axis_parent_ids) != _AXIS_KEYS or dict(axis_parent_ids) != (
        _AXIS_PARENT_IDS
    ):
        raise TMPage58MappingError("TM page-58 axis parent targets drifted")
    if (
        tuple(key for key, _ in metric_target_ids) != _METRIC_KEYS
        or dict(metric_target_ids) != _METRIC_TARGET_IDS
    ):
        raise TMPage58MappingError("TM page-58 metric targets drifted")
    if set(not_observed_ids) != _NOT_OBSERVED_IDS:
        raise TMPage58MappingError("TM page-58 not-observed partition drifted")
    if payload.get("hierarchy_contract") != _EXPECTED_HIERARCHY_CONTRACT:
        raise TMPage58MappingError("TM page-58 hierarchy contract drifted")
    if payload.get("validation_only_contract") != _EXPECTED_VALIDATION_CONTRACT:
        raise TMPage58MappingError("TM page-58 validation-only contract drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage58MappingError("TM page-58 forbidden inputs drifted")
    return TMPage58MappingPolicy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=58,
        page_tag="page-0058",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=str(payload.get("mapping_authority_scope", "")),
        source_table_policy=table_policy,
        source_table_policy_sha256=str(hashes[0]),
        source_pdf_sha256=str(hashes[1]),
        source_render_sha256=str(hashes[2]),
        source_ocr_sha256=str(hashes[3]),
        upstream_ocr_sha256=str(hashes[4]),
        schema_workbook_sha256=str(hashes[5]),
        schema_total=TM_PAGE58_SCHEMA_TOTAL,
        scope_schema_ids=tuple(sorted(_SCOPE_IDS)),
        schema_scope_sha256=str(hashes[6]),
        root_report_norm_id=_ROOT_ID,
        axis_parent_ids=axis_parent_ids,
        metric_target_ids=metric_target_ids,
        not_observed_schema_ids=not_observed_ids,
        forbidden_mapping_inputs=tuple(str(item) for item in forbidden),
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
        (
            schema_id,
            schema_by_id[schema_id].canonical_name,
            schema_by_id[schema_id].parent_id,
            tuple(schema_by_id[schema_id].children),
        )
        for schema_id in sorted(_SCOPE_IDS)
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validate_schema_branch(schema_by_id: dict[int, SchemaItem]) -> None:
    if schema_by_id[_ROOT_ID].parent_id != 1259:
        raise TMPage58MappingError("TM page-58 currency-risk root hierarchy drifted")
    if tuple(schema_by_id[_ROOT_ID].children) != (1353, 1379, 1405, 1431, 1457):
        raise TMPage58MappingError("TM page-58 axis branch order drifted")
    metric_targets = dict(_METRIC_TARGET_IDS)
    direct_axis_metrics = (
        "TOTAL_ASSETS",
        "CASH_AND_PRECIOUS_METALS",
        "SBV_DEPOSITS",
        "INTERBANK_ASSETS",
        "DERIVATIVE_ASSETS",
        "CUSTOMER_LOANS",
        "INVESTMENT_SECURITIES",
        "LONG_TERM_INVESTMENTS",
        "FIXED_ASSETS_AND_INVESTMENT_PROPERTY",
        "OTHER_ASSETS",
        "ON_BALANCE_CURRENCY_POSITION",
        "OFF_BALANCE_CURRENCY_POSITION",
        "COMBINED_CURRENCY_POSITION",
    )
    liability_headers = (1392, 1366, 1444, 1470)
    liability_totals = (5852, 5850, 5854, 5856)
    capital_ids = (1401, 1375, 1453, 1479)
    broad_interbank_ids = (1393, 1367, 1445, 1471)
    government_ids = (1394, 1368, 1446, 1472)
    entrusted_ids = (1398, 1372, 1450, 1476)
    issued_ids = (1399, 1373, 1451, 1477)
    fixed_children = ((1389, 1390), (1363, 1364), (1441, 1442), (1467, 1468))
    for axis_index, axis_key in enumerate(_AXIS_KEYS):
        parent_id = _AXIS_PARENT_IDS[axis_key]
        if schema_by_id[parent_id].parent_id != _ROOT_ID:
            raise TMPage58MappingError(f"TM page-58 axis parent drifted: {axis_key}")
        for metric_key in direct_axis_metrics:
            target_id = metric_targets[metric_key][axis_index]
            if schema_by_id[target_id].parent_id != parent_id:
                raise TMPage58MappingError(
                    f"TM page-58 direct metric hierarchy drifted: {axis_key}/{metric_key}"
                )
        header_id = liability_headers[axis_index]
        total_id = liability_totals[axis_index]
        broad_id = broad_interbank_ids[axis_index]
        specific_id = metric_targets["INTERBANK_LIABILITIES"][axis_index]
        customer_id = metric_targets["CUSTOMER_DEPOSITS"][axis_index]
        derivative_id = metric_targets["DERIVATIVE_LIABILITIES"][axis_index]
        other_id = metric_targets["OTHER_LIABILITIES"][axis_index]
        fixed_id = metric_targets["FIXED_ASSETS_AND_INVESTMENT_PROPERTY"][axis_index]
        fixed_child_a, fixed_child_b = fixed_children[axis_index]
        if (
            schema_by_id[header_id].parent_id != parent_id
            or tuple(schema_by_id[header_id].children) != (total_id, capital_ids[axis_index])
            or metric_targets["TOTAL_LIABILITIES"][axis_index] != total_id
            or schema_by_id[total_id].parent_id != header_id
            or tuple(schema_by_id[total_id].children)
            != (
                broad_id,
                customer_id,
                derivative_id,
                entrusted_ids[axis_index],
                issued_ids[axis_index],
                other_id,
            )
            or schema_by_id[broad_id].parent_id != total_id
            or tuple(schema_by_id[broad_id].children) != (government_ids[axis_index], specific_id)
            or schema_by_id[specific_id].parent_id != broad_id
            or tuple(schema_by_id[fixed_id].children) != (fixed_child_a, fixed_child_b)
            or schema_by_id[fixed_child_a].parent_id != fixed_id
            or schema_by_id[fixed_child_b].parent_id != fixed_id
        ):
            raise TMPage58MappingError("TM page-58 combined-item hierarchy drifted")


def _validation_check(
    *,
    check_id: str,
    check_kind: str,
    axis_key: str | None,
    metric_key: str | None,
    operands: Sequence[Any],
    observed_cell: Any,
    target_report_norm_id: int,
    subtract: bool = False,
) -> TMPage58ValidationCheck:
    has_dash = observed_cell.observation is ObservationKind.DASH or any(
        cell.observation is ObservationKind.DASH for cell in operands
    )
    if has_dash:
        return TMPage58ValidationCheck(
            check_id=check_id,
            check_kind=check_kind,
            axis_key=axis_key,
            metric_key=metric_key,
            status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
            expected_value=None,
            observed_value=observed_cell.value,
            residual=None,
            target_report_norm_id=target_report_norm_id,
            reason=(
                "the printed equation contains at least one DASH and is explicitly not testable; "
                "DASH is never coerced to zero"
            ),
        )
    if observed_cell.value is None or any(cell.value is None for cell in operands):
        raise TMPage58MappingError("TM page-58 validation operand is absent")
    if subtract:
        if len(operands) != 2:
            raise TMPage58MappingError("TM page-58 subtraction arity drifted")
        expected = operands[0].value - operands[1].value
    else:
        expected = sum((cell.value for cell in operands), Decimal(0))
    residual = observed_cell.value - expected
    return TMPage58ValidationCheck(
        check_id=check_id,
        check_kind=check_kind,
        axis_key=axis_key,
        metric_key=metric_key,
        status="PASS" if residual == 0 else "FAIL",
        expected_value=expected,
        observed_value=observed_cell.value,
        residual=residual,
        target_report_norm_id=target_report_norm_id,
        reason="the printed equation is tested after mapping and never selects or populates an item",
    )


def _validations(parsed: ParsedTMPage58) -> tuple[TMPage58ValidationCheck, ...]:
    rows = {row.metric_key: row for row in parsed.rows if row.metric_key is not None}
    targets = _METRIC_TARGET_IDS
    checks = []
    for metric_key in _METRIC_KEYS:
        row = rows[metric_key]
        checks.append(
            _validation_check(
                check_id=f"ROW_TOTAL_{metric_key}",
                check_kind="ROW_TOTAL_VALIDATION_ONLY",
                axis_key="TOTAL",
                metric_key=metric_key,
                operands=row.row.cells[:3],
                observed_cell=row.row.cells[3],
                target_report_norm_id=targets[metric_key][3],
            )
        )
    for axis_index, axis_key in enumerate(_AXIS_KEYS):
        checks.append(
            _validation_check(
                check_id=f"ASSET_COMPOSITION_{axis_key}",
                check_kind="ASSET_COMPOSITION_VALIDATION_ONLY",
                axis_key=axis_key,
                metric_key="TOTAL_ASSETS",
                operands=tuple(rows[key].row.cells[axis_index] for key in _ASSET_DETAIL_METRICS),
                observed_cell=rows["TOTAL_ASSETS"].row.cells[axis_index],
                target_report_norm_id=targets["TOTAL_ASSETS"][axis_index],
            )
        )
    for axis_index, axis_key in enumerate(_AXIS_KEYS):
        checks.append(
            _validation_check(
                check_id=f"LIABILITY_COMPOSITION_{axis_key}",
                check_kind="LIABILITY_COMPOSITION_VALIDATION_ONLY",
                axis_key=axis_key,
                metric_key="TOTAL_LIABILITIES",
                operands=tuple(
                    rows[key].row.cells[axis_index] for key in _LIABILITY_DETAIL_METRICS
                ),
                observed_cell=rows["TOTAL_LIABILITIES"].row.cells[axis_index],
                target_report_norm_id=targets["TOTAL_LIABILITIES"][axis_index],
            )
        )
    for axis_index, axis_key in enumerate(_AXIS_KEYS):
        checks.append(
            _validation_check(
                check_id=f"ON_BALANCE_POSITION_{axis_key}",
                check_kind="ON_BALANCE_POSITION_VALIDATION_ONLY",
                axis_key=axis_key,
                metric_key="ON_BALANCE_CURRENCY_POSITION",
                operands=(
                    rows["TOTAL_ASSETS"].row.cells[axis_index],
                    rows["TOTAL_LIABILITIES"].row.cells[axis_index],
                ),
                observed_cell=rows["ON_BALANCE_CURRENCY_POSITION"].row.cells[axis_index],
                target_report_norm_id=targets["ON_BALANCE_CURRENCY_POSITION"][axis_index],
                subtract=True,
            )
        )
    for axis_index, axis_key in enumerate(_AXIS_KEYS):
        checks.append(
            _validation_check(
                check_id=f"COMBINED_POSITION_{axis_key}",
                check_kind="COMBINED_POSITION_VALIDATION_ONLY",
                axis_key=axis_key,
                metric_key="COMBINED_CURRENCY_POSITION",
                operands=(
                    rows["ON_BALANCE_CURRENCY_POSITION"].row.cells[axis_index],
                    rows["OFF_BALANCE_CURRENCY_POSITION"].row.cells[axis_index],
                ),
                observed_cell=rows["COMBINED_CURRENCY_POSITION"].row.cells[axis_index],
                target_report_norm_id=targets["COMBINED_CURRENCY_POSITION"][axis_index],
            )
        )
    return tuple(checks)


def reconcile_tm_page58_items(
    parsed: ParsedTMPage58,
    *,
    schema: Sequence[SchemaItem],
    policy: TMPage58MappingPolicy,
    source_pdf_path: Path,
    schema_workbook_path: Path,
) -> TMPage58MappingResult:
    if (
        policy.mapping_authority_scope
        != "MBB_CONSOLIDATED_Q1_2026_PAGE58_IDS_1352_1482_AND_5849_5856_ONLY"
        or policy.root_report_norm_id != _ROOT_ID
        or dict(policy.axis_parent_ids) != _AXIS_PARENT_IDS
        or dict(policy.metric_target_ids) != _METRIC_TARGET_IDS
        or set(policy.forbidden_mapping_inputs) != _REQUIRED_FORBIDDEN
    ):
        raise TMPage58MappingError("TM page-58 mapping policy target drifted")
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
        or parsed.upstream_ocr_sha256 != policy.upstream_ocr_sha256
    ):
        raise TMPage58MappingError("TM page-58 parser/mapping identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage58MappingError("TM page-58 source PDF hash drifted")
    if sha256_file(schema_workbook_path) != policy.schema_workbook_sha256:
        raise TMPage58MappingError("TM page-58 schema workbook hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != TM_PAGE58_SCHEMA_TOTAL or len(tm_schema) != policy.schema_total:
        raise TMPage58MappingError("TM page-58 schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if (
        set(policy.scope_schema_ids) != _SCOPE_IDS
        or set(policy.not_observed_schema_ids) != _NOT_OBSERVED_IDS
        or _schema_scope_hash(schema_by_id) != policy.schema_scope_sha256
    ):
        raise TMPage58MappingError("TM page-58 owned schema scope drifted")
    _validate_schema_branch(schema_by_id)
    if tuple(axis.axis_key for axis in parsed.axes) != _AXIS_KEYS:
        raise TMPage58MappingError("TM page-58 parsed axis order drifted")
    numeric_rows = tuple(row for row in parsed.rows if row.metric_key is not None)
    if tuple(row.metric_key for row in numeric_rows) != _METRIC_KEYS:
        raise TMPage58MappingError("TM page-58 parsed metric order drifted")

    source_by_schema: dict[int, list[str]] = {schema_id: [] for schema_id in _MAPPED_IDS}
    source_by_schema[_ROOT_ID].append(
        f"{parsed.page_tag}:line-{parsed.table.title_line_indices[0]:04d}"
    )
    for axis, parent_id in zip(parsed.axes, _AXIS_PARENT_IDS.values(), strict=True):
        source_by_schema[parent_id].extend(
            f"{parsed.page_tag}:line-{index:04d}" for index in axis.header_line_indices
        )
    assignments = []
    source_dispositions = []
    targets = dict(policy.metric_target_ids)
    for row in parsed.rows:
        if row.metric_key is None:
            source_dispositions.append(
                TMPage58SourceDisposition(
                    row_id=row.row_id,
                    ordinal=row.ordinal,
                    source_role=row.source_role,
                    metric_key=None,
                    status=TMPage58SourceStatus.SOURCE_ONLY_CONTEXT.value,
                    report_norm_ids=(),
                    observations=tuple(cell.observation.value for cell in row.row.cells),
                    values=tuple(cell.value for cell in row.row.cells),
                    period_starts=(None,) * 4,
                    period_ends=(None,) * 4,
                    period_roles=(None,) * 4,
                    period_types=(None,) * 4,
                    unit=parsed.axes[0].canonical_unit,
                    unit_multiplier=parsed.axes[0].unit_multiplier,
                    question_required=False,
                    reason="visible asset/liability section heading supplies source context only",
                )
            )
            continue
        report_norm_ids = targets[row.metric_key]
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
                or cell.observation
                not in {ObservationKind.VALUE, ObservationKind.ZERO, ObservationKind.DASH}
            ):
                raise TMPage58MappingError("TM page-58 assignment status/period drifted")
            source_by_schema[schema_id].append(row.row_id)
            assignments.append(
                TMPage58MappedAssignment(
                    source_row_id=row.row_id,
                    source_role=row.source_role,
                    metric_key=row.metric_key,
                    cell_index=index,
                    axis_key=axis.axis_key,
                    report_norm_id=schema_id,
                    observation=cell.observation.value,
                    value=cell.value,
                    period_start=start.isoformat(),
                    period_end=end.isoformat(),
                    period_role=role,
                    period_type=period_type,
                    unit=axis.canonical_unit,
                    unit_multiplier=axis.unit_multiplier,
                    mapping_basis=(
                        "VISIBLE_PAGE58_METRIC_ROW_X_FIXED_CURRENCY_RISK_AXIS_TO_FROZEN_SCHEMA"
                    ),
                )
            )
        source_dispositions.append(
            TMPage58SourceDisposition(
                row_id=row.row_id,
                ordinal=row.ordinal,
                source_role=row.source_role,
                metric_key=row.metric_key,
                status=TMPage58SourceStatus.MAPPED_AUTOMATIC_SCOPED.value,
                report_norm_ids=report_norm_ids,
                observations=tuple(cell.observation.value for cell in row.row.cells),
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
                period_types=row.cell_period_types,
                unit=parsed.axes[0].canonical_unit,
                unit_multiplier=parsed.axes[0].unit_multiplier,
                question_required=False,
                reason=(
                    "visible metric row and fixed currency-risk axis uniquely bind all four cells; "
                    "values, dashes, and equations never select an item"
                ),
            )
        )
    if any(not source_by_schema[schema_id] for schema_id in _MAPPED_IDS):
        raise TMPage58MappingError("TM page-58 mapped item lacks source provenance")

    checks = _validations(parsed)
    if (
        len(checks) != TM_PAGE58_VALIDATION_CHECK_COUNT
        or sum(check.status == "PASS" for check in checks) != TM_PAGE58_VALIDATION_PASS_COUNT
        or sum(check.status.startswith("NOT_TESTABLE") for check in checks)
        != TM_PAGE58_VALIDATION_NOT_TESTABLE_COUNT
        or any(
            check.status == "FAIL"
            or (check.status == "PASS" and check.residual != 0)
            or (check.status.startswith("NOT_TESTABLE") and check.residual is not None)
            for check in checks
        )
    ):
        raise TMPage58MappingError("TM page-58 accounting validation failed")
    schema_dispositions = tuple(
        TMPage58SchemaDisposition(
            report_norm_id=item.schema_id,
            display_order=item.display_order,
            canonical_name=item.canonical_name,
            status=(
                TMPage58SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
                if item.schema_id in _MAPPED_IDS
                else TMPage58SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
                if item.schema_id in _NOT_OBSERVED_IDS
                else TMPage58SchemaStatus.UNASSESSED.value
            ),
            source_ids=tuple(dict.fromkeys(source_by_schema.get(item.schema_id, ()))),
            reason=(
                "page 58 is the unique scoped owner of this visible structural or value-bearing item"
                if item.schema_id in _MAPPED_IDS
                else "fully assessed scope item with no distinct visible page-58 source row"
                if item.schema_id in _NOT_OBSERVED_IDS
                else "outside the page-58 owned currency-risk schema scope"
            ),
        )
        for item in tm_schema
    )
    result = TMPage58MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=58,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="PAGE58_CURRENCY_RISK_SCOPE_RECONCILED_MAPPED_AND_VALIDATED",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=TM_PAGE58_SCOPE_SCHEMA_COUNT,
        mapped_schema_count=TM_PAGE58_MAPPED_SCHEMA_COUNT,
        structural_mapped_schema_count=TM_PAGE58_STRUCTURAL_MAPPED_SCHEMA_COUNT,
        value_bearing_mapped_schema_count=TM_PAGE58_VALUE_BEARING_MAPPED_SCHEMA_COUNT,
        not_observed_schema_count=TM_PAGE58_NOT_OBSERVED_SCHEMA_COUNT,
        not_applicable_schema_count=0,
        ambiguous_schema_count=0,
        unresolved_schema_count=0,
        unassessed_schema_count=TM_PAGE58_UNASSESSED_SCHEMA_COUNT,
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMPage58SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status == TMPage58SourceStatus.SOURCE_ONLY_CONTEXT.value
            for item in source_dispositions
        ),
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
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        upstream_ocr_sha256=policy.upstream_ocr_sha256,
        schema_workbook_sha256=policy.schema_workbook_sha256,
        schema_projection_sha256=_schema_projection_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS_AND_GEOMETRY",
            "VISIBLE_PAGE58_METRIC_ROW_AND_FIXED_CURRENCY_RISK_AXIS_ORDER",
            "VISIBLE_SNAPSHOT_PERIOD_UNIT_AND_CONSOLIDATED_SCOPE",
            "PIXEL_BACKED_DASH_STATUS_WITHOUT_ZERO_COERCION",
            "FROZEN_TM_SCHEMA_SCOPE_IDS_1352_THROUGH_1482_AND_5849_THROUGH_5856",
            "COMBINED_FIXED_PROPERTY_AS_PARENT_OF_TWO_REPARENTED_COMPONENTS",
            "TOTAL_LIABILITIES_AS_CHILD_OF_LIABILITIES_AND_EQUITY_HEADER",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
            "PAGE57_AS_DISJOINT_INDEPENDENT_OWNER",
        ),
    )
    return validate_tm_page58_mapping_result(result)


def validate_tm_page58_mapping_result(
    result: TMPage58MappingResult,
) -> TMPage58MappingResult:
    if (
        result.schema_item_count != TM_PAGE58_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE58_SCOPE_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE58_MAPPED_SCHEMA_COUNT
        or result.structural_mapped_schema_count != TM_PAGE58_STRUCTURAL_MAPPED_SCHEMA_COUNT
        or result.value_bearing_mapped_schema_count != TM_PAGE58_VALUE_BEARING_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE58_NOT_OBSERVED_SCHEMA_COUNT
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != 0
        or result.unresolved_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE58_UNASSESSED_SCHEMA_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE58_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE58_MAPPED_SOURCE_ROW_COUNT
        or result.source_only_row_count != TM_PAGE58_SOURCE_ONLY_ROW_COUNT
        or result.source_question_row_count != 0
        or result.financial_slot_count != TM_PAGE58_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE58_VALUE_COUNT
        or result.dash_count != TM_PAGE58_DASH_COUNT
        or result.mapped_assignment_count != TM_PAGE58_ASSIGNMENT_COUNT
        or result.validation_check_count != TM_PAGE58_VALIDATION_CHECK_COUNT
        or result.validation_pass_count != TM_PAGE58_VALIDATION_PASS_COUNT
        or result.validation_not_testable_count != TM_PAGE58_VALIDATION_NOT_TESTABLE_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage58MappingError("TM page-58 mapping denominator drifted")
    if result.status_reconciled_schema_count + result.unassessed_schema_count != (
        result.schema_item_count
    ):
        raise TMPage58MappingError("TM page-58 schema statuses do not reconcile")
    mapped = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage58SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    not_observed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage58SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    }
    unassessed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage58SchemaStatus.UNASSESSED.value
    }
    if (
        mapped != _MAPPED_IDS
        or not_observed != _NOT_OBSERVED_IDS
        or len(unassessed) != TM_PAGE58_UNASSESSED_SCHEMA_COUNT
        or mapped | not_observed | unassessed
        != {item.report_norm_id for item in result.schema_dispositions}
        or any(
            not item.source_ids
            for item in result.schema_dispositions
            if item.report_norm_id in _MAPPED_IDS
        )
        or any(
            item.source_ids
            for item in result.schema_dispositions
            if item.report_norm_id not in _MAPPED_IDS
        )
    ):
        raise TMPage58MappingError("TM page-58 schema disposition partition drifted")
    if (
        tuple(item.status for item in result.source_dispositions).count(
            TMPage58SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        )
        != 18
        or tuple(item.status for item in result.source_dispositions).count(
            TMPage58SourceStatus.SOURCE_ONLY_CONTEXT.value
        )
        != 2
        or any(item.question_required for item in result.source_dispositions)
    ):
        raise TMPage58MappingError("TM page-58 source disposition drifted")
    dash_assignments = tuple(
        item for item in result.mapped_assignments if item.observation == ObservationKind.DASH.value
    )
    if (
        {item.report_norm_id for item in result.mapped_assignments} != _VALUE_IDS
        or len(dash_assignments) != 9
        or any(item.value is not None for item in dash_assignments)
        or sum(
            item.observation == ObservationKind.VALUE.value for item in result.mapped_assignments
        )
        != 63
        or {(item.unit, item.unit_multiplier) for item in result.mapped_assignments}
        != {("VND", 1_000_000)}
        or {item.period_type for item in result.mapped_assignments} != {"SNAPSHOT"}
    ):
        raise TMPage58MappingError("TM page-58 assignment partition drifted")
    kinds = tuple(check.check_kind for check in result.validation_checks)
    expected_splits = {
        "ROW_TOTAL_VALIDATION_ONLY": (18, 14, 4),
        "ASSET_COMPOSITION_VALIDATION_ONLY": (4, 0, 4),
        "LIABILITY_COMPOSITION_VALIDATION_ONLY": (4, 4, 0),
        "ON_BALANCE_POSITION_VALIDATION_ONLY": (4, 4, 0),
        "COMBINED_POSITION_VALIDATION_ONLY": (4, 4, 0),
    }
    for kind, (total, passed, not_testable) in expected_splits.items():
        selected = tuple(check for check in result.validation_checks if check.check_kind == kind)
        if (
            kinds.count(kind) != total
            or sum(check.status == "PASS" for check in selected) != passed
            or sum(check.status.startswith("NOT_TESTABLE") for check in selected) != not_testable
        ):
            raise TMPage58MappingError("TM page-58 validation split drifted")
    if any(
        check.status == "FAIL"
        or (check.status == "PASS" and check.residual != 0)
        or (check.status.startswith("NOT_TESTABLE") and check.residual is not None)
        for check in result.validation_checks
    ):
        raise TMPage58MappingError("TM page-58 validation result drifted")
    return result


__all__ = [
    "TM_PAGE58_MAPPING_POLICY_RELATIVE_PATH",
    "TMPage58MappedAssignment",
    "TMPage58MappingError",
    "TMPage58MappingPolicy",
    "TMPage58MappingResult",
    "TMPage58SchemaDisposition",
    "TMPage58SchemaStatus",
    "TMPage58SourceDisposition",
    "TMPage58SourceStatus",
    "TMPage58ValidationCheck",
    "load_tm_page58_mapping_policy",
    "reconcile_tm_page58_items",
    "validate_tm_page58_mapping_result",
]
