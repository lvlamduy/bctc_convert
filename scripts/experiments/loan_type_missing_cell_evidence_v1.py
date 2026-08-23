"""Resolve detector-missing loan-type cells from authenticated page pixels.

The table graph selects the row and lane.  A missing cell is first challenged
as a visible dash.  When a broad row proposal contains an adjacent dash or a
table rule, a generic component selector chooses the unique dash-shaped glyph
nearest the visible label baseline and re-crops it tightly.  Non-dash cells
require an exact same-crop reference-blind PP-OCRv6 observation; accounting is
only a final veto and never supplies a digit or zero.
"""

from __future__ import annotations

import copy
import io
import math
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1  # noqa: E402
from bctc_ai.evaluation.accounting_pixel_glyphs_v1 import (  # noqa: E402
    foreground_components_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (  # noqa: E402
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.evaluation.family_first_numeric_cell_evidence_v1 import (  # noqa: E402
    build_family_first_ppocrv6_numeric_cell_evidence_v1,
)
from bctc_ai.evaluation.family_first_visible_dash_glyph_evidence_v1 import (  # noqa: E402
    build_family_first_visible_dash_glyph_evidence_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import loan_type_numeric_row_reconciliation_v1 as numeric_v1  # noqa: E402
from scripts.experiments import loan_type_variant_graph_v1 as graph_v1  # noqa: E402

FORMAT_VERSION = "LOAN_TYPE_MISSING_CELL_PIXEL_EVIDENCE_V1"
CLAIM_BOUNDARY = (
    "UNIQUE_LOAN_TYPE_ROW_LANE_AUTHENTICATED_PIXEL_DASH_OR_EXACT_SAME_CROP_"
    "REFERENCE_BLIND_PPOCRV6_EVIDENCE_PLUS_ACCOUNTING_VETO_ONLY_NO_SCHEMA_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_equation_used_as_final_veto_only": True,
    "blank_cell_means_zero": False,
    "gemma_numeric_authority": False,
    "mapping_authority": False,
    "missing_digit_inferred_from_total": False,
    "ppocrv6_same_crop_numeric_evidence_required_for_non_dash_rescue": True,
    "schema_authority": False,
    "visible_dash_may_normalize_to_zero": True,
}
_RESCUE_FIELDS = {
    "crop_sha256",
    "lane_index",
    "page_sequence",
    "raw_prediction",
    "reader_score",
    "role",
}


class LoanTypeMissingCellEvidenceV1Error(ValueError):
    """The table, pixel crop, rescue observation, or equation drifted."""


def _error(message: str) -> LoanTypeMissingCellEvidenceV1Error:
    return LoanTypeMissingCellEvidenceV1Error(message)


def _direct_pixel_crop(render: bytes, bbox: Sequence[int]) -> Image.Image:
    try:
        with Image.open(io.BytesIO(render)) as raw:
            raw.load()
            image = raw.convert("RGB")
    except OSError as exc:
        raise _error("authenticated render cannot be decoded") from exc
    if (
        type(bbox) is not list
        or len(bbox) != 4
        or any(type(item) is not int for item in bbox)
        or not 0 <= bbox[0] < bbox[2] <= image.width
        or not 0 <= bbox[1] < bbox[3] <= image.height
    ):
        raise _error("missing-cell proposal bbox drifted")
    return image.crop(tuple(bbox))


def _tight_dash_bbox(
    render: bytes,
    proposed_bbox: list[int],
    *,
    label_baseline_y: int,
) -> list[int] | None:
    """Select one dash-shaped component nearest a source-row baseline."""

    image = _direct_pixel_crop(render, proposed_bbox)
    candidates: list[tuple[float, list[int]]] = []
    for component in foreground_components_v1(image)["components"]:
        left, top, right, bottom = component["bbox"]
        width = right - left
        height = bottom - top
        aspect = width / height
        fill = component["ink_pixel_count"] / (width * height)
        if not (1.25 <= aspect <= 8.0 and width <= 40 and height <= 15 and fill >= 0.2):
            continue
        page_bbox = [
            proposed_bbox[0] + left,
            proposed_bbox[1] + top,
            proposed_bbox[0] + right,
            proposed_bbox[1] + bottom,
        ]
        distance = abs((page_bbox[1] + page_bbox[3]) / 2 - label_baseline_y)
        candidates.append((distance, page_bbox))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    if len(candidates) > 1 and math.isclose(candidates[0][0], candidates[1][0], abs_tol=2.0):
        return None
    left, top, right, bottom = candidates[0][1]
    return [
        max(proposed_bbox[0], left - 14),
        max(proposed_bbox[1], top - 8),
        min(proposed_bbox[2], right + 14),
        min(proposed_bbox[3], bottom + 8),
    ]


def _rescue_map(value: Any) -> dict[tuple[int, str, int], dict[str, Any]]:
    if type(value) is not tuple:
        raise _error("numeric rescue observations must be one exact tuple")
    result = {}
    for raw in value:
        if (
            type(raw) is not dict
            or set(raw) != _RESCUE_FIELDS
            or type(raw["page_sequence"]) is not int
            or raw["page_sequence"] <= 0
            or type(raw["role"]) is not str
            or not raw["role"]
            or type(raw["lane_index"]) is not int
            or raw["lane_index"] < 0
            or type(raw["crop_sha256"]) is not str
            or len(raw["crop_sha256"]) != 64
            or type(raw["raw_prediction"]) is not str
            or type(raw["reader_score"]) not in {int, float}
            or not math.isfinite(float(raw["reader_score"]))
            or not 0 <= float(raw["reader_score"]) <= 1
        ):
            raise _error("numeric rescue observation fields drifted")
        key = (raw["page_sequence"], raw["role"], raw["lane_index"])
        if key in result:
            raise _error("numeric rescue observation repeats one row lane")
        result[key] = canonical_clone_v1(raw)
    return result


def _matcher_pages(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for page in pages:
        if type(page) is not dict or set(page) != {"lines", "page_sequence", "page_width"}:
            raise _error("joined loan-type page fields drifted")
        result.append(
            {
                "lines": [
                    {
                        "bbox": line["bbox"],
                        "source_line_index": line["line_ordinal"],
                        "source_text": line["numeric_recognition"]["raw_prediction"],
                        "vietocr_text": line["vietocr_text"],
                    }
                    for line in page["lines"]
                ],
                "page_sequence": page["page_sequence"],
                "primary_numeric_authority": True,
            }
        )
    return result


def build_loan_type_missing_cell_evidence_v1(
    pages: Sequence[Mapping[str, Any]],
    render_snapshot: Mapping[str, Any],
    *,
    numeric_rescue_observations: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    """Resolve every detector-missing money cell in one loan-type table."""

    matcher_pages = _matcher_pages(pages)
    base = numeric_v1.build_loan_type_numeric_row_reconciliation_v1(matcher_pages)
    graph = graph_v1.build_loan_type_variant_graph_document_v1(
        matcher_pages, enable_extended_owner_table_variants=True
    )["graphs"][0]
    page_sequence = graph["page_sequence"]
    source_page = next((page for page in pages if page["page_sequence"] == page_sequence), None)
    matcher_page = next(
        (page for page in matcher_pages if page["page_sequence"] == page_sequence), None
    )
    if source_page is None or matcher_page is None or source_page["page_width"] is None:
        raise _error("selected loan-type page/dimensions are absent")
    render_record, render = region_v1._validated_render_snapshot(render_snapshot)
    if (
        render_record["physical_page"] != page_sequence
        or render_record["render_ref"]["pixel_width"] != source_page["page_width"]
    ):
        raise _error("loan-type graph and authenticated render select another page")
    by_index = {line["source_line_index"]: line for line in matcher_page["lines"]}
    centers = tuple(value / 2.0 for value in graph["lane_centers_x2"])
    rescues = _rescue_map(numeric_rescue_observations)
    evidence = []
    rows = copy.deepcopy([*base["rows"], *base["unmodelled_additive_rows"]])
    for row in rows:
        missing = [cell["lane_index"] for cell in row["cells"] if cell["parsed_value"] is None]
        if not missing:
            continue
        visible = [
            {
                "bbox": by_index[cell["source_line_index"]]["bbox"],
                "column_ordinal": cell["lane_index"],
            }
            for cell in row["cells"]
            if cell["source_line_index"] is not None
        ]
        label_boxes = [by_index[index]["bbox"] for index in row["label"]["source_line_indices"]]
        proposals = {
            item["column_ordinal"]: item
            for item in propose_missing_value_lane_regions_v1(
                matcher_page["lines"],
                label_boxes=label_boxes,
                is_numeric=graph_v1._line_is_number_like,
                page_width=source_page["page_width"],
                page_height=render_record["render_ref"]["pixel_height"],
                minimum_x_ratio=0.05,
                maximum_x_ratio=0.98,
                resolved_column_centers=centers,
                resolved_visible_value_cells=visible,
            )
        }
        for lane in missing:
            proposal = proposals.get(lane)
            if proposal is None:
                raise _error("missing loan-type lane has no geometric proposal")
            region = region_v1._crop_authenticated_family_first_page_render_snapshot_v1(
                dict(render_snapshot), raw_pixel_bbox=proposal["raw_pixel_bbox"]
            )
            dash = build_family_first_visible_dash_glyph_evidence_v1(
                crop_png_bytes=region["region_png_bytes"]
            )
            selection = "DIRECT_GRID_REGION"
            if dash["classification"] != "VISIBLE_HORIZONTAL_DASH_GLYPH":
                tight = _tight_dash_bbox(
                    render,
                    proposal["raw_pixel_bbox"],
                    label_baseline_y=max(box[3] for box in label_boxes),
                )
                if tight is not None:
                    tight_region = (
                        region_v1._crop_authenticated_family_first_page_render_snapshot_v1(
                            dict(render_snapshot), raw_pixel_bbox=tight
                        )
                    )
                    tight_dash = build_family_first_visible_dash_glyph_evidence_v1(
                        crop_png_bytes=tight_region["region_png_bytes"]
                    )
                    if tight_dash["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH":
                        region, dash = tight_region, tight_dash
                        selection = "UNIQUE_NEAREST_LABEL_BASELINE_DASH_COMPONENT"
            cell = row["cells"][lane]
            if dash["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH":
                cell.update(
                    {
                        "parsed_value": 0,
                        "ppocrv6_surface": None,
                        "semantic_surface": None,
                        "source_line_index": None,
                        "status": "VISIBLE_PIXEL_DASH_ZERO",
                    }
                )
                evidence.append(
                    {
                        "classification": "VISIBLE_PIXEL_DASH_ZERO",
                        "dash_evidence": dash,
                        "lane_index": lane,
                        "numeric_evidence": None,
                        "page_sequence": page_sequence,
                        "proposed_raw_pixel_bbox": proposal["raw_pixel_bbox"],
                        "recognition_raw_pixel_bbox": region["recognition_raw_pixel_bbox"],
                        "region_id": region["region_id"],
                        "role": row["role"],
                        "selection": selection,
                    }
                )
                continue
            rescue_key = (page_sequence, row["role"], lane)
            rescue = rescues.get(rescue_key)
            if rescue is not None and rescue["crop_sha256"] != region["region_png_ref"]["sha256"]:
                raise _error("numeric rescue observation belongs to another exact crop")
            if rescue is None:
                evidence.append(
                    {
                        "classification": "UNRESOLVED_MISSING_CELL",
                        "dash_evidence": dash,
                        "lane_index": lane,
                        "numeric_evidence": None,
                        "page_sequence": page_sequence,
                        "proposed_raw_pixel_bbox": proposal["raw_pixel_bbox"],
                        "recognition_raw_pixel_bbox": region["recognition_raw_pixel_bbox"],
                        "region_id": region["region_id"],
                        "role": row["role"],
                        "selection": selection,
                    }
                )
                continue
            rescues.pop(rescue_key)
            numeric = build_family_first_ppocrv6_numeric_cell_evidence_v1(
                crop_png_bytes=region["region_png_bytes"],
                recognizer_payload={
                    "input_path": None,
                    "page_index": None,
                    "rec_score": rescue["reader_score"],
                    "rec_text": rescue["raw_prediction"],
                },
            )
            token = numeric["parsed_token"]
            if token["classification"] != "SIGNED_NUMBER" or token["scale"] != 0:
                raise _error("targeted PP-OCRv6 rescue is not one integer-money token")
            cell.update(
                {
                    "parsed_value": token["coefficient"],
                    "ppocrv6_surface": rescue["raw_prediction"],
                    "semantic_surface": None,
                    "source_line_index": None,
                    "status": "TARGETED_SAME_CROP_PPOCRV6_NUMERIC_RESCUE",
                }
            )
            evidence.append(
                {
                    "classification": "TARGETED_SAME_CROP_PPOCRV6_NUMERIC_RESCUE",
                    "dash_evidence": dash,
                    "lane_index": lane,
                    "numeric_evidence": numeric,
                    "page_sequence": page_sequence,
                    "proposed_raw_pixel_bbox": proposal["raw_pixel_bbox"],
                    "recognition_raw_pixel_bbox": region["recognition_raw_pixel_bbox"],
                    "region_id": region["region_id"],
                    "role": row["role"],
                    "selection": selection,
                }
            )
    if rescues:
        raise _error("numeric rescue observation was not consumed by one missing cell")
    known_count = len(base["rows"])
    finalized_rows = rows[:known_count]
    finalized_additive = rows[known_count:]
    checks = []
    for lane, lane_type in enumerate(base["lane_types"]):
        if lane_type != "MONEY":
            continue
        values = [row["cells"][lane]["parsed_value"] for row in rows]
        target = base["total"][lane]["parsed_value"]
        exact = (
            type(target) is int
            and all(type(value) is int for value in values)
            and sum(values) == target
        )
        checks.append(
            {
                "additive_sum": sum(value for value in values if type(value) is int),
                "lane_index": lane,
                "status": "EXACT_PIXEL_AND_PP_NUMERIC_EQUATION" if exact else "UNRESOLVED",
                "target_total": target,
            }
        )
    status = (
        "PIXEL_AND_PP_NUMERIC_EXACT"
        if checks
        and all(item["status"] == "EXACT_PIXEL_AND_PP_NUMERIC_EQUATION" for item in checks)
        else "UNRESOLVED_MISSING_CELL_OR_ACCOUNTING"
    )
    material = {
        "accounting_checks": checks,
        "authority": canonical_clone_v1(_AUTHORITY),
        "base_reconciliation_id": base["result_id"],
        "claim_boundary": CLAIM_BOUNDARY,
        "evidence": evidence,
        "format_version": FORMAT_VERSION,
        "intermediate_subtotals": canonical_clone_v1(base["intermediate_subtotals"]),
        "lane_types": canonical_clone_v1(base["lane_types"]),
        "page_sequence": page_sequence,
        "rows": finalized_rows,
        "status": status,
        "total": canonical_clone_v1(base["total"]),
        "unmodelled_additive_rows": finalized_additive,
    }
    return {
        **material,
        "result_id": "ltmcev1:result:" + canonical_json_sha256_v1(material),
    }


def validate_loan_type_missing_cell_evidence_replay_v1(
    value: Any,
    pages: Sequence[Mapping[str, Any]],
    render_snapshot: Mapping[str, Any],
    *,
    numeric_rescue_observations: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    expected = build_loan_type_missing_cell_evidence_v1(
        pages,
        render_snapshot,
        numeric_rescue_observations=numeric_rescue_observations,
    )
    if not same_typed_json_v1(value, expected):
        raise _error("loan-type missing-cell evidence does not replay exactly")
    return expected
