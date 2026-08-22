from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.experiments import run_family_first_accounting_document_store_pipeline_v1 as subject


def _patch_specs(monkeypatch: pytest.MonkeyPatch) -> None:
    def load(_root: Path, path: Path):
        if "schema" in path.name:
            return {"family_id": "FAMILY", "kind": "schema"}
        if "evaluation" in path.name:
            return {"family_id": "FAMILY", "kind": "evaluation"}
        return {"family_id": "FAMILY", "kind": "family"}

    monkeypatch.setattr(subject.topology_cli, "_family_spec", load)
    monkeypatch.setattr(
        subject.evidence_cli,
        "_artifact_path",
        lambda _family, _evaluation: Path("evidence.json"),
    )
    monkeypatch.setattr(
        subject.mapping_cli,
        "_artifact_path",
        lambda _family, _evaluation, _schema: Path("mapping.json"),
    )


def test_document_store_pipeline_builds_and_replays_without_ocr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_specs(monkeypatch)
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
    calls = {"authenticate": 0, "build": 0}

    def authenticate(_root: Path):
        calls["authenticate"] += 1
        return object()

    def build(_cap, _family, _evaluation):
        calls["build"] += 1
        return evidence

    monkeypatch.setattr(
        subject.store_v1,
        "authenticate_family_first_document_evidence_store_v1",
        authenticate,
    )
    monkeypatch.setattr(
        subject.evidence_v1,
        "build_authenticated_family_first_accounting_evidence_sweep_from_document_store_v1",
        build,
    )
    monkeypatch.setattr(
        subject.mapping_v1,
        "_build_from_same_turn_authenticated_evidence_sweep_v1",
        lambda _root, same_turn, _family, _schema: (
            mapping
            if same_turn is evidence
            else pytest.fail("mapping did not consume the same-turn document-store evidence")
        ),
    )

    kwargs = {
        "family_spec_path": Path("family.json"),
        "evaluation_spec_path": Path("evaluation.json"),
        "schema_binding_spec_path": Path("schema.json"),
    }
    built = subject.run_family_first_accounting_document_store_pipeline_v1(
        tmp_path, command="build", **kwargs
    )
    assert built["upstream_ocr_replay_count"] == 0
    assert built["per_document_packet_root_recomputation_count"] == 140
    assert json.loads((tmp_path / "evidence.json").read_text()) == evidence
    assert json.loads((tmp_path / "mapping.json").read_text()) == mapping

    replayed = subject.run_family_first_accounting_document_store_pipeline_v1(
        tmp_path, command="verify", **kwargs
    )
    assert replayed == built
    assert calls == {"authenticate": 2, "build": 2}


def test_document_store_pipeline_refuses_existing_partial_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_specs(monkeypatch)
    (tmp_path / "mapping.json").write_text("occupied")

    with pytest.raises(ValueError, match="destination already exists"):
        subject.run_family_first_accounting_document_store_pipeline_v1(
            tmp_path,
            family_spec_path=Path("family.json"),
            evaluation_spec_path=Path("evaluation.json"),
            schema_binding_spec_path=Path("schema.json"),
            command="build",
        )
