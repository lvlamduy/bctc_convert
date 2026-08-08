"""Hierarchy-safe mapping for MBB consolidated TM page 60 liquidity risk."""

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
from bctc_ai.tables.tm_note_page60 import ParsedTMPage60

TM_PAGE60_MAPPING_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page60-v1.yaml")
TM_PAGE60_SCHEMA_TOTAL = 1_701
TM_PAGE60_SCOPE_SCHEMA_COUNT = 222
TM_PAGE60_MAPPED_SCHEMA_COUNT = 148
TM_PAGE60_STRUCTURAL_MAPPED_SCHEMA_COUNT = 8
TM_PAGE60_VALUE_BEARING_MAPPED_SCHEMA_COUNT = 140
TM_PAGE60_NOT_OBSERVED_SCHEMA_COUNT = 74
TM_PAGE60_UNASSESSED_SCHEMA_COUNT = 1_479
TM_PAGE60_SOURCE_ROW_COUNT = 22
TM_PAGE60_MAPPED_SOURCE_ROW_COUNT = 20
TM_PAGE60_SOURCE_ONLY_ROW_COUNT = 2
TM_PAGE60_FINANCIAL_SLOT_COUNT = 140
TM_PAGE60_VALUE_COUNT = 93
TM_PAGE60_DASH_COUNT = 47
TM_PAGE60_ASSIGNMENT_COUNT = 140
TM_PAGE60_VALIDATION_CHECK_COUNT = 47
TM_PAGE60_VALIDATION_PASS_COUNT = 31
TM_PAGE60_VALIDATION_NOT_TESTABLE_COUNT = 16

TM_PAGE60_SCOPE_IDS = frozenset(range(1759, 1944)) | frozenset(range(5898, 5935))

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ROOT_ID = 1759
_AXIS_KEYS = (
    "OVERDUE",
    "WITHIN_1M",
    "FROM_1_TO_3M",
    "FROM_3_TO_12M",
    "FROM_1_TO_5Y",
    "OVER_5Y",
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
    "NET_LIQUIDITY_GAP",
)
_AXIS_PARENT_IDS = {
    "OVERDUE": 5898,
    "WITHIN_1M": 1806,
    "FROM_1_TO_3M": 1829,
    "FROM_3_TO_12M": 1852,
    "FROM_1_TO_5Y": 1875,
    "OVER_5Y": 1898,
    "TOTAL": 1921,
}
_AXIS_PERIOD_CONTRACT = tuple(
    (axis_key, "CURRENT", "SNAPSHOT", "2026-03-31", "2026-03-31", "VND", 1_000_000)
    for axis_key in _AXIS_KEYS
)
_METRIC_TARGET_IDS = {
    "CASH_AND_PRECIOUS_METALS": (5900, 1808, 1831, 1854, 1877, 1900, 1923),
    "SBV_DEPOSITS": (5901, 1809, 1832, 1855, 1878, 1901, 1924),
    "INTERBANK_ASSETS": (5902, 1810, 1833, 1856, 1879, 1902, 1925),
    "TRADING_SECURITIES": (5903, 1811, 1834, 1857, 1880, 1903, 1926),
    "DERIVATIVE_ASSETS": (5904, 1812, 1835, 1858, 1881, 1904, 1927),
    "CUSTOMER_LOANS_AND_PURCHASED_DEBT": (5905, 5923, 5925, 5927, 5929, 5931, 5933),
    "INVESTMENT_SECURITIES": (5907, 1814, 1837, 1860, 1883, 1906, 1929),
    "LONG_TERM_INVESTMENTS": (5908, 1815, 1838, 1861, 1884, 1907, 1930),
    "FIXED_ASSETS_AND_INVESTMENT_PROPERTY": (5909, 5924, 5926, 5928, 5930, 5932, 5934),
    "OTHER_ASSETS": (5912, 1818, 1841, 1864, 1887, 1910, 1933),
    "TOTAL_ASSETS": (5899, 1807, 1830, 1853, 1876, 1899, 1922),
    "GOVERNMENT_SBV_LIABILITIES": (5915, 1821, 1844, 1867, 1890, 1913, 1936),
    "INTERBANK_LIABILITIES": (5914, 1820, 1843, 1866, 1889, 1912, 1935),
    "CUSTOMER_DEPOSITS": (5917, 1823, 1846, 1869, 1892, 1915, 1938),
    "DERIVATIVE_LIABILITIES": (5918, 1824, 1847, 1870, 1893, 1916, 1939),
    "ENTRUSTED_FUNDS": (5919, 1825, 1848, 1871, 1894, 1917, 1940),
    "ISSUED_VALUABLE_PAPERS": (5920, 1826, 1849, 1872, 1895, 1918, 1941),
    "OTHER_LIABILITIES": (5921, 1827, 1850, 1873, 1896, 1919, 1942),
    "TOTAL_LIABILITIES": (5913, 1819, 1842, 1865, 1888, 1911, 1934),
    "NET_LIQUIDITY_GAP": (5922, 1828, 1851, 1874, 1897, 1920, 1943),
}
_VALUE_IDS = frozenset(schema_id for ids in _METRIC_TARGET_IDS.values() for schema_id in ids)
_STRUCTURAL_IDS = frozenset({_ROOT_ID, *_AXIS_PARENT_IDS.values()})
TM_PAGE60_MAPPED_SCHEMA_IDS = _VALUE_IDS | _STRUCTURAL_IDS
TM_PAGE60_NOT_OBSERVED_SCHEMA_IDS = TM_PAGE60_SCOPE_IDS - TM_PAGE60_MAPPED_SCHEMA_IDS
_EXPECTED_NOT_OBSERVED_IDS = frozenset(range(1760, 1806)) | frozenset(
    {
        1813,
        1816,
        1817,
        1822,
        1836,
        1839,
        1840,
        1845,
        1859,
        1862,
        1863,
        1868,
        1882,
        1885,
        1886,
        1891,
        1905,
        1908,
        1909,
        1914,
        1928,
        1931,
        1932,
        1937,
        5906,
        5910,
        5911,
        5916,
    }
)
_ROOT_CHILDREN = (5898, 1760, 1783, 1806, 1829, 1852, 1875, 1898, 1921)
_COMBINED_PAIRS = (
    (5898, 5905, 5909, 5906, 5910, 5911),
    (1806, 5923, 5924, 1813, 1816, 1817),
    (1829, 5925, 5926, 1836, 1839, 1840),
    (1852, 5927, 5928, 1859, 1862, 1863),
    (1875, 5929, 5930, 1882, 1885, 1886),
    (1898, 5931, 5932, 1905, 1908, 1909),
    (1921, 5933, 5934, 1928, 1931, 1932),
)
_EXTERNAL_PAGE57_IDS = {
    "CASH_AND_PRECIOUS_METALS": 1736,
    "SBV_DEPOSITS": 1737,
    "INTERBANK_ASSETS": 1738,
    "TRADING_SECURITIES": 1739,
    "DERIVATIVE_ASSETS": 1740,
    "CUSTOMER_LOANS_AND_PURCHASED_DEBT": 5896,
    "INVESTMENT_SECURITIES": 1742,
    "LONG_TERM_INVESTMENTS": 1743,
    "FIXED_ASSETS_AND_INVESTMENT_PROPERTY": 5897,
    "OTHER_ASSETS": 1746,
    "TOTAL_ASSETS": 1735,
    "GOVERNMENT_SBV_LIABILITIES": 1749,
    "INTERBANK_LIABILITIES": 1748,
    "CUSTOMER_DEPOSITS": 1751,
    "DERIVATIVE_LIABILITIES": 1752,
    "ENTRUSTED_FUNDS": 1753,
    "ISSUED_VALUABLE_PAPERS": 1754,
    "OTHER_LIABILITIES": 1755,
    "TOTAL_LIABILITIES": 1747,
    "NET_LIQUIDITY_GAP": 1756,
}
_EXPECTED_HIERARCHY_CONTRACT = {
    "root_children": list(_ROOT_CHILDREN),
    "combined_customer_loans_and_purchased_debt": {
        "role": "SIBLING_LEAF_AGGREGATE",
        "children": [],
        "formula": None,
        "reparent_existing_customer_loans": False,
    },
    "combined_fixed_assets_and_investment_property": {
        "role": "PARENT_OF_TWO_EXISTING_COMPONENTS",
        "formula": None,
        "reparent_existing_components": True,
    },
}
_EXPECTED_VALIDATION_CONTRACT = [
    {"kind": "ROW_TOTAL_VALIDATION_ONLY", "checks": 20, "pass": 5, "not_testable_dash": 15},
    {
        "kind": "ASSETS_MINUS_LIABILITIES_VALIDATION_ONLY",
        "checks": 7,
        "pass": 6,
        "not_testable_dash": 1,
    },
    {
        "kind": "EXTERNAL_PAGE57_TOTAL_VALIDATION_ONLY",
        "checks": 19,
        "pass": 19,
        "not_testable_dash": 0,
    },
    {"kind": "DUPLICATE_STATUS_EQUAL", "checks": 1, "pass": 1, "not_testable_dash": 0},
]
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text_as_item_selector",
    "numeric_value_magnitude_as_item_selector",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
    "accounting_equation_result_as_extracted_value",
    "schema_id_outside_page60_scope",
    "page57_value_as_page60_item_selector",
    "page57_value_as_page60_imputation",
    "page61_value_as_page60_item_selector",
    "page61_value_as_page60_imputation",
}

if (
    len(TM_PAGE60_SCOPE_IDS) != TM_PAGE60_SCOPE_SCHEMA_COUNT
    or len(TM_PAGE60_MAPPED_SCHEMA_IDS) != TM_PAGE60_MAPPED_SCHEMA_COUNT
    or len(_VALUE_IDS) != TM_PAGE60_VALUE_BEARING_MAPPED_SCHEMA_COUNT
    or TM_PAGE60_NOT_OBSERVED_SCHEMA_IDS != _EXPECTED_NOT_OBSERVED_IDS
    or len(TM_PAGE60_NOT_OBSERVED_SCHEMA_IDS) != TM_PAGE60_NOT_OBSERVED_SCHEMA_COUNT
):
    raise AssertionError("TM page-60 static scope partition drifted")


class TMPage60MappingError(ValueError):
    pass


class TMPage60SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage60SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_CONTEXT = "SOURCE_ONLY_CONTEXT"


@dataclass(frozen=True)
class TMPage60ExternalTotal:
    metric_key: str
    report_norm_id: int
    observation: str
    value: Decimal | None
    owner_scope: str


@dataclass(frozen=True)
class TMPage60MappingPolicy:
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
    axis_parent_ids: tuple[tuple[str, int], ...]
    metric_target_ids: tuple[tuple[str, tuple[int, ...]], ...]
    not_observed_schema_ids: tuple[int, ...]
    external_page57_totals: tuple[TMPage60ExternalTotal, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage60SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage60SourceDisposition:
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
class TMPage60MappedAssignment:
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
class TMPage60ValidationCheck:
    check_id: str
    check_kind: str
    axis_key: str | None
    metric_key: str | None
    status: str
    expected_value: Decimal | None
    observed_value: Decimal | None
    residual: Decimal | None
    expected_observation: str | None
    observed_observation: str | None
    target_report_norm_id: int
    external_report_norm_id: int | None
    external_owner_scope: str | None
    reason: str


@dataclass(frozen=True)
class TMPage60MappingResult:
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
    schema_dispositions: tuple[TMPage60SchemaDisposition, ...]
    source_dispositions: tuple[TMPage60SourceDisposition, ...]
    mapped_assignments: tuple[TMPage60MappedAssignment, ...]
    validation_checks: tuple[TMPage60ValidationCheck, ...]
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
        raise TMPage60MappingError(f"invalid positive TM page-60 field: {field}")
    return value


def _int_list(value: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise TMPage60MappingError(f"TM page-60 {field} is invalid")
    result = tuple(value)
    if len(set(result)) != len(result):
        raise TMPage60MappingError(f"TM page-60 {field} contains duplicates")
    return result


def _expanded_ids(value: Any, field: str) -> tuple[int, ...]:
    if not isinstance(value, dict) or not isinstance(value.get("ranges"), list):
        raise TMPage60MappingError(f"TM page-60 {field} is invalid")
    ids = list(_int_list(value.get("ids"), field, allow_empty=True))
    for record in value["ranges"]:
        if not isinstance(record, dict):
            raise TMPage60MappingError(f"TM page-60 {field} range is invalid")
        start = _positive_int(record, "start")
        end = _positive_int(record, "end")
        if end < start:
            raise TMPage60MappingError(f"TM page-60 {field} range is reversed")
        ids.extend(range(start, end + 1))
    if len(set(ids)) != len(ids):
        raise TMPage60MappingError(f"TM page-60 {field} contains duplicates")
    return tuple(sorted(ids))


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
        for schema_id in sorted(TM_PAGE60_SCOPE_IDS)
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_tm_page60_mapping_policy(path: Path) -> TMPage60MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage60MappingError(f"cannot load TM page-60 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE60_LIQUIDITY_RISK_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("document") != "MBB_CONSOLIDATED_Q1_2026"
        or payload.get("page_number") != 60
        or payload.get("page_tag") != "page-0060"
        or payload.get("report_scope") != "CONSOLIDATED"
        or payload.get("mapping_authority_scope")
        != "MBB_CONSOLIDATED_Q1_2026_PAGE60_IDS_1759_1943_AND_5898_5934_ONLY"
    ):
        raise TMPage60MappingError("TM page-60 mapping identity drifted")
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
        raise TMPage60MappingError("TM page-60 mapping hashes are invalid")
    table_policy = payload.get("source_table_policy")
    if table_policy != "config/tables/tm-note-page60-v1.yaml":
        raise TMPage60MappingError("TM page-60 source table policy path drifted")
    table_path = (path.parents[2] / str(table_policy)).resolve()
    if not table_path.is_file() or sha256_file(table_path) != hashes[0]:
        raise TMPage60MappingError("TM page-60 source table policy hash drifted")
    if (
        payload.get("schema_total") != TM_PAGE60_SCHEMA_TOTAL
        or payload.get("scope_schema_ids")
        != [{"start": 1759, "end": 1943}, {"start": 5898, "end": 5934}]
        or payload.get("scope_schema_total") != TM_PAGE60_SCOPE_SCHEMA_COUNT
        or payload.get("root_report_norm_id") != _ROOT_ID
    ):
        raise TMPage60MappingError("TM page-60 schema denominator/scope drifted")
    raw_axes = payload.get("axis_parent_ids")
    if not isinstance(raw_axes, dict) or tuple(raw_axes) != _AXIS_KEYS:
        raise TMPage60MappingError("TM page-60 axis parent order drifted")
    axis_ids = tuple((str(key), value) for key, value in raw_axes.items())
    if dict(axis_ids) != _AXIS_PARENT_IDS:
        raise TMPage60MappingError("TM page-60 axis parent targets drifted")
    raw_targets = payload.get("metric_target_ids")
    if not isinstance(raw_targets, dict) or tuple(raw_targets) != _METRIC_KEYS:
        raise TMPage60MappingError("TM page-60 metric target order drifted")
    targets = tuple(
        (str(key), _int_list(value, "metric targets")) for key, value in raw_targets.items()
    )
    if dict(targets) != _METRIC_TARGET_IDS:
        raise TMPage60MappingError("TM page-60 metric targets drifted")
    not_observed = _expanded_ids(payload.get("not_observed_schema_ids"), "not-observed IDs")
    if set(not_observed) != TM_PAGE60_NOT_OBSERVED_SCHEMA_IDS:
        raise TMPage60MappingError("TM page-60 not-observed partition drifted")
    if payload.get("hierarchy_contract") != _EXPECTED_HIERARCHY_CONTRACT:
        raise TMPage60MappingError("TM page-60 hierarchy contract drifted")
    if payload.get("validation_only_contract") != _EXPECTED_VALIDATION_CONTRACT:
        raise TMPage60MappingError("TM page-60 validation-only contract drifted")
    raw_external = payload.get("external_page57_totals_validation_only")
    if not isinstance(raw_external, list) or len(raw_external) != 20:
        raise TMPage60MappingError("TM page-60 page-57 external totals drifted")
    external = []
    for record in raw_external:
        if not isinstance(record, dict):
            raise TMPage60MappingError("TM page-60 page-57 external total is invalid")
        value = record.get("value")
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise TMPage60MappingError("TM page-60 page-57 external value is invalid")
        external.append(
            TMPage60ExternalTotal(
                metric_key=str(record.get("metric_key", "")),
                report_norm_id=_positive_int(record, "report_norm_id"),
                observation=str(record.get("observation", "")),
                value=Decimal(value) if value is not None else None,
                owner_scope=str(record.get("owner_scope", "")),
            )
        )
    if (
        tuple(item.metric_key for item in external) != _METRIC_KEYS
        or any(item.owner_scope != "page-0057" for item in external)
        or {item.metric_key: item.report_norm_id for item in external} != _EXTERNAL_PAGE57_IDS
        or any(
            (item.metric_key == "DERIVATIVE_ASSETS")
            != (item.observation == ObservationKind.DASH.value and item.value is None)
            for item in external
        )
        or any(
            item.metric_key != "DERIVATIVE_ASSETS"
            and (item.observation != ObservationKind.VALUE.value or item.value is None)
            for item in external
        )
    ):
        raise TMPage60MappingError("TM page-60 page-57 external contract drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage60MappingError("TM page-60 forbidden inputs drifted")
    return TMPage60MappingPolicy(
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
        schema_total=TM_PAGE60_SCHEMA_TOTAL,
        scope_schema_ids=tuple(sorted(TM_PAGE60_SCOPE_IDS)),
        schema_scope_sha256=str(hashes[7]),
        root_report_norm_id=_ROOT_ID,
        axis_parent_ids=axis_ids,
        metric_target_ids=targets,
        not_observed_schema_ids=not_observed,
        external_page57_totals=tuple(external),
        forbidden_mapping_inputs=tuple(str(item) for item in forbidden),
        policy_sha256=sha256_file(path),
    )


def _validate_schema_branch(schema_by_id: dict[int, SchemaItem]) -> None:
    root = schema_by_id[_ROOT_ID]
    if root.parent_id != 1259 or tuple(root.children) != _ROOT_CHILDREN:
        raise TMPage60MappingError("TM page-60 liquidity-risk root hierarchy drifted")
    for axis_index, (axis_key, parent_id) in enumerate(_AXIS_PARENT_IDS.items()):
        if schema_by_id[parent_id].parent_id != _ROOT_ID:
            raise TMPage60MappingError(f"TM page-60 axis parent hierarchy drifted: {axis_key}")
        for metric_key, ids in _METRIC_TARGET_IDS.items():
            if schema_by_id[ids[axis_index]].parent_id != parent_id:
                raise TMPage60MappingError(
                    f"TM page-60 direct metric hierarchy drifted: {axis_key}/{metric_key}"
                )
    for parent_id, loan_id, fixed_id, old_loan_id, fixed_a, fixed_b in _COMBINED_PAIRS:
        if (
            schema_by_id[loan_id].parent_id != parent_id
            or schema_by_id[loan_id].children
            or schema_by_id[old_loan_id].parent_id != parent_id
            or schema_by_id[fixed_id].parent_id != parent_id
            or tuple(schema_by_id[fixed_id].children) != (fixed_a, fixed_b)
            or schema_by_id[fixed_a].parent_id != fixed_id
            or schema_by_id[fixed_b].parent_id != fixed_id
        ):
            raise TMPage60MappingError("TM page-60 combined-item hierarchy drifted")


def _arithmetic_check(
    *,
    check_id: str,
    check_kind: str,
    axis_key: str | None,
    metric_key: str | None,
    operands: Sequence[Any],
    observed_cell: Any,
    target_report_norm_id: int,
    subtract: bool = False,
) -> TMPage60ValidationCheck:
    has_dash = observed_cell.observation is ObservationKind.DASH or any(
        cell.observation is ObservationKind.DASH for cell in operands
    )
    if has_dash:
        return TMPage60ValidationCheck(
            check_id=check_id,
            check_kind=check_kind,
            axis_key=axis_key,
            metric_key=metric_key,
            status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
            expected_value=None,
            observed_value=observed_cell.value,
            residual=None,
            expected_observation=None,
            observed_observation=observed_cell.observation.value,
            target_report_norm_id=target_report_norm_id,
            external_report_norm_id=None,
            external_owner_scope=None,
            reason=(
                "the printed arithmetic contains at least one DASH and is not testable; DASH is "
                "never coerced to zero"
            ),
        )
    if observed_cell.value is None or any(cell.value is None for cell in operands):
        raise TMPage60MappingError("TM page-60 arithmetic validation operand is absent")
    if subtract:
        if len(operands) != 2:
            raise TMPage60MappingError("TM page-60 subtraction arity drifted")
        expected = operands[0].value - operands[1].value
    else:
        expected = sum((cell.value for cell in operands), Decimal(0))
    residual = observed_cell.value - expected
    return TMPage60ValidationCheck(
        check_id=check_id,
        check_kind=check_kind,
        axis_key=axis_key,
        metric_key=metric_key,
        status="PASS" if residual == 0 else "FAIL",
        expected_value=expected,
        observed_value=observed_cell.value,
        residual=residual,
        expected_observation=ObservationKind.VALUE.value,
        observed_observation=observed_cell.observation.value,
        target_report_norm_id=target_report_norm_id,
        external_report_norm_id=None,
        external_owner_scope=None,
        reason="the printed equation is tested after mapping and never selects or populates an item",
    )


def _validations(
    parsed: ParsedTMPage60, policy: TMPage60MappingPolicy
) -> tuple[TMPage60ValidationCheck, ...]:
    rows = {row.metric_key: row for row in parsed.rows if row.metric_key is not None}
    checks: list[TMPage60ValidationCheck] = []
    for metric_key in _METRIC_KEYS:
        row = rows[metric_key]
        checks.append(
            _arithmetic_check(
                check_id=f"ROW_TOTAL_{metric_key}",
                check_kind="ROW_TOTAL_VALIDATION_ONLY",
                axis_key="TOTAL",
                metric_key=metric_key,
                operands=row.row.cells[:6],
                observed_cell=row.row.cells[6],
                target_report_norm_id=_METRIC_TARGET_IDS[metric_key][6],
            )
        )
    for axis_index, axis_key in enumerate(_AXIS_KEYS):
        checks.append(
            _arithmetic_check(
                check_id=f"ASSETS_MINUS_LIABILITIES_{axis_key}",
                check_kind="ASSETS_MINUS_LIABILITIES_VALIDATION_ONLY",
                axis_key=axis_key,
                metric_key="NET_LIQUIDITY_GAP",
                operands=(
                    rows["TOTAL_ASSETS"].row.cells[axis_index],
                    rows["TOTAL_LIABILITIES"].row.cells[axis_index],
                ),
                observed_cell=rows["NET_LIQUIDITY_GAP"].row.cells[axis_index],
                target_report_norm_id=_METRIC_TARGET_IDS["NET_LIQUIDITY_GAP"][axis_index],
                subtract=True,
            )
        )
    external_by_metric = {item.metric_key: item for item in policy.external_page57_totals}
    for metric_key in _METRIC_KEYS:
        external = external_by_metric[metric_key]
        observed = rows[metric_key].row.cells[6]
        target_id = _METRIC_TARGET_IDS[metric_key][6]
        if metric_key == "DERIVATIVE_ASSETS":
            equal = (
                external.observation == ObservationKind.DASH.value
                and observed.observation is ObservationKind.DASH
                and external.value is None
                and observed.value is None
            )
            checks.append(
                TMPage60ValidationCheck(
                    check_id="EXTERNAL_PAGE57_DERIVATIVE_ASSETS_STATUS",
                    check_kind="DUPLICATE_STATUS_EQUAL",
                    axis_key="TOTAL",
                    metric_key=metric_key,
                    status="PASS" if equal else "FAIL",
                    expected_value=None,
                    observed_value=None,
                    residual=None,
                    expected_observation=external.observation,
                    observed_observation=observed.observation.value,
                    target_report_norm_id=target_id,
                    external_report_norm_id=external.report_norm_id,
                    external_owner_scope=external.owner_scope,
                    reason=(
                        "typed page-57/page-60 DASH status consistency only; this is not an "
                        "arithmetic equality and DASH is never coerced to zero"
                    ),
                )
            )
            continue
        if observed.observation is not ObservationKind.VALUE or observed.value is None:
            raise TMPage60MappingError("TM page-60 numeric page-57 comparison operand drifted")
        if external.value is None:
            raise TMPage60MappingError("TM page-60 numeric page-57 external value is absent")
        residual = observed.value - external.value
        checks.append(
            TMPage60ValidationCheck(
                check_id=f"EXTERNAL_PAGE57_TOTAL_{metric_key}",
                check_kind="EXTERNAL_PAGE57_TOTAL_VALIDATION_ONLY",
                axis_key="TOTAL",
                metric_key=metric_key,
                status="PASS" if residual == 0 else "FAIL",
                expected_value=external.value,
                observed_value=observed.value,
                residual=residual,
                expected_observation=external.observation,
                observed_observation=observed.observation.value,
                target_report_norm_id=target_id,
                external_report_norm_id=external.report_norm_id,
                external_owner_scope=external.owner_scope,
                reason=(
                    "page-57 total is an external validation-only value owned by page-0057; it "
                    "never selects, maps, or imputes the page-60 item"
                ),
            )
        )
    return tuple(checks)


def reconcile_tm_page60_items(
    parsed: ParsedTMPage60,
    *,
    schema: Sequence[SchemaItem],
    policy: TMPage60MappingPolicy,
    source_pdf_path: Path,
    schema_workbook_path: Path,
) -> TMPage60MappingResult:
    if (
        policy.mapping_authority_scope
        != "MBB_CONSOLIDATED_Q1_2026_PAGE60_IDS_1759_1943_AND_5898_5934_ONLY"
        or policy.root_report_norm_id != _ROOT_ID
        or dict(policy.axis_parent_ids) != _AXIS_PARENT_IDS
        or dict(policy.metric_target_ids) != _METRIC_TARGET_IDS
        or set(policy.not_observed_schema_ids) != TM_PAGE60_NOT_OBSERVED_SCHEMA_IDS
        or set(policy.forbidden_mapping_inputs) != _REQUIRED_FORBIDDEN
        or {item.metric_key: item.report_norm_id for item in policy.external_page57_totals}
        != _EXTERNAL_PAGE57_IDS
        or tuple(item.metric_key for item in policy.external_page57_totals) != _METRIC_KEYS
        or any(item.owner_scope != "page-0057" for item in policy.external_page57_totals)
        or any(
            (item.metric_key == "DERIVATIVE_ASSETS")
            != (item.observation == ObservationKind.DASH.value and item.value is None)
            for item in policy.external_page57_totals
        )
        or any(
            item.metric_key != "DERIVATIVE_ASSETS"
            and (item.observation != ObservationKind.VALUE.value or item.value is None)
            for item in policy.external_page57_totals
        )
    ):
        raise TMPage60MappingError("TM page-60 mapping policy target drifted")
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
        or parsed.upstream_ocr_sha256 != policy.upstream_ocr_sha256
    ):
        raise TMPage60MappingError("TM page-60 parser/mapping identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage60MappingError("TM page-60 source PDF hash drifted")
    if sha256_file(schema_workbook_path) != policy.schema_workbook_sha256:
        raise TMPage60MappingError("TM page-60 schema workbook hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != TM_PAGE60_SCHEMA_TOTAL or len(tm_schema) != policy.schema_total:
        raise TMPage60MappingError("TM page-60 schema denominator drifted")
    projection_hash = _schema_projection_hash(tm_schema)
    if projection_hash != policy.schema_projection_sha256:
        raise TMPage60MappingError("TM page-60 full schema projection drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if (
        set(policy.scope_schema_ids) != TM_PAGE60_SCOPE_IDS
        or _schema_scope_hash(schema_by_id) != policy.schema_scope_sha256
    ):
        raise TMPage60MappingError("TM page-60 owned schema scope drifted")
    _validate_schema_branch(schema_by_id)
    if (
        tuple(
            (
                axis.axis_key,
                axis.period_role,
                axis.period_type,
                axis.period_start.isoformat(),
                axis.period_end.isoformat(),
                axis.canonical_unit,
                axis.unit_multiplier,
            )
            for axis in parsed.axes
        )
        != _AXIS_PERIOD_CONTRACT
    ):
        raise TMPage60MappingError("TM page-60 parsed axis period/unit order drifted")
    numeric_rows = tuple(row for row in parsed.rows if row.metric_key is not None)
    if tuple(row.metric_key for row in numeric_rows) != _METRIC_KEYS:
        raise TMPage60MappingError("TM page-60 parsed metric order drifted")

    source_by_schema: dict[int, list[str]] = {
        schema_id: [] for schema_id in TM_PAGE60_MAPPED_SCHEMA_IDS
    }
    source_by_schema[_ROOT_ID].append(
        f"{parsed.page_tag}:line-{parsed.table.title_line_indices[0]:04d}"
    )
    for axis, parent_id in zip(parsed.axes, _AXIS_PARENT_IDS.values(), strict=True):
        source_by_schema[parent_id].extend(
            f"{parsed.page_tag}:line-{index:04d}" for index in axis.header_line_indices
        )
    assignments: list[TMPage60MappedAssignment] = []
    source_dispositions: list[TMPage60SourceDisposition] = []
    targets = dict(policy.metric_target_ids)
    for row in parsed.rows:
        if row.metric_key is None:
            source_dispositions.append(
                TMPage60SourceDisposition(
                    row_id=row.row_id,
                    ordinal=row.ordinal,
                    source_role=row.source_role,
                    metric_key=None,
                    status=TMPage60SourceStatus.SOURCE_ONLY_CONTEXT.value,
                    report_norm_ids=(),
                    observations=tuple(cell.observation.value for cell in row.row.cells),
                    values=tuple(cell.value for cell in row.row.cells),
                    period_starts=(None,) * 7,
                    period_ends=(None,) * 7,
                    period_roles=(None,) * 7,
                    period_types=(None,) * 7,
                    unit="VND",
                    unit_multiplier=1_000_000,
                    question_required=False,
                    reason="visible asset/liability section heading supplies source context only",
                )
            )
            continue
        if (
            tuple(
                (
                    role,
                    period_type,
                    start.isoformat() if start is not None else None,
                    end.isoformat() if end is not None else None,
                )
                for role, period_type, start, end in zip(
                    row.cell_period_roles,
                    row.cell_period_types,
                    row.cell_period_starts,
                    row.cell_period_ends,
                    strict=True,
                )
            )
            != (("CURRENT", "SNAPSHOT", "2026-03-31", "2026-03-31"),) * 7
        ):
            raise TMPage60MappingError("TM page-60 row/header period alignment drifted")
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
                or cell.observation not in {ObservationKind.VALUE, ObservationKind.DASH}
                or (cell.observation is ObservationKind.DASH) != (cell.value is None)
                or (axis.canonical_unit, axis.unit_multiplier) != ("VND", 1_000_000)
            ):
                raise TMPage60MappingError("TM page-60 assignment status/period/unit drifted")
            source_by_schema[schema_id].append(row.row_id)
            assignments.append(
                TMPage60MappedAssignment(
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
                        "VISIBLE_PAGE60_METRIC_ROW_X_FIXED_LIQUIDITY_AXIS_TO_FROZEN_SCHEMA"
                    ),
                )
            )
        source_dispositions.append(
            TMPage60SourceDisposition(
                row_id=row.row_id,
                ordinal=row.ordinal,
                source_role=row.source_role,
                metric_key=row.metric_key,
                status=TMPage60SourceStatus.MAPPED_AUTOMATIC_SCOPED.value,
                report_norm_ids=report_norm_ids,
                observations=tuple(cell.observation.value for cell in row.row.cells),
                values=tuple(cell.value for cell in row.row.cells),
                period_starts=tuple(
                    value.isoformat() if value else None for value in row.cell_period_starts
                ),
                period_ends=tuple(
                    value.isoformat() if value else None for value in row.cell_period_ends
                ),
                period_roles=row.cell_period_roles,
                period_types=row.cell_period_types,
                unit="VND",
                unit_multiplier=1_000_000,
                question_required=False,
                reason=(
                    "visible metric row and fixed liquidity axis uniquely bind all seven cells; "
                    "values, dashes, and equations never select an item"
                ),
            )
        )
    if any(not source_by_schema[schema_id] for schema_id in TM_PAGE60_MAPPED_SCHEMA_IDS):
        raise TMPage60MappingError("TM page-60 mapped item lacks source provenance")

    checks = _validations(parsed, policy)
    if (
        len(checks) != TM_PAGE60_VALIDATION_CHECK_COUNT
        or sum(check.status == "PASS" for check in checks) != TM_PAGE60_VALIDATION_PASS_COUNT
        or sum(check.status.startswith("NOT_TESTABLE") for check in checks)
        != TM_PAGE60_VALIDATION_NOT_TESTABLE_COUNT
        or any(
            check.status == "FAIL"
            or (
                check.status == "PASS"
                and check.check_kind != "DUPLICATE_STATUS_EQUAL"
                and check.residual != 0
            )
            or (check.status.startswith("NOT_TESTABLE") and check.residual is not None)
            for check in checks
        )
    ):
        raise TMPage60MappingError("TM page-60 validation contract failed")
    schema_dispositions = tuple(
        TMPage60SchemaDisposition(
            report_norm_id=item.schema_id,
            display_order=item.display_order,
            canonical_name=item.canonical_name,
            status=(
                TMPage60SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
                if item.schema_id in TM_PAGE60_MAPPED_SCHEMA_IDS
                else TMPage60SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
                if item.schema_id in TM_PAGE60_NOT_OBSERVED_SCHEMA_IDS
                else TMPage60SchemaStatus.UNASSESSED.value
            ),
            source_ids=tuple(dict.fromkeys(source_by_schema.get(item.schema_id, ()))),
            reason=(
                "page 60 is the unique scoped owner of this visible liquidity structural or value item"
                if item.schema_id in TM_PAGE60_MAPPED_SCHEMA_IDS
                else "fully assessed liquidity-scope item with no distinct visible page-60 source row"
                if item.schema_id in TM_PAGE60_NOT_OBSERVED_SCHEMA_IDS
                else "outside the page-60 owned liquidity-risk schema scope"
            ),
        )
        for item in tm_schema
    )
    result = TMPage60MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=60,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="PAGE60_LIQUIDITY_RISK_SCOPE_RECONCILED_MAPPED_AND_VALIDATED",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=TM_PAGE60_SCOPE_SCHEMA_COUNT,
        mapped_schema_count=TM_PAGE60_MAPPED_SCHEMA_COUNT,
        structural_mapped_schema_count=TM_PAGE60_STRUCTURAL_MAPPED_SCHEMA_COUNT,
        value_bearing_mapped_schema_count=TM_PAGE60_VALUE_BEARING_MAPPED_SCHEMA_COUNT,
        not_observed_schema_count=TM_PAGE60_NOT_OBSERVED_SCHEMA_COUNT,
        not_applicable_schema_count=0,
        ambiguous_schema_count=0,
        unresolved_schema_count=0,
        unassessed_schema_count=TM_PAGE60_UNASSESSED_SCHEMA_COUNT,
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMPage60SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status == TMPage60SourceStatus.SOURCE_ONLY_CONTEXT.value
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
        schema_projection_sha256=projection_hash,
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS_AND_GEOMETRY",
            "VISIBLE_PAGE60_METRIC_ROW_AND_FIXED_LIQUIDITY_AXIS_ORDER",
            "VISIBLE_SNAPSHOT_PERIOD_VND_MILLION_AND_CONSOLIDATED_SCOPE",
            "PIXEL_BACKED_DASH_STATUS_WITHOUT_ZERO_COERCION",
            "FROZEN_TM_SCHEMA_SCOPE_IDS_1759_THROUGH_1943_AND_5898_THROUGH_5934",
            "COMBINED_LOAN_AS_SIBLING_LEAF_WITHOUT_REPARENT_OR_FORMULA",
            "COMBINED_FIXED_PROPERTY_AS_PARENT_OF_TWO_REPARENTED_COMPONENTS",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
            "PAGE57_TOTALS_AS_EXTERNAL_VALIDATION_ONLY_WITH_DISJOINT_OWNERSHIP",
            "DERIVATIVE_DASH_COMPARISON_AS_TYPED_STATUS_EQUALITY_NOT_ARITHMETIC",
            "PAGE61_AS_DISJOINT_INDEPENDENT_OWNER",
        ),
    )
    return validate_tm_page60_mapping_result(result)


def validate_tm_page60_mapping_result(result: TMPage60MappingResult) -> TMPage60MappingResult:
    if (
        result.schema_item_count != TM_PAGE60_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE60_SCOPE_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE60_MAPPED_SCHEMA_COUNT
        or result.structural_mapped_schema_count != TM_PAGE60_STRUCTURAL_MAPPED_SCHEMA_COUNT
        or result.value_bearing_mapped_schema_count != TM_PAGE60_VALUE_BEARING_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE60_NOT_OBSERVED_SCHEMA_COUNT
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != 0
        or result.unresolved_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE60_UNASSESSED_SCHEMA_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE60_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE60_MAPPED_SOURCE_ROW_COUNT
        or result.source_only_row_count != TM_PAGE60_SOURCE_ONLY_ROW_COUNT
        or result.source_question_row_count != 0
        or result.financial_slot_count != TM_PAGE60_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE60_VALUE_COUNT
        or result.dash_count != TM_PAGE60_DASH_COUNT
        or result.mapped_assignment_count != TM_PAGE60_ASSIGNMENT_COUNT
        or result.validation_check_count != TM_PAGE60_VALIDATION_CHECK_COUNT
        or result.validation_pass_count != TM_PAGE60_VALIDATION_PASS_COUNT
        or result.validation_not_testable_count != TM_PAGE60_VALIDATION_NOT_TESTABLE_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage60MappingError("TM page-60 mapping denominator drifted")
    mapped = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage60SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    not_observed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage60SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    }
    unassessed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage60SchemaStatus.UNASSESSED.value
    }
    if (
        result.status_reconciled_schema_count + result.unassessed_schema_count
        != result.schema_item_count
        or mapped != TM_PAGE60_MAPPED_SCHEMA_IDS
        or not_observed != TM_PAGE60_NOT_OBSERVED_SCHEMA_IDS
        or len(unassessed) != TM_PAGE60_UNASSESSED_SCHEMA_COUNT
        or mapped | not_observed | unassessed
        != {item.report_norm_id for item in result.schema_dispositions}
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
        raise TMPage60MappingError("TM page-60 disposition partition drifted")
    dash_assignments = tuple(
        item for item in result.mapped_assignments if item.observation == ObservationKind.DASH.value
    )
    if (
        {item.report_norm_id for item in result.mapped_assignments} != _VALUE_IDS
        or len(dash_assignments) != TM_PAGE60_DASH_COUNT
        or any(item.value is not None for item in dash_assignments)
        or sum(
            item.observation == ObservationKind.VALUE.value for item in result.mapped_assignments
        )
        != TM_PAGE60_VALUE_COUNT
        or {(item.unit, item.unit_multiplier) for item in result.mapped_assignments}
        != {("VND", 1_000_000)}
        or {item.period_type for item in result.mapped_assignments} != {"SNAPSHOT"}
        or {item.period_start for item in result.mapped_assignments} != {"2026-03-31"}
        or {item.period_end for item in result.mapped_assignments} != {"2026-03-31"}
    ):
        raise TMPage60MappingError("TM page-60 assignment partition drifted")
    expected_splits = {
        "ROW_TOTAL_VALIDATION_ONLY": (20, 5, 15),
        "ASSETS_MINUS_LIABILITIES_VALIDATION_ONLY": (7, 6, 1),
        "EXTERNAL_PAGE57_TOTAL_VALIDATION_ONLY": (19, 19, 0),
        "DUPLICATE_STATUS_EQUAL": (1, 1, 0),
    }
    for kind, (total, passed, not_testable) in expected_splits.items():
        selected = tuple(check for check in result.validation_checks if check.check_kind == kind)
        if (
            len(selected) != total
            or sum(check.status == "PASS" for check in selected) != passed
            or sum(check.status.startswith("NOT_TESTABLE") for check in selected) != not_testable
        ):
            raise TMPage60MappingError("TM page-60 validation split drifted")
    status_checks = tuple(
        check for check in result.validation_checks if check.check_kind == "DUPLICATE_STATUS_EQUAL"
    )
    if (
        len(status_checks) != 1
        or status_checks[0].expected_observation != ObservationKind.DASH.value
        or status_checks[0].observed_observation != ObservationKind.DASH.value
        or status_checks[0].expected_value is not None
        or status_checks[0].observed_value is not None
        or status_checks[0].residual is not None
        or any(
            check.status == "FAIL"
            or (
                check.status == "PASS"
                and check.check_kind != "DUPLICATE_STATUS_EQUAL"
                and check.residual != 0
            )
            or (check.status.startswith("NOT_TESTABLE") and check.residual is not None)
            for check in result.validation_checks
        )
    ):
        raise TMPage60MappingError("TM page-60 validation result drifted")
    return result


__all__ = [
    "TM_PAGE60_MAPPING_POLICY_RELATIVE_PATH",
    "TM_PAGE60_MAPPED_SCHEMA_IDS",
    "TM_PAGE60_NOT_OBSERVED_SCHEMA_IDS",
    "TM_PAGE60_SCOPE_IDS",
    "TMPage60ExternalTotal",
    "TMPage60MappedAssignment",
    "TMPage60MappingError",
    "TMPage60MappingPolicy",
    "TMPage60MappingResult",
    "TMPage60SchemaDisposition",
    "TMPage60SchemaStatus",
    "TMPage60SourceDisposition",
    "TMPage60SourceStatus",
    "TMPage60ValidationCheck",
    "load_tm_page60_mapping_policy",
    "reconcile_tm_page60_items",
    "validate_tm_page60_mapping_result",
]
