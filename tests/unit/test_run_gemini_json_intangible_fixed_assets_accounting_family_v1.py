from __future__ import annotations

import argparse
import importlib.util
import json
from hashlib import sha256
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_fixed_asset_rollforward_family_v1 import (
    GeminiJsonFixedAssetRollforwardFamilyV1Error,
    compile_gemini_json_fixed_asset_rollforward_family_specs_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    ROOT / "scripts/experiments/run_gemini_json_intangible_fixed_assets_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location("run_intangible_fixed_assets_family_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _compiled_specs():
    paths = (
        "config/families/tm-intangible-fixed-assets-topology-v1.json",
        "config/families/tm-intangible-fixed-assets-evaluation-v1.json",
        "config/families/tm-intangible-fixed-assets-schema-binding-v1.json",
    )
    return compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
        *[json.loads((ROOT / path).read_bytes()) for path in paths]
    )


def _sweep(*, coefficient: int = 7, mapping_id: str = "mapping-a"):
    return {
        "family_id": runner.FAMILY_ID,
        "trials": [
            {
                "mappings": [
                    {
                        "bound_unit": "MILLION_VND",
                        "cell": {"coefficient": coefficient, "state": "NUMBER"},
                        "item_mapping_id": mapping_id,
                        "period_date": "2025-12-31",
                        "report_norm_id": 915,
                        "role": "COST_OPENING",
                        "row_id": "r2",
                        "source_refs": [
                            {
                                "label_exact": "Tại ngày 1/1/2025",
                                "row_id": "r2",
                                "source_ordinal": 2,
                            }
                        ],
                    }
                ],
                "reasons": [],
                "source_logical_name": "vietstock_bctc/BANK/2025/report.pdf",
                "source_sha256": "a" * 64,
                "status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
            }
        ],
    }


def _pin_baseline(monkeypatch, tmp_path, sweep):
    payload = json.dumps(sweep, ensure_ascii=False, sort_keys=True).encode()
    baseline = tmp_path / "baseline.json"
    baseline.write_bytes(payload)
    monkeypatch.setattr(runner, "PINNED_STRICT_REGRESSION_SWEEP_SHA256", sha256(payload).hexdigest())
    monkeypatch.setattr(runner, "PINNED_STRICT_REGRESSION_SWEEP_SIZE_BYTES", len(payload))
    return baseline


def test_strict_regression_compares_every_semantic_mapping_field(monkeypatch, tmp_path):
    baseline = _pin_baseline(monkeypatch, tmp_path, _sweep())
    receipt = runner._strict_regression_receipt(
        sweep=_sweep(mapping_id="new-spec-derived-id"), baseline_path=baseline
    )
    assert receipt["disposition"] == "EXACT_SEMANTIC_TRIAL_AXIS"
    assert receipt["source_count"] == 1
    with pytest.raises(
        runner.RunGeminiJsonIntangibleFixedAssetsAccountingFamilyV1Error,
        match="semantic regression is not exact",
    ):
        runner._strict_regression_receipt(
            sweep=_sweep(coefficient=8), baseline_path=baseline
        )


def test_strict_regression_requires_pinned_regular_bytes(monkeypatch, tmp_path):
    baseline = _pin_baseline(monkeypatch, tmp_path, _sweep())
    monkeypatch.setattr(runner, "PINNED_STRICT_REGRESSION_SWEEP_SHA256", "0" * 64)
    with pytest.raises(
        runner.RunGeminiJsonIntangibleFixedAssetsAccountingFamilyV1Error,
        match="bytes drifted",
    ):
        runner._strict_regression_receipt(sweep=_sweep(), baseline_path=baseline)
    with pytest.raises(
        runner.RunGeminiJsonIntangibleFixedAssetsAccountingFamilyV1Error,
        match="requires --strict-regression-sweep",
    ):
        runner._strict_regression_receipt(sweep=_sweep(), baseline_path=None)


def test_semantic_axis_rejects_wrong_family_and_duplicate_sources():
    wrong = _sweep()
    wrong["family_id"] = "TANGIBLE_FIXED_ASSETS_ROLLFORWARD"
    with pytest.raises(
        runner.RunGeminiJsonIntangibleFixedAssetsAccountingFamilyV1Error,
        match="not Family 20",
    ):
        runner._semantic_trial_axis(wrong)
    duplicate = _sweep()
    duplicate["trials"].append(duplicate["trials"][0])
    with pytest.raises(
        runner.RunGeminiJsonIntangibleFixedAssetsAccountingFamilyV1Error,
        match="source axis is invalid",
    ):
        runner._semantic_trial_axis(duplicate)


def test_disjoint_receipt_requires_zero_intersection_and_empty_comparator():
    audit = {
        "axes": {"historical_comparator": []},
        "historical_comparator_policy_receipt": {
            "comparison_axis": [],
            "corpus_relation": {"overlap_count": 0},
            "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
            "policy": runner.DISJOINT_EXPANSION,
        },
    }
    runner._assert_policy_receipt(audit=audit, policy=runner.DISJOINT_EXPANSION)
    audit["historical_comparator_policy_receipt"]["corpus_relation"]["overlap_count"] = 1
    with pytest.raises(
        runner.RunGeminiJsonIntangibleFixedAssetsAccountingFamilyV1Error,
        match="not exactly disjoint",
    ):
        runner._assert_policy_receipt(audit=audit, policy=runner.DISJOINT_EXPANSION)


def test_strict_receipt_requires_exact_historical_comparison():
    audit = {
        "historical_comparator_policy_receipt": {
            "disposition": runner.EXACT_HISTORICAL_COMPARISON,
            "policy": runner.STRICT_RELEASE,
        }
    }
    runner._assert_policy_receipt(audit=audit, policy=runner.STRICT_RELEASE)
    audit["historical_comparator_policy_receipt"]["disposition"] = "MISMATCH"
    with pytest.raises(
        runner.RunGeminiJsonIntangibleFixedAssetsAccountingFamilyV1Error,
        match="is not exact",
    ):
        runner._assert_policy_receipt(audit=audit, policy=runner.STRICT_RELEASE)


def test_run_mode_gate_rejects_official_expansion_and_baseline_on_expansion(tmp_path):
    with pytest.raises(
        runner.RunGeminiJsonIntangibleFixedAssetsAccountingFamilyV1Error,
        match="OFFICIAL Family 20 run requires STRICT_RELEASE",
    ):
        runner.run(
            argparse.Namespace(
                historical_comparator_policy=runner.DISJOINT_EXPANSION,
                run_kind="OFFICIAL",
                strict_regression_sweep=None,
            )
        )
    with pytest.raises(
        runner.RunGeminiJsonIntangibleFixedAssetsAccountingFamilyV1Error,
        match="cannot claim a strict regression sweep",
    ):
        runner.run(
            argparse.Namespace(
                historical_comparator_policy=runner.DISJOINT_EXPANSION,
                run_kind="EXPERIMENTAL",
                strict_regression_sweep=tmp_path / "baseline.json",
            )
        )


def test_implementation_receipt_includes_family_specific_runner():
    refs = runner._implementation_refs()
    assert refs[0]["path"] == (
        "scripts/experiments/"
        "run_gemini_json_intangible_fixed_assets_accounting_family_v1.py"
    )


def test_specialized_runner_accepts_the_compiled_fixed_asset_family_shape():
    assert runner._family_id(_compiled_specs()) == runner.FAMILY_ID


def test_f20_registered_source_repair_artifact_compiles_exactly():
    compiled = _compiled_specs()
    ref = compiled["source_repair_artifact_ref"]
    overlay = compiled["source_repair_overlay"]
    payload = (ROOT / ref["path"]).read_bytes()
    assert ref == {
        "artifact_format_version": (
            "GEMINI_JSON_FIXED_ASSET_AUTHENTICATED_SOURCE_REPAIR_ARTIFACT_V1"
        ),
        "overlay_id": (
            "gjffasrv1:overlay:"
            "8dfbc74f811967922e4ea906158e9e4fce0479c9f714a409b8a0034be0beb2d1"
        ),
        "path": (
            "data/registered/"
            "gemini_json_intangible_fixed_asset_source_repair_artifact_v1.json"
        ),
        "sha256": "518a1e54599b0822de19367c609673c361ed2b6c2d13057aaa9e2bb55ed529cb",
        "size_bytes": 19481,
    }
    assert sha256(payload).hexdigest() == ref["sha256"]
    assert len(overlay["repairs"]) == 5
    assert sum(len(item["cell_repairs"]) for item in overlay["repairs"]) == 12
    assert {
        item["source_binding"]["source_sha256"] for item in overlay["repairs"]
    } == {
        "91a030b2dcf82adee0ef5db4ef924f24287d08d72e9ec16ee116e5539c2c0f50",
        "6a10fc0ff127c752b99969039e76c4baf35f068b27934023c83551667eb114da",
        "cbff3d2bd30c6487a3be7f0942e65a19ec52f0711838eb89cf332cba517f2f3b",
        "bcd5937e4fc889ee5eb0ac0d4d89de7b06c9198d30d39b7313e4891a6c4f1366",
        "d6481fddd606aa38e8dda6f6614e81e38d6e0882d6c7512a3d5f601ae718e450",
    }


def test_f20_source_repair_artifact_outer_bytes_tamper_fails_closed(monkeypatch):
    paths = (
        "config/families/tm-intangible-fixed-assets-topology-v1.json",
        "config/families/tm-intangible-fixed-assets-evaluation-v1.json",
        "config/families/tm-intangible-fixed-assets-schema-binding-v1.json",
    )
    topology, evaluation, binding = [json.loads((ROOT / path).read_bytes()) for path in paths]
    artifact_name = Path(evaluation["authenticated_source_repair_artifact_ref"]["path"]).name
    original_read_bytes = Path.read_bytes

    def tampered_read_bytes(path):
        payload = original_read_bytes(path)
        return payload + b" " if path.name == artifact_name else payload

    monkeypatch.setattr(Path, "read_bytes", tampered_read_bytes)
    with pytest.raises(
        GeminiJsonFixedAssetRollforwardFamilyV1Error,
        match="authenticated source-repair artifact bytes drifted",
    ):
        compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
            topology, evaluation, binding
        )


def test_f20_source_repair_artifact_inner_cell_tamper_fails_replay(monkeypatch):
    paths = (
        "config/families/tm-intangible-fixed-assets-topology-v1.json",
        "config/families/tm-intangible-fixed-assets-evaluation-v1.json",
        "config/families/tm-intangible-fixed-assets-schema-binding-v1.json",
    )
    topology, evaluation, binding = [json.loads((ROOT / path).read_bytes()) for path in paths]
    artifact_path = ROOT / evaluation["authenticated_source_repair_artifact_ref"]["path"]
    artifact = json.loads(artifact_path.read_bytes())
    artifact["repairs"][0]["cell_repairs"][0].update(
        {"after_exact": "(1)", "visual_state": "PRINTED_MONEY"}
    )
    tampered_payload = json.dumps(
        artifact, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    evaluation["authenticated_source_repair_artifact_ref"].update(
        {
            "sha256": sha256(tampered_payload).hexdigest(),
            "size_bytes": len(tampered_payload),
        }
    )
    original_read_bytes = Path.read_bytes

    def tampered_read_bytes(path):
        return tampered_payload if path == artifact_path else original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", tampered_read_bytes)
    with pytest.raises(
        GeminiJsonFixedAssetRollforwardFamilyV1Error,
        match="authenticated source-repair identity does not replay",
    ):
        compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
            topology, evaluation, binding
        )


def test_f20_visual_variants_are_declarative_and_generic():
    compiled = _compiled_specs()
    assert compiled["topology"]["family_id"] == runner.FAMILY_ID
    assert {
        "nguyen gia tscd vo hinh",
        "gia tri hao mon",
        "gia tri khau hao luy ke",
    } <= {
        *compiled["role_aliases"]["COST_BRANCH"],
        *compiled["role_aliases"]["DEPRECIATION_BRANCH"],
    }
    assert {
        "chuyen tu mua sam xdcb do dang",
        "chuyen tu xdcd do dang",
        "chuyen tu tam ung mua sam tscd va chi phi xdcb do dang",
    } <= set(compiled["role_aliases"]["COST_CIP_TRANSFER"])
    assert "phan loai lai" in compiled["role_aliases"]["COST_RECLASSIFICATION"]
    assert "thanh ly nhuong ban" in compiled["role_aliases"]["COST_DISPOSAL"]
    assert compiled["unit_binding_by_alias"]["vnd"]["accepted"] is True
    assert compiled["unit_binding_by_alias"]["vnd"]["canonical_unit"] == "VND"


def test_f20_source_only_and_owner_policies_stay_narrow():
    compiled = _compiled_specs()
    evaluation = compiled["evaluation"]
    assert evaluation["source_only_row_aliases"] == [
        "tam thoi khong su dung",
        "tam thoi chua su dung",
        "dang cho thanh ly",
    ]
    assert evaluation["missing_local_unit_policy"] == (
        "UNIQUE_TYPED_BALANCE_SHEET_OWNER_ENDPOINT_VECTOR_BASE_VALUE"
    )
    assert evaluation["endpoint_first_layout"]["layout_kind"] == (
        "CARRYING_ENDPOINT_PARENT_WITH_COST_AND_DEPRECIATION_CHILDREN"
    )
    assert all("tong" not in alias for alias in compiled["query_policy"]["owner_aliases"])
