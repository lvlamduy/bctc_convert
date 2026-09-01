from __future__ import annotations

import copy
import json
import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest

from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    UNRESOLVED,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
)
from bctc_ai.evaluation.gemini_json_region_repair_v1 import (
    merge_table_axis_repair_v1,
    table_axis_repair_targets_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage import gemini_accounting_family_store_v1 as family_store
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    ingest_gemini_accounting_family_sweep_v1,
    pending_gemini_family_region_repair_plans_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (
    build_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_family_effective_page_frontier_v1 import (
    build_gemini_family_effective_page_frontier_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    initialize_gemini_financial_page_store_v1,
    query_selected_equity_matrix_family_regions_v1,
    record_page_json_region_repair_v1,
)
from scripts.experiments import run_gemini_json_family_region_repair_worker_v1 as worker
from scripts.experiments import (
    run_gemini_json_segment_report_region_repair_queue_v1 as runner,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_NAME = "ACB/2025/family54-fixture.pdf"
SOURCE_SHA256 = "4" * 64


def _triplet() -> tuple[dict, dict, dict]:
    values = []
    for suffix in ("topology", "evaluation", "schema-binding"):
        path = ROOT / "config/families" / f"tm-consolidated-segment-report-{suffix}-v1.json"
        values.append(json.loads(path.read_text()))
    return values[0], values[1], values[2]


def _table(*, year: int = 2025) -> dict:
    return {
        "columns": [
            {
                "header_path_exact": [f"31/12/{year}", "Ngân hàng\nTriệu VND"],
                "value_kind": "MONEY",
            },
            {
                "header_path_exact": [
                    f"31/12/{year}",
                    "Cho thuê tài chính\nTriệu VND",
                ],
                "value_kind": "MONEY",
            },
            {
                "header_path_exact": [f"31/12/{year}", "Loại trừ\nTriệu VND"],
                "value_kind": "MONEY",
            },
            {
                "header_path_exact": [f"31/12/{year}", "Tổng cộng\nTriệu VND"],
                "value_kind": "MONEY",
            },
        ],
        "continuation": "NONE",
        "rows": [
            {
                "hierarchy_path_exact": ["Doanh thu"],
                "label_exact": "Doanh thu",
                "row_kind": "TOTAL",
                "values_exact": ["100", "20", "(10)", "110"],
            },
            {
                "hierarchy_path_exact": ["Chi phí"],
                "label_exact": "Chi phí",
                "row_kind": "TOTAL",
                "values_exact": ["(50)", "(5)", "5", "(50)"],
            },
        ],
        "title_exact": "Báo cáo bộ phận theo lĩnh vực kinh doanh",
        "unit_exact": "Triệu VND",
    }


def _page(*, tables: list[dict] | None = None) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [_table()] if tables is None else tables,
                "title_exact": ("THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM 2025\nBÁO CÁO BỘ PHẬN"),
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _fixture_sweep_pages(
    tmp_path: Path, *, page_jsons: list[dict]
) -> tuple[Path, list[str], dict, dict, dict]:
    topology, evaluation, schema = _triplet()
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    page_database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(page_database)
    selected_ids = [
        _ingest(
            page_database,
            physical_page=physical_page,
            image_sha256=f"{physical_page:064x}",
            source_logical_name=SOURCE_NAME,
            source_sha256=SOURCE_SHA256,
            page_json=page_json,
        )["page_json_version_id"]
        for physical_page, page_json in enumerate(page_jsons, start=1)
    ]
    indexed = query_selected_equity_matrix_family_regions_v1(
        page_database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    assert len(indexed["accepted_clusters"]) == 1
    cluster = indexed["accepted_clusters"][0]
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=dict(zip(selected_ids, page_jsons, strict=True)),
        compiled_specs=compiled,
        query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
            cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
        ),
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    assert candidate["status"] == UNRESOLVED
    trial = {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": [],
        "reasons": candidate["reasons"],
        "selected_candidate_id": None,
        "source_logical_name": SOURCE_NAME,
        "source_sha256": SOURCE_SHA256,
        "status": UNRESOLVED,
    }
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        indexed_query_evidence=indexed,
        trials=[trial],
    )
    return page_database, selected_ids, sweep, candidate, compiled


def _fixture_sweep(tmp_path: Path, *, page_json: dict) -> tuple[Path, list[str], dict, dict, dict]:
    return _fixture_sweep_pages(tmp_path, page_jsons=[page_json])


def _store_sweep(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    page_database: Path,
    selected_ids: list[str],
    sweep: dict,
) -> tuple[Path, str]:
    monkeypatch.setattr(
        family_store,
        "_selected_corpus_page_frontier_v1",
        lambda **_kwargs: selected_ids,
    )
    results_database = tmp_path / "families.sqlite3"
    stored = ingest_gemini_accounting_family_sweep_v1(
        results_database,
        sweep=sweep,
        corpus_index_ref={"path": "corpus.json", "sha256": "b" * 64, "size_bytes": 123},
        implementation_refs=[{"path": "runner.py", "sha256": "c" * 64, "size_bytes": 456}],
        run_kind="EXPERIMENTAL",
        source_page_database=page_database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=tmp_path.resolve(),
    )
    return results_database, stored["family_run_id"]


def _file_ref(path: Path, *, root: Path | None = None) -> dict:
    payload = path.read_bytes()
    logical = str(path.resolve() if root is None else path.resolve().relative_to(root.resolve()))
    return {"path": logical, "sha256": sha256(payload).hexdigest(), "size_bytes": len(payload)}


def _record_row_repair_lineage(
    page_database: Path,
    *,
    base_version_id: str,
    merged_version_id: str,
    base_page: dict,
    merged_page: dict,
    target_id: str,
) -> dict:
    section_id, table_id, row_id = target_id.split(":")
    row_index = int(row_id[1:]) - 1
    table_index = int(table_id[1:]) - 1
    section_index = int(section_id[1:]) - 1
    before = base_page["sections"][section_index]["tables"][table_index]["rows"][row_index][
        "values_exact"
    ]
    after = merged_page["sections"][section_index]["tables"][table_index]["rows"][row_index][
        "values_exact"
    ]
    material = {
        "base_page_json_sha256": canonical_json_sha256_v1(base_page),
        "base_page_json_version_id": base_version_id,
        "changes": [
            {
                "target_id": target_id,
                "values_after_exact": after,
                "values_before_exact": before,
            }
        ],
        "format_version": "GEMINI_JSON_REGION_REPAIR_V1",
        "merged_page_json_sha256": canonical_json_sha256_v1(merged_page),
        "repair_response_sha256": "d" * 64,
    }
    receipt = {
        **material,
        "repair_id": "gjfrrv1:repair:" + canonical_json_sha256_v1(material),
    }
    return record_page_json_region_repair_v1(
        page_database,
        merged_page_json_version_id=merged_version_id,
        receipt=receipt,
    )


def _corpus_authority(
    tmp_path: Path,
    *,
    page_database: Path,
    selected_ids: list[str],
) -> tuple[Path, dict]:
    pages = [{"page_json_version_id": selected_ids[0], "physical_page": 1}]
    manifest_material = {
        "document": {
            "source_logical_name": SOURCE_NAME,
            "source_sha256": SOURCE_SHA256,
        },
        "page_count": 1,
        "pages": pages,
    }
    manifest = {
        **manifest_material,
        "document_manifest_id": "gfdmv1:manifest:" + canonical_json_sha256_v1(manifest_material),
    }
    manifest_path = tmp_path / "documents" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(canonical_json_bytes_v1(manifest) + b"\n")
    provider_counts = [
        {
            "count": 1,
            "gateway": "OPENROUTER",
            "selected_provider": "Google",
            "selected_service_tier": "flex",
        }
    ]
    index = build_current_corpus_manifest_index_v1(
        corpus_plan_id="gjfpcorpusv1:" + "1" * 64,
        corpus_run_id="gjfpcrunv1:" + "2" * 64,
        corpus_plan_ref={"path": "plan.json", "sha256": "3" * 64, "size_bytes": 100},
        database_ref=_file_ref(page_database, root=tmp_path),
        ledger_ref={"path": "ledger.sqlite3", "sha256": "5" * 64, "size_bytes": 100},
        documents=[
            {
                "document_manifest_id": manifest["document_manifest_id"],
                "document_manifest_ref": _file_ref(manifest_path, root=tmp_path),
                "document_plan_id": "gjfpdocv1:" + "6" * 64,
                "page_count": 1,
                "page_json_frontier_sha256": canonical_json_sha256_v1(pages),
                "page_status_counts": {
                    "FINANCIAL_NOTE_CONTENT": 1,
                    "MIXED_FINANCIAL_CONTENT": 0,
                    "NO_RELEVANT_FINANCIAL_CONTENT": 0,
                    "PRIMARY_FINANCIAL_STATEMENT": 0,
                },
                "provider_counts": provider_counts,
                "relative_path": SOURCE_NAME,
                "selection_id": "gjfcdmsv1:selection:" + "7" * 64,
                "selection_ref": {
                    "path": "selection.json",
                    "sha256": "8" * 64,
                    "size_bytes": 100,
                },
                "source_ordinal": 1,
                "source_sha256": SOURCE_SHA256,
                "source_size_bytes": 123,
            }
        ],
        store_usage_summary={
            "attempts": [
                {
                    "count": 1,
                    "credential_slot": "OPENROUTER_SLOT_1",
                    "outcome": "COMPLETED",
                    "provider": "OPENROUTER",
                }
            ],
            "cached_input_tokens": 0,
            "input_tokens": 100,
            "output_tokens": 50,
            "run_count": 1,
            "thought_tokens": 2,
            "total_cost_usd": "0.010000000000",
        },
    )
    index_path = tmp_path / "corpus-index.json"
    index_path.write_bytes(canonical_json_bytes_v1(index) + b"\n")
    return index_path, index


def test_parser_accepts_only_stored_run_and_authenticated_corpus_inputs(
    tmp_path: Path,
) -> None:
    args = runner._parser().parse_args(
        [
            "--corpus-index",
            str(tmp_path / "corpus.json"),
            "--artifact-root",
            str(tmp_path / "corpus"),
            "--effective-page-artifact-root",
            str(tmp_path / "effective"),
            "--results-database",
            str(tmp_path / "families.sqlite3"),
            "--family-run-id",
            "gjfafstorev1:run:" + "1" * 64,
        ]
    )
    assert args.family_run_id == "gjfafstorev1:run:" + "1" * 64
    assert args.effective_page_artifact_root == tmp_path / "effective"
    assert not hasattr(args, "run_kind")
    assert not hasattr(args, "openrouter_key_file")


def test_effective_frontier_sweep_preserves_exact_row_repair_planning(
    tmp_path: Path,
) -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "1.2.3"
    _page_database, selected_ids, base_sweep, candidate, compiled = _fixture_sweep(
        tmp_path, page_json=page
    )
    assert candidate["reasons"] == ["SEGMENT_MONEY_CELL_INVALID"]
    frontier = build_gemini_family_effective_page_frontier_v1(
        base_corpus_manifest_index_id=base_sweep["corpus_manifest_index_id"],
        base_page_json_version_ids=selected_ids,
        database_ref={"path": "page-store.sqlite3", "sha256": "a" * 64, "size_bytes": 1},
        family_id=runner.FAMILY_ID,
        job_status_counts={"ABSTAINED": 0, "RESOLVED": 1},
        repair_source_family_run_id="gjfafstorev1:run:" + "b" * 64,
        replacements=[
            {
                "base_page_json_version_id": selected_ids[0],
                "candidate_id": candidate["candidate_id"],
                "document_ordinal": 1,
                "physical_page": 1,
                "repair_id": "gjfrrv1:repair:" + "c" * 64,
                "repair_job_id": "gjfrrqv1:job:" + "d" * 64,
                "repair_receipt_sha256": "e" * 64,
                "selected_page_json_version_id": selected_ids[0],
            }
        ],
        results_database_ref={
            "path": "family-results.sqlite3",
            "sha256": "f" * 64,
            "size_bytes": 1,
        },
    )
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=base_sweep["corpus_manifest_index_id"],
        topology_spec=base_sweep["specs"]["topology"]["value"],
        evaluation_spec=base_sweep["specs"]["evaluation"]["value"],
        schema_binding_spec=base_sweep["specs"]["schema_binding"]["value"],
        indexed_query_evidence=base_sweep["indexed_query_evidence"],
        trials=base_sweep["trials"],
        effective_page_frontier=frontier,
    )

    plans = runner.build_segment_report_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={selected_ids[0]: page},
        compiled_specs=compiled,
    )

    assert len(plans) == 1
    assert plans[0]["repair_scope"] == "ROW_VALUES"
    assert plans[0]["base_page_json_version_id"] == selected_ids[0]


def test_runner_authenticates_fixture_corpus_replays_sweep_and_enqueues(
    tmp_path: Path,
) -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "1.2.3"
    page_database, selected_ids, provisional_sweep, _candidate, compiled = _fixture_sweep(
        tmp_path, page_json=page
    )
    index_path, index = _corpus_authority(
        tmp_path,
        page_database=page_database,
        selected_ids=selected_ids,
    )
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=provisional_sweep["specs"]["topology"]["value"],
        evaluation_spec=provisional_sweep["specs"]["evaluation"]["value"],
        schema_binding_spec=provisional_sweep["specs"]["schema_binding"]["value"],
        indexed_query_evidence=provisional_sweep["indexed_query_evidence"],
        trials=provisional_sweep["trials"],
    )
    results_database = tmp_path / "authenticated-families.sqlite3"
    stored = ingest_gemini_accounting_family_sweep_v1(
        results_database,
        sweep=sweep,
        corpus_index_ref=_file_ref(index_path),
        implementation_refs=[{"path": "runner.py", "sha256": "9" * 64, "size_bytes": 456}],
        run_kind="EXPERIMENTAL",
        source_page_database=page_database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=tmp_path.resolve(),
    )
    result = runner.run(
        runner._parser().parse_args(
            [
                "--corpus-index",
                str(index_path),
                "--artifact-root",
                str(tmp_path),
                "--results-database",
                str(results_database),
                "--family-run-id",
                stored["family_run_id"],
            ]
        )
    )
    assert result == {
        "disposition": "SUCCEEDED",
        "family_id": runner.FAMILY_ID,
        "family_run_id": stored["family_run_id"],
        "format_version": runner.FORMAT_VERSION,
        "pending_region_repair_job_count": 1,
        "prior_terminal_repair_suppressed_count": 0,
        "repair_job_ids": result["repair_job_ids"],
        "repair_plan_axis_sha256": result["repair_plan_axis_sha256"],
        "repair_scope_counts": {"ROW_VALUES": 1, "TABLE_PERIOD_AXIS": 0},
        "sweep_id": sweep["sweep_id"],
    }
    assert len(result["repair_job_ids"]) == 1
    assert pending_gemini_family_region_repair_plans_v1(
        results_database, family_run_id=stored["family_run_id"]
    )[0]["plan"]["target_ids"] == ["s1:t1:r1"]
    assert compiled["segment_report_mode"] is True


def test_prior_terminal_effective_target_is_not_enqueued_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "1.2.3"
    page_database, selected_ids, sweep, _candidate, compiled = _fixture_sweep(
        tmp_path, page_json=page
    )
    results_database, family_run_id = _store_sweep(
        tmp_path,
        monkeypatch,
        page_database=page_database,
        selected_ids=selected_ids,
        sweep=sweep,
    )
    plans = runner.build_segment_report_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={selected_ids[0]: page},
        compiled_specs=compiled,
    )
    assert len(plans) == 1

    filtered, identifiers = runner.enqueue_segment_report_region_repair_plans_v1(
        results_database,
        family_run_id=family_run_id,
        sweep=sweep,
        page_json_by_version={selected_ids[0]: page},
        compiled_specs=compiled,
        prior_terminal_repair_target_keys={runner._repair_target_key(plans[0])},
    )

    assert filtered == []
    assert identifiers == []
    assert (
        pending_gemini_family_region_repair_plans_v1(results_database, family_run_id=family_run_id)
        == []
    )


def test_invalid_money_cell_enqueues_one_exact_row_job_deterministically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = _page()
    row = page["sections"][0]["tables"][0]["rows"][0]
    row["values_exact"][0] = "1.2.3"
    row["values_exact"][-1] = "133"
    page["sections"][0]["tables"][0]["rows"].append(
        {
            "hierarchy_path_exact": ["Chỉ tiêu ngoài cấu hình"],
            "label_exact": "Chỉ tiêu ngoài cấu hình",
            "row_kind": "ITEM",
            "values_exact": ["2.3.4", "10)", None, None],
        }
    )
    page_database, selected_ids, sweep, candidate, compiled = _fixture_sweep(
        tmp_path, page_json=page
    )
    assert candidate["reasons"] == ["SEGMENT_MONEY_CELL_INVALID"]
    results_database, family_run_id = _store_sweep(
        tmp_path,
        monkeypatch,
        page_database=page_database,
        selected_ids=selected_ids,
        sweep=sweep,
    )
    binding = runner._stored_run_binding(results_database, family_run_id=family_run_id)
    assert binding["family_id"] == runner.FAMILY_ID
    assert binding["unresolved_count"] == 1
    pages = {selected_ids[0]: page}

    plans, identifiers = runner.enqueue_segment_report_region_repair_plans_v1(
        results_database,
        family_run_id=family_run_id,
        sweep=sweep,
        page_json_by_version=pages,
        compiled_specs=compiled,
    )
    assert len(plans) == 1
    assert identifiers == [plans[0]["repair_job_id"]]
    assert plans[0]["repair_scope"] == "ROW_VALUES"
    assert plans[0]["target_ids"] == ["s1:t1:r1"]
    assert plans[0]["target_table_refs"] == []
    assert plans[0]["target_cell_refs"] == [
        {
            "column_id": "c1",
            "page_json_version_id": selected_ids[0],
            "physical_page": 1,
            "row_id": "r1",
            "section_id": "s1",
            "table_id": "t1",
        }
    ]
    assert plans[0]["trigger_kinds"] == ["INVALID_MONEY_CELL"]
    assert plans[0]["candidate_semantic_replay_sha256"] == (
        runner.canonical_json_sha256_v1(candidate)
    )

    forged_scope = copy.deepcopy(plans[0])
    forged_scope["target_ids"] = ["s1:t1:r2"]
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportRegionRepairQueueV1Error,
        match="target frontier drifted",
    ):
        runner.stored_segment_repair_authority_v1(
            results_database=results_database,
            family_run_id=family_run_id,
            plan=forged_scope,
            compiled_specs=compiled,
            page_database=page_database,
        )

    forged_component_hash = copy.deepcopy(plans[0])
    forged_component_hash["candidate_component_region_axis_sha256"] = "0" * 64
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportRegionRepairQueueV1Error,
        match="candidate identity drifted",
    ):
        runner.stored_segment_repair_authority_v1(
            results_database=results_database,
            family_run_id=family_run_id,
            plan=forged_component_hash,
            compiled_specs=compiled,
            page_database=page_database,
        )

    forged_dispatch = copy.deepcopy(plans[0])
    forged_dispatch["query_disposition_sha256"] = "8" * 64
    forged_material = {
        key: value for key, value in forged_dispatch.items() if key != "repair_job_id"
    }
    forged_dispatch["repair_job_id"] = "gjfrrqv1:job:" + canonical_json_sha256_v1(forged_material)
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportRegionRepairQueueV1Error,
        match="exact stored scope",
    ):
        runner.stored_segment_repair_authority_v1(
            results_database=results_database,
            family_run_id=family_run_id,
            plan=forged_dispatch,
            compiled_specs=compiled,
            page_database=page_database,
        )

    repeated_plans, repeated_ids = runner.enqueue_segment_report_region_repair_plans_v1(
        results_database,
        family_run_id=family_run_id,
        sweep=sweep,
        page_json_by_version=pages,
        compiled_specs=compiled,
    )
    assert repeated_plans == plans
    assert repeated_ids == identifiers
    pending = pending_gemini_family_region_repair_plans_v1(
        results_database, family_run_id=family_run_id
    )
    assert [item["repair_job_id"] for item in pending] == identifiers

    foreign_sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "f" * 64,
        topology_spec=sweep["specs"]["topology"]["value"],
        evaluation_spec=sweep["specs"]["evaluation"]["value"],
        schema_binding_spec=sweep["specs"]["schema_binding"]["value"],
        indexed_query_evidence=sweep["indexed_query_evidence"],
        trials=sweep["trials"],
    )
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportRegionRepairQueueV1Error,
        match="differs from its stored family run",
    ):
        runner.enqueue_segment_report_region_repair_plans_v1(
            results_database,
            family_run_id=family_run_id,
            sweep=foreign_sweep,
            page_json_by_version=pages,
            compiled_specs=compiled,
        )


def test_enqueue_rechecks_experimental_authority_in_write_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "1.2.3"
    page_database, selected_ids, sweep, _candidate, compiled = _fixture_sweep(
        tmp_path, page_json=page
    )
    results_database, family_run_id = _store_sweep(
        tmp_path,
        monkeypatch,
        page_database=page_database,
        selected_ids=selected_ids,
        sweep=sweep,
    )
    with sqlite3.connect(results_database) as connection:
        connection.execute(
            "UPDATE family_run_execution SET run_kind='OFFICIAL' WHERE family_run_id=?",
            (family_run_id,),
        )
        connection.commit()

    with pytest.raises(
        family_store.GeminiAccountingFamilyStoreV1Error,
        match="lacks required execution authorization",
    ):
        runner.enqueue_segment_report_region_repair_plans_v1(
            results_database,
            family_run_id=family_run_id,
            sweep=sweep,
            page_json_by_version={selected_ids[0]: page},
            compiled_specs=compiled,
        )
    with sqlite3.connect(results_database) as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM sqlite_master "
                "WHERE type='table' AND name='family_region_repair_job'"
            ).fetchone()[0]
            == 0
        )


def test_enqueued_money_job_replays_full_segment_cluster_in_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"] = [
        "1.2.3",
        "20",
        "(10)",
        "133",
    ]
    page_database, selected_ids, sweep, candidate, compiled = _fixture_sweep(
        tmp_path, page_json=page
    )
    assert candidate["reasons"] == ["SEGMENT_MONEY_CELL_INVALID"]
    results_database, family_run_id = _store_sweep(
        tmp_path,
        monkeypatch,
        page_database=page_database,
        selected_ids=selected_ids,
        sweep=sweep,
    )
    plans, _identifiers = runner.enqueue_segment_report_region_repair_plans_v1(
        results_database,
        family_run_id=family_run_id,
        sweep=sweep,
        page_json_by_version={selected_ids[0]: page},
        compiled_specs=compiled,
    )
    assert not worker._targeted_repair_is_accepted(plans[0], candidate)

    repaired_page = copy.deepcopy(page)
    repaired_page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "123"
    repaired = _ingest(
        page_database,
        physical_page=1,
        image_sha256=f"{1:064x}",
        source_logical_name=SOURCE_NAME,
        source_sha256=SOURCE_SHA256,
        prompt_sha256="a" * 64,
        page_json=repaired_page,
    )
    repaired_version_id = repaired["page_json_version_id"]
    lineage = _record_row_repair_lineage(
        page_database,
        base_version_id=selected_ids[0],
        merged_version_id=repaired_version_id,
        base_page=page,
        merged_page=repaired_page,
        target_id="s1:t1:r1",
    )
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportRegionRepairQueueV1Error,
        match="direct lineage",
    ):
        runner.authenticate_segment_repair_observation_v1(
            plan=plans[0],
            observation={
                "database_identities": {"page_json_version_id": repaired_version_id},
                "lineage": {**lineage, "base_page_json_version_id": "gfpstorev1:json:" + "0" * 64},
            },
            page_database=page_database,
        )
    broad_page = copy.deepcopy(repaired_page)
    broad_page["sections"][0]["tables"][0]["rows"][0]["values_exact"][1] = "21"
    broad_page["sections"][0]["tables"][0]["rows"][0]["values_exact"][3] = "134"
    broad = _ingest(
        page_database,
        physical_page=1,
        image_sha256=f"{1:064x}",
        source_logical_name=SOURCE_NAME,
        source_sha256=SOURCE_SHA256,
        prompt_sha256="b" * 64,
        page_json=broad_page,
    )
    broad_lineage = _record_row_repair_lineage(
        page_database,
        base_version_id=selected_ids[0],
        merged_version_id=broad["page_json_version_id"],
        base_page=page,
        merged_page=broad_page,
        target_id="s1:t1:r1",
    )
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportRegionRepairQueueV1Error,
        match="outside planned cells",
    ):
        runner.authenticate_segment_repair_observation_v1(
            plan=plans[0],
            observation={
                "database_identities": {"page_json_version_id": broad["page_json_version_id"]},
                "lineage": broad_lineage,
            },
            page_database=page_database,
        )
    monkeypatch.setattr(
        worker,
        "run_region_repair_v1",
        lambda _args: {
            "database_identities": {"page_json_version_id": repaired_version_id},
            "lineage": lineage,
            "usage": {},
        },
    )
    topology, evaluation, schema = [
        ROOT / "config/families" / f"tm-consolidated-segment-report-{suffix}-v1.json"
        for suffix in ("topology", "evaluation", "schema-binding")
    ]
    result = worker.run(
        worker._parser().parse_args(
            [
                "--results-database",
                str(results_database),
                "--family-run-id",
                family_run_id,
                "--page-database",
                str(page_database),
                "--pdf-root",
                str(tmp_path),
                "--topology-spec",
                str(topology),
                "--evaluation-spec",
                str(evaluation),
                "--schema-binding-spec",
                str(schema),
                "--artifact-root",
                str(tmp_path / "repair-artifacts"),
                "--max-jobs",
                "1",
            ]
        )
    )
    assert result["attempt_count"] == 1
    assert result["job_count"] == 1
    assert result["outcomes"][0]["outcome"] == "RESOLVED"
    assert result["outcomes"][0]["next_status"] == "RESOLVED"
    assert (
        pending_gemini_family_region_repair_plans_v1(results_database, family_run_id=family_run_id)
        == []
    )


def test_nonprimary_period_job_replays_full_segment_cluster_in_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dated = _table()
    undated = copy.deepcopy(_table())
    for column in undated["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    page = _page(tables=[dated, undated])
    page_database, selected_ids, sweep, candidate, compiled = _fixture_sweep(
        tmp_path, page_json=page
    )
    assert candidate["reasons"] == ["SEGMENT_PERIOD_NOT_RESOLVED"]
    results_database, family_run_id = _store_sweep(
        tmp_path,
        monkeypatch,
        page_database=page_database,
        selected_ids=selected_ids,
        sweep=sweep,
    )
    plans, _identifiers = runner.enqueue_segment_report_region_repair_plans_v1(
        results_database,
        family_run_id=family_run_id,
        sweep=sweep,
        page_json_by_version={selected_ids[0]: page},
        compiled_specs=compiled,
    )
    assert plans[0]["target_table_refs"] == [{"section_id": "s1", "table_id": "t2"}]

    targets = table_axis_repair_targets_v1(
        page,
        table_refs=plans[0]["target_table_refs"],
    )
    repaired_headers = [
        ["31/12/2024", *column["header_path_exact"]]
        for column in page["sections"][0]["tables"][1]["columns"]
    ]
    repaired_page, receipt = merge_table_axis_repair_v1(
        page,
        base_page_json_version_id=selected_ids[0],
        targets=targets,
        repair={
            "all_targets_transcribed": True,
            "tables": [
                {
                    "columns_header_path_exact": repaired_headers,
                    "table_title_exact": page["sections"][0]["tables"][1]["title_exact"],
                    "target_id": "s1:t2",
                }
            ],
            "uncertainty_exact": [],
        },
    )
    repaired = _ingest(
        page_database,
        physical_page=1,
        image_sha256=f"{1:064x}",
        source_logical_name=SOURCE_NAME,
        source_sha256=SOURCE_SHA256,
        prompt_sha256="a" * 64,
        page_json=repaired_page,
    )
    repaired_version_id = repaired["page_json_version_id"]
    lineage = record_page_json_region_repair_v1(
        page_database,
        merged_page_json_version_id=repaired_version_id,
        receipt=receipt,
    )
    repeated_observation = _ingest(
        page_database,
        physical_page=1,
        image_sha256=f"{1:064x}",
        source_logical_name=SOURCE_NAME,
        source_sha256=SOURCE_SHA256,
        prompt_sha256="b" * 64,
        page_json=repaired_page,
    )
    repeated_lineage = record_page_json_region_repair_v1(
        page_database,
        merged_page_json_version_id=repeated_observation["page_json_version_id"],
        receipt=receipt,
    )
    assert repeated_observation["page_json_version_id"] != repaired_version_id
    assert (
        runner.authenticate_segment_repair_observation_v1(
            plan=plans[0],
            observation={
                "database_identities": {
                    "page_json_version_id": repeated_observation["page_json_version_id"]
                },
                "lineage": repeated_lineage,
            },
            page_database=page_database,
        )
        == repaired_version_id
    )
    monkeypatch.setattr(
        worker,
        "run_region_repair_v1",
        lambda _args: {
            "database_identities": {"page_json_version_id": repaired_version_id},
            "lineage": lineage,
            "usage": {},
        },
    )
    topology, evaluation, schema = [
        ROOT / "config/families" / f"tm-consolidated-segment-report-{suffix}-v1.json"
        for suffix in ("topology", "evaluation", "schema-binding")
    ]
    result = worker.run(
        worker._parser().parse_args(
            [
                "--results-database",
                str(results_database),
                "--family-run-id",
                family_run_id,
                "--page-database",
                str(page_database),
                "--pdf-root",
                str(tmp_path),
                "--topology-spec",
                str(topology),
                "--evaluation-spec",
                str(evaluation),
                "--schema-binding-spec",
                str(schema),
                "--artifact-root",
                str(tmp_path / "period-repair-artifacts"),
                "--max-jobs",
                "1",
            ]
        )
    )
    assert result["outcomes"][-1]["outcome"] == "RESOLVED"
    assert (
        pending_gemini_family_region_repair_plans_v1(results_database, family_run_id=family_run_id)
        == []
    )


def test_missing_period_axis_enqueues_only_the_undated_nonprimary_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dated = _table()
    undated = copy.deepcopy(dated)
    for column in undated["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    page = _page(tables=[dated, undated])
    page_database, selected_ids, sweep, candidate, compiled = _fixture_sweep(
        tmp_path, page_json=page
    )
    assert "SEGMENT_PERIOD_NOT_RESOLVED" in candidate["reasons"]
    results_database, family_run_id = _store_sweep(
        tmp_path,
        monkeypatch,
        page_database=page_database,
        selected_ids=selected_ids,
        sweep=sweep,
    )
    plans, identifiers = runner.enqueue_segment_report_region_repair_plans_v1(
        results_database,
        family_run_id=family_run_id,
        sweep=sweep,
        page_json_by_version={selected_ids[0]: page},
        compiled_specs=compiled,
    )
    assert len(plans) == 1
    assert identifiers == [plans[0]["repair_job_id"]]
    assert plans[0]["repair_scope"] == "TABLE_PERIOD_AXIS"
    assert plans[0]["target_table_refs"] == [{"section_id": "s1", "table_id": "t2"}]
    assert plans[0]["target_ids"] == ["s1:t2:r1", "s1:t2:r2"]
    assert plans[0]["target_cell_refs"] == []
    assert plans[0]["trigger_kinds"] == ["TABLE_PERIOD_AXIS_INCOMPLETE"]


def test_ambiguous_money_cell_targets_its_exact_row_and_cell(tmp_path: Path) -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][2] = "10)"
    _database, selected_ids, sweep, candidate, compiled = _fixture_sweep(tmp_path, page_json=page)
    assert candidate["reasons"] == ["SEGMENT_MONEY_CELL_AMBIGUOUS"]

    plans = runner.build_segment_report_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={selected_ids[0]: page},
        compiled_specs=compiled,
    )
    assert len(plans) == 1
    assert plans[0]["repair_scope"] == "ROW_VALUES"
    assert plans[0]["target_ids"] == ["s1:t1:r1"]
    assert plans[0]["target_cell_refs"] == [
        {
            "column_id": "c3",
            "page_json_version_id": selected_ids[0],
            "physical_page": 1,
            "row_id": "r1",
            "section_id": "s1",
            "table_id": "t1",
        }
    ]


def test_period_axis_precedes_money_row_when_both_fail_on_one_page(tmp_path: Path) -> None:
    dated = _table()
    dated["rows"][0]["values_exact"][0] = "10)"
    undated = copy.deepcopy(_table())
    for column in undated["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    page = _page(tables=[dated, undated])
    _database, selected_ids, sweep, candidate, compiled = _fixture_sweep(tmp_path, page_json=page)
    assert {"SEGMENT_MONEY_CELL_AMBIGUOUS", "SEGMENT_PERIOD_NOT_RESOLVED"} <= set(
        candidate["reasons"]
    )

    plans = runner.build_segment_report_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={selected_ids[0]: page},
        compiled_specs=compiled,
    )
    assert len(plans) == 1
    assert plans[0]["repair_scope"] == "TABLE_PERIOD_AXIS"
    assert plans[0]["target_table_refs"] == [{"section_id": "s1", "table_id": "t2"}]
    assert plans[0]["target_cell_refs"] == []


def test_period_axis_precedes_money_row_across_the_whole_candidate(tmp_path: Path) -> None:
    money_page = _page()
    money_page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "10)"
    undated = _table()
    for column in undated["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    period_page = _page(tables=[undated])
    _database, selected_ids, sweep, candidate, compiled = _fixture_sweep_pages(
        tmp_path,
        page_jsons=[money_page, period_page],
    )
    assert {"SEGMENT_MONEY_CELL_AMBIGUOUS", "SEGMENT_PERIOD_NOT_RESOLVED"} <= set(
        candidate["reasons"]
    )

    plans = runner.build_segment_report_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version=dict(zip(selected_ids, [money_page, period_page], strict=True)),
        compiled_specs=compiled,
    )
    assert len(plans) == 1
    assert plans[0]["base_page_json_version_id"] == selected_ids[1]
    assert plans[0]["repair_scope"] == "TABLE_PERIOD_AXIS"
    assert plans[0]["acceptance_policy"]["require_candidate_status"] == UNRESOLVED


def test_same_scope_frontier_across_two_pages_fails_closed(tmp_path: Path) -> None:
    first = _page()
    second = _page()
    first["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "1.2.3"
    second["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = "4.5.6"
    _database, selected_ids, sweep, candidate, compiled = _fixture_sweep_pages(
        tmp_path,
        page_jsons=[first, second],
    )
    assert "SEGMENT_MONEY_CELL_INVALID" in candidate["reasons"]

    with pytest.raises(
        runner.RunGeminiJsonSegmentReportRegionRepairQueueV1Error,
        match="spans multiple base pages",
    ):
        runner.build_segment_report_region_repair_plans_v1(
            sweep=sweep,
            page_json_by_version=dict(zip(selected_ids, [first, second], strict=True)),
            compiled_specs=compiled,
        )


def test_two_page_period_repairs_compose_before_full_candidate_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    flow = _page()
    stock = _page()
    for page in (flow, stock):
        for column in page["sections"][0]["tables"][0]["columns"]:
            column["header_path_exact"] = column["header_path_exact"][1:]
    for row, label in zip(
        stock["sections"][0]["tables"][0]["rows"],
        ("Tài sản", "Nợ phải trả"),
        strict=True,
    ):
        row["label_exact"] = label
        row["hierarchy_path_exact"] = [label]
    page_database, selected_ids, sweep, candidate, compiled = _fixture_sweep_pages(
        tmp_path,
        page_jsons=[flow, stock],
    )
    assert candidate["reasons"] == ["SEGMENT_PERIOD_END_NOT_RESOLVED"]
    results_database, family_run_id = _store_sweep(
        tmp_path,
        monkeypatch,
        page_database=page_database,
        selected_ids=selected_ids,
        sweep=sweep,
    )
    plans, _identifiers = runner.enqueue_segment_report_region_repair_plans_v1(
        results_database,
        family_run_id=family_run_id,
        sweep=sweep,
        page_json_by_version=dict(zip(selected_ids, [flow, stock], strict=True)),
        compiled_specs=compiled,
    )
    assert [plan["physical_page"] for plan in plans] == [1, 2]
    assert all(plan["repair_frontier_base_page_json_version_ids"] == selected_ids for plan in plans)
    assert all(
        plan["acceptance_policy"]["require_local_period_scope_resolution"] is True for plan in plans
    )

    observations = {}
    for plan, page, year in zip(plans, (flow, stock), (2025, 2024), strict=True):
        targets = table_axis_repair_targets_v1(
            page,
            table_refs=plan["target_table_refs"],
        )
        repaired_page, receipt = merge_table_axis_repair_v1(
            page,
            base_page_json_version_id=plan["base_page_json_version_id"],
            targets=targets,
            repair={
                "all_targets_transcribed": True,
                "tables": [
                    {
                        "columns_header_path_exact": [
                            [f"31/12/{year}", *column["header_path_exact"]]
                            for column in page["sections"][0]["tables"][0]["columns"]
                        ],
                        "table_title_exact": page["sections"][0]["tables"][0]["title_exact"],
                        "target_id": "s1:t1",
                    }
                ],
                "uncertainty_exact": [],
            },
        )
        repaired = _ingest(
            page_database,
            physical_page=plan["physical_page"],
            image_sha256=f"{plan['physical_page']:064x}",
            source_logical_name=SOURCE_NAME,
            source_sha256=SOURCE_SHA256,
            prompt_sha256=f"{year:064x}",
            page_json=repaired_page,
        )
        lineage = record_page_json_region_repair_v1(
            page_database,
            merged_page_json_version_id=repaired["page_json_version_id"],
            receipt=receipt,
        )
        observations[plan["physical_page"]] = {
            "database_identities": {"page_json_version_id": repaired["page_json_version_id"]},
            "lineage": lineage,
            "usage": {},
        }
    monkeypatch.setattr(
        worker,
        "run_region_repair_v1",
        lambda args: observations[args.physical_page],
    )
    topology, evaluation, schema = [
        ROOT / "config/families" / f"tm-consolidated-segment-report-{suffix}-v1.json"
        for suffix in ("topology", "evaluation", "schema-binding")
    ]
    result = worker.run(
        worker._parser().parse_args(
            [
                "--results-database",
                str(results_database),
                "--family-run-id",
                family_run_id,
                "--page-database",
                str(page_database),
                "--pdf-root",
                str(tmp_path),
                "--topology-spec",
                str(topology),
                "--evaluation-spec",
                str(evaluation),
                "--schema-binding-spec",
                str(schema),
                "--artifact-root",
                str(tmp_path / "composed-period-repair-artifacts"),
                "--max-jobs",
                "2",
            ]
        )
    )
    assert [outcome["outcome"] for outcome in result["outcomes"]] == [
        "RESOLVED",
        "RESOLVED",
    ]
    replacements = family_store.resolved_gemini_family_region_repair_candidate_replacements_v1(
        results_database,
        family_run_id=family_run_id,
        candidate_id=candidate["candidate_id"],
    )
    assert [item["physical_page"] for item in replacements] == [1, 2]


def test_valid_multi_period_receipt_is_not_targeted_with_bad_sibling(tmp_path: Path) -> None:
    multi_period = _table()
    comparative = copy.deepcopy(multi_period["columns"])
    for column in comparative:
        column["header_path_exact"] = [
            value.replace("2025", "2024") for value in column["header_path_exact"]
        ]
    multi_period["columns"] += comparative
    for row in multi_period["rows"]:
        row["values_exact"] += copy.deepcopy(row["values_exact"])
    multi_period["title_exact"] += " Năm 2025 và 2024"
    undated = _table()
    for column in undated["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    page = _page(tables=[multi_period, undated])
    _database, selected_ids, sweep, candidate, compiled = _fixture_sweep(tmp_path, page_json=page)
    receipts = candidate["closure_receipt"]["table_receipts"]
    assert receipts[0]["period_year"] is None
    assert {cell["period_year"] for cell in receipts[0]["cell_axis"]} == {2024, 2025}

    plans = runner.build_segment_report_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={selected_ids[0]: page},
        compiled_specs=compiled,
    )
    assert [plan["target_table_refs"] for plan in plans] == [
        [{"section_id": "s1", "table_id": "t2"}]
    ]


def test_bare_year_period_end_targets_exact_table_axis(tmp_path: Path) -> None:
    page = _page()
    for column in page["sections"][0]["tables"][0]["columns"]:
        column["header_path_exact"][0] = "2025"
    _database, selected_ids, sweep, candidate, compiled = _fixture_sweep(tmp_path, page_json=page)
    assert "SEGMENT_PERIOD_END_NOT_RESOLVED" in candidate["reasons"]

    plans = runner.build_segment_report_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={selected_ids[0]: page},
        compiled_specs=compiled,
    )
    assert len(plans) == 1
    assert plans[0]["repair_scope"] == "TABLE_PERIOD_AXIS"
    assert plans[0]["target_table_refs"] == [{"section_id": "s1", "table_id": "t1"}]


def test_row_period_ambiguity_is_not_claimed_by_table_axis_repair(tmp_path: Path) -> None:
    page = _page()
    row = page["sections"][0]["tables"][0]["rows"][0]
    row["label_exact"] = "Doanh thu năm 2025 và 2024"
    row["hierarchy_path_exact"] = [row["label_exact"]]
    page["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = "50)"
    _database, selected_ids, sweep, candidate, compiled = _fixture_sweep(tmp_path, page_json=page)
    assert "SEGMENT_ROW_PERIOD_AMBIGUOUS" in candidate["reasons"]
    assert "SEGMENT_MONEY_CELL_AMBIGUOUS" in candidate["reasons"]
    assert not set(candidate["reasons"]) & runner._PERIOD_REASONS

    assert (
        runner.build_segment_report_region_repair_plans_v1(
            sweep=sweep,
            page_json_by_version={selected_ids[0]: page},
            compiled_specs=compiled,
        )
        == []
    )


def test_unresolved_candidate_without_supported_ocr_reason_is_clean_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][-1] = "999"
    page_database, selected_ids, sweep, candidate, compiled = _fixture_sweep(
        tmp_path, page_json=page
    )
    assert not set(candidate["reasons"]) & (runner._PERIOD_REASONS | runner._MONEY_REASONS)
    results_database, family_run_id = _store_sweep(
        tmp_path,
        monkeypatch,
        page_database=page_database,
        selected_ids=selected_ids,
        sweep=sweep,
    )

    plans, identifiers = runner.enqueue_segment_report_region_repair_plans_v1(
        results_database,
        family_run_id=family_run_id,
        sweep=sweep,
        page_json_by_version={selected_ids[0]: page},
        compiled_specs=compiled,
    )
    assert plans == []
    assert identifiers == []
    with sqlite3.connect(results_database) as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM sqlite_master "
                "WHERE type='table' AND name='family_region_repair_job'"
            ).fetchone()[0]
            == 0
        )
    assert (
        pending_gemini_family_region_repair_plans_v1(results_database, family_run_id=family_run_id)
        == []
    )


def test_typed_money_failure_without_matching_cell_lineage_fails_closed(
    tmp_path: Path,
) -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "1.2.3"
    _database, selected_ids, _sweep, candidate, compiled = _fixture_sweep(tmp_path, page_json=page)
    forged = copy.deepcopy(candidate)
    invalid = next(
        cell
        for receipt in forged["closure_receipt"]["table_receipts"]
        for cell in receipt["cell_axis"]
        if cell["state"] == "INVALID_MONEY_SOURCE"
    )
    invalid["state"] = "RAW_INTEGER"
    regions = runner._candidate_region_axis(
        forged,
        trial={
            "document_ordinal": 1,
            "source_logical_name": SOURCE_NAME,
            "source_sha256": SOURCE_SHA256,
        },
    )
    receipts = runner._candidate_table_receipts(forged, regions=regions)
    with pytest.raises(
        runner.RunGeminiJsonSegmentReportRegionRepairQueueV1Error,
        match="typed money failure has no exact cell frontier",
    ):
        runner._money_cell_frontier(
            forged,
            receipts=receipts,
            page_json_by_version={selected_ids[0]: page},
            compiled_specs=compiled,
        )
