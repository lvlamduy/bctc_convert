from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


@pytest.fixture(scope="module")
def module(project_root: Path) -> ModuleType:
    path = (
        project_root / "scripts/experiments/"
        "build_annual_2025_consolidated_segment_report_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_consolidated_segment_report_test_target_v1"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    target = importlib.util.module_from_spec(spec)
    sys.modules[name] = target
    spec.loader.exec_module(target)
    return target


@pytest.fixture(scope="module")
def live(module: ModuleType) -> dict:
    return (
        module.build_live_annual_2025_consolidated_segment_report_8bank_codex_verified_mapping_v1()
    )


def _trial(live: dict, bank: str) -> dict:
    return next(item for item in live["trials"] if item["bank_code"] == bank)


def test_whole_pdf_unique_region_and_related_party_skip(live: dict) -> None:
    assert [item["bank_code"] for item in live["trials"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [item["evidence_page_sequence"] for item in live["trials"]] == [
        [95, 96, 97, 98, 99],
        [83, 84, 85, 86, 87, 88, 89, 90],
        [95, 96, 97],
        [60, 61],
        [71, 72],
        [81, 82, 83, 84],
        [36, 37, 38],
        [61, 62],
    ]
    assert all(item["scan"]["page_count_scanned"] > 50 for item in live["trials"])
    assert live["metrics"]["document_unique_region_count"] == 8
    assert live["metrics"]["related_party_family_processed_count"] == 0
    assert live["authority"]["related_party_root_5750_skipped_by_project_owner"] is True
    assert all(
        binding["report_norm_id"] != 5750
        for trial in live["trials"]
        for binding in trial["verified_structure_bindings"]
    )
    assert all(
        assignment["report_norm_id"] != 5750
        for trial in live["trials"]
        for assignment in trial["verified_numeric_assignments"]
    )
    assert 82 not in _trial(live, "MBB")["evidence_page_sequence"]


def test_exact_structure_numeric_equations_and_absences(live: dict) -> None:
    assert live["schema_family"]["first_report_norm_id"] == 5762
    assert live["schema_family"]["last_report_norm_id"] == 5848
    assert live["metrics"] == {
        "accounting_equation_verified_count": 43,
        "blank_cell_preserved_count": 2,
        "detailed_business_report_absence_count": 2,
        "detailed_geographic_report_absence_count": 1,
        "document_count": 8,
        "document_unique_region_count": 8,
        "numeric_assignment_verified_count": 208,
        "related_party_family_processed_count": 0,
        "source_only_equation_component_count": 32,
        "source_only_open_item_count": 17,
        "structure_binding_verified_count": 73,
    }
    assert _trial(live, "VPB")["bounded_absences"]["detailed_geographic_report"] == (
        "NOT_OBSERVED_IN_BOUND_ANNUAL_REPORT"
    )
    for bank in ("HDB", "VIB"):
        assert _trial(live, bank)["bounded_absences"]["detailed_business_report"] == (
            "NOT_OBSERVED_IN_BOUND_ANNUAL_REPORT"
        )


def test_source_specific_axes_are_equation_components_not_schema_mappings(live: dict) -> None:
    source_only = [
        cell
        for trial in live["trials"]
        for row in trial["verified_numeric_rows"]
        for cell in row["cells"]
        if cell["axis_key"].endswith("SOURCE_ONLY")
    ]
    assert len(source_only) == 34  # 32 values plus two preserved blank cells.
    assert sum(item["source_cell_status"] == "VALUE" for item in source_only) == 32
    assert all(item["report_norm_id"] is None for item in source_only)
    labels = {
        item["source_label"] for trial in live["trials"] for item in trial["open_source_items"]
    }
    assert "Miền Trung và Tây Nguyên" in labels
    assert "Nước ngoài" in labels
    assert "Cho thuê tài chính / Chứng khoán / Khác" in labels


def test_vib_blank_is_not_dash_or_zero(live: dict) -> None:
    vib = _trial(live, "VIB")
    blank = [
        cell
        for row in vib["verified_numeric_rows"]
        for cell in row["cells"]
        if cell["source_cell_status"] == "BLANK"
    ]
    assert len(blank) == 2
    assert all(item["axis_key"] == "CENTRAL_BLANK_SOURCE_ONLY" for item in blank)
    assert all(item["pixel_transcription"] is None for item in blank)
    assert all(item["normalized_value"] is None for item in blank)
    assert (
        sum(
            row["verified_accounting_equation"]["status"] == "NOT_TESTABLE"
            for row in vib["verified_numeric_rows"]
        )
        == 2
    )


def test_ctg_pixel_correction_and_bid_rotated_rescue_are_bound(live: dict) -> None:
    ctg = _trial(live, "CTG")
    comparative_liability = next(
        row
        for row in ctg["verified_numeric_rows"]
        if row["metric_key"] == "LIABILITIES" and row["period_role"] == "COMPARATIVE"
    )
    elimination = next(
        cell for cell in comparative_liability["cells"] if cell["axis_key"] == "ELIMINATION"
    )
    assert elimination["pixel_transcription"] == "(5.341.026)"
    assert elimination["evidence"]["vietocr_text"] == "(6.341.026)"
    assert comparative_liability["verified_accounting_equation"]["visible_total"] == 2_236_883_024

    bid = _trial(live, "BID")
    assert {row["evidence_mode"] for row in bid["verified_numeric_rows"]} == {
        "ROTATED_VIETOCR_PIXEL_BOUND"
    }
    assert all(
        cell["evidence"] is None or "source_crop_sha256" in cell["evidence"]
        for row in bid["verified_numeric_rows"]
        for cell in row["cells"]
    )


def test_all_verified_rows_close_and_all_mappings_are_live_schema(live: dict) -> None:
    for trial in live["trials"]:
        for row in trial["verified_numeric_rows"]:
            equation = row["verified_accounting_equation"]
            if equation["status"] == "CORROBORATED_EXACT":
                assert sum(equation["component_values"]) == equation["visible_total"]
            for assignment in row["verified_numeric_assignments"]:
                assert 5765 <= assignment["report_norm_id"] <= 5848
                assert assignment["status"] == "VERIFIED_BY_CODEX"
        assert all(
            binding["status"] == "VERIFIED_BY_CODEX"
            for binding in trial["verified_structure_bindings"]
        )


def test_shape_and_coordinated_rehash_cannot_authenticate(
    module: ModuleType, live: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    tampered = copy.deepcopy(live)
    tampered["metrics"]["related_party_family_processed_count"] = 1
    material = copy.deepcopy(tampered)
    material.pop("result_id")
    tampered["result_id"] = module.RESULT_PREFIX + module.canonical_json_sha256_v1(material)
    with pytest.raises(module.Annual2025ConsolidatedSegmentReport8BankError):
        module._validate_shape(tampered)

    altered = copy.deepcopy(live)
    altered["trials"][0]["verified_numeric_assignments"][0]["normalized_value"] += 1
    material = copy.deepcopy(altered)
    material.pop("result_id")
    altered["result_id"] = module.RESULT_PREFIX + module.canonical_json_sha256_v1(material)
    monkeypatch.setattr(module, "_build_payload", lambda: (live, {}))
    with pytest.raises(module.Annual2025ConsolidatedSegmentReport8BankError):
        module.validate_annual_2025_consolidated_segment_report_8bank_codex_verified_mapping_replay_v1(
            altered
        )
