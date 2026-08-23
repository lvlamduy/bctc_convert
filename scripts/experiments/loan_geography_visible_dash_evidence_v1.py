"""Authenticated visible-dash evidence for loan-geography graph holes.

The geography graph owns semantic scope, layout, role, period and missing-cell
geometry.  This module owns none of those decisions.  It binds a canonical
hole manifest to an immutable document packet and exact full-page renders,
crops each proposed cell, and runs the shared shape-only dash classifier.

A detector omission or blank crop never means zero.  Only a directly visible
horizontal dash can expose ``normalized_value == 0``.  A degraded centered
mark remains unresolved in this overlay.  It may be paired explicitly with a
distinct, directly visible structural peer, but that typed pair is built only
from material returned after exact pixel replay and never consults accounting
values, expected values, bank names, filenames, pages, or schema IDs.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1
from bctc_ai.evaluation import family_first_visible_dash_glyph_evidence_v1 as glyph_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FAMILY_ID",
    "FORMAT_VERSION",
    "HOLE_MANIFEST_FORMAT_VERSION",
    "LoanGeographyVisibleDashEvidenceV1Error",
    "build_loan_geography_bounded_dash_peer_binding_v1",
    "build_loan_geography_dash_hole_manifest_v1",
    "build_loan_geography_dash_hole_manifest_from_graph_v1",
    "build_loan_geography_visible_dash_evidence_v1",
    "read_loan_geography_direct_dash_numeric_bindings_v1",
    "read_loan_geography_dash_cell_replay_material_v1",
    "read_loan_geography_numeric_reconciliation_dash_bindings_v1",
    "validate_loan_geography_visible_dash_evidence_replay_v1",
    "validate_loan_geography_visible_dash_evidence_v1",
]


FORMAT_VERSION = "LOAN_GEOGRAPHY_VISIBLE_DASH_EVIDENCE_V1"
HOLE_MANIFEST_FORMAT_VERSION = "LOAN_GEOGRAPHY_DASH_HOLE_MANIFEST_V1"
PAIR_FORMAT_VERSION = "LOAN_GEOGRAPHY_BOUNDED_DASH_PEER_BINDING_V1"
FAMILY_ID = "LOAN_GEOGRAPHIC_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "AUTHENTICATED_GRAPH_HOLE_MANIFEST_DOCUMENT_PACKET_FULL_PAGE_RENDER_ROLE_"
    "PERIOD_LANE_LAYOUT_SEGMENT_CROP_AND_EXACT_PIXEL_DASH_REPLAY_ONLY_NO_BLANK_"
    "ZERO_ACCOUNTING_BACKSOLVE_BANK_PAGE_VALUE_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_can_infer_or_backsolve_zero": False,
    "bank_filename_page_or_expected_value_routing_authority": False,
    "blank_or_detector_omission_means_zero": False,
    "bounded_candidate_alone_means_zero": False,
    "bounded_peer_selection_uses_accounting_values": False,
    "exact_authenticated_crop_replay_required_before_numeric_use": True,
    "graph_owns_role_period_lane_layout_and_geometry": True,
    "mapping_authority": False,
    "schema_authority": False,
    "visible_horizontal_dash_may_normalize_to_zero": True,
}
_MISSING_STATUS = "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_EVIDENCE"
_DIRECT = "DIRECT_VISIBLE_HORIZONTAL_DASH"
_CANDIDATE = "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE_RETAINED"
_UNRESOLVED = "UNRESOLVED_PIXEL_GLYPH"
_ACCEPTED_STATUS = "AUTHENTICATED_VISIBLE_DASH_CELLS_BOUND"
_MIXED_STATUS = "PARTIAL_VISIBLE_DASH_EVIDENCE_RETAINED_WITH_UNRESOLVED_CELLS"
_UNRESOLVED_STATUS = "UNRESOLVED_NO_DIRECT_VISIBLE_DASH_CELL"
_LAYOUTS = {
    "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS",
    "GEOGRAPHY_COLUMNS_ACCOUNTING_FAMILY_ROWS",
}
_ROLES = {"DOMESTIC_TOTAL", "FOREIGN_TOTAL"}
_PERIOD_ROLES = {"CURRENT", "COMPARATIVE"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PIXEL_REGION_ID = re.compile(r"^ffaprv1:region:[0-9a-f]{64}$")

_HOLE_FIELDS = {
    "axis_binding_sha256",
    "coordinate_space",
    "graph_id",
    "graph_cell_id",
    "hole_id",
    "label_binding_sha256",
    "lane_index",
    "lane_type",
    "layout_mode",
    "missing_status",
    "page_sequence",
    "period_key",
    "period_lane_index",
    "period_role",
    "expected_pixel_bbox",
    "resolved_period",
    "role",
    "segment_id",
    "source_geography_ordinal",
}
_MANIFEST_FIELDS = {
    "family_id",
    "format_version",
    "graph_result_id",
    "graph_snapshot_sha256",
    "holes",
    "manifest_id",
    "selection_receipt_id",
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "document_binding",
    "evidence_id",
    "family_id",
    "format_version",
    "graph_binding",
    "hole_manifest",
    "metrics",
    "render_bindings",
    "rescue_cells",
    "status",
}
_GRAPH_BINDING_FIELDS = {
    "graph_result_id",
    "graph_snapshot_sha256",
    "selection_receipt_id",
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
_CELL_FIELDS = _HOLE_FIELDS | {
    "admission_class",
    "cell_evidence_id",
    "classification",
    "dash_evidence",
    "normalized_value",
    "recognition_raw_pixel_bbox",
    "pixel_region_id",
    "region_png_ref",
    "render_id",
}
_METRIC_FIELDS = {
    "bounded_candidate_cell_count",
    "direct_visible_dash_zero_cell_count",
    "requested_hole_count",
    "unresolved_pixel_cell_count",
}
_PAIR_FIELDS = {
    "candidate",
    "claim_boundary",
    "format_version",
    "normalized_value",
    "pair_binding_id",
    "peer",
    "structural_binding",
}


class LoanGeographyVisibleDashEvidenceV1Error(ValueError):
    """The graph hole, packet, render, crop, glyph or replay drifted."""


def _error(message: str) -> LoanGeographyVisibleDashEvidenceV1Error:
    return LoanGeographyVisibleDashEvidenceV1Error(message)


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise _error(f"{label} sha256 drifted")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _bbox(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise _error(f"{label} bbox drifted")
    return list(value)


def _strict_blob_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"sha256", "size_bytes"}
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"{label} reference drifted")
    _sha(value["sha256"], label)
    return canonical_clone_v1(value)


def _strict_source_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"path", "sha256", "size_bytes"}
        or type(value["path"]) is not str
        or not value["path"]
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"{label} reference drifted")
    _sha(value["sha256"], label)
    return canonical_clone_v1(value)


def _strict_render_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"pixel_height", "pixel_width", "sha256", "size_bytes"}
        or type(value["pixel_height"]) is not int
        or value["pixel_height"] <= 0
        or type(value["pixel_width"]) is not int
        or value["pixel_width"] <= 0
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"{label} reference drifted")
    _sha(value["sha256"], label)
    return canonical_clone_v1(value)


def _graph_result(value: Any) -> dict[str, Any]:
    """Validate the common content-addressed graph envelope without routing."""

    if (
        type(value) is not dict
        or value.get("family_id") != FAMILY_ID
        or type(value.get("format_version")) is not str
        or not value["format_version"]
        or type(value.get("result_id")) is not str
        or ":" not in value["result_id"]
    ):
        raise _error("loan-geography graph envelope drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id")
    if result_id.rsplit(":", 1)[-1] != canonical_json_sha256_v1(material):
        raise _error("loan-geography graph identity drifted")
    return canonical_clone_v1(value)


def _graph_hole_bindings(graph: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Project exact graph detector holes without interpreting their geometry."""

    graphs = graph.get("graphs")
    if type(graphs) is not list:
        raise _error("loan-geography graph list drifted")
    result: dict[str, dict[str, Any]] = {}
    for logical in graphs:
        if (
            type(logical) is not dict
            or type(logical.get("graph_id")) is not str
            or not logical["graph_id"]
            or type(logical.get("segments")) is not list
        ):
            raise _error("loan-geography logical graph segments drifted")
        for segment in logical["segments"]:
            if (
                type(segment) is not dict
                or type(segment.get("segment_id")) is not str
                or not segment["segment_id"]
                or segment.get("layout") not in _LAYOUTS
                or type(segment.get("period_key")) is not str
                or not segment["period_key"]
                or type(segment.get("period_lane_index")) is not int
                or segment["period_lane_index"] < 0
                or segment.get("period_role") not in _PERIOD_ROLES
                or type(segment.get("resolved_period")) is not str
                or not segment["resolved_period"]
                or type(segment.get("role_cells")) is not list
                or type(segment.get("geography_axis")) is not dict
                or set(segment["geography_axis"]) != {"domestic", "foreign"}
                or type(segment.get("period_headings")) is not list
                or type(segment.get("unit_headings")) is not list
                or type(segment.get("scope_axis")) is not dict
            ):
                raise _error("loan-geography graph segment dash projection drifted")
            axis_sha = canonical_json_sha256_v1(
                {
                    "period_headings": segment["period_headings"],
                    "scope_axis": segment["scope_axis"],
                    "unit_headings": segment["unit_headings"],
                }
            )
            labels = {
                "DOMESTIC_TOTAL": canonical_json_sha256_v1(segment["geography_axis"]["domestic"]),
                "FOREIGN_TOTAL": canonical_json_sha256_v1(segment["geography_axis"]["foreign"]),
            }
            for cell in segment["role_cells"]:
                if type(cell) is not dict or cell.get("status") != _MISSING_STATUS:
                    continue
                graph_cell_id = cell.get("graph_cell_id")
                role = cell.get("role")
                if (
                    type(graph_cell_id) is not str
                    or not graph_cell_id
                    or graph_cell_id in result
                    or role not in _ROLES
                    or type(cell.get("lane_index")) is not int
                    or cell["lane_index"] < 0
                    or cell["lane_index"] != segment["period_lane_index"]
                    or cell.get("lane_type") != "MONEY"
                    or type(cell.get("page_sequence")) is not int
                    or cell["page_sequence"] <= 0
                    or cell.get("coordinate_space")
                    != "OCR_PAGE_PIXEL_COORDINATES_BOUND_TO_RECEIPT_RENDER"
                    or cell.get("period_role") != segment["period_role"]
                    or cell.get("resolved_period") != segment["resolved_period"]
                    or type(cell.get("source_geography_ordinal")) is not int
                    or cell["source_geography_ordinal"] < 0
                ):
                    raise _error("loan-geography graph detector-hole cell drifted")
                expected_bbox = _bbox(
                    cell.get("expected_pixel_bbox"), "loan-geography graph expected cell"
                )
                result[graph_cell_id] = {
                    "axis_binding_sha256": axis_sha,
                    "coordinate_space": cell["coordinate_space"],
                    "expected_pixel_bbox": expected_bbox,
                    "graph_id": logical["graph_id"],
                    "graph_cell_id": graph_cell_id,
                    "label_binding_sha256": labels[role],
                    "lane_index": cell["lane_index"],
                    "lane_type": "MONEY",
                    "layout_mode": segment["layout"],
                    "missing_status": _MISSING_STATUS,
                    "page_sequence": cell["page_sequence"],
                    "period_key": segment["period_key"],
                    "period_lane_index": segment["period_lane_index"],
                    "period_role": segment["period_role"],
                    "resolved_period": segment["resolved_period"],
                    "role": role,
                    "segment_id": segment["segment_id"],
                    "source_geography_ordinal": cell["source_geography_ordinal"],
                }
    return result


def _hole_id(graph_result_id: str, selection_receipt_id: str, value: Mapping[str, Any]) -> str:
    material = {key: canonical_clone_v1(value[key]) for key in sorted(_HOLE_FIELDS - {"hole_id"})}
    material.update(
        {
            "graph_result_id": graph_result_id,
            "selection_receipt_id": selection_receipt_id,
        }
    )
    return "lgdashv1:hole:" + canonical_json_sha256_v1(material)


def _hole(value: Any, *, graph_result_id: str, selection_receipt_id: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _HOLE_FIELDS:
        raise _error("loan-geography dash hole fields drifted")
    if (
        type(value["axis_binding_sha256"]) is not str
        or type(value["label_binding_sha256"]) is not str
        or type(value["graph_id"]) is not str
        or not value["graph_id"]
        or type(value["graph_cell_id"]) is not str
        or not value["graph_cell_id"]
        or type(value["segment_id"]) is not str
        or not value["segment_id"]
        or value["role"] not in _ROLES
        or value["period_role"] not in _PERIOD_ROLES
        or type(value["period_key"]) is not str
        or not value["period_key"]
        or type(value["period_lane_index"]) is not int
        or value["period_lane_index"] < 0
        or value["period_lane_index"] != value["lane_index"]
        or type(value["resolved_period"]) is not str
        or not value["resolved_period"]
        or value["layout_mode"] not in _LAYOUTS
        or value["coordinate_space"] != "OCR_PAGE_PIXEL_COORDINATES_BOUND_TO_RECEIPT_RENDER"
        or value["lane_type"] != "MONEY"
        or type(value["lane_index"]) is not int
        or value["lane_index"] < 0
        or type(value["source_geography_ordinal"]) is not int
        or value["source_geography_ordinal"] < 0
        or value["missing_status"] != _MISSING_STATUS
    ):
        raise _error("loan-geography dash hole semantic axis drifted")
    _sha(value["axis_binding_sha256"], "loan-geography hole axis binding")
    _sha(value["label_binding_sha256"], "loan-geography hole label binding")
    _positive_int(value["page_sequence"], "loan-geography hole page")
    _bbox(value["expected_pixel_bbox"], "loan-geography expected cell")
    expected = _hole_id(graph_result_id, selection_receipt_id, value)
    if value["hole_id"] != expected:
        raise _error("loan-geography dash hole identity drifted")
    return canonical_clone_v1(value)


def build_loan_geography_dash_hole_manifest_v1(
    graph_result: Any,
    *,
    selection_receipt_id: str,
    holes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Canonicalize graph-emitted detector holes before reading any pixels.

    Input holes omit ``hole_id``; this builder content-addresses every exact
    role/period/page/lane/layout/segment/geometry tuple and the full manifest.
    """

    graph = _graph_result(graph_result)
    if type(selection_receipt_id) is not str or not selection_receipt_id:
        raise _error("loan-geography selection receipt identity drifted")
    evidence_binding = graph.get("evidence_binding")
    if (
        type(evidence_binding) is not dict
        or evidence_binding.get("receipt_id") != selection_receipt_id
    ):
        raise _error("loan-geography selection receipt is not graph-bound")
    if isinstance(holes, (str, bytes, bytearray)) or not isinstance(holes, Sequence) or not holes:
        raise _error("loan-geography dash manifest requires detector holes")
    graph_holes = _graph_hole_bindings(graph)
    complete = []
    for raw in holes:
        if type(raw) is not dict or set(raw) != _HOLE_FIELDS - {"hole_id"}:
            raise _error("loan-geography raw dash hole fields drifted")
        candidate = canonical_clone_v1(raw)
        candidate["hole_id"] = _hole_id(graph["result_id"], selection_receipt_id, candidate)
        complete.append(
            _hole(
                candidate,
                graph_result_id=graph["result_id"],
                selection_receipt_id=selection_receipt_id,
            )
        )
    if {hole["graph_cell_id"] for hole in complete} != set(graph_holes):
        raise _error("loan-geography dash manifest must cover exact graph detector holes")
    for hole in complete:
        expected = graph_holes[hole["graph_cell_id"]]
        if any(
            not same_typed_json_v1(hole[field], expected[field])
            for field in (
                "axis_binding_sha256",
                "coordinate_space",
                "expected_pixel_bbox",
                "graph_id",
                "graph_cell_id",
                "label_binding_sha256",
                "lane_index",
                "lane_type",
                "layout_mode",
                "missing_status",
                "page_sequence",
                "period_key",
                "period_lane_index",
                "period_role",
                "resolved_period",
                "role",
                "segment_id",
                "source_geography_ordinal",
            )
        ):
            raise _error("loan-geography dash manifest differs from graph detector hole")
    keys = [
        (hole["graph_cell_id"], hole["role"], hole["resolved_period"], hole["page_sequence"])
        for hole in complete
    ]
    if len(set(keys)) != len(keys) or len({hole["hole_id"] for hole in complete}) != len(complete):
        raise _error("loan-geography dash manifest repeats a graph cell")
    complete.sort(
        key=lambda item: (
            item["page_sequence"],
            item["segment_id"],
            item["role"],
            item["period_role"],
            item["lane_index"],
        )
    )
    material = {
        "family_id": FAMILY_ID,
        "format_version": HOLE_MANIFEST_FORMAT_VERSION,
        "graph_result_id": graph["result_id"],
        "graph_snapshot_sha256": canonical_json_sha256_v1(graph),
        "holes": complete,
        "selection_receipt_id": selection_receipt_id,
    }
    return {
        **material,
        "manifest_id": "lgdashv1:manifest:" + canonical_json_sha256_v1(material),
    }


def build_loan_geography_dash_hole_manifest_from_graph_v1(
    graph_result: Any,
    *,
    selection_receipt_id: str,
    period_bindings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Project graph geometry and join only externally resolved period semantics.

    The caller cannot restate role, lane, page, layout, segment or bbox.  Those
    fields are copied byte-for-byte from the content-addressed graph.  The
    period resolver supplies one exact role/date binding per detector hole.
    """

    graph = _graph_result(graph_result)
    structural = _graph_hole_bindings(graph)
    if (
        isinstance(period_bindings, (str, bytes, bytearray))
        or not isinstance(period_bindings, Sequence)
        or not period_bindings
    ):
        raise _error("loan-geography dash period bindings must be one sequence")
    by_cell: dict[str, dict[str, Any]] = {}
    for raw in period_bindings:
        if type(raw) is not dict or set(raw) != {
            "graph_cell_id",
            "period_role",
            "resolved_period",
        }:
            raise _error("loan-geography dash period binding fields drifted")
        graph_cell_id = raw["graph_cell_id"]
        if (
            type(graph_cell_id) is not str
            or graph_cell_id in by_cell
            or raw["period_role"] not in _PERIOD_ROLES
            or type(raw["resolved_period"]) is not str
            or not raw["resolved_period"]
        ):
            raise _error("loan-geography dash period binding identity drifted")
        by_cell[graph_cell_id] = canonical_clone_v1(raw)
    if set(by_cell) != set(structural):
        raise _error("loan-geography dash period bindings do not cover exact graph holes")
    holes = [
        {
            **canonical_clone_v1(structural[cell_id]),
            "period_role": by_cell[cell_id]["period_role"],
            "resolved_period": by_cell[cell_id]["resolved_period"],
        }
        for cell_id in sorted(structural)
    ]
    return build_loan_geography_dash_hole_manifest_v1(
        graph,
        selection_receipt_id=selection_receipt_id,
        holes=holes,
    )


def _manifest(value: Any, graph: Mapping[str, Any]) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _MANIFEST_FIELDS
        or value["family_id"] != FAMILY_ID
        or value["format_version"] != HOLE_MANIFEST_FORMAT_VERSION
        or value["graph_result_id"] != graph["result_id"]
        or value["graph_snapshot_sha256"] != canonical_json_sha256_v1(graph)
        or type(value["selection_receipt_id"]) is not str
        or not value["selection_receipt_id"]
        or type(value["holes"]) is not list
        or not value["holes"]
    ):
        raise _error("loan-geography dash hole manifest drifted")
    evidence_binding = graph.get("evidence_binding")
    if (
        type(evidence_binding) is not dict
        or evidence_binding.get("receipt_id") != value["selection_receipt_id"]
    ):
        raise _error("loan-geography persisted manifest receipt is not graph-bound")
    holes = [
        _hole(
            item,
            graph_result_id=graph["result_id"],
            selection_receipt_id=value["selection_receipt_id"],
        )
        for item in value["holes"]
    ]
    graph_holes = _graph_hole_bindings(graph)
    if {hole["graph_cell_id"] for hole in holes} != set(graph_holes):
        raise _error("loan-geography persisted manifest graph-hole coverage drifted")
    for hole in holes:
        expected = graph_holes[hole["graph_cell_id"]]
        if any(
            not same_typed_json_v1(hole[field], expected[field])
            for field in (
                "axis_binding_sha256",
                "coordinate_space",
                "expected_pixel_bbox",
                "graph_id",
                "graph_cell_id",
                "label_binding_sha256",
                "lane_index",
                "lane_type",
                "layout_mode",
                "missing_status",
                "page_sequence",
                "period_key",
                "period_lane_index",
                "period_role",
                "resolved_period",
                "role",
                "segment_id",
                "source_geography_ordinal",
            )
        ):
            raise _error("loan-geography persisted manifest graph-hole binding drifted")
    if len({item["hole_id"] for item in holes}) != len(holes):
        raise _error("loan-geography dash hole manifest identity repeats")
    material = canonical_clone_v1(value)
    manifest_id = material.pop("manifest_id")
    if manifest_id != "lgdashv1:manifest:" + canonical_json_sha256_v1(material):
        raise _error("loan-geography dash hole manifest identity drifted")
    return canonical_clone_v1(value)


def _document_packet(value: Any) -> dict[str, Any]:
    if type(value) is not dict or type(value.get("document_ordinal")) is not int:
        raise _error("loan-geography dash document packet drifted")
    try:
        return store_v1._packet(value, value["document_ordinal"])
    except (ValueError, RuntimeError) as exc:
        raise _error("loan-geography dash document packet is not self-consistent") from exc


def _document_binding(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
        "document_id": packet["document_id"],
        "document_ordinal": packet["document_ordinal"],
        "packet_id": packet["packet_id"],
        "source_pdf_ref": canonical_clone_v1(packet["source_pdf_ref"]),
    }


def _render_snapshots(
    values: Any, *, document_ordinal: int, required_pages: set[int]
) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    if (
        isinstance(values, (str, bytes, bytearray))
        or not isinstance(values, Sequence)
        or not values
    ):
        raise _error("loan-geography dash needs authenticated page renders")
    snapshots: dict[int, dict[str, Any]] = {}
    bindings = []
    for value in values:
        if type(value) is not dict:
            raise _error("loan-geography page render is not one exact object")
        try:
            record, _payload = region_v1._validated_render_snapshot(value)
        except (ValueError, RuntimeError) as exc:
            raise _error("loan-geography page render does not authenticate") from exc
        page = record["physical_page"]
        if record["document_ordinal"] != document_ordinal or page in snapshots:
            raise _error("loan-geography dash render document/page binding drifted")
        snapshots[page] = dict(value)
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
    if set(snapshots) != required_pages:
        raise _error("loan-geography dash renders are not the exact hole pages")
    return snapshots, sorted(bindings, key=lambda item: item["physical_page"])


def _cell_evidence_id(packet_id: str, graph_result_id: str, value: Mapping[str, Any]) -> str:
    material = {
        "graph_result_id": graph_result_id,
        "hole_id": value["hole_id"],
        "packet_id": packet_id,
        "pixel_region_id": value["pixel_region_id"],
    }
    return "lgdashv1:cell:" + canonical_json_sha256_v1(material)


def _build_with_transient_regions(
    graph_result: Any,
    hole_manifest: Any,
    render_snapshots: Any,
    document_packet: Any,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    graph = _graph_result(graph_result)
    manifest = _manifest(hole_manifest, graph)
    packet = _document_packet(document_packet)
    evidence_binding = graph.get("evidence_binding")
    if (
        type(evidence_binding) is not dict
        or evidence_binding.get("document_id") != packet["document_id"]
    ):
        raise _error("loan-geography graph and document packet identities differ")
    required_pages = {hole["page_sequence"] for hole in manifest["holes"]}
    if max(required_pages) > packet["page_count"]:
        raise _error("loan-geography dash hole page exceeds document packet")
    renders, render_bindings = _render_snapshots(
        render_snapshots,
        document_ordinal=packet["document_ordinal"],
        required_pages=required_pages,
    )
    rescue_cells = []
    crops: dict[str, bytes] = {}
    for hole in manifest["holes"]:
        try:
            region = region_v1._crop_authenticated_family_first_page_render_snapshot_v1(
                renders[hole["page_sequence"]],
                raw_pixel_bbox=hole["expected_pixel_bbox"],
            )
            dash = glyph_v1.build_family_first_visible_dash_glyph_evidence_v1(
                crop_png_bytes=region["region_png_bytes"]
            )
        except (ValueError, RuntimeError) as exc:
            raise _error("loan-geography dash crop/glyph classification failed") from exc
        if dash["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH":
            admission = _DIRECT
            normalized_value: int | None = 0
        elif dash["classification"] == "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE":
            admission = _CANDIDATE
            normalized_value = None
        else:
            admission = _UNRESOLVED
            normalized_value = None
        cell = {
            **canonical_clone_v1(hole),
            "admission_class": admission,
            "classification": dash["classification"],
            "dash_evidence": canonical_clone_v1(dash),
            "normalized_value": normalized_value,
            "recognition_raw_pixel_bbox": canonical_clone_v1(region["recognition_raw_pixel_bbox"]),
            "pixel_region_id": region["region_id"],
            "region_png_ref": canonical_clone_v1(region["region_png_ref"]),
            "render_id": region["render_id"],
        }
        cell["cell_evidence_id"] = _cell_evidence_id(packet["packet_id"], graph["result_id"], cell)
        rescue_cells.append(cell)
        crops[region["region_id"]] = bytes(region["region_png_bytes"])
    direct_count = sum(cell["admission_class"] == _DIRECT for cell in rescue_cells)
    candidate_count = sum(cell["admission_class"] == _CANDIDATE for cell in rescue_cells)
    unresolved_count = len(rescue_cells) - direct_count - candidate_count
    status = (
        _ACCEPTED_STATUS
        if direct_count == len(rescue_cells)
        else _MIXED_STATUS
        if direct_count
        else _UNRESOLVED_STATUS
    )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "document_binding": _document_binding(packet),
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "graph_binding": {
            "graph_result_id": graph["result_id"],
            "graph_snapshot_sha256": canonical_json_sha256_v1(graph),
            "selection_receipt_id": manifest["selection_receipt_id"],
        },
        "hole_manifest": canonical_clone_v1(manifest),
        "metrics": {
            "bounded_candidate_cell_count": candidate_count,
            "direct_visible_dash_zero_cell_count": direct_count,
            "requested_hole_count": len(rescue_cells),
            "unresolved_pixel_cell_count": unresolved_count,
        },
        "render_bindings": render_bindings,
        "rescue_cells": rescue_cells,
        "status": status,
    }
    result = {
        **material,
        "evidence_id": "lgdashv1:evidence:" + canonical_json_sha256_v1(material),
    }
    return _validate(result), crops


def _validate(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or value["status"] not in {_ACCEPTED_STATUS, _MIXED_STATUS, _UNRESOLVED_STATUS}
        or type(value["rescue_cells"]) is not list
        or not value["rescue_cells"]
        or type(value["render_bindings"]) is not list
        or not value["render_bindings"]
        or type(value["metrics"]) is not dict
        or set(value["metrics"]) != _METRIC_FIELDS
    ):
        raise _error("loan-geography dash evidence result shape drifted")
    graph_binding = value["graph_binding"]
    if (
        type(graph_binding) is not dict
        or set(graph_binding) != _GRAPH_BINDING_FIELDS
        or any(
            type(graph_binding[field]) is not str or not graph_binding[field]
            for field in graph_binding
        )
    ):
        raise _error("loan-geography dash graph binding drifted")
    _sha(graph_binding["graph_snapshot_sha256"], "loan-geography graph snapshot")
    manifest = value["hole_manifest"]
    if (
        type(manifest) is not dict
        or set(manifest) != _MANIFEST_FIELDS
        or manifest["manifest_id"] is None
        or manifest["graph_result_id"] != graph_binding["graph_result_id"]
        or manifest["graph_snapshot_sha256"] != graph_binding["graph_snapshot_sha256"]
        or manifest["selection_receipt_id"] != graph_binding["selection_receipt_id"]
    ):
        raise _error("loan-geography embedded hole manifest binding drifted")
    # Validate manifest hashes without needing the full graph object again.
    for hole in manifest["holes"]:
        _hole(
            hole,
            graph_result_id=graph_binding["graph_result_id"],
            selection_receipt_id=graph_binding["selection_receipt_id"],
        )
    manifest_material = canonical_clone_v1(manifest)
    manifest_id = manifest_material.pop("manifest_id")
    if manifest_id != "lgdashv1:manifest:" + canonical_json_sha256_v1(manifest_material):
        raise _error("loan-geography embedded manifest identity drifted")
    binding = value["document_binding"]
    if (
        type(binding) is not dict
        or set(binding) != _DOCUMENT_BINDING_FIELDS
        or type(binding["document_id"]) is not str
        or not binding["document_id"]
        or type(binding["packet_id"]) is not str
        or not binding["packet_id"]
    ):
        raise _error("loan-geography dash document binding drifted")
    _positive_int(binding["document_ordinal"], "loan-geography document ordinal")
    _sha(binding["document_evidence_root_sha256"], "loan-geography document root")
    _strict_source_ref(binding["source_pdf_ref"], "loan-geography source PDF")
    renders = {}
    for render in value["render_bindings"]:
        if (
            type(render) is not dict
            or set(render) != _RENDER_BINDING_FIELDS
            or any(
                type(render[field]) is not str or not render[field]
                for field in ("archive_id", "index_id", "plan_id", "render_id")
            )
        ):
            raise _error("loan-geography dash render binding drifted")
        page = _positive_int(render["physical_page"], "loan-geography render page")
        if page in renders:
            raise _error("loan-geography dash render page repeats")
        _strict_render_ref(render["render_ref"], "loan-geography render")
        renders[page] = render
    holes = {hole["hole_id"]: hole for hole in manifest["holes"]}
    if len(holes) != len(manifest["holes"]):
        raise _error("loan-geography dash hole identity repeats")
    seen_cells = set()
    direct_count = candidate_count = unresolved_count = 0
    for cell in value["rescue_cells"]:
        if type(cell) is not dict or set(cell) != _CELL_FIELDS:
            raise _error("loan-geography dash rescue cell fields drifted")
        hole = holes.get(cell["hole_id"])
        if hole is None or any(
            not same_typed_json_v1(cell[field], hole[field]) for field in _HOLE_FIELDS
        ):
            raise _error("loan-geography dash rescue cell/hole binding drifted")
        if cell["cell_evidence_id"] in seen_cells:
            raise _error("loan-geography dash cell identity repeats")
        render = renders.get(cell["page_sequence"])
        if render is None or render["render_id"] != cell["render_id"]:
            raise _error("loan-geography dash cell/render page binding drifted")
        _bbox(cell["recognition_raw_pixel_bbox"], "loan-geography recognition crop")
        _strict_blob_ref(cell["region_png_ref"], "loan-geography dash crop")
        if (
            type(cell["pixel_region_id"]) is not str
            or _PIXEL_REGION_ID.fullmatch(cell["pixel_region_id"]) is None
            or cell["pixel_region_id"] == cell["graph_id"]
        ):
            raise _error("loan-geography pixel/logical region identities drifted")
        try:
            dash = glyph_v1._validate(cell["dash_evidence"])
        except (ValueError, RuntimeError) as exc:
            raise _error("loan-geography dash glyph evidence drifted") from exc
        if (
            dash["crop_ref"]["sha256"] != cell["region_png_ref"]["sha256"]
            or dash["crop_ref"]["size_bytes"] != cell["region_png_ref"]["size_bytes"]
            or dash["classification"] != cell["classification"]
        ):
            raise _error("loan-geography dash crop/classification binding drifted")
        if cell["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH":
            expected_admission, expected_value = _DIRECT, 0
            direct_count += 1
        elif cell["classification"] == "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE":
            expected_admission, expected_value = _CANDIDATE, None
            candidate_count += 1
        else:
            expected_admission, expected_value = _UNRESOLVED, None
            unresolved_count += 1
        if (
            cell["admission_class"] != expected_admission
            or cell["normalized_value"] != expected_value
        ):
            raise _error("loan-geography dash admission/value drifted")
        expected_cell_id = _cell_evidence_id(
            binding["packet_id"], graph_binding["graph_result_id"], cell
        )
        if cell["cell_evidence_id"] != expected_cell_id:
            raise _error("loan-geography dash cell evidence identity drifted")
        seen_cells.add(cell["cell_evidence_id"])
    if set(holes) != {cell["hole_id"] for cell in value["rescue_cells"]}:
        raise _error("loan-geography dash rescue cells do not cover exact manifest")
    expected_metrics = {
        "bounded_candidate_cell_count": candidate_count,
        "direct_visible_dash_zero_cell_count": direct_count,
        "requested_hole_count": len(value["rescue_cells"]),
        "unresolved_pixel_cell_count": unresolved_count,
    }
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("loan-geography dash metrics drifted")
    expected_status = (
        _ACCEPTED_STATUS
        if direct_count == len(value["rescue_cells"])
        else _MIXED_STATUS
        if direct_count
        else _UNRESOLVED_STATUS
    )
    if value["status"] != expected_status:
        raise _error("loan-geography dash terminal status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("evidence_id")
    if identity != "lgdashv1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("loan-geography dash evidence identity drifted")
    return canonical_clone_v1(value)


def build_loan_geography_visible_dash_evidence_v1(
    graph_result: Any,
    hole_manifest: Any,
    render_snapshots: Any,
    document_packet: Any,
) -> dict[str, Any]:
    """Build JSON-safe evidence from graph holes and authenticated page pixels."""

    result, _crops = _build_with_transient_regions(
        graph_result, hole_manifest, render_snapshots, document_packet
    )
    return result


def validate_loan_geography_visible_dash_evidence_v1(value: Any) -> dict[str, Any]:
    """Validate shape and content identities; this alone does not replay pixels."""

    return _validate(value)


def validate_loan_geography_visible_dash_evidence_replay_v1(
    value: Any,
    graph_result: Any,
    hole_manifest: Any,
    render_snapshots: Any,
    document_packet: Any,
) -> dict[str, Any]:
    """Re-crop authenticated pages and require exact typed evidence replay."""

    persisted = _validate(value)
    rebuilt, _crops = _build_with_transient_regions(
        graph_result, hole_manifest, render_snapshots, document_packet
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-geography dash evidence does not replay exact source pixels")
    return persisted


def read_loan_geography_dash_cell_replay_material_v1(
    value: Any,
    graph_result: Any,
    hole_manifest: Any,
    render_snapshots: Any,
    document_packet: Any,
) -> tuple[dict[str, Any], ...]:
    """Return raw direct/candidate/unresolved crops only after exact replay."""

    persisted = _validate(value)
    rebuilt, crops = _build_with_transient_regions(
        graph_result, hole_manifest, render_snapshots, document_packet
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-geography dash replay material differs from exact pixels")
    return tuple(
        {
            "admission_class": cell["admission_class"],
            "cell_evidence_id": cell["cell_evidence_id"],
            "crop_png_bytes": bytes(crops[cell["pixel_region_id"]]),
            "document_packet_id": persisted["document_binding"]["packet_id"],
            "evidence": canonical_clone_v1(cell["dash_evidence"]),
            "graph_id": cell["graph_id"],
            "graph_cell_id": cell["graph_cell_id"],
            "graph_result_id": persisted["graph_binding"]["graph_result_id"],
            "hole_id": cell["hole_id"],
            "lane_index": cell["lane_index"],
            "lane_type": cell["lane_type"],
            "layout_mode": cell["layout_mode"],
            "normalized_value": cell["normalized_value"],
            "overlay_evidence_id": persisted["evidence_id"],
            "page_sequence": cell["page_sequence"],
            "period_key": cell["period_key"],
            "period_lane_index": cell["period_lane_index"],
            "period_role": cell["period_role"],
            "raw_classification": cell["classification"],
            "pixel_region_id": cell["pixel_region_id"],
            "resolved_period": cell["resolved_period"],
            "role": cell["role"],
            "segment_id": cell["segment_id"],
            "source_geography_ordinal": cell["source_geography_ordinal"],
        }
        for cell in persisted["rescue_cells"]
    )


def read_loan_geography_direct_dash_numeric_bindings_v1(
    value: Any,
    graph_result: Any,
    hole_manifest: Any,
    render_snapshots: Any,
    document_packet: Any,
) -> tuple[dict[str, Any], ...]:
    """Expose only directly visible zero bindings after exact pixel replay."""

    material = read_loan_geography_dash_cell_replay_material_v1(
        value, graph_result, hole_manifest, render_snapshots, document_packet
    )
    return tuple(
        {
            "cell_evidence_id": cell["cell_evidence_id"],
            "crop_png_bytes": bytes(cell["crop_png_bytes"]),
            "evidence": canonical_clone_v1(cell["evidence"]),
            "graph_id": cell["graph_id"],
            "graph_cell_id": cell["graph_cell_id"],
            "graph_result_id": cell["graph_result_id"],
            "lane_index": cell["lane_index"],
            "lane_type": cell["lane_type"],
            "normalized_value": 0,
            "overlay_evidence_id": cell["overlay_evidence_id"],
            "page_sequence": cell["page_sequence"],
            "period_key": cell["period_key"],
            "period_lane_index": cell["period_lane_index"],
            "period_role": cell["period_role"],
            "pixel_region_id": cell["pixel_region_id"],
            "resolved_period": cell["resolved_period"],
            "role": cell["role"],
            "segment_id": cell["segment_id"],
            "source_geography_ordinal": cell["source_geography_ordinal"],
        }
        for cell in material
        if cell["admission_class"] == _DIRECT and cell["normalized_value"] == 0
    )


def read_loan_geography_numeric_reconciliation_dash_bindings_v1(
    value: Any,
    graph_result: Any,
    hole_manifest: Any,
    render_snapshots: Any,
    document_packet: Any,
) -> tuple[dict[str, Any], ...]:
    """Project exact direct bindings into the frozen numeric-reconciler shape."""

    graph = _graph_result(graph_result)
    direct = read_loan_geography_direct_dash_numeric_bindings_v1(
        value, graph_result, hole_manifest, render_snapshots, document_packet
    )
    structural = _graph_hole_bindings(graph)
    for item in direct:
        graph_cell = structural.get(item["graph_cell_id"])
        if graph_cell is None or any(
            not same_typed_json_v1(item[field], graph_cell[field])
            for field in (
                "graph_id",
                "lane_index",
                "lane_type",
                "page_sequence",
                "period_key",
                "period_lane_index",
                "period_role",
                "resolved_period",
                "role",
                "segment_id",
                "source_geography_ordinal",
            )
        ):
            raise _error("loan-geography numeric adapter graph-cell binding drifted")
    return tuple(
        {
            "cell_id": item["graph_cell_id"],
            "crop_png_bytes": bytes(item["crop_png_bytes"]),
            "evidence": canonical_clone_v1(item["evidence"]),
            "lane_index": item["lane_index"],
            "lane_type": item["lane_type"],
            "page_sequence": item["page_sequence"],
            "region_id": item["graph_id"],
            "role": item["role"],
        }
        for item in direct
    )


def _replayed_material(value: Any, label: str) -> dict[str, Any]:
    required = {
        "admission_class",
        "cell_evidence_id",
        "crop_png_bytes",
        "document_packet_id",
        "evidence",
        "graph_id",
        "graph_cell_id",
        "graph_result_id",
        "hole_id",
        "lane_index",
        "lane_type",
        "layout_mode",
        "normalized_value",
        "overlay_evidence_id",
        "page_sequence",
        "period_key",
        "period_lane_index",
        "period_role",
        "raw_classification",
        "pixel_region_id",
        "resolved_period",
        "role",
        "segment_id",
        "source_geography_ordinal",
    }
    if (
        type(value) is not dict
        or set(value) != required
        or type(value["crop_png_bytes"]) is not bytes
    ):
        raise _error(f"{label} replay material drifted")
    try:
        glyph_v1.validate_family_first_visible_dash_glyph_evidence_replay_v1(
            value["evidence"], crop_png_bytes=value["crop_png_bytes"]
        )
    except (ValueError, RuntimeError) as exc:
        raise _error(f"{label} pixel replay drifted") from exc
    if (
        type(value["graph_result_id"]) is not str
        or not value["graph_result_id"]
        or type(value["overlay_evidence_id"]) is not str
        or not value["overlay_evidence_id"].startswith("lgdashv1:evidence:")
        or type(value["pixel_region_id"]) is not str
        or _PIXEL_REGION_ID.fullmatch(value["pixel_region_id"]) is None
        or value["graph_id"] == value["pixel_region_id"]
    ):
        raise _error(f"{label} logical/pixel provenance drifted")
    expected_cell_id = _cell_evidence_id(
        value["document_packet_id"], value["graph_result_id"], value
    )
    if value["cell_evidence_id"] != expected_cell_id:
        raise _error(f"{label} cell provenance identity drifted")
    return canonical_clone_v1({key: item for key, item in value.items() if key != "crop_png_bytes"})


def build_loan_geography_bounded_dash_peer_binding_v1(
    candidate_replay_material: Any,
    direct_peer_replay_material: Any,
) -> dict[str, Any]:
    """Bind one degraded candidate to one explicit direct structural peer.

    Selection is caller-explicit and typed.  Both inputs must originate from
    exact replay accessors.  Matching uses only semantic graph context and
    independent pixels; no accounting value or equation is accepted here.
    """

    candidate = _replayed_material(candidate_replay_material, "candidate")
    peer = _replayed_material(direct_peer_replay_material, "direct peer")
    if (
        candidate["admission_class"] != _CANDIDATE
        or candidate["raw_classification"] != "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE"
        or candidate["normalized_value"] is not None
        or peer["admission_class"] != _DIRECT
        or peer["raw_classification"] != "VISIBLE_HORIZONTAL_DASH_GLYPH"
        or peer["normalized_value"] != 0
        or candidate["document_packet_id"] == peer["document_packet_id"]
    ):
        raise _error("loan-geography bounded dash peer classes drifted")
    context_fields = (
        "role",
        "resolved_period",
        "period_role",
        "lane_type",
        "lane_index",
        "layout_mode",
        "period_lane_index",
        "source_geography_ordinal",
    )
    if any(candidate[field] != peer[field] for field in context_fields):
        raise _error("loan-geography bounded dash peer structural context differs")
    candidate_ref = {
        key: canonical_clone_v1(candidate[key])
        for key in (
            "cell_evidence_id",
            "document_packet_id",
            "graph_cell_id",
            "graph_result_id",
            "hole_id",
            "graph_id",
            "overlay_evidence_id",
            "pixel_region_id",
        )
    }
    peer_ref = {
        key: canonical_clone_v1(peer[key])
        for key in (
            "cell_evidence_id",
            "document_packet_id",
            "graph_cell_id",
            "graph_result_id",
            "hole_id",
            "graph_id",
            "overlay_evidence_id",
            "pixel_region_id",
        )
    }
    structural = {field: canonical_clone_v1(candidate[field]) for field in context_fields}
    material = {
        "candidate": candidate_ref,
        "claim_boundary": (
            "EXACT_REPLAYED_DEGRADED_MARK_AND_DISTINCT_DIRECT_DASH_STRUCTURAL_PEER_"
            "ONLY_NO_ACCOUNTING_EXPECTED_VALUE_BANK_PAGE_OR_SCHEMA_AUTHORITY"
        ),
        "format_version": PAIR_FORMAT_VERSION,
        "normalized_value": 0,
        "peer": peer_ref,
        "structural_binding": structural,
    }
    return {
        **material,
        "pair_binding_id": "lgdashv1:pair:" + canonical_json_sha256_v1(material),
    }
