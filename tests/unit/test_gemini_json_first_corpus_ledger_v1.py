from __future__ import annotations

import copy
import json
from hashlib import sha256

import pytest

from bctc_ai.evaluation.gemini_json_first_corpus_ledger_v1 import (
    GeminiJsonFirstCorpusLedgerV1Error,
    claim_google_document_for_openrouter_acceleration_v1,
    corpus_ledger_summary_v1,
    initialize_gemini_json_first_corpus_ledger_v1,
    list_corpus_tasks_v1,
    recover_failed_openrouter_artifact_collision_v1,
    requeue_failed_openrouter_corpus_task_v1,
    seal_current_document_revalidated_corpus_tasks_v1,
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
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
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
        "cached_pages": list(range(2, task["last_physical_page"] + 1)),
        "disposition": "SUCCEEDED",
        "failed_pages": [],
        "ingested_pages": [1],
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
            "revalidated_pages": list(
                range(task["first_physical_page"], task["last_physical_page"] + 1)
            ),
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
                "revalidated_pages": list(
                    range(task["first_physical_page"], task["last_physical_page"] + 1)
                ),
                "result": tampered,
            },
        )


def test_failed_openrouter_task_can_be_requeued_once_with_exact_failed_pages(tmp_path) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    initialize_gemini_json_first_corpus_ledger_v1(
        ledger,
        plan=_plan(),
        max_task_attempts=3,
    )
    task = list_corpus_tasks_v1(ledger, states=["PENDING"], route=OPENROUTER_ROUTE, limit=1)[0]
    transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="PENDING",
        next_state="RUNNING",
        receipt={"document_run_started": True},
    )
    retry = transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state="NEEDS_RETRY",
        receipt={"failed_pages": [1], "semantic_failed_pages": []},
    )
    assert retry["attempt_count"] == 1
    transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="NEEDS_RETRY",
        next_state="RUNNING",
        receipt={"document_retry_started": True},
    )
    failed = transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state="FAILED",
        receipt={
            "failed_pages": [1, 2],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [2],
            "unresolved_pages": [2],
        },
    )
    assert failed["attempt_count"] == 2

    requeued = requeue_failed_openrouter_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
    )
    assert requeued["state"] == "NEEDS_RETRY"
    assert requeued["attempt_count"] == 2
    receipt = json.loads(requeued["last_receipt_json"])
    assert receipt["format_version"] == "GEMINI_JSON_FIRST_OPENROUTER_FAILED_REQUEUE_V1"
    assert receipt["failed_pages"] == [1, 2]
    assert receipt["semantic_failed_pages"] == [2]
    assert receipt["unresolved_pages"] == [2]
    assert len(receipt["prior_failed_receipt_sha256"]) == 64

    final_running = transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="NEEDS_RETRY",
        next_state="RUNNING",
        receipt={"final_retry_started": True},
    )
    assert final_running["attempt_count"] == 3
    transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state="FAILED",
        receipt={"failed_pages": [1]},
    )
    with pytest.raises(GeminiJsonFirstCorpusLedgerV1Error, match="bound is exhausted"):
        requeue_failed_openrouter_corpus_task_v1(ledger, task_id=task["task_id"])


def test_exhausted_local_retry_contract_collision_recovers_same_attempt(tmp_path) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    initialize_gemini_json_first_corpus_ledger_v1(
        ledger,
        plan=_plan(),
        max_task_attempts=3,
    )
    task = list_corpus_tasks_v1(
        ledger,
        states=["PENDING"],
        route=OPENROUTER_ROUTE,
        limit=1,
    )[0]
    pages = list(range(task["first_physical_page"], task["first_physical_page"] + 5))
    legacy_frontiers = {
        "items": [pages[0], pages[2], pages[4]],
        "simple": [pages[1], pages[3], pages[4]],
    }
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
        next_state="NEEDS_RETRY",
        receipt={
            "failed_pages": pages,
            "recitation_failed_pages": [],
            "semantic_failed_pages": [pages[2], pages[4]],
            "unresolved_pages": [],
        },
    )
    transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="NEEDS_RETRY",
        next_state="RUNNING",
        receipt={"document_run_started": True},
    )
    transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state="FAILED",
        receipt={
            "alternate_prompt_variants": [
                {
                    "physical_pages": legacy_frontiers["simple"],
                    "prompt_variant": "simple",
                },
                {
                    "physical_pages": legacy_frontiers["items"],
                    "prompt_variant": "items",
                },
            ],
            "failed_pages": pages[:3],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [pages[2]],
            "unresolved_pages": [],
        },
    )
    requeue_failed_openrouter_corpus_task_v1(ledger, task_id=task["task_id"])
    transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="NEEDS_RETRY",
        next_state="RUNNING",
        receipt={"document_run_started": True},
    )
    exhausted = transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state="FAILED",
        receipt={
            "disposition": "OPENROUTER_PROVIDER_SUBPROCESS_FAILURE",
            "provider_returncode": 1,
            "provider_stderr_bytes": len(b"local contract conflict"),
            "provider_stderr_sha256": sha256(b"local contract conflict").hexdigest(),
            "provider_stdout_bytes": 0,
            "provider_stdout_sha256": sha256(b"").hexdigest(),
            "retry_allowed": False,
        },
    )
    assert running["attempt_count"] == 1
    assert exhausted["attempt_count"] == 3

    artifact_root = tmp_path / "artifacts"
    task_root = artifact_root / task["artifact_relative_path"]
    for variant, selected_pages in legacy_frontiers.items():
        material = {
            "document": {
                "source_logical_name": task["relative_path"],
                "source_sha256": task["source_sha256"],
                "source_size_bytes": task["source_size_bytes"],
            },
            "format_version": "GEMINI_JSON_FIRST_OPENROUTER_PAGE_FRONTIER_V1",
            "page_count": task["document_page_count"],
            "prompt_variant": variant,
            "selected_physical_pages": selected_pages,
        }
        contract = {
            **material,
            "document_run_id": "gjfporv1:document:" + canonical_json_sha256_v1(material),
        }
        destination = task_root / "adaptive-retry" / variant / "document-contract.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(canonical_json_bytes_v1(contract))

    recovered = recover_failed_openrouter_artifact_collision_v1(
        ledger,
        task_id=task["task_id"],
        artifact_root=artifact_root,
    )
    assert recovered["state"] == "RUNNING"
    assert recovered["attempt_count"] == 3
    receipt = json.loads(recovered["last_receipt_json"])
    assert receipt["recovery_same_attempt"] is True
    assert receipt["failed_pages"] == pages[:3]
    assert [item["prompt_variant"] for item in receipt["collision_evidence"]] == [
        "items",
        "simple",
    ]
    assert receipt["collision_evidence"][0]["legacy_physical_pages"] == legacy_frontiers["items"]
    assert receipt["collision_evidence"][0]["retry_physical_pages"] == [pages[2]]
    assert receipt["collision_evidence"][1]["legacy_physical_pages"] == legacy_frontiers["simple"]
    assert receipt["collision_evidence"][1]["retry_physical_pages"] == pages[:2]
    with pytest.raises(GeminiJsonFirstCorpusLedgerV1Error, match="exhausted task"):
        recover_failed_openrouter_artifact_collision_v1(
            ledger,
            task_id=task["task_id"],
            artifact_root=artifact_root,
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


def test_failed_chunks_can_be_sealed_by_complete_current_document_revalidation(tmp_path) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    initialize_gemini_json_first_corpus_ledger_v1(ledger, plan=_plan())
    tasks = list_corpus_tasks_v1(ledger)
    document_plan_id = tasks[0]["document_plan_id"]
    document_tasks = [task for task in tasks if task["document_plan_id"] == document_plan_id]
    failed = document_tasks[0]
    transition_corpus_task_v1(
        ledger,
        task_id=failed["task_id"],
        expected_state="PENDING",
        next_state="FAILED",
        receipt={"provider_failure": True},
    )
    for task in document_tasks[1:]:
        transition_corpus_task_v1(
            ledger,
            task_id=task["task_id"],
            expected_state="PENDING",
            next_state="RUNNING",
            receipt={"started": True},
        )
        transition_corpus_task_v1(
            ledger,
            task_id=task["task_id"],
            expected_state="RUNNING",
            next_state="SUCCEEDED",
            receipt={"completed": True},
        )
    pages = list(range(1, failed["document_page_count"] + 1))
    receipt = {
        "current_document_revalidated": True,
        "document_manifest_id": "gfdmv1:manifest:" + "5" * 64,
        "page_image_sha256s": [
            {"image_sha256": f"{page:064x}", "physical_page": page} for page in pages
        ],
        "page_prompt_variants": [
            {
                "physical_page": page,
                "prompt_variant": "items" if page == 1 else "simple",
            }
            for page in pages
        ],
        "repaired_task_ids": [failed["task_id"]],
        "revalidated_pages": pages,
        "status_counts": {
            "FINANCIAL_NOTE_CONTENT": len(pages) - 1,
            "MIXED_FINANCIAL_CONTENT": 1,
        },
    }
    repaired = seal_current_document_revalidated_corpus_tasks_v1(
        ledger, task_id=failed["task_id"], receipt=receipt
    )
    assert [task["task_id"] for task in repaired] == [failed["task_id"]]
    assert repaired[0]["state"] == "SUCCEEDED"
    assert repaired[0]["attempt_count"] == 0

    tampered = copy.deepcopy(receipt)
    tampered["page_image_sha256s"][0]["image_sha256"] = "z" * 64
    with pytest.raises(GeminiJsonFirstCorpusLedgerV1Error, match="image frontier"):
        seal_current_document_revalidated_corpus_tasks_v1(
            ledger, task_id=failed["task_id"], receipt=tampered
        )


def test_google_document_acceleration_claim_is_atomic_resumable_and_bounded(tmp_path) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    initialize_gemini_json_first_corpus_ledger_v1(ledger, plan=_plan(), max_task_attempts=2)
    google = list_corpus_tasks_v1(ledger, states=["PENDING"], route=GOOGLE_ROUTE)
    document_plan_id = google[0]["document_plan_id"]
    document_tasks = [task for task in google if task["document_plan_id"] == document_plan_id]
    claim = claim_google_document_for_openrouter_acceleration_v1(
        ledger, task_id=document_tasks[0]["task_id"]
    )
    assert claim["claim_id"].startswith("gjfpaccelv1:claim:")
    assert [task["state"] for task in claim["tasks"]] == ["RUNNING"] * len(document_tasks)
    assert [task["attempt_count"] for task in claim["tasks"]] == [1] * len(document_tasks)
    assert {task["provider_job_ref"] for task in claim["tasks"]} == {claim["claim_id"]}
    resumed = claim_google_document_for_openrouter_acceleration_v1(
        ledger, task_id=document_tasks[-1]["task_id"]
    )
    assert resumed["claim_id"] == claim["claim_id"]
    assert [task["attempt_count"] for task in resumed["tasks"]] == [1] * len(document_tasks)

    retry_ledger = tmp_path / "retry-ledger.sqlite3"
    initialize_gemini_json_first_corpus_ledger_v1(retry_ledger, plan=_plan(), max_task_attempts=2)
    retry_tasks = list_corpus_tasks_v1(retry_ledger, states=["PENDING"], route=GOOGLE_ROUTE)
    retry_document_id = retry_tasks[0]["document_plan_id"]
    retry_document_tasks = [
        task for task in retry_tasks if task["document_plan_id"] == retry_document_id
    ]
    for task in retry_document_tasks:
        transition_corpus_task_v1(
            retry_ledger,
            task_id=task["task_id"],
            expected_state="PENDING",
            next_state="SUBMITTED",
            receipt={"provider_batch_name": "cancelled"},
        )
        transition_corpus_task_v1(
            retry_ledger,
            task_id=task["task_id"],
            expected_state="SUBMITTED",
            next_state="NEEDS_RETRY",
            receipt={"provider_batch_state": "BATCH_STATE_CANCELLED"},
        )
    already_succeeded = retry_document_tasks[-1]
    transition_corpus_task_v1(
        retry_ledger,
        task_id=already_succeeded["task_id"],
        expected_state="NEEDS_RETRY",
        next_state="RUNNING",
        receipt={"gateway": "OPENROUTER"},
        provider_job_ref="prior-openrouter-claim",
    )
    transition_corpus_task_v1(
        retry_ledger,
        task_id=already_succeeded["task_id"],
        expected_state="RUNNING",
        next_state="SUCCEEDED",
        receipt={"document_manifest_id": "gfdmv1:manifest:" + "a" * 64},
    )
    retried = claim_google_document_for_openrouter_acceleration_v1(
        retry_ledger, task_id=retry_document_tasks[0]["task_id"]
    )
    assert [task["state"] for task in retried["tasks"]] == [
        *("RUNNING" for _task in retry_document_tasks[:-1]),
        "SUCCEEDED",
    ]
    assert [task["attempt_count"] for task in retried["tasks"]] == [2] * len(retry_document_tasks)

    other_ledger = tmp_path / "other-ledger.sqlite3"
    initialize_gemini_json_first_corpus_ledger_v1(other_ledger, plan=_plan())
    other_tasks = list_corpus_tasks_v1(other_ledger, states=["PENDING"], route=GOOGLE_ROUTE)
    other_document_plan_id = other_tasks[0]["document_plan_id"]
    other_document_tasks = [
        task for task in other_tasks if task["document_plan_id"] == other_document_plan_id
    ]
    other = other_document_tasks[0]
    transition_corpus_task_v1(
        other_ledger,
        task_id=other["task_id"],
        expected_state="PENDING",
        next_state="SUBMITTED",
        receipt={"provider_batch_name": "already-submitted"},
    )
    with pytest.raises(GeminiJsonFirstCorpusLedgerV1Error, match="retryable document frontier"):
        claim_google_document_for_openrouter_acceleration_v1(
            other_ledger, task_id=other_document_tasks[-1]["task_id"]
        )
