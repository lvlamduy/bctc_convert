from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.evaluation.holdout_discovery_seal import (  # noqa: E402
    capture_e0022_unresolved_role_b_discovery,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seal unresolved E-0022 Role B discovery")
    parser.add_argument("--model-cache-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0022-role-b-unresolved-discovery.json"),
    )
    args = parser.parse_args()
    payload = capture_e0022_unresolved_role_b_discovery(
        PROJECT_ROOT,
        model_cache_root=args.model_cache_root,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "state": payload["state"],
                "allowed_next_action": payload["allowed_next_action"],
                "mapping_invoked": payload["mapping"]["invoked"],
                "semantic_reader_invoked": payload["semantic_reader"]["invoked"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
