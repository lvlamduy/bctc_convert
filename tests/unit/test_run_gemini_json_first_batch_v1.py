from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts/experiments/run_gemini_json_first_batch_v1.py"
_SPEC = importlib.util.spec_from_file_location("run_gemini_json_first_batch_v1", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
target = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target)


def test_submit_rejects_openrouter_image_batch_before_media_or_artifact_write(
    tmp_path,
) -> None:
    artifact_dir = tmp_path / "must-not-exist"
    with pytest.raises(
        target.RunGeminiJsonFirstBatchV1Error,
        match="OpenRouter Vertex Gemini Batch image transport is unsupported",
    ):
        target._submit(
            argparse.Namespace(
                artifact_dir=artifact_dir,
                provider="openrouter",
            )
        )
    assert not artifact_dir.exists()


def _write_batch_manifest(path: Path, pages: list[int], *, prompt: str = "p") -> None:
    path.mkdir()
    document = {
        "source_logical_name": "filing.pdf",
        "source_sha256": "a" * 64,
        "source_size_bytes": 123,
    }
    material = {
        "format_version": "GEMINI_JSON_FIRST_BATCH_RUN_V1",
        "prompt_sha256": prompt,
        "provider": "GOOGLE_GEMINI_BATCH_API",
        "requested_model": "gemini-3.7-flash",
        "requested_service_tier": "batch",
        "response_schema_sha256": "s",
        "requests": [
            {
                "document": document,
                "page": {
                    "image_sha256": format(page, "064x"),
                    "physical_page": page,
                },
                "request_id": f"page-{page}",
            }
            for page in pages
        ],
    }
    (path / "manifest.json").write_text(json.dumps(material))


def test_document_manifest_command_merges_disjoint_batches_in_page_order(
    tmp_path, monkeypatch
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_batch_manifest(first, [1, 2])
    _write_batch_manifest(second, [3])
    observed = {}

    def build(database, **kwargs):
        observed.update({"database": database, **kwargs})
        return {
            "document_manifest_id": "gfdmv1:manifest:ok",
            "page_count": 3,
            "status_counts": {"FINANCIAL_NOTE_CONTENT": 3},
            "totals": {"cost_usd": "0.01"},
        }

    monkeypatch.setattr(target, "build_financial_document_manifest_v1", build)
    output = tmp_path / "document-manifest.json"
    assert (
        target._document_manifest(
            argparse.Namespace(
                batch_artifact_dir=[second, first],
                database=tmp_path / "store.sqlite3",
                expected_page_count=3,
                output=output,
            )
        )
        == 0
    )
    assert observed["expected_physical_pages"] == [1, 2, 3]
    assert observed["source_sha256"] == "a" * 64
    assert observed["selected_provider"] == "GOOGLE_GEMINI_BATCH_API"
    assert json.loads(output.read_bytes())["document_manifest_id"] == "gfdmv1:manifest:ok"

    observed.clear()
    mixed_output = tmp_path / "mixed-document-manifest.json"
    assert (
        target._document_manifest(
            argparse.Namespace(
                allow_openrouter_fallback=True,
                batch_artifact_dir=[first, second],
                database=tmp_path / "store.sqlite3",
                expected_page_count=3,
                output=mixed_output,
            )
        )
        == 0
    )
    assert "selected_provider" not in observed
    assert observed["allowed_gateway_service_tiers"] == [
        {"gateway": "GOOGLE_GEMINI_BATCH_API", "requested_service_tier": "batch"},
        {"gateway": "OPENROUTER", "requested_service_tier": "flex"},
    ]


@pytest.mark.parametrize(
    ("second_pages", "second_prompt", "message"),
    [
        ([4], "p", "page frontier"),
        ([3], "different", "extraction contract"),
    ],
)
def test_document_manifest_command_rejects_overlap_or_contract_drift(
    tmp_path, second_pages, second_prompt, message
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_batch_manifest(first, [1, 2])
    _write_batch_manifest(second, second_pages, prompt=second_prompt)
    with pytest.raises(target.RunGeminiJsonFirstBatchV1Error, match=message):
        target._document_manifest(
            argparse.Namespace(
                batch_artifact_dir=[first, second],
                database=tmp_path / "store.sqlite3",
                expected_page_count=3,
                output=tmp_path / "document-manifest.json",
            )
        )


def test_document_manifest_allows_exact_retry_overlap_but_rejects_page_drift(
    tmp_path, monkeypatch
) -> None:
    first = tmp_path / "first"
    retry = tmp_path / "retry"
    second = tmp_path / "second"
    _write_batch_manifest(first, [1, 2])
    _write_batch_manifest(retry, [2])
    _write_batch_manifest(second, [3])
    monkeypatch.setattr(
        target,
        "build_financial_document_manifest_v1",
        lambda database, **kwargs: {
            "document_manifest_id": "gfdmv1:manifest:retry",
            "page_count": 3,
            "status_counts": {"FINANCIAL_NOTE_CONTENT": 3},
            "totals": {"cost_usd": "0.01"},
        },
    )
    args = argparse.Namespace(
        batch_artifact_dir=[first, retry, second],
        database=tmp_path / "store.sqlite3",
        expected_page_count=3,
        output=tmp_path / "document-manifest.json",
    )
    assert target._document_manifest(args) == 0

    retry_manifest = json.loads((retry / "manifest.json").read_text())
    retry_manifest["requests"][0]["page"]["image_sha256"] = "b" * 64
    (retry / "manifest.json").write_text(json.dumps(retry_manifest))
    args.output = tmp_path / "other-manifest.json"
    with pytest.raises(target.RunGeminiJsonFirstBatchV1Error, match="retried page binding"):
        target._document_manifest(args)


def test_register_existing_is_hash_bound_and_idempotent(tmp_path, monkeypatch, capsys) -> None:
    artifacts = tmp_path / "job"
    artifacts.mkdir()
    manifest = {
        "display_name": "one-document-part-1",
        "output_contract_mode": "JSON_SCHEMA",
        "prompt_sha256": "p",
        "prompt_variant": "balanced",
        "provider": "GOOGLE_GEMINI_BATCH_API",
        "requested_model": "gemini-3.7-flash",
        "requested_service_tier": "batch",
        "requests": [
            {
                "document": {
                    "source_logical_name": "filing.pdf",
                    "source_sha256": "a" * 64,
                    "source_size_bytes": 123,
                },
                "page": {"physical_page": 1},
                "provider_file_ref": None,
                "request_id": "page-1",
            }
        ],
        "response_schema_sha256": "s",
        "thinking_level": "low",
    }
    manifest_bytes = json.dumps(manifest).encode()
    submission_bytes = b'{"name":"batches/existing","metadata":{"state":"BATCH_STATE_PENDING"}}\n'
    (artifacts / "manifest.json").write_bytes(manifest_bytes)
    (artifacts / "submission-response.json").write_bytes(submission_bytes)
    receipt = {
        "batch_name": "batches/existing",
        "credential_slot": "GOOGLE_SLOT_2",
        "elapsed_seconds": "1.000",
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "provider": "GOOGLE_GEMINI_BATCH_API",
        "state": "BATCH_STATE_PENDING",
        "submission_response_sha256": hashlib.sha256(submission_bytes).hexdigest(),
    }
    (artifacts / "submission-receipt.json").write_text(json.dumps(receipt))
    observed = {}
    monkeypatch.setattr(
        target, "initialize_gemini_financial_page_store_v1", lambda path: path.touch()
    )
    monkeypatch.setattr(target, "batch_progress_v1", lambda path: observed.get("progress", []))

    def register(path, **kwargs):
        observed.update({"path": path, **kwargs})
        return "gfpstorev1:batch:existing"

    monkeypatch.setattr(target, "register_batch_submission_v1", register)
    args = argparse.Namespace(database=tmp_path / "store.sqlite3", artifact_dir=artifacts)
    assert target._register_existing(args) == 0
    assert observed["submission"].batch_name == "batches/existing"
    assert observed["requests"][0]["request_id"] == "page-1"
    assert json.loads(capsys.readouterr().out)["disposition"] == "REGISTERED_EXISTING"

    observed["progress"] = [
        {
            "batch_job_id": "gfpstorev1:batch:existing",
            "batch_name": "batches/existing",
            "credential_slot": "GOOGLE_SLOT_2",
            "provider": "GOOGLE_GEMINI_BATCH_API",
            "request_count": 1,
        }
    ]
    assert target._register_existing(args) == 0
    assert json.loads(capsys.readouterr().out)["disposition"] == "ALREADY_REGISTERED"

    receipt["manifest_sha256"] = "0" * 64
    (artifacts / "submission-receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(target.RunGeminiJsonFirstBatchV1Error, match="manifest hash"):
        target._register_existing(args)


@pytest.mark.parametrize(("failed_pages", "exit_code"), [(0, 0), (1, 2)])
def test_watch_stops_at_terminal_disposition(
    tmp_path, monkeypatch, capsys, failed_pages, exit_code
) -> None:
    artifacts = tmp_path / "job"
    artifacts.mkdir()
    (artifacts / "submission-receipt.json").write_text(json.dumps({"batch_name": "batches/one"}))
    polls = []
    monkeypatch.setattr(target, "_poll", lambda args: polls.append(args) or 0)
    monkeypatch.setattr(
        target,
        "batch_progress_v1",
        lambda path: [
            {
                "batch_name": "batches/one",
                "failed_pages": failed_pages,
                "state": "BATCH_STATE_SUCCEEDED",
            }
        ],
    )
    args = argparse.Namespace(
        artifact_dir=artifacts,
        database=tmp_path / "store.sqlite3",
        max_wait_seconds=60,
        poll_interval_seconds=1,
    )
    assert target._watch(args) == exit_code
    assert len(polls) == 1
    expected = "SUCCEEDED" if exit_code == 0 else "NEEDS_RETRY"
    assert json.loads(capsys.readouterr().out)["disposition"] == expected


def test_watch_has_bounded_wait(tmp_path, monkeypatch) -> None:
    artifacts = tmp_path / "job"
    artifacts.mkdir()
    (artifacts / "submission-receipt.json").write_text(json.dumps({"batch_name": "batches/one"}))
    monkeypatch.setattr(target, "_poll", lambda args: 0)
    monkeypatch.setattr(
        target,
        "batch_progress_v1",
        lambda path: [
            {
                "batch_name": "batches/one",
                "failed_pages": 0,
                "state": "BATCH_STATE_RUNNING",
            }
        ],
    )
    ticks = iter((0.0, 2.0))
    monkeypatch.setattr(target.time, "monotonic", lambda: next(ticks))
    args = argparse.Namespace(
        artifact_dir=artifacts,
        database=tmp_path / "store.sqlite3",
        max_wait_seconds=1,
        poll_interval_seconds=0.1,
    )
    with pytest.raises(target.RunGeminiJsonFirstBatchV1Error, match="bounded wait"):
        target._watch(args)
