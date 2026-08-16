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
    / "scripts/experiments/build_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def test_all_eight_reports_lack_the_three_row_detailed_family() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "bound_report_detailed_note_absence_count": 8,
        "document_count": 8,
        "mapping_verified_count": 0,
        "near_control_count": 43,
        "open_review_item_count": 0,
    }
    assert all(trial["mappings"] == [] for trial in result["trials"])
    assert all(
        trial["whole_document_scan_metrics"]["complete_region_count"] == 0
        for trial in result["trials"]
    )


def test_schema_family_is_exact_1255_to_1258() -> None:
    family = _result()["schema_family"]
    assert family["family_root_report_norm_id"] == 1255
    assert [item["report_norm_id"] for item in family["items"]] == [
        1255,
        1256,
        1257,
        1258,
    ]
    assert family["first_display_order"] == 831
    assert family["last_display_order"] == 834


def test_hdb_acquisition_and_ctg_cash_flow_mentions_remain_controls() -> None:
    result = _result()
    hdb = result["trials"][3]
    ctg = result["trials"][5]
    assert any(
        "HDS" in item["vietocr_transformer_proposal"]
        or "hợp nhất kinh doanh" in item["vietocr_transformer_proposal"].lower()
        for item in hdb["near_controls"]
    )
    assert any(
        "mua công ty con" in item["vietocr_transformer_proposal"].lower()
        or "thanh lý công ty con" in item["vietocr_transformer_proposal"].lower()
        for item in ctg["near_controls"]
    )


def test_public_replay_rejects_coordinated_promotion() -> None:
    forged = copy.deepcopy(_result())
    forged["trials"][0]["mappings"] = [{"report_norm_id": 1255}]
    forged["metrics"]["mapping_verified_count"] = 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0093:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.SubsidiaryAcquisitionDisposal8BankBoundReportAbsenceV1Error,
        match="trial drifted|replay exactly",
    ):
        builder.validate_live_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1(forged)
