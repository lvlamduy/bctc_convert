from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import stat
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bctc_ai.core.hashing import sha256_bytes  # noqa: E402
from bctc_ai.corpus.wave1_role_b_page_reader import (  # noqa: E402
    POLICY_RELATIVE_PATH,
    WaveOneRoleBPageReaderError,
    build_wave_one_role_b_route_plan,
    canonical_json_bytes,
    seal_wave_one_role_b_execution_plan,
)


def _exclusive_write(path: Path, payload: bytes) -> None:
    expected = (
        PROJECT_ROOT / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/"
        "wave-1-role-b-page-read-plan.json"
    )
    path = path.absolute()
    if path != expected:
        raise WaveOneRoleBPageReaderError("plan output is not the fixed policy location")
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    descriptors = [os.open(PROJECT_ROOT, directory_flags)]
    root_identity = os.fstat(descriptors[0])
    hierarchy = [(PROJECT_ROOT, (root_identity.st_dev, root_identity.st_ino))]
    current = PROJECT_ROOT
    try:
        for component in path.parent.relative_to(PROJECT_ROOT).parts:
            current /= component
            try:
                directory = os.open(component, directory_flags, dir_fd=descriptors[-1])
            except FileNotFoundError:
                try:
                    os.mkdir(component, 0o755, dir_fd=descriptors[-1])
                    os.fsync(descriptors[-1])
                except FileExistsError:
                    pass
                directory = os.open(component, directory_flags, dir_fd=descriptors[-1])
            descriptors.append(directory)
            identity = os.fstat(directory)
            hierarchy.append((current, (identity.st_dev, identity.st_ino)))
    except BaseException:
        for open_descriptor in reversed(descriptors):
            os.close(open_descriptor)
        raise
    directory = descriptors[-1]
    temporary_name = f".{path.name}.{secrets.token_hex(16)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    temporary_identity: tuple[int, int] | None = None
    try:
        descriptor = os.open(temporary_name, flags, 0o644, dir_fd=directory)
        identity = os.fstat(descriptor)
        temporary_identity = (identity.st_dev, identity.st_ino)
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o444)
        os.fsync(descriptor)
        owned = os.fstat(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.link(
            temporary_name,
            path.name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
            follow_symlinks=False,
        )
        os.fsync(directory)
        final_flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            final_flags |= os.O_NOFOLLOW
        final_descriptor = os.open(path.name, final_flags, dir_fd=directory)
        try:
            final_identity = os.fstat(final_descriptor)
            hasher = hashlib.sha256()
            while block := os.read(final_descriptor, 1024 * 1024):
                hasher.update(block)
            named_identity = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
            expected_identity = (owned.st_dev, owned.st_ino, len(payload))
            if (
                not stat.S_ISREG(final_identity.st_mode)
                or stat.S_IMODE(final_identity.st_mode) != 0o444
                or (final_identity.st_dev, final_identity.st_ino, final_identity.st_size)
                != expected_identity
                or (named_identity.st_dev, named_identity.st_ino, named_identity.st_size)
                != expected_identity
                or hasher.digest() != hashlib.sha256(payload).digest()
            ):
                raise WaveOneRoleBPageReaderError("published plan byte identity drifted")
        finally:
            os.close(final_descriptor)
        for hierarchy_path, expected_hierarchy_identity in hierarchy:
            observed = hierarchy_path.stat(follow_symlinks=False)
            if (
                stat.S_ISLNK(observed.st_mode)
                or (
                    observed.st_dev,
                    observed.st_ino,
                )
                != expected_hierarchy_identity
            ):
                raise WaveOneRoleBPageReaderError(
                    "plan output hierarchy changed during publication"
                )
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_identity is not None:
            try:
                observed = os.stat(temporary_name, dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                observed = None
            if observed is not None and (observed.st_dev, observed.st_ino) == temporary_identity:
                os.unlink(temporary_name, dir_fd=directory)
        for open_descriptor in reversed(descriptors):
            os.close(open_descriptor)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan the receipt-bound Wave 1 Role-B page reader")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("route-plan", help="replay the deterministic route plan")
    seal = subcommands.add_parser("seal-plan", help="bind clean code, runtime, and models")
    seal.add_argument("--model-cache", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    policy_path = PROJECT_ROOT / POLICY_RELATIVE_PATH
    if arguments.command == "route-plan":
        plan = build_wave_one_role_b_route_plan(PROJECT_ROOT, policy_path)
        output = None
    elif arguments.command == "seal-plan":
        plan = seal_wave_one_role_b_execution_plan(
            PROJECT_ROOT,
            model_cache=arguments.model_cache,
            require_clean_git=True,
        )
        output = (
            PROJECT_ROOT / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/"
            "wave-1-role-b-page-read-plan.json"
        )
    else:  # pragma: no cover - argparse guarantees the command set
        raise WaveOneRoleBPageReaderError("unsupported command")
    payload = canonical_json_bytes(plan)
    if output:
        _exclusive_write(output, payload)
    print(
        json.dumps(
            {
                "status": plan["status"],
                "selection_receipt_sha256": plan["selection_receipt_sha256"],
                "route_plan_sha256": plan["route_plan_sha256"],
                "artifact_sha256": sha256_bytes(payload),
                "artifact_size_bytes": len(payload),
                "output": output.relative_to(PROJECT_ROOT).as_posix() if output else None,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
