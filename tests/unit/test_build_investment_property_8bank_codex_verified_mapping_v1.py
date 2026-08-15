from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_investment_property_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_investment_property_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _artifact() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text(encoding="utf-8"))


def test_current_artifact_replays_exactly_and_maps_visible_dash_to_zero() -> None:
    artifact = _artifact()
    replayed = builder.validate_live_investment_property_8bank_codex_verified_mapping_v1(artifact)

    assert replayed["metrics"] == {
        "accounting_equation_count": 11,
        "confirmed_bound_report_absence_count": 7,
        "document_count": 8,
        "mapping_verified_count": 9,
        "open_review_item_count": 0,
        "verified_present_document_count": 1,
        "visible_dash_zero_mapping_count": 1,
    }
    mbb = replayed["trials"][1]
    dash = next(mapping for mapping in mbb["mappings"] if mapping["report_norm_id"] == 6002)
    assert dash["value"]["normalized_value"] == 0
    assert dash["value"]["source_line_index"] is None
    assert dash["value"]["pixel_rgb_sha256"] == builder._DASH_RGB_SHA256
    assert mbb["comparative_control"]["source_period"] == "2025-12-31"


def test_result_contains_only_mbb_as_present_and_no_open_rows() -> None:
    artifact = _artifact()

    assert [trial["document_provenance"] for trial in artifact["trials"] if trial["mappings"]] == [
        "MBB"
    ]
    assert all(
        mapping["final_status"] == "VERIFIED_BY_CODEX"
        for trial in artifact["trials"]
        for mapping in trial["mappings"]
    )
    assert artifact["metrics"]["open_review_item_count"] == 0


def test_public_replay_rejects_coordinated_dash_and_result_rehash() -> None:
    artifact = _artifact()
    forged = copy.deepcopy(artifact)
    dash = next(
        mapping for mapping in forged["trials"][1]["mappings"] if mapping["report_norm_id"] == 6002
    )
    dash["value"]["normalized_value"] = 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0072:result:" + builder.canonical_json_sha256_v1(material)

    with pytest.raises(
        builder.InvestmentProperty8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_investment_property_8bank_codex_verified_mapping_v1(forged)
