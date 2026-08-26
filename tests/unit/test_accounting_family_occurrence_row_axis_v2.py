from __future__ import annotations

import copy
import hashlib
import io
import json
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import accounting_family_coextensive_parent_total_v1 as total_v1
from bctc_ai.evaluation import accounting_family_column_context_v1 as column_context_v1
from bctc_ai.evaluation import accounting_family_occurrence_row_axis_v2 as subject
from bctc_ai.evaluation import accounting_family_one_edit_exact_authority_v1 as one_edit_v1
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_v1
from bctc_ai.evaluation import accounting_family_topology_candidates_v2 as candidates_v2
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import accounting_scoped_hierarchical_table_closure_v2 as closure_v2
from bctc_ai.evaluation import authenticated_semantic_region_snapshot_v1 as snapshot_v1
from bctc_ai.evaluation import family_first_accounting_evidence_sweep_v1 as sweep_v1
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_F3_TOPOLOGY_PATH = _PROJECT_ROOT / "config/families/tm-interbank-deposits-loans-topology-v4.json"
_F3_EVALUATION_PATH = (
    _PROJECT_ROOT / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
)


def _matcher(alias: str, within: str | None = None) -> dict[str, object]:
    return {"aliases": [alias], "within_role": within}


def _spec() -> dict[str, object]:
    return {
        "children": [
            {
                "matchers": [_matcher("Tiền gửi tại TCTD khác")],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [_matcher("Bằng VND", "DEPOSIT_GROUP")],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Tiền gửi có kỳ hạn")],
                "presence": "OPTIONAL",
                "role": "TERM_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [_matcher("Bằng ngoại tệ", "TERM_GROUP")],
                "presence": "OPTIONAL",
                "role": "TERM_FOREIGN_CURRENCY",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Cho vay TCTD khác")],
                "presence": "OPTIONAL",
                "role": "LOAN_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [_matcher("Bằng VND", "LOAN_GROUP")],
                "presence": "OPTIONAL",
                "role": "LOAN_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Bằng ngoại tệ", "LOAN_GROUP")],
                "presence": "OPTIONAL",
                "role": "LOAN_FOREIGN_CURRENCY",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Dự phòng rủi ro tiền gửi tại TCTD khác")],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_PROVISION",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Tiền gửi và cho vay TCTD khác")],
                "presence": "OPTIONAL",
                "role": "EXPLICIT_FAMILY_TOTAL",
                "role_kind": "TOTAL",
            },
        ],
        "family_id": "INTERBANK",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3",
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 60,
            "max_continuation_pages": 1,
            "max_label_line_span": 3,
        },
        "parent": {
            "aliases": ["Tiền gửi và cho vay TCTD khác"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "INTERBANK",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [["DEPOSIT_GROUP", "LOAN_GROUP"]],
        "structural_reset_aliases": ["Tiền gửi khách hàng"],
    }


def _line(ordinal: int, text: str, numeric: str, bbox: list[int]) -> dict[str, object]:
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": numeric, "reader_score": 0.97},
        "sample_id": f"sample-{ordinal + 1:09d}",
        "vietocr_text": text,
    }


def _row(lines: list[dict[str, object]], label: str, current: str, prior: str) -> None:
    ordinal = len(lines)
    top = 70 + ordinal * 22
    lines.extend(
        [
            _line(ordinal, label, "", [45, top, 430, top + 20]),
            _line(ordinal + 1, current, current, [610, top, 700, top + 20]),
            _line(ordinal + 2, prior, prior, [810, top, 900, top + 20]),
        ]
    )


def _pages(rows: list[tuple[str, str, str]]) -> list[dict[str, object]]:
    lines = [
        _line(0, "Tiền gửi và cho vay TCTD khác", "", [25, 15, 460, 38]),
        _line(1, "31.12.2025", "31.12.2025", [610, 45, 700, 65]),
        _line(2, "31.12.2024", "31.12.2024", [810, 45, 900, 65]),
        _line(3, "150", "150", [610, 15, 700, 38]),
        _line(4, "130", "130", [810, 15, 900, 38]),
    ]
    for row in rows:
        _row(lines, *row)
    return [{"lines": lines, "page_sequence": 1, "page_width": 1000}]


def _build(pages: list[dict[str, object]]) -> tuple[dict, dict]:
    spec = _spec()
    scan = topology_v1.build_accounting_family_topology_scan_v1(row_v1._topology_pages(pages), spec)
    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    effective = total_v1.project_accounting_family_coextensive_parent_total_region_v1(
        spec, scan, scan["regions"][0]
    )
    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        scan["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
    )
    return scan, axis


def _ref(label: str) -> dict[str, object]:
    payload = label.encode()
    return {
        "path": f"fixture/{label}.bin",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _snapshot_and_render(
    pages: list[dict[str, object]],
    dash_bboxes: list[list[int]],
    *,
    colored_bboxes: list[tuple[list[int], str]] | None = None,
) -> tuple[dict, dict]:
    image = Image.new("RGB", (1000, 800), "white")
    draw = ImageDraw.Draw(image)
    for left, top, right, bottom in dash_bboxes:
        center_y = (top + bottom) // 2
        center_x = (left + right) // 2
        draw.rectangle((center_x - 8, center_y - 2, center_x + 8, center_y + 2), fill="black")
    for bbox, color in colored_bboxes or []:
        draw.rectangle(tuple(bbox), fill=color)
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    render_ref = {
        "pixel_height": 800,
        "pixel_width": 1000,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    packet_material = {
        "assurance": "AUDITED",
        "bank_provenance": "SYNTHETIC",
        "document_evidence_root_sha256": hashlib.sha256(b"document-root").hexdigest(),
        "document_id": "document-occurrence-dash",
        "document_ordinal": 1,
        "line_count": len(pages[0]["lines"]),
        "page_count": 1,
        "period": "ANNUAL",
        "scope": "CONSOLIDATED",
        "source_pdf_ref": _ref("source-pdf"),
        "year": 2025,
    }
    packet = {
        **packet_material,
        "packet_id": "ffdesv1:document:" + canonical_json_sha256_v1(packet_material),
    }
    dimensions = [
        {
            "physical_page": 1,
            "pixel_height": 800,
            "pixel_width": 1000,
            "render_sha256": render_ref["sha256"],
            "render_size_bytes": render_ref["size_bytes"],
        }
    ]
    selection_material = {
        "document_id": packet["document_id"],
        "document_ordinal": 1,
        "joined_pages": pages,
        "selected_page_dimensions": dimensions,
    }
    snapshot_material = {
        "document_packet": packet,
        "joined_pages": pages,
        "manifest_id": "ffdesv1:manifest:occurrence-dash",
        "query_selection_id": "ffoqcv1:selection:" + canonical_json_sha256_v1(selection_material),
        "selected_page_dimensions": dimensions,
        "state": "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE",
    }
    snapshot = {
        **snapshot_material,
        "snapshot_id": "ffdesv1:selected:" + canonical_json_sha256_v1(snapshot_material),
    }
    render_material = {
        "archive_id": "archive-occurrence-dash",
        "authority": dict(region_v1._RENDER_AUTHORITY),
        "document_ordinal": 1,
        "format_version": region_v1.RENDER_FORMAT_VERSION,
        "index_id": "index-occurrence-dash",
        "physical_page": 1,
        "plan_id": "plan-occurrence-dash",
        "render_ref": render_ref,
        "state": "AUTHENTICATED_EXACT_SOURCE_PAGE_RENDER_SNAPSHOT",
    }
    render = {
        **render_material,
        "render_id": "ffaprv1:render:" + canonical_json_sha256_v1(render_material),
        "render_png_bytes": payload,
    }
    return snapshot, render


def _blank_region(raw_pixel_bbox: list[int]) -> dict[str, object]:
    image = Image.new("RGB", (42, 27), "white")
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    material = {
        "authority": dict(region_v1._REGION_AUTHORITY),
        "document_ordinal": 1,
        "format_version": region_v1.FORMAT_VERSION,
        "index_id": "index-optional-blank",
        "ink_localization_status": "GLYPH_COMPONENT_TIGHTENED_WITHIN_PROPOSED_CELL",
        "physical_page": 1,
        "proposed_raw_pixel_bbox": list(raw_pixel_bbox),
        "recognition_raw_pixel_bbox": list(raw_pixel_bbox),
        "region_png_ref": {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        "render_id": "render-optional-blank",
        "render_ref": {
            "pixel_height": 1200,
            "pixel_width": 1000,
            "sha256": "1" * 64,
            "size_bytes": 100,
        },
        "state": "AUTHENTICATED_RENDER_CALLER_PROPOSED_REGION_CROP",
        "white_border": [12, 8, 12, 8],
    }
    return {
        **material,
        "region_id": "ffaprv1:region:" + canonical_json_sha256_v1(material),
        "region_png_bytes": payload,
    }


def _dash_rescue_region(
    raw_pixel_bbox: list[int],
    *,
    width: int,
    height: int,
    include_noncentral_artifact: bool,
) -> dict[str, object]:
    image = Image.new("RGB", (40, 32), "white")
    draw = ImageDraw.Draw(image)
    left = 20 - width // 2
    top = 16 - height // 2
    draw.rectangle((left, top, left + width - 1, top + height - 1), fill="black")
    if include_noncentral_artifact:
        draw.rectangle((2, 2, 3, 3), fill="black")
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    material = {
        "authority": dict(region_v1._REGION_AUTHORITY),
        "document_ordinal": 1,
        "format_version": region_v1.FORMAT_VERSION,
        "index_id": f"index-dash-{width}x{height}-{include_noncentral_artifact}",
        "ink_localization_status": "GLYPH_COMPONENT_TIGHTENED_WITHIN_PROPOSED_CELL",
        "physical_page": 1,
        "proposed_raw_pixel_bbox": list(raw_pixel_bbox),
        "recognition_raw_pixel_bbox": list(raw_pixel_bbox),
        "region_png_ref": {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        "render_id": f"render-dash-{width}x{height}-{include_noncentral_artifact}",
        "render_ref": {
            "pixel_height": 1200,
            "pixel_width": 1000,
            "sha256": "2" * 64,
            "size_bytes": 100,
        },
        "state": "AUTHENTICATED_RENDER_CALLER_PROPOSED_REGION_CROP",
        "white_border": [12, 8, 12, 8],
    }
    return {
        **material,
        "region_id": "ffaprv1:region:" + canonical_json_sha256_v1(material),
        "region_png_bytes": payload,
    }


def _tiny_artifact_dash_region(raw_pixel_bbox: list[int]) -> dict[str, object]:
    return _dash_rescue_region(
        raw_pixel_bbox,
        width=4,
        height=2,
        include_noncentral_artifact=True,
    )


def _clear_dash_region(raw_pixel_bbox: list[int]) -> dict[str, object]:
    return _dash_rescue_region(
        raw_pixel_bbox,
        width=9,
        height=4,
        include_noncentral_artifact=False,
    )


def _unique_dash_with_acb_scan_speck_region(
    raw_pixel_bbox: list[int],
) -> dict[str, object]:
    """Preserve ACB's 10x4 dash / 4x3 speck morphology in a proposal-sized crop."""

    width = raw_pixel_bbox[2] - raw_pixel_bbox[0]
    height = raw_pixel_bbox[3] - raw_pixel_bbox[1]
    image = Image.new("RGB", (width + 24, height + 16), "white")
    draw = ImageDraw.Draw(image)
    dash_left = image.width - 35
    dash_top = image.height // 2 + 5
    for y, row in enumerate((".########.", ".#########", "##########", ".#########"), dash_top):
        for x, pixel in enumerate(row, dash_left):
            if pixel == "#":
                draw.point((x, y), fill="black")
    speck_left = max(13, dash_left - 100)
    speck_top = dash_top - 17
    for y, row in enumerate(("##..", "####", ".##."), speck_top):
        for x, pixel in enumerate(row, speck_left):
            if pixel == "#":
                draw.point((x, y), fill="black")
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    material = {
        "authority": dict(region_v1._REGION_AUTHORITY),
        "document_ordinal": 1,
        "format_version": region_v1.FORMAT_VERSION,
        "index_id": "index-unique-dash-acb-speck",
        "ink_localization_status": "GLYPH_COMPONENT_TIGHTENED_WITHIN_PROPOSED_CELL",
        "physical_page": 1,
        "proposed_raw_pixel_bbox": list(raw_pixel_bbox),
        "recognition_raw_pixel_bbox": list(raw_pixel_bbox),
        "region_png_ref": {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        "render_id": "render-unique-dash-acb-speck",
        "render_ref": {
            "pixel_height": 1200,
            "pixel_width": 1000,
            "sha256": "4" * 64,
            "size_bytes": 100,
        },
        "state": "AUTHENTICATED_RENDER_CALLER_PROPOSED_REGION_CROP",
        "white_border": [12, 8, 12, 8],
    }
    return {
        **material,
        "region_id": "ffaprv1:region:" + canonical_json_sha256_v1(material),
        "region_png_bytes": payload,
    }


def _optional_blank_v1_axis(*, partial: bool) -> dict:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Bằng VND", "" if not partial else "70", ""),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    spec = _spec()
    scan = topology_v1.build_accounting_family_topology_scan_v1(row_v1._topology_pages(pages), spec)
    region = scan["regions"][0]
    base = row_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
        pages, spec, scan, region
    )
    child = next(row for row in base["rows"] if row["role"] == "DEPOSIT_VND")
    centers, visible_cells = row_v1._resolved_page_grid_inputs(
        base["rows"], child, base["column_grids"]
    )
    proposals = propose_missing_value_lane_regions_v1(
        [{**line, "source_line_index": line["line_ordinal"]} for line in pages[0]["lines"]],
        label_boxes=[pages[0]["lines"][child["label_match"]["source_line_index"]]["bbox"]],
        is_numeric=lambda line: line["numeric_recognition"]["raw_prediction"].isdigit(),
        page_width=1000,
        page_height=1200,
        resolved_column_centers=centers,
        resolved_visible_value_cells=visible_cells,
    )
    rescues = tuple(
        {
            "column_ordinal": proposal["column_ordinal"],
            "page_sequence": 1,
            "region": _blank_region(proposal["raw_pixel_bbox"]),
            "role": "DEPOSIT_VND",
        }
        for proposal in proposals
    )
    return row_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
        pages,
        spec,
        scan,
        region,
        visible_dash_rescues=rescues,
    )


@pytest.mark.parametrize(
    ("partial", "expected_status"),
    [
        (False, "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS"),
        (True, "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES"),
    ],
)
def test_existing_dash_authentication_preserves_sealed_optional_blank_status_without_dash(
    partial: bool, expected_status: str
) -> None:
    axis = _optional_blank_v1_axis(partial=partial)
    before = next(row for row in axis["rows"] if row["role"] == "DEPOSIT_VND")
    assert before["status"] == expected_status

    completed, projections, reasons = subject._authenticate_existing_dashes(
        axis,
        selected_snapshot=None,
        render_snapshots=(),
    )

    after = next(row for row in completed["rows"] if row["role"] == "DEPOSIT_VND")
    assert completed == axis
    assert after["status"] == expected_status
    assert after["values"] == before["values"]
    assert completed["visible_dash_rescues"] == axis["visible_dash_rescues"]
    assert projections == []
    assert reasons == []


@pytest.mark.parametrize(
    ("partial", "expected_status"),
    [
        (False, "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS"),
        (True, "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES"),
    ],
)
def test_v4_unique_dash_speck_pass_preserves_sealed_optional_blank_status_without_receipt(
    partial: bool, expected_status: str
) -> None:
    axis = _optional_blank_v1_axis(partial=partial)
    before = next(row for row in axis["rows"] if row["role"] == "DEPOSIT_VND")
    assert before["status"] == expected_status

    completed, receipts = subject._project_unique_dash_speck_rescues_v2(
        axis,
        (),
        (),
        topology_candidates_id="afotcv2:result:" + "a" * 64,
        topology_scan_id="afotv1:scan:" + "b" * 64,
    )

    after = next(row for row in completed["rows"] if row["role"] == "DEPOSIT_VND")
    assert completed == axis
    assert after["status"] == expected_status
    assert after["values"] == before["values"]
    assert completed["visible_dash_rescues"] == axis["visible_dash_rescues"]
    assert receipts == []


def test_repeated_children_bind_nearest_parent_and_foreign_term_row_survives() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Bằng VND", "100", "90"),
            ("Tiền gửi có kỳ hạn", "30", "20"),
            ("Bằng ngoại tệ", "30", "20"),
            ("Cho vay TCTD khác", "25", "22"),
            ("Bằng VND", "20", "18"),
            ("Bằng ngoại tệ", "5", "4"),
            ("Cho vay TCTD khác", "12", "10"),
            ("Bằng VND", "9", "8"),
            ("Bằng ngoại tệ", "3", "2"),
        ]
    )
    _scan, axis = _build(pages)

    occurrences = axis["role_occurrences"]
    loan_groups = [item for item in occurrences if item["role"] == "LOAN_GROUP"]
    loan_foreign = [item for item in occurrences if item["role"] == "LOAN_FOREIGN_CURRENCY"]
    assert len(loan_groups) == len(loan_foreign) == 2
    assert [item["scope_owner_occurrence_id"] for item in loan_foreign] == [
        item["occurrence_id"] for item in loan_groups
    ]
    assert any(item["role"] == "TERM_FOREIGN_CURRENCY" for item in occurrences)
    assert axis["status"] == (
        "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
    )


def test_numeric_universe_owns_internal_money_samples_but_excludes_header_dates() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
        ]
    )
    lines = pages[0]["lines"]
    lines[8:8] = [
        _line(999, "7", "7", [610, 213, 700, 233]),
        _line(1_000, "-2", "-2", [810, 213, 900, 233]),
    ]
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal
        line["sample_id"] = f"sample-{ordinal + 1:09d}"
        line["crop_ref"] = {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        }

    _scan, axis = _build(pages)

    cluster = axis["internal_unassigned_numeric_clusters"]
    assert len(cluster) == 1
    assert cluster[0]["column_ordinals"] == [0, 1]
    universe = {sample["sample_id"]: sample for sample in axis["numeric_sample_universe"]}
    assert set(cluster[0]["sample_ids"]) <= set(universe)
    assert {universe[sample_id]["owner_kind"] for sample_id in cluster[0]["sample_ids"]} == {
        "SOURCE_ONLY_INTERNAL_CLUSTER"
    }
    assert lines[1]["sample_id"] not in universe
    assert lines[2]["sample_id"] not in universe
    owned_sample_ids = [
        value["sample_id"] for row in axis["row_axis"]["rows"] for value in row["values"]
    ]
    owned_sample_ids.extend(
        sample_id
        for evidence in axis["coextensive_structural_numeric_evidence"]
        if evidence["status"] == total_v1.COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_STATUS
        for sample_id in evidence["source_sample_ids"]
    )
    assert set(universe) == {*owned_sample_ids, *cluster[0]["sample_ids"]}

    attacked = copy.deepcopy(axis)
    attacked_sample = next(
        sample
        for sample in attacked["numeric_sample_universe"]
        if sample["owner_kind"] == "SOURCE_ONLY_INTERNAL_CLUSTER"
    )
    attacked_sample["owner_id"] = "aforav2:unassigned:forged"
    material = copy.deepcopy(attacked)
    material.pop("occurrence_axis_id")
    attacked["occurrence_axis_id"] = "aforav2:axis:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="internal cluster differs",
    ):
        subject._validate_result(attacked)


def test_numeric_universe_types_body_off_lane_number_but_excludes_header_and_footer() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
        ]
    )
    lines = pages[0]["lines"]
    lines[8:8] = [_line(999, "17", "17", [940, 213, 990, 233])]
    lines.append(_line(1_000, "19", "19", [940, 700, 990, 720]))
    _reindex_page_lines(lines)

    _scan, axis = _build(pages)

    clusters = axis["internal_unassigned_numeric_clusters"]
    assert len(clusters) == 1
    assert clusters[0]["status"] == "SOURCE_ONLY_OFF_LANE_NUMERIC_CLUSTER"
    assert len(clusters[0]["sample_ids"]) == 1
    universe = {sample["sample_id"]: sample for sample in axis["numeric_sample_universe"]}
    assert clusters[0]["sample_ids"][0] in universe
    assert lines[1]["sample_id"] not in universe
    assert lines[2]["sample_id"] not in universe
    assert lines[-1]["sample_id"] not in universe


def test_source_only_numeric_fence_requires_one_exact_contextual_body_owner() -> None:
    pages = [
        {
            "lines": [
                _line(0, "Theo loại hình", "", [45, 100, 430, 122]),
                _line(1, "Loại A", "", [45, 150, 430, 172]),
                _line(2, "Loại B", "", [45, 190, 430, 212]),
            ],
            "page_sequence": 1,
            "page_width": 1000,
        }
    ]
    owner_id = "aforav2:occurrence:" + "a" * 64
    owner = {
        "end_source_line_index": 0,
        "match_kind": "EXACT_ACCENTLESS_ALIAS",
        "occurrence_id": owner_id,
        "page_sequence": 1,
        "role_kind": "STRUCTURAL_GROUP",
        "source_line_index": 0,
    }
    rows = [
        {
            "label_match": {
                "page_sequence": 1,
                "scope_owner_occurrence_id": owner_id,
            },
            "role_kind": "ADDITIVE_CHILD",
        },
        {
            "label_match": {
                "page_sequence": 1,
                "scope_owner_occurrence_id": owner_id,
            },
            "role_kind": "ADDITIVE_CHILD",
        },
    ]

    assert subject._active_contextual_body_owner_top_by_page(pages, [owner], {"rows": rows}) == {
        1: 100
    }
    assert subject._source_only_numeric_is_before_contextual_body(
        {"bbox": [600, 78, 700, 100]}, 100
    )
    assert not subject._source_only_numeric_is_before_contextual_body(
        {"bbox": [600, 99, 700, 101]}, 100
    )
    assert not subject._source_only_numeric_is_before_contextual_body(
        {"bbox": [600, 78, 700, 100]}, None
    )

    mixed = copy.deepcopy(rows)
    mixed[1]["label_match"]["scope_owner_occurrence_id"] = "aforav2:occurrence:" + "b" * 64
    assert subject._active_contextual_body_owner_top_by_page(pages, [owner], {"rows": mixed}) == {}

    for field, value in (
        ("match_kind", "ONE_EDIT_ALIAS_REQUIRES_COMPLETE_TOPOLOGY"),
        ("role_kind", "ADDITIVE_CHILD"),
        ("page_sequence", 2),
    ):
        attacked = copy.deepcopy(owner)
        attacked[field] = value
        assert (
            subject._active_contextual_body_owner_top_by_page(pages, [attacked], {"rows": rows})
            == {}
        )


def test_unique_contextual_structural_body_projects_only_exact_sibling_interval() -> None:
    lines = [
        _line(0, "Outer family", "", [30, 10, 400, 30]),
        _line(1, "Prior view", "", [45, 50, 430, 70]),
        _line(2, "Prior role", "", [45, 90, 430, 110]),
        _line(3, "10", "10", [610, 90, 700, 110]),
        _line(4, "9", "9", [810, 90, 900, 110]),
        _line(5, "Target view", "", [45, 140, 430, 160]),
        _line(6, "Target A", "", [45, 190, 430, 210]),
        _line(7, "60", "60", [610, 190, 700, 210]),
        _line(8, "50", "50", [810, 190, 900, 210]),
        _line(9, "Target B", "", [45, 230, 430, 250]),
        _line(10, "40", "40", [610, 230, 700, 250]),
        _line(11, "35", "35", [810, 230, 900, 250]),
        _line(12, "Next view", "", [45, 290, 430, 310]),
        _line(13, "Later role", "", [45, 340, 430, 360]),
        _line(14, "20", "20", [610, 340, 700, 360]),
        _line(15, "18", "18", [810, 340, 900, 360]),
    ]
    pages = [{"lines": lines, "page_sequence": 1, "page_width": 1000}]

    def match(
        role: str,
        role_kind: str,
        line: int,
        *,
        within_role: str | None = None,
        ordinal: int = 0,
    ) -> dict[str, object]:
        return {
            "document_line_ordinal": line,
            "end_document_line_ordinal": line,
            "end_source_line_index": line,
            "match_kind": "EXACT_ACCENTLESS_ALIAS",
            "matched_within_role": within_role,
            "normalized_surface": role.lower(),
            "page_sequence": 1,
            "preferred_ordinal": line,
            "presence": "OPTIONAL",
            "role": role,
            "role_kind": role_kind,
            "role_occurrence_ordinal": ordinal,
            "source_line_index": line,
            "surface": role,
        }

    raw = [
        match("PRIOR_VIEW", "SOURCE_ONLY_GROUP_PARENT", 1),
        match("PRIOR_ROLE", "ADDITIVE_CHILD", 2),
        match("TARGET_VIEW", "STRUCTURAL_GROUP", 5),
        match("TARGET_A", "ADDITIVE_CHILD", 6, within_role="TARGET_VIEW"),
        match("TARGET_B", "ADDITIVE_CHILD", 9, within_role="TARGET_VIEW"),
        match("NEXT_VIEW", "SOURCE_ONLY_GROUP_PARENT", 12),
        match("LATER_ROLE", "ADDITIVE_CHILD", 13),
    ]
    region = {
        "cluster_end_document_line_ordinal_exclusive": 16,
        "cluster_start_document_line_ordinal": 0,
        "parent_match": {"role": "OUTER"},
    }
    decorated = subject._decorate_scopes(raw, region)
    projected = subject._project_unique_contextual_structural_body_matches_v1(
        pages,
        decorated,
        region,
    )

    assert [item["role"] for item in projected] == ["TARGET_VIEW", "TARGET_A", "TARGET_B"]

    # One sibling-free contextual table is not a subview projection trigger.
    no_siblings = [
        item
        for item in decorated
        if item["role"] not in {"PRIOR_VIEW", "PRIOR_ROLE", "NEXT_VIEW", "LATER_ROLE"}
    ]
    assert (
        subject._project_unique_contextual_structural_body_matches_v1(
            pages,
            no_siblings,
            region,
        )
        == no_siblings
    )

    # A non-exact owner and a second equally evidenced owner both abstain.
    nonexact = copy.deepcopy(decorated)
    next(item for item in nonexact if item["role"] == "TARGET_VIEW")["match_kind"] = (
        "ONE_EDIT_ALIAS_REQUIRES_COMPLETE_TOPOLOGY"
    )
    assert (
        subject._project_unique_contextual_structural_body_matches_v1(
            pages,
            nonexact,
            region,
        )
        == nonexact
    )

    duplicate_raw = [
        *raw,
        match("SECOND_TARGET", "STRUCTURAL_GROUP", 12),
        match("SECOND_A", "ADDITIVE_CHILD", 13, within_role="SECOND_TARGET"),
        match("SECOND_B", "ADDITIVE_CHILD", 13, within_role="SECOND_TARGET"),
    ]
    duplicate = subject._decorate_scopes(duplicate_raw, region)
    assert (
        subject._project_unique_contextual_structural_body_matches_v1(
            pages,
            duplicate,
            region,
        )
        == duplicate
    )


def test_unique_contextual_structural_body_projects_exact_next_page_boundary() -> None:
    pages = [
        {
            "lines": [
                _line(0, "Prior role", "", [45, 90, 430, 110]),
                _line(1, "10", "10", [610, 90, 700, 110]),
                _line(2, "9", "9", [810, 90, 900, 110]),
            ],
            "page_sequence": 1,
            "page_width": 1000,
        },
        {
            "lines": [
                _line(0, "Prior role", "", [45, 40, 430, 60]),
                _line(1, "8", "8", [610, 40, 700, 60]),
                _line(2, "7", "7", [810, 40, 900, 60]),
                _line(3, "Target view", "", [45, 120, 430, 140]),
                _line(4, "Target A", "", [45, 170, 430, 190]),
                _line(5, "60", "60", [610, 170, 700, 190]),
                _line(6, "60%", "60%", [710, 170, 780, 190]),
                _line(7, "50", "50", [810, 170, 900, 190]),
                _line(8, "50%", "50%", [910, 170, 980, 190]),
                _line(9, "Target B", "", [45, 210, 430, 230]),
                _line(10, "40", "40", [610, 210, 700, 230]),
                _line(11, "40%", "40%", [710, 210, 780, 230]),
                _line(12, "35", "35", [810, 210, 900, 230]),
                _line(13, "35%", "35%", [910, 210, 980, 230]),
            ],
            "page_sequence": 2,
            "page_width": 1000,
        },
    ]

    def match(
        role: str,
        role_kind: str,
        page: int,
        line: int,
        document_line: int,
        *,
        within_role: str | None = None,
        ordinal: int = 0,
    ) -> dict[str, object]:
        return {
            "document_line_ordinal": document_line,
            "end_document_line_ordinal": document_line,
            "end_source_line_index": line,
            "match_kind": "EXACT_ACCENTLESS_ALIAS",
            "matched_within_role": within_role,
            "normalized_surface": role.lower(),
            "page_sequence": page,
            "preferred_ordinal": document_line,
            "presence": "OPTIONAL",
            "role": role,
            "role_kind": role_kind,
            "role_occurrence_ordinal": ordinal,
            "source_line_index": line,
            "surface": role,
        }

    raw = [
        match("PRIOR_ROLE", "ADDITIVE_CHILD", 1, 0, 0),
        match("PRIOR_ROLE", "ADDITIVE_CHILD", 2, 0, 100, ordinal=1),
        match("TARGET_VIEW", "STRUCTURAL_GROUP", 2, 3, 103),
        match("TARGET_A", "ADDITIVE_CHILD", 2, 4, 104, within_role="TARGET_VIEW"),
        match("TARGET_B", "ADDITIVE_CHILD", 2, 9, 109, within_role="TARGET_VIEW"),
    ]
    region = {
        "cluster_end_document_line_ordinal_exclusive": 114,
        "cluster_start_document_line_ordinal": 0,
        "continuation_page_count": 1,
        "page_sequence": 1,
        "parent_match": {"role": "OUTER"},
    }
    projected_raw = subject._project_unique_contextual_structural_body_matches_v1(
        pages,
        raw,
        region,
    )
    decorated = subject._decorate_scopes(raw, region)
    projected = subject._project_unique_contextual_structural_body_matches_v1(
        pages, decorated, region
    )

    assert [item["role"] for item in projected_raw] == ["TARGET_VIEW", "TARGET_A", "TARGET_B"]
    assert all("scope_owner_occurrence_id" not in item for item in projected_raw)
    assert [item["role"] for item in projected] == ["TARGET_VIEW", "TARGET_A", "TARGET_B"]

    wrapped_pages = copy.deepcopy(pages)
    for page_sequence, line_ordinals in ((1, {1, 2}), (2, {1, 2})):
        page = wrapped_pages[page_sequence - 1]
        for line in page["lines"]:
            if line["line_ordinal"] in line_ordinals:
                line["bbox"][1] += 30
                line["bbox"][3] += 30
    assert (
        subject._project_unique_contextual_structural_body_matches_v1(
            wrapped_pages, decorated, region
        )
        == decorated
    )

    def complete_row(match_record: dict[str, object], lane_count: int) -> dict[str, object]:
        return {
            "label_match": {"occurrence_id": match_record["occurrence_id"]},
            "missing_column_ordinals": [],
            "status": "VISIBLE_VALUE_LANES_BOUND",
            "values": [{"column_ordinal": lane} for lane in range(lane_count)],
        }

    additive = [item for item in decorated if item["role_kind"] == "ADDITIVE_CHILD"]
    wrapped_row_axis = {
        "rows": [complete_row(item, 2 if item["role"] == "PRIOR_ROLE" else 4) for item in additive]
    }
    projected_from_rows = subject._project_unique_contextual_structural_body_matches_v1(
        wrapped_pages,
        decorated,
        region,
        row_axis=wrapped_row_axis,
    )
    assert [item["role"] for item in projected_from_rows] == [
        "TARGET_VIEW",
        "TARGET_A",
        "TARGET_B",
    ]

    partial_axis = copy.deepcopy(wrapped_row_axis)
    partial_axis["rows"][0]["status"] = "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
    partial_axis["rows"][0]["missing_column_ordinals"] = [1]
    partial_axis["rows"][0]["values"] = [{"column_ordinal": 0}]
    assert (
        subject._project_unique_contextual_structural_body_matches_v1(
            wrapped_pages,
            decorated,
            region,
            row_axis=partial_axis,
        )
        == decorated
    )

    same_lane_axis = copy.deepcopy(wrapped_row_axis)
    for row in same_lane_axis["rows"][:2]:
        row["values"] = [{"column_ordinal": lane} for lane in range(4)]
    assert (
        subject._project_unique_contextual_structural_body_matches_v1(
            wrapped_pages,
            decorated,
            region,
            row_axis=same_lane_axis,
        )
        == decorated
    )

    wrong_continuation = copy.deepcopy(region)
    wrong_continuation["continuation_page_count"] = 0
    assert (
        subject._project_unique_contextual_structural_body_matches_v1(
            pages,
            decorated,
            wrong_continuation,
        )
        == decorated
    )

    same_lane_pages = copy.deepcopy(pages)
    same_lane_pages[1]["lines"] = [
        line for line in same_lane_pages[1]["lines"] if line["line_ordinal"] not in {6, 8, 11, 13}
    ]
    assert (
        subject._project_unique_contextual_structural_body_matches_v1(
            same_lane_pages,
            decorated,
            region,
        )
        == decorated
    )

    pages_with_later_outer = copy.deepcopy(pages)
    pages_with_later_outer[1]["lines"].extend(
        [
            _line(14, "Later outer", "", [45, 260, 430, 280]),
            _line(15, "20", "20", [610, 260, 700, 280]),
            _line(16, "18", "18", [810, 260, 900, 280]),
        ]
    )
    attacked = subject._decorate_scopes(
        [*raw, match("LATER_OUTER", "ADDITIVE_CHILD", 2, 14, 114)],
        {**region, "cluster_end_document_line_ordinal_exclusive": 117},
    )
    assert (
        subject._project_unique_contextual_structural_body_matches_v1(
            pages_with_later_outer,
            attacked,
            {**region, "cluster_end_document_line_ordinal_exclusive": 117},
        )
        == attacked
    )


def test_prose_candidate_with_empty_v1_grid_is_typed_unresolved_without_margin_numeric() -> None:
    pages = [
        {
            "lines": [
                _line(0, "Tiền gửi và cho vay TCTD khác", "", [45, 70, 460, 92]),
                _line(1, "Tiền gửi tại TCTD khác", "", [45, 110, 430, 132]),
                _line(2, "được ghi nhận theo giá gốc", "", [45, 140, 500, 162]),
                _line(3, "Cho vay TCTD khác", "", [45, 180, 430, 202]),
                _line(
                    4,
                    "được phân loại vào tài sản tài chính",
                    "",
                    [45, 210, 520, 232],
                ),
                _line(5, "1", "1", [10, 760, 22, 780]),
            ],
            "page_sequence": 1,
            "page_width": 1000,
        }
    ]

    _scan, axis = _build(pages)

    assert axis["row_axis"]["column_grids"] == [
        {
            "column_centers": [],
            "geometry_status": "BODY_DERIVED_NUMERIC_COLUMN_GRID",
            "header_evidence_source_line_indices": [],
            "page_sequence": 1,
        }
    ]
    assert axis["numeric_sample_universe"] == []
    assert axis["internal_unassigned_numeric_clusters"] == []
    assert axis["status"] == "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"
    assert axis["unresolved_reasons"] == ["VISIBLE_ROLE_OCCURRENCE_ROW_LANES_NOT_COMPLETE"]


def test_projected_owner_and_wrapped_provision_bind_but_reset_footer_does_not() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Bằng VND", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    lines = pages[0]["lines"]
    ordinal = len(lines)
    top = 70 + ordinal * 22
    lines.extend(
        [
            _line(ordinal, "Dự phòng rủi ro tiền gửi tại", "", [45, top, 380, top + 20]),
            _line(ordinal + 1, "TCTD khác", "", [45, top + 21, 250, top + 41]),
            _line(ordinal + 2, "-5", "-5", [610, top + 21, 700, top + 41]),
            _line(ordinal + 3, "-4", "-4", [810, top + 21, 900, top + 41]),
            _line(ordinal + 4, "Tiền gửi khách hàng", "", [45, top + 70, 380, top + 90]),
            _line(ordinal + 5, "999", "999", [610, top + 70, 700, top + 90]),
            _line(ordinal + 6, "888", "888", [810, top + 70, 900, top + 90]),
            _line(ordinal + 7, "21", "21", [810, top + 110, 900, top + 130]),
        ]
    )
    _scan, axis = _build(pages)

    rows = {row["role"]: row for row in axis["row_axis"]["rows"]}
    assert [
        item["parsed_token"]["coefficient"] for item in rows["EXPLICIT_FAMILY_TOTAL"]["values"]
    ] == [
        150,
        130,
    ]
    assert [
        item["parsed_token"]["coefficient"] for item in rows["DEPOSIT_PROVISION"]["values"]
    ] == [
        -5,
        -4,
    ]
    assert axis["row_axis"]["trailing_value_rows"] == []


def test_effective_region_injection_fails_closed() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Bằng VND", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    scan, axis = _build(pages)
    forged = copy.deepcopy(scan["regions"][0])
    forged["child_matches"][0]["role"] = "FORGED_ROLE"
    forged["observed_roles"][0] = "FORGED_ROLE"

    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error, match="closed generic projector"
    ):
        subject.build_accounting_family_occurrence_row_axis_v2(
            pages,
            _spec(),
            scan,
            scan["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=forged,
        )


def test_prepruning_candidate_envelope_is_replayed_and_bound_in_result() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Tiền gửi và cho vay TCTD khác", "200", "180"),
            ("Tiền gửi tại TCTD khác", "120", "110"),
            ("Cho vay TCTD khác", "80", "70"),
            ("Bằng VND", "80", "70"),
        ]
    )
    spec = _spec()
    topology_pages = row_v1._topology_pages(pages)
    scan = topology_v1.build_accounting_family_topology_scan_v1(topology_pages, spec)
    candidates = candidates_v2.build_accounting_family_topology_candidates_v2(topology_pages, spec)
    summary_region = candidates["regions"][0]
    assert len(candidates["regions"]) == 2
    assert summary_region not in scan["regions"]
    assert summary_region["observed_roles"] == ["DEPOSIT_GROUP", "LOAN_GROUP"]
    binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        topology_pages, spec, candidates, summary_region
    )

    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        summary_region,
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=binding["effective_topology_region"],
        topology_candidates=candidates,
    )

    assert axis["topology_candidates_id"] == candidates["result_id"]
    assert axis["topology_scan_id"] == scan["scan_id"]


def test_two_authenticated_dash_lanes_survive_and_coherent_rehash_replay_fails() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Bằng VND", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
            ("Dự phòng rủi ro tiền gửi tại TCTD khác", "-", "-"),
        ]
    )
    dash_lines = [line for line in pages[0]["lines"] if line["vietocr_text"] == "-"]
    snapshot, render = _snapshot_and_render(pages, [line["bbox"] for line in dash_lines])
    spec = _spec()
    scan = topology_v1.build_accounting_family_topology_scan_v1(row_v1._topology_pages(pages), spec)
    effective = total_v1.project_accounting_family_coextensive_parent_total_region_v1(
        spec, scan, scan["regions"][0]
    )
    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        scan["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
        selected_snapshot=snapshot,
        render_snapshots=(render,),
    )

    provision = next(row for row in axis["row_axis"]["rows"] if row["role"] == "DEPOSIT_PROVISION")
    assert [value["parsed_token"]["coefficient"] for value in provision["values"]] == [0, 0]
    assert [item["status"] for item in axis["authenticated_existing_dash_evidence"]] == [
        "AUTHENTICATED_VISIBLE_EXISTING_CELL_DASH_ZERO",
        "AUTHENTICATED_VISIBLE_EXISTING_CELL_DASH_ZERO",
    ]
    assert axis["status"] == (
        "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
    )

    blank_snapshot, blank_render = _snapshot_and_render(pages, [])
    blank_axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        scan["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
        selected_snapshot=blank_snapshot,
        render_snapshots=(blank_render,),
    )
    blank_provision = next(
        row for row in blank_axis["row_axis"]["rows"] if row["role"] == "DEPOSIT_PROVISION"
    )
    assert blank_provision["values"] == []
    assert blank_provision["missing_column_ordinals"] == [0, 1]
    assert blank_axis["status"] == "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"

    attacked = copy.deepcopy(axis)
    attacked["unresolved_reasons"] = ["COHERENT_REHASH_FORGED_REASON"]
    attacked["status"] = "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"
    material = copy.deepcopy(attacked)
    material.pop("occurrence_axis_id")
    attacked["occurrence_axis_id"] = "aforav2:axis:" + canonical_json_sha256_v1(material)
    with pytest.raises(subject.AccountingFamilyOccurrenceRowAxisV2Error, match="replay exactly"):
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            attacked,
            pages,
            _spec(),
            scan,
            scan["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=total_v1.project_accounting_family_coextensive_parent_total_region_v1(
                _spec(), scan, scan["regions"][0]
            ),
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )


def test_prepared_snapshot_projection_matches_public_build_without_replay(monkeypatch) -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Bằng VND", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    snapshot, _render = _snapshot_and_render(pages, [])
    expected_projection = snapshot_v1.build_authenticated_semantic_region_snapshot_v1(snapshot)
    prepared = subject._prepare_authenticated_snapshot_projection_v2(snapshot)
    typed_snapshot, projection = subject._prepared_authenticated_snapshot_projection_authority_v2(
        prepared
    )

    assert projection == expected_projection
    monkeypatch.setattr(
        snapshot_v1,
        "build_authenticated_semantic_region_snapshot_v1",
        lambda *_args, **_kwargs: pytest.fail("prepared occurrence rebuilt the snapshot"),
    )
    monkeypatch.setattr(
        snapshot_v1,
        "validate_authenticated_semantic_region_snapshot_replay_v1",
        lambda *_args, **_kwargs: pytest.fail("prepared occurrence replayed the snapshot"),
    )
    monkeypatch.setattr(
        subject,
        "_prepared_authenticated_snapshot_projection_authority_v2",
        lambda *_args, **_kwargs: pytest.fail("prepared occurrence rehashed the full snapshot"),
    )

    subject._validate_snapshot_and_renders(
        row_v1._pages(typed_snapshot["joined_pages"]),
        typed_snapshot,
        (),
        prepared_snapshot=prepared,
    )
    typed_snapshot["joined_pages"][0]["lines"][0]["vietocr_text"] = "MUTATED AFTER OPEN"
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="projection binding drifted",
    ):
        subject._validate_snapshot_and_renders(
            row_v1._pages(typed_snapshot["joined_pages"]),
            typed_snapshot,
            (),
            prepared_snapshot=prepared,
        )


def test_prepared_candidate_binding_skips_document_topology_replay(monkeypatch) -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Tiền gửi và cho vay TCTD khác", "200", "180"),
            ("Tiền gửi tại TCTD khác", "120", "110"),
            ("Cho vay TCTD khác", "80", "70"),
            ("Bằng VND", "80", "70"),
        ]
    )
    spec = _spec()
    topology_pages = row_v1._topology_pages(pages)
    prepared = candidates_v2._prepare_accounting_family_topology_candidates_v2(
        topology_pages,
        spec,
    )
    scan, candidates, bindings = candidates_v2._prepared_accounting_family_topology_authority_v2(
        prepared
    )
    monkeypatch.setattr(
        candidates_v2,
        "bind_accounting_family_topology_candidate_v2",
        lambda *_args, **_kwargs: pytest.fail("prepared binding replayed full topology"),
    )

    axis = subject._build_accounting_family_occurrence_row_axis_from_authenticated_topology_scan_v2(
        pages,
        spec,
        scan,
        candidates["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        topology_candidates=candidates,
        prepared_topology_binding=bindings[0],
    )

    assert axis["topology_candidates_id"] == candidates["result_id"]
    assert axis["topology_scan_id"] == scan["scan_id"]

    changed_spec = copy.deepcopy(spec)
    changed_spec["limits"]["max_cluster_span_lines"] -= 1
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="candidate replay failed",
    ):
        subject._build_accounting_family_occurrence_row_axis_from_authenticated_topology_scan_v2(
            pages,
            changed_spec,
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            topology_candidates=candidates,
            prepared_topology_binding=bindings[0],
        )


def _f3_spec() -> dict:
    return json.loads(_F3_TOPOLOGY_PATH.read_text(encoding="utf-8"))


def _f3_hierarchy() -> dict:
    return json.loads(_F3_EVALUATION_PATH.read_text(encoding="utf-8"))["hierarchical_closure_spec"]


def _f3_pages(rows: list[tuple[str, str, str]]) -> list[dict[str, object]]:
    pages = _pages(rows)
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho vay các TCTD khác"
    return pages


def _f3_parent_frontier_pages(
    rows: list[tuple[str, str, str]],
) -> list[dict[str, object]]:
    pages = _f3_pages(rows)
    for line_index in (0, 3, 4):
        bbox = pages[0]["lines"][line_index]["bbox"]
        height = bbox[3] - bbox[1]
        bbox[1:4:2] = [155, 155 + height]
    pages[0]["lines"].insert(
        3,
        _line(999, "Đơn vị: Triệu đồng", "", [600, 75, 900, 95]),
    )
    _reindex_page_lines(pages[0]["lines"])

    def document_context_page(
        page_sequence: int, sample_base: int, *, with_reset: bool
    ) -> dict[str, object]:
        lines = [
            _line(sample_base, "31/12/2025", "", [600, 30, 700, 52]),
            _line(sample_base + 1, "31/12/2024", "", [800, 30, 900, 52]),
            _line(sample_base + 2, "Đơn vị: Triệu đồng", "", [600, 60, 900, 82]),
        ]
        if with_reset:
            lines.append(_line(sample_base + 3, "Cho vay khách hàng", "", [30, 100, 500, 122]))
        for ordinal, line in enumerate(lines):
            line["line_ordinal"] = ordinal
        return {"lines": lines, "page_sequence": page_sequence, "page_width": 1000}

    pages.extend(
        [
            document_context_page(2, 100, with_reset=True),
            document_context_page(3, 200, with_reset=False),
        ]
    )
    return pages


def _reindex_page_lines(lines: list[dict[str, object]]) -> None:
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal
        line["sample_id"] = f"sample-{ordinal + 1:09d}"
        line["crop_ref"] = {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        }


def _insert_wrapped_other(
    pages: list[dict[str, object]],
    *,
    prefix: str,
) -> None:
    lines = pages[0]["lines"]
    insert_at = 8
    top = 205
    wrapped = [
        _line(900, prefix, "", [45, top, 430, top + 20]),
        _line(901, "Khác", "", [47, top + 19, 180, top + 39]),
        _line(902, "7", "7", [610, top + 19, 700, top + 39]),
        _line(903, "6", "6", [810, top + 19, 900, top + 39]),
    ]
    lines[insert_at:insert_at] = wrapped
    _reindex_page_lines(lines)


def _build_f3(pages: list[dict[str, object]]) -> tuple[dict, dict]:
    spec = _f3_spec()
    topology_pages = row_v1._topology_pages(pages)
    scan = topology_v1.build_accounting_family_topology_scan_v1(topology_pages, spec)
    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = scan["regions"][0]
    effective = total_v1.project_accounting_family_coextensive_parent_total_region_v1(
        spec, scan, region
    )
    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        region,
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
    )
    return scan, axis


def _f3_column_context(axis: dict, pages: list[dict[str, object]]) -> dict:
    evaluation = json.loads(_F3_EVALUATION_PATH.read_text(encoding="utf-8"))
    return column_context_v1._build_accounting_family_column_context_from_authenticated_row_axis_v1(
        axis["row_axis"],
        pages,
        _f3_spec(),
        period_semantics=evaluation["period_semantics"],
        expected_lane_unit_kinds=evaluation["expected_lane_unit_kinds"],
    )


def _f3_structural_evidence(axis: dict) -> dict:
    return {
        "internal_unassigned_numeric_clusters": axis["internal_unassigned_numeric_clusters"],
        "numeric_sample_universe": axis["numeric_sample_universe"],
        "role_occurrences": axis["role_occurrences"],
        "row_axis": axis["row_axis"],
    }


def _f3_explicit_group_total_rows() -> list[tuple[str, str, str]]:
    return [
        ("Tiền gửi tại các TCTD khác", "150", "130"),
        ("Tiền gửi không kỳ hạn", "30", "20"),
        ("Bằng VND", "20", "10"),
        ("Bằng ngoại tệ", "10", "10"),
        ("Tiền gửi có kỳ hạn", "120", "110"),
        ("Bằng VND", "100", "90"),
        ("Bằng ngoại tệ", "20", "20"),
        ("Tổng tiền gửi tại các TCTD khác", "150", "130"),
        ("Cho vay các TCTD khác", "50", "40"),
        ("Bằng VND", "50", "40"),
        ("Tổng cho vay các TCTD khác", "50", "40"),
        ("Tổng tiền gửi và cho vay các TCTD khác", "200", "170"),
    ]


def test_f3_explicit_group_totals_bind_once_to_exact_nearest_parent_intervals() -> None:
    _scan, axis = _build_f3(_f3_pages(_f3_explicit_group_total_rows()))

    totals = [
        item
        for item in axis["role_occurrences"]
        if item["role"] in {"EXPLICIT_INTERBANK_DEPOSIT_TOTAL", "EXPLICIT_INTERBANK_LOAN_TOTAL"}
    ]
    assert [item["role"] for item in totals] == [
        "EXPLICIT_INTERBANK_DEPOSIT_TOTAL",
        "EXPLICIT_INTERBANK_LOAN_TOTAL",
    ]
    assert not any(item["role"].endswith("_TOTAL_AMBIGUOUS") for item in axis["role_occurrences"])
    assert [item["source_scope_binding"]["binding_kind"] for item in totals] == [
        "UNIQUE_EXACT_EXPLICIT_GROUP_TOTAL_INTERVAL",
        "UNIQUE_EXACT_EXPLICIT_GROUP_TOTAL_INTERVAL",
    ]
    assert [item["scope_owner_role"] for item in totals] == [
        "INTERBANK_DEPOSIT_GROUP",
        "INTERBANK_LOAN_GROUP",
    ]
    assert [
        item["source_scope_binding"]["geometry"]["anchor_occurrence_id"] for item in totals
    ] == [item["scope_owner_occurrence_id"] for item in totals]
    assert totals[0]["label_match"]["retrieval_role"] == (
        "EXPLICIT_INTERBANK_DEPOSIT_TOTAL_AMBIGUOUS"
    )
    assert totals[0]["label_match"]["retrieval_within_role"] is None
    assert totals[1]["label_match"]["retrieval_role"] == "EXPLICIT_INTERBANK_LOAN_TOTAL"
    assert totals[1]["label_match"]["retrieval_within_role"] == "INTERBANK_LOAN_GROUP"


def test_f3_contextual_explicit_total_receipt_binds_exact_parent_occurrence_id() -> None:
    _scan, axis = _build_f3(_f3_pages(_f3_explicit_group_total_rows()))
    loan_total = next(
        item for item in axis["role_occurrences"] if item["role"] == "EXPLICIT_INTERBANK_LOAN_TOTAL"
    )
    receipt = copy.deepcopy(loan_total["source_scope_binding"])
    receipt["geometry"]["anchor_occurrence_id"] = "aforav2:occurrence:" + "0" * 64
    material = copy.deepcopy(receipt)
    material.pop("binding_id")
    receipt["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(material)

    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="semantic matrix",
    ):
        subject._validate_source_scope_binding(
            receipt,
            label_match=loan_total["label_match"],
            role=loan_total["role"],
        )


def _extreme_margin_fixture_pages(
    *,
    candidate_bbox: list[int] | None = None,
    include_peers: bool = True,
    candidate_vietocr: str = "304",
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    bbox = candidate_bbox or [950, 290, 995, 310]
    stamp_lines = []
    if include_peers:
        stamp_lines.extend(
            [
                _line(900, "DẤU", "", [952, 270, 997, 289]),
                _line(901, "MỘC", "", [951, 311, 996, 331]),
            ]
        )
    stamp_lines.append(_line(902, candidate_vietocr, "506", bbox))
    pages[0]["lines"].extend(stamp_lines)
    _reindex_page_lines(pages[0]["lines"])
    return pages, stamp_lines


def _build_authenticated_extreme_margin_fixture(
    pages: list[dict[str, object]],
    stamp_lines: list[dict[str, object]],
    *,
    color: str,
    with_render: bool,
    with_topology_candidates: bool = True,
    render_colored_bboxes: list[tuple[list[int], str]] | None = None,
) -> tuple[dict, dict, dict, dict]:
    spec = _f3_spec()
    topology_pages = row_v1._topology_pages(pages)
    scan = topology_v1.build_accounting_family_topology_scan_v1(topology_pages, spec)
    candidates = candidates_v2.build_accounting_family_topology_candidates_v2(topology_pages, spec)
    region = candidates["regions"][0]
    binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        topology_pages, spec, candidates, region
    )
    snapshot, render = _snapshot_and_render(
        pages,
        [],
        colored_bboxes=(
            render_colored_bboxes
            if render_colored_bboxes is not None
            else [(line["bbox"], color) for line in stamp_lines]
        ),
    )
    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        region,
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=binding["effective_topology_region"],
        topology_candidates=candidates if with_topology_candidates else None,
        selected_snapshot=snapshot,
        render_snapshots=(render,) if with_render else (),
    )
    return scan, candidates, snapshot, axis


def _numeric_extreme_margin_stamp_fixture(
    *,
    candidate_vietocr: str = "1001",
    candidate_numeric: str = "6",
    candidate_bbox: list[int] | None = None,
    peer_count: int = 3,
    component_attack: str | None = None,
    color: str = "red",
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[tuple[list[int], str]]]:
    pages, stamp_lines = _extreme_margin_fixture_pages(
        include_peers=False,
        candidate_bbox=candidate_bbox or [950, 290, 995, 330],
        candidate_vietocr=candidate_vietocr,
    )
    candidate = stamp_lines[0]
    candidate["numeric_recognition"]["raw_prediction"] = candidate_numeric
    peers = [
        _line(910, "NHÁN", "", [952, 205, 997, 225]),
        _line(911, "TYIN", "", [951, 235, 996, 255]),
        _line(912, "MG", "", [952, 265, 997, 285]),
    ][:peer_count]
    pages[0]["lines"].extend(peers)
    stamp_lines = [*peers, candidate]
    _reindex_page_lines(pages[0]["lines"])
    colored = [
        ([956, 210, 990, 220], color),
        ([956, 240, 990, 250], color),
        ([956, 270, 990, 280], color),
    ][:peer_count]
    target = candidate["bbox"]
    center = (target[0] + target[2]) // 2
    if component_attack == "PARTIAL":
        colored.append(([center - 6, target[1] + 8, center + 6, target[3] - 8], color))
    elif component_attack == "DUPLICATE":
        colored.extend(
            [
                ([target[0] + 8, target[1], target[0] + 16, target[3] - 1], color),
                ([target[0] + 30, target[1], target[0] + 38, target[3] - 1], color),
            ]
        )
    else:
        colored.append(([center - 6, target[1], center + 6, target[3] - 1], color))
    return pages, stamp_lines, colored


def _extreme_right_vertical_stamp_v4_fixture(
    *,
    mode: str,
    include_peers: bool = True,
    candidate_bbox: list[int] | None = None,
    candidate_vietocr: str | None = None,
    candidate_numeric: str | None = None,
    peer_numeric: bool = False,
    margin_label: bool = False,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[tuple[list[int], str]]]:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    if mode == "CHROMATIC":
        bbox = candidate_bbox or [950, 180, 999, 380]
        candidate = _line(
            930,
            candidate_vietocr or "2",
            candidate_numeric or "20",
            bbox,
        )
        peers: list[dict[str, object]] = []
        component_left = bbox[0] + max(3, (bbox[2] - bbox[0]) // 5)
        component_right = bbox[2] - max(3, (bbox[2] - bbox[0]) // 5)
        component_height = max(8, (bbox[3] - bbox[1]) // 8)
        colored = [
            (
                [
                    component_left,
                    bbox[1] + 5,
                    component_right,
                    bbox[1] + 5 + component_height,
                ],
                "red",
            ),
            (
                [
                    component_left,
                    (bbox[1] + bbox[3] - component_height) // 2,
                    component_right,
                    (bbox[1] + bbox[3] + component_height) // 2,
                ],
                "red",
            ),
            (
                [
                    component_left,
                    bbox[3] - 5 - component_height,
                    component_right,
                    bbox[3] - 5,
                ],
                "red",
            ),
        ]
    elif mode == "CLIPPED":
        bbox = candidate_bbox or [970, 280, 1000, 340]
        candidate = _line(
            930,
            candidate_vietocr or "1",
            candidate_numeric or "1",
            bbox,
        )
        peers = (
            [
                _line(931, "N", "7" if peer_numeric else "N", [972, 350, 1000, 372]),
                _line(932, "di", "H", [972, 390, 1000, 412]),
                _line(933, "%", "F", [970, 430, 1000, 454]),
            ]
            if include_peers
            else []
        )
        component_left = bbox[0] + max(3, (bbox[2] - bbox[0]) // 4)
        component_right = bbox[2] - max(3, (bbox[2] - bbox[0]) // 5)
        component_height = max(6, (bbox[3] - bbox[1]) // 8)
        colored = [
            (
                [
                    component_left,
                    bbox[1] + 4,
                    component_right,
                    bbox[1] + 4 + component_height,
                ],
                "black",
            ),
            (
                [
                    component_left,
                    (bbox[1] + bbox[3] - component_height) // 2,
                    component_right,
                    (bbox[1] + bbox[3] + component_height) // 2,
                ],
                "black",
            ),
            (
                [
                    component_left,
                    bbox[3] - 4 - component_height,
                    component_right,
                    bbox[3] - 4,
                ],
                "black",
            ),
            *(
                [
                    ([978, 354, 994, 366], "black"),
                    ([978, 394, 994, 406], "black"),
                    ([978, 434, 994, 448], "black"),
                ]
                if include_peers
                else []
            ),
        ]
    elif mode == "FRAGMENTED":
        bbox = candidate_bbox or [950, 230, 995, 250]
        candidate = _line(
            930,
            candidate_vietocr or "180",
            candidate_numeric or "180",
            bbox,
        )
        peers = (
            [
                _line(931, "G Ty", "61", [950, 180, 995, 200]),
                _line(932, "NHIN", "H", [950, 205, 995, 225]),
                _line(933, "& YC", "& 10", [950, 255, 995, 275]),
                _line(934, "1 Nổ", "IN", [950, 280, 995, 300]),
                _line(935, "THỔ", "3H", [950, 305, 995, 325]),
            ]
            if include_peers
            else []
        )
        colored = [
            ([955, bbox[1] + 2, 963, bbox[3] - 2], "black"),
            ([968, bbox[1] + 2, 976, bbox[3] - 2], "black"),
            ([981, bbox[1] + 2, 989, bbox[3] - 2], "black"),
            *(
                [
                    ([955, 182, 963, 198], "black"),
                    ([968, 182, 976, 198], "black"),
                    ([981, 182, 989, 198], "black"),
                    ([960, 208, 985, 222], "black"),
                    ([960, 258, 985, 272], "black"),
                    ([960, 283, 985, 297], "black"),
                    ([960, 308, 985, 322], "black"),
                ]
                if include_peers
                else []
            ),
        ]
    else:
        raise AssertionError("unsupported vertical-stamp fixture mode")
    stamp_lines = [candidate, *peers]
    pages[0]["lines"].extend(stamp_lines)
    if margin_label:
        pages[0]["lines"].append(
            _line(934, "Nhãn tài chính", "", [925, bbox[1] + 10, 970, bbox[1] + 35])
        )
    _reindex_page_lines(pages[0]["lines"])
    return pages, stamp_lines, colored


def _clipped_right_edge_local_subtotal_pages(
    *,
    decoration_bbox: list[int] | None = None,
    decoration_numeric: str = "x",
    decoration_text: str = "x",
    extra_gap_lines: int = 0,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "80"),
            ("Cấp tín dụng cho các TCTD khác", "", ""),
            ("Bằng VND", "50", "40"),
            ("Trong đó: Chiết khấu, tái chiết khấu bằng VND", "30", "20"),
        ]
    )
    lines = pages[0]["lines"]
    next_ordinal = len(lines)
    for offset in range(extra_gap_lines):
        lines.append(
            _line(
                next_ordinal + offset,
                "ghi chú",
                "",
                [500, 410 + offset * 2, 575, 429 + offset * 2],
            )
        )
    decoration = _line(
        next_ordinal + extra_gap_lines,
        decoration_text,
        decoration_numeric,
        decoration_bbox or [985, 414, 999, 434],
    )
    lines.extend(
        [
            decoration,
            _line(next_ordinal + extra_gap_lines + 1, "50", "50", [610, 438, 700, 458]),
            _line(next_ordinal + extra_gap_lines + 2, "40", "40", [810, 438, 900, 458]),
            _line(
                next_ordinal + extra_gap_lines + 3,
                "Mức lãi suất",
                "",
                [45, 490, 430, 510],
            ),
        ]
    )
    _reindex_page_lines(lines)
    return pages, decoration


def _build_authenticated_clipped_right_edge_local_subtotal(
    pages: list[dict[str, object]],
    decoration: dict[str, object],
    *,
    with_render: bool = True,
) -> tuple[dict, dict, dict, dict, dict, dict]:
    spec = _f3_spec()
    topology_pages = row_v1._topology_pages(pages)
    scan = topology_v1.build_accounting_family_topology_scan_v1(topology_pages, spec)
    candidates = candidates_v2.build_accounting_family_topology_candidates_v2(topology_pages, spec)
    region = candidates["regions"][0]
    binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        topology_pages, spec, candidates, region
    )
    snapshot, render = _snapshot_and_render(
        pages,
        [],
        colored_bboxes=[(decoration["bbox"], "black")],
    )
    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        region,
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=binding["effective_topology_region"],
        topology_candidates=candidates,
        selected_snapshot=snapshot,
        render_snapshots=(render,) if with_render else (),
    )
    return scan, candidates, binding, snapshot, render, axis


def _coherently_rehash_nonnumeric_decoration_axis(axis: dict) -> None:
    evidence = next(
        item
        for item in axis["authenticated_extreme_margin_furniture_evidence"]
        if item["status"] == subject._EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_STATUS
    )
    evidence_material = copy.deepcopy(evidence)
    evidence_material.pop("evidence_id")
    evidence["evidence_id"] = "aforav2:extreme-margin-furniture:" + canonical_json_sha256_v1(
        evidence_material
    )
    _coherently_rehash_occurrence(axis)


def test_clipped_right_edge_nonnumeric_decoration_binds_exact_local_subtotal_seam() -> None:
    pages, decoration = _clipped_right_edge_local_subtotal_pages()
    scan, candidates, binding, snapshot, render, axis = (
        _build_authenticated_clipped_right_edge_local_subtotal(pages, decoration)
    )

    decorations = [
        evidence
        for evidence in axis["authenticated_extreme_margin_furniture_evidence"]
        if evidence["status"] == subject._EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_STATUS
    ]
    assert len(decorations) == 1
    evidence = decorations[0]
    assert evidence["source_record"]["line_ordinal"] == decoration["line_ordinal"]
    assert evidence["sample_id"] not in {
        sample["sample_id"] for sample in axis["numeric_sample_universe"]
    }
    assert any(
        occurrence["occurrence_id"] in evidence["structural_gap_anchor_occurrence_ids"]
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "INTERBANK_LOAN_GROUP"
        and occurrence["has_bound_value_row"] is False
    )

    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    local = next(
        equation
        for equation in closure["equations"]["local"]
        if equation["result_role"] == "INTERBANK_LOAN_GROUP"
    )
    assert local["status"] == "LOCAL_TRAILING_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"
    receipt = local["local_trailing_subgroup_subtotal_receipt"]
    assert receipt["intervening_source_line_indices"] == [decoration["line_ordinal"]]
    assert receipt["intervening_furniture_evidence_ids"] == [evidence["evidence_id"]]
    assert receipt["extreme_margin_furniture_evidence_sha256"] == canonical_json_sha256_v1(
        axis["authenticated_extreme_margin_furniture_evidence"]
    )
    assert not any(
        record["source_record"].get("evidence_id") == evidence["evidence_id"]
        for record in closure["coverage_receipt"]
    )
    assert (
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            axis,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=binding["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )
        == axis
    )
    assert (
        closure_v2.validate_accounting_scoped_hierarchical_table_closure_replay_v2(
            closure, axis, _f3_spec(), _f3_hierarchy()
        )
        == closure
    )


@pytest.mark.parametrize(
    ("fixture_kwargs", "with_render"),
    [
        ({"decoration_bbox": [900, 414, 914, 434]}, True),
        ({"decoration_text": "Khác", "decoration_numeric": "Khác"}, True),
        ({"decoration_text": "1", "decoration_numeric": "1"}, True),
        ({"decoration_text": "unknown", "decoration_numeric": ""}, True),
        ({"extra_gap_lines": 4}, True),
        ({}, False),
    ],
    ids=["not-edge", "semantic-role", "numeric", "long-label", "too-far", "no-render"],
)
def test_clipped_right_edge_nonnumeric_decoration_rejects_unsealed_sources(
    fixture_kwargs: dict[str, object], with_render: bool
) -> None:
    pages, decoration = _clipped_right_edge_local_subtotal_pages(**fixture_kwargs)
    *_authority, axis = _build_authenticated_clipped_right_edge_local_subtotal(
        pages, decoration, with_render=with_render
    )

    assert not any(
        evidence["status"] == subject._EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_STATUS
        for evidence in axis["authenticated_extreme_margin_furniture_evidence"]
    )
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert not any(
        equation["status"] == "LOCAL_TRAILING_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"
        for equation in closure["equations"]["local"]
    )


def test_clipped_right_edge_decoration_coherent_source_and_receipt_tamper_rejects() -> None:
    pages, decoration = _clipped_right_edge_local_subtotal_pages()
    scan, candidates, binding, snapshot, render, axis = (
        _build_authenticated_clipped_right_edge_local_subtotal(pages, decoration)
    )
    attacked_axis = copy.deepcopy(axis)
    evidence = next(
        item
        for item in attacked_axis["authenticated_extreme_margin_furniture_evidence"]
        if item["status"] == subject._EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_STATUS
    )
    for source in (
        evidence["source_record"],
        evidence["candidate_crop_proof"]["source_line_record"],
        next(
            line
            for line in evidence["margin_band"]["source_line_axis"]
            if line["sample_id"] == evidence["sample_id"]
        ),
    ):
        source["vietocr_text"] = "q"
        source["numeric_raw_prediction"] = "q"
    evidence["margin_band"]["source_line_axis_sha256"] = canonical_json_sha256_v1(
        evidence["margin_band"]["source_line_axis"]
    )
    _coherently_rehash_nonnumeric_decoration_axis(attacked_axis)
    assert subject._validate_result(attacked_axis) == attacked_axis
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="does not replay exactly",
    ):
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            attacked_axis,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=binding["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )

    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    attacked_closure = copy.deepcopy(closure)
    local = next(
        equation
        for equation in attacked_closure["equations"]["local"]
        if equation["result_role"] == "INTERBANK_LOAN_GROUP"
    )
    receipt = local["local_trailing_subgroup_subtotal_receipt"]
    receipt["intervening_source_line_indices"] = [decoration["line_ordinal"] + 1]
    receipt_material = copy.deepcopy(receipt)
    receipt_material.pop("receipt_id")
    receipt["receipt_id"] = "ashtcv2:local-trailing-subgroup-subtotal:" + (
        canonical_json_sha256_v1(receipt_material)
    )
    _coherently_rehash_scoped_closure(attacked_closure)
    with pytest.raises(
        closure_v2.AccountingScopedHierarchicalTableClosureV2Error,
        match="local trailing subgroup",
    ):
        closure_v2.validate_accounting_scoped_hierarchical_table_closure_replay_v2(
            attacked_closure, axis, _f3_spec(), _f3_hierarchy()
        )


def _printed_note_reference_fixture_pages() -> tuple[list[dict[str, object]], list[list[int]]]:
    lines = [
        _line(0, "Thuyết minh", "Thuyết minh", [480, 10, 570, 36]),
        _line(1, "Khoản mục trước", "", [45, 48, 430, 68]),
        _line(2, "5", "5", [520, 48, 550, 68]),
        _line(3, "90", "90", [610, 48, 700, 68]),
        _line(4, "80", "80", [810, 48, 900, 68]),
        _line(5, "Tiền gửi và cho vay các TCTD khác", "", [45, 82, 430, 104]),
        _line(6, "6", "6", [520, 82, 550, 104]),
        _line(7, "150", "150", [610, 82, 700, 104]),
        _line(8, "130", "130", [810, 82, 900, 104]),
        _line(9, "Tiền gửi tại các TCTD khác", "", [45, 116, 430, 136]),
        _line(10, "100", "100", [610, 116, 700, 136]),
        _line(11, "90", "90", [810, 116, 900, 136]),
        _line(12, "Cho vay các TCTD khác", "", [45, 148, 430, 168]),
        _line(13, "50", "50", [610, 148, 700, 168]),
        _line(14, "40", "40", [810, 148, 900, 168]),
        _line(15, "Chứng khoán kinh doanh", "", [45, 180, 430, 200]),
        _line(16, "Khoản mục sau", "", [45, 214, 430, 234]),
        _line(17, "7", "7", [520, 214, 550, 234]),
        _line(18, "70", "70", [610, 214, 700, 234]),
        _line(19, "60", "60", [810, 214, 900, 234]),
    ]
    return [{"lines": lines, "page_sequence": 1, "page_width": 1000}], [
        lines[index]["bbox"] for index in (0, 2, 6, 17)
    ]


def _dotted_printed_note_reference_fixture_pages() -> tuple[
    list[dict[str, object]], list[list[int]]
]:
    lines = [
        _line(0, "Thuyết minh", "Thuyết minh", [480, 10, 570, 36]),
        _line(1, "Khoản mục trước", "", [45, 48, 430, 68]),
        _line(2, "4", "4", [520, 48, 550, 68]),
        _line(3, "90", "90", [610, 48, 700, 68]),
        _line(4, "80", "80", [810, 48, 900, 68]),
        _line(5, "Tiền gửi và cho vay các TCTD khác", "", [45, 82, 430, 104]),
        _line(6, "5", "5", [520, 82, 550, 104]),
        _line(7, "150", "150", [610, 82, 700, 104]),
        _line(8, "130", "130", [810, 82, 900, 104]),
        _line(9, "Tiền gửi tại các TCTD khác", "", [45, 116, 430, 138]),
        _line(10, "5.1", "5.1", [500, 116, 560, 138]),
        _line(11, "100", "100", [610, 116, 700, 138]),
        _line(12, "90", "90", [810, 116, 900, 138]),
        _line(13, "Cho vay các TCTD khác", "", [45, 150, 430, 172]),
        _line(14, "5.2", "5.2", [500, 150, 560, 172]),
        _line(15, "50", "50", [610, 150, 700, 172]),
        _line(16, "40", "40", [810, 150, 900, 172]),
        _line(17, "Chứng khoán kinh doanh", "", [45, 184, 430, 206]),
        _line(18, "Khoản mục sau", "", [45, 218, 430, 240]),
        _line(19, "6", "6", [520, 218, 550, 240]),
        _line(20, "70", "70", [610, 218, 700, 240]),
        _line(21, "60", "60", [810, 218, 900, 240]),
    ]
    return [{"lines": lines, "page_sequence": 1, "page_width": 1000}], [
        lines[index]["bbox"] for index in (0, 2, 6, 10, 14, 19)
    ]


def _build_authenticated_printed_note_reference_fixture(
    pages: list[dict[str, object]],
    ink_bboxes: list[list[int]],
    *,
    with_render: bool = True,
) -> tuple[dict, dict, dict, dict, dict]:
    spec = _f3_spec()
    topology_pages = row_v1._topology_pages(pages)
    scan = topology_v1.build_accounting_family_topology_scan_v1(topology_pages, spec)
    candidates = candidates_v2.build_accounting_family_topology_candidates_v2(topology_pages, spec)
    assert len(candidates["regions"]) == 1
    region = candidates["regions"][0]
    binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        topology_pages, spec, candidates, region
    )
    snapshot, render = _snapshot_and_render(pages, ink_bboxes)
    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        region,
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=binding["effective_topology_region"],
        topology_candidates=candidates,
        selected_snapshot=snapshot,
        render_snapshots=(render,) if with_render else (),
    )
    return scan, candidates, binding, snapshot, axis


def _coherently_rehash_furniture_axis(axis: dict) -> None:
    evidence = axis["authenticated_extreme_margin_furniture_evidence"][0]
    evidence_material = copy.deepcopy(evidence)
    evidence_material.pop("evidence_id")
    prefix = (
        "aforav2:printed-note-reference-v4:"
        if evidence["status"] == subject._PRINTED_NOTE_REFERENCE_FURNITURE_V4_STATUS
        else "aforav2:extreme-right-vertical-stamp-v4:"
        if evidence["status"] == subject._EXTREME_MARGIN_VERTICAL_STAMP_V4_STATUS
        else "aforav2:extreme-margin-furniture:"
    )
    evidence["evidence_id"] = prefix + canonical_json_sha256_v1(evidence_material)
    sample = next(
        item
        for item in axis["numeric_sample_universe"]
        if item["sample_id"] == evidence["sample_id"]
    )
    sample["owner_id"] = evidence["evidence_id"]
    _coherently_rehash_occurrence(axis)


def test_persisted_v3_note_evidence_and_default_legacy_replay_remain_byte_stable() -> None:
    pages, ink_bboxes = _printed_note_reference_fixture_pages()
    scan, candidates, binding, snapshot, axis = _build_authenticated_printed_note_reference_fixture(
        pages, ink_bboxes
    )

    assert axis["status"] == (
        "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
    )
    assert axis["internal_unassigned_numeric_clusters"] == []
    furniture = axis["authenticated_extreme_margin_furniture_evidence"]
    assert len(furniture) == 1
    evidence = furniture[0]
    assert evidence["status"] == subject._PRINTED_NOTE_REFERENCE_FURNITURE_V3_STATUS
    assert evidence["geometry"]["candidate_note_value"] == 6
    assert [row["note_value"] for row in evidence["note_reference_axis"]] == [5, 6, 7]
    assert "binding_kind" not in evidence["semantic_row_binding"]
    assert canonical_json_sha256_v1(evidence) == (
        "ba4d44e61f80c2ef6089833ce1e1c40a9961f11acfa1f9fa8213165e4c1ebdac"
    )
    candidate = next(
        sample
        for sample in axis["numeric_sample_universe"]
        if sample["sample_id"] == evidence["sample_id"]
    )
    assert candidate["owner_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
    assert candidate["owner_id"] == evidence["evidence_id"]
    assert (
        sum(
            sample["sample_id"] == evidence["sample_id"]
            for sample in axis["numeric_sample_universe"]
        )
        == 1
    )

    render = _snapshot_and_render(pages, ink_bboxes)[1]
    assert (
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            axis,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=binding["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )
        == axis
    )

    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    receipts = [
        receipt
        for receipt in closure["coverage_receipt"]
        if receipt["row_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
    ]
    assert len(receipts) == 1
    assert receipts[0]["sample_ids"] == [evidence["sample_id"]]
    assert receipts[0]["source_record"] == evidence
    assert (
        closure_v2.validate_accounting_scoped_hierarchical_table_closure_replay_v2(
            closure, axis, _f3_spec(), _f3_hierarchy()
        )
        == closure
    )

    for mode in ("DELETE", "DUPLICATE"):
        attacked = copy.deepcopy(closure)
        if mode == "DELETE":
            attacked["coverage_receipt"] = [
                receipt
                for receipt in attacked["coverage_receipt"]
                if receipt["row_kind"] != "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
            ]
        else:
            duplicate = copy.deepcopy(receipts[0])
            duplicate["coverage_id"] += ":duplicate"
            attacked["coverage_receipt"].append(duplicate)
        _coherently_rehash_scoped_closure(attacked)
        with pytest.raises(
            closure_v2.AccountingScopedHierarchicalTableClosureV2Error,
            match="exactly one owning coverage receipt",
        ):
            closure_v2._validate_result(attacked)


def test_v4_dotted_note_column_projects_parent_and_role_rows_with_one_owner_each() -> None:
    pages, ink_bboxes = _dotted_printed_note_reference_fixture_pages()
    scan, candidates, binding, snapshot, axis = _build_authenticated_printed_note_reference_fixture(
        pages, ink_bboxes
    )

    furniture = axis["authenticated_extreme_margin_furniture_evidence"]
    assert all(
        item["status"] == subject._PRINTED_NOTE_REFERENCE_FURNITURE_V4_STATUS for item in furniture
    )
    assert all(
        item["evidence_id"].startswith("aforav2:printed-note-reference-v4:") for item in furniture
    )
    assert [item["geometry"]["candidate_note_reference"] for item in furniture] == [
        "5",
        "5.1",
        "5.2",
    ]
    assert axis["row_axis"]["column_grids"][0]["column_centers"] == [655.0, 855.0]
    assert all(len(row["values"]) == 2 for row in axis["row_axis"]["rows"])
    for evidence in furniture:
        owned = [
            sample
            for sample in axis["numeric_sample_universe"]
            if sample["sample_id"] == evidence["sample_id"]
        ]
        assert len(owned) == 1
        assert owned[0]["owner_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
        assert owned[0]["owner_id"] == evidence["evidence_id"]

    render = _snapshot_and_render(pages, ink_bboxes)[1]
    assert (
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            axis,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=binding["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )
        == axis
    )

    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    receipts = [
        receipt
        for receipt in closure["coverage_receipt"]
        if receipt["row_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
    ]
    assert len(receipts) == 3
    assert {receipt["sample_ids"][0] for receipt in receipts} == {
        evidence["sample_id"] for evidence in furniture
    }


def test_v4_dotted_note_evidence_coherent_rehash_still_fails_closed() -> None:
    pages, ink_bboxes = _dotted_printed_note_reference_fixture_pages()
    _scan, _candidates, _binding, _snapshot, axis = (
        _build_authenticated_printed_note_reference_fixture(pages, ink_bboxes)
    )
    attacked = copy.deepcopy(axis)
    attacked["authenticated_extreme_margin_furniture_evidence"][0]["geometry"][
        "candidate_note_reference"
    ] = "5.3"
    _coherently_rehash_furniture_axis(attacked)

    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="candidate source or pixel binding drifted",
    ):
        subject._validate_result(attacked)


def test_printed_note_reference_never_reowns_decimal_financial_money() -> None:
    pages, ink_bboxes = _printed_note_reference_fixture_pages()
    decimal = pages[0]["lines"][7]
    decimal["vietocr_text"] = "6.5"
    decimal["numeric_recognition"]["raw_prediction"] = "6.5"
    _scan, _candidates, _binding, _snapshot, axis = (
        _build_authenticated_printed_note_reference_fixture(pages, ink_bboxes)
    )

    evidence = axis["authenticated_extreme_margin_furniture_evidence"]
    assert len(evidence) == 1
    assert evidence[0]["geometry"]["candidate_note_value"] == 6
    decimal_sample = next(
        sample
        for sample in axis["numeric_sample_universe"]
        if sample["sample_id"] == decimal["sample_id"]
    )
    assert decimal_sample["parsed_token"]["scale"] == 1
    assert decimal_sample["owner_kind"] == "ROLE_OCCURRENCE"


@pytest.mark.parametrize(
    "attack",
    [
        "MISSING_HEADER",
        "WRONG_HEADER_CHANNEL",
        "DUPLICATE_HEADER",
        "DUPLICATE_NOTE_REFERENCE",
        "DUPLICATE_NOTE_COLUMN",
        "INCOMPLETE_FINANCIAL_LANES",
        "CONFLICTING_LABEL",
        "CONFLICTING_FINANCIAL_LANE",
        "NO_RENDER",
    ],
)
def test_printed_note_reference_fails_closed_without_every_gate(attack: str) -> None:
    pages, ink_bboxes = _printed_note_reference_fixture_pages()
    lines = pages[0]["lines"]
    with_render = attack != "NO_RENDER"
    if attack == "MISSING_HEADER":
        lines[0]["vietocr_text"] = "Ghi chú"
        lines[0]["numeric_recognition"]["raw_prediction"] = "Ghi chú"
    elif attack == "WRONG_HEADER_CHANNEL":
        lines[0]["numeric_recognition"]["raw_prediction"] = "Thuyết min"
    elif attack == "DUPLICATE_HEADER":
        lines.append(_line(900, "Thuyết minh", "Thuyết minh", [480, 250, 570, 276]))
    elif attack == "DUPLICATE_NOTE_REFERENCE":
        lines[17]["vietocr_text"] = "5"
        lines[17]["numeric_recognition"]["raw_prediction"] = "5"
    elif attack == "DUPLICATE_NOTE_COLUMN":
        lines.append(_line(900, "6", "6", [552, 82, 568, 104]))
    elif attack == "INCOMPLETE_FINANCIAL_LANES":
        lines[18]["vietocr_text"] = "missing"
        lines[18]["numeric_recognition"]["raw_prediction"] = "missing"
    elif attack == "CONFLICTING_LABEL":
        lines.insert(6, _line(900, "khác", "khác", [440, 82, 472, 104]))
    elif attack == "CONFLICTING_FINANCIAL_LANE":
        lines.append(_line(900, "151", "151", [615, 82, 695, 104]))
    _reindex_page_lines(lines)

    _scan, _candidates, _binding, _snapshot, axis = (
        _build_authenticated_printed_note_reference_fixture(
            pages, ink_bboxes, with_render=with_render
        )
    )
    assert axis["authenticated_extreme_margin_furniture_evidence"] == []
    candidate_id = next(line["sample_id"] for line in lines if line["bbox"] == [520, 82, 550, 104])
    assert any(
        candidate_id in cluster["sample_ids"]
        for cluster in axis["internal_unassigned_numeric_clusters"]
    )
    if attack == "NO_RENDER":
        assert axis["unresolved_reasons"][-1] == (
            "EXTREME_MARGIN_ANNOTATION_RENDER_REQUIRED:PAGE_SEQUENCE:1"
        )


@pytest.mark.parametrize(
    "attack",
    [
        "SOURCE_SAMPLE",
        "SOURCE_BBOX",
        "HEADER_SOURCE",
        "WRONG_ROW_PARENT",
        "WRONG_PAGE",
        "CROSS_CROP",
    ],
)
def test_printed_note_reference_coherent_evidence_tamper_rejects(attack: str) -> None:
    pages, ink_bboxes = _printed_note_reference_fixture_pages()
    _scan, _candidates, _binding, _snapshot, axis = (
        _build_authenticated_printed_note_reference_fixture(pages, ink_bboxes)
    )
    attacked = copy.deepcopy(axis)
    evidence = attacked["authenticated_extreme_margin_furniture_evidence"][0]
    if attack == "SOURCE_SAMPLE":
        evidence["source_record"]["sample_id"] = "forged-sample"
    elif attack == "SOURCE_BBOX":
        evidence["source_record"]["bbox"][0] += 1
    elif attack == "HEADER_SOURCE":
        header = evidence["header_proof"]
        header["source_line_axis"][0]["vietocr_text"] = "Ghi chú"
        header["crop_proofs"][0]["source_line_record"]["vietocr_text"] = "Ghi chú"
        header["source_line_axis_sha256"] = canonical_json_sha256_v1(header["source_line_axis"])
    elif attack == "WRONG_ROW_PARENT":
        semantic = evidence["semantic_row_binding"]
        other = next(
            row
            for row in attacked["row_axis"]["rows"]
            if row["label_match"]["occurrence_id"] != semantic["occurrence_id"]
        )
        semantic["occurrence_id"] = other["label_match"]["occurrence_id"]
        semantic["role"] = other["role"]
        semantic["source_record"] = copy.deepcopy(other)
    elif attack == "WRONG_PAGE":
        evidence["page_sequence"] = 2
    elif attack == "CROSS_CROP":
        evidence["candidate_crop_proof"] = copy.deepcopy(
            evidence["note_reference_axis"][0]["note_crop_proof"]
        )
    _coherently_rehash_furniture_axis(attacked)

    with pytest.raises(subject.AccountingFamilyOccurrenceRowAxisV2Error):
        subject._validate_result(attacked)


def test_printed_note_reference_pixel_hash_tamper_only_fails_public_replay() -> None:
    pages, ink_bboxes = _printed_note_reference_fixture_pages()
    scan, candidates, binding, snapshot, axis = _build_authenticated_printed_note_reference_fixture(
        pages, ink_bboxes
    )
    attacked = copy.deepcopy(axis)
    evidence = attacked["authenticated_extreme_margin_furniture_evidence"][0]
    evidence["candidate_crop_proof"]["exact_bbox_rgb_sha256"] = "0" * 64
    candidate_row = next(
        row
        for row in evidence["note_reference_axis"]
        if row["source_line_record"]["sample_id"] == evidence["sample_id"]
    )
    candidate_row["note_crop_proof"]["exact_bbox_rgb_sha256"] = "0" * 64
    _coherently_rehash_furniture_axis(attacked)
    assert subject._validate_result(attacked) == attacked

    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="does not replay exactly",
    ):
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            attacked,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=binding["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(_snapshot_and_render(pages, ink_bboxes)[1],),
        )


def _coherently_rehash_scoped_closure(closure: dict) -> None:
    closure["metrics"] = closure_v2._metrics(
        closure["resolved_roles"],
        closure["equations"]["global"],
        closure["equations"]["local"],
        closure["coverage_receipt"],
        closure["unresolved_reasons"],
    )
    material = copy.deepcopy(closure)
    material.pop("closure_id")
    closure["closure_id"] = "ashtcv2:closure:" + canonical_json_sha256_v1(material)


def test_authenticated_extreme_margin_chromatic_furniture_keeps_one_owned_sample() -> None:
    pages, stamp_lines = _extreme_margin_fixture_pages()
    scan, candidates, snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages, stamp_lines, color="red", with_render=True
    )

    assert axis["status"] == (
        "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
    )
    assert axis["internal_unassigned_numeric_clusters"] == []
    assert len(axis["authenticated_extreme_margin_furniture_evidence"]) == 1
    evidence = axis["authenticated_extreme_margin_furniture_evidence"][0]
    sample = next(
        item
        for item in axis["numeric_sample_universe"]
        if item["sample_id"] == evidence["sample_id"]
    )
    assert sample["owner_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
    assert sample["owner_id"] == evidence["evidence_id"]
    assert evidence["topology_candidates_id"] == candidates["result_id"]
    assert evidence["margin_band"]["qualifying_peer_line_ordinals"] == sorted(
        line["line_ordinal"] for line in stamp_lines if line["vietocr_text"] != "304"
    )
    assert evidence["candidate_crop_proof"]["chromatic_ink_pixel_count"] * 3 >= (
        evidence["candidate_crop_proof"]["ink_pixel_count"] * 2
    )
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    furniture_receipt = next(
        item
        for item in closure["coverage_receipt"]
        if item["row_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
    )
    assert furniture_receipt["sample_ids"] == [evidence["sample_id"]]
    assert furniture_receipt["source_record"] == evidence
    assert closure["metrics"]["source_only_numeric_sample_count"] == 0
    deleted = copy.deepcopy(closure)
    deleted["coverage_receipt"] = [
        item
        for item in deleted["coverage_receipt"]
        if item["row_kind"] != "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
    ]
    _coherently_rehash_scoped_closure(deleted)
    with pytest.raises(
        closure_v2.AccountingScopedHierarchicalTableClosureV2Error,
        match="exactly one owning coverage receipt",
    ):
        closure_v2._validate_result(deleted)

    duplicated = copy.deepcopy(closure)
    duplicate_receipt = copy.deepcopy(furniture_receipt)
    duplicate_receipt["coverage_id"] += ":duplicate"
    duplicated["coverage_receipt"].append(duplicate_receipt)
    _coherently_rehash_scoped_closure(duplicated)
    with pytest.raises(
        closure_v2.AccountingScopedHierarchicalTableClosureV2Error,
        match="exactly one owning coverage receipt",
    ):
        closure_v2._validate_result(duplicated)

    swapped = copy.deepcopy(closure)
    swapped_receipt = next(
        item
        for item in swapped["coverage_receipt"]
        if item["row_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
    )
    swapped_receipt["sample_ids"] = [
        next(
            item["sample_id"]
            for item in swapped["numeric_sample_universe"]
            if item["owner_kind"] == "ROLE_OCCURRENCE"
        )
    ]
    _coherently_rehash_scoped_closure(swapped)
    with pytest.raises(
        closure_v2.AccountingScopedHierarchicalTableClosureV2Error,
        match="furniture receipt differs|visible occurrence coverage receipt drifted",
    ):
        closure_v2._validate_result(swapped)
    assert (
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            axis,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=candidates_v2.bind_accounting_family_topology_candidate_v2(
                row_v1._topology_pages(pages),
                _f3_spec(),
                candidates,
                candidates["regions"][0],
            )["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(
                _snapshot_and_render(
                    pages,
                    [],
                    colored_bboxes=[(line["bbox"], "red") for line in stamp_lines],
                )[1],
            ),
        )
        == axis
    )


def test_extreme_margin_v2_connected_stamp_accepts_separated_label_and_replays() -> None:
    pages, stamp_lines = _extreme_margin_fixture_pages(candidate_vietocr="soom")
    pages[0]["lines"].append(_line(903, "Lãi suất năm", "", [700, 290, 850, 310]))
    _reindex_page_lines(pages[0]["lines"])
    scan, candidates, snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages, stamp_lines, color="red", with_render=True
    )

    assert axis["internal_unassigned_numeric_clusters"] == []
    evidence = axis["authenticated_extreme_margin_furniture_evidence"][0]
    assert evidence["status"] == subject._EXTREME_MARGIN_FURNITURE_V2_STATUS
    assert evidence["geometry"]["margin_boundary"] == 939
    assert evidence["label_collision_proof"]["status"] == ("EXACT_MARGIN_SEPARATED_SAME_ROW_LABELS")
    assert evidence["label_collision_proof"]["maximum_label_right"] == 850
    proof = evidence["expanded_component_proof"]
    component = proof["component_axis"][proof["qualifying_component_ordinal"]]
    assert proof["qualifying_component_count"] == 1
    assert component["clear_extent_above_center"] >= proof["minimum_side_extent_pixels"]
    assert component["clear_extent_below_center"] >= proof["minimum_side_extent_pixels"]
    assert (
        component["chromatic_original_ink_pixel_count"] * 2
        >= (component["original_ink_pixel_count"])
    )
    sample = next(
        item
        for item in axis["numeric_sample_universe"]
        if item["sample_id"] == evidence["sample_id"]
    )
    assert sample["owner_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
    assert sample["owner_id"] == evidence["evidence_id"]
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    assert (
        len(
            [
                item
                for item in closure["coverage_receipt"]
                if item["row_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
                and item["sample_ids"] == [evidence["sample_id"]]
            ]
        )
        == 1
    )
    render = _snapshot_and_render(
        pages,
        [],
        colored_bboxes=[(line["bbox"], "red") for line in stamp_lines],
    )[1]
    binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        row_v1._topology_pages(pages),
        _f3_spec(),
        candidates,
        candidates["regions"][0],
    )
    assert (
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            axis,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=binding["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )
        == axis
    )


def test_extreme_margin_v2_numeric_rotated_stamp_requires_exact_pixels_and_replays() -> None:
    pages, stamp_lines, colored = _numeric_extreme_margin_stamp_fixture()
    scan, candidates, snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages,
        stamp_lines,
        color="red",
        with_render=True,
        render_colored_bboxes=colored,
    )

    assert axis["internal_unassigned_numeric_clusters"] == []
    evidence = axis["authenticated_extreme_margin_furniture_evidence"][0]
    assert evidence["status"] == subject._EXTREME_MARGIN_FURNITURE_V2_STATUS
    assert len(evidence["peer_crop_proofs"]) == 3
    assert evidence["candidate_crop_proof"]["chromatic_ink_pixel_count"] * 4 >= (
        evidence["candidate_crop_proof"]["ink_pixel_count"] * 3
    )
    proof = evidence["expanded_component_proof"]
    component = proof["component_axis"][proof["qualifying_component_ordinal"]]
    assert proof["qualifying_component_count"] == 1
    assert component["bbox"][1] <= evidence["geometry"]["candidate_bbox"][1]
    assert component["bbox"][3] >= evidence["geometry"]["candidate_bbox"][3]
    assert component["target_overlap_ink_pixel_count"] * 4 >= (
        evidence["candidate_crop_proof"]["ink_pixel_count"] * 3
    )
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    render = _snapshot_and_render(pages, [], colored_bboxes=colored)[1]
    binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        row_v1._topology_pages(pages),
        _f3_spec(),
        candidates,
        candidates["regions"][0],
    )
    assert (
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            axis,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=binding["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )
        == axis
    )


@pytest.mark.parametrize(
    ("mode", "expected_mode", "expected_peer_count", "expected_owned_count"),
    [
        (
            "CHROMATIC",
            subject._EXTREME_MARGIN_VERTICAL_STAMP_V4_CHROMATIC_MODE,
            0,
            1,
        ),
        (
            "CLIPPED",
            subject._EXTREME_MARGIN_VERTICAL_STAMP_V4_CLIPPED_MODE,
            3,
            1,
        ),
        (
            "FRAGMENTED",
            subject._EXTREME_MARGIN_VERTICAL_STAMP_V4_FRAGMENTED_MODE,
            5,
            2,
        ),
    ],
)
def test_extreme_right_vertical_stamp_v4_owns_one_sample_and_publicly_replays(
    mode: str,
    expected_mode: str,
    expected_peer_count: int,
    expected_owned_count: int,
) -> None:
    pages, stamp_lines, colored = _extreme_right_vertical_stamp_v4_fixture(mode=mode)
    scan, candidates, snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages,
        stamp_lines,
        color="black",
        with_render=True,
        render_colored_bboxes=colored,
    )

    assert axis["internal_unassigned_numeric_clusters"] == []
    evidence = axis["authenticated_extreme_margin_furniture_evidence"]
    assert len(evidence) == expected_owned_count
    for stamp in evidence:
        assert stamp["status"] == subject._EXTREME_MARGIN_VERTICAL_STAMP_V4_STATUS
        assert stamp["geometry"]["stamp_mode"] == expected_mode
        assert len(stamp["peer_crop_proofs"]) == expected_peer_count
        component_proof = stamp["component_peer_proof"]
        assert component_proof["qualifying_component_count"] >= 3
        assert component_proof["qualifying_vertical_span"] * 4 >= (
            stamp["geometry"]["candidate_height"] * 3
        )
    owned = [
        sample
        for sample in axis["numeric_sample_universe"]
        if sample["owner_kind"] == subject._EXTREME_MARGIN_FURNITURE_OWNER_KIND
    ]
    assert len(owned) == expected_owned_count
    assert {(sample["sample_id"], sample["owner_id"]) for sample in owned} == {
        (stamp["sample_id"], stamp["evidence_id"]) for stamp in evidence
    }
    if mode == "FRAGMENTED":
        assert axis["row_axis"]["column_grids"][0]["column_centers"] == [655.0, 855.0]
        assert {stamp["source_record"]["raw_prediction"] for stamp in evidence} == {"61", "180"}
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    for stamp in evidence:
        assert (
            len(
                [
                    receipt
                    for receipt in closure["coverage_receipt"]
                    if receipt["row_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
                    and receipt["sample_ids"] == [stamp["sample_id"]]
                ]
            )
            == 1
        )
    duplicated_closure = copy.deepcopy(closure)
    furniture_receipt = next(
        receipt
        for receipt in duplicated_closure["coverage_receipt"]
        if receipt["row_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
    )
    duplicate_receipt = copy.deepcopy(furniture_receipt)
    duplicate_receipt["coverage_id"] += ":duplicate"
    duplicated_closure["coverage_receipt"].append(duplicate_receipt)
    _coherently_rehash_scoped_closure(duplicated_closure)
    with pytest.raises(
        closure_v2.AccountingScopedHierarchicalTableClosureV2Error,
        match="exactly one owning coverage receipt",
    ):
        closure_v2._validate_result(duplicated_closure)
    binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        row_v1._topology_pages(pages),
        _f3_spec(),
        candidates,
        candidates["regions"][0],
    )
    render = _snapshot_and_render(pages, [], colored_bboxes=colored)[1]
    assert (
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            axis,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=binding["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )
        == axis
    )


@pytest.mark.parametrize(
    "attack",
    [
        "SECOND_EXACT_NUMERIC_ANCHOR",
        "INCOMPLETE_PEER_AXIS",
        "HORIZONTAL_PEER_AXIS",
        "CONFLICTING_MARGIN_LABEL",
        "NO_RENDER_AUTHORITY",
    ],
)
def test_fragmented_extreme_margin_projection_fails_closed_without_every_gate(
    attack: str,
) -> None:
    pages, stamp_lines, colored = _extreme_right_vertical_stamp_v4_fixture(
        mode="FRAGMENTED",
        margin_label=attack == "CONFLICTING_MARGIN_LABEL",
    )
    if attack == "SECOND_EXACT_NUMERIC_ANCHOR":
        peer = next(line for line in stamp_lines if line["vietocr_text"] == "G Ty")
        peer["vietocr_text"] = "61"
    elif attack == "INCOMPLETE_PEER_AXIS":
        removed = stamp_lines[-1]
        pages[0]["lines"].remove(removed)
        stamp_lines.remove(removed)
        _reindex_page_lines(pages[0]["lines"])
    elif attack == "HORIZONTAL_PEER_AXIS":
        for ordinal, line in enumerate(stamp_lines):
            line["bbox"][1] = 180 + ordinal
            line["bbox"][3] = 200 + ordinal
    _scan, _candidates, _snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages,
        stamp_lines,
        color="black",
        with_render=attack != "NO_RENDER_AUTHORITY",
        render_colored_bboxes=colored,
    )

    assert not any(
        evidence["status"] == subject._EXTREME_MARGIN_VERTICAL_STAMP_V4_STATUS
        and evidence["geometry"]["stamp_mode"]
        == subject._EXTREME_MARGIN_VERTICAL_STAMP_V4_FRAGMENTED_MODE
        for evidence in axis["authenticated_extreme_margin_furniture_evidence"]
    )
    assert any(len(grid["column_centers"]) == 3 for grid in axis["row_axis"]["column_grids"])


def test_fragmented_extreme_margin_peer_consensus_tamper_rejects() -> None:
    pages, stamp_lines, colored = _extreme_right_vertical_stamp_v4_fixture(mode="FRAGMENTED")
    _scan, _candidates, _snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages,
        stamp_lines,
        color="black",
        with_render=True,
        render_colored_bboxes=colored,
    )
    attacked = copy.deepcopy(axis)
    evidence = attacked["authenticated_extreme_margin_furniture_evidence"][0]
    peer = next(
        line
        for line in evidence["margin_band"]["source_line_axis"]
        if line["vietocr_text"] == "G Ty"
    )
    peer["vietocr_text"] = "61"
    evidence["margin_band"]["source_line_axis_sha256"] = canonical_json_sha256_v1(
        evidence["margin_band"]["source_line_axis"]
    )
    crop = next(
        proof
        for proof in evidence["peer_crop_proofs"]
        if proof["source_line_record"]["numeric_raw_prediction"] == "61"
    )
    crop["source_line_record"]["vietocr_text"] = "61"
    _coherently_rehash_furniture_axis(attacked)

    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="peer-mode proof",
    ):
        subject._validate_result(attacked)


@pytest.mark.parametrize(
    "attack",
    [
        "REAL_THIRD_FINANCIAL_LANE",
        "UNIT_HEADER_SURFACE",
        "SINGLE_BLACK_DIGIT_IN_NORMAL_LANE",
        "NO_EXTERNAL_PEERS",
        "NUMERIC_EXTERNAL_PEER",
        "CONFLICTING_MARGIN_LABEL",
        "NO_RENDER_AUTHORITY",
    ],
)
def test_extreme_right_vertical_stamp_v4_fails_closed_without_every_gate(attack: str) -> None:
    mode = "CHROMATIC" if attack == "REAL_THIRD_FINANCIAL_LANE" else "CLIPPED"
    kwargs: dict[str, object] = {"mode": mode}
    if attack == "UNIT_HEADER_SURFACE":
        kwargs["candidate_vietocr"] = "Triệu đồng"
    elif attack == "SINGLE_BLACK_DIGIT_IN_NORMAL_LANE":
        kwargs["candidate_bbox"] = [820, 280, 850, 340]
    elif attack == "NO_EXTERNAL_PEERS":
        kwargs["include_peers"] = False
    elif attack == "NUMERIC_EXTERNAL_PEER":
        kwargs["peer_numeric"] = True
    elif attack == "CONFLICTING_MARGIN_LABEL":
        kwargs["margin_label"] = True
    pages, stamp_lines, colored = _extreme_right_vertical_stamp_v4_fixture(**kwargs)
    if attack == "REAL_THIRD_FINANCIAL_LANE":
        pages[0]["lines"].extend(
            [
                _line(940, "31.12.2023", "31.12.2023", [930, 45, 990, 65]),
                _line(941, "120", "120", [930, 15, 990, 38]),
                _line(942, "80", "80", [930, 180, 990, 200]),
                _line(943, "30", "30", [930, 246, 990, 266]),
            ]
        )
        _reindex_page_lines(pages[0]["lines"])
    _scan, _candidates, _snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages,
        stamp_lines,
        color="black",
        with_render=attack != "NO_RENDER_AUTHORITY",
        render_colored_bboxes=colored,
    )

    assert not any(
        evidence["status"] == subject._EXTREME_MARGIN_VERTICAL_STAMP_V4_STATUS
        for evidence in axis["authenticated_extreme_margin_furniture_evidence"]
    )
    stamp_sample_ids = {line["sample_id"] for line in stamp_lines}
    assert not any(
        sample["sample_id"] in stamp_sample_ids
        and sample["owner_kind"] == subject._EXTREME_MARGIN_FURNITURE_OWNER_KIND
        for sample in axis["numeric_sample_universe"]
    )
    if attack == "REAL_THIRD_FINANCIAL_LANE":
        assert any(len(grid["column_centers"]) == 3 for grid in axis["row_axis"]["column_grids"])


def test_extreme_right_vertical_stamp_v4_never_reowns_printed_note_reference_axis() -> None:
    pages, ink_bboxes = _printed_note_reference_fixture_pages()
    _scan, _candidates, _binding, _snapshot, axis = (
        _build_authenticated_printed_note_reference_fixture(pages, ink_bboxes)
    )

    assert axis["authenticated_extreme_margin_furniture_evidence"]
    assert all(
        evidence["status"]
        in {
            subject._PRINTED_NOTE_REFERENCE_FURNITURE_V3_STATUS,
            subject._PRINTED_NOTE_REFERENCE_FURNITURE_V4_STATUS,
        }
        for evidence in axis["authenticated_extreme_margin_furniture_evidence"]
    )


@pytest.mark.parametrize(
    ("attack", "error"),
    [
        ("CROSS_PAGE", "candidate binding|component proof"),
        ("BBOX", "authenticated render binding"),
        ("COMPONENT", "component peer chain"),
        ("OWNER", "universe owner"),
    ],
)
def test_extreme_right_vertical_stamp_v4_coherent_tamper_rejects(attack: str, error: str) -> None:
    pages, stamp_lines, colored = _extreme_right_vertical_stamp_v4_fixture(mode="CHROMATIC")
    _scan, _candidates, _snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages,
        stamp_lines,
        color="red",
        with_render=True,
        render_colored_bboxes=colored,
    )
    attacked = copy.deepcopy(axis)
    evidence = attacked["authenticated_extreme_margin_furniture_evidence"][0]
    if attack == "CROSS_PAGE":
        evidence["candidate_crop_proof"]["render_binding"]["physical_page"] += 1
        _coherently_rehash_furniture_axis(attacked)
    elif attack == "BBOX":
        evidence["candidate_crop_proof"]["render_binding"]["raw_pixel_bbox"][0] += 1
        _coherently_rehash_furniture_axis(attacked)
    elif attack == "COMPONENT":
        evidence["component_peer_proof"]["qualifying_component_count"] -= 1
        _coherently_rehash_furniture_axis(attacked)
    else:
        sample = next(
            item
            for item in attacked["numeric_sample_universe"]
            if item["sample_id"] == evidence["sample_id"]
        )
        sample["owner_id"] = attacked["role_occurrences"][0]["occurrence_id"]
        _coherently_rehash_occurrence(attacked)
    with pytest.raises(subject.AccountingFamilyOccurrenceRowAxisV2Error, match=error):
        subject._validate_result(attacked)


@pytest.mark.parametrize("proof_kind", ["CANDIDATE", "PEER"])
def test_extreme_right_vertical_stamp_v4_exact_pixel_hash_requires_public_replay(
    proof_kind: str,
) -> None:
    pages, stamp_lines, colored = _extreme_right_vertical_stamp_v4_fixture(mode="CLIPPED")
    scan, candidates, snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages,
        stamp_lines,
        color="black",
        with_render=True,
        render_colored_bboxes=colored,
    )
    attacked = copy.deepcopy(axis)
    evidence = attacked["authenticated_extreme_margin_furniture_evidence"][0]
    proof = (
        evidence["candidate_crop_proof"]
        if proof_kind == "CANDIDATE"
        else evidence["peer_crop_proofs"][0]
    )
    proof["exact_bbox_rgb_sha256"] = "0" * 64
    _coherently_rehash_furniture_axis(attacked)
    assert subject._validate_result(attacked) == attacked
    binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        row_v1._topology_pages(pages),
        _f3_spec(),
        candidates,
        candidates["regions"][0],
    )
    render = _snapshot_and_render(pages, [], colored_bboxes=colored)[1]
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="does not replay exactly",
    ):
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            attacked,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=binding["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )


@pytest.mark.parametrize(
    "attack",
    [
        "REAL_NUMERIC_COLUMN",
        "BLACK",
        "PARTIAL_COMPONENT",
        "DUPLICATE_COMPONENT",
        "PARTIAL_PEERS",
        "NUMERIC_PEER",
        "NOT_EXTREME_RIGHT",
        "SAME_ROW_LABEL_AT_MARGIN",
        "UNKNOWN_LABEL_SURFACE",
    ],
)
def test_extreme_margin_v2_numeric_rotated_stamp_fails_closed(attack: str) -> None:
    kwargs: dict[str, object] = {}
    if attack == "REAL_NUMERIC_COLUMN":
        kwargs["candidate_numeric"] = "1001"
    elif attack == "BLACK":
        kwargs["color"] = "black"
    elif attack == "PARTIAL_COMPONENT":
        kwargs["component_attack"] = "PARTIAL"
    elif attack == "DUPLICATE_COMPONENT":
        kwargs["component_attack"] = "DUPLICATE"
    elif attack == "PARTIAL_PEERS":
        kwargs["peer_count"] = 2
    elif attack == "NOT_EXTREME_RIGHT":
        kwargs["candidate_bbox"] = [940, 290, 985, 330]
    elif attack == "UNKNOWN_LABEL_SURFACE":
        kwargs["candidate_vietocr"] = "UNKNOWN LABEL"
    pages, stamp_lines, colored = _numeric_extreme_margin_stamp_fixture(**kwargs)
    if attack == "NUMERIC_PEER":
        stamp_lines[0]["numeric_recognition"]["raw_prediction"] = "7"
    elif attack == "SAME_ROW_LABEL_AT_MARGIN":
        pages[0]["lines"].append(_line(920, "Tham chiếu", "", [930, 292, 955, 328]))
        _reindex_page_lines(pages[0]["lines"])
    _scan, _candidates, _snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages,
        stamp_lines,
        color=str(kwargs.get("color", "red")),
        with_render=True,
        render_colored_bboxes=colored,
    )

    assert axis["authenticated_extreme_margin_furniture_evidence"] == []
    assert axis["internal_unassigned_numeric_clusters"]


@pytest.mark.parametrize(
    ("attack", "error"),
    [
        ("CROSS_PAGE", "V2 authenticated chromatic peer axis"),
        ("CROSS_PARENT", "authenticated extreme-margin V2 furniture evidence drifted"),
        ("BBOX", "geometry or label separation|authenticated render binding"),
        ("COMPONENT", "component uniqueness"),
    ],
)
def test_extreme_margin_v2_numeric_rotated_stamp_coherent_tamper_rejects(
    attack: str, error: str
) -> None:
    pages, stamp_lines, colored = _numeric_extreme_margin_stamp_fixture()
    _scan, _candidates, _snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages,
        stamp_lines,
        color="red",
        with_render=True,
        render_colored_bboxes=colored,
    )
    attacked = copy.deepcopy(axis)
    evidence = attacked["authenticated_extreme_margin_furniture_evidence"][0]
    if attack == "CROSS_PAGE":
        evidence["candidate_crop_proof"]["render_binding"]["physical_page"] += 1
    elif attack == "CROSS_PARENT":
        evidence["topology_candidates_id"] = "aftcv2:result:" + "0" * 64
    elif attack == "BBOX":
        evidence["candidate_crop_proof"]["render_binding"]["raw_pixel_bbox"][0] += 1
    else:
        proof = evidence["expanded_component_proof"]
        component = proof["component_axis"][proof["qualifying_component_ordinal"]]
        component["target_overlap_ink_pixel_count"] = 0
        proof["component_axis_sha256"] = canonical_json_sha256_v1(proof["component_axis"])
    _coherently_rehash_furniture_axis(attacked)

    with pytest.raises(subject.AccountingFamilyOccurrenceRowAxisV2Error, match=error):
        subject._validate_result(attacked)


@pytest.mark.parametrize(
    "attack",
    [
        "BLACK",
        "WEAK_CHROMA",
        "NO_PEERS",
        "SINGLE_PEER",
        "DIGIT_PEERS",
        "LABEL_TEXT",
        "LABEL_CROSSES_MARGIN",
        "MONEY_LANE",
    ],
)
def test_extreme_margin_v2_rejects_missing_or_ambiguous_authority(attack: str) -> None:
    pages, stamp_lines = _extreme_margin_fixture_pages(candidate_vietocr="soom")
    color = "red"
    if attack == "BLACK":
        color = "black"
    elif attack == "WEAK_CHROMA":
        color = "#b4aaaa"
    elif attack == "NO_PEERS":
        pages, stamp_lines = _extreme_margin_fixture_pages(
            include_peers=False, candidate_vietocr="soom"
        )
    elif attack == "SINGLE_PEER":
        removed = stamp_lines.pop(0)
        pages[0]["lines"].remove(removed)
        _reindex_page_lines(pages[0]["lines"])
    elif attack == "DIGIT_PEERS":
        for line in stamp_lines[:-1]:
            line["numeric_recognition"]["raw_prediction"] = "STAMP2"
    elif attack == "LABEL_TEXT":
        pages, stamp_lines = _extreme_margin_fixture_pages(candidate_vietocr="UNKNOWN LABEL")
    elif attack == "LABEL_CROSSES_MARGIN":
        pages[0]["lines"].append(_line(903, "Nhãn", "", [920, 290, 945, 310]))
        _reindex_page_lines(pages[0]["lines"])
    elif attack == "MONEY_LANE":
        pages, stamp_lines = _extreme_margin_fixture_pages(
            candidate_bbox=[850, 290, 900, 310], candidate_vietocr="soom"
        )
    _scan, _candidates, _snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages, stamp_lines, color=color, with_render=True
    )

    assert axis["authenticated_extreme_margin_furniture_evidence"] == []
    if attack == "MONEY_LANE":
        return
    assert axis["internal_unassigned_numeric_clusters"]
    assert all(
        cluster["status"]
        in {
            "SOURCE_ONLY_OFF_LANE_NUMERIC_CLUSTER",
            "SOURCE_ONLY_INTERNAL_UNASSIGNED_NUMERIC_CLUSTER",
        }
        for cluster in axis["internal_unassigned_numeric_clusters"]
    )


def _extreme_margin_v2_component_test_proof(
    rectangles: list[tuple[list[int], str]],
) -> dict | None:
    image = Image.new("RGB", (1000, 800), "white")
    draw = ImageDraw.Draw(image)
    for bbox, color in rectangles:
        draw.rectangle(tuple(bbox), fill=color)
    return subject._authenticated_extreme_margin_v2_component_proof(
        image=image,
        render_record={
            "document_ordinal": 1,
            "physical_page": 1,
            "render_ref": {
                "pixel_height": 800,
                "pixel_width": 1000,
                "sha256": "0" * 64,
                "size_bytes": 1,
            },
        },
        render_id="ffaprv1:render:fixture",
        candidate={"bbox": [950, 290, 995, 310]},
        margin_boundary=939,
        scale=20.0,
    )


@pytest.mark.parametrize(
    "rectangles",
    [
        [([940, 292, 999, 308], "red")],
        [([960, 299, 970, 360], "red")],
        [([960, 260, 970, 340], "black")],
        [([952, 260, 960, 340], "red"), ([980, 260, 988, 340], "red")],
    ],
)
def test_extreme_margin_v2_component_rejects_horizontal_one_sided_black_or_nonunique(
    rectangles: list[tuple[list[int], str]],
) -> None:
    assert _extreme_margin_v2_component_test_proof(rectangles) is None


def test_extreme_margin_v2_component_and_render_tamper_rejects() -> None:
    pages, stamp_lines = _extreme_margin_fixture_pages(candidate_vietocr="soom")
    scan, candidates, snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages, stamp_lines, color="red", with_render=True
    )
    qualification_tamper = copy.deepcopy(axis)
    evidence = qualification_tamper["authenticated_extreme_margin_furniture_evidence"][0]
    component = evidence["expanded_component_proof"]["component_axis"][
        evidence["expanded_component_proof"]["qualifying_component_ordinal"]
    ]
    component["target_overlap_ink_pixel_count"] = 0
    evidence["expanded_component_proof"]["component_axis_sha256"] = canonical_json_sha256_v1(
        evidence["expanded_component_proof"]["component_axis"]
    )
    _coherently_rehash_furniture_axis(qualification_tamper)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="component uniqueness",
    ):
        subject._validate_result(qualification_tamper)

    label_tamper = copy.deepcopy(axis)
    evidence = label_tamper["authenticated_extreme_margin_furniture_evidence"][0]
    evidence["label_collision_proof"]["semantic_label_line_ordinals"].append(
        evidence["source_record"]["line_ordinal"]
    )
    evidence["label_collision_proof"]["semantic_label_line_ordinals"].sort()
    _coherently_rehash_furniture_axis(label_tamper)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="label collision proof",
    ):
        subject._validate_result(label_tamper)

    pixel_tamper = copy.deepcopy(axis)
    pixel_tamper["authenticated_extreme_margin_furniture_evidence"][0]["expanded_component_proof"][
        "expanded_rgb_sha256"
    ] = "0" * 64
    _coherently_rehash_furniture_axis(pixel_tamper)
    assert subject._validate_result(pixel_tamper) == pixel_tamper
    render = _snapshot_and_render(
        pages,
        [],
        colored_bboxes=[(line["bbox"], "red") for line in stamp_lines],
    )[1]
    binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        row_v1._topology_pages(pages),
        _f3_spec(),
        candidates,
        candidates["regions"][0],
    )
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="does not replay exactly",
    ):
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            pixel_tamper,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=binding["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )


def test_extreme_margin_furniture_fails_closed_without_every_gate() -> None:
    pages, stamp_lines = _extreme_margin_fixture_pages()
    _scan, _candidates, _snapshot, no_render = _build_authenticated_extreme_margin_fixture(
        pages, stamp_lines, color="red", with_render=False
    )
    assert no_render["authenticated_extreme_margin_furniture_evidence"] == []
    assert no_render["internal_unassigned_numeric_clusters"][0]["status"] == (
        "SOURCE_ONLY_OFF_LANE_NUMERIC_CLUSTER"
    )
    assert no_render["unresolved_reasons"][-1] == (
        "EXTREME_MARGIN_ANNOTATION_RENDER_REQUIRED:PAGE_SEQUENCE:1"
    )

    for color, peers, topology_authority, vietocr in [
        ("black", True, True, "304"),
        ("red", False, True, "304"),
        ("red", True, False, "304"),
        ("red", True, True, "UNKNOWN LABEL"),
    ]:
        variant_pages, variant_lines = _extreme_margin_fixture_pages(
            include_peers=peers,
            candidate_vietocr=vietocr,
        )
        _scan, _candidates, _snapshot, variant = _build_authenticated_extreme_margin_fixture(
            variant_pages,
            variant_lines,
            color=color,
            with_render=True,
            with_topology_candidates=topology_authority,
        )
        assert variant["authenticated_extreme_margin_furniture_evidence"] == []
        assert variant["internal_unassigned_numeric_clusters"][0]["status"] == (
            "SOURCE_ONLY_OFF_LANE_NUMERIC_CLUSTER"
        )

    in_lane_pages, in_lane_lines = _extreme_margin_fixture_pages(
        candidate_bbox=[610, 290, 700, 310]
    )
    _scan, _candidates, _snapshot, in_lane = _build_authenticated_extreme_margin_fixture(
        in_lane_pages, in_lane_lines, color="red", with_render=True
    )
    assert in_lane["authenticated_extreme_margin_furniture_evidence"] == []


@pytest.mark.parametrize(
    ("numeric_channel", "numeric_surface", "expected_cluster_count"),
    [
        ("PP", "111", 3),
        ("VIETOCR", "111", 1),
        ("PP", "-", 3),
        ("PP", "1.460,873", 3),
        ("PP", "3.202.820 0UNG", 3),
        ("PP", "1O0", 1),
        ("VIETOCR", "123abc", 1),
        ("PP", "DẤU ١", 1),
        ("VIETOCR", "12/34", 1),
        ("PP", "DẤU ²", 1),
    ],
)
def test_chromatic_numeric_margin_peers_cannot_prove_furniture(
    numeric_channel: str,
    numeric_surface: str,
    expected_cluster_count: int,
) -> None:
    pages, stamp_lines = _extreme_margin_fixture_pages()
    peer_lines = [line for line in stamp_lines if line["vietocr_text"] != "304"]
    for peer in peer_lines:
        if numeric_channel == "PP":
            peer["numeric_recognition"]["raw_prediction"] = numeric_surface
        else:
            peer["vietocr_text"] = numeric_surface
    _scan, _candidates, _snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages,
        stamp_lines,
        color="red",
        with_render=True,
    )

    assert axis["authenticated_extreme_margin_furniture_evidence"] == []
    assert len(axis["internal_unassigned_numeric_clusters"]) == expected_cluster_count
    candidate_sample_id = next(
        line["sample_id"] for line in stamp_lines if line["vietocr_text"] == "304"
    )
    candidate_cluster = next(
        cluster
        for cluster in axis["internal_unassigned_numeric_clusters"]
        if candidate_sample_id in cluster["sample_ids"]
    )
    assert candidate_cluster["status"] in {
        "SOURCE_ONLY_INTERNAL_UNASSIGNED_NUMERIC_CLUSTER",
        "SOURCE_ONLY_OFF_LANE_NUMERIC_CLUSTER",
    }
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        "SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO" in reason
        or "OFF_LANE_NUMERIC_SOURCE_ONLY_VETO" in reason
        for reason in closure["unresolved_reasons"]
    )


def test_extreme_margin_furniture_coherent_band_and_owner_tamper_rejects() -> None:
    pages, stamp_lines = _extreme_margin_fixture_pages()
    scan, candidates, snapshot, axis = _build_authenticated_extreme_margin_fixture(
        pages, stamp_lines, color="red", with_render=True
    )
    attacked = copy.deepcopy(axis)
    evidence = attacked["authenticated_extreme_margin_furniture_evidence"][0]
    evidence["margin_band"]["qualifying_peer_line_ordinals"] = evidence["margin_band"][
        "qualifying_peer_line_ordinals"
    ][1:]
    evidence["peer_crop_proofs"] = evidence["peer_crop_proofs"][1:]
    _coherently_rehash_furniture_axis(attacked)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="repeated peer source binding|chromatic peer axis",
    ):
        subject._validate_result(attacked)

    swapped = copy.deepcopy(axis)
    furniture_sample = next(
        item
        for item in swapped["numeric_sample_universe"]
        if item["owner_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
    )
    furniture_sample["owner_id"] = swapped["role_occurrences"][0]["occurrence_id"]
    _coherently_rehash_occurrence(swapped)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="furniture universe owner",
    ):
        subject._validate_result(swapped)

    for numeric_surface in ("111", "1O0"):
        numeric_peer = copy.deepcopy(axis)
        numeric_evidence = numeric_peer["authenticated_extreme_margin_furniture_evidence"][0]
        peer_ordinal = numeric_evidence["margin_band"]["qualifying_peer_line_ordinals"][0]
        margin_peer = next(
            line
            for line in numeric_evidence["margin_band"]["source_line_axis"]
            if line["line_ordinal"] == peer_ordinal
        )
        crop_peer = next(
            proof["source_line_record"]
            for proof in numeric_evidence["peer_crop_proofs"]
            if proof["source_line_record"]["line_ordinal"] == peer_ordinal
        )
        margin_peer["vietocr_text"] = numeric_surface
        crop_peer["vietocr_text"] = numeric_surface
        numeric_evidence["margin_band"]["source_line_axis_sha256"] = canonical_json_sha256_v1(
            numeric_evidence["margin_band"]["source_line_axis"]
        )
        _coherently_rehash_furniture_axis(numeric_peer)
        with pytest.raises(
            subject.AccountingFamilyOccurrenceRowAxisV2Error,
            match="repeated peer source binding",
        ):
            subject._validate_result(numeric_peer)

    coherent_peer_relabel = copy.deepcopy(axis)
    relabel_evidence = coherent_peer_relabel["authenticated_extreme_margin_furniture_evidence"][0]
    peer_ordinal = relabel_evidence["margin_band"]["qualifying_peer_line_ordinals"][0]
    margin_peer = next(
        line
        for line in relabel_evidence["margin_band"]["source_line_axis"]
        if line["line_ordinal"] == peer_ordinal
    )
    crop_peer = next(
        proof["source_line_record"]
        for proof in relabel_evidence["peer_crop_proofs"]
        if proof["source_line_record"]["line_ordinal"] == peer_ordinal
    )
    margin_peer["vietocr_text"] = "DẤU KHÁC"
    margin_peer["sample_id"] = "forged-peer-sample"
    crop_peer["vietocr_text"] = "DẤU KHÁC"
    crop_peer["sample_id"] = "forged-peer-sample"
    relabel_evidence["margin_band"]["source_line_axis_sha256"] = canonical_json_sha256_v1(
        relabel_evidence["margin_band"]["source_line_axis"]
    )
    _coherently_rehash_furniture_axis(coherent_peer_relabel)
    assert subject._validate_result(coherent_peer_relabel) == coherent_peer_relabel

    bbox_drift = copy.deepcopy(axis)
    bbox_drift["authenticated_extreme_margin_furniture_evidence"][0]["candidate_crop_proof"][
        "render_binding"
    ]["raw_pixel_bbox"][0] += 1
    _coherently_rehash_furniture_axis(bbox_drift)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="authenticated render binding",
    ):
        subject._validate_result(bbox_drift)

    coherent_pixel_hash = copy.deepcopy(axis)
    coherent_pixel_hash["authenticated_extreme_margin_furniture_evidence"][0][
        "candidate_crop_proof"
    ]["exact_bbox_rgb_sha256"] = "0" * 64
    _coherently_rehash_furniture_axis(coherent_pixel_hash)
    assert subject._validate_result(coherent_pixel_hash) == coherent_pixel_hash
    render = _snapshot_and_render(
        pages,
        [],
        colored_bboxes=[(line["bbox"], "red") for line in stamp_lines],
    )[1]
    binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        row_v1._topology_pages(pages),
        _f3_spec(),
        candidates,
        candidates["regions"][0],
    )
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="does not replay exactly",
    ):
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            coherent_pixel_hash,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=binding["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="does not replay exactly",
    ):
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            coherent_peer_relabel,
            pages,
            _f3_spec(),
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=binding["effective_topology_region"],
            topology_candidates=candidates,
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )


def _f3_detector_dash_rescues(
    pages: list[dict[str, object]],
    *,
    role: str,
    region_builders: list,
) -> tuple[dict, dict, tuple[dict[str, object], ...]]:
    spec = _f3_spec()
    parsed_pages = row_v1._pages(pages)
    scan = topology_v1.build_accounting_family_topology_scan_v1(row_v1._topology_pages(pages), spec)
    region = scan["regions"][0]
    effective = total_v1.project_accounting_family_coextensive_parent_total_region_v1(
        spec, scan, region
    )
    base = row_v1._build_axis(parsed_pages, scan, effective, ())
    target = next(row for row in base["rows"] if row["role"] == role)
    centers, visible_cells = row_v1._resolved_page_grid_inputs(
        base["rows"], target, base["column_grids"]
    )
    label_indices = row_v1._match_source_line_indices(target["label_match"])
    label_boxes = [
        line["bbox"] for line in parsed_pages[0]["lines"] if line["line_ordinal"] in label_indices
    ]
    proposals = propose_missing_value_lane_regions_v1(
        [{**line, "source_line_index": line["line_ordinal"]} for line in parsed_pages[0]["lines"]],
        label_boxes=label_boxes,
        is_numeric=row_v1._is_numeric,
        page_width=1000,
        page_height=1200,
        resolved_column_centers=centers,
        resolved_visible_value_cells=visible_cells,
    )
    assert len(proposals) == len(region_builders)
    rescues = tuple(
        {
            "column_ordinal": proposal["column_ordinal"],
            "page_sequence": 1,
            "region": builder(proposal["raw_pixel_bbox"]),
            "role": role,
        }
        for proposal, builder in zip(proposals, region_builders, strict=True)
    )
    return scan, effective, rescues


def _coherently_rehash_occurrence(axis: dict) -> None:
    material = copy.deepcopy(axis)
    material.pop("occurrence_axis_id")
    axis["occurrence_axis_id"] = "aforav2:axis:" + canonical_json_sha256_v1(material)


def _coherently_replace_source_scope_binding(
    axis: dict, occurrence: dict, receipt: dict | None
) -> None:
    occurrence["source_scope_binding"] = copy.deepcopy(receipt)
    occurrence["label_match"]["source_scope_binding"] = copy.deepcopy(receipt)
    for row in axis["row_axis"]["rows"]:
        if row["label_match"].get("occurrence_id") == occurrence["occurrence_id"]:
            row["label_match"]["source_scope_binding"] = copy.deepcopy(receipt)
    axis["row_axis"] = subject._regenerate_v1_axis(axis["row_axis"])


def test_f3_tiny_isolated_structural_rescue_becomes_owner_only_with_complete_subtree() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "", ""),
            ("Tiền gửi không kỳ hạn", "", ""),
            ("Bằng VND", "60", "50"),
            ("Bằng ngoại tệ", "10", "10"),
            ("Tiền gửi có kỳ hạn", "", ""),
            ("Bằng VND", "30", "25"),
            ("Bằng ngoại tệ", "0", "5"),
            ("Cho vay các TCTD khác", "", ""),
            ("Bằng VND", "50", "40"),
        ]
    )
    scan, effective, rescues = _f3_detector_dash_rescues(
        pages,
        role="INTERBANK_DEPOSIT_GROUP",
        region_builders=[_tiny_artifact_dash_region, _blank_region],
    )
    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        _f3_spec(),
        scan,
        scan["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
        visible_dash_rescues=rescues,
    )

    deposit = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_DEPOSIT_GROUP"
    )
    assert deposit["has_bound_value_row"] is False
    assert all(
        row["label_match"].get("occurrence_id") != deposit["occurrence_id"]
        for row in axis["row_axis"]["rows"]
    )
    assert axis["row_axis"]["visible_dash_rescues"] == []
    assert len(axis["structural_owner_only_rescue_rejections"]) == 1
    evidence = axis["structural_owner_only_rescue_rejections"][0]
    assert evidence["occurrence_id"] == deposit["occurrence_id"]
    assert evidence["status"] == "STRUCTURAL_OWNER_ONLY_TINY_ISOLATED_RESCUE_REJECTED"
    assert len(evidence["complete_descendant_occurrence_ids"]) >= 4
    assert evidence["source_record"]["status"] == (
        "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
    )
    tiny = next(
        item
        for item in evidence["rejected_rescue_projections"]
        if item["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    )
    assert tiny["dash_evidence"]["glyph_metrics"]["component_bbox"] == [18, 15, 22, 17]
    assert tiny["dash_evidence"]["glyph_metrics"]["discarded_noncentral_component_count"] == 1
    assert axis["status"] == (
        "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
    )

    attacked = copy.deepcopy(axis)
    attacked["structural_owner_only_rescue_rejections"][0]["source_record"]["role"] = (
        "INTERBANK_LOAN_GROUP"
    )
    _coherently_rehash_occurrence(attacked)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="owner-only rescue rejection",
    ):
        subject._validate_result(attacked)

    removed = copy.deepcopy(axis)
    removed["structural_owner_only_rescue_rejections"] = []
    _coherently_rehash_occurrence(removed)
    with pytest.raises(subject.AccountingFamilyOccurrenceRowAxisV2Error, match="replay exactly"):
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            removed,
            pages,
            _f3_spec(),
            scan,
            scan["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=effective,
            visible_dash_rescues=rescues,
        )

    forged_descendants = copy.deepcopy(axis)
    forged_evidence = forged_descendants["structural_owner_only_rescue_rejections"][0]
    forged_evidence["complete_descendant_occurrence_ids"] = [
        item["occurrence_id"]
        for item in forged_descendants["role_occurrences"]
        if item["role"] in {"INTERBANK_LOAN_GROUP", "INTERBANK_LOAN_VND"}
    ]
    evidence_material = copy.deepcopy(forged_evidence)
    evidence_material.pop("evidence_id")
    forged_evidence["evidence_id"] = "aforav2:owner-only-rescue:" + canonical_json_sha256_v1(
        evidence_material
    )
    _coherently_rehash_occurrence(forged_descendants)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="owner-only rescue rejection replay",
    ):
        subject._validate_result(forged_descendants)


def test_f3_structural_rescue_rejection_requires_complete_subtree_and_tiny_artifact() -> None:
    incomplete_pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "", ""),
            ("Tiền gửi không kỳ hạn", "", ""),
            ("Bằng VND", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    scan, effective, rescues = _f3_detector_dash_rescues(
        incomplete_pages,
        role="INTERBANK_DEPOSIT_GROUP",
        region_builders=[_tiny_artifact_dash_region, _blank_region],
    )
    incomplete_axis = subject.build_accounting_family_occurrence_row_axis_v2(
        incomplete_pages,
        _f3_spec(),
        scan,
        scan["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
        visible_dash_rescues=rescues,
    )
    incomplete_parent = next(
        row
        for row in incomplete_axis["row_axis"]["rows"]
        if row["role"] == "INTERBANK_DEPOSIT_GROUP"
    )
    assert incomplete_parent["status"] == "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
    assert incomplete_axis["structural_owner_only_rescue_rejections"] == []
    assert incomplete_axis["status"] == "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"

    complete_pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "", ""),
            ("Tiền gửi không kỳ hạn", "", ""),
            ("Bằng VND", "60", "50"),
            ("Bằng ngoại tệ", "10", "10"),
            ("Tiền gửi có kỳ hạn", "", ""),
            ("Bằng VND", "30", "25"),
            ("Bằng ngoại tệ", "0", "5"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    scan, effective, rescues = _f3_detector_dash_rescues(
        complete_pages,
        role="INTERBANK_DEPOSIT_GROUP",
        region_builders=[_clear_dash_region, _blank_region],
    )
    clear_axis = subject.build_accounting_family_occurrence_row_axis_v2(
        complete_pages,
        _f3_spec(),
        scan,
        scan["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
        visible_dash_rescues=rescues,
    )
    clear_parent = next(
        row for row in clear_axis["row_axis"]["rows"] if row["role"] == "INTERBANK_DEPOSIT_GROUP"
    )
    assert clear_parent["status"] == "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
    assert clear_parent["values"][0]["parsed_token"]["classification"] == "DASH_ZERO"
    assert clear_axis["structural_owner_only_rescue_rejections"] == []


def test_f3_normal_size_detector_dash_remains_owned_by_loan_foreign_currency_leaf() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "49", "40"),
            ("Bằng ngoại tệ", "1", ""),
        ]
    )
    scan, effective, rescues = _f3_detector_dash_rescues(
        pages,
        role="INTERBANK_LOAN_FOREIGN_CURRENCY",
        region_builders=[_clear_dash_region],
    )
    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        _f3_spec(),
        scan,
        scan["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
        visible_dash_rescues=rescues,
    )

    foreign = next(
        row for row in axis["row_axis"]["rows"] if row["role"] == "INTERBANK_LOAN_FOREIGN_CURRENCY"
    )
    assert foreign["status"] == "VISIBLE_VALUE_LANES_BOUND"
    assert [value["parsed_token"]["coefficient"] for value in foreign["values"]] == [1, 0]
    assert axis["structural_owner_only_rescue_rejections"] == []
    assert axis["row_axis"]["visible_dash_rescues"][0]["dash_evidence"]["glyph_metrics"][
        "component_bbox"
    ] == [16, 14, 25, 18]


def test_v4_unique_material_dash_plus_acb_scan_speck_binds_exact_leaf_parent_and_lane() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "", "150.979"),
            ("Bằng ngoại tệ", "0", "0"),
        ]
    )
    scan, effective, rescues = _f3_detector_dash_rescues(
        pages,
        role="INTERBANK_LOAN_VND",
        region_builders=[_unique_dash_with_acb_scan_speck_region],
    )
    topology_pages = row_v1._topology_pages(pages)
    candidates = candidates_v2.build_accounting_family_topology_candidates_v2(
        topology_pages, _f3_spec()
    )
    assert len(candidates["regions"]) == 1
    candidate_binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        topology_pages,
        _f3_spec(),
        candidates,
        candidates["regions"][0],
    )
    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        _f3_spec(),
        scan,
        candidates["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=candidate_binding["effective_topology_region"],
        topology_candidates=candidates,
        visible_dash_rescues=rescues,
    )

    vnd = next(row for row in axis["row_axis"]["rows"] if row["role"] == "INTERBANK_LOAN_VND")
    assert vnd["status"] == "VISIBLE_VALUE_LANES_BOUND"
    assert [value["parsed_token"]["coefficient"] for value in vnd["values"]] == [0, 150979]
    assert len(axis["authenticated_unique_dash_speck_evidence"]) == 1
    evidence = axis["authenticated_unique_dash_speck_evidence"][0]
    assert evidence["classification"] == ("VISIBLE_HORIZONTAL_DASH_WITH_ISOLATED_TINY_SCAN_SPECKS")
    assert evidence["authority"]["split_glyph_authority"] is False
    occurrence = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_LOAN_VND"
    )
    parent = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_LOAN_GROUP"
    )
    assert (
        evidence["input_binding"]["occurrence_binding"]["occurrence_id"]
        == occurrence["occurrence_id"]
    )
    assert evidence["input_binding"]["parent_binding"]["occurrence_id"] == parent["occurrence_id"]
    assert evidence["input_binding"]["lane_binding"]["column_ordinal"] == 0
    assert (
        evidence["input_binding"]["lane_binding"]["proposed_raw_pixel_bbox"]
        == rescues[0]["region"]["proposed_raw_pixel_bbox"]
    )
    assert evidence["component_analysis"]["selected_component"]["ink_pixel_count"] == 36
    assert evidence["component_analysis"]["discarded_total_ink_pixel_count"] == 8
    unresolved = axis["row_axis"]["visible_dash_rescues"][0]
    assert unresolved["classification"] == "UNRESOLVED_NOT_ONE_DASH_GLYPH"
    assert unresolved["dash_evidence"] == evidence["original_dash_evidence"]

    # The identical crop has no authority through the non-V4 seam.
    legacy = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        _f3_spec(),
        scan,
        scan["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
        visible_dash_rescues=rescues,
    )
    legacy_vnd = next(
        row for row in legacy["row_axis"]["rows"] if row["role"] == "INTERBANK_LOAN_VND"
    )
    assert legacy_vnd["status"] == "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
    assert legacy["authenticated_unique_dash_speck_evidence"] == []

    removed = copy.deepcopy(axis)
    removed["authenticated_unique_dash_speck_evidence"] = []
    _coherently_rehash_occurrence(removed)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="lacks exact unique-dash/speck ownership",
    ):
        subject._validate_result(removed)

    parent_tamper = copy.deepcopy(axis)
    receipt = parent_tamper["authenticated_unique_dash_speck_evidence"][0]
    receipt["input_binding"]["parent_binding"]["role"] = "FORGED_PARENT"
    receipt_material = copy.deepcopy(receipt)
    receipt_material.pop("evidence_id")
    receipt["evidence_id"] = "ffaudsv1:evidence:" + canonical_json_sha256_v1(receipt_material)
    _coherently_rehash_occurrence(parent_tamper)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="unique-dash/speck receipt drifted",
    ):
        subject._validate_result(parent_tamper)

    # A second same-role occurrence on the page makes the receipt ineligible,
    # even if all pixels and the first occurrence's binding remain unchanged.
    unresolved_axis = copy.deepcopy(axis["row_axis"])
    unresolved_row = next(
        row for row in unresolved_axis["rows"] if row["role"] == "INTERBANK_LOAN_VND"
    )
    unresolved_row["values"] = [
        value for value in unresolved_row["values"] if value["sample_id"] != unresolved["region_id"]
    ]
    unresolved_row["missing_column_ordinals"] = [0]
    unresolved_row["status"] = "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
    unresolved_axis = subject._regenerate_v1_axis(unresolved_axis)
    repeated_matches = [item["label_match"] for item in axis["role_occurrences"]]
    repeated = copy.deepcopy(occurrence["label_match"])
    repeated["occurrence_id"] = "aforav2:occurrence:" + "f" * 64
    repeated_matches.append(repeated)
    unchanged, repeated_receipts = subject._project_unique_dash_speck_rescues_v2(
        unresolved_axis,
        repeated_matches,
        rescues,
        topology_candidates_id=candidates["result_id"],
        topology_scan_id=scan["scan_id"],
    )
    assert repeated_receipts == []
    assert unchanged == unresolved_axis


def test_f3_blank_discount_does_not_steal_vnd_total_at_close_row_gaps() -> None:
    for gap in (18, 20):
        pages = _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "98", "89"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Chiết khấu, tái chiết khấu", "", ""),
                ("Bằng ngoại tệ", "0", "0"),
            ]
        )
        lines = pages[0]["lines"]
        vnd_label = next(line for line in lines if line["vietocr_text"] == "Bằng VND")
        discount_label = next(
            line for line in lines if line["vietocr_text"] == "Chiết khấu, tái chiết khấu"
        )
        discount_top = vnd_label["bbox"][3] + gap
        delta = discount_top - discount_label["bbox"][1]
        for line in lines:
            if line is discount_label or (
                line["bbox"][1] == discount_label["bbox"][1] and line["vietocr_text"] == ""
            ):
                line["bbox"][1] += delta
                line["bbox"][3] += delta

        _scan, axis = _build_f3(pages)

        rows = {row["role"]: row for row in axis["row_axis"]["rows"]}
        assert [
            value["parsed_token"]["coefficient"] for value in rows["INTERBANK_LOAN_VND"]["values"]
        ] == [50, 40]
        discount_occurrence = next(
            item
            for item in axis["role_occurrences"]
            if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
        )
        assert discount_occurrence["source_scope_binding"]["binding_kind"] == (
            "UNIQUE_EXACT_PRECEDING_SOURCE_SUBSCOPE_INTERVAL"
        )
        discount_row = next(
            row
            for row in axis["row_axis"]["rows"]
            if row["label_match"]["occurrence_id"] == discount_occurrence["occurrence_id"]
        )
        assert discount_row["values"] == []


def test_f3_generic_discount_requires_nearest_exact_currency_interval() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Chiết khấu, tái chiết khấu", "5", "4"),
            ("Bằng VND", "50", "40"),
        ]
    )

    _scan, axis = _build_f3(pages)

    ambiguous = next(
        item
        for item in axis["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
    )
    assert ambiguous["source_scope_binding"] is None
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith(
            "SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE:INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS:"
        )
        for reason in closure["unresolved_reasons"]
    )


def test_f3_repeated_retrieval_occurrence_ids_cannot_swap_physical_rows() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
            ("Chiết khấu, tái chiết khấu", "5", "4"),
            ("Chiết khấu, tái chiết khấu", "6", "5"),
        ]
    )

    _scan, axis = _build_f3(pages)
    repeated = [
        item
        for item in axis["role_occurrences"]
        if item["label_match"]["retrieval_role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
    ]
    assert len(repeated) == 2
    assert len({item["retrieval_scope_owner_occurrence_id"] for item in repeated}) == 1

    attacked = copy.deepcopy(axis)
    attacked_repeated = [
        item
        for item in attacked["role_occurrences"]
        if item["label_match"]["retrieval_role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
    ]
    first_id, second_id = [item["retrieval_occurrence_id"] for item in attacked_repeated]
    for item, swapped_id in zip(attacked_repeated, (second_id, first_id), strict=True):
        original_id = item["retrieval_occurrence_id"]
        item["retrieval_occurrence_id"] = swapped_id
        item["label_match"]["retrieval_occurrence_id"] = swapped_id
        row = next(
            row
            for row in attacked["row_axis"]["rows"]
            if row["label_match"].get("occurrence_id") == item["occurrence_id"]
        )
        assert row["label_match"]["retrieval_occurrence_id"] == original_id
        row["label_match"]["retrieval_occurrence_id"] = swapped_id
    attacked["row_axis"] = subject._regenerate_v1_axis(attacked["row_axis"])
    _coherently_rehash_occurrence(attacked)

    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="retrieval occurrence physical identity or owner drifted",
    ):
        subject._validate_result(attacked)


def test_f3_one_edit_vnd_with_exact_same_crop_source_anchors_generic_discount() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VNB", "50", "40"),
            ("Chiết khấu, tái chiết khấu", "5", "4"),
            ("Bằng ngoại tệ", "0", "0"),
        ]
    )
    vnd_line = next(line for line in pages[0]["lines"] if line["vietocr_text"] == "Bằng VNB")
    vnd_line["numeric_recognition"]["raw_prediction"] = "Bằng VND"

    _scan, axis = _build_f3(pages)

    vnd = next(item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_LOAN_VND")
    assert vnd["label_match"]["match_kind"].startswith("ONE_EDIT_")
    assert vnd["label_match"]["one_edit_exact_source_authority_check"]["status"] == (
        "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"
    )
    discount = next(
        item
        for item in axis["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
    )
    assert discount["occurrence_id"] != discount["retrieval_occurrence_id"]
    assert discount["source_scope_binding"]["binding_kind"] == (
        "UNIQUE_EXACT_PRECEDING_SOURCE_SUBSCOPE_INTERVAL"
    )
    assert (
        discount["source_scope_binding"]["anchor_exact_source_authority_check"]
        == (vnd["label_match"]["one_edit_exact_source_authority_check"])
    )
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    assert not any("ONE_EDIT" in reason for reason in closure["unresolved_reasons"])

    attacked = copy.deepcopy(axis)
    attacked_vnd = next(
        item for item in attacked["role_occurrences"] if item["role"] == "INTERBANK_LOAN_VND"
    )
    attacked_deposit = next(
        item for item in attacked["role_occurrences"] if item["role"] == "INTERBANK_DEPOSIT_GROUP"
    )
    attacked_vnd["retrieval_scope_owner_occurrence_id"] = attacked_deposit[
        "retrieval_occurrence_id"
    ]
    attacked_vnd["label_match"]["retrieval_scope_owner_occurrence_id"] = attacked_deposit[
        "retrieval_occurrence_id"
    ]
    row = next(
        row
        for row in attacked["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == attacked_vnd["occurrence_id"]
    )
    row["label_match"]["retrieval_scope_owner_occurrence_id"] = attacked_deposit[
        "retrieval_occurrence_id"
    ]
    attacked["row_axis"] = subject._regenerate_v1_axis(attacked["row_axis"])
    _coherently_rehash_occurrence(attacked)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="one-edit exact-source structural occurrence proof|retrieval occurrence owner",
    ):
        subject._validate_result(attacked)


def test_f3_one_edit_vnd_without_independent_exact_source_keeps_discount_ambiguous() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VNB", "50", "40"),
            ("Chiết khấu, tái chiết khấu", "5", "4"),
            ("Bằng ngoại tệ", "0", "0"),
        ]
    )
    vnd_line = next(line for line in pages[0]["lines"] if line["vietocr_text"] == "Bằng VNB")
    vnd_line["numeric_recognition"]["raw_prediction"] = "Bằng VNB"

    _scan, axis = _build_f3(pages)

    vnd = next(item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_LOAN_VND")
    assert "one_edit_exact_source_authority_check" not in vnd["label_match"]
    assert any(
        item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
        for item in axis["role_occurrences"]
    )
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        "ONE_EDIT_ROLE_OR_SCOPE_MATCH_SCHEMA_INELIGIBLE" in reason
        for reason in closure["unresolved_reasons"]
    )


def _exact_source_missing_term_foreign_fixture() -> list[dict[str, object]]:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "150", "130"),
            ("Tiền gửi không kỳ hạn", "", ""),
            ("Bằng VND", "20", "10"),
            ("Bằng ngoại tệ", "10", "10"),
            ("Tiền gửi có kỳ hạn", "", ""),
            ("Bằng VND", "100", "90"),
            ("Bằng ngoại lộ", "20", "20"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    foreign = next(line for line in pages[0]["lines"] if line["vietocr_text"] == "Bằng ngoại lộ")
    foreign["numeric_recognition"]["raw_prediction"] = "Bằng ngoại tệ"
    return pages


def test_f3_exact_bound_source_recovers_one_absent_contextual_additive_leaf() -> None:
    pages = _exact_source_missing_term_foreign_fixture()
    spec = _f3_spec()
    topology_pages = row_v1._topology_pages(pages)
    scan = topology_v1.build_accounting_family_topology_scan_v1(topology_pages, spec)
    candidates = candidates_v2.build_accounting_family_topology_candidates_v2(topology_pages, spec)
    binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        topology_pages, spec, candidates, candidates["regions"][0]
    )

    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        candidates["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=binding["effective_topology_region"],
        topology_candidates=candidates,
    )

    foreign = next(
        item for item in axis["role_occurrences"] if item["role"] == "TERM_DEPOSIT_FOREIGN_CURRENCY"
    )
    owner = next(item for item in axis["role_occurrences"] if item["role"] == "TERM_DEPOSIT_GROUP")
    assert foreign["label_match"]["match_kind"] == (
        "EXACT_ACCENTLESS_BOUND_SOURCE_TEXT_CHALLENGER_ALIAS"
    )
    assert foreign["label_match"]["surface"] == "Bằng ngoại tệ"
    assert foreign["scope_owner_occurrence_id"] == owner["occurrence_id"]
    assert foreign["retrieval_occurrence_id"] == foreign["occurrence_id"]
    row = next(
        row for row in axis["row_axis"]["rows"] if row["role"] == "TERM_DEPOSIT_FOREIGN_CURRENCY"
    )
    assert [value["parsed_token"]["coefficient"] for value in row["values"]] == [20, 20]
    assert not any(
        check.get("role") == "TERM_DEPOSIT_FOREIGN_CURRENCY"
        for check in axis["one_edit_exact_source_structural_proofs"]["checks"]
    )
    subject.validate_accounting_family_occurrence_row_axis_replay_v2(
        axis,
        pages,
        spec,
        scan,
        candidates["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=binding["effective_topology_region"],
        topology_candidates=candidates,
    )


def test_f3_bound_source_challenger_cannot_retype_one_occupied_vietocr_line() -> None:
    pages = _exact_source_missing_term_foreign_fixture()
    original_foreign = next(
        line for line in pages[0]["lines"] if line["vietocr_text"] == "Bằng ngoại lộ"
    )
    original_foreign["numeric_recognition"]["raw_prediction"] = "Bằng ngoại lộ"
    vnd_lines = [line for line in pages[0]["lines"] if line["vietocr_text"] == "Bằng VND"]
    term_vnd = vnd_lines[1]
    term_vnd["numeric_recognition"]["raw_prediction"] = "Bằng ngoại tệ"

    _scan, axis = _build_f3(pages)

    same_physical_line = [
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["label_match"]["page_sequence"] == 1
        and occurrence["label_match"]["source_line_index"] == term_vnd["line_ordinal"]
        and occurrence["label_match"]["end_source_line_index"] == term_vnd["line_ordinal"]
    ]
    assert [occurrence["role"] for occurrence in same_physical_line] == ["TERM_DEPOSIT_VND"]
    assert not any(
        occurrence["role"] == "TERM_DEPOSIT_FOREIGN_CURRENCY"
        and occurrence["label_match"]["match_kind"]
        == "EXACT_ACCENTLESS_BOUND_SOURCE_TEXT_CHALLENGER_ALIAS"
        for occurrence in axis["role_occurrences"]
    )


def test_f3_bound_source_challenger_abstains_on_cross_role_same_unoccupied_span() -> None:
    span = {
        "document_line_ordinal": 23,
        "end_document_line_ordinal": 23,
        "end_source_line_index": 23,
        "page_sequence": 1,
        "source_line_index": 23,
    }
    first = ({**span, "role": "TERM_DEPOSIT_FOREIGN_CURRENCY"}, {"role": "TERM_DEPOSIT_GROUP"})
    second = (
        {**span, "role": "DEMAND_DEPOSIT_FOREIGN_CURRENCY"},
        {"role": "DEMAND_DEPOSIT_GROUP"},
    )

    assert subject._unique_exact_bound_source_challengers_v1([first, second]) == []


@pytest.mark.parametrize(
    "mutation",
    [
        "SOURCE_NOT_EXACT",
        "ONE_EDIT_RETRIEVAL_EXISTS",
        "OWNER_NOT_RETRIEVED_EXACTLY",
        "NO_SAME_ROW_NUMERIC",
        "REPEATED_SOURCE_CHALLENGER",
    ],
)
def test_f3_bound_source_challenger_fails_closed_on_ambiguous_or_incomplete_shape(
    mutation: str,
) -> None:
    pages = _exact_source_missing_term_foreign_fixture()
    foreign = next(line for line in pages[0]["lines"] if line["vietocr_text"] == "Bằng ngoại lộ")
    if mutation == "SOURCE_NOT_EXACT":
        foreign["numeric_recognition"]["raw_prediction"] = "Bằng ngoại hế"
    elif mutation == "ONE_EDIT_RETRIEVAL_EXISTS":
        foreign["vietocr_text"] = "Bằng ngoại tệx"
    elif mutation == "OWNER_NOT_RETRIEVED_EXACTLY":
        owner = next(
            line for line in pages[0]["lines"] if line["vietocr_text"] == "Tiền gửi có kỳ hạn"
        )
        owner["vietocr_text"] = "Tiền gửi có kỳ hạx"
        owner["numeric_recognition"]["raw_prediction"] = "Tiền gửi có kỳ hạn"
    elif mutation == "NO_SAME_ROW_NUMERIC":
        label_ordinal = foreign["line_ordinal"]
        for line in pages[0]["lines"]:
            if line["line_ordinal"] in {label_ordinal + 1, label_ordinal + 2}:
                line["vietocr_text"] = ""
                line["numeric_recognition"]["raw_prediction"] = ""
    elif mutation == "REPEATED_SOURCE_CHALLENGER":
        lines = pages[0]["lines"]
        insertion = foreign["line_ordinal"] + 3
        top = foreign["bbox"][1] + 21
        lines[insertion:insertion] = [
            _line(900, "Bằng ngoại lộ", "Bằng ngoại tệ", [290, top, 470, top + 20]),
            _line(901, "1", "1", [610, top, 700, top + 20]),
            _line(902, "1", "1", [810, top, 900, top + 20]),
        ]
        _reindex_page_lines(lines)

    _scan, axis = _build_f3(pages)
    challenged = [
        item
        for item in axis["role_occurrences"]
        if item["label_match"]["match_kind"]
        == "EXACT_ACCENTLESS_BOUND_SOURCE_TEXT_CHALLENGER_ALIAS"
    ]
    assert not any(item["role"] == "TERM_DEPOSIT_FOREIGN_CURRENCY" for item in challenged)


def test_f3_bound_source_challenger_never_admits_context_free_compound_or_bad_crop() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Tiền gửi có kỳ hạn bằng ngoại lộ", "20", "20"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    compound = next(
        line
        for line in pages[0]["lines"]
        if line["vietocr_text"] == "Tiền gửi có kỳ hạn bằng ngoại lộ"
    )
    compound["numeric_recognition"]["raw_prediction"] = "Tiền gửi có kỳ hạn bằng ngoại tệ"
    _scan, axis = _build_f3(pages)
    assert not any(
        item["label_match"]["match_kind"] == "EXACT_ACCENTLESS_BOUND_SOURCE_TEXT_CHALLENGER_ALIAS"
        for item in axis["role_occurrences"]
    )

    del compound["crop_ref"]
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="shared input contract drifted",
    ):
        _build_f3(pages)


@pytest.mark.parametrize(
    "intervening_label",
    ["Khác", "Dự phòng rủi ro cho vay các TCTD khác"],
)
def test_f3_generic_discount_interval_stops_at_any_intervening_loan_sibling(
    intervening_label: str,
) -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "45", "36"),
                (intervening_label, "5", "4"),
                ("Chiết khấu, tái chiết khấu", "2", "1"),
            ]
        )
    )

    generic = next(
        item
        for item in axis["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
    )
    assert generic["source_scope_binding"] is None
    assert not any(
        item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
        and item["label_match"]["document_line_ordinal"]
        == generic["label_match"]["document_line_ordinal"]
        for item in axis["role_occurrences"]
    )


def test_f3_touching_wrapped_explicit_vnd_discount_overrides_prior_fx_scope() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng ngoại tệ", "20", "10"),
            ("Chiết khấu, tái chiết khấu", "", ""),
            ("Bằng VND", "5", "4"),
        ]
    )
    lines = pages[0]["lines"]
    prefix = next(line for line in lines if line["vietocr_text"] == "Chiết khấu, tái chiết khấu")
    suffix = next(
        line
        for line in lines
        if line["vietocr_text"] == "Bằng VND" and line["line_ordinal"] > prefix["line_ordinal"]
    )
    delta = prefix["bbox"][3] - suffix["bbox"][1]
    suffix_top = suffix["bbox"][1]
    for line in lines:
        if line["bbox"][1] == suffix_top:
            line["bbox"][1] += delta
            line["bbox"][3] += delta

    _scan, axis = _build_f3(pages)

    explicit = next(
        item
        for item in axis["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
        and item["source_scope_binding"] is not None
        and item["source_scope_binding"]["binding_kind"]
        == "EXPLICIT_EXACT_SOURCE_SUBSCOPE_IN_LABEL"
    )
    assert explicit["source_scope_binding"]["source_scope_role"] == "INTERBANK_LOAN_VND"
    assert not any(
        item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY"
        and item["label_match"]["document_line_ordinal"]
        == explicit["label_match"]["document_line_ordinal"]
        for item in axis["role_occurrences"]
    )


@pytest.mark.parametrize(
    ("rows", "expected_role", "expected_kind"),
    [
        (
            [
                ("Tiền gửi tại các TCTD khác", "98", "89"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "60", "50"),
                ("Tiền gửi có kỳ hạn", "40", "40"),
                ("Bằng VND", "40", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ],
            "INTERBANK_DEPOSIT_PROVISION",
            "UNIQUE_EXACT_RECURSIVE_PARENT_DIRECT_FRONTIER_EQUATION",
        ),
        (
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "52", "41"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ],
            "TOTAL_INTERBANK_PROVISION",
            "UNIQUE_EXACT_RECURSIVE_PARENT_DIRECT_FRONTIER_EQUATION",
        ),
        (
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "48", "39"),
                ("Bằng VND", "50", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ],
            "INTERBANK_LOAN_PROVISION",
            "UNIQUE_EXACT_RECURSIVE_PARENT_DIRECT_FRONTIER_EQUATION",
        ),
    ],
)
def test_f3_provision_schema_role_is_bound_by_exact_parent_interval(
    rows: list[tuple[str, str, str]], expected_role: str, expected_kind: str | None
) -> None:
    pages = _f3_pages(rows)
    scan, axis = _build_f3(pages)

    occurrence = next(item for item in axis["role_occurrences"] if item["role"] == expected_role)
    if expected_kind is None:
        assert occurrence["source_scope_binding"] is None
    else:
        assert occurrence["source_scope_binding"]["binding_kind"] == expected_kind
    effective = total_v1.project_accounting_family_coextensive_parent_total_region_v1(
        _f3_spec(), scan, scan["regions"][0]
    )
    subject.validate_accounting_family_occurrence_row_axis_replay_v2(
        axis,
        pages,
        _f3_spec(),
        scan,
        scan["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
    )


def _remove_unlabeled_fixture_carrier_labels(
    pages: list[dict[str, object]], labels: set[str]
) -> None:
    lines = pages[0]["lines"]
    lines[:] = [line for line in lines if line["vietocr_text"] not in labels]
    _reindex_page_lines(lines)


def _f3_exact_trailing_root_provision_pages(
    *,
    extra_after_provision: tuple[tuple[str, str, str], ...] = (),
    trailing_rows: tuple[tuple[str, str, str], ...] = (("UNLABELED ROOT", "150", "130"),),
) -> list[dict[str, object]]:
    pages = _f3_parent_frontier_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Tiền gửi không kỳ hạn", "", ""),
            ("Bằng VND", "50", "40"),
            ("Bằng ngoại tệ", "10", "10"),
            ("Tiền gửi có kỳ hạn", "", ""),
            ("Bằng VND", "30", "30"),
            ("Bằng ngoại tệ", "10", "10"),
            ("Cho vay các TCTD khác", "52", "41"),
            ("Bằng VND", "52", "41"),
            ("Dự phòng rủi ro", "-2", "-1"),
            *extra_after_provision,
            *trailing_rows,
        ]
    )
    lines = pages[0]["lines"]
    lines[:] = [
        line
        for line in lines
        if not (line["vietocr_text"] in {"150", "130"} and line["bbox"][1] == 155)
    ]
    _remove_unlabeled_fixture_carrier_labels(
        pages, {label for label, _current, _prior in trailing_rows}
    )
    return pages


def test_f3_generic_deposit_provision_uses_exact_immediate_internal_parent_subtotal() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "", ""),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Bằng VND", "60", "50"),
            ("Tiền gửi có kỳ hạn", "40", "40"),
            ("Bằng VND", "40", "40"),
            ("Dự phòng rủi ro", "0", "0"),
            ("UNLABELED DEPOSIT", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    _remove_unlabeled_fixture_carrier_labels(pages, {"UNLABELED DEPOSIT"})

    _scan, axis = _build_f3(pages)

    provision = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "INTERBANK_DEPOSIT_PROVISION"
    )
    equation = provision["source_scope_binding"]["geometry"]["equation"]
    assert provision["scope_owner_role"] == "INTERBANK_DEPOSIT_GROUP"
    assert equation["parent_role"] == "INTERBANK_DEPOSIT_GROUP"
    assert [component["role"] for component in equation["component_frontier"]] == [
        "DEMAND_DEPOSIT_GROUP",
        "TERM_DEPOSIT_GROUP",
        "INTERBANK_DEPOSIT_PROVISION",
    ]
    assert [number["coefficient"] for number in equation["result"]["numbers"]] == [100, 90]
    matching_clusters = [
        cluster
        for cluster in axis["internal_unassigned_numeric_clusters"]
        if cluster["sample_ids"] == equation["result"]["sample_ids"]
    ]
    assert len(matching_clusters) == 1
    assert (
        closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
            axis, _f3_spec(), _f3_hierarchy()
        )["status"]
        == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    )


def test_f3_generic_root_provision_uses_exact_immediate_trailing_result_and_context() -> None:
    pages = _f3_exact_trailing_root_provision_pages()

    _scan, axis = _build_f3(pages)

    provision = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    equation = provision["source_scope_binding"]["geometry"]["equation"]
    trailing = axis["row_axis"]["trailing_value_rows"]
    assert len(trailing) == 1
    assert equation["parent_role"] == "INTERBANK_DEPOSITS_AND_LOANS"
    assert equation["result"]["sample_ids"] == [
        value["sample_id"] for value in trailing[0]["values"]
    ]
    assert [number["coefficient"] for number in equation["result"]["numbers"]] == [150, 130]
    context = _f3_column_context(axis, pages)
    assert context["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [lane["resolved_period"] for lane in context["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    assert [lane["magnitude_power10"] for lane in context["unit_axis"]] == [6, 6]
    assert (
        closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
            axis, _f3_spec(), _f3_hierarchy()
        )["status"]
        == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    )


def test_f3_generic_root_provision_rejects_inexact_derived_structural_frontier() -> None:
    pages = _f3_exact_trailing_root_provision_pages()
    foreign_label = next(
        line for line in pages[0]["lines"] if line["vietocr_text"] == "Bằng ngoại tệ"
    )
    current_value = pages[0]["lines"][foreign_label["line_ordinal"] + 1]
    current_value["vietocr_text"] = "11"
    current_value["numeric_recognition"]["raw_prediction"] = "11"

    _scan, axis = _build_f3(pages)

    provision = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["label_match"]["normalized_surface"] == "du phong rui ro"
    )
    assert provision["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    assert provision["source_scope_binding"] is None


def test_f3_generic_root_provision_receipt_rejects_coherent_selected_interval_tamper() -> None:
    pages = _f3_exact_trailing_root_provision_pages()
    _scan, axis = _build_f3(pages)
    attacked = copy.deepcopy(axis)
    provision = next(
        occurrence
        for occurrence in attacked["role_occurrences"]
        if occurrence["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    receipt = provision["source_scope_binding"]
    receipt["interval"]["end_document_line_ordinal_exclusive"] -= 1
    material = copy.deepcopy(receipt)
    material.pop("binding_id")
    receipt["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(material)
    _coherently_replace_source_scope_binding(attacked, provision, receipt)
    _coherently_rehash_occurrence(attacked)

    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="selected root interval drifted",
    ):
        subject._validate_result(attacked)


@pytest.mark.parametrize(
    ("trailing_rows", "extra_after_provision"),
    [
        ((("UNLABELED ROOT", "151", "130"),), ()),
        ((("UNLABELED ROOT", "150", ""),), ()),
        (
            (
                ("UNLABELED ROOT A", "150", "130"),
                ("UNLABELED ROOT B", "150", "130"),
            ),
            (),
        ),
        (
            (("UNLABELED ROOT", "150", "130"),),
            (("Cho vay khách hàng", "", ""),),
        ),
    ],
    ids=["nonexact", "partial", "duplicate-exact", "later-structural-reset"],
)
def test_f3_generic_root_provision_rejects_nonunique_or_out_of_interval_trailing_carrier(
    trailing_rows: tuple[tuple[str, str, str], ...],
    extra_after_provision: tuple[tuple[str, str, str], ...],
) -> None:
    pages = _f3_exact_trailing_root_provision_pages(
        extra_after_provision=extra_after_provision,
        trailing_rows=trailing_rows,
    )

    _scan, axis = _build_f3(pages)

    provision = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["label_match"]["normalized_surface"] == "du phong rui ro"
    )
    assert provision["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    assert provision["source_scope_binding"] is None


def test_f3_generic_deposit_provision_rejects_nonadjacent_internal_subtotal() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "", ""),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Bằng VND", "60", "50"),
            ("Tiền gửi có kỳ hạn", "40", "40"),
            ("Bằng VND", "40", "40"),
            ("Dự phòng rủi ro", "0", "0"),
            ("UNLABELED DEPOSIT", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    carrier_label = next(
        line for line in pages[0]["lines"] if line["vietocr_text"] == "UNLABELED DEPOSIT"
    )
    carrier_label["vietocr_text"] = ""
    carrier_label["numeric_recognition"]["raw_prediction"] = ""

    _scan, axis = _build_f3(pages)

    provision = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["label_match"]["normalized_surface"] == "du phong rui ro"
    )
    assert provision["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    assert provision["source_scope_binding"] is None


@pytest.mark.parametrize(
    "rows",
    [
        [
            ("Tiền gửi tại các TCTD khác", "99", "89"),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Tiền gửi có kỳ hạn", "40", "40"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ],
        [
            ("Tiền gửi tại các TCTD khác", "98", "89"),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Tiền gửi có kỳ hạn", "40", "40"),
            ("Dự phòng rủi ro", "-2", ""),
        ],
        [
            ("Tiền gửi tại các TCTD khác", "96", "88"),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Tiền gửi có kỳ hạn", "40", "40"),
            ("Dự phòng rủi ro", "-2", "-1"),
            ("Dự phòng", "-2", "-1"),
        ],
        [
            ("Tiền gửi tại các TCTD khác", "98.1", "89"),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Tiền gửi có kỳ hạn", "40", "40"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ],
        [
            ("Tiền gửi tại các TCTD khác", "98", "89"),
            ("Tiền gửi có kỳ hạn", "40", "40"),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ],
        [
            ("Tiền gửi tại các TCTD khác", "98", "89"),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Tiền gửi có kỳ hạn", "35", "35"),
            ("Khoản chưa rõ", "5", "5"),
            ("Dự phòng rủi ro", "3", "4"),
        ],
        [
            ("Tiền gửi tại các TCTD khác", "98", "89"),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Tiền gửi có kỳ hạn", "40", "40"),
            ("Dự phòng tiền gửi tại các TCTD khác", "-2", "-1"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ],
        [
            ("Tiền gửi tại các TCTD khác", "98", "89"),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Tiền gửi có kỳ hạn", "40", "40"),
            ("Tiền gửi tại các TCTD khác", "10", "10"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ],
    ],
)
def test_f3_recursive_parent_provision_fails_closed_without_one_exact_frontier(
    rows: list[tuple[str, str, str]],
) -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                *rows,
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )

    assert not [
        occurrence
        for occurrence in axis["role_occurrences"]
        if type(occurrence["source_scope_binding"]) is dict
        and occurrence["source_scope_binding"].get("binding_kind")
        == "UNIQUE_EXACT_RECURSIVE_PARENT_DIRECT_FRONTIER_EQUATION"
    ]


def test_f3_recursive_provision_rejects_visible_leaf_under_missing_direct_subtotal() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "58", "49"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "60", "50"),
                # This coextensive source creates a visible TERM leaf, but the
                # structural TERM occurrence has no independently bound row.
                ("Tiền gửi có kỳ hạn bằng VND", "40", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )

    term_group = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "TERM_DEPOSIT_GROUP"
    )
    term_leaf = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "TERM_DEPOSIT_VND"
    )
    provision = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert term_group["has_bound_value_row"] is False
    assert term_leaf["has_bound_value_row"] is True
    assert provision["source_scope_binding"] is None


def test_f3_recursive_provision_validator_rejects_coherent_zero_frontier_removal() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "58", "49"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "60", "50"),
                ("Tiền gửi có kỳ hạn", "0", "0"),
                ("Bằng VND", "0", "0"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )
    attacked = copy.deepcopy(axis)
    provision = next(
        occurrence
        for occurrence in attacked["role_occurrences"]
        if occurrence["role"] == "INTERBANK_DEPOSIT_PROVISION"
    )
    receipt = provision["source_scope_binding"]
    equation = receipt["geometry"]["equation"]
    term_index = next(
        index
        for index, component in enumerate(equation["component_frontier"])
        if component["role"] == "TERM_DEPOSIT_GROUP"
    )
    equation["component_frontier"].pop(term_index)
    receipt["geometry"]["ordered_source_label_bboxes"].pop(term_index)
    equation_material = copy.deepcopy(equation)
    equation_material.pop("equation_id")
    equation["equation_id"] = "aforav2:direct-frontier-equation:" + canonical_json_sha256_v1(
        equation_material
    )
    binding_material = copy.deepcopy(receipt)
    binding_material.pop("binding_id")
    receipt["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(binding_material)
    _coherently_replace_source_scope_binding(attacked, provision, receipt)
    _coherently_rehash_occurrence(attacked)

    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="direct frontier is incomplete or mixed",
    ):
        subject._validate_result(attacked)


def test_f3_root_provision_never_double_counts_a_loan_result_and_its_leaf() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "52", "41"),
                ("Bằng VND", "52", "41"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )

    equation = next(
        occurrence["source_scope_binding"]["geometry"]["equation"]
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    assert [component["role"] for component in equation["component_frontier"]] == [
        "INTERBANK_DEPOSIT_GROUP",
        "INTERBANK_LOAN_GROUP",
        "TOTAL_INTERBANK_PROVISION",
    ]


def test_f3_root_provision_excludes_known_nonadditive_discount_from_loan_sum() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "52", "41"),
                ("Bằng VND", "52", "41"),
                ("Chiết khấu, tái chiết khấu bằng VND", "5", "4"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )

    equation = next(
        occurrence["source_scope_binding"]["geometry"]["equation"]
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    assert [component["role"] for component in equation["component_frontier"]] == [
        "INTERBANK_DEPOSIT_GROUP",
        "INTERBANK_LOAN_GROUP",
        "TOTAL_INTERBANK_PROVISION",
    ]


def test_f3_root_provision_rejects_exact_root_with_contradictory_deposit_frontier() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "98", "89"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "60", "50"),
                ("Tiền gửi có kỳ hạn", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Cho vay các TCTD khác", "54", "42"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )

    provision = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert provision["source_scope_binding"] is None


@pytest.mark.parametrize("partial_leaf", [False, True])
def test_f3_root_provision_recursively_rejects_invalid_demand_leaf_frontier(
    partial_leaf: bool,
) -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "98", "89"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "40", "30"),
                ("Bằng ngoại tệ", "10", "" if partial_leaf else "10"),
                ("Tiền gửi có kỳ hạn", "38", "39"),
                ("Bằng VND", "38", "39"),
                ("Cho vay các TCTD khác", "54", "42"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )

    provision = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert provision["source_scope_binding"] is None


def test_recursive_support_rejects_leaf_owned_by_repeated_same_role_parent() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "98", "89"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "60", "50"),
                ("Tiền gửi có kỳ hạn", "38", "39"),
                ("Bằng VND", "38", "39"),
                ("Cho vay các TCTD khác", "54", "42"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )
    demand = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "DEMAND_DEPOSIT_GROUP"
    )
    demand_row = next(
        row
        for row in axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == demand["occurrence_id"]
    )
    rows_by_occurrence_id = {
        row["label_match"]["occurrence_id"]: [row] for row in axis["row_axis"]["rows"]
    }
    occurrences = copy.deepcopy(axis["role_occurrences"])
    effective_roles = {id(occurrence): occurrence["role"] for occurrence in occurrences}
    assert subject._recursive_direct_component_support_is_exact(
        occurrences,
        rows_by_occurrence_id,
        effective_roles,
        result_role="DEMAND_DEPOSIT_GROUP",
        result_row=demand_row,
    )

    repeated = copy.deepcopy(
        next(
            occurrence for occurrence in occurrences if occurrence["role"] == "DEMAND_DEPOSIT_GROUP"
        )
    )
    repeated["occurrence_id"] = "aforav2:occurrence:" + "f" * 64
    repeated["label_match"]["occurrence_id"] = repeated["occurrence_id"]
    leaf = next(
        occurrence for occurrence in occurrences if occurrence["role"] == "DEMAND_DEPOSIT_VND"
    )
    leaf["scope_owner_occurrence_id"] = repeated["occurrence_id"]
    leaf["label_match"]["scope_owner_occurrence_id"] = repeated["occurrence_id"]
    occurrences.append(repeated)
    effective_roles = {id(occurrence): occurrence["role"] for occurrence in occurrences}

    assert not subject._recursive_direct_component_support_is_exact(
        occurrences,
        rows_by_occurrence_id,
        effective_roles,
        result_role="DEMAND_DEPOSIT_GROUP",
        result_row=demand_row,
    )


def test_recursive_deposit_support_rejects_visual_child_with_wrong_structural_owner() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "98", "89"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "60", "50"),
                ("Tiền gửi có kỳ hạn", "38", "39"),
                ("Bằng VND", "38", "39"),
                ("Cho vay các TCTD khác", "54", "42"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )
    deposit = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "INTERBANK_DEPOSIT_GROUP"
    )
    deposit_row = next(
        row
        for row in axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == deposit["occurrence_id"]
    )
    rows_by_occurrence_id = {
        row["label_match"]["occurrence_id"]: [row] for row in axis["row_axis"]["rows"]
    }
    occurrences = copy.deepcopy(axis["role_occurrences"])
    effective_roles = {id(occurrence): occurrence["role"] for occurrence in occurrences}
    assert subject._recursive_direct_component_support_is_exact(
        occurrences,
        rows_by_occurrence_id,
        effective_roles,
        result_role="INTERBANK_DEPOSIT_GROUP",
        result_row=deposit_row,
    )

    loan = next(
        occurrence for occurrence in occurrences if occurrence["role"] == "INTERBANK_LOAN_GROUP"
    )
    demand = next(
        occurrence for occurrence in occurrences if occurrence["role"] == "DEMAND_DEPOSIT_GROUP"
    )
    demand["scope_owner_occurrence_id"] = loan["occurrence_id"]
    demand["label_match"]["scope_owner_occurrence_id"] = loan["occurrence_id"]

    assert not subject._recursive_direct_component_support_is_exact(
        occurrences,
        rows_by_occurrence_id,
        effective_roles,
        result_role="INTERBANK_DEPOSIT_GROUP",
        result_row=deposit_row,
    )

    for field in (
        "document_line_ordinal",
        "end_document_line_ordinal",
        "end_source_line_index",
        "page_sequence",
        "source_line_index",
    ):
        demand["label_match"][field] = deposit["label_match"][field]
    assert not subject._recursive_direct_component_support_is_exact(
        occurrences,
        rows_by_occurrence_id,
        effective_roles,
        result_role="INTERBANK_DEPOSIT_GROUP",
        result_row=deposit_row,
    )

    forged_owner_id = "aforav2:occurrence:" + "e" * 64
    demand["scope_owner_occurrence_id"] = forged_owner_id
    demand["label_match"]["scope_owner_occurrence_id"] = forged_owner_id
    assert not subject._recursive_direct_component_support_is_exact(
        occurrences,
        rows_by_occurrence_id,
        effective_roles,
        result_role="INTERBANK_DEPOSIT_GROUP",
        result_row=deposit_row,
    )


def test_f3_one_edit_family_parent_binds_only_through_exact_root_frontier() -> None:
    pages = _f3_parent_frontier_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Bằng VND", "60", "50"),
            ("Tiền gửi có kỳ hạn", "40", "40"),
            ("Bằng VND", "40", "40"),
            ("Cho vay các TCTD khác", "52", "41"),
            ("Bằng VND", "52", "41"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ]
    )
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho yay các TCTD khác"
    scan, axis = _build_f3(pages)
    source_receipt = axis["one_edit_exact_source_structural_proofs"]
    assert source_receipt["format_version"] == one_edit_v1.FORMAT_VERSION
    assert source_receipt["status"] == "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY"
    assert source_receipt["metrics"] == {
        "exact_bound_count": 0,
        "selected_one_edit_match_count": 1,
        "unresolved_match_count": 1,
    }
    context = _f3_column_context(axis, pages)
    assert context["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"

    projected = subject.project_accounting_family_one_edit_parent_frontier_authority_v2(
        axis,
        context,
        pages,
        _f3_spec(),
        scan["regions"][0],
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    receipt = projected["one_edit_exact_source_structural_proofs"]
    assert receipt["format_version"] == one_edit_v1.PARENT_FRONTIER_FORMAT_VERSION
    assert receipt["status"] == "EXACT_SOURCE_AUTHORITY_BOUND"
    assert receipt["unresolved_reasons"] == []
    assert one_edit_v1.family_parent_has_exact_authority_v1(receipt) is False
    assert (
        one_edit_v1.family_parent_has_exact_authority_v1(
            receipt,
            structural_evidence=_f3_structural_evidence(projected),
        )
        is True
    )
    proof = receipt["parent_frontier_authority"]
    equation = proof["source_scope_binding"]["geometry"]["equation"]
    assert [item["role"] for item in equation["component_frontier"]] == [
        "INTERBANK_DEPOSIT_GROUP",
        "INTERBANK_LOAN_GROUP",
        "TOTAL_INTERBANK_PROVISION",
    ]
    repeated_vnd_occurrences = [
        occurrence
        for occurrence in projected["role_occurrences"]
        if occurrence["label_match"]["normalized_surface"] == "bang vnd"
    ]
    assert len(repeated_vnd_occurrences) == 3
    assert (
        len({occurrence["occurrence_id"] for occurrence in repeated_vnd_occurrences})
        == len({occurrence["scope_owner_occurrence_id"] for occurrence in repeated_vnd_occurrences})
        == 3
    )
    assert [item["coefficient"] for item in equation["result"]["numbers"]] == [150, 130]
    assert [item["resolved_period"] for item in proof["column_context_receipt"]["period_axis"]] == [
        "31/12/2025",
        "31/12/2024",
    ]
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        projected,
        _f3_spec(),
        _f3_hierarchy(),
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    assert closure["one_edit_exact_source_structural_proofs"] == receipt
    assert [
        record["disposition"]
        for record in closure["coverage_receipt"]
        if record["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
    ] == ["ONE_EDIT_FAMILY_PARENT_RESULT_EXACT_FRONTIER_CORROBORATION"]

    authority_pages = subject._one_edit_authority_pages_v2(row_v1._pages(pages))
    parsed_authority_pages = one_edit_v1._pages_with_occurrence_geometry_v1(authority_pages)
    expanded = one_edit_v1._canonical_expanded_occurrence_region_v1(
        parsed_authority_pages,
        _f3_spec(),
        scan["regions"][0],
    )
    assert (
        one_edit_v1.validate_accounting_family_one_edit_exact_authority_replay_v1(
            receipt,
            authority_pages,
            _f3_spec(),
            scan["regions"][0],
            expanded,
            structural_evidence=_f3_structural_evidence(projected),
            column_context=context,
            column_context_document_pages=pages,
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=["MONEY", "MONEY"],
        )
        == receipt
    )


def _coherently_rehash_parent_frontier_column_context(axis: dict) -> None:
    receipt = axis["one_edit_exact_source_structural_proofs"]
    proof = receipt["parent_frontier_authority"]
    context = proof["column_context_receipt"]
    context_material = copy.deepcopy(context)
    context_material.pop("column_context_id")
    context["column_context_id"] = "afccv1:context:" + canonical_json_sha256_v1(context_material)
    receipt["input_binding"]["column_context_sha256"] = canonical_json_sha256_v1(context)
    proof["input_binding"] = copy.deepcopy(receipt["input_binding"])
    proof_material = copy.deepcopy(proof)
    proof_material.pop("proof_id")
    proof["proof_id"] = "afeoepfav1:proof:" + canonical_json_sha256_v1(proof_material)
    receipt_material = copy.deepcopy(receipt)
    receipt_material.pop("receipt_id")
    receipt["receipt_id"] = "afeoeav1:receipt:" + canonical_json_sha256_v1(receipt_material)
    _coherently_rehash_occurrence(axis)


@pytest.mark.parametrize("attack", ["PERIOD", "UNIT"])
def test_f3_parent_frontier_public_replay_rejects_coherent_period_or_unit_tamper(
    attack: str,
) -> None:
    pages = _f3_parent_frontier_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "52", "41"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ]
    )
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho yay các TCTD khác"
    scan, axis = _build_f3(pages)
    context = _f3_column_context(axis, pages)
    projected = subject.project_accounting_family_one_edit_parent_frontier_authority_v2(
        axis,
        context,
        pages,
        _f3_spec(),
        scan["regions"][0],
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )
    attacked = copy.deepcopy(projected)
    attacked_context = attacked["one_edit_exact_source_structural_proofs"][
        "parent_frontier_authority"
    ]["column_context_receipt"]
    if attack == "PERIOD":
        attacked_context["period_axis"][0]["resolved_period"] = "31/12/2099"
        attacked_context["document_period_context"]["current_period_end"] = "31/12/2099"
        attacked_context["document_period_context"]["reporting_year"] = 2099
        attacked_context["document_period_context"]["observed_dates"][1]["date"] = "31/12/2099"
    else:
        attacked_context["document_unit_context"]["currency"] = "USD"
        for lane in attacked_context["unit_axis"]:
            lane["currency"] = "USD"
    _coherently_rehash_parent_frontier_column_context(attacked)

    # Shape-only consumers cannot authenticate source pages.  The public
    # replay boundary must reject the coherently rehashed object before it can
    # become selected schema evidence.
    attacked_closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        attacked,
        _f3_spec(),
        _f3_hierarchy(),
    )
    assert attacked_closure["status"] == ("HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO")
    authority_pages = subject._one_edit_authority_pages_v2(row_v1._pages(pages))
    expanded = one_edit_v1._canonical_expanded_occurrence_region_v1(
        one_edit_v1._pages_with_occurrence_geometry_v1(authority_pages),
        _f3_spec(),
        scan["regions"][0],
    )
    with pytest.raises(
        one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error,
        match="column context does not replay exactly",
    ):
        one_edit_v1.validate_accounting_family_one_edit_exact_authority_replay_v1(
            attacked["one_edit_exact_source_structural_proofs"],
            authority_pages,
            _f3_spec(),
            scan["regions"][0],
            expanded,
            structural_evidence=_f3_structural_evidence(attacked),
            column_context=attacked_context,
            column_context_document_pages=pages,
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=["MONEY", "MONEY"],
        )
    evaluation = json.loads(_F3_EVALUATION_PATH.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="column context does not replay exactly"):
        sweep_v1._selected_v4_one_edit_authority_v1(
            {
                "additive_closure": attacked_closure,
                "candidate_ordinal": 0,
                "column_context": attacked_context,
                "column_context_visible_dash_rescues": (),
                "one_edit_exact_source_structural_proofs": attacked[
                    "one_edit_exact_source_structural_proofs"
                ],
                "row_axis": attacked["row_axis"],
            },
            joined_pages=pages,
            family_spec=_f3_spec(),
            topology_candidates=scan,
            evaluation_spec=evaluation,
        )


@pytest.mark.parametrize(
    "rows",
    [
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "52", "41"),
            ("Dự phòng rủi ro", "-3", "-1"),
        ],
        [
            ("Tiền gửi tại các TCTD khác", "100", ""),
            ("Cho vay các TCTD khác", "52", "41"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ],
        [
            ("Tiền gửi tại các TCTD khác", "50", "45"),
            ("Tiền gửi tại các TCTD khác", "50", "45"),
            ("Cho vay các TCTD khác", "52", "41"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ],
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Dự phòng rủi ro", "-2", "-1"),
            ("Cho vay các TCTD khác", "52", "41"),
        ],
    ],
    ids=["one-lane-mismatch", "partial-lane", "duplicate-role", "reordered-frontier"],
)
def test_f3_one_edit_family_parent_frontier_fails_closed_without_one_complete_equation(
    rows: list[tuple[str, str, str]],
) -> None:
    pages = _f3_parent_frontier_pages(rows)
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho yay các TCTD khác"
    scan, axis = _build_f3(pages)
    context = _f3_column_context(axis, pages)

    projected = subject.project_accounting_family_one_edit_parent_frontier_authority_v2(
        axis,
        context,
        pages,
        _f3_spec(),
        scan["regions"][0],
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )

    assert projected["one_edit_exact_source_structural_proofs"]["format_version"] == (
        one_edit_v1.FORMAT_VERSION
    )
    assert (
        projected["one_edit_exact_source_structural_proofs"]
        == (axis["one_edit_exact_source_structural_proofs"])
    )


def test_f3_one_edit_parent_frontier_coherent_component_id_swap_fails_in_closure() -> None:
    pages = _f3_parent_frontier_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "52", "41"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ]
    )
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho yay các TCTD khác"
    scan, axis = _build_f3(pages)
    projected = subject.project_accounting_family_one_edit_parent_frontier_authority_v2(
        axis,
        _f3_column_context(axis, pages),
        pages,
        _f3_spec(),
        scan["regions"][0],
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )
    attacked = copy.deepcopy(projected)
    receipt = attacked["one_edit_exact_source_structural_proofs"]
    proof = receipt["parent_frontier_authority"]
    first = proof["component_frontier_bindings"][0]
    second = proof["component_frontier_bindings"][1]
    first["occurrence_id"], second["occurrence_id"] = (
        second["occurrence_id"],
        first["occurrence_id"],
    )
    proof_material = copy.deepcopy(proof)
    proof_material.pop("proof_id")
    proof["proof_id"] = "afeoepfav1:proof:" + canonical_json_sha256_v1(proof_material)
    receipt_material = copy.deepcopy(receipt)
    receipt_material.pop("receipt_id")
    receipt["receipt_id"] = "afeoeav1:receipt:" + canonical_json_sha256_v1(receipt_material)
    _coherently_rehash_occurrence(attacked)

    with pytest.raises(
        closure_v2.AccountingScopedHierarchicalTableClosureV2Error,
        match="occurrence row-axis validation failed",
    ):
        closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
            attacked,
            _f3_spec(),
            _f3_hierarchy(),
        )


def test_f3_parent_frontier_cluster_cannot_be_coherently_downgraded_downstream() -> None:
    pages = _f3_parent_frontier_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "52", "41"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ]
    )
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho yay các TCTD khác"
    scan, axis = _build_f3(pages)
    projected = subject.project_accounting_family_one_edit_parent_frontier_authority_v2(
        axis,
        _f3_column_context(axis, pages),
        pages,
        _f3_spec(),
        scan["regions"][0],
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        projected,
        _f3_spec(),
        _f3_hierarchy(),
    )
    attacked = copy.deepcopy(closure)
    cluster_receipt = next(
        record
        for record in attacked["coverage_receipt"]
        if record["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
    )
    cluster_id = cluster_receipt["source_record"]["cluster_id"]
    cluster_receipt["coverage_id"] = "ashtcv2:coverage:source-only:" + cluster_id
    cluster_receipt["disposition"] = "UNRESOLVED_SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER"
    attacked["status"] = "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    attacked["unresolved_reasons"] = ["SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO:" + cluster_id]
    closure_material = copy.deepcopy(attacked)
    closure_material.pop("closure_id")
    attacked["closure_id"] = "ashtcv2:closure:" + canonical_json_sha256_v1(closure_material)

    with pytest.raises(
        closure_v2.AccountingScopedHierarchicalTableClosureV2Error,
        match="parent-frontier cluster coverage drifted",
    ):
        closure_v2._validate_result(attacked)


def test_f3_root_provision_accepts_one_coextensive_roman_section_ordinal() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "52", "41"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ]
    )
    pages[0]["lines"].insert(5, _line(900, "III", "", [2, 17, 20, 40]))
    _reindex_page_lines(pages[0]["lines"])

    _scan, axis = _build_f3(pages)

    provision = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    assert provision["source_scope_binding"]["binding_kind"] == (
        "UNIQUE_EXACT_RECURSIVE_PARENT_DIRECT_FRONTIER_EQUATION"
    )


@pytest.mark.parametrize("markers", [["UNKNOWN"], ["III", "IV"]])
def test_f3_root_provision_rejects_unknown_or_duplicate_coextensive_fragments(
    markers: list[str],
) -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "52", "41"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ]
    )
    for offset, marker in enumerate(markers):
        pages[0]["lines"].insert(
            5 + offset,
            _line(900 + offset, marker, "", [2 + 20 * offset, 17, 18 + 20 * offset, 40]),
        )
    _reindex_page_lines(pages[0]["lines"])

    _scan, axis = _build_f3(pages)

    assert not [
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "TOTAL_INTERBANK_PROVISION"
        or type(occurrence.get("source_scope_binding")) is dict
        and occurrence["source_scope_binding"].get("binding_kind")
        == "UNIQUE_EXACT_RECURSIVE_PARENT_DIRECT_FRONTIER_EQUATION"
    ]


@pytest.mark.parametrize("shape", ["DUPLICATE_SAME_ROLE", "PARTIAL_LANE"])
def test_f3_root_provision_requires_one_complete_generic_occurrence(shape: str) -> None:
    provision_prior = "" if shape == "PARTIAL_LANE" else "-1"
    rows = [
        ("Tiền gửi tại các TCTD khác", "100", "90"),
        ("Cho vay các TCTD khác", "52", "41"),
        ("Dự phòng rủi ro", "-2", provision_prior),
    ]
    if shape == "DUPLICATE_SAME_ROLE":
        rows.append(("Dự phòng", "-2", "-1"))

    _scan, axis = _build_f3(_f3_pages(rows))

    assert not [
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "TOTAL_INTERBANK_PROVISION"
        or type(occurrence.get("source_scope_binding")) is dict
        and occurrence["source_scope_binding"].get("binding_kind")
        == "UNIQUE_EXACT_RECURSIVE_PARENT_DIRECT_FRONTIER_EQUATION"
    ]


def test_f3_root_provision_rejects_a_mixed_level_compensating_equation() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "52", "41"),
            ("Bằng VND", "52", "40"),
            ("Dự phòng rủi ro", "-2", "-1"),
        ]
    )
    for line, value in zip(pages[0]["lines"][3:5], ("202", "170"), strict=True):
        line["vietocr_text"] = value
        line["numeric_recognition"]["raw_prediction"] = value

    _scan, axis = _build_f3(pages)

    provision = next(
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert provision["source_scope_binding"] is None


def test_f3_same_generic_label_binds_distinct_exact_deposit_and_loan_parents() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "98", "89"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Tiền gửi có kỳ hạn", "40", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Cho vay các TCTD khác", "52", "41"),
                ("Bằng VND", "54", "42"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )

    provisions = [
        occurrence
        for occurrence in axis["role_occurrences"]
        if occurrence["role"] in {"INTERBANK_DEPOSIT_PROVISION", "INTERBANK_LOAN_PROVISION"}
    ]
    assert [occurrence["role"] for occurrence in provisions] == [
        "INTERBANK_DEPOSIT_PROVISION",
        "INTERBANK_LOAN_PROVISION",
    ]
    assert len({occurrence["retrieval_occurrence_id"] for occurrence in provisions}) == 2
    assert len({occurrence["scope_owner_occurrence_id"] for occurrence in provisions}) == 2
    assert all(
        occurrence["source_scope_binding"]["geometry"]["equation"]["parent_occurrence_id"]
        == occurrence["scope_owner_occurrence_id"]
        for occurrence in provisions
    )


def test_f3_recursive_provision_retarget_preserves_opaque_dash_region_bytes() -> None:
    png_bytes = b"\x89PNG\r\n\x1a\nopaque-authenticated-region"
    region = {"region_png_bytes": png_bytes, "sealed": object()}
    raw = {
        "column_ordinal": 0,
        "page_sequence": 1,
        "region": region,
        "role": "INTERBANK_PROVISION_AMBIGUOUS",
    }

    projected = subject._retarget_recursive_parent_provision_dash_rescues(
        (raw,),
        [
            {
                "page_sequence": 1,
                "retrieval_occurrence_id": "retrieval-provision",
                "role": "INTERBANK_PROVISION_AMBIGUOUS",
            }
        ],
        [
            {
                "retrieval_occurrence_id": "retrieval-provision",
                "role": "INTERBANK_DEPOSIT_PROVISION",
            }
        ],
    )

    assert raw["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    assert projected[0] is not raw
    assert projected[0]["role"] == "INTERBANK_DEPOSIT_PROVISION"
    assert projected[0]["region"] is region
    assert projected[0]["region"]["region_png_bytes"] is png_bytes
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="dash item must remain one mapping",
    ):
        subject._retarget_recursive_parent_provision_dash_rescues((b"opaque",), [], [])


def test_f3_bare_provision_before_loan_leaf_remains_source_only_ambiguous() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )

    occurrence = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert occurrence["source_scope_binding"] is None


def test_f3_bare_deposit_provision_before_final_deposit_role_remains_ambiguous() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "60", "50"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Tiền gửi có kỳ hạn", "40", "40"),
                ("Bằng VND", "40", "40"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )

    occurrence = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert occurrence["source_scope_binding"] is None


def test_f3_bare_root_provision_with_later_deposit_role_remains_ambiguous() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Tiền gửi có kỳ hạn", "40", "40"),
                ("Bằng VND", "40", "40"),
            ]
        )
    )

    occurrence = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert occurrence["source_scope_binding"] is None


def test_f3_root_provision_accepts_complete_exact_loan_group_total_without_leaves() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "52", "41"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )

    occurrence = next(
        item for item in axis["role_occurrences"] if item["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    assert occurrence["source_scope_binding"]["binding_kind"] == (
        "UNIQUE_EXACT_RECURSIVE_PARENT_DIRECT_FRONTIER_EQUATION"
    )
    loan = next(item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_LOAN_GROUP")
    loan_row = next(
        row
        for row in axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == loan["occurrence_id"]
    )
    assert loan_row["status"] == "VISIBLE_VALUE_LANES_BOUND"


def test_f3_partial_loan_group_total_cannot_complete_root_provision_scope() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", ""),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )

    provision = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert provision["source_scope_binding"] is None
    loan = next(item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_LOAN_GROUP")
    loan_row = next(
        row
        for row in axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == loan["occurrence_id"]
    )
    assert loan_row["status"] == "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"


def test_f3_discount_scope_never_borrows_an_anchor_from_a_prior_page() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
            ("Chiết khấu, tái chiết khấu", "5", "4"),
        ]
    )
    lines = pages[0]["lines"]
    split = next(
        index
        for index, line in enumerate(lines)
        if line["vietocr_text"] == "Chiết khấu, tái chiết khấu"
    )
    second_page_lines = lines[split:]
    pages[0]["lines"] = lines[:split]
    for ordinal, line in enumerate(second_page_lines):
        line["line_ordinal"] = ordinal
    pages.append({"lines": second_page_lines, "page_sequence": 2, "page_width": 1000})

    _scan, axis = _build_f3(pages)

    source = next(
        item
        for item in axis["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
    )
    assert source["label_match"]["page_sequence"] == 2
    assert source["source_scope_binding"] is None


def test_f3_provision_scope_never_borrows_an_anchor_from_a_prior_page() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Dự phòng rủi ro", "-2", "-1"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    lines = pages[0]["lines"]
    split = next(
        index for index, line in enumerate(lines) if line["vietocr_text"] == "Dự phòng rủi ro"
    )
    second_page_lines = lines[split:]
    pages[0]["lines"] = lines[:split]
    for ordinal, line in enumerate(second_page_lines):
        line["line_ordinal"] = ordinal
    pages.append({"lines": second_page_lines, "page_sequence": 2, "page_width": 1000})

    _scan, axis = _build_f3(pages)

    source = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert source["label_match"]["page_sequence"] == 2
    assert source["source_scope_binding"] is None


def test_f3_bare_provisions_are_unique_per_exact_parent_interval() -> None:
    _scan, distinct_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Dự phòng", "-3", "-2"),
            ]
        )
    )
    assert [
        occurrence["role"]
        for occurrence in distinct_axis["role_occurrences"]
        if occurrence["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    ] == ["INTERBANK_PROVISION_AMBIGUOUS", "INTERBANK_PROVISION_AMBIGUOUS"]

    _scan, duplicate_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Dự phòng", "-3", "-2"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )
    assert [
        occurrence["role"]
        for occurrence in duplicate_axis["role_occurrences"]
        if occurrence["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    ] == ["INTERBANK_PROVISION_AMBIGUOUS", "INTERBANK_PROVISION_AMBIGUOUS"]


def test_f3_explicit_provision_wins_over_bare_duplicate_in_same_interval() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Dự phòng tiền gửi tại các TCTD khác", "-2", "-1"),
                ("Dự phòng", "-3", "-2"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )

    roles = [occurrence["role"] for occurrence in axis["role_occurrences"]]
    assert roles.count("INTERBANK_DEPOSIT_PROVISION") == 1
    assert roles.count("INTERBANK_PROVISION_AMBIGUOUS") == 1


def test_f3_generic_discount_is_unique_within_one_currency_subscope() -> None:
    _scan, duplicate_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Chiết khấu, tái chiết khấu", "5", "4"),
                ("Chiết khấu, tái chiết khấu", "6", "5"),
            ]
        )
    )
    assert [
        occurrence["role"]
        for occurrence in duplicate_axis["role_occurrences"]
        if occurrence["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
    ] == [
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS",
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS",
    ]

    _scan, explicit_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Chiết khấu, tái chiết khấu", "5", "4"),
                ("Chiết khấu, tái chiết khấu bằng VND", "6", "5"),
            ]
        )
    )
    roles = [occurrence["role"] for occurrence in explicit_axis["role_occurrences"]]
    assert roles.count("INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND") == 1
    assert roles.count("INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS") == 1


def test_f3_other_requires_noncontinuation_geometry_and_exact_parent_scope() -> None:
    known = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    _insert_wrapped_other(known, prefix="Tiền gửi tại các TCTD")
    _scan, known_axis = _build_f3(known)
    assert "INTERBANK_DEPOSIT_OTHER" not in {
        item["role"] for item in known_axis["role_occurrences"]
    }

    unknown = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    _insert_wrapped_other(unknown, prefix="Khoản diễn giải chưa có trong schema")
    _scan, unknown_axis = _build_f3(unknown)
    ambiguous = next(
        item
        for item in unknown_axis["role_occurrences"]
        if item["role"] == "INTERBANK_DEPOSIT_OTHER"
    )
    assert ambiguous["source_scope_binding"]["status"] == (
        "SOURCE_ONLY_AMBIGUOUS_TOUCHING_WRAPPED_LABEL"
    )
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        unknown_axis, _f3_spec(), _f3_hierarchy()
    )
    assert any(
        reason.startswith("SOURCE_ONLY_AMBIGUOUS_TOUCHING_WRAPPED_LABEL:")
        for reason in closure["unresolved_reasons"]
    )

    standalone = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Khác", "7", "6"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    _scan, standalone_axis = _build_f3(standalone)
    other = next(
        item
        for item in standalone_axis["role_occurrences"]
        if item["role"] == "INTERBANK_DEPOSIT_OTHER"
    )
    assert other["source_scope_binding"] is None
    other_row = next(
        row for row in standalone_axis["row_axis"]["rows"] if row["role"] == other["role"]
    )
    assert [value["parsed_token"]["coefficient"] for value in other_row["values"]] == [7, 6]


def test_f3_declared_scoped_other_alias_composes_touching_label_fragments() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    _insert_wrapped_other(pages, prefix="Các khoản")

    _scan, axis = _build_f3(pages)

    other = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_DEPOSIT_OTHER"
    )
    assert other["source_scope_binding"] is None
    assert other["label_match"]["normalized_surface"] == "cac khoan khac"
    assert other["label_match"]["match_kind"] == ("EXACT_ACCENTLESS_ALIAS_VISUAL_CONTINUATION")
    row = next(
        row
        for row in axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == other["occurrence_id"]
    )
    assert [value["parsed_token"]["coefficient"] for value in row["values"]] == [7, 6]


def test_f3_known_total_provision_wrap_suppresses_interleaved_other_suffix() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    lines = pages[0]["lines"]
    lines.extend(
        [
            _line(
                900,
                "Dự phòng rủi ro tiền gửi và cho vay các TCTD",
                "",
                [45, 400, 500, 420],
            ),
            _line(901, "-2", "-2", [610, 400, 700, 420]),
            _line(902, "-1", "-1", [810, 400, 900, 420]),
            _line(903, "|", "", [950, 402, 990, 418]),
            _line(904, "Khác", "", [47, 419, 180, 439]),
        ]
    )
    _reindex_page_lines(lines)

    _scan, axis = _build_f3(pages)

    assert "INTERBANK_LOAN_OTHER" not in {item["role"] for item in axis["role_occurrences"]}
    total = next(
        item for item in axis["role_occurrences"] if item["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    total_row = next(
        row
        for row in axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == total["occurrence_id"]
    )
    assert [value["parsed_token"]["coefficient"] for value in total_row["values"]] == [
        -2,
        -1,
    ]


def test_heading_only_parent_total_clone_is_pruned_but_same_row_values_are_retained() -> None:
    heading_only = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    for line in heading_only[0]["lines"][3:5]:
        line["vietocr_text"] = ""
        line["numeric_recognition"]["raw_prediction"] = ""
    _scan, heading_axis = _build_f3(heading_only)
    assert "EXPLICIT_FAMILY_TOTAL" not in {
        item["role"] for item in heading_axis["role_occurrences"]
    }

    with_values = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    _scan, valued_axis = _build_f3(with_values)
    total = next(
        item for item in valued_axis["role_occurrences"] if item["role"] == "EXPLICIT_FAMILY_TOTAL"
    )
    total_row = next(
        row
        for row in valued_axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == total["occurrence_id"]
    )
    assert [value["parsed_token"]["coefficient"] for value in total_row["values"]] == [
        150,
        130,
    ]


def test_wrapped_parent_total_owns_values_aligned_to_its_terminal_fragment() -> None:
    lines = [
        _line(0, "Tiền gửi và cho vay các tổ chức tín dụng", "", [25, 15, 560, 37]),
        _line(1, '(TCTD") khác', "", [30, 35, 220, 58]),
        _line(2, "422318628", "422318628", [610, 35, 700, 58]),
        _line(3, "374863906", "374863906", [810, 35, 900, 58]),
        _line(4, "30.06.2025", "30.06.2025", [610, 65, 700, 85]),
        _line(5, "31.12.2024", "31.12.2024", [810, 65, 900, 85]),
        _line(
            6,
            "Tiền gửi tại các tổ chức tín dụng khác",
            "",
            [45, 95, 430, 117],
        ),
        _line(7, "419162106", "419162106", [610, 95, 700, 117]),
        _line(8, "371252257", "371252257", [810, 95, 900, 117]),
        _line(
            9,
            "Cho vay các tổ chức tín dụng khác",
            "",
            [45, 130, 430, 152],
        ),
        _line(10, "3156522", "3156522", [610, 130, 700, 152]),
        _line(11, "3611649", "3611649", [810, 130, 900, 152]),
        _line(12, "Cho vay khách hàng", "", [45, 170, 430, 192]),
        _line(13, "1850880450", "1850880450", [610, 170, 700, 192]),
        _line(14, "1672377122", "1672377122", [810, 170, 900, 192]),
    ]
    pages = [{"lines": lines, "page_sequence": 1, "page_width": 1000}]

    _scan, axis = _build_f3(pages)

    total = next(row for row in axis["row_axis"]["rows"] if row["role"] == "EXPLICIT_FAMILY_TOTAL")
    assert (
        total["label_match"]["source_line_index"],
        total["label_match"]["end_source_line_index"],
    ) == (0, 1)
    assert [value["parsed_token"]["coefficient"] for value in total["values"]] == [
        422_318_628,
        374_863_906,
    ]
    assert {
        value["parsed_token"]["coefficient"]
        for sample in axis["numeric_sample_universe"]
        for value in [sample]
    }.isdisjoint({1_850_880_450, 1_672_377_122})
    assert axis["internal_unassigned_numeric_clusters"] == []
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"


def test_wrapped_parent_does_not_borrow_a_nearer_neighbor_row() -> None:
    lines = [
        _line(0, "Tiền gửi và cho vay các tổ chức tín dụng", "", [25, 15, 560, 37]),
        _line(1, "(TCTD) khác", "", [30, 35, 220, 58]),
        _line(
            2,
            "Tiền gửi tại các tổ chức tín dụng khác",
            "",
            [45, 45, 430, 67],
        ),
        _line(3, "419162106", "419162106", [610, 45, 700, 67]),
        _line(4, "371252257", "371252257", [810, 45, 900, 67]),
        _line(
            5,
            "Cho vay các tổ chức tín dụng khác",
            "",
            [45, 95, 430, 117],
        ),
        _line(6, "3156522", "3156522", [610, 95, 700, 117]),
        _line(7, "3611649", "3611649", [810, 95, 900, 117]),
    ]
    pages = [{"lines": lines, "page_sequence": 1, "page_width": 1000}]

    _scan, axis = _build_f3(pages)

    total = next(row for row in axis["row_axis"]["rows"] if row["role"] == "EXPLICIT_FAMILY_TOTAL")
    assert total["status"] == "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL"
    assert total["values"] == []
    assert axis["status"] == "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    deposit = next(
        row for row in axis["row_axis"]["rows"] if row["role"] == "INTERBANK_DEPOSIT_GROUP"
    )
    assert [value["sample_id"] for value in deposit["values"]] == [
        lines[3]["sample_id"],
        lines[4]["sample_id"],
    ]


def test_wrapped_parent_rejects_partial_or_note_reference_lane_shapes() -> None:
    def pages_with_root_values(values: list[tuple[str, list[int]]]) -> list[dict[str, object]]:
        lines = [
            _line(
                0,
                "Tiền gửi và cho vay các tổ chức tín dụng",
                "",
                [25, 15, 560, 37],
            ),
            _line(1, "(TCTD) khác", "", [30, 35, 220, 58]),
        ]
        lines.extend(
            _line(index + 2, value, value, bbox) for index, (value, bbox) in enumerate(values)
        )
        start = len(lines)
        lines.extend(
            [
                _line(
                    start,
                    "Tiền gửi tại các tổ chức tín dụng khác",
                    "",
                    [45, 95, 430, 117],
                ),
                _line(start + 1, "419162106", "419162106", [610, 95, 700, 117]),
                _line(start + 2, "371252257", "371252257", [810, 95, 900, 117]),
                _line(
                    start + 3,
                    "Cho vay các tổ chức tín dụng khác",
                    "",
                    [45, 130, 430, 152],
                ),
                _line(start + 4, "3156522", "3156522", [610, 130, 700, 152]),
                _line(start + 5, "3611649", "3611649", [810, 130, 900, 152]),
            ]
        )
        return [{"lines": lines, "page_sequence": 1, "page_width": 1000}]

    for root_values in (
        [("422318628", [610, 35, 700, 58])],
        [
            ("422318628", [610, 35, 700, 58]),
            ("8", [710, 35, 760, 58]),
            ("374863906", [810, 35, 900, 58]),
        ],
    ):
        pages = pages_with_root_values(root_values)
        _scan, axis = _build_f3(pages)
        total = next(
            row for row in axis["row_axis"]["rows"] if row["role"] == "EXPLICIT_FAMILY_TOTAL"
        )
        universe_ids = [sample["sample_id"] for sample in axis["numeric_sample_universe"]]
        root_sample_ids = {
            line["sample_id"] for line in pages[0]["lines"][2 : 2 + len(root_values)]
        }
        assert root_sample_ids <= set(universe_ids)
        assert len(universe_ids) == len(set(universe_ids))
        if len(root_values) == 1:
            assert total["status"] == "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
            assert axis["status"] == ("UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE")
        else:
            assert total["status"] == "VISIBLE_VALUE_LANES_BOUND"
            assert axis["internal_unassigned_numeric_clusters"]
        closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
            axis, _f3_spec(), _f3_hierarchy()
        )
        assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"


def test_interleaved_wrapped_parent_fragments_own_each_value_sample_once() -> None:
    lines = [
        _line(0, "Tiền gửi và cho vay các tổ chức tín dụng", "", [25, 15, 560, 37]),
        _line(1, "422318628", "422318628", [610, 15, 700, 37]),
        _line(2, "374863906", "374863906", [810, 15, 900, 37]),
        _line(3, "(TCTD) khác", "", [30, 37, 220, 60]),
        _line(
            4,
            "Tiền gửi tại các tổ chức tín dụng khác",
            "",
            [45, 95, 430, 117],
        ),
        _line(5, "419162106", "419162106", [610, 95, 700, 117]),
        _line(6, "371252257", "371252257", [810, 95, 900, 117]),
        _line(
            7,
            "Cho vay các tổ chức tín dụng khác",
            "",
            [45, 130, 430, 152],
        ),
        _line(8, "3156522", "3156522", [610, 130, 700, 152]),
        _line(9, "3611649", "3611649", [810, 130, 900, 152]),
    ]
    pages = [{"lines": lines, "page_sequence": 1, "page_width": 1000}]

    _scan, axis = _build_f3(pages)

    total = next(row for row in axis["row_axis"]["rows"] if row["role"] == "EXPLICIT_FAMILY_TOTAL")
    assert total["label_match"]["source_line_indices"] == [0, 3]
    assert [value["sample_id"] for value in total["values"]] == [
        lines[1]["sample_id"],
        lines[2]["sample_id"],
    ]
    universe_ids = [sample["sample_id"] for sample in axis["numeric_sample_universe"]]
    assert universe_ids.count(lines[1]["sample_id"]) == 1
    assert universe_ids.count(lines[2]["sample_id"]) == 1
    total_occurrence = next(
        item for item in axis["role_occurrences"] if item["role"] == "EXPLICIT_FAMILY_TOTAL"
    )
    for sample_id in (lines[1]["sample_id"], lines[2]["sample_id"]):
        sample = next(
            item for item in axis["numeric_sample_universe"] if item["sample_id"] == sample_id
        )
        assert (sample["owner_kind"], sample["owner_id"]) == (
            "ROLE_OCCURRENCE",
            total_occurrence["occurrence_id"],
        )
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"


def test_interleaved_wrapped_parent_lone_sample_is_owned_and_replay_bound() -> None:
    lines = [
        _line(0, "Tiền gửi và cho vay các tổ chức tín dụng", "", [25, 15, 560, 37]),
        _line(1, "8", "8", [610, 15, 700, 37]),
        _line(2, "(TCTD) khác", "", [30, 37, 220, 60]),
        _line(
            3,
            "Tiền gửi tại các tổ chức tín dụng khác",
            "",
            [45, 95, 430, 117],
        ),
        _line(4, "100", "100", [610, 95, 700, 117]),
        _line(5, "90", "90", [810, 95, 900, 117]),
        _line(
            6,
            "Cho vay các tổ chức tín dụng khác",
            "",
            [45, 130, 430, 152],
        ),
        _line(7, "50", "50", [610, 130, 700, 152]),
        _line(8, "40", "40", [810, 130, 900, 152]),
    ]
    pages = [{"lines": lines, "page_sequence": 1, "page_width": 1000}]

    scan, axis = _build_f3(pages)

    total_occurrence = next(
        item for item in axis["role_occurrences"] if item["role"] == "EXPLICIT_FAMILY_TOTAL"
    )
    total = next(
        row
        for row in axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == total_occurrence["occurrence_id"]
    )
    assert total["label_match"]["source_line_indices"] == [0, 2]
    assert total["status"] == "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
    assert [value["sample_id"] for value in total["values"]] == [lines[1]["sample_id"]]
    sample = next(
        item
        for item in axis["numeric_sample_universe"]
        if item["sample_id"] == lines[1]["sample_id"]
    )
    assert (sample["owner_kind"], sample["owner_id"]) == (
        "ROLE_OCCURRENCE",
        total_occurrence["occurrence_id"],
    )
    assert axis["status"] == "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"

    attacked = copy.deepcopy(axis)
    attacked_total = next(
        row
        for row in attacked["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == total_occurrence["occurrence_id"]
    )
    attacked_total["values"] = []
    attacked_total["missing_column_ordinals"] = [0, 1]
    attacked_total["status"] = "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL"
    attacked["row_axis"] = subject._regenerate_v1_axis(attacked["row_axis"])
    attacked["numeric_sample_universe"] = [
        item
        for item in attacked["numeric_sample_universe"]
        if item["sample_id"] != lines[1]["sample_id"]
    ]
    _coherently_rehash_occurrence(attacked)
    effective = total_v1.project_accounting_family_coextensive_parent_total_region_v1(
        _f3_spec(), scan, scan["regions"][0]
    )
    with pytest.raises(subject.AccountingFamilyOccurrenceRowAxisV2Error):
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            attacked,
            pages,
            _f3_spec(),
            scan,
            scan["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=effective,
        )


def _f3_hierarchy_frontier_hdb_pages(
    *,
    current_total: str = "150",
    deposit_current: str = "100",
    extra_rows: tuple[tuple[str, str, str], ...] = (),
    loan_current: str = "50",
    reverse_components: bool = False,
    source_surface: str = "Tièn gn ti các TCTD khác",
) -> list[dict[str, object]]:
    components = [
        ("Tiền gửi tại các TCTD khác", deposit_current, "90"),
        ("Cho vay các TCTD khác", loan_current, "40"),
    ]
    if reverse_components:
        components.reverse()
    pages = _f3_parent_frontier_pages(
        [
            ("Tổng tiền gửi và cho vay các TCTD khác", current_total, "130"),
            *components,
            *extra_rows,
        ]
    )
    for index in (5, 4):
        pages[0]["lines"].pop(index)
    _reindex_page_lines(pages[0]["lines"])
    for line in pages[0]["lines"]:
        if line["vietocr_text"] == "Tiền gửi tại các TCTD khác":
            line["vietocr_text"] = "Tiần gửi tại các TCTD khác"
            line["numeric_recognition"]["raw_prediction"] = source_surface
    return pages


def _f3_hierarchy_frontier_ctg_pages(
    *,
    loan_semantic_surface: str = "50.000.000",
    loan_value: str = "50,000.000",
    parent_semantic_surface: str = "150.000.000",
    parent_value: str = "150.000,000",
) -> list[dict[str, object]]:
    pages = _f3_parent_frontier_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100.000.000", "90.000.000"),
            ("Cho vay các TCTD khác", loan_value, "40.000.000"),
        ]
    )
    lines = pages[0]["lines"]
    lines[0]["vietocr_text"] = "Tiền gửi và cho yay các TCTD khác"
    lines[0]["numeric_recognition"]["raw_prediction"] = "Tin gi và cho vay các TCTD khác"
    for index, pp_surface, semantic_surface in (
        (4, parent_value, parent_semantic_surface),
        (5, "130.000.000", "130.000.000"),
        (10, loan_value, loan_semantic_surface),
    ):
        lines[index]["numeric_recognition"]["raw_prediction"] = pp_surface
        lines[index]["vietocr_text"] = semantic_surface
    return pages


def _project_f3_hierarchy_frontier(
    pages: list[dict[str, object]],
) -> tuple[dict, dict, dict, dict]:
    scan, axis = _build_f3(pages)
    context = _f3_column_context(axis, pages)
    assert context["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    projected = subject.project_accounting_family_one_edit_hierarchy_frontier_authority_v2(
        axis,
        context,
        pages,
        _f3_spec(),
        scan["regions"][0],
        _f3_hierarchy(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=["MONEY", "MONEY"],
    )
    return scan, axis, context, projected


@pytest.mark.parametrize(
    ("shape", "target_kind", "carrier_kind"),
    [
        ("HDB_COMPONENT", "COMPONENT", "ROLE_OCCURRENCE"),
        ("CTG_PARENT", "FAMILY_PARENT", "LABELED_PARENT_CLUSTER"),
    ],
)
def test_f3_one_edit_hierarchy_frontier_binds_source_visible_root_equation(
    shape: str,
    target_kind: str,
    carrier_kind: str,
) -> None:
    pages = (
        _f3_hierarchy_frontier_hdb_pages()
        if shape == "HDB_COMPONENT"
        else _f3_hierarchy_frontier_ctg_pages()
    )
    scan, _axis, context, projected = _project_f3_hierarchy_frontier(pages)
    receipt = projected["one_edit_exact_source_structural_proofs"]
    assert receipt["format_version"] == one_edit_v1.HIERARCHY_FRONTIER_FORMAT_VERSION
    assert receipt["status"] == "EXACT_SOURCE_AUTHORITY_BOUND"
    assert receipt["unresolved_reasons"] == []
    proof = receipt["hierarchy_direct_frontier_authority"]
    assert proof["target_kind"] == target_kind
    assert proof["result_carrier_binding"]["carrier_kind"] == carrier_kind
    assert [item["role"] for item in proof["component_frontier_bindings"]] == [
        "INTERBANK_DEPOSIT_GROUP",
        "INTERBANK_LOAN_GROUP",
    ]
    if shape == "CTG_PARENT":
        assert [item["certificate_kind"] for item in proof["numeric_cell_certificates"]].count(
            "MIXED_SAME_CROP_EXACT_INTEGER"
        ) == 2

    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        projected,
        _f3_spec(),
        _f3_hierarchy(),
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    assert closure["unresolved_reasons"] == []
    assert (
        sweep_v1._mixed_separator_consensus_reasons(
            row_axis=projected["row_axis"],
            column_context=context,
            closure=closure,
            joined_pages=pages,
        )
        == []
    )

    authority_pages = subject._one_edit_authority_pages_v2(row_v1._pages(pages))
    expanded = one_edit_v1._canonical_expanded_occurrence_region_v1(
        one_edit_v1._pages_with_occurrence_geometry_v1(authority_pages),
        _f3_spec(),
        scan["regions"][0],
    )
    assert (
        one_edit_v1.validate_accounting_family_one_edit_exact_authority_replay_v1(
            receipt,
            authority_pages,
            _f3_spec(),
            scan["regions"][0],
            expanded,
            structural_evidence=_f3_structural_evidence(projected),
            column_context=context,
            column_context_document_pages=pages,
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=["MONEY", "MONEY"],
            hierarchy_spec=_f3_hierarchy(),
        )
        == receipt
    )


@pytest.mark.parametrize(
    "pages",
    [
        _f3_hierarchy_frontier_hdb_pages(current_total="151"),
        _f3_hierarchy_frontier_hdb_pages(current_total=""),
        _f3_hierarchy_frontier_hdb_pages(deposit_current=""),
        _f3_hierarchy_frontier_hdb_pages(source_surface=""),
        _f3_hierarchy_frontier_hdb_pages(
            extra_rows=(("Dự phòng rủi ro tiền gửi và cho vay các TCTD khác", "", "-1"),)
        ),
        _f3_hierarchy_frontier_hdb_pages(extra_rows=(("Tổng cho vay các TCTD khác", "1", "1"),)),
        _f3_hierarchy_frontier_hdb_pages(extra_rows=(("Tiền gửi tại các TCTD khác", "1", "1"),)),
        _f3_hierarchy_frontier_ctg_pages(parent_semantic_surface="151.000.000"),
        _f3_hierarchy_frontier_ctg_pages(loan_semantic_surface="51.000.000"),
    ],
    ids=[
        "one-lane-residual",
        "missing-visible-result",
        "partial-component",
        "wrong-unbound-status",
        "partial-declared-provision",
        "root-nonadditive-row",
        "duplicate-component-role",
        "mixed-result-reader-disagreement",
        "mixed-component-reader-disagreement",
    ],
)
def test_f3_one_edit_hierarchy_frontier_abstains_on_incomplete_or_untrusted_axis(
    pages: list[dict[str, object]],
) -> None:
    _scan, axis, _context, projected = _project_f3_hierarchy_frontier(pages)
    assert (
        projected["one_edit_exact_source_structural_proofs"]
        == axis["one_edit_exact_source_structural_proofs"]
    )
    assert projected["one_edit_exact_source_structural_proofs"]["format_version"] == (
        one_edit_v1.FORMAT_VERSION
    )


def test_f3_one_edit_hierarchy_frontier_preserves_reordered_physical_siblings() -> None:
    _scan, _axis, _context, projected = _project_f3_hierarchy_frontier(
        _f3_hierarchy_frontier_hdb_pages(reverse_components=True)
    )
    proof = projected["one_edit_exact_source_structural_proofs"][
        "hierarchy_direct_frontier_authority"
    ]
    assert [item["role"] for item in proof["component_frontier_bindings"]] == [
        "INTERBANK_DEPOSIT_GROUP",
        "INTERBANK_LOAN_GROUP",
    ]
    assert [item["source_visual_ordinal"] for item in proof["component_frontier_bindings"]] == [
        1,
        0,
    ]


def _coherently_rehash_hierarchy_frontier(axis: dict) -> None:
    receipt = axis["one_edit_exact_source_structural_proofs"]
    proof = receipt["hierarchy_direct_frontier_authority"]
    receipt["input_binding"] = copy.deepcopy(proof["input_binding"])
    proof_material = copy.deepcopy(proof)
    proof_material.pop("proof_id")
    proof["proof_id"] = "afeoehdfav1:proof:" + canonical_json_sha256_v1(proof_material)
    receipt_material = copy.deepcopy(receipt)
    receipt_material.pop("receipt_id")
    receipt["receipt_id"] = "afeoeav1:receipt:" + canonical_json_sha256_v1(receipt_material)
    _coherently_rehash_occurrence(axis)


def _coherently_replace_hierarchy_frontier_source_check(
    axis: dict,
    check: dict,
) -> None:
    receipt = axis["one_edit_exact_source_structural_proofs"]
    proof = receipt["hierarchy_direct_frontier_authority"]
    source = receipt["source_exact_authority_receipt"]
    source["checks"] = [copy.deepcopy(check)]
    source["unresolved_reasons"] = [one_edit_v1._parent_frontier_reason(check)]
    source_material = copy.deepcopy(source)
    source_material.pop("receipt_id")
    source["receipt_id"] = "afeoeav1:receipt:" + canonical_json_sha256_v1(source_material)
    proof["source_check"] = copy.deepcopy(check)
    proof["input_binding"]["source_exact_authority_receipt_sha256"] = canonical_json_sha256_v1(
        source
    )
    receipt["checks"] = [copy.deepcopy(check)]


@pytest.mark.parametrize("attack", ["PERIOD", "UNIT", "CROP", "VIETOCR"])
def test_f3_hierarchy_frontier_selected_public_replay_rejects_coherent_context_or_crop_tamper(
    attack: str,
) -> None:
    pages = _f3_hierarchy_frontier_ctg_pages()
    scan, _axis, context, projected = _project_f3_hierarchy_frontier(pages)
    attacked = copy.deepcopy(projected)
    proof = attacked["one_edit_exact_source_structural_proofs"][
        "hierarchy_direct_frontier_authority"
    ]
    attacked_context = proof["column_context_receipt"]
    if attack == "PERIOD":
        attacked_context["period_axis"][0]["resolved_period"] = "31/12/2099"
        attacked_context["document_period_context"]["current_period_end"] = "31/12/2099"
        attacked_context["document_period_context"]["reporting_year"] = 2099
        attacked_context["document_period_context"]["observed_dates"][1]["date"] = "31/12/2099"
    elif attack == "UNIT":
        attacked_context["document_unit_context"]["currency"] = "USD"
        for lane in attacked_context["unit_axis"]:
            lane["currency"] = "USD"
    elif attack == "CROP":
        certificate = proof["numeric_cell_certificates"][0]
        certificate["crop_ref"]["sha256"] = "f" * 64
        certificate["crop_ref"]["path"] = "opaque/coherently-forged-crop.png"
    else:
        certificate = proof["numeric_cell_certificates"][0]
        assert certificate["certificate_kind"] == "MIXED_SAME_CROP_EXACT_INTEGER"
        certificate["vietocr_surface"] = "151.000.000"
    if attack in {"PERIOD", "UNIT"}:
        context_material = copy.deepcopy(attacked_context)
        context_material.pop("column_context_id")
        attacked_context["column_context_id"] = "afccv1:context:" + canonical_json_sha256_v1(
            context_material
        )
        proof["input_binding"]["column_context_sha256"] = canonical_json_sha256_v1(attacked_context)
    _coherently_rehash_hierarchy_frontier(attacked)
    if attack in {"CROP", "VIETOCR"}:
        with pytest.raises(
            one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error,
            match="hierarchy-frontier",
        ):
            one_edit_v1._validate_hierarchy_frontier_against_structural_evidence_v1(
                attacked["one_edit_exact_source_structural_proofs"],
                _f3_structural_evidence(attacked),
            )
        return
    attacked_closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        attacked,
        _f3_spec(),
        _f3_hierarchy(),
    )
    assert attacked_closure["status"] == ("HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO")
    selected_context = attacked_context if attack in {"PERIOD", "UNIT"} else context
    with pytest.raises(ValueError, match="column context does not replay exactly"):
        sweep_v1._selected_v4_one_edit_authority_v1(
            {
                "additive_closure": attacked_closure,
                "candidate_ordinal": 0,
                "column_context": selected_context,
                "column_context_visible_dash_rescues": (),
                "one_edit_exact_source_structural_proofs": attacked[
                    "one_edit_exact_source_structural_proofs"
                ],
                "row_axis": attacked["row_axis"],
            },
            joined_pages=pages,
            family_spec=_f3_spec(),
            topology_candidates=scan,
            evaluation_spec=json.loads(_F3_EVALUATION_PATH.read_text(encoding="utf-8")),
        )


def test_f3_hierarchy_frontier_public_replay_rejects_coherently_rehashed_equivalent_reader_surface() -> (
    None
):
    pages = _f3_hierarchy_frontier_ctg_pages()
    scan, _axis, context, projected = _project_f3_hierarchy_frontier(pages)
    attacked = copy.deepcopy(projected)
    proof = attacked["one_edit_exact_source_structural_proofs"][
        "hierarchy_direct_frontier_authority"
    ]
    certificate = next(
        item
        for item in proof["numeric_cell_certificates"]
        if item["certificate_kind"] == "MIXED_SAME_CROP_EXACT_INTEGER"
    )
    certificate["vietocr_surface"] = str(certificate["number"]["coefficient"])
    sample = next(
        item
        for item in attacked["numeric_sample_universe"]
        if item["sample_id"] == certificate["sample_id"]
    )
    certificate["page_line_sha256"] = canonical_json_sha256_v1(
        one_edit_v1._hierarchy_frontier_page_line_from_sample_v1(
            sample,
            certificate["vietocr_surface"],
        )
    )
    _coherently_rehash_hierarchy_frontier(attacked)
    assert subject._validate_result(attacked) == attacked
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        attacked,
        _f3_spec(),
        _f3_hierarchy(),
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    with pytest.raises(ValueError, match="differs from occurrence proof"):
        sweep_v1._selected_v4_one_edit_authority_v1(
            {
                "additive_closure": closure,
                "candidate_ordinal": 0,
                "column_context": context,
                "column_context_visible_dash_rescues": (),
                "one_edit_exact_source_structural_proofs": attacked[
                    "one_edit_exact_source_structural_proofs"
                ],
                "row_axis": attacked["row_axis"],
            },
            joined_pages=pages,
            family_spec=_f3_spec(),
            topology_candidates=scan,
            evaluation_spec=json.loads(_F3_EVALUATION_PATH.read_text(encoding="utf-8")),
        )


def test_f3_selected_public_replay_cache_reuses_only_identical_bound_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = _f3_hierarchy_frontier_ctg_pages()
    scan, _axis, context, projected = _project_f3_hierarchy_frontier(pages)
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        projected,
        _f3_spec(),
        _f3_hierarchy(),
    )
    selected = {
        "additive_closure": closure,
        "candidate_ordinal": 0,
        "column_context": context,
        "column_context_visible_dash_rescues": (),
        "one_edit_exact_source_structural_proofs": projected[
            "one_edit_exact_source_structural_proofs"
        ],
        "row_axis": projected["row_axis"],
    }
    evaluation = json.loads(_F3_EVALUATION_PATH.read_text(encoding="utf-8"))
    original_projector = (
        one_edit_v1.project_accounting_family_one_edit_hierarchy_frontier_authority_v1
    )
    projector_calls = 0

    def counted_projector(*args: object, **kwargs: object) -> dict[str, object]:
        nonlocal projector_calls
        projector_calls += 1
        return original_projector(*args, **kwargs)

    monkeypatch.setattr(
        one_edit_v1,
        "project_accounting_family_one_edit_hierarchy_frontier_authority_v1",
        counted_projector,
    )
    cache: dict[str, object] = {}
    first = sweep_v1._selected_v4_one_edit_authority_v1(
        selected,
        joined_pages=pages,
        family_spec=_f3_spec(),
        topology_candidates=scan,
        evaluation_spec=evaluation,
        prepared_public_replay_cache=cache,
    )
    second = sweep_v1._selected_v4_one_edit_authority_v1(
        selected,
        joined_pages=pages,
        family_spec=_f3_spec(),
        topology_candidates=scan,
        evaluation_spec=evaluation,
        prepared_public_replay_cache=cache,
    )
    assert second == first
    assert projector_calls == 1
    assert len(cache) == 1

    changed = copy.deepcopy(selected)
    changed["column_context"]["document_unit_context"]["currency"] = "USD"
    with pytest.raises(ValueError, match="one-edit exact authority replay failed"):
        sweep_v1._selected_v4_one_edit_authority_v1(
            changed,
            joined_pages=pages,
            family_spec=_f3_spec(),
            topology_candidates=scan,
            evaluation_spec=evaluation,
            prepared_public_replay_cache=cache,
        )
    assert projector_calls == 2

    cache_key = next(iter(cache))
    cache[cache_key] = replace(cache[cache_key], receipt_sha256="0" * 64)
    with pytest.raises(ValueError, match="public-replay cache binding drifted"):
        sweep_v1._selected_v4_one_edit_authority_v1(
            selected,
            joined_pages=pages,
            family_spec=_f3_spec(),
            topology_candidates=scan,
            evaluation_spec=evaluation,
            prepared_public_replay_cache=cache,
        )


def test_f3_selected_public_replay_accepts_only_same_turn_projector_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = _f3_hierarchy_frontier_ctg_pages()
    scan, _axis, context, projected = _project_f3_hierarchy_frontier(pages)
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        projected,
        _f3_spec(),
        _f3_hierarchy(),
    )
    selected = {
        "additive_closure": closure,
        "candidate_ordinal": 0,
        "column_context": context,
        "column_context_visible_dash_rescues": (),
        "one_edit_exact_source_structural_proofs": projected[
            "one_edit_exact_source_structural_proofs"
        ],
        "reasons": [],
        "row_axis": projected["row_axis"],
    }
    evaluation = json.loads(_F3_EVALUATION_PATH.read_text(encoding="utf-8"))
    cache: dict[str, object] = {}
    sweep_v1._retain_selected_one_edit_public_replay_handoff_v1(
        cache,
        candidate=selected,
        joined_pages=pages,
        family_spec=_f3_spec(),
        evaluation_spec=evaluation,
        selected_topology_region=scan["regions"][0],
    )
    monkeypatch.setattr(
        one_edit_v1,
        "project_accounting_family_one_edit_hierarchy_frontier_authority_v1",
        lambda *_args, **_kwargs: pytest.fail("same-turn handoff rebuilt its projector"),
    )

    receipt, reasons = sweep_v1._selected_v4_one_edit_authority_v1(
        selected,
        joined_pages=pages,
        family_spec=_f3_spec(),
        topology_candidates=scan,
        evaluation_spec=evaluation,
        prepared_public_replay_cache=cache,
    )
    assert receipt == projected["one_edit_exact_source_structural_proofs"]
    assert reasons == []


@pytest.mark.parametrize("attack", ["DELETE", "REORDER", "DUPLICATE"])
def test_f3_hierarchy_frontier_public_replay_rejects_different_hierarchy_spec(
    attack: str,
) -> None:
    pages = _f3_hierarchy_frontier_hdb_pages()
    scan, _axis, context, projected = _project_f3_hierarchy_frontier(pages)
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        projected,
        _f3_spec(),
        _f3_hierarchy(),
    )
    evaluation = json.loads(_F3_EVALUATION_PATH.read_text(encoding="utf-8"))
    root_equation = next(
        equation
        for equation in evaluation["hierarchical_closure_spec"]["equations"]
        if equation["result_role"] == "INTERBANK_DEPOSITS_AND_LOANS"
    )
    alternative = root_equation["component_role_alternatives"][0]
    if attack == "DELETE":
        root_equation["component_role_alternatives"].pop(0)
    elif attack == "REORDER":
        alternative["component_roles"].reverse()
    else:
        alternative["component_roles"][1] = alternative["component_roles"][0]
    with pytest.raises(ValueError, match="one-edit exact authority"):
        sweep_v1._selected_v4_one_edit_authority_v1(
            {
                "additive_closure": closure,
                "candidate_ordinal": 0,
                "column_context": context,
                "column_context_visible_dash_rescues": (),
                "one_edit_exact_source_structural_proofs": projected[
                    "one_edit_exact_source_structural_proofs"
                ],
                "row_axis": projected["row_axis"],
            },
            joined_pages=pages,
            family_spec=_f3_spec(),
            topology_candidates=scan,
            evaluation_spec=evaluation,
        )


@pytest.mark.parametrize(
    ("shape", "attack"),
    [
        ("HDB", "WRONG_ROOT"),
        ("HDB", "WRONG_PAGE"),
        ("HDB", "WRONG_COMPONENT_PARENT"),
        ("HDB", "DUPLICATE_COMPONENT_OCCURRENCE"),
        ("HDB", "MIXED_LEVEL_RESULT_AS_COMPONENT"),
        ("HDB", "DECLARED_BINDING_ORDER"),
        ("HDB", "DUPLICATE_SAMPLE"),
        ("HDB", "ROW_HASH"),
        ("CTG", "RESULT_CLUSTER"),
        ("CTG", "PAGE_LINE_HASH"),
        ("HDB", "ARITHMETIC_RESIDUAL"),
        ("HDB", "ROUNDING_SCALE"),
    ],
)
def test_f3_hierarchy_frontier_occurrence_rejects_coherently_rehashed_receipt_tamper(
    shape: str,
    attack: str,
) -> None:
    pages = (
        _f3_hierarchy_frontier_hdb_pages() if shape == "HDB" else _f3_hierarchy_frontier_ctg_pages()
    )
    _scan, _axis, _context, projected = _project_f3_hierarchy_frontier(pages)
    attacked = copy.deepcopy(projected)
    receipt = attacked["one_edit_exact_source_structural_proofs"]
    proof = receipt["hierarchy_direct_frontier_authority"]
    components = proof["component_frontier_bindings"]
    forged_root = "aforav2:root:" + "f" * 64
    if attack == "WRONG_ROOT":
        proof["root_occurrence_id"] = forged_root
    elif attack == "WRONG_PAGE":
        proof["page_sequence"] = 2
        check = copy.deepcopy(proof["source_check"])
        check["page_sequence"] = 2
        _coherently_replace_hierarchy_frontier_source_check(attacked, check)
        for certificate in proof["numeric_cell_certificates"]:
            certificate["page_sequence"] = 2
    elif attack == "WRONG_COMPONENT_PARENT":
        occurrence = next(
            item
            for item in attacked["role_occurrences"]
            if item["occurrence_id"] == components[0]["occurrence_id"]
        )
        occurrence["scope_owner_occurrence_id"] = forged_root
        occurrence["retrieval_scope_owner_occurrence_id"] = forged_root
        occurrence["label_match"]["scope_owner_occurrence_id"] = forged_root
        occurrence["label_match"]["retrieval_scope_owner_occurrence_id"] = forged_root
        components[0]["role_occurrence_sha256"] = canonical_json_sha256_v1(occurrence)
        proof["input_binding"]["role_occurrences_sha256"] = canonical_json_sha256_v1(
            attacked["role_occurrences"]
        )
    elif attack == "DUPLICATE_COMPONENT_OCCURRENCE":
        components[1]["occurrence_id"] = components[0]["occurrence_id"]
        components[1]["retrieval_occurrence_id"] = components[0]["retrieval_occurrence_id"]
    elif attack == "MIXED_LEVEL_RESULT_AS_COMPONENT":
        carrier = proof["result_carrier_binding"]
        components[1]["occurrence_id"] = carrier["occurrence_id"]
        components[1]["retrieval_occurrence_id"] = carrier["occurrence_id"]
    elif attack == "DECLARED_BINDING_ORDER":
        components.reverse()
    elif attack == "DUPLICATE_SAMPLE":
        duplicate = components[0]["sample_ids"][0]
        components[1]["sample_ids"][0] = duplicate
        certificate = next(
            item
            for item in proof["numeric_cell_certificates"]
            if item["node_kind"] == "COMPONENT"
            and item["node_ordinal"] == 1
            and item["column_ordinal"] == 0
        )
        certificate["sample_id"] = duplicate
    elif attack == "ROW_HASH":
        components[0]["row_sha256"] = "f" * 64
    elif attack == "RESULT_CLUSTER":
        proof["result_carrier_binding"]["cluster_id"] = "aforav2:unassigned:" + "f" * 64
    elif attack == "PAGE_LINE_HASH":
        mixed = next(
            item
            for item in proof["numeric_cell_certificates"]
            if item["certificate_kind"] == "MIXED_SAME_CROP_EXACT_INTEGER"
        )
        mixed["page_line_sha256"] = "f" * 64
    else:
        carrier = proof["result_carrier_binding"]
        result_certificate = next(
            item
            for item in proof["numeric_cell_certificates"]
            if item["node_kind"] == "RESULT" and item["column_ordinal"] == 0
        )
        if attack == "ARITHMETIC_RESIDUAL":
            carrier["numbers"][0]["coefficient"] += 1
            result_certificate["number"]["coefficient"] += 1
        else:
            carrier["numbers"][0]["scale"] = 1
            result_certificate["number"]["scale"] = 1
    _coherently_rehash_hierarchy_frontier(attacked)
    with pytest.raises(
        one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error,
        match="hierarchy-frontier",
    ):
        one_edit_v1._validate_hierarchy_frontier_against_structural_evidence_v1(
            receipt,
            _f3_structural_evidence(attacked),
        )


def test_f3_hierarchy_frontier_occurrence_rejects_coherent_wrong_target_source_span() -> None:
    _scan, _axis, _context, projected = _project_f3_hierarchy_frontier(
        _f3_hierarchy_frontier_hdb_pages()
    )
    attacked = copy.deepcopy(projected)
    receipt = attacked["one_edit_exact_source_structural_proofs"]
    proof = receipt["hierarchy_direct_frontier_authority"]
    source = receipt["source_exact_authority_receipt"]
    wrong_lines = [proof["source_check"]["source_line_indices"][0] + 1]
    proof["source_check"]["source_line_indices"] = wrong_lines
    source["checks"][0]["source_line_indices"] = wrong_lines
    receipt["checks"][0]["source_line_indices"] = wrong_lines
    source["unresolved_reasons"] = [one_edit_v1._parent_frontier_reason(source["checks"][0])]
    source_material = copy.deepcopy(source)
    source_material.pop("receipt_id")
    source["receipt_id"] = "afeoeav1:receipt:" + canonical_json_sha256_v1(source_material)
    proof["input_binding"]["source_exact_authority_receipt_sha256"] = canonical_json_sha256_v1(
        source
    )
    with pytest.raises(
        one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error,
        match="component target",
    ):
        _coherently_rehash_hierarchy_frontier(attacked)
        one_edit_v1._validate_hierarchy_frontier_against_structural_evidence_v1(
            attacked["one_edit_exact_source_structural_proofs"],
            _f3_structural_evidence(attacked),
        )


def test_wrapped_parent_adjacent_outside_tolerance_number_stays_source_only() -> None:
    lines = [
        _line(0, "Tiền gửi và cho vay các tổ chức tín dụng", "", [25, 15, 560, 37]),
        _line(1, "(TCTD) khác", "", [30, 35, 220, 58]),
        _line(2, "8", "8", [610, 62, 700, 84]),
        _line(
            3,
            "Tiền gửi tại các tổ chức tín dụng khác",
            "",
            [45, 95, 430, 117],
        ),
        _line(4, "100", "100", [610, 95, 700, 117]),
        _line(5, "90", "90", [810, 95, 900, 117]),
        _line(
            6,
            "Cho vay các tổ chức tín dụng khác",
            "",
            [45, 130, 430, 152],
        ),
        _line(7, "50", "50", [610, 130, 700, 152]),
        _line(8, "40", "40", [810, 130, 900, 152]),
    ]
    pages = [{"lines": lines, "page_sequence": 1, "page_width": 1000}]

    _scan, axis = _build_f3(pages)

    assert "EXPLICIT_FAMILY_TOTAL" not in {
        occurrence["role"] for occurrence in axis["role_occurrences"]
    }
    sample = next(
        item
        for item in axis["numeric_sample_universe"]
        if item["sample_id"] == lines[2]["sample_id"]
    )
    assert sample["owner_kind"] == "SOURCE_ONLY_INTERNAL_CLUSTER"
    cluster = next(
        item
        for item in axis["internal_unassigned_numeric_clusters"]
        if lines[2]["sample_id"] in item["sample_ids"]
    )
    assert cluster["status"] == "SOURCE_ONLY_INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"


def test_complete_same_row_proof_uses_only_eligible_fragments_and_independent_peers() -> None:
    pages = [
        {
            "lines": [
                _line(0, "Wide owner fragment", "", [0, 90, 900, 110]),
                _line(1, "5", "5", [650, 90, 750, 110]),
                _line(2, "Terminal owner fragment", "", [0, 98, 200, 118]),
                _line(3, "Closer semantic peer", "", [0, 94, 300, 114]),
                _line(4, "7", "7", [650, 140, 750, 160]),
            ],
            "page_sequence": 1,
            "page_width": 1000,
        }
    ]
    owner = {
        "end_source_line_index": 2,
        "page_sequence": 1,
        "source_line_index": 0,
        "source_line_indices": [0, 2],
    }
    peer = {
        "end_source_line_index": 3,
        "page_sequence": 1,
        "source_line_index": 3,
    }

    assert subject._same_row_numeric_samples(pages, owner) == [pages[0]["lines"][1]]
    assert not subject._same_row_numeric_samples_are_complete(pages, owner, [owner, peer])
    assert not subject._same_row_numeric_samples_are_complete(pages, owner, [owner])

    pages[0]["lines"][3]["bbox"] = [0, 140, 300, 160]
    assert subject._same_row_numeric_samples_are_complete(pages, owner, [owner, peer])


def test_f3_scope_receipts_reject_coherent_status_anchor_and_explicit_surface_forgery() -> None:
    unknown = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    _insert_wrapped_other(unknown, prefix="Khoản diễn giải chưa có trong schema")
    _scan, unknown_axis = _build_f3(unknown)
    attacked = copy.deepcopy(unknown_axis)
    occurrence = next(
        item for item in attacked["role_occurrences"] if item["role"] == "INTERBANK_DEPOSIT_OTHER"
    )
    occurrence["source_scope_binding"]["status"] = (
        "REVIEWED_EXACT_SOURCE_SCOPE_TO_SCHEMA_ROLE_BINDING"
    )
    material = copy.deepcopy(occurrence["source_scope_binding"])
    material.pop("binding_id")
    occurrence["source_scope_binding"]["binding_id"] = (
        "aforav2:scope-binding:" + canonical_json_sha256_v1(material)
    )
    _coherently_replace_source_scope_binding(
        attacked, occurrence, occurrence["source_scope_binding"]
    )
    _coherently_rehash_occurrence(attacked)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="semantic matrix",
    ):
        subject._validate_result(attacked)

    _scan, discount_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Chiết khấu, tái chiết khấu", "5", "4"),
                ("Bằng ngoại tệ", "0", "0"),
            ]
        )
    )
    split_brain = copy.deepcopy(discount_axis)
    split_occurrence = next(
        item
        for item in split_brain["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
    )
    split_occurrence["source_scope_binding"] = None
    _coherently_rehash_occurrence(split_brain)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="nearest-parent scope axis",
    ):
        subject._validate_result(split_brain)

    attacked = copy.deepcopy(discount_axis)
    occurrence = next(
        item
        for item in attacked["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
    )
    receipt = occurrence["source_scope_binding"]
    receipt["anchor_span"]["source_line_index"] += 1
    material = copy.deepcopy(receipt)
    material.pop("binding_id")
    receipt["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(material)
    _coherently_replace_source_scope_binding(attacked, occurrence, receipt)
    _coherently_rehash_occurrence(attacked)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="actual occurrence",
    ):
        subject._validate_result(attacked)

    bare_occurrence = next(
        item
        for item in discount_axis["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
    )
    receipt = copy.deepcopy(bare_occurrence["source_scope_binding"])
    receipt.update(
        {
            "anchor_span": None,
            "binding_kind": "EXPLICIT_EXACT_SOURCE_SUBSCOPE_IN_LABEL",
            "interval": {
                "end_document_line_ordinal_exclusive": bare_occurrence["label_match"][
                    "end_document_line_ordinal"
                ]
                + 1,
                "start_document_line_ordinal": bare_occurrence["label_match"][
                    "document_line_ordinal"
                ],
            },
            "source_role": bare_occurrence["role"],
        }
    )
    receipt["source_span"]["role"] = bare_occurrence["role"]
    material = copy.deepcopy(receipt)
    material.pop("binding_id")
    receipt["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="semantic matrix",
    ):
        subject._validate_source_scope_binding(
            receipt,
            label_match=bare_occurrence["label_match"],
            role=bare_occurrence["role"],
        )


def test_f3_recursive_parent_provision_receipts_rederive_rows_and_geometry() -> None:
    _scan, deposit_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "98", "89"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "60", "50"),
                ("Tiền gửi có kỳ hạn", "40", "40"),
                ("Bằng VND", "40", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )
    attacked = copy.deepcopy(deposit_axis)
    provision = next(
        item
        for item in attacked["role_occurrences"]
        if item["role"] == "INTERBANK_DEPOSIT_PROVISION"
    )
    receipt = provision["source_scope_binding"]
    equation = receipt["geometry"]["equation"]
    equation["component_frontier"][0]["numbers"][0]["coefficient"] += 1
    equation["result"]["numbers"][0]["coefficient"] += 1
    equation_material = copy.deepcopy(equation)
    equation_material.pop("equation_id")
    equation["equation_id"] = "aforav2:direct-frontier-equation:" + canonical_json_sha256_v1(
        equation_material
    )
    material = copy.deepcopy(receipt)
    material.pop("binding_id")
    receipt["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(material)
    _coherently_replace_source_scope_binding(attacked, provision, receipt)
    _coherently_rehash_occurrence(attacked)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="component row or owner",
    ):
        subject._validate_result(attacked)

    _scan, total_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "52", "41"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )
    attacked = copy.deepcopy(total_axis)
    provision = next(
        item for item in attacked["role_occurrences"] if item["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    receipt = provision["source_scope_binding"]
    receipt["geometry"]["ordered_source_label_bboxes"][0][0] += 1
    material = copy.deepcopy(receipt)
    material.pop("binding_id")
    receipt["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(material)
    _coherently_replace_source_scope_binding(attacked, provision, receipt)
    _coherently_rehash_occurrence(attacked)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="component row or owner",
    ):
        subject._validate_result(attacked)


@pytest.mark.parametrize("tamper", ["WRONG_LOCAL_PARENT", "WRONG_ROOT"])
def test_f3_recursive_parent_provision_public_replay_rejects_parent_tamper(
    tamper: str,
) -> None:
    if tamper == "WRONG_LOCAL_PARENT":
        pages = _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "98", "89"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "60", "50"),
                ("Tiền gửi có kỳ hạn", "40", "40"),
                ("Bằng VND", "40", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ]
        )
        target_role = "INTERBANK_DEPOSIT_PROVISION"
    else:
        pages = _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "52", "41"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
        target_role = "TOTAL_INTERBANK_PROVISION"
    scan, axis = _build_f3(pages)
    attacked = copy.deepcopy(axis)
    provision = next(
        occurrence
        for occurrence in attacked["role_occurrences"]
        if occurrence["role"] == target_role
    )
    receipt = provision["source_scope_binding"]
    equation = receipt["geometry"]["equation"]
    if tamper == "WRONG_LOCAL_PARENT":
        wrong_parent = next(
            occurrence
            for occurrence in attacked["role_occurrences"]
            if occurrence["role"] == "INTERBANK_LOAN_GROUP"
        )
        equation["parent_occurrence_id"] = wrong_parent["occurrence_id"]
    else:
        equation["parent_occurrence_id"] = "aforav2:root:" + "0" * 64
    equation_material = copy.deepcopy(equation)
    equation_material.pop("equation_id")
    equation["equation_id"] = "aforav2:direct-frontier-equation:" + canonical_json_sha256_v1(
        equation_material
    )
    binding_material = copy.deepcopy(receipt)
    binding_material.pop("binding_id")
    receipt["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(binding_material)
    _coherently_replace_source_scope_binding(attacked, provision, receipt)
    _coherently_rehash_occurrence(attacked)
    effective = total_v1.project_accounting_family_coextensive_parent_total_region_v1(
        _f3_spec(), scan, scan["regions"][0]
    )

    with pytest.raises(subject.AccountingFamilyOccurrenceRowAxisV2Error):
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            attacked,
            pages,
            _f3_spec(),
            scan,
            scan["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=effective,
        )
