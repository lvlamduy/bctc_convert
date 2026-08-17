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
    / "scripts/experiments/build_annual_2025_customer_deposit_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_customer_deposit_8bank_codex_verified_mapping_v1",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict[str, object]:
    return builder.build_live_annual_2025_customer_deposit_8bank_codex_verified_mapping_v1()


def test_all_eight_reports_have_one_unique_annual_region(live: dict[str, object]) -> None:
    assert live["metrics"] == builder._EXPECTED_METRICS
    assert [trial["document_provenance"] for trial in live["trials"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert all(
        trial["source_period"] == "2025-12-31"
        and trial["source_period_status"]
        == "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_PERIOD"
        and trial["whole_document_uniqueness"]
        == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        for trial in live["trials"]
    )


def test_exact_schema_coverage_and_accounting(live: dict[str, object]) -> None:
    for trial in live["trials"]:
        assert {mapping["report_norm_id"] for mapping in trial["verified_mappings"]} == (
            builder._EXPECTED_IDS[trial["document_provenance"]]
        )
        assert all(
            equation["status"] == "CORROBORATED_EXACT"
            and equation["computed_total"] == equation["printed_total"]
            for equation in trial["verified_accounting_equations"]
        )


def test_user_directed_variants_and_combined_bid_rows(live: dict[str, object]) -> None:
    by_bank = {trial["document_provenance"]: trial for trial in live["trials"]}
    assert {
        mapping["role"]: mapping["report_norm_id"]
        for mapping in by_bank["MBB"]["verified_mappings"]
        if mapping["section"] == "CUSTOMER_TYPE"
    } == {"CUSTOMER_TCKT": 1084, "CUSTOMER_INDIVIDUAL": 1089}
    assert any(
        mapping["role"] == "STATE_OVER_50_MULTI_MEMBER_TNHH" and mapping["report_norm_id"] == 770
        for bank in ("VPB", "VIB")
        for mapping in by_bank[bank]["verified_mappings"]
    )
    assert [item["source_label"] for item in by_bank["BID"]["unresolved_items"]] == [
        "Công ty cổ phần",
        "Doanh nghiệp tư nhân, cá nhân",
    ]
    assert all(
        item["status"] == "UNRESOLVED_NO_EXACT_SCHEMA_ITEM"
        for item in by_bank["BID"]["unresolved_items"]
    )


def test_hdb_pixel_digits_override_vietocr_numeric_proposals(
    live: dict[str, object],
) -> None:
    hdb = next(trial for trial in live["trials"] if trial["document_provenance"] == "HDB")
    dedicated = next(
        mapping for mapping in hdb["verified_mappings"] if mapping["role"] == "DEDICATED"
    )
    foreign = next(
        mapping for mapping in hdb["verified_mappings"] if mapping["role"] == "DEDICATED_FOREIGN"
    )
    assert dedicated["normalized_value"] == 985_313
    assert dedicated["source_values"][0]["fresh_vietocr_numeric_proposal"] == "965.313"
    assert foreign["normalized_value"] == 95_596
    assert foreign["source_values"][0]["fresh_vietocr_numeric_proposal"] == "95.596"


def test_exact_replay_rejects_coordinated_mapping_rehash(live: dict[str, object]) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][0]["verified_mappings"][0]["normalized_value"] += 1
    base = builder._configure_base()
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + base.canonical_json_sha256_v1(material)

    with pytest.raises(builder.Annual2025CustomerDeposit8BankError):
        builder.validate_annual_2025_customer_deposit_8bank_codex_verified_mapping_replay_v1(forged)


def test_persisted_review_and_result_equal_live_bytes(live: dict[str, object]) -> None:
    persisted_review = json.loads((builder.PROJECT_ROOT / builder.REVIEW_PATH).read_text("utf-8"))
    persisted_result = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text("utf-8"))

    assert persisted_review == (
        builder.build_annual_2025_customer_deposit_pixel_review_blueprint_v1()
    )
    assert persisted_result == live
