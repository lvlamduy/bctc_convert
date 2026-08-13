from __future__ import annotations

import copy
import hashlib
import io
import pickle
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

import bctc_ai.source_structure.vietocr_semantic_receipt_v3 as subject
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

_RUN_COMMIT = "1" * 40
_SELECTION_COMMIT = "2" * 40
_CONSUMER_COMMIT = "3" * 40
_SOURCE_TREE = "4" * 40
_FREEZE_ID = "voalrv3:freeze:" + "5" * 64
_STARTED_AT = "2026-08-13T20:00:00+00:00"
_COMPLETED_AT = "2026-08-13T20:01:00+00:00"


def _pin(path: Path, payload: bytes) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _batch() -> tuple[dict[str, Any], ...]:
    buffer = io.BytesIO()
    Image.new("RGB", (96, 32), "white").save(buffer, format="PNG")
    crop_template = buffer.getvalue()
    records = []
    for page_ordinal, line_count in enumerate(subject.EXPECTED_LINE_COUNT_VECTOR, start=1):
        page_id = f"page-{page_ordinal:04d}"
        for line_index in range(line_count):
            crop = crop_template
            records.append(
                {
                    "crop_png_bytes": crop,
                    "crop_sha256": hashlib.sha256(crop).hexdigest(),
                    "page_id": page_id,
                    "sample_id": f"{page_id}-line-{line_index:04d}",
                }
            )
    assert len(records) == subject.EXPECTED_SAMPLE_COUNT
    return tuple(records)


def _execution_counts() -> dict[str, int]:
    return {
        "authenticated_batch_accessor_call_count": 1,
        "checkpoint_deserialization_count": 1,
        "formal_run_count": 1,
        "model_build_count": 1,
        "process_input_count": subject.EXPECTED_SAMPLE_COUNT,
        "reader_request_count": 1,
        "result_count": subject.EXPECTED_SAMPLE_COUNT,
        "state_dict_load_count": 1,
        "translate_call_count": subject.EXPECTED_SAMPLE_COUNT,
    }


def _chain() -> dict[str, Any]:
    batch = _batch()
    projection = {
        "freeze_id": _FREEZE_ID,
        "line_count_vector": list(subject.EXPECTED_LINE_COUNT_VECTOR),
        "page_count": 8,
        "sample_count": subject.EXPECTED_SAMPLE_COUNT,
        "state": "FROZEN_READY_NO_MODEL_RUN",
    }
    config_payload = (Path.cwd() / subject.CONFIG_PATH).read_bytes()
    trust_payloads = {
        subject._FREEZER_PATH: b"freezer-v3",
        subject._RUNNER_PATH: b"runner-v3",
        subject._ORCHESTRATOR_PATH: b"orchestrator-v3",
        subject.CONFIG_PATH: config_payload,
    }
    git_binding = {
        "commit": _RUN_COMMIT,
        "dirty": False,
        "implementation_refs": [_pin(path, payload) for path, payload in trust_payloads.items()],
        "source_tree_oid": _SOURCE_TREE,
    }
    runtime_artifacts = {
        name: {
            "path": {
                "base_config": "artifacts/base.yml",
                "model_config": "artifacts/vgg-transformer.yml",
                "weights": "artifacts/vgg_transformer.pth",
                "wheel": "artifacts/vietocr-0.3.13-py3-none-any.whl",
            }[name],
            "sha256": digest,
            "size_bytes": size,
        }
        for name, (digest, size) in subject._EXPECTED_ARTIFACTS.items()
    }
    preflight = {
        "configuration_ref": {
            "path": subject.CONFIG_PATH.as_posix(),
            "sha256": hashlib.sha256(config_payload).hexdigest(),
            "size_bytes": len(config_payload),
        },
        "execution_policy": canonical_clone_v1(subject._EXECUTION_POLICY),
        "experiment_id": subject.EXPERIMENT_ID,
        "freeze_id": _FREEZE_ID,
        "git_binding": canonical_clone_v1(git_binding),
        "line_count_vector": list(subject.EXPECTED_LINE_COUNT_VECTOR),
        "page_count": 8,
        "runtime_artifacts": canonical_clone_v1(runtime_artifacts),
        "sample_count": subject.EXPECTED_SAMPLE_COUNT,
    }
    attempt = {
        "attempt_id": f"voalrv3:attempt:{canonical_json_sha256_v1(preflight)}",
        "claim_boundary": "FRESH_REFERENCE_BLIND_SEMANTIC_PROPOSAL_ATTEMPT_ONLY",
        "format_version": subject.ATTEMPT_FORMAT_VERSION,
        "preflight": preflight,
        "started_at": _STARTED_AT,
        "state": "FORMAL_ATTEMPT_STARTED_NO_RESUME_OR_RETRY",
    }
    attempt_raw = canonical_json_bytes_v1(attempt)

    samples = []
    for ordinal, source in enumerate(batch):
        raw_prediction = "Tie\u0302\u0300n gui" if ordinal == 0 else f"dong {ordinal:04d}"
        samples.append(
            {
                "crop_sha256": source["crop_sha256"],
                "mean_decoded_character_probability": 0.75,
                "page_id": source["page_id"],
                "processed_height": 32,
                "processed_width": 100,
                "raw_prediction": raw_prediction,
                "sample_id": source["sample_id"],
            }
        )
    result_material = {
        "attempt_id": attempt["attempt_id"],
        "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
        "experiment_id": subject.EXPERIMENT_ID,
        "format_version": subject.RESULT_FORMAT_VERSION,
        "freeze_id": _FREEZE_ID,
        "line_count_vector": list(subject.EXPECTED_LINE_COUNT_VECTOR),
        "page_count": 8,
        "reference_text_available_to_reader": False,
        "sample_count": subject.EXPECTED_SAMPLE_COUNT,
        "samples": samples,
        "state": "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE",
    }
    result = {
        **result_material,
        "result_id": f"voalrv3:result:{canonical_json_sha256_v1(result_material)}",
    }
    result_raw = canonical_json_bytes_v1(result)

    run_material = {
        "artifacts": {
            "attempt": _pin(subject.ATTEMPT_PATH, attempt_raw),
            "ocr_result": _pin(subject.RESULT_PATH, result_raw),
        },
        "attempt_id": attempt["attempt_id"],
        "completed_at": _COMPLETED_AT,
        "configuration": canonical_clone_v1(preflight["configuration_ref"]),
        "execution_counts": _execution_counts(),
        "execution_policy": canonical_clone_v1(subject._EXECUTION_POLICY),
        "experiment_id": subject.EXPERIMENT_ID,
        "format_version": subject.RUN_FORMAT_VERSION,
        "git_binding": canonical_clone_v1(git_binding),
        "input": {
            "freeze_id": _FREEZE_ID,
            "line_count_vector": list(subject.EXPECTED_LINE_COUNT_VECTOR),
            "page_count": 8,
            "sample_count": subject.EXPECTED_SAMPLE_COUNT,
        },
        "metrics": {
            "model_load_seconds": 1.0,
            "peak_gpu_memory_allocated_mib": 2.0,
            "peak_gpu_memory_reserved_mib": 3.0,
            "total_wall_seconds": 4.0,
        },
        "result_id": result["result_id"],
        "runtime": {
            "artifacts": runtime_artifacts,
            "compute_capability": "8.9",
            "cuda_runtime": "13.0",
            "device_name": "NVIDIA GeForce RTX 4090",
            "packages": canonical_clone_v1(subject._EXPECTED_PACKAGES),
            "python_major_minor": "3.11",
            "runtime_root": "/workspace/bctc-ai-runtime/vietocr-0.3.13",
        },
        "safety": canonical_clone_v1(subject._SAFETY),
        "started_at": _STARTED_AT,
        "state": "FRESH_SINGLE_RUN_COMPLETE",
    }
    run = {
        **run_material,
        "run_id": f"voalrv3:run:{canonical_json_sha256_v1(run_material)}",
    }
    run_raw = canonical_json_bytes_v1(run)
    return {
        "attempt": attempt,
        "attempt_raw": attempt_raw,
        "batch": batch,
        "projection": projection,
        "result": result,
        "result_raw": result_raw,
        "run": run,
        "run_raw": run_raw,
    }


def _install_artifact_boundary(
    monkeypatch: pytest.MonkeyPatch,
    chain: dict[str, Any],
) -> tuple[object, dict[Path, bytes], dict[str, int]]:
    freeze = object.__new__(subject.AuthenticatedVietOCRAllLineFreezeV3)
    calls = {"snapshot": 0}

    def snapshot(candidate: object):
        assert candidate is freeze
        calls["snapshot"] += 1
        return canonical_clone_v1(chain["projection"]), copy.deepcopy(chain["batch"])

    stable = {
        subject.ATTEMPT_PATH: chain["attempt_raw"],
        subject.RESULT_PATH: chain["result_raw"],
        subject.RUN_PATH: chain["run_raw"],
        subject._FREEZER_PATH: b"freezer-v3",
        subject._RUNNER_PATH: b"runner-v3",
        subject._RECEIPT_PATH: b"receipt-v3",
        subject._ORCHESTRATOR_PATH: b"orchestrator-v3",
        subject.CONFIG_PATH: (Path.cwd() / subject.CONFIG_PATH).read_bytes(),
    }

    def stable_bytes(_root: Path, relative: Path, _label: str) -> bytes:
        return stable[relative]

    monkeypatch.setattr(subject, "read_authenticated_vietocr_all_line_snapshot_v3", snapshot)
    monkeypatch.setattr(
        subject,
        "assert_authenticated_vietocr_all_line_freeze_project_root_v3",
        lambda *_args: None,
    )
    monkeypatch.setattr(subject, "_stable_bytes", stable_bytes)
    return freeze, stable, calls


def _install_git(
    monkeypatch: pytest.MonkeyPatch,
    stable: dict[Path, bytes],
    selection_raw: bytes | None = None,
) -> None:
    trust_paths = {
        subject._FREEZER_PATH,
        subject._RUNNER_PATH,
        subject._RECEIPT_PATH,
        subject._ORCHESTRATOR_PATH,
        subject.CONFIG_PATH,
    }

    def fake_git(_root: Path, *args: str) -> bytes:
        if args == ("status", "--porcelain", "--untracked-files=normal"):
            return b""
        if args == ("rev-parse", "--show-toplevel"):
            return f"{_root.resolve()}\n".encode()
        if args == ("rev-parse", "HEAD"):
            head = _RUN_COMMIT if selection_raw is None else _CONSUMER_COMMIT
            return f"{head}\n".encode()
        if args[:5] == ("log", "--all", "--diff-filter=A", "--format=%H", "--"):
            return f"{_SELECTION_COMMIT}\n".encode()
        if args == ("show", "-s", "--format=%P", _SELECTION_COMMIT):
            return f"{_RUN_COMMIT}\n".encode()
        if args == (
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            _SELECTION_COMMIT,
        ):
            return f"A\t{subject.SELECTION_PATH.as_posix()}\n".encode()
        if len(args) == 2 and args[0] == "show":
            commit, path_text = args[1].split(":", 1)
            path = Path(path_text)
            if path == subject.SELECTION_PATH:
                assert commit in {_SELECTION_COMMIT, _CONSUMER_COMMIT}
                assert selection_raw is not None
                return selection_raw
            if path in trust_paths:
                assert commit in {_RUN_COMMIT, _SELECTION_COMMIT, _CONSUMER_COMMIT}
                return stable[path]
        if len(args) == 2 and args[0] == "rev-parse" and args[1].endswith(":src/bctc_ai"):
            return f"{_SOURCE_TREE}\n".encode()
        raise AssertionError(f"unexpected Git call: {args!r}")

    monkeypatch.setattr(subject, "_git", fake_git)
    monkeypatch.setattr(subject, "_is_ancestor", lambda *_args: None)


def _build_and_track(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[dict[str, Any], object, dict[Path, bytes], dict[str, int], dict[str, Any]]:
    chain = _chain()
    freeze, stable, calls = _install_artifact_boundary(monkeypatch, chain)
    _install_git(monkeypatch, stable)
    selection = subject.build_vietocr_all_line_run_selection_v3(tmp_path, freeze)
    selection_raw = canonical_json_bytes_v1(selection)
    stable[subject.SELECTION_PATH] = selection_raw
    _install_git(monkeypatch, stable, selection_raw)
    return chain, freeze, stable, calls, selection


def test_selection_builder_and_closed_validator(monkeypatch, tmp_path):
    chain, _freeze, _stable, _calls, selection = _build_and_track(monkeypatch, tmp_path)

    assert selection["sample_count"] == 835
    assert selection["line_count_vector"] == [85, 109, 110, 101, 91, 88, 87, 164]
    assert selection["authority"] == {
        "caller_selected_artifact_pins": False,
        "hardware_execution_attestation": False,
        "historical_attempt_absence_attestation": False,
        "quality_selection_absence_attestation": False,
        "retry_absence_attestation": False,
        "semantic_proposal_selection_only": True,
    }
    validated = subject._validate_selection(
        selection,
        chain["projection"],
        chain["attempt_raw"],
        chain["result_raw"],
        chain["result"],
        chain["run_raw"],
        chain["run"],
    )
    assert validated is selection

    extra = canonical_clone_v1(selection)
    extra["caller_pin"] = "7" * 64
    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="fields drifted"):
        subject._validate_selection(
            extra,
            chain["projection"],
            chain["attempt_raw"],
            chain["result_raw"],
            chain["result"],
            chain["run_raw"],
            chain["run"],
        )


def test_authenticated_projection_global_and_page_accessors_cover_exact_order(
    monkeypatch, tmp_path
):
    _chain_value, freeze, _stable, calls, selection = _build_and_track(monkeypatch, tmp_path)

    run_capability = subject.authenticate_tracked_vietocr_all_line_run_v3(tmp_path, freeze)
    receipt = subject.build_authenticated_vietocr_semantic_receipt_v3(run_capability)
    projection = subject.project_authenticated_vietocr_semantic_receipt_v3(receipt)
    proposals = subject.read_authenticated_vietocr_semantic_proposals_v3(receipt)

    assert projection["selection_id"] == selection["selection_id"]
    assert projection["sample_count"] == subject.EXPECTED_SAMPLE_COUNT
    assert projection["authority"]["semantic_acceptance"] is False
    assert len(proposals) == subject.EXPECTED_SAMPLE_COUNT
    assert [record["sample_id"] for record in proposals] == [
        f"page-{page_ordinal:04d}-line-{line_index:04d}"
        for page_ordinal, line_count in enumerate(subject.EXPECTED_LINE_COUNT_VECTOR, start=1)
        for line_index in range(line_count)
    ]
    assert proposals[0]["raw_prediction"] == "Tie\u0302\u0300n gui"
    assert proposals[0]["normalized_prediction"] == "Tiền gui"
    for page_ordinal, line_count in enumerate(subject.EXPECTED_LINE_COUNT_VECTOR, start=1):
        page = subject.read_authenticated_vietocr_semantic_page_v3(receipt, page_ordinal)
        assert len(page) == line_count
        assert {record["page_id"] for record in page} == {f"page-{page_ordinal:04d}"}
        assert [record["line_index"] for record in page] == list(range(line_count))
    # Authentication plus every public projection/proposal/page accessor replays
    # the live freeze capability rather than trusting a stale in-memory receipt.
    assert calls["snapshot"] == 23


def test_result_self_rehash_drift_is_rejected(monkeypatch, tmp_path):
    chain, freeze, stable, _calls, selection = _build_and_track(monkeypatch, tmp_path)
    drifted = canonical_clone_v1(chain["result"])
    drifted["samples"][0]["raw_prediction"] = "coherent-looking mutation"
    stable[subject.RESULT_PATH] = canonical_json_bytes_v1(drifted)
    selection_raw = canonical_json_bytes_v1(selection)
    _install_git(monkeypatch, stable, selection_raw)

    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="result ID drifted"):
        subject.authenticate_tracked_vietocr_all_line_run_v3(tmp_path, freeze)


def test_rehashed_result_cannot_reorder_the_authenticated_835_batch(monkeypatch, tmp_path):
    chain = _chain()
    reordered = canonical_clone_v1(chain["result"])
    reordered["samples"][0], reordered["samples"][1] = (
        reordered["samples"][1],
        reordered["samples"][0],
    )
    reordered["result_id"] = subject._result_id(reordered)

    with pytest.raises(
        subject.VietOCRSemanticReceiptV3Error,
        match="proposal differs from its authenticated crop",
    ):
        subject._validate_result(
            reordered,
            _FREEZE_ID,
            chain["batch"],
            chain["attempt"]["attempt_id"],
        )


def test_raw_forged_copied_and_pickled_capabilities_are_rejected(monkeypatch, tmp_path):
    _chain_value, freeze, _stable, _calls, selection = _build_and_track(monkeypatch, tmp_path)
    run_capability = subject.authenticate_tracked_vietocr_all_line_run_v3(tmp_path, freeze)
    receipt = subject.build_authenticated_vietocr_semantic_receipt_v3(run_capability)

    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="exact opaque handle"):
        subject.build_authenticated_vietocr_semantic_receipt_v3(selection)  # type: ignore[arg-type]
    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="only be minted"):
        subject.AuthenticatedVietOCRAllLineRunV3(object())
    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="only be minted"):
        subject.AuthenticatedVietOCRSemanticReceiptV3(object())

    forged_run = object.__new__(subject.AuthenticatedVietOCRAllLineRunV3)
    forged_receipt = object.__new__(subject.AuthenticatedVietOCRSemanticReceiptV3)
    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="unknown or expired"):
        subject.build_authenticated_vietocr_semantic_receipt_v3(forged_run)
    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="unknown or expired"):
        subject.project_authenticated_vietocr_semantic_receipt_v3(forged_receipt)

    for capability in (run_capability, receipt):
        with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="cannot be copied"):
            copy.copy(capability)
        with pytest.raises((TypeError, subject.VietOCRSemanticReceiptV3Error)):
            copy.deepcopy(capability)
        with pytest.raises(pickle.PicklingError, match="cannot be serialized"):
            pickle.dumps(capability)

    for bad_page in (True, 0, 9, "1"):
        with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="page ordinal"):
            subject.read_authenticated_vietocr_semantic_page_v3(receipt, bad_page)  # type: ignore[arg-type]


def test_typed_rehash_config_pin_dimensions_and_live_state_mutation_fail_closed(
    monkeypatch, tmp_path
):
    chain, freeze, stable, _calls, selection = _build_and_track(monkeypatch, tmp_path)

    typed = canonical_clone_v1(chain["attempt"])
    typed["preflight"]["execution_policy"]["onnx"] = 0
    typed["attempt_id"] = f"voalrv3:attempt:{canonical_json_sha256_v1(typed['preflight'])}"
    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="policy drifted"):
        subject._validate_attempt(typed, _FREEZE_ID, _RUN_COMMIT, tmp_path)

    forged_pin = canonical_clone_v1(chain["attempt"])
    forged_pin["preflight"]["configuration_ref"]["sha256"] = "7" * 64
    forged_pin["attempt_id"] = (
        f"voalrv3:attempt:{canonical_json_sha256_v1(forged_pin['preflight'])}"
    )
    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="byte identity drifted"):
        subject._validate_attempt(forged_pin, _FREEZE_ID, _RUN_COMMIT, tmp_path)

    dimensions = canonical_clone_v1(chain["result"])
    dimensions["samples"][0]["processed_width"] = 9999
    dimensions["result_id"] = subject._result_id(dimensions)
    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="authenticated crop"):
        subject._validate_result(
            dimensions, _FREEZE_ID, chain["batch"], chain["attempt"]["attempt_id"]
        )

    typed_selection = canonical_clone_v1(selection)
    typed_selection["authority"]["semantic_proposal_selection_only"] = 1
    typed_selection["line_count_vector"][0] = 85.0
    typed_selection["selection_id"] = subject._selection_id(typed_selection)
    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="boundary drifted"):
        subject._validate_selection(
            typed_selection,
            chain["projection"],
            chain["attempt_raw"],
            chain["result_raw"],
            chain["result"],
            chain["run_raw"],
            chain["run"],
        )

    run_capability = subject.authenticate_tracked_vietocr_all_line_run_v3(tmp_path, freeze)
    receipt = subject.build_authenticated_vietocr_semantic_receipt_v3(run_capability)
    stable[subject.RESULT_PATH] = stable[subject.RESULT_PATH].replace(b"dong 0001", b"MUTATED01")
    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="changed after authentication"):
        subject.read_authenticated_vietocr_semantic_proposals_v3(receipt)


def test_nested_project_root_is_rejected(monkeypatch, tmp_path):
    nested = tmp_path / "output"
    nested.mkdir()
    monkeypatch.setattr(
        subject,
        "_git",
        lambda _root, *args: (
            f"{tmp_path}\n".encode()
            if args == ("rev-parse", "--show-toplevel")
            else (_ for _ in ()).throw(AssertionError(args))
        ),
    )
    with pytest.raises(subject.VietOCRSemanticReceiptV3Error, match="Git top-level"):
        subject._resolve_root(nested)
