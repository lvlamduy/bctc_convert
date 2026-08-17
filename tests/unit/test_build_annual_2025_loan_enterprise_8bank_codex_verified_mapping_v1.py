from __future__ import annotations

import copy
import hashlib
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
    _ROOT
    / "scripts/experiments/build_annual_2025_loan_enterprise_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("annual_2025_loan_enterprise_builder_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict:
    return builder.build_live_annual_2025_loan_enterprise_8bank_codex_verified_mapping_v1()


def _trial(result: dict, bank: str) -> dict:
    return next(item for item in result["trials"] if item["document_provenance"] == bank)


def test_annual_enterprise_result_has_six_unique_tables_and_two_bounded_absences(
    live: dict,
) -> None:
    assert live["metrics"] == {
        "document_count": 8,
        "document_no_complete_region_count": 2,
        "document_unique_structure_count": 6,
        "mapped_item_verified_by_codex_count": 57,
        "mapped_money_value_cell_count": 114,
        "mapped_percentage_corroboration_cell_count": 86,
        "negative_family_control_count": 32,
        "source_group_equation_verified_count": 0,
        "source_only_total_verified_count": 6,
        "transformer_disagreement_preserved_count": 33,
        "typed_dash_cell_verified_count": 2,
        "unresolved_schema_semantic_row_count": 0,
    }
    assert [_trial(live, bank)["physical_page"] for bank in builder._POSITIVE_BANKS] == [
        52,
        46,
        36,
        40,
        42,
        39,
    ]
    assert _trial(live, "ACB")["verified_mappings"] == []
    assert _trial(live, "CTG")["verified_mappings"] == []


def test_vcb_combined_legal_form_maps_to_exact_combined_leaf(live: dict) -> None:
    trial = _trial(live, "VCB")
    assert trial["unresolved_rows"] == []
    item = next(
        mapping
        for mapping in trial["verified_mappings"]
        if mapping["role"] == "COOPERATIVE_AND_PRIVATE_ENTERPRISE_COMBINED"
    )
    assert item["role"] == "COOPERATIVE_AND_PRIVATE_ENTERPRISE_COMBINED"
    assert item["report_norm_id"] == 6074
    assert item["independent_pixel_label"] == "Hợp tác xã và công ty tư nhân"
    assert [value["normalized_value"] for value in item["money_values"]] == [937036, 1371552]


def test_mbb_pixel_bound_dashes_are_retained_before_zero_normalization(live: dict) -> None:
    partnership = next(
        item for item in _trial(live, "MBB")["verified_mappings"] if item["role"] == "PARTNERSHIP"
    )
    cells = partnership["money_values"] + partnership["percentage_corroboration"]
    dashes = [cell for cell in cells if cell["value_status"] == "DASH"]
    assert [(cell["lane_index"], cell["normalized_value"]) for cell in dashes] == [
        (2, 0),
        (3, 0),
    ]
    assert all(cell["independent_pixel_transcription"] == "-" for cell in dashes)
    assert all(cell["pixel_binding"] is not None for cell in dashes)


def test_review_and_numeric_challenger_are_exactly_bound(live: dict) -> None:
    review = (_ROOT / builder.REVIEW_PATH).read_bytes()
    assert hashlib.sha256(review).hexdigest() == builder.EXPECTED_REVIEW_SHA256
    refs = live["input_refs"]["ppocrv6_numeric_challenger_pages"]
    assert [item["bank"] for item in refs] == list(builder._POSITIVE_BANKS)
    assert sum(item["checked_numeric_cell_count"] for item in refs) == 218


def test_paddle_numeric_disagreement_fails_before_mapping() -> None:
    base, _, manifest, _, scan = builder._live_core(include_review=False)
    forged = copy.deepcopy(scan)
    mbb = builder._trial(forged, "MBB")["matcher_result"]["graphs"][0]
    mbb["rows"][0]["values"][0]["semantic_surface"] = "39.709.934"
    with pytest.raises(builder.Annual2025LoanEnterprise8BankError, match="challengers disagree"):
        builder._provider_numeric_refs(base, manifest, forged)


def test_coordinated_result_rehash_cannot_replace_live_replay(live: dict) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][1]["verified_mappings"][0]["independent_pixel_label"] = "forged label"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + canonical_json_sha256_v1(material)
    with pytest.raises(builder.Annual2025LoanEnterprise8BankError, match="does not replay exactly"):
        builder.validate_annual_2025_loan_enterprise_8bank_codex_verified_mapping_replay_v1(forged)


def test_persisted_result_bytes_equal_live_result(live: dict) -> None:
    persisted = (_ROOT / builder.RESULT_PATH).read_bytes()
    assert persisted == canonical_json_bytes_v1(live) + b"\n"
