from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/run_family_first_accounting_schema_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "run_family_first_accounting_schema_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
subject = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(subject)


def _write_specs(root: Path) -> tuple[Path, Path, Path]:
    directory = root / "config/families"
    directory.mkdir(parents=True)
    family = Path("config/families/cash-topology.json")
    evaluation = Path("config/families/cash-evaluation.json")
    binding = Path("config/families/cash-schema.json")
    for path in (family, evaluation, binding):
        (root / path).write_text(
            json.dumps({"family_id": "CASH_PRECIOUS_METALS"}), encoding="utf-8"
        )
    return family, evaluation, binding


def _result() -> dict[str, object]:
    return {
        "family_id": "CASH_PRECIOUS_METALS",
        "mapping_id": "ffasmv1:mapping:" + "1" * 64,
        "metrics": {"document_count": 140, "verified_document_count": 10},
    }


def _patch_auth(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "authenticate_family_first_semantic_label_archive_v1",
        lambda *_args, **_kwargs: "archive",
    )
    monkeypatch.setattr(
        subject, "authenticate_family_first_semantic_index_v1", lambda *_args: "semantic"
    )
    monkeypatch.setattr(
        subject,
        "authenticate_family_first_ppocrv6_numeric_index_v3",
        lambda *_args, **_kwargs: "numeric",
    )


def test_build_uses_fixed_family_path_and_no_clobber(tmp_path, monkeypatch) -> None:
    family, evaluation, binding = _write_specs(tmp_path)
    _patch_auth(monkeypatch)
    built = _result()
    calls = []

    def build(root, semantic, numeric, family_spec, evaluation_spec, binding_spec):
        calls.append((root, semantic, numeric, family_spec, evaluation_spec, binding_spec))
        return built

    monkeypatch.setattr(
        subject, "build_authenticated_family_first_accounting_schema_mapping_v1", build
    )

    summary = subject.run_family_first_accounting_schema_mapping_v1(
        tmp_path,
        model_cache=tmp_path / "models",
        family_spec_path=family,
        evaluation_spec_path=evaluation,
        schema_binding_spec_path=binding,
        command="build",
    )

    expected = subject.OUTPUT_ROOT / "cash-precious-metals.json"
    assert summary["output_path"] == expected.as_posix()
    assert (tmp_path / expected).read_bytes() == canonical_json_bytes_v1(built) + b"\n"
    assert calls[0][1:3] == ("semantic", "numeric")
    with pytest.raises(FileExistsError):
        subject.run_family_first_accounting_schema_mapping_v1(
            tmp_path,
            model_cache=tmp_path / "models",
            family_spec_path=family,
            evaluation_spec_path=evaluation,
            schema_binding_spec_path=binding,
            command="build",
        )


def test_verify_reads_canonical_artifact_and_calls_live_replay(tmp_path, monkeypatch) -> None:
    family, evaluation, binding = _write_specs(tmp_path)
    _patch_auth(monkeypatch)
    built = _result()
    output = tmp_path / subject.OUTPUT_ROOT / "cash-precious-metals.json"
    output.parent.mkdir(parents=True)
    output.write_bytes(canonical_json_bytes_v1(built) + b"\n")
    calls = []

    def validate(value, root, semantic, numeric, family_spec, evaluation_spec, binding_spec):
        calls.append((value, root, semantic, numeric, family_spec, evaluation_spec, binding_spec))
        return built

    monkeypatch.setattr(
        subject, "validate_authenticated_family_first_accounting_schema_mapping_replay_v1", validate
    )

    summary = subject.run_family_first_accounting_schema_mapping_v1(
        tmp_path,
        model_cache=tmp_path / "models",
        family_spec_path=family,
        evaluation_spec_path=evaluation,
        schema_binding_spec_path=binding,
        command="verify",
    )

    assert summary["metrics"]["document_count"] == 140
    assert len(calls) == 1
    assert calls[0][2:4] == ("semantic", "numeric")


def test_all_three_spec_ids_must_match(tmp_path, monkeypatch) -> None:
    family, evaluation, binding = _write_specs(tmp_path)
    (tmp_path / binding).write_text(json.dumps({"family_id": "OTHER_FAMILY"}), encoding="utf-8")
    _patch_auth(monkeypatch)

    with pytest.raises(subject.FamilyFirstAccountingSchemaMappingCliV1Error, match="identities"):
        subject.run_family_first_accounting_schema_mapping_v1(
            tmp_path,
            model_cache=tmp_path / "models",
            family_spec_path=family,
            evaluation_spec_path=evaluation,
            schema_binding_spec_path=binding,
            command="build",
        )


def test_tracked_cash_specs_parse_and_select_fixed_artifact() -> None:
    family_path = Path("config/families/tm-cash-precious-metals-topology-v1.json")
    evaluation_path = Path("config/families/tm-cash-precious-metals-evaluation-v1.json")
    binding_path = Path("config/families/tm-cash-precious-metals-schema-binding-v1.json")

    family = subject.topology_cli._family_spec(_ROOT, family_path)
    evaluation = subject.topology_cli._family_spec(_ROOT, evaluation_path)
    binding = subject.topology_cli._family_spec(_ROOT, binding_path)

    assert subject._artifact_path(family, evaluation, binding) == (
        subject.OUTPUT_ROOT / "cash-precious-metals.json"
    )
