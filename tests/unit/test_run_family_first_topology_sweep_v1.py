from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/run_family_first_topology_sweep_v1.py"
_SPEC = importlib.util.spec_from_file_location("run_family_first_topology_sweep_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
cli = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cli)


def _family_spec() -> dict[str, object]:
    return {
        "children": [
            {
                "aliases": ["Tiền mặt bằng VND"],
                "presence": "REQUIRED",
                "role": "CASH_VND",
                "role_kind": "ADDITIVE_CHILD",
            }
        ],
        "family_id": "CASH_PRECIOUS_METALS",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1",
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 20,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Tiền mặt, vàng bạc, đá quý"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "CASH_PRECIOUS_METALS",
        },
        "structural_reset_aliases": [],
    }


def _result() -> dict[str, object]:
    return {
        "family_id": "CASH_PRECIOUS_METALS",
        "metrics": {
            "accepted_unique_topology_proposal_count": 1,
            "document_count": 140,
            "mapping_verified_count": 0,
            "multiple_or_nonunique_document_count": 2,
            "no_complete_region_document_count": 137,
            "not_observed_count": 0,
            "unresolved_document_count": 140,
        },
        "sweep_id": "fftsv1:sweep:" + "1" * 64,
    }


def _root(tmp_path: Path) -> tuple[Path, Path]:
    relative = Path("config/families/tm-cash-precious-metals-topology-v1.json")
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_family_spec(), ensure_ascii=False, indent=2), encoding="utf-8")
    return tmp_path, relative


def _live_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli, "authenticate_family_first_semantic_label_archive_v1", lambda *_a, **_k: object()
    )
    monkeypatch.setattr(
        cli, "authenticate_family_first_semantic_index_v1", lambda *_a, **_k: object()
    )


def test_build_and_verify_use_one_deterministic_family_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, relative = _root(tmp_path)
    expected = _result()
    _live_mocks(monkeypatch)
    monkeypatch.setattr(
        cli,
        "build_authenticated_family_first_topology_sweep_v1",
        lambda _cap, spec: expected if spec == _family_spec() else None,
    )

    summary = cli.run_family_first_topology_sweep_v1(
        root,
        model_cache=tmp_path / "models",
        family_spec_path=relative,
        command="build",
    )
    output = root / summary["output_path"]
    assert summary == {
        "family_id": "CASH_PRECIOUS_METALS",
        "metrics": expected["metrics"],
        "output_path": (
            "output/calibration/family-first-topology-sweeps-v1/cash-precious-metals.json"
        ),
        "sweep_id": expected["sweep_id"],
    }
    assert output.read_bytes() == canonical_json_bytes_v1(expected) + b"\n"

    monkeypatch.setattr(
        cli,
        "validate_authenticated_family_first_topology_sweep_replay_v1",
        lambda persisted, _cap, spec: (
            expected if persisted == expected and spec == _family_spec() else None
        ),
    )
    assert (
        cli.run_family_first_topology_sweep_v1(
            root,
            model_cache=tmp_path / "models",
            family_spec_path=relative,
            command="verify",
        )
        == summary
    )


def test_build_is_no_clobber_and_spec_path_is_confined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, relative = _root(tmp_path)
    _live_mocks(monkeypatch)
    monkeypatch.setattr(
        cli, "build_authenticated_family_first_topology_sweep_v1", lambda *_a: _result()
    )
    cli.run_family_first_topology_sweep_v1(
        root,
        model_cache=tmp_path / "models",
        family_spec_path=relative,
        command="build",
    )
    with pytest.raises(FileExistsError):
        cli.run_family_first_topology_sweep_v1(
            root,
            model_cache=tmp_path / "models",
            family_spec_path=relative,
            command="build",
        )
    with pytest.raises(cli.FamilyFirstTopologySweepCliV1Error, match="config/families"):
        cli.run_family_first_topology_sweep_v1(
            root,
            model_cache=tmp_path / "models",
            family_spec_path=Path("docs/not-a-family.json"),
            command="build",
        )


def test_duplicate_spec_field_and_noncanonical_sweep_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, relative = _root(tmp_path)
    spec_path = root / relative
    spec_path.write_text('{"family_id":"A","family_id":"B"}', encoding="utf-8")
    with pytest.raises(cli.FamilyFirstTopologySweepCliV1Error, match="duplicate"):
        cli._family_spec(root, relative)

    spec_path.write_text(json.dumps(_family_spec(), ensure_ascii=False), encoding="utf-8")
    _live_mocks(monkeypatch)
    output = root / cli._artifact_path(_family_spec())
    output.parent.mkdir(parents=True)
    output.write_text(json.dumps(_result(), indent=2), encoding="utf-8")
    with pytest.raises(cli.FamilyFirstTopologySweepCliV1Error, match="canonical"):
        cli.run_family_first_topology_sweep_v1(
            root,
            model_cache=tmp_path / "models",
            family_spec_path=relative,
            command="verify",
        )
