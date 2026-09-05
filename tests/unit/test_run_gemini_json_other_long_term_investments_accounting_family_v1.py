from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_other_long_term_investments_indexed_wiring_v1 import (
    _fixture as _indexed_fixture,
)
from test_gemini_json_other_long_term_investments_indexed_wiring_v1 import (
    _json as _family_spec,
)

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    ROOT / "scripts/experiments/run_gemini_json_other_long_term_investments_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_other_long_term_investments_family_v1", RUNNER_PATH
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _oracle_refs() -> list[dict]:
    return [reference for reference, _oracle in runner._historical_oracles()]


def _expansion_receipt(*, documents: int, candidates: int, pages: int) -> dict:
    return {
        "comparison_axis": [],
        "corpus_relation": {"overlap_count": 0},
        "current_axis_validation": {
            "candidate_source_count": candidates,
            "manifest_document_count": documents,
            "replay_source_count": candidates,
            "selected_page_json_version_count": pages,
            "trial_source_count": documents,
        },
        "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
        "format_version": runner.HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION,
        "oracle_authentication": {"refs": _oracle_refs()},
        "policy": runner.DISJOINT_EXPANSION,
    }


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
        runner.RunGeminiJsonOtherLongTermInvestmentsAccountingFamilyV1Error,
        match="sidecar",
    ):
        with runner._authenticated_sqlite_snapshot(source, reference=reference):
            pass
    sidecar.unlink()

    original = tmp_path / "original.sqlite3"
    with pytest.raises(
        runner.RunGeminiJsonOtherLongTermInvestmentsAccountingFamilyV1Error,
        match="changed during use",
    ):
        with runner._authenticated_sqlite_snapshot(source, reference=reference):
            os.replace(source, original)
            shutil.copyfile(original, source)


def _repair_manifest_fixture(tmp_path: Path) -> tuple[dict, dict, dict]:
    image = {
        "height": 200,
        "media_type": "image/png",
        "render_dpi": 300,
        "sha256": "a" * 64,
        "size_bytes": 123,
        "width": 100,
    }
    repair = {
        "page_image": image,
        "page_json_version_id": "gfpstorev1:json:" + "b" * 64,
        "physical_page": 2,
        "repair_id": "gjfoltisrv1:repair:" + "c" * 64,
        "source_logical_name": "bank/report.pdf",
        "source_sha256": "d" * 64,
    }
    manifest = {
        "document_manifest_id": "manifest-a",
        "page_count": 2,
        "pages": [
            {
                "image": {**image, "sha256": "e" * 64},
                "page_json_version_id": "gfpstorev1:json:" + "f" * 64,
                "physical_page": 1,
            },
            {
                "image": image,
                "page_json_version_id": repair["page_json_version_id"],
                "physical_page": repair["physical_page"],
            },
        ],
    }
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_bytes(payload)
    index = {
        "documents": [
            {
                "document_manifest_id": manifest["document_manifest_id"],
                "document_manifest_ref": {
                    "path": manifest_path.name,
                    "sha256": sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                },
                "page_count": 2,
                "relative_path": repair["source_logical_name"],
                "source_sha256": repair["source_sha256"],
            }
        ]
    }
    compiled = {"source_repair_overlay": {"repairs": [repair]}}
    return index, compiled, repair


def test_source_repair_manifest_authentication_and_application_are_exhaustive(
    tmp_path: Path,
) -> None:
    index, compiled, repair = _repair_manifest_fixture(tmp_path)
    expected = runner._authenticate_source_repair_manifest_axis_v1(
        index=index,
        artifact_root=tmp_path,
        compiled_specs=compiled,
    )
    assert expected == [repair["repair_id"]]
    trial = {
        "candidates": [
            {
                "closure_receipt": {
                    "source_repair_overlay_receipts": [{"repair_id": repair["repair_id"]}]
                }
            }
        ]
    }
    assert (
        runner._validate_source_repair_application_axis_v1(
            expected_repair_ids=expected,
            trials=[trial],
        )
        == expected
    )
    with pytest.raises(
        runner.RunGeminiJsonOtherLongTermInvestmentsAccountingFamilyV1Error,
        match="application axis is incomplete",
    ):
        runner._validate_source_repair_application_axis_v1(
            expected_repair_ids=expected,
            trials=[{"candidates": []}],
        )
    with pytest.raises(
        runner.RunGeminiJsonOtherLongTermInvestmentsAccountingFamilyV1Error,
        match="application axis is incomplete",
    ):
        runner._validate_source_repair_application_axis_v1(
            expected_repair_ids=expected,
            trials=[trial, copy.deepcopy(trial)],
        )


@pytest.mark.parametrize("drift", ["path", "page_version", "image"])
def test_source_repair_manifest_authentication_rejects_asymmetric_drift(
    tmp_path: Path,
    drift: str,
) -> None:
    index, compiled, _repair = _repair_manifest_fixture(tmp_path)
    if drift == "path":
        index["documents"][0]["relative_path"] = "bank/another-report.pdf"
        expected = "document path drifted"
    else:
        manifest_path = tmp_path / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        if drift == "page_version":
            manifest["pages"][1]["page_json_version_id"] = "gfpstorev1:json:" + "9" * 64
        else:
            manifest["pages"][1]["image"]["sha256"] = "8" * 64
        payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode()
        manifest_path.write_bytes(payload)
        index["documents"][0]["document_manifest_ref"].update(
            {"sha256": sha256(payload).hexdigest(), "size_bytes": len(payload)}
        )
        expected = "page/image drifted"
    with pytest.raises(
        runner.RunGeminiJsonOtherLongTermInvestmentsAccountingFamilyV1Error,
        match=expected,
    ):
        runner._authenticate_source_repair_manifest_axis_v1(
            index=index,
            artifact_root=tmp_path,
            compiled_specs=compiled,
        )


def test_audit_content_rejects_changed_axis_without_matching_seals() -> None:
    axes = {
        "clusters": [],
        "equations": [],
        "historical_comparator": [],
        "mappings": [],
    }
    material = {
        "axes": axes,
        "axis_counts": {name: 0 for name in axes},
        "axis_sha256": {name: runner.canonical_json_sha256_v1(axis) for name, axis in axes.items()},
        "audit_metrics": {},
        "claim_boundary": "fixture",
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": _expansion_receipt(
            documents=0, candidates=0, pages=0
        ),
        "historical_oracle_refs": _oracle_refs(),
        "query_evidence_id": "fixture",
        "query_receipt": {
            "accepted_cluster_count": 0,
            "selected_document_count": 0,
            "selected_page_count": 0,
        },
        "selected_page_json_frontier_sha256": "0" * 64,
        "spec_refs": {},
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {},
    }
    value = {
        **material,
        "audit_id": "gjfoltieav1:audit:" + runner.canonical_json_sha256_v1(material),
    }
    assert runner.validate_other_long_term_investments_experimental_audit_content_v1(value) == value
    value["axes"]["mappings"].append({"coefficient": 999})
    with pytest.raises(
        runner.RunGeminiJsonOtherLongTermInvestmentsAccountingFamilyV1Error,
        match="axis seal",
    ):
        runner.validate_other_long_term_investments_experimental_audit_content_v1(value)


def test_expansion_comparator_authenticates_oracles_and_proves_zero_overlap() -> None:
    current_sources = ["1" * 64, "2" * 64]
    axis, refs, receipt = runner._historical_comparator_axis(
        policy=runner.DISJOINT_EXPANSION,
        current_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        current_manifest_source_sha256s=current_sources,
        current_manifest_page_json_version_ids=["page-a", "page-b"],
        current_candidate_source_sha256s=[],
        current_replay_source_sha256s=[],
        trials=[{"source_sha256": source} for source in current_sources],
        compiled_specs={},
    )
    assert axis == []
    assert refs == _oracle_refs()
    assert receipt["policy"] == runner.DISJOINT_EXPANSION
    assert receipt["disposition"] == runner.NOT_APPLICABLE_DISJOINT_CORPUS
    assert receipt["corpus_relation"]["oracle_source_count"] == 16
    assert receipt["corpus_relation"]["overlap_count"] == 0
    assert receipt["current_axis_validation"]["trial_source_count"] == 2


def test_expansion_comparator_rejects_partial_historical_overlap() -> None:
    _refs, oracle_rows = runner._normalised_historical_oracle_rows()
    current_sources = [oracle_rows[0]["source_sha256"], "4" * 64]
    with pytest.raises(ValueError, match="overlap only partially"):
        runner._historical_comparator_axis(
            policy=runner.DISJOINT_EXPANSION,
            current_manifest_index_id="gjfccmiv1:index:" + "5" * 64,
            current_manifest_source_sha256s=current_sources,
            current_manifest_page_json_version_ids=["page-a", "page-b"],
            current_candidate_source_sha256s=[],
            current_replay_source_sha256s=[],
            trials=[{"source_sha256": source} for source in current_sources],
            compiled_specs={},
        )


def test_audit_replay_rejects_coherent_axis_and_embedded_schema_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_historical_comparator_axis",
        lambda **_kwargs: (
            [],
            _oracle_refs(),
            _expansion_receipt(
                documents=evidence["query_receipt"]["selected_document_count"],
                candidates=evidence["query_receipt"]["accepted_cluster_count"],
                pages=evidence["query_receipt"]["selected_page_count"],
            ),
        ),
    )
    database, selected, evidence, trials, compiled = _indexed_fixture(tmp_path)
    topology = _family_spec("tm-other-long-term-investments-topology-v1.json")
    evaluation = _family_spec("tm-other-long-term-investments-evaluation-v1.json")
    schema = _family_spec("tm-other-long-term-investments-schema-binding-v1.json")
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
    audit = runner.build_other_long_term_investments_experimental_audit_v1(
        sweep=sweep,
        sweep_output=sweep_output,
        historical_comparator_policy=runner.DISJOINT_EXPANSION,
        current_manifest_index_id=sweep["corpus_manifest_index_id"],
        current_manifest_source_sha256s=[trial["source_sha256"] for trial in trials],
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
        "historical_comparator_policy": runner.DISJOINT_EXPANSION,
        "current_manifest_index_id": sweep["corpus_manifest_index_id"],
        "current_manifest_source_sha256s": [trial["source_sha256"] for trial in trials],
        "selected_page_json_version_ids": selected,
        "indexed_query_evidence": evidence,
        "trials": trials,
        "compiled_specs": compiled,
        "spec_refs": spec_refs,
    }
    assert (
        runner.validate_other_long_term_investments_experimental_audit_replay_v1(
            audit, **replay_args
        )
        == audit
    )

    forged_audit = copy.deepcopy(audit)
    forged_audit["axes"]["mappings"][0]["coefficients"][0] += 777
    forged_audit["axis_sha256"]["mappings"] = runner.canonical_json_sha256_v1(
        forged_audit["axes"]["mappings"]
    )
    material = {key: value for key, value in forged_audit.items() if key != "audit_id"}
    forged_audit["audit_id"] = "gjfoltieav1:audit:" + runner.canonical_json_sha256_v1(material)
    runner.validate_other_long_term_investments_experimental_audit_content_v1(forged_audit)
    with pytest.raises(
        runner.RunGeminiJsonOtherLongTermInvestmentsAccountingFamilyV1Error,
        match="does not replay exactly",
    ):
        runner.validate_other_long_term_investments_experimental_audit_replay_v1(
            forged_audit, **replay_args
        )

    forged_sweep = copy.deepcopy(sweep)
    forged_sweep["specs"]["schema_binding"]["value"]["role_bindings"][0]["report_norm_id"] = 999999
    forged_sweep["specs"]["schema_binding"]["sha256"] = runner.canonical_json_sha256_v1(
        forged_sweep["specs"]["schema_binding"]["value"]
    )
    sweep_material = {key: value for key, value in forged_sweep.items() if key != "sweep_id"}
    forged_sweep["sweep_id"] = "gjfafsv1:sweep:" + runner.canonical_json_sha256_v1(sweep_material)
    with pytest.raises(
        runner.RunGeminiJsonOtherLongTermInvestmentsAccountingFamilyV1Error,
        match="caller and embedded compiled specs differ",
    ):
        runner.validate_other_long_term_investments_experimental_audit_replay_v1(
            audit,
            **{
                **replay_args,
                "sweep": forged_sweep,
                "indexed_query_evidence": forged_sweep["indexed_query_evidence"],
                "trials": forged_sweep["trials"],
            },
        )
