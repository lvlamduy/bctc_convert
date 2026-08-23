from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import sys
from pathlib import Path
from typing import Any

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation.accounting_table_axes_v1 import (
    line_has_accounting_value_surface_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, relative: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


graph_v2 = _load(
    "loan_maturity_variant_graph_v2_for_additional_test",
    "scripts/experiments/loan_maturity_variant_graph_v2.py",
)
evidence_v1 = _load(
    "loan_maturity_additional_population_evidence_v1_test",
    "scripts/experiments/loan_maturity_additional_population_evidence_v1.py",
)


def _record(text: str, x: int, y: int, *, width: int = 150) -> dict[str, Any]:
    return {
        "bbox": [x, y, x + width, y + 30],
        "source_text": text,
        "vietocr_text": text,
    }


def _inputs(
    *,
    parent_glyph: str = "DASH",
    child_glyph: str = "DASH",
    current_grand: str = "60",
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    records = [
        _record("5. Cho vay khách hàng", 40, 20, width=300),
        _record("Phân tích dư nợ theo thời gian", 70, 55, width=470),
        _record("30/06/2026", 650, 90, width=120),
        _record("31/12/2025", 950, 90, width=120),
        _record("Triệu đồng", 650, 125, width=120),
        _record("Triệu đồng", 950, 125, width=120),
        _record("Nợ ngắn hạn", 100, 190, width=310),
        _record("10", 650, 187, width=120),
        _record("11", 950, 187, width=120),
        _record("Nợ trung hạn", 100, 235, width=310),
        _record("20", 650, 232, width=120),
        _record("21", 950, 232, width=120),
        _record("Nợ dài hạn", 100, 280, width=310),
        _record("30", 650, 277, width=120),
        _record("31", 950, 277, width=120),
        _record("60", 650, 325, width=120),
        _record("63", 950, 325, width=120),
        _record("Nghiệp vụ phát hành thư tín dụng trả chậm", 100, 370, width=440),
        _record("5", 950, 367, width=120),
        _record("phát sinh trước ngày 01 tháng 7 năm 2024", 100, 400, width=430),
        _record("Nợ ngắn hạn", 100, 440, width=280),
        _record("5", 950, 437, width=120),
        _record(current_grand, 650, 490, width=120),
        _record("68", 950, 490, width=120),
        _record("Phân tích chất lượng nợ cho vay", 70, 550, width=450),
        _record("22", 700, 600, width=40),
    ]
    page = {
        "lines": [
            {**copy.deepcopy(record), "source_line_index": index}
            for index, record in enumerate(records)
        ],
        "page_sequence": 1,
        "primary_numeric_authority": True,
    }
    base = graph_v2.build_loan_maturity_variant_graph_document_v2([page])
    assert base["status"] == "UNRESOLVED"
    assert base["graphs"][0]["unresolved_reasons"] == [
        "ADDITIONAL_POPULATION_VISIBLE_DASH_EVIDENCE_REQUIRED"
    ]
    joined = [
        {
            "lines": [
                {
                    "bbox": copy.deepcopy(record["bbox"]),
                    "crop_ref": {
                        "path": f"unused/line-{index:04d}.png",
                        "sha256": f"{index + 1:064x}",
                        "size_bytes": 1,
                    },
                    "line_ordinal": index,
                    "numeric_recognition": {
                        "raw_prediction": record["source_text"],
                        "reader_score": 1.0,
                    },
                    "sample_id": f"sample-{index:09d}",
                    "vietocr_text": record["vietocr_text"],
                }
                for index, record in enumerate(records)
            ],
            "page_sequence": 1,
            "page_width": 1200,
        }
    ]
    image = Image.new("RGB", (1200, 650), "white")
    draw = ImageDraw.Draw(image)
    matcher = evidence_v1._matcher_page(joined[0])
    population = base["graphs"][0]["additional_source_populations"][0]
    centers = evidence_v1._lane_centers(base["graphs"][0])
    line_axis = evidence_v1._line_axis(joined[0])
    for record, glyph in zip(
        (population, population["breakdown"]),
        (parent_glyph, child_glyph),
        strict=True,
    ):
        label_boxes = evidence_v1._label_boxes(record, line_axis)
        visible = [
            {"bbox": cell["bbox"], "column_ordinal": cell["lane_index"]}
            for cell in record["values"]
            if cell["bbox"] is not None
        ]
        proposals = propose_missing_value_lane_regions_v1(
            matcher["lines"],
            label_boxes=label_boxes,
            is_numeric=line_has_accounting_value_surface_v1,
            page_width=1200,
            page_height=650,
            minimum_x_ratio=0.05,
            maximum_x_ratio=0.995,
            resolved_column_centers=centers,
            resolved_visible_value_cells=visible,
        )
        assert len(proposals) == 1 and proposals[0]["column_ordinal"] == 0
        left, top, right, bottom = proposals[0]["raw_pixel_bbox"]
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        if glyph == "DASH":
            draw.line(
                (center_x - 10, center_y, center_x + 10, center_y),
                fill="black",
                width=2,
            )
        elif glyph == "DEGRADED":
            draw.rectangle(
                (center_x - 5, center_y - 4, center_x + 5, center_y + 4),
                fill="black",
            )
        elif glyph != "BLANK":
            raise AssertionError("unsupported synthetic glyph")
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    render_ref = {
        "pixel_height": 650,
        "pixel_width": 1200,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    material = {
        "archive_id": "synthetic-archive",
        "authority": copy.deepcopy(region_v1._RENDER_AUTHORITY),
        "document_ordinal": 1,
        "format_version": region_v1.RENDER_FORMAT_VERSION,
        "index_id": "synthetic-index",
        "physical_page": 1,
        "plan_id": "synthetic-plan",
        "render_ref": render_ref,
        "state": "AUTHENTICATED_EXACT_SOURCE_PAGE_RENDER_SNAPSHOT",
    }
    snapshot = {
        **material,
        "render_id": "ffaprv1:render:" + canonical_json_sha256_v1(material),
        "render_png_bytes": payload,
    }
    return base, joined, snapshot


def test_visible_dash_overlay_is_exact_replayable_and_keeps_footer_outside_table() -> None:
    base, joined, snapshot = _inputs()
    result = evidence_v1.build_loan_maturity_additional_population_evidence_v1(
        base, joined, snapshot, document_ordinal=1
    )

    assert result["status"] == "AUTHENTICATED_PIXEL_DASH_AND_ACCOUNTING_EXACT"
    assert len(result["evidence"]) == 2
    assert {item["role"] for item in result["evidence"]} == {
        "ADDITIONAL_PARENT",
        "ADDITIONAL_SHORT_BREAKDOWN",
    }
    assert all(item["classification"] == "VISIBLE_PIXEL_DASH_ZERO" for item in result["evidence"])
    assert all(check["status"] == "CORROBORATED_EXACT" for check in result["accounting_checks"])
    assert result["additional_population"]["grand_total"]["selected_values"] == [60, 68]
    assert (
        evidence_v1.validate_loan_maturity_additional_population_evidence_replay_v1(
            result, base, joined, snapshot, document_ordinal=1
        )
        == result
    )


def test_blank_crop_and_tampered_identity_fail_closed() -> None:
    base, joined, snapshot = _inputs()
    blank = Image.new("RGB", (1200, 650), "white")
    stream = io.BytesIO()
    blank.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    blank_snapshot = copy.deepcopy(snapshot)
    blank_snapshot["render_png_bytes"] = payload
    blank_snapshot["render_ref"].update(
        {"sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)}
    )
    material = {
        key: copy.deepcopy(value)
        for key, value in blank_snapshot.items()
        if key not in {"render_id", "render_png_bytes"}
    }
    blank_snapshot["render_id"] = "ffaprv1:render:" + canonical_json_sha256_v1(material)
    unresolved = evidence_v1.build_loan_maturity_additional_population_evidence_v1(
        base, joined, blank_snapshot, document_ordinal=1
    )
    assert unresolved["status"] == "UNRESOLVED_PIXEL_GLYPH_OR_ACCOUNTING"
    assert all(
        item["classification"] == "UNRESOLVED_PIXEL_GLYPH" for item in unresolved["evidence"]
    )

    forged = copy.deepcopy(unresolved)
    forged["accounting_checks"][0]["status"] = "CORROBORATED_EXACT"
    with pytest.raises(evidence_v1.LoanMaturityAdditionalPopulationEvidenceV1Error):
        evidence_v1.validate_loan_maturity_additional_population_evidence_v1(forged)

    shuffled = copy.deepcopy(joined)
    shuffled[0]["lines"][0], shuffled[0]["lines"][1] = (
        shuffled[0]["lines"][1],
        shuffled[0]["lines"][0],
    )
    with pytest.raises(evidence_v1.LoanMaturityAdditionalPopulationEvidenceV1Error):
        evidence_v1.build_loan_maturity_additional_population_evidence_v1(
            base, shuffled, snapshot, document_ordinal=1
        )


def test_one_centered_short_mark_needs_same_lane_clear_peer_and_exact_equations() -> None:
    base, joined, snapshot = _inputs(parent_glyph="DEGRADED")
    paired = evidence_v1.build_loan_maturity_additional_population_evidence_v1(
        base, joined, snapshot, document_ordinal=1
    )
    assert paired["status"] == "AUTHENTICATED_PIXEL_DASH_AND_ACCOUNTING_EXACT"
    degraded = next(
        item
        for item in paired["evidence"]
        if item["classification"] == "PAIRED_CENTERED_HIGH_FILL_SHORT_MARK_CANDIDATE"
    )
    assert degraded["dash_evidence"]["classification"] == "UNRESOLVED_NOT_ONE_DASH_GLYPH"
    assert degraded["paired_clear_dash_peer_role"] == "ADDITIONAL_SHORT_BREAKDOWN"

    for parent_glyph, child_glyph in (
        ("DEGRADED", "DEGRADED"),
        ("BLANK", "DASH"),
    ):
        base, joined, snapshot = _inputs(
            parent_glyph=parent_glyph,
            child_glyph=child_glyph,
        )
        unresolved = evidence_v1.build_loan_maturity_additional_population_evidence_v1(
            base, joined, snapshot, document_ordinal=1
        )
        assert unresolved["status"] == "UNRESOLVED_PIXEL_GLYPH_OR_ACCOUNTING"

    parent_values = [{"selected_value": None}, {"selected_value": 5}]
    child_values = [{"selected_value": None}, {"selected_value": 5}]
    parent_evidence = [
        {
            "classification": "UNRESOLVED_PIXEL_GLYPH",
            "dash_evidence": {
                "classification": "UNRESOLVED_NOT_ONE_DASH_GLYPH",
                "glyph_metrics": {
                    "component_aspect_ratio": 1.22,
                    "component_count": 1,
                    "component_height_ratio": 0.27,
                    "component_width_ratio": 0.23,
                    "horizontal_center_displacement_ratio": 0.0,
                    "ink_fill_ratio": 0.8,
                    "vertical_center_displacement_ratio": 0.0,
                },
            },
            "lane_index": 0,
            "region_id": "parent-region",
            "role": "ADDITIONAL_PARENT",
        }
    ]
    wrong_lane_child = [
        {
            "classification": "VISIBLE_PIXEL_DASH_ZERO",
            "dash_evidence": {"classification": "VISIBLE_HORIZONTAL_DASH_GLYPH"},
            "lane_index": 1,
            "region_id": "child-region",
            "role": "ADDITIONAL_SHORT_BREAKDOWN",
        }
    ]
    evidence_v1._promote_one_paired_short_mark(
        parent_values,
        child_values,
        parent_evidence,
        wrong_lane_child,
    )
    assert parent_values[0]["selected_value"] is None

    base, joined, snapshot = _inputs(current_grand="61")
    mismatch = evidence_v1.build_loan_maturity_additional_population_evidence_v1(
        base, joined, snapshot, document_ordinal=1
    )
    assert mismatch["status"] == "UNRESOLVED_PIXEL_GLYPH_OR_ACCOUNTING"
    assert any(check["status"] == "UNRESOLVED" for check in mismatch["accounting_checks"])
