from __future__ import annotations

import copy
import hashlib
import io

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_axis_v1
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import family_first_accounting_evidence_sweep_v1 as sweep_v1
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from scripts.experiments import loan_currency_variant_graph_v2 as graph_v2
from scripts.experiments import loan_currency_visible_dash_evidence_v1 as subject


def _line(
    ordinal: int,
    text: str,
    raw: str,
    bbox: list[int],
    *,
    document_ordinal: int,
    page_sequence: int = 1,
) -> dict[str, object]:
    sample = document_ordinal * 100_000 + page_sequence * 1_000 + ordinal + 1
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"opaque/crop-{sample}.png",
            "sha256": f"{sample:064x}",
            "size_bytes": 100 + sample,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": raw, "reader_score": 0.95},
        "sample_id": f"sample-{sample:09d}",
        "vietocr_text": text,
    }


def _joined_page(document_ordinal: int, *, current_period: str = "31/12/2025"):
    rows: list[dict[str, object]] = []

    def add(text: str, raw: str, bbox: list[int]) -> None:
        rows.append(_line(len(rows), text, raw, bbox, document_ordinal=document_ordinal))

    add("Phân tích dư nợ theo loại hình tiền tệ", "", [20, 20, 500, 42])
    add(current_period, current_period, [580, 50, 680, 72])
    add("31/12/2024", "31/12/2024", [780, 50, 880, 72])
    add("Đơn vị: Triệu VND", "", [580, 75, 880, 97])
    for label, top, current, prior in (
        ("Cho vay khách hàng", 110, "120", "105"),
        ("Bằng VND", 140, "100", "84"),
        ("Bằng ngoại tệ", 170, "20", "21"),
    ):
        add(label, "", [40, top, 360, top + 22])
        add(current, current, [600, top, 660, top + 22])
        add(prior, prior, [800, top, 860, top + 22])
    add(
        "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 01 tháng 7 năm 2024",
        "",
        [40, 210, 550, 232],
    )
    add("5", "5", [800, 210, 860, 232])
    add("Bằng VND", "", [60, 240, 300, 262])
    add("4", "4", [800, 240, 860, 262])
    add("Bằng ngoại tệ", "", [60, 270, 300, 292])
    add("1", "1", [800, 270, 860, 292])
    add("120", "120", [600, 310, 660, 332])
    add("110", "110", [800, 310, 860, 332])
    add("Theo ngành nghề kinh doanh", "", [20, 350, 500, 372])
    return {"lines": rows, "page_sequence": 1, "page_width": 1000}


def _context_page(
    document_ordinal: int,
    page_sequence: int,
    *,
    current_period: str,
) -> dict[str, object]:
    rows = [
        _line(
            0,
            current_period,
            current_period,
            [580, 30, 680, 52],
            document_ordinal=document_ordinal,
            page_sequence=page_sequence,
        ),
        _line(
            1,
            "31/12/2024",
            "31/12/2024",
            [780, 30, 880, 52],
            document_ordinal=document_ordinal,
            page_sequence=page_sequence,
        ),
        _line(
            2,
            "Đơn vị: Triệu VND",
            "",
            [580, 60, 880, 82],
            document_ordinal=document_ordinal,
            page_sequence=page_sequence,
        ),
        _line(
            3,
            "Thuyết minh khác",
            "",
            [20, 100, 500, 122],
            document_ordinal=document_ordinal,
            page_sequence=page_sequence,
        ),
    ]
    return {"lines": rows, "page_sequence": page_sequence, "page_width": 1000}


def _semantic_page(joined: dict[str, object]) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": copy.deepcopy(line["bbox"]),
                "source_line_index": line["line_ordinal"],
                "source_text": line["numeric_recognition"]["raw_prediction"],
                "vietocr_text": line["vietocr_text"],
            }
            for line in joined["lines"]
        ],
        "page_sequence": joined["page_sequence"],
    }


def _packet(document_ordinal: int, *, line_count: int, page_count: int) -> dict[str, object]:
    material = {
        "assurance": "AUDITED",
        "bank_provenance": "SYNTHETIC",
        "document_evidence_root_sha256": f"{document_ordinal + 100:064x}",
        "document_id": f"synthetic-{document_ordinal}",
        "document_ordinal": document_ordinal,
        "line_count": line_count,
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


def _render(image: Image.Image, *, document_ordinal: int) -> dict[str, object]:
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
        "physical_page": 1,
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


def _draw_bounded_candidate(draw: ImageDraw.ImageDraw, bbox: list[int]) -> None:
    """One connected 8x6, 62.5%-fill component: candidate, not direct."""

    center_x = (bbox[0] + bbox[2]) // 2
    center_y = (bbox[1] + bbox[3]) // 2
    left, top = center_x - 4, center_y - 3
    spans = ((2, 5), (1, 6), (0, 7), (0, 7), (2, 3), (2, 3))
    for y, (start, stop) in enumerate(spans):
        draw.line([left + start, top + y, left + stop, top + y], fill="black")


def _inputs(
    document_ordinal: int,
    *,
    candidate_role: str | None = None,
    blank_role: str | None = None,
    current_period: str = "31/12/2025",
):
    joined = _joined_page(document_ordinal, current_period=current_period)
    pages = [
        joined,
        _context_page(document_ordinal, 2, current_period=current_period),
        _context_page(document_ordinal, 3, current_period=current_period),
    ]
    scan = topology_v1.build_accounting_family_topology_scan_v1(
        [_semantic_page(page) for page in pages], graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2
    )
    base = row_axis_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
        pages,
        graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2,
        scan,
        scan["regions"][0],
    )
    blank = Image.new("RGB", (1000, 400), "white")
    blank_render = _render(blank, document_ordinal=document_ordinal)
    proposals = sweep_v1._visible_dash_rescue_inputs(
        joined_pages=pages,
        row_axis=base,
        render_snapshots=(blank_render,),
    )
    image = Image.new("RGB", (1000, 400), "white")
    draw = ImageDraw.Draw(image)
    for proposal in proposals:
        role = proposal["role"]
        if role == blank_role:
            continue
        if role == candidate_role:
            _draw_bounded_candidate(draw, proposal["region"]["proposed_raw_pixel_bbox"])
        else:
            _draw_direct(draw, proposal["region"]["proposed_raw_pixel_bbox"])
    render = _render(image, document_ordinal=document_ordinal)
    packet = _packet(
        document_ordinal,
        line_count=sum(len(page["lines"]) for page in pages),
        page_count=len(pages),
    )
    return base, scan, pages, (render,), packet


def _overlay(inputs):
    result = subject.build_loan_currency_visible_dash_evidence_v1(*inputs)
    subject.validate_loan_currency_visible_dash_evidence_replay_v1(result, *inputs)
    return result


def _rehash_overlay(value: dict[str, object]) -> None:
    material = copy.deepcopy(value)
    material.pop("evidence_id")
    value["evidence_id"] = "lcdashv1:evidence:" + canonical_json_sha256_v1(material)


def test_direct_overlay_replays_exact_crops_and_exposes_numeric_bindings() -> None:
    inputs = _inputs(1)
    result = _overlay(inputs)

    assert result["status"] == "AUTHENTICATED_VISIBLE_DASH_CELLS_BOUND"
    assert len(result["rescue_cells"]) == 3
    assert {cell["admission_class"] for cell in result["rescue_cells"]} == {
        "DIRECT_VISIBLE_HORIZONTAL_DASH"
    }
    bindings = subject.read_loan_currency_visible_dash_numeric_bindings_v1(result, *inputs)
    assert len(bindings) == 3
    assert all(item["crop_png_bytes"].startswith(b"\x89PNG") for item in bindings)


def test_bounded_candidate_retains_raw_class_and_needs_unique_direct_peer() -> None:
    candidate_inputs = _inputs(1, candidate_role="DEFERRED_LC_FOREIGN")
    peer_inputs = _inputs(2)
    candidate = _overlay(candidate_inputs)
    peer = _overlay(peer_inputs)

    candidate_cell = next(
        cell for cell in candidate["rescue_cells"] if cell["role"] == "DEFERRED_LC_FOREIGN"
    )
    assert candidate["status"] == ("AUTHENTICATED_DIRECT_AND_BOUNDED_CANDIDATE_CELLS_BOUND")
    assert candidate_cell["classification"] == "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE"
    assert candidate_cell["injected_value_sample_id"] is None
    pairs = subject.build_loan_currency_bounded_dash_peer_bindings_v1([candidate, peer])
    assert len(pairs) == 1
    assert pairs[0]["candidate_cell_id"] == candidate_cell["cell_id"]
    assert pairs[0]["peer_raw_classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"

    with pytest.raises(subject.LoanCurrencyVisibleDashEvidenceV1Error):
        subject.build_loan_currency_bounded_dash_peer_bindings_v1([candidate])
    duplicate_peer = _overlay(_inputs(3))
    with pytest.raises(subject.LoanCurrencyVisibleDashEvidenceV1Error):
        subject.build_loan_currency_bounded_dash_peer_bindings_v1([candidate, peer, duplicate_peer])


def test_blank_crop_never_becomes_zero() -> None:
    inputs = _inputs(1, blank_role="DEFERRED_LC_FOREIGN")
    result = _overlay(inputs)

    cell = next(cell for cell in result["rescue_cells"] if cell["role"] == "DEFERRED_LC_FOREIGN")
    assert result["status"] == "UNRESOLVED_PIXEL_GLYPH_OR_ROW_AXIS"
    assert cell["classification"] == "UNRESOLVED_NOT_ONE_DASH_GLYPH"
    assert cell["admission_class"] == "UNRESOLVED_PIXEL_GLYPH"
    with pytest.raises(subject.LoanCurrencyVisibleDashEvidenceV1Error):
        subject.read_loan_currency_visible_dash_numeric_bindings_v1(result, *inputs)


def test_self_rehashed_document_mutation_still_fails_exact_replay() -> None:
    inputs = _inputs(1)
    result = _overlay(inputs)
    forged = copy.deepcopy(result)
    forged["document_binding"]["source_pdf_ref"]["path"] = "opaque/forged.pdf"
    _rehash_overlay(forged)

    subject.validate_loan_currency_visible_dash_evidence_v1(forged)
    with pytest.raises(subject.LoanCurrencyVisibleDashEvidenceV1Error):
        subject.validate_loan_currency_visible_dash_evidence_replay_v1(forged, *inputs)


@pytest.mark.parametrize(
    "mutation",
    ("role", "lane", "period", "packet", "region", "crop"),
)
def test_role_lane_period_packet_region_or_crop_swap_fails_exact_replay(mutation: str) -> None:
    inputs = _inputs(
        1,
        candidate_role="DEFERRED_LC_FOREIGN" if mutation == "crop" else None,
    )
    result = _overlay(inputs)
    forged = copy.deepcopy(result)
    first, second = forged["rescue_cells"][:2]
    if mutation == "role":
        first["role"] = second["role"]
    elif mutation == "lane":
        first["column_ordinal"] = 1
    elif mutation == "period":
        first["resolved_period"] = "31/12/2024"
    elif mutation == "packet":
        forged["document_binding"]["packet_id"] = "ffdesv1:document:" + "0" * 64
    elif mutation == "region":
        first["region_id"], second["region_id"] = second["region_id"], first["region_id"]
    else:
        candidate = forged["rescue_cells"][-1]
        first["region_png_ref"], candidate["region_png_ref"] = (
            candidate["region_png_ref"],
            first["region_png_ref"],
        )
    _rehash_overlay(forged)

    with pytest.raises(subject.LoanCurrencyVisibleDashEvidenceV1Error):
        subject.validate_loan_currency_visible_dash_evidence_replay_v1(forged, *inputs)


@pytest.mark.parametrize("field", ("page_sequence", "column_ordinal"))
def test_bool_is_not_an_integer_axis_coordinate(field: str) -> None:
    inputs = _inputs(1)
    forged = copy.deepcopy(_overlay(inputs))
    forged["rescue_cells"][0][field] = True
    _rehash_overlay(forged)

    with pytest.raises(subject.LoanCurrencyVisibleDashEvidenceV1Error):
        subject.validate_loan_currency_visible_dash_evidence_v1(forged)


@pytest.mark.parametrize(
    "metrics",
    (
        {"component_count": 0},
        {"component_count": 2},
        {
            "component_count": 1,
            "component_aspect_ratio": 0.25,
            "component_height_ratio": 0.25,
            "component_width_ratio": 0.06,
            "ink_fill_ratio": 1.0,
            "horizontal_center_displacement_ratio": 0.0,
            "vertical_center_displacement_ratio": 0.0,
        },
        {
            "component_count": 1,
            "component_aspect_ratio": 1.0,
            "component_height_ratio": 0.20,
            "component_width_ratio": 0.20,
            "ink_fill_ratio": 1.0,
            "horizontal_center_displacement_ratio": 0.0,
            "vertical_center_displacement_ratio": 0.0,
        },
        {
            "component_count": 1,
            "component_aspect_ratio": 0.8,
            "component_height_ratio": 0.25,
            "component_width_ratio": 0.20,
            "ink_fill_ratio": 0.7,
            "horizontal_center_displacement_ratio": 0.0,
            "vertical_center_displacement_ratio": 0.0,
        },
        {
            "component_count": 1,
            "component_aspect_ratio": 10.0,
            "component_height_ratio": 0.10,
            "component_width_ratio": 0.80,
            "ink_fill_ratio": 1.0,
            "horizontal_center_displacement_ratio": 0.0,
            "vertical_center_displacement_ratio": 0.0,
        },
        {
            "component_count": 1,
            "component_aspect_ratio": 1.5,
            "component_height_ratio": 0.20,
            "component_width_ratio": 0.20,
            "ink_fill_ratio": 0.7,
            "horizontal_center_displacement_ratio": 0.20,
            "vertical_center_displacement_ratio": 0.0,
        },
    ),
)
def test_blank_multi_digit_dot_comma_rule_or_off_center_is_not_bounded_candidate(
    metrics: dict[str, object],
) -> None:
    assert not subject._bounded_high_fill_candidate({"glyph_metrics": metrics})
