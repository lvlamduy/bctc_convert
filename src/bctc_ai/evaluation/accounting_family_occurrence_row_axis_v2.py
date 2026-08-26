"""Opt-in occurrence-aware projection over the sealed family row axis V1.

Topology discovery deliberately keeps one hit per semantic role.  A stacked
accounting table may nevertheless repeat the same child role under several
visible local parents.  This add-only adapter expands only occurrences that
the shared topology engine can replay inside the already selected region.  It
then delegates all row/lane geometry to the sealed V1 primitive.

The adapter also closes two narrow numeric evidence gaps.  A PP-OCR token whose
surface parses as ``DASH_ZERO`` is retained only after the committed
selected-snapshot/exact-page-render pixel bridge proves a visible dash glyph.
For V4 only, one unresolved detector-hole crop may additionally be promoted by
a versioned receipt proving exactly one material dash plus only isolated tiny
off-baseline scan specks.  This is not split-glyph authority, and sealed row
axis V1 remains unchanged.
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
from itertools import product
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter

from bctc_ai.evaluation import accounting_family_coextensive_parent_total_v1 as total_v1
from bctc_ai.evaluation import accounting_family_column_context_v1 as column_context_v1
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_v1
from bctc_ai.evaluation import accounting_family_topology_candidates_v2 as candidates_v2
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import accounting_printed_note_reference_axis_v1 as note_axis_v1
from bctc_ai.evaluation import authenticated_semantic_region_snapshot_v1 as snapshot_v1
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as render_v1
from bctc_ai.evaluation import family_first_authenticated_snapshot_cell_dash_v1 as dash_v1
from bctc_ai.evaluation import family_first_authenticated_unique_dash_speck_v1 as speck_dash_v1
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
    "project_accounting_family_one_edit_parent_frontier_authority_v2",
    "project_accounting_family_one_edit_hierarchy_frontier_authority_v2",
    "validate_accounting_family_occurrence_row_axis_replay_v2",
]


FORMAT_VERSION = "ACCOUNTING_FAMILY_OCCURRENCE_ROW_AXIS_V2"
POLICY_FORMAT_VERSION = "ACCOUNTING_FAMILY_OCCURRENCE_ROW_AXIS_POLICY_V1"
CLAIM_BOUNDARY = (
    "EXACT_SELECTED_TOPOLOGY_REGION_CONTEXT_BOUND_ROLE_OCCURRENCE_EXPANSION_"
    "UNIQUE_EXACT_BOUND_SOURCE_CONTEXTUAL_ADDITIVE_CHALLENGER_UNDER_SELECTED_"
    "EXACT_STRUCTURAL_OWNER_"
    "SEALED_V1_ROW_GEOMETRY_AUTHENTICATED_EXISTING_CELL_PIXEL_DASH_GATE_AND_"
    "AUTHENTICATED_V4_UNIQUE_MATERIAL_DASH_PLUS_ISOLATED_TINY_SCAN_SPECK_GATE_"
    "EXACT_PRECEDING_SCOPE_SUBTOTAL_SOURCE_OWNERSHIP_AND_REVIEWED_EXACT_"
    "SOURCE_SUBSCOPE_INTERVAL_SCHEMA_ROLE_TYPING_"
    "AUTHENTICATED_EXTREME_MARGIN_CHROMATIC_FURNITURE_NUMERIC_DENOMINATOR_"
    "AUTHENTICATED_PRINTED_NOTE_REFERENCE_FURNITURE_NUMERIC_DENOMINATOR_"
    "PROPOSAL_ONLY_NO_ACCOUNTING_PERIOD_UNIT_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "accounting_authority": False,
    "bank_file_page_period_scope_used_for_routing": False,
    "bound_source_challenger_may_create_structural_owner": False,
    "bound_source_challenger_requires_exact_retrieved_structural_owner": True,
    "bound_source_challenger_requires_exact_recursive_owner_chain": True,
    "bound_source_challenger_requires_otherwise_absent_contextual_additive_role": True,
    "bound_source_challenger_requires_unique_declared_alias_and_physical_row": True,
    "detector_hole_dash_authority_changed": False,
    "detector_hole_unique_dash_speck_requires_exact_occurrence_parent_lane": True,
    "existing_dash_text_alone_means_zero": False,
    "extreme_margin_furniture_requires_authenticated_exact_page_pixels": True,
    "extreme_margin_numeric_may_be_silently_deleted": False,
    "printed_note_reference_requires_exact_header_row_and_page_pixels": True,
    "printed_note_reference_numeric_may_be_silently_deleted": False,
    "mapping_authority": False,
    "occurrences_may_cross_selected_topology_region": False,
    "preceding_numeric_source_ambiguous_ownership_can_resolve": False,
    "preceding_scope_subtotal_may_be_reused_by_next_structural_group": False,
    "repeated_roles_may_be_silently_collapsed": False,
    "schema_authority": False,
    "schema_role_typing_requires_exact_source_scope_receipt": True,
    "sealed_row_axis_v1_bytes_changed": False,
    "split_dash_glyph_authority": False,
    "source_channel_can_participate_in_topology_retrieval": False,
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
    "authenticated_unique_dash_speck_evidence",
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
_ONE_EDIT_COMPLEMENTARY_BOUND_STATUS = "SAME_CROP_COMPLEMENTARY_EXACT_TOKEN_ALIAS_BOUND"
_ONE_EDIT_AUTHORITY_BOUND_STATUSES = {
    _ONE_EDIT_COMPLEMENTARY_BOUND_STATUS,
    _ONE_EDIT_EXACT_BOUND_STATUS,
}
_EXACT_BOUND_SOURCE_CONTEXT_CHALLENGER_MATCH_KIND = (
    "EXACT_ACCENTLESS_BOUND_SOURCE_TEXT_CHALLENGER_ALIAS"
)
_DISCOUNT_GENERIC_ROLE = "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
_DISCOUNT_SCOPE_TARGETS = {
    "INTERBANK_LOAN_VND": "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND",
    "INTERBANK_LOAN_FOREIGN_CURRENCY": ("INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY"),
}
_PROVISION_GENERIC_ROLE = "INTERBANK_PROVISION_AMBIGUOUS"
_COEXTENSIVE_TABLE_SECTION_ORDINAL = re.compile(r"[IVXLCDM]+[.)]?", re.IGNORECASE)
_RECURSIVE_PARENT_PROVISION_BINDING_KIND = "UNIQUE_EXACT_RECURSIVE_PARENT_DIRECT_FRONTIER_EQUATION"
_RECURSIVE_PARENT_PROVISION_EQUATION_STATUS = "EXACT_ORDERED_DIRECT_COMPONENT_FRONTIER_CORROBORATED"
_RECURSIVE_PARENT_PROVISION_GEOMETRY_STATUS = "EXACT_VISUAL_PARENT_INTERVAL_AND_DIRECT_FRONTIER"
_RECURSIVE_PARENT_PROVISION_BINDING_SPECS = (
    {
        "direct_component_descendant_roles": (
            (
                "DEMAND_DEPOSIT_GROUP",
                (
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    "DEMAND_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",
                    "DEMAND_DEPOSIT_VND",
                ),
            ),
            (
                "TERM_DEPOSIT_GROUP",
                (
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    "TERM_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",
                    "TERM_DEPOSIT_VND",
                ),
            ),
            ("INTERBANK_DEPOSIT_OTHER", ()),
            ("INTERBANK_DEPOSIT_PROVISION", ()),
        ),
        "direct_component_role_alternatives": (
            (
                "DEMAND_DEPOSIT_GROUP",
                "TERM_DEPOSIT_GROUP",
                "INTERBANK_DEPOSIT_PROVISION",
            ),
            ("DEMAND_DEPOSIT_GROUP", "INTERBANK_DEPOSIT_PROVISION"),
            ("TERM_DEPOSIT_GROUP", "INTERBANK_DEPOSIT_PROVISION"),
            ("INTERBANK_DEPOSIT_OTHER", "INTERBANK_DEPOSIT_PROVISION"),
            (
                "DEMAND_DEPOSIT_GROUP",
                "TERM_DEPOSIT_GROUP",
                "INTERBANK_DEPOSIT_OTHER",
                "INTERBANK_DEPOSIT_PROVISION",
            ),
        ),
        "matched_within_role": "INTERBANK_DEPOSIT_GROUP",
        "parent_role": "INTERBANK_DEPOSIT_GROUP",
        "result_roles": (
            "INTERBANK_DEPOSIT_GROUP",
            "EXPLICIT_INTERBANK_DEPOSIT_TOTAL",
        ),
        "target_role": "INTERBANK_DEPOSIT_PROVISION",
    },
    {
        "direct_component_descendant_roles": (
            (
                "INTERBANK_LOAN_VND",
                (
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS",
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND",
                    "INTERBANK_LOAN_GOLD_AND_FOREIGN_CURRENCY",
                ),
            ),
            (
                "INTERBANK_LOAN_FOREIGN_CURRENCY",
                (
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS",
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY",
                    "INTERBANK_LOAN_GOLD_AND_FOREIGN_CURRENCY",
                ),
            ),
            ("INTERBANK_LOAN_OTHER", ()),
            ("INTERBANK_LOAN_PROVISION", ()),
        ),
        "direct_component_role_alternatives": (
            (
                "INTERBANK_LOAN_VND",
                "INTERBANK_LOAN_FOREIGN_CURRENCY",
                "INTERBANK_LOAN_PROVISION",
            ),
            ("INTERBANK_LOAN_VND", "INTERBANK_LOAN_PROVISION"),
            ("INTERBANK_LOAN_FOREIGN_CURRENCY", "INTERBANK_LOAN_PROVISION"),
            ("INTERBANK_LOAN_OTHER", "INTERBANK_LOAN_PROVISION"),
            (
                "INTERBANK_LOAN_VND",
                "INTERBANK_LOAN_FOREIGN_CURRENCY",
                "INTERBANK_LOAN_OTHER",
                "INTERBANK_LOAN_PROVISION",
            ),
        ),
        "matched_within_role": "INTERBANK_LOAN_GROUP",
        "parent_role": "INTERBANK_LOAN_GROUP",
        "result_roles": (
            "INTERBANK_LOAN_GROUP",
            "EXPLICIT_INTERBANK_LOAN_TOTAL",
        ),
        "target_role": "INTERBANK_LOAN_PROVISION",
    },
    {
        "direct_component_descendant_roles": (
            (
                "INTERBANK_DEPOSIT_GROUP",
                (
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    "DEMAND_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",
                    "DEMAND_DEPOSIT_GROUP",
                    "DEMAND_DEPOSIT_VND",
                    "INTERBANK_DEPOSIT_OTHER",
                    "INTERBANK_DEPOSIT_PROVISION",
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    "TERM_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",
                    "TERM_DEPOSIT_GROUP",
                    "TERM_DEPOSIT_VND",
                ),
            ),
            (
                "INTERBANK_LOAN_GROUP",
                (
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS",
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY",
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND",
                    "INTERBANK_LOAN_FOREIGN_CURRENCY",
                    "INTERBANK_LOAN_GOLD_AND_FOREIGN_CURRENCY",
                    "INTERBANK_LOAN_OTHER",
                    "INTERBANK_LOAN_PROVISION",
                    "INTERBANK_LOAN_VND",
                ),
            ),
            ("TOTAL_INTERBANK_PROVISION", ()),
        ),
        "direct_component_role_alternatives": (
            (
                "INTERBANK_DEPOSIT_GROUP",
                "INTERBANK_LOAN_GROUP",
                "TOTAL_INTERBANK_PROVISION",
            ),
        ),
        "matched_within_role": None,
        "parent_role": None,
        "result_roles": ("EXPLICIT_FAMILY_TOTAL",),
        "target_role": "TOTAL_INTERBANK_PROVISION",
    },
)
_RECURSIVE_PARENT_DIRECT_COMPONENT_SUPPORT_SPECS = (
    {
        "component_role_alternatives": (
            ("DEMAND_DEPOSIT_VND", "DEMAND_DEPOSIT_FOREIGN_CURRENCY"),
            ("DEMAND_DEPOSIT_VND",),
            ("DEMAND_DEPOSIT_FOREIGN_CURRENCY",),
        ),
        "direct_component_descendant_roles": (
            ("DEMAND_DEPOSIT_VND", ("DEMAND_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",)),
            (
                "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                ("DEMAND_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",),
            ),
        ),
        "result_role": "DEMAND_DEPOSIT_GROUP",
    },
    {
        "component_role_alternatives": (
            ("TERM_DEPOSIT_VND", "TERM_DEPOSIT_FOREIGN_CURRENCY"),
            ("TERM_DEPOSIT_VND",),
            ("TERM_DEPOSIT_FOREIGN_CURRENCY",),
        ),
        "direct_component_descendant_roles": (
            ("TERM_DEPOSIT_VND", ("TERM_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",)),
            (
                "TERM_DEPOSIT_FOREIGN_CURRENCY",
                ("TERM_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",),
            ),
        ),
        "result_role": "TERM_DEPOSIT_GROUP",
    },
    {
        "component_role_alternatives": (
            ("DEMAND_DEPOSIT_GROUP", "TERM_DEPOSIT_GROUP"),
            (
                "DEMAND_DEPOSIT_GROUP",
                "TERM_DEPOSIT_GROUP",
                "INTERBANK_DEPOSIT_PROVISION",
            ),
            (
                "DEMAND_DEPOSIT_GROUP",
                "TERM_DEPOSIT_GROUP",
                "INTERBANK_DEPOSIT_OTHER",
            ),
            (
                "DEMAND_DEPOSIT_GROUP",
                "TERM_DEPOSIT_GROUP",
                "INTERBANK_DEPOSIT_PROVISION",
                "INTERBANK_DEPOSIT_OTHER",
            ),
            ("DEMAND_DEPOSIT_GROUP",),
            ("TERM_DEPOSIT_GROUP",),
            ("DEMAND_DEPOSIT_GROUP", "INTERBANK_DEPOSIT_PROVISION"),
            ("TERM_DEPOSIT_GROUP", "INTERBANK_DEPOSIT_PROVISION"),
            ("INTERBANK_DEPOSIT_OTHER",),
            ("INTERBANK_DEPOSIT_OTHER", "INTERBANK_DEPOSIT_PROVISION"),
            ("DEMAND_DEPOSIT_GROUP", "INTERBANK_DEPOSIT_OTHER"),
            ("TERM_DEPOSIT_GROUP", "INTERBANK_DEPOSIT_OTHER"),
            (
                "DEMAND_DEPOSIT_GROUP",
                "INTERBANK_DEPOSIT_PROVISION",
                "INTERBANK_DEPOSIT_OTHER",
            ),
            (
                "TERM_DEPOSIT_GROUP",
                "INTERBANK_DEPOSIT_PROVISION",
                "INTERBANK_DEPOSIT_OTHER",
            ),
        ),
        "direct_component_descendant_roles": (
            (
                "DEMAND_DEPOSIT_GROUP",
                (
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    "DEMAND_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",
                    "DEMAND_DEPOSIT_VND",
                ),
            ),
            (
                "TERM_DEPOSIT_GROUP",
                (
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    "TERM_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",
                    "TERM_DEPOSIT_VND",
                ),
            ),
            ("INTERBANK_DEPOSIT_PROVISION", ()),
            ("INTERBANK_DEPOSIT_OTHER", ()),
        ),
        "result_role": "INTERBANK_DEPOSIT_GROUP",
    },
    {
        "component_role_alternatives": (
            ("INTERBANK_LOAN_VND", "INTERBANK_LOAN_FOREIGN_CURRENCY"),
            (
                "INTERBANK_LOAN_VND",
                "INTERBANK_LOAN_FOREIGN_CURRENCY",
                "INTERBANK_LOAN_PROVISION",
            ),
            (
                "INTERBANK_LOAN_VND",
                "INTERBANK_LOAN_FOREIGN_CURRENCY",
                "INTERBANK_LOAN_OTHER",
            ),
            (
                "INTERBANK_LOAN_VND",
                "INTERBANK_LOAN_FOREIGN_CURRENCY",
                "INTERBANK_LOAN_PROVISION",
                "INTERBANK_LOAN_OTHER",
            ),
            ("INTERBANK_LOAN_VND",),
            ("INTERBANK_LOAN_FOREIGN_CURRENCY",),
            ("INTERBANK_LOAN_VND", "INTERBANK_LOAN_PROVISION"),
            ("INTERBANK_LOAN_FOREIGN_CURRENCY", "INTERBANK_LOAN_PROVISION"),
            ("INTERBANK_LOAN_OTHER",),
            ("INTERBANK_LOAN_OTHER", "INTERBANK_LOAN_PROVISION"),
            ("INTERBANK_LOAN_VND", "INTERBANK_LOAN_OTHER"),
            ("INTERBANK_LOAN_FOREIGN_CURRENCY", "INTERBANK_LOAN_OTHER"),
            (
                "INTERBANK_LOAN_VND",
                "INTERBANK_LOAN_PROVISION",
                "INTERBANK_LOAN_OTHER",
            ),
            (
                "INTERBANK_LOAN_FOREIGN_CURRENCY",
                "INTERBANK_LOAN_PROVISION",
                "INTERBANK_LOAN_OTHER",
            ),
        ),
        "direct_component_descendant_roles": (
            (
                "INTERBANK_LOAN_VND",
                (
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS",
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND",
                    "INTERBANK_LOAN_GOLD_AND_FOREIGN_CURRENCY",
                ),
            ),
            (
                "INTERBANK_LOAN_FOREIGN_CURRENCY",
                (
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS",
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY",
                    "INTERBANK_LOAN_GOLD_AND_FOREIGN_CURRENCY",
                ),
            ),
            ("INTERBANK_LOAN_PROVISION", ()),
            ("INTERBANK_LOAN_OTHER", ()),
        ),
        "result_role": "INTERBANK_LOAN_GROUP",
    },
)
_RECURSIVE_PARENT_OWNER_BOUND_NONADDITIVE_EXCLUSIONS = {
    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY",
    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND",
}
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
_EXTREME_MARGIN_FURNITURE_V2_STATUS = (
    "AUTHENTICATED_EXTREME_MARGIN_CONNECTED_CHROMATIC_ANNOTATION_FURNITURE_V2"
)
_EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_STATUS = (
    "AUTHENTICATED_CLIPPED_RIGHT_EDGE_NONNUMERIC_DECORATION_V3"
)
_EXTREME_MARGIN_VERTICAL_STAMP_V4_STATUS = "AUTHENTICATED_EXTREME_RIGHT_VERTICAL_STAMP_FURNITURE_V4"
_EXTREME_MARGIN_VERTICAL_STAMP_V4_COMPONENT_STATUS = (
    "EXACT_CANDIDATE_CROP_CONNECTED_COMPONENT_PEER_CHAIN"
)
_EXTREME_MARGIN_VERTICAL_STAMP_V4_CHROMATIC_MODE = "TALL_CHROMATIC_INTERNAL_COMPONENT_CHAIN"
_EXTREME_MARGIN_VERTICAL_STAMP_V4_CLIPPED_MODE = "CLIPPED_NEUTRAL_EXTERNAL_PEER_CHAIN"
_PRINTED_NOTE_REFERENCE_FURNITURE_V3_STATUS = "AUTHENTICATED_PRINTED_NOTE_REFERENCE_FURNITURE_V3"
_PRINTED_NOTE_REFERENCE_V3_LEGACY_TOPOLOGY_DEPENDENCY_REF = {
    "path": "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
    "sha256": "60da089b5df5a6ee9f53dac8569bc4a9484bf5816721fb992f8d4d09a43bc236",
    "size_bytes": 68_515,
}
_PRINTED_NOTE_REFERENCE_FURNITURE_V4_STATUS = "AUTHENTICATED_PRINTED_NOTE_REFERENCE_FURNITURE_V4"
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
_EXTREME_MARGIN_FURNITURE_V2_FIELDS = {
    *_EXTREME_MARGIN_FURNITURE_FIELDS,
    "expanded_component_proof",
    "label_collision_proof",
}
_EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_FIELDS = {
    "candidate_crop_proof",
    "document_pages_sha256",
    "evidence_id",
    "geometry",
    "margin_band",
    "page_sequence",
    "sample_id",
    "semantic_label_line_ordinals",
    "snapshot_id",
    "source_record",
    "status",
    "structural_gap_anchor_occurrence_ids",
    "topology_candidates_id",
}
_EXTREME_MARGIN_VERTICAL_STAMP_V4_FIELDS = {
    "candidate_crop_proof",
    "component_peer_proof",
    "document_pages_sha256",
    "evidence_id",
    "full_page_inspected_label_band",
    "geometry",
    "label_collision_proof",
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
_PRINTED_NOTE_REFERENCE_FURNITURE_V3_FIELDS = {
    "candidate_crop_proof",
    "document_pages_sha256",
    "evidence_id",
    "geometry",
    "header_proof",
    "note_reference_axis",
    "original_cluster",
    "page_sequence",
    "sample_id",
    "semantic_row_binding",
    "snapshot_id",
    "source_record",
    "status",
    "topology_candidates_id",
}
_PRINTED_NOTE_REFERENCE_FURNITURE_V4_FIELDS = {
    "candidate_crop_proof",
    "document_pages_sha256",
    "evidence_id",
    "geometry",
    "header_proof",
    "note_reference_axis",
    "original_cluster",
    "page_sequence",
    "sample_id",
    "semantic_row_binding",
    "snapshot_id",
    "source_record",
    "status",
    "topology_candidates_id",
}
_PRINTED_NOTE_REFERENCE_GEOMETRY_V3_FIELDS = {
    "body_text_scale",
    "candidate_bbox",
    "candidate_center_twice",
    "candidate_note_value",
    "first_financial_lane_left_boundary",
    "header_bbox",
    "lane_centers_quads",
    "lane_tolerance",
    "page_width",
    "qualifying_note_reference_row_count",
}
_PRINTED_NOTE_REFERENCE_GEOMETRY_V4_FIELDS = {
    "body_text_scale",
    "candidate_bbox",
    "candidate_center_twice",
    "candidate_note_reference",
    "first_financial_lane_left_boundary",
    "header_bbox",
    "lane_centers_quads",
    "lane_tolerance",
    "page_width",
    "qualifying_note_reference_row_count",
}
_PRINTED_NOTE_REFERENCE_HEADER_FIELDS = {
    "crop_proofs",
    "header_bbox",
    "normalized_surface",
    "source_line_axis",
    "source_line_axis_sha256",
    "status",
}
_PRINTED_NOTE_REFERENCE_AXIS_V3_FIELDS = {
    "financial_line_axis",
    "label_line_axis",
    "note_crop_proof",
    "note_value",
    "source_line_record",
}
_PRINTED_NOTE_REFERENCE_AXIS_V4_FIELDS = {
    "financial_line_axis",
    "label_line_axis",
    "note_crop_proof",
    "note_reference",
    "source_line_record",
}
_PRINTED_NOTE_REFERENCE_FINANCIAL_LINE_FIELDS = {
    "column_ordinal",
    "source_line_record",
}
_PRINTED_NOTE_REFERENCE_SEMANTIC_ROW_V3_FIELDS = {
    "candidate_financial_line_axis_sha256",
    "candidate_same_row_label_axis_sha256",
    "label_source_line_axis",
    "label_source_line_axis_sha256",
    "occurrence_id",
    "role",
    "row_axis_id",
    "source_record",
    "status",
}
_PRINTED_NOTE_REFERENCE_SEMANTIC_ROW_V4_FIELDS = {
    "binding_kind",
    "candidate_financial_line_axis_sha256",
    "candidate_same_row_label_axis_sha256",
    "label_source_line_axis",
    "label_source_line_axis_sha256",
    "occurrence_id",
    "role",
    "row_axis_id",
    "source_record",
    "status",
}
_PRINTED_NOTE_REFERENCE_HEADER_STATUS = "EXACT_PRINTED_THUYET_MINH_COLUMN_HEADER"
_PRINTED_NOTE_REFERENCE_SEMANTIC_ROW_STATUS = (
    "UNIQUE_EXACT_SEMANTIC_ROW_WITH_COMPLETE_FINANCIAL_LANES"
)
_PRINTED_NOTE_REFERENCE_PARENT_STATUS = (
    "UNIQUE_SELECTED_TOPOLOGY_PARENT_SPAN_WITH_COMPLETE_FINANCIAL_LANES"
)
_PRINTED_NOTE_REFERENCE_ROLE_BINDING_KIND = "EXACT_ROLE_OCCURRENCE_ROW"
_PRINTED_NOTE_REFERENCE_PARENT_BINDING_KIND = "SELECTED_TOPOLOGY_PARENT_SPAN"
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
_EXTREME_MARGIN_V2_GEOMETRY_FIELDS = {
    "candidate_bbox",
    "candidate_center_quads",
    "lane_centers_quads",
    "lane_tolerance",
    "margin_boundary",
    "nearest_lane_ordinal",
    "page_width",
    "right_edge_gap",
}
_EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_GEOMETRY_FIELDS = {
    "body_source_line_start",
    "body_source_line_stop_exclusive",
    "body_text_scale",
    "candidate_bbox",
    "candidate_center_quads",
    "following_numeric_line_ordinal",
    "lane_centers_quads",
    "lane_tolerance",
    "margin_boundary",
    "page_width",
    "preceding_numeric_line_ordinal",
    "right_edge_gap",
}
_EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_BAND_FIELDS = {
    "document_pages_sha256",
    "input_page_line_count",
    "page_sequence",
    "source_line_axis",
    "source_line_axis_sha256",
}
_EXTREME_MARGIN_VERTICAL_STAMP_V4_GEOMETRY_FIELDS = {
    "body_text_scale",
    "candidate_bbox",
    "candidate_center_quads",
    "candidate_height",
    "candidate_width",
    "lane_centers_quads",
    "lane_tolerance",
    "margin_boundary",
    "page_edge_denominator",
    "page_edge_numerator",
    "page_width",
    "right_edge_gap",
    "stamp_mode",
}
_EXTREME_MARGIN_VERTICAL_STAMP_V4_COMPONENT_FIELDS = {
    "bbox",
    "chromatic_ink_pixel_count",
    "ink_pixel_count",
}
_EXTREME_MARGIN_VERTICAL_STAMP_V4_COMPONENT_PROOF_FIELDS = {
    "candidate_center_twice",
    "chroma_spread_threshold",
    "component_axis",
    "component_axis_sha256",
    "ink_threshold",
    "minimum_component_ink_pixel_count",
    "qualifying_component_count",
    "qualifying_component_ordinals",
    "qualifying_vertical_span",
    "render_binding",
    "status",
}
_EXTREME_MARGIN_V2_LABEL_COLLISION_FIELDS = {
    "candidate_line_ordinal",
    "margin_boundary",
    "maximum_label_right",
    "same_row_label_evidence",
    "same_row_label_evidence_sha256",
    "semantic_label_line_ordinals",
    "status",
}
_EXTREME_MARGIN_V2_COMPONENT_FIELDS = {
    "above_center_original_ink_pixel_count",
    "bbox",
    "below_center_original_ink_pixel_count",
    "chromatic_original_ink_pixel_count",
    "clear_extent_above_center",
    "clear_extent_below_center",
    "closed_pixel_count",
    "original_ink_pixel_count",
    "target_overlap_ink_pixel_count",
    "vertical_extension_outside_target",
}
_EXTREME_MARGIN_V2_COMPONENT_PROOF_FIELDS = {
    "body_text_scale",
    "candidate_center_twice",
    "chroma_spread_threshold",
    "closed_mask_sha256",
    "component_axis",
    "component_axis_sha256",
    "expanded_pixel_count",
    "expanded_raw_pixel_bbox",
    "expanded_rgb_sha256",
    "ink_threshold",
    "minimum_component_height",
    "minimum_original_ink_pixels",
    "minimum_side_extent_pixels",
    "minimum_side_ink_pixels",
    "minimum_target_overlap_ink_pixels",
    "minimum_vertical_extension_pixels",
    "morphology_kernel_size",
    "qualifying_component_count",
    "qualifying_component_ordinal",
    "render_binding",
}
_MAX_ROLE_OCCURRENCES = 4_096
_MAX_EXISTING_DASH_CELLS = 16_384
_MAX_NUMERIC_SAMPLES = 65_536
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEPENDENCIES = {
    "accounting_printed_note_reference_axis_v1": {
        "path": "src/bctc_ai/evaluation/accounting_printed_note_reference_axis_v1.py",
        "sha256": "e4afee7d204afb80fd61938fd4239678348d7d9e8a3eee73f9eac342953ac453",
        "size_bytes": 23_170,
    },
    "coextensive_parent_total_projector": {
        "path": "src/bctc_ai/evaluation/accounting_family_coextensive_parent_total_v1.py",
        "sha256": "31a7e42e85c6b16689a1148a1ccb3d02cee18f85139b6f800bed3aa309b48e68",
        "size_bytes": 14_722,
    },
    "exact_page_render_validator": {
        "path": "src/bctc_ai/evaluation/family_first_authenticated_page_region_v1.py",
        "sha256": "7a19254f73b625174d001ddbcad55d2b426ed9e137bde86070a09ce776c822af",
        "size_bytes": 31_249,
    },
    "existing_cell_dash_bridge": {
        "path": "src/bctc_ai/evaluation/family_first_authenticated_snapshot_cell_dash_v1.py",
        "sha256": "4d868880e2e997a997b2c4549301ed97c10641d76c8c5030de8c29dc86b195cb",
        "size_bytes": 18_259,
    },
    "unique_dash_isolated_speck_bridge": {
        "path": ("src/bctc_ai/evaluation/family_first_authenticated_unique_dash_speck_v1.py"),
        "sha256": "90e2a6be40281e42df7472989798e5e4dd88e565e023b577b485c9fc60943ea5",
        "size_bytes": 32_177,
    },
    "row_axis_v1": {
        "path": "src/bctc_ai/evaluation/accounting_family_row_axis_v1.py",
        "sha256": "a3c1d806149a45e390bf330559b36a18958b5e9dc59690a62fd2052b76e789c0",
        "size_bytes": 86_373,
    },
    "selected_snapshot_validator": {
        "path": "src/bctc_ai/evaluation/authenticated_semantic_region_snapshot_v1.py",
        "sha256": "139085696c138d7992b285968789918aef583bfa0bc5149d5a5a9956f5d7504d",
        "size_bytes": 24_406,
    },
    "topology_v1": {
        "path": "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        "sha256": "409cd254f7a43f641f3f3728b05e45ba79d9fe607bcd0837984575b09642b5c0",
        "size_bytes": 79_501,
    },
    "topology_candidates_v2": {
        "path": "src/bctc_ai/evaluation/accounting_family_topology_candidates_v2.py",
        "sha256": "281e8fb354a2dab665d1fa3674ce730b5b88023c112843e9939002c35da88195",
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


def _printed_note_reference_v3_topology_candidates_id(
    topology_candidates: Mapping[str, Any] | None,
) -> str | None:
    """Preserve the persisted integer-note V3 semantic candidate identity.

    The V3 furniture envelope predates additive topology-spec V4.  Its stored
    candidate identity is a semantic binding, not authority for loading the
    dependency bytes.  Public replay still validates the current candidate
    envelope and rebuilds the V3 evidence exactly; only this inner persisted
    compatibility identity retains the original dependency commitment.
    """

    if topology_candidates is None:
        return None
    try:
        current = candidates_v2._validate_result(topology_candidates)  # noqa: SLF001
    except candidates_v2.AccountingFamilyTopologyCandidatesV2Error as exc:
        raise _error("printed-note V3 topology candidate envelope drifted") from exc
    material = canonical_clone_v1(current)
    material.pop("result_id")
    dependency_refs = material.get("dependency_content_refs")
    if type(dependency_refs) is not dict or set(dependency_refs) != {
        "coextensive_parent_total_projector_v1",
        "topology_v1",
    }:
        raise _error("printed-note V3 topology dependency axis drifted")
    dependency_refs["topology_v1"] = canonical_clone_v1(
        _PRINTED_NOTE_REFERENCE_V3_LEGACY_TOPOLOGY_DEPENDENCY_REF
    )
    return "aftcv2:result:" + canonical_json_sha256_v1(material)


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


def _direct_frontier_number(value: Mapping[str, Any]) -> dict[str, Any] | None:
    parsed = value.get("parsed_token")
    if (
        type(parsed) is not dict
        or parsed.get("classification")
        not in {
            "DASH_ZERO",
            "MIXED_GROUPED_INTEGER_CANDIDATE",
            "NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
            "SIGNED_NUMBER",
        }
        or type(parsed.get("coefficient")) is not int
        or type(parsed.get("scale")) is not int
        or parsed["scale"] < 0
        or type(parsed.get("percentage_mark_present")) is not bool
    ):
        return None
    return {
        "coefficient": parsed["coefficient"],
        "percentage_mark_present": parsed["percentage_mark_present"],
        "scale": parsed["scale"],
    }


def _direct_frontier_row_receipt(row: Mapping[str, Any]) -> dict[str, Any] | None:
    values = sorted(row.get("values", []), key=lambda item: item.get("column_ordinal", -1))
    if (
        row.get("status") != "VISIBLE_VALUE_LANES_BOUND"
        or not values
        or [value.get("column_ordinal") for value in values] != list(range(len(values)))
    ):
        return None
    numbers = [_direct_frontier_number(value) for value in values]
    if any(number is None for number in numbers):
        return None
    return {
        "numbers": numbers,
        "sample_ids": [value["sample_id"] for value in values],
    }


def _direct_frontier_trailing_row_receipt(
    row: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return one exact complete trailing-row lane receipt."""

    values = sorted(row.get("values", []), key=lambda item: item.get("column_ordinal", -1))
    if (
        row.get("status") != "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
        or not values
        or [value.get("column_ordinal") for value in values] != list(range(len(values)))
    ):
        return None
    numbers = [_direct_frontier_number(value) for value in values]
    if any(number is None for number in numbers):
        return None
    return {
        "numbers": numbers,
        "sample_ids": [value["sample_id"] for value in values],
    }


def _direct_frontier_internal_cluster_receipt(
    cluster: Mapping[str, Any],
    universe_by_sample_id: Mapping[str, Mapping[str, Any]],
    *,
    expected_column_ordinals: Sequence[int],
) -> dict[str, Any] | None:
    """Return one exact complete unlabeled internal-subtotal lane receipt."""

    sample_ids = cluster.get("sample_ids")
    if (
        cluster.get("status") != _INTERNAL_UNASSIGNED_CLUSTER_STATUS
        or cluster.get("label_lane_status") != _UNLABELED_LABEL_LANE_STATUS
        or cluster.get("column_ordinals") != list(expected_column_ordinals)
        or type(sample_ids) is not list
        or len(sample_ids) != len(expected_column_ordinals)
        or len(sample_ids) != len(set(sample_ids))
    ):
        return None
    records = [universe_by_sample_id.get(sample_id) for sample_id in sample_ids]
    if any(
        type(record) is not dict
        or record.get("owner_kind") != "SOURCE_ONLY_INTERNAL_CLUSTER"
        or record.get("owner_id") != cluster.get("cluster_id")
        or record.get("page_sequence") != cluster.get("page_sequence")
        or record.get("column_ordinal") != column_ordinal
        for record, column_ordinal in zip(records, expected_column_ordinals, strict=True)
    ):
        return None
    numbers = [
        _direct_frontier_number(record) if type(record) is dict else None for record in records
    ]
    if any(number is None for number in numbers):
        return None
    return {
        "numbers": numbers,
        "sample_ids": list(sample_ids),
    }


def _has_immediate_post_carrier_financial_numeric_line(
    pages: Sequence[Mapping[str, Any]],
    *,
    after_line_ordinal: int,
    carrier_bboxes: Sequence[Sequence[int]],
    column_centers: Sequence[float],
    page_sequence: int,
) -> bool:
    """Reject another unlabeled financial row before the next text boundary."""

    page = next(
        (candidate for candidate in pages if candidate["page_sequence"] == page_sequence),
        None,
    )
    if type(page) is not dict or not column_centers or not carrier_bboxes:
        return True
    carrier_bottom = max(bbox[3] for bbox in carrier_bboxes)
    maximum_open_row_gap = 3 * max(bbox[3] - bbox[1] for bbox in carrier_bboxes)
    spacing = min(
        (right - left for left, right in zip(column_centers, column_centers[1:], strict=False)),
        default=80.0,
    )
    tolerance = max(8.0, spacing / 4)
    for line in page["lines"]:
        if line["line_ordinal"] <= after_line_ordinal:
            continue
        if line["bbox"][1] - carrier_bottom > maximum_open_row_gap:
            return False
        if row_v1._is_numeric(line):  # noqa: SLF001
            center = (line["bbox"][0] + line["bbox"][2]) / 2
            if min(abs(center - expected) for expected in column_centers) <= tolerance:
                return True
            continue
        if line["vietocr_text"].strip() or line["numeric_recognition"]["raw_prediction"].strip():
            return False
    return False


def _recursive_frontier_item_match(item: Mapping[str, Any]) -> Mapping[str, Any]:
    label_match = item.get("label_match")
    return label_match if type(label_match) is dict else item


def _recursive_direct_component_support_is_exact(
    interval_occurrences: Sequence[Mapping[str, Any]],
    rows_by_occurrence_id: Mapping[str, Sequence[Mapping[str, Any]]],
    effective_roles: Mapping[int, str],
    *,
    allow_derived_structural_frontier: bool = False,
    result_role: str,
    result_row: Mapping[str, Any],
) -> bool:
    """Recursively corroborate every visible structural component subtree."""

    matching_specs = [
        spec
        for spec in _RECURSIVE_PARENT_DIRECT_COMPONENT_SUPPORT_SPECS
        if spec["result_role"] == result_role
    ]
    if not matching_specs:
        return True
    if len(matching_specs) != 1:
        raise _error("recursive direct-component support spec repeats")
    spec = matching_specs[0]
    descendant_pairs = spec["direct_component_descendant_roles"]
    direct_roles = {
        role for alternative in spec["component_role_alternatives"] for role in alternative
    }
    if {pair[0] for pair in descendant_pairs} != direct_roles:
        raise _error("recursive direct-component support descendants drifted")
    direct_by_descendant: dict[str, set[str]] = {role: {role} for role in direct_roles}
    for direct_role, descendants in descendant_pairs:
        for descendant in descendants:
            direct_by_descendant.setdefault(descendant, set()).add(direct_role)

    occurrence_by_id = {
        occurrence.get(
            "occurrence_id",
            _recursive_frontier_item_match(occurrence).get("occurrence_id"),
        ): occurrence
        for occurrence in interval_occurrences
    }
    result_occurrence_id = result_row["label_match"].get("occurrence_id")
    result_occurrence = occurrence_by_id.get(result_occurrence_id)
    if type(result_occurrence) is not dict:
        return False
    result_match = _recursive_frontier_item_match(result_occurrence)
    result_scope_owner_occurrence_id = result_occurrence.get(
        "scope_owner_occurrence_id",
        result_match.get("scope_owner_occurrence_id"),
    )

    def coextensive(occurrence: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
        match = _recursive_frontier_item_match(occurrence)
        owner_match = _recursive_frontier_item_match(owner)
        return (
            match["page_sequence"] == owner_match["page_sequence"]
            and match["document_line_ordinal"] == owner_match["document_line_ordinal"]
            and match["end_document_line_ordinal"] == owner_match["end_document_line_ordinal"]
            and match["source_line_index"] == owner_match["source_line_index"]
            and match["end_source_line_index"] == owner_match["end_source_line_index"]
        )

    result_key = _visual_match_key(result_match)
    deposit_boundary = None
    if result_role == "INTERBANK_DEPOSIT_GROUP":
        deposit_boundary = min(
            (
                _visual_match_key(_recursive_frontier_item_match(occurrence))
                for occurrence in interval_occurrences
                if effective_roles.get(id(occurrence))
                in {"INTERBANK_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"}
                and _visual_match_key(_recursive_frontier_item_match(occurrence)) > result_key
            ),
            default=None,
        )

    def belongs_to_exact_result(
        occurrence: Mapping[str, Any], visited: set[int] | None = None
    ) -> bool:
        visited = set() if visited is None else set(visited)
        if id(occurrence) in visited:
            return False
        visited.add(id(occurrence))
        match = _recursive_frontier_item_match(occurrence)
        role = effective_roles.get(id(occurrence))
        expected_direct_owners = direct_by_descendant.get(role, set())
        owner_id = occurrence.get(
            "scope_owner_occurrence_id", match.get("scope_owner_occurrence_id")
        )
        if owner_id == result_occurrence_id:
            return role in direct_roles or (
                role in _RECURSIVE_PARENT_OWNER_BOUND_NONADDITIVE_EXCLUSIONS
                and len(expected_direct_owners) == 1
            )
        explicit_owner = occurrence_by_id.get(owner_id)
        if type(explicit_owner) is dict:
            return effective_roles.get(
                id(explicit_owner)
            ) in expected_direct_owners and belongs_to_exact_result(explicit_owner, visited)
        if coextensive(occurrence, result_occurrence):
            return role in direct_roles and owner_id == result_scope_owner_occurrence_id
        if result_role != "INTERBANK_DEPOSIT_GROUP":
            return False
        key = _visual_match_key(match)
        if not (result_key < key and (deposit_boundary is None or key < deposit_boundary)):
            return False
        if owner_id != result_scope_owner_occurrence_id:
            return False
        if role in direct_roles:
            return True
        coextensive_direct_owners = [
            candidate
            for candidate in interval_occurrences
            if effective_roles.get(id(candidate)) in expected_direct_owners
            and coextensive(occurrence, candidate)
            and belongs_to_exact_result(candidate, visited)
        ]
        return len(coextensive_direct_owners) == 1

    relevant_occurrences = [
        occurrence
        for occurrence in interval_occurrences
        if effective_roles.get(id(occurrence)) in direct_by_descendant
    ]
    if any(not belongs_to_exact_result(occurrence) for occurrence in relevant_occurrences):
        return False
    required_direct_roles = set()
    support_occurrences = [
        occurrence for occurrence in interval_occurrences if belongs_to_exact_result(occurrence)
    ]
    for occurrence in support_occurrences:
        owners = direct_by_descendant.get(effective_roles.get(id(occurrence)), set())
        if len(owners) > 1:
            return False
        required_direct_roles.update(owners)
    if not required_direct_roles:
        return True

    frontier = []
    for direct_role in required_direct_roles:
        candidates = [
            occurrence
            for occurrence in support_occurrences
            if effective_roles.get(id(occurrence)) == direct_role
        ]
        if len(candidates) != 1:
            return False
        occurrence = candidates[0]
        match = _recursive_frontier_item_match(occurrence)
        occurrence_id = occurrence.get("occurrence_id", match.get("occurrence_id"))
        direct_rows = rows_by_occurrence_id.get(occurrence_id, ())
        direct_receipt = (
            _direct_frontier_row_receipt(direct_rows[0]) if len(direct_rows) == 1 else None
        )
        if direct_receipt is not None:
            if not _recursive_direct_component_support_is_exact(
                support_occurrences,
                rows_by_occurrence_id,
                effective_roles,
                allow_derived_structural_frontier=allow_derived_structural_frontier,
                result_role=direct_role,
                result_row=direct_rows[0],
            ):
                return False
            frontier.append((direct_role, match, [direct_receipt]))
            continue
        if not allow_derived_structural_frontier:
            return False
        child_specs = [
            candidate
            for candidate in _RECURSIVE_PARENT_DIRECT_COMPONENT_SUPPORT_SPECS
            if candidate["result_role"] == direct_role
        ]
        if len(child_specs) != 1:
            return False
        child_spec = child_specs[0]
        child_direct_roles = {
            role
            for alternative in child_spec["component_role_alternatives"]
            for role in alternative
        }
        owned_children = [
            candidate
            for candidate in support_occurrences
            if candidate.get(
                "scope_owner_occurrence_id",
                _recursive_frontier_item_match(candidate).get("scope_owner_occurrence_id"),
            )
            == occurrence_id
        ]
        additive_children = [
            candidate
            for candidate in owned_children
            if candidate.get(
                "role_kind", _recursive_frontier_item_match(candidate).get("role_kind")
            )
            in {"ADDITIVE_CHILD", "STRUCTURAL_GROUP"}
        ]
        if any(
            effective_roles.get(id(candidate)) not in child_direct_roles
            for candidate in additive_children
        ):
            return False
        child_frontier = []
        for child_role in child_direct_roles:
            child_candidates = [
                candidate
                for candidate in additive_children
                if effective_roles.get(id(candidate)) == child_role
            ]
            if not child_candidates:
                continue
            if len(child_candidates) != 1:
                return False
            child_occurrence = child_candidates[0]
            child_match = _recursive_frontier_item_match(child_occurrence)
            child_occurrence_id = child_occurrence.get(
                "occurrence_id", child_match.get("occurrence_id")
            )
            child_rows = rows_by_occurrence_id.get(child_occurrence_id, ())
            child_receipt = (
                _direct_frontier_row_receipt(child_rows[0]) if len(child_rows) == 1 else None
            )
            if child_receipt is None or not _recursive_direct_component_support_is_exact(
                owned_children,
                rows_by_occurrence_id,
                effective_roles,
                allow_derived_structural_frontier=False,
                result_role=child_role,
                result_row=child_rows[0],
            ):
                return False
            child_frontier.append((child_role, child_match, child_receipt))
        child_frontier.sort(key=lambda item: _visual_match_key(item[1]))
        if (
            tuple(role for role, _match, _receipt in child_frontier)
            not in child_spec["component_role_alternatives"]
        ):
            return False
        frontier.append(
            (
                direct_role,
                match,
                [receipt for _role, _match, receipt in child_frontier],
            )
        )
    frontier.sort(key=lambda item: _visual_match_key(item[1]))
    frontier_roles = tuple(role for role, _match, _receipts in frontier)
    if frontier_roles not in spec["component_role_alternatives"]:
        return False
    result_receipt = _direct_frontier_row_receipt(result_row)
    component_receipts = [receipt for _role, _match, receipts in frontier for receipt in receipts]
    if result_receipt is None or not _direct_frontier_sum_is_exact(
        result_receipt, component_receipts
    ):
        return False
    sample_ids = [
        sample_id for receipt in component_receipts for sample_id in receipt["sample_ids"]
    ]
    if len(sample_ids) != len(set(sample_ids)):
        return False
    return True


def _complete_recursive_parent_direct_frontier(
    occurrences: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    binding_spec: Mapping[str, Any],
    *,
    interval_end: tuple[int, int, int, int] | None,
    interval_start: tuple[int, int, int, int] | None,
    page_sequence: int,
    parent_occurrence_id: str,
    source_retrieval_occurrence_id: str,
) -> list[tuple[str, Mapping[str, Any]]] | None:
    """Rebuild one exhaustive, ordered direct-component frontier.

    Every visible additive/structural occurrence in the exact parent interval
    must map to exactly one declared direct component.  A component can enter
    the frontier only through its own complete final row; a visible descendant
    under a missing or incomplete direct subtotal therefore abstains instead
    of letting an arithmetic coincidence skip that sibling subtree.
    """

    descendant_pairs = binding_spec.get("direct_component_descendant_roles")
    alternatives = binding_spec.get("direct_component_role_alternatives")
    if (
        type(descendant_pairs) is not tuple
        or not descendant_pairs
        or type(alternatives) is not tuple
        or not alternatives
    ):
        raise _error("recursive parent direct-frontier declaration drifted")
    direct_roles = {role for alternative in alternatives for role in alternative}
    declared_direct_roles = {pair[0] for pair in descendant_pairs}
    if (
        any(
            type(pair) is not tuple
            or len(pair) != 2
            or type(pair[0]) is not str
            or type(pair[1]) is not tuple
            or any(type(role) is not str for role in pair[1])
            for pair in descendant_pairs
        )
        or declared_direct_roles != direct_roles
    ):
        raise _error("recursive parent direct-frontier descendants drifted")
    direct_by_descendant: dict[str, set[str]] = {role: {role} for role in direct_roles}
    for direct_role, descendant_roles in descendant_pairs:
        for descendant_role in descendant_roles:
            direct_by_descendant.setdefault(descendant_role, set()).add(direct_role)

    def in_interval(item: Mapping[str, Any]) -> bool:
        match = _recursive_frontier_item_match(item)
        if match["page_sequence"] != page_sequence:
            return False
        key = _visual_match_key(match)
        return (interval_start is None or interval_start < key) and (
            interval_end is None or key < interval_end
        )

    interval_occurrences = [item for item in occurrences if in_interval(item)]
    required_direct_roles = set()
    effective_roles: dict[int, str] = {}
    for occurrence in interval_occurrences:
        match = _recursive_frontier_item_match(occurrence)
        if occurrence.get("occurrence_id", match.get("occurrence_id")) == parent_occurrence_id:
            continue
        retrieval_id = occurrence.get(
            "retrieval_occurrence_id", match.get("retrieval_occurrence_id")
        )
        role = occurrence.get("role", match.get("role"))
        effective_role = (
            binding_spec["target_role"] if retrieval_id == source_retrieval_occurrence_id else role
        )
        effective_roles[id(occurrence)] = effective_role
        owners = direct_by_descendant.get(effective_role, set())
        if len(owners) > 1:
            return None
        if len(owners) == 1:
            required_direct_roles.update(owners)
            continue
        role_kind = occurrence.get("role_kind", match.get("role_kind"))
        if (
            role_kind in {"ADDITIVE_CHILD", "STRUCTURAL_GROUP"}
            and effective_role not in binding_spec["result_roles"]
            and effective_role != binding_spec["parent_role"]
        ):
            return None

    rows_by_occurrence_id: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        occurrence_id = row["label_match"].get("occurrence_id")
        if type(occurrence_id) is str:
            rows_by_occurrence_id.setdefault(occurrence_id, []).append(row)
    frontier = []
    for direct_role in required_direct_roles:
        candidates = [
            occurrence
            for occurrence in interval_occurrences
            if effective_roles.get(id(occurrence)) == direct_role
        ]
        if len(candidates) != 1:
            return None
        occurrence = candidates[0]
        match = _recursive_frontier_item_match(occurrence)
        occurrence_id = occurrence.get("occurrence_id", match.get("occurrence_id"))
        direct_rows = rows_by_occurrence_id.get(occurrence_id, [])
        if len(direct_rows) != 1 or _direct_frontier_row_receipt(direct_rows[0]) is None:
            return None
        frontier.append((direct_role, direct_rows[0]))
    frontier.sort(key=lambda item: _visual_match_key(item[1]["label_match"]))
    receipts = [_direct_frontier_row_receipt(row) for _role, row in frontier]
    sample_ids = [sample_id for receipt in receipts for sample_id in receipt["sample_ids"]]
    if len(sample_ids) != len(set(sample_ids)):
        return None
    if not all(
        _recursive_direct_component_support_is_exact(
            interval_occurrences,
            rows_by_occurrence_id,
            effective_roles,
            allow_derived_structural_frontier=binding_spec["parent_role"] is None,
            result_role=role,
            result_row=row,
        )
        for role, row in frontier
    ):
        return None
    return frontier


def _direct_frontier_parent_row_receipt(
    pages: Sequence[Mapping[str, Any]],
    parent_match: Mapping[str, Any],
    preliminary_axis: Mapping[str, Any],
) -> dict[str, Any] | None:
    samples = _same_row_numeric_samples(pages, parent_match)
    grid = next(
        (
            item
            for item in preliminary_axis["column_grids"]
            if item["page_sequence"] == parent_match["page_sequence"]
        ),
        None,
    )
    if type(grid) is not dict or len(samples) != len(grid["column_centers"]) or not samples:
        return None
    samples = sorted(samples, key=lambda item: (item["bbox"][0], item["line_ordinal"]))
    numbers = []
    for sample in samples:
        parsed = row_v1.parse_visible_financial_numeric_token_v1(
            sample["numeric_recognition"]["raw_prediction"]
        )
        number = _direct_frontier_number({"parsed_token": parsed})
        if number is None:
            return None
        numbers.append(number)
    return {
        "numbers": numbers,
        "sample_ids": [sample["sample_id"] for sample in samples],
    }


def _direct_frontier_sum_is_exact(
    result: Mapping[str, Any], components: Sequence[Mapping[str, Any]]
) -> bool:
    result_numbers = result["numbers"]
    if not components or any(len(item["numbers"]) != len(result_numbers) for item in components):
        return False
    for lane, expected in enumerate(result_numbers):
        observed = [item["numbers"][lane] for item in components]
        percentages = {item["percentage_mark_present"] for item in [expected, *observed]}
        if len(percentages) != 1:
            return False
        scale = max(item["scale"] for item in [expected, *observed])
        expected_coefficient = expected["coefficient"] * 10 ** (scale - expected["scale"])
        observed_coefficient = sum(
            item["coefficient"] * 10 ** (scale - item["scale"]) for item in observed
        )
        if expected_coefficient != observed_coefficient:
            return False
    return True


def _visual_match_key(match: Mapping[str, Any]) -> tuple[int, int, int, int]:
    bbox = match.get("source_label_bbox")
    if type(bbox) is not list:
        return (
            match["page_sequence"],
            2 * match["document_line_ordinal"],
            2 * match["end_document_line_ordinal"],
            match["document_line_ordinal"],
        )
    return (
        match["page_sequence"],
        bbox[1] + bbox[3],
        2 * bbox[0],
        match["document_line_ordinal"],
    )


def _has_unmatched_complete_labeled_numeric_row(
    pages: Sequence[Mapping[str, Any]],
    matches: Sequence[Mapping[str, Any]],
    *,
    allowed_coextensive_results: Sequence[Mapping[str, Any]],
    lower_bbox: Sequence[int],
    page_sequence: int,
    upper_bbox: Sequence[int],
    expected_lane_count: int,
) -> bool:
    if expected_lane_count <= 0:
        return True
    page = next(
        (item for item in pages if item["page_sequence"] == page_sequence),
        None,
    )
    if type(page) is not dict:
        return True
    claimed_source_indices = {
        source_line_index
        for match in matches
        if match["page_sequence"] == page_sequence
        for source_line_index in row_v1._match_source_line_indices(match)  # noqa: SLF001
    }
    lower_center = lower_bbox[1] + lower_bbox[3]
    upper_center = upper_bbox[1] + upper_bbox[3]
    unmatched_rows = []
    for source_line_index, line in enumerate(page["lines"]):
        bbox = line["bbox"]
        if (
            source_line_index in claimed_source_indices
            or not lower_center < bbox[1] + bbox[3] < upper_center
            or row_v1._is_numeric(line)  # noqa: SLF001
            or not line["vietocr_text"].strip()
        ):
            continue
        numeric_peers = [
            peer
            for peer in page["lines"]
            if row_v1._is_numeric(peer)  # noqa: SLF001
            and _same_row_fragment_distance(peer, bbox) is not None
        ]
        if len(numeric_peers) == expected_lane_count:
            unmatched_rows.append((line, numeric_peers))
    if not unmatched_rows:
        return False

    # OCR commonly emits a table section ordinal (for example ``III``) as a
    # separate label fragment immediately to the left of an otherwise exact
    # result row.  It is furniture, not another accounting row, only when its
    # numeric peers are byte-for-byte the already selected result samples and
    # the fragment is one isolated Roman ordinal on the same visual baseline.
    # Unknown text, duplicate ordinals, and a marker for any other value row
    # remain an unmatched-row veto.
    if len(unmatched_rows) != 1:
        return True
    line, numeric_peers = unmatched_rows[0]
    compact = re.sub(r"\s+", "", line["vietocr_text"].strip())
    if _COEXTENSIVE_TABLE_SECTION_ORDINAL.fullmatch(compact) is None:
        return True
    peer_sample_ids = [
        peer["sample_id"]
        for peer in sorted(numeric_peers, key=lambda item: (item["bbox"][0], item["bbox"][2]))
    ]
    bbox = line["bbox"]
    matching_results = []
    for result in allowed_coextensive_results:
        label_bbox = result["source_label_bbox"]
        overlap = min(bbox[3], label_bbox[3]) - max(bbox[1], label_bbox[1])
        minimum_height = min(bbox[3] - bbox[1], label_bbox[3] - label_bbox[1])
        if (
            peer_sample_ids == result["sample_ids"]
            and bbox[2] <= label_bbox[0]
            and label_bbox[0] - bbox[2] <= 4 * minimum_height
            and overlap > 0
            and 2 * overlap >= minimum_height
        ):
            matching_results.append(result)
    return len(matching_results) != 1


def _recursive_parent_provision_equation_geometry(
    *,
    component_rows: Sequence[Mapping[str, Any]],
    component_roles: Sequence[str],
    generic_occurrence: Mapping[str, Any],
    parent_occurrence_id: str,
    parent_role: str,
    result_occurrence_id: str,
    result_receipt: Mapping[str, Any],
    result_role: str,
) -> dict[str, Any]:
    component_frontier = []
    for row, role in zip(component_rows, component_roles, strict=True):
        receipt = _direct_frontier_row_receipt(row)
        if receipt is None:
            raise _error("recursive parent provision lost a complete direct component row")
        match = row["label_match"]
        component_frontier.append(
            {
                "numbers": receipt["numbers"],
                "retrieval_occurrence_id": match["retrieval_occurrence_id"],
                "role": role,
                "sample_ids": receipt["sample_ids"],
            }
        )
    equation_material = {
        "component_frontier": component_frontier,
        "parent_occurrence_id": parent_occurrence_id,
        "parent_role": parent_role,
        "result": {
            "numbers": canonical_clone_v1(result_receipt["numbers"]),
            "occurrence_id": result_occurrence_id,
            "role": result_role,
            "sample_ids": canonical_clone_v1(result_receipt["sample_ids"]),
        },
        "source_retrieval_occurrence_id": generic_occurrence["retrieval_occurrence_id"],
        "status": _RECURSIVE_PARENT_PROVISION_EQUATION_STATUS,
    }
    equation = {
        **equation_material,
        "equation_id": "aforav2:direct-frontier-equation:"
        + canonical_json_sha256_v1(equation_material),
    }
    return {
        "equation": equation,
        "ordered_source_label_bboxes": [
            canonical_clone_v1(row["label_match"]["source_label_bbox"]) for row in component_rows
        ],
        "status": _RECURSIVE_PARENT_PROVISION_GEOMETRY_STATUS,
    }


def _recursive_parent_provision_geometry_is_valid(
    geometry: Any, *, label_match: Mapping[str, Any], role: str
) -> bool:
    if (
        type(geometry) is not dict
        or set(geometry) != {"equation", "ordered_source_label_bboxes", "status"}
        or geometry["status"] != _RECURSIVE_PARENT_PROVISION_GEOMETRY_STATUS
        or type(geometry["equation"]) is not dict
    ):
        return False
    equation = geometry["equation"]
    if (
        set(equation)
        != {
            "component_frontier",
            "equation_id",
            "parent_occurrence_id",
            "parent_role",
            "result",
            "source_retrieval_occurrence_id",
            "status",
        }
        or equation["status"] != _RECURSIVE_PARENT_PROVISION_EQUATION_STATUS
        or type(equation["parent_occurrence_id"]) is not str
        or not equation["parent_occurrence_id"]
        or type(equation["parent_role"]) is not str
        or not equation["parent_role"]
        or equation["source_retrieval_occurrence_id"]
        != label_match.get("retrieval_occurrence_id", label_match.get("occurrence_id"))
        or type(equation["component_frontier"]) is not list
        or not equation["component_frontier"]
        or type(equation["result"]) is not dict
        or set(equation["result"]) != {"numbers", "occurrence_id", "role", "sample_ids"}
    ):
        return False

    def numbers_valid(value: Any) -> bool:
        return (
            type(value) is list
            and bool(value)
            and all(
                type(number) is dict
                and set(number) == {"coefficient", "percentage_mark_present", "scale"}
                and type(number["coefficient"]) is int
                and type(number["percentage_mark_present"]) is bool
                and type(number["scale"]) is int
                and number["scale"] >= 0
                for number in value
            )
        )

    result = equation["result"]
    components = equation["component_frontier"]
    if (
        type(result["occurrence_id"]) is not str
        or not result["occurrence_id"]
        or type(result["role"]) is not str
        or not result["role"]
        or not numbers_valid(result["numbers"])
        or type(result["sample_ids"]) is not list
        or len(result["sample_ids"]) != len(result["numbers"])
        or len(result["sample_ids"]) != len(set(result["sample_ids"]))
        or any(type(sample_id) is not str or not sample_id for sample_id in result["sample_ids"])
        or any(
            type(component) is not dict
            or set(component) != {"numbers", "retrieval_occurrence_id", "role", "sample_ids"}
            or type(component["retrieval_occurrence_id"]) is not str
            or not component["retrieval_occurrence_id"]
            or type(component["role"]) is not str
            or not component["role"]
            or not numbers_valid(component["numbers"])
            or len(component["numbers"]) != len(result["numbers"])
            or type(component["sample_ids"]) is not list
            or len(component["sample_ids"]) != len(component["numbers"])
            or len(component["sample_ids"]) != len(set(component["sample_ids"]))
            or any(
                type(sample_id) is not str or not sample_id for sample_id in component["sample_ids"]
            )
            for component in components
        )
    ):
        return False
    matching_specs = [
        spec
        for spec in _RECURSIVE_PARENT_PROVISION_BINDING_SPECS
        if spec["target_role"] == role
        and tuple(component["role"] for component in components)
        in spec["direct_component_role_alternatives"]
    ]
    if len(matching_specs) != 1:
        return False
    spec = matching_specs[0]
    expected_parent_role = spec["parent_role"] or "INTERBANK_DEPOSITS_AND_LOANS"
    allowed_result_roles = set(spec["result_roles"])
    if spec["parent_role"] is None:
        allowed_result_roles.add(expected_parent_role)
    if (
        equation["parent_role"] != expected_parent_role
        or result["role"] not in allowed_result_roles
        or (
            spec["parent_role"] is not None
            and result["occurrence_id"] != equation["parent_occurrence_id"]
        )
        or sum(component["role"] == role for component in components) != 1
        or len({component["retrieval_occurrence_id"] for component in components})
        != len(components)
        or len({sample_id for component in components for sample_id in component["sample_ids"]})
        != sum(len(component["sample_ids"]) for component in components)
    ):
        return False
    if not _direct_frontier_sum_is_exact(
        result,
        [
            {"numbers": component["numbers"], "sample_ids": component["sample_ids"]}
            for component in components
        ],
    ):
        return False
    bboxes = geometry["ordered_source_label_bboxes"]
    if (
        type(bboxes) is not list
        or len(bboxes) != len(components)
        or any(
            type(bbox) is not list
            or len(bbox) != 4
            or any(type(coordinate) is not int for coordinate in bbox)
            or not bbox[0] < bbox[2]
            or not bbox[1] < bbox[3]
            for bbox in bboxes
        )
        or [(bbox[1] + bbox[3], bbox[0]) for bbox in bboxes]
        != sorted((bbox[1] + bbox[3], bbox[0]) for bbox in bboxes)
    ):
        return False
    material = {
        key: canonical_clone_v1(value) for key, value in equation.items() if key != "equation_id"
    }
    return equation[
        "equation_id"
    ] == "aforav2:direct-frontier-equation:" + canonical_json_sha256_v1(material)


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
        or check.get("status") not in _ONE_EDIT_AUTHORITY_BOUND_STATUSES
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


def _project_recursive_parent_provision_bindings(
    pages: Sequence[Mapping[str, Any]],
    compiled_family: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]],
    preliminary_matches: Sequence[Mapping[str, Any]],
    preliminary_axis: Mapping[str, Any],
    preliminary_internal_clusters: Sequence[Mapping[str, Any]],
    preliminary_numeric_sample_universe: Sequence[Mapping[str, Any]],
    selected_region: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Bind a generic additive row only through one exact recursive equation.

    The primitive consumes the sealed visible row/lane axis, not OCR provider
    order.  A candidate parent is eligible only when one declared ordered
    direct-component frontier is complete and sums exactly to its visible
    result in every lane.  Parent results and their leaves can therefore never
    coexist in one frontier.  More than one physical source, parent, result, or
    exact frontier is an abstention.
    """

    projected = [canonical_clone_v1(match) for match in matches]
    definitions = {child["role"]: child for child in compiled_family["children"]}
    required_roles = {
        _PROVISION_GENERIC_ROLE,
        *(spec["target_role"] for spec in _RECURSIVE_PARENT_PROVISION_BINDING_SPECS),
    }
    if not required_roles <= set(definitions):
        return projected
    rows = [
        row for row in preliminary_axis["rows"] if _direct_frontier_row_receipt(row) is not None
    ]
    all_rows = preliminary_axis["rows"]
    rows_by_role: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        rows_by_role.setdefault(row["role"], []).append(row)
    grids_by_page = {grid["page_sequence"]: grid for grid in preliminary_axis["column_grids"]}
    preliminary_universe_by_sample_id = {
        record.get("sample_id"): record
        for record in preliminary_numeric_sample_universe
        if type(record) is dict and type(record.get("sample_id")) is str
    }
    generic_occurrences = [
        match
        for match in preliminary_matches
        if match["role"] == _PROVISION_GENERIC_ROLE
        and _match_has_effective_exact_source_authority(match)
        and match["occurrence_id"]
        in {
            row["label_match"]["occurrence_id"]
            for row in rows_by_role.get(_PROVISION_GENERIC_ROLE, [])
        }
    ]
    if not generic_occurrences:
        return projected
    row_by_occurrence = {row["label_match"]["occurrence_id"]: row for row in rows}
    projected_by_retrieval_id = {
        match.get("retrieval_occurrence_id", match.get("occurrence_id")): match
        for match in projected
    }
    root_scope_id = "aforav2:root:" + canonical_json_sha256_v1(
        {
            "end": selected_region["cluster_end_document_line_ordinal_exclusive"],
            "parent_match": selected_region.get("parent_match"),
            "start": selected_region["cluster_start_document_line_ordinal"],
        }
    )
    parent_match = canonical_clone_v1(selected_region["parent_match"])
    parent_match["role"] = compiled_family["family_id"]
    parent_match["source_label_bbox"] = _source_line_bbox(pages, parent_match)
    parent_result = _direct_frontier_parent_row_receipt(pages, parent_match, preliminary_axis)

    proposals: list[dict[str, Any]] = []
    for generic in generic_occurrences:
        generic_row = row_by_occurrence[generic["occurrence_id"]]
        generic_key = _visual_match_key(generic)
        source_proposals = []
        for binding_spec in _RECURSIVE_PARENT_PROVISION_BINDING_SPECS:
            target_role = binding_spec["target_role"]
            parent_role = binding_spec["parent_role"]
            if parent_role is None:
                parent_role_for_receipt = compiled_family["family_id"]
                parent_sources = [(root_scope_id, parent_match, None)]
            else:
                parent_role_for_receipt = parent_role
                parent_sources = [
                    (
                        candidate["occurrence_id"],
                        candidate,
                        row_by_occurrence.get(candidate["occurrence_id"]),
                    )
                    for candidate in preliminary_matches
                    if candidate["role"] == parent_role
                    and candidate["page_sequence"] == generic["page_sequence"]
                    and _match_has_effective_exact_source_authority(candidate)
                ]
            for parent_occurrence_id, interval_parent_match, parent_row in parent_sources:
                if parent_role is None:
                    result_candidates = [
                        (
                            row["label_match"]["occurrence_id"],
                            row["role"],
                            _direct_frontier_row_receipt(row),
                        )
                        for result_role in binding_spec["result_roles"]
                        for row in rows_by_role.get(result_role, [])
                        if row["label_match"]["page_sequence"] == generic["page_sequence"]
                        and row["label_match"].get("scope_owner_occurrence_id") == root_scope_id
                    ]
                    if (
                        parent_result is not None
                        and parent_match["page_sequence"] == generic["page_sequence"]
                        and parent_result["sample_ids"]
                        not in [
                            candidate[2]["sample_ids"]
                            for candidate in result_candidates
                            if candidate[2] is not None
                        ]
                    ):
                        result_candidates.append(
                            (
                                root_scope_id,
                                compiled_family["family_id"],
                                parent_result,
                            )
                        )
                else:
                    result_candidates = (
                        [
                            (
                                parent_occurrence_id,
                                parent_role,
                                _direct_frontier_row_receipt(parent_row),
                            )
                        ]
                        if parent_row is not None
                        else []
                    )
                next_parent_boundary = None
                if parent_role is not None:
                    later_parent_boundaries = [
                        _visual_match_key(candidate)
                        for candidate in preliminary_matches
                        if candidate["role"] in {"INTERBANK_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"}
                        and candidate["page_sequence"] == generic["page_sequence"]
                        and candidate["occurrence_id"] != parent_occurrence_id
                        and _visual_match_key(candidate) > _visual_match_key(interval_parent_match)
                    ]
                    next_parent_boundary = min(later_parent_boundaries, default=None)
                    if (
                        generic_key <= _visual_match_key(interval_parent_match)
                        or next_parent_boundary is not None
                        and generic_key >= next_parent_boundary
                    ):
                        continue

                frontier_page_sequence = generic["page_sequence"]
                frontier_start = (
                    None if parent_role is None else _visual_match_key(interval_parent_match)
                )
                frontier_end = next_parent_boundary

                def belongs_to_parent_frontier(
                    row: Mapping[str, Any],
                    *,
                    end: tuple[int, int, int, int] | None = frontier_end,
                    page_sequence: int = frontier_page_sequence,
                    start: tuple[int, int, int, int] | None = frontier_start,
                ) -> bool:
                    match = row["label_match"]
                    if match["page_sequence"] != page_sequence:
                        return False
                    if start is None:
                        return match.get("scope_owner_occurrence_id") == root_scope_id
                    key = _visual_match_key(match)
                    return start < key and (end is None or key < end)

                explicit_target_rows = [
                    row
                    for row in all_rows
                    if row["role"] == target_role and belongs_to_parent_frontier(row)
                ]
                if explicit_target_rows:
                    continue
                complete_frontier = _complete_recursive_parent_direct_frontier(
                    preliminary_matches,
                    all_rows,
                    binding_spec,
                    interval_end=frontier_end,
                    interval_start=frontier_start,
                    page_sequence=frontier_page_sequence,
                    parent_occurrence_id=parent_occurrence_id,
                    source_retrieval_occurrence_id=generic["retrieval_occurrence_id"],
                )
                if complete_frontier is None:
                    continue
                complete_frontier_roles = tuple(role for role, _row in complete_frontier)
                grid = grids_by_page.get(generic["page_sequence"])
                if type(grid) is not dict:
                    continue
                expected_column_ordinals = list(range(len(grid["column_centers"])))
                if parent_role is None:
                    generic_source_end = max(
                        [
                            *row_v1._match_source_line_indices(generic),  # noqa: SLF001
                            *(value["line_ordinal"] for value in generic_row["values"]),
                        ]
                    )
                    trailing_rows_after_source = [
                        trailing
                        for trailing in preliminary_axis["trailing_value_rows"]
                        if trailing.get("page_sequence") == generic["page_sequence"]
                        and trailing.get("values")
                        and min(value["line_ordinal"] for value in trailing["values"])
                        > generic_source_end
                    ]
                    later_semantics = [
                        candidate
                        for candidate in preliminary_matches
                        if candidate["occurrence_id"] != generic["occurrence_id"]
                        and candidate["page_sequence"] == generic["page_sequence"]
                        and _visual_match_key(candidate) > generic_key
                    ]
                    for trailing in (
                        trailing_rows_after_source
                        if len(trailing_rows_after_source) == 1
                        and not later_semantics
                        and parent_match["page_sequence"] == generic["page_sequence"]
                        else []
                    ):
                        receipt = _direct_frontier_trailing_row_receipt(trailing)
                        values = trailing.get("values", [])
                        trailing_line_ordinals = sorted(value["line_ordinal"] for value in values)
                        if (
                            receipt is None
                            or len(receipt["numbers"]) != len(expected_column_ordinals)
                            or not values
                            or trailing_line_ordinals
                            != list(
                                range(
                                    generic_source_end + 1,
                                    generic_source_end + 1 + len(values),
                                )
                            )
                            or _has_immediate_post_carrier_financial_numeric_line(
                                pages,
                                after_line_ordinal=max(trailing_line_ordinals),
                                carrier_bboxes=[value["bbox"] for value in values],
                                column_centers=grid["column_centers"],
                                page_sequence=generic["page_sequence"],
                            )
                            or min(value["bbox"][1] + value["bbox"][3] for value in values)
                            <= generic["source_label_bbox"][1] + generic["source_label_bbox"][3]
                        ):
                            continue
                        result_candidates.append(
                            (root_scope_id, compiled_family["family_id"], receipt)
                        )
                else:
                    for cluster in preliminary_internal_clusters:
                        receipt = _direct_frontier_internal_cluster_receipt(
                            cluster,
                            preliminary_universe_by_sample_id,
                            expected_column_ordinals=expected_column_ordinals,
                        )
                        records = [
                            preliminary_universe_by_sample_id.get(sample_id)
                            for sample_id in cluster.get("sample_ids", [])
                        ]
                        if (
                            receipt is None
                            or cluster.get("page_sequence") != generic["page_sequence"]
                            or any(type(record) is not dict for record in records)
                        ):
                            continue
                        result_key = min(
                            (
                                record["page_sequence"],
                                record["bbox"][1] + record["bbox"][3],
                                2 * record["bbox"][0],
                                record["line_ordinal"],
                            )
                            for record in records
                            if type(record) is dict
                        )
                        cluster_line_ordinals = sorted(
                            record["line_ordinal"] for record in records if type(record) is dict
                        )
                        generic_source_end = max(
                            [
                                *row_v1._match_source_line_indices(generic),  # noqa: SLF001
                                *(value["line_ordinal"] for value in generic_row["values"]),
                            ]
                        )
                        if (
                            cluster_line_ordinals
                            != list(
                                range(
                                    generic_source_end + 1,
                                    generic_source_end + 1 + len(records),
                                )
                            )
                            or result_key <= generic_key
                            or (frontier_end is not None and result_key >= frontier_end)
                        ):
                            continue
                        intervening_semantics = [
                            candidate
                            for candidate in preliminary_matches
                            if candidate["occurrence_id"] != generic["occurrence_id"]
                            and generic_key < _visual_match_key(candidate) < result_key
                        ]
                        if intervening_semantics:
                            continue
                        result_candidates.append((parent_occurrence_id, parent_role, receipt))
                allowed_coextensive_results = [
                    {
                        "sample_ids": result_receipt["sample_ids"],
                        "source_label_bbox": (
                            row_by_occurrence[result_occurrence_id]["label_match"][
                                "source_label_bbox"
                            ]
                            if result_occurrence_id in row_by_occurrence
                            else interval_parent_match["source_label_bbox"]
                        ),
                    }
                    for result_occurrence_id, _result_role, result_receipt in result_candidates
                    if result_receipt is not None
                ]
                if _has_unmatched_complete_labeled_numeric_row(
                    pages,
                    preliminary_matches,
                    allowed_coextensive_results=allowed_coextensive_results,
                    lower_bbox=interval_parent_match["source_label_bbox"],
                    page_sequence=generic["page_sequence"],
                    upper_bbox=generic["source_label_bbox"],
                    expected_lane_count=len(grid["column_centers"]),
                ):
                    continue
                for alternative in binding_spec["direct_component_role_alternatives"]:
                    if complete_frontier_roles != alternative:
                        continue
                    source_roles = tuple(
                        _PROVISION_GENERIC_ROLE if role == target_role else role
                        for role in alternative
                    )
                    choices = []
                    for source_role in source_roles:
                        if source_role == _PROVISION_GENERIC_ROLE:
                            choices.append([generic_row])
                        else:
                            choices.append(
                                [
                                    row
                                    for row in rows_by_role.get(source_role, [])
                                    if belongs_to_parent_frontier(row)
                                    and _match_has_effective_exact_source_authority(
                                        row["label_match"]
                                    )
                                ]
                            )
                    if any(not choice for choice in choices):
                        continue
                    for component_rows in product(*choices):
                        component_matches = [row["label_match"] for row in component_rows]
                        if (
                            len({row["label_match"]["occurrence_id"] for row in component_rows})
                            != len(component_rows)
                            or [_visual_match_key(match) for match in component_matches]
                            != sorted(_visual_match_key(match) for match in component_matches)
                            or _visual_match_key(component_matches[-1]) != generic_key
                        ):
                            continue
                        if parent_role is not None and not (
                            _visual_match_key(interval_parent_match)
                            < _visual_match_key(component_matches[0])
                        ):
                            continue
                        component_receipts = [
                            _direct_frontier_row_receipt(row) for row in component_rows
                        ]
                        for result_occurrence_id, result_role, result_receipt in result_candidates:
                            if result_receipt is None or not _direct_frontier_sum_is_exact(
                                result_receipt, component_receipts
                            ):
                                continue
                            geometry = _recursive_parent_provision_equation_geometry(
                                component_rows=component_rows,
                                component_roles=alternative,
                                generic_occurrence=generic,
                                parent_occurrence_id=parent_occurrence_id,
                                parent_role=parent_role_for_receipt,
                                result_occurrence_id=result_occurrence_id,
                                result_receipt=result_receipt,
                                result_role=result_role,
                            )
                            anchor_match = (
                                interval_parent_match
                                if parent_role is not None
                                else component_rows[-2]["label_match"]
                            )
                            source_proposals.append(
                                {
                                    "anchor": anchor_match,
                                    "geometry": geometry,
                                    "matched_within_role": binding_spec["matched_within_role"],
                                    "parent_occurrence_id": parent_occurrence_id,
                                    "source": generic,
                                    "target_role": target_role,
                                }
                            )
        unique_by_equation = {
            proposal["geometry"]["equation"]["equation_id"]: proposal
            for proposal in source_proposals
        }
        if len(unique_by_equation) == 1:
            proposals.append(next(iter(unique_by_equation.values())))

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for proposal in proposals:
        grouped.setdefault((proposal["parent_occurrence_id"], proposal["target_role"]), []).append(
            proposal
        )
    for group in grouped.values():
        if len(group) != 1:
            continue
        proposal = group[0]
        source = proposal["source"]
        projected_source = projected_by_retrieval_id.get(source["retrieval_occurrence_id"])
        if projected_source is None or projected_source["role"] != _PROVISION_GENERIC_ROLE:
            continue
        anchor = proposal["anchor"]
        receipt = _scope_binding(
            anchor=anchor,
            anchor_exact_source_authority_check=_bound_one_edit_exact_source_check(anchor),
            binding_kind=_RECURSIVE_PARENT_PROVISION_BINDING_KIND,
            geometry=proposal["geometry"],
            interval_end_exclusive=selected_region["cluster_end_document_line_ordinal_exclusive"],
            interval_start=selected_region["cluster_start_document_line_ordinal"],
            source=projected_source,
            source_role=_PROVISION_GENERIC_ROLE,
            source_scope_role=(proposal["matched_within_role"] or compiled_family["family_id"]),
            target_role=proposal["target_role"],
        )
        definition = definitions[proposal["target_role"]]
        projected_source.update(
            {
                "matched_within_role": proposal["matched_within_role"],
                "preferred_ordinal": definition["preferred_ordinal"],
                "presence": definition["presence"],
                "role": proposal["target_role"],
                "role_kind": definition["role_kind"],
                "source_scope_binding": receipt,
            }
        )
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


def _retarget_recursive_parent_provision_dash_rescues(
    visible_dash_rescues: Any,
    preliminary_matches: Sequence[Mapping[str, Any]],
    projected_matches: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    if type(visible_dash_rescues) is not tuple:
        raise _error("recursive parent provision dash inputs must remain one exact tuple")
    projected_by_retrieval = {
        match.get("retrieval_occurrence_id", match.get("occurrence_id")): match
        for match in projected_matches
    }
    targets_by_page: dict[int, list[str]] = {}
    for source in preliminary_matches:
        if source["role"] != _PROVISION_GENERIC_ROLE:
            continue
        target = projected_by_retrieval.get(source["retrieval_occurrence_id"])
        if target is None or target["role"] == _PROVISION_GENERIC_ROLE:
            continue
        targets_by_page.setdefault(source["page_sequence"], []).append(target["role"])
    result = []
    for raw in visible_dash_rescues:
        if type(raw) is not dict:
            raise _error("recursive parent provision dash item must remain one mapping")
        # Detector regions intentionally carry opaque PNG bytes.  Copy only
        # the outer routing envelope so those authenticated payloads retain
        # their exact object/value identity and never enter the JSON cloner.
        item = dict(raw)
        targets = targets_by_page.get(item.get("page_sequence"), [])
        if item.get("role") == _PROVISION_GENERIC_ROLE and len(targets) == 1:
            item["role"] = targets[0]
        result.append(item)
    return tuple(result)


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


def _project_unique_contextual_structural_body_matches_v1(
    pages: Sequence[Mapping[str, Any]],
    matches: Sequence[Mapping[str, Any]],
    region: Mapping[str, Any],
    *,
    row_axis: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Fence one exact contextual body from sibling tables under a broad parent.

    Some notes print several independent analysis tables beneath one explicit
    accounting parent.  A target subgroup can therefore be preceded and
    followed by exact sibling structural headings while a context-free alias
    from either sibling still happens to match one family role.  Retain only
    the visual interval of one uniquely evidenced direct structural subgroup
    when it owns at least two distinct visible additive roles and at least one
    exact sibling heading proves that the outer parent contains multiple
    subviews.  No sibling heading means no projection, preserving ordinary
    flat/contextual layouts byte-for-byte.

    This is source-scope selection only.  It grants no row, numeric,
    accounting, period/unit, schema, or mapping authority; downstream stages
    still rebuild the rows and require exhaustive direct-frontier closure.
    """

    source_matches = [canonical_clone_v1(match) for match in matches]
    # The production build invokes this projector before the public scope
    # decorator, while focused callers may already provide decorated records.
    # Derive scope ownership privately for selection and return the caller's
    # original record shape so this source-only fence cannot mutate persisted
    # occurrence bytes outside the selected subset.
    decorated = (
        source_matches
        if all(
            type(match.get("occurrence_id")) is str
            and type(match.get("scope_owner_occurrence_id")) is str
            and "scope_owner_role" in match
            for match in source_matches
        )
        else _decorate_scopes(source_matches, region)
    )

    rows_by_occurrence_id: dict[str, list[Mapping[str, Any]]] = {}
    if row_axis is not None:
        if type(row_axis) is not dict or type(row_axis.get("rows")) is not list:
            raise _error("contextual structural body row-axis input drifted")
        for row in row_axis["rows"]:
            label_match = row.get("label_match") if type(row) is dict else None
            occurrence_id = label_match.get("occurrence_id") if type(label_match) is dict else None
            if type(occurrence_id) is not str or not occurrence_id:
                raise _error("contextual structural body row lost its occurrence identity")
            rows_by_occurrence_id.setdefault(occurrence_id, []).append(row)

    def visible_values(match: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        if row_axis is None:
            return _same_row_numeric_samples(pages, match)
        rows = rows_by_occurrence_id.get(match["occurrence_id"], [])
        if len(rows) != 1:
            return []
        row = rows[0]
        values = row.get("values")
        if (
            row.get("status") != "VISIBLE_VALUE_LANES_BOUND"
            or row.get("missing_column_ordinals") != []
            or type(values) is not list
            or not values
            or [value.get("column_ordinal") for value in values] != list(range(len(values)))
        ):
            return []
        return values

    page_by_sequence = {page["page_sequence"]: page for page in pages}

    def visual_key(match: Mapping[str, Any]) -> tuple[int, float, int]:
        page = page_by_sequence.get(match.get("page_sequence"))
        indices = row_v1._match_source_line_indices(match)
        if type(page) is not dict:
            raise _error("contextual structural body lost its source page")
        boxes = [line["bbox"] for line in page["lines"] if line["line_ordinal"] in indices]
        if len(boxes) != len(indices):
            raise _error("contextual structural body lost exact source geometry")
        return (
            match["page_sequence"],
            min((box[1] + box[3]) / 2 for box in boxes),
            match["document_line_ordinal"],
        )

    exact_root_structural = [
        match
        for match in decorated
        if match.get("role_kind") == "STRUCTURAL_GROUP"
        and match.get("scope_owner_role") is None
        and str(match.get("match_kind", "")).startswith("EXACT_")
        and not visible_values(match)
        and type(match.get("occurrence_id")) is str
        and match["occurrence_id"]
    ]
    candidates: list[dict[str, Any]] = []
    for owner in exact_root_structural:
        direct_visible = [
            match
            for match in decorated
            if match.get("role_kind") == "ADDITIVE_CHILD"
            and match.get("scope_owner_occurrence_id") == owner["occurrence_id"]
            and visible_values(match)
        ]
        if len({match["role"] for match in direct_visible}) >= 2:
            candidates.append(owner)
    if len(candidates) != 1:
        return source_matches

    owner = candidates[0]
    owner_key = visual_key(owner)
    siblings = [
        match
        for match in decorated
        if match.get("role_kind") == "SOURCE_ONLY_GROUP_PARENT"
        and match.get("scope_owner_role") is None
        and str(match.get("match_kind", "")).startswith("EXACT_")
        and not visible_values(match)
    ]
    if not siblings:
        # A contextual subgroup can begin on the sole continuation page after
        # one or more valued sibling tables under the broad outer parent.  In
        # that shape the subgroup heading itself is the exact visual fence;
        # requiring a separate SOURCE_ONLY_GROUP_PARENT sibling would retain
        # the preceding table and manufacture competing body grids.  Admit the
        # boundary only when the outer region starts on the immediately prior
        # page, every valued non-owned additive row is strictly before the
        # subgroup, and every matched record at/after the subgroup is owned by
        # it.  Same-page sibling-free layouts remain byte-for-byte unchanged.
        region_page = region.get("page_sequence")
        owner_page = owner.get("page_sequence")
        unowned_visible = [
            match
            for match in decorated
            if match.get("role_kind") == "ADDITIVE_CHILD"
            and match.get("scope_owner_occurrence_id") != owner["occurrence_id"]
            and visible_values(match)
        ]
        owner_visible = [
            match
            for match in decorated
            if match.get("role_kind") == "ADDITIVE_CHILD"
            and match.get("scope_owner_occurrence_id") == owner["occurrence_id"]
            and visible_values(match)
        ]
        owner_lane_counts = {len(visible_values(match)) for match in owner_visible}
        unowned_additive = [
            match
            for match in decorated
            if match.get("role_kind") == "ADDITIVE_CHILD"
            and match.get("scope_owner_occurrence_id") != owner["occurrence_id"]
        ]
        prior_unowned_pages = {
            match["page_sequence"]
            for match in unowned_additive
            if match["page_sequence"] < owner["page_sequence"]
        }
        prior_visible_pages = {
            match["page_sequence"]
            for match in unowned_visible
            if match["page_sequence"] < owner["page_sequence"]
        }
        post_owner_unowned = [
            match
            for match in decorated
            if match.get("occurrence_id") != owner["occurrence_id"]
            and visual_key(match) >= owner_key
            and match.get("scope_owner_occurrence_id") != owner["occurrence_id"]
        ]
        if (
            type(region_page) is not int
            or type(owner_page) is not int
            or region.get("continuation_page_count") != 1
            or owner_page != region_page + 1
            or not unowned_visible
            or (
                row_axis is not None
                and (not prior_unowned_pages or not prior_unowned_pages <= prior_visible_pages)
            )
            or len(owner_lane_counts) != 1
            or 0 in owner_lane_counts
            or any(len(visible_values(match)) in owner_lane_counts for match in unowned_visible)
            or any(visual_key(match) >= owner_key for match in unowned_visible)
            or post_owner_unowned
        ):
            return source_matches
    following = [match for match in siblings if visual_key(match) > owner_key]
    stop_key: tuple[int, float, int] | None = None
    if following:
        first_key = min(visual_key(match) for match in following)
        if sum(visual_key(match) == first_key for match in following) != 1:
            return source_matches
        stop_key = first_key

    projected = [
        match
        for match in decorated
        if visual_key(match) >= owner_key and (stop_key is None or visual_key(match) < stop_key)
    ]
    if owner["occurrence_id"] not in {match.get("occurrence_id") for match in projected}:
        raise _error("contextual structural body projection lost its exact owner")
    projected_direct_roles = {
        match["role"]
        for match in projected
        if match.get("role_kind") == "ADDITIVE_CHILD"
        and match.get("scope_owner_occurrence_id") == owner["occurrence_id"]
        and visible_values(match)
    }
    if len(projected_direct_roles) < 2:
        raise _error("contextual structural body projection lost its direct evidence")
    projected_occurrence_ids = {match["occurrence_id"] for match in projected}
    return [
        source
        for source, working in zip(source_matches, decorated, strict=True)
        if working["occurrence_id"] in projected_occurrence_ids
    ]


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
            and anchor_check.get("status") in _ONE_EDIT_AUTHORITY_BOUND_STATUSES
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
        elif kind == _RECURSIVE_PARENT_PROVISION_BINDING_KIND:
            binding_specs = [
                spec
                for spec in _RECURSIVE_PARENT_PROVISION_BINDING_SPECS
                if spec["target_role"] == role
            ]
            binding_spec = binding_specs[0] if len(binding_specs) == 1 else None
            expected_scope_role = (
                binding_spec["parent_role"]
                if binding_spec is not None and binding_spec["parent_role"] is not None
                else "INTERBANK_DEPOSITS_AND_LOANS"
            )
            expected_anchor_role = (
                binding_spec["parent_role"]
                if binding_spec is not None and binding_spec["parent_role"] is not None
                else "INTERBANK_LOAN_GROUP"
            )
            reviewed_matrix_valid = (
                binding_spec is not None
                and value["source_role"] == _PROVISION_GENERIC_ROLE
                and value["source_scope_role"] == expected_scope_role
                and exact_source
                and exact_anchor
                and source_proof_shape_valid
                and anchor_proof_shape_valid
                and anchor.get("role") == expected_anchor_role
                and _recursive_parent_provision_geometry_is_valid(
                    geometry,
                    label_match=label_match,
                    role=role,
                )
                and geometry["ordered_source_label_bboxes"][-1]
                == value["source_span"]["source_label_bbox"]
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
                    **(
                        {"crop_ref": canonical_clone_v1(line["crop_ref"])}
                        if "crop_ref" in line
                        else {}
                    ),
                    "numeric_recognition": canonical_clone_v1(line["numeric_recognition"]),
                    **({"sample_id": line["sample_id"]} if "sample_id" in line else {}),
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
    *,
    prepared_source_exact_axis_cache: dict[tuple[str, str], Any] | None,
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
            prepared_source_exact_axis_cache=prepared_source_exact_axis_cache,
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
        if type(check) is dict and check["status"] in _ONE_EDIT_AUTHORITY_BOUND_STATUSES:
            match["one_edit_exact_source_authority_check"] = canonical_clone_v1(check)
    return receipt, decorated


def _exact_physical_source_span_signature_v1(item: Mapping[str, Any]) -> tuple[Any, ...]:
    """Identify one occupied source span independently of its proposed role."""

    explicit_indices = item.get("source_line_indices")
    return (
        item["page_sequence"],
        item["document_line_ordinal"],
        item["end_document_line_ordinal"],
        item["source_line_index"],
        item["end_source_line_index"],
        tuple(explicit_indices) if type(explicit_indices) is list else None,
    )


def _unique_exact_bound_source_challengers_v1(
    eligible: Sequence[tuple[dict[str, Any], Mapping[str, Any]]],
) -> list[tuple[dict[str, Any], Mapping[str, Any]]]:
    """Admit only one role and one challenger for each unoccupied source span."""

    by_role: dict[str, list[tuple[dict[str, Any], Mapping[str, Any]]]] = {}
    by_physical_signature: dict[
        tuple[Any, ...], list[tuple[dict[str, Any], Mapping[str, Any]]]
    ] = {}
    for item in eligible:
        by_role.setdefault(item[0]["role"], []).append(item)
        by_physical_signature.setdefault(
            _exact_physical_source_span_signature_v1(item[0]), []
        ).append(item)
    return [
        item
        for item in eligible
        if len(by_role[item[0]["role"]]) == 1
        and len(by_physical_signature[_exact_physical_source_span_signature_v1(item[0])]) == 1
    ]


def _project_exact_bound_source_context_challengers_v1(
    pages: Sequence[Mapping[str, Any]],
    compiled_family: Mapping[str, Any],
    selected_region: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Recover one otherwise absent exact-PP contextual additive row.

    V4 topology retrieval is intentionally VietOCR-only.  The sealed topology
    matcher nevertheless has a stricter, existing source-channel match kind:
    it uses PP-OCR only when VietOCR does not match and the bound PP surface is
    an exact declared alias.  Ordinarily that challenger is useful only while
    auditing a retrieved occurrence.  A filing can instead lose the entire
    leaf when VietOCR is more than one edit from the alias.

    This post-retrieval projector admits that existing exact challenger only
    for an otherwise absent contextual additive role under the *same physical
    structural owner already selected exactly by VietOCR*.  It does not admit
    parents, totals, context-free aliases, wrapped labels, repeated candidates,
    owner substitutions, or rows without visible same-row numeric evidence.
    Accounting closure remains downstream and supplies no authority here.
    """

    start = selected_region["cluster_start_document_line_ordinal"]
    stop = selected_region["cluster_end_document_line_ordinal_exclusive"]
    topology_pages = [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "source_line_index": line["line_ordinal"],
                    "source_text": line["numeric_recognition"]["raw_prediction"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]
    try:
        parsed_source_pages = topology_v1._pages(topology_pages)  # noqa: SLF001
        source_hits, _line_axis, _page_axis = topology_v1._document_hits(  # noqa: SLF001
            parsed_source_pages,
            compiled_family,
        )
        source_records = topology_v1._child_records_in_range(  # noqa: SLF001
            source_hits["children"],
            compiled_family,
            retain_all_occurrences=True,
            start=start,
            stop=stop,
        )
    except topology_v1.AccountingFamilyTopologyV1Error as exc:
        raise _error("bound-source contextual challenger replay failed") from exc

    definition_by_role = {child["role"]: child for child in compiled_family["children"]}
    original_roles = {match["role"] for match in matches}
    page_by_sequence = {page["page_sequence"]: page for page in pages}
    match_by_occurrence_id = {match["occurrence_id"]: match for match in matches}

    def has_exact_recursive_owner_chain(owner: Mapping[str, Any]) -> bool:
        cursor = owner
        visited: set[str] = set()
        while cursor.get("scope_owner_role") is not None:
            parent_id = cursor.get("scope_owner_occurrence_id")
            if type(parent_id) is not str or parent_id in visited:
                return False
            visited.add(parent_id)
            parent = match_by_occurrence_id.get(parent_id)
            if (
                parent is None
                or parent["role"] != cursor["scope_owner_role"]
                or not str(parent["match_kind"]).startswith("EXACT_")
            ):
                return False
            cursor = parent
        return True

    original_physical_signatures = {
        _exact_physical_source_span_signature_v1(match) for match in matches
    }

    def visual_position(hit: Mapping[str, Any]) -> tuple[int, float]:
        bbox = hit["_bbox"]
        return hit["page_sequence"], (bbox[1] + bbox[3]) / 2

    def precedes(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        return visual_position(left) < visual_position(right)

    eligible: list[tuple[dict[str, Any], Mapping[str, Any]]] = []
    for record in source_records:
        within_role = record.get("matched_within_role")
        definition = definition_by_role[record["role"]]
        if (
            record["match_kind"] != _EXACT_BOUND_SOURCE_CONTEXT_CHALLENGER_MATCH_KIND
            or definition["role_kind"] != "ADDITIVE_CHILD"
            or type(within_role) is not str
            or not within_role
            or record["role"] in original_roles
            or record["document_line_ordinal"] != record["end_document_line_ordinal"]
            or record["source_line_index"] != record["end_source_line_index"]
            or "source_line_indices" in record
            or _exact_physical_source_span_signature_v1(record) in original_physical_signatures
        ):
            continue
        page = page_by_sequence.get(record["page_sequence"])
        source_index = record["source_line_index"]
        if type(page) is not dict or not 0 <= source_index < len(page["lines"]):
            continue
        line = page["lines"][source_index]
        source_surface = line["numeric_recognition"]["raw_prediction"]
        alias_pointers = [
            (child["role"], matcher_ordinal, alias_ordinal)
            for child in compiled_family["children"]
            for matcher_ordinal, matcher in enumerate(child["matchers"])
            if matcher["within_role"] == within_role
            for alias_ordinal, alias in enumerate(matcher["aliases"])
            if alias == record["normalized_surface"]
        ]
        if (
            len(alias_pointers) != 1
            or alias_pointers[0][0] != record["role"]
            or source_surface != record["surface"]
            or normalize_vietnamese_anchor_v1(source_surface) != record["normalized_surface"]
            or type(line.get("crop_ref")) is not dict
            or type(line.get("sample_id")) is not str
            or not line["sample_id"]
            or not _same_row_numeric_samples(pages, record)
        ):
            continue
        raw_hits = [
            hit
            for hit in source_hits["children"][record["role"]]
            if hit.get("_within_role") == within_role
            and hit["match_kind"] == record["match_kind"]
            and hit["document_line_ordinal"] == record["document_line_ordinal"]
            and hit["end_document_line_ordinal"] == record["end_document_line_ordinal"]
            and hit["source_line_index"] == record["source_line_index"]
            and hit["end_source_line_index"] == record["end_source_line_index"]
        ]
        if len(raw_hits) != 1:
            continue
        hit = raw_hits[0]
        source_contexts = [
            owner_hit
            for owner_hit in source_hits["children"].get(within_role, [])
            if start < owner_hit["document_line_ordinal"] < stop and precedes(owner_hit, hit)
        ]
        if not source_contexts:
            continue
        source_owner = max(source_contexts, key=visual_position)
        original_owners = [
            owner
            for owner in matches
            if owner["role"] == within_role
            and owner["role_kind"] == "STRUCTURAL_GROUP"
            and str(owner["match_kind"]).startswith("EXACT_")
            and owner["page_sequence"] == source_owner["page_sequence"]
            and owner["document_line_ordinal"] == source_owner["document_line_ordinal"]
            and owner["end_document_line_ordinal"] == source_owner["end_document_line_ordinal"]
            and owner["source_line_index"] == source_owner["source_line_index"]
            and owner["end_source_line_index"] == source_owner["end_source_line_index"]
        ]
        if len(original_owners) != 1 or not has_exact_recursive_owner_chain(original_owners[0]):
            continue
        eligible.append((canonical_clone_v1(record), original_owners[0]))

    # More than one source-only row for one absent role, or more than one role
    # proposed for one source span, is an occupancy ambiguity rather than an
    # occurrence-expansion opportunity.
    admitted = _unique_exact_bound_source_challengers_v1(eligible)
    if not admitted:
        return [canonical_clone_v1(match) for match in matches]

    undecorated = []
    for match in matches:
        raw = canonical_clone_v1(match)
        raw.pop("occurrence_id", None)
        raw.pop("scope_owner_occurrence_id", None)
        raw.pop("scope_owner_role", None)
        undecorated.append(raw)
    admitted_signatures: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for challenger, owner in admitted:
        challenger["role_occurrence_ordinal"] = 0
        challenger["source_label_bbox"] = _source_line_bbox(pages, challenger)
        challenger["retrieval_role"] = challenger["role"]
        challenger["retrieval_role_kind"] = challenger["role_kind"]
        challenger["retrieval_role_occurrence_ordinal"] = 0
        challenger["retrieval_within_role"] = challenger["matched_within_role"]
        admitted_signatures[_exact_physical_source_span_signature_v1(challenger)] = owner
        undecorated.append(challenger)
    undecorated.sort(
        key=lambda item: (
            item["document_line_ordinal"],
            item["end_document_line_ordinal"],
            item["preferred_ordinal"],
            item["role"],
        )
    )
    decorated = _decorate_scopes(undecorated, selected_region)
    for match in decorated:
        owner = admitted_signatures.get(_exact_physical_source_span_signature_v1(match))
        if owner is None:
            continue
        if match["scope_owner_occurrence_id"] != owner["occurrence_id"]:
            raise _error("bound-source challenger changed its exact structural owner")
        match["retrieval_occurrence_id"] = match["occurrence_id"]
        match["retrieval_scope_owner_occurrence_id"] = match["scope_owner_occurrence_id"]
    return decorated


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


def _unique_dash_occurrence_binding(match: Mapping[str, Any]) -> dict[str, Any]:
    """Project the exact semantic row fields sealed into the V4 receipt."""

    return {
        "document_line_ordinal": match["document_line_ordinal"],
        "end_document_line_ordinal": match["end_document_line_ordinal"],
        "end_source_line_index": match["end_source_line_index"],
        "label_match_sha256": canonical_json_sha256_v1(match),
        "occurrence_id": match["occurrence_id"],
        "page_sequence": match["page_sequence"],
        "role": match["role"],
        "role_kind": match["role_kind"],
        "scope_owner_occurrence_id": match["scope_owner_occurrence_id"],
        "scope_owner_role": match["scope_owner_role"],
        "source_line_index": match["source_line_index"],
    }


def _unique_dash_parent_binding(match: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "document_line_ordinal": match["document_line_ordinal"],
        "end_document_line_ordinal": match["end_document_line_ordinal"],
        "end_source_line_index": match["end_source_line_index"],
        "label_match_sha256": canonical_json_sha256_v1(match),
        "occurrence_id": match["occurrence_id"],
        "page_sequence": match["page_sequence"],
        "role": match["role"],
        "role_kind": match["role_kind"],
        "source_line_index": match["source_line_index"],
    }


def _unique_dash_lane_binding(
    projection: Mapping[str, Any], region: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "column_center": projection["column_center"],
        "column_ordinal": projection["column_ordinal"],
        "document_ordinal": region["document_ordinal"],
        "index_id": region["index_id"],
        "physical_page": region["physical_page"],
        "proposed_raw_pixel_bbox": canonical_clone_v1(region["proposed_raw_pixel_bbox"]),
        "recognition_raw_pixel_bbox": canonical_clone_v1(region["recognition_raw_pixel_bbox"]),
        "region_id": region["region_id"],
        "region_png_ref": canonical_clone_v1(region["region_png_ref"]),
        "render_id": region["render_id"],
        "render_ref": canonical_clone_v1(region["render_ref"]),
        "white_border": canonical_clone_v1(region["white_border"]),
    }


def _unique_dash_rescued_value(
    row: Mapping[str, Any], projection: Mapping[str, Any], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    crop_ref = receipt["original_dash_evidence"]["crop_ref"]
    return {
        "bbox": canonical_clone_v1(projection["recognition_raw_pixel_bbox"]),
        "column_center": projection["column_center"],
        "column_ordinal": projection["column_ordinal"],
        "crop_ref": {
            "path": f"authenticated-render-region/{projection['region_id']}.png",
            "sha256": crop_ref["sha256"],
            "size_bytes": crop_ref["size_bytes"],
        },
        "line_ordinal": row["label_match"]["source_line_index"],
        "page_sequence": projection["page_sequence"],
        "parsed_token": row_v1.parse_visible_financial_numeric_token_v1("-"),
        "raw_prediction": "-",
        "reader_score": 1.0,
        "row_affinity": None,
        "sample_id": projection["region_id"],
    }


def _project_unique_dash_speck_rescues_v2(
    axis: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]],
    visible_dash_rescues: Any,
    *,
    topology_candidates_id: str | None,
    topology_scan_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Promote only V4's exact one-dash-plus-isolated-speck detector holes."""

    if topology_candidates_id is None:
        return canonical_clone_v1(axis), []
    if type(visible_dash_rescues) is not tuple:
        raise _error("V4 unique-dash rescue inputs must remain one exact tuple")
    completed = canonical_clone_v1(axis)
    raw_regions: dict[str, dict[str, Any]] = {}
    for raw in visible_dash_rescues:
        if (
            type(raw) is not dict
            or set(raw) != row_v1._RESCUE_INPUT_FIELDS
            or type(raw.get("page_sequence")) is not int
        ):
            raise _error("V4 unique-dash rescue input shape drifted")
        try:
            region = row_v1._region_record(raw["region"], page_sequence=raw["page_sequence"])
        except row_v1.AccountingFamilyRowAxisV1Error as exc:
            raise _error("V4 unique-dash authenticated region drifted") from exc
        if region["region_id"] in raw_regions:
            raise _error("V4 unique-dash authenticated region repeats")
        raw_regions[region["region_id"]] = region
    matches_by_id = {match["occurrence_id"]: match for match in matches}
    if len(matches_by_id) != len(matches):
        raise _error("V4 unique-dash occurrence denominator repeats")
    receipts: list[dict[str, Any]] = []
    claimed_keys: set[tuple[str, int]] = set()
    for projection in completed["visible_dash_rescues"]:
        original = projection.get("dash_evidence")
        if (
            projection.get("classification") != "UNRESOLVED_NOT_ONE_DASH_GLYPH"
            or type(original) is not dict
            or original.get("classification") != "UNRESOLVED_NOT_ONE_DASH_GLYPH"
            or original.get("glyph_metrics", {}).get("component_count") not in {2, 3, 4}
        ):
            continue
        region = raw_regions.get(projection["region_id"])
        if region is None:
            continue
        candidates = [
            row
            for row in completed["rows"]
            if row["role"] == projection["role"]
            and row["label_match"]["page_sequence"] == projection["page_sequence"]
            and projection["column_ordinal"] in row["missing_column_ordinals"]
        ]
        role_page_matches = [
            match
            for match in matches
            if match["role"] == projection["role"]
            and match["page_sequence"] == projection["page_sequence"]
        ]
        if len(candidates) != 1 or len(role_page_matches) != 1:
            # Repeated same-role rows on one page are intentionally ineligible.
            continue
        row = candidates[0]
        occurrence = matches_by_id.get(row["label_match"].get("occurrence_id"))
        parent = (
            matches_by_id.get(occurrence.get("scope_owner_occurrence_id"))
            if type(occurrence) is dict
            else None
        )
        if (
            type(occurrence) is not dict
            or role_page_matches[0]["occurrence_id"] != occurrence["occurrence_id"]
            or occurrence.get("scope_owner_role") is None
            or type(parent) is not dict
            or parent["occurrence_id"] != occurrence["scope_owner_occurrence_id"]
            or parent["role"] != occurrence["scope_owner_role"]
        ):
            continue
        key = (occurrence["occurrence_id"], projection["column_ordinal"])
        if key in claimed_keys:
            raise _error("V4 unique-dash occurrence lane repeats")
        binding = {
            "lane_binding": _unique_dash_lane_binding(projection, region),
            "occurrence_binding": _unique_dash_occurrence_binding(occurrence),
            "parent_binding": _unique_dash_parent_binding(parent),
            "source_row_sha256": canonical_json_sha256_v1(row),
            "topology_candidates_id": topology_candidates_id,
            "topology_scan_id": topology_scan_id,
        }
        try:
            receipt = speck_dash_v1.build_family_first_authenticated_unique_dash_speck_v1(
                crop_png_bytes=region["region_png_bytes"],
                input_binding=binding,
            )
        except speck_dash_v1.FamilyFirstAuthenticatedUniqueDashSpeckV1Error:
            continue
        rescued = _unique_dash_rescued_value(row, projection, receipt)
        row["values"].append(rescued)
        row["values"].sort(key=lambda item: item["column_ordinal"])
        row["missing_column_ordinals"].remove(projection["column_ordinal"])
        receipts.append(receipt)
        claimed_keys.add(key)
    for row in completed["rows"]:
        if not row["missing_column_ordinals"]:
            row["status"] = "VISIBLE_VALUE_LANES_BOUND"
        elif row["status"] in {
            "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS",
            "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES",
        }:
            # V1 has already authenticated every remaining missing lane as a
            # blank pixel crop under one complete structural parent.  The V4
            # speck bridge is additive: a failed or unrelated promotion must
            # not erase that sealed optional-row disposition and turn a safe
            # blank into an unresolved accounting cell.
            row["status"] = (
                "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES"
                if row["values"]
                else "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS"
            )
        else:
            row["status"] = (
                "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
                if row["values"]
                else "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL"
            )
    return _regenerate_v1_axis(completed), receipts


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
    permitted_label_sample_ids: frozenset[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    numeric_left = min(line["bbox"][0] for line in ordered_numeric_lines)
    source_line_axis = []
    for line in local_lines:
        if (
            permitted_label_sample_ids is not None
            and line["sample_id"] not in permitted_label_sample_ids
        ):
            continue
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


def _extreme_margin_v2_candidate_surface_is_nonnumeric(line: Mapping[str, Any]) -> bool:
    surface = line["vietocr_text"].strip()
    compact = "".join(normalize_vietnamese_anchor_v1(surface).split())
    return (
        not any(character.isdigit() for character in surface)
        and row_v1.parse_visible_financial_numeric_token_v1(surface)["classification"]
        not in _EXTREME_MARGIN_ADMITTED_NUMERIC_CLASSIFICATIONS
        and len(compact) <= 4
    )


def _extreme_margin_v2_candidate_surface_mode(line: Mapping[str, Any]) -> str | None:
    if _extreme_margin_v2_candidate_surface_is_nonnumeric(line):
        return "NONNUMERIC_COMPACT"
    surface = line["vietocr_text"].strip()
    compact = "".join(surface.split())
    numeric_raw = line.get("numeric_raw_prediction")
    if type(numeric_raw) is not str:
        recognition = line.get("numeric_recognition")
        numeric_raw = recognition.get("raw_prediction") if type(recognition) is dict else None
    if type(numeric_raw) is not str:
        return None
    raw = numeric_raw.strip()
    surface_token = row_v1.parse_visible_financial_numeric_token_v1(surface)
    raw_token = row_v1.parse_visible_financial_numeric_token_v1(raw)
    if (
        re.fullmatch(r"[0-9]{2,4}", compact)
        and surface_token["classification"] == "SIGNED_NUMBER"
        and raw_token["classification"] == "SIGNED_NUMBER"
        and raw_token["sign"] == 1
        and raw_token["scale"] == 0
        and 1 <= raw_token["coefficient"] <= 9
        and surface_token["coefficient"] != raw_token["coefficient"]
    ):
        return "NUMERIC_SINGLE_DIGIT_ROTATED_STAMP"
    return None


def _extreme_margin_v2_band_axis(
    page: Mapping[str, Any], *, margin_boundary: int
) -> list[dict[str, Any]]:
    page_width = page["page_width"]
    return sorted(
        (
            _extreme_margin_line_record(line)
            for line in page["lines"]
            if line["bbox"][0] >= margin_boundary
            and line["bbox"][2] <= page_width
            and (
                line["vietocr_text"].strip()
                or line["numeric_recognition"]["raw_prediction"].strip()
            )
        ),
        key=lambda item: (item["line_ordinal"], item["bbox"]),
    )


def _extreme_margin_v2_geometric_peer_ordinals(
    source_line_axis: Sequence[Mapping[str, Any]], candidate: Mapping[str, Any]
) -> list[int]:
    candidate_bbox = candidate["bbox"]
    candidate_height = candidate_bbox[3] - candidate_bbox[1]
    peers = []
    for line in source_line_axis:
        if line["line_ordinal"] == candidate["line_ordinal"]:
            continue
        bbox = line["bbox"]
        vertical_gap = max(0, candidate_bbox[1] - bbox[3], bbox[1] - candidate_bbox[3])
        if (
            min(candidate_bbox[2], bbox[2]) <= max(candidate_bbox[0], bbox[0])
            or vertical_gap > 6 * max(candidate_height, bbox[3] - bbox[1])
            or not _extreme_margin_peer_surfaces_are_nonnumeric(line)
        ):
            continue
        peers.append(line["line_ordinal"])
    return sorted(peers)


def _extreme_margin_v2_component_qualifies(
    component: Mapping[str, Any],
    *,
    margin_boundary: int,
    target_bbox: Sequence[int],
    minimum_component_height: int,
    minimum_original_ink_pixels: int,
    minimum_side_extent_pixels: int,
    minimum_side_ink_pixels: int,
    minimum_target_overlap_ink_pixels: int,
    minimum_vertical_extension_pixels: int,
) -> bool:
    bbox = component["bbox"]
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return (
        bbox[0] >= margin_boundary
        and min(bbox[2], target_bbox[2]) > max(bbox[0], target_bbox[0])
        and min(bbox[3], target_bbox[3]) > max(bbox[1], target_bbox[1])
        and height >= minimum_component_height
        and height * 5 >= width * 6
        and component["original_ink_pixel_count"] >= minimum_original_ink_pixels
        and component["chromatic_original_ink_pixel_count"] * 2
        >= component["original_ink_pixel_count"]
        and component["target_overlap_ink_pixel_count"] >= minimum_target_overlap_ink_pixels
        and component["clear_extent_above_center"] >= minimum_side_extent_pixels
        and component["clear_extent_below_center"] >= minimum_side_extent_pixels
        and component["above_center_original_ink_pixel_count"] >= minimum_side_ink_pixels
        and component["below_center_original_ink_pixel_count"] >= minimum_side_ink_pixels
        and component["vertical_extension_outside_target"] >= minimum_vertical_extension_pixels
    )


def _extreme_margin_v2_numeric_stamp_component_qualifies(
    component: Mapping[str, Any],
    *,
    margin_boundary: int,
    target_bbox: Sequence[int],
    body_text_scale: float,
    candidate_ink_pixel_count: int,
) -> bool:
    bbox = component["bbox"]
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    target_height = target_bbox[3] - target_bbox[1]
    return (
        candidate_ink_pixel_count > 0
        and bbox[0] >= margin_boundary
        and min(bbox[2], target_bbox[2]) > max(bbox[0], target_bbox[0])
        and min(bbox[3], target_bbox[3]) > max(bbox[1], target_bbox[1])
        and bbox[1] <= target_bbox[1]
        and bbox[3] >= target_bbox[3]
        and height >= target_height
        and height >= width
        and target_height * 5 >= 7 * body_text_scale
        and component["original_ink_pixel_count"] >= max(64, 2 * target_height)
        and component["chromatic_original_ink_pixel_count"] * 4
        >= component["original_ink_pixel_count"] * 3
        and component["target_overlap_ink_pixel_count"] * 4 >= candidate_ink_pixel_count * 3
        and component["clear_extent_above_center"] >= max(4, (target_height + 7) // 8)
        and component["clear_extent_below_center"] >= max(4, (target_height + 7) // 8)
        and component["above_center_original_ink_pixel_count"] >= max(8, target_height // 2)
        and component["below_center_original_ink_pixel_count"] >= max(8, target_height // 2)
    )


def _authenticated_extreme_margin_v2_component_proof(
    *,
    image: Any,
    render_record: Mapping[str, Any],
    render_id: str,
    candidate: Mapping[str, Any],
    margin_boundary: int,
    scale: float,
    numeric_stamp_mode: bool = False,
    candidate_ink_pixel_count: int = 0,
) -> dict[str, Any] | None:
    target_bbox = candidate["bbox"]
    target_height = target_bbox[3] - target_bbox[1]
    expanded_bbox = [
        margin_boundary,
        max(0, target_bbox[1] - 2 * target_height),
        image.width,
        min(image.height, target_bbox[3] + 2 * target_height),
    ]
    if (
        expanded_bbox[0] >= expanded_bbox[2]
        or expanded_bbox[1] >= expanded_bbox[3]
        or render_record["render_ref"]["pixel_width"] != image.width
        or render_record["render_ref"]["pixel_height"] != image.height
    ):
        return None
    expanded = image.crop(tuple(expanded_bbox))
    expanded_rgb = expanded.tobytes()
    pixels = list(zip(expanded_rgb[0::3], expanded_rgb[1::3], expanded_rgb[2::3], strict=True))
    ink_threshold = 220
    chroma_spread_threshold = 30
    original_ink = bytes(255 if min(pixel) < ink_threshold else 0 for pixel in pixels)
    kernel_radius = max(1, min(7, int(scale // 8)))
    kernel_size = 2 * kernel_radius + 1
    closed = (
        Image.frombytes("L", expanded.size, original_ink)
        .filter(ImageFilter.MaxFilter(kernel_size))
        .filter(ImageFilter.MinFilter(kernel_size))
    )
    closed_bytes = bytes(closed.tobytes())
    width, height = expanded.size
    visited = bytearray(len(closed_bytes))
    component_axis = []
    candidate_center_twice = target_bbox[1] + target_bbox[3]
    for origin in range(len(closed_bytes)):
        if not closed_bytes[origin] or visited[origin]:
            continue
        visited[origin] = 1
        stack = [origin]
        indices = []
        while stack:
            index = stack.pop()
            indices.append(index)
            x = index % width
            y = index // width
            for next_y in range(max(0, y - 1), min(height, y + 2)):
                row_offset = next_y * width
                for next_x in range(max(0, x - 1), min(width, x + 2)):
                    neighbor = row_offset + next_x
                    if closed_bytes[neighbor] and not visited[neighbor]:
                        visited[neighbor] = 1
                        stack.append(neighbor)
        xs = [index % width for index in indices]
        ys = [index // width for index in indices]
        bbox = [
            expanded_bbox[0] + min(xs),
            expanded_bbox[1] + min(ys),
            expanded_bbox[0] + max(xs) + 1,
            expanded_bbox[1] + max(ys) + 1,
        ]
        original_indices = [index for index in indices if original_ink[index]]
        chromatic_indices = [
            index
            for index in original_indices
            if max(pixels[index]) - min(pixels[index]) >= chroma_spread_threshold
        ]
        target_overlap = 0
        above = 0
        below = 0
        for index in original_indices:
            absolute_x = expanded_bbox[0] + index % width
            absolute_y = expanded_bbox[1] + index // width
            if (
                target_bbox[0] <= absolute_x < target_bbox[2]
                and target_bbox[1] <= absolute_y < target_bbox[3]
            ):
                target_overlap += 1
            pixel_center_twice = 2 * absolute_y + 1
            if pixel_center_twice < candidate_center_twice:
                above += 1
            elif pixel_center_twice > candidate_center_twice:
                below += 1
        component_axis.append(
            {
                "above_center_original_ink_pixel_count": above,
                "bbox": bbox,
                "below_center_original_ink_pixel_count": below,
                "chromatic_original_ink_pixel_count": len(chromatic_indices),
                "clear_extent_above_center": max(0, (candidate_center_twice - 2 * bbox[1]) // 2),
                "clear_extent_below_center": max(0, (2 * bbox[3] - candidate_center_twice) // 2),
                "closed_pixel_count": len(indices),
                "original_ink_pixel_count": len(original_indices),
                "target_overlap_ink_pixel_count": target_overlap,
                "vertical_extension_outside_target": max(0, target_bbox[1] - bbox[1])
                + max(0, bbox[3] - target_bbox[3]),
            }
        )
    component_axis.sort(key=lambda item: (item["bbox"], item["closed_pixel_count"]))
    if len(component_axis) > _MAX_ROLE_OCCURRENCES:
        return None
    minimum_component_height = max(6, (3 * target_height + 1) // 2)
    minimum_original_ink_pixels = max(64, 2 * target_height)
    minimum_side_extent_pixels = max(4, (target_height + 7) // 8)
    minimum_side_ink_pixels = max(8, target_height // 2)
    minimum_target_overlap_ink_pixels = max(16, target_height // 4)
    minimum_vertical_extension_pixels = max(4, (target_height + 1) // 2)
    if numeric_stamp_mode:
        qualifying = [
            ordinal
            for ordinal, component in enumerate(component_axis)
            if _extreme_margin_v2_numeric_stamp_component_qualifies(
                component,
                margin_boundary=margin_boundary,
                target_bbox=target_bbox,
                body_text_scale=scale,
                candidate_ink_pixel_count=candidate_ink_pixel_count,
            )
        ]
    else:
        qualifying = [
            ordinal
            for ordinal, component in enumerate(component_axis)
            if _extreme_margin_v2_component_qualifies(
                component,
                margin_boundary=margin_boundary,
                target_bbox=target_bbox,
                minimum_component_height=minimum_component_height,
                minimum_original_ink_pixels=minimum_original_ink_pixels,
                minimum_side_extent_pixels=minimum_side_extent_pixels,
                minimum_side_ink_pixels=minimum_side_ink_pixels,
                minimum_target_overlap_ink_pixels=minimum_target_overlap_ink_pixels,
                minimum_vertical_extension_pixels=minimum_vertical_extension_pixels,
            )
        ]
    if len(qualifying) != 1:
        return None
    return {
        "body_text_scale": float(scale),
        "candidate_center_twice": candidate_center_twice,
        "chroma_spread_threshold": chroma_spread_threshold,
        "closed_mask_sha256": hashlib.sha256(closed_bytes).hexdigest(),
        "component_axis": component_axis,
        "component_axis_sha256": canonical_json_sha256_v1(component_axis),
        "expanded_pixel_count": len(pixels),
        "expanded_raw_pixel_bbox": expanded_bbox,
        "expanded_rgb_sha256": hashlib.sha256(expanded_rgb).hexdigest(),
        "ink_threshold": ink_threshold,
        "minimum_component_height": minimum_component_height,
        "minimum_original_ink_pixels": minimum_original_ink_pixels,
        "minimum_side_extent_pixels": minimum_side_extent_pixels,
        "minimum_side_ink_pixels": minimum_side_ink_pixels,
        "minimum_target_overlap_ink_pixels": minimum_target_overlap_ink_pixels,
        "minimum_vertical_extension_pixels": minimum_vertical_extension_pixels,
        "morphology_kernel_size": kernel_size,
        "qualifying_component_count": 1,
        "qualifying_component_ordinal": qualifying[0],
        "render_binding": {
            "document_ordinal": render_record["document_ordinal"],
            "physical_page": render_record["physical_page"],
            "raw_pixel_bbox": expanded_bbox,
            "render_id": render_id,
            "render_ref": canonical_clone_v1(render_record["render_ref"]),
        },
    }


def _build_authenticated_extreme_margin_furniture_evidence_v2(
    *,
    topology_candidates_id: str | None,
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    ordered_numeric_lines: Sequence[Mapping[str, Any]],
    cluster: Mapping[str, Any],
    source_record: Mapping[str, Any],
    centers: Sequence[float],
    lane_tolerance: float,
    scale: float,
    matches: Sequence[Mapping[str, Any]],
    selected_snapshot: Mapping[str, Any] | None,
    render_by_page: Mapping[int, Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, bool]:
    if (
        type(topology_candidates_id) is not str
        or not topology_candidates_id.startswith("aftcv2:result:")
        or len(ordered_numeric_lines) != 1
        or cluster.get("status") != _OFF_LANE_NUMERIC_CLUSTER_STATUS
        or source_record.get("parsed_token", {}).get("classification") != "SIGNED_NUMBER"
        or type(page.get("page_width")) is not int
        or page["page_width"] <= 0
        or not centers
    ):
        return None, False
    candidate = ordered_numeric_lines[0]
    candidate_surface_mode = _extreme_margin_v2_candidate_surface_mode(candidate)
    if candidate_surface_mode is None:
        return None, False
    numeric_stamp_mode = candidate_surface_mode == "NUMERIC_SINGLE_DIGIT_ROTATED_STAMP"
    center_quads = [center * 4 for center in centers]
    if any(not float(center).is_integer() for center in center_quads):
        return None, False
    margin_boundary = math.ceil(centers[-1] + lane_tolerance)
    bbox = candidate["bbox"]
    page_width = page["page_width"]
    if (
        bbox[0] < margin_boundary
        or bbox[2] > page_width
        or (numeric_stamp_mode and bbox[0] < (page_width * 19) // 20)
    ):
        return None, False
    full_page_label_band, full_page_label_evidence = _build_inspected_label_band(
        ordered_numeric_lines=ordered_numeric_lines,
        page=page,
        pages=pages,
        local_lines=page["lines"],
    )
    if any(label["bbox"][2] >= margin_boundary for label in full_page_label_evidence):
        return None, False
    semantic_label_line_ordinals = sorted(
        {
            page["lines"][index]["line_ordinal"]
            for match in matches
            if match["page_sequence"] == page["page_sequence"]
            for index in range(match["source_line_index"], match["end_source_line_index"] + 1)
        }
    )
    if candidate["line_ordinal"] in semantic_label_line_ordinals:
        return None, False
    margin_axis = _extreme_margin_v2_band_axis(page, margin_boundary=margin_boundary)
    candidate_records = [
        line for line in margin_axis if line["sample_id"] == candidate["sample_id"]
    ]
    peer_ordinals = _extreme_margin_v2_geometric_peer_ordinals(margin_axis, candidate)
    minimum_peer_count = 3 if numeric_stamp_mode else 2
    if len(candidate_records) != 1 or len(peer_ordinals) < minimum_peer_count:
        return None, False
    page_sequence = page["page_sequence"]
    if selected_snapshot is None or page_sequence not in render_by_page:
        return None, selected_snapshot is not None
    render = render_by_page[page_sequence]
    try:
        render_record, payload = render_v1._validated_render_snapshot(render)
        image = render_v1._png_image(payload).convert("RGB")
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise _error("authenticated extreme-margin V2 render replay failed") from exc
    if image.width != page_width:
        return None, False
    candidate_crop = _authenticated_extreme_margin_crop_proof(
        image=image,
        render_record=render_record,
        render_id=render["render_id"],
        line=candidate,
    )
    if numeric_stamp_mode and (
        candidate_crop["ink_pixel_count"] <= 0
        or candidate_crop["chromatic_ink_pixel_count"] * 4 < candidate_crop["ink_pixel_count"] * 3
    ):
        return None, False
    component_proof = _authenticated_extreme_margin_v2_component_proof(
        image=image,
        render_record=render_record,
        render_id=render["render_id"],
        candidate=candidate,
        margin_boundary=margin_boundary,
        scale=scale,
        numeric_stamp_mode=numeric_stamp_mode,
        candidate_ink_pixel_count=candidate_crop["ink_pixel_count"],
    )
    if component_proof is None:
        return None, False
    page_line_by_ordinal = {line["line_ordinal"]: line for line in page["lines"]}
    peer_crops = []
    for ordinal in peer_ordinals:
        proof = _authenticated_extreme_margin_crop_proof(
            image=image,
            render_record=render_record,
            render_id=render["render_id"],
            line=page_line_by_ordinal[ordinal],
        )
        if (
            proof["ink_pixel_count"] > 0
            and proof["chromatic_ink_pixel_count"] * 2 >= proof["ink_pixel_count"]
        ):
            peer_crops.append(proof)
    qualifying_peer_ordinals = sorted(
        proof["source_line_record"]["line_ordinal"] for proof in peer_crops
    )
    if len(qualifying_peer_ordinals) < minimum_peer_count:
        return None, False
    document_pages_sha256 = canonical_json_sha256_v1(pages)
    maximum_label_right = (
        max(label["bbox"][2] for label in full_page_label_evidence)
        if full_page_label_evidence
        else None
    )
    material = {
        "candidate_crop_proof": candidate_crop,
        "document_pages_sha256": document_pages_sha256,
        "expanded_component_proof": component_proof,
        "full_page_inspected_label_band": full_page_label_band,
        "geometry": {
            "candidate_bbox": canonical_clone_v1(bbox),
            "candidate_center_quads": 2 * (bbox[0] + bbox[2]),
            "lane_centers_quads": [int(center) for center in center_quads],
            "lane_tolerance": float(lane_tolerance),
            "margin_boundary": margin_boundary,
            "nearest_lane_ordinal": source_record["column_ordinal"],
            "page_width": page_width,
            "right_edge_gap": page_width - bbox[2],
        },
        "label_collision_proof": {
            "candidate_line_ordinal": candidate["line_ordinal"],
            "margin_boundary": margin_boundary,
            "maximum_label_right": maximum_label_right,
            "same_row_label_evidence": full_page_label_evidence,
            "same_row_label_evidence_sha256": canonical_json_sha256_v1(full_page_label_evidence),
            "semantic_label_line_ordinals": semantic_label_line_ordinals,
            "status": (
                "EXACT_MARGIN_SEPARATED_SAME_ROW_LABELS"
                if full_page_label_evidence
                else "NO_SAME_ROW_LABEL_COLLISION"
            ),
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
        "status": _EXTREME_MARGIN_FURNITURE_V2_STATUS,
        "topology_candidates_id": topology_candidates_id,
    }
    return {
        **material,
        "evidence_id": "aforav2:extreme-margin-furniture:" + canonical_json_sha256_v1(material),
    }, False


def _extreme_margin_vertical_stamp_surface_v4(line: Mapping[str, Any]) -> bool:
    vietocr = line.get("vietocr_text")
    numeric = line.get("numeric_raw_prediction")
    if type(numeric) is not str:
        recognition = line.get("numeric_recognition")
        numeric = recognition.get("raw_prediction") if type(recognition) is dict else None
    if type(vietocr) is not str or type(numeric) is not str:
        return False
    surfaces = (vietocr.strip(), numeric.strip())
    if (
        any(re.fullmatch(r"[1-9][0-9]?", surface) is None for surface in surfaces)
        or min(len(surface) for surface in surfaces) != 1
    ):
        return False
    tokens = [row_v1.parse_visible_financial_numeric_token_v1(surface) for surface in surfaces]
    return all(
        token["classification"] == "SIGNED_NUMBER"
        and token["sign"] == 1
        and token["scale"] == 0
        and not token["percentage_mark_present"]
        for token in tokens
    )


def _authenticated_extreme_margin_vertical_stamp_component_proof_v4(
    *,
    image: Any,
    render_record: Mapping[str, Any],
    render_id: str,
    candidate: Mapping[str, Any],
    scale: float,
) -> dict[str, Any] | None:
    bbox = candidate["bbox"]
    if (
        render_record["render_ref"]["pixel_width"] != image.width
        or render_record["render_ref"]["pixel_height"] != image.height
        or not (0 <= bbox[0] < bbox[2] <= image.width)
        or not (0 <= bbox[1] < bbox[3] <= image.height)
    ):
        return None
    crop = image.crop(tuple(bbox))
    rgb = crop.tobytes()
    pixels = list(zip(rgb[0::3], rgb[1::3], rgb[2::3], strict=True))
    width, height = crop.size
    ink_threshold = 220
    chroma_spread_threshold = 30
    ink_mask = bytearray(1 if min(pixel) < ink_threshold else 0 for pixel in pixels)
    visited = bytearray(len(ink_mask))
    component_axis = []
    for origin, is_ink in enumerate(ink_mask):
        if not is_ink or visited[origin]:
            continue
        visited[origin] = 1
        stack = [origin]
        indices = []
        while stack:
            index = stack.pop()
            indices.append(index)
            x = index % width
            y = index // width
            for next_y in range(max(0, y - 1), min(height, y + 2)):
                row_offset = next_y * width
                for next_x in range(max(0, x - 1), min(width, x + 2)):
                    neighbor = row_offset + next_x
                    if ink_mask[neighbor] and not visited[neighbor]:
                        visited[neighbor] = 1
                        stack.append(neighbor)
        xs = [index % width for index in indices]
        ys = [index // width for index in indices]
        component_axis.append(
            {
                "bbox": [
                    bbox[0] + min(xs),
                    bbox[1] + min(ys),
                    bbox[0] + max(xs) + 1,
                    bbox[1] + max(ys) + 1,
                ],
                "chromatic_ink_pixel_count": sum(
                    max(pixels[index]) - min(pixels[index]) >= chroma_spread_threshold
                    for index in indices
                ),
                "ink_pixel_count": len(indices),
            }
        )
    component_axis.sort(
        key=lambda component: (
            component["bbox"],
            component["ink_pixel_count"],
            component["chromatic_ink_pixel_count"],
        )
    )
    if not component_axis or len(component_axis) > _MAX_ROLE_OCCURRENCES:
        return None
    minimum_component_ink = max(8, math.ceil(scale / 4))
    qualifying = [
        ordinal
        for ordinal, component in enumerate(component_axis)
        if component["ink_pixel_count"] >= minimum_component_ink
    ]
    if len(qualifying) < 3:
        return None
    qualifying_components = [component_axis[ordinal] for ordinal in qualifying]
    vertical_span = max(component["bbox"][3] for component in qualifying_components) - min(
        component["bbox"][1] for component in qualifying_components
    )
    if (
        vertical_span * 4 < height * 3
        or not any(
            (component["bbox"][1] - bbox[1]) * 3 <= height for component in qualifying_components
        )
        or not any(
            (bbox[3] - component["bbox"][3]) * 3 <= height for component in qualifying_components
        )
    ):
        return None
    return {
        "candidate_center_twice": bbox[1] + bbox[3],
        "chroma_spread_threshold": chroma_spread_threshold,
        "component_axis": component_axis,
        "component_axis_sha256": canonical_json_sha256_v1(component_axis),
        "ink_threshold": ink_threshold,
        "minimum_component_ink_pixel_count": minimum_component_ink,
        "qualifying_component_count": len(qualifying),
        "qualifying_component_ordinals": qualifying,
        "qualifying_vertical_span": vertical_span,
        "render_binding": {
            "document_ordinal": render_record["document_ordinal"],
            "physical_page": render_record["physical_page"],
            "raw_pixel_bbox": canonical_clone_v1(bbox),
            "render_id": render_id,
            "render_ref": canonical_clone_v1(render_record["render_ref"]),
        },
        "status": _EXTREME_MARGIN_VERTICAL_STAMP_V4_COMPONENT_STATUS,
    }


def _extreme_margin_vertical_stamp_collides_with_note_axis_v4(
    page: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any],
    centers: Sequence[float],
    lane_tolerance: float,
    scale: float,
) -> bool:
    try:
        note_axis = note_axis_v1.build_accounting_printed_note_reference_axis_v1(
            page,
            detected_column_centers=centers,
            lane_tolerance=float(lane_tolerance),
            body_text_scale=float(scale),
        )
    except note_axis_v1.AccountingPrintedNoteReferenceAxisV1Error:
        return True
    header = note_axis.get("header")
    if type(header) is not dict:
        return False
    candidate_id = candidate["sample_id"]
    if candidate_id in header["sample_ids"] or any(
        row["note_sample_id"] == candidate_id for row in note_axis["rows"]
    ):
        return True
    reference = note_axis_v1.exact_note_reference_surface_v1(candidate)
    bbox = candidate["bbox"]
    header_bbox = header["bbox"]
    return (
        reference is not None
        and bbox[1] >= header_bbox[3]
        and bbox[0] >= header_bbox[0]
        and bbox[2] <= header_bbox[2]
    )


def _build_authenticated_extreme_margin_vertical_stamp_furniture_evidence_v4(
    *,
    topology_candidates_id: str | None,
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    ordered_numeric_lines: Sequence[Mapping[str, Any]],
    cluster: Mapping[str, Any],
    source_record: Mapping[str, Any],
    centers: Sequence[float],
    lane_tolerance: float,
    scale: float,
    matches: Sequence[Mapping[str, Any]],
    selected_snapshot: Mapping[str, Any] | None,
    render_by_page: Mapping[int, Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, bool]:
    """Authenticate one tall/clipped page-edge stamp OCR'd as a small integer."""

    page_width = page.get("page_width")
    if (
        type(topology_candidates_id) is not str
        or not topology_candidates_id.startswith("aftcv2:result:")
        or len(ordered_numeric_lines) != 1
        or cluster.get("status") != _OFF_LANE_NUMERIC_CLUSTER_STATUS
        or source_record.get("parsed_token", {}).get("classification") != "SIGNED_NUMBER"
        or type(page_width) is not int
        or page_width <= 0
        or not centers
        or not _extreme_margin_vertical_stamp_surface_v4(ordered_numeric_lines[0])
    ):
        return None, False
    center_quads = [center * 4 for center in centers]
    if any(not float(center).is_integer() for center in center_quads):
        return None, False
    candidate = ordered_numeric_lines[0]
    bbox = candidate["bbox"]
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    margin_boundary = math.ceil(centers[-1] + lane_tolerance)
    right_edge_gap = page_width - bbox[2]
    if (
        bbox[0] < margin_boundary
        or bbox[0] * 20 < page_width * 19
        or bbox[2] > page_width
        or right_edge_gap < 0
        or right_edge_gap > math.ceil(scale / 4)
        or height < math.ceil(3 * scale / 2)
        or height < width
    ):
        return None, False
    full_page_label_band, full_page_label_evidence = _build_inspected_label_band(
        ordered_numeric_lines=ordered_numeric_lines,
        page=page,
        pages=pages,
        local_lines=page["lines"],
    )
    if any(label["bbox"][2] >= margin_boundary for label in full_page_label_evidence):
        return None, False
    semantic_label_line_ordinals = sorted(
        {
            page["lines"][index]["line_ordinal"]
            for match in matches
            if match["page_sequence"] == page["page_sequence"]
            for index in range(match["source_line_index"], match["end_source_line_index"] + 1)
        }
    )
    if candidate["line_ordinal"] in semantic_label_line_ordinals or (
        _extreme_margin_vertical_stamp_collides_with_note_axis_v4(
            page,
            candidate=candidate,
            centers=centers,
            lane_tolerance=lane_tolerance,
            scale=scale,
        )
    ):
        return None, False
    margin_axis = _extreme_margin_v2_band_axis(page, margin_boundary=margin_boundary)
    candidate_records = [
        line for line in margin_axis if line["sample_id"] == candidate["sample_id"]
    ]
    external_peer_ordinals = _extreme_margin_v2_geometric_peer_ordinals(margin_axis, candidate)
    if len(candidate_records) != 1:
        return None, False
    page_sequence = page["page_sequence"]
    if selected_snapshot is None or page_sequence not in render_by_page:
        return None, selected_snapshot is not None
    render = render_by_page[page_sequence]
    try:
        render_record, payload = render_v1._validated_render_snapshot(render)
        image = render_v1._png_image(payload).convert("RGB")
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise _error("authenticated extreme-right vertical-stamp V4 render replay failed") from exc
    if image.width != page_width:
        return None, False
    candidate_crop = _authenticated_extreme_margin_crop_proof(
        image=image,
        render_record=render_record,
        render_id=render["render_id"],
        line=candidate,
    )
    if candidate_crop["ink_pixel_count"] <= 0:
        return None, False
    component_proof = _authenticated_extreme_margin_vertical_stamp_component_proof_v4(
        image=image,
        render_record=render_record,
        render_id=render["render_id"],
        candidate=candidate,
        scale=scale,
    )
    if component_proof is None:
        return None, False
    chromatic_mode = (
        height >= math.ceil(3 * scale)
        and candidate_crop["chromatic_ink_pixel_count"] * 2 >= candidate_crop["ink_pixel_count"]
    )
    clipped_mode = (
        right_edge_gap <= 1
        and candidate_crop["chromatic_ink_pixel_count"] * 4 <= candidate_crop["ink_pixel_count"]
        and len(external_peer_ordinals) >= 3
    )
    if chromatic_mode == clipped_mode:
        return None, False
    page_line_by_ordinal = {line["line_ordinal"]: line for line in page["lines"]}
    peer_crops = []
    if clipped_mode:
        for ordinal in external_peer_ordinals:
            proof = _authenticated_extreme_margin_crop_proof(
                image=image,
                render_record=render_record,
                render_id=render["render_id"],
                line=page_line_by_ordinal[ordinal],
            )
            if proof["ink_pixel_count"] > 0:
                peer_crops.append(proof)
        if len(peer_crops) < 3:
            return None, False
    qualifying_peer_ordinals = [proof["source_line_record"]["line_ordinal"] for proof in peer_crops]
    document_pages_sha256 = canonical_json_sha256_v1(pages)
    maximum_label_right = (
        max(label["bbox"][2] for label in full_page_label_evidence)
        if full_page_label_evidence
        else None
    )
    stamp_mode = (
        _EXTREME_MARGIN_VERTICAL_STAMP_V4_CHROMATIC_MODE
        if chromatic_mode
        else _EXTREME_MARGIN_VERTICAL_STAMP_V4_CLIPPED_MODE
    )
    material = {
        "candidate_crop_proof": candidate_crop,
        "component_peer_proof": component_proof,
        "document_pages_sha256": document_pages_sha256,
        "full_page_inspected_label_band": full_page_label_band,
        "geometry": {
            "body_text_scale": float(scale),
            "candidate_bbox": canonical_clone_v1(bbox),
            "candidate_center_quads": 2 * (bbox[0] + bbox[2]),
            "candidate_height": height,
            "candidate_width": width,
            "lane_centers_quads": [int(center) for center in center_quads],
            "lane_tolerance": float(lane_tolerance),
            "margin_boundary": margin_boundary,
            "page_edge_denominator": 20,
            "page_edge_numerator": 19,
            "page_width": page_width,
            "right_edge_gap": right_edge_gap,
            "stamp_mode": stamp_mode,
        },
        "label_collision_proof": {
            "candidate_line_ordinal": candidate["line_ordinal"],
            "margin_boundary": margin_boundary,
            "maximum_label_right": maximum_label_right,
            "same_row_label_evidence": full_page_label_evidence,
            "same_row_label_evidence_sha256": canonical_json_sha256_v1(full_page_label_evidence),
            "semantic_label_line_ordinals": semantic_label_line_ordinals,
            "status": (
                "EXACT_MARGIN_SEPARATED_SAME_ROW_LABELS"
                if full_page_label_evidence
                else "NO_SAME_ROW_LABEL_COLLISION"
            ),
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
        "peer_crop_proofs": peer_crops,
        "sample_id": source_record["sample_id"],
        "snapshot_id": selected_snapshot["snapshot_id"],
        "source_record": canonical_clone_v1(source_record),
        "status": _EXTREME_MARGIN_VERTICAL_STAMP_V4_STATUS,
        "topology_candidates_id": topology_candidates_id,
    }
    return {
        **material,
        "evidence_id": "aforav2:extreme-right-vertical-stamp-v4:"
        + canonical_json_sha256_v1(material),
    }, False


def _extreme_margin_nonnumeric_decoration_surface(line: Mapping[str, Any]) -> bool:
    numeric_surface = line.get("numeric_raw_prediction")
    if type(numeric_surface) is not str:
        recognition = line.get("numeric_recognition")
        numeric_surface = recognition.get("raw_prediction") if type(recognition) is dict else None
    if type(line.get("vietocr_text")) is not str or type(numeric_surface) is not str:
        return False
    surfaces = (line["vietocr_text"].strip(), numeric_surface.strip())
    compact = ["".join(normalize_vietnamese_anchor_v1(surface).split()) for surface in surfaces]
    return (
        any(compact)
        and all(len(surface) <= 4 for surface in compact)
        and all(not any(character.isdigit() for character in surface) for surface in surfaces)
        and all(
            row_v1.parse_visible_financial_numeric_token_v1(surface)["classification"]
            not in _EXTREME_MARGIN_ADMITTED_NUMERIC_CLASSIFICATIONS
            for surface in surfaces
        )
    )


def _build_authenticated_extreme_margin_nonnumeric_decoration_v3(
    *,
    topology_candidates_id: str | None,
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    local_lines: Sequence[Mapping[str, Any]],
    candidate: Mapping[str, Any],
    centers: Sequence[float],
    lane_tolerance: float,
    scale: float,
    matches: Sequence[Mapping[str, Any]],
    structural_gap_anchor_occurrence_ids: Sequence[str],
    numeric_line_ordinals: Sequence[int],
    selected_snapshot: Mapping[str, Any] | None,
    render_by_page: Mapping[int, Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, bool]:
    """Seal one clipped page-edge glyph as nonnumeric table decoration.

    This evidence owns no numeric sample.  It only authorizes an exact source
    line ordinal to sit between an already declared additive frontier and its
    physical subtotal.  The closure must still cite the line and this evidence
    explicitly; an arbitrary label or numeric row never reaches this builder.
    """

    page_width = page.get("page_width")
    if (
        type(topology_candidates_id) is not str
        or not topology_candidates_id.startswith("aftcv2:result:")
        or type(page_width) is not int
        or page_width <= 0
        or not centers
        or not structural_gap_anchor_occurrence_ids
        or not _extreme_margin_nonnumeric_decoration_surface(candidate)
    ):
        return None, False
    center_quads = [center * 4 for center in centers]
    if any(not float(center).is_integer() for center in center_quads):
        return None, False
    bbox = candidate["bbox"]
    candidate_ordinal = candidate["line_ordinal"]
    body_ordinals = sorted(line["line_ordinal"] for line in local_lines)
    numeric_ordinals = sorted(set(numeric_line_ordinals))
    preceding = [ordinal for ordinal in numeric_ordinals if ordinal < candidate_ordinal]
    following = [ordinal for ordinal in numeric_ordinals if ordinal > candidate_ordinal]
    preceding_ordinal = preceding[-1] if preceding else None
    following_ordinal = following[0] if following else None
    margin_boundary = math.ceil(centers[-1] + lane_tolerance)
    body_start = body_ordinals[0] if body_ordinals else None
    body_stop = body_ordinals[-1] + 1 if body_ordinals else None
    if (
        type(preceding_ordinal) is not int
        or type(body_start) is not int
        or type(body_stop) is not int
        or candidate_ordinal not in set(body_ordinals)
        or candidate_ordinal - preceding_ordinal > 4
        or (following_ordinal is None and body_stop - candidate_ordinal > 2)
        or (following_ordinal is not None and following_ordinal - candidate_ordinal > 4)
        or bbox[0] < margin_boundary
        or bbox[0] * 50 < page_width * 49
        or bbox[2] > page_width
        or page_width - bbox[2] > math.ceil(scale / 2)
        or bbox[2] - bbox[0] > math.ceil(scale * 1.25)
    ):
        return None, False
    semantic_label_line_ordinals = sorted(
        {
            page["lines"][index]["line_ordinal"]
            for match in matches
            if match["page_sequence"] == page["page_sequence"]
            for index in range(match["source_line_index"], match["end_source_line_index"] + 1)
        }
    )
    if candidate_ordinal in semantic_label_line_ordinals:
        return None, False
    page_sequence = page["page_sequence"]
    if selected_snapshot is None or page_sequence not in render_by_page:
        return None, selected_snapshot is not None
    render = render_by_page[page_sequence]
    try:
        render_record, payload = render_v1._validated_render_snapshot(render)
        image = render_v1._png_image(payload).convert("RGB")
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise _error("authenticated nonnumeric margin-decoration render replay failed") from exc
    if image.width != page_width:
        return None, False
    candidate_crop = _authenticated_extreme_margin_crop_proof(
        image=image,
        render_record=render_record,
        render_id=render["render_id"],
        line=candidate,
    )
    if candidate_crop["ink_pixel_count"] <= 0:
        return None, False
    document_pages_sha256 = canonical_json_sha256_v1(pages)
    margin_axis = _extreme_margin_v2_band_axis(page, margin_boundary=margin_boundary)
    material = {
        "candidate_crop_proof": candidate_crop,
        "document_pages_sha256": document_pages_sha256,
        "geometry": {
            "body_source_line_start": body_start,
            "body_source_line_stop_exclusive": body_stop,
            "body_text_scale": float(scale),
            "candidate_bbox": canonical_clone_v1(bbox),
            "candidate_center_quads": 2 * (bbox[0] + bbox[2]),
            "following_numeric_line_ordinal": following_ordinal,
            "lane_centers_quads": [int(center) for center in center_quads],
            "lane_tolerance": float(lane_tolerance),
            "margin_boundary": margin_boundary,
            "page_width": page_width,
            "preceding_numeric_line_ordinal": preceding_ordinal,
            "right_edge_gap": page_width - bbox[2],
        },
        "margin_band": {
            "document_pages_sha256": document_pages_sha256,
            "input_page_line_count": len(page["lines"]),
            "page_sequence": page_sequence,
            "source_line_axis": margin_axis,
            "source_line_axis_sha256": canonical_json_sha256_v1(margin_axis),
        },
        "page_sequence": page_sequence,
        "sample_id": candidate["sample_id"],
        "semantic_label_line_ordinals": semantic_label_line_ordinals,
        "snapshot_id": selected_snapshot["snapshot_id"],
        "source_record": _extreme_margin_line_record(candidate),
        "status": _EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_STATUS,
        "structural_gap_anchor_occurrence_ids": list(structural_gap_anchor_occurrence_ids),
        "topology_candidates_id": topology_candidates_id,
    }
    return {
        **material,
        "evidence_id": "aforav2:extreme-margin-furniture:" + canonical_json_sha256_v1(material),
    }, False


def _printed_note_reference_same_row_v3(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_bbox = left["bbox"]
    right_bbox = right["bbox"]
    return abs(left_bbox[1] + left_bbox[3] - right_bbox[1] - right_bbox[3]) <= max(
        left_bbox[3] - left_bbox[1],
        right_bbox[3] - right_bbox[1],
    )


def _printed_note_reference_exact_integer_v3(line: Mapping[str, Any]) -> int | None:
    vietocr = line["vietocr_text"].strip()
    numeric = line["numeric_recognition"]["raw_prediction"].strip()
    if vietocr != numeric or re.fullmatch(r"[1-9][0-9]{0,2}", vietocr) is None:
        return None
    return int(vietocr)


def _printed_note_reference_header_candidates_v3(
    page: Mapping[str, Any],
) -> list[dict[str, Any]]:
    lines = [
        line
        for line in page["lines"]
        if line["vietocr_text"].strip() and line["numeric_recognition"]["raw_prediction"].strip()
    ]

    def normalized_channels(line: Mapping[str, Any]) -> tuple[str, str]:
        return (
            normalize_vietnamese_anchor_v1(line["vietocr_text"]),
            normalize_vietnamese_anchor_v1(line["numeric_recognition"]["raw_prediction"]),
        )

    candidates = []
    for line in lines:
        if normalized_channels(line) == ("thuyet minh", "thuyet minh"):
            candidates.append({"bbox": canonical_clone_v1(line["bbox"]), "lines": [line]})
    upper_lines = [line for line in lines if normalized_channels(line) == ("thuyet", "thuyet")]
    lower_lines = [line for line in lines if normalized_channels(line) == ("minh", "minh")]
    for upper in upper_lines:
        for lower in lower_lines:
            upper_bbox = upper["bbox"]
            lower_bbox = lower["bbox"]
            overlap = min(upper_bbox[2], lower_bbox[2]) - max(upper_bbox[0], lower_bbox[0])
            vertical_gap = max(0, lower_bbox[1] - upper_bbox[3])
            if (
                lower_bbox[1] <= upper_bbox[1]
                or 2 * overlap < min(upper_bbox[2] - upper_bbox[0], lower_bbox[2] - lower_bbox[0])
                or vertical_gap > max(upper_bbox[3] - upper_bbox[1], lower_bbox[3] - lower_bbox[1])
            ):
                continue
            candidates.append(
                {
                    "bbox": [
                        min(upper_bbox[0], lower_bbox[0]),
                        min(upper_bbox[1], lower_bbox[1]),
                        max(upper_bbox[2], lower_bbox[2]),
                        max(upper_bbox[3], lower_bbox[3]),
                    ],
                    "lines": [upper, lower],
                }
            )
    deduplicated = {
        tuple(line["sample_id"] for line in candidate["lines"]): candidate
        for candidate in candidates
    }
    return [
        deduplicated[key]
        for key in sorted(
            deduplicated,
            key=lambda sample_ids: (
                deduplicated[sample_ids]["bbox"],
                sample_ids,
            ),
        )
    ]


def _printed_note_reference_row_candidates_v3(
    *,
    page: Mapping[str, Any],
    header_bbox: Sequence[int],
    centers: Sequence[float],
    lane_tolerance: float,
) -> list[dict[str, Any]]:
    if len(centers) < 2:
        return []
    first_financial_lane_left_boundary = math.floor(centers[0] - lane_tolerance)
    adjacent_lane_span = min(
        right - left for left, right in zip(centers, centers[1:], strict=False)
    )
    table_right = centers[-1] + adjacent_lane_span * 0.75
    admitted = _EXTREME_MARGIN_ADMITTED_NUMERIC_CLASSIFICATIONS
    rows = []
    for note_line in page["lines"]:
        note_value = _printed_note_reference_exact_integer_v3(note_line)
        note_bbox = note_line["bbox"]
        if (
            note_value is None
            or note_bbox[1] < header_bbox[3]
            or note_bbox[0] < header_bbox[0]
            or note_bbox[2] > header_bbox[2]
            or note_bbox[2] > first_financial_lane_left_boundary
            or 2 * (note_bbox[2] - note_bbox[0]) > header_bbox[2] - header_bbox[0]
        ):
            continue
        financial_axis = []
        selected_sample_ids = set()
        for column_ordinal, center in enumerate(centers):
            matches = []
            for line in page["lines"]:
                bbox = line["bbox"]
                parsed = row_v1.parse_visible_financial_numeric_token_v1(
                    line["numeric_recognition"]["raw_prediction"]
                )
                if (
                    line["sample_id"] == note_line["sample_id"]
                    or parsed["classification"] not in admitted
                    or not _printed_note_reference_same_row_v3(line, note_line)
                    or bbox[0] < first_financial_lane_left_boundary
                    or bbox[0] <= note_bbox[2]
                    or abs((bbox[0] + bbox[2]) / 2 - center) > lane_tolerance
                ):
                    continue
                matches.append(line)
            if len(matches) != 1:
                financial_axis = []
                break
            financial_axis.append(
                {
                    "column_ordinal": column_ordinal,
                    "source_line_record": _extreme_margin_line_record(matches[0]),
                }
            )
            selected_sample_ids.add(matches[0]["sample_id"])
        if not financial_axis:
            continue
        unassigned_financial = [
            line
            for line in page["lines"]
            if line["sample_id"] not in selected_sample_ids
            and line["sample_id"] != note_line["sample_id"]
            and first_financial_lane_left_boundary
            <= (line["bbox"][0] + line["bbox"][2]) / 2
            <= table_right
            and _printed_note_reference_same_row_v3(line, note_line)
            and row_v1.parse_visible_financial_numeric_token_v1(
                line["numeric_recognition"]["raw_prediction"]
            )["classification"]
            in admitted
        ]
        if unassigned_financial:
            continue
        label_axis = sorted(
            (
                _extreme_margin_line_record(line)
                for line in page["lines"]
                if line["bbox"][2] <= note_bbox[0]
                and _printed_note_reference_same_row_v3(line, note_line)
                and not row_v1._is_numeric(line)
                and _extreme_margin_peer_surfaces_are_nonnumeric(_extreme_margin_line_record(line))
                and (
                    line["vietocr_text"].strip()
                    or line["numeric_recognition"]["raw_prediction"].strip()
                )
            ),
            key=lambda line: (line["line_ordinal"], line["bbox"]),
        )
        if not label_axis:
            continue
        rows.append(
            {
                "financial_line_axis": financial_axis,
                "label_line_axis": label_axis,
                "note_value": note_value,
                "source_line_record": _extreme_margin_line_record(note_line),
            }
        )
    rows.sort(key=lambda row: (row["source_line_record"]["line_ordinal"], row["note_value"]))
    return rows


def _printed_note_reference_semantic_row_binding_v3(
    *,
    page: Mapping[str, Any],
    axis: Mapping[str, Any],
    cluster: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_row: Mapping[str, Any],
) -> dict[str, Any] | None:
    exact_match_kinds = {
        "EXACT_ACCENTLESS_ALIAS",
        "EXACT_ACCENTLESS_ALIAS_AFTER_ENUMERATION_PREFIX",
    }
    candidates = []
    for row in axis["rows"]:
        match = row["label_match"]
        if (
            match.get("page_sequence") != page["page_sequence"]
            or match.get("match_kind") not in exact_match_kinds
            or row.get("status") != "VISIBLE_VALUE_LANES_BOUND"
            or row.get("missing_column_ordinals") != []
            or len(row.get("values", [])) != len(candidate_row["financial_line_axis"])
        ):
            continue
        start = match.get("source_line_index")
        stop = match.get("end_source_line_index")
        if (
            type(start) is not int
            or type(stop) is not int
            or not 0 <= start <= stop < len(page["lines"])
        ):
            continue
        label_lines = page["lines"][start : stop + 1]
        label_axis = [_extreme_margin_line_record(line) for line in label_lines]
        normalized_surface = normalize_vietnamese_anchor_v1(
            " ".join(line["vietocr_text"] for line in label_lines)
        )
        same_row_labels = [
            _inspected_label_band_line(line)
            for line in label_lines
            if _printed_note_reference_same_row_v3(line, candidate)
        ]
        expected_financial = [
            item["source_line_record"] for item in candidate_row["financial_line_axis"]
        ]
        row_financial = []
        for value in sorted(row["values"], key=lambda value: value["column_ordinal"]):
            source_lines = [
                line
                for line in page["lines"]
                if line["sample_id"] == value["sample_id"]
                and line["bbox"] == value["bbox"]
                and line["line_ordinal"] == value["line_ordinal"]
                and line["numeric_recognition"]["raw_prediction"] == value["raw_prediction"]
                and line["numeric_recognition"]["reader_score"] == value["reader_score"]
                and line["crop_ref"] == value["crop_ref"]
            ]
            if len(source_lines) != 1:
                row_financial = []
                break
            row_financial.append(_extreme_margin_line_record(source_lines[0]))
        if (
            normalized_surface != match.get("normalized_surface")
            or any(line["bbox"][2] >= candidate["bbox"][0] for line in label_lines)
            or same_row_labels != cluster["same_row_label_evidence"]
            or row_financial != expected_financial
        ):
            continue
        candidates.append(
            {
                "candidate_financial_line_axis_sha256": canonical_json_sha256_v1(
                    expected_financial
                ),
                "candidate_same_row_label_axis_sha256": canonical_json_sha256_v1(same_row_labels),
                "label_source_line_axis": label_axis,
                "label_source_line_axis_sha256": canonical_json_sha256_v1(label_axis),
                "occurrence_id": match["occurrence_id"],
                "role": row["role"],
                "row_axis_id": axis["row_axis_id"],
                "source_record": canonical_clone_v1(row),
                "status": _PRINTED_NOTE_REFERENCE_SEMANTIC_ROW_STATUS,
            }
        )
    return candidates[0] if len(candidates) == 1 else None


def _printed_note_reference_crop_is_neutral_ink_v3(proof: Mapping[str, Any]) -> bool:
    return (
        proof["ink_pixel_count"] > 0
        and proof["ink_pixel_count"] * 100 >= proof["pixel_count"]
        and proof["chromatic_ink_pixel_count"] * 20 <= proof["ink_pixel_count"]
    )


def _build_authenticated_printed_note_reference_furniture_evidence_v3(
    *,
    topology_candidates_id: str | None,
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    ordered_numeric_lines: Sequence[Mapping[str, Any]],
    cluster: Mapping[str, Any],
    source_record: Mapping[str, Any],
    centers: Sequence[float],
    lane_tolerance: float,
    scale: float,
    axis: Mapping[str, Any],
    selected_snapshot: Mapping[str, Any] | None,
    render_by_page: Mapping[int, Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, bool]:
    if (
        type(topology_candidates_id) is not str
        or not topology_candidates_id.startswith("aftcv2:result:")
        or len(ordered_numeric_lines) != 1
        or len(centers) < 2
        or cluster.get("status") != _OFF_LANE_NUMERIC_CLUSTER_STATUS
        or cluster.get("label_lane_status") != _LABELED_LABEL_LANE_STATUS
        or not cluster.get("same_row_label_evidence")
        or source_record.get("parsed_token", {}).get("classification") != "SIGNED_NUMBER"
        or type(page.get("page_width")) is not int
        or page["page_width"] <= 0
    ):
        return None, False
    candidate = ordered_numeric_lines[0]
    candidate_value = _printed_note_reference_exact_integer_v3(candidate)
    center_quads = [center * 4 for center in centers]
    if candidate_value is None or any(not float(center).is_integer() for center in center_quads):
        return None, False
    headers = _printed_note_reference_header_candidates_v3(page)
    if len(headers) != 1:
        return None, False
    header = headers[0]
    header_bbox = header["bbox"]
    first_financial_lane_left_boundary = math.floor(centers[0] - lane_tolerance)
    bbox = candidate["bbox"]
    if (
        bbox[0] < header_bbox[0]
        or bbox[2] > header_bbox[2]
        or bbox[1] < header_bbox[3]
        or header_bbox[2] > first_financial_lane_left_boundary
        or bbox[2] > first_financial_lane_left_boundary
    ):
        return None, False
    note_rows = _printed_note_reference_row_candidates_v3(
        page=page,
        header_bbox=header_bbox,
        centers=centers,
        lane_tolerance=lane_tolerance,
    )
    candidate_rows = [
        row for row in note_rows if row["source_line_record"]["sample_id"] == candidate["sample_id"]
    ]
    note_values = [row["note_value"] for row in note_rows]
    note_centers_twice = [
        row["source_line_record"]["bbox"][0] + row["source_line_record"]["bbox"][2]
        for row in note_rows
    ]
    horizontal_tolerance = max(scale, (header_bbox[2] - header_bbox[0]) / 4)
    if (
        len(candidate_rows) != 1
        or len(note_rows) < 3
        or len(note_values) != len(set(note_values))
        or candidate_value - 1 not in note_values
        or candidate_value + 1 not in note_values
        or any(
            abs(center_twice - bbox[0] - bbox[2]) > 2 * horizontal_tolerance
            for center_twice in note_centers_twice
        )
        or not any(
            row["source_line_record"]["line_ordinal"] < candidate["line_ordinal"]
            for row in note_rows
        )
        or not any(
            row["source_line_record"]["line_ordinal"] > candidate["line_ordinal"]
            for row in note_rows
        )
    ):
        return None, False
    semantic_row_binding = _printed_note_reference_semantic_row_binding_v3(
        page=page,
        axis=axis,
        cluster=cluster,
        candidate=candidate,
        candidate_row=candidate_rows[0],
    )
    if semantic_row_binding is None:
        return None, False
    page_sequence = page["page_sequence"]
    if selected_snapshot is None or page_sequence not in render_by_page:
        return None, selected_snapshot is not None
    render = render_by_page[page_sequence]
    try:
        render_record, payload = render_v1._validated_render_snapshot(render)
        image = render_v1._png_image(payload).convert("RGB")
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise _error("authenticated printed note-reference render replay failed") from exc
    if image.width != page["page_width"]:
        return None, False
    header_crop_proofs = [
        _authenticated_extreme_margin_crop_proof(
            image=image,
            render_record=render_record,
            render_id=render["render_id"],
            line=line,
        )
        for line in header["lines"]
    ]
    if not all(
        _printed_note_reference_crop_is_neutral_ink_v3(proof) for proof in header_crop_proofs
    ):
        return None, False
    note_axis = []
    for row in note_rows:
        line = next(
            line
            for line in page["lines"]
            if line["sample_id"] == row["source_line_record"]["sample_id"]
        )
        crop_proof = _authenticated_extreme_margin_crop_proof(
            image=image,
            render_record=render_record,
            render_id=render["render_id"],
            line=line,
        )
        if not _printed_note_reference_crop_is_neutral_ink_v3(crop_proof):
            return None, False
        note_axis.append({**row, "note_crop_proof": crop_proof})
    candidate_axis = [
        row for row in note_axis if row["source_line_record"]["sample_id"] == candidate["sample_id"]
    ]
    if len(candidate_axis) != 1:
        return None, False
    candidate_crop_proof = candidate_axis[0]["note_crop_proof"]
    document_pages_sha256 = canonical_json_sha256_v1(pages)
    header_source_axis = [_extreme_margin_line_record(line) for line in header["lines"]]
    material = {
        "candidate_crop_proof": candidate_crop_proof,
        "document_pages_sha256": document_pages_sha256,
        "geometry": {
            "body_text_scale": float(scale),
            "candidate_bbox": canonical_clone_v1(bbox),
            "candidate_center_twice": bbox[0] + bbox[2],
            "candidate_note_value": candidate_value,
            "first_financial_lane_left_boundary": first_financial_lane_left_boundary,
            "header_bbox": canonical_clone_v1(header_bbox),
            "lane_centers_quads": [int(center) for center in center_quads],
            "lane_tolerance": float(lane_tolerance),
            "page_width": page["page_width"],
            "qualifying_note_reference_row_count": len(note_axis),
        },
        "header_proof": {
            "crop_proofs": header_crop_proofs,
            "header_bbox": canonical_clone_v1(header_bbox),
            "normalized_surface": "thuyet minh",
            "source_line_axis": header_source_axis,
            "source_line_axis_sha256": canonical_json_sha256_v1(header_source_axis),
            "status": _PRINTED_NOTE_REFERENCE_HEADER_STATUS,
        },
        "note_reference_axis": note_axis,
        "original_cluster": canonical_clone_v1(cluster),
        "page_sequence": page_sequence,
        "sample_id": source_record["sample_id"],
        "semantic_row_binding": semantic_row_binding,
        "snapshot_id": selected_snapshot["snapshot_id"],
        "source_record": canonical_clone_v1(source_record),
        "status": _PRINTED_NOTE_REFERENCE_FURNITURE_V3_STATUS,
        "topology_candidates_id": topology_candidates_id,
    }
    return {
        **material,
        "evidence_id": "aforav2:extreme-margin-furniture:" + canonical_json_sha256_v1(material),
    }, False


def _printed_note_reference_same_row(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    body_text_scale: float,
) -> bool:
    return note_axis_v1.same_visual_row_v1(
        left,
        right,
        body_text_scale=body_text_scale,
    )


def _printed_note_reference_exact_surface(line: Mapping[str, Any]) -> str | None:
    return note_axis_v1.exact_note_reference_surface_v1(line)


def _printed_note_reference_parts(surface: str) -> tuple[int, int | None]:
    return note_axis_v1.note_reference_parts_v1(surface)


def _printed_note_reference_has_local_peer(
    candidate: str,
    references: Sequence[str],
) -> bool:
    """Require a local printed-note series without treating it as accounting math."""

    return note_axis_v1.note_reference_has_local_peer_v1(candidate, references)


def _printed_note_reference_row_candidates(
    *,
    page: Mapping[str, Any],
    header_bbox: Sequence[int],
    centers: Sequence[float],
    lane_tolerance: float,
    body_text_scale: float,
) -> list[dict[str, Any]]:
    try:
        shared_axis = note_axis_v1.build_accounting_printed_note_reference_axis_v1(
            page,
            detected_column_centers=centers,
            lane_tolerance=lane_tolerance,
            body_text_scale=body_text_scale,
        )
    except note_axis_v1.AccountingPrintedNoteReferenceAxisV1Error:
        return []
    if (
        shared_axis["status"] != note_axis_v1.READY_STATUS
        or shared_axis["header"]["bbox"] != list(header_bbox)
        or shared_axis["financial_column_centers"] != list(centers)
    ):
        return []
    by_sample: dict[str, list[Mapping[str, Any]]] = {}
    for line in page["lines"]:
        by_sample.setdefault(line["sample_id"], []).append(line)
    rows = []
    for shared_row in shared_axis["rows"]:
        sample_axes = [
            shared_row["note_sample_id"],
            *shared_row["financial_sample_ids"],
            *shared_row["label_sample_ids"],
        ]
        if any(len(by_sample.get(sample_id, [])) != 1 for sample_id in sample_axes):
            return []
        note_line = by_sample[shared_row["note_sample_id"]][0]
        financial_axis = [
            {
                "column_ordinal": column_ordinal,
                "source_line_record": _extreme_margin_line_record(by_sample[sample_id][0]),
            }
            for column_ordinal, sample_id in enumerate(shared_row["financial_sample_ids"])
        ]
        label_axis = [
            _extreme_margin_line_record(by_sample[sample_id][0])
            for sample_id in shared_row["label_sample_ids"]
        ]
        rows.append(
            {
                "financial_line_axis": financial_axis,
                "label_line_axis": label_axis,
                "note_reference": shared_row["note_reference"],
                "source_line_record": _extreme_margin_line_record(note_line),
            }
        )
    rows.sort(
        key=lambda row: (
            row["source_line_record"]["line_ordinal"],
            _printed_note_reference_parts(row["note_reference"]),
        )
    )
    return rows


def _printed_note_reference_semantic_row_binding(
    *,
    page: Mapping[str, Any],
    axis: Mapping[str, Any],
    cluster: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_row: Mapping[str, Any],
    body_text_scale: float,
) -> dict[str, Any] | None:
    exact_match_kinds = {
        "EXACT_ACCENTLESS_ALIAS",
        "EXACT_ACCENTLESS_ALIAS_AFTER_ENUMERATION_PREFIX",
    }
    candidates = []
    for row in axis["rows"]:
        match = row["label_match"]
        if (
            match.get("page_sequence") != page["page_sequence"]
            or match.get("match_kind") not in exact_match_kinds
            or row.get("status") != "VISIBLE_VALUE_LANES_BOUND"
            or row.get("missing_column_ordinals") != []
            or len(row.get("values", [])) != len(candidate_row["financial_line_axis"])
        ):
            continue
        start = match.get("source_line_index")
        stop = match.get("end_source_line_index")
        if (
            type(start) is not int
            or type(stop) is not int
            or not 0 <= start <= stop < len(page["lines"])
        ):
            continue
        label_lines = page["lines"][start : stop + 1]
        label_axis = [_extreme_margin_line_record(line) for line in label_lines]
        normalized_surface = normalize_vietnamese_anchor_v1(
            " ".join(line["vietocr_text"] for line in label_lines)
        )
        selected_label_ids = {line["sample_id"] for line in candidate_row["label_line_axis"]}
        same_row_labels = [
            _inspected_label_band_line(line)
            for line in label_lines
            if line["sample_id"] in selected_label_ids
            and _printed_note_reference_same_row(
                line,
                candidate,
                body_text_scale=body_text_scale,
            )
        ]
        expected_financial = [
            item["source_line_record"] for item in candidate_row["financial_line_axis"]
        ]
        row_financial = []
        for value in sorted(row["values"], key=lambda value: value["column_ordinal"]):
            source_lines = [
                line
                for line in page["lines"]
                if line["sample_id"] == value["sample_id"]
                and line["bbox"] == value["bbox"]
                and line["line_ordinal"] == value["line_ordinal"]
                and line["numeric_recognition"]["raw_prediction"] == value["raw_prediction"]
                and line["numeric_recognition"]["reader_score"] == value["reader_score"]
                and line["crop_ref"] == value["crop_ref"]
            ]
            if len(source_lines) != 1:
                row_financial = []
                break
            row_financial.append(_extreme_margin_line_record(source_lines[0]))
        if (
            normalized_surface != match.get("normalized_surface")
            or any(line["bbox"][2] >= candidate["bbox"][0] for line in label_lines)
            or same_row_labels != cluster["same_row_label_evidence"]
            or row_financial != expected_financial
        ):
            continue
        candidates.append(
            {
                "binding_kind": _PRINTED_NOTE_REFERENCE_ROLE_BINDING_KIND,
                "candidate_financial_line_axis_sha256": canonical_json_sha256_v1(
                    expected_financial
                ),
                "candidate_same_row_label_axis_sha256": canonical_json_sha256_v1(same_row_labels),
                "label_source_line_axis": label_axis,
                "label_source_line_axis_sha256": canonical_json_sha256_v1(label_axis),
                "occurrence_id": match["occurrence_id"],
                "role": row["role"],
                "row_axis_id": axis["row_axis_id"],
                "source_record": canonical_clone_v1(row),
                "status": _PRINTED_NOTE_REFERENCE_SEMANTIC_ROW_STATUS,
            }
        )
    return candidates[0] if len(candidates) == 1 else None


def _printed_note_reference_parent_row_binding(
    *,
    page: Mapping[str, Any],
    axis: Mapping[str, Any],
    cluster: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_row: Mapping[str, Any],
    body_text_scale: float,
) -> dict[str, Any] | None:
    """Bind furniture to the one selected parent span, without semantic promotion."""

    parent = axis.get("topology_region", {}).get("parent_match")
    if (
        type(parent) is not dict
        or parent.get("page_sequence") != page["page_sequence"]
        or parent.get("parent_resolution") is not None
    ):
        # ``parent_resolution`` belongs to the region, never the match.  Its
        # presence here is therefore an injected/replayed shape.
        return None
    start = parent.get("source_line_index")
    stop = parent.get("end_source_line_index")
    if (
        type(start) is not int
        or type(stop) is not int
        or not 0 <= start <= stop < len(page["lines"])
    ):
        return None
    label_lines = page["lines"][start : stop + 1]
    label_axis = [_extreme_margin_line_record(line) for line in label_lines]
    selected_label_ids = {line["sample_id"] for line in candidate_row["label_line_axis"]}
    same_row_labels = [
        _inspected_label_band_line(line)
        for line in label_lines
        if line["sample_id"] in selected_label_ids
        and _printed_note_reference_same_row(
            line,
            candidate,
            body_text_scale=body_text_scale,
        )
    ]
    financial_records = [
        item["source_line_record"] for item in candidate_row["financial_line_axis"]
    ]
    if (
        not same_row_labels
        or same_row_labels != cluster["same_row_label_evidence"]
        or any(line["bbox"][2] >= candidate["bbox"][0] for line in label_lines)
        or normalize_vietnamese_anchor_v1(" ".join(line["vietocr_text"] for line in label_lines))
        != parent.get("normalized_surface")
    ):
        return None
    binding_id = "aforav2:parent-note-row:" + canonical_json_sha256_v1(parent)
    return {
        "binding_kind": _PRINTED_NOTE_REFERENCE_PARENT_BINDING_KIND,
        "candidate_financial_line_axis_sha256": canonical_json_sha256_v1(financial_records),
        "candidate_same_row_label_axis_sha256": canonical_json_sha256_v1(same_row_labels),
        "label_source_line_axis": label_axis,
        "label_source_line_axis_sha256": canonical_json_sha256_v1(label_axis),
        "occurrence_id": binding_id,
        "role": "FAMILY_PARENT",
        "row_axis_id": axis["row_axis_id"],
        "source_record": canonical_clone_v1(parent),
        "status": _PRINTED_NOTE_REFERENCE_PARENT_STATUS,
    }


def _printed_note_reference_crop_is_neutral_ink(proof: Mapping[str, Any]) -> bool:
    return (
        proof["ink_pixel_count"] > 0
        and proof["ink_pixel_count"] * 100 >= proof["pixel_count"]
        and proof["chromatic_ink_pixel_count"] * 20 <= proof["ink_pixel_count"]
    )


def _build_authenticated_printed_note_reference_furniture_evidence_v4(
    *,
    topology_candidates_id: str | None,
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    ordered_numeric_lines: Sequence[Mapping[str, Any]],
    cluster: Mapping[str, Any],
    source_record: Mapping[str, Any],
    centers: Sequence[float],
    lane_tolerance: float,
    scale: float,
    axis: Mapping[str, Any],
    selected_snapshot: Mapping[str, Any] | None,
    render_by_page: Mapping[int, Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, bool]:
    if (
        type(topology_candidates_id) is not str
        or not topology_candidates_id.startswith("aftcv2:result:")
        or len(ordered_numeric_lines) != 1
        or len(centers) < 2
        or cluster.get("status") != _OFF_LANE_NUMERIC_CLUSTER_STATUS
        or cluster.get("label_lane_status") != _LABELED_LABEL_LANE_STATUS
        or not cluster.get("same_row_label_evidence")
        or source_record.get("parsed_token", {}).get("classification") != "SIGNED_NUMBER"
        or type(page.get("page_width")) is not int
        or page["page_width"] <= 0
    ):
        return None, False
    candidate = ordered_numeric_lines[0]
    candidate_reference = _printed_note_reference_exact_surface(candidate)
    center_quads = [center * 4 for center in centers]
    if candidate_reference is None or any(
        not float(center).is_integer() for center in center_quads
    ):
        return None, False
    try:
        shared_axis = note_axis_v1.build_accounting_printed_note_reference_axis_v1(
            page,
            detected_column_centers=centers,
            lane_tolerance=float(lane_tolerance),
            body_text_scale=float(scale),
        )
    except note_axis_v1.AccountingPrintedNoteReferenceAxisV1Error:
        return None, False
    if shared_axis["status"] != note_axis_v1.READY_STATUS or shared_axis[
        "financial_column_centers"
    ] != list(centers):
        return None, False
    sample_axes: dict[str, list[Mapping[str, Any]]] = {}
    for line in page["lines"]:
        sample_axes.setdefault(line["sample_id"], []).append(line)
    by_sample = {sample_id: lines[0] for sample_id, lines in sample_axes.items() if len(lines) == 1}
    header_lines = [by_sample.get(sample_id) for sample_id in shared_axis["header"]["sample_ids"]]
    if any(line is None for line in header_lines):
        return None, False
    header = {"bbox": shared_axis["header"]["bbox"], "lines": header_lines}
    header_bbox = header["bbox"]
    first_financial_lane_left_boundary = math.floor(centers[0] - lane_tolerance)
    bbox = candidate["bbox"]
    if (
        bbox[0] < header_bbox[0]
        or bbox[2] > header_bbox[2]
        or bbox[1] < header_bbox[3]
        or header_bbox[2] > first_financial_lane_left_boundary
        or bbox[2] > first_financial_lane_left_boundary
    ):
        return None, False
    note_rows = _printed_note_reference_row_candidates(
        page=page,
        header_bbox=header_bbox,
        centers=centers,
        lane_tolerance=float(lane_tolerance),
        body_text_scale=float(scale),
    )
    candidate_rows = [
        row for row in note_rows if row["source_line_record"]["sample_id"] == candidate["sample_id"]
    ]
    note_references = [row["note_reference"] for row in note_rows]
    note_centers_twice = [
        row["source_line_record"]["bbox"][0] + row["source_line_record"]["bbox"][2]
        for row in note_rows
    ]
    horizontal_tolerance = max(scale, (header_bbox[2] - header_bbox[0]) / 4)
    if (
        len(candidate_rows) != 1
        or len(note_rows) < 3
        or len(note_references) != len(set(note_references))
        or not _printed_note_reference_has_local_peer(candidate_reference, note_references)
        or any(
            abs(center_twice - bbox[0] - bbox[2]) > 2 * horizontal_tolerance
            for center_twice in note_centers_twice
        )
        or not any(
            row["source_line_record"]["line_ordinal"] < candidate["line_ordinal"]
            for row in note_rows
        )
        or not any(
            row["source_line_record"]["line_ordinal"] > candidate["line_ordinal"]
            for row in note_rows
        )
    ):
        return None, False
    semantic_row_binding = _printed_note_reference_semantic_row_binding(
        page=page,
        axis=axis,
        cluster=cluster,
        candidate=candidate,
        candidate_row=candidate_rows[0],
        body_text_scale=float(scale),
    )
    if semantic_row_binding is None:
        semantic_row_binding = _printed_note_reference_parent_row_binding(
            page=page,
            axis=axis,
            cluster=cluster,
            candidate=candidate,
            candidate_row=candidate_rows[0],
            body_text_scale=float(scale),
        )
    if semantic_row_binding is None:
        return None, False
    page_sequence = page["page_sequence"]
    if selected_snapshot is None or page_sequence not in render_by_page:
        return None, selected_snapshot is not None
    render = render_by_page[page_sequence]
    try:
        render_record, payload = render_v1._validated_render_snapshot(render)
        image = render_v1._png_image(payload).convert("RGB")
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise _error("authenticated printed note-reference render replay failed") from exc
    if image.width != page["page_width"]:
        return None, False
    header_crop_proofs = [
        _authenticated_extreme_margin_crop_proof(
            image=image,
            render_record=render_record,
            render_id=render["render_id"],
            line=line,
        )
        for line in header["lines"]
    ]
    if not all(_printed_note_reference_crop_is_neutral_ink(proof) for proof in header_crop_proofs):
        return None, False
    note_axis = []
    for row in note_rows:
        line = next(
            line
            for line in page["lines"]
            if line["sample_id"] == row["source_line_record"]["sample_id"]
        )
        crop_proof = _authenticated_extreme_margin_crop_proof(
            image=image,
            render_record=render_record,
            render_id=render["render_id"],
            line=line,
        )
        if not _printed_note_reference_crop_is_neutral_ink(crop_proof):
            return None, False
        note_axis.append({**row, "note_crop_proof": crop_proof})
    candidate_axis = [
        row for row in note_axis if row["source_line_record"]["sample_id"] == candidate["sample_id"]
    ]
    if len(candidate_axis) != 1:
        return None, False
    candidate_crop_proof = candidate_axis[0]["note_crop_proof"]
    document_pages_sha256 = canonical_json_sha256_v1(pages)
    header_source_axis = [_extreme_margin_line_record(line) for line in header["lines"]]
    material = {
        "candidate_crop_proof": candidate_crop_proof,
        "document_pages_sha256": document_pages_sha256,
        "geometry": {
            "body_text_scale": float(scale),
            "candidate_bbox": canonical_clone_v1(bbox),
            "candidate_center_twice": bbox[0] + bbox[2],
            "candidate_note_reference": candidate_reference,
            "first_financial_lane_left_boundary": first_financial_lane_left_boundary,
            "header_bbox": canonical_clone_v1(header_bbox),
            "lane_centers_quads": [int(center) for center in center_quads],
            "lane_tolerance": float(lane_tolerance),
            "page_width": page["page_width"],
            "qualifying_note_reference_row_count": len(note_axis),
        },
        "header_proof": {
            "crop_proofs": header_crop_proofs,
            "header_bbox": canonical_clone_v1(header_bbox),
            "normalized_surface": "thuyet minh",
            "source_line_axis": header_source_axis,
            "source_line_axis_sha256": canonical_json_sha256_v1(header_source_axis),
            "status": _PRINTED_NOTE_REFERENCE_HEADER_STATUS,
        },
        "note_reference_axis": note_axis,
        "original_cluster": canonical_clone_v1(cluster),
        "page_sequence": page_sequence,
        "sample_id": source_record["sample_id"],
        "semantic_row_binding": semantic_row_binding,
        "snapshot_id": selected_snapshot["snapshot_id"],
        "source_record": canonical_clone_v1(source_record),
        "status": _PRINTED_NOTE_REFERENCE_FURNITURE_V4_STATUS,
        "topology_candidates_id": topology_candidates_id,
    }
    return {
        **material,
        "evidence_id": "aforav2:printed-note-reference-v4:" + canonical_json_sha256_v1(material),
    }, False


def _printed_note_reference_line_is_inside_region(
    *,
    expanded_region: Mapping[str, Any],
    page_sequence: int,
    line_ordinal: int,
) -> bool:
    start_page = expanded_region["page_sequence"]
    stop_page = expanded_region.get("cluster_end_page_sequence_inclusive", start_page)
    if not start_page <= page_sequence <= stop_page:
        return False
    start = expanded_region.get("cluster_start_source_line_index")
    stop = expanded_region.get("cluster_end_source_line_index_exclusive")
    return not (
        (page_sequence == start_page and type(start) is int and line_ordinal < start)
        or (page_sequence == stop_page and type(stop) is int and line_ordinal >= stop)
    )


def _project_authenticated_printed_note_reference_columns_v3(
    *,
    pages: Sequence[Mapping[str, Any]],
    expanded_region: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]],
    axis: Mapping[str, Any],
) -> tuple[dict[str, Any], frozenset[str]]:
    """Propose a financial-only grid; pixels must later authorize every removal."""

    projected = canonical_clone_v1(axis)
    page_by_sequence = {page["page_sequence"]: page for page in pages}
    body_by_page = row_v1._role_body_lines_by_page(pages, expanded_region, matches)
    candidate_sample_ids: set[str] = set()
    changed = False
    for grid in projected["column_grids"]:
        page_sequence = grid["page_sequence"]
        page = page_by_sequence[page_sequence]
        local_lines = body_by_page.get(page_sequence, [])
        centers = grid["column_centers"]
        if len(centers) < 2 or not local_lines:
            continue
        scale = row_v1.median_text_height_v1(local_lines)
        lane_tolerance = max(
            scale * 1.6,
            min(right - left for left, right in zip(centers, centers[1:], strict=False)) * 0.42,
        )
        try:
            shared_axis = note_axis_v1.build_accounting_printed_note_reference_axis_v1(
                page,
                detected_column_centers=centers,
                lane_tolerance=float(lane_tolerance),
                body_text_scale=float(scale),
            )
        except note_axis_v1.AccountingPrintedNoteReferenceAxisV1Error:
            continue
        if shared_axis["status"] != note_axis_v1.READY_STATUS:
            continue
        header_bbox = shared_axis["header"]["bbox"]
        financial_centers = shared_axis["financial_column_centers"]
        note_rows = _printed_note_reference_row_candidates(
            page=page,
            header_bbox=header_bbox,
            centers=financial_centers,
            lane_tolerance=float(lane_tolerance),
            body_text_scale=float(scale),
        )
        references = [row["note_reference"] for row in note_rows]
        local_note_rows = [
            row
            for row in note_rows
            if _printed_note_reference_line_is_inside_region(
                expanded_region=expanded_region,
                page_sequence=page_sequence,
                line_ordinal=row["source_line_record"]["line_ordinal"],
            )
            and _printed_note_reference_has_local_peer(row["note_reference"], references)
        ]
        if not local_note_rows:
            continue
        page_candidate_ids = {row["source_line_record"]["sample_id"] for row in local_note_rows}
        removed_centers = [center for center in centers if center not in financial_centers]
        rows_on_page = [
            row for row in projected["rows"] if row["label_match"]["page_sequence"] == page_sequence
        ]
        if (
            any(
                value["column_center"] in removed_centers
                and value["sample_id"] not in page_candidate_ids
                for row in rows_on_page
                for value in row["values"]
            )
            or any(
                value["column_center"] in removed_centers
                and value["sample_id"] not in page_candidate_ids
                for trailing in projected["trailing_value_rows"]
                if trailing["page_sequence"] == page_sequence
                for value in trailing["values"]
            )
            or any(
                rescue["column_center"] in removed_centers
                for rescue in projected["visible_dash_rescues"]
                if rescue["page_sequence"] == page_sequence
            )
        ):
            # A decimal/money cell occupies the would-be removed column.  The
            # header alone cannot turn that financial lane into furniture.
            continue
        if removed_centers:
            for row in rows_on_page:
                retained = [
                    value for value in row["values"] if value["sample_id"] not in page_candidate_ids
                ]
                if any(value["column_center"] not in financial_centers for value in retained):
                    return canonical_clone_v1(axis), frozenset()
                for value in retained:
                    value["column_ordinal"] = financial_centers.index(value["column_center"])
                row["values"] = sorted(retained, key=lambda value: value["column_ordinal"])
                visible = {value["column_ordinal"] for value in retained}
                row["missing_column_ordinals"] = [
                    ordinal for ordinal in range(len(financial_centers)) if ordinal not in visible
                ]
                row["status"] = (
                    "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL"
                    if not retained
                    else "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
                    if row["missing_column_ordinals"]
                    else "VISIBLE_VALUE_LANES_BOUND"
                )
            for trailing in projected["trailing_value_rows"]:
                if trailing["page_sequence"] != page_sequence:
                    continue
                retained = [
                    value
                    for value in trailing["values"]
                    if value["sample_id"] not in page_candidate_ids
                ]
                for value in retained:
                    value["column_ordinal"] = financial_centers.index(value["column_center"])
                trailing["values"] = sorted(retained, key=lambda value: value["column_ordinal"])
                visible = {value["column_ordinal"] for value in retained}
                trailing["missing_column_ordinals"] = [
                    ordinal for ordinal in range(len(financial_centers)) if ordinal not in visible
                ]
                trailing["status"] = (
                    "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
                    if retained and not trailing["missing_column_ordinals"]
                    else "PARTIAL_TRAILING_VALUE_ROW_REQUIRES_PIXEL_RESCUE"
                )
            grid["column_centers"] = canonical_clone_v1(financial_centers)
            changed = True
        candidate_sample_ids.update(page_candidate_ids)
    if not candidate_sample_ids:
        return canonical_clone_v1(axis), frozenset()
    return (
        _regenerate_v1_axis(projected) if changed else canonical_clone_v1(axis),
        frozenset(candidate_sample_ids),
    )


def _active_contextual_body_owner_top_by_page(
    pages: Sequence[Mapping[str, Any]],
    matches: Sequence[Mapping[str, Any]],
    axis: Mapping[str, Any],
) -> dict[int, int]:
    """Fence source-only numerics to one exact contextual child table.

    An outer accounting-note parent can contain a preceding sibling table
    before one explicit structural subgroup. When every visible additive row
    on a page is owned by that same exact subgroup, unowned numerics ending at
    or above the subgroup's top edge belong outside the active body. Mixed,
    singleton, non-structural, non-exact, or cross-page ownership abstains.
    """

    page_by_sequence = {page["page_sequence"]: page for page in pages}
    additive_rows_by_page: dict[int, list[Mapping[str, Any]]] = {}
    for row in axis["rows"]:
        label = row["label_match"]
        if row["role_kind"] != "ADDITIVE_CHILD":
            continue
        additive_rows_by_page.setdefault(label["page_sequence"], []).append(row)
    result: dict[int, int] = {}
    for page_sequence, rows in sorted(additive_rows_by_page.items()):
        if len(rows) < 2:
            continue
        owner_ids = {row["label_match"].get("scope_owner_occurrence_id") for row in rows}
        if len(owner_ids) != 1:
            continue
        owner_id = next(iter(owner_ids))
        if type(owner_id) is not str or not owner_id:
            continue
        owners = [match for match in matches if match.get("occurrence_id") == owner_id]
        if len(owners) != 1:
            continue
        owner = owners[0]
        if (
            owner.get("role_kind") != "STRUCTURAL_GROUP"
            or owner.get("page_sequence") != page_sequence
            or not str(owner.get("match_kind", "")).startswith("EXACT_")
        ):
            continue
        page = page_by_sequence.get(page_sequence)
        if page is None:
            continue
        owner_indices = row_v1._match_source_line_indices(owner)
        boxes = [line["bbox"] for line in page["lines"] if line["line_ordinal"] in owner_indices]
        if len(boxes) != len(owner_indices):
            raise _error("contextual body owner lost exact source geometry")
        result[page_sequence] = min(box[1] for box in boxes)
    return result


def _source_only_numeric_is_before_contextual_body(
    line: Mapping[str, Any],
    active_owner_top: int | None,
) -> bool:
    """Return true only for a source line wholly before the active body."""

    return active_owner_top is not None and line["bbox"][3] <= active_owner_top


def _build_numeric_sample_universe(
    pages: Sequence[Mapping[str, Any]],
    expanded_region: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]],
    axis: Mapping[str, Any],
    coextensive_evidence: Sequence[Mapping[str, Any]],
    *,
    topology_candidates_id: str | None,
    printed_note_v3_topology_candidates_id: str | None,
    selected_snapshot: Mapping[str, Any] | None,
    render_snapshots: Sequence[Mapping[str, Any]],
    printed_note_candidate_sample_ids: frozenset[str] = frozenset(),
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
    contextual_body_owner_top_by_page = _active_contextual_body_owner_top_by_page(
        pages,
        matches,
        axis,
    )
    grid_by_page = {grid["page_sequence"]: grid for grid in axis["column_grids"]}
    bound_occurrence_ids = {
        row["label_match"].get("occurrence_id")
        for row in axis["rows"]
        if type(row.get("label_match", {}).get("occurrence_id")) is str
    }
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
        printed_note_label_ids: dict[str, frozenset[str]] = {}
        printed_note_furniture_version = 3
        if any(line["sample_id"] in printed_note_candidate_sample_ids for line in local_lines):
            try:
                shared_note_axis = note_axis_v1.build_accounting_printed_note_reference_axis_v1(
                    page,
                    detected_column_centers=centers,
                    lane_tolerance=float(lane_tolerance),
                    body_text_scale=float(scale),
                )
            except note_axis_v1.AccountingPrintedNoteReferenceAxisV1Error:
                shared_note_axis = None
            if (
                type(shared_note_axis) is dict
                and shared_note_axis["status"] == note_axis_v1.READY_STATUS
                and shared_note_axis["financial_column_centers"] == centers
            ):
                if any("." in row["note_reference"] for row in shared_note_axis["rows"]):
                    printed_note_furniture_version = 4
                    printed_note_label_ids = {
                        row["note_sample_id"]: frozenset(row["label_sample_ids"])
                        for row in shared_note_axis["rows"]
                        if row["note_sample_id"] in printed_note_candidate_sample_ids
                    }
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
            active_owner_top = contextual_body_owner_top_by_page.get(page_sequence)
            if _source_only_numeric_is_before_contextual_body(line, active_owner_top):
                continue
            center = (line["bbox"][0] + line["bbox"][2]) / 2
            if (
                line["sample_id"] not in printed_note_candidate_sample_ids
                and not table_left <= center <= table_right
            ):
                continue
            lane = min(range(len(centers)), key=lambda index: abs(center - centers[index]))
            projected = {**canonical_clone_v1(line), "source_line_index": line["line_ordinal"]}
            candidates.append(projected)
            lanes_by_sample[line["sample_id"]] = lane
            if abs(center - centers[lane]) > lane_tolerance:
                off_lane_sample_ids.add(line["sample_id"])
        forced_note_lines = [
            line for line in candidates if line["sample_id"] in printed_note_candidate_sample_ids
        ]
        ordinary_lines = [
            line
            for line in candidates
            if line["sample_id"] not in printed_note_candidate_sample_ids
        ]
        physical_clusters = [[line] for line in forced_note_lines]
        if ordinary_lines:
            physical_clusters.extend(
                row_v1.cluster_numeric_rows_v1(
                    ordinary_lines,
                    is_numeric=row_v1._is_numeric,
                    start_index=min(line["source_line_index"] for line in ordinary_lines) - 1,
                    stop_index=max(line["source_line_index"] for line in ordinary_lines) + 1,
                    page_width=page["page_width"],
                    minimum_x_ratio=0.0,
                    maximum_x_ratio=1.0,
                )
            )
        physical_clusters.sort(
            key=lambda cluster: (
                min(line["line_ordinal"] for line in cluster),
                min(line["sample_id"] for line in cluster),
            )
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
            forced_note_sample_id = (
                ordered[0]["sample_id"]
                if len(ordered) == 1
                and ordered[0]["sample_id"] in printed_note_candidate_sample_ids
                else None
            )
            inspected_label_band, same_row_label_evidence = _build_inspected_label_band(
                ordered_numeric_lines=ordered,
                page=page,
                pages=pages,
                local_lines=local_lines,
                permitted_label_sample_ids=(
                    printed_note_label_ids[forced_note_sample_id]
                    if forced_note_sample_id in printed_note_label_ids
                    else None
                ),
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
                if evidence is None:
                    evidence_v2, render_required_v2 = (
                        _build_authenticated_extreme_margin_furniture_evidence_v2(
                            pages=pages,
                            topology_candidates_id=topology_candidates_id,
                            page=page,
                            ordered_numeric_lines=ordered,
                            cluster=cluster,
                            source_record=source_records[0],
                            centers=centers,
                            lane_tolerance=lane_tolerance,
                            scale=scale,
                            matches=matches,
                            selected_snapshot=selected_snapshot,
                            render_by_page=render_by_page,
                        )
                    )
                    evidence = evidence_v2
                    render_required = render_required or render_required_v2
                if evidence is None:
                    vertical_stamp_evidence, vertical_stamp_render_required = (
                        _build_authenticated_extreme_margin_vertical_stamp_furniture_evidence_v4(
                            pages=pages,
                            topology_candidates_id=topology_candidates_id,
                            page=page,
                            ordered_numeric_lines=ordered,
                            cluster=cluster,
                            source_record=source_records[0],
                            centers=centers,
                            lane_tolerance=lane_tolerance,
                            scale=scale,
                            matches=matches,
                            selected_snapshot=selected_snapshot,
                            render_by_page=render_by_page,
                        )
                    )
                    evidence = vertical_stamp_evidence
                    render_required = render_required or vertical_stamp_render_required
                if evidence is None:
                    printed_note_builder = (
                        _build_authenticated_printed_note_reference_furniture_evidence_v4
                        if printed_note_furniture_version == 4
                        else _build_authenticated_printed_note_reference_furniture_evidence_v3
                    )
                    note_evidence, note_render_required = printed_note_builder(
                        pages=pages,
                        topology_candidates_id=(
                            topology_candidates_id
                            if printed_note_furniture_version == 4
                            else printed_note_v3_topology_candidates_id
                        ),
                        page=page,
                        ordered_numeric_lines=ordered,
                        cluster=cluster,
                        source_record=source_records[0],
                        centers=centers,
                        lane_tolerance=lane_tolerance,
                        scale=scale,
                        axis=axis,
                        selected_snapshot=selected_snapshot,
                        render_by_page=render_by_page,
                    )
                    evidence = note_evidence
                    render_required = render_required or note_render_required
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
        structural_gap_anchor_occurrence_ids = [
            match["occurrence_id"]
            for match in sorted(
                matches,
                key=lambda item: (item["source_line_index"], item["occurrence_id"]),
            )
            if match.get("page_sequence") == page_sequence
            and match.get("role_kind") == "STRUCTURAL_GROUP"
            and match.get("occurrence_id") not in bound_occurrence_ids
            and _match_has_effective_exact_source_authority(match)
        ]
        numeric_line_ordinals = [
            source["line_ordinal"]
            for source in universe_by_sample.values()
            if source["page_sequence"] == page_sequence
        ]
        if structural_gap_anchor_occurrence_ids and numeric_line_ordinals:
            for line in local_lines:
                if (
                    line["sample_id"] in universe_by_sample
                    or row_v1._is_numeric(line)
                    or not _extreme_margin_nonnumeric_decoration_surface(line)
                ):
                    continue
                evidence, render_required = (
                    _build_authenticated_extreme_margin_nonnumeric_decoration_v3(
                        pages=pages,
                        topology_candidates_id=topology_candidates_id,
                        page=page,
                        local_lines=local_lines,
                        candidate=line,
                        centers=centers,
                        lane_tolerance=lane_tolerance,
                        scale=scale,
                        matches=matches,
                        structural_gap_anchor_occurrence_ids=(structural_gap_anchor_occurrence_ids),
                        numeric_line_ordinals=numeric_line_ordinals,
                        selected_snapshot=selected_snapshot,
                        render_by_page=render_by_page,
                    )
                )
                if evidence is not None:
                    furniture_evidence.append(evidence)
                elif render_required:
                    render_required_reasons.append(
                        _EXTREME_MARGIN_RENDER_REASON_PREFIX + str(page_sequence)
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


def _validate_extreme_margin_furniture_evidence_axis_v1(
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


def _validate_extreme_margin_v2_exact_crop_proof(value: Any) -> dict[str, Any]:
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
        or not 0 <= value["chromatic_ink_pixel_count"] <= value["ink_pixel_count"]
        or type(value["exact_bbox_rgb_sha256"]) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", value["exact_bbox_rgb_sha256"])
    ):
        raise _error("extreme-margin V2 exact crop proof drifted")
    source_line = _validate_extreme_margin_line_record(source_line)
    bbox = source_line["bbox"]
    if value["pixel_count"] != (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]):
        raise _error("extreme-margin V2 exact crop pixel denominator drifted")
    _validate_extreme_margin_render_binding(value["render_binding"], source_line)
    return canonical_clone_v1(value)


def _validate_printed_note_reference_crop_proof(value: Any) -> dict[str, Any]:
    proof = _validate_extreme_margin_v2_exact_crop_proof(value)
    if not _printed_note_reference_crop_is_neutral_ink(proof):
        raise _error("printed note-reference neutral-ink crop proof drifted")
    return proof


def _validate_extreme_margin_v2_component_proof(
    value: Any,
    *,
    geometry: Mapping[str, Any],
    candidate_crop: Mapping[str, Any],
    numeric_stamp_mode: bool,
) -> None:
    component_axis = value.get("component_axis") if type(value) is dict else None
    render_binding = value.get("render_binding") if type(value) is dict else None
    target_bbox = geometry["candidate_bbox"]
    target_height = target_bbox[3] - target_bbox[1]
    if (
        type(value) is not dict
        or set(value) != _EXTREME_MARGIN_V2_COMPONENT_PROOF_FIELDS
        or type(value["body_text_scale"]) is not float
        or not math.isfinite(value["body_text_scale"])
        or value["body_text_scale"] <= 0
        or value["candidate_center_twice"] != target_bbox[1] + target_bbox[3]
        or value["ink_threshold"] != 220
        or value["chroma_spread_threshold"] != 30
        or value["morphology_kernel_size"]
        != 2 * max(1, min(7, int(value["body_text_scale"] // 8))) + 1
        or type(component_axis) is not list
        or len(component_axis) > _MAX_ROLE_OCCURRENCES
        or any(type(component) is not dict for component in component_axis)
        or component_axis
        != sorted(
            component_axis, key=lambda item: (item.get("bbox"), item.get("closed_pixel_count"))
        )
        or value["component_axis_sha256"] != canonical_json_sha256_v1(component_axis)
        or type(value["expanded_raw_pixel_bbox"]) is not list
        or len(value["expanded_raw_pixel_bbox"]) != 4
        or type(value["expanded_pixel_count"]) is not int
        or value["expanded_pixel_count"] <= 0
        or type(value["expanded_rgb_sha256"]) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", value["expanded_rgb_sha256"])
        or type(value["closed_mask_sha256"]) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", value["closed_mask_sha256"])
        or value["minimum_component_height"] != max(6, (3 * target_height + 1) // 2)
        or value["minimum_original_ink_pixels"] != max(64, 2 * target_height)
        or value["minimum_side_extent_pixels"] != max(4, (target_height + 7) // 8)
        or value["minimum_side_ink_pixels"] != max(8, target_height // 2)
        or value["minimum_target_overlap_ink_pixels"] != max(16, target_height // 4)
        or value["minimum_vertical_extension_pixels"] != max(4, (target_height + 1) // 2)
        or type(render_binding) is not dict
        or set(render_binding) != _EXTREME_MARGIN_RENDER_BINDING_FIELDS
        or render_binding["raw_pixel_bbox"] != value["expanded_raw_pixel_bbox"]
        or render_binding["render_id"] != candidate_crop["render_binding"]["render_id"]
        or render_binding["document_ordinal"]
        != candidate_crop["render_binding"]["document_ordinal"]
        or not same_typed_json_v1(
            render_binding["render_ref"], candidate_crop["render_binding"]["render_ref"]
        )
    ):
        raise _error("extreme-margin V2 expanded component proof drifted")
    try:
        render_ref = render_v1._render_reference(render_binding["render_ref"])
    except (ValueError, RuntimeError) as exc:
        raise _error("extreme-margin V2 component render reference drifted") from exc
    expanded_bbox = value["expanded_raw_pixel_bbox"]
    expected_expanded_bbox = [
        geometry["margin_boundary"],
        max(0, target_bbox[1] - 2 * target_height),
        render_ref["pixel_width"],
        min(render_ref["pixel_height"], target_bbox[3] + 2 * target_height),
    ]
    if (
        expanded_bbox != expected_expanded_bbox
        or value["expanded_pixel_count"]
        != (expanded_bbox[2] - expanded_bbox[0]) * (expanded_bbox[3] - expanded_bbox[1])
        or render_binding["physical_page"] != candidate_crop["render_binding"]["physical_page"]
    ):
        raise _error("extreme-margin V2 expanded RGB denominator drifted")
    for component in component_axis:
        bbox = component.get("bbox") if type(component) is dict else None
        if (
            type(component) is not dict
            or set(component) != _EXTREME_MARGIN_V2_COMPONENT_FIELDS
            or type(bbox) is not list
            or len(bbox) != 4
            or any(type(coordinate) is not int for coordinate in bbox)
            or not (
                expanded_bbox[0] <= bbox[0] < bbox[2] <= expanded_bbox[2]
                and expanded_bbox[1] <= bbox[1] < bbox[3] <= expanded_bbox[3]
            )
            or type(component["closed_pixel_count"]) is not int
            or not 0 < component["closed_pixel_count"] <= (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            or type(component["original_ink_pixel_count"]) is not int
            or not 0 <= component["original_ink_pixel_count"] <= component["closed_pixel_count"]
            or type(component["chromatic_original_ink_pixel_count"]) is not int
            or not 0
            <= component["chromatic_original_ink_pixel_count"]
            <= component["original_ink_pixel_count"]
            or type(component["target_overlap_ink_pixel_count"]) is not int
            or not 0
            <= component["target_overlap_ink_pixel_count"]
            <= component["original_ink_pixel_count"]
            or type(component["above_center_original_ink_pixel_count"]) is not int
            or type(component["below_center_original_ink_pixel_count"]) is not int
            or min(
                component["above_center_original_ink_pixel_count"],
                component["below_center_original_ink_pixel_count"],
            )
            < 0
            or component["above_center_original_ink_pixel_count"]
            + component["below_center_original_ink_pixel_count"]
            > component["original_ink_pixel_count"]
            or component["clear_extent_above_center"]
            != max(0, (value["candidate_center_twice"] - 2 * bbox[1]) // 2)
            or component["clear_extent_below_center"]
            != max(0, (2 * bbox[3] - value["candidate_center_twice"]) // 2)
            or component["vertical_extension_outside_target"]
            != max(0, target_bbox[1] - bbox[1]) + max(0, bbox[3] - target_bbox[3])
        ):
            raise _error("extreme-margin V2 connected component axis drifted")
    if numeric_stamp_mode:
        qualifying = [
            ordinal
            for ordinal, component in enumerate(component_axis)
            if _extreme_margin_v2_numeric_stamp_component_qualifies(
                component,
                margin_boundary=geometry["margin_boundary"],
                target_bbox=target_bbox,
                body_text_scale=value["body_text_scale"],
                candidate_ink_pixel_count=candidate_crop["ink_pixel_count"],
            )
        ]
    else:
        qualifying = [
            ordinal
            for ordinal, component in enumerate(component_axis)
            if _extreme_margin_v2_component_qualifies(
                component,
                margin_boundary=geometry["margin_boundary"],
                target_bbox=target_bbox,
                minimum_component_height=value["minimum_component_height"],
                minimum_original_ink_pixels=value["minimum_original_ink_pixels"],
                minimum_side_extent_pixels=value["minimum_side_extent_pixels"],
                minimum_side_ink_pixels=value["minimum_side_ink_pixels"],
                minimum_target_overlap_ink_pixels=value["minimum_target_overlap_ink_pixels"],
                minimum_vertical_extension_pixels=value["minimum_vertical_extension_pixels"],
            )
        ]
    if (
        value["qualifying_component_count"] != 1
        or type(value["qualifying_component_ordinal"]) is not int
        or qualifying != [value["qualifying_component_ordinal"]]
    ):
        raise _error("extreme-margin V2 component uniqueness drifted")


def _validate_extreme_margin_furniture_evidence_axis_v2(
    evidence_axis: Any,
    *,
    universe_by_sample: Mapping[str, Mapping[str, Any]],
    axis: Mapping[str, Any],
    topology_candidates_id: str | None,
) -> set[str]:
    grid_by_page = {grid["page_sequence"]: grid for grid in axis["column_grids"]}
    evidence_ids = []
    sample_ids = []
    for evidence in evidence_axis:
        if (
            type(evidence) is not dict
            or set(evidence) != _EXTREME_MARGIN_FURNITURE_V2_FIELDS
            or evidence.get("status") != _EXTREME_MARGIN_FURNITURE_V2_STATUS
            or type(evidence.get("evidence_id")) is not str
            or type(evidence.get("snapshot_id")) is not str
            or not evidence["snapshot_id"].startswith("ffdesv1:selected:")
            or type(evidence.get("document_pages_sha256")) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", evidence["document_pages_sha256"])
            or type(evidence.get("page_sequence")) is not int
            or evidence["page_sequence"] <= 0
            or type(evidence.get("sample_id")) is not str
            or not evidence["sample_id"]
            or evidence.get("topology_candidates_id") != topology_candidates_id
        ):
            raise _error("authenticated extreme-margin V2 furniture evidence drifted")
        material = canonical_clone_v1(evidence)
        evidence_id = material.pop("evidence_id")
        if evidence_id != "aforav2:extreme-margin-furniture:" + canonical_json_sha256_v1(material):
            raise _error("authenticated extreme-margin V2 furniture identity drifted")
        cluster = evidence["original_cluster"]
        source = evidence["source_record"]
        if (
            type(cluster) is not dict
            or set(cluster) != _INTERNAL_UNASSIGNED_CLUSTER_FIELDS
            or cluster.get("status") != _OFF_LANE_NUMERIC_CLUSTER_STATUS
            or cluster.get("page_sequence") != evidence["page_sequence"]
            or cluster.get("sample_ids") != [evidence["sample_id"]]
            or type(source) is not dict
        ):
            raise _error("extreme-margin V2 original singleton cluster drifted")
        _validate_numeric_sample_record(source)
        if (
            source["sample_id"] != evidence["sample_id"]
            or source["page_sequence"] != evidence["page_sequence"]
            or source["parsed_token"]["classification"] != "SIGNED_NUMBER"
            or source["owner_kind"] != "SOURCE_ONLY_INTERNAL_CLUSTER"
            or source["owner_id"] != cluster["cluster_id"]
        ):
            raise _error("extreme-margin V2 original numeric owner drifted")
        cluster_material = canonical_clone_v1(cluster)
        cluster_id = cluster_material.pop("cluster_id", None)
        if cluster_id != "aforav2:unassigned:" + canonical_json_sha256_v1(cluster_material):
            raise _error("extreme-margin V2 original cluster identity drifted")
        _validate_inspected_label_band(cluster, {evidence["sample_id"]: source})
        label_proof = evidence["label_collision_proof"]
        full_page_band = evidence["full_page_inspected_label_band"]
        full_page_evidence = _same_row_label_evidence_from_inspected_band(
            full_page_band.get("source_line_axis", []) if type(full_page_band) is dict else []
        )
        if (
            type(label_proof) is not dict
            or set(label_proof) != _EXTREME_MARGIN_V2_LABEL_COLLISION_FIELDS
            or label_proof["candidate_line_ordinal"] != source["line_ordinal"]
            or label_proof["same_row_label_evidence"] != full_page_evidence
            or label_proof["same_row_label_evidence_sha256"]
            != canonical_json_sha256_v1(full_page_evidence)
            or label_proof["status"]
            != (
                "EXACT_MARGIN_SEPARATED_SAME_ROW_LABELS"
                if full_page_evidence
                else "NO_SAME_ROW_LABEL_COLLISION"
            )
            or type(label_proof["semantic_label_line_ordinals"]) is not list
            or label_proof["semantic_label_line_ordinals"]
            != sorted(set(label_proof["semantic_label_line_ordinals"]))
            or any(
                type(ordinal) is not int or ordinal < 0
                for ordinal in label_proof["semantic_label_line_ordinals"]
            )
            or source["line_ordinal"] in label_proof["semantic_label_line_ordinals"]
        ):
            raise _error("extreme-margin V2 exact label collision proof drifted")
        full_page_cluster = canonical_clone_v1(cluster)
        full_page_cluster["inspected_label_band"] = full_page_band
        full_page_cluster["same_row_label_evidence"] = canonical_clone_v1(full_page_evidence)
        full_page_cluster["label_lane_status"] = (
            _LABELED_LABEL_LANE_STATUS if full_page_evidence else _UNLABELED_LABEL_LANE_STATUS
        )
        _validate_inspected_label_band(full_page_cluster, {evidence["sample_id"]: source})
        if (
            full_page_band["document_pages_sha256"] != evidence["document_pages_sha256"]
            or full_page_band["page_sequence"] != evidence["page_sequence"]
        ):
            raise _error("extreme-margin V2 full-page label denominator drifted")
        geometry = evidence["geometry"]
        grid = grid_by_page.get(evidence["page_sequence"])
        bbox = source["bbox"]
        if (
            type(geometry) is not dict
            or set(geometry) != _EXTREME_MARGIN_V2_GEOMETRY_FIELDS
            or type(grid) is not dict
            or geometry["candidate_bbox"] != bbox
            or geometry["candidate_center_quads"] != 2 * (bbox[0] + bbox[2])
            or type(geometry["page_width"]) is not int
            or geometry["page_width"] <= 0
            or geometry["right_edge_gap"] != geometry["page_width"] - bbox[2]
            or type(geometry["lane_centers_quads"]) is not list
            or any(not float(center * 4).is_integer() for center in grid["column_centers"])
            or geometry["lane_centers_quads"]
            != [int(center * 4) for center in grid["column_centers"]]
            or type(geometry["lane_tolerance"]) is not float
            or not math.isfinite(geometry["lane_tolerance"])
            or geometry["lane_tolerance"] <= 0
            or geometry["margin_boundary"]
            != math.ceil(grid["column_centers"][-1] + geometry["lane_tolerance"])
            or bbox[0] < geometry["margin_boundary"]
            or bbox[2] > geometry["page_width"]
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
            or label_proof["margin_boundary"] != geometry["margin_boundary"]
            or label_proof["maximum_label_right"]
            != (
                max(label["bbox"][2] for label in full_page_evidence)
                if full_page_evidence
                else None
            )
            or any(label["bbox"][2] >= geometry["margin_boundary"] for label in full_page_evidence)
        ):
            raise _error("extreme-margin V2 geometry or label separation drifted")
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
            or margin_band["input_page_line_count"] != full_page_band["input_page_line_count"]
            or type(source_axis) is not list
            or len(source_axis) > margin_band["input_page_line_count"]
            or any(
                not same_typed_json_v1(_validate_extreme_margin_line_record(line), line)
                for line in source_axis
            )
            or source_axis
            != sorted(source_axis, key=lambda item: (item["line_ordinal"], item["bbox"]))
            or len({line["line_ordinal"] for line in source_axis}) != len(source_axis)
            or len({line["sample_id"] for line in source_axis}) != len(source_axis)
            or margin_band["source_line_axis_sha256"] != canonical_json_sha256_v1(source_axis)
            or any(
                line["bbox"][0] < geometry["margin_boundary"]
                or line["bbox"][2] > geometry["page_width"]
                or not (line["vietocr_text"].strip() or line["numeric_raw_prediction"].strip())
                for line in source_axis
            )
            or type(peer_ordinals) is not list
            or peer_ordinals != sorted(set(peer_ordinals))
            or len(peer_ordinals) < 2
        ):
            raise _error("extreme-margin V2 complete source-band denominator drifted")
        candidate_lines = [
            line for line in source_axis if line["sample_id"] == evidence["sample_id"]
        ]
        candidate_crop = _validate_extreme_margin_v2_exact_crop_proof(
            evidence["candidate_crop_proof"]
        )
        candidate_surface_mode = _extreme_margin_v2_candidate_surface_mode(candidate_lines[0])
        numeric_stamp_mode = candidate_surface_mode == "NUMERIC_SINGLE_DIGIT_ROTATED_STAMP"
        if (
            len(candidate_lines) != 1
            or not same_typed_json_v1(candidate_lines[0], candidate_crop["source_line_record"])
            or candidate_lines[0]["bbox"] != source["bbox"]
            or candidate_lines[0]["line_ordinal"] != source["line_ordinal"]
            or candidate_lines[0]["crop_ref"] != source["crop_ref"]
            or candidate_lines[0]["numeric_raw_prediction"] != source["raw_prediction"]
            or candidate_lines[0]["numeric_reader_score"] != source["reader_score"]
            or candidate_surface_mode is None
            or (
                numeric_stamp_mode
                and geometry["candidate_bbox"][0] < (geometry["page_width"] * 19) // 20
            )
            or (
                numeric_stamp_mode
                and (
                    candidate_crop["ink_pixel_count"] <= 0
                    or candidate_crop["chromatic_ink_pixel_count"] * 4
                    < candidate_crop["ink_pixel_count"] * 3
                )
            )
            or not set(peer_ordinals).issubset(
                _extreme_margin_v2_geometric_peer_ordinals(source_axis, candidate_lines[0])
            )
        ):
            raise _error("extreme-margin V2 candidate or peer source binding drifted")
        peer_crops = evidence["peer_crop_proofs"]
        source_by_ordinal = {line["line_ordinal"]: line for line in source_axis}
        if (
            candidate_crop["render_binding"]["physical_page"] != evidence["page_sequence"]
            or candidate_crop["render_binding"]["render_ref"]["pixel_width"]
            != geometry["page_width"]
            or type(peer_crops) is not list
            or len(peer_ordinals) < (3 if numeric_stamp_mode else 2)
            or [proof["source_line_record"]["line_ordinal"] for proof in peer_crops]
            != peer_ordinals
            or any(
                not same_typed_json_v1(
                    _validate_extreme_margin_v2_exact_crop_proof(proof)["source_line_record"],
                    source_by_ordinal.get(proof["source_line_record"]["line_ordinal"]),
                )
                or proof["chromatic_ink_pixel_count"] * 2 < proof["ink_pixel_count"]
                or not _extreme_margin_peer_surfaces_are_nonnumeric(proof["source_line_record"])
                or proof["render_binding"]["render_id"]
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
            raise _error("extreme-margin V2 authenticated chromatic peer axis drifted")
        _validate_extreme_margin_v2_component_proof(
            evidence["expanded_component_proof"],
            geometry=geometry,
            candidate_crop=candidate_crop,
            numeric_stamp_mode=numeric_stamp_mode,
        )
        expected_final = canonical_clone_v1(source)
        expected_final["owner_kind"] = _EXTREME_MARGIN_FURNITURE_OWNER_KIND
        expected_final["owner_id"] = evidence_id
        if not same_typed_json_v1(universe_by_sample.get(evidence["sample_id"]), expected_final):
            raise _error("extreme-margin V2 furniture universe owner drifted")
        evidence_ids.append(evidence_id)
        sample_ids.append(evidence["sample_id"])
    if len(evidence_ids) != len(set(evidence_ids)) or len(sample_ids) != len(set(sample_ids)):
        raise _error("authenticated extreme-margin V2 furniture ownership repeats")
    return set(sample_ids)


def _validate_extreme_margin_vertical_stamp_component_proof_v4(
    value: Any,
    *,
    geometry: Mapping[str, Any],
    candidate_crop: Mapping[str, Any],
) -> None:
    component_axis = value.get("component_axis") if type(value) is dict else None
    bbox = geometry["candidate_bbox"]
    height = geometry["candidate_height"]
    if (
        type(value) is not dict
        or set(value) != _EXTREME_MARGIN_VERTICAL_STAMP_V4_COMPONENT_PROOF_FIELDS
        or value.get("status") != _EXTREME_MARGIN_VERTICAL_STAMP_V4_COMPONENT_STATUS
        or value.get("candidate_center_twice") != bbox[1] + bbox[3]
        or value.get("ink_threshold") != 220
        or value.get("chroma_spread_threshold") != 30
        or value.get("minimum_component_ink_pixel_count")
        != max(8, math.ceil(geometry["body_text_scale"] / 4))
        or type(component_axis) is not list
        or not component_axis
        or len(component_axis) > _MAX_ROLE_OCCURRENCES
        or component_axis
        != sorted(
            component_axis,
            key=lambda component: (
                component.get("bbox"),
                component.get("ink_pixel_count"),
                component.get("chromatic_ink_pixel_count"),
            ),
        )
        or value.get("component_axis_sha256") != canonical_json_sha256_v1(component_axis)
        or not same_typed_json_v1(value.get("render_binding"), candidate_crop["render_binding"])
    ):
        raise _error("extreme-right vertical-stamp V4 component proof drifted")
    for component in component_axis:
        component_bbox = component.get("bbox") if type(component) is dict else None
        if (
            type(component) is not dict
            or set(component) != _EXTREME_MARGIN_VERTICAL_STAMP_V4_COMPONENT_FIELDS
            or type(component_bbox) is not list
            or len(component_bbox) != 4
            or any(type(coordinate) is not int for coordinate in component_bbox)
            or not (
                bbox[0] <= component_bbox[0] < component_bbox[2] <= bbox[2]
                and bbox[1] <= component_bbox[1] < component_bbox[3] <= bbox[3]
            )
            or type(component["ink_pixel_count"]) is not int
            or not 0
            < component["ink_pixel_count"]
            <= (component_bbox[2] - component_bbox[0]) * (component_bbox[3] - component_bbox[1])
            or type(component["chromatic_ink_pixel_count"]) is not int
            or not 0 <= component["chromatic_ink_pixel_count"] <= component["ink_pixel_count"]
        ):
            raise _error("extreme-right vertical-stamp V4 component axis drifted")
    minimum_ink = value["minimum_component_ink_pixel_count"]
    qualifying = [
        ordinal
        for ordinal, component in enumerate(component_axis)
        if component["ink_pixel_count"] >= minimum_ink
    ]
    qualifying_components = [component_axis[ordinal] for ordinal in qualifying]
    vertical_span = (
        max(component["bbox"][3] for component in qualifying_components)
        - min(component["bbox"][1] for component in qualifying_components)
        if qualifying_components
        else 0
    )
    if (
        len(qualifying) < 3
        or value["qualifying_component_count"] != len(qualifying)
        or value["qualifying_component_ordinals"] != qualifying
        or value["qualifying_vertical_span"] != vertical_span
        or vertical_span * 4 < height * 3
        or not any(
            (component["bbox"][1] - bbox[1]) * 3 <= height for component in qualifying_components
        )
        or not any(
            (bbox[3] - component["bbox"][3]) * 3 <= height for component in qualifying_components
        )
    ):
        raise _error("extreme-right vertical-stamp V4 component peer chain drifted")


def _validate_extreme_margin_vertical_stamp_furniture_axis_v4(
    evidence_axis: Any,
    *,
    universe_by_sample: Mapping[str, Mapping[str, Any]],
    axis: Mapping[str, Any],
    topology_candidates_id: str | None,
) -> set[str]:
    grid_by_page = {grid["page_sequence"]: grid for grid in axis["column_grids"]}
    evidence_ids = []
    sample_ids = []
    for evidence in evidence_axis:
        if (
            type(evidence) is not dict
            or set(evidence) != _EXTREME_MARGIN_VERTICAL_STAMP_V4_FIELDS
            or evidence.get("status") != _EXTREME_MARGIN_VERTICAL_STAMP_V4_STATUS
            or type(evidence.get("evidence_id")) is not str
            or type(evidence.get("snapshot_id")) is not str
            or not evidence["snapshot_id"].startswith("ffdesv1:selected:")
            or type(evidence.get("document_pages_sha256")) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", evidence["document_pages_sha256"])
            or type(evidence.get("page_sequence")) is not int
            or evidence["page_sequence"] <= 0
            or type(evidence.get("sample_id")) is not str
            or not evidence["sample_id"]
            or evidence.get("topology_candidates_id") != topology_candidates_id
        ):
            raise _error("authenticated extreme-right vertical-stamp V4 evidence drifted")
        material = canonical_clone_v1(evidence)
        evidence_id = material.pop("evidence_id")
        if evidence_id != (
            "aforav2:extreme-right-vertical-stamp-v4:" + canonical_json_sha256_v1(material)
        ):
            raise _error("authenticated extreme-right vertical-stamp V4 identity drifted")
        cluster = evidence["original_cluster"]
        source = evidence["source_record"]
        if (
            type(cluster) is not dict
            or set(cluster) != _INTERNAL_UNASSIGNED_CLUSTER_FIELDS
            or cluster.get("status") != _OFF_LANE_NUMERIC_CLUSTER_STATUS
            or cluster.get("page_sequence") != evidence["page_sequence"]
            or cluster.get("sample_ids") != [evidence["sample_id"]]
            or type(source) is not dict
        ):
            raise _error("extreme-right vertical-stamp V4 singleton cluster drifted")
        _validate_numeric_sample_record(source)
        if (
            source["sample_id"] != evidence["sample_id"]
            or source["page_sequence"] != evidence["page_sequence"]
            or source["parsed_token"]["classification"] != "SIGNED_NUMBER"
            or source["owner_kind"] != "SOURCE_ONLY_INTERNAL_CLUSTER"
            or source["owner_id"] != cluster["cluster_id"]
        ):
            raise _error("extreme-right vertical-stamp V4 original numeric owner drifted")
        cluster_material = canonical_clone_v1(cluster)
        cluster_id = cluster_material.pop("cluster_id", None)
        if cluster_id != "aforav2:unassigned:" + canonical_json_sha256_v1(cluster_material):
            raise _error("extreme-right vertical-stamp V4 cluster identity drifted")
        _validate_inspected_label_band(cluster, {evidence["sample_id"]: source})

        full_page_band = evidence["full_page_inspected_label_band"]
        full_page_evidence = _same_row_label_evidence_from_inspected_band(
            full_page_band.get("source_line_axis", []) if type(full_page_band) is dict else []
        )
        full_page_cluster = canonical_clone_v1(cluster)
        full_page_cluster["inspected_label_band"] = full_page_band
        full_page_cluster["same_row_label_evidence"] = canonical_clone_v1(full_page_evidence)
        full_page_cluster["label_lane_status"] = (
            _LABELED_LABEL_LANE_STATUS if full_page_evidence else _UNLABELED_LABEL_LANE_STATUS
        )
        _validate_inspected_label_band(full_page_cluster, {evidence["sample_id"]: source})
        if (
            full_page_band["document_pages_sha256"] != evidence["document_pages_sha256"]
            or full_page_band["page_sequence"] != evidence["page_sequence"]
        ):
            raise _error("extreme-right vertical-stamp V4 label denominator drifted")

        geometry = evidence["geometry"]
        grid = grid_by_page.get(evidence["page_sequence"])
        bbox = source["bbox"]
        if (
            type(geometry) is not dict
            or set(geometry) != _EXTREME_MARGIN_VERTICAL_STAMP_V4_GEOMETRY_FIELDS
            or type(grid) is not dict
            or type(geometry["body_text_scale"]) is not float
            or not math.isfinite(geometry["body_text_scale"])
            or geometry["body_text_scale"] <= 0
            or type(geometry["lane_tolerance"]) is not float
            or not math.isfinite(geometry["lane_tolerance"])
            or geometry["lane_tolerance"] <= 0
            or geometry["candidate_bbox"] != bbox
            or geometry["candidate_center_quads"] != 2 * (bbox[0] + bbox[2])
            or geometry["candidate_width"] != bbox[2] - bbox[0]
            or geometry["candidate_height"] != bbox[3] - bbox[1]
            or geometry["lane_centers_quads"]
            != [int(center * 4) for center in grid["column_centers"]]
            or any(not float(center * 4).is_integer() for center in grid["column_centers"])
            or geometry["margin_boundary"]
            != math.ceil(grid["column_centers"][-1] + geometry["lane_tolerance"])
            or geometry["page_edge_numerator"] != 19
            or geometry["page_edge_denominator"] != 20
            or geometry["right_edge_gap"] != geometry["page_width"] - bbox[2]
            or bbox[0] < geometry["margin_boundary"]
            or bbox[0] * geometry["page_edge_denominator"]
            < geometry["page_width"] * geometry["page_edge_numerator"]
            or bbox[2] > geometry["page_width"]
            or not 0 <= geometry["right_edge_gap"] <= math.ceil(geometry["body_text_scale"] / 4)
            or geometry["candidate_height"] < math.ceil(3 * geometry["body_text_scale"] / 2)
            or geometry["candidate_height"] < geometry["candidate_width"]
            or source["column_ordinal"] >= len(grid["column_centers"])
            or source["column_center"] != grid["column_centers"][source["column_ordinal"]]
            or source["column_ordinal"]
            != min(
                range(len(grid["column_centers"])),
                key=lambda index: abs(
                    geometry["candidate_center_quads"] - geometry["lane_centers_quads"][index]
                ),
            )
            or abs(
                geometry["candidate_center_quads"]
                - geometry["lane_centers_quads"][source["column_ordinal"]]
            )
            <= 4 * geometry["lane_tolerance"]
        ):
            raise _error("extreme-right vertical-stamp V4 geometry drifted")

        label_proof = evidence["label_collision_proof"]
        if (
            type(label_proof) is not dict
            or set(label_proof) != _EXTREME_MARGIN_V2_LABEL_COLLISION_FIELDS
            or label_proof["candidate_line_ordinal"] != source["line_ordinal"]
            or label_proof["margin_boundary"] != geometry["margin_boundary"]
            or label_proof["same_row_label_evidence"] != full_page_evidence
            or label_proof["same_row_label_evidence_sha256"]
            != canonical_json_sha256_v1(full_page_evidence)
            or label_proof["maximum_label_right"]
            != (
                max(label["bbox"][2] for label in full_page_evidence)
                if full_page_evidence
                else None
            )
            or any(label["bbox"][2] >= geometry["margin_boundary"] for label in full_page_evidence)
            or label_proof["status"]
            != (
                "EXACT_MARGIN_SEPARATED_SAME_ROW_LABELS"
                if full_page_evidence
                else "NO_SAME_ROW_LABEL_COLLISION"
            )
            or type(label_proof["semantic_label_line_ordinals"]) is not list
            or label_proof["semantic_label_line_ordinals"]
            != sorted(set(label_proof["semantic_label_line_ordinals"]))
            or source["line_ordinal"] in label_proof["semantic_label_line_ordinals"]
        ):
            raise _error("extreme-right vertical-stamp V4 label collision proof drifted")

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
            or margin_band["input_page_line_count"] != full_page_band["input_page_line_count"]
            or type(source_axis) is not list
            or len(source_axis) > margin_band["input_page_line_count"]
            or source_axis
            != sorted(source_axis, key=lambda line: (line["line_ordinal"], line["bbox"]))
            or len({line["line_ordinal"] for line in source_axis}) != len(source_axis)
            or len({line["sample_id"] for line in source_axis}) != len(source_axis)
            or any(
                not same_typed_json_v1(_validate_extreme_margin_line_record(line), line)
                or line["bbox"][0] < geometry["margin_boundary"]
                or line["bbox"][2] > geometry["page_width"]
                for line in source_axis
            )
            or margin_band["source_line_axis_sha256"] != canonical_json_sha256_v1(source_axis)
            or type(peer_ordinals) is not list
            or peer_ordinals != sorted(set(peer_ordinals))
        ):
            raise _error("extreme-right vertical-stamp V4 complete margin band drifted")
        candidate_lines = [
            line for line in source_axis if line["sample_id"] == evidence["sample_id"]
        ]
        candidate_crop = _validate_extreme_margin_v2_exact_crop_proof(
            evidence["candidate_crop_proof"]
        )
        if (
            len(candidate_lines) != 1
            or not same_typed_json_v1(candidate_lines[0], candidate_crop["source_line_record"])
            or candidate_lines[0]["bbox"] != source["bbox"]
            or candidate_lines[0]["line_ordinal"] != source["line_ordinal"]
            or candidate_lines[0]["crop_ref"] != source["crop_ref"]
            or candidate_lines[0]["numeric_raw_prediction"] != source["raw_prediction"]
            or candidate_lines[0]["numeric_reader_score"] != source["reader_score"]
            or not _extreme_margin_vertical_stamp_surface_v4(candidate_lines[0])
            or candidate_crop["render_binding"]["physical_page"] != evidence["page_sequence"]
            or candidate_crop["render_binding"]["render_ref"]["pixel_width"]
            != geometry["page_width"]
        ):
            raise _error("extreme-right vertical-stamp V4 candidate binding drifted")
        _validate_extreme_margin_vertical_stamp_component_proof_v4(
            evidence["component_peer_proof"],
            geometry=geometry,
            candidate_crop=candidate_crop,
        )

        chromatic_mode = (
            geometry["candidate_height"] >= math.ceil(3 * geometry["body_text_scale"])
            and candidate_crop["chromatic_ink_pixel_count"] * 2 >= candidate_crop["ink_pixel_count"]
        )
        clipped_mode = (
            geometry["right_edge_gap"] <= 1
            and candidate_crop["chromatic_ink_pixel_count"] * 4 <= candidate_crop["ink_pixel_count"]
            and len(peer_ordinals) >= 3
        )
        expected_mode = (
            _EXTREME_MARGIN_VERTICAL_STAMP_V4_CHROMATIC_MODE
            if chromatic_mode and not clipped_mode
            else _EXTREME_MARGIN_VERTICAL_STAMP_V4_CLIPPED_MODE
            if clipped_mode and not chromatic_mode
            else None
        )
        source_by_ordinal = {line["line_ordinal"]: line for line in source_axis}
        peer_crops = evidence["peer_crop_proofs"]
        if (
            geometry["stamp_mode"] != expected_mode
            or type(peer_crops) is not list
            or [proof.get("source_line_record", {}).get("line_ordinal") for proof in peer_crops]
            != peer_ordinals
            or (
                expected_mode == _EXTREME_MARGIN_VERTICAL_STAMP_V4_CHROMATIC_MODE
                and (peer_ordinals or peer_crops)
            )
            or (
                expected_mode == _EXTREME_MARGIN_VERTICAL_STAMP_V4_CLIPPED_MODE
                and (
                    len(peer_crops) < 3
                    or not set(peer_ordinals).issubset(
                        _extreme_margin_v2_geometric_peer_ordinals(source_axis, candidate_lines[0])
                    )
                )
            )
            or any(
                not same_typed_json_v1(
                    _validate_extreme_margin_v2_exact_crop_proof(proof)["source_line_record"],
                    source_by_ordinal.get(proof["source_line_record"]["line_ordinal"]),
                )
                or proof["ink_pixel_count"] <= 0
                or not _extreme_margin_peer_surfaces_are_nonnumeric(proof["source_line_record"])
                or proof["render_binding"]["render_id"]
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
            raise _error("extreme-right vertical-stamp V4 peer-mode proof drifted")

        expected_final = canonical_clone_v1(source)
        expected_final["owner_kind"] = _EXTREME_MARGIN_FURNITURE_OWNER_KIND
        expected_final["owner_id"] = evidence_id
        if not same_typed_json_v1(universe_by_sample.get(evidence["sample_id"]), expected_final):
            raise _error("extreme-right vertical-stamp V4 universe owner drifted")
        evidence_ids.append(evidence_id)
        sample_ids.append(evidence["sample_id"])
    if len(evidence_ids) != len(set(evidence_ids)) or len(sample_ids) != len(set(sample_ids)):
        raise _error("authenticated extreme-right vertical-stamp V4 ownership repeats")
    return set(sample_ids)


def _validate_extreme_margin_nonnumeric_decoration_axis_v3(
    evidence_axis: Any,
    *,
    universe_by_sample: Mapping[str, Mapping[str, Any]],
    axis: Mapping[str, Any],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
    topology_candidates_id: str | None,
) -> None:
    grid_by_page = {grid["page_sequence"]: grid for grid in axis["column_grids"]}
    evidence_ids: list[str] = []
    line_keys: list[tuple[int, int]] = []
    for evidence in evidence_axis:
        if (
            type(evidence) is not dict
            or set(evidence) != _EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_FIELDS
            or evidence.get("status") != _EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_STATUS
            or type(evidence.get("evidence_id")) is not str
            or type(evidence.get("snapshot_id")) is not str
            or not evidence["snapshot_id"].startswith("ffdesv1:selected:")
            or type(evidence.get("document_pages_sha256")) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", evidence["document_pages_sha256"])
            or type(evidence.get("page_sequence")) is not int
            or evidence["page_sequence"] <= 0
            or type(evidence.get("sample_id")) is not str
            or not evidence["sample_id"]
            or evidence.get("topology_candidates_id") != topology_candidates_id
        ):
            raise _error("authenticated nonnumeric margin-decoration evidence drifted")
        material = canonical_clone_v1(evidence)
        evidence_id = material.pop("evidence_id")
        if evidence_id != "aforav2:extreme-margin-furniture:" + canonical_json_sha256_v1(material):
            raise _error("authenticated nonnumeric margin-decoration identity drifted")
        source = _validate_extreme_margin_line_record(evidence["source_record"])
        candidate_crop = _validate_extreme_margin_v2_exact_crop_proof(
            evidence["candidate_crop_proof"]
        )
        if (
            evidence["sample_id"] != source["sample_id"]
            or evidence["sample_id"] in universe_by_sample
            or evidence["page_sequence"] != candidate_crop["render_binding"]["physical_page"]
            or not same_typed_json_v1(candidate_crop["source_line_record"], source)
            or not _extreme_margin_nonnumeric_decoration_surface(source)
        ):
            raise _error("nonnumeric margin-decoration exact source binding drifted")

        geometry = evidence["geometry"]
        grid = grid_by_page.get(evidence["page_sequence"])
        bbox = source["bbox"]
        if (
            type(geometry) is not dict
            or set(geometry) != _EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_GEOMETRY_FIELDS
            or type(grid) is not dict
            or type(geometry["body_text_scale"]) is not float
            or not math.isfinite(geometry["body_text_scale"])
            or geometry["body_text_scale"] <= 0
            or type(geometry["lane_tolerance"]) is not float
            or not math.isfinite(geometry["lane_tolerance"])
            or geometry["lane_tolerance"] <= 0
            or geometry["candidate_bbox"] != bbox
            or geometry["candidate_center_quads"] != 2 * (bbox[0] + bbox[2])
            or geometry["lane_centers_quads"]
            != [int(center * 4) for center in grid["column_centers"]]
            or any(not float(center * 4).is_integer() for center in grid["column_centers"])
            or geometry["margin_boundary"]
            != math.ceil(grid["column_centers"][-1] + geometry["lane_tolerance"])
            or geometry["page_width"]
            != candidate_crop["render_binding"]["render_ref"]["pixel_width"]
            or geometry["right_edge_gap"] != geometry["page_width"] - bbox[2]
            or bbox[0] < geometry["margin_boundary"]
            or bbox[0] * 50 < geometry["page_width"] * 49
            or bbox[2] > geometry["page_width"]
            or geometry["right_edge_gap"] > math.ceil(geometry["body_text_scale"] / 2)
            or bbox[2] - bbox[0] > math.ceil(geometry["body_text_scale"] * 1.25)
            or type(geometry["body_source_line_start"]) is not int
            or type(geometry["body_source_line_stop_exclusive"]) is not int
            or not geometry["body_source_line_start"]
            <= source["line_ordinal"]
            < geometry["body_source_line_stop_exclusive"]
            or type(geometry["preceding_numeric_line_ordinal"]) is not int
            or geometry["following_numeric_line_ordinal"] is not None
            and type(geometry["following_numeric_line_ordinal"]) is not int
        ):
            raise _error("nonnumeric margin-decoration geometry drifted")
        numeric_ordinals = sorted(
            {
                sample["line_ordinal"]
                for sample in universe_by_sample.values()
                if sample["page_sequence"] == evidence["page_sequence"]
                and geometry["body_source_line_start"]
                <= sample["line_ordinal"]
                < geometry["body_source_line_stop_exclusive"]
            }
        )
        preceding = [ordinal for ordinal in numeric_ordinals if ordinal < source["line_ordinal"]]
        following = [ordinal for ordinal in numeric_ordinals if ordinal > source["line_ordinal"]]
        expected_following = following[0] if following else None
        if (
            not preceding
            or geometry["preceding_numeric_line_ordinal"] != preceding[-1]
            or geometry["following_numeric_line_ordinal"] != expected_following
            or source["line_ordinal"] - preceding[-1] > 4
            or (
                expected_following is None
                and geometry["body_source_line_stop_exclusive"] - source["line_ordinal"] > 2
            )
            or (expected_following is not None and expected_following - source["line_ordinal"] > 4)
        ):
            raise _error("nonnumeric margin-decoration numeric neighbor binding drifted")

        expected_anchors = [
            occurrence["occurrence_id"]
            for occurrence in sorted(
                occurrence_by_id.values(),
                key=lambda item: (
                    item.get("label_match", {}).get("source_line_index", 2**31),
                    item["occurrence_id"],
                ),
            )
            if occurrence.get("role_kind") == "STRUCTURAL_GROUP"
            and occurrence.get("has_bound_value_row") is False
            and occurrence.get("label_match", {}).get("page_sequence") == evidence["page_sequence"]
            and _match_has_effective_exact_source_authority(occurrence.get("label_match", {}))
        ]
        expected_semantic_ordinals = sorted(
            {
                ordinal
                for occurrence in occurrence_by_id.values()
                if occurrence.get("label_match", {}).get("page_sequence")
                == evidence["page_sequence"]
                for ordinal in range(
                    occurrence["label_match"]["source_line_index"],
                    occurrence["label_match"]["end_source_line_index"] + 1,
                )
            }
        )
        if (
            not expected_anchors
            or evidence["structural_gap_anchor_occurrence_ids"] != expected_anchors
            or evidence["semantic_label_line_ordinals"] != expected_semantic_ordinals
            or source["line_ordinal"] in expected_semantic_ordinals
        ):
            raise _error("nonnumeric margin-decoration structural anchor drifted")

        margin_band = evidence["margin_band"]
        source_axis = margin_band.get("source_line_axis") if type(margin_band) is dict else None
        if (
            type(margin_band) is not dict
            or set(margin_band) != _EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_BAND_FIELDS
            or margin_band["document_pages_sha256"] != evidence["document_pages_sha256"]
            or margin_band["page_sequence"] != evidence["page_sequence"]
            or type(margin_band["input_page_line_count"]) is not int
            or type(source_axis) is not list
            or len(source_axis) > margin_band["input_page_line_count"]
            or source_axis
            != sorted(source_axis, key=lambda item: (item["line_ordinal"], item["bbox"]))
            or len({item["line_ordinal"] for item in source_axis}) != len(source_axis)
            or len({item["sample_id"] for item in source_axis}) != len(source_axis)
            or any(
                not same_typed_json_v1(_validate_extreme_margin_line_record(line), line)
                or line["bbox"][0] < geometry["margin_boundary"]
                or line["bbox"][2] > geometry["page_width"]
                for line in source_axis
            )
            or margin_band["source_line_axis_sha256"] != canonical_json_sha256_v1(source_axis)
            or [line for line in source_axis if line["sample_id"] == evidence["sample_id"]]
            != [source]
        ):
            raise _error("nonnumeric margin-decoration complete source band drifted")
        evidence_ids.append(evidence_id)
        line_keys.append((evidence["page_sequence"], source["line_ordinal"]))
    if len(evidence_ids) != len(set(evidence_ids)) or len(line_keys) != len(set(line_keys)):
        raise _error("nonnumeric margin-decoration evidence repeats one source line")


def _validate_printed_note_reference_furniture_evidence_axis_v3(
    evidence_axis: Any,
    *,
    universe_by_sample: Mapping[str, Mapping[str, Any]],
    axis: Mapping[str, Any],
    topology_candidates_id: str | None,
) -> set[str]:
    grid_by_page = {grid["page_sequence"]: grid for grid in axis["column_grids"]}
    row_by_occurrence = {row["label_match"].get("occurrence_id"): row for row in axis["rows"]}
    evidence_ids = []
    sample_ids = []
    for evidence in evidence_axis:
        if (
            type(evidence) is not dict
            or set(evidence) != _PRINTED_NOTE_REFERENCE_FURNITURE_V3_FIELDS
            or evidence.get("status") != _PRINTED_NOTE_REFERENCE_FURNITURE_V3_STATUS
            or type(evidence.get("evidence_id")) is not str
            or type(evidence.get("snapshot_id")) is not str
            or not evidence["snapshot_id"].startswith("ffdesv1:selected:")
            or type(evidence.get("document_pages_sha256")) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", evidence["document_pages_sha256"])
            or type(evidence.get("page_sequence")) is not int
            or evidence["page_sequence"] <= 0
            or type(evidence.get("sample_id")) is not str
            or not evidence["sample_id"]
            or type(topology_candidates_id) is not str
            or not topology_candidates_id.startswith("aftcv2:result:")
            or type(evidence.get("topology_candidates_id")) is not str
            or not evidence["topology_candidates_id"].startswith("aftcv2:result:")
        ):
            raise _error("authenticated printed note-reference furniture evidence drifted")
        material = canonical_clone_v1(evidence)
        evidence_id = material.pop("evidence_id")
        if evidence_id != "aforav2:extreme-margin-furniture:" + canonical_json_sha256_v1(material):
            raise _error("authenticated printed note-reference furniture identity drifted")
        cluster = evidence["original_cluster"]
        source = evidence["source_record"]
        if (
            type(cluster) is not dict
            or set(cluster) != _INTERNAL_UNASSIGNED_CLUSTER_FIELDS
            or cluster.get("status") != _OFF_LANE_NUMERIC_CLUSTER_STATUS
            or cluster.get("page_sequence") != evidence["page_sequence"]
            or cluster.get("sample_ids") != [evidence["sample_id"]]
            or cluster.get("label_lane_status") != _LABELED_LABEL_LANE_STATUS
            or not cluster.get("same_row_label_evidence")
            or type(source) is not dict
        ):
            raise _error("printed note-reference original labeled singleton cluster drifted")
        _validate_numeric_sample_record(source)
        if (
            source["sample_id"] != evidence["sample_id"]
            or source["page_sequence"] != evidence["page_sequence"]
            or source["parsed_token"]["classification"] != "SIGNED_NUMBER"
            or source["owner_kind"] != "SOURCE_ONLY_INTERNAL_CLUSTER"
            or source["owner_id"] != cluster["cluster_id"]
        ):
            raise _error("printed note-reference original numeric owner drifted")
        cluster_material = canonical_clone_v1(cluster)
        cluster_id = cluster_material.pop("cluster_id", None)
        if cluster_id != "aforav2:unassigned:" + canonical_json_sha256_v1(cluster_material):
            raise _error("printed note-reference original cluster identity drifted")
        _validate_inspected_label_band(cluster, {evidence["sample_id"]: source})
        if (
            cluster["inspected_label_band"]["document_pages_sha256"]
            != evidence["document_pages_sha256"]
            or cluster["inspected_label_band"]["page_sequence"] != evidence["page_sequence"]
        ):
            raise _error("printed note-reference cluster document binding drifted")

        geometry = evidence["geometry"]
        grid = grid_by_page.get(evidence["page_sequence"])
        bbox = source["bbox"]
        if (
            type(geometry) is not dict
            or set(geometry) != _PRINTED_NOTE_REFERENCE_GEOMETRY_V3_FIELDS
            or type(grid) is not dict
            or len(grid["column_centers"]) < 2
            or type(geometry["body_text_scale"]) is not float
            or not math.isfinite(geometry["body_text_scale"])
            or geometry["body_text_scale"] <= 0
            or geometry["candidate_bbox"] != bbox
            or geometry["candidate_center_twice"] != bbox[0] + bbox[2]
            or type(geometry["candidate_note_value"]) is not int
            or not 1 <= geometry["candidate_note_value"] <= 999
            or type(geometry["page_width"]) is not int
            or geometry["page_width"] <= 0
            or bbox[2] > geometry["page_width"]
            or type(geometry["lane_tolerance"]) is not float
            or not math.isfinite(geometry["lane_tolerance"])
            or geometry["lane_tolerance"] <= 0
            or type(geometry["lane_centers_quads"]) is not list
            or any(not float(center * 4).is_integer() for center in grid["column_centers"])
            or geometry["lane_centers_quads"]
            != [int(center * 4) for center in grid["column_centers"]]
            or geometry["first_financial_lane_left_boundary"]
            != math.floor(grid["column_centers"][0] - geometry["lane_tolerance"])
            or bbox[2] > geometry["first_financial_lane_left_boundary"]
            or source["column_ordinal"]
            != min(
                range(len(grid["column_centers"])),
                key=lambda index: abs(
                    geometry["candidate_center_twice"] - geometry["lane_centers_quads"][index] // 2
                ),
            )
            or source["column_center"] != grid["column_centers"][source["column_ordinal"]]
            or abs(
                geometry["candidate_center_twice"] / 2
                - grid["column_centers"][source["column_ordinal"]]
            )
            <= geometry["lane_tolerance"]
            or type(geometry["qualifying_note_reference_row_count"]) is not int
            or geometry["qualifying_note_reference_row_count"] < 3
        ):
            raise _error("printed note-reference geometry or column exclusion drifted")

        candidate_crop = _validate_printed_note_reference_crop_proof(
            evidence["candidate_crop_proof"]
        )
        candidate_line = candidate_crop["source_line_record"]
        candidate_value = _printed_note_reference_exact_integer_v3(
            {
                "numeric_recognition": {"raw_prediction": candidate_line["numeric_raw_prediction"]},
                "vietocr_text": candidate_line["vietocr_text"],
            }
        )
        if (
            candidate_value != geometry["candidate_note_value"]
            or candidate_line["sample_id"] != source["sample_id"]
            or candidate_line["bbox"] != source["bbox"]
            or candidate_line["line_ordinal"] != source["line_ordinal"]
            or candidate_line["crop_ref"] != source["crop_ref"]
            or candidate_line["numeric_raw_prediction"] != source["raw_prediction"]
            or candidate_line["numeric_reader_score"] != source["reader_score"]
            or candidate_crop["render_binding"]["physical_page"] != evidence["page_sequence"]
            or candidate_crop["render_binding"]["render_ref"]["pixel_width"]
            != geometry["page_width"]
        ):
            raise _error("printed note-reference candidate source or pixel binding drifted")

        header = evidence["header_proof"]
        header_axis = header.get("source_line_axis") if type(header) is dict else None
        header_crops = header.get("crop_proofs") if type(header) is dict else None
        if (
            type(header) is not dict
            or set(header) != _PRINTED_NOTE_REFERENCE_HEADER_FIELDS
            or header["status"] != _PRINTED_NOTE_REFERENCE_HEADER_STATUS
            or header["normalized_surface"] != "thuyet minh"
            or type(header_axis) is not list
            or len(header_axis) not in {1, 2}
            or any(
                not same_typed_json_v1(_validate_extreme_margin_line_record(line), line)
                for line in header_axis
            )
            or header["source_line_axis_sha256"] != canonical_json_sha256_v1(header_axis)
            or type(header_crops) is not list
            or len(header_crops) != len(header_axis)
            or header["header_bbox"] != geometry["header_bbox"]
            or header["header_bbox"]
            != [
                min(line["bbox"][0] for line in header_axis),
                min(line["bbox"][1] for line in header_axis),
                max(line["bbox"][2] for line in header_axis),
                max(line["bbox"][3] for line in header_axis),
            ]
            or bbox[0] < header["header_bbox"][0]
            or bbox[2] > header["header_bbox"][2]
            or bbox[1] < header["header_bbox"][3]
            or header["header_bbox"][2] > geometry["first_financial_lane_left_boundary"]
        ):
            raise _error("printed note-reference exact header proof drifted")
        normalized_header_channels = [
            (
                normalize_vietnamese_anchor_v1(line["vietocr_text"]),
                normalize_vietnamese_anchor_v1(line["numeric_raw_prediction"]),
            )
            for line in header_axis
        ]
        if normalized_header_channels not in [
            [("thuyet minh", "thuyet minh")],
            [("thuyet", "thuyet"), ("minh", "minh")],
        ]:
            raise _error("printed note-reference header text is not exact")
        validated_header_crops = [
            _validate_printed_note_reference_crop_proof(proof) for proof in header_crops
        ]
        if any(
            not same_typed_json_v1(proof["source_line_record"], line)
            or proof["render_binding"]["physical_page"] != evidence["page_sequence"]
            or proof["render_binding"]["render_id"] != candidate_crop["render_binding"]["render_id"]
            or proof["render_binding"]["document_ordinal"]
            != candidate_crop["render_binding"]["document_ordinal"]
            or not same_typed_json_v1(
                proof["render_binding"]["render_ref"],
                candidate_crop["render_binding"]["render_ref"],
            )
            for proof, line in zip(validated_header_crops, header_axis, strict=True)
        ):
            raise _error("printed note-reference header pixels or render binding drifted")

        note_axis = evidence["note_reference_axis"]
        if (
            type(note_axis) is not list
            or len(note_axis) != geometry["qualifying_note_reference_row_count"]
            or note_axis
            != sorted(
                note_axis,
                key=lambda row: (
                    row.get("source_line_record", {}).get("line_ordinal", -1),
                    row.get("note_value", -1),
                ),
            )
        ):
            raise _error("printed note-reference complete row axis drifted")
        note_values = []
        note_sample_ids = []
        candidate_rows = []
        all_financial_sample_ids = []
        horizontal_tolerance = max(
            geometry["body_text_scale"],
            (header["header_bbox"][2] - header["header_bbox"][0]) / 4,
        )
        for note_row in note_axis:
            note_line = note_row.get("source_line_record") if type(note_row) is dict else None
            financial_axis = note_row.get("financial_line_axis") if type(note_row) is dict else None
            label_axis = note_row.get("label_line_axis") if type(note_row) is dict else None
            if (
                type(note_row) is not dict
                or set(note_row) != _PRINTED_NOTE_REFERENCE_AXIS_V3_FIELDS
                or type(note_line) is not dict
                or type(note_row["note_value"]) is not int
                or not same_typed_json_v1(
                    _validate_extreme_margin_line_record(note_line), note_line
                )
                or _printed_note_reference_exact_integer_v3(
                    {
                        "numeric_recognition": {
                            "raw_prediction": note_line["numeric_raw_prediction"]
                        },
                        "vietocr_text": note_line["vietocr_text"],
                    }
                )
                != note_row["note_value"]
                or note_line["bbox"][0] < header["header_bbox"][0]
                or note_line["bbox"][2] > header["header_bbox"][2]
                or note_line["bbox"][1] < header["header_bbox"][3]
                or note_line["bbox"][2] > geometry["first_financial_lane_left_boundary"]
                or 2 * (note_line["bbox"][2] - note_line["bbox"][0])
                > header["header_bbox"][2] - header["header_bbox"][0]
                or abs(
                    note_line["bbox"][0] + note_line["bbox"][2] - geometry["candidate_center_twice"]
                )
                > 2 * horizontal_tolerance
                or type(financial_axis) is not list
                or len(financial_axis) != len(grid["column_centers"])
                or type(label_axis) is not list
                or not label_axis
            ):
                raise _error("printed note-reference row geometry or source drifted")
            note_crop = _validate_printed_note_reference_crop_proof(note_row["note_crop_proof"])
            if (
                not same_typed_json_v1(note_crop["source_line_record"], note_line)
                or note_crop["render_binding"]["physical_page"] != evidence["page_sequence"]
                or note_crop["render_binding"]["render_id"]
                != candidate_crop["render_binding"]["render_id"]
                or note_crop["render_binding"]["document_ordinal"]
                != candidate_crop["render_binding"]["document_ordinal"]
                or not same_typed_json_v1(
                    note_crop["render_binding"]["render_ref"],
                    candidate_crop["render_binding"]["render_ref"],
                )
            ):
                raise _error("printed note-reference peer pixel binding drifted")
            for column_ordinal, item in enumerate(financial_axis):
                line = item.get("source_line_record") if type(item) is dict else None
                parsed = (
                    row_v1.parse_visible_financial_numeric_token_v1(
                        line.get("numeric_raw_prediction", "")
                    )
                    if type(line) is dict
                    else {"classification": None}
                )
                if (
                    type(item) is not dict
                    or set(item) != _PRINTED_NOTE_REFERENCE_FINANCIAL_LINE_FIELDS
                    or item["column_ordinal"] != column_ordinal
                    or type(line) is not dict
                    or not same_typed_json_v1(_validate_extreme_margin_line_record(line), line)
                    or parsed["classification"]
                    not in _EXTREME_MARGIN_ADMITTED_NUMERIC_CLASSIFICATIONS
                    or not _printed_note_reference_same_row_v3(line, note_line)
                    or line["bbox"][0] < geometry["first_financial_lane_left_boundary"]
                    or line["bbox"][0] <= note_line["bbox"][2]
                    or abs(
                        (line["bbox"][0] + line["bbox"][2]) / 2
                        - grid["column_centers"][column_ordinal]
                    )
                    > geometry["lane_tolerance"]
                ):
                    raise _error("printed note-reference complete financial lane axis drifted")
                all_financial_sample_ids.append(line["sample_id"])
            for line in label_axis:
                if (
                    not same_typed_json_v1(_validate_extreme_margin_line_record(line), line)
                    or not _extreme_margin_peer_surfaces_are_nonnumeric(line)
                    or not _printed_note_reference_same_row_v3(line, note_line)
                    or line["bbox"][2] > note_line["bbox"][0]
                ):
                    raise _error("printed note-reference same-row label axis drifted")
            note_values.append(note_row["note_value"])
            note_sample_ids.append(note_line["sample_id"])
            if note_line["sample_id"] == evidence["sample_id"]:
                candidate_rows.append(note_row)
        if (
            len(note_values) != len(set(note_values))
            or len(note_sample_ids) != len(set(note_sample_ids))
            or len(all_financial_sample_ids) != len(set(all_financial_sample_ids))
            or len(candidate_rows) != 1
            or geometry["candidate_note_value"] - 1 not in note_values
            or geometry["candidate_note_value"] + 1 not in note_values
            or not any(
                row["source_line_record"]["line_ordinal"] < source["line_ordinal"]
                for row in note_axis
            )
            or not any(
                row["source_line_record"]["line_ordinal"] > source["line_ordinal"]
                for row in note_axis
            )
            or not same_typed_json_v1(
                candidate_rows[0]["note_crop_proof"], evidence["candidate_crop_proof"]
            )
        ):
            raise _error("printed note-reference peer uniqueness or candidate binding drifted")

        semantic = evidence["semantic_row_binding"]
        semantic_source = semantic.get("source_record") if type(semantic) is dict else None
        label_source_axis = (
            semantic.get("label_source_line_axis") if type(semantic) is dict else None
        )
        matching_axis_row = (
            row_by_occurrence.get(semantic.get("occurrence_id")) if type(semantic) is dict else None
        )
        if (
            type(semantic) is not dict
            or set(semantic) != _PRINTED_NOTE_REFERENCE_SEMANTIC_ROW_V3_FIELDS
            or semantic["status"] != _PRINTED_NOTE_REFERENCE_SEMANTIC_ROW_STATUS
            or semantic["row_axis_id"] != axis["row_axis_id"]
            or type(semantic["occurrence_id"]) is not str
            or type(semantic["role"]) is not str
            or type(semantic_source) is not dict
            or type(matching_axis_row) is not dict
            or not same_typed_json_v1(semantic_source, matching_axis_row)
            or semantic_source.get("role") != semantic["role"]
            or semantic_source.get("status") != "VISIBLE_VALUE_LANES_BOUND"
            or semantic_source.get("missing_column_ordinals") != []
            or semantic_source.get("label_match", {}).get("match_kind")
            not in {
                "EXACT_ACCENTLESS_ALIAS",
                "EXACT_ACCENTLESS_ALIAS_AFTER_ENUMERATION_PREFIX",
            }
            or type(label_source_axis) is not list
            or not label_source_axis
            or any(
                not same_typed_json_v1(_validate_extreme_margin_line_record(line), line)
                for line in label_source_axis
            )
            or semantic["label_source_line_axis_sha256"]
            != canonical_json_sha256_v1(label_source_axis)
            or normalize_vietnamese_anchor_v1(
                " ".join(line["vietocr_text"] for line in label_source_axis)
            )
            != semantic_source["label_match"].get("normalized_surface")
            or any(line["bbox"][2] >= bbox[0] for line in label_source_axis)
        ):
            raise _error("printed note-reference exact semantic row binding drifted")
        same_row_semantic_labels = [
            {
                "bbox": canonical_clone_v1(line["bbox"]),
                "line_ordinal": line["line_ordinal"],
                "numeric_raw_prediction": line["numeric_raw_prediction"],
                "vietocr_text": line["vietocr_text"],
            }
            for line in label_source_axis
            if _printed_note_reference_same_row_v3(line, candidate_line)
        ]
        candidate_financial_records = [
            item["source_line_record"] for item in candidate_rows[0]["financial_line_axis"]
        ]
        semantic_value_records = []
        for value in sorted(semantic_source["values"], key=lambda item: item["column_ordinal"]):
            matching = [
                line
                for line in candidate_financial_records
                if line["sample_id"] == value["sample_id"]
                and line["bbox"] == value["bbox"]
                and line["line_ordinal"] == value["line_ordinal"]
                and line["crop_ref"] == value["crop_ref"]
                and line["numeric_raw_prediction"] == value["raw_prediction"]
                and line["numeric_reader_score"] == value["reader_score"]
            ]
            if len(matching) != 1:
                semantic_value_records = []
                break
            semantic_value_records.append(matching[0])
        if (
            same_row_semantic_labels != cluster["same_row_label_evidence"]
            or semantic["candidate_same_row_label_axis_sha256"]
            != canonical_json_sha256_v1(same_row_semantic_labels)
            or semantic_value_records != candidate_financial_records
            or semantic["candidate_financial_line_axis_sha256"]
            != canonical_json_sha256_v1(candidate_financial_records)
        ):
            raise _error("printed note-reference label fragment or financial row binding drifted")

        expected_final = canonical_clone_v1(source)
        expected_final["owner_kind"] = _EXTREME_MARGIN_FURNITURE_OWNER_KIND
        expected_final["owner_id"] = evidence_id
        if not same_typed_json_v1(universe_by_sample.get(evidence["sample_id"]), expected_final):
            raise _error("printed note-reference furniture universe owner drifted")
        evidence_ids.append(evidence_id)
        sample_ids.append(evidence["sample_id"])
    if len(evidence_ids) != len(set(evidence_ids)) or len(sample_ids) != len(set(sample_ids)):
        raise _error("authenticated printed note-reference furniture ownership repeats")
    return set(sample_ids)


def _validate_printed_note_reference_furniture_evidence_axis_v4(
    evidence_axis: Any,
    *,
    universe_by_sample: Mapping[str, Mapping[str, Any]],
    axis: Mapping[str, Any],
    topology_candidates_id: str | None,
) -> set[str]:
    grid_by_page = {grid["page_sequence"]: grid for grid in axis["column_grids"]}
    row_by_occurrence = {row["label_match"].get("occurrence_id"): row for row in axis["rows"]}
    evidence_ids = []
    sample_ids = []
    for evidence in evidence_axis:
        if (
            type(evidence) is not dict
            or set(evidence) != _PRINTED_NOTE_REFERENCE_FURNITURE_V4_FIELDS
            or evidence.get("status") != _PRINTED_NOTE_REFERENCE_FURNITURE_V4_STATUS
            or type(evidence.get("evidence_id")) is not str
            or type(evidence.get("snapshot_id")) is not str
            or not evidence["snapshot_id"].startswith("ffdesv1:selected:")
            or type(evidence.get("document_pages_sha256")) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", evidence["document_pages_sha256"])
            or type(evidence.get("page_sequence")) is not int
            or evidence["page_sequence"] <= 0
            or type(evidence.get("sample_id")) is not str
            or not evidence["sample_id"]
            or evidence.get("topology_candidates_id") != topology_candidates_id
        ):
            raise _error("authenticated printed note-reference furniture evidence drifted")
        material = canonical_clone_v1(evidence)
        evidence_id = material.pop("evidence_id")
        if evidence_id != "aforav2:printed-note-reference-v4:" + canonical_json_sha256_v1(material):
            raise _error("authenticated printed note-reference furniture identity drifted")
        cluster = evidence["original_cluster"]
        source = evidence["source_record"]
        if (
            type(cluster) is not dict
            or set(cluster) != _INTERNAL_UNASSIGNED_CLUSTER_FIELDS
            or cluster.get("status") != _OFF_LANE_NUMERIC_CLUSTER_STATUS
            or cluster.get("page_sequence") != evidence["page_sequence"]
            or cluster.get("sample_ids") != [evidence["sample_id"]]
            or cluster.get("label_lane_status") != _LABELED_LABEL_LANE_STATUS
            or not cluster.get("same_row_label_evidence")
            or type(source) is not dict
        ):
            raise _error("printed note-reference original labeled singleton cluster drifted")
        _validate_numeric_sample_record(source)
        if (
            source["sample_id"] != evidence["sample_id"]
            or source["page_sequence"] != evidence["page_sequence"]
            or source["parsed_token"]["classification"] != "SIGNED_NUMBER"
            or source["owner_kind"] != "SOURCE_ONLY_INTERNAL_CLUSTER"
            or source["owner_id"] != cluster["cluster_id"]
        ):
            raise _error("printed note-reference original numeric owner drifted")
        cluster_material = canonical_clone_v1(cluster)
        cluster_id = cluster_material.pop("cluster_id", None)
        if cluster_id != "aforav2:unassigned:" + canonical_json_sha256_v1(cluster_material):
            raise _error("printed note-reference original cluster identity drifted")
        _validate_inspected_label_band(cluster, {evidence["sample_id"]: source})
        if (
            cluster["inspected_label_band"]["document_pages_sha256"]
            != evidence["document_pages_sha256"]
            or cluster["inspected_label_band"]["page_sequence"] != evidence["page_sequence"]
        ):
            raise _error("printed note-reference cluster document binding drifted")

        geometry = evidence["geometry"]
        grid = grid_by_page.get(evidence["page_sequence"])
        bbox = source["bbox"]
        if (
            type(geometry) is not dict
            or set(geometry) != _PRINTED_NOTE_REFERENCE_GEOMETRY_V4_FIELDS
            or type(grid) is not dict
            or len(grid["column_centers"]) < 2
            or type(geometry["body_text_scale"]) is not float
            or not math.isfinite(geometry["body_text_scale"])
            or geometry["body_text_scale"] <= 0
            or geometry["candidate_bbox"] != bbox
            or geometry["candidate_center_twice"] != bbox[0] + bbox[2]
            or type(geometry["candidate_note_reference"]) is not str
            or _printed_note_reference_exact_surface(
                {
                    "numeric_recognition": {"raw_prediction": geometry["candidate_note_reference"]},
                    "vietocr_text": geometry["candidate_note_reference"],
                }
            )
            != geometry["candidate_note_reference"]
            or type(geometry["page_width"]) is not int
            or geometry["page_width"] <= 0
            or bbox[2] > geometry["page_width"]
            or type(geometry["lane_tolerance"]) is not float
            or not math.isfinite(geometry["lane_tolerance"])
            or geometry["lane_tolerance"] <= 0
            or type(geometry["lane_centers_quads"]) is not list
            or any(not float(center * 4).is_integer() for center in grid["column_centers"])
            or geometry["lane_centers_quads"]
            != [int(center * 4) for center in grid["column_centers"]]
            or geometry["first_financial_lane_left_boundary"]
            != math.floor(grid["column_centers"][0] - geometry["lane_tolerance"])
            or bbox[2] > geometry["first_financial_lane_left_boundary"]
            or source["column_ordinal"]
            != min(
                range(len(grid["column_centers"])),
                key=lambda index: abs(
                    geometry["candidate_center_twice"] - geometry["lane_centers_quads"][index] // 2
                ),
            )
            or source["column_center"] != grid["column_centers"][source["column_ordinal"]]
            or abs(
                geometry["candidate_center_twice"] / 2
                - grid["column_centers"][source["column_ordinal"]]
            )
            <= geometry["lane_tolerance"]
            or type(geometry["qualifying_note_reference_row_count"]) is not int
            or geometry["qualifying_note_reference_row_count"] < 3
        ):
            raise _error("printed note-reference geometry or column exclusion drifted")

        candidate_crop = _validate_printed_note_reference_crop_proof(
            evidence["candidate_crop_proof"]
        )
        candidate_line = candidate_crop["source_line_record"]
        candidate_reference = _printed_note_reference_exact_surface(
            {
                "numeric_recognition": {"raw_prediction": candidate_line["numeric_raw_prediction"]},
                "vietocr_text": candidate_line["vietocr_text"],
            }
        )
        if (
            candidate_reference != geometry["candidate_note_reference"]
            or candidate_line["sample_id"] != source["sample_id"]
            or candidate_line["bbox"] != source["bbox"]
            or candidate_line["line_ordinal"] != source["line_ordinal"]
            or candidate_line["crop_ref"] != source["crop_ref"]
            or candidate_line["numeric_raw_prediction"] != source["raw_prediction"]
            or candidate_line["numeric_reader_score"] != source["reader_score"]
            or candidate_crop["render_binding"]["physical_page"] != evidence["page_sequence"]
            or candidate_crop["render_binding"]["render_ref"]["pixel_width"]
            != geometry["page_width"]
        ):
            raise _error("printed note-reference candidate source or pixel binding drifted")

        header = evidence["header_proof"]
        header_axis = header.get("source_line_axis") if type(header) is dict else None
        header_crops = header.get("crop_proofs") if type(header) is dict else None
        if (
            type(header) is not dict
            or set(header) != _PRINTED_NOTE_REFERENCE_HEADER_FIELDS
            or header["status"] != _PRINTED_NOTE_REFERENCE_HEADER_STATUS
            or header["normalized_surface"] != "thuyet minh"
            or type(header_axis) is not list
            or len(header_axis) not in {1, 2}
            or any(
                not same_typed_json_v1(_validate_extreme_margin_line_record(line), line)
                for line in header_axis
            )
            or header["source_line_axis_sha256"] != canonical_json_sha256_v1(header_axis)
            or type(header_crops) is not list
            or len(header_crops) != len(header_axis)
            or header["header_bbox"] != geometry["header_bbox"]
            or header["header_bbox"]
            != [
                min(line["bbox"][0] for line in header_axis),
                min(line["bbox"][1] for line in header_axis),
                max(line["bbox"][2] for line in header_axis),
                max(line["bbox"][3] for line in header_axis),
            ]
            or bbox[0] < header["header_bbox"][0]
            or bbox[2] > header["header_bbox"][2]
            or bbox[1] < header["header_bbox"][3]
            or header["header_bbox"][2] > geometry["first_financial_lane_left_boundary"]
        ):
            raise _error("printed note-reference exact header proof drifted")
        normalized_header_channels = [
            (
                normalize_vietnamese_anchor_v1(line["vietocr_text"]),
                normalize_vietnamese_anchor_v1(line["numeric_raw_prediction"]),
            )
            for line in header_axis
        ]
        if normalized_header_channels not in [
            [("thuyet minh", "thuyet minh")],
            [("thuyet", "thuyet"), ("minh", "minh")],
        ]:
            raise _error("printed note-reference header text is not exact")
        validated_header_crops = [
            _validate_printed_note_reference_crop_proof(proof) for proof in header_crops
        ]
        if any(
            not same_typed_json_v1(proof["source_line_record"], line)
            or proof["render_binding"]["physical_page"] != evidence["page_sequence"]
            or proof["render_binding"]["render_id"] != candidate_crop["render_binding"]["render_id"]
            or proof["render_binding"]["document_ordinal"]
            != candidate_crop["render_binding"]["document_ordinal"]
            or not same_typed_json_v1(
                proof["render_binding"]["render_ref"],
                candidate_crop["render_binding"]["render_ref"],
            )
            for proof, line in zip(validated_header_crops, header_axis, strict=True)
        ):
            raise _error("printed note-reference header pixels or render binding drifted")

        note_axis = evidence["note_reference_axis"]
        if (
            type(note_axis) is not list
            or len(note_axis) != geometry["qualifying_note_reference_row_count"]
            or note_axis
            != sorted(
                note_axis,
                key=lambda row: (
                    row.get("source_line_record", {}).get("line_ordinal", -1),
                    row.get("note_reference", ""),
                ),
            )
        ):
            raise _error("printed note-reference complete row axis drifted")
        note_references = []
        note_sample_ids = []
        candidate_rows = []
        all_financial_sample_ids = []
        horizontal_tolerance = max(
            geometry["body_text_scale"],
            (header["header_bbox"][2] - header["header_bbox"][0]) / 4,
        )
        for note_row in note_axis:
            note_line = note_row.get("source_line_record") if type(note_row) is dict else None
            financial_axis = note_row.get("financial_line_axis") if type(note_row) is dict else None
            label_axis = note_row.get("label_line_axis") if type(note_row) is dict else None
            if (
                type(note_row) is not dict
                or set(note_row) != _PRINTED_NOTE_REFERENCE_AXIS_V4_FIELDS
                or type(note_line) is not dict
                or type(note_row["note_reference"]) is not str
                or not same_typed_json_v1(
                    _validate_extreme_margin_line_record(note_line), note_line
                )
                or _printed_note_reference_exact_surface(
                    {
                        "numeric_recognition": {
                            "raw_prediction": note_line["numeric_raw_prediction"]
                        },
                        "vietocr_text": note_line["vietocr_text"],
                    }
                )
                != note_row["note_reference"]
                or note_line["bbox"][0] < header["header_bbox"][0]
                or note_line["bbox"][2] > header["header_bbox"][2]
                or note_line["bbox"][1] < header["header_bbox"][3]
                or note_line["bbox"][2] > geometry["first_financial_lane_left_boundary"]
                or note_line["bbox"][2] - note_line["bbox"][0]
                > header["header_bbox"][2] - header["header_bbox"][0]
                or abs(
                    note_line["bbox"][0] + note_line["bbox"][2] - geometry["candidate_center_twice"]
                )
                > 2 * horizontal_tolerance
                or type(financial_axis) is not list
                or len(financial_axis) != len(grid["column_centers"])
                or type(label_axis) is not list
                or not label_axis
            ):
                raise _error("printed note-reference row geometry or source drifted")
            note_crop = _validate_printed_note_reference_crop_proof(note_row["note_crop_proof"])
            if (
                not same_typed_json_v1(note_crop["source_line_record"], note_line)
                or note_crop["render_binding"]["physical_page"] != evidence["page_sequence"]
                or note_crop["render_binding"]["render_id"]
                != candidate_crop["render_binding"]["render_id"]
                or note_crop["render_binding"]["document_ordinal"]
                != candidate_crop["render_binding"]["document_ordinal"]
                or not same_typed_json_v1(
                    note_crop["render_binding"]["render_ref"],
                    candidate_crop["render_binding"]["render_ref"],
                )
            ):
                raise _error("printed note-reference peer pixel binding drifted")
            for column_ordinal, item in enumerate(financial_axis):
                line = item.get("source_line_record") if type(item) is dict else None
                parsed = (
                    row_v1.parse_visible_financial_numeric_token_v1(
                        line.get("numeric_raw_prediction", "")
                    )
                    if type(line) is dict
                    else {"classification": None}
                )
                if (
                    type(item) is not dict
                    or set(item) != _PRINTED_NOTE_REFERENCE_FINANCIAL_LINE_FIELDS
                    or item["column_ordinal"] != column_ordinal
                    or type(line) is not dict
                    or not same_typed_json_v1(_validate_extreme_margin_line_record(line), line)
                    or parsed["classification"]
                    not in _EXTREME_MARGIN_ADMITTED_NUMERIC_CLASSIFICATIONS
                    or not _printed_note_reference_same_row(
                        line,
                        note_line,
                        body_text_scale=geometry["body_text_scale"],
                    )
                    or (line["bbox"][0] + line["bbox"][2]) / 2
                    < geometry["first_financial_lane_left_boundary"]
                    or line["bbox"][0] <= note_line["bbox"][2]
                    or abs(
                        (line["bbox"][0] + line["bbox"][2]) / 2
                        - grid["column_centers"][column_ordinal]
                    )
                    > geometry["lane_tolerance"]
                ):
                    raise _error("printed note-reference complete financial lane axis drifted")
                all_financial_sample_ids.append(line["sample_id"])
            for line in label_axis:
                if (
                    not same_typed_json_v1(_validate_extreme_margin_line_record(line), line)
                    or not _extreme_margin_peer_surfaces_are_nonnumeric(line)
                    or not _printed_note_reference_same_row(
                        line,
                        note_line,
                        body_text_scale=geometry["body_text_scale"],
                    )
                    or line["bbox"][2] > note_line["bbox"][0]
                ):
                    raise _error("printed note-reference same-row label axis drifted")
            note_references.append(note_row["note_reference"])
            note_sample_ids.append(note_line["sample_id"])
            if note_line["sample_id"] == evidence["sample_id"]:
                candidate_rows.append(note_row)
        if (
            len(note_references) != len(set(note_references))
            or len(note_sample_ids) != len(set(note_sample_ids))
            or len(all_financial_sample_ids) != len(set(all_financial_sample_ids))
            or len(candidate_rows) != 1
            or not _printed_note_reference_has_local_peer(
                geometry["candidate_note_reference"], note_references
            )
            or not any(
                row["source_line_record"]["line_ordinal"] < source["line_ordinal"]
                for row in note_axis
            )
            or not any(
                row["source_line_record"]["line_ordinal"] > source["line_ordinal"]
                for row in note_axis
            )
            or not same_typed_json_v1(
                candidate_rows[0]["note_crop_proof"], evidence["candidate_crop_proof"]
            )
        ):
            raise _error("printed note-reference peer uniqueness or candidate binding drifted")

        semantic = evidence["semantic_row_binding"]
        semantic_source = semantic.get("source_record") if type(semantic) is dict else None
        label_source_axis = (
            semantic.get("label_source_line_axis") if type(semantic) is dict else None
        )
        matching_axis_row = (
            row_by_occurrence.get(semantic.get("occurrence_id")) if type(semantic) is dict else None
        )
        binding_kind = semantic.get("binding_kind") if type(semantic) is dict else None
        selected_parent = axis.get("topology_region", {}).get("parent_match")
        role_binding_valid = (
            binding_kind == _PRINTED_NOTE_REFERENCE_ROLE_BINDING_KIND
            and semantic.get("status") == _PRINTED_NOTE_REFERENCE_SEMANTIC_ROW_STATUS
            and type(matching_axis_row) is dict
            and same_typed_json_v1(semantic_source, matching_axis_row)
            and semantic_source.get("role") == semantic.get("role")
            and semantic_source.get("status") == "VISIBLE_VALUE_LANES_BOUND"
            and semantic_source.get("missing_column_ordinals") == []
            and semantic_source.get("label_match", {}).get("match_kind")
            in {
                "EXACT_ACCENTLESS_ALIAS",
                "EXACT_ACCENTLESS_ALIAS_AFTER_ENUMERATION_PREFIX",
            }
        )
        parent_binding_valid = (
            binding_kind == _PRINTED_NOTE_REFERENCE_PARENT_BINDING_KIND
            and semantic.get("status") == _PRINTED_NOTE_REFERENCE_PARENT_STATUS
            and semantic.get("role") == "FAMILY_PARENT"
            and type(selected_parent) is dict
            and same_typed_json_v1(semantic_source, selected_parent)
            and semantic.get("occurrence_id")
            == "aforav2:parent-note-row:" + canonical_json_sha256_v1(selected_parent)
            and axis.get("topology_region", {}).get("parent_resolution") == "EXPLICIT_PARENT"
        )
        if (
            type(semantic) is not dict
            or set(semantic) != _PRINTED_NOTE_REFERENCE_SEMANTIC_ROW_V4_FIELDS
            or semantic["row_axis_id"] != axis["row_axis_id"]
            or type(semantic["occurrence_id"]) is not str
            or type(semantic["role"]) is not str
            or type(semantic_source) is not dict
            or not (role_binding_valid or parent_binding_valid)
            or type(label_source_axis) is not list
            or not label_source_axis
            or any(
                not same_typed_json_v1(_validate_extreme_margin_line_record(line), line)
                for line in label_source_axis
            )
            or semantic["label_source_line_axis_sha256"]
            != canonical_json_sha256_v1(label_source_axis)
            or normalize_vietnamese_anchor_v1(
                " ".join(line["vietocr_text"] for line in label_source_axis)
            )
            != (
                semantic_source["label_match"].get("normalized_surface")
                if role_binding_valid
                else semantic_source.get("normalized_surface")
            )
            or any(line["bbox"][2] >= bbox[0] for line in label_source_axis)
        ):
            raise _error("printed note-reference exact semantic row binding drifted")
        candidate_label_ids = {line["sample_id"] for line in candidate_rows[0]["label_line_axis"]}
        same_row_semantic_labels = [
            {
                "bbox": canonical_clone_v1(line["bbox"]),
                "line_ordinal": line["line_ordinal"],
                "numeric_raw_prediction": line["numeric_raw_prediction"],
                "vietocr_text": line["vietocr_text"],
            }
            for line in label_source_axis
            if line["sample_id"] in candidate_label_ids
            and _printed_note_reference_same_row(
                line,
                candidate_line,
                body_text_scale=geometry["body_text_scale"],
            )
        ]
        candidate_financial_records = [
            item["source_line_record"] for item in candidate_rows[0]["financial_line_axis"]
        ]
        semantic_value_records = candidate_financial_records if parent_binding_valid else []
        if role_binding_valid:
            for value in sorted(semantic_source["values"], key=lambda item: item["column_ordinal"]):
                matching = [
                    line
                    for line in candidate_financial_records
                    if line["sample_id"] == value["sample_id"]
                    and line["bbox"] == value["bbox"]
                    and line["line_ordinal"] == value["line_ordinal"]
                    and line["crop_ref"] == value["crop_ref"]
                    and line["numeric_raw_prediction"] == value["raw_prediction"]
                    and line["numeric_reader_score"] == value["reader_score"]
                ]
                if len(matching) != 1:
                    semantic_value_records = []
                    break
                semantic_value_records.append(matching[0])
        if (
            same_row_semantic_labels != cluster["same_row_label_evidence"]
            or semantic["candidate_same_row_label_axis_sha256"]
            != canonical_json_sha256_v1(same_row_semantic_labels)
            or semantic_value_records != candidate_financial_records
            or semantic["candidate_financial_line_axis_sha256"]
            != canonical_json_sha256_v1(candidate_financial_records)
        ):
            raise _error("printed note-reference label fragment or financial row binding drifted")

        expected_final = canonical_clone_v1(source)
        expected_final["owner_kind"] = _EXTREME_MARGIN_FURNITURE_OWNER_KIND
        expected_final["owner_id"] = evidence_id
        if not same_typed_json_v1(universe_by_sample.get(evidence["sample_id"]), expected_final):
            raise _error("printed note-reference furniture universe owner drifted")
        evidence_ids.append(evidence_id)
        sample_ids.append(evidence["sample_id"])
    if len(evidence_ids) != len(set(evidence_ids)) or len(sample_ids) != len(set(sample_ids)):
        raise _error("authenticated printed note-reference furniture ownership repeats")
    return set(sample_ids)


def _validate_extreme_margin_furniture_evidence_axis(
    evidence_axis: Any,
    *,
    universe_by_sample: Mapping[str, Mapping[str, Any]],
    axis: Mapping[str, Any],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
    topology_candidates_id: str | None,
) -> set[str]:
    if type(evidence_axis) is not list or len(evidence_axis) > _MAX_ROLE_OCCURRENCES:
        raise _error("authenticated extreme-margin furniture evidence axis drifted")
    v1 = [
        evidence
        for evidence in evidence_axis
        if type(evidence) is dict and evidence.get("status") == _EXTREME_MARGIN_FURNITURE_STATUS
    ]
    v2 = [
        evidence
        for evidence in evidence_axis
        if type(evidence) is dict and evidence.get("status") == _EXTREME_MARGIN_FURNITURE_V2_STATUS
    ]
    vertical_stamp_v4 = [
        evidence
        for evidence in evidence_axis
        if type(evidence) is dict
        and evidence.get("status") == _EXTREME_MARGIN_VERTICAL_STAMP_V4_STATUS
    ]
    decoration_v3 = [
        evidence
        for evidence in evidence_axis
        if type(evidence) is dict
        and evidence.get("status") == _EXTREME_MARGIN_NONNUMERIC_DECORATION_V3_STATUS
    ]
    note_v3 = [
        evidence
        for evidence in evidence_axis
        if type(evidence) is dict
        and evidence.get("status") == _PRINTED_NOTE_REFERENCE_FURNITURE_V3_STATUS
    ]
    note_v4 = [
        evidence
        for evidence in evidence_axis
        if type(evidence) is dict
        and evidence.get("status") == _PRINTED_NOTE_REFERENCE_FURNITURE_V4_STATUS
    ]
    if len(v1) + len(v2) + len(vertical_stamp_v4) + len(decoration_v3) + len(note_v3) + len(
        note_v4
    ) != len(evidence_axis):
        raise _error("authenticated extreme-margin furniture evidence version drifted")
    v1_samples = _validate_extreme_margin_furniture_evidence_axis_v1(
        v1,
        universe_by_sample=universe_by_sample,
        axis=axis,
        topology_candidates_id=topology_candidates_id,
    )
    v2_samples = _validate_extreme_margin_furniture_evidence_axis_v2(
        v2,
        universe_by_sample=universe_by_sample,
        axis=axis,
        topology_candidates_id=topology_candidates_id,
    )
    vertical_stamp_v4_samples = _validate_extreme_margin_vertical_stamp_furniture_axis_v4(
        vertical_stamp_v4,
        universe_by_sample=universe_by_sample,
        axis=axis,
        topology_candidates_id=topology_candidates_id,
    )
    _validate_extreme_margin_nonnumeric_decoration_axis_v3(
        decoration_v3,
        universe_by_sample=universe_by_sample,
        axis=axis,
        occurrence_by_id=occurrence_by_id,
        topology_candidates_id=topology_candidates_id,
    )
    note_v3_samples = _validate_printed_note_reference_furniture_evidence_axis_v3(
        note_v3,
        universe_by_sample=universe_by_sample,
        axis=axis,
        topology_candidates_id=topology_candidates_id,
    )
    note_v4_samples = _validate_printed_note_reference_furniture_evidence_axis_v4(
        note_v4,
        universe_by_sample=universe_by_sample,
        axis=axis,
        topology_candidates_id=topology_candidates_id,
    )
    owned_sample_axes = [
        v1_samples,
        v2_samples,
        vertical_stamp_v4_samples,
        note_v3_samples,
        note_v4_samples,
    ]
    if any(
        left & right
        for index, left in enumerate(owned_sample_axes)
        for right in owned_sample_axes[index + 1 :]
    ) or len({item["evidence_id"] for item in evidence_axis}) != len(evidence_axis):
        raise _error("authenticated extreme-margin furniture cross-version ownership repeats")
    return set().union(*owned_sample_axes)


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
        occurrence_by_id=occurrence_by_id,
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


def _validate_unique_dash_speck_evidence_axis(
    evidence_axis: Any,
    *,
    axis: Mapping[str, Any],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
    topology_candidates_id: str | None,
    topology_scan_id: str,
) -> None:
    """Bind every receipt back to one exact unresolved V1 projection and row."""

    if type(evidence_axis) is not list or len(evidence_axis) > _MAX_EXISTING_DASH_CELLS:
        raise _error("authenticated unique-dash/speck evidence axis drifted")
    receipts_by_occurrence: dict[str, list[dict[str, Any]]] = {}
    evidence_ids: list[str] = []
    region_ids: list[str] = []
    occurrence_lane_keys: list[tuple[str, int]] = []
    rescue_by_region = {item["region_id"]: item for item in axis["visible_dash_rescues"]}
    row_by_occurrence = {row["label_match"].get("occurrence_id"): row for row in axis["rows"]}
    for raw in evidence_axis:
        try:
            receipt = speck_dash_v1._validate(raw)
        except speck_dash_v1.FamilyFirstAuthenticatedUniqueDashSpeckV1Error as exc:
            raise _error("authenticated unique-dash/speck receipt drifted") from exc
        binding = receipt["input_binding"]
        occurrence_binding = binding["occurrence_binding"]
        parent_binding = binding["parent_binding"]
        lane = binding["lane_binding"]
        occurrence = occurrence_by_id.get(occurrence_binding["occurrence_id"])
        parent = occurrence_by_id.get(parent_binding["occurrence_id"])
        row = row_by_occurrence.get(occurrence_binding["occurrence_id"])
        rescue = rescue_by_region.get(lane["region_id"])
        row_values = (
            [item for item in row["values"] if item["sample_id"] == lane["region_id"]]
            if type(row) is dict
            else []
        )
        crop_ref = receipt["original_dash_evidence"]["crop_ref"]
        expected_value = {
            "bbox": canonical_clone_v1(lane["recognition_raw_pixel_bbox"]),
            "column_center": lane["column_center"],
            "column_ordinal": lane["column_ordinal"],
            "crop_ref": {
                "path": f"authenticated-render-region/{lane['region_id']}.png",
                "sha256": crop_ref["sha256"],
                "size_bytes": crop_ref["size_bytes"],
            },
            "line_ordinal": occurrence_binding["source_line_index"],
            "page_sequence": occurrence_binding["page_sequence"],
            "parsed_token": row_v1.parse_visible_financial_numeric_token_v1("-"),
            "raw_prediction": "-",
            "reader_score": 1.0,
            "row_affinity": None,
            "sample_id": lane["region_id"],
        }
        if (
            topology_candidates_id is None
            or binding["topology_candidates_id"] != topology_candidates_id
            or binding["topology_scan_id"] != topology_scan_id
            or type(occurrence) is not dict
            or type(parent) is not dict
            or type(row) is not dict
            or not same_typed_json_v1(
                occurrence_binding,
                _unique_dash_occurrence_binding(occurrence["label_match"]),
            )
            or not same_typed_json_v1(
                parent_binding,
                _unique_dash_parent_binding(parent["label_match"]),
            )
            or occurrence["scope_owner_occurrence_id"] != parent["occurrence_id"]
            or occurrence["scope_owner_role"] != parent["role"]
            or occurrence["role"] != row["role"]
            or len(row_values) != 1
            or not same_typed_json_v1(row_values[0], expected_value)
            or lane["column_ordinal"] in row["missing_column_ordinals"]
            or type(rescue) is not dict
            or rescue["classification"] != "UNRESOLVED_NOT_ONE_DASH_GLYPH"
            or rescue["role"] != occurrence["role"]
            or rescue["page_sequence"] != occurrence_binding["page_sequence"]
            or rescue["column_ordinal"] != lane["column_ordinal"]
            or rescue["column_center"] != lane["column_center"]
            or rescue["proposed_raw_pixel_bbox"] != lane["proposed_raw_pixel_bbox"]
            or rescue["recognition_raw_pixel_bbox"] != lane["recognition_raw_pixel_bbox"]
            or not same_typed_json_v1(rescue["dash_evidence"], receipt["original_dash_evidence"])
        ):
            raise _error("authenticated unique-dash/speck occurrence/parent/lane binding drifted")
        evidence_ids.append(receipt["evidence_id"])
        region_ids.append(lane["region_id"])
        occurrence_lane_keys.append((occurrence_binding["occurrence_id"], lane["column_ordinal"]))
        receipts_by_occurrence.setdefault(occurrence_binding["occurrence_id"], []).append(receipt)
    if (
        len(evidence_ids) != len(set(evidence_ids))
        or len(region_ids) != len(set(region_ids))
        or len(occurrence_lane_keys) != len(set(occurrence_lane_keys))
    ):
        raise _error("authenticated unique-dash/speck ownership repeats")
    assigned_region_ids = {item["sample_id"] for row in axis["rows"] for item in row["values"]}
    unresolved_rescue_ids = {
        item["region_id"]
        for item in axis["visible_dash_rescues"]
        if item["classification"] == "UNRESOLVED_NOT_ONE_DASH_GLYPH"
    }
    if assigned_region_ids & unresolved_rescue_ids != set(region_ids):
        raise _error("unresolved V1 rescue assignment lacks exact unique-dash/speck ownership")
    for occurrence_id, receipts in receipts_by_occurrence.items():
        source = canonical_clone_v1(row_by_occurrence[occurrence_id])
        receipt_region_ids = {
            receipt["input_binding"]["lane_binding"]["region_id"] for receipt in receipts
        }
        receipt_lanes = {
            receipt["input_binding"]["lane_binding"]["column_ordinal"] for receipt in receipts
        }
        source["values"] = [
            item for item in source["values"] if item["sample_id"] not in receipt_region_ids
        ]
        source["missing_column_ordinals"] = sorted(
            [*source["missing_column_ordinals"], *receipt_lanes]
        )
        source["status"] = (
            "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL"
            if not source["values"]
            else "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
        )
        source_hashes = {receipt["input_binding"]["source_row_sha256"] for receipt in receipts}
        if source_hashes != {canonical_json_sha256_v1(source)}:
            raise _error("authenticated unique-dash/speck exact source row binding drifted")


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
        or type(value["authenticated_unique_dash_speck_evidence"]) is not list
        or len(value["authenticated_unique_dash_speck_evidence"]) > _MAX_EXISTING_DASH_CELLS
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
    occurrences_by_retrieval_id: dict[str, list[Mapping[str, Any]]] = {}
    for item in value["role_occurrences"]:
        occurrences_by_retrieval_id.setdefault(item["retrieval_occurrence_id"], []).append(item)
    universe_by_sample_id = {
        record.get("sample_id"): record
        for record in value["numeric_sample_universe"]
        if type(record) is dict and type(record.get("sample_id")) is str
    }
    for item in value["role_occurrences"]:
        receipt = item["source_scope_binding"]
        if (
            type(receipt) is not dict
            or receipt.get("binding_kind") != _RECURSIVE_PARENT_PROVISION_BINDING_KIND
        ):
            continue
        geometry = receipt["geometry"]
        equation = geometry["equation"]
        topology_region = axis["topology_region"]
        if receipt["interval"] != {
            "end_document_line_ordinal_exclusive": topology_region[
                "cluster_end_document_line_ordinal_exclusive"
            ],
            "start_document_line_ordinal": topology_region["cluster_start_document_line_ordinal"],
        }:
            raise _error("recursive parent equation selected root interval drifted")
        parent_occurrence_id = equation["parent_occurrence_id"]
        parent_occurrence_for_interval = occurrence_by_id.get(parent_occurrence_id)
        next_parent_boundary_key = None
        if type(parent_occurrence_for_interval) is dict:
            later_parent_boundary_keys = [
                _visual_match_key(candidate["label_match"])
                for candidate in value["role_occurrences"]
                if candidate["role"] in {"INTERBANK_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"}
                and candidate["occurrence_id"] != parent_occurrence_id
                and candidate["label_match"]["page_sequence"]
                == parent_occurrence_for_interval["label_match"]["page_sequence"]
                and _visual_match_key(candidate["label_match"])
                > _visual_match_key(parent_occurrence_for_interval["label_match"])
            ]
            next_parent_boundary_key = min(later_parent_boundary_keys, default=None)
        matching_specs = [
            spec
            for spec in _RECURSIVE_PARENT_PROVISION_BINDING_SPECS
            if spec["target_role"] == item["role"]
            and tuple(component["role"] for component in equation["component_frontier"])
            in spec["direct_component_role_alternatives"]
        ]
        if len(matching_specs) != 1:
            raise _error("recursive parent equation direct-frontier spec drifted")
        complete_frontier = _complete_recursive_parent_direct_frontier(
            value["role_occurrences"],
            value["row_axis"]["rows"],
            matching_specs[0],
            interval_end=next_parent_boundary_key,
            interval_start=(
                _visual_match_key(parent_occurrence_for_interval["label_match"])
                if type(parent_occurrence_for_interval) is dict
                else None
            ),
            page_sequence=item["label_match"]["page_sequence"],
            parent_occurrence_id=parent_occurrence_id,
            source_retrieval_occurrence_id=item["retrieval_occurrence_id"],
        )
        if complete_frontier is None or tuple(role for role, _row in complete_frontier) != tuple(
            component["role"] for component in equation["component_frontier"]
        ):
            raise _error("recursive parent equation direct frontier is incomplete or mixed")
        component_occurrences = []
        for component, expected_bbox in zip(
            equation["component_frontier"],
            geometry["ordered_source_label_bboxes"],
            strict=True,
        ):
            candidates = occurrences_by_retrieval_id.get(component["retrieval_occurrence_id"], [])
            if len(candidates) != 1:
                raise _error(
                    "recursive parent equation component is not one actual retrieval occurrence"
                )
            component_occurrence = candidates[0]
            component_row = row_by_occurrence.get(component_occurrence["occurrence_id"])
            component_receipt = (
                _direct_frontier_row_receipt(component_row) if type(component_row) is dict else None
            )
            component_key = _visual_match_key(component_occurrence["label_match"])
            component_is_in_exact_parent_interval = (
                component_occurrence["scope_owner_occurrence_id"] == parent_occurrence_id
                if equation["parent_role"] == "INTERBANK_DEPOSITS_AND_LOANS"
                else type(parent_occurrence_for_interval) is dict
                and _visual_match_key(parent_occurrence_for_interval["label_match"]) < component_key
                and (next_parent_boundary_key is None or component_key < next_parent_boundary_key)
            )
            if (
                component_occurrence["role"] != component["role"]
                or not component_is_in_exact_parent_interval
                or component_occurrence["label_match"].get("source_label_bbox") != expected_bbox
                or component_receipt is None
                or component_receipt["numbers"] != component["numbers"]
                or component_receipt["sample_ids"] != component["sample_ids"]
            ):
                raise _error(
                    "recursive parent equation component row or owner does not replay exactly"
                )
            component_occurrences.append(component_occurrence)
        target_components = [
            occurrence for occurrence in component_occurrences if occurrence["role"] == item["role"]
        ]
        if (
            len(target_components) != 1
            or target_components[0]["occurrence_id"] != item["occurrence_id"]
            or equation["source_retrieval_occurrence_id"] != item["retrieval_occurrence_id"]
            or item["scope_owner_occurrence_id"] != parent_occurrence_id
        ):
            raise _error("recursive parent equation source occurrence or owner drifted")
        result = equation["result"]
        result_occurrence = occurrence_by_id.get(result["occurrence_id"])
        result_row = (
            row_by_occurrence.get(result_occurrence["occurrence_id"])
            if type(result_occurrence) is dict
            else None
        )
        result_receipt = (
            _direct_frontier_row_receipt(result_row) if type(result_row) is dict else None
        )
        if result_receipt is None:
            result_records = [
                universe_by_sample_id.get(sample_id) for sample_id in result["sample_ids"]
            ]
            result_numbers = [
                _direct_frontier_number(record) if type(record) is dict else None
                for record in result_records
            ]
            if any(number is None for number in result_numbers):
                raise _error("recursive parent equation result samples are absent")
            result_receipt = {
                "numbers": result_numbers,
                "sample_ids": list(result["sample_ids"]),
            }
            if equation["parent_role"] in {
                "INTERBANK_DEPOSIT_GROUP",
                "INTERBANK_LOAN_GROUP",
            }:
                matching_clusters = [
                    cluster
                    for cluster in value["internal_unassigned_numeric_clusters"]
                    if cluster.get("sample_ids") == result["sample_ids"]
                    and _direct_frontier_internal_cluster_receipt(
                        cluster,
                        universe_by_sample_id,
                        expected_column_ordinals=list(range(len(result["numbers"]))),
                    )
                    == result_receipt
                ]
                if len(matching_clusters) != 1:
                    raise _error(
                        "recursive parent equation result is not one exact internal subtotal"
                    )
                cluster = matching_clusters[0]
                cluster_records = [
                    universe_by_sample_id[sample_id] for sample_id in cluster["sample_ids"]
                ]
                source_row = row_by_occurrence.get(item["occurrence_id"])
                if type(source_row) is not dict:
                    raise _error("recursive parent equation source row is absent")
                source_end = max(
                    [
                        *row_v1._match_source_line_indices(item["label_match"]),  # noqa: SLF001
                        *(value_record["line_ordinal"] for value_record in source_row["values"]),
                    ]
                )
                cluster_line_ordinals = sorted(record["line_ordinal"] for record in cluster_records)
                result_key = min(
                    (
                        record["page_sequence"],
                        record["bbox"][1] + record["bbox"][3],
                        2 * record["bbox"][0],
                        record["line_ordinal"],
                    )
                    for record in cluster_records
                )
                if (
                    cluster["page_sequence"] != item["label_match"]["page_sequence"]
                    or cluster_line_ordinals
                    != list(range(source_end + 1, source_end + 1 + len(cluster_records)))
                    or result_key <= _visual_match_key(item["label_match"])
                    or next_parent_boundary_key is not None
                    and result_key >= next_parent_boundary_key
                    or any(
                        candidate["occurrence_id"] != item["occurrence_id"]
                        and _visual_match_key(item["label_match"])
                        < _visual_match_key(candidate["label_match"])
                        < result_key
                        for candidate in value["role_occurrences"]
                    )
                ):
                    raise _error(
                        "recursive parent equation internal subtotal left its exact interval"
                    )
            elif {record.get("owner_kind") for record in result_records} == {"TRAILING_VALUE_ROW"}:
                matching_trailing_rows = [
                    trailing
                    for trailing in value["row_axis"]["trailing_value_rows"]
                    if _direct_frontier_trailing_row_receipt(trailing) == result_receipt
                ]
                if len(matching_trailing_rows) != 1:
                    raise _error("recursive root equation result is not one exact trailing row")
                trailing = matching_trailing_rows[0]
                source_row = row_by_occurrence.get(item["occurrence_id"])
                if type(source_row) is not dict:
                    raise _error("recursive root equation source row is absent")
                source_end = max(
                    [
                        *row_v1._match_source_line_indices(item["label_match"]),  # noqa: SLF001
                        *(value_record["line_ordinal"] for value_record in source_row["values"]),
                    ]
                )
                trailing_line_ordinals = sorted(
                    value_record["line_ordinal"] for value_record in trailing["values"]
                )
                trailing_rows_after_source = [
                    candidate
                    for candidate in value["row_axis"]["trailing_value_rows"]
                    if candidate["page_sequence"] == item["label_match"]["page_sequence"]
                    and candidate["values"]
                    and min(value_record["line_ordinal"] for value_record in candidate["values"])
                    > source_end
                ]
                if (
                    trailing["page_sequence"] != item["label_match"]["page_sequence"]
                    or topology_region["parent_match"]["page_sequence"]
                    != item["label_match"]["page_sequence"]
                    or len(trailing_rows_after_source) != 1
                    or trailing_line_ordinals
                    != list(range(source_end + 1, source_end + 1 + len(trailing["values"])))
                    or any(
                        candidate["occurrence_id"] != item["occurrence_id"]
                        and candidate["label_match"]["page_sequence"]
                        == item["label_match"]["page_sequence"]
                        and _visual_match_key(candidate["label_match"])
                        > _visual_match_key(item["label_match"])
                        for candidate in value["role_occurrences"]
                    )
                    or min(
                        value_record["bbox"][1] + value_record["bbox"][3]
                        for value_record in trailing["values"]
                    )
                    <= item["label_match"]["source_label_bbox"][1]
                    + item["label_match"]["source_label_bbox"][3]
                ):
                    raise _error("recursive root trailing result left its exact source page")
        if (
            result_receipt["numbers"] != result["numbers"]
            or result_receipt["sample_ids"] != result["sample_ids"]
            or (type(result_occurrence) is dict and result_occurrence["role"] != result["role"])
            or (
                type(result_occurrence) is not dict
                and (
                    result["occurrence_id"] != parent_occurrence_id
                    or result["role"] != equation["parent_role"]
                )
            )
        ):
            raise _error("recursive parent equation result does not replay exactly")
        if equation["parent_role"] in {
            "INTERBANK_DEPOSIT_GROUP",
            "INTERBANK_LOAN_GROUP",
        }:
            parent_occurrence = occurrence_by_id.get(parent_occurrence_id)
            if (
                type(parent_occurrence) is not dict
                or parent_occurrence["role"] != equation["parent_role"]
                or result["occurrence_id"] != parent_occurrence_id
                or item["scope_owner_role"] != equation["parent_role"]
            ):
                raise _error("recursive parent equation exact parent occurrence drifted")
        elif parent_occurrence_id not in root_scope_ids or item["scope_owner_role"] is not None:
            raise _error("recursive root equation exact parent scope drifted")
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
        kind = receipt["binding_kind"]
        anchor_exact_check = receipt.get("anchor_exact_source_authority_check")
        if anchor_exact_check is not None and (
            _bound_one_edit_exact_source_check(anchor_match) is None
            or not same_typed_json_v1(
                anchor_exact_check,
                anchor_match.get("one_edit_exact_source_authority_check"),
            )
        ):
            raise _error("reviewed schema source-scope anchor exact-source proof drifted")
        document_order_precedes = (
            anchor_match["end_document_line_ordinal"] < source_match["document_line_ordinal"]
        )
        visual_order_precedes = anchor_match["page_sequence"] == source_match[
            "page_sequence"
        ] and _visual_match_key(anchor_match) < _visual_match_key(source_match)
        if anchor_match["page_sequence"] != source_match["page_sequence"] or not (
            document_order_precedes
            or kind == _RECURSIVE_PARENT_PROVISION_BINDING_KIND
            and visual_order_precedes
        ):
            raise _error("reviewed schema source-scope anchor does not precede its source")
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
        elif kind == _RECURSIVE_PARENT_PROVISION_BINDING_KIND:
            equation = receipt["geometry"]["equation"]
            parent_occurrence_id = equation["parent_occurrence_id"]
            same_parent_targets = [
                candidate
                for candidate in value["role_occurrences"]
                if candidate["role"] == occurrence["role"]
                and candidate["scope_owner_occurrence_id"] == parent_occurrence_id
            ]
            if equation["parent_role"] in {
                "INTERBANK_DEPOSIT_GROUP",
                "INTERBANK_LOAN_GROUP",
            }:
                expected_anchor = occurrence_by_id.get(parent_occurrence_id)
                later_parent_boundaries = (
                    [
                        candidate
                        for candidate in value["role_occurrences"]
                        if candidate["role"] in {"INTERBANK_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"}
                        and candidate["occurrence_id"] != parent_occurrence_id
                        and candidate["label_match"]["page_sequence"]
                        == source_match["page_sequence"]
                        and _visual_match_key(candidate["label_match"])
                        > _visual_match_key(expected_anchor["label_match"])
                    ]
                    if type(expected_anchor) is dict
                    else []
                )
                next_parent_boundary = min(
                    later_parent_boundaries,
                    key=lambda candidate: _visual_match_key(candidate["label_match"]),
                    default=None,
                )
                source_precedes_boundary = next_parent_boundary is None or _visual_match_key(
                    source_match
                ) < _visual_match_key(next_parent_boundary["label_match"])
            else:
                expected_anchor_candidates = [
                    candidates[0]
                    for component in equation["component_frontier"][:-1]
                    if len(
                        candidates := occurrences_by_retrieval_id.get(
                            component["retrieval_occurrence_id"], []
                        )
                    )
                    == 1
                ]
                expected_anchor = (
                    expected_anchor_candidates[-1] if expected_anchor_candidates else None
                )
                source_precedes_boundary = True
            topology_region = axis["topology_region"]
            if (
                type(expected_anchor) is not dict
                or expected_anchor["occurrence_id"] != anchor["occurrence_id"]
                or not source_precedes_boundary
                or len(same_parent_targets) != 1
                or same_parent_targets[0]["occurrence_id"] != occurrence["occurrence_id"]
                or receipt["interval"]["start_document_line_ordinal"]
                != topology_region["cluster_start_document_line_ordinal"]
                or receipt["interval"]["end_document_line_ordinal_exclusive"]
                != topology_region["cluster_end_document_line_ordinal_exclusive"]
            ):
                raise _error("recursive parent provision interval or unique owner drifted")
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
    _validate_unique_dash_speck_evidence_axis(
        value["authenticated_unique_dash_speck_evidence"],
        axis=axis,
        occurrence_by_id=occurrence_by_id,
        topology_candidates_id=value["topology_candidates_id"],
        topology_scan_id=value["topology_scan_id"],
    )
    _validate_numeric_sample_universe(value, axis, occurrence_by_id)
    if one_edit_proofs["format_version"] == one_edit_v1.PARENT_FRONTIER_FORMAT_VERSION:
        try:
            one_edit_v1._validate_parent_frontier_against_structural_evidence_v1(  # noqa: SLF001
                one_edit_proofs,
                {
                    "authenticated_extreme_margin_furniture_evidence": value[
                        "authenticated_extreme_margin_furniture_evidence"
                    ],
                    "internal_unassigned_numeric_clusters": value[
                        "internal_unassigned_numeric_clusters"
                    ],
                    "numeric_sample_universe": value["numeric_sample_universe"],
                    "role_occurrences": value["role_occurrences"],
                    "row_axis": axis,
                },
            )
        except one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error as exc:
            raise _error(
                "one-edit parent-frontier proof does not bind the occurrence axis"
            ) from exc
    if one_edit_proofs["format_version"] == one_edit_v1.HIERARCHY_FRONTIER_FORMAT_VERSION:
        try:
            one_edit_v1._validate_hierarchy_frontier_against_structural_evidence_v1(  # noqa: SLF001
                one_edit_proofs,
                {
                    "internal_unassigned_numeric_clusters": value[
                        "internal_unassigned_numeric_clusters"
                    ],
                    "numeric_sample_universe": value["numeric_sample_universe"],
                    "role_occurrences": value["role_occurrences"],
                    "row_axis": axis,
                },
            )
        except one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error as exc:
            raise _error(
                "one-edit hierarchy-frontier proof does not bind the occurrence axis"
            ) from exc
    if one_edit_proofs["format_version"] == one_edit_v1.RECURSIVE_HIERARCHY_FRONTIER_FORMAT_VERSION:
        try:
            one_edit_v1._validate_recursive_hierarchy_frontier_against_structural_evidence_v1(  # noqa: SLF001
                one_edit_proofs,
                {
                    "authenticated_extreme_margin_furniture_evidence": value[
                        "authenticated_extreme_margin_furniture_evidence"
                    ],
                    "internal_unassigned_numeric_clusters": value[
                        "internal_unassigned_numeric_clusters"
                    ],
                    "numeric_sample_universe": value["numeric_sample_universe"],
                    "role_occurrences": value["role_occurrences"],
                    "row_axis": axis,
                },
            )
        except one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error as exc:
            raise _error(
                "one-edit recursive hierarchy-frontier proof does not bind the occurrence axis"
            ) from exc
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
    prepared_source_exact_axis_cache: dict[tuple[str, str], Any] | None,
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
    printed_note_v3_topology_candidates_id = _printed_note_reference_v3_topology_candidates_id(
        topology_candidates
    )
    one_edit_exact_source_structural_proofs, expanded_matches = (
        _one_edit_exact_source_structural_proofs_v2(
            parsed_pages,
            family_spec,
            compiled_family,
            selected_region,
            expected_effective,
            expanded_matches,
            prepared_source_exact_axis_cache=prepared_source_exact_axis_cache,
        )
    )
    expanded_matches = _project_exact_bound_source_context_challengers_v1(
        parsed_pages,
        compiled_family,
        selected_region,
        expanded_matches,
    )
    expanded_matches = _project_reviewed_schema_source_scopes(
        parsed_pages,
        compiled_family,
        expanded_matches,
        selected_region,
    )
    expanded_matches = _project_unique_contextual_structural_body_matches_v1(
        parsed_pages,
        expanded_matches,
        selected_region,
    )
    preliminary_matches = _decorate_scopes(expanded_matches, selected_region)
    if any(match["role"] == _PROVISION_GENERIC_ROLE for match in preliminary_matches):
        preliminary_expanded = _expanded_region(expected_effective, preliminary_matches)
        try:
            preliminary_axis = row_v1._build_axis(
                parsed_pages,
                scan,
                preliminary_expanded,
                visible_dash_rescues,
            )
        except row_v1.AccountingFamilyRowAxisV1Error as exc:
            raise _error("sealed preliminary recursive-parent row projection failed") from exc
        preliminary_axis, _preliminary_unique_dash_evidence = _project_unique_dash_speck_rescues_v2(
            preliminary_axis,
            preliminary_matches,
            visible_dash_rescues,
            topology_candidates_id=topology_candidates_id,
            topology_scan_id=scan["scan_id"],
        )
        preliminary_axis, _preliminary_dash_evidence, _preliminary_dash_reasons = (
            _authenticate_existing_dashes(
                preliminary_axis,
                selected_snapshot=selected_snapshot,
                render_snapshots=render_snapshots,
            )
        )
        preliminary_axis, _preliminary_structural_rejections = (
            _project_structural_owner_only_rescue_rejections(preliminary_axis, preliminary_matches)
        )
        try:
            preliminary_axis, preliminary_coextensive = (
                total_v1.project_accounting_family_coextensive_structural_numeric_rows_v1(
                    preliminary_axis,
                    preliminary_matches,
                )
            )
            if preliminary_coextensive:
                preliminary_axis = _regenerate_v1_axis(preliminary_axis)
        except total_v1.AccountingFamilyCoextensiveParentTotalV1Error as exc:
            raise _error("recursive-parent preliminary subtotal projection failed") from exc
        (
            preliminary_numeric_sample_universe,
            preliminary_internal_unassigned_numeric_clusters,
            _preliminary_furniture_evidence,
            _preliminary_furniture_reasons,
        ) = _build_numeric_sample_universe(
            parsed_pages,
            preliminary_expanded,
            preliminary_matches,
            preliminary_axis,
            preliminary_coextensive,
            topology_candidates_id=topology_candidates_id,
            printed_note_v3_topology_candidates_id=printed_note_v3_topology_candidates_id,
            selected_snapshot=selected_snapshot,
            render_snapshots=render_snapshots,
        )
        expanded_matches = _project_recursive_parent_provision_bindings(
            parsed_pages,
            compiled_family,
            expanded_matches,
            preliminary_matches,
            preliminary_axis,
            preliminary_internal_unassigned_numeric_clusters,
            preliminary_numeric_sample_universe,
            selected_region,
        )
        visible_dash_rescues = _retarget_recursive_parent_provision_dash_rescues(
            visible_dash_rescues,
            preliminary_matches,
            expanded_matches,
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
    post_row_matches = _project_unique_contextual_structural_body_matches_v1(
        parsed_pages,
        row_matches,
        selected_region,
        row_axis=raw_axis,
    )
    if [match["occurrence_id"] for match in post_row_matches] != [
        match["occurrence_id"] for match in row_matches
    ]:
        row_matches = post_row_matches
        expanded_matches = [canonical_clone_v1(match) for match in row_matches]
        expanded = _expanded_region(expected_effective, row_matches)
        try:
            raw_axis = row_v1._build_axis(
                parsed_pages,
                scan,
                expanded,
                visible_dash_rescues,
            )
        except row_v1.AccountingFamilyRowAxisV1Error as exc:
            raise _error("contextual structural body row/lane replay failed") from exc
    raw_axis, unique_dash_speck_evidence = _project_unique_dash_speck_rescues_v2(
        raw_axis,
        row_matches,
        visible_dash_rescues,
        topology_candidates_id=topology_candidates_id,
        topology_scan_id=scan["scan_id"],
    )
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
    original_axis = axis
    projected_axis, printed_note_candidate_sample_ids = (
        _project_authenticated_printed_note_reference_columns_v3(
            pages=parsed_pages,
            expanded_region=expanded,
            matches=row_matches,
            axis=original_axis,
        )
    )
    projected_numeric_result = _build_numeric_sample_universe(
        parsed_pages,
        expanded,
        row_matches,
        projected_axis,
        coextensive_evidence,
        topology_candidates_id=topology_candidates_id,
        printed_note_v3_topology_candidates_id=printed_note_v3_topology_candidates_id,
        selected_snapshot=selected_snapshot,
        render_snapshots=render_snapshots,
        printed_note_candidate_sample_ids=printed_note_candidate_sample_ids,
    )
    projected_furniture = projected_numeric_result[2]
    authenticated_printed_note_sample_ids = {
        evidence["sample_id"]
        for evidence in projected_furniture
        if evidence["status"]
        in {
            _PRINTED_NOTE_REFERENCE_FURNITURE_V3_STATUS,
            _PRINTED_NOTE_REFERENCE_FURNITURE_V4_STATUS,
        }
    }
    if (
        printed_note_candidate_sample_ids
        and authenticated_printed_note_sample_ids == printed_note_candidate_sample_ids
    ):
        axis = projected_axis
        (
            numeric_sample_universe,
            internal_unassigned_numeric_clusters,
            authenticated_extreme_margin_furniture_evidence,
            extreme_margin_render_reasons,
        ) = projected_numeric_result
    elif printed_note_candidate_sample_ids:
        axis = original_axis
        (
            numeric_sample_universe,
            internal_unassigned_numeric_clusters,
            authenticated_extreme_margin_furniture_evidence,
            fallback_render_reasons,
        ) = _build_numeric_sample_universe(
            parsed_pages,
            expanded,
            row_matches,
            original_axis,
            coextensive_evidence,
            topology_candidates_id=topology_candidates_id,
            printed_note_v3_topology_candidates_id=printed_note_v3_topology_candidates_id,
            selected_snapshot=selected_snapshot,
            render_snapshots=render_snapshots,
        )
        extreme_margin_render_reasons = list(
            dict.fromkeys([*projected_numeric_result[3], *fallback_render_reasons])
        )
    else:
        axis = original_axis
        (
            numeric_sample_universe,
            internal_unassigned_numeric_clusters,
            authenticated_extreme_margin_furniture_evidence,
            extreme_margin_render_reasons,
        ) = projected_numeric_result
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
        "authenticated_unique_dash_speck_evidence": unique_dash_speck_evidence,
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


def project_accounting_family_one_edit_parent_frontier_authority_v2(
    occurrence_axis: Any,
    column_context: Any,
    pages: Any,
    family_spec: Any,
    selected_topology_region: Any,
    *,
    period_semantics: Any = None,
    expected_lane_unit_kinds: Any = None,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Add one arithmetic family-parent proof without changing row evidence."""

    axis = _validate_result(occurrence_axis)
    try:
        parsed_pages = row_v1._pages(pages)
        compiled = topology_v1._spec(family_spec)
    except (ValueError, RuntimeError) as exc:
        raise _error("one-edit parent-frontier projection input drifted") from exc
    if axis["family_id"] != compiled["family_id"] or type(selected_topology_region) is not dict:
        raise _error("one-edit parent-frontier projection family drifted")
    from bctc_ai.evaluation import (  # noqa: PLC0415
        accounting_family_one_edit_exact_authority_v1 as one_edit_v1,
    )

    if period_semantics is None or expected_lane_unit_kinds is None:
        try:
            replay_context = column_context_v1._validate_result(column_context)  # noqa: SLF001
        except column_context_v1.AccountingFamilyColumnContextV1Error as exc:
            raise _error("one-edit parent-frontier column policy input drifted") from exc
        if period_semantics is None:
            period_semantics = replay_context["period_semantics"]
        if expected_lane_unit_kinds is None:
            expected_lane_unit_kinds = [item["unit_kind"] for item in replay_context["unit_axis"]]
    projected_receipt = one_edit_v1.project_accounting_family_one_edit_parent_frontier_authority_v1(
        axis["one_edit_exact_source_structural_proofs"],
        {
            "authenticated_extreme_margin_furniture_evidence": axis[
                "authenticated_extreme_margin_furniture_evidence"
            ],
            "internal_unassigned_numeric_clusters": axis["internal_unassigned_numeric_clusters"],
            "numeric_sample_universe": axis["numeric_sample_universe"],
            "role_occurrences": axis["role_occurrences"],
            "row_axis": axis["row_axis"],
        },
        column_context,
        _one_edit_authority_pages_v2(parsed_pages),
        family_spec,
        selected_topology_region,
        column_context_document_pages=parsed_pages,
        period_semantics=period_semantics,
        expected_lane_unit_kinds=expected_lane_unit_kinds,
        visible_dash_rescues=visible_dash_rescues,
    )
    if same_typed_json_v1(
        projected_receipt,
        axis["one_edit_exact_source_structural_proofs"],
    ):
        return axis
    material = canonical_clone_v1(axis)
    material.pop("occurrence_axis_id")
    material["one_edit_exact_source_structural_proofs"] = projected_receipt
    return _validate_result(
        {
            **material,
            "occurrence_axis_id": "aforav2:axis:" + canonical_json_sha256_v1(material),
        }
    )


def project_accounting_family_one_edit_hierarchy_frontier_authority_v2(
    occurrence_axis: Any,
    column_context: Any,
    pages: Any,
    family_spec: Any,
    selected_topology_region: Any,
    hierarchy_spec: Any,
    *,
    period_semantics: Any,
    expected_lane_unit_kinds: Any,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Add one hierarchy-declared direct-frontier proof without changing rows."""

    axis = _validate_result(occurrence_axis)
    try:
        parsed_pages = row_v1._pages(pages)
        compiled = topology_v1._spec(family_spec)
    except (ValueError, RuntimeError) as exc:
        raise _error("one-edit hierarchy-frontier projection input drifted") from exc
    if axis["family_id"] != compiled["family_id"] or type(selected_topology_region) is not dict:
        raise _error("one-edit hierarchy-frontier projection family drifted")
    from bctc_ai.evaluation import (  # noqa: PLC0415
        accounting_family_one_edit_exact_authority_v1 as one_edit_v1,
    )

    projected_receipt = (
        one_edit_v1.project_accounting_family_one_edit_hierarchy_frontier_authority_v1(
            axis["one_edit_exact_source_structural_proofs"],
            {
                "authenticated_extreme_margin_furniture_evidence": axis[
                    "authenticated_extreme_margin_furniture_evidence"
                ],
                "internal_unassigned_numeric_clusters": axis[
                    "internal_unassigned_numeric_clusters"
                ],
                "numeric_sample_universe": axis["numeric_sample_universe"],
                "role_occurrences": axis["role_occurrences"],
                "row_axis": axis["row_axis"],
            },
            column_context,
            _one_edit_authority_pages_v2(parsed_pages),
            family_spec,
            selected_topology_region,
            hierarchy_spec,
            column_context_document_pages=parsed_pages,
            period_semantics=period_semantics,
            expected_lane_unit_kinds=expected_lane_unit_kinds,
            visible_dash_rescues=visible_dash_rescues,
        )
    )
    if same_typed_json_v1(
        projected_receipt,
        axis["one_edit_exact_source_structural_proofs"],
    ):
        return axis
    material = canonical_clone_v1(axis)
    material.pop("occurrence_axis_id")
    material["one_edit_exact_source_structural_proofs"] = projected_receipt
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
    _prepared_source_exact_axis_cache: dict[tuple[str, str], Any] | None = None,
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
        prepared_source_exact_axis_cache=_prepared_source_exact_axis_cache,
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
    prepared_source_exact_axis_cache: dict[tuple[str, str], Any] | None = None,
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
        prepared_source_exact_axis_cache=prepared_source_exact_axis_cache,
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
