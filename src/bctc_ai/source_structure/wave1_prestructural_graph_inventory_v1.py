"""Build the compact finalized Wave-1 page pre-structural graph inventory.

The builder replays the exact authenticated V3 survey stream through the
committed V2 source projection, V2 geometry-proposal projection, and page-local
pre-structural graph builder.  The corpus artifact keeps only source/page
bindings, the full graph identity, closed graph counts, atom-disposition
counts, and a payload-free candidate topology.  It deliberately drops graph
nodes' identities, boxes, source citations, evidence nodes, support edges, and
per-atom dispositions.

Every retained TABLE/ROW/CELL_OR_VALUE_POSITION/AXIS_OR_DIMENSION item remains
a pre-structural candidate.  This inventory accepts no statement, table,
financial row/cell, period/unit/scope, hierarchy, value, schema, mapping, or
absence truth.
"""

from __future__ import annotations

import os
import re
import secrets
import stat
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.corpus import wave1_role_b_sentinel as sentinel
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.contracts_v2 import make_page_proposal_set_v2
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.finalized_v3_survey_stream_v1 import (
    FINALIZED_V3_SURVEY_AUTHORITY_V1,
    FinalizedV3SurveyAuthority,
    open_finalized_v3_survey_stream_v1,
)
from bctc_ai.source_structure.page_geometry_proposals_v1 import (
    generate_page_geometry_proposals_v1,
)
from bctc_ai.source_structure.page_prestructural_graph_v1 import (
    build_page_prestructural_graph_v1,
)
from bctc_ai.source_structure.structural_graph_contracts_v1 import (
    AtomGraphDispositionV1,
    GraphEdgeKindV1,
    GraphNodeKindV1,
    GraphNodeStatusV1,
    validate_page_prestructural_graph_v1,
)
from bctc_ai.source_structure.wave1_source_inventory_v1 import (
    validate_wave1_source_inventory_v1,
)

__all__ = [
    "WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_CLAIM_BOUNDARY_V1",
    "WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_FORMAT_VERSION_V1",
    "WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_OUTPUT_RELATIVE_PATH_V1",
    "Wave1PrestructuralGraphInventoryV1Error",
    "build_wave1_prestructural_graph_inventory_v1",
    "publish_wave1_prestructural_graph_inventory_v1",
    "validate_wave1_prestructural_graph_inventory_v1",
]


class Wave1PrestructuralGraphInventoryV1Error(ValueError):
    """The compact graph inventory crossed its candidate-only boundary."""


WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_FORMAT_VERSION_V1 = (
    "BANK_CORPUS_WAVE_1_ROLE_B_PRESTRUCTURAL_GRAPH_INVENTORY_V1"
)
WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_CLAIM_BOUNDARY_V1 = (
    "EXHAUSTIVE_PAGE_LOCAL_PRESTRUCTURAL_GRAPH_IDENTITIES_COUNTS_DISPOSITIONS_"
    "AND_PAYLOAD_FREE_CANDIDATE_TOPOLOGY_ONLY_NO_ACCEPTED_SEMANTIC_CLAIM"
)
WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_OUTPUT_RELATIVE_PATH_V1 = Path(
    "output/development/bank-corpus-survey-v1/wave-1-role-b-prestructural-graph-inventory-v1.json"
)

_SOURCE_INVENTORY_RELATIVE_PATH = Path(
    "output/development/bank-corpus-survey-v1/wave-1-role-b-source-first-inventory-v1.json"
)
_SOURCE_INVENTORY_SHA256 = "c20c9b42ff6f96baf6eff6607e12b27681146d8d968e4e86f0e792bde1429162"
_SOURCE_INVENTORY_SIZE_BYTES = 1_920_845
_SOURCE_INVENTORY_IDENTITY_SHA256 = (
    "63c5988b80cc9893cc20f1b7476d9124880c838d8e4bc6a9d5f4df195550ad84"
)

_FORMAT_STATUS = "COMPLETE_PAGE_LOCAL_PRESTRUCTURAL_CANDIDATE_GRAPH_INVENTORY"
_TOPOLOGY_FORMAT_VERSION = (
    "BANK_CORPUS_WAVE_1_ROLE_B_PAYLOAD_FREE_PRESTRUCTURAL_CANDIDATE_TOPOLOGY_V1"
)
_ROUTES = ("CAUSAL_NATIVE_TEXT", "DOMINANT_RASTER_OCR")
_UPSTREAM_STATUSES = (
    "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
    "OCR_WORD_BOX_READ_COMPLETE",
    "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
    "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
)
_STATUS_ROUTE = {
    "CAUSAL_NATIVE_TEXT_READ_COMPLETE": "CAUSAL_NATIVE_TEXT",
    "OCR_WORD_BOX_READ_COMPLETE": "DOMINANT_RASTER_OCR",
    "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY": "CAUSAL_NATIVE_TEXT",
    "UNRESOLVED_OCR_WORD_BOX_GEOMETRY": "DOMINANT_RASTER_OCR",
}
_NODE_KINDS = tuple(kind.value for kind in GraphNodeKindV1)
_EDGE_KINDS = tuple(kind.value for kind in GraphEdgeKindV1)
_DISPOSITIONS = tuple(kind.value for kind in AtomGraphDispositionV1)
_SOURCE_DISPOSITIONS = (
    "OWNED_BY_SOURCE_OBJECT",
    "RETAINED_UNOWNED",
    "UPSTREAM_TERMINAL_UNRESOLVED",
    "UPSTREAM_QUARANTINED",
)
_EVIDENCE_KIND = GraphNodeKindV1.EVIDENCE.value
_SUPPORT_EDGE_KIND = GraphEdgeKindV1.SUPPORTS.value
_CANDIDATE_KINDS = (
    GraphNodeKindV1.TABLE.value,
    GraphNodeKindV1.ROW.value,
    GraphNodeKindV1.CELL_OR_VALUE_POSITION.value,
    GraphNodeKindV1.AXIS_OR_DIMENSION.value,
)
_EXPECTED_NODE_STATUS = {
    GraphNodeKindV1.DOCUMENT.value: GraphNodeStatusV1.BOUND_SOURCE_CONTEXT.value,
    GraphNodeKindV1.PAGE.value: GraphNodeStatusV1.BOUND_SOURCE_CONTEXT.value,
    GraphNodeKindV1.STATEMENT_BLOCK.value: GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE.value,
    GraphNodeKindV1.TABLE.value: GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE.value,
    GraphNodeKindV1.ROW.value: GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE.value,
    GraphNodeKindV1.CELL_OR_VALUE_POSITION.value: (GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE.value),
    GraphNodeKindV1.AXIS_OR_DIMENSION.value: GraphNodeStatusV1.PRESTRUCTURAL_CANDIDATE.value,
    GraphNodeKindV1.UNRESOLVED_REGION.value: GraphNodeStatusV1.EXPLICIT_UNRESOLVED.value,
}

_SAFETY = {
    "prestructural_candidates_only": True,
    "full_graph_payload_retained": False,
    "graph_node_identities_retained": False,
    "source_text_retained": False,
    "source_geometry_retained": False,
    "source_atom_identities_retained": False,
    "source_proposal_identities_retained": False,
    "evidence_nodes_retained": False,
    "evidence_support_edges_retained": False,
    "per_atom_dispositions_retained": False,
    "payload_free_candidate_topology_retained": True,
    "statement_claimed": False,
    "table_claimed": False,
    "logical_rows_claimed": False,
    "financial_cells_claimed": False,
    "period_axis_claimed": False,
    "unit_axis_claimed": False,
    "scope_claimed": False,
    "hierarchy_claimed": False,
    "value_claimed": False,
    "schema_mapping_claimed": False,
    "absence_claimed": False,
    "source_pdf_opened": False,
    "model_or_ocr_invoked": False,
    "bank_identity_used_for_routing": False,
    "filename_or_path_used_for_routing": False,
    "document_name_used_for_routing": False,
    "note_number_used_for_routing": False,
    "physical_page_used_for_routing": False,
    "period_used_for_routing": False,
    "role_a_used": False,
    "schema_used_for_routing": False,
    "historical_values_used_for_routing": False,
    "compact_source_inventory_used_for_exact_binding_only": True,
    "standalone_validator_is_structural_accounting_only": True,
    "downstream_exact_raw_artifact_sha256_pin_required": True,
}

_TOP_LEVEL_FIELDS = {
    "format_version",
    "claim_boundary",
    "status",
    "authority",
    "documents",
    "pages",
    "corpus_metrics",
    "producer",
    "safety",
    "inventory_identity_sha256",
}
_AUTHORITY_FIELDS = {"finalized_v3", "source_inventory"}
_FINALIZED_AUTHORITY_FIELDS = {
    "aggregate_artifact_sha256",
    "aggregate_size_bytes",
    "aggregate_identity_sha256",
    "control_artifact_sha256",
    "control_size_bytes",
    "control_identity_sha256",
    "sealed_plan_sha256",
    "document_ids",
    "document_count",
    "request_count",
    "referenced_object_count",
}
_SOURCE_INVENTORY_AUTHORITY_FIELDS = {
    "path",
    "sha256",
    "size_bytes",
    "inventory_identity_sha256",
}
_PAGE_FIELDS = {
    "request_ordinal",
    "document_id",
    "physical_page",
    "route",
    "upstream_status",
    "terminal",
    "source_projection_identity",
    "source_projection_sha256",
    "source_proposal_projection_sha256",
    "source_inventory_page_identity_sha256",
    "graph_identity",
    "graph_metrics",
    "candidate_topology",
    "page_inventory_identity_sha256",
}
_GRAPH_METRIC_FIELDS = {"atom_count", "node_counts", "edge_counts", "disposition_counts"}
_TOPOLOGY_FIELDS = {"format_version", "nodes", "edges", "topology_identity"}
_TOPOLOGY_NODE_FIELDS = {
    "ordinal",
    "kind",
    "status",
    "source_atom_count",
    "source_proposal_count",
}
_TOPOLOGY_EDGE_FIELDS = {"ordinal", "kind", "from_node_ordinal", "to_node_ordinal"}
_DOCUMENT_FIELDS = {
    "document_id",
    "page_count",
    "terminal_page_count",
    "atom_count",
    "node_counts",
    "edge_counts",
    "disposition_counts",
    "distinct_candidate_topology_count",
}
_CORPUS_FIELDS = {
    "document_count",
    "page_count",
    "source_accounted_page_count",
    "complete_page_count",
    "terminal_page_count",
    "atom_count",
    "node_counts",
    "edge_counts",
    "disposition_counts",
    "distinct_graph_identity_count",
    "distinct_candidate_topology_count",
}
_PRODUCER_FIELDS = {"git", "implementation_ledger"}
_GIT_FIELDS = {"commit", "dirty"}
_LEDGER_FIELDS = {"records", "sha256"}
_LEDGER_RECORD_FIELDS = {"phase", "kind", "path", "sha256", "size_bytes"}

_IMPLEMENTATION_PATHS = (
    Path("src/bctc_ai/__init__.py"),
    Path("src/bctc_ai/core/__init__.py"),
    Path("src/bctc_ai/core/contracts.py"),
    Path("src/bctc_ai/core/coordinates.py"),
    Path("src/bctc_ai/core/hashing.py"),
    Path("src/bctc_ai/core/text.py"),
    Path("src/bctc_ai/corpus/__init__.py"),
    Path("src/bctc_ai/corpus/wave1_pre_ocr_structure.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_full_reader_v3.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_page_reader.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_sentinel.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_word_box_normalization.py"),
    Path("src/bctc_ai/ocr/__init__.py"),
    Path("src/bctc_ai/ocr/_causal_visibility_core.py"),
    Path("src/bctc_ai/ocr/causal_native_text.py"),
    Path("src/bctc_ai/ocr/causal_native_text_evidence_v1.py"),
    Path("src/bctc_ai/ocr/causal_native_text_evidence_v2.py"),
    Path("src/bctc_ai/ocr/native_text_quality_v2.py"),
    Path("src/bctc_ai/ocr/pdf_text.py"),
    Path("src/bctc_ai/ocr/ppocrv6_page_session.py"),
    Path("src/bctc_ai/rendering/__init__.py"),
    Path("src/bctc_ai/rendering/page_reader.py"),
    Path("src/bctc_ai/source_structure/__init__.py"),
    Path("src/bctc_ai/source_structure/contracts_v1.py"),
    Path("src/bctc_ai/source_structure/contracts_v2.py"),
    Path("src/bctc_ai/source_structure/evidence_projection_v1.py"),
    Path("src/bctc_ai/source_structure/evidence_projection_v2.py"),
    Path("src/bctc_ai/source_structure/finalized_v3_survey_stream_v1.py"),
    Path("src/bctc_ai/source_structure/page_geometry_proposals_v1.py"),
    Path("src/bctc_ai/source_structure/structural_graph_contracts_v1.py"),
    Path("src/bctc_ai/source_structure/page_prestructural_graph_v1.py"),
    Path("src/bctc_ai/source_structure/wave1_source_inventory_v1.py"),
    Path("src/bctc_ai/source_structure/wave1_prestructural_graph_inventory_v1.py"),
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DOCUMENT_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PAGE_ID_RE = re.compile(r"^ssv2:page:[0-9a-f]{64}$")
_GRAPH_ID_RE = re.compile(r"^ssgv1:graph:[0-9a-f]{64}$")
_TOPOLOGY_ID_RE = re.compile(r"^sspgiv1:topology:[0-9a-f]{64}$")


def _error(message: str) -> Wave1PrestructuralGraphInventoryV1Error:
    return Wave1PrestructuralGraphInventoryV1Error(message)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise _error(f"{label} must be a lowercase SHA-256")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be a positive integer")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be a nonnegative integer")
    return value


def _closed_counts(value: Any, vocabulary: Sequence[str], label: str) -> dict[str, int]:
    counts = _exact_dict(value, set(vocabulary), label)
    for key in vocabulary:
        _nonnegative(counts[key], f"{label} {key}")
    return counts


def _authority_payload(authority: FinalizedV3SurveyAuthority) -> dict[str, Any]:
    return {
        "aggregate_artifact_sha256": authority.aggregate_artifact_sha256,
        "aggregate_size_bytes": authority.aggregate_size_bytes,
        "aggregate_identity_sha256": authority.aggregate_identity_sha256,
        "control_artifact_sha256": authority.control_artifact_sha256,
        "control_size_bytes": authority.control_size_bytes,
        "control_identity_sha256": authority.control_identity_sha256,
        "sealed_plan_sha256": authority.sealed_plan_sha256,
        "document_ids": list(authority.document_ids),
        "document_count": authority.document_count,
        "request_count": authority.request_count,
        "referenced_object_count": authority.referenced_object_count,
    }


def _source_inventory_authority() -> dict[str, Any]:
    return {
        "path": _SOURCE_INVENTORY_RELATIVE_PATH.as_posix(),
        "sha256": _SOURCE_INVENTORY_SHA256,
        "size_bytes": _SOURCE_INVENTORY_SIZE_BYTES,
        "inventory_identity_sha256": _SOURCE_INVENTORY_IDENTITY_SHA256,
    }


def _producer_receipt(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    try:
        git = sentinel._git_identity(project_root, require_clean=True)  # noqa: SLF001
        ledger = sentinel._implementation_ledger(  # noqa: SLF001
            project_root,
            git["commit"],
            _IMPLEMENTATION_PATHS,
        )
    except (OSError, sentinel.WaveOneRoleBSentinelError) as exc:
        raise _error(f"prestructural graph producer is not a clean commit: {exc}") from exc
    return {
        "git": canonical_clone_v1(git),
        "implementation_ledger": canonical_clone_v1(ledger),
    }


def _validate_producer(value: Any, *, project_root: Path) -> dict[str, Any]:
    producer = _exact_dict(value, _PRODUCER_FIELDS, "producer")
    git = _exact_dict(producer["git"], _GIT_FIELDS, "producer Git")
    if (
        type(git["commit"]) is not str
        or re.fullmatch(r"[0-9a-f]{40}", git["commit"]) is None
        or git["dirty"] is not False
    ):
        raise _error("producer Git identity drifted")
    ledger = _exact_dict(
        producer["implementation_ledger"],
        _LEDGER_FIELDS,
        "producer implementation ledger",
    )
    records = ledger["records"]
    expected_paths = [path.as_posix() for path in sorted(set(_IMPLEMENTATION_PATHS))]
    if type(records) is not list or len(records) != len(expected_paths):
        raise _error("producer implementation denominator drifted")
    for expected_path, raw_record in zip(expected_paths, records, strict=True):
        record = _exact_dict(raw_record, _LEDGER_RECORD_FIELDS, "implementation record")
        if (
            record["phase"] != "READ"
            or record["kind"] != "IMPLEMENTATION"
            or record["path"] != expected_path
        ):
            raise _error("producer implementation role/path drifted")
        _sha(record["sha256"], "implementation digest")
        _positive(record["size_bytes"], "implementation size")
    if _sha(ledger["sha256"], "implementation ledger identity") != canonical_json_sha256_v1(
        records
    ):
        raise _error("implementation ledger identity drifted")
    try:
        recomputed = sentinel._implementation_ledger(  # noqa: SLF001
            project_root.resolve(),
            git["commit"],
            _IMPLEMENTATION_PATHS,
        )
    except (OSError, sentinel.WaveOneRoleBSentinelError) as exc:
        raise _error("producer implementation cannot be replayed from stored commit") from exc
    if not same_typed_json_v1(ledger, recomputed):
        raise _error("stored producer ledger differs from committed implementation bytes")
    return producer


def _read_stable_nofollow(
    path: Path,
    label: str,
    *,
    expected_mode: int | None = None,
) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or (expected_mode is not None and stat.S_IMODE(before.st_mode) != expected_mode)
        ):
            raise _error(f"{label} is not a canonical regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise _error(f"cannot read {label}: {path}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    try:
        named = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise _error(f"cannot revalidate {label}: {path}") from exc
    token = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        stat.S_IFMT(item.st_mode),
        stat.S_IMODE(item.st_mode),
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if token(before) != token(after) or token(after) != token(named):
        raise _error(f"{label} changed while being read")
    payload = b"".join(chunks)
    if len(payload) != before.st_size:
        raise _error(f"{label} byte count drifted")
    return payload


def _load_source_inventory(project_root: Path) -> dict[str, Any]:
    payload = _read_stable_nofollow(
        project_root.resolve() / _SOURCE_INVENTORY_RELATIVE_PATH,
        "compact source inventory",
        expected_mode=0o444,
    )
    if (
        len(payload) != _SOURCE_INVENTORY_SIZE_BYTES
        or sha256(payload).hexdigest() != _SOURCE_INVENTORY_SHA256
    ):
        raise _error("compact source inventory artifact identity drifted")
    try:
        source = validate_wave1_source_inventory_v1(decode_canonical_json_bytes_v1(payload))
    except ValueError as exc:
        raise _error("compact source inventory contract drifted") from exc
    if source.get("inventory_identity_sha256") != _SOURCE_INVENTORY_IDENTITY_SHA256:
        raise _error("compact source inventory logical identity drifted")
    return source


def _validate_source_inventory_pin(source: Mapping[str, Any]) -> None:
    """Require the supplied logical object to reproduce the sealed raw source pin."""

    try:
        payload = canonical_json_bytes_v1(source)
    except (TypeError, ValueError) as exc:
        raise _error("compact source inventory is not canonical JSON") from exc
    if (
        len(payload) != _SOURCE_INVENTORY_SIZE_BYTES
        or sha256(payload).hexdigest() != _SOURCE_INVENTORY_SHA256
        or source.get("inventory_identity_sha256") != _SOURCE_INVENTORY_IDENTITY_SHA256
        or source.get("inventory_identity_sha256")
        != canonical_json_sha256_v1(
            {key: source[key] for key in source if key != "inventory_identity_sha256"}
        )
    ):
        raise _error("compact source inventory exact raw/logical pin drifted")


def _compact_candidate_topology(graph: Mapping[str, Any]) -> dict[str, Any]:
    node_by_id = {node["node_id"]: node for node in graph["nodes"]}
    retained_nodes = [node for node in graph["nodes"] if node["kind"] != _EVIDENCE_KIND]
    retained_node_ids = {node["node_id"] for node in retained_nodes}
    nodes = [
        {
            "ordinal": node["ordinal"],
            "kind": node["kind"],
            "status": node["status"],
            "source_atom_count": len(node["source_atom_ids"]),
            "source_proposal_count": len(node["source_proposal_ids"]),
        }
        for node in retained_nodes
    ]
    edges = []
    for edge in graph["edges"]:
        if edge["kind"] == _SUPPORT_EDGE_KIND:
            continue
        if (
            edge["from_node_id"] not in retained_node_ids
            or edge["to_node_id"] not in retained_node_ids
        ):
            raise _error("non-support topology edge referenced a dropped evidence node")
        edges.append(
            {
                "ordinal": edge["ordinal"],
                "kind": edge["kind"],
                "from_node_ordinal": node_by_id[edge["from_node_id"]]["ordinal"],
                "to_node_ordinal": node_by_id[edge["to_node_id"]]["ordinal"],
            }
        )
    topology: dict[str, Any] = {
        "format_version": _TOPOLOGY_FORMAT_VERSION,
        "nodes": nodes,
        "edges": edges,
    }
    topology["topology_identity"] = f"sspgiv1:topology:{canonical_json_sha256_v1(topology)}"
    return topology


def _graph_metrics(value: Any, label: str) -> dict[str, Any]:
    metrics = _exact_dict(value, _GRAPH_METRIC_FIELDS, label)
    atom_count = _nonnegative(metrics["atom_count"], f"{label} atom count")
    node_counts = _closed_counts(metrics["node_counts"], _NODE_KINDS, f"{label} node counts")
    _closed_counts(metrics["edge_counts"], _EDGE_KINDS, f"{label} edge counts")
    disposition_counts = _closed_counts(
        metrics["disposition_counts"], _DISPOSITIONS, f"{label} disposition counts"
    )
    if (
        node_counts[_EVIDENCE_KIND] != atom_count
        or sum(disposition_counts.values()) != atom_count
        or node_counts[GraphNodeKindV1.DOCUMENT.value] != 1
        or node_counts[GraphNodeKindV1.PAGE.value] != 1
        or node_counts[GraphNodeKindV1.STATEMENT_BLOCK.value] != 0
        or node_counts[GraphNodeKindV1.UNRESOLVED_REGION.value] != 1
    ):
        raise _error(f"{label} source accounting/closed candidate boundary drifted")
    return metrics


def _validate_topology(value: Any, *, metrics: Mapping[str, Any]) -> dict[str, Any]:
    topology = _exact_dict(value, _TOPOLOGY_FIELDS, "candidate topology")
    if topology["format_version"] != _TOPOLOGY_FORMAT_VERSION:
        raise _error("candidate topology format drifted")
    if type(topology["nodes"]) is not list or type(topology["edges"]) is not list:
        raise _error("candidate topology collections drifted")
    nodes = [
        _exact_dict(item, _TOPOLOGY_NODE_FIELDS, "candidate topology node")
        for item in topology["nodes"]
    ]
    ordinals: list[int] = []
    node_by_ordinal: dict[int, dict[str, Any]] = {}
    for node in nodes:
        ordinal = _positive(node["ordinal"], "candidate topology node ordinal")
        if node["kind"] not in set(_NODE_KINDS) - {_EVIDENCE_KIND}:
            raise _error("candidate topology retained a forbidden node kind")
        if node["status"] != _EXPECTED_NODE_STATUS[node["kind"]]:
            raise _error("candidate topology node status drifted")
        atom_count = _nonnegative(node["source_atom_count"], "topology node source atom count")
        proposal_count = _nonnegative(
            node["source_proposal_count"], "topology node source proposal count"
        )
        if node["kind"] in _CANDIDATE_KINDS and (atom_count == 0 or proposal_count == 0):
            raise _error("candidate topology node lacks source-count evidence")
        if node["kind"] in _CANDIDATE_KINDS and proposal_count != 1:
            raise _error("candidate topology node proposal denominator drifted")
        if node["kind"] in {
            GraphNodeKindV1.DOCUMENT.value,
            GraphNodeKindV1.PAGE.value,
        } and (atom_count != 0 or proposal_count != 0):
            raise _error("topology source-context node carried source payload counts")
        if node["kind"] == GraphNodeKindV1.UNRESOLVED_REGION.value and proposal_count != 0:
            raise _error("unresolved topology node cited proposal counts")
        if ordinal in node_by_ordinal:
            raise _error("candidate topology node ordinal duplicated")
        ordinals.append(ordinal)
        node_by_ordinal[ordinal] = node
    if ordinals != sorted(ordinals) or ordinals != list(range(1, len(nodes) + 1)):
        raise _error("candidate topology node order drifted")
    observed_node_counts = Counter(node["kind"] for node in nodes)
    expected_node_count = sum(
        metrics["node_counts"][kind] for kind in _NODE_KINDS if kind != _EVIDENCE_KIND
    )
    if len(nodes) != expected_node_count or any(
        observed_node_counts[kind] != metrics["node_counts"][kind]
        for kind in _NODE_KINDS
        if kind != _EVIDENCE_KIND
    ):
        raise _error("candidate topology node counts drifted from graph metrics")
    unresolved = next(
        node for node in nodes if node["kind"] == GraphNodeKindV1.UNRESOLVED_REGION.value
    )
    table_atom_count = sum(
        node["source_atom_count"] for node in nodes if node["kind"] == GraphNodeKindV1.TABLE.value
    )
    if table_atom_count + unresolved["source_atom_count"] != metrics["atom_count"]:
        raise _error("candidate topology table/unresolved atom partition drifted")
    if (
        table_atom_count
        != metrics["disposition_counts"][
            AtomGraphDispositionV1.SUPPORTS_PRESTRUCTURAL_CANDIDATE.value
        ]
        or unresolved["source_atom_count"]
        != metrics["disposition_counts"][AtomGraphDispositionV1.RETAINED_UNRESOLVED.value]
        + metrics["disposition_counts"][AtomGraphDispositionV1.UPSTREAM_TERMINAL_UNRESOLVED.value]
        + metrics["disposition_counts"][AtomGraphDispositionV1.UPSTREAM_QUARANTINED.value]
    ):
        raise _error("candidate topology atom disposition partition drifted")
    cited_support_count = sum(
        node["source_atom_count"]
        for node in nodes
        if node["kind"] in _CANDIDATE_KINDS
        or node["kind"] == GraphNodeKindV1.UNRESOLVED_REGION.value
    )
    if cited_support_count != metrics["edge_counts"][_SUPPORT_EDGE_KIND]:
        raise _error("candidate topology source citation/support accounting drifted")

    edges = [
        _exact_dict(item, _TOPOLOGY_EDGE_FIELDS, "candidate topology edge")
        for item in topology["edges"]
    ]
    edge_ordinals: list[int] = []
    logical_edges: set[tuple[str, int, int]] = set()
    observed_edge_counts: Counter[str] = Counter()
    incoming_contains: dict[int, list[int]] = defaultdict(list)
    alignment_pairs: list[tuple[int, int]] = []
    precedes_pairs: list[tuple[int, int]] = []
    for edge in edges:
        ordinal = _positive(edge["ordinal"], "candidate topology edge ordinal")
        kind = edge["kind"]
        if kind not in set(_EDGE_KINDS) - {_SUPPORT_EDGE_KIND}:
            raise _error("candidate topology retained a forbidden edge kind")
        left_ordinal = _positive(edge["from_node_ordinal"], "topology edge source ordinal")
        right_ordinal = _positive(edge["to_node_ordinal"], "topology edge target ordinal")
        if left_ordinal not in node_by_ordinal or right_ordinal not in node_by_ordinal:
            raise _error("candidate topology edge referenced a dropped node")
        left = node_by_ordinal[left_ordinal]
        right = node_by_ordinal[right_ordinal]
        if left_ordinal == right_ordinal:
            raise _error("candidate topology self-edge is forbidden")
        pair = (left["kind"], right["kind"])
        if kind == GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS.value and pair not in {
            (GraphNodeKindV1.DOCUMENT.value, GraphNodeKindV1.PAGE.value),
            (GraphNodeKindV1.PAGE.value, GraphNodeKindV1.UNRESOLVED_REGION.value),
            (GraphNodeKindV1.UNRESOLVED_REGION.value, GraphNodeKindV1.TABLE.value),
            (GraphNodeKindV1.TABLE.value, GraphNodeKindV1.ROW.value),
            (GraphNodeKindV1.ROW.value, GraphNodeKindV1.CELL_OR_VALUE_POSITION.value),
            (GraphNodeKindV1.TABLE.value, GraphNodeKindV1.AXIS_OR_DIMENSION.value),
        }:
            raise _error("candidate topology containment relation drifted")
        if kind == GraphEdgeKindV1.PRESTRUCTURAL_CONTAINS.value:
            incoming_contains[right_ordinal].append(left_ordinal)
        if kind == GraphEdgeKindV1.PRECEDES_IN_AUTHENTICATED_SOURCE_ORDER.value and (
            left["kind"] != right["kind"]
            or left["kind"]
            not in {
                GraphNodeKindV1.ROW.value,
                GraphNodeKindV1.CELL_OR_VALUE_POSITION.value,
            }
        ):
            raise _error("candidate topology source-order relation drifted")
        if kind == GraphEdgeKindV1.PRECEDES_IN_AUTHENTICATED_SOURCE_ORDER.value:
            precedes_pairs.append((left_ordinal, right_ordinal))
        if kind == GraphEdgeKindV1.PRESTRUCTURAL_ALIGNED_TO_AXIS.value and pair != (
            GraphNodeKindV1.CELL_OR_VALUE_POSITION.value,
            GraphNodeKindV1.AXIS_OR_DIMENSION.value,
        ):
            raise _error("candidate topology cell-axis relation drifted")
        if kind == GraphEdgeKindV1.PRESTRUCTURAL_ALIGNED_TO_AXIS.value:
            alignment_pairs.append((left_ordinal, right_ordinal))
        logical = (kind, left_ordinal, right_ordinal)
        if logical in logical_edges:
            raise _error("candidate topology logical edge duplicated")
        logical_edges.add(logical)
        edge_ordinals.append(ordinal)
        observed_edge_counts[kind] += 1
    if edge_ordinals != list(range(1, len(edges) + 1)):
        raise _error("candidate topology edge order drifted")
    if any(
        observed_edge_counts[kind] != metrics["edge_counts"][kind]
        for kind in _EDGE_KINDS
        if kind != _SUPPORT_EDGE_KIND
    ):
        raise _error("candidate topology edge counts drifted from graph metrics")
    expected_parent_kind = {
        GraphNodeKindV1.PAGE.value: GraphNodeKindV1.DOCUMENT.value,
        GraphNodeKindV1.UNRESOLVED_REGION.value: GraphNodeKindV1.PAGE.value,
        GraphNodeKindV1.TABLE.value: GraphNodeKindV1.UNRESOLVED_REGION.value,
        GraphNodeKindV1.ROW.value: GraphNodeKindV1.TABLE.value,
        GraphNodeKindV1.CELL_OR_VALUE_POSITION.value: GraphNodeKindV1.ROW.value,
        GraphNodeKindV1.AXIS_OR_DIMENSION.value: GraphNodeKindV1.TABLE.value,
    }
    parent_by_ordinal: dict[int, int] = {}
    for node in nodes:
        if node["kind"] == GraphNodeKindV1.DOCUMENT.value:
            if incoming_contains.get(node["ordinal"]):
                raise _error("candidate topology document acquired a parent")
            continue
        parents = incoming_contains.get(node["ordinal"], [])
        if (
            len(parents) != 1
            or node_by_ordinal[parents[0]]["kind"] != expected_parent_kind[node["kind"]]
        ):
            raise _error("candidate topology exact containment coverage drifted")
        parent_by_ordinal[node["ordinal"]] = parents[0]
    children_by_parent: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for child_ordinal, parent_ordinal in parent_by_ordinal.items():
        children_by_parent[parent_ordinal].append(node_by_ordinal[child_ordinal])
    for table in (node for node in nodes if node["kind"] == GraphNodeKindV1.TABLE.value):
        children = children_by_parent[table["ordinal"]]
        rows = [child for child in children if child["kind"] == GraphNodeKindV1.ROW.value]
        axes = [
            child for child in children if child["kind"] == GraphNodeKindV1.AXIS_OR_DIMENSION.value
        ]
        if sum(row["source_atom_count"] for row in rows) != table["source_atom_count"]:
            raise _error("candidate topology table/row source partition drifted")
        if sum(axis["source_atom_count"] for axis in axes) > table["source_atom_count"]:
            raise _error("candidate topology table/axis source accounting drifted")
    for row in (node for node in nodes if node["kind"] == GraphNodeKindV1.ROW.value):
        cells = [
            child
            for child in children_by_parent[row["ordinal"]]
            if child["kind"] == GraphNodeKindV1.CELL_OR_VALUE_POSITION.value
        ]
        if sum(cell["source_atom_count"] for cell in cells) > row["source_atom_count"]:
            raise _error("candidate topology row/cell source accounting drifted")
    alignment_count_by_axis = Counter(axis for _cell, axis in alignment_pairs)
    alignment_count_by_cell = Counter(cell for cell, _axis in alignment_pairs)
    for cell_ordinal, axis_ordinal in alignment_pairs:
        row_ordinal = parent_by_ordinal[cell_ordinal]
        cell_table_ordinal = parent_by_ordinal[row_ordinal]
        axis_table_ordinal = parent_by_ordinal[axis_ordinal]
        if cell_table_ordinal != axis_table_ordinal:
            raise _error("candidate topology cell-axis table context drifted")
    for axis in (node for node in nodes if node["kind"] == GraphNodeKindV1.AXIS_OR_DIMENSION.value):
        if alignment_count_by_axis[axis["ordinal"]] != axis["source_atom_count"]:
            raise _error("candidate topology axis/alignment source accounting drifted")
    if any(count > 1 for count in alignment_count_by_cell.values()):
        raise _error("candidate topology cell aligned to multiple axes")
    observed_precedes = set(precedes_pairs)
    expected_precedes: set[tuple[int, int]] = set()
    siblings: dict[tuple[str, int], list[int]] = defaultdict(list)
    for node in nodes:
        if node["kind"] in {
            GraphNodeKindV1.ROW.value,
            GraphNodeKindV1.CELL_OR_VALUE_POSITION.value,
        }:
            siblings[(node["kind"], parent_by_ordinal[node["ordinal"]])].append(node["ordinal"])
    for sibling_ordinals in siblings.values():
        ordered = sorted(sibling_ordinals)
        expected_precedes.update(zip(ordered, ordered[1:], strict=False))
    if observed_precedes != expected_precedes or any(
        parent_by_ordinal[left] != parent_by_ordinal[right] for left, right in precedes_pairs
    ):
        raise _error("candidate topology exact sibling source-order chain drifted")
    identity = topology["topology_identity"]
    expected_identity = "sspgiv1:topology:" + canonical_json_sha256_v1(
        {key: topology[key] for key in topology if key != "topology_identity"}
    )
    if (
        type(identity) is not str
        or _TOPOLOGY_ID_RE.fullmatch(identity) is None
        or identity != expected_identity
    ):
        raise _error("candidate topology identity drifted")
    return topology


def _page_inventory(
    *,
    page_record: Mapping[str, Any],
    source_page: Mapping[str, Any],
    projection: Mapping[str, Any],
    proposal_projection: Mapping[str, Any],
    graph: Mapping[str, Any],
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "request_ordinal": page_record["request_ordinal"],
        "document_id": page_record["document_id"],
        "physical_page": page_record["physical_page"],
        "route": projection["route"],
        "upstream_status": projection["upstream_status"],
        "terminal": projection["terminal"],
        "source_projection_identity": projection["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(projection),
        "source_proposal_projection_sha256": canonical_json_sha256_v1(proposal_projection),
        "source_inventory_page_identity_sha256": source_page["page_inventory_identity_sha256"],
        "graph_identity": graph["graph_identity"],
        "graph_metrics": canonical_clone_v1(graph["metrics"]),
        "candidate_topology": _compact_candidate_topology(graph),
    }
    item["page_inventory_identity_sha256"] = canonical_json_sha256_v1(item)
    return item


def _sum_closed_counts(
    pages: Sequence[Mapping[str, Any]],
    metric: str,
    vocabulary: Sequence[str],
) -> dict[str, int]:
    return {key: sum(page["graph_metrics"][metric][key] for page in pages) for key in vocabulary}


def _document_rollup(document_id: str, pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "page_count": len(pages),
        "terminal_page_count": sum(page["terminal"] for page in pages),
        "atom_count": sum(page["graph_metrics"]["atom_count"] for page in pages),
        "node_counts": _sum_closed_counts(pages, "node_counts", _NODE_KINDS),
        "edge_counts": _sum_closed_counts(pages, "edge_counts", _EDGE_KINDS),
        "disposition_counts": _sum_closed_counts(pages, "disposition_counts", _DISPOSITIONS),
        "distinct_candidate_topology_count": len(
            {page["candidate_topology"]["topology_identity"] for page in pages}
        ),
    }


def _rollup_documents(
    document_ids: Sequence[str], pages: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for page in pages:
        grouped[page["document_id"]].append(page)
    return [_document_rollup(document_id, grouped[document_id]) for document_id in document_ids]


def _rollup_corpus(
    authority: Mapping[str, Any], pages: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "document_count": authority["document_count"],
        "page_count": len(pages),
        "source_accounted_page_count": len(pages),
        "complete_page_count": sum(not page["terminal"] for page in pages),
        "terminal_page_count": sum(page["terminal"] for page in pages),
        "atom_count": sum(page["graph_metrics"]["atom_count"] for page in pages),
        "node_counts": _sum_closed_counts(pages, "node_counts", _NODE_KINDS),
        "edge_counts": _sum_closed_counts(pages, "edge_counts", _EDGE_KINDS),
        "disposition_counts": _sum_closed_counts(pages, "disposition_counts", _DISPOSITIONS),
        "distinct_graph_identity_count": len({page["graph_identity"] for page in pages}),
        "distinct_candidate_topology_count": len(
            {page["candidate_topology"]["topology_identity"] for page in pages}
        ),
    }


def _validate_finalized_authority(value: Any) -> dict[str, Any]:
    authority = _exact_dict(value, _FINALIZED_AUTHORITY_FIELDS, "finalized V3 authority")
    for field in (
        "aggregate_artifact_sha256",
        "aggregate_identity_sha256",
        "control_artifact_sha256",
        "control_identity_sha256",
        "sealed_plan_sha256",
    ):
        _sha(authority[field], f"finalized V3 authority {field}")
    for field in (
        "aggregate_size_bytes",
        "control_size_bytes",
        "document_count",
        "request_count",
        "referenced_object_count",
    ):
        _positive(authority[field], f"finalized V3 authority {field}")
    document_ids = authority["document_ids"]
    if (
        type(document_ids) is not list
        or any(
            type(document_id) is not str or _DOCUMENT_ID_RE.fullmatch(document_id) is None
            for document_id in document_ids
        )
        or document_ids != sorted(set(document_ids))
        or len(document_ids) != authority["document_count"]
    ):
        raise _error("finalized V3 document identities drifted")
    if not same_typed_json_v1(authority, _authority_payload(FINALIZED_V3_SURVEY_AUTHORITY_V1)):
        raise _error("finalized V3 authority differs from the exact pin")
    return authority


def _validate_authority(value: Any, *, source_inventory: Mapping[str, Any]) -> dict[str, Any]:
    authority = _exact_dict(value, _AUTHORITY_FIELDS, "inventory authority")
    finalized = _validate_finalized_authority(authority["finalized_v3"])
    source = _exact_dict(
        authority["source_inventory"],
        _SOURCE_INVENTORY_AUTHORITY_FIELDS,
        "compact source inventory authority",
    )
    if source != _source_inventory_authority():
        raise _error("compact source inventory authority pin drifted")
    if not same_typed_json_v1(source_inventory["authority"], finalized):
        raise _error("compact source inventory and finalized V3 authority diverged")
    return authority


def _validate_page(
    value: Any,
    *,
    expected_ordinal: int,
    source_page: Mapping[str, Any],
) -> dict[str, Any]:
    page = _exact_dict(value, _PAGE_FIELDS, "prestructural graph inventory page")
    if page["request_ordinal"] != expected_ordinal:
        raise _error("prestructural graph request ordinal drifted")
    if (
        type(page["document_id"]) is not str
        or _DOCUMENT_ID_RE.fullmatch(page["document_id"]) is None
        or page["document_id"] != source_page["document_id"]
    ):
        raise _error("prestructural graph page document identity drifted")
    _positive(page["physical_page"], "prestructural graph physical page")
    if (
        page["route"] not in _ROUTES
        or page["upstream_status"] not in _UPSTREAM_STATUSES
        or _STATUS_ROUTE[page["upstream_status"]] != page["route"]
    ):
        raise _error("prestructural graph page route/status drifted")
    if type(page["terminal"]) is not bool or page["terminal"] != page["upstream_status"].startswith(
        "UNRESOLVED_"
    ):
        raise _error("prestructural graph page terminal state drifted")
    if (
        type(page["source_projection_identity"]) is not str
        or _PAGE_ID_RE.fullmatch(page["source_projection_identity"]) is None
    ):
        raise _error("prestructural graph source projection identity drifted")
    for field in (
        "source_projection_sha256",
        "source_proposal_projection_sha256",
        "source_inventory_page_identity_sha256",
        "page_inventory_identity_sha256",
    ):
        _sha(page[field], f"prestructural graph page {field}")
    if (
        type(page["graph_identity"]) is not str
        or _GRAPH_ID_RE.fullmatch(page["graph_identity"]) is None
    ):
        raise _error("prestructural graph identity drifted")
    metrics = _graph_metrics(page["graph_metrics"], "prestructural graph page metrics")
    _validate_topology(page["candidate_topology"], metrics=metrics)
    source_metrics = source_page["metrics"]
    source_dispositions = _closed_counts(
        source_metrics["disposition_counts"],
        _SOURCE_DISPOSITIONS,
        "compact source page disposition counts",
    )
    graph_dispositions = metrics["disposition_counts"]
    if (
        metrics["atom_count"] != source_metrics["atom_count"]
        or graph_dispositions[AtomGraphDispositionV1.UPSTREAM_QUARANTINED.value]
        != source_dispositions["UPSTREAM_QUARANTINED"]
        or graph_dispositions[AtomGraphDispositionV1.UPSTREAM_TERMINAL_UNRESOLVED.value]
        != source_dispositions["UPSTREAM_TERMINAL_UNRESOLVED"]
        or graph_dispositions[AtomGraphDispositionV1.SUPPORTS_PRESTRUCTURAL_CANDIDATE.value]
        + graph_dispositions[AtomGraphDispositionV1.RETAINED_UNRESOLVED.value]
        != source_dispositions["OWNED_BY_SOURCE_OBJECT"] + source_dispositions["RETAINED_UNOWNED"]
        or metrics["node_counts"][GraphNodeKindV1.TABLE.value]
        > source_metrics["proposal_kind_counts"]["TABULAR_GEOMETRY_CANDIDATE"]
    ):
        raise _error("prestructural graph/source atom-disposition accounting drifted")
    if page["terminal"] and any(metrics["node_counts"][kind] for kind in _CANDIDATE_KINDS):
        raise _error("terminal page promoted prestructural candidates")
    if (
        page["physical_page"] != source_page["physical_page"]
        or page["route"] != source_page["route"]
        or page["upstream_status"] != source_page["status"]
        or page["terminal"] != source_page["terminal"]
        or page["source_projection_identity"] != source_page["projection_identity"]
        or page["source_projection_sha256"] != source_page["projection_sha256"]
        or page["source_proposal_projection_sha256"]
        != source_page["v2_geometry_proposal_projection_sha256"]
        or page["source_inventory_page_identity_sha256"]
        != source_page["page_inventory_identity_sha256"]
    ):
        raise _error("prestructural graph page differs from compact source inventory")
    expected_page_identity = canonical_json_sha256_v1(
        {key: page[key] for key in page if key != "page_inventory_identity_sha256"}
    )
    if page["page_inventory_identity_sha256"] != expected_page_identity:
        raise _error("prestructural graph page inventory identity drifted")
    return page


def _validate_document(value: Any, *, expected_id: str) -> dict[str, Any]:
    document = _exact_dict(value, _DOCUMENT_FIELDS, "prestructural graph document rollup")
    if document["document_id"] != expected_id:
        raise _error("prestructural graph document order/identity drifted")
    for field in (
        "page_count",
        "terminal_page_count",
        "atom_count",
        "distinct_candidate_topology_count",
    ):
        _nonnegative(document[field], f"prestructural graph document {field}")
    _closed_counts(document["node_counts"], _NODE_KINDS, "document node counts")
    _closed_counts(document["edge_counts"], _EDGE_KINDS, "document edge counts")
    dispositions = _closed_counts(
        document["disposition_counts"], _DISPOSITIONS, "document disposition counts"
    )
    if sum(dispositions.values()) != document["atom_count"]:
        raise _error("prestructural graph document atom accounting drifted")
    return document


def validate_wave1_prestructural_graph_inventory_v1(
    value: Any,
    *,
    project_root: Path,
    source_inventory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate exact authority plus all compact page/document/corpus sums."""

    project_root = project_root.resolve()
    source = (
        _load_source_inventory(project_root)
        if source_inventory is None
        else validate_wave1_source_inventory_v1(source_inventory)
    )
    _validate_source_inventory_pin(source)
    inventory = _exact_dict(value, _TOP_LEVEL_FIELDS, "Wave-1 prestructural graph inventory")
    if (
        inventory["format_version"] != WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_FORMAT_VERSION_V1
        or inventory["claim_boundary"] != WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_CLAIM_BOUNDARY_V1
        or inventory["status"] != _FORMAT_STATUS
        or inventory["safety"] != _SAFETY
    ):
        raise _error("prestructural graph inventory header/safety drifted")
    authority = _validate_authority(inventory["authority"], source_inventory=source)
    _validate_producer(inventory["producer"], project_root=project_root)
    pages_raw = inventory["pages"]
    source_pages = source["pages"]
    if type(pages_raw) is not list or len(pages_raw) != len(source_pages):
        raise _error("prestructural graph page denominator drifted")
    pages = [
        _validate_page(page, expected_ordinal=index, source_page=source_page)
        for index, (page, source_page) in enumerate(
            zip(pages_raw, source_pages, strict=True), start=1
        )
    ]
    if (
        len(pages) != authority["finalized_v3"]["request_count"]
        or {page["document_id"] for page in pages} != set(authority["finalized_v3"]["document_ids"])
        or len({page["source_projection_identity"] for page in pages}) != len(pages)
        or len({page["source_projection_sha256"] for page in pages}) != len(pages)
        or len({page["graph_identity"] for page in pages}) != len(pages)
        or len({page["page_inventory_identity_sha256"] for page in pages}) != len(pages)
        or len({(page["document_id"], page["physical_page"]) for page in pages}) != len(pages)
    ):
        raise _error("prestructural graph page coverage/identity drifted")

    document_ids = authority["finalized_v3"]["document_ids"]
    documents_raw = inventory["documents"]
    if type(documents_raw) is not list or len(documents_raw) != len(document_ids):
        raise _error("prestructural graph document denominator drifted")
    documents = [
        _validate_document(document, expected_id=document_id)
        for document_id, document in zip(document_ids, documents_raw, strict=True)
    ]
    expected_documents = _rollup_documents(document_ids, pages)
    if not same_typed_json_v1(documents, expected_documents):
        raise _error("prestructural graph per-document accounting drifted")

    corpus = _exact_dict(inventory["corpus_metrics"], _CORPUS_FIELDS, "corpus metrics")
    for field in (
        "document_count",
        "page_count",
        "source_accounted_page_count",
        "complete_page_count",
        "terminal_page_count",
        "atom_count",
        "distinct_graph_identity_count",
        "distinct_candidate_topology_count",
    ):
        _nonnegative(corpus[field], f"prestructural graph corpus {field}")
    _closed_counts(corpus["node_counts"], _NODE_KINDS, "corpus node counts")
    _closed_counts(corpus["edge_counts"], _EDGE_KINDS, "corpus edge counts")
    dispositions = _closed_counts(
        corpus["disposition_counts"], _DISPOSITIONS, "corpus disposition counts"
    )
    expected_corpus = _rollup_corpus(authority["finalized_v3"], pages)
    if (
        not same_typed_json_v1(corpus, expected_corpus)
        or corpus["document_count"] != authority["finalized_v3"]["document_count"]
        or corpus["page_count"] != authority["finalized_v3"]["request_count"]
        or corpus["page_count"] != source["corpus_metrics"]["page_count"]
        or corpus["terminal_page_count"] != source["corpus_metrics"]["terminal_page_count"]
        or corpus["source_accounted_page_count"] != corpus["page_count"]
        or sum(dispositions.values()) != corpus["atom_count"]
    ):
        raise _error("prestructural graph corpus authority/accounting drifted")
    identity = _sha(inventory["inventory_identity_sha256"], "inventory identity")
    if identity != canonical_json_sha256_v1(
        {key: inventory[key] for key in inventory if key != "inventory_identity_sha256"}
    ):
        raise _error("prestructural graph inventory logical identity drifted")
    return canonical_clone_v1(inventory)


def _build_pages(
    project_root: Path,
    *,
    source_inventory: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], FinalizedV3SurveyAuthority]:
    source_pages = source_inventory["pages"]
    pages: list[dict[str, Any]] = []
    with open_finalized_v3_survey_stream_v1(project_root) as stream:
        authority = stream.authority
        for delivered, authenticated_page in enumerate(stream, start=1):
            if delivered > len(source_pages):
                raise _error("finalized V3 stream exceeded compact source denominator")
            record = authenticated_page.page_record
            source_page = source_pages[delivered - 1]
            projection = project_authenticated_page_v2(
                page_record=record,
                page_result=authenticated_page.page_result,
            )
            proposal_v1 = generate_page_geometry_proposals_v1(projection)
            proposal_v2 = make_page_proposal_set_v2(
                projection,
                proposal_set_v1=proposal_v1,
            )
            graph = build_page_prestructural_graph_v1(projection, proposal_v2)
            graph = validate_page_prestructural_graph_v1(
                graph,
                projection=projection,
                proposal_projection=proposal_v2,
            )
            source_sha256 = projection["source_locator"]["source_sha256"]
            if (
                record["request_ordinal"] != delivered
                or record["document_id"] != source_page["document_id"]
                or record["physical_page"] != source_page["physical_page"]
                or record["document_id"] != f"sha256:{source_sha256}"
                or projection["source_local_page_id"] != source_page["projection_identity"]
                or canonical_json_sha256_v1(projection) != source_page["projection_sha256"]
                or canonical_json_sha256_v1(proposal_v2)
                != source_page["v2_geometry_proposal_projection_sha256"]
                or projection["route"] != source_page["route"]
                or projection["upstream_status"] != source_page["status"]
                or projection["terminal"] != source_page["terminal"]
            ):
                raise _error("finalized graph input differs from compact source inventory")
            pages.append(
                _page_inventory(
                    page_record=record,
                    source_page=source_page,
                    projection=projection,
                    proposal_projection=proposal_v2,
                    graph=graph,
                )
            )
    if len(pages) != len(source_pages) or len(pages) != authority.request_count:
        raise _error("finalized V3 stream was not consumed at its exact denominator")
    observed_document_order: list[str] = []
    closed_documents: set[str] = set()
    for page in pages:
        document_id = page["document_id"]
        if not observed_document_order or document_id != observed_document_order[-1]:
            if document_id in closed_documents:
                raise _error("finalized V3 document pages are not contiguous")
            if observed_document_order:
                closed_documents.add(observed_document_order[-1])
            observed_document_order.append(document_id)
    if observed_document_order != list(authority.document_ids):
        raise _error("finalized V3 document coverage/order drifted")
    return pages, authority


def build_wave1_prestructural_graph_inventory_v1(project_root: Path) -> dict[str, Any]:
    """Build and validate the compact candidate graph inventory without publishing."""

    project_root = project_root.resolve()
    producer_before = _producer_receipt(project_root)
    source_before = _load_source_inventory(project_root)
    pages, authority = _build_pages(project_root, source_inventory=source_before)
    source_after = _load_source_inventory(project_root)
    producer_after = _producer_receipt(project_root)
    if not same_typed_json_v1(source_before, source_after):
        raise _error("compact source inventory changed during graph construction")
    if not same_typed_json_v1(producer_before, producer_after):
        raise _error("prestructural graph producer changed during construction")
    authority_payload = _authority_payload(authority)
    inventory: dict[str, Any] = {
        "format_version": WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_FORMAT_VERSION_V1,
        "claim_boundary": WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_CLAIM_BOUNDARY_V1,
        "status": _FORMAT_STATUS,
        "authority": {
            "finalized_v3": authority_payload,
            "source_inventory": _source_inventory_authority(),
        },
        "documents": _rollup_documents(authority.document_ids, pages),
        "pages": pages,
        "corpus_metrics": _rollup_corpus(authority_payload, pages),
        "producer": producer_before,
        "safety": canonical_clone_v1(_SAFETY),
    }
    inventory["inventory_identity_sha256"] = canonical_json_sha256_v1(inventory)
    return validate_wave1_prestructural_graph_inventory_v1(
        inventory,
        project_root=project_root,
        source_inventory=source_before,
    )


def _open_output_directory(project_root: Path) -> tuple[Path, int]:
    relative_parent = WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_OUTPUT_RELATIVE_PATH_V1.parent
    descriptor = os.open(
        project_root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        for part in relative_parent.parts:
            child = os.open(
                part,
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        identity = os.fstat(descriptor)
        if not stat.S_ISDIR(identity.st_mode):
            raise _error("prestructural graph output parent is not a directory")
    except Exception:
        os.close(descriptor)
        raise
    return project_root / relative_parent, descriptor


def _require_destination_absent(project_root: Path) -> None:
    _parent, directory_fd = _open_output_directory(project_root)
    try:
        try:
            os.stat(
                WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_OUTPUT_RELATIVE_PATH_V1.name,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return
        raise _error("prestructural graph inventory destination already exists")
    finally:
        os.close(directory_fd)


def _read_regular_at(directory_fd: int, filename: str) -> tuple[bytes, os.stat_result]:
    descriptor = os.open(
        filename,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=directory_fd,
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error("published prestructural graph inventory is not regular")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        named = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
    finally:
        os.close(descriptor)
    token = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        stat.S_IFMT(item.st_mode),
        stat.S_IMODE(item.st_mode),
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if token(before) != token(after) or token(after) != token(named):
        raise _error("published prestructural graph inventory changed during validation")
    return b"".join(chunks), after


def _publish_canonical_exclusive(project_root: Path, payload: bytes) -> Path:
    if not payload.endswith(b"\n") or payload.endswith(b"\n\n"):
        raise _error("prestructural graph publication is not canonical newline JSON")
    try:
        decode_canonical_json_bytes_v1(payload)
    except ValueError as exc:
        raise _error("prestructural graph publication bytes are not canonical JSON") from exc
    parent, directory_fd = _open_output_directory(project_root)
    filename = WAVE1_PRESTRUCTURAL_GRAPH_INVENTORY_OUTPUT_RELATIVE_PATH_V1.name
    temporary_pattern = re.compile(rf"^\.{re.escape(filename)}\.[0-9a-f]{{32}}\.tmp$")
    temporary_name = f".{filename}.{secrets.token_hex(16)}.tmp"
    descriptor = -1
    owned_identity: tuple[int, int] | None = None
    final_linked = False
    publication_committed = False
    try:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        if any(temporary_pattern.fullmatch(name) for name in os.listdir(directory_fd)):
            raise _error("prestructural graph publication temporary already exists")
        try:
            os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise _error("prestructural graph inventory destination already exists")
        try:
            descriptor = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        except FileExistsError as exc:
            raise _error("prestructural graph temporary publication collided") from exc
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise _error("owned prestructural graph publication identity drifted")
        owned_identity = (opened.st_dev, opened.st_ino)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise _error("prestructural graph publication write made no progress")
            offset += written
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o444)
        os.fsync(descriptor)
        final_open = os.fstat(descriptor)
        if (
            not stat.S_ISREG(final_open.st_mode)
            or stat.S_IMODE(final_open.st_mode) != 0o444
            or final_open.st_nlink != 1
            or final_open.st_size != len(payload)
        ):
            raise _error("prestructural graph sealed temporary identity drifted")
        try:
            os.link(
                temporary_name,
                filename,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise _error("prestructural graph publication lost its exclusive race") from exc
        final_linked = True
        linked = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
        temporary = os.stat(temporary_name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            (linked.st_dev, linked.st_ino) != owned_identity
            or (temporary.st_dev, temporary.st_ino) != owned_identity
            or stat.S_IMODE(linked.st_mode) != 0o444
            or linked.st_nlink != 2
            or temporary.st_nlink != 2
            or linked.st_size != len(payload)
        ):
            raise _error("linked prestructural graph publication identity drifted")
        os.fsync(directory_fd)
        publication_committed = True
        os.unlink(temporary_name, dir_fd=directory_fd)
        os.fsync(directory_fd)
        published, identity = _read_regular_at(directory_fd, filename)
        if (
            published != payload
            or stat.S_IMODE(identity.st_mode) != 0o444
            or identity.st_nlink != 1
            or any(temporary_pattern.fullmatch(name) for name in os.listdir(directory_fd))
        ):
            raise _error("published prestructural graph inventory bytes/topology drifted")
    except OSError as exc:
        raise _error("prestructural graph inventory publication failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if final_linked and not publication_committed and owned_identity is not None:
            try:
                observed_final = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                observed_final = None
            if (
                observed_final is not None
                and (observed_final.st_dev, observed_final.st_ino) == owned_identity
            ):
                os.unlink(filename, dir_fd=directory_fd)
                os.fsync(directory_fd)
        if owned_identity is not None:
            try:
                observed = os.stat(temporary_name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                observed = None
            if observed is not None and (observed.st_dev, observed.st_ino) == owned_identity:
                os.unlink(temporary_name, dir_fd=directory_fd)
                os.fsync(directory_fd)
        os.close(directory_fd)
    return parent / filename


def publish_wave1_prestructural_graph_inventory_v1(
    project_root: Path,
) -> tuple[Path, str, int, str]:
    """Build and exclusively publish canonical bytes to the one final name."""

    project_root = project_root.resolve()
    _require_destination_absent(project_root)
    inventory = build_wave1_prestructural_graph_inventory_v1(project_root)
    source = _load_source_inventory(project_root)
    validate_wave1_prestructural_graph_inventory_v1(
        inventory,
        project_root=project_root,
        source_inventory=source,
    )
    if not same_typed_json_v1(_producer_receipt(project_root), inventory["producer"]):
        raise _error("prestructural graph producer changed before publication")
    payload = canonical_json_bytes_v1(inventory)
    path = _publish_canonical_exclusive(project_root, payload)
    return (
        path,
        sha256(payload).hexdigest(),
        len(payload),
        inventory["inventory_identity_sha256"],
    )
