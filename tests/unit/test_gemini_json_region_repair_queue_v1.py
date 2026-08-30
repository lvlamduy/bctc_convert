from __future__ import annotations

from copy import deepcopy

import pytest
from test_gemini_json_flat_accounting_family_v1 import (
    _loan_quality_page,
    _loan_quality_specs,
    _loan_type_page,
    _loan_type_specs,
    _page,
    _specs,
)
from test_gemini_json_interest_rate_risk_matrix_v1 import (
    _evaluate as _interest_evaluate,
)
from test_gemini_json_interest_rate_risk_matrix_v1 import (
    _page as _interest_page,
)
from test_gemini_json_interest_rate_risk_matrix_v1 import (
    _record as _interest_record,
)
from test_gemini_json_interest_rate_risk_matrix_v1 import (
    _table as _interest_table,
)
from test_gemini_json_stacked_period_accounting_family_v1 import (
    _compiled as _stacked_compiled,
)
from test_gemini_json_stacked_period_accounting_family_v1 import (
    _evaluate as _stacked_evaluate,
)
from test_gemini_json_stacked_period_accounting_family_v1 import (
    _json as _family_json,
)
from test_gemini_json_stacked_period_accounting_family_v1 import (
    _separate_period_page,
)

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    UNRESOLVED,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    evaluate_gemini_json_flat_family_table_v1,
)
from bctc_ai.evaluation.gemini_json_region_repair_queue_v1 import (
    build_family_region_repair_plans_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    _stored_candidate_repair_target_replays_v1,
    enqueue_gemini_family_region_repair_plans_v1,
    ingest_gemini_accounting_family_sweep_v1,
    pending_gemini_family_region_repair_plans_v1,
    record_gemini_family_region_repair_attempt_v1,
    resolved_gemini_family_region_repair_overlay_v1,
)


def _reference(name: str, digit: str) -> dict:
    return {"path": name, "sha256": digit * 64, "size_bytes": 123}


def test_invalid_money_cell_becomes_database_pending_region_job(tmp_path) -> None:
    topology, evaluation, schema = _specs()
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    page = deepcopy(_page())
    page["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = "-ktCap-"
    version_id = "gfpstorev1:json:" + "1" * 64
    candidate = evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id=version_id,
        physical_page=7,
        section_id="s1",
        table_id="t1",
        compiled_specs=compiled,
    )
    assert candidate["status"] == UNRESOLVED
    trial = {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": [],
        "reasons": candidate["reasons"],
        "selected_candidate_id": None,
        "source_logical_name": "ACB/2025/example.pdf",
        "source_sha256": "2" * 64,
        "status": UNRESOLVED,
    }
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[trial],
    )
    plans = build_family_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={version_id: page},
        compiled_specs=compiled,
    )
    assert len(plans) == 1
    assert plans[0]["target_ids"] == ["s1:t1:r2"]
    assert plans[0]["repair_policy"] == {
        "context_radius_by_thinking_level": {"high": 3, "low": 1, "medium": 2},
        "initial_thinking_level": "low",
        "max_attempts": 3,
        "thinking_escalation": ["medium", "high"],
    }

    database = tmp_path / "families.sqlite3"
    stored = ingest_gemini_accounting_family_sweep_v1(
        database,
        sweep=sweep,
        corpus_index_ref=_reference("corpus.json", "4"),
        implementation_refs=[_reference("runner.py", "5")],
        run_kind="EXPERIMENTAL",
    )
    identifiers = enqueue_gemini_family_region_repair_plans_v1(
        database,
        family_run_id=stored["family_run_id"],
        plans=plans,
    )
    pending = pending_gemini_family_region_repair_plans_v1(
        database, family_run_id=stored["family_run_id"]
    )
    assert identifiers == [plans[0]["repair_job_id"]]
    assert pending == [
        {
            "attempt_count": 0,
            "family_run_id": stored["family_run_id"],
            "next_thinking_level": "low",
            "plan": plans[0],
            "repair_job_id": plans[0]["repair_job_id"],
        }
    ]
    first = record_gemini_family_region_repair_attempt_v1(
        database,
        repair_job_id=plans[0]["repair_job_id"],
        thinking_level="low",
        outcome="RETRYABLE_VALIDATION_FAILURE",
        page_json_version_id=None,
        usage={"thought_tokens": 12},
        reasons=["still ambiguous"],
    )
    assert first["next_status"] == "PENDING"
    escalated = pending_gemini_family_region_repair_plans_v1(database)
    assert escalated[0]["attempt_count"] == 1
    assert escalated[0]["next_thinking_level"] == "medium"
    selected_version_id = "gfpstorev1:json:" + "6" * 64
    second = record_gemini_family_region_repair_attempt_v1(
        database,
        repair_job_id=plans[0]["repair_job_id"],
        thinking_level="medium",
        outcome="RESOLVED",
        page_json_version_id=selected_version_id,
        usage={"thought_tokens": 24},
        reasons=[],
    )
    assert second["next_status"] == "RESOLVED"
    overlay = resolved_gemini_family_region_repair_overlay_v1(
        database, family_run_id=stored["family_run_id"]
    )
    assert overlay["job_status_counts"] == {"ABSTAINED": 0, "RESOLVED": 1}
    assert overlay["replacements"] == [
        {
            "base_page_json_version_id": version_id,
            "candidate_id": candidate["candidate_id"],
            "document_ordinal": 1,
            "physical_page": 7,
            "repair_job_id": plans[0]["repair_job_id"],
            "selected_page_json_version_id": selected_version_id,
        }
    ]


def test_source_corroborated_no_change_resolves_queue_without_replacement(tmp_path) -> None:
    topology, evaluation, schema = _specs()
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    page = deepcopy(_page())
    page["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = "-ktCap-"
    version_id = "gfpstorev1:json:" + "1" * 64
    candidate = evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id=version_id,
        physical_page=7,
        section_id="s1",
        table_id="t1",
        compiled_specs=compiled,
    )
    trial = {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": [],
        "reasons": candidate["reasons"],
        "selected_candidate_id": None,
        "source_logical_name": "ACB/2025/example.pdf",
        "source_sha256": "2" * 64,
        "status": UNRESOLVED,
    }
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[trial],
    )
    plan = build_family_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={version_id: page},
        compiled_specs=compiled,
    )[0]
    database = tmp_path / "families.sqlite3"
    stored = ingest_gemini_accounting_family_sweep_v1(
        database,
        sweep=sweep,
        corpus_index_ref=_reference("corpus.json", "4"),
        implementation_refs=[_reference("runner.py", "5")],
        run_kind="EXPERIMENTAL",
    )
    enqueue_gemini_family_region_repair_plans_v1(
        database, family_run_id=stored["family_run_id"], plans=[plan]
    )
    result = record_gemini_family_region_repair_attempt_v1(
        database,
        repair_job_id=plan["repair_job_id"],
        thinking_level="low",
        outcome="SOURCE_CORROBORATED_NO_CHANGE",
        page_json_version_id=version_id,
        usage={"thought_tokens": 12},
        reasons=[],
    )
    assert result["next_status"] == "RESOLVED"
    overlay = resolved_gemini_family_region_repair_overlay_v1(
        database, family_run_id=stored["family_run_id"]
    )
    assert overlay["job_status_counts"] == {"ABSTAINED": 0, "RESOLVED": 1}
    assert overlay["replacements"] == []


def test_ready_candidate_repair_requires_exact_semantic_replay(tmp_path) -> None:
    topology, evaluation, schema = _specs()
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    version_id = "gfpstorev1:json:" + "1" * 64

    unresolved_page = deepcopy(_page())
    unresolved_page["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = "-ktCap-"
    unresolved_candidate = evaluate_gemini_json_flat_family_table_v1(
        page_json=unresolved_page,
        page_json_version_id=version_id,
        physical_page=7,
        section_id="s1",
        table_id="t1",
        compiled_specs=compiled,
    )
    unresolved_trial = {
        "candidate_count": 1,
        "candidates": [unresolved_candidate],
        "document_ordinal": 1,
        "mappings": [],
        "reasons": unresolved_candidate["reasons"],
        "selected_candidate_id": None,
        "source_logical_name": "ACB/2025/example.pdf",
        "source_sha256": "2" * 64,
        "status": UNRESOLVED,
    }
    unresolved_sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[unresolved_trial],
    )
    base_plan = build_family_region_repair_plans_v1(
        sweep=unresolved_sweep,
        page_json_by_version={version_id: unresolved_page},
        compiled_specs=compiled,
    )[0]

    ready_page = deepcopy(_page())
    ready_candidate = evaluate_gemini_json_flat_family_table_v1(
        page_json=ready_page,
        page_json_version_id=version_id,
        physical_page=7,
        section_id="s1",
        table_id="t1",
        compiled_specs=compiled,
    )
    assert ready_candidate["status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    ready_trial = {
        "candidate_count": 1,
        "candidates": [ready_candidate],
        "document_ordinal": 1,
        "mappings": ready_candidate["mappings"],
        "reasons": [],
        "selected_candidate_id": ready_candidate["candidate_id"],
        "source_logical_name": "ACB/2025/example.pdf",
        "source_sha256": "2" * 64,
        "status": ready_candidate["status"],
    }
    ready_sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[ready_trial],
    )
    plan = {
        **base_plan,
        "candidate_semantic_replay_sha256": canonical_json_sha256_v1(ready_candidate),
    }
    material = {key: plan[key] for key in plan if key != "repair_job_id"}
    plan["repair_job_id"] = "gjfrrqv1:job:" + canonical_json_sha256_v1(material)

    database = tmp_path / "families.sqlite3"
    stored = ingest_gemini_accounting_family_sweep_v1(
        database,
        sweep=ready_sweep,
        corpus_index_ref=_reference("corpus.json", "4"),
        implementation_refs=[_reference("runner.py", "5")],
        run_kind="EXPERIMENTAL",
    )
    assert enqueue_gemini_family_region_repair_plans_v1(
        database,
        family_run_id=stored["family_run_id"],
        plans=[plan],
    ) == [plan["repair_job_id"]]

    forged = {**plan, "candidate_semantic_replay_sha256": "0" * 64}
    material = {key: forged[key] for key in forged if key != "repair_job_id"}
    forged["repair_job_id"] = "gjfrrqv1:job:" + canonical_json_sha256_v1(material)
    with pytest.raises(RuntimeError, match="candidate does not replay"):
        enqueue_gemini_family_region_repair_plans_v1(
            database,
            family_run_id=stored["family_run_id"],
            plans=[forged],
        )


def test_ready_cluster_repair_may_target_one_exact_nonprimary_component() -> None:
    records = [
        _interest_record(_interest_page(_interest_table(title="Tại ngày 31/12/2025")), ordinal=1),
        _interest_record(_interest_page(_interest_table(title="Tại ngày 31/12/2024")), ordinal=2),
    ]
    _cluster, candidate = _interest_evaluate(records)
    assert candidate["status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    trial = {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": candidate["mappings"],
        "reasons": [],
        "selected_candidate_id": candidate["candidate_id"],
        "source_logical_name": records[0]["source_logical_name"],
        "source_sha256": records[0]["source_sha256"],
        "status": candidate["status"],
    }
    plan = {
        "base_page_json_version_id": records[1]["page_json_version_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_semantic_replay_sha256": canonical_json_sha256_v1(candidate),
        "document_ordinal": 1,
        "family_id": "INTEREST_RATE_RISK",
        "format_version": "GEMINI_JSON_REGION_REPAIR_QUEUE_V1",
        "physical_page": records[1]["physical_page"],
        "section_id": "s1",
        "source_logical_name": records[1]["source_logical_name"],
        "source_sha256": records[1]["source_sha256"],
        "table_id": "t1",
        "target_ids": ["r1:c1"],
    }
    candidate_row = (
        candidate["page_json_version_id"],
        candidate["physical_page"],
        candidate["section_id"],
        candidate["table_id"],
        candidate["status"],
        records[0]["source_logical_name"],
        records[0]["source_sha256"],
    )
    assert _stored_candidate_repair_target_replays_v1(
        plan=plan,
        candidate_row=candidate_row,
        stored_trial=trial,
        stored_candidate=candidate,
    )
    foreign = {**plan, "base_page_json_version_id": "gfpstorev1:json:" + "f" * 64}
    assert not _stored_candidate_repair_target_replays_v1(
        plan=foreign,
        candidate_row=candidate_row,
        stored_trial=trial,
        stored_candidate=candidate,
    )


def test_missing_title_footnote_narrative_targets_only_its_section() -> None:
    topology, evaluation, schema = _loan_quality_specs()
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    page = _loan_quality_page()
    page["sections"][0]["tables"][0]["title_exact"] += " (*)"
    version_id = "gfpstorev1:json:" + "6" * 64
    candidate = evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id=version_id,
        physical_page=18,
        section_id="s1",
        table_id="t1",
        compiled_specs=compiled,
    )
    assert candidate["reasons"] == ["TITLE_FOOTNOTE_NARRATIVE_SOURCE_NOT_EXACT"]
    trial = {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": [],
        "reasons": candidate["reasons"],
        "selected_candidate_id": None,
        "source_logical_name": "ACB/2025/example.pdf",
        "source_sha256": "7" * 64,
        "status": UNRESOLVED,
    }
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "8" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[trial],
    )
    plans = build_family_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={version_id: page},
        compiled_specs=compiled,
    )
    assert len(plans) == 1
    assert plans[0]["repair_scope"] == "SECTION_NARRATIVES"
    assert plans[0]["target_table_refs"] == [{"section_id": "s1", "table_id": "t1"}]
    assert plans[0]["trigger_kinds"] == ["SECTION_NARRATIVE_SOURCE_INCOMPLETE"]


def test_stacked_lane_failure_targets_exact_cross_table_row_with_header_context() -> None:
    page = _separate_period_page()
    page["sections"][0]["tables"][0]["rows"][1]["values_exact"][3] = "9"
    candidate = _stacked_evaluate(page)
    assert candidate["status"] == UNRESOLVED
    topology = _family_json("tm-derivative-financial-instruments-topology-v1.json")
    evaluation = _family_json("tm-derivative-financial-instruments-evaluation-v1.json")
    schema = _family_json("tm-derivative-financial-instruments-schema-binding-v1.json")
    trial = {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": [],
        "reasons": candidate["reasons"],
        "selected_candidate_id": None,
        "source_logical_name": "ACB/2025/derivative.pdf",
        "source_sha256": "7" * 64,
        "status": UNRESOLVED,
    }
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "8" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[trial],
    )
    plans = build_family_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={candidate["page_json_version_id"]: page},
        compiled_specs=_stacked_compiled(),
    )
    assert len(plans) == 1
    assert plans[0]["component_table_refs"] == [
        {"section_id": "s1", "table_id": "t1"},
        {"section_id": "s1", "table_id": "t2"},
    ]
    assert plans[0]["target_ids"] == ["s1:t1:r2"]
    assert plans[0]["trigger_kinds"] == ["UNSATISFIED_EXACT_EQUATION"]


def test_stacked_missing_period_axis_targets_only_the_bound_table_headers() -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        table["title_exact"] = None
        table["columns"] = [
            {
                **column,
                "header_path_exact": [
                    value
                    for value in column["header_path_exact"]
                    if "2025" not in value and "2024" not in value
                ],
            }
            for column in table["columns"]
        ]
    candidate = _stacked_evaluate(page)
    assert candidate["status"] == UNRESOLVED
    topology = _family_json("tm-derivative-financial-instruments-topology-v1.json")
    evaluation = _family_json("tm-derivative-financial-instruments-evaluation-v1.json")
    schema = _family_json("tm-derivative-financial-instruments-schema-binding-v1.json")
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "9" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[
            {
                "candidate_count": 1,
                "candidates": [candidate],
                "document_ordinal": 1,
                "mappings": [],
                "reasons": candidate["reasons"],
                "selected_candidate_id": None,
                "source_logical_name": "ACB/2025/undated-derivative.pdf",
                "source_sha256": "a" * 64,
                "status": UNRESOLVED,
            }
        ],
    )
    plans = build_family_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={candidate["page_json_version_id"]: page},
        compiled_specs=_stacked_compiled(),
    )
    assert len(plans) == 1
    assert plans[0]["repair_scope"] == "TABLE_PERIOD_AXIS"
    assert plans[0]["target_table_refs"] == [
        {"section_id": "s1", "table_id": "t1"},
        {"section_id": "s1", "table_id": "t2"},
    ]
    assert plans[0]["trigger_kinds"] == ["TABLE_PERIOD_AXIS_INCOMPLETE"]


def test_stacked_presentation_failure_targets_only_the_printed_net_rows() -> None:
    page = _separate_period_page()
    for table in page["sections"][0]["tables"]:
        table["rows"].append(
            {
                "hierarchy_path_exact": ["Giá trị thuần"],
                "label_exact": "Giá trị thuần",
                "row_kind": "SUBTOTAL",
                "values_exact": [None, None, None, "999"],
            }
        )
    candidate = _stacked_evaluate(page)
    assert candidate["status"] == UNRESOLVED
    topology = _family_json("tm-derivative-financial-instruments-topology-v1.json")
    evaluation = _family_json("tm-derivative-financial-instruments-evaluation-v1.json")
    schema = _family_json("tm-derivative-financial-instruments-schema-binding-v1.json")
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "b" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[
            {
                "candidate_count": 1,
                "candidates": [candidate],
                "document_ordinal": 1,
                "mappings": [],
                "reasons": candidate["reasons"],
                "selected_candidate_id": None,
                "source_logical_name": "HDB/2025/derivative.pdf",
                "source_sha256": "c" * 64,
                "status": UNRESOLVED,
            }
        ],
    )
    plans = build_family_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={candidate["page_json_version_id"]: page},
        compiled_specs=_stacked_compiled(),
    )
    assert plans[0]["repair_scope"] == "ROW_VALUES"
    assert plans[0]["target_ids"] == ["s1:t1:r7", "s1:t2:r7"]


def test_missing_explicit_family_title_schedules_table_axis_before_row_repairs() -> None:
    topology, evaluation, schema = _loan_type_specs()
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    page = _loan_type_page(percentage_companions=False)
    section = page["sections"][0]
    section["title_exact"] = "Thuyết minh báo cáo tài chính (tiếp theo)"
    section["tables"][0]["title_exact"] = None
    version_id = "gfpstorev1:json:" + "a" * 64
    candidate = evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id=version_id,
        physical_page=11,
        section_id="s1",
        table_id="t1",
        compiled_specs=compiled,
    )
    assert "FAMILY_PARENT_NOT_VISIBLE_IN_SECTION_TABLE_OR_UNIQUE_ROW" in candidate["reasons"]
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "b" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[
            {
                "candidate_count": 1,
                "candidates": [candidate],
                "document_ordinal": 1,
                "mappings": [],
                "reasons": candidate["reasons"],
                "selected_candidate_id": None,
                "source_logical_name": "VPB/2025/loan-type.pdf",
                "source_sha256": "c" * 64,
                "status": UNRESOLVED,
            }
        ],
    )
    plans = build_family_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={version_id: page},
        compiled_specs=compiled,
    )
    assert len(plans) == 1
    assert plans[0]["repair_scope"] == "TABLE_TITLE_AND_COLUMNS"
    assert plans[0]["target_table_refs"] == [{"section_id": "s1", "table_id": "t1"}]
    assert plans[0]["target_ids"] == ["s1:t1:r1", "s1:t1:r2", "s1:t1:r3"]
    assert plans[0]["trigger_kinds"] == ["TABLE_EXPLICIT_FAMILY_TITLE_MISSING"]


def test_unbound_visible_numeric_row_queues_exact_label_and_value_reread() -> None:
    topology, evaluation, schema = _loan_type_specs()
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    page = _loan_type_page(percentage_companions=False)
    row = page["sections"][0]["tables"][0]["rows"][1]
    row["label_exact"] = "Cho vay chiết khấu công cụ chuyển"
    row["hierarchy_path_exact"][-1] = row["label_exact"]
    version_id = "gfpstorev1:json:" + "d" * 64
    candidate = evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id=version_id,
        physical_page=11,
        section_id="s1",
        table_id="t1",
        compiled_specs=compiled,
    )
    assert "UNBOUND_VISIBLE_NUMERIC_ROWS:2" in candidate["reasons"]
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "e" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[
            {
                "candidate_count": 1,
                "candidates": [candidate],
                "document_ordinal": 1,
                "mappings": [],
                "reasons": candidate["reasons"],
                "selected_candidate_id": None,
                "source_logical_name": "CTG/2025/loan-type.pdf",
                "source_sha256": "f" * 64,
                "status": UNRESOLVED,
            }
        ],
    )
    plans = build_family_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={version_id: page},
        compiled_specs=compiled,
    )
    assert len(plans) == 1
    assert plans[0]["repair_scope"] == "ROW_LABEL_AND_VALUES"
    assert plans[0]["target_ids"] == ["s1:t1:r2"]
    assert set(plans[0]["trigger_kinds"]) == {
        "UNMATCHED_SOURCE_LABEL",
        "UNSATISFIED_EXACT_EQUATION",
    }
