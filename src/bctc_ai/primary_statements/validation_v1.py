"""Accounting corroboration of mapped PRIMARY values.

Equations are the schema registry's formula parents (after the audited
business overlay), evaluated lane by lane over mapped, observed values only:

* the direct frontier of a parent is its mapped children; an unmapped child
  that has its own children is replaced by its children (so an unprinted
  subtotal does not hide its components), an unmapped leaf is ABSENT;
* a parent and its descendants are never summed together;
* if the parent's printed source children include a valued row without a
  schema identity, the frontier is incomplete and cannot FAIL;
* a BLANK cell makes that lane NOT_EVALUABLE; a printed dash is a numeric
  zero only when no valued component contradicts it (validated DASH_ZERO);
* deductions enter by declared role: pure deductions as -|value|, reversible
  ones by the instance's printed convention (an alternate unsigned reading is
  reported separately, never written back), NCI attribution as printed.

Rounding is accepted only under the declared policy for statements printed in
millions or larger. A FAIL needs a complete frontier. No value is altered.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.primary_statements.assembly_v1 import StatementInstance
from bctc_ai.primary_statements.catalog_v1 import PrimaryCatalog
from bctc_ai.primary_statements.mapping_v1 import (
    MAPPED,
    PER_SHARE_IDS,
    RowDisposition,
    cell_observation_v1,
)
from bctc_ai.primary_statements.units_v1 import SCALE

VALIDATION_VERSION = "PRIMARY_ACCOUNTING_VALIDATION_V1"
EQUATIONS_RELATIVE_PATH = "config/primary_statements/equations_v1.yaml"
PASS_STATES = {"PASS", "PASS_WITHIN_DECLARED_ROUNDING", "PASS_UNDER_ALTERNATE_SIGN_READING"}


@dataclass
class EquationResult:
    equation_id: str
    kind: str
    parent: int | None
    lane: int
    period_key: str | None
    status: str
    reason: str | None
    terms: list[dict[str, Any]] = field(default_factory=list)
    absent: list[int] = field(default_factory=list)
    left: str | None = None
    right: str | None = None
    residual: str | None = None
    convention: str | None = None
    tolerance: str | None = None

    def participants(self) -> list[int]:
        ids = [term["report_norm_id"] for term in self.terms]
        return ([self.parent] if self.parent is not None else []) + ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "equation_id": self.equation_id, "kind": self.kind, "parent": self.parent, "lane": self.lane,
            "period_key": self.period_key, "status": self.status, "reason": self.reason, "terms": self.terms,
            "absent_components": self.absent, "left": self.left, "right": self.right, "residual": self.residual,
            "sign_convention": self.convention, "rounding_tolerance": self.tolerance,
        }


@dataclass
class EquationConfig:
    raw_sha256: str
    statements: dict[str, dict[str, Any]]
    rounding: dict[str, Any]


def load_equation_config_v1(project_root: Path) -> EquationConfig:
    raw = (project_root / EQUATIONS_RELATIVE_PATH).read_bytes()
    payload = yaml.safe_load(raw.decode("utf-8"))
    if payload.get("format_version") != "PRIMARY_STATEMENT_EQUATIONS_V1":
        raise ValueError("equation config format drifted")
    return EquationConfig(hashlib.sha256(raw).hexdigest(), payload["statements"], payload["rounding_policy"])


def _children_by_parent(catalog: PrimaryCatalog, statement: str, non_additive: set[int]) -> dict[int, list[int]]:
    result: dict[int, list[int]] = defaultdict(list)
    items = [item for (st, _), item in catalog.schema_items.items() if st == statement]
    for item in sorted(items, key=lambda item: item.display_order):
        if item.parent_id is not None and item.schema_id not in non_additive:
            result[item.parent_id].append(item.schema_id)
    return result


def _convention(values: dict[int, list[Decimal | None]], witnesses: list[int]) -> str:
    signs = set()
    for rnid in witnesses:
        for value in values.get(rnid, []):
            if value is not None and value != 0:
                signs.add(value < 0)
    if signs == {True}:
        return "SIGNED_AS_PRINTED"
    if signs == {False}:
        return "UNSIGNED_DEDUCTIONS"
    return "MIXED" if signs else "UNKNOWN"


class _Roles:
    def __init__(self, spec: dict[str, Any], convention: str):
        self.pure = set(spec["pure_deductions"])
        self.reversible = set(spec["reversible_deductions"])
        self.subtract = set(spec["always_subtract_as_printed"])
        self.convention = convention

    def orient(self, rnid: int, value: Decimal, alternate: bool) -> Decimal | None:
        """Value in economic orientation (income/asset positive, deduction negative)."""

        if rnid in self.pure:
            return -abs(value)
        if rnid in self.reversible:
            if alternate:
                return -abs(value)
            if self.convention == "SIGNED_AS_PRINTED":
                return value
            if self.convention == "UNSIGNED_DEDUCTIONS":
                return -value
            return None if value != 0 else value
        if rnid in self.subtract:
            return -value
        return value


def _numeric_values(mapped: dict[int, RowDisposition]) -> tuple[dict[int, list[Decimal | None]], dict[int, list[str]]]:
    values, states = {}, {}
    for rnid, item in mapped.items():
        lane_values, lane_states = [], []
        for cell in item.row.cells:
            state, value, _ = cell_observation_v1(cell)
            lane_states.append(state)
            lane_values.append(Decimal(value) if value is not None and state != "UNRESOLVED_CELL" else None)
        values[rnid], states[rnid] = lane_values, lane_states
    return values, states


def validate_instance_v1(
    instance: StatementInstance,
    dispositions: list[RowDisposition],
    catalog: PrimaryCatalog,
    config: EquationConfig,
) -> list[EquationResult]:
    statement = instance.statement
    spec = config.statements[statement]
    children = _children_by_parent(catalog, statement, set(spec["non_additive_children"]))
    mapped = {
        item.report_norm_id: item for item in dispositions
        if item.disposition == MAPPED and item.report_norm_id is not None and item.report_norm_id not in PER_SHARE_IDS
    }
    row_index = {id(item.row): position for position, item in enumerate(dispositions)}
    values, states = _numeric_values(mapped)
    roles = _Roles(spec, _convention(values, spec["convention_witnesses"]))
    results: list[EquationResult] = []

    def frontier(rnid: int, seen: set[int]) -> tuple[list[int], list[int]]:
        terms, absent = [], []
        for child in children.get(rnid, []):
            if child in seen:
                continue
            if child in mapped:
                terms.append(child)
            elif children.get(child):
                sub_terms, sub_absent = frontier(child, seen | {child})
                if sub_terms:
                    terms += sub_terms
                    absent += sub_absent
                else:
                    absent.append(child)
            else:
                absent.append(child)
        return terms, absent

    def unmapped_source_children(rnid: int) -> list[str]:
        position = row_index[id(mapped[rnid].row)]
        found = []
        for item in dispositions:
            if item.row.parent_row == position and item.row.has_numeric and item.report_norm_id is None \
                    and item.disposition not in {"STRUCTURAL"}:
                found.append(item.row.label_exact or item.row.uid)
        return found

    order = catalog.statements[statement].items
    equations = []
    for parent in sorted(mapped, key=lambda rnid: order[rnid].display_order):
        if children.get(parent):
            terms, absent = frontier(parent, {parent})
            if terms:
                equations.append((parent, terms, absent, unmapped_source_children(parent)))
    # Validated DASH_ZERO: a dash on a parent whose valued components do not sum
    # to zero is not a numeric zero; the lane becomes non-numeric (DASH).
    for parent, terms, _absent, _extra in equations:
        for lane in range(len(instance.lanes)):
            if lane < len(states[parent]) and states[parent][lane] == "DASH_ZERO":
                component = [values[t][lane] for t in terms if lane < len(values[t]) and values[t][lane] is not None]
                if any(value != 0 for value in component):
                    instance.dash_unvalidated.add((parent, lane))
                    values[parent][lane] = None
    for parent, terms, absent, extra in equations:
        for lane_index, lane in enumerate(instance.lanes):
            key = lane.period.get("key") if lane.period else None
            unit_scale = SCALE.get(lane.unit or "", 0)
            result = EquationResult(f"{statement}:{parent}", "SCHEMA_FORMULA_DIRECT_FRONTIER", parent, lane_index, key,
                                    "NOT_EVALUABLE", None, absent=absent, convention=roles.convention)
            parent_value = values[parent][lane_index] if lane_index < len(values[parent]) else None
            raw_terms = []
            for term in terms:
                value = values[term][lane_index] if lane_index < len(values[term]) else None
                raw_terms.append((term, value))
                result.terms.append({"report_norm_id": term, "value": None if value is None else str(value)})
            if parent_value is None:
                result.reason = "PARENT_LANE_NOT_NUMERIC"
            elif any(value is None for _, value in raw_terms):
                result.reason = "COMPONENT_LANE_NOT_NUMERIC"
            else:
                for alternate in (False, True):
                    oriented_parent = roles.orient(parent, parent_value, alternate)
                    oriented = [roles.orient(term, value, alternate) for term, value in raw_terms]
                    if oriented_parent is None or any(value is None for value in oriented):
                        result.reason = f"SIGN_CONVENTION_{roles.convention}"
                        continue
                    total = sum(oriented, Decimal(0))
                    residual = oriented_parent - total
                    tolerance = Decimal(0)
                    if unit_scale >= config.rounding["minimum_unit_scale"]:
                        tolerance = Decimal(max(1, (len(oriented) + 1) // 2))
                    if residual == 0 or abs(residual) <= tolerance:
                        result.status = ("PASS_UNDER_ALTERNATE_SIGN_READING" if alternate else
                                         "PASS" if residual == 0 else "PASS_WITHIN_DECLARED_ROUNDING")
                        result.left, result.right, result.residual = str(oriented_parent), str(total), str(residual)
                        result.tolerance = str(tolerance)
                        result.reason = None
                        break
                    if not alternate:
                        result.left, result.right, result.residual = str(oriented_parent), str(total), str(residual)
                        result.tolerance = str(tolerance)
                        result.status = "FAIL" if not absent and not extra else "MISMATCH_WITH_INCOMPLETE_FRONTIER"
                        result.reason = ("SOURCE_ONLY_COMPONENTS:" + "|".join(extra)[:300]) if extra else (
                            "ABSENT_SCHEMA_COMPONENTS" if absent else "COMPLETE_FRONTIER_DOES_NOT_CLOSE")
                    if not (roles.reversible & ({parent} | set(terms))):
                        break
            results.append(result)
    for identity in spec.get("cross_identities", []):
        left, right = identity["left"], identity["right"]
        if left not in mapped or right not in mapped:
            continue
        for lane_index, lane in enumerate(instance.lanes):
            key = lane.period.get("key") if lane.period else None
            a, b = values[left][lane_index], values[right][lane_index]
            result = EquationResult(f"{statement}:{identity['name']}", "CROSS_IDENTITY", None, lane_index, key,
                                    "NOT_EVALUABLE", None,
                                    terms=[{"report_norm_id": left, "value": None if a is None else str(a)},
                                           {"report_norm_id": right, "value": None if b is None else str(b)}])
            if a is not None and b is not None:
                result.left, result.right, result.residual = str(a), str(b), str(a - b)
                result.status = "PASS" if a == b else "FAIL"
            else:
                result.reason = "LANE_NOT_NUMERIC"
            results.append(result)
    return results
