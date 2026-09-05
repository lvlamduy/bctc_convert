from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts/experiments/build_f36_source_row_coverage_from_sweep_v1.py"
)
SPEC = importlib.util.spec_from_file_location("f36_coverage_builder_test", SCRIPT)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def inputs(tmp_path):
    artifact = tmp_path / "corpus"
    artifact.mkdir()
    temporary = tmp_path / "private-tmp"
    temporary.mkdir()
    (artifact / "source.sqlite3").write_bytes(b"immutable fake DB")
    diagnostic, index = tmp_path / "diagnostic.json", tmp_path / "index.json"
    write_json(diagnostic, {
        "family_id": "OPERATING_EXPENSE", "corpus_manifest_index_id": "index:1",
        "indexed_query_evidence": {"selected_page_axis": ["selected-page"]},
        "trials": ["trial"],
    })
    write_json(index, {
        "corpus_manifest_index_id": "index:1",
        "database_ref": {"path": "source.sqlite3", "sha256": "expected", "size_bytes": 17},
    })
    specs = {}
    for name in builder.SPEC_NAMES:
        path = tmp_path / f"{name}.json"
        write_json(path, {"spec": name})
        specs[name] = path
    return argparse.Namespace(
        repo_root=builder.REPO_ROOT, diagnostic=diagnostic, corpus_index=index,
        artifact_root=artifact, temporary_root=temporary, output=tmp_path / "new/coverage.json",
        **specs,
    )


@pytest.fixture
def fake_runtime(inputs, monkeypatch):
    calls = []

    @contextmanager
    def snapshot(source, *, reference):
        assert source == inputs.artifact_root / "source.sqlite3"
        assert reference["sha256"] == "expected"
        assert tempfile.tempdir == str(inputs.temporary_root)
        assert os.environ["SQLITE_TMPDIR"] == str(inputs.temporary_root)
        calls.append("snapshot-enter")
        yield SimpleNamespace(path=inputs.temporary_root / "private-snapshot.sqlite3")
        calls.append("snapshot-exit-validated")

    def load_pages(database, **kwargs):
        assert database == inputs.temporary_root / "private-snapshot.sqlite3"
        assert database != inputs.artifact_root / "source.sqlite3"
        assert kwargs == {"selected_ids": ["version:1"], "selected_page_axis": ["selected-page"]}
        calls.append("load-snapshot-pages")
        return {1: {"version:1": {"source": "page"}}}

    def compile_specs(*specs):
        assert [item["spec"] for item in specs] == list(builder.SPEC_NAMES)
        return {"compiled": True}

    def build_coverage(**kwargs):
        assert kwargs["fail_on_violation"] is True
        assert kwargs["compiled_specs"] == {"compiled": True}
        assert kwargs["trials"] == ["trial"]
        calls.append("coverage")
        return {
            "candidate_table_total_row_axis": [], "raw_target_like_row_axis": [],
            "source_row_axis": ["row"], "receipt_id": "coverage:1", "violation_count": 0,
        }

    runtime = SimpleNamespace(
        generic=SimpleNamespace(
            _content_ref=lambda root, ref: root / ref["path"],
            _selected_page_axis=lambda **kwargs: ["version:1"],
            _authenticated_sqlite_snapshot=snapshot, _load_selected_pages_by_document=load_pages,
        ),
        compile_specs=compile_specs, build_coverage=build_coverage,
        canonical_bytes=lambda value: json.dumps(value, sort_keys=True).encode(),
        validate_index=lambda value: value,
    )
    monkeypatch.setattr(builder, "_load_runtime", lambda root: runtime)
    return runtime, calls


def test_coverage_preserves_adapter_semantics_and_reads_private_snapshot(inputs, fake_runtime):
    _, calls = fake_runtime
    original_source = (inputs.artifact_root / "source.sqlite3").read_bytes()
    original_temp = tempfile.tempdir
    original_sqlite_temp = os.environ.get("SQLITE_TMPDIR")
    result = builder.build(inputs)
    assert calls == ["snapshot-enter", "load-snapshot-pages", "coverage", "snapshot-exit-validated"]
    assert json.loads(inputs.output.read_bytes())["receipt_id"] == "coverage:1"
    assert result["source_rows"] == 1
    assert result["violations"] == 0
    assert result["output_sha256"] == builder._hash(inputs.output)
    assert set(result["config_sha256"]) == set(builder.SPEC_NAMES)
    assert result["code_sha256"] == {
        relative: builder._hash(inputs.repo_root / relative)
        for relative in builder.ACTIVE_CODE_RELATIVE
    }
    assert len(result["input_references"]) == 6
    assert (inputs.artifact_root / "source.sqlite3").read_bytes() == original_source
    assert tempfile.tempdir == original_temp
    assert os.environ.get("SQLITE_TMPDIR") == original_sqlite_temp


@pytest.mark.parametrize("kind", ["existing", "dangling-symlink", "inside-corpus", "inside-repo"])
def test_output_guards_run_before_import_or_snapshot(inputs, monkeypatch, kind):
    if kind == "existing":
        inputs.output.parent.mkdir()
        inputs.output.write_bytes(b"keep")
    elif kind == "dangling-symlink":
        inputs.output.parent.mkdir()
        inputs.output.symlink_to(inputs.output.parent / "missing")
    elif kind == "inside-corpus":
        inputs.output = inputs.artifact_root / "new.json"
    else:
        inputs.output = builder.REPO_ROOT / "new.json"
    monkeypatch.setattr(builder, "_load_runtime", lambda root: pytest.fail("runtime loaded"))
    with pytest.raises(builder.CoverageBuilderError):
        builder.build(inputs)
    if kind == "existing":
        assert inputs.output.read_bytes() == b"keep"


def test_exclusive_output_cannot_overwrite_late_creator(tmp_path):
    path = tmp_path / "race.json"
    path.write_bytes(b"other worker")
    with pytest.raises(FileExistsError):
        builder._write_new(path, b"new")
    assert path.read_bytes() == b"other worker"


@pytest.mark.parametrize("field,value", [
    ("family_id", "INCOME_TAX"), ("corpus_manifest_index_id", "different-index")
])
def test_diagnostic_identity_mismatch_fails_before_source_read(inputs, fake_runtime, field, value):
    diagnostic = json.loads(inputs.diagnostic.read_bytes())
    diagnostic[field] = value
    write_json(inputs.diagnostic, diagnostic)
    with pytest.raises(builder.CoverageBuilderError, match="mismatch"):
        builder.build(inputs)
    assert fake_runtime[1] == []
    assert not inputs.output.exists()


def test_snapshot_exit_failure_does_not_publish_output(inputs, fake_runtime):
    runtime, _ = fake_runtime

    @contextmanager
    def invalid_snapshot(*args, **kwargs):
        yield SimpleNamespace(path=inputs.temporary_root / "private-snapshot.sqlite3")
        raise RuntimeError("source identity changed")

    runtime.generic._authenticated_sqlite_snapshot = invalid_snapshot
    with pytest.raises(RuntimeError, match="source identity changed"):
        builder.build(inputs)
    assert not inputs.output.exists()


def test_input_config_drift_does_not_publish_output(inputs, fake_runtime):
    runtime, _ = fake_runtime
    previous = runtime.build_coverage

    def mutate_config(**kwargs):
        result = previous(**kwargs)
        write_json(inputs.topology, {"spec": "changed"})
        return result

    runtime.build_coverage = mutate_config
    with pytest.raises(builder.CoverageBuilderError, match="JSON input changed"):
        builder.build(inputs)
    assert not inputs.output.exists()


@pytest.mark.parametrize("relative", builder.ACTIVE_CODE_RELATIVE)
def test_active_code_changed_during_build_does_not_publish(
    inputs, fake_runtime, tmp_path, monkeypatch, relative
):
    # Mutate only isolated fixture files, never the live builder/family code.
    fake_repo = tmp_path / "fake-repo"
    for code_relative in builder.ACTIVE_CODE_RELATIVE:
        path = fake_repo / code_relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture code before build\n")
    inputs.repo_root = fake_repo
    monkeypatch.setattr(builder, "REPO_ROOT", fake_repo)
    monkeypatch.setattr(builder, "FROZEN_SHA256", {})
    runtime, _ = fake_runtime
    original_build_coverage = runtime.build_coverage

    def mutate_code(**kwargs):
        result = original_build_coverage(**kwargs)
        (fake_repo / relative).write_bytes(b"fixture code modified during build\n")
        return result

    runtime.build_coverage = mutate_code
    with pytest.raises(builder.CoverageBuilderError, match="Active code changed"):
        builder.build(inputs)
    assert not inputs.output.exists()


def test_preimported_family_adapter_requires_fresh_process(monkeypatch):
    adapter_path = builder.REPO_ROOT / builder.ACTIVE_CODE_RELATIVE[1]
    monkeypatch.setitem(sys.modules, builder.ADAPTER_MODULE,
                        SimpleNamespace(__file__=str(adapter_path)))
    with pytest.raises(builder.CoverageBuilderError, match="fresh process"):
        builder._load_runtime(builder.REPO_ROOT)


def test_wrong_repo_refused(inputs, fake_runtime, tmp_path):
    inputs.repo_root = tmp_path
    with pytest.raises(builder.CoverageBuilderError, match="checkout containing this builder"):
        builder.build(inputs)


def test_temporary_root_cannot_write_inside_corpus(inputs, fake_runtime):
    inputs.temporary_root = inputs.artifact_root
    with pytest.raises(builder.CoverageBuilderError, match="outside"):
        builder.build(inputs)


def test_foreign_imported_modules_are_rejected(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "bctc_ai.foreign_test", SimpleNamespace(__file__="/other/x.py"))
    with pytest.raises(builder.CoverageBuilderError, match="another checkout"):
        builder._verify_module_roots(tmp_path)


def test_runtime_imports_are_bound_to_active_worktree(tmp_path):
    code = (
        "import importlib.util, pathlib, sys; "
        "s=importlib.util.spec_from_file_location('portable_f36',sys.argv[1]); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        "r=m._load_runtime(m.REPO_ROOT); "
        "assert pathlib.Path(r.generic.__file__).resolve().is_relative_to(m.REPO_ROOT); "
        "print('bound-runtime-pass')"
    )
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-c", code, str(SCRIPT)], cwd=tmp_path,
                            env=environment, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "bound-runtime-pass" in result.stdout


def test_cli_help_does_not_require_project_imports(tmp_path):
    result = subprocess.run([sys.executable, str(SCRIPT), "--help"], cwd=tmp_path,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0
    for argument in ("--repo-root", "--temporary-root", "--source-repair", "--schema-binding"):
        assert argument in result.stdout
