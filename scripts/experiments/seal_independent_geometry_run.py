from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.sealing import seal_independent_geometry_run


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
    parser = argparse.ArgumentParser(description="Seal a completed independent geometry run")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--pages", type=_pages, required=True)
    parser.add_argument("--role-b-seal", type=Path, required=True)
    parser.add_argument("--model-cache-root", type=Path, required=True)
    args = parser.parse_args()
    project_root = args.project_root.resolve()

    def resolve(path: Path) -> Path:
        return path if path.is_absolute() else project_root / path

    result = seal_independent_geometry_run(
        project_root,
        resolve(args.run_root),
        pages=args.pages,
        role_b_seal_path=resolve(args.role_b_seal),
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
