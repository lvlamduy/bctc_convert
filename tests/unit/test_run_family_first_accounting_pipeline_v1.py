from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.experiments import run_family_first_accounting_pipeline_v1 as pipeline


def _specs(monkeypatch: pytest.MonkeyPatch) -> None:
    def load(_root: Path, path: Path):
        if "schema" in path.name:
            return {"family_id": "FAMILY", "kind": "schema"}
        if "evaluation" in path.name:
            return {"family_id": "FAMILY", "kind": "evaluation"}
        return {"family_id": "FAMILY", "kind": "family"}

    monkeypatch.setattr(pipeline.topology_cli, "_family_spec", load)
    monkeypatch.setattr(
        pipeline.evidence_cli,
        "_artifact_path",
        lambda _family, _evaluation: Path("evidence.json"),
    )
    monkeypatch.setattr(
        pipeline.mapping_cli,
        "_artifact_path",
        lambda _family, _evaluation, _schema: Path("mapping.json"),
    )


def test_pipeline_build_and_verify_traverse_live_source_once_each(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _specs(monkeypatch)
    calls = {"sweep": 0}
    evidence = {
        "family_id": "FAMILY",
        "metrics": {"document_count": 140},
        "sweep_id": "ffaesv1:sweep:" + "1" * 64,
    }
    mapping = {
        "evidence_sweep_id": evidence["sweep_id"],
        "family_id": "FAMILY",
        "mapping_id": "ffasmv1:mapping:" + "2" * 64,
        "metrics": {"verified_document_count": 80},
    }
    monkeypatch.setattr(
        pipeline,
        "authenticate_family_first_semantic_label_archive_v1",
        lambda _root, *, model_cache: ("archive", model_cache),
    )
    monkeypatch.setattr(
        pipeline,
        "authenticate_family_first_semantic_index_v1",
        lambda _root, _archive: "semantic",
    )
    monkeypatch.setattr(
        pipeline,
        "authenticate_family_first_ppocrv6_numeric_index_v3",
        lambda _root, _archive, *, model_cache: ("numeric", model_cache),
    )

    def build(*_args):
        calls["sweep"] += 1
        return evidence

    monkeypatch.setattr(
        pipeline.evidence_v1,
        "build_authenticated_family_first_accounting_evidence_sweep_v1",
        build,
    )
    monkeypatch.setattr(
        pipeline.mapping_v1,
        "_build_from_same_turn_authenticated_evidence_sweep_v1",
        lambda _root, same_turn, _family, _schema: (
            mapping
            if same_turn is evidence
            else pytest.fail("mapping did not consume the same-turn evidence object")
        ),
    )

    kwargs = {
        "model_cache": tmp_path / "models",
        "family_spec_path": Path("family.json"),
        "evaluation_spec_path": Path("evaluation.json"),
        "schema_binding_spec_path": Path("schema.json"),
    }
    built = pipeline.run_family_first_accounting_pipeline_v1(
        tmp_path,
        command="build",
        **kwargs,
    )
    assert built["source_traversal_count"] == 1
    assert calls["sweep"] == 1
    assert json.loads((tmp_path / "evidence.json").read_text()) == evidence
    assert json.loads((tmp_path / "mapping.json").read_text()) == mapping

    verified = pipeline.run_family_first_accounting_pipeline_v1(
        tmp_path,
        command="verify",
        **kwargs,
    )
    assert verified == built
    assert calls["sweep"] == 2


def test_pipeline_rolls_back_first_owned_artifact_if_second_publish_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = {"family_id": "F", "metrics": {}, "sweep_id": "s"}
    mapping = {"evidence_sweep_id": "s", "mapping_id": "m", "metrics": {}}
    evidence_path = tmp_path / "evidence.json"
    mapping_path = tmp_path / "mapping.json"
    original = pipeline.topology_cli._write_exclusive
    calls = 0

    def fail_second(path: Path, payload: bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected second publication failure")
        original(path, payload)

    monkeypatch.setattr(pipeline.topology_cli, "_write_exclusive", fail_second)
    with pytest.raises(OSError, match="injected"):
        pipeline._publish_pair(evidence_path, evidence, mapping_path, mapping)
    assert not evidence_path.exists()
    assert not mapping_path.exists()
