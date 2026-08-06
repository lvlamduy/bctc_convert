from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from bctc_ai.preprocessing.targeted_run import build_targeted_reread_inputs

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _git_state() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {"commit": commit, "dirty": bool(status.strip())}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build hash-bound E-0016 targeted reread crops from the original PDFs"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0016-mbb-vcb-targeted-reread.yaml"),
    )
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    payload = build_targeted_reread_inputs(
        project_root=PROJECT_ROOT,
        config_path=args.config,
        output_directory=args.output_directory,
        git_state=_git_state(),
        allow_dirty=args.allow_dirty,
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "output_directory": args.output_directory.resolve().as_posix(),
                "metrics": payload["metrics"],
                "variant_selection_status": payload["diagnostics"]["variant_selection_status"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
