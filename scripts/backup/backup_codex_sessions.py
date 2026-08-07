from __future__ import annotations

import argparse
import json
import os
import socket
from dataclasses import replace
from pathlib import Path

from bctc_ai.storage.codex_session_backup import (
    backup_sessions_to_s3,
    result_payload,
)
from bctc_ai.storage.s3_snapshot import AwsCli, load_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Back up ~/.codex/sessions only to an immutable, checksum-verified S3 key"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "config/backup/s3-v1.toml",
    )
    parser.add_argument("--profile", default=None)
    parser.add_argument("--prefix", default="codex-sessions")
    parser.add_argument("--host", default=socket.gethostname())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = load_settings(args.config)
    if args.profile:
        settings = replace(settings, profile=args.profile)
    result = backup_sessions_to_s3(
        source_root=args.source,
        client=AwsCli(settings),
        prefix=args.prefix,
        host=args.host,
    )
    print(json.dumps(result_payload(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
