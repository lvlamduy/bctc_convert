"""Independent same-source authority for selected one-edit topology anchors.

The topology reader may use one edit to *retrieve* a plausible family region.
That tolerance is deliberately not accounting or mapping authority.  This
module closes that gap for V4 callers.  The ordinary route re-observes an exact
declared alias on the identical bound source-text lines.  V2 also permits one
narrow same-crop route: two independent recognizers may cover complementary,
disjoint exact tokens of one multi-token alias while each has exactly one
character error in a different token.  Both routes retain the identical
family/role/recursive structural-owner context.  Expanded children are bound
by occurrence ID so one occurrence can never corroborate a fuzzy repetition
of the same role.

Only accent removal/case/punctuation normalization, an enumeration prefix,
and the topology engine's bounded decorative parenthetical removal are exact
transforms here.  Edit distance is never consulted by the authority channel.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from bctc_ai.evaluation import (
    accounting_family_column_context_multilevel_v2 as column_context_multilevel_v2,
)
from bctc_ai.evaluation import accounting_family_occurrence_row_axis_v2 as occurrence_row_v2
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_v1
from bctc_ai.evaluation import accounting_family_topology_candidates_v2 as candidates_v2
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.family_first_numeric_cell_evidence_v1 import (
    parse_visible_financial_numeric_token_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "HIERARCHY_FRONTIER_FORMAT_VERSION",
    "RECURSIVE_HIERARCHY_FRONTIER_FORMAT_VERSION",
    "PARENT_FRONTIER_FORMAT_VERSION",
    "AccountingFamilyOneEditExactAuthorityV1Error",
    "build_accounting_family_one_edit_exact_authority_v1",
    "family_parent_exact_frontier_result_cluster_v1",
    "family_parent_has_exact_authority_v1",
    "project_accounting_family_one_edit_parent_frontier_authority_v1",
    "project_accounting_family_one_edit_hierarchy_frontier_authority_v1",
    "validate_accounting_family_one_edit_exact_authority_receipt_shape_v1",
    "validate_accounting_family_one_edit_exact_authority_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_FAMILY_ONE_EDIT_EXACT_AUTHORITY_V2"
PARENT_FRONTIER_FORMAT_VERSION = "ACCOUNTING_FAMILY_ONE_EDIT_EXACT_AUTHORITY_V3"
HIERARCHY_FRONTIER_FORMAT_VERSION = "ACCOUNTING_FAMILY_ONE_EDIT_EXACT_AUTHORITY_V4"
RECURSIVE_HIERARCHY_FRONTIER_FORMAT_VERSION = "ACCOUNTING_FAMILY_ONE_EDIT_EXACT_AUTHORITY_V5"
CLAIM_BOUNDARY = (
    "SELECTED_V4_TOPOLOGY_ONE_EDIT_RETRIEVAL_MATCHES_REQUIRE_EITHER_INDEPENDENT_EXACT_"
    "BOUND_SOURCE_TEXT_ALIAS_OR_AUTHENTICATED_SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_"
    "COVERAGE_ON_IDENTICAL_OCCURRENCE_FAMILY_ROLE_RECURSIVE_PARENT_CHAIN_PAGE_AND_LINE_"
    "SPAN_NO_NUMERIC_SCHEMA_MAPPING_OR_DISCARDED_CANDIDATE_VETO_AUTHORITY"
)
PARENT_FRONTIER_CLAIM_BOUNDARY = (
    "SELECTED_V4_ONE_EDIT_FAMILY_PARENT_MAY_ALSO_BE_STRUCTURALLY_BOUND_BY_ONE_"
    "UNIQUE_EXACT_ORDERED_DIRECT_COMPONENT_FRONTIER_ON_THE_IDENTICAL_PHYSICAL_"
    "PARENT_PAGE_ROOT_PERIOD_UNIT_AND_COMPLETE_LANE_AXIS_WITH_SOURCE_OBSERVED_"
    "NUMBERS_ONLY_NO_DIGIT_BACKSOLVE_PARENT_PLUS_OWN_LEAF_DOUBLE_COUNT_SCHEMA_"
    "MAPPING_OR_BANK_FILE_PAGE_PERIOD_SCOPE_ROUTING_AUTHORITY"
)
HIERARCHY_FRONTIER_CLAIM_BOUNDARY = (
    "SELECTED_V4_ONE_EDIT_COMPONENT_OR_FAMILY_PARENT_MAY_BE_BOUND_ONLY_BY_ONE_"
    "HIERARCHY_DECLARED_EXHAUSTIVE_ORDERED_DIRECT_FRONTIER_WITH_ONE_SOURCE_"
    "VISIBLE_RESULT_AND_ALL_SOURCE_VISIBLE_COMPONENT_VALUES_ON_THE_IDENTICAL_"
    "PHYSICAL_PAGE_ROOT_PERIOD_UNIT_AND_COMPLETE_LANE_AXIS_MIXED_GROUPING_"
    "REQUIRES_AUTHENTICATED_SAME_CROP_INDEPENDENT_EXACT_INTEGER_REPLAY_NO_"
    "BACKSOLVE_ROUNDING_PARENT_PLUS_DESCENDANT_DOUBLE_COUNT_OR_ROUTING_AUTHORITY"
)
RECURSIVE_HIERARCHY_FRONTIER_CLAIM_BOUNDARY = (
    "SELECTED_V4_ONE_EDIT_COMPONENT_MAY_BE_BOUND_ONLY_WHEN_THE_SHARED_HIERARCHY_"
    "COMPILER_REPLAYS_ONE_EXHAUSTIVE_RECURSIVE_DIRECT_FRONTIER_FROM_SOURCE_"
    "VISIBLE_ROWS_THROUGH_EVERY_PRINTED_INTERMEDIATE_SUBTOTAL_TO_ONE_SOURCE_"
    "VISIBLE_ROOT_RESULT_ON_THE_IDENTICAL_PAGE_ROOT_PERIOD_UNIT_AND_COMPLETE_"
    "MIXED_LANE_AXIS_NO_BACKSOLVE_ROUNDING_MIXED_LEVEL_DUPLICATE_OR_ROUTING_AUTHORITY"
)


@dataclass(frozen=True, slots=True, eq=False)
class _PreparedOneEditExactSourceAxisV1:
    """One same-turn exact-source scan, sealed to its document and spec."""

    document_pages_sha256: str
    exact_hits_sha256: str
    family_spec_sha256: str
    prepared_axis_sha256: str
    exact_hits: Any = field(repr=False, compare=False)
    seal: object = field(repr=False, compare=False)


_PREPARED_ONE_EDIT_EXACT_SOURCE_AXIS_SEAL = object()
_AUTHORITY_SPEC = {
    "allowed_exact_transforms": [
        "ACCENTLESS",
        "ACCENTLESS_AFTER_ENUMERATION_PREFIX",
        "ACCENTLESS_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL",
        "ACCENTLESS_AFTER_ENUMERATION_PREFIX_AND_DECORATIVE_PARENTHETICAL_REMOVAL",
    ],
    "bound_source_channel": "PPOCR_BOUND_SOURCE_TEXT",
    "exact_alias_requires_same_family_parent_context": True,
    "exact_alias_requires_same_expanded_occurrence_id": True,
    "exact_alias_requires_same_page_and_source_line_indices": True,
    "exact_alias_requires_same_recursive_nearest_structural_owner_chain": True,
    "exact_source_occurrence_axis": "PPOCR_EXACT_DECLARED_ALIASES_ONLY",
    "one_edit_channel": "VIETOCR_TRANSFORMER_RETRIEVAL_ONLY",
    "same_crop_complementary_token_authority": {
        "alias_candidate_count": 1,
        "allowed_transform": "ACCENTLESS",
        "channel_mismatch_token_count": 1,
        "minimum_alias_token_count": 2,
        "match_scope": "EXPANDED_OCCURRENCE_ONLY",
        "mismatch_token_axes_must_be_disjoint": True,
        "physical_source_line_count": 1,
        "required_channels": [
            "PPOCR_BOUND_SOURCE_TEXT",
            "VIETOCR_TRANSFORMER_RETRIEVAL_ONLY",
        ],
        "same_authenticated_crop_ref_and_sample_id_required": True,
        "token_count_must_equal_declared_alias": True,
    },
    "selected_candidate_only": True,
}
_PARENT_FRONTIER_AUTHORITY_SPEC = {
    **_AUTHORITY_SPEC,
    "arithmetic_parent_frontier_authority": {
        "component_frontier": "ORDERED_DIRECT_CHILD_OCCURRENCES_ONLY",
        "exact_equation_required_in_every_lane": True,
        "largest_visible_parent_result_required": True,
        "one_physical_family_parent_occurrence_required": True,
        "parent_and_own_leaf_double_count_forbidden": True,
        "same_page_root_period_unit_and_complete_lane_axis_required": True,
        "source_observed_numeric_assignments_only": True,
        "unique_frontier_required": True,
    },
}
_HIERARCHY_FRONTIER_AUTHORITY_SPEC = {
    **_AUTHORITY_SPEC,
    "hierarchy_direct_frontier_authority": {
        "component_frontier": (
            "UNIQUE_EXHAUSTIVE_DIRECT_SOURCE_SIBLINGS_PERSISTED_IN_HIERARCHY_DECLARED_ORDER"
        ),
        "physical_sibling_order_is_bound_but_may_differ_from_declaration_order": True,
        "exact_equation_required_in_every_lane": True,
        "mixed_grouping_requires_same_crop_independent_exact_integer": True,
        "mixed_node_requires_two_certified_lane_peers_and_one_raw_signed_anchor": True,
        "one_source_visible_result_required": True,
        "result_carriers": ["LABELED_PARENT_CLUSTER", "ROLE_OCCURRENCE"],
        "same_page_root_period_unit_and_complete_lane_axis_required": True,
        "source_observed_numeric_assignments_only": True,
        "target_kinds": ["COMPONENT", "FAMILY_PARENT"],
        "unique_exhaustive_frontier_required": True,
    },
}
_RECURSIVE_HIERARCHY_FRONTIER_AUTHORITY_SPEC = {
    **_AUTHORITY_SPEC,
    "recursive_hierarchy_direct_frontier_authority": {
        "component_frontier": "SHARED_HIERARCHY_COMPILER_SELECTED_DIRECT_FRONTIER_PER_LEVEL",
        "exact_equation_required_in_every_lane": True,
        "intermediate_result_carrier": "ONE_EXACT_UNLABELED_SOURCE_SUBTOTAL",
        "mixed_level_or_duplicate_component_use_forbidden": True,
        "numeric_cells": "RAW_SIGNED_OR_DASH_SOURCE_VISIBLE_ONLY",
        "result_carrier": "ONE_COMPLETE_VISIBLE_TRAILING_RESULT",
        "same_page_root_period_unit_and_complete_lane_axis_required": True,
        "source_observed_numeric_assignments_only": True,
        "target_kind": "COMPONENT",
        "unique_exhaustive_recursive_frontier_required": True,
    },
}
_SAFETY = {
    "bank_file_page_period_scope_used_for_routing": False,
    "discarded_or_near_one_edit_match_can_veto_selected_candidate": False,
    "mapping_authority": False,
    "one_edit_similarity_can_grant_exact_authority": False,
    "same_crop_reference_without_complementary_exact_token_coverage_can_grant_authority": False,
    "shared_or_overlapping_channel_edit_can_grant_authority": False,
    "schema_authority": False,
    "same_role_span_with_different_parent_context_can_authorize": False,
    "source_text_exact_alias_or_same_crop_complementary_token_context_required": True,
    "expanded_occurrence_identity_required": True,
}
_PARENT_FRONTIER_SAFETY = {
    **_SAFETY,
    "accounting_can_invent_or_correct_a_numeric_token": False,
    "competing_or_partial_frontier_can_authorize": False,
    "direct_parent_and_its_own_descendants_can_share_one_frontier": False,
    "same_label_under_a_different_parent_is_same_occurrence": False,
    "structural_parent_frontier_requires_public_exact_replay": True,
}
_HIERARCHY_FRONTIER_SAFETY = {
    **_PARENT_FRONTIER_SAFETY,
    "arithmetic_can_backsolve_a_missing_result_or_component": False,
    "hierarchy_alternative_can_be_selected_from_a_partial_visible_frontier": False,
    "mixed_grouped_token_can_be_reclassified_or_mutated": False,
    "result_and_component_source_samples_must_be_disjoint": True,
}
_RECURSIVE_HIERARCHY_FRONTIER_SAFETY = {
    **_HIERARCHY_FRONTIER_SAFETY,
    "intermediate_subtotal_can_be_invented_or_backsolved": False,
    "percentage_and_money_lanes_may_be_collapsed_to_one_unit": False,
    "recursive_proof_requires_shared_closure_replay": True,
    "uncertified_mixed_numeric_token_can_authorize": False,
}
_RESULT_FIELDS = {
    "authority_spec",
    "checks",
    "claim_boundary",
    "family_id",
    "format_version",
    "input_binding",
    "metrics",
    "receipt_id",
    "safety",
    "status",
    "unresolved_reasons",
}
_PARENT_FRONTIER_RESULT_FIELDS = {
    *_RESULT_FIELDS,
    "parent_frontier_authority",
    "source_exact_authority_receipt",
}
_HIERARCHY_FRONTIER_RESULT_FIELDS = {
    *_RESULT_FIELDS,
    "hierarchy_direct_frontier_authority",
    "source_exact_authority_receipt",
}
_RECURSIVE_HIERARCHY_FRONTIER_RESULT_FIELDS = {
    *_RESULT_FIELDS,
    "recursive_hierarchy_direct_frontier_authority",
    "source_exact_authority_receipt",
}
_INPUT_BINDING_FIELDS = {
    "document_pages_sha256",
    "expanded_occurrence_region_sha256",
    "family_spec_sha256",
    "selected_topology_region_sha256",
}
_PARENT_FRONTIER_INPUT_BINDING_FIELDS = {
    *_INPUT_BINDING_FIELDS,
    "column_context_sha256",
    "internal_unassigned_numeric_clusters_sha256",
    "numeric_sample_universe_sha256",
    "role_occurrences_sha256",
    "row_axis_sha256",
    "source_exact_authority_receipt_sha256",
}
_HIERARCHY_FRONTIER_INPUT_BINDING_FIELDS = {
    *_PARENT_FRONTIER_INPUT_BINDING_FIELDS,
    "column_policy_sha256",
    "hierarchy_spec_sha256",
}
_RECURSIVE_HIERARCHY_FRONTIER_INPUT_BINDING_FIELDS = {
    *_HIERARCHY_FRONTIER_INPUT_BINDING_FIELDS,
    "authenticated_extreme_margin_furniture_evidence_sha256",
}
_METRIC_FIELDS = {
    "exact_bound_count",
    "selected_one_edit_match_count",
    "unresolved_match_count",
}
_CHECK_FIELDS = {
    "complementary_token_authority",
    "exact_channel",
    "match_scope",
    "occurrence_id",
    "page_sequence",
    "retrieval_channel",
    "role",
    "role_kind",
    "source_line_indices",
    "status",
    "within_role",
}
_RETRIEVAL_FIELDS = {
    "alias_candidates",
    "alias_candidates_sha256",
    "channel",
    "match_kind",
    "normalized_surface",
    "surface",
}
_EXACT_FIELDS = {
    "alias_normalized",
    "alias_pointer",
    "alias_sha256",
    "channel",
    "context_binding",
    "context_binding_sha256",
    "normalized_surface",
    "source_surface",
    "source_surface_sha256",
    "transform",
}
_CONTEXT_FIELDS = {
    "family_id",
    "family_parent",
    "occurrence_id",
    "parent_resolution",
    "scope_owner_occurrence_id",
    "selected_region_sha256",
    "structural_parent",
    "within_role",
}
_STATUSES = {
    "EXACT_SOURCE_AUTHORITY_BOUND",
    "NOT_REQUIRED_NO_SELECTED_ONE_EDIT_RETRIEVAL",
    "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY",
}
_CHECK_STATUSES = {
    "BOUND_SOURCE_TEXT_REMAINS_ONE_EDIT_NOT_EXACT",
    "EXACT_ALIAS_DIFFERENT_SOURCE_SPAN",
    "EXACT_FAMILY_PARENT_CONTEXT_MISMATCH",
    "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND",
    "EXACT_STRUCTURAL_PARENT_CONTEXT_MISMATCH",
    "MISSING_BOUND_SOURCE_TEXT",
    "NO_EXACT_DECLARED_ALIAS_ON_RETRIEVAL_SOURCE_SPAN",
    "RETRIEVAL_ONE_EDIT_ALIAS_SPEC_BINDING_DRIFTED",
    "SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_ALIAS_BOUND",
}
_BOUND_CHECK_STATUSES = {
    "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND",
    "SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_ALIAS_BOUND",
}
_PARENT_FRONTIER_BOUND_STATUS = "EXACT_ORDERED_PARENT_FRONTIER_AUTHORITY_BOUND"
_PARENT_FRONTIER_PROOF_FORMAT_VERSION = (
    "ACCOUNTING_FAMILY_ONE_EDIT_PARENT_FRONTIER_AUTHORITY_PROOF_V1"
)
_PARENT_FRONTIER_PROOF_FIELDS = {
    "column_context_receipt",
    "component_frontier_bindings",
    "format_version",
    "input_binding",
    "parent_match_binding",
    "proof_id",
    "root_occurrence_id",
    "source_check",
    "source_scope_binding",
    "status",
    "target_label_match",
    "target_occurrence_id",
    "target_role",
}
_PARENT_FRONTIER_COMPONENT_BINDING_FIELDS = {
    "component_ordinal",
    "equation_component",
    "occurrence_id",
    "role_occurrence_sha256",
    "row_receipt",
    "row_sha256",
    "retrieval_role",
    "retrieval_within_role",
    "source_line_indices",
}
_HIERARCHY_FRONTIER_BOUND_STATUS = "EXACT_HIERARCHY_DIRECT_FRONTIER_AUTHORITY_BOUND"
_HIERARCHY_FRONTIER_PROOF_FORMAT_VERSION = (
    "ACCOUNTING_FAMILY_ONE_EDIT_HIERARCHY_DIRECT_FRONTIER_AUTHORITY_PROOF_V1"
)
_HIERARCHY_FRONTIER_PROOF_FIELDS = {
    "column_context_receipt",
    "component_frontier_bindings",
    "format_version",
    "hierarchy_equation_binding",
    "input_binding",
    "numeric_cell_certificates",
    "page_sequence",
    "proof_id",
    "result_carrier_binding",
    "root_occurrence_id",
    "source_check",
    "status",
    "target_kind",
    "target_occurrence_id",
    "target_role",
}
_HIERARCHY_FRONTIER_EQUATION_BINDING_FIELDS = {
    "alternative_ordinal",
    "alternative_spec",
    "compiled_equation_sha256",
    "component_roles",
    "hierarchy_spec_sha256",
    "result_role",
    "visible_result_roles",
}
_HIERARCHY_FRONTIER_RESULT_CARRIER_FIELDS = {
    "carrier_kind",
    "cluster_id",
    "numbers",
    "occurrence_id",
    "role_occurrence_sha256",
    "semantic_result_role",
    "sample_ids",
    "source_line_indices",
    "source_record_sha256",
    "source_role",
}
_HIERARCHY_FRONTIER_COMPONENT_FIELDS = {
    "component_ordinal",
    "numbers",
    "occurrence_id",
    "retrieval_occurrence_id",
    "role",
    "role_occurrence_sha256",
    "row_sha256",
    "sample_ids",
    "source_line_indices",
    "source_visual_ordinal",
    "visual_match_key_sha256",
}
_HIERARCHY_FRONTIER_CELL_FIELDS = {
    "bbox",
    "certificate_kind",
    "column_ordinal",
    "crop_ref",
    "node_kind",
    "node_ordinal",
    "number",
    "numeric_sample_sha256",
    "page_line_sha256",
    "page_sequence",
    "pp_classification",
    "pp_surface",
    "role",
    "sample_id",
    "source_line_index",
    "vietocr_number",
    "vietocr_surface",
}
_RECURSIVE_HIERARCHY_FRONTIER_BOUND_STATUS = (
    "EXACT_RECURSIVE_HIERARCHY_DIRECT_FRONTIER_AUTHORITY_BOUND"
)
_RECURSIVE_HIERARCHY_FRONTIER_PROOF_FORMAT_VERSION = (
    "ACCOUNTING_FAMILY_ONE_EDIT_RECURSIVE_HIERARCHY_DIRECT_FRONTIER_AUTHORITY_PROOF_V1"
)
_RECURSIVE_HIERARCHY_FRONTIER_PROOF_FIELDS = {
    "column_context_receipt",
    "format_version",
    "input_binding",
    "proof_id",
    "recursive_frontier",
    "source_check",
    "status",
}
_RECURSIVE_FRONTIER_FIELDS = {
    "covered_source_sample_ids",
    "family_id",
    "format_version",
    "global_equations_sha256",
    "hierarchy_spec_sha256",
    "local_equations_sha256",
    "page_sequence",
    "proof_id",
    "resolved_roles_sha256",
    "root_equation",
    "root_occurrence_id",
    "selected_component_use_count",
    "synthetic_intermediate_coverage",
    "target_occurrence_id",
    "target_retrieval_occurrence_id",
    "target_role",
    "trailing_result",
}
_PARENT_MATCH_BINDING_FIELDS = {
    "document_line_span",
    "label_bbox",
    "numbers",
    "page_sequence",
    "result_sample_ids",
    "source_line_indices",
}
_COMPLEMENTARY_FORMAT_VERSION = "SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_AUTHORITY_V1"
_COMPLEMENTARY_FIELDS = {
    "alias_normalized",
    "alias_pointer",
    "alias_sha256",
    "channel_proofs",
    "crop_binding",
    "crop_binding_sha256",
    "format_version",
    "proof_id",
    "token_axis",
}
_COMPLEMENTARY_CHANNEL_FIELDS = {
    "channel",
    "edit",
    "exact_token_indices",
    "mismatch_token_indices",
    "normalized_surface",
    "surface",
    "tokens",
}
_COMPLEMENTARY_EDIT_FIELDS = {
    "alias_character",
    "alias_character_index",
    "candidate_character",
    "candidate_character_index",
    "kind",
    "token_index",
}
_COMPLEMENTARY_CROP_BINDING_FIELDS = {
    "bbox",
    "crop_ref",
    "page_sequence",
    "sample_id",
    "source_line_index",
}


class AccountingFamilyOneEditExactAuthorityV1Error(ValueError):
    """The selected match, exact source channel, spec, or receipt drifted."""


def _error(message: str) -> AccountingFamilyOneEditExactAuthorityV1Error:
    return AccountingFamilyOneEditExactAuthorityV1Error(message)


def _visible_dash_rescues_sha256_v1(value: Any) -> str:
    """Bind opaque dash crops through their independently replayed region refs."""

    if type(value) is not tuple:
        raise _error("one-edit visible-dash rescues must be one exact tuple")
    bindings = []
    for rescue in value:
        if (
            type(rescue) is not dict
            or set(rescue) != {"column_ordinal", "page_sequence", "region", "role"}
            or type(rescue["column_ordinal"]) is not int
            or rescue["column_ordinal"] < 0
            or type(rescue["page_sequence"]) is not int
            or rescue["page_sequence"] <= 0
            or type(rescue["role"]) is not str
            or not rescue["role"]
        ):
            raise _error("one-edit visible-dash rescue binding drifted")
        try:
            region = row_v1._region_record(  # noqa: SLF001
                rescue["region"], page_sequence=rescue["page_sequence"]
            )
        except row_v1.AccountingFamilyRowAxisV1Error as exc:
            raise _error("one-edit visible-dash region replay failed") from exc
        bindings.append(
            {
                "column_ordinal": rescue["column_ordinal"],
                "page_sequence": rescue["page_sequence"],
                "region": {
                    key: canonical_clone_v1(item)
                    for key, item in region.items()
                    if key != "region_png_bytes"
                },
                "role": rescue["role"],
            }
        )
    return canonical_json_sha256_v1(bindings)


def _is_one_edit(match: Mapping[str, Any]) -> bool:
    return str(match.get("match_kind", "")).startswith("ONE_EDIT_ALIAS")


def _crop_reference(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"path", "sha256", "size_bytes"}
        or type(value["path"]) is not str
        or not value["path"]
        or type(value["sha256"]) is not str
        or len(value["sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in value["sha256"])
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error("one-edit exact-authority crop reference drifted")
    return canonical_clone_v1(value)


def _pages_with_occurrence_geometry_v1(document_pages: Any) -> list[dict[str, Any]]:
    """Parse topology fields while retaining production occurrence evidence.

    The public authority input may carry the canonical numeric-recognizer
    record used by occurrence geometry.  It is excluded from topology text
    retrieval, but retained byte-for-byte for the coextensive/wrapped-row
    replay so a fabricated score or stripped page cannot change that replay.
    """

    if type(document_pages) is not list:
        raise _error("one-edit exact-authority document pages drifted")
    topology_pages = []
    widths = []
    retained_axes = []
    for raw_page in document_pages:
        if type(raw_page) is not dict or set(raw_page) not in (
            {"lines", "page_sequence"},
            {"lines", "page_sequence", "page_width"},
        ):
            raise _error("one-edit exact-authority document page drifted")
        width = raw_page.get("page_width")
        if width is not None and (type(width) is not int or width <= 0):
            raise _error("one-edit exact-authority page width drifted")
        if type(raw_page.get("lines")) is not list:
            raise _error("one-edit exact-authority document line axis drifted")
        topology_lines = []
        retained_axis = []
        for raw_line in raw_page["lines"]:
            required_fields = {"bbox", "source_line_index", "source_text", "vietocr_text"}
            optional_fields = {"crop_ref", "numeric_recognition", "sample_id"}
            if (
                type(raw_line) is not dict
                or not required_fields <= set(raw_line)
                or set(raw_line) - required_fields - optional_fields
                or ("crop_ref" in raw_line) != ("sample_id" in raw_line)
            ):
                raise _error("one-edit exact-authority document line drifted")
            numeric_recognition = raw_line.get("numeric_recognition")
            if numeric_recognition is not None and (
                type(numeric_recognition) is not dict
                or type(numeric_recognition.get("raw_prediction")) is not str
            ):
                raise _error("one-edit exact-authority numeric recognition drifted")
            crop_ref = raw_line.get("crop_ref")
            sample_id = raw_line.get("sample_id")
            if sample_id is not None and (type(sample_id) is not str or not sample_id):
                raise _error("one-edit exact-authority sample identity drifted")
            retained = {"numeric_recognition": canonical_clone_v1(numeric_recognition)}
            if crop_ref is not None:
                retained.update(
                    {
                        "crop_ref": _crop_reference(crop_ref),
                        "sample_id": sample_id,
                    }
                )
            topology_lines.append(
                {
                    "bbox": canonical_clone_v1(raw_line["bbox"]),
                    "source_line_index": raw_line["source_line_index"],
                    "source_text": raw_line["source_text"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
            retained_axis.append(retained)
        topology_pages.append(
            {
                "lines": topology_lines,
                "page_sequence": raw_page.get("page_sequence"),
            }
        )
        widths.append(width)
        retained_axes.append(retained_axis)
    pages = topology_v1._pages(topology_pages)  # noqa: SLF001
    for page, width, retained_axis in zip(pages, widths, retained_axes, strict=True):
        page["page_width"] = width
        for line, retained in zip(page["lines"], retained_axis, strict=True):
            numeric_recognition = retained["numeric_recognition"]
            if numeric_recognition is not None:
                line["numeric_recognition"] = numeric_recognition
            if "crop_ref" in retained:
                line["crop_ref"] = retained["crop_ref"]
                line["sample_id"] = retained["sample_id"]
    return pages


def _retrieval_only_pages_v1(
    pages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Rebuild the exact page contract used by V2 topology retrieval."""

    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "source_line_index": line["source_line_index"],
                    # PP-OCR is the independent exact-authority channel.  It
                    # must never participate in the retrieval replay.
                    "source_text": None,
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]


def _occurrence_row_pages_v1(
    pages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Project the complete fields consumed by occurrence expansion.

    Occurrence expansion is semantic, but it also uses exact same-row numeric
    evidence to reject a heading-only coextensive total and to distinguish an
    independently complete row from a wrapped label.  Stripping the PP-OCR
    source text here made the independent replay crash on those legitimate V4
    shapes.  The source channel remains retrieval-inert: it is exposed only as
    ``numeric_recognition`` to the occurrence geometry predicates, never as
    topology match input.
    """

    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    **(
                        {
                            "crop_ref": canonical_clone_v1(line["crop_ref"]),
                            "sample_id": line["sample_id"],
                        }
                        if "crop_ref" in line and "sample_id" in line
                        else {}
                    ),
                    "line_ordinal": line["source_line_index"],
                    "numeric_recognition": canonical_clone_v1(
                        line.get("numeric_recognition")
                        or {
                            "raw_prediction": (
                                line["source_text"] if type(line["source_text"]) is str else ""
                            ),
                            "reader_score": 1.0,
                        }
                    ),
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
            "page_width": page.get("page_width"),
        }
        for page in pages
    ]


def _expected_occurrence_id_v1(match: Mapping[str, Any]) -> str:
    return "aforav2:occurrence:" + canonical_json_sha256_v1(
        {
            "document_line_ordinal": match["document_line_ordinal"],
            "end_document_line_ordinal": match["end_document_line_ordinal"],
            "page_sequence": match["page_sequence"],
            "role": match["role"],
            "role_occurrence_ordinal": match["role_occurrence_ordinal"],
        }
    )


def _root_scope_id_v1(selected_region: Mapping[str, Any]) -> str:
    return "aforav2:root:" + canonical_json_sha256_v1(
        {
            "end": selected_region["cluster_end_document_line_ordinal_exclusive"],
            "parent_match": selected_region.get("parent_match"),
            "start": selected_region["cluster_start_document_line_ordinal"],
        }
    )


def _physical_occurrence_signature_v1(match: Mapping[str, Any]) -> str:
    """Typed physical identity; distinct coextensive semantic roles remain valid."""

    return canonical_json_sha256_v1(
        {
            "document_line_ordinal": match["document_line_ordinal"],
            "end_document_line_ordinal": match["end_document_line_ordinal"],
            "end_source_line_index": match["end_source_line_index"],
            "page_sequence": match["page_sequence"],
            "role": match["role"],
            "source_line_index": match["source_line_index"],
        }
    )


def _validate_canonical_expanded_occurrence_axis_v1(
    expanded_region: Mapping[str, Any],
    selected_region: Mapping[str, Any],
) -> None:
    """Verify identities and nearest structural owners on the replayed axis."""

    matches = expanded_region.get("child_matches")
    if type(matches) is not list or any(type(match) is not dict for match in matches):
        raise _error("canonical expanded occurrence child axis drifted")
    occurrence_ids = [match.get("occurrence_id") for match in matches]
    physical_signatures = [_physical_occurrence_signature_v1(match) for match in matches]
    if (
        any(
            type(occurrence_id) is not str or occurrence_id != _expected_occurrence_id_v1(match)
            for occurrence_id, match in zip(occurrence_ids, matches, strict=True)
        )
        or len(occurrence_ids) != len(set(occurrence_ids))
        or len(physical_signatures) != len(set(physical_signatures))
    ):
        raise _error("canonical expanded occurrence identity axis drifted")
    undecorated = []
    for match in matches:
        raw = canonical_clone_v1(match)
        raw.pop("occurrence_id", None)
        raw.pop("scope_owner_occurrence_id", None)
        raw.pop("scope_owner_role", None)
        undecorated.append(raw)
    try:
        expected = occurrence_row_v2._decorate_scopes(  # noqa: SLF001
            undecorated,
            selected_region,
        )
    except occurrence_row_v2.AccountingFamilyOccurrenceRowAxisV2Error as exc:
        raise _error("canonical occurrence lost its nearest structural owner") from exc
    if not same_typed_json_v1(matches, expected):
        raise _error("canonical occurrence nearest structural owner drifted")


def _canonical_expanded_occurrence_region_v1(
    pages: Sequence[Mapping[str, Any]],
    family_spec: Mapping[str, Any],
    selected_topology_region: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the complete selected V2 occurrence authority from source inputs."""

    retrieval_pages = _retrieval_only_pages_v1(pages)
    try:
        prepared = candidates_v2._prepare_accounting_family_topology_candidates_v2(  # noqa: SLF001
            retrieval_pages,
            family_spec,
        )
        topology_scan, topology_candidates, bindings = (
            candidates_v2._prepared_accounting_family_topology_authority_v2(  # noqa: SLF001
                prepared
            )
        )
    except candidates_v2.AccountingFamilyTopologyCandidatesV2Error as exc:
        raise _error("canonical V2 topology candidate replay failed") from exc
    selected_ordinals = [
        ordinal
        for ordinal, region in enumerate(topology_candidates["regions"])
        if same_typed_json_v1(region, selected_topology_region)
    ]
    if len(selected_ordinals) != 1:
        raise _error("selected topology region is not one exact canonical V2 candidate")
    selected_ordinal = selected_ordinals[0]
    canonical_selected = topology_candidates["regions"][selected_ordinal]
    try:
        matches, replayed_selected, effective_region, _topology_candidates_id = (
            occurrence_row_v2._expanded_matches(  # noqa: SLF001
                _occurrence_row_pages_v1(pages),
                family_spec,
                topology_scan,
                canonical_selected,
                None,
                topology_candidates,
                bindings[selected_ordinal],
            )
        )
        if not same_typed_json_v1(replayed_selected, canonical_selected):
            raise _error("selected candidate changed during occurrence replay")
        matches = occurrence_row_v2._attach_schema_scope_source_label_bboxes(  # noqa: SLF001
            _occurrence_row_pages_v1(pages),
            topology_v1._spec(family_spec),  # noqa: SLF001
            matches,
        )
        decorated = occurrence_row_v2._decorate_scopes(  # noqa: SLF001
            matches,
            replayed_selected,
        )
        expanded_region = occurrence_row_v2._expanded_region(  # noqa: SLF001
            effective_region,
            decorated,
        )
    except occurrence_row_v2.AccountingFamilyOccurrenceRowAxisV2Error as exc:
        raise _error("canonical V2 occurrence-axis replay failed") from exc
    _validate_canonical_expanded_occurrence_axis_v1(expanded_region, canonical_selected)
    return canonical_clone_v1(expanded_region)


def _match_line_indices(
    match: Mapping[str, Any], pages: Sequence[Mapping[str, Any]]
) -> tuple[int, ...]:
    page_sequence = match.get("page_sequence")
    page = next((item for item in pages if item["page_sequence"] == page_sequence), None)
    if page is None:
        raise _error("selected one-edit match page is absent from the complete source axis")
    start = match.get("source_line_index")
    stop = match.get("end_source_line_index")
    if type(start) is not int or type(stop) is not int or stop < start:
        raise _error("selected one-edit match source span drifted")
    positions = {line["source_line_index"]: position for position, line in enumerate(page["lines"])}
    if start not in positions or stop not in positions or positions[stop] < positions[start]:
        raise _error("selected one-edit match source span is absent from its bound page")
    explicit = match.get("source_line_indices")
    if explicit is None:
        result = tuple(
            line["source_line_index"]
            for line in page["lines"][positions[start] : positions[stop] + 1]
        )
    else:
        if (
            type(explicit) is not list
            or not explicit
            or any(type(index) is not int for index in explicit)
            or len(explicit) != len(set(explicit))
            or explicit[0] != start
            or explicit[-1] != stop
            or any(index not in positions for index in explicit)
            or explicit != sorted(explicit, key=positions.__getitem__)
        ):
            raise _error("selected one-edit noncontiguous source-line identity drifted")
        result = tuple(explicit)
    if not result:
        raise _error("selected one-edit match retained an empty source-line span")
    return result


def _match_identity(match: Mapping[str, Any], pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "document_line_span": [
            match.get("document_line_ordinal"),
            match.get("end_document_line_ordinal"),
        ],
        "occurrence_id": match.get("occurrence_id"),
        "page_sequence": match.get("page_sequence"),
        "role": match.get("role"),
        "source_line_indices": list(_match_line_indices(match, pages)),
        "scope_owner_occurrence_id": match.get("scope_owner_occurrence_id"),
        "within_role": match.get("matched_within_role"),
    }


def _same_match_span(
    left: Mapping[str, Any], right: Mapping[str, Any], pages: Sequence[Mapping[str, Any]]
) -> bool:
    return (
        left.get("page_sequence") == right.get("page_sequence")
        and left.get("document_line_ordinal") == right.get("document_line_ordinal")
        and left.get("end_document_line_ordinal") == right.get("end_document_line_ordinal")
        and _match_line_indices(left, pages) == _match_line_indices(right, pages)
    )


def _source_surface(match: Mapping[str, Any], pages: Sequence[Mapping[str, Any]]) -> str | None:
    page = next(item for item in pages if item["page_sequence"] == match["page_sequence"])
    by_index = {line["source_line_index"]: line for line in page["lines"]}
    values = [by_index[index]["source_text"] for index in _match_line_indices(match, pages)]
    if any(type(value) is not str or not value.strip() for value in values):
        return None
    return " ".join(value.strip() for value in values).strip()


def _exact_axes(surface: str) -> list[tuple[str, str]]:
    axes = [("ACCENTLESS", normalize_vietnamese_anchor_v1(surface))]
    stripped = topology_v1._ENUMERATION_PREFIX.sub("", surface, count=1)  # noqa: SLF001
    if stripped != surface:
        axes.append(
            (
                "ACCENTLESS_AFTER_ENUMERATION_PREFIX",
                normalize_vietnamese_anchor_v1(stripped),
            )
        )
    decorative = topology_v1._without_decorative_parentheticals(surface)  # noqa: SLF001
    if decorative != surface:
        axes.append(
            (
                "ACCENTLESS_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL",
                normalize_vietnamese_anchor_v1(decorative),
            )
        )
    decorative_stripped = topology_v1._ENUMERATION_PREFIX.sub(  # noqa: SLF001
        "", decorative, count=1
    )
    if decorative_stripped != decorative:
        axes.append(
            (
                "ACCENTLESS_AFTER_ENUMERATION_PREFIX_AND_DECORATIVE_PARENTHETICAL_REMOVAL",
                normalize_vietnamese_anchor_v1(decorative_stripped),
            )
        )
    deduplicated: list[tuple[str, str]] = []
    seen = set()
    for transform, normalized in axes:
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduplicated.append((transform, normalized))
    return deduplicated


def _alias_entries(
    compiled: Mapping[str, Any], *, role: str, within_role: str | None
) -> list[dict[str, str]]:
    if role == compiled["parent"]["role"]:
        return [
            {
                "alias": alias,
                "pointer": f"/parent/aliases/{alias_ordinal}",
            }
            for alias_ordinal, alias in enumerate(compiled["parent"]["aliases"])
        ]
    children = [
        (child_ordinal, child)
        for child_ordinal, child in enumerate(compiled["children"])
        if child["role"] == role
    ]
    if len(children) != 1:
        return []
    child_ordinal, child = children[0]
    if compiled["spec_format_version"] != topology_v1.SPEC_FORMAT_VERSION_V3:
        matcher = child["matchers"][0]
        if matcher["within_role"] != within_role:
            return []
        return [
            {
                "alias": alias,
                "pointer": f"/children/{child_ordinal}/aliases/{alias_ordinal}",
            }
            for alias_ordinal, alias in enumerate(matcher["aliases"])
        ]
    return [
        {
            "alias": alias,
            "pointer": (
                f"/children/{child_ordinal}/matchers/{matcher_ordinal}/aliases/{alias_ordinal}"
            ),
        }
        for matcher_ordinal, matcher in enumerate(child["matchers"])
        if matcher["within_role"] == within_role
        for alias_ordinal, alias in enumerate(matcher["aliases"])
    ]


def _retrieval_alias_candidates(
    match: Mapping[str, Any], aliases: Sequence[Mapping[str, str]]
) -> list[dict[str, str]]:
    transform_by_kind = {
        "ONE_EDIT_ALIAS_REQUIRES_COMPLETE_TOPOLOGY": "ACCENTLESS",
        "ONE_EDIT_ALIAS_AFTER_ENUMERATION_PREFIX_REQUIRES_COMPLETE_TOPOLOGY": (
            "ACCENTLESS_AFTER_ENUMERATION_PREFIX"
        ),
        "ONE_EDIT_ALIAS_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL_REQUIRES_COMPLETE_TOPOLOGY": (
            "ACCENTLESS_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL"
        ),
        "ONE_EDIT_ALIAS_AFTER_ENUMERATION_PREFIX_AND_DECORATIVE_PARENTHETICAL_REMOVAL_REQUIRES_COMPLETE_TOPOLOGY": (
            "ACCENTLESS_AFTER_ENUMERATION_PREFIX_AND_DECORATIVE_PARENTHETICAL_REMOVAL"
        ),
    }
    selected_transform = transform_by_kind.get(match.get("match_kind"))
    candidates = []
    for transform, normalized in _exact_axes(str(match.get("surface", ""))):
        if transform != selected_transform:
            continue
        for alias in aliases:
            if normalized != alias["alias"] and topology_v1._one_edit_alias_is_safe(  # noqa: SLF001
                normalized, alias["alias"]
            ):
                candidates.append(dict(alias))
    return sorted(
        {item["pointer"]: item for item in candidates}.values(),
        key=lambda item: item["pointer"],
    )


def _accentless_one_edit_alias_candidates(
    surface: str, aliases: Sequence[Mapping[str, str]]
) -> list[dict[str, str]]:
    normalized = normalize_vietnamese_anchor_v1(surface)
    return sorted(
        {
            alias["pointer"]: dict(alias)
            for alias in aliases
            if normalized != alias["alias"]
            and topology_v1._one_edit_alias_is_safe(normalized, alias["alias"])  # noqa: SLF001
        }.values(),
        key=lambda item: item["pointer"],
    )


def _single_character_edit(
    candidate: str, alias: str, *, token_index: int
) -> dict[str, Any] | None:
    if candidate == alias or not topology_v1._edit_distance_at_most_one(  # noqa: SLF001
        candidate, alias
    ):
        return None
    if len(candidate) == len(alias):
        indices = [
            index
            for index, (candidate_character, alias_character) in enumerate(
                zip(candidate, alias, strict=True)
            )
            if candidate_character != alias_character
        ]
        if len(indices) != 1:
            return None
        index = indices[0]
        return {
            "alias_character": alias[index],
            "alias_character_index": index,
            "candidate_character": candidate[index],
            "candidate_character_index": index,
            "kind": "SUBSTITUTE_CHANNEL_CHARACTER",
            "token_index": token_index,
        }
    if len(candidate) + 1 == len(alias):
        index = next(
            (
                position
                for position, character in enumerate(candidate)
                if character != alias[position]
            ),
            len(candidate),
        )
        if candidate[:index] + alias[index] + candidate[index:] != alias:
            return None
        return {
            "alias_character": alias[index],
            "alias_character_index": index,
            "candidate_character": None,
            "candidate_character_index": index,
            "kind": "INSERT_MISSING_ALIAS_CHARACTER",
            "token_index": token_index,
        }
    if len(candidate) == len(alias) + 1:
        index = next(
            (
                position
                for position, character in enumerate(alias)
                if character != candidate[position]
            ),
            len(alias),
        )
        if candidate[:index] + candidate[index + 1 :] != alias:
            return None
        return {
            "alias_character": None,
            "alias_character_index": index,
            "candidate_character": candidate[index],
            "candidate_character_index": index,
            "kind": "DISCARD_EXTRA_CHANNEL_CHARACTER",
            "token_index": token_index,
        }
    return None


def _same_crop_complementary_token_authority_v1(
    match: Mapping[str, Any],
    *,
    aliases: Sequence[Mapping[str, str]],
    pages: Sequence[Mapping[str, Any]],
    retrieval_candidates: Sequence[Mapping[str, str]],
) -> dict[str, Any] | None:
    """Bind disjoint exact-token coverage from two readers of one crop.

    Neither one-edit surface is promoted on similarity alone.  Every declared
    alias token must instead be read exactly by at least one of the two pinned
    recognizers, and their sole mismatching token positions must be disjoint.
    The proof is limited to one authenticated source line so token evidence
    cannot be assembled across crops or wrapped-label fragments.
    """

    indices = _match_line_indices(match, pages)
    if len(indices) != 1 or len(retrieval_candidates) != 1:
        return None
    page = next(item for item in pages if item["page_sequence"] == match["page_sequence"])
    line = next(item for item in page["lines"] if item["source_line_index"] == indices[0])
    crop_ref = line.get("crop_ref")
    sample_id = line.get("sample_id")
    source_surface = line.get("source_text")
    retrieval_surface = line.get("vietocr_text")
    if (
        type(crop_ref) is not dict
        or type(sample_id) is not str
        or not sample_id
        or type(source_surface) is not str
        or not source_surface.strip()
        or type(retrieval_surface) is not str
        or not retrieval_surface.strip()
        or retrieval_surface != match.get("surface")
    ):
        return None
    alias = dict(retrieval_candidates[0])
    source_candidates = _accentless_one_edit_alias_candidates(source_surface, aliases)
    if len(source_candidates) != 1 or source_candidates[0] != alias:
        return None
    alias_tokens = alias["alias"].split()
    channel_axis = [
        ("PPOCR_BOUND_SOURCE_TEXT", source_surface),
        ("VIETOCR_TRANSFORMER_RETRIEVAL_ONLY", retrieval_surface),
    ]
    if len(alias_tokens) < 2:
        return None
    channel_proofs = []
    mismatch_axes = []
    for channel, surface in channel_axis:
        normalized = normalize_vietnamese_anchor_v1(surface)
        tokens = normalized.split()
        if len(tokens) != len(alias_tokens):
            return None
        mismatches = [
            index
            for index, (candidate_token, alias_token) in enumerate(
                zip(tokens, alias_tokens, strict=True)
            )
            if candidate_token != alias_token
        ]
        if len(mismatches) != 1:
            return None
        mismatch = mismatches[0]
        edit = _single_character_edit(
            tokens[mismatch], alias_tokens[mismatch], token_index=mismatch
        )
        if edit is None:
            return None
        exact_indices = [index for index in range(len(alias_tokens)) if index != mismatch]
        channel_proofs.append(
            {
                "channel": channel,
                "edit": edit,
                "exact_token_indices": exact_indices,
                "mismatch_token_indices": mismatches,
                "normalized_surface": normalized,
                "surface": surface,
                "tokens": tokens,
            }
        )
        mismatch_axes.append(set(mismatches))
    if mismatch_axes[0] & mismatch_axes[1]:
        return None
    token_axis = []
    for token_index, alias_token in enumerate(alias_tokens):
        exact_channels = [
            proof["channel"]
            for proof in channel_proofs
            if token_index in proof["exact_token_indices"]
        ]
        if not exact_channels:
            return None
        token_axis.append(
            {
                "alias_token": alias_token,
                "exact_channels": exact_channels,
                "token_index": token_index,
            }
        )
    crop_binding = {
        "bbox": canonical_clone_v1(line["bbox"]),
        "crop_ref": _crop_reference(crop_ref),
        "page_sequence": match["page_sequence"],
        "sample_id": sample_id,
        "source_line_index": indices[0],
    }
    material = {
        "alias_normalized": alias["alias"],
        "alias_pointer": alias["pointer"],
        "alias_sha256": canonical_json_sha256_v1(alias["alias"]),
        "channel_proofs": channel_proofs,
        "crop_binding": crop_binding,
        "crop_binding_sha256": canonical_json_sha256_v1(crop_binding),
        "format_version": _COMPLEMENTARY_FORMAT_VERSION,
        "token_axis": token_axis,
    }
    return {
        **material,
        "proof_id": "afcetav1:proof:" + canonical_json_sha256_v1(material),
    }


def _exact_alias_bindings(
    surface: str, aliases: Sequence[Mapping[str, str]]
) -> list[dict[str, str]]:
    bindings = []
    for transform, normalized in _exact_axes(surface):
        for alias in aliases:
            if normalized == alias["alias"]:
                bindings.append({**dict(alias), "transform": transform})
    return sorted(
        {item["pointer"]: item for item in bindings}.values(),
        key=lambda item: item["pointer"],
    )


def _source_exact_axes(
    pages: Sequence[Mapping[str, Any]], compiled: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_pages = [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "normalized_text": normalize_vietnamese_anchor_v1(
                        line["source_text"] if type(line["source_text"]) is str else ""
                    ),
                    "source_line_index": line["source_line_index"],
                    "source_text": None,
                    "vietocr_text": (
                        line["source_text"] if type(line["source_text"]) is str else ""
                    ),
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]
    hits, _line_axis, _page_axis = topology_v1._document_hits(  # noqa: SLF001
        source_pages, compiled
    )
    exact_hits = {
        "children": {
            role: [
                hit
                for hit in records
                if str(hit.get("match_kind", "")).startswith("EXACT_ACCENTLESS_ALIAS")
            ]
            for role, records in hits["children"].items()
        },
        "parents": [
            hit
            for hit in hits["parents"]
            if str(hit.get("match_kind", "")).startswith("EXACT_ACCENTLESS_ALIAS")
        ],
    }
    return exact_hits, source_pages


def _prepared_exact_source_axis_material_v1(
    *,
    document_pages_sha256: str,
    exact_hits_sha256: str,
    family_spec_sha256: str,
) -> dict[str, str]:
    return {
        "document_pages_sha256": document_pages_sha256,
        "exact_hits_sha256": exact_hits_sha256,
        "family_spec_sha256": family_spec_sha256,
    }


def _prepare_one_edit_exact_source_axis_v1(
    pages: Sequence[Mapping[str, Any]],
    compiled: Mapping[str, Any],
    *,
    document_pages: Any,
    family_spec: Any,
) -> _PreparedOneEditExactSourceAxisV1:
    """Scan one authenticated document source axis once for this call tree."""

    exact_hits, _source_pages = _source_exact_axes(pages, compiled)
    document_pages_sha256 = canonical_json_sha256_v1(document_pages)
    family_spec_sha256 = canonical_json_sha256_v1(family_spec)
    exact_hits_sha256 = canonical_json_sha256_v1(exact_hits)
    material = _prepared_exact_source_axis_material_v1(
        document_pages_sha256=document_pages_sha256,
        exact_hits_sha256=exact_hits_sha256,
        family_spec_sha256=family_spec_sha256,
    )
    return _PreparedOneEditExactSourceAxisV1(
        document_pages_sha256=document_pages_sha256,
        exact_hits_sha256=exact_hits_sha256,
        family_spec_sha256=family_spec_sha256,
        prepared_axis_sha256=canonical_json_sha256_v1(material),
        exact_hits=exact_hits,
        seal=_PREPARED_ONE_EDIT_EXACT_SOURCE_AXIS_SEAL,
    )


def _open_prepared_one_edit_exact_source_axis_v1(
    value: Any,
    *,
    document_pages_sha256: str,
    family_spec_sha256: str,
) -> dict[str, Any]:
    if (
        type(value) is not _PreparedOneEditExactSourceAxisV1
        or value.seal is not _PREPARED_ONE_EDIT_EXACT_SOURCE_AXIS_SEAL
        or value.document_pages_sha256 != document_pages_sha256
        or value.family_spec_sha256 != family_spec_sha256
        or value.exact_hits_sha256 != canonical_json_sha256_v1(value.exact_hits)
    ):
        raise _error("prepared one-edit exact-source axis differs from its source")
    material = _prepared_exact_source_axis_material_v1(
        document_pages_sha256=value.document_pages_sha256,
        exact_hits_sha256=value.exact_hits_sha256,
        family_spec_sha256=value.family_spec_sha256,
    )
    if value.prepared_axis_sha256 != canonical_json_sha256_v1(material):
        raise _error("prepared one-edit exact-source axis binding drifted")
    return canonical_clone_v1(value.exact_hits)


def _same_turn_exact_source_hits_v1(
    pages: Sequence[Mapping[str, Any]],
    compiled: Mapping[str, Any],
    *,
    document_pages: Any,
    family_spec: Any,
    prepared_axis_cache: dict[tuple[str, str], Any] | None,
) -> dict[str, Any]:
    """Open one local content-bound scan or build it for public standalone use."""

    if prepared_axis_cache is None:
        exact_hits, _source_pages = _source_exact_axes(pages, compiled)
        return exact_hits
    document_pages_sha256 = canonical_json_sha256_v1(document_pages)
    family_spec_sha256 = canonical_json_sha256_v1(family_spec)
    key = (document_pages_sha256, family_spec_sha256)
    prepared = prepared_axis_cache.get(key)
    if prepared is None:
        prepared = _prepare_one_edit_exact_source_axis_v1(
            pages,
            compiled,
            document_pages=document_pages,
            family_spec=family_spec,
        )
        prepared_axis_cache[key] = prepared
    return _open_prepared_one_edit_exact_source_axis_v1(
        prepared,
        document_pages_sha256=document_pages_sha256,
        family_spec_sha256=family_spec_sha256,
    )


def _context_bound_source_records(
    exact_hits: Mapping[str, Any],
    compiled: Mapping[str, Any],
    selected_region: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return topology_v1._child_records_in_range(  # noqa: SLF001
        exact_hits["children"],
        compiled,
        retain_all_occurrences=True,
        start=selected_region["cluster_start_document_line_ordinal"],
        stop=selected_region["cluster_end_document_line_ordinal_exclusive"],
    )


def _source_occurrence_id_v1(match: Mapping[str, Any]) -> str:
    return "afeoeav1:source-occurrence:" + canonical_json_sha256_v1(
        {
            "document_line_ordinal": match["document_line_ordinal"],
            "end_document_line_ordinal": match["end_document_line_ordinal"],
            "matched_within_role": match.get("matched_within_role"),
            "page_sequence": match["page_sequence"],
            "role": match["role"],
            "role_occurrence_ordinal": match["role_occurrence_ordinal"],
            "source_line_index": match["source_line_index"],
            "end_source_line_index": match["end_source_line_index"],
        }
    )


def _decorate_exact_source_occurrences_v1(
    source_records: Sequence[Mapping[str, Any]],
    pages: Sequence[Mapping[str, Any]],
    selected_region: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Give exact PP-OCR records an independent deterministic owner axis."""

    root_scope_id = "afeoeav1:source-root:" + canonical_json_sha256_v1(
        {
            "family_parent": selected_region.get("parent_match"),
            "region_end": selected_region["cluster_end_document_line_ordinal_exclusive"],
            "region_start": selected_region["cluster_start_document_line_ordinal"],
        }
    )
    decorated = []
    for source_record in source_records:
        match = canonical_clone_v1(source_record)
        page = next(item for item in pages if item["page_sequence"] == match["page_sequence"])
        source_line = next(
            line
            for line in page["lines"]
            if line["source_line_index"] == match["source_line_index"]
        )
        match["source_label_bbox"] = canonical_clone_v1(source_line["bbox"])
        match["source_occurrence_id"] = _source_occurrence_id_v1(match)
        decorated.append(match)
    if len({item["source_occurrence_id"] for item in decorated}) != len(decorated):
        raise _error("exact-source occurrence identity repeats")
    for match in decorated:
        within_role = match.get("matched_within_role")
        owners = []
        for candidate in decorated:
            if (
                candidate["role"] != within_role
                or candidate["source_occurrence_id"] == match["source_occurrence_id"]
            ):
                continue
            source_precedes = candidate["document_line_ordinal"] <= match["document_line_ordinal"]
            parent_bbox = candidate["source_label_bbox"]
            child_bbox = match["source_label_bbox"]
            text_height = max(
                parent_bbox[3] - parent_bbox[1],
                child_bbox[3] - child_bbox[1],
            )
            visual_precedes = (
                candidate["page_sequence"] == match["page_sequence"]
                and parent_bbox[1] <= child_bbox[1]
                and parent_bbox[3] <= child_bbox[3]
                and 2 * (child_bbox[1] - parent_bbox[3]) >= -text_height
            )
            if source_precedes or visual_precedes:
                owners.append(candidate)
        owner = max(
            owners,
            key=lambda item: (
                item["page_sequence"],
                item["source_label_bbox"][1],
                item["source_label_bbox"][3],
                item["document_line_ordinal"],
            ),
            default=None,
        )
        match["source_scope_owner_occurrence_id"] = (
            owner["source_occurrence_id"]
            if owner is not None
            else root_scope_id
            if within_role is None
            else None
        )
        match["source_scope_owner_role"] = owner["role"] if owner is not None else None
    return decorated


def _nearest_selected_owner(
    match: Mapping[str, Any], effective_matches: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    owner_id = match.get("scope_owner_occurrence_id")
    if owner_id is not None:
        selected = [item for item in effective_matches if item.get("occurrence_id") == owner_id]
        if len(selected) == 1:
            return selected[0]
    within_role = match.get("matched_within_role")
    if within_role is None:
        return None
    preceding = [
        item
        for item in effective_matches
        if item.get("role") == within_role
        and item.get("document_line_ordinal", -1) <= match.get("document_line_ordinal", -1)
        and item is not match
    ]
    return max(
        preceding,
        key=lambda item: (
            item.get("document_line_ordinal", -1),
            item.get("end_document_line_ordinal", -1),
        ),
        default=None,
    )


def _nearest_source_owner(
    match: Mapping[str, Any], source_occurrences: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    owner_id = match.get("source_scope_owner_occurrence_id")
    selected = [item for item in source_occurrences if item.get("source_occurrence_id") == owner_id]
    if len(selected) == 1:
        return selected[0]
    return None


def _exact_source_occurrence_matches_retrieval_v1(
    retrieval: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    compiled: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
) -> bool:
    if (
        source.get("role") != retrieval.get("role")
        or source.get("matched_within_role") != retrieval.get("matched_within_role")
        or not _same_match_span(source, retrieval, pages)
    ):
        return False
    surface = _source_surface(source, pages)
    if surface is None:
        return False
    aliases = _alias_entries(
        compiled,
        role=retrieval["role"],
        within_role=retrieval.get("matched_within_role"),
    )
    return len(_exact_alias_bindings(surface, aliases)) == 1


def _exact_source_owner_chain_matches_retrieval_v1(
    retrieval: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    compiled: Mapping[str, Any],
    effective_matches: Sequence[Mapping[str, Any]],
    pages: Sequence[Mapping[str, Any]],
    source_occurrences: Sequence[Mapping[str, Any]],
    visited: set[tuple[str, str]] | None = None,
) -> bool:
    """Recursively bind one exact occurrence and every nearest owner."""

    if not _exact_source_occurrence_matches_retrieval_v1(
        retrieval,
        source,
        compiled=compiled,
        pages=pages,
    ):
        return False
    retrieval_id = retrieval.get("occurrence_id")
    source_id = source.get("source_occurrence_id")
    if type(retrieval_id) is not str:
        return False
    pair = (retrieval_id, source_id if type(source_id) is str else "EXACT_RAW_SAME_SPAN")
    seen = set() if visited is None else visited
    if pair in seen:
        return False
    seen.add(pair)
    retrieval_owner = _nearest_selected_owner(retrieval, effective_matches)
    within_role = retrieval.get("matched_within_role")
    if within_role is None:
        return retrieval_owner is None
    if retrieval_owner is None or retrieval_owner.get("role") != within_role:
        return False
    source_owner = _nearest_source_owner(source, source_occurrences)
    # An exact retrieval owner already seals the selected role/parent context
    # and nearest-owner geometry.  Independent PP-OCR exactness is required
    # only for retrieval nodes that themselves used one-edit search.  But an
    # independently exact *contradictory* owner may not be ignored.
    if not _is_one_edit(retrieval_owner):
        return source_owner is None or _exact_source_occurrence_matches_retrieval_v1(
            retrieval_owner,
            source_owner,
            compiled=compiled,
            pages=pages,
        )
    if source_owner is None:
        return False
    return _exact_source_owner_chain_matches_retrieval_v1(
        retrieval_owner,
        source_owner,
        compiled=compiled,
        effective_matches=effective_matches,
        pages=pages,
        source_occurrences=source_occurrences,
        visited=seen,
    )


def _complementary_token_owner_chain_matches_retrieval_v1(
    retrieval: Mapping[str, Any],
    *,
    compiled: Mapping[str, Any],
    effective_matches: Sequence[Mapping[str, Any]],
    pages: Sequence[Mapping[str, Any]],
    source_occurrences: Sequence[Mapping[str, Any]],
) -> bool:
    """Require the same independent recursive owner checks as exact PP text."""

    retrieval_owner = _nearest_selected_owner(retrieval, effective_matches)
    within_role = retrieval.get("matched_within_role")
    if within_role is None:
        return retrieval_owner is None
    if retrieval_owner is None or retrieval_owner.get("role") != within_role:
        return False
    same_span_exact = [
        source for source in source_occurrences if _same_match_span(source, retrieval_owner, pages)
    ]
    matching = [
        source
        for source in same_span_exact
        if _exact_source_occurrence_matches_retrieval_v1(
            retrieval_owner,
            source,
            compiled=compiled,
            pages=pages,
        )
    ]
    # An independently exact contradictory owner on the same physical span
    # cannot be ignored.  Exact retrieval owners otherwise already seal their
    # canonical role/geometry; one-edit owners still need one recursively
    # exact source occurrence, matching the pre-existing authority rule.
    if same_span_exact:
        if len(same_span_exact) != 1 or len(matching) != 1:
            return False
        return _exact_source_owner_chain_matches_retrieval_v1(
            retrieval_owner,
            matching[0],
            compiled=compiled,
            effective_matches=effective_matches,
            pages=pages,
            source_occurrences=source_occurrences,
        )
    return not _is_one_edit(retrieval_owner)


def _empty_exact_channel(
    *, source_surface: str | None, context_binding: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "alias_normalized": None,
        "alias_pointer": None,
        "alias_sha256": None,
        "channel": "PPOCR_BOUND_SOURCE_TEXT_EXACT",
        "context_binding": canonical_clone_v1(context_binding),
        "context_binding_sha256": canonical_json_sha256_v1(context_binding),
        "normalized_surface": (
            normalize_vietnamese_anchor_v1(source_surface) if source_surface is not None else None
        ),
        "source_surface": source_surface,
        "source_surface_sha256": (
            canonical_json_sha256_v1(source_surface) if source_surface is not None else None
        ),
        "transform": None,
    }


def _check(
    match: Mapping[str, Any],
    *,
    aliases: Sequence[Mapping[str, str]],
    compiled: Mapping[str, Any],
    effective_matches: Sequence[Mapping[str, Any]],
    exact_hits: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    selected_region: Mapping[str, Any],
    source_occurrences: Sequence[Mapping[str, Any]],
    match_scope: str,
) -> dict[str, Any]:
    indices = _match_line_indices(match, pages)
    role = compiled["parent"]["role"] if match_scope == "FAMILY_PARENT" else match["role"]
    within_role = None if match_scope == "FAMILY_PARENT" else match.get("matched_within_role")
    occurrence_id = None if match_scope == "FAMILY_PARENT" else match.get("occurrence_id")
    retrieval_candidates = _retrieval_alias_candidates(match, aliases)
    retrieval_alias_axis = [
        {
            "alias_normalized": item["alias"],
            "alias_pointer": item["pointer"],
            "alias_sha256": canonical_json_sha256_v1(item["alias"]),
        }
        for item in retrieval_candidates
    ]
    retrieval = {
        "alias_candidates": retrieval_alias_axis,
        "alias_candidates_sha256": canonical_json_sha256_v1(retrieval_alias_axis),
        "channel": "VIETOCR_TRANSFORMER_RETRIEVAL_ONLY",
        "match_kind": match["match_kind"],
        "normalized_surface": normalize_vietnamese_anchor_v1(match["surface"]),
        "surface": match["surface"],
    }
    selected_parent = selected_region.get("parent_match")
    owner = _nearest_selected_owner(match, effective_matches)
    context_binding = {
        "family_id": compiled["family_id"],
        "family_parent": (
            _match_identity(selected_parent, pages) if selected_parent is not None else None
        ),
        "occurrence_id": occurrence_id,
        "parent_resolution": selected_region["parent_resolution"],
        "scope_owner_occurrence_id": (
            None if match_scope == "FAMILY_PARENT" else match.get("scope_owner_occurrence_id")
        ),
        "selected_region_sha256": canonical_json_sha256_v1(selected_region),
        "structural_parent": _match_identity(owner, pages) if owner is not None else None,
        "within_role": within_role,
    }
    surface = _source_surface(match, pages)
    exact_channel = _empty_exact_channel(
        source_surface=surface,
        context_binding=context_binding,
    )
    status = "RETRIEVAL_ONE_EDIT_ALIAS_SPEC_BINDING_DRIFTED"
    if retrieval_candidates and surface is None:
        status = "MISSING_BOUND_SOURCE_TEXT"
    exact_bindings = _exact_alias_bindings(surface, aliases) if surface is not None else []
    coextensive_parent_child = (
        match_scope == "EXPANDED_OCCURRENCE"
        and selected_parent is not None
        and _same_match_span(match, selected_parent, pages)
    )
    if match_scope == "FAMILY_PARENT":
        source_role_axis = exact_hits["parents"]
    else:
        raw_source_role_axis = [
            {
                **canonical_clone_v1(item),
                "matched_within_role": item.get("_within_role"),
                "role": role,
            }
            for item in exact_hits["children"].get(role, [])
        ]
        source_role_axis = [item for item in source_occurrences if item["role"] == role]
        if coextensive_parent_child:
            source_role_axis = raw_source_role_axis
        else:
            decorated_same_physical_span = [
                item for item in source_role_axis if _same_match_span(item, match, pages)
            ]
            decorated_signatures = {
                (
                    item.get("page_sequence"),
                    item.get("source_line_index"),
                    item.get("end_source_line_index"),
                    item.get("matched_within_role"),
                )
                for item in source_role_axis
            }
            if not decorated_same_physical_span:
                source_role_axis.extend(
                    item
                    for item in raw_source_role_axis
                    if (
                        item.get("page_sequence"),
                        item.get("source_line_index"),
                        item.get("end_source_line_index"),
                        item.get("matched_within_role"),
                    )
                    not in decorated_signatures
                )
    same_role_context_span = [
        item
        for item in source_role_axis
        if (
            (match_scope == "FAMILY_PARENT" or item.get("matched_within_role") == within_role)
            and _same_match_span(item, match, pages)
        )
    ]
    exact_parent = (
        None
        if selected_parent is None
        else next(
            (
                item
                for item in exact_hits["parents"]
                if _same_match_span(item, selected_parent, pages)
                and _exact_alias_bindings(
                    _source_surface(selected_parent, pages) or "",
                    _alias_entries(
                        compiled,
                        role=compiled["parent"]["role"],
                        within_role=None,
                    ),
                )
            ),
            None,
        )
    )
    source_occurrence = same_role_context_span[0] if len(same_role_context_span) == 1 else None
    source_owner_chain_bound = (
        match_scope == "FAMILY_PARENT"
        or source_occurrence is not None
        and _exact_source_owner_chain_matches_retrieval_v1(
            match,
            source_occurrence,
            compiled=compiled,
            effective_matches=effective_matches,
            pages=pages,
            source_occurrences=source_occurrences,
        )
    )
    complementary_token_authority = (
        _same_crop_complementary_token_authority_v1(
            match,
            aliases=aliases,
            pages=pages,
            retrieval_candidates=retrieval_candidates,
        )
        if match_scope == "EXPANDED_OCCURRENCE" and not exact_bindings
        else None
    )
    complementary_owner_chain_bound = (
        complementary_token_authority is not None
        and _complementary_token_owner_chain_matches_retrieval_v1(
            match,
            compiled=compiled,
            effective_matches=effective_matches,
            pages=pages,
            source_occurrences=source_occurrences,
        )
    )
    if retrieval_candidates and surface is not None:
        if not exact_bindings:
            if (
                complementary_token_authority is not None
                and selected_parent is not None
                and _is_one_edit(selected_parent)
                and exact_parent is None
            ):
                status = "EXACT_FAMILY_PARENT_CONTEXT_MISMATCH"
            elif complementary_token_authority is not None and not complementary_owner_chain_bound:
                status = "EXACT_STRUCTURAL_PARENT_CONTEXT_MISMATCH"
            elif complementary_token_authority is not None:
                status = "SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_ALIAS_BOUND"
                exact_channel.update(
                    {
                        "alias_normalized": complementary_token_authority["alias_normalized"],
                        "alias_pointer": complementary_token_authority["alias_pointer"],
                        "alias_sha256": complementary_token_authority["alias_sha256"],
                        "channel": "PPOCR_AND_VIETOCR_SAME_CROP_COMPLEMENTARY_TOKEN_EXACT",
                        "normalized_surface": complementary_token_authority["alias_normalized"],
                        "transform": "SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_COVERAGE",
                    }
                )
            elif any(
                topology_v1._one_edit_alias_is_safe(  # noqa: SLF001
                    normalized, alias["alias"]
                )
                and normalized != alias["alias"]
                for _transform, normalized in _exact_axes(surface)
                for alias in aliases
            ):
                status = "BOUND_SOURCE_TEXT_REMAINS_ONE_EDIT_NOT_EXACT"
            elif any(
                item
                for item in source_role_axis
                if (
                    match_scope == "FAMILY_PARENT" or item.get("matched_within_role") == within_role
                )
            ):
                status = "EXACT_ALIAS_DIFFERENT_SOURCE_SPAN"
            else:
                status = "NO_EXACT_DECLARED_ALIAS_ON_RETRIEVAL_SOURCE_SPAN"
        elif selected_parent is not None and _is_one_edit(selected_parent) and exact_parent is None:
            status = "EXACT_FAMILY_PARENT_CONTEXT_MISMATCH"
        elif match_scope == "EXPANDED_OCCURRENCE" and not source_owner_chain_bound:
            status = "EXACT_STRUCTURAL_PARENT_CONTEXT_MISMATCH"
        elif len(exact_bindings) != 1 or len(same_role_context_span) != 1:
            # An exact surface under another role/parent or on another span is
            # not independent corroboration of this selected retrieval match.
            status = (
                "EXACT_ALIAS_DIFFERENT_SOURCE_SPAN"
                if any(
                    item
                    for item in source_role_axis
                    if (
                        match_scope == "FAMILY_PARENT"
                        or item.get("matched_within_role") == within_role
                    )
                )
                else "NO_EXACT_DECLARED_ALIAS_ON_RETRIEVAL_SOURCE_SPAN"
            )
        else:
            binding = exact_bindings[0]
            status = "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"
            exact_channel.update(
                {
                    "alias_normalized": binding["alias"],
                    "alias_pointer": binding["pointer"],
                    "alias_sha256": canonical_json_sha256_v1(binding["alias"]),
                    "normalized_surface": binding["alias"],
                    "transform": binding["transform"],
                }
            )
    role_kind = (
        "FAMILY_PARENT" if match_scope == "FAMILY_PARENT" else str(match.get("role_kind", ""))
    )
    return {
        "complementary_token_authority": (
            complementary_token_authority
            if status == "SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_ALIAS_BOUND"
            else None
        ),
        "exact_channel": exact_channel,
        "match_scope": match_scope,
        "occurrence_id": occurrence_id,
        "page_sequence": match["page_sequence"],
        "retrieval_channel": retrieval,
        "role": role,
        "role_kind": role_kind,
        "source_line_indices": list(indices),
        "status": status,
        "within_role": within_role,
    }


def _validate_complementary_token_authority_shape_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _COMPLEMENTARY_FIELDS
        or value["format_version"] != _COMPLEMENTARY_FORMAT_VERSION
        or type(value["alias_normalized"]) is not str
        or len(value["alias_normalized"].split()) < 2
        or type(value["alias_pointer"]) is not str
        or not value["alias_pointer"]
        or value["alias_sha256"] != canonical_json_sha256_v1(value["alias_normalized"])
        or type(value["channel_proofs"]) is not list
        or len(value["channel_proofs"]) != 2
        or type(value["crop_binding"]) is not dict
        or set(value["crop_binding"]) != _COMPLEMENTARY_CROP_BINDING_FIELDS
        or value["crop_binding_sha256"] != canonical_json_sha256_v1(value["crop_binding"])
        or type(value["token_axis"]) is not list
    ):
        raise _error("same-crop complementary-token authority shape drifted")
    crop_binding = value["crop_binding"]
    bbox = crop_binding["bbox"]
    if (
        type(bbox) is not list
        or len(bbox) != 4
        or any(type(item) is not int for item in bbox)
        or bbox[2] <= bbox[0]
        or bbox[3] <= bbox[1]
        or type(crop_binding["page_sequence"]) is not int
        or crop_binding["page_sequence"] <= 0
        or type(crop_binding["source_line_index"]) is not int
        or crop_binding["source_line_index"] < 0
        or type(crop_binding["sample_id"]) is not str
        or not crop_binding["sample_id"]
    ):
        raise _error("same-crop complementary-token crop binding drifted")
    _crop_reference(crop_binding["crop_ref"])
    alias_tokens = value["alias_normalized"].split()
    expected_channels = [
        "PPOCR_BOUND_SOURCE_TEXT",
        "VIETOCR_TRANSFORMER_RETRIEVAL_ONLY",
    ]
    mismatch_axes = []
    for proof, expected_channel in zip(value["channel_proofs"], expected_channels, strict=True):
        if (
            type(proof) is not dict
            or set(proof) != _COMPLEMENTARY_CHANNEL_FIELDS
            or proof["channel"] != expected_channel
            or type(proof["surface"]) is not str
            or not proof["surface"].strip()
            or proof["normalized_surface"] != normalize_vietnamese_anchor_v1(proof["surface"])
            or proof["tokens"] != proof["normalized_surface"].split()
            or len(proof["tokens"]) != len(alias_tokens)
            or type(proof["mismatch_token_indices"]) is not list
            or type(proof["exact_token_indices"]) is not list
        ):
            raise _error("same-crop complementary-token channel proof drifted")
        mismatches = [
            index
            for index, (candidate, alias) in enumerate(
                zip(proof["tokens"], alias_tokens, strict=True)
            )
            if candidate != alias
        ]
        if (
            proof["mismatch_token_indices"] != mismatches
            or len(mismatches) != 1
            or proof["exact_token_indices"]
            != [index for index in range(len(alias_tokens)) if index not in mismatches]
            or type(proof["edit"]) is not dict
            or set(proof["edit"]) != _COMPLEMENTARY_EDIT_FIELDS
            or proof["edit"]
            != _single_character_edit(
                proof["tokens"][mismatches[0]],
                alias_tokens[mismatches[0]],
                token_index=mismatches[0],
            )
        ):
            raise _error("same-crop complementary-token edit proof drifted")
        mismatch_axes.append(set(mismatches))
    if mismatch_axes[0] & mismatch_axes[1]:
        raise _error("same-crop complementary-token edit axes overlap")
    expected_token_axis = [
        {
            "alias_token": alias_token,
            "exact_channels": [
                proof["channel"]
                for proof in value["channel_proofs"]
                if token_index in proof["exact_token_indices"]
            ],
            "token_index": token_index,
        }
        for token_index, alias_token in enumerate(alias_tokens)
    ]
    if (
        any(not item["exact_channels"] for item in expected_token_axis)
        or value["token_axis"] != expected_token_axis
    ):
        raise _error("same-crop complementary-token exact coverage drifted")
    material = canonical_clone_v1(value)
    proof_id = material.pop("proof_id")
    if proof_id != "afcetav1:proof:" + canonical_json_sha256_v1(material):
        raise _error("same-crop complementary-token proof identity drifted")
    return canonical_clone_v1(value)


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["authority_spec"]) is not dict
        or set(value["authority_spec"]) != {"sha256", "value"}
        or not same_typed_json_v1(value["authority_spec"]["value"], _AUTHORITY_SPEC)
        or value["authority_spec"]["sha256"] != canonical_json_sha256_v1(_AUTHORITY_SPEC)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["input_binding"]) is not dict
        or set(value["input_binding"]) != _INPUT_BINDING_FIELDS
        or any(
            type(item) is not str
            or len(item) != 64
            or any(character not in "0123456789abcdef" for character in item)
            for item in value["input_binding"].values()
        )
        or type(value["metrics"]) is not dict
        or set(value["metrics"]) != _METRIC_FIELDS
        or any(type(item) is not int or item < 0 for item in value["metrics"].values())
        or type(value["checks"]) is not list
        or value["status"] not in _STATUSES
        or type(value["unresolved_reasons"]) is not list
        or any(type(reason) is not str or not reason for reason in value["unresolved_reasons"])
    ):
        raise _error("one-edit exact-authority receipt shape drifted")
    for check in value["checks"]:
        exact = check.get("exact_channel") if type(check) is dict else None
        retrieval = check.get("retrieval_channel") if type(check) is dict else None
        complementary = check.get("complementary_token_authority") if type(check) is dict else None
        if type(check) is dict and check.get("status") == (
            "SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_ALIAS_BOUND"
        ):
            _validate_complementary_token_authority_shape_v1(complementary)
        elif complementary is not None:
            raise _error("unbound one-edit check retained complementary-token authority")
        if (
            type(check) is not dict
            or set(check) != _CHECK_FIELDS
            or check["match_scope"] not in {"EXPANDED_OCCURRENCE", "FAMILY_PARENT"}
            or (check["match_scope"] == "FAMILY_PARENT" and check["occurrence_id"] is not None)
            or (
                check["match_scope"] == "EXPANDED_OCCURRENCE"
                and (type(check["occurrence_id"]) is not str or not check["occurrence_id"])
            )
            or type(check["role"]) is not str
            or not check["role"]
            or type(check["role_kind"]) is not str
            or not check["role_kind"]
            or (
                check["within_role"] is not None
                and (type(check["within_role"]) is not str or not check["within_role"])
            )
            or type(check["page_sequence"]) is not int
            or check["page_sequence"] <= 0
            or type(check["source_line_indices"]) is not list
            or not check["source_line_indices"]
            or any(type(index) is not int or index < 0 for index in check["source_line_indices"])
            or check["status"] not in _CHECK_STATUSES
            or type(retrieval) is not dict
            or set(retrieval) != _RETRIEVAL_FIELDS
            or retrieval["channel"] != "VIETOCR_TRANSFORMER_RETRIEVAL_ONLY"
            or not str(retrieval["match_kind"]).startswith("ONE_EDIT_ALIAS")
            or type(retrieval["alias_candidates"]) is not list
            or any(
                type(alias) is not dict
                or set(alias) != {"alias_normalized", "alias_pointer", "alias_sha256"}
                or type(alias["alias_normalized"]) is not str
                or not alias["alias_normalized"]
                or type(alias["alias_pointer"]) is not str
                or not alias["alias_pointer"]
                or alias["alias_sha256"] != canonical_json_sha256_v1(alias["alias_normalized"])
                for alias in retrieval["alias_candidates"]
            )
            or retrieval["alias_candidates_sha256"]
            != canonical_json_sha256_v1(retrieval["alias_candidates"])
            or type(exact) is not dict
            or set(exact) != _EXACT_FIELDS
            or exact["channel"]
            != (
                "PPOCR_AND_VIETOCR_SAME_CROP_COMPLEMENTARY_TOKEN_EXACT"
                if check["status"] == "SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_ALIAS_BOUND"
                else "PPOCR_BOUND_SOURCE_TEXT_EXACT"
            )
            or type(exact["context_binding"]) is not dict
            or set(exact["context_binding"]) != _CONTEXT_FIELDS
            or exact["context_binding"]["family_id"] != value["family_id"]
            or exact["context_binding"].get("occurrence_id") != check["occurrence_id"]
            or exact["context_binding"].get("within_role") != check["within_role"]
            or exact["context_binding"]["selected_region_sha256"]
            != value["input_binding"]["selected_topology_region_sha256"]
            or (
                check["match_scope"] == "FAMILY_PARENT"
                and exact["context_binding"]["scope_owner_occurrence_id"] is not None
            )
            or (
                exact["context_binding"]["structural_parent"] is not None
                and exact["context_binding"]["structural_parent"].get("occurrence_id")
                != exact["context_binding"]["scope_owner_occurrence_id"]
            )
            or exact["context_binding_sha256"] != canonical_json_sha256_v1(exact["context_binding"])
            or (exact["source_surface"] is None and exact["source_surface_sha256"] is not None)
            or (
                exact["source_surface"] is not None
                and exact["source_surface_sha256"]
                != canonical_json_sha256_v1(exact["source_surface"])
            )
            or (
                check["status"] in _BOUND_CHECK_STATUSES
                and (
                    exact["alias_pointer"] is None
                    or exact["alias_normalized"] is None
                    or exact["alias_sha256"] != canonical_json_sha256_v1(exact["alias_normalized"])
                    or (
                        check["status"] == "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"
                        and exact["transform"] not in _AUTHORITY_SPEC["allowed_exact_transforms"]
                    )
                    or (
                        check["status"] == "SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_ALIAS_BOUND"
                        and exact["transform"] != "SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_COVERAGE"
                    )
                )
            )
        ):
            raise _error("one-edit exact-authority check axis drifted")
        if check["status"] == "SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_ALIAS_BOUND" and (
            check["match_scope"] != "EXPANDED_OCCURRENCE"
            or check["source_line_indices"] != [complementary["crop_binding"]["source_line_index"]]
            or check["page_sequence"] != complementary["crop_binding"]["page_sequence"]
            or exact["alias_normalized"] != complementary["alias_normalized"]
            or exact["alias_pointer"] != complementary["alias_pointer"]
            or exact["alias_sha256"] != complementary["alias_sha256"]
            or exact["source_surface"] != complementary["channel_proofs"][0]["surface"]
            or retrieval["surface"] != complementary["channel_proofs"][1]["surface"]
            or retrieval["alias_candidates"]
            != [
                {
                    "alias_normalized": complementary["alias_normalized"],
                    "alias_pointer": complementary["alias_pointer"],
                    "alias_sha256": complementary["alias_sha256"],
                }
            ]
        ):
            raise _error("same-crop complementary-token check binding drifted")
    bound = sum(check["status"] in _BOUND_CHECK_STATUSES for check in value["checks"])
    occurrence_ids = [
        check["occurrence_id"]
        for check in value["checks"]
        if check["match_scope"] == "EXPANDED_OCCURRENCE"
    ]
    if len(occurrence_ids) != len(set(occurrence_ids)):
        raise _error("one-edit exact-authority occurrence identity repeats")
    metrics = {
        "exact_bound_count": bound,
        "selected_one_edit_match_count": len(value["checks"]),
        "unresolved_match_count": len(value["checks"]) - bound,
    }
    expected_status = (
        "NOT_REQUIRED_NO_SELECTED_ONE_EDIT_RETRIEVAL"
        if not value["checks"]
        else "EXACT_SOURCE_AUTHORITY_BOUND"
        if bound == len(value["checks"])
        else "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY"
    )
    expected_reasons = [
        (
            f"ONE_EDIT_EXACT_AUTHORITY:{check['status']}:{check['role']}:"
            f"OCCURRENCE_{check['occurrence_id'] or 'FAMILY_PARENT'}:"
            f"PAGE_{check['page_sequence']}:LINES_"
            + ",".join(str(index) for index in check["source_line_indices"])
        )
        for check in value["checks"]
        if check["status"] not in _BOUND_CHECK_STATUSES
    ]
    if (
        not same_typed_json_v1(value["metrics"], metrics)
        or value["status"] != expected_status
        or value["unresolved_reasons"] != expected_reasons
    ):
        raise _error("one-edit exact-authority status or metrics drifted")
    material = canonical_clone_v1(value)
    receipt_id = material.pop("receipt_id")
    if receipt_id != "afeoeav1:receipt:" + canonical_json_sha256_v1(material):
        raise _error("one-edit exact-authority receipt identity drifted")
    return canonical_clone_v1(value)


def _parent_frontier_reason(check: Mapping[str, Any]) -> str:
    return (
        f"ONE_EDIT_EXACT_AUTHORITY:{check['status']}:{check['role']}:"
        f"OCCURRENCE_{check['occurrence_id'] or 'FAMILY_PARENT'}:"
        f"PAGE_{check['page_sequence']}:LINES_"
        + ",".join(str(index) for index in check["source_line_indices"])
    )


def _parent_frontier_structural_evidence_v1(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise _error("one-edit parent-frontier structural evidence drifted")
    required = {
        "internal_unassigned_numeric_clusters",
        "numeric_sample_universe",
        "role_occurrences",
        "row_axis",
    }
    if not required <= set(value):
        raise _error("one-edit parent-frontier structural evidence fields drifted")
    try:
        row_axis = row_v1._validate_result(value["row_axis"])  # noqa: SLF001
    except row_v1.AccountingFamilyRowAxisV1Error as exc:
        raise _error("one-edit parent-frontier row axis drifted") from exc
    axes = {
        key: value[key]
        for key in (
            "internal_unassigned_numeric_clusters",
            "numeric_sample_universe",
            "role_occurrences",
        )
    }
    if any(type(axis) is not list for axis in axes.values()):
        raise _error("one-edit parent-frontier occurrence evidence axis drifted")
    furniture = value.get("authenticated_extreme_margin_furniture_evidence", [])
    if type(furniture) is not list:
        raise _error("one-edit parent-frontier furniture evidence axis drifted")
    return {
        "authenticated_extreme_margin_furniture_evidence": canonical_clone_v1(furniture),
        "internal_unassigned_numeric_clusters": canonical_clone_v1(
            axes["internal_unassigned_numeric_clusters"]
        ),
        "numeric_sample_universe": canonical_clone_v1(axes["numeric_sample_universe"]),
        "role_occurrences": canonical_clone_v1(axes["role_occurrences"]),
        "row_axis": row_axis,
    }


def _parent_frontier_input_binding_v1(
    source_receipt: Mapping[str, Any],
    evidence: Mapping[str, Any],
    column_context: Mapping[str, Any],
) -> dict[str, str]:
    return {
        **canonical_clone_v1(source_receipt["input_binding"]),
        "column_context_sha256": canonical_json_sha256_v1(column_context),
        "internal_unassigned_numeric_clusters_sha256": canonical_json_sha256_v1(
            evidence["internal_unassigned_numeric_clusters"]
        ),
        "numeric_sample_universe_sha256": canonical_json_sha256_v1(
            evidence["numeric_sample_universe"]
        ),
        "role_occurrences_sha256": canonical_json_sha256_v1(evidence["role_occurrences"]),
        "row_axis_sha256": canonical_json_sha256_v1(evidence["row_axis"]),
        "source_exact_authority_receipt_sha256": canonical_json_sha256_v1(source_receipt),
    }


def _validate_parent_frontier_column_context_replay_v1(
    value: Any,
    *,
    row_axis: Any,
    document_pages: Any,
    authority_pages: Any,
    family_spec: Any,
    period_semantics: Any,
    expected_lane_unit_kinds: Any,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Rebuild V3 period/unit evidence from the authenticated source pages.

    A content hash over a caller-supplied column context is not source
    authentication: a caller can coherently change a date or currency and
    recompute every downstream identity.  V3 therefore re-runs the column
    reader over the exact occurrence row axis and the original joined-page
    evidence before it may project (or publicly replay) an authority.

    ``authority_pages`` is the independently projected PP-OCR/VietOCR page
    contract already bound by the V2 source receipt.  Re-projecting
    ``document_pages`` must equal it exactly, so a forged context cannot be
    rebuilt from a different page object.
    """

    try:
        context = column_context_multilevel_v2._validate_context_receipt_v2(  # noqa: SLF001
            value
        )
        parsed_context_pages = row_v1._pages(document_pages)  # noqa: SLF001
        expected_authority_pages = occurrence_row_v2._one_edit_authority_pages_v2(  # noqa: SLF001
            parsed_context_pages
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("one-edit parent-frontier column replay input drifted") from exc
    if not same_typed_json_v1(expected_authority_pages, authority_pages):
        raise _error("one-edit parent-frontier column pages differ from source authority")
    if (
        period_semantics not in {"BALANCE_COMPARATIVE", "CURRENT_ROLLFORWARD"}
        or type(expected_lane_unit_kinds) is not list
        or not expected_lane_unit_kinds
        or any(item not in {"MONEY", "PERCENT"} for item in expected_lane_unit_kinds)
        or type(visible_dash_rescues) is not tuple
    ):
        raise _error("one-edit parent-frontier column replay policy drifted")
    try:
        replayed = column_context_multilevel_v2._build_accounting_family_column_context_multilevel_from_authenticated_row_axis_v2(  # noqa: SLF001
            row_axis,
            parsed_context_pages,
            family_spec,
            period_semantics=period_semantics,
            expected_lane_unit_kinds=expected_lane_unit_kinds,
            visible_dash_rescues=visible_dash_rescues,
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("one-edit parent-frontier column context replay failed") from exc
    if not same_typed_json_v1(context, replayed):
        raise _error("one-edit parent-frontier column context does not replay exactly")
    return context


def _parent_frontier_number_axis_is_valid(value: Any) -> bool:
    return (
        type(value) is list
        and bool(value)
        and all(
            type(item) is dict
            and set(item) == {"coefficient", "percentage_mark_present", "scale"}
            and type(item["coefficient"]) is int
            and type(item["percentage_mark_present"]) is bool
            and type(item["scale"]) is int
            and item["scale"] >= 0
            for item in value
        )
    )


def _validate_parent_frontier_proof_shape_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _PARENT_FRONTIER_PROOF_FIELDS
        or value["format_version"] != _PARENT_FRONTIER_PROOF_FORMAT_VERSION
        or value["status"] != _PARENT_FRONTIER_BOUND_STATUS
        or type(value["source_check"]) is not dict
        or type(value["root_occurrence_id"]) is not str
        or not value["root_occurrence_id"].startswith("aforav2:root:")
        or type(value["target_occurrence_id"]) is not str
        or not value["target_occurrence_id"].startswith("aforav2:occurrence:")
        or type(value["target_role"]) is not str
        or not value["target_role"]
        or type(value["component_frontier_bindings"]) is not list
        or not value["component_frontier_bindings"]
        or type(value["input_binding"]) is not dict
        or set(value["input_binding"]) != _PARENT_FRONTIER_INPUT_BINDING_FIELDS
        or any(
            type(item) is not str
            or len(item) != 64
            or any(character not in "0123456789abcdef" for character in item)
            for item in value["input_binding"].values()
        )
        or type(value["parent_match_binding"]) is not dict
        or set(value["parent_match_binding"]) != _PARENT_MATCH_BINDING_FIELDS
        or type(value["column_context_receipt"]) is not dict
        or type(value["target_label_match"]) is not dict
        or type(value["source_scope_binding"]) is not dict
    ):
        raise _error("one-edit parent-frontier proof shape drifted")
    parent = value["parent_match_binding"]
    bbox = parent["label_bbox"]
    if (
        type(parent["page_sequence"]) is not int
        or parent["page_sequence"] <= 0
        or type(parent["source_line_indices"]) is not list
        or not parent["source_line_indices"]
        or parent["source_line_indices"] != sorted(set(parent["source_line_indices"]))
        or any(type(item) is not int or item < 0 for item in parent["source_line_indices"])
        or type(parent["document_line_span"]) is not list
        or len(parent["document_line_span"]) != 2
        or any(type(item) is not int or item < 0 for item in parent["document_line_span"])
        or parent["document_line_span"][1] < parent["document_line_span"][0]
        or type(bbox) is not list
        or len(bbox) != 4
        or any(type(item) is not int for item in bbox)
        or not bbox[0] < bbox[2]
        or not bbox[1] < bbox[3]
        or type(parent["result_sample_ids"]) is not list
        or not parent["result_sample_ids"]
        or len(parent["result_sample_ids"]) != len(set(parent["result_sample_ids"]))
        or any(type(item) is not str or not item for item in parent["result_sample_ids"])
        or not _parent_frontier_number_axis_is_valid(parent["numbers"])
        or len(parent["numbers"]) != len(parent["result_sample_ids"])
    ):
        raise _error("one-edit parent-frontier parent binding drifted")
    try:
        context = column_context_multilevel_v2._validate_context_receipt_v2(  # noqa: SLF001
            value["column_context_receipt"]
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("one-edit parent-frontier column binding drifted") from exc
    lane_count = len(context["period_axis"])
    if (
        context["status"] != "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
        or lane_count == 0
        or len(context["unit_axis"]) != lane_count
        or len(parent["numbers"]) != lane_count
        or len(
            {
                (item["unit_kind"], item["currency"], item["magnitude_power10"])
                for item in context["unit_axis"]
            }
        )
        != 1
    ):
        raise _error("one-edit parent-frontier column binding drifted")
    label = canonical_clone_v1(value["target_label_match"])
    label.pop("source_scope_binding", None)
    if (
        label.get("occurrence_id") != value["target_occurrence_id"]
        or label.get("role") != value["target_role"]
        or label.get("scope_owner_occurrence_id") != value["root_occurrence_id"]
        or label.get("scope_owner_role") is not None
    ):
        raise _error("one-edit parent-frontier target occurrence drifted")
    try:
        occurrence_row_v2._validate_source_scope_binding(  # noqa: SLF001
            value["source_scope_binding"],
            label_match=label,
            role=value["target_role"],
        )
    except occurrence_row_v2.AccountingFamilyOccurrenceRowAxisV2Error as exc:
        raise _error("one-edit parent-frontier source equation drifted") from exc
    equation = value["source_scope_binding"].get("geometry", {}).get("equation", {})
    if (
        equation.get("parent_occurrence_id") != value["root_occurrence_id"]
        or equation.get("result", {}).get("occurrence_id") != value["root_occurrence_id"]
        or equation.get("result", {}).get("sample_ids") != parent["result_sample_ids"]
        or equation.get("result", {}).get("numbers") != parent["numbers"]
        or len(equation.get("component_frontier", [])) != len(value["component_frontier_bindings"])
    ):
        raise _error("one-edit parent-frontier root equation binding drifted")
    component_occurrence_ids = []
    component_receipts = []
    source_component_occurrence_ids = []
    for ordinal, (binding, equation_component) in enumerate(
        zip(
            value["component_frontier_bindings"],
            equation["component_frontier"],
            strict=True,
        )
    ):
        row_receipt = binding.get("row_receipt") if type(binding) is dict else None
        if (
            type(binding) is not dict
            or set(binding) != _PARENT_FRONTIER_COMPONENT_BINDING_FIELDS
            or binding["component_ordinal"] != ordinal
            or not same_typed_json_v1(binding["equation_component"], equation_component)
            or type(binding["occurrence_id"]) is not str
            or not binding["occurrence_id"].startswith("aforav2:occurrence:")
            or type(binding["retrieval_role"]) is not str
            or not binding["retrieval_role"]
            or (
                binding["retrieval_within_role"] is not None
                and (
                    type(binding["retrieval_within_role"]) is not str
                    or not binding["retrieval_within_role"]
                )
            )
            or type(binding["source_line_indices"]) is not list
            or not binding["source_line_indices"]
            or binding["source_line_indices"] != sorted(set(binding["source_line_indices"]))
            or any(type(item) is not int or item < 0 for item in binding["source_line_indices"])
            or any(
                type(binding[key]) is not str
                or len(binding[key]) != 64
                or any(character not in "0123456789abcdef" for character in binding[key])
                for key in ("role_occurrence_sha256", "row_sha256")
            )
            or type(row_receipt) is not dict
            or set(row_receipt) != {"numbers", "sample_ids"}
            or not _parent_frontier_number_axis_is_valid(row_receipt["numbers"])
            or len(row_receipt["numbers"]) != lane_count
            or type(row_receipt["sample_ids"]) is not list
            or len(row_receipt["sample_ids"]) != lane_count
            or len(row_receipt["sample_ids"]) != len(set(row_receipt["sample_ids"]))
            or any(type(item) is not str or not item for item in row_receipt["sample_ids"])
            or row_receipt["numbers"] != equation_component.get("numbers")
            or row_receipt["sample_ids"] != equation_component.get("sample_ids")
        ):
            raise _error("one-edit parent-frontier component binding drifted")
        component_occurrence_ids.append(binding["occurrence_id"])
        component_receipts.append(row_receipt)
        if (
            equation_component.get("retrieval_occurrence_id")
            == equation.get("source_retrieval_occurrence_id")
            and equation_component.get("role") == value["target_role"]
        ):
            source_component_occurrence_ids.append(binding["occurrence_id"])
    if (
        len(component_occurrence_ids) != len(set(component_occurrence_ids))
        or source_component_occurrence_ids != [value["target_occurrence_id"]]
        or not occurrence_row_v2._direct_frontier_sum_is_exact(  # noqa: SLF001
            {"numbers": parent["numbers"]}, component_receipts
        )
    ):
        raise _error("one-edit parent-frontier ordered component axis drifted")
    source_check = value["source_check"]
    if (
        set(source_check) != _CHECK_FIELDS
        or source_check["status"] in _BOUND_CHECK_STATUSES
        or source_check["match_scope"] != "FAMILY_PARENT"
        or source_check["occurrence_id"] is not None
        or source_check["page_sequence"] != parent["page_sequence"]
        or source_check["source_line_indices"] != parent["source_line_indices"]
    ):
        raise _error("one-edit parent-frontier source check binding drifted")
    material = canonical_clone_v1(value)
    proof_id = material.pop("proof_id")
    if proof_id != "afeoepfav1:proof:" + canonical_json_sha256_v1(material):
        raise _error("one-edit parent-frontier proof identity drifted")
    return canonical_clone_v1(value)


def _validate_parent_frontier_result_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _PARENT_FRONTIER_RESULT_FIELDS
        or value.get("format_version") != PARENT_FRONTIER_FORMAT_VERSION
        or value.get("claim_boundary") != PARENT_FRONTIER_CLAIM_BOUNDARY
        or not same_typed_json_v1(value.get("safety"), _PARENT_FRONTIER_SAFETY)
        or type(value.get("authority_spec")) is not dict
        or set(value["authority_spec"]) != {"sha256", "value"}
        or not same_typed_json_v1(value["authority_spec"]["value"], _PARENT_FRONTIER_AUTHORITY_SPEC)
        or value["authority_spec"]["sha256"]
        != canonical_json_sha256_v1(_PARENT_FRONTIER_AUTHORITY_SPEC)
        or type(value.get("input_binding")) is not dict
        or set(value["input_binding"]) != _PARENT_FRONTIER_INPUT_BINDING_FIELDS
    ):
        raise _error("one-edit parent-frontier receipt shape drifted")
    source = _validate_result(value["source_exact_authority_receipt"])
    proof = _validate_parent_frontier_proof_shape_v1(value["parent_frontier_authority"])
    if (
        value["family_id"] != source["family_id"]
        or value["checks"] != source["checks"]
        or value["input_binding"] != proof["input_binding"]
        or value["input_binding"]["source_exact_authority_receipt_sha256"]
        != canonical_json_sha256_v1(source)
        or any(
            value["input_binding"][key] != source["input_binding"][key]
            for key in _INPUT_BINDING_FIELDS
        )
    ):
        raise _error("one-edit parent-frontier source receipt binding drifted")
    unbound_checks = [
        check for check in source["checks"] if check["status"] not in _BOUND_CHECK_STATUSES
    ]
    if (
        len(unbound_checks) != 1
        or unbound_checks[0]["match_scope"] != "FAMILY_PARENT"
        or not same_typed_json_v1(proof["source_check"], unbound_checks[0])
    ):
        raise _error("one-edit parent-frontier source check binding drifted")
    source_reason = _parent_frontier_reason(unbound_checks[0])
    expected_reasons = [
        reason for reason in source["unresolved_reasons"] if reason != source_reason
    ]
    expected_metrics = {
        "exact_bound_count": source["metrics"]["exact_bound_count"] + 1,
        "selected_one_edit_match_count": source["metrics"]["selected_one_edit_match_count"],
        "unresolved_match_count": source["metrics"]["unresolved_match_count"] - 1,
    }
    expected_status = (
        "EXACT_SOURCE_AUTHORITY_BOUND"
        if not expected_reasons
        else "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY"
    )
    if (
        value["metrics"] != expected_metrics
        or value["unresolved_reasons"] != expected_reasons
        or value["status"] != expected_status
    ):
        raise _error("one-edit parent-frontier status or metrics drifted")
    material = canonical_clone_v1(value)
    receipt_id = material.pop("receipt_id")
    if receipt_id != "afeoeav1:receipt:" + canonical_json_sha256_v1(material):
        raise _error("one-edit parent-frontier receipt identity drifted")
    return canonical_clone_v1(value)


def _replay_recursive_parent_direct_frontier_v1(
    role_occurrences: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    equation: Mapping[str, Any],
    *,
    page_sequence: int,
    root_occurrence_id: str,
    target_role: str,
) -> list[tuple[str, Mapping[str, Any]]] | None:
    component_roles = tuple(
        component.get("role") for component in equation.get("component_frontier", [])
    )
    matching_specs = [
        spec
        for spec in occurrence_row_v2._RECURSIVE_PARENT_PROVISION_BINDING_SPECS  # noqa: SLF001
        if spec["target_role"] == target_role
        and component_roles in spec["direct_component_role_alternatives"]
    ]
    if len(matching_specs) != 1:
        return None
    frontier = occurrence_row_v2._complete_recursive_parent_direct_frontier(  # noqa: SLF001
        role_occurrences,
        rows,
        matching_specs[0],
        interval_end=None,
        interval_start=None,
        page_sequence=page_sequence,
        parent_occurrence_id=root_occurrence_id,
        source_retrieval_occurrence_id=equation["source_retrieval_occurrence_id"],
    )
    if frontier is None or tuple(role for role, _row in frontier) != component_roles:
        return None
    return frontier


def _validate_parent_frontier_against_structural_evidence_v1(
    value: Any,
    structural_evidence: Any,
) -> dict[str, Any]:
    """Rebind a V3 proof to the occurrence axis that downstream consumes."""

    receipt = _validate_parent_frontier_result_v1(value)
    evidence = _parent_frontier_structural_evidence_v1(structural_evidence)
    proof = receipt["parent_frontier_authority"]
    binding = receipt["input_binding"]
    context = proof["column_context_receipt"]
    if (
        binding["internal_unassigned_numeric_clusters_sha256"]
        != canonical_json_sha256_v1(evidence["internal_unassigned_numeric_clusters"])
        or binding["numeric_sample_universe_sha256"]
        != canonical_json_sha256_v1(evidence["numeric_sample_universe"])
        or binding["role_occurrences_sha256"]
        != canonical_json_sha256_v1(evidence["role_occurrences"])
        or binding["row_axis_sha256"] != canonical_json_sha256_v1(evidence["row_axis"])
        or binding["column_context_sha256"] != canonical_json_sha256_v1(context)
        or context["family_id"] != receipt["family_id"]
        or context["row_axis_id"] != evidence["row_axis"]["row_axis_id"]
    ):
        raise _error("one-edit parent-frontier structural input binding drifted")

    parent = proof["parent_match_binding"]
    page_sequence = parent["page_sequence"]
    grids = [
        grid
        for grid in evidence["row_axis"]["column_grids"]
        if grid["page_sequence"] == page_sequence
    ]
    if len(grids) != 1:
        raise _error("one-edit parent-frontier physical page grid is not unique")
    centers = grids[0]["column_centers"]
    lane_count = len(centers)
    if (
        lane_count == 0
        or [item["column_center"] for item in context["period_axis"]] != centers
        or [item["column_center"] for item in context["unit_axis"]] != centers
        or len(parent["numbers"]) != lane_count
    ):
        raise _error("one-edit parent-frontier complete column axis drifted")

    role_occurrences = evidence["role_occurrences"]
    occurrence_by_id = {
        occurrence.get("occurrence_id"): occurrence
        for occurrence in role_occurrences
        if type(occurrence) is dict and type(occurrence.get("occurrence_id")) is str
    }
    rows = evidence["row_axis"]["rows"]
    rows_by_occurrence: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        occurrence_id = row.get("label_match", {}).get("occurrence_id")
        if type(occurrence_id) is str:
            rows_by_occurrence.setdefault(occurrence_id, []).append(row)
    if len(occurrence_by_id) != len(role_occurrences):
        raise _error("one-edit parent-frontier role occurrence identity repeats")

    equation = proof["source_scope_binding"]["geometry"]["equation"]
    component_ids = []
    component_receipts = []
    component_keys = []
    component_sample_ids: list[str] = []
    for persisted, equation_component in zip(
        proof["component_frontier_bindings"],
        equation["component_frontier"],
        strict=True,
    ):
        occurrence = occurrence_by_id.get(persisted["occurrence_id"])
        matching_rows = rows_by_occurrence.get(persisted["occurrence_id"], [])
        row = matching_rows[0] if len(matching_rows) == 1 else None
        label_match = occurrence.get("label_match", {}) if type(occurrence) is dict else {}
        explicit_indices = label_match.get("source_line_indices")
        source_start = label_match.get("source_line_index")
        source_stop = label_match.get("end_source_line_index")
        occurrence_source_line_indices = (
            explicit_indices
            if type(explicit_indices) is list
            else list(range(source_start, source_stop + 1))
            if type(source_start) is int
            and type(source_stop) is int
            and source_stop >= source_start
            else []
        )
        row_receipt = (
            occurrence_row_v2._direct_frontier_row_receipt(row)  # noqa: SLF001
            if type(row) is dict
            else None
        )
        if (
            type(occurrence) is not dict
            or canonical_json_sha256_v1(occurrence) != persisted["role_occurrence_sha256"]
            or occurrence.get("retrieval_occurrence_id")
            != equation_component["retrieval_occurrence_id"]
            or occurrence.get("role") != equation_component["role"]
            or label_match.get("retrieval_role") != persisted["retrieval_role"]
            or label_match.get("retrieval_within_role") != persisted["retrieval_within_role"]
            or occurrence_source_line_indices != persisted["source_line_indices"]
            or occurrence.get("scope_owner_occurrence_id") != proof["root_occurrence_id"]
            or occurrence.get("scope_owner_role") is not None
            or occurrence.get("has_bound_value_row") is not True
            or occurrence.get("label_match", {}).get("page_sequence") != page_sequence
            or not occurrence_row_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
                occurrence["label_match"]
            )
            or type(row) is not dict
            or canonical_json_sha256_v1(row) != persisted["row_sha256"]
            or not same_typed_json_v1(row_receipt, persisted["row_receipt"])
            or not same_typed_json_v1(
                row_receipt,
                {
                    "numbers": equation_component["numbers"],
                    "sample_ids": equation_component["sample_ids"],
                },
            )
            or [item.get("column_ordinal") for item in row["values"]] != list(range(lane_count))
            or [item.get("column_center") for item in row["values"]] != centers
        ):
            raise _error("one-edit parent-frontier component occurrence/row binding drifted")
        component_ids.append(occurrence["occurrence_id"])
        component_receipts.append(row_receipt)
        component_keys.append(occurrence_row_v2._visual_match_key(occurrence["label_match"]))  # noqa: SLF001
        component_sample_ids.extend(row_receipt["sample_ids"])
    if (
        component_keys != sorted(component_keys)
        or len(component_sample_ids) != len(set(component_sample_ids))
        or not occurrence_row_v2._direct_frontier_sum_is_exact(  # noqa: SLF001
            {"numbers": parent["numbers"]}, component_receipts
        )
    ):
        raise _error("one-edit parent-frontier component order or arithmetic drifted")

    target = occurrence_by_id.get(proof["target_occurrence_id"])
    target_label_match = canonical_clone_v1(target["label_match"]) if type(target) is dict else None
    if type(target_label_match) is dict:
        target_label_match.pop("source_scope_binding", None)
    if (
        type(target) is not dict
        or not same_typed_json_v1(target_label_match, proof["target_label_match"])
        or not same_typed_json_v1(target["source_scope_binding"], proof["source_scope_binding"])
    ):
        raise _error("one-edit parent-frontier target equation occurrence drifted")
    direct_frontier = _replay_recursive_parent_direct_frontier_v1(
        role_occurrences,
        rows,
        equation,
        page_sequence=page_sequence,
        root_occurrence_id=proof["root_occurrence_id"],
        target_role=proof["target_role"],
    )
    if (
        direct_frontier is None
        or [row["label_match"]["occurrence_id"] for _role, row in direct_frontier] != component_ids
    ):
        raise _error("one-edit parent-frontier is partial, mixed, or non-direct")

    sample_by_id = {
        sample.get("sample_id"): sample
        for sample in evidence["numeric_sample_universe"]
        if type(sample) is dict and type(sample.get("sample_id")) is str
    }
    if len(sample_by_id) != len(evidence["numeric_sample_universe"]):
        raise _error("one-edit parent-frontier numeric sample identity repeats")
    result_records = [sample_by_id.get(item) for item in parent["result_sample_ids"]]
    result_numbers = [
        occurrence_row_v2._direct_frontier_number(record)  # noqa: SLF001
        if type(record) is dict
        else None
        for record in result_records
    ]
    if (
        any(type(record) is not dict for record in result_records)
        or result_numbers != parent["numbers"]
        or any(record["page_sequence"] != page_sequence for record in result_records)
        or [record["column_ordinal"] for record in result_records] != list(range(lane_count))
        or [record["column_center"] for record in result_records] != centers
        or set(parent["result_sample_ids"]) & set(component_sample_ids)
    ):
        raise _error("one-edit parent-frontier result sample axis drifted")
    result_sample_ids = set(parent["result_sample_ids"])
    result_clusters = [
        cluster
        for cluster in evidence["internal_unassigned_numeric_clusters"]
        if type(cluster) is dict and set(cluster.get("sample_ids", [])) & result_sample_ids
    ]
    if (
        len(result_clusters) != 1
        or set(result_clusters[0].get("sample_ids", [])) != result_sample_ids
        or result_clusters[0].get("page_sequence") != page_sequence
        or result_clusters[0].get("status") != occurrence_row_v2._INTERNAL_UNASSIGNED_CLUSTER_STATUS  # noqa: SLF001
        or result_clusters[0].get("label_lane_status")
        != occurrence_row_v2._LABELED_LABEL_LANE_STATUS  # noqa: SLF001
        or len(result_clusters[0].get("same_row_label_evidence", [])) != 1
        or result_clusters[0]["same_row_label_evidence"][0].get("bbox") != parent["label_bbox"]
        or result_clusters[0]["same_row_label_evidence"][0].get("line_ordinal")
        not in parent["source_line_indices"]
        or any(
            record.get("owner_kind") != "SOURCE_ONLY_INTERNAL_CLUSTER"
            or record.get("owner_id") != result_clusters[0].get("cluster_id")
            for record in result_records
        )
    ):
        raise _error("one-edit parent-frontier physical parent cluster drifted")
    return receipt


def _validate_parent_frontier_against_closure_axes_v1(
    value: Any,
    *,
    internal_unassigned_numeric_clusters: Any,
    numeric_sample_universe: Any,
    role_occurrences: Any,
) -> dict[str, Any]:
    """Rebind the sealed frontier to the exact axes persisted by closure.

    Closure does not persist a second copy of the row axis.  It does retain
    every occurrence, numeric sample, and internal cluster.  Those axes are
    sufficient to authenticate the component identities/order, their printed
    numbers, and the physical parent-result cluster; public replay remains the
    stronger source-page check.
    """

    receipt = _validate_parent_frontier_result_v1(value)
    if any(
        type(axis) is not list
        for axis in (
            internal_unassigned_numeric_clusters,
            numeric_sample_universe,
            role_occurrences,
        )
    ):
        raise _error("one-edit parent-frontier closure axis drifted")
    binding = receipt["input_binding"]
    if (
        binding["internal_unassigned_numeric_clusters_sha256"]
        != canonical_json_sha256_v1(internal_unassigned_numeric_clusters)
        or binding["numeric_sample_universe_sha256"]
        != canonical_json_sha256_v1(numeric_sample_universe)
        or binding["role_occurrences_sha256"] != canonical_json_sha256_v1(role_occurrences)
    ):
        raise _error("one-edit parent-frontier closure input binding drifted")

    proof = receipt["parent_frontier_authority"]
    equation = proof["source_scope_binding"]["geometry"]["equation"]
    parent = proof["parent_match_binding"]
    page_sequence = parent["page_sequence"]
    context = proof["column_context_receipt"]
    centers = [item["column_center"] for item in context["period_axis"]]
    lane_count = len(centers)
    occurrence_by_id = {
        occurrence.get("occurrence_id"): occurrence
        for occurrence in role_occurrences
        if type(occurrence) is dict and type(occurrence.get("occurrence_id")) is str
    }
    sample_by_id = {
        sample.get("sample_id"): sample
        for sample in numeric_sample_universe
        if type(sample) is dict and type(sample.get("sample_id")) is str
    }
    if (
        len(occurrence_by_id) != len(role_occurrences)
        or len(sample_by_id) != len(numeric_sample_universe)
        or lane_count == 0
        or [item["column_center"] for item in context["unit_axis"]] != centers
    ):
        raise _error("one-edit parent-frontier closure identity axis repeats")

    component_ids: list[str] = []
    component_keys: list[tuple[Any, ...]] = []
    component_receipts: list[dict[str, Any]] = []
    component_sample_ids: list[str] = []
    for persisted, equation_component in zip(
        proof["component_frontier_bindings"],
        equation["component_frontier"],
        strict=True,
    ):
        occurrence = occurrence_by_id.get(persisted["occurrence_id"])
        label_match = occurrence.get("label_match", {}) if type(occurrence) is dict else {}
        explicit_indices = label_match.get("source_line_indices")
        source_start = label_match.get("source_line_index")
        source_stop = label_match.get("end_source_line_index")
        source_line_indices = (
            explicit_indices
            if type(explicit_indices) is list
            else list(range(source_start, source_stop + 1))
            if type(source_start) is int
            and type(source_stop) is int
            and source_stop >= source_start
            else []
        )
        row_receipt = persisted["row_receipt"]
        records = [sample_by_id.get(sample_id) for sample_id in row_receipt["sample_ids"]]
        numbers = [
            occurrence_row_v2._direct_frontier_number(record)  # noqa: SLF001
            if type(record) is dict
            else None
            for record in records
        ]
        if (
            type(occurrence) is not dict
            or canonical_json_sha256_v1(occurrence) != persisted["role_occurrence_sha256"]
            or occurrence.get("retrieval_occurrence_id")
            != equation_component["retrieval_occurrence_id"]
            or occurrence.get("role") != equation_component["role"]
            or label_match.get("retrieval_role") != persisted["retrieval_role"]
            or label_match.get("retrieval_within_role") != persisted["retrieval_within_role"]
            or source_line_indices != persisted["source_line_indices"]
            or occurrence.get("scope_owner_occurrence_id") != proof["root_occurrence_id"]
            or occurrence.get("scope_owner_role") is not None
            or occurrence.get("has_bound_value_row") is not True
            or label_match.get("page_sequence") != page_sequence
            or not occurrence_row_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
                label_match
            )
            or len(records) != lane_count
            or any(type(record) is not dict for record in records)
            or numbers != row_receipt["numbers"]
            or not same_typed_json_v1(
                row_receipt,
                {
                    "numbers": equation_component["numbers"],
                    "sample_ids": equation_component["sample_ids"],
                },
            )
            or any(
                record.get("owner_kind") != "ROLE_OCCURRENCE"
                or record.get("owner_id") != persisted["occurrence_id"]
                or record.get("page_sequence") != page_sequence
                for record in records
            )
            or [record.get("column_ordinal") for record in records] != list(range(lane_count))
            or [record.get("column_center") for record in records] != centers
        ):
            raise _error("one-edit parent-frontier closure component binding drifted")
        component_ids.append(persisted["occurrence_id"])
        component_keys.append(occurrence_row_v2._visual_match_key(label_match))  # noqa: SLF001
        component_receipts.append(row_receipt)
        component_sample_ids.extend(row_receipt["sample_ids"])
    if (
        component_keys != sorted(component_keys)
        or len(component_sample_ids) != len(set(component_sample_ids))
        or not occurrence_row_v2._direct_frontier_sum_is_exact(  # noqa: SLF001
            {"numbers": parent["numbers"]}, component_receipts
        )
    ):
        raise _error("one-edit parent-frontier closure component axis drifted")

    target = occurrence_by_id.get(proof["target_occurrence_id"])
    target_label_match = canonical_clone_v1(target["label_match"]) if type(target) is dict else None
    if type(target_label_match) is dict:
        target_label_match.pop("source_scope_binding", None)
    closure_rows = []
    for occurrence in role_occurrences:
        if occurrence.get("has_bound_value_row") is not True:
            continue
        occurrence_id = occurrence["occurrence_id"]
        records = sorted(
            (
                sample
                for sample in numeric_sample_universe
                if sample.get("owner_kind") == "ROLE_OCCURRENCE"
                and sample.get("owner_id") == occurrence_id
            ),
            key=lambda sample: (sample.get("column_ordinal", -1), sample.get("sample_id", "")),
        )
        complete = len(records) == lane_count and [
            record.get("column_ordinal") for record in records
        ] == list(range(lane_count))
        closure_rows.append(
            {
                "label_match": canonical_clone_v1(occurrence["label_match"]),
                "status": "VISIBLE_VALUE_LANES_BOUND" if complete else "PARTIAL",
                "values": canonical_clone_v1(records),
            }
        )
    direct_frontier = _replay_recursive_parent_direct_frontier_v1(
        role_occurrences,
        closure_rows,
        equation,
        page_sequence=page_sequence,
        root_occurrence_id=proof["root_occurrence_id"],
        target_role=proof["target_role"],
    )
    if (
        type(target) is not dict
        or not same_typed_json_v1(target_label_match, proof["target_label_match"])
        or not same_typed_json_v1(target["source_scope_binding"], proof["source_scope_binding"])
        or direct_frontier is None
        or [row["label_match"]["occurrence_id"] for _role, row in direct_frontier] != component_ids
    ):
        raise _error("one-edit parent-frontier closure direct frontier drifted")

    result_records = [sample_by_id.get(sample_id) for sample_id in parent["result_sample_ids"]]
    result_numbers = [
        occurrence_row_v2._direct_frontier_number(record)  # noqa: SLF001
        if type(record) is dict
        else None
        for record in result_records
    ]
    result_sample_ids = set(parent["result_sample_ids"])
    result_clusters = [
        cluster
        for cluster in internal_unassigned_numeric_clusters
        if type(cluster) is dict and set(cluster.get("sample_ids", [])) & result_sample_ids
    ]
    if (
        len(result_records) != lane_count
        or any(type(record) is not dict for record in result_records)
        or result_numbers != parent["numbers"]
        or [record.get("column_ordinal") for record in result_records] != list(range(lane_count))
        or [record.get("column_center") for record in result_records] != centers
        or set(component_sample_ids) & result_sample_ids
        or len(result_clusters) != 1
        or set(result_clusters[0].get("sample_ids", [])) != result_sample_ids
        or result_clusters[0].get("page_sequence") != page_sequence
        or result_clusters[0].get("status") != occurrence_row_v2._INTERNAL_UNASSIGNED_CLUSTER_STATUS  # noqa: SLF001
        or result_clusters[0].get("label_lane_status")
        != occurrence_row_v2._LABELED_LABEL_LANE_STATUS  # noqa: SLF001
        or len(result_clusters[0].get("same_row_label_evidence", [])) != 1
        or result_clusters[0]["same_row_label_evidence"][0].get("bbox") != parent["label_bbox"]
        or result_clusters[0]["same_row_label_evidence"][0].get("line_ordinal")
        not in parent["source_line_indices"]
        or any(
            record.get("owner_kind") != "SOURCE_ONLY_INTERNAL_CLUSTER"
            or record.get("owner_id") != result_clusters[0].get("cluster_id")
            or record.get("page_sequence") != page_sequence
            for record in result_records
        )
    ):
        raise _error("one-edit parent-frontier closure parent cluster drifted")
    return canonical_clone_v1(result_clusters[0])


def family_parent_exact_frontier_result_cluster_v1(
    value: Any,
    *,
    structural_evidence: Any,
) -> dict[str, Any] | None:
    """Return the sole replayed physical parent-result cluster for V3."""

    receipt = validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(value)
    if receipt["format_version"] != PARENT_FRONTIER_FORMAT_VERSION:
        return hierarchy_frontier_result_cluster_v1(
            receipt,
            structural_evidence=structural_evidence,
        )
    evidence = _parent_frontier_structural_evidence_v1(structural_evidence)
    _validate_parent_frontier_against_structural_evidence_v1(receipt, evidence)
    return _validate_parent_frontier_against_closure_axes_v1(
        receipt,
        internal_unassigned_numeric_clusters=evidence["internal_unassigned_numeric_clusters"],
        numeric_sample_universe=evidence["numeric_sample_universe"],
        role_occurrences=evidence["role_occurrences"],
    )


def _build_parent_frontier_proof_v1(
    source_receipt: Mapping[str, Any],
    evidence: Mapping[str, Any],
    column_context: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    compiled: Mapping[str, Any],
    selected_region: Mapping[str, Any],
    input_binding: Mapping[str, str],
) -> dict[str, Any] | None:
    unbound_checks = [
        check for check in source_receipt["checks"] if check["status"] not in _BOUND_CHECK_STATUSES
    ]
    if (
        len(unbound_checks) != 1
        or unbound_checks[0]["match_scope"] != "FAMILY_PARENT"
        or selected_region.get("parent_match") is None
        or not _is_one_edit(selected_region["parent_match"])
    ):
        return None
    source_check = unbound_checks[0]
    parent_match = canonical_clone_v1(selected_region["parent_match"])
    if (
        source_check["role"] != compiled["parent"]["role"]
        or source_check["page_sequence"] != parent_match["page_sequence"]
        or source_check["source_line_indices"] != list(_match_line_indices(parent_match, pages))
    ):
        return None
    occurrence_pages = _occurrence_row_pages_v1(pages)
    parent_match["source_label_bbox"] = occurrence_row_v2._source_line_bbox(  # noqa: SLF001
        occurrence_pages, parent_match
    )
    row_axis = evidence["row_axis"]
    parent_result = occurrence_row_v2._direct_frontier_parent_row_receipt(  # noqa: SLF001
        occurrence_pages,
        parent_match,
        row_axis,
    )
    if parent_result is None:
        return None
    root_occurrence_id = _root_scope_id_v1(selected_region)
    role_occurrences = evidence["role_occurrences"]
    candidates = []
    for occurrence in role_occurrences:
        binding = occurrence.get("source_scope_binding")
        geometry = binding.get("geometry") if type(binding) is dict else None
        equation = geometry.get("equation") if type(geometry) is dict else None
        if (
            type(binding) is dict
            and binding.get("binding_kind")
            == occurrence_row_v2._RECURSIVE_PARENT_PROVISION_BINDING_KIND  # noqa: SLF001
            and type(equation) is dict
            and equation.get("parent_role") == compiled["family_id"]
            and equation.get("parent_occurrence_id") == root_occurrence_id
            and equation.get("result", {}).get("role") == compiled["family_id"]
            and equation.get("result", {}).get("occurrence_id") == root_occurrence_id
            and occurrence.get("scope_owner_occurrence_id") == root_occurrence_id
            and occurrence.get("scope_owner_role") is None
        ):
            candidates.append((occurrence, binding, equation))
    if len(candidates) != 1:
        return None
    target, source_scope_binding, equation = candidates[0]
    target_label_match = canonical_clone_v1(target["label_match"])
    target_label_match.pop("source_scope_binding", None)
    try:
        if not occurrence_row_v2._recursive_parent_provision_geometry_is_valid(  # noqa: SLF001
            source_scope_binding["geometry"],
            label_match=target_label_match,
            role=target["role"],
        ):
            return None
    except (KeyError, TypeError):
        return None
    if (
        target_label_match.get("page_sequence") != parent_match["page_sequence"]
        or equation["result"].get("sample_ids") != parent_result["sample_ids"]
        or equation["result"].get("numbers") != parent_result["numbers"]
    ):
        return None
    occurrences_by_retrieval: dict[str, list[Mapping[str, Any]]] = {}
    for occurrence in role_occurrences:
        retrieval_id = occurrence.get("retrieval_occurrence_id")
        if type(retrieval_id) is str:
            occurrences_by_retrieval.setdefault(retrieval_id, []).append(occurrence)
    rows_by_occurrence: dict[str, list[Mapping[str, Any]]] = {}
    for row in row_axis["rows"]:
        occurrence_id = row.get("label_match", {}).get("occurrence_id")
        if type(occurrence_id) is str:
            rows_by_occurrence.setdefault(occurrence_id, []).append(row)
    component_occurrences = []
    component_rows = []
    component_receipts = []
    for component in equation["component_frontier"]:
        matching_occurrences = [
            occurrence
            for occurrence in occurrences_by_retrieval.get(component["retrieval_occurrence_id"], [])
            if occurrence.get("role") == component["role"]
        ]
        if len(matching_occurrences) != 1:
            return None
        occurrence = matching_occurrences[0]
        matching_rows = rows_by_occurrence.get(occurrence["occurrence_id"], [])
        if (
            len(matching_rows) != 1
            or occurrence.get("scope_owner_occurrence_id") != root_occurrence_id
            or occurrence.get("scope_owner_role") is not None
            or occurrence.get("has_bound_value_row") is not True
            or occurrence["label_match"].get("page_sequence") != parent_match["page_sequence"]
            or not occurrence_row_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
                occurrence["label_match"]
            )
        ):
            return None
        receipt = occurrence_row_v2._direct_frontier_row_receipt(  # noqa: SLF001
            matching_rows[0]
        )
        if (
            receipt is None
            or receipt["numbers"] != component["numbers"]
            or receipt["sample_ids"] != component["sample_ids"]
        ):
            return None
        component_occurrences.append(occurrence)
        component_rows.append(matching_rows[0])
        component_receipts.append(receipt)
    component_ids = [occurrence["occurrence_id"] for occurrence in component_occurrences]
    if len(component_ids) != len(
        set(component_ids)
    ) or not occurrence_row_v2._direct_frontier_sum_is_exact(  # noqa: SLF001
        parent_result, component_receipts
    ):
        return None
    direct_frontier = _replay_recursive_parent_direct_frontier_v1(
        role_occurrences,
        row_axis["rows"],
        equation,
        page_sequence=parent_match["page_sequence"],
        root_occurrence_id=root_occurrence_id,
        target_role=target["role"],
    )
    if (
        direct_frontier is None
        or [row["label_match"]["occurrence_id"] for _role, row in direct_frontier] != component_ids
    ):
        return None
    result_samples = set(parent_result["sample_ids"])
    component_samples = {
        sample_id for receipt in component_receipts for sample_id in receipt["sample_ids"]
    }
    if result_samples & component_samples:
        return None
    sample_by_id = {
        sample.get("sample_id"): sample
        for sample in evidence["numeric_sample_universe"]
        if type(sample) is dict and type(sample.get("sample_id")) is str
    }
    result_records = [sample_by_id.get(sample_id) for sample_id in parent_result["sample_ids"]]
    if any(type(record) is not dict for record in result_records):
        return None
    result_numbers = [
        occurrence_row_v2._direct_frontier_number(record)  # noqa: SLF001
        for record in result_records
    ]
    if (
        any(number is None for number in result_numbers)
        or result_numbers != parent_result["numbers"]
        or any(
            record.get("page_sequence") != parent_match["page_sequence"]
            for record in result_records
        )
    ):
        return None
    result_clusters = [
        cluster
        for cluster in evidence["internal_unassigned_numeric_clusters"]
        if type(cluster) is dict and set(cluster.get("sample_ids", [])) & result_samples
    ]
    if (
        len(result_clusters) != 1
        or set(result_clusters[0].get("sample_ids", [])) != result_samples
        or any(
            type(cluster) is dict
            and cluster is not result_clusters[0]
            and cluster.get("page_sequence") == parent_match["page_sequence"]
            for cluster in evidence["internal_unassigned_numeric_clusters"]
        )
    ):
        return None
    grids = [
        grid
        for grid in row_axis["column_grids"]
        if grid["page_sequence"] == parent_match["page_sequence"]
    ]
    if len(grids) != 1:
        return None
    centers = grids[0]["column_centers"]
    lane_count = len(centers)
    period_axis = sorted(column_context["period_axis"], key=lambda item: item["column_ordinal"])
    unit_axis = sorted(column_context["unit_axis"], key=lambda item: item["column_ordinal"])
    if (
        column_context["status"] != "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
        or column_context["row_axis_id"] != row_axis["row_axis_id"]
        or len(parent_result["numbers"]) != lane_count
        or [item.get("column_ordinal") for item in period_axis] != list(range(lane_count))
        or [item.get("column_ordinal") for item in unit_axis] != list(range(lane_count))
        or any(
            type(item.get("resolved_period")) is not str or not item["resolved_period"]
            for item in period_axis
        )
        or any(
            item.get("column_center") != centers[index] for index, item in enumerate(period_axis)
        )
        or any(item.get("column_center") != centers[index] for index, item in enumerate(unit_axis))
        or len(
            {
                (item.get("unit_kind"), item.get("currency"), item.get("magnitude_power10"))
                for item in unit_axis
            }
        )
        != 1
    ):
        return None
    parent_bbox = parent_match["source_label_bbox"]
    parent_binding = {
        "document_line_span": [
            parent_match["document_line_ordinal"],
            parent_match["end_document_line_ordinal"],
        ],
        "label_bbox": canonical_clone_v1(parent_bbox),
        "numbers": canonical_clone_v1(parent_result["numbers"]),
        "page_sequence": parent_match["page_sequence"],
        "result_sample_ids": canonical_clone_v1(parent_result["sample_ids"]),
        "source_line_indices": canonical_clone_v1(source_check["source_line_indices"]),
    }
    component_bindings = [
        {
            "component_ordinal": ordinal,
            "equation_component": canonical_clone_v1(equation_component),
            "occurrence_id": occurrence["occurrence_id"],
            "role_occurrence_sha256": canonical_json_sha256_v1(occurrence),
            "row_receipt": canonical_clone_v1(receipt),
            "row_sha256": canonical_json_sha256_v1(row),
            "retrieval_role": occurrence["label_match"]["retrieval_role"],
            "retrieval_within_role": occurrence["label_match"]["retrieval_within_role"],
            "source_line_indices": list(_match_line_indices(occurrence["label_match"], pages)),
        }
        for ordinal, (equation_component, occurrence, row, receipt) in enumerate(
            zip(
                equation["component_frontier"],
                component_occurrences,
                component_rows,
                component_receipts,
                strict=True,
            )
        )
    ]
    material = {
        "column_context_receipt": canonical_clone_v1(column_context),
        "component_frontier_bindings": component_bindings,
        "format_version": _PARENT_FRONTIER_PROOF_FORMAT_VERSION,
        "input_binding": canonical_clone_v1(input_binding),
        "parent_match_binding": parent_binding,
        "root_occurrence_id": root_occurrence_id,
        "source_check": canonical_clone_v1(source_check),
        "source_scope_binding": canonical_clone_v1(source_scope_binding),
        "status": _PARENT_FRONTIER_BOUND_STATUS,
        "target_label_match": target_label_match,
        "target_occurrence_id": target["occurrence_id"],
        "target_role": target["role"],
    }
    return _validate_parent_frontier_proof_shape_v1(
        {
            **material,
            "proof_id": "afeoepfav1:proof:" + canonical_json_sha256_v1(material),
        }
    )


def project_accounting_family_one_edit_parent_frontier_authority_v1(
    source_exact_authority_receipt: Any,
    structural_evidence: Any,
    column_context: Any,
    document_pages: Any,
    family_spec: Any,
    selected_topology_region: Any,
    *,
    column_context_document_pages: Any,
    period_semantics: Any,
    expected_lane_unit_kinds: Any,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Promote only one exact, exhaustive family-parent direct frontier.

    This adapter never changes a source token or chooses among numeric
    assignments.  It consumes the already authenticated row/occurrence axis,
    one resolved period/unit column axis, and the recursive direct-frontier
    equation emitted for a physical source occurrence.  Every ordinary V2
    receipt is returned byte-for-byte when those gates do not close uniquely.
    """

    source = _validate_result(source_exact_authority_receipt)
    evidence = _parent_frontier_structural_evidence_v1(structural_evidence)
    try:
        context = column_context_multilevel_v2._validate_context_receipt_v2(  # noqa: SLF001
            column_context
        )
        pages = _pages_with_occurrence_geometry_v1(document_pages)
        compiled = topology_v1._spec(family_spec)  # noqa: SLF001
    except (ValueError, RuntimeError) as exc:
        raise _error("one-edit parent-frontier authenticated input drifted") from exc
    if (
        type(selected_topology_region) is not dict
        or source["family_id"] != compiled["family_id"]
        or evidence["row_axis"]["family_id"] != compiled["family_id"]
        or context["family_id"] != compiled["family_id"]
        or source["input_binding"]["document_pages_sha256"]
        != canonical_json_sha256_v1(document_pages)
        or source["input_binding"]["family_spec_sha256"] != canonical_json_sha256_v1(family_spec)
        or source["input_binding"]["selected_topology_region_sha256"]
        != canonical_json_sha256_v1(selected_topology_region)
    ):
        raise _error("one-edit parent-frontier family/source binding drifted")
    context = _validate_parent_frontier_column_context_replay_v1(
        context,
        row_axis=evidence["row_axis"],
        document_pages=column_context_document_pages,
        authority_pages=document_pages,
        family_spec=family_spec,
        period_semantics=period_semantics,
        expected_lane_unit_kinds=expected_lane_unit_kinds,
        visible_dash_rescues=visible_dash_rescues,
    )
    input_binding = _parent_frontier_input_binding_v1(source, evidence, context)
    proof = _build_parent_frontier_proof_v1(
        source,
        evidence,
        context,
        pages,
        compiled,
        selected_topology_region,
        input_binding,
    )
    if proof is None:
        return canonical_clone_v1(source)
    source_reason = _parent_frontier_reason(proof["source_check"])
    reasons = [reason for reason in source["unresolved_reasons"] if reason != source_reason]
    metrics = {
        "exact_bound_count": source["metrics"]["exact_bound_count"] + 1,
        "selected_one_edit_match_count": source["metrics"]["selected_one_edit_match_count"],
        "unresolved_match_count": source["metrics"]["unresolved_match_count"] - 1,
    }
    material = {
        "authority_spec": {
            "sha256": canonical_json_sha256_v1(_PARENT_FRONTIER_AUTHORITY_SPEC),
            "value": canonical_clone_v1(_PARENT_FRONTIER_AUTHORITY_SPEC),
        },
        "checks": canonical_clone_v1(source["checks"]),
        "claim_boundary": PARENT_FRONTIER_CLAIM_BOUNDARY,
        "family_id": compiled["family_id"],
        "format_version": PARENT_FRONTIER_FORMAT_VERSION,
        "input_binding": input_binding,
        "metrics": metrics,
        "parent_frontier_authority": proof,
        "safety": canonical_clone_v1(_PARENT_FRONTIER_SAFETY),
        "source_exact_authority_receipt": canonical_clone_v1(source),
        "status": (
            "EXACT_SOURCE_AUTHORITY_BOUND"
            if not reasons
            else "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY"
        ),
        "unresolved_reasons": reasons,
    }
    persisted = {
        **material,
        "receipt_id": "afeoeav1:receipt:" + canonical_json_sha256_v1(material),
    }
    return _validate_parent_frontier_against_structural_evidence_v1(
        persisted,
        evidence,
    )


def _hierarchy_frontier_input_binding_v1(
    source_receipt: Mapping[str, Any],
    evidence: Mapping[str, Any],
    column_context: Mapping[str, Any],
    hierarchy_spec: Any,
    column_policy: Mapping[str, Any],
) -> dict[str, str]:
    return {
        **_parent_frontier_input_binding_v1(source_receipt, evidence, column_context),
        "hierarchy_spec_sha256": canonical_json_sha256_v1(hierarchy_spec),
        "column_policy_sha256": canonical_json_sha256_v1(column_policy),
    }


def _recursive_hierarchy_frontier_input_binding_v1(
    source_receipt: Mapping[str, Any],
    evidence: Mapping[str, Any],
    column_context: Mapping[str, Any],
    hierarchy_spec: Any,
    column_policy: Mapping[str, Any],
) -> dict[str, str]:
    return {
        **_hierarchy_frontier_input_binding_v1(
            source_receipt,
            evidence,
            column_context,
            hierarchy_spec,
            column_policy,
        ),
        "authenticated_extreme_margin_furniture_evidence_sha256": canonical_json_sha256_v1(
            evidence["authenticated_extreme_margin_furniture_evidence"]
        ),
    }


def _hierarchy_frontier_number(value: Mapping[str, Any]) -> dict[str, Any] | None:
    return occurrence_row_v2._direct_frontier_number(value)  # noqa: SLF001


def _hierarchy_frontier_source_line_indices(match: Mapping[str, Any]) -> list[int]:
    explicit = match.get("source_line_indices")
    if type(explicit) is list:
        return canonical_clone_v1(explicit)
    start = match.get("source_line_index")
    stop = match.get("end_source_line_index")
    if type(start) is int and type(stop) is int and stop >= start:
        return list(range(start, stop + 1))
    return []


def _hierarchy_frontier_row_receipt_v1(row: Mapping[str, Any]) -> dict[str, Any] | None:
    return occurrence_row_v2._direct_frontier_row_receipt(row)  # noqa: SLF001


def _hierarchy_frontier_cell_certificate_v1(
    sample: Mapping[str, Any],
    *,
    node_kind: str,
    node_ordinal: int,
    role: str,
    page_line_by_sample: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    sample_id = sample.get("sample_id")
    line = page_line_by_sample.get(sample_id) if type(sample_id) is str else None
    parsed = sample.get("parsed_token")
    number = _hierarchy_frontier_number(sample)
    if (
        type(line) is not dict
        or type(parsed) is not dict
        or number is None
        or line.get("sample_id") != sample_id
        or line.get("source_line_index") != sample.get("line_ordinal")
        or line.get("bbox") != sample.get("bbox")
        or line.get("numeric_recognition", {}).get("raw_prediction") != sample.get("raw_prediction")
        or type(line.get("vietocr_text")) is not str
    ):
        return None
    try:
        crop_ref = _crop_reference(line.get("crop_ref"))
    except AccountingFamilyOneEditExactAuthorityV1Error:
        return None
    classification = parsed.get("classification")
    vietocr_surface = line["vietocr_text"]
    vietocr_parsed = parse_visible_financial_numeric_token_v1(vietocr_surface)
    vietocr_number = None
    if classification == "SIGNED_NUMBER":
        certificate_kind = "RAW_SIGNED_SOURCE_VISIBLE"
    elif classification == "MIXED_GROUPED_INTEGER_CANDIDATE":
        if (
            vietocr_parsed.get("classification") != "SIGNED_NUMBER"
            or vietocr_parsed.get("coefficient") != number["coefficient"]
            or vietocr_parsed.get("scale") != number["scale"]
            or vietocr_parsed.get("percentage_mark_present")
            is not number["percentage_mark_present"]
            or number["scale"] != 0
            or number["percentage_mark_present"] is not False
        ):
            return None
        certificate_kind = "MIXED_SAME_CROP_EXACT_INTEGER"
        vietocr_number = canonical_clone_v1(number)
    else:
        return None
    return {
        "bbox": canonical_clone_v1(sample["bbox"]),
        "certificate_kind": certificate_kind,
        "column_ordinal": sample["column_ordinal"],
        "crop_ref": crop_ref,
        "node_kind": node_kind,
        "node_ordinal": node_ordinal,
        "number": canonical_clone_v1(number),
        "numeric_sample_sha256": canonical_json_sha256_v1(sample),
        "page_line_sha256": canonical_json_sha256_v1(line),
        "page_sequence": sample["page_sequence"],
        "pp_classification": classification,
        "pp_surface": sample["raw_prediction"],
        "role": role,
        "sample_id": sample_id,
        "source_line_index": sample["line_ordinal"],
        "vietocr_number": vietocr_number,
        "vietocr_surface": vietocr_surface,
    }


def _hierarchy_frontier_page_line_from_sample_v1(
    sample: Mapping[str, Any],
    vietocr_surface: str,
) -> dict[str, Any]:
    """Rebuild the exact authority-page line committed by a V4 cell certificate."""

    return {
        "bbox": canonical_clone_v1(sample["bbox"]),
        "crop_ref": canonical_clone_v1(sample["crop_ref"]),
        "normalized_text": normalize_vietnamese_anchor_v1(vietocr_surface),
        "numeric_recognition": {
            "raw_prediction": sample["raw_prediction"],
            "reader_score": sample["reader_score"],
        },
        "sample_id": sample["sample_id"],
        "source_line_index": sample["line_ordinal"],
        "source_text": sample["raw_prediction"],
        "vietocr_text": vietocr_surface,
    }


def _compiled_hierarchy_frontier_equation_v1(
    hierarchy_spec: Any,
    family_spec: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    # Lazy import avoids a module-import cycle: scoped closure imports this
    # authority module, while this public projector reuses closure's sole
    # hierarchy compiler instead of introducing a private parser.
    from bctc_ai.evaluation import (  # noqa: PLC0415
        accounting_scoped_hierarchical_table_closure_v2 as closure_v2,
    )

    try:
        compiled = closure_v2._spec(hierarchy_spec, family_spec)  # noqa: SLF001
    except closure_v2.AccountingScopedHierarchicalTableClosureV2Error as exc:
        raise _error("one-edit hierarchy-frontier hierarchy spec drifted") from exc
    roots = [
        equation
        for equation in compiled["equations"]
        if equation["result_role"] == compiled["family_id"]
    ]
    if len(roots) != 1:
        raise _error("one-edit hierarchy-frontier root equation is not unique")
    return compiled, roots[0]


def _build_hierarchy_frontier_proof_v1(
    source_receipt: Mapping[str, Any],
    evidence: Mapping[str, Any],
    context: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    compiled_family: Mapping[str, Any],
    family_spec: Any,
    selected_region: Mapping[str, Any],
    hierarchy_spec: Any,
    input_binding: Mapping[str, str],
) -> dict[str, Any] | None:
    if len(source_receipt["checks"]) != 1:
        return None
    source_check = source_receipt["checks"][0]
    retrieval = source_check.get("retrieval_channel")
    if (
        source_check["status"] != "NO_EXACT_DECLARED_ALIAS_ON_RETRIEVAL_SOURCE_SPAN"
        or type(retrieval) is not dict
        or retrieval.get("match_kind") != "ONE_EDIT_ALIAS_REQUIRES_COMPLETE_TOPOLOGY"
        or type(retrieval.get("alias_candidates")) is not list
        or len(retrieval["alias_candidates"]) != 1
    ):
        return None
    target_kind = (
        "FAMILY_PARENT"
        if source_check["match_scope"] == "FAMILY_PARENT"
        else "COMPONENT"
        if source_check["match_scope"] == "EXPANDED_OCCURRENCE"
        else None
    )
    if target_kind is None:
        return None
    parent_match = selected_region.get("parent_match")
    if type(parent_match) is not dict:
        return None
    root_occurrence_id = _root_scope_id_v1(selected_region)
    page_sequence = parent_match.get("page_sequence")
    if type(page_sequence) is not int or page_sequence <= 0:
        return None
    if target_kind == "FAMILY_PARENT":
        if (
            not _is_one_edit(parent_match)
            or source_check["occurrence_id"] is not None
            or source_check["role"] != compiled_family["parent"]["role"]
            or source_check["source_line_indices"] != list(_match_line_indices(parent_match, pages))
        ):
            return None
    elif _is_one_edit(parent_match):
        return None

    try:
        _compiled_hierarchy, equation = _compiled_hierarchy_frontier_equation_v1(
            hierarchy_spec,
            family_spec,
        )
    except AccountingFamilyOneEditExactAuthorityV1Error:
        return None
    component_role_universe = {
        role
        for alternative in equation["component_role_alternatives"]
        for role in alternative["component_roles"]
    }
    occurrence_by_id = {
        item.get("occurrence_id"): item
        for item in evidence["role_occurrences"]
        if type(item) is dict and type(item.get("occurrence_id")) is str
    }
    if len(occurrence_by_id) != len(evidence["role_occurrences"]):
        return None
    rows_by_occurrence: dict[str, list[Mapping[str, Any]]] = {}
    for row in evidence["row_axis"]["rows"]:
        occurrence_id = row.get("label_match", {}).get("occurrence_id")
        if type(occurrence_id) is str:
            rows_by_occurrence.setdefault(occurrence_id, []).append(row)
    direct_candidates = []
    extra_direct_rows = []
    for occurrence in evidence["role_occurrences"]:
        occurrence_id = occurrence["occurrence_id"]
        rows = rows_by_occurrence.get(occurrence_id, [])
        if (
            occurrence.get("scope_owner_occurrence_id") != root_occurrence_id
            or occurrence.get("scope_owner_role") is not None
            or occurrence.get("label_match", {}).get("page_sequence") != page_sequence
        ):
            continue
        role = occurrence["role"]
        inventory_role = role in component_role_universe or occurrence.get("role_kind") in {
            "ADDITIVE_CHILD",
            "STRUCTURAL_GROUP",
        }
        if inventory_role and (
            len(rows) != 1
            or rows[0].get("status") != "VISIBLE_VALUE_LANES_BOUND"
            or not rows[0].get("values")
        ):
            return None
        if role in equation["visible_result_roles"] and (
            len(rows) != 1
            or rows[0].get("status") != "VISIBLE_VALUE_LANES_BOUND"
            or not rows[0].get("values")
        ):
            return None
        if role in component_role_universe:
            direct_candidates.append((occurrence, rows[0]))
        elif role not in equation["visible_result_roles"] and any(
            row.get("values") for row in rows
        ):
            extra_direct_rows.append((occurrence, rows[0]))
    visual_candidates = sorted(
        direct_candidates,
        key=lambda item: occurrence_row_v2._visual_match_key(item[0]["label_match"]),  # noqa: SLF001
    )
    observed_roles = [item[0]["role"] for item in visual_candidates]
    selected_alternatives = [
        (ordinal, alternative)
        for ordinal, alternative in enumerate(equation["component_role_alternatives"])
        if len(observed_roles) == len(set(observed_roles))
        and len(alternative["component_roles"]) == len(observed_roles)
        and set(alternative["component_roles"]) == set(observed_roles)
        and alternative["coverage_policy"] == "EXHAUSTIVE_COMPONENT_SET"
        and alternative["derivation_policy"]
        == "ALLOW_DERIVATION_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"
    ]
    if len(selected_alternatives) != 1 or extra_direct_rows:
        return None
    alternative_ordinal, alternative = selected_alternatives[0]
    direct_by_role = {item[0]["role"]: item for item in visual_candidates}
    visual_ordinal_by_occurrence = {
        item[0]["occurrence_id"]: ordinal for ordinal, item in enumerate(visual_candidates)
    }
    direct_candidates = [direct_by_role[role] for role in alternative["component_roles"]]

    component_receipts = []
    for _occurrence, row in direct_candidates:
        receipt = _hierarchy_frontier_row_receipt_v1(row)
        if receipt is None:
            return None
        component_receipts.append(receipt)
    component_ids = [item[0]["occurrence_id"] for item in direct_candidates]
    if len(component_ids) != len(set(component_ids)):
        return None

    target_occurrence_id = None
    target_role = source_check["role"]
    if target_kind == "COMPONENT":
        targets = [
            occurrence
            for occurrence, _row in direct_candidates
            if occurrence["retrieval_occurrence_id"] == source_check["occurrence_id"]
            and occurrence["role"] == source_check["role"]
        ]
        if len(targets) != 1 or not _is_one_edit(targets[0]["label_match"]):
            return None
        target_occurrence_id = targets[0]["occurrence_id"]
        if source_check["source_line_indices"] != _hierarchy_frontier_source_line_indices(
            targets[0]["label_match"]
        ):
            return None
    for occurrence, _row in direct_candidates:
        if occurrence["occurrence_id"] == target_occurrence_id:
            continue
        if not occurrence_row_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
            occurrence["label_match"]
        ):
            return None

    lane_grids = [
        grid
        for grid in evidence["row_axis"]["column_grids"]
        if grid["page_sequence"] == page_sequence
    ]
    if len(lane_grids) != 1:
        return None
    centers = lane_grids[0]["column_centers"]
    lane_count = len(centers)
    if lane_count == 0:
        return None
    period_axis = sorted(context["period_axis"], key=lambda item: item["column_ordinal"])
    unit_axis = sorted(context["unit_axis"], key=lambda item: item["column_ordinal"])
    if (
        context["status"] != "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
        or context["row_axis_id"] != evidence["row_axis"]["row_axis_id"]
        or [item.get("column_ordinal") for item in period_axis] != list(range(lane_count))
        or [item.get("column_ordinal") for item in unit_axis] != list(range(lane_count))
        or [item.get("column_center") for item in period_axis] != centers
        or [item.get("column_center") for item in unit_axis] != centers
        or len(
            {
                (item.get("unit_kind"), item.get("currency"), item.get("magnitude_power10"))
                for item in unit_axis
            }
        )
        != 1
        or any(len(receipt["numbers"]) != lane_count for receipt in component_receipts)
    ):
        return None

    sample_by_id = {
        item.get("sample_id"): item
        for item in evidence["numeric_sample_universe"]
        if type(item) is dict and type(item.get("sample_id")) is str
    }
    page_line_by_sample = {
        line.get("sample_id"): line
        for page in pages
        for line in page["lines"]
        if type(line.get("sample_id")) is str
    }
    if len(sample_by_id) != len(evidence["numeric_sample_universe"]) or len(
        page_line_by_sample
    ) != sum(1 for page in pages for line in page["lines"] if type(line.get("sample_id")) is str):
        return None

    role_result_candidates = []
    for occurrence in evidence["role_occurrences"]:
        rows = rows_by_occurrence.get(occurrence["occurrence_id"], [])
        if (
            occurrence["role"] in equation["visible_result_roles"]
            and occurrence.get("scope_owner_occurrence_id") == root_occurrence_id
            and occurrence.get("scope_owner_role") is None
            and occurrence.get("label_match", {}).get("page_sequence") == page_sequence
            and len(rows) == 1
            and occurrence_row_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
                occurrence["label_match"]
            )
        ):
            receipt = _hierarchy_frontier_row_receipt_v1(rows[0])
            if receipt is not None and len(receipt["numbers"]) == lane_count:
                role_result_candidates.append((occurrence, rows[0], receipt))
    parent_source_indices = list(_match_line_indices(parent_match, pages))
    cluster_result_candidates = []
    for cluster in evidence["internal_unassigned_numeric_clusters"]:
        cluster_sample_ids = cluster.get("sample_ids")
        samples = (
            [sample_by_id.get(sample_id) for sample_id in cluster_sample_ids]
            if type(cluster_sample_ids) is list
            else None
        )
        label_indices = [
            item.get("line_ordinal") for item in cluster.get("same_row_label_evidence", [])
        ]
        if (
            cluster.get("status") != occurrence_row_v2._INTERNAL_UNASSIGNED_CLUSTER_STATUS  # noqa: SLF001
            or cluster.get("label_lane_status") != occurrence_row_v2._LABELED_LABEL_LANE_STATUS  # noqa: SLF001
            or cluster.get("page_sequence") != page_sequence
            or label_indices != parent_source_indices
            or type(samples) is not list
            or any(type(item) is not dict for item in samples)
            or [item.get("column_ordinal") for item in samples] != list(range(lane_count))
            or [item.get("column_center") for item in samples] != centers
            or any(
                item.get("owner_kind") != "SOURCE_ONLY_INTERNAL_CLUSTER"
                or item.get("owner_id") != cluster.get("cluster_id")
                or item.get("page_sequence") != page_sequence
                for item in samples
            )
        ):
            continue
        numbers = [_hierarchy_frontier_number(item) for item in samples]
        if any(item is None for item in numbers):
            continue
        cluster_result_candidates.append(
            (
                cluster,
                {
                    "numbers": numbers,
                    "sample_ids": [item["sample_id"] for item in samples],
                },
                samples,
            )
        )
    same_page_clusters = [
        cluster
        for cluster in evidence["internal_unassigned_numeric_clusters"]
        if cluster.get("page_sequence") == page_sequence
    ]
    if len(role_result_candidates) + len(cluster_result_candidates) != 1 or len(
        same_page_clusters
    ) != len(cluster_result_candidates):
        return None
    if role_result_candidates:
        result_occurrence, result_record, result_receipt = role_result_candidates[0]
        result_carrier = {
            "carrier_kind": "ROLE_OCCURRENCE",
            "cluster_id": None,
            "numbers": canonical_clone_v1(result_receipt["numbers"]),
            "occurrence_id": result_occurrence["occurrence_id"],
            "role_occurrence_sha256": canonical_json_sha256_v1(result_occurrence),
            "semantic_result_role": equation["result_role"],
            "sample_ids": canonical_clone_v1(result_receipt["sample_ids"]),
            "source_line_indices": _hierarchy_frontier_source_line_indices(
                result_occurrence["label_match"]
            ),
            "source_record_sha256": canonical_json_sha256_v1(result_record),
            "source_role": result_occurrence["role"],
        }
        result_samples = result_record["values"]
    else:
        result_record, result_receipt, result_samples = cluster_result_candidates[0]
        result_carrier = {
            "carrier_kind": "LABELED_PARENT_CLUSTER",
            "cluster_id": result_record["cluster_id"],
            "numbers": canonical_clone_v1(result_receipt["numbers"]),
            "occurrence_id": None,
            "role_occurrence_sha256": None,
            "semantic_result_role": equation["result_role"],
            "sample_ids": canonical_clone_v1(result_receipt["sample_ids"]),
            "source_line_indices": parent_source_indices,
            "source_record_sha256": canonical_json_sha256_v1(result_record),
            "source_role": None,
        }
    certificates = []
    nodes = [("RESULT", 0, equation["result_role"], result_receipt, result_samples)] + [
        ("COMPONENT", ordinal, occurrence["role"], receipt, row["values"])
        for ordinal, ((occurrence, row), receipt) in enumerate(
            zip(direct_candidates, component_receipts, strict=True)
        )
    ]
    all_sample_ids = []
    for node_kind, node_ordinal, role, receipt, node_samples in nodes:
        samples = [sample_by_id.get(sample_id) for sample_id in receipt["sample_ids"]]
        if (
            len(samples) != lane_count
            or any(type(sample) is not dict for sample in samples)
            or [sample["column_ordinal"] for sample in samples] != list(range(lane_count))
            or [sample["column_center"] for sample in samples] != centers
            or [sample["page_sequence"] for sample in samples] != [page_sequence] * lane_count
            or [sample["sample_id"] for sample in node_samples] != receipt["sample_ids"]
        ):
            return None
        for sample in samples:
            certificate = _hierarchy_frontier_cell_certificate_v1(
                sample,
                node_kind=node_kind,
                node_ordinal=node_ordinal,
                role=role,
                page_line_by_sample=page_line_by_sample,
            )
            if certificate is None:
                return None
            certificates.append(certificate)
            all_sample_ids.append(sample["sample_id"])
    if len(all_sample_ids) != len(set(all_sample_ids)):
        return None
    for certificate in certificates:
        if certificate["certificate_kind"] != "MIXED_SAME_CROP_EXACT_INTEGER":
            continue
        peers = [
            item
            for item in certificates
            if item["column_ordinal"] == certificate["column_ordinal"]
            and item["sample_id"] != certificate["sample_id"]
        ]
        anchors = [
            item
            for item in certificates
            if item["column_ordinal"] == certificate["column_ordinal"]
            and item["certificate_kind"] == "RAW_SIGNED_SOURCE_VISIBLE"
        ]
        if len(peers) < 2 or not anchors:
            return None

    certified_number_by_sample = {
        certificate["sample_id"]: certificate["number"] for certificate in certificates
    }
    certified_result = {
        "numbers": [
            certified_number_by_sample[sample_id] for sample_id in result_receipt["sample_ids"]
        ]
    }
    certified_components = [
        {"numbers": [certified_number_by_sample[sample_id] for sample_id in receipt["sample_ids"]]}
        for receipt in component_receipts
    ]
    if not occurrence_row_v2._direct_frontier_sum_is_exact(  # noqa: SLF001
        certified_result,
        certified_components,
    ):
        return None

    component_bindings = [
        {
            "component_ordinal": ordinal,
            "numbers": canonical_clone_v1(receipt["numbers"]),
            "occurrence_id": occurrence["occurrence_id"],
            "retrieval_occurrence_id": occurrence["retrieval_occurrence_id"],
            "role": occurrence["role"],
            "role_occurrence_sha256": canonical_json_sha256_v1(occurrence),
            "row_sha256": canonical_json_sha256_v1(row),
            "sample_ids": canonical_clone_v1(receipt["sample_ids"]),
            "source_line_indices": _hierarchy_frontier_source_line_indices(
                occurrence["label_match"]
            ),
            "source_visual_ordinal": visual_ordinal_by_occurrence[occurrence["occurrence_id"]],
            "visual_match_key_sha256": canonical_json_sha256_v1(
                list(
                    occurrence_row_v2._visual_match_key(  # noqa: SLF001
                        occurrence["label_match"]
                    )
                )
            ),
        }
        for ordinal, ((occurrence, row), receipt) in enumerate(
            zip(direct_candidates, component_receipts, strict=True)
        )
    ]
    hierarchy_binding = {
        "alternative_ordinal": alternative_ordinal,
        "alternative_spec": canonical_clone_v1(alternative),
        "compiled_equation_sha256": canonical_json_sha256_v1(equation),
        "component_roles": canonical_clone_v1(alternative["component_roles"]),
        "hierarchy_spec_sha256": canonical_json_sha256_v1(hierarchy_spec),
        "result_role": equation["result_role"],
        "visible_result_roles": canonical_clone_v1(equation["visible_result_roles"]),
    }
    material = {
        "column_context_receipt": canonical_clone_v1(context),
        "component_frontier_bindings": component_bindings,
        "format_version": _HIERARCHY_FRONTIER_PROOF_FORMAT_VERSION,
        "hierarchy_equation_binding": hierarchy_binding,
        "input_binding": canonical_clone_v1(input_binding),
        "numeric_cell_certificates": certificates,
        "page_sequence": page_sequence,
        "result_carrier_binding": result_carrier,
        "root_occurrence_id": root_occurrence_id,
        "source_check": canonical_clone_v1(source_check),
        "status": _HIERARCHY_FRONTIER_BOUND_STATUS,
        "target_kind": target_kind,
        "target_occurrence_id": target_occurrence_id,
        "target_role": target_role,
    }
    return {
        **material,
        "proof_id": "afeoehdfav1:proof:" + canonical_json_sha256_v1(material),
    }


def _build_recursive_hierarchy_frontier_proof_v1(
    source_receipt: Mapping[str, Any],
    evidence: Mapping[str, Any],
    context: Mapping[str, Any],
    family_spec: Any,
    hierarchy_spec: Any,
    input_binding: Mapping[str, str],
) -> dict[str, Any] | None:
    if len(source_receipt["checks"]) != 1:
        return None
    source_check = source_receipt["checks"][0]
    retrieval = source_check.get("retrieval_channel")
    if (
        source_check.get("match_scope") != "EXPANDED_OCCURRENCE"
        or source_check.get("status")
        not in {
            "NO_EXACT_DECLARED_ALIAS_ON_RETRIEVAL_SOURCE_SPAN",
            "RETRIEVAL_ONE_EDIT_ALIAS_SPEC_BINDING_DRIFTED",
        }
        or type(source_check.get("occurrence_id")) is not str
        or type(retrieval) is not dict
        or retrieval.get("match_kind") != "ONE_EDIT_ALIAS_REQUIRES_COMPLETE_TOPOLOGY"
    ):
        return None
    targets = [
        occurrence
        for occurrence in evidence["role_occurrences"]
        if occurrence.get("retrieval_occurrence_id") == source_check["occurrence_id"]
        and occurrence.get("role") == source_check["role"]
        and str(occurrence.get("label_match", {}).get("match_kind", "")).startswith("ONE_EDIT_")
    ]
    if len(targets) != 1 or source_check["source_line_indices"] != (
        _hierarchy_frontier_source_line_indices(targets[0]["label_match"])
    ):
        return None
    target_page = targets[0]["label_match"].get("page_sequence")
    grids = [
        grid
        for grid in evidence["row_axis"]["column_grids"]
        if grid.get("page_sequence") == target_page
    ]
    if len(grids) != 1:
        return None
    centers = grids[0]["column_centers"]
    period_axis = sorted(context["period_axis"], key=lambda item: item["column_ordinal"])
    unit_axis = sorted(context["unit_axis"], key=lambda item: item["column_ordinal"])
    if (
        context.get("status") != "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
        or context.get("row_axis_id") != evidence["row_axis"]["row_axis_id"]
        or [item.get("column_ordinal") for item in period_axis] != list(range(len(centers)))
        or [item.get("column_ordinal") for item in unit_axis] != list(range(len(centers)))
        or [item.get("column_center") for item in period_axis] != centers
        or [item.get("column_center") for item in unit_axis] != centers
    ):
        return None
    from bctc_ai.evaluation import (  # noqa: PLC0415
        accounting_scoped_hierarchical_table_closure_v2 as closure_v2,
    )

    recursive = closure_v2._project_provisional_one_edit_recursive_frontier_v1(  # noqa: SLF001
        authenticated_extreme_margin_furniture_evidence=evidence[
            "authenticated_extreme_margin_furniture_evidence"
        ],
        family_topology_spec=family_spec,
        hierarchy_spec=hierarchy_spec,
        internal_unassigned_numeric_clusters=evidence["internal_unassigned_numeric_clusters"],
        numeric_sample_universe=evidence["numeric_sample_universe"],
        role_occurrences=evidence["role_occurrences"],
        row_axis=evidence["row_axis"],
        target_retrieval_occurrence_id=source_check["occurrence_id"],
    )
    if (
        type(recursive) is not dict
        or recursive.get("target_occurrence_id") != targets[0]["occurrence_id"]
        or recursive.get("target_role") != source_check["role"]
        or recursive.get("page_sequence") != target_page
    ):
        return None
    sample_by_id = {sample["sample_id"]: sample for sample in evidence["numeric_sample_universe"]}
    covered_samples = [
        sample_by_id.get(sample_id) for sample_id in recursive["covered_source_sample_ids"]
    ]
    if any(
        type(sample) is not dict
        or sample.get("parsed_token", {}).get("classification")
        not in {"DASH_ZERO", "SIGNED_NUMBER"}
        for sample in covered_samples
    ):
        return None
    material = {
        "column_context_receipt": canonical_clone_v1(context),
        "format_version": _RECURSIVE_HIERARCHY_FRONTIER_PROOF_FORMAT_VERSION,
        "input_binding": canonical_clone_v1(input_binding),
        "recursive_frontier": canonical_clone_v1(recursive),
        "source_check": canonical_clone_v1(source_check),
        "status": _RECURSIVE_HIERARCHY_FRONTIER_BOUND_STATUS,
    }
    return {
        **material,
        "proof_id": "afeoerhdfav1:proof:" + canonical_json_sha256_v1(material),
    }


def _validate_recursive_hierarchy_frontier_proof_shape_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RECURSIVE_HIERARCHY_FRONTIER_PROOF_FIELDS
        or value.get("format_version") != _RECURSIVE_HIERARCHY_FRONTIER_PROOF_FORMAT_VERSION
        or value.get("status") != _RECURSIVE_HIERARCHY_FRONTIER_BOUND_STATUS
        or type(value.get("source_check")) is not dict
        or type(value.get("input_binding")) is not dict
        or set(value["input_binding"]) != _RECURSIVE_HIERARCHY_FRONTIER_INPUT_BINDING_FIELDS
        or any(
            type(item) is not str
            or len(item) != 64
            or any(character not in "0123456789abcdef" for character in item)
            for item in value["input_binding"].values()
        )
    ):
        raise _error("one-edit recursive hierarchy-frontier proof shape drifted")
    try:
        column_context_multilevel_v2._validate_context_receipt_v2(  # noqa: SLF001
            value["column_context_receipt"]
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("one-edit recursive hierarchy-frontier column receipt drifted") from exc
    recursive = value.get("recursive_frontier")
    if (
        type(recursive) is not dict
        or set(recursive) != _RECURSIVE_FRONTIER_FIELDS
        or recursive.get("format_version")
        != "ACCOUNTING_SCOPED_HIERARCHICAL_PROVISIONAL_ONE_EDIT_RECURSIVE_FRONTIER_V1"
        or recursive.get("target_retrieval_occurrence_id")
        != value["source_check"].get("occurrence_id")
        or recursive.get("target_role") != value["source_check"].get("role")
    ):
        raise _error("one-edit recursive hierarchy-frontier closure proof drifted")
    recursive_material = canonical_clone_v1(recursive)
    recursive_id = recursive_material.pop("proof_id")
    if recursive_id != "ashtcv2:provisional-one-edit-recursive-frontier:" + (
        canonical_json_sha256_v1(recursive_material)
    ):
        raise _error("one-edit recursive hierarchy-frontier closure identity drifted")
    material = canonical_clone_v1(value)
    proof_id = material.pop("proof_id")
    if proof_id != "afeoerhdfav1:proof:" + canonical_json_sha256_v1(material):
        raise _error("one-edit recursive hierarchy-frontier proof identity drifted")
    return canonical_clone_v1(value)


def _validate_hierarchy_frontier_proof_shape_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _HIERARCHY_FRONTIER_PROOF_FIELDS
        or value.get("format_version") != _HIERARCHY_FRONTIER_PROOF_FORMAT_VERSION
        or value.get("status") != _HIERARCHY_FRONTIER_BOUND_STATUS
        or type(value.get("root_occurrence_id")) is not str
        or not value["root_occurrence_id"].startswith("aforav2:root:")
        or type(value.get("page_sequence")) is not int
        or value["page_sequence"] <= 0
        or value.get("target_kind") not in {"COMPONENT", "FAMILY_PARENT"}
        or type(value.get("target_role")) is not str
        or not value["target_role"]
        or type(value.get("source_check")) is not dict
        or type(value.get("input_binding")) is not dict
        or set(value["input_binding"]) != _HIERARCHY_FRONTIER_INPUT_BINDING_FIELDS
        or any(
            type(item) is not str
            or len(item) != 64
            or any(character not in "0123456789abcdef" for character in item)
            for item in value["input_binding"].values()
        )
    ):
        raise _error("one-edit hierarchy-frontier proof shape drifted")
    if (value["target_kind"] == "FAMILY_PARENT" and value["target_occurrence_id"] is not None) or (
        value["target_kind"] == "COMPONENT"
        and (
            type(value["target_occurrence_id"]) is not str
            or not value["target_occurrence_id"].startswith("aforav2:occurrence:")
        )
    ):
        raise _error("one-edit hierarchy-frontier target identity drifted")
    try:
        context = column_context_multilevel_v2._validate_context_receipt_v2(  # noqa: SLF001
            value["column_context_receipt"]
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("one-edit hierarchy-frontier column receipt drifted") from exc
    lane_count = len(context["period_axis"])
    equation = value.get("hierarchy_equation_binding")
    carrier = value.get("result_carrier_binding")
    components = value.get("component_frontier_bindings")
    certificates = value.get("numeric_cell_certificates")
    if (
        lane_count == 0
        or len(context["unit_axis"]) != lane_count
        or type(equation) is not dict
        or set(equation) != _HIERARCHY_FRONTIER_EQUATION_BINDING_FIELDS
        or type(equation["alternative_ordinal"]) is not int
        or equation["alternative_ordinal"] < 0
        or type(equation["alternative_spec"]) is not dict
        or set(equation["alternative_spec"])
        != {
            "component_roles",
            "coverage_policy",
            "derivation_policy",
        }
        or equation["alternative_spec"].get("coverage_policy") != "EXHAUSTIVE_COMPONENT_SET"
        or equation["alternative_spec"].get("derivation_policy")
        != "ALLOW_DERIVATION_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"
        or equation["component_roles"] != equation["alternative_spec"].get("component_roles")
        or type(equation["component_roles"]) is not list
        or not equation["component_roles"]
        or len(equation["component_roles"]) != len(set(equation["component_roles"]))
        or type(equation["result_role"]) is not str
        or not equation["result_role"]
        or type(equation["visible_result_roles"]) is not list
        or not equation["visible_result_roles"]
        or equation["hierarchy_spec_sha256"] != value["input_binding"]["hierarchy_spec_sha256"]
        or any(
            type(equation[key]) is not str
            or len(equation[key]) != 64
            or any(character not in "0123456789abcdef" for character in equation[key])
            for key in ("compiled_equation_sha256", "hierarchy_spec_sha256")
        )
        or type(carrier) is not dict
        or set(carrier) != _HIERARCHY_FRONTIER_RESULT_CARRIER_FIELDS
        or carrier["carrier_kind"] not in {"LABELED_PARENT_CLUSTER", "ROLE_OCCURRENCE"}
        or carrier["semantic_result_role"] != equation["result_role"]
        or not _parent_frontier_number_axis_is_valid(carrier["numbers"])
        or len(carrier["numbers"]) != lane_count
        or type(carrier["sample_ids"]) is not list
        or len(carrier["sample_ids"]) != lane_count
        or len(carrier["sample_ids"]) != len(set(carrier["sample_ids"]))
        or type(carrier["source_line_indices"]) is not list
        or not carrier["source_line_indices"]
        or carrier["source_line_indices"] != sorted(set(carrier["source_line_indices"]))
        or type(carrier["source_record_sha256"]) is not str
        or len(carrier["source_record_sha256"]) != 64
        or type(components) is not list
        or len(components) != len(equation["component_roles"])
        or type(certificates) is not list
        or len(certificates) != lane_count * (len(components) + 1)
    ):
        raise _error("one-edit hierarchy-frontier equation or result binding drifted")
    if (
        carrier["carrier_kind"] == "ROLE_OCCURRENCE"
        and (
            type(carrier["occurrence_id"]) is not str
            or not carrier["occurrence_id"].startswith("aforav2:occurrence:")
            or carrier["cluster_id"] is not None
            or carrier["source_role"] not in equation["visible_result_roles"]
            or type(carrier["role_occurrence_sha256"]) is not str
            or len(carrier["role_occurrence_sha256"]) != 64
        )
    ) or (
        carrier["carrier_kind"] == "LABELED_PARENT_CLUSTER"
        and (
            carrier["occurrence_id"] is not None
            or carrier["role_occurrence_sha256"] is not None
            or carrier["source_role"] is not None
            or type(carrier["cluster_id"]) is not str
            or not carrier["cluster_id"].startswith("aforav2:unassigned:")
        )
    ):
        raise _error("one-edit hierarchy-frontier result carrier drifted")
    component_receipts = []
    component_ids = []
    sample_ids = list(carrier["sample_ids"])
    for ordinal, (binding, role) in enumerate(
        zip(components, equation["component_roles"], strict=True)
    ):
        if (
            type(binding) is not dict
            or set(binding) != _HIERARCHY_FRONTIER_COMPONENT_FIELDS
            or binding["component_ordinal"] != ordinal
            or binding["role"] != role
            or type(binding["occurrence_id"]) is not str
            or not binding["occurrence_id"].startswith("aforav2:occurrence:")
            or type(binding["retrieval_occurrence_id"]) is not str
            or not binding["retrieval_occurrence_id"].startswith("aforav2:occurrence:")
            or not _parent_frontier_number_axis_is_valid(binding["numbers"])
            or len(binding["numbers"]) != lane_count
            or type(binding["sample_ids"]) is not list
            or len(binding["sample_ids"]) != lane_count
            or len(binding["sample_ids"]) != len(set(binding["sample_ids"]))
            or type(binding["source_line_indices"]) is not list
            or not binding["source_line_indices"]
            or binding["source_line_indices"] != sorted(set(binding["source_line_indices"]))
            or type(binding["source_visual_ordinal"]) is not int
            or not 0 <= binding["source_visual_ordinal"] < len(components)
            or any(
                type(binding[key]) is not str or len(binding[key]) != 64
                for key in (
                    "role_occurrence_sha256",
                    "row_sha256",
                    "visual_match_key_sha256",
                )
            )
        ):
            raise _error("one-edit hierarchy-frontier component binding drifted")
        component_ids.append(binding["occurrence_id"])
        sample_ids.extend(binding["sample_ids"])
        component_receipts.append({"numbers": binding["numbers"]})
    if (
        len(component_ids) != len(set(component_ids))
        or len(sample_ids) != len(set(sample_ids))
        or sorted(item["source_visual_ordinal"] for item in components)
        != list(range(len(components)))
    ):
        raise _error("one-edit hierarchy-frontier component identity drifted")
    expected_cell_keys = [
        *(("RESULT", 0, equation["result_role"], lane) for lane in range(lane_count)),
        *(
            ("COMPONENT", ordinal, role, lane)
            for ordinal, role in enumerate(equation["component_roles"])
            for lane in range(lane_count)
        ),
    ]
    observed_cell_keys = []
    certificate_samples = []
    for certificate in certificates:
        if (
            type(certificate) is not dict
            or set(certificate) != _HIERARCHY_FRONTIER_CELL_FIELDS
            or certificate["certificate_kind"]
            not in {"RAW_SIGNED_SOURCE_VISIBLE", "MIXED_SAME_CROP_EXACT_INTEGER"}
            or certificate["pp_classification"]
            not in {"SIGNED_NUMBER", "MIXED_GROUPED_INTEGER_CANDIDATE"}
            or (
                certificate["certificate_kind"] == "RAW_SIGNED_SOURCE_VISIBLE"
                and (
                    certificate["pp_classification"] != "SIGNED_NUMBER"
                    or certificate["vietocr_number"] is not None
                )
            )
            or (
                certificate["certificate_kind"] == "MIXED_SAME_CROP_EXACT_INTEGER"
                and (
                    certificate["pp_classification"] != "MIXED_GROUPED_INTEGER_CANDIDATE"
                    or not same_typed_json_v1(certificate["vietocr_number"], certificate["number"])
                )
            )
            or not _parent_frontier_number_axis_is_valid([certificate["number"]])
            or type(certificate["sample_id"]) is not str
            or not certificate["sample_id"]
            or type(certificate["pp_surface"]) is not str
            or type(certificate["vietocr_surface"]) is not str
            or type(certificate["page_sequence"]) is not int
            or certificate["page_sequence"] != value["page_sequence"]
            or type(certificate["source_line_index"]) is not int
            or certificate["source_line_index"] < 0
            or type(certificate["bbox"]) is not list
            or len(certificate["bbox"]) != 4
            or any(type(item) is not int for item in certificate["bbox"])
            or any(
                type(certificate[key]) is not str or len(certificate[key]) != 64
                for key in ("numeric_sample_sha256", "page_line_sha256")
            )
        ):
            raise _error("one-edit hierarchy-frontier numeric certificate drifted")
        _crop_reference(certificate["crop_ref"])
        if certificate["certificate_kind"] == "MIXED_SAME_CROP_EXACT_INTEGER":
            replayed_vietocr = parse_visible_financial_numeric_token_v1(
                certificate["vietocr_surface"]
            )
            expected_number = certificate["vietocr_number"]
            if (
                replayed_vietocr.get("classification") != "SIGNED_NUMBER"
                or replayed_vietocr.get("coefficient") != expected_number["coefficient"]
                or replayed_vietocr.get("scale") != expected_number["scale"]
                or replayed_vietocr.get("percentage_mark_present")
                is not expected_number["percentage_mark_present"]
            ):
                raise _error("one-edit hierarchy-frontier VietOCR certificate drifted")
        observed_cell_keys.append(
            (
                certificate["node_kind"],
                certificate["node_ordinal"],
                certificate["role"],
                certificate["column_ordinal"],
            )
        )
        certificate_samples.append(certificate["sample_id"])
    if observed_cell_keys != expected_cell_keys or certificate_samples != sample_ids:
        raise _error("one-edit hierarchy-frontier numeric certificate axis drifted")
    for certificate in certificates:
        if certificate["certificate_kind"] != "MIXED_SAME_CROP_EXACT_INTEGER":
            continue
        lane_peers = [
            item
            for item in certificates
            if item["column_ordinal"] == certificate["column_ordinal"]
            and item["sample_id"] != certificate["sample_id"]
        ]
        raw_anchors = [
            item
            for item in certificates
            if item["column_ordinal"] == certificate["column_ordinal"]
            and item["certificate_kind"] == "RAW_SIGNED_SOURCE_VISIBLE"
        ]
        if len(lane_peers) < 2 or not raw_anchors:
            raise _error("one-edit hierarchy-frontier mixed peer axis drifted")
    certified_by_sample = {item["sample_id"]: item["number"] for item in certificates}
    certified_result = {"numbers": [certified_by_sample[item] for item in carrier["sample_ids"]]}
    certified_components = [
        {"numbers": [certified_by_sample[item] for item in binding["sample_ids"]]}
        for binding in components
    ]
    if not occurrence_row_v2._direct_frontier_sum_is_exact(  # noqa: SLF001
        certified_result,
        certified_components,
    ):
        raise _error("one-edit hierarchy-frontier certified arithmetic drifted")
    source_check = value["source_check"]
    target_components = [
        item for item in components if item["occurrence_id"] == value["target_occurrence_id"]
    ]
    if (
        set(source_check) != _CHECK_FIELDS
        or source_check["status"] != "NO_EXACT_DECLARED_ALIAS_ON_RETRIEVAL_SOURCE_SPAN"
        or source_check.get("retrieval_channel", {}).get("match_kind")
        != "ONE_EDIT_ALIAS_REQUIRES_COMPLETE_TOPOLOGY"
        or len(source_check.get("retrieval_channel", {}).get("alias_candidates", [])) != 1
        or source_check["role"] != value["target_role"]
        or source_check["page_sequence"] != value["page_sequence"]
        or (
            value["target_kind"] == "FAMILY_PARENT"
            and (
                source_check["match_scope"] != "FAMILY_PARENT"
                or source_check["occurrence_id"] is not None
                or source_check["source_line_indices"] != carrier["source_line_indices"]
            )
        )
        or (
            value["target_kind"] == "COMPONENT"
            and (
                len(target_components) != 1
                or source_check["match_scope"] != "EXPANDED_OCCURRENCE"
                or source_check["occurrence_id"]
                != (target_components[0]["retrieval_occurrence_id"] if target_components else None)
            )
        )
    ):
        raise _error("one-edit hierarchy-frontier source check drifted")
    material = canonical_clone_v1(value)
    proof_id = material.pop("proof_id")
    if proof_id != "afeoehdfav1:proof:" + canonical_json_sha256_v1(material):
        raise _error("one-edit hierarchy-frontier proof identity drifted")
    return canonical_clone_v1(value)


def _validate_hierarchy_frontier_result_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _HIERARCHY_FRONTIER_RESULT_FIELDS
        or value.get("format_version") != HIERARCHY_FRONTIER_FORMAT_VERSION
        or value.get("claim_boundary") != HIERARCHY_FRONTIER_CLAIM_BOUNDARY
        or not same_typed_json_v1(value.get("safety"), _HIERARCHY_FRONTIER_SAFETY)
        or type(value.get("authority_spec")) is not dict
        or set(value["authority_spec"]) != {"sha256", "value"}
        or not same_typed_json_v1(
            value["authority_spec"]["value"], _HIERARCHY_FRONTIER_AUTHORITY_SPEC
        )
        or value["authority_spec"]["sha256"]
        != canonical_json_sha256_v1(_HIERARCHY_FRONTIER_AUTHORITY_SPEC)
    ):
        raise _error("one-edit hierarchy-frontier receipt shape drifted")
    source = _validate_result(value["source_exact_authority_receipt"])
    proof = _validate_hierarchy_frontier_proof_shape_v1(
        value["hierarchy_direct_frontier_authority"]
    )
    unbound_checks = [
        check for check in source["checks"] if check["status"] not in _BOUND_CHECK_STATUSES
    ]
    if (
        len(source["checks"]) != 1
        or len(unbound_checks) != 1
        or not same_typed_json_v1(unbound_checks[0], proof["source_check"])
        or value["family_id"] != source["family_id"]
        or value["checks"] != source["checks"]
        or value["input_binding"] != proof["input_binding"]
        or value["input_binding"]["source_exact_authority_receipt_sha256"]
        != canonical_json_sha256_v1(source)
        or any(
            value["input_binding"][key] != source["input_binding"][key]
            for key in _INPUT_BINDING_FIELDS
        )
    ):
        raise _error("one-edit hierarchy-frontier source binding drifted")
    source_reason = _parent_frontier_reason(unbound_checks[0])
    expected_reasons = [
        reason for reason in source["unresolved_reasons"] if reason != source_reason
    ]
    expected_metrics = {
        "exact_bound_count": source["metrics"]["exact_bound_count"] + 1,
        "selected_one_edit_match_count": source["metrics"]["selected_one_edit_match_count"],
        "unresolved_match_count": source["metrics"]["unresolved_match_count"] - 1,
    }
    expected_status = (
        "EXACT_SOURCE_AUTHORITY_BOUND"
        if not expected_reasons
        else "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY"
    )
    if (
        value["metrics"] != expected_metrics
        or value["unresolved_reasons"] != expected_reasons
        or value["status"] != expected_status
    ):
        raise _error("one-edit hierarchy-frontier status drifted")
    material = canonical_clone_v1(value)
    receipt_id = material.pop("receipt_id")
    if receipt_id != "afeoeav1:receipt:" + canonical_json_sha256_v1(material):
        raise _error("one-edit hierarchy-frontier receipt identity drifted")
    return canonical_clone_v1(value)


def _validate_recursive_hierarchy_frontier_result_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RECURSIVE_HIERARCHY_FRONTIER_RESULT_FIELDS
        or value.get("format_version") != RECURSIVE_HIERARCHY_FRONTIER_FORMAT_VERSION
        or value.get("claim_boundary") != RECURSIVE_HIERARCHY_FRONTIER_CLAIM_BOUNDARY
        or not same_typed_json_v1(value.get("safety"), _RECURSIVE_HIERARCHY_FRONTIER_SAFETY)
        or type(value.get("authority_spec")) is not dict
        or set(value["authority_spec"]) != {"sha256", "value"}
        or not same_typed_json_v1(
            value["authority_spec"]["value"],
            _RECURSIVE_HIERARCHY_FRONTIER_AUTHORITY_SPEC,
        )
        or value["authority_spec"]["sha256"]
        != canonical_json_sha256_v1(_RECURSIVE_HIERARCHY_FRONTIER_AUTHORITY_SPEC)
    ):
        raise _error("one-edit recursive hierarchy-frontier receipt shape drifted")
    source = _validate_result(value["source_exact_authority_receipt"])
    proof = _validate_recursive_hierarchy_frontier_proof_shape_v1(
        value["recursive_hierarchy_direct_frontier_authority"]
    )
    unbound_checks = [
        check for check in source["checks"] if check["status"] not in _BOUND_CHECK_STATUSES
    ]
    if (
        len(source["checks"]) != 1
        or len(unbound_checks) != 1
        or not same_typed_json_v1(unbound_checks[0], proof["source_check"])
        or value["family_id"] != source["family_id"]
        or value["checks"] != source["checks"]
        or value["input_binding"] != proof["input_binding"]
        or value["input_binding"]["source_exact_authority_receipt_sha256"]
        != canonical_json_sha256_v1(source)
        or any(
            value["input_binding"][key] != source["input_binding"][key]
            for key in _INPUT_BINDING_FIELDS
        )
    ):
        raise _error("one-edit recursive hierarchy-frontier source binding drifted")
    source_reason = _parent_frontier_reason(unbound_checks[0])
    expected_reasons = [
        reason for reason in source["unresolved_reasons"] if reason != source_reason
    ]
    expected_metrics = {
        "exact_bound_count": source["metrics"]["exact_bound_count"] + 1,
        "selected_one_edit_match_count": source["metrics"]["selected_one_edit_match_count"],
        "unresolved_match_count": source["metrics"]["unresolved_match_count"] - 1,
    }
    expected_status = (
        "EXACT_SOURCE_AUTHORITY_BOUND"
        if not expected_reasons
        else "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY"
    )
    if (
        value["metrics"] != expected_metrics
        or value["unresolved_reasons"] != expected_reasons
        or value["status"] != expected_status
    ):
        raise _error("one-edit recursive hierarchy-frontier status drifted")
    material = canonical_clone_v1(value)
    receipt_id = material.pop("receipt_id")
    if receipt_id != "afeoeav1:receipt:" + canonical_json_sha256_v1(material):
        raise _error("one-edit recursive hierarchy-frontier receipt identity drifted")
    return canonical_clone_v1(value)


def _validate_recursive_hierarchy_frontier_against_structural_evidence_v1(
    value: Any,
    structural_evidence: Any,
    *,
    family_spec: Any = None,
    hierarchy_spec: Any = None,
) -> dict[str, Any]:
    receipt = _validate_recursive_hierarchy_frontier_result_v1(value)
    evidence = _parent_frontier_structural_evidence_v1(structural_evidence)
    proof = receipt["recursive_hierarchy_direct_frontier_authority"]
    recursive = proof["recursive_frontier"]
    context = proof["column_context_receipt"]
    binding = receipt["input_binding"]
    if (
        binding["internal_unassigned_numeric_clusters_sha256"]
        != canonical_json_sha256_v1(evidence["internal_unassigned_numeric_clusters"])
        or binding["numeric_sample_universe_sha256"]
        != canonical_json_sha256_v1(evidence["numeric_sample_universe"])
        or binding["role_occurrences_sha256"]
        != canonical_json_sha256_v1(evidence["role_occurrences"])
        or binding["row_axis_sha256"] != canonical_json_sha256_v1(evidence["row_axis"])
        or binding["column_context_sha256"] != canonical_json_sha256_v1(context)
        or binding["authenticated_extreme_margin_furniture_evidence_sha256"]
        != canonical_json_sha256_v1(evidence["authenticated_extreme_margin_furniture_evidence"])
        or context["row_axis_id"] != evidence["row_axis"]["row_axis_id"]
    ):
        raise _error("one-edit recursive hierarchy-frontier structural input drifted")
    target_matches = [
        occurrence
        for occurrence in evidence["role_occurrences"]
        if occurrence.get("occurrence_id") == recursive["target_occurrence_id"]
        and occurrence.get("retrieval_occurrence_id") == recursive["target_retrieval_occurrence_id"]
        and occurrence.get("role") == recursive["target_role"]
    ]
    if (
        len(target_matches) != 1
        or not str(target_matches[0].get("label_match", {}).get("match_kind", "")).startswith(
            "ONE_EDIT_"
        )
        or _hierarchy_frontier_source_line_indices(target_matches[0]["label_match"])
        != proof["source_check"]["source_line_indices"]
        or target_matches[0].get("scope_owner_occurrence_id") != recursive["root_occurrence_id"]
    ):
        raise _error("one-edit recursive hierarchy-frontier target binding drifted")
    sample_by_id = {sample["sample_id"]: sample for sample in evidence["numeric_sample_universe"]}
    covered_samples = [
        sample_by_id.get(sample_id) for sample_id in recursive["covered_source_sample_ids"]
    ]
    if any(
        type(sample) is not dict
        or sample.get("parsed_token", {}).get("classification")
        not in {"DASH_ZERO", "SIGNED_NUMBER"}
        for sample in covered_samples
    ) or set(recursive["covered_source_sample_ids"]) != set(sample_by_id):
        raise _error("one-edit recursive hierarchy-frontier source sample binding drifted")
    if (family_spec is None) is not (hierarchy_spec is None):
        raise _error("one-edit recursive hierarchy-frontier replay policy is incomplete")
    if family_spec is not None:
        from bctc_ai.evaluation import (  # noqa: PLC0415
            accounting_scoped_hierarchical_table_closure_v2 as closure_v2,
        )

        expected = closure_v2._project_provisional_one_edit_recursive_frontier_v1(  # noqa: SLF001
            authenticated_extreme_margin_furniture_evidence=evidence[
                "authenticated_extreme_margin_furniture_evidence"
            ],
            family_topology_spec=family_spec,
            hierarchy_spec=hierarchy_spec,
            internal_unassigned_numeric_clusters=evidence["internal_unassigned_numeric_clusters"],
            numeric_sample_universe=evidence["numeric_sample_universe"],
            role_occurrences=evidence["role_occurrences"],
            row_axis=evidence["row_axis"],
            target_retrieval_occurrence_id=recursive["target_retrieval_occurrence_id"],
        )
        if not same_typed_json_v1(expected, recursive):
            raise _error("one-edit recursive hierarchy-frontier closure does not replay exactly")
    return receipt


def _validate_hierarchy_frontier_against_structural_evidence_v1(
    value: Any,
    structural_evidence: Any,
) -> dict[str, Any]:
    receipt = _validate_hierarchy_frontier_result_v1(value)
    evidence = _parent_frontier_structural_evidence_v1(structural_evidence)
    proof = receipt["hierarchy_direct_frontier_authority"]
    context = proof["column_context_receipt"]
    centers = [item["column_center"] for item in context["period_axis"]]
    lane_count = len(centers)
    context = proof["column_context_receipt"]
    binding = receipt["input_binding"]
    if (
        binding["internal_unassigned_numeric_clusters_sha256"]
        != canonical_json_sha256_v1(evidence["internal_unassigned_numeric_clusters"])
        or binding["numeric_sample_universe_sha256"]
        != canonical_json_sha256_v1(evidence["numeric_sample_universe"])
        or binding["role_occurrences_sha256"]
        != canonical_json_sha256_v1(evidence["role_occurrences"])
        or binding["row_axis_sha256"] != canonical_json_sha256_v1(evidence["row_axis"])
        or binding["column_context_sha256"] != canonical_json_sha256_v1(context)
        or context["row_axis_id"] != evidence["row_axis"]["row_axis_id"]
    ):
        raise _error("one-edit hierarchy-frontier structural input drifted")
    page_sequence = proof["page_sequence"]
    grids = [
        grid
        for grid in evidence["row_axis"]["column_grids"]
        if grid["page_sequence"] == page_sequence
    ]
    if len(grids) != 1:
        raise _error("one-edit hierarchy-frontier page grid is not unique")
    centers = grids[0]["column_centers"]
    lane_count = len(centers)
    if (
        lane_count == 0
        or [item["column_center"] for item in context["period_axis"]] != centers
        or [item["column_center"] for item in context["unit_axis"]] != centers
    ):
        raise _error("one-edit hierarchy-frontier column axis drifted")
    occurrence_by_id = {
        occurrence.get("occurrence_id"): occurrence
        for occurrence in evidence["role_occurrences"]
        if type(occurrence) is dict and type(occurrence.get("occurrence_id")) is str
    }
    rows_by_occurrence: dict[str, list[Mapping[str, Any]]] = {}
    for row in evidence["row_axis"]["rows"]:
        occurrence_id = row.get("label_match", {}).get("occurrence_id")
        if type(occurrence_id) is str:
            rows_by_occurrence.setdefault(occurrence_id, []).append(row)
    sample_by_id = {
        sample.get("sample_id"): sample
        for sample in evidence["numeric_sample_universe"]
        if type(sample) is dict and type(sample.get("sample_id")) is str
    }
    if len(occurrence_by_id) != len(evidence["role_occurrences"]) or len(sample_by_id) != len(
        evidence["numeric_sample_universe"]
    ):
        raise _error("one-edit hierarchy-frontier structural identities repeat")
    component_receipts = []
    component_visual_axis = []
    for binding_record in proof["component_frontier_bindings"]:
        occurrence = occurrence_by_id.get(binding_record["occurrence_id"])
        rows = rows_by_occurrence.get(binding_record["occurrence_id"], [])
        row = rows[0] if len(rows) == 1 else None
        receipt_row = _hierarchy_frontier_row_receipt_v1(row) if type(row) is dict else None
        if (
            type(occurrence) is not dict
            or canonical_json_sha256_v1(occurrence) != binding_record["role_occurrence_sha256"]
            or occurrence.get("role") != binding_record["role"]
            or occurrence.get("retrieval_occurrence_id")
            != binding_record["retrieval_occurrence_id"]
            or occurrence.get("scope_owner_occurrence_id") != proof["root_occurrence_id"]
            or occurrence.get("scope_owner_role") is not None
            or occurrence.get("label_match", {}).get("page_sequence") != page_sequence
            or _hierarchy_frontier_source_line_indices(occurrence["label_match"])
            != binding_record["source_line_indices"]
            or canonical_json_sha256_v1(
                list(
                    occurrence_row_v2._visual_match_key(  # noqa: SLF001
                        occurrence["label_match"]
                    )
                )
            )
            != binding_record["visual_match_key_sha256"]
            or type(row) is not dict
            or canonical_json_sha256_v1(row) != binding_record["row_sha256"]
            or receipt_row
            != {
                "numbers": binding_record["numbers"],
                "sample_ids": binding_record["sample_ids"],
            }
            or [item.get("column_ordinal") for item in row["values"]] != list(range(lane_count))
            or [item.get("column_center") for item in row["values"]] != centers
        ):
            raise _error("one-edit hierarchy-frontier component structural binding drifted")
        component_receipts.append(receipt_row)
        component_visual_axis.append(
            (occurrence_row_v2._visual_match_key(occurrence["label_match"]), binding_record)  # noqa: SLF001
        )
    if len({item[0] for item in component_visual_axis}) != len(component_visual_axis) or any(
        binding_record["source_visual_ordinal"] != ordinal
        for ordinal, (_key, binding_record) in enumerate(
            sorted(component_visual_axis, key=lambda item: item[0])
        )
    ):
        raise _error("one-edit hierarchy-frontier source visual order drifted")
    carrier = proof["result_carrier_binding"]
    result_samples = [sample_by_id.get(item) for item in carrier["sample_ids"]]
    if (
        any(type(item) is not dict for item in result_samples)
        or [_hierarchy_frontier_number(item) for item in result_samples] != carrier["numbers"]
        or [item["column_ordinal"] for item in result_samples] != list(range(lane_count))
        or [item["column_center"] for item in result_samples] != centers
        or [item["page_sequence"] for item in result_samples] != [page_sequence] * lane_count
    ):
        raise _error("one-edit hierarchy-frontier result sample binding drifted")
    if carrier["carrier_kind"] == "ROLE_OCCURRENCE":
        occurrence = occurrence_by_id.get(carrier["occurrence_id"])
        rows = rows_by_occurrence.get(carrier["occurrence_id"], [])
        record = rows[0] if len(rows) == 1 else None
        if (
            type(occurrence) is not dict
            or canonical_json_sha256_v1(occurrence) != carrier["role_occurrence_sha256"]
            or occurrence.get("role") != carrier["source_role"]
            or occurrence.get("scope_owner_occurrence_id") != proof["root_occurrence_id"]
            or occurrence.get("scope_owner_role") is not None
            or type(record) is not dict
            or canonical_json_sha256_v1(record) != carrier["source_record_sha256"]
            or _hierarchy_frontier_row_receipt_v1(record)
            != {"numbers": carrier["numbers"], "sample_ids": carrier["sample_ids"]}
        ):
            raise _error("one-edit hierarchy-frontier role result drifted")
    else:
        clusters = [
            item
            for item in evidence["internal_unassigned_numeric_clusters"]
            if item.get("cluster_id") == carrier["cluster_id"]
        ]
        if (
            len(clusters) != 1
            or canonical_json_sha256_v1(clusters[0]) != carrier["source_record_sha256"]
            or clusters[0].get("sample_ids") != carrier["sample_ids"]
            or clusters[0].get("page_sequence") != page_sequence
            or [item.get("line_ordinal") for item in clusters[0].get("same_row_label_evidence", [])]
            != carrier["source_line_indices"]
        ):
            raise _error("one-edit hierarchy-frontier cluster result drifted")
    for certificate in proof["numeric_cell_certificates"]:
        sample = sample_by_id.get(certificate["sample_id"])
        if (
            type(sample) is not dict
            or canonical_json_sha256_v1(sample) != certificate["numeric_sample_sha256"]
            or sample.get("page_sequence") != certificate["page_sequence"]
            or sample.get("line_ordinal") != certificate["source_line_index"]
            or sample.get("bbox") != certificate["bbox"]
            or not same_typed_json_v1(sample.get("crop_ref"), certificate["crop_ref"])
            or canonical_json_sha256_v1(
                _hierarchy_frontier_page_line_from_sample_v1(
                    sample,
                    certificate["vietocr_surface"],
                )
            )
            != certificate["page_line_sha256"]
            or sample.get("raw_prediction") != certificate["pp_surface"]
            or sample.get("parsed_token", {}).get("classification")
            != certificate["pp_classification"]
            or _hierarchy_frontier_number(sample) != certificate["number"]
        ):
            raise _error("one-edit hierarchy-frontier numeric sample drifted")
    certified_by_sample = {
        item["sample_id"]: item["number"] for item in proof["numeric_cell_certificates"]
    }
    certified_result = {"numbers": [certified_by_sample[item] for item in carrier["sample_ids"]]}
    certified_components = [
        {"numbers": [certified_by_sample[item] for item in binding["sample_ids"]]}
        for binding in proof["component_frontier_bindings"]
    ]
    if not occurrence_row_v2._direct_frontier_sum_is_exact(  # noqa: SLF001
        certified_result,
        certified_components,
    ):
        raise _error("one-edit hierarchy-frontier certified structural arithmetic drifted")
    target = occurrence_by_id.get(proof["target_occurrence_id"])
    if proof["target_kind"] == "COMPONENT":
        target_bindings = [
            item
            for item in proof["component_frontier_bindings"]
            if item["occurrence_id"] == proof["target_occurrence_id"]
        ]
        if (
            type(target) is not dict
            or not _is_one_edit(target["label_match"])
            or target["role"] != proof["target_role"]
            or len(target_bindings) != 1
            or proof["source_check"]["source_line_indices"]
            != target_bindings[0]["source_line_indices"]
        ):
            raise _error("one-edit hierarchy-frontier component target drifted")
    return receipt


def _validate_hierarchy_frontier_against_closure_axes_v1(
    value: Any,
    *,
    internal_unassigned_numeric_clusters: Any,
    numeric_sample_universe: Any,
    role_occurrences: Any,
) -> dict[str, Any]:
    """Rebind V4 to the exact occurrence/sample/cluster axes retained by closure."""

    receipt = _validate_hierarchy_frontier_result_v1(value)
    if any(
        type(axis) is not list
        for axis in (
            internal_unassigned_numeric_clusters,
            numeric_sample_universe,
            role_occurrences,
        )
    ):
        raise _error("one-edit hierarchy-frontier closure axes drifted")
    binding = receipt["input_binding"]
    if (
        binding["internal_unassigned_numeric_clusters_sha256"]
        != canonical_json_sha256_v1(internal_unassigned_numeric_clusters)
        or binding["numeric_sample_universe_sha256"]
        != canonical_json_sha256_v1(numeric_sample_universe)
        or binding["role_occurrences_sha256"] != canonical_json_sha256_v1(role_occurrences)
    ):
        raise _error("one-edit hierarchy-frontier closure input binding drifted")
    proof = receipt["hierarchy_direct_frontier_authority"]
    context = proof["column_context_receipt"]
    centers = [item["column_center"] for item in context["period_axis"]]
    lane_count = len(centers)
    occurrence_by_id = {
        item.get("occurrence_id"): item
        for item in role_occurrences
        if type(item) is dict and type(item.get("occurrence_id")) is str
    }
    sample_by_id = {
        item.get("sample_id"): item
        for item in numeric_sample_universe
        if type(item) is dict and type(item.get("sample_id")) is str
    }
    if (
        len(occurrence_by_id) != len(role_occurrences)
        or len(sample_by_id) != len(numeric_sample_universe)
        or lane_count == 0
        or [item["column_center"] for item in context["unit_axis"]] != centers
    ):
        raise _error("one-edit hierarchy-frontier closure identities repeat")
    component_visual_axis = []
    for component in proof["component_frontier_bindings"]:
        occurrence = occurrence_by_id.get(component["occurrence_id"])
        samples = [sample_by_id.get(item) for item in component["sample_ids"]]
        if (
            type(occurrence) is not dict
            or canonical_json_sha256_v1(occurrence) != component["role_occurrence_sha256"]
            or occurrence.get("role") != component["role"]
            or occurrence.get("retrieval_occurrence_id") != component["retrieval_occurrence_id"]
            or occurrence.get("scope_owner_occurrence_id") != proof["root_occurrence_id"]
            or occurrence.get("scope_owner_role") is not None
            or _hierarchy_frontier_source_line_indices(occurrence["label_match"])
            != component["source_line_indices"]
            or canonical_json_sha256_v1(
                list(
                    occurrence_row_v2._visual_match_key(  # noqa: SLF001
                        occurrence["label_match"]
                    )
                )
            )
            != component["visual_match_key_sha256"]
            or any(type(item) is not dict for item in samples)
            or [_hierarchy_frontier_number(item) for item in samples] != component["numbers"]
            or [item.get("column_ordinal") for item in samples] != list(range(lane_count))
            or [item.get("column_center") for item in samples] != centers
            or any(
                item.get("owner_kind") != "ROLE_OCCURRENCE"
                or item.get("owner_id") != component["occurrence_id"]
                or item.get("page_sequence") != proof["page_sequence"]
                for item in samples
            )
        ):
            raise _error("one-edit hierarchy-frontier closure component drifted")
        component_visual_axis.append(
            (occurrence_row_v2._visual_match_key(occurrence["label_match"]), component)  # noqa: SLF001
        )
    if len({item[0] for item in component_visual_axis}) != len(component_visual_axis) or any(
        component["source_visual_ordinal"] != ordinal
        for ordinal, (_key, component) in enumerate(
            sorted(component_visual_axis, key=lambda item: item[0])
        )
    ):
        raise _error("one-edit hierarchy-frontier closure visual order drifted")
    carrier = proof["result_carrier_binding"]
    result_samples = [sample_by_id.get(item) for item in carrier["sample_ids"]]
    if (
        any(type(item) is not dict for item in result_samples)
        or [_hierarchy_frontier_number(item) for item in result_samples] != carrier["numbers"]
        or [item.get("column_ordinal") for item in result_samples] != list(range(lane_count))
        or [item.get("column_center") for item in result_samples] != centers
        or any(item.get("page_sequence") != proof["page_sequence"] for item in result_samples)
    ):
        raise _error("one-edit hierarchy-frontier closure result samples drifted")
    component_ids = {item["occurrence_id"] for item in proof["component_frontier_bindings"]}
    result_occurrence_id = (
        carrier["occurrence_id"] if carrier["carrier_kind"] == "ROLE_OCCURRENCE" else None
    )
    direct_inventory = []
    for occurrence in role_occurrences:
        if (
            occurrence.get("scope_owner_occurrence_id") != proof["root_occurrence_id"]
            or occurrence.get("scope_owner_role") is not None
            or occurrence.get("label_match", {}).get("page_sequence") != proof["page_sequence"]
        ):
            continue
        owned_samples = [
            sample
            for sample in numeric_sample_universe
            if sample.get("owner_kind") == "ROLE_OCCURRENCE"
            and sample.get("owner_id") == occurrence["occurrence_id"]
        ]
        if occurrence["occurrence_id"] == result_occurrence_id:
            continue
        if occurrence.get("role_kind") in {"ADDITIVE_CHILD", "STRUCTURAL_GROUP"} or owned_samples:
            if (
                occurrence["occurrence_id"] not in component_ids
                or occurrence.get("has_bound_value_row") is not True
                or len(owned_samples) != lane_count
            ):
                raise _error("one-edit hierarchy-frontier closure direct inventory drifted")
            direct_inventory.append(occurrence["occurrence_id"])
    if set(direct_inventory) != component_ids or len(direct_inventory) != len(component_ids):
        raise _error("one-edit hierarchy-frontier closure frontier is not exhaustive")
    result_cluster = None
    if carrier["carrier_kind"] == "ROLE_OCCURRENCE":
        occurrence = occurrence_by_id.get(carrier["occurrence_id"])
        if (
            type(occurrence) is not dict
            or canonical_json_sha256_v1(occurrence) != carrier["role_occurrence_sha256"]
            or occurrence.get("role") != carrier["source_role"]
            or occurrence.get("scope_owner_occurrence_id") != proof["root_occurrence_id"]
            or any(
                item.get("owner_kind") != "ROLE_OCCURRENCE"
                or item.get("owner_id") != carrier["occurrence_id"]
                for item in result_samples
            )
        ):
            raise _error("one-edit hierarchy-frontier closure role result drifted")
    else:
        matches = [
            item
            for item in internal_unassigned_numeric_clusters
            if item.get("cluster_id") == carrier["cluster_id"]
        ]
        if (
            len(matches) != 1
            or canonical_json_sha256_v1(matches[0]) != carrier["source_record_sha256"]
            or matches[0].get("sample_ids") != carrier["sample_ids"]
            or any(
                item.get("owner_kind") != "SOURCE_ONLY_INTERNAL_CLUSTER"
                or item.get("owner_id") != carrier["cluster_id"]
                for item in result_samples
            )
        ):
            raise _error("one-edit hierarchy-frontier closure cluster result drifted")
        result_cluster = canonical_clone_v1(matches[0])
    for certificate in proof["numeric_cell_certificates"]:
        sample = sample_by_id.get(certificate["sample_id"])
        if (
            type(sample) is not dict
            or canonical_json_sha256_v1(sample) != certificate["numeric_sample_sha256"]
            or _hierarchy_frontier_number(sample) != certificate["number"]
            or sample.get("bbox") != certificate["bbox"]
            or not same_typed_json_v1(sample.get("crop_ref"), certificate["crop_ref"])
            or canonical_json_sha256_v1(
                _hierarchy_frontier_page_line_from_sample_v1(
                    sample,
                    certificate["vietocr_surface"],
                )
            )
            != certificate["page_line_sha256"]
            or sample.get("line_ordinal") != certificate["source_line_index"]
            or sample.get("raw_prediction") != certificate["pp_surface"]
            or sample.get("parsed_token", {}).get("classification")
            != certificate["pp_classification"]
        ):
            raise _error("one-edit hierarchy-frontier closure certificate drifted")
    if proof["target_kind"] == "COMPONENT":
        target_bindings = [
            item
            for item in proof["component_frontier_bindings"]
            if item["occurrence_id"] == proof["target_occurrence_id"]
        ]
        if (
            len(target_bindings) != 1
            or proof["source_check"]["source_line_indices"]
            != target_bindings[0]["source_line_indices"]
        ):
            raise _error("one-edit hierarchy-frontier closure target span drifted")
    certified_by_sample = {
        item["sample_id"]: item["number"] for item in proof["numeric_cell_certificates"]
    }
    if not occurrence_row_v2._direct_frontier_sum_is_exact(  # noqa: SLF001
        {"numbers": [certified_by_sample[item] for item in carrier["sample_ids"]]},
        [
            {"numbers": [certified_by_sample[item] for item in component["sample_ids"]]}
            for component in proof["component_frontier_bindings"]
        ],
    ):
        raise _error("one-edit hierarchy-frontier closure certified arithmetic drifted")
    return result_cluster


def project_accounting_family_one_edit_hierarchy_frontier_authority_v1(
    source_exact_authority_receipt: Any,
    structural_evidence: Any,
    column_context: Any,
    document_pages: Any,
    family_spec: Any,
    selected_topology_region: Any,
    hierarchy_spec: Any,
    *,
    column_context_document_pages: Any,
    period_semantics: Any,
    expected_lane_unit_kinds: Any,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Bind one source-visible hierarchy-declared root frontier, or abstain."""

    source = _validate_result(source_exact_authority_receipt)
    evidence = _parent_frontier_structural_evidence_v1(structural_evidence)
    try:
        context = column_context_multilevel_v2._validate_context_receipt_v2(  # noqa: SLF001
            column_context
        )
        pages = _pages_with_occurrence_geometry_v1(document_pages)
        compiled = topology_v1._spec(family_spec)  # noqa: SLF001
    except (ValueError, RuntimeError) as exc:
        raise _error("one-edit hierarchy-frontier authenticated input drifted") from exc
    if (
        type(selected_topology_region) is not dict
        or source["family_id"] != compiled["family_id"]
        or evidence["row_axis"]["family_id"] != compiled["family_id"]
        or context["family_id"] != compiled["family_id"]
        or source["input_binding"]["document_pages_sha256"]
        != canonical_json_sha256_v1(document_pages)
        or source["input_binding"]["family_spec_sha256"] != canonical_json_sha256_v1(family_spec)
        or source["input_binding"]["selected_topology_region_sha256"]
        != canonical_json_sha256_v1(selected_topology_region)
    ):
        raise _error("one-edit hierarchy-frontier source binding drifted")
    context = _validate_parent_frontier_column_context_replay_v1(
        context,
        row_axis=evidence["row_axis"],
        document_pages=column_context_document_pages,
        authority_pages=document_pages,
        family_spec=family_spec,
        period_semantics=period_semantics,
        expected_lane_unit_kinds=expected_lane_unit_kinds,
        visible_dash_rescues=visible_dash_rescues,
    )
    _compiled_hierarchy_frontier_equation_v1(hierarchy_spec, family_spec)
    column_policy = {
        "expected_lane_unit_kinds": canonical_clone_v1(expected_lane_unit_kinds),
        "period_semantics": period_semantics,
        "visible_dash_rescues_sha256": _visible_dash_rescues_sha256_v1(visible_dash_rescues),
    }
    input_binding = _hierarchy_frontier_input_binding_v1(
        source, evidence, context, hierarchy_spec, column_policy
    )
    proof = _build_hierarchy_frontier_proof_v1(
        source,
        evidence,
        context,
        pages,
        compiled,
        family_spec,
        selected_topology_region,
        hierarchy_spec,
        input_binding,
    )
    if proof is None:
        recursive_input_binding = _recursive_hierarchy_frontier_input_binding_v1(
            source,
            evidence,
            context,
            hierarchy_spec,
            column_policy,
        )
        recursive_proof = _build_recursive_hierarchy_frontier_proof_v1(
            source,
            evidence,
            context,
            family_spec,
            hierarchy_spec,
            recursive_input_binding,
        )
        if recursive_proof is None:
            return canonical_clone_v1(source)
        source_reason = _parent_frontier_reason(recursive_proof["source_check"])
        reasons = [reason for reason in source["unresolved_reasons"] if reason != source_reason]
        material = {
            "authority_spec": {
                "sha256": canonical_json_sha256_v1(_RECURSIVE_HIERARCHY_FRONTIER_AUTHORITY_SPEC),
                "value": canonical_clone_v1(_RECURSIVE_HIERARCHY_FRONTIER_AUTHORITY_SPEC),
            },
            "checks": canonical_clone_v1(source["checks"]),
            "claim_boundary": RECURSIVE_HIERARCHY_FRONTIER_CLAIM_BOUNDARY,
            "family_id": compiled["family_id"],
            "format_version": RECURSIVE_HIERARCHY_FRONTIER_FORMAT_VERSION,
            "input_binding": recursive_input_binding,
            "metrics": {
                "exact_bound_count": source["metrics"]["exact_bound_count"] + 1,
                "selected_one_edit_match_count": source["metrics"]["selected_one_edit_match_count"],
                "unresolved_match_count": source["metrics"]["unresolved_match_count"] - 1,
            },
            "recursive_hierarchy_direct_frontier_authority": recursive_proof,
            "safety": canonical_clone_v1(_RECURSIVE_HIERARCHY_FRONTIER_SAFETY),
            "source_exact_authority_receipt": canonical_clone_v1(source),
            "status": (
                "EXACT_SOURCE_AUTHORITY_BOUND"
                if not reasons
                else "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY"
            ),
            "unresolved_reasons": reasons,
        }
        persisted = {
            **material,
            "receipt_id": "afeoeav1:receipt:" + canonical_json_sha256_v1(material),
        }
        return _validate_recursive_hierarchy_frontier_against_structural_evidence_v1(
            persisted,
            evidence,
        )
    source_reason = _parent_frontier_reason(proof["source_check"])
    reasons = [reason for reason in source["unresolved_reasons"] if reason != source_reason]
    material = {
        "authority_spec": {
            "sha256": canonical_json_sha256_v1(_HIERARCHY_FRONTIER_AUTHORITY_SPEC),
            "value": canonical_clone_v1(_HIERARCHY_FRONTIER_AUTHORITY_SPEC),
        },
        "checks": canonical_clone_v1(source["checks"]),
        "claim_boundary": HIERARCHY_FRONTIER_CLAIM_BOUNDARY,
        "family_id": compiled["family_id"],
        "format_version": HIERARCHY_FRONTIER_FORMAT_VERSION,
        "hierarchy_direct_frontier_authority": proof,
        "input_binding": input_binding,
        "metrics": {
            "exact_bound_count": source["metrics"]["exact_bound_count"] + 1,
            "selected_one_edit_match_count": source["metrics"]["selected_one_edit_match_count"],
            "unresolved_match_count": source["metrics"]["unresolved_match_count"] - 1,
        },
        "safety": canonical_clone_v1(_HIERARCHY_FRONTIER_SAFETY),
        "source_exact_authority_receipt": canonical_clone_v1(source),
        "status": (
            "EXACT_SOURCE_AUTHORITY_BOUND"
            if not reasons
            else "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY"
        ),
        "unresolved_reasons": reasons,
    }
    persisted = {
        **material,
        "receipt_id": "afeoeav1:receipt:" + canonical_json_sha256_v1(material),
    }
    return _validate_hierarchy_frontier_against_structural_evidence_v1(
        persisted,
        evidence,
    )


def hierarchy_frontier_bound_retrieval_occurrence_ids_v1(
    value: Any,
    *,
    structural_evidence: Any,
    family_spec: Any = None,
    hierarchy_spec: Any = None,
) -> set[str]:
    """Return only component retrieval IDs sealed by one replayed hierarchy proof."""

    receipt = validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(value)
    if receipt["format_version"] == RECURSIVE_HIERARCHY_FRONTIER_FORMAT_VERSION:
        _validate_recursive_hierarchy_frontier_against_structural_evidence_v1(
            receipt,
            structural_evidence,
            family_spec=family_spec,
            hierarchy_spec=hierarchy_spec,
        )
        return {
            receipt["recursive_hierarchy_direct_frontier_authority"]["recursive_frontier"][
                "target_retrieval_occurrence_id"
            ]
        }
    if receipt["format_version"] != HIERARCHY_FRONTIER_FORMAT_VERSION:
        return set()
    _validate_hierarchy_frontier_against_structural_evidence_v1(receipt, structural_evidence)
    proof = receipt["hierarchy_direct_frontier_authority"]
    if proof["target_kind"] != "COMPONENT":
        return set()
    return {
        item["retrieval_occurrence_id"]
        for item in proof["component_frontier_bindings"]
        if item["occurrence_id"] == proof["target_occurrence_id"]
    }


def hierarchy_frontier_certified_sample_ids_v1(
    value: Any,
    *,
    structural_evidence: Any,
) -> set[str]:
    """Return source samples whose V4 crop/reader bindings were sealed."""

    receipt = validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(value)
    if receipt["format_version"] == RECURSIVE_HIERARCHY_FRONTIER_FORMAT_VERSION:
        _validate_recursive_hierarchy_frontier_against_structural_evidence_v1(
            receipt, structural_evidence
        )
        return set(
            receipt["recursive_hierarchy_direct_frontier_authority"]["recursive_frontier"][
                "covered_source_sample_ids"
            ]
        )
    if receipt["format_version"] != HIERARCHY_FRONTIER_FORMAT_VERSION:
        return set()
    _validate_hierarchy_frontier_against_structural_evidence_v1(receipt, structural_evidence)
    return {
        item["sample_id"]
        for item in receipt["hierarchy_direct_frontier_authority"]["numeric_cell_certificates"]
    }


def hierarchy_frontier_result_cluster_v1(
    value: Any,
    *,
    structural_evidence: Any,
) -> dict[str, Any] | None:
    """Return the sole V4 labeled parent-result cluster, when that is the carrier."""

    receipt = validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(value)
    if receipt["format_version"] != HIERARCHY_FRONTIER_FORMAT_VERSION:
        return None
    evidence = _parent_frontier_structural_evidence_v1(structural_evidence)
    _validate_hierarchy_frontier_against_structural_evidence_v1(receipt, evidence)
    carrier = receipt["hierarchy_direct_frontier_authority"]["result_carrier_binding"]
    if carrier["carrier_kind"] != "LABELED_PARENT_CLUSTER":
        return None
    matches = [
        item
        for item in evidence["internal_unassigned_numeric_clusters"]
        if item.get("cluster_id") == carrier["cluster_id"]
    ]
    if len(matches) != 1:
        raise _error("one-edit hierarchy-frontier result cluster is not unique")
    return canonical_clone_v1(matches[0])


def family_parent_has_exact_authority_v1(
    value: Any,
    *,
    structural_evidence: Any = None,
) -> bool:
    """Return whether the selected family parent has one replayable authority."""

    receipt = validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(value)
    if any(
        check["match_scope"] == "FAMILY_PARENT" and check["status"] in _BOUND_CHECK_STATUSES
        for check in receipt["checks"]
    ):
        return True
    if receipt["format_version"] != PARENT_FRONTIER_FORMAT_VERSION:
        if receipt["format_version"] == RECURSIVE_HIERARCHY_FRONTIER_FORMAT_VERSION:
            return False
        if receipt["format_version"] != HIERARCHY_FRONTIER_FORMAT_VERSION:
            return False
        if structural_evidence is None:
            return False
        _validate_hierarchy_frontier_against_structural_evidence_v1(receipt, structural_evidence)
        proof = receipt["hierarchy_direct_frontier_authority"]
        return (
            proof["target_kind"] == "FAMILY_PARENT"
            and proof["status"] == _HIERARCHY_FRONTIER_BOUND_STATUS
        )
    if structural_evidence is None:
        return False
    _validate_parent_frontier_against_structural_evidence_v1(receipt, structural_evidence)
    return receipt["parent_frontier_authority"]["status"] == _PARENT_FRONTIER_BOUND_STATUS


def _build_from_canonical_expanded_occurrences_v1(
    pages: Sequence[Mapping[str, Any]],
    compiled: Mapping[str, Any],
    *,
    document_pages: Any,
    family_spec: Any,
    selected_topology_region: Mapping[str, Any],
    expanded_occurrence_region: Mapping[str, Any],
    prepared_source_exact_axis_cache: dict[tuple[str, str], Any] | None = None,
) -> dict[str, Any]:
    """Build the receipt from one already canonical retrieval occurrence axis.

    Occurrence V2 uses this low-level primitive before its schema projector.
    It deliberately performs no occurrence replay of its own, avoiding a
    private replay cycle; the caller supplies an axis it has just derived from
    the same canonical pages/spec/selected region.  The public builder below
    still independently replays that axis before entering this primitive.
    """

    _validate_canonical_expanded_occurrence_axis_v1(
        expanded_occurrence_region,
        selected_topology_region,
    )
    selected_parent = selected_topology_region.get("parent_match")
    effective_matches = expanded_occurrence_region["child_matches"]
    occurrence_ids = [
        match.get("occurrence_id") if type(match) is dict else None for match in effective_matches
    ]
    if (
        any(type(occurrence_id) is not str or not occurrence_id for occurrence_id in occurrence_ids)
        or len(occurrence_ids) != len(set(occurrence_ids))
        or any(
            type(match.get("scope_owner_occurrence_id")) is not str
            or not match["scope_owner_occurrence_id"]
            or match.get("matched_within_role") != match.get("scope_owner_role")
            or (
                match.get("scope_owner_role") is not None
                and (type(match["scope_owner_role"]) is not str or not match["scope_owner_role"])
            )
            for match in effective_matches
        )
    ):
        raise _error("one-edit exact-authority expanded occurrence identity axis drifted")
    occurrence_by_id = {match["occurrence_id"]: match for match in effective_matches}
    if any(
        match["scope_owner_role"] is not None
        and (
            match["scope_owner_occurrence_id"] not in occurrence_by_id
            or occurrence_by_id[match["scope_owner_occurrence_id"]].get("role")
            != match["scope_owner_role"]
        )
        for match in effective_matches
    ):
        raise _error("one-edit exact-authority expanded structural-owner axis drifted")
    selected_matches: list[tuple[str, Mapping[str, Any]]] = []
    if selected_parent is not None and _is_one_edit(selected_parent):
        selected_matches.append(("FAMILY_PARENT", selected_parent))
    selected_matches.extend(
        ("EXPANDED_OCCURRENCE", match) for match in effective_matches if _is_one_edit(match)
    )
    checks = []
    # Exact-source discovery is deliberately expensive because it scans the
    # complete authenticated document axis.  With no selected one-edit
    # retrieval there is no authority claim to prove, so scanning that axis
    # cannot affect the canonical NOT_REQUIRED receipt.  Keeping the scan
    # strictly inside this branch preserves full replay for every real claim
    # while avoiding the same whole-document pass for exact-only candidates.
    if selected_matches:
        exact_hits = _same_turn_exact_source_hits_v1(
            pages,
            compiled,
            document_pages=document_pages,
            family_spec=family_spec,
            prepared_axis_cache=prepared_source_exact_axis_cache,
        )
        source_occurrences = _decorate_exact_source_occurrences_v1(
            _context_bound_source_records(
                exact_hits,
                compiled,
                selected_topology_region,
            ),
            pages,
            selected_topology_region,
        )
        for match_scope, match in selected_matches:
            role = (
                compiled["parent"]["role"] if match_scope == "FAMILY_PARENT" else match.get("role")
            )
            within_role = (
                None if match_scope == "FAMILY_PARENT" else match.get("matched_within_role")
            )
            checks.append(
                _check(
                    match,
                    aliases=_alias_entries(compiled, role=role, within_role=within_role),
                    compiled=compiled,
                    effective_matches=effective_matches,
                    exact_hits=exact_hits,
                    pages=pages,
                    selected_region=selected_topology_region,
                    source_occurrences=source_occurrences,
                    match_scope=match_scope,
                )
            )
    bound = sum(check["status"] in _BOUND_CHECK_STATUSES for check in checks)
    metrics = {
        "exact_bound_count": bound,
        "selected_one_edit_match_count": len(checks),
        "unresolved_match_count": len(checks) - bound,
    }
    reasons = [
        (
            f"ONE_EDIT_EXACT_AUTHORITY:{check['status']}:{check['role']}:"
            f"OCCURRENCE_{check['occurrence_id'] or 'FAMILY_PARENT'}:"
            f"PAGE_{check['page_sequence']}:LINES_"
            + ",".join(str(index) for index in check["source_line_indices"])
        )
        for check in checks
        if check["status"] not in _BOUND_CHECK_STATUSES
    ]
    material = {
        "authority_spec": {
            "sha256": canonical_json_sha256_v1(_AUTHORITY_SPEC),
            "value": canonical_clone_v1(_AUTHORITY_SPEC),
        },
        "checks": checks,
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": compiled["family_id"],
        "format_version": FORMAT_VERSION,
        "input_binding": {
            "document_pages_sha256": canonical_json_sha256_v1(document_pages),
            "expanded_occurrence_region_sha256": canonical_json_sha256_v1(
                expanded_occurrence_region
            ),
            "family_spec_sha256": canonical_json_sha256_v1(family_spec),
            "selected_topology_region_sha256": canonical_json_sha256_v1(selected_topology_region),
        },
        "metrics": metrics,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "NOT_REQUIRED_NO_SELECTED_ONE_EDIT_RETRIEVAL"
            if not checks
            else "EXACT_SOURCE_AUTHORITY_BOUND"
            if not reasons
            else "UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY"
        ),
        "unresolved_reasons": reasons,
    }
    return _validate_result(
        {
            **material,
            "receipt_id": "afeoeav1:receipt:" + canonical_json_sha256_v1(material),
        }
    )


def build_accounting_family_one_edit_exact_authority_v1(
    document_pages: Any,
    family_spec: Any,
    selected_topology_region: Any,
    expanded_occurrence_region: Any,
    *,
    _prepared_source_exact_axis_cache: dict[tuple[str, str], Any] | None = None,
) -> dict[str, Any]:
    """Gate one selected V4 candidate and every expanded role occurrence."""

    try:
        pages = _pages_with_occurrence_geometry_v1(document_pages)
        compiled = topology_v1._spec(family_spec)  # noqa: SLF001
    except (ValueError, RuntimeError) as exc:
        raise _error("one-edit exact-authority document or family spec drifted") from exc
    if type(selected_topology_region) is not dict or type(expanded_occurrence_region) is not dict:
        raise _error("one-edit exact-authority selected/expanded region binding drifted")
    canonical_expanded_occurrence_region = _canonical_expanded_occurrence_region_v1(
        pages,
        family_spec,
        selected_topology_region,
    )
    if not same_typed_json_v1(
        expanded_occurrence_region,
        canonical_expanded_occurrence_region,
    ):
        raise _error("expanded occurrence region does not replay exactly")
    # Never derive authority from the caller-owned object, even after the
    # typed comparison.  All later checks and hashes consume the replayed axis.
    return _build_from_canonical_expanded_occurrences_v1(
        pages,
        compiled,
        document_pages=document_pages,
        family_spec=family_spec,
        selected_topology_region=selected_topology_region,
        expanded_occurrence_region=canonical_expanded_occurrence_region,
        prepared_source_exact_axis_cache=_prepared_source_exact_axis_cache,
    )


def validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(
    value: Any,
) -> dict[str, Any]:
    """Validate a closed receipt and all of its internal content hashes."""

    if type(value) is dict and value.get("format_version") == PARENT_FRONTIER_FORMAT_VERSION:
        return _validate_parent_frontier_result_v1(value)
    if type(value) is dict and value.get("format_version") == HIERARCHY_FRONTIER_FORMAT_VERSION:
        return _validate_hierarchy_frontier_result_v1(value)
    if (
        type(value) is dict
        and value.get("format_version") == RECURSIVE_HIERARCHY_FRONTIER_FORMAT_VERSION
    ):
        return _validate_recursive_hierarchy_frontier_result_v1(value)
    return _validate_result(value)


def validate_accounting_family_one_edit_exact_authority_replay_v1(
    value: Any,
    document_pages: Any,
    family_spec: Any,
    selected_topology_region: Any,
    expanded_occurrence_region: Any,
    *,
    structural_evidence: Any = None,
    column_context: Any = None,
    column_context_document_pages: Any = None,
    period_semantics: Any = None,
    expected_lane_unit_kinds: Any = None,
    visible_dash_rescues: Any = (),
    hierarchy_spec: Any = None,
) -> dict[str, Any]:
    """Exact-rebuild a receipt from bound source text and the selected region."""

    persisted = validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(value)
    source_expected = build_accounting_family_one_edit_exact_authority_v1(
        document_pages,
        family_spec,
        selected_topology_region,
        expanded_occurrence_region,
    )
    expected = (
        project_accounting_family_one_edit_parent_frontier_authority_v1(
            source_expected,
            structural_evidence,
            column_context,
            document_pages,
            family_spec,
            selected_topology_region,
            column_context_document_pages=column_context_document_pages,
            period_semantics=period_semantics,
            expected_lane_unit_kinds=expected_lane_unit_kinds,
            visible_dash_rescues=visible_dash_rescues,
        )
        if persisted["format_version"] == PARENT_FRONTIER_FORMAT_VERSION
        else project_accounting_family_one_edit_hierarchy_frontier_authority_v1(
            source_expected,
            structural_evidence,
            column_context,
            document_pages,
            family_spec,
            selected_topology_region,
            hierarchy_spec,
            column_context_document_pages=column_context_document_pages,
            period_semantics=period_semantics,
            expected_lane_unit_kinds=expected_lane_unit_kinds,
            visible_dash_rescues=visible_dash_rescues,
        )
        if persisted["format_version"]
        in {
            HIERARCHY_FRONTIER_FORMAT_VERSION,
            RECURSIVE_HIERARCHY_FRONTIER_FORMAT_VERSION,
        }
        else source_expected
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("one-edit exact-authority receipt does not replay exactly")
    return persisted
