from __future__ import annotations

from pathlib import Path

from bctc_ai.core.hashing import sha256_file
from bctc_ai.reporting.bootstrap import _write_schema_artifacts


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    workbooks, count, graph_hash, _ = _write_schema_artifacts(project_root)
    counts = {str(record["statement_type"]): int(record["item_count"]) for record in workbooks}
    print("BUSINESS_SCHEMA_ARTIFACT_REFRESH=PASS")
    print(f"SCHEMA_COUNT={count}")
    print(f"SCHEMA_COUNTS={counts}")
    print(f"SCHEMA_GRAPH_SHA256={graph_hash}")
    print(
        "SCHEMA_REGISTRY_SHA256="
        f"{sha256_file(project_root / 'data/registered/schema_registry.json')}"
    )
    print(
        "SCHEMA_COVERAGE_REGISTRY_SHA256="
        f"{sha256_file(project_root / 'data/registered/schema_coverage_registry.json')}"
    )


if __name__ == "__main__":
    main()
