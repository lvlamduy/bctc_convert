from __future__ import annotations

import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.core.hashing import sha256_bytes
from bctc_ai.evaluation import semantic_graph_numeric_cell_crops_v1 as crop_subject
from bctc_ai.evaluation import semantic_graph_numeric_proposal_receipt_v1 as subject


def _write_json(path: Path, value: object) -> bytes:
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _pin(root: Path, path: Path) -> subject.ArtifactPinV1:
    raw = path.read_bytes()
    return subject.ArtifactPinV1(
        path=path.relative_to(root), sha256=sha256_bytes(raw), size_bytes=len(raw)
    )


def _registry(root: Path) -> tuple[dict, Path]:
    directory = root / "output/crops"
    crops = directory / "crops"
    crops.mkdir(parents=True)
    cells = []
    for row in range(4):
        for axis in range(2):
            cell_id = f"page-0001-row-{row:03d}-axis-{axis + 1}"
            relative = f"crops/{cell_id}.png"
            raw = f"opaque-pixels-{row}-{axis}".encode()
            (directory / relative).write_bytes(raw)
            value = str((row + 1) * 100 + axis)
            cells.append(
                {
                    "axis_id": f"axis-{axis}",
                    "axis_ordinal": axis,
                    "cell_id": cell_id,
                    "crop_path": relative,
                    "crop_sha256": sha256_bytes(raw),
                    "crop_size_bytes": len(raw),
                    "page": 1,
                    "primary_normalized_text": value,
                    "primary_observation": "VALUE",
                    "primary_raw_text": value,
                    "primary_sign_evidence": None,
                    "primary_value": value,
                    "recognizer_payload": {"crop_path": relative},
                    "row_ordinal": row,
                    "source_atom_id": f"atom-{row}-{axis}",
                    "source_bbox_raw_pixels": [axis, row, axis + 1, row + 1],
                    "source_evidence_node_id": f"evidence-{row}-{axis}",
                    "source_graph_node_id": f"node-{row}-{axis}",
                    "source_line_index": row * 2 + axis,
                    "visual_punctuation_evidence": None,
                }
            )
    registry = {
        "claim_boundary": subject.CROP_CLAIM_BOUNDARY,
        "format_version": 3,
        "geometry_authority": subject.CROP_GEOMETRY_AUTHORITY,
        "metrics": {"cell_count": 8},
        "policy": subject.CROP_POLICY,
        "recognizer_input_fields": ["crop_path"],
        "registry_id": "registry-opaque",
        "semantic_graph": {"graph_id": "graph-opaque", "sha256": "1" * 64},
        "semantic_page_binding_sha256": "2" * 64,
        "source_projection_sha256": "3" * 64,
        "cells": cells,
    }
    path = directory / "crop_registry.json"
    _write_json(path, registry)
    return registry, path


def _artifacts(root: Path, registry: dict, registry_path: Path) -> dict[str, object]:
    run_directory = root / "output/run"
    predictions = [
        {
            "cell_id": cell["cell_id"],
            "crop_path": (registry_path.parent / cell["crop_path"]).as_posix(),
            "crop_sha256": cell["crop_sha256"],
            "raw_prediction": cell["primary_raw_text"],
            "reader_score": 0.01,
            "proposal_status": "NUMERIC_CHARACTERS_ONLY_PROPOSAL",
        }
        for cell in registry["cells"]
    ]
    predictions_path = run_directory / "predictions.json"
    _write_json(predictions_path, predictions)
    registry_pin = _pin(root, registry_path)
    predictions_pin = _pin(root, predictions_path)
    run_commit = "a" * 40
    run = {
        "format_version": 1,
        "state": "NUMERIC_CELL_PROPOSALS_COMPLETE",
        "dataset_role": "CALIBRATION",
        "evidence_role": "INDEPENDENT_NUMERIC_CELL_PROPOSAL_ONLY",
        "confidence_policy": "NO_AUTOMATIC_TRUTH_MAPPING_OR_CONFIDENCE_PROMOTION",
        "code": {"commit": run_commit, "dirty": False},
        "configuration": {
            "path": "config/models/numeric-recognizer-v1.toml",
            "sha256": "4" * 64,
            "network_policy": "PROCESS_SOCKET_CONNECT_DENIED",
            "batch_size": 8,
            "cpu_threads": 1,
            "precision": "fp32",
            "device": "cpu",
        },
        "crop_registry": {
            "path": registry_pin.path.as_posix(),
            "sha256": registry_pin.sha256,
            "cell_count": 8,
            "recognizer_input_fields": ["crop_path"],
        },
        "runtime": {
            "paddlepaddle": "3.3.0",
            "paddleocr": "3.7.0",
            "paddlex": "3.7.2",
            "paddle_device": "cpu",
            "model": {},
        },
        "metrics": {
            "cell_count": 8,
            "proposal_status_counts": {"NUMERIC_CHARACTERS_ONLY_PROPOSAL": 8},
            "wall_seconds": 1.0,
            "model_load_session_count": 1,
        },
        "artifacts": {
            "predictions": {
                "path": "predictions.json",
                "size_bytes": predictions_pin.size_bytes,
                "sha256": predictions_pin.sha256,
            }
        },
        "started_at": "2026-01-01T00:00:00+00:00",
        "completed_at": "2026-01-01T00:00:01+00:00",
    }
    run_path = run_directory / "run_manifest.json"
    _write_json(run_path, run)
    run_pin = _pin(root, run_path)
    selection = {
        "format_version": 1,
        "state": subject._SELECTION_STATE,
        "claim_boundary": subject._SELECTION_CLAIM_BOUNDARY,
        "run_commit": run_commit,
        "cell_count": 8,
        "artifacts": {
            "registry": subject._pin_record(registry_pin),
            "predictions": subject._pin_record(predictions_pin),
            "run_manifest": subject._pin_record(run_pin),
        },
    }
    selection_path = root / "evidence/numeric-selection.json"
    _write_json(selection_path, selection)
    return {
        "predictions": predictions,
        "predictions_path": predictions_path,
        "registry_pin": registry_pin,
        "predictions_pin": predictions_pin,
        "run_pin": run_pin,
        "run": run,
        "run_path": run_path,
        "selection_pin": _pin(root, selection_path),
        "run_commit": run_commit,
        "selection_commit": "b" * 40,
    }


@pytest.fixture
def authenticated(monkeypatch, tmp_path):
    registry, registry_path = _registry(tmp_path)
    artifacts = _artifacts(tmp_path, registry, registry_path)
    monkeypatch.setattr(
        subject,
        "validate_semantic_graph_numeric_cell_crop_registry_replay_v1",
        lambda value, *_args: deepcopy(value),
    )
    monkeypatch.setattr(
        subject,
        "_verify_git_execution_ledger",
        lambda *_args: {
            "clean_descendant_replay_validated_but_not_persisted": True,
            "entrypoints": [],
            "selection_authority_commit": artifacts["selection_commit"],
            "source_tree": {"git_object_id": "c" * 40, "path": "src/bctc_ai"},
        },
    )
    monkeypatch.setattr(subject, "_validate_config_and_model", lambda *_args: ({}, {}))
    receipt = subject.authenticate_semantic_graph_numeric_proposals_v1(
        tmp_path,
        registry=artifacts["registry_pin"],
        predictions=artifacts["predictions_pin"],
        run_manifest=artifacts["run_pin"],
        selection_authority=artifacts["selection_pin"],
        expected_run_commit=artifacts["run_commit"],
        expected_selection_authority_commit=artifacts["selection_commit"],
        model_cache=tmp_path / "models",
        semantic_graph_v2={},
        source_projection_v2={},
        semantic_page_binding_v2={},
        authenticated_transformer_receipt_v2=object(),
        family_spec=None,
        family_specs_for_collision_scope=(),
    )
    return tmp_path, receipt, artifacts


def _verify(root: Path, receipt):
    return subject.verify_semantic_graph_numeric_proposals_v1(
        receipt,
        root,
        semantic_graph_v2={},
        source_projection_v2={},
        semantic_page_binding_v2={},
        authenticated_transformer_receipt_v2=object(),
        family_spec=None,
        family_specs_for_collision_scope=(),
    )


def test_opaque_receipt_verifies_exact_eight_cells_and_replays(authenticated) -> None:
    root, receipt, _ = authenticated
    result = _verify(root, receipt)
    assert result["status"] == "COMPLETE_WITH_EXACT_EIGHT_CELL_AGREEMENT"
    assert result["metrics"]["authenticated_cell_count"] == 8
    assert result["metrics"]["reader_score_decision_use_count"] == 0
    assert [cell["normalized_numeric_value"] for cell in result["cells"]] == [
        "100",
        "101",
        "200",
        "201",
        "300",
        "301",
        "400",
        "401",
    ]
    assert (
        subject.validate_semantic_graph_numeric_verification_replay_v1(
            result,
            receipt,
            root,
            semantic_graph_v2={},
            source_projection_v2={},
            semantic_page_binding_v2={},
            authenticated_transformer_receipt_v2=object(),
            family_spec=None,
            family_specs_for_collision_scope=(),
        )
        == result
    )
    with pytest.raises(TypeError, match="opaque"):
        subject.AuthenticatedSemanticGraphNumericProposalReceiptV1()


def test_persisted_result_cannot_reauthor_decision(authenticated) -> None:
    root, receipt, _ = authenticated
    forged = _verify(root, receipt)
    forged["cells"][0]["normalized_numeric_value"] = "999"
    forged["verification_id"] = subject._verification_id(forged)
    with pytest.raises(ValueError, match="differs from exact receipt replay"):
        subject.validate_semantic_graph_numeric_verification_replay_v1(
            forged,
            receipt,
            root,
            semantic_graph_v2={},
            source_projection_v2={},
            semantic_page_binding_v2={},
            authenticated_transformer_receipt_v2=object(),
            family_spec=None,
            family_specs_for_collision_scope=(),
        )


@pytest.mark.parametrize(
    "raw",
    [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'],
)
def test_strict_json_rejects_duplicates_and_nonfinite_numbers(raw: bytes) -> None:
    with pytest.raises(ValueError):
        subject._strict_json(raw, "test")


def test_selection_authority_rejects_bool_denominator(tmp_path) -> None:
    registry, registry_path = _registry(tmp_path)
    artifacts = _artifacts(tmp_path, registry, registry_path)
    selection = json.loads((tmp_path / artifacts["selection_pin"].path).read_bytes())
    selection["cell_count"] = True
    with pytest.raises(ValueError, match="identity or denominator"):
        subject._validate_selection_authority(
            selection,
            registry=artifacts["registry_pin"],
            predictions=artifacts["predictions_pin"],
            run_manifest=artifacts["run_pin"],
            expected_run_commit=artifacts["run_commit"],
        )


def test_selection_authority_rejects_schema_and_self_pinned_artifact_drift(tmp_path) -> None:
    registry, registry_path = _registry(tmp_path)
    artifacts = _artifacts(tmp_path, registry, registry_path)
    selection = json.loads((tmp_path / artifacts["selection_pin"].path).read_bytes())
    with_extra = deepcopy(selection)
    with_extra["expected_value"] = "forbidden self-authored truth"
    with pytest.raises(ValueError, match="fields drifted"):
        subject._validate_selection_authority(
            with_extra,
            registry=artifacts["registry_pin"],
            predictions=artifacts["predictions_pin"],
            run_manifest=artifacts["run_pin"],
            expected_run_commit=artifacts["run_commit"],
        )

    forged_prediction_pin = subject.ArtifactPinV1(
        path=artifacts["predictions_pin"].path,
        sha256="f" * 64,
        size_bytes=artifacts["predictions_pin"].size_bytes,
    )
    with pytest.raises(ValueError, match="predictions pin differs from external pin"):
        subject._validate_selection_authority(
            selection,
            registry=artifacts["registry_pin"],
            predictions=forged_prediction_pin,
            run_manifest=artifacts["run_pin"],
            expected_run_commit=artifacts["run_commit"],
        )


@pytest.mark.parametrize(
    ("target", "bad"),
    [
        (("format_version",), True),
        (("crop_registry", "cell_count"), 8.0),
        (("metrics", "cell_count"), 8.0),
        (("metrics", "model_load_session_count"), True),
        (("metrics", "proposal_status_counts", "NUMERIC_CHARACTERS_ONLY_PROPOSAL"), 8.0),
        (("artifacts", "predictions", "size_bytes"), 1.0),
    ],
)
def test_run_manifest_rejects_bool_and_float_integer_aliases(
    tmp_path, target: tuple[str, ...], bad: object
) -> None:
    registry, registry_path = _registry(tmp_path)
    artifacts = _artifacts(tmp_path, registry, registry_path)
    run = deepcopy(artifacts["run"])
    cursor = run
    for key in target[:-1]:
        cursor = cursor[key]
    cursor[target[-1]] = bad
    with pytest.raises(ValueError, match="identity, lineage, or denominator"):
        subject._validate_run_manifest(
            run,
            root=tmp_path,
            run_path=artifacts["run_path"],
            predictions_pin=artifacts["predictions_pin"],
            predictions_path=artifacts["predictions_path"],
            registry_pin=artifacts["registry_pin"],
            registry=registry,
            expected_run_commit=artifacts["run_commit"],
        )


def _git(root: Path, *args: str) -> str:
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    return subprocess.run(
        ["git", *args],
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_git_ledger_allows_clean_descendant_with_unchanged_trust_closure(tmp_path) -> None:
    _git(tmp_path, "init")
    for relative, content in (
        (Path("src/bctc_ai/module.py"), "trusted source\n"),
        (Path("config/models/numeric-recognizer-v1.toml"), "trusted config\n"),
        (Path("scripts/models/run_numeric_cell_recognizer.py"), "trusted runner\n"),
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "run freeze")
    run_commit = _git(tmp_path, "rev-parse", "HEAD")
    selection_path = Path("evidence/selection.json")
    selection_raw = b'{"selection":"opaque"}\n'
    (tmp_path / selection_path).parent.mkdir()
    (tmp_path / selection_path).write_bytes(selection_raw)
    _git(tmp_path, "add", selection_path.as_posix())
    _git(tmp_path, "commit", "-m", "selection")
    selection_commit = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "README.md").write_text("later non-trust artifact\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "later consumer")

    ledger = subject._verify_git_execution_ledger(
        tmp_path, run_commit, selection_commit, selection_path, selection_raw
    )
    assert ledger["selection_authority_commit"] == selection_commit
    assert ledger["clean_descendant_replay_validated_but_not_persisted"] is True
    assert _git(tmp_path, "rev-parse", "HEAD") not in json.dumps(ledger, sort_keys=True)

    with pytest.raises(ValueError, match="selection authority bytes differ"):
        subject._verify_git_execution_ledger(
            tmp_path,
            run_commit,
            selection_commit,
            selection_path,
            b'{"selection":"rehashed-forgery"}\n',
        )

    (tmp_path / "src/bctc_ai/module.py").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="clean committed consumer"):
        subject._verify_git_execution_ledger(
            tmp_path, run_commit, selection_commit, selection_path, selection_raw
        )


def test_git_ledger_rejects_committed_trust_tree_change_after_selection(tmp_path) -> None:
    _git(tmp_path, "init")
    for relative, content in (
        (Path("src/bctc_ai/module.py"), "trusted source\n"),
        (Path("config/models/numeric-recognizer-v1.toml"), "trusted config\n"),
        (Path("scripts/models/run_numeric_cell_recognizer.py"), "trusted runner\n"),
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "run freeze")
    run_commit = _git(tmp_path, "rev-parse", "HEAD")
    selection_path = Path("evidence/selection.json")
    selection_raw = b'{"selection":"opaque"}\n'
    (tmp_path / selection_path).parent.mkdir()
    (tmp_path / selection_path).write_bytes(selection_raw)
    _git(tmp_path, "add", selection_path.as_posix())
    _git(tmp_path, "commit", "-m", "selection")
    selection_commit = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "src/bctc_ai/module.py").write_text("committed drift\n", encoding="utf-8")
    _git(tmp_path, "add", "src/bctc_ai/module.py")
    _git(tmp_path, "commit", "-m", "forged later implementation")

    with pytest.raises(ValueError, match="source tree changed"):
        subject._verify_git_execution_ledger(
            tmp_path, run_commit, selection_commit, selection_path, selection_raw
        )


def test_prediction_validation_rejects_order_status_score_and_extra(tmp_path) -> None:
    registry, registry_path = _registry(tmp_path)
    artifacts = _artifacts(tmp_path, registry, registry_path)
    original = artifacts["predictions"]
    for mutate in (
        lambda value: value.reverse(),
        lambda value: value[0].__setitem__("proposal_status", "EMPTY_PROPOSAL"),
        lambda value: value[0].__setitem__("reader_score", True),
        lambda value: value[0].__setitem__("extra", "forbidden"),
    ):
        forged = deepcopy(original)
        mutate(forged)
        with pytest.raises(ValueError):
            subject._validate_predictions(forged, registry, registry_path.parent)


def test_artifact_pin_rejects_path_escape_bool_size_and_bad_hash() -> None:
    for kwargs in (
        {"path": Path("../escape"), "sha256": "a" * 64, "size_bytes": 1},
        {"path": Path("artifact"), "sha256": "a" * 64, "size_bytes": True},
        {"path": Path("artifact"), "sha256": "A" * 64, "size_bytes": 1},
    ):
        with pytest.raises(ValueError, match="artifact pin"):
            subject.ArtifactPinV1(**kwargs)


@pytest.mark.parametrize("module", [crop_subject, subject])
def test_replay_temp_directory_rejects_symlink_escape(monkeypatch, tmp_path, module) -> None:
    root = tmp_path / "project"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    marker = outside / "must-survive"
    marker.write_text("outside", encoding="utf-8")
    escape = root / ".numeric-replay-attacker"
    escape.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(module.tempfile, "mkdtemp", lambda **_kwargs: escape.as_posix())

    with pytest.raises(ValueError, match="escaped project root"):
        module._make_in_project_replay_directory(root.resolve(), ".numeric-replay-")

    assert marker.read_text(encoding="utf-8") == "outside"
    assert escape.is_symlink()
