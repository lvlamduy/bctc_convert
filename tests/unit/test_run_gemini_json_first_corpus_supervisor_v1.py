from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import (
    build_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts/experiments/run_gemini_json_first_corpus_supervisor_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "run_gemini_json_first_corpus_supervisor_v1", _SCRIPT
)
assert _SPEC is not None and _SPEC.loader is not None
target = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = target
_SPEC.loader.exec_module(target)


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
        openrouter_workers=20,
        provider_timeout_seconds=60,
        max_fallback_attempts=2,
    )
    assert result["state"] == "SUCCEEDED"
    assert [item["next_state"] for item in transitions] == [
        "FALLBACK_RUNNING",
        "SUCCEEDED",
    ]


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
    provider_result = {
        "cached_pages": [1, 2, 3],
        "disposition": "SUCCEEDED",
        "failed_pages": [],
        "ingested_pages": [],
        "manifest_id": "gfdmv1:manifest:" + "c" * 64,
        "offline_missing_pages": [],
        "semantic_failed_pages": [],
    }
    monkeypatch.setattr(target, "_command", lambda *_args, **_kwargs: (0, provider_result))
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


def test_openrouter_provider_retry_uses_only_item_frontier_and_seals_manifest(
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
        assert argv[argv.index("--prompt-variant") + 1] == "items"
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
    assert prompts[2] != prompts[1]
    assert manifests[0]["page_image_sha256s"] == {page: str(page) * 64 for page in (1, 2, 3)}
    final_receipt = transitions[-1]["receipt"]
    assert final_receipt["alternate_prompt_pages"] == [2]
    assert final_receipt["alternate_prompt_variant"] == "items"
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
        "document": {"page_count": 3},
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

    for prior in (
        {"failed_pages": [2, 2], "semantic_failed_pages": []},
        {"failed_pages": [0], "semantic_failed_pages": []},
        {"failed_pages": [2], "semantic_failed_pages": [3]},
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
