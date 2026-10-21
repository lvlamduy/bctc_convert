"""Upload one PRIMARY_STATEMENTS run as immutable S3 artifacts.

Every file under ``--run-dir`` (and each ``--extra`` file) is written to a new
key under ``bctc-ai/primary-statements/2025-current/v1/runs/<run-id>/`` with
``IfNoneMatch``, a SHA-256 checksum and exact VersionId readback. Nothing is
overwritten or deleted. A manifest listing every key, VersionId, size and
SHA-256 is uploaded last the same way and written locally.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import boto3

BUCKET = "test-s3-duylv"
REGION = "us-east-1"
PREFIX = "bctc-ai/primary-statements/2025-current/v1/runs/"
CONTENT_TYPES = {".json": "application/json", ".sqlite3": "application/vnd.sqlite3", ".log": "text/plain",
                 ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".md": "text/markdown"}


def _put(s3, key: str, raw: bytes, content_type: str) -> dict[str, object]:
    digest = hashlib.sha256(raw)
    response = s3.put_object(
        Bucket=BUCKET, Key=key, Body=raw, ContentType=content_type, Metadata={"sha256": digest.hexdigest()},
        IfNoneMatch="*", ChecksumSHA256=base64.b64encode(digest.digest()).decode("ascii"),
    )
    version = response.get("VersionId")
    if not version:
        raise RuntimeError("missing VersionId: " + key)
    check = s3.get_object(Bucket=BUCKET, Key=key, VersionId=version)
    if check["VersionId"] != version or hashlib.sha256(check["Body"].read()).hexdigest() != digest.hexdigest():
        raise RuntimeError("exact-version readback failed: " + key)
    return {"key": key, "version_id": version, "sha256": digest.hexdigest(), "size_bytes": len(raw)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--git-head", required=True)
    parser.add_argument("--extra", type=Path, action="append", default=[])
    parser.add_argument("--local-manifest", type=Path, required=True)
    args = parser.parse_args()

    s3 = boto3.client("s3", region_name=REGION)
    if s3.get_bucket_versioning(Bucket=BUCKET).get("Status") != "Enabled":
        raise RuntimeError("bucket versioning is not enabled")
    account = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
    base = PREFIX + args.run_id + "/"
    files = sorted(path for path in args.run_dir.rglob("*") if path.is_file())
    entries = []
    for path in files:
        relative = path.relative_to(args.run_dir).as_posix()
        entries.append({"path": relative, **_put(s3, base + relative, path.read_bytes(),
                                                  CONTENT_TYPES.get(path.suffix, "application/octet-stream"))})
    for path in args.extra:
        entries.append({"path": "extra/" + path.name, **_put(s3, base + "extra/" + path.name, path.read_bytes(),
                                                              CONTENT_TYPES.get(path.suffix, "application/octet-stream"))})
    manifest = {
        "schema": "bctc-ai-primary-statements-artifact-manifest-v1",
        "run_id": args.run_id, "git_head": args.git_head, "aws_account": account, "bucket": BUCKET,
        "created_at_utc": datetime.now(UTC).isoformat(), "objects": entries,
    }
    raw = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    manifest_ref = _put(s3, base + "ARTIFACT_MANIFEST.json", raw, "application/json")
    args.local_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.local_manifest.write_bytes(raw)
    print(json.dumps({"manifest": manifest_ref, "objects": len(entries)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
