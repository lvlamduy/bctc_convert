from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bctc_ai.core.hashing import sha256_file


class RecoveryArtifactError(RuntimeError):
    """Raised when neither original bytes nor a registered recovery seal verifies."""


@dataclass(frozen=True)
class FrozenArtifactVerification:
    path: str
    expected_sha256: str
    status: str
    recovery_id: str | None = None
    recovery_seal_path: str | None = None


DEFAULT_REGISTRY = Path("data/registered/recovery_artifact_registry.json")


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RecoveryArtifactError(f"cannot load recovery registry artifact: {path}") from error
    if not isinstance(payload, dict):
        raise RecoveryArtifactError(f"recovery registry artifact must be an object: {path}")
    return payload


def _project_path(project_root: Path, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        raise RecoveryArtifactError(f"unsafe project-relative recovery path: {value!r}")
    path = (project_root / raw).resolve()
    if not path.is_relative_to(project_root):
        raise RecoveryArtifactError(f"recovery path escapes project root: {value!r}")
    return path


def _direct_verification(
    project_root: Path, path_value: str, expected_sha256: str
) -> FrozenArtifactVerification | None:
    path = _project_path(project_root, path_value)
    if not path.exists():
        return None
    if not path.is_file() or path.is_symlink():
        raise RecoveryArtifactError(f"frozen artifact is not a regular file: {path_value}")
    digest = sha256_file(path)
    if digest != expected_sha256:
        raise RecoveryArtifactError(
            f"frozen artifact SHA-256 drifted: {path_value}: {digest} != {expected_sha256}"
        )
    return FrozenArtifactVerification(
        path=path_value,
        expected_sha256=expected_sha256,
        status="DIRECT_BYTES_VERIFIED",
    )


def _matching_record(
    registry: dict[str, Any], path_value: str, expected_sha256: str
) -> dict[str, Any]:
    if (
        registry.get("format_version") != 1
        or registry.get("policy") != "EXPLICIT_LOST_ARTIFACT_FUNCTIONAL_REPRODUCTION_V1"
    ):
        raise RecoveryArtifactError("recovery artifact registry policy drifted")
    matches = [
        item
        for item in registry.get("records", [])
        if isinstance(item, dict)
        and item.get("lost_artifact", {}).get("path") == path_value
        and item.get("lost_artifact", {}).get("sha256") == expected_sha256
    ]
    if len(matches) != 1:
        raise RecoveryArtifactError(
            f"missing frozen artifact has no unique registered recovery: {path_value}"
        )
    return matches[0]


def _verify_recovery_seal(
    project_root: Path,
    record: dict[str, Any],
    *,
    path_value: str,
    expected_sha256: str,
) -> FrozenArtifactVerification:
    lost = record.get("lost_artifact")
    recovery = record.get("recovery_seal")
    if not isinstance(lost, dict) or not isinstance(recovery, dict):
        raise RecoveryArtifactError("recovery registry record is incomplete")
    seal_path_value = str(recovery.get("path", ""))
    seal_path = _project_path(project_root, seal_path_value)
    if not seal_path.is_file() or seal_path.is_symlink():
        raise RecoveryArtifactError(f"registered recovery seal is absent: {seal_path_value}")
    if (
        seal_path.stat().st_size != int(recovery.get("size_bytes", -1))
        or sha256_file(seal_path) != recovery.get("sha256")
    ):
        raise RecoveryArtifactError(f"registered recovery seal drifted: {seal_path_value}")
    seal = _load_object(seal_path)
    required_status = str(recovery.get("required_status", ""))
    if seal.get("status") != required_status:
        raise RecoveryArtifactError("registered recovery seal status drifted")
    seal_lost = seal.get("lost_artifact")
    if not isinstance(seal_lost, dict):
        raise RecoveryArtifactError("recovery seal has no lost-artifact identity")
    for key, expected in (
        ("path", path_value),
        ("sha256", expected_sha256),
        ("size_bytes", int(lost["size_bytes"])),
    ):
        if seal_lost.get(key) != expected:
            raise RecoveryArtifactError(f"recovery seal lost-artifact {key} drifted")
    reproduction = seal.get("reproduction")
    page_evidence = seal.get("page_evidence")
    if (
        not isinstance(reproduction, dict)
        or reproduction.get("original_batch_manifest_recovered") is not False
        or reproduction.get("batch_identity_matches_original") is not False
        or seal.get("stable_metrics_exact") is not True
        or seal.get("discovery_result_json_exact") is not True
        or not isinstance(page_evidence, list)
        or {item.get("page") for item in page_evidence if isinstance(item, dict)} != {3, 4}
        or not all(
            item.get("render_byte_exact") is True
            and item.get("canonical_historical_ocr_byte_exact") is True
            and item.get("only_canonicalized_field") == "input_path"
            for item in page_evidence
            if isinstance(item, dict)
        )
    ):
        raise RecoveryArtifactError("recovery seal equivalence gates are incomplete")
    if record.get("allowed_use") != "CONTROL_REGRESSION_WITH_EXPLICIT_RECOVERY_STATUS":
        raise RecoveryArtifactError("recovery registry allowed-use boundary drifted")
    forbidden = set(record.get("forbidden_use", []))
    if "silently_replace_historical_hash" not in forbidden:
        raise RecoveryArtifactError("recovery registry lacks silent-replacement prohibition")
    return FrozenArtifactVerification(
        path=path_value,
        expected_sha256=expected_sha256,
        status="FUNCTIONAL_RECOVERY_SEAL_VERIFIED_ORIGINAL_BYTES_ABSENT",
        recovery_id=str(seal.get("recovery_id")),
        recovery_seal_path=seal_path_value,
    )


def verify_frozen_artifact(
    project_root: Path,
    artifact: Mapping[str, Any],
    *,
    registry_path: Path = DEFAULT_REGISTRY,
) -> FrozenArtifactVerification:
    project_root = project_root.resolve()
    path_value = str(artifact.get("path", ""))
    expected_sha256 = str(artifact.get("sha256", ""))
    if not path_value or len(expected_sha256) != 64:
        raise RecoveryArtifactError("frozen artifact identity is incomplete")
    direct = _direct_verification(project_root, path_value, expected_sha256)
    if direct is not None:
        return direct
    registry_file = _project_path(project_root, registry_path.as_posix())
    registry = _load_object(registry_file)
    record = _matching_record(registry, path_value, expected_sha256)
    return _verify_recovery_seal(
        project_root,
        record,
        path_value=path_value,
        expected_sha256=expected_sha256,
    )
