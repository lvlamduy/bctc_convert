#!/usr/bin/env python3
"""Build, register, or authenticate the family-first document evidence store."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1  # noqa: E402
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


class FamilyFirstDocumentEvidenceStoreCliV1Error(RuntimeError):
    """The migration inputs, candidate manifest, or tracked registry drifted."""


def _error(message: str) -> FamilyFirstDocumentEvidenceStoreCliV1Error:
    return FamilyFirstDocumentEvidenceStoreCliV1Error(message)


def _candidate() -> dict:
    payload = topology_cli._stable_bytes(
        PROJECT_ROOT / store_v1.MANIFEST_PATH, "document evidence candidate manifest"
    )
    try:
        value = json.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("document evidence candidate manifest is not strict JSON") from exc
    if type(value) is not dict or payload != canonical_json_bytes_v1(value) + b"\n":
        raise _error("document evidence candidate manifest is not canonical JSON")
    return store_v1.validate_family_first_document_evidence_manifest_shape_v1(value)


def run(command: str, *, model_cache: Path | None) -> dict:
    if command == "build":
        if model_cache is None:
            raise _error("build requires the exact numeric model cache")
        destination = PROJECT_ROOT / store_v1.MANIFEST_PATH
        if destination.exists():
            raise _error("document evidence candidate manifest already exists")
        archive = authenticate_family_first_semantic_label_archive_v1(
            PROJECT_ROOT, model_cache=model_cache
        )
        semantic = authenticate_family_first_semantic_index_v1(PROJECT_ROOT, archive)
        numeric = authenticate_family_first_ppocrv6_numeric_index_v3(
            PROJECT_ROOT, archive, model_cache=model_cache
        )
        manifest = store_v1.build_authenticated_family_first_document_evidence_manifest_v1(
            PROJECT_ROOT, semantic, numeric
        )
        topology_cli._write_exclusive(destination, canonical_json_bytes_v1(manifest) + b"\n")
    elif command == "register":
        manifest = _candidate()
        destination = PROJECT_ROOT / store_v1.REGISTRY_PATH
        if destination.exists():
            raise _error("tracked document evidence registry already exists")
        topology_cli._write_exclusive(destination, canonical_json_bytes_v1(manifest) + b"\n")
    elif command == "authenticate":
        capability = store_v1.authenticate_family_first_document_evidence_store_v1(PROJECT_ROOT)
        return store_v1.project_authenticated_family_first_document_evidence_store_v1(capability)
    else:
        raise _error("document evidence store command is unsupported")
    return {
        "document_count": manifest["metrics"]["document_count"],
        "line_count": manifest["metrics"]["line_count"],
        "manifest_id": manifest["manifest_id"],
        "page_count": manifest["metrics"]["page_count"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "register", "authenticate"))
    parser.add_argument("--model-cache", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = run(args.command, model_cache=args.model_cache)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
