#!/usr/bin/env python3
"""Build the provider-pinned Gemini plan for the 27-bank expansion."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_first_vertex_flex_expansion_v1 import (  # noqa: E402
    build_gemini_json_first_vertex_flex_expansion_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1  # noqa: E402


class BuildGeminiJsonFirst27BankVertexFlexPlanV1Error(RuntimeError):
    pass


def _write_once(path: Path, payload: bytes) -> None:
    if path.exists():
        raise BuildGeminiJsonFirst27BankVertexFlexPlanV1Error(
            f"refusing to overwrite output: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--already-processed-corpus-manifest-index", type=Path, required=True)
    parser.add_argument("--vietnamese-page-scope", type=Path, required=True)
    parser.add_argument("--bundle-output", type=Path, required=True)
    parser.add_argument("--corpus-plan-output", type=Path, required=True)
    parser.add_argument("--dpi", type=int, choices=(200, 300), default=300)
    parser.add_argument("--workers", type=int, default=20)
    args = parser.parse_args()

    universe = json.loads(args.universe.read_bytes())
    already_processed_corpus_manifest_index = json.loads(
        args.already_processed_corpus_manifest_index.read_bytes()
    )
    vietnamese_page_scope = json.loads(args.vietnamese_page_scope.read_bytes())
    bundle = build_gemini_json_first_vertex_flex_expansion_v1(
        universe,
        already_processed_corpus_manifest_index=already_processed_corpus_manifest_index,
        vietnamese_page_scope=vietnamese_page_scope,
        dpi=args.dpi,
        workers=args.workers,
    )
    _write_once(args.bundle_output, canonical_json_bytes_v1(bundle))
    _write_once(
        args.corpus_plan_output,
        canonical_json_bytes_v1(bundle["corpus_plan"]),
    )
    print(
        json.dumps(
            {
                "corpus_plan_id": bundle["corpus_plan"]["corpus_plan_id"],
                "document_count": bundle["corpus_plan"]["summary"]["document_count"],
                "expansion_plan_id": bundle["expansion_plan_id"],
                "page_count": bundle["corpus_plan"]["summary"]["page_count"],
                "provider": bundle["execution_contract"]["provider"],
                "service_tier": bundle["execution_contract"]["service_tier"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
