from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
from typing import Any

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.evaluation.financial_cells_v2 import (
    parse_financial_number_strict_grouping,
)


class NumericCellVerificationError(RuntimeError):
    pass


_PRIMARY_OBSERVATIONS = {"BLANK", "DASH", "VALUE", "ZERO"}
_PROPOSAL_STATUSES = {
    "EMPTY_PROPOSAL",
    "NUMERIC_CHARACTERS_ONLY_PROPOSAL",
    "REJECT_NON_NUMERIC_CHARACTERS",
}


def _decimal(value: object, *, name: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise NumericCellVerificationError(f"{name} must not be boolean")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise NumericCellVerificationError(f"{name} is not numeric") from exc


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _validate_inputs(
    registry: dict[str, Any], predictions: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    cells = registry.get("cells")
    if (
        registry.get("format_version") != 1
        or registry.get("policy") != "FIXED_GRID_NUMERIC_CELL_CROPS_V1"
        or registry.get("geometry_authority") != "E0029_PP_OCRV6_FIXED_GRID"
        or not isinstance(cells, list)
        or registry.get("metrics", {}).get("cell_count") != len(cells)
    ):
        raise NumericCellVerificationError("numeric crop registry identity drifted")
    if not isinstance(predictions, list) or len(predictions) != len(cells):
        raise NumericCellVerificationError("numeric reader changed the cell denominator")

    by_id: dict[str, dict[str, Any]] = {}
    for prediction in predictions:
        if not isinstance(prediction, dict):
            raise NumericCellVerificationError("numeric prediction must be an object")
        cell_id = prediction.get("cell_id")
        status = prediction.get("proposal_status")
        raw = prediction.get("raw_prediction")
        score = prediction.get("reader_score")
        if (
            not isinstance(cell_id, str)
            or cell_id in by_id
            or status not in _PROPOSAL_STATUSES
            or not isinstance(raw, str)
            or isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 0 <= float(score) <= 1
        ):
            raise NumericCellVerificationError("numeric prediction identity or type drifted")
        by_id[cell_id] = prediction

    cell_ids = [cell.get("cell_id") for cell in cells if isinstance(cell, dict)]
    if len(cell_ids) != len(cells) or len(set(cell_ids)) != len(cells):
        raise NumericCellVerificationError("numeric crop cell identities are invalid")
    if set(cell_ids) != set(by_id):
        raise NumericCellVerificationError("numeric reader changed cell identities")
    return cells, by_id


def _challenger_record(prediction: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    raw = prediction["raw_prediction"]
    parsed = parse_financial_number_strict_grouping(raw)
    record = {
        "raw_text": raw,
        "reader_score": float(prediction["reader_score"]),
        "proposal_status": prediction["proposal_status"],
        "parsed_observation": parsed.observation.value,
        "parsed_value": _decimal_text(parsed.value),
        "sign_evidence": parsed.sign_evidence,
        "parse_reason": parsed.reason,
    }
    return record, parsed


def verify_numeric_cell_proposals(
    registry: dict[str, Any], predictions: list[dict[str, Any]]
) -> dict[str, Any]:
    """Fuse two readers only on exact numeric/sign agreement.

    Reader probability never participates in a decision. A primary blank is
    retained as unresolved even if the challenger proposes a value; row
    semantics must later distinguish a heading, a visible empty cell and an
    obscured cell. A dash additionally requires the independent visual mark
    recorded by the fixed-grid parser.
    """

    cells, predictions_by_id = _validate_inputs(registry, predictions)
    records: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    proposal_counts: Counter[str] = Counter()
    for cell in cells:
        cell_id = str(cell["cell_id"])
        primary_observation = cell.get("primary_observation")
        if primary_observation not in _PRIMARY_OBSERVATIONS:
            raise NumericCellVerificationError(f"unsupported primary observation: {cell_id}")
        primary_value = _decimal(cell.get("primary_value"), name=f"{cell_id} primary value")
        if primary_observation in {"VALUE", "ZERO"} and primary_value is None:
            raise NumericCellVerificationError(f"observed numeric cell lacks value: {cell_id}")
        if primary_observation in {"BLANK", "DASH"} and primary_value is not None:
            raise NumericCellVerificationError(
                f"blank or dash primary cell unexpectedly has a value: {cell_id}"
            )

        prediction = predictions_by_id[cell_id]
        if (
            prediction.get("crop_sha256") != cell.get("crop_sha256")
            or prediction.get("crop_path", "").rsplit("/", maxsplit=1)[-1]
            != str(cell.get("crop_path", "")).rsplit("/", maxsplit=1)[-1]
        ):
            raise NumericCellVerificationError(f"numeric reader crop identity drifted: {cell_id}")
        challenger, parsed = _challenger_record(prediction)
        proposal_counts[prediction["proposal_status"]] += 1

        selected_raw: str | None = None
        selected_value: str | None = None
        final_value_status: str | None = None
        decision: str
        if primary_observation in {"VALUE", "ZERO"}:
            if (
                prediction["proposal_status"] == "NUMERIC_CHARACTERS_ONLY_PROPOSAL"
                and parsed.observation in {ObservationKind.VALUE, ObservationKind.ZERO}
                and parsed.value == primary_value
                and parsed.sign_evidence == cell.get("primary_sign_evidence")
            ):
                verification_status = "VERIFIED_OBSERVED_VALUE"
                decision = "ACCEPT_EXACT_VALUE_AND_SIGN_AGREEMENT"
                selected_raw = str(cell.get("primary_raw_text", ""))
                selected_value = _decimal_text(primary_value)
                final_value_status = "OBSERVED_VALUE"
            else:
                verification_status = "UNRESOLVED_READER_DISAGREEMENT"
                decision = "ABSTAIN_AND_RETAIN_BOTH_READER_PROPOSALS"
        elif primary_observation == "DASH":
            visual = cell.get("visual_punctuation_evidence")
            if (
                prediction["proposal_status"] == "NUMERIC_CHARACTERS_ONLY_PROPOSAL"
                and parsed.observation is ObservationKind.DASH
                and isinstance(visual, dict)
                and visual.get("observation") == "DASH"
            ):
                verification_status = "VERIFIED_OBSERVED_DASH"
                decision = "ACCEPT_DASH_WITH_READER_AND_PIXEL_AGREEMENT"
                selected_raw = str(cell.get("primary_raw_text", ""))
                selected_value = "0"
                final_value_status = "OBSERVED_ZERO"
            else:
                verification_status = "UNRESOLVED_READER_DISAGREEMENT"
                decision = "ABSTAIN_AND_RETAIN_BOTH_READER_PROPOSALS"
        else:
            verification_status = "UNRESOLVED_BLANK_PENDING_ROW_SEMANTICS"
            decision = "RETAIN_BLANK_WITHOUT_ZERO_OR_VALUE_PROMOTION"

        status_counts[verification_status] += 1
        records.append(
            {
                "cell_id": cell_id,
                "page": cell.get("page"),
                "row_ordinal": cell.get("row_ordinal"),
                "axis_ordinal": cell.get("axis_ordinal"),
                "axis_id": cell.get("axis_id"),
                "crop_sha256": cell.get("crop_sha256"),
                "primary": {
                    "raw_text": cell.get("primary_raw_text"),
                    "normalized_text": cell.get("primary_normalized_text"),
                    "observation": primary_observation,
                    "value": _decimal_text(primary_value),
                    "sign_evidence": cell.get("primary_sign_evidence"),
                    "visual_punctuation_evidence": cell.get(
                        "visual_punctuation_evidence"
                    ),
                },
                "challenger": challenger,
                "verification_status": verification_status,
                "decision": decision,
                "selected_raw_value": selected_raw,
                "normalized_numeric_value": selected_value,
                "final_value_status": final_value_status,
            }
        )

    observed_count = sum(
        status_counts[name]
        for name in ("VERIFIED_OBSERVED_VALUE", "VERIFIED_OBSERVED_DASH")
    ) + status_counts["UNRESOLVED_READER_DISAGREEMENT"]
    verified_count = (
        status_counts["VERIFIED_OBSERVED_VALUE"]
        + status_counts["VERIFIED_OBSERVED_DASH"]
    )
    metrics = {
        "cell_count": len(records),
        "primary_observation_counts": dict(
            sorted(Counter(cell["primary_observation"] for cell in cells).items())
        ),
        "reader_proposal_status_counts": dict(sorted(proposal_counts.items())),
        "verification_status_counts": dict(sorted(status_counts.items())),
        "observed_cell_count": observed_count,
        "verified_observed_cell_count": verified_count,
        "observed_exact_agreement_rate": (
            round(verified_count / observed_count, 6) if observed_count else 0.0
        ),
        "unresolved_observed_cell_count": status_counts[
            "UNRESOLVED_READER_DISAGREEMENT"
        ],
        "blank_cell_count": status_counts["UNRESOLVED_BLANK_PENDING_ROW_SEMANTICS"],
        "blank_to_zero_or_value_promotion_count": 0,
        "automatic_reader_overwrite_count": 0,
        "reader_score_decision_use_count": 0,
    }
    return {
        "format_version": 1,
        "policy": "EXACT_VALUE_SIGN_AND_PIXEL_DASH_AGREEMENT_V1",
        "authority": "BOUNDED_NUMERIC_VERIFICATION_ONLY",
        "metrics": metrics,
        "cells": records,
    }
