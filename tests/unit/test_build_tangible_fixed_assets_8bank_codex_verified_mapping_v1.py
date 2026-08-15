from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_tangible_fixed_assets_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_tangible_fixed_assets_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> tuple[tuple[object, ...], dict[str, object]]:
    inputs = builder._live_inputs()
    result = builder.build_tangible_fixed_assets_8bank_codex_verified_mapping_v1(*inputs)
    return inputs, result


def test_live_result_has_three_verified_regions_and_five_bound_absences(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    _, result = live

    assert result["metrics"] == {
        "accounting_equation_count": 12,
        "confirmed_bound_report_absence_count": 5,
        "document_count": 8,
        "mapping_verified_count": 35,
        "q1_source_period_caveat_document_count": 1,
        "rotated_original_source_numeric_disagreement_count": 4,
        "rotated_ppocrv6_verified_value_count": 10,
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


def test_only_current_period_rows_are_mapped_and_mbb_comparative_is_control(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    _, result = live
    mbb = result["trials"][1]
    vpb = result["trials"][2]

    assert mbb["page_sequence"] == 37
    assert mbb["comparative_control_page"] == 38
    assert mbb["source_period"] == "2026-06-30"
    assert all(mapping["value"]["source_line_index"] < 96 for mapping in mbb["mappings"])
    assert vpb["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"


def test_vib_rotation_uses_vietocr_for_text_and_ppocrv6_for_numbers(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    _, result = live
    vib = result["trials"][7]

    assert vib["owner_evidence"]["semantic_text_source"] == (
        "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE"
    )
    assert all(
        item["value"]["rotated_ppocrv6_challenger_status"]
        == "ROTATED_PPOCRV6_MATCHED_VISIBLE_PIXEL"
        for item in vib["mappings"]
    )
    assert (
        sum(
            item["value"]["source_numeric_challenger_status"]
            == "ORIGINAL_ROTATED_SOURCE_OCR_DISAGREED_RESCUED_BY_ROTATED_PPOCRV6"
            for item in vib["mappings"]
        )
        == 4
    )
    assert all(
        item["value"]["normalized_value"]
        == builder._money(item["value"]["rotated_ppocrv6_challenger"])
        for item in vib["mappings"]
    )


def test_all_accounting_equations_close_without_repair(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    _, result = live

    equations = [equation for trial in result["trials"] for equation in trial["equations"]]
    assert len(equations) == 12
    assert all(equation["status"] == "CORROBORATED_EXACT" for equation in equations)
    assert all(equation["computed_total"] == equation["visible_total"] for equation in equations)


def test_schema_is_reused_without_family_specific_new_ids(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    _, result = live
    mapped_ids = {
        mapping["report_norm_id"] for trial in result["trials"] for mapping in trial["mappings"]
    }

    assert mapped_ids == set(builder._SCHEMA_EXPECTED)
    assert all(
        mapping["schema_binding"]["report_norm_id"] == mapping["report_norm_id"]
        for trial in result["trials"]
        for mapping in trial["mappings"]
    )


def test_exact_replay_rejects_coordinated_mapping_promotion(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    inputs, result = live
    forged = copy.deepcopy(result)
    forged["trials"][1]["mappings"][0]["final_status"] = "CANONICAL_EXPORT_READY"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0069:result:" + builder.canonical_json_sha256_v1(material)

    with pytest.raises(
        builder.TangibleFixedAssets8BankCodexVerifiedMappingV1Error,
        match="does not replay exactly",
    ):
        builder.validate_tangible_fixed_assets_8bank_codex_verified_mapping_replay_v1(
            forged, *inputs
        )


def test_fixed_review_tamper_is_rejected_before_mapping(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    inputs, _ = live
    poisoned = list(inputs)
    review = copy.deepcopy(poisoned[3])
    review["documents"][1]["mappings"][0]["report_norm_id"] = 871
    poisoned[3] = review

    with pytest.raises(
        builder.TangibleFixedAssets8BankCodexVerifiedMappingV1Error,
        match="differs from the fixed ledger",
    ):
        builder.build_tangible_fixed_assets_8bank_codex_verified_mapping_v1(*poisoned)


def test_persisted_review_and_result_equal_live_bytes(
    live: tuple[tuple[object, ...], dict[str, object]],
) -> None:
    _, result = live
    persisted_review = json.loads((builder.PROJECT_ROOT / builder.REVIEW_PATH).read_text("utf-8"))
    persisted_result = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text("utf-8"))

    assert persisted_review == builder._review_blueprint()
    assert persisted_result == result
