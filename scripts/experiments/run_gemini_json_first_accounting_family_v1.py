#!/usr/bin/env python3
"""Run one declarative accounting family over the frozen Gemini JSON corpus."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    evaluate_gemini_json_flat_family_table_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1  # noqa: E402
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    load_page_json_versions_v1,
    query_selected_family_anchor_hits_v1,
    query_selected_family_anchor_regions_v1,
)


class RunGeminiJsonFirstAccountingFamilyV1Error(RuntimeError):
    """The frozen corpus, family specs, or output frontier drifted."""


def _error(message: str) -> RunGeminiJsonFirstAccountingFamilyV1Error:
    return RunGeminiJsonFirstAccountingFamilyV1Error(message)


def _json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _error(f"JSON input is absent or not regular: {path}")
    try:
        value = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"JSON input is invalid: {path}") from exc
    if type(value) is not dict:
        raise _error("JSON input is not one object")
    return value


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _content_ref(root: Path, reference: dict[str, Any]) -> Path:
    if type(reference) is not dict or set(reference) != {"path", "sha256", "size_bytes"}:
        raise _error("frozen corpus content reference fields drifted")
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise _error("frozen corpus content reference escapes its root")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != reference["size_bytes"]
        or _sha256(path) != reference["sha256"]
    ):
        raise _error("frozen corpus content reference does not authenticate")
    return path


def _write_once(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_json_bytes_v1(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error("Gemini JSON family output already exists with different bytes")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    artifact_root = args.artifact_root.resolve()
    database = _content_ref(artifact_root, index["database_ref"])
    topology = _json(args.topology_spec)
    evaluation = _json(args.evaluation_spec)
    schema = _json(args.schema_binding_spec)
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)

    selected_ids: list[str] = []
    for document in index["documents"]:
        manifest = _json(_content_ref(artifact_root, document["document_manifest_ref"]))
        if (
            manifest.get("document_manifest_id") != document["document_manifest_id"]
            or manifest.get("page_count") != document["page_count"]
            or type(manifest.get("pages")) is not list
        ):
            raise _error("selected document manifest identity or page axis drifted")
        page_ids = [page.get("page_json_version_id") for page in manifest["pages"]]
        if len(page_ids) != document["page_count"]:
            raise _error("selected document manifest JSON version axis is incomplete")
        selected_ids.extend(page_ids)
    if len(selected_ids) != index["summary"]["page_count"] or len(set(selected_ids)) != len(
        selected_ids
    ):
        raise _error("selected corpus JSON version frontier is incomplete or duplicate")

    regions_by_key: dict[tuple[str, int, str, str], dict[str, Any]] = {}
    for anchor_groups in compiled["anchor_alias_groups"]:
        regions = query_selected_family_anchor_regions_v1(
            database,
            selected_page_json_version_ids=selected_ids,
            anchor_aliases=anchor_groups,
            adjacent_page_radius=1,
        )
        for region in regions:
            key = (
                region["source_logical_name"],
                region["physical_page"],
                region["section_id"],
                region["table_id"],
            )
            regions_by_key[key] = region
    required_roles = {
        role
        for combination in compiled["topology"]["required_role_combinations"]
        for role in combination
    }
    near_aliases = sorted(
        {alias for role in required_roles for alias in compiled["aliases_by_role"][role]}
    )
    near_hits = query_selected_family_anchor_hits_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        anchor_aliases=near_aliases,
    )
    near_paths = {hit["source_logical_name"] for hit in near_hits}

    candidate_version_ids = sorted(
        {region["page_json_version_id"] for region in regions_by_key.values()}
    )
    loaded = load_page_json_versions_v1(
        database,
        page_json_version_ids=candidate_version_ids,
    )
    page_by_version = {record["page_json_version_id"]: record for record in loaded}
    candidates_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key in sorted(regions_by_key):
        region = regions_by_key[key]
        page = page_by_version[region["page_json_version_id"]]
        candidate = evaluate_gemini_json_flat_family_table_v1(
            page_json=page["page_json"],
            page_json_version_id=region["page_json_version_id"],
            physical_page=region["physical_page"],
            section_id=region["section_id"],
            table_id=region["table_id"],
            compiled_specs=compiled,
        )
        candidates_by_path[region["source_logical_name"]].append(candidate)

    trials = []
    for document in index["documents"]:
        path = document["relative_path"]
        candidates = candidates_by_path.get(path, [])
        ready = [candidate for candidate in candidates if candidate["status"] == READY]
        unresolved_candidates = [
            candidate for candidate in candidates if candidate["status"] == UNRESOLVED
        ]
        reasons = []
        selected_candidate_id = None
        mappings = []
        if len(ready) == 1 and not unresolved_candidates:
            status = READY
            selected_candidate_id = ready[0]["candidate_id"]
            mappings = ready[0]["mappings"]
        elif not candidates and path not in near_paths:
            status = NOT_OBSERVED
        else:
            status = UNRESOLVED
            if len(ready) > 1:
                reasons.append("MULTIPLE_EXACT_GEMINI_JSON_FAMILY_REGIONS")
            if not candidates and path in near_paths:
                reasons.append("PARTIAL_REQUIRED_ANCHOR_FRONTIER_ONLY")
            reasons.extend(
                reason for candidate in unresolved_candidates for reason in candidate["reasons"]
            )
        trials.append(
            {
                "candidate_count": len(candidates),
                "candidates": candidates,
                "document_ordinal": document["source_ordinal"],
                "mappings": mappings,
                "reasons": sorted(set(reasons)),
                "selected_candidate_id": selected_candidate_id,
                "source_logical_name": path,
                "source_sha256": document["source_sha256"],
                "status": status,
            }
        )
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
    )
    _write_once(args.output, sweep)
    return {
        "disposition": "SUCCEEDED",
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "sweep_id": sweep["sweep_id"],
    }


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
