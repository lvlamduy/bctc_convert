from __future__ import annotations

import re
from typing import Any


class LogicalRowLabelReaderContractError(RuntimeError):
    """Raised when a semantic reader request exposes non-allowlisted context."""


REQUEST_KEYS = {
    "format_version",
    "experiment_id",
    "state",
    "dataset_role",
    "evidence_role",
    "git_commit",
    "git_dirty",
    "crop_manifest",
    "reference_text_available_to_reader",
    "sample_count",
    "samples",
}
SAMPLE_KEYS = {"sample_id", "category", "crop_path", "crop_sha256"}
_SAMPLE_ID = re.compile(r"page-[0-9]{4}-row-[0-9]{3}-label")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _is_safe_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parts = value.split("/")
    return not value.startswith("/") and ".." not in parts and "" not in parts


def validate_logical_row_label_reader_request(
    payload: dict[str, Any],
) -> list[dict[str, str]]:
    if set(payload) != REQUEST_KEYS:
        raise LogicalRowLabelReaderContractError(
            "logical-row label request contains forbidden top-level fields"
        )
    if (
        payload.get("format_version") != 1
        or payload.get("experiment_id") != "E-0036"
        or payload.get("state") != "READY_FOR_REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE"
        or payload.get("dataset_role") != "CALIBRATION"
        or payload.get("evidence_role") != "INDEPENDENT_VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY"
        or payload.get("git_dirty") is not False
        or payload.get("reference_text_available_to_reader") is not False
        or payload.get("sample_count") != 64
    ):
        raise LogicalRowLabelReaderContractError(
            "logical-row label request identity or reference isolation drifted"
        )
    crop_manifest = payload.get("crop_manifest")
    if (
        not isinstance(payload.get("git_commit"), str)
        or re.fullmatch(r"[0-9a-f]{40}", payload["git_commit"]) is None
        or not isinstance(crop_manifest, dict)
        or set(crop_manifest) != {"path", "sha256"}
        or not _is_safe_relative_path(crop_manifest.get("path"))
        or not isinstance(crop_manifest.get("sha256"), str)
        or _SHA256.fullmatch(crop_manifest["sha256"]) is None
    ):
        raise LogicalRowLabelReaderContractError("crop-manifest identity is invalid")
    raw_samples = payload.get("samples")
    if not isinstance(raw_samples, list) or len(raw_samples) != 64:
        raise LogicalRowLabelReaderContractError("logical-row label denominator drifted")
    samples: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in raw_samples:
        if not isinstance(raw, dict) or set(raw) != SAMPLE_KEYS:
            raise LogicalRowLabelReaderContractError(
                "logical-row label sample contains a forbidden field"
            )
        sample = {key: str(raw[key]) for key in SAMPLE_KEYS}
        sample_id = sample["sample_id"]
        if (
            _SAMPLE_ID.fullmatch(sample_id) is None
            or sample_id in seen
            or sample["category"] != "LOGICAL_ROW_LABEL"
            or not _is_safe_relative_path(sample["crop_path"])
            or _SHA256.fullmatch(sample["crop_sha256"]) is None
        ):
            raise LogicalRowLabelReaderContractError("logical-row label sample identity is invalid")
        seen.add(sample_id)
        samples.append(sample)
    return samples


__all__ = [
    "LogicalRowLabelReaderContractError",
    "REQUEST_KEYS",
    "SAMPLE_KEYS",
    "validate_logical_row_label_reader_request",
]
