from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


class TargetedRereadError(RuntimeError):
    pass


@dataclass(frozen=True)
class RereadProfile:
    dpi: int
    readers: tuple[str, ...]
    variant_policy: str


@dataclass(frozen=True)
class TargetedRereadPolicy:
    dense_structural_trigger_fraction: float
    dense_structural_trigger_minimum: int
    group_gap_line_heights: float
    context_rows_before: int
    context_rows_after: int
    horizontal_margin_line_heights: float
    vertical_margin_line_heights: float
    maximum_trigger_units_per_band: int
    profiles: dict[str, RereadProfile]
    trigger_escalations: frozenset[str]
    non_trigger_escalations: frozenset[str]
    safety: dict[str, bool]


@dataclass(frozen=True)
class LocalizedTrigger:
    alignment_index: int
    escalation: str
    role_b_indices: tuple[int, ...]
    role_c_indices: tuple[int, ...]
    line_indices: tuple[int, ...]
    y0: float
    y1: float
    localization: str
    structural: bool


@dataclass(frozen=True)
class TargetedRereadRegion:
    region_id: str
    region_kind: str
    bbox_in_baseline_render: tuple[int, int, int, int]
    bbox_normalized: tuple[float, float, float, float]
    trigger_alignment_indices: tuple[int, ...]
    escalations: tuple[str, ...]
    role_b_indices: tuple[int, ...]
    role_c_indices: tuple[int, ...]
    source_line_indices: tuple[int, ...]
    localization_methods: tuple[str, ...]
    target_dpi: int
    readers: tuple[str, ...]
    variant_policy: str
    includes_period_header_pixels: bool
    period_binding_from_reread_allowed: bool
    automatic_value_replacement: bool = False
    automatic_confidence_promotion: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_PROFILE_NAMES = {
    "full_table_structural",
    "row_band_structural",
    "numeric_cell_strip",
}
_STRUCTURAL_ESCALATIONS = {
    "ROLE_B_MISSING_OR_TRUNCATED_ROW_REREAD",
    "ROLE_C_MISSING_ROW_RECONSTRUCTION_OR_REREAD",
    "ROW_COLLAPSE_OR_WRAP_STRUCTURAL_REVIEW",
    "CELL_AXIS_WIDTH_REVIEW",
    "TARGETED_INVALID_CELL_REREAD",
}
_REQUIRED_SAFETY = {
    "require_upstream_mapping_eligible": True,
    "preserve_original": True,
    "arithmetic_selects_variant": False,
    "history_selects_variant": False,
    "schema_selects_variant": False,
    "automatic_value_replacement": False,
    "automatic_confidence_promotion": False,
    "cross_page_region": False,
}


def _positive_number(payload: dict[str, Any], name: str) -> float:
    value = payload.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise TargetedRereadError(f"{name} must be positive")
    return float(value)


def _nonnegative_integer(payload: dict[str, Any], name: str) -> int:
    value = payload.get(name)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise TargetedRereadError(f"{name} must be a non-negative integer")
    return value


def load_targeted_reread_policy(path: Path) -> TargetedRereadPolicy:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise TargetedRereadError("targeted-reread policy must be version 1")
    localization = payload.get("localization")
    raw_profiles = payload.get("reread_profiles")
    if not isinstance(localization, dict) or not isinstance(raw_profiles, dict):
        raise TargetedRereadError("targeted-reread policy lacks localization or profiles")
    if set(raw_profiles) != _PROFILE_NAMES:
        raise TargetedRereadError("targeted-reread profile set is incomplete or unknown")
    profiles: dict[str, RereadProfile] = {}
    for name, raw in raw_profiles.items():
        if not isinstance(raw, dict):
            raise TargetedRereadError(f"profile {name} is not an object")
        dpi = raw.get("dpi")
        readers = raw.get("readers")
        variant_policy = raw.get("variant_policy")
        if not isinstance(dpi, int) or not 300 <= dpi <= 600:
            raise TargetedRereadError(f"profile {name} DPI must be in [300, 600]")
        if (
            not isinstance(readers, list)
            or not readers
            or any(not isinstance(reader, str) or not reader for reader in readers)
            or len(set(readers)) != len(readers)
        ):
            raise TargetedRereadError(f"profile {name} has invalid readers")
        if not isinstance(variant_policy, str) or not variant_policy:
            raise TargetedRereadError(f"profile {name} has no variant policy")
        profiles[name] = RereadProfile(dpi, tuple(readers), variant_policy)
    trigger_escalations = payload.get("trigger_escalations")
    non_trigger_escalations = payload.get("non_trigger_escalations")
    safety = payload.get("safety")
    if (
        not isinstance(trigger_escalations, list)
        or not trigger_escalations
        or any(not isinstance(value, str) or not value for value in trigger_escalations)
        or not isinstance(non_trigger_escalations, list)
        or not non_trigger_escalations
        or any(not isinstance(value, str) or not value for value in non_trigger_escalations)
    ):
        raise TargetedRereadError("invalid escalation policy")
    trigger_set = frozenset(trigger_escalations)
    non_trigger_set = frozenset(non_trigger_escalations)
    if trigger_set & non_trigger_set:
        raise TargetedRereadError("trigger and non-trigger escalation sets overlap")
    if not isinstance(safety, dict) or safety != _REQUIRED_SAFETY:
        raise TargetedRereadError("targeted-reread safety contract drifted")
    fraction = _positive_number(localization, "dense_structural_trigger_fraction")
    if fraction > 1:
        raise TargetedRereadError("dense structural fraction cannot exceed one")
    minimum = _nonnegative_integer(localization, "dense_structural_trigger_minimum")
    maximum_per_band = _nonnegative_integer(localization, "maximum_trigger_units_per_band")
    if minimum < 1 or maximum_per_band < 1:
        raise TargetedRereadError("trigger minimums must be at least one")
    return TargetedRereadPolicy(
        dense_structural_trigger_fraction=fraction,
        dense_structural_trigger_minimum=minimum,
        group_gap_line_heights=_positive_number(localization, "group_gap_line_heights"),
        context_rows_before=_nonnegative_integer(localization, "context_rows_before"),
        context_rows_after=_nonnegative_integer(localization, "context_rows_after"),
        horizontal_margin_line_heights=_positive_number(
            localization, "horizontal_margin_line_heights"
        ),
        vertical_margin_line_heights=_positive_number(localization, "vertical_margin_line_heights"),
        maximum_trigger_units_per_band=maximum_per_band,
        profiles=profiles,
        trigger_escalations=trigger_set,
        non_trigger_escalations=non_trigger_set,
        safety=dict(safety),
    )


def _validated_boxes(ocr_payload: dict[str, Any]) -> tuple[tuple[float, float, float, float], ...]:
    raw_boxes = ocr_payload.get("rec_boxes")
    if not isinstance(raw_boxes, list) or not raw_boxes:
        raise TargetedRereadError("baseline OCR has no line boxes")
    boxes = []
    for index, raw in enumerate(raw_boxes):
        if not isinstance(raw, list) or len(raw) != 4:
            raise TargetedRereadError(f"baseline OCR line {index} has no four-coordinate box")
        try:
            box = tuple(float(value) for value in raw)
        except (TypeError, ValueError) as exc:
            raise TargetedRereadError(f"baseline OCR line {index} box is nonnumeric") from exc
        if not all(math.isfinite(value) for value in box) or box[2] <= box[0] or box[3] <= box[1]:
            raise TargetedRereadError(f"baseline OCR line {index} box is degenerate")
        boxes.append(box)
    return tuple(boxes)


def _row_line_indices(row: dict[str, Any]) -> tuple[int, ...]:
    geometry = row.get("geometry")
    if not isinstance(geometry, dict):
        raise TargetedRereadError("Role C row has no geometry")
    raw_groups = [
        geometry.get("index_line_indices", []),
        geometry.get("label_line_indices", []),
        geometry.get("note_line_indices", []),
    ]
    value_groups = geometry.get("value_line_indices", [])
    if not isinstance(value_groups, list):
        raise TargetedRereadError("Role C row value-line geometry is invalid")
    raw_groups.extend(value_groups)
    indices: set[int] = set()
    for group in raw_groups:
        if not isinstance(group, list) or any(
            not isinstance(index, int) or isinstance(index, bool) or index < 0 for index in group
        ):
            raise TargetedRereadError("Role C row contains invalid line indices")
        indices.update(group)
    return tuple(sorted(indices))


def _row_anchor(row: dict[str, Any]) -> float:
    geometry = row.get("geometry")
    value = geometry.get("y_anchor") if isinstance(geometry, dict) else None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise TargetedRereadError("Role C row lacks a finite y anchor")
    return float(value)


def _line_span(
    indices: tuple[int, ...],
    boxes: tuple[tuple[float, float, float, float], ...],
    *,
    fallback_anchor: float,
    line_height: float,
) -> tuple[float, float]:
    try:
        selected = [boxes[index] for index in indices]
    except IndexError as exc:
        raise TargetedRereadError("Role C line index exceeds baseline OCR axes") from exc
    if selected:
        return min(box[1] for box in selected), max(box[3] for box in selected)
    return fallback_anchor - line_height / 2, fallback_anchor + line_height / 2


def _nearest_role_c_bracket(
    alignment: list[dict[str, Any]],
    alignment_index: int,
    role_c_rows: list[dict[str, Any]],
    line_height: float,
) -> tuple[float, float, str]:
    previous: list[int] = []
    following: list[int] = []
    for record in alignment[:alignment_index]:
        indices = record.get("role_c_indices", []) if isinstance(record, dict) else []
        if isinstance(indices, list):
            previous.extend(index for index in indices if isinstance(index, int))
    for record in alignment[alignment_index + 1 :]:
        indices = record.get("role_c_indices", []) if isinstance(record, dict) else []
        if isinstance(indices, list):
            following.extend(index for index in indices if isinstance(index, int))
    try:
        previous_anchor = _row_anchor(role_c_rows[max(previous)]) if previous else None
        following_anchor = _row_anchor(role_c_rows[min(following)]) if following else None
    except IndexError as exc:
        raise TargetedRereadError("alignment references a missing Role C row") from exc
    if previous_anchor is not None and following_anchor is not None:
        return previous_anchor, following_anchor, "ORDER_GAP_BRACKETED_BY_ROLE_C_ROWS"
    if previous_anchor is not None:
        return (
            previous_anchor - line_height / 2,
            previous_anchor + 2 * line_height,
            "ORDER_GAP_EXTRAPOLATED_AFTER_ROLE_C_ROW",
        )
    if following_anchor is not None:
        return (
            following_anchor - 2 * line_height,
            following_anchor + line_height / 2,
            "ORDER_GAP_EXTRAPOLATED_BEFORE_ROLE_C_ROW",
        )
    raise TargetedRereadError("cannot localize Role B-only gap without Role C neighbors")


def _localized_triggers(
    page_record: dict[str, Any],
    boxes: tuple[tuple[float, float, float, float], ...],
    policy: TargetedRereadPolicy,
) -> tuple[list[LocalizedTrigger], list[dict[str, Any]]]:
    role_c = page_record.get("role_c")
    comparison = page_record.get("comparison")
    if not isinstance(role_c, dict) or not isinstance(comparison, dict):
        raise TargetedRereadError("page lacks Role C or comparison evidence")
    role_c_rows = role_c.get("rows")
    alignment = comparison.get("alignment")
    line_height = role_c.get("line_height")
    if (
        not isinstance(role_c_rows, list)
        or not isinstance(alignment, list)
        or not isinstance(line_height, (int, float))
        or isinstance(line_height, bool)
        or line_height <= 0
    ):
        raise TargetedRereadError("invalid Role C rows, alignment, or line height")
    localized: list[LocalizedTrigger] = []
    unsupported: list[dict[str, Any]] = []
    for alignment_index, raw in enumerate(alignment):
        if not isinstance(raw, dict):
            raise TargetedRereadError("alignment record is not an object")
        escalation = raw.get("escalation")
        if not isinstance(escalation, str):
            raise TargetedRereadError("alignment record lacks escalation")
        if escalation in policy.non_trigger_escalations:
            continue
        if escalation not in policy.trigger_escalations:
            unsupported.append(
                {
                    "alignment_index": alignment_index,
                    "escalation": escalation,
                    "status": "UNRESOLVED_UNSUPPORTED_ESCALATION",
                }
            )
            continue
        raw_b = raw.get("role_b_indices", [])
        raw_c = raw.get("role_c_indices", [])
        if (
            not isinstance(raw_b, list)
            or not isinstance(raw_c, list)
            or any(not isinstance(index, int) or index < 0 for index in raw_b + raw_c)
        ):
            raise TargetedRereadError("alignment row indices are invalid")
        role_c_indices = tuple(raw_c)
        line_indices: set[int] = set()
        spans: list[tuple[float, float]] = []
        for row_index in role_c_indices:
            try:
                row = role_c_rows[row_index]
            except IndexError as exc:
                raise TargetedRereadError("alignment references a missing Role C row") from exc
            indices = _row_line_indices(row)
            line_indices.update(indices)
            spans.append(
                _line_span(
                    indices,
                    boxes,
                    fallback_anchor=_row_anchor(row),
                    line_height=float(line_height),
                )
            )
        if spans:
            y0 = min(span[0] for span in spans)
            y1 = max(span[1] for span in spans)
            localization = "ROLE_C_OBSERVED_LINE_GEOMETRY"
        else:
            y0, y1, localization = _nearest_role_c_bracket(
                alignment,
                alignment_index,
                role_c_rows,
                float(line_height),
            )
        localized.append(
            LocalizedTrigger(
                alignment_index=alignment_index,
                escalation=escalation,
                role_b_indices=tuple(raw_b),
                role_c_indices=role_c_indices,
                line_indices=tuple(sorted(line_indices)),
                y0=y0,
                y1=y1,
                localization=localization,
                structural=escalation in _STRUCTURAL_ESCALATIONS,
            )
        )
    return localized, unsupported


def _clamped_bbox(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    left = max(0, min(width - 1, math.floor(x0)))
    top = max(0, min(height - 1, math.floor(y0)))
    right = max(left + 1, min(width, math.ceil(x1)))
    bottom = max(top + 1, min(height, math.ceil(y1)))
    return left, top, right, bottom


def _normalized_bbox(
    bbox: tuple[int, int, int, int], width: int, height: int
) -> tuple[float, float, float, float]:
    return tuple(
        round(value, 10)
        for value in (
            bbox[0] / width,
            bbox[1] / height,
            bbox[2] / width,
            bbox[3] / height,
        )
    )


def _row_context_span(
    triggers: list[LocalizedTrigger],
    role_c_rows: list[dict[str, Any]],
    boxes: tuple[tuple[float, float, float, float], ...],
    line_height: float,
    policy: TargetedRereadPolicy,
) -> tuple[float, float, tuple[int, ...]]:
    requested = {index for trigger in triggers for index in trigger.role_c_indices}
    if requested:
        low = max(0, min(requested) - policy.context_rows_before)
        high = min(len(role_c_rows) - 1, max(requested) + policy.context_rows_after)
        context_indices = range(low, high + 1)
        spans = []
        lines: set[int] = set()
        for row_index in context_indices:
            row = role_c_rows[row_index]
            row_lines = _row_line_indices(row)
            lines.update(row_lines)
            spans.append(
                _line_span(
                    row_lines,
                    boxes,
                    fallback_anchor=_row_anchor(row),
                    line_height=line_height,
                )
            )
        return (
            min([trigger.y0 for trigger in triggers] + [span[0] for span in spans]),
            max([trigger.y1 for trigger in triggers] + [span[1] for span in spans]),
            tuple(sorted(lines)),
        )
    return (
        min(trigger.y0 for trigger in triggers),
        max(trigger.y1 for trigger in triggers),
        tuple(sorted({index for trigger in triggers for index in trigger.line_indices})),
    )


def _group_triggers(
    triggers: list[LocalizedTrigger], policy: TargetedRereadPolicy, line_height: float
) -> list[list[LocalizedTrigger]]:
    ordered = sorted(
        triggers, key=lambda trigger: (trigger.y0, trigger.y1, trigger.alignment_index)
    )
    groups: list[list[LocalizedTrigger]] = []
    for trigger in ordered:
        if not groups:
            groups.append([trigger])
            continue
        previous = groups[-1]
        current_end = max(item.y1 for item in previous)
        if (
            trigger.y0 - current_end <= policy.group_gap_line_heights * line_height
            and len(previous) < policy.maximum_trigger_units_per_band
        ):
            previous.append(trigger)
        else:
            groups.append([trigger])
    return groups


def _region(
    *,
    sequence: int,
    kind: str,
    triggers: list[LocalizedTrigger],
    bbox: tuple[int, int, int, int],
    width: int,
    height: int,
    profile: RereadProfile,
    context_lines: tuple[int, ...],
    includes_period_headers: bool,
) -> TargetedRereadRegion:
    return TargetedRereadRegion(
        region_id=f"region-{sequence:04d}",
        region_kind=kind,
        bbox_in_baseline_render=bbox,
        bbox_normalized=_normalized_bbox(bbox, width, height),
        trigger_alignment_indices=tuple(sorted(trigger.alignment_index for trigger in triggers)),
        escalations=tuple(sorted({trigger.escalation for trigger in triggers})),
        role_b_indices=tuple(
            sorted({index for trigger in triggers for index in trigger.role_b_indices})
        ),
        role_c_indices=tuple(
            sorted({index for trigger in triggers for index in trigger.role_c_indices})
        ),
        source_line_indices=tuple(
            sorted(
                set(context_lines)
                | {index for trigger in triggers for index in trigger.line_indices}
            )
        ),
        localization_methods=tuple(sorted({trigger.localization for trigger in triggers})),
        target_dpi=profile.dpi,
        readers=profile.readers,
        variant_policy=profile.variant_policy,
        includes_period_header_pixels=includes_period_headers,
        period_binding_from_reread_allowed=includes_period_headers,
    )


def plan_page_targeted_rereads(
    page_record: dict[str, Any],
    baseline_ocr_payload: dict[str, Any],
    *,
    baseline_width: int,
    baseline_height: int,
    policy: TargetedRereadPolicy,
) -> dict[str, Any]:
    """Plan evidence-preserving crop rereads from structural failure signals.

    The planner consumes only current page structure and geometry. It never uses
    institution identity, schema candidates, values from history, or arithmetic.
    """

    if baseline_width < 1 or baseline_height < 1:
        raise TargetedRereadError("baseline render dimensions must be positive")
    page = page_record.get("page")
    statement_type = page_record.get("statement_type")
    if not isinstance(page, int) or page < 1 or statement_type not in {"CDKT", "KQKD", "LCTT"}:
        raise TargetedRereadError("page record lacks valid page/statement identity")
    if page_record.get("mapping_eligible") is not True:
        return {
            "page": page,
            "statement_type": statement_type,
            "status": "SKIPPED_UPSTREAM_MAPPING_INELIGIBLE",
            "regions": [],
            "unsupported_escalations": [],
            "safety": dict(policy.safety),
        }
    boxes = _validated_boxes(baseline_ocr_payload)
    role_c = page_record.get("role_c")
    role_b = page_record.get("role_b")
    if not isinstance(role_c, dict) or not isinstance(role_b, dict):
        raise TargetedRereadError("page lacks reader evidence")
    role_c_rows = role_c.get("rows")
    table_bbox = role_c.get("table_bbox")
    line_height = role_c.get("line_height")
    axes = role_c.get("axes")
    if (
        not isinstance(role_c_rows, list)
        or not isinstance(table_bbox, list)
        or len(table_bbox) != 4
        or not isinstance(line_height, (int, float))
        or isinstance(line_height, bool)
        or line_height <= 0
        or not isinstance(axes, list)
        or not axes
    ):
        raise TargetedRereadError("Role C page geometry is incomplete")
    localized, unsupported = _localized_triggers(page_record, boxes, policy)
    if not localized:
        status = "UNRESOLVED_UNSUPPORTED_ESCALATION" if unsupported else "NO_REREAD_TRIGGER"
        return {
            "page": page,
            "statement_type": statement_type,
            "status": status,
            "regions": [],
            "unsupported_escalations": unsupported,
            "safety": dict(policy.safety),
        }
    structural = [trigger for trigger in localized if trigger.structural]
    row_denominator = max(len(role_c_rows), 1)
    tables = role_b.get("tables", [])
    unresolved_table = isinstance(tables, list) and any(
        isinstance(table, dict) and table.get("status") == "UNRESOLVED_COLUMN_ROLES"
        for table in tables
    )
    dense_structural = len(structural) >= policy.dense_structural_trigger_minimum and (
        len(structural) / row_denominator >= policy.dense_structural_trigger_fraction
    )
    x0, table_y0, x1, table_y1 = (float(value) for value in table_bbox)
    horizontal_margin = float(line_height) * policy.horizontal_margin_line_heights
    vertical_margin = float(line_height) * policy.vertical_margin_line_heights
    regions: list[TargetedRereadRegion] = []
    if unresolved_table or dense_structural:
        header_indices = []
        for axis in axes:
            index = axis.get("header_line_index") if isinstance(axis, dict) else None
            if not isinstance(index, int) or index < 0 or index >= len(boxes):
                raise TargetedRereadError("period axis lacks a valid baseline header line")
            header_indices.append(index)
        header_y0 = min(boxes[index][1] for index in header_indices)
        bbox = _clamped_bbox(
            x0 - horizontal_margin,
            min(table_y0, header_y0) - vertical_margin,
            x1 + horizontal_margin,
            max(table_y1, max(trigger.y1 for trigger in localized)) + vertical_margin,
            width=baseline_width,
            height=baseline_height,
        )
        regions.append(
            _region(
                sequence=1,
                kind="FULL_TABLE_STRUCTURAL_RECOVERY",
                triggers=localized,
                bbox=bbox,
                width=baseline_width,
                height=baseline_height,
                profile=policy.profiles["full_table_structural"],
                context_lines=tuple(header_indices),
                includes_period_headers=True,
            )
        )
        handled = {trigger.alignment_index for trigger in localized}
    else:
        handled = set()
    remaining = [trigger for trigger in localized if trigger.alignment_index not in handled]
    for group in _group_triggers(remaining, policy, float(line_height)):
        y0, y1, context_lines = _row_context_span(
            group,
            role_c_rows,
            boxes,
            float(line_height),
            policy,
        )
        is_structural = any(trigger.structural for trigger in group)
        profile_name = "row_band_structural" if is_structural else "numeric_cell_strip"
        kind = "ROW_BAND_STRUCTURAL_RECOVERY" if is_structural else "NUMERIC_CELL_STRIP_REREAD"
        bbox = _clamped_bbox(
            x0 - horizontal_margin,
            y0 - vertical_margin,
            x1 + horizontal_margin,
            y1 + vertical_margin,
            width=baseline_width,
            height=baseline_height,
        )
        regions.append(
            _region(
                sequence=len(regions) + 1,
                kind=kind,
                triggers=group,
                bbox=bbox,
                width=baseline_width,
                height=baseline_height,
                profile=policy.profiles[profile_name],
                context_lines=context_lines,
                includes_period_headers=False,
            )
        )
    return {
        "page": page,
        "statement_type": statement_type,
        "status": "PLANNED" if not unsupported else "PLANNED_WITH_UNSUPPORTED_ESCALATIONS",
        "baseline_render": {
            "width_pixels": baseline_width,
            "height_pixels": baseline_height,
            "input_path_from_ocr": str(baseline_ocr_payload.get("input_path", "")),
        },
        "trigger_count": len(localized),
        "structural_trigger_count": len(structural),
        "structural_trigger_fraction_of_role_c_rows": round(len(structural) / row_denominator, 10),
        "unresolved_role_b_table_present": unresolved_table,
        "dense_structural_recovery": dense_structural,
        "regions": [region.to_dict() for region in regions],
        "unsupported_escalations": unsupported,
        "safety": dict(policy.safety),
    }
