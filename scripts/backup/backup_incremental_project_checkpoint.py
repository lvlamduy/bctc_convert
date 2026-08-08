from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from bctc_ai.storage.s3_incremental_checkpoint import (
    create_incremental_project_checkpoint,
)
from bctc_ai.storage.s3_snapshot import AwsCli, load_settings

DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Publish a parent-bound incremental project checkpoint without hydrating "
            "the offloaded source corpus"
        )
    )
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--profile")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--parent-manifest-key", required=True)
    parser.add_argument("--parent-manifest-sha256", required=True)
    parser.add_argument("--parent-run-record-key", required=True)
    parser.add_argument("--parent-run-record-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    config_path = (
        args.config.resolve()
        if args.config is not None
        else project_root / "config/backup/s3-v1.toml"
    )
    settings = load_settings(config_path)
    if args.profile:
        settings = replace(settings, profile=args.profile)
    result = create_incremental_project_checkpoint(
        project_root,
        settings=settings,
        selected_paths=args.path,
        parent_manifest_key=args.parent_manifest_key,
        parent_manifest_sha256=args.parent_manifest_sha256,
        parent_run_record_key=args.parent_run_record_key,
        parent_run_record_sha256=args.parent_run_record_sha256,
        client=AwsCli(settings),
        workers=args.workers,
        progress=print,
    )
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
