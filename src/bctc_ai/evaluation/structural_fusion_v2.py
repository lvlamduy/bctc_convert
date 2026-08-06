from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.evaluation.reader_outputs import reader_row_to_dict
from bctc_ai.mapping.scope import ScopePolicy, classify_mapping_scopes
from bctc_ai.validation.reader_agreement import ReaderRow, align_ordered_reader_rows


@dataclass(frozen=True)
class StructuredReaderRow:
    row: ReaderRow
    row_code: str | None = None


def _structured_row_record(item: StructuredReaderRow) -> dict[str, Any]:
    return {"row_code": item.row_code, "row": reader_row_to_dict(item.row)}


def preserve_continuation_boundary_v2(
    *,
    statement_type: str,
    from_page: int,
    to_page: int,
    role_b_from: tuple[StructuredReaderRow, ...],
    role_b_to: tuple[StructuredReaderRow, ...],
    role_c_from: tuple[StructuredReaderRow, ...],
    role_c_to: tuple[StructuredReaderRow, ...],
    context_rows: int = 2,
) -> dict[str, Any]:
    if statement_type not in {"CDKT", "KQKD", "LCTT"}:
        raise ValueError("invalid continuation statement type")
    if from_page < 1 or to_page != from_page + 1:
        raise ValueError("continuation pages must be positive and adjacent")
    if context_rows < 1:
        raise ValueError("context_rows must be positive")
    return {
        "statement_type": statement_type,
        "from_page": from_page,
        "to_page": to_page,
        "accepted": True,
        "table_continuation_only": True,
        "automatic_cross_page_row_merge": False,
        "boundary_evidence": {
            "role_b_previous_tail": [
                _structured_row_record(item) for item in role_b_from[-context_rows:]
            ],
            "role_b_next_head": [_structured_row_record(item) for item in role_b_to[:context_rows]],
            "role_c_previous_tail": [
                _structured_row_record(item) for item in role_c_from[-context_rows:]
            ],
            "role_c_next_head": [_structured_row_record(item) for item in role_c_to[:context_rows]],
        },
        "status": "BOUNDARY_PRESERVED_PENDING_EXPLICIT_ROW_CONTINUATION_EVIDENCE",
    }


def _financial(row: ReaderRow) -> bool:
    return any(cell.observation is not ObservationKind.BLANK for cell in row.cells)


def _scope_by_index(
    rows: tuple[StructuredReaderRow, ...],
    *,
    statement_type: str,
    scope_policy: ScopePolicy,
    context_text: str,
) -> tuple[bool, ...]:
    decisions = classify_mapping_scopes(
        [(statement_type, item.row.label) for item in rows],
        scope_policy,
        initial_section_label=context_text,
    )
    return tuple(decision.allowed for decision in decisions)


def _cell_record(role_b_cell, role_c_cell) -> dict[str, Any]:
    exact = (
        role_b_cell.observation is role_c_cell.observation
        and role_b_cell.value == role_c_cell.value
    )
    return {
        "role_b_raw": role_b_cell.raw_text,
        "role_c_raw": role_c_cell.raw_text,
        "role_b_observation": role_b_cell.observation.value,
        "role_c_observation": role_c_cell.observation.value,
        "role_b_value": str(role_b_cell.value) if role_b_cell.value is not None else None,
        "role_c_value": str(role_c_cell.value) if role_c_cell.value is not None else None,
        "role_b_reason": role_b_cell.reason,
        "role_c_reason": role_c_cell.reason,
        "exact": exact,
        "confidence_effect": "NONE",
    }


def _escalation(action: str, cells: list[dict[str, Any]], width_exact: bool) -> str:
    if action == "MISSING_CANDIDATE":
        return "ROLE_C_MISSING_ROW_RECONSTRUCTION_OR_REREAD"
    if action == "EXTRA_CANDIDATE":
        return "ROLE_B_MISSING_OR_TRUNCATED_ROW_REREAD"
    if action in {"MERGE_REFERENCE", "MERGE_CANDIDATE"}:
        return "ROW_COLLAPSE_OR_WRAP_STRUCTURAL_REVIEW"
    if not width_exact:
        return "CELL_AXIS_WIDTH_REVIEW"
    if any(
        cell[reader] == ObservationKind.INVALID.value
        for cell in cells
        for reader in ("role_b_observation", "role_c_observation")
    ):
        return "TARGETED_INVALID_CELL_REREAD"
    if any(not cell["exact"] for cell in cells):
        return "TARGETED_NUMERIC_DISAGREEMENT_REREAD"
    return "CROSS_READER_AGREEMENT_NO_CONFIDENCE_PROMOTION"


def compare_structural_readers_v2(
    role_b_rows: tuple[StructuredReaderRow, ...],
    role_c_rows: tuple[StructuredReaderRow, ...],
    *,
    statement_type: str,
    page_mapping_eligible: bool,
    upstream_scope_reason: str,
    scope_policy: ScopePolicy,
    role_b_context_text: str = "",
    role_c_context_text: str = "",
) -> dict[str, Any]:
    """Compare readers using labels/order only, then inspect cells and scope.

    Role B is the label/context proposal and Role C is the geometry/value
    proposal. Neither is truth and agreement has no automatic confidence effect.
    """

    alignment = align_ordered_reader_rows(
        tuple(item.row for item in role_b_rows),
        tuple(item.row for item in role_c_rows),
    )
    role_b_scope = _scope_by_index(
        role_b_rows,
        statement_type=statement_type,
        scope_policy=scope_policy,
        context_text=role_b_context_text,
    )
    role_c_scope = _scope_by_index(
        role_c_rows,
        statement_type=statement_type,
        scope_policy=scope_policy,
        context_text=role_c_context_text,
    )
    records = []
    covered_b: set[int] = set()
    covered_c: set[int] = set()
    for step in alignment:
        if step.reference_indices and step.candidate_indices:
            covered_b.update(step.reference_indices)
            covered_c.update(step.candidate_indices)
        b_codes = [role_b_rows[index].row_code for index in step.reference_indices]
        c_codes = [role_c_rows[index].row_code for index in step.candidate_indices]
        local_scope_allowed = all(role_b_scope[index] for index in step.reference_indices) and all(
            role_c_scope[index] for index in step.candidate_indices
        )
        mapping_eligible = page_mapping_eligible and local_scope_allowed
        cells: list[dict[str, Any]] = []
        width_exact = True
        note_exact = None
        if step.reference is not None and step.candidate is not None:
            width_exact = len(step.reference.cells) == len(step.candidate.cells)
            cells = [
                _cell_record(role_b_cell, role_c_cell)
                for role_b_cell, role_c_cell in zip(
                    step.reference.cells,
                    step.candidate.cells,
                    strict=False,
                )
            ]
            note_exact = step.reference.note_reference == step.candidate.note_reference
        record = {
            "action": step.action,
            "role_b_indices": list(step.reference_indices),
            "role_c_indices": list(step.candidate_indices),
            "role_b": reader_row_to_dict(step.reference) if step.reference is not None else None,
            "role_c": reader_row_to_dict(step.candidate) if step.candidate is not None else None,
            "role_b_row_codes": b_codes,
            "role_c_row_codes": c_codes,
            "semantic_similarity": step.semantic_similarity,
            "label_exact": step.label_exact,
            "semantic_key_exact": step.semantic_key_exact,
            "note_exact": note_exact,
            "cell_width_exact": width_exact,
            "cells": cells,
            "scope": {
                "upstream_page_mapping_eligible": page_mapping_eligible,
                "upstream_reason": upstream_scope_reason,
                "local_reader_scope_allowed": local_scope_allowed,
                "mapping_eligible": mapping_eligible,
            },
            "escalation": _escalation(step.action, cells, width_exact),
            "automatic_acceptance": False,
            "confidence_effect": "NONE",
        }
        records.append(record)

    paired = [record for record in records if record["role_b"] and record["role_c"]]
    paired_cells = [cell for record in paired for cell in record["cells"]]
    observed_paired_cells = [
        cell
        for cell in paired_cells
        if cell["role_b_observation"] != ObservationKind.BLANK.value
        or cell["role_c_observation"] != ObservationKind.BLANK.value
    ]
    financial_paired_units = [
        record
        for record in paired
        if any(
            cell["role_b_observation"] != ObservationKind.BLANK.value
            or cell["role_c_observation"] != ObservationKind.BLANK.value
            for cell in record["cells"]
        )
    ]
    note_units = [
        record
        for record in paired
        if record["role_b"]["note_reference"] is not None
        or record["role_c"]["note_reference"] is not None
    ]
    row_code_units = [
        record
        for record in paired
        if any(code is not None for code in record["role_b_row_codes"])
        or any(code is not None for code in record["role_c_row_codes"])
    ]
    b_financial = {index for index, item in enumerate(role_b_rows) if _financial(item.row)}
    c_financial = {index for index, item in enumerate(role_c_rows) if _financial(item.row)}
    return {
        "policy": {
            "alignment_features": ["DOCUMENT_ORDER", "NORMALIZED_LABEL_TEXT"],
            "values_or_notes_affect_alignment": False,
            "role_b_is_truth": False,
            "role_c_is_truth": False,
            "agreement_promotes_confidence": False,
            "page_scope_applied_before_mapping": True,
        },
        "counts": {
            "role_b_rows": len(role_b_rows),
            "role_c_rows": len(role_c_rows),
            "alignment_actions": dict(
                sorted(Counter(record["action"] for record in records).items())
            ),
            "paired_alignment_units": len(paired),
            "paired_financial_alignment_units": len(financial_paired_units),
            "exact_paired_financial_alignment_units": sum(
                record["cell_width_exact"] and all(cell["exact"] for cell in record["cells"])
                for record in financial_paired_units
            ),
            "source_exact_labels": sum(record["label_exact"] is True for record in paired),
            "semantic_key_exact_labels": sum(
                record["semantic_key_exact"] is True for record in paired
            ),
            "role_b_financial_rows": len(b_financial),
            "role_c_financial_rows": len(c_financial),
            "covered_role_b_financial_rows": len(covered_b & b_financial),
            "covered_role_c_financial_rows": len(covered_c & c_financial),
            "paired_cells": len(paired_cells),
            "exact_paired_cells": sum(cell["exact"] for cell in paired_cells),
            "paired_observed_cells": len(observed_paired_cells),
            "exact_paired_observed_cells": sum(cell["exact"] for cell in observed_paired_cells),
            "note_comparison_units": len(note_units),
            "exact_note_units": sum(record["note_exact"] is True for record in note_units),
            "row_code_comparison_units": len(row_code_units),
            "exact_row_code_units": sum(
                record["role_b_row_codes"] == record["role_c_row_codes"]
                for record in row_code_units
            ),
            "exact_cell_width_units": sum(record["cell_width_exact"] for record in paired),
            "role_b_invalid_cells": sum(
                cell.observation is ObservationKind.INVALID
                for item in role_b_rows
                for cell in item.row.cells
            ),
            "role_c_invalid_cells": sum(
                cell.observation is ObservationKind.INVALID
                for item in role_c_rows
                for cell in item.row.cells
            ),
            "mapping_eligible_alignment_units": sum(
                record["scope"]["mapping_eligible"] for record in records
            ),
            "mapping_excluded_alignment_units": sum(
                not record["scope"]["mapping_eligible"] for record in records
            ),
            "escalations": dict(
                sorted(Counter(record["escalation"] for record in records).items())
            ),
        },
        "alignment": records,
    }
