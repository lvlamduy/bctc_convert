"""Resolve detector-omitted maturity source-population dashes from page pixels.

The maturity graph first identifies one source-only additive population, its
SHORT breakdown, the two money lanes, and the printed grand total.  This
overlay proposes only the missing row/lane regions from that graph and crops an
authenticated source-page render.  It accepts a visible horizontal dash, or
one degraded centered mark only with a distinct same-lane clear-dash peer and
both observed equations exact; the raw glyph classification remains intact.
Blank regions never mean zero and accounting remains final corroboration/veto;
no bank, filename, page, period, note, or schema route is available.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation.accounting_table_axes_v1 import (
    line_has_accounting_value_surface_v1,
    money_integer_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.evaluation.family_first_visible_dash_glyph_evidence_v1 import (
    build_family_first_visible_dash_glyph_evidence_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import loan_maturity_variant_graph_v2 as graph_v2
from scripts.experiments import loan_type_missing_cell_evidence_v1 as shared_pixel_v1

__all__ = [
    "FORMAT_VERSION",
    "LoanMaturityAdditionalPopulationEvidenceV1Error",
    "build_loan_maturity_additional_population_evidence_v1",
    "validate_loan_maturity_additional_population_evidence_replay_v1",
    "validate_loan_maturity_additional_population_evidence_v1",
]


FORMAT_VERSION = "LOAN_MATURITY_ADDITIONAL_POPULATION_EVIDENCE_V1"
CLAIM_BOUNDARY = (
    "UNIQUE_MATURITY_SOURCE_ONLY_PARENT_SHORT_AND_GRAND_ROWS_AUTHENTICATED_"
    "PIXEL_DASH_OR_ONE_PAIRED_CENTERED_HIGH_FILL_SHORT_MARK_EVIDENCE_PLUS_"
    "EXACT_ACCOUNTING_"
    "VETO_ONLY_NO_BANK_FILENAME_PAGE_PERIOD_NOTE_SCHEMA_MAPPING_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_equation_used_as_final_corroboration_and_veto_only": True,
    "bank_filename_note_page_or_period_routing_authority": False,
    "blank_or_detector_omission_means_zero": False,
    "mapping_authority": False,
    "numeric_digits_authority": False,
    "one_centered_high_fill_short_mark_requires_related_clear_dash_peer": True,
    "paired_short_mark_requires_both_observed_equations_exact": True,
    "schema_authority": False,
    "visible_authenticated_pixel_dash_may_normalize_to_zero": True,
}
_FIELDS = {
    "accounting_checks",
    "additional_population",
    "authority",
    "base_result_id",
    "claim_boundary",
    "document_ordinal",
    "evidence",
    "family_id",
    "format_version",
    "page_sequence",
    "render_id",
    "render_ref",
    "result_id",
    "status",
}


class LoanMaturityAdditionalPopulationEvidenceV1Error(ValueError):
    """The graph, source page, pixel glyph, or exact equations drifted."""


def _error(message: str) -> LoanMaturityAdditionalPopulationEvidenceV1Error:
    return LoanMaturityAdditionalPopulationEvidenceV1Error(message)


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _selected_joined_page(
    joined_pages: Sequence[Mapping[str, Any]], *, page_sequence: int
) -> dict[str, Any]:
    if isinstance(joined_pages, (str, bytes, bytearray)) or not isinstance(joined_pages, Sequence):
        raise _error("joined pages must be one exact sequence")
    matches = [page for page in joined_pages if page.get("page_sequence") == page_sequence]
    if len(matches) != 1:
        raise _error("maturity additional-population page is not unique in joined evidence")
    raw_page = matches[0]
    if (
        type(raw_page) is not dict
        or set(raw_page) != {"lines", "page_sequence", "page_width"}
        or type(raw_page["page_width"]) is not int
        or raw_page["page_width"] <= 0
        or type(raw_page["lines"]) is not list
    ):
        raise _error("joined maturity page fields or width drifted")
    lines = []
    seen = set()
    for raw in raw_page["lines"]:
        if (
            type(raw) is not dict
            or set(raw)
            != {
                "bbox",
                "crop_ref",
                "line_ordinal",
                "numeric_recognition",
                "sample_id",
                "vietocr_text",
            }
            or type(raw["line_ordinal"]) is not int
            or raw["line_ordinal"] < 0
            or raw["line_ordinal"] in seen
            or type(raw["vietocr_text"]) is not str
            or type(raw["sample_id"]) is not str
            or not raw["sample_id"]
            or type(raw["numeric_recognition"]) is not dict
            or set(raw["numeric_recognition"]) != {"raw_prediction", "reader_score"}
            or type(raw["numeric_recognition"]["raw_prediction"]) is not str
        ):
            raise _error("joined maturity line fields drifted")
        seen.add(raw["line_ordinal"])
        lines.append(canonical_clone_v1(raw))
    if [line["line_ordinal"] for line in lines] != list(range(len(lines))):
        raise _error("joined maturity line ordinal axis drifted")
    return {
        "lines": lines,
        "page_sequence": page_sequence,
        "page_width": raw_page["page_width"],
    }


def _matcher_page(page: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "lines": [
            {
                "bbox": canonical_clone_v1(line["bbox"]),
                "source_line_index": line["line_ordinal"],
                "source_text": line["numeric_recognition"]["raw_prediction"],
                "vietocr_text": line["vietocr_text"],
            }
            for line in page["lines"]
        ],
        "page_sequence": page["page_sequence"],
        "primary_numeric_authority": True,
    }


def _line_axis(page: Mapping[str, Any]) -> dict[int, Mapping[str, Any]]:
    return {line["line_ordinal"]: line for line in page["lines"]}


def _lane_centers(graph: Mapping[str, Any]) -> tuple[float, ...]:
    by_lane: dict[int, list[float]] = {}
    for row in graph["rows"]:
        for cell in row["values"]:
            if cell["lane_type"] != "MONEY":
                continue
            by_lane.setdefault(cell["lane_index"], []).append(cell["x_center_x2"] / 2)
    if set(by_lane) != {0, 1}:
        raise _error("additional-population graph does not retain two money lanes")
    centers = tuple(sum(by_lane[lane]) / len(by_lane[lane]) for lane in sorted(by_lane))
    if list(centers) != sorted(set(centers)):
        raise _error("additional-population money lane centers drifted")
    return centers


def _bind_visible_cell(
    cell: Mapping[str, Any], line_by_index: Mapping[int, Mapping[str, Any]]
) -> int:
    source_index = cell.get("source_line_index")
    line = line_by_index.get(source_index)
    numeric = line.get("numeric_recognition") if line is not None else None
    if (
        type(source_index) is not int
        or line is None
        or line["bbox"] != cell.get("bbox")
        or line["vietocr_text"] != cell.get("semantic_surface")
        or type(numeric) is not dict
        or numeric["raw_prediction"] != cell.get("surface")
        or cell.get("source_authoritative") is not True
    ):
        raise _error("visible additional-population cell differs from joined evidence")
    parsed = money_integer_v1(cell["surface"])
    if parsed is None:
        raise _error("visible additional-population cell is not one integer-money token")
    return parsed


def _label_boxes(
    record: Mapping[str, Any], line_by_index: Mapping[int, Mapping[str, Any]]
) -> list[list[int]]:
    indices = record.get("label_source_line_indices")
    if type(indices) is not list or not indices or any(type(index) is not int for index in indices):
        raise _error("additional-population label line axis drifted")
    boxes = []
    for index in indices:
        line = line_by_index.get(index)
        if line is None:
            raise _error("additional-population label is absent from joined page")
        boxes.append(canonical_clone_v1(line["bbox"]))
    return boxes


def _dash_region(
    render_snapshot: Mapping[str, Any],
    *,
    proposal: Mapping[str, Any],
    label_baseline_y: int,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    snapshot = dict(render_snapshot)
    region = region_v1._crop_authenticated_family_first_page_render_snapshot_v1(
        snapshot, raw_pixel_bbox=proposal["raw_pixel_bbox"]
    )
    dash = build_family_first_visible_dash_glyph_evidence_v1(
        crop_png_bytes=region["region_png_bytes"]
    )
    selection = "DIRECT_ADAPTIVE_BODY_GRID_REGION"
    if dash["classification"] != "VISIBLE_HORIZONTAL_DASH_GLYPH":
        _record, render = region_v1._validated_render_snapshot(snapshot)
        tight = shared_pixel_v1._tight_dash_bbox(
            render,
            proposal["raw_pixel_bbox"],
            label_baseline_y=label_baseline_y,
        )
        if tight is not None:
            tight_region = region_v1._crop_authenticated_family_first_page_render_snapshot_v1(
                snapshot, raw_pixel_bbox=tight
            )
            tight_dash = build_family_first_visible_dash_glyph_evidence_v1(
                crop_png_bytes=tight_region["region_png_bytes"]
            )
            if tight_dash["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH":
                region, dash = tight_region, tight_dash
                selection = "SHARED_UNIQUE_NEAREST_LABEL_BASELINE_DASH_COMPONENT"
    return region, dash, selection


def _resolve_vector(
    record: Mapping[str, Any],
    *,
    role: str,
    matcher_page: Mapping[str, Any],
    joined_page: Mapping[str, Any],
    render_snapshot: Mapping[str, Any],
    lane_centers: tuple[float, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    vector = record.get("values")
    if (
        type(vector) is not list
        or len(vector) != len(lane_centers)
        or [cell.get("lane_index") for cell in vector] != list(range(len(lane_centers)))
        or any(cell.get("lane_type") != "MONEY" for cell in vector)
    ):
        raise _error("additional-population value vector drifted")
    line_by_index = _line_axis(joined_page)
    label_boxes = _label_boxes(record, line_by_index)
    visible = [
        {
            "bbox": canonical_clone_v1(cell["bbox"]),
            "column_ordinal": cell["lane_index"],
        }
        for cell in vector
        if cell.get("source_line_index") is not None
    ]
    proposals = {
        proposal["column_ordinal"]: proposal
        for proposal in propose_missing_value_lane_regions_v1(
            matcher_page["lines"],
            label_boxes=label_boxes,
            is_numeric=line_has_accounting_value_surface_v1,
            page_width=joined_page["page_width"],
            page_height=render_snapshot["render_ref"]["pixel_height"],
            minimum_x_ratio=0.05,
            maximum_x_ratio=0.995,
            resolved_column_centers=lane_centers,
            resolved_visible_value_cells=visible,
        )
    }
    selected = []
    evidence = []
    for cell in vector:
        lane = cell["lane_index"]
        if cell.get("source_line_index") is not None:
            value = _bind_visible_cell(cell, line_by_index)
            selected.append(
                {
                    "bbox": canonical_clone_v1(cell["bbox"]),
                    "lane_index": lane,
                    "lane_type": "MONEY",
                    "ppocrv6_surface": cell["surface"],
                    "selected_surface": cell["surface"],
                    "selected_value": value,
                    "selection_mode": "BOUND_PPOCRV6_PRIMARY",
                    "source_line_index": cell["source_line_index"],
                    "vietocr_transformer_surface": cell["semantic_surface"],
                }
            )
            continue
        if cell.get("status") != ("MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_EVIDENCE"):
            raise _error("additional-population unresolved cell reason drifted")
        proposal = proposals.get(lane)
        if proposal is None:
            raise _error("additional-population missing lane has no adaptive proposal")
        region, dash, selection = _dash_region(
            render_snapshot,
            proposal=proposal,
            label_baseline_y=max(box[3] for box in label_boxes),
        )
        recognized = dash["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
        selected.append(
            {
                "bbox": None,
                "lane_index": lane,
                "lane_type": "MONEY",
                "ppocrv6_surface": None,
                "selected_surface": "-" if recognized else None,
                "selected_value": 0 if recognized else None,
                "selection_mode": (
                    "AUTHENTICATED_PIXEL_VISIBLE_DASH_ZERO"
                    if recognized
                    else "UNRESOLVED_PIXEL_GLYPH"
                ),
                "source_line_index": None,
                "vietocr_transformer_surface": None,
            }
        )
        evidence.append(
            {
                "classification": (
                    "VISIBLE_PIXEL_DASH_ZERO" if recognized else "UNRESOLVED_PIXEL_GLYPH"
                ),
                "dash_evidence": dash,
                "lane_index": lane,
                "proposed_raw_pixel_bbox": canonical_clone_v1(proposal["raw_pixel_bbox"]),
                "recognition_raw_pixel_bbox": canonical_clone_v1(
                    region["recognition_raw_pixel_bbox"]
                ),
                "region_id": region["region_id"],
                "region_png_ref": canonical_clone_v1(region["region_png_ref"]),
                "role": role,
                "row_band_evidence": proposal["row_band_evidence"],
                "selection": selection,
            }
        )
    return selected, evidence


def _centered_high_fill_short_mark_candidate(evidence: Mapping[str, Any]) -> bool:
    """Recognize only the narrow raw-metric gap seen in one embedded dash font."""

    raw = evidence.get("dash_evidence")
    metrics = raw.get("glyph_metrics") if type(raw) is dict else None
    return (
        type(metrics) is dict
        and metrics.get("component_count") == 1
        and type(metrics.get("component_aspect_ratio")) is float
        and 1.1 <= metrics["component_aspect_ratio"] < 1.25
        and type(metrics.get("component_height_ratio")) is float
        and 0.2 <= metrics["component_height_ratio"] <= 0.3
        and type(metrics.get("component_width_ratio")) is float
        and 0.15 <= metrics["component_width_ratio"] <= 0.3
        and type(metrics.get("ink_fill_ratio")) is float
        and metrics["ink_fill_ratio"] >= 0.6
        and type(metrics.get("horizontal_center_displacement_ratio")) is float
        and metrics["horizontal_center_displacement_ratio"] <= 0.05
        and type(metrics.get("vertical_center_displacement_ratio")) is float
        and metrics["vertical_center_displacement_ratio"] <= 0.05
    )


def _promote_one_paired_short_mark(
    parent_values: list[dict[str, Any]],
    child_values: list[dict[str, Any]],
    parent_evidence: list[dict[str, Any]],
    child_evidence: list[dict[str, Any]],
) -> None:
    """Admit one centered mark only beside its duplicated-population dash peer."""

    parent_by_lane = {item["lane_index"]: item for item in parent_evidence}
    child_by_lane = {item["lane_index"]: item for item in child_evidence}
    for lane in range(len(parent_values)):
        parent = parent_by_lane.get(lane)
        child = child_by_lane.get(lane)
        if parent is None or child is None:
            continue
        pair = ((parent, parent_values[lane], child), (child, child_values[lane], parent))
        promotable = [
            (candidate, cell)
            for candidate, cell, peer in pair
            if _centered_high_fill_short_mark_candidate(candidate)
            and peer["classification"] == "VISIBLE_PIXEL_DASH_ZERO"
            and candidate["region_id"] != peer["region_id"]
        ]
        if len(promotable) != 1:
            continue
        candidate, cell = promotable[0]
        candidate["classification"] = "PAIRED_CENTERED_HIGH_FILL_SHORT_MARK_CANDIDATE"
        peer = child if candidate is parent else parent
        candidate["paired_clear_dash_peer_region_id"] = peer["region_id"]
        candidate["paired_clear_dash_peer_role"] = peer["role"]
        cell.update(
            {
                "selected_surface": "-",
                "selected_value": 0,
                "selection_mode": (
                    "RELATED_PARENT_SHORT_CLEAR_DASH_PEER_PLUS_EXACT_ACCOUNTING_REQUIRED"
                ),
            }
        )


def _result_shape(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["family_id"] != graph_v2.FAMILY_ID
        or value["status"]
        not in {
            "AUTHENTICATED_PIXEL_DASH_AND_ACCOUNTING_EXACT",
            "UNRESOLVED_PIXEL_GLYPH_OR_ACCOUNTING",
        }
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["accounting_checks"]) is not list
        or type(value["evidence"]) is not list
    ):
        raise _error("maturity additional-population evidence result shape drifted")
    _positive_int(value["document_ordinal"], "additional-population document ordinal")
    _positive_int(value["page_sequence"], "additional-population page")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "lmaperv1:result:" + canonical_json_sha256_v1(material):
        raise _error("maturity additional-population evidence identity drifted")
    return canonical_clone_v1(value)


def build_loan_maturity_additional_population_evidence_v1(
    base: Any,
    joined_pages: Sequence[Mapping[str, Any]],
    render_snapshot: Mapping[str, Any],
    *,
    document_ordinal: int,
) -> dict[str, Any]:
    """Resolve one graph's detector holes without changing its raw OCR evidence."""

    graph_v2.validate_loan_maturity_variant_graph_document_v2(base)
    _positive_int(document_ordinal, "additional-population document ordinal")
    if (
        base["status"] != "UNRESOLVED"
        or len(base["graphs"]) != 1
        or base["graphs"][0]["unresolved_reasons"]
        != ["ADDITIONAL_POPULATION_VISIBLE_DASH_EVIDENCE_REQUIRED"]
    ):
        raise _error("pixel-dash overlay requires the one expected maturity base veto")
    graph = base["graphs"][0]
    if len(graph["additional_source_populations"]) != 1:
        raise _error("pixel-dash overlay requires one source-only additive population")
    population = graph["additional_source_populations"][0]
    page_sequence = graph["rows"][0]["label"]["page_sequence"]
    joined_page = _selected_joined_page(joined_pages, page_sequence=page_sequence)
    matcher_page = _matcher_page(joined_page)
    render_record, _render = region_v1._validated_render_snapshot(dict(render_snapshot))
    if (
        render_record["document_ordinal"] != document_ordinal
        or render_record["physical_page"] != page_sequence
        or render_record["render_ref"]["pixel_width"] != joined_page["page_width"]
    ):
        raise _error("authenticated render and maturity graph select another document/page")
    centers = _lane_centers(graph)
    parent_values, parent_evidence = _resolve_vector(
        population,
        role="ADDITIONAL_PARENT",
        matcher_page=matcher_page,
        joined_page=joined_page,
        render_snapshot=render_snapshot,
        lane_centers=centers,
    )
    child_values, child_evidence = _resolve_vector(
        population["breakdown"],
        role="ADDITIONAL_SHORT_BREAKDOWN",
        matcher_page=matcher_page,
        joined_page=joined_page,
        render_snapshot=render_snapshot,
        lane_centers=centers,
    )
    _promote_one_paired_short_mark(
        parent_values,
        child_values,
        parent_evidence,
        child_evidence,
    )
    grand = population.get("grand_total")
    if (
        type(grand) is not dict
        or type(grand.get("values")) is not list
        or len(grand["values"]) != 2
        or [cell.get("lane_index") for cell in grand["values"]] != [0, 1]
        or any(cell.get("lane_type") != "MONEY" for cell in grand["values"])
    ):
        raise _error("additional-population printed grand total is absent")
    line_by_index = _line_axis(joined_page)
    grand_values = [_bind_visible_cell(cell, line_by_index) for cell in grand["values"]]
    core = graph["accounting"]["core_money_values"]
    checks = []
    for lane, (parent, child, printed_grand) in enumerate(
        zip(parent_values, child_values, grand_values, strict=True)
    ):
        parent_value = parent["selected_value"]
        child_value = child["selected_value"]
        equality_exact = (
            type(parent_value) is int and type(child_value) is int and parent_value == child_value
        )
        grand_exact = (
            type(parent_value) is int
            and type(core[lane]) is int
            and core[lane] + parent_value == printed_grand
        )
        checks.extend(
            [
                {
                    "equation": "ADDITIONAL_PARENT_EQUALS_SHORT_BREAKDOWN",
                    "lane_index": lane,
                    "left_value": parent_value,
                    "right_value": child_value,
                    "status": "CORROBORATED_EXACT" if equality_exact else "UNRESOLVED",
                },
                {
                    "addend_core": core[lane],
                    "addend_source_only_population": parent_value,
                    "equation": "CORE_PLUS_ADDITIONAL_EQUALS_PRINTED_GRAND",
                    "lane_index": lane,
                    "printed_grand": printed_grand,
                    "status": "CORROBORATED_EXACT" if grand_exact else "UNRESOLVED",
                },
            ]
        )
    evidence = [*parent_evidence, *child_evidence]
    exact = (
        evidence
        and all(
            item["classification"]
            in {
                "PAIRED_CENTERED_HIGH_FILL_SHORT_MARK_CANDIDATE",
                "VISIBLE_PIXEL_DASH_ZERO",
            }
            for item in evidence
        )
        and all(check["status"] == "CORROBORATED_EXACT" for check in checks)
    )
    selected_population = copy.deepcopy(population)
    selected_population["values"] = parent_values
    selected_population["breakdown"]["values"] = child_values
    selected_population["grand_total"]["selected_values"] = grand_values
    material = {
        "accounting_checks": checks,
        "additional_population": selected_population,
        "authority": canonical_clone_v1(_AUTHORITY),
        "base_result_id": base["result_id"],
        "claim_boundary": CLAIM_BOUNDARY,
        "document_ordinal": document_ordinal,
        "evidence": evidence,
        "family_id": graph_v2.FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "page_sequence": page_sequence,
        "render_id": render_snapshot["render_id"],
        "render_ref": canonical_clone_v1(render_record["render_ref"]),
        "status": (
            "AUTHENTICATED_PIXEL_DASH_AND_ACCOUNTING_EXACT"
            if exact
            else "UNRESOLVED_PIXEL_GLYPH_OR_ACCOUNTING"
        ),
    }
    return _result_shape(
        {**material, "result_id": "lmaperv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_loan_maturity_additional_population_evidence_v1(value: Any) -> dict[str, Any]:
    """Validate one persisted overlay's exact typed identity."""

    return _result_shape(value)


def validate_loan_maturity_additional_population_evidence_replay_v1(
    value: Any,
    base: Any,
    joined_pages: Sequence[Mapping[str, Any]],
    render_snapshot: Mapping[str, Any],
    *,
    document_ordinal: int,
) -> dict[str, Any]:
    """Rebuild one overlay from the same graph, page evidence, and source pixels."""

    persisted = _result_shape(value)
    rebuilt = build_loan_maturity_additional_population_evidence_v1(
        base,
        joined_pages,
        render_snapshot,
        document_ordinal=document_ordinal,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("maturity additional-population pixel evidence does not replay exactly")
    return canonical_clone_v1(rebuilt)
