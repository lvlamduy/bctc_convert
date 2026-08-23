from __future__ import annotations

import copy
import io

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation.family_first_visible_dash_glyph_evidence_v1 import (
    build_family_first_visible_dash_glyph_evidence_v1,
)
from bctc_ai.evaluation.loan_geography_numeric_reconciliation_v1 import (
    INPUT_FORMAT_VERSION,
    LoanGeographyNumericReconciliationV1Error,
    build_loan_geography_numeric_reconciliation_v1,
    validate_loan_geography_numeric_reconciliation_replay_v1,
    validate_loan_geography_numeric_reconciliation_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _cell(
    cell_id: str,
    lane: int,
    ppocr: str | None,
    *,
    page: int = 7,
    vietocr: str | None = None,
) -> dict:
    return {
        "bbox": [100 + lane * 100, 200, 180 + lane * 100, 230],
        "cell_id": cell_id,
        "crop_sha256": None,
        "lane_index": lane,
        "lane_type": "MONEY",
        "page_sequence": page,
        "ppocrv6_score": 0.99 if ppocr is not None else None,
        "ppocrv6_surface": ppocr,
        "sample_id": f"sample-{cell_id}" if ppocr is not None else None,
        "source_line_index": lane + 10 if ppocr is not None else None,
        "vietocr_surface": ppocr if vietocr is None else vietocr,
    }


def _row(
    role: str,
    ppocr: list[str | None],
    *,
    pages: tuple[int, int] = (7, 7),
    vietocr: list[str | None] | None = None,
) -> dict:
    vietocr = ppocr if vietocr is None else vietocr
    return {
        "cells": [
            _cell(
                f"{role}-{lane}",
                lane,
                surface,
                page=pages[lane],
                vietocr=vietocr[lane],
            )
            for lane, surface in enumerate(ppocr)
        ],
        "label_evidence_ref": f"label-{role}",
        "label_surface": role,
        "role": role,
    }


def _total_row(
    ppocr: list[str | None],
    *,
    pages: tuple[int, int],
    vietocr: list[str | None] | None,
) -> dict:
    row = _row(
        "PRINTED_CUSTOMER_LOAN_TOTAL",
        ppocr,
        pages=pages,
        vietocr=vietocr,
    )
    row["control_evidence"] = [
        {
            "evidence_refs": [f"line:{pages[lane]}:{lane + 10}"],
            "label_evidence_ref": "label-PRINTED_CUSTOMER_LOAN_TOTAL",
            "label_surface": "PRINTED_CUSTOMER_LOAN_TOTAL",
            "lane_index": lane,
            "page_sequence": pages[lane],
            "resolution_mode": "LOCAL_LABELED_TOTAL",
            "row_bbox": [100 + lane * 100, 200, 180 + lane * 100, 230],
            "source_bboxes": [[100 + lane * 100, 200, 180 + lane * 100, 230]],
            "source_line_indices": [lane + 10],
            "source_surfaces_raw_nfc": [surface or "-"],
        }
        for lane, surface in enumerate(ppocr)
    ]
    row["label_evidence_ref"] = "|".join(
        item["label_evidence_ref"] for item in row["control_evidence"]
    )
    row["label_surface"] = " | ".join(item["label_surface"] for item in row["control_evidence"])
    return row


def _source(
    *,
    domestic: list[str | None] | None = None,
    foreign: list[str | None] | None = None,
    total: list[str | None] | None = None,
    domestic_viet: list[str | None] | None = None,
    foreign_viet: list[str | None] | None = None,
    total_viet: list[str | None] | None = None,
    pages: tuple[int, int] = (7, 7),
    presentation: str = "SINGLE_PAGE_GEOGRAPHY_ROWS_ACCOUNTING_COLUMNS",
    challengers: list[dict] | None = None,
) -> dict:
    domestic = domestic or ["100", "90"]
    foreign = foreign or ["20", "10"]
    total = total or ["120", "100"]
    return {
        "family_id": "LOAN_GEOGRAPHIC_CLASSIFICATION",
        "format_version": INPUT_FORMAT_VERSION,
        "known_nested_domestic_roles_outside_contract": [
            "HO_CHI_MINH_CITY",
            "MEKONG_DELTA",
            "CENTRAL_AND_CENTRAL_HIGHLANDS",
            "NORTH",
            "SOUTHEAST",
        ],
        "lane_types": ["MONEY", "MONEY"],
        "mapped_rows": [
            _row("DOMESTIC_TOTAL", domestic, pages=pages, vietocr=domestic_viet),
            _row("FOREIGN_TOTAL", foreign, pages=pages, vietocr=foreign_viet),
        ],
        "period_axis": [
            {
                "evidence_ref": "period-current",
                "lane_index": 0,
                "lane_type": "MONEY",
                "period_end": "2026-06-30",
                "period_role": "CURRENT",
                "resolution_mode": "LOCAL_EXACT_DATE",
                "source_surface": "30/06/2026",
            },
            {
                "evidence_ref": "period-comparative",
                "lane_index": 1,
                "lane_type": "MONEY",
                "period_end": "2025-12-31",
                "period_role": "COMPARATIVE",
                "resolution_mode": "DOCUMENT_INHERITED_EXACT_DATE",
                "source_surface": "31/12/2025",
            },
        ],
        "presentation_mode": presentation,
        "printed_customer_loan_total": _total_row(total, pages=pages, vietocr=total_viet),
        "region_id": "region-geography-test",
        "source_id": "source-geography-test",
        "structure_challenger_refs": [] if challengers is None else challengers,
        "unit_context": {
            "currency": "VND",
            "evidence_ref": "unit-local",
            "resolution_mode": "LOCAL_EXACT_UNIT",
            "scale": 6,
            "source_surface": "Triệu VND",
            "unit_kind": "MONEY",
        },
    }


def _dash(cell: dict, role: str, region_id: str) -> dict:
    image = Image.new("RGB", (40, 20), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((11, 9, 26, 10), fill="black")
    payload = io.BytesIO()
    image.save(payload, format="PNG")
    crop = payload.getvalue()
    evidence = build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=crop)
    assert evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    return {
        "cell_id": cell["cell_id"],
        "crop_png_bytes": crop,
        "evidence": evidence,
        "lane_index": cell["lane_index"],
        "lane_type": "MONEY",
        "page_sequence": cell["page_sequence"],
        "region_id": region_id,
        "role": role,
    }


def test_single_page_rows_are_exact_and_publicly_replayable() -> None:
    source = _source()
    result = build_loan_geography_numeric_reconciliation_v1(source)
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["metrics"]["mapped_money_cell_count"] == 4
    assert result["metrics"]["exact_observed_equation_count"] == 2
    assert validate_loan_geography_numeric_reconciliation_v1(result) == result
    assert validate_loan_geography_numeric_reconciliation_replay_v1(result, source) == result


def test_repeated_full_segments_on_two_pages_use_the_same_normalized_matrix() -> None:
    source = _source(pages=(53, 54), presentation="REPEATED_FULL_SEGMENT_ONE_PERIOD_PER_PAGE")
    result = build_loan_geography_numeric_reconciliation_v1(source)
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert [cell["page_sequence"] for cell in result["mapped_rows"][0]["cells"]] == [53, 54]
    assert result["presentation_mode"] == "REPEATED_FULL_SEGMENT_ONE_PERIOD_PER_PAGE"


def test_one_current_period_lane_is_complete_without_a_comparative_lane() -> None:
    source = _source()
    source["lane_types"] = ["MONEY"]
    source["period_axis"] = source["period_axis"][:1]
    for row in [*source["mapped_rows"], source["printed_customer_loan_total"]]:
        row["cells"] = row["cells"][:1]
    source["printed_customer_loan_total"]["control_evidence"] = source[
        "printed_customer_loan_total"
    ]["control_evidence"][:1]
    source["printed_customer_loan_total"]["label_evidence_ref"] = (
        "label-PRINTED_CUSTOMER_LOAN_TOTAL"
    )
    source["printed_customer_loan_total"]["label_surface"] = "PRINTED_CUSTOMER_LOAN_TOTAL"
    result = build_loan_geography_numeric_reconciliation_v1(source)
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["metrics"]["mapped_money_cell_count"] == 2
    assert result["metrics"]["source_control_money_cell_count"] == 1
    assert result["metrics"]["exact_observed_equation_count"] == 1


def test_three_observed_period_segments_remain_one_generic_matrix() -> None:
    source = _source(pages=(53, 54), presentation="REPEATED_FULL_SEGMENT_ONE_PERIOD_PER_PAGE")
    source["lane_types"].append("MONEY")
    source["period_axis"].append(
        {
            "evidence_ref": "period-comparative-2",
            "lane_index": 2,
            "lane_type": "MONEY",
            "period_end": "2024-12-31",
            "period_role": "COMPARATIVE",
            "resolution_mode": "LOCAL_EXACT_DATE",
            "source_surface": "31/12/2024",
        }
    )
    for row, value in zip(
        [*source["mapped_rows"], source["printed_customer_loan_total"]],
        ["80", "5", "85"],
        strict=True,
    ):
        row["cells"].append(_cell(f"{row['role']}-2", 2, value, page=55))
    source["printed_customer_loan_total"]["control_evidence"].append(
        {
            "evidence_refs": ["line:55:12"],
            "label_evidence_ref": "label-PRINTED_CUSTOMER_LOAN_TOTAL",
            "label_surface": "PRINTED_CUSTOMER_LOAN_TOTAL",
            "lane_index": 2,
            "page_sequence": 55,
            "resolution_mode": "LOCAL_LABELED_TOTAL",
            "row_bbox": [300, 200, 380, 230],
            "source_bboxes": [[300, 200, 380, 230]],
            "source_line_indices": [12],
            "source_surfaces_raw_nfc": ["85"],
        }
    )
    source["printed_customer_loan_total"]["label_evidence_ref"] += (
        "|label-PRINTED_CUSTOMER_LOAN_TOTAL"
    )
    source["printed_customer_loan_total"]["label_surface"] += " | PRINTED_CUSTOMER_LOAN_TOTAL"
    result = build_loan_geography_numeric_reconciliation_v1(source)
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["metrics"]["mapped_money_cell_count"] == 6
    assert result["metrics"]["source_control_money_cell_count"] == 3
    assert result["metrics"]["exact_observed_equation_count"] == 3


def _make_second_total_lane_unlabeled(source: dict) -> None:
    total = source["printed_customer_loan_total"]
    lane = total["control_evidence"][1]
    lane["label_evidence_ref"] = "astgv1:trailing-total-resolution:unlabeled-lane-1"
    lane["label_surface"] = None
    lane["resolution_mode"] = "LOCAL_UNLABELED_TOTAL_ROW"
    total["label_evidence_ref"] = "|".join(
        item["label_evidence_ref"] for item in total["control_evidence"]
    )
    total["label_surface"] = None


def _make_second_total_lane_upstream(source: dict) -> None:
    total = source["printed_customer_loan_total"]
    cell = total["cells"][1]
    locator = {
        "bbox": copy.deepcopy(cell["bbox"]),
        "crop_ref": {"path": "upstream-total.png", "sha256": "a" * 64, "size_bytes": 1},
        "page_render": {
            "physical_page": cell["page_sequence"],
            "pixel_height": 1_000,
            "pixel_width": 1_000,
            "render_sha256": "b" * 64,
            "render_size_bytes": 1,
        },
        "page_sequence": cell["page_sequence"],
        "ppocrv6_reader_score": cell["ppocrv6_score"],
        "ppocrv6_surface": cell["ppocrv6_surface"],
        "sample_id": cell["sample_id"],
        "source_line_index": cell["source_line_index"],
        "vietocr_transformer_surface": cell["vietocr_surface"],
    }
    cell["crop_sha256"] = locator["crop_ref"]["sha256"]
    evidence = total["control_evidence"][1]
    evidence.clear()
    evidence.update(
        {
            "control_request_id": "lgstv1:total-control-request:" + "1" * 64,
            "control_result_id": "cltcv1:result:" + "2" * 64,
            "evidence_refs": [f"line:{locator['page_sequence']}:{locator['source_line_index']}"],
            "label_evidence_ref": "cltcv1:result:" + "2" * 64,
            "label_surface": None,
            "lane_index": 1,
            "page_sequence": locator["page_sequence"],
            "request_set_id": "lgstv1:total-control-request-set:" + "3" * 64,
            "resolution_mode": "UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL",
            "row_bbox": copy.deepcopy(locator["bbox"]),
            "source_bboxes": [copy.deepcopy(locator["bbox"])],
            "source_control_graph_result_id": "ltvgv1:result:" + "4" * 64,
            "source_control_numeric_result_id": "ltnrrv1:result:" + "5" * 64,
            "source_document_graph_result_id": "lgstv1:document:" + "6" * 64,
            "source_graph_id": "astgv1:graph:upstream-test",
            "source_line_indices": [locator["source_line_index"]],
            "source_locator": locator,
            "source_locator_id": "lgstv1:source-locator:" + canonical_json_sha256_v1(locator),
            "source_segment_id": "astgv1:segment:upstream-test",
            "source_snapshot_id": "ffdesv1:snapshot:" + "7" * 64,
            "source_surfaces_raw_nfc": [locator["vietocr_transformer_surface"]],
        }
    )
    total["label_evidence_ref"] = "|".join(
        item["label_evidence_ref"] for item in total["control_evidence"]
    )
    total["label_surface"] = None


def test_total_control_mode_is_typed_per_lane_and_mixed_modes_replay() -> None:
    source = _source()
    _make_second_total_lane_unlabeled(source)

    result = build_loan_geography_numeric_reconciliation_v1(source)

    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    total = result["printed_customer_loan_total"]
    assert total["label_surface"] is None
    assert [item["resolution_mode"] for item in total["control_evidence"]] == [
        "LOCAL_LABELED_TOTAL",
        "LOCAL_UNLABELED_TOTAL_ROW",
    ]
    assert validate_loan_geography_numeric_reconciliation_replay_v1(result, source) == result


def test_upstream_total_control_mode_retains_typed_source_ids_and_replays() -> None:
    source = _source()
    _make_second_total_lane_upstream(source)

    result = build_loan_geography_numeric_reconciliation_v1(source)

    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    evidence = result["printed_customer_loan_total"]["control_evidence"][1]
    assert evidence["resolution_mode"] == ("UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL")
    assert evidence["control_request_id"].startswith("lgstv1:total-control-request:")
    assert evidence["control_result_id"].startswith("cltcv1:result:")
    assert evidence["source_locator_id"] == (
        "lgstv1:source-locator:" + canonical_json_sha256_v1(evidence["source_locator"])
    )
    assert evidence["source_locator"]["page_render"]["render_sha256"] == "b" * 64
    assert evidence["source_locator"]["crop_ref"]["sha256"] == "a" * 64
    assert result["authority"]["upstream_authenticated_total_control_can_backsolve"] is False
    assert validate_loan_geography_numeric_reconciliation_replay_v1(result, source) == result


@pytest.mark.parametrize(
    "mutation",
    [
        "MISSING_FIELD",
        "CONTROL_ID",
        "REQUEST_ID",
        "LOCATOR_ID",
        "RENDER",
        "CROP",
        "SOURCE_PAGE",
        "CELL_CROP",
        "CELL_SURFACE",
    ],
)
def test_upstream_total_control_mode_tamper_fails_closed(mutation: str) -> None:
    source = _source()
    _make_second_total_lane_upstream(source)
    total = source["printed_customer_loan_total"]
    evidence = total["control_evidence"][1]
    cell = total["cells"][1]
    if mutation == "MISSING_FIELD":
        evidence.pop("source_segment_id")
    elif mutation == "CONTROL_ID":
        evidence["control_result_id"] = "wrong-control"
    elif mutation == "REQUEST_ID":
        evidence["control_request_id"] = "wrong-request"
    elif mutation == "LOCATOR_ID":
        evidence["source_locator_id"] = "lgstv1:source-locator:" + "8" * 64
    elif mutation == "RENDER":
        evidence["source_locator"]["page_render"]["render_sha256"] = "8" * 64
    elif mutation == "CROP":
        evidence["source_locator"]["crop_ref"]["sha256"] = "8" * 64
    elif mutation == "SOURCE_PAGE":
        evidence["source_locator"]["page_sequence"] += 1
    elif mutation == "CELL_CROP":
        cell["crop_sha256"] = "8" * 64
    else:
        cell["ppocrv6_surface"] = "101"

    with pytest.raises(LoanGeographyNumericReconciliationV1Error):
        build_loan_geography_numeric_reconciliation_v1(source)


@pytest.mark.parametrize(
    "mutation",
    [
        "UNLABELED_LABEL",
        "LABELED_NULL_LABEL",
        "AGGREGATE_LABEL",
        "SOURCE_BBOX",
        "SOURCE_LINE",
        "UNKNOWN_MODE",
    ],
)
def test_total_control_mode_and_raw_geometry_tamper_fail_closed(mutation: str) -> None:
    source = _source()
    _make_second_total_lane_unlabeled(source)
    total = source["printed_customer_loan_total"]
    if mutation == "UNLABELED_LABEL":
        total["control_evidence"][1]["label_surface"] = "Tổng cộng"
    elif mutation == "LABELED_NULL_LABEL":
        total["control_evidence"][0]["label_surface"] = None
    elif mutation == "AGGREGATE_LABEL":
        total["label_surface"] = "Tổng cộng"
    elif mutation == "SOURCE_BBOX":
        total["control_evidence"][1]["source_bboxes"][0][0] += 1
    elif mutation == "SOURCE_LINE":
        total["control_evidence"][1]["source_line_indices"][0] += 1
    else:
        total["control_evidence"][1]["resolution_mode"] = "INVENTED_TOTAL"

    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="printed-total"):
        build_loan_geography_numeric_reconciliation_v1(source)


def test_period_and_source_role_order_are_not_presentation_routing_rules() -> None:
    source = _source()
    source["mapped_rows"].reverse()
    source["period_axis"].reverse()
    for lane, period in enumerate(source["period_axis"]):
        period["lane_index"] = lane
    for row in [*source["mapped_rows"], source["printed_customer_loan_total"]]:
        row["cells"].reverse()
        for lane, cell in enumerate(row["cells"]):
            cell["lane_index"] = lane
    source["printed_customer_loan_total"]["control_evidence"].reverse()
    for lane, evidence in enumerate(source["printed_customer_loan_total"]["control_evidence"]):
        evidence["lane_index"] = lane
    result = build_loan_geography_numeric_reconciliation_v1(source)
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert [period["period_role"] for period in result["period_axis"]] == [
        "COMPARATIVE",
        "CURRENT",
    ]
    assert [row["role"] for row in result["mapped_rows"]] == [
        "DOMESTIC_TOTAL",
        "FOREIGN_TOTAL",
    ]


def test_duplicate_period_and_missing_or_extra_source_role_fail_closed() -> None:
    source = _source()
    source["period_axis"][1]["period_end"] = source["period_axis"][0]["period_end"]
    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="repeat"):
        build_loan_geography_numeric_reconciliation_v1(source)

    source = _source()
    source["mapped_rows"].pop()
    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="population"):
        build_loan_geography_numeric_reconciliation_v1(source)

    source = _source()
    source["mapped_rows"][1]["role"] = "UNKNOWN_GEOGRAPHY"
    with pytest.raises(
        LoanGeographyNumericReconciliationV1Error, match="missing, duplicate, or extra"
    ):
        build_loan_geography_numeric_reconciliation_v1(source)


def test_exact_equation_selects_only_one_already_observed_reader_candidate() -> None:
    source = _source(domestic_viet=["101", "90"])
    result = build_loan_geography_numeric_reconciliation_v1(source)
    cell = result["mapped_rows"][0]["cells"][0]
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert cell["candidate_values"] == [
        {"readers": ["PPOCRV6"], "value": 100},
        {"readers": ["VIETOCR"], "value": 101},
    ]
    assert cell["selected_value"] == 100
    assert cell["selected_readers"] == ["PPOCRV6"]
    assert cell["selection_mode"] == "UNIQUE_OBSERVED_CANDIDATE_SELECTED_BY_EXACT_EQUATION"
    assert result["metrics"]["accounting_uniquely_selected_observed_cell_count"] == 1


def test_two_exact_observed_assignments_remain_ambiguous() -> None:
    source = _source(
        domestic_viet=["101", "90"],
        foreign_viet=["19", "10"],
    )
    result = build_loan_geography_numeric_reconciliation_v1(source)
    assert result["status"] == "UNRESOLVED"
    assert result["accounting_checks"][0]["exact_observed_assignment_count"] == 2
    assert (
        result["accounting_checks"][0]["status"] == "UNRESOLVED_MULTIPLE_EXACT_OBSERVED_ASSIGNMENTS"
    )
    assert result["mapped_rows"][0]["cells"][0]["selected_value"] is None


def test_printed_total_mismatch_vetoes_without_mutating_observations() -> None:
    result = build_loan_geography_numeric_reconciliation_v1(_source(total=["121", "100"]))
    assert result["status"] == "UNRESOLVED"
    assert result["printed_customer_loan_total"]["cells"][0]["selected_value"] == 121
    assert result["accounting_checks"][0]["status"] == "VETOED_NO_EXACT_OBSERVED_ASSIGNMENT"


def test_blank_is_not_zero_and_is_never_backsolved() -> None:
    source = _source(domestic=[None, "90"], domestic_viet=[None, "90"])
    result = build_loan_geography_numeric_reconciliation_v1(source)
    cell = result["mapped_rows"][0]["cells"][0]
    assert result["status"] == "UNRESOLVED"
    assert cell["selected_value"] is None
    assert cell["candidate_values"] == []
    assert result["metrics"]["accounting_backsolved_or_invented_value_count"] == 0


def test_typed_visible_dash_pixel_is_zero_and_exact_replays() -> None:
    source = _source(foreign=[None, "10"], foreign_viet=[None, "10"], total=["100", "100"])
    cell = source["mapped_rows"][1]["cells"][0]
    overlay = _dash(cell, "FOREIGN_TOTAL", source["region_id"])
    result = build_loan_geography_numeric_reconciliation_v1(source, visible_dash_evidence=[overlay])
    resolved = result["mapped_rows"][1]["cells"][0]
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert resolved["selected_value"] == 0
    assert resolved["selected_readers"] == ["PIXEL_DASH"]
    assert result["metrics"]["visible_dash_zero_cell_count"] == 1
    assert (
        validate_loan_geography_numeric_reconciliation_replay_v1(
            result, source, visible_dash_evidence=[overlay]
        )
        == result
    )


def test_raw_dash_surface_without_pixel_replay_is_not_zero() -> None:
    source = _source(foreign=["-", "10"], foreign_viet=["-", "10"], total=["100", "100"])
    result = build_loan_geography_numeric_reconciliation_v1(source)
    assert result["status"] == "UNRESOLVED"
    assert result["mapped_rows"][1]["cells"][0]["selected_value"] is None


def test_dash_cannot_overlay_numeric_or_bind_wrong_region() -> None:
    source = _source()
    overlay = _dash(source["mapped_rows"][0]["cells"][0], "DOMESTIC_TOTAL", source["region_id"])
    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="nonnumeric"):
        build_loan_geography_numeric_reconciliation_v1(source, visible_dash_evidence=[overlay])

    source = _source(foreign=[None, "10"], foreign_viet=[None, "10"], total=["100", "100"])
    overlay = _dash(source["mapped_rows"][1]["cells"][0], "FOREIGN_TOTAL", "wrong-region")
    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="lane/region"):
        build_loan_geography_numeric_reconciliation_v1(source, visible_dash_evidence=[overlay])


def test_self_rehashed_forged_dash_evidence_fails_exact_pixel_replay() -> None:
    source = _source(foreign=[None, "10"], foreign_viet=[None, "10"], total=["100", "100"])
    overlay = _dash(source["mapped_rows"][1]["cells"][0], "FOREIGN_TOTAL", source["region_id"])
    forged = copy.deepcopy(overlay)
    forged["evidence"]["authority"]["mapping_authority"] = True
    material = copy.deepcopy(forged["evidence"])
    material.pop("evidence_id")
    forged["evidence"]["evidence_id"] = "ffvdgev1:evidence:" + canonical_json_sha256_v1(material)
    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="pixel replay"):
        build_loan_geography_numeric_reconciliation_v1(source, visible_dash_evidence=[forged])


def test_gemma_reference_is_structure_only_and_cannot_carry_numbers() -> None:
    challenger = {
        "challenger_id": "challenger-1",
        "kind": "FULL_PAGE_TABLE_STRUCTURE_PROPOSAL",
        "model": "gemma-4-26b-a4b-it",
        "numeric_authority": False,
        "page_image_sha256": "b" * 64,
        "page_sequence": 7,
        "prompt_sha256": "c" * 64,
        "provider": "HOSTED_API",
        "raw_response_sha256": "a" * 64,
    }
    result = build_loan_geography_numeric_reconciliation_v1(_source(challengers=[challenger]))
    assert result["structure_challenger_refs"] == [challenger]
    assert result["metrics"]["structure_challenger_count"] == 1
    assert result["metrics"]["gemma_numeric_authority_count"] == 0

    challenger["numeric_authority"] = True
    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="challenger"):
        build_loan_geography_numeric_reconciliation_v1(_source(challengers=[challenger]))

    challenger["numeric_authority"] = False
    challenger["numeric_values"] = [120]
    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="challenger"):
        build_loan_geography_numeric_reconciliation_v1(_source(challengers=[challenger]))


def test_known_nested_roles_are_preserved_outside_numeric_contract() -> None:
    source = _source()
    result = build_loan_geography_numeric_reconciliation_v1(source)
    assert result["known_nested_domestic_roles_outside_contract"] == [
        "HO_CHI_MINH_CITY",
        "MEKONG_DELTA",
        "CENTRAL_AND_CENTRAL_HIGHLANDS",
        "NORTH",
        "SOUTHEAST",
    ]
    source["known_nested_domestic_roles_outside_contract"].pop()
    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="nested-role"):
        build_loan_geography_numeric_reconciliation_v1(source)


def test_coordinated_rehash_cannot_change_selected_value() -> None:
    result = build_loan_geography_numeric_reconciliation_v1(_source())
    tampered = copy.deepcopy(result)
    tampered["mapped_rows"][0]["cells"][0]["selected_value"] = 99
    material = copy.deepcopy(tampered)
    material.pop("result_id")
    tampered["result_id"] = "lgnrv1:result:" + canonical_json_sha256_v1(material)
    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="semantics"):
        validate_loan_geography_numeric_reconciliation_v1(tampered)


def test_exact_types_and_cell_identity_bindings_fail_closed() -> None:
    source = _source()
    source["mapped_rows"][0]["cells"][0]["ppocrv6_score"] = True
    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="score"):
        build_loan_geography_numeric_reconciliation_v1(source)

    source = _source()
    source["mapped_rows"][0]["cells"][0]["cell_id"] = source["mapped_rows"][1]["cells"][0][
        "cell_id"
    ]
    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="repeat"):
        build_loan_geography_numeric_reconciliation_v1(source)


@pytest.mark.parametrize(
    ("field", "value"),
    [("currency", "USD"), ("scale", 3), ("scale", True)],
)
def test_unit_contract_is_exact_million_vnd(field: str, value: object) -> None:
    source = _source()
    source["unit_context"][field] = value
    with pytest.raises(LoanGeographyNumericReconciliationV1Error, match="unit context identity"):
        build_loan_geography_numeric_reconciliation_v1(source)
