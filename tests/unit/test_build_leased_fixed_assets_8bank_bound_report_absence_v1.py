from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import same_typed_json_v1

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_leased_fixed_assets_8bank_bound_report_absence_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_leased_fixed_assets_8bank_bound_report_absence_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live_result() -> dict[str, object]:
    return builder.build_live_leased_fixed_assets_8bank_bound_report_absence_v1()


def test_all_eight_bound_reports_are_closed_without_manufactured_mappings(
    live_result: dict[str, object],
) -> None:
    assert live_result["metrics"] == {
        "bound_report_absence_count": 8,
        "document_count": 8,
        "mapping_verified_count": 0,
        "negative_control_line_count": 24,
        "open_review_item_count": 0,
    }
    assert all(trial["mappings"] == [] for trial in live_result["trials"])
    assert all(
        trial["whole_document_scan_metrics"]
        == {"complete_region_count": 0, "near_region_count": 0, "owner_candidate_count": 0}
        for trial in live_result["trials"]
    )
    assert live_result["authority"]["absence_claim_bounded_to_supplied_pdf"] is True
    assert live_result["authority"]["broad_corpus_or_other_report_absence_authority"] is False


def test_live_schema_interval_is_exact_and_persisted_artifact_replays(
    live_result: dict[str, object],
) -> None:
    schema = live_result["schema_family"]
    assert schema["first_report_norm_id"] == 896
    assert schema["last_report_norm_id"] == 912
    assert [item["report_norm_id"] for item in schema["items"]] == list(range(896, 913))
    assert schema["items"][0]["children"] == [897, 905]
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text(encoding="utf-8"))
    assert same_typed_json_v1(persisted, live_result)


def test_finance_lease_controls_and_coordinated_rehash_cannot_promote_absence(
    live_result: dict[str, object],
) -> None:
    assert any(
        control["semantic_text"] == "Cho thuê tài chính"
        for trial in live_result["trials"]
        for control in trial["negative_controls"]
    )
    forged = copy.deepcopy(live_result)
    forged["trials"][0]["mappings"] = [{"report_norm_id": 896}]
    forged["metrics"]["mapping_verified_count"] = 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0070:result:" + builder.canonical_json_sha256_v1(material)

    with pytest.raises(
        builder.LeasedFixedAssets8BankBoundReportAbsenceV1Error,
        match="content drifted",
    ):
        builder._validate_result(forged)
