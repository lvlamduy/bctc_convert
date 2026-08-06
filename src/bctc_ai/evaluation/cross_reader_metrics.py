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


def classify_cross_reader_error_classes(metrics: Mapping[str, Any]) -> dict[str, Any]:
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
    compared_numeric_disagreements = max(
        0,
        int(metrics["compared_reference_financial_cells"])
        - int(metrics["exact_reference_financial_cells"]),
    )
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
            "impact_count": structural_alignment_units + missing_reference_cells,
            "structural_alignment_units": structural_alignment_units,
            "missing_reference_cells": missing_reference_cells,
        },
        "NUMERIC_SIGN_OCR": {
            "impact_count": compared_numeric_disagreements,
            "compared_cell_disagreements": compared_numeric_disagreements,
            "invalid_candidate_cells": int(metrics["candidate_invalid_cells"]),
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
        "selection_rule": (
            "largest directly measured impact count; deterministic priority resolves ties"
        ),
    }
