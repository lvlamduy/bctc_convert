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
from statistics import median
from typing import Any

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation.accounting_table_axes_v1 import (
    accounting_unit_surface_v1,
    extract_period_axis_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    assign_value_row_lanes_v1,
    cluster_numeric_rows_v1,
    infer_numeric_column_centers_v1,
    median_text_height_v1,
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
    "build_accounting_family_row_axis_for_topology_region_v1",
    "validate_accounting_family_row_axis_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_FAMILY_ROW_AXIS_V1"
CLAIM_BOUNDARY = (
    "COMPLETE_DOCUMENT_DECLARATIVE_FAMILY_TOPOLOGY_TO_GEOMETRY_BOUND_VISIBLE_"
    "PPOCRV6_RECOGNITION_LANE_WITH_EXACT_LOCAL_PERIOD_AND_UNIT_HEADER_SUPPORTED_"
    "MISSING_COLUMN_GEOMETRY_PROPOSAL_ONLY_NO_MISSING_CELL_INFERENCE_NUMERIC_"
    "ACCOUNTING_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "accounting_authority": False,
    "bank_file_note_page_period_scope_used_for_matching_or_routing": False,
    "detector_geometry_treated_as_numeric_recognition": False,
    "degraded_short_mark_requires_clear_same_row_peer_and_accounting": True,
    "family_layout_logic_is_declarative": True,
    "header_supported_column_completion_requires_period_unit_geometry_agreement": True,
    "mapping_authority": False,
    "missing_cells_synthesized": False,
    "numeric_reader_may_identify_bounded_left_footnote_marker": True,
    "numeric_authority": False,
    "optional_blank_structural_groups_remain_topology_only": True,
    "optional_label_only_rows_require_blank_pixel_lanes_and_complete_structural_parent": True,
    "optional_partial_rows_require_blank_missing_lanes_and_complete_structural_parent": True,
    "period_or_unit_authority": False,
    "ppocrv6_recognition_used_as_raw_proposal_only": True,
    "raw_record_self_authenticating": False,
    "schema_authority": False,
    "staggered_lane_bboxes_bound_by_complete_parent_child_row_axis": True,
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
    "column_grids",
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
_COLUMN_GRID_FIELDS = {
    "column_centers",
    "geometry_status",
    "header_evidence_source_line_indices",
    "page_sequence",
}
_SHA = re.compile(r"^[0-9a-f]{64}$")
_STANDALONE_DECORATIVE_MARKER = re.compile(r"^\(\s*(?:[0-9]{1,2}|[ivxIVX]{1,4}|\*{1,3})\s*\)$")
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
    "supporting_peer_dash_column_ordinal",
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
    return parsed["classification"] in {
        "DASH_ZERO",
        "MIXED_GROUPED_INTEGER_CANDIDATE",
        "NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
        "SIGNED_NUMBER",
    }


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


def _role_body_lines_by_page(
    pages: Sequence[Mapping[str, Any]],
    region: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    """Bound numeric-grid inference to the semantic role body on each page.

    A topology region can intentionally span an adjacent subview or page, but
    the remainder of either page may contain a different table with percentage
    columns, approval stamps, or the next disclosure.  Inferring one grid from
    the complete topology window lets that later furniture manufacture extra
    numeric lanes.  The role labels are the stable vertical anchors: retain the
    visible body plus a small text-height-scaled trailing band for printed
    subtotals, without using a bank, page, family, or fixed pixel threshold.
    """

    by_page = {page["page_sequence"]: page for page in pages}
    region_by_page = _region_lines(pages, region)
    result: dict[int, list[dict[str, Any]]] = {}
    for page_sequence in sorted({match["page_sequence"] for match in matches}):
        page = by_page[page_sequence]
        local = region_by_page.get(page_sequence, [])
        page_matches = [match for match in matches if match["page_sequence"] == page_sequence]
        label_lines = [
            line
            for match in page_matches
            for line in page["lines"]
            if line["line_ordinal"] in _match_source_line_indices(match)
        ]
        if not local or not label_lines:
            raise _error("family role-body band retained no source geometry")
        scale = median_text_height_v1(local)
        top = min(line["bbox"][1] for line in label_lines) - scale * 0.8
        bottom = max(line["bbox"][3] for line in label_lines) + scale * 4.0
        selected = [line for line in local if line["bbox"][3] >= top and line["bbox"][1] <= bottom]
        if not selected:
            raise _error("family role-body band selected no source line")
        result[page_sequence] = selected
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


def _match_source_line_indices(match: Mapping[str, Any]) -> tuple[int, ...]:
    """Return only semantic label fragments, excluding interleaved value cells."""

    raw = match.get("source_line_indices")
    if raw is None:
        start = match["source_line_index"]
        stop = match["end_source_line_index"]
        return tuple(range(start, stop + 1))
    if (
        type(raw) is not list
        or len(raw) < 2
        or any(type(index) is not int for index in raw)
        or raw != sorted(set(raw))
        or raw[0] != match["source_line_index"]
        or raw[-1] != match["end_source_line_index"]
    ):
        raise _error("noncontiguous topology label source axis drifted")
    return tuple(raw)


def _label_geometry_boxes(
    page: Mapping[str, Any],
    match: Mapping[str, Any],
    *,
    column_centers: Sequence[float],
    page_matches: Sequence[Mapping[str, Any]],
    local_lines: Sequence[Mapping[str, Any]],
) -> list[list[int]]:
    """Retain a bounded standalone footnote as part of its source label band.

    A wrapped accounting label can end with ``(ii)`` on a separate detector
    line while its two numeric cells share that final line's baseline.  The
    semantic matcher correctly prefers the shorter label surface, but row
    geometry must not therefore strand the values.  Extend the geometry by at
    most one immediately following decorative marker, only on the label side
    of an already inferred numeric grid and before the next semantic role.

    This is deliberately narrower than deleting arbitrary parentheticals: a
    year, narrative qualifier, value-lane token, or non-adjacent line cannot
    change the row band.
    """

    label_indices = _match_source_line_indices(match)
    stop = match["end_source_line_index"]
    boxes = [
        canonical_clone_v1(line["bbox"])
        for line in page["lines"]
        if line["line_ordinal"] in label_indices
    ]
    if not boxes or not column_centers:
        return boxes
    following_ordinal = stop + 1
    next_role = min(
        (
            other["source_line_index"]
            for other in page_matches
            if other is not match and other["source_line_index"] > stop
        ),
        default=None,
    )
    if next_role is not None and following_ordinal >= next_role:
        return boxes
    following = next(
        (line for line in page["lines"] if line["line_ordinal"] == following_ordinal),
        None,
    )
    if following is None:
        return boxes
    marker_surfaces = (
        following["vietocr_text"].strip(),
        following["numeric_recognition"]["raw_prediction"].strip(),
    )
    if not any(_STANDALONE_DECORATIVE_MARKER.fullmatch(surface) for surface in marker_surfaces):
        return boxes
    marker = following["bbox"]
    if marker[2] >= min(column_centers):
        return boxes
    scale = median_text_height_v1(local_lines)
    label_bottom = max(box[3] for box in boxes)
    if marker[1] - label_bottom > scale * 0.45:
        return boxes
    return [*boxes, canonical_clone_v1(marker)]


def _complete_physical_value_clusters(
    rows: Sequence[Mapping[str, Any]], *, lane_count: int
) -> list[list[dict[str, Any]]]:
    """Cluster unique detector cells into complete physical value rows."""

    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        for value in row["values"]:
            prior = unique.get(value["sample_id"])
            if prior is not None and not same_typed_json_v1(prior, value):
                # Row affinity is role-relative; every other source-cell field
                # must remain identical across contenders.
                left = canonical_clone_v1(prior)
                right = canonical_clone_v1(value)
                left.pop("row_affinity")
                right.pop("row_affinity")
                if not same_typed_json_v1(left, right):
                    raise _error("one source cell changed across semantic row contenders")
            unique.setdefault(value["sample_id"], canonical_clone_v1(value))
    if not unique:
        return []
    heights = [value["bbox"][3] - value["bbox"][1] for value in unique.values()]
    scale = float(median(heights))
    clusters: list[list[dict[str, Any]]] = []
    for value in sorted(
        unique.values(),
        key=lambda item: (
            item["page_sequence"],
            (item["bbox"][1] + item["bbox"][3]) / 2,
            item["column_ordinal"],
        ),
    ):
        center = (value["bbox"][1] + value["bbox"][3]) / 2
        target = next(
            (
                cluster
                for cluster in clusters
                if cluster[0]["page_sequence"] == value["page_sequence"]
                and value["column_ordinal"] not in {item["column_ordinal"] for item in cluster}
                and abs(
                    center
                    - float(median((item["bbox"][1] + item["bbox"][3]) / 2 for item in cluster))
                )
                <= scale * 0.55
            ),
            None,
        )
        if target is None:
            clusters.append([value])
        else:
            target.append(value)
    expected_lanes = list(range(lane_count))
    return [
        sorted(cluster, key=lambda item: item["column_ordinal"])
        for cluster in clusters
        if sorted(item["column_ordinal"] for item in cluster) == expected_lanes
    ]


def _structural_group_cluster_assignments(
    rows: list[dict[str, Any]],
) -> dict[str, int]:
    """Bind complete physical rows to a label-only group's exact children.

    If one structural group has N observed children and exactly N complete
    numeric row clusters, the parent is a label-only context.  Matching the
    ordered physical axes as wholes prevents staggered detector boxes from
    splitting the two lanes between adjacent labels.  N+1 clusters retain a
    genuinely valued parent and deliberately do not enter this rule.
    """

    assignments: dict[str, int] = {}
    for group_index, group in enumerate(rows):
        if group["role_kind"] != "STRUCTURAL_GROUP":
            continue
        children = [
            (index, row)
            for index, row in enumerate(rows)
            if row["label_match"].get("matched_within_role") == group["role"]
            and row["label_match"]["page_sequence"] == group["label_match"]["page_sequence"]
        ]
        if not children:
            continue
        lane_count = group["_lane_count"]
        if any(child["_lane_count"] != lane_count for _index, child in children):
            raise _error("one structural group spans inconsistent value-lane counts")
        participant_indices = {group_index, *(index for index, _child in children)}
        participants = [group, *(child for _index, child in children)]
        clusters = _complete_physical_value_clusters(participants, lane_count=lane_count)
        if len(clusters) != len(children):
            continue
        ordered_children = sorted(children, key=lambda item: item[1]["_label_vertical_center"])
        ordered_clusters = sorted(
            clusters,
            key=lambda cluster: float(
                median((item["bbox"][1] + item["bbox"][3]) / 2 for item in cluster)
            ),
        )
        cluster_sample_ids = {
            value["sample_id"] for cluster in ordered_clusters for value in cluster
        }
        proposed: dict[str, int] = {}
        coherent = True
        for cluster, (child_index, child) in zip(ordered_clusters, ordered_children, strict=True):
            cluster_center = float(
                median((item["bbox"][1] + item["bbox"][3]) / 2 for item in cluster)
            )
            cluster_height = float(median(item["bbox"][3] - item["bbox"][1] for item in cluster))
            cluster_lanes = {item["column_ordinal"] for item in cluster}
            residual_lanes = {
                item["column_ordinal"]
                for item in child["values"]
                if item["sample_id"] not in cluster_sample_ids
            }
            group_direct_by_sample = {item["sample_id"]: item for item in group["values"]}
            valued_parent_has_exact_direct_source_affinity = (
                {item["sample_id"] for item in cluster} <= set(group_direct_by_sample)
                # row_affinity_v1 reaches 2.0 only for a fully coextensive
                # label/value interval with the same center.  Preserve that
                # exact parent-direct source even when an adjacent child OCR
                # box overlaps it by one positive pixel.  Lower-affinity
                # staggered clusters still use the ordered child-axis rule.
                and all(
                    type(group_direct_by_sample[item["sample_id"]].get("row_affinity")) is float
                    and group_direct_by_sample[item["sample_id"]]["row_affinity"] == 2.0
                    for item in cluster
                )
            )
            if (
                abs(cluster_center - child["_label_vertical_center"]) > cluster_height
                or cluster_lanes & residual_lanes
                or valued_parent_has_exact_direct_source_affinity
            ):
                coherent = False
                break
            for value in cluster:
                sample_id = value["sample_id"]
                participant_affinities = [
                    contender["row_affinity"]
                    for index, row in enumerate(rows)
                    if index in participant_indices
                    for contender in row["values"]
                    if contender["sample_id"] == sample_id
                ]
                outsider_affinities = [
                    contender["row_affinity"]
                    for index, row in enumerate(rows)
                    if index not in participant_indices
                    for contender in row["values"]
                    if contender["sample_id"] == sample_id
                ]
                if outsider_affinities:
                    if any(
                        type(affinity) is not float
                        for affinity in [*participant_affinities, *outsider_affinities]
                    ):
                        raise _error("structural row-cluster contender affinity drifted")
                    if max(outsider_affinities) > max(participant_affinities):
                        # The ordered structural-owner axis can reconcile
                        # staggered lanes among one parent and its children,
                        # but it cannot preempt a directly observed row from
                        # outside that participant set.  Abstain only for the
                        # challenged source cell; the ordinary global
                        # exclusivity pass below will retain its unique
                        # strongest contender, while exact ties continue to
                        # preserve the complete structural axis.
                        continue
                proposed[sample_id] = child_index
        if not coherent:
            continue
        for sample_id, child_index in proposed.items():
            prior = assignments.setdefault(sample_id, child_index)
            if prior != child_index:
                raise _error("one physical value row belongs to two structural groups")
    return assignments


def _enforce_exclusive_source_cells(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Let one detector cell support at most one semantic source row.

    Adjacent labels can both have weak vertical overlap with the same value.
    Assigning each row independently then duplicates that source cell across
    two accounting roles.  The globally strongest row affinity wins only when
    it is unique; an exact affinity tie is ambiguous and the cell is removed
    from every contender so the ordinary pixel-rescue path can fail closed.
    """

    cluster_assignments = _structural_group_cluster_assignments(rows)
    if cluster_assignments:
        original_uses: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for row_index, row in enumerate(rows):
            for value in row["values"]:
                original_uses.setdefault(value["sample_id"], []).append((row_index, value))
        assigned_samples = set(cluster_assignments)
        for row in rows:
            removed = [value for value in row["values"] if value["sample_id"] in assigned_samples]
            row["values"] = [
                value for value in row["values"] if value["sample_id"] not in assigned_samples
            ]
            for value in removed:
                lane = value["column_ordinal"]
                if lane not in row["missing_column_ordinals"]:
                    row["missing_column_ordinals"].append(lane)
            row["missing_column_ordinals"].sort()
        for sample_id, target_index in cluster_assignments.items():
            contenders = original_uses[sample_id]
            direct = next((value for index, value in contenders if index == target_index), None)
            template = canonical_clone_v1(direct if direct is not None else contenders[0][1])
            if direct is None:
                template["row_affinity"] = None
            lane = template["column_ordinal"]
            target = rows[target_index]
            if any(value["column_ordinal"] == lane for value in target["values"]):
                raise _error("physical row-cluster binding repeats one value lane")
            target["values"].append(template)
            target["values"].sort(key=lambda value: value["column_ordinal"])
            if lane in target["missing_column_ordinals"]:
                target["missing_column_ordinals"].remove(lane)

    uses: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for row in rows:
        for value in row["values"]:
            uses.setdefault(value["sample_id"], []).append((row, value))
    for contenders in uses.values():
        if len(contenders) == 1:
            continue
        affinities = [value["row_affinity"] for _row, value in contenders]
        if any(type(affinity) is not float for affinity in affinities):
            raise _error("visible source-cell row affinity drifted")
        strongest = max(affinities)
        winners = [(row, value) for row, value in contenders if value["row_affinity"] == strongest]
        winner = winners[0] if len(winners) == 1 else None
        for row, value in contenders:
            if winner is not None and row is winner[0] and value is winner[1]:
                continue
            row["values"].remove(value)
            lane = value["column_ordinal"]
            if lane not in row["missing_column_ordinals"]:
                row["missing_column_ordinals"].append(lane)
                row["missing_column_ordinals"].sort()
    for row in rows:
        row.pop("_label_vertical_center")
        row.pop("_lane_count")
        row["status"] = (
            "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL"
            if not row["values"]
            else "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
            if row["missing_column_ordinals"]
            else "VISIBLE_VALUE_LANES_BOUND"
        )
    return rows


def _resolved_page_grid_inputs(
    rows: Sequence[Mapping[str, Any]],
    target_row: Mapping[str, Any],
    column_grids: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[tuple[float, ...], tuple[dict[str, Any], ...]]:
    """Reuse the exclusive row-axis grid for detector-independent cell crops.

    Re-running row affinity inside the crop proposer can borrow an adjacent
    row's detector cell after the row-axis exclusivity gate has already
    rejected that assignment.  All role rows on one page were built from the
    same inferred grid, so their retained lane centers form the exact input to
    the missing-cell proposal.
    """

    page_sequence = target_row["label_match"]["page_sequence"]
    page_rows = [row for row in rows if row["label_match"]["page_sequence"] == page_sequence]
    grid = (
        next(
            (item for item in column_grids if item["page_sequence"] == page_sequence),
            None,
        )
        if column_grids is not None
        else None
    )
    lane_count = (
        max(
            (
                lane
                for row in page_rows
                for lane in (
                    [value["column_ordinal"] for value in row["values"]]
                    + list(row["missing_column_ordinals"])
                )
            ),
            default=-1,
        )
        + 1
    )
    if grid is not None:
        centers = tuple(grid["column_centers"])
        if len(centers) != lane_count:
            raise _error("retained page column grid differs from the role-row lane axis")
    else:
        centers = ()
    if lane_count <= 0:
        raise _error("resolved page grid retained no numeric lane")
    if not centers:
        reconstructed = []
        for lane in range(lane_count):
            candidates = {
                value["column_center"]
                for row in page_rows
                for value in row["values"]
                if value["column_ordinal"] == lane
            }
            if len(candidates) != 1 or any(
                type(center) is not float or not math.isfinite(center) for center in candidates
            ):
                raise _error("resolved page grid lane center is absent or inconsistent")
            reconstructed.append(next(iter(candidates)))
        centers = tuple(reconstructed)
    visible_cells = tuple(
        {
            "bbox": canonical_clone_v1(value["bbox"]),
            "column_ordinal": value["column_ordinal"],
        }
        for value in target_row["values"]
    )
    return centers, visible_cells


def _header_axis_line(line: Mapping[str, Any]) -> dict[str, Any]:
    """Project one joined evidence line into the shared header parser shape."""

    return {
        "bbox": canonical_clone_v1(line["bbox"]),
        "numeric_score": line["numeric_recognition"]["reader_score"],
        "numeric_text": line["numeric_recognition"]["raw_prediction"],
        "source_line_index": line["line_ordinal"],
        "vietocr_text": line["vietocr_text"],
    }


def _box_anchor(box: Sequence[int], alignment: str) -> float:
    if alignment == "LEFT":
        return float(box[0])
    if alignment == "CENTER":
        return (box[0] + box[2]) / 2
    if alignment == "RIGHT":
        return float(box[2])
    raise _error("header/body column alignment mode drifted")


def _evidence_union_box(
    lines_by_index: Mapping[int, Mapping[str, Any]], indices: Sequence[int]
) -> list[int] | None:
    selected = [lines_by_index.get(index) for index in indices]
    if not selected or any(line is None for line in selected):
        return None
    boxes = [line["bbox"] for line in selected if line is not None]
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _header_supported_numeric_column_centers(
    *,
    page: Mapping[str, Any],
    body_lines: Sequence[Mapping[str, Any]],
    header_source_lines: Sequence[Mapping[str, Any]],
    page_matches: Sequence[Mapping[str, Any]],
    body_centers: Sequence[float],
    region_start_source_line_index: int,
) -> tuple[list[float], list[int]] | None:
    """Complete a detector-deficient body grid from two agreeing header levels.

    A detector can omit every printed DASH in one comparison column, leaving
    the body with only one recognized numeric lane.  The missing *cell* is not
    inferred here.  We recover only its column geometry, and only when one
    bounded local header band independently contains a complete period axis
    and a coextensive unit axis.  Existing body cells must align uniquely with
    the resulting grid; a later authenticated pixel crop still has to prove a
    visible DASH or number.
    """

    if not page_matches:
        return None
    first_match = min(page_matches, key=lambda item: item["source_line_index"])
    first_boxes = [
        line["bbox"]
        for line in body_lines
        if line["line_ordinal"] in _match_source_line_indices(first_match)
    ]
    if not first_boxes:
        raise _error("first family role retained no page-local geometry")
    scale = median_text_height_v1(header_source_lines)
    first_top = min(box[1] for box in first_boxes)
    header_lines = [
        _header_axis_line(line)
        for line in header_source_lines
        if region_start_source_line_index <= line["line_ordinal"]
        and line["bbox"][1] < first_top
        and first_top - scale * 10.0 <= line["bbox"][3] <= first_top + scale * 0.35
    ]
    period_records, period_mode = extract_period_axis_v1(header_lines)
    if period_mode not in {
        "LOCAL_EXACT_DATES",
        "LOCAL_RELATIVE_PERIOD_ROLES",
        "LOCAL_SPLIT_DATES",
    } or not (2 <= len(period_records) <= 8):
        return None
    period_roles = [record["period"] for record in period_records]
    if len(period_roles) != len(set(period_roles)):
        return None
    unit_lines = [
        line
        for line in header_lines
        if accounting_unit_surface_v1(line["vietocr_text"]) is not None
    ]
    if len(unit_lines) != len(period_records):
        return None
    unit_lines.sort(key=lambda line: (line["bbox"][0] + line["bbox"][2], line["source_line_index"]))
    lines_by_index = {line["source_line_index"]: line for line in header_lines}
    period_boxes = [
        _evidence_union_box(lines_by_index, record["evidence_source_line_indices"])
        for record in period_records
    ]
    if any(box is None for box in period_boxes):
        return None
    parsed_period_boxes = [box for box in period_boxes if box is not None]
    lane_gap = min(
        (right[0] + right[2]) / 2 - (left[0] + left[2]) / 2
        for left, right in zip(parsed_period_boxes, parsed_period_boxes[1:], strict=False)
    )
    if lane_gap <= scale * 2.0:
        return None
    alignment, residuals = min(
        [
            (
                mode,
                [
                    abs(_box_anchor(period_box, mode) - _box_anchor(unit["bbox"], mode))
                    for period_box, unit in zip(parsed_period_boxes, unit_lines, strict=True)
                ],
            )
            for mode in ("LEFT", "CENTER", "RIGHT")
        ],
        key=lambda item: (
            float(median(item[1])),
            ("RIGHT", "CENTER", "LEFT").index(item[0]),
        ),
    )
    if max(residuals) > max(scale * 1.5, lane_gap * 0.2):
        return None
    body_boxes = [
        line["bbox"]
        for line in body_lines
        if line["line_ordinal"] >= first_match["source_line_index"] and _is_numeric(line)
    ]
    if body_boxes:
        typical_width = float(median(box[2] - box[0] for box in body_boxes))
        if alignment == "RIGHT":
            candidates = [float(line["bbox"][2]) - typical_width / 2 for line in unit_lines]
        elif alignment == "LEFT":
            candidates = [float(line["bbox"][0]) + typical_width / 2 for line in unit_lines]
        else:
            candidates = [(line["bbox"][0] + line["bbox"][2]) / 2 for line in unit_lines]
    else:
        # A table whose every body value is a printed DASH can legitimately
        # have zero detector-produced numeric boxes.  Two independent local
        # header levels (period and unit) still prove the lane geometry.  This
        # only creates pixel-crop proposals; the render-level glyph reader must
        # independently prove each DASH before any zero enters the row axis.
        candidates = [(line["bbox"][0] + line["bbox"][2]) / 2 for line in unit_lines]
    if (
        candidates != sorted(set(candidates))
        or candidates[0] < 0
        or candidates[-1] > page["page_width"]
        or len(candidates) <= len(body_centers)
    ):
        return None
    candidate_gap = min(
        right - left for left, right in zip(candidates, candidates[1:], strict=False)
    )
    tolerance = max(scale * 2.5, candidate_gap * 0.35)
    used: set[int] = set()
    for center in body_centers:
        lane = min(range(len(candidates)), key=lambda ordinal: abs(center - candidates[ordinal]))
        if lane in used or abs(center - candidates[lane]) > tolerance:
            return None
        used.add(lane)
    evidence_indices = sorted(
        {
            *(
                index
                for record in period_records
                for index in record["evidence_source_line_indices"]
            ),
            *(line["source_line_index"] for line in unit_lines),
        }
    )
    return candidates, evidence_indices


def _structural_roles_with_complete_children(
    rows: Sequence[Mapping[str, Any]],
) -> set[str]:
    roles = {
        row["label_match"].get("matched_within_role")
        for row in rows
        if row["status"] == "VISIBLE_VALUE_LANES_BOUND"
    }
    for index, row in enumerate(rows):
        if row["role_kind"] != "STRUCTURAL_GROUP":
            continue
        following = []
        for candidate in rows[index + 1 :]:
            if candidate["role_kind"] == "STRUCTURAL_GROUP":
                break
            following.append(candidate)
        if any(
            candidate["role_kind"] == "ADDITIVE_CHILD"
            and candidate["status"] == "VISIBLE_VALUE_LANES_BOUND"
            and candidate["label_match"].get("matched_within_role") in {None, row["role"]}
            for candidate in following
        ):
            roles.add(row["role"])
    return {role for role in roles if type(role) is str}


def _rows(
    pages: Sequence[Mapping[str, Any]], region: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_page = {page["page_sequence"]: page for page in pages}
    rows = []
    nonstructural_spans = {
        (
            match["page_sequence"],
            _match_source_line_indices(match),
        )
        for match in region["child_matches"]
        if match["role_kind"] != "STRUCTURAL_GROUP"
    }
    retained_matches = []
    for match in region["child_matches"]:
        span = (
            match["page_sequence"],
            _match_source_line_indices(match),
        )
        # A flattened source row can satisfy both its structural context and
        # one valued leaf (for example "Tiền gửi không kỳ hạn bằng VND").
        # The same detector cell may never be emitted twice.
        if match["role_kind"] == "STRUCTURAL_GROUP" and span in nonstructural_spans:
            continue
        retained_matches.append(match)
    region_by_page = _role_body_lines_by_page(pages, region, retained_matches)

    # Resolve one immutable numeric-column grid per page from every semantic
    # row in the selected family region.  The left boundary is derived from
    # the observed label bboxes rather than a fixed page-width percentage:
    # wide four-lane tables commonly start before 45% of the page, while a
    # narrow two-lane table begins much farther right.
    centers_by_page: dict[int, list[float]] = {}
    grids_by_page: dict[int, dict[str, Any]] = {}
    for page_sequence in sorted({item["page_sequence"] for item in retained_matches}):
        page = by_page[page_sequence]
        if type(page["page_width"]) is not int:
            raise _error("matched family page requires one authenticated render width")
        local_lines = region_by_page[page_sequence]
        label_rights: list[int] = []
        for match in retained_matches:
            if match["page_sequence"] != page_sequence:
                continue
            boxes = [
                line["bbox"]
                for line in page["lines"]
                if line["line_ordinal"] in _match_source_line_indices(match)
            ]
            if not boxes:
                raise _error("topology label span retained no row-axis geometry")
            label_rights.append(max(box[2] for box in boxes))
        heights = [line["bbox"][3] - line["bbox"][1] for line in local_lines]
        if not label_rights or not heights:
            raise _error("family page retained no adaptive row/column geometry")
        minimum_x_ratio = min(
            0.45,
            max(
                0.05,
                (float(median(label_rights)) + float(median(heights)) * 0.5) / page["page_width"],
            ),
        )
        body_centers = infer_numeric_column_centers_v1(
            local_lines,
            is_numeric=_is_numeric,
            page_width=page["page_width"],
            minimum_x_ratio=minimum_x_ratio,
            retain_singleton_columns=False,
        )
        header_grid = _header_supported_numeric_column_centers(
            page=page,
            body_lines=local_lines,
            header_source_lines=page["lines"],
            page_matches=[
                item for item in retained_matches if item["page_sequence"] == page_sequence
            ],
            body_centers=body_centers,
            region_start_source_line_index=(
                region["cluster_start_source_line_index"]
                if page_sequence == region["page_sequence"]
                and type(region["cluster_start_source_line_index"]) is int
                else 0
            ),
        )
        centers = header_grid[0] if header_grid is not None else body_centers
        centers_by_page[page_sequence] = centers
        grids_by_page[page_sequence] = {
            "column_centers": canonical_clone_v1(centers),
            "geometry_status": (
                "LOCAL_PERIOD_AND_UNIT_HEADER_SUPPORTED_COLUMN_GRID"
                if header_grid is not None
                else "BODY_DERIVED_NUMERIC_COLUMN_GRID"
            ),
            "header_evidence_source_line_indices": (
                canonical_clone_v1(header_grid[1]) if header_grid is not None else []
            ),
            "page_sequence": page_sequence,
        }

    for match in retained_matches:
        page_sequence = match["page_sequence"]
        page = by_page[page_sequence]
        local_lines = region_by_page[page_sequence]
        centers = centers_by_page[page_sequence]
        label_boxes = _label_geometry_boxes(
            page,
            match,
            column_centers=centers,
            page_matches=[
                item for item in retained_matches if item["page_sequence"] == page_sequence
            ],
            local_lines=local_lines,
        )
        if not label_boxes:
            raise _error("topology label span retained no row-axis geometry")
        assignments = (
            assign_value_row_lanes_v1(
                local_lines,
                label_boxes=label_boxes,
                is_numeric=_is_numeric,
                page_width=page["page_width"],
                retain_singleton_columns=False,
                resolved_column_centers=tuple(centers),
            )
            if centers
            else []
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
                "_label_vertical_center": float(
                    median((box[1] + box[3]) / 2 for box in label_boxes)
                ),
                "_lane_count": len(centers),
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
    exclusive = _enforce_exclusive_source_cells(rows)
    # Structural headings are allowed to be either valued inline subtotals or
    # label-only contexts. Retain them as source rows only when the complete
    # visible lane axis binds after global cell exclusivity; otherwise they
    # remain available solely through the topology region. This behavior is
    # needed by hierarchical families and does not synthesize missing cells.
    complete_roles = _structural_roles_with_complete_children(exclusive)
    retained_rows = [
        row
        for row in exclusive
        if row["role_kind"] != "STRUCTURAL_GROUP"
        or row["status"] == "VISIBLE_VALUE_LANES_BOUND"
        or row["role"] not in complete_roles
    ]
    retained_pages = {row["label_match"]["page_sequence"] for row in retained_rows}
    return retained_rows, [grids_by_page[page] for page in sorted(retained_pages)]


def _rescue_projection(
    raw: Any,
    *,
    pages: Sequence[Mapping[str, Any]],
    region: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    column_grids: Sequence[Mapping[str, Any]],
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
        if line["line_ordinal"] in _match_source_line_indices(label_match)
    ]
    centers, visible_cells = _resolved_page_grid_inputs(rows, row, column_grids)
    proposals = propose_missing_value_lane_regions_v1(
        local_lines,
        label_boxes=label_boxes,
        is_numeric=_is_numeric,
        page_width=page["page_width"],
        page_height=render_ref["pixel_height"],
        retain_singleton_columns=False,
        resolved_column_centers=centers,
        resolved_visible_value_cells=visible_cells,
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
        "supporting_peer_dash_column_ordinal": None,
    }
    if dash["classification"] not in {
        "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE",
        "VISIBLE_HORIZONTAL_DASH_GLYPH",
    }:
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
    column_grids: Sequence[Mapping[str, Any]],
    value: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if type(value) is not tuple:
        raise _error("visible-dash rescues must be one exact tuple")
    completed = canonical_clone_v1(rows)
    projections: list[dict[str, Any]] = []
    proposed_values: list[dict[str, Any] | None] = []
    keys: set[tuple[str, int, int]] = set()
    for raw in value:
        projection, rescued = _rescue_projection(
            raw,
            pages=pages,
            region=region,
            # Every proposal is authenticated against the same immutable base
            # row grid.  Applying an earlier dash changes `completed` and must
            # not move the expected bbox for a later rescue.
            rows=rows,
            column_grids=column_grids,
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
        proposed_values.append(rescued)
    for index, (projection, rescued) in enumerate(zip(projections, proposed_values, strict=True)):
        if projection["classification"] == "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE":
            peers = sorted(
                candidate["column_ordinal"]
                for candidate in projections
                if candidate["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
                and candidate["role"] == projection["role"]
                and candidate["page_sequence"] == projection["page_sequence"]
                and candidate["column_ordinal"] != projection["column_ordinal"]
            )
            if not peers:
                proposed_values[index] = None
                rescued = None
            else:
                projection["supporting_peer_dash_column_ordinal"] = peers[0]
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


def _mark_optional_blank_rows(
    rows: list[dict[str, Any]], rescue_projections: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Retain optional blank lanes without pretending they contain values.

    Some disclosures print a valued structural parent and then spell out
    optional component names without placing a number or DASH on one or all
    of those child lanes.  Such labels and any genuinely visible peer values
    are useful provenance, but a blank pixel crop is never zero.  Admit the
    optional row as nonblocking only when its exact parent is a complete
    visible structural row and every missing body-grid crop is independently
    blank.  The incomplete child remains excluded from the numeric/accounting
    role axis downstream and therefore remains visible as an unmapped source
    item rather than blocking secure sibling/parent mappings.
    """

    completed = canonical_clone_v1(rows)
    parent_by_role = {
        row["role"]: row
        for row in completed
        if row["role_kind"] == "STRUCTURAL_GROUP" and row["status"] == "VISIBLE_VALUE_LANES_BOUND"
    }
    rescue_by_key = {
        (item["role"], item["page_sequence"], item["column_ordinal"]): item
        for item in rescue_projections
    }
    for row in completed:
        match = row["label_match"]
        parent_role = match.get("matched_within_role")
        if (
            row["role_kind"] != "ADDITIVE_CHILD"
            or match.get("presence") != "OPTIONAL"
            or type(parent_role) is not str
            or parent_role not in parent_by_role
            or not row["missing_column_ordinals"]
        ):
            continue
        blank = []
        for lane in row["missing_column_ordinals"]:
            rescue = rescue_by_key.get((row["role"], match["page_sequence"], lane))
            blank.append(
                rescue is not None
                and rescue["classification"] == "UNRESOLVED_NOT_ONE_DASH_GLYPH"
                and rescue["dash_evidence"]["glyph_metrics"]["component_count"] == 0
            )
        if blank and all(blank):
            row["status"] = (
                "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES"
                if row["values"]
                else "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS"
            )
    return completed


def _blank_optional_structural_group_keys(
    rows: Sequence[Mapping[str, Any]],
    rescue_projections: Sequence[Mapping[str, Any]],
) -> set[tuple[str, int]]:
    """Keep an empty optional group as topology, not a manufactured value row."""

    rescue_by_key = {
        (item["role"], item["page_sequence"], item["column_ordinal"]): item
        for item in rescue_projections
    }
    result = set()
    for row in rows:
        match = row["label_match"]
        if (
            row["role_kind"] != "STRUCTURAL_GROUP"
            or match.get("presence") != "OPTIONAL"
            or row["values"]
            or not row["missing_column_ordinals"]
        ):
            continue
        if all(
            (rescue := rescue_by_key.get((row["role"], match["page_sequence"], lane))) is not None
            and rescue["classification"] == "UNRESOLVED_NOT_ONE_DASH_GLYPH"
            and rescue["dash_evidence"]["glyph_metrics"]["component_count"] == 0
            for lane in row["missing_column_ordinals"]
        ):
            result.add((row["role"], match["page_sequence"]))
    return result


def _rescue_completed_structural_group_keys(
    base_rows: Sequence[Mapping[str, Any]],
    completed_rows: Sequence[Mapping[str, Any]],
    rescue_projections: Sequence[Mapping[str, Any]],
) -> set[tuple[str, int]]:
    """Retain one partial subtotal completed only by sealed ordinary dashes."""

    result = set()
    keys = {
        (row["role"], row["label_match"]["page_sequence"])
        for row in base_rows
        if row["role_kind"] == "STRUCTURAL_GROUP"
    }
    for key in keys:
        base = [
            row
            for row in base_rows
            if (row["role"], row["label_match"]["page_sequence"]) == key
        ]
        completed = [
            row
            for row in completed_rows
            if (row["role"], row["label_match"]["page_sequence"]) == key
        ]
        projections = [
            projection
            for projection in rescue_projections
            if (projection["role"], projection["page_sequence"]) == key
        ]
        if len(base) != 1 or len(completed) != 1:
            continue
        base_row = base[0]
        completed_row = completed[0]
        missing = base_row["missing_column_ordinals"]
        if (
            base_row["status"] != "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
            or not base_row["values"]
            or not missing
            or completed_row["status"] != "VISIBLE_VALUE_LANES_BOUND"
            or not same_typed_json_v1(
                base_row["label_match"], completed_row["label_match"]
            )
            or len(projections) != len(missing)
            or sorted(projection["column_ordinal"] for projection in projections) != missing
        ):
            continue
        if all(
            projection["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
            and len(
                rescued_values := [
                    value
                    for value in completed_row["values"]
                    if value["column_ordinal"] == projection["column_ordinal"]
                ]
            )
            == 1
            and rescued_values[0]["sample_id"] == projection["region_id"]
            and rescued_values[0]["parsed_token"]["classification"] == "DASH_ZERO"
            for projection in projections
        ):
            result.add(key)
    return result


def _trailing_value_rows(
    pages: Sequence[Mapping[str, Any]],
    region: Mapping[str, Any],
    role_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not region["child_matches"]:
        return []
    by_page = {page["page_sequence"]: page for page in pages}
    region_by_page = _role_body_lines_by_page(pages, region, region["child_matches"])
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
            retain_singleton_columns=False,
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
        "missing_lane_count": sum(
            len(row["missing_column_ordinals"])
            for row in rows
            if row["status"]
            not in {
                "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS",
                "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES",
            }
        ),
        "optional_label_only_blank_lane_count": sum(
            len(row["missing_column_ordinals"])
            for row in rows
            if row["status"] == "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS"
        ),
        "optional_label_only_row_count": sum(
            row["status"] == "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS" for row in rows
        ),
        "optional_partial_blank_lane_count": sum(
            len(row["missing_column_ordinals"])
            for row in rows
            if row["status"] == "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES"
        ),
        "optional_partial_row_count": sum(
            row["status"] == "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES" for row in rows
        ),
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
            item["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
            or (
                item["classification"] == "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE"
                and item["supporting_peer_dash_column_ordinal"] is not None
            )
            for item in rescues
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
        or type(value["column_grids"]) is not list
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
    grid_by_page: dict[int, dict[str, Any]] = {}
    for expected_page_order, grid in enumerate(value["column_grids"]):
        if (
            type(grid) is not dict
            or set(grid) != _COLUMN_GRID_FIELDS
            or type(grid["page_sequence"]) is not int
            or grid["page_sequence"] <= 0
            or grid["page_sequence"] in grid_by_page
            or (
                expected_page_order > 0
                and grid["page_sequence"]
                <= value["column_grids"][expected_page_order - 1]["page_sequence"]
            )
            or type(grid["column_centers"]) is not list
            or any(
                type(center) is not float or not math.isfinite(center) or center < 0
                for center in grid["column_centers"]
            )
            or grid["column_centers"] != sorted(set(grid["column_centers"]))
            or grid["geometry_status"]
            not in {
                "BODY_DERIVED_NUMERIC_COLUMN_GRID",
                "LOCAL_PERIOD_AND_UNIT_HEADER_SUPPORTED_COLUMN_GRID",
            }
            or type(grid["header_evidence_source_line_indices"]) is not list
            or any(
                type(index) is not int or index < 0
                for index in grid["header_evidence_source_line_indices"]
            )
            or grid["header_evidence_source_line_indices"]
            != sorted(set(grid["header_evidence_source_line_indices"]))
            or (
                grid["geometry_status"] == "BODY_DERIVED_NUMERIC_COLUMN_GRID"
                and grid["header_evidence_source_line_indices"]
            )
            or (
                grid["geometry_status"] == "LOCAL_PERIOD_AND_UNIT_HEADER_SUPPORTED_COLUMN_GRID"
                and (not grid["column_centers"] or not grid["header_evidence_source_line_indices"])
            )
        ):
            raise _error("family row-axis page column grid drifted")
        grid_by_page[grid["page_sequence"]] = grid
    if {row["label_match"].get("page_sequence") for row in value["rows"]} != set(grid_by_page):
        raise _error("family role-row pages differ from their column-grid axis")
    for row in value["rows"]:
        grid = grid_by_page[row["label_match"]["page_sequence"]]
        lane_count = len(grid["column_centers"])
        observed = [item["column_ordinal"] for item in row["values"]]
        missing = row["missing_column_ordinals"]
        if (
            observed != sorted(set(observed))
            or type(missing) is not list
            or missing != sorted(set(missing))
            or sorted([*observed, *missing]) != list(range(lane_count))
            or any(
                item["column_center"] != grid["column_centers"][item["column_ordinal"]]
                for item in row["values"]
            )
            or row["status"]
            not in {
                "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE",
                "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL",
                "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS",
                "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES",
                "VISIBLE_VALUE_LANES_BOUND",
            }
        ):
            raise _error("family role row differs from its retained page column grid")
    material = canonical_clone_v1(value)
    identity = material.pop("row_axis_id")
    if identity != "afrav1:axis:" + canonical_json_sha256_v1(material):
        raise _error("family row-axis hash identity drifted")
    for rescue in value["visible_dash_rescues"]:
        if (
            type(rescue) is not dict
            or set(rescue) != _RESCUE_PROJECTION_FIELDS
            or rescue["classification"]
            not in {
                "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE",
                "UNRESOLVED_NOT_ONE_DASH_GLYPH",
                "VISIBLE_HORIZONTAL_DASH_GLYPH",
            }
            or type(rescue["column_center"]) is not float
            or type(rescue["column_ordinal"]) is not int
            or rescue["column_ordinal"] < 0
            or type(rescue["page_sequence"]) is not int
            or rescue["page_sequence"] <= 0
            or type(rescue["region_id"]) is not str
            or not rescue["region_id"].startswith("ffaprv1:region:")
            or type(rescue["role"]) is not str
            or not rescue["role"]
            or (
                rescue["supporting_peer_dash_column_ordinal"] is not None
                and (
                    type(rescue["supporting_peer_dash_column_ordinal"]) is not int
                    or rescue["supporting_peer_dash_column_ordinal"] < 0
                    or rescue["supporting_peer_dash_column_ordinal"] == rescue["column_ordinal"]
                )
            )
        ):
            raise _error("visible-dash rescue projection drifted")
        if (
            rescue["supporting_peer_dash_column_ordinal"] is not None
            and rescue["classification"] != "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE"
        ):
            raise _error("degraded visible-mark peer binding drifted")
        if rescue["supporting_peer_dash_column_ordinal"] is not None and not any(
            peer["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
            and peer["role"] == rescue["role"]
            and peer["page_sequence"] == rescue["page_sequence"]
            and peer["column_ordinal"] == rescue["supporting_peer_dash_column_ordinal"]
            for peer in value["visible_dash_rescues"]
        ):
            raise _error("degraded visible-mark clear peer is absent")
    assigned_region_ids = {item["sample_id"] for row in value["rows"] for item in row["values"]}
    for rescue in value["visible_dash_rescues"]:
        if rescue["classification"] == "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE" and (
            rescue["supporting_peer_dash_column_ordinal"] is not None
        ) != (rescue["region_id"] in assigned_region_ids):
            raise _error("degraded visible-mark admission drifted")
    for row in value["rows"]:
        if row["status"] not in {
            "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS",
            "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES",
        }:
            continue
        match = row["label_match"]
        parent = next(
            (
                candidate
                for candidate in value["rows"]
                if candidate["role"] == match.get("matched_within_role")
                and candidate["role_kind"] == "STRUCTURAL_GROUP"
                and candidate["status"] == "VISIBLE_VALUE_LANES_BOUND"
            ),
            None,
        )
        if (
            match.get("presence") != "OPTIONAL"
            or parent is None
            or (row["status"] == "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS" and row["values"])
            or (
                row["status"] == "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES"
                and not row["values"]
            )
            or not row["missing_column_ordinals"]
            or any(
                not any(
                    rescue["role"] == row["role"]
                    and rescue["page_sequence"] == match["page_sequence"]
                    and rescue["column_ordinal"] == lane
                    and rescue["classification"] == "UNRESOLVED_NOT_ONE_DASH_GLYPH"
                    and rescue["dash_evidence"]["glyph_metrics"]["component_count"] == 0
                    for rescue in value["visible_dash_rescues"]
                )
                for lane in row["missing_column_ordinals"]
            )
        ):
            raise _error("optional blank-lane role lacks exact pixel-parent proof")
    return canonical_clone_v1(value)


def _build_axis(
    parsed_pages: list[dict[str, Any]],
    topology: dict[str, Any],
    selected_region: dict[str, Any] | None,
    visible_dash_rescues: Any,
) -> dict[str, Any]:
    base_rows, column_grids = (
        _rows(parsed_pages, selected_region) if selected_region is not None else ([], [])
    )
    rows, rescue_projections = (
        _apply_visible_dash_rescues(
            parsed_pages,
            selected_region,
            base_rows,
            column_grids,
            visible_dash_rescues,
        )
        if selected_region is not None
        else (base_rows, [])
    )
    complete_structural_roles = _structural_roles_with_complete_children(rows)
    originally_complete_structural_rows = {
        (row["role"], row["label_match"]["page_sequence"])
        for row in base_rows
        if row["role_kind"] == "STRUCTURAL_GROUP" and row["status"] == "VISIBLE_VALUE_LANES_BOUND"
    }
    # A structural subtotal can be visibly valued while one printed zero lane
    # is represented only by an authenticated dash crop.  Preserve that narrow
    # case after the rescue has replayed, without permitting a repeated
    # same-role occurrence, blank crop, degraded mark, or partial rescue set to
    # bypass the complete-child filter.
    rescue_completed_structural_rows = _rescue_completed_structural_group_keys(
        base_rows, rows, rescue_projections
    )
    blank_optional_structural_rows = _blank_optional_structural_group_keys(rows, rescue_projections)
    rows = [
        row
        for row in rows
        if (row["role"], row["label_match"]["page_sequence"]) not in blank_optional_structural_rows
        and (
            row["role_kind"] != "STRUCTURAL_GROUP"
            or (
                row["status"] == "VISIBLE_VALUE_LANES_BOUND"
                and (row["role"], row["label_match"]["page_sequence"])
                in originally_complete_structural_rows | rescue_completed_structural_rows
            )
            or row["role"] not in complete_structural_roles
        )
    ]
    retained_pages = {row["label_match"]["page_sequence"] for row in rows}
    column_grids = [grid for grid in column_grids if grid["page_sequence"] in retained_pages]
    rows = _mark_optional_blank_rows(rows, rescue_projections)
    if selected_region is None and visible_dash_rescues != ():
        raise _error("visible-dash rescue cannot bypass an unselected topology region")
    trailing = (
        _trailing_value_rows(parsed_pages, selected_region, rows)
        if selected_region is not None
        else []
    )
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "column_grids": column_grids,
        "family_id": topology["family_id"],
        "format_version": FORMAT_VERSION,
        "metrics": _result_metrics(rows, trailing, rescue_projections),
        "rows": rows,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "UNRESOLVED_TOPOLOGY"
            if not rows
            else "ROW_AXIS_PROPOSAL_WITH_UNRESOLVED_CELLS"
            if any(
                row["status"]
                not in {
                    "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS",
                    "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES",
                    "VISIBLE_VALUE_LANES_BOUND",
                }
                for row in rows
            )
            else "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
        ),
        "topology_region": (
            canonical_clone_v1(selected_region) if selected_region is not None else None
        ),
        "topology_scan_id": topology["scan_id"],
        "topology_status": topology["status"],
        "trailing_value_rows": trailing,
        "visible_dash_rescues": rescue_projections,
    }
    return _validate_result(
        {**material, "row_axis_id": "afrav1:axis:" + canonical_json_sha256_v1(material)}
    )


def _scan_topology(parsed_pages: list[dict[str, Any]], family_topology_spec: Any) -> dict[str, Any]:
    try:
        return topology_v1.build_accounting_family_topology_scan_v1(
            _topology_pages(parsed_pages), family_topology_spec
        )
    except topology_v1.AccountingFamilyTopologyV1Error as exc:
        raise _error("family row-axis topology input drifted") from exc


def build_accounting_family_row_axis_v1(
    pages: Any,
    family_topology_spec: Any,
    *,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Rebuild topology and bind its unique child region to visible lanes."""

    parsed_pages = _pages(pages)
    topology = _scan_topology(parsed_pages, family_topology_spec)
    selected = (
        topology["regions"][0]
        if topology["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
        else None
    )
    return _build_axis(parsed_pages, topology, selected, visible_dash_rescues)


def build_accounting_family_row_axis_for_topology_region_v1(
    pages: Any,
    family_topology_spec: Any,
    topology_region: Any,
    *,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Bind one exact observed region so later evidence can disambiguate it.

    The caller cannot invent or alter a region: the complete-document topology
    scan is rebuilt and the supplied value must exactly equal one of its
    regions.  This keeps bank/page routing out of candidate selection while
    allowing period, unit, geometry and accounting gates to distinguish two
    semantically plausible regions.
    """

    parsed_pages = _pages(pages)
    topology = _scan_topology(parsed_pages, family_topology_spec)
    if type(topology_region) is not dict:
        raise _error("selected topology region must be one exact object")
    selected = [
        region for region in topology["regions"] if same_typed_json_v1(region, topology_region)
    ]
    if len(selected) != 1:
        raise _error("selected topology region is not one exact scan candidate")
    return _build_axis(parsed_pages, topology, selected[0], visible_dash_rescues)


def _build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
    pages: Any,
    family_topology_spec: Any,
    topology_scan: Any,
    topology_region: Any,
    *,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Bind a region from an already authenticated same-engine scan.

    This private seam avoids rebuilding the complete-document semantic scan
    during row/column/accounting evaluation.  Its caller must obtain the scan
    from a live evidence capability or from the same-turn topology builder;
    public replay continues to rebuild the scan from source pages.
    """

    parsed_pages = _pages(pages)
    try:
        topology = topology_v1._validate_result(topology_scan)
        compiled = topology_v1._spec(family_topology_spec)
    except topology_v1.AccountingFamilyTopologyV1Error as exc:
        raise _error("authenticated family row-axis topology input drifted") from exc
    if topology["family_id"] != compiled["family_id"] or type(topology_region) is not dict:
        raise _error("authenticated family row-axis topology family/region drifted")
    selected = [
        region for region in topology["regions"] if same_typed_json_v1(region, topology_region)
    ]
    if len(selected) != 1:
        raise _error("authenticated selected topology region is not one exact scan candidate")
    return _build_axis(parsed_pages, topology, selected[0], visible_dash_rescues)


def validate_accounting_family_row_axis_replay_v1(
    value: Any,
    pages: Any,
    family_topology_spec: Any,
    *,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Reject any row/lane mutation by exact complete-input reconstruction."""

    persisted = _validate_result(value)
    expected = (
        build_accounting_family_row_axis_for_topology_region_v1(
            pages,
            family_topology_spec,
            persisted["topology_region"],
            visible_dash_rescues=visible_dash_rescues,
        )
        if persisted["topology_region"] is not None
        and persisted["topology_status"] != "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
        else build_accounting_family_row_axis_v1(
            pages,
            family_topology_spec,
            visible_dash_rescues=visible_dash_rescues,
        )
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("family row-axis result does not replay exactly")
    return persisted
