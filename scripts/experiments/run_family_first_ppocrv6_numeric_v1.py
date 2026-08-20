from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.family_first_ppocrv6_numeric_index_v1 import (
    authenticate_family_first_ppocrv6_numeric_index_v1,
    finalize_authenticated_family_first_ppocrv6_numeric_index_v1,
    project_authenticated_family_first_ppocrv6_numeric_index_v1,
)
from bctc_ai.evaluation.family_first_semantic_label_archive_v1 import (
    authenticate_family_first_semantic_label_archive_v1,
)
from bctc_ai.ocr.family_first_ppocrv6_numeric_runner_v1 import (
    run_authenticated_family_first_ppocrv6_numeric_v1,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the fixed reference-blind all-filing PP-OCRv6 numeric cache"
    )
    parser.add_argument("--model-cache", type=Path, required=True)
    parser.add_argument("command", choices=("run", "finalize", "verify"))
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    archive = authenticate_family_first_semantic_label_archive_v1(
        root, model_cache=arguments.model_cache
    )
    if arguments.command == "run":
        result = run_authenticated_family_first_ppocrv6_numeric_v1(
            root, archive, model_cache=arguments.model_cache
        )
    elif arguments.command == "finalize":
        result = finalize_authenticated_family_first_ppocrv6_numeric_index_v1(root, archive)
    else:
        capability = authenticate_family_first_ppocrv6_numeric_index_v1(root, archive)
        result = project_authenticated_family_first_ppocrv6_numeric_index_v1(capability)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
