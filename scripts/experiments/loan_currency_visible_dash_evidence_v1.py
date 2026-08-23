"""Content-addressed visible-dash evidence for loan-currency detector holes.

The generic row-axis engine proposes a missing money-lane rectangle from the
observed body grid.  This wrapper binds that proposal to an authenticated
document packet and exact full-page render, classifies the resulting immutable
crop with the shared dash classifier, and records the completed row axis.

Persisted JSON intentionally contains references rather than pixel bytes.
Exact replay crops the authenticated render again and reruns the classifier.
The separate numeric-binding accessor returns the crop bytes only after that
replay, so a self-rehashed JSON mutation cannot create numeric authority.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation import accounting_family_column_context_v1 as column_context_v1
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_axis_v1
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import family_first_accounting_evidence_sweep_v1 as sweep_v1
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import loan_currency_variant_graph_v2 as graph_v2

__all__ = [
    "FORMAT_VERSION",
    "LoanCurrencyVisibleDashEvidenceV1Error",
    "build_loan_currency_bounded_dash_peer_bindings_v1",
    "build_loan_currency_visible_dash_evidence_v1",
    "read_loan_currency_dash_cell_replay_material_v1",
    "read_loan_currency_visible_dash_numeric_bindings_v1",
    "validate_loan_currency_visible_dash_evidence_replay_v1",
    "validate_loan_currency_visible_dash_evidence_v1",
]


FORMAT_VERSION = "LOAN_CURRENCY_VISIBLE_DASH_EVIDENCE_V1"
CLAIM_BOUNDARY = (
    "AUTHENTICATED_DOCUMENT_PACKET_FULL_PAGE_RENDER_BODY_GRID_ROLE_LANE_REGION_"
    "AND_EXACT_PIXEL_DASH_REPLAY_ONLY_NO_BLANK_ZERO_ACCOUNTING_BACKSOLVE_BANK_"
    "PAGE_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_can_infer_or_backsolve_zero": False,
    "bank_filename_note_page_or_period_routing_authority": False,
    "blank_or_detector_omission_means_zero": False,
    "bounded_candidate_requires_distinct_contextual_direct_peer": True,
    "bounded_high_fill_candidate_alone_means_zero": False,
    "candidate_peer_selection_uses_accounting_values": False,
    "exact_authenticated_crop_replay_required_before_numeric_use": True,
    "mapping_authority": False,
    "schema_authority": False,
    "visible_horizontal_dash_may_normalize_to_zero": True,
}
_FIELDS = {
    "authority",
    "base_row_axis_id",
    "claim_boundary",
    "column_context_binding",
    "completed_row_axis",
    "document_binding",
    "evidence_id",
    "family_id",
    "format_version",
    "render_bindings",
    "rescue_cells",
    "status",
    "topology_scan_id",
}
_DOCUMENT_BINDING_FIELDS = {
    "document_evidence_root_sha256",
    "document_id",
    "document_ordinal",
    "packet_id",
    "source_pdf_ref",
}
_RENDER_BINDING_FIELDS = {
    "archive_id",
    "index_id",
    "physical_page",
    "plan_id",
    "render_id",
    "render_ref",
}
_CELL_FIELDS = {
    "admission_class",
    "cell_id",
    "classification",
    "column_ordinal",
    "dash_evidence",
    "injected_value_sample_id",
    "label_match_sha256",
    "page_sequence",
    "proposed_raw_pixel_bbox",
    "recognition_raw_pixel_bbox",
    "region_id",
    "region_png_ref",
    "render_id",
    "resolved_period",
    "role",
    "source_population_role",
    "source_population_surface",
}
_COLUMN_CONTEXT_BINDING_FIELDS = {
    "column_context_id",
    "period_axis",
    "row_axis_id",
    "status",
    "unit_axis",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ACCEPTED_STATUS = "AUTHENTICATED_VISIBLE_DASH_CELLS_BOUND"
_BOUNDED_CANDIDATE_STATUS = "AUTHENTICATED_DIRECT_AND_BOUNDED_CANDIDATE_CELLS_BOUND"
_UNRESOLVED_STATUS = "UNRESOLVED_PIXEL_GLYPH_OR_ROW_AXIS"


class LoanCurrencyVisibleDashEvidenceV1Error(ValueError):
    """The packet, render, grid proposal, crop, glyph or replay drifted."""


def _error(message: str) -> LoanCurrencyVisibleDashEvidenceV1Error:
    return LoanCurrencyVisibleDashEvidenceV1Error(message)


def _strict_ref(value: Any, label: str, *, render: bool = False) -> dict[str, Any]:
    fields = (
        {"path", "sha256", "size_bytes"}
        if not render
        else {
            "pixel_height",
            "pixel_width",
            "sha256",
            "size_bytes",
        }
    )
    if (
        type(value) is not dict
        or set(value) != fields
        or type(value["sha256"]) is not str
        or _SHA256.fullmatch(value["sha256"]) is None
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
        or (not render and (type(value["path"]) is not str or not value["path"]))
        or (
            render
            and (
                type(value["pixel_height"]) is not int
                or value["pixel_height"] <= 0
                or type(value["pixel_width"]) is not int
                or value["pixel_width"] <= 0
            )
        )
    ):
        raise _error(f"{label} reference drifted")
    return canonical_clone_v1(value)


def _strict_blob_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"sha256", "size_bytes"}
        or type(value["sha256"]) is not str
        or _SHA256.fullmatch(value["sha256"]) is None
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"{label} reference drifted")
    return canonical_clone_v1(value)


def _document_packet(value: Any) -> dict[str, Any]:
    if type(value) is not dict or type(value.get("document_ordinal")) is not int:
        raise _error("loan-currency dash document packet drifted")
    try:
        return store_v1._packet(value, value["document_ordinal"])
    except (ValueError, RuntimeError) as exc:
        raise _error("loan-currency dash document packet is not self-consistent") from exc


def _document_binding(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
        "document_id": packet["document_id"],
        "document_ordinal": packet["document_ordinal"],
        "packet_id": packet["packet_id"],
        "source_pdf_ref": canonical_clone_v1(packet["source_pdf_ref"]),
    }


def _render_snapshots(
    values: Any, *, document_ordinal: int
) -> tuple[tuple[dict[str, Any], ...], list[dict[str, Any]]]:
    if (
        isinstance(values, (str, bytes, bytearray))
        or not isinstance(values, Sequence)
        or not values
    ):
        raise _error("loan-currency dash needs authenticated page renders")
    snapshots = []
    bindings = []
    pages = set()
    for value in values:
        if type(value) is not dict:
            raise _error("loan-currency page render is not one exact object")
        try:
            record, _payload = region_v1._validated_render_snapshot(value)
        except (ValueError, RuntimeError) as exc:
            raise _error("loan-currency page render does not authenticate") from exc
        page = record["physical_page"]
        if record["document_ordinal"] != document_ordinal or page in pages:
            raise _error("loan-currency page render document/page binding drifted")
        pages.add(page)
        snapshots.append(dict(value))
        bindings.append(
            {
                "archive_id": record["archive_id"],
                "index_id": record["index_id"],
                "physical_page": page,
                "plan_id": record["plan_id"],
                "render_id": value["render_id"],
                "render_ref": canonical_clone_v1(record["render_ref"]),
            }
        )
    order = sorted(range(len(bindings)), key=lambda index: bindings[index]["physical_page"])
    return tuple(snapshots[index] for index in order), [bindings[index] for index in order]


def _base_inputs(
    base_row_axis: Any,
    topology_scan: Any,
    joined_pages: Any,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    if type(joined_pages) is not list or not joined_pages:
        raise _error("loan-currency dash joined-page axis drifted")
    try:
        base = row_axis_v1._validate_result(base_row_axis)
        scan = topology_v1._validate_result(topology_scan)
    except (ValueError, RuntimeError) as exc:
        raise _error("loan-currency dash topology/row-axis identity drifted") from exc
    if (
        base["family_id"] != graph_v2.FAMILY_ID
        or scan["family_id"] != graph_v2.FAMILY_ID
        or base["topology_scan_id"] != scan["scan_id"]
        or base["topology_region"] is None
        or base["visible_dash_rescues"]
    ):
        raise _error("loan-currency dash base graph binding drifted")
    try:
        replayed = (
            row_axis_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
                joined_pages,
                graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2,
                scan,
                base["topology_region"],
            )
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("loan-currency dash base row axis cannot replay") from exc
    if not same_typed_json_v1(base, replayed):
        raise _error("loan-currency dash base row axis differs from joined evidence")
    return base, scan, joined_pages


def _cell_id(
    *,
    packet_id: str,
    base_row_axis_id: str,
    role: str,
    page_sequence: int,
    column_ordinal: int,
    label_match_sha256: str,
    region_id: str,
) -> str:
    material = {
        "base_row_axis_id": base_row_axis_id,
        "column_ordinal": column_ordinal,
        "label_match_sha256": label_match_sha256,
        "packet_id": packet_id,
        "page_sequence": page_sequence,
        "region_id": region_id,
        "role": role,
    }
    return "lcdashv1:cell:" + canonical_json_sha256_v1(material)


def _bounded_high_fill_candidate(value: Mapping[str, Any]) -> bool:
    """Retain one narrow dash-like metric gap as a candidate, never zero."""

    metrics = value.get("glyph_metrics")
    return (
        type(metrics) is dict
        and metrics.get("component_count") == 1
        and type(metrics.get("component_aspect_ratio")) is float
        and 1.25 <= metrics["component_aspect_ratio"] < 1.8
        and type(metrics.get("component_height_ratio")) is float
        and 0.15 <= metrics["component_height_ratio"] <= 0.30
        and type(metrics.get("component_width_ratio")) is float
        and 0.10 <= metrics["component_width_ratio"] <= 0.30
        and type(metrics.get("ink_fill_ratio")) is float
        and metrics["ink_fill_ratio"] >= 0.60
        and type(metrics.get("horizontal_center_displacement_ratio")) is float
        and metrics["horizontal_center_displacement_ratio"] <= 0.05
        and type(metrics.get("vertical_center_displacement_ratio")) is float
        and metrics["vertical_center_displacement_ratio"] <= 0.05
    )


def _column_context_binding(base: Mapping[str, Any], pages: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        context = column_context_v1._build_accounting_family_column_context_from_authenticated_row_axis_v1(
            base,
            pages,
            graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2,
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=["MONEY", "MONEY"],
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("loan-currency dash period/unit context cannot replay") from exc
    if (
        context["status"] != "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
        or len(context["period_axis"]) != 2
        or len(context["unit_axis"]) != 2
    ):
        raise _error("loan-currency dash needs two resolved period/unit money lanes")
    return {
        "column_context_id": context["column_context_id"],
        "period_axis": canonical_clone_v1(context["period_axis"]),
        "row_axis_id": context["row_axis_id"],
        "status": context["status"],
        "unit_axis": canonical_clone_v1(context["unit_axis"]),
    }


def _build_with_transient_regions(
    base_row_axis: Any,
    topology_scan: Any,
    joined_pages: Any,
    render_snapshots: Any,
    document_packet: Any,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    packet = _document_packet(document_packet)
    base, scan, pages = _base_inputs(base_row_axis, topology_scan, joined_pages)
    context_binding = _column_context_binding(base, pages)
    renders, render_bindings = _render_snapshots(
        render_snapshots, document_ordinal=packet["document_ordinal"]
    )
    try:
        rescue_inputs = sweep_v1._visible_dash_rescue_inputs(
            joined_pages=pages,
            row_axis=base,
            render_snapshots=renders,
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("loan-currency missing-lane pixel proposals drifted") from exc
    if not rescue_inputs:
        raise _error("loan-currency base row axis has no pixel-rescuable missing lane")
    used_pages = {item["page_sequence"] for item in rescue_inputs}
    if used_pages != {item["physical_page"] for item in render_bindings}:
        raise _error("loan-currency dash renders are not the exact missing-lane pages")
    try:
        completed = (
            row_axis_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
                pages,
                graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2,
                scan,
                base["topology_region"],
                visible_dash_rescues=rescue_inputs,
            )
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("loan-currency pixel overlay cannot rebuild the row axis") from exc
    input_by_region = {item["region"]["region_id"]: item for item in rescue_inputs}
    if len(input_by_region) != len(rescue_inputs):
        raise _error("loan-currency dash region identity repeats")
    # A partial printed structural parent may be excluded from the generic
    # completed role axis once its children become complete.  The immutable
    # base axis still owns that printed source row, so bind the crop to it.
    rows_by_key = {(row["role"], row["label_match"]["page_sequence"]): row for row in base["rows"]}
    period_by_lane = {
        item["column_ordinal"]: item["resolved_period"] for item in context_binding["period_axis"]
    }
    rescue_cells = []
    all_direct_dashes = True
    all_direct_or_bounded_candidates = True
    for projection in completed["visible_dash_rescues"]:
        key = (projection["role"], projection["page_sequence"])
        row = rows_by_key.get(key)
        transient = input_by_region.get(projection["region_id"])
        if row is None or transient is None:
            raise _error("loan-currency dash projection lost its role/region binding")
        label_sha = canonical_json_sha256_v1(row["label_match"])
        direct = projection["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
        bounded_candidate = not direct and _bounded_high_fill_candidate(projection["dash_evidence"])
        admission_class = (
            "DIRECT_VISIBLE_HORIZONTAL_DASH"
            if direct
            else "BOUNDED_CENTERED_HIGH_FILL_HORIZONTAL_MARK_CANDIDATE"
            if bounded_candidate
            else "UNRESOLVED_PIXEL_GLYPH"
        )
        injected_sample_id = projection["region_id"] if direct else None
        all_direct_dashes = all_direct_dashes and direct
        all_direct_or_bounded_candidates = all_direct_or_bounded_candidates and (
            direct or bounded_candidate
        )
        source_population_role = row["label_match"].get("matched_within_role")
        if projection["role"] == "DEFERRED_LC_PRE_2024_GROUP":
            source_population_role = projection["role"]
        population_row = rows_by_key.get((source_population_role, projection["page_sequence"]))
        region = transient["region"]
        rescue_cells.append(
            {
                "admission_class": admission_class,
                "cell_id": _cell_id(
                    packet_id=packet["packet_id"],
                    base_row_axis_id=base["row_axis_id"],
                    role=projection["role"],
                    page_sequence=projection["page_sequence"],
                    column_ordinal=projection["column_ordinal"],
                    label_match_sha256=label_sha,
                    region_id=projection["region_id"],
                ),
                "classification": projection["classification"],
                "column_ordinal": projection["column_ordinal"],
                "dash_evidence": canonical_clone_v1(projection["dash_evidence"]),
                "injected_value_sample_id": injected_sample_id,
                "label_match_sha256": label_sha,
                "page_sequence": projection["page_sequence"],
                "proposed_raw_pixel_bbox": canonical_clone_v1(
                    projection["proposed_raw_pixel_bbox"]
                ),
                "recognition_raw_pixel_bbox": canonical_clone_v1(
                    projection["recognition_raw_pixel_bbox"]
                ),
                "region_id": projection["region_id"],
                "region_png_ref": canonical_clone_v1(region["region_png_ref"]),
                "render_id": region["render_id"],
                "resolved_period": period_by_lane[projection["column_ordinal"]],
                "role": projection["role"],
                "source_population_role": source_population_role,
                "source_population_surface": (
                    population_row["label_match"]["surface"] if population_row is not None else None
                ),
            }
        )
    accepted = (
        all_direct_dashes
        and completed["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
        and len(rescue_cells) == len(rescue_inputs)
    )
    status = (
        _ACCEPTED_STATUS
        if accepted
        else _BOUNDED_CANDIDATE_STATUS
        if all_direct_or_bounded_candidates and len(rescue_cells) == len(rescue_inputs)
        else _UNRESOLVED_STATUS
    )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "base_row_axis_id": base["row_axis_id"],
        "claim_boundary": CLAIM_BOUNDARY,
        "column_context_binding": context_binding,
        "completed_row_axis": canonical_clone_v1(completed),
        "document_binding": _document_binding(packet),
        "family_id": graph_v2.FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "render_bindings": render_bindings,
        "rescue_cells": rescue_cells,
        "status": status,
        "topology_scan_id": scan["scan_id"],
    }
    result = {
        **material,
        "evidence_id": "lcdashv1:evidence:" + canonical_json_sha256_v1(material),
    }
    return _validate(result), rescue_inputs


def _validate(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["family_id"] != graph_v2.FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or value["status"] not in {_ACCEPTED_STATUS, _BOUNDED_CANDIDATE_STATUS, _UNRESOLVED_STATUS}
        or type(value["base_row_axis_id"]) is not str
        or not value["base_row_axis_id"].startswith("afrav1:axis:")
        or type(value["topology_scan_id"]) is not str
        or not value["topology_scan_id"].startswith("aftv1:scan:")
        or type(value["rescue_cells"]) is not list
        or not value["rescue_cells"]
        or type(value["render_bindings"]) is not list
        or not value["render_bindings"]
    ):
        raise _error("loan-currency dash evidence result shape drifted")
    try:
        completed = row_axis_v1._validate_result(value["completed_row_axis"])
    except (ValueError, RuntimeError) as exc:
        raise _error("loan-currency completed row axis identity drifted") from exc
    if (
        completed["family_id"] != graph_v2.FAMILY_ID
        or completed["topology_scan_id"] != value["topology_scan_id"]
    ):
        raise _error("loan-currency completed row axis family/topology drifted")
    context = value["column_context_binding"]
    if (
        type(context) is not dict
        or set(context) != _COLUMN_CONTEXT_BINDING_FIELDS
        or context["row_axis_id"] != value["base_row_axis_id"]
        or context["status"] != "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
        or type(context["period_axis"]) is not list
        or len(context["period_axis"]) != 2
        or type(context["unit_axis"]) is not list
        or len(context["unit_axis"]) != 2
    ):
        raise _error("loan-currency dash column-context binding drifted")
    period_by_lane = {
        item.get("column_ordinal"): item.get("resolved_period")
        for item in context["period_axis"]
        if type(item) is dict
    }
    if set(period_by_lane) != {0, 1} or any(
        type(period) is not str or not period for period in period_by_lane.values()
    ):
        raise _error("loan-currency dash resolved-period lane axis drifted")
    binding = value["document_binding"]
    if (
        type(binding) is not dict
        or set(binding) != _DOCUMENT_BINDING_FIELDS
        or type(binding["document_ordinal"]) is not int
        or binding["document_ordinal"] <= 0
        or any(
            type(binding[field]) is not str or not binding[field]
            for field in ("document_id", "packet_id", "document_evidence_root_sha256")
        )
        or _SHA256.fullmatch(binding["document_evidence_root_sha256"]) is None
    ):
        raise _error("loan-currency dash document binding drifted")
    _strict_ref(binding["source_pdf_ref"], "loan-currency source PDF")
    render_by_id = {}
    for render in value["render_bindings"]:
        if (
            type(render) is not dict
            or set(render) != _RENDER_BINDING_FIELDS
            or any(
                type(render[field]) is not str or not render[field]
                for field in ("archive_id", "index_id", "plan_id", "render_id")
            )
            or type(render["physical_page"]) is not int
            or render["physical_page"] <= 0
            or render["render_id"] in render_by_id
        ):
            raise _error("loan-currency dash render binding drifted")
        _strict_ref(render["render_ref"], "loan-currency render", render=True)
        render_by_id[render["render_id"]] = render
    projection_by_region = {item["region_id"]: item for item in completed["visible_dash_rescues"]}
    if len(projection_by_region) != len(completed["visible_dash_rescues"]):
        raise _error("loan-currency completed dash regions repeat")
    seen_cells = set()
    seen_keys = set()
    all_direct = True
    all_direct_or_bounded = True
    for cell in value["rescue_cells"]:
        if type(cell) is not dict or set(cell) != _CELL_FIELDS:
            raise _error("loan-currency dash cell fields drifted")
        projection = projection_by_region.get(cell["region_id"])
        key = (cell["role"], cell["page_sequence"], cell["column_ordinal"])
        if (
            type(cell["cell_id"]) is not str
            or not cell["cell_id"].startswith("lcdashv1:cell:")
            or cell["cell_id"] in seen_cells
            or key in seen_keys
            or type(cell["page_sequence"]) is not int
            or cell["page_sequence"] <= 0
            or type(cell["column_ordinal"]) is not int
            or cell["column_ordinal"] < 0
            or projection is None
            or cell["render_id"] not in render_by_id
            or render_by_id[cell["render_id"]]["physical_page"] != cell["page_sequence"]
            or projection["role"] != cell["role"]
            or projection["page_sequence"] != cell["page_sequence"]
            or projection["column_ordinal"] != cell["column_ordinal"]
            or projection["classification"] != cell["classification"]
            or projection["proposed_raw_pixel_bbox"] != cell["proposed_raw_pixel_bbox"]
            or projection["recognition_raw_pixel_bbox"] != cell["recognition_raw_pixel_bbox"]
            or not same_typed_json_v1(projection["dash_evidence"], cell["dash_evidence"])
            or type(cell["label_match_sha256"]) is not str
            or _SHA256.fullmatch(cell["label_match_sha256"]) is None
            or cell["resolved_period"] != period_by_lane.get(cell["column_ordinal"])
            or cell["source_population_role"] not in {"DEFERRED_LC_PRE_2024_GROUP", None}
            or (
                cell["source_population_role"] is None
                and cell["source_population_surface"] is not None
            )
            or (
                cell["source_population_role"] is not None
                and (
                    type(cell["source_population_surface"]) is not str
                    or not cell["source_population_surface"]
                )
            )
        ):
            raise _error("loan-currency dash cell/projection binding drifted")
        _strict_blob_ref(cell["region_png_ref"], "loan-currency dash crop")
        expected_id = _cell_id(
            packet_id=binding["packet_id"],
            base_row_axis_id=value["base_row_axis_id"],
            role=cell["role"],
            page_sequence=cell["page_sequence"],
            column_ordinal=cell["column_ordinal"],
            label_match_sha256=cell["label_match_sha256"],
            region_id=cell["region_id"],
        )
        if cell["cell_id"] != expected_id:
            raise _error("loan-currency dash cell identity drifted")
        injected = cell["injected_value_sample_id"] == cell["region_id"]
        direct = cell["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH" and injected
        bounded_candidate = (
            not injected
            and _bounded_high_fill_candidate(cell["dash_evidence"])
            and cell["admission_class"] == "BOUNDED_CENTERED_HIGH_FILL_HORIZONTAL_MARK_CANDIDATE"
        )
        if direct != (cell["admission_class"] == "DIRECT_VISIBLE_HORIZONTAL_DASH"):
            raise _error("loan-currency dash admission class drifted")
        if (
            not direct
            and not bounded_candidate
            and cell["admission_class"] != ("UNRESOLVED_PIXEL_GLYPH")
        ):
            raise _error("loan-currency dash unresolved admission class drifted")
        all_direct = all_direct and direct
        all_direct_or_bounded = all_direct_or_bounded and (direct or bounded_candidate)
        if injected != (cell["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"):
            raise _error("loan-currency dash injected-value binding drifted")
        seen_cells.add(cell["cell_id"])
        seen_keys.add(key)
    if set(projection_by_region) != {cell["region_id"] for cell in value["rescue_cells"]}:
        raise _error("loan-currency dash cell axis differs from row-axis projections")
    expected_status = (
        _ACCEPTED_STATUS
        if all_direct and completed["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
        else _BOUNDED_CANDIDATE_STATUS
        if all_direct_or_bounded
        else _UNRESOLVED_STATUS
    )
    if value["status"] != expected_status:
        raise _error("loan-currency dash terminal status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("evidence_id")
    if identity != "lcdashv1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("loan-currency dash evidence identity drifted")
    return canonical_clone_v1(value)


def build_loan_currency_visible_dash_evidence_v1(
    base_row_axis: Any,
    topology_scan: Any,
    joined_pages: Any,
    render_snapshots: Any,
    document_packet: Any,
) -> dict[str, Any]:
    """Build JSON-safe evidence from exact authenticated page pixels."""

    result, _transient = _build_with_transient_regions(
        base_row_axis,
        topology_scan,
        joined_pages,
        render_snapshots,
        document_packet,
    )
    return result


def validate_loan_currency_visible_dash_evidence_v1(value: Any) -> dict[str, Any]:
    """Validate shape and content IDs only; this does not replay pixels."""

    return _validate(value)


def validate_loan_currency_visible_dash_evidence_replay_v1(
    value: Any,
    base_row_axis: Any,
    topology_scan: Any,
    joined_pages: Any,
    render_snapshots: Any,
    document_packet: Any,
) -> dict[str, Any]:
    """Re-crop the authenticated page and require exact evidence replay."""

    persisted = _validate(value)
    rebuilt, _transient = _build_with_transient_regions(
        base_row_axis,
        topology_scan,
        joined_pages,
        render_snapshots,
        document_packet,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-currency dash evidence does not replay exact source pixels")
    return persisted


def build_loan_currency_bounded_dash_peer_bindings_v1(
    values: Sequence[Any],
) -> tuple[dict[str, Any], ...]:
    """Pair each bounded candidate with one exact structural/period peer.

    This function binds references only.  Callers must first replay every
    overlay against its authenticated page pixels and must pass candidate and
    peer crop bytes to the numeric reconciler.  The paired pixel evidence
    independently selects zero; accounting can only corroborate or veto the
    terminal numeric result afterward.
    """

    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise _error("loan-currency dash peer overlays must be one sequence")
    overlays = [_validate(value) for value in values]
    cells = [(overlay, cell) for overlay in overlays for cell in overlay["rescue_cells"]]
    direct = [
        (overlay, cell)
        for overlay, cell in cells
        if cell["admission_class"] == "DIRECT_VISIBLE_HORIZONTAL_DASH"
    ]
    candidates = [
        (overlay, cell)
        for overlay, cell in cells
        if cell["admission_class"] == "BOUNDED_CENTERED_HIGH_FILL_HORIZONTAL_MARK_CANDIDATE"
    ]
    result = []
    for overlay, candidate in candidates:
        if type(candidate["column_ordinal"]) is not int:
            raise _error("bounded loan-currency dash pair lane type drifted")
        peers = [
            (peer_overlay, peer)
            for peer_overlay, peer in direct
            if peer["role"] == candidate["role"]
            and peer["source_population_role"] == candidate["source_population_role"]
            and peer["column_ordinal"] == candidate["column_ordinal"]
            and peer["resolved_period"] == candidate["resolved_period"]
            and peer["region_id"] != candidate["region_id"]
            and peer_overlay["document_binding"]["packet_id"]
            != overlay["document_binding"]["packet_id"]
        ]
        if len(peers) != 1:
            raise _error("bounded loan-currency dash candidate lacks one unique direct peer")
        peer_overlay, peer = peers[0]
        material = {
            "candidate_admission_class": candidate["admission_class"],
            "candidate_cell_id": candidate["cell_id"],
            "candidate_evidence_id": candidate["dash_evidence"]["evidence_id"],
            "candidate_overlay_evidence_id": overlay["evidence_id"],
            "candidate_packet_id": overlay["document_binding"]["packet_id"],
            "candidate_raw_classification": candidate["classification"],
            "candidate_region_id": candidate["region_id"],
            "column_ordinal": candidate["column_ordinal"],
            "peer_cell_id": peer["cell_id"],
            "peer_evidence_id": peer["dash_evidence"]["evidence_id"],
            "peer_overlay_evidence_id": peer_overlay["evidence_id"],
            "peer_packet_id": peer_overlay["document_binding"]["packet_id"],
            "peer_raw_classification": peer["classification"],
            "peer_region_id": peer["region_id"],
            "resolved_period": candidate["resolved_period"],
            "role": candidate["role"],
            "source_population_role": candidate["source_population_role"],
        }
        result.append(
            {
                **material,
                "pair_binding_id": "lcdashv1:pair:" + canonical_json_sha256_v1(material),
            }
        )
    return tuple(sorted(result, key=lambda item: item["candidate_cell_id"]))


def read_loan_currency_dash_cell_replay_material_v1(
    value: Any,
    base_row_axis: Any,
    topology_scan: Any,
    joined_pages: Any,
    render_snapshots: Any,
    document_packet: Any,
) -> tuple[dict[str, Any], ...]:
    """Return every direct/candidate crop only after exact overlay replay."""

    persisted = _validate(value)
    rebuilt, rescue_inputs = _build_with_transient_regions(
        base_row_axis,
        topology_scan,
        joined_pages,
        render_snapshots,
        document_packet,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-currency dash replay material differs from exact pixels")
    region_by_id = {item["region"]["region_id"]: item["region"] for item in rescue_inputs}
    return tuple(
        {
            "admission_class": cell["admission_class"],
            "cell_id": cell["cell_id"],
            "crop_png_bytes": bytes(region_by_id[cell["region_id"]]["region_png_bytes"]),
            "document_packet_id": persisted["document_binding"]["packet_id"],
            "evidence": canonical_clone_v1(cell["dash_evidence"]),
            "lane_index": cell["column_ordinal"],
            "lane_type": "MONEY",
            "overlay_evidence_id": persisted["evidence_id"],
            "page_sequence": cell["page_sequence"],
            "raw_classification": cell["classification"],
            "region_id": cell["region_id"],
            "resolved_period": cell["resolved_period"],
            "role": cell["role"],
            "source_population_role": cell["source_population_role"],
            "source_population_surface": cell["source_population_surface"],
        }
        for cell in persisted["rescue_cells"]
    )


def read_loan_currency_visible_dash_numeric_bindings_v1(
    value: Any,
    base_row_axis: Any,
    topology_scan: Any,
    joined_pages: Any,
    render_snapshots: Any,
    document_packet: Any,
) -> tuple[dict[str, Any], ...]:
    """Return transient reconciler bindings only after exact pixel replay."""

    persisted = _validate(value)
    material = read_loan_currency_dash_cell_replay_material_v1(
        value,
        base_row_axis,
        topology_scan,
        joined_pages,
        render_snapshots,
        document_packet,
    )
    if persisted["status"] != _ACCEPTED_STATUS:
        raise _error("loan-currency dash numeric binding lacks accepted exact replay")
    return tuple(
        {
            "cell_id": cell["cell_id"],
            "crop_png_bytes": bytes(cell["crop_png_bytes"]),
            "evidence": canonical_clone_v1(cell["evidence"]),
            "lane_index": cell["lane_index"],
            "lane_type": cell["lane_type"],
            "page_sequence": cell["page_sequence"],
            "region_id": cell["region_id"],
            "role": cell["role"],
        }
        for cell in material
    )
