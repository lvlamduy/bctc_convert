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
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    GeminiAccountingFamilyStoreV1Error,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "scripts/experiments/run_gemini_json_equity_matrix_accounting_family_v1.py"
SPEC = importlib.util.spec_from_file_location("run_equity_matrix_family_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_parser_accepts_external_effective_frontier_root(tmp_path: Path) -> None:
    frontier = tmp_path / "effective.json"
    repair_root = tmp_path / "repair-root"
    args = runner._parser().parse_args(
        [
            "--corpus-index",
            str(tmp_path / "index.json"),
            "--artifact-root",
            str(tmp_path / "corpus"),
            "--effective-page-frontier",
            str(frontier),
            "--effective-page-artifact-root",
            str(repair_root),
            "--topology-spec",
            str(tmp_path / "topology.json"),
            "--evaluation-spec",
            str(tmp_path / "evaluation.json"),
            "--schema-binding-spec",
            str(tmp_path / "schema.json"),
            "--results-database",
            str(tmp_path / "results.sqlite3"),
            "--run-kind",
            "EXPERIMENTAL",
            "--output",
            str(tmp_path / "sweep.json"),
        ]
    )
    assert args.effective_page_frontier == frontier
    assert args.effective_page_artifact_root == repair_root


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


def test_historical_comparator_normalizes_family_movement_vocabulary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_sha256 = "a" * 64
    oracle = {
        "format_version": "fixture",
        "metrics": {"mapping_verified_count": 1},
        "trials": [
            {
                "document_provenance": "fixture",
                "source_pdf_sha256": source_sha256,
                "status": "VERIFIED_BY_CODEX",
                "verified_source_only_rows": [
                    {"label_evidence": [{"normalized_pixel_transcription": "tien thue dat"}]}
                ],
                "verified_mappings": [
                    {
                        "role": "OTHER_TAX",
                        "schema_binding": {"report_norm_id": 1278},
                        "values": [
                            {"axis_role": "OPENING", "normalized_value": 1},
                            {"axis_role": "PAYABLE_INCREASE", "normalized_value": 5},
                            {"axis_role": "PAID_DECREASE", "normalized_value": -3},
                            {"axis_role": "CLOSING_PAYABLE", "normalized_value": 4},
                            {"axis_role": "CLOSING_RECEIVABLE", "normalized_value": -1},
                            {"axis_role": "CLOSING", "normalized_value": 3},
                        ],
                    }
                ],
            }
        ],
    }
    monkeypatch.setattr(
        runner,
        "_historical_oracles",
        lambda: [({"format_version": "fixture"}, oracle)],
    )
    trials = [
        {
            "candidates": [
                {
                    "closure_receipt": {
                        "source_only_component_axes": [
                            {
                                "semantic_path": ["tien thue dat"],
                            }
                        ]
                    },
                    "mappings": [
                        {
                            "report_norm_id": 1278,
                            "role": "OTHER_TAX",
                            "values": [
                                {"axis_role": "OPENING", "coefficient": 1},
                                {"axis_role": "INCREASE", "coefficient": 5},
                                {"axis_role": "DECREASE", "coefficient": -3},
                                {"axis_role": "CLOSING", "coefficient": 3},
                            ],
                        }
                    ],
                }
            ],
            "document_ordinal": 1,
            "source_sha256": source_sha256,
            "status": runner.READY,
        }
    ]
    axes, refs = runner._historical_comparator_axis(
        trials=trials,
        compiled_specs={
            "component_report_norm_id_by_role": {"OTHER_TAX": 1278},
            "mapped_supplemental_movement_roles": [],
            "movement_roles": [
                "OPENING",
                "INCREASE",
                "DECREASE",
                "CLOSING",
                "CLOSING_OFFSET",
                "CLOSING_PAYABLE",
            ],
            "movement_total_report_norm_id_by_role": {},
        },
    )
    assert refs == [{"format_version": "fixture"}]
    assert axes["historical_documents"][0]["historical_source_only_disposition"] == ("EXACT")
    assert axes["historical_mappings"][0]["disposition"] == "EXACT"
    assert axes["historical_mappings"][0]["historical_axis"] == {
        "CLOSING": 3,
        "DECREASE": -3,
        "INCREASE": 5,
        "OPENING": 1,
    }
    assert axes["historical_mappings"][0]["historical_auxiliary_axis"] == {
        "CLOSING_OFFSET": -1,
        "CLOSING_PAYABLE": 4,
    }


def test_audit_inventory_keeps_query_unresolved_trial_without_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_historical_comparator_axis",
        lambda **_kwargs: (
            {"historical_documents": [], "historical_mappings": []},
            [],
        ),
    )
    axes, _refs = runner._audit_axes(
        trials=[
            {
                "candidates": [],
                "document_ordinal": 1,
                "reasons": ["DUPLICATE_MAPPED_COMPONENT_ROLE"],
                "source_logical_name": "fixture.pdf",
                "source_sha256": "a" * 64,
                "status": runner.UNRESOLVED,
            }
        ],
        compiled_specs={},
    )
    assert axes["unresolved_documents"] == [
        {
            "candidate_id": None,
            "component_regions": [],
            "document_ordinal": 1,
            "orientation": None,
            "reasons": ["DUPLICATE_MAPPED_COMPONENT_ROLE"],
            "source_logical_name": "fixture.pdf",
            "source_sha256": "a" * 64,
        }
    ]


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


def test_equity_store_requires_authenticated_sqlite_candidate_replay(tmp_path: Path) -> None:
    _database_path, _selected, evidence, trials, _compiled = _indexed_fixture(tmp_path)
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
    with pytest.raises(GeminiAccountingFamilyStoreV1Error, match="source-replayed family"):
        runner.ingest_gemini_accounting_family_sweep_v1(
            tmp_path / "results.sqlite3",
            sweep=sweep,
            corpus_index_ref={
                "path": "index.json",
                "sha256": "b" * 64,
                "size_bytes": 1,
            },
            implementation_refs=[],
            run_kind="EXPERIMENTAL",
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
        "axis_counts": copy.deepcopy(runner.PINNED_AXIS_COUNTS),
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
