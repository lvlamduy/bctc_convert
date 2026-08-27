from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest

from bctc_ai.evaluation.gemini_json_dual_component_accounting_family_v1 import (
    READY,
    build_gemini_json_dual_component_region_query_receipt_v1,
    evaluate_gemini_json_dual_component_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    NOT_OBSERVED,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    GeminiFinancialPageStoreV1Error,
    initialize_gemini_financial_page_store_v1,
    query_selected_dual_component_family_regions_v1,
    validate_selected_dual_component_family_candidate_replays_v1,
    validate_selected_dual_component_family_query_evidence_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_text(encoding="utf-8"))


def _specs() -> tuple[dict, dict, dict, dict]:
    topology = _json("tm-purchased-debt-activity-topology-v1.json")
    evaluation = _json("tm-purchased-debt-activity-evaluation-v1.json")
    schema = _json("tm-purchased-debt-activity-schema-binding-v1.json")
    return (
        topology,
        evaluation,
        schema,
        compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema),
    )


def _columns() -> list[dict]:
    return [
        {"header_path_exact": ["30/06/2026", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"},
    ]


def _row(label: str | None, values: list[str], kind: str = "ITEM") -> dict:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(rows: list[dict], title: str | None = None) -> dict:
    return {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": rows,
        "title_exact": title,
        "unit_exact": "Triệu đồng",
    }


def _target_page(*, incidental: bool = False) -> dict:
    tables = []
    if incidental:
        tables.append(
            _table(
                [
                    _row("Giá trị nợ gốc bằng VND", ["200", "180"]),
                    _row("Lãi dự thu", ["2", "1"]),
                    _row("Dự phòng rủi ro", ["(1)", "(1)"]),
                    _row(None, ["201", "180"], "TOTAL"),
                ]
            )
        )
    tables.extend(
        [
            _table(
                [
                    _row("Mua nợ bằng VND", ["100", "80"]),
                    _row("Dự phòng rủi ro mua nợ", ["(20)", "(15)"]),
                    _row(None, ["80", "65"], "TOTAL"),
                ]
            ),
            _table(
                [
                    _row("Nợ gốc đã mua", ["70", "60"]),
                    _row("Lãi từ các khoản nợ đã mua", ["5", "4"]),
                    _row(None, ["75", "64"], "TOTAL"),
                ],
                "Giá trị nợ gốc và lãi của các khoản nợ đã mua",
            ),
        ]
    )
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": tables,
                "title_exact": "11. Hoạt động mua nợ",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _empty_page() -> dict:
    page = _target_page()
    page["sections"][0]["title_exact"] = "Tài sản cố định"
    page["sections"][0]["tables"] = []
    return page


def _optional_only_page() -> dict:
    page = _target_page()
    page["sections"][0]["tables"] = [_table([_row("Lãi của khoản nợ đã mua", ["1", "1"])])]
    return page


def _trial(document: dict, *, candidate: dict | None, status: str, reasons: list[str]) -> dict:
    ready = candidate is not None and status == READY
    return {
        "candidate_count": int(candidate is not None),
        "candidates": [] if candidate is None else [candidate],
        "document_ordinal": document["document_ordinal"],
        "mappings": candidate["mappings"] if ready else [],
        "reasons": reasons,
        "selected_candidate_id": candidate["candidate_id"] if ready else None,
        "source_logical_name": document["source_logical_name"],
        "source_sha256": document["source_sha256"],
        "status": status,
    }


def test_indexed_query_exhaustive_dispositions_and_standard_sweep_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    target_page = _target_page(incidental=True)
    target = _ingest(database, page_json=target_page)
    absent = _ingest(
        database,
        image_sha256="1" * 64,
        physical_page=1,
        prompt_sha256="2" * 64,
        source_logical_name="absent.pdf",
        source_sha256="3" * 64,
        page_json=_empty_page(),
    )
    selected_ids = [target["page_json_version_id"], absent["page_json_version_id"]]
    topology, evaluation, schema, compiled = _specs()
    indexed = query_selected_dual_component_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    assert indexed["query_receipt"]["disposition_counts"] == {
        "ACCEPTED_CLUSTER": 1,
        "NOT_OBSERVED": 1,
        "UNRESOLVED_CLUSTER": 0,
    }
    assert indexed["query_receipt"]["accepted_fragment_count"] == 2
    incidental_hits = [
        hit
        for hit in indexed["indexed_role_hits"]
        if hit["query_disposition"] == "INCIDENTAL_ROLE_IN_FOREIGN_POPULATION"
    ]
    assert len(incidental_hits) == 1
    assert incidental_hits[0]["label_exact"] == "Dự phòng rủi ro"
    replayed = validate_selected_dual_component_family_query_evidence_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
    )
    assert replayed == indexed

    regions = indexed["accepted_clusters"][0]["component_regions"]
    candidate = evaluate_gemini_json_dual_component_family_cluster_v1(
        regions=regions,
        page_json_by_version={target["page_json_version_id"]: target_page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_dual_component_region_query_receipt_v1(regions),
    )
    documents = indexed["selected_document_axis"]
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "4" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        indexed_query_evidence=indexed,
        trials=[
            _trial(documents[0], candidate=candidate, status=READY, reasons=[]),
            _trial(documents[1], candidate=None, status=NOT_OBSERVED, reasons=[]),
        ],
    )
    assert sweep["format_version"] == "GEMINI_JSON_DUAL_COMPONENT_ACCOUNTING_FAMILY_V1"
    assert sweep["metrics"] == {
        "document_count": 2,
        "mapping_count": 4,
        "not_observed_count": 1,
        "ready_count": 1,
        "unresolved_count": 0,
    }
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep
    assert (
        validate_selected_dual_component_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=compiled,
            indexed_query_evidence=indexed,
            trials=sweep["trials"],
        )
        == sweep["trials"]
    )

    forged_candidate = copy.deepcopy(candidate)
    forged_candidate["closure_receipt"]["source_inventory"][0]["row_axis"][0]["label_exact"] = (
        "coherently forged source receipt"
    )
    candidate_material = {
        key: value for key, value in forged_candidate.items() if key != "candidate_id"
    }
    forged_candidate["candidate_id"] = "gjfafcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    forged_sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "4" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        indexed_query_evidence=indexed,
        trials=[
            _trial(documents[0], candidate=forged_candidate, status=READY, reasons=[]),
            _trial(documents[1], candidate=None, status=NOT_OBSERVED, reasons=[]),
        ],
    )
    assert validate_gemini_json_flat_family_sweep_v1(forged_sweep) == forged_sweep
    with pytest.raises(ValueError, match="candidate does not replay exactly"):
        validate_selected_dual_component_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=compiled,
            indexed_query_evidence=indexed,
            trials=forged_sweep["trials"],
        )

    runner_path = (
        ROOT / "scripts/experiments/run_gemini_json_dual_component_accounting_family_v1.py"
    )
    runner_spec = importlib.util.spec_from_file_location(
        "dual_component_runner_candidate_attack_v1", runner_path
    )
    assert runner_spec is not None and runner_spec.loader is not None
    runner = importlib.util.module_from_spec(runner_spec)
    runner_spec.loader.exec_module(runner)
    monkeypatch.setattr(
        runner,
        "validate_dual_component_experimental_audit_content_v1",
        lambda value: value,
    )
    with pytest.raises(ValueError, match="candidate does not replay exactly"):
        runner.validate_dual_component_experimental_audit_replay_v1(
            {},
            compiled_specs=compiled,
            database=database,
            sweep=forged_sweep,
            sweep_output=tmp_path / "forged-sweep.json",
            selected_page_json_version_ids=selected_ids,
            indexed_query_evidence=indexed,
            trials=forged_sweep["trials"],
        )

    root_drift_sweep = copy.deepcopy(sweep)
    schema_reference = root_drift_sweep["specs"]["schema_binding"]
    schema_reference["value"]["family_root_report_norm_id"] = 999999
    schema_reference["sha256"] = canonical_json_sha256_v1(schema_reference["value"])
    sweep_material = {key: value for key, value in root_drift_sweep.items() if key != "sweep_id"}
    root_drift_sweep["sweep_id"] = "gjfafsv1:sweep:" + canonical_json_sha256_v1(sweep_material)
    assert validate_gemini_json_flat_family_sweep_v1(root_drift_sweep) == root_drift_sweep
    with pytest.raises(
        runner.RunGeminiJsonDualComponentAccountingFamilyV1Error,
        match="pinned compiled spec triplet drifted",
    ):
        runner.validate_dual_component_experimental_audit_replay_v1(
            {},
            compiled_specs=compiled,
            database=database,
            sweep=root_drift_sweep,
            sweep_output=tmp_path / "root-drift-sweep.json",
            selected_page_json_version_ids=selected_ids,
            indexed_query_evidence=indexed,
            trials=root_drift_sweep["trials"],
        )

    drifted_schema = copy.deepcopy(schema)
    drifted_schema["family_root_report_norm_id"] = 999999
    drifted_compiled = compile_gemini_json_flat_family_specs_v1(
        topology, evaluation, drifted_schema
    )
    with pytest.raises(ValueError, match="candidate does not replay exactly"):
        validate_selected_dual_component_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=drifted_compiled,
            indexed_query_evidence=indexed,
            trials=sweep["trials"],
        )

    tampered = copy.deepcopy(sweep)
    tampered["indexed_query_evidence"]["accepted_clusters"][0]["component_regions"][0][
        "table_id"
    ] = "t9"
    with pytest.raises(ValueError):
        validate_gemini_json_flat_family_sweep_v1(tampered)


def test_optional_only_page_and_partial_seed_are_unresolved_not_absent(tmp_path: Path) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    target = _ingest(database, page_json=_target_page())
    optional = _ingest(
        database,
        physical_page=8,
        image_sha256="1" * 64,
        prompt_sha256="2" * 64,
        page_json=_optional_only_page(),
    )
    _, _, _, compiled = _specs()
    indexed = query_selected_dual_component_family_regions_v1(
        database,
        selected_page_json_version_ids=[
            target["page_json_version_id"],
            optional["page_json_version_id"],
        ],
        compiled_specs=compiled,
    )
    disposition = indexed["candidate_dispositions"][0]
    assert disposition["disposition"] == "UNRESOLVED_CLUSTER"
    assert "EXACTLY_ONE_CANDIDATE_PAGE_PER_DOCUMENT_REQUIRED" in disposition["reason_codes"]
    assert indexed["accepted_clusters"] == []

    partial_database = tmp_path / "partial.sqlite3"
    initialize_gemini_financial_page_store_v1(partial_database)
    partial_page = _target_page()
    partial_page["sections"][0]["tables"] = partial_page["sections"][0]["tables"][:1]
    partial = _ingest(partial_database, page_json=partial_page)
    indexed = query_selected_dual_component_family_regions_v1(
        partial_database,
        selected_page_json_version_ids=[partial["page_json_version_id"]],
        compiled_specs=compiled,
    )
    assert indexed["candidate_dispositions"][0]["disposition"] == "UNRESOLVED_CLUSTER"
    assert indexed["query_receipt"]["indexed_seed_hit_count"] == 1


def test_mixed_foreign_population_with_nonincidental_declared_role_is_unresolved(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page = _target_page()
    page["sections"][0]["tables"].append(
        _table(
            [
                _row("Dự phòng rủi ro", ["1", "1"]),
                _row("Khoản mục ngoài gia đình", ["2", "2"]),
            ]
        )
    )
    selected = _ingest(database, page_json=page)
    _, _, _, compiled = _specs()
    indexed = query_selected_dual_component_family_regions_v1(
        database,
        selected_page_json_version_ids=[selected["page_json_version_id"]],
        compiled_specs=compiled,
    )
    assert indexed["accepted_clusters"] == []
    assert indexed["candidate_dispositions"][0]["disposition"] == "UNRESOLVED_CLUSTER"
    assert (
        "UNCONSUMED_ROLE_BEARING_FRAGMENT_UNDER_OWNER_FENCE"
        in (indexed["candidate_dispositions"][0]["reason_codes"])
    )
    provision_hit = next(
        hit
        for hit in indexed["indexed_role_hits"]
        if hit["role"] == "PURCHASE_PROVISION" and hit["table_id"] == "t3"
    )
    assert provision_hit["query_disposition"] == "UNCONSUMED_FAMILY_INTERVAL_ROLE_HIT"


def test_database_replay_rejects_query_evidence_tamper(tmp_path: Path) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    selected = _ingest(database, page_json=_target_page())
    _, _, _, compiled = _specs()
    selected_ids = [selected["page_json_version_id"]]
    indexed = query_selected_dual_component_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    tampered = copy.deepcopy(indexed)
    tampered["indexed_role_hits"][0]["label_exact"] = "tampered"
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="does not replay"):
        validate_selected_dual_component_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=compiled,
            indexed_query_evidence=tampered,
        )


def test_runner_pins_specs_and_authenticated_sqlite_main_file(
    tmp_path: Path,
) -> None:
    runner_path = (
        ROOT / "scripts/experiments/run_gemini_json_dual_component_accounting_family_v1.py"
    )
    spec = importlib.util.spec_from_file_location("dual_component_runner_seals_v1", runner_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    topology, evaluation, schema, compiled = _specs()
    runner._validate_pinned_compiled_specs(compiled)
    drifted_schema = copy.deepcopy(schema)
    drifted_schema["family_root_report_norm_id"] = 999999
    drifted = compile_gemini_json_flat_family_specs_v1(topology, evaluation, drifted_schema)
    with pytest.raises(
        runner.RunGeminiJsonDualComponentAccountingFamilyV1Error,
        match="compiled spec triplet drifted",
    ):
        runner._validate_pinned_compiled_specs(drifted)

    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    reference = {
        "path": database.name,
        "sha256": runner._sha256(database),
        "size_bytes": database.stat().st_size,
    }
    sidecar = Path(f"{database}-wal")
    sidecar.write_bytes(b"forged wal")
    with pytest.raises(
        runner.RunGeminiJsonDualComponentAccountingFamilyV1Error,
        match="journal/WAL sidecar",
    ):
        with runner._authenticated_sqlite_snapshot(database, reference=reference):
            pass
    sidecar.unlink()

    with runner._authenticated_sqlite_snapshot(database, reference=reference) as guard:
        assert guard.path.is_file()
        guard.validate()

    moved = tmp_path / "original.sqlite3"
    with pytest.raises(
        runner.RunGeminiJsonDualComponentAccountingFamilyV1Error,
        match="changed during use",
    ):
        with runner._authenticated_sqlite_snapshot(database, reference=reference):
            database.replace(moved)
            database.write_bytes(moved.read_bytes())


def test_experimental_audit_content_validator_rejects_rehashed_axis_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner_path = (
        ROOT / "scripts/experiments/run_gemini_json_dual_component_accounting_family_v1.py"
    )
    spec = importlib.util.spec_from_file_location("dual_component_runner_v1", runner_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    axis_names = set(runner.PINNED_AUDIT_AXIS_COUNTS)
    axes = {name: [{"axis": name}] for name in axis_names}
    counts = {name: 1 for name in axis_names}
    digests = {name: runner._axis_file_sha256(axis) for name, axis in axes.items()}
    preflight = {name: digests[name] for name in runner.PINNED_PREFLIGHT_AXIS_SHA256}
    metrics = {
        "fallback_document_ordinals": [],
        "mapped_source_cell_count": 1,
        "old_oracle_exact_not_observed_count": 0,
        "old_oracle_exact_ready_count": 0,
    }
    monkeypatch.setattr(runner, "PINNED_AUDIT_AXIS_COUNTS", counts)
    monkeypatch.setattr(runner, "PINNED_AUDIT_METRICS", metrics)
    monkeypatch.setattr(runner, "PINNED_PREFLIGHT_AXIS_SHA256", preflight)
    monkeypatch.setattr(
        runner,
        "PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256",
        digests["selected_page_json_version"],
    )
    material = {
        "axes": axes,
        "axis_counts": counts,
        "axis_field_recipes": {name: "synthetic exact recipe" for name in axis_names},
        "axis_sha256": digests,
        "claim_boundary": "SYNTHETIC_AUDIT_VALIDATOR_TEST_ONLY",
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "metrics": metrics,
        "pinned_old_oracle_refs": [
            reference for reference, _oracle in runner._pinned_old_oracles()
        ],
        "pinned_preflight_axis_sha256": preflight,
        "pinned_selected_page_json_frontier_sha256": digests["selected_page_json_version"],
        "query_evidence_id": "gjfidcqev1:evidence:" + "1" * 64,
        "serialization": "COMPACT_SORTED_KEY_UTF8_JSON_LIST_PLUS_LF",
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {
            "path": "sweep.json",
            "sha256": "2" * 64,
            "size_bytes": 1,
            "sweep_id": "gjfafsv1:sweep:" + "3" * 64,
        },
    }
    audit = {
        **material,
        "audit_id": "gjdceav1:audit:"
        + runner.sha256(runner.canonical_json_bytes_v1(material)).hexdigest(),
    }
    assert runner.validate_dual_component_experimental_audit_content_v1(audit) == audit

    tampered = copy.deepcopy(audit)
    tampered["axes"]["mapping"][0]["axis"] = "tampered"
    tampered["axis_sha256"]["mapping"] = runner._axis_file_sha256(tampered["axes"]["mapping"])
    tampered_material = {key: value for key, value in tampered.items() if key != "audit_id"}
    tampered["audit_id"] = (
        "gjdceav1:audit:"
        + runner.sha256(runner.canonical_json_bytes_v1(tampered_material)).hexdigest()
    )
    with pytest.raises(
        runner.RunGeminiJsonDualComponentAccountingFamilyV1Error,
        match="count/hash pin drifted",
    ):
        runner.validate_dual_component_experimental_audit_content_v1(tampered)
