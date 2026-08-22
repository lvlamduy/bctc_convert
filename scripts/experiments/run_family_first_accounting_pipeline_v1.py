#!/usr/bin/env python3
"""Build or replay one family evidence+schema mapping with one source traversal."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import (  # noqa: E402
    family_first_accounting_evidence_sweep_v1 as evidence_v1,
)
from bctc_ai.evaluation import (  # noqa: E402
    family_first_accounting_schema_mapping_v1 as mapping_v1,
)
from bctc_ai.evaluation.family_first_ppocrv6_numeric_index_v3 import (  # noqa: E402
    authenticate_family_first_ppocrv6_numeric_index_v3,
)
from bctc_ai.evaluation.family_first_semantic_index_v1 import (  # noqa: E402
    authenticate_family_first_semantic_index_v1,
)
from bctc_ai.evaluation.family_first_semantic_label_archive_v1 import (  # noqa: E402
    authenticate_family_first_semantic_label_archive_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    same_typed_json_v1,
)
from scripts.experiments import (  # noqa: E402
    run_family_first_accounting_evidence_sweep_v1 as evidence_cli,
)
from scripts.experiments import (  # noqa: E402
    run_family_first_accounting_schema_mapping_v1 as mapping_cli,
)
from scripts.experiments import run_family_first_topology_sweep_v1 as topology_cli  # noqa: E402


class FamilyFirstAccountingPipelineV1Error(RuntimeError):
    """The shared inputs, paired artifacts, or same-turn lineage drifted."""


def _error(message: str) -> FamilyFirstAccountingPipelineV1Error:
    return FamilyFirstAccountingPipelineV1Error(message)


def _read_canonical_object(path: Path, label: str) -> dict[str, Any]:
    payload = topology_cli._stable_bytes(path, label)
    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=topology_cli._duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict JSON") from exc
    if type(value) is not dict or payload != canonical_json_bytes_v1(value) + b"\n":
        raise _error(f"{label} is not canonical JSON")
    return value


def _remove_exact_owned_file(path: Path, payload: bytes) -> None:
    """Rollback only a file this call exclusively created with exact bytes."""

    try:
        current = topology_cli._stable_bytes(path, "paired family artifact rollback")
    except (OSError, RuntimeError):
        return
    if current == payload:
        path.unlink()


def _publish_pair(
    evidence_path: Path,
    evidence: dict[str, Any],
    mapping_path: Path,
    mapping: dict[str, Any],
) -> None:
    if evidence_path.exists() or mapping_path.exists():
        raise _error("paired family evidence/mapping destination already exists")
    evidence_payload = canonical_json_bytes_v1(evidence) + b"\n"
    mapping_payload = canonical_json_bytes_v1(mapping) + b"\n"
    evidence_written = False
    try:
        topology_cli._write_exclusive(evidence_path, evidence_payload)
        evidence_written = True
        topology_cli._write_exclusive(mapping_path, mapping_payload)
    except Exception:
        if evidence_written:
            _remove_exact_owned_file(evidence_path, evidence_payload)
        raise


def run_family_first_accounting_pipeline_v1(
    project_root: Path,
    *,
    model_cache: Path,
    family_spec_path: Path,
    evaluation_spec_path: Path,
    schema_binding_spec_path: Path,
    command: str,
) -> dict[str, Any]:
    """Build or exact-replay paired artifacts after one authenticated sweep."""

    if command not in {"build", "verify"}:
        raise _error("accounting pipeline command must be build or verify")
    root = project_root.resolve()
    family_spec = topology_cli._family_spec(root, family_spec_path)
    evaluation_spec = topology_cli._family_spec(root, evaluation_spec_path)
    schema_binding_spec = topology_cli._family_spec(root, schema_binding_spec_path)
    evidence_relative = evidence_cli._artifact_path(family_spec, evaluation_spec)
    mapping_relative = mapping_cli._artifact_path(
        family_spec,
        evaluation_spec,
        schema_binding_spec,
    )
    evidence_path = root / evidence_relative
    mapping_path = root / mapping_relative

    persisted_evidence = None
    persisted_mapping = None
    if command == "verify":
        persisted_evidence = _read_canonical_object(
            evidence_path,
            "family accounting evidence sweep artifact",
        )
        persisted_mapping = _read_canonical_object(
            mapping_path,
            "family accounting schema mapping artifact",
        )
    elif evidence_path.exists() or mapping_path.exists():
        raise _error("paired family evidence/mapping destination already exists")

    archive = authenticate_family_first_semantic_label_archive_v1(root, model_cache=model_cache)
    semantic_index = authenticate_family_first_semantic_index_v1(root, archive)
    numeric_index = authenticate_family_first_ppocrv6_numeric_index_v3(
        root,
        archive,
        model_cache=model_cache,
    )
    evidence = evidence_v1.build_authenticated_family_first_accounting_evidence_sweep_v1(
        semantic_index,
        numeric_index,
        family_spec,
        evaluation_spec,
    )
    mapping = mapping_v1._build_from_same_turn_authenticated_evidence_sweep_v1(
        root,
        evidence,
        family_spec,
        schema_binding_spec,
    )
    if mapping["evidence_sweep_id"] != evidence["sweep_id"]:
        raise _error("same-turn family evidence/mapping lineage differs")

    if command == "build":
        _publish_pair(evidence_path, evidence, mapping_path, mapping)
    elif not same_typed_json_v1(persisted_evidence, evidence) or not same_typed_json_v1(
        persisted_mapping,
        mapping,
    ):
        raise _error("paired family evidence/mapping does not replay exactly")

    return {
        "evidence_metrics": evidence["metrics"],
        "evidence_path": evidence_relative.as_posix(),
        "family_id": evidence["family_id"],
        "mapping_id": mapping["mapping_id"],
        "mapping_metrics": mapping["metrics"],
        "mapping_path": mapping_relative.as_posix(),
        "source_traversal_count": 1,
        "sweep_id": evidence["sweep_id"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-cache", required=True, type=Path)
    parser.add_argument("--family-spec", required=True, type=Path)
    parser.add_argument("--evaluation-spec", required=True, type=Path)
    parser.add_argument("--schema-binding-spec", required=True, type=Path)
    parser.add_argument("command", choices=("build", "verify"))
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = run_family_first_accounting_pipeline_v1(
        PROJECT_ROOT,
        model_cache=args.model_cache,
        family_spec_path=args.family_spec,
        evaluation_spec_path=args.evaluation_spec,
        schema_binding_spec_path=args.schema_binding_spec,
        command=args.command,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
