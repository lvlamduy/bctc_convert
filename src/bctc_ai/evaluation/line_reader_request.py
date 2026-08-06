from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file


class LineReaderRequestError(RuntimeError):
    pass


_SAMPLE_KEYS = {"sample_id", "category", "crop_path", "crop_sha256"}


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _resolve(project_root: Path, path: Path | str) -> Path:
    value = (project_root / path).resolve()
    try:
        value.relative_to(project_root)
    except ValueError as exc:
        raise LineReaderRequestError(f"path escapes project root: {path}") from exc
    return value


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise LineReaderRequestError(f"cannot read crop manifest: {path}") from exc
    if not isinstance(value, dict):
        raise LineReaderRequestError("crop manifest must be an object")
    return value


def prepare_line_reader_request(
    project_root: Path,
    *,
    crop_manifest_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise LineReaderRequestError("formal inference request requires a clean Git worktree")
    manifest_path = _resolve(project_root, crop_manifest_path)
    destination = _resolve(project_root, output_path)
    if destination.exists():
        raise LineReaderRequestError(f"refusing to overwrite inference request: {destination}")
    manifest = _load_json(manifest_path)
    if (
        manifest.get("experiment_id") != "E-0024"
        or manifest.get("state") != "FROZEN_CROPS_BUILT_NO_CHALLENGER_INFERENCE"
        or manifest.get("dataset_role") != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
        or manifest.get("git_dirty") is not False
    ):
        raise LineReaderRequestError("crop manifest identity or state is invalid")
    authority = manifest.get("authority")
    if not isinstance(authority, dict) or (
        authority.get("expected_text_must_not_enter_decoder") is not True
        or authority.get("semantic_reader_may_create_numeric_geometry") is not False
        or authority.get("semantic_reader_may_replace_digits_periods_units_or_signs") is not False
    ):
        raise LineReaderRequestError("crop manifest grants unsafe semantic-reader authority")
    raw_samples = manifest.get("samples")
    if not isinstance(raw_samples, list) or len(raw_samples) != manifest.get("sample_count"):
        raise LineReaderRequestError("crop manifest sample denominator is invalid")

    samples = []
    seen: set[str] = set()
    for raw in raw_samples:
        if not isinstance(raw, dict):
            raise LineReaderRequestError("crop manifest sample is not an object")
        sample_id = str(raw.get("sample_id", ""))
        if not sample_id or sample_id in seen:
            raise LineReaderRequestError("crop manifest sample IDs must be unique")
        seen.add(sample_id)
        crop = _resolve(project_root, str(raw.get("crop_path", "")))
        expected_hash = str(raw.get("crop_sha256", ""))
        if not crop.is_file() or sha256_file(crop) != expected_hash:
            raise LineReaderRequestError(f"crop is missing or hash-drifted: {sample_id}")
        sample = {
            "sample_id": sample_id,
            "category": str(raw.get("category", "")),
            "crop_path": crop.relative_to(project_root).as_posix(),
            "crop_sha256": expected_hash,
        }
        if set(sample) != _SAMPLE_KEYS:
            raise AssertionError("inference request sample allowlist drifted")
        samples.append(sample)

    payload: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0024",
        "state": "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE",
        "dataset_role": manifest["dataset_role"],
        "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
        "git_commit": _git(project_root, "rev-parse", "HEAD"),
        "git_dirty": False,
        "crop_manifest": {
            "path": manifest_path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(manifest_path),
        },
        "reference_text_available_to_reader": False,
        "sample_count": len(samples),
        "samples": samples,
    }
    atomic_write_json(destination, payload)
    return payload
