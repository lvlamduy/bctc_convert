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
    assert plan["jobs"][29]["execution_kind"] == "ACCOUNTING_FAMILY_RUNNER"
    assert plan["jobs"][29]["family_id"] == "NET_INTEREST_INCOME"
    assert plan["jobs"][29]["schema_order"] == 30
    assert plan["jobs"][29]["vietnamese_name"] == "Thu nhập từ lãi thuần"
    assert plan["jobs"][29]["runner"].endswith(
        "run_gemini_json_multitable_hierarchical_accounting_family_v1.py"
    )
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

    sweep = {
        "family_id": family["family_id"],
        "metrics": {"ready": 1},
        "sweep_id": "sweep-1",
    }
    monkeypatch.setattr(
        runner,
        "load_gemini_accounting_family_sweep_v1",
        lambda _database, _family_run_id: sweep,
    )

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> SimpleNamespace:
        assert cwd == runner.ROOT
        assert check is False
        assert capture_output is True
        assert text is True
        calls.append(command)
        output = Path(command[command.index("--output") + 1])
        output.write_text(json.dumps(sweep) + "\n", encoding="utf-8")
        child = {
            "disposition": "SUCCEEDED",
            "family_run_id": "gjfafstorev1:run:" + "a" * 64,
            "metrics": sweep["metrics"],
            "output": str(output),
            "results_database": str(tmp_path / "results.sqlite3"),
            "run_kind": "EXPERIMENTAL",
            "sweep_id": sweep["sweep_id"],
        }
        return SimpleNamespace(returncode=0, stdout=json.dumps(child) + "\n")

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
    assert receipt["completed"][0]["family_run_id"].startswith("gjfafstorev1:run:")
    assert receipt["completed"][0]["metrics"] == {"ready": 1}
    assert receipt["completed"][0]["sweep_id"] == "sweep-1"
    assert receipt["deferred"] == []
    assert len(calls) == 1
    assert calls[0][1].endswith("run_gemini_json_first_accounting_family_v1.py")
    assert json.loads((args.output_dir / "run-receipt.json").read_bytes()) == receipt


def test_net_interest_family_invokes_the_visible_source_result_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = runner._plan()
    net_interest = plan["jobs"][29]
    corpus = _index()
    calls: list[list[str]] = []
    monkeypatch.setattr(runner, "_checked_corpus", lambda _path: corpus)
    monkeypatch.setattr(runner, "_plan", lambda: {**plan, "jobs": [net_interest]})

    sweep = {
        "family_id": net_interest["family_id"],
        "metrics": {"ready": 1},
        "sweep_id": "sweep-net-interest",
    }
    monkeypatch.setattr(
        runner,
        "load_gemini_accounting_family_sweep_v1",
        lambda _database, _family_run_id: sweep,
    )

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> SimpleNamespace:
        assert cwd == runner.ROOT
        assert check is False
        assert capture_output is True
        assert text is True
        calls.append(command)
        output = Path(command[command.index("--output") + 1])
        output.write_text(json.dumps(sweep) + "\n", encoding="utf-8")
        child = {
            "disposition": "SUCCEEDED",
            "family_run_id": "gjfafstorev1:run:" + "b" * 64,
            "metrics": sweep["metrics"],
            "output": str(output),
            "results_database": str(tmp_path / "results.sqlite3"),
            "run_kind": "EXPERIMENTAL",
            "sweep_id": sweep["sweep_id"],
        }
        return SimpleNamespace(returncode=0, stdout=json.dumps(child) + "\n")

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
    assert receipt["deferred"] == []
    assert [item["family_id"] for item in receipt["completed"]] == ["NET_INTEREST_INCOME"]
    assert len(calls) == 1
    assert calls[0][1].endswith("run_gemini_json_multitable_hierarchical_accounting_family_v1.py")


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


def test_child_receipt_rejects_missing_run_lineage(tmp_path: Path) -> None:
    output = tmp_path / "family.json"
    output.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        runner.RunGeminiJsonAllAccountingFamiliesV1Error,
        match="receipt drifted",
    ):
        runner._child_receipt(
            SimpleNamespace(returncode=0, stdout="{}\n"),
            job={"family_id": "CASH_PRECIOUS_METALS", "schema_order": 1},
            output=output,
            results_database=tmp_path / "results.sqlite3",
            run_kind="EXPERIMENTAL",
        )


def test_child_receipt_rejects_stored_sweep_from_another_family(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "family.json"
    sweep = {
        "family_id": "OTHER_FAMILY",
        "metrics": {"ready": 1},
        "sweep_id": "sweep-1",
    }
    output.write_text(json.dumps(sweep) + "\n", encoding="utf-8")
    database = tmp_path / "results.sqlite3"
    family_run_id = "gjfafstorev1:run:" + "c" * 64
    monkeypatch.setattr(
        runner,
        "load_gemini_accounting_family_sweep_v1",
        lambda _database, _family_run_id: sweep,
    )
    receipt = {
        "disposition": "SUCCEEDED",
        "family_run_id": family_run_id,
        "metrics": sweep["metrics"],
        "output": str(output),
        "results_database": str(database),
        "run_kind": "EXPERIMENTAL",
        "sweep_id": sweep["sweep_id"],
    }

    with pytest.raises(
        runner.RunGeminiJsonAllAccountingFamiliesV1Error,
        match="stored family sweep drifted",
    ):
        runner._child_receipt(
            SimpleNamespace(returncode=0, stdout=json.dumps(receipt) + "\n"),
            job={"family_id": "CASH_PRECIOUS_METALS", "schema_order": 1},
            output=output,
            results_database=database,
            run_kind="EXPERIMENTAL",
        )
