from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/experiments/build_f36_diagnostic_from_corpus_v1.py"


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


producer = load_file("f36_diagnostic_test", SCRIPT)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    support = load_file("f36_diagnostic_test_support", ROOT / producer.SUPPORT_RELATIVE)
    root, artifact, temp, pdf = [tmp_path / name for name in ("repo", "corpus", "tmp", "pdf")]
    for directory in (root, artifact, temp, pdf):
        directory.mkdir()
    (artifact / "source.sqlite3").write_bytes(b"source DB must not change")
    for relative in producer.CODE_RELATIVES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture implementation\n")
    for name in support.SPEC_NAMES:
        path = root / f"config/families/tm-operating-expense-{name.replace('_', '-')}-v1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical({"spec": name}))
    index = tmp_path / "index.json"
    index.write_bytes(canonical({
        "corpus_manifest_index_id": "index:1", "documents": [{"relative_path": "BANK/2025/a.pdf"}],
        "database_ref": {"path": "source.sqlite3", "sha256": "expected", "size_bytes": 25},
    }))
    args = argparse.Namespace(repo_root=root, artifact_root=artifact, source_pdf_root=pdf,
                              temporary_root=temp, corpus_index=index, output=tmp_path / "out.json")
    monkeypatch.setattr(producer, "ROOT", root)
    monkeypatch.setattr(support, "REPO_ROOT", root)
    monkeypatch.setattr(support, "FROZEN_SHA256", {})
    monkeypatch.setattr(producer, "_load_support", lambda unused: support)
    calls = []
    private_db = temp / "private.sqlite3"

    @contextmanager
    def snapshot(source, *, reference):
        assert source == artifact / "source.sqlite3"
        assert reference["sha256"] == "expected"
        assert os.environ["SQLITE_TMPDIR"] == str(temp)
        calls.append("snapshot-enter")
        yield SimpleNamespace(path=private_db)
        calls.append("snapshot-exit")

    def query(database, **kwargs):
        assert database == private_db
        calls.append("query")
        return {"selected_page_axis": ["page-axis"]}

    def auth(**kwargs):
        assert kwargs["source_pdf_root"] == pdf
        calls.append("real-source-auth")
        return {"authenticated": True, "receipt_id": "auth:1", "repair_axis": []}

    def indexed(**kwargs):
        assert "real-source-auth" in calls
        calls.append("indexed")
        return {"selected_page_axis": ["page-axis"], "query_evidence_id": "query:1"}

    trials = [{"document_ordinal": 1, "status": "UNRESOLVED_GEMINI_JSON_FAMILY"}]

    def replay(**kwargs):
        assert kwargs["source_page_database"] == private_db
        assert kwargs["selected_page_json_version_ids"] == ("selected:1",)
        calls.append("independent-source-replay")
        return trials

    def sweep(**kwargs):
        calls.append("sweep")
        return {"family_id": "OPERATING_EXPENSE", "corpus_manifest_index_id": "index:1",
                "indexed_query_evidence": kwargs["indexed_query_evidence"], "trials": trials,
                "metrics": {"document_count": 1, "unresolved_count": 1}, "sweep_id": "sweep:1"}

    def coverage(**kwargs):
        assert kwargs["fail_on_violation"] is False
        assert type(kwargs["page_json_by_document"]) is dict
        calls.append("coverage")
        return {"receipt_id": "coverage:1", "violation_count": 1, "violation_axis": ["visible-gap"]}

    runner = SimpleNamespace(
        generic=SimpleNamespace(
            _content_ref=lambda root, ref: root / ref["path"],
            _selected_page_axis=lambda **kwargs: ["selected:1"],
            _authenticated_sqlite_snapshot=snapshot,
            _load_selected_pages_by_document=lambda *args, **kwargs: defaultdict(
                dict, {1: {"page": "selected"}}
            ),
        ),
        validate_current_corpus_manifest_index_v1=lambda index: index,
        _assert_current_corpus=lambda index: None,
        compile_gemini_json_operating_expense_family_specs_v1=lambda *specs: {"family": "compiled"},
        compile_gemini_json_flat_family_specs_v1=lambda *specs: {"flat": "compiled"},
        query_selected_multitable_hierarchical_family_regions_v1=query,
        _authenticate_source_repairs_v1=auth,
        build_gemini_json_operating_expense_indexed_query_evidence_v1=indexed,
        build_gemini_json_operating_expense_trials_v1=lambda **kwargs: trials,
        validate_gemini_json_operating_expense_replay_v1=lambda **kwargs: None,
        replay_operating_expense_trials_from_source_v1=replay,
        same_typed_json_v1=lambda left, right: left == right,
        build_gemini_json_flat_family_sweep_v1=sweep,
        validate_gemini_json_flat_family_sweep_v1=lambda sweep: None,
        validate_source_observation_mapping_contract_v1=lambda sweep: {"validated": True},
        build_operating_expense_source_row_coverage_receipt_v1=coverage,
        _validate_source_row_coverage_receipt_v1=lambda coverage: coverage,
        canonical_json_sha256_v1=digest,
        canonical_json_bytes_v1=canonical,
        _source_path=lambda root, logical: root / logical,
    )
    monkeypatch.setattr(producer, "_load_runner", lambda root, support: runner)
    monkeypatch.setattr(producer.shutil, "disk_usage", lambda root: SimpleNamespace(free=2**40))
    return SimpleNamespace(args=args, support=support, runner=runner, calls=calls)


def test_diagnostic_preserves_unresolved_and_coverage_violations_without_release(fixture):
    summary = producer.build(fixture.args)
    output = json.loads(fixture.args.output.read_bytes())
    assert output["format_version"] == producer.FORMAT_VERSION
    assert output["family_id"] == "OPERATING_EXPENSE"
    assert output["corpus_manifest_index_id"] == "index:1"
    assert output["metrics"]["unresolved_count"] == 1
    assert output["source_row_coverage_receipt"]["violation_axis"] == ["visible-gap"]
    assert output["gates"]["independent_source_replay"] == "PASS"
    assert output["gates"]["source_row_coverage"] == "FAIL"
    assert output["gates"]["manual_pdf_visible_row_review"] == "NOT_PERFORMED"
    assert output["authority"]["release_authority"] is False
    assert output["authority"]["results_store_written"] is False
    assert set(output["hashes"]["active_code_sha256"]) == set(producer.CODE_RELATIVES)
    assert fixture.calls == ["snapshot-enter", "query", "real-source-auth", "indexed",
                             "independent-source-replay", "sweep", "coverage", "snapshot-exit"]
    assert (fixture.args.artifact_root / "source.sqlite3").read_bytes() == b"source DB must not change"
    assert summary["output_sha256"] == producer._hash(fixture.args.output)
    assert not list(fixture.args.temporary_root.iterdir())


@pytest.mark.parametrize("boundary", ["replay", "denominator", "source-auth", "snapshot-exit"])
def test_drift_or_auth_failure_never_publishes(fixture, boundary):
    runner = fixture.runner
    if boundary == "replay":
        runner.replay_operating_expense_trials_from_source_v1 = lambda **kwargs: []
    elif boundary == "denominator":
        original = runner.build_gemini_json_flat_family_sweep_v1

        def bad_denominator(**kwargs):
            value = original(**kwargs)
            value["metrics"]["document_count"] = 2
            return value

        runner.build_gemini_json_flat_family_sweep_v1 = bad_denominator
    elif boundary == "source-auth":
        def bad_auth(**kwargs):
            raise RuntimeError("source repair evidence drift")

        runner._authenticate_source_repairs_v1 = bad_auth
    else:
        @contextmanager
        def bad_snapshot(*args, **kwargs):
            yield SimpleNamespace(path=fixture.args.temporary_root / "private.sqlite3")
            raise RuntimeError("source DB changed")

        runner.generic._authenticated_sqlite_snapshot = bad_snapshot
    with pytest.raises(RuntimeError):
        producer.build(fixture.args)
    assert not fixture.args.output.exists()
    if boundary == "source-auth":
        assert "indexed" not in fixture.calls


@pytest.mark.parametrize("what", ["code", "config", "index", "source-pdf"])
def test_changed_inputs_fail_before_publication(fixture, what):
    runner, args = fixture.runner, fixture.args
    original = runner.build_operating_expense_source_row_coverage_receipt_v1
    pdf_file = args.source_pdf_root / "source.pdf"
    if what == "source-pdf":
        pdf_file.write_bytes(b"source PDF")
        runner._authenticate_source_repairs_v1 = lambda **kwargs: {
            "authenticated": True, "repair_axis": [{"source": {
                "source_logical_name": "source.pdf", "source_sha256": producer._hash(pdf_file),
                "source_size_bytes": 10,
            }}],
        }
        # The stub above still represents the source-auth gate, not a fabricated production audit.
        fixture.calls.append("real-source-auth")

    def mutate(**kwargs):
        result = original(**kwargs)
        if what == "code":
            path = args.repo_root / producer.CODE_RELATIVES[-1]
        elif what == "config":
            path = args.repo_root / "config/families/tm-operating-expense-topology-v1.json"
        elif what == "index":
            path = args.corpus_index
        else:
            path = pdf_file
        path.write_bytes(b"changed after source reading")
        return result

    runner.build_operating_expense_source_row_coverage_receipt_v1 = mutate
    with pytest.raises(producer.DiagnosticError, match="changed during diagnostic"):
        producer.build(args)
    assert not args.output.exists()


@pytest.mark.parametrize("boundary", ["existing-output", "temp-in-pdf", "output-in-corpus", "capacity"])
def test_paths_and_capacity_fail_closed(fixture, monkeypatch, boundary):
    args = fixture.args
    if boundary == "existing-output":
        args.output.write_bytes(b"preserve")
    elif boundary == "temp-in-pdf":
        args.temporary_root = args.source_pdf_root
    elif boundary == "output-in-corpus":
        args.output = args.artifact_root / "new.json"
    else:
        monkeypatch.setattr(producer.shutil, "disk_usage", lambda root: SimpleNamespace(free=0))
    with pytest.raises(RuntimeError):
        producer.build(args)
    assert "snapshot-enter" not in fixture.calls
    if boundary == "existing-output":
        assert args.output.read_bytes() == b"preserve"


def test_cli_help_and_runtime_binding_without_corpus_reads(tmp_path):
    code = (
        "import importlib.util,sys; "
        "s=importlib.util.spec_from_file_location('diag',sys.argv[1]); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        "h=m._load_support(m.ROOT); r=m._load_runner(m.ROOT,h); "
        "assert r.ROOT == m.ROOT; print('active-runtime-bound')"
    )
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-c", code, str(SCRIPT)], cwd=tmp_path,
                            env=environment, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "active-runtime-bound" in result.stdout
    help_result = subprocess.run([sys.executable, str(SCRIPT), "--help"], cwd=tmp_path,
                                 env=environment, capture_output=True, text=True, check=False)
    assert help_result.returncode == 0
    assert "--source-pdf-root" in help_result.stdout
    assert "--results-database" not in help_result.stdout


def _assert_real_sqlite_runtime(tmp_path, *, check_runner=False):
    """Fresh-process fixture: genuine SQLite/query/replay, no provider or release."""

    active = load_file("f36_real_diagnostic", SCRIPT)
    support = active._load_support(ROOT)
    runtime = active._load_runner(ROOT, support)
    # Import the synthetic page helpers only after checkout-bound runtime loading.
    from test_gemini_financial_page_store_v1 import _ingest
    from test_gemini_json_operating_expense_family_v1 import (
        _base_rows,
        _page,
        _section,
        _table,
    )

    from bctc_ai.storage.gemini_financial_page_store_v1 import (
        initialize_gemini_financial_page_store_v1,
    )

    database = tmp_path / "tiny-real-pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    rows = _base_rows()
    rows[-1]["label_exact"] = "Tổng cộng"
    rows[-1]["hierarchy_path_exact"] = ["Tổng cộng"]
    inserted = _ingest(
        database, physical_page=1, source_sha256="7" * 64,
        source_logical_name="BANK/2025/fixture.pdf",
        page_json=_page(_section("Chi phí hoạt động", _table(rows))),
    )
    reference = {"path": database.name, "sha256": active._hash(database),
                 "size_bytes": database.stat().st_size}
    index = {
        "corpus_manifest_index_id": "gjfccmiv1:index:" + "8" * 64,
        "documents": [{"source_sha256": "7" * 64, "source_size_bytes": 123,
                       "relative_path": "BANK/2025/fixture.pdf"}],
    }
    specs = [json.loads((ROOT / (
        f"config/families/tm-operating-expense-{name.replace('_', '-')}-v1.json"
    )).read_bytes()) for name in support.SPEC_NAMES]
    selected = [inserted["page_json_version_id"]]
    with support._temporary_directory_root(tmp_path), runtime.generic._authenticated_sqlite_snapshot(
        database, reference=reference
    ) as guard:
        result = active._evaluate(runtime, index, guard.path, selected, specs, tmp_path)
        assert result["metrics"]["document_count"] == 1
        assert result["source_row_coverage_receipt"]["violation_count"] == 0
        assert result["source_repair_authentication_receipt"]["applicable_repair_count"] == 0
        assert result["gates"]["independent_source_replay"] == "PASS"
        assert result["gates"]["final_store_acceptance"] == "NOT_PERFORMED"
        loaded = runtime.generic._load_selected_pages_by_document(
            guard.path, selected_ids=selected,
            selected_page_axis=result["indexed_query_evidence"]["selected_page_axis"],
        )
        assert type(loaded) is defaultdict  # The actual frozen loader boundary.
        if check_runner:
            class CoverageBoundaryReached(Exception):
                pass

            real_coverage = runtime.build_operating_expense_source_row_coverage_receipt_v1

            def checked_coverage(**kwargs):
                assert type(kwargs["page_json_by_document"]) is dict
                assert kwargs["page_json_by_document"] == loaded
                assert real_coverage(**kwargs)["violation_count"] == 0
                # Stop before unrelated residual audit/store acceptance paths.
                raise CoverageBoundaryReached

            runtime.build_operating_expense_source_row_coverage_receipt_v1 = checked_coverage
            with pytest.raises(CoverageBoundaryReached):
                runtime._run_with_database(
                    argparse.Namespace(), index=index, database_guard=guard,
                    selected_ids=selected, topology=specs[0], evaluation=specs[1],
                    schema=specs[2], spec_refs={},
                    compiled=runtime.compile_gemini_json_operating_expense_family_specs_v1(*specs),
                )
    assert active._hash(database) == reference["sha256"]
    assert not list(tmp_path.glob("family22-authenticated-sqlite-*"))


def _run_real_sqlite_subprocess(tmp_path, *, check_runner=False):
    code = (
        "import sys; from pathlib import Path; "
        "sys.path.insert(0,sys.argv[1]); "
        "from test_build_f36_diagnostic_from_corpus_v1 import _assert_real_sqlite_runtime; "
        "_assert_real_sqlite_runtime(Path(sys.argv[2]),check_runner=sys.argv[3]=='yes'); "
        "print('real-sqlite-wiring-pass')"
    )
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                   "TMPDIR": str(tmp_path), "SQLITE_TMPDIR": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, "-c", code, str(ROOT / "tests/unit"), str(tmp_path),
         "yes" if check_runner else "no"], cwd=ROOT, env=environment,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "real-sqlite-wiring-pass" in result.stdout


def test_real_sqlite_diagnostic_query_replay_and_coverage(tmp_path):
    _run_real_sqlite_subprocess(tmp_path)
