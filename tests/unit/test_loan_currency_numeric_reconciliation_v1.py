from __future__ import annotations

import copy
import io

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation.family_first_visible_dash_glyph_evidence_v1 import (
    build_family_first_visible_dash_glyph_evidence_v1,
)
from bctc_ai.evaluation.loan_currency_numeric_reconciliation_v1 import (
    INPUT_FORMAT_VERSION,
    LoanCurrencyNumericReconciliationV1Error,
    build_loan_currency_numeric_reconciliation_v1,
    validate_loan_currency_numeric_reconciliation_replay_v1,
    validate_loan_currency_numeric_reconciliation_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _cell(cell_id: str, lane: int, surface: str | None, *, page: int = 7) -> dict:
    return {
        "bbox": [100 + lane * 100, 200, 180 + lane * 100, 230],
        "cell_id": cell_id,
        "crop_sha256": None,
        "lane_index": lane,
        "lane_type": "MONEY",
        "page_sequence": page,
        "ppocrv6_score": 0.99 if surface is not None else None,
        "ppocrv6_surface": surface,
        "sample_id": f"sample-{cell_id}" if surface is not None else None,
        "source_line_index": lane + 10 if surface is not None else None,
        "vietocr_surface": surface,
    }


def _row(role: str, surfaces: list[str | None]) -> dict:
    return {
        "cells": [_cell(f"{role}-{lane}", lane, surface) for lane, surface in enumerate(surfaces)],
        "label_surface": role,
        "role": role,
    }


def _source(
    *,
    mapped: list[list[str | None]] | None = None,
    core_total: list[str | None] | None = None,
    additional: tuple[list[str | None], list[list[str | None]]] | None = None,
    grand_total: list[str | None] | None = None,
) -> dict:
    mapped = mapped or [["100", "90"], ["20", "10"]]
    core_total = core_total or ["120", "100"]
    return {
        "additional_population": (
            None
            if additional is None
            else {
                "breakdown_rows": [
                    _row(role, surfaces)
                    for role, surfaces in zip(
                        ("DEFERRED_LC_VND", "DEFERRED_LC_FOREIGN"),
                        additional[1],
                        strict=True,
                    )
                ],
                "parent": _row("DEFERRED_LC_PRE_2024_GROUP", additional[0]),
            }
        ),
        "core_total": _row("CORE_TOTAL", core_total),
        "family_id": "LOAN_CURRENCY_CLASSIFICATION",
        "format_version": INPUT_FORMAT_VERSION,
        "grand_total": None if grand_total is None else _row("GRAND_TOTAL", grand_total),
        "lane_types": ["MONEY", "MONEY"],
        "mapped_rows": [
            _row(role, surfaces)
            for role, surfaces in zip(
                ("VND_LOANS", "FOREIGN_CURRENCY_AND_GOLD_LOANS"), mapped, strict=True
            )
        ],
        "period_axis": {"mode": "EXACT_DATE", "periods": ["CURRENT", "COMPARATIVE"]},
        "source_id": "test-loan-currency-graph",
        "unit_context": {"kind": "MILLION_VND", "mode": "LOCAL"},
    }


def _dash(cell: dict, role: str, character: str) -> dict:
    image = Image.new("RGB", (40, 20), "white")
    draw = ImageDraw.Draw(image)
    left = 11 + int(character) % 3
    draw.rectangle((left, 9, left + 15, 10), fill="black")
    payload = io.BytesIO()
    image.save(payload, format="PNG")
    crop_png_bytes = payload.getvalue()
    evidence = build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=crop_png_bytes)
    assert evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    return {
        "cell_id": cell["cell_id"],
        "crop_png_bytes": crop_png_bytes,
        "evidence": evidence,
        "lane_index": cell["lane_index"],
        "lane_type": "MONEY",
        "page_sequence": cell["page_sequence"],
        "region_id": f"region-{cell['cell_id']}",
        "role": role,
    }


def _candidate_pixels(*, multiple: bool = False, blank: bool = False) -> tuple[bytes, dict]:
    image = Image.new("RGB", (40, 20), "white")
    if not blank:
        draw = ImageDraw.Draw(image)
        for point in (
            (18, 8),
            (19, 8),
            (20, 8),
            (17, 9),
            (18, 9),
            (19, 9),
            (20, 9),
            (21, 9),
            (18, 10),
            (19, 10),
            (20, 10),
            (19, 11),
        ):
            draw.point(point, fill="black")
        if multiple:
            draw.rectangle((2, 2, 4, 4), fill="black")
    payload = io.BytesIO()
    image.save(payload, format="PNG")
    crop = payload.getvalue()
    return crop, build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=crop)


def _replay_material(
    cell: dict,
    role: str,
    *,
    admission: str,
    crop: bytes,
    evidence: dict,
    packet: str,
) -> dict:
    return {
        "admission_class": admission,
        "cell_id": cell["cell_id"],
        "crop_png_bytes": crop,
        "document_packet_id": packet,
        "evidence": evidence,
        "lane_index": cell["lane_index"],
        "lane_type": "MONEY",
        "overlay_evidence_id": f"overlay-{packet}",
        "page_sequence": cell["page_sequence"],
        "raw_classification": evidence["classification"],
        "region_id": f"region-{packet}-{cell['cell_id']}",
        "resolved_period": "COMPARATIVE" if cell["lane_index"] else "CURRENT",
        "role": role,
        "source_population_role": "DEFERRED_LC_PRE_2024_GROUP",
        "source_population_surface": "Deferred LC",
    }


def _bounded_pair(cell: dict, role: str) -> dict:
    candidate_crop, candidate_evidence = _candidate_pixels()
    assert candidate_evidence["classification"] == "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE"
    candidate = _replay_material(
        cell,
        role,
        admission="BOUNDED_CENTERED_HIGH_FILL_HORIZONTAL_MARK_CANDIDATE",
        crop=candidate_crop,
        evidence=candidate_evidence,
        packet="candidate-packet",
    )
    peer_cell = copy.deepcopy(cell)
    peer_cell["cell_id"] = "external-direct-peer"
    direct = _dash(peer_cell, role, "3")
    peer = _replay_material(
        peer_cell,
        role,
        admission="DIRECT_VISIBLE_HORIZONTAL_DASH",
        crop=direct["crop_png_bytes"],
        evidence=direct["evidence"],
        packet="peer-packet",
    )
    material = {
        "candidate_admission_class": candidate["admission_class"],
        "candidate_cell_id": candidate["cell_id"],
        "candidate_evidence_id": candidate["evidence"]["evidence_id"],
        "candidate_overlay_evidence_id": candidate["overlay_evidence_id"],
        "candidate_packet_id": candidate["document_packet_id"],
        "candidate_raw_classification": candidate["raw_classification"],
        "candidate_region_id": candidate["region_id"],
        "column_ordinal": candidate["lane_index"],
        "peer_cell_id": peer["cell_id"],
        "peer_evidence_id": peer["evidence"]["evidence_id"],
        "peer_overlay_evidence_id": peer["overlay_evidence_id"],
        "peer_packet_id": peer["document_packet_id"],
        "peer_raw_classification": peer["raw_classification"],
        "peer_region_id": peer["region_id"],
        "resolved_period": candidate["resolved_period"],
        "role": role,
        "source_population_role": candidate["source_population_role"],
    }
    pair = {
        **material,
        "pair_binding_id": "lcdashv1:pair:" + canonical_json_sha256_v1(material),
    }
    return {"candidate": candidate, "pair_binding": pair, "peer": peer}


def _rehash_pair(pair: dict) -> None:
    material = copy.deepcopy(pair["pair_binding"])
    material.pop("pair_binding_id")
    pair["pair_binding"]["pair_binding_id"] = "lcdashv1:pair:" + canonical_json_sha256_v1(material)


def _hostile_mark_pixels(kind: str) -> tuple[bytes, dict]:
    image = Image.new("RGB", (40, 20), "white")
    draw = ImageDraw.Draw(image)
    if kind == "vertical_digit_one":
        draw.rectangle((19, 5, 21, 15), fill="black")
    elif kind == "dot":
        draw.rectangle((18, 8, 21, 11), fill="black")
    elif kind == "comma_tail":
        draw.rectangle((18, 7, 21, 11), fill="black")
        draw.line((20, 11, 18, 14), fill="black", width=2)
    elif kind == "long_table_rule":
        draw.rectangle((2, 9, 37, 10), fill="black")
    elif kind == "off_center":
        for point in (
            (5, 8),
            (6, 8),
            (7, 8),
            (4, 9),
            (5, 9),
            (6, 9),
            (7, 9),
            (8, 9),
            (5, 10),
            (6, 10),
            (7, 10),
            (6, 11),
        ):
            draw.point(point, fill="black")
    else:  # pragma: no cover - test helper contract
        raise AssertionError(kind)
    payload = io.BytesIO()
    image.save(payload, format="PNG")
    crop = payload.getvalue()
    return crop, build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=crop)


def test_core_currency_rows_are_exact_and_replayable() -> None:
    source = _source()
    result = build_loan_currency_numeric_reconciliation_v1(source)
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["metrics"]["mapped_money_cell_count"] == 4
    assert result["metrics"]["independent_observed_equation_count"] == 2
    assert result["metrics"]["source_only_additional_row_count"] == 0
    assert validate_loan_currency_numeric_reconciliation_v1(result) == result
    assert validate_loan_currency_numeric_reconciliation_replay_v1(result, source) == result


def test_source_only_deferred_lc_closes_six_equations_with_typed_dash_pixels() -> None:
    source = _source(
        additional=(["10", None], [["7", None], ["3", None]]),
        grand_total=["130", "100"],
    )
    population = source["additional_population"]
    overlays = [
        _dash(population["parent"]["cells"][1], "DEFERRED_LC_PRE_2024_GROUP", "4"),
        _dash(population["breakdown_rows"][0]["cells"][1], "DEFERRED_LC_VND", "5"),
        _dash(population["breakdown_rows"][1]["cells"][1], "DEFERRED_LC_FOREIGN", "6"),
    ]
    result = build_loan_currency_numeric_reconciliation_v1(source, visible_dash_evidence=overlays)
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["metrics"]["independent_observed_equation_count"] == 6
    assert result["metrics"]["source_only_additional_row_count"] == 3
    assert result["metrics"]["source_only_additional_money_cell_count"] == 6
    assert result["metrics"]["visible_dash_zero_cell_count"] == 3
    assert result["additional_population"]["parent"]["cells"][1]["selected_value"] == 0
    assert (
        validate_loan_currency_numeric_reconciliation_replay_v1(
            result, source, visible_dash_evidence=overlays
        )
        == result
    )


def test_blank_is_not_zero_and_accounting_never_backsolves() -> None:
    source = _source(
        additional=(["10", None], [["7", None], ["3", None]]),
        grand_total=["130", "100"],
    )
    result = build_loan_currency_numeric_reconciliation_v1(source)
    parent = result["additional_population"]["parent"]["cells"][1]
    assert result["status"] == "UNRESOLVED"
    assert parent["selected_value"] is None
    assert parent["selection_mode"] == "UNRESOLVED_NO_PRIMARY_OR_TYPED_DASH_EVIDENCE"
    assert result["metrics"]["independent_observed_equation_count"] == 4


def test_ppocr_primary_and_vietocr_disagreement_are_both_retained() -> None:
    source = _source()
    cell = source["mapped_rows"][0]["cells"][0]
    cell["vietocr_surface"] = "99"
    result = build_loan_currency_numeric_reconciliation_v1(source)
    resolved = result["mapped_rows"][0]["cells"][0]
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert resolved["ppocrv6_surface"] == "100"
    assert resolved["vietocr_surface"] == "99"
    assert resolved["selected_value"] == 100
    assert result["metrics"]["ppocrv6_vietocr_numeric_disagreement_count"] == 1


def test_printed_total_mismatch_vetoes_without_mutating_source_values() -> None:
    result = build_loan_currency_numeric_reconciliation_v1(_source(core_total=["121", "100"]))
    assert result["status"] == "UNRESOLVED"
    assert result["core_total"]["cells"][0]["selected_value"] == 121
    assert result["accounting_checks"][0]["status"] == "VETOED_OBSERVED_EQUATION"


def test_unbound_or_numeric_dash_overlay_fails_closed() -> None:
    source = _source()
    overlay = _dash(source["mapped_rows"][0]["cells"][0], "VND_LOANS", "7")
    with pytest.raises(LoanCurrencyNumericReconciliationV1Error, match="raw source cell"):
        build_loan_currency_numeric_reconciliation_v1(source, visible_dash_evidence=[overlay])

    source = _source(
        additional=(["10", None], [["7", None], ["3", None]]), grand_total=["130", "100"]
    )
    overlay = _dash(
        source["additional_population"]["parent"]["cells"][1],
        "DEFERRED_LC_PRE_2024_GROUP",
        "8",
    )
    overlay["cell_id"] = "not-a-cell"
    with pytest.raises(LoanCurrencyNumericReconciliationV1Error, match="duplicate or unused"):
        build_loan_currency_numeric_reconciliation_v1(source, visible_dash_evidence=[overlay])


def test_self_rehashed_forged_dash_cannot_become_zero() -> None:
    source = _source(
        additional=(["10", None], [["7", None], ["3", None]]),
        grand_total=["130", "100"],
    )
    cell = source["additional_population"]["parent"]["cells"][1]
    overlay = _dash(cell, "DEFERRED_LC_PRE_2024_GROUP", "9")
    forged = copy.deepcopy(overlay)
    forged["evidence"]["authority"]["mapping_authority"] = True
    material = copy.deepcopy(forged["evidence"])
    material.pop("evidence_id")
    forged["evidence"]["evidence_id"] = "ffvdgev1:evidence:" + canonical_json_sha256_v1(material)
    with pytest.raises(LoanCurrencyNumericReconciliationV1Error, match="pixel replay failed"):
        build_loan_currency_numeric_reconciliation_v1(source, visible_dash_evidence=[forged])


def test_rehashed_selected_value_tamper_is_rejected_semantically() -> None:
    result = build_loan_currency_numeric_reconciliation_v1(_source())
    tampered = copy.deepcopy(result)
    tampered["mapped_rows"][0]["cells"][0]["selected_value"] = 99
    material = copy.deepcopy(tampered)
    material.pop("result_id")
    tampered["result_id"] = "lcnrv1:result:" + canonical_json_sha256_v1(material)
    with pytest.raises(LoanCurrencyNumericReconciliationV1Error, match="selection drifted"):
        validate_loan_currency_numeric_reconciliation_v1(tampered)


def test_bounded_high_fill_mark_needs_peer_then_accounting_corroborates_zero() -> None:
    source = _source(
        additional=(["10", "0"], [["7", "0"], ["3", None]]),
        grand_total=["130", "100"],
    )
    cell = source["additional_population"]["breakdown_rows"][1]["cells"][1]
    pair = _bounded_pair(cell, "DEFERRED_LC_FOREIGN")
    result = build_loan_currency_numeric_reconciliation_v1(
        source, bounded_dash_peer_evidence=[pair]
    )
    resolved = result["additional_population"]["breakdown_rows"][1]["cells"][1]
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert resolved["selected_value"] == 0
    assert resolved["evidence_ref"]["classification"] != "VISIBLE_HORIZONTAL_DASH_GLYPH"
    assert result["metrics"]["direct_visible_dash_zero_cell_count"] == 0
    assert result["metrics"]["bounded_paired_dash_zero_cell_count"] == 1
    assert (
        validate_loan_currency_numeric_reconciliation_replay_v1(
            result, source, bounded_dash_peer_evidence=[pair]
        )
        == result
    )


def test_bounded_pair_is_pixel_admitted_before_accounting_veto() -> None:
    source = _source(
        additional=(["10", "0"], [["7", "0"], ["3", None]]),
        grand_total=["130", "100"],
    )
    cell = source["additional_population"]["breakdown_rows"][1]["cells"][1]
    pair = _bounded_pair(cell, "DEFERRED_LC_FOREIGN")
    exact = build_loan_currency_numeric_reconciliation_v1(source, bounded_dash_peer_evidence=[pair])
    source["grand_total"]["cells"][1]["ppocrv6_surface"] = "101"
    source["grand_total"]["cells"][1]["vietocr_surface"] = "101"
    vetoed = build_loan_currency_numeric_reconciliation_v1(
        source, bounded_dash_peer_evidence=[pair]
    )
    assert exact["bounded_dash_pair_evidence_refs"] == vetoed["bounded_dash_pair_evidence_refs"]
    assert vetoed["status"] == "UNRESOLVED"
    assert vetoed["additional_population"]["breakdown_rows"][1]["cells"][1]["selected_value"] == 0
    assert vetoed["metrics"]["bounded_paired_dash_zero_cell_count"] == 1


def test_bounded_candidate_without_one_direct_peer_fails_closed() -> None:
    source = _source(
        additional=(["10", "0"], [["7", "0"], ["3", None]]),
        grand_total=["130", "100"],
    )
    cell = source["additional_population"]["breakdown_rows"][1]["cells"][1]
    pair = _bounded_pair(cell, "DEFERRED_LC_FOREIGN")
    pair["peer"] = copy.deepcopy(pair["candidate"])
    pair["peer"]["cell_id"] = pair["pair_binding"]["peer_cell_id"]
    with pytest.raises(LoanCurrencyNumericReconciliationV1Error, match="admission"):
        build_loan_currency_numeric_reconciliation_v1(source, bounded_dash_peer_evidence=[pair])


@pytest.mark.parametrize("multiple", [False, True])
def test_blank_or_multiple_component_candidate_cannot_become_zero(multiple: bool) -> None:
    source = _source(
        additional=(["10", "0"], [["7", "0"], ["3", None]]),
        grand_total=["130", "100"],
    )
    cell = source["additional_population"]["breakdown_rows"][1]["cells"][1]
    pair = _bounded_pair(cell, "DEFERRED_LC_FOREIGN")
    crop, evidence = _candidate_pixels(multiple=multiple, blank=not multiple)
    pair["candidate"]["crop_png_bytes"] = crop
    pair["candidate"]["evidence"] = evidence
    pair["candidate"]["raw_classification"] = evidence["classification"]
    with pytest.raises(LoanCurrencyNumericReconciliationV1Error, match="candidate pixel"):
        build_loan_currency_numeric_reconciliation_v1(source, bounded_dash_peer_evidence=[pair])


@pytest.mark.parametrize(
    "kind",
    ["vertical_digit_one", "dot", "comma_tail", "long_table_rule", "off_center"],
)
def test_digit_punctuation_rule_or_off_center_mark_cannot_become_zero(kind: str) -> None:
    source = _source(
        additional=(["10", "0"], [["7", "0"], ["3", None]]),
        grand_total=["130", "100"],
    )
    cell = source["additional_population"]["breakdown_rows"][1]["cells"][1]
    pair = _bounded_pair(cell, "DEFERRED_LC_FOREIGN")
    crop, evidence = _hostile_mark_pixels(kind)
    pair["candidate"]["crop_png_bytes"] = crop
    pair["candidate"]["evidence"] = evidence
    pair["candidate"]["raw_classification"] = evidence["classification"]
    with pytest.raises(LoanCurrencyNumericReconciliationV1Error, match="candidate pixel"):
        build_loan_currency_numeric_reconciliation_v1(source, bounded_dash_peer_evidence=[pair])


def test_bool_is_not_an_integer_lane_or_page_in_raw_and_direct_bindings() -> None:
    source = _source()
    source["mapped_rows"][0]["cells"][0]["lane_index"] = False
    with pytest.raises(LoanCurrencyNumericReconciliationV1Error, match="typed-lane"):
        build_loan_currency_numeric_reconciliation_v1(source)

    source = _source(
        additional=(["10", None], [["7", None], ["3", None]]),
        grand_total=["130", "100"],
    )
    cell = source["additional_population"]["parent"]["cells"][1]
    direct = _dash(cell, "DEFERRED_LC_PRE_2024_GROUP", "4")
    direct["lane_index"] = True
    with pytest.raises(LoanCurrencyNumericReconciliationV1Error, match="typed lane/page"):
        build_loan_currency_numeric_reconciliation_v1(source, visible_dash_evidence=[direct])
    direct = _dash(cell, "DEFERRED_LC_PRE_2024_GROUP", "4")
    direct["page_sequence"] = True
    with pytest.raises(LoanCurrencyNumericReconciliationV1Error, match="typed lane/page"):
        build_loan_currency_numeric_reconciliation_v1(source, visible_dash_evidence=[direct])


@pytest.mark.parametrize(
    ("target", "field", "value", "message"),
    [
        ("candidate", "lane_index", True, "geometry axis"),
        ("candidate", "page_sequence", True, "geometry axis"),
        ("peer", "lane_index", True, "geometry axis"),
        ("peer", "page_sequence", True, "geometry axis"),
        ("pair_binding", "column_ordinal", True, "pair lane"),
    ],
)
def test_bool_is_not_an_integer_in_bounded_pair_axes(
    target: str, field: str, value: object, message: str
) -> None:
    source = _source(
        additional=(["10", "0"], [["7", "0"], ["3", None]]),
        grand_total=["130", "100"],
    )
    cell = source["additional_population"]["breakdown_rows"][1]["cells"][1]
    pair = _bounded_pair(cell, "DEFERRED_LC_FOREIGN")
    pair[target][field] = value
    if target == "pair_binding":
        _rehash_pair(pair)
    with pytest.raises(LoanCurrencyNumericReconciliationV1Error, match=message):
        build_loan_currency_numeric_reconciliation_v1(source, bounded_dash_peer_evidence=[pair])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("role", "DEFERRED_LC_VND"),
        ("resolved_period", "WRONG_PERIOD"),
        ("candidate_packet_id", "peer-packet"),
        ("candidate_region_id", "wrong-region"),
        ("candidate_cell_id", "wrong-cell"),
    ],
)
def test_self_rehashed_pair_field_mutation_fails_exact_join(field: str, value: str) -> None:
    source = _source(
        additional=(["10", "0"], [["7", "0"], ["3", None]]),
        grand_total=["130", "100"],
    )
    cell = source["additional_population"]["breakdown_rows"][1]["cells"][1]
    pair = _bounded_pair(cell, "DEFERRED_LC_FOREIGN")
    pair["pair_binding"][field] = value
    _rehash_pair(pair)
    with pytest.raises(LoanCurrencyNumericReconciliationV1Error):
        build_loan_currency_numeric_reconciliation_v1(source, bounded_dash_peer_evidence=[pair])
