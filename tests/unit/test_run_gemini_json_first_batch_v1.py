from __future__ import annotations

import argparse
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
                "page": {"physical_page": page},
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


@pytest.mark.parametrize(
    ("second_pages", "second_prompt", "message"),
    [
        ([2, 3], "p", "page frontier"),
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
