#!/usr/bin/env python3
"""Build the protected Flex-first OpenRouter plan for all 27 banks in 2024."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_first_vertex_flex_expansion_2024_v1 import (  # noqa: E402
    build_gemini_json_first_vertex_flex_expansion_2024_v1,
    validate_gemini_json_first_vertex_flex_expansion_2024_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1  # noqa: E402


class BuildGeminiJsonFirst27Bank2024VertexFlexPlanV1Error(RuntimeError):
    pass


def _json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise BuildGeminiJsonFirst27Bank2024VertexFlexPlanV1Error(
            f"JSON authority is absent or not regular: {path}"
        )
    value = json.loads(path.read_bytes())
    if type(value) is not dict:
        raise BuildGeminiJsonFirst27Bank2024VertexFlexPlanV1Error(
            f"JSON authority is not one object: {path}"
        )
    return value


def _write_once(path: Path, payload: bytes) -> None:
    if path.exists():
        raise BuildGeminiJsonFirst27Bank2024VertexFlexPlanV1Error(
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
    parser.add_argument("--protected-2025-current-expansion", type=Path, required=True)
    parser.add_argument("--vietnamese-page-scope", type=Path, required=True)
    parser.add_argument("--bundle-output", type=Path, required=True)
    parser.add_argument("--corpus-plan-output", type=Path, required=True)
    parser.add_argument("--dpi", type=int, choices=(200, 300), default=300)
    parser.add_argument("--workers", type=int, choices=range(1, 31), default=20)
    args = parser.parse_args()

    universe = _json(args.universe)
    protected = _json(args.protected_2025_current_expansion)
    scope = _json(args.vietnamese_page_scope)
    bundle = build_gemini_json_first_vertex_flex_expansion_2024_v1(
        universe,
        protected_2025_current_expansion=protected,
        vietnamese_page_scope=scope,
        dpi=args.dpi,
        workers=args.workers,
    )
    validate_gemini_json_first_vertex_flex_expansion_2024_v1(
        bundle,
        authenticated_universe=universe,
        protected_2025_current_expansion=protected,
    )
    _write_once(args.bundle_output, canonical_json_bytes_v1(bundle))
    _write_once(args.corpus_plan_output, canonical_json_bytes_v1(bundle["corpus_plan"]))
    print(
        json.dumps(
            {
                "corpus_plan_id": bundle["corpus_plan"]["corpus_plan_id"],
                "document_count": bundle["corpus_plan"]["summary"]["document_count"],
                "expansion_plan_id": bundle["expansion_plan_id"],
                "page_count": bundle["corpus_plan"]["summary"]["page_count"],
                "fallback_policy": bundle["execution_contract"]["fallback_policy"],
                "fallback_provider": bundle["execution_contract"]["fallback_provider"],
                "protected_document_count": bundle["protected_2025_current_binding"][
                    "document_count"
                ],
                "protected_page_count": bundle["protected_2025_current_binding"]["page_count"],
                "provider": bundle["execution_contract"]["provider"],
                "service_tier": bundle["execution_contract"]["service_tier"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
