"""Bind declarative family roles to visible numeric lanes by geometry.

This shared stage starts from complete-document fresh VietOCR labels and the
independent PP-OCRv6 recognition proposal for the same immutable line crops.
It first rebuilds the bank-blind family topology, then binds every observed
child label to body-derived numeric-column ordinals.  It does not infer a
missing cell, choose a reporting period, accept a number, close an equation or
map a schema row.  Those remain later, separately replayed gates.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    assign_value_row_lanes_v1,
    cluster_numeric_rows_v1,
    infer_numeric_column_centers_v1,
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.evaluation.family_first_authenticated_page_region_v1 import (
    _REGION_AUTHORITY,
)
from bctc_ai.evaluation.family_first_authenticated_page_region_v1 import (
    FORMAT_VERSION as REGION_FORMAT_VERSION,
)
from bctc_ai.evaluation.family_first_numeric_cell_evidence_v1 import (
    parse_visible_financial_numeric_token_v1,
)
from bctc_ai.evaluation.family_first_visible_dash_glyph_evidence_v1 import (
    build_family_first_visible_dash_glyph_evidence_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "AccountingFamilyRowAxisV1Error",
    "build_accounting_family_row_axis_v1",
    "validate_accounting_family_row_axis_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_FAMILY_ROW_AXIS_V1"
CLAIM_BOUNDARY = (
    "COMPLETE_DOCUMENT_DECLARATIVE_FAMILY_TOPOLOGY_TO_GEOMETRY_BOUND_VISIBLE_"
    "PPOCRV6_RECOGNITION_LANE_PROPOSAL_ONLY_NO_MISSING_CELL_INFERENCE_PERIOD_"
    "UNIT_NUMERIC_ACCOUNTING_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "accounting_authority": False,
    "bank_file_note_page_period_scope_used_for_matching_or_routing": False,
    "detector_geometry_treated_as_numeric_recognition": False,
    "family_layout_logic_is_declarative": True,
    "mapping_authority": False,
    "missing_cells_synthesized": False,
    "numeric_authority": False,
    "period_or_unit_authority": False,
    "ppocrv6_recognition_used_as_raw_proposal_only": True,
    "raw_record_self_authenticating": False,
    "schema_authority": False,
    "text_similarity_alone_can_accept": False,
    "visible_dash_pixel_evidence_may_complete_missing_lane": True,
    "visible_dash_pixel_evidence_required_for_non_detector_zero": True,
}
_PAGE_FIELDS = {"lines", "page_sequence", "page_width"}
_LINE_FIELDS = {
    "bbox",
    "crop_ref",
    "line_ordinal",
    "numeric_recognition",
    "sample_id",
    "vietocr_text",
}
_RECOGNITION_FIELDS = {"raw_prediction", "reader_score"}
_REF_FIELDS = {"path", "sha256", "size_bytes"}
_RESULT_FIELDS = {
    "claim_boundary",
    "family_id",
    "format_version",
    "metrics",
    "row_axis_id",
    "rows",
    "safety",
    "status",
    "topology_region",
    "topology_scan_id",
    "topology_status",
    "trailing_value_rows",
    "visible_dash_rescues",
}
_SHA = re.compile(r"^[0-9a-f]{64}$")
_REGION_INPUT_FIELDS = {
    "authority",
    "document_ordinal",
    "format_version",
    "index_id",
    "ink_localization_status",
    "physical_page",
    "proposed_raw_pixel_bbox",
    "recognition_raw_pixel_bbox",
    "region_id",
    "region_png_bytes",
    "region_png_ref",
    "render_id",
    "render_ref",
    "state",
    "white_border",
}
_RESCUE_INPUT_FIELDS = {"column_ordinal", "page_sequence", "region", "role"}
_RESCUE_PROJECTION_FIELDS = {
    "classification",
    "column_center",
    "column_ordinal",
    "dash_evidence",
    "page_sequence",
    "proposed_raw_pixel_bbox",
    "recognition_raw_pixel_bbox",
    "region_id",
    "role",
}


class AccountingFamilyRowAxisV1Error(ValueError):
    """The page/line join, topology, geometry or exact replay drifted."""


def _error(message: str) -> AccountingFamilyRowAxisV1Error:
    return AccountingFamilyRowAxisV1Error(message)


def _bbox(value: Any, page_width: int | None) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[2] <= value[0]
        or value[3] <= value[1]
        or (page_width is not None and value[2] > page_width)
    ):
        raise _error("family row-axis bbox drifted")
    return list(value)


def _ref(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _REF_FIELDS
        or type(value["path"]) is not str
        or not value["path"]
        or type(value["sha256"]) is not str
        or _SHA.fullmatch(value["sha256"]) is None
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error("family row-axis crop reference drifted")
    return canonical_clone_v1(value)


def _region_record(value: Any, *, page_sequence: int) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _REGION_INPUT_FIELDS
        or value["format_version"] != REGION_FORMAT_VERSION
        or value["state"] != "AUTHENTICATED_RENDER_CALLER_PROPOSED_REGION_CROP"
        or not same_typed_json_v1(value["authority"], _REGION_AUTHORITY)
        or value["physical_page"] != page_sequence
        or type(value["document_ordinal"]) is not int
        or value["document_ordinal"] <= 0
        or type(value["index_id"]) is not str
        or not value["index_id"]
        or type(value["render_id"]) is not str
        or not value["render_id"]
        or type(value["ink_localization_status"]) is not str
        or not value["ink_localization_status"]
        or type(value["region_png_bytes"]) is not bytes
        or not value["region_png_bytes"].startswith(b"\x89PNG\r\n\x1a\n")
        or type(value["region_png_ref"]) is not dict
        or set(value["region_png_ref"]) != {"sha256", "size_bytes"}
        or type(value["region_png_ref"]["sha256"]) is not str
        or _SHA.fullmatch(value["region_png_ref"]["sha256"]) is None
        or type(value["region_png_ref"]["size_bytes"]) is not int
        or value["region_png_ref"]["size_bytes"] <= 0
        or type(value["white_border"]) is not list
        or value["white_border"] != [12, 8, 12, 8]
    ):
        raise _error("visible-dash region crop contract drifted")
    proposed = _bbox(value["proposed_raw_pixel_bbox"], None)
    recognition = _bbox(value["recognition_raw_pixel_bbox"], None)
    if not (
        proposed[0] <= recognition[0] < recognition[2] <= proposed[2]
        and proposed[1] <= recognition[1] < recognition[3] <= proposed[3]
    ):
        raise _error("visible-dash recognition bbox lies outside its proposed cell")
    payload = value["region_png_bytes"]
    if (
        len(payload) != value["region_png_ref"]["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != value["region_png_ref"]["sha256"]
    ):
        raise _error("visible-dash region bytes differ from their reference")
    material = {
        key: canonical_clone_v1(item)
        for key, item in value.items()
        if key not in {"region_id", "region_png_bytes"}
    }
    if value["region_id"] != "ffaprv1:region:" + canonical_json_sha256_v1(material):
        raise _error("visible-dash region identity drifted")
    return {
        **material,
        "region_id": value["region_id"],
        "region_png_bytes": bytes(payload),
    }


def _pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or not value:
        raise _error("family row axis requires one nonempty complete document")
    pages: list[dict[str, Any]] = []
    sample_ids: set[str] = set()
    for expected_page, raw_page in enumerate(value, 1):
        if type(raw_page) is not dict or set(raw_page) != _PAGE_FIELDS:
            raise _error("family row-axis page fields drifted")
        width = raw_page["page_width"]
        if (
            raw_page["page_sequence"] != expected_page
            or (width is not None and (type(width) is not int or width <= 0))
            or type(raw_page["lines"]) is not list
        ):
            raise _error("family row-axis page identity or width drifted")
        lines = []
        for expected_line, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != _LINE_FIELDS:
                raise _error("family row-axis line fields drifted")
            recognition = raw_line["numeric_recognition"]
            if type(recognition) is not dict or set(recognition) != _RECOGNITION_FIELDS:
                raise _error("family row-axis numeric recognition fields drifted")
            score = recognition["reader_score"]
            if (
                raw_line["line_ordinal"] != expected_line
                or type(raw_line["vietocr_text"]) is not str
                or type(raw_line["sample_id"]) is not str
                or not raw_line["sample_id"]
                or raw_line["sample_id"] in sample_ids
                or type(recognition["raw_prediction"]) is not str
                or type(score) is not float
                or not math.isfinite(score)
                or not 0 <= score <= 1
            ):
                raise _error("family row-axis line identity/text/score drifted")
            sample_ids.add(raw_line["sample_id"])
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"], width),
                    "crop_ref": _ref(raw_line["crop_ref"]),
                    "line_ordinal": expected_line,
                    "numeric_recognition": canonical_clone_v1(recognition),
                    "sample_id": raw_line["sample_id"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
        pages.append({"lines": lines, "page_sequence": expected_page, "page_width": width})
    return pages


def _topology_pages(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "source_line_index": line["line_ordinal"],
                    "source_text": None,
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]


def _is_numeric(line: Mapping[str, Any]) -> bool:
    parsed = parse_visible_financial_numeric_token_v1(line["numeric_recognition"]["raw_prediction"])
    return parsed["classification"] in {"DASH_ZERO", "SIGNED_NUMBER"}


def _region_lines(
    pages: Sequence[Mapping[str, Any]], region: Mapping[str, Any]
) -> dict[int, list[dict[str, Any]]]:
    start = region["cluster_start_document_line_ordinal"]
    stop = region["cluster_end_document_line_ordinal_exclusive"]
    offset = 0
    result: dict[int, list[dict[str, Any]]] = {}
    for page in pages:
        selected = [
            line
            for local_ordinal, line in enumerate(page["lines"])
            if start <= offset + local_ordinal < stop
        ]
        if selected:
            result[page["page_sequence"]] = selected
        offset += len(page["lines"])
    return result


def _value_record(
    page_sequence: int,
    line: Mapping[str, Any],
    *,
    column_center: float,
    column_ordinal: int,
    row_affinity: float | None,
) -> dict[str, Any]:
    recognition = line["numeric_recognition"]
    return {
        "bbox": canonical_clone_v1(line["bbox"]),
        "column_center": float(column_center),
        "column_ordinal": column_ordinal,
        "crop_ref": canonical_clone_v1(line["crop_ref"]),
        "line_ordinal": line["line_ordinal"],
        "page_sequence": page_sequence,
        "parsed_token": parse_visible_financial_numeric_token_v1(recognition["raw_prediction"]),
        "raw_prediction": recognition["raw_prediction"],
        "reader_score": recognition["reader_score"],
        "row_affinity": row_affinity,
        "sample_id": line["sample_id"],
    }


def _rows(pages: Sequence[Mapping[str, Any]], region: Mapping[str, Any]) -> list[dict[str, Any]]:
    by_page = {page["page_sequence"]: page for page in pages}
    region_by_page = _region_lines(pages, region)
    rows = []
    for match in region["child_matches"]:
        page_sequence = match["page_sequence"]
        page = by_page[page_sequence]
        if type(page["page_width"]) is not int:
            raise _error("matched family page requires one authenticated render width")
        local_lines = region_by_page[page_sequence]
        label_boxes = [
            line["bbox"]
            for line in page["lines"]
            if match["source_line_index"] <= line["line_ordinal"] <= match["end_source_line_index"]
        ]
        if not label_boxes:
            raise _error("topology label span retained no row-axis geometry")
        centers = infer_numeric_column_centers_v1(
            local_lines,
            is_numeric=_is_numeric,
            page_width=page["page_width"],
            retain_singleton_columns=True,
        )
        assignments = assign_value_row_lanes_v1(
            local_lines,
            label_boxes=label_boxes,
            is_numeric=_is_numeric,
            page_width=page["page_width"],
            retain_singleton_columns=True,
        )
        values = [
            _value_record(
                page_sequence,
                assignment["line"],
                column_center=assignment["column_center"],
                column_ordinal=assignment["column_ordinal"],
                row_affinity=assignment["row_affinity"],
            )
            for assignment in assignments
        ]
        visible = [item["column_ordinal"] for item in values]
        missing = [ordinal for ordinal in range(len(centers)) if ordinal not in visible]
        rows.append(
            {
                "label_match": canonical_clone_v1(match),
                "missing_column_ordinals": missing,
                "role": match["role"],
                "role_kind": match["role_kind"],
                "status": (
                    "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL"
                    if not values
                    else "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
                    if missing
                    else "VISIBLE_VALUE_LANES_BOUND"
                ),
                "values": values,
            }
        )
    return rows


def _rescue_projection(
    raw: Any,
    *,
    pages: Sequence[Mapping[str, Any]],
    region: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if (
        type(raw) is not dict
        or set(raw) != _RESCUE_INPUT_FIELDS
        or type(raw["role"]) is not str
        or not raw["role"]
        or type(raw["page_sequence"]) is not int
        or raw["page_sequence"] <= 0
        or type(raw["column_ordinal"]) is not int
        or raw["column_ordinal"] < 0
    ):
        raise _error("visible-dash rescue input fields drifted")
    candidates = [
        row
        for row in rows
        if row["role"] == raw["role"]
        and row["label_match"]["page_sequence"] == raw["page_sequence"]
    ]
    if len(candidates) != 1:
        raise _error("visible-dash rescue does not select one observed role row")
    row = candidates[0]
    lane = raw["column_ordinal"]
    if lane not in row["missing_column_ordinals"]:
        raise _error("visible-dash rescue targets no missing body lane")
    by_page = {page["page_sequence"]: page for page in pages}
    page = by_page.get(raw["page_sequence"])
    if page is None or type(page["page_width"]) is not int:
        raise _error("visible-dash rescue page lacks authenticated dimensions")
    region_record = _region_record(raw["region"], page_sequence=raw["page_sequence"])
    render_ref = region_record["render_ref"]
    if (
        type(render_ref) is not dict
        or type(render_ref.get("pixel_height")) is not int
        or render_ref["pixel_height"] <= 0
        or render_ref.get("pixel_width") != page["page_width"]
    ):
        raise _error("visible-dash rescue render dimensions drifted")
    local_lines = _region_lines(pages, region)[raw["page_sequence"]]
    label_match = row["label_match"]
    label_boxes = [
        line["bbox"]
        for line in page["lines"]
        if label_match["source_line_index"]
        <= line["line_ordinal"]
        <= label_match["end_source_line_index"]
    ]
    proposals = propose_missing_value_lane_regions_v1(
        local_lines,
        label_boxes=label_boxes,
        is_numeric=_is_numeric,
        page_width=page["page_width"],
        page_height=render_ref["pixel_height"],
        retain_singleton_columns=True,
    )
    expected = next(
        (proposal for proposal in proposals if proposal["column_ordinal"] == lane), None
    )
    if expected is None:
        raise _error("visible-dash rescue has no body-grid missing-lane proposal")
    if (
        not same_typed_json_v1(region_record["proposed_raw_pixel_bbox"], expected["raw_pixel_bbox"])
        or type(expected["column_center"]) is not float
    ):
        raise _error("visible-dash rescue differs from the body-grid proposal")
    dash = build_family_first_visible_dash_glyph_evidence_v1(
        crop_png_bytes=region_record["region_png_bytes"]
    )
    projection = {
        "classification": dash["classification"],
        "column_center": expected["column_center"],
        "column_ordinal": lane,
        "dash_evidence": dash,
        "page_sequence": raw["page_sequence"],
        "proposed_raw_pixel_bbox": canonical_clone_v1(expected["raw_pixel_bbox"]),
        "recognition_raw_pixel_bbox": canonical_clone_v1(
            region_record["recognition_raw_pixel_bbox"]
        ),
        "region_id": region_record["region_id"],
        "role": raw["role"],
    }
    if dash["classification"] != "VISIBLE_HORIZONTAL_DASH_GLYPH":
        return projection, None
    crop_ref = dash["crop_ref"]
    value = {
        "bbox": canonical_clone_v1(region_record["recognition_raw_pixel_bbox"]),
        "column_center": expected["column_center"],
        "column_ordinal": lane,
        "crop_ref": {
            "path": f"authenticated-render-region/{region_record['region_id']}.png",
            "sha256": crop_ref["sha256"],
            "size_bytes": crop_ref["size_bytes"],
        },
        "line_ordinal": label_match["source_line_index"],
        "page_sequence": raw["page_sequence"],
        "parsed_token": parse_visible_financial_numeric_token_v1("-"),
        "raw_prediction": "-",
        "reader_score": 1.0,
        "row_affinity": None,
        "sample_id": region_record["region_id"],
    }
    return projection, value


def _apply_visible_dash_rescues(
    pages: Sequence[Mapping[str, Any]],
    region: Mapping[str, Any],
    rows: list[dict[str, Any]],
    value: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if type(value) is not tuple:
        raise _error("visible-dash rescues must be one exact tuple")
    completed = canonical_clone_v1(rows)
    projections: list[dict[str, Any]] = []
    keys: set[tuple[str, int, int]] = set()
    for raw in value:
        projection, rescued = _rescue_projection(
            raw,
            pages=pages,
            region=region,
            rows=completed,
        )
        key = (
            projection["role"],
            projection["page_sequence"],
            projection["column_ordinal"],
        )
        if key in keys:
            raise _error("visible-dash rescue body lane repeats")
        keys.add(key)
        projections.append(projection)
        if rescued is None:
            continue
        row = next(
            item
            for item in completed
            if item["role"] == projection["role"]
            and item["label_match"]["page_sequence"] == projection["page_sequence"]
        )
        row["values"].append(rescued)
        row["values"].sort(key=lambda item: item["column_ordinal"])
        row["missing_column_ordinals"].remove(projection["column_ordinal"])
    for row in completed:
        row["status"] = (
            "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL"
            if not row["values"]
            else "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
            if row["missing_column_ordinals"]
            else "VISIBLE_VALUE_LANES_BOUND"
        )
    return completed, projections


def _trailing_value_rows(
    pages: Sequence[Mapping[str, Any]],
    region: Mapping[str, Any],
    role_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not region["child_matches"]:
        return []
    by_page = {page["page_sequence"]: page for page in pages}
    region_by_page = _region_lines(pages, region)
    last_match = max(region["child_matches"], key=lambda item: item["end_document_line_ordinal"])
    first_page = last_match["page_sequence"]
    assigned_sample_ids = {value["sample_id"] for row in role_rows for value in row["values"]}
    result: list[dict[str, Any]] = []
    for page_sequence in sorted(region_by_page):
        if page_sequence < first_page:
            continue
        page = by_page[page_sequence]
        local_lines = region_by_page[page_sequence]
        if not local_lines:
            continue
        geometry_lines = [
            {**line, "source_line_index": line["line_ordinal"]} for line in local_lines
        ]

        def is_unassigned_numeric(line: Mapping[str, Any]) -> bool:
            return line["sample_id"] not in assigned_sample_ids and _is_numeric(line)

        start_index = last_match["end_source_line_index"] if page_sequence == first_page else -1
        stop_index = max(line["source_line_index"] for line in geometry_lines) + 1
        if stop_index <= start_index or not any(
            start_index < line["source_line_index"] < stop_index and is_unassigned_numeric(line)
            for line in geometry_lines
        ):
            continue
        if type(page["page_width"]) is not int:
            raise _error("trailing family page requires one authenticated render width")
        centers = infer_numeric_column_centers_v1(
            geometry_lines,
            is_numeric=_is_numeric,
            page_width=page["page_width"],
            retain_singleton_columns=True,
        )
        if not centers:
            continue

        clusters = cluster_numeric_rows_v1(
            geometry_lines,
            is_numeric=is_unassigned_numeric,
            start_index=start_index,
            stop_index=stop_index,
            page_width=page["page_width"],
        )
        for cluster in clusters:
            by_lane: dict[int, Mapping[str, Any]] = {}
            for line in cluster:
                center = (line["bbox"][0] + line["bbox"][2]) / 2
                lane = min(range(len(centers)), key=lambda ordinal: abs(center - centers[ordinal]))
                if lane in by_lane:
                    by_lane = {}
                    break
                by_lane[lane] = line
            if not by_lane:
                continue
            values = [
                _value_record(
                    page_sequence,
                    by_lane[lane],
                    column_center=centers[lane],
                    column_ordinal=lane,
                    row_affinity=None,
                )
                for lane in sorted(by_lane)
            ]
            missing = [ordinal for ordinal in range(len(centers)) if ordinal not in by_lane]
            result.append(
                {
                    "candidate_ordinal": len(result),
                    "missing_column_ordinals": missing,
                    "page_sequence": page_sequence,
                    "status": (
                        "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
                        if not missing
                        else "PARTIAL_TRAILING_VALUE_ROW_REQUIRES_PIXEL_RESCUE"
                    ),
                    "values": values,
                }
            )
    return result


def _metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "bound_value_count": sum(len(row["values"]) for row in rows),
        "missing_lane_count": sum(len(row["missing_column_ordinals"]) for row in rows),
        "partial_row_count": sum(
            row["status"] == "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE" for row in rows
        ),
        "role_row_count": len(rows),
        "unresolved_empty_row_count": sum(
            row["status"] == "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL" for row in rows
        ),
    }


def _result_metrics(
    rows: Sequence[Mapping[str, Any]],
    trailing: Sequence[Mapping[str, Any]],
    rescues: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    return {
        **_metrics(rows),
        "complete_trailing_value_row_count": sum(
            item["status"] == "COMPLETE_VISIBLE_TRAILING_VALUE_ROW" for item in trailing
        ),
        "partial_trailing_value_row_count": sum(
            item["status"] == "PARTIAL_TRAILING_VALUE_ROW_REQUIRES_PIXEL_RESCUE"
            for item in trailing
        ),
        "trailing_value_row_count": len(trailing),
        "visible_dash_rescue_attempt_count": len(rescues),
        "visible_dash_zero_count": sum(
            item["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH" for item in rescues
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["topology_scan_id"]) is not str
        or not value["topology_scan_id"].startswith("aftv1:scan:")
        or type(value["topology_status"]) is not str
        or (value["topology_region"] is not None and type(value["topology_region"]) is not dict)
        or type(value["rows"]) is not list
        or type(value["trailing_value_rows"]) is not list
        or type(value["visible_dash_rescues"]) is not list
        or not same_typed_json_v1(
            value["metrics"],
            _result_metrics(
                value["rows"], value["trailing_value_rows"], value["visible_dash_rescues"]
            ),
        )
    ):
        raise _error("family row-axis result contract drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("row_axis_id")
    if identity != "afrav1:axis:" + canonical_json_sha256_v1(material):
        raise _error("family row-axis hash identity drifted")
    for rescue in value["visible_dash_rescues"]:
        if (
            type(rescue) is not dict
            or set(rescue) != _RESCUE_PROJECTION_FIELDS
            or rescue["classification"]
            not in {"VISIBLE_HORIZONTAL_DASH_GLYPH", "UNRESOLVED_NOT_ONE_DASH_GLYPH"}
            or type(rescue["column_center"]) is not float
            or type(rescue["column_ordinal"]) is not int
            or rescue["column_ordinal"] < 0
            or type(rescue["page_sequence"]) is not int
            or rescue["page_sequence"] <= 0
            or type(rescue["region_id"]) is not str
            or not rescue["region_id"].startswith("ffaprv1:region:")
            or type(rescue["role"]) is not str
            or not rescue["role"]
        ):
            raise _error("visible-dash rescue projection drifted")
    return canonical_clone_v1(value)


def build_accounting_family_row_axis_v1(
    pages: Any,
    family_topology_spec: Any,
    *,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Rebuild topology and bind its observed child labels to visible lanes."""

    parsed_pages = _pages(pages)
    try:
        topology = topology_v1.build_accounting_family_topology_scan_v1(
            _topology_pages(parsed_pages), family_topology_spec
        )
    except topology_v1.AccountingFamilyTopologyV1Error as exc:
        raise _error("family row-axis topology input drifted") from exc
    base_rows = (
        _rows(parsed_pages, topology["regions"][0])
        if topology["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
        else []
    )
    rows, rescue_projections = (
        _apply_visible_dash_rescues(
            parsed_pages,
            topology["regions"][0],
            base_rows,
            visible_dash_rescues,
        )
        if topology["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
        else (base_rows, [])
    )
    if topology["status"] != "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL" and visible_dash_rescues != ():
        raise _error("visible-dash rescue cannot bypass unresolved topology")
    trailing = (
        _trailing_value_rows(parsed_pages, topology["regions"][0], rows)
        if topology["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
        else []
    )
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": topology["family_id"],
        "format_version": FORMAT_VERSION,
        "metrics": _result_metrics(rows, trailing, rescue_projections),
        "rows": rows,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "UNRESOLVED_TOPOLOGY"
            if not rows
            else "ROW_AXIS_PROPOSAL_WITH_UNRESOLVED_CELLS"
            if any(row["status"] != "VISIBLE_VALUE_LANES_BOUND" for row in rows)
            else "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
        ),
        "topology_region": (
            canonical_clone_v1(topology["regions"][0])
            if topology["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
            else None
        ),
        "topology_scan_id": topology["scan_id"],
        "topology_status": topology["status"],
        "trailing_value_rows": trailing,
        "visible_dash_rescues": rescue_projections,
    }
    return _validate_result(
        {**material, "row_axis_id": "afrav1:axis:" + canonical_json_sha256_v1(material)}
    )


def validate_accounting_family_row_axis_replay_v1(
    value: Any,
    pages: Any,
    family_topology_spec: Any,
    *,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Reject any row/lane mutation by exact complete-input reconstruction."""

    persisted = _validate_result(value)
    expected = build_accounting_family_row_axis_v1(
        pages,
        family_topology_spec,
        visible_dash_rescues=visible_dash_rescues,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("family row-axis result does not replay exactly")
    return persisted
