from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from hashlib import sha256
from pathlib import Path

import fitz
import pytest

from bctc_ai.evaluation.gemini_financial_page_json_v1 import (
    build_financial_page_json_prompt_v1,
    financial_page_json_response_schema_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    build_financial_document_manifest_v1,
    ingest_financial_page_extraction_v1,
    initialize_gemini_financial_page_store_v1,
)

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts/experiments/run_gemini_json_first_agy_document_v1.py"
_SPEC = importlib.util.spec_from_file_location("run_gemini_json_first_agy_document_v1", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
target = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = target
_SPEC.loader.exec_module(target)


def _page_json(status: str = "NO_RELEVANT_FINANCIAL_CONTENT") -> dict:
    return {
        "completion": {
            "all_relevant_content_transcribed": status != "UNRESOLVED_PAGE",
            "uncertainty_exact": [] if status != "UNRESOLVED_PAGE" else ["Chưa đọc đủ"],
        },
        "sections": [],
        "status": status,
    }


def _agy_envelope(page_json: dict, *, conversation: str) -> bytes:
    return json.dumps(
        {
            "conversation_id": conversation,
            "status": "SUCCESS",
            "structured_output": page_json,
            "usage": {
                "cache_read_tokens": 0,
                "input_tokens": 100,
                "output_tokens": 20,
                "thinking_tokens": 5,
                "total_tokens": 125,
            },
        },
        separators=(",", ":"),
    ).encode()


def _pdf(path: Path) -> tuple[str, int]:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Bao cao tai chinh")
    document.save(path)
    document.close()
    payload = path.read_bytes()
    return sha256(payload).hexdigest(), len(payload)


def test_checked_agy_envelope_uses_structured_output_not_display_response() -> None:
    raw = json.dumps(
        {
            "conversation_id": "conversation-1",
            "response": "display text that is not the contract",
            "status": "SUCCESS",
            "structured_output": _page_json(),
            "usage": {
                "cache_read_tokens": 2,
                "input_tokens": 100,
                "output_tokens": 20,
                "thinking_tokens": 5,
                "total_tokens": 127,
            },
        }
    ).encode()
    page_json, usage, conversation = target._checked_agy_envelope(raw)
    assert page_json == _page_json()
    assert usage["thinking_tokens"] == 5
    assert conversation == "conversation-1"


def test_agy_routes_prefer_flex_then_low_before_escalated_efforts() -> None:
    preferred = target._preferred_routes()
    assert preferred[:5] == [
        {"gateway": "OPENROUTER", "requested_service_tier": "flex"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-low"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-medium"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-high"},
        {"gateway": "CKEY_API", "requested_service_tier": "ckey-standard"},
    ]
    assert {tuple(sorted(route.items())) for route in preferred} == {
        tuple(sorted(route.items())) for route in target._routes()
    }


def test_page_escalates_only_after_unresolved_then_reuses_store(monkeypatch, tmp_path) -> None:
    pdf = tmp_path / "report.pdf"
    source_sha, source_size = _pdf(pdf)
    database = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    schema = financial_page_json_response_schema_v1()
    schema_path = tmp_path / "response-schema.json"
    schema_path.write_bytes(canonical_json_bytes_v1(schema))
    prompt = build_financial_page_json_prompt_v1(variant="simple")
    task = {
        "relative_path": "BANK/2025/report.pdf",
        "source_sha256": source_sha,
        "source_size_bytes": source_size,
    }
    calls: list[str] = []

    def call_agy(**kwargs):
        effort = kwargs["effort"]
        calls.append(effort)
        status = "UNRESOLVED_PAGE" if effort == "low" else "NO_RELEVANT_FINANCIAL_CONTENT"
        return _agy_envelope(_page_json(status), conversation=effort), b"", 1.25

    monkeypatch.setattr(target, "_call_agy", call_agy)
    outcome = target._process_page(
        task=task,
        source=pdf,
        database=database,
        artifact_root=tmp_path / "artifacts",
        agy_binary=tmp_path / "agy",
        dpi=300,
        prompt=prompt,
        prompt_sha256=sha256(prompt.encode()).hexdigest(),
        schema_path=schema_path,
        response_schema_sha256=canonical_json_sha256_v1(schema),
        timeout_seconds=60,
        physical_page=1,
    )
    assert calls == ["low", "medium"]
    assert outcome.disposition == "INGESTED"
    assert outcome.effort == "medium"
    with sqlite3.connect(database) as connection:
        stored = connection.execute(
            "SELECT requested_service_tier,thinking_level,selected_provider,selected_model "
            "FROM extraction_run"
        ).fetchone()
    assert stored == ("agy-medium", "medium", "Agy", "gemini-3.7-flash-medium")

    monkeypatch.setattr(
        target,
        "_call_agy",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("must reuse")),
    )
    replay = target._process_page(
        task=task,
        source=pdf,
        database=database,
        artifact_root=tmp_path / "artifacts",
        agy_binary=tmp_path / "agy",
        dpi=300,
        prompt=prompt,
        prompt_sha256=sha256(prompt.encode()).hexdigest(),
        schema_path=schema_path,
        response_schema_sha256=canonical_json_sha256_v1(schema),
        timeout_seconds=60,
        physical_page=1,
    )
    assert replay.disposition == "REUSED"


def test_page_outside_terminal_claim_cannot_reach_agy_provider(monkeypatch, tmp_path) -> None:
    pdf = tmp_path / "report.pdf"
    source_sha, source_size = _pdf(pdf)
    database = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    schema = financial_page_json_response_schema_v1()
    schema_path = tmp_path / "response-schema.json"
    schema_path.write_bytes(canonical_json_bytes_v1(schema))
    prompt = build_financial_page_json_prompt_v1(variant="simple")
    monkeypatch.setattr(
        target,
        "_call_agy",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("provider must not be called")),
    )
    with pytest.raises(
        target.RunGeminiJsonFirstAgyDocumentV1Error,
        match="outside its exact claimed page frontier",
    ):
        target._process_page(
            task={
                "relative_path": "BANK/2025/report.pdf",
                "source_sha256": source_sha,
                "source_size_bytes": source_size,
            },
            source=pdf,
            database=database,
            artifact_root=tmp_path / "artifacts",
            agy_binary=tmp_path / "agy",
            dpi=300,
            prompt=prompt,
            prompt_sha256=sha256(prompt.encode()).hexdigest(),
            schema_path=schema_path,
            response_schema_sha256=canonical_json_sha256_v1(schema),
            timeout_seconds=60,
            physical_page=1,
            provider_authorized=False,
        )


def test_unaccepted_page_image_drift_cannot_reach_agy_provider(monkeypatch, tmp_path) -> None:
    pdf = tmp_path / "report.pdf"
    source_sha, source_size = _pdf(pdf)
    database = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    schema = financial_page_json_response_schema_v1()
    schema_path = tmp_path / "response-schema.json"
    schema_path.write_bytes(canonical_json_bytes_v1(schema))
    prompt = build_financial_page_json_prompt_v1(variant="simple")
    monkeypatch.setattr(
        target,
        "_call_agy",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("provider must not be called")),
    )
    with pytest.raises(
        target._AgyPageImageIdentityV1Error,
        match="image changed after its atomic claim",
    ):
        target._process_page(
            task={
                "relative_path": "BANK/2025/report.pdf",
                "source_sha256": source_sha,
                "source_size_bytes": source_size,
            },
            source=pdf,
            database=database,
            artifact_root=tmp_path / "artifacts",
            agy_binary=tmp_path / "agy",
            dpi=300,
            prompt=prompt,
            prompt_sha256=sha256(prompt.encode()).hexdigest(),
            schema_path=schema_path,
            response_schema_sha256=canonical_json_sha256_v1(schema),
            timeout_seconds=60,
            physical_page=1,
            provider_authorized=True,
            expected_image_sha256="0" * 64,
        )


def test_unaccepted_queue_requires_two_canonical_flex_exhaustion_receipts(tmp_path) -> None:
    prior = canonical_json_bytes_v1(
        {
            "failed_pages": [2],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [2],
            "unresolved_pages": [],
        }
    )
    task = {
        "artifact_relative_path": "tasks/aa/task",
        "last_receipt_json": prior,
    }
    receipts = (
        tmp_path / task["artifact_relative_path"] / "openrouter-exhausted-page-repair" / "receipts"
    )
    receipts.mkdir(parents=True)

    def receipt(repair_attempt: int) -> dict:
        return {
            "disposition": "NEEDS_REPAIR",
            "failed_pages": [2],
            "format_version": "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V2",
            "prior_failed_receipt_sha256": sha256(prior).hexdigest(),
            "repair_attempt": repair_attempt,
        }

    (receipts / "attempt-01.json").write_bytes(canonical_json_bytes_v1(receipt(1)))
    with pytest.raises(
        target.RunGeminiJsonFirstAgyDocumentV1Error,
        match="bounded Flex history is incomplete",
    ):
        target._bounded_flex_exhaustion_evidence_v1(task=task, artifact_root=tmp_path)

    (receipts / "attempt-02.json").write_bytes(canonical_json_bytes_v1(receipt(2)))
    evidence = target._bounded_flex_exhaustion_evidence_v1(
        task=task,
        artifact_root=tmp_path,
    )
    assert [item["repair_attempt"] for item in evidence] == [1, 2]
    assert [item["failed_pages"] for item in evidence] == [[2], [2]]
    assert all(len(item["receipt_sha256"]) == 64 for item in evidence)

    (receipts / "attempt-02.json").write_text(
        json.dumps(receipt(2), indent=2),
        encoding="utf-8",
    )
    with pytest.raises(
        target.RunGeminiJsonFirstAgyDocumentV1Error,
        match="receipt binding is invalid",
    ):
        target._bounded_flex_exhaustion_evidence_v1(task=task, artifact_root=tmp_path)


def test_unaccepted_queue_accepts_one_structurally_terminal_balanced_receipt(tmp_path) -> None:
    prior = canonical_json_bytes_v1(
        {
            "failed_pages": [2, 3],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [2],
            "unresolved_pages": [],
        }
    )
    task = {
        "artifact_relative_path": "tasks/aa/task",
        "last_receipt_json": prior,
    }
    receipts = (
        tmp_path / task["artifact_relative_path"] / "openrouter-exhausted-page-repair" / "receipts"
    )
    receipts.mkdir(parents=True)
    receipt = {
        "disposition": "NEEDS_REPAIR",
        "failed_pages": [2, 3],
        "format_version": "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V2",
        "prior_failed_receipt_sha256": sha256(prior).hexdigest(),
        "provider_results": [
            {
                "physical_pages": [2, 3],
                "prompt_variant": "balanced",
                "result": {"semantic_failed_pages": [2]},
            }
        ],
        "repair_attempt": 1,
        "semantic_failed_pages": [2],
    }
    receipt_bytes = canonical_json_bytes_v1(receipt)
    (receipts / "attempt-01.json").write_bytes(receipt_bytes)

    evidence = target._bounded_flex_exhaustion_evidence_v1(
        task=task,
        artifact_root=tmp_path,
    )
    assert evidence == [
        {
            "balanced_semantic_failed_pages": [2],
            "disposition": "NEEDS_REPAIR",
            "exhaustion_kind": "BALANCED_SEMANTIC_RETRY_BLOCKS_SECOND_ATTEMPT",
            "failed_pages": [2, 3],
            "format_version": "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V2",
            "prior_failed_receipt_sha256": sha256(prior).hexdigest(),
            "receipt_sha256": sha256(receipt_bytes).hexdigest(),
            "repair_attempt": 1,
        }
    ]


def test_unaccepted_queue_uses_strict_legacy_source_bound_frontier(monkeypatch, tmp_path) -> None:
    prior = canonical_json_bytes_v1(
        {
            "disposition": "OPENROUTER_PROVIDER_SUBPROCESS_FAILURE",
            "provider_returncode": 1,
            "provider_stderr_bytes": 1,
            "provider_stderr_sha256": sha256(b"x").hexdigest(),
            "provider_stdout_bytes": 0,
            "provider_stdout_sha256": sha256(b"").hexdigest(),
            "retry_allowed": False,
        }
    )
    task = {
        "artifact_relative_path": "tasks/aa/task",
        "first_physical_page": 1,
        "last_physical_page": 2,
        "last_receipt_json": prior,
        "relative_path": "BANK/2025/legacy.pdf",
        "source_sha256": "a" * 64,
        "task_id": "gjfptaskv1:" + "b" * 64,
    }

    class Lock:
        closed = False

        def close(self):
            self.closed = True

    class Rendered:
        page = {"image_sha256": "e" * 64, "physical_page": 1}

    lock = Lock()
    captured = {}
    monkeypatch.setattr(target, "_superseded_source_identities_v1", lambda _path: {})
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda *_args, **_kwargs: [task])
    monkeypatch.setattr(
        target,
        "acquire_corpus_task_execution_lock_v1",
        lambda *_args, **_kwargs: lock,
    )
    monkeypatch.setattr(target, "_source", lambda *_args, **_kwargs: tmp_path / "legacy.pdf")
    monkeypatch.setattr(
        target,
        "_source_bound_store_frontier_v1",
        lambda **_kwargs: {
            "failed_pages": [1],
            "format_version": "GEMINI_JSON_FIRST_SOURCE_BOUND_STORE_FRONTIER_V1",
            "semantic_failure_artifact_pages": [1],
            "source_logical_name": task["relative_path"],
            "source_sha256": task["source_sha256"],
            "stored_pages": [2],
        },
    )
    monkeypatch.setattr(
        target,
        "openrouter_failed_task_repair_frontier_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            target.GeminiJsonFirstCorpusLedgerV1Error(
                "OpenRouter repair subprocess event chain is invalid"
            )
        ),
    )
    monkeypatch.setattr(
        target,
        "_bounded_flex_exhaustion_evidence_v1",
        lambda **_kwargs: [
            {"failed_pages": [1], "receipt_sha256": "c" * 64},
            {"failed_pages": [1], "receipt_sha256": "d" * 64},
        ],
    )
    monkeypatch.setattr(target, "_render_page", lambda *_args, **_kwargs: Rendered())
    monkeypatch.setattr(
        target,
        "_failure_evidence_sha256s_v1",
        lambda **_kwargs: [sha256(prior).hexdigest(), "c" * 64, "d" * 64],
    )

    def claim(*_args, **kwargs):
        captured.update(kwargs)
        return {**task, "state": "SUBMITTED"}

    monkeypatch.setattr(
        target,
        "claim_exhausted_openrouter_unaccepted_pages_for_agy_v1",
        claim,
    )
    claimed, returned_lock = target._claim_unaccepted_task_with_execution_lock_v1(
        ledger=tmp_path / "ledger.sqlite3",
        source_root=tmp_path,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path,
        source_revision_registry=tmp_path / "revisions.json",
        dpi=300,
        task_id=task["task_id"],
    )
    assert claimed["state"] == "SUBMITTED"
    assert returned_lock is lock
    assert captured["source_bound_store_frontier"]["failed_pages"] == [1]
    assert captured["page_evidence"] == [
        {
            "failure_evidence_sha256s": [sha256(prior).hexdigest(), "c" * 64, "d" * 64],
            "failure_kind": "SEMANTIC_NO_ACCEPTED_JSON",
            "image_sha256": "e" * 64,
            "physical_page": 1,
        }
    ]
    returned_lock.close()


def test_unaccepted_queue_render_failure_never_claims_or_calls_provider(
    monkeypatch, tmp_path
) -> None:
    task = {
        "artifact_relative_path": "tasks/aa/task",
        "first_physical_page": 1,
        "last_physical_page": 1,
        "last_receipt_json": canonical_json_bytes_v1(
            {
                "failed_pages": [1],
                "recitation_failed_pages": [],
                "semantic_failed_pages": [1],
                "unresolved_pages": [],
            }
        ),
        "relative_path": "BANK/2025/report.pdf",
        "source_sha256": "a" * 64,
        "task_id": "gjfptaskv1:" + "b" * 64,
    }

    class Lock:
        closed = False

        def close(self):
            self.closed = True

    lock = Lock()
    monkeypatch.setattr(target, "_superseded_source_identities_v1", lambda _path: {})
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda *_args, **_kwargs: [task])
    monkeypatch.setattr(
        target,
        "acquire_corpus_task_execution_lock_v1",
        lambda *_args, **_kwargs: lock,
    )
    monkeypatch.setattr(target, "_source", lambda *_args, **_kwargs: tmp_path / "report.pdf")
    monkeypatch.setattr(
        target,
        "_source_bound_store_frontier_v1",
        lambda **_kwargs: {
            "failed_pages": [1],
            "format_version": "GEMINI_JSON_FIRST_SOURCE_BOUND_STORE_FRONTIER_V1",
            "semantic_failure_artifact_pages": [1],
            "source_logical_name": task["relative_path"],
            "source_sha256": task["source_sha256"],
            "stored_pages": [],
        },
    )
    monkeypatch.setattr(
        target,
        "openrouter_failed_task_repair_frontier_v1",
        lambda *_args, **_kwargs: {
            "failed_pages": [1],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [1],
            "unresolved_pages": [],
        },
    )
    monkeypatch.setattr(
        target,
        "_bounded_flex_exhaustion_evidence_v1",
        lambda **_kwargs: [{"failed_pages": [1]}, {"failed_pages": [1]}],
    )
    monkeypatch.setattr(
        target,
        "_render_page",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            target.GeminiJsonFirstPageRenderV1Error("cropped source")
        ),
    )
    monkeypatch.setattr(
        target,
        "claim_exhausted_openrouter_unaccepted_pages_for_agy_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("render failure must not create a provider lease")
        ),
    )
    monkeypatch.setattr(
        target,
        "_call_agy",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("provider must not be called")),
    )
    with pytest.raises(
        target.RunGeminiJsonFirstAgyDocumentV1Error,
        match="no authenticated exhausted no-JSON task",
    ):
        target._claim_unaccepted_task_with_execution_lock_v1(
            ledger=tmp_path / "ledger.sqlite3",
            source_root=tmp_path,
            database=tmp_path / "store.sqlite3",
            artifact_root=tmp_path,
            source_revision_registry=tmp_path / "revisions.json",
            dpi=300,
            task_id=None,
        )
    assert lock.closed


def _source_render_recovery_task() -> dict:
    provider_job_ref = "agyjobv1:" + "c" * 64
    task_id = "gjfptaskv1:" + "b" * 64
    return {
        "artifact_relative_path": "tasks/aa/source-render",
        "first_physical_page": 1,
        "last_physical_page": 3,
        "last_receipt_json": canonical_json_bytes_v1(
            {
                "disposition": "AGY_TERMINAL_PROVIDER_REPAIR_FAILED",
                "failed_pages": [1, 2],
                "format_version": "GEMINI_JSON_FIRST_AGY_DOCUMENT_RUNNER_V1",
                "provider_failed_pages": [2],
                "provider_job_ref": provider_job_ref,
                "recitation_failed_pages": [],
                "semantic_failed_pages": [],
                "source_failed_pages": [1],
                "task_id": task_id,
                "unresolved_pages": [1],
            }
        ),
        "provider_job_ref": provider_job_ref,
        "relative_path": "BANK/2025/source-render.pdf",
        "source_sha256": "a" * 64,
        "task_id": task_id,
    }


def test_source_render_recovery_renders_exact_frontier_before_atomic_claim(
    monkeypatch, tmp_path
) -> None:
    task = _source_render_recovery_task()

    class Lock:
        closed = False

        def close(self):
            self.closed = True

    lock = Lock()
    events = []
    monkeypatch.setattr(target, "_superseded_source_identities_v1", lambda _path: {})
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda *_args, **_kwargs: [task])
    monkeypatch.setattr(
        target,
        "acquire_corpus_task_execution_lock_v1",
        lambda *_args, **_kwargs: lock,
    )
    monkeypatch.setattr(target, "_source", lambda *_args, **_kwargs: tmp_path / "source.pdf")
    monkeypatch.setattr(
        target,
        "_source_bound_store_frontier_v1",
        lambda **_kwargs: {
            "failed_pages": [1, 2],
            "format_version": "GEMINI_JSON_FIRST_SOURCE_BOUND_STORE_FRONTIER_V1",
            "semantic_failure_artifact_pages": [],
            "source_logical_name": task["relative_path"],
            "source_sha256": task["source_sha256"],
            "stored_pages": [3],
        },
    )

    def render(_source, *, physical_page, **_kwargs):
        events.append(("render", physical_page))
        return target._RenderedPage(
            image=f"image-{physical_page}".encode(),
            page={"image_sha256": str(physical_page) * 64, "physical_page": physical_page},
            receipt={"physical_page": physical_page, "rendered": True},
        )

    monkeypatch.setattr(target, "_render_page", render)
    prior_sha = sha256(task["last_receipt_json"]).hexdigest()
    monkeypatch.setattr(
        target,
        "_failure_evidence_sha256s_v1",
        lambda **_kwargs: [prior_sha],
    )
    captured = {}

    def claim(*_args, **kwargs):
        events.append(("claim", tuple(kwargs["source_bound_store_frontier"]["failed_pages"])))
        captured.update(kwargs)
        return {**task, "state": "SUBMITTED"}

    monkeypatch.setattr(target, "claim_source_render_repaired_pages_for_agy_v1", claim)
    claimed, returned_lock = target._claim_source_render_recovery_with_execution_lock_v1(
        ledger=tmp_path / "ledger.sqlite3",
        source_root=tmp_path,
        database=tmp_path / "store.sqlite3",
        artifact_root=tmp_path / "artifacts",
        source_revision_registry=tmp_path / "revisions.json",
        dpi=300,
        task_id=task["task_id"],
    )
    assert claimed["state"] == "SUBMITTED"
    assert returned_lock is lock
    assert events == [("render", 1), ("render", 2), ("claim", (1, 2))]
    assert [item["physical_page"] for item in captured["local_render_repair_evidence"]] == [1]
    assert [item["failure_kind"] for item in captured["page_evidence"]] == [
        "LOCAL_RENDER_REPAIRED",
        "PROVIDER_NO_ACCEPTED_JSON",
    ]
    assert all(len(item["failure_evidence_sha256s"]) >= 2 for item in captured["page_evidence"])
    returned_lock.close()


def test_source_render_recovery_render_failure_creates_no_claim_or_provider_call(
    monkeypatch, tmp_path
) -> None:
    task = _source_render_recovery_task()

    class Lock:
        closed = False

        def close(self):
            self.closed = True

    lock = Lock()
    monkeypatch.setattr(target, "_superseded_source_identities_v1", lambda _path: {})
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda *_args, **_kwargs: [task])
    monkeypatch.setattr(
        target,
        "acquire_corpus_task_execution_lock_v1",
        lambda *_args, **_kwargs: lock,
    )
    monkeypatch.setattr(target, "_source", lambda *_args, **_kwargs: tmp_path / "source.pdf")
    monkeypatch.setattr(
        target,
        "_source_bound_store_frontier_v1",
        lambda **_kwargs: {
            "failed_pages": [1, 2],
            "format_version": "GEMINI_JSON_FIRST_SOURCE_BOUND_STORE_FRONTIER_V1",
            "semantic_failure_artifact_pages": [],
            "source_logical_name": task["relative_path"],
            "source_sha256": task["source_sha256"],
            "stored_pages": [3],
        },
    )
    monkeypatch.setattr(
        target,
        "_render_page",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            target.GeminiJsonFirstPageRenderV1Error("still cropped")
        ),
    )
    monkeypatch.setattr(
        target,
        "claim_source_render_repaired_pages_for_agy_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("render failure must not create a provider lease")
        ),
    )
    monkeypatch.setattr(
        target,
        "_call_agy",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("provider must not be called")),
    )
    with pytest.raises(target.RunGeminiJsonFirstAgyDocumentV1Error, match="still cropped"):
        target._claim_source_render_recovery_with_execution_lock_v1(
            ledger=tmp_path / "ledger.sqlite3",
            source_root=tmp_path,
            database=tmp_path / "store.sqlite3",
            artifact_root=tmp_path / "artifacts",
            source_revision_registry=tmp_path / "revisions.json",
            dpi=300,
            task_id=task["task_id"],
        )
    assert lock.closed


def test_source_render_recovery_superseded_source_creates_no_claim_or_provider_call(
    monkeypatch, tmp_path
) -> None:
    task = _source_render_recovery_task()

    class Lock:
        def close(self):
            pass

    monkeypatch.setattr(
        target,
        "_superseded_source_identities_v1",
        lambda _path: {task["relative_path"]: task["source_sha256"]},
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda *_args, **_kwargs: [task])
    monkeypatch.setattr(
        target,
        "acquire_corpus_task_execution_lock_v1",
        lambda *_args, **_kwargs: Lock(),
    )
    monkeypatch.setattr(
        target,
        "_render_page",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("superseded source must not render")
        ),
    )
    monkeypatch.setattr(
        target,
        "claim_source_render_repaired_pages_for_agy_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("superseded source must not create a lease")
        ),
    )
    monkeypatch.setattr(
        target,
        "_call_agy",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("provider must not be called")),
    )
    with pytest.raises(
        target.RunGeminiJsonFirstAgyDocumentV1Error,
        match="refused a superseded source identity",
    ):
        target._claim_source_render_recovery_with_execution_lock_v1(
            ledger=tmp_path / "ledger.sqlite3",
            source_root=tmp_path,
            database=tmp_path / "store.sqlite3",
            artifact_root=tmp_path / "artifacts",
            source_revision_registry=tmp_path / "revisions.json",
            dpi=300,
            task_id=task["task_id"],
        )


def test_source_render_recovery_image_mismatch_never_calls_agy_provider(
    monkeypatch, tmp_path
) -> None:
    pdf = tmp_path / "report.pdf"
    source_sha, source_size = _pdf(pdf)
    database = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    schema = financial_page_json_response_schema_v1()
    schema_path = tmp_path / "response-schema.json"
    schema_path.write_bytes(canonical_json_bytes_v1(schema))
    prompt = build_financial_page_json_prompt_v1(variant="simple")
    monkeypatch.setattr(
        target,
        "_call_agy",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("provider must not be called")),
    )
    with pytest.raises(target._AgyPageImageIdentityV1Error, match="atomic claim"):
        target._process_page(
            task={
                "relative_path": "BANK/2025/report.pdf",
                "source_sha256": source_sha,
                "source_size_bytes": source_size,
            },
            source=pdf,
            database=database,
            artifact_root=tmp_path / "artifacts",
            agy_binary=tmp_path / "agy",
            dpi=300,
            prompt=prompt,
            prompt_sha256=sha256(prompt.encode()).hexdigest(),
            schema_path=schema_path,
            response_schema_sha256=canonical_json_sha256_v1(schema),
            timeout_seconds=60,
            physical_page=1,
            provider_authorized=True,
            expected_image_sha256="0" * 64,
        )


def test_source_render_recovery_flag_is_mutually_exclusive_with_other_repairs() -> None:
    with pytest.raises(SystemExit):
        target._parser().parse_args(
            [
                "--plan",
                "plan.json",
                "--ledger",
                "ledger.sqlite3",
                "--source-root",
                "source",
                "--database",
                "store.sqlite3",
                "--artifact-root",
                "artifacts",
                "--source-render-recovery",
                "--terminal-provider-repair",
            ]
        )


def test_orientation_repair_rotation_is_deterministic_and_receipt_bound(tmp_path) -> None:
    pdf = tmp_path / "page.pdf"
    source_sha, _source_size = _pdf(pdf)
    original = target._render_page(
        pdf,
        physical_page=1,
        dpi=300,
        source_sha256=source_sha,
    )
    first = target._rotate_rendered_page_v1(
        original,
        source_sha256=source_sha,
        physical_page=1,
        clockwise_degrees=90,
    )
    second = target._rotate_rendered_page_v1(
        original,
        source_sha256=source_sha,
        physical_page=1,
        clockwise_degrees=90,
    )
    assert first.image == second.image
    assert first.page["image_sha256"] == sha256(first.image).hexdigest()
    assert first.page["pixel_width"] == original.page["pixel_height"]
    assert first.page["pixel_height"] == original.page["pixel_width"]
    assert first.receipt["base_image_sha256"] == original.page["image_sha256"]
    assert first.receipt["clockwise_degrees"] == 90
    assert first.receipt["format_version"] == (
        "GEMINI_JSON_FIRST_AGY_ORIENTATION_REPAIRED_RENDER_V1"
    )
    with pytest.raises(target.RunGeminiJsonFirstAgyDocumentV1Error, match="rotation is invalid"):
        target._rotate_rendered_page_v1(
            original,
            source_sha256=source_sha,
            physical_page=1,
            clockwise_degrees=180,
        )


def test_orientation_repair_registry_is_exact_and_rejects_implicit_policy(tmp_path) -> None:
    path = tmp_path / "orientation.json"
    entry = {
        "clockwise_degrees": 90,
        "corrected_image_sha256": "b" * 64,
        "original_image_sha256": "a" * 64,
        "physical_page": 46,
        "reason": "sideways scan verified",
        "source_logical_name": "BVB/2025/report.pdf",
        "source_sha256": "c" * 64,
    }
    registry = {
        "format_version": "GEMINI_JSON_FIRST_AGY_ORIENTATION_REPAIR_REGISTRY_V1",
        "policy": {
            "exact_source_page_only": True,
            "implicit_orientation_detection": False,
        },
        "repairs": [entry],
    }
    path.write_bytes(canonical_json_bytes_v1(registry))
    assert target._orientation_repairs_v1(path) == {("BVB/2025/report.pdf", "c" * 64, 46): entry}
    registry["policy"]["implicit_orientation_detection"] = True
    path.write_bytes(canonical_json_bytes_v1(registry))
    with pytest.raises(target.RunGeminiJsonFirstAgyDocumentV1Error, match="registry is invalid"):
        target._orientation_repairs_v1(path)


def test_schema_alignment_registry_and_prior_attempt_evidence_are_exact(tmp_path) -> None:
    registry_path = tmp_path / "alignment.json"
    entry = {
        "image_sha256": "a" * 64,
        "physical_page": 23,
        "reason": "verified eight-column continuation",
        "repair_instruction": "Do not call tools. Emit eight values per row.",
        "source_logical_name": "VBB/2025/report.pdf",
        "source_sha256": "b" * 64,
    }
    registry = {
        "format_version": "GEMINI_JSON_FIRST_AGY_SCHEMA_ALIGNMENT_REPAIR_REGISTRY_V1",
        "policy": {
            "exact_source_page_only": True,
            "implicit_alignment_hints": False,
            "tools_forbidden": True,
        },
        "repairs": [entry],
    }
    registry_path.write_bytes(canonical_json_bytes_v1(registry))
    assert target._schema_alignment_repairs_v1(registry_path) == {
        ("VBB/2025/report.pdf", "b" * 64, 23): entry
    }
    registry["policy"]["tools_forbidden"] = False
    registry_path.write_bytes(canonical_json_bytes_v1(registry))
    with pytest.raises(target.RunGeminiJsonFirstAgyDocumentV1Error, match="registry is invalid"):
        target._schema_alignment_repairs_v1(registry_path)

    task = {"artifact_relative_path": "tasks/aa/task"}
    root = tmp_path / task["artifact_relative_path"] / "agy-exhausted-unaccepted-repair"
    for effort in target.EFFORT_ORDER:
        effort_root = root / "page-00023" / f"effort-{effort}"
        effort_root.mkdir(parents=True)
        message = {
            "low": "row values do not align with table value columns",
            "medium": "Agy successful envelope lacks structured output or usage",
            "high": "Agy did not return a successful envelope",
        }[effort]
        (effort_root / "failure.json").write_bytes(
            canonical_json_bytes_v1(
                {
                    "error_message": message,
                    "error_type": "Error",
                    "failure_kind": "AGY_PROVIDER_OR_SCHEMA_FAILED",
                }
            )
        )
        (effort_root / "invocation.json").write_bytes(
            canonical_json_bytes_v1(
                {
                    "effort": effort,
                    "format_version": target.FORMAT_VERSION,
                    "image_sha256": "a" * 64,
                    "model": target.AGY_MODEL_BY_EFFORT[effort],
                }
            )
        )
        response = {
            "response": "{}" if effort == "low" else "",
            "status": "CANCELED" if effort == "high" else "SUCCESS",
        }
        if effort == "low":
            response["structured_output"] = {"invalid": "alignment"}
        (effort_root / "agy-response.json").write_bytes(canonical_json_bytes_v1(response))
        (effort_root / "agy-stderr.log").write_text(
            "" if effort == "low" else "headless mode cannot prompt; command auto-denied",
            encoding="utf-8",
        )
    evidence = target._schema_alignment_attempt_evidence_v1(
        task=task,
        artifact_root=tmp_path,
        physical_page=23,
        image_sha256="a" * 64,
    )
    assert [item["failure_kind"] for item in evidence] == [
        "ROW_COLUMN_ALIGNMENT",
        "COMMAND_TOOL_DENIED",
        "COMMAND_TOOL_DENIED",
    ]
    (root / "page-00023" / "effort-low" / "failure.json").write_bytes(
        canonical_json_bytes_v1(
            {
                "error_message": "different failure",
                "error_type": "Error",
                "failure_kind": "AGY_PROVIDER_OR_SCHEMA_FAILED",
            }
        )
    )
    with pytest.raises(
        target.RunGeminiJsonFirstAgyDocumentV1Error,
        match="prior-attempt evidence is not exact",
    ):
        target._schema_alignment_attempt_evidence_v1(
            task=task,
            artifact_root=tmp_path,
            physical_page=23,
            image_sha256="a" * 64,
        )


def test_orientation_recovery_authenticates_all_three_command_denials(tmp_path) -> None:
    task = {"artifact_relative_path": "tasks/aa/task"}
    root = tmp_path / task["artifact_relative_path"] / "agy-exhausted-unaccepted-repair"
    for effort in target.EFFORT_ORDER:
        effort_root = root / "page-00046" / f"effort-{effort}"
        effort_root.mkdir(parents=True)
        (effort_root / "failure.json").write_bytes(
            canonical_json_bytes_v1(
                {
                    "error_message": "Agy successful envelope lacks structured output or usage",
                    "error_type": "RunGeminiJsonFirstAgyDocumentV1Error",
                    "failure_kind": "AGY_PROVIDER_OR_SCHEMA_FAILED",
                }
            )
        )
        (effort_root / "invocation.json").write_bytes(
            canonical_json_bytes_v1(
                {
                    "effort": effort,
                    "format_version": target.FORMAT_VERSION,
                    "image_sha256": "a" * 64,
                    "model": target.AGY_MODEL_BY_EFFORT[effort],
                }
            )
        )
        (effort_root / "agy-response.json").write_bytes(
            canonical_json_bytes_v1(
                {
                    "denied_actions": [{"action": "command", "display_name": "RunCommand"}],
                    "response": "",
                    "status": "SUCCESS",
                    "usage": {"total_tokens": 1},
                }
            )
        )
        (effort_root / "agy-stderr.log").write_text(
            "headless mode cannot prompt, therefore command was auto-denied",
            encoding="utf-8",
        )
    evidence = target._tool_denied_rotation_evidence_v1(
        task=task,
        artifact_root=tmp_path,
        physical_pages=[46],
        original_image_sha256s={46: "a" * 64},
    )
    assert [(item["physical_page"], item["effort"]) for item in evidence] == [
        (46, "low"),
        (46, "medium"),
        (46, "high"),
    ]
    response = root / "page-00046" / "effort-high" / "agy-response.json"
    response.write_bytes(
        canonical_json_bytes_v1(
            {
                "denied_actions": [],
                "response": "",
                "status": "SUCCESS",
            }
        )
    )
    with pytest.raises(
        target.RunGeminiJsonFirstAgyDocumentV1Error,
        match="not an exact command-tool denial",
    ):
        target._tool_denied_rotation_evidence_v1(
            task=task,
            artifact_root=tmp_path,
            physical_pages=[46],
            original_image_sha256s={46: "a" * 64},
        )


def test_orientation_recovery_image_registry_drift_never_claims_or_calls_provider(
    monkeypatch, tmp_path
) -> None:
    task = _source_render_recovery_task()
    task["last_receipt_json"] = canonical_json_bytes_v1(
        {
            "disposition": "AGY_EXHAUSTED_UNACCEPTED_REPAIR_FAILED",
            "format_version": target.FORMAT_VERSION,
        }
    )

    class Lock:
        closed = False

        def close(self):
            self.closed = True

    lock = Lock()
    monkeypatch.setattr(target, "_superseded_source_identities_v1", lambda _path: {})
    monkeypatch.setattr(
        target,
        "_orientation_repairs_v1",
        lambda _path: {
            (task["relative_path"], task["source_sha256"], 1): {
                "clockwise_degrees": 90,
                "corrected_image_sha256": "f" * 64,
                "original_image_sha256": "a" * 64,
                "physical_page": 1,
            }
        },
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda *_args, **_kwargs: [task])
    monkeypatch.setattr(
        target,
        "acquire_corpus_task_execution_lock_v1",
        lambda *_args, **_kwargs: lock,
    )
    monkeypatch.setattr(target, "_source", lambda *_args, **_kwargs: tmp_path / "source.pdf")
    monkeypatch.setattr(
        target,
        "_source_bound_store_frontier_v1",
        lambda **_kwargs: {
            "failed_pages": [1],
            "format_version": "GEMINI_JSON_FIRST_SOURCE_BOUND_STORE_FRONTIER_V1",
            "semantic_failure_artifact_pages": [],
            "source_logical_name": task["relative_path"],
            "source_sha256": task["source_sha256"],
            "stored_pages": [2, 3],
        },
    )
    monkeypatch.setattr(
        target,
        "_render_page",
        lambda *_args, **_kwargs: target._RenderedPage(
            image=b"not-used",
            page={"image_sha256": "e" * 64},
            receipt={"render": True},
        ),
    )
    monkeypatch.setattr(
        target,
        "claim_agy_tool_denied_orientation_repaired_pages_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("image drift must not create a claim")
        ),
    )
    monkeypatch.setattr(
        target,
        "_call_agy",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("provider must not be called")),
    )
    with pytest.raises(
        target.RunGeminiJsonFirstAgyDocumentV1Error,
        match="original image identity drifted",
    ):
        target._claim_tool_denied_orientation_recovery_with_execution_lock_v1(
            ledger=tmp_path / "ledger.sqlite3",
            source_root=tmp_path,
            database=tmp_path / "store.sqlite3",
            artifact_root=tmp_path,
            source_revision_registry=tmp_path / "revisions.json",
            orientation_repair_registry=tmp_path / "orientation.json",
            dpi=300,
            task_id=task["task_id"],
        )
    assert lock.closed


def test_page_reuses_authenticated_items_variant_without_second_agy_call(
    monkeypatch, tmp_path
) -> None:
    pdf = tmp_path / "report.pdf"
    source_sha, source_size = _pdf(pdf)
    database = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    schema = financial_page_json_response_schema_v1()
    schema_sha256 = canonical_json_sha256_v1(schema)
    schema_path = tmp_path / "response-schema.json"
    schema_path.write_bytes(canonical_json_bytes_v1(schema))
    simple_prompt = build_financial_page_json_prompt_v1(variant="simple")
    items_prompt = build_financial_page_json_prompt_v1(variant="items")
    task = {
        "relative_path": "BANK/2025/report.pdf",
        "source_sha256": source_sha,
        "source_size_bytes": source_size,
    }
    rendered = target._render_page(
        pdf,
        physical_page=1,
        dpi=300,
        source_sha256=source_sha,
    )
    page_json = _page_json()
    provider_result = target._provider_result(
        raw=_agy_envelope(page_json, conversation="existing-items"),
        page_json=page_json,
        usage={
            "cache_read_tokens": 0,
            "input_tokens": 100,
            "output_tokens": 20,
            "thinking_tokens": 5,
            "total_tokens": 125,
        },
        conversation_id="existing-items",
        effort="low",
        elapsed=0.5,
    )
    ingest_financial_page_extraction_v1(
        database,
        document={
            "source_logical_name": task["relative_path"],
            "source_sha256": source_sha,
            "source_size_bytes": source_size,
        },
        page=rendered.page,
        prompt_variant="items",
        output_contract_mode="JSON_SCHEMA",
        prompt_sha256=sha256(items_prompt.encode()).hexdigest(),
        response_schema_sha256=schema_sha256,
        requested_model=target.GOOGLE_MODEL,
        requested_service_tier="agy-low",
        thinking_level="low",
        provider_result=provider_result,
        page_json=page_json,
    )
    monkeypatch.setattr(
        target,
        "_call_agy",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("must reuse items page")),
    )
    outcome = target._process_page(
        task=task,
        source=pdf,
        database=database,
        artifact_root=tmp_path / "artifacts",
        agy_binary=tmp_path / "agy",
        dpi=300,
        prompt=simple_prompt,
        prompt_sha256=sha256(simple_prompt.encode()).hexdigest(),
        schema_path=schema_path,
        response_schema_sha256=schema_sha256,
        timeout_seconds=60,
        physical_page=1,
    )
    assert outcome.disposition == "REUSED"
    assert outcome.prompt_variant == "items"
    manifest = build_financial_document_manifest_v1(
        database,
        source_sha256=source_sha,
        source_logical_name=task["relative_path"],
        expected_physical_pages=[1],
        page_image_sha256s={1: rendered.page["image_sha256"]},
        prompt_sha256={1: sha256(items_prompt.encode()).hexdigest()},
        response_schema_sha256=schema_sha256,
        requested_model=target.GOOGLE_MODEL,
        allowed_gateway_service_tiers=target._routes(),
        preferred_gateway_service_tiers=target._preferred_routes(),
    )
    assert manifest["page_count"] == 1


def test_low_success_never_calls_medium_or_high(monkeypatch, tmp_path) -> None:
    pdf = tmp_path / "report.pdf"
    source_sha, source_size = _pdf(pdf)
    database = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    schema = financial_page_json_response_schema_v1()
    schema_path = tmp_path / "response-schema.json"
    schema_path.write_bytes(canonical_json_bytes_v1(schema))
    prompt = build_financial_page_json_prompt_v1(variant="simple")
    calls = []

    def call_agy(**kwargs):
        calls.append(kwargs["effort"])
        return _agy_envelope(_page_json(), conversation="low-ok"), b"", 0.5

    monkeypatch.setattr(target, "_call_agy", call_agy)
    outcome = target._process_page(
        task={
            "relative_path": "BANK/2025/report.pdf",
            "source_sha256": source_sha,
            "source_size_bytes": source_size,
        },
        source=pdf,
        database=database,
        artifact_root=tmp_path / "artifacts",
        agy_binary=tmp_path / "agy",
        dpi=300,
        prompt=prompt,
        prompt_sha256=sha256(prompt.encode()).hexdigest(),
        schema_path=schema_path,
        response_schema_sha256=canonical_json_sha256_v1(schema),
        timeout_seconds=60,
        physical_page=1,
    )
    assert calls == ["low"]
    assert outcome.effort == "low"
