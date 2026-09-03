from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import threading
from argparse import Namespace
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import (
    build_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts/experiments/run_gemini_json_first_corpus_supervisor_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "run_gemini_json_first_corpus_supervisor_v1", _SCRIPT
)
assert _SPEC is not None and _SPEC.loader is not None
target = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = target
_SPEC.loader.exec_module(target)


def test_paid_command_preflights_openrouter_credential_before_dispatch(
    monkeypatch, tmp_path
) -> None:
    key_file = tmp_path / "openrouter"
    args = Namespace(command="run", openrouter_key_file=key_file)

    class Parser:
        @staticmethod
        def parse_args():
            return args

    calls = []
    monkeypatch.setattr(target, "_parser", lambda: Parser())
    monkeypatch.setattr(target, "run_corpus", lambda _args: calls.append(_args))

    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="credential preflight failed before task execution",
    ):
        target.main()
    assert calls == []

    key_file.write_text("OPENROUTER_API_KEY=test-key-value-that-is-long-enough\n")
    key_file.chmod(0o600)
    monkeypatch.setattr(
        target,
        "run_corpus",
        lambda _args: calls.append(_args) or {"disposition": "SUCCEEDED"},
    )
    assert target.main() == 0
    assert calls == [args]


def test_provider_dispatcher_lock_is_exclusive_per_ledger(tmp_path) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    first = target._acquire_corpus_execution_lock_v1(ledger)
    try:
        with pytest.raises(
            target.RunGeminiJsonFirstCorpusSupervisorV1Error,
            match="another corpus provider dispatcher already owns this ledger",
        ):
            target._acquire_corpus_execution_lock_v1(ledger)
    finally:
        first.close()

    resumed = target._acquire_corpus_execution_lock_v1(ledger)
    resumed.close()


def test_openrouter_stale_snapshot_skips_task_already_claimed_by_agy(monkeypatch, tmp_path) -> None:
    task = {
        "attempt_count": 0,
        "first_physical_page": 1,
        "last_physical_page": 1,
        "provider_job_ref": None,
        "state": "PENDING",
        "task_id": "gjfptaskv1:" + "a" * 64,
    }
    monkeypatch.setattr(target, "_retry_prompt_frontiers_v1", lambda _task: None)
    monkeypatch.setattr(target, "_protected_retry_pages_v1", lambda _task: [])
    monkeypatch.setattr(
        target,
        "transition_corpus_task_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            target.GeminiJsonFirstCorpusLedgerV1Error("state raced")
        ),
    )
    monkeypatch.setattr(
        target,
        "list_corpus_tasks_v1",
        lambda _ledger: [
            {
                **task,
                "provider_job_ref": "agyjobv1:" + "b" * 64,
                "state": "SUBMITTED",
            }
        ],
    )
    result = target._run_openrouter(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=tmp_path,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=20,
        google_key_file=tmp_path / "google",
        google_key_slot=1,
        provider_timeout_seconds=900,
        max_attempts=3,
        openrouter_only=True,
    )
    assert result == {
        "disposition": "SKIPPED_AFTER_AGY_CLAIM_RACE",
        "task_id": task["task_id"],
    }


def test_adaptive_manifest_accepts_cheapest_openrouter_standard_fallback(
    monkeypatch, tmp_path
) -> None:
    captured = {}

    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )

    def build_manifest(_database, **kwargs):
        captured.update(kwargs)
        return {"document_manifest_id": "gfdmv1:manifest:" + "a" * 64}

    monkeypatch.setattr(target, "build_financial_document_manifest_v1", build_manifest)
    manifest = target._page_variant_manifest_v1(
        task={
            "document_page_count": 2,
            "first_physical_page": 1,
            "last_physical_page": 2,
            "relative_path": "MBB/2025/report.pdf",
            "source_sha256": "b" * 64,
        },
        ledger=tmp_path / "ledger.sqlite3",
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        page_image_sha256s={1: "1" * 64, 2: "2" * 64},
        page_prompt_variants={1: "simple", 2: "items"},
        write=False,
    )

    assert manifest["document_manifest_id"].startswith("gfdmv1:manifest:")
    assert captured["allowed_gateway_service_tiers"] == [
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-low"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-medium"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-high"},
        {
            "gateway": "GOOGLE_GEMINI_API",
            "requested_service_tier": "standard",
        },
        {"gateway": "OPENROUTER", "requested_service_tier": "flex"},
        {"gateway": "OPENROUTER", "requested_service_tier": "standard"},
    ]
    assert captured["preferred_gateway_service_tiers"] == [
        {"gateway": "OPENROUTER", "requested_service_tier": "flex"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-low"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-medium"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-high"},
        {"gateway": "OPENROUTER", "requested_service_tier": "standard"},
        {
            "gateway": "GOOGLE_GEMINI_API",
            "requested_service_tier": "standard",
        },
    ]
    assert target._allowed_gateway_service_tiers_v1() == [
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-low"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-medium"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-high"},
        {
            "gateway": "GOOGLE_GEMINI_API",
            "requested_service_tier": "standard",
        },
        {
            "gateway": "GOOGLE_GEMINI_BATCH_API",
            "requested_service_tier": "batch",
        },
        {"gateway": "OPENROUTER", "requested_service_tier": "flex"},
        {"gateway": "OPENROUTER", "requested_service_tier": "standard"},
    ]
    assert target._preferred_gateway_service_tiers_v1() == [
        {"gateway": "OPENROUTER", "requested_service_tier": "flex"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-low"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-medium"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-high"},
        {"gateway": "OPENROUTER", "requested_service_tier": "standard"},
        {
            "gateway": "GOOGLE_GEMINI_BATCH_API",
            "requested_service_tier": "batch",
        },
        {
            "gateway": "GOOGLE_GEMINI_API",
            "requested_service_tier": "standard",
        },
    ]


def _plan():
    return build_gemini_json_first_corpus_plan_v1(
        [
            {
                "relative_path": "MBB/2025/a.pdf",
                "source_sha256": "1" * 64,
                "source_size_bytes": 100,
                "page_count": 31,
            },
            {
                "relative_path": "VCB/2025/b.pdf",
                "source_sha256": "2" * 64,
                "source_size_bytes": 200,
                "page_count": 10,
            },
        ],
        google_batch_chunk_pages=30,
        openrouter_page_fraction="0.25",
    )


def test_init_and_status_cli_are_exact_and_resume_visible(tmp_path) -> None:
    plan_path = tmp_path / "plan.json"
    ledger = tmp_path / "ledger.sqlite3"
    plan_path.write_bytes(canonical_json_bytes_v1(_plan()))
    plan_path.chmod(0o444)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(_ROOT / "src")
    initialized = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "init",
            "--plan",
            str(plan_path),
            "--ledger",
            str(ledger),
            "--prompt-variant",
            "simple",
        ],
        cwd=_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    status = subprocess.run(
        [sys.executable, str(_SCRIPT), "status", "--ledger", str(ledger)],
        cwd=_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(initialized.stdout) == json.loads(status.stdout)
    payload = json.loads(status.stdout)
    assert payload["documents"] == 2
    assert payload["total_pages"] == 41
    assert payload["prompt_variant"] == "simple"
    assert sum(item["tasks"] for item in payload["progress"]) == _plan()["summary"]["task_count"]


def test_single_openrouter_task_runner_is_resumable_and_forces_no_google(
    monkeypatch, tmp_path
) -> None:
    plan = build_gemini_json_first_corpus_plan_v1(
        [
            {
                "relative_path": "vietstock_bctc/ABB/2025/report.pdf",
                "source_sha256": "3" * 64,
                "source_size_bytes": 100,
                "page_count": 2,
            }
        ],
        openrouter_page_fraction="1.0",
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_bytes(canonical_json_bytes_v1(plan))
    ledger = tmp_path / "ledger.sqlite3"
    target.initialize_gemini_json_first_corpus_ledger_v1(ledger, plan=plan)
    task_id = target.list_corpus_tasks_v1(ledger)[0]["task_id"]
    calls = []

    def run_openrouter(**kwargs):
        calls.append(kwargs)
        return {
            "attempt_count": 1,
            "last_receipt_json": canonical_json_bytes_v1({"completed": True}),
            "state": "SUCCEEDED",
            "task_id": kwargs["task"]["task_id"],
        }

    monkeypatch.setattr(target, "_run_openrouter", run_openrouter)
    result = target.run_one_openrouter_task(
        Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            google_key_file=tmp_path / "unused-google-key",
            ledger=ledger,
            openrouter_key_file=tmp_path / "openrouter-key",
            openrouter_only=True,
            openrouter_workers=2,
            plan=plan_path,
            provider_timeout_seconds=60,
            source_root=tmp_path / "sources",
            task_id=task_id,
        )
    )

    assert result["disposition"] == "SUCCEEDED"
    assert result["task"]["task_id"] == task_id
    assert result["ledger"]["progress"] == [
        {
            "pages": 2,
            "route": target.OPENROUTER_ROUTE,
            "state": "PENDING",
            "tasks": 1,
        }
    ]
    assert len(calls) == 1
    assert calls[0]["openrouter_only"] is True
    assert calls[0]["task"]["task_id"] == task_id


def test_openrouter_subprocess_failure_is_typed_and_never_strands_running(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "vietstock_bctc/ABB/2025/report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    plan = build_gemini_json_first_corpus_plan_v1(
        [
            {
                "relative_path": "vietstock_bctc/ABB/2025/report.pdf",
                "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
                "source_size_bytes": 3,
                "page_count": 2,
            }
        ],
        openrouter_page_fraction="1.0",
    )
    ledger = tmp_path / "ledger.sqlite3"
    target.initialize_gemini_json_first_corpus_ledger_v1(ledger, plan=plan, max_task_attempts=3)

    def command(_argv, *, expected):
        assert expected == {0, 2}
        raise target._ProviderSubprocessError(
            returncode=-9,
            stdout="partial stdout",
            stderr="child traceback",
        )

    monkeypatch.setattr(target, "_command", command)
    task = target.list_corpus_tasks_v1(ledger)[0]
    states = []
    for _attempt in range(3):
        result = target._run_openrouter(
            task=task,
            plan=plan,
            ledger=ledger,
            source_root=source_root,
            database=tmp_path / "store.sqlite3",
            artifact_root=tmp_path / "artifacts",
            openrouter_key_file=tmp_path / "openrouter-key",
            openrouter_workers=2,
            google_key_file=tmp_path / "unused-google-key",
            google_key_slot=1,
            provider_timeout_seconds=60,
            max_attempts=3,
            openrouter_only=True,
        )
        states.append(result["state"])
        receipt = json.loads(result["last_receipt_json"])
        assert receipt["disposition"] == "OPENROUTER_PROVIDER_SUBPROCESS_FAILURE"
        assert receipt["provider_returncode"] == -9
        assert receipt["provider_stdout_bytes"] == len(b"partial stdout")
        assert receipt["provider_stderr_bytes"] == len(b"child traceback")
        assert len(receipt["provider_stdout_sha256"]) == 64
        assert len(receipt["provider_stderr_sha256"]) == 64
        task = result

    assert states == ["NEEDS_RETRY", "NEEDS_RETRY", "FAILED"]
    assert receipt["retry_allowed"] is False
    assert target.list_corpus_tasks_v1(ledger)[0]["attempt_count"] == 3


def test_openrouter_subprocess_failure_preserves_exact_adaptive_retry_frontier(
    tmp_path,
) -> None:
    plan = build_gemini_json_first_corpus_plan_v1(
        [
            {
                "relative_path": "vietstock_bctc/SGB/2025/report.pdf",
                "source_sha256": "2" * 64,
                "source_size_bytes": 100,
                "page_count": 4,
            }
        ],
        openrouter_page_fraction="1.0",
    )
    ledger = tmp_path / "ledger.sqlite3"
    target.initialize_gemini_json_first_corpus_ledger_v1(ledger, plan=plan, max_task_attempts=3)
    task = target.list_corpus_tasks_v1(ledger)[0]
    task = target.transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="PENDING",
        next_state="RUNNING",
        receipt={"document_run_started": True},
    )
    frontiers = {"balanced": [], "default": [2], "items": [3], "scope": []}
    result = target._record_openrouter_subprocess_failure_v1(
        error=target._ProviderSubprocessError(
            returncode=-9,
            stdout="partial stdout",
            stderr="child traceback",
        ),
        task=task,
        ledger=ledger,
        max_attempts=3,
        retry_prompt_frontiers=frontiers,
    )

    receipt = json.loads(result["last_receipt_json"])
    assert result["state"] == "NEEDS_RETRY"
    assert receipt["retry_prompt_frontiers"] == frontiers
    assert target._retry_prompt_frontiers_v1(result) == frontiers


def test_repeated_item_semantic_failure_promotes_once_to_balanced() -> None:
    frontiers = {"default": [], "items": [2], "scope": []}
    prior = {
        "adaptive_retry_results": [
            {
                "physical_pages": [2],
                "prompt_variant": "items",
                "result": {"semantic_failed_pages": [2]},
            }
        ]
    }

    assert target._promote_repeated_item_semantic_pages_v1(frontiers, prior=prior) == {
        "balanced": [2],
        "default": [],
        "items": [],
        "scope": [],
    }

    exhausted = {
        "adaptive_retry_results": [
            {
                "physical_pages": [2],
                "prompt_variant": "balanced",
                "result": {"semantic_failed_pages": [2]},
            }
        ]
    }
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="balanced semantic retry is exhausted",
    ):
        target._promote_repeated_item_semantic_pages_v1(frontiers, prior=exhausted)


def test_requeue_command_requires_matching_plan_and_preserves_attempt_count(
    tmp_path,
) -> None:
    plan = build_gemini_json_first_corpus_plan_v1(
        [
            {
                "relative_path": "vietstock_bctc/ABB/2025/report.pdf",
                "source_sha256": "3" * 64,
                "source_size_bytes": 100,
                "page_count": 2,
            }
        ],
        openrouter_page_fraction="1.0",
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_bytes(canonical_json_bytes_v1(plan))
    ledger = tmp_path / "ledger.sqlite3"
    target.initialize_gemini_json_first_corpus_ledger_v1(ledger, plan=plan, max_task_attempts=3)
    task = target.list_corpus_tasks_v1(ledger)[0]
    running = target.transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="PENDING",
        next_state="RUNNING",
        receipt={"started": True},
    )
    target.transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state="FAILED",
        receipt={
            "failed_pages": [1],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        },
    )
    result = target.requeue_openrouter_task(
        Namespace(ledger=ledger, plan=plan_path, task_id=task["task_id"])
    )
    assert result["disposition"] == "NEEDS_RETRY"
    assert result["task"]["attempt_count"] == running["attempt_count"]
    assert result["task"]["state"] == "NEEDS_RETRY"


def test_source_binding_and_subprocess_json_receipt_are_fail_closed(tmp_path) -> None:
    root = tmp_path / "root"
    source = root / "MBB" / "a.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf-source")
    task = {
        "relative_path": "MBB/a.pdf",
        "source_sha256": hashlib.sha256(b"pdf-source").hexdigest(),
        "source_size_bytes": len(b"pdf-source"),
    }
    assert target._source(task, root) == source
    source.write_bytes(b"drifted")
    with pytest.raises(target.RunGeminiJsonFirstCorpusSupervisorV1Error, match="size drifted"):
        target._source(task, root)
    assert target._last_json('noise\n{"ok":true}\n') == {"ok": True}
    with pytest.raises(target.RunGeminiJsonFirstCorpusSupervisorV1Error, match="no JSON receipt"):
        target._last_json("noise only")


def test_google_key_slots_are_unique_and_task_stable() -> None:
    assert target._google_slots_v1(Namespace(google_key_slot=None, google_key_slots="1,2")) == [
        1,
        2,
    ]
    task_id = "gjfptaskv1:" + "f" * 64
    selected = target._google_slot_for_task_v1(task_id, [1, 2])
    assert selected in {1, 2}
    assert target._google_slot_for_task_v1(task_id, [1, 2]) == selected
    with pytest.raises(target.RunGeminiJsonFirstCorpusSupervisorV1Error):
        target._google_slots_v1(Namespace(google_key_slot=None, google_key_slots="1,1"))


def test_google_poll_is_nonblocking_while_batch_remains_active(monkeypatch, tmp_path) -> None:
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 1,
        "provider_job_ref": "batches/active",
        "state": "SUBMITTED",
        "task_id": "task-1",
    }
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "state": kwargs["next_state"]}

    def command(argv, *, expected):
        assert "poll" in argv
        assert "watch" not in argv
        assert expected == {0, 2}
        return 0, {"state": "BATCH_STATE_RUNNING"}

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "batch_progress_v1",
        lambda _database: [
            {
                "batch_name": "batches/active",
                "failed_pages": 0,
                "ingested_pages": 0,
                "request_count": 30,
                "state": "BATCH_STATE_RUNNING",
            }
        ],
    )
    result = target._poll_google(
        task=task,
        ledger=tmp_path / "ledger.sqlite3",
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        google_key_file=tmp_path / "keys",
        provider_timeout_seconds=60,
        max_attempts=3,
    )
    assert result["state"] == "RUNNING"
    assert [item["next_state"] for item in transitions] == ["RUNNING"]


def test_google_poll_transitions_only_after_terminal_ingestion(monkeypatch, tmp_path) -> None:
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 1,
        "provider_job_ref": "batches/done",
        "state": "RUNNING",
        "task_id": "task-1",
    }
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "state": kwargs["next_state"]}

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(target, "_command", lambda _argv, *, expected: (0, {}))
    monkeypatch.setattr(
        target,
        "batch_progress_v1",
        lambda _database: [
            {
                "batch_name": "batches/done",
                "failed_pages": 0,
                "ingested_pages": 30,
                "request_count": 30,
                "state": "BATCH_STATE_SUCCEEDED",
            }
        ],
    )
    result = target._poll_google(
        task=task,
        ledger=tmp_path / "ledger.sqlite3",
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        google_key_file=tmp_path / "keys",
        provider_timeout_seconds=60,
        max_attempts=3,
    )
    assert result["state"] == "SUCCEEDED"
    assert transitions[0]["expected_state"] == "RUNNING"
    assert transitions[0]["next_state"] == "SUCCEEDED"


@pytest.mark.parametrize(
    "poll_state",
    [
        "RUNNING",
        "SUCCEEDED",
    ],
)
def test_scheduler_progresses_google_and_openrouter_concurrently(
    monkeypatch, tmp_path, poll_state
) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    ledger.touch()
    phase = {"complete": False}
    calls = []
    google_task = {
        "route": target.GOOGLE_ROUTE,
        "state": "RUNNING",
        "task_id": "gjfptaskv1:" + "1" * 64,
    }
    openrouter_task = {
        "route": target.OPENROUTER_ROUTE,
        "state": "PENDING",
        "task_id": "gjfptaskv1:" + "2" * 64,
    }

    def tasks(_ledger):
        if phase["complete"]:
            return [
                {**google_task, "state": "SUCCEEDED"},
                {**openrouter_task, "state": "SUCCEEDED"},
            ]
        return [google_task, openrouter_task]

    def poll_google(**_kwargs):
        calls.append("poll-google")
        if poll_state == "SUCCEEDED":
            phase["complete"] = True
        return {**google_task, "state": poll_state}

    def run_openrouter(**_kwargs):
        assert _kwargs["openrouter_workers"] == 20
        calls.append("run-openrouter")
        phase["complete"] = True
        return {**openrouter_task, "state": "SUCCEEDED"}

    monkeypatch.setattr(
        target,
        "_plan",
        lambda _path: {"corpus_plan_id": "plan-1", "policy": {}},
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1", "max_task_attempts": 3},
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", tasks)
    monkeypatch.setattr(target, "_poll_google", poll_google)
    monkeypatch.setattr(target, "_run_openrouter", run_openrouter)
    monkeypatch.setattr(target, "_finalize_google_manifests", lambda **_kwargs: [])
    monkeypatch.setattr(target, "usage_summary_v1", lambda _database: {})

    result = target.run_corpus(
        Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            google_key_file=tmp_path / "google-keys",
            google_key_slot=1,
            google_poll_interval_seconds=0,
            google_watch_max_seconds=60,
            ledger=ledger,
            max_active_google=1,
            max_fallback_attempts=2,
            openrouter_key_file=tmp_path / "openrouter-key",
            openrouter_workers=20,
            plan=tmp_path / "plan.json",
            provider_timeout_seconds=60,
            source_root=tmp_path / "source",
        )
    )
    assert result["disposition"] == "SUCCEEDED"
    assert sorted(calls) == ["poll-google", "run-openrouter"]


def test_openrouter_circuit_trip_is_read_from_nested_child_receipt() -> None:
    assert target._openrouter_task_result_has_circuit_trip_v1(
        {
            "last_receipt_json": target.canonical_json_bytes_v1(
                {
                    "adaptive_retry_results": [
                        {
                            "result": {
                                "provider_circuit_breaker_trigger_page": 17,
                            }
                        }
                    ]
                }
            )
        }
    )
    assert not target._openrouter_task_result_has_circuit_trip_v1(
        {
            "last_receipt_json": target.canonical_json_bytes_v1(
                {"provider_circuit_breaker_trigger_page": None}
            )
        }
    )
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="trigger page is invalid",
    ):
        target._openrouter_task_result_has_circuit_trip_v1(
            {
                "last_receipt_json": target.canonical_json_bytes_v1(
                    {"provider_circuit_breaker_trigger_page": "17"}
                )
            }
        )


def test_openrouter_schedule_prioritizes_paid_semantic_replay_before_provider_work() -> None:
    base = {
        "first_physical_page": 1,
        "last_physical_page": 1,
        "relative_path": "bank/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "task_id": "task-1",
    }
    pending = {**base, "state": "PENDING"}
    provider_retry = {
        **base,
        "state": "NEEDS_RETRY",
        "last_receipt_json": target.canonical_json_bytes_v1(
            {"failed_pages": [1], "semantic_failed_pages": []}
        ),
    }
    semantic_retry = {
        **base,
        "state": "NEEDS_RETRY",
        "last_receipt_json": target.canonical_json_bytes_v1(
            {"failed_pages": [1], "semantic_failed_pages": [1]}
        ),
    }
    running = {**base, "state": "RUNNING"}

    ordered = sorted(
        [pending, provider_retry, semantic_retry, running],
        key=target._openrouter_schedule_key_v1,
    )
    assert [task["state"] for task in ordered] == [
        "RUNNING",
        "NEEDS_RETRY",
        "NEEDS_RETRY",
        "PENDING",
    ]
    assert ordered[1] is semantic_retry
    assert ordered[2] is provider_retry


def test_openrouter_circuit_cooldown_grows_exponentially_and_caps_at_one_hour() -> None:
    assert [
        target._openrouter_circuit_cooldown_v1(base_seconds=300, consecutive_trips=count)
        for count in range(1, 6)
    ] == [300.0, 600.0, 1200.0, 2400.0, 3600.0]
    assert target._openrouter_circuit_cooldown_v1(base_seconds=300, consecutive_trips=100) == 3600.0
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="cooldown inputs are invalid",
    ):
        target._openrouter_circuit_cooldown_v1(base_seconds=300, consecutive_trips=0)


def test_scheduler_waits_after_openrouter_circuit_trip(monkeypatch, tmp_path) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    ledger.touch()
    clock = [0.0]
    phase = [0]
    calls = []
    first = {
        "route": target.OPENROUTER_ROUTE,
        "state": "PENDING",
        "task_id": "gjfptaskv1:" + "5" * 64,
    }
    second = {
        "route": target.OPENROUTER_ROUTE,
        "state": "PENDING",
        "task_id": "gjfptaskv1:" + "6" * 64,
    }

    def tasks(_ledger):
        return [
            {**first, "state": "SUCCEEDED" if phase[0] >= 1 else "PENDING"},
            {**second, "state": "SUCCEEDED" if phase[0] >= 2 else "PENDING"},
        ]

    def run_openrouter(**kwargs):
        calls.append((kwargs["task"]["task_id"], clock[0]))
        if kwargs["task"]["task_id"] == first["task_id"]:
            phase[0] = 1
            receipt = {"provider_circuit_breaker_trigger_page": 1}
        else:
            phase[0] = 2
            receipt = {"provider_circuit_breaker_trigger_page": None}
        return {
            **kwargs["task"],
            "last_receipt_json": target.canonical_json_bytes_v1(receipt),
            "state": "SUCCEEDED",
        }

    def sleep(seconds):
        clock[0] += seconds
        threading.Event().wait(0.001)

    monkeypatch.setattr(target.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(target.time, "sleep", sleep)
    monkeypatch.setattr(target, "_plan", lambda _path: {"corpus_plan_id": "plan-1", "policy": {}})
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1", "max_task_attempts": 3},
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", tasks)
    monkeypatch.setattr(target, "_run_openrouter", run_openrouter)
    monkeypatch.setattr(target, "_finalize_google_manifests", lambda **_kwargs: [])
    monkeypatch.setattr(target, "usage_summary_v1", lambda _database: {})

    result = target.run_corpus(
        Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            google_key_file=tmp_path / "google-keys",
            google_key_slot=1,
            google_poll_interval_seconds=0,
            google_watch_max_seconds=60,
            ledger=ledger,
            max_active_google=1,
            max_fallback_attempts=2,
            openrouter_circuit_cooldown_seconds=10,
            openrouter_key_file=tmp_path / "openrouter-key",
            openrouter_workers=1,
            plan=tmp_path / "plan.json",
            provider_timeout_seconds=60,
            source_root=tmp_path / "source",
        )
    )

    assert result["disposition"] == "SUCCEEDED"
    assert calls[0] == (first["task_id"], 0.0)
    assert calls[1] == (second["task_id"], 10.0)


def test_scheduler_throttles_google_polling_while_batch_remains_active(
    monkeypatch, tmp_path
) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    ledger.touch()
    clock = [0.0]
    complete = [False]
    poll_times = []
    task = {
        "route": target.GOOGLE_ROUTE,
        "state": "RUNNING",
        "task_id": "gjfptaskv1:" + "3" * 64,
    }

    def tasks(_ledger):
        return [{**task, "state": "SUCCEEDED" if complete[0] else "RUNNING"}]

    def poll_google(**_kwargs):
        poll_times.append(clock[0])
        if len(poll_times) == 2:
            complete[0] = True
            return {**task, "state": "SUCCEEDED"}
        return task

    monkeypatch.setattr(target.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        target.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    )
    monkeypatch.setattr(target, "_plan", lambda _path: {"corpus_plan_id": "plan-1", "policy": {}})
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1", "max_task_attempts": 3},
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", tasks)
    monkeypatch.setattr(target, "_poll_google", poll_google)
    monkeypatch.setattr(target, "_finalize_google_manifests", lambda **_kwargs: [])
    monkeypatch.setattr(target, "usage_summary_v1", lambda _database: {})

    result = target.run_corpus(
        Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            google_key_file=tmp_path / "google-keys",
            google_key_slot=1,
            google_poll_interval_seconds=15,
            google_watch_max_seconds=60,
            ledger=ledger,
            max_active_google=1,
            max_fallback_attempts=2,
            openrouter_key_file=tmp_path / "openrouter-key",
            openrouter_workers=20,
            plan=tmp_path / "plan.json",
            provider_timeout_seconds=60,
            source_root=tmp_path / "source",
        )
    )
    assert result["disposition"] == "SUCCEEDED"
    assert poll_times == [0.0, 15.0]


def test_scheduler_waits_for_externally_accelerated_google_document(monkeypatch, tmp_path) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    ledger.touch()
    clock = [0.0]
    calls = [0]
    task = {
        "provider_job_ref": "gjfpaccelv1:claim:" + "a" * 64,
        "route": target.GOOGLE_ROUTE,
        "state": "RUNNING",
        "task_id": "gjfptaskv1:" + "4" * 64,
    }

    def tasks(_ledger):
        calls[0] += 1
        return [{**task, "state": "SUCCEEDED"}] if calls[0] > 1 else [task]

    monkeypatch.setattr(target.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        target.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    )
    monkeypatch.setattr(target, "_plan", lambda _path: {"corpus_plan_id": "plan-1", "policy": {}})
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1", "max_task_attempts": 3},
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", tasks)
    monkeypatch.setattr(target, "_finalize_google_manifests", lambda **_kwargs: [])
    monkeypatch.setattr(target, "usage_summary_v1", lambda _database: {})

    result = target.run_corpus(
        Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            google_key_file=tmp_path / "google-keys",
            google_key_slot=1,
            google_poll_interval_seconds=15,
            google_watch_max_seconds=60,
            ledger=ledger,
            max_active_google=1,
            max_fallback_attempts=2,
            openrouter_key_file=tmp_path / "openrouter-key",
            openrouter_workers=20,
            plan=tmp_path / "plan.json",
            provider_timeout_seconds=60,
            source_root=tmp_path / "source",
        )
    )
    assert result["disposition"] == "SUCCEEDED"
    assert clock == [1.0]


def test_scheduler_quarantines_failed_document_until_other_work_finishes(
    monkeypatch, tmp_path
) -> None:
    ledger = tmp_path / "ledger.sqlite3"
    ledger.touch()
    phase = {"complete": False}
    failed_task = {
        "route": target.OPENROUTER_ROUTE,
        "state": "FAILED",
        "task_id": "gjfptaskv1:" + "1" * 64,
    }
    pending_task = {
        "route": target.OPENROUTER_ROUTE,
        "state": "PENDING",
        "task_id": "gjfptaskv1:" + "2" * 64,
    }
    calls = []

    def tasks(_ledger):
        state = "SUCCEEDED" if phase["complete"] else "PENDING"
        return [failed_task, {**pending_task, "state": state}]

    def run_openrouter(**_kwargs):
        calls.append(_kwargs["task"]["task_id"])
        phase["complete"] = True
        return {**pending_task, "state": "SUCCEEDED"}

    monkeypatch.setattr(
        target,
        "_plan",
        lambda _path: {"corpus_plan_id": "plan-1", "policy": {}},
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1", "max_task_attempts": 2},
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", tasks)
    monkeypatch.setattr(target, "_run_openrouter", run_openrouter)

    result = target.run_corpus(
        Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            google_key_file=tmp_path / "google-keys",
            google_key_slot=1,
            google_poll_interval_seconds=0,
            google_watch_max_seconds=60,
            ledger=ledger,
            max_active_google=1,
            max_fallback_attempts=2,
            openrouter_key_file=tmp_path / "openrouter-key",
            openrouter_workers=25,
            plan=tmp_path / "plan.json",
            provider_timeout_seconds=60,
            source_root=tmp_path / "source",
        )
    )
    assert result["disposition"] == "FAILED"
    assert calls == [pending_task["task_id"]]


def test_google_retry_exhaustion_moves_to_typed_fallback(monkeypatch, tmp_path) -> None:
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 2,
        "last_receipt_json": None,
        "provider_job_ref": "batches/done",
        "state": "RUNNING",
        "task_id": "task-1",
    }
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "state": kwargs["next_state"]}

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)

    def command(_argv, *, expected):
        assert expected == {0, 2}
        return 2, {"disposition": "NEEDS_RETRY"}

    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "batch_progress_v1",
        lambda _database: [
            {
                "batch_name": "batches/done",
                "failed_pages": 1,
                "ingested_pages": 0,
                "request_count": 1,
                "state": "BATCH_STATE_SUCCEEDED",
            }
        ],
    )
    result = target._poll_google(
        task=task,
        ledger=tmp_path / "ledger.sqlite3",
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        google_key_file=tmp_path / "keys",
        provider_timeout_seconds=60,
        max_attempts=2,
    )
    assert result["state"] == "FALLBACK_PENDING"
    assert transitions[0]["next_state"] == "FALLBACK_PENDING"


def test_google_fallback_calls_openrouter_only_for_failed_pages(monkeypatch, tmp_path) -> None:
    source_root = tmp_path / "source"
    source = source_root / "MBB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 2,
        "last_receipt_json": None,
        "provider_job_ref": "batches/done",
        "relative_path": "MBB/report.pdf",
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "FALLBACK_PENDING",
        "task_id": "task-1",
    }
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "state": kwargs["next_state"]}

    def command(argv, *, expected):
        assert expected == {0, 2}
        assert "--physical-page" in argv
        assert argv.count("--physical-page") == 2
        assert "7" in argv and "9" in argv
        assert argv[argv.index("--google-key-file") + 1] == str(tmp_path / "google")
        assert argv[argv.index("--google-key-slot") + 1] == "2"
        assert argv[argv.index("--google-standard-mode") + 1] == "on-provider-error"
        assert argv[argv.index("--openrouter-route-policy") + 1] == "flex-only"
        return 0, {"disposition": "SUCCEEDED"}

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    monkeypatch.setattr(
        target,
        "batch_failed_page_requests_v1",
        lambda _database, *, batch_name: [
            {"error": {"provider_error": {}}, "physical_page": 7, "request_id": "p7"},
            {"error": {"provider_error": {}}, "physical_page": 9, "request_id": "p9"},
        ],
    )
    result = target._run_google_fallback(
        task=task,
        plan={"policy": {"dpi": 300, "openrouter_workers": 5}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        google_key_file=tmp_path / "google",
        google_key_slot=2,
        openrouter_workers=20,
        provider_timeout_seconds=60,
        max_fallback_attempts=2,
    )
    assert result["state"] == "SUCCEEDED"
    assert [item["next_state"] for item in transitions] == [
        "FALLBACK_RUNNING",
        "SUCCEEDED",
    ]


def test_openrouter_task_can_forbid_direct_google_fallback(monkeypatch, tmp_path) -> None:
    source_root = tmp_path / "source"
    source = source_root / "MBB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 0,
        "last_receipt_json": None,
        "relative_path": "MBB/report.pdf",
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "PENDING",
        "task_id": "task-1",
    }
    commands = []

    def command(argv, *, expected):
        commands.append(argv)
        assert expected == {0, 2}
        return 2, {
            "disposition": "NEEDS_RETRY",
            "recitation_failed_pages": [],
            "semantic_failed_pages": [1],
        }

    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "transition_corpus_task_v1",
        lambda _ledger, **kwargs: {**task, "state": kwargs["next_state"]},
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {1: "1" * 64},
    )
    monkeypatch.setattr(
        target,
        "build_financial_document_manifest_v1",
        lambda *_args, **_kwargs: {
            "document_manifest_id": "gfdmv1:manifest:" + "d" * 64,
            "pages": [{"physical_page": 1, "status": "UNRESOLVED_PAGE"}],
        },
    )

    target._run_openrouter(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=1,
        google_key_file=tmp_path / "google",
        google_key_slot=1,
        provider_timeout_seconds=60,
        max_attempts=1,
        openrouter_only=True,
    )

    assert commands
    assert all(
        command[command.index("--google-standard-mode") + 1] == "disabled" for command in commands
    )
    assert all(
        command[command.index("--openrouter-route-policy") + 1] == "flex-only"
        for command in commands
    )
    assert all("--stop-provider-frontier-on-transient-error" in command for command in commands)


def test_interrupted_google_file_uploads_are_preserved_before_clean_resubmission(
    tmp_path,
) -> None:
    attempt = tmp_path / "task" / "google-attempt-0001"
    uploaded = attempt / "uploaded-files"
    uploaded.mkdir(parents=True)
    for page in (1, 2):
        (uploaded / f"request-{page}.json").write_text(
            json.dumps({"file": {"name": f"files/{page}"}}), encoding="utf-8"
        )
    quarantine = target._quarantine_pre_submission_google_uploads_v1(attempt)
    assert not attempt.exists()
    assert [path.name for path in sorted((quarantine / "uploaded-files").glob("*.json"))] == [
        "request-1.json",
        "request-2.json",
    ]
    receipt = json.loads((quarantine / "quarantine-receipt.json").read_bytes())
    assert receipt["disposition"] == "QUARANTINED_PRE_SUBMISSION_UPLOADS"
    assert len(receipt["uploaded_files"]) == 2

    unsafe = tmp_path / "unsafe" / "google-attempt-0001"
    (unsafe / "uploaded-files").mkdir(parents=True)
    (unsafe / "uploaded-files" / "request.json").write_text(
        json.dumps({"file": {"name": "files/unsafe"}}), encoding="utf-8"
    )
    (unsafe / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(target.RunGeminiJsonFirstCorpusSupervisorV1Error, match="safe pre"):
        target._quarantine_pre_submission_google_uploads_v1(unsafe)
    assert unsafe.is_dir()


def test_google_upload_start_429_is_deferred_without_advancing_the_ledger(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "HDB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task_id = "gjfptaskv1:" + "1" * 64
    task = {
        "artifact_relative_path": "tasks/one",
        "attempt_count": 0,
        "first_physical_page": 1,
        "last_physical_page": 1,
        "relative_path": "HDB/report.pdf",
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "PENDING",
        "task_id": task_id,
    }
    plan = {
        "documents": [
            {
                "document": {"page_count": 1},
                "tasks": [{"task_id": task_id}],
            }
        ],
        "policy": {"dpi": 300},
    }
    monkeypatch.setattr(target, "_google_success_pages", lambda *_args: set())
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )

    def command(_argv, *, expected):
        assert expected == {0}
        raise target._ProviderSubprocessError(
            returncode=1,
            stdout="",
            stderr=(
                "bctc_ai.evaluation.gemini_json_first_batch_v1."
                "GeminiJsonFirstBatchV1Error: Google file upload start returned HTTP 429\n"
            ),
        )

    monkeypatch.setattr(target, "_command", command)
    result = target._recover_or_submit_google(
        task=task,
        plan=plan,
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        google_key_file=tmp_path / "keys",
        google_key_slot=2,
        provider_timeout_seconds=60,
    )
    assert result["disposition"] == target.RETRYABLE_GOOGLE_UPLOAD_DISPOSITION
    assert result["state"] == "PENDING"
    receipts = list((tmp_path / "artifacts/tasks/one/google-submit-deferrals").glob("*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_bytes())
    assert receipt["provider_failure_kind"] == "GOOGLE_FILE_UPLOAD_START_TRANSIENT"

    nonretryable = target._ProviderSubprocessError(
        returncode=1,
        stdout="",
        stderr="GeminiJsonFirstBatchV1Error: Google file upload start returned HTTP 400\n",
    )
    assert not target._retryable_google_upload_start_failure_v1(nonretryable)


def test_google_submit_throttle_is_global_and_has_no_hidden_queue() -> None:
    assert target._google_submit_capacity_v1(active_count=0, future_count=0, max_active=12) == 1
    assert target._google_submit_capacity_v1(active_count=0, future_count=1, max_active=12) == 0
    assert target._google_submit_capacity_v1(active_count=12, future_count=0, max_active=12) == 0
    assert not target._google_submit_ready_v1(
        task_id="other-task",
        now=10.0,
        global_not_before=20.0,
        task_not_before={},
    )
    assert target._google_submit_ready_v1(
        task_id="other-task",
        now=20.0,
        global_not_before=20.0,
        task_not_before={},
    )


def test_google_fallback_selects_scope_and_items_from_typed_batch_failures(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "CTG" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-typed",
        "attempt_count": 2,
        "last_receipt_json": None,
        "provider_job_ref": "batches/typed",
        "relative_path": "CTG/report.pdf",
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "FALLBACK_PENDING",
        "task_id": "task-typed",
    }
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "state": kwargs["next_state"]}

    calls = []

    def command(argv, *, expected):
        assert expected == {0, 2}
        variant = argv[argv.index("--prompt-variant") + 1]
        pages = [
            int(argv[index + 1]) for index, value in enumerate(argv) if value == "--physical-page"
        ]
        calls.append((variant, pages, Path(argv[argv.index("--artifact-dir") + 1])))
        return 0, {"disposition": "SUCCEEDED", "physical_pages": pages}

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target, "corpus_ledger_summary_v1", lambda _ledger: {"prompt_variant": "simple"}
    )
    monkeypatch.setattr(
        target,
        "batch_failed_page_requests_v1",
        lambda _database, *, batch_name: [
            {
                "error": {"provider_error": {"finish_reason": "RECITATION"}},
                "physical_page": 7,
                "request_id": "p7",
            },
            {
                "error": {"error_type": "GeminiFinancialPageJsonV1Error"},
                "physical_page": 9,
                "request_id": "p9",
            },
        ],
    )
    result = target._run_google_fallback(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        google_key_file=tmp_path / "google",
        google_key_slot=2,
        openrouter_workers=20,
        provider_timeout_seconds=60,
        max_fallback_attempts=2,
    )
    assert result["state"] == "SUCCEEDED"
    assert [(variant, pages) for variant, pages, _path in calls] == [
        ("scope", [7]),
        ("items", [9]),
    ]
    assert all("attempt-01" in path.parts for _variant, _pages, path in calls)
    assert [item["prompt_variant"] for item in transitions[-1]["receipt"]["fallback_results"]] == [
        "scope",
        "items",
    ]


def test_google_fallback_uses_balanced_after_one_persistent_item_semantic_failure(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "VCB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-balanced",
        "attempt_count": 2,
        "last_receipt_json": canonical_json_bytes_v1(
            {
                "fallback_attempt": 1,
                "fallback_results": [
                    {
                        "physical_pages": [9],
                        "prompt_variant": "items",
                        "result": {
                            "failed_pages": [9],
                            "semantic_failed_pages": [9],
                        },
                    }
                ],
            }
        ),
        "provider_job_ref": "batches/typed",
        "relative_path": "VCB/report.pdf",
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "FALLBACK_PENDING",
        "task_id": "task-balanced",
    }
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "state": kwargs["next_state"]}

    calls = []

    def command(argv, *, expected):
        calls.append(
            (
                argv[argv.index("--prompt-variant") + 1],
                Path(argv[argv.index("--artifact-dir") + 1]),
            )
        )
        return 0, {"disposition": "SUCCEEDED", "physical_pages": [9]}

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target, "corpus_ledger_summary_v1", lambda _ledger: {"prompt_variant": "simple"}
    )
    monkeypatch.setattr(
        target,
        "batch_failed_page_requests_v1",
        lambda _database, *, batch_name: [
            {
                "error": {"error_type": "GeminiFinancialPageJsonV1Error"},
                "physical_page": 9,
                "request_id": "p9",
            }
        ],
    )
    result = target._run_google_fallback(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        google_key_file=tmp_path / "google",
        google_key_slot=2,
        openrouter_workers=20,
        provider_timeout_seconds=60,
        max_fallback_attempts=2,
    )
    assert result["state"] == "SUCCEEDED"
    assert calls[0][0] == "balanced"
    assert "attempt-02" in calls[0][1].parts


def test_google_repair_excludes_semantic_pages_replayed_into_cache(monkeypatch, tmp_path) -> None:
    source_root = tmp_path / "source"
    source = source_root / "BID" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 1,
        "first_physical_page": 1,
        "last_physical_page": 66,
        "last_receipt_json": json.dumps(
            {
                "failed_pages": [27, 53, 62],
                "semantic_failed_pages": [53],
            }
        ),
        "relative_path": "BID/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "FAILED",
        "task_id": "task-1",
    }
    sealed = []

    monkeypatch.setattr(
        target,
        "_plan",
        lambda _path: {"policy": {"dpi": 300, "openrouter_workers": 25}},
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda *_args, **_kwargs: [task])
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )

    def command(argv, *, expected):
        assert expected == {0}
        assert "for-missing" in argv
        return 0, {
            "cached_pages": [1, 53],
            "disposition": "SUCCEEDED",
            "failed_pages": [],
            "ingested_pages": [27, 62],
            "manifest_id": "gfdmv1:manifest:" + "a" * 64,
            "offline_missing_pages": [],
            "semantic_failed_pages": [],
        }

    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "seal_google_fallback_corpus_task_v1",
        lambda _ledger, **kwargs: sealed.append(kwargs) or task,
    )
    args = Namespace(
        artifact_root=tmp_path / "artifacts",
        database=tmp_path / "store.sqlite3",
        google_key_file=tmp_path / "google",
        google_key_slot=2,
        ledger=tmp_path / "ledger.sqlite3",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=25,
        plan=tmp_path / "plan.json",
        provider_timeout_seconds=900,
        source_root=source_root,
        task_id="task-1",
    )
    result = target.repair_openrouter_google_task(args)
    assert result["fallback_pages"] == [27, 62]
    assert sealed[0]["receipt"]["fallback_pages"] == [27, 62]

    monkeypatch.setattr(
        target,
        "_command",
        lambda *_args, **_kwargs: (
            0,
            {
                "cached_pages": [1],
                "disposition": "SUCCEEDED",
                "failed_pages": [],
                "ingested_pages": [27, 53, 62],
                "manifest_id": "gfdmv1:manifest:" + "b" * 64,
                "offline_missing_pages": [],
                "semantic_failed_pages": [],
            },
        ),
    )
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="preserve replayed semantic pages",
    ):
        target.repair_openrouter_google_task(args)


def test_exhausted_page_repair_uses_only_openrouter_and_exact_failed_pages(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "ABB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    prior = {
        "failed_pages": [1, 3],
        "recitation_failed_pages": [],
        "semantic_failed_pages": [3],
        "unresolved_pages": [],
    }
    task = {
        "artifact_relative_path": "tasks/task-1",
        "attempt_count": 3,
        "document_page_count": 3,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "last_receipt_json": canonical_json_bytes_v1(prior),
        "relative_path": "ABB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "FAILED",
        "task_id": "task-1",
    }
    calls = []
    sealed = []
    monkeypatch.setattr(
        target,
        "_plan",
        lambda _path: {"corpus_plan_id": "plan-1", "policy": {"dpi": 300}},
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1", "prompt_variant": "simple"},
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda *_args, **_kwargs: [task])
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {page: str(page) * 64 for page in (1, 2, 3)},
    )
    monkeypatch.setattr(
        target,
        "_successful_historical_prompt_context_v1",
        lambda **_kwargs: ({}, []),
    )

    def command(argv, *, expected):
        assert expected == {0, 2}
        assert argv[argv.index("--google-standard-mode") + 1] == "disabled"
        variant = argv[argv.index("--prompt-variant") + 1]
        pages = [
            int(argv[index + 1]) for index, value in enumerate(argv) if value == "--physical-page"
        ]
        offline = "--offline-replay-only" in argv
        calls.append(("OFFLINE" if offline else variant, pages))
        if offline:
            assert "--openrouter-route-policy" not in argv
            assert pages == [3]
            assert argv[argv.index("--semantic-replay-source-dir") + 1].endswith(
                "/artifacts/tasks/task-1"
            )
        else:
            assert argv[argv.index("--openrouter-route-policy") + 1] == "flex-only"
            assert "--stop-provider-frontier-on-transient-error" in argv
        return 0, {
            "cached_pages": [],
            "disposition": "SUCCEEDED",
            "execution_mode": "OFFLINE_REPLAY_ONLY" if offline else "PROVIDER_OR_CACHE",
            "failed_pages": [],
            "ingested_pages": pages,
            "offline_missing_pages": [],
            "page_image_sha256s": [
                {"image_sha256": str(page) * 64, "physical_page": page} for page in pages
            ],
            "provider_request_pages": [] if offline else pages,
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "semantic_replay_sources": (
                [
                    {
                        "physical_page": 3,
                        "source_relative_path": ("page-00003/attempt-0001/raw-response.json"),
                    }
                ]
                if offline
                else []
            ),
            "unresolved_pages": [],
        }

    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "_page_variant_manifest_v1",
        lambda **_kwargs: {
            "document_manifest_id": "gfdmv1:manifest:" + "a" * 64,
            "pages": [
                {"physical_page": page, "status": "FINANCIAL_NOTE_CONTENT"} for page in (1, 2, 3)
            ],
        },
    )
    monkeypatch.setattr(
        target,
        "seal_openrouter_exhausted_page_repair_corpus_task_v1",
        lambda _ledger, **kwargs: sealed.append(kwargs) or {**task, "state": "SUCCEEDED"},
    )
    result = target.repair_openrouter_flex_pages_task(
        Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            google_key_file=tmp_path / "unused-google-key",
            ledger=tmp_path / "ledger.sqlite3",
            openrouter_key_file=tmp_path / "openrouter-key",
            openrouter_workers=1,
            plan=tmp_path / "plan.json",
            provider_timeout_seconds=900,
            repair_attempt=1,
            source_root=source_root,
            task_id="task-1",
        )
    )
    assert result["disposition"] == "SUCCEEDED"
    assert calls == [("OFFLINE", [3]), ("simple", [1])]
    receipt = sealed[0]["receipt"]
    assert receipt["repair_gateway"] == "OPENROUTER"
    assert receipt["requested_service_tier"] == "flex"
    assert receipt["revalidated_pages"] == [1, 2, 3]
    assert [item["accepted_pages"] for item in receipt["provider_results"]] == [[1]]
    assert [item["accepted_pages"] for item in receipt["offline_replay_results"]] == [[3]]


def test_exhausted_page_repair_recovers_frontier_after_local_subprocess_failure(
    monkeypatch, tmp_path
) -> None:
    task = {
        "artifact_relative_path": "tasks/task-1",
        "attempt_count": 3,
        "document_page_count": 3,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "last_receipt_json": canonical_json_bytes_v1(
            {
                "disposition": "OPENROUTER_PROVIDER_SUBPROCESS_FAILURE",
                "provider_returncode": 1,
                "provider_stderr_bytes": 1,
                "provider_stderr_sha256": "a" * 64,
                "provider_stdout_bytes": 0,
                "provider_stdout_sha256": hashlib.sha256(b"").hexdigest(),
                "retry_allowed": False,
            }
        ),
        "relative_path": "EIB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": "b" * 64,
        "source_size_bytes": 3,
        "state": "FAILED",
        "task_id": "task-1",
    }
    frontier = {
        "failed_pages": [1, 3],
        "format_version": "GEMINI_JSON_FIRST_OPENROUTER_FAILED_REQUEUE_V1",
        "prior_failed_receipt_sha256": "c" * 64,
        "recitation_failed_pages": [],
        "requeue_authorized": True,
        "semantic_failed_pages": [3],
        "unresolved_pages": [],
    }
    monkeypatch.setattr(
        target,
        "openrouter_failed_task_repair_frontier_v1",
        lambda _ledger, *, task_id: frontier if task_id == "task-1" else None,
    )
    assert (
        target._terminal_repair_frontier_receipt_v1(
            task=task,
            ledger=tmp_path / "ledger.sqlite3",
        )
        == frontier
    )
    assert (
        target._exhausted_page_repair_remaining_page_count_v1(
            task=task,
            ledger=tmp_path / "ledger.sqlite3",
            artifact_root=tmp_path / "artifacts",
            repair_attempt=1,
        )
        == 2
    )


def test_exhausted_page_repair_defers_later_prompt_frontiers_after_circuit(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "ABB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    prior = {
        "failed_pages": [1, 3],
        "recitation_failed_pages": [],
        "semantic_failed_pages": [],
        "unresolved_pages": [3],
    }
    task = {
        "artifact_relative_path": "tasks/task-1",
        "attempt_count": 3,
        "document_page_count": 3,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "last_receipt_json": canonical_json_bytes_v1(prior),
        "relative_path": "ABB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "FAILED",
        "task_id": "task-1",
    }
    calls = []
    monkeypatch.setattr(
        target,
        "_plan",
        lambda _path: {"corpus_plan_id": "plan-1", "policy": {"dpi": 300}},
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1", "prompt_variant": "simple"},
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda *_args, **_kwargs: [task])
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {page: str(page) * 64 for page in (1, 2, 3)},
    )

    def command(argv, *, expected):
        assert expected == {0, 2}
        variant = argv[argv.index("--prompt-variant") + 1]
        pages = [
            int(argv[index + 1]) for index, value in enumerate(argv) if value == "--physical-page"
        ]
        offline = "--offline-replay-only" in argv
        calls.append((variant, pages, offline))
        assert "--stop-provider-frontier-on-transient-error" in argv
        if pages == [1]:
            assert not offline
            return_code = 2
            circuit_page = 1
            offline_missing_pages = []
            provider_request_pages = [1]
            unresolved_pages = []
            execution_mode = "PROVIDER_OR_CACHE"
        else:
            assert pages == [3]
            assert offline
            return_code = 2
            circuit_page = None
            offline_missing_pages = [3]
            provider_request_pages = []
            unresolved_pages = [3]
            execution_mode = "OFFLINE_REPLAY_ONLY"
        return return_code, {
            "cached_pages": [],
            "disposition": "NEEDS_RETRY",
            "execution_mode": execution_mode,
            "failed_pages": pages,
            "ingested_pages": [],
            "offline_missing_pages": offline_missing_pages,
            "page_image_sha256s": [
                {"image_sha256": str(page) * 64, "physical_page": page} for page in pages
            ],
            "provider_circuit_breaker_trigger_page": circuit_page,
            "provider_request_pages": provider_request_pages,
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "semantic_replay_sources": [],
            "unresolved_pages": unresolved_pages,
        }

    monkeypatch.setattr(target, "_command", command)
    result = target.repair_openrouter_flex_pages_task(
        Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            google_key_file=tmp_path / "unused-google-key",
            ledger=tmp_path / "ledger.sqlite3",
            openrouter_key_file=tmp_path / "openrouter-key",
            openrouter_workers=1,
            plan=tmp_path / "plan.json",
            provider_timeout_seconds=900,
            repair_attempt=1,
            source_root=source_root,
            task_id="task-1",
        )
    )
    assert result == {
        "disposition": "NEEDS_REPAIR",
        "failed_pages": [1, 3],
        "repair_attempt": 1,
        "task_id": "task-1",
    }
    assert calls == [("simple", [1], False), ("items", [3], True)]
    receipt = json.loads(
        (
            tmp_path
            / "artifacts/tasks/task-1/openrouter-exhausted-page-repair/receipts/attempt-01.json"
        ).read_text()
    )
    assert [item["physical_pages"] for item in receipt["provider_results"]] == [[1]]
    assert [item["physical_pages"] for item in receipt["offline_replay_results"]] == [[3]]


def test_terminal_flex_repair_runs_only_after_frontier_and_cools_after_circuit(
    monkeypatch, tmp_path
) -> None:
    tasks = [
        {
            "artifact_relative_path": f"tasks/task-{ordinal}",
            "first_physical_page": 1,
            "last_physical_page": ordinal + 2,
            "last_receipt_json": canonical_json_bytes_v1(
                {
                    "failed_pages": [1, 2] if ordinal == 1 else [1],
                    "recitation_failed_pages": [],
                    "semantic_failed_pages": [],
                    "unresolved_pages": [],
                }
            ),
            "relative_path": f"ABB/report-{ordinal}.pdf",
            "route": target.OPENROUTER_ROUTE,
            "state": "FAILED",
            "task_id": f"task-{ordinal}",
        }
        for ordinal in (1, 2)
    ]

    def listed(_ledger, *, states=None, route=None):
        return [
            dict(task)
            for task in tasks
            if (states is None or task["state"] in states)
            and (route is None or task["route"] == route)
        ]

    monkeypatch.setattr(target, "list_corpus_tasks_v1", listed)
    monkeypatch.setattr(target, "_plan", lambda _path: {"corpus_plan_id": "plan-1"})
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1"},
    )
    repair_calls = []

    def repair(args):
        repair_calls.append((args.task_id, args.repair_attempt))
        task = next(item for item in tasks if item["task_id"] == args.task_id)
        succeeded = args.task_id == "task-1" or args.repair_attempt == 2
        if succeeded:
            task["state"] = "SUCCEEDED"
        receipt = {
            "disposition": "SUCCEEDED" if succeeded else "NEEDS_REPAIR",
            "failed_pages": [] if succeeded else [1],
            "format_version": "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V2",
            "offline_missing_pages": [],
            "prior_failed_receipt_sha256": hashlib.sha256(task["last_receipt_json"]).hexdigest(),
            "provider_results": [
                {
                    "result": {
                        "provider_circuit_breaker_trigger_page": (
                            1 if args.task_id == "task-2" and args.repair_attempt == 1 else None
                        )
                    }
                }
            ],
            "recitation_failed_pages": [],
            "repair_attempt": args.repair_attempt,
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        }
        receipt_path = (
            args.artifact_root
            / task["artifact_relative_path"]
            / "openrouter-exhausted-page-repair"
            / "receipts"
            / f"attempt-{args.repair_attempt:02d}.json"
        )
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_bytes(canonical_json_bytes_v1(receipt))
        return {
            "disposition": "SUCCEEDED" if succeeded else "NEEDS_REPAIR",
            "failed_pages": [] if succeeded else [1],
            "repair_attempt": args.repair_attempt,
            "task_id": args.task_id,
        }

    monkeypatch.setattr(target, "repair_openrouter_flex_pages_task", repair)
    sleeps = []
    monkeypatch.setattr(target.time, "sleep", sleeps.append)
    result = target.repair_failed_openrouter_flex_tasks(
        Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            google_key_file=tmp_path / "unused-google-key",
            ledger=tmp_path / "ledger.sqlite3",
            max_repair_actions=4,
            openrouter_circuit_cooldown_seconds=5,
            openrouter_key_file=tmp_path / "openrouter-key",
            openrouter_workers=1,
            plan=tmp_path / "plan.json",
            provider_timeout_seconds=900,
            source_root=tmp_path / "source",
        )
    )
    assert result["disposition"] == "SUCCEEDED"
    assert result["completed_task_ids"] == ["task-1", "task-2"]
    assert result["repairable_task_ids"] == []
    assert result["exhausted_task_ids"] == []
    assert repair_calls == [("task-2", 1), ("task-2", 2), ("task-1", 1)]
    assert sleeps == [5.0]


def test_terminal_flex_repair_rejects_an_unfinished_ordinary_frontier(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(target, "_plan", lambda _path: {"corpus_plan_id": "plan-1"})
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1"},
    )
    monkeypatch.setattr(
        target,
        "list_corpus_tasks_v1",
        lambda *_args, **_kwargs: [{"state": "PENDING"}],
    )
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="ordinary corpus frontier",
    ):
        target.repair_failed_openrouter_flex_tasks(
            Namespace(
                artifact_root=tmp_path / "artifacts",
                database=tmp_path / "store.sqlite3",
                google_key_file=tmp_path / "unused-google-key",
                ledger=tmp_path / "ledger.sqlite3",
                max_repair_actions=1,
                openrouter_circuit_cooldown_seconds=5,
                openrouter_key_file=tmp_path / "openrouter-key",
                openrouter_workers=1,
                plan=tmp_path / "plan.json",
                provider_timeout_seconds=900,
                source_root=tmp_path / "source",
            )
        )


def test_terminal_flex_repair_rejects_a_foreign_provider_route(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(target, "_plan", lambda _path: {"corpus_plan_id": "plan-1"})
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1"},
    )
    monkeypatch.setattr(
        target,
        "list_corpus_tasks_v1",
        lambda *_args, **_kwargs: [{"route": "GOOGLE_GEMINI_BATCH_API", "state": "FAILED"}],
    )
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="OpenRouter-only",
    ):
        target.repair_failed_openrouter_flex_tasks(
            Namespace(
                artifact_root=tmp_path / "artifacts",
                database=tmp_path / "store.sqlite3",
                google_key_file=tmp_path / "unused-google-key",
                ledger=tmp_path / "ledger.sqlite3",
                max_repair_actions=1,
                openrouter_circuit_cooldown_seconds=5,
                openrouter_key_file=tmp_path / "openrouter-key",
                openrouter_workers=1,
                plan=tmp_path / "plan.json",
                provider_timeout_seconds=900,
                source_root=tmp_path / "source",
            )
        )


def test_failed_task_seals_from_complete_current_mixed_prompt_store(monkeypatch, tmp_path) -> None:
    artifact_root = tmp_path / "artifacts"
    task = {
        "artifact_relative_path": "tasks/task-1",
        "attempt_count": 3,
        "document_page_count": 3,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "relative_path": "BAB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": "1" * 64,
        "source_size_bytes": 100,
        "state": "FAILED",
        "task_id": "task-1",
    }
    captured = []
    sealed = []
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {1: "a" * 64, 2: "b" * 64, 3: "c" * 64},
    )
    monkeypatch.setattr(
        target,
        "_successful_historical_prompt_context_v1",
        lambda **_kwargs: ({}, [2]),
    )
    monkeypatch.setattr(
        target,
        "document_page_extraction_frontier_v1",
        lambda *_args, **_kwargs: {
            1: {"image_sha256": "a" * 64, "prompt_variant": "simple"},
            2: {"image_sha256": "b" * 64, "prompt_variant": "items"},
            3: {"image_sha256": "c" * 64, "prompt_variant": "simple"},
        },
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple", "documents": 1},
    )

    def manifest(**kwargs):
        captured.append(kwargs)
        return {
            "document_manifest_id": "gfdmv1:manifest:" + "d" * 64,
            "pages": [
                {"physical_page": 1, "status": "FINANCIAL_NOTE_CONTENT"},
                {"physical_page": 2, "status": "FINANCIAL_NOTE_CONTENT"},
                {"physical_page": 3, "status": "FINANCIAL_NOTE_CONTENT"},
            ],
        }

    monkeypatch.setattr(target, "_page_variant_manifest_v1", manifest)
    monkeypatch.setattr(
        target,
        "seal_offline_revalidated_corpus_task_v1",
        lambda _ledger, **kwargs: sealed.append(kwargs) or {**task, "state": "SUCCEEDED"},
    )

    result = target._seal_failed_task_from_current_store_v1(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=tmp_path / "source",
        database=tmp_path / "store.sqlite3",
        artifact_root=artifact_root,
    )

    assert result["disposition"] == "SUCCEEDED"
    assert result["result"]["provider_request_pages"] == []
    assert captured[0]["page_prompt_variants"] == {1: "simple", 2: "items", 3: "simple"}
    assert sealed[0]["receipt"]["replayed_pages"] == []
    assert sealed[0]["receipt"]["revalidated_pages"] == [1, 2, 3]
    assert (
        artifact_root / "tasks/task-1/offline-current-store-revalidation-v1/document-manifest.json"
    ).is_file()


def test_offline_repair_seals_one_fully_cached_document(monkeypatch, tmp_path) -> None:
    source_root = tmp_path / "source"
    source = source_root / "BID" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    artifact_root = tmp_path / "artifacts"
    task_root = artifact_root / "task-1"
    task_root.mkdir(parents=True)
    (task_root / "document-contract.json").write_text(
        json.dumps({"google_standard_mode": "on-provider-error"})
    )
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 1,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "relative_path": "BID/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "FAILED",
        "task_id": "task-1",
    }
    sealed = []
    monkeypatch.setattr(
        target,
        "_plan",
        lambda _path: {"policy": {"dpi": 300, "openrouter_workers": 25}},
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda *_args, **_kwargs: [task])
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    monkeypatch.setattr(
        target,
        "_seal_failed_task_from_current_store_v1",
        lambda **_kwargs: None,
    )
    provider_result = {
        "cached_pages": [1, 2, 3],
        "disposition": "SUCCEEDED",
        "failed_pages": [],
        "ingested_pages": [],
        "manifest_id": "gfdmv1:manifest:" + "c" * 64,
        "offline_missing_pages": [],
        "semantic_failed_pages": [],
    }

    def command(argv, **_kwargs):
        assert argv[argv.index("--openrouter-route-policy") + 1] == "flex-then-standard"
        assert argv[argv.index("--artifact-dir") + 1] == str(
            task_root / "offline-full-document-revalidation-v1"
        )
        assert "--offline-replay-only" in argv
        assert "--physical-page" not in argv
        return 0, provider_result

    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "seal_offline_revalidated_corpus_task_v1",
        lambda _ledger, **kwargs: sealed.append(kwargs) or {**task, "state": "SUCCEEDED"},
    )
    args = Namespace(
        artifact_root=artifact_root,
        database=tmp_path / "store.sqlite3",
        google_key_file=tmp_path / "google",
        google_key_slot=2,
        ledger=tmp_path / "ledger.sqlite3",
        plan=tmp_path / "plan.json",
        source_root=source_root,
        task_id="task-1",
    )

    result = target.repair_openrouter_task(args)
    assert result["disposition"] == "SUCCEEDED"
    assert sealed[0]["receipt"]["replayed_pages"] == []
    assert sealed[0]["receipt"]["revalidated_pages"] == [1, 2, 3]

    provider_result["cached_pages"] = [1, 3]
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="complete page frontier",
    ):
        target.repair_openrouter_task(args)


def test_item_only_repair_seals_one_prompt_hash_per_page_without_provider_call(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "BID" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 1,
        "document_page_count": 3,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "relative_path": "BID/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "FAILED",
        "task_id": "task-1",
    }
    captured = []
    sealed = []
    monkeypatch.setattr(target, "_plan", lambda _path: {"policy": {"dpi": 300}})
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda *_args, **_kwargs: [task])
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple", "documents": 1},
    )

    def manifest(_database, **kwargs):
        captured.append(kwargs)
        return {
            "document_manifest_id": "gfdmv1:manifest:" + "d" * 64,
            "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V3",
        }

    monkeypatch.setattr(target, "build_financial_document_manifest_v1", manifest)
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {page: str(page) * 64 for page in (1, 2, 3)},
    )
    monkeypatch.setattr(target, "usage_summary_v1", lambda _database: {"run_count": 3})
    monkeypatch.setattr(
        target,
        "seal_google_fallback_corpus_task_v1",
        lambda _ledger, **kwargs: sealed.append(kwargs) or {**task, "state": "SUCCEEDED"},
    )
    args = Namespace(
        artifact_root=tmp_path / "artifacts",
        database=tmp_path / "store.sqlite3",
        ledger=tmp_path / "ledger.sqlite3",
        physical_page=[2],
        plan=tmp_path / "plan.json",
        source_root=source_root,
        task_id="task-1",
    )
    result = target.repair_openrouter_items_task(args)
    prompts = captured[0]["prompt_sha256"]
    assert list(prompts) == [1, 2, 3]
    assert prompts[1] == prompts[3]
    assert prompts[2] != prompts[1]
    assert captured[0]["page_image_sha256s"] == {page: str(page) * 64 for page in (1, 2, 3)}
    assert result["result"]["alternate_prompt_pages"] == [2]
    assert sealed[0]["receipt"]["fallback_pages"] == [2]
    assert (tmp_path / "artifacts" / "task-1" / "mixed-prompt-document-manifest.json").is_file()

    args.physical_page = [2, 2]
    with pytest.raises(target.RunGeminiJsonFirstCorpusSupervisorV1Error, match="duplicate"):
        target.repair_openrouter_items_task(args)


def test_openrouter_untyped_provider_retry_repeats_default_prompt_and_seals_manifest(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "VIB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    prior = {
        "cached_pages": [1, 3],
        "failed_pages": [2],
        "semantic_failed_pages": [],
    }
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 1,
        "document_page_count": 3,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "last_receipt_json": canonical_json_bytes_v1(prior),
        "relative_path": "VIB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "NEEDS_RETRY",
        "task_id": "task-1",
    }
    transitions = []
    commands = []
    manifests = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {
            **task,
            "attempt_count": 2,
            "state": kwargs["next_state"],
        }

    def command(argv, *, expected):
        commands.append(argv)
        assert expected == {0, 2}
        assert argv[argv.index("--prompt-variant") + 1] == "simple"
        assert argv.count("--physical-page") == 1
        assert argv[argv.index("--physical-page") + 1] == "2"
        return 0, {
            "cached_pages": [],
            "disposition": "SUCCEEDED",
            "failed_pages": [],
            "ingested_pages": [2],
            "manifest_id": None,
            "page_image_sha256s": [{"image_sha256": "2" * 64, "physical_page": 2}],
            "semantic_failed_pages": [],
        }

    def manifest(_database, **kwargs):
        manifests.append(kwargs)
        return {
            "document_manifest_id": "gfdmv1:manifest:" + "d" * 64,
            "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V3",
            "pages": [
                {"physical_page": page, "status": "FINANCIAL_NOTE_CONTENT"} for page in (1, 2, 3)
            ],
        }

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    monkeypatch.setattr(target, "build_financial_document_manifest_v1", manifest)
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {page: str(page) * 64 for page in (1, 2, 3)},
    )
    result = target._run_openrouter(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=25,
        google_key_file=tmp_path / "google",
        google_key_slot=2,
        provider_timeout_seconds=60,
        max_attempts=2,
    )
    assert len(commands) == 1
    assert [item["next_state"] for item in transitions] == ["RUNNING", "SUCCEEDED"]
    assert result["state"] == "SUCCEEDED"
    prompts = manifests[0]["prompt_sha256"]
    assert prompts[1] == prompts[3]
    assert prompts[2] == prompts[1]
    assert manifests[0]["page_image_sha256s"] == {page: str(page) * 64 for page in (1, 2, 3)}
    final_receipt = transitions[-1]["receipt"]
    assert final_receipt["alternate_prompt_pages"] == [2]
    assert final_receipt["alternate_prompt_variant"] == "simple"
    assert final_receipt["revalidated_document_pages"] == [1, 2, 3]
    assert final_receipt["protected_retry_pages"] == []


def test_provider_page_image_frontier_rejects_missing_duplicate_and_bad_hash() -> None:
    valid = [
        {"image_sha256": "1" * 64, "physical_page": 1},
        {"image_sha256": "2" * 64, "physical_page": 2},
    ]
    assert target._summary_page_image_sha256s_v1(valid, allowed_pages=[1, 2]) == {
        1: "1" * 64,
        2: "2" * 64,
    }
    attacks = (
        valid[:1],
        [valid[0], valid[0]],
        [valid[0], {"image_sha256": "not-a-hash", "physical_page": 2}],
        [valid[0], {"image_sha256": "2" * 64, "physical_page": 3}],
    )
    for attack in attacks:
        with pytest.raises(
            target.RunGeminiJsonFirstCorpusSupervisorV1Error,
            match="page image frontier",
        ):
            target._summary_page_image_sha256s_v1(attack, allowed_pages=[1, 2])


def test_adaptive_retry_artifact_dir_is_bound_to_exact_page_frontier(tmp_path) -> None:
    first = target._adaptive_retry_artifact_dir_v1(
        task_root=tmp_path / "task",
        prompt_variant="scope",
        pages=[2, 4],
    )
    same = target._adaptive_retry_artifact_dir_v1(
        task_root=tmp_path / "task",
        prompt_variant="scope",
        pages=[2, 4],
    )
    narrowed = target._adaptive_retry_artifact_dir_v1(
        task_root=tmp_path / "task",
        prompt_variant="scope",
        pages=[4],
    )

    assert first == same
    assert first != narrowed
    assert first.parent.parent.name == "adaptive-retry"
    assert first.parent.name == "scope"
    assert first.name.startswith("pages-")
    assert len(first.name.removeprefix("pages-")) == 64
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="artifact frontier",
    ):
        target._adaptive_retry_artifact_dir_v1(
            task_root=tmp_path / "task",
            prompt_variant="scope",
            pages=[4, 2],
        )


def test_running_same_attempt_recovery_retains_exact_retry_frontiers() -> None:
    recovered = {
        "state": "RUNNING",
        "first_physical_page": 1,
        "last_physical_page": 5,
        "last_receipt_json": canonical_json_bytes_v1(
            {
                "collision_evidence": [],
                "failed_pages": [1, 2, 4],
                "format_version": (
                    "GEMINI_JSON_FIRST_OPENROUTER_LOCAL_ARTIFACT_COLLISION_RECOVERY_V1"
                ),
                "prior_failed_receipt_sha256": "1" * 64,
                "recitation_failed_pages": [1],
                "recovery_same_attempt": True,
                "retry_frontier_receipt_sha256": "2" * 64,
                "semantic_failed_pages": [4],
                "unresolved_pages": [],
            }
        ),
    }

    assert target._retry_prompt_frontiers_v1(recovered) == {
        "balanced": [],
        "default": [2],
        "items": [4],
        "scope": [1],
    }
    assert target._protected_retry_pages_v1(recovered) == [4]
    ordinary_running = {
        **recovered,
        "last_receipt_json": canonical_json_bytes_v1({"document_run_started": True}),
    }
    assert target._retry_prompt_frontiers_v1(ordinary_running) is None
    assert target._protected_retry_pages_v1(ordinary_running) == []


def test_historical_successful_prompt_variants_survive_a_later_retry(tmp_path) -> None:
    plan = build_gemini_json_first_corpus_plan_v1(
        [
            {
                "relative_path": "vietstock_bctc/ABB/2025/report.pdf",
                "source_sha256": "3" * 64,
                "source_size_bytes": 100,
                "page_count": 3,
            }
        ],
        openrouter_page_fraction="1.0",
    )
    ledger = tmp_path / "ledger.sqlite3"
    target.initialize_gemini_json_first_corpus_ledger_v1(ledger, plan=plan, max_task_attempts=3)
    task = target.list_corpus_tasks_v1(ledger)[0]
    task = target.transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="PENDING",
        next_state="RUNNING",
        receipt={"document_run_started": True},
    )
    task = target.transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state="NEEDS_RETRY",
        receipt={
            "failed_pages": [1, 2, 3],
            "recitation_failed_pages": [2],
            "semantic_failed_pages": [1],
            "unresolved_pages": [],
        },
    )
    task = target.transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="NEEDS_RETRY",
        next_state="RUNNING",
        receipt={"document_run_started": True},
    )
    task = target.transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state="FAILED",
        receipt={
            "alternate_prompt_variants": [
                {"physical_pages": [3], "prompt_variant": "simple"},
                {"physical_pages": [2], "prompt_variant": "scope"},
                {"physical_pages": [1], "prompt_variant": "items"},
            ],
            "failed_pages": [3],
            "protected_retry_pages": [1],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        },
    )

    assert target._successful_historical_prompt_context_v1(ledger=ledger, task=task) == (
        {1: "items", 2: "scope"},
        [1],
    )


def test_third_attempt_manifest_keeps_prior_successful_prompt_variants(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "ABB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 2,
        "document_page_count": 3,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "last_receipt_json": canonical_json_bytes_v1(
            {
                "failed_pages": [3],
                "recitation_failed_pages": [],
                "semantic_failed_pages": [],
                "unresolved_pages": [],
            }
        ),
        "relative_path": "ABB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "NEEDS_RETRY",
        "task_id": "task-1",
    }
    transitions = []
    manifests = []
    monkeypatch.setattr(
        target,
        "_successful_historical_prompt_context_v1",
        lambda **_kwargs: ({1: "items", 2: "scope"}, [1]),
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    monkeypatch.setattr(
        target,
        "transition_corpus_task_v1",
        lambda _ledger, **kwargs: (
            transitions.append(kwargs)
            or {**task, "attempt_count": 3, "state": kwargs["next_state"]}
        ),
    )
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {page: str(page) * 64 for page in (1, 2, 3)},
    )
    monkeypatch.setattr(
        target,
        "_command",
        lambda _argv, *, expected: (
            0,
            {
                "cached_pages": [],
                "disposition": "SUCCEEDED",
                "failed_pages": [],
                "ingested_pages": [3],
                "offline_missing_pages": [],
                "page_image_sha256s": [{"image_sha256": "3" * 64, "physical_page": 3}],
                "recitation_failed_pages": [],
                "semantic_failed_pages": [],
                "unresolved_pages": [],
            },
        ),
    )

    def manifest(_database, **kwargs):
        manifests.append(kwargs)
        return {
            "document_manifest_id": "gfdmv1:manifest:" + "a" * 64,
            "pages": [
                {"physical_page": page, "status": "FINANCIAL_NOTE_CONTENT"} for page in (1, 2, 3)
            ],
        }

    monkeypatch.setattr(target, "build_financial_document_manifest_v1", manifest)
    result = target._run_openrouter(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=20,
        google_key_file=tmp_path / "unused-google",
        google_key_slot=1,
        provider_timeout_seconds=900,
        max_attempts=3,
        openrouter_only=True,
    )
    assert result["state"] == "SUCCEEDED"
    assert len(set(manifests[0]["prompt_sha256"].values())) == 3
    assert transitions[-1]["receipt"]["protected_retry_pages"] == [1]


def test_openrouter_recitation_retry_uses_scope_and_may_resolve_to_no_relevant(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "ACB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 1,
        "document_page_count": 3,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "last_receipt_json": canonical_json_bytes_v1(
            {
                "failed_pages": [2],
                "recitation_failed_pages": [2],
                "semantic_failed_pages": [],
            }
        ),
        "relative_path": "ACB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "NEEDS_RETRY",
        "task_id": "task-1",
    }
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "attempt_count": 2, "state": kwargs["next_state"]}

    def command(argv, *, expected):
        assert expected == {0, 2}
        assert argv[argv.index("--prompt-variant") + 1] == "scope"
        assert argv[argv.index("--physical-page") + 1] == "2"
        assert "adaptive-retry/scope" in argv[argv.index("--artifact-dir") + 1]
        return 0, {
            "cached_pages": [],
            "disposition": "SUCCEEDED",
            "failed_pages": [],
            "ingested_pages": [2],
            "page_image_sha256s": [{"image_sha256": "2" * 64, "physical_page": 2}],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
        }

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    monkeypatch.setattr(
        target,
        "build_financial_document_manifest_v1",
        lambda *_args, **_kwargs: {
            "document_manifest_id": "gfdmv1:manifest:" + "f" * 64,
            "pages": [
                {
                    "physical_page": page,
                    "status": (
                        "NO_RELEVANT_FINANCIAL_CONTENT" if page == 2 else "FINANCIAL_NOTE_CONTENT"
                    ),
                }
                for page in (1, 2, 3)
            ],
        },
    )
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {page: str(page) * 64 for page in (1, 2, 3)},
    )
    result = target._run_openrouter(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=25,
        google_key_file=tmp_path / "google",
        google_key_slot=2,
        provider_timeout_seconds=60,
        max_attempts=2,
    )
    assert result["state"] == "SUCCEEDED"
    receipt = transitions[-1]["receipt"]
    assert receipt["alternate_prompt_variant"] == "scope"
    assert receipt["protected_retry_pages"] == []
    assert (tmp_path / "artifacts" / "task-1" / "adaptive-prompt-document-manifest.json").is_file()


def test_openrouter_adaptive_retry_partitions_mixed_failure_kinds(monkeypatch, tmp_path) -> None:
    source_root = tmp_path / "source"
    source = source_root / "MBB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 1,
        "document_page_count": 4,
        "first_physical_page": 1,
        "last_physical_page": 4,
        "last_receipt_json": canonical_json_bytes_v1(
            {
                "failed_pages": [2, 3, 4],
                "recitation_failed_pages": [2],
                "semantic_failed_pages": [3],
            }
        ),
        "relative_path": "MBB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "NEEDS_RETRY",
        "task_id": "task-1",
    }
    transitions = []
    calls = []
    manifests = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "attempt_count": 2, "state": kwargs["next_state"]}

    def command(argv, *, expected):
        assert expected == {0, 2}
        variant = argv[argv.index("--prompt-variant") + 1]
        page = int(argv[argv.index("--physical-page") + 1])
        offline = "--offline-replay-only" in argv
        calls.append(("OFFLINE" if offline else variant, page))
        return 0, {
            "cached_pages": [],
            "execution_mode": "OFFLINE_REPLAY_ONLY" if offline else "PROVIDER_OR_CACHE",
            "failed_pages": [],
            "ingested_pages": [page],
            "page_image_sha256s": [{"image_sha256": str(page) * 64, "physical_page": page}],
            "provider_request_pages": [] if offline else [page],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        }

    def manifest(_database, **kwargs):
        manifests.append(kwargs)
        return {
            "document_manifest_id": "gfdmv1:manifest:" + "c" * 64,
            "pages": [
                {
                    "physical_page": page,
                    "status": (
                        "NO_RELEVANT_FINANCIAL_CONTENT" if page == 2 else "FINANCIAL_NOTE_CONTENT"
                    ),
                }
                for page in (1, 2, 3, 4)
            ],
        }

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    monkeypatch.setattr(target, "build_financial_document_manifest_v1", manifest)
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {page: str(page) * 64 for page in (1, 2, 3, 4)},
    )
    result = target._run_openrouter(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=25,
        google_key_file=tmp_path / "google",
        google_key_slot=2,
        provider_timeout_seconds=60,
        max_attempts=2,
    )
    assert result["state"] == "SUCCEEDED"
    assert calls == [("OFFLINE", 3), ("simple", 4), ("scope", 2)]
    prompt_hashes = manifests[0]["prompt_sha256"]
    assert prompt_hashes[3] == prompt_hashes[1]
    assert len({prompt_hashes[2], prompt_hashes[4]}) == 2
    receipt = transitions[-1]["receipt"]
    assert receipt["protected_retry_pages"] == [3]
    assert [item["accepted_pages"] for item in receipt["offline_replay_results"]] == [[3]]
    assert receipt["alternate_prompt_variants"] == [
        {"physical_pages": [3, 4], "prompt_variant": "simple"},
        {"physical_pages": [2], "prompt_variant": "scope"},
    ]


def test_openrouter_adaptive_retry_defers_later_prompt_frontiers_after_circuit_trip(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "KLB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 1,
        "document_page_count": 2,
        "first_physical_page": 1,
        "last_physical_page": 2,
        "last_receipt_json": canonical_json_bytes_v1(
            {"failed_pages": [1, 2], "semantic_failed_pages": [2]}
        ),
        "relative_path": "KLB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "NEEDS_RETRY",
        "task_id": "task-1",
    }
    transitions = []
    calls = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "attempt_count": 2, "state": kwargs["next_state"]}

    def command(argv, *, expected):
        assert expected == {0, 2}
        variant = argv[argv.index("--prompt-variant") + 1]
        page = int(argv[argv.index("--physical-page") + 1])
        offline = "--offline-replay-only" in argv
        calls.append((variant, page, offline))
        return 2, {
            "cached_pages": [],
            "execution_mode": "OFFLINE_REPLAY_ONLY" if offline else "PROVIDER_OR_CACHE",
            "failed_pages": [page],
            "ingested_pages": [],
            "offline_missing_pages": [page] if offline else [],
            "page_image_sha256s": [{"image_sha256": str(page) * 64, "physical_page": page}],
            "provider_circuit_breaker_trigger_page": None if offline else page,
            "provider_request_pages": [] if offline else [page],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        }

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "_offline_semantic_replay_result_v1",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {1: "1" * 64, 2: "2" * 64},
    )

    result = target._run_openrouter(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=1,
        google_key_file=tmp_path / "google",
        google_key_slot=1,
        provider_timeout_seconds=60,
        max_attempts=2,
        openrouter_only=True,
    )

    assert result["state"] == "FAILED"
    assert calls == [("simple", 1, False), ("items", 2, True)]
    receipt = transitions[-1]["receipt"]
    assert receipt["failed_pages"] == [1, 2]
    assert receipt["offline_missing_pages"] == [2]
    assert receipt["provider_circuit_deferred_pages"] == [2]
    assert (
        receipt["adaptive_retry_results"][0]["result"]["provider_circuit_breaker_trigger_page"] == 1
    )
    assert receipt["adaptive_retry_results"][1]["result"]["provider_request_pages"] == []


def test_openrouter_semantic_retry_can_finish_without_provider_request(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "MBB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 1,
        "document_page_count": 1,
        "first_physical_page": 1,
        "last_physical_page": 1,
        "last_receipt_json": canonical_json_bytes_v1(
            {"failed_pages": [1], "semantic_failed_pages": [1]}
        ),
        "relative_path": "MBB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "NEEDS_RETRY",
        "task_id": "task-1",
    }
    transitions = []
    calls = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "attempt_count": 2, "state": kwargs["next_state"]}

    def command(argv, *, expected):
        assert expected == {0, 2}
        assert "--offline-replay-only" in argv
        calls.append(argv)
        return 0, {
            "cached_pages": [],
            "execution_mode": "OFFLINE_REPLAY_ONLY",
            "failed_pages": [],
            "ingested_pages": [1],
            "page_image_sha256s": [{"image_sha256": "1" * 64, "physical_page": 1}],
            "provider_request_pages": [],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        }

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {1: "1" * 64},
    )
    monkeypatch.setattr(
        target,
        "_page_variant_manifest_v1",
        lambda **_kwargs: {
            "document_manifest_id": "gfdmv1:manifest:" + "f" * 64,
            "pages": [{"physical_page": 1, "status": "FINANCIAL_NOTE_CONTENT"}],
        },
    )

    result = target._run_openrouter(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=20,
        google_key_file=tmp_path / "google",
        google_key_slot=1,
        provider_timeout_seconds=60,
        max_attempts=2,
        openrouter_only=True,
    )

    assert result["state"] == "SUCCEEDED"
    assert len(calls) == 1
    receipt = transitions[-1]["receipt"]
    assert receipt["adaptive_retry_results"] == []
    assert receipt["alternate_prompt_variants"] == [
        {"physical_pages": [1], "prompt_variant": "simple"}
    ]
    assert receipt["offline_replay_results"][0]["accepted_pages"] == [1]


def test_openrouter_semantic_retry_replays_paid_items_response_before_provider(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "ABB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 2,
        "document_page_count": 1,
        "first_physical_page": 1,
        "last_physical_page": 1,
        "last_receipt_json": canonical_json_bytes_v1(
            {"failed_pages": [1], "semantic_failed_pages": [1]}
        ),
        "relative_path": "ABB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "NEEDS_RETRY",
        "task_id": "task-1",
    }
    transitions = []
    calls = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "attempt_count": 3, "state": kwargs["next_state"]}

    def command(argv, *, expected):
        assert expected == {0, 2}
        assert "--offline-replay-only" in argv
        variant = argv[argv.index("--prompt-variant") + 1]
        calls.append(variant)
        accepted = variant == "items"
        return (0 if accepted else 2), {
            "cached_pages": [],
            "execution_mode": "OFFLINE_REPLAY_ONLY",
            "failed_pages": [] if accepted else [1],
            "ingested_pages": [1] if accepted else [],
            "offline_missing_pages": [] if accepted else [1],
            "page_image_sha256s": [{"image_sha256": "1" * 64, "physical_page": 1}],
            "provider_request_pages": [],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        }

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    monkeypatch.setattr(
        target,
        "_successful_historical_prompt_context_v1",
        lambda **_kwargs: ({}, []),
    )
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {1: "1" * 64},
    )
    monkeypatch.setattr(
        target,
        "_page_variant_manifest_v1",
        lambda **_kwargs: {
            "document_manifest_id": "gfdmv1:manifest:" + "f" * 64,
            "pages": [{"physical_page": 1, "status": "FINANCIAL_NOTE_CONTENT"}],
        },
    )

    result = target._run_openrouter(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=1,
        google_key_file=tmp_path / "google",
        google_key_slot=1,
        provider_timeout_seconds=60,
        max_attempts=3,
        openrouter_only=True,
    )

    assert result["state"] == "SUCCEEDED"
    assert calls == ["simple", "items"]
    receipt = transitions[-1]["receipt"]
    assert [item["accepted_pages"] for item in receipt["offline_replay_results"]] == [
        [],
        [1],
    ]
    assert receipt["alternate_prompt_variants"] == [
        {"physical_pages": [1], "prompt_variant": "items"}
    ]


def test_current_document_manifest_binds_image_and_prompt_frontiers(monkeypatch, tmp_path) -> None:
    task = {
        "artifact_relative_path": "task-1",
        "document_page_count": 3,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "relative_path": "ACB/report.pdf",
        "source_sha256": "a" * 64,
        "state": "SUCCEEDED",
        "task_id": "task-1",
    }
    planned = {
        "document": {
            "page_count": 3,
            "relative_path": "ACB/report.pdf",
            "source_sha256": "b" * 64,
            "source_size_bytes": 3,
        },
        "document_plan_id": "gjfpdocv1:" + "b" * 64,
        "route": target.OPENROUTER_ROUTE,
        "tasks": [{"task_id": "task-1"}],
    }
    monkeypatch.setattr(
        target, "_plan", lambda _path: {"documents": [planned], "policy": {"dpi": 300}}
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda _ledger: [task])
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    images = {page: str(page) * 64 for page in (1, 2, 3)}
    monkeypatch.setattr(target, "_current_page_image_sha256s_v1", lambda **_kwargs: images)
    captured = []

    def manifest(_database, **kwargs):
        captured.append(kwargs)
        return {
            "document_manifest_id": "gfdmv1:manifest:" + "c" * 64,
            "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4",
            "page_count": 3,
            "pages": [
                {"physical_page": page, "status": "FINANCIAL_NOTE_CONTENT"} for page in (1, 2, 3)
            ],
            "status_counts": {"FINANCIAL_NOTE_CONTENT": 3},
            "totals": {"cost_usd": "0.010000000000"},
        }

    monkeypatch.setattr(target, "build_financial_document_manifest_v1", manifest)
    args = Namespace(
        artifact_root=tmp_path / "artifacts",
        database=tmp_path / "store.sqlite3",
        ledger=tmp_path / "ledger.sqlite3",
        page_prompt_variant=["2=scope", "3=items"],
        plan=tmp_path / "plan.json",
        source_root=tmp_path / "source",
        task_id="task-1",
    )
    result = target.build_current_document_manifest(args)
    assert result["disposition"] == "SUCCEEDED"
    assert captured[0]["page_image_sha256s"] == images
    prompts = captured[0]["prompt_sha256"]
    assert len(set(prompts.values())) == 3
    assert [item["prompt_variant"] for item in result["page_prompt_variants"]] == [
        "simple",
        "scope",
        "items",
    ]
    assert Path(result["output"]).is_file()
    assert result["repaired_task_ids"] == []


def test_current_document_manifest_atomically_seals_failed_chunks(monkeypatch, tmp_path) -> None:
    tasks = [
        {
            "artifact_relative_path": "task-1",
            "document_page_count": 3,
            "first_physical_page": 1,
            "last_physical_page": 2,
            "relative_path": "ACB/report.pdf",
            "source_sha256": "a" * 64,
            "state": "FAILED",
            "task_id": "task-1",
        },
        {
            "artifact_relative_path": "task-2",
            "document_page_count": 3,
            "first_physical_page": 3,
            "last_physical_page": 3,
            "relative_path": "ACB/report.pdf",
            "source_sha256": "a" * 64,
            "state": "SUCCEEDED",
            "task_id": "task-2",
        },
    ]
    planned = {
        "document": {"page_count": 3},
        "document_plan_id": "gjfpdocv1:" + "b" * 64,
        "route": target.GOOGLE_ROUTE,
        "tasks": [{"task_id": "task-1"}, {"task_id": "task-2"}],
    }
    monkeypatch.setattr(
        target, "_plan", lambda _path: {"documents": [planned], "policy": {"dpi": 300}}
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda _ledger: tasks)
    monkeypatch.setattr(
        target, "corpus_ledger_summary_v1", lambda _ledger: {"prompt_variant": "simple"}
    )
    images = {page: str(page) * 64 for page in (1, 2, 3)}
    monkeypatch.setattr(target, "_current_page_image_sha256s_v1", lambda **_kwargs: images)
    monkeypatch.setattr(
        target,
        "build_financial_document_manifest_v1",
        lambda *_args, **_kwargs: {
            "document_manifest_id": "gfdmv1:manifest:" + "c" * 64,
            "page_count": 3,
            "pages": [
                {"physical_page": page, "status": "FINANCIAL_NOTE_CONTENT"} for page in (1, 2, 3)
            ],
            "status_counts": {"FINANCIAL_NOTE_CONTENT": 3},
            "totals": {"cost_usd": "0.010000000000"},
        },
    )
    captured = []

    def seal(_ledger, *, task_id, receipt):
        captured.append((task_id, receipt))
        return [{"task_id": "task-1"}]

    monkeypatch.setattr(target, "seal_current_document_revalidated_corpus_tasks_v1", seal)
    result = target.build_current_document_manifest(
        Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            ledger=tmp_path / "ledger.sqlite3",
            page_prompt_variant=["2=scope"],
            plan=tmp_path / "plan.json",
            source_root=tmp_path / "source",
            task_id="task-1",
        )
    )
    assert result["repaired_task_ids"] == ["task-1"]
    assert captured[0][0] == "task-1"
    assert captured[0][1]["repaired_task_ids"] == ["task-1"]
    assert captured[0][1]["revalidated_pages"] == [1, 2, 3]
    assert captured[0][1]["page_prompt_variants"][1] == {
        "physical_page": 2,
        "prompt_variant": "scope",
    }


def test_current_document_manifest_accepts_a_retryable_complete_store(
    monkeypatch, tmp_path
) -> None:
    task = {
        "artifact_relative_path": "task-1",
        "document_page_count": 1,
        "first_physical_page": 1,
        "last_physical_page": 1,
        "relative_path": "ACB/report.pdf",
        "source_sha256": "a" * 64,
        "state": "NEEDS_RETRY",
        "task_id": "task-1",
    }
    planned = {
        "document": {"page_count": 1},
        "document_plan_id": "gjfpdocv1:" + "b" * 64,
        "route": target.OPENROUTER_ROUTE,
        "tasks": [{"task_id": "task-1"}],
    }
    monkeypatch.setattr(
        target, "_plan", lambda _path: {"documents": [planned], "policy": {"dpi": 300}}
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda _ledger: [task])
    monkeypatch.setattr(
        target, "corpus_ledger_summary_v1", lambda _ledger: {"prompt_variant": "simple"}
    )
    monkeypatch.setattr(target, "_current_page_image_sha256s_v1", lambda **_kwargs: {1: "1" * 64})
    monkeypatch.setattr(
        target,
        "build_financial_document_manifest_v1",
        lambda *_args, **_kwargs: {
            "document_manifest_id": "gfdmv1:manifest:" + "c" * 64,
            "page_count": 1,
            "pages": [{"physical_page": 1, "status": "FINANCIAL_NOTE_CONTENT"}],
            "status_counts": {"FINANCIAL_NOTE_CONTENT": 1},
            "totals": {"cost_usd": "0.010000000000"},
        },
    )
    captured = []

    def seal(_ledger, *, task_id, receipt):
        captured.append((task_id, receipt))
        return [{"task_id": task_id}]

    monkeypatch.setattr(target, "seal_current_document_revalidated_corpus_tasks_v1", seal)

    result = target.build_current_document_manifest(
        Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            ledger=tmp_path / "ledger.sqlite3",
            page_prompt_variant=[],
            plan=tmp_path / "plan.json",
            source_root=tmp_path / "source",
            task_id="task-1",
        )
    )

    assert result["disposition"] == "SUCCEEDED"
    assert result["repaired_task_ids"] == ["task-1"]
    assert captured[0][1]["repaired_task_ids"] == ["task-1"]


def test_page_prompt_variant_overrides_fail_closed() -> None:
    for overrides in (["1=scope", "1=items"], ["4=scope"], ["1=unknown"], ["bad"]):
        with pytest.raises(
            target.RunGeminiJsonFirstCorpusSupervisorV1Error,
            match="page prompt override",
        ):
            target._page_prompt_variants_v1(
                expected_pages=[1, 2, 3],
                default_variant="simple",
                overrides=overrides,
            )


def test_openrouter_first_semantic_failure_moves_to_item_retry(monkeypatch, tmp_path) -> None:
    source_root = tmp_path / "source"
    source = source_root / "VPB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 0,
        "document_page_count": 3,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "last_receipt_json": None,
        "relative_path": "VPB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "PENDING",
        "task_id": "task-1",
    }
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "attempt_count": 1, "state": kwargs["next_state"]}

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(
        target,
        "_command",
        lambda *_args, **_kwargs: (
            2,
            {
                "disposition": "NEEDS_RETRY",
                "failed_pages": [2],
                "semantic_failed_pages": [2],
            },
        ),
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    result = target._run_openrouter(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=25,
        google_key_file=tmp_path / "google",
        google_key_slot=2,
        provider_timeout_seconds=60,
        max_attempts=2,
    )
    assert result["state"] == "NEEDS_RETRY"
    assert [item["next_state"] for item in transitions] == ["RUNNING", "NEEDS_RETRY"]


def test_openrouter_item_retry_accepts_semantic_subset_and_rejects_ambiguous_frontier() -> None:
    task = {
        "document_page_count": 3,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "state": "NEEDS_RETRY",
    }
    semantic = {
        **task,
        "last_receipt_json": canonical_json_bytes_v1(
            {"failed_pages": [2], "semantic_failed_pages": [2]}
        ),
    }
    assert target._provider_retry_pages_v1(semantic) == [2]
    assert target._protected_retry_pages_v1(semantic) == [2]
    unresolved = {
        **task,
        "last_receipt_json": canonical_json_bytes_v1(
            {
                "failed_pages": [2],
                "semantic_failed_pages": [],
                "unresolved_pages": [2],
            }
        ),
    }
    assert target._provider_retry_pages_v1(unresolved) == [2]
    assert target._protected_retry_pages_v1(unresolved) == [2]
    recitation = {
        **task,
        "last_receipt_json": canonical_json_bytes_v1(
            {
                "failed_pages": [2],
                "recitation_failed_pages": [2],
                "semantic_failed_pages": [],
            }
        ),
    }
    assert target._retry_prompt_frontiers_v1(recitation) == {
        "balanced": [],
        "default": [],
        "items": [],
        "scope": [2],
    }
    assert target._protected_retry_pages_v1(recitation) == []

    for prior in (
        {"failed_pages": [2, 2], "semantic_failed_pages": []},
        {"failed_pages": [0], "semantic_failed_pages": []},
        {"failed_pages": [2], "semantic_failed_pages": [3]},
        {
            "failed_pages": [2],
            "recitation_failed_pages": [2],
            "semantic_failed_pages": [2],
        },
    ):
        candidate = {**task, "last_receipt_json": canonical_json_bytes_v1(prior)}
        with pytest.raises(
            target.RunGeminiJsonFirstCorpusSupervisorV1Error,
            match="failed-page frontier",
        ):
            target._provider_retry_pages_v1(candidate)


@pytest.mark.parametrize(
    ("item_status", "expected_state"),
    [
        ("FINANCIAL_NOTE_CONTENT", "SUCCEEDED"),
        ("NO_RELEVANT_FINANCIAL_CONTENT", "FAILED"),
    ],
)
def test_openrouter_semantic_item_retry_never_drops_known_financial_content(
    monkeypatch, tmp_path, item_status, expected_state
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "VPB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 1,
        "document_page_count": 3,
        "first_physical_page": 1,
        "last_physical_page": 3,
        "last_receipt_json": canonical_json_bytes_v1(
            {
                "cached_pages": [1, 3],
                "failed_pages": [2],
                "semantic_failed_pages": [2],
            }
        ),
        "relative_path": "VPB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "NEEDS_RETRY",
        "task_id": "task-1",
    }
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {**task, "attempt_count": 2, "state": kwargs["next_state"]}

    def command(argv, *, expected):
        assert expected == {0, 2}
        assert argv[argv.index("--prompt-variant") + 1] == "items"
        assert argv[argv.index("--physical-page") + 1] == "2"
        return 0, {
            "cached_pages": [],
            "disposition": "SUCCEEDED",
            "failed_pages": [],
            "ingested_pages": [2],
            "manifest_id": None,
            "page_image_sha256s": [{"image_sha256": "2" * 64, "physical_page": 2}],
            "semantic_failed_pages": [],
        }

    def manifest(_database, **_kwargs):
        return {
            "document_manifest_id": "gfdmv1:manifest:" + "e" * 64,
            "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V3",
            "pages": [
                {"physical_page": 1, "status": "FINANCIAL_NOTE_CONTENT"},
                {"physical_page": 2, "status": item_status},
                {"physical_page": 3, "status": "FINANCIAL_NOTE_CONTENT"},
            ],
        }

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "_offline_semantic_replay_result_v1",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )
    monkeypatch.setattr(target, "build_financial_document_manifest_v1", manifest)
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: {page: str(page) * 64 for page in (1, 2, 3)},
    )
    result = target._run_openrouter(
        task=task,
        plan={"policy": {"dpi": 300}},
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=25,
        google_key_file=tmp_path / "google",
        google_key_slot=2,
        provider_timeout_seconds=60,
        max_attempts=2,
    )
    assert result["state"] == expected_state
    receipt = transitions[-1]["receipt"]
    assert receipt["protected_retry_pages"] == [2]
    if expected_state == "SUCCEEDED":
        assert receipt["manifest_id"].startswith("gfdmv1:manifest:")
        assert (tmp_path / "artifacts" / "task-1" / "mixed-prompt-document-manifest.json").is_file()
    else:
        assert receipt["semantic_item_no_relevant_pages"] == [2]
        assert not (
            tmp_path / "artifacts" / "task-1" / "mixed-prompt-document-manifest.json"
        ).exists()


def _acceleration_fixture(monkeypatch, tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"pdf")
    tasks = [
        {
            "artifact_relative_path": "task-1",
            "document_page_count": 3,
            "first_physical_page": 1,
            "last_physical_page": 2,
            "provider_job_ref": "gjfpaccelv1:claim:" + "a" * 64,
            "relative_path": "ACB/report.pdf",
            "route": target.GOOGLE_ROUTE,
            "source_sha256": "b" * 64,
            "state": "RUNNING",
            "task_id": "task-1",
        },
        {
            "artifact_relative_path": "task-2",
            "document_page_count": 3,
            "first_physical_page": 3,
            "last_physical_page": 3,
            "provider_job_ref": "gjfpaccelv1:claim:" + "a" * 64,
            "relative_path": "ACB/report.pdf",
            "route": target.GOOGLE_ROUTE,
            "source_sha256": "b" * 64,
            "state": "RUNNING",
            "task_id": "task-2",
        },
    ]
    planned = {
        "document": {
            "page_count": 3,
            "relative_path": "ACB/report.pdf",
            "source_sha256": "b" * 64,
            "source_size_bytes": 3,
        },
        "document_plan_id": "gjfpdocv1:" + "c" * 64,
        "route": target.GOOGLE_ROUTE,
        "tasks": [{"task_id": "task-1"}, {"task_id": "task-2"}],
    }
    monkeypatch.setattr(
        target, "_plan", lambda _path: {"documents": [planned], "policy": {"dpi": 300}}
    )
    monkeypatch.setattr(
        target,
        "claim_google_document_for_openrouter_acceleration_v1",
        lambda _ledger, *, task_id: {
            "claim_id": "gjfpaccelv1:claim:" + "a" * 64,
            "document_plan_id": planned["document_plan_id"],
            "tasks": tasks,
        },
    )
    monkeypatch.setattr(target, "_source", lambda *_args, **_kwargs: source)
    images = {page: str(page) * 64 for page in (1, 2, 3)}
    monkeypatch.setattr(target, "_current_page_image_sha256s_v1", lambda **_kwargs: images)
    monkeypatch.setattr(
        target, "corpus_ledger_summary_v1", lambda _ledger: {"prompt_variant": "simple"}
    )
    args = Namespace(
        artifact_root=tmp_path / "artifacts",
        database=tmp_path / "store.sqlite3",
        google_key_file=tmp_path / "google",
        google_key_slot=2,
        ledger=tmp_path / "ledger.sqlite3",
        max_acceleration_attempts=2,
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=25,
        plan=tmp_path / "plan.json",
        provider_timeout_seconds=60,
        source_root=tmp_path,
        task_id="task-1",
    )
    return args, tasks, images


def _selected_acceleration_manifest_fixture(tmp_path, *, image_frontier):
    planned = {
        "document": {
            "page_count": 3,
            "relative_path": "ACB/report.pdf",
            "source_sha256": "b" * 64,
            "source_size_bytes": 3,
        },
        "document_plan_id": "gjfpdocv1:" + "c" * 64,
    }
    material = {
        "document": {
            "source_logical_name": "ACB/report.pdf",
            "source_sha256": "b" * 64,
            "source_size_bytes": 3,
        },
        "extraction_contract": {"page_image_sha256s": image_frontier},
        "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4",
        "page_count": 3,
        "pages": [
            {"physical_page": page, "status": "FINANCIAL_NOTE_CONTENT"} for page in (1, 2, 3)
        ],
    }
    manifest = {
        **material,
        "document_manifest_id": "gfdmv1:manifest:" + target.canonical_json_sha256_v1(material),
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_bytes(canonical_json_bytes_v1(manifest) + b"\n")
    selection = {
        "document_manifest_id": manifest["document_manifest_id"],
        "page_image_frontier_sha256": target.canonical_json_sha256_v1(image_frontier),
        "selection_id": "gjfcdmsv1:selection:" + "d" * 64,
    }
    return planned, manifest_path, selection


def test_acceleration_resumes_selected_current_manifest_without_provider_call(
    monkeypatch, tmp_path
) -> None:
    _args, tasks, images = _acceleration_fixture(monkeypatch, tmp_path)
    frontier = [{"image_sha256": images[page], "physical_page": page} for page in (1, 2, 3)]
    planned, manifest_path, selection = _selected_acceleration_manifest_fixture(
        tmp_path, image_frontier=frontier
    )
    monkeypatch.setattr(
        target,
        "load_current_document_manifest_selection_v1",
        lambda *_args, **_kwargs: (selection, manifest_path),
    )
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {"task_id": kwargs["task_id"]}

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    result = target._resume_acceleration_from_current_manifest_v1(
        ledger=tmp_path / "ledger.sqlite3",
        planned=planned,
        tasks=tasks,
        document_root=tmp_path / "document",
        current_images=images,
    )
    assert result is not None
    assert result["completed_task_ids"] == ["task-1", "task-2"]
    assert [transition["next_state"] for transition in transitions] == [
        "SUCCEEDED",
        "SUCCEEDED",
    ]
    assert len(list((tmp_path / "document").rglob("run-receipts/*.json"))) == 1


def test_acceleration_resume_rejects_stale_whole_page_image_frontier(monkeypatch, tmp_path) -> None:
    _args, tasks, images = _acceleration_fixture(monkeypatch, tmp_path)
    stale = [
        {"image_sha256": ("f" * 64 if page == 2 else images[page]), "physical_page": page}
        for page in (1, 2, 3)
    ]
    planned, manifest_path, selection = _selected_acceleration_manifest_fixture(
        tmp_path, image_frontier=stale
    )
    monkeypatch.setattr(
        target,
        "load_current_document_manifest_selection_v1",
        lambda *_args, **_kwargs: (selection, manifest_path),
    )
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="does not replay exactly",
    ):
        target._resume_acceleration_from_current_manifest_v1(
            ledger=tmp_path / "ledger.sqlite3",
            planned=planned,
            tasks=tasks,
            document_root=tmp_path / "document",
            current_images=images,
        )


def test_google_document_acceleration_seals_full_manifest_without_duplicate_submission(
    monkeypatch, tmp_path
) -> None:
    args, tasks, images = _acceleration_fixture(monkeypatch, tmp_path)
    args.openrouter_only = True
    prior_contract = (
        args.artifact_root
        / "documents"
        / ("c" * 64)
        / "openrouter-acceleration"
        / "attempt-01"
        / "base"
        / "document-contract.json"
    )
    prior_contract.parent.mkdir(parents=True)
    prior_contract.write_text(
        json.dumps({"google_standard_mode": "on-provider-error"}), encoding="utf-8"
    )
    commands = []

    def command(argv, *, expected):
        commands.append(argv)
        return (
            0,
            {
                "disposition": "SUCCEEDED",
                "failed_pages": [],
                "page_image_sha256s": [
                    {"image_sha256": images[page], "physical_page": page} for page in (1, 2, 3)
                ],
                "recitation_failed_pages": [],
                "semantic_failed_pages": [],
                "unresolved_pages": [],
            },
        )

    monkeypatch.setattr(
        target,
        "_command",
        command,
    )
    manifest = {
        "document_manifest_id": "gfdmv1:manifest:" + "d" * 64,
        "pages": [
            {"physical_page": page, "status": "FINANCIAL_NOTE_CONTENT"} for page in (1, 2, 3)
        ],
    }
    monkeypatch.setattr(target, "build_financial_document_manifest_v1", lambda *_a, **_k: manifest)
    monkeypatch.setattr(
        target,
        "build_current_document_manifest",
        lambda _args: {
            "document_manifest_id": manifest["document_manifest_id"],
            "selection_id": "gjfcdmsv1:selection:" + "e" * 64,
        },
    )
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {"task_id": kwargs["task_id"]}

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    result = target.accelerate_google_document(args)
    assert result["disposition"] == "SUCCEEDED"
    assert result["completed_task_ids"] == [task["task_id"] for task in tasks]
    assert [item["next_state"] for item in transitions] == ["SUCCEEDED", "SUCCEEDED"]
    assert all(item["expected_state"] == "RUNNING" for item in transitions)
    assert commands[0][commands[0].index("--google-standard-mode") + 1] == "disabled"
    assert "attempt-02/base" in commands[0][commands[0].index("--artifact-dir") + 1]
    assert len(list((args.artifact_root / "documents").rglob("run-receipts/*.json"))) == 1


def test_openrouter_language_scope_submits_only_the_vietnamese_page_prefix(
    monkeypatch, tmp_path
) -> None:
    source_root = tmp_path / "source"
    source = source_root / "OCB" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")
    plan = build_gemini_json_first_corpus_plan_v1(
        [
            {
                "page_count": 2,
                "page_selection": {
                    "included_first_physical_page": 1,
                    "included_last_physical_page": 2,
                    "review_basis": "HUMAN_VISUAL_LANGUAGE_BOUNDARY",
                    "selection_kind": "VIETNAMESE_PREFIX_EXCLUDES_NON_VIETNAMESE_APPENDIX",
                },
                "relative_path": "OCB/report.pdf",
                "source_page_count": 4,
                "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
                "source_size_bytes": 3,
            }
        ],
        openrouter_page_fraction="1.0",
    )
    planned = plan["documents"][0]
    planned_task = planned["tasks"][0]
    task = {
        "artifact_relative_path": "task-1",
        "attempt_count": 0,
        "document_page_count": 2,
        "first_physical_page": 1,
        "last_physical_page": 2,
        "last_receipt_json": None,
        "relative_path": "OCB/report.pdf",
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "source_size_bytes": 3,
        "state": "PENDING",
        "task_id": planned_task["task_id"],
    }
    commands = []

    def command(argv, *, expected):
        commands.append(argv)
        assert expected == {0, 2}
        pages = [
            int(argv[index + 1]) for index, value in enumerate(argv) if value == "--physical-page"
        ]
        assert pages == [1, 2]
        assert "adaptive-retry" not in argv[argv.index("--artifact-dir") + 1]
        return 2, {
            "disposition": "NEEDS_RETRY",
            "recitation_failed_pages": [],
            "semantic_failed_pages": [1],
        }

    def transition(_ledger, **kwargs):
        return {**task, "attempt_count": 1, "state": kwargs["next_state"]}

    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"prompt_variant": "simple"},
    )

    result = target._run_openrouter(
        task=task,
        plan=plan,
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=2,
        google_key_file=tmp_path / "google",
        google_key_slot=1,
        provider_timeout_seconds=60,
        max_attempts=2,
        openrouter_only=True,
    )

    assert result["state"] == "NEEDS_RETRY"
    assert len(commands) == 1


def test_google_document_acceleration_preserves_semantic_page_when_items_drops_it(
    monkeypatch, tmp_path
) -> None:
    args, _tasks, images = _acceleration_fixture(monkeypatch, tmp_path)
    calls = []

    def command(argv, *, expected):
        calls.append(argv)
        pages = [
            int(argv[index + 1]) for index, value in enumerate(argv) if value == "--physical-page"
        ]
        if not pages:
            return 2, {
                "disposition": "NEEDS_RETRY",
                "failed_pages": [2],
                "page_image_sha256s": [
                    {"image_sha256": images[page], "physical_page": page} for page in (1, 2, 3)
                ],
                "recitation_failed_pages": [],
                "semantic_failed_pages": [2],
                "unresolved_pages": [],
            }
        assert pages == [2]
        assert argv[argv.index("--prompt-variant") + 1] == "items"
        return 0, {
            "disposition": "SUCCEEDED",
            "failed_pages": [],
            "page_image_sha256s": [{"image_sha256": images[2], "physical_page": 2}],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        }

    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "build_financial_document_manifest_v1",
        lambda *_a, **_k: {
            "document_manifest_id": "gfdmv1:manifest:" + "f" * 64,
            "pages": [
                {
                    "physical_page": page,
                    "status": (
                        "NO_RELEVANT_FINANCIAL_CONTENT" if page == 2 else "FINANCIAL_NOTE_CONTENT"
                    ),
                }
                for page in (1, 2, 3)
            ],
        },
    )
    transitions = []
    monkeypatch.setattr(
        target, "transition_corpus_task_v1", lambda *_a, **kwargs: transitions.append(kwargs)
    )
    result = target.accelerate_google_document(args)
    assert result["disposition"] == "NEEDS_RETRY"
    assert result["semantic_item_no_relevant_pages"] == [2]
    assert transitions == []
    assert len(calls) == 2


def test_google_document_acceleration_uses_balanced_only_after_persistent_semantic_failure(
    monkeypatch, tmp_path
) -> None:
    args, tasks, images = _acceleration_fixture(monkeypatch, tmp_path)
    calls = []

    def command(argv, *, expected):
        variant = argv[argv.index("--prompt-variant") + 1]
        pages = [
            int(argv[index + 1]) for index, value in enumerate(argv) if value == "--physical-page"
        ]
        calls.append((variant, pages))
        selected_pages = pages or [1, 2, 3]
        if variant in {"simple", "items"}:
            return 2, {
                "disposition": "NEEDS_RETRY",
                "failed_pages": [2],
                "page_image_sha256s": [
                    {"image_sha256": images[page], "physical_page": page} for page in selected_pages
                ],
                "recitation_failed_pages": [],
                "semantic_failed_pages": [2],
                "unresolved_pages": [],
            }
        assert variant == "balanced"
        return 0, {
            "disposition": "SUCCEEDED",
            "failed_pages": [],
            "page_image_sha256s": [{"image_sha256": images[2], "physical_page": 2}],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        }

    monkeypatch.setattr(target, "_command", command)
    manifest = {
        "document_manifest_id": "gfdmv1:manifest:" + "9" * 64,
        "pages": [
            {"physical_page": page, "status": "FINANCIAL_NOTE_CONTENT"} for page in (1, 2, 3)
        ],
    }
    monkeypatch.setattr(target, "build_financial_document_manifest_v1", lambda *_a, **_k: manifest)
    monkeypatch.setattr(
        target,
        "build_current_document_manifest",
        lambda _args: {
            "document_manifest_id": manifest["document_manifest_id"],
            "selection_id": "gjfcdmsv1:selection:" + "8" * 64,
        },
    )
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {"task_id": kwargs["task_id"]}

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    result = target.accelerate_google_document(args)
    assert result["disposition"] == "SUCCEEDED"
    assert calls == [("simple", []), ("items", [2]), ("balanced", [2])]
    assert result["provider_results"][-1]["prompt_variant"] == "balanced"
    assert [transition["next_state"] for transition in transitions] == [
        "SUCCEEDED",
        "SUCCEEDED",
    ]


def test_google_document_acceleration_escalates_provider_retry_semantic_failure(
    monkeypatch, tmp_path
) -> None:
    args, tasks, images = _acceleration_fixture(monkeypatch, tmp_path)
    calls = []

    def command(argv, *, expected):
        variant = argv[argv.index("--prompt-variant") + 1]
        pages = [
            int(argv[index + 1]) for index, value in enumerate(argv) if value == "--physical-page"
        ]
        calls.append((variant, pages))
        selected_pages = pages or [1, 2, 3]
        semantic = pages == [2]
        if variant != "balanced":
            return 2, {
                "disposition": "NEEDS_RETRY",
                "failed_pages": [2],
                "page_image_sha256s": [
                    {"image_sha256": images[page], "physical_page": page} for page in selected_pages
                ],
                "recitation_failed_pages": [],
                "semantic_failed_pages": [2] if semantic else [],
                "unresolved_pages": [],
            }
        return 0, {
            "disposition": "SUCCEEDED",
            "failed_pages": [],
            "page_image_sha256s": [{"image_sha256": images[2], "physical_page": 2}],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        }

    monkeypatch.setattr(target, "_command", command)
    manifest = {
        "document_manifest_id": "gfdmv1:manifest:" + "7" * 64,
        "pages": [
            {"physical_page": page, "status": "FINANCIAL_NOTE_CONTENT"} for page in (1, 2, 3)
        ],
    }
    monkeypatch.setattr(target, "build_financial_document_manifest_v1", lambda *_a, **_k: manifest)
    monkeypatch.setattr(
        target,
        "build_current_document_manifest",
        lambda _args: {
            "document_manifest_id": manifest["document_manifest_id"],
            "selection_id": "gjfcdmsv1:selection:" + "6" * 64,
        },
    )
    transitions = []

    def transition(_ledger, **kwargs):
        transitions.append(kwargs)
        return {"task_id": kwargs["task_id"]}

    monkeypatch.setattr(target, "transition_corpus_task_v1", transition)
    result = target.accelerate_google_document(args)
    assert result["disposition"] == "SUCCEEDED"
    assert calls == [
        ("simple", []),
        ("simple", [2]),
        ("items", [2]),
        ("balanced", [2]),
    ]
    assert [transition["next_state"] for transition in transitions] == [
        "SUCCEEDED",
        "SUCCEEDED",
    ]


def test_google_document_acceleration_promotes_repeated_provider_failure_to_items(
    monkeypatch, tmp_path
) -> None:
    args, tasks, images = _acceleration_fixture(monkeypatch, tmp_path)
    receipt_root = (
        args.artifact_root / "documents" / ("c" * 64) / "openrouter-acceleration" / "run-receipts"
    )
    receipt_root.mkdir(parents=True)
    (receipt_root / ("a" * 64 + ".json")).write_text(
        json.dumps(
            {
                "acceleration_attempt": 1,
                "format_version": "GEMINI_JSON_FIRST_OPENROUTER_ACCELERATION_RECEIPT_V1",
                "provider_results": [
                    {
                        "physical_pages": [1, 2, 3],
                        "prompt_variant": "simple",
                        "result": {
                            "failed_pages": [2],
                            "recitation_failed_pages": [],
                            "semantic_failed_pages": [],
                            "unresolved_pages": [],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def command(argv, *, expected):
        variant = argv[argv.index("--prompt-variant") + 1]
        pages = [
            int(argv[index + 1]) for index, value in enumerate(argv) if value == "--physical-page"
        ]
        calls.append((variant, pages))
        selected_pages = pages or [1, 2, 3]
        failed = not pages
        return (2 if failed else 0), {
            "disposition": "NEEDS_RETRY" if failed else "SUCCEEDED",
            "failed_pages": [2] if failed else [],
            "page_image_sha256s": [
                {"image_sha256": images[page], "physical_page": page} for page in selected_pages
            ],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        }

    monkeypatch.setattr(target, "_command", command)
    manifest = {
        "document_manifest_id": "gfdmv1:manifest:" + "5" * 64,
        "pages": [
            {"physical_page": page, "status": "FINANCIAL_NOTE_CONTENT"} for page in (1, 2, 3)
        ],
    }
    monkeypatch.setattr(target, "build_financial_document_manifest_v1", lambda *_a, **_k: manifest)
    monkeypatch.setattr(
        target,
        "build_current_document_manifest",
        lambda _args: {
            "document_manifest_id": manifest["document_manifest_id"],
            "selection_id": "gjfcdmsv1:selection:" + "4" * 64,
        },
    )
    monkeypatch.setattr(
        target,
        "transition_corpus_task_v1",
        lambda _ledger, **kwargs: {"task_id": kwargs["task_id"]},
    )
    result = target.accelerate_google_document(args)
    assert result["disposition"] == "SUCCEEDED"
    assert calls == [("simple", []), ("items", [2])]
    assert result["provider_results"][-1]["prompt_variant"] == "items"
    assert result["completed_task_ids"] == [task["task_id"] for task in tasks]


def test_google_document_acceleration_retry_sends_only_unresolved_pages(
    monkeypatch, tmp_path
) -> None:
    args, tasks, images = _acceleration_fixture(monkeypatch, tmp_path)
    for task in tasks:
        task["attempt_count"] = 2
    calls = []

    def command(argv, *, expected):
        pages = [
            int(argv[index + 1]) for index, value in enumerate(argv) if value == "--physical-page"
        ]
        calls.append(pages)
        return 0, {
            "disposition": "SUCCEEDED",
            "failed_pages": [],
            "page_image_sha256s": [{"image_sha256": images[2], "physical_page": 2}],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        }

    monkeypatch.setattr(target, "_command", command)
    monkeypatch.setattr(
        target,
        "_missing_current_default_pages_v1",
        lambda **_kwargs: [2],
    )
    manifests = [
        {
            "document_manifest_id": "gfdmv1:manifest:" + "2" * 64,
            "pages": [
                {"physical_page": page, "status": "FINANCIAL_NOTE_CONTENT"} for page in (1, 2, 3)
            ],
        }
    ]
    monkeypatch.setattr(
        target,
        "build_financial_document_manifest_v1",
        lambda *_a, **_k: manifests.pop(0),
    )
    monkeypatch.setattr(
        target,
        "build_current_document_manifest",
        lambda _args: {
            "document_manifest_id": "gfdmv1:manifest:" + "2" * 64,
            "selection_id": "gjfcdmsv1:selection:" + "1" * 64,
        },
    )
    monkeypatch.setattr(
        target,
        "transition_corpus_task_v1",
        lambda _ledger, **kwargs: {"task_id": kwargs["task_id"]},
    )
    result = target.accelerate_google_document(args)
    assert result["disposition"] == "SUCCEEDED"
    assert calls == [[2]]
    assert result["provider_results"][0]["physical_pages"] == [2]
    assert manifests == []


def test_missing_current_default_pages_accepts_only_typed_incomplete_frontier(
    monkeypatch, tmp_path
) -> None:
    calls = []

    def manifest(_database, **kwargs):
        page = kwargs["expected_physical_pages"][0]
        calls.append((page, kwargs["preferred_gateway_service_tiers"][0]["gateway"]))
        if page == 2:
            raise target.GeminiFinancialPageStoreV1Error(
                "document manifest page frontier is incomplete"
            )
        return {"pages": [{"physical_page": page}]}

    monkeypatch.setattr(target, "build_financial_document_manifest_v1", manifest)
    missing = target._missing_current_default_pages_v1(
        database=tmp_path / "store.sqlite3",
        task={"relative_path": "ACB/report.pdf", "source_sha256": "a" * 64},
        expected_pages=[1, 2, 3],
        current_images={page: str(page) * 64 for page in (1, 2, 3)},
        default_variant="simple",
    )
    assert missing == [2]
    assert calls == [(1, "OPENROUTER"), (2, "OPENROUTER"), (3, "OPENROUTER")]

    monkeypatch.setattr(
        target,
        "build_financial_document_manifest_v1",
        lambda *_a, **_k: (_ for _ in ()).throw(
            target.GeminiFinancialPageStoreV1Error("document manifest page frontier is duplicate")
        ),
    )
    with pytest.raises(target.GeminiFinancialPageStoreV1Error, match="duplicate"):
        target._missing_current_default_pages_v1(
            database=tmp_path / "store.sqlite3",
            task={"relative_path": "ACB/report.pdf", "source_sha256": "a" * 64},
            expected_pages=[1],
            current_images={1: "1" * 64},
            default_variant="simple",
        )


def test_all_pending_google_documents_are_smallest_first_and_require_complete_frontier(
    monkeypatch, tmp_path
) -> None:
    plan = {
        "documents": [
            {
                "document": {"page_count": 50, "relative_path": "B/large.pdf"},
                "document_plan_id": "document-large",
                "route": target.GOOGLE_ROUTE,
                "tasks": [{"task_id": "large-1"}, {"task_id": "large-2"}],
            },
            {
                "document": {"page_count": 20, "relative_path": "A/small.pdf"},
                "document_plan_id": "document-small",
                "route": target.GOOGLE_ROUTE,
                "tasks": [{"task_id": "small-1"}],
            },
            {
                "document": {"page_count": 30, "relative_path": "A/mixed.pdf"},
                "document_plan_id": "document-mixed",
                "route": target.GOOGLE_ROUTE,
                "tasks": [{"task_id": "mixed-1"}, {"task_id": "mixed-2"}],
            },
            {
                "document": {"page_count": 25, "relative_path": "A/resume.pdf"},
                "document_plan_id": "document-resume",
                "route": target.GOOGLE_ROUTE,
                "tasks": [{"task_id": "resume-1"}, {"task_id": "resume-2"}],
            },
            {
                "document": {"page_count": 10, "relative_path": "C/openrouter.pdf"},
                "document_plan_id": "document-openrouter",
                "route": target.OPENROUTER_ROUTE,
                "tasks": [{"task_id": "openrouter-1"}],
            },
        ]
    }
    monkeypatch.setattr(
        target,
        "list_corpus_tasks_v1",
        lambda *_a, **_k: [
            {"state": "PENDING", "task_id": "large-1"},
            {"state": "SUBMITTED", "task_id": "large-2"},
            {"state": "NEEDS_RETRY", "task_id": "small-1"},
            {"state": "NEEDS_RETRY", "task_id": "mixed-1"},
            {"state": "SUCCEEDED", "task_id": "mixed-2"},
            {"state": "RUNNING", "task_id": "resume-1"},
            {"state": "SUCCEEDED", "task_id": "resume-2"},
        ],
    )
    assert target._all_pending_google_documents_v1(
        plan=plan, ledger=tmp_path / "ledger.sqlite3"
    ) == [
        {
            "document_plan_id": "document-small",
            "document_page_count": 20,
            "relative_path": "A/small.pdf",
            "task_id": "small-1",
        },
        {
            "document_plan_id": "document-resume",
            "document_page_count": 25,
            "relative_path": "A/resume.pdf",
            "task_id": "resume-1",
        },
        {
            "document_plan_id": "document-mixed",
            "document_page_count": 30,
            "relative_path": "A/mixed.pdf",
            "task_id": "mixed-1",
        },
    ]


def test_accelerate_pending_google_documents_refreshes_after_each_document(
    monkeypatch, tmp_path
) -> None:
    args = Namespace(
        ledger=tmp_path / "ledger.sqlite3",
        max_documents=3,
        plan=tmp_path / "plan.json",
    )
    monkeypatch.setattr(target, "_plan", lambda _path: {"documents": []})
    frontiers = iter(
        [
            [{"document_page_count": 20, "relative_path": "a.pdf", "task_id": "task-a"}],
            [{"document_page_count": 30, "relative_path": "b.pdf", "task_id": "task-b"}],
            [],
        ]
    )
    monkeypatch.setattr(
        target, "_all_pending_google_documents_v1", lambda **_kwargs: next(frontiers)
    )
    calls = []

    def accelerate(document_args):
        calls.append(document_args.task_id)
        return {
            "disposition": "SUCCEEDED",
            "document_manifest_id": "manifest-" + document_args.task_id,
            "selection_id": "selection-" + document_args.task_id,
        }

    monkeypatch.setattr(target, "accelerate_google_document", accelerate)
    monkeypatch.setattr(target, "corpus_ledger_summary_v1", lambda _path: {"progress": []})
    result = target.accelerate_pending_google_documents(args)
    assert result["disposition"] == "SUCCEEDED"
    assert result["race_count"] == 0
    assert calls == ["task-a", "task-b"]
    assert [item["task_id"] for item in result["completed_documents"]] == calls


def test_accelerate_pending_google_documents_retries_one_claim_before_advancing(
    monkeypatch, tmp_path
) -> None:
    args = Namespace(
        ledger=tmp_path / "ledger.sqlite3",
        max_documents=1,
        plan=tmp_path / "plan.json",
    )
    monkeypatch.setattr(target, "_plan", lambda _path: {"documents": []})
    candidate = {
        "document_plan_id": "document-a",
        "document_page_count": 20,
        "relative_path": "a.pdf",
        "task_id": "task-a",
    }
    frontiers = iter([[candidate], [candidate], []])
    monkeypatch.setattr(
        target, "_all_pending_google_documents_v1", lambda **_kwargs: next(frontiers)
    )
    calls = []

    def accelerate(document_args):
        calls.append(document_args.task_id)
        if len(calls) == 1:
            return {"disposition": "NEEDS_RETRY"}
        return {
            "disposition": "SUCCEEDED",
            "document_manifest_id": "manifest-a",
            "selection_id": "selection-a",
        }

    monkeypatch.setattr(target, "accelerate_google_document", accelerate)
    monkeypatch.setattr(target, "corpus_ledger_summary_v1", lambda _path: {"progress": []})
    result = target.accelerate_pending_google_documents(args)
    assert result["disposition"] == "SUCCEEDED"
    assert result["retry_count"] == 1
    assert calls == ["task-a", "task-a"]
    assert [item["task_id"] for item in result["completed_documents"]] == ["task-a"]


@pytest.mark.parametrize("current_mode", ["accelerated", "revalidated"])
def test_finalize_google_manifests_reuses_selected_current_manifest(
    monkeypatch, tmp_path, current_mode
) -> None:
    source_sha256 = "a" * 64
    document_plan_id = "gjfpdocv1:" + "b" * 64
    relative_path = "HDB/report.pdf"
    plan = {
        "documents": [
            {
                "document": {
                    "page_count": 3,
                    "relative_path": relative_path,
                    "source_sha256": source_sha256,
                },
                "document_plan_id": document_plan_id,
                "route": target.GOOGLE_ROUTE,
                "tasks": [{"task_id": "task-1"}, {"task_id": "task-2"}],
            }
        ]
    }
    claim_id = (
        "gjfpaccelv1:claim:" + "c" * 64 if current_mode == "accelerated" else "batches/google-batch"
    )
    last_receipt = (
        None
        if current_mode == "accelerated"
        else json.dumps({"current_document_revalidated": True}).encode("utf-8")
    )
    monkeypatch.setattr(
        target,
        "list_corpus_tasks_v1",
        lambda _ledger: [
            {
                "last_receipt_json": last_receipt,
                "provider_job_ref": claim_id,
                "state": "SUCCEEDED",
                "task_id": "task-1",
            },
            {
                "last_receipt_json": last_receipt,
                "provider_job_ref": claim_id,
                "state": "SUCCEEDED",
                "task_id": "task-2",
            },
        ],
    )
    selected_manifest = tmp_path / "selected.json"
    selected_manifest.write_text(
        json.dumps(
            {
                "document": {
                    "source_logical_name": relative_path,
                    "source_sha256": source_sha256,
                },
                "page_count": 3,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        target,
        "load_current_document_manifest_selection_v1",
        lambda *_a, **_k: ({"selection_id": "selection"}, selected_manifest),
    )
    monkeypatch.setattr(
        target,
        "_command",
        lambda *_a, **_k: pytest.fail("accelerated selection must not rebuild a batch manifest"),
    )
    assert target._finalize_google_manifests(
        plan=plan,
        ledger=tmp_path / "ledger.sqlite3",
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
    ) == [str(selected_manifest)]


def test_corpus_document_replay_reuses_selected_manifest_and_rebuilds_from_store(
    monkeypatch, tmp_path
) -> None:
    prompt_sha = hashlib.sha256(
        target.build_financial_page_json_prompt_v1(variant="items").encode("utf-8")
    ).hexdigest()
    image_sha = "3" * 64
    page = {
        "canonical_json_sha256": "4" * 64,
        "image": {
            "height": 3508,
            "media_type": "image/png",
            "render_dpi": 300,
            "sha256": image_sha,
            "size_bytes": 1234,
            "width": 2480,
        },
        "physical_page": 1,
        "provider_route": {
            "gateway": "OPENROUTER",
            "requested_service_tier": "flex",
            "selected_provider": "Google",
        },
        "selected_service_tier": "flex",
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    material = {
        "document": {
            "source_logical_name": "ACB/report.pdf",
            "source_sha256": "2" * 64,
            "source_size_bytes": 200,
        },
        "extraction_contract": {
            "page_image_sha256s": [{"image_sha256": image_sha, "physical_page": 1}],
            "page_prompt_sha256s": [{"physical_page": 1, "prompt_sha256": prompt_sha}],
        },
        "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4",
        "page_count": 1,
        "pages": [page],
        "status_counts": {"FINANCIAL_NOTE_CONTENT": 1},
        "totals": {"cost_usd": "0.001000000000"},
    }
    manifest = {
        **material,
        "document_manifest_id": "gfdmv1:manifest:" + canonical_json_sha256_v1(material),
    }
    rebuilt_material = {
        **material,
        "extraction_contract": {
            **material["extraction_contract"],
            "preferred_gateway_service_tiers": target._preferred_gateway_service_tiers_v1(),
        },
    }
    rebuilt = {
        **rebuilt_material,
        "document_manifest_id": "gfdmv1:manifest:" + canonical_json_sha256_v1(rebuilt_material),
    }
    planned = {
        "document": {
            "page_count": 1,
            "relative_path": "ACB/report.pdf",
            "source_sha256": "2" * 64,
            "source_size_bytes": 200,
        },
        "document_plan_id": "gjfpdocv1:" + "1" * 64,
        "tasks": [{"task_id": "task-1"}],
    }
    document_root = tmp_path / "artifacts/documents" / ("1" * 64)
    manifest_relative = Path("current-document-manifests") / (
        manifest["document_manifest_id"].split(":", 2)[2] + ".json"
    )
    manifest_path = document_root / manifest_relative
    target._write_or_verify(manifest_path, canonical_json_bytes_v1(manifest) + b"\n")
    selection = target.build_current_document_manifest_selection_v1(
        document_plan_id=planned["document_plan_id"],
        source_sha256="2" * 64,
        document_manifest_id=manifest["document_manifest_id"],
        document_manifest_ref={
            "path": manifest_relative.as_posix(),
            "sha256": hashlib.sha256(canonical_json_bytes_v1(manifest) + b"\n").hexdigest(),
            "size_bytes": len(canonical_json_bytes_v1(manifest) + b"\n"),
        },
        page_image_frontier_sha256=canonical_json_sha256_v1(
            [{"image_sha256": image_sha, "physical_page": 1}]
        ),
        page_prompt_frontier_sha256=canonical_json_sha256_v1(
            [{"physical_page": 1, "prompt_variant": "items"}]
        ),
        prior_selection_ids=[],
    )
    selection_path = (
        document_root
        / "current-document-manifest-selections"
        / (selection["selection_id"].split(":", 2)[2] + ".json")
    )
    target._write_or_verify(selection_path, canonical_json_bytes_v1(selection) + b"\n")
    monkeypatch.setattr(
        target,
        "build_current_document_manifest",
        lambda *_args, **_kwargs: pytest.fail("selected adaptive manifest must be reused"),
    )
    monkeypatch.setattr(
        target,
        "_stored_page_image_sha256s_v1",
        lambda **_kwargs: {1: image_sha},
    )
    monkeypatch.setattr(
        target,
        "_manifest_extraction_frontier_v1",
        lambda **_kwargs: {
            "page_images": {1: image_sha},
            "prompt_sha256s": {1: prompt_sha},
            "variants": {1: "items"},
        },
    )
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: pytest.fail("corpus freeze must not render stored pages again"),
    )
    monkeypatch.setattr(target, "_source", lambda *_args, **_kwargs: tmp_path / "source.pdf")
    monkeypatch.setattr(
        target,
        "build_financial_document_manifest_v1",
        lambda *_args, **_kwargs: rebuilt,
    )
    record = target._replay_selected_document_for_corpus_v1(
        args=Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            ledger=tmp_path / "ledger.sqlite3",
            plan=tmp_path / "plan.json",
            source_root=tmp_path / "source",
        ),
        plan={"policy": {"dpi": 300}},
        planned=planned,
        task={"source_sha256": "2" * 64, "relative_path": "ACB/report.pdf"},
    )
    assert record["selection_id"] != selection["selection_id"]
    assert record["document_manifest_id"] == rebuilt["document_manifest_id"]
    assert record["page_status_counts"]["FINANCIAL_NOTE_CONTENT"] == 1
    assert record["provider_counts"] == [
        {
            "count": 1,
            "gateway": "OPENROUTER",
            "selected_provider": "Google",
            "selected_service_tier": "flex",
        }
    ]
    drifted_material = {
        **rebuilt_material,
        "extraction_contract": {
            **rebuilt_material["extraction_contract"],
            "page_image_sha256s": [{"image_sha256": "9" * 64, "physical_page": 1}],
        },
    }
    drifted = {
        **drifted_material,
        "document_manifest_id": "gfdmv1:manifest:" + canonical_json_sha256_v1(drifted_material),
    }
    monkeypatch.setattr(
        target,
        "build_financial_document_manifest_v1",
        lambda *_args, **_kwargs: drifted,
    )
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="does not replay exactly",
    ):
        target._replay_selected_document_for_corpus_v1(
            args=Namespace(
                artifact_root=tmp_path / "artifacts",
                database=tmp_path / "store.sqlite3",
                ledger=tmp_path / "ledger.sqlite3",
                plan=tmp_path / "plan.json",
                source_root=tmp_path / "source",
            ),
            plan={"policy": {"dpi": 300}},
            planned=planned,
            task={"source_sha256": "2" * 64, "relative_path": "ACB/report.pdf"},
        )


def test_corpus_document_replay_migrates_legacy_pointer_with_adaptive_prompt(
    monkeypatch, tmp_path
) -> None:
    prompt_sha = hashlib.sha256(
        target.build_financial_page_json_prompt_v1(variant="items").encode("utf-8")
    ).hexdigest()
    image_sha = "3" * 64
    planned = {
        "document": {
            "page_count": 1,
            "relative_path": "ACB/report.pdf",
            "source_sha256": "2" * 64,
            "source_size_bytes": 200,
        },
        "document_plan_id": "gjfpdocv1:" + "1" * 64,
        "tasks": [{"task_id": "task-1"}],
    }
    material = {
        "document": {
            "source_logical_name": "ACB/report.pdf",
            "source_sha256": "2" * 64,
            "source_size_bytes": 200,
        },
        "extraction_contract": {
            "page_image_sha256s": [{"image_sha256": image_sha, "physical_page": 1}],
            "page_prompt_sha256s": [{"physical_page": 1, "prompt_sha256": prompt_sha}],
            "preferred_gateway_service_tiers": target._preferred_gateway_service_tiers_v1(),
        },
        "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4",
        "page_count": 1,
        "pages": [
            {
                "canonical_json_sha256": "4" * 64,
                "image": {
                    "height": 3508,
                    "media_type": "image/png",
                    "render_dpi": 300,
                    "sha256": image_sha,
                    "size_bytes": 1234,
                    "width": 2480,
                },
                "physical_page": 1,
                "provider_route": {
                    "gateway": "OPENROUTER",
                    "requested_service_tier": "flex",
                    "selected_provider": "Google",
                },
                "selected_service_tier": "flex",
                "status": "FINANCIAL_NOTE_CONTENT",
            }
        ],
        "status_counts": {"FINANCIAL_NOTE_CONTENT": 1},
        "totals": {"cost_usd": "0.001000000000"},
    }
    manifest = {
        **material,
        "document_manifest_id": "gfdmv1:manifest:" + canonical_json_sha256_v1(material),
    }
    legacy_material = {
        **material,
        "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V3",
    }
    legacy_manifest = {
        **legacy_material,
        "document_manifest_id": "gfdmv1:manifest:" + canonical_json_sha256_v1(legacy_material),
    }
    document_root = tmp_path / "artifacts/documents" / ("1" * 64)
    legacy_path = document_root / "current-document-manifest.json"
    target._write_or_verify(legacy_path, canonical_json_bytes_v1(legacy_manifest) + b"\n")
    manifest_relative = Path("current-document-manifests") / (
        manifest["document_manifest_id"].split(":", 2)[2] + ".json"
    )
    manifest_path = document_root / manifest_relative
    target._write_or_verify(manifest_path, canonical_json_bytes_v1(manifest) + b"\n")
    selection = target.build_current_document_manifest_selection_v1(
        document_plan_id=planned["document_plan_id"],
        source_sha256="2" * 64,
        document_manifest_id=manifest["document_manifest_id"],
        document_manifest_ref={
            "path": manifest_relative.as_posix(),
            "sha256": hashlib.sha256(canonical_json_bytes_v1(manifest) + b"\n").hexdigest(),
            "size_bytes": len(canonical_json_bytes_v1(manifest) + b"\n"),
        },
        page_image_frontier_sha256=canonical_json_sha256_v1(
            [{"image_sha256": image_sha, "physical_page": 1}]
        ),
        page_prompt_frontier_sha256=canonical_json_sha256_v1(
            [{"physical_page": 1, "prompt_variant": "items"}]
        ),
        prior_selection_ids=[],
    )
    selection_path = (
        document_root
        / "current-document-manifest-selections"
        / (selection["selection_id"].split(":", 2)[2] + ".json")
    )
    target._write_or_verify(selection_path, canonical_json_bytes_v1(selection) + b"\n")
    loads = iter([None, (selection, manifest_path)])
    monkeypatch.setattr(
        target,
        "load_current_document_manifest_selection_v1",
        lambda *_a, **_k: next(loads),
    )
    captured = []

    def build(args):
        captured.append(args.page_prompt_variant)
        return {"disposition": "SUCCEEDED"}

    monkeypatch.setattr(target, "build_current_document_manifest", build)
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda *_a, **_k: {"prompt_variant": "simple"},
    )
    monkeypatch.setattr(
        target,
        "_stored_page_image_sha256s_v1",
        lambda **_kwargs: {1: image_sha},
    )
    monkeypatch.setattr(
        target,
        "_manifest_extraction_frontier_v1",
        lambda **_kwargs: {
            "page_images": {1: image_sha},
            "prompt_sha256s": {1: prompt_sha},
            "variants": {1: "items"},
        },
    )
    monkeypatch.setattr(
        target,
        "_current_page_image_sha256s_v1",
        lambda **_kwargs: pytest.fail("corpus freeze must not render stored pages again"),
    )
    monkeypatch.setattr(target, "_source", lambda *_args, **_kwargs: tmp_path / "source.pdf")
    monkeypatch.setattr(
        target,
        "build_financial_document_manifest_v1",
        lambda *_args, **_kwargs: manifest,
    )
    record = target._replay_selected_document_for_corpus_v1(
        args=Namespace(
            artifact_root=tmp_path / "artifacts",
            database=tmp_path / "store.sqlite3",
            ledger=tmp_path / "ledger.sqlite3",
            plan=tmp_path / "plan.json",
            source_root=tmp_path / "source",
        ),
        plan={"policy": {"dpi": 300}},
        planned=planned,
        task={"source_sha256": "2" * 64, "relative_path": "ACB/report.pdf"},
    )
    assert captured == [["1=items"]]
    assert record["selection_id"] == selection["selection_id"]


def test_receipt_bound_legacy_manifest_is_unique_and_content_exact(tmp_path) -> None:
    manifest_id = "gfdmv1:manifest:" + "1" * 64
    task = {
        "artifact_relative_path": "tasks/aa/task",
        "last_receipt_json": canonical_json_bytes_v1(
            {
                "document_manifest_id": manifest_id,
                "result": {"manifest_id": manifest_id},
            }
        ),
    }
    task_root = tmp_path / "artifacts/tasks/aa/task"
    task_root.mkdir(parents=True)
    manifest = {"document_manifest_id": manifest_id, "marker": "sealed"}
    (task_root / "mixed-prompt-document-manifest.json").write_bytes(
        canonical_json_bytes_v1(manifest) + b"\n"
    )
    assert (
        target._receipt_bound_legacy_document_manifest_v1(
            artifact_root=tmp_path / "artifacts", task=task
        )
        == manifest
    )

    duplicate = task_root / "nested/document-manifest-copy.json"
    duplicate.parent.mkdir()
    duplicate.write_bytes(canonical_json_bytes_v1(manifest) + b"\n")
    assert (
        target._receipt_bound_legacy_document_manifest_v1(
            artifact_root=tmp_path / "artifacts", task=task
        )
        == manifest
    )

    duplicate.write_bytes(canonical_json_bytes_v1({**manifest, "marker": "conflict"}) + b"\n")
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="conflicting manifests",
    ):
        target._receipt_bound_legacy_document_manifest_v1(
            artifact_root=tmp_path / "artifacts", task=task
        )


def test_legacy_v2_global_prompt_migrates_to_exact_page_frontier() -> None:
    prompt_sha = hashlib.sha256(
        target.build_financial_page_json_prompt_v1(variant="simple").encode("utf-8")
    ).hexdigest()
    manifest = {
        "extraction_contract": {"prompt_sha256": prompt_sha},
        "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V2",
        "page_count": 3,
    }
    assert target._prompt_variants_from_manifest_v1(manifest) == {
        1: "simple",
        2: "simple",
        3: "simple",
    }

    manifest["extraction_contract"]["prompt_sha256"] = "f" * 64
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="legacy document prompt",
    ):
        target._prompt_variants_from_manifest_v1(manifest)


def test_sqlite_snapshot_is_integrity_checked_immutable_and_single_link(tmp_path) -> None:
    source = tmp_path / "source.sqlite3"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE item(value TEXT NOT NULL)")
        connection.execute("INSERT INTO item VALUES ('sealed')")
    output, reference = target._sqlite_snapshot_v1(
        source=source,
        artifact_root=tmp_path / "artifacts",
        logical_name="store.sqlite3",
    )
    assert output.stat().st_mode & 0o777 == 0o444
    assert output.stat().st_nlink == 1
    assert hashlib.sha256(output.read_bytes()).hexdigest() == reference["sha256"]
    with sqlite3.connect(f"file:{output}?mode=ro", uri=True) as connection:
        assert connection.execute("SELECT value FROM item").fetchone()[0] == "sealed"


def test_current_corpus_manifest_requires_all_tasks_and_preserves_source_order(
    monkeypatch, tmp_path
) -> None:
    documents = []
    tasks = []
    for digit, path in (("1", "A/a.pdf"), ("2", "B/b.pdf")):
        task_id = "gjfptaskv1:" + digit * 64
        documents.append(
            {
                "document": {
                    "page_count": 1,
                    "relative_path": path,
                    "source_sha256": digit * 64,
                    "source_size_bytes": 100,
                },
                "document_plan_id": "gjfpdocv1:" + digit * 64,
                "tasks": [{"task_id": task_id}],
            }
        )
        tasks.append(
            {
                "document_plan_id": "gjfpdocv1:" + digit * 64,
                "state": "SUCCEEDED",
                "task_id": task_id,
            }
        )
    plan = {
        "corpus_plan_id": "gjfpcorpusv1:" + "a" * 64,
        "documents": documents,
        "summary": {"page_count": 2},
    }
    summary = {
        "corpus_plan_id": plan["corpus_plan_id"],
        "corpus_run_id": "gjfpcrunv1:" + "b" * 64,
        "documents": 2,
        "total_pages": 2,
    }
    monkeypatch.setattr(target, "_plan", lambda _path: plan)
    monkeypatch.setattr(target, "corpus_ledger_summary_v1", lambda _path: summary)
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda _path: tasks)
    replayed = []

    def replay(**kwargs):
        planned = kwargs["planned"]
        digit = planned["document_plan_id"][-1]
        replayed.append(planned["document"]["relative_path"])
        return {
            "document_manifest_id": "gfdmv1:manifest:" + digit * 64,
            "document_manifest_ref": {
                "path": f"documents/{digit}/manifest.json",
                "sha256": digit * 64,
                "size_bytes": 100,
            },
            "document_plan_id": planned["document_plan_id"],
            "page_count": 1,
            "page_json_frontier_sha256": digit * 64,
            "page_status_counts": {
                "FINANCIAL_NOTE_CONTENT": 1,
                "MIXED_FINANCIAL_CONTENT": 0,
                "NO_RELEVANT_FINANCIAL_CONTENT": 0,
                "PRIMARY_FINANCIAL_STATEMENT": 0,
            },
            "provider_counts": [
                {
                    "count": 1,
                    "gateway": "OPENROUTER",
                    "selected_provider": "Google",
                    "selected_service_tier": "flex",
                }
            ],
            "relative_path": planned["document"]["relative_path"],
            "selection_id": "gjfcdmsv1:selection:" + digit * 64,
            "selection_ref": {
                "path": f"documents/{digit}/selection.json",
                "sha256": digit * 64,
                "size_bytes": 100,
            },
            "source_sha256": digit * 64,
            "source_size_bytes": 100,
        }

    monkeypatch.setattr(target, "_replay_selected_document_for_corpus_v1", replay)

    def snapshot(*, source, artifact_root, logical_name):
        output = artifact_root / "current-corpus-freeze-inputs" / logical_name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(logical_name.encode())
        output.chmod(0o444)
        return output, target._artifact_content_ref_v1(artifact_root=artifact_root, path=output)

    monkeypatch.setattr(target, "_sqlite_snapshot_v1", snapshot)
    usage = {
        "attempts": [],
        "cached_input_tokens": 0,
        "input_tokens": 10,
        "output_tokens": 5,
        "run_count": 2,
        "thought_tokens": 0,
        "total_cost_usd": "0.001000000000",
    }
    monkeypatch.setattr(target, "usage_summary_v1", lambda _path: usage)
    args = Namespace(
        artifact_root=tmp_path / "artifacts",
        database=tmp_path / "store.sqlite3",
        ledger=tmp_path / "ledger.sqlite3",
        plan=tmp_path / "plan.json",
        source_root=tmp_path / "source",
    )
    result = target.build_current_corpus_manifest(args)
    assert result["disposition"] == "SUCCEEDED"
    assert result["document_count"] == 2
    assert result["page_count"] == 2
    assert replayed == ["A/a.pdf", "B/b.pdf"]
    assert Path(result["output"]).stat().st_mode & 0o777 == 0o444
    tasks[1]["state"] = "PENDING"
    with pytest.raises(
        target.RunGeminiJsonFirstCorpusSupervisorV1Error,
        match="fully succeeded ledger frontier",
    ):
        target.build_current_corpus_manifest(args)
