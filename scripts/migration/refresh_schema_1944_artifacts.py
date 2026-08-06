from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.questions.bootstrap import bootstrap_questions, write_questions
from bctc_ai.reference.historical import verify_historical_weak_reference
from bctc_ai.reporting.bootstrap import _write_schema_artifacts, _write_schema_proposal


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    _write_schema_artifacts(project_root)
    historical = verify_historical_weak_reference(project_root)
    _write_schema_proposal(project_root, historical)
    write_questions(project_root, bootstrap_questions())

    schema_registry_path = project_root / "data/registered/schema_registry.json"
    schema_registry = json.loads(schema_registry_path.read_text(encoding="utf-8"))
    bootstrap_path = project_root / "BOOTSTRAP_MANIFEST.json"
    bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
    bootstrap["schemas"] = {
        "workbooks": schema_registry["workbooks"],
        "counts": schema_registry["counts"],
        "total_items": schema_registry["total_items"],
        "graph": "reference/schemas/schema_graph.jsonl",
        "graph_hash": schema_registry["graph_sha256"],
        "contains_tm_1944": schema_registry["contains_tm_1944"],
        "lctt_semantics": schema_registry["lctt_semantics"],
        "hierarchy_reference": schema_registry["hierarchy_reference"],
        "coverage_contract": schema_registry["coverage_contract"],
    }
    mongodb = bootstrap.get("mongodb")
    if isinstance(mongodb, dict):
        mongodb["historical_weak_reference"] = historical
    bootstrap["schema_refresh"] = {
        "captured_at": datetime.now(UTC).isoformat(),
        "reason": "Q-BOOT-004_APPEND_ONLY_TM_1944",
        "schema_registry": "data/registered/schema_registry.json",
        "schema_registry_sha256": sha256_file(schema_registry_path),
        "schema_append_audit": "data/registered/schema_append_1944.json",
        "schema_append_audit_sha256": sha256_file(
            project_root / "data/registered/schema_append_1944.json"
        ),
    }
    atomic_write_json(bootstrap_path, bootstrap)
    print("SCHEMA_1944_ARTIFACT_REFRESH=PASS")
    print(f"SCHEMA_COUNT={schema_registry['total_items']}")
    print(f"TM_COUNT={schema_registry['counts']['TM']}")
    print(f"SCHEMA_REGISTRY_SHA256={sha256_file(schema_registry_path)}")


if __name__ == "__main__":
    main()
