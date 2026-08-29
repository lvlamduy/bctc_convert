from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest
from test_gemini_json_multitable_hierarchical_family_v1 import _json as _family_spec
from test_gemini_json_multitable_hierarchical_indexed_wiring_v1 import (
    _fixture as _indexed_fixture,
)

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    ROOT / "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_multitable_hierarchical_accounting_family_v1", RUNNER_PATH
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_audit_replay_rejects_coherent_axis_and_embedded_schema_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_historical_comparator_axis",
        lambda **_kwargs: ([], [{"fixture": "historical-oracle"}]),
    )
    database, selected, evidence, trials, compiled = _indexed_fixture(tmp_path)
    topology = _family_spec("tm-other-assets-topology-v1.json")
    evaluation = _family_spec("tm-other-assets-evaluation-v1.json")
    schema = _family_spec("tm-other-assets-schema-binding-v1.json")
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=evidence,
    )
    sweep_output = tmp_path / "sweep.json"
    sweep_output.write_bytes(runner.canonical_json_bytes_v1(sweep))
    spec_refs = {
        "evaluation": {"fixture": "evaluation"},
        "schema_binding": {"fixture": "schema_binding"},
        "topology": {"fixture": "topology"},
    }
    audit = runner.build_multitable_hierarchical_experimental_audit_v1(
        sweep=sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected,
        indexed_query_evidence=evidence,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    replay_args = {
        "database": database,
        "sweep": sweep,
        "sweep_output": sweep_output,
        "selected_page_json_version_ids": selected,
        "indexed_query_evidence": evidence,
        "trials": trials,
        "compiled_specs": compiled,
        "spec_refs": spec_refs,
    }
    assert (
        runner.validate_multitable_hierarchical_experimental_audit_replay_v1(audit, **replay_args)
        == audit
    )

    forged_audit = copy.deepcopy(audit)
    forged_audit["axes"]["mappings"][0]["coefficients"][0] += 777
    forged_audit["axis_sha256"]["mappings"] = runner.canonical_json_sha256_v1(
        forged_audit["axes"]["mappings"]
    )
    audit_material = {key: value for key, value in forged_audit.items() if key != "audit_id"}
    forged_audit["audit_id"] = "gjmthfeav1:audit:" + runner.canonical_json_sha256_v1(audit_material)
    runner.validate_multitable_hierarchical_experimental_audit_content_v1(forged_audit)
    with pytest.raises(
        runner.RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error,
        match="does not replay exactly",
    ):
        runner.validate_multitable_hierarchical_experimental_audit_replay_v1(
            forged_audit, **replay_args
        )

    forged_sweep = copy.deepcopy(sweep)
    forged_sweep["specs"]["schema_binding"]["value"]["family_root_report_norm_id"] = 999999
    forged_sweep["specs"]["schema_binding"]["sha256"] = runner.canonical_json_sha256_v1(
        forged_sweep["specs"]["schema_binding"]["value"]
    )
    sweep_material = {key: value for key, value in forged_sweep.items() if key != "sweep_id"}
    forged_sweep["sweep_id"] = "gjfafsv1:sweep:" + runner.canonical_json_sha256_v1(sweep_material)
    with pytest.raises(
        runner.RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error,
        match="caller and embedded compiled specs differ",
    ):
        runner.validate_multitable_hierarchical_experimental_audit_replay_v1(
            audit,
            **{
                **replay_args,
                "sweep": forged_sweep,
                "indexed_query_evidence": forged_sweep["indexed_query_evidence"],
                "trials": forged_sweep["trials"],
            },
        )
