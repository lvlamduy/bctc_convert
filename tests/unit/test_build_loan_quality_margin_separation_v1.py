from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_loan_quality_margin_separation_v1.py"
_SPEC = importlib.util.spec_from_file_location("build_loan_quality_margin_separation_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
quality = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = quality
_SPEC.loader.exec_module(quality)


def _persisted() -> dict[str, object]:
    return json.loads((quality.PROJECT_ROOT / quality.OUTPUT_PATH).read_text())


def _by_bank(result: dict[str, object]) -> dict[str, dict[str, object]]:
    return {trial["bank_provenance"]: trial for trial in result["trials"]}


def _mapping(trial: dict[str, object], report_norm_id: int) -> dict[str, object]:
    matches = [
        mapping
        for mapping in trial["normalized_mappings"]
        if mapping["report_norm_id"] == report_norm_id
    ]
    assert len(matches) == 1
    return matches[0]


def test_bounded_context_reuses_registered_1944_under_746() -> None:
    result = quality._validate(_persisted())
    context = result["schema_context"]

    assert context["standalone_item"] == {
        "canonical_name": "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
        "hierarchy_level": 2,
        "mapping_eligible_in_this_bounded_context": True,
        "parent_report_norm_id": 746,
        "report_norm_id": 1944,
        "template_identity_reused": True,
    }
    assert context["included_source_disclosure"]["report_norm_id"] == 5746
    assert context["included_source_disclosure"]["mapping_output_authority"] is False
    assert result["metrics"] == {
        "accounting_equation_count": 18,
        "adjusted_standard_grade_bank_count": 1,
        "document_count": 8,
        "double_count_count": 0,
        "normalized_mapping_count": 43,
        "source_5746_bridge_count": 1,
        "standalone_margin_mapping_count": 3,
        "unobserved_margin_bank_count": 5,
        "visible_normalized_period_cell_count": 86,
    }


def test_standalone_and_included_presentations_normalize_without_double_count() -> None:
    by_bank = _by_bank(quality._validate(_persisted()))

    for code, margin_values in {
        "ACB": [20644553, 17340705],
        "VPB": [36278045, 34093219],
    }.items():
        trial = by_bank[code]
        assert trial["presentation_mode"] == "STANDALONE_AFTER_FIVE_GRADES"
        standard = _mapping(trial, 747)
        assert all(
            value["source_reported_value"] == value["normalized_value"]
            for value in standard["values"]
        )
        margin = _mapping(trial, 1944)
        assert [value["normalized_value"] for value in margin["values"]] == margin_values
        assert trial["source_5746_bridge"] is None

    mbb = by_bank["MBB"]
    assert mbb["presentation_mode"] == "INCLUDED_IN_747_VIA_5746"
    standard = _mapping(mbb, 747)
    assert [value["source_reported_value"] for value in standard["values"]] == [
        1197767532,
        1059781834,
    ]
    assert [value["normalized_value"] for value in standard["values"]] == [
        1180939478,
        1044741249,
    ]
    assert [value["normalized_value"] for value in _mapping(mbb, 1944)["values"]] == [
        16828054,
        15040585,
    ]
    assert mbb["source_5746_bridge"]["mapping_output_authority"] is False
    assert all(mapping["report_norm_id"] != 5746 for mapping in mbb["normalized_mappings"])
    assert all(equation["status"] == "CORROBORATED" for equation in mbb["normalization_equations"])


def test_unobserved_banks_do_not_synthesize_margin_mapping() -> None:
    by_bank = _by_bank(quality._validate(_persisted()))
    for code in ("HDB", "VCB", "CTG", "BID", "VIB"):
        trial = by_bank[code]
        assert trial["presentation_mode"] == "NOT_OBSERVED_DO_NOT_SYNTHESIZE"
        assert [mapping["report_norm_id"] for mapping in trial["normalized_mappings"]] == [
            747,
            748,
            749,
            750,
            751,
        ]


def test_presentation_classifier_does_not_route_on_bank_or_page() -> None:
    source, _, _ = quality._load_inputs()
    standalone = copy.deepcopy(source["trials"][0])
    standalone["bank_provenance"] = "SYNTHETIC-A"
    standalone["physical_page"] = 999
    included = copy.deepcopy(source["trials"][1])
    included["bank_provenance"] = "SYNTHETIC-B"
    included["physical_page"] = 1

    assert quality._trial(standalone)["presentation_mode"] == "STANDALONE_AFTER_FIVE_GRADES"
    assert quality._trial(included)["presentation_mode"] == "INCLUDED_IN_747_VIA_5746"


def test_typed_and_coordinated_rehash_tamper_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forged = _persisted()
    forged["metrics"]["double_count_count"] = False
    with pytest.raises(
        quality.LoanQualityMarginSeparationV1Error,
        match="identity or metrics drifted",
    ):
        quality._validate(forged)

    persisted = _persisted()
    forged = copy.deepcopy(persisted)
    forged["trials"][1]["normalized_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0067b:result:" + quality.canonical_json_sha256_v1(material)
    monkeypatch.setattr(quality, "build_live_loan_quality_margin_separation_v1", lambda: persisted)
    with pytest.raises(
        quality.LoanQualityMarginSeparationV1Error,
        match="does not exact-replay",
    ):
        quality.validate_loan_quality_margin_separation_replay_v1(forged)
