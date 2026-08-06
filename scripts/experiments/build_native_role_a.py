from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.native_reference import build_native_role_a_reference


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a sealed native-geometry Role A machine reference"
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--suite-config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--geometry-config",
        type=Path,
        default=Path("config/tables/geometry-v2.yaml"),
    )
    args = parser.parse_args()
    result = build_native_role_a_reference(
        args.project_root,
        suite_config=args.suite_config,
        output_root=args.output_root,
        geometry_config=args.geometry_config,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
