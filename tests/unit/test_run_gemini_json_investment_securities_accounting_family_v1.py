from __future__ import annotations

import argparse
import copy
import importlib.util
import os
import shutil
import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_investment_securities_indexed_wiring_v1 import (
    _fixture as _indexed_fixture,
)
from test_gemini_json_investment_securities_indexed_wiring_v1 import (
    _json as _family_spec,
)

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    ROOT / "scripts/experiments/run_gemini_json_investment_securities_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location("run_investment_securities_family_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _authenticated_oracle_refs() -> list[dict[str, object]]:
    return [
        {
            **runner.PINNED_HISTORICAL_ORACLE,
            "expected_trial_count": runner.PINNED_HISTORICAL_ORACLE_TRIAL_COUNT,
        }
    ]


def _expansion_receipt(*, documents: int, candidates: int, pages: int) -> dict[str, object]:
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
        "oracle_authentication": {"refs": _authenticated_oracle_refs()},
        "policy": runner.DISJOINT_EXPANSION,
    }


def _strict_oracle_fixture() -> tuple[list[str], list[dict], dict[str, object]]:
    _ref, oracle = runner._historical_oracle()
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-investment-securities-topology-v1.json"),
        _family_spec("tm-investment-securities-evaluation-v1.json"),
        _family_spec("tm-investment-securities-schema-binding-v1.json"),
    )
    role_by_id = {
        report_norm_id: role for role, report_norm_id in compiled["bindings"].items()
    }
    sources = []
    trials = []
    for ordinal, oracle_trial in enumerate(oracle["trials"], start=1):
        source_sha256 = oracle_trial["source_pdf"]["sha256"]
        sources.append(source_sha256)
        mappings = []
        for historical in oracle_trial["verified_mappings"]:
            report_norm_id = historical["report_norm_id"]
            role = role_by_id[report_norm_id]
            mappings.append(
                {
                    "report_norm_id": report_norm_id,
                    "role": role,
                    "values": [
                        {"coefficient": value["normalized_value"]}
                        for value in historical["source_values"]
                    ],
                }
            )
        trials.append(
            {
                "candidates": [{"mappings": mappings}],
                "document_ordinal": ordinal,
                "source_sha256": source_sha256,
                "status": runner.READY,
            }
        )
    return sources, trials, compiled


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
        runner.RunGeminiJsonInvestmentSecuritiesAccountingFamilyV1Error,
        match="sidecar",
    ):
        with runner._authenticated_sqlite_snapshot(source, reference=reference):
            pass
    sidecar.unlink()

    original = tmp_path / "original.sqlite3"
    with pytest.raises(
        runner.RunGeminiJsonInvestmentSecuritiesAccountingFamilyV1Error,
        match="changed during use",
    ):
        with runner._authenticated_sqlite_snapshot(source, reference=reference):
            os.replace(source, original)
            shutil.copyfile(original, source)


def test_disjoint_expansion_authenticates_oracle_and_has_no_fake_match_count() -> None:
    sources = ["1" * 64, "2" * 64]
    axis, legacy_ref, receipt = runner._historical_comparator_axis(
        policy=runner.DISJOINT_EXPANSION,
        current_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        current_manifest_source_sha256s=sources,
        current_manifest_page_json_version_ids=["page-a", "page-b"],
        current_candidate_source_sha256s=[],
        current_replay_source_sha256s=[],
        trials=[{"source_sha256": source} for source in sources],
        compiled_specs={},
    )
    assert axis == []
    assert legacy_ref == runner.PINNED_HISTORICAL_ORACLE
    assert receipt["policy"] == runner.DISJOINT_EXPANSION
    assert receipt["disposition"] == runner.NOT_APPLICABLE_DISJOINT_CORPUS
    assert receipt["comparison_axis"] == []
    assert receipt["corpus_relation"]["overlap_count"] == 0
    assert receipt["corpus_relation"]["oracle_source_count"] == 8


def test_disjoint_expansion_rejects_partial_historical_overlap() -> None:
    _refs, oracle_rows = runner._normalised_historical_oracle_rows()
    sources = [oracle_rows[0]["source_sha256"], "4" * 64]
    with pytest.raises(ValueError, match="overlap only partially"):
        runner._historical_comparator_axis(
            policy=runner.DISJOINT_EXPANSION,
            current_manifest_index_id="gjfccmiv1:index:" + "5" * 64,
            current_manifest_source_sha256s=sources,
            current_manifest_page_json_version_ids=["page-a", "page-b"],
            current_candidate_source_sha256s=[],
            current_replay_source_sha256s=[],
            trials=[{"source_sha256": source} for source in sources],
            compiled_specs={},
        )


def test_strict_release_exactly_compares_all_eight_historical_sources() -> None:
    sources, trials, compiled = _strict_oracle_fixture()
    axis, legacy_ref, receipt = runner._historical_comparator_axis(
        policy=runner.STRICT_RELEASE,
        current_manifest_index_id="gjfccmiv1:index:" + "6" * 64,
        current_manifest_source_sha256s=sources,
        current_manifest_page_json_version_ids=[f"page-{ordinal}" for ordinal in range(8)],
        current_candidate_source_sha256s=sources,
        current_replay_source_sha256s=sources,
        trials=trials,
        compiled_specs=compiled,
    )
    assert legacy_ref == runner.PINNED_HISTORICAL_ORACLE
    assert len(axis) == 112
    assert all(item["disposition"] == "EXACT" for item in axis)
    assert runner.canonical_json_sha256_v1(axis) == (
        "6a5af179170b7e6ca0477632309906091c82b5da2279b665a27515704cadf8fb"
    )
    assert receipt["policy"] == runner.STRICT_RELEASE
    assert receipt["disposition"] == runner.EXACT_HISTORICAL_COMPARISON
    assert len(receipt["comparison_axis"]) == 8
    assert receipt["corpus_relation"]["overlap_count"] == 8


def test_strict_release_allows_complete_oracle_subset_of_larger_corpus() -> None:
    sources, trials, compiled = _strict_oracle_fixture()
    expansion_source = "8" * 64
    sources.append(expansion_source)
    trials.append(
        {
            "candidates": [],
            "document_ordinal": 9,
            "source_sha256": expansion_source,
            "status": runner.NOT_OBSERVED,
        }
    )
    axis, _legacy_ref, receipt = runner._historical_comparator_axis(
        policy=runner.STRICT_RELEASE,
        current_manifest_index_id="gjfccmiv1:index:" + "9" * 64,
        current_manifest_source_sha256s=sources,
        current_manifest_page_json_version_ids=[f"page-{ordinal}" for ordinal in range(9)],
        current_candidate_source_sha256s=sources[:-1],
        current_replay_source_sha256s=sources[:-1],
        trials=trials,
        compiled_specs=compiled,
    )
    assert len(axis) == 112
    assert receipt["corpus_relation"]["current_source_count"] == 9
    assert receipt["corpus_relation"]["overlap_count"] == 8


def test_strict_release_rejects_one_tampered_historical_value() -> None:
    sources, trials, compiled = _strict_oracle_fixture()
    trials[0]["candidates"][0]["mappings"][0]["values"][0]["coefficient"] += 1
    with pytest.raises(ValueError, match="not exact"):
        runner._historical_comparator_axis(
            policy=runner.STRICT_RELEASE,
            current_manifest_index_id="gjfccmiv1:index:" + "7" * 64,
            current_manifest_source_sha256s=sources,
            current_manifest_page_json_version_ids=[
                f"page-{ordinal}" for ordinal in range(8)
            ],
            current_candidate_source_sha256s=sources,
            current_replay_source_sha256s=sources,
            trials=trials,
            compiled_specs=compiled,
        )


def test_run_mode_gate_allows_expansion_only_for_experimental() -> None:
    with pytest.raises(
        runner.RunGeminiJsonInvestmentSecuritiesAccountingFamilyV1Error,
        match="requires STRICT_RELEASE",
    ):
        runner.run(
            argparse.Namespace(
                historical_comparator_policy=runner.DISJOINT_EXPANSION,
                run_kind="OFFICIAL",
            )
        )


def test_audit_content_rejects_changed_axis_without_matching_seals() -> None:
    axes = {
        "clusters": [],
        "equations": [],
        "historical_comparator": [],
        "mappings": [],
        "source_row_dispositions": [],
        "trial_dispositions": [],
    }
    material = {
        "axes": axes,
        "axis_counts": {name: 0 for name in axes},
        "axis_sha256": {name: runner.canonical_json_sha256_v1(axis) for name, axis in axes.items()},
        "audit_metrics": {
            "equation_count": 0,
            "historical_value_match_count": None,
            "mapping_count": 0,
            "not_observed_count": 0,
            "ready_count": 0,
            "source_row_disposition_count": 0,
            "source_visible_blank_value_omission_count": 0,
            "undisposed_visible_source_row_count": 0,
            "unresolved_count": 0,
        },
        "claim_boundary": "fixture",
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": _expansion_receipt(
            documents=0, candidates=0, pages=0
        ),
        "historical_oracle_ref": dict(runner.PINNED_HISTORICAL_ORACLE),
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
        "audit_id": "gjfiseav1:audit:" + runner.canonical_json_sha256_v1(material),
    }
    assert runner.validate_investment_securities_experimental_audit_content_v1(value) == value
    value["axes"]["mappings"].append({"coefficient": 999})
    with pytest.raises(
        runner.RunGeminiJsonInvestmentSecuritiesAccountingFamilyV1Error,
        match="axis seal",
    ):
        runner.validate_investment_securities_experimental_audit_content_v1(value)


def test_audit_replay_rejects_coherent_axis_and_embedded_schema_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, selected, evidence, trials, compiled = _indexed_fixture(tmp_path)
    monkeypatch.setattr(
        runner,
        "_historical_comparator_axis",
        lambda **_kwargs: (
            [],
            dict(runner.PINNED_HISTORICAL_ORACLE),
            _expansion_receipt(
                documents=evidence["query_receipt"]["selected_document_count"],
                candidates=evidence["query_receipt"]["accepted_cluster_count"],
                pages=evidence["query_receipt"]["selected_page_count"],
            ),
        ),
    )
    topology = _family_spec("tm-investment-securities-topology-v1.json")
    evaluation = _family_spec("tm-investment-securities-evaluation-v1.json")
    schema = _family_spec("tm-investment-securities-schema-binding-v1.json")
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
    audit = runner.build_investment_securities_experimental_audit_v1(
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
    assert audit["axes"]["historical_comparator"] == []
    assert audit["audit_metrics"]["historical_value_match_count"] is None
    assert audit["audit_metrics"]["ready_count"] == sum(
        trial["status"] == runner.READY for trial in trials
    )
    assert audit["audit_metrics"]["not_observed_count"] == sum(
        trial["status"] == runner.NOT_OBSERVED for trial in trials
    )
    assert audit["audit_metrics"]["unresolved_count"] == sum(
        trial["status"] == runner.UNRESOLVED for trial in trials
    )
    assert audit["audit_metrics"]["undisposed_visible_source_row_count"] == 0
    assert len(audit["axes"]["trial_dispositions"]) == len(trials)
    assert (
        audit["historical_comparator_policy_receipt"]["disposition"]
        == runner.NOT_APPLICABLE_DISJOINT_CORPUS
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
        runner.validate_investment_securities_experimental_audit_replay_v1(audit, **replay_args)
        == audit
    )

    forged_audit = copy.deepcopy(audit)
    forged_audit["axes"]["mappings"][0]["coefficients"][0] += 777
    forged_audit["axis_sha256"]["mappings"] = runner.canonical_json_sha256_v1(
        forged_audit["axes"]["mappings"]
    )
    material = {key: value for key, value in forged_audit.items() if key != "audit_id"}
    forged_audit["audit_id"] = "gjfiseav1:audit:" + runner.canonical_json_sha256_v1(material)
    runner.validate_investment_securities_experimental_audit_content_v1(forged_audit)
    with pytest.raises(
        runner.RunGeminiJsonInvestmentSecuritiesAccountingFamilyV1Error,
        match="does not replay exactly",
    ):
        runner.validate_investment_securities_experimental_audit_replay_v1(
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
        runner.RunGeminiJsonInvestmentSecuritiesAccountingFamilyV1Error,
        match="caller and embedded compiled specs differ",
    ):
        runner.validate_investment_securities_experimental_audit_replay_v1(
            audit,
            **{
                **replay_args,
                "sweep": forged_sweep,
                "indexed_query_evidence": forged_sweep["indexed_query_evidence"],
                "trials": forged_sweep["trials"],
            },
        )
