from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/experiments/run_gemini_json_first_27bank_vertex_flex_v1.py"
SPEC = importlib.util.spec_from_file_location("run_27bank_2024_vertex_flex", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
target = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = target
SPEC.loader.exec_module(target)

BUNDLE = ROOT / "data/registered/gemini_json_first_27bank_2024_vertex_flex_expansion_v1.json"
PLAN = ROOT / "data/registered/gemini_json_first_27bank_2024_vertex_flex_corpus_plan_v1.json"
UNIVERSE = ROOT / "data/registered/bank_filing_universe_27bank_2024_v1.json"
PROTECTED = ROOT / (
    "data/registered/gemini_json_first_27bank_vertex_flex_vietnamese_only_expansion_v1.json"
)


def _args(tmp_path: Path, *, command: str = "run") -> Namespace:
    return Namespace(
        artifact_root=tmp_path / "artifacts",
        bundle=BUNDLE,
        command=command,
        database=tmp_path / "store.sqlite3",
        ledger=tmp_path / "ledger.sqlite3",
        max_fallback_attempts=2,
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=20,
        plan=PLAN,
        protected_2025_current_expansion=PROTECTED,
        protected_2025_current_ledger=tmp_path / "protected.sqlite3",
        provider_timeout_seconds=900,
        source_root=ROOT,
        universe=UNIVERSE,
    )


def _complete_protected_summary() -> dict[str, object]:
    return {
        "corpus_plan_id": "gjfpcorpusv1:186886f3792cb8e2402aeb3815c4469e1668dd6e2f4842f033b9d400f50acf41",
        "documents": 279,
        "progress": [
            {
                "pages": 15335,
                "route": "OPENROUTER_VERTEX_FLEX",
                "state": "SUCCEEDED",
                "tasks": 279,
            }
        ],
        "total_pages": 15335,
        "total_tasks": 279,
    }


def test_2024_run_is_openrouter_only_after_exact_protected_completion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    args = _args(tmp_path)
    args.protected_2025_current_ledger.write_bytes(b"one test ledger identity")
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: _complete_protected_summary(),
    )

    command = target._supervisor_command(args)

    assert command[2] == "run"
    assert command[-1] == "--openrouter-only"
    assert "--google-key-file" not in command
    assert "--universe" not in command
    assert "--protected-2025-current-expansion" not in command


def test_2024_run_fails_before_provider_when_protected_run_is_incomplete(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    args = _args(tmp_path)
    args.protected_2025_current_ledger.write_bytes(b"one incomplete ledger identity")
    incomplete = _complete_protected_summary()
    incomplete["progress"] = [
        {
            "pages": 1094,
            "route": "OPENROUTER_VERTEX_FLEX",
            "state": "SUCCEEDED",
            "tasks": 22,
        },
        {
            "pages": 14241,
            "route": "OPENROUTER_VERTEX_FLEX",
            "state": "PENDING",
            "tasks": 257,
        },
    ]
    monkeypatch.setattr(target, "corpus_ledger_summary_v1", lambda _ledger: incomplete)

    with pytest.raises(
        target.RunGeminiJsonFirst27BankVertexFlexV1Error,
        match="not completely successful",
    ):
        target._supervisor_command(args)


def test_2024_status_remains_read_only_without_a_protected_ledger(tmp_path: Path) -> None:
    args = _args(tmp_path, command="status")
    args.protected_2025_current_ledger = None

    command = target._supervisor_command(args)

    assert command[2] == "status"
    assert command[-2:] == ["--ledger", str(args.ledger)]
