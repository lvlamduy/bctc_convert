from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

import bctc_ai.storage.gemini_accounting_family_store_v1 as family_store
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    evaluate_gemini_json_flat_family_table_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    SourceObservationMappingContractError,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    GeminiAccountingFamilyStoreV1Error,
    _run_checked_source_replay_adapter_v1,
    gemini_accounting_family_store_summary_v1,
    ingest_gemini_accounting_family_sweep_v1,
    load_gemini_accounting_family_sweep_v1,
    record_gemini_accounting_family_export_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sweep() -> dict:
    topology = _json("config/families/tm-cash-precious-metals-topology-v1.json")
    evaluation = _json("config/families/tm-cash-precious-metals-evaluation-v1.json")
    schema = _json("config/families/tm-cash-precious-metals-schema-binding-v1.json")
    page = {
        "status": "FINANCIAL_NOTE_CONTENT",
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "title_exact": "TIỀN MẶT, VÀNG BẠC, ĐÁ QUÝ",
                "tables": [
                    {
                        "columns": [
                            {"header_path_exact": ["2025"], "value_kind": "MONEY"},
                            {"header_path_exact": ["2024"], "value_kind": "MONEY"},
                        ],
                        "continuation": "NONE",
                        "rows": [
                            {
                                "hierarchy_path_exact": ["Tiền mặt bằng VND"],
                                "label_exact": "Tiền mặt bằng VND",
                                "row_kind": "ITEM",
                                "values_exact": ["100", "90"],
                            },
                            {
                                "hierarchy_path_exact": ["Tiền mặt bằng ngoại tệ"],
                                "label_exact": "Tiền mặt bằng ngoại tệ",
                                "row_kind": "ITEM",
                                "values_exact": ["20", "10"],
                            },
                            {
                                "hierarchy_path_exact": ["Vàng tiền tệ"],
                                "label_exact": "Vàng tiền tệ",
                                "row_kind": "ITEM",
                                "values_exact": ["-", "-"],
                            },
                            {
                                "hierarchy_path_exact": [None],
                                "label_exact": None,
                                "row_kind": "TOTAL",
                                "values_exact": ["120", "100"],
                            },
                        ],
                        "title_exact": None,
                        "unit_exact": "Triệu đồng",
                    }
                ],
            }
        ],
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
    }
    candidate = evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "1" * 64,
        physical_page=7,
        section_id="s1",
        table_id="t1",
        compiled_specs=compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema),
    )
    assert candidate["status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    trial = {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": candidate["mappings"],
        "reasons": [],
        "selected_candidate_id": candidate["candidate_id"],
        "source_logical_name": "ACB/2025/example.pdf",
        "source_sha256": "2" * 64,
        "status": candidate["status"],
    }
    return build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[trial],
    )


def _reference(name: str, digit: str) -> dict:
    return {"path": name, "sha256": digit * 64, "size_bytes": 123}


def _replay_adapter_fixture_v1(**_: object) -> list[dict]:
    return [{"document_ordinal": 1, "status": "NOT_OBSERVED"}]


def _adapter_reference() -> dict:
    payload = Path(__file__).read_bytes()
    return {
        "path": "tests/unit/test_gemini_accounting_family_store_v1.py",
        "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def test_source_replay_adapter_is_byte_bound_and_must_rebuild_exact_trials() -> None:
    reference = _adapter_reference()
    expected = _replay_adapter_fixture_v1()
    _run_checked_source_replay_adapter_v1(
        _replay_adapter_fixture_v1,
        adapter_ref=reference,
        implementation_refs=[reference],
        source_page_database=Path("source.sqlite3"),
        selected_page_json_version_ids=["gfpstorev1:json:" + "1" * 64],
        compiled_specs={"family_id": "EXAMPLE"},
        indexed_query_evidence={"accepted_clusters": []},
        expected_trials=expected,
    )

    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="returned a different trial axis",
    ):
        _run_checked_source_replay_adapter_v1(
            lambda **_: [],
            adapter_ref=reference,
            implementation_refs=[reference],
            source_page_database=Path("source.sqlite3"),
            selected_page_json_version_ids=["gfpstorev1:json:" + "1" * 64],
            compiled_specs={"family_id": "EXAMPLE"},
            indexed_query_evidence={"accepted_clusters": []},
            expected_trials=expected,
        )


def test_source_replay_adapter_rejects_unbound_or_path_drifted_implementation() -> None:
    reference = _adapter_reference()
    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="is not an implementation reference",
    ):
        _run_checked_source_replay_adapter_v1(
            _replay_adapter_fixture_v1,
            adapter_ref=reference,
            implementation_refs=[],
            source_page_database=Path("source.sqlite3"),
            selected_page_json_version_ids=["gfpstorev1:json:" + "1" * 64],
            compiled_specs={"family_id": "EXAMPLE"},
            indexed_query_evidence={"accepted_clusters": []},
            expected_trials=_replay_adapter_fixture_v1(),
        )

    drifted = {**reference, "path": "tests/unit/not-the-adapter.py"}
    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="implementation path drifted",
    ):
        _run_checked_source_replay_adapter_v1(
            _replay_adapter_fixture_v1,
            adapter_ref=drifted,
            implementation_refs=[drifted],
            source_page_database=Path("source.sqlite3"),
            selected_page_json_version_ids=["gfpstorev1:json:" + "1" * 64],
            compiled_specs={"family_id": "EXAMPLE"},
            indexed_query_evidence={"accepted_clusters": []},
            expected_trials=_replay_adapter_fixture_v1(),
        )


def test_ingest_enforces_source_observation_contract_before_store_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def reject(_: object) -> None:
        raise SourceObservationMappingContractError("invented blank value")

    monkeypatch.setattr(
        family_store,
        "validate_source_observation_mapping_contract_v1",
        reject,
    )
    database = tmp_path / "families.sqlite3"
    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="violates the source-observation mapping contract",
    ):
        ingest_gemini_accounting_family_sweep_v1(
            database,
            sweep=_sweep(),
            corpus_index_ref=_reference("corpus-index.json", "4"),
            implementation_refs=[_reference("engine.py", "5")],
            run_kind="EXPERIMENTAL",
        )
    assert not database.exists()


def test_family_sweep_is_stored_before_export_with_full_trace(tmp_path: Path) -> None:
    database = tmp_path / "families.sqlite3"
    sweep = _sweep()
    stored = ingest_gemini_accounting_family_sweep_v1(
        database,
        sweep=sweep,
        corpus_index_ref=_reference("corpus-index.json", "4"),
        implementation_refs=[
            _reference("runner.py", "5"),
            _reference("engine.py", "6"),
        ],
        run_kind="OFFICIAL",
    )
    assert load_gemini_accounting_family_sweep_v1(database, stored["family_run_id"]) == sweep
    assert gemini_accounting_family_store_summary_v1(database) == {
        "current": [
            {
                "family_id": "CASH_PRECIOUS_METALS",
                "family_run_id": stored["family_run_id"],
                "sweep_id": sweep["sweep_id"],
                "ready_count": 1,
                "not_observed_count": 0,
                "unresolved_count": 0,
                "mapping_count": 4,
            }
        ],
        "documents_across_runs": 1,
        "family_count": 1,
        "mapping_count_across_runs": 4,
        "run_count": 1,
    }
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM family_trial").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM family_candidate").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM family_mapping").fetchone()[0] == 4
        assert connection.execute("SELECT COUNT(*) FROM family_run_execution").fetchone()[0] == 1

    output = tmp_path / "family.json"
    output.write_bytes(canonical_json_bytes_v1(sweep) + b"\n")
    export = record_gemini_accounting_family_export_v1(
        database, family_run_id=stored["family_run_id"], output_path=output
    )
    assert export["size_bytes"] == output.stat().st_size

    canonical_output = tmp_path / "family-canonical.json"
    canonical_output.write_bytes(canonical_json_bytes_v1(sweep))
    canonical_export = record_gemini_accounting_family_export_v1(
        database,
        family_run_id=stored["family_run_id"],
        output_path=canonical_output,
    )
    assert canonical_export["size_bytes"] == canonical_output.stat().st_size


def test_experimental_history_does_not_replace_current_and_tamper_fails(
    tmp_path: Path,
) -> None:
    database = tmp_path / "families.sqlite3"
    sweep = _sweep()
    first = ingest_gemini_accounting_family_sweep_v1(
        database,
        sweep=sweep,
        corpus_index_ref=_reference("corpus-index.json", "4"),
        implementation_refs=[_reference("engine-v1.py", "5")],
        run_kind="OFFICIAL",
    )
    second = ingest_gemini_accounting_family_sweep_v1(
        database,
        sweep=sweep,
        corpus_index_ref=_reference("corpus-index.json", "4"),
        implementation_refs=[_reference("engine-v2.py", "6")],
        run_kind="EXPERIMENTAL",
    )
    assert first["family_run_id"] != second["family_run_id"]
    summary = gemini_accounting_family_store_summary_v1(database)
    assert summary["run_count"] == 2
    assert summary["current"][0]["family_run_id"] == first["family_run_id"]

    output = tmp_path / "tampered.json"
    tampered = deepcopy(sweep)
    tampered["metrics"]["mapping_count"] += 1
    output.write_bytes(canonical_json_bytes_v1(tampered) + b"\n")
    with pytest.raises(GeminiAccountingFamilyStoreV1Error, match="does not equal"):
        record_gemini_accounting_family_export_v1(
            database, family_run_id=first["family_run_id"], output_path=output
        )
