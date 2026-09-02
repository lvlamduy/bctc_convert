from __future__ import annotations

import importlib.util
import json
import sys
from argparse import Namespace
from hashlib import sha256
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_first_vertex_flex_expansion_v1 import (
    build_gemini_json_first_vertex_flex_expansion_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/experiments/run_gemini_json_first_27bank_vertex_flex_v1.py"
SPEC = importlib.util.spec_from_file_location("run_27bank_vertex_flex", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
target = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = target
SPEC.loader.exec_module(target)


def _files(tmp_path: Path) -> tuple[Path, Path]:
    processed = ["ACB", "BID", "CTG", "HDB", "MBB", "VCB", "VIB", "VPB"]
    new = [f"N{ordinal:02d}" for ordinal in range(1, 20)]
    filings = [
        {
            "bank": bank,
            "content_ref": {
                "path": f"vietstock_bctc/{bank}/2025/report.pdf",
                "sha256": f"{ordinal:064x}",
                "size_bytes": 100,
            },
            "filename_hints_non_authoritative": {},
            "page_count": 1,
            "provider_disposition": (
                "REUSE_EXISTING_GEMINI_JSON" if bank in processed else "NEW_VERTEX_FLEX_FRONTIER"
            ),
            "source_authentication_flags": [],
            "year": 2025,
        }
        for ordinal, bank in enumerate(sorted([*processed, *new]), start=1)
    ]
    universe = {
        "already_processed_bank_codes": processed,
        "already_processed_corpus_ref": {
            "bank_codes": processed,
            "document_count": 8,
            "manifest_index_id": "gjfccmiv1:index:" + "c" * 64,
            "page_count": 8,
        },
        "authenticated_universe_id": "bankfilingauthv1:" + "a" * 64,
        "filings": filings,
        "format_version": "BANK_FILING_UNIVERSE_27BANK_2025_CURRENT_V1",
        "local_source_authentication": {
            "all_content_sha256_verified": True,
            "all_pdf_signatures_verified": True,
            "all_sources_regular_nonsymlink_files": True,
            "page_count_engine": "PYMUPDF_DOCUMENT_PAGE_COUNT",
        },
        "new_bank_codes": new,
        "summary": {
            "already_processed_bank_count": 8,
            "bank_count": 27,
            "candidate_filing_count": 27,
            "candidate_page_count": 27,
            "new_bank_count": 19,
            "provider_call_candidate_filing_count": 19,
            "provider_call_candidate_page_count": 19,
        },
    }
    manifest = {
        "corpus_manifest_index_id": "gjfccmiv1:index:" + "c" * 64,
        "documents": [
            {
                "relative_path": f"vietstock_bctc/{bank}/2025/old-report.pdf",
                "source_sha256": f"{ordinal + 100:064x}",
            }
            for ordinal, bank in enumerate(processed, start=1)
        ],
        "format_version": "GEMINI_CURRENT_CORPUS_MANIFEST_INDEX_V1",
        "summary": {"document_count": 8, "page_count": 8},
    }
    bundle = build_gemini_json_first_vertex_flex_expansion_v1(
        universe,
        already_processed_corpus_manifest_index=manifest,
    )
    bundle_path = tmp_path / "bundle.json"
    plan_path = tmp_path / "plan.json"
    bundle_path.write_bytes(canonical_json_bytes_v1(bundle) + b"\n")
    plan_path.write_bytes(canonical_json_bytes_v1(bundle["corpus_plan"]) + b"\n")
    return bundle_path, plan_path


def test_run_command_always_includes_openrouter_only_and_no_provider_override(
    tmp_path: Path,
) -> None:
    bundle, plan = _files(tmp_path)
    args = Namespace(
        artifact_root=tmp_path / "artifacts",
        bundle=bundle,
        command="run",
        database=tmp_path / "store.sqlite3",
        ledger=tmp_path / "ledger.sqlite3",
        max_fallback_attempts=2,
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=20,
        plan=plan,
        provider_timeout_seconds=900,
        source_root=tmp_path / "sources",
    )

    command = target._supervisor_command(args)

    assert command[-1] == "--openrouter-only"
    assert "--google-key-file" not in command
    assert "--google-standard-mode" not in command
    assert command[command.index("--openrouter-key-file") + 1] == str(tmp_path / "openrouter")


def test_run_one_targets_one_task_and_remains_openrouter_only(tmp_path: Path) -> None:
    bundle, plan = _files(tmp_path)
    task_id = "gjfptaskv1:" + "f" * 64
    args = Namespace(
        artifact_root=tmp_path / "artifacts",
        bundle=bundle,
        command="run-one",
        database=tmp_path / "store.sqlite3",
        ledger=tmp_path / "ledger.sqlite3",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=20,
        plan=plan,
        provider_timeout_seconds=900,
        source_root=tmp_path / "sources",
        task_id=task_id,
    )

    command = target._supervisor_command(args)

    assert command[2] == "run-openrouter-task"
    assert command[command.index("--task-id") + 1] == task_id
    assert command[-1] == "--openrouter-only"
    assert "--google-key-file" not in command


def test_terminal_retry_recovers_exact_failed_page_variants() -> None:
    failed, variants = target._retry_prompt_variants(
        {
            "adaptive_retry_results": [
                {"physical_pages": [3], "prompt_variant": "items", "result": {}},
            ],
            "alternate_prompt_variants": [
                {"physical_pages": [2], "prompt_variant": "scope"},
            ],
            "failed_pages": [2, 3],
        },
        document_page_count=4,
        default_variant="simple",
    )

    assert failed == [2, 3]
    assert variants == {1: "simple", 2: "scope", 3: "items", 4: "simple"}


def test_terminal_retry_rejects_an_out_of_document_page() -> None:
    with pytest.raises(
        target.RunGeminiJsonFirst27BankVertexFlexV1Error,
        match="terminal page frontier",
    ):
        target._retry_prompt_variants(
            {"failed_pages": [4]},
            document_page_count=3,
            default_variant="simple",
        )


def test_repair_one_calls_only_failed_pages_and_seals_mixed_prompt_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source_root = tmp_path / "sources"
    relative_path = "vietstock_bctc/N01/2025/report.pdf"
    source = source_root / relative_path
    source.parent.mkdir(parents=True)
    source.write_bytes(b"one authenticated PDF")
    task_id = "gjfptaskv1:" + "f" * 64
    receipt = {
        "adaptive_retry_results": [
            {"physical_pages": [3], "prompt_variant": "items", "result": {}},
        ],
        "alternate_prompt_variants": [
            {"physical_pages": [3], "prompt_variant": "items"},
        ],
        "failed_pages": [2, 3],
    }
    task = {
        "artifact_relative_path": "tasks/ff/task",
        "document_page_count": 4,
        "last_receipt_json": json.dumps(receipt).encode(),
        "relative_path": relative_path,
        "route": target.OPENROUTER_ROUTE,
        "source_sha256": sha256(source.read_bytes()).hexdigest(),
        "source_size_bytes": source.stat().st_size,
        "state": "FAILED",
        "task_id": task_id,
    }
    monkeypatch.setattr(
        target,
        "_load_bundle_and_plan",
        lambda _bundle, _plan: {
            "corpus_plan": {
                "corpus_plan_id": "plan-1",
                "policy": {"dpi": 300},
            }
        },
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1", "prompt_variant": "simple"},
    )
    monkeypatch.setattr(target, "list_corpus_tasks_v1", lambda _ledger: [task])
    commands: list[list[str]] = []

    def fake_command(
        command: list[str], *, environment: dict[str, str], expected: set[int]
    ) -> tuple[int, dict[str, object]]:
        assert environment["PYTHONPATH"]
        commands.append(command)
        if "document-manifest-current" in command:
            assert expected == {0}
            return 0, {
                "disposition": "SUCCEEDED",
                "document_manifest_id": "gfdmv1:manifest:" + "a" * 64,
            }
        pages = [
            int(command[index + 1])
            for index, value in enumerate(command)
            if value == "--physical-page"
        ]
        assert expected == {0, 2}
        return 0, {"disposition": "SUCCEEDED", "failed_pages": [], "pages": pages}

    monkeypatch.setattr(target, "_json_subprocess", fake_command)
    args = Namespace(
        artifact_root=tmp_path / "artifacts",
        bundle=tmp_path / "bundle.json",
        command="repair-one",
        database=tmp_path / "store.sqlite3",
        ledger=tmp_path / "ledger.sqlite3",
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=4,
        plan=tmp_path / "plan.json",
        provider_timeout_seconds=900,
        source_root=source_root,
        task_id=task_id,
    )

    result = target._repair_one(args, environment={"PYTHONPATH": "src"})

    assert result["disposition"] == "SUCCEEDED"
    provider_commands = [command for command in commands if "--physical-page" in command]
    assert len(provider_commands) == 2
    assert {
        tuple(
            int(command[index + 1])
            for index, value in enumerate(command)
            if value == "--physical-page"
        )
        for command in provider_commands
    } == {(2,), (3,)}
    assert all("--google-key-file" not in command for command in provider_commands)
    assert all(
        command[command.index("--google-standard-mode") + 1] == "disabled"
        for command in provider_commands
    )
    manifest_command = commands[-1]
    assert manifest_command[manifest_command.index("--page-prompt-variant") + 1] == "3=items"


def test_repair_all_waits_for_a_fully_terminal_main_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        target,
        "_load_bundle_and_plan",
        lambda _bundle, _plan: {"corpus_plan": {"corpus_plan_id": "plan-1"}},
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1"},
    )
    monkeypatch.setattr(
        target,
        "list_corpus_tasks_v1",
        lambda _ledger, **_kwargs: [
            {
                "relative_path": "vietstock_bctc/N01/2025/report.pdf",
                "state": "RUNNING",
                "task_id": "task-1",
            }
        ],
    )
    monkeypatch.setattr(
        target,
        "_repair_one",
        lambda *_args, **_kwargs: pytest.fail("repair must not overlap the main pass"),
    )
    args = Namespace(
        bundle=tmp_path / "bundle.json",
        ledger=tmp_path / "ledger.sqlite3",
        max_tasks=None,
        plan=tmp_path / "plan.json",
    )

    with pytest.raises(
        target.RunGeminiJsonFirst27BankVertexFlexV1Error,
        match="fully terminal",
    ):
        target._repair_all(args, environment={"PYTHONPATH": "src"})


def test_repair_all_is_sorted_sequential_and_resumable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tasks = [
        {
            "relative_path": "vietstock_bctc/N02/2025/b.pdf",
            "route": target.OPENROUTER_ROUTE,
            "state": "FAILED",
            "task_id": "task-b",
        },
        {
            "relative_path": "vietstock_bctc/N01/2025/a.pdf",
            "route": target.OPENROUTER_ROUTE,
            "state": "FAILED",
            "task_id": "task-a",
        },
        {
            "relative_path": "vietstock_bctc/N03/2025/c.pdf",
            "route": target.OPENROUTER_ROUTE,
            "state": "SUCCEEDED",
            "task_id": "task-c",
        },
    ]
    monkeypatch.setattr(
        target,
        "_load_bundle_and_plan",
        lambda _bundle, _plan: {"corpus_plan": {"corpus_plan_id": "plan-1"}},
    )
    monkeypatch.setattr(
        target,
        "corpus_ledger_summary_v1",
        lambda _ledger: {"corpus_plan_id": "plan-1"},
    )

    def listed(_ledger: Path, *, states=None, route=None):
        result = tasks
        if states is not None:
            result = [task for task in result if task["state"] in states]
        if route is not None:
            result = [task for task in result if task["route"] == route]
        return result

    monkeypatch.setattr(target, "list_corpus_tasks_v1", listed)
    repaired = []

    def repair_one(args: Namespace, *, environment: dict[str, str]):
        assert environment == {"PYTHONPATH": "src"}
        repaired.append(args.task_id)
        next(task for task in tasks if task["task_id"] == args.task_id)["state"] = "SUCCEEDED"
        return {"disposition": "SUCCEEDED", "task_id": args.task_id}

    monkeypatch.setattr(target, "_repair_one", repair_one)
    args = Namespace(
        bundle=tmp_path / "bundle.json",
        ledger=tmp_path / "ledger.sqlite3",
        max_tasks=1,
        plan=tmp_path / "plan.json",
    )

    first = target._repair_all(args, environment={"PYTHONPATH": "src"})

    assert repaired == ["task-a"]
    assert first["disposition"] == "NEEDS_RETRY"
    assert first["remaining_failed_task_count"] == 1

    args.max_tasks = None
    second = target._repair_all(args, environment={"PYTHONPATH": "src"})

    assert repaired == ["task-a", "task-b"]
    assert second["disposition"] == "SUCCEEDED"
    assert second["remaining_failed_task_count"] == 0
