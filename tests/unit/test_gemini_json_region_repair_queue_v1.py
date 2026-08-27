from __future__ import annotations

from copy import deepcopy

from test_gemini_json_flat_accounting_family_v1 import _page, _specs

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
