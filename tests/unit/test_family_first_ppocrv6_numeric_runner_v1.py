from __future__ import annotations

import ast
import copy
import json
import math
import os
from pathlib import Path

import pytest

from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive
from bctc_ai.ocr import family_first_ppocrv6_numeric_runner_v1 as runner
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1


def _raw_result(ordinal: int, *, score: float = 0.9, text: str = "603.040.884"):
    return {
        "crop_sha256": f"{ordinal:064x}",
        "raw_prediction": text,
        "reader_score": score,
        "sample_id": f"sample-{ordinal:09d}",
    }


def _model() -> dict[str, object]:
    return {
        "cache_directory": "PP-OCRv6_medium_rec",
        "enable_mkldnn": False,
        "repo_id": "PaddlePaddle/PP-OCRv6_medium_rec",
        "required_files": [
            {"path": f"model-{index}", "sha256": str(index) * 64, "size_bytes": index}
            for index in range(1, 4)
        ],
        "revision": "e5a92bcbc5cc1b494628e458d267778f0704fd7c",
    }


def test_result_schema_preserves_empty_and_rejects_coercions() -> None:
    result = runner._validate_result(_raw_result(1, text=""), 1)
    assert result["format_version"] == runner.PROPOSAL_FORMAT_VERSION
    assert result["raw_prediction"] == ""

    for field, value in (
        ("reader_score", True),
        ("reader_score", math.nan),
        ("crop_sha256", "bad"),
        ("sample_id", "sample-000000002"),
    ):
        malformed = _raw_result(1)
        malformed[field] = value
        with pytest.raises(runner.FamilyFirstPPocrV6NumericRunnerV1Error):
            runner._validate_result(malformed, 1)


def test_jsonl_readback_requires_exact_order_and_counts_empty(tmp_path: Path) -> None:
    descriptor = os.open(tmp_path / "proposals.jsonl", os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        first = runner._validate_result(_raw_result(1, text=""), 1)
        second = runner._validate_result(_raw_result(2, text="–"), 2)
        payload = b"".join(canonical_json_bytes_v1(item) for item in (first, second))
        os.write(descriptor, payload)
        sha, size, empty = runner._readback_jsonl(descriptor, 2)
        assert len(sha) == 64
        assert size == len(payload)
        assert empty == 1
    finally:
        os.close(descriptor)


def test_attempt_root_is_exclusive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "output/calibration").mkdir(parents=True)
    monkeypatch.setattr(runner, "RUN_ROOT", Path("output/calibration/test-numeric/fresh-run"))
    run_fd, parent_fd, identity = runner._create_attempt_root(tmp_path, b"attempt")
    try:
        assert os.fstat(run_fd).st_ino == identity[1]
        descriptor = os.open("attempt.json", os.O_RDONLY, dir_fd=run_fd)
        os.close(descriptor)
    finally:
        os.close(run_fd)
        os.close(parent_fd)
    with pytest.raises(FileExistsError):
        runner._create_attempt_root(tmp_path, b"another")


def test_formal_runner_writes_one_complete_reference_blind_axis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "output/calibration").mkdir(parents=True)
    fixed_run = Path("output/calibration/test-numeric-run/fresh-run")
    monkeypatch.setattr(runner, "RUN_ROOT", fixed_run)
    monkeypatch.setattr(runner.runtime_v3, "_resolve_root", lambda value: value)
    monkeypatch.setattr(runner.runtime_v3, "_stable_bytes", lambda *_args: b"config")
    git = {
        "commit": "a" * 40,
        "dirty": False,
        "implementation_refs": [],
        "source_tree_oid": "b" * 40,
    }
    monkeypatch.setattr(runner, "_git_binding", lambda _root: copy.deepcopy(git))
    monkeypatch.setattr(
        runner.kernel_v1,
        "_recognizer_projection",
        lambda *_args: (copy.deepcopy(_model()), tmp_path / "model"),
    )
    projection = {
        "archive_id": "ffslav1:archive:" + "1" * 64,
        "batch_id": "ffslcv1:batch:" + "2" * 64,
        "plan_id": "ffslpv1:plan:" + "3" * 64,
        "sample_count": 2,
    }
    session = object.__new__(archive.AuthenticatedFamilyFirstSemanticLabelReaderSessionV1)
    monkeypatch.setattr(
        runner.archive_v1,
        "open_authenticated_family_first_semantic_label_reader_snapshot_v1",
        lambda _root, _cap: (copy.deepcopy(projection), session),
    )

    def execute(
        _root,
        supplied_session,
        *,
        expected_sample_count,
        model_cache,
        result_sink,
        batch_size,
        cpu_threads,
    ):
        assert supplied_session is session
        assert expected_sample_count == 2
        assert model_cache == tmp_path
        assert (batch_size, cpu_threads) == (64, 16)
        result_sink(_raw_result(1, text=""))
        result_sink(_raw_result(2, score=0.8, text="–"))
        return (
            {
                "device": "cpu",
                "model": copy.deepcopy(_model()),
                "packages": {"paddleocr": "3.7.0", "paddlepaddle": "3.3.0"},
                "precision": "fp32",
            },
            {
                "formal_run_count": 1,
                "model_build_count": 1,
                "reader_chunk_call_count": 2,
                "recognizer_predict_call_count": 1,
                "result_count": 2,
            },
            {"model_load_seconds": 1.0, "total_wall_seconds": 2.0},
        )

    monkeypatch.setattr(
        runner.kernel_v1,
        "execute_authenticated_ppocrv6_numeric_reference_blind_v1",
        execute,
    )
    capability = object.__new__(archive.AuthenticatedFamilyFirstSemanticLabelArchiveV1)
    manifest = runner.run_authenticated_family_first_ppocrv6_numeric_v1(
        tmp_path, capability, model_cache=tmp_path
    )

    assert manifest["metrics"]["sample_count"] == 2
    assert manifest["metrics"]["empty_prediction_count"] == 1
    assert manifest["safety"]["automatic_digit_repair"] is False
    run_root = tmp_path / fixed_run
    assert sorted(path.name for path in run_root.iterdir()) == [
        "attempt.json",
        "numeric-proposals.jsonl",
        "run_manifest.json",
    ]
    proposals = [
        json.loads(line)
        for line in (run_root / "numeric-proposals.jsonl").read_text(encoding="utf-8").splitlines()
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


def test_numeric_trust_paths_cover_every_static_local_import() -> None:
    closure = _local_import_closure(
        (
            "bctc_ai.evaluation.family_first_ppocrv6_numeric_index_v1",
            "bctc_ai.evaluation.family_first_semantic_label_archive_v1",
            "bctc_ai.ocr.family_first_ppocrv6_numeric_runner_v1",
            "bctc_ai.ocr.ppocrv6_numeric_reference_blind_kernel_v1",
        )
    )
    pinned_source = {path.as_posix() for path in runner._TRUST_PATHS if path.parts[0] == "src"}
    assert pinned_source == closure
