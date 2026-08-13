"""Reference-blind numeric crops for an accepted Semantic Accounting Graph v2.

The graph already binds each VALUE_POSITION to one authenticated PP-OCRv6 LINE.
This module copies the exact corresponding all-LINE crop into a new immutable
numeric-reader registry.  The reader sees only the crop path; labels, periods,
units, primary OCR text/values, graph roles and schema candidates remain sealed
in the registry and are not part of its request payload.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_bytes, sha256_file
from bctc_ai.evaluation.financial_cells_v2 import parse_financial_number_strict_grouping
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    FamilySpecV1,
    local_accounting_family_spec_sha256_v1,
)
from bctc_ai.source_structure.semantic_local_accounting_graph_v2 import (
    validate_semantic_local_accounting_graph_replay_v2,
)
from bctc_ai.source_structure.vietocr_semantic_receipt_v2 import (
    validate_vietocr_semantic_page_binding_v2,
)

__all__ = [
    "FORMAT_VERSION",
    "GEOMETRY_AUTHORITY",
    "POLICY",
    "SemanticGraphNumericCellCropV1Error",
    "build_semantic_graph_numeric_cell_crop_registry_v1",
    "validate_semantic_graph_numeric_cell_crop_registry_replay_v1",
]


FORMAT_VERSION = 3
POLICY = "SEMANTIC_GRAPH_V2_VALUE_POSITION_CROPS_V1"
GEOMETRY_AUTHORITY = "AUTHENTICATED_V3_LINE_GEOMETRY"
CLAIM_BOUNDARY = (
    "REPLAYED_SEMANTIC_GRAPH_VALUE_POSITION_PIXEL_CROPS_FOR_REFERENCE_BLIND_"
    "NUMERIC_PROPOSALS_ONLY_NO_LABEL_PERIOD_UNIT_SCOPE_SCHEMA_OR_EXPORT_AUTHORITY"
)
_EXPECTED_RECOGNIZER_INPUT_FIELDS = ["crop_path"]
_FORBIDDEN_RECOGNIZER_INPUTS = [
    "accounting_or_family_role",
    "expected_or_primary_numeric_text_or_value",
    "human_review_value",
    "label_or_owner_or_branch_text",
    "period_or_unit_or_scope",
    "schema_label_or_report_norm_id",
]
_REFERENCE_ISOLATION = {
    "accounting_or_family_roles_available_to_reader": False,
    "expected_or_primary_numeric_text_or_value_available_to_reader": False,
    "human_review_available_to_reader": False,
    "label_owner_or_branch_text_available_to_reader": False,
    "period_unit_or_scope_available_to_reader": False,
    "schema_label_or_report_norm_id_available_to_reader": False,
}
_TOP_FIELDS = {
    "claim_boundary",
    "format_version",
    "geometry_authority",
    "metrics",
    "policy",
    "recognizer_input_fields",
    "forbidden_recognizer_inputs",
    "reference_isolation",
    "registry_id",
    "semantic_graph",
    "semantic_page_binding_sha256",
    "source_projection_sha256",
    "cells",
}
_CELL_FIELDS = {
    "axis_id",
    "axis_ordinal",
    "cell_id",
    "crop_path",
    "crop_sha256",
    "crop_size_bytes",
    "page",
    "primary_normalized_text",
    "primary_observation",
    "primary_raw_text",
    "primary_sign_evidence",
    "primary_value",
    "recognizer_payload",
    "row_ordinal",
    "source_atom_id",
    "source_bbox_raw_pixels",
    "source_evidence_node_id",
    "source_graph_node_id",
    "source_line_index",
    "visual_punctuation_evidence",
}


class SemanticGraphNumericCellCropV1Error(ValueError):
    """The graph, source-line/crop binding, or isolated registry drifted."""


def _error(message: str) -> SemanticGraphNumericCellCropV1Error:
    return SemanticGraphNumericCellCropV1Error(message)


def _primary_observation(node: Mapping[str, Any]) -> tuple[str, str, str, str | None]:
    attributes = node["attributes"]
    state = attributes["state"]
    raw = attributes["raw_text"]
    normalized = attributes["normalized_decimal"]
    parsed = parse_financial_number_strict_grouping(raw)
    if (
        state == "OBSERVED_VALUE"
        and parsed.observation is ObservationKind.VALUE
        and parsed.value is not None
        and format(parsed.value, "f") == normalized
    ):
        return "VALUE", raw, normalized, parsed.sign_evidence
    raise _error("numeric crop v1 supports only nonzero observed graph values")


def _registry_id(value: Mapping[str, Any]) -> str:
    payload = canonical_clone_v1(value)
    payload.pop("registry_id", None)
    return f"sgncrv1:registry:{canonical_json_sha256_v1(payload)}"


def _validate_registry_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _TOP_FIELDS:
        raise _error("semantic-graph numeric registry fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["policy"] != POLICY
        or value["geometry_authority"] != GEOMETRY_AUTHORITY
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["recognizer_input_fields"] != _EXPECTED_RECOGNIZER_INPUT_FIELDS
        or value["forbidden_recognizer_inputs"] != _FORBIDDEN_RECOGNIZER_INPUTS
        or value["reference_isolation"] != _REFERENCE_ISOLATION
        or value["registry_id"] != _registry_id(value)
        or type(value["cells"]) is not list
        or any(type(cell) is not dict or set(cell) != _CELL_FIELDS for cell in value["cells"])
    ):
        raise _error("semantic-graph numeric registry identity or shape drifted")
    return canonical_clone_v1(value)


def _stable_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        before = path.stat()
        first = path.read_bytes()
        second = path.read_bytes()
        after = path.stat()
        if (
            first != second
            or before.st_size != len(first)
            or after.st_size != len(first)
            or before.st_mtime_ns != after.st_mtime_ns
        ):
            raise _error(f"{label} changed while read")

        def closed_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, item in pairs:
                if key in result:
                    raise _error(f"{label} contains duplicate JSON key")
                result[key] = item
            return result

        value = json.loads(first, object_pairs_hook=closed_pairs)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} cannot be read as UTF-8 JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be one JSON object")
    return value


def _make_in_project_replay_directory(root: Path, prefix: str) -> Path:
    """Create an unpredictable real directory directly under resolved root."""

    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise _error("numeric replay project root is unsafe")
    try:
        directory = Path(tempfile.mkdtemp(prefix=prefix, dir=root))
        resolved = directory.resolve(strict=True)
    except OSError as exc:
        raise _error("numeric replay directory cannot be created") from exc
    if directory.is_symlink() or resolved.parent != root or not resolved.is_dir():
        shutil.rmtree(directory, ignore_errors=True)
        raise _error("numeric replay directory escaped project root")
    return resolved


def build_semantic_graph_numeric_cell_crop_registry_v1(
    project_root: Path,
    output_directory: Path,
    semantic_graph_v2: Any,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: tuple[FamilySpecV1, ...],
) -> dict[str, Any]:
    """Copy the exact graph VALUE_POSITION crops into a closed reader registry."""

    root = project_root.resolve()
    output = output_directory.resolve()
    try:
        output.relative_to(root)
    except ValueError as exc:
        raise _error("numeric crop output escapes project root") from exc
    if output.exists():
        raise _error("refusing to overwrite semantic-graph numeric crop registry")
    try:
        graph = validate_semantic_local_accounting_graph_replay_v2(
            semantic_graph_v2,
            source_projection_v2,
            semantic_page_binding_v2,
            authenticated_transformer_receipt_v2,
            family_spec,
            family_specs_for_collision_scope,
        )
        binding = validate_vietocr_semantic_page_binding_v2(
            semantic_page_binding_v2,
            source_projection_v2,
            authenticated_transformer_receipt_v2,
        )
    except ValueError as exc:
        raise _error("numeric crops require exact replayed graph/page inputs") from exc
    if graph["status"] != "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE":
        raise _error("numeric crops require one accepted semantic graph")
    if (
        family_spec.family_id != LOAN_MATURITY_BUCKETS_SPEC_V1.family_id
        or graph["family_id"] != LOAN_MATURITY_BUCKETS_SPEC_V1.family_id
        or graph["family_spec_sha256"]
        != local_accounting_family_spec_sha256_v1(LOAN_MATURITY_BUCKETS_SPEC_V1)
    ):
        raise _error("numeric crop v1 is bounded to the exact loan-maturity family spec")
    evidence_by_id = {
        node["node_id"]: node for node in graph["nodes"] if node["kind"] == "EVIDENCE"
    }
    samples_by_atom = {
        sample["source_atom"]["source_atom_id"]: sample for sample in binding["samples"]
    }
    value_nodes = sorted(
        (node for node in graph["nodes"] if node["kind"] == "VALUE_POSITION"),
        key=lambda node: (node["attributes"]["row_ordinal"], node["attributes"]["axis_index"]),
    )
    if len(value_nodes) != 8:
        raise _error("semantic-graph numeric v1 requires the exact eight-cell maturity core")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        crops = temporary / "crops"
        crops.mkdir()
        records = []
        for node in value_nodes:
            attributes = node["attributes"]
            source_ids = node["source_ref"]["source_atom_ids"]
            if len(source_ids) != 1:
                raise _error("numeric VALUE_POSITION must cite exactly one source LINE")
            sample = samples_by_atom.get(source_ids[0])
            if sample is None:
                raise _error("numeric VALUE_POSITION lacks one exact all-LINE crop binding")
            source_crop = (root / sample["crop_ref"]["path"]).resolve()
            try:
                source_crop.relative_to(root)
            except ValueError as exc:
                raise _error("bound numeric source crop escapes project root") from exc
            try:
                before = source_crop.stat()
                crop_bytes = source_crop.read_bytes()
                second = source_crop.read_bytes()
                after = source_crop.stat()
            except OSError as exc:
                raise _error("bound numeric source crop cannot be read") from exc
            if (
                crop_bytes != second
                or before.st_size != len(crop_bytes)
                or after.st_size != len(crop_bytes)
                or before.st_mtime_ns != after.st_mtime_ns
                or len(crop_bytes) != sample["crop_ref"]["size_bytes"]
                or sha256_bytes(crop_bytes) != sample["crop_ref"]["sha256"]
            ):
                raise _error("bound numeric source crop is missing or hash-drifted")
            numeric_evidence = [
                evidence
                for evidence in evidence_by_id.values()
                if evidence["attributes"]["evidence_role"] == "VALUE_NUMERIC"
                and evidence["source_ref"]["source_atom_ids"] == source_ids
            ]
            if len(numeric_evidence) != 1:
                raise _error("numeric VALUE_POSITION lacks unique numeric evidence")
            if numeric_evidence[0]["attributes"]["raw_text_utf8"] != attributes["raw_text"]:
                raise _error("numeric evidence text differs from VALUE_POSITION")
            row_ordinal = attributes["row_ordinal"]
            axis_index = attributes["axis_index"]
            cell_id = f"page-0001-row-{row_ordinal:03d}-axis-{axis_index + 1}"
            relative = Path("crops") / f"{cell_id}.png"
            target = temporary / relative
            target.write_bytes(crop_bytes)
            if sha256_file(target) != sample["crop_ref"]["sha256"]:
                raise _error("copied numeric crop differs from authenticated source crop")
            observation, raw, normalized, sign = _primary_observation(node)
            records.append(
                {
                    "cell_id": cell_id,
                    "page": 1,
                    "row_ordinal": row_ordinal,
                    "axis_ordinal": axis_index,
                    "axis_id": f"axis-{axis_index}",
                    "source_graph_node_id": node["node_id"],
                    "source_evidence_node_id": numeric_evidence[0]["node_id"],
                    "source_atom_id": source_ids[0],
                    "source_line_index": sample["source_line_index"],
                    "source_bbox_raw_pixels": canonical_clone_v1(sample["source_bbox_raw_pixels"]),
                    "crop_path": relative.as_posix(),
                    "crop_size_bytes": target.stat().st_size,
                    "crop_sha256": sha256_file(target),
                    "primary_observation": observation,
                    "primary_raw_text": raw,
                    "primary_normalized_text": normalized,
                    "primary_value": normalized,
                    "primary_sign_evidence": sign,
                    "visual_punctuation_evidence": None,
                    "recognizer_payload": {"crop_path": relative.as_posix()},
                }
            )
        registry = {
            "claim_boundary": CLAIM_BOUNDARY,
            "format_version": FORMAT_VERSION,
            "policy": POLICY,
            "geometry_authority": GEOMETRY_AUTHORITY,
            "semantic_graph": {
                "graph_id": graph["graph_id"],
                "sha256": canonical_json_sha256_v1(graph),
            },
            "source_projection_sha256": graph["source_projection_sha256"],
            "semantic_page_binding_sha256": canonical_json_sha256_v1(binding),
            "recognizer_input_fields": list(_EXPECTED_RECOGNIZER_INPUT_FIELDS),
            "forbidden_recognizer_inputs": list(_FORBIDDEN_RECOGNIZER_INPUTS),
            "reference_isolation": dict(_REFERENCE_ISOLATION),
            "metrics": {
                "page_count": 1,
                "row_count": 4,
                "cell_count": len(records),
                "primary_observation_counts": {"VALUE": len(records)},
            },
            "cells": records,
        }
        registry["registry_id"] = _registry_id(registry)
        registry = _validate_registry_shape(registry)
        atomic_write_json(temporary / "crop_registry.json", registry)
        os.replace(temporary, output)
        return registry
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def validate_semantic_graph_numeric_cell_crop_registry_replay_v1(
    value: Any,
    registry_directory: Path,
    project_root: Path,
    semantic_graph_v2: Any,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: tuple[FamilySpecV1, ...],
) -> dict[str, Any]:
    """Rebuild exact registry bytes/crops from authenticated upstream inputs."""

    persisted = _validate_registry_shape(value)
    directory = registry_directory.resolve()
    root = project_root.resolve()
    try:
        directory.relative_to(root)
    except ValueError as exc:
        raise _error("numeric registry directory escapes project root") from exc
    if registry_directory.is_symlink() or not directory.is_dir():
        raise _error("numeric registry directory is absent")
    replay_directory = _make_in_project_replay_directory(root, ".numeric-registry-replay-")
    replay_output = replay_directory / "rebuilt"
    try:
        rebuilt = build_semantic_graph_numeric_cell_crop_registry_v1(
            root,
            replay_output,
            semantic_graph_v2,
            source_projection_v2,
            semantic_page_binding_v2,
            authenticated_transformer_receipt_v2,
            family_spec,
            family_specs_for_collision_scope,
        )
        registry_path = directory / "crop_registry.json"
        persisted_file = _stable_json_object(registry_path, "persisted numeric crop registry")
        if not same_typed_json_v1(persisted_file, persisted):
            raise _error("persisted numeric crop registry file differs from supplied value")
        if not same_typed_json_v1(persisted, rebuilt):
            raise _error("persisted numeric crop registry differs from exact replay")
        for cell in rebuilt["cells"]:
            unresolved_crop = directory / cell["crop_path"]
            if unresolved_crop.is_symlink():
                raise _error("persisted numeric crop path is a symlink")
            persisted_crop = unresolved_crop.resolve()
            replay_crop = (replay_output / cell["crop_path"]).resolve()
            try:
                before = persisted_crop.stat()
                first = persisted_crop.read_bytes()
                second = persisted_crop.read_bytes()
                after = persisted_crop.stat()
            except OSError as exc:
                raise _error("persisted numeric crop cannot be read") from exc
            if (
                not persisted_crop.is_relative_to(directory)
                or not persisted_crop.is_file()
                or first != second
                or before.st_size != len(first)
                or after.st_size != len(first)
                or before.st_mtime_ns != after.st_mtime_ns
                or first != replay_crop.read_bytes()
            ):
                raise _error("persisted numeric crop differs from exact replay")
        return rebuilt
    finally:
        shutil.rmtree(replay_directory, ignore_errors=True)
