"""Lane-aware arithmetic that never treats an unobserved cell as numeric zero."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1

__all__ = [
    "SourceObservationLaneMathError",
    "additive_source_lane_receipts_v1",
    "observed_source_coefficient_v1",
    "partial_source_mapping_values_v1",
]


class SourceObservationLaneMathError(ValueError):
    """Raised when a source-cell vector is malformed or arithmetic is ambiguous."""


_NULL_STATES = {
    "ABSENT_SOURCE_AXIS_ROLE",
    "BLANK_SOURCE_CELL",
    "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
    "UNOBSERVED_SOURCE_LANE",
}


def _is_blank_state(state: Any) -> bool:
    return type(state) is str and (
        state in _NULL_STATES or "BLANK_ZERO" in state or ("BLANK" in state and "INFERRED" in state)
    )


def observed_source_coefficient_v1(cell: Mapping[str, Any]) -> int | None:
    """Return an observed/derived coefficient, or ``None`` for a source blank.

    Legacy ``BLANK_ZERO`` states are interpreted as missing observations during
    migration; their stored numeric zero is never allowed into arithmetic.
    """

    if not isinstance(cell, Mapping):
        raise SourceObservationLaneMathError("source cell is not one mapping")
    state = cell.get("state")
    coefficient = cell.get("coefficient")
    source_text = cell.get("source_text")
    if _is_blank_state(state):
        if source_text is not None:
            raise SourceObservationLaneMathError("blank source cell carries source text")
        if coefficient not in {None, 0}:
            raise SourceObservationLaneMathError("blank source cell carries a nonzero value")
        return None
    if type(state) is not str or not state:
        raise SourceObservationLaneMathError("source cell state is not typed")
    if type(coefficient) is not int:
        raise SourceObservationLaneMathError("observed source coefficient is not an integer")
    return coefficient


def additive_source_lane_receipts_v1(
    *,
    result_cells: Sequence[Mapping[str, Any]],
    component_cell_vectors: Sequence[Sequence[Mapping[str, Any]]],
    maximum_absolute_residual: int = 0,
) -> list[dict[str, Any]]:
    """Evaluate an additive equation independently on each observed lane.

    A lane with any unobserved operand is typed as unobserved and cannot prove,
    round, infer, or veto an equation.  Other lanes remain independently usable.
    """

    if (
        type(result_cells) not in {list, tuple}
        or not result_cells
        or type(component_cell_vectors) not in {list, tuple}
        or not component_cell_vectors
        or type(maximum_absolute_residual) is not int
        or maximum_absolute_residual < 0
        or any(
            type(vector) not in {list, tuple} or len(vector) != len(result_cells)
            for vector in component_cell_vectors
        )
    ):
        raise SourceObservationLaneMathError("additive source lane axis is invalid")
    receipts = []
    for lane, result_cell in enumerate(result_cells):
        result = observed_source_coefficient_v1(result_cell)
        components = [
            observed_source_coefficient_v1(vector[lane]) for vector in component_cell_vectors
        ]
        if result is None:
            receipts.append(
                {
                    "component_coefficients": components,
                    "component_sum": None,
                    "lane": lane,
                    "residual": None,
                    "result_coefficient": None,
                    "status": "RESULT_SOURCE_LANE_UNOBSERVED",
                }
            )
            continue
        if any(component is None for component in components):
            receipts.append(
                {
                    "component_coefficients": components,
                    "component_sum": None,
                    "lane": lane,
                    "residual": None,
                    "result_coefficient": result,
                    "status": "COMPONENT_SOURCE_LANE_UNOBSERVED",
                }
            )
            continue
        component_sum = sum(component for component in components if component is not None)
        residual = result - component_sum
        receipts.append(
            {
                "component_coefficients": components,
                "component_sum": component_sum,
                "lane": lane,
                "residual": residual,
                "result_coefficient": result,
                "status": (
                    "EXACT_OBSERVED_SOURCE_LANE"
                    if residual == 0
                    else "BOUNDED_DISPLAY_ROUNDING_SOURCE_LANE"
                    if abs(residual) <= maximum_absolute_residual
                    else "SOURCE_LANE_EQUATION_CONFLICT"
                ),
            }
        )
    return receipts


def partial_source_mapping_values_v1(
    cells: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]] | None:
    """Preserve observed lanes and type missing lanes; omit an all-blank role."""

    if type(cells) not in {list, tuple} or not cells:
        raise SourceObservationLaneMathError("source mapping cell axis is invalid")
    output: list[dict[str, Any]] = []
    observed = 0
    for cell in cells:
        coefficient = observed_source_coefficient_v1(cell)
        if coefficient is None:
            output.append(
                {
                    "coefficient": None,
                    "source_text": None,
                    "state": "BLANK_SOURCE_CELL",
                }
            )
        else:
            output.append(canonical_clone_v1(dict(cell)))
            observed += 1
    return output if observed else None
