from __future__ import annotations

import copy
import json
import os
import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_gemini_json_segment_report_matrix_v1 import VERSION_A, _compiled, _record

from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    initialize_gemini_accounting_family_store_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    initialize_gemini_financial_page_store_v1,
    query_selected_equity_matrix_family_regions_v1,
)
from scripts.experiments import (
    run_gemini_json_segment_report_accounting_family_v1 as runner,
)

ROOT = Path(__file__).resolve().parents[2]


def _spec(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_text())


def _triplet() -> tuple[dict, dict, dict]:
    return (
        _spec("tm-consolidated-segment-report-topology-v1.json"),
        _spec("tm-consolidated-segment-report-evaluation-v1.json"),
        _spec("tm-consolidated-segment-report-schema-binding-v1.json"),
    )


def _indexed_fixture(tmp_path: Path) -> tuple[Path, list[str], dict, list[dict], dict]:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    record = _record(version=VERSION_A, page=1, year=2025)
    stored = _ingest(
        database,
        page_json=record["page_json"],
        source_logical_name=record["source_logical_name"],
        source_sha256=record["source_sha256"],
    )
    selected = [stored["page_json_version_id"]]
    compiled = _compiled()
    indexed = query_selected_equity_matrix_family_regions_v1(
        database,
        selected_page_json_version_ids=selected,
        compiled_specs=compiled,
    )
    cluster = indexed["accepted_clusters"][0]
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={stored["page_json_version_id"]: record["page_json"]},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
            cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
        ),
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    trials = runner._trials(
        indexed=indexed,
        candidates_by_ordinal={cluster["document_ordinal"]: candidate},
    )
    return database, selected, indexed, trials, compiled


def _bundle(tmp_path: Path) -> tuple[Path, list[str], dict, dict, dict]:
    database, selected, _indexed, _trials, _compiled_specs = _indexed_fixture(tmp_path)
    topology, evaluation, schema = _triplet()
    sweep, audit, compiled = runner.build_segment_report_experimental_bundle_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
        database=database,
        selected_ids=selected,
        topology=topology,
        evaluation=evaluation,
        schema=schema,
        sweep_output=tmp_path / "sweep.json",
        spec_refs={
            "evaluation": {"fixture": "evaluation"},
            "schema_binding": {"fixture": "schema-binding"},
            "topology": {"fixture": "topology"},
        },
    )
    return database, selected, sweep, audit, compiled


def test_parser_and_implementation_lineage_are_segment_specific(tmp_path: Path) -> None:
    args = runner._parser().parse_args(
        [
            "--corpus-index",
            str(tmp_path / "index.json"),
            "--artifact-root",
            str(tmp_path / "corpus"),
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
    assert args.run_kind == "EXPERIMENTAL"
    relative_paths = {str(path.relative_to(ROOT)) for path in runner._implementation_paths()}
    assert "scripts/experiments/run_gemini_json_segment_report_accounting_family_v1.py" in (
        relative_paths
    )
    assert "scripts/experiments/run_gemini_json_equity_matrix_accounting_family_v1.py" in (
        relative_paths
    )
    assert "src/bctc_ai/evaluation/gemini_json_segment_report_matrix_v1.py" in relative_paths
    assert "src/bctc_ai/storage/gemini_financial_page_store_v1.py" in relative_paths


def test_runner_reuses_one_authenticated_same_fd_snapshot(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE authority(value TEXT NOT NULL)")
    connection.execute("INSERT INTO authority VALUES ('sealed')")
    connection.commit()
    connection.close()
    payload = source.read_bytes()
    reference = {
        "path": source.name,
        "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    with runner._authenticated_sqlite_snapshot(source, reference=reference) as guard:
        assert guard.path != source
        assert guard.path.read_bytes() == payload
        assert oct(guard.path.stat().st_mode & 0o777) == "0o444"
        guard.validate()


def test_results_store_preflight_rejects_path_symlink_hardlink_and_uncreated_aliases(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.sqlite3"
    source.write_bytes(b"authenticated-source")
    runner._assert_disjoint_results_store(
        source_database=source,
        results_database=tmp_path / "fresh-results.sqlite3",
    )
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="source database path",
    ):
        runner._assert_disjoint_results_store(
            source_database=source,
            results_database=source,
        )

    symlink = tmp_path / "symlink-results.sqlite3"
    symlink.symlink_to(source)
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="source database path",
    ):
        runner._assert_disjoint_results_store(
            source_database=source,
            results_database=symlink,
        )

    hardlink = tmp_path / "hardlink-results.sqlite3"
    os.link(source, hardlink)
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="source database inode",
    ):
        runner._assert_disjoint_results_store(
            source_database=source,
            results_database=hardlink,
        )

    # The intermediate directory intentionally does not exist: lexical existence
    # checks alone would miss that this output resolves back onto the source.
    not_created_alias = tmp_path / "not-created" / ".." / source.name
    assert not os.path.lexists(not_created_alias)
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="source database path",
    ):
        runner._assert_disjoint_results_store(
            source_database=source,
            results_database=not_created_alias,
        )


def test_run_rejects_results_inode_alias_before_frontier_snapshot_or_evaluation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.sqlite3"
    source.write_bytes(b"authenticated-source")
    hardlink = tmp_path / "results.sqlite3"
    os.link(source, hardlink)
    index_path = tmp_path / "index.json"
    index_path.write_text("{}")
    args = runner._parser().parse_args(
        [
            "--corpus-index",
            str(index_path),
            "--artifact-root",
            str(tmp_path),
            "--topology-spec",
            str(tmp_path / "topology.json"),
            "--evaluation-spec",
            str(tmp_path / "evaluation.json"),
            "--schema-binding-spec",
            str(tmp_path / "schema.json"),
            "--results-database",
            str(hardlink),
            "--run-kind",
            "EXPERIMENTAL",
            "--output",
            str(tmp_path / "sweep.json"),
        ]
    )
    monkeypatch.setattr(
        runner,
        "validate_current_corpus_manifest_index_v1",
        lambda _value: {"database_ref": {"fixture": True}},
    )
    monkeypatch.setattr(runner, "_content_ref", lambda _root, _ref: source)
    monkeypatch.setattr(
        runner,
        "_selected_page_axis",
        lambda **_kwargs: pytest.fail("frontier must not be read after inode alias detection"),
    )
    monkeypatch.setattr(
        runner,
        "_authenticated_sqlite_snapshot",
        lambda *_args, **_kwargs: pytest.fail(
            "snapshot must not start after inode alias detection"
        ),
    )
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="source database inode",
    ):
        runner.run(args)


@pytest.mark.parametrize(
    ("alias_kind", "message"),
    [
        ("path", "source database path"),
        ("symlink", "source database path"),
        ("hardlink_inode", "source database inode"),
    ],
)
def test_run_preflights_every_authenticated_frontier_repair_store_before_overlay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    alias_kind: str,
    message: str,
) -> None:
    paths = {
        name: tmp_path / f"{name}.sqlite3"
        for name in ("base", "repair1", "repair2", "stage1", "stage2")
    }
    for ordinal, path in enumerate(paths.values(), start=1):
        path.write_bytes(f"authenticated-{ordinal}".encode())
    refs = {name: runner._file_ref(path, root=tmp_path) for name, path in paths.items()}

    if alias_kind == "path":
        results_database = paths["repair2"]
    else:
        results_database = tmp_path / "results.sqlite3"
        if alias_kind == "symlink":
            results_database.symlink_to(paths["repair2"])
        else:
            os.link(paths["repair2"], results_database)

    corpus_index_id = "gjfccmiv1:index:" + "a" * 64
    index_path = tmp_path / "index.json"
    index_path.write_text("{}")
    frontier_path = tmp_path / "frontier.json"
    frontier_path.write_text("{}")
    args = runner._parser().parse_args(
        [
            "--corpus-index",
            str(index_path),
            "--artifact-root",
            str(tmp_path),
            "--effective-page-frontier",
            str(frontier_path),
            "--topology-spec",
            str(tmp_path / "topology.json"),
            "--evaluation-spec",
            str(tmp_path / "evaluation.json"),
            "--schema-binding-spec",
            str(tmp_path / "schema.json"),
            "--results-database",
            str(results_database),
            "--run-kind",
            "EXPERIMENTAL",
            "--output",
            str(tmp_path / "sweep.json"),
        ]
    )
    index = {
        "corpus_manifest_index_id": corpus_index_id,
        "database_ref": refs["base"],
    }
    effective_frontier = {
        "base_corpus_manifest_index_id": corpus_index_id,
        "family_id": runner.FAMILY_ID,
    }
    stages = [
        {
            "database_ref": refs["stage1"],
            "results_database_ref": refs["repair1"],
        },
        {
            "database_ref": refs["stage2"],
            "results_database_ref": refs["repair2"],
        },
    ]
    monkeypatch.setattr(runner, "validate_current_corpus_manifest_index_v1", lambda _value: index)
    monkeypatch.setattr(runner, "_selected_page_axis", lambda **_kwargs: [VERSION_A])
    monkeypatch.setattr(
        runner,
        "apply_gemini_family_effective_page_frontier_v1",
        lambda _value, **_kwargs: (effective_frontier, [VERSION_A]),
    )
    monkeypatch.setattr(
        runner,
        "effective_page_frontier_stages_v1",
        lambda _frontier: stages,
    )
    monkeypatch.setattr(
        runner,
        "resolved_gemini_family_region_repair_overlay_v1",
        lambda *_args, **_kwargs: pytest.fail(
            "no repair overlay may open before every stage store passes preflight"
        ),
    )
    monkeypatch.setattr(
        runner,
        "_authenticated_sqlite_snapshot",
        lambda *_args, **_kwargs: pytest.fail(
            "snapshot must not start after a repair results-store alias"
        ),
    )
    with pytest.raises(runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error, match=message):
        runner.run(args)


def test_e0161_projection_is_semantic_and_has_exact_denominators() -> None:
    reference, oracle = runner._historical_oracle()
    axes = runner._historical_expected_axes(oracle=oracle, compiled_specs=_compiled())
    assert reference == runner.PINNED_HISTORICAL_ORACLE
    assert {name: len(axis) for name, axis in axes.items()} == {
        "assignments": 208,
        "blank_cells": 2,
        "bounded_absences": 3,
        "documents": 8,
        "equations": 45,
        "open_source_items": 17,
        "source_only_components": 32,
        "structures": 73,
    }
    assert {item["period_role"] for item in axes["assignments"]} == {
        "COMPARATIVE_PERIOD",
        "CURRENT_PERIOD",
    }
    rendered = json.dumps(axes, ensure_ascii=False, sort_keys=True)
    assert "pixel_transcription" not in rendered
    assert "vietocr_text" not in rendered
    assert "crop_ref" not in rendered


def test_e0179_corrigendum_exactly_repairs_bounded_historical_axes() -> None:
    _, oracle = runner._historical_oracle()
    reference, corrigendum = runner._historical_corrigendum()
    raw = runner._historical_expected_axes(oracle=oracle, compiled_specs=_compiled())
    corrected = runner._apply_historical_corrigendum(expected=raw, corrigendum=corrigendum)

    assert reference == runner.PINNED_HISTORICAL_CORRIGENDUM
    assert {
        f"historical_{'source_only_equation_components' if name == 'source_only_components' else name}": len(
            axis
        )
        for name, axis in corrected.items()
    } == runner.PINNED_HISTORICAL_CORRECTED_AXIS_COUNTS

    bid_source = "415d713b18f281f97ea5416da01ddec32d20d9ad49342f3e31fc001743b8a222"
    bid_pbt = [
        item
        for item in corrected["assignments"]
        if item["source_sha256"] == bid_source and item["metric_role"] == "PROFIT_BEFORE_TAX"
    ]
    assert {item["axis_role"]: item["normalized_value"] for item in bid_pbt} == {
        "BANK": 35740232,
        "ELIMINATION": 745105,
        "INSURANCE": 678928,
        "TOTAL": 37787518,
    }

    vpb_source = "f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0"
    assert not any(
        item["source_sha256"] == vpb_source and item["metric_role"] == "PROFIT_BEFORE_TAX"
        for item in corrected["assignments"]
    )
    assert any(
        item["source_sha256"] == vpb_source and item["source_label"] == "Kết quả kinh doanh bộ phận"
        for item in corrected["open_source_items"]
    )

    drifted = copy.deepcopy(corrigendum)
    drifted["axis_operations"][0]["before"]["normalized_value"] += 1
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="operation target drifted",
    ):
        runner._apply_historical_corrigendum(expected=raw, corrigendum=drifted)


def test_semantic_projection_normalizes_provider_numeric_state_without_losing_raw() -> None:
    expected = [
        {
            "axis_role": "BANK",
            "branch": "BUSINESS",
            "metric_role": "REVENUE",
            "normalized_value": 0,
            "parent_report_norm_id": 5807,
            "period_end": "2025-12-31",
            "period_role": "CURRENT_PERIOD",
            "report_norm_id": 5811,
            "source_sha256": "a" * 64,
            "source_state": "VALUE",
        }
    ]
    current = [{**expected[0], "cell_ref": {"row_id": "r1"}, "raw_state": "DASH"}]
    compared = runner._compare_expected_axis(
        expected=expected,
        current=current,
        key_fields=(
            "source_sha256",
            "report_norm_id",
            "parent_report_norm_id",
            "branch",
            "axis_role",
            "metric_role",
            "period_role",
            "period_end",
        ),
        value_fields=("normalized_value", "source_state"),
        trials_by_source={"a" * 64: {"status": runner.READY}},
    )
    assert compared[0]["disposition"] == "EXACT"
    assert compared[0]["current"]["raw_state"] == "DASH"

    current[0]["normalized_value"] = 1
    mismatch = runner._compare_expected_axis(
        expected=expected,
        current=current,
        key_fields=(
            "source_sha256",
            "report_norm_id",
            "parent_report_norm_id",
            "branch",
            "axis_role",
            "metric_role",
            "period_role",
            "period_end",
        ),
        value_fields=("normalized_value", "source_state"),
        trials_by_source={"a" * 64: {"status": runner.READY}},
    )
    assert mismatch[0]["disposition"] == "VALUE_MISMATCH"


def test_segment_audit_inventory_uses_segment_closure_axes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _database, _selected, indexed, trials, compiled = _indexed_fixture(tmp_path)
    historical_names = {
        name: [] for name in runner.AUDIT_AXIS_NAMES if name.startswith("historical_")
    }
    monkeypatch.setattr(
        runner,
        "_historical_comparator_axes",
        lambda **_kwargs: (historical_names, []),
    )
    axes, refs = runner._audit_axes(
        sweep={"indexed_query_evidence": indexed, "trials": trials},
        compiled_specs=compiled,
    )
    assert refs == []
    assert set(axes) == runner.AUDIT_AXIS_NAMES
    assert len(axes["table_receipts"]) == 1
    assert len(axes["mapping_values"]) == 6
    assert len(axes["equations"]) == 2
    assert len(axes["source_only_cells"]) == 2
    assert len(axes["period_assignments"]) == 8
    assert {item["assignment"]["period_assignment_id"] for item in axes["period_assignments"]} == {
        item["period_assignment_id"]
        for item in trials[0]["candidates"][0]["closure_receipt"]["period_receipt"][
            "period_assignment_axis"
        ]
    }
    assert axes["unresolved_documents"] == []


def test_source_only_audit_axis_includes_metric_only_cells(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _database, _selected, indexed, trials, compiled = _indexed_fixture(tmp_path)
    historical_names = {
        name: [] for name in runner.AUDIT_AXIS_NAMES if name.startswith("historical_")
    }
    monkeypatch.setattr(
        runner,
        "_historical_comparator_axes",
        lambda **_kwargs: (historical_names, []),
    )
    trial = copy.deepcopy(trials[0])
    bank_cell = next(
        cell
        for cell in trial["candidates"][0]["closure_receipt"]["table_receipts"][0]["cell_axis"]
        if cell["axis_role"] == "BANK" and cell["metric_role"] == "REVENUE"
    )
    bank_cell["metric_role"] = "SOURCE_ONLY_METRIC:r1:visible-extra"
    axes, _refs = runner._audit_axes(
        sweep={"indexed_query_evidence": indexed, "trials": [trial]},
        compiled_specs=compiled,
    )
    metric_only = [
        item for item in axes["source_only_cells"] if item["source_only_kinds"] == ["METRIC"]
    ]
    assert len(metric_only) == 1
    assert metric_only[0]["cell"]["axis_role"] == "BANK"


def test_bundle_mandates_query_candidate_and_embedded_triplet_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, selected, sweep, audit, compiled = _bundle(tmp_path)
    spec_refs = audit["spec_refs"]
    replay_args = {
        "database": database,
        "sweep": sweep,
        "sweep_output": tmp_path / "sweep.json",
        "selected_page_json_version_ids": selected,
        "compiled_specs": compiled,
        "spec_refs": spec_refs,
    }
    assert (
        runner.validate_segment_report_experimental_audit_replay_v1(audit, **replay_args) == audit
    )

    drifted_compiled = copy.deepcopy(compiled)
    drifted_compiled["family_root_report_norm_id"] += 1
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="embedded compiled triplet",
    ):
        runner.validate_segment_report_experimental_audit_replay_v1(
            audit, **{**replay_args, "compiled_specs": drifted_compiled}
        )

    calls: list[str] = []
    monkeypatch.setattr(
        runner,
        "validate_selected_equity_matrix_family_query_evidence_v1",
        lambda *_args, **_kwargs: calls.append("query"),
    )
    monkeypatch.setattr(
        runner,
        "validate_selected_equity_matrix_family_candidate_replays_v1",
        lambda *_args, **_kwargs: calls.append("candidate"),
    )
    runner._validate_sqlite_replay(
        database=database,
        selected_page_json_version_ids=selected,
        compiled_specs=compiled,
        indexed_query_evidence=sweep["indexed_query_evidence"],
        trials=sweep["trials"],
    )
    assert calls == ["query", "candidate"]


def test_coherently_rehashed_audit_tamper_still_fails_sqlite_replay(tmp_path: Path) -> None:
    database, selected, sweep, audit, compiled = _bundle(tmp_path)
    forged = copy.deepcopy(audit)
    forged["axes"]["mapping_values"][0]["value"]["coefficient"] += 777
    forged["axis_sha256"]["mapping_values"] = runner.canonical_json_sha256_v1(
        forged["axes"]["mapping_values"]
    )
    material = {key: value for key, value in forged.items() if key != "audit_id"}
    forged["audit_id"] = "gjsrmeav1:audit:" + runner.canonical_json_sha256_v1(material)
    runner.validate_segment_report_experimental_audit_content_v1(forged)
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="does not replay exactly",
    ):
        runner.validate_segment_report_experimental_audit_replay_v1(
            forged,
            database=database,
            sweep=sweep,
            sweep_output=tmp_path / "sweep.json",
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            spec_refs=audit["spec_refs"],
        )


def test_current_extras_are_audited_without_failing_expected_comparator() -> None:
    axes = {name: [] for name in runner.AUDIT_AXIS_NAMES}
    axes["historical_assignments"] = [
        {"disposition": "EXACT", "expected": {"fixture": "required"}},
        {
            "current": {"fixture": "newly-authenticated"},
            "disposition": "CURRENT_EXTRA",
            "expected": None,
        },
    ]
    metrics = runner._audit_metrics(axes)
    assert metrics["historical_comparator_failure_count"] == 0
    assert metrics["historical_current_extra_count"] == 1
    assert metrics["historical_expected_axis_counts"]["historical_assignments"] == 1

    axes["historical_assignments"][0]["disposition"] = "VALUE_MISMATCH"
    assert runner._audit_metrics(axes)["historical_comparator_failure_count"] == 1


def test_release_runner_hash_redacts_only_the_pin_literal() -> None:
    first = b"""from typing import Any\nPINNED_RELEASE_PINS: dict[str, Any] = {}\nVALUE = 1\n"""
    second = b"""from typing import Any\nPINNED_RELEASE_PINS: dict[str, Any] = {\n    \"axis\": {\"sha256\": \"a\" * 64},\n}\nVALUE = 1\n"""
    changed_code = second.replace(b"VALUE = 1", b"VALUE = 2")

    first_redacted = runner._release_pin_redacted_runner_bytes_v1(first)
    second_redacted = runner._release_pin_redacted_runner_bytes_v1(second)
    assert first_redacted == second_redacted
    assert runner._release_pin_redacted_runner_bytes_v1(changed_code) != second_redacted


def test_experimental_skips_pointer_gates_but_official_requires_store_readiness_and_pins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected = ["gfpstorev1:json:" + "1" * 64]
    topology, evaluation, schema_binding = _triplet()
    embedded_specs = {
        "evaluation": evaluation,
        "schema_binding": schema_binding,
        "topology": topology,
    }
    spec_refs = {
        name: runner._file_ref(
            ROOT
            / "config/families"
            / f"tm-consolidated-segment-report-{name.replace('_', '-')}-v1.json",
            root=ROOT,
        )
        for name in embedded_specs
    }
    sweep = {
        "corpus_manifest_index_id": "gjfccmiv1:index:" + "a" * 64,
        "indexed_query_evidence": {"query_receipt": {"fixture": True}},
        "metrics": {"unresolved_count": 0},
        "specs": {
            name: {
                "sha256": runner.canonical_json_sha256_v1(value),
                "value": value,
            }
            for name, value in embedded_specs.items()
        },
        "sweep_id": "gjeqmfv1:sweep:" + "d" * 64,
    }
    implementation_refs = [{"path": "fixture.py", "sha256": "c" * 64, "size_bytes": 123}]
    monkeypatch.setattr(
        runner,
        "_release_implementation_refs",
        lambda: copy.deepcopy(implementation_refs),
    )
    axis_counts = copy.deepcopy(runner.PINNED_HISTORICAL_CORRECTED_AXIS_COUNTS)
    audit = {
        "audit_id": "gjsrmeav1:audit:" + "e" * 64,
        "audit_metrics": {
            "historical_comparator_failure_count": 0,
            "historical_current_extra_count": 0,
            "historical_expected_axis_counts": copy.deepcopy(axis_counts),
            "query_unresolved_count": 0,
            "unresolved_document_count": 0,
        },
        "axis_counts": axis_counts,
        "axis_sha256": {"fixture": "b" * 64},
        "historical_oracle_refs": [
            copy.deepcopy(runner.PINNED_HISTORICAL_ORACLE),
            copy.deepcopy(runner.PINNED_HISTORICAL_CORRIGENDUM),
        ],
        "spec_refs": spec_refs,
    }
    missing = tmp_path / "missing.sqlite3"
    runner._assert_persistence_gate(
        run_kind="EXPERIMENTAL",
        results_database=missing,
        sweep=sweep,
        audit=audit,
        selected_ids=selected,
    )
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="existing regular results store",
    ):
        runner._assert_persistence_gate(
            run_kind="OFFICIAL",
            results_database=missing,
            sweep=sweep,
            audit=audit,
            selected_ids=selected,
        )

    database = tmp_path / "results.sqlite3"
    initialize_gemini_accounting_family_store_v1(database)
    monkeypatch.setattr(runner, "PINNED_RELEASE_PINS", {})
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="pins have not been frozen",
    ):
        runner._assert_persistence_gate(
            run_kind="OFFICIAL",
            results_database=database,
            sweep=sweep,
            audit=audit,
            selected_ids=selected,
        )

    actual_pins = runner._release_pin_actual(sweep=sweep, audit=audit, selected_ids=selected)
    monkeypatch.setattr(runner, "PINNED_RELEASE_PINS", actual_pins)
    runner._assert_persistence_gate(
        run_kind="OFFICIAL",
        results_database=database,
        sweep=sweep,
        audit=audit,
        selected_ids=selected,
    )

    audit_with_extra = copy.deepcopy(audit)
    audit_with_extra["axis_counts"]["historical_assignments"] += 1
    audit_with_extra["audit_metrics"]["historical_current_extra_count"] = 1
    extra_pins = runner._release_pin_actual(
        sweep=sweep, audit=audit_with_extra, selected_ids=selected
    )
    monkeypatch.setattr(runner, "PINNED_RELEASE_PINS", extra_pins)
    runner._assert_persistence_gate(
        run_kind="OFFICIAL",
        results_database=database,
        sweep=sweep,
        audit=audit_with_extra,
        selected_ids=selected,
    )
    monkeypatch.setattr(runner, "PINNED_RELEASE_PINS", actual_pins)

    drifted_audit = copy.deepcopy(audit)
    drifted_audit["spec_refs"]["topology"]["sha256"] = "f" * 64
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="frozen release pins drifted",
    ):
        runner._assert_release_pins(
            sweep=sweep,
            audit=drifted_audit,
            selected_ids=selected,
        )

    drifted_audit = copy.deepcopy(audit)
    drifted_audit["historical_oracle_refs"][1]["sha256"] = "0" * 64
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="frozen release pins drifted",
    ):
        runner._assert_release_pins(
            sweep=sweep,
            audit=drifted_audit,
            selected_ids=selected,
        )

    monkeypatch.setattr(
        runner,
        "_release_implementation_refs",
        lambda: [{**implementation_refs[0], "sha256": "1" * 64}],
    )
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="frozen release pins drifted",
    ):
        runner._assert_release_pins(
            sweep=sweep,
            audit=audit,
            selected_ids=selected,
        )
    monkeypatch.setattr(
        runner,
        "_release_implementation_refs",
        lambda: copy.deepcopy(implementation_refs),
    )

    drifted_sweep = copy.deepcopy(sweep)
    drifted_topology = drifted_sweep["specs"]["topology"]
    drifted_topology["value"]["hard_negative_aliases"].append("Phụ lục kiểm thử pin")
    drifted_topology["sha256"] = runner.canonical_json_sha256_v1(drifted_topology["value"])
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportAccountingFamilyV1Error,
        match="frozen release pins drifted",
    ):
        runner._assert_release_pins(
            sweep=drifted_sweep,
            audit=audit,
            selected_ids=selected,
        )
