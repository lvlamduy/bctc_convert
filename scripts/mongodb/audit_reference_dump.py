from __future__ import annotations

import argparse
from pathlib import Path

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.ingestion.mongodb_dump import audit_financial_reference_dump


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--mongo-uri", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/registered/mongodb_dump_registry.json"),
    )
    parser.add_argument("--proposed-id", type=int, default=1944)
    parser.add_argument(
        "--proposed-name",
        default="Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
    )
    arguments = parser.parse_args()
    project_root = Path(__file__).resolve().parents[2]
    result = audit_financial_reference_dump(
        arguments.archive,
        project_root,
        mongo_uri=arguments.mongo_uri,
        proposed_id=arguments.proposed_id,
        proposed_name=arguments.proposed_name,
    )
    output = arguments.output
    if not output.is_absolute():
        output = project_root / output
    atomic_write_json(output, result)
    print(f"MONGODB_DUMP_REGISTRY={output.resolve()}")
    print(
        "ID_COLLISION_SAFE="
        f"{result['collision_audit']['append_safe_from_id_collision_perspective']}"
    )


if __name__ == "__main__":
    main()
