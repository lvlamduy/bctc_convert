from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

_SUM_FIELDS = (
    "reference_rows",
    "candidate_rows",
    "structurally_comparable_rows",
    "source_exact_labels",
    "semantic_key_exact_labels",
    "reference_financial_rows",
    "covered_reference_financial_rows",
    "exact_reference_financial_rows",
    "reference_financial_cells",
    "compared_reference_financial_cells",
    "exact_reference_financial_cells",
    "candidate_invalid_cells",
    "note_rows",
    "exact_note_references",
    "scope_allowed_candidate_rows",
    "scope_excluded_candidate_rows",
)


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def aggregate_cross_reader_metrics(
    comparisons: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate Role A/Role B comparisons without treating either label as truth.

    Each input is the result of ``compare_reader_rows``.  Coverage and strict
    agreement keep missing reference evidence in the denominator, while
    conditional agreement only measures aligned cells or rows.
    """

    materialized = tuple(comparisons)
    totals: dict[str, Any] = {
        field: sum(int(item["counts"][field]) for item in materialized)
        for field in _SUM_FIELDS
    }
    actions: Counter[str] = Counter()
    escalations: Counter[str] = Counter()
    for item in materialized:
        actions.update(item["counts"]["alignment_actions"])
        escalations.update(item["counts"]["escalations"])
    totals["alignment_actions"] = dict(sorted(actions.items()))
    totals["escalations"] = dict(sorted(escalations.items()))
    totals["source_exact_label_rate"] = _ratio(
        totals["source_exact_labels"], totals["structurally_comparable_rows"]
    )
    totals["semantic_key_exact_label_rate"] = _ratio(
        totals["semantic_key_exact_labels"], totals["structurally_comparable_rows"]
    )
    totals["reference_financial_row_coverage_rate"] = _ratio(
        totals["covered_reference_financial_rows"], totals["reference_financial_rows"]
    )
    totals["reference_financial_cell_coverage_rate"] = _ratio(
        totals["compared_reference_financial_cells"], totals["reference_financial_cells"]
    )
    totals["conditional_exact_cell_agreement_rate"] = _ratio(
        totals["exact_reference_financial_cells"],
        totals["compared_reference_financial_cells"],
    )
    totals["conditional_exact_financial_row_agreement_rate"] = _ratio(
        totals["exact_reference_financial_rows"],
        totals["covered_reference_financial_rows"],
    )
    totals["strict_exact_reference_cell_agreement_rate"] = _ratio(
        totals["exact_reference_financial_cells"], totals["reference_financial_cells"]
    )
    totals["strict_exact_reference_financial_row_agreement_rate"] = _ratio(
        totals["exact_reference_financial_rows"], totals["reference_financial_rows"]
    )
    return totals


def _cell_error_root_cause(cell: Mapping[str, Any], action: str) -> str | None:
    if cell.get("exact") is True:
        return None
    if action != "MATCH":
        return "STRUCTURAL_ROW_CELL_RECONSTRUCTION"
    if not cell.get("reference_present", True) or not cell.get("candidate_present", True):
        return "STRUCTURAL_ROW_CELL_RECONSTRUCTION"
    candidate_reason = str(cell.get("candidate_reason") or "")
    if candidate_reason == "multiple financial numbers in one cell":
        return "STRUCTURAL_ROW_CELL_RECONSTRUCTION"
    observations = {
        str(cell.get("reference_observation") or ""),
        str(cell.get("candidate_observation") or ""),
    }
    if "BLANK" in observations:
        return "STRUCTURAL_ROW_CELL_RECONSTRUCTION"
    return "NUMERIC_SIGN_OCR"


def classify_cross_reader_error_classes(
    metrics: Mapping[str, Any],
    comparisons: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Classify measurable errors by their direct downstream impact.

    This deliberately does not count the generic "no confidence promotion"
    escalation as an error.  Missing reference cells are structural failures;
    disagreements among already aligned cells are numeric/sign failures.
    """

    actions = metrics.get("alignment_actions", {})
    structural_alignment_units = sum(
        int(count) for action, count in actions.items() if action != "MATCH"
    )
    missing_reference_cells = max(
        0,
        int(metrics["reference_financial_cells"])
        - int(metrics["compared_reference_financial_cells"]),
    )
    measured_cell_disagreements = max(
        0,
        int(metrics["compared_reference_financial_cells"])
        - int(metrics["exact_reference_financial_cells"]),
    )
    structural_compared_cell_disagreements = 0
    numeric_disagreements = measured_cell_disagreements
    structural_multi_number_cells = 0
    numeric_invalid_cells = int(metrics["candidate_invalid_cells"])
    root_cause_mode = "AGGREGATE_FALLBACK"
    if comparisons is not None:
        root_cause_mode = "CELL_AND_ALIGNMENT_EVIDENCE"
        numeric_invalid_cells = 0
        causes: Counter[str] = Counter()
        for comparison in comparisons:
            for record in comparison["alignment"]:
                action = str(record["action"])
                cells = record.get("cells", [])
                if not any(
                    cell.get("reference_observation") != "BLANK" for cell in cells
                ):
                    continue
                for cell in cells:
                    cause = _cell_error_root_cause(cell, action)
                    if cause is not None and cell.get("reference_present", True):
                        causes[cause] += 1
                        if cell.get("candidate_observation") == "INVALID":
                            if cause == "STRUCTURAL_ROW_CELL_RECONSTRUCTION":
                                structural_multi_number_cells += 1
                            else:
                                numeric_invalid_cells += 1
        structural_compared_cell_disagreements = causes[
            "STRUCTURAL_ROW_CELL_RECONSTRUCTION"
        ]
        numeric_disagreements = causes["NUMERIC_SIGN_OCR"]
        if structural_compared_cell_disagreements + numeric_disagreements != (
            measured_cell_disagreements
        ):
            raise ValueError("cell-level error causes do not reconcile with aggregate metrics")
    semantic_label_disagreements = max(
        0,
        int(metrics["structurally_comparable_rows"])
        - int(metrics["semantic_key_exact_labels"]),
    )
    note_disagreements = max(
        0, int(metrics["note_rows"]) - int(metrics["exact_note_references"])
    )
    classes = {
        "STRUCTURAL_ROW_CELL_RECONSTRUCTION": {
            "impact_count": (
                structural_alignment_units
                + missing_reference_cells
                + structural_compared_cell_disagreements
            ),
            "structural_alignment_units": structural_alignment_units,
            "missing_reference_cells": missing_reference_cells,
            "structural_compared_cell_disagreements": (
                structural_compared_cell_disagreements
            ),
            "multi_number_candidate_cells": structural_multi_number_cells,
        },
        "NUMERIC_SIGN_OCR": {
            "impact_count": numeric_disagreements,
            "compared_cell_disagreements": numeric_disagreements,
            "invalid_candidate_cells_attributed_to_numeric": numeric_invalid_cells,
            "all_invalid_candidate_cells": int(metrics["candidate_invalid_cells"]),
        },
        "LABEL_SEMANTICS": {
            "impact_count": semantic_label_disagreements,
            "semantic_key_disagreements": semantic_label_disagreements,
        },
        "NOTE_REFERENCE": {
            "impact_count": note_disagreements,
            "note_disagreements": note_disagreements,
        },
    }
    priority = {
        "STRUCTURAL_ROW_CELL_RECONSTRUCTION": 0,
        "NUMERIC_SIGN_OCR": 1,
        "LABEL_SEMANTICS": 2,
        "NOTE_REFERENCE": 3,
    }
    main_error_class = min(
        classes,
        key=lambda name: (-int(classes[name]["impact_count"]), priority[name]),
    )
    return {
        "main_error_class": main_error_class,
        "classes": classes,
        "root_cause_mode": root_cause_mode,
        "selection_rule": (
            "largest directly measured impact count; deterministic priority resolves ties"
        ),
    }
