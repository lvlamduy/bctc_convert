from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from hashlib import sha256
from pathlib import Path

import fitz

from bctc_ai.evaluation.gemini_financial_page_json_v1 import (
    build_financial_page_json_prompt_v1,
    financial_page_json_response_schema_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
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
    assert preferred[:4] == [
        {"gateway": "OPENROUTER", "requested_service_tier": "flex"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-low"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-medium"},
        {"gateway": "AGY_CLI", "requested_service_tier": "agy-high"},
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
