from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
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
