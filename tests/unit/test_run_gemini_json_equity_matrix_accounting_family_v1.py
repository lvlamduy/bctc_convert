from __future__ import annotations

import copy
import importlib.util
import os
import shutil
import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_equity_matrix_accounting_family_v1 import _json as _family_spec
from test_gemini_json_equity_matrix_indexed_wiring_v1 import _fixture as _indexed_fixture

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "scripts/experiments/run_gemini_json_equity_matrix_accounting_family_v1.py"
SPEC = importlib.util.spec_from_file_location("run_equity_matrix_family_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _database(path: Path) -> dict[str, object]:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE authority(value TEXT NOT NULL)")
    connection.execute("INSERT INTO authority VALUES ('source-a')")
    connection.commit()
    connection.close()
    payload = path.read_bytes()
    return {"path": path.name, "sha256": sha256(payload).hexdigest(), "size_bytes": len(payload)}


def test_authenticated_snapshot_is_one_immutable_source_view(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    reference = _database(source)
    with runner._authenticated_sqlite_snapshot(source, reference=reference) as guard:
        assert guard.path != source
        assert guard.path.read_bytes() == source.read_bytes()
        assert oct(guard.path.stat().st_mode & 0o777) == "0o444"
        connection = sqlite3.connect(f"file:{guard.path}?mode=ro", uri=True)
        assert connection.execute("SELECT value FROM authority").fetchone()[0] == "source-a"
        connection.close()
        guard.validate()


def test_authenticated_snapshot_rejects_sidecar_and_path_replacement(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    reference = _database(source)
    sidecar = Path(f"{source}-wal")
    sidecar.write_bytes(b"not-authoritative")
    with pytest.raises(
        runner.RunGeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="sidecar",
    ):
        with runner._authenticated_sqlite_snapshot(source, reference=reference):
            pass
    sidecar.unlink()

    original = tmp_path / "original.sqlite3"
    with pytest.raises(
        runner.RunGeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="changed during use",
    ):
        with runner._authenticated_sqlite_snapshot(source, reference=reference):
            os.replace(source, original)
            shutil.copyfile(original, source)


def test_audit_content_rejects_changed_axis_without_matching_seals() -> None:
    axes = {
        "alignments": [],
        "clusters": [],
        "equations": [],
        "historical_documents": [],
        "historical_mappings": [],
        "mappings": [],
        "period_blocks": [],
        "unresolved_documents": [],
    }
    material = {
        "axes": axes,
        "axis_counts": {name: 0 for name in axes},
        "axis_sha256": {name: runner.canonical_json_sha256_v1(axis) for name, axis in axes.items()},
        "audit_metrics": {},
        "claim_boundary": "fixture",
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_oracle_refs": [],
        "query_evidence_id": "fixture",
        "query_receipt": {},
        "selected_page_json_frontier_sha256": "0" * 64,
        "spec_refs": {},
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {},
    }
    value = {**material, "audit_id": "gjeqmeav1:audit:" + runner.canonical_json_sha256_v1(material)}
    assert runner.validate_equity_matrix_experimental_audit_content_v1(value) == value
    value["axes"]["mappings"].append({"coefficient": 999})
    with pytest.raises(
        runner.RunGeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="axis seal",
    ):
        runner.validate_equity_matrix_experimental_audit_content_v1(value)


def test_audit_replay_rejects_coherent_axis_and_embedded_schema_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_historical_comparator_axis",
        lambda **_kwargs: (
            {"historical_documents": [], "historical_mappings": []},
            [{"fixture": "historical-oracle"}],
        ),
    )
    database, selected, evidence, trials, compiled = _indexed_fixture(tmp_path)
    topology = _family_spec("tm-capital-and-funds-topology-v1.json")
    evaluation = _family_spec("tm-capital-and-funds-evaluation-v1.json")
    schema = _family_spec("tm-capital-and-funds-schema-binding-v1.json")
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
    audit = runner.build_equity_matrix_experimental_audit_v1(
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
    assert runner.validate_equity_matrix_experimental_audit_replay_v1(audit, **replay_args) == audit

    forged_audit = copy.deepcopy(audit)
    forged_audit["axes"]["mappings"][0]["coefficients"][0] += 777
    forged_audit["axis_sha256"]["mappings"] = runner.canonical_json_sha256_v1(
        forged_audit["axes"]["mappings"]
    )
    material = {key: value for key, value in forged_audit.items() if key != "audit_id"}
    forged_audit["audit_id"] = "gjeqmeav1:audit:" + runner.canonical_json_sha256_v1(material)
    runner.validate_equity_matrix_experimental_audit_content_v1(forged_audit)
    with pytest.raises(
        runner.RunGeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="does not replay exactly",
    ):
        runner.validate_equity_matrix_experimental_audit_replay_v1(forged_audit, **replay_args)

    forged_sweep = copy.deepcopy(sweep)
    forged_sweep["specs"]["schema_binding"]["value"]["family_root_report_norm_id"] = 999999
    forged_sweep["specs"]["schema_binding"]["sha256"] = runner.canonical_json_sha256_v1(
        forged_sweep["specs"]["schema_binding"]["value"]
    )
    sweep_material = {key: value for key, value in forged_sweep.items() if key != "sweep_id"}
    forged_sweep["sweep_id"] = "gjfafsv1:sweep:" + runner.canonical_json_sha256_v1(sweep_material)
    with pytest.raises(
        (runner.RunGeminiJsonEquityMatrixAccountingFamilyV1Error, ValueError),
        match="schema binding drifted|caller and embedded compiled specs differ",
    ):
        runner.validate_equity_matrix_experimental_audit_replay_v1(
            audit,
            **{
                **replay_args,
                "sweep": forged_sweep,
                "indexed_query_evidence": forged_sweep["indexed_query_evidence"],
                "trials": forged_sweep["trials"],
            },
        )


def test_release_pins_bind_all_transparent_axes(monkeypatch: pytest.MonkeyPatch) -> None:
    selected_ids: list[str] = []
    monkeypatch.setattr(
        runner,
        "PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256",
        runner.canonical_json_sha256_v1(selected_ids),
    )
    index = {"corpus_manifest_index_id": runner.PINNED_CORPUS_MANIFEST_INDEX_ID}
    sweep = {"metrics": copy.deepcopy(runner.PINNED_RELEASE_METRICS)}
    indexed = {"query_receipt": copy.deepcopy(runner.PINNED_QUERY_RECEIPT)}
    audit = {
        "audit_metrics": copy.deepcopy(runner.PINNED_RELEASE_AUDIT_METRICS),
        "axis_counts": {
            "alignments": 9,
            "clusters": 137,
            "equations": 2252,
            "historical_documents": 16,
            "historical_mappings": 139,
            "mappings": 1295,
            "period_blocks": 95,
            "unresolved_documents": 3,
        },
        "axis_sha256": copy.deepcopy(runner.PINNED_AXIS_SHA256),
    }
    runner._assert_release_pins(
        index=index,
        selected_ids=selected_ids,
        sweep=sweep,
        indexed=indexed,
        audit=audit,
    )
    audit["axis_sha256"]["unresolved_documents"] = "0" * 64
    with pytest.raises(
        runner.RunGeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="axis_sha256",
    ):
        runner._assert_release_pins(
            index=index,
            selected_ids=selected_ids,
            sweep=sweep,
            indexed=indexed,
            audit=audit,
        )
