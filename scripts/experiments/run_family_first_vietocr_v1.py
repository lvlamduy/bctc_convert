#!/usr/bin/env python3
"""Seal and run the fixed all-filing reference-blind VietOCR semantic cache."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation.family_first_semantic_index_v1 import (  # noqa: E402
    authenticate_family_first_semantic_index_v1,
    finalize_authenticated_family_first_semantic_index_v1,
    project_authenticated_family_first_semantic_index_v1,
)
from bctc_ai.evaluation.family_first_semantic_label_archive_v1 import (  # noqa: E402
    authenticate_family_first_semantic_label_archive_v1,
    project_authenticated_family_first_semantic_label_archive_v1,
    seal_family_first_semantic_label_archive_v1,
)
from bctc_ai.ocr.family_first_vietocr_runner_v1 import (  # noqa: E402
    run_authenticated_family_first_vietocr_v1,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-cache", required=True, type=Path)
    parser.add_argument(
        "command", choices=("seal", "verify", "run", "finalize-index", "verify-index")
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "seal":
        result = seal_family_first_semantic_label_archive_v1(
            PROJECT_ROOT, model_cache=args.model_cache
        )
    else:
        capability = authenticate_family_first_semantic_label_archive_v1(
            PROJECT_ROOT, model_cache=args.model_cache
        )
        if args.command == "verify":
            result = project_authenticated_family_first_semantic_label_archive_v1(capability)
        elif args.command == "run":
            result = run_authenticated_family_first_vietocr_v1(PROJECT_ROOT, capability)
        elif args.command == "finalize-index":
            result = finalize_authenticated_family_first_semantic_index_v1(PROJECT_ROOT, capability)
        else:
            index_capability = authenticate_family_first_semantic_index_v1(PROJECT_ROOT, capability)
            result = project_authenticated_family_first_semantic_index_v1(index_capability)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
