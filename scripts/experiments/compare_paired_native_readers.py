from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.paired_native_evaluation import compare_paired_native_readers


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare sealed Role B rows against a native Role A machine reference"
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--suite-config", type=Path, required=True)
    parser.add_argument("--role-a-seal", type=Path, required=True)
    parser.add_argument("--role-b-seal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--parser-config",
        type=Path,
        default=Path("config/tables/vlm-table-parser-v2.yaml"),
    )
    args = parser.parse_args()
    result = compare_paired_native_readers(
        args.project_root,
        suite_config=args.suite_config,
        role_a_seal=args.role_a_seal,
        role_b_seal=args.role_b_seal,
        output=args.output,
        parser_config=args.parser_config,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "experiment_id": result["experiment_id"],
                "main_error_class": result["error_analysis"]["main_error_class"],
                "metrics": result["metrics"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
