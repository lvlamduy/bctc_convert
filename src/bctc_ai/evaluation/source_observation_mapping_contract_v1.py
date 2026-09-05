"""Cross-family source-observation contract for schema mappings.

Accounting equations may corroborate a visible value or derive a genuinely
unprinted aggregate from visible components.  They may not turn a blank source
cell into a numeric zero.  This module is deliberately family-agnostic so every
family artifact can be checked by the same acceptance gate.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

__all__ = [
    "SourceObservationMappingContractError",
    "audit_source_observation_mapping_contract_v1",
    "validate_source_observation_mapping_contract_v1",
]


class SourceObservationMappingContractError(ValueError):
    """Raised when a schema mapping invents a value from missing source data."""


_TYPED_UNOBSERVED_STATES = {
    "ABSENT_SOURCE_AXIS_ROLE",
    "BLANK_SOURCE_CELL",
    "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
    "UNOBSERVED_SOURCE_LANE",
}


def _mapping_role(value: Mapping) -> str | None:
    if type(value.get("role")) is str and value["role"]:
        return value["role"]
    if type(value.get("lane_role")) is str and type(value.get("movement_role")) is str:
        return value["lane_role"] + "/" + value["movement_role"]
    return None


def _mapping_cells(value: Mapping) -> list[Mapping] | None:
    if type(value.get("values")) is list and all(
        isinstance(cell, Mapping) for cell in value["values"]
    ):
        return value["values"]
    if isinstance(value.get("cell"), Mapping):
        return [value["cell"]]
    return None


def _is_mapping(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and type(value.get("report_norm_id")) is int
        and _mapping_role(value) is not None
        and _mapping_cells(value) is not None
    )


def _walk(value: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Mapping]]:
    mappings: list[tuple[tuple[str, ...], Mapping]] = []
    if _is_mapping(value):
        mappings.append((path, value))
    if isinstance(value, Mapping):
        for key, child in value.items():
            mappings.extend(_walk(child, (*path, str(key))))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            mappings.extend(_walk(child, (*path, str(index))))
    return mappings


def _violation(
    *,
    path: tuple[str, ...],
    mapping: Mapping,
    lane: int | None,
    reason: str,
) -> dict[str, Any]:
    return {
        "lane": lane,
        "path": "/" + "/".join(path),
        "reason": reason,
        "report_norm_id": mapping["report_norm_id"],
        "role": _mapping_role(mapping),
    }


def _has_bound_source_rows(mapping: Mapping) -> bool:
    refs = mapping.get("source_refs")
    return (
        type(refs) is list
        and bool(refs)
        and all(
            type(ref) is dict
            and type(ref.get("row_id")) is str
            and type(ref.get("locator")) is dict
            and type(ref["locator"].get("page_json_version_id")) is str
            and type(ref["locator"].get("table_id")) is str
            for ref in refs
        )
    )


def _has_bound_source_cell(mapping: Mapping, cell: Mapping) -> bool:
    refs = mapping.get("source_refs")
    return (
        type(refs) is list
        and bool(refs)
        and all(
            type(ref) is dict
            and type(ref.get("cell")) is dict
            and type(ref["cell"].get("coefficient")) is int
            and type(ref["cell"].get("source_text")) is str
            and (
                type(ref.get("locator")) is dict
                or type(ref["cell"].get("source_locator")) is dict
            )
            for ref in refs
        )
        and (
            len(refs) > 1
            or refs[0]["cell"]["coefficient"] == cell.get("coefficient")
        )
    )


def audit_source_observation_mapping_contract_v1(value: Any) -> dict[str, Any]:
    """Audit every direct ``mapping.values`` vector nested in ``value``.

    A partially observed role is valid: visible lanes remain numeric and blank
    lanes carry ``coefficient=null`` with a typed non-observation state.  A role
    whose every lane is unobserved must not be emitted.  A numeric value without
    source text is accepted only for an explicitly derived, non-blank value.
    """

    mappings = _walk(value)
    violations: list[dict[str, Any]] = []
    cell_count = 0
    derived_cell_count = 0
    source_blank_cell_count = 0
    partial_mapping_count = 0

    for path, mapping in mappings:
        observed_lanes = 0
        unobserved_lanes = 0
        mapping_cells = _mapping_cells(mapping)
        assert mapping_cells is not None
        for lane, cell in enumerate(mapping_cells):
            cell_count += 1
            coefficient = cell.get("coefficient")
            source_text = cell.get("source_text")
            state = cell.get("state")
            if type(state) is not str or not state:
                violations.append(
                    _violation(
                        path=path,
                        mapping=mapping,
                        lane=lane,
                        reason="MAPPING_CELL_STATE_IS_NOT_TYPED",
                    )
                )
                continue
            if "BLANK_ZERO" in state or ("BLANK" in state and "INFERRED" in state):
                violations.append(
                    _violation(
                        path=path,
                        mapping=mapping,
                        lane=lane,
                        reason="SOURCE_BLANK_WAS_CONVERTED_TO_NUMERIC_ZERO",
                    )
                )
                continue
            if coefficient is None:
                unobserved_lanes += 1
                source_blank_cell_count += 1
                if source_text is not None or state not in _TYPED_UNOBSERVED_STATES:
                    violations.append(
                        _violation(
                            path=path,
                            mapping=mapping,
                            lane=lane,
                            reason="NULL_MAPPING_CELL_LACKS_TYPED_SOURCE_NON_OBSERVATION",
                        )
                    )
                continue
            if type(coefficient) is not int:
                violations.append(
                    _violation(
                        path=path,
                        mapping=mapping,
                        lane=lane,
                        reason="MAPPING_COEFFICIENT_IS_NOT_INTEGER_OR_NULL",
                    )
                )
                continue
            observed_lanes += 1
            if source_text is None:
                if (
                    state.startswith(("AGGREGATED_", "DERIVED_", "EXACT_"))
                    and "BLANK" not in state
                ) or (
                    state.startswith("SOURCE_VISIBLE_") and _has_bound_source_rows(mapping)
                ) or _has_bound_source_cell(mapping, cell):
                    derived_cell_count += 1
                else:
                    violations.append(
                        _violation(
                            path=path,
                            mapping=mapping,
                            lane=lane,
                            reason="NUMERIC_MAPPING_HAS_NO_SOURCE_OR_EXACT_DERIVATION",
                        )
                    )
            elif type(source_text) is not str:
                violations.append(
                    _violation(
                        path=path,
                        mapping=mapping,
                        lane=lane,
                        reason="MAPPING_SOURCE_TEXT_IS_NOT_STRING_OR_NULL",
                    )
                )
        if observed_lanes and unobserved_lanes:
            partial_mapping_count += 1
        elif unobserved_lanes and not observed_lanes:
            violations.append(
                _violation(
                    path=path,
                    mapping=mapping,
                    lane=None,
                    reason="ALL_LANES_UNOBSERVED_ROLE_WAS_MAPPED",
                )
            )

    return {
        "cell_count": cell_count,
        "derived_cell_count": derived_cell_count,
        "format_version": "SOURCE_OBSERVATION_MAPPING_CONTRACT_AUDIT_V1",
        "mapping_count": len(mappings),
        "partial_mapping_count": partial_mapping_count,
        "source_blank_cell_count": source_blank_cell_count,
        "status": "PASS" if not violations else "FAILED",
        "violation_count": len(violations),
        "violations": violations,
    }


def validate_source_observation_mapping_contract_v1(value: Any) -> dict[str, Any]:
    """Return the audit or fail closed on any invented blank-derived value."""

    audit = audit_source_observation_mapping_contract_v1(value)
    if audit["violations"]:
        first = audit["violations"][0]
        raise SourceObservationMappingContractError(
            "source-observation mapping contract failed: "
            f"{first['reason']} at {first['path']} lane {first['lane']}"
        )
    return audit
