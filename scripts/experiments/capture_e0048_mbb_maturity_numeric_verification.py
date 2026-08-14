#!/usr/bin/env python3
"""Capture independent eight-cell numeric evidence for the MBB maturity core.

E-0048 is deliberately narrower than mapping.  It rebuilds the MBB ordered
graph from the sealed E-0046 capture and the tracked E-0047 mechanism result,
copies only the eight authenticated value-line crops into a reference-blind
registry, and fuses a separately selected numeric-reader run solely on exact
digit and sign agreement.  The three maturity rows and the source-only core
subtotal remain schema candidates, never mappings, in this artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import evaluate_e0047_ordered_row_value_lane_assignment as e0047
import ordered_graph_numeric_cell_registry_v1 as registry_v1

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.evaluation import semantic_graph_numeric_proposal_receipt_v1 as numeric_receipt
from bctc_ai.evaluation.numeric_cell_verification import (
    NumericCellVerificationError,
    _verify_numeric_cell_proposals,
)
from bctc_ai.source_structure import semantic_local_accounting_graph_v2 as graph_v2
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.vietnamese_semantic_surface_v1 import (
    compile_vietnamese_family_alias_index_v1,
)

__all__ = [
    "E0048MBBMaturityNumericVerificationError",
    "build_e0048_mbb_maturity_numeric_selection_v1",
    "build_e0048_mbb_maturity_numeric_verification_v1",
    "freeze_e0048_mbb_maturity_numeric_registry_v1",
    "validate_e0048_mbb_maturity_numeric_verification_v1",
]


FORMAT_VERSION = "E0048_MBB_MATURITY_INDEPENDENT_NUMERIC_VERIFICATION_V1"
EXPERIMENT_ID = "E-0048"
STATE = "INDEPENDENT_NUMERIC_SOURCE_VERIFICATION_COMPLETE_MAPPING_NOT_EVALUATED"
CLAIM_BOUNDARY = (
    "EXACT_SELECTED_EIGHT_CELL_REFERENCE_BLIND_NUMERIC_READER_AGREEMENT_"
    "WITH_SEALED_SOURCE_GRAPH_AND_CROP_REPLAY_ONLY_NO_LABEL_PERIOD_UNIT_SCOPE_"
    "STATEMENT_SCHEMA_REPORT_NORM_ID_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
E0047_PATH = Path(
    "docs/experiments/E-0047-loan-maturity-ordered-row-value-lane-mechanism-evaluation.json"
)
REGISTRY_DIRECTORY = Path("output/development/mbb-maturity-numeric-v1/frozen")
REGISTRY_PATH = REGISTRY_DIRECTORY / "crop_registry.json"
RUN_DIRECTORY = Path("output/development/mbb-maturity-numeric-v1/reader-run-v1")
PREDICTIONS_PATH = RUN_DIRECTORY / "predictions.json"
RUN_MANIFEST_PATH = RUN_DIRECTORY / "run_manifest.json"
SELECTION_PATH = Path("docs/experiments/E-0048-mbb-maturity-numeric-selection-authority.json")
VERIFICATION_PATH = Path("docs/experiments/E-0048-mbb-maturity-numeric-verification.json")
MODEL_CACHE = Path("/workspace/bctc-ai-models/verified_numeric_v1")
_MBB_BANK = "MBB"
_MBB_PAGE_ORDINAL = 2
_MBB_PHYSICAL_PAGE = 31
_MBB_SOURCE_PDF_SHA256 = "a86757a4499953264ca22dd57ae2e3257057631107742e1d04ad1ecd0e2c23d1"
_EXPECTED_ROLES = ("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "TOTAL")
_EXPECTED_SOURCE_LINES = (92, 93, 95, 96, 98, 99, 100, 101)
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/capture_e0048_mbb_maturity_numeric_verification.py"),
    Path("scripts/experiments/ordered_graph_numeric_cell_registry_v1.py"),
    Path("scripts/experiments/evaluate_e0047_ordered_row_value_lane_assignment.py"),
    Path("scripts/experiments/ordered_row_value_lane_assignment_v1.py"),
    Path("scripts/models/run_numeric_cell_recognizer.py"),
    Path("config/models/numeric-recognizer-v1.toml"),
)
_SELECTION_STATE = "FROZEN_NUMERIC_PROPOSAL_SELECTION_AUTHORITY"
_SELECTION_CLAIM_BOUNDARY = (
    "SELECTS_EXACT_PERSISTED_NUMERIC_PROPOSAL_ARTIFACT_BYTES_ONLY_"
    "NO_NUMERIC_TRUTH_GEOMETRY_PERIOD_UNIT_SCOPE_STATEMENT_SCHEMA_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "accounting_closure_used_to_repair_or_select_digits": False,
    "automatic_reader_overwrite_authority": False,
    "confidence_or_reader_score_decision_authority": False,
    "geometry_authority": False,
    "mapping_or_verified_by_codex_authority": False,
    "numeric_candidate_verification_only": True,
    "period_unit_scope_or_statement_authority": False,
    "persisted_result_self_authenticating": False,
    "report_norm_id_or_schema_authority": False,
    "source_only_total_mapped_to_schema": False,
    "transformer_text_used_as_numeric_truth": False,
}
_TOP_FIELDS = {
    "cells",
    "claim_boundary",
    "closure_equations",
    "experiment_id",
    "format_version",
    "inputs",
    "metrics",
    "safety",
    "state",
    "status",
    "verification_id",
}
_CELL_FIELDS = {
    "axis_id",
    "axis_ordinal",
    "cell_id",
    "challenger",
    "crop_sha256",
    "decision",
    "final_value_status",
    "normalized_numeric_value",
    "page_ordinal",
    "primary",
    "row_ordinal",
    "row_role",
    "selected_raw_value",
    "source_atom_id",
    "source_evidence_node_id",
    "source_graph_node_id",
    "source_line_index",
    "verification_status",
}


class E0048MBBMaturityNumericVerificationError(RuntimeError):
    """The selected numeric run or exact MBB source replay drifted."""


def _error(message: str) -> E0048MBBMaturityNumericVerificationError:
    return E0048MBBMaturityNumericVerificationError(message)


def _root(value: Any) -> Path:
    root = e0047._root(value)
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise _error("E-0048 project root is not a Git worktree")
    try:
        top = Path(completed.stdout.decode("utf-8").strip()).resolve(strict=True)
    except UnicodeDecodeError as exc:
        raise _error("E-0048 Git root is not UTF-8") from exc
    if top != root:
        raise _error("E-0048 project root is not the exact Git toplevel")
    return root


def _git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout
    except subprocess.CalledProcessError as exc:
        raise _error(f"E-0048 Git check failed: {' '.join(args)}") from exc


def _clean_head(root: Path) -> str:
    if _git(root, "status", "--porcelain"):
        raise _error("E-0048 requires one clean committed worktree")
    head = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    if _COMMIT.fullmatch(head) is None:
        raise _error("E-0048 HEAD is not one full commit identity")
    return head


def _strict_json(raw: bytes, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise _error(f"{label} repeats JSON key {key!r}")
            result[key] = value
        return result

    def reject(value: str) -> None:
        raise _error(f"{label} contains non-finite JSON constant {value}")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc


def _artifact_pin(path: Path, raw: bytes) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def _load_mbb_source_frontier(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    raw = e0047._stable_regular_bytes(root / E0047_PATH, "tracked E-0047 result")
    persisted = e0047._strict_json_bytes(raw, "tracked E-0047 result")
    evaluated = e0047.validate_e0047_ordered_row_value_lane_evaluation(persisted, root)
    e0046_payload, _authority = e0047._input_authority(root)
    matches = [
        trial
        for trial in e0046_payload["trials"]
        if trial["bank_provenance"] == _MBB_BANK
        and trial["selection_provenance"]["page_ordinal"] == _MBB_PAGE_ORDINAL
    ]
    if len(matches) != 1:
        raise _error("E-0048 cannot uniquely resolve the MBB source trial")
    trial = matches[0]
    selection = trial["selection_provenance"]
    if (
        selection["physical_page"] != _MBB_PHYSICAL_PAGE
        or selection["source_pdf_sha256"] != _MBB_SOURCE_PDF_SHA256
        or trial["semantic_page_binding"].get("binding_mode") != e0047._ORDINARY_MODE
    ):
        raise _error("E-0048 MBB source locator or binding mode drifted")
    alias_index = compile_vietnamese_family_alias_index_v1(e0047._FAMILY_SPECS)
    observation, assignment = e0047._candidate_payload_with_ordered_lanes(
        trial["source_projection"], trial["semantic_page_binding"], alias_index
    )
    if assignment is None or assignment["status"] != "RESOLVED_ORDERED_ROW_VALUE_LANES":
        raise _error("E-0048 requires the exact resolved ordered MBB value lanes")
    graph = graph_v2._build_from_observation(
        observation,
        e0047.LOAN_MATURITY_BUCKETS_SPEC_V1,
        e0047._FAMILY_SPECS,
    )
    if graph["status"] != "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE":
        raise _error("E-0048 requires one accepted MBB structural graph frontier")
    e0047_trial = evaluated["trials"][_MBB_PAGE_ORDINAL - 1]
    if (
        e0047_trial["bank_provenance"] != _MBB_BANK
        or e0047_trial["semantic_graph"]["graph_id"] != graph["graph_id"]
        or e0047_trial["semantic_graph"]["payload_sha256"] != canonical_json_sha256_v1(graph)
        or e0047_trial["schema_candidate"]["status"] != "CANDIDATE_SET_READY"
        or e0047_trial["independent_numeric_status"] != "NOT_EVALUATED"
        or e0047_trial["independent_mapping_status"] != "NOT_EVALUATED"
    ):
        raise _error("E-0048 MBB graph differs from the tracked E-0047 frontier")
    return (
        canonical_clone_v1(trial["source_projection"]),
        canonical_clone_v1(trial["semantic_page_binding"]),
        canonical_clone_v1(graph),
        canonical_clone_v1(evaluated),
    )


def _load_registry(
    root: Path,
    source: dict[str, Any],
    binding: dict[str, Any],
    graph: dict[str, Any],
) -> tuple[dict[str, Any], bytes]:
    raw = e0047._stable_regular_bytes(root / REGISTRY_PATH, "E-0048 numeric registry")
    value = _strict_json(raw, "E-0048 numeric registry")
    try:
        replayed = registry_v1.validate_ordered_graph_numeric_cell_registry_replay_v1(
            value,
            REGISTRY_DIRECTORY,
            root,
            source,
            binding,
            graph,
        )
    except registry_v1.OrderedGraphNumericCellRegistryV1Error as exc:
        raise _error("E-0048 numeric registry failed exact source replay") from exc
    if [cell["source_line_index"] for cell in replayed["cells"]] != list(_EXPECTED_SOURCE_LINES):
        raise _error("E-0048 numeric registry source-line frontier drifted")
    return replayed, raw


def freeze_e0048_mbb_maturity_numeric_registry_v1(project_root: Path) -> dict[str, Any]:
    """Create the fixed reference-blind MBB eight-cell registry once."""

    root = _root(project_root)
    _clean_head(root)
    source, binding, graph, _evaluated = _load_mbb_source_frontier(root)
    return registry_v1.build_ordered_graph_numeric_cell_registry_v1(
        root,
        REGISTRY_DIRECTORY,
        source,
        binding,
        graph,
    )


def _validate_selected_artifacts(
    root: Path,
    selection: dict[str, Any] | None = None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    bytes,
    bytes,
    bytes,
]:
    source, binding, graph, evaluated = _load_mbb_source_frontier(root)
    registry, registry_raw = _load_registry(root, source, binding, graph)
    predictions_raw = e0047._stable_regular_bytes(
        root / PREDICTIONS_PATH, "E-0048 numeric predictions"
    )
    run_raw = e0047._stable_regular_bytes(root / RUN_MANIFEST_PATH, "E-0048 numeric run manifest")
    predictions_pin = numeric_receipt.ArtifactPinV1(
        PREDICTIONS_PATH,
        hashlib.sha256(predictions_raw).hexdigest(),
        len(predictions_raw),
    )
    registry_pin = numeric_receipt.ArtifactPinV1(
        REGISTRY_PATH,
        hashlib.sha256(registry_raw).hexdigest(),
        len(registry_raw),
    )
    run_pin = numeric_receipt.ArtifactPinV1(
        RUN_MANIFEST_PATH,
        hashlib.sha256(run_raw).hexdigest(),
        len(run_raw),
    )
    predictions = numeric_receipt._validate_predictions(
        _strict_json(predictions_raw, "E-0048 numeric predictions"),
        registry,
        (root / REGISTRY_PATH).parent,
    )
    run_unchecked = _strict_json(run_raw, "E-0048 numeric run manifest")
    run_commit = run_unchecked.get("code", {}).get("commit")
    if _COMMIT.fullmatch(run_commit or "") is None:
        raise _error("E-0048 numeric run commit is invalid")
    run = numeric_receipt._validate_run_manifest(
        run_unchecked,
        root=root,
        run_path=(root / RUN_MANIFEST_PATH).resolve(strict=True),
        predictions_pin=predictions_pin,
        predictions_path=(root / PREDICTIONS_PATH).resolve(strict=True),
        registry_pin=registry_pin,
        registry=registry,
        expected_run_commit=run_commit,
    )
    expected_counts = dict(sorted(Counter(item["proposal_status"] for item in predictions).items()))
    if run["metrics"]["proposal_status_counts"] != expected_counts:
        raise _error("E-0048 numeric proposal-status counts drifted")
    numeric_receipt._validate_config_and_model(root, MODEL_CACHE, run)
    if selection is not None:
        expected_selection = {
            "artifacts": {
                "predictions": numeric_receipt._pin_record(predictions_pin),
                "registry": numeric_receipt._pin_record(registry_pin),
                "run_manifest": numeric_receipt._pin_record(run_pin),
            },
            "cell_count": 8,
            "claim_boundary": _SELECTION_CLAIM_BOUNDARY,
            "format_version": 1,
            "run_commit": run_commit,
            "state": _SELECTION_STATE,
        }
        if not same_typed_json_v1(selection, expected_selection):
            raise _error("E-0048 tracked selection differs from exact selected artifacts")
    return evaluated, source, binding, graph, registry_raw, predictions_raw, run_raw


def build_e0048_mbb_maturity_numeric_selection_v1(project_root: Path) -> dict[str, Any]:
    """Build the fixed selection payload at the clean numeric run commit."""

    root = _root(project_root)
    head = _clean_head(root)
    if (root / SELECTION_PATH).exists():
        raise _error("E-0048 numeric selection already exists")
    _evaluated, _source, _binding, _graph, registry_raw, predictions_raw, run_raw = (
        _validate_selected_artifacts(root)
    )
    run = _strict_json(run_raw, "E-0048 numeric run manifest")
    if run["code"]["commit"] != head or run["code"]["dirty"] is not False:
        raise _error("E-0048 selection must be built at the exact clean numeric run commit")
    selection = {
        "artifacts": {
            "predictions": _artifact_pin(PREDICTIONS_PATH, predictions_raw),
            "registry": _artifact_pin(REGISTRY_PATH, registry_raw),
            "run_manifest": _artifact_pin(RUN_MANIFEST_PATH, run_raw),
        },
        "cell_count": 8,
        "claim_boundary": _SELECTION_CLAIM_BOUNDARY,
        "format_version": 1,
        "run_commit": head,
        "state": _SELECTION_STATE,
    }
    if _clean_head(root) != head:
        raise _error("E-0048 Git state changed while building selection")
    return selection


def _selection_git_lineage(
    root: Path,
    selection_raw: bytes,
    selection: dict[str, Any],
) -> dict[str, Any]:
    head = _clean_head(root)
    run_commit = selection["run_commit"]
    additions = [
        item
        for item in _git(
            root,
            "log",
            "--all",
            "--diff-filter=A",
            "--format=%H",
            "--",
            SELECTION_PATH.as_posix(),
        )
        .decode("ascii")
        .splitlines()
        if item
    ]
    if len(additions) != 1 or _COMMIT.fullmatch(additions[0]) is None:
        raise _error("E-0048 selection does not have one unique Git ADD commit")
    selection_commit = additions[0]
    parents = _git(root, "show", "-s", "--format=%P", selection_commit).decode().split()
    if parents != [run_commit]:
        raise _error("E-0048 selection commit is not the direct child of the run commit")
    changed = [
        line
        for line in _git(
            root,
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            selection_commit,
        )
        .decode("utf-8")
        .splitlines()
        if line
    ]
    if changed != [f"A\t{SELECTION_PATH.as_posix()}"]:
        raise _error("E-0048 selection commit added more than the fixed selection artifact")
    numeric_receipt._verify_git_execution_ledger(
        root,
        run_commit,
        selection_commit,
        SELECTION_PATH,
        selection_raw,
    )
    implementation = []
    for path in _IMPLEMENTATION_PATHS:
        current = e0047._stable_regular_bytes(root / path, f"E-0048 trust closure {path}")
        if any(
            _git(root, "show", f"{commit}:{path.as_posix()}") != current
            for commit in (run_commit, selection_commit, head)
        ):
            raise _error(f"E-0048 implementation changed across run/selection/replay: {path}")
        implementation.append(_artifact_pin(path, current))
    return {
        "clean_consumer_head_validated_but_not_persisted": True,
        "consumer_head": head,
        "implementation_refs": implementation,
        "run_commit": run_commit,
        "selection_commit": selection_commit,
    }


def _verification_id(value: dict[str, Any]) -> str:
    material = canonical_clone_v1(value)
    material.pop("verification_id", None)
    return "e0048:numeric-verification:" + canonical_json_sha256_v1(material)


def _contains_verified_by_codex(value: Any) -> bool:
    if type(value) is str:
        return value == "VERIFIED_BY_CODEX"
    if type(value) is list:
        return any(_contains_verified_by_codex(item) for item in value)
    if type(value) is dict:
        return any(
            _contains_verified_by_codex(key) or _contains_verified_by_codex(item)
            for key, item in value.items()
        )
    return False


def _validate_result_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _TOP_FIELDS:
        raise _error("E-0048 verification fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["experiment_id"] != EXPERIMENT_ID
        or value["state"] != STATE
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or value["verification_id"] != _verification_id(value)
        or _contains_verified_by_codex(value)
        or type(value["cells"]) is not list
        or len(value["cells"]) != 8
        or any(type(cell) is not dict or set(cell) != _CELL_FIELDS for cell in value["cells"])
    ):
        raise _error("E-0048 verification identity or safety boundary drifted")
    if [cell["source_line_index"] for cell in value["cells"]] != list(_EXPECTED_SOURCE_LINES) or [
        cell["row_role"] for cell in value["cells"]
    ] != [role for role in _EXPECTED_ROLES for _axis in range(2)]:
        raise _error("E-0048 verification cell frontier drifted")
    equations = value["closure_equations"]
    if type(equations) is not list or len(equations) != 2:
        raise _error("E-0048 closure equation denominator drifted")
    for axis, equation in enumerate(equations):
        if (
            type(equation) is not dict
            or set(equation) != {"addends", "axis_ordinal", "observed_total", "residual", "status"}
            or equation["axis_ordinal"] != axis
            or type(equation["addends"]) is not list
            or len(equation["addends"]) != 3
            or equation["status"] not in {"CORROBORATED", "UNRESOLVED"}
        ):
            raise _error("E-0048 closure equation shape drifted")
    metrics = value["metrics"]
    expected_metric_fields = {
        "cell_count",
        "closure_axis_count",
        "corroborated_closure_axis_count",
        "mapped_cell_count",
        "reader_score_decision_use_count",
        "unresolved_cell_count",
        "verified_cell_count",
    }
    if (
        type(metrics) is not dict
        or set(metrics) != expected_metric_fields
        or any(type(metrics[key]) is not int or metrics[key] < 0 for key in metrics)
        or metrics["cell_count"] != 8
        or metrics["closure_axis_count"] != 2
        or metrics["mapped_cell_count"] != 0
        or metrics["reader_score_decision_use_count"] != 0
        or metrics["verified_cell_count"] + metrics["unresolved_cell_count"] != 8
    ):
        raise _error("E-0048 verification metrics drifted")
    return canonical_clone_v1(value)


def build_e0048_mbb_maturity_numeric_verification_v1(
    project_root: Path,
) -> dict[str, Any]:
    """Exact-replay the selected numeric run and derive the bounded result."""

    root = _root(project_root)
    selection_raw = e0047._stable_regular_bytes(root / SELECTION_PATH, "E-0048 selection")
    selection_value = _strict_json(selection_raw, "E-0048 selection")
    if type(selection_value) is not dict:
        raise _error("E-0048 selection must be one JSON object")
    evaluated, source, binding, graph, registry_raw, predictions_raw, run_raw = (
        _validate_selected_artifacts(root, selection_value)
    )
    lineage = _selection_git_lineage(root, selection_raw, selection_value)
    registry = _strict_json(registry_raw, "E-0048 registry")
    predictions = _strict_json(predictions_raw, "E-0048 predictions")
    try:
        fused = _verify_numeric_cell_proposals(
            canonical_clone_v1(registry),
            canonical_clone_v1(predictions),
            allow_semantic_graph_v3=True,
        )
    except NumericCellVerificationError as exc:
        raise _error("E-0048 exact numeric proposal fusion failed") from exc
    fused_by_id = {cell["cell_id"]: cell for cell in fused["cells"]}
    records = []
    for source_cell in registry["cells"]:
        fused_cell = fused_by_id[source_cell["cell_id"]]
        row = source_cell["row_ordinal"]
        records.append(
            {
                "axis_id": source_cell["axis_id"],
                "axis_ordinal": source_cell["axis_ordinal"],
                "cell_id": source_cell["cell_id"],
                "challenger": canonical_clone_v1(fused_cell["challenger"]),
                "crop_sha256": source_cell["crop_sha256"],
                "decision": fused_cell["decision"],
                "final_value_status": fused_cell["final_value_status"],
                "normalized_numeric_value": fused_cell["normalized_numeric_value"],
                "page_ordinal": source_cell["page"],
                "primary": canonical_clone_v1(fused_cell["primary"]),
                "row_ordinal": row,
                "row_role": _EXPECTED_ROLES[row],
                "selected_raw_value": fused_cell["selected_raw_value"],
                "source_atom_id": source_cell["source_atom_id"],
                "source_evidence_node_id": source_cell["source_evidence_node_id"],
                "source_graph_node_id": source_cell["source_graph_node_id"],
                "source_line_index": source_cell["source_line_index"],
                "verification_status": fused_cell["verification_status"],
            }
        )
    equations = []
    for axis in range(2):
        cells = [records[row * 2 + axis] for row in range(4)]
        values = [cell["normalized_numeric_value"] for cell in cells]
        exact = all(
            cell["verification_status"] == "VERIFIED_OBSERVED_VALUE"
            and type(value) is str
            and value.isdigit()
            for cell, value in zip(cells, values, strict=True)
        )
        if exact:
            addends = [int(value) for value in values[:3]]
            total = int(values[3])
            residual = total - sum(addends)
            status = "CORROBORATED" if residual == 0 else "UNRESOLVED"
        else:
            addends = [value for value in values[:3]]
            total = values[3]
            residual = None
            status = "UNRESOLVED"
        equations.append(
            {
                "addends": addends,
                "axis_ordinal": axis,
                "observed_total": total,
                "residual": residual,
                "status": status,
            }
        )
    verified_count = sum(
        cell["verification_status"] == "VERIFIED_OBSERVED_VALUE" for cell in records
    )
    corroborated = sum(item["status"] == "CORROBORATED" for item in equations)
    e0047_raw = e0047._stable_regular_bytes(root / E0047_PATH, "E-0047 result")
    selection_pin = _artifact_pin(SELECTION_PATH, selection_raw)
    result = {
        "cells": records,
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_equations": equations,
        "experiment_id": EXPERIMENT_ID,
        "format_version": FORMAT_VERSION,
        "inputs": {
            "e0047": {
                **_artifact_pin(E0047_PATH, e0047_raw),
                "result_id": evaluated["result_id"],
            },
            "graph": {
                "graph_id": graph["graph_id"],
                "sha256": canonical_json_sha256_v1(graph),
            },
            "numeric_artifacts": {
                "predictions": _artifact_pin(PREDICTIONS_PATH, predictions_raw),
                "registry": {
                    **_artifact_pin(REGISTRY_PATH, registry_raw),
                    "registry_id": registry["registry_id"],
                },
                "run_manifest": _artifact_pin(RUN_MANIFEST_PATH, run_raw),
                "selection": selection_pin,
            },
            "run_lineage": lineage,
            "source": {
                "physical_page": _MBB_PHYSICAL_PAGE,
                "semantic_page_binding_sha256": canonical_json_sha256_v1(binding),
                "source_local_page_id": source["source_local_page_id"],
                "source_pdf_sha256": _MBB_SOURCE_PDF_SHA256,
                "source_projection_sha256": canonical_json_sha256_v1(source),
            },
        },
        "metrics": {
            "cell_count": 8,
            "closure_axis_count": 2,
            "corroborated_closure_axis_count": corroborated,
            "mapped_cell_count": 0,
            "reader_score_decision_use_count": 0,
            "unresolved_cell_count": 8 - verified_count,
            "verified_cell_count": verified_count,
        },
        "safety": canonical_clone_v1(_SAFETY),
        "state": STATE,
        "status": (
            "COMPLETE_WITH_EXACT_EIGHT_CELL_AGREEMENT_AND_TWO_AXIS_CLOSURE"
            if verified_count == 8 and corroborated == 2
            else "COMPLETE_WITH_UNRESOLVED_NUMERIC_CANDIDATES"
        ),
        "verification_id": "",
    }
    result["verification_id"] = _verification_id(result)
    return _validate_result_shape(result)


def validate_e0048_mbb_maturity_numeric_verification_v1(
    value: Any,
    project_root: Path,
) -> dict[str, Any]:
    """Typed-compare a persisted result with one complete exact rebuild."""

    persisted = _validate_result_shape(value)
    rebuilt = build_e0048_mbb_maturity_numeric_verification_v1(project_root)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("persisted E-0048 result differs from exact live replay")
    return rebuilt


def _write_once(root: Path, relative: Path, value: Any) -> None:
    target = root / relative
    if target.exists():
        raise _error(f"refusing to overwrite E-0048 artifact: {relative}")
    atomic_write_json(target, value)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("freeze", "write-selection", "write-verification", "validate")
    )
    return parser


def _main() -> int:
    args = _parser().parse_args()
    root = PROJECT_ROOT
    if args.command == "freeze":
        value = freeze_e0048_mbb_maturity_numeric_registry_v1(root)
        summary = {"registry_id": value["registry_id"], "cell_count": 8}
    elif args.command == "write-selection":
        value = build_e0048_mbb_maturity_numeric_selection_v1(root)
        _write_once(root, SELECTION_PATH, value)
        summary = {"selection_path": SELECTION_PATH.as_posix(), "run_commit": value["run_commit"]}
    elif args.command == "write-verification":
        value = build_e0048_mbb_maturity_numeric_verification_v1(root)
        _write_once(root, VERIFICATION_PATH, value)
        summary = {
            "status": value["status"],
            "verification_id": value["verification_id"],
        }
    else:
        raw = e0047._stable_regular_bytes(root / VERIFICATION_PATH, "E-0048 verification")
        value = validate_e0048_mbb_maturity_numeric_verification_v1(
            _strict_json(raw, "E-0048 verification"), root
        )
        summary = {
            "status": value["status"],
            "verification_id": value["verification_id"],
        }
    os.write(1, (json.dumps(summary, sort_keys=True) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
