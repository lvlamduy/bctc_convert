from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.document_phase.statement_evidence import (
    StatementEvidenceError,
    load_ocr_pages_from_batch,
)
from bctc_ai.document_phase.statement_locator import (
    load_statement_locator_config,
    locate_statement_pages,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _git_state() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return {"commit": commit, "dirty": dirty}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Locate an ordered bank main-statement block from sealed word OCR"
    )
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    git = _git_state()
    if git["dirty"] and not args.allow_dirty:
        raise StatementEvidenceError("refusing statement evidence from a dirty worktree")
    batch_root = args.batch_root.resolve()
    config_path = args.config.resolve()
    output_path = args.output.resolve()
    batch, pages = load_ocr_pages_from_batch(
        batch_root,
        project_root=PROJECT_ROOT,
    )
    config = load_statement_locator_config(config_path)
    result = locate_statement_pages(pages, config)
    payload = {
        "format_version": 1,
        "state": "STATEMENT_LOCATION_COMPLETE" if not result["errors"] else "UNRESOLVED",
        "dataset_role": batch["dataset_role"],
        "source": batch["source"],
        "batch": {
            "path": batch_root.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(batch_root / "batch_manifest.json"),
            "identity_sha256": batch["batch_identity"],
            "checkpoint_state": batch["state"],
            "completed_pages": len(batch["pages"]),
            "requested_pages": len(batch["requested_pages"]),
        },
        "configuration": {
            "path": config_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(config_path),
        },
        "algorithm": {
            "path": Path(__file__).relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(Path(__file__)),
            "locator_path": "src/bctc_ai/document_phase/statement_locator.py",
            "locator_sha256": sha256_file(
                PROJECT_ROOT / "src/bctc_ai/document_phase/statement_locator.py"
            ),
        },
        "code": git,
        "result": result,
        "generated_at": datetime.now(UTC).isoformat(),
        "claim_boundary": (
            "Page/type/scope location proposal only. It does not map rows, choose a conflicted "
            "cash-flow schema block, or promote OCR values."
        ),
    }
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite statement-location output: {output_path}")
    atomic_write_json(output_path, payload)
    print(
        json.dumps(
            {
                "state": payload["state"],
                "output": output_path.as_posix(),
                "block": result.get("block"),
                "cash_flow": result.get("cash_flow"),
                "errors": result["errors"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if not result["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
