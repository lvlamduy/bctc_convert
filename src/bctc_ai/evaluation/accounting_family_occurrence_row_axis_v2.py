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
    "EXACT_PRECEDING_SCOPE_SUBTOTAL_SOURCE_OWNERSHIP_AND_REVIEWED_EXACT_"
    "SOURCE_SUBSCOPE_INTERVAL_SCHEMA_ROLE_TYPING_"
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
    "authenticated_existing_dash_evidence",
    "claim_boundary",
    "coextensive_structural_numeric_evidence",
    "dependency_content_refs",
    "family_id",
    "format_version",
    "internal_unassigned_numeric_clusters",
    "numeric_sample_universe",
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
    "COEXTENSIVE_SCOPE_TOTAL_REFERENCE",
    "ROLE_OCCURRENCE",
    "SOURCE_ONLY_INTERNAL_CLUSTER",
    "TRAILING_VALUE_ROW",
}
_SOURCE_SCOPE_BINDING_FIELDS = {
    "anchor_span",
    "binding_id",
    "binding_kind",
    "geometry",
    "interval",
    "source_role",
    "source_scope_role",
    "source_span",
    "status",
    "target_role",
}
_SOURCE_SCOPE_BINDING_STATUS = "REVIEWED_EXACT_SOURCE_SCOPE_TO_SCHEMA_ROLE_BINDING"
_AMBIGUOUS_WRAPPED_LABEL_STATUS = "SOURCE_ONLY_AMBIGUOUS_TOUCHING_WRAPPED_LABEL"
_DISCOUNT_GENERIC_ROLE = "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
_DISCOUNT_SCOPE_TARGETS = {
    "INTERBANK_LOAN_VND": "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND",
    "INTERBANK_LOAN_FOREIGN_CURRENCY": ("INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY"),
}
_PROVISION_GENERIC_ROLE = "INTERBANK_PROVISION_AMBIGUOUS"
_DEPOSIT_SCOPE_ROLES = {
    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
    "DEMAND_DEPOSIT_GROUP",
    "DEMAND_DEPOSIT_VND",
    "INTERBANK_DEPOSIT_GROUP",
    "TERM_DEPOSIT_FOREIGN_CURRENCY",
    "TERM_DEPOSIT_GROUP",
    "TERM_DEPOSIT_VND",
}
_LOAN_LEAF_ROLES = {
    *_DISCOUNT_SCOPE_TARGETS,
    *_DISCOUNT_SCOPE_TARGETS.values(),
    "INTERBANK_LOAN_GOLD_AND_FOREIGN_CURRENCY",
    "INTERBANK_LOAN_OTHER",
    "INTERBANK_LOAN_PROVISION",
}
_INTERNAL_UNASSIGNED_CLUSTER_FIELDS = {
    "cluster_id",
    "column_ordinals",
    "page_sequence",
    "sample_ids",
    "status",
}
_INTERNAL_UNASSIGNED_CLUSTER_STATUS = "SOURCE_ONLY_INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
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

    result = []
    for candidate in candidates:
        visual_preceding_fragment = (
            visual_preceding_label_fragment(candidate)
            if candidate["document_line_ordinal"] == candidate["end_document_line_ordinal"]
            and candidate["normalized_surface"] in {"cac khoan khac", "khac"}
            and candidate["role"] in {"INTERBANK_DEPOSIT_OTHER", "INTERBANK_LOAN_OTHER"}
            else None
        )
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
    result = {
        "document_line_ordinal": match["document_line_ordinal"],
        "end_document_line_ordinal": match["end_document_line_ordinal"],
        "end_source_line_index": match["end_source_line_index"],
        "match_kind": match["match_kind"],
        "normalized_surface": match["normalized_surface"],
        "page_sequence": match["page_sequence"],
        "role": match["role"],
        "source_line_index": match["source_line_index"],
    }
    if "source_label_bbox" in match:
        result["source_label_bbox"] = canonical_clone_v1(match["source_label_bbox"])
    return result


def _scope_binding(
    *,
    anchor: Mapping[str, Any] | None,
    binding_kind: str,
    geometry: Mapping[str, Any] | None,
    interval_end_exclusive: int,
    interval_start: int,
    source: Mapping[str, Any],
    source_role: str,
    source_scope_role: str,
    status: str = _SOURCE_SCOPE_BINDING_STATUS,
    target_role: str,
) -> dict[str, Any]:
    material = {
        "anchor_span": _source_span(anchor) if anchor is not None else None,
        "binding_kind": binding_kind,
        "geometry": canonical_clone_v1(geometry) if geometry is not None else None,
        "interval": {
            "end_document_line_ordinal_exclusive": interval_end_exclusive,
            "start_document_line_ordinal": interval_start,
        },
        "source_role": source_role,
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


def _same_row_numeric_samples(
    pages: Sequence[Mapping[str, Any]], match: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    page = next(
        (item for item in pages if item["page_sequence"] == match["page_sequence"]),
        None,
    )
    if type(page) is not dict:
        return []
    label_bbox = _source_line_bbox(pages, match)
    label_center_twice = label_bbox[1] + label_bbox[3]
    label_height = label_bbox[3] - label_bbox[1]
    return sorted(
        (
            line
            for line in page["lines"]
            if row_v1._is_numeric(line)  # noqa: SLF001
            and line["bbox"][0] >= label_bbox[2]
            and abs(line["bbox"][1] + line["bbox"][3] - label_center_twice)
            <= max(label_height, line["bbox"][3] - line["bbox"][1])
        ),
        key=lambda line: (line["bbox"][0], line["line_ordinal"]),
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
    required_roles = {
        _DISCOUNT_GENERIC_ROLE,
        _PROVISION_GENERIC_ROLE,
        *_DISCOUNT_SCOPE_TARGETS,
        *_DISCOUNT_SCOPE_TARGETS.values(),
        "INTERBANK_DEPOSIT_PROVISION",
        "INTERBANK_LOAN_GROUP",
        "TOTAL_INTERBANK_PROVISION",
    }
    projected = [canonical_clone_v1(match) for match in matches]
    if not required_roles <= set(by_role_definition):
        return projected
    for match in projected:
        match["source_label_bbox"] = _source_line_bbox(pages, match)
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
    currency_scopes = sorted(
        (match for match in projected if match["role"] in _DISCOUNT_SCOPE_TARGETS),
        key=lambda item: (
            item["document_line_ordinal"],
            item["end_document_line_ordinal"],
            item["role"],
        ),
    )

    # Explicit currency words are independently sufficient source-subscope
    # evidence.  Persist the same reviewed receipt shape used by interval-bound
    # generic rows so the schema mapper can fail closed on a missing/tampered
    # source-scope proof.
    for match in projected:
        reverse_scope = {target: scope for scope, target in _DISCOUNT_SCOPE_TARGETS.items()}
        source_scope_role = reverse_scope.get(match["role"])
        if source_scope_role is None or not str(match["match_kind"]).startswith("EXACT_"):
            continue
        match["source_scope_binding"] = _scope_binding(
            anchor=None,
            binding_kind="EXPLICIT_EXACT_SOURCE_SUBSCOPE_IN_LABEL",
            geometry=None,
            interval_end_exclusive=match["end_document_line_ordinal"] + 1,
            interval_start=match["document_line_ordinal"],
            source=match,
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
            if group["document_line_ordinal"] <= match["document_line_ordinal"]
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
            if loan["document_line_ordinal"] <= scope["document_line_ordinal"]
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
            str(scope["match_kind"]).startswith("EXACT_") for scope in nearest
        ):
            continue
        anchor = max(nearest, key=lambda item: item["document_line_ordinal"])
        next_currency = min(
            (
                scope["document_line_ordinal"]
                for scope in currency_scopes
                if scope["document_line_ordinal"] > anchor["document_line_ordinal"]
                and scope["document_line_ordinal"] < next_loan
            ),
            default=next_loan,
        )
        if match["document_line_ordinal"] >= next_currency:
            continue
        target_role = _DISCOUNT_SCOPE_TARGETS[anchor["role"]]
        receipt = _scope_binding(
            anchor=anchor,
            binding_kind="UNIQUE_EXACT_PRECEDING_SOURCE_SUBSCOPE_INTERVAL",
            geometry=None,
            interval_end_exclusive=next_currency,
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
    for match in projected:
        if match["role"] != _PROVISION_GENERIC_ROLE or not str(match["match_kind"]).startswith(
            "EXACT_"
        ):
            continue
        before = match["document_line_ordinal"]
        prior_deposits = [
            item
            for item in deposit_matches
            if item["document_line_ordinal"] < before
            and str(item["match_kind"]).startswith("EXACT_")
        ]
        prior_loans = [item for item in loan_groups if item["document_line_ordinal"] < before]
        later_loans = [item for item in loan_groups if item["document_line_ordinal"] > before]
        if prior_deposits and not prior_loans and later_loans:
            anchor = max(
                prior_deposits,
                key=lambda item: (
                    item["document_line_ordinal"],
                    item["end_document_line_ordinal"],
                    item["preferred_ordinal"],
                    item["role"],
                ),
            )
            if not str(anchor["match_kind"]).startswith("EXACT_"):
                continue
            receipt = _scope_binding(
                anchor=anchor,
                binding_kind="EXACT_DEPOSIT_SUBTREE_BEFORE_NEXT_LOAN_BOUNDARY",
                geometry=None,
                interval_end_exclusive=min(item["document_line_ordinal"] for item in later_loans),
                interval_start=min(item["document_line_ordinal"] for item in prior_deposits),
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
            prior_loan_leaves = [
                item
                for item in projected
                if item["role"] in _LOAN_LEAF_ROLES
                and loan["document_line_ordinal"] <= item["document_line_ordinal"] < before
                and str(item["match_kind"]).startswith("EXACT_")
            ]
            later_loan_leaves = [
                item
                for item in projected
                if item["role"] in _LOAN_LEAF_ROLES
                and before < item["document_line_ordinal"] < region_end
            ]
            all_loan_leaves = [
                item
                for item in projected
                if item["role"] in _LOAN_LEAF_ROLES
                and loan["document_line_ordinal"] <= item["document_line_ordinal"] < region_end
            ]
            exact_group_total_without_leaf_labels = not all_loan_leaves and bool(
                _same_row_numeric_samples(pages, loan)
            )
            if (
                not prior_loan_leaves and not exact_group_total_without_leaf_labels
            ) or later_loan_leaves:
                continue
            if not str(loan["match_kind"]).startswith("EXACT_"):
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
    exact_source = str(value["source_span"].get("match_kind", "")).startswith("EXACT_")
    exact_anchor = type(anchor) is dict and str(anchor.get("match_kind", "")).startswith("EXACT_")
    discount_pair = {
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND": "INTERBANK_LOAN_VND",
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY": ("INTERBANK_LOAN_FOREIGN_CURRENCY"),
    }
    kind = value["binding_kind"]
    reviewed_matrix_valid = False
    if value["status"] == _SOURCE_SCOPE_BINDING_STATUS:
        expected_subscope = discount_pair.get(role)
        if kind == "EXPLICIT_EXACT_SOURCE_SUBSCOPE_IN_LABEL":
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
                and explicit_scope_surface
                and anchor is None
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
                and exact_source
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


def _build_numeric_sample_universe(
    pages: Sequence[Mapping[str, Any]],
    expanded_region: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]],
    axis: Mapping[str, Any],
    coextensive_evidence: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
        for line in local_lines:
            if (
                line["sample_id"] in universe_by_sample
                or line["line_ordinal"] in header_indices
                or not row_v1._is_numeric(line)
            ):
                continue
            center = (line["bbox"][0] + line["bbox"][2]) / 2
            lane = min(range(len(centers)), key=lambda index: abs(center - centers[index]))
            if abs(center - centers[lane]) > lane_tolerance:
                continue
            projected = {**canonical_clone_v1(line), "source_line_index": line["line_ordinal"]}
            candidates.append(projected)
            lanes_by_sample[line["sample_id"]] = lane
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
            cluster_material = {
                "column_ordinals": [lanes_by_sample[line["sample_id"]] for line in ordered],
                "page_sequence": page_sequence,
                "sample_ids": [line["sample_id"] for line in ordered],
                "status": _INTERNAL_UNASSIGNED_CLUSTER_STATUS,
            }
            cluster_id = "aforav2:unassigned:" + canonical_json_sha256_v1(cluster_material)
            cluster = {**cluster_material, "cluster_id": cluster_id}
            clusters.append(cluster)
            for line in ordered:
                lane = lanes_by_sample[line["sample_id"]]
                value = row_v1._value_record(
                    page_sequence,
                    line,
                    column_center=centers[lane],
                    column_ordinal=lane,
                    row_affinity=None,
                )
                own(
                    value,
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
    return universe, clusters


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
            or cluster["status"] != _INTERNAL_UNASSIGNED_CLUSTER_STATUS
            or type(cluster["page_sequence"]) is not int
            or cluster["page_sequence"] <= 0
            or type(cluster["sample_ids"]) is not list
            or not cluster["sample_ids"]
            or len(cluster["sample_ids"]) != len(set(cluster["sample_ids"]))
            or any(type(item) is not str or not item for item in cluster["sample_ids"])
            or type(cluster["column_ordinals"]) is not list
            or len(cluster["column_ordinals"]) != len(cluster["sample_ids"])
            or any(type(item) is not int or item < 0 for item in cluster["column_ordinals"])
        ):
            raise _error("internal unassigned numeric cluster drifted")
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
    if set(expected_owned) & set(source_only_ids) or set(by_sample) != {
        *expected_owned,
        *source_only_ids,
    }:
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
        or type(item["scope_owner_match_kind"]) is not str
        or not item["scope_owner_match_kind"]
        or type(item["label_match"]) is not dict
        or item["label_match"].get("occurrence_id") != item["occurrence_id"]
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
    for item in value["role_occurrences"]:
        _validate_source_scope_binding(
            item["source_scope_binding"],
            label_match=item["label_match"],
            role=item["role"],
        )
    actual_span_occurrences: dict[str, list[Mapping[str, Any]]] = {}
    for occurrence in value["role_occurrences"]:
        span = _source_span(occurrence["label_match"])
        actual_span_occurrences.setdefault(canonical_json_sha256_v1(span), []).append(occurrence)
    currency_roles = set(_DISCOUNT_SCOPE_TARGETS)
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
        if (
            anchor_match["page_sequence"] != source_match["page_sequence"]
            or anchor_match["end_document_line_ordinal"] >= source_match["document_line_ordinal"]
        ):
            raise _error("reviewed schema source-scope anchor does not precede its source")
        kind = receipt["binding_kind"]
        if kind == "UNIQUE_EXACT_PRECEDING_SOURCE_SUBSCOPE_INTERVAL":
            preceding_currency = [
                item
                for item in value["role_occurrences"]
                if item["role"] in currency_roles
                and item["label_match"]["page_sequence"] == source_match["page_sequence"]
                and item["label_match"]["end_document_line_ordinal"]
                < source_match["document_line_ordinal"]
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
            if (
                len(nearest) != 1
                or nearest[0]["occurrence_id"] != anchor["occurrence_id"]
                or occurrence["scope_owner_occurrence_id"] != anchor["occurrence_id"]
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
                and item["label_match"]["document_line_ordinal"] < source_ordinal
                and str(item["label_match"]["match_kind"]).startswith("EXACT_")
            ]
            prior_loans = [
                item
                for item in value["role_occurrences"]
                if item["role"] == "INTERBANK_LOAN_GROUP"
                and item["label_match"]["document_line_ordinal"] < source_ordinal
            ]
            later_loans = [
                item
                for item in value["role_occurrences"]
                if item["role"] == "INTERBANK_LOAN_GROUP"
                and item["label_match"]["document_line_ordinal"] > source_ordinal
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
            if (
                expected_anchor is None
                or expected_anchor["occurrence_id"] != anchor["occurrence_id"]
                or prior_loans
                or not later_loans
                or receipt["interval"]["start_document_line_ordinal"]
                != min(item["label_match"]["document_line_ordinal"] for item in prior_deposits)
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
                and item["label_match"]["document_line_ordinal"] < source_ordinal
                and str(item["label_match"]["match_kind"]).startswith("EXACT_")
            ]
            prior_loans = [
                item
                for item in value["role_occurrences"]
                if item["role"] == "INTERBANK_LOAN_GROUP"
                and item["label_match"]["document_line_ordinal"] < source_ordinal
            ]
            later_loans = [
                item
                for item in value["role_occurrences"]
                if item["role"] == "INTERBANK_LOAN_GROUP"
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
                and anchor_ordinal <= item["label_match"]["document_line_ordinal"] < source_ordinal
                and str(item["label_match"]["match_kind"]).startswith("EXACT_")
            ]
            later_leaves = [
                item
                for item in value["role_occurrences"]
                if item["role"] in _LOAN_LEAF_ROLES
                and item["label_match"]["document_line_ordinal"] > source_ordinal
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
            if (
                not prior_deposits
                or expected_loan is None
                or expected_loan["occurrence_id"] != anchor["occurrence_id"]
                or not str(anchor_match["match_kind"]).startswith("EXACT_")
                or not (exact_leaf_completion or exact_group_total_completion)
                or later_loans
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
    numeric_sample_universe, internal_unassigned_numeric_clusters = _build_numeric_sample_universe(
        parsed_pages,
        expanded,
        row_matches,
        axis,
        coextensive_evidence,
    )
    rows_by_occurrence = {row["label_match"].get("occurrence_id"): row for row in axis["rows"]}
    role_occurrences = [
        {
            "has_bound_value_row": match["occurrence_id"] in rows_by_occurrence,
            "label_match": canonical_clone_v1(match),
            "occurrence_id": match["occurrence_id"],
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
    if axis["status"] != "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY":
        reasons.insert(0, "VISIBLE_ROLE_OCCURRENCE_ROW_LANES_NOT_COMPLETE")
    material = {
        "authenticated_existing_dash_evidence": dash_evidence,
        "claim_boundary": CLAIM_BOUNDARY,
        "coextensive_structural_numeric_evidence": coextensive_evidence,
        "dependency_content_refs": _dependency_refs(),
        "family_id": compiled_family["family_id"],
        "format_version": FORMAT_VERSION,
        "internal_unassigned_numeric_clusters": internal_unassigned_numeric_clusters,
        "numeric_sample_universe": numeric_sample_universe,
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
