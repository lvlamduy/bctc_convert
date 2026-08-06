from __future__ import annotations

import math
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from rapidfuzz.distance import Levenshtein

_WHITESPACE = re.compile(r"\s+")


def normalize_evaluation_line(value: str) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", value)).strip()


def _base_character(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    stripped = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return stripped.replace("đ", "d").replace("Đ", "D")


def _base_folded_text(value: str) -> str:
    return "".join(_base_character(char) for char in value).casefold()


@dataclass(frozen=True)
class EditMetrics:
    reference_characters: int
    prediction_characters: int
    edit_distance: int
    deletion_count: int
    insertion_count: int
    substitution_count: int
    base_character_error_count: int
    diacritic_only_error_count: int
    case_or_case_plus_diacritic_error_count: int


def character_edit_metrics(reference: str, prediction: str) -> EditMetrics:
    reference = normalize_evaluation_line(reference)
    prediction = normalize_evaluation_line(prediction)
    operations = Levenshtein.editops(reference, prediction)
    deletions = sum(operation.tag == "delete" for operation in operations)
    insertions = sum(operation.tag == "insert" for operation in operations)
    substitutions = sum(operation.tag == "replace" for operation in operations)
    base_errors = 0
    diacritic_errors = 0
    case_or_combined = 0
    for operation in operations:
        if operation.tag != "replace":
            continue
        source = reference[operation.src_pos]
        target = prediction[operation.dest_pos]
        source_base = _base_character(source)
        target_base = _base_character(target)
        if source_base == target_base:
            diacritic_errors += 1
        elif source_base.casefold() == target_base.casefold():
            case_or_combined += 1
        else:
            base_errors += 1
    return EditMetrics(
        reference_characters=len(reference),
        prediction_characters=len(prediction),
        edit_distance=len(operations),
        deletion_count=deletions,
        insertion_count=insertions,
        substitution_count=substitutions,
        base_character_error_count=base_errors,
        diacritic_only_error_count=diacritic_errors,
        case_or_case_plus_diacritic_error_count=case_or_combined,
    )


def _suffix_truncated(
    reference: str,
    prediction: str,
    *,
    minimum_missing_characters: int,
    minimum_missing_fraction: float,
) -> bool:
    reference_base = _base_folded_text(normalize_evaluation_line(reference))
    prediction_base = _base_folded_text(normalize_evaluation_line(prediction))
    if not prediction_base:
        return bool(reference_base)
    missing = len(reference_base) - len(prediction_base)
    return (
        reference_base.startswith(prediction_base)
        and missing >= minimum_missing_characters
        and missing >= math.ceil(len(reference_base) * minimum_missing_fraction)
    )


def score_line(
    reference: str,
    prediction: str,
    *,
    minimum_missing_characters: int = 2,
    minimum_missing_fraction: float = 0.10,
) -> dict[str, Any]:
    normalized_reference = normalize_evaluation_line(reference)
    normalized_prediction = normalize_evaluation_line(prediction)
    characters = character_edit_metrics(normalized_reference, normalized_prediction)
    reference_words = normalized_reference.split()
    prediction_words = normalized_prediction.split()
    word_distance = Levenshtein.distance(reference_words, prediction_words)
    empty = not normalized_prediction
    truncated = _suffix_truncated(
        normalized_reference,
        normalized_prediction,
        minimum_missing_characters=minimum_missing_characters,
        minimum_missing_fraction=minimum_missing_fraction,
    )
    return {
        "exact": normalized_reference == normalized_prediction,
        "casefold_exact": normalized_reference.casefold() == normalized_prediction.casefold(),
        "reference_characters": characters.reference_characters,
        "prediction_characters": characters.prediction_characters,
        "character_edit_distance": characters.edit_distance,
        "reference_words": len(reference_words),
        "prediction_words": len(prediction_words),
        "word_edit_distance": word_distance,
        "deletion_count": characters.deletion_count,
        "insertion_count": characters.insertion_count,
        "substitution_count": characters.substitution_count,
        "base_character_error_count": characters.base_character_error_count,
        "diacritic_only_error_count": characters.diacritic_only_error_count,
        "case_or_case_plus_diacritic_error_count": (
            characters.case_or_case_plus_diacritic_error_count
        ),
        "empty_prediction": empty,
        "suffix_truncated": truncated,
        "empty_or_suffix_truncated": empty or truncated,
    }


def _aggregate_records(records: list[dict[str, Any]], title_categories: set[str]) -> dict[str, Any]:
    count = len(records)
    reference_characters = sum(int(record["metrics"]["reference_characters"]) for record in records)
    reference_words = sum(int(record["metrics"]["reference_words"]) for record in records)
    exact = sum(bool(record["metrics"]["exact"]) for record in records)
    casefold_exact = sum(bool(record["metrics"]["casefold_exact"]) for record in records)
    edit_distance = sum(int(record["metrics"]["character_edit_distance"]) for record in records)
    word_distance = sum(int(record["metrics"]["word_edit_distance"]) for record in records)
    title_records = [record for record in records if record["category"] in title_categories]
    return {
        "line_count": count,
        "exact_line_count": exact,
        "exact_line_accuracy": exact / count if count else None,
        "casefold_exact_line_count": casefold_exact,
        "casefold_exact_line_accuracy": casefold_exact / count if count else None,
        "reference_character_count": reference_characters,
        "character_edit_distance": edit_distance,
        "character_error_rate": edit_distance / reference_characters
        if reference_characters
        else None,
        "reference_word_count": reference_words,
        "word_edit_distance": word_distance,
        "word_error_rate": word_distance / reference_words if reference_words else None,
        "deletion_count": sum(int(record["metrics"]["deletion_count"]) for record in records),
        "insertion_count": sum(int(record["metrics"]["insertion_count"]) for record in records),
        "substitution_count": sum(
            int(record["metrics"]["substitution_count"]) for record in records
        ),
        "base_character_error_count": sum(
            int(record["metrics"]["base_character_error_count"]) for record in records
        ),
        "diacritic_only_error_count": sum(
            int(record["metrics"]["diacritic_only_error_count"]) for record in records
        ),
        "case_or_case_plus_diacritic_error_count": sum(
            int(record["metrics"]["case_or_case_plus_diacritic_error_count"])
            for record in records
        ),
        "empty_prediction_count": sum(
            bool(record["metrics"]["empty_prediction"]) for record in records
        ),
        "suffix_truncated_count": sum(
            bool(record["metrics"]["suffix_truncated"]) for record in records
        ),
        "empty_or_suffix_truncated_count": sum(
            bool(record["metrics"]["empty_or_suffix_truncated"]) for record in records
        ),
        "title_line_count": len(title_records),
        "title_exact_line_count": sum(
            bool(record["metrics"]["exact"]) for record in title_records
        ),
    }


def score_reader(
    samples: list[dict[str, str]],
    *,
    title_categories: set[str],
    minimum_missing_characters: int = 2,
    minimum_missing_fraction: float = 0.10,
) -> dict[str, Any]:
    records = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        record = {
            "sample_id": sample["sample_id"],
            "document": sample["document"],
            "category": sample["category"],
            "reference": normalize_evaluation_line(sample["reference"]),
            "prediction": normalize_evaluation_line(sample["prediction"]),
            "metrics": score_line(
                sample["reference"],
                sample["prediction"],
                minimum_missing_characters=minimum_missing_characters,
                minimum_missing_fraction=minimum_missing_fraction,
            ),
        }
        records.append(record)
        grouped[record["category"]].append(record)
    return {
        "aggregate": _aggregate_records(records, title_categories),
        "by_category": {
            category: _aggregate_records(group, title_categories)
            for category, group in sorted(grouped.items())
        },
        "samples": records,
    }


def compare_reader_scores(
    baseline: dict[str, Any], challenger: dict[str, Any]
) -> dict[str, Any]:
    baseline_aggregate = baseline["aggregate"]
    challenger_aggregate = challenger["aggregate"]
    gates = {
        "strictly_lower_aggregate_cer": (
            challenger_aggregate["character_error_rate"]
            < baseline_aggregate["character_error_rate"]
        ),
        "title_exact_line_count_not_regressed": (
            challenger_aggregate["title_exact_line_count"]
            >= baseline_aggregate["title_exact_line_count"]
        ),
        "empty_or_suffix_truncated_count_not_increased": (
            challenger_aggregate["empty_or_suffix_truncated_count"]
            <= baseline_aggregate["empty_or_suffix_truncated_count"]
        ),
    }
    return {
        "gates": gates,
        "adopt_as_semantic_proposal_reader": all(gates.values()),
        "numeric_period_unit_sign_geometry_mapping_authority_granted": False,
        "character_error_rate_delta": (
            challenger_aggregate["character_error_rate"]
            - baseline_aggregate["character_error_rate"]
        ),
        "exact_line_count_delta": (
            challenger_aggregate["exact_line_count"] - baseline_aggregate["exact_line_count"]
        ),
        "title_exact_line_count_delta": (
            challenger_aggregate["title_exact_line_count"]
            - baseline_aggregate["title_exact_line_count"]
        ),
    }
