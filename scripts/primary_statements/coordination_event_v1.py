"""Publish one immutable PRIMARY_STATEMENTS coordination event.

The event reuses the existing ``bctc-ai-coordination-event-v1`` envelope. It
does not invent a family ID: ``family_id`` is null and the claimed namespace is
carried in ``scope.claim_scope``. Every write uses a fresh key, ``IfNoneMatch``,
a SHA-256 checksum and exact VersionId readback. Existing events are only read.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3

BUCKET = "test-s3-duylv"
REGION = "us-east-1"
EVENT_PREFIX = "bctc-ai/coordination/2025-current/v1/events/"
WORKER_ID = "CLAUDE_PRIMARY"
CLAIM_SCOPE = "PRIMARY_STATEMENTS"
EVENT_TYPES = ("CLAIMED", "HEARTBEAT", "BLOCKED", "READY_FOR_INTEGRATION")


def _git(root: Path, *parts: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *parts], text=True).strip()


def _observed_refs(s3) -> list[dict[str, object]]:
    refs = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=EVENT_PREFIX):
        for item in page.get("Contents", []):
            response = s3.get_object(Bucket=BUCKET, Key=item["Key"])
            raw = response["Body"].read()
            refs.append(
                {
                    "key": item["Key"],
                    "version_id": response["VersionId"],
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "size_bytes": len(raw),
                }
            )
    return sorted(refs, key=lambda ref: ref["key"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-type", choices=EVENT_TYPES, required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--preflight-status", choices=("PASS", "FAIL"), required=True)
    parser.add_argument("--attachment", type=Path, action="append", default=[])
    parser.add_argument("--local-dir", type=Path, required=True)
    args = parser.parse_args()

    s3 = boto3.client("s3", region_name=REGION)
    if s3.get_bucket_versioning(Bucket=BUCKET).get("Status") != "Enabled":
        raise RuntimeError("coordination bucket versioning is not enabled")
    identity = boto3.client("sts", region_name=REGION).get_caller_identity()
    now = datetime.now(UTC)
    event_id = (
        now.strftime("%Y%m%dT%H%M%S%fZ")
        + f"-{WORKER_ID}-{args.event_type}-{uuid.uuid4().hex}"
    )
    attachments = []
    for path in args.attachment:
        raw = path.read_bytes()
        attachments.append(
            {
                "name": path.name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
                "content": json.loads(raw) if path.suffix == ".json" else None,
            }
        )
    event = {
        "schema": "bctc-ai-coordination-event-v1",
        "event_id": event_id,
        "created_at_utc": now.isoformat(),
        "event_type": args.event_type,
        "phase": args.phase,
        "worker_id": WORKER_ID,
        "family_id": None,
        "claim_active": args.event_type != "READY_FOR_INTEGRATION",
        "preflight_status": args.preflight_status,
        "message": args.message,
        "aws_account": identity["Account"],
        "git": {
            "base_commit": args.base_commit,
            "head": _git(args.worktree, "rev-parse", "HEAD"),
            "branch": _git(args.worktree, "branch", "--show-current"),
            "status_porcelain": _git(args.worktree, "status", "--porcelain"),
        },
        "scope": {
            "claim_scope": CLAIM_SCOPE,
            "statements": ["CDKT", "KQKD", "LCTT"],
            "claims_tm_or_any_family": False,
            "claims_f36_f37_f39": False,
            "report_year_from": 2025,
            "through": "current",
            "production_2024": False,
            "provider_calls_allowed": False,
            "shared_files_frozen": True,
            "push_branch": "codex/primary-statements-claude",
            "direct_common_branch_push_allowed": False,
        },
        "attachments": attachments,
        "observed_event_refs": _observed_refs(s3),
    }
    raw = json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    key = EVENT_PREFIX + event_id + ".json"
    response = s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=raw,
        ContentType="application/json",
        Metadata={"sha256": digest},
        IfNoneMatch="*",
        ChecksumSHA256=base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii"),
    )
    version = response.get("VersionId")
    if not version:
        raise RuntimeError("missing published VersionId: " + key)
    check = s3.get_object(Bucket=BUCKET, Key=key, VersionId=version)
    if check["Body"].read() != raw or check["VersionId"] != version:
        raise RuntimeError("published event exact-version readback failed: " + key)
    args.local_dir.mkdir(parents=True, exist_ok=True)
    local = args.local_dir / (event_id + ".json")
    local.write_bytes(raw)
    print(
        json.dumps(
            {
                "bucket": BUCKET,
                "key": key,
                "version_id": version,
                "sha256": digest,
                "size_bytes": len(raw),
                "local_path": str(local),
                "status": "PASS_EXACT_VERSION_READBACK",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
