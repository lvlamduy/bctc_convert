from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.family_first_ppocrv6_numeric_index_v2 import (
    authenticate_family_first_ppocrv6_numeric_index_v2,
    finalize_authenticated_family_first_ppocrv6_numeric_index_v2,
    project_authenticated_family_first_ppocrv6_numeric_index_v2,
)
from bctc_ai.evaluation.family_first_semantic_label_archive_v1 import (
    authenticate_family_first_semantic_label_archive_v1,
)
from bctc_ai.ocr.family_first_ppocrv6_numeric_sharded_runner_v2 import (
    aggregate_authenticated_family_first_ppocrv6_numeric_v2,
    project_authenticated_family_first_ppocrv6_numeric_shards_v2,
    run_authenticated_family_first_ppocrv6_numeric_missing_shards_v2,
    run_authenticated_family_first_ppocrv6_numeric_shard_v2,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run crash-bounded reference-blind PP-OCRv6 numeric shards"
    )
    parser.add_argument("--model-cache", type=Path, required=True)
    parser.add_argument("--shard-ordinal", type=int)
    parser.add_argument("--maximum-new-shards", type=int)
    parser.add_argument(
        "command",
        choices=("run-shard", "run-missing", "status", "aggregate", "finalize", "verify"),
    )
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    archive = authenticate_family_first_semantic_label_archive_v1(
        root, model_cache=arguments.model_cache
    )
    if arguments.command == "run-shard":
        if arguments.shard_ordinal is None:
            parser.error("--shard-ordinal is required for run-shard")
        result = run_authenticated_family_first_ppocrv6_numeric_shard_v2(
            root,
            archive,
            model_cache=arguments.model_cache,
            shard_ordinal=arguments.shard_ordinal,
        )
    elif arguments.command == "run-missing":
        result = run_authenticated_family_first_ppocrv6_numeric_missing_shards_v2(
            root,
            archive,
            model_cache=arguments.model_cache,
            maximum_new_shards=arguments.maximum_new_shards,
        )
    elif arguments.command == "status":
        result = project_authenticated_family_first_ppocrv6_numeric_shards_v2(
            root, archive, model_cache=arguments.model_cache
        )
    elif arguments.command == "aggregate":
        result = aggregate_authenticated_family_first_ppocrv6_numeric_v2(
            root, archive, model_cache=arguments.model_cache
        )
    elif arguments.command == "finalize":
        result = finalize_authenticated_family_first_ppocrv6_numeric_index_v2(
            root, archive, model_cache=arguments.model_cache
        )
    else:
        capability = authenticate_family_first_ppocrv6_numeric_index_v2(
            root, archive, model_cache=arguments.model_cache
        )
        result = project_authenticated_family_first_ppocrv6_numeric_index_v2(capability)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
