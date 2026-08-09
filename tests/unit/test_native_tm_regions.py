from __future__ import annotations

from collections import Counter
from pathlib import Path

import fitz
import pytest
import yaml

from bctc_ai.core.contracts import BoundingBox, ObservationKind, RowType
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.ocr.native_text_quality_v2 import load_native_text_quality_v2_config
from bctc_ai.ocr.pdf_text import PDFTextPage, PDFWord
from bctc_ai.tables.geometry import build_text_runs, load_geometry_config
from bctc_ai.tables.native_tm_regions import (
    NativeTMRegionError,
    discover_native_tm_regions,
    extract_visible_native_text_page,
    load_native_tm_region_policy,
    resolve_region_blank_slots,
)

_POLICY_RELATIVE_PATH = Path("config/tables/native-tm-regions-v1.yaml")
_GEOMETRY_RELATIVE_PATH = Path("config/tables/geometry-v2.yaml")
_QUALITY_RELATIVE_PATH = Path("config/ocr/native-text-quality-v2.yaml")
_VPB_SOURCE_RELATIVE_PATH = Path("vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf")
_VPB_SOURCE_SHA256 = "614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde"


def _word(
    text: str,
    *,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    line: int,
    number: int = 0,
) -> PDFWord:
    return PDFWord(
        raw_text=text,
        normalized_text=normalize_text(text),
        bbox_points=BoundingBox(x0, y0, x1, y1),
        block_number=0,
        line_number=line,
        word_number=number,
    )


def _page(page: int, words: list[PDFWord]) -> PDFTextPage:
    return PDFTextPage(
        page=page,
        width_points=600,
        height_points=800,
        rotation=0,
        words=words,
        text_quality="USABLE_TEXT_LAYER",
        corruption_markers=(),
    )


def _two_local_table_page(page_number: int) -> PDFTextPage:
    words = [
        _word("Thuyết minh định lượng", x0=40, y0=35, x1=220, y1=45, line=0),
        # First table: one local date/unit/value axis.
        _word("31/03/2026", x0=480, y0=80, x1=540, y1=90, line=1),
        _word("Triệu đồng", x0=470, y0=100, x1=540, y1=110, line=2),
        _word("Khoản mục một", x0=50, y0=130, x1=250, y1=140, line=3),
        _word("1.000", x0=490, y0=130, x1=540, y1=140, line=3, number=1),
        _word("Khoản mục gạch", x0=50, y0=150, x1=250, y1=160, line=4),
        _word("-", x0=490, y0=150, x1=540, y1=160, line=4, number=1),
        _word("Khoản mục không", x0=50, y0=170, x1=250, y1=180, line=5),
        _word("0", x0=490, y0=170, x1=540, y1=180, line=5, number=1),
        # Both records are inside the local region. The first is an explicit
        # row outside financial_table_span; the second cannot be assigned to a
        # row or value axis and must remain explicit unassigned evidence.
        _word("Diễn giải sau bảng", x0=50, y0=220, x1=250, y1=230, line=6),
        _word("Chú thích lề", x0=560, y0=235, x1=595, y1=245, line=7),
        # Second table: its own two dates, two units, and two value axes.
        _word("31/03/2026", x0=380, y0=300, x1=440, y1=310, line=8),
        _word("31/12/2025", x0=490, y0=300, x1=550, y1=310, line=8, number=1),
        _word("Triệu đồng", x0=370, y0=320, x1=440, y1=330, line=9),
        _word("Triệu đồng", x0=480, y0=320, x1=550, y1=330, line=9, number=1),
        _word("Khoản mục hai", x0=50, y0=350, x1=260, y1=360, line=10),
        _word("2.000", x0=390, y0=350, x1=440, y1=360, line=10, number=1),
        _word("1.500", x0=500, y0=350, x1=550, y1=360, line=10, number=2),
        _word("Khoản mục ba", x0=50, y0=370, x1=260, y1=380, line=11),
        _word("30", x0=390, y0=370, x1=440, y1=380, line=11, number=1),
        _word("20", x0=500, y0=370, x1=550, y1=380, line=11, number=2),
    ]
    return _page(page_number, words)


def _mixed_amount_percentage_page(page_number: int = 1) -> PDFTextPage:
    """Four stable axes: percentage, amount, percentage, amount.

    Only the two amount axes expose exact source-visible unit headers. Each
    percentage cluster still has two observations and is locally adjacent to a
    unit-anchored amount cluster. Two source-empty cells exercise the expected
    grid without pretending native-text absence is already BLANK.
    """

    words = [
        _word("%", x0=305, y0=80, x1=330, y1=90, line=0),
        _word("%", x0=465, y0=80, x1=490, y1=90, line=0, number=1),
        _word("31/03/2026", x0=350, y0=80, x1=410, y1=90, line=1),
        _word("31/12/2025", x0=510, y0=80, x1=570, y1=90, line=1, number=1),
        _word("Triệu đồng", x0=340, y0=100, x1=410, y1=110, line=2),
        _word("Triệu đồng", x0=500, y0=100, x1=570, y1=110, line=2, number=1),
        _word("Dòng đầy đủ", x0=50, y0=130, x1=230, y1=140, line=3),
        _word("10", x0=290, y0=130, x1=330, y1=140, line=3, number=1),
        _word("1.000", x0=360, y0=130, x1=410, y1=140, line=3, number=2),
        _word("5", x0=450, y0=130, x1=490, y1=140, line=3, number=3),
        _word("2.000", x0=520, y0=130, x1=570, y1=140, line=3, number=4),
        # The first percentage slot is source-empty.
        _word("Dòng thiếu trái", x0=50, y0=150, x1=230, y1=160, line=4),
        _word("1.100", x0=360, y0=150, x1=410, y1=160, line=4, number=1),
        _word("6", x0=450, y0=150, x1=490, y1=160, line=4, number=2),
        _word("2.100", x0=520, y0=150, x1=570, y1=160, line=4, number=3),
        # The second percentage slot is source-empty.
        _word("Dòng thiếu phải", x0=50, y0=170, x1=230, y1=180, line=5),
        _word("12", x0=290, y0=170, x1=330, y1=180, line=5, number=1),
        _word("1.200", x0=360, y0=170, x1=410, y1=180, line=5, number=2),
        _word("2.200", x0=520, y0=170, x1=570, y1=180, line=5, number=3),
    ]
    return _page(page_number, words)


def _two_axis_amount_percentage_page(page_number: int = 1) -> PDFTextPage:
    """A local percentage label governs only its own axis, not the table."""

    return _page(
        page_number,
        [
            _word("31/03/2026", x0=330, y0=70, x1=400, y1=80, line=0),
            _word("Triệu đồng", x0=330, y0=90, x1=400, y1=100, line=1),
            _word("Tỷ lệ (%)", x0=420, y0=90, x1=470, y1=100, line=2),
            _word("Dòng một", x0=50, y0=120, x1=180, y1=130, line=3),
            _word("100", x0=360, y0=120, x1=400, y1=130, line=3, number=1),
            _word("10", x0=440, y0=120, x1=470, y1=130, line=3, number=2),
            _word("Dòng hai", x0=50, y0=140, x1=180, y1=150, line=4),
            _word("200", x0=360, y0=140, x1=400, y1=150, line=4, number=1),
            _word("20", x0=440, y0=140, x1=470, y1=150, line=4, number=2),
        ],
    )


def _translated_two_axis_page(horizontal_shift: float) -> PDFTextPage:
    def shifted(
        text: str,
        *,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        line: int,
        number: int = 0,
    ) -> PDFWord:
        return _word(
            text,
            x0=x0 + horizontal_shift,
            y0=y0,
            x1=x1 + horizontal_shift,
            y1=y1,
            line=line,
            number=number,
        )

    return _page(
        1,
        [
            shifted("Triệu đồng", x0=170, y0=80, x1=240, y1=90, line=0),
            shifted("Dòng một", x0=20, y0=120, x1=120, y1=130, line=1),
            shifted("100", x0=200, y0=120, x1=240, y1=130, line=1, number=1),
            shifted("10", x0=270, y0=120, x1=310, y1=130, line=1, number=2),
            shifted("Dòng hai", x0=20, y0=140, x1=120, y1=150, line=2),
            shifted("200", x0=200, y0=140, x1=240, y1=150, line=2, number=1),
            shifted("20", x0=270, y0=140, x1=310, y1=150, line=2, number=2),
        ],
    )


def _load_configs(project_root: Path):
    return (
        load_native_tm_region_policy(project_root / _POLICY_RELATIVE_PATH),
        load_geometry_config(project_root / _GEOMETRY_RELATIVE_PATH),
        load_native_text_quality_v2_config(project_root / _QUALITY_RELATIVE_PATH),
    )


def _discover_vpb_pages(project_root: Path, page_numbers: tuple[int, ...]):
    policy, geometry, quality = _load_configs(project_root)
    source = project_root / _VPB_SOURCE_RELATIVE_PATH
    assert source.is_file()
    assert sha256_file(source) == _VPB_SOURCE_SHA256
    results = {}
    with fitz.open(source) as document:
        for page_number in page_numbers:
            visible = extract_visible_native_text_page(
                document[page_number - 1],
                policy,
                native_text_quality_config=quality,
            )
            results[page_number] = discover_native_tm_regions(
                visible.page,
                geometry_config=geometry,
                policy=policy,
                table_id_prefix=f"source-{_VPB_SOURCE_SHA256[:16]}",
                excluded_spans=visible.excluded_spans,
            )
    return results


def _is_visible_tm_page(page: PDFTextPage) -> bool:
    source_header = " ".join(
        word.normalized_text
        for word in page.words
        if word.bbox_points.y0 < page.height_points * 0.20
    )
    return "thuyet minh bao cao tai chinh" in retrieval_key(source_header)


@pytest.mark.parametrize(
    "forbidden_key",
    (
        "bank",
        "page_number",
        "expected_row_count",
        "expected_cell_count",
        "schema_label",
        "reportnorm_id",
    ),
)
def test_policy_rejects_bank_page_count_and_schema_specific_keys(
    project_root: Path,
    tmp_path: Path,
    forbidden_key: str,
):
    source = project_root / _POLICY_RELATIVE_PATH
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["forbidden_test_injection"] = {forbidden_key: "must-not-be-used"}
    candidate = tmp_path / f"policy-{forbidden_key}.yaml"
    candidate.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")

    with pytest.raises(NativeTMRegionError, match="document/schema specific"):
        load_native_tm_region_policy(candidate)


@pytest.mark.parametrize(
    ("section", "key"),
    (
        ("acceptance", "require_every_distinct_unit_axis_observed"),
        ("geometry", "preserve_rows_outside_financial_span"),
        ("geometry", "preserve_unassigned_runs"),
        ("visibility", "exclude_fully_transparent_text_paints"),
        ("visibility", "require_causal_visibility_for_nonopaque_text"),
    ),
)
def test_policy_rejects_disabled_source_completeness_gates(
    project_root: Path,
    tmp_path: Path,
    section: str,
    key: str,
):
    payload = yaml.safe_load((project_root / _POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    payload[section][key] = False
    candidate = tmp_path / f"policy-{key}.yaml"
    candidate.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")

    with pytest.raises(NativeTMRegionError):
        load_native_tm_region_policy(candidate)


def test_policy_rejects_unknown_routing_metadata(project_root: Path, tmp_path: Path):
    payload = yaml.safe_load((project_root / _POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    payload["routing"] = {
        "institution": "VPB",
        "pages": [38],
        "row_count": 694,
        "schema_route": "TM",
    }
    candidate = tmp_path / "policy-routing.yaml"
    candidate.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")

    with pytest.raises(NativeTMRegionError, match="policy fields are invalid"):
        load_native_tm_region_policy(candidate)


@pytest.mark.parametrize("invalid_value", (float("nan"), float("inf")))
def test_policy_rejects_non_finite_thresholds(
    project_root: Path,
    tmp_path: Path,
    invalid_value: float,
):
    payload = yaml.safe_load((project_root / _POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    payload["acceptance"]["axis_alignment_tolerance_multiplier"] = invalid_value
    candidate = tmp_path / "policy-non-finite.yaml"
    candidate.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")

    with pytest.raises(NativeTMRegionError, match="positive number"):
        load_native_tm_region_policy(candidate)


@pytest.mark.parametrize(
    ("key", "weakened_value"),
    [
        ("near_white_channel_minimum", 0),
        ("raster_scale", 0.01),
        ("minimum_visible_contrast", 255),
        ("minimum_causal_contribution_ratio", 0.1),
        ("minimum_glyph_core_alpha", 1),
        ("relative_glyph_core_alpha", 0.1),
        ("minimum_glyph_core_survival_ratio", 0.1),
        ("blank_slot_inset_ratio", 0.44),
    ],
)
def test_policy_pins_every_claim_critical_visibility_threshold(
    project_root: Path,
    tmp_path: Path,
    key: str,
    weakened_value: float,
):
    payload = yaml.safe_load((project_root / _POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    payload["visibility"][key] = weakened_value
    candidate = tmp_path / f"policy-weakened-{key}.yaml"
    candidate.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")

    with pytest.raises(NativeTMRegionError, match="causal visibility gate is invalid"):
        load_native_tm_region_policy(candidate)


def test_policy_rejects_arbitrary_non_unit_header_key(project_root: Path, tmp_path: Path):
    payload = yaml.safe_load((project_root / _POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    payload["unit_headers"]["exact_retrieval_keys"] = ["foo"]
    candidate = tmp_path / "policy-fake-unit.yaml"
    candidate.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")

    with pytest.raises(NativeTMRegionError, match="unit-header keys are invalid"):
        load_native_tm_region_policy(candidate)


def test_two_tables_use_local_axes_headers_and_rows_without_page_or_count_rules(
    project_root: Path,
):
    policy, geometry, _ = _load_configs(project_root)

    first = discover_native_tm_regions(
        _two_local_table_page(7),
        geometry_config=geometry,
        policy=policy,
        table_id_prefix="synthetic-source",
    )
    renumbered = discover_native_tm_regions(
        _two_local_table_page(917),
        geometry_config=geometry,
        policy=policy,
        table_id_prefix="synthetic-source",
    )

    assert len(first.regions) == len(renumbered.regions) == 2
    assert [len(region.geometry.axes) for region in first.regions] == [1, 2]
    assert [region.value_bearing_row_count for region in first.regions] == [3, 2]
    assert [region.visible_cell_count for region in first.regions] == [3, 4]
    assert [
        tuple(binding.period_end.isoformat() for binding in region.header_bindings)
        for region in first.regions
    ] == [("2026-03-31",), ("2026-03-31", "2025-12-31")]
    assert all(
        binding.unit == "VND" and binding.unit_multiplier == 1_000_000
        for region in first.regions
        for binding in region.header_bindings
    )
    assert [
        (region.value_bearing_row_count, region.visible_cell_count) for region in renumbered.regions
    ] == [(3, 3), (2, 4)]


def test_stable_percentage_axes_are_kept_next_to_unit_anchored_amount_axes(
    project_root: Path,
):
    policy, geometry, _ = _load_configs(project_root)

    result = discover_native_tm_regions(
        _mixed_amount_percentage_page(),
        geometry_config=geometry,
        policy=policy,
        table_id_prefix="synthetic-mixed-axis",
    )

    assert len(result.regions) == 1
    region = result.regions[0]
    assert len(region.geometry.unit_run_ids) == 2
    assert len(region.geometry.axes) == 4
    assert [axis.sample_count for axis in region.geometry.axes] == [2, 3, 2, 3]
    assert [axis.source for axis in region.geometry.axes] == [
        "stable-local-numeric-cluster-adjacent-to-unit-anchored-axes",
        "source-visible-exact-unit-header+local-numeric-cluster",
        "stable-local-numeric-cluster-adjacent-to-unit-anchored-axes",
        "source-visible-exact-unit-header+local-numeric-cluster",
    ]
    assert [binding.raw_header.startswith("%") for binding in region.header_bindings] == [
        True,
        False,
        True,
        False,
    ]
    assert [binding.measure_role for binding in region.header_bindings] == [
        "PERCENTAGE",
        "AMOUNT",
        "PERCENTAGE",
        "AMOUNT",
    ]
    assert [binding.unit for binding in region.header_bindings] == [
        "PERCENT",
        "VND",
        "PERCENT",
        "VND",
    ]
    assert [binding.unit_multiplier for binding in region.header_bindings] == [
        1,
        1_000_000,
        1,
        1_000_000,
    ]
    assert [binding.period_end.isoformat() for binding in region.header_bindings] == [
        "2026-03-31",
        "2026-03-31",
        "2025-12-31",
        "2025-12-31",
    ]
    assert [binding.current_or_comparative for binding in region.header_bindings] == [
        "CURRENT",
        "CURRENT",
        "COMPARATIVE",
        "COMPARATIVE",
    ]
    assert [binding.period_group_id for binding in region.header_bindings] == [
        "period-group-001",
        "period-group-001",
        "period-group-002",
        "period-group-002",
    ]
    assert region.visible_cell_count == 10
    assert region.grid_slot_count == 12
    assert region.unresolved_empty_slot_count == 2


def test_local_percentage_heading_cannot_overwrite_a_sibling_money_axis(project_root: Path):
    policy, geometry, _ = _load_configs(project_root)

    result = discover_native_tm_regions(
        _two_axis_amount_percentage_page(),
        geometry_config=geometry,
        policy=policy,
        table_id_prefix="synthetic-amount-percentage",
    )

    assert len(result.regions) == 1
    bindings = result.regions[0].header_bindings
    assert [binding.measure_role for binding in bindings] == ["AMOUNT", "PERCENTAGE"]
    assert [binding.unit for binding in bindings] == ["VND", "PERCENT"]
    assert [binding.unit_multiplier for binding in bindings] == [1_000_000, 1]
    assert all(not binding.conflicts for binding in bindings)


def test_adjacent_axis_expansion_is_invariant_to_horizontal_translation(
    project_root: Path,
):
    policy, geometry, _ = _load_configs(project_root)
    results = [
        discover_native_tm_regions(
            _translated_two_axis_page(shift),
            geometry_config=geometry,
            policy=policy,
            table_id_prefix=f"synthetic-shift-{int(shift)}",
        )
        for shift in (0.0, 200.0)
    ]

    assert [len(result.regions) for result in results] == [1, 1]
    assert [len(result.regions[0].geometry.axes) for result in results] == [2, 2]
    assert [result.regions[0].visible_cell_count for result in results] == [4, 4]
    assert [
        [axis.sample_count for axis in result.regions[0].geometry.axes] for result in results
    ] == [[2, 2], [2, 2]]


def test_empty_grid_slot_needs_pixel_white_evidence_before_blank_promotion(
    project_root: Path,
    tmp_path: Path,
):
    policy, geometry, _ = _load_configs(project_root)
    result = discover_native_tm_regions(
        _mixed_amount_percentage_page(),
        geometry_config=geometry,
        policy=policy,
        table_id_prefix="synthetic-grid",
    )
    region = result.regions[0]
    unresolved = sorted(
        (slot for slot in region.grid_slots if slot.source_status == "UNRESOLVED_EMPTY_SLOT"),
        key=lambda slot: (slot.row_id, slot.axis_ordinal),
    )
    assert len(unresolved) == 2
    assert all(slot.raw_text is None and slot.source_run_id is None for slot in unresolved)

    blank_slot, marked_slot = unresolved
    marked_box = marked_slot.grid_slot_bbox
    mark_x = (marked_box.x0 + marked_box.x1) / 2
    mark_y = (marked_box.y0 + marked_box.y1) / 2
    pdf_path = tmp_path / "grid-slot-pixels.pdf"
    document = fitz.open()
    page = document.new_page(width=600, height=800)
    page.draw_rect(
        fitz.Rect(mark_x - 2, mark_y - 2, mark_x + 2, mark_y + 2),
        color=(0, 0, 0),
        fill=(0, 0, 0),
    )
    document.save(pdf_path)
    document.close()

    with fitz.open(pdf_path) as reopened:
        resolved = resolve_region_blank_slots(reopened[0], region, policy)

    status_by_slot = {
        (slot.row_id, slot.axis_id): slot.source_status for slot in resolved.grid_slots
    }
    assert status_by_slot[(blank_slot.row_id, blank_slot.axis_id)] == "BLANK"
    assert status_by_slot[(marked_slot.row_id, marked_slot.axis_id)] == "UNRESOLVED_EMPTY_SLOT"
    assert any(
        "BLANK is proven" in evidence
        for evidence in next(
            slot
            for slot in resolved.grid_slots
            if (slot.row_id, slot.axis_id) == (blank_slot.row_id, blank_slot.axis_id)
        ).evidence
    )
    assert any(
        "not proven source-white" in evidence
        for evidence in next(
            slot
            for slot in resolved.grid_slots
            if (slot.row_id, slot.axis_id) == (marked_slot.row_id, marked_slot.axis_id)
        ).evidence
    )


@pytest.mark.parametrize("fill", [(0, 0, 0), (1, 0, 0), (0, 0.5, 0)])
def test_uniform_dark_or_colored_grid_slot_is_never_promoted_to_blank(
    project_root: Path,
    fill: tuple[float, float, float],
):
    policy, geometry, _ = _load_configs(project_root)
    region = discover_native_tm_regions(
        _mixed_amount_percentage_page(),
        geometry_config=geometry,
        policy=policy,
        table_id_prefix="synthetic-solid-slot",
    ).regions[0]
    target = next(
        slot for slot in region.grid_slots if slot.source_status == "UNRESOLVED_EMPTY_SLOT"
    )
    document = fitz.open()
    page = document.new_page(width=600, height=800)
    target_bbox = target.grid_slot_bbox
    page.draw_rect(
        fitz.Rect(target_bbox.x0, target_bbox.y0, target_bbox.x1, target_bbox.y1),
        color=fill,
        fill=fill,
    )

    resolved = resolve_region_blank_slots(page, region, policy)
    document.close()

    resolved_target = next(
        slot
        for slot in resolved.grid_slots
        if slot.axis_id == target.axis_id and slot.row_id == target.row_id
    )
    assert resolved_target.source_status == "UNRESOLVED_EMPTY_SLOT"
    assert "not proven source-white" in resolved_target.evidence[-1]


def test_dash_zero_outside_rows_and_unassigned_runs_are_preserved(project_root: Path):
    policy, geometry, _ = _load_configs(project_root)
    result = discover_native_tm_regions(
        _two_local_table_page(23),
        geometry_config=geometry,
        policy=policy,
        table_id_prefix="synthetic-source",
    )

    first = result.regions[0]
    observations = [cell.parsed.observation for row in first.rows for cell in row.cells]
    values = [cell.parsed.value for row in first.rows for cell in row.cells]
    assert observations == [
        ObservationKind.VALUE,
        ObservationKind.DASH,
        ObservationKind.ZERO,
    ]
    assert values[0] is not None
    assert values[1] is None
    assert values[2] == 0
    assert first.outside_financial_span_rows == ()
    assert len(result.inter_table_contexts) == 1
    assert [run.raw_text for run in result.inter_table_contexts[0].runs] == ["Diễn giải sau bảng"]
    assert result.inter_table_contexts[0].ownership_status == ("UNRESOLVED_INTER_TABLE_OWNERSHIP")
    assert [run.raw_text for run in first.unassigned_runs] == ["Chú thích lề"]


def test_false_unit_like_prose_is_rejected_and_fully_unassigned(project_root: Path):
    policy, geometry, _ = _load_configs(project_root)
    page = _page(
        14,
        [
            _word("Thuyết minh bằng lời", x0=40, y0=60, x1=220, y1=70, line=0),
            _word("Triệu đồng", x0=190, y0=100, x1=260, y1=110, line=1),
            _word("100", x0=220, y0=140, x1=260, y1=150, line=2),
            _word("không tạo thành bảng", x0=40, y0=165, x1=220, y1=175, line=3),
        ],
    )

    result = discover_native_tm_regions(
        page,
        geometry_config=geometry,
        policy=policy,
        table_id_prefix="synthetic-source",
    )

    expected_runs = build_text_runs(
        page.words,
        gap_height_factor=geometry.run_separation_gap_height_factor,
        financial_gap_height_factor=geometry.financial_token_separation_gap_height_factor,
    )
    assert result.regions == ()
    assert len(result.unit_group_diagnostics) == 1
    assert result.unit_group_diagnostics[0].accepted is False
    assert "lacks repeated aligned observations" in result.unit_group_diagnostics[0].reason
    assert result.unassigned_page_runs == tuple(expected_runs)


def test_contract_word_cannot_turn_a_dated_row_into_a_money_scalar(project_root: Path):
    policy, geometry, _ = _load_configs(project_root)
    page = _page(
        16,
        [
            _word("31/03/2026", x0=370, y0=70, x1=430, y1=80, line=0),
            _word("31/12/2025", x0=490, y0=70, x1=550, y1=80, line=0, number=1),
            _word("Triệu đồng", x0=360, y0=90, x1=430, y1=100, line=1),
            _word("Triệu đồng", x0=480, y0=90, x1=550, y1=100, line=1, number=1),
            _word("Dòng một", x0=50, y0=120, x1=200, y1=130, line=2),
            _word("100", x0=390, y0=120, x1=430, y1=130, line=2, number=1),
            _word("200", x0=510, y0=120, x1=550, y1=130, line=2, number=2),
            _word("Dòng hai", x0=50, y0=140, x1=200, y1=150, line=3),
            _word("110", x0=390, y0=140, x1=430, y1=150, line=3, number=1),
            _word("210", x0=510, y0=140, x1=550, y1=150, line=3, number=2),
            _word("Tại ngày 31/03/2026", x0=50, y0=170, x1=230, y1=180, line=4),
            _word("999", x0=390, y0=170, x1=430, y1=180, line=4, number=1),
            _word("hợp đồng", x0=460, y0=170, x1=520, y1=180, line=4, number=2),
        ],
    )

    result = discover_native_tm_regions(
        page,
        geometry_config=geometry,
        policy=policy,
        table_id_prefix="synthetic-contract-prose",
    )

    assert len(result.regions) == 1
    region = result.regions[0]
    assert region.scalar_disclosures == ()
    assert [(row.label, len(row.cells)) for row in region.rows][-1] == (
        "Tại ngày 31/03/2026",
        1,
    )
    assert [run.raw_text for run in region.unassigned_runs] == ["hợp đồng"]


def test_narrative_page_has_no_regions_and_all_runs_remain_unassigned(project_root: Path):
    policy, geometry, _ = _load_configs(project_root)
    page = _page(
        15,
        [
            _word("Chính sách kế toán", x0=40, y0=60, x1=220, y1=70, line=0),
            _word(
                "Các khoản mục được ghi nhận theo quy định.", x0=40, y0=90, x1=360, y1=100, line=1
            ),
            _word(
                "Không có bảng định lượng trên trang này.", x0=40, y0=120, x1=350, y1=130, line=2
            ),
        ],
    )

    result = discover_native_tm_regions(
        page,
        geometry_config=geometry,
        policy=policy,
        table_id_prefix="synthetic-source",
    )
    expected_runs = build_text_runs(
        page.words,
        gap_height_factor=geometry.run_separation_gap_height_factor,
        financial_gap_height_factor=geometry.financial_token_separation_gap_height_factor,
    )

    assert result.regions == ()
    assert result.unit_group_diagnostics == ()
    assert result.unassigned_page_runs == tuple(expected_runs)


def test_source_invisible_white_ghost_is_excluded_but_white_on_dark_is_retained(
    project_root: Path,
    tmp_path: Path,
):
    policy, _, quality = _load_configs(project_root)
    pdf_path = tmp_path / "native-visibility.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((20, 35), "VISIBLE BLACK", color=(0, 0, 0))
    page.insert_text((20, 70), "WHITE GHOST", color=(1, 1, 1))
    page.draw_rect(
        fitz.Rect(15, 90, 180, 130),
        color=(0, 0, 0),
        fill=(0, 0, 0),
    )
    page.insert_text((20, 115), "WHITE ON DARK", color=(1, 1, 1))
    document.save(pdf_path)
    document.close()

    with fitz.open(pdf_path) as reopened:
        visible = extract_visible_native_text_page(
            reopened[0],
            policy,
            native_text_quality_config=quality,
        )

    visible_words = [word.raw_text for word in visible.page.words]
    assert "VISIBLE" in visible_words
    assert "BLACK" in visible_words
    assert "DARK" in visible_words
    assert "GHOST" not in visible_words
    assert any(span.raw_text == "WHITE GHOST" for span in visible.excluded_spans)
    assert all(span.raw_text != "WHITE ON DARK" for span in visible.excluded_spans)


@pytest.mark.parametrize(
    ("color", "opacity"),
    [
        ((0.8, 0.8, 0.8), 1.0),
        ((0.95, 0.95, 0.95), 1.0),
        ((0.0, 0.0, 0.0), 0.1),
        ((0.0, 0.0, 0.0), 0.5),
    ],
)
def test_causal_rgb_preserves_visible_low_contrast_and_nonopaque_text(
    project_root: Path,
    color: tuple[float, float, float],
    opacity: float,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "VISIBLE", color=color, fill_opacity=opacity)

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert [word.raw_text for word in visible.page.words] == ["VISIBLE"]
    assert visible.excluded_spans == ()


def test_causal_rgb_preserves_equal_luminance_chromatic_text(project_root: Path):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.draw_rect(page.rect, color=(0, 0.5, 0), fill=(0, 0.5, 0))
    page.insert_text((100, 100), "REDTEXT", color=(1, 0, 0))

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert [word.raw_text for word in visible.page.words] == ["REDTEXT"]
    assert visible.excluded_spans == ()


def test_non_normal_text_blend_is_unresolved_not_silently_excluded(project_root: Path):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=200, height=100)
    page.draw_rect(page.rect, color=(0.8, 0.8, 0.8), fill=(0.8, 0.8, 0.8))
    page.insert_text((20, 50), "DIFF", color=(1, 1, 1))
    graphics_state_xref = document.get_new_xref()
    document.update_object(
        graphics_state_xref,
        "<< /Type /ExtGState /BM /Difference >>",
    )
    resources_xref = int(document.xref_get_key(page.xref, "Resources")[1].split()[0])
    document.xref_set_key(
        resources_xref,
        "ExtGState/GSdiff",
        f"{graphics_state_xref} 0 R",
    )
    content_xref = page.get_contents()[-1]
    document.update_stream(
        content_xref,
        b"q /GSdiff gs\n" + document.xref_stream(content_xref) + b"\nQ\n",
    )
    page = document.reload_page(page)

    with pytest.raises(NativeTMRegionError, match="glyph color attribution is unresolved"):
        extract_visible_native_text_page(page, policy)
    document.close()


def test_thin_background_stripe_cannot_make_hidden_raw_text_look_visible(
    project_root: Path,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.draw_rect(page.rect, color=(0, 0, 0), fill=(0, 0, 0))
    page.draw_rect(
        fitz.Rect(100, 95.75, 180, 96.25),
        color=(1, 1, 1),
        fill=(1, 1, 1),
    )
    page.insert_text((100, 100), "123456789", color=(0, 0, 0))

    with pytest.raises(
        NativeTMRegionError,
        match="insufficient observable background coverage",
    ):
        extract_visible_native_text_page(page, policy)
    document.close()


def test_active_path_clip_on_text_cannot_leak_the_unclipped_raw_value(
    project_root: Path,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "123.456", color=(0, 0, 0))
    painted = fitz.Rect(page.get_bboxlog()[0][1])
    visible_y0 = painted.y0 + painted.height * 0.40
    visible_y1 = painted.y0 + painted.height * 0.60
    pdf_y = page.rect.height - visible_y1
    clip = (f"q {painted.x0} {pdf_y} {painted.width} {visible_y1 - visible_y0} re W n\n").encode(
        "ascii"
    )
    content_xref = page.get_contents()[-1]
    document.update_stream(
        content_xref,
        clip + document.xref_stream(content_xref) + b"\nQ\n",
    )
    page = document.reload_page(page)

    with pytest.raises(
        NativeTMRegionError,
        match="insufficient observable background coverage|partially source-visible",
    ):
        extract_visible_native_text_page(page, policy)
    document.close()


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_causal_raster_uses_native_coordinates_on_rotated_pages(
    project_root: Path,
    rotation: int,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "VISIBLE", color=(0, 0, 0))
    page.set_rotation(rotation)

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert [word.raw_text for word in visible.page.words] == ["VISIBLE"]
    assert visible.excluded_spans == ()


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_rotated_page_discovery_keeps_native_dimensions_axes_and_cells(
    project_root: Path,
    rotation: int,
):
    policy, geometry, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((217, 50), "VND", fontsize=8)
    page.insert_text((20, 80), "Row one", fontsize=8)
    page.insert_text((220, 80), "100", fontsize=8)
    page.insert_text((264, 80), "10", fontsize=8)
    page.insert_text((20, 100), "Row two", fontsize=8)
    page.insert_text((220, 100), "200", fontsize=8)
    page.insert_text((264, 100), "20", fontsize=8)
    page.set_rotation(rotation)

    visible = extract_visible_native_text_page(page, policy)
    result = discover_native_tm_regions(
        visible.page,
        geometry_config=geometry,
        policy=policy,
        table_id_prefix=f"synthetic-rotation-{rotation}",
        excluded_spans=visible.excluded_spans,
    )
    document.close()

    assert (visible.page.width_points, visible.page.height_points) == (300.0, 200.0)
    assert len(result.regions) == 1
    assert len(result.regions[0].geometry.axes) == 2
    assert result.regions[0].visible_cell_count == 4


@pytest.mark.parametrize("visibility_case", ("LOW_ALPHA_BLACK", "BLACK_ON_BLACK"))
def test_render_invisible_native_table_cannot_become_source_evidence(
    project_root: Path,
    visibility_case: str,
):
    policy, geometry, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    if visibility_case == "BLACK_ON_BLACK":
        page.draw_rect(
            fitz.Rect(0, 0, 300, 190),
            color=(0, 0, 0),
            fill=(0, 0, 0),
        )
    else:
        # These opaque bands create strong bbox contrast unrelated to the 1%-
        # opacity glyphs.  The alpha gate must reject the text independently.
        for y0 in (28, 58, 83):
            page.draw_rect(
                fitz.Rect(0, y0, 300, y0 + 4),
                color=(0, 0, 0),
                fill=(0, 0, 0),
            )
    opacity = 0.01 if visibility_case == "LOW_ALPHA_BLACK" else 1.0
    page.insert_text((220, 35), "VND", color=(0, 0, 0), fill_opacity=opacity)
    page.insert_text((20, 65), "Dòng một", color=(0, 0, 0), fill_opacity=opacity)
    page.insert_text((220, 65), "1.000", color=(0, 0, 0), fill_opacity=opacity)
    page.insert_text((20, 90), "Dòng hai", color=(0, 0, 0), fill_opacity=opacity)
    page.insert_text((220, 90), "2.000", color=(0, 0, 0), fill_opacity=opacity)

    visible = extract_visible_native_text_page(page, policy)
    document.close()
    assert visible.page.words == []
    assert len(visible.excluded_spans) == 5
    with pytest.raises(NativeTMRegionError, match="no usable native text geometry"):
        discover_native_tm_regions(
            visible.page,
            geometry_config=geometry,
            policy=policy,
            table_id_prefix="synthetic-invisible-table",
            excluded_spans=visible.excluded_spans,
        )


def test_later_opaque_render_objects_cannot_hide_native_table_evidence(project_root: Path):
    policy, geometry, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((220, 35), "VND", color=(0, 0, 0))
    page.insert_text((20, 65), "Dòng một", color=(0, 0, 0))
    page.insert_text((220, 65), "1.000", color=(0, 0, 0))
    page.insert_text((20, 90), "Dòng hai", color=(0, 0, 0))
    page.insert_text((220, 90), "2.000", color=(0, 0, 0))
    source_span_boxes = [
        fitz.Rect(entry[1])
        for entry in page.get_bboxlog()
        if entry[0] in {"fill-text", "stroke-text", "ignore-text"}
    ]
    assert len(source_span_boxes) == 5
    for bbox in source_span_boxes:
        page.draw_rect(
            bbox,
            color=(1, 1, 1),
            fill=(0, 0, 0),
            width=1,
        )

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert visible.page.words == []
    assert len(visible.excluded_spans) == 5
    assert all(
        span.reason == "later opaque render object fully covers painted native text"
        and span.occluding_sequence is not None
        and span.occluding_sequence > span.render_sequence
        and span.occluding_object_type == "fill-path"
        for span in visible.excluded_spans
    )
    with pytest.raises(NativeTMRegionError, match="no usable native text geometry"):
        discover_native_tm_regions(
            visible.page,
            geometry_config=geometry,
            policy=policy,
            table_id_prefix="synthetic-occluded-table",
            excluded_spans=visible.excluded_spans,
        )


def test_exact_glyph_bbox_same_color_background_cannot_supply_false_contrast(
    project_root: Path,
):
    policy, _, _ = _load_configs(project_root)
    probe_document = fitz.open()
    probe_page = probe_document.new_page(width=300, height=200)
    probe_page.insert_text((100, 50), "123.456", color=(0, 0, 0))
    painted_bbox = fitz.Rect(probe_page.get_bboxlog()[0][1])
    probe_document.close()

    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.draw_rect(painted_bbox, color=(0, 0, 0), fill=(0, 0, 0))
    page.insert_text((100, 50), "123.456", color=(0, 0, 0))

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert visible.page.words == []
    assert len(visible.excluded_spans) == 1
    assert (
        visible.excluded_spans[0].reason
        == "native glyph paint has no potential source-visible contrast"
    )


def test_final_visible_background_supersedes_an_earlier_same_color_fill(
    project_root: Path,
):
    policy, _, _ = _load_configs(project_root)
    probe_document = fitz.open()
    probe_page = probe_document.new_page(width=300, height=200)
    probe_page.insert_text((100, 50), "VISIBLE", color=(0, 0, 0))
    painted_bbox = fitz.Rect(probe_page.get_bboxlog()[0][1])
    probe_document.close()

    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.draw_rect(painted_bbox, color=(0, 0, 0), fill=(0, 0, 0))
    page.draw_rect(painted_bbox, color=(1, 1, 1), fill=(1, 1, 1))
    page.insert_text((100, 50), "VISIBLE", color=(0, 0, 0))

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert [word.raw_text for word in visible.page.words] == ["VISIBLE"]
    assert visible.excluded_spans == ()


def test_later_visible_replacement_retains_only_the_latest_text_identity(
    project_root: Path,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "1.000", color=(0, 0, 0))
    old_bbox = fitz.Rect(page.get_bboxlog()[0][1])
    page.draw_rect(old_bbox, color=(0, 0, 0), fill=(0, 0, 0))
    page.insert_text((100, 100), "9.999", color=(1, 1, 1))

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert [word.raw_text for word in visible.page.words] == ["9.999"]
    assert len(visible.excluded_spans) == 1
    excluded = visible.excluded_spans[0]
    assert excluded.raw_text == "1.000"
    assert excluded.render_sequence == 0
    assert excluded.occluding_sequence == 1
    assert excluded.occluding_object_type == "fill-path"


def test_mixed_fill_and_stroke_text_colors_are_unresolved(project_root: Path):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.draw_rect(page.rect, color=(0, 0, 0), fill=(0, 0, 0))
    page.insert_text(
        (20, 100),
        "OUTLINE",
        fontsize=30,
        color=(1, 1, 1),
        fill=(0, 0, 0),
        border_width=0.5,
        render_mode=2,
    )

    with pytest.raises(NativeTMRegionError, match="mixed render-event colors"):
        extract_visible_native_text_page(page, policy)
    document.close()


def test_transparent_fill_cannot_hide_visible_stroke_text_identity(project_root: Path):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.draw_rect(page.rect, color=(0, 0, 0), fill=(0, 0, 0))
    page.insert_text(
        (20, 100),
        "OUTLINE",
        fontsize=30,
        color=(1, 1, 1),
        fill=(0, 0, 0),
        border_width=0.5,
        render_mode=2,
        fill_opacity=0,
        stroke_opacity=1,
    )

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert [word.raw_text for word in visible.page.words] == ["OUTLINE"]
    assert visible.excluded_spans == ()


@pytest.mark.parametrize("fill_opacity", [0.01, 0.5])
def test_translucent_rectangle_does_not_occlude_visible_native_text(
    project_root: Path,
    fill_opacity: float,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "VISIBLE", color=(0, 0, 0))
    text_bbox = fitz.Rect(page.get_text("dict")["blocks"][0]["lines"][0]["spans"][0]["bbox"])
    page.draw_rect(
        text_bbox,
        color=(1, 1, 0),
        fill=(1, 1, 0),
        fill_opacity=fill_opacity,
    )

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert [word.raw_text for word in visible.page.words] == ["VISIBLE"]
    assert visible.excluded_spans == ()


@pytest.mark.parametrize("fill_opacity", [0.95, 0.99])
def test_near_opaque_overlay_cannot_supply_false_text_identity(
    project_root: Path,
    fill_opacity: float,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "VISIBLE", color=(0, 0, 0))
    text_bbox = fitz.Rect(page.get_bboxlog()[0][1])
    page.draw_rect(
        text_bbox,
        color=(1, 1, 1),
        fill=(1, 1, 1),
        fill_opacity=fill_opacity,
    )

    with pytest.raises(NativeTMRegionError, match="causally occluded and unresolved"):
        extract_visible_native_text_page(page, policy)
    document.close()


def test_partial_opaque_cover_cannot_claim_full_span_occlusion(project_root: Path):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "VISIBLE", color=(0, 0, 0))
    text_bbox = fitz.Rect(page.get_text("dict")["blocks"][0]["lines"][0]["spans"][0]["bbox"])
    page.draw_rect(
        fitz.Rect(
            text_bbox.x0,
            text_bbox.y0,
            text_bbox.x1 - text_bbox.width * 0.05,
            text_bbox.y1,
        ),
        color=(1, 1, 1),
        fill=(1, 1, 1),
    )

    with pytest.raises(
        NativeTMRegionError,
        match="native text is materially or character-wise occluded and unresolved",
    ):
        extract_visible_native_text_page(page, policy)
    document.close()


@pytest.mark.parametrize("cover_kind", ["THIN_RECTANGLE", "POLYGON", "THICK_STROKE"])
def test_material_mid_glyph_cover_never_leaks_the_full_raw_value(
    project_root: Path,
    cover_kind: str,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "123.456", color=(0, 0, 0))
    painted = fitz.Rect(page.get_bboxlog()[0][1])
    if cover_kind == "THIN_RECTANGLE":
        height = painted.height * 0.08
        page.draw_rect(
            fitz.Rect(
                painted.x0,
                painted.y0 + (painted.height - height) / 2,
                painted.x1,
                painted.y0 + (painted.height + height) / 2,
            ),
            color=(1, 1, 1),
            fill=(1, 1, 1),
        )
    elif cover_kind == "POLYGON":
        y0 = painted.y0 + painted.height * 0.25
        y1 = painted.y0 + painted.height * 0.75
        shape = page.new_shape()
        shape.draw_polyline(
            (
                (painted.x0, y0),
                (painted.x1, y0),
                (painted.x1, y1),
                (painted.x0, y1),
                (painted.x0, y0),
            )
        )
        shape.finish(color=(1, 1, 1), fill=(1, 1, 1))
        shape.commit()
    else:
        page.draw_line(
            (painted.x0, (painted.y0 + painted.y1) / 2),
            (painted.x1, (painted.y0 + painted.y1) / 2),
            color=(1, 1, 1),
            width=painted.height * 0.5,
        )

    with pytest.raises(NativeTMRegionError, match="occluded|partially source-visible"):
        extract_visible_native_text_page(page, policy)
    document.close()


def test_full_first_character_redaction_cannot_leak_the_raw_native_value(
    project_root: Path,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "123.456", color=(0, 0, 0))
    painted_bbox = fitz.Rect(page.get_bboxlog()[0][1])
    first_character_bbox = fitz.Rect(
        page.get_text("rawdict")["blocks"][0]["lines"][0]["spans"][0]["chars"][0]["bbox"]
    )
    character_target = painted_bbox & first_character_bbox
    assert character_target.width / painted_bbox.width < 0.20
    page.draw_rect(character_target, color=(0, 0, 0), fill=(0, 0, 0))

    with pytest.raises(
        NativeTMRegionError,
        match="native text is materially or character-wise occluded and unresolved",
    ):
        extract_visible_native_text_page(page, policy)
    document.close()


def test_full_height_partial_character_strip_cannot_leak_the_raw_native_value(
    project_root: Path,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "123.456", color=(0, 0, 0))
    painted_bbox = fitz.Rect(page.get_bboxlog()[0][1])
    characters = page.get_text("rawdict")["blocks"][0]["lines"][0]["spans"][0]["chars"]
    first = fitz.Rect(characters[0]["bbox"])
    second = fitz.Rect(characters[1]["bbox"])
    redaction = fitz.Rect(
        (first.x0 + first.x1) / 2,
        painted_bbox.y0,
        (second.x0 + second.x1) / 2,
        painted_bbox.y1,
    )
    assert redaction.width / painted_bbox.width < 0.20
    page.draw_rect(redaction, color=(0, 0, 0), fill=(0, 0, 0))

    with pytest.raises(
        NativeTMRegionError,
        match="native text is materially or character-wise occluded and unresolved",
    ):
        extract_visible_native_text_page(page, policy)
    document.close()


def test_clipped_fill_path_cannot_claim_its_unclipped_bbox_as_occlusion(
    project_root: Path,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "VISIBLE", color=(0, 0, 0))
    text_bbox = fitz.Rect(page.get_text("dict")["blocks"][0]["lines"][0]["spans"][0]["bbox"])
    pdf_y = page.rect.height - text_bbox.y1
    clipped_fill = (
        f"q {text_bbox.x0} {pdf_y} {text_bbox.width * 0.25} {text_bbox.height} re W n "
        f"{text_bbox.x0} {pdf_y} {text_bbox.width} {text_bbox.height} re f Q\n"
    ).encode("ascii")
    content_xref = page.get_contents()[-1]
    document.update_stream(
        content_xref,
        document.xref_stream(content_xref) + b"\n" + clipped_fill,
    )
    page = document.reload_page(page)

    with pytest.raises(
        NativeTMRegionError,
        match="native text is materially or character-wise occluded and unresolved",
    ):
        extract_visible_native_text_page(page, policy)
    document.close()


@pytest.mark.parametrize(
    ("alpha", "expected_words", "raises_unresolved"),
    [
        (0, ["VISIBLE"], False),
        (128, [], True),
        (243, [], True),
        (254, [], True),
        (255, [], True),
    ],
)
def test_image_mask_proves_whether_a_later_image_can_occlude_text(
    project_root: Path,
    alpha: int,
    expected_words: list[str],
    raises_unresolved: bool,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "VISIBLE", color=(0, 0, 0))
    text_bbox = fitz.Rect(page.get_text("dict")["blocks"][0]["lines"][0]["spans"][0]["bbox"])
    overlay = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), True)
    assert overlay.set_rect(overlay.irect, (255, 0, 0, alpha)) is True
    page.insert_image(text_bbox, pixmap=overlay)

    if raises_unresolved:
        with pytest.raises(
            NativeTMRegionError,
            match="native text visibility beneath a later image is unresolved",
        ):
            extract_visible_native_text_page(page, policy)
        document.close()
        return
    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert [word.raw_text for word in visible.page.words] == expected_words
    assert visible.excluded_spans == ()


def test_nonrectangular_fill_bbox_does_not_claim_text_outside_the_shape(
    project_root: Path,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((220, 170), "VISIBLE", color=(0, 0, 0))
    shape = page.new_shape()
    shape.draw_polyline(((0, 0), (300, 0), (0, 200), (0, 0)))
    shape.finish(color=(1, 0, 0), fill=(1, 0, 0))
    shape.commit()

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert [word.raw_text for word in visible.page.words] == ["VISIBLE"]
    assert visible.excluded_spans == ()


def test_invisible_overlapping_span_cannot_delete_visible_word_identity(
    project_root: Path,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((20, 70), "WHITE GHOST", color=(1, 1, 1))
    page.insert_text((20, 70), "VISIBLE BLACK", color=(0, 0, 0))

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert [word.raw_text for word in visible.page.words] == ["VISIBLE", "BLACK"]
    assert {span.raw_text for span in visible.excluded_spans} == {"WHITE GHOST"}
    excluded = visible.excluded_spans[0]
    assert (excluded.block_number, excluded.line_number, excluded.span_number) == (0, 0, 0)


def test_any_exact_glyph_core_overlap_has_ambiguous_source_ownership(
    project_root: Path,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text(
        (100, 100),
        "MMMM",
        fontsize=20,
        fontname="helv",
        color=(0, 0, 0),
    )
    page.insert_text(
        (133, 100),
        "WWWW",
        fontsize=20,
        fontname="Times-Roman",
        color=(0, 0, 0),
    )

    with pytest.raises(NativeTMRegionError, match="ambiguous source ownership"):
        extract_visible_native_text_page(page, policy)
    document.close()


def test_mixed_visible_and_invisible_spans_are_rebuilt_from_visible_characters(
    project_root: Path,
):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_htmlbox(
        fitz.Rect(20, 20, 280, 80),
        '<span style="color:#000">REAL</span><span style="color:#fff">GHOST</span>',
    )

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert [word.raw_text for word in visible.page.words] == ["REAL"]
    assert {span.raw_text for span in visible.excluded_spans} == {"GHOST"}


def test_combining_mark_mismatch_cannot_leak_an_invisible_span(project_root: Path):
    policy, _, _ = _load_configs(project_root)
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_htmlbox(
        fitz.Rect(20, 20, 280, 80),
        '<span style="color:#000">REAL</span><span style="color:#fff">GHOSTe\u0301</span>',
    )

    visible = extract_visible_native_text_page(page, policy)
    document.close()

    assert [word.raw_text for word in visible.page.words] == ["REAL"]
    assert {span.raw_text for span in visible.excluded_spans} == {"GHOSTe"}


def test_vpb_pages_38_to_41_have_source_verified_local_tm_regions(project_root: Path):
    policy, geometry, quality = _load_configs(project_root)
    source = project_root / _VPB_SOURCE_RELATIVE_PATH
    assert source.is_file()
    assert sha256_file(source) == _VPB_SOURCE_SHA256

    page_results = []
    with fitz.open(source) as document:
        for page_number in range(38, 42):
            visible = extract_visible_native_text_page(
                document[page_number - 1],
                policy,
                native_text_quality_config=quality,
            )
            assert visible.page.text_quality == "USABLE_TEXT_LAYER"
            page_results.append(
                discover_native_tm_regions(
                    visible.page,
                    geometry_config=geometry,
                    policy=policy,
                    table_id_prefix=f"source-{_VPB_SOURCE_SHA256[:16]}",
                    excluded_spans=visible.excluded_spans,
                )
            )

    assert [len(result.regions) for result in page_results] == [3, 3, 3, 3]
    assert (
        sum(region.value_bearing_row_count for result in page_results for region in result.regions)
        == 57
    )
    assert (
        sum(region.visible_cell_count for result in page_results for region in result.regions)
        == 146
    )


def test_vpb_axis_bindings_preserve_percentage_quantity_rate_and_conversion_semantics(
    project_root: Path,
):
    results = _discover_vpb_pages(project_root, (38, 42, 43, 44, 48, 53, 55, 61, 80, 90))

    ratio = results[38].regions[2].header_bindings
    assert [binding.measure_role for binding in ratio] == ["PERCENTAGE", "PERCENTAGE"]
    assert [binding.unit for binding in ratio] == ["PERCENT", "PERCENT"]
    assert [binding.period_end.isoformat() for binding in ratio] == [
        "2026-03-31",
        "2025-12-31",
    ]
    assert all(
        binding.conflicts == ("EXPLICIT_PERCENT_MEASURE_VS_MONEY_SCALE_TOKEN",)
        and binding.binding_status == "RESOLVED_WITH_SOURCE_CONFLICT"
        for binding in ratio
    )

    for page_number, region_index in ((42, 0), (43, 0), (44, 0), (48, 3), (55, 1)):
        bindings = results[page_number].regions[region_index].header_bindings
        assert [binding.measure_role for binding in bindings] == [
            "AMOUNT",
            "PERCENTAGE",
            "AMOUNT",
            "PERCENTAGE",
        ]
        assert [binding.unit for binding in bindings] == [
            "VND",
            "PERCENT",
            "VND",
            "PERCENT",
        ]
        assert [binding.unit_multiplier for binding in bindings] == [1_000_000, 1, 1_000_000, 1]
        assert [binding.period_end.isoformat() for binding in bindings] == [
            "2026-03-31",
            "2026-03-31",
            "2025-12-31",
            "2025-12-31",
        ]

    share_bindings = results[61].regions[0].header_bindings
    assert [binding.measure_role for binding in share_bindings] == [
        "QUANTITY",
        "AMOUNT",
        "QUANTITY",
        "AMOUNT",
    ]
    assert [binding.unit for binding in share_bindings] == ["SHARE", "VND", "SHARE", "VND"]
    assert [binding.unit_multiplier for binding in share_bindings] == [1, 1_000_000, 1, 1_000_000]
    eps_bindings = results[61].regions[1].header_bindings
    assert all(
        binding.unit_scope == "ROW_DEPENDENT" and binding.binding_status == "PARTIALLY_RESOLVED"
        for binding in eps_bindings
    )
    goodwill_bindings = results[53].regions[0].header_bindings
    assert all(
        binding.unit_scope == "ROW_DEPENDENT" and binding.binding_status == "PARTIALLY_RESOLVED"
        for binding in goodwill_bindings
    )

    converted = results[80].regions[0].header_bindings
    assert len(converted) == 5
    assert all(
        binding.measure_role == "AMOUNT"
        and binding.unit == "VND"
        and binding.unit_multiplier == 1_000_000
        for binding in converted
    )
    assert converted[3].unit_scope == "TABLE_DEFAULT"
    assert all(not binding.conflicts for binding in converted)

    rates = results[90].regions[0].header_bindings
    assert all(
        binding.measure_role == "RATE"
        and binding.unit == "VND"
        and binding.unit_multiplier == 1
        and binding.unit_denominator == "ROW_LABEL_CURRENCY_OR_COMMODITY_UNIT"
        and binding.unit_scope == "ROW_DEPENDENT"
        and binding.binding_status == "PARTIALLY_RESOLVED"
        for binding in rates
    )


def test_vpb_row_dependent_periods_and_scalar_disclosures_are_not_flattened(
    project_root: Path,
):
    results = _discover_vpb_pages(project_root, (40, 41, 45, 48, 49, 50, 60, 66, 88, 91))

    for page_number, region_indices in {
        40: (1, 2),
        41: (2,),
        45: (1, 2),
        48: (0, 1),
        49: (0,),
        50: (0,),
        60: (0,),
        88: (0,),
    }.items():
        for region_index in region_indices:
            bindings = results[page_number].regions[region_index].header_bindings
            assert bindings
            assert all(
                binding.period_scope == "ROW_DEPENDENT"
                and binding.period_type is None
                and binding.period_start is None
                and binding.current_or_comparative is None
                and binding.binding_status == "PARTIALLY_RESOLVED"
                for binding in bindings
            )

    page_49_scalars = results[49].regions[0].scalar_disclosures
    page_50_scalars = results[50].regions[0].scalar_disclosures
    assert [scalar.period_end.isoformat() for scalar in page_49_scalars] == [
        "2026-03-31",
        "2025-12-31",
    ]
    assert [scalar.raw_text for scalar in page_49_scalars] == ["1.489.639", "1.447.869"]
    assert [scalar.period_end.isoformat() for scalar in page_50_scalars] == [
        "2026-03-31",
        "2025-12-31",
    ]
    assert [scalar.raw_text for scalar in page_50_scalars] == ["1.219.881", "1.158.286"]
    assert all(
        scalar.unit == "VND"
        and scalar.unit_multiplier == 1_000_000
        and scalar.ownership_status == "ROW_LOCAL_SCALAR_DISCLOSURE"
        for scalar in (*page_49_scalars, *page_50_scalars)
    )
    assert sum(len(row.cells) for row in results[49].regions[0].rows) == 66
    assert sum(len(row.cells) for row in results[50].regions[0].rows) == 27

    employee = results[66].regions[2].header_bindings
    assert all(
        binding.unit_scope == "ROW_DEPENDENT" and binding.binding_status == "PARTIALLY_RESOLVED"
        for binding in employee
    )
    prior_only = results[91].regions[0].header_bindings
    assert all(
        binding.period_type == "DURATION"
        and binding.period_end.isoformat() == "2025-03-31"
        and binding.current_or_comparative is None
        for binding in prior_only
    )


@pytest.mark.parametrize(
    (
        "page_number",
        "expected_maximum_axis_count",
        "expected_visible_cell_count",
        "expected_grid_slot_count",
        "expected_invalid_marker_count",
    ),
    (
        (42, 4, 56, 56, 0),
        (80, 5, 70, 70, 0),
        (86, 7, 63, 119, 14),
    ),
)
def test_vpb_source_checkpoints_cover_wide_axes_and_sparse_grid(
    project_root: Path,
    page_number: int,
    expected_maximum_axis_count: int,
    expected_visible_cell_count: int,
    expected_grid_slot_count: int,
    expected_invalid_marker_count: int,
):
    policy, geometry, quality = _load_configs(project_root)
    source = project_root / _VPB_SOURCE_RELATIVE_PATH
    assert source.is_file()
    assert sha256_file(source) == _VPB_SOURCE_SHA256

    with fitz.open(source) as document:
        visible = extract_visible_native_text_page(
            document[page_number - 1],
            policy,
            native_text_quality_config=quality,
        )
    result = discover_native_tm_regions(
        visible.page,
        geometry_config=geometry,
        policy=policy,
        table_id_prefix=f"source-{_VPB_SOURCE_SHA256[:16]}",
        excluded_spans=visible.excluded_spans,
    )

    assert max(len(region.geometry.axes) for region in result.regions) == (
        expected_maximum_axis_count
    )
    assert sum(region.visible_cell_count for region in result.regions) == (
        expected_visible_cell_count
    )
    assert sum(region.grid_slot_count for region in result.regions) == expected_grid_slot_count
    assert (
        sum(
            slot.source_status == "INVALID_SOURCE_MARKER"
            for region in result.regions
            for slot in region.grid_slots
        )
        == expected_invalid_marker_count
    )


def test_vpb_all_source_visible_tm_pages_have_stable_aggregate_coverage(
    project_root: Path,
):
    """Classify TM pages from their visible headers, never an expected page list."""

    policy, geometry, quality = _load_configs(project_root)
    source = project_root / _VPB_SOURCE_RELATIVE_PATH
    assert source.is_file()
    assert sha256_file(source) == _VPB_SOURCE_SHA256

    page_results = []
    excluded_span_count = 0
    with fitz.open(source) as document:
        for source_page in document:
            visible = extract_visible_native_text_page(
                source_page,
                policy,
                native_text_quality_config=quality,
            )
            if visible.page.text_quality != "USABLE_TEXT_LAYER" or not _is_visible_tm_page(
                visible.page
            ):
                continue
            excluded_span_count += len(visible.excluded_spans)
            result = discover_native_tm_regions(
                visible.page,
                geometry_config=geometry,
                policy=policy,
                table_id_prefix=f"source-{_VPB_SOURCE_SHA256[:16]}",
                excluded_spans=visible.excluded_spans,
            )
            source_runs = build_text_runs(
                visible.page.words,
                gap_height_factor=geometry.run_separation_gap_height_factor,
                financial_gap_height_factor=geometry.financial_token_separation_gap_height_factor,
            )
            owned_run_ids = [
                *(run.run_id for region in result.regions for run in region.geometry.runs),
                *(run.run_id for region in result.regions for run in region.detached_margin_runs),
                *(run.run_id for context in result.inter_table_contexts for run in context.runs),
                *(run.run_id for run in result.unassigned_page_runs),
            ]
            assert Counter(owned_run_ids) == Counter(run.run_id for run in source_runs)
            page_results.append(result)

    assert page_results
    assert any(not result.regions for result in page_results)
    assert any(result.regions for result in page_results)
    assert excluded_span_count == 51
    assert (
        sum(region.value_bearing_row_count for result in page_results for region in result.regions)
        == 694
    )
    assert (
        sum(region.visible_cell_count for result in page_results for region in result.regions)
        == 2163
    )


def test_vpb_hidden_continuation_numbers_and_margin_glyph_do_not_corrupt_rows(
    project_root: Path,
):
    policy, geometry, quality = _load_configs(project_root)
    source = project_root / _VPB_SOURCE_RELATIVE_PATH
    assert sha256_file(source) == _VPB_SOURCE_SHA256

    with fitz.open(source) as document:
        results = {}
        for page_number in (78, 82):
            visible = extract_visible_native_text_page(
                document[page_number - 1],
                policy,
                native_text_quality_config=quality,
            )
            results[page_number] = (
                visible,
                discover_native_tm_regions(
                    visible.page,
                    geometry_config=geometry,
                    policy=policy,
                    table_id_prefix=f"source-{_VPB_SOURCE_SHA256[:16]}",
                    excluded_spans=visible.excluded_spans,
                ),
            )

    page_78 = results[78][1]
    assert page_78.regions[0].detached_margin_runs == ()
    assert any(
        row.label == "Công cụ tài chính phái sinh và các khoản nợ tài chính khác"
        for row in page_78.regions[0].rows
    )
    assert all(not row.label.startswith("6 ") for row in page_78.regions[0].rows)
    assert {"6", "43."} <= {span.raw_text for span in results[78][0].excluded_spans}
    assert "43" in {span.raw_text for span in results[82][0].excluded_spans}


def test_vpb_multiline_labels_inter_table_context_and_row_roles_are_fail_closed(
    project_root: Path,
):
    policy, geometry, quality = _load_configs(project_root)
    source = project_root / _VPB_SOURCE_RELATIVE_PATH
    assert sha256_file(source) == _VPB_SOURCE_SHA256
    requested = (38, 40, 42, 45, 61, 71, 78, 82, 90)

    results = {}
    with fitz.open(source) as document:
        for page_number in requested:
            visible = extract_visible_native_text_page(
                document[page_number - 1],
                policy,
                native_text_quality_config=quality,
            )
            results[page_number] = (
                visible.page,
                discover_native_tm_regions(
                    visible.page,
                    geometry_config=geometry,
                    policy=policy,
                    table_id_prefix=f"source-{_VPB_SOURCE_SHA256[:16]}",
                    excluded_spans=visible.excluded_spans,
                ),
            )

    labels = {
        page: [row.label for region in result.regions for row in region.rows]
        for page, (_visible, result) in results.items()
    }
    assert "Cho vay chiết khấu công cụ chuyển nhượng và các giấy tờ có giá" in labels[42]
    assert "Sử dụng dự phòng xử lý rủi ro tín dụng trong kỳ" in labels[45]
    assert "CTCP Cảng Sài Gòn - VPB đầu tư góp vốn dài hạn trên 5% vốn điều lệ" in labels[71]
    assert "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro" in labels[78]
    assert "Tiền gửi tại Ngân hàng Nhà nước Việt Nam" in labels[82]

    page_90_rows = [row for region in results[90][1].regions for row in region.rows]
    assert {row.label for row in page_90_rows if row.label in {"AUD", "USD", "Vàng (*)"}} == {
        "AUD",
        "USD",
        "Vàng (*)",
    }
    assert all(
        row.row_type is RowType.DATA_ROW
        for row in page_90_rows
        if row.label in {"AUD", "USD", "Vàng (*)"}
    )
    assert any(
        row.label == "(*) là tỷ giá cho 0,1 lượng vàng."
        for region in results[90][1].regions
        for row in region.outside_financial_span_rows
    )
    assert all(
        not row.label.startswith("Công ") or row.row_type is RowType.DATA_ROW
        for _page, (_visible, result) in results.items()
        for region in result.regions
        for row in region.rows
        if row.cells
    )

    page_38_context = results[38][1].inter_table_contexts[0]
    assert [run.raw_text for run in page_38_context.runs] == [
        "6.",
        "TIỀN GỬI TẠI NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
    ]
    page_40_context = results[40][1].inter_table_contexts[0]
    assert "thế chấp" in " ".join(run.raw_text for run in page_40_context.runs)
    page_61_context = results[61][1].inter_table_contexts[0]
    assert [run.raw_text for run in page_61_context.runs][-2:] == [
        "26.",
        "THU NHẬP TRÊN MỖI CỔ PHIẾU",
    ]
    assert all(
        context.ownership_status == "UNRESOLVED_INTER_TABLE_OWNERSHIP"
        for page in (38, 40, 61)
        for context in results[page][1].inter_table_contexts
    )

    for visible, result in results.values():
        source_runs = build_text_runs(
            visible.words,
            gap_height_factor=geometry.run_separation_gap_height_factor,
            financial_gap_height_factor=geometry.financial_token_separation_gap_height_factor,
        )
        owned_run_ids = [
            *(run.run_id for region in result.regions for run in region.geometry.runs),
            *(run.run_id for region in result.regions for run in region.detached_margin_runs),
            *(run.run_id for context in result.inter_table_contexts for run in context.runs),
            *(run.run_id for run in result.unassigned_page_runs),
        ]
        assert Counter(owned_run_ids) == Counter(run.run_id for run in source_runs)
