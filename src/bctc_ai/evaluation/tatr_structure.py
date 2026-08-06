from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any


class TatrStructureError(RuntimeError):
    pass


def resolve_checkpoint_compatibility(
    payload: Mapping[str, Any],
    compatibility: Mapping[str, Any],
    *,
    transformers_version: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve one pinned legacy-null field in memory without changing the artifact."""

    if compatibility.get("mode") != "EXPLICIT_IN_MEMORY_CHECKPOINT_CONFIG_RESOLUTION":
        raise TatrStructureError("unsupported TATR checkpoint compatibility mode")
    expected_version = str(compatibility.get("runtime_transformers", ""))
    if transformers_version != expected_version:
        raise TatrStructureError(
            f"TATR compatibility is not approved for Transformers {transformers_version}; "
            f"expected {expected_version}"
        )
    field = str(compatibility.get("field", ""))
    if field != "dilation":
        raise TatrStructureError(f"unsupported TATR compatibility field: {field!r}")
    if compatibility.get("checkpoint_value_kind") != "NULL" or payload.get(field) is not None:
        raise TatrStructureError("TATR checkpoint dilation is not the pinned legacy null")
    resolved_value = compatibility.get("resolved_value")
    if resolved_value is not False:
        raise TatrStructureError("TATR compatibility may resolve dilation only to false")
    if compatibility.get("checkpoint_artifact_mutated") is not False:
        raise TatrStructureError("TATR compatibility must not mutate the checkpoint artifact")
    resolved = deepcopy(dict(payload))
    resolved[field] = False
    return resolved, {
        "mode": compatibility["mode"],
        "field": field,
        "checkpoint_value": None,
        "resolved_value": False,
        "runtime_transformers": transformers_version,
        "checkpoint_artifact_mutated": False,
        "reason": str(compatibility.get("reason", "")),
    }


def resolve_processor_size_compatibility(
    size: Mapping[str, Any],
    compatibility: Mapping[str, Any],
    *,
    transformers_version: str,
) -> tuple[dict[str, int], dict[str, Any]]:
    """Resolve the legacy longest-edge-only processor size without image distortion."""

    if compatibility.get("mode") != "EXPLICIT_IN_MEMORY_PROCESSOR_SIZE_RESOLUTION":
        raise TatrStructureError("unsupported TATR processor compatibility mode")
    expected_version = str(compatibility.get("runtime_transformers", ""))
    if transformers_version != expected_version:
        raise TatrStructureError(
            f"TATR processor compatibility is not approved for Transformers "
            f"{transformers_version}; expected {expected_version}"
        )
    expected_keys = [str(value) for value in compatibility.get("checkpoint_keys", [])]
    if expected_keys != ["longest_edge"] or set(size) != {"longest_edge"}:
        raise TatrStructureError(
            f"TATR checkpoint processor keys drifted: {sorted(size)} != ['longest_edge']"
        )
    checkpoint_longest = int(compatibility.get("checkpoint_longest_edge", -1))
    if size.get("longest_edge") != checkpoint_longest:
        raise TatrStructureError(
            f"TATR checkpoint longest edge drifted: {size.get('longest_edge')} "
            f"!= {checkpoint_longest}"
        )
    shortest = int(compatibility.get("resolved_shortest_edge", -1))
    longest = int(compatibility.get("resolved_longest_edge", -1))
    if shortest != checkpoint_longest or longest != checkpoint_longest:
        raise TatrStructureError("TATR processor resolution must retain maximum edge 800")
    if compatibility.get("checkpoint_artifact_mutated") is not False:
        raise TatrStructureError("TATR processor compatibility must not mutate the artifact")
    resolved = {"shortest_edge": shortest, "longest_edge": longest}
    return resolved, {
        "mode": compatibility["mode"],
        "checkpoint_size": dict(size),
        "resolved_size": resolved,
        "runtime_transformers": transformers_version,
        "aspect_ratio_preserved": True,
        "checkpoint_artifact_mutated": False,
        "reason": str(compatibility.get("reason", "")),
    }


def _finite_float(value: object, *, field: str) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise TatrStructureError(f"{field} is not numeric: {value!r}") from error
    if not math.isfinite(number):
        raise TatrStructureError(f"{field} is not finite: {value!r}")
    return number


def cxcywh_to_clipped_xyxy(
    box: Sequence[object], *, image_width: int, image_height: int
) -> tuple[list[float], list[float], str]:
    """Convert a normalized TATR box to normalized and source-pixel xyxy boxes."""

    if image_width < 1 or image_height < 1:
        raise TatrStructureError("image dimensions must be positive")
    if len(box) != 4:
        raise TatrStructureError(f"expected four cxcywh coordinates, received {len(box)}")
    cx, cy, width, height = (
        _finite_float(value, field=f"box[{index}]") for index, value in enumerate(box)
    )
    x0 = max(0.0, min(1.0, cx - width / 2.0))
    y0 = max(0.0, min(1.0, cy - height / 2.0))
    x1 = max(0.0, min(1.0, cx + width / 2.0))
    y1 = max(0.0, min(1.0, cy + height / 2.0))
    normalized = [x0, y0, x1, y1]
    pixels = [x0 * image_width, y0 * image_height, x1 * image_width, y1 * image_height]
    status = "VALID" if x1 > x0 and y1 > y0 else "DEGENERATE"
    return normalized, pixels, status


def build_query_predictions(
    *,
    boxes: Sequence[Sequence[object]],
    probabilities: Sequence[Sequence[object]],
    id2label: Mapping[int, str],
    image_width: int,
    image_height: int,
) -> list[dict[str, Any]]:
    """Retain every model query so thresholds can be changed without rerunning inference."""

    if len(boxes) != len(probabilities):
        raise TatrStructureError(
            f"box/probability query axes disagree: {len(boxes)} != {len(probabilities)}"
        )
    if not id2label:
        raise TatrStructureError("TATR label map is empty")
    class_count = max(id2label) + 1
    predictions: list[dict[str, Any]] = []
    for query_index, (box, raw_scores) in enumerate(zip(boxes, probabilities, strict=True)):
        if len(raw_scores) != class_count + 1:
            raise TatrStructureError(
                f"query {query_index} has {len(raw_scores)} probabilities; "
                f"expected {class_count + 1} including no-object"
            )
        scores = [
            _finite_float(value, field=f"probabilities[{query_index}][{index}]")
            for index, value in enumerate(raw_scores)
        ]
        object_index = max(range(class_count), key=scores.__getitem__)
        normalized, pixels, box_status = cxcywh_to_clipped_xyxy(
            box,
            image_width=image_width,
            image_height=image_height,
        )
        predictions.append(
            {
                "query_index": query_index,
                "predicted_class_id": object_index,
                "predicted_label": id2label[object_index],
                "object_score": scores[object_index],
                "no_object_score": scores[-1],
                "scores_by_label": {id2label[index]: scores[index] for index in range(class_count)},
                "bbox_normalized_xyxy": normalized,
                "bbox_source_pixels_xyxy": pixels,
                "bbox_status": box_status,
            }
        )
    return predictions


def summarize_thresholds(
    predictions: Sequence[Mapping[str, Any]], thresholds: Sequence[object]
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for raw_threshold in thresholds:
        threshold = _finite_float(raw_threshold, field="threshold")
        if threshold < 0.0 or threshold > 1.0:
            raise TatrStructureError(f"threshold is outside [0, 1]: {threshold}")
        retained = [
            prediction
            for prediction in predictions
            if prediction.get("bbox_status") == "VALID"
            and _finite_float(prediction.get("object_score"), field="object_score") >= threshold
            and _finite_float(prediction.get("object_score"), field="object_score")
            > _finite_float(prediction.get("no_object_score"), field="no_object_score")
        ]
        by_label: dict[str, int] = {}
        for prediction in retained:
            label = str(prediction["predicted_label"])
            by_label[label] = by_label.get(label, 0) + 1
        result[f"{threshold:.6f}"] = {
            "retained_query_count": len(retained),
            "counts_by_label": dict(sorted(by_label.items())),
            "retained_query_indices": [int(item["query_index"]) for item in retained],
        }
    return result
