from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


def _load_subject() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[2]
        / "scripts/experiments/capture_shb_maturity_numeric_verification_v1.py"
    )
    specification = importlib.util.spec_from_file_location(
        "capture_shb_maturity_numeric_verification_v1_test",
        path,
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.fixture
def subject() -> ModuleType:
    return _load_subject()


def _capture_arguments() -> dict[str, Any]:
    return {
        "registry_path": Path("evidence/crops/crop_registry.json"),
        "registry_sha256": "1" * 64,
        "registry_size_bytes": 101,
        "predictions_path": Path("evidence/run/predictions.json"),
        "predictions_sha256": "2" * 64,
        "predictions_size_bytes": 202,
        "run_manifest_path": Path("evidence/run/run_manifest.json"),
        "run_manifest_sha256": "3" * 64,
        "run_manifest_size_bytes": 303,
        "selection_authority_path": Path("evidence/selection.json"),
        "selection_authority_sha256": "4" * 64,
        "selection_authority_size_bytes": 404,
        "expected_run_commit": "a" * 40,
        "expected_selection_authority_commit": "b" * 40,
        "model_cache": Path("model-cache"),
        "output": Path("evidence/verification.json"),
    }


def test_capture_authenticates_then_verifies_and_writes_exact_module_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    subject: ModuleType,
) -> None:
    transformer_receipt = object()
    projection = {"projection": "exact"}
    binding = {"binding": "exact"}
    graph = {"graph": "exact"}
    proposal_receipt = object()
    verified = {
        "claim_boundary": "MODULE_OWNED_BOUNDARY",
        "status": "COMPLETE_WITH_EXACT_EIGHT_CELL_AGREEMENT",
        "verification_id": "sgnpvv1:verification:opaque",
    }
    calls: dict[str, Any] = {}
    monkeypatch.setattr(subject, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        subject,
        "_reconstruct_shb_maturity_graph_v1",
        lambda: (transformer_receipt, projection, binding, graph),
    )

    def authenticate(root: Path, **kwargs: Any) -> object:
        calls["authenticate"] = root, kwargs
        return proposal_receipt

    def verify(receipt: object, root: Path, **kwargs: Any) -> dict[str, Any]:
        calls["verify"] = receipt, root, kwargs
        return verified

    def write(path: Path, value: Any) -> str:
        calls["write"] = path, value
        return "5" * 64

    monkeypatch.setattr(subject, "authenticate_semantic_graph_numeric_proposals_v1", authenticate)
    monkeypatch.setattr(subject, "verify_semantic_graph_numeric_proposals_v1", verify)
    monkeypatch.setattr(subject, "atomic_write_json", write)

    arguments = _capture_arguments()
    assert subject.capture_shb_maturity_numeric_verification_v1(**arguments) is verified

    root, authentication = calls["authenticate"]
    assert root == tmp_path
    assert authentication["registry"] == subject.ArtifactPinV1(
        arguments["registry_path"],
        arguments["registry_sha256"],
        arguments["registry_size_bytes"],
    )
    assert authentication["predictions"] == subject.ArtifactPinV1(
        arguments["predictions_path"],
        arguments["predictions_sha256"],
        arguments["predictions_size_bytes"],
    )
    assert authentication["run_manifest"] == subject.ArtifactPinV1(
        arguments["run_manifest_path"],
        arguments["run_manifest_sha256"],
        arguments["run_manifest_size_bytes"],
    )
    assert authentication["selection_authority"] == subject.ArtifactPinV1(
        arguments["selection_authority_path"],
        arguments["selection_authority_sha256"],
        arguments["selection_authority_size_bytes"],
    )
    assert authentication["expected_run_commit"] == "a" * 40
    assert authentication["expected_selection_authority_commit"] == "b" * 40
    assert authentication["model_cache"] == tmp_path / "model-cache"
    expected_replay = {
        "semantic_graph_v2": graph,
        "source_projection_v2": projection,
        "semantic_page_binding_v2": binding,
        "authenticated_transformer_receipt_v2": transformer_receipt,
        "family_spec": subject.LOAN_MATURITY_BUCKETS_SPEC_V1,
        "family_specs_for_collision_scope": subject.SPECS,
    }
    for key, value in expected_replay.items():
        assert authentication[key] is value
    assert calls["verify"] == (proposal_receipt, tmp_path, expected_replay)
    assert calls["write"] == (tmp_path / "evidence/verification.json", verified)


def test_capture_refuses_existing_output_before_replay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    subject: ModuleType,
) -> None:
    monkeypatch.setattr(subject, "PROJECT_ROOT", tmp_path)
    output = tmp_path / "evidence/verification.json"
    output.parent.mkdir()
    output.write_text("must survive\n", encoding="utf-8")
    monkeypatch.setattr(
        subject,
        "_reconstruct_shb_maturity_graph_v1",
        lambda: pytest.fail("replay must not start when output exists"),
    )
    arguments = _capture_arguments()

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        subject.capture_shb_maturity_numeric_verification_v1(**arguments)

    assert output.read_text(encoding="utf-8") == "must survive\n"


def test_reconstructs_the_same_frozen_shb_maturity_chain(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    subject: ModuleType,
) -> None:
    transformer_receipt = object()
    projection = {"projection": "exact"}
    binding = {"binding": "exact"}
    graph = {"graph": "exact"}
    page_record = {"record": "target"}
    page_result = {"result": "target"}
    values = {
        subject.MANIFEST: {"pages": [{"result_ref": {"sha256": "target-page"}}]},
        subject.TIER1: {
            "cases": [
                {
                    "provenance_only_not_inference": {
                        "v3_document_manifest_ref": {"path": "document.json"},
                        "page_inputs": [
                            {
                                "result_ref": {
                                    "path": "page-result.json",
                                    "sha256": "target-page",
                                },
                                "page_record_json_pointer": "/page_records/2",
                            }
                        ],
                    }
                }
            ]
        },
        "document.json": {"page_records": [{}, {}, page_record]},
        "page-result.json": page_result,
    }
    calls: dict[str, Any] = {}
    monkeypatch.setattr(subject, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(subject, "_json", lambda path: values[path])

    def validate_receipt(*args: Any, **kwargs: Any) -> object:
        calls["receipt"] = args, kwargs
        return transformer_receipt

    def project(**kwargs: Any) -> dict[str, Any]:
        calls["projection"] = kwargs
        return projection

    def bind(*args: Any) -> dict[str, Any]:
        calls["binding"] = args
        return binding

    def build(*args: Any) -> dict[str, Any]:
        calls["graph"] = args
        return graph

    monkeypatch.setattr(subject, "validate_vietocr_semantic_receipt_v2", validate_receipt)
    monkeypatch.setattr(subject, "project_authenticated_page_v2", project)
    monkeypatch.setattr(subject, "bind_vietocr_semantic_page_v2", bind)
    monkeypatch.setattr(subject, "build_semantic_local_accounting_graph_v2", build)

    assert subject._reconstruct_shb_maturity_graph_v1() == (
        transformer_receipt,
        projection,
        binding,
        graph,
    )
    assert calls["receipt"] == (
        (tmp_path, subject.MANIFEST, subject.REQUEST, subject.RESULT, subject.RUN),
        {
            "expected_ocr_result_sha256": subject.RESULT_SHA256,
            "expected_run_manifest_sha256": subject.RUN_SHA256,
        },
    )
    assert calls["projection"] == {
        "page_record": page_record,
        "page_result": page_result,
    }
    assert calls["binding"] == (projection, transformer_receipt)
    assert calls["graph"] == (
        projection,
        binding,
        transformer_receipt,
        subject.LOAN_MATURITY_BUCKETS_SPEC_V1,
        subject.SPECS,
    )


def test_main_wires_all_external_pins_and_prints_module_claim(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    subject: ModuleType,
) -> None:
    captured: dict[str, Any] = {}
    verified = {
        "claim_boundary": "MODULE_BOUNDARY",
        "status": "COMPLETE",
        "verification_id": "module-id",
    }

    def capture(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return verified

    monkeypatch.setattr(subject, "capture_shb_maturity_numeric_verification_v1", capture)
    arguments = _capture_arguments()
    command = ["capture"]
    cli_names = {
        "registry_path": "registry",
        "predictions_path": "predictions",
        "run_manifest_path": "run-manifest",
        "selection_authority_path": "selection-authority",
    }
    for name, value in arguments.items():
        command.extend((f"--{cli_names.get(name, name.replace('_', '-'))}", str(value)))
    monkeypatch.setattr(sys, "argv", command)

    assert subject.main() == 0
    assert captured == arguments
    assert json.loads(capsys.readouterr().out) == {
        "claim_boundary": "MODULE_BOUNDARY",
        "status": "COMPLETE",
        "verification_id": "module-id",
    }
