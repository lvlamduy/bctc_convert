from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/build_annual_2025_other_activity_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_other_activity_8bank_codex_verified_mapping_v1",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    built = builder.build_live_annual_2025_other_activity_8bank_codex_verified_mapping_v1()
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert builder.same_typed_json_v1(built, persisted)
    return built


def test_exact_annual_denominator_and_unique_region_per_document(
    result: dict[str, object],
) -> None:
    assert result["result_id"] == builder.EXPECTED_RESULT_ID
    assert result["metrics"] == builder._EXPECTED_METRICS
    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert [trial["page_span"] for trial in result["trials"]] == list(
        builder._EXPECTED_PAGES.values()
    )
    assert [len(trial["verified_mappings"]) for trial in result["trials"]] == list(
        builder._EXPECTED_MAPPING_COUNTS.values()
    )
    assert all(
        trial["status"] == "VERIFIED_BY_CODEX"
        and trial["whole_document_uniqueness"]
        == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        for trial in result["trials"]
    )


def test_controlled_catchall_aggregations_bind_visible_components(
    result: dict[str, object],
) -> None:
    expected = {
        ("ACB", "INCOME_OTHER"): (1239, 1_144_358, 525_194, 2),
        ("ACB", "EXPENSE_OTHER"): (1246, -1_205_407, -642_495, 2),
        ("VPB", "INCOME_ASSET_DISPOSAL"): (1231, 141_510, 35_998, 2),
        ("VPB", "INCOME_OTHER"): (1239, 1_313_885, 176_672, 2),
        ("VPB", "EXPENSE_ASSET_DISPOSAL"): (1242, -117_591, -27_835, 2),
        ("HDB", "EXPENSE_OTHER"): (1246, -249_122, -136_076, 2),
    }
    for (code, role), (report_norm_id, current, comparative, component_count) in expected.items():
        trial = next(item for item in result["trials"] if item["document_provenance"] == code)
        mapping = next(item for item in trial["verified_mappings"] if item["role"] == role)
        assert mapping["schema_binding"]["report_norm_id"] == report_norm_id
        values = {item["axis_role"]: item for item in mapping["values"]}
        assert values["CURRENT_PERIOD"]["normalized_value"] == current
        assert values["COMPARATIVE_PERIOD"]["normalized_value"] == comparative
        assert all(len(item["component_evidence"]) == component_count for item in values.values())
        assert all(
            item["source_numeric_challenger_status"]
            == "CONTROLLED_SUM_OF_AUTHENTICATED_SOURCE_NUMERIC_LINES"
            for item in values.values()
        )


def test_all_visible_accounting_equations_close_without_open_rows(
    result: dict[str, object],
) -> None:
    equations = [
        equation
        for trial in result["trials"]
        for equation in trial["verified_accounting_equations"]
    ]
    assert len(equations) == 48
    assert all(
        equation["status"] == "VERIFIED_EXACT"
        and equation["computed_value"] == equation["visible_total"]
        for equation in equations
    )
    assert all(not trial["verified_source_only_rows"] for trial in result["trials"])
    assert result["metrics"]["fresh_vietocr_numeric_disagreement_count"] == 0


def test_vib_provider_order_variant_keeps_explicit_labels_and_values(
    result: dict[str, object],
) -> None:
    vib = next(trial for trial in result["trials"] if trial["document_provenance"] == "VIB")
    total = next(mapping for mapping in vib["verified_mappings"] if mapping["role"] == "TOTAL")
    other = next(
        mapping for mapping in vib["verified_mappings"] if mapping["role"] == "EXPENSE_OTHER"
    )
    assert total["topology"] == "PROVIDER_ORDER_NUMBERS_PRECEDE_EXPLICIT_NET_LABEL"
    assert other["topology"] == "PROVIDER_ORDER_NUMBERS_PRECEDE_LABEL"
    assert [item["line_index"] for item in total["label_evidence"]] == [86]
    assert [item["source_line_index"] for item in total["values"]] == [85, 84]
    assert [item["line_index"] for item in other["label_evidence"]] == [83]
    assert [item["source_line_index"] for item in other["values"]] == [82, 81]


def test_schema_bindings_use_current_live_other_activity_positions(
    result: dict[str, object],
) -> None:
    bindings = {
        mapping["schema_binding"]["report_norm_id"]: mapping["schema_binding"]
        for trial in result["trials"]
        for mapping in trial["verified_mappings"]
    }
    assert bindings[6029]["display_order"] == 792
    assert bindings[1229]["display_order"] == 794
    assert bindings[1246]["display_order"] == 811
    assert bindings[1239]["schema_parent_report_norm_id"] == 1229
    assert bindings[1246]["schema_parent_report_norm_id"] == 1240


def test_public_validator_rejects_coordinated_numeric_tamper(
    result: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(result)
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder.base.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        builder,
        "build_live_annual_2025_other_activity_8bank_codex_verified_mapping_v1",
        lambda: result,
    )
    with pytest.raises(
        builder.Annual2025OtherActivity8BankError,
        match="does not replay exactly",
    ):
        builder.validate_live_annual_2025_other_activity_8bank_codex_verified_mapping_v1(forged)
