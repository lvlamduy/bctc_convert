from __future__ import annotations

import copy
import hashlib
import inspect
import io
from collections.abc import Sequence
from typing import Any

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation import loan_geography_numeric_reconciliation_v1 as numeric_v1
from bctc_ai.evaluation.loan_geography_scoped_table_adapter_v1 import (
    FAMILY_ID,
    LOAN_GEOGRAPHY_REGION_QUERY_SPEC_V2,
    build_loan_geography_scoped_graphs_v1,
    project_loan_geography_numeric_input_v1,
    project_loan_geography_visible_dash_graph_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from scripts.experiments import loan_geography_visible_dash_evidence_v1 as subject


def _adapter_line(
    index: int, text: str, bbox: list[int], numeric: str | None = None
) -> dict[str, Any]:
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"crop-{index}.png",
            "sha256": f"{index % 10}" * 64,
            "size_bytes": index + 1,
        },
        "line_ordinal": index,
        "numeric_recognition": {
            "raw_prediction": numeric if numeric is not None else text,
            "reader_score": 0.99,
        },
        "sample_id": f"sample-{index}",
        "vietocr_text": text,
    }


def _owner_lines(offset: int = 0) -> list[dict[str, Any]]:
    return [
        _adapter_line(90 + offset, "Mức độ tập trung tài sản và công nợ", [20, 20, 610, 46]),
        _adapter_line(3 + offset, "theo khu vực địa lý", [20, 50, 310, 76]),
    ]


def _row_page(*, two_periods: bool) -> dict[str, Any]:
    if two_periods:
        lines = [
            *_owner_lines(),
            _adapter_line(1, "31/12/2025", [540, 84, 690, 110]),
            _adapter_line(2, "31/12/2024", [760, 84, 910, 110]),
            _adapter_line(30, "Cho vay khách hàng", [520, 125, 710, 153]),
            _adapter_line(31, "Cho vay khách hàng", [740, 125, 930, 153]),
            _adapter_line(32, "Triệu VND", [550, 165, 690, 191]),
            _adapter_line(33, "Triệu VND", [770, 165, 910, 191]),
            _adapter_line(4, "Trong nước", [40, 220, 190, 248]),
            _adapter_line(5, "1.000", [580, 220, 660, 248], "1.000"),
            _adapter_line(6, "900", [800, 220, 870, 248], "900"),
            _adapter_line(7, "Nước ngoài", [40, 270, 190, 298]),
            _adapter_line(10, "Tổng cộng", [40, 320, 190, 348]),
            _adapter_line(11, "1.000", [580, 320, 660, 348], "1.000"),
            _adapter_line(12, "900", [800, 320, 870, 348], "900"),
        ]
    else:
        lines = [
            *_owner_lines(),
            _adapter_line(1, "30/06/2025", [650, 84, 810, 110]),
            _adapter_line(2, "Cho vay khách hàng", [620, 125, 840, 153]),
            _adapter_line(3_000, "Triệu VND", [650, 165, 810, 191]),
            _adapter_line(4, "Trong nước", [40, 220, 190, 248]),
            _adapter_line(5, "619.850.276", [685, 220, 800, 248], "619.850.276"),
            _adapter_line(7, "Nước ngoài", [40, 270, 190, 298]),
            _adapter_line(10, "Tổng cộng", [40, 320, 190, 348]),
            _adapter_line(11, "619.850.276", [685, 320, 800, 348], "619.850.276"),
        ]
    return {
        "lines": list(reversed(lines)),
        "page_height": 400,
        "page_sequence": 1,
        "page_width": 1_000,
    }


def _column_page(sequence: int, period: str) -> dict[str, Any]:
    offset = sequence * 100
    lines = [
        *_owner_lines(offset),
        _adapter_line(20 + offset, period, [590, 80, 830, 106]),
        _adapter_line(21 + offset, "Triệu VND", [700, 84, 845, 110]),
        _adapter_line(22 + offset, "Trong nước", [570, 120, 710, 148]),
        _adapter_line(23 + offset, "Nước ngoài", [750, 120, 890, 148]),
        _adapter_line(26 + offset, "Tổng cộng", [920, 120, 995, 148]),
        _adapter_line(24 + offset, "Cho vay", [30, 178, 170, 206]),
        _adapter_line(25 + offset, "khách hàng", [30, 208, 185, 236]),
        _adapter_line(28 + offset, "900", [595, 204, 665, 232], "900"),
        _adapter_line(37 + offset, "900", [930, 204, 990, 232], "900"),
    ]
    return {
        "lines": list(reversed(lines)),
        "page_height": 400,
        "page_sequence": sequence,
        "page_width": 1_000,
    }


def _packet(
    document_ordinal: int, *, page_count: int, document_id: str | None = None
) -> dict[str, Any]:
    material = {
        "assurance": "AUDITED",
        "bank_provenance": "SYNTHETIC",
        "document_evidence_root_sha256": f"{document_ordinal + 100:064x}",
        "document_id": document_id or f"synthetic-{document_ordinal}",
        # The adapter receipt contains one document, so its authenticated
        # corpus ordinal is one. ``document_ordinal`` remains only a fixture
        # identity seed and never routes table discovery.
        "document_ordinal": 1,
        "line_count": page_count * 10,
        "page_count": page_count,
        "period": "ANNUAL",
        "scope": "CONSOLIDATED",
        "source_pdf_ref": {
            "path": f"opaque/source-{document_ordinal}.pdf",
            "sha256": f"{document_ordinal + 200:064x}",
            "size_bytes": 1000 + document_ordinal,
        },
        "year": 2025,
    }
    return {
        **material,
        "packet_id": "ffdesv1:document:" + canonical_json_sha256_v1(material),
    }


def _adapter_snapshot(document_seed: int, pages: Sequence[dict[str, Any]]) -> dict[str, Any]:
    packet = _packet(document_seed, page_count=max(page["page_sequence"] for page in pages))
    packet["line_count"] = sum(len(page["lines"]) for page in pages)
    packet_material = copy.deepcopy(packet)
    packet_material.pop("packet_id")
    packet["packet_id"] = "ffdesv1:document:" + canonical_json_sha256_v1(packet_material)
    material = {
        "document_packet": packet,
        "joined_pages": list(pages),
        "manifest_id": f"manifest-{document_seed}",
        "query_selection_id": f"selection-{document_seed}",
        "selected_page_dimensions": [
            {
                "physical_page": page["page_sequence"],
                "pixel_height": page["page_height"],
                "pixel_width": page["page_width"],
                "render_sha256": f"{document_seed % 10}" * 64,
                "render_size_bytes": 1,
            }
            for page in pages
        ],
        "state": "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE",
    }
    return {
        **material,
        "snapshot_id": "ffdesv1:selected:" + canonical_json_sha256_v1(material),
    }


def _adapter_receipt(snapshot: dict[str, Any]) -> dict[str, Any]:
    packet = snapshot["document_packet"]
    outcome_material = {
        "coverage_status": "PROVEN_COMPLETE_FOR_DECLARED_SPEC",
        "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
        "document_id": packet["document_id"],
        "document_ordinal": packet["document_ordinal"],
        "document_packet_id": packet["packet_id"],
        "selected_pages": [page["page_sequence"] for page in snapshot["joined_pages"]],
    }
    outcome = {
        **outcome_material,
        "outcome_id": "fffrrv2:document:" + canonical_json_sha256_v1(outcome_material),
    }
    material = {
        "documents": [outcome],
        "family_id": FAMILY_ID,
        "format_version": "FAMILY_FIRST_REGION_RETRIEVAL_RECEIPT_V2",
        "query_spec": copy.deepcopy(LOAN_GEOGRAPHY_REGION_QUERY_SPEC_V2),
    }
    return {
        **material,
        "receipt_id": "fffrrv2:receipt:" + canonical_json_sha256_v1(material),
    }


def _adapter_projection(
    document_seed: int, *, layout_mode: str, two_periods: bool = True
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    pages = (
        [_row_page(two_periods=two_periods)]
        if layout_mode == "ROW_GEOGRAPHY_COLUMN_ACCOUNTING"
        else [
            _column_page(1, "31/12/2025"),
            _column_page(2, "31/12/2024"),
        ]
    )
    snapshot = _adapter_snapshot(document_seed, pages)
    receipt = _adapter_receipt(snapshot)
    batch = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])
    document = batch["documents"][0]
    assert document["disposition"] == "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
    graph = project_loan_geography_visible_dash_graph_v1(document, snapshot["document_packet"])
    numeric = project_loan_geography_numeric_input_v1(document, snapshot["document_packet"])
    return graph, receipt, snapshot, numeric


def _render(image: Image.Image, *, document_ordinal: int, physical_page: int) -> dict[str, Any]:
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    reference = {
        "pixel_height": image.height,
        "pixel_width": image.width,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    material = {
        "archive_id": "archive",
        "authority": copy.deepcopy(region_v1._RENDER_AUTHORITY),
        "document_ordinal": document_ordinal,
        "format_version": region_v1.RENDER_FORMAT_VERSION,
        "index_id": "index",
        "physical_page": physical_page,
        "plan_id": "plan",
        "render_ref": reference,
        "state": "AUTHENTICATED_EXACT_SOURCE_PAGE_RENDER_SNAPSHOT",
    }
    return {
        **material,
        "render_id": "ffaprv1:render:" + canonical_json_sha256_v1(material),
        "render_png_bytes": payload,
    }


def _draw_direct(draw: ImageDraw.ImageDraw, bbox: list[int]) -> None:
    center_x = (bbox[0] + bbox[2]) // 2
    center_y = (bbox[1] + bbox[3]) // 2
    draw.rectangle([center_x - 6, center_y - 2, center_x + 5, center_y + 1], fill="black")


def _draw_candidate(draw: ImageDraw.ImageDraw, bbox: list[int]) -> None:
    center_x = (bbox[0] + bbox[2]) // 2
    center_y = (bbox[1] + bbox[3]) // 2
    draw.rectangle([center_x - 1, center_y - 1, center_x + 1, center_y + 1], fill="black")


def _inputs(
    document_ordinal: int,
    *,
    layout_mode: str = "ROW_GEOGRAPHY_COLUMN_ACCOUNTING",
    glyphs: Sequence[str] = ("direct", "direct"),
) -> tuple[dict[str, Any], dict[str, Any], tuple[dict[str, Any], ...], dict[str, Any]]:
    graph, receipt, snapshot, _numeric = _adapter_projection(
        document_ordinal, layout_mode=layout_mode
    )
    missing_cells = [
        cell
        for logical in graph["graphs"]
        for segment in logical["segments"]
        for cell in segment["role_cells"]
        if cell["status"] == "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_EVIDENCE"
    ]
    assert len(missing_cells) == len(glyphs) == 2
    manifest = subject.build_loan_geography_dash_hole_manifest_from_graph_v1(
        graph,
        selection_receipt_id=receipt["receipt_id"],
        period_bindings=[
            {
                "graph_cell_id": cell["graph_cell_id"],
                "period_role": cell["period_role"],
                "resolved_period": cell["resolved_period"],
            }
            for cell in missing_cells
        ],
    )
    holes = sorted(manifest["holes"], key=lambda item: item["period_lane_index"])
    dimensions = {item["physical_page"]: item for item in snapshot["selected_page_dimensions"]}
    by_page: dict[int, Image.Image] = {
        page: Image.new(
            "RGB",
            (dimensions[page]["pixel_width"], dimensions[page]["pixel_height"]),
            "white",
        )
        for page in {hole["page_sequence"] for hole in holes}
    }
    for hole, glyph in zip(holes, glyphs, strict=True):
        draw = ImageDraw.Draw(by_page[hole["page_sequence"]])
        if glyph == "direct":
            _draw_direct(draw, hole["expected_pixel_bbox"])
        elif glyph == "candidate":
            _draw_candidate(draw, hole["expected_pixel_bbox"])
        elif glyph == "digit":
            bbox = hole["expected_pixel_bbox"]
            center_x = (bbox[0] + bbox[2]) // 2
            center_y = (bbox[1] + bbox[3]) // 2
            draw.rectangle([center_x - 2, center_y - 9, center_x + 2, center_y + 8], fill="black")
        elif glyph != "blank":
            raise AssertionError(glyph)
    renders = tuple(
        _render(
            image,
            document_ordinal=snapshot["document_packet"]["document_ordinal"],
            physical_page=page,
        )
        for page, image in sorted(by_page.items())
    )
    return graph, manifest, renders, snapshot["document_packet"]


def _overlay(inputs: tuple[Any, ...]) -> dict[str, Any]:
    value = subject.build_loan_geography_visible_dash_evidence_v1(*inputs)
    assert subject.validate_loan_geography_visible_dash_evidence_replay_v1(value, *inputs) == value
    return value


def _actual_row_graph() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    return _adapter_projection(
        33,
        layout_mode="ROW_GEOGRAPHY_COLUMN_ACCOUNTING",
        two_periods=False,
    )


def _rehash(value: dict[str, Any]) -> None:
    material = copy.deepcopy(value)
    material.pop("evidence_id")
    value["evidence_id"] = "lgdashv1:evidence:" + canonical_json_sha256_v1(material)


def test_direct_dashes_replay_and_expose_only_authenticated_zero_bindings() -> None:
    inputs = _inputs(1)
    result = _overlay(inputs)

    assert result["status"] == "AUTHENTICATED_VISIBLE_DASH_CELLS_BOUND"
    assert result["metrics"] == {
        "bounded_candidate_cell_count": 0,
        "direct_visible_dash_zero_cell_count": 2,
        "requested_hole_count": 2,
        "unresolved_pixel_cell_count": 0,
    }
    bindings = subject.read_loan_geography_direct_dash_numeric_bindings_v1(result, *inputs)
    assert len(bindings) == 2
    assert {item["normalized_value"] for item in bindings} == {0}
    assert all(item["crop_png_bytes"].startswith(b"\x89PNG") for item in bindings)
    assert all(item["graph_id"] == inputs[0]["graphs"][0]["graph_id"] for item in bindings)
    assert all(item["pixel_region_id"].startswith("ffaprv1:region:") for item in bindings)
    assert all(item["graph_id"] != item["pixel_region_id"] for item in bindings)

    numeric_bindings = subject.read_loan_geography_numeric_reconciliation_dash_bindings_v1(
        result, *inputs
    )
    assert len(numeric_bindings) == 2
    assert set(numeric_bindings[0]) == {
        "cell_id",
        "crop_png_bytes",
        "evidence",
        "lane_index",
        "lane_type",
        "page_sequence",
        "region_id",
        "role",
    }
    assert {item["region_id"] for item in numeric_bindings} == {inputs[0]["graphs"][0]["graph_id"]}


def test_thin_adapter_projectors_join_dash_and_numeric_without_retyping_geometry() -> None:
    graph, receipt, snapshot, numeric_source = _actual_row_graph()
    segment = graph["graphs"][0]["segments"][0]
    graph_cell = next(
        cell
        for cell in segment["role_cells"]
        if cell["status"] == "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_EVIDENCE"
    )
    manifest = subject.build_loan_geography_dash_hole_manifest_from_graph_v1(
        graph,
        selection_receipt_id=receipt["receipt_id"],
        period_bindings=[
            {
                "graph_cell_id": graph_cell["graph_cell_id"],
                "period_role": "CURRENT",
                "resolved_period": "2025-06-30",
            }
        ],
    )
    hole = manifest["holes"][0]
    assert hole["expected_pixel_bbox"] == graph_cell["expected_pixel_bbox"]
    assert hole["page_sequence"] == graph_cell["page_sequence"] == 1
    assert hole["role"] == graph_cell["role"] == "FOREIGN_TOTAL"
    assert hole["graph_id"] == graph["graphs"][0]["graph_id"]
    assert hole["axis_binding_sha256"] == canonical_json_sha256_v1(
        {
            "period_headings": segment["period_headings"],
            "scope_axis": segment["scope_axis"],
            "unit_headings": segment["unit_headings"],
        }
    )

    dimensions = snapshot["selected_page_dimensions"][0]
    image = Image.new("RGB", (dimensions["pixel_width"], dimensions["pixel_height"]), "white")
    _draw_direct(ImageDraw.Draw(image), hole["expected_pixel_bbox"])
    packet = snapshot["document_packet"]
    render = _render(
        image,
        document_ordinal=packet["document_ordinal"],
        physical_page=hole["page_sequence"],
    )
    inputs = graph, manifest, (render,), packet
    overlay = _overlay(inputs)
    assert overlay["metrics"]["direct_visible_dash_zero_cell_count"] == 1
    assert overlay["rescue_cells"][0]["graph_cell_id"] == graph_cell["graph_cell_id"]
    assert overlay["rescue_cells"][0]["graph_id"] == graph["graphs"][0]["graph_id"]
    assert overlay["rescue_cells"][0]["pixel_region_id"].startswith("ffaprv1:region:")

    direct = subject.read_loan_geography_numeric_reconciliation_dash_bindings_v1(overlay, *inputs)
    foreign_numeric_cell = next(
        row["cells"][0] for row in numeric_source["mapped_rows"] if row["role"] == "FOREIGN_TOTAL"
    )
    assert numeric_source["region_id"] == graph["graphs"][0]["graph_id"]
    assert foreign_numeric_cell["cell_id"] == graph_cell["graph_cell_id"]
    reconciled = numeric_v1.build_loan_geography_numeric_reconciliation_v1(
        numeric_source, visible_dash_evidence=direct
    )
    assert reconciled["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert reconciled["metrics"]["visible_dash_zero_cell_count"] == 1

    wrong_region = copy.deepcopy(numeric_source)
    wrong_region["region_id"] = overlay["rescue_cells"][0]["pixel_region_id"]
    with pytest.raises(numeric_v1.LoanGeographyNumericReconciliationV1Error):
        numeric_v1.build_loan_geography_numeric_reconciliation_v1(
            wrong_region, visible_dash_evidence=direct
        )

    wrong_cell = copy.deepcopy(numeric_source)
    foreign_row = next(row for row in wrong_cell["mapped_rows"] if row["role"] == "FOREIGN_TOTAL")
    foreign_row["cells"][0]["cell_id"] = next(
        row["cells"][0]["cell_id"]
        for row in wrong_cell["mapped_rows"]
        if row["role"] == "DOMESTIC_TOTAL"
    )
    with pytest.raises(numeric_v1.LoanGeographyNumericReconciliationV1Error):
        numeric_v1.build_loan_geography_numeric_reconciliation_v1(
            wrong_cell, visible_dash_evidence=direct
        )


@pytest.mark.parametrize("glyph", ("blank", "digit"))
def test_blank_or_nondash_pixels_never_become_zero(glyph: str) -> None:
    inputs = _inputs(1, glyphs=("direct", glyph))
    result = _overlay(inputs)

    assert result["status"] == ("PARTIAL_VISIBLE_DASH_EVIDENCE_RETAINED_WITH_UNRESOLVED_CELLS")
    unresolved = next(
        cell for cell in result["rescue_cells"] if cell["period_role"] == "COMPARATIVE"
    )
    assert unresolved["admission_class"] == "UNRESOLVED_PIXEL_GLYPH"
    assert unresolved["normalized_value"] is None
    bindings = subject.read_loan_geography_direct_dash_numeric_bindings_v1(result, *inputs)
    assert len(bindings) == 1


def test_degraded_mark_stays_raw_until_exact_replayed_structural_peer_binding() -> None:
    candidate_inputs = _inputs(1, glyphs=("candidate", "direct"))
    peer_inputs = _inputs(2)
    candidate_result = _overlay(candidate_inputs)
    peer_result = _overlay(peer_inputs)
    candidate_material = next(
        cell
        for cell in subject.read_loan_geography_dash_cell_replay_material_v1(
            candidate_result, *candidate_inputs
        )
        if cell["period_role"] == "CURRENT"
    )
    peer_material = next(
        cell
        for cell in subject.read_loan_geography_dash_cell_replay_material_v1(
            peer_result, *peer_inputs
        )
        if cell["period_role"] == "CURRENT"
    )

    assert candidate_material["admission_class"] == (
        "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE_RETAINED"
    )
    assert candidate_material["normalized_value"] is None
    pair = subject.build_loan_geography_bounded_dash_peer_binding_v1(
        candidate_material, peer_material
    )
    assert pair["normalized_value"] == 0
    assert pair["structural_binding"]["role"] == "FOREIGN_TOTAL"
    assert set(pair["structural_binding"]) == {
        "role",
        "resolved_period",
        "period_role",
        "lane_type",
        "lane_index",
        "layout_mode",
        "period_lane_index",
        "source_geography_ordinal",
    }

    wrong_period = copy.deepcopy(peer_material)
    wrong_period["resolved_period"] = "30/06/2025"
    with pytest.raises(subject.LoanGeographyVisibleDashEvidenceV1Error):
        subject.build_loan_geography_bounded_dash_peer_binding_v1(candidate_material, wrong_period)


def test_exact_expected_42_detector_holes_cover_both_generic_orientations() -> None:
    overlays = []
    for ordinal in range(1, 4):
        inputs = _inputs(ordinal, layout_mode="ROW_GEOGRAPHY_COLUMN_ACCOUNTING")
        overlays.append(_overlay(inputs))
    for ordinal in range(4, 22):
        inputs = _inputs(ordinal, layout_mode="COLUMN_GEOGRAPHY_ROW_ACCOUNTING")
        overlays.append(_overlay(inputs))

    assert sum(item["metrics"]["requested_hole_count"] for item in overlays) == 42
    assert sum(item["metrics"]["direct_visible_dash_zero_cell_count"] for item in overlays) == 42
    assert {cell["layout_mode"] for overlay in overlays for cell in overlay["rescue_cells"]} == {
        "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS",
        "GEOGRAPHY_COLUMNS_ACCOUNTING_FAMILY_ROWS",
    }


def test_cross_page_segments_crop_only_their_own_authenticated_page_raster() -> None:
    inputs = _inputs(1, layout_mode="COLUMN_GEOGRAPHY_ROW_ACCOUNTING")
    result = _overlay(inputs)
    material = subject.read_loan_geography_dash_cell_replay_material_v1(result, *inputs)

    assert {item["page_sequence"] for item in material} == {1, 2}
    assert len({item["segment_id"] for item in material}) == 2
    assert len({item["pixel_region_id"] for item in material}) == 2
    for item in material:
        source_render = next(
            render
            for render in result["render_bindings"]
            if render["physical_page"] == item["page_sequence"]
        )
        rescue_cell = next(
            cell
            for cell in result["rescue_cells"]
            if cell["cell_evidence_id"] == item["cell_evidence_id"]
        )
        assert rescue_cell["render_id"] == source_render["render_id"]


@pytest.mark.parametrize(
    "mutation",
    (
        "graph_id",
        "segment",
        "role",
        "lane",
        "period",
        "period_key",
        "period_lane",
        "period_role",
        "source_column",
        "pixel_region_id",
        "crop",
        "render",
    ),
)
def test_role_lane_period_crop_or_render_swap_fails_closed(mutation: str) -> None:
    inputs = _inputs(1)
    result = _overlay(inputs)
    forged = copy.deepcopy(result)
    first, second = forged["rescue_cells"]
    if mutation == "graph_id":
        first["graph_id"] = "astgv1:graph:" + "0" * 64
    elif mutation == "segment":
        first["segment_id"] = "astgv1:segment:" + "0" * 64
    elif mutation == "role":
        first["role"] = "DOMESTIC_TOTAL"
    elif mutation == "lane":
        first["lane_index"] = second["lane_index"]
    elif mutation == "period":
        first["resolved_period"] = second["resolved_period"]
    elif mutation == "period_key":
        first["period_key"] = second["period_key"]
    elif mutation == "period_lane":
        first["period_lane_index"] = second["period_lane_index"]
    elif mutation == "period_role":
        first["period_role"] = second["period_role"]
    elif mutation == "source_column":
        first["source_geography_ordinal"] = 0
    elif mutation == "pixel_region_id":
        first["pixel_region_id"] = first["graph_id"]
    elif mutation == "crop":
        first["region_png_ref"]["sha256"] = "0" * 64
    else:
        first["render_id"] = "ffaprv1:render:" + "0" * 64
    _rehash(forged)

    with pytest.raises(subject.LoanGeographyVisibleDashEvidenceV1Error):
        subject.validate_loan_geography_visible_dash_evidence_v1(forged)


def test_graph_manifest_render_and_packet_are_exact_replay_bindings() -> None:
    inputs = _inputs(1)
    result = _overlay(inputs)
    graph, manifest, renders, packet = inputs

    forged_graph = copy.deepcopy(graph)
    forged_graph["status"] = "FORGED_SHARED_GRAPH_STATUS"
    graph_material = copy.deepcopy(forged_graph)
    graph_material.pop("result_id")
    result_prefix = graph["result_id"].rsplit(":", 1)[0] + ":"
    forged_graph["result_id"] = result_prefix + canonical_json_sha256_v1(graph_material)
    with pytest.raises(subject.LoanGeographyVisibleDashEvidenceV1Error):
        subject.validate_loan_geography_visible_dash_evidence_replay_v1(
            result, forged_graph, manifest, renders, packet
        )

    forged_render = copy.deepcopy(renders[0])
    forged_render["render_png_bytes"] += b"x"
    with pytest.raises(subject.LoanGeographyVisibleDashEvidenceV1Error):
        subject.validate_loan_geography_visible_dash_evidence_replay_v1(
            result, graph, manifest, (forged_render,), packet
        )

    forged_packet = copy.deepcopy(packet)
    forged_packet["source_pdf_ref"]["path"] = "opaque/forged.pdf"
    with pytest.raises(subject.LoanGeographyVisibleDashEvidenceV1Error):
        subject.validate_loan_geography_visible_dash_evidence_replay_v1(
            result, graph, manifest, renders, forged_packet
        )


def test_external_period_binding_cannot_override_graph_resolved_period_lane() -> None:
    graph, manifest, _renders, _packet_value = _inputs(1)
    bindings = [
        {
            "graph_cell_id": hole["graph_cell_id"],
            "period_role": hole["period_role"],
            "resolved_period": hole["resolved_period"],
        }
        for hole in manifest["holes"]
    ]
    bindings[0]["resolved_period"] = "2025-06-30"

    with pytest.raises(subject.LoanGeographyVisibleDashEvidenceV1Error):
        subject.build_loan_geography_dash_hole_manifest_from_graph_v1(
            graph,
            selection_receipt_id=manifest["selection_receipt_id"],
            period_bindings=bindings,
        )


@pytest.mark.parametrize("field", ("page_sequence", "lane_index"))
def test_bool_is_not_an_integer_page_or_lane(field: str) -> None:
    graph, manifest, _renders, _packet_value = _inputs(1)
    raw = [
        {key: copy.deepcopy(value) for key, value in hole.items() if key != "hole_id"}
        for hole in manifest["holes"]
    ]
    raw[0][field] = True
    with pytest.raises(subject.LoanGeographyVisibleDashEvidenceV1Error):
        subject.build_loan_geography_dash_hole_manifest_v1(
            graph,
            selection_receipt_id=manifest["selection_receipt_id"],
            holes=raw,
        )


@pytest.mark.parametrize("noncanonical_role", ("DOMESTIC", "FOREIGN"))
def test_noncanonical_short_role_alias_is_rejected_without_translation(
    noncanonical_role: str,
) -> None:
    graph, manifest, _renders, _packet_value = _inputs(1)
    raw = [
        {key: copy.deepcopy(value) for key, value in hole.items() if key != "hole_id"}
        for hole in manifest["holes"]
    ]
    raw[0]["role"] = noncanonical_role
    with pytest.raises(subject.LoanGeographyVisibleDashEvidenceV1Error):
        subject.build_loan_geography_dash_hole_manifest_v1(
            graph,
            selection_receipt_id=manifest["selection_receipt_id"],
            holes=raw,
        )


def test_contract_has_no_bank_page_value_or_accounting_routing() -> None:
    source = inspect.getsource(subject)
    assert "bank_code" not in source
    assert "report_norm_id" not in source
    assert subject._AUTHORITY["accounting_can_infer_or_backsolve_zero"] is False
    assert subject._AUTHORITY["bounded_peer_selection_uses_accounting_values"] is False
    assert subject._AUTHORITY["bank_filename_page_or_expected_value_routing_authority"] is False
