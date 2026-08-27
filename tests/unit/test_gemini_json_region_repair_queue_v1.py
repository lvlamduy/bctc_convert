from __future__ import annotations

from copy import deepcopy

from test_gemini_json_flat_accounting_family_v1 import _page, _specs
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
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
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
