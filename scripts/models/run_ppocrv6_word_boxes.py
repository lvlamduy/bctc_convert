from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_MANIFEST = PROJECT_ROOT / "config/models/gpu-runtime.toml"
MODEL_KEYS = ("pp_ocrv6_medium_det", "pp_ocrv6_medium_rec")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _deny_network_connections() -> None:
    def audit_hook(event: str, _: tuple[Any, ...]) -> None:
        if event == "socket.connect":
            raise RuntimeError("network access is forbidden during sealed PP-OCRv6 inference")

    sys.addaudithook(audit_hook)


def _git_state() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {"commit": commit, "dirty": bool(status.strip())}


def _model_records(model_cache: Path, runtime: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for key in MODEL_KEYS:
        config = runtime["models"][key]
        directory = model_cache / "official_models" / config["cache_directory"]
        weights = directory / config["weights_file"]
        if not weights.is_file():
            raise FileNotFoundError(f"missing pinned model weights: {weights}")
        size = weights.stat().st_size
        digest = _sha256(weights)
        if size != config["weights_size_bytes"] or digest != config["weights_sha256"]:
            raise RuntimeError(f"pinned model integrity mismatch: {weights}")
        records.append(
            {
                "key": key,
                "repo_id": config["repo_id"],
                "revision": config["revision"],
                "weights_path": weights.as_posix(),
                "weights_size_bytes": size,
                "weights_sha256": digest,
            }
        )
    return records


def _validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("return_word_box") is not True:
        raise RuntimeError("PP-OCRv6 result omitted required word boxes")
    line_fields = ("rec_texts", "rec_scores", "rec_polys", "rec_boxes", "text_word_boxes")
    counts = {field: len(payload.get(field, [])) for field in line_fields}
    if len(set(counts.values())) != 1:
        raise RuntimeError(f"inconsistent PP-OCRv6 line-axis lengths: {counts}")
    word_lines = payload.get("text_word", [])
    if len(word_lines) != counts["rec_texts"]:
        raise RuntimeError(
            "inconsistent PP-OCRv6 word-text line axis: "
            f"{len(word_lines)} != {counts['rec_texts']}"
        )
    return {
        "line_count": counts["rec_texts"],
        "word_token_count": sum(len(line) for line in word_lines),
    }


def _write_artifacts(
    output_directory: Path,
    payload: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=output_directory.parent)
    )
    try:
        result_path = temporary / "ocr_result.json"
        result_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest["artifacts"] = {
            "ocr_result": {
                "path": "ocr_result.json",
                "size_bytes": result_path.stat().st_size,
                "sha256": _sha256(result_path),
            }
        }
        manifest_path = temporary / "run_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if output_directory.exists():
            raise FileExistsError(f"output appeared during inference: {output_directory}")
        os.replace(temporary, output_directory)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pinned PP-OCRv6 JSON-only word-box OCR")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset-role", choices=("CALIBRATION", "HOLDOUT"), required=True)
    parser.add_argument("--cpu-threads", type=int, default=8)
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.resolve()
    output_directory = args.output_directory.resolve()
    model_cache = args.model_cache.resolve()
    config_path = args.config.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"input image does not exist: {input_path}")
    if not config_path.is_file():
        raise FileNotFoundError(f"PP-OCRv6 config does not exist: {config_path}")
    if output_directory.exists():
        raise FileExistsError(f"refusing to overwrite output: {output_directory}")
    if args.cpu_threads < 1:
        raise ValueError("cpu_threads must be positive")

    git = _git_state()
    if git["dirty"] and not args.allow_dirty:
        raise RuntimeError("refusing evidence OCR from a dirty Git worktree")
    runtime = tomllib.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    models = _model_records(model_cache, runtime)

    started_at = datetime.now(UTC)
    started = time.perf_counter()
    _deny_network_connections()
    import paddle
    from paddleocr import PaddleOCR

    pipeline = PaddleOCR(
        paddlex_config=config_path.as_posix(),
        text_detection_model_dir=str(Path(models[0]["weights_path"]).parent),
        text_recognition_model_dir=str(Path(models[1]["weights_path"]).parent),
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        return_word_box=True,
        device="cpu",
        engine="paddle",
        enable_hpi=False,
        precision="fp32",
        enable_mkldnn=False,
        cpu_threads=args.cpu_threads,
    )
    results = pipeline.predict(
        input_path.as_posix(),
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        return_word_box=True,
    )
    if len(results) != 1:
        raise RuntimeError(f"expected one PP-OCRv6 result, received {len(results)}")
    payload = results[0].json["res"]
    geometry = _validate_payload(payload)
    elapsed = time.perf_counter() - started
    scores = [float(score) for score in payload["rec_scores"]]
    manifest = {
        "schema_version": 1,
        "state": "OCR_COMPLETE",
        "dataset_role": args.dataset_role,
        "evidence_role": "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY",
        "confidence_policy": "NO_AUTOMATIC_TRUTH_OR_SCHEMA_PROMOTION",
        "input": {
            "path": input_path.as_posix(),
            "size_bytes": input_path.stat().st_size,
            "sha256": _sha256(input_path),
        },
        "code": git,
        "configuration": {
            "path": config_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": _sha256(config_path),
            "runner_path": Path(__file__).relative_to(PROJECT_ROOT).as_posix(),
            "runner_sha256": _sha256(Path(__file__)),
            "implicit_orientation_or_unwarp": False,
            "network_policy": "PROCESS_SOCKET_CONNECT_DENIED",
            "mkldnn": False,
            "precision": "fp32",
            "cpu_threads": args.cpu_threads,
        },
        "runtime": {
            "manifest_path": RUNTIME_MANIFEST.relative_to(PROJECT_ROOT).as_posix(),
            "manifest_sha256": _sha256(RUNTIME_MANIFEST),
            "paddlepaddle": importlib.metadata.version("paddlepaddle"),
            "paddleocr": importlib.metadata.version("paddleocr"),
            "paddlex": importlib.metadata.version("paddlex"),
            "device": paddle.device.get_device(),
            "compiled_with_cuda": paddle.device.is_compiled_with_cuda(),
            "models": models,
        },
        "metrics": {
            **geometry,
            "wall_seconds": elapsed,
            "minimum_line_score": min(scores) if scores else None,
            "mean_line_score": statistics.fmean(scores) if scores else None,
            "lines_below_0_8": sum(score < 0.8 for score in scores),
            "lines_below_0_9": sum(score < 0.9 for score in scores),
        },
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
    }
    _write_artifacts(output_directory, payload, manifest)
    print(
        json.dumps(
            {
                "status": "PASS",
                "output_directory": output_directory.as_posix(),
                "metrics": manifest["metrics"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
