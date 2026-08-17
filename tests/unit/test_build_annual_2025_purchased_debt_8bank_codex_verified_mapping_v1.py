from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/"
    "build_annual_2025_purchased_debt_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("annual_2025_purchased_debt_builder_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict:
    return builder.build_live_annual_2025_purchased_debt_8bank_codex_verified_mapping_v1()


def _trial(result: dict, bank: str) -> dict:
    return next(item for item in result["trials"] if item["bank_provenance"] == bank)


def test_annual_purchased_debt_maps_four_unique_regions(live: dict) -> None:
    assert live["metrics"] == {
        "accounting_equation_verified_count": 19,
        "core_accounting_equation_verified_count": 16,
        "dash_cell_verified_as_zero_count": 5,
        "document_count": 8,
        "document_not_observed_count": 4,
        "document_verified_count": 4,
        "mapped_value_cell_count": 30,
        "mapping_verified_count": 15,
        "optional_check_equation_count": 3,
        "unresolved_mapping_count": 0,
    }
    assert [
        (trial["bank_provenance"], trial["page_evidence"][0]["page_sequence"])
        for trial in live["trials"]
        if trial["status"] == "VERIFIED_BY_CODEX"
    ] == [("MBB", 54), ("VPB", 49), ("HDB", 39), ("VIB", 40)]


def test_hdb_legitimately_omits_optional_interest_and_foreign_currency(live: dict) -> None:
    hdb = _trial(live, "HDB")
    assert {mapping["report_norm_id"] for mapping in hdb["verified_mappings"]} == {
        801,
        803,
        5738,
    }
    roles = {row["role"] for row in hdb["page_evidence"][0]["rows"]}
    assert roles == {"PURCHASE_VND", "PROVISION", "PRINCIPAL"}
    assert {equation["role"] for equation in hdb["verified_accounting_equations"]} == {
        "CURRENT_BALANCE_GROSS_CURRENCY_PLUS_PROVISION_EQUALS_NET",
        "COMPARATIVE_BALANCE_GROSS_CURRENCY_PLUS_PROVISION_EQUALS_NET",
        "CURRENT_PRINCIPAL_EQUALS_DETAIL_TOTAL",
        "COMPARATIVE_PRINCIPAL_EQUALS_DETAIL_TOTAL",
    }


def test_all_line_values_are_challenged_by_ppocrv6_and_dashes_stay_typed(live: dict) -> None:
    values = [
        value
        for trial in live["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["source_values"]
    ]
    dashes = [value for value in values if value["source_cell_status"] == "DASH"]
    assert len(values) == 30
    assert len(dashes) == 5
    assert all(
        value["normalized_value"] == 0
        and value["primary_numeric_challenger"]["status"]
        == "VISIBLE_PIXEL_DASH_WITH_NO_PROVIDER_TEXT_LINE"
        for value in dashes
    )
    assert all(
        value["primary_numeric_challenger"]["status"]
        == "PPOCRV6_NUMERIC_CHALLENGER_MATCHED_VISIBLE_PIXEL"
        for value in values
        if value["source_cell_status"] == "VALUE"
    )


def test_every_core_and_optional_equation_closes(live: dict) -> None:
    for trial in live["trials"]:
        for equation in [
            *trial["verified_accounting_equations"],
            *trial["optional_check_equations"],
        ]:
            assert sum(equation["addends"]) == equation["visible_total"]
            assert equation["computed_total"] == equation["visible_total"]


def test_pixel_number_tamper_is_rejected_by_ppocrv6_challenger() -> None:
    base = builder._base()
    semantic, manifest, scan, review, schema_authority, schema_by_id, manifest_sha, review_sha = (
        base._live_inputs()
    )
    forged = copy.deepcopy(review)
    hdb = next(item for item in forged["documents"] if item["bank_code"] == "HDB")
    purchase = next(item for item in hdb["pages"][0]["rows"] if item["role"] == "PURCHASE_VND")
    purchase["values"][0]["pixel_transcription"] = "23.925.868"
    base._review_blueprint = lambda: copy.deepcopy(forged)
    with pytest.raises(
        builder.Annual2025PurchasedDebt8BankError,
        match="visible pixel and PaddleOCR6 numeric challenger disagree",
    ):
        base.build_purchased_debt_8bank_codex_verified_mapping_v1(
            semantic,
            manifest,
            scan,
            forged,
            schema_authority,
            schema_by_id,
            crop_manifest_sha256=manifest_sha,
            review_sha256=review_sha,
        )


def test_coordinated_result_rehash_cannot_replace_live_replay(live: dict) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][1]["verified_mappings"][0]["source_values"][0][
        "independent_pixel_transcription"
    ] = "forged"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + canonical_json_sha256_v1(material)
    with pytest.raises(Exception, match="replay exactly"):
        builder.validate_annual_2025_purchased_debt_8bank_codex_verified_mapping_replay_v1(forged)


def test_persisted_review_and_result_equal_live_bytes(live: dict) -> None:
    assert (_ROOT / builder.REVIEW_PATH).read_bytes() == canonical_json_bytes_v1(
        builder.build_annual_2025_purchased_debt_pixel_review_blueprint_v1()
    )
    assert (_ROOT / builder.RESULT_PATH).read_bytes() == canonical_json_bytes_v1(live)
