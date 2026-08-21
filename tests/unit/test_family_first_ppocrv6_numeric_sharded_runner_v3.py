from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from bctc_ai.ocr import family_first_ppocrv6_numeric_sharded_runner_v3 as runner


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


def _context(sample_count: int) -> dict[str, object]:
    batch = {
        "sample_count": sample_count,
        "samples": [
            {
                "crop_ref": {"sha256": f"{ordinal:064x}", "size_bytes": ordinal},
                "sample_id": f"sample-{ordinal:09d}",
            }
            for ordinal in range(1, sample_count + 1)
        ],
    }
    return {
        "archive": object(),
        "batch": batch,
        "config_payload": b"config",
        "config_ref": {
            "path": runner._CONFIG_PATH.as_posix(),
            "sha256": "c" * 64,
            "size_bytes": 6,
        },
        "git": {
            "commit": "a" * 40,
            "dirty": False,
            "implementation_refs": [],
            "source_tree_oid": "b" * 40,
        },
        "model": _model(),
        "model_cache": Path("model-cache"),
        "projection": {
            "archive_id": "ffslav1:archive:" + "1" * 64,
            "batch_id": "ffslcv1:batch:" + "2" * 64,
            "plan_id": "ffslpv1:plan:" + "3" * 64,
            "sample_count": sample_count,
        },
        "session": object(),
    }


def _install_kernel(monkeypatch: pytest.MonkeyPatch) -> None:
    def execute(
        _root,
        _session,
        *,
        expected_sample_count,
        model_cache,
        result_sink,
        batch_size,
        cpu_threads,
        first_sample_ordinal,
        require_archive_end,
        device,
        paddle_distribution,
    ):
        assert model_cache == Path("model-cache")
        assert (batch_size, cpu_threads) == (64, 4)
        assert (device, paddle_distribution) == ("gpu:0", "paddlepaddle-gpu")
        for ordinal in range(first_sample_ordinal, first_sample_ordinal + expected_sample_count):
            result_sink(
                {
                    "crop_sha256": f"{ordinal:064x}",
                    "raw_prediction": "" if ordinal == 2 else str(ordinal),
                    "reader_score": 0.9,
                    "sample_id": f"sample-{ordinal:09d}",
                }
            )
        return (
            {
                "accelerator": {
                    "compute_capability": [8, 9],
                    "device_name": "NVIDIA GeForce RTX 4090",
                },
                "device": "gpu:0",
                "model": _model(),
                "packages": {
                    "paddleocr": "3.7.0",
                    "paddlepaddle-gpu": "3.3.0",
                },
                "precision": "fp32",
            },
            runner._expected_counts(
                expected_sample_count,
                final_shard=require_archive_end,
            ),
            {"model_load_seconds": 1.0, "total_wall_seconds": 2.0},
        )

    monkeypatch.setattr(
        runner.kernel_v1,
        "execute_authenticated_ppocrv6_numeric_reference_blind_v1",
        execute,
    )
    monkeypatch.setattr(runner, "_assert_context", lambda *_args: None)


def test_fixed_shard_ranges_cover_axis_once() -> None:
    assert runner._range(2050, 1) == (1, 2048, 2048, 2)
    assert runner._range(2050, 2) == (2049, 2050, 2, 2)
    with pytest.raises(runner.FamilyFirstPPocrV6NumericShardedRunnerV3Error):
        runner._range(2050, 3)


def test_shard_publication_is_atomic_and_global_ordered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "output/calibration").mkdir(parents=True)
    context = _context(2)
    _install_kernel(monkeypatch)

    manifest = runner._run_shard(tmp_path, context, shard_ordinal=1)
    replay, _manifest_payload, proposal_payload = runner._validate_shard(tmp_path, context, 1)

    assert replay == manifest
    assert manifest["metrics"]["empty_prediction_count"] == 1
    assert manifest["safety"]["retry_absence_attestation"] is False
    proposals = [json.loads(line) for line in proposal_payload.splitlines()]
    assert [item["sample_id"] for item in proposals] == [
        "sample-000000001",
        "sample-000000002",
    ]
    shards = tmp_path / runner.SHARDS_ROOT
    assert [path.name for path in shards.iterdir()] == ["shard-000001"]


def test_failed_shard_never_publishes_official_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "output/calibration").mkdir(parents=True)
    context = _context(2)
    monkeypatch.setattr(runner, "_assert_context", lambda *_args: None)
    monkeypatch.setattr(
        runner.kernel_v1,
        "execute_authenticated_ppocrv6_numeric_reference_blind_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("injected")),
    )

    with pytest.raises(RuntimeError, match="injected"):
        runner._run_shard(tmp_path, context, shard_ordinal=1)

    shards = tmp_path / runner.SHARDS_ROOT
    assert not (shards / "shard-000001").exists()
    assert list(shards.iterdir()) == []


def test_missing_orchestrator_reuses_only_valid_completed_shards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "output/calibration").mkdir(parents=True)
    context = _context(2050)
    _install_kernel(monkeypatch)
    runner._run_shard(tmp_path, context, shard_ordinal=1)
    monkeypatch.setattr(runner.runtime_v3, "_resolve_root", lambda value: value)
    monkeypatch.setattr(runner, "_context", lambda *_args, **_kwargs: copy.deepcopy(context))

    result = runner.run_authenticated_family_first_ppocrv6_numeric_missing_shards_v3(
        tmp_path,
        object(),
        model_cache=Path("model-cache"),
    )

    assert result["created_shard_count"] == 1
    assert result["completed_shard_count"] == 2
    assert result["remaining_shard_count"] == 0
    assert result["state"] == "NUMERIC_SHARD_AXIS_COMPLETE"


def test_aggregate_requires_and_replays_complete_gap_free_shard_axis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "output/calibration").mkdir(parents=True)
    context = _context(2050)
    _install_kernel(monkeypatch)
    runner._run_shard(tmp_path, context, shard_ordinal=1)
    runner._run_shard(tmp_path, context, shard_ordinal=2)
    monkeypatch.setattr(runner.runtime_v3, "_resolve_root", lambda value: value)
    monkeypatch.setattr(runner, "_context", lambda *_args, **_kwargs: copy.deepcopy(context))

    aggregate = runner.aggregate_authenticated_family_first_ppocrv6_numeric_v3(
        tmp_path,
        object(),
        model_cache=Path("model-cache"),
    )
    replay, _manifest_payload, proposals, offsets = (
        runner.validate_authenticated_family_first_ppocrv6_numeric_aggregate_v3(
            tmp_path,
            object(),
            model_cache=Path("model-cache"),
        )
    )

    assert replay == aggregate
    assert len(offsets) == 2050
    assert len(proposals.splitlines()) == 2050
    assert aggregate["metrics"]["sample_count"] == 2050
    assert aggregate["metrics"]["shard_count"] == 2
    assert aggregate["authority"]["retry_absence_attestation"] is False


def test_aggregate_rejects_tampered_completed_shard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "output/calibration").mkdir(parents=True)
    context = _context(2)
    _install_kernel(monkeypatch)
    runner._run_shard(tmp_path, context, shard_ordinal=1)
    proposal = tmp_path / runner.SHARDS_ROOT / "shard-000001" / runner._PROPOSAL_NAME
    proposal.chmod(0o600)
    proposal.write_bytes(
        proposal.read_bytes().replace(b'"raw_prediction":"1"', b'"raw_prediction":"9"')
    )

    with pytest.raises(runner.FamilyFirstPPocrV6NumericShardedRunnerV3Error):
        runner._validate_shard(tmp_path, context, 1)


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


def test_numeric_v3_trust_paths_cover_every_static_local_import() -> None:
    closure = _local_import_closure(
        (
            "bctc_ai.evaluation.family_first_ppocrv6_numeric_index_v3",
            "bctc_ai.evaluation.family_first_semantic_label_archive_v1",
            "bctc_ai.ocr.family_first_ppocrv6_numeric_sharded_runner_v3",
            "bctc_ai.ocr.ppocrv6_numeric_reference_blind_kernel_v1",
        )
    )
    pinned_source = {path.as_posix() for path in runner._TRUST_PATHS if path.parts[0] == "src"}
    assert pinned_source == closure


def test_numeric_v3_cli_bootstraps_source_tree_without_installed_package(tmp_path: Path) -> None:
    project_root = Path(runner.__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            project_root / "scripts/experiments/run_family_first_ppocrv6_numeric_v3.py",
            "--help",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "run-missing" in result.stdout
