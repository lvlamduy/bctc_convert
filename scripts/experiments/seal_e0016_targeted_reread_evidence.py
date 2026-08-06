from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.targeted_reread_evidence import seal_targeted_reread_evidence

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
        description="Seal hash-bound E-0016 original-crop reader evidence"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0016-mbb-vcb-targeted-reread-evidence.yaml"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    result = seal_targeted_reread_evidence(
        project_root=PROJECT_ROOT,
        config_path=args.config,
        output_path=args.output,
        git_state=_git_state(),
        allow_dirty=args.allow_dirty,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "output_path": result["output_path"],
                "sha256": result["sha256"],
                "metrics": result["metrics"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
