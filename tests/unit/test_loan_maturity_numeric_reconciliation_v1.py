from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.loan_maturity_numeric_reconciliation_v1 import (
    INPUT_FORMAT_VERSION,
    LoanMaturityNumericReconciliationV1Error,
    build_loan_maturity_numeric_reconciliation_v1,
    validate_loan_maturity_numeric_reconciliation_replay_v1,
    validate_loan_maturity_numeric_reconciliation_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _cell(cell_id: str, lane: int, kind: str, surface: str | None) -> dict:
    return {
        "bbox": [100 + lane * 100, 200, 180 + lane * 100, 230],
        "cell_id": cell_id,
        "crop_sha256": None,
        "lane_index": lane,
        "lane_type": kind,
        "ppocrv6_score": 0.99 if surface is not None else None,
        "ppocrv6_surface": surface,
        "sample_id": f"sample-{cell_id}",
        "source_line_index": lane + 10,
        "vietocr_surface": surface,
    }


def _row(role: str, surfaces: list[str | None], lanes: list[str]) -> dict:
    return {
        "cells": [
            _cell(f"{role}-{index}", index, kind, surfaces[index])
            for index, kind in enumerate(lanes)
        ],
        "label_surface": role,
        "role": role,
    }


def _source(
    *,
    lanes: list[str] | None = None,
    rows: list[list[str | None]] | None = None,
    subtotal: list[str | None] | None = None,
    margin: list[str | None] | None = None,
    grand: list[str | None] | None = None,
    additional: tuple[list[str | None], list[list[str | None]]] | None = None,
) -> dict:
    lanes = lanes or ["MONEY", "MONEY"]
    rows = rows or [["100", "90"], ["50", "40"], ["25", "20"]]
    return {
        "additional_population": (
            None
            if additional is None
            else {
                "breakdown_rows": [
                    _row(f"ADDITIONAL_BREAKDOWN_{index}", values, lanes)
                    for index, values in enumerate(additional[1], start=1)
                ],
                "parent": _row("ADDITIONAL_POPULATION_PARENT", additional[0], lanes),
            }
        ),
        "core_rows": [
            _row(role, values, lanes)
            for role, values in zip(("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"), rows, strict=True)
        ],
        "core_subtotal": None if subtotal is None else _row("CORE_SUBTOTAL", subtotal, lanes),
        "family_id": "LOAN_MATURITY_BUCKETS",
        "format_version": INPUT_FORMAT_VERSION,
        "grand_total": None if grand is None else _row("GRAND_TOTAL", grand, lanes),
        "lane_types": lanes,
        "margin": (
            None if margin is None else _row("MARGIN_AND_SECURITIES_ADVANCE", margin, lanes)
        ),
        "period_axis": {"mode": "EXACT_DATE", "periods": ["CURRENT", "COMPARATIVE"]},
        "source_id": "test-source",
    }


def _e0170(source: dict, target: tuple[str, int, str], control: tuple[str, int, str]) -> dict:
    indexed = {
        (row["role"], cell["lane_index"]): cell
        for row in [
            *source["core_rows"],
            source["core_subtotal"],
            source["grand_total"],
            source["margin"],
        ]
        if row is not None
        for cell in row["cells"]
    }

    def observation(spec: tuple[str, int, str], *, total_control: bool) -> dict:
        role, lane, selected = spec
        cell = indexed[(role, lane)]
        return {
            "hosted_gemma4_consensus_surface": selected,
            "lane_index": lane,
            "lane_type": cell["lane_type"],
            "ppocrv6_original_surface": cell["ppocrv6_surface"],
            "role": "CORE_TOTAL" if total_control and role == "CORE_SUBTOTAL" else role,
            "sample_id": cell["sample_id"],
            "selected_surface": selected,
            "selected_value": int(selected.replace(".", "")),
            "source_bbox_cached_200dpi": cell["bbox"],
            "source_line_index": cell["source_line_index"],
            "vietocr_transformer_surface": cell["vietocr_surface"],
        }

    content_sha = "1" * 64
    material = {
        "decision": {
            "both_hosted_responses_agree_exactly": True,
            "fresh_request_count": 2,
            "gemma4_may_act_as_sole_numeric_reader": False,
            "hosted_requests_are_stateless": True,
        },
        "format_version": (
            "FAMILY_FIRST_LOAN_MATURITY_HOSTED_GEMMA4_NUMERIC_CHALLENGER_EVALUATION_V1"
        ),
        "requests": [
            {
                "fresh_context": True,
                "http_status": 200,
                "raw_response_ref": {"sha256": char * 64},
                "request_ordinal": ordinal,
                "response_content_ref": {"sha256": content_sha},
            }
            for ordinal, char in ((1, "2"), (2, "3"))
        ],
        "target_observation": observation(target, total_control=False),
        "total_control_observation": observation(control, total_control=True),
    }
    return {
        **material,
        "evaluation_id": "maturitygemma4v1:evaluation:" + canonical_json_sha256_v1(material),
    }


def _dash(cell: dict, character: str, role: str) -> dict:
    crop_sha = character * 64
    material = {
        "classification": "VISIBLE_HORIZONTAL_DASH_GLYPH",
        "crop_ref": {"sha256": crop_sha},
        "format_version": "FAMILY_FIRST_VISIBLE_DASH_GLYPH_EVIDENCE_V1",
        "normalized_value": 0,
    }
    evidence = {
        **material,
        "evidence_id": "ffvdgev1:evidence:" + canonical_json_sha256_v1(material),
    }
    return {
        "cell_id": cell["cell_id"],
        "evidence": evidence,
        "lane_index": cell["lane_index"],
        "lane_type": cell["lane_type"],
        "role": role,
    }


def _additional_wrapper(source: dict) -> dict:
    def raw_dash(character: str, *, visible: bool) -> dict:
        material = {
            "classification": (
                "VISIBLE_HORIZONTAL_DASH_GLYPH" if visible else "UNRESOLVED_NOT_ONE_DASH_GLYPH"
            ),
            "crop_ref": {"sha256": character * 64},
            "format_version": "FAMILY_FIRST_VISIBLE_DASH_GLYPH_EVIDENCE_V1",
            "normalized_value": 0 if visible else None,
        }
        return {
            **material,
            "evidence_id": "ffvdgev1:evidence:" + canonical_json_sha256_v1(material),
        }

    clear = {
        "classification": "VISIBLE_PIXEL_DASH_ZERO",
        "dash_evidence": raw_dash("7", visible=True),
        "lane_index": 1,
        "region_id": "region-clear",
        "role": "ADDITIONAL_PARENT",
    }
    paired = {
        "classification": "PAIRED_CENTERED_HIGH_FILL_SHORT_MARK_CANDIDATE",
        "dash_evidence": raw_dash("8", visible=False),
        "lane_index": 1,
        "paired_clear_dash_peer_region_id": "region-clear",
        "paired_clear_dash_peer_role": "ADDITIONAL_PARENT",
        "region_id": "region-paired",
        "role": "ADDITIONAL_SHORT_BREAKDOWN",
    }
    checks = [
        {
            "equation": equation,
            "lane_index": lane,
            "status": "CORROBORATED_EXACT",
        }
        for lane in (0, 1)
        for equation in (
            "ADDITIONAL_PARENT_EQUALS_SHORT_BREAKDOWN",
            "CORE_PLUS_ADDITIONAL_EQUALS_PRINTED_GRAND",
        )
    ]
    selected = lambda lane, value: {  # noqa: E731
        "lane_index": lane,
        "ppocrv6_surface": "10" if lane == 0 else None,
        "selected_value": value,
        "vietocr_transformer_surface": "10" if lane == 0 else None,
    }
    material = {
        "accounting_checks": checks,
        "additional_population": {
            "breakdown": {"values": [selected(0, 10), selected(1, 0)]},
            "values": [selected(0, 10), selected(1, 0)],
        },
        "authority": {
            "accounting_equation_used_as_final_corroboration_and_veto_only": True,
            "bank_filename_note_page_or_period_routing_authority": False,
            "blank_or_detector_omission_means_zero": False,
            "mapping_authority": False,
            "numeric_digits_authority": False,
            "one_centered_high_fill_short_mark_requires_related_clear_dash_peer": True,
            "paired_short_mark_requires_both_observed_equations_exact": True,
            "schema_authority": False,
            "visible_authenticated_pixel_dash_may_normalize_to_zero": True,
        },
        "base_result_id": source["source_id"],
        "claim_boundary": (
            "UNIQUE_MATURITY_SOURCE_ONLY_PARENT_SHORT_AND_GRAND_ROWS_AUTHENTICATED_"
            "PIXEL_DASH_OR_ONE_PAIRED_CENTERED_HIGH_FILL_SHORT_MARK_EVIDENCE_PLUS_"
            "EXACT_ACCOUNTING_VETO_ONLY_NO_BANK_FILENAME_PAGE_PERIOD_NOTE_SCHEMA_MAPPING_"
            "CANONICALIZATION_OR_EXPORT_AUTHORITY"
        ),
        "document_ordinal": 1,
        "evidence": [clear, paired],
        "family_id": "LOAN_MATURITY_BUCKETS",
        "format_version": "LOAN_MATURITY_ADDITIONAL_POPULATION_EVIDENCE_V1",
        "page_sequence": 1,
        "render_id": "render-1",
        "render_ref": {"sha256": "9" * 64},
        "status": "AUTHENTICATED_PIXEL_DASH_AND_ACCOUNTING_EXACT",
    }
    return {
        **material,
        "result_id": "lmaperv1:result:" + canonical_json_sha256_v1(material),
    }


def test_core_only_and_exact_replay() -> None:
    source = _source(subtotal=["175", "150"])
    result = build_loan_maturity_numeric_reconciliation_v1(source)
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["metrics"]["independent_observed_equation_count"] == 2
    assert result["metrics"]["mapped_core_money_cell_count"] == 6
    assert result["metrics"]["computed_unprinted_core_identity_count"] == 0
    assert validate_loan_maturity_numeric_reconciliation_v1(result) == result
    assert validate_loan_maturity_numeric_reconciliation_replay_v1(result, source) == result


def test_margin_without_subtotal_counts_only_two_observed_equations() -> None:
    source = _source(margin=["5", "4"], grand=["180", "154"])
    result = build_loan_maturity_numeric_reconciliation_v1(source)
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["metrics"]["independent_observed_equation_count"] == 2
    assert result["metrics"]["computed_unprinted_core_identity_count"] == 2
    assert result["metrics"]["mapped_margin_money_cell_count"] == 2


def test_margin_with_printed_core_subtotal_has_four_equations() -> None:
    source = _source(subtotal=["175", "150"], margin=["5", "4"], grand=["180", "154"])
    result = build_loan_maturity_numeric_reconciliation_v1(source)
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["metrics"]["independent_observed_equation_count"] == 4
    assert result["metrics"]["source_control_row_count"] == 2


def test_hdb_additional_population_is_source_only_and_has_six_equations() -> None:
    source = _source(
        subtotal=["175", "150"],
        grand=["185", "150"],
        additional=(["10", None], [["10", None]]),
    )
    parent_dash = _dash(
        source["additional_population"]["parent"]["cells"][1],
        "4",
        "ADDITIONAL_POPULATION_PARENT",
    )
    child_dash = _dash(
        source["additional_population"]["breakdown_rows"][0]["cells"][1],
        "5",
        "ADDITIONAL_BREAKDOWN_1",
    )
    result = build_loan_maturity_numeric_reconciliation_v1(
        source, visible_dash_evidence=[parent_dash, child_dash]
    )
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["metrics"]["independent_observed_equation_count"] == 6
    assert result["metrics"]["source_additional_population_count"] == 1
    assert result["metrics"]["visible_dash_zero_cell_count"] == 2
    assert result["additional_population"]["parent"]["cells"][1]["selected_value"] == 0


def test_blank_is_not_zero_and_accounting_does_not_backsolve() -> None:
    source = _source(
        subtotal=["175", "150"],
        grand=["185", "150"],
        additional=(["10", None], [["10", None]]),
    )
    result = build_loan_maturity_numeric_reconciliation_v1(source)
    assert result["status"] == "UNRESOLVED"
    assert result["additional_population"]["parent"]["cells"][1]["selected_value"] is None
    assert result["metrics"]["independent_observed_equation_count"] == 4


def test_typed_additional_population_wrapper_preserves_paired_mark_provenance() -> None:
    source = _source(
        subtotal=["175", "150"],
        grand=["185", "150"],
        additional=(["10", None], [["10", None]]),
    )
    source["source_id"] = "base-result-id"
    source["additional_population"]["parent"]["cells"][1]["source_line_index"] = None
    source["additional_population"]["breakdown_rows"][0]["cells"][1]["source_line_index"] = None
    wrapper = _additional_wrapper(source)
    result = build_loan_maturity_numeric_reconciliation_v1(source, visible_dash_evidence=[wrapper])
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["metrics"]["visible_dash_zero_cell_count"] == 2
    child = result["additional_population"]["breakdown_rows"][0]["cells"][1]
    assert child["ppocrv6_surface"] is None
    assert child["selected_value"] == 0
    assert child["evidence_ref"]["classification"] == (
        "PAIRED_CENTERED_HIGH_FILL_SHORT_MARK_CANDIDATE"
    )
    assert child["evidence_ref"]["region_id"] == "region-paired"
    assert child["evidence_ref"]["wrapper_result_id"] == wrapper["result_id"]


def test_four_lane_money_and_percentage_controls_are_typed() -> None:
    source = _source(
        lanes=["MONEY", "PERCENT", "MONEY", "PERCENT"],
        rows=[
            ["100", "50%", "90", "60%"],
            ["50", "25%", "40", "20%"],
            ["25", "25%", "20", "20%"],
        ],
        subtotal=["175", "100%", "150", "100%"],
    )
    result = build_loan_maturity_numeric_reconciliation_v1(source)
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["metrics"]["independent_observed_equation_count"] == 4
    assert result["metrics"]["percentage_child_cell_count"] == 6
    assert result["metrics"]["percentage_total_control_cell_count"] == 2


def test_percentage_rounding_tolerance_is_explicit_and_bounded() -> None:
    source = _source(
        lanes=["MONEY", "PERCENT", "MONEY", "PERCENT"],
        rows=[
            ["100", "50%", "90", "60%"],
            ["50", "25%", "40", "20%"],
            ["25", "25%", "20", "20%"],
        ],
        subtotal=["175", "99.99%", "150", "100%"],
    )
    result = build_loan_maturity_numeric_reconciliation_v1(source)
    check = next(item for item in result["accounting_checks"] if item["lane_index"] == 1)
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert check["status"] == "CORROBORATED_BOUNDED_ROUNDING_OBSERVED_EQUATION"
    assert check["residual"] == "0.01"
    assert check["equation_tolerance"] == "0.05"


def test_e0170_selects_only_bound_vietocr_and_retains_both_raw_surfaces() -> None:
    source = _source(
        rows=[
            ["437.159.424", "413.956.564"],
            ["90.684.358", "8.454.207"],
            ["258.251.127", "263.953.346"],
        ],
        subtotal=["786.094.909", "766.364.117"],
        margin=["11.441.806", "10.293.729"],
        grand=["797.536.715", "776.657.846"],
    )
    medium = source["core_rows"][1]["cells"][1]
    medium["vietocr_surface"] = "88.454.207"
    subtotal = source["core_subtotal"]["cells"][1]
    subtotal["vietocr_surface"] = "768.364.117"
    overlay = _e0170(
        source,
        ("MEDIUM_TERM", 1, "88.454.207"),
        ("CORE_SUBTOTAL", 1, "766.364.117"),
    )
    result = build_loan_maturity_numeric_reconciliation_v1(source, challenger_overlays=[overlay])
    resolved = result["core_rows"][1]["cells"][1]
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert resolved["ppocrv6_surface"] == "8.454.207"
    assert resolved["vietocr_surface"] == "88.454.207"
    assert resolved["selected_value"] == 88_454_207
    assert result["metrics"]["challenger_observation_count"] == 2
    assert result["metrics"]["challenger_changed_primary_cell_count"] == 1
    assert result["metrics"]["independent_observed_equation_count"] == 4


def test_mismatch_vetoes_without_mutating_any_observation() -> None:
    source = _source(subtotal=["176", "150"])
    result = build_loan_maturity_numeric_reconciliation_v1(source)
    assert result["status"] == "UNRESOLVED"
    assert result["core_subtotal"]["cells"][0]["selected_value"] == 176
    assert result["accounting_checks"][0]["status"] == "VETOED_OBSERVED_EQUATION"


def test_unbound_dash_and_challenger_that_invents_a_value_fail_closed() -> None:
    source = _source(subtotal=["175", "150"])
    bound = _dash(source["core_rows"][0]["cells"][0], "6", "SHORT_TERM")
    bound["cell_id"] = "does-not-exist"
    with pytest.raises(LoanMaturityNumericReconciliationV1Error, match="duplicate or unused"):
        build_loan_maturity_numeric_reconciliation_v1(source, visible_dash_evidence=[bound])

    overlay = _e0170(source, ("MEDIUM_TERM", 1, "40"), ("CORE_SUBTOTAL", 1, "150"))
    overlay_material = copy.deepcopy(overlay)
    overlay_material.pop("evaluation_id")
    overlay_material["target_observation"]["selected_surface"] = "41"
    overlay_material["target_observation"]["selected_value"] = 41
    overlay_material["target_observation"]["hosted_gemma4_consensus_surface"] = "41"
    overlay = {
        **overlay_material,
        "evaluation_id": "maturitygemma4v1:evaluation:"
        + canonical_json_sha256_v1(overlay_material),
    }
    with pytest.raises(LoanMaturityNumericReconciliationV1Error, match="raw source binding"):
        build_loan_maturity_numeric_reconciliation_v1(source, challenger_overlays=[overlay])


def test_result_tamper_is_rejected() -> None:
    result = build_loan_maturity_numeric_reconciliation_v1(_source(subtotal=["175", "150"]))
    result["metrics"]["independent_observed_equation_count"] = 99
    with pytest.raises(LoanMaturityNumericReconciliationV1Error, match="identity"):
        validate_loan_maturity_numeric_reconciliation_v1(result)
