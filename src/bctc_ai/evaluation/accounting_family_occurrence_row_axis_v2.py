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
import math
import os
import re
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
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
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
    "EXACT_PRECEDING_SCOPE_SUBTOTAL_SOURCE_OWNERSHIP_AND_REVIEWED_EXACT_"
    "SOURCE_SUBSCOPE_INTERVAL_SCHEMA_ROLE_TYPING_"
    "AUTHENTICATED_EXTREME_MARGIN_CHROMATIC_FURNITURE_NUMERIC_DENOMINATOR_"
    "PROPOSAL_ONLY_NO_ACCOUNTING_PERIOD_UNIT_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "accounting_authority": False,
    "bank_file_page_period_scope_used_for_routing": False,
    "detector_hole_dash_authority_changed": False,
    "existing_dash_text_alone_means_zero": False,
    "extreme_margin_furniture_requires_authenticated_exact_page_pixels": True,
    "extreme_margin_numeric_may_be_silently_deleted": False,
    "mapping_authority": False,
    "occurrences_may_cross_selected_topology_region": False,
    "preceding_numeric_source_ambiguous_ownership_can_resolve": False,
    "preceding_scope_subtotal_may_be_reused_by_next_structural_group": False,
    "repeated_roles_may_be_silently_collapsed": False,
    "schema_authority": False,
    "schema_role_typing_requires_exact_source_scope_receipt": True,
    "sealed_row_axis_v1_bytes_changed": False,
    "visible_existing_dash_requires_authenticated_exact_cell_pixels": True,
}
_POLICY_FIELDS = {
    "format_version",
    "require_authenticated_existing_dash_pixels",
    "retain_all_context_bound_role_occurrences",
}
_RESULT_FIELDS = {
    "authenticated_extreme_margin_furniture_evidence",
    "authenticated_existing_dash_evidence",
    "claim_boundary",
    "coextensive_structural_numeric_evidence",
    "dependency_content_refs",
    "family_id",
    "format_version",
    "internal_unassigned_numeric_clusters",
    "numeric_sample_universe",
    "occurrence_axis_id",
    "one_edit_exact_source_structural_proofs",
    "role_occurrences",
    "row_axis",
    "safety",
    "status",
    "structural_owner_only_rescue_rejections",
    "topology_candidates_id",
    "topology_scan_id",
    "unresolved_reasons",
}
_OCCURRENCE_FIELDS = {
    "has_bound_value_row",
    "label_match",
    "occurrence_id",
    "retrieval_occurrence_id",
    "retrieval_scope_owner_occurrence_id",
    "role",
    "role_kind",
    "scope_owner_occurrence_id",
    "scope_owner_match_kind",
    "scope_owner_role",
    "source_scope_binding",
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
_NUMERIC_SAMPLE_FIELDS = {
    "bbox",
    "column_center",
    "column_ordinal",
    "crop_ref",
    "line_ordinal",
    "owner_id",
    "owner_kind",
    "page_sequence",
    "parsed_token",
    "raw_prediction",
    "reader_score",
    "sample_id",
}
_NUMERIC_SAMPLE_OWNER_KINDS = {
    "AUTHENTICATED_EXTREME_MARGIN_FURNITURE",
    "COEXTENSIVE_SCOPE_TOTAL_REFERENCE",
    "ROLE_OCCURRENCE",
    "SOURCE_ONLY_INTERNAL_CLUSTER",
    "TRAILING_VALUE_ROW",
}
_SOURCE_SCOPE_BINDING_FIELDS = {
    "anchor_span",
    "anchor_exact_source_authority_check",
    "binding_id",
    "binding_kind",
    "geometry",
    "interval",
    "source_role",
    "source_exact_source_authority_check",
    "source_scope_role",
    "source_span",
    "status",
    "target_role",
}
_SOURCE_SCOPE_BINDING_STATUS = "REVIEWED_EXACT_SOURCE_SCOPE_TO_SCHEMA_ROLE_BINDING"
_AMBIGUOUS_WRAPPED_LABEL_STATUS = "SOURCE_ONLY_AMBIGUOUS_TOUCHING_WRAPPED_LABEL"
_ONE_EDIT_EXACT_BOUND_STATUS = "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"
_DISCOUNT_GENERIC_ROLE = "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
_DISCOUNT_SCOPE_TARGETS = {
    "INTERBANK_LOAN_VND": "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND",
    "INTERBANK_LOAN_FOREIGN_CURRENCY": ("INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY"),
}
_PROVISION_GENERIC_ROLE = "INTERBANK_PROVISION_AMBIGUOUS"
_EXPLICIT_GROUP_TOTAL_SOURCE_TARGETS = {
    "EXPLICIT_INTERBANK_DEPOSIT_TOTAL_AMBIGUOUS": (
        "EXPLICIT_INTERBANK_DEPOSIT_TOTAL",
        "INTERBANK_DEPOSIT_GROUP",
    ),
    "EXPLICIT_INTERBANK_LOAN_TOTAL_AMBIGUOUS": (
        "EXPLICIT_INTERBANK_LOAN_TOTAL",
        "INTERBANK_LOAN_GROUP",
    ),
}
_EXPLICIT_GROUP_TOTAL_TARGET_SOURCES = {
    target: (source, owner)
    for source, (target, owner) in _EXPLICIT_GROUP_TOTAL_SOURCE_TARGETS.items()
}
_EXPLICIT_GROUP_TOTAL_ROLES = {
    *_EXPLICIT_GROUP_TOTAL_SOURCE_TARGETS,
    *_EXPLICIT_GROUP_TOTAL_TARGET_SOURCES,
}
_EXPLICIT_GROUP_TOTAL_BINDING_KIND = "UNIQUE_EXACT_EXPLICIT_GROUP_TOTAL_INTERVAL"
_EXPLICIT_GROUP_TOTAL_PARENT_GEOMETRY_STATUS = "EXACT_EXPLICIT_GROUP_TOTAL_PARENT_OCCURRENCE"
_SCHEMA_SCOPE_REQUIRED_ROLES = {
    _DISCOUNT_GENERIC_ROLE,
    _PROVISION_GENERIC_ROLE,
    *_DISCOUNT_SCOPE_TARGETS,
    *_DISCOUNT_SCOPE_TARGETS.values(),
    "INTERBANK_DEPOSIT_PROVISION",
    "INTERBANK_LOAN_GROUP",
    "TOTAL_INTERBANK_PROVISION",
}
_DEPOSIT_SCOPE_ROLES = {
    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
    "DEMAND_DEPOSIT_GROUP",
    "DEMAND_DEPOSIT_VND",
    "INTERBANK_DEPOSIT_GROUP",
    "TERM_DEPOSIT_FOREIGN_CURRENCY",
    "TERM_DEPOSIT_GROUP",
    "TERM_DEPOSIT_VND",
}
_DEPOSIT_SEMANTIC_INTERVAL_ROLES = {
    *_DEPOSIT_SCOPE_ROLES,
    "DEMAND_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",
    "INTERBANK_DEPOSIT_OTHER",
    "INTERBANK_DEPOSIT_PROVISION",
    "TERM_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",
    _PROVISION_GENERIC_ROLE,
}
_LOAN_LEAF_ROLES = {
    *_DISCOUNT_SCOPE_TARGETS,
    *_DISCOUNT_SCOPE_TARGETS.values(),
    "INTERBANK_LOAN_GOLD_AND_FOREIGN_CURRENCY",
    "INTERBANK_LOAN_OTHER",
    "INTERBANK_LOAN_PROVISION",
}
_LOAN_SEMANTIC_INTERVAL_ROLES = {
    *_LOAN_LEAF_ROLES,
    _DISCOUNT_GENERIC_ROLE,
    _PROVISION_GENERIC_ROLE,
}
_LOAN_SOURCE_SUBSCOPE_BOUNDARY_ROLES = {
    *_LOAN_SEMANTIC_INTERVAL_ROLES,
    *_DEPOSIT_SEMANTIC_INTERVAL_ROLES,
    *_EXPLICIT_GROUP_TOTAL_ROLES,
    "EXPLICIT_FAMILY_TOTAL",
    "INTERBANK_LOAN_GROUP",
    "TOTAL_INTERBANK_PROVISION",
}
_STRUCTURAL_OWNER_ONLY_RESCUE_STATUS = "STRUCTURAL_OWNER_ONLY_TINY_ISOLATED_RESCUE_REJECTED"
_STRUCTURAL_OWNER_ONLY_RESCUE_FIELDS = {
    "complete_descendant_occurrence_ids",
    "evidence_id",
    "interval",
    "occurrence_id",
    "page_sequence",
    "rejected_rescue_projections",
    "role",
    "source_record",
    "status",
}
_STRUCTURAL_OWNER_ONLY_INTERVAL_FIELDS = {
    "end_document_line_ordinal_exclusive",
    "start_document_line_ordinal",
}
_INTERNAL_UNASSIGNED_CLUSTER_FIELDS = {
    "cluster_id",
    "column_ordinals",
    "inspected_label_band",
    "label_lane_status",
    "page_sequence",
    "same_row_label_evidence",
    "sample_ids",
    "status",
}
_SAME_ROW_LABEL_EVIDENCE_FIELDS = {
    "bbox",
    "line_ordinal",
    "numeric_raw_prediction",
    "vietocr_text",
}
_INSPECTED_LABEL_BAND_FIELDS = {
    "document_pages_sha256",
    "input_page_line_count",
    "numeric_row_bboxes",
    "numeric_row_sample_ids",
    "page_sequence",
    "receipt_id",
    "source_line_axis",
    "source_line_axis_sha256",
}
_UNLABELED_LABEL_LANE_STATUS = "NO_SAME_ROW_LABEL_FRAGMENT_IN_EXACT_LABEL_BAND"
_LABELED_LABEL_LANE_STATUS = "EXPLICIT_SAME_ROW_LABEL_FRAGMENT_PRESENT"
_INTERNAL_UNASSIGNED_CLUSTER_STATUS = "SOURCE_ONLY_INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
_OFF_LANE_NUMERIC_CLUSTER_STATUS = "SOURCE_ONLY_OFF_LANE_NUMERIC_CLUSTER"
_EXTREME_MARGIN_FURNITURE_STATUS = "AUTHENTICATED_EXTREME_MARGIN_CHROMATIC_ANNOTATION_FURNITURE"
_EXTREME_MARGIN_FURNITURE_OWNER_KIND = "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
_EXTREME_MARGIN_ADMITTED_NUMERIC_CLASSIFICATIONS = {
    "DASH_ZERO",
    "MIXED_GROUPED_INTEGER_CANDIDATE",
    "NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
    "SIGNED_NUMBER",
}
_EXTREME_MARGIN_RENDER_REASON_PREFIX = "EXTREME_MARGIN_ANNOTATION_RENDER_REQUIRED:PAGE_SEQUENCE:"
_EXTREME_MARGIN_FURNITURE_FIELDS = {
    "candidate_crop_proof",
    "document_pages_sha256",
    "evidence_id",
    "full_page_inspected_label_band",
    "geometry",
    "margin_band",
    "original_cluster",
    "page_sequence",
    "peer_crop_proofs",
    "sample_id",
    "snapshot_id",
    "source_record",
    "status",
    "topology_candidates_id",
}
_EXTREME_MARGIN_GEOMETRY_FIELDS = {
    "candidate_bbox",
    "candidate_center_quads",
    "extreme_right_denominator",
    "extreme_right_numerator",
    "lane_centers_quads",
    "lane_tolerance",
    "nearest_lane_ordinal",
    "page_width",
    "right_edge_gap",
}
_EXTREME_MARGIN_BAND_FIELDS = {
    "document_pages_sha256",
    "input_page_line_count",
    "page_sequence",
    "qualifying_peer_line_ordinals",
    "source_line_axis",
    "source_line_axis_sha256",
}
_EXTREME_MARGIN_LINE_FIELDS = {
    "bbox",
    "crop_ref",
    "line_ordinal",
    "numeric_raw_prediction",
    "numeric_reader_score",
    "sample_id",
    "vietocr_text",
}
_EXTREME_MARGIN_CROP_PROOF_FIELDS = {
    "chromatic_ink_pixel_count",
    "exact_bbox_rgb_sha256",
    "ink_pixel_count",
    "pixel_count",
    "render_binding",
    "source_line_record",
}
_EXTREME_MARGIN_RENDER_BINDING_FIELDS = {
    "document_ordinal",
    "physical_page",
    "raw_pixel_bbox",
    "render_id",
    "render_ref",
}
_MAX_ROLE_OCCURRENCES = 4_096
_MAX_EXISTING_DASH_CELLS = 16_384
_MAX_NUMERIC_SAMPLES = 65_536
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
    def context_depth(candidate: Mapping[str, Any]) -> int:
        depth = 0
        cursor = candidate
        visited: set[str] = set()
        while (within_role := cursor.get("matched_within_role")) is not None:
            if within_role in visited:
                raise _error("contextual role occurrence ancestry contains a cycle")
            visited.add(within_role)
            owners = [
                other
                for other in candidates
                if other["role"] == within_role
                and other["document_line_ordinal"] <= candidate["document_line_ordinal"]
                and other is not cursor
            ]
            if not owners:
                return depth
            cursor = max(
                owners,
                key=lambda item: (
                    item["document_line_ordinal"],
                    item["end_document_line_ordinal"],
                ),
            )
            depth += 1
        return depth

    context_depths = {id(candidate): context_depth(candidate) for candidate in candidates}
    composed_suffix_evidence = [*candidates]
    if type(selected.get("parent_match")) is dict:
        composed_suffix_evidence.append(selected["parent_match"])
    composed_suffix_evidence.extend(selected.get("hard_negative_matches", []))
    page_by_sequence = {page["page_sequence"]: page for page in pages}
    compiled_for_wrapped_labels = topology_v1._spec(family_spec)
    aliases_by_role = {
        child["role"]: {alias for matcher in child["matchers"] for alias in matcher["aliases"]}
        for child in compiled_for_wrapped_labels["children"]
    }
    contextual_aliases_by_role: dict[str, dict[str | None, set[str]]] = {}
    for child in compiled_for_wrapped_labels["children"]:
        for matcher in child["matchers"]:
            contextual_aliases_by_role.setdefault(child["role"], {}).setdefault(
                matcher["within_role"], set()
            ).update(matcher["aliases"])

    def fragments_touch(first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
        page = page_by_sequence.get(first["page_sequence"])
        if type(page) is not dict or second["page_sequence"] != first["page_sequence"]:
            return False
        first_bbox = page["lines"][first["end_source_line_index"]]["bbox"]
        second_bbox = page["lines"][second["source_line_index"]]["bbox"]
        text_height = max(
            first_bbox[3] - first_bbox[1],
            second_bbox[3] - second_bbox[1],
        )
        vertical_gap = second_bbox[1] - first_bbox[3]
        return 2 * vertical_gap >= -text_height and 4 * vertical_gap <= text_height

    def has_same_row_money(match: Mapping[str, Any]) -> bool:
        page = page_by_sequence.get(match["page_sequence"])
        if type(page) is not dict:
            return False
        label_bbox = page["lines"][match["end_source_line_index"]]["bbox"]
        label_center_twice = label_bbox[1] + label_bbox[3]
        label_height = label_bbox[3] - label_bbox[1]
        return any(
            row_v1._is_numeric(line)  # noqa: SLF001
            and line["bbox"][0] >= label_bbox[2]
            and abs(line["bbox"][1] + line["bbox"][3] - label_center_twice)
            <= max(label_height, line["bbox"][3] - line["bbox"][1])
            for line in page["lines"]
        )

    def is_wrapped_explicit_discount(bare: Mapping[str, Any], suffix: Mapping[str, Any]) -> bool:
        return fragments_touch(bare, suffix) and not has_same_row_money(bare)

    def typed_discount_wraps_bare(bare: Mapping[str, Any], typed: Mapping[str, Any]) -> bool:
        return any(
            typed["role"] == target_role
            and suffix["role"] == scope_role
            and suffix["page_sequence"] == typed["page_sequence"]
            and suffix["end_document_line_ordinal"] == typed["end_document_line_ordinal"]
            and is_wrapped_explicit_discount(bare, suffix)
            for scope_role, target_role in _DISCOUNT_SCOPE_TARGETS.items()
            for suffix in candidates
        )

    def visual_preceding_label_fragment(
        candidate: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        page = page_by_sequence.get(candidate["page_sequence"])
        source_index = candidate["source_line_index"]
        if type(page) is not dict or source_index <= 0:
            return None
        current_bbox = page["lines"][source_index]["bbox"]
        preceding_candidates = []
        for preceding in page["lines"][max(0, source_index - 12) : source_index]:
            preceding_bbox = preceding["bbox"]
            text_height = max(
                preceding_bbox[3] - preceding_bbox[1],
                current_bbox[3] - current_bbox[1],
            )
            vertical_gap = current_bbox[1] - preceding_bbox[3]
            if (
                preceding["vietocr_text"].strip()
                and not row_v1._is_numeric(preceding)  # noqa: SLF001
                and abs(preceding_bbox[0] - current_bbox[0]) <= 6
                and 2 * vertical_gap >= -text_height
                and 4 * vertical_gap <= text_height
            ):
                preceding_candidates.append(preceding)
        return max(
            preceding_candidates,
            key=lambda item: (item["bbox"][3], item["line_ordinal"]),
            default=None,
        )

    def known_visual_owner_composes_other(
        candidate: Mapping[str, Any], preceding: Mapping[str, Any] | None
    ) -> bool:
        if preceding is None:
            return False
        page = page_by_sequence[candidate["page_sequence"]]
        page_width = page.get("page_width")
        for owner in composed_suffix_evidence:
            if (
                owner.get("role") == candidate["role"]
                or owner["page_sequence"] != candidate["page_sequence"]
                or owner["end_source_line_index"] != preceding["line_ordinal"]
                or not str(owner.get("match_kind", "")).startswith("EXACT_")
                or (
                    f"{owner['normalized_surface']} {candidate['normalized_surface']}"
                    not in aliases_by_role.get(owner.get("role"), set())
                )
            ):
                continue
            owner_bbox = preceding["bbox"]
            owner_center_twice = owner_bbox[1] + owner_bbox[3]
            owner_height = owner_bbox[3] - owner_bbox[1]
            intervening = page["lines"][
                preceding["line_ordinal"] + 1 : candidate["source_line_index"]
            ]
            if all(
                (
                    line["bbox"][0] >= owner_bbox[2]
                    and (
                        not line["vietocr_text"].strip() or row_v1._is_numeric(line)  # noqa: SLF001
                    )
                    and abs(line["bbox"][1] + line["bbox"][3] - owner_center_twice)
                    <= max(owner_height, line["bbox"][3] - line["bbox"][1])
                )
                or (type(page_width) is int and 4 * line["bbox"][0] >= 3 * page_width)
                for line in intervening
            ):
                return True
        return False

    def compose_known_scoped_other(
        candidate: dict[str, Any], preceding: Mapping[str, Any] | None
    ) -> bool:
        if preceding is None or not has_same_row_money(candidate):
            return False
        within_role = candidate.get("matched_within_role")
        if type(within_role) is not str:
            return False
        composite_surface = (
            f"{preceding['vietocr_text'].strip()} {candidate['surface'].strip()}".strip()
        )
        composite_normalized = normalize_vietnamese_anchor_v1(composite_surface)
        aliases = contextual_aliases_by_role.get(candidate["role"], {}).get(within_role, set())
        if composite_normalized not in aliases:
            return False
        owners = [
            match
            for match in candidates
            if match["role"] == within_role
            and match["page_sequence"] == candidate["page_sequence"]
            and match["end_document_line_ordinal"] < candidate["document_line_ordinal"]
        ]
        if not owners:
            return False
        nearest_end = max(owner["end_document_line_ordinal"] for owner in owners)
        nearest = [owner for owner in owners if owner["end_document_line_ordinal"] == nearest_end]
        if len(nearest) != 1 or not str(nearest[0]["match_kind"]).startswith("EXACT_"):
            return False
        candidate["document_line_ordinal"] = (
            candidate["document_line_ordinal"]
            - candidate["source_line_index"]
            + preceding["line_ordinal"]
        )
        candidate["match_kind"] = "EXACT_ACCENTLESS_ALIAS_VISUAL_CONTINUATION"
        candidate["normalized_surface"] = composite_normalized
        candidate["source_line_index"] = preceding["line_ordinal"]
        candidate["source_line_indices"] = [
            preceding["line_ordinal"],
            candidate["end_source_line_index"],
        ]
        candidate["surface"] = composite_surface
        return True

    result = []
    for candidate in candidates:
        visual_preceding_fragment = (
            visual_preceding_label_fragment(candidate)
            if candidate["document_line_ordinal"] == candidate["end_document_line_ordinal"]
            and candidate["normalized_surface"] in {"cac khoan khac", "khac"}
            and candidate["role"] in {"INTERBANK_DEPOSIT_OTHER", "INTERBANK_LOAN_OTHER"}
            else None
        )
        compose_known_scoped_other(candidate, visual_preceding_fragment)
        same_source_twins = [
            other
            for other in candidates
            if other["page_sequence"] == candidate["page_sequence"]
            and other["document_line_ordinal"] == candidate["document_line_ordinal"]
            and other["end_document_line_ordinal"] == candidate["end_document_line_ordinal"]
            and other["normalized_surface"] == candidate["normalized_surface"]
        ]
        superseded = (
            any(
                other is not candidate
                and other["role"] == candidate["role"]
                and other["page_sequence"] == candidate["page_sequence"]
                and other["end_document_line_ordinal"] == candidate["end_document_line_ordinal"]
                and other.get("matched_within_role") is not None
                and candidate.get("matched_within_role") is None
                and other["document_line_ordinal"] >= candidate["document_line_ordinal"]
                for other in candidates
            )
            or (
                candidate["role"] == _DISCOUNT_GENERIC_ROLE
                and any(
                    other["role"] in set(_DISCOUNT_SCOPE_TARGETS.values())
                    and other["page_sequence"] == candidate["page_sequence"]
                    and other["document_line_ordinal"] == candidate["document_line_ordinal"]
                    and other["end_document_line_ordinal"] > candidate["end_document_line_ordinal"]
                    and typed_discount_wraps_bare(candidate, other)
                    for other in candidates
                )
            )
            or context_depths[id(candidate)]
            < max(context_depths[id(other)] for other in same_source_twins)
        )
        singleton_other_is_composed_suffix = (
            candidate["document_line_ordinal"] == candidate["end_document_line_ordinal"]
            and candidate["normalized_surface"] in {"cac khoan khac", "khac"}
            and candidate["role"] in {"INTERBANK_DEPOSIT_OTHER", "INTERBANK_LOAN_OTHER"}
            and (
                any(
                    other.get("role") != candidate["role"]
                    and other["page_sequence"] == candidate["page_sequence"]
                    and other["document_line_ordinal"] < candidate["document_line_ordinal"]
                    and other["end_document_line_ordinal"] == candidate["end_document_line_ordinal"]
                    and other["normalized_surface"].endswith(candidate["normalized_surface"])
                    for other in composed_suffix_evidence
                )
                or known_visual_owner_composes_other(candidate, visual_preceding_fragment)
            )
        )
        touching_unknown_preceding_fragment = None
        touching_unknown_candidate_bbox = None
        if (
            not singleton_other_is_composed_suffix
            and candidate["document_line_ordinal"] == candidate["end_document_line_ordinal"]
            and candidate["normalized_surface"] in {"cac khoan khac", "khac"}
            and candidate["role"] in {"INTERBANK_DEPOSIT_OTHER", "INTERBANK_LOAN_OTHER"}
        ):
            page = page_by_sequence.get(candidate["page_sequence"])
            source_index = candidate["source_line_index"]
            if type(page) is dict and source_index > 0:
                current = page["lines"][source_index]
                current_bbox = current["bbox"]
                if visual_preceding_fragment is not None:
                    touching_unknown_preceding_fragment = visual_preceding_fragment
                    touching_unknown_candidate_bbox = current_bbox
        # Do not let the generic surface compositor concatenate one complete
        # bare discount row with a later, independently complete currency row
        # and thereby manufacture an explicit-currency discount.  A genuinely
        # wrapped explicit label has no exact bare-discount match ending before
        # its currency suffix and therefore remains untouched, including valid
        # interleaved source-line shapes.
        bare_discount_starts = [
            bare
            for bare in candidates
            if bare["role"] == _DISCOUNT_GENERIC_ROLE
            and bare["page_sequence"] == candidate["page_sequence"]
            and bare["document_line_ordinal"] == candidate["document_line_ordinal"]
            and bare["end_document_line_ordinal"] < candidate["end_document_line_ordinal"]
        ]
        currency_suffixes = [
            scope
            for scope_role in _DISCOUNT_SCOPE_TARGETS
            for scope in candidates
            if _DISCOUNT_SCOPE_TARGETS[scope_role] == candidate["role"]
            and scope["role"] == scope_role
            and scope["page_sequence"] == candidate["page_sequence"]
            and scope["document_line_ordinal"] > candidate["document_line_ordinal"]
            and scope["end_document_line_ordinal"] == candidate["end_document_line_ordinal"]
        ]
        touching_explicit_discount_fragments = any(
            is_wrapped_explicit_discount(bare, suffix)
            for bare in bare_discount_starts
            for suffix in currency_suffixes
        )
        synthetic_discount_currency_compound = (
            candidate["role"] in set(_DISCOUNT_SCOPE_TARGETS.values())
            and candidate["document_line_ordinal"] < candidate["end_document_line_ordinal"]
            and bare_discount_starts
            and currency_suffixes
            and not touching_explicit_discount_fragments
        )
        parent_match = selected.get("parent_match")
        coextensive_parent_total_without_values = (
            candidate["role_kind"] == "TOTAL"
            and type(parent_match) is dict
            and candidate["page_sequence"] == parent_match["page_sequence"]
            and candidate["document_line_ordinal"] == parent_match["document_line_ordinal"]
            and candidate["end_document_line_ordinal"] == parent_match["end_document_line_ordinal"]
            and not _same_row_numeric_samples(pages, candidate)
        )
        if (
            not superseded
            and not singleton_other_is_composed_suffix
            and not synthetic_discount_currency_compound
            and not coextensive_parent_total_without_values
        ):
            if touching_unknown_preceding_fragment is not None:
                candidate["source_label_bbox"] = list(touching_unknown_candidate_bbox)
                candidate["source_scope_binding"] = _ambiguous_wrapped_other_binding(
                    candidate=candidate,
                    candidate_bbox=touching_unknown_candidate_bbox,
                    preceding_line=touching_unknown_preceding_fragment,
                )
            result.append(candidate)
    ordinals: dict[str, int] = {}
    for match in result:
        ordinal = ordinals.get(match["role"], 0)
        match["role_occurrence_ordinal"] = ordinal
        ordinals[match["role"]] = ordinal + 1
    return result, selected, expected_effective, topology_candidates_id


def _source_span(match: Mapping[str, Any]) -> dict[str, Any]:
    explicit_indices = match.get("source_line_indices")
    result = {
        "document_line_ordinal": match["document_line_ordinal"],
        "end_document_line_ordinal": match["end_document_line_ordinal"],
        "end_source_line_index": match["end_source_line_index"],
        "match_kind": match["match_kind"],
        "normalized_surface": match["normalized_surface"],
        "page_sequence": match["page_sequence"],
        "role": match["role"],
        "source_line_index": match["source_line_index"],
        "source_line_indices": (
            list(explicit_indices)
            if type(explicit_indices) is list
            else list(range(match["source_line_index"], match["end_source_line_index"] + 1))
        ),
    }
    if "source_label_bbox" in match:
        result["source_label_bbox"] = canonical_clone_v1(match["source_label_bbox"])
    return result


def _scope_binding(
    *,
    anchor: Mapping[str, Any] | None,
    anchor_exact_source_authority_check: Mapping[str, Any] | None = None,
    binding_kind: str,
    geometry: Mapping[str, Any] | None,
    interval_end_exclusive: int,
    interval_start: int,
    source: Mapping[str, Any],
    source_exact_source_authority_check: Mapping[str, Any] | None = None,
    source_role: str,
    source_scope_role: str,
    status: str = _SOURCE_SCOPE_BINDING_STATUS,
    target_role: str,
) -> dict[str, Any]:
    material = {
        "anchor_span": _source_span(anchor) if anchor is not None else None,
        "anchor_exact_source_authority_check": (
            canonical_clone_v1(anchor_exact_source_authority_check)
            if anchor_exact_source_authority_check is not None
            else None
        ),
        "binding_kind": binding_kind,
        "geometry": canonical_clone_v1(geometry) if geometry is not None else None,
        "interval": {
            "end_document_line_ordinal_exclusive": interval_end_exclusive,
            "start_document_line_ordinal": interval_start,
        },
        "source_role": source_role,
        "source_exact_source_authority_check": (
            canonical_clone_v1(source_exact_source_authority_check)
            if source_exact_source_authority_check is not None
            else None
        ),
        "source_scope_role": source_scope_role,
        "source_span": _source_span(source),
        "status": status,
        "target_role": target_role,
    }
    return {
        **material,
        "binding_id": "aforav2:scope-binding:" + canonical_json_sha256_v1(material),
    }


def _ambiguous_wrapped_other_binding(
    *,
    candidate: Mapping[str, Any],
    candidate_bbox: Sequence[int],
    preceding_line: Mapping[str, Any],
) -> dict[str, Any]:
    preceding_bbox = preceding_line["bbox"]
    skipped_source_line_indices = list(
        range(preceding_line["line_ordinal"] + 1, candidate["source_line_index"])
    )
    geometry = {
        "absolute_left_delta": abs(preceding_bbox[0] - candidate_bbox[0]),
        "candidate_bbox": list(candidate_bbox),
        "candidate_source_line_index": candidate["source_line_index"],
        "preceding_bbox": list(preceding_bbox),
        "preceding_source_line_index": preceding_line["line_ordinal"],
        "skipped_source_line_indices": skipped_source_line_indices,
        "vertical_gap": candidate_bbox[1] - preceding_bbox[3],
    }
    return _scope_binding(
        anchor=None,
        binding_kind="AMBIGUOUS_TOUCHING_PRECEDING_LABEL_FRAGMENT",
        geometry=geometry,
        interval_end_exclusive=candidate["end_document_line_ordinal"] + 1,
        interval_start=(
            candidate["document_line_ordinal"]
            - candidate["source_line_index"]
            + preceding_line["line_ordinal"]
        ),
        source=candidate,
        source_role=candidate["role"],
        source_scope_role=candidate.get("matched_within_role") or "SELECTED_FAMILY_ROOT",
        status=_AMBIGUOUS_WRAPPED_LABEL_STATUS,
        target_role=candidate["role"],
    )


def _source_line_bbox(pages: Sequence[Mapping[str, Any]], match: Mapping[str, Any]) -> list[int]:
    page_sequence = match["page_sequence"]
    source_line_index = match["source_line_index"]
    page = next((item for item in pages if item["page_sequence"] == page_sequence), None)
    if type(page) is not dict or not 0 <= source_line_index < len(page["lines"]):
        raise _error("schema scope source locator is absent from the selected pages")
    bbox = page["lines"][source_line_index]["bbox"]
    if type(bbox) is not list or len(bbox) != 4:
        raise _error("schema scope source locator lost its exact bbox")
    return list(bbox)


def _attach_schema_scope_source_label_bboxes(
    pages: Sequence[Mapping[str, Any]],
    compiled_family: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Expose canonical visual order before nearest-owner decoration.

    Some providers emit a child line before its visually preceding structural
    heading.  Family-3 source-scope projection already needs the exact label
    bboxes; attaching them before either retrieval-proof or projected-scope
    decoration gives both paths the same visual parent axis.
    """

    projected = [canonical_clone_v1(match) for match in matches]
    roles = {child["role"] for child in compiled_family["children"]}
    if not _SCHEMA_SCOPE_REQUIRED_ROLES <= roles:
        return projected
    for match in projected:
        match["source_label_bbox"] = _source_line_bbox(pages, match)
    return projected


def _source_label_fragment_bboxes(
    pages: Sequence[Mapping[str, Any]], match: Mapping[str, Any]
) -> list[list[int]]:
    page = next(
        (item for item in pages if item["page_sequence"] == match["page_sequence"]),
        None,
    )
    if type(page) is not dict:
        return []
    result = []
    for source_line_index in row_v1._match_source_line_indices(match):  # noqa: SLF001
        if not 0 <= source_line_index < len(page["lines"]):
            raise _error("logical label fragment is absent from its authenticated page")
        result.append(list(page["lines"][source_line_index]["bbox"]))
    return result


def _same_row_fragment_distance(
    numeric_line: Mapping[str, Any], label_bbox: Sequence[int]
) -> int | None:
    distance = abs(
        numeric_line["bbox"][1] + numeric_line["bbox"][3] - label_bbox[1] - label_bbox[3]
    )
    if numeric_line["bbox"][0] < label_bbox[2] or distance > max(
        label_bbox[3] - label_bbox[1],
        numeric_line["bbox"][3] - numeric_line["bbox"][1],
    ):
        return None
    return distance


def _same_row_numeric_samples(
    pages: Sequence[Mapping[str, Any]], match: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    page = next(
        (item for item in pages if item["page_sequence"] == match["page_sequence"]),
        None,
    )
    if type(page) is not dict:
        return []
    label_bboxes = _source_label_fragment_bboxes(pages, match)
    return sorted(
        (
            line
            for line in page["lines"]
            if row_v1._is_numeric(line)  # noqa: SLF001
            and any(
                _same_row_fragment_distance(line, label_bbox) is not None
                for label_bbox in label_bboxes
            )
        ),
        key=lambda line: (line["bbox"][0], line["line_ordinal"]),
    )


def _same_row_numeric_samples_are_complete(
    pages: Sequence[Mapping[str, Any]],
    match: Mapping[str, Any],
    semantic_matches: Sequence[Mapping[str, Any]],
) -> bool:
    """Fail closed unless a structural total exposes every page money lane.

    Scope projection runs before the sealed row axis is available.  The
    complete-lane proof therefore uses the same exact same-row samples and the
    maximum visible semantic-row lane count on that page.  A lone visible
    value in a two-lane table is not evidence that the structural subtree is
    complete; the sealed row-axis validator later replays the stronger
    ``VISIBLE_VALUE_LANES_BOUND`` status.
    """

    samples = _same_row_numeric_samples(pages, match)
    if not samples:
        return False
    match_label_bboxes = _source_label_fragment_bboxes(pages, match)
    for sample in samples:
        match_distances = [
            distance
            for bbox in match_label_bboxes
            if (distance := _same_row_fragment_distance(sample, bbox)) is not None
        ]
        if not match_distances:
            raise _error("same-row numeric sample lost every eligible logical label fragment")
        match_distance = min(match_distances)
        for peer in semantic_matches:
            if peer is match or peer["page_sequence"] != match["page_sequence"]:
                continue
            peer_distances = [
                distance
                for bbox in _source_label_fragment_bboxes(pages, peer)
                if (distance := _same_row_fragment_distance(sample, bbox)) is not None
            ]
            if peer_distances and min(peer_distances) <= match_distance:
                return False
    expected_lane_count = max(
        (
            len(_same_row_numeric_samples(pages, peer))
            for peer in semantic_matches
            if peer is not match and peer["page_sequence"] == match["page_sequence"]
        ),
        default=0,
    )
    return expected_lane_count > 0 and len(samples) == expected_lane_count


def _bound_one_edit_exact_source_check(
    match: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    check = match.get("one_edit_exact_source_authority_check")
    retrieval_occurrence_id = match.get("retrieval_occurrence_id", match.get("occurrence_id"))
    retrieval_role = match.get("retrieval_role", match.get("role"))
    retrieval_role_kind = match.get("retrieval_role_kind", match.get("role_kind"))
    retrieval_within_role = match.get("retrieval_within_role", match.get("matched_within_role"))
    explicit_indices = match.get("source_line_indices")
    expected_indices = (
        explicit_indices
        if type(explicit_indices) is list
        else list(range(match["source_line_index"], match["end_source_line_index"] + 1))
    )
    if (
        type(check) is not dict
        or check.get("status") != _ONE_EDIT_EXACT_BOUND_STATUS
        or check.get("match_scope") != "EXPANDED_OCCURRENCE"
        or check.get("occurrence_id") != retrieval_occurrence_id
        or check.get("page_sequence") != match.get("page_sequence")
        or check.get("role") != retrieval_role
        or check.get("role_kind") != retrieval_role_kind
        or check.get("within_role") != retrieval_within_role
        or check.get("source_line_indices") != expected_indices
        or type(check.get("retrieval_channel")) is not dict
        or check["retrieval_channel"].get("match_kind") != match.get("match_kind")
        or check["retrieval_channel"].get("surface") != match.get("surface")
        or type(check.get("exact_channel")) is not dict
        or type(check["exact_channel"].get("alias_normalized")) is not str
        or not check["exact_channel"]["alias_normalized"]
        or check["exact_channel"].get("context_binding", {}).get("occurrence_id")
        != retrieval_occurrence_id
        or check["exact_channel"].get("context_binding", {}).get("scope_owner_occurrence_id")
        != match.get("retrieval_scope_owner_occurrence_id")
    ):
        return None
    return check


def _match_has_effective_exact_source_authority(match: Mapping[str, Any]) -> bool:
    return str(match.get("match_kind", "")).startswith("EXACT_") or (
        str(match.get("match_kind", "")).startswith("ONE_EDIT_")
        and _bound_one_edit_exact_source_check(match) is not None
    )


def _project_reviewed_schema_source_scopes(
    pages: Sequence[Mapping[str, Any]],
    compiled_family: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]],
    selected_region: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Type only generic rows with one exact, reviewed semantic source scope.

    The topology matcher remains retrieval-only for bare discount/provision
    labels.  This V2 adapter uses their exact position among already selected
    semantic occurrences; it never changes the sealed V1 structural-group
    assignment heuristic and never guesses by a repeated-label ordinal.
    """

    by_role_definition = {child["role"]: child for child in compiled_family["children"]}
    projected = _attach_schema_scope_source_label_bboxes(pages, compiled_family, matches)
    if not _SCHEMA_SCOPE_REQUIRED_ROLES <= set(by_role_definition):
        return projected
    for match in projected:
        binding = match.get("source_scope_binding")
        if type(binding) is dict and binding.get("status") == _AMBIGUOUS_WRAPPED_LABEL_STATUS:
            match["source_scope_binding"] = _scope_binding(
                anchor=None,
                binding_kind=binding["binding_kind"],
                geometry=binding["geometry"],
                interval_end_exclusive=binding["interval"]["end_document_line_ordinal_exclusive"],
                interval_start=binding["interval"]["start_document_line_ordinal"],
                source=match,
                source_role=binding["source_role"],
                source_scope_role=binding["source_scope_role"],
                status=_AMBIGUOUS_WRAPPED_LABEL_STATUS,
                target_role=binding["target_role"],
            )

    def retype(
        match: dict[str, Any],
        target_role: str,
        receipt: Mapping[str, Any],
        *,
        matched_within_role: str | None,
    ) -> None:
        definition = by_role_definition[target_role]
        match.update(
            {
                "matched_within_role": matched_within_role,
                "preferred_ordinal": definition["preferred_ordinal"],
                "presence": definition["presence"],
                "role": target_role,
                "role_kind": definition["role_kind"],
                "source_scope_binding": canonical_clone_v1(receipt),
            }
        )

    region_end = selected_region["cluster_end_document_line_ordinal_exclusive"]
    loan_groups = sorted(
        (match for match in projected if match["role"] == "INTERBANK_LOAN_GROUP"),
        key=lambda item: item["document_line_ordinal"],
    )

    def explicit_total_definition(
        match: Mapping[str, Any],
    ) -> tuple[str, str, str] | None:
        role = match.get("role")
        if role in _EXPLICIT_GROUP_TOTAL_SOURCE_TARGETS:
            target, owner = _EXPLICIT_GROUP_TOTAL_SOURCE_TARGETS[role]
            return role, target, owner
        if role in _EXPLICIT_GROUP_TOTAL_TARGET_SOURCES:
            source, owner = _EXPLICIT_GROUP_TOTAL_TARGET_SOURCES[role]
            return source, role, owner
        return None

    def downgrade_explicit_total(match: dict[str, Any], source_role: str) -> None:
        definition = by_role_definition[source_role]
        match.update(
            {
                "matched_within_role": None,
                "preferred_ordinal": definition["preferred_ordinal"],
                "presence": definition["presence"],
                "role": source_role,
                "role_kind": definition["role_kind"],
                "source_scope_binding": None,
            }
        )

    if _EXPLICIT_GROUP_TOTAL_ROLES <= set(by_role_definition):

        def physical_total_key(match: Mapping[str, Any]) -> tuple[Any, ...]:
            explicit_indices = match.get("source_line_indices")
            return (
                match["page_sequence"],
                match["document_line_ordinal"],
                match["end_document_line_ordinal"],
                tuple(
                    explicit_indices
                    if type(explicit_indices) is list
                    else range(
                        match["source_line_index"],
                        match["end_source_line_index"] + 1,
                    )
                ),
                match["normalized_surface"],
            )

        # The contextual and retrieval-only aliases deliberately share exact
        # surfaces.  Keep one physical occurrence, preferring the contextual
        # role when legacy topology could bind it.  Distinct physical rows are
        # never collapsed, so a repeated explicit total still fails closed.
        total_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        for candidate in projected:
            if explicit_total_definition(candidate) is not None:
                total_groups.setdefault(physical_total_key(candidate), []).append(candidate)
        total_matches = []
        superseded_total_ids: set[int] = set()
        for group in total_groups.values():
            contextual = [
                candidate
                for candidate in group
                if candidate["role"] in _EXPLICIT_GROUP_TOTAL_TARGET_SOURCES
                and candidate.get("matched_within_role") is not None
            ]
            winner = min(
                contextual or group,
                key=lambda candidate: (
                    not _match_has_effective_exact_source_authority(candidate),
                    candidate["preferred_ordinal"],
                    candidate["role"],
                ),
            )
            total_matches.append(winner)
            superseded_total_ids.update(
                id(candidate) for candidate in group if candidate is not winner
            )
        if superseded_total_ids:
            projected = [
                candidate for candidate in projected if id(candidate) not in superseded_total_ids
            ]

        top_boundary_roles = {
            "EXPLICIT_FAMILY_TOTAL",
            "INTERBANK_DEPOSIT_GROUP",
            "INTERBANK_LOAN_GROUP",
        }
        for match in total_matches:
            definition = explicit_total_definition(match)
            if definition is None:
                continue
            source_role, target_role, owner_role = definition
            source_ordinal = match["document_line_ordinal"]
            page_sequence = match["page_sequence"]
            exact_source = _match_has_effective_exact_source_authority(match)
            preceding_top = [
                item
                for item in projected
                if item["role"] in {"INTERBANK_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"}
                and item["page_sequence"] == page_sequence
                and item["document_line_ordinal"] < source_ordinal
            ]
            nearest_owner_ordinal = max(
                (item["document_line_ordinal"] for item in preceding_top),
                default=None,
            )
            nearest_owners = [
                item
                for item in preceding_top
                if item["document_line_ordinal"] == nearest_owner_ordinal
            ]
            owner = nearest_owners[0] if len(nearest_owners) == 1 else None
            exact_owner = (
                owner is not None
                and owner["role"] == owner_role
                and _match_has_effective_exact_source_authority(owner)
            )
            later_boundaries = [
                item
                for item in projected
                if item["role"] in top_boundary_roles
                and item["page_sequence"] == page_sequence
                and item["document_line_ordinal"] > source_ordinal
            ]
            nearest_boundary_ordinal = min(
                (item["document_line_ordinal"] for item in later_boundaries),
                default=None,
            )
            nearest_boundaries = [
                item
                for item in later_boundaries
                if item["document_line_ordinal"] == nearest_boundary_ordinal
            ]
            boundary = nearest_boundaries[0] if len(nearest_boundaries) == 1 else None
            exact_boundary = boundary is not None and _match_has_effective_exact_source_authority(
                boundary
            )
            retrieval_role = match.get("retrieval_role", match.get("role"))
            retrieval_owner_matches_interval_owner = (
                retrieval_role == source_role
                or owner is not None
                and match.get("retrieval_scope_owner_occurrence_id") == owner.get("occurrence_id")
            )
            interval_totals = [
                item
                for item in total_matches
                if owner is not None
                and boundary is not None
                and explicit_total_definition(item) is not None
                and explicit_total_definition(item)[1] == target_role
                and item["page_sequence"] == page_sequence
                and owner["document_line_ordinal"]
                < item["document_line_ordinal"]
                < boundary["document_line_ordinal"]
            ]
            semantic_roles = (
                _DEPOSIT_SEMANTIC_INTERVAL_ROLES
                if owner_role == "INTERBANK_DEPOSIT_GROUP"
                else _LOAN_SEMANTIC_INTERVAL_ROLES
            )
            prior_semantics = [
                item
                for item in projected
                if owner is not None
                and item["role"] in semantic_roles
                and item["role"] != owner_role
                and item["page_sequence"] == page_sequence
                and owner["document_line_ordinal"] < item["document_line_ordinal"] < source_ordinal
                and _match_has_effective_exact_source_authority(item)
            ]
            later_semantics = [
                item
                for item in projected
                if boundary is not None
                and item["role"] in semantic_roles
                and item["page_sequence"] == page_sequence
                and source_ordinal
                < item["document_line_ordinal"]
                < boundary["document_line_ordinal"]
            ]
            proved = (
                exact_source
                and exact_owner
                and exact_boundary
                and retrieval_owner_matches_interval_owner
                and len(interval_totals) == 1
                and interval_totals[0] is match
                and bool(prior_semantics)
                and not later_semantics
            )
            if not proved:
                if match["role"] == target_role:
                    downgrade_explicit_total(match, source_role)
                continue
            receipt = _scope_binding(
                anchor=owner,
                binding_kind=_EXPLICIT_GROUP_TOTAL_BINDING_KIND,
                geometry={
                    "anchor_occurrence_id": owner["occurrence_id"],
                    "status": _EXPLICIT_GROUP_TOTAL_PARENT_GEOMETRY_STATUS,
                },
                interval_end_exclusive=boundary["document_line_ordinal"],
                interval_start=owner["document_line_ordinal"],
                source=match,
                anchor_exact_source_authority_check=_bound_one_edit_exact_source_check(owner),
                source_exact_source_authority_check=_bound_one_edit_exact_source_check(match),
                source_role=match.get("retrieval_role", match["role"]),
                source_scope_role=owner_role,
                target_role=target_role,
            )
            retype(match, target_role, receipt, matched_within_role=owner_role)

    currency_scopes = sorted(
        (match for match in projected if match["role"] in _DISCOUNT_SCOPE_TARGETS),
        key=lambda item: (
            item["document_line_ordinal"],
            item["end_document_line_ordinal"],
            item["role"],
        ),
    )
    generic_discount_sources = [
        match
        for match in projected
        if match["role"] == _DISCOUNT_GENERIC_ROLE and str(match["match_kind"]).startswith("EXACT_")
    ]

    # Explicit currency words are independently sufficient source-subscope
    # evidence.  Persist the same reviewed receipt shape used by interval-bound
    # generic rows so the schema mapper can fail closed on a missing/tampered
    # source-scope proof.
    for match in projected:
        reverse_scope = {target: scope for scope, target in _DISCOUNT_SCOPE_TARGETS.items()}
        source_scope_role = reverse_scope.get(match["role"])
        if source_scope_role is None or not _match_has_effective_exact_source_authority(match):
            continue
        match["source_scope_binding"] = _scope_binding(
            anchor=None,
            binding_kind="EXPLICIT_EXACT_SOURCE_SUBSCOPE_IN_LABEL",
            geometry=None,
            interval_end_exclusive=match["end_document_line_ordinal"] + 1,
            interval_start=match["document_line_ordinal"],
            source=match,
            source_exact_source_authority_check=_bound_one_edit_exact_source_check(match),
            source_role=match["role"],
            source_scope_role=source_scope_role,
            target_role=match["role"],
        )

    for match in projected:
        if match["role"] != _DISCOUNT_GENERIC_ROLE or not str(match["match_kind"]).startswith(
            "EXACT_"
        ):
            continue
        preceding_loan = [
            group
            for group in loan_groups
            if group["page_sequence"] == match["page_sequence"]
            and group["document_line_ordinal"] <= match["document_line_ordinal"]
        ]
        if not preceding_loan:
            continue
        loan = max(preceding_loan, key=lambda item: item["document_line_ordinal"])
        next_loan = min(
            (
                group["document_line_ordinal"]
                for group in loan_groups
                if group["document_line_ordinal"] > match["document_line_ordinal"]
            ),
            default=region_end,
        )
        preceding_scopes = [
            scope
            for scope in currency_scopes
            if scope["page_sequence"] == match["page_sequence"]
            and loan["document_line_ordinal"] <= scope["document_line_ordinal"]
            and scope["end_document_line_ordinal"] < match["document_line_ordinal"]
            and scope["document_line_ordinal"] < next_loan
        ]
        if not preceding_scopes:
            continue
        nearest_end = max(scope["end_document_line_ordinal"] for scope in preceding_scopes)
        nearest = [
            scope for scope in preceding_scopes if scope["end_document_line_ordinal"] == nearest_end
        ]
        if len({scope["role"] for scope in nearest}) != 1 or not all(
            _match_has_effective_exact_source_authority(scope) for scope in nearest
        ):
            continue
        anchor = max(nearest, key=lambda item: item["document_line_ordinal"])
        non_generic_boundaries = [
            sibling["document_line_ordinal"]
            for sibling in projected
            if sibling is not match
            and sibling["role"] in _LOAN_SOURCE_SUBSCOPE_BOUNDARY_ROLES
            and sibling["role"] != _DISCOUNT_GENERIC_ROLE
            and anchor["end_document_line_ordinal"] < sibling["document_line_ordinal"] < next_loan
        ]
        source_subscope_end = min(non_generic_boundaries, default=next_loan)
        interval_generic_discounts = [
            source
            for source in generic_discount_sources
            if anchor["end_document_line_ordinal"]
            < source["document_line_ordinal"]
            < source_subscope_end
        ]
        intervening_loan_siblings = [
            sibling
            for sibling in projected
            if sibling is not match
            and sibling["role"] in _LOAN_SOURCE_SUBSCOPE_BOUNDARY_ROLES
            and anchor["end_document_line_ordinal"]
            < sibling["document_line_ordinal"]
            < match["document_line_ordinal"]
            and sibling["document_line_ordinal"] < next_loan
        ]
        target_role = _DISCOUNT_SCOPE_TARGETS[anchor["role"]]
        explicit_same_target = [
            sibling
            for sibling in projected
            if sibling is not match
            and sibling["role"] == target_role
            and loan["document_line_ordinal"] <= sibling["document_line_ordinal"] < next_loan
        ]
        if (
            intervening_loan_siblings
            or len(interval_generic_discounts) != 1
            or explicit_same_target
        ):
            continue
        receipt = _scope_binding(
            anchor=anchor,
            anchor_exact_source_authority_check=_bound_one_edit_exact_source_check(anchor),
            binding_kind="UNIQUE_EXACT_PRECEDING_SOURCE_SUBSCOPE_INTERVAL",
            geometry=None,
            interval_end_exclusive=match["end_document_line_ordinal"] + 1,
            interval_start=anchor["document_line_ordinal"],
            source=match,
            source_role=_DISCOUNT_GENERIC_ROLE,
            source_scope_role=anchor["role"],
            target_role=target_role,
        )
        retype(match, target_role, receipt, matched_within_role=anchor["role"])

    deposit_matches = sorted(
        (match for match in projected if match["role"] in _DEPOSIT_SCOPE_ROLES),
        key=lambda item: item["document_line_ordinal"],
    )
    generic_provision_sources = [
        match
        for match in projected
        if match["role"] == _PROVISION_GENERIC_ROLE
        and str(match["match_kind"]).startswith("EXACT_")
    ]
    for match in projected:
        if match["role"] != _PROVISION_GENERIC_ROLE or not str(match["match_kind"]).startswith(
            "EXACT_"
        ):
            continue
        before = match["document_line_ordinal"]
        prior_deposits = [
            item
            for item in deposit_matches
            if item["page_sequence"] == match["page_sequence"]
            and item["document_line_ordinal"] < before
            and _match_has_effective_exact_source_authority(item)
        ]
        active_deposit_groups = [
            item for item in prior_deposits if item["role"] == "INTERBANK_DEPOSIT_GROUP"
        ]
        if active_deposit_groups:
            active_deposit_start = max(
                item["document_line_ordinal"] for item in active_deposit_groups
            )
            prior_deposits = [
                item
                for item in prior_deposits
                if item["document_line_ordinal"] >= active_deposit_start
            ]
        prior_loans = [
            item
            for item in loan_groups
            if item["page_sequence"] == match["page_sequence"]
            and item["document_line_ordinal"] < before
        ]
        later_loans = [
            item
            for item in loan_groups
            if item["page_sequence"] == match["page_sequence"]
            and item["document_line_ordinal"] > before
        ]
        if prior_deposits and not prior_loans and later_loans:
            next_loan_ordinal = min(item["document_line_ordinal"] for item in later_loans)
            deposit_interval_start = min(item["document_line_ordinal"] for item in prior_deposits)
            prior_explicit_group_totals = [
                item
                for item in projected
                if item["role"] in _EXPLICIT_GROUP_TOTAL_ROLES
                and deposit_interval_start
                < item["document_line_ordinal"]
                < match["document_line_ordinal"]
            ]
            interval_provisions = [
                item
                for item in generic_provision_sources
                if deposit_interval_start <= item["document_line_ordinal"] < next_loan_ordinal
            ]
            explicit_interval_provisions = [
                item
                for item in projected
                if item is not match
                and item["role"] == "INTERBANK_DEPOSIT_PROVISION"
                and deposit_interval_start <= item["document_line_ordinal"] < next_loan_ordinal
            ]
            if (
                any(
                    before < item["document_line_ordinal"] < next_loan_ordinal
                    and (
                        item["role"] in _DEPOSIT_SEMANTIC_INTERVAL_ROLES
                        or item["role"] in _LOAN_SEMANTIC_INTERVAL_ROLES
                    )
                    for item in projected
                    if item is not match
                )
                or prior_explicit_group_totals
                or len(interval_provisions) != 1
                or explicit_interval_provisions
            ):
                continue
            anchor = max(
                prior_deposits,
                key=lambda item: (
                    item["document_line_ordinal"],
                    item["end_document_line_ordinal"],
                    item["preferred_ordinal"],
                    item["role"],
                ),
            )
            if not _match_has_effective_exact_source_authority(anchor):
                continue
            receipt = _scope_binding(
                anchor=anchor,
                anchor_exact_source_authority_check=_bound_one_edit_exact_source_check(anchor),
                binding_kind="EXACT_DEPOSIT_SUBTREE_BEFORE_NEXT_LOAN_BOUNDARY",
                geometry=None,
                interval_end_exclusive=next_loan_ordinal,
                interval_start=deposit_interval_start,
                source=match,
                source_role=_PROVISION_GENERIC_ROLE,
                source_scope_role="INTERBANK_DEPOSIT_GROUP",
                target_role="INTERBANK_DEPOSIT_PROVISION",
            )
            deposit_group = next(
                (
                    item
                    for item in reversed(prior_deposits)
                    if item["role"] == "INTERBANK_DEPOSIT_GROUP"
                ),
                None,
            )
            retype(
                match,
                "INTERBANK_DEPOSIT_PROVISION",
                receipt,
                matched_within_role=(
                    "INTERBANK_DEPOSIT_GROUP" if deposit_group is not None else None
                ),
            )
            continue
        if prior_deposits and prior_loans and not later_loans:
            loan = max(prior_loans, key=lambda item: item["document_line_ordinal"])
            prior_explicit_group_totals = [
                item
                for item in projected
                if item["role"] in _EXPLICIT_GROUP_TOTAL_ROLES
                and loan["document_line_ordinal"]
                < item["document_line_ordinal"]
                < match["document_line_ordinal"]
            ]
            root_interval_provisions = [
                item
                for item in generic_provision_sources
                if loan["document_line_ordinal"] <= item["document_line_ordinal"] < region_end
            ]
            explicit_root_interval_provisions = [
                item
                for item in projected
                if item is not match
                and item["role"] == "TOTAL_INTERBANK_PROVISION"
                and loan["document_line_ordinal"] <= item["document_line_ordinal"] < region_end
            ]
            prior_loan_leaves = [
                item
                for item in projected
                if item["role"] in _LOAN_LEAF_ROLES
                and loan["document_line_ordinal"] <= item["document_line_ordinal"] < before
                and _match_has_effective_exact_source_authority(item)
            ]
            later_loan_leaves = [
                item
                for item in projected
                if item["role"] in _LOAN_LEAF_ROLES
                and before < item["document_line_ordinal"] < region_end
            ]
            later_loan_semantics = [
                item
                for item in projected
                if item is not match
                and item["role"] in _LOAN_SEMANTIC_INTERVAL_ROLES
                and before < item["document_line_ordinal"] < region_end
            ]
            later_deposit_roles = [
                item
                for item in projected
                if item is not match
                and item["role"] in _DEPOSIT_SEMANTIC_INTERVAL_ROLES
                and before < item["document_line_ordinal"] < region_end
            ]
            all_loan_leaves = [
                item
                for item in projected
                if item["role"] in _LOAN_LEAF_ROLES
                and loan["document_line_ordinal"] <= item["document_line_ordinal"] < region_end
            ]
            exact_group_total_without_leaf_labels = (
                not all_loan_leaves
                and _same_row_numeric_samples_are_complete(pages, loan, projected)
            )
            if (not prior_loan_leaves and not exact_group_total_without_leaf_labels) or (
                len(root_interval_provisions) != 1
                or explicit_root_interval_provisions
                or prior_explicit_group_totals
                or later_loan_leaves
                or later_loan_semantics
                or later_deposit_roles
            ):
                continue
            if not _match_has_effective_exact_source_authority(loan):
                continue
            source_bbox = match["source_label_bbox"]
            loan_bbox = loan["source_label_bbox"]
            absolute_left_delta = abs(source_bbox[0] - loan_bbox[0])
            maximum_delta = max(source_bbox[3] - source_bbox[1], loan_bbox[3] - loan_bbox[1])
            if absolute_left_delta > maximum_delta:
                continue
            geometry = {
                "absolute_left_delta": absolute_left_delta,
                "anchor_left": loan_bbox[0],
                "maximum_root_sibling_left_delta": maximum_delta,
                "source_left": source_bbox[0],
                "status": "EXACT_ROOT_SIBLING_ALIGNMENT_WITHIN_ONE_LABEL_HEIGHT",
            }
            receipt = _scope_binding(
                anchor=loan,
                anchor_exact_source_authority_check=_bound_one_edit_exact_source_check(loan),
                binding_kind="EXACT_TOP_SIBLING_AFTER_COMPLETE_DEPOSIT_AND_LOAN_SUBTREES",
                geometry=geometry,
                interval_end_exclusive=region_end,
                interval_start=loan["document_line_ordinal"],
                source=match,
                source_role=_PROVISION_GENERIC_ROLE,
                source_scope_role=compiled_family["family_id"],
                target_role="TOTAL_INTERBANK_PROVISION",
            )
            retype(match, "TOTAL_INTERBANK_PROVISION", receipt, matched_within_role=None)

    projected.sort(
        key=lambda item: (
            item["document_line_ordinal"],
            item["end_document_line_ordinal"],
            item["preferred_ordinal"],
            item["role"],
        )
    )
    ordinals: dict[str, int] = {}
    for match in projected:
        ordinal = ordinals.get(match["role"], 0)
        match["role_occurrence_ordinal"] = ordinal
        ordinals[match["role"]] = ordinal + 1
    return projected


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

    def parent_precedes(candidate: Mapping[str, Any], child: Mapping[str, Any]) -> bool:
        if candidate["document_line_ordinal"] <= child["document_line_ordinal"]:
            return True
        candidate_bbox = candidate.get("source_label_bbox")
        child_bbox = child.get("source_label_bbox")
        if (
            candidate["page_sequence"] != child["page_sequence"]
            or type(candidate_bbox) is not list
            or type(child_bbox) is not list
        ):
            return False
        text_height = max(
            candidate_bbox[3] - candidate_bbox[1],
            child_bbox[3] - child_bbox[1],
        )
        vertical_gap = child_bbox[1] - candidate_bbox[3]
        return (
            candidate_bbox[1] <= child_bbox[1]
            and candidate_bbox[3] <= child_bbox[3]
            and 2 * vertical_gap >= -text_height
        )

    def parent_order(candidate: Mapping[str, Any]) -> tuple[int, int, int, int]:
        bbox = candidate.get("source_label_bbox")
        return (
            candidate["page_sequence"],
            bbox[1] if type(bbox) is list else candidate["document_line_ordinal"],
            bbox[3] if type(bbox) is list else candidate["end_document_line_ordinal"],
            candidate["document_line_ordinal"],
        )

    for match in decorated:
        within_role = match.get("matched_within_role")
        parents = [
            candidate
            for candidate in decorated
            if candidate["role"] == within_role
            and parent_precedes(candidate, match)
            and candidate["occurrence_id"] != match["occurrence_id"]
        ]
        owner = max(
            parents,
            key=parent_order,
            default=None,
        )
        if within_role is not None and owner is None:
            raise _error("context-bound role occurrence lost its nearest structural parent")
        match["scope_owner_occurrence_id"] = (
            owner["occurrence_id"] if owner is not None else root_scope_id
        )
        match["scope_owner_role"] = owner["role"] if owner is not None else None
    return decorated


def _validate_source_scope_binding(
    value: Any, *, label_match: Mapping[str, Any], role: str
) -> None:
    if value is None:
        return
    expected_source_span = _source_span(label_match)
    if type(value) is dict and type(value.get("source_role")) is str:
        expected_source_span["role"] = value["source_role"]
    if (
        type(value) is not dict
        or set(value) != _SOURCE_SCOPE_BINDING_FIELDS
        or value["status"] not in {_SOURCE_SCOPE_BINDING_STATUS, _AMBIGUOUS_WRAPPED_LABEL_STATUS}
        or type(value["binding_kind"]) is not str
        or not value["binding_kind"]
        or type(value["source_role"]) is not str
        or not value["source_role"]
        or type(value["source_scope_role"]) is not str
        or not value["source_scope_role"]
        or value["target_role"] != role
        or type(value["source_span"]) is not dict
        or not same_typed_json_v1(value["source_span"], expected_source_span)
        or type(value["source_span"].get("source_label_bbox")) is not list
        or len(value["source_span"]["source_label_bbox"]) != 4
        or any(
            type(coordinate) is not int for coordinate in value["source_span"]["source_label_bbox"]
        )
        or (value["anchor_span"] is not None and type(value["anchor_span"]) is not dict)
        or (
            value["anchor_exact_source_authority_check"] is not None
            and type(value["anchor_exact_source_authority_check"]) is not dict
        )
        or (
            value["source_exact_source_authority_check"] is not None
            and type(value["source_exact_source_authority_check"]) is not dict
        )
        or (
            type(value["anchor_span"]) is dict
            and (
                type(value["anchor_span"].get("source_label_bbox")) is not list
                or len(value["anchor_span"]["source_label_bbox"]) != 4
                or any(
                    type(coordinate) is not int
                    for coordinate in value["anchor_span"]["source_label_bbox"]
                )
            )
        )
        or (value["geometry"] is not None and type(value["geometry"]) is not dict)
        or type(value["interval"]) is not dict
        or set(value["interval"])
        != {"end_document_line_ordinal_exclusive", "start_document_line_ordinal"}
        or type(value["interval"]["start_document_line_ordinal"]) is not int
        or type(value["interval"]["end_document_line_ordinal_exclusive"]) is not int
        or not (
            value["interval"]["start_document_line_ordinal"]
            <= label_match["document_line_ordinal"]
            < value["interval"]["end_document_line_ordinal_exclusive"]
        )
    ):
        raise _error("reviewed schema source-scope binding drifted")
    anchor = value["anchor_span"]
    interval = value["interval"]
    geometry = value["geometry"]
    source_check = value["source_exact_source_authority_check"]
    anchor_check = value["anchor_exact_source_authority_check"]
    bound_label_check = _bound_one_edit_exact_source_check(label_match)
    exact_source = str(value["source_span"].get("match_kind", "")).startswith("EXACT_") or (
        type(source_check) is dict
        and type(bound_label_check) is dict
        and same_typed_json_v1(source_check, bound_label_check)
    )
    exact_anchor = type(anchor) is dict and (
        str(anchor.get("match_kind", "")).startswith("EXACT_")
        or (
            type(anchor_check) is dict
            and anchor_check.get("status") == _ONE_EDIT_EXACT_BOUND_STATUS
            and anchor_check.get("match_scope") == "EXPANDED_OCCURRENCE"
            and anchor_check.get("page_sequence") == anchor.get("page_sequence")
            and anchor_check.get("role") == anchor.get("role")
            and anchor_check.get("source_line_indices") == anchor.get("source_line_indices")
            and anchor_check.get("retrieval_channel", {}).get("match_kind")
            == anchor.get("match_kind")
        )
    )
    source_proof_shape_valid = (
        str(value["source_span"].get("match_kind", "")).startswith("EXACT_")
        and source_check is None
    ) or (
        str(value["source_span"].get("match_kind", "")).startswith("ONE_EDIT_")
        and type(source_check) is dict
        and type(bound_label_check) is dict
        and same_typed_json_v1(source_check, bound_label_check)
    )
    anchor_proof_shape_valid = (
        anchor is None
        and anchor_check is None
        or (
            type(anchor) is dict
            and (
                str(anchor.get("match_kind", "")).startswith("EXACT_")
                and anchor_check is None
                or str(anchor.get("match_kind", "")).startswith("ONE_EDIT_")
                and type(anchor_check) is dict
                and exact_anchor
            )
        )
    )
    discount_pair = {
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND": "INTERBANK_LOAN_VND",
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY": ("INTERBANK_LOAN_FOREIGN_CURRENCY"),
    }
    kind = value["binding_kind"]
    reviewed_matrix_valid = False
    if value["status"] == _SOURCE_SCOPE_BINDING_STATUS:
        expected_subscope = discount_pair.get(role)
        if kind == _EXPLICIT_GROUP_TOTAL_BINDING_KIND:
            explicit_total_source = _EXPLICIT_GROUP_TOTAL_TARGET_SOURCES.get(role)
            retrieval_role = label_match.get("retrieval_role", label_match.get("role"))
            retrieval_within_role = label_match.get(
                "retrieval_within_role", label_match.get("matched_within_role")
            )
            retrieval_scope_owner_occurrence_id = label_match.get(
                "retrieval_scope_owner_occurrence_id"
            )
            explicit_total_parent_geometry_valid = (
                type(geometry) is dict
                and set(geometry) == {"anchor_occurrence_id", "status"}
                and geometry["status"] == _EXPLICIT_GROUP_TOTAL_PARENT_GEOMETRY_STATUS
                and type(geometry["anchor_occurrence_id"]) is str
                and bool(geometry["anchor_occurrence_id"])
            )
            reviewed_matrix_valid = (
                explicit_total_source is not None
                and value["source_role"] == retrieval_role
                and (
                    retrieval_role == explicit_total_source[0]
                    and retrieval_within_role is None
                    or retrieval_role == role
                    and retrieval_within_role == explicit_total_source[1]
                    and type(retrieval_scope_owner_occurrence_id) is str
                    and explicit_total_parent_geometry_valid
                    and retrieval_scope_owner_occurrence_id == geometry["anchor_occurrence_id"]
                )
                and value["source_scope_role"] == explicit_total_source[1]
                and exact_source
                and exact_anchor
                and source_proof_shape_valid
                and anchor_proof_shape_valid
                and anchor.get("role") == explicit_total_source[1]
                and explicit_total_parent_geometry_valid
                and interval["start_document_line_ordinal"] == anchor["document_line_ordinal"]
                and interval["end_document_line_ordinal_exclusive"]
                > label_match["document_line_ordinal"]
            )
        elif kind == "EXPLICIT_EXACT_SOURCE_SUBSCOPE_IN_LABEL":
            normalized = value["source_span"]["normalized_surface"]
            explicit_scope_surface = (
                "bang vnd" in normalized
                if expected_subscope == "INTERBANK_LOAN_VND"
                else ("bang ngoai te" in normalized or "bang ngoai hoi" in normalized)
            )
            reviewed_matrix_valid = (
                expected_subscope is not None
                and value["source_role"] == role
                and value["source_scope_role"] == expected_subscope
                and exact_source
                and source_proof_shape_valid
                and anchor_proof_shape_valid
                and explicit_scope_surface
                and anchor is None
                and value["anchor_exact_source_authority_check"] is None
                and geometry is None
                and interval["start_document_line_ordinal"] == label_match["document_line_ordinal"]
                and interval["end_document_line_ordinal_exclusive"]
                == label_match["end_document_line_ordinal"] + 1
            )
        elif kind == "UNIQUE_EXACT_PRECEDING_SOURCE_SUBSCOPE_INTERVAL":
            reviewed_matrix_valid = (
                expected_subscope is not None
                and value["source_role"] == _DISCOUNT_GENERIC_ROLE
                and value["source_scope_role"] == expected_subscope
                and exact_source
                and exact_anchor
                and source_proof_shape_valid
                and anchor_proof_shape_valid
                and anchor.get("role") == expected_subscope
                and geometry is None
                and anchor["end_document_line_ordinal"] < label_match["document_line_ordinal"]
                and interval["start_document_line_ordinal"] == anchor["document_line_ordinal"]
            )
        elif kind == "EXACT_DEPOSIT_SUBTREE_BEFORE_NEXT_LOAN_BOUNDARY":
            reviewed_matrix_valid = (
                role == "INTERBANK_DEPOSIT_PROVISION"
                and value["source_role"] == _PROVISION_GENERIC_ROLE
                and value["source_scope_role"] == "INTERBANK_DEPOSIT_GROUP"
                and exact_source
                and exact_anchor
                and source_proof_shape_valid
                and anchor_proof_shape_valid
                and anchor.get("role") in _DEPOSIT_SCOPE_ROLES
                and geometry is None
                and anchor["document_line_ordinal"] < label_match["document_line_ordinal"]
            )
        elif kind == "EXACT_TOP_SIBLING_AFTER_COMPLETE_DEPOSIT_AND_LOAN_SUBTREES":
            reviewed_matrix_valid = (
                role == "TOTAL_INTERBANK_PROVISION"
                and value["source_role"] == _PROVISION_GENERIC_ROLE
                and value["source_scope_role"] == "INTERBANK_DEPOSITS_AND_LOANS"
                and exact_source
                and exact_anchor
                and source_proof_shape_valid
                and anchor_proof_shape_valid
                and anchor.get("role") == "INTERBANK_LOAN_GROUP"
                and type(geometry) is dict
                and set(geometry)
                == {
                    "absolute_left_delta",
                    "anchor_left",
                    "maximum_root_sibling_left_delta",
                    "source_left",
                    "status",
                }
                and geometry["status"] == "EXACT_ROOT_SIBLING_ALIGNMENT_WITHIN_ONE_LABEL_HEIGHT"
                and all(
                    type(geometry[field]) is int
                    for field in (
                        "absolute_left_delta",
                        "anchor_left",
                        "maximum_root_sibling_left_delta",
                        "source_left",
                    )
                )
                and geometry["absolute_left_delta"]
                == abs(geometry["source_left"] - geometry["anchor_left"])
                and geometry["source_left"] == value["source_span"]["source_label_bbox"][0]
                and geometry["anchor_left"] == anchor["source_label_bbox"][0]
                and geometry["maximum_root_sibling_left_delta"]
                == max(
                    value["source_span"]["source_label_bbox"][3]
                    - value["source_span"]["source_label_bbox"][1],
                    anchor["source_label_bbox"][3] - anchor["source_label_bbox"][1],
                )
                and 0
                <= geometry["absolute_left_delta"]
                <= geometry["maximum_root_sibling_left_delta"]
                and interval["start_document_line_ordinal"] == anchor["document_line_ordinal"]
            )
    ambiguous_matrix_valid = False
    if value["status"] == _AMBIGUOUS_WRAPPED_LABEL_STATUS:
        if type(geometry) is dict and set(geometry) == {
            "absolute_left_delta",
            "candidate_bbox",
            "candidate_source_line_index",
            "preceding_bbox",
            "preceding_source_line_index",
            "skipped_source_line_indices",
            "vertical_gap",
        }:
            candidate_bbox = geometry["candidate_bbox"]
            preceding_bbox = geometry["preceding_bbox"]
            valid_bboxes = all(
                type(bbox) is list and len(bbox) == 4 and all(type(item) is int for item in bbox)
                for bbox in (candidate_bbox, preceding_bbox)
            )
            text_height = (
                max(
                    preceding_bbox[3] - preceding_bbox[1],
                    candidate_bbox[3] - candidate_bbox[1],
                )
                if valid_bboxes
                else -1
            )
            ambiguous_matrix_valid = (
                valid_bboxes
                and role.endswith("_OTHER")
                and value["source_role"] == role
                and value["target_role"] == role
                and value["source_scope_role"]
                in {"INTERBANK_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"}
                and kind == "AMBIGUOUS_TOUCHING_PRECEDING_LABEL_FRAGMENT"
                and anchor is None
                and value["anchor_exact_source_authority_check"] is None
                and value["source_exact_source_authority_check"] is None
                and exact_source
                and source_proof_shape_valid
                and anchor_proof_shape_valid
                and type(geometry["absolute_left_delta"]) is int
                and geometry["absolute_left_delta"] == abs(preceding_bbox[0] - candidate_bbox[0])
                and geometry["absolute_left_delta"] <= 6
                and geometry["candidate_source_line_index"] == label_match["source_line_index"]
                and candidate_bbox == value["source_span"]["source_label_bbox"]
                and type(geometry["preceding_source_line_index"]) is int
                and geometry["preceding_source_line_index"]
                < geometry["candidate_source_line_index"]
                and type(geometry["skipped_source_line_indices"]) is list
                and geometry["skipped_source_line_indices"]
                == list(
                    range(
                        geometry["preceding_source_line_index"] + 1,
                        geometry["candidate_source_line_index"],
                    )
                )
                and geometry["vertical_gap"] == candidate_bbox[1] - preceding_bbox[3]
                and 2 * geometry["vertical_gap"] >= -text_height
                and 4 * geometry["vertical_gap"] <= text_height
                and interval["start_document_line_ordinal"]
                == (
                    label_match["document_line_ordinal"]
                    - label_match["source_line_index"]
                    + geometry["preceding_source_line_index"]
                )
                and interval["end_document_line_ordinal_exclusive"]
                == label_match["end_document_line_ordinal"] + 1
            )
    if not (reviewed_matrix_valid or ambiguous_matrix_valid):
        raise _error("schema source-scope binding status and semantic matrix drifted")
    material = canonical_clone_v1(value)
    binding_id = material.pop("binding_id")
    if binding_id != "aforav2:scope-binding:" + canonical_json_sha256_v1(material):
        raise _error("reviewed schema source-scope binding identity drifted")


def _expanded_region(
    effective_region: Mapping[str, Any], matches: list[dict[str, Any]]
) -> dict[str, Any]:
    result = canonical_clone_v1(effective_region)
    result["child_matches"] = canonical_clone_v1(matches)
    result["observed_roles"] = list(dict.fromkeys(match["role"] for match in matches))
    return result


def _one_edit_authority_pages_v2(
    pages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Expose the independent PP-OCR source channel on identical line spans."""

    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "numeric_recognition": canonical_clone_v1(line["numeric_recognition"]),
                    "source_line_index": line["line_ordinal"],
                    "source_text": line["numeric_recognition"]["raw_prediction"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
            "page_width": page.get("page_width"),
        }
        for page in pages
    ]


def _one_edit_exact_source_structural_proofs_v2(
    pages: Sequence[Mapping[str, Any]],
    family_spec: Mapping[str, Any],
    compiled_family: Mapping[str, Any],
    selected_region: Mapping[str, Any],
    effective_region: Mapping[str, Any],
    expanded_matches: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Derive structural-only exact-source proofs before schema projection.

    The one-edit module owns the exact second-channel contract.  Importing it
    at call time avoids a module-initialization cycle (that module replays this
    occurrence implementation) while keeping one canonical proof builder.
    The receipt never grants mapping authority here; it only makes an exact
    structural occurrence view available to the reviewed scope projector and
    later closure.  The selected-trial gate must independently rebuild and
    persist the same receipt before schema mapping can become ready.
    """

    from bctc_ai.evaluation import (  # noqa: PLC0415
        accounting_family_one_edit_exact_authority_v1 as one_edit_v1,
    )

    visual_matches = _attach_schema_scope_source_label_bboxes(
        pages,
        compiled_family,
        expanded_matches,
    )
    decorated = _decorate_scopes(visual_matches, selected_region)
    retrieval_region = _expanded_region(effective_region, decorated)
    authority_pages = _one_edit_authority_pages_v2(pages)
    try:
        receipt = one_edit_v1._build_from_canonical_expanded_occurrences_v1(  # noqa: SLF001
            one_edit_v1._pages_with_occurrence_geometry_v1(authority_pages),  # noqa: SLF001
            compiled_family,
            document_pages=authority_pages,
            family_spec=family_spec,
            selected_topology_region=selected_region,
            expanded_occurrence_region=retrieval_region,
        )
    except one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error as exc:
        raise _error("one-edit exact-source structural proof replay failed") from exc
    checks_by_occurrence_id = {
        check["occurrence_id"]: check
        for check in receipt["checks"]
        if check["match_scope"] == "EXPANDED_OCCURRENCE"
    }
    for match in decorated:
        match["retrieval_occurrence_id"] = match["occurrence_id"]
        match["retrieval_role"] = match["role"]
        match["retrieval_role_kind"] = match["role_kind"]
        match["retrieval_role_occurrence_ordinal"] = match["role_occurrence_ordinal"]
        match["retrieval_scope_owner_occurrence_id"] = match["scope_owner_occurrence_id"]
        match["retrieval_within_role"] = match.get("matched_within_role")
        check = checks_by_occurrence_id.get(match["occurrence_id"])
        if type(check) is dict and check["status"] == _ONE_EDIT_EXACT_BOUND_STATUS:
            match["one_edit_exact_source_authority_check"] = canonical_clone_v1(check)
    return receipt, decorated


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


def _is_tiny_isolated_structural_rescue(
    projection: Mapping[str, Any],
) -> bool:
    """Reject one empirically grounded false-DASH shape, never a normal dash.

    MBB's label-only deposit parent intersects a 4x2-pixel scan speck plus one
    discarded noncentral artifact.  A genuine peer cell DASH in the same PDF
    is 9x4 pixels with no discarded component.  Keep this rule intentionally
    conjunctive and integer-based: it cannot reject a normal-size dash, a
    peer-supported degraded mark, or a two-lane all-DASH row.
    """

    dash = projection.get("dash_evidence")
    metrics = dash.get("glyph_metrics") if type(dash) is dict else None
    bbox = metrics.get("component_bbox") if type(metrics) is dict else None
    if (
        projection.get("classification") != "VISIBLE_HORIZONTAL_DASH_GLYPH"
        or projection.get("supporting_peer_dash_column_ordinal") is not None
        or type(bbox) is not list
        or len(bbox) != 4
        or any(type(coordinate) is not int for coordinate in bbox)
        or type(metrics.get("discarded_noncentral_component_count")) is not int
        or metrics["discarded_noncentral_component_count"] < 1
    ):
        return False
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return 0 < width <= 4 and 0 < height <= 2 and width * height <= 8


def _structural_owner_only_descendants(
    source_record: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]],
    row_by_occurrence: Mapping[str, Mapping[str, Any]],
) -> tuple[list[str], dict[str, int]] | None:
    """Prove one closed Family-3 deposit subtree after its label-only owner.

    Demand/term headings are intentionally flattened topology roles, so sealed
    V1 cannot see them as direct children of the deposit group.  V2 uses the
    already declared Family-3 semantic interval: one deposit owner ends at the
    next deposit owner or loan group.  Every visible numeric descendant in the
    interval must be complete, every visible nonstructural semantic role must
    own a row, and at least two complete descendants are required.  This only
    decides whether an isolated rescue may be rejected; it grants no numeric,
    accounting, or mapping authority.
    """

    match = source_record.get("label_match")
    if (
        source_record.get("role") != "INTERBANK_DEPOSIT_GROUP"
        or source_record.get("role_kind") != "STRUCTURAL_GROUP"
        or type(match) is not dict
        or type(match.get("occurrence_id")) is not str
    ):
        return None
    start = match.get("document_line_ordinal")
    page_sequence = match.get("page_sequence")
    if type(start) is not int or type(page_sequence) is not int:
        return None
    later_boundaries = [
        item
        for item in matches
        if type(item.get("document_line_ordinal")) is int
        and item["document_line_ordinal"] > start
        and item.get("role") in {"INTERBANK_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"}
    ]
    if not later_boundaries:
        return None
    boundary = min(later_boundaries, key=lambda item: item["document_line_ordinal"])
    if (
        boundary.get("role") != "INTERBANK_LOAN_GROUP"
        or boundary.get("page_sequence") != page_sequence
    ):
        return None
    end = boundary["document_line_ordinal"]
    interval_occurrences = [
        item
        for item in matches
        if type(item.get("document_line_ordinal")) is int
        and start < item["document_line_ordinal"] < end
        and item.get("role") in _DEPOSIT_SEMANTIC_INTERVAL_ROLES
        and item.get("role") != "INTERBANK_DEPOSIT_GROUP"
    ]
    if not interval_occurrences:
        return None
    if any(item.get("page_sequence") != page_sequence for item in interval_occurrences):
        return None
    complete_ids: list[str] = []
    for item in interval_occurrences:
        occurrence_id = item.get("occurrence_id")
        if type(occurrence_id) is not str:
            return None
        row = row_by_occurrence.get(occurrence_id)
        if row is not None:
            if row.get("status") != "VISIBLE_VALUE_LANES_BOUND":
                return None
            complete_ids.append(occurrence_id)
            continue
        if item.get("role_kind") != "STRUCTURAL_GROUP":
            return None
        direct_complete_children = [
            child
            for child in interval_occurrences
            if child.get("scope_owner_occurrence_id") == occurrence_id
            and row_by_occurrence.get(child.get("occurrence_id"), {}).get("status")
            == "VISIBLE_VALUE_LANES_BOUND"
        ]
        if not direct_complete_children:
            return None
    if len(complete_ids) < 2:
        return None
    return sorted(complete_ids), {
        "end_document_line_ordinal_exclusive": end,
        "start_document_line_ordinal": start,
    }


def _project_structural_owner_only_rescue_rejections(
    axis: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Remove only a tiny isolated false rescue from a proved structural owner."""

    completed = canonical_clone_v1(axis)
    row_by_occurrence = {row["label_match"].get("occurrence_id"): row for row in completed["rows"]}
    rescue_by_region = {item["region_id"]: item for item in completed["visible_dash_rescues"]}
    rejected_occurrence_ids: set[str] = set()
    rejected_region_ids: set[str] = set()
    evidence_axis: list[dict[str, Any]] = []
    for source_record in completed["rows"]:
        match = source_record["label_match"]
        occurrence_id = match.get("occurrence_id")
        if (
            type(occurrence_id) is not str
            or source_record.get("role_kind") != "STRUCTURAL_GROUP"
            or source_record.get("status") != "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
            or len(source_record.get("values", [])) != 1
            or not source_record.get("missing_column_ordinals")
        ):
            continue
        value = source_record["values"][0]
        admitted = rescue_by_region.get(value.get("sample_id"))
        if admitted is None or not _is_tiny_isolated_structural_rescue(admitted):
            continue
        page = match.get("page_sequence")
        role = source_record.get("role")
        role_page_rows = [
            row
            for row in completed["rows"]
            if row.get("role") == role and row.get("label_match", {}).get("page_sequence") == page
        ]
        role_page_matches = [
            item
            for item in matches
            if item.get("role") == role and item.get("page_sequence") == page
        ]
        if (
            len(role_page_rows) != 1
            or len(role_page_matches) != 1
            or role_page_matches[0].get("occurrence_id") != occurrence_id
        ):
            continue
        projections = sorted(
            (
                item
                for item in completed["visible_dash_rescues"]
                if item.get("page_sequence") == page and item.get("role") == role
            ),
            key=lambda item: item["column_ordinal"],
        )
        lane_ordinals = sorted(
            [item["column_ordinal"] for item in source_record["values"]]
            + source_record["missing_column_ordinals"]
        )
        if (
            len(projections) != len(lane_ordinals)
            or [item["column_ordinal"] for item in projections] != lane_ordinals
            or sum(
                item["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH" for item in projections
            )
            != 1
            or any(
                item is not admitted and item["classification"] != "UNRESOLVED_NOT_ONE_DASH_GLYPH"
                for item in projections
            )
        ):
            continue
        descendant_proof = _structural_owner_only_descendants(
            source_record,
            matches,
            row_by_occurrence,
        )
        if descendant_proof is None:
            continue
        complete_descendant_ids, interval = descendant_proof
        material = {
            "complete_descendant_occurrence_ids": complete_descendant_ids,
            "interval": interval,
            "occurrence_id": occurrence_id,
            "page_sequence": page,
            "rejected_rescue_projections": canonical_clone_v1(projections),
            "role": role,
            "source_record": canonical_clone_v1(source_record),
            "status": _STRUCTURAL_OWNER_ONLY_RESCUE_STATUS,
        }
        evidence_axis.append(
            {
                **material,
                "evidence_id": "aforav2:owner-only-rescue:" + canonical_json_sha256_v1(material),
            }
        )
        rejected_occurrence_ids.add(occurrence_id)
        rejected_region_ids.update(item["region_id"] for item in projections)
    if not evidence_axis:
        return completed, []
    completed["rows"] = [
        row
        for row in completed["rows"]
        if row["label_match"].get("occurrence_id") not in rejected_occurrence_ids
    ]
    completed["visible_dash_rescues"] = [
        item
        for item in completed["visible_dash_rescues"]
        if item["region_id"] not in rejected_region_ids
    ]
    return _regenerate_v1_axis(completed), evidence_axis


def _validate_structural_owner_only_rescue_rejections(
    evidence_axis: Any,
    axis: Mapping[str, Any],
    occurrences: Sequence[Mapping[str, Any]],
) -> None:
    if type(evidence_axis) is not list or len(evidence_axis) > _MAX_ROLE_OCCURRENCES:
        raise _error("structural owner-only rescue rejection axis drifted")
    occurrence_by_id = {item["occurrence_id"]: item for item in occurrences}
    evidence_ids: list[str] = []
    occurrence_ids: list[str] = []
    region_ids: list[str] = []
    restored = canonical_clone_v1(axis)
    for evidence in evidence_axis:
        source = evidence.get("source_record") if type(evidence) is dict else None
        projections = (
            evidence.get("rejected_rescue_projections") if type(evidence) is dict else None
        )
        interval = evidence.get("interval") if type(evidence) is dict else None
        occurrence = occurrence_by_id.get(
            evidence.get("occurrence_id", "") if type(evidence) is dict else ""
        )
        if (
            type(evidence) is not dict
            or set(evidence) != _STRUCTURAL_OWNER_ONLY_RESCUE_FIELDS
            or evidence["status"] != _STRUCTURAL_OWNER_ONLY_RESCUE_STATUS
            or type(evidence["evidence_id"]) is not str
            or type(evidence["occurrence_id"]) is not str
            or type(evidence["role"]) is not str
            or type(evidence["page_sequence"]) is not int
            or evidence["page_sequence"] <= 0
            or type(evidence["complete_descendant_occurrence_ids"]) is not list
            or len(evidence["complete_descendant_occurrence_ids"]) < 2
            or len(evidence["complete_descendant_occurrence_ids"])
            != len(set(evidence["complete_descendant_occurrence_ids"]))
            or type(interval) is not dict
            or set(interval) != _STRUCTURAL_OWNER_ONLY_INTERVAL_FIELDS
            or any(type(value) is not int for value in interval.values())
            or interval["start_document_line_ordinal"]
            >= interval["end_document_line_ordinal_exclusive"]
            or type(source) is not dict
            or source.get("label_match", {}).get("occurrence_id") != evidence["occurrence_id"]
            or source.get("role") != evidence["role"]
            or source.get("label_match", {}).get("page_sequence") != evidence["page_sequence"]
            or type(projections) is not list
            or len(projections) < 2
            or type(occurrence) is not dict
            or occurrence["role"] != evidence["role"]
            or occurrence["role_kind"] != "STRUCTURAL_GROUP"
            or occurrence["has_bound_value_row"] is not False
            or not same_typed_json_v1(occurrence["label_match"], source["label_match"])
            or any(
                type(item) is not dict
                or item.get("role") != evidence["role"]
                or item.get("page_sequence") != evidence["page_sequence"]
                or type(item.get("region_id")) is not str
                for item in projections
            )
        ):
            raise _error("structural owner-only rescue rejection evidence drifted")
        material = canonical_clone_v1(evidence)
        evidence_id = material.pop("evidence_id")
        if evidence_id != "aforav2:owner-only-rescue:" + canonical_json_sha256_v1(material):
            raise _error("structural owner-only rescue rejection identity drifted")
        evidence_ids.append(evidence_id)
        occurrence_ids.append(evidence["occurrence_id"])
        region_ids.extend(item["region_id"] for item in projections)
        restored["rows"].append(canonical_clone_v1(source))
        restored["visible_dash_rescues"].extend(canonical_clone_v1(projections))
    if (
        len(evidence_ids) != len(set(evidence_ids))
        or len(occurrence_ids) != len(set(occurrence_ids))
        or len(region_ids) != len(set(region_ids))
        or set(region_ids) & {item["region_id"] for item in axis["visible_dash_rescues"]}
    ):
        raise _error("structural owner-only rescue rejection ownership repeats")
    if not evidence_axis:
        return
    restored = _regenerate_v1_axis(restored)
    replayed_axis, replayed_evidence = _project_structural_owner_only_rescue_rejections(
        restored,
        [item["label_match"] for item in occurrences],
    )
    if not same_typed_json_v1(replayed_axis, axis) or not same_typed_json_v1(
        replayed_evidence, evidence_axis
    ):
        raise _error("structural owner-only rescue rejection replay drifted")


def _numeric_universe_record(
    value: Mapping[str, Any],
    *,
    owner_kind: str,
    owner_id: str,
) -> dict[str, Any]:
    if owner_kind not in _NUMERIC_SAMPLE_OWNER_KINDS or not owner_id:
        raise _error("numeric sample universe owner drifted")
    return {
        "bbox": canonical_clone_v1(value["bbox"]),
        "column_center": float(value["column_center"]),
        "column_ordinal": value["column_ordinal"],
        "crop_ref": canonical_clone_v1(value["crop_ref"]),
        "line_ordinal": value["line_ordinal"],
        "owner_id": owner_id,
        "owner_kind": owner_kind,
        "page_sequence": value["page_sequence"],
        "parsed_token": canonical_clone_v1(value["parsed_token"]),
        "raw_prediction": value["raw_prediction"],
        "reader_score": value["reader_score"],
        "sample_id": value["sample_id"],
    }


def _inspected_label_band_line(line: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bbox": canonical_clone_v1(line["bbox"]),
        "line_ordinal": line["line_ordinal"],
        "numeric_raw_prediction": line["numeric_recognition"]["raw_prediction"],
        "vietocr_text": line["vietocr_text"],
    }


def _same_row_label_evidence_from_inspected_band(
    source_line_axis: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    evidence = []
    for line in source_line_axis:
        numeric_probe = {
            "bbox": line["bbox"],
            "line_ordinal": line["line_ordinal"],
            "numeric_recognition": {"raw_prediction": line["numeric_raw_prediction"]},
            "vietocr_text": line["vietocr_text"],
        }
        if row_v1._is_numeric(numeric_probe):  # noqa: SLF001
            continue
        if not (line["vietocr_text"].strip() or line["numeric_raw_prediction"].strip()):
            continue
        evidence.append(canonical_clone_v1(line))
    return sorted(evidence, key=lambda item: (item["bbox"][0], item["line_ordinal"]))


def _build_inspected_label_band(
    *,
    ordered_numeric_lines: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    local_lines: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    numeric_left = min(line["bbox"][0] for line in ordered_numeric_lines)
    source_line_axis = []
    for line in local_lines:
        if line["bbox"][0] >= numeric_left:
            continue
        line_height = line["bbox"][3] - line["bbox"][1]
        if not any(
            abs(line["bbox"][1] + line["bbox"][3] - numeric["bbox"][1] - numeric["bbox"][3])
            <= max(line_height, numeric["bbox"][3] - numeric["bbox"][1])
            for numeric in ordered_numeric_lines
        ):
            continue
        source_line_axis.append(_inspected_label_band_line(line))
    source_line_axis.sort(key=lambda item: (item["line_ordinal"], item["bbox"]))
    material = {
        "document_pages_sha256": canonical_json_sha256_v1(pages),
        "input_page_line_count": len(page["lines"]),
        "numeric_row_bboxes": [canonical_clone_v1(line["bbox"]) for line in ordered_numeric_lines],
        "numeric_row_sample_ids": [line["sample_id"] for line in ordered_numeric_lines],
        "page_sequence": page["page_sequence"],
        "source_line_axis": source_line_axis,
        "source_line_axis_sha256": canonical_json_sha256_v1(source_line_axis),
    }
    receipt = {
        **material,
        "receipt_id": "aforav2:label-band:" + canonical_json_sha256_v1(material),
    }
    return receipt, _same_row_label_evidence_from_inspected_band(source_line_axis)


def _extreme_margin_line_record(line: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bbox": canonical_clone_v1(line["bbox"]),
        "crop_ref": canonical_clone_v1(line["crop_ref"]),
        "line_ordinal": line["line_ordinal"],
        "numeric_raw_prediction": line["numeric_recognition"]["raw_prediction"],
        "numeric_reader_score": line["numeric_recognition"]["reader_score"],
        "sample_id": line["sample_id"],
        "vietocr_text": line["vietocr_text"],
    }


def _extreme_margin_peer_surfaces_are_nonnumeric(line: Mapping[str, Any]) -> bool:
    return all(
        not any(character.isdigit() for character in surface)
        and row_v1.parse_visible_financial_numeric_token_v1(surface)["classification"]
        not in _EXTREME_MARGIN_ADMITTED_NUMERIC_CLASSIFICATIONS
        for surface in (line["numeric_raw_prediction"], line["vietocr_text"])
    )


def _extreme_margin_band_axis(
    page: Mapping[str, Any], candidate: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Return the complete bounded right-edge source band around one token."""

    page_width = page["page_width"]
    bbox = candidate["bbox"]
    height = bbox[3] - bbox[1]
    axis = []
    for line in page["lines"]:
        line_bbox = line["bbox"]
        line_height = line_bbox[3] - line_bbox[1]
        if (
            line_bbox[0] * 20 < page_width * 19
            or page_width - line_bbox[2] > max(height, line_height)
            or min(line_bbox[2], bbox[2]) <= max(line_bbox[0], bbox[0])
            or not (
                line["vietocr_text"].strip()
                or line["numeric_recognition"]["raw_prediction"].strip()
            )
        ):
            continue
        axis.append(_extreme_margin_line_record(line))
    return sorted(axis, key=lambda item: (item["line_ordinal"], item["bbox"]))


def _extreme_margin_geometric_peer_ordinals(
    source_line_axis: Sequence[Mapping[str, Any]], candidate: Mapping[str, Any]
) -> list[int]:
    candidate_ordinal = candidate["line_ordinal"]
    candidate_bbox = candidate["bbox"]
    candidate_width = candidate_bbox[2] - candidate_bbox[0]
    candidate_height = candidate_bbox[3] - candidate_bbox[1]
    peers = []
    for line in source_line_axis:
        if line["line_ordinal"] == candidate_ordinal:
            continue
        bbox = line["bbox"]
        overlap = min(candidate_bbox[2], bbox[2]) - max(candidate_bbox[0], bbox[0])
        vertical_gap = max(
            0,
            candidate_bbox[1] - bbox[3],
            bbox[1] - candidate_bbox[3],
        )
        if 2 * overlap < min(candidate_width, bbox[2] - bbox[0]) or vertical_gap > 4 * max(
            candidate_height, bbox[3] - bbox[1]
        ):
            continue
        peers.append(line["line_ordinal"])
    return sorted(peers)


def _extreme_margin_has_bidirectional_peers(
    source_line_axis: Sequence[Mapping[str, Any]],
    candidate: Mapping[str, Any],
    peer_ordinals: Sequence[int],
) -> bool:
    if len(peer_ordinals) < 2:
        return False
    by_ordinal = {line["line_ordinal"]: line for line in source_line_axis}
    candidate_center_twice = candidate["bbox"][1] + candidate["bbox"][3]
    centers = [
        by_ordinal[ordinal]["bbox"][1] + by_ordinal[ordinal]["bbox"][3]
        for ordinal in peer_ordinals
        if ordinal in by_ordinal
    ]
    return (
        len(centers) == len(peer_ordinals)
        and any(center < candidate_center_twice for center in centers)
        and any(center > candidate_center_twice for center in centers)
    )


def _authenticated_extreme_margin_crop_proof(
    *,
    image: Any,
    render_record: Mapping[str, Any],
    render_id: str,
    line: Mapping[str, Any],
) -> dict[str, Any]:
    bbox = line["bbox"]
    exact_crop = image.crop(tuple(bbox))
    exact_rgb = exact_crop.tobytes()
    pixels = list(zip(exact_rgb[0::3], exact_rgb[1::3], exact_rgb[2::3], strict=True))
    ink = [pixel for pixel in pixels if min(pixel) < 220]
    chromatic = [pixel for pixel in ink if max(pixel) - min(pixel) >= 30]
    return {
        "chromatic_ink_pixel_count": len(chromatic),
        "exact_bbox_rgb_sha256": hashlib.sha256(exact_rgb).hexdigest(),
        "ink_pixel_count": len(ink),
        "pixel_count": len(pixels),
        "render_binding": {
            "document_ordinal": render_record["document_ordinal"],
            "physical_page": render_record["physical_page"],
            "raw_pixel_bbox": canonical_clone_v1(bbox),
            "render_id": render_id,
            "render_ref": canonical_clone_v1(render_record["render_ref"]),
        },
        "source_line_record": _extreme_margin_line_record(line),
    }


def _crop_proof_is_chromatic(proof: Mapping[str, Any]) -> bool:
    return (
        proof["ink_pixel_count"] > 0
        and proof["chromatic_ink_pixel_count"] * 3 >= proof["ink_pixel_count"] * 2
    )


def _build_authenticated_extreme_margin_furniture_evidence(
    *,
    topology_candidates_id: str | None,
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    ordered_numeric_lines: Sequence[Mapping[str, Any]],
    cluster: Mapping[str, Any],
    source_record: Mapping[str, Any],
    centers: Sequence[float],
    lane_tolerance: float,
    selected_snapshot: Mapping[str, Any] | None,
    render_by_page: Mapping[int, Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, bool]:
    """Prove one numeric OCR token is authenticated chromatic margin furniture.

    The non-pixel half is also the exact render-request gate.  It is deliberately
    Family-3/V2-only and never suppresses a multi-token or labeled source row.
    """

    if (
        type(topology_candidates_id) is not str
        or not topology_candidates_id.startswith("aftcv2:result:")
        or len(ordered_numeric_lines) != 1
        or cluster.get("status") != _OFF_LANE_NUMERIC_CLUSTER_STATUS
        or cluster.get("label_lane_status") != _UNLABELED_LABEL_LANE_STATUS
        or cluster.get("same_row_label_evidence") != []
        or source_record.get("parsed_token", {}).get("classification") != "SIGNED_NUMBER"
        or type(page.get("page_width")) is not int
        or page["page_width"] <= 0
    ):
        return None, False
    candidate = ordered_numeric_lines[0]
    if (
        row_v1.parse_visible_financial_numeric_token_v1(candidate["vietocr_text"])["classification"]
        != "SIGNED_NUMBER"
    ):
        return None, False
    bbox = candidate["bbox"]
    height = bbox[3] - bbox[1]
    page_width = page["page_width"]
    if bbox[0] * 20 < page_width * 19 or page_width - bbox[2] > height:
        return None, False
    full_page_label_band, full_page_label_evidence = _build_inspected_label_band(
        ordered_numeric_lines=ordered_numeric_lines,
        page=page,
        pages=pages,
        local_lines=page["lines"],
    )
    if full_page_label_evidence:
        return None, False
    margin_axis = _extreme_margin_band_axis(page, candidate)
    candidate_records = [
        line for line in margin_axis if line["line_ordinal"] == candidate["line_ordinal"]
    ]
    geometric_peers = _extreme_margin_geometric_peer_ordinals(margin_axis, candidate)
    margin_by_ordinal = {line["line_ordinal"]: line for line in margin_axis}
    geometric_peers = [
        ordinal
        for ordinal in geometric_peers
        if _extreme_margin_peer_surfaces_are_nonnumeric(margin_by_ordinal[ordinal])
    ]
    if len(candidate_records) != 1 or not _extreme_margin_has_bidirectional_peers(
        margin_axis, candidate, geometric_peers
    ):
        return None, False
    page_sequence = page["page_sequence"]
    if selected_snapshot is None or page_sequence not in render_by_page:
        return None, selected_snapshot is not None
    render = render_by_page[page_sequence]
    try:
        render_record, payload = render_v1._validated_render_snapshot(render)
        image = render_v1._png_image(payload).convert("RGB")
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise _error("authenticated extreme-margin render replay failed") from exc
    candidate_crop = _authenticated_extreme_margin_crop_proof(
        image=image,
        render_record=render_record,
        render_id=render["render_id"],
        line=candidate,
    )
    if not _crop_proof_is_chromatic(candidate_crop):
        return None, False
    page_line_by_ordinal = {line["line_ordinal"]: line for line in page["lines"]}
    peer_crops = []
    for ordinal in geometric_peers:
        proof = _authenticated_extreme_margin_crop_proof(
            image=image,
            render_record=render_record,
            render_id=render["render_id"],
            line=page_line_by_ordinal[ordinal],
        )
        if _crop_proof_is_chromatic(proof):
            peer_crops.append(proof)
    qualifying_peer_ordinals = sorted(
        proof["source_line_record"]["line_ordinal"] for proof in peer_crops
    )
    if not _extreme_margin_has_bidirectional_peers(
        margin_axis, candidate, qualifying_peer_ordinals
    ):
        return None, False
    lane = source_record["column_ordinal"]
    center_quads = [center * 4 for center in centers]
    if any(not float(center).is_integer() for center in center_quads):
        return None, False
    document_pages_sha256 = canonical_json_sha256_v1(pages)
    material = {
        "candidate_crop_proof": candidate_crop,
        "document_pages_sha256": document_pages_sha256,
        "full_page_inspected_label_band": full_page_label_band,
        "geometry": {
            "candidate_bbox": canonical_clone_v1(bbox),
            "candidate_center_quads": 2 * (bbox[0] + bbox[2]),
            "extreme_right_denominator": 20,
            "extreme_right_numerator": 19,
            "lane_centers_quads": [int(center) for center in center_quads],
            "lane_tolerance": float(lane_tolerance),
            "nearest_lane_ordinal": lane,
            "page_width": page_width,
            "right_edge_gap": page_width - bbox[2],
        },
        "margin_band": {
            "document_pages_sha256": document_pages_sha256,
            "input_page_line_count": len(page["lines"]),
            "page_sequence": page_sequence,
            "qualifying_peer_line_ordinals": qualifying_peer_ordinals,
            "source_line_axis": margin_axis,
            "source_line_axis_sha256": canonical_json_sha256_v1(margin_axis),
        },
        "original_cluster": canonical_clone_v1(cluster),
        "page_sequence": page_sequence,
        "peer_crop_proofs": sorted(
            peer_crops,
            key=lambda proof: proof["source_line_record"]["line_ordinal"],
        ),
        "sample_id": source_record["sample_id"],
        "snapshot_id": selected_snapshot["snapshot_id"],
        "source_record": canonical_clone_v1(source_record),
        "status": _EXTREME_MARGIN_FURNITURE_STATUS,
        "topology_candidates_id": topology_candidates_id,
    }
    return {
        **material,
        "evidence_id": "aforav2:extreme-margin-furniture:" + canonical_json_sha256_v1(material),
    }, False


def _build_numeric_sample_universe(
    pages: Sequence[Mapping[str, Any]],
    expanded_region: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]],
    axis: Mapping[str, Any],
    coextensive_evidence: Sequence[Mapping[str, Any]],
    *,
    topology_candidates_id: str | None,
    selected_snapshot: Mapping[str, Any] | None,
    render_snapshots: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Own every typed body-lane sample or expose it as source-only.

    The sealed V1 axis owns role rows and trailing challengers, but deliberately
    does not expose numeric rows stranded *between* semantic labels.  V2 closes
    that denominator without changing V1: it reuses the exact V1 role-body
    fence and immutable body column grid, then groups only still-unowned,
    same-baseline numeric boxes.  Header/unit/page furniture outside those
    existing geometric fences never enters this universe.
    """

    universe_by_sample: dict[str, dict[str, Any]] = {}

    def own(value: Mapping[str, Any], *, owner_kind: str, owner_id: str) -> None:
        sample_id = value.get("sample_id")
        if type(sample_id) is not str or not sample_id or sample_id in universe_by_sample:
            raise _error("numeric sample universe repeats one physical source sample")
        universe_by_sample[sample_id] = _numeric_universe_record(
            value,
            owner_kind=owner_kind,
            owner_id=owner_id,
        )

    for row in axis["rows"]:
        occurrence_id = row["label_match"].get("occurrence_id")
        if type(occurrence_id) is not str or not occurrence_id:
            raise _error("numeric role row lost its owning occurrence")
        for value in row["values"]:
            own(value, owner_kind="ROLE_OCCURRENCE", owner_id=occurrence_id)
    for trailing in axis["trailing_value_rows"]:
        owner_id = f"aforav2:trailing:{trailing['candidate_ordinal']}"
        for value in trailing["values"]:
            own(value, owner_kind="TRAILING_VALUE_ROW", owner_id=owner_id)
    for evidence in coextensive_evidence:
        if evidence["status"] != total_v1.COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_STATUS:
            # Ambiguous coextensive evidence remains one ordinary role-row
            # owner.  The evidence object is a reference and cannot become a
            # second numeric owner.
            continue
        for value in evidence["source_record"]["values"]:
            own(
                value,
                owner_kind="COEXTENSIVE_SCOPE_TOTAL_REFERENCE",
                owner_id=evidence["owner_occurrence_id"],
            )

    render_by_page = {
        render["physical_page"]: render
        for render in render_snapshots
        if type(render) is dict and type(render.get("physical_page")) is int
    }
    furniture_evidence: list[dict[str, Any]] = []
    render_required_reasons: list[str] = []
    body_by_page = row_v1._role_body_lines_by_page(pages, expanded_region, matches)
    grid_by_page = {grid["page_sequence"]: grid for grid in axis["column_grids"]}
    clusters: list[dict[str, Any]] = []
    for page_sequence in sorted(grid_by_page):
        grid = grid_by_page[page_sequence]
        centers = grid["column_centers"]
        local_lines = body_by_page.get(page_sequence, [])
        page = next(page for page in pages if page["page_sequence"] == page_sequence)
        if not centers:
            # The sealed V1 axis uses an empty grid for prose/non-table
            # candidates.  With no admitted body MONEY lane there is no
            # numeric-universe projection to perform; in particular, margin
            # numerals must not manufacture a lane.  The incomplete V1 rows
            # remain the typed occurrence-level veto.
            continue
        if not local_lines or type(page["page_width"]) is not int:
            raise _error("numeric sample universe lost its exact body lane grid")
        scale = row_v1.median_text_height_v1(local_lines)
        lane_tolerance = (
            max(
                scale * 1.6,
                min(right - left for left, right in zip(centers, centers[1:], strict=False)) * 0.42,
            )
            if len(centers) > 1
            else scale * 2.5
        )
        header_indices = set(grid["header_evidence_source_line_indices"])
        candidates: list[dict[str, Any]] = []
        lanes_by_sample: dict[str, int] = {}
        off_lane_sample_ids: set[str] = set()
        adjacent_lane_span = (
            min(right - left for left, right in zip(centers, centers[1:], strict=False))
            if len(centers) > 1
            else scale * 4.0
        )
        table_left = centers[0] - adjacent_lane_span * 0.75
        table_right = centers[-1] + adjacent_lane_span * 0.75
        for line in local_lines:
            if (
                line["sample_id"] in universe_by_sample
                or line["line_ordinal"] in header_indices
                or not row_v1._is_numeric(line)
            ):
                continue
            center = (line["bbox"][0] + line["bbox"][2]) / 2
            if not table_left <= center <= table_right:
                continue
            lane = min(range(len(centers)), key=lambda index: abs(center - centers[index]))
            projected = {**canonical_clone_v1(line), "source_line_index": line["line_ordinal"]}
            candidates.append(projected)
            lanes_by_sample[line["sample_id"]] = lane
            if abs(center - centers[lane]) > lane_tolerance:
                off_lane_sample_ids.add(line["sample_id"])
        if not candidates:
            continue
        physical_clusters = row_v1.cluster_numeric_rows_v1(
            candidates,
            is_numeric=row_v1._is_numeric,
            start_index=min(line["source_line_index"] for line in candidates) - 1,
            stop_index=max(line["source_line_index"] for line in candidates) + 1,
            page_width=page["page_width"],
            minimum_x_ratio=0.0,
            maximum_x_ratio=1.0,
        )
        for physical_cluster in physical_clusters:
            ordered = sorted(
                physical_cluster,
                key=lambda line: (
                    lanes_by_sample[line["sample_id"]],
                    line["line_ordinal"],
                    line["sample_id"],
                ),
            )
            inspected_label_band, same_row_label_evidence = _build_inspected_label_band(
                ordered_numeric_lines=ordered,
                page=page,
                pages=pages,
                local_lines=local_lines,
            )
            cluster_material = {
                "column_ordinals": [lanes_by_sample[line["sample_id"]] for line in ordered],
                "inspected_label_band": inspected_label_band,
                "label_lane_status": (
                    _LABELED_LABEL_LANE_STATUS
                    if same_row_label_evidence
                    else _UNLABELED_LABEL_LANE_STATUS
                ),
                "page_sequence": page_sequence,
                "same_row_label_evidence": same_row_label_evidence,
                "sample_ids": [line["sample_id"] for line in ordered],
                "status": (
                    _OFF_LANE_NUMERIC_CLUSTER_STATUS
                    if any(line["sample_id"] in off_lane_sample_ids for line in ordered)
                    else _INTERNAL_UNASSIGNED_CLUSTER_STATUS
                ),
            }
            cluster_id = "aforav2:unassigned:" + canonical_json_sha256_v1(cluster_material)
            cluster = {**cluster_material, "cluster_id": cluster_id}
            source_records = []
            for line in ordered:
                lane = lanes_by_sample[line["sample_id"]]
                value = row_v1._value_record(
                    page_sequence,
                    line,
                    column_center=centers[lane],
                    column_ordinal=lane,
                    row_affinity=None,
                )
                source_records.append(
                    _numeric_universe_record(
                        value,
                        owner_kind="SOURCE_ONLY_INTERNAL_CLUSTER",
                        owner_id=cluster_id,
                    )
                )
            evidence = None
            render_required = False
            if len(source_records) == 1:
                evidence, render_required = _build_authenticated_extreme_margin_furniture_evidence(
                    pages=pages,
                    topology_candidates_id=topology_candidates_id,
                    page=page,
                    ordered_numeric_lines=ordered,
                    cluster=cluster,
                    source_record=source_records[0],
                    centers=centers,
                    lane_tolerance=lane_tolerance,
                    selected_snapshot=selected_snapshot,
                    render_by_page=render_by_page,
                )
            if evidence is not None:
                furniture_evidence.append(evidence)
                source = source_records[0]
                own(
                    source,
                    owner_kind=_EXTREME_MARGIN_FURNITURE_OWNER_KIND,
                    owner_id=evidence["evidence_id"],
                )
                continue
            clusters.append(cluster)
            if render_required:
                render_required_reasons.append(
                    _EXTREME_MARGIN_RENDER_REASON_PREFIX + str(page_sequence)
                )
            for source in source_records:
                own(
                    source,
                    owner_kind="SOURCE_ONLY_INTERNAL_CLUSTER",
                    owner_id=cluster_id,
                )
    universe = sorted(
        universe_by_sample.values(),
        key=lambda record: (
            record["page_sequence"],
            record["line_ordinal"],
            record["column_ordinal"],
            record["sample_id"],
        ),
    )
    return (
        universe,
        clusters,
        sorted(furniture_evidence, key=lambda item: (item["page_sequence"], item["sample_id"])),
        list(dict.fromkeys(render_required_reasons)),
    )


def _validate_numeric_sample_record(record: Any) -> dict[str, Any]:
    if type(record) is not dict or type(record.get("raw_prediction")) is not str:
        raise _error("numeric sample universe record drifted")
    parsed = row_v1.parse_visible_financial_numeric_token_v1(record["raw_prediction"])
    if (
        set(record) != _NUMERIC_SAMPLE_FIELDS
        or type(record["sample_id"]) is not str
        or not record["sample_id"]
        or type(record["page_sequence"]) is not int
        or record["page_sequence"] <= 0
        or type(record["line_ordinal"]) is not int
        or record["line_ordinal"] < 0
        or type(record["bbox"]) is not list
        or len(record["bbox"]) != 4
        or any(type(item) is not int or item < 0 for item in record["bbox"])
        or record["bbox"][2] <= record["bbox"][0]
        or record["bbox"][3] <= record["bbox"][1]
        or type(record["column_center"]) is not float
        or record["column_center"] < 0
        or type(record["column_ordinal"]) is not int
        or record["column_ordinal"] < 0
        or type(record["reader_score"]) is not float
        or not 0 <= record["reader_score"] <= 1
        or not same_typed_json_v1(record["parsed_token"], parsed)
        or parsed["classification"]
        not in {
            "DASH_ZERO",
            "MIXED_GROUPED_INTEGER_CANDIDATE",
            "NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
            "SIGNED_NUMBER",
        }
        or record["owner_kind"] not in _NUMERIC_SAMPLE_OWNER_KINDS
        or type(record["owner_id"]) is not str
        or not record["owner_id"]
    ):
        raise _error("numeric sample universe record drifted")
    try:
        validated_ref = row_v1._ref(record["crop_ref"])
    except row_v1.AccountingFamilyRowAxisV1Error as exc:
        raise _error("numeric sample universe crop reference drifted") from exc
    if not same_typed_json_v1(validated_ref, record["crop_ref"]):
        raise _error("numeric sample universe crop reference drifted")
    return canonical_clone_v1(record)


def _validate_inspected_label_band(
    cluster: Mapping[str, Any], by_sample: Mapping[str, Mapping[str, Any]]
) -> None:
    receipt = cluster.get("inspected_label_band")
    if type(receipt) is not dict or set(receipt) != _INSPECTED_LABEL_BAND_FIELDS:
        raise _error("internal numeric cluster inspected label-band receipt drifted")
    source_axis = receipt["source_line_axis"]
    if (
        type(receipt["document_pages_sha256"]) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", receipt["document_pages_sha256"])
        or type(receipt["input_page_line_count"]) is not int
        or receipt["input_page_line_count"] < len(source_axis)
        or receipt["page_sequence"] != cluster["page_sequence"]
        or receipt["numeric_row_sample_ids"] != cluster["sample_ids"]
        or type(receipt["numeric_row_bboxes"]) is not list
        or len(receipt["numeric_row_bboxes"]) != len(cluster["sample_ids"])
        or type(source_axis) is not list
        or any(
            type(item) is not dict
            or set(item) != _SAME_ROW_LABEL_EVIDENCE_FIELDS
            or type(item["bbox"]) is not list
            or len(item["bbox"]) != 4
            or any(type(coordinate) is not int for coordinate in item["bbox"])
            or type(item["line_ordinal"]) is not int
            or item["line_ordinal"] < 0
            or type(item["numeric_raw_prediction"]) is not str
            or type(item["vietocr_text"]) is not str
            for item in source_axis
        )
        or source_axis != sorted(source_axis, key=lambda item: (item["line_ordinal"], item["bbox"]))
        or len({item["line_ordinal"] for item in source_axis}) != len(source_axis)
        or receipt["source_line_axis_sha256"] != canonical_json_sha256_v1(source_axis)
    ):
        raise _error("internal numeric cluster inspected label-band denominator drifted")
    expected_bboxes = []
    for sample_id in cluster["sample_ids"]:
        sample = by_sample.get(sample_id)
        if type(sample) is not dict:
            raise _error("inspected label-band numeric source sample is absent")
        expected_bboxes.append(sample["bbox"])
    if not same_typed_json_v1(receipt["numeric_row_bboxes"], expected_bboxes):
        raise _error("inspected label-band numeric row geometry drifted")
    material = canonical_clone_v1(receipt)
    receipt_id = material.pop("receipt_id", None)
    if receipt_id != "aforav2:label-band:" + canonical_json_sha256_v1(material):
        raise _error("internal numeric cluster inspected label-band identity drifted")
    expected_evidence = _same_row_label_evidence_from_inspected_band(source_axis)
    if not same_typed_json_v1(cluster["same_row_label_evidence"], expected_evidence) or (
        cluster["label_lane_status"]
        != (_LABELED_LABEL_LANE_STATUS if expected_evidence else _UNLABELED_LABEL_LANE_STATUS)
    ):
        raise _error("internal numeric cluster label-lane status did not replay from its band")


def _validate_extreme_margin_line_record(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _EXTREME_MARGIN_LINE_FIELDS
        or type(value["bbox"]) is not list
        or len(value["bbox"]) != 4
        or any(type(coordinate) is not int or coordinate < 0 for coordinate in value["bbox"])
        or value["bbox"][2] <= value["bbox"][0]
        or value["bbox"][3] <= value["bbox"][1]
        or type(value["line_ordinal"]) is not int
        or value["line_ordinal"] < 0
        or type(value["sample_id"]) is not str
        or not value["sample_id"]
        or type(value["numeric_raw_prediction"]) is not str
        or type(value["numeric_reader_score"]) is not float
        or not 0 <= value["numeric_reader_score"] <= 1
        or type(value["vietocr_text"]) is not str
    ):
        raise _error("extreme-margin source line record drifted")
    try:
        reference = row_v1._ref(value["crop_ref"])
    except row_v1.AccountingFamilyRowAxisV1Error as exc:
        raise _error("extreme-margin source crop reference drifted") from exc
    if not same_typed_json_v1(reference, value["crop_ref"]):
        raise _error("extreme-margin source crop reference drifted")
    return canonical_clone_v1(value)


def _validate_extreme_margin_render_binding(value: Any, source_line: Mapping[str, Any]) -> None:
    if (
        type(value) is not dict
        or set(value) != _EXTREME_MARGIN_RENDER_BINDING_FIELDS
        or type(value["document_ordinal"]) is not int
        or value["document_ordinal"] <= 0
        or type(value["physical_page"]) is not int
        or value["physical_page"] <= 0
        or value["raw_pixel_bbox"] != source_line["bbox"]
        or type(value["render_id"]) is not str
        or not value["render_id"].startswith("ffaprv1:render:")
    ):
        raise _error("extreme-margin authenticated render binding drifted")
    try:
        render_ref = render_v1._render_reference(value["render_ref"])
    except (ValueError, RuntimeError) as exc:
        raise _error("extreme-margin authenticated render reference drifted") from exc
    bbox = value["raw_pixel_bbox"]
    if bbox[2] > render_ref["pixel_width"] or bbox[3] > render_ref["pixel_height"]:
        raise _error("extreme-margin crop lies outside authenticated render dimensions")


def _validate_extreme_margin_crop_proof(value: Any) -> dict[str, Any]:
    source_line = value.get("source_line_record") if type(value) is dict else None
    if (
        type(value) is not dict
        or set(value) != _EXTREME_MARGIN_CROP_PROOF_FIELDS
        or type(source_line) is not dict
        or type(value["pixel_count"]) is not int
        or value["pixel_count"] <= 0
        or type(value["ink_pixel_count"]) is not int
        or not 0 < value["ink_pixel_count"] <= value["pixel_count"]
        or type(value["chromatic_ink_pixel_count"]) is not int
        or not 0 < value["chromatic_ink_pixel_count"] <= value["ink_pixel_count"]
        or value["chromatic_ink_pixel_count"] * 3 < value["ink_pixel_count"] * 2
        or type(value["exact_bbox_rgb_sha256"]) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", value["exact_bbox_rgb_sha256"])
    ):
        raise _error("extreme-margin chromatic crop proof drifted")
    source_line = _validate_extreme_margin_line_record(source_line)
    bbox = source_line["bbox"]
    if value["pixel_count"] != (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]):
        raise _error("extreme-margin exact source-bbox pixel denominator drifted")
    _validate_extreme_margin_render_binding(value["render_binding"], source_line)
    return canonical_clone_v1(value)


def _validate_extreme_margin_furniture_evidence_axis(
    evidence_axis: Any,
    *,
    universe_by_sample: Mapping[str, Mapping[str, Any]],
    axis: Mapping[str, Any],
    topology_candidates_id: str | None,
) -> set[str]:
    if type(evidence_axis) is not list or len(evidence_axis) > _MAX_ROLE_OCCURRENCES:
        raise _error("authenticated extreme-margin furniture evidence axis drifted")
    grid_by_page = {grid["page_sequence"]: grid for grid in axis["column_grids"]}
    evidence_ids: list[str] = []
    sample_ids: list[str] = []
    for evidence in evidence_axis:
        if (
            type(evidence) is not dict
            or set(evidence) != _EXTREME_MARGIN_FURNITURE_FIELDS
            or evidence["status"] != _EXTREME_MARGIN_FURNITURE_STATUS
            or type(evidence["evidence_id"]) is not str
            or type(evidence["snapshot_id"]) is not str
            or not evidence["snapshot_id"].startswith("ffdesv1:selected:")
            or type(evidence["document_pages_sha256"]) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", evidence["document_pages_sha256"])
            or type(evidence["page_sequence"]) is not int
            or evidence["page_sequence"] <= 0
            or type(evidence["sample_id"]) is not str
            or not evidence["sample_id"]
            or evidence["topology_candidates_id"] != topology_candidates_id
        ):
            raise _error("authenticated extreme-margin furniture evidence drifted")
        material = canonical_clone_v1(evidence)
        evidence_id = material.pop("evidence_id")
        if evidence_id != "aforav2:extreme-margin-furniture:" + canonical_json_sha256_v1(material):
            raise _error("authenticated extreme-margin furniture identity drifted")
        cluster = evidence["original_cluster"]
        source = evidence["source_record"]
        if (
            type(cluster) is not dict
            or set(cluster) != _INTERNAL_UNASSIGNED_CLUSTER_FIELDS
            or cluster.get("status") != _OFF_LANE_NUMERIC_CLUSTER_STATUS
            or cluster.get("page_sequence") != evidence["page_sequence"]
            or cluster.get("sample_ids") != [evidence["sample_id"]]
            or cluster.get("label_lane_status") != _UNLABELED_LABEL_LANE_STATUS
            or cluster.get("same_row_label_evidence") != []
            or type(source) is not dict
        ):
            raise _error("extreme-margin furniture original singleton cluster drifted")
        _validate_numeric_sample_record(source)
        if (
            source["sample_id"] != evidence["sample_id"]
            or source["page_sequence"] != evidence["page_sequence"]
            or source["parsed_token"]["classification"] != "SIGNED_NUMBER"
            or source["owner_kind"] != "SOURCE_ONLY_INTERNAL_CLUSTER"
            or source["owner_id"] != cluster["cluster_id"]
        ):
            raise _error("extreme-margin furniture original numeric owner drifted")
        cluster_material = canonical_clone_v1(cluster)
        cluster_id = cluster_material.pop("cluster_id", None)
        if cluster_id != "aforav2:unassigned:" + canonical_json_sha256_v1(cluster_material):
            raise _error("extreme-margin furniture original cluster identity drifted")
        _validate_inspected_label_band(cluster, {evidence["sample_id"]: source})
        if (
            cluster["inspected_label_band"]["document_pages_sha256"]
            != evidence["document_pages_sha256"]
            or cluster["inspected_label_band"]["page_sequence"] != evidence["page_sequence"]
        ):
            raise _error("extreme-margin original cluster document binding drifted")
        full_page_band = evidence["full_page_inspected_label_band"]
        full_page_cluster = {**canonical_clone_v1(cluster), "inspected_label_band": full_page_band}
        _validate_inspected_label_band(full_page_cluster, {evidence["sample_id"]: source})
        if _same_row_label_evidence_from_inspected_band(full_page_band["source_line_axis"]):
            raise _error("extreme-margin furniture has a same-row full-page label")
        if (
            full_page_band["document_pages_sha256"] != evidence["document_pages_sha256"]
            or full_page_band["page_sequence"] != evidence["page_sequence"]
        ):
            raise _error("extreme-margin full-page label denominator binding drifted")
        geometry = evidence["geometry"]
        grid = grid_by_page.get(evidence["page_sequence"])
        bbox = source["bbox"]
        if (
            type(geometry) is not dict
            or set(geometry) != _EXTREME_MARGIN_GEOMETRY_FIELDS
            or type(grid) is not dict
            or type(geometry["page_width"]) is not int
            or geometry["page_width"] <= 0
            or geometry["candidate_bbox"] != bbox
            or geometry["candidate_center_quads"] != 2 * (bbox[0] + bbox[2])
            or geometry["extreme_right_numerator"] != 19
            or geometry["extreme_right_denominator"] != 20
            or bbox[0] * 20 < geometry["page_width"] * 19
            or geometry["right_edge_gap"] != geometry["page_width"] - bbox[2]
            or geometry["right_edge_gap"] > bbox[3] - bbox[1]
            or type(geometry["lane_centers_quads"]) is not list
            or any(not float(center * 4).is_integer() for center in grid["column_centers"])
            or geometry["lane_centers_quads"]
            != [int(center * 4) for center in grid["column_centers"]]
            or type(geometry["lane_tolerance"]) is not float
            or not math.isfinite(geometry["lane_tolerance"])
            or geometry["lane_tolerance"] <= 0
            or type(geometry["nearest_lane_ordinal"]) is not int
            or not 0 <= geometry["nearest_lane_ordinal"] < len(grid["column_centers"])
            or source["column_ordinal"] != geometry["nearest_lane_ordinal"]
            or source["column_center"] != grid["column_centers"][source["column_ordinal"]]
            or geometry["nearest_lane_ordinal"]
            != min(
                range(len(grid["column_centers"])),
                key=lambda index: abs(
                    geometry["candidate_center_quads"] - geometry["lane_centers_quads"][index]
                ),
            )
            or abs(
                geometry["candidate_center_quads"]
                - geometry["lane_centers_quads"][geometry["nearest_lane_ordinal"]]
            )
            <= 4 * geometry["lane_tolerance"]
        ):
            raise _error("extreme-margin furniture geometry or lane exclusion drifted")
        margin_band = evidence["margin_band"]
        source_axis = margin_band.get("source_line_axis") if type(margin_band) is dict else None
        peer_ordinals = (
            margin_band.get("qualifying_peer_line_ordinals") if type(margin_band) is dict else None
        )
        if (
            type(margin_band) is not dict
            or set(margin_band) != _EXTREME_MARGIN_BAND_FIELDS
            or margin_band["document_pages_sha256"] != evidence["document_pages_sha256"]
            or margin_band["page_sequence"] != evidence["page_sequence"]
            or type(margin_band["input_page_line_count"]) is not int
            or type(source_axis) is not list
            or margin_band["input_page_line_count"] < len(source_axis)
            or margin_band["input_page_line_count"] != full_page_band["input_page_line_count"]
            or any(
                not same_typed_json_v1(_validate_extreme_margin_line_record(line), line)
                for line in source_axis
            )
            or source_axis
            != sorted(source_axis, key=lambda item: (item["line_ordinal"], item["bbox"]))
            or len({item["line_ordinal"] for item in source_axis}) != len(source_axis)
            or len({item["sample_id"] for item in source_axis}) != len(source_axis)
            or margin_band["source_line_axis_sha256"] != canonical_json_sha256_v1(source_axis)
            or type(peer_ordinals) is not list
            or peer_ordinals != sorted(set(peer_ordinals))
        ):
            raise _error("extreme-margin complete source-band denominator drifted")
        candidate_lines = [
            line for line in source_axis if line["sample_id"] == evidence["sample_id"]
        ]
        candidate_source_line = evidence["candidate_crop_proof"].get("source_line_record")
        if (
            len(candidate_lines) != 1
            or not same_typed_json_v1(candidate_lines[0], candidate_source_line)
            or candidate_lines[0]["bbox"] != source["bbox"]
            or candidate_lines[0]["line_ordinal"] != source["line_ordinal"]
            or candidate_lines[0]["crop_ref"] != source["crop_ref"]
            or candidate_lines[0]["numeric_raw_prediction"] != source["raw_prediction"]
            or candidate_lines[0]["numeric_reader_score"] != source["reader_score"]
            or row_v1.parse_visible_financial_numeric_token_v1(candidate_lines[0]["vietocr_text"])[
                "classification"
            ]
            != "SIGNED_NUMBER"
            or any(
                line["bbox"][0] * 20 < geometry["page_width"] * 19
                or geometry["page_width"] - line["bbox"][2]
                > max(
                    bbox[3] - bbox[1],
                    line["bbox"][3] - line["bbox"][1],
                )
                or min(line["bbox"][2], bbox[2]) <= max(line["bbox"][0], bbox[0])
                or not (line["vietocr_text"].strip() or line["numeric_raw_prediction"].strip())
                for line in source_axis
            )
            or not set(peer_ordinals).issubset(
                _extreme_margin_geometric_peer_ordinals(source_axis, candidate_lines[0])
            )
            or any(
                not _extreme_margin_peer_surfaces_are_nonnumeric(
                    next(line for line in source_axis if line["line_ordinal"] == ordinal)
                )
                for ordinal in peer_ordinals
            )
            or not _extreme_margin_has_bidirectional_peers(
                source_axis, candidate_lines[0], peer_ordinals
            )
        ):
            raise _error("extreme-margin candidate or repeated peer source binding drifted")
        candidate_crop = _validate_extreme_margin_crop_proof(evidence["candidate_crop_proof"])
        peer_crops = evidence["peer_crop_proofs"]
        source_axis_by_ordinal = {line["line_ordinal"]: line for line in source_axis}
        if (
            candidate_crop["render_binding"]["physical_page"] != evidence["page_sequence"]
            or candidate_crop["render_binding"]["render_ref"]["pixel_width"]
            != geometry["page_width"]
            or type(peer_crops) is not list
            or [proof["source_line_record"]["line_ordinal"] for proof in peer_crops]
            != peer_ordinals
            or any(
                _validate_extreme_margin_crop_proof(proof)["render_binding"]["physical_page"]
                != evidence["page_sequence"]
                for proof in peer_crops
            )
            or any(
                not same_typed_json_v1(
                    proof["source_line_record"],
                    source_axis_by_ordinal.get(proof["source_line_record"]["line_ordinal"]),
                )
                for proof in peer_crops
            )
            or any(
                proof["render_binding"]["render_id"]
                != candidate_crop["render_binding"]["render_id"]
                or proof["render_binding"]["document_ordinal"]
                != candidate_crop["render_binding"]["document_ordinal"]
                or not same_typed_json_v1(
                    proof["render_binding"]["render_ref"],
                    candidate_crop["render_binding"]["render_ref"],
                )
                for proof in peer_crops
            )
        ):
            raise _error("extreme-margin authenticated chromatic peer axis drifted")
        expected_final = canonical_clone_v1(source)
        expected_final["owner_kind"] = _EXTREME_MARGIN_FURNITURE_OWNER_KIND
        expected_final["owner_id"] = evidence_id
        if not same_typed_json_v1(universe_by_sample.get(evidence["sample_id"]), expected_final):
            raise _error("extreme-margin furniture universe owner drifted")
        evidence_ids.append(evidence_id)
        sample_ids.append(evidence["sample_id"])
    if len(evidence_ids) != len(set(evidence_ids)) or len(sample_ids) != len(set(sample_ids)):
        raise _error("authenticated extreme-margin furniture ownership repeats")
    return set(sample_ids)


def _validate_numeric_sample_universe(
    value: Mapping[str, Any],
    axis: Mapping[str, Any],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    universe = value["numeric_sample_universe"]
    clusters = value["internal_unassigned_numeric_clusters"]
    if (
        type(universe) is not list
        or len(universe) > _MAX_NUMERIC_SAMPLES
        or type(clusters) is not list
        or len(clusters) > _MAX_ROLE_OCCURRENCES
    ):
        raise _error("numeric sample universe or internal cluster axis drifted")
    sample_ids: list[str] = []
    by_sample: dict[str, Mapping[str, Any]] = {}
    for record in universe:
        _validate_numeric_sample_record(record)
        sample_ids.append(record["sample_id"])
        by_sample[record["sample_id"]] = record
    if len(sample_ids) != len(set(sample_ids)) or universe != sorted(
        universe,
        key=lambda record: (
            record["page_sequence"],
            record["line_ordinal"],
            record["column_ordinal"],
            record["sample_id"],
        ),
    ):
        raise _error("numeric sample universe identity or source order drifted")
    furniture_sample_ids = _validate_extreme_margin_furniture_evidence_axis(
        value["authenticated_extreme_margin_furniture_evidence"],
        universe_by_sample=by_sample,
        axis=axis,
        topology_candidates_id=value["topology_candidates_id"],
    )

    expected_owned: dict[str, dict[str, Any]] = {}

    def expect(value_record: Mapping[str, Any], *, owner_kind: str, owner_id: str) -> None:
        expected = _numeric_universe_record(
            value_record,
            owner_kind=owner_kind,
            owner_id=owner_id,
        )
        sample_id = expected["sample_id"]
        if sample_id in expected_owned:
            raise _error("numeric sample received more than one non-source-only owner")
        expected_owned[sample_id] = expected

    for row in axis["rows"]:
        occurrence_id = row["label_match"].get("occurrence_id")
        for value_record in row["values"]:
            expect(value_record, owner_kind="ROLE_OCCURRENCE", owner_id=occurrence_id)
    for trailing in axis["trailing_value_rows"]:
        owner_id = f"aforav2:trailing:{trailing['candidate_ordinal']}"
        for value_record in trailing["values"]:
            expect(value_record, owner_kind="TRAILING_VALUE_ROW", owner_id=owner_id)
    for evidence in value["coextensive_structural_numeric_evidence"]:
        if evidence["status"] != total_v1.COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_STATUS:
            continue
        if evidence["owner_occurrence_id"] not in occurrence_by_id:
            raise _error("coextensive numeric universe owner is absent")
        for value_record in evidence["source_record"]["values"]:
            expect(
                value_record,
                owner_kind="COEXTENSIVE_SCOPE_TOTAL_REFERENCE",
                owner_id=evidence["owner_occurrence_id"],
            )

    cluster_ids: list[str] = []
    source_only_ids: list[str] = []
    for cluster in clusters:
        if (
            type(cluster) is not dict
            or set(cluster) != _INTERNAL_UNASSIGNED_CLUSTER_FIELDS
            or cluster["status"]
            not in {_INTERNAL_UNASSIGNED_CLUSTER_STATUS, _OFF_LANE_NUMERIC_CLUSTER_STATUS}
            or type(cluster["page_sequence"]) is not int
            or cluster["page_sequence"] <= 0
            or type(cluster["sample_ids"]) is not list
            or not cluster["sample_ids"]
            or len(cluster["sample_ids"]) != len(set(cluster["sample_ids"]))
            or any(type(item) is not str or not item for item in cluster["sample_ids"])
            or type(cluster["column_ordinals"]) is not list
            or len(cluster["column_ordinals"]) != len(cluster["sample_ids"])
            or any(type(item) is not int or item < 0 for item in cluster["column_ordinals"])
            or cluster["label_lane_status"]
            not in {_UNLABELED_LABEL_LANE_STATUS, _LABELED_LABEL_LANE_STATUS}
            or type(cluster["same_row_label_evidence"]) is not list
            or any(
                type(item) is not dict
                or set(item) != _SAME_ROW_LABEL_EVIDENCE_FIELDS
                or type(item["bbox"]) is not list
                or len(item["bbox"]) != 4
                or any(type(coordinate) is not int for coordinate in item["bbox"])
                or type(item["line_ordinal"]) is not int
                or item["line_ordinal"] < 0
                or type(item["numeric_raw_prediction"]) is not str
                or type(item["vietocr_text"]) is not str
                for item in cluster["same_row_label_evidence"]
            )
            or (cluster["label_lane_status"] == _UNLABELED_LABEL_LANE_STATUS)
            != (not cluster["same_row_label_evidence"])
        ):
            raise _error("internal unassigned numeric cluster drifted")
        _validate_inspected_label_band(cluster, by_sample)
        material = canonical_clone_v1(cluster)
        cluster_id = material.pop("cluster_id", None)
        if type(
            cluster_id
        ) is not str or cluster_id != "aforav2:unassigned:" + canonical_json_sha256_v1(material):
            raise _error("internal unassigned numeric cluster identity drifted")
        for sample_id, column_ordinal in zip(
            cluster["sample_ids"], cluster["column_ordinals"], strict=True
        ):
            sample = by_sample.get(sample_id)
            if (
                type(sample) is not dict
                or sample["page_sequence"] != cluster["page_sequence"]
                or sample["column_ordinal"] != column_ordinal
                or sample["owner_kind"] != "SOURCE_ONLY_INTERNAL_CLUSTER"
                or sample["owner_id"] != cluster_id
            ):
                raise _error("internal cluster differs from its source-only universe samples")
            source_only_ids.append(sample_id)
        cluster_ids.append(cluster_id)
    if len(cluster_ids) != len(set(cluster_ids)) or len(source_only_ids) != len(
        set(source_only_ids)
    ):
        raise _error("internal unassigned numeric cluster ownership repeats")
    if (
        set(expected_owned) & set(source_only_ids)
        or set(expected_owned) & furniture_sample_ids
        or set(source_only_ids) & furniture_sample_ids
        or set(by_sample)
        != {
            *expected_owned,
            *source_only_ids,
            *furniture_sample_ids,
        }
    ):
        raise _error("numeric sample universe is not one exact owned/source-only partition")
    if any(
        not same_typed_json_v1(by_sample[sample_id], expected)
        for sample_id, expected in expected_owned.items()
    ):
        raise _error("numeric sample universe differs from its exact source owner")


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
        or type(value["authenticated_extreme_margin_furniture_evidence"]) is not list
        or len(value["authenticated_extreme_margin_furniture_evidence"]) > _MAX_ROLE_OCCURRENCES
        or type(value["coextensive_structural_numeric_evidence"]) is not list
        or len(value["coextensive_structural_numeric_evidence"]) > _MAX_ROLE_OCCURRENCES
        or type(value["structural_owner_only_rescue_rejections"]) is not list
        or len(value["structural_owner_only_rescue_rejections"]) > _MAX_ROLE_OCCURRENCES
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
    from bctc_ai.evaluation import (  # noqa: PLC0415
        accounting_family_one_edit_exact_authority_v1 as one_edit_v1,
    )

    try:
        one_edit_proofs = (
            one_edit_v1.validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(
                value["one_edit_exact_source_structural_proofs"]
            )
        )
    except one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error as exc:
        raise _error("one-edit exact-source structural proof receipt drifted") from exc
    if one_edit_proofs["family_id"] != value["family_id"]:
        raise _error("one-edit exact-source structural proof family drifted")
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
    retrieval_occurrence_ids = [
        item.get("retrieval_occurrence_id") for item in value["role_occurrences"]
    ]
    if (
        any(
            type(item) is not dict or set(item) != _OCCURRENCE_FIELDS
            for item in value["role_occurrences"]
        )
        or any(type(item) is not str or not item for item in occurrence_ids)
        or len(occurrence_ids) != len(set(occurrence_ids))
        or any(type(item) is not str or not item for item in retrieval_occurrence_ids)
        or len(retrieval_occurrence_ids) != len(set(retrieval_occurrence_ids))
    ):
        raise _error("role occurrence identity axis repeats or drifted")
    occurrence_by_id = {item["occurrence_id"]: item for item in value["role_occurrences"]}
    proof_checks_by_occurrence_id = {
        check["occurrence_id"]: check
        for check in one_edit_proofs["checks"]
        if check["match_scope"] == "EXPANDED_OCCURRENCE"
    }
    if any(
        (
            str(item["label_match"].get("match_kind", "")).startswith("ONE_EDIT_")
            and (
                item["retrieval_occurrence_id"] not in proof_checks_by_occurrence_id
                or proof_checks_by_occurrence_id[item["retrieval_occurrence_id"]].get("role")
                != item["label_match"].get("retrieval_role")
                or proof_checks_by_occurrence_id[item["retrieval_occurrence_id"]].get("within_role")
                != item["label_match"].get("retrieval_within_role")
            )
        )
        or (
            "one_edit_exact_source_authority_check" in item["label_match"]
            and (
                _bound_one_edit_exact_source_check(item["label_match"]) is None
                or not same_typed_json_v1(
                    item["label_match"]["one_edit_exact_source_authority_check"],
                    proof_checks_by_occurrence_id.get(item["retrieval_occurrence_id"]),
                )
            )
        )
        for item in value["role_occurrences"]
    ):
        raise _error("one-edit exact-source structural occurrence proof drifted")
    retrieval_proxies = []
    for item in value["role_occurrences"]:
        label = canonical_clone_v1(item["label_match"])
        if (
            type(label.get("retrieval_role")) is not str
            or not label["retrieval_role"]
            or type(label.get("retrieval_role_kind")) is not str
            or not label["retrieval_role_kind"]
            or type(label.get("retrieval_role_occurrence_ordinal")) is not int
            or label["retrieval_role_occurrence_ordinal"] < 0
            or label.get("retrieval_within_role") is not None
            and (
                type(label["retrieval_within_role"]) is not str
                or not label["retrieval_within_role"]
            )
        ):
            raise _error("retrieval occurrence semantic identity drifted")
        label["role"] = label["retrieval_role"]
        label["role_kind"] = label["retrieval_role_kind"]
        label["role_occurrence_ordinal"] = label["retrieval_role_occurrence_ordinal"]
        label["matched_within_role"] = label["retrieval_within_role"]
        label.pop("occurrence_id", None)
        label.pop("scope_owner_occurrence_id", None)
        label.pop("scope_owner_role", None)
        retrieval_proxies.append(label)
    try:
        replayed_retrieval = _decorate_scopes(retrieval_proxies, axis["topology_region"])
    except AccountingFamilyOccurrenceRowAxisV2Error as exc:
        raise _error("retrieval occurrence owner replay failed") from exc
    replayed_retrieval_by_id = {item["occurrence_id"]: item for item in replayed_retrieval}

    def retrieval_physical_signature(match: Mapping[str, Any]) -> dict[str, Any]:
        explicit_indices = match.get("source_line_indices")
        return {
            "document_line_ordinal": match["document_line_ordinal"],
            "end_document_line_ordinal": match["end_document_line_ordinal"],
            "end_source_line_index": match["end_source_line_index"],
            "matched_within_role": match.get("matched_within_role"),
            "page_sequence": match["page_sequence"],
            "role": match["role"],
            "role_kind": match["role_kind"],
            "role_occurrence_ordinal": match["role_occurrence_ordinal"],
            "source_label_bbox": canonical_clone_v1(match.get("source_label_bbox")),
            "source_line_index": match["source_line_index"],
            "source_line_indices": (
                list(explicit_indices)
                if type(explicit_indices) is list
                else list(range(match["source_line_index"], match["end_source_line_index"] + 1))
            ),
        }

    # Bind every final projected item to the retrieval occurrence reconstructed
    # from that same physical row.  Set membership is insufficient: two exact
    # repeated rows with the same role and owner could otherwise exchange their
    # retrieval IDs while leaving both IDs and both owners globally valid.
    if (
        len(replayed_retrieval_by_id) != len(replayed_retrieval)
        or len(replayed_retrieval) != len(value["role_occurrences"])
        or any(
            item["retrieval_occurrence_id"] != replayed["occurrence_id"]
            or item["retrieval_scope_owner_occurrence_id"] != replayed["scope_owner_occurrence_id"]
            or not same_typed_json_v1(
                retrieval_physical_signature(retrieval_proxies[index]),
                retrieval_physical_signature(replayed),
            )
            for index, (item, replayed) in enumerate(
                zip(value["role_occurrences"], replayed_retrieval, strict=True)
            )
        )
    ):
        raise _error("retrieval occurrence physical identity or owner drifted")
    row_occurrence_ids = {row["label_match"].get("occurrence_id") for row in axis["rows"]}
    row_by_occurrence = {row["label_match"].get("occurrence_id"): row for row in axis["rows"]}
    root_scope_ids = {
        item["scope_owner_occurrence_id"]
        for item in value["role_occurrences"]
        if item["scope_owner_role"] is None
    }
    if len(root_scope_ids) != 1 or any(
        type(item["has_bound_value_row"]) is not bool
        or type(item["scope_owner_match_kind"]) is not str
        or not item["scope_owner_match_kind"]
        or type(item["label_match"]) is not dict
        or item["label_match"].get("occurrence_id") != item["occurrence_id"]
        or item["label_match"].get("retrieval_occurrence_id") != item["retrieval_occurrence_id"]
        or item["label_match"].get("retrieval_scope_owner_occurrence_id")
        != item["retrieval_scope_owner_occurrence_id"]
        or item["label_match"].get("role") != item["role"]
        or item["label_match"].get("role_kind") != item["role_kind"]
        or item["label_match"].get("scope_owner_occurrence_id") != item["scope_owner_occurrence_id"]
        or item["label_match"].get("scope_owner_role") != item["scope_owner_role"]
        or not same_typed_json_v1(
            item["source_scope_binding"], item["label_match"].get("source_scope_binding")
        )
        or item["has_bound_value_row"] is not (item["occurrence_id"] in row_occurrence_ids)
        or (
            item["has_bound_value_row"]
            and not same_typed_json_v1(
                item["label_match"], row_by_occurrence[item["occurrence_id"]]["label_match"]
            )
        )
        or (
            item["scope_owner_role"] is not None
            and (
                item["scope_owner_occurrence_id"] not in occurrence_by_id
                or occurrence_by_id[item["scope_owner_occurrence_id"]]["role"]
                != item["scope_owner_role"]
                or occurrence_by_id[item["scope_owner_occurrence_id"]]["label_match"].get(
                    "match_kind"
                )
                != item["scope_owner_match_kind"]
            )
        )
        for item in value["role_occurrences"]
    ):
        raise _error("role occurrence nearest-parent scope axis drifted")
    for item in value["role_occurrences"]:
        if item["scope_owner_role"] is None:
            continue
        child = item["label_match"]
        eligible = []
        for candidate in value["role_occurrences"]:
            if (
                candidate["role"] != item["scope_owner_role"]
                or candidate["occurrence_id"] == item["occurrence_id"]
            ):
                continue
            parent = candidate["label_match"]
            source_precedes = parent["document_line_ordinal"] <= child["document_line_ordinal"]
            parent_bbox = parent.get("source_label_bbox")
            child_bbox = child.get("source_label_bbox")
            visual_precedes = False
            if (
                parent["page_sequence"] == child["page_sequence"]
                and type(parent_bbox) is list
                and type(child_bbox) is list
            ):
                text_height = max(
                    parent_bbox[3] - parent_bbox[1],
                    child_bbox[3] - child_bbox[1],
                )
                visual_precedes = (
                    parent_bbox[1] <= child_bbox[1]
                    and parent_bbox[3] <= child_bbox[3]
                    and 2 * (child_bbox[1] - parent_bbox[3]) >= -text_height
                )
            if source_precedes or visual_precedes:
                eligible.append(candidate)
        expected_owner = max(
            eligible,
            key=lambda candidate: (
                candidate["label_match"]["page_sequence"],
                candidate["label_match"].get(
                    "source_label_bbox",
                    [
                        0,
                        candidate["label_match"]["document_line_ordinal"],
                        0,
                        candidate["label_match"]["end_document_line_ordinal"],
                    ],
                )[1],
                candidate["label_match"].get(
                    "source_label_bbox",
                    [
                        0,
                        candidate["label_match"]["document_line_ordinal"],
                        0,
                        candidate["label_match"]["end_document_line_ordinal"],
                    ],
                )[3],
                candidate["label_match"]["document_line_ordinal"],
            ),
            default=None,
        )
        if (
            expected_owner is None
            or expected_owner["occurrence_id"] != item["scope_owner_occurrence_id"]
        ):
            raise _error("role occurrence nearest visual parent replay drifted")
    _validate_structural_owner_only_rescue_rejections(
        value["structural_owner_only_rescue_rejections"],
        axis,
        value["role_occurrences"],
    )
    for item in value["role_occurrences"]:
        _validate_source_scope_binding(
            item["source_scope_binding"],
            label_match=item["label_match"],
            role=item["role"],
        )
        if item["role"] in _EXPLICIT_GROUP_TOTAL_TARGET_SOURCES and (
            type(item["source_scope_binding"]) is not dict
            or item["source_scope_binding"].get("binding_kind")
            != _EXPLICIT_GROUP_TOTAL_BINDING_KIND
        ):
            raise _error("explicit group total lacks its exact parent-interval receipt")
    actual_span_occurrences: dict[str, list[Mapping[str, Any]]] = {}
    for occurrence in value["role_occurrences"]:
        span = _source_span(occurrence["label_match"])
        actual_span_occurrences.setdefault(canonical_json_sha256_v1(span), []).append(occurrence)
    currency_roles = set(_DISCOUNT_SCOPE_TARGETS)
    generic_provision_sources = [
        item
        for item in value["role_occurrences"]
        if item["role"] == _PROVISION_GENERIC_ROLE
        or (
            type(item.get("source_scope_binding")) is dict
            and item["source_scope_binding"].get("source_role") == _PROVISION_GENERIC_ROLE
        )
    ]
    generic_discount_sources = [
        item
        for item in value["role_occurrences"]
        if item["role"] == _DISCOUNT_GENERIC_ROLE
        or (
            type(item.get("source_scope_binding")) is dict
            and item["source_scope_binding"].get("source_role") == _DISCOUNT_GENERIC_ROLE
        )
    ]
    explicit_group_total_sources = [
        item
        for item in value["role_occurrences"]
        if item["role"] in _EXPLICIT_GROUP_TOTAL_ROLES
        or (
            type(item.get("source_scope_binding")) is dict
            and item["source_scope_binding"].get("source_role") in _EXPLICIT_GROUP_TOTAL_ROLES
        )
    ]

    def explicit_total_physical_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
        label = item["label_match"]
        explicit_indices = label.get("source_line_indices")
        return (
            label["page_sequence"],
            label["document_line_ordinal"],
            label["end_document_line_ordinal"],
            tuple(
                explicit_indices
                if type(explicit_indices) is list
                else range(label["source_line_index"], label["end_source_line_index"] + 1)
            ),
            label["normalized_surface"],
        )

    explicit_total_physical_keys = [
        explicit_total_physical_key(item) for item in explicit_group_total_sources
    ]
    if len(set(explicit_total_physical_keys)) != len(explicit_total_physical_keys):
        raise _error("one physical explicit group total has duplicate typed occurrences")

    for occurrence in value["role_occurrences"]:
        receipt = occurrence["source_scope_binding"]
        anchor_span = receipt.get("anchor_span") if type(receipt) is dict else None
        if anchor_span is None:
            continue
        anchors = actual_span_occurrences.get(canonical_json_sha256_v1(anchor_span), [])
        if len(anchors) != 1 or not same_typed_json_v1(
            _source_span(anchors[0]["label_match"]), anchor_span
        ):
            raise _error("reviewed schema source-scope anchor is not one actual occurrence")
        anchor = anchors[0]
        source_match = occurrence["label_match"]
        anchor_match = anchor["label_match"]
        anchor_exact_check = receipt.get("anchor_exact_source_authority_check")
        if anchor_exact_check is not None and (
            _bound_one_edit_exact_source_check(anchor_match) is None
            or not same_typed_json_v1(
                anchor_exact_check,
                anchor_match.get("one_edit_exact_source_authority_check"),
            )
        ):
            raise _error("reviewed schema source-scope anchor exact-source proof drifted")
        if (
            anchor_match["page_sequence"] != source_match["page_sequence"]
            or anchor_match["end_document_line_ordinal"] >= source_match["document_line_ordinal"]
        ):
            raise _error("reviewed schema source-scope anchor does not precede its source")
        kind = receipt["binding_kind"]
        if kind == _EXPLICIT_GROUP_TOTAL_BINDING_KIND:
            source_role = receipt["source_role"]
            target_role = occurrence["role"]
            target_definition = _EXPLICIT_GROUP_TOTAL_TARGET_SOURCES.get(target_role)
            if target_definition is None:
                raise _error("explicit group total receipt targets an unknown role")
            expected_source_role, owner_role = target_definition
            retrieval_role = source_match.get("retrieval_role", source_match.get("role"))
            retrieval_within_role = source_match.get(
                "retrieval_within_role", source_match.get("matched_within_role")
            )
            if source_role != retrieval_role or not (
                retrieval_role == expected_source_role
                and retrieval_within_role is None
                or retrieval_role == target_role
                and retrieval_within_role == owner_role
                and source_match.get("retrieval_scope_owner_occurrence_id")
                == anchor["occurrence_id"]
            ):
                raise _error("explicit group total receipt source role drifted")
            source_ordinal = source_match["document_line_ordinal"]
            page_sequence = source_match["page_sequence"]
            preceding_top = [
                item
                for item in value["role_occurrences"]
                if item["role"] in {"INTERBANK_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"}
                and item["label_match"]["page_sequence"] == page_sequence
                and item["label_match"]["document_line_ordinal"] < source_ordinal
            ]
            nearest_owner_ordinal = max(
                (item["label_match"]["document_line_ordinal"] for item in preceding_top),
                default=None,
            )
            nearest_owners = [
                item
                for item in preceding_top
                if item["label_match"]["document_line_ordinal"] == nearest_owner_ordinal
            ]
            owner = nearest_owners[0] if len(nearest_owners) == 1 else None
            later_boundaries = [
                item
                for item in value["role_occurrences"]
                if item["role"]
                in {
                    "EXPLICIT_FAMILY_TOTAL",
                    "INTERBANK_DEPOSIT_GROUP",
                    "INTERBANK_LOAN_GROUP",
                }
                and item["label_match"]["page_sequence"] == page_sequence
                and item["label_match"]["document_line_ordinal"] > source_ordinal
            ]
            nearest_boundary_ordinal = min(
                (item["label_match"]["document_line_ordinal"] for item in later_boundaries),
                default=None,
            )
            nearest_boundaries = [
                item
                for item in later_boundaries
                if item["label_match"]["document_line_ordinal"] == nearest_boundary_ordinal
            ]
            boundary = nearest_boundaries[0] if len(nearest_boundaries) == 1 else None

            def total_target(item: Mapping[str, Any]) -> str | None:
                item_role = item["role"]
                if item_role in _EXPLICIT_GROUP_TOTAL_TARGET_SOURCES:
                    return item_role
                if item_role in _EXPLICIT_GROUP_TOTAL_SOURCE_TARGETS:
                    return _EXPLICIT_GROUP_TOTAL_SOURCE_TARGETS[item_role][0]
                binding = item.get("source_scope_binding")
                binding_source = binding.get("source_role") if type(binding) is dict else None
                if binding_source in _EXPLICIT_GROUP_TOTAL_SOURCE_TARGETS:
                    return _EXPLICIT_GROUP_TOTAL_SOURCE_TARGETS[binding_source][0]
                return None

            interval_totals = [
                item
                for item in explicit_group_total_sources
                if owner is not None
                and boundary is not None
                and total_target(item) == target_role
                and item["label_match"]["page_sequence"] == page_sequence
                and owner["label_match"]["document_line_ordinal"]
                < item["label_match"]["document_line_ordinal"]
                < boundary["label_match"]["document_line_ordinal"]
            ]
            semantic_roles = (
                _DEPOSIT_SEMANTIC_INTERVAL_ROLES
                if owner_role == "INTERBANK_DEPOSIT_GROUP"
                else _LOAN_SEMANTIC_INTERVAL_ROLES
            )
            prior_semantics = [
                item
                for item in value["role_occurrences"]
                if owner is not None
                and item["role"] in semantic_roles
                and item["role"] != owner_role
                and item["label_match"]["page_sequence"] == page_sequence
                and owner["label_match"]["document_line_ordinal"]
                < item["label_match"]["document_line_ordinal"]
                < source_ordinal
                and _match_has_effective_exact_source_authority(item["label_match"])
            ]
            later_semantics = [
                item
                for item in value["role_occurrences"]
                if boundary is not None
                and item["role"] in semantic_roles
                and item["label_match"]["page_sequence"] == page_sequence
                and source_ordinal
                < item["label_match"]["document_line_ordinal"]
                < boundary["label_match"]["document_line_ordinal"]
            ]
            if (
                not _match_has_effective_exact_source_authority(source_match)
                or owner is None
                or owner["role"] != owner_role
                or not _match_has_effective_exact_source_authority(owner["label_match"])
                or owner["occurrence_id"] != anchor["occurrence_id"]
                or boundary is None
                or not _match_has_effective_exact_source_authority(boundary["label_match"])
                or len(interval_totals) != 1
                or interval_totals[0]["occurrence_id"] != occurrence["occurrence_id"]
                or not prior_semantics
                or later_semantics
                or occurrence["scope_owner_occurrence_id"] != owner["occurrence_id"]
                or occurrence["scope_owner_role"] != owner_role
                or receipt["source_scope_role"] != owner_role
                or receipt["geometry"]
                != {
                    "anchor_occurrence_id": anchor["occurrence_id"],
                    "status": _EXPLICIT_GROUP_TOTAL_PARENT_GEOMETRY_STATUS,
                }
                or receipt["interval"]["start_document_line_ordinal"]
                != owner["label_match"]["document_line_ordinal"]
                or receipt["interval"]["end_document_line_ordinal_exclusive"]
                != boundary["label_match"]["document_line_ordinal"]
            ):
                raise _error("explicit group total parent-interval proof drifted")
        elif kind == "UNIQUE_EXACT_PRECEDING_SOURCE_SUBSCOPE_INTERVAL":
            prior_loan_groups = [
                item
                for item in value["role_occurrences"]
                if item["role"] == "INTERBANK_LOAN_GROUP"
                and item["label_match"]["page_sequence"] == source_match["page_sequence"]
                and item["label_match"]["document_line_ordinal"]
                < source_match["document_line_ordinal"]
            ]
            expected_loan = max(
                prior_loan_groups,
                key=lambda item: item["label_match"]["document_line_ordinal"],
                default=None,
            )
            next_loan_ordinal = min(
                (
                    item["label_match"]["document_line_ordinal"]
                    for item in value["role_occurrences"]
                    if item["role"] == "INTERBANK_LOAN_GROUP"
                    and item["label_match"]["document_line_ordinal"]
                    > source_match["document_line_ordinal"]
                ),
                default=2**63 - 1,
            )
            preceding_currency = [
                item
                for item in value["role_occurrences"]
                if item["role"] in currency_roles
                and item["label_match"]["page_sequence"] == source_match["page_sequence"]
                and item["label_match"]["end_document_line_ordinal"]
                < source_match["document_line_ordinal"]
                and _match_has_effective_exact_source_authority(item["label_match"])
                and type(expected_loan) is dict
                and item["label_match"]["document_line_ordinal"]
                >= expected_loan["label_match"]["document_line_ordinal"]
            ]
            nearest_end = max(
                (item["label_match"]["end_document_line_ordinal"] for item in preceding_currency),
                default=-1,
            )
            nearest = [
                item
                for item in preceding_currency
                if item["label_match"]["end_document_line_ordinal"] == nearest_end
            ]
            intervening_loan_siblings = [
                item
                for item in value["role_occurrences"]
                if item["occurrence_id"]
                not in {occurrence["occurrence_id"], anchor["occurrence_id"]}
                and item["role"] in _LOAN_SOURCE_SUBSCOPE_BOUNDARY_ROLES
                and anchor_match["end_document_line_ordinal"]
                < item["label_match"]["document_line_ordinal"]
                < source_match["document_line_ordinal"]
            ]
            generic_discount_ids = {item["occurrence_id"] for item in generic_discount_sources}
            non_generic_boundaries = [
                item["label_match"]["document_line_ordinal"]
                for item in value["role_occurrences"]
                if item["occurrence_id"] not in generic_discount_ids
                and item["role"] in _LOAN_SOURCE_SUBSCOPE_BOUNDARY_ROLES
                and anchor_match["end_document_line_ordinal"]
                < item["label_match"]["document_line_ordinal"]
                < next_loan_ordinal
            ]
            source_subscope_end = min(non_generic_boundaries, default=next_loan_ordinal)
            interval_generic_discounts = [
                item
                for item in generic_discount_sources
                if anchor_match["end_document_line_ordinal"]
                < item["label_match"]["document_line_ordinal"]
                < source_subscope_end
            ]
            explicit_same_target = [
                item
                for item in value["role_occurrences"]
                if item["occurrence_id"] != occurrence["occurrence_id"]
                and item["role"] == occurrence["role"]
                and item["occurrence_id"] not in generic_discount_ids
                and type(expected_loan) is dict
                and expected_loan["label_match"]["document_line_ordinal"]
                <= item["label_match"]["document_line_ordinal"]
                < next_loan_ordinal
            ]
            if (
                expected_loan is None
                or len(nearest) != 1
                or nearest[0]["occurrence_id"] != anchor["occurrence_id"]
                or anchor["scope_owner_occurrence_id"] != expected_loan["occurrence_id"]
                or occurrence["scope_owner_occurrence_id"] != anchor["occurrence_id"]
                or intervening_loan_siblings
                or len(interval_generic_discounts) != 1
                or explicit_same_target
                or receipt["interval"]["start_document_line_ordinal"]
                != anchor_match["document_line_ordinal"]
                or receipt["interval"]["end_document_line_ordinal_exclusive"]
                != source_match["end_document_line_ordinal"] + 1
            ):
                raise _error(
                    "discount source subscope is not the nearest exact currency occurrence"
                )
        elif kind == "EXACT_DEPOSIT_SUBTREE_BEFORE_NEXT_LOAN_BOUNDARY":
            source_ordinal = source_match["document_line_ordinal"]
            prior_deposits = [
                item
                for item in value["role_occurrences"]
                if item["role"] in _DEPOSIT_SCOPE_ROLES
                and item["label_match"]["page_sequence"] == source_match["page_sequence"]
                and item["label_match"]["document_line_ordinal"] < source_ordinal
                and _match_has_effective_exact_source_authority(item["label_match"])
            ]
            active_deposit_groups = [
                item for item in prior_deposits if item["role"] == "INTERBANK_DEPOSIT_GROUP"
            ]
            if active_deposit_groups:
                active_deposit_start = max(
                    item["label_match"]["document_line_ordinal"] for item in active_deposit_groups
                )
                prior_deposits = [
                    item
                    for item in prior_deposits
                    if item["label_match"]["document_line_ordinal"] >= active_deposit_start
                ]
            prior_loans = [
                item
                for item in value["role_occurrences"]
                if item["role"] == "INTERBANK_LOAN_GROUP"
                and item["label_match"]["page_sequence"] == source_match["page_sequence"]
                and item["label_match"]["document_line_ordinal"] < source_ordinal
            ]
            later_loans = [
                item
                for item in value["role_occurrences"]
                if item["role"] == "INTERBANK_LOAN_GROUP"
                and item["label_match"]["page_sequence"] == source_match["page_sequence"]
                and item["label_match"]["document_line_ordinal"] > source_ordinal
            ]
            next_loan_ordinal = min(
                (item["label_match"]["document_line_ordinal"] for item in later_loans),
                default=None,
            )
            later_deposits_before_loan = [
                item
                for item in value["role_occurrences"]
                if item["role"] in _DEPOSIT_SEMANTIC_INTERVAL_ROLES
                and item["occurrence_id"] != occurrence["occurrence_id"]
                and source_ordinal < item["label_match"]["document_line_ordinal"]
                and type(next_loan_ordinal) is int
                and item["label_match"]["document_line_ordinal"] < next_loan_ordinal
            ]
            incompatible_semantics_before_loan = [
                item
                for item in value["role_occurrences"]
                if item["occurrence_id"] != occurrence["occurrence_id"]
                and item["role"] in _LOAN_SEMANTIC_INTERVAL_ROLES
                and source_ordinal < item["label_match"]["document_line_ordinal"]
                and type(next_loan_ordinal) is int
                and item["label_match"]["document_line_ordinal"] < next_loan_ordinal
            ]
            expected_anchor = max(
                prior_deposits,
                key=lambda item: (
                    item["label_match"]["document_line_ordinal"],
                    item["label_match"]["end_document_line_ordinal"],
                    item["label_match"]["preferred_ordinal"],
                    item["role"],
                ),
                default=None,
            )
            prior_deposit_groups = [
                item for item in prior_deposits if item["role"] == "INTERBANK_DEPOSIT_GROUP"
            ]
            expected_owner = max(
                prior_deposit_groups,
                key=lambda item: (
                    item["label_match"]["document_line_ordinal"],
                    item["label_match"]["end_document_line_ordinal"],
                ),
                default=None,
            )
            deposit_interval_start = min(
                (item["label_match"]["document_line_ordinal"] for item in prior_deposits),
                default=None,
            )
            interval_provisions = [
                item
                for item in generic_provision_sources
                if type(deposit_interval_start) is int
                and type(next_loan_ordinal) is int
                and deposit_interval_start
                <= item["label_match"]["document_line_ordinal"]
                < next_loan_ordinal
            ]
            generic_provision_ids = {item["occurrence_id"] for item in generic_provision_sources}
            explicit_interval_provisions = [
                item
                for item in value["role_occurrences"]
                if item["occurrence_id"] != occurrence["occurrence_id"]
                and item["occurrence_id"] not in generic_provision_ids
                and item["role"] == "INTERBANK_DEPOSIT_PROVISION"
                and type(deposit_interval_start) is int
                and type(next_loan_ordinal) is int
                and deposit_interval_start
                <= item["label_match"]["document_line_ordinal"]
                < next_loan_ordinal
            ]
            prior_explicit_group_totals = [
                item
                for item in explicit_group_total_sources
                if type(deposit_interval_start) is int
                and deposit_interval_start
                < item["label_match"]["document_line_ordinal"]
                < source_ordinal
            ]
            if (
                expected_anchor is None
                or expected_anchor["occurrence_id"] != anchor["occurrence_id"]
                or len(interval_provisions) != 1
                or explicit_interval_provisions
                or prior_explicit_group_totals
                or prior_loans
                or not later_loans
                or later_deposits_before_loan
                or incompatible_semantics_before_loan
                or receipt["interval"]["start_document_line_ordinal"] != deposit_interval_start
                or receipt["interval"]["end_document_line_ordinal_exclusive"]
                != min(item["label_match"]["document_line_ordinal"] for item in later_loans)
                or (
                    expected_owner is not None
                    and occurrence["scope_owner_occurrence_id"] != expected_owner["occurrence_id"]
                )
                or (expected_owner is None and occurrence["scope_owner_role"] is not None)
            ):
                raise _error("deposit provision source does not occupy the exact deposit interval")
        elif kind == "EXACT_TOP_SIBLING_AFTER_COMPLETE_DEPOSIT_AND_LOAN_SUBTREES":
            source_ordinal = source_match["document_line_ordinal"]
            anchor_ordinal = anchor_match["document_line_ordinal"]
            prior_deposits = [
                item
                for item in value["role_occurrences"]
                if item["role"] in _DEPOSIT_SCOPE_ROLES
                and item["label_match"]["page_sequence"] == source_match["page_sequence"]
                and item["label_match"]["document_line_ordinal"] < source_ordinal
                and _match_has_effective_exact_source_authority(item["label_match"])
            ]
            prior_loans = [
                item
                for item in value["role_occurrences"]
                if item["role"] == "INTERBANK_LOAN_GROUP"
                and item["label_match"]["page_sequence"] == source_match["page_sequence"]
                and item["label_match"]["document_line_ordinal"] < source_ordinal
            ]
            later_loans = [
                item
                for item in value["role_occurrences"]
                if item["role"] == "INTERBANK_LOAN_GROUP"
                and item["label_match"]["page_sequence"] == source_match["page_sequence"]
                and item["label_match"]["document_line_ordinal"] > source_ordinal
            ]
            later_deposits = [
                item
                for item in value["role_occurrences"]
                if item["role"] in _DEPOSIT_SEMANTIC_INTERVAL_ROLES
                and item["occurrence_id"] != occurrence["occurrence_id"]
                and item["label_match"]["document_line_ordinal"] > source_ordinal
            ]
            expected_loan = max(
                prior_loans,
                key=lambda item: (
                    item["label_match"]["document_line_ordinal"],
                    item["label_match"]["end_document_line_ordinal"],
                ),
                default=None,
            )
            prior_leaves = [
                item
                for item in value["role_occurrences"]
                if item["role"] in _LOAN_LEAF_ROLES
                and item["label_match"]["page_sequence"] == source_match["page_sequence"]
                and anchor_ordinal <= item["label_match"]["document_line_ordinal"] < source_ordinal
                and _match_has_effective_exact_source_authority(item["label_match"])
            ]
            later_leaves = [
                item
                for item in value["role_occurrences"]
                if item["role"] in _LOAN_LEAF_ROLES
                and item["label_match"]["document_line_ordinal"] > source_ordinal
            ]
            later_loan_semantics = [
                item
                for item in value["role_occurrences"]
                if item["occurrence_id"] != occurrence["occurrence_id"]
                and item["role"] in _LOAN_SEMANTIC_INTERVAL_ROLES
                and item["label_match"]["document_line_ordinal"] > source_ordinal
            ]
            prior_explicit_group_totals = [
                item
                for item in explicit_group_total_sources
                if anchor_ordinal < item["label_match"]["document_line_ordinal"] < source_ordinal
            ]
            all_loan_leaf_occurrences = [
                item
                for item in value["role_occurrences"]
                if item["role"] in _LOAN_LEAF_ROLES
                and anchor_ordinal <= item["label_match"]["document_line_ordinal"]
            ]
            topology_region = axis["topology_region"]
            region_end = (
                topology_region.get("cluster_end_document_line_ordinal_exclusive")
                if type(topology_region) is dict
                else None
            )
            anchor_row = row_by_occurrence.get(anchor["occurrence_id"])
            exact_leaf_completion = (
                bool(prior_leaves)
                and not later_leaves
                and len(all_loan_leaf_occurrences) == len(prior_leaves)
            )
            exact_group_total_completion = (
                not all_loan_leaf_occurrences
                and type(anchor_row) is dict
                and anchor_row.get("role") == "INTERBANK_LOAN_GROUP"
                and anchor_row.get("status") == "VISIBLE_VALUE_LANES_BOUND"
                and type(anchor_row.get("values")) is list
                and bool(anchor_row["values"])
            )
            root_interval_provisions = [
                item
                for item in generic_provision_sources
                if type(region_end) is int
                and anchor_ordinal <= item["label_match"]["document_line_ordinal"] < region_end
            ]
            generic_provision_ids = {item["occurrence_id"] for item in generic_provision_sources}
            explicit_root_interval_provisions = [
                item
                for item in value["role_occurrences"]
                if item["occurrence_id"] != occurrence["occurrence_id"]
                and item["occurrence_id"] not in generic_provision_ids
                and item["role"] == "TOTAL_INTERBANK_PROVISION"
                and type(region_end) is int
                and anchor_ordinal <= item["label_match"]["document_line_ordinal"] < region_end
            ]
            if (
                not prior_deposits
                or len(root_interval_provisions) != 1
                or explicit_root_interval_provisions
                or expected_loan is None
                or expected_loan["occurrence_id"] != anchor["occurrence_id"]
                or not _match_has_effective_exact_source_authority(anchor_match)
                or not (exact_leaf_completion or exact_group_total_completion)
                or later_loans
                or later_deposits
                or later_loan_semantics
                or prior_explicit_group_totals
                or occurrence["scope_owner_role"] is not None
                or receipt["interval"]["start_document_line_ordinal"] != anchor_ordinal
                or type(region_end) is not int
                or receipt["interval"]["end_document_line_ordinal_exclusive"] != region_end
            ):
                raise _error("total provision source does not follow one complete loan subtree")
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
    _validate_numeric_sample_universe(value, axis, occurrence_by_id)
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
    one_edit_exact_source_structural_proofs, expanded_matches = (
        _one_edit_exact_source_structural_proofs_v2(
            parsed_pages,
            family_spec,
            compiled_family,
            selected_region,
            expected_effective,
            expanded_matches,
        )
    )
    expanded_matches = _project_reviewed_schema_source_scopes(
        parsed_pages,
        compiled_family,
        expanded_matches,
        selected_region,
    )
    matches = _decorate_scopes(
        expanded_matches,
        selected_region,
    )
    row_matches = matches
    expanded = _expanded_region(expected_effective, row_matches)
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
    axis, structural_owner_only_rescue_rejections = (
        _project_structural_owner_only_rescue_rejections(axis, row_matches)
    )
    try:
        axis, coextensive_evidence = (
            total_v1.project_accounting_family_coextensive_structural_numeric_rows_v1(
                axis,
                row_matches,
            )
        )
        if coextensive_evidence:
            axis = _regenerate_v1_axis(axis)
    except total_v1.AccountingFamilyCoextensiveParentTotalV1Error as exc:
        raise _error("coextensive structural numeric source projection failed") from exc
    (
        numeric_sample_universe,
        internal_unassigned_numeric_clusters,
        authenticated_extreme_margin_furniture_evidence,
        extreme_margin_render_reasons,
    ) = _build_numeric_sample_universe(
        parsed_pages,
        expanded,
        row_matches,
        axis,
        coextensive_evidence,
        topology_candidates_id=topology_candidates_id,
        selected_snapshot=selected_snapshot,
        render_snapshots=render_snapshots,
    )
    rows_by_occurrence = {row["label_match"].get("occurrence_id"): row for row in axis["rows"]}
    role_occurrences = [
        {
            "has_bound_value_row": match["occurrence_id"] in rows_by_occurrence,
            "label_match": canonical_clone_v1(match),
            "occurrence_id": match["occurrence_id"],
            "retrieval_occurrence_id": match["retrieval_occurrence_id"],
            "retrieval_scope_owner_occurrence_id": match["retrieval_scope_owner_occurrence_id"],
            "role": match["role"],
            "role_kind": match["role_kind"],
            "scope_owner_occurrence_id": match["scope_owner_occurrence_id"],
            "scope_owner_match_kind": (
                next(
                    owner["match_kind"]
                    for owner in matches
                    if owner["occurrence_id"] == match["scope_owner_occurrence_id"]
                )
                if match["scope_owner_role"] is not None
                else selected_region["parent_match"]["match_kind"]
            ),
            "scope_owner_role": match["scope_owner_role"],
            "source_scope_binding": canonical_clone_v1(match.get("source_scope_binding")),
        }
        for match in matches
    ]
    reasons = list(dash_reasons)
    reasons.extend(
        f"{evidence['status']}:{evidence['projected_occurrence_id']}"
        for evidence in coextensive_evidence
        if evidence["status"] == total_v1.COEXTENSIVE_PRECEDING_NUMERIC_AMBIGUITY_STATUS
    )
    reasons.extend(extreme_margin_render_reasons)
    if axis["status"] != "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY":
        reasons.insert(0, "VISIBLE_ROLE_OCCURRENCE_ROW_LANES_NOT_COMPLETE")
    material = {
        "authenticated_extreme_margin_furniture_evidence": (
            authenticated_extreme_margin_furniture_evidence
        ),
        "authenticated_existing_dash_evidence": dash_evidence,
        "claim_boundary": CLAIM_BOUNDARY,
        "coextensive_structural_numeric_evidence": coextensive_evidence,
        "dependency_content_refs": _dependency_refs(),
        "family_id": compiled_family["family_id"],
        "format_version": FORMAT_VERSION,
        "internal_unassigned_numeric_clusters": internal_unassigned_numeric_clusters,
        "numeric_sample_universe": numeric_sample_universe,
        "one_edit_exact_source_structural_proofs": one_edit_exact_source_structural_proofs,
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
        "structural_owner_only_rescue_rejections": (structural_owner_only_rescue_rejections),
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
