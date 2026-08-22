#!/usr/bin/env python3
"""Build or replay one family from the authenticated per-document evidence store."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import (  # noqa: E402
    family_first_accounting_evidence_sweep_v1 as evidence_v1,
)
from bctc_ai.evaluation import (  # noqa: E402
    family_first_accounting_schema_mapping_v1 as mapping_v1,
)
from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1  # noqa: E402
from bctc_ai.source_structure.contracts_v1 import same_typed_json_v1  # noqa: E402
from scripts.experiments import (  # noqa: E402
    run_family_first_accounting_evidence_sweep_v1 as evidence_cli,
)
from scripts.experiments import run_family_first_accounting_pipeline_v1 as pipeline_v1  # noqa: E402
from scripts.experiments import (  # noqa: E402
    run_family_first_accounting_schema_mapping_v1 as mapping_cli,
)
from scripts.experiments import run_family_first_topology_sweep_v1 as topology_cli  # noqa: E402


def run_family_first_accounting_document_store_pipeline_v1(
    project_root: Path,
    *,
    family_spec_path: Path,
    evaluation_spec_path: Path,
    schema_binding_spec_path: Path,
    command: str,
) -> dict[str, object]:
    if command not in {"build", "verify"}:
        raise ValueError("document-store family pipeline command must be build or verify")
    root = project_root.resolve()
    family_spec = topology_cli._family_spec(root, family_spec_path)
    evaluation_spec = topology_cli._family_spec(root, evaluation_spec_path)
    schema_binding_spec = topology_cli._family_spec(root, schema_binding_spec_path)
    evidence_relative = evidence_cli._artifact_path(family_spec, evaluation_spec)
    mapping_relative = mapping_cli._artifact_path(family_spec, evaluation_spec, schema_binding_spec)
    persisted_evidence = persisted_mapping = None
    if command == "verify":
        persisted_evidence = pipeline_v1._read_canonical_object(
            root / evidence_relative, "document-store family evidence sweep"
        )
        persisted_mapping = pipeline_v1._read_canonical_object(
            root / mapping_relative, "document-store family schema mapping"
        )
    elif (root / evidence_relative).exists() or (root / mapping_relative).exists():
        raise ValueError("document-store family artifact destination already exists")
    capability = store_v1.authenticate_family_first_document_evidence_store_v1(root)
    evidence = evidence_v1.build_authenticated_family_first_accounting_evidence_sweep_from_document_store_v1(
        capability, family_spec, evaluation_spec
    )
    mapping = mapping_v1._build_from_same_turn_authenticated_evidence_sweep_v1(
        root, evidence, family_spec, schema_binding_spec
    )
    if command == "build":
        pipeline_v1._publish_pair(
            root / evidence_relative,
            evidence,
            root / mapping_relative,
            mapping,
        )
    elif not same_typed_json_v1(persisted_evidence, evidence) or not same_typed_json_v1(
        persisted_mapping, mapping
    ):
        raise ValueError("document-store family evidence/mapping replay differs")
    return {
        "evidence_metrics": evidence["metrics"],
        "evidence_path": evidence_relative.as_posix(),
        "family_id": evidence["family_id"],
        "mapping_id": mapping["mapping_id"],
        "mapping_metrics": mapping["metrics"],
        "mapping_path": mapping_relative.as_posix(),
        "per_document_packet_root_recomputation_count": evidence["metrics"]["document_count"],
        "upstream_ocr_replay_count": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-spec", required=True, type=Path)
    parser.add_argument("--evaluation-spec", required=True, type=Path)
    parser.add_argument("--schema-binding-spec", required=True, type=Path)
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    result = run_family_first_accounting_document_store_pipeline_v1(
        PROJECT_ROOT,
        family_spec_path=args.family_spec,
        evaluation_spec_path=args.evaluation_spec,
        schema_binding_spec_path=args.schema_binding_spec,
        command=args.command,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
