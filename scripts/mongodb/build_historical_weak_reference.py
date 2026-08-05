from __future__ import annotations

import argparse
import os
from pathlib import Path

from bctc_ai.reference.historical import build_historical_weak_reference


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a non-authoritative DuckDB index from allowlisted Mongo bank data"
    )
    parser.add_argument(
        "--mongo-uri-env",
        default="BCTC_HISTORY_MONGO_URI",
        help="environment variable containing the MongoDB URI; the URI is never persisted",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/local/historical_weak_reference.duckdb"),
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("data/registered/historical_weak_reference_registry.json"),
    )
    parser.add_argument("--replace", action="store_true")
    arguments = parser.parse_args()
    mongo_uri = os.environ.get(arguments.mongo_uri_env)
    if not mongo_uri:
        parser.error(f"environment variable {arguments.mongo_uri_env!r} is not set")
    project_root = Path(__file__).resolve().parents[2]
    result = build_historical_weak_reference(
        project_root,
        mongo_uri=mongo_uri,
        output_path=arguments.output,
        registry_path=arguments.registry,
        replace=arguments.replace,
    )
    print(f"HISTORICAL_REFERENCE_STATUS={result['status']}")
    print(f"HISTORICAL_REFERENCE_DATABASE={result['database']['path']}")
    print(f"HISTORICAL_REFERENCE_ROWS={result['cells']['count']}")
    print(
        "HISTORICAL_1944_COLLISION_SAFE="
        f"{result['schema']['append_safe_from_historical_key_collision_perspective']}"
    )


if __name__ == "__main__":
    main()
