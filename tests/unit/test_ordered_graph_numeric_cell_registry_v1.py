from __future__ import annotations

import copy
import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]


def _load():
    name = "ordered_graph_numeric_cell_registry_v1"
    path = _ROOT / "scripts/experiments/ordered_graph_numeric_cell_registry_v1.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


subject = _load()


def _inputs(root: Path) -> tuple[dict, dict, dict]:
    source = {
        "source_local_page_id": "ssv2:page:" + "1" * 64,
        "page_result": {"lines": [{"raw_text": f"{index + 1}.000"} for index in range(8)]},
    }
    source_sha = canonical_json_sha256_v1(source)
    samples = []
    for index in range(8):
        relative = f"authority/crop-{index}.png"
        raw = b"png" + bytes([index])
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        samples.append(
            {
                "crop_ref": {
                    "path": relative,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "size_bytes": len(raw),
                },
                "source_atom": {"source_atom_id": f"atom-{index}"},
                "source_bbox_raw_pixels": [index, index, index + 10, index + 5],
                "source_line_index": index,
            }
        )
    binding = {
        "binding_mode": "ORDINARY_V2_PRIMARY_LINES",
        "page_ordinal": 2,
        "samples": samples,
        "source_local_page_id": source["source_local_page_id"],
        "source_projection_sha256": source_sha,
        "status": "BOUND_TO_EXACT_NONTERMINAL_SOURCE_LINE_AXIS",
    }
    binding_sha = canonical_json_sha256_v1(binding)
    nodes = []
    roles = ("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "TOTAL")
    for index in range(8):
        row, axis = divmod(index, 2)
        raw = f"{index + 1}.000"
        source_ref = {
            "canonical_bbox_mpt": [index, index, index + 1, index + 1],
            "source_atom_ids": [f"atom-{index}"],
            "source_local_page_id": source["source_local_page_id"],
            "source_projection_sha256": source_sha,
        }
        nodes.append(
            {
                "attributes": {
                    "axis_index": axis,
                    "normalized_decimal": str((index + 1) * 1000),
                    "raw_text": raw,
                    "row_ordinal": row,
                    "row_role": roles[row],
                    "state": "OBSERVED_VALUE",
                },
                "kind": "VALUE_POSITION",
                "node_id": f"value-{index}",
                "source_ref": source_ref,
            }
        )
        nodes.append(
            {
                "attributes": {
                    "evidence_role": "VALUE_NUMERIC",
                    "numeric_authority": True,
                    "raw_text_utf8": raw,
                    "source_line_index": index,
                    "text_source": "PPOCRV6_NUMERIC_ONLY",
                },
                "kind": "EVIDENCE",
                "node_id": f"evidence-{index}",
                "source_ref": source_ref,
            }
        )
    graph = {
        "graph_id": "slagv2:graph:" + "2" * 64,
        "nodes": nodes,
        "semantic_page_binding_sha256": binding_sha,
        "source_local_page_id": source["source_local_page_id"],
        "source_projection_sha256": source_sha,
        "status": "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE",
    }
    return source, binding, graph


def test_build_and_replay_exact_reference_blind_registry(tmp_path: Path) -> None:
    source, binding, graph = _inputs(tmp_path)
    output = tmp_path / "numeric/frozen"

    registry = subject.build_ordered_graph_numeric_cell_registry_v1(
        tmp_path, output, source, binding, graph
    )
    replayed = subject.validate_ordered_graph_numeric_cell_registry_replay_v1(
        registry, output, tmp_path, source, binding, graph
    )

    assert replayed == registry
    assert registry["metrics"] == {
        "cell_count": 8,
        "page_count": 1,
        "primary_observation_counts": {"VALUE": 8},
        "row_count": 4,
    }
    assert [item["source_line_index"] for item in registry["cells"]] == list(range(8))
    assert all(
        item["recognizer_payload"] == {"crop_path": item["crop_path"]} for item in registry["cells"]
    )
    assert all(set(item["recognizer_payload"]) == {"crop_path"} for item in registry["cells"])


def test_replay_rejects_crop_byte_drift(tmp_path: Path) -> None:
    source, binding, graph = _inputs(tmp_path)
    output = tmp_path / "numeric/frozen"
    registry = subject.build_ordered_graph_numeric_cell_registry_v1(
        tmp_path, output, source, binding, graph
    )
    (output / registry["cells"][3]["crop_path"]).write_bytes(b"changed")

    with pytest.raises(
        subject.OrderedGraphNumericCellRegistryV1Error,
        match="differs from authenticated graph crop",
    ):
        subject.validate_ordered_graph_numeric_cell_registry_replay_v1(
            registry, output, tmp_path, source, binding, graph
        )


def test_graph_role_or_binding_hash_drift_fails_closed(tmp_path: Path) -> None:
    source, binding, graph = _inputs(tmp_path)
    bad_role = copy.deepcopy(graph)
    bad_role["nodes"][0]["attributes"]["row_role"] = "MEDIUM_TERM"
    with pytest.raises(
        subject.OrderedGraphNumericCellRegistryV1Error,
        match="four-row/two-axis",
    ):
        subject.build_ordered_graph_numeric_cell_registry_v1(
            tmp_path, tmp_path / "bad-role", source, binding, bad_role
        )

    bad_binding = copy.deepcopy(binding)
    bad_binding["source_projection_sha256"] = "f" * 64
    with pytest.raises(
        subject.OrderedGraphNumericCellRegistryV1Error,
        match="lineage drifted",
    ):
        subject.build_ordered_graph_numeric_cell_registry_v1(
            tmp_path, tmp_path / "bad-binding", source, bad_binding, graph
        )


def test_output_is_exclusive(tmp_path: Path) -> None:
    source, binding, graph = _inputs(tmp_path)
    output = tmp_path / "numeric/frozen"
    subject.build_ordered_graph_numeric_cell_registry_v1(tmp_path, output, source, binding, graph)
    with pytest.raises(
        subject.OrderedGraphNumericCellRegistryV1Error,
        match="already exists",
    ):
        subject.build_ordered_graph_numeric_cell_registry_v1(
            tmp_path, output, source, binding, graph
        )
