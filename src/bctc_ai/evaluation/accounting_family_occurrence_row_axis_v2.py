"""Opt-in occurrence-aware projection over the sealed family row axis V1.

Topology discovery deliberately keeps one hit per semantic role.  A stacked
accounting table may nevertheless repeat the same child role under several
visible local parents.  This add-only adapter expands only occurrences that
the shared topology engine can replay inside the already selected region.  It
then delegates all row/lane geometry to the sealed V1 primitive.

The adapter also closes one narrow numeric evidence gap: a PP-OCR token whose
surface parses as ``DASH_ZERO`` is retained only after the committed
selected-snapshot/exact-page-render pixel bridge proves a visible dash glyph.
Detector-hole dash proposals remain owned by row-axis V1 and are not
reclassified here.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import accounting_family_coextensive_parent_total_v1 as total_v1
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_v1
from bctc_ai.evaluation import accounting_family_topology_candidates_v2 as candidates_v2
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import authenticated_semantic_region_snapshot_v1 as snapshot_v1
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as render_v1
from bctc_ai.evaluation import family_first_authenticated_snapshot_cell_dash_v1 as dash_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "POLICY_FORMAT_VERSION",
    "AccountingFamilyOccurrenceRowAxisV2Error",
    "build_accounting_family_occurrence_row_axis_v2",
    "validate_accounting_family_occurrence_row_axis_replay_v2",
]


FORMAT_VERSION = "ACCOUNTING_FAMILY_OCCURRENCE_ROW_AXIS_V2"
POLICY_FORMAT_VERSION = "ACCOUNTING_FAMILY_OCCURRENCE_ROW_AXIS_POLICY_V1"
CLAIM_BOUNDARY = (
    "EXACT_SELECTED_TOPOLOGY_REGION_CONTEXT_BOUND_ROLE_OCCURRENCE_EXPANSION_"
    "SEALED_V1_ROW_GEOMETRY_AUTHENTICATED_EXISTING_CELL_PIXEL_DASH_GATE_AND_"
    "EXACT_PRECEDING_SCOPE_SUBTOTAL_SOURCE_OWNERSHIP_"
    "PROPOSAL_ONLY_NO_ACCOUNTING_PERIOD_UNIT_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "accounting_authority": False,
    "bank_file_page_period_scope_used_for_routing": False,
    "detector_hole_dash_authority_changed": False,
    "existing_dash_text_alone_means_zero": False,
    "mapping_authority": False,
    "occurrences_may_cross_selected_topology_region": False,
    "preceding_numeric_source_ambiguous_ownership_can_resolve": False,
    "preceding_scope_subtotal_may_be_reused_by_next_structural_group": False,
    "repeated_roles_may_be_silently_collapsed": False,
    "schema_authority": False,
    "sealed_row_axis_v1_bytes_changed": False,
    "visible_existing_dash_requires_authenticated_exact_cell_pixels": True,
}
_POLICY_FIELDS = {
    "format_version",
    "require_authenticated_existing_dash_pixels",
    "retain_all_context_bound_role_occurrences",
}
_RESULT_FIELDS = {
    "authenticated_existing_dash_evidence",
    "claim_boundary",
    "coextensive_structural_numeric_evidence",
    "dependency_content_refs",
    "family_id",
    "format_version",
    "occurrence_axis_id",
    "role_occurrences",
    "row_axis",
    "safety",
    "status",
    "topology_candidates_id",
    "topology_scan_id",
    "unresolved_reasons",
}
_OCCURRENCE_FIELDS = {
    "has_bound_value_row",
    "label_match",
    "occurrence_id",
    "role",
    "role_kind",
    "scope_owner_occurrence_id",
    "scope_owner_role",
}
_DASH_PROJECTION_FIELDS = {
    "dash_evidence",
    "occurrence_id",
    "page_sequence",
    "role",
    "row_kind",
    "sample_id",
    "status",
}
_COEXTENSIVE_STRUCTURAL_NUMERIC_FIELDS = {
    "owner_component_occurrence_ids",
    "owner_occurrence_id",
    "owner_role",
    "projected_occurrence_id",
    "projected_role",
    "source_record",
    "source_sample_ids",
    "status",
}
_MAX_ROLE_OCCURRENCES = 4_096
_MAX_EXISTING_DASH_CELLS = 16_384
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEPENDENCIES = {
    "coextensive_parent_total_projector": {
        "path": "src/bctc_ai/evaluation/accounting_family_coextensive_parent_total_v1.py",
        "sha256": "31a7e42e85c6b16689a1148a1ccb3d02cee18f85139b6f800bed3aa309b48e68",
        "size_bytes": 14_722,
    },
    "exact_page_render_validator": {
        "path": "src/bctc_ai/evaluation/family_first_authenticated_page_region_v1.py",
        "sha256": "5759b50dbe35aa5fe5a302f42f3e96229ec5764d3ae50f4c45a460533acd1def",
        "size_bytes": 24_228,
    },
    "existing_cell_dash_bridge": {
        "path": "src/bctc_ai/evaluation/family_first_authenticated_snapshot_cell_dash_v1.py",
        "sha256": "4d868880e2e997a997b2c4549301ed97c10641d76c8c5030de8c29dc86b195cb",
        "size_bytes": 18_259,
    },
    "row_axis_v1": {
        "path": "src/bctc_ai/evaluation/accounting_family_row_axis_v1.py",
        "sha256": "333c6b811d5d72229b5a0adbaa500265959426babc08304af9f1a9eb4b8d000a",
        "size_bytes": 79_925,
    },
    "selected_snapshot_validator": {
        "path": "src/bctc_ai/evaluation/authenticated_semantic_region_snapshot_v1.py",
        "sha256": "139085696c138d7992b285968789918aef583bfa0bc5149d5a5a9956f5d7504d",
        "size_bytes": 24_406,
    },
    "topology_v1": {
        "path": "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        "sha256": "60da089b5df5a6ee9f53dac8569bc4a9484bf5816721fb992f8d4d09a43bc236",
        "size_bytes": 68_515,
    },
    "topology_candidates_v2": {
        "path": "src/bctc_ai/evaluation/accounting_family_topology_candidates_v2.py",
        "sha256": "609f914fa16baf85c11c44d994e1e8b554f5700b7b46971b225322406e68aad7",
        "size_bytes": 32_335,
    },
}


class AccountingFamilyOccurrenceRowAxisV2Error(ValueError):
    """The occurrence boundary, V1 row projection, dash proof, or replay drifted."""


def _error(message: str) -> AccountingFamilyOccurrenceRowAxisV2Error:
    return AccountingFamilyOccurrenceRowAxisV2Error(message)


@dataclass(frozen=True, slots=True, eq=False)
class _PreparedAuthenticatedSnapshotProjectionV2:
    """Process-local canonical snapshot projection for repeated V4 consumers."""

    document_ordinal: int
    page_axis: tuple[int, ...]
    prepared_context_sha256: str
    projection_content_sha256: str
    projection_id: str
    selected_snapshot_content_sha256: str
    snapshot_id: str
    _projection_bytes: bytes = field(repr=False, compare=False)
    _selected_snapshot_bytes: bytes = field(repr=False, compare=False)
    seal: object = field(repr=False, compare=False)


_PREPARED_SNAPSHOT_SEAL = object()


def _policy(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _POLICY_FIELDS
        or value["format_version"] != POLICY_FORMAT_VERSION
        or value["require_authenticated_existing_dash_pixels"] is not True
        or value["retain_all_context_bound_role_occurrences"] is not True
    ):
        raise _error("occurrence row-axis policy drifted")
    return canonical_clone_v1(value)


def _stable_dependency_ref(expected: Mapping[str, Any]) -> dict[str, Any]:
    path = _PROJECT_ROOT / expected["path"]
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error("occurrence row-axis dependency is not one regular nofollow file")
        chunks = []
        while chunk := os.read(descriptor, 1 << 20):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise _error("occurrence row-axis dependency cannot be read stable nofollow") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    payload = b"".join(chunks)
    observed = {
        "path": expected["path"],
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    if (
        identity(before) != identity(after)
        or len(payload) != before.st_size
        or not same_typed_json_v1(observed, expected)
    ):
        raise _error("occurrence row-axis dependency content reference drifted")
    return observed


def _dependency_refs() -> dict[str, dict[str, Any]]:
    return {
        name: _stable_dependency_ref(expected) for name, expected in sorted(_DEPENDENCIES.items())
    }


def _selected_scan_region(
    topology_scan: Mapping[str, Any], topology_region: Mapping[str, Any]
) -> dict[str, Any]:
    exact = [
        region for region in topology_scan["regions"] if same_typed_json_v1(region, topology_region)
    ]
    if len(exact) == 1:
        return canonical_clone_v1(exact[0])
    raise _error("occurrence region is not one exact selected V1 topology candidate")


def _match_signature(match: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        match.get("role"),
        match.get("page_sequence"),
        match.get("document_line_ordinal"),
        match.get("end_document_line_ordinal"),
        match.get("source_line_index"),
        match.get("end_source_line_index"),
    )


def _expanded_matches(
    pages: Sequence[Mapping[str, Any]],
    family_spec: Mapping[str, Any],
    topology_scan: Mapping[str, Any],
    topology_region: Mapping[str, Any],
    effective_region: Mapping[str, Any] | None,
    topology_candidates: Mapping[str, Any] | None,
    prepared_topology_binding: (
        candidates_v2._PreparedAccountingFamilyTopologyCandidateBindingV2 | None
    ),
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], str | None]:
    if topology_candidates is None:
        if prepared_topology_binding is not None:
            raise _error("prepared candidate binding requires its V2 topology envelope")
        selected = _selected_scan_region(topology_scan, topology_region)
        try:
            expected_effective = (
                total_v1.project_accounting_family_coextensive_parent_total_region_v1(
                    family_spec, topology_scan, selected
                )
            )
            occurrences = topology_v1.enumerate_accounting_family_role_occurrences_v1(
                row_v1._topology_pages(pages), family_spec, selected
            )
        except (
            total_v1.AccountingFamilyCoextensiveParentTotalV1Error,
            topology_v1.AccountingFamilyTopologyV1Error,
        ) as exc:
            raise _error("legacy topology occurrence or coextensive TOTAL replay failed") from exc
        topology_candidates_id = None
    else:
        try:
            if prepared_topology_binding is None:
                binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
                    row_v1._topology_pages(pages),
                    family_spec,
                    topology_candidates,
                    topology_region,
                )
            else:
                binding = candidates_v2._validate_prepared_accounting_family_topology_candidate_binding_v2(
                    prepared_topology_binding,
                    document_pages=row_v1._topology_pages(pages),
                    family_spec=family_spec,
                    topology_candidates=topology_candidates,
                    topology_region=topology_region,
                )
        except candidates_v2.AccountingFamilyTopologyCandidatesV2Error as exc:
            raise _error("pre-pruning topology candidate replay failed") from exc
        if (
            topology_candidates.get("input_binding", {}).get("legacy_topology_scan_id")
            != topology_scan["scan_id"]
        ):
            raise _error("topology candidate envelope differs from the legacy scan binding")
        selected = binding["topology_region"]
        expected_effective = binding["effective_topology_region"]
        occurrences = binding["role_occurrences"]
        topology_candidates_id = binding["topology_candidates_id"]
    if effective_region is not None and not same_typed_json_v1(
        effective_region, expected_effective
    ):
        raise _error("effective occurrence region differs from the closed generic projector")
    by_signature = {_match_signature(item): canonical_clone_v1(item) for item in occurrences}
    # An upstream generic projector may add a role that is exactly
    # coextensive with the selected parent (for example a declared TOTAL).
    # It cannot broaden the region.  Preserve that already-adjudicated match
    # while every ordinary repeated occurrence still comes from the topology
    for match in expected_effective["child_matches"]:
        by_signature.setdefault(_match_signature(match), canonical_clone_v1(match))
    candidates = sorted(
        by_signature.values(),
        key=lambda item: (
            item["document_line_ordinal"],
            item["end_document_line_ordinal"],
            item["preferred_ordinal"],
            item["role"],
        ),
    )
    # A compound matcher can end on the same exact leaf as a narrower
    # contextual matcher (``group label`` + ``Bằng VND`` versus the exact
    # contextual ``Bằng VND`` line).  Prefer the contextual narrower twin.
    # A genuinely flattened one-line compound remains because it has no such
    # contextual challenger.
    result = []
    for candidate in candidates:
        superseded = any(
            other is not candidate
            and other["role"] == candidate["role"]
            and other["page_sequence"] == candidate["page_sequence"]
            and other["end_document_line_ordinal"] == candidate["end_document_line_ordinal"]
            and other.get("matched_within_role") is not None
            and candidate.get("matched_within_role") is None
            and other["document_line_ordinal"] >= candidate["document_line_ordinal"]
            for other in candidates
        )
        if not superseded:
            result.append(candidate)
    ordinals: dict[str, int] = {}
    for match in result:
        ordinal = ordinals.get(match["role"], 0)
        match["role_occurrence_ordinal"] = ordinal
        ordinals[match["role"]] = ordinal + 1
    return result, selected, expected_effective, topology_candidates_id


def _decorate_scopes(
    matches: list[dict[str, Any]], region: Mapping[str, Any]
) -> list[dict[str, Any]]:
    root_scope_id = "aforav2:root:" + canonical_json_sha256_v1(
        {
            "end": region["cluster_end_document_line_ordinal_exclusive"],
            "parent_match": region.get("parent_match"),
            "start": region["cluster_start_document_line_ordinal"],
        }
    )
    decorated: list[dict[str, Any]] = []
    for match in matches:
        occurrence_material = {
            "document_line_ordinal": match["document_line_ordinal"],
            "end_document_line_ordinal": match["end_document_line_ordinal"],
            "page_sequence": match["page_sequence"],
            "role": match["role"],
            "role_occurrence_ordinal": match["role_occurrence_ordinal"],
        }
        occurrence_id = "aforav2:occurrence:" + canonical_json_sha256_v1(occurrence_material)
        decorated.append({**canonical_clone_v1(match), "occurrence_id": occurrence_id})
    for match in decorated:
        within_role = match.get("matched_within_role")
        parents = [
            candidate
            for candidate in decorated
            if candidate["role"] == within_role
            and candidate["document_line_ordinal"] <= match["document_line_ordinal"]
            and candidate["occurrence_id"] != match["occurrence_id"]
        ]
        owner = max(
            parents,
            key=lambda item: (
                item["document_line_ordinal"],
                item["end_document_line_ordinal"],
            ),
            default=None,
        )
        if within_role is not None and owner is None:
            raise _error("context-bound role occurrence lost its nearest structural parent")
        match["scope_owner_occurrence_id"] = (
            owner["occurrence_id"] if owner is not None else root_scope_id
        )
        match["scope_owner_role"] = owner["role"] if owner is not None else None
    return decorated


def _expanded_region(
    effective_region: Mapping[str, Any], matches: list[dict[str, Any]]
) -> dict[str, Any]:
    result = canonical_clone_v1(effective_region)
    result["child_matches"] = canonical_clone_v1(matches)
    result["observed_roles"] = list(dict.fromkeys(match["role"] for match in matches))
    return result


def _local_page_sequence(selected_pages: Sequence[int], physical_page: int) -> int:
    local = 0
    prior = None
    for page in selected_pages:
        local = local + 1 if prior is not None and page == prior + 1 else 1
        if page == physical_page:
            return local
        prior = page
    raise _error("DASH cell page is absent from the authenticated selected snapshot")


def _projection_from_canonical_snapshot_v2(
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Mirror the pinned snapshot projection over an already canonical value."""

    dimensions = {item["physical_page"]: item for item in snapshot["selected_page_dimensions"]}
    region_pages = []
    page_bindings = []
    line_bindings = []
    for page in snapshot["joined_pages"]:
        page_sequence = page["page_sequence"]
        dimension = dimensions[page_sequence]
        region_lines = []
        for line in page["lines"]:
            numeric = line["numeric_recognition"]
            region_lines.append(
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "source_line_index": line["line_ordinal"],
                    "source_text": numeric["raw_prediction"],
                    "vietocr_text": line["vietocr_text"],
                }
            )
            line_bindings.append(
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "crop_ref": canonical_clone_v1(line["crop_ref"]),
                    "page_sequence": page_sequence,
                    "ppocrv6_reader_score": numeric["reader_score"],
                    "ppocrv6_surface": numeric["raw_prediction"],
                    "sample_id": line["sample_id"],
                    "source_line_index": line["line_ordinal"],
                    "vietocr_transformer_surface": line["vietocr_text"],
                }
            )
        region_pages.append(
            {
                "lines": region_lines,
                "page_height": dimension["pixel_height"],
                "page_sequence": page_sequence,
                "page_width": dimension["pixel_width"],
            }
        )
        page_bindings.append(
            {
                "line_count": len(region_lines),
                "page_height": dimension["pixel_height"],
                "page_sequence": page_sequence,
                "page_width": dimension["pixel_width"],
                "render_ref": {
                    "sha256": dimension["render_sha256"],
                    "size_bytes": dimension["render_size_bytes"],
                },
            }
        )
    packet = snapshot["document_packet"]
    material = {
        "authority": canonical_clone_v1(snapshot_v1._AUTHORITY),  # noqa: SLF001
        "claim_boundary": snapshot_v1.CLAIM_BOUNDARY,
        "format_version": snapshot_v1.FORMAT_VERSION,
        "line_bindings": line_bindings,
        "metrics": {
            "line_count": len(line_bindings),
            "page_count": len(region_pages),
            "zero_line_page_count": sum(not page["lines"] for page in region_pages),
        },
        "page_bindings": page_bindings,
        "region_pages": region_pages,
        "source_binding": {
            "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
            "document_id": packet["document_id"],
            "document_line_count": packet["line_count"],
            "document_ordinal": packet["document_ordinal"],
            "document_packet_id": packet["packet_id"],
            "document_page_count": packet["page_count"],
            "manifest_id": snapshot["manifest_id"],
            "query_selection_id": snapshot["query_selection_id"],
            "selected_pages": [page["page_sequence"] for page in region_pages],
            "snapshot_id": snapshot["snapshot_id"],
        },
        "state": "CALLER_AUTHENTICATED_SELECTED_SNAPSHOT_PROJECTED_FOR_SEMANTIC_GRAPH",
    }
    return {
        **material,
        "projection_id": "asrsv1:projection:" + canonical_json_sha256_v1(material),
    }


def _prepared_snapshot_context_material(
    *,
    document_ordinal: int,
    page_axis: tuple[int, ...],
    projection_content_sha256: str,
    projection_id: str,
    selected_snapshot_content_sha256: str,
    snapshot_id: str,
) -> dict[str, Any]:
    return {
        "document_ordinal": document_ordinal,
        "page_axis": list(page_axis),
        "projection_content_sha256": projection_content_sha256,
        "projection_id": projection_id,
        "selected_snapshot_content_sha256": selected_snapshot_content_sha256,
        "snapshot_id": snapshot_id,
    }


def _prepare_authenticated_snapshot_projection_v2(
    selected_snapshot: Mapping[str, Any],
) -> _PreparedAuthenticatedSnapshotProjectionV2:
    """Canonicalize and project one caller-authenticated snapshot once."""

    try:
        typed = snapshot_v1._canonical_snapshot(selected_snapshot)  # noqa: SLF001
        projection = _projection_from_canonical_snapshot_v2(typed)
    except (ValueError, RuntimeError) as exc:
        raise _error("caller-authenticated selected snapshot contract drifted") from exc
    source = projection["source_binding"]
    page_axis = tuple(source["selected_pages"])
    projection_bytes = canonical_json_bytes_v1(projection)
    selected_snapshot_bytes = canonical_json_bytes_v1(typed)
    projection_content_sha256 = hashlib.sha256(projection_bytes).hexdigest()
    selected_snapshot_content_sha256 = hashlib.sha256(selected_snapshot_bytes).hexdigest()
    material = _prepared_snapshot_context_material(
        document_ordinal=source["document_ordinal"],
        page_axis=page_axis,
        projection_content_sha256=projection_content_sha256,
        projection_id=projection["projection_id"],
        selected_snapshot_content_sha256=selected_snapshot_content_sha256,
        snapshot_id=source["snapshot_id"],
    )
    return _PreparedAuthenticatedSnapshotProjectionV2(
        document_ordinal=source["document_ordinal"],
        page_axis=page_axis,
        prepared_context_sha256=canonical_json_sha256_v1(material),
        projection_content_sha256=projection_content_sha256,
        projection_id=projection["projection_id"],
        selected_snapshot_content_sha256=selected_snapshot_content_sha256,
        snapshot_id=source["snapshot_id"],
        _projection_bytes=projection_bytes,
        _selected_snapshot_bytes=selected_snapshot_bytes,
        seal=_PREPARED_SNAPSHOT_SEAL,
    )


def _prepared_authenticated_snapshot_projection_authority_v2(
    value: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Open and content-check one sealed same-turn snapshot projection."""

    if (
        type(value) is not _PreparedAuthenticatedSnapshotProjectionV2
        or value.seal is not _PREPARED_SNAPSHOT_SEAL
    ):
        raise _error("prepared selected-snapshot projection identity drifted")
    selected_snapshot_bytes = value._selected_snapshot_bytes  # noqa: SLF001
    projection_bytes = value._projection_bytes  # noqa: SLF001
    try:
        selected_snapshot = json.loads(selected_snapshot_bytes.decode("utf-8"))
        projection = json.loads(projection_bytes.decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("prepared selected-snapshot projection content drifted") from exc
    if (
        type(selected_snapshot_bytes) is not bytes
        or type(projection_bytes) is not bytes
        or type(selected_snapshot) is not dict
        or type(projection) is not dict
        or hashlib.sha256(selected_snapshot_bytes).hexdigest()
        != value.selected_snapshot_content_sha256
        or hashlib.sha256(projection_bytes).hexdigest() != value.projection_content_sha256
    ):
        raise _error("prepared selected-snapshot projection content drifted")
    snapshot_material = canonical_clone_v1(selected_snapshot)
    snapshot_id = snapshot_material.pop("snapshot_id", None)
    projection_material = canonical_clone_v1(projection)
    projection_id = projection_material.pop("projection_id", None)
    source = projection.get("source_binding")
    if (
        type(source) is not dict
        or snapshot_id != "ffdesv1:selected:" + canonical_json_sha256_v1(snapshot_material)
        or projection_id != "asrsv1:projection:" + canonical_json_sha256_v1(projection_material)
        or value.snapshot_id != snapshot_id
        or value.projection_id != projection_id
        or value.document_ordinal != source.get("document_ordinal")
        or value.snapshot_id != source.get("snapshot_id")
        or value.page_axis != tuple(source.get("selected_pages", ()))
    ):
        raise _error("prepared selected-snapshot projection content drifted")
    material = _prepared_snapshot_context_material(
        document_ordinal=value.document_ordinal,
        page_axis=value.page_axis,
        projection_content_sha256=value.projection_content_sha256,
        projection_id=value.projection_id,
        selected_snapshot_content_sha256=value.selected_snapshot_content_sha256,
        snapshot_id=value.snapshot_id,
    )
    if value.prepared_context_sha256 != canonical_json_sha256_v1(material):
        raise _error("prepared selected-snapshot projection binding drifted")
    return selected_snapshot, projection


def _use_prepared_authenticated_snapshot_projection_v2(
    value: Any,
    selected_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind current snapshot content to one immutable same-turn projection."""

    if (
        type(value) is not _PreparedAuthenticatedSnapshotProjectionV2
        or value.seal is not _PREPARED_SNAPSHOT_SEAL
    ):
        raise _error("prepared selected snapshot differs from the occurrence source")
    projection_bytes = value._projection_bytes  # noqa: SLF001
    try:
        projection = json.loads(projection_bytes.decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("prepared selected-snapshot projection binding drifted") from exc
    source = projection.get("source_binding") if type(projection) is dict else None
    material = _prepared_snapshot_context_material(
        document_ordinal=value.document_ordinal,
        page_axis=value.page_axis,
        projection_content_sha256=value.projection_content_sha256,
        projection_id=value.projection_id,
        selected_snapshot_content_sha256=value.selected_snapshot_content_sha256,
        snapshot_id=value.snapshot_id,
    )
    if (
        type(source) is not dict
        or type(projection_bytes) is not bytes
        or canonical_json_sha256_v1(selected_snapshot) != value.selected_snapshot_content_sha256
        or hashlib.sha256(projection_bytes).hexdigest() != value.projection_content_sha256
        or selected_snapshot.get("snapshot_id") != value.snapshot_id
        or projection.get("projection_id") != value.projection_id
        or source.get("document_ordinal") != value.document_ordinal
        or source.get("snapshot_id") != value.snapshot_id
        or tuple(source.get("selected_pages", ())) != value.page_axis
        or value.prepared_context_sha256 != canonical_json_sha256_v1(material)
    ):
        raise _error("prepared selected-snapshot projection binding drifted")
    return projection


def _validate_snapshot_and_renders(
    pages: Sequence[Mapping[str, Any]],
    selected_snapshot: Mapping[str, Any] | None,
    render_snapshots: Sequence[Mapping[str, Any]],
    *,
    prepared_snapshot: _PreparedAuthenticatedSnapshotProjectionV2 | None = None,
) -> None:
    if selected_snapshot is None:
        if render_snapshots or prepared_snapshot is not None:
            raise _error("authenticated renders require their selected-snapshot binding")
        return
    if prepared_snapshot is None:
        try:
            projection = snapshot_v1.build_authenticated_semantic_region_snapshot_v1(
                selected_snapshot
            )
            snapshot_v1.validate_authenticated_semantic_region_snapshot_replay_v1(
                projection, selected_snapshot
            )
        except (ValueError, RuntimeError) as exc:
            raise _error("caller-authenticated selected snapshot contract drifted") from exc
    else:
        projection = _use_prepared_authenticated_snapshot_projection_v2(
            prepared_snapshot,
            selected_snapshot,
        )
    source = projection["source_binding"]
    snapshot_pages = {page["page_sequence"]: page for page in selected_snapshot["joined_pages"]}
    if set(snapshot_pages) != {page["page_sequence"] for page in pages}:
        raise _error("occurrence row pages differ from the selected snapshot page axis")
    for page in pages:
        snapshot_page = snapshot_pages[page["page_sequence"]]
        if not same_typed_json_v1(page["lines"], snapshot_page["lines"]):
            raise _error("occurrence row lines differ from the selected snapshot")
        if page["page_width"] is not None and page["page_width"] != snapshot_page["page_width"]:
            raise _error("occurrence row page width differs from the selected snapshot")
    bindings = {item["page_sequence"]: item for item in projection["page_bindings"]}
    seen: set[int] = set()
    for render in render_snapshots:
        try:
            record, _payload = render_v1._validated_render_snapshot(render)
        except (ValueError, RuntimeError) as exc:
            raise _error("caller-authenticated exact page render contract drifted") from exc
        page = record["physical_page"]
        binding = bindings.get(page)
        if (
            page in seen
            or record["document_ordinal"] != source["document_ordinal"]
            or binding is None
            or record["render_ref"]["sha256"] != binding["render_ref"]["sha256"]
            or record["render_ref"]["size_bytes"] != binding["render_ref"]["size_bytes"]
            or record["render_ref"]["pixel_width"] != binding["page_width"]
            or record["render_ref"]["pixel_height"] != binding["page_height"]
        ):
            raise _error("exact page render differs from its selected-snapshot binding")
        seen.add(page)


def _existing_dash_evidence(
    *,
    value: Mapping[str, Any],
    row_kind: str,
    role: str | None,
    occurrence_id: str | None,
    selected_snapshot: Mapping[str, Any] | None,
    render_by_page: Mapping[int, Mapping[str, Any]],
) -> tuple[dict[str, Any], bool]:
    page = value["page_sequence"]
    base = {
        "occurrence_id": occurrence_id,
        "page_sequence": page,
        "role": role,
        "row_kind": row_kind,
        "sample_id": value["sample_id"],
    }
    if selected_snapshot is None or page not in render_by_page:
        return {
            **base,
            "dash_evidence": None,
            "status": "UNRESOLVED_AUTHENTICATED_EXACT_CELL_RENDER_NOT_AVAILABLE",
        }, False
    try:
        dimensions = {
            item["physical_page"]: item for item in selected_snapshot["selected_page_dimensions"]
        }
        selected_pages = sorted(dimensions)
        dimension = dimensions[page]
        render = render_by_page[page]
        binding = {
            "binding_kind": dash_v1.BINDING_KIND,
            "document_ordinal": selected_snapshot["document_packet"]["document_ordinal"],
            "local_to_physical_page": {
                "local_page_sequence": _local_page_sequence(selected_pages, page),
                "physical_page": page,
            },
            "raw_pixel_bbox": canonical_clone_v1(value["bbox"]),
            "render_dimensions": {
                "pixel_height": dimension["pixel_height"],
                "pixel_width": dimension["pixel_width"],
            },
            "render_id": render["render_id"],
            "sample_id": value["sample_id"],
            "snapshot_id": selected_snapshot["snapshot_id"],
            "source_line_index": value["line_ordinal"],
        }
        evidence = dash_v1.build_family_first_authenticated_snapshot_cell_dash_v1(
            selected_snapshot=selected_snapshot,
            render_snapshot=render,
            cell_binding=binding,
        )
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        return {
            **base,
            "dash_evidence": None,
            "status": f"UNRESOLVED_AUTHENTICATED_EXACT_CELL_DASH_BRIDGE:{type(exc).__name__}",
        }, False
    proved = (
        evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
        and evidence["normalized_value"] == 0
    )
    return {
        **base,
        "dash_evidence": evidence,
        "status": (
            "AUTHENTICATED_VISIBLE_EXISTING_CELL_DASH_ZERO"
            if proved
            else "UNRESOLVED_EXISTING_CELL_PIXELS_ARE_NOT_ONE_VISIBLE_DASH"
        ),
    }, proved


def _regenerate_v1_axis(axis: Mapping[str, Any]) -> dict[str, Any]:
    material = canonical_clone_v1(axis)
    material.pop("row_axis_id", None)
    material["metrics"] = row_v1._result_metrics(
        material["rows"], material["trailing_value_rows"], material["visible_dash_rescues"]
    )
    material["status"] = (
        "UNRESOLVED_TOPOLOGY"
        if not material["rows"]
        else "ROW_AXIS_PROPOSAL_WITH_UNRESOLVED_CELLS"
        if any(
            row["status"]
            not in {
                "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS",
                "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES",
                "VISIBLE_VALUE_LANES_BOUND",
            }
            for row in material["rows"]
        )
        else "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    )
    return row_v1._validate_result(
        {
            **material,
            "row_axis_id": "afrav1:axis:" + canonical_json_sha256_v1(material),
        }
    )


def _authenticate_existing_dashes(
    axis: Mapping[str, Any],
    *,
    selected_snapshot: Mapping[str, Any] | None,
    render_snapshots: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    completed = canonical_clone_v1(axis)
    render_by_page: dict[int, Mapping[str, Any]] = {}
    for render in render_snapshots:
        page = render.get("physical_page")
        if type(page) is not int or page <= 0 or page in render_by_page:
            raise _error("authenticated render page axis repeats or drifted")
        render_by_page[page] = render
    detector_rescue_ids = {item["region_id"] for item in completed["visible_dash_rescues"]}
    projections: list[dict[str, Any]] = []
    reasons: list[str] = []
    for row in completed["rows"]:
        occurrence_id = row["label_match"].get("occurrence_id")
        retained = []
        removed_existing_dash = False
        for value in row["values"]:
            is_existing_dash = (
                value["parsed_token"]["classification"] == "DASH_ZERO"
                and value["sample_id"] not in detector_rescue_ids
            )
            if not is_existing_dash:
                retained.append(value)
                continue
            projection, proved = _existing_dash_evidence(
                value=value,
                row_kind="ROLE_ROW",
                role=row["role"],
                occurrence_id=occurrence_id,
                selected_snapshot=selected_snapshot,
                render_by_page=render_by_page,
            )
            projections.append(projection)
            if proved:
                retained.append(value)
            else:
                removed_existing_dash = True
                if value["column_ordinal"] not in row["missing_column_ordinals"]:
                    row["missing_column_ordinals"].append(value["column_ordinal"])
                reasons.append(projection["status"] + ":" + value["sample_id"])
        row["values"] = sorted(retained, key=lambda item: item["column_ordinal"])
        row["missing_column_ordinals"].sort()
        if removed_existing_dash:
            row["status"] = (
                "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL"
                if not row["values"]
                else "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
                if row["missing_column_ordinals"]
                else "VISIBLE_VALUE_LANES_BOUND"
            )
    for trailing in completed["trailing_value_rows"]:
        retained = []
        removed_existing_dash = False
        for value in trailing["values"]:
            if value["parsed_token"]["classification"] != "DASH_ZERO":
                retained.append(value)
                continue
            projection, proved = _existing_dash_evidence(
                value=value,
                row_kind="TRAILING_VALUE_ROW",
                role=None,
                occurrence_id=None,
                selected_snapshot=selected_snapshot,
                render_by_page=render_by_page,
            )
            projections.append(projection)
            if proved:
                retained.append(value)
            else:
                removed_existing_dash = True
                if value["column_ordinal"] not in trailing["missing_column_ordinals"]:
                    trailing["missing_column_ordinals"].append(value["column_ordinal"])
                reasons.append(projection["status"] + ":" + value["sample_id"])
        trailing["values"] = sorted(retained, key=lambda item: item["column_ordinal"])
        trailing["missing_column_ordinals"].sort()
        if removed_existing_dash:
            trailing["status"] = (
                "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
                if not trailing["missing_column_ordinals"]
                else "PARTIAL_TRAILING_VALUE_ROW_REQUIRES_PIXEL_RESCUE"
            )
    return _regenerate_v1_axis(completed), projections, list(dict.fromkeys(reasons))


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["topology_scan_id"]) is not str
        or not value["topology_scan_id"].startswith("aftv1:scan:")
        or (
            value["topology_candidates_id"] is not None
            and (
                type(value["topology_candidates_id"]) is not str
                or not value["topology_candidates_id"].startswith("aftcv2:result:")
            )
        )
        or type(value["role_occurrences"]) is not list
        or not value["role_occurrences"]
        or len(value["role_occurrences"]) > _MAX_ROLE_OCCURRENCES
        or type(value["authenticated_existing_dash_evidence"]) is not list
        or len(value["authenticated_existing_dash_evidence"]) > _MAX_EXISTING_DASH_CELLS
        or type(value["coextensive_structural_numeric_evidence"]) is not list
        or len(value["coextensive_structural_numeric_evidence"]) > _MAX_ROLE_OCCURRENCES
        or not same_typed_json_v1(value["dependency_content_refs"], _dependency_refs())
        or type(value["unresolved_reasons"]) is not list
        or any(type(reason) is not str or not reason for reason in value["unresolved_reasons"])
        or value["status"]
        not in {
            "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY",
            "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE",
        }
    ):
        raise _error("occurrence row-axis result contract drifted")
    try:
        axis = row_v1._validate_result(value["row_axis"])
    except row_v1.AccountingFamilyRowAxisV1Error as exc:
        raise _error("occurrence row-axis retained an invalid sealed V1 projection") from exc
    if (
        axis["family_id"] != value["family_id"]
        or axis["topology_scan_id"] != value["topology_scan_id"]
    ):
        raise _error("occurrence row-axis family or topology identity differs")
    occurrence_ids = [item.get("occurrence_id") for item in value["role_occurrences"]]
    if (
        any(
            type(item) is not dict or set(item) != _OCCURRENCE_FIELDS
            for item in value["role_occurrences"]
        )
        or any(type(item) is not str or not item for item in occurrence_ids)
        or len(occurrence_ids) != len(set(occurrence_ids))
    ):
        raise _error("role occurrence identity axis repeats or drifted")
    occurrence_by_id = {item["occurrence_id"]: item for item in value["role_occurrences"]}
    row_occurrence_ids = {row["label_match"].get("occurrence_id") for row in axis["rows"]}
    row_by_occurrence = {row["label_match"].get("occurrence_id"): row for row in axis["rows"]}
    root_scope_ids = {
        item["scope_owner_occurrence_id"]
        for item in value["role_occurrences"]
        if item["scope_owner_role"] is None
    }
    if len(root_scope_ids) != 1 or any(
        type(item["has_bound_value_row"]) is not bool
        or type(item["label_match"]) is not dict
        or item["label_match"].get("occurrence_id") != item["occurrence_id"]
        or item["label_match"].get("role") != item["role"]
        or item["label_match"].get("role_kind") != item["role_kind"]
        or item["label_match"].get("scope_owner_occurrence_id") != item["scope_owner_occurrence_id"]
        or item["label_match"].get("scope_owner_role") != item["scope_owner_role"]
        or item["has_bound_value_row"] is not (item["occurrence_id"] in row_occurrence_ids)
        or (
            item["scope_owner_role"] is not None
            and (
                item["scope_owner_occurrence_id"] not in occurrence_by_id
                or occurrence_by_id[item["scope_owner_occurrence_id"]]["role"]
                != item["scope_owner_role"]
            )
        )
        for item in value["role_occurrences"]
    ):
        raise _error("role occurrence nearest-parent scope axis drifted")
    retained_sample_ids = {
        source_value.get("sample_id")
        for row in [*axis["rows"], *axis["trailing_value_rows"]]
        for source_value in row.get("values", [])
    }
    coextensive_projected_ids: list[str] = []
    coextensive_sample_ids: list[str] = []
    for item in value["coextensive_structural_numeric_evidence"]:
        if type(item) is not dict:
            raise _error("coextensive structural numeric evidence axis drifted")
        source_record = item.get("source_record")
        source_values = source_record.get("values") if type(source_record) is dict else None
        projected = occurrence_by_id.get(item.get("projected_occurrence_id"))
        owner = occurrence_by_id.get(item.get("owner_occurrence_id"))
        component_ids = item.get("owner_component_occurrence_ids")
        is_owned = item.get("status") == total_v1.COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_STATUS
        is_ambiguous = item.get("status") == total_v1.COEXTENSIVE_PRECEDING_NUMERIC_AMBIGUITY_STATUS
        if (
            set(item) != _COEXTENSIVE_STRUCTURAL_NUMERIC_FIELDS
            or not (is_owned or is_ambiguous)
            or type(projected) is not dict
            or projected["role_kind"] != "STRUCTURAL_GROUP"
            or projected["role"] != item["projected_role"]
            or projected["has_bound_value_row"] is not is_ambiguous
            or type(owner) is not dict
            or owner["role_kind"] != "STRUCTURAL_GROUP"
            or owner["role"] != item["owner_role"]
            or type(component_ids) is not list
            or len(component_ids) < 2
            or len(component_ids) != len(set(component_ids))
            or any(
                component_id not in occurrence_by_id
                or occurrence_by_id[component_id]["role_kind"] != "ADDITIVE_CHILD"
                or occurrence_by_id[component_id]["scope_owner_occurrence_id"]
                != item["owner_occurrence_id"]
                for component_id in component_ids
            )
            or type(source_record) is not dict
            or source_record.get("status") != "VISIBLE_VALUE_LANES_BOUND"
            or source_record.get("role") != item["projected_role"]
            or source_record.get("label_match", {}).get("occurrence_id")
            != item["projected_occurrence_id"]
            or type(source_values) is not list
            or not source_values
            or item["source_sample_ids"]
            != [source_value.get("sample_id") for source_value in source_values]
            or any(
                (sample_id in retained_sample_ids) is not is_ambiguous
                for sample_id in item["source_sample_ids"]
            )
            or (
                is_ambiguous
                and not same_typed_json_v1(
                    source_record,
                    row_by_occurrence.get(item["projected_occurrence_id"]),
                )
            )
        ):
            raise _error("coextensive structural numeric evidence axis drifted")
        coextensive_projected_ids.append(item["projected_occurrence_id"])
        coextensive_sample_ids.extend(item["source_sample_ids"])
    if len(coextensive_projected_ids) != len(set(coextensive_projected_ids)) or len(
        coextensive_sample_ids
    ) != len(set(coextensive_sample_ids)):
        raise _error("coextensive structural numeric evidence repeats source ownership")
    dash_sample_ids = []
    for item in value["authenticated_existing_dash_evidence"]:
        embedded = item.get("dash_evidence") if type(item) is dict else None
        if embedded is not None:
            try:
                embedded = dash_v1._validate(embedded)
            except dash_v1.FamilyFirstAuthenticatedSnapshotCellDashV1Error as exc:
                raise _error("embedded authenticated existing DASH evidence drifted") from exc
        if (
            type(item) is not dict
            or set(item) != _DASH_PROJECTION_FIELDS
            or item["row_kind"] not in {"ROLE_ROW", "TRAILING_VALUE_ROW"}
            or type(item["sample_id"]) is not str
            or not item["sample_id"]
            or type(item["page_sequence"]) is not int
            or item["page_sequence"] <= 0
            or type(item["status"]) is not str
            or not item["status"]
            or (
                item["row_kind"] == "ROLE_ROW"
                and (
                    item["occurrence_id"] not in occurrence_by_id
                    or item["role"] != occurrence_by_id[item["occurrence_id"]]["role"]
                )
            )
            or (
                item["row_kind"] == "TRAILING_VALUE_ROW"
                and (item["occurrence_id"] is not None or item["role"] is not None)
            )
            or (
                item["dash_evidence"] is None
                and item["status"] == "AUTHENTICATED_VISIBLE_EXISTING_CELL_DASH_ZERO"
            )
            or (
                item["dash_evidence"] is not None
                and (
                    type(item["dash_evidence"]) is not dict
                    or embedded["input_binding"]["sample_id"] != item["sample_id"]
                    or embedded["input_binding"]["local_to_physical_page"]["physical_page"]
                    != item["page_sequence"]
                    or (item["status"] == "AUTHENTICATED_VISIBLE_EXISTING_CELL_DASH_ZERO")
                    is not (
                        embedded["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
                        and embedded["normalized_value"] == 0
                    )
                )
            )
        ):
            raise _error("authenticated existing DASH evidence axis drifted")
        dash_sample_ids.append(item["sample_id"])
    if len(dash_sample_ids) != len(set(dash_sample_ids)):
        raise _error("authenticated existing DASH sample axis repeats")
    if (not value["unresolved_reasons"]) is not (
        value["status"]
        == "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
    ):
        raise _error("occurrence row-axis status differs from its unresolved reasons")
    material = canonical_clone_v1(value)
    identity = material.pop("occurrence_axis_id")
    if identity != "aforav2:axis:" + canonical_json_sha256_v1(material):
        raise _error("occurrence row-axis identity drifted")
    return canonical_clone_v1(value)


def _build(
    pages: Any,
    family_spec: Any,
    topology_scan: Any,
    topology_region: Any,
    policy: Any,
    *,
    effective_topology_region: Mapping[str, Any] | None,
    topology_candidates: Mapping[str, Any] | None,
    prepared_topology_binding: (
        candidates_v2._PreparedAccountingFamilyTopologyCandidateBindingV2 | None
    ),
    selected_snapshot: Mapping[str, Any] | None,
    prepared_snapshot: _PreparedAuthenticatedSnapshotProjectionV2 | None,
    render_snapshots: Sequence[Mapping[str, Any]],
    visible_dash_rescues: Any,
) -> dict[str, Any]:
    _policy(policy)
    try:
        parsed_pages = row_v1._pages(pages)
        compiled_family = topology_v1._spec(family_spec)
        scan = topology_v1._validate_result(topology_scan)
    except (ValueError, RuntimeError) as exc:
        raise _error("occurrence row-axis shared input contract drifted") from exc
    if scan["family_id"] != compiled_family["family_id"] or type(topology_region) is not dict:
        raise _error("occurrence row-axis family or selected region drifted")
    _validate_snapshot_and_renders(
        parsed_pages,
        selected_snapshot,
        render_snapshots,
        prepared_snapshot=prepared_snapshot,
    )
    expanded_matches, selected_region, expected_effective, topology_candidates_id = (
        _expanded_matches(
            parsed_pages,
            family_spec,
            scan,
            topology_region,
            effective_topology_region,
            topology_candidates,
            prepared_topology_binding,
        )
    )
    matches = _decorate_scopes(
        expanded_matches,
        selected_region,
    )
    expanded = _expanded_region(expected_effective, matches)
    try:
        raw_axis = row_v1._build_axis(
            parsed_pages,
            scan,
            expanded,
            visible_dash_rescues,
        )
    except row_v1.AccountingFamilyRowAxisV1Error as exc:
        raise _error("sealed V1 occurrence row/lane projection failed") from exc
    axis, dash_evidence, dash_reasons = _authenticate_existing_dashes(
        raw_axis,
        selected_snapshot=selected_snapshot,
        render_snapshots=render_snapshots,
    )
    try:
        axis, coextensive_evidence = (
            total_v1.project_accounting_family_coextensive_structural_numeric_rows_v1(
                axis,
                matches,
            )
        )
        if coextensive_evidence:
            axis = _regenerate_v1_axis(axis)
    except total_v1.AccountingFamilyCoextensiveParentTotalV1Error as exc:
        raise _error("coextensive structural numeric source projection failed") from exc
    rows_by_occurrence = {row["label_match"].get("occurrence_id"): row for row in axis["rows"]}
    role_occurrences = [
        {
            "has_bound_value_row": match["occurrence_id"] in rows_by_occurrence,
            "label_match": canonical_clone_v1(match),
            "occurrence_id": match["occurrence_id"],
            "role": match["role"],
            "role_kind": match["role_kind"],
            "scope_owner_occurrence_id": match["scope_owner_occurrence_id"],
            "scope_owner_role": match["scope_owner_role"],
        }
        for match in matches
    ]
    reasons = list(dash_reasons)
    reasons.extend(
        f"{evidence['status']}:{evidence['projected_occurrence_id']}"
        for evidence in coextensive_evidence
        if evidence["status"] == total_v1.COEXTENSIVE_PRECEDING_NUMERIC_AMBIGUITY_STATUS
    )
    if axis["status"] != "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY":
        reasons.insert(0, "VISIBLE_ROLE_OCCURRENCE_ROW_LANES_NOT_COMPLETE")
    material = {
        "authenticated_existing_dash_evidence": dash_evidence,
        "claim_boundary": CLAIM_BOUNDARY,
        "coextensive_structural_numeric_evidence": coextensive_evidence,
        "dependency_content_refs": _dependency_refs(),
        "family_id": compiled_family["family_id"],
        "format_version": FORMAT_VERSION,
        "role_occurrences": role_occurrences,
        "row_axis": axis,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
            if not reasons
            else "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"
        ),
        "topology_candidates_id": topology_candidates_id,
        "topology_scan_id": scan["scan_id"],
        "unresolved_reasons": list(dict.fromkeys(reasons)),
    }
    return _validate_result(
        {
            **material,
            "occurrence_axis_id": "aforav2:axis:" + canonical_json_sha256_v1(material),
        }
    )


def build_accounting_family_occurrence_row_axis_v2(
    pages: Any,
    family_spec: Any,
    topology_scan: Any,
    topology_region: Any,
    policy: Any,
    *,
    effective_topology_region: Mapping[str, Any] | None = None,
    topology_candidates: Mapping[str, Any] | None = None,
    selected_snapshot: Mapping[str, Any] | None = None,
    render_snapshots: Sequence[Mapping[str, Any]] = (),
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Expand context-bound occurrences and authenticate existing DASH cells."""

    return _build(
        pages,
        family_spec,
        topology_scan,
        topology_region,
        policy,
        effective_topology_region=effective_topology_region,
        topology_candidates=topology_candidates,
        prepared_topology_binding=None,
        selected_snapshot=selected_snapshot,
        prepared_snapshot=None,
        render_snapshots=render_snapshots,
        visible_dash_rescues=visible_dash_rescues,
    )


def _build_accounting_family_occurrence_row_axis_from_authenticated_topology_scan_v2(
    pages: Any,
    family_spec: Any,
    topology_scan: Any,
    topology_region: Any,
    policy: Any,
    *,
    effective_topology_region: Mapping[str, Any] | None = None,
    topology_candidates: Mapping[str, Any] | None = None,
    prepared_topology_binding: (
        candidates_v2._PreparedAccountingFamilyTopologyCandidateBindingV2 | None
    ) = None,
    selected_snapshot: Mapping[str, Any] | None = None,
    prepared_snapshot: _PreparedAuthenticatedSnapshotProjectionV2 | None = None,
    render_snapshots: Sequence[Mapping[str, Any]] = (),
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    return _build(
        pages,
        family_spec,
        topology_scan,
        topology_region,
        policy,
        effective_topology_region=effective_topology_region,
        topology_candidates=topology_candidates,
        prepared_topology_binding=prepared_topology_binding,
        selected_snapshot=selected_snapshot,
        prepared_snapshot=prepared_snapshot,
        render_snapshots=render_snapshots,
        visible_dash_rescues=visible_dash_rescues,
    )


def validate_accounting_family_occurrence_row_axis_replay_v2(
    value: Any,
    pages: Any,
    family_spec: Any,
    topology_scan: Any,
    topology_region: Any,
    policy: Any,
    *,
    effective_topology_region: Mapping[str, Any] | None = None,
    topology_candidates: Mapping[str, Any] | None = None,
    selected_snapshot: Mapping[str, Any] | None = None,
    render_snapshots: Sequence[Mapping[str, Any]] = (),
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Rebuild the occurrence, row/lane, scope, and exact-cell dash evidence."""

    persisted = _validate_result(value)
    expected = build_accounting_family_occurrence_row_axis_v2(
        pages,
        family_spec,
        topology_scan,
        topology_region,
        policy,
        effective_topology_region=effective_topology_region,
        topology_candidates=topology_candidates,
        selected_snapshot=selected_snapshot,
        render_snapshots=render_snapshots,
        visible_dash_rescues=visible_dash_rescues,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("occurrence row-axis does not replay exactly")
    return persisted
