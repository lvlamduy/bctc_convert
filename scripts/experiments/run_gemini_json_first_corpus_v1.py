#!/usr/bin/env python3
"""Build an immutable provider-partitioned Gemini JSON-first corpus plan."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.family_first_filing_inventory_v1 import (  # noqa: E402
    read_family_first_filing_inventory_v1,
)
from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import (  # noqa: E402
    build_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1  # noqa: E402


class RunGeminiJsonFirstCorpusV1Error(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dpi", type=int, choices=(200, 300), default=300)
    parser.add_argument("--google-batch-chunk-pages", type=int, default=30)
    parser.add_argument("--openrouter-page-fraction", default="0.20")
    parser.add_argument("--openrouter-workers", type=int, default=5)
    return parser


def _inventory(project_root: Path) -> list[dict[str, Any]]:
    root = project_root.resolve()
    if not root.is_dir():
        raise RunGeminiJsonFirstCorpusV1Error("project root is not one directory")
    inventory = read_family_first_filing_inventory_v1(root)
    documents = []
    for filing in inventory["filings"]:
        source_ref = filing["content_ref"]
        path = root / source_ref["path"]
        if path.is_symlink() or not path.is_file():
            raise RunGeminiJsonFirstCorpusV1Error("corpus PDF must be one regular file")
        stat = path.stat()
        if stat.st_nlink != 1 or stat.st_size != source_ref["size_bytes"] or stat.st_size <= 0:
            raise RunGeminiJsonFirstCorpusV1Error(
                "corpus PDF size or filesystem-link authority drifted"
            )
        with fitz.open(path) as document:
            page_count = document.page_count
        if page_count <= 0:
            raise RunGeminiJsonFirstCorpusV1Error("corpus PDF has no pages")
        documents.append(
            {
                "page_count": page_count,
                "relative_path": source_ref["path"],
                "source_sha256": source_ref["sha256"],
                "source_size_bytes": source_ref["size_bytes"],
            }
        )
    if len(documents) != inventory["metrics"]["selected_filing_count"]:
        raise RunGeminiJsonFirstCorpusV1Error("selected filing denominator drifted")
    return documents


def main() -> int:
    args = _parser().parse_args()
    if args.output.exists():
        raise RunGeminiJsonFirstCorpusV1Error("refusing to overwrite corpus plan")
    plan = build_gemini_json_first_corpus_plan_v1(
        _inventory(args.project_root),
        dpi=args.dpi,
        google_batch_chunk_pages=args.google_batch_chunk_pages,
        openrouter_page_fraction=args.openrouter_page_fraction,
        openrouter_workers=args.openrouter_workers,
    )
    payload = canonical_json_bytes_v1(plan) + b"\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        args.output.unlink(missing_ok=True)
        raise
    print(
        json.dumps(
            {
                "corpus_plan_id": plan["corpus_plan_id"],
                "output": str(args.output),
                **plan["summary"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
