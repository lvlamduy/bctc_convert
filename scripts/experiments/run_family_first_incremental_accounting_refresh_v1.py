#!/usr/bin/env python3
# ruff: noqa: E402
"""Refresh affected family trials from authenticated per-document evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import (
    family_first_accounting_evidence_sweep_v1 as evidence_v1,
)  # noqa: E402
from bctc_ai.evaluation import family_first_accounting_schema_mapping_v1 as mapping_v1  # noqa: E402
from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1  # noqa: E402
from bctc_ai.evaluation.family_first_numeric_cell_evidence_v1 import (  # noqa: E402
    parse_visible_financial_numeric_token_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import run_family_first_topology_sweep_v1 as topology_cli  # noqa: E402

BASE_EVIDENCE_ROOT = Path("output/calibration/family-first-accounting-evidence-sweeps-v1")
OUTPUT_ROOT = Path("output/calibration/family-first-accounting-incremental-refresh-v1")
FORMAT_VERSION = "FAMILY_FIRST_INCREMENTAL_ACCOUNTING_REFRESH_RECEIPT_V1"


class FamilyFirstIncrementalAccountingRefreshV1Error(RuntimeError):
    """The baseline, authenticated packet scope, or bounded rebuild drifted."""


def _error(message: str) -> FamilyFirstIncrementalAccountingRefreshV1Error:
    return FamilyFirstIncrementalAccountingRefreshV1Error(message)


def _object(root: Path, relative: Path, label: str) -> tuple[dict[str, Any], bytes]:
    payload = topology_cli._stable_bytes(root / relative, label)
    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"), object_pairs_hook=topology_cli._duplicates
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict JSON") from exc
    if type(value) is not dict or payload != canonical_json_bytes_v1(value) + b"\n":
        raise _error(f"{label} is not canonical JSON")
    return value, payload


def _ref(relative: Path, payload: bytes) -> dict[str, Any]:
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _family_stem(family_id: str) -> str:
    if type(family_id) is not str or topology_cli._FAMILY_ID.fullmatch(family_id) is None:
        raise _error("incremental family identifier is unsafe")
    return family_id.lower().replace("_", "-")


def _page_offsets(connection: Any, document_ordinal: int) -> tuple[dict[int, int], dict[int, int]]:
    offsets: dict[int, int] = {}
    counts: dict[int, int] = {}
    offset = 0
    rows = connection.execute(
        "SELECT physical_page, line_count FROM pages WHERE document_ordinal = ? "
        "ORDER BY physical_page",
        (document_ordinal,),
    ).fetchall()
    for row in rows:
        offsets[row["physical_page"]] = offset
        counts[row["physical_page"]] = row["line_count"]
        offset += row["line_count"]
    return offsets, counts


def _selected_pages(connection: Any, trial: dict[str, Any]) -> tuple[int, ...]:
    offsets, counts = _page_offsets(connection, trial["document_ordinal"])
    selected = set()
    for region in trial["topology_scan"]["regions"]:
        start = region["cluster_start_document_line_ordinal"]
        stop = region["cluster_end_document_line_ordinal_exclusive"]
        for page, offset in offsets.items():
            if offset < stop and offset + counts[page] > start:
                selected.add(page)
    if not selected:
        raise _error("incremental trial selected no authenticated page")
    return tuple(sorted(selected))


def _mixed_candidate_documents(
    connection: Any,
    trials: list[dict[str, Any]],
) -> tuple[int, ...]:
    regions = {
        trial["document_ordinal"]: tuple(
            (
                region["cluster_start_document_line_ordinal"],
                region["cluster_end_document_line_ordinal_exclusive"],
            )
            for region in trial["topology_scan"]["regions"]
        )
        for trial in trials
        if trial["topology_scan"]["regions"]
    }
    offsets_by_document = {ordinal: _page_offsets(connection, ordinal)[0] for ordinal in regions}
    impacted = set()
    rows = connection.execute(
        "SELECT document_ordinal, physical_page, line_ordinal, numeric_text "
        "FROM lines WHERE instr(numeric_text, '.') > 0 AND instr(numeric_text, ',') > 0 "
        "ORDER BY document_ordinal, physical_page, line_ordinal"
    ).fetchall()
    for row in rows:
        ordinal = row["document_ordinal"]
        if ordinal not in regions:
            continue
        parsed = parse_visible_financial_numeric_token_v1(row["numeric_text"])
        if parsed["classification"] != "MIXED_GROUPED_INTEGER_CANDIDATE":
            continue
        document_line = offsets_by_document[ordinal][row["physical_page"]] + row["line_ordinal"]
        if any(start <= document_line < stop for start, stop in regions[ordinal]):
            impacted.add(ordinal)
    return tuple(sorted(impacted))


def run_family_first_incremental_accounting_refresh_v1(
    project_root: Path,
    *,
    family_spec_path: Path,
    evaluation_spec_path: Path,
    schema_binding_spec_path: Path,
    document_ordinals: tuple[int, ...],
) -> dict[str, Any]:
    """Rebuild exactly the mixed-separator-affected trials for one family."""

    started = time.perf_counter()
    if (
        type(document_ordinals) is not tuple
        or not document_ordinals
        or any(type(ordinal) is not int or ordinal <= 0 for ordinal in document_ordinals)
        or len(document_ordinals) != len(set(document_ordinals))
    ):
        raise _error("incremental document ordinal axis drifted")
    root = project_root.resolve()
    family_spec = topology_cli._family_spec(root, family_spec_path)
    evaluation_spec = topology_cli._family_spec(root, evaluation_spec_path)
    schema_binding_spec = topology_cli._family_spec(root, schema_binding_spec_path)
    family_id = family_spec.get("family_id")
    if (
        evaluation_spec.get("family_id") != family_id
        or schema_binding_spec.get("family_id") != family_id
    ):
        raise _error("incremental family specifications identify different families")
    stem = _family_stem(family_id)
    baseline_relative = BASE_EVIDENCE_ROOT / f"{stem}.json"
    baseline, baseline_payload = _object(root, baseline_relative, "baseline family evidence sweep")
    baseline = evidence_v1._validate(baseline)
    if (
        baseline["family_id"] != family_id
        or not same_typed_json_v1(baseline["family_spec"]["value"], family_spec)
        or not same_typed_json_v1(baseline["evaluation_spec"]["value"], evaluation_spec)
    ):
        raise _error("baseline family evidence belongs to another specification revision")
    capability = store_v1.authenticate_family_first_document_evidence_store_v1(root)
    store_projection = store_v1.project_authenticated_family_first_document_evidence_store_v1(
        capability
    )
    if not same_typed_json_v1(
        baseline["input_indices"],
        {
            "numeric_receipt_id": store_projection["input_indices"]["numeric_receipt_id"],
            "semantic_index_id": store_projection["input_indices"]["semantic_index_id"],
        },
    ):
        raise _error("baseline family evidence belongs to another document store snapshot")
    state = store_v1._live_store(capability)
    with store_v1.cache_v1._connect(state.database_path) as connection:
        impacted = _mixed_candidate_documents(connection, baseline["trials"])
        if impacted != tuple(sorted(document_ordinals)):
            raise _error("requested incremental documents do not equal the complete affected scope")
        selections = {
            ordinal: _selected_pages(connection, baseline["trials"][ordinal - 1])
            for ordinal in document_ordinals
        }
    trials = canonical_clone_v1(baseline["trials"])
    snapshots = []
    for ordinal in document_ordinals:
        snapshot = store_v1.read_authenticated_family_first_document_evidence_snapshot_v1(
            capability,
            document_ordinal=ordinal,
            selected_pages=selections[ordinal],
        )
        trials[ordinal - 1] = (
            evidence_v1.rebuild_family_first_accounting_trial_from_document_snapshot_v1(
                trials[ordinal - 1], snapshot, family_spec, evaluation_spec
            )
        )
        snapshots.append(
            {
                "document_ordinal": ordinal,
                "packet_id": snapshot["document_packet"]["packet_id"],
                "selected_pages": list(selections[ordinal]),
                "snapshot_id": snapshot["snapshot_id"],
            }
        )
    material = canonical_clone_v1(baseline)
    material.pop("sweep_id")
    material["metrics"] = evidence_v1._metrics(trials)
    material["trials"] = trials
    evidence = evidence_v1._validate(
        {**material, "sweep_id": "ffaesv1:sweep:" + canonical_json_sha256_v1(material)}
    )
    mapping = mapping_v1._build_from_same_turn_authenticated_evidence_sweep_v1(
        root, evidence, family_spec, schema_binding_spec
    )
    evidence_relative = OUTPUT_ROOT / f"{stem}-evidence.json"
    mapping_relative = OUTPUT_ROOT / f"{stem}-mapping.json"
    receipt_relative = OUTPUT_ROOT / f"{stem}-receipt.json"
    evidence_payload = canonical_json_bytes_v1(evidence) + b"\n"
    mapping_payload = canonical_json_bytes_v1(mapping) + b"\n"
    receipt_material = {
        "affected_document_ordinals": list(impacted),
        "authority": {
            "baseline_unchanged_trials_reused": True,
            "full_corpus_ocr_or_evidence_replay_performed": False,
            "mapping_authority_inherited_from_exact_family_gates": True,
            "mixed_candidate_scope_exhaustively_queried_inside_family_regions": True,
            "per_document_packet_roots_recomputed": True,
        },
        "baseline_evidence_ref": _ref(baseline_relative, baseline_payload),
        "document_evidence_manifest_id": store_projection["manifest_id"],
        "evidence_ref": _ref(evidence_relative, evidence_payload),
        "family_id": family_id,
        "format_version": FORMAT_VERSION,
        "mapping_ref": _ref(mapping_relative, mapping_payload),
        "snapshots": snapshots,
    }
    receipt = {
        **receipt_material,
        "refresh_id": "ffiarv1:refresh:" + canonical_json_sha256_v1(receipt_material),
    }
    topology_cli._write_exclusive(root / evidence_relative, evidence_payload)
    topology_cli._write_exclusive(root / mapping_relative, mapping_payload)
    topology_cli._write_exclusive(root / receipt_relative, canonical_json_bytes_v1(receipt) + b"\n")
    return {
        "affected_document_ordinals": list(impacted),
        "elapsed_seconds": time.perf_counter() - started,
        "evidence_metrics": evidence["metrics"],
        "family_id": family_id,
        "mapping_metrics": mapping["metrics"],
        "output_root": OUTPUT_ROOT.as_posix(),
        "refresh_id": receipt["refresh_id"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-spec", required=True, type=Path)
    parser.add_argument("--evaluation-spec", required=True, type=Path)
    parser.add_argument("--schema-binding-spec", required=True, type=Path)
    parser.add_argument("--document-ordinal", required=True, action="append", type=int)
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = run_family_first_incremental_accounting_refresh_v1(
        PROJECT_ROOT,
        family_spec_path=args.family_spec,
        evaluation_spec_path=args.evaluation_spec,
        schema_binding_spec_path=args.schema_binding_spec,
        document_ordinals=tuple(args.document_ordinal),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
