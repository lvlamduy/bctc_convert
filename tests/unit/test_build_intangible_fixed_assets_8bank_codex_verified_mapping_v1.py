from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/build_intangible_fixed_assets_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_intangible_fixed_assets_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> tuple[tuple[object, ...], dict[str, object]]:
    inputs = builder._live_inputs()
    result = builder.build_intangible_fixed_assets_8bank_codex_verified_mapping_v1(*inputs)
    return inputs, result


def test_live_result_has_three_verified_regions_and_five_bound_absences(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    _, result = live

    assert result["metrics"] == {
        "accounting_equation_count": 12,
        "confirmed_bound_report_absence_count": 5,
        "document_count": 8,
        "mapping_verified_count": 32,
        "open_review_item_count": 0,
        "q1_source_period_caveat_document_count": 1,
        "verified_present_document_count": 3,
    }
    assert [trial["document_provenance"] for trial in result["trials"] if trial["mappings"]] == [
        "MBB",
        "VPB",
        "VIB",
    ]
    assert [
        trial["document_provenance"]
        for trial in result["trials"]
        if trial["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
    ] == ["ACB", "HDB", "VCB", "CTG", "BID"]


def test_current_period_only_and_comparative_control_are_explicit(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    _, result = live
    mbb = result["trials"][1]
    vpb = result["trials"][2]

    assert mbb["page_sequence"] == 39
    assert mbb["comparative_control"]["page_sequence"] == 40
    assert mbb["source_period"] == "2026-06-30"
    assert vpb["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"


def test_fully_amortized_still_in_use_maps_only_where_visibly_disclosed(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    _, result = live
    mapped_6069 = [
        (trial["document_provenance"], mapping["value"]["normalized_value"])
        for trial in result["trials"]
        for mapping in trial["mappings"]
        if mapping["report_norm_id"] == 6069
    ]

    assert mapped_6069 == [("VPB", 1_219_881), ("VIB", 314_667)]


def test_all_accounting_equations_close_without_repair(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    _, result = live
    equations = [equation for trial in result["trials"] for equation in trial["equations"]]

    assert len(equations) == 12
    assert all(equation["status"] == "CORROBORATED_EXACT" for equation in equations)
    assert all(equation["computed_total"] == equation["visible_total"] for equation in equations)


def test_every_mapping_is_live_schema_bound_and_verified(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    _, result = live
    mappings = [mapping for trial in result["trials"] for mapping in trial["mappings"]]

    assert {mapping["report_norm_id"] for mapping in mappings} <= set(builder._SCHEMA_EXPECTED)
    assert all(mapping["final_status"] == "VERIFIED_BY_CODEX" for mapping in mappings)
    assert all(
        mapping["schema_binding"]["report_norm_id"] == mapping["report_norm_id"]
        for mapping in mappings
    )


def test_exact_replay_rejects_coordinated_mapping_promotion(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    inputs, result = live
    forged = copy.deepcopy(result)
    forged["trials"][1]["mappings"][0]["final_status"] = "CANONICAL_EXPORT_READY"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0071:result:" + builder.canonical_json_sha256_v1(material)

    with pytest.raises(
        builder.IntangibleFixedAssets8BankCodexVerifiedMappingV1Error,
        match="mapping status drifted|does not replay exactly",
    ):
        builder.validate_intangible_fixed_assets_8bank_codex_verified_mapping_replay_v1(
            forged, *inputs
        )


def test_fixed_review_tamper_is_rejected_before_mapping(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    inputs, _ = live
    poisoned = list(inputs)
    review = copy.deepcopy(poisoned[3])
    review["documents"][1]["mappings"][0]["report_norm_id"] = 916
    poisoned[3] = review

    with pytest.raises(
        builder.IntangibleFixedAssets8BankCodexVerifiedMappingV1Error,
        match="pixel review drifted|differs from the fixed ledger",
    ):
        builder.build_intangible_fixed_assets_8bank_codex_verified_mapping_v1(*poisoned)


def test_persisted_review_and_result_equal_live_bytes(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    _, result = live
    persisted_review = json.loads((builder.PROJECT_ROOT / builder.REVIEW_PATH).read_text("utf-8"))
    persisted_result = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text("utf-8"))

    assert persisted_review == builder._review_blueprint()
    assert persisted_result == result
