#!/usr/bin/env python3
"""Immutable cooperative S3 mailbox; not a lock, lease, or worker launcher."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

BUCKET = "test-s3-duylv"
REGION = "us-east-1"
PREFIX = "bctc-ai/coordination/2025-current/v1"
STATES = (
    "WAITING_FOR_PEER",
    "HEARTBEAT",
    "BLOCKED",
    "CHECKPOINT",
    "READY_FOR_INTEGRATION",
    "RELEASED",
    "INTEGRATED",
)


class GateError(RuntimeError):
    """Stop before further action when protocol evidence is absent or inconsistent."""


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("ascii")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode(data: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise GateError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(data, object_pairs_hook=unique)
        if not isinstance(value, dict) or canonical(value) != data:
            raise GateError("Object must be a canonical JSON object")
        return value
    except (ValueError, UnicodeError) as exc:
        raise GateError("Invalid JSON object") from exc


class S3:
    def __init__(self, profile: str | None = None):
        self.profile = profile

    def call(self, operation: str, args: list[str], *, missing_ok=False, conflict_ok=False):
        command = ["aws", "--region", REGION, "--no-cli-pager", "--output", "json"]
        if self.profile:
            command += ["--profile", self.profile]
        command += ["s3api", operation, "--bucket", BUCKET, *args]
        result = subprocess.run(command, capture_output=True, check=False, timeout=120)
        if result.returncode:
            error = result.stderr.decode("utf-8", errors="replace")
            if missing_ok and re.search(r"\(NoSuchKey\).*GetObject", error):
                return None
            if conflict_ok and re.search(r"\(PreconditionFailed\).*PutObject", error):
                return None
            raise GateError(f"S3 {operation} failed: {error.strip()}")
        try:
            return json.loads(result.stdout or b"{}")
        except (ValueError, UnicodeError) as exc:
            raise GateError(f"Invalid S3 {operation} response") from exc

    def get(self, key: str, version: str | None = None):
        with tempfile.TemporaryDirectory(prefix="bctc-mailbox-") as directory:
            path = Path(directory) / "object"
            args = ["--key", key]
            if version:
                args += ["--version-id", version]
            metadata = self.call("get-object", [*args, str(path)], missing_ok=not version)
            if metadata is None:
                return None
            actual_version = metadata.get("VersionId")
            if not actual_version or actual_version == "null":
                raise GateError("Mailbox requires an enabled, versioned S3 bucket")
            if version and actual_version != version:
                raise GateError("S3 returned an unexpected object version")
            return path.read_bytes(), actual_version

    def create(self, key: str, payload: dict) -> dict:
        data = canonical(payload)
        with tempfile.TemporaryDirectory(prefix="bctc-mailbox-") as directory:
            path = Path(directory) / "object.json"
            path.write_bytes(data)
            metadata = self.call(
                "put-object",
                [
                    "--key",
                    key,
                    "--body",
                    str(path),
                    "--if-none-match",
                    "*",
                    "--server-side-encryption",
                    "AES256",
                    "--checksum-algorithm",
                    "SHA256",
                    "--content-type",
                    "application/json",
                ],
                conflict_ok=True,
            )
        version = metadata.get("VersionId") if metadata is not None else None
        if metadata is not None and (not version or version == "null"):
            raise GateError("PUT did not return an immutable VersionId")
        restored = self.get(key, version)
        if restored is None or restored[0] != data:
            raise GateError(f"Immutable object conflict or read-back mismatch: {key}")
        return {
            "key": key,
            "version_id": restored[1],
            "sha256": sha256(data),
            "bytes": len(data),
            "already_present": metadata is None,
        }

    def keys(self, prefix: str) -> list[str]:
        # AWS CLI automatically consumes ListObjectsV2 continuation tokens.
        result = self.call("list-objects-v2", ["--prefix", prefix])
        return sorted(item["Key"] for item in result.get("Contents", []))


def validate_contract(contract: dict) -> None:
    for field, expected in (("bucket", BUCKET), ("region", REGION), ("prefix", PREFIX)):
        if field in contract and contract[field] != expected:
            raise GateError(f"Unexpected fixed mailbox {field}")
    if contract.get("protocol_version") != 1:
        raise GateError("Unsupported protocol version")
    if not re.fullmatch(r"[a-zA-Z0-9-]{1,100}", contract.get("round_id", "")):
        raise GateError("Invalid round ID")
    if not re.fullmatch(r"[0-9a-f]{40}", contract.get("base_commit", "")):
        raise GateError("Invalid base commit")
    roles = contract.get("roles", {})
    if set(roles) != {"vps", "laptop"}:
        raise GateError("Expected exactly the vps and laptop roles")
    for worker, family in (("vps", "F36"), ("laptop", "F39")):
        role = roles[worker]
        if role.get("family") != family or not role.get("branch", "").startswith("codex/"):
            raise GateError("Unexpected worker ownership")
        if not role.get("allowed_paths") or not all(
            isinstance(path, str)
            and path
            and not path.startswith("/")
            and ".." not in path.split("/")
            for path in role["allowed_paths"]
        ):
            raise GateError("Missing or invalid owned path patterns")
    if roles["vps"]["branch"] == roles["laptop"]["branch"]:
        raise GateError("Workers must use separate branches")
    pins = contract.get("frozen_sha256", {})
    if not pins or not all(re.fullmatch(r"[0-9a-f]{64}", value) for value in pins.values()):
        raise GateError("Missing or malformed frozen SHA-256 pins")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False, timeout=30
    )
    if result.returncode:
        raise GateError(f"Git preflight failed: {' '.join(args[:2])}")
    return result.stdout.decode("utf-8")


def check_repo(contract: dict, worker: str, repo: Path) -> str:
    role = contract["roles"][worker]
    if git(repo, "branch", "--show-current").strip() != role["branch"]:
        raise GateError(f"Worker {worker} must use branch {role['branch']}")
    git(repo, "merge-base", "--is-ancestor", contract["base_commit"], "HEAD")
    for relative, expected in contract["frozen_sha256"].items():
        path = (repo / relative).resolve()
        if not path.is_relative_to(repo.resolve()) or sha256(path.read_bytes()) != expected:
            raise GateError(f"Frozen file drift: {relative}")
    patterns = role["allowed_paths"] + contract.get("common_allowed_paths", [])
    peer = "laptop" if worker == "vps" else "vps"
    peer_patterns = contract["roles"][peer]["allowed_paths"]
    paths = set()
    for args in (
        ("diff", "--name-only", "--no-renames", "-z", contract["base_commit"], "HEAD"),
        ("diff", "--cached", "--name-only", "--no-renames", "-z", "HEAD"),
        ("diff", "--name-only", "--no-renames", "-z", "HEAD"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ):
        paths.update(filter(None, git(repo, *args).split("\0")))
    for path in sorted(paths):
        if any(fnmatch.fnmatchcase(path, p) for p in peer_patterns) or not any(
            fnmatch.fnmatchcase(path, pattern) for pattern in patterns
        ):
            raise GateError(f"Out-of-scope or peer-owned change: {path}")
    return git(repo, "rev-parse", "HEAD").strip()


class Mailbox:
    def __init__(self, contract: dict, transport: S3):
        validate_contract(contract)
        self.contract = contract
        self.transport = transport
        self.digest = sha256(canonical(contract))
        self.round_prefix = f"{PREFIX}/rounds/{contract['round_id']}"

    def envelope(self, worker: str) -> dict:
        role = self.contract["roles"][worker]
        return {
            "protocol_version": 1,
            "round_id": self.contract["round_id"],
            "contract_sha256": self.digest,
            "worker": worker,
            "family": role["family"],
            "branch": role["branch"],
        }

    def join_payload(self, worker: str) -> dict:
        return {**self.envelope(worker), "accept_disjoint_ownership": True}

    def require_contract(self) -> None:
        remote = self.transport.get(f"{self.round_prefix}/contract.json")
        if remote is None or remote[0] != canonical(self.contract):
            raise GateError(
                "Remote contract is missing or differs from the reviewed local contract"
            )

    def events(self) -> tuple[list[dict], list[dict]]:
        result, inbox = [], []
        round_events = f"{PREFIX}/events/{self.contract['round_id']}/"
        for key in self.transport.keys(f"{PREFIX}/events/"):
            remote = self.transport.get(key)
            if remote is None:
                raise GateError(f"Listed event disappeared: {key}")
            if not key.startswith(round_events):
                # Discovery/messages from peers may precede installation of this helper.
                # Never interpret these unvalidated messages as joins or ownership changes.
                try:
                    body = json.loads(remote[0])
                except (ValueError, UnicodeError):
                    body = {"error": "Non-JSON inbox object; inspect separately"}
                inbox.append(
                    {
                        "key": key,
                        "version_id": remote[1],
                        "sha256": sha256(remote[0]),
                        "informational_only": True,
                        "body": body,
                    }
                )
                continue
            event = decode(remote[0])
            worker = event.get("worker")
            if (
                worker not in self.contract["roles"]
                or any(event.get(field) != value for field, value in self.envelope(worker).items())
                or event.get("state") not in STATES
            ):
                raise GateError(f"Invalid event envelope: {key}")
            result.append({**event, "key": key, "version_id": remote[1]})
        return result, inbox

    def status(self) -> dict:
        self.require_contract()
        joined = []
        for worker in self.contract["roles"]:
            remote = self.transport.get(f"{self.round_prefix}/joins/{worker}.json")
            if remote is None:
                continue
            if remote[0] != canonical(self.join_payload(worker)):
                raise GateError(f"Join does not authenticate the current ownership: {worker}")
            joined.append(worker)
        events, inbox = self.events()
        closed = any(event["state"] in {"RELEASED", "INTEGRATED"} for event in events)
        return {
            "contract_sha256": self.digest,
            "joined": sorted(joined),
            "handshake": "READY" if len(joined) == 2 else "PENDING",
            "round_closed": closed,
            "events": events,
            "informational_inbox": inbox,
        }

    def check(self, worker: str, repo: Path) -> str:
        status = self.status()
        if status["handshake"] != "READY" or status["round_closed"]:
            raise GateError("Both matching joins are required; released rounds cannot resume")
        return check_repo(self.contract, worker, repo)

    def send(self, worker: str, state: str, message: str, repo: Path) -> dict:
        self.require_contract()
        if state not in STATES:
            raise GateError("Unknown event state")
        if state in {"CHECKPOINT", "READY_FOR_INTEGRATION", "INTEGRATED"}:
            head = self.check(worker, repo)
        else:
            head = check_repo(self.contract, worker, repo)
        if state == "INTEGRATED" and worker != "laptop":
            raise GateError("Only the laptop integrator can report integration")
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        payload = {
            **self.envelope(worker),
            "state": state,
            "message": message,
            "head": head,
            "created_at": stamp,
        }
        key = f"{PREFIX}/events/{self.contract['round_id']}/{stamp}-{worker}-{uuid.uuid4()}.json"
        return self.transport.create(key, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--contract", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("bootstrap")
    commands.add_parser("status")
    for name in ("join", "check", "send"):
        command = commands.add_parser(name)
        command.add_argument("--worker", choices=("vps", "laptop"), required=True)
        if name == "join":
            command.add_argument("--accept-disjoint-ownership", action="store_true", required=True)
        if name == "send":
            command.add_argument("--state", choices=STATES, required=True)
            command.add_argument("--message", required=True)
    args = parser.parse_args(argv)
    try:
        path = args.contract or args.repo / "config/coordination/dual-machine-v1.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        mailbox = Mailbox(contract, S3(args.profile))
        if args.command == "bootstrap":
            result = mailbox.transport.create(f"{mailbox.round_prefix}/contract.json", contract)
        elif args.command == "status":
            result = mailbox.status()
        elif args.command == "join":
            mailbox.require_contract()
            check_repo(contract, args.worker, args.repo)
            result = mailbox.transport.create(
                f"{mailbox.round_prefix}/joins/{args.worker}.json",
                mailbox.join_payload(args.worker),
            )
        elif args.command == "check":
            result = {"gate": "PASS", "head": mailbox.check(args.worker, args.repo)}
        else:
            result = mailbox.send(args.worker, args.state, args.message, args.repo)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (GateError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
