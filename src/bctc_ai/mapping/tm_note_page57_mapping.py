"""Hierarchy-safe mapping for MBB consolidated TM page 57 interest-rate risk."""

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
from bctc_ai.tables.tm_note_page57 import ParsedTMPage57

TM_PAGE57_MAPPING_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page57-v1.yaml")
TM_PAGE57_SCHEMA_TOTAL = 1_710
TM_PAGE57_SCOPE_SCHEMA_COUNT = 317
TM_PAGE57_MAPPED_SCHEMA_COUNT = 169
TM_PAGE57_STRUCTURAL_MAPPED_SCHEMA_COUNT = 9
TM_PAGE57_VALUE_BEARING_MAPPED_SCHEMA_COUNT = 160
TM_PAGE57_NOT_OBSERVED_SCHEMA_COUNT = 148
TM_PAGE57_UNASSESSED_SCHEMA_COUNT = 1_393
TM_PAGE57_SOURCE_ROW_COUNT = 22
TM_PAGE57_MAPPED_SOURCE_ROW_COUNT = 20
TM_PAGE57_SOURCE_ONLY_ROW_COUNT = 2
TM_PAGE57_FINANCIAL_SLOT_COUNT = 160
TM_PAGE57_VALUE_COUNT = 92
TM_PAGE57_DASH_COUNT = 68
TM_PAGE57_ASSIGNMENT_COUNT = 160
TM_PAGE57_VALIDATION_CHECK_COUNT = 44
TM_PAGE57_VALIDATION_PASS_COUNT = 10
TM_PAGE57_VALIDATION_NOT_TESTABLE_COUNT = 34

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_AXIS_KEYS = (
    "OVERDUE",
    "NOT_REPRICED",
    "WITHIN_1M",
    "FROM_1_TO_3M",
    "FROM_3_TO_6M",
    "FROM_6_TO_12M",
    "OVER_1Y",
    "TOTAL",
)
_METRIC_KEYS = (
    "CASH_AND_PRECIOUS_METALS",
    "SBV_DEPOSITS",
    "INTERBANK_ASSETS",
    "TRADING_SECURITIES",
    "DERIVATIVE_ASSETS",
    "CUSTOMER_LOANS_AND_PURCHASED_DEBT",
    "INVESTMENT_SECURITIES",
    "LONG_TERM_INVESTMENTS",
    "FIXED_ASSETS_AND_INVESTMENT_PROPERTY",
    "OTHER_ASSETS",
    "TOTAL_ASSETS",
    "GOVERNMENT_SBV_LIABILITIES",
    "INTERBANK_LIABILITIES",
    "CUSTOMER_DEPOSITS",
    "DERIVATIVE_LIABILITIES",
    "ENTRUSTED_FUNDS",
    "ISSUED_VALUABLE_PAPERS",
    "OTHER_LIABILITIES",
    "TOTAL_LIABILITIES",
    "ON_BALANCE_INTEREST_SENSITIVITY_GAP",
)
_ASSET_DETAIL_METRICS = _METRIC_KEYS[:10]
_LIABILITY_DETAIL_METRICS = _METRIC_KEYS[11:18]
_ROOT_ID = 1483
_AXIS_PARENT_IDS = {
    "OVERDUE": 1509,
    "NOT_REPRICED": 1484,
    "WITHIN_1M": 1584,
    "FROM_1_TO_3M": 1609,
    "FROM_3_TO_6M": 1634,
    "FROM_6_TO_12M": 1659,
    "OVER_1Y": 5869,
    "TOTAL": 1734,
}
_METRIC_TARGET_IDS = {
    "CASH_AND_PRECIOUS_METALS": (1511, 1486, 1586, 1611, 1636, 1661, 5871, 1736),
    "SBV_DEPOSITS": (1512, 1487, 1587, 1612, 1637, 1662, 5872, 1737),
    "INTERBANK_ASSETS": (1513, 1488, 1588, 1613, 1638, 1663, 5873, 1738),
    "TRADING_SECURITIES": (1514, 1489, 1589, 1614, 1639, 1664, 5874, 1739),
    "DERIVATIVE_ASSETS": (1515, 1490, 1590, 1615, 1640, 1665, 5875, 1740),
    "CUSTOMER_LOANS_AND_PURCHASED_DEBT": (
        5859,
        5857,
        5861,
        5863,
        5865,
        5867,
        5876,
        5896,
    ),
    "INVESTMENT_SECURITIES": (1517, 1492, 1592, 1617, 1642, 1667, 5878, 1742),
    "LONG_TERM_INVESTMENTS": (1518, 1493, 1593, 1618, 1643, 1668, 5879, 1743),
    "FIXED_ASSETS_AND_INVESTMENT_PROPERTY": (
        5860,
        5858,
        5862,
        5864,
        5866,
        5868,
        5880,
        5897,
    ),
    "OTHER_ASSETS": (1521, 1496, 1596, 1621, 1646, 1671, 5883, 1746),
    "TOTAL_ASSETS": (1510, 1485, 1585, 1610, 1635, 1660, 5870, 1735),
    "GOVERNMENT_SBV_LIABILITIES": (
        1524,
        1499,
        1599,
        1624,
        1649,
        1674,
        5886,
        1749,
    ),
    "INTERBANK_LIABILITIES": (1523, 1498, 1598, 1623, 1648, 1673, 5885, 1748),
    "CUSTOMER_DEPOSITS": (1526, 1501, 1601, 1626, 1651, 1676, 5888, 1751),
    "DERIVATIVE_LIABILITIES": (1527, 1502, 1602, 1627, 1652, 1677, 5889, 1752),
    "ENTRUSTED_FUNDS": (1528, 1503, 1603, 1628, 1653, 1678, 5890, 1753),
    "ISSUED_VALUABLE_PAPERS": (1529, 1504, 1604, 1629, 1654, 1679, 5891, 1754),
    "OTHER_LIABILITIES": (1530, 1505, 1605, 1630, 1655, 1680, 5892, 1755),
    "TOTAL_LIABILITIES": (1522, 1497, 1597, 1622, 1647, 1672, 5884, 1747),
    "ON_BALANCE_INTEREST_SENSITIVITY_GAP": (
        1531,
        1506,
        1606,
        1631,
        1656,
        1681,
        5893,
        1756,
    ),
}
_SCOPE_IDS = set(range(1483, 1759)) | set(range(5857, 5898))
_VALUE_IDS = {schema_id for ids in _METRIC_TARGET_IDS.values() for schema_id in ids}
_STRUCTURAL_IDS = {_ROOT_ID, *_AXIS_PARENT_IDS.values()}
_MAPPED_IDS = _VALUE_IDS | _STRUCTURAL_IDS
_NOT_OBSERVED_IDS = _SCOPE_IDS - _MAPPED_IDS
_EXPECTED_NOT_OBSERVED_IDS = (
    set(range(1534, 1584))
    | set(range(1684, 1734))
    | {
        1491,
        1494,
        1495,
        1500,
        1507,
        1508,
        1516,
        1519,
        1520,
        1525,
        1532,
        1533,
        1591,
        1594,
        1595,
        1600,
        1607,
        1608,
        1616,
        1619,
        1620,
        1625,
        1632,
        1633,
        1641,
        1644,
        1645,
        1650,
        1657,
        1658,
        1666,
        1669,
        1670,
        1675,
        1682,
        1683,
        1741,
        1744,
        1745,
        1750,
        1757,
        1758,
        5877,
        5881,
        5882,
        5887,
        5894,
        5895,
    }
)
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text_as_item_selector",
    "numeric_value_magnitude_as_item_selector",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
    "accounting_equation_result_as_extracted_value",
    "schema_id_outside_page57_scope",
    "page58_value_as_page57_item_selector",
    "page58_value_as_page57_imputation",
}
_EXPECTED_HIERARCHY_CONTRACT = {
    "combined_customer_loans_and_purchased_debt": {
        "role": "SIBLING_LEAF_AGGREGATE",
        "children": [],
        "formula": None,
        "reparent_existing_customer_loans": False,
    },
    "combined_fixed_assets_and_investment_property": {
        "role": "PARENT_OF_TWO_EXISTING_COMPONENTS",
        "reparent_existing_components": True,
    },
}
_EXPECTED_VALIDATION_CONTRACT = [
    {
        "kind": "ROW_TOTAL_VALIDATION_ONLY",
        "checks": 20,
        "pass": 2,
        "not_testable_dash": 18,
    },
    {
        "kind": "ASSET_COMPOSITION_VALIDATION_ONLY",
        "checks": 8,
        "pass": 0,
        "not_testable_dash": 8,
    },
    {
        "kind": "LIABILITY_COMPOSITION_VALIDATION_ONLY",
        "checks": 8,
        "pass": 1,
        "not_testable_dash": 7,
    },
    {
        "kind": "ON_BALANCE_GAP_VALIDATION_ONLY",
        "checks": 8,
        "pass": 7,
        "not_testable_dash": 1,
    },
]

if (
    len(_SCOPE_IDS) != TM_PAGE57_SCOPE_SCHEMA_COUNT
    or len(_MAPPED_IDS) != TM_PAGE57_MAPPED_SCHEMA_COUNT
    or len(_VALUE_IDS) != TM_PAGE57_VALUE_BEARING_MAPPED_SCHEMA_COUNT
    or _NOT_OBSERVED_IDS != _EXPECTED_NOT_OBSERVED_IDS
    or len(_NOT_OBSERVED_IDS) != TM_PAGE57_NOT_OBSERVED_SCHEMA_COUNT
):
    raise AssertionError("TM page-57 static scope partition drifted")


class TMPage57MappingError(ValueError):
    pass


class TMPage57SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage57SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_CONTEXT = "SOURCE_ONLY_CONTEXT"


@dataclass(frozen=True)
class TMPage57MappingPolicy:
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
class TMPage57SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage57SourceDisposition:
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
class TMPage57MappedAssignment:
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
class TMPage57ValidationCheck:
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
class TMPage57MappingResult:
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
    schema_dispositions: tuple[TMPage57SchemaDisposition, ...]
    source_dispositions: tuple[TMPage57SourceDisposition, ...]
    mapped_assignments: tuple[TMPage57MappedAssignment, ...]
    validation_checks: tuple[TMPage57ValidationCheck, ...]
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
        raise TMPage57MappingError(f"invalid positive TM page-57 field: {field}")
    return value


def _int_list(value: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise TMPage57MappingError(f"TM page-57 {field} is invalid")
    result = tuple(value)
    if len(set(result)) != len(result):
        raise TMPage57MappingError(f"TM page-57 {field} contains duplicates")
    return result


def _ordered_int_mapping(value: Any, field: str) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, dict) or any(
        not isinstance(key, str) or not key or isinstance(item, bool) or not isinstance(item, int)
        for key, item in value.items()
    ):
        raise TMPage57MappingError(f"TM page-57 {field} is invalid")
    return tuple((key, item) for key, item in value.items())


def _ordered_list_mapping(value: Any, field: str) -> tuple[tuple[str, tuple[int, ...]], ...]:
    if not isinstance(value, dict):
        raise TMPage57MappingError(f"TM page-57 {field} is invalid")
    return tuple((str(key), _int_list(items, field)) for key, items in value.items())


def _expanded_ids(value: Any, field: str) -> tuple[int, ...]:
    if not isinstance(value, dict):
        raise TMPage57MappingError(f"TM page-57 {field} is invalid")
    raw_ranges = value.get("ranges")
    raw_ids = value.get("ids")
    if not isinstance(raw_ranges, list) or not isinstance(raw_ids, list):
        raise TMPage57MappingError(f"TM page-57 {field} axes are invalid")
    ids = list(_int_list(raw_ids, field, allow_empty=True))
    for record in raw_ranges:
        if not isinstance(record, dict):
            raise TMPage57MappingError(f"TM page-57 {field} range is invalid")
        start = _positive_int(record, "start")
        end = _positive_int(record, "end")
        if end < start:
            raise TMPage57MappingError(f"TM page-57 {field} range is reversed")
        ids.extend(range(start, end + 1))
    if len(set(ids)) != len(ids):
        raise TMPage57MappingError(f"TM page-57 {field} contains duplicates")
    return tuple(sorted(ids))


def load_tm_page57_mapping_policy(path: Path) -> TMPage57MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage57MappingError(f"cannot load TM page-57 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE57_INTEREST_RATE_RISK_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 57
        or payload.get("page_tag") != "page-0057"
        or payload.get("report_scope") != "CONSOLIDATED"
        or payload.get("document") != "MBB_CONSOLIDATED_Q1_2026"
        or payload.get("mapping_authority_scope")
        != "MBB_CONSOLIDATED_Q1_2026_PAGE57_IDS_1483_1758_AND_5857_5897_ONLY"
    ):
        raise TMPage57MappingError("TM page-57 mapping identity drifted")
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
        raise TMPage57MappingError("TM page-57 mapping hashes are invalid")
    table_policy = payload.get("source_table_policy")
    if not isinstance(table_policy, str) or table_policy != "config/tables/tm-note-page57-v1.yaml":
        raise TMPage57MappingError("TM page-57 source table policy path drifted")
    table_path = (path.parents[2] / table_policy).resolve()
    if not table_path.is_file() or sha256_file(table_path) != hashes[0]:
        raise TMPage57MappingError("TM page-57 source table policy hash drifted")
    if (
        payload.get("schema_total") != TM_PAGE57_SCHEMA_TOTAL
        or payload.get("scope_schema_ids")
        != [{"start": 1483, "end": 1758}, {"start": 5857, "end": 5897}]
        or payload.get("scope_schema_total") != TM_PAGE57_SCOPE_SCHEMA_COUNT
        or payload.get("root_report_norm_id") != _ROOT_ID
    ):
        raise TMPage57MappingError("TM page-57 schema denominator/scope drifted")
    axis_parent_ids = _ordered_int_mapping(payload.get("axis_parent_ids"), "axis parents")
    metric_target_ids = _ordered_list_mapping(payload.get("metric_target_ids"), "metric targets")
    not_observed_ids = _expanded_ids(
        payload.get("not_observed_schema_ids"), "not-observed schema IDs"
    )
    if tuple(key for key, _ in axis_parent_ids) != _AXIS_KEYS or dict(axis_parent_ids) != (
        _AXIS_PARENT_IDS
    ):
        raise TMPage57MappingError("TM page-57 axis parent targets drifted")
    if (
        tuple(key for key, _ in metric_target_ids) != _METRIC_KEYS
        or dict(metric_target_ids) != _METRIC_TARGET_IDS
    ):
        raise TMPage57MappingError("TM page-57 metric targets drifted")
    if set(not_observed_ids) != _NOT_OBSERVED_IDS:
        raise TMPage57MappingError("TM page-57 not-observed partition drifted")
    if payload.get("hierarchy_contract") != _EXPECTED_HIERARCHY_CONTRACT:
        raise TMPage57MappingError("TM page-57 hierarchy contract drifted")
    if payload.get("validation_only_contract") != _EXPECTED_VALIDATION_CONTRACT:
        raise TMPage57MappingError("TM page-57 validation-only contract drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage57MappingError("TM page-57 forbidden inputs drifted")
    return TMPage57MappingPolicy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=57,
        page_tag="page-0057",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=str(payload.get("mapping_authority_scope", "")),
        source_table_policy=table_policy,
        source_table_policy_sha256=str(hashes[0]),
        source_pdf_sha256=str(hashes[1]),
        source_render_sha256=str(hashes[2]),
        source_ocr_sha256=str(hashes[3]),
        upstream_ocr_sha256=str(hashes[4]),
        schema_workbook_sha256=str(hashes[5]),
        schema_total=TM_PAGE57_SCHEMA_TOTAL,
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
        raise TMPage57MappingError("TM page-57 interest-risk root hierarchy drifted")
    root_children = tuple(schema_by_id[_ROOT_ID].children)
    if tuple(root_children) != (1484, 1509, 1584, 1609, 1634, 1659, 1684, 1709, 5869, 1734):
        raise TMPage57MappingError("TM page-57 axis branch order drifted")
    metric_targets = dict(_METRIC_TARGET_IDS)
    for axis_index, axis_key in enumerate(_AXIS_KEYS):
        parent_id = _AXIS_PARENT_IDS[axis_key]
        if schema_by_id[parent_id].parent_id != _ROOT_ID:
            raise TMPage57MappingError(f"TM page-57 axis parent drifted: {axis_key}")
        for metric_key in _METRIC_KEYS:
            target_id = metric_targets[metric_key][axis_index]
            if schema_by_id[target_id].parent_id != parent_id:
                raise TMPage57MappingError(
                    f"TM page-57 direct metric hierarchy drifted: {axis_key}/{metric_key}"
                )
    combined_pairs = (
        (1484, 5857, 5858, 1491, 1494, 1495),
        (1509, 5859, 5860, 1516, 1519, 1520),
        (1584, 5861, 5862, 1591, 1594, 1595),
        (1609, 5863, 5864, 1616, 1619, 1620),
        (1634, 5865, 5866, 1641, 1644, 1645),
        (1659, 5867, 5868, 1666, 1669, 1670),
        (5869, 5876, 5880, 5877, 5881, 5882),
        (1734, 5896, 5897, 1741, 1744, 1745),
    )
    for parent_id, loan_id, fixed_id, old_loan_id, fixed_child_a, fixed_child_b in combined_pairs:
        if (
            schema_by_id[loan_id].parent_id != parent_id
            or schema_by_id[loan_id].children
            or schema_by_id[old_loan_id].parent_id != parent_id
            or schema_by_id[fixed_id].parent_id != parent_id
            or tuple(schema_by_id[fixed_id].children) != (fixed_child_a, fixed_child_b)
            or schema_by_id[fixed_child_a].parent_id != fixed_id
            or schema_by_id[fixed_child_b].parent_id != fixed_id
        ):
            raise TMPage57MappingError("TM page-57 combined-item hierarchy drifted")


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
) -> TMPage57ValidationCheck:
    has_dash = observed_cell.observation is ObservationKind.DASH or any(
        cell.observation is ObservationKind.DASH for cell in operands
    )
    if has_dash:
        return TMPage57ValidationCheck(
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
        raise TMPage57MappingError("TM page-57 validation operand is absent")
    if subtract:
        if len(operands) != 2:
            raise TMPage57MappingError("TM page-57 subtraction arity drifted")
        expected = operands[0].value - operands[1].value
    else:
        expected = sum((cell.value for cell in operands), Decimal(0))
    residual = observed_cell.value - expected
    return TMPage57ValidationCheck(
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


def _validations(parsed: ParsedTMPage57) -> tuple[TMPage57ValidationCheck, ...]:
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
                operands=row.row.cells[:7],
                observed_cell=row.row.cells[7],
                target_report_norm_id=targets[metric_key][7],
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
                check_id=f"ON_BALANCE_GAP_{axis_key}",
                check_kind="ON_BALANCE_GAP_VALIDATION_ONLY",
                axis_key=axis_key,
                metric_key="ON_BALANCE_INTEREST_SENSITIVITY_GAP",
                operands=(
                    rows["TOTAL_ASSETS"].row.cells[axis_index],
                    rows["TOTAL_LIABILITIES"].row.cells[axis_index],
                ),
                observed_cell=rows["ON_BALANCE_INTEREST_SENSITIVITY_GAP"].row.cells[axis_index],
                target_report_norm_id=targets["ON_BALANCE_INTEREST_SENSITIVITY_GAP"][axis_index],
                subtract=True,
            )
        )
    return tuple(checks)


def reconcile_tm_page57_items(
    parsed: ParsedTMPage57,
    *,
    schema: Sequence[SchemaItem],
    policy: TMPage57MappingPolicy,
    source_pdf_path: Path,
    schema_workbook_path: Path,
) -> TMPage57MappingResult:
    if (
        policy.mapping_authority_scope
        != "MBB_CONSOLIDATED_Q1_2026_PAGE57_IDS_1483_1758_AND_5857_5897_ONLY"
        or policy.root_report_norm_id != _ROOT_ID
        or dict(policy.axis_parent_ids) != _AXIS_PARENT_IDS
        or dict(policy.metric_target_ids) != _METRIC_TARGET_IDS
        or set(policy.forbidden_mapping_inputs) != _REQUIRED_FORBIDDEN
    ):
        raise TMPage57MappingError("TM page-57 mapping policy target drifted")
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
        or parsed.upstream_ocr_sha256 != policy.upstream_ocr_sha256
    ):
        raise TMPage57MappingError("TM page-57 parser/mapping identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage57MappingError("TM page-57 source PDF hash drifted")
    if sha256_file(schema_workbook_path) != policy.schema_workbook_sha256:
        raise TMPage57MappingError("TM page-57 schema workbook hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != TM_PAGE57_SCHEMA_TOTAL or len(tm_schema) != policy.schema_total:
        raise TMPage57MappingError("TM page-57 schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if (
        set(policy.scope_schema_ids) != _SCOPE_IDS
        or set(policy.not_observed_schema_ids) != _NOT_OBSERVED_IDS
        or _schema_scope_hash(schema_by_id) != policy.schema_scope_sha256
    ):
        raise TMPage57MappingError("TM page-57 owned schema scope drifted")
    _validate_schema_branch(schema_by_id)
    if tuple(axis.axis_key for axis in parsed.axes) != _AXIS_KEYS:
        raise TMPage57MappingError("TM page-57 parsed axis order drifted")
    numeric_rows = tuple(row for row in parsed.rows if row.metric_key is not None)
    if tuple(row.metric_key for row in numeric_rows) != _METRIC_KEYS:
        raise TMPage57MappingError("TM page-57 parsed metric order drifted")

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
                TMPage57SourceDisposition(
                    row_id=row.row_id,
                    ordinal=row.ordinal,
                    source_role=row.source_role,
                    metric_key=None,
                    status=TMPage57SourceStatus.SOURCE_ONLY_CONTEXT.value,
                    report_norm_ids=(),
                    observations=tuple(cell.observation.value for cell in row.row.cells),
                    values=tuple(cell.value for cell in row.row.cells),
                    period_starts=(None,) * 8,
                    period_ends=(None,) * 8,
                    period_roles=(None,) * 8,
                    period_types=(None,) * 8,
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
                raise TMPage57MappingError("TM page-57 assignment status/period drifted")
            source_by_schema[schema_id].append(row.row_id)
            assignments.append(
                TMPage57MappedAssignment(
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
                        "VISIBLE_PAGE57_METRIC_ROW_X_FIXED_INTEREST_RISK_AXIS_TO_FROZEN_SCHEMA"
                    ),
                )
            )
        source_dispositions.append(
            TMPage57SourceDisposition(
                row_id=row.row_id,
                ordinal=row.ordinal,
                source_role=row.source_role,
                metric_key=row.metric_key,
                status=TMPage57SourceStatus.MAPPED_AUTOMATIC_SCOPED.value,
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
                    "visible metric row and fixed interest-risk axis uniquely bind all eight cells; "
                    "values, dashes, and equations never select an item"
                ),
            )
        )
    if any(not source_by_schema[schema_id] for schema_id in _MAPPED_IDS):
        raise TMPage57MappingError("TM page-57 mapped item lacks source provenance")

    checks = _validations(parsed)
    if (
        len(checks) != TM_PAGE57_VALIDATION_CHECK_COUNT
        or sum(check.status == "PASS" for check in checks) != TM_PAGE57_VALIDATION_PASS_COUNT
        or sum(check.status.startswith("NOT_TESTABLE") for check in checks)
        != TM_PAGE57_VALIDATION_NOT_TESTABLE_COUNT
        or any(
            check.status == "FAIL"
            or (check.status == "PASS" and check.residual != 0)
            or (check.status.startswith("NOT_TESTABLE") and check.residual is not None)
            for check in checks
        )
    ):
        raise TMPage57MappingError("TM page-57 accounting validation failed")
    schema_dispositions = tuple(
        TMPage57SchemaDisposition(
            report_norm_id=item.schema_id,
            display_order=item.display_order,
            canonical_name=item.canonical_name,
            status=(
                TMPage57SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
                if item.schema_id in _MAPPED_IDS
                else TMPage57SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
                if item.schema_id in _NOT_OBSERVED_IDS
                else TMPage57SchemaStatus.UNASSESSED.value
            ),
            source_ids=tuple(dict.fromkeys(source_by_schema.get(item.schema_id, ()))),
            reason=(
                "page 57 is the unique scoped owner of this visible structural or value-bearing item"
                if item.schema_id in _MAPPED_IDS
                else "fully assessed scope item with no distinct visible page-57 source row"
                if item.schema_id in _NOT_OBSERVED_IDS
                else "outside the page-57 owned interest-rate-risk schema scope"
            ),
        )
        for item in tm_schema
    )
    result = TMPage57MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=57,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="PAGE57_INTEREST_RISK_SCOPE_RECONCILED_MAPPED_AND_VALIDATED",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=TM_PAGE57_SCOPE_SCHEMA_COUNT,
        mapped_schema_count=TM_PAGE57_MAPPED_SCHEMA_COUNT,
        structural_mapped_schema_count=TM_PAGE57_STRUCTURAL_MAPPED_SCHEMA_COUNT,
        value_bearing_mapped_schema_count=TM_PAGE57_VALUE_BEARING_MAPPED_SCHEMA_COUNT,
        not_observed_schema_count=TM_PAGE57_NOT_OBSERVED_SCHEMA_COUNT,
        not_applicable_schema_count=0,
        ambiguous_schema_count=0,
        unresolved_schema_count=0,
        unassessed_schema_count=TM_PAGE57_UNASSESSED_SCHEMA_COUNT,
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMPage57SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status == TMPage57SourceStatus.SOURCE_ONLY_CONTEXT.value
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
            "VISIBLE_PAGE57_METRIC_ROW_AND_FIXED_INTEREST_RISK_AXIS_ORDER",
            "VISIBLE_SNAPSHOT_PERIOD_UNIT_AND_CONSOLIDATED_SCOPE",
            "PIXEL_BACKED_DASH_STATUS_WITHOUT_ZERO_COERCION",
            "FROZEN_TM_SCHEMA_SCOPE_IDS_1483_THROUGH_1758_AND_5857_THROUGH_5897",
            "COMBINED_LOAN_AS_SIBLING_LEAF_WITHOUT_REPARENT_OR_FORMULA",
            "COMBINED_FIXED_PROPERTY_AS_PARENT_OF_TWO_REPARENTED_COMPONENTS",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
            "PAGE58_AS_DISJOINT_INDEPENDENT_OWNER",
        ),
    )
    return validate_tm_page57_mapping_result(result)


def validate_tm_page57_mapping_result(
    result: TMPage57MappingResult,
) -> TMPage57MappingResult:
    if (
        result.schema_item_count != TM_PAGE57_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE57_SCOPE_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE57_MAPPED_SCHEMA_COUNT
        or result.structural_mapped_schema_count != TM_PAGE57_STRUCTURAL_MAPPED_SCHEMA_COUNT
        or result.value_bearing_mapped_schema_count != TM_PAGE57_VALUE_BEARING_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE57_NOT_OBSERVED_SCHEMA_COUNT
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != 0
        or result.unresolved_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE57_UNASSESSED_SCHEMA_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE57_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE57_MAPPED_SOURCE_ROW_COUNT
        or result.source_only_row_count != TM_PAGE57_SOURCE_ONLY_ROW_COUNT
        or result.source_question_row_count != 0
        or result.financial_slot_count != TM_PAGE57_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE57_VALUE_COUNT
        or result.dash_count != TM_PAGE57_DASH_COUNT
        or result.mapped_assignment_count != TM_PAGE57_ASSIGNMENT_COUNT
        or result.validation_check_count != TM_PAGE57_VALIDATION_CHECK_COUNT
        or result.validation_pass_count != TM_PAGE57_VALIDATION_PASS_COUNT
        or result.validation_not_testable_count != TM_PAGE57_VALIDATION_NOT_TESTABLE_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage57MappingError("TM page-57 mapping denominator drifted")
    if result.status_reconciled_schema_count + result.unassessed_schema_count != (
        result.schema_item_count
    ):
        raise TMPage57MappingError("TM page-57 schema statuses do not reconcile")
    mapped = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage57SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    not_observed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage57SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    }
    unassessed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage57SchemaStatus.UNASSESSED.value
    }
    if (
        mapped != _MAPPED_IDS
        or not_observed != _NOT_OBSERVED_IDS
        or len(unassessed) != TM_PAGE57_UNASSESSED_SCHEMA_COUNT
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
        raise TMPage57MappingError("TM page-57 schema disposition partition drifted")
    if (
        tuple(item.status for item in result.source_dispositions).count(
            TMPage57SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        )
        != 20
        or tuple(item.status for item in result.source_dispositions).count(
            TMPage57SourceStatus.SOURCE_ONLY_CONTEXT.value
        )
        != 2
        or any(item.question_required for item in result.source_dispositions)
    ):
        raise TMPage57MappingError("TM page-57 source disposition drifted")
    dash_assignments = tuple(
        item for item in result.mapped_assignments if item.observation == ObservationKind.DASH.value
    )
    if (
        {item.report_norm_id for item in result.mapped_assignments} != _VALUE_IDS
        or len(dash_assignments) != 68
        or any(item.value is not None for item in dash_assignments)
        or sum(
            item.observation == ObservationKind.VALUE.value for item in result.mapped_assignments
        )
        != 92
        or {(item.unit, item.unit_multiplier) for item in result.mapped_assignments}
        != {("VND", 1_000_000)}
        or {item.period_type for item in result.mapped_assignments} != {"SNAPSHOT"}
    ):
        raise TMPage57MappingError("TM page-57 assignment partition drifted")
    kinds = tuple(check.check_kind for check in result.validation_checks)
    expected_splits = {
        "ROW_TOTAL_VALIDATION_ONLY": (20, 2, 18),
        "ASSET_COMPOSITION_VALIDATION_ONLY": (8, 0, 8),
        "LIABILITY_COMPOSITION_VALIDATION_ONLY": (8, 1, 7),
        "ON_BALANCE_GAP_VALIDATION_ONLY": (8, 7, 1),
    }
    for kind, (total, passed, not_testable) in expected_splits.items():
        selected = tuple(check for check in result.validation_checks if check.check_kind == kind)
        if (
            kinds.count(kind) != total
            or sum(check.status == "PASS" for check in selected) != passed
            or sum(check.status.startswith("NOT_TESTABLE") for check in selected) != not_testable
        ):
            raise TMPage57MappingError("TM page-57 validation split drifted")
    if any(
        check.status == "FAIL"
        or (check.status == "PASS" and check.residual != 0)
        or (check.status.startswith("NOT_TESTABLE") and check.residual is not None)
        for check in result.validation_checks
    ):
        raise TMPage57MappingError("TM page-57 validation result drifted")
    return result


__all__ = [
    "TM_PAGE57_MAPPING_POLICY_RELATIVE_PATH",
    "TMPage57MappedAssignment",
    "TMPage57MappingError",
    "TMPage57MappingPolicy",
    "TMPage57MappingResult",
    "TMPage57SchemaDisposition",
    "TMPage57SchemaStatus",
    "TMPage57SourceDisposition",
    "TMPage57SourceStatus",
    "TMPage57ValidationCheck",
    "load_tm_page57_mapping_policy",
    "reconcile_tm_page57_items",
    "validate_tm_page57_mapping_result",
]
