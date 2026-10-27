from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from bctc_ai.evaluation import accounting_family_topology_v1 as topology

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/experiments/run_gemini_json_income_tax_accounting_family_v1.py"
SPEC = importlib.util.spec_from_file_location("income_tax_implementation_axis_v2_tests", PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _local_module(name, path):
    module = ModuleType(name)
    module.__file__ = str(path)
    module.__spec__ = importlib.util.spec_from_file_location(name, path)
    return module


def _check(monkeypatch, modules, paths, refs, previous=None):
    # An isolated module table tests the real file/origin guard without
    # assigning financial meaning to pytest's unrelated loaded modules.
    with monkeypatch.context() as scope:
        scope.setattr(sys, "modules", dict(modules))
        return runner._check_income_tax_implementation_origins_v2(
            paths, refs, previous_origins=previous,
        )


@pytest.fixture
def local_sources(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    directory = checkout / "src/bctc_ai/evaluation"
    directory.mkdir(parents=True)
    first, second = directory / "first.py", directory / "second.py"
    first.write_text("VALUE = 1\n", encoding="utf-8")
    second.write_text("VALUE = 2\n", encoding="utf-8")
    monkeypatch.setattr(runner, "ROOT", checkout)
    paths = [first, second]
    refs = [runner.generic._file_ref(path) for path in paths]
    module = _local_module("bctc_ai.evaluation.axis_existing", first)
    return checkout, paths, refs, {module.__name__: module}


def test_actual_family_compiler_dependency_is_bound_and_missing_path_is_rejected(monkeypatch):
    _specs, compiled = runner._compile_specs_v1()
    assert compiled["topology"]["family_id"] == "INCOME_TAX"
    compiler_path = Path(topology.compile_accounting_family_topology_spec_v1.__code__.co_filename).resolve()
    paths, refs, _origins = runner._seal_income_tax_implementation_axis_v2(runner.PAGE_SCOPE_PATH)
    assert compiler_path in paths
    actual = {topology.__name__: topology}
    origins = _check(monkeypatch, actual, paths, refs)
    assert origins[topology.__name__] == runner.generic._file_ref(compiler_path)
    pruned = [path for path in paths if path != compiler_path]
    pruned_refs = [runner.generic._file_ref(path) for path in pruned]
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="source is unlisted"):
        _check(monkeypatch, actual, pruned, pruned_refs)


def test_initial_other_family_import_is_sealed_without_late_axis_expansion(monkeypatch):
    extra = ROOT / "src/bctc_ai/evaluation/accounting_family_occurrence_row_axis_v2.py"
    assert extra.is_file() and extra not in runner._income_tax_implementation_paths_v2(runner.PAGE_SCOPE_PATH)
    module = _local_module("bctc_ai.evaluation.axis_preexisting_other_family", extra)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    paths, refs, origins = runner._seal_income_tax_implementation_axis_v2(runner.PAGE_SCOPE_PATH)
    assert paths.count(extra) == 1
    assert origins[module.__name__] == runner.generic._file_ref(extra)
    assert _check(monkeypatch, {module.__name__: module}, paths, refs) == {
        module.__name__: runner.generic._file_ref(extra),
    }


def test_declared_dependency_may_load_later_without_expanding_source_axis(local_sources, monkeypatch):
    _checkout, paths, refs, modules = local_sources
    before = _check(monkeypatch, modules, paths, refs)
    late = _local_module("bctc_ai.evaluation.axis_declared_late", paths[1])
    modules[late.__name__] = late
    after = _check(monkeypatch, modules, paths, refs, before)
    assert len(after) == 2 and after[late.__name__] == refs[1]
    assert len(paths) == len(refs) == 2


def test_late_unlisted_project_module_is_rejected(local_sources, monkeypatch):
    checkout, paths, refs, modules = local_sources
    before = _check(monkeypatch, modules, paths, refs)
    late_path = checkout / "src/bctc_ai/evaluation/late_unlisted.py"
    late_path.write_text("VALUE = 3\n", encoding="utf-8")
    late = _local_module("bctc_ai.evaluation.axis_unlisted", late_path)
    modules[late.__name__] = late
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="source is unlisted"):
        _check(monkeypatch, modules, paths, refs, before)


def test_initial_foreign_project_module_refuses_before_source_seal(tmp_path, monkeypatch):
    foreign = tmp_path / "foreign.py"
    foreign.write_text("VALUE = 4\n", encoding="utf-8")
    module = _local_module("bctc_ai.evaluation.axis_foreign", foreign)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="origin is outside checkout"):
        runner._seal_income_tax_implementation_axis_v2(runner.PAGE_SCOPE_PATH)


def test_late_foreign_project_module_is_rejected(local_sources, tmp_path, monkeypatch):
    _checkout, paths, refs, modules = local_sources
    before = _check(monkeypatch, modules, paths, refs)
    foreign = tmp_path / "late_foreign.py"
    foreign.write_text("VALUE = 5\n", encoding="utf-8")
    late = _local_module("bctc_ai.evaluation.axis_foreign", foreign)
    modules[late.__name__] = late
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="origin is outside checkout"):
        _check(monkeypatch, modules, paths, refs, before)


def test_existing_module_cannot_switch_to_another_already_pinned_source(local_sources, monkeypatch):
    _checkout, paths, refs, modules = local_sources
    before = _check(monkeypatch, modules, paths, refs)
    name = next(iter(modules))
    modules[name] = _local_module(name, paths[1])
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="origin changed or disappeared"):
        _check(monkeypatch, modules, paths, refs, before)


def test_existing_project_module_cannot_disappear_after_capture(local_sources, monkeypatch):
    _checkout, paths, refs, modules = local_sources
    before = _check(monkeypatch, modules, paths, refs)
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="origin changed or disappeared"):
        _check(monkeypatch, {}, paths, refs, before)


def test_source_byte_drift_is_detected_without_resealing(local_sources, monkeypatch):
    _checkout, paths, refs, modules = local_sources
    before = _check(monkeypatch, modules, paths, refs)
    paths[0].write_text("VALUE = 9\n", encoding="utf-8")
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="source bytes changed"):
        _check(monkeypatch, modules, paths, refs, before)


def test_module_spec_origin_cannot_disagree_with_its_source_file(local_sources, monkeypatch):
    _checkout, paths, refs, modules = local_sources
    module = next(iter(modules.values()))
    module.__spec__.origin = str(paths[1])
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="file/spec origins differ"):
        _check(monkeypatch, modules, paths, refs)


@pytest.mark.parametrize("filename", [None, "relative.py", "compiled.pyc"])
def test_project_module_requires_an_absolute_python_source_origin(local_sources, monkeypatch, filename):
    _checkout, paths, refs, modules = local_sources
    next(iter(modules.values())).__file__ = (
        str(paths[0].with_suffix(".pyc")) if filename == "compiled.pyc" else filename
    )
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="no Python source origin"):
        _check(monkeypatch, modules, paths, refs)


def test_script_alias_uses_source_path_even_when_module_name_is_arbitrary(local_sources, monkeypatch):
    checkout, paths, refs, _modules = local_sources
    script = checkout / "scripts/experiments/extra_alias.py"
    script.parent.mkdir(parents=True)
    script.write_text("VALUE = 6\n", encoding="utf-8")
    module = _local_module("arbitrary_alias", script)
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="source is unlisted"):
        _check(monkeypatch, {module.__name__: module}, paths, refs)


@pytest.mark.parametrize("relative", [
    "foreign/run_gemini_json_income_tax_accounting_family_v1.py",
    "foreign/src/bctc_ai/evaluation/helper.py",
])
def test_foreign_project_filename_cannot_hide_under_an_arbitrary_alias(
    local_sources, tmp_path, monkeypatch, relative,
):
    _checkout, paths, refs, _modules = local_sources
    foreign = tmp_path / relative
    foreign.parent.mkdir(parents=True)
    foreign.write_text("VALUE = 7\n", encoding="utf-8")
    module = _local_module("arbitrary_foreign_alias", foreign)
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="origin is outside checkout"):
        _check(monkeypatch, {module.__name__: module}, paths, refs)


def test_project_source_symlink_alias_is_rejected(local_sources, monkeypatch):
    checkout, paths, refs, _modules = local_sources
    alias = checkout / "src/bctc_ai/evaluation/alias.py"
    alias.symlink_to(paths[0])
    module = _local_module("bctc_ai.evaluation.axis_symlink", alias)
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="Symlink"):
        _check(monkeypatch, {module.__name__: module}, paths, refs)
