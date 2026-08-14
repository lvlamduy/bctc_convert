#!/usr/bin/env python3
"""Build a reference-blind numeric registry from one replayed ordered graph.

This helper deliberately owns no source-selection authority.  Its caller must
first replay the source projection, semantic page binding, and graph.  Given
those exact payloads, it deterministically copies the eight bound line crops
for a four-row/two-axis ordered table into the existing numeric-reader request
shape.  Expected text, values, row roles, and graph identities remain sealed
in the registry and are never included in ``recognizer_payload``.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.evaluation.financial_cells_v2 import (
    parse_financial_number_strict_grouping,
)
from bctc_ai.evaluation.semantic_graph_numeric_cell_crops_v1 import (
    CLAIM_BOUNDARY,
    FORMAT_VERSION,
    GEOMETRY_AUTHORITY,
    POLICY,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "OrderedGraphNumericCellRegistryV1Error",
    "build_ordered_graph_numeric_cell_registry_v1",
    "validate_ordered_graph_numeric_cell_registry_replay_v1",
]


_EXPECTED_ROLES = ("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "TOTAL")
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
    "cells",
    "claim_boundary",
    "forbidden_recognizer_inputs",
    "format_version",
    "geometry_authority",
    "metrics",
    "policy",
    "recognizer_input_fields",
    "reference_isolation",
    "registry_id",
    "semantic_graph",
    "semantic_page_binding_sha256",
    "source_projection_sha256",
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


class OrderedGraphNumericCellRegistryV1Error(RuntimeError):
    """The graph/binding/crop axis cannot form the exact isolated registry."""


def _error(message: str) -> OrderedGraphNumericCellRegistryV1Error:
    return OrderedGraphNumericCellRegistryV1Error(message)


def _strict_root(value: Any) -> Path:
    if not isinstance(value, Path):
        raise _error("numeric registry project root must be one pathlib Path")
    root = value.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise _error("numeric registry project root is unsafe")
    return root


def _stable_regular_bytes(path: Path, label: str) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise _error(f"{label} cannot be opened nofollow") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error(f"{label} is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)

        def identity(item: os.stat_result) -> tuple[int, ...]:
            return (
                item.st_dev,
                item.st_ino,
                item.st_mode,
                item.st_nlink,
                item.st_size,
                item.st_mtime_ns,
                item.st_ctime_ns,
            )

        raw = b"".join(chunks)
        if identity(before) != identity(after) or len(raw) != before.st_size:
            raise _error(f"{label} changed while being read")
        return raw
    finally:
        os.close(descriptor)


def _safe_project_file(root: Path, value: Any, label: str) -> tuple[Path, bytes]:
    if (
        type(value) is not str
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
        or Path(value).as_posix() != value
    ):
        raise _error(f"{label} path is not one safe project-relative path")
    cursor = root
    for part in Path(value).parts:
        cursor /= part
        if cursor.is_symlink():
            raise _error(f"{label} path contains a symlink")
    path = (root / value).resolve(strict=True)
    if not path.is_relative_to(root):
        raise _error(f"{label} escapes the project root")
    return path, _stable_regular_bytes(path, label)


def _registry_id(value: dict[str, Any]) -> str:
    material = canonical_clone_v1(value)
    material.pop("registry_id", None)
    return "sgncrv1:registry:" + canonical_json_sha256_v1(material)


def _validate_registry_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _TOP_FIELDS:
        raise _error("ordered-graph numeric registry fields drifted")
    cells = value["cells"]
    if (
        type(value["format_version"]) is not int
        or value["format_version"] != FORMAT_VERSION
        or value["policy"] != POLICY
        or value["geometry_authority"] != GEOMETRY_AUTHORITY
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(
            value["recognizer_input_fields"], _EXPECTED_RECOGNIZER_INPUT_FIELDS
        )
        or not same_typed_json_v1(
            value["forbidden_recognizer_inputs"], _FORBIDDEN_RECOGNIZER_INPUTS
        )
        or not same_typed_json_v1(value["reference_isolation"], _REFERENCE_ISOLATION)
        or type(cells) is not list
        or len(cells) != 8
        or any(type(cell) is not dict or set(cell) != _CELL_FIELDS for cell in cells)
        or value["registry_id"] != _registry_id(value)
    ):
        raise _error("ordered-graph numeric registry identity or shape drifted")
    expected_ids = [
        f"page-{value['cells'][0]['page']:04d}-row-{row:03d}-axis-{axis + 1}"
        for row in range(4)
        for axis in range(2)
    ]
    if [cell["cell_id"] for cell in cells] != expected_ids:
        raise _error("ordered-graph numeric registry cell order drifted")
    metrics = value["metrics"]
    if not same_typed_json_v1(
        metrics,
        {
            "cell_count": 8,
            "page_count": 1,
            "primary_observation_counts": {"VALUE": 8},
            "row_count": 4,
        },
    ):
        raise _error("ordered-graph numeric registry denominator drifted")
    for row, cell in enumerate(cells):
        expected_row, expected_axis = divmod(row, 2)
        if (
            type(cell["page"]) is not int
            or cell["page"] < 1
            or type(cell["row_ordinal"]) is not int
            or cell["row_ordinal"] != expected_row
            or type(cell["axis_ordinal"]) is not int
            or cell["axis_ordinal"] != expected_axis
            or cell["axis_id"] != f"axis-{expected_axis}"
            or cell["primary_observation"] != "VALUE"
            or type(cell["crop_size_bytes"]) is not int
            or cell["crop_size_bytes"] < 1
            or type(cell["source_line_index"]) is not int
            or cell["source_line_index"] < 0
            or not same_typed_json_v1(cell["recognizer_payload"], {"crop_path": cell["crop_path"]})
        ):
            raise _error("ordered-graph numeric registry cell identity drifted")
    return canonical_clone_v1(value)


def _validated_inputs(
    source_projection: Any,
    semantic_page_binding: Any,
    semantic_graph: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not all(
        type(item) is dict for item in (source_projection, semantic_page_binding, semantic_graph)
    ):
        raise _error("ordered-graph registry inputs must be exact JSON objects")
    source = canonical_clone_v1(source_projection)
    binding = canonical_clone_v1(semantic_page_binding)
    graph = canonical_clone_v1(semantic_graph)
    source_sha = canonical_json_sha256_v1(source)
    binding_sha = canonical_json_sha256_v1(binding)
    if (
        binding.get("status") != "BOUND_TO_EXACT_NONTERMINAL_SOURCE_LINE_AXIS"
        or binding.get("binding_mode") != "ORDINARY_V2_PRIMARY_LINES"
        or binding.get("source_projection_sha256") != source_sha
        or graph.get("status") != "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE"
        or graph.get("source_projection_sha256") != source_sha
        or graph.get("semantic_page_binding_sha256") != binding_sha
        or graph.get("source_local_page_id") != binding.get("source_local_page_id")
        or graph.get("source_local_page_id") != source.get("source_local_page_id")
        or type(binding.get("page_ordinal")) is not int
        or binding["page_ordinal"] < 1
    ):
        raise _error("ordered graph/source/binding lineage drifted")
    samples = binding.get("samples")
    lines = source.get("page_result", {}).get("lines")
    if (
        type(samples) is not list
        or type(lines) is not list
        or len(samples) != len(lines)
        or not samples
    ):
        raise _error("ordered graph source and binding LINE axes are not coextensive")
    for ordinal, (sample, line) in enumerate(zip(samples, lines, strict=True)):
        if (
            type(sample) is not dict
            or sample.get("source_line_index") != ordinal
            or type(line) is not dict
            or type(line.get("raw_text")) is not str
        ):
            raise _error("ordered graph source or binding LINE identity drifted")
    return source, binding, graph


def _build_registry_and_crops(
    root: Path,
    source: dict[str, Any],
    binding: dict[str, Any],
    graph: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, bytes]]:
    evidence = {
        node["node_id"]: node
        for node in graph.get("nodes", [])
        if type(node) is dict
        and node.get("kind") == "EVIDENCE"
        and node.get("attributes", {}).get("evidence_role") == "VALUE_NUMERIC"
    }
    values = sorted(
        (
            node
            for node in graph.get("nodes", [])
            if type(node) is dict and node.get("kind") == "VALUE_POSITION"
        ),
        key=lambda node: (
            node.get("attributes", {}).get("row_ordinal", -1),
            node.get("attributes", {}).get("axis_index", -1),
        ),
    )
    expected_coordinates = [(row, axis) for row in range(4) for axis in range(2)]
    if (
        len(values) != 8
        or [
            (
                node.get("attributes", {}).get("row_ordinal"),
                node.get("attributes", {}).get("axis_index"),
            )
            for node in values
        ]
        != expected_coordinates
        or [values[row * 2]["attributes"].get("row_role") for row in range(4)]
        != list(_EXPECTED_ROLES)
        or any(
            values[row * 2 + axis]["attributes"].get("row_role") != _EXPECTED_ROLES[row]
            for row, axis in expected_coordinates
        )
    ):
        raise _error("ordered graph is not one exact four-row/two-axis maturity frontier")
    samples_by_atom: dict[str, dict[str, Any]] = {}
    for sample in binding["samples"]:
        atom = sample.get("source_atom", {}).get("source_atom_id")
        if type(atom) is not str or atom in samples_by_atom:
            raise _error("ordered graph binding source atom axis is invalid")
        samples_by_atom[atom] = sample

    page = binding["page_ordinal"]
    crops: dict[str, bytes] = {}
    records: list[dict[str, Any]] = []
    for node in values:
        attributes = node["attributes"]
        row = attributes["row_ordinal"]
        axis = attributes["axis_index"]
        atom_ids = node.get("source_ref", {}).get("source_atom_ids")
        if type(atom_ids) is not list or len(atom_ids) != 1 or type(atom_ids[0]) is not str:
            raise _error("numeric VALUE_POSITION does not cite exactly one source atom")
        atom_id = atom_ids[0]
        sample = samples_by_atom.get(atom_id)
        if sample is None:
            raise _error("numeric VALUE_POSITION lacks one exact bound source crop")
        matching_evidence = [
            item
            for item in evidence.values()
            if item.get("source_ref", {}).get("source_atom_ids") == [atom_id]
            and item.get("attributes", {}).get("source_line_index")
            == sample.get("source_line_index")
        ]
        if len(matching_evidence) != 1:
            raise _error("numeric VALUE_POSITION lacks one unique source numeric evidence node")
        numeric_evidence = matching_evidence[0]
        raw_text = attributes.get("raw_text")
        normalized = attributes.get("normalized_decimal")
        parsed = parse_financial_number_strict_grouping(raw_text)
        if (
            type(raw_text) is not str
            or type(normalized) is not str
            or attributes.get("state") != "OBSERVED_VALUE"
            or parsed.observation is not ObservationKind.VALUE
            or parsed.value is None
            or format(parsed.value, "f") != normalized
            or numeric_evidence["attributes"].get("raw_text_utf8") != raw_text
            or numeric_evidence["attributes"].get("numeric_authority") is not True
            or numeric_evidence["attributes"].get("text_source") != "PPOCRV6_NUMERIC_ONLY"
        ):
            raise _error("numeric graph primary value/evidence identity drifted")
        crop_ref = sample.get("crop_ref")
        if type(crop_ref) is not dict or set(crop_ref) != {"path", "sha256", "size_bytes"}:
            raise _error("bound numeric crop reference drifted")
        _, raw = _safe_project_file(
            root, crop_ref["path"], f"numeric crop line {sample['source_line_index']}"
        )
        if (
            type(crop_ref["sha256"]) is not str
            or hashlib.sha256(raw).hexdigest() != crop_ref["sha256"]
            or type(crop_ref["size_bytes"]) is not int
            or len(raw) != crop_ref["size_bytes"]
        ):
            raise _error("bound numeric crop bytes differ from their authenticated reference")
        cell_id = f"page-{page:04d}-row-{row:03d}-axis-{axis + 1}"
        relative = f"crops/{cell_id}.png"
        crops[relative] = raw
        records.append(
            {
                "axis_id": f"axis-{axis}",
                "axis_ordinal": axis,
                "cell_id": cell_id,
                "crop_path": relative,
                "crop_sha256": hashlib.sha256(raw).hexdigest(),
                "crop_size_bytes": len(raw),
                "page": page,
                "primary_normalized_text": normalized,
                "primary_observation": "VALUE",
                "primary_raw_text": raw_text,
                "primary_sign_evidence": parsed.sign_evidence,
                "primary_value": normalized,
                "recognizer_payload": {"crop_path": relative},
                "row_ordinal": row,
                "source_atom_id": atom_id,
                "source_bbox_raw_pixels": canonical_clone_v1(sample["source_bbox_raw_pixels"]),
                "source_evidence_node_id": numeric_evidence["node_id"],
                "source_graph_node_id": node["node_id"],
                "source_line_index": sample["source_line_index"],
                "visual_punctuation_evidence": None,
            }
        )
    if len(crops) != 8:
        raise _error("ordered graph numeric crop identity is not unique")
    registry = {
        "cells": records,
        "claim_boundary": CLAIM_BOUNDARY,
        "forbidden_recognizer_inputs": list(_FORBIDDEN_RECOGNIZER_INPUTS),
        "format_version": FORMAT_VERSION,
        "geometry_authority": GEOMETRY_AUTHORITY,
        "metrics": {
            "cell_count": 8,
            "page_count": 1,
            "primary_observation_counts": dict(
                sorted(Counter(cell["primary_observation"] for cell in records).items())
            ),
            "row_count": 4,
        },
        "policy": POLICY,
        "recognizer_input_fields": list(_EXPECTED_RECOGNIZER_INPUT_FIELDS),
        "reference_isolation": dict(_REFERENCE_ISOLATION),
        "registry_id": "",
        "semantic_graph": {
            "graph_id": graph["graph_id"],
            "sha256": canonical_json_sha256_v1(graph),
        },
        "semantic_page_binding_sha256": canonical_json_sha256_v1(binding),
        "source_projection_sha256": canonical_json_sha256_v1(source),
    }
    registry["registry_id"] = _registry_id(registry)
    return _validate_registry_shape(registry), crops


def _write_exclusive(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o444,
    )
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise _error(f"numeric registry write made no progress: {path.name}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build_ordered_graph_numeric_cell_registry_v1(
    project_root: Path,
    output_directory: Path,
    source_projection: Any,
    semantic_page_binding: Any,
    semantic_graph: Any,
) -> dict[str, Any]:
    """Build the exact eight-cell reader registry without exposing references."""

    root = _strict_root(project_root)
    if not isinstance(output_directory, Path):
        raise _error("numeric registry output must be one pathlib Path")
    output = output_directory if output_directory.is_absolute() else root / output_directory
    output = output.resolve(strict=False)
    if output == root or not output.is_relative_to(root) or output.exists():
        raise _error("numeric registry output escapes the project or already exists")
    source, binding, graph = _validated_inputs(
        source_projection, semantic_page_binding, semantic_graph
    )
    registry, crops = _build_registry_and_crops(root, source, binding, graph)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        (stage / "crops").mkdir(mode=0o755)
        for relative, raw in crops.items():
            _write_exclusive(stage / relative, raw)
        _write_exclusive(stage / "crop_registry.json", canonical_json_bytes_v1(registry) + b"\n")
        if output.exists():
            raise _error("numeric registry output appeared while staging")
        os.rename(stage, output)
        stage = Path()
        return registry
    finally:
        if stage != Path() and stage.exists():
            shutil.rmtree(stage)


def validate_ordered_graph_numeric_cell_registry_replay_v1(
    value: Any,
    registry_directory: Path,
    project_root: Path,
    source_projection: Any,
    semantic_page_binding: Any,
    semantic_graph: Any,
) -> dict[str, Any]:
    """Rebuild the registry/crops and compare every persisted byte."""

    persisted = _validate_registry_shape(value)
    root = _strict_root(project_root)
    if not isinstance(registry_directory, Path):
        raise _error("numeric registry directory must be one pathlib Path")
    directory = (
        registry_directory if registry_directory.is_absolute() else root / registry_directory
    ).resolve(strict=True)
    if directory.is_symlink() or not directory.is_dir() or not directory.is_relative_to(root):
        raise _error("numeric registry directory is unsafe")
    source, binding, graph = _validated_inputs(
        source_projection, semantic_page_binding, semantic_graph
    )
    rebuilt, crops = _build_registry_and_crops(root, source, binding, graph)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("persisted numeric registry differs from exact graph replay")
    raw_registry = _stable_regular_bytes(directory / "crop_registry.json", "numeric registry")
    try:
        on_disk = json.loads(raw_registry.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("persisted numeric registry is not UTF-8 JSON") from exc
    if raw_registry != canonical_json_bytes_v1(persisted) + b"\n" or not same_typed_json_v1(
        on_disk, persisted
    ):
        raise _error("persisted numeric registry bytes drifted")
    expected_entries = {"crop_registry.json", "crops"}
    if {item.name for item in directory.iterdir()} != expected_entries:
        raise _error("numeric registry directory contains undeclared artifacts")
    crop_directory = directory / "crops"
    if crop_directory.is_symlink() or not crop_directory.is_dir():
        raise _error("numeric registry crop directory is unsafe")
    actual = {
        item.relative_to(directory).as_posix()
        for item in crop_directory.rglob("*")
        if item.is_file()
    }
    if actual != set(crops) or any(item.is_symlink() for item in crop_directory.rglob("*")):
        raise _error("numeric registry crop denominator drifted")
    for relative, expected in crops.items():
        if _stable_regular_bytes(directory / relative, f"numeric registry {relative}") != expected:
            raise _error("persisted numeric crop differs from authenticated graph crop")
    return rebuilt
