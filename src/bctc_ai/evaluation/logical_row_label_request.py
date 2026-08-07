from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file


class LogicalRowLabelRequestError(RuntimeError):
    """Raised when an E-0035 crop manifest cannot yield a reference-blind request."""


_SAMPLE_FIELDS = {"sample_id", "category", "crop_path", "crop_sha256"}


def _git(project_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _resolve(project_root: Path, value: Path | str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        raise LogicalRowLabelRequestError(f"unsafe project-relative path: {value}")
    path = (project_root / raw).resolve()
    if not path.is_relative_to(project_root):
        raise LogicalRowLabelRequestError(f"path escapes project root: {value}")
    return path


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LogicalRowLabelRequestError(f"cannot load E-0035 crop manifest: {path}") from error
    if not isinstance(payload, dict):
        raise LogicalRowLabelRequestError("E-0035 crop manifest must be an object")
    return payload


def build_logical_row_label_request(
    project_root: Path,
    *,
    crop_manifest_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Strip all primary/reference context from the fixed E-0035 crop registry."""

    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise LogicalRowLabelRequestError("formal E-0036 request capture requires clean Git code")
    manifest_path = _resolve(project_root, crop_manifest_path)
    destination = _resolve(project_root, output_path)
    if destination.exists():
        raise LogicalRowLabelRequestError(f"refusing to overwrite E-0036 request: {destination}")
    manifest = _load_json(manifest_path)
    authority = manifest.get("authority")
    if (
        manifest.get("format_version") != 1
        or manifest.get("experiment_id") != "E-0035"
        or manifest.get("state") != "FROZEN_ALL_LOGICAL_ROW_LABEL_CROPS_NO_SEMANTIC_INFERENCE"
        or manifest.get("dataset_role") != "CALIBRATION"
        or manifest.get("git_dirty") is not False
        or manifest.get("sample_count") != 64
        or not isinstance(manifest.get("decoder_visible_sample_fields"), list)
        or set(manifest["decoder_visible_sample_fields"]) != _SAMPLE_FIELDS
        or manifest.get("reference_text_available_to_decoder") is not False
        or not isinstance(authority, dict)
        or authority.get("reader_receives_crop_pixels_only") is not True
        or authority.get("reader_may_change_geometry") is not False
        or authority.get("reader_may_change_numeric_value_or_status") is not False
        or authority.get("reader_may_assign_period_unit_scope_or_schema_id") is not False
    ):
        raise LogicalRowLabelRequestError("E-0035 crop-manifest identity or authority drifted")
    raw_samples = manifest.get("samples")
    if not isinstance(raw_samples, list) or len(raw_samples) != 64:
        raise LogicalRowLabelRequestError("E-0035 sample denominator drifted")

    samples: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in raw_samples:
        if not isinstance(raw, dict):
            raise LogicalRowLabelRequestError("E-0035 sample is not an object")
        sample = {field: str(raw.get(field, "")) for field in _SAMPLE_FIELDS}
        if (
            not sample["sample_id"]
            or sample["sample_id"] in seen
            or sample["category"] != "LOGICAL_ROW_LABEL"
        ):
            raise LogicalRowLabelRequestError("E-0035 sample identity drifted")
        seen.add(sample["sample_id"])
        crop = _resolve(project_root, sample["crop_path"])
        if not crop.is_file() or sha256_file(crop) != sample["crop_sha256"]:
            raise LogicalRowLabelRequestError(
                f"E-0035 crop is absent or hash-drifted: {sample['sample_id']}"
            )
        if set(sample) != _SAMPLE_FIELDS:
            raise AssertionError("E-0036 decoder sample allowlist drifted")
        samples.append(sample)

    payload: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "state": "READY_FOR_REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE",
        "dataset_role": "CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY",
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
    destination.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(destination, payload)
    return payload


__all__ = [
    "LogicalRowLabelRequestError",
    "build_logical_row_label_request",
]
