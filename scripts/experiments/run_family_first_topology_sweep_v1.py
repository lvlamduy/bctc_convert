#!/usr/bin/env python3
"""Build or replay one generic family topology sweep over every filing."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation.family_first_semantic_index_v1 import (  # noqa: E402
    authenticate_family_first_semantic_index_v1,
)
from bctc_ai.evaluation.family_first_semantic_label_archive_v1 import (  # noqa: E402
    authenticate_family_first_semantic_label_archive_v1,
)
from bctc_ai.evaluation.family_first_topology_sweep_v1 import (  # noqa: E402
    build_authenticated_family_first_topology_sweep_v1,
    validate_authenticated_family_first_topology_sweep_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
)

OUTPUT_ROOT = Path("output/calibration/family-first-topology-sweeps-v1")
_FAMILY_ID = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")


class FamilyFirstTopologySweepCliV1Error(RuntimeError):
    """The tracked family spec or fixed sweep artifact drifted."""


def _error(message: str) -> FamilyFirstTopologySweepCliV1Error:
    return FamilyFirstTopologySweepCliV1Error(message)


def _duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _error("family spec contains a duplicate JSON field")
        value[key] = item
    return value


def _stable_bytes(path: Path, label: str) -> bytes:
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise _error(f"{label} must be one single-link regular file")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        chunks = []
        while True:
            chunk = os.read(descriptor, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    payload = b"".join(chunks)
    after = path.stat(follow_symlinks=False)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ) or len(payload) != before.st_size:
        raise _error(f"{label} changed while being read")
    return payload


def _family_spec(root: Path, relative: Path) -> dict[str, Any]:
    if (
        not isinstance(relative, Path)
        or relative.is_absolute()
        or ".." in relative.parts
        or len(relative.parts) != 3
        or relative.parts[:2] != ("config", "families")
        or relative.suffix != ".json"
    ):
        raise _error("family spec must be one project-relative config/families JSON path")
    cursor = root
    for component in relative.parts[:-1]:
        cursor /= component
        metadata = cursor.stat(follow_symlinks=False)
        if not stat.S_ISDIR(metadata.st_mode) or cursor.is_symlink():
            raise _error("family spec parent path is not one nofollow directory")
    payload = _stable_bytes(root / relative, "family topology spec")
    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_duplicates,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                _error("family spec contains a non-finite JSON value")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("family topology spec is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise _error("family topology spec must be one JSON object")
    return value


def _artifact_path(spec: dict[str, Any]) -> Path:
    family_id = spec.get("family_id")
    if type(family_id) is not str or _FAMILY_ID.fullmatch(family_id) is None:
        raise _error("family topology spec has an unsafe family_id")
    return OUTPUT_ROOT / (family_id.lower().replace("_", "-") + ".json")


def _write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o444,
    )
    try:
        view = memoryview(payload)
        while view:
            count = os.write(descriptor, view)
            if count <= 0:
                raise _error("family sweep artifact write made no progress")
            view = view[count:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def run_family_first_topology_sweep_v1(
    project_root: Path,
    *,
    model_cache: Path,
    family_spec_path: Path,
    command: str,
) -> dict[str, Any]:
    """Build or exact-replay a deterministic all-filing family proposal."""

    if command not in {"build", "verify"}:
        raise _error("family topology sweep command must be build or verify")
    root = project_root.resolve()
    spec = _family_spec(root, family_spec_path)
    output_relative = _artifact_path(spec)
    archive = authenticate_family_first_semantic_label_archive_v1(root, model_cache=model_cache)
    semantic_index = authenticate_family_first_semantic_index_v1(root, archive)
    if command == "build":
        result = build_authenticated_family_first_topology_sweep_v1(semantic_index, spec)
        _write_exclusive(root / output_relative, canonical_json_bytes_v1(result) + b"\n")
    else:
        payload = _stable_bytes(root / output_relative, "family topology sweep artifact")
        try:
            persisted = json.loads(
                payload.decode("utf-8", errors="strict"),
                object_pairs_hook=_duplicates,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("family topology sweep artifact is not strict JSON") from exc
        if type(persisted) is not dict or payload != canonical_json_bytes_v1(persisted) + b"\n":
            raise _error("family topology sweep artifact is not canonical JSON")
        result = validate_authenticated_family_first_topology_sweep_replay_v1(
            persisted, semantic_index, spec
        )
    return {
        "family_id": result["family_id"],
        "metrics": result["metrics"],
        "output_path": output_relative.as_posix(),
        "sweep_id": result["sweep_id"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-cache", required=True, type=Path)
    parser.add_argument("--family-spec", required=True, type=Path)
    parser.add_argument("command", choices=("build", "verify"))
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = run_family_first_topology_sweep_v1(
        PROJECT_ROOT,
        model_cache=args.model_cache,
        family_spec_path=args.family_spec,
        command=args.command,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
