from __future__ import annotations

import importlib.util
import json
import sys
import threading
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import fitz
import pytest

from bctc_ai.evaluation.gemini_financial_page_json_v1 import (
    build_financial_page_json_prompt_v1,
    financial_page_json_response_schema_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    initialize_gemini_financial_page_store_v1,
)

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts/experiments/run_gemini_json_first_ckey_document_v1.py"
_SPEC = importlib.util.spec_from_file_location("run_gemini_json_first_ckey_document_v1", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
target = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = target
_SPEC.loader.exec_module(target)

_OPENROUTER_SCRIPT = _ROOT / "scripts/experiments/run_gemini_json_first_openrouter_document_v1.py"
_OPENROUTER_SPEC = importlib.util.spec_from_file_location(
    "run_gemini_json_first_openrouter_document_for_ckey_test_v1", _OPENROUTER_SCRIPT
)
assert _OPENROUTER_SPEC is not None and _OPENROUTER_SPEC.loader is not None
openrouter_target = importlib.util.module_from_spec(_OPENROUTER_SPEC)
sys.modules[_OPENROUTER_SPEC.name] = openrouter_target
_OPENROUTER_SPEC.loader.exec_module(openrouter_target)

_PAID_MODELS = (
    "provider-a/gemini-3.7-flash",
    "provider-b/gemini-3.7-flash",
)


def _page_json(status: str = "NO_RELEVANT_FINANCIAL_CONTENT") -> dict:
    return {
        "completion": {
            "all_relevant_content_transcribed": status != "UNRESOLVED_PAGE",
            "uncertainty_exact": [] if status != "UNRESOLVED_PAGE" else ["Chưa đọc đủ"],
        },
        "sections": [],
        "status": status,
    }


def _response(page_json: dict, *, fenced: bool = False) -> bytes:
    content = json.dumps(page_json, ensure_ascii=False, separators=(",", ":"))
    if fenced:
        content = "```json\n" + content + "\n```"
    return json.dumps(
        {
            "choices": [
                {"finish_reason": "stop", "message": {"content": content, "role": "assistant"}}
            ],
            "id": "chatcmpl-ckey-1",
            "model": "provider-a/gemini-3.7-flash",
            "usage": {
                "completion_tokens": 20,
                "prompt_tokens": 100,
                "total_tokens": 120,
                "x_ckey": {"cost": 1.3, "request_id": "req-1"},
            },
        },
        ensure_ascii=False,
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


def test_ckey_decoder_accepts_direct_or_one_bounded_fence_only() -> None:
    direct = json.dumps(_page_json(), separators=(",", ":"))
    assert target._decode_ckey_content(direct) == _page_json()
    assert target._decode_ckey_content("```json\n" + direct + "\n```") == _page_json()
    with pytest.raises(target.RunGeminiJsonFirstCkeyDocumentV1Error, match="neither direct"):
        target._decode_ckey_content("Lời dẫn\n```json\n" + direct + "\n```")
    with pytest.raises(target.RunGeminiJsonFirstCkeyDocumentV1Error, match="neither direct"):
        target._decode_ckey_content("```json\n" + direct + "\n```\n```json\n{}\n```")


def test_checked_response_preserves_actual_vnd_cost_and_explicit_conversion() -> None:
    page, usage, response_id, model = target._checked_ckey_response(
        _response(_page_json(), fenced=True), vnd_per_usd=Decimal("26000")
    )
    assert page == _page_json()
    assert usage["actual_cost_vnd"] == "1.3"
    assert usage["actual_cost_usd"] == "0.000050000000"
    assert usage["billing_disposition"] == "BILLED_ACTUAL_VND_WITH_CONFIGURED_USD_CONVERSION"
    assert response_id == "chatcmpl-ckey-1"
    assert model == "provider-a/gemini-3.7-flash"


def test_scope_is_locked_to_2025_current() -> None:
    assert target._report_year("vietstock_bctc/ABC/2025/a.pdf") == 2025
    with pytest.raises(target.RunGeminiJsonFirstCkeyDocumentV1Error, match="2025-current"):
        target._report_year("vietstock_bctc/ABC/2024/a.pdf")


def test_ckey_requires_an_explicit_unique_paid_gemini_37_pool() -> None:
    assert target._checked_paid_model_pool_v1(_PAID_MODELS) == _PAID_MODELS
    for models in (
        None,
        (),
        ("provider/gemini-flash-3.7free",),
        ("provider/gemini-3.8-flash",),
        ("provider/other-3.7",),
        (_PAID_MODELS[0], _PAID_MODELS[0]),
    ):
        with pytest.raises(
            target.RunGeminiJsonFirstCkeyDocumentV1Error,
            match="unique paid Gemini 3.7 routes",
        ):
            target._checked_paid_model_pool_v1(models)


def test_page_ingests_valid_fenced_json_then_reuses_without_resend(monkeypatch, tmp_path) -> None:
    pdf = tmp_path / "report.pdf"
    source_sha, source_size = _pdf(pdf)
    database = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    prompt = build_financial_page_json_prompt_v1(variant="simple")
    schema = financial_page_json_response_schema_v1()
    calls = []

    def call_ckey(**kwargs):
        calls.append(kwargs["model"])
        return _response(_page_json(), fenced=True), 0.25

    monkeypatch.setattr(target, "_call_ckey", call_ckey)
    kwargs = {
        "task": {
            "relative_path": "BANK/2025/report.pdf",
            "source_sha256": source_sha,
            "source_size_bytes": source_size,
        },
        "source": pdf,
        "database": database,
        "artifact_root": tmp_path / "artifacts",
        "api_key": "sk-test-key-long-enough",
        "models": _PAID_MODELS,
        "dpi": 300,
        "prompt": prompt,
        "prompt_sha256": sha256(prompt.encode()).hexdigest(),
        "schema": schema,
        "response_schema_sha256": canonical_json_sha256_v1(schema),
        "timeout_seconds": 60,
        "page_attempts": 2,
        "retry_delay_seconds": 0,
        "vnd_per_usd": Decimal("26000"),
        "page_cost_cap_vnd": Decimal("50"),
        "circuit_open": threading.Event(),
        "physical_page": 1,
    }
    result = target._process_page(**kwargs)
    assert result.disposition == "INGESTED"
    assert result.cost_vnd == "1.3"
    assert calls == [_PAID_MODELS[0]]

    rendered = target._render_page(pdf, physical_page=1, dpi=300, source_sha256=source_sha)
    cross_provider = openrouter_target._cross_provider_cached_page_json_v1(
        database,
        source_sha256=source_sha,
        source_logical_name="BANK/2025/report.pdf",
        physical_page=1,
        image_sha256=rendered.page["image_sha256"],
        prompt_sha256=kwargs["prompt_sha256"],
        response_schema_sha256=kwargs["response_schema_sha256"],
    )
    assert cross_provider == _page_json()

    monkeypatch.setattr(
        target,
        "_call_ckey",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("must reuse CKey page")),
    )
    replay = target._process_page(**kwargs)
    assert replay.disposition == "REUSED"


def test_provider_circuit_opens_after_rate_limited_pool_is_exhausted(monkeypatch, tmp_path) -> None:
    pdf = tmp_path / "report.pdf"
    source_sha, source_size = _pdf(pdf)
    database = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    prompt = build_financial_page_json_prompt_v1(variant="simple")
    schema = financial_page_json_response_schema_v1()
    calls = []

    def call_ckey(**_kwargs):
        calls.append(1)
        raise target._CKeyHttpError(429, b'{"error":"rate limited"}')

    monkeypatch.setattr(target, "_call_ckey", call_ckey)
    circuit = threading.Event()
    result = target._process_page(
        task={
            "relative_path": "BANK/2025/report.pdf",
            "source_sha256": source_sha,
            "source_size_bytes": source_size,
        },
        source=pdf,
        database=database,
        artifact_root=tmp_path / "artifacts",
        api_key="sk-test-key-long-enough",
        models=_PAID_MODELS,
        dpi=300,
        prompt=prompt,
        prompt_sha256=sha256(prompt.encode()).hexdigest(),
        schema=schema,
        response_schema_sha256=canonical_json_sha256_v1(schema),
        timeout_seconds=60,
        page_attempts=3,
        retry_delay_seconds=0,
        vnd_per_usd=Decimal("26000"),
        page_cost_cap_vnd=Decimal("50"),
        circuit_open=circuit,
        physical_page=1,
    )
    assert result.disposition == "FAILED"
    assert result.failure_kind == "CKEY_PROVIDER_CIRCUIT_OPEN"
    assert circuit.is_set()
    assert calls == [1, 1, 1]


def test_provider_price_change_falls_through_to_next_model(monkeypatch, tmp_path) -> None:
    pdf = tmp_path / "report.pdf"
    source_sha, source_size = _pdf(pdf)
    database = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    prompt = build_financial_page_json_prompt_v1(variant="simple")
    schema = financial_page_json_response_schema_v1()
    calls = []

    def call_ckey(**kwargs):
        calls.append(kwargs["model"])
        if len(calls) == 1:
            raise target._CKeyHttpError(402, b'{"error":"price changed"}')
        return _response(_page_json()), 0.25

    monkeypatch.setattr(target, "_call_ckey", call_ckey)
    circuit = threading.Event()
    result = target._process_page(
        task={
            "relative_path": "BANK/2025/report.pdf",
            "source_sha256": source_sha,
            "source_size_bytes": source_size,
        },
        source=pdf,
        database=database,
        artifact_root=tmp_path / "artifacts",
        api_key="sk-test-key-long-enough",
        models=_PAID_MODELS,
        dpi=300,
        prompt=prompt,
        prompt_sha256=sha256(prompt.encode()).hexdigest(),
        schema=schema,
        response_schema_sha256=canonical_json_sha256_v1(schema),
        timeout_seconds=60,
        page_attempts=3,
        retry_delay_seconds=0,
        vnd_per_usd=Decimal("26000"),
        page_cost_cap_vnd=Decimal("50"),
        circuit_open=circuit,
        physical_page=1,
    )
    assert result.disposition == "INGESTED"
    assert not circuit.is_set()
    assert calls == list(_PAID_MODELS[:2])
