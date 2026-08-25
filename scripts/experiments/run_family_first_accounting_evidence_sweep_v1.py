#!/usr/bin/env python3
"""Build or replay one generic all-filing accounting evidence sweep."""

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

from bctc_ai.evaluation.family_first_accounting_evidence_sweep_v1 import (  # noqa: E402
    build_authenticated_family_first_accounting_evidence_sweep_v1,
    validate_authenticated_family_first_accounting_evidence_sweep_replay_v1,
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
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1  # noqa: E402
from scripts.experiments import run_family_first_topology_sweep_v1 as topology_cli  # noqa: E402

OUTPUT_ROOT = Path("output/calibration/family-first-accounting-evidence-sweeps-v1")


class FamilyFirstAccountingEvidenceSweepCliV1Error(RuntimeError):
    """The tracked specs, authenticated indices, or fixed artifact drifted."""


def _error(message: str) -> FamilyFirstAccountingEvidenceSweepCliV1Error:
    return FamilyFirstAccountingEvidenceSweepCliV1Error(message)


def _artifact_path(family_spec: dict[str, Any], evaluation_spec: dict[str, Any]) -> Path:
    family_id = family_spec.get("family_id")
    if (
        type(family_id) is not str
        or topology_cli._FAMILY_ID.fullmatch(family_id) is None
        or evaluation_spec.get("family_id") != family_id
    ):
        raise _error("family/evaluation specification identities differ or are unsafe")
    return OUTPUT_ROOT / (family_id.lower().replace("_", "-") + ".json")


def run_family_first_accounting_evidence_sweep_v1(
    project_root: Path,
    *,
    model_cache: Path,
    family_spec_path: Path,
    evaluation_spec_path: Path,
    command: str,
) -> dict[str, Any]:
    """Build or exact-replay one fixed family evidence artifact."""

    if command not in {"build", "verify"}:
        raise _error("accounting evidence sweep command must be build or verify")
    root = project_root.resolve()
    family_spec = topology_cli._family_spec(root, family_spec_path)
    evaluation_spec = topology_cli._family_spec(root, evaluation_spec_path)
    output_relative = _artifact_path(family_spec, evaluation_spec)
    archive = authenticate_family_first_semantic_label_archive_v1(root, model_cache=model_cache)
    semantic_index = authenticate_family_first_semantic_index_v1(root, archive)
    numeric_index = authenticate_family_first_ppocrv6_numeric_index_v3(
        root, archive, model_cache=model_cache
    )
    if command == "build":
        result = build_authenticated_family_first_accounting_evidence_sweep_v1(
            semantic_index,
            numeric_index,
            family_spec,
            evaluation_spec,
        )
        topology_cli._write_exclusive(root / output_relative, canonical_json_bytes_v1(result))
    else:
        payload = topology_cli._stable_bytes(
            root / output_relative, "family accounting evidence sweep artifact"
        )
        try:
            persisted = json.loads(
                payload.decode("utf-8", errors="strict"),
                object_pairs_hook=topology_cli._duplicates,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("family accounting evidence sweep artifact is not strict JSON") from exc
        if type(persisted) is not dict or payload != canonical_json_bytes_v1(persisted):
            raise _error("family accounting evidence sweep artifact is not canonical JSON")
        result = validate_authenticated_family_first_accounting_evidence_sweep_replay_v1(
            persisted,
            semantic_index,
            numeric_index,
            family_spec,
            evaluation_spec,
        )
    return {
        "family_id": result["family_id"],
        "metrics": result["metrics"],
        "output_path": output_relative.as_posix(),
        "sweep_id": result["sweep_id"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-cache", required=True, type=Path)
    parser.add_argument("--family-spec", required=True, type=Path)
    parser.add_argument("--evaluation-spec", required=True, type=Path)
    parser.add_argument("command", choices=("build", "verify"))
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = run_family_first_accounting_evidence_sweep_v1(
        PROJECT_ROOT,
        model_cache=args.model_cache,
        family_spec_path=args.family_spec,
        evaluation_spec_path=args.evaluation_spec,
        command=args.command,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
