from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.gemini_json_first_corpus_ledger_v1 import (
    GeminiJsonFirstCorpusLedgerV1Error,
    corpus_ledger_summary_v1,
    initialize_gemini_json_first_corpus_ledger_v1,
    list_corpus_tasks_v1,
    seal_google_fallback_corpus_task_v1,
    seal_offline_revalidated_corpus_task_v1,
    transition_corpus_task_v1,
    validate_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import (
    GOOGLE_ROUTE,
    OPENROUTER_ROUTE,
    build_gemini_json_first_corpus_plan_v1,
)


def _plan():
    return build_gemini_json_first_corpus_plan_v1(
        [
            {
                "relative_path": "MBB/2025/a.pdf",
                "source_sha256": "1" * 64,
                "source_size_bytes": 100,
                "page_count": 61,
            },
            {
                "relative_path": "VCB/2025/b.pdf",
                "source_sha256": "2" * 64,
                "source_size_bytes": 200,
                "page_count": 35,
            },
        ],
        google_batch_chunk_pages=30,
        openrouter_page_fraction="0.35",
        openrouter_workers=5,
    )


def test_plan_replay_and_ledger_cover_exact_tasks_pages_and_documents(tmp_path) -> None:
    plan = _plan()
    assert validate_gemini_json_first_corpus_plan_v1(plan) == plan
    ledger = tmp_path / "ledger.sqlite3"
    summary = initialize_gemini_json_first_corpus_ledger_v1(ledger, plan=plan)
    assert summary == corpus_ledger_summary_v1(ledger)
    assert summary["documents"] == 2
    assert summary["total_pages"] == 96
    assert summary["total_tasks"] == plan["summary"]["task_count"]
    assert summary["prompt_variant"] == "simple"
    assert ledger.stat().st_mode & 0o777 == 0o600
    tasks = list_corpus_tasks_v1(ledger, states=["PENDING"])
    assert len(tasks) == plan["summary"]["task_count"]
    assert sum(task["last_physical_page"] - task["first_physical_page"] + 1 for task in tasks) == 96
    assert {task["route"] for task in tasks} == {GOOGLE_ROUTE, OPENROUTER_ROUTE}
    assert all(task["artifact_relative_path"].startswith("tasks/") for task in tasks)
    with pytest.raises(GeminiJsonFirstCorpusLedgerV1Error, match="overwrite"):
        initialize_gemini_json_first_corpus_ledger_v1(ledger, plan=plan)


def test_plan_coherent_mutation_and_invalid_filters_reject(tmp_path) -> None:
    plan = _plan()
    changed = copy.deepcopy(plan)
    changed["documents"][0]["tasks"][0]["last_physical_page"] -= 1
    with pytest.raises(GeminiJsonFirstCorpusLedgerV1Error, match="replay"):
        validate_gemini_json_first_corpus_plan_v1(changed)
    ledger = tmp_path / "ledger.sqlite3"
    initialize_gemini_json_first_corpus_ledger_v1(ledger, plan=plan)
    with pytest.raises(GeminiJsonFirstCorpusLedgerV1Error, match="state filter"):
        list_corpus_tasks_v1(ledger, states=["UNKNOWN"])
    with pytest.raises(GeminiJsonFirstCorpusLedgerV1Error, match="route filter"):
        list_corpus_tasks_v1(ledger, route="UNKNOWN")


def test_task_transitions_are_append_only_bounded_and_expected_state_guarded(tmp_path) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    initialize_gemini_json_first_corpus_ledger_v1(
        ledger,
        plan=_plan(),
        max_task_attempts=2,
    )
    task = list_corpus_tasks_v1(ledger, states=["PENDING"], limit=1)[0]
    submitted = transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="PENDING",
        next_state="SUBMITTED",
        receipt={"provider_batch_name": "batch-1"},
        provider_job_ref="batch-1",
    )
    assert submitted["attempt_count"] == 1
    assert submitted["state"] == "SUBMITTED"
    retry = transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="SUBMITTED",
        next_state="NEEDS_RETRY",
        receipt={"failed_pages": [1]},
    )
    assert retry["attempt_count"] == 1
    running = transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="NEEDS_RETRY",
        next_state="RUNNING",
        receipt={"retry": 2},
    )
    assert running["attempt_count"] == 2
    succeeded = transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state="SUCCEEDED",
        receipt={"ingested_pages": 30},
    )
    assert succeeded["state"] == "SUCCEEDED"
    with pytest.raises(GeminiJsonFirstCorpusLedgerV1Error, match="transition"):
        transition_corpus_task_v1(
            ledger,
            task_id=task["task_id"],
            expected_state="SUCCEEDED",
            next_state="RUNNING",
            receipt={"bad": True},
        )
    with pytest.raises(GeminiJsonFirstCorpusLedgerV1Error, match="current state"):
        transition_corpus_task_v1(
            ledger,
            task_id=list_corpus_tasks_v1(ledger, states=["PENDING"], limit=1)[0]["task_id"],
            expected_state="RUNNING",
            next_state="SUCCEEDED",
            receipt={"bad": True},
        )

    other = list_corpus_tasks_v1(ledger, states=["PENDING"], limit=1)[0]
    transition_corpus_task_v1(
        ledger,
        task_id=other["task_id"],
        expected_state="PENDING",
        next_state="SUBMITTED",
        receipt={"provider_batch_name": "batch-2"},
    )
    provider_running = transition_corpus_task_v1(
        ledger,
        task_id=other["task_id"],
        expected_state="SUBMITTED",
        next_state="RUNNING",
        receipt={"provider_state": "RUNNING"},
    )
    assert provider_running["attempt_count"] == 1

    fallback = transition_corpus_task_v1(
        ledger,
        task_id=other["task_id"],
        expected_state="RUNNING",
        next_state="FALLBACK_PENDING",
        receipt={"failed_pages": [1]},
    )
    assert fallback["attempt_count"] == 1
    fallback_running = transition_corpus_task_v1(
        ledger,
        task_id=other["task_id"],
        expected_state="FALLBACK_PENDING",
        next_state="FALLBACK_RUNNING",
        receipt={"gateway": "OPENROUTER"},
    )
    assert fallback_running["attempt_count"] == 1
    fallback_retry = transition_corpus_task_v1(
        ledger,
        task_id=other["task_id"],
        expected_state="FALLBACK_RUNNING",
        next_state="FALLBACK_PENDING",
        receipt={"fallback_attempt": 1},
    )
    assert fallback_retry["attempt_count"] == 1


def test_failed_openrouter_task_can_only_be_sealed_by_complete_offline_revalidation(
    tmp_path,
) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    initialize_gemini_json_first_corpus_ledger_v1(ledger, plan=_plan())
    task = list_corpus_tasks_v1(ledger, states=["PENDING"], route=OPENROUTER_ROUTE, limit=1)[0]
    running = transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="PENDING",
        next_state="RUNNING",
        receipt={"document_run_started": True},
    )
    transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state="FAILED",
        receipt={"semantic_failed_pages": [1]},
    )
    result = {
        "disposition": "SUCCEEDED",
        "failed_pages": [],
        "manifest_id": "gfdmv1:manifest:" + "3" * 64,
        "offline_missing_pages": [],
        "semantic_failed_pages": [],
    }
    repaired = seal_offline_revalidated_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        receipt={
            "document_manifest_id": result["manifest_id"],
            "offline_revalidated": True,
            "replayed_pages": [1],
            "result": result,
        },
    )
    assert repaired["state"] == "SUCCEEDED"
    assert repaired["attempt_count"] == running["attempt_count"]

    tampered = copy.deepcopy(result)
    tampered["semantic_failed_pages"] = [1]
    with pytest.raises(GeminiJsonFirstCorpusLedgerV1Error):
        seal_offline_revalidated_corpus_task_v1(
            ledger,
            task_id=task["task_id"],
            receipt={
                "document_manifest_id": result["manifest_id"],
                "offline_revalidated": True,
                "replayed_pages": [1],
                "result": tampered,
            },
        )


def test_failed_openrouter_task_can_be_sealed_by_complete_google_page_fallback(tmp_path) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    initialize_gemini_json_first_corpus_ledger_v1(ledger, plan=_plan())
    task = list_corpus_tasks_v1(ledger, states=["PENDING"], route=OPENROUTER_ROUTE, limit=1)[0]
    running = transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="PENDING",
        next_state="RUNNING",
        receipt={"document_run_started": True},
    )
    transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state="FAILED",
        receipt={"failed_pages": [1]},
    )
    result = {
        "disposition": "SUCCEEDED",
        "failed_pages": [],
        "manifest_id": "gfdmv1:manifest:" + "4" * 64,
        "offline_missing_pages": [],
        "semantic_failed_pages": [],
    }
    repaired = seal_google_fallback_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        receipt={
            "document_manifest_id": result["manifest_id"],
            "fallback_gateway": "GOOGLE_GEMINI_API",
            "fallback_pages": [1],
            "result": result,
        },
    )
    assert repaired["state"] == "SUCCEEDED"
    assert repaired["attempt_count"] == running["attempt_count"]
