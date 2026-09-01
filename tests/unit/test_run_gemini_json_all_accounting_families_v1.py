from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.experiments import run_gemini_json_all_accounting_families_v1 as runner


def test_plan_is_schema_ordered_exhaustive_and_compilable() -> None:
    plan = runner._plan()

    assert plan["format_version"] == "GEMINI_JSON_ALL_ACCOUNTING_FAMILIES_PLAN_V1"
    assert plan["family_count"] == 55
    assert [job["schema_order"] for job in plan["jobs"]] == list(range(1, 56))
    assert len({job["family_id"] for job in plan["jobs"]}) == 55
    assert plan["jobs"][29] == {
        "execution_kind": "DERIVED_VISIBLE_STATEMENT_LINE",
        "family_id": "NET_INTEREST_INCOME",
        "schema_order": 30,
        "vietnamese_name": "Thu nhập từ lãi thuần",
    }
    assert plan["jobs"][-1]["family_id"] == "CONSOLIDATED_SEGMENT_REPORT"
    assert plan["jobs"][-1]["runner"].endswith(
        "run_gemini_json_segment_report_accounting_family_v1.py"
    )
    for job in plan["jobs"]:
        if job["execution_kind"] != "ACCOUNTING_FAMILY_RUNNER":
            continue
        assert (runner.ROOT / job["runner"]).is_file()
        assert (runner.ROOT / job["topology_spec"]).is_file()
        assert (runner.ROOT / job["evaluation_spec"]).is_file()
        assert (runner.ROOT / job["schema_binding_spec"]).is_file()


def test_paid_scope_is_disjoint_from_reuse_only_banks() -> None:
    assert len(runner.PAID_BANKS) == 19
    assert len(runner.REUSE_ONLY_BANKS) == 8
    assert runner.PAID_BANKS.isdisjoint(runner.REUSE_ONLY_BANKS)
    scope = runner._plan()["execution_scope"]
    assert scope == {
        "document_count": 279,
        "excluded_reuse_only_bank_codes": sorted(runner.REUSE_ONLY_BANKS),
        "page_count": 15_968,
        "paid_bank_codes": sorted(runner.PAID_BANKS),
        "period_start": "2025-Q1",
    }


def test_family_selection_accepts_schema_order_or_family_id() -> None:
    plan = runner._plan()

    selected = runner._selected_jobs(plan, ["1", "CONSOLIDATED_SEGMENT_REPORT"])

    assert [job["schema_order"] for job in selected] == [1, 55]
    with pytest.raises(runner.RunGeminiJsonAllAccountingFamiliesV1Error):
        runner._selected_jobs(plan, ["999"])
    with pytest.raises(runner.RunGeminiJsonAllAccountingFamiliesV1Error):
        runner._selected_jobs(plan, ["1", "CASH_PRECIOUS_METALS"])


def _index(*, replace_bank: str | None = None) -> dict:
    documents = []
    banks = sorted(runner.PAID_BANKS)
    for ordinal in range(1, runner.EXPECTED_DOCUMENT_COUNT + 1):
        bank = banks[(ordinal - 1) % len(banks)]
        if ordinal == 1 and replace_bank is not None:
            bank = replace_bank
        documents.append({"relative_path": f"vietstock_bctc/{bank}/2025/report-{ordinal:03d}.pdf"})
    return {
        "corpus_manifest_index_id": "gjfccmiv1:index:" + "a" * 64,
        "documents": documents,
        "summary": {
            "document_count": runner.EXPECTED_DOCUMENT_COUNT,
            "page_count": runner.EXPECTED_PAGE_COUNT,
        },
    }


def test_corpus_gate_rejects_a_reuse_only_bank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "_load_json", lambda _path: {})
    monkeypatch.setattr(
        runner,
        "validate_current_corpus_manifest_index_v1",
        lambda _value: _index(replace_bank="ACB"),
    )

    with pytest.raises(
        runner.RunGeminiJsonAllAccountingFamiliesV1Error,
        match="exact 19-bank",
    ):
        runner._checked_corpus(Path("index.json"))


def test_corpus_gate_accepts_exact_paid_frontier(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = _index()
    monkeypatch.setattr(runner, "_load_json", lambda _path: {})
    monkeypatch.setattr(
        runner,
        "validate_current_corpus_manifest_index_v1",
        lambda _value: expected,
    )

    assert runner._checked_corpus(Path("index.json")) is expected


def test_run_invokes_exact_family_specs_and_writes_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = runner._plan()
    family = plan["jobs"][0]
    corpus = _index()
    calls: list[list[str]] = []
    monkeypatch.setattr(runner, "_checked_corpus", lambda _path: corpus)
    monkeypatch.setattr(runner, "_plan", lambda: {**plan, "jobs": [family]})

    def fake_run(command: list[str], *, cwd: Path, check: bool) -> SimpleNamespace:
        assert cwd == runner.ROOT
        assert check is False
        calls.append(command)
        output = Path(command[command.index("--output") + 1])
        output.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    args = argparse.Namespace(
        artifact_root=tmp_path / "artifacts",
        corpus_index=tmp_path / "index.json",
        family=[],
        output_dir=tmp_path / "outputs",
        results_database=tmp_path / "results.sqlite3",
        run_kind="EXPERIMENTAL",
    )

    receipt = runner._run(args)

    assert receipt["disposition"] == "SUCCEEDED"
    assert receipt["selected_family_count"] == 1
    assert [item["family_id"] for item in receipt["completed"]] == ["CASH_PRECIOUS_METALS"]
    assert receipt["deferred"] == []
    assert len(calls) == 1
    assert calls[0][1].endswith("run_gemini_json_first_accounting_family_v1.py")
    assert json.loads((args.output_dir / "run-receipt.json").read_bytes()) == receipt


def test_derived_family_is_explicitly_deferred(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = runner._plan()
    derived = plan["jobs"][29]
    corpus = _index()
    monkeypatch.setattr(runner, "_checked_corpus", lambda _path: corpus)
    monkeypatch.setattr(runner, "_plan", lambda: {**plan, "jobs": [derived]})
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("derived family must not invoke a subprocess"),
    )
    args = argparse.Namespace(
        artifact_root=tmp_path / "artifacts",
        corpus_index=tmp_path / "index.json",
        family=[],
        output_dir=tmp_path / "outputs",
        results_database=tmp_path / "results.sqlite3",
        run_kind="EXPERIMENTAL",
    )

    receipt = runner._run(args)

    assert receipt["disposition"] == "NEEDS_DERIVED_PROJECTION"
    assert receipt["completed"] == []
    assert receipt["deferred"] == [
        {
            "family_id": "NET_INTEREST_INCOME",
            "reason": "DERIVED_VISIBLE_STATEMENT_LINE_REQUIRES_DEDICATED_PROJECTION",
            "schema_order": 30,
        }
    ]


def test_run_fails_if_family_runner_does_not_write_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = runner._plan()
    monkeypatch.setattr(runner, "_checked_corpus", lambda _path: _index())
    monkeypatch.setattr(runner, "_plan", lambda: {**plan, "jobs": [plan["jobs"][0]]})
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
    args = argparse.Namespace(
        artifact_root=tmp_path / "artifacts",
        corpus_index=tmp_path / "index.json",
        family=[],
        output_dir=tmp_path / "outputs",
        results_database=tmp_path / "results.sqlite3",
        run_kind="EXPERIMENTAL",
    )

    with pytest.raises(
        runner.RunGeminiJsonAllAccountingFamiliesV1Error,
        match="family runner failed",
    ):
        runner._run(args)
