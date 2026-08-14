from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


@pytest.fixture(scope="module")
def module(project_root: Path):
    path = (
        project_root
        / "scripts/experiments/build_provision_movement_8bank_codex_verified_mapping_v1.py"
    )
    spec = importlib.util.spec_from_file_location("test_provision_mapping_builder", path)
    assert spec is not None and spec.loader is not None
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


@pytest.fixture(scope="module")
def persisted(project_root: Path):
    return json.loads(
        (
            project_root
            / "docs/experiments/E-0057-provision-movement-8bank-codex-verified-mapping-v1.json"
        ).read_text(encoding="utf-8")
    )


def _rehash(module, value):
    material = deepcopy(value)
    material.pop("result_id")
    value["result_id"] = "pm8bcv1:result:" + canonical_json_sha256_v1(material)
    return value


def test_review_keeps_only_current_period_mapping_and_explicit_comparatives(module):
    review = module._review(module._review_blueprint())
    assert [item["document_provenance"] for item in review["documents"]] == list(
        module.EXPECTED_DOCUMENT_ORDER
    )
    assert all(
        series["period"].startswith("2026-")
        for document in review["documents"]
        for series in document["series"]
    )
    assert all(
        document["comparison_periods_excluded_from_mapping"] for document in review["documents"]
    )
    assert (
        sum(
            row["pixel_value_transcription"] == "-"
            for document in review["documents"]
            for series in document["series"]
            for row in series["rows"]
        )
        == 10
    )


def test_persisted_result_has_exact_boundaries_layout_axes_and_schema_counts(module, persisted):
    result = module._validate_result(persisted)
    assert result["metrics"] == {
        "accounting_equation_verified_count": 17,
        "current_period_lane_parent_verified_count": 17,
        "current_period_role_mapping_verified_count": 73,
        "document_count": 8,
        "document_unique_region_count": 8,
        "q1_source_period_caveat_document_count": 1,
        "visible_dash_verified_as_zero_count": 10,
    }
    by_code = {trial["document_provenance"]: trial for trial in result["trials"]}
    assert by_code["VCB"]["layout_variant"] == "VERTICAL_STACKED_PROVISION_LANE_BLOCKS"
    assert by_code["MBB"]["selected_axes"]["value_axis"] == (
        "OVERALL_TOTAL_ONLY_GEOGRAPHIC_SUBCOLUMNS_EXCLUDED"
    )
    assert by_code["VPB"]["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
    assert [lane["lane"] for lane in by_code["VPB"]["verified_lane_mappings"]] == [
        "GENERAL",
        "SPECIFIC",
        "MARGIN_ADVANCE",
    ]
    assert by_code["VIB"]["cluster_boundary"][
        "comparison_page_sequences_excluded_from_mapping"
    ] == [35]
    for trial in result["trials"]:
        boundaries = trial["cluster_boundary"]["current_period_page_boundaries"]
        assert boundaries
        assert all(item["root_anchor_line_index"] < item["first_line_index"] for item in boundaries)
        assert all(item["first_line_index"] < item["last_line_index"] for item in boundaries)


def test_public_replay_rebuilds_every_live_authority(module, persisted):
    assert (
        module.validate_provision_movement_8bank_codex_verified_mapping_replay_v1(persisted)
        == persisted
    )


def test_coordinated_value_and_result_rehash_cannot_break_accounting(module, persisted):
    forged = deepcopy(persisted)
    row = forged["trials"][0]["verified_lane_mappings"][0]["rows"][1]
    row["pixel_value_transcription"] = "418.854"
    row["normalized_value"] = 418_854
    _rehash(module, forged)
    with pytest.raises(
        module.ProvisionMovement8BankCodexVerifiedMappingV1Error, match="accounting"
    ):
        module._validate_result(forged)


def test_q1_source_period_cannot_be_relabelled_as_q2(module, persisted):
    forged = deepcopy(persisted)
    vpb = forged["trials"][2]
    vpb["source_period_status"] = "VERIFIED_SOURCE_PERIOD_Q2_2026"
    vpb["status"] = "VERIFIED_BY_CODEX"
    _rehash(module, forged)
    with pytest.raises(
        module.ProvisionMovement8BankCodexVerifiedMappingV1Error, match="source-period"
    ):
        module._validate_result(forged)


def test_raw_review_tamper_is_rejected_even_after_review_id_rehash(module):
    forged = module._review_blueprint()
    forged["documents"][0]["series"][0]["rows"][0]["pixel_value_transcription"] = "4.982.251"
    material = deepcopy(forged)
    material.pop("review_id")
    forged["review_id"] = "e0057:pixel-review:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        module.ProvisionMovement8BankCodexVerifiedMappingV1Error, match="fixed reviewed ledger"
    ):
        module._review(forged)
