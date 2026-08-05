from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.sealing import seal_role_b_ocr_run


def _pages(value: str) -> tuple[int, ...]:
    pages: set[int] = set()
    for token in value.split(","):
        token = token.strip()
        if "-" in token:
            start, end = (int(part) for part in token.split("-", 1))
            if end < start:
                raise argparse.ArgumentTypeError(f"invalid page range: {token}")
            pages.update(range(start, end + 1))
        else:
            pages.add(int(token))
    if not pages or min(pages) < 1:
        raise argparse.ArgumentTypeError("pages must be positive")
    return tuple(sorted(pages))


def main() -> int:
    parser = argparse.ArgumentParser(description="Seal a completed Role B OCR run")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--pages", type=_pages, required=True)
    parser.add_argument("--model-cache-root", type=Path, required=True)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    run_root = args.run_root
    if not run_root.is_absolute():
        run_root = project_root / run_root
    result = seal_role_b_ocr_run(
        project_root,
        run_root,
        pages=args.pages,
        model_cache_root=args.model_cache_root,
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "seal_path": result["seal_path"],
                "seal_sha256": result["seal_sha256"],
                "metrics": result["metrics"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

