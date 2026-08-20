from __future__ import annotations

import ast
import copy
import json
import math
import os
from pathlib import Path

import pytest

from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive
from bctc_ai.ocr import family_first_vietocr_runner_v1 as runner
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1


def _raw_result(ordinal: int, *, probability: float | None = 0.9, text: str = "Nhãn"):
    return {
        "crop_sha256": f"{ordinal:064x}",
        "mean_decoded_character_probability": probability,
        "processed_height": 32,
        "processed_width": 120,
        "raw_prediction": text,
        "sample_id": f"sample-{ordinal:09d}",
    }


def test_result_schema_preserves_empty_and_null_but_rejects_malformed_values() -> None:
    result = runner._validate_result(_raw_result(1, probability=None, text=""), 1)
    assert result["format_version"] == runner.PROPOSAL_FORMAT_VERSION
    assert result["raw_prediction"] == ""
    assert result["mean_decoded_character_probability"] is None

    for field, value in (
        ("processed_width", True),
        ("mean_decoded_character_probability", math.nan),
        ("crop_sha256", "bad"),
    ):
        malformed = _raw_result(1)
        malformed[field] = value
        with pytest.raises(runner.FamilyFirstVietOCRRunnerV1Error):
            runner._validate_result(malformed, 1)


def test_jsonl_readback_requires_exact_canonical_order_and_counts_null_empty(
    tmp_path: Path,
) -> None:
    path = tmp_path / "proposals.jsonl"
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        first = runner._validate_result(_raw_result(1, probability=None, text=""), 1)
        second = runner._validate_result(_raw_result(2), 2)
        payload = b"".join(canonical_json_bytes_v1(value) for value in (first, second))
        os.write(descriptor, payload)
        sha, size, null_count, empty_count = runner._readback_jsonl(descriptor, 2)
        assert len(sha) == 64
        assert size == len(payload)
        assert (null_count, empty_count) == (1, 1)
    finally:
        os.close(descriptor)


def test_attempt_root_is_exclusive_and_stakes_attempt_before_inference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "output/calibration").mkdir(parents=True)
    monkeypatch.setattr(runner, "RUN_ROOT", Path("output/calibration/test-family-reader/fresh-run"))
    run_fd, parent_fd, identity = runner._create_attempt_root(tmp_path, b"attempt")
    try:
        assert os.fstat(run_fd).st_ino == identity[1]
        attempt_fd = os.open("attempt.json", os.O_RDONLY, dir_fd=run_fd)
        os.close(attempt_fd)
    finally:
        os.close(run_fd)
        os.close(parent_fd)
    with pytest.raises(FileExistsError):
        runner._create_attempt_root(tmp_path, b"attempt-two")


def test_result_publication_never_replaces_an_existing_name(tmp_path: Path) -> None:
    (tmp_path / "source").write_bytes(b"owned")
    (tmp_path / "destination").write_bytes(b"foreign")
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        with pytest.raises(runner.FamilyFirstVietOCRRunnerV1Error, match="appeared"):
            runner._rename_noreplace_fd(descriptor, "source", "destination")
    finally:
        os.close(descriptor)
    assert (tmp_path / "source").read_bytes() == b"owned"
    assert (tmp_path / "destination").read_bytes() == b"foreign"


def test_formal_runner_writes_all_proposals_once_and_preserves_null_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "output/calibration").mkdir(parents=True)
    fixed_run = Path("output/calibration/test-family-vietocr/fresh-run")
    monkeypatch.setattr(runner, "RUN_ROOT", fixed_run)
    monkeypatch.setattr(runner.runtime_v3, "_resolve_root", lambda value: value)
    projection = {
        "archive_id": "ffslav1:archive:" + "1" * 64,
        "batch_id": "ffslcv1:batch:" + "2" * 64,
        "plan_id": "ffslpv1:plan:" + "3" * 64,
        "sample_count": 2,
    }
    reader_session = object.__new__(archive.AuthenticatedFamilyFirstSemanticLabelReaderSessionV1)
    monkeypatch.setattr(
        runner,
        "open_authenticated_family_first_semantic_label_reader_snapshot_v1",
        lambda _root, _cap: (copy.deepcopy(projection), reader_session),
    )
    git = {
        "commit": "a" * 40,
        "dirty": False,
        "implementation_refs": [],
        "source_tree_oid": "b" * 40,
    }
    monkeypatch.setattr(runner, "_git_binding", lambda _root: copy.deepcopy(git))
    monkeypatch.setattr(runner.runtime_v3, "_stable_bytes", lambda *_args: b"config")
    preflight = {
        "configuration": {"inference": {"max_sequence_length": 128}},
        "runtime_artifacts": {"weights": {"sha256": "4" * 64}},
        "snapshots": {"weights": b"weights"},
    }
    monkeypatch.setattr(
        runner,
        "preflight_authenticated_vietocr_runtime_v1",
        lambda _payload: copy.deepcopy(preflight),
    )

    def execute(
        _root,
        supplied_session,
        *,
        expected_sample_count,
        config,
        runtime_snapshots,
        result_sink,
    ):
        assert supplied_session is reader_session
        assert expected_sample_count == 2
        assert config == preflight["configuration"]
        assert runtime_snapshots == preflight["snapshots"]
        result_sink(_raw_result(1, probability=None, text=""))
        result_sink(_raw_result(2, probability=0.75, text="Tiền mặt"))
        return (
            {
                "compute_capability": "8.9",
                "cuda_runtime": "13.0",
                "device_name": "NVIDIA GeForce RTX 4090",
                "packages": copy.deepcopy(runner.runtime_v3._EXPECTED_PACKAGES),
                "python_major_minor": "3.11",
                "runtime_root": runner.runtime_v3.RUNTIME_ROOT.as_posix(),
            },
            {
                "checkpoint_deserialization_count": 1,
                "formal_run_count": 1,
                "model_build_count": 1,
                "process_input_count": 2,
                "reader_chunk_call_count": 2,
                "result_count": 2,
                "state_dict_load_count": 1,
                "translate_call_count": 2,
            },
            {
                "model_load_seconds": 1.0,
                "peak_gpu_memory_allocated_mib": 2.0,
                "peak_gpu_memory_reserved_mib": 3.0,
                "total_wall_seconds": 4.0,
            },
        )

    monkeypatch.setattr(runner, "execute_authenticated_vietocr_reference_blind_v1", execute)
    capability = object.__new__(archive.AuthenticatedFamilyFirstSemanticLabelArchiveV1)
    manifest = runner.run_authenticated_family_first_vietocr_v1(tmp_path, capability)

    assert manifest["metrics"]["sample_count"] == 2
    assert manifest["metrics"]["null_probability_count"] == 1
    assert manifest["metrics"]["empty_prediction_count"] == 1
    run_root = tmp_path / fixed_run
    assert sorted(path.name for path in run_root.iterdir()) == [
        "attempt.json",
        "run_manifest.json",
        "semantic-proposals.jsonl",
    ]
    proposals = [
        json.loads(line)
        for line in (run_root / "semantic-proposals.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [item["sample_id"] for item in proposals] == [
        "sample-000000001",
        "sample-000000002",
    ]


def _local_import_closure(modules: tuple[str, ...]) -> set[str]:
    source_root = Path(runner.__file__).resolve().parents[2]

    def module_path(module: str) -> Path | None:
        candidate = source_root.joinpath(*module.split("."))
        if candidate.with_suffix(".py").is_file():
            return candidate.with_suffix(".py")
        if (candidate / "__init__.py").is_file():
            return candidate / "__init__.py"
        return None

    seen: set[str] = set()
    pending = list(modules)
    while pending:
        module = pending.pop()
        if module in seen:
            continue
        path = module_path(module)
        if path is None:
            continue
        seen.add(module)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                names = [node.module, *(f"{node.module}.{alias.name}" for alias in node.names)]
            else:
                continue
            pending.extend(
                name for name in names if name.startswith("bctc_ai") and module_path(name)
            )
    return {module_path(module).relative_to(source_root.parent).as_posix() for module in seen}


def test_semantic_trust_paths_cover_every_static_local_import() -> None:
    closure = _local_import_closure(
        (
            "bctc_ai.evaluation.family_first_semantic_label_archive_v1",
            "bctc_ai.evaluation.family_first_semantic_index_v1",
            "bctc_ai.ocr.family_first_vietocr_runner_v1",
            "bctc_ai.ocr.vietocr_reference_blind_kernel_v1",
        )
    )
    pinned_source = {path.as_posix() for path in runner._TRUST_PATHS if path.parts[0] == "src"}
    assert pinned_source == closure
