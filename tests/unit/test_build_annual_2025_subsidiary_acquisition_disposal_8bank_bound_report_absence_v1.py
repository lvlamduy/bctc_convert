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
    "build_annual_2025_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)

_ORDER = ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB"]


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    return builder.build_live_annual_2025_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1()


def test_all_eight_reports_have_bounded_detail_absence(
    result: dict[str, object],
) -> None:
    assert result["metrics"] == {
        "bound_report_detailed_note_absence_count": 8,
        "complete_region_count": 0,
        "document_count": 8,
        "mapping_verified_count": 0,
        "near_control_count": 25,
        "open_review_item_count": 0,
        "page_count": 695,
    }
    assert [trial["document_provenance"] for trial in result["trials"]] == _ORDER
    assert [trial["complete_pdf_page_count"] for trial in result["trials"]] == [
        100,
        103,
        100,
        71,
        84,
        85,
        74,
        78,
    ]
    assert all(
        trial["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" and trial["mappings"] == []
        for trial in result["trials"]
    )


def test_near_controls_remain_policy_or_narrative_only(
    result: dict[str, object],
) -> None:
    assert [len(trial["near_controls"]) for trial in result["trials"]] == [
        0,
        2,
        9,
        4,
        0,
        3,
        5,
        2,
    ]
    observed = {
        role
        for trial in result["trials"]
        for control in trial["near_controls"]
        for role in control["observed_roles"]
    }
    assert observed <= {"TOTAL_CONSIDERATION"}
    assert all(
        not {
            "TOTAL_CONSIDERATION",
            "CASH_SETTLEMENT",
            "CASH_HELD_BY_SUBSIDIARY",
        }
        <= set(control["observed_roles"])
        for trial in result["trials"]
        for control in trial["near_controls"]
    )


def test_live_schema_family_is_exact(result: dict[str, object]) -> None:
    family = result["schema_family"]
    assert family["family_root_report_norm_id"] == 1255
    assert family["first_display_order"] == 835
    assert family["last_display_order"] == 838
    assert [item["report_norm_id"] for item in family["items"]] == list(range(1255, 1259))


def test_coordinated_promotion_is_rejected(result: dict[str, object]) -> None:
    forged = copy.deepcopy(result)
    forged["trials"][0]["disposition"] = "VERIFIED_BY_CODEX"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder.canonical_json_sha256_v1(material)
    with pytest.raises(builder.Annual2025SubsidiaryAcquisitionDisposalAbsenceV1Error):
        builder._validate(forged)


def test_persisted_result_equals_live_replay(result: dict[str, object]) -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert persisted == result
