from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/"
    "build_annual_2025_combined_securities_net_8bank_bound_report_absence_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_combined_securities_net_8bank_bound_report_absence_v1",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)

_ORDER = ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB"]


@pytest.fixture(scope="module")
def live_result() -> dict[str, object]:
    return builder.build_live_annual_2025_combined_securities_net_8bank_bound_report_absence_v1()


def test_all_eight_reports_have_bounded_numeric_row_absence(
    live_result: dict[str, object],
) -> None:
    assert live_result["metrics"] == builder._EXPECTED_METRICS
    assert [trial["document_provenance"] for trial in live_result["trials"]] == _ORDER
    assert all(
        trial["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
        for trial in live_result["trials"]
    )
    assert live_result["schema_family"] == {
        "family_end_display_order": 757,
        "family_root_report_norm_id": 5990,
        "mapped_report_norm_ids": [],
    }


def test_bid_combined_heading_is_preserved_as_one_negative_control(
    live_result: dict[str, object],
) -> None:
    bid = next(trial for trial in live_result["trials"] if trial["document_provenance"] == "BID")
    controls = bid["absence_evidence"]["negative_controls"]
    assert len(controls) == 1
    assert controls[0]["disposition"] == "SECTION_HEADING_WITHOUT_SAME_ROW_MONETARY_VALUES"
    assert controls[0]["page_span"] == [56, 56]
    assert controls[0]["label_lines"][0]["line_index"] == 4
    assert all(
        trial["absence_evidence"]["near_section_heading_match_count"] == 0
        for trial in live_result["trials"]
        if trial["document_provenance"] != "BID"
    )


def test_absence_profile_never_imports_component_results_as_authority(
    live_result: dict[str, object],
) -> None:
    assert live_result["input_refs"]["component_results_required"] is False
    assert "trading_result_id" not in live_result["input_refs"]
    assert "investment_result_id" not in live_result["input_refs"]
    assert live_result["authority"]["mapping_authority"] is False


def test_coordinated_rehash_cannot_promote_bid_heading(
    live_result: dict[str, object],
) -> None:
    forged = copy.deepcopy(live_result)
    bid = next(trial for trial in forged["trials"] if trial["document_provenance"] == "BID")
    bid["status"] = "VERIFIED_BY_CODEX"
    bid["absence_evidence"] = None
    with pytest.raises(builder.Annual2025CombinedSecuritiesNetAbsenceV1Error):
        builder._assert_result(forged)


def test_persisted_result_equals_live_replay(live_result: dict[str, object]) -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert persisted == live_result
