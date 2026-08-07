from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from bctc_ai.storage.s3_artifact_backup import backup_artifacts_to_s3
from bctc_ai.storage.s3_snapshot import load_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Back up exact output paths as a restore-tested child of a full S3 snapshot"
    )
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "config/backup/s3-v1.toml",
    )
    parser.add_argument("--profile")
    parser.add_argument("--parent-manifest-key", required=True)
    parser.add_argument("--parent-manifest-sha256", required=True)
    parser.add_argument("--parent-run-record-key", required=True)
    parser.add_argument("--parent-run-record-sha256", required=True)
    args = parser.parse_args()
    settings = load_settings(args.config)
    if args.profile:
        settings = replace(settings, profile=args.profile)
    result = backup_artifacts_to_s3(
        PROJECT_ROOT,
        settings=settings,
        selected_paths=args.path,
        parent_manifest_key=args.parent_manifest_key,
        parent_manifest_sha256=args.parent_manifest_sha256,
        parent_run_record_key=args.parent_run_record_key,
        parent_run_record_sha256=args.parent_run_record_sha256,
        label=args.label,
    )
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
