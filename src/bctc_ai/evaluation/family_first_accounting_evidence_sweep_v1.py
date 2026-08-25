"""Generic all-filing evidence sweep after family topology discovery.

One declarative family topology and one small evaluation policy are applied to
every authenticated filing.  Complete-document VietOCR text is scanned before
provenance is exposed.  Numeric proposals and page renders are opened only for
documents with one unique complete topology region.  No trial is mapped here;
the strongest output is a replayable schema-review readiness proposal.
"""

from __future__ import annotations

import copy
import json
import os
import re
from collections.abc import Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from contextlib import ExitStack
from dataclasses import dataclass, field
from multiprocessing import get_context
from pathlib import Path
from time import perf_counter
from typing import Any

from bctc_ai.evaluation import accounting_additive_table_closure_v1 as additive_v1
from bctc_ai.evaluation import (
    accounting_family_column_context_multilevel_v2 as column_context_multilevel_v2,
)
from bctc_ai.evaluation import accounting_family_column_context_v1 as column_context_v1
from bctc_ai.evaluation import accounting_family_occurrence_row_axis_v2 as occurrence_row_v2
from bctc_ai.evaluation import accounting_family_one_edit_exact_authority_v1 as one_edit_v1
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_axis_v1
from bctc_ai.evaluation import accounting_family_topology_candidates_v2 as topology_candidates_v2
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import accounting_hierarchical_table_closure_v1 as hierarchical_v1
from bctc_ai.evaluation import accounting_scoped_hierarchical_table_closure_v2 as scoped_v2
from bctc_ai.evaluation import family_first_accounting_input_snapshot_v1 as snapshot_v1
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as render_v1
from bctc_ai.evaluation import family_first_document_evidence_store_v1 as document_store_v1
from bctc_ai.evaluation import family_first_ppocrv6_numeric_index_v3 as numeric_v3
from bctc_ai.evaluation import family_first_semantic_index_v1 as semantic_v1
from bctc_ai.evaluation.accounting_family_document_axis_join_v1 import (
    build_accounting_family_document_axis_join_v1,
    project_accounting_family_document_pages_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.evaluation.family_first_numeric_cell_evidence_v1 import (
    parse_visible_financial_numeric_token_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "FamilyFirstAccountingEvidenceSweepV1Error",
    "build_authenticated_family_first_accounting_evidence_sweep_v1",
    "build_authenticated_family_first_accounting_evidence_sweep_from_document_store_v1",
    "rebuild_family_first_accounting_trial_from_document_snapshot_v1",
    "validate_authenticated_family_first_accounting_evidence_sweep_replay_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_ACCOUNTING_EVIDENCE_SWEEP_V1"
EVALUATION_SPEC_FORMAT = "ACCOUNTING_FAMILY_EVALUATION_SPEC_V1"
EVALUATION_SPEC_FORMAT_V2 = "ACCOUNTING_FAMILY_EVALUATION_SPEC_V2"
EVALUATION_SPEC_FORMAT_V3 = "ACCOUNTING_FAMILY_EVALUATION_SPEC_V3"
EVALUATION_SPEC_FORMAT_V4 = "ACCOUNTING_FAMILY_EVALUATION_SPEC_V4"
EVALUATION_SPEC_FORMAT_V5 = "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5"
_DOCUMENT_STORE_SELECTED_PAGE_BATCH_SIZE = 16
_MAX_DOCUMENT_STORE_V4_JOBS = 16
_V4_WORKER_MISSING_PAGE_MODES = frozenset({"CANDIDATE_SCOPED", "FULL", "NONE"})
_V4_RENDER_PREFLIGHT_FORMAT_VERSION = "FAMILY_FIRST_DOCUMENT_RENDER_PREFLIGHT_V1"
_V4_RENDER_PREFLIGHT_CONTEXT_CACHE: dict[str, dict[str, Any]] = {}
_V4_TRIAL_CHECKPOINT_FORMAT_VERSION = "FAMILY_FIRST_DOCUMENT_TRIAL_CHECKPOINT_V1"
CLAIM_BOUNDARY = (
    "AUTHENTICATED_ALL_FILING_COMPLETE_DOCUMENT_TOPOLOGY_FRESH_VIETOCR_LABEL_"
    "PPOCRV6_MEDIUM_NUMERIC_PERIOD_UNIT_AND_VISIBLE_ADDITIVE_CLOSURE_EVIDENCE_"
    "SWEEP_PROPOSAL_ONLY_NO_NOT_OBSERVED_SCHEMA_MAPPING_CANONICALIZATION_EXPORT_"
    "OR_PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "all_authenticated_documents_scanned_for_topology": True,
    "bank_file_page_period_scope_used_for_matching_or_routing": False,
    "mapping_authority": False,
    "not_observed_authority": False,
    "numeric_authority": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "schema_authority": False,
    "schema_review_readiness_proposal_only": True,
}
_FIELDS = {
    "authority",
    "claim_boundary",
    "evaluation_spec",
    "family_id",
    "family_spec",
    "format_version",
    "input_indices",
    "metrics",
    "state",
    "sweep_id",
    "trials",
}
_SPEC_FIELDS = {
    "closure_policy",
    "expected_lane_unit_kinds",
    "family_id",
    "format_version",
    "period_semantics",
}
_SPEC_FIELDS_V2 = {*_SPEC_FIELDS, "source_group_equivalences"}
_SPEC_FIELDS_V3 = {*_SPEC_FIELDS, "hierarchical_closure_spec"}
_SPEC_FIELDS_V4 = {
    *_SPEC_FIELDS_V3,
    "candidate_selection_policy",
    "occurrence_row_axis_policy",
}
_SPEC_FIELDS_V5 = {
    *(_SPEC_FIELDS_V4 - {"expected_lane_unit_kinds"}),
    "expected_lane_unit_kind_alternatives",
}
_SOURCE_GROUP_EQUIVALENCE_FIELDS = {"component_roles", "group_role"}
_TRIAL_FIELDS = {
    "additive_closure",
    "column_context",
    "document_axis_binding",
    "document_ordinal",
    "evidence_status",
    "private_provenance",
    "row_axis",
    "source_pdf_ref",
    "topology_scan",
    "unresolved_reasons",
}
_TRIAL_FIELDS_V4 = {*_TRIAL_FIELDS, "one_edit_exact_authority_receipt"}
_BINDING_FIELDS = {"document_axis_id", "metrics", "source_binding_sha256"}
_INDEX_FIELDS = {"numeric_receipt_id", "semantic_index_id"}
_METRIC_FIELDS = {
    "document_count",
    "evidence_ready_for_schema_review_count",
    "mapping_verified_count",
    "not_observed_count",
    "unique_topology_document_count",
    "unresolved_document_count",
}


class FamilyFirstAccountingEvidenceSweepV1Error(ValueError):
    """The capabilities, family policy, source join, gate, or replay drifted."""


def _error(message: str) -> FamilyFirstAccountingEvidenceSweepV1Error:
    return FamilyFirstAccountingEvidenceSweepV1Error(message)


def _is_scoped_evaluation_format(value: Any) -> bool:
    return value in {EVALUATION_SPEC_FORMAT_V4, EVALUATION_SPEC_FORMAT_V5}


def _is_scoped_evaluation_policy(value: Any) -> bool:
    return type(value) is dict and _is_scoped_evaluation_format(value.get("format_version"))


def _lane_unit_kind_alternatives(evaluation_spec: Mapping[str, Any]) -> list[list[str]]:
    if evaluation_spec.get("format_version") == EVALUATION_SPEC_FORMAT_V5:
        return canonical_clone_v1(evaluation_spec["expected_lane_unit_kind_alternatives"])
    return [canonical_clone_v1(evaluation_spec["expected_lane_unit_kinds"])]


def _resolved_lane_unit_kinds(
    evaluation_spec: Mapping[str, Any], column_context: Mapping[str, Any]
) -> list[str]:
    try:
        resolved = [
            record["unit_kind"]
            for record in sorted(
                column_context["unit_axis"], key=lambda record: record["column_ordinal"]
            )
        ]
    except (KeyError, TypeError):
        raise _error("column context lost its resolved lane unit axis") from None
    alternatives = _lane_unit_kind_alternatives(evaluation_spec)
    if resolved not in alternatives:
        raise _error("column context unit axis is outside the declared alternatives")
    return resolved


@dataclass(frozen=True, slots=True, eq=False)
class _PreparedV4DocumentStoreContextV1:
    """Same-turn snapshot/topology authority reused by base and render passes."""

    caller_snapshot_sha256: str
    evaluation_spec_sha256: str
    family_spec_sha256: str
    prepared_context_sha256: str
    prepared_snapshot: Any = field(repr=False, compare=False)
    prepared_topology: Any = field(repr=False, compare=False)
    seal: object = field(repr=False, compare=False)


_PREPARED_V4_DOCUMENT_CONTEXT_SEAL = object()


@dataclass(frozen=True, slots=True, eq=False)
class _PreparedV4RenderTopologyHandoffV1:
    """Topology authority already authenticated by one exact trial pass."""

    legacy_topology_scan_id: str
    prepared_context_sha256: str
    topology_candidates_id: str
    seal: object = field(repr=False, compare=False)


_PREPARED_V4_RENDER_TOPOLOGY_HANDOFF_SEAL = object()


@dataclass(frozen=True, slots=True, eq=False)
class _PreparedV4CandidateOccurrenceAxisV1:
    """One exact candidate occurrence axis reusable for identical pixels."""

    input_sha256: str
    occurrence_axis_id: str
    occurrence_axis_sha256: str
    payload: bytes = field(repr=False, compare=False)
    seal: object = field(repr=False, compare=False)


_PREPARED_V4_CANDIDATE_OCCURRENCE_AXIS_SEAL = object()


@dataclass(frozen=True, slots=True, eq=False)
class _PreparedV4CandidateRenderScheduleV1:
    """Candidate-local render pages derived before downstream selection."""

    candidate_axis_sha256: str
    render_pages: tuple[int, ...]
    schedule_sha256: str
    topology_candidates_id: str
    topology_scan_id: str
    seal: object = field(repr=False, compare=False)


_PREPARED_V4_CANDIDATE_RENDER_SCHEDULE_SEAL = object()


@dataclass(frozen=True, slots=True, eq=False)
class _PreparedSelectedOneEditPublicReplayV1:
    """One successful selected replay, reusable only for identical inputs."""

    input_sha256: str
    receipt_sha256: str
    seal: object = field(repr=False, compare=False)


_PREPARED_SELECTED_ONE_EDIT_PUBLIC_REPLAY_SEAL = object()

_SELECTED_PUBLIC_REPLAY_DEFERRED_FOR_RENDER_REASON = (
    "SELECTED_ONE_EDIT_PUBLIC_REPLAY_DEFERRED_FOR_AUTHENTICATED_RENDER"
)


def _prepared_v4_document_context_material_v1(
    *,
    caller_snapshot_sha256: str,
    evaluation_spec_sha256: str,
    family_spec_sha256: str,
    prepared_snapshot: Any,
    prepared_topology: Any,
) -> dict[str, Any]:
    return {
        "caller_snapshot_sha256": caller_snapshot_sha256,
        "evaluation_spec_sha256": evaluation_spec_sha256,
        "family_spec_sha256": family_spec_sha256,
        "prepared_snapshot_context_sha256": getattr(
            prepared_snapshot, "prepared_context_sha256", None
        ),
        "prepared_topology_context_sha256": getattr(
            prepared_topology, "prepared_context_sha256", None
        ),
    }


def _new_v4_runtime_telemetry_v1() -> dict[str, int | float]:
    """Create opt-in process telemetry; it is never persisted as evidence."""

    return {
        "candidate_count": 0,
        "occurrence_axis_build_count": 0,
        "occurrence_base_reuse_count": 0,
        "render_page_count": 0,
        "render_retry_count": 0,
        "snapshot_prepare_count": 0,
        "snapshot_prepare_seconds": 0.0,
        "topology_prepare_count": 0,
        "topology_prepare_seconds": 0.0,
    }


def _telemetry_add(
    telemetry: dict[str, int | float] | None,
    field_name: str,
    value: int | float,
) -> None:
    if telemetry is not None:
        telemetry[field_name] = telemetry.get(field_name, 0) + value


def _evaluation_spec(
    value: Any,
    family_spec: dict[str, Any],
    *,
    raw_family_spec: Any = None,
) -> dict[str, Any]:
    is_v2 = type(value) is dict and value.get("format_version") == EVALUATION_SPEC_FORMAT_V2
    is_v3 = type(value) is dict and value.get("format_version") == EVALUATION_SPEC_FORMAT_V3
    is_v4 = type(value) is dict and value.get("format_version") == EVALUATION_SPEC_FORMAT_V4
    is_v5 = type(value) is dict and value.get("format_version") == EVALUATION_SPEC_FORMAT_V5
    if (
        type(value) is not dict
        or set(value)
        != (
            _SPEC_FIELDS_V5
            if is_v5
            else _SPEC_FIELDS_V4
            if is_v4
            else _SPEC_FIELDS_V3
            if is_v3
            else _SPEC_FIELDS_V2
            if is_v2
            else _SPEC_FIELDS
        )
        or value["format_version"]
        not in {
            EVALUATION_SPEC_FORMAT,
            EVALUATION_SPEC_FORMAT_V2,
            EVALUATION_SPEC_FORMAT_V3,
            EVALUATION_SPEC_FORMAT_V4,
            EVALUATION_SPEC_FORMAT_V5,
        }
        or value["family_id"] != family_spec["family_id"]
        or value["period_semantics"] not in {"BALANCE_COMPARATIVE", "CURRENT_ROLLFORWARD"}
        or value["closure_policy"]
        not in {
            "CORROBORATE_IF_VISIBLE",
            "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE",
            "REQUIRE_EXACT_UNIQUE_VISIBLE_TRAILING_TOTAL",
            "SCOPED_HIERARCHICAL_EXHAUSTIVE_CORROBORATE_OR_DERIVE",
        }
        or (
            not is_v5
            and (
                type(value["expected_lane_unit_kinds"]) is not list
                or not value["expected_lane_unit_kinds"]
                or any(
                    item not in {"MONEY", "PERCENT"} for item in value["expected_lane_unit_kinds"]
                )
            )
        )
    ):
        raise _error("family evaluation specification drifted")
    if is_v5:
        alternatives = value["expected_lane_unit_kind_alternatives"]
        if (
            type(alternatives) is not list
            or not alternatives
            or len(alternatives)
            != len({tuple(item) for item in alternatives if type(item) is list})
            or any(
                type(item) is not list
                or not item
                or any(kind not in {"MONEY", "PERCENT"} for kind in item)
                for item in alternatives
            )
        ):
            raise _error("family evaluation lane-unit alternatives drifted")
    if is_v4 or is_v5:
        if (
            value["closure_policy"] != "SCOPED_HIERARCHICAL_EXHAUSTIVE_CORROBORATE_OR_DERIVE"
            or value["candidate_selection_policy"]
            != "SAME_POPULATION_STRICT_ROLE_SUPERSET_WITH_EXACT_PERIOD_UNIT_ROOT_TOTAL"
        ):
            raise _error("scoped hierarchical family evaluation policy drifted")
        try:
            occurrence_row_v2._policy(value["occurrence_row_axis_policy"])
            scoped_v2._spec(value["hierarchical_closure_spec"], raw_family_spec)
        except (ValueError, RuntimeError) as exc:
            raise _error("scoped hierarchical family evaluation specification drifted") from exc
    if is_v3:
        if value["closure_policy"] != "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE":
            raise _error("hierarchical family evaluation closure policy drifted")
        hierarchy = value["hierarchical_closure_spec"]
        if type(hierarchy) is not dict:
            raise _error("hierarchical family evaluation specification drifted")
        if raw_family_spec is not None:
            try:
                hierarchical_v1._spec(hierarchy, raw_family_spec)
            except (ValueError, RuntimeError) as exc:
                raise _error("hierarchical family evaluation specification drifted") from exc
    if is_v2:
        if (
            type(value["source_group_equivalences"]) is not list
            or not value["source_group_equivalences"]
        ):
            raise _error("family evaluation source-group equivalence drifted")
        role_kinds = {child["role"]: child["role_kind"] for child in family_spec["children"]}
        groups: set[str] = set()
        components: set[str] = set()
        for item in value["source_group_equivalences"]:
            if (
                type(item) is not dict
                or set(item) != _SOURCE_GROUP_EQUIVALENCE_FIELDS
                or type(item["group_role"]) is not str
                or not item["group_role"]
                or type(item["component_roles"]) is not list
                or not item["component_roles"]
                or any(type(role) is not str or not role for role in item["component_roles"])
                or len(item["component_roles"]) != len(set(item["component_roles"]))
                or item["group_role"] in groups
                or any(role in components for role in item["component_roles"])
                or role_kinds.get(item["group_role"]) != "SOURCE_ONLY_GROUP_PARENT"
                or any(role_kinds.get(role) != "ADDITIVE_CHILD" for role in item["component_roles"])
            ):
                raise _error("family evaluation source-group equivalence drifted")
            groups.add(item["group_role"])
            components.update(item["component_roles"])
    return canonical_clone_v1(value)


def _blind_pages(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["source_bbox_raw_pixels"]),
                    "source_line_index": line["line_ordinal"],
                    "source_text": None,
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["physical_page"],
        }
        for page in document["pages"]
    ]


def _v4_topology_authority(
    topology_pages: list[dict[str, Any]],
    family_spec: dict[str, Any],
    *,
    expected_legacy_scan: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Rebuild one V1 scan and its complete pre-pruning V2 candidate axis."""

    prepared = topology_candidates_v2._prepare_accounting_family_topology_candidates_v2(
        topology_pages,
        family_spec,
    )
    legacy_scan, candidates, _bindings = (
        topology_candidates_v2._prepared_accounting_family_topology_authority_v2(prepared)
    )
    if expected_legacy_scan is not None and not same_typed_json_v1(
        legacy_scan,
        expected_legacy_scan,
    ):
        raise _error("V4 legacy topology scan differs from its complete source replay")
    if candidates["input_binding"]["legacy_topology_scan_id"] != legacy_scan["scan_id"]:
        raise _error("V4 topology candidate authority lost its legacy scan binding")
    return legacy_scan, candidates


def _region_pages(document: dict[str, Any], region: dict[str, Any]) -> tuple[int, ...]:
    start = region["cluster_start_document_line_ordinal"]
    stop = region["cluster_end_document_line_ordinal_exclusive"]
    offset = 0
    pages = []
    for page in document["pages"]:
        page_stop = offset + page["line_count"]
        if offset < stop and page_stop > start:
            pages.append(page["physical_page"])
        offset = page_stop
    if not pages:
        raise _error("unique topology region retained no source page")
    return tuple(pages)


def _axis_binding(document_axis: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_axis_id": document_axis["document_axis_id"],
        "metrics": canonical_clone_v1(document_axis["metrics"]),
        "source_binding_sha256": document_axis["source_binding_sha256"],
    }


def _visible_dash_rescue_inputs(
    *,
    joined_pages: list[dict[str, Any]],
    row_axis: dict[str, Any],
    render_snapshots: tuple[dict[str, Any], ...],
    require_unique_role_page_owner: bool = False,
) -> tuple[dict[str, Any], ...]:
    if not render_snapshots:
        # The document-store fast path intentionally carries authenticated
        # text/numeric/geometry evidence but no render pixels.  Missing cells
        # therefore remain unresolved for a bounded page-local pixel refresh;
        # they must not abort or silently broaden the family sweep.
        return ()
    region = row_axis["topology_region"]
    if region is None:
        return ()
    by_page = {page["page_sequence"]: page for page in joined_pages}
    heights = {
        snapshot["physical_page"]: snapshot["render_ref"]["pixel_height"]
        for snapshot in render_snapshots
    }
    region_lines = row_axis_v1._region_lines(joined_pages, region)
    if type(require_unique_role_page_owner) is not bool:
        raise _error("visible-dash rescue owner policy must be one exact boolean")
    v1_role_page_owner_counts: dict[tuple[str, int], int] = {}
    if require_unique_role_page_owner:
        for observed_row in row_axis["rows"]:
            owner_key = (
                observed_row["role"],
                observed_row["label_match"]["page_sequence"],
            )
            v1_role_page_owner_counts[owner_key] = v1_role_page_owner_counts.get(owner_key, 0) + 1
    rescues = []
    for row in row_axis["rows"]:
        if not row["missing_column_ordinals"]:
            continue
        match = row["label_match"]
        page_sequence = match["page_sequence"]
        if (
            require_unique_role_page_owner
            and v1_role_page_owner_counts[(row["role"], page_sequence)] != 1
        ):
            # The sealed V1 rescue contract selects rows by role and page,
            # not by the V2 occurrence identity.  A repeated role on one
            # page therefore cannot receive an unambiguous V1 pixel hint.
            # Keep its base missing lane so typed source-only evidence and
            # ordinary closure vetoes remain authoritative.
            continue
        page = by_page[page_sequence]
        page_height = heights.get(page_sequence)
        if type(page["page_width"]) is not int or type(page_height) is not int:
            raise _error("missing-lane page lacks authenticated render dimensions")
        label_boxes = [
            line["bbox"]
            for line in page["lines"]
            if match["source_line_index"] <= line["line_ordinal"] <= match["end_source_line_index"]
        ]
        try:
            centers, visible_cells = row_axis_v1._resolved_page_grid_inputs(
                row_axis["rows"], row, row_axis["column_grids"]
            )
        except row_axis_v1.AccountingFamilyRowAxisV1Error:
            # Pixel dash rescue is optional and may never broaden an
            # inconsistent observed grid.  Preserve the missing lane so the
            # ordinary row-axis gate remains UNRESOLVED instead of aborting
            # every filing in the family sweep.
            continue
        proposals = propose_missing_value_lane_regions_v1(
            region_lines[page_sequence],
            label_boxes=label_boxes,
            is_numeric=row_axis_v1._is_numeric,
            page_width=page["page_width"],
            page_height=page_height,
            retain_singleton_columns=False,
            resolved_column_centers=centers,
            resolved_visible_value_cells=visible_cells,
        )
        by_lane = {proposal["column_ordinal"]: proposal for proposal in proposals}
        for lane in row["missing_column_ordinals"]:
            proposal = by_lane.get(lane)
            if proposal is None:
                continue
            crop = render_v1._crop_authenticated_family_first_page_render_snapshot_v1(
                next(
                    snapshot
                    for snapshot in render_snapshots
                    if snapshot["physical_page"] == page_sequence
                ),
                raw_pixel_bbox=proposal["raw_pixel_bbox"],
            )
            rescues.append(
                {
                    "column_ordinal": lane,
                    "page_sequence": page_sequence,
                    "region": crop,
                    "role": row["role"],
                }
            )
    return tuple(rescues)


def _unresolved_reasons(
    row_axis: dict[str, Any],
    column_context: dict[str, Any],
    closure: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    reasons = []
    if row_axis["status"] != "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY":
        reasons.append("VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE")
    if column_context["status"] != "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY":
        reasons.extend(
            f"COLUMN_CONTEXT:{reason}" for reason in column_context["unresolved_reasons"]
        )
    if policy["closure_policy"] in {
        "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE",
        "SCOPED_HIERARCHICAL_EXHAUSTIVE_CORROBORATE_OR_DERIVE",
    }:
        if closure["status"] != "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO":
            reasons.extend(
                f"HIERARCHICAL_CLOSURE:{reason}" for reason in closure["unresolved_reasons"]
            )
    elif (
        policy["closure_policy"] == "REQUIRE_EXACT_UNIQUE_VISIBLE_TRAILING_TOTAL"
        and closure["status"] != "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL"
    ):
        reasons.extend(f"ADDITIVE_CLOSURE:{reason}" for reason in closure["unresolved_reasons"])
    elif (
        policy["closure_policy"] == "CORROBORATE_IF_VISIBLE"
        and closure["metrics"]["visible_trailing_candidate_count"] > 0
        and closure["status"] != "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL"
    ):
        reasons.extend(
            f"VISIBLE_ADDITIVE_CLOSURE_VETO:{reason}" for reason in closure["unresolved_reasons"]
        )
    return reasons


def _axis_numeric_values(row_axis: dict[str, Any]) -> list[tuple[str | None, dict[str, Any]]]:
    return [
        *((row["role"], value) for row in row_axis["rows"] for value in row["values"]),
        *((None, value) for row in row_axis["trailing_value_rows"] for value in row["values"]),
    ]


def _mixed_candidate_has_accounting_corroboration(
    *,
    role: str | None,
    sample_id: str,
    closure: dict[str, Any],
    hierarchy_frontier_certified_sample_ids: set[str] | None = None,
) -> bool:
    if sample_id in (hierarchy_frontier_certified_sample_ids or set()):
        return True
    if closure["format_version"] in {
        "ACCOUNTING_ADDITIVE_TABLE_CLOSURE_V1",
        "ACCOUNTING_ADDITIVE_TABLE_CLOSURE_V2",
    }:
        if closure["status"] != "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL":
            return False
        if any(sample_id in lane["component_sample_ids"] for lane in closure["lane_sums"]) or any(
            sample_id in candidate["sample_ids"] for candidate in closure["exact_total_candidates"]
        ):
            return True
        # V2 may replace exact component rows with their visible source-group
        # parent in the outer sum. Successful closure means that group equality
        # was checked before replacement.
        return role is not None and any(
            role in item["component_roles"] for item in closure.get("source_group_equivalences", [])
        )
    if closure["format_version"] == "ACCOUNTING_HIERARCHICAL_TABLE_CLOSURE_V1":
        if closure["status"] != "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO":
            return False
        return role is not None and any(
            equation["status"]
            in {
                "VISIBLE_RESULT_CORROBORATED_BY_COMPONENTS",
                "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_COMPONENTS",
            }
            and (role == equation["result_role"] or role in equation["component_roles_present"])
            for equation in closure["equations"]
        )
    if closure["format_version"] == "ACCOUNTING_SCOPED_HIERARCHICAL_TABLE_CLOSURE_V2":
        if closure["status"] != "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO":
            return False
        receipts = [
            receipt for receipt in closure["coverage_receipt"] if sample_id in receipt["sample_ids"]
        ]
        if len(receipts) != 1:
            return False
        receipt = receipts[0]
        if role is None:
            if (
                receipt["row_kind"] != "TRAILING_VALUE_ROW"
                or receipt["disposition"] != "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE"
            ):
                return False
            exact_trailing = [
                equation
                for equation in closure["equations"]["global"]
                if equation["status"]
                == "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
                and equation["selected_trailing_candidate_ordinal"] == receipt["candidate_ordinal"]
                and any(
                    evidence["candidate_ordinal"] == receipt["candidate_ordinal"]
                    and evidence["status"] == "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE"
                    and sample_id in evidence["sample_ids"]
                    for evidence in equation["trailing_candidate_evidence"]
                )
            ]
            return len(exact_trailing) == 1
        if (
            receipt["row_kind"] != "ROLE_ROW"
            or receipt["role"] != role
            or receipt["occurrence_id"] is None
        ):
            return False
        if receipt["disposition"] in {
            "LOCAL_EXHAUSTIVE_COMPONENT_OCCURRENCE",
            "LOCAL_SUBTOTAL_RESULT_OCCURRENCE",
        }:
            owner_occurrence_id = (
                receipt["occurrence_id"]
                if receipt["disposition"] == "LOCAL_SUBTOTAL_RESULT_OCCURRENCE"
                else receipt["source_record"]["label_match"]["scope_owner_occurrence_id"]
            )
            exact_local = [
                equation
                for equation in closure["equations"]["local"]
                if equation["result_occurrence_id"] == owner_occurrence_id
                and equation["status"]
                == "LOCAL_VISIBLE_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"
                and (role == equation["result_role"] or role in equation["component_roles_present"])
            ]
            return len(exact_local) == 1
        if receipt["disposition"] != "GLOBAL_HIERARCHY_SOURCE_OCCURRENCE":
            return False
        accounting_roles = {role}
        accounting_roles.update(
            record["role"]
            for record in closure["resolved_roles"]
            if record["source"] is not None
            and record["source"]["kind"] == "ROLE_ROW"
            and record["source"]["record"]["label_match"].get("occurrence_id")
            == receipt["occurrence_id"]
            and any(
                value["sample_id"] == sample_id for value in record["source"]["record"]["values"]
            )
        )
        reachable_roles = set(accounting_roles)
        exact_derived_status = "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM"
        exact_visible_statuses = {
            "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
            "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
        }
        equations = closure["equations"]["global"]
        while True:
            changed = False
            for equation in equations:
                if equation["status"] not in exact_visible_statuses | {exact_derived_status}:
                    continue
                components = set(equation["component_roles_present"])
                if not reachable_roles & components:
                    continue
                result_role = equation["result_role"]
                if result_role not in reachable_roles:
                    reachable_roles.add(result_role)
                    changed = True
            if not changed:
                break
        return any(
            equation["status"] in exact_visible_statuses
            and (
                equation["result_role"] in reachable_roles
                or bool(reachable_roles & set(equation["component_roles_present"]))
            )
            for equation in equations
        )
    return False


def _mixed_separator_consensus_reasons(
    *,
    row_axis: dict[str, Any],
    column_context: dict[str, Any],
    closure: dict[str, Any],
    joined_pages: list[dict[str, Any]],
) -> list[str]:
    """Require independent text, money/scale, and equation support.

    The raw PP-OCRv6 token retains either the complete digit sequence with
    mixed grouping punctuation or one intact grouped-integer prefix followed
    by OCR contamination. Fresh VietOCR on the identical crop must retain the
    same scale-zero integer (exactly, or as the same grouped leading prefix),
    the resolved lane must be monetary with consistent scale-zero peers, and
    the candidate must participate in an exact visible accounting equation.
    No bank, page, family, expected value, or manual pixel coordinate enters
    this decision.
    """

    def semantic_retains_grouped_prefix(surface: str, coefficient: int) -> bool:
        """Prove that one independent OCR surface starts with the same integer."""

        normalized = surface.strip()
        for end in range(1, len(normalized) + 1):
            if end < len(normalized) and normalized[end].isdigit():
                continue
            parsed_prefix = parse_visible_financial_numeric_token_v1(normalized[:end])
            if (
                parsed_prefix["classification"] == "SIGNED_NUMBER"
                and parsed_prefix["coefficient"] == coefficient
                and parsed_prefix["scale"] == 0
                and parsed_prefix["percentage_mark_present"] is False
            ):
                return True
        return False

    values = _axis_numeric_values(row_axis)
    hierarchy_frontier_certified_sample_ids: set[str] = set()
    if (
        closure.get("format_version") == "ACCOUNTING_SCOPED_HIERARCHICAL_TABLE_CLOSURE_V2"
        and type(closure.get("one_edit_exact_source_structural_proofs")) is dict
        and closure["one_edit_exact_source_structural_proofs"].get("format_version")
        in {
            one_edit_v1.HIERARCHY_FRONTIER_FORMAT_VERSION,
            one_edit_v1.RECURSIVE_HIERARCHY_FRONTIER_FORMAT_VERSION,
        }
    ):
        structural_evidence = {
            "authenticated_extreme_margin_furniture_evidence": closure[
                "authenticated_extreme_margin_furniture_evidence"
            ],
            "internal_unassigned_numeric_clusters": closure["internal_unassigned_numeric_clusters"],
            "numeric_sample_universe": closure["numeric_sample_universe"],
            "role_occurrences": closure["role_occurrences"],
            "row_axis": row_axis,
        }
        hierarchy_frontier_certified_sample_ids = (
            one_edit_v1.hierarchy_frontier_certified_sample_ids_v1(
                closure["one_edit_exact_source_structural_proofs"],
                structural_evidence=structural_evidence,
            )
        )
        result_cluster = one_edit_v1.hierarchy_frontier_result_cluster_v1(
            closure["one_edit_exact_source_structural_proofs"],
            structural_evidence=structural_evidence,
        )
        if result_cluster is not None:
            sample_by_id = {
                sample["sample_id"]: sample for sample in closure["numeric_sample_universe"]
            }
            values.extend(
                (None, sample_by_id[sample_id]) for sample_id in result_cluster["sample_ids"]
            )
    candidates = [
        (role, value)
        for role, value in values
        if value["parsed_token"]["classification"]
        in {
            "MIXED_GROUPED_INTEGER_CANDIDATE",
            "NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
        }
    ]
    if not candidates:
        return []
    semantic_by_sample = {
        line["sample_id"]: line["vietocr_text"] for page in joined_pages for line in page["lines"]
    }
    units = {
        item["column_ordinal"]: item
        for item in column_context.get("unit_axis", [])
        if type(item) is dict and type(item.get("column_ordinal")) is int
    }
    reasons = []
    exact_total_samples = {
        sample_id
        for candidate in closure.get("exact_total_candidates", [])
        for sample_id in candidate.get("sample_ids", [])
    }
    for role, candidate in candidates:
        sample_id = candidate["sample_id"]
        parsed = candidate["parsed_token"]
        candidate_kind = parsed["classification"]
        reason_prefix = (
            "MIXED_SEPARATOR"
            if candidate_kind == "MIXED_GROUPED_INTEGER_CANDIDATE"
            else "OCR_NOISE_SUFFIX"
        )
        semantic_surface = semantic_by_sample.get(sample_id, "")
        semantic = parse_visible_financial_numeric_token_v1(semantic_surface)
        independent_agrees = (
            semantic["classification"] == "SIGNED_NUMBER"
            and semantic["coefficient"] == parsed["coefficient"]
            and semantic["scale"] == 0
            and semantic["percentage_mark_present"] is False
        ) or (
            candidate_kind == "NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE"
            and semantic_retains_grouped_prefix(semantic_surface, parsed["coefficient"])
        )
        if not independent_agrees:
            reasons.append(reason_prefix + ":INDEPENDENT_SAME_CROP_READER_DISAGREES:" + sample_id)
        unit = units.get(candidate["column_ordinal"])
        if unit is None or unit.get("unit_kind") != "MONEY":
            reasons.append(reason_prefix + ":INTEGER_MONEY_UNIT_NOT_RESOLVED:" + sample_id)
        peers = [
            value["parsed_token"]
            for peer_role, value in values
            if value["sample_id"] != sample_id
            and value["column_ordinal"] == candidate["column_ordinal"]
            and (
                peer_role is not None
                or value["sample_id"] in exact_total_samples
                or value["sample_id"] in hierarchy_frontier_certified_sample_ids
            )
            and (
                value["parsed_token"]["classification"] in {"DASH_ZERO", "SIGNED_NUMBER"}
                or value["sample_id"] in hierarchy_frontier_certified_sample_ids
            )
        ]
        raw_signed_anchors = [
            value
            for _peer_role, value in values
            if value["column_ordinal"] == candidate["column_ordinal"]
            and value["parsed_token"]["classification"] in {"DASH_ZERO", "SIGNED_NUMBER"}
        ]
        if (
            len(peers) < 2
            or not raw_signed_anchors
            or any(
                peer["scale"] != 0 or peer["percentage_mark_present"] is not False for peer in peers
            )
        ):
            reasons.append(reason_prefix + ":SCALE_ZERO_LANE_PEERS_NOT_ESTABLISHED:" + sample_id)
        if not _mixed_candidate_has_accounting_corroboration(
            role=role,
            sample_id=sample_id,
            closure=closure,
            hierarchy_frontier_certified_sample_ids=(hierarchy_frontier_certified_sample_ids),
        ):
            reasons.append(reason_prefix + ":EXACT_VISIBLE_ACCOUNTING_CLOSURE_ABSENT:" + sample_id)
    return list(dict.fromkeys(reasons))


def _degraded_dash_consensus_reasons(
    *, row_axis: dict[str, Any], closure: dict[str, Any]
) -> list[str]:
    """Require exact accounting or a repeated same-page dash-glyph family.

    The pixel contract deliberately does not call a two- or three-pixel mark a
    dash.  The row-axis layer may provisionally admit it only when a clear dash
    exists in another lane of the same source row.  This final gate additionally
    requires either an exact visible accounting equation or a repeated clear
    dash family on the same rendered page.  The latter covers low-resolution
    scans where one horizontal dash rasterizes to a square, without accepting a
    lone dot: the same-row peer, component height, crop scale and at least four
    independent clear page peers must all agree.
    """

    def repeated_page_glyph_consensus(candidate: dict[str, Any]) -> bool:
        evidence = candidate.get("dash_evidence")
        if type(evidence) is not dict or type(evidence.get("glyph_metrics")) is not dict:
            return False
        metrics = evidence["glyph_metrics"]
        crop = evidence.get("crop_ref")
        bbox = metrics.get("component_bbox")
        if (
            type(crop) is not dict
            or type(bbox) is not list
            or len(bbox) != 4
            or any(type(item) is not int for item in bbox)
        ):
            return False
        height = bbox[3] - bbox[1]
        width = bbox[2] - bbox[0]
        peers = [
            item
            for item in row_axis["visible_dash_rescues"]
            if item.get("classification") == "VISIBLE_HORIZONTAL_DASH_GLYPH"
            and item.get("page_sequence") == candidate.get("page_sequence")
            and type(item.get("dash_evidence")) is dict
            and type(item["dash_evidence"].get("glyph_metrics")) is dict
            and type(item["dash_evidence"].get("crop_ref")) is dict
        ]
        same_row = next(
            (
                item
                for item in peers
                if item.get("role") == candidate.get("role")
                and item.get("column_ordinal")
                == candidate.get("supporting_peer_dash_column_ordinal")
            ),
            None,
        )
        if same_row is None:
            return False
        comparable = []
        height_tolerance = max(1, int(round(height * 0.34)))
        for peer in peers:
            peer_metrics = peer["dash_evidence"]["glyph_metrics"]
            peer_bbox = peer_metrics.get("component_bbox")
            peer_crop = peer["dash_evidence"]["crop_ref"]
            if (
                type(peer_bbox) is list
                and len(peer_bbox) == 4
                and all(type(item) is int for item in peer_bbox)
                and type(peer_crop.get("pixel_height")) is int
                and abs(peer_crop["pixel_height"] - crop.get("pixel_height", -1000)) <= 2
                and abs((peer_bbox[3] - peer_bbox[1]) - height) <= height_tolerance
            ):
                comparable.append(peer)
        same_metrics = same_row["dash_evidence"]["glyph_metrics"]
        same_bbox = same_metrics.get("component_bbox")
        if type(same_bbox) is not list or len(same_bbox) != 4:
            return False
        same_width = same_bbox[2] - same_bbox[0]
        return (
            len(comparable) >= 6
            and height > 0
            and width > 0
            and same_width > 0
            and width * 2 >= same_width
            and width <= same_width
        )

    roles_by_sample = {
        value["sample_id"]: row["role"] for row in row_axis["rows"] for value in row["values"]
    }
    reasons = []
    for rescue in row_axis["visible_dash_rescues"]:
        if (
            rescue["classification"] != "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE"
            or rescue["supporting_peer_dash_column_ordinal"] is None
        ):
            continue
        sample_id = rescue["region_id"]
        role = roles_by_sample.get(sample_id)
        if role is None or not (
            _mixed_candidate_has_accounting_corroboration(
                role=role,
                sample_id=sample_id,
                closure=closure,
            )
            or repeated_page_glyph_consensus(rescue)
        ):
            reasons.append("DEGRADED_DASH:EXACT_VISIBLE_ACCOUNTING_CLOSURE_ABSENT:" + sample_id)
    return list(dict.fromkeys(reasons))


def _candidate_population_signature(candidate: dict[str, Any]) -> dict[str, Any] | None:
    """Return exact period/unit/root-total lanes for safe region subsumption.

    A primary-statement summary can be a useful control for a richer note, but
    page order and role count alone cannot prove that both regions describe the
    same population.  The signature ignores evidence locators while preserving
    every typed semantic field that changes the accounting value.  The root
    must be a visible total already corroborated by its components; a merely
    derived root is not a source control and cannot authorize pruning.
    """

    closure = candidate.get("additive_closure")
    context = candidate.get("column_context")
    if type(closure) is not dict or type(context) is not dict:
        return None
    family_id = closure.get("family_id")
    resolved = closure.get("resolved_roles")
    period_axis = context.get("period_axis")
    unit_axis = context.get("unit_axis")
    if (
        type(family_id) is not str
        or not family_id
        or type(resolved) is not list
        or type(period_axis) is not list
        or type(unit_axis) is not list
        or not period_axis
        or len(period_axis) != len(unit_axis)
    ):
        return None
    roots = [record for record in resolved if record.get("role") == family_id]
    if len(roots) != 1 or roots[0].get("resolution_kind") not in {
        "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS",
        "VISIBLE_SOURCE_ROLE_ROUNDING_CORROBORATED_BY_COMPONENTS",
        "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS",
        "VISIBLE_TRAILING_TOTAL_ROUNDING_CORROBORATED_BY_COMPONENTS",
    }:
        return None
    values = roots[0].get("values")
    if type(values) is not list or not values:
        return None
    try:
        periods = sorted(
            (
                {
                    "column_ordinal": record["column_ordinal"],
                    "resolved_period": record["resolved_period"],
                }
                for record in period_axis
            ),
            key=lambda record: record["column_ordinal"],
        )
        units = sorted(
            (
                {
                    "column_ordinal": record["column_ordinal"],
                    "currency": record["currency"],
                    "magnitude_power10": record["magnitude_power10"],
                    "unit_kind": record["unit_kind"],
                }
                for record in unit_axis
            ),
            key=lambda record: record["column_ordinal"],
        )
        numeric_lanes = sorted(
            (
                {
                    "column_ordinal": record["column_ordinal"],
                    "number": canonical_clone_v1(record["number"]),
                }
                for record in values
            ),
            key=lambda record: record["column_ordinal"],
        )
    except (KeyError, TypeError):
        return None
    ordinals = [record["column_ordinal"] for record in numeric_lanes]
    if (
        not ordinals
        or ordinals != [record["column_ordinal"] for record in periods]
        or ordinals != [record["column_ordinal"] for record in units]
        or any(type(ordinal) is not int or ordinal < 0 for ordinal in ordinals)
        or ordinals != sorted(set(ordinals))
    ):
        return None
    return {
        "numeric_lanes": numeric_lanes,
        "period_axis": periods,
        "period_semantics": context.get("period_semantics"),
        "unit_axis": units,
    }


_V4_COARSE_INTERBANK_PROVISION_ROLE = "TOTAL_INTERBANK_PROVISION"
_V4_SPLIT_INTERBANK_PROVISION_PARENT_ROLES = {
    "INTERBANK_DEPOSIT_PROVISION": "INTERBANK_DEPOSIT_GROUP",
    "INTERBANK_LOAN_PROVISION": "INTERBANK_LOAN_GROUP",
}
_V4_INTERBANK_PROVISION_ROLES = {
    _V4_COARSE_INTERBANK_PROVISION_ROLE,
    *_V4_SPLIT_INTERBANK_PROVISION_PARENT_ROLES,
}
_V4_INTERBANK_PROVISION_CONTRIBUTION_TOKEN = "__V4_EXACT_INTERBANK_PROVISION_CONTRIBUTION__"
_V4_EXACT_VISIBLE_EQUATION_STATUSES = {
    "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
    "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
}
_V4_EXACT_EQUATION_STATUSES = {
    "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM",
    *_V4_EXACT_VISIBLE_EQUATION_STATUSES,
}


def _v4_resolved_number_axis(record: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    """Project one complete, typed resolved lane axis without its provenance."""

    values = record.get("values")
    if type(values) is not list or not values:
        return None
    axis = []
    for value in values:
        number = value.get("number") if type(value) is dict else None
        if (
            type(value) is not dict
            or type(value.get("column_ordinal")) is not int
            or type(number) is not dict
            or set(number) != {"coefficient", "percentage_mark_present", "scale"}
            or type(number.get("coefficient")) is not int
            or number.get("percentage_mark_present") is not False
            or type(number.get("scale")) is not int
            or number["scale"] < 0
        ):
            return None
        axis.append(
            {
                "column_ordinal": value["column_ordinal"],
                "number": canonical_clone_v1(number),
            }
        )
    axis.sort(key=lambda item: item["column_ordinal"])
    return axis if [item["column_ordinal"] for item in axis] == list(range(len(axis))) else None


def _v4_self_authenticated_mapping(
    value: Any,
    *,
    identity_field: str,
    identity_prefix: str,
) -> bool:
    """Verify one canonical envelope identity without weakening its exact payload."""

    if type(value) is not dict:
        return False
    try:
        material = canonical_clone_v1(value)
        identity = material.pop(identity_field, None)
        return type(identity) is str and identity == identity_prefix + canonical_json_sha256_v1(
            material
        )
    except (KeyError, TypeError, ValueError):
        return False


def _v4_authenticated_candidate_axes(
    candidate: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Bind selector inputs to their sealed closure, row, occurrence, and sample axes.

    The public sweep replay remains the source-authority boundary.  This private
    projection nevertheless must not compare two mutually consistent copies that
    are both detached from the candidate's authenticated axes.
    """

    closure = candidate.get("additive_closure")
    row_axis = candidate.get("row_axis")
    if (
        type(closure) is not dict
        or type(row_axis) is not dict
        or not _v4_self_authenticated_mapping(
            closure,
            identity_field="closure_id",
            identity_prefix="ashtcv2:closure:",
        )
        or not _v4_self_authenticated_mapping(
            row_axis,
            identity_field="row_axis_id",
            identity_prefix="afrav1:axis:",
        )
        or closure.get("row_axis_id") != row_axis.get("row_axis_id")
        or closure.get("family_id") != row_axis.get("family_id")
        or closure.get("status") != "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
        or row_axis.get("status") != "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    ):
        return None

    occurrence_axis_id = closure.get("occurrence_axis_id")
    occurrence_binding = closure.get("occurrence_axis_binding")
    try:
        closure_dependency_refs = scoped_v2._dependency_refs()  # noqa: SLF001
        occurrence_dependency_refs = occurrence_row_v2._dependency_refs()  # noqa: SLF001
    except (OSError, RuntimeError, TypeError, ValueError):
        return None
    if (
        type(occurrence_axis_id) is not str
        or not occurrence_axis_id.startswith("aforav2:axis:")
        or type(occurrence_binding) is not dict
        or set(occurrence_binding)
        != {
            "dependency_content_refs",
            "occurrence_axis_id",
            "topology_candidates_id",
            "topology_scan_id",
        }
        or occurrence_binding.get("occurrence_axis_id") != occurrence_axis_id
        or type(occurrence_binding.get("topology_candidates_id")) is not str
        or not occurrence_binding["topology_candidates_id"].startswith("aftcv2:result:")
        or type(occurrence_binding.get("topology_scan_id")) is not str
        or not occurrence_binding["topology_scan_id"].startswith("aftv1:scan:")
        or not same_typed_json_v1(closure.get("dependency_content_refs"), closure_dependency_refs)
        or not same_typed_json_v1(
            occurrence_binding.get("dependency_content_refs"),
            occurrence_dependency_refs,
        )
    ):
        return None

    occurrences = closure.get("role_occurrences")
    samples = closure.get("numeric_sample_universe")
    coverage = closure.get("coverage_receipt")
    if type(occurrences) is not list or type(samples) is not list or type(coverage) is not list:
        return None

    occurrence_by_id: dict[str, Mapping[str, Any]] = {}
    for occurrence in occurrences:
        label = occurrence.get("label_match") if type(occurrence) is dict else None
        occurrence_id = occurrence.get("occurrence_id") if type(occurrence) is dict else None
        role = occurrence.get("role") if type(occurrence) is dict else None
        if (
            type(occurrence) is not dict
            or type(label) is not dict
            or type(occurrence_id) is not str
            or not occurrence_id
            or occurrence_id in occurrence_by_id
            or type(role) is not str
            or not role
            or label.get("occurrence_id") != occurrence_id
            or label.get("role") != role
            or label.get("role_kind") != occurrence.get("role_kind")
            or label.get("scope_owner_occurrence_id") != occurrence.get("scope_owner_occurrence_id")
            or label.get("scope_owner_role") != occurrence.get("scope_owner_role")
            or not same_typed_json_v1(
                label.get("source_scope_binding"), occurrence.get("source_scope_binding")
            )
            or type(label.get("document_line_ordinal")) is not int
            or type(label.get("end_document_line_ordinal")) is not int
            or type(label.get("page_sequence")) is not int
            or type(label.get("role_occurrence_ordinal")) is not int
            or label["role_occurrence_ordinal"] < 0
            or occurrence_id
            != "aforav2:occurrence:"
            + canonical_json_sha256_v1(
                {
                    "document_line_ordinal": label["document_line_ordinal"],
                    "end_document_line_ordinal": label["end_document_line_ordinal"],
                    "page_sequence": label["page_sequence"],
                    "role": role,
                    "role_occurrence_ordinal": label["role_occurrence_ordinal"],
                }
            )
        ):
            return None
        occurrence_by_id[occurrence_id] = occurrence

    root_owner_ids = {
        occurrence.get("scope_owner_occurrence_id")
        for occurrence in occurrence_by_id.values()
        if occurrence.get("scope_owner_role") is None
    }
    if (
        len(root_owner_ids) != 1
        or type(next(iter(root_owner_ids))) is not str
        or not next(iter(root_owner_ids)).startswith("aforav2:root:")
    ):
        return None
    root_occurrence_id = next(iter(root_owner_ids))

    sample_by_id: dict[str, Mapping[str, Any]] = {}
    try:
        for sample in samples:
            validated = occurrence_row_v2._validate_numeric_sample_record(sample)  # noqa: SLF001
            sample_id = validated["sample_id"]
            if sample_id in sample_by_id:
                return None
            sample_by_id[sample_id] = validated
    except (KeyError, TypeError, ValueError):
        return None

    coverage_by_occurrence: dict[str, Mapping[str, Any]] = {}
    coverage_ids: set[str] = set()
    for receipt in coverage:
        coverage_id = receipt.get("coverage_id") if type(receipt) is dict else None
        if type(coverage_id) is not str or not coverage_id or coverage_id in coverage_ids:
            return None
        coverage_ids.add(coverage_id)
        if receipt.get("row_kind") != "ROLE_ROW":
            continue
        occurrence_id = receipt.get("occurrence_id")
        if (
            type(occurrence_id) is not str
            or occurrence_id not in occurrence_by_id
            or occurrence_id in coverage_by_occurrence
        ):
            return None
        coverage_by_occurrence[occurrence_id] = receipt

    return {
        "closure": closure,
        "coverage_by_occurrence": coverage_by_occurrence,
        "occurrence_by_id": occurrence_by_id,
        "root_occurrence_id": root_occurrence_id,
        "row_axis": row_axis,
        "sample_by_id": sample_by_id,
    }


def _v4_exact_visible_role_axis(
    record: Mapping[str, Any],
    authenticated_axes: Mapping[str, Any],
    *,
    expected_parent_role: str,
    expected_role_kind: str = "ADDITIVE_CHILD",
    expected_parent_role_kind: str = "STRUCTURAL_GROUP",
    expected_parent_occurrence_id: str | None = None,
    allow_family_root_scope_without_binding: bool = False,
) -> tuple[list[dict[str, Any]], str] | None:
    """Return one exact visible leaf bound to one authenticated row projection."""

    closure = authenticated_axes.get("closure")
    row_axis = authenticated_axes.get("row_axis")
    occurrence_by_id = authenticated_axes.get("occurrence_by_id")
    sample_by_id = authenticated_axes.get("sample_by_id")
    coverage_by_occurrence = authenticated_axes.get("coverage_by_occurrence")
    root_occurrence_id = authenticated_axes.get("root_occurrence_id")
    role = record.get("role")
    source = record.get("source")
    source_record = source.get("record") if type(source) is dict else None
    label_match = source_record.get("label_match") if type(source_record) is dict else None
    if (
        type(closure) is not dict
        or type(row_axis) is not dict
        or type(occurrence_by_id) is not dict
        or type(sample_by_id) is not dict
        or type(coverage_by_occurrence) is not dict
        or type(root_occurrence_id) is not str
        or type(role) is not str
        or type(expected_role_kind) is not str
        or not expected_role_kind
        or type(expected_parent_role_kind) is not str
        or not expected_parent_role_kind
        or (
            expected_parent_occurrence_id is not None
            and (
                type(expected_parent_occurrence_id) is not str or not expected_parent_occurrence_id
            )
        )
        or record.get("resolution_kind") != "VISIBLE_SOURCE_ROLE"
        or type(source) is not dict
        or source.get("kind") != "ROLE_ROW"
        or type(source_record) is not dict
        or source_record.get("role") != role
        or source_record.get("role_kind") != expected_role_kind
        or source_record.get("status") != "VISIBLE_VALUE_LANES_BOUND"
        or source_record.get("missing_column_ordinals") != []
        or type(label_match) is not dict
        or label_match.get("role") != role
        or label_match.get("role_kind") != expected_role_kind
        or type(label_match.get("occurrence_id")) is not str
        or not label_match["occurrence_id"]
        or type(label_match.get("scope_owner_occurrence_id")) is not str
        or not label_match["scope_owner_occurrence_id"]
        or type(label_match.get("match_kind")) is not str
        or not label_match["match_kind"].startswith("EXACT_")
        or type(label_match.get("document_line_ordinal")) is not int
        or type(label_match.get("end_document_line_ordinal")) is not int
        or type(label_match.get("page_sequence")) is not int
        or type(label_match.get("role_occurrence_ordinal")) is not int
        or label_match["role_occurrence_ordinal"] < 0
        or row_axis.get("status") != "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
        or type(row_axis.get("rows")) is not list
    ):
        return None

    occurrence_material = {
        "document_line_ordinal": label_match["document_line_ordinal"],
        "end_document_line_ordinal": label_match["end_document_line_ordinal"],
        "page_sequence": label_match["page_sequence"],
        "role": role,
        "role_occurrence_ordinal": label_match["role_occurrence_ordinal"],
    }
    if label_match["occurrence_id"] != "aforav2:occurrence:" + canonical_json_sha256_v1(
        occurrence_material
    ):
        return None

    def row_binding_projection(row: Mapping[str, Any]) -> dict[str, Any] | None:
        row_label = row.get("label_match")
        values = row.get("values")
        if (
            row.get("role") != role
            or row.get("role_kind") != expected_role_kind
            or row.get("status") != "VISIBLE_VALUE_LANES_BOUND"
            or row.get("missing_column_ordinals") != []
            or type(row_label) is not dict
            or row_label.get("role") != role
            or row_label.get("role_kind") != expected_role_kind
            or type(values) is not list
            or not values
        ):
            return None
        label_fields = (
            "document_line_ordinal",
            "end_document_line_ordinal",
            "match_kind",
            "occurrence_id",
            "page_sequence",
            "role",
            "role_kind",
            "scope_owner_occurrence_id",
            "scope_owner_role",
        )
        if any(field not in row_label for field in label_fields):
            return None
        projected_values = []
        for value in values:
            parsed = value.get("parsed_token") if type(value) is dict else None
            if (
                type(value) is not dict
                or type(value.get("column_ordinal")) is not int
                or type(value.get("sample_id")) is not str
                or not value["sample_id"]
                or type(parsed) is not dict
                or parsed.get("classification") not in {"DASH_ZERO", "SIGNED_NUMBER"}
                or type(parsed.get("coefficient")) is not int
                or parsed.get("percentage_mark_present") is not False
                or type(parsed.get("scale")) is not int
                or parsed["scale"] < 0
            ):
                return None
            projected_values.append(
                {
                    "column_ordinal": value["column_ordinal"],
                    "parsed_token": {
                        "classification": parsed["classification"],
                        "coefficient": parsed["coefficient"],
                        "percentage_mark_present": False,
                        "scale": parsed["scale"],
                    },
                    "sample_id": value["sample_id"],
                }
            )
        projected_values.sort(key=lambda value: value["column_ordinal"])
        if [value["column_ordinal"] for value in projected_values] != list(
            range(len(projected_values))
        ):
            return None
        return {
            "label_match": {field: canonical_clone_v1(row_label[field]) for field in label_fields},
            "missing_column_ordinals": [],
            "role": role,
            "role_kind": expected_role_kind,
            "status": "VISIBLE_VALUE_LANES_BOUND",
            "values": projected_values,
        }

    source_row_projection = row_binding_projection(source_record)
    matching_rows = [
        row for row in row_axis["rows"] if type(row) is dict and row.get("role") == role
    ]
    matching_row_projection = (
        row_binding_projection(matching_rows[0]) if len(matching_rows) == 1 else None
    )
    if (
        source_row_projection is None
        or matching_row_projection is None
        or not same_typed_json_v1(matching_row_projection, source_row_projection)
    ):
        return None

    occurrence_id = label_match["occurrence_id"]
    occurrence = occurrence_by_id.get(occurrence_id)
    receipt = coverage_by_occurrence.get(occurrence_id)
    if (
        type(occurrence) is not dict
        or occurrence.get("role") != role
        or occurrence.get("role_kind") != expected_role_kind
        or occurrence.get("has_bound_value_row") is not True
        or not same_typed_json_v1(occurrence.get("label_match"), label_match)
        or occurrence.get("scope_owner_occurrence_id") != label_match["scope_owner_occurrence_id"]
        or occurrence.get("scope_owner_role") != label_match.get("scope_owner_role")
        or type(receipt) is not dict
        or receipt.get("role") != role
        or receipt.get("occurrence_id") != occurrence_id
        or receipt.get("candidate_ordinal") is not None
        or receipt.get("row_kind") != "ROLE_ROW"
        or receipt.get("coverage_id") != f"ashtcv2:coverage:role:{occurrence_id}"
        or not same_typed_json_v1(receipt.get("source_record"), source_record)
        or not same_typed_json_v1(matching_rows[0], source_record)
    ):
        return None

    parent_occurrence_id = label_match["scope_owner_occurrence_id"]
    parent_role = label_match.get("scope_owner_role")
    family_id = closure.get("family_id")
    if expected_parent_role == family_id:
        if parent_role is not None or parent_occurrence_id != root_occurrence_id:
            return None
    else:
        parent = occurrence_by_id.get(parent_occurrence_id)
        child_line = label_match["document_line_ordinal"]
        preceding_parents = [
            occurrence
            for occurrence in occurrence_by_id.values()
            if occurrence.get("role") == expected_parent_role
            and occurrence.get("role_kind") == expected_parent_role_kind
            and type(occurrence.get("label_match")) is dict
            and occurrence["label_match"].get("end_document_line_ordinal", child_line + 1)
            <= child_line
        ]
        nearest_start = max(
            (
                occurrence["label_match"]["document_line_ordinal"]
                for occurrence in preceding_parents
            ),
            default=None,
        )
        nearest = [
            occurrence
            for occurrence in preceding_parents
            if occurrence["label_match"]["document_line_ordinal"] == nearest_start
        ]
        if (
            parent_role != expected_parent_role
            or type(parent) is not dict
            or parent.get("role") != expected_parent_role
            or parent.get("role_kind") != expected_parent_role_kind
            or len(nearest) != 1
            or nearest[0].get("occurrence_id") != parent_occurrence_id
            or (
                expected_parent_occurrence_id is not None
                and parent_occurrence_id != expected_parent_occurrence_id
            )
            or (
                expected_parent_occurrence_id is None
                and (
                    parent.get("scope_owner_role") is not None
                    or parent.get("scope_owner_occurrence_id") != root_occurrence_id
                )
            )
        ):
            return None

    source_values = source_record.get("values")
    if type(source_values) is not list or receipt.get("sample_ids") != [
        value.get("sample_id") for value in source_values if type(value) is dict
    ]:
        return None
    try:
        for value in source_values:
            expected_sample = occurrence_row_v2._numeric_universe_record(  # noqa: SLF001
                value,
                owner_kind="ROLE_OCCURRENCE",
                owner_id=occurrence_id,
            )
            if not same_typed_json_v1(
                sample_by_id.get(expected_sample["sample_id"]), expected_sample
            ):
                return None
    except (KeyError, TypeError, ValueError):
        return None

    scope_binding = label_match.get("source_scope_binding")
    if type(scope_binding) is dict:
        binding_material = canonical_clone_v1(scope_binding)
        binding_id = binding_material.pop("binding_id", None)
        if binding_id != "aforav2:scope-binding:" + canonical_json_sha256_v1(binding_material):
            return None
    if parent_role != expected_parent_role:
        if not (
            (
                allow_family_root_scope_without_binding
                and expected_parent_role == family_id
                and parent_role is None
                and parent_occurrence_id == root_occurrence_id
                and scope_binding is None
            )
            or (
                parent_role is None
                and type(scope_binding) is dict
                and scope_binding.get("status")
                == "REVIEWED_EXACT_SOURCE_SCOPE_TO_SCHEMA_ROLE_BINDING"
                and scope_binding.get("target_role") == role
                and scope_binding.get("source_scope_role") == expected_parent_role
            )
        ):
            return None
    elif type(scope_binding) is dict and (
        scope_binding.get("status") != "REVIEWED_EXACT_SOURCE_SCOPE_TO_SCHEMA_ROLE_BINDING"
        or scope_binding.get("target_role") != role
        or scope_binding.get("source_scope_role") != expected_parent_role
    ):
        return None

    def source_axis(values: Any) -> list[dict[str, Any]] | None:
        if type(values) is not list or not values:
            return None
        axis = []
        for value in values:
            parsed = value.get("parsed_token") if type(value) is dict else None
            if (
                type(value) is not dict
                or type(value.get("column_ordinal")) is not int
                or type(parsed) is not dict
                or parsed.get("classification") not in {"DASH_ZERO", "SIGNED_NUMBER"}
                or type(parsed.get("coefficient")) is not int
                or parsed.get("percentage_mark_present") is not False
                or type(parsed.get("scale")) is not int
                or parsed["scale"] < 0
                or (parsed["classification"] == "DASH_ZERO" and parsed["coefficient"] != 0)
            ):
                return None
            axis.append(
                {
                    "column_ordinal": value["column_ordinal"],
                    "number": {
                        "coefficient": parsed["coefficient"],
                        "percentage_mark_present": False,
                        "scale": parsed["scale"],
                    },
                }
            )
        axis.sort(key=lambda item: item["column_ordinal"])
        return axis if [item["column_ordinal"] for item in axis] == list(range(len(axis))) else None

    visible_axis = _v4_resolved_number_axis(record)
    direct_source_axis = source_axis(source_record.get("values"))
    if (
        visible_axis is None
        or direct_source_axis is None
        or not same_typed_json_v1(visible_axis, direct_source_axis)
    ):
        return None
    return visible_axis, occurrence_id


def _v4_exact_visible_trailing_result_axis(
    record: Mapping[str, Any],
    equation: Mapping[str, Any],
    authenticated_axes: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], int] | None:
    """Replay one selected visible trailing result against every sealed axis.

    A trailing total has no semantic occurrence ID, so it cannot use the
    ordinary role-row authenticator.  Bind it instead to the unique row-axis
    candidate, numeric-universe owner, coverage receipt, and selected equation
    evidence.  Arithmetic remains corroborative: no value is derived here.
    """

    closure = authenticated_axes.get("closure")
    row_axis = authenticated_axes.get("row_axis")
    sample_by_id = authenticated_axes.get("sample_by_id")
    role = record.get("role")
    source = record.get("source")
    source_record = source.get("record") if type(source) is dict else None
    candidate_ordinal = (
        source_record.get("candidate_ordinal") if type(source_record) is dict else None
    )
    values = source_record.get("values") if type(source_record) is dict else None
    if (
        type(closure) is not dict
        or type(row_axis) is not dict
        or type(sample_by_id) is not dict
        or type(role) is not str
        or not role
        or record.get("resolution_kind") != "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS"
        or type(source) is not dict
        or source.get("kind") != "TRAILING_VALUE_ROW"
        or type(source_record) is not dict
        or type(candidate_ordinal) is not int
        or candidate_ordinal < 0
        or source_record.get("status") != "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
        or source_record.get("missing_column_ordinals") != []
        or type(source_record.get("page_sequence")) is not int
        or type(values) is not list
        or not values
        or equation.get("result_role") != role
        or equation.get("status") != "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
        or equation.get("selected_trailing_candidate_ordinal") != candidate_ordinal
    ):
        return None

    source_axis = []
    sample_ids = []
    owner_id = f"aforav2:trailing:{candidate_ordinal}"
    try:
        for expected_ordinal, value in enumerate(values):
            parsed = value.get("parsed_token") if type(value) is dict else None
            sample_id = value.get("sample_id") if type(value) is dict else None
            if (
                type(value) is not dict
                or value.get("column_ordinal") != expected_ordinal
                or value.get("page_sequence") != source_record["page_sequence"]
                or type(sample_id) is not str
                or not sample_id
                or sample_id in sample_ids
                or type(parsed) is not dict
                or parsed.get("classification") not in {"DASH_ZERO", "SIGNED_NUMBER"}
                or type(parsed.get("coefficient")) is not int
                or parsed.get("percentage_mark_present") is not False
                or type(parsed.get("scale")) is not int
                or parsed["scale"] < 0
                or (parsed["classification"] == "DASH_ZERO" and parsed["coefficient"] != 0)
            ):
                return None
            expected_sample = occurrence_row_v2._numeric_universe_record(  # noqa: SLF001
                value,
                owner_kind="TRAILING_VALUE_ROW",
                owner_id=owner_id,
            )
            if not same_typed_json_v1(sample_by_id.get(sample_id), expected_sample):
                return None
            sample_ids.append(sample_id)
            source_axis.append(
                {
                    "column_ordinal": expected_ordinal,
                    "number": {
                        "coefficient": parsed["coefficient"],
                        "percentage_mark_present": False,
                        "scale": parsed["scale"],
                    },
                }
            )
    except (KeyError, TypeError, ValueError):
        return None

    trailing_rows = row_axis.get("trailing_value_rows")
    matching_rows = (
        [
            row
            for row in trailing_rows
            if type(row) is dict and row.get("candidate_ordinal") == candidate_ordinal
        ]
        if type(trailing_rows) is list
        else []
    )
    coverage = closure.get("coverage_receipt")
    matching_coverage = (
        [
            receipt
            for receipt in coverage
            if type(receipt) is dict
            and receipt.get("row_kind") == "TRAILING_VALUE_ROW"
            and receipt.get("candidate_ordinal") == candidate_ordinal
        ]
        if type(coverage) is list
        else []
    )
    selected_evidence = equation.get("trailing_candidate_evidence")
    matching_evidence = (
        [
            evidence
            for evidence in selected_evidence
            if type(evidence) is dict
            and evidence.get("candidate_ordinal") == candidate_ordinal
            and evidence.get("status") == "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE"
        ]
        if type(selected_evidence) is list
        else []
    )
    receipt = matching_coverage[0] if len(matching_coverage) == 1 else None
    evidence = matching_evidence[0] if len(matching_evidence) == 1 else None
    resolved_axis = _v4_resolved_number_axis(record)
    if (
        len(matching_rows) != 1
        or not same_typed_json_v1(matching_rows[0], source_record)
        or type(receipt) is not dict
        or receipt.get("coverage_id") != f"ashtcv2:coverage:trailing:{candidate_ordinal}"
        or receipt.get("disposition") != "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE"
        or receipt.get("occurrence_id") is not None
        or receipt.get("role") is not None
        or receipt.get("sample_ids") != sample_ids
        or not same_typed_json_v1(receipt.get("source_record"), source_record)
        or type(evidence) is not dict
        or evidence.get("sample_ids") != sample_ids
        or not same_typed_json_v1(evidence.get("source_record"), source_record)
        or resolved_axis is None
        or not same_typed_json_v1(resolved_axis, source_axis)
    ):
        return None
    return resolved_axis, candidate_ordinal


def _v4_canonical_exact_sum_axis(
    component_axes: Sequence[Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]] | None:
    """Add complete money lanes exactly and canonicalize only decimal scale."""

    if not component_axes or not component_axes[0]:
        return None
    lane_count = len(component_axes[0])
    if any(len(axis) != lane_count for axis in component_axes):
        return None
    result = []
    for lane in range(lane_count):
        records = [axis[lane] for axis in component_axes]
        if any(record.get("column_ordinal") != lane for record in records):
            return None
        numbers = [record.get("number") for record in records]
        if any(
            type(number) is not dict
            or set(number) != {"coefficient", "percentage_mark_present", "scale"}
            or type(number.get("coefficient")) is not int
            or number.get("percentage_mark_present") is not False
            or type(number.get("scale")) is not int
            or number["scale"] < 0
            for number in numbers
        ):
            return None
        scale = max(number["scale"] for number in numbers)
        coefficient = sum(
            number["coefficient"] * 10 ** (scale - number["scale"]) for number in numbers
        )
        while scale and coefficient % 10 == 0:
            coefficient //= 10
            scale -= 1
        result.append(
            {
                "column_ordinal": lane,
                "number": {
                    "coefficient": coefficient,
                    "percentage_mark_present": False,
                    "scale": scale,
                },
            }
        )
    return result


def _v4_exact_equation_holds(
    equation: Mapping[str, Any],
    resolved_by_role: Mapping[str, Mapping[str, Any]],
    expected_column_ordinals: Sequence[int],
) -> bool:
    """Recompute one claimed exact equation from its complete resolved lanes."""

    result_role = equation.get("result_role")
    component_roles = equation.get("component_roles_present")
    if (
        equation.get("status") not in _V4_EXACT_EQUATION_STATUSES
        or type(result_role) is not str
        or not result_role
        or type(component_roles) is not list
        or not component_roles
        or any(type(role) is not str or not role for role in component_roles)
        or len(component_roles) != len(set(component_roles))
        or result_role in component_roles
    ):
        return False
    result_axis = _v4_resolved_number_axis(resolved_by_role.get(result_role, {}))
    component_axes = [
        _v4_resolved_number_axis(resolved_by_role.get(role, {})) for role in component_roles
    ]
    if result_axis is None or any(axis is None for axis in component_axes):
        return False
    if any(
        [lane["column_ordinal"] for lane in axis] != list(expected_column_ordinals)
        for axis in [result_axis, *(axis for axis in component_axes if axis is not None)]
    ):
        return False
    canonical_result = _v4_canonical_exact_sum_axis([result_axis])
    canonical_components = _v4_canonical_exact_sum_axis(
        [axis for axis in component_axes if axis is not None]
    )
    return (
        canonical_result is not None
        and canonical_components is not None
        and same_typed_json_v1(canonical_result, canonical_components)
    )


def _v4_interbank_provision_projection(
    candidate: Mapping[str, Any], role_set: set[str]
) -> (
    tuple[
        str,
        list[dict[str, Any]],
        dict[str, list[dict[str, Any]]],
        tuple[str, ...],
    ]
    | None
):
    """Project either the one coarse provision or both exact parented leaves."""

    authenticated_axes = _v4_authenticated_candidate_axes(candidate)
    closure = authenticated_axes.get("closure") if authenticated_axes is not None else None
    resolved = closure.get("resolved_roles") if type(closure) is dict else None
    family_id = closure.get("family_id") if type(closure) is dict else None
    if (
        authenticated_axes is None
        or type(resolved) is not list
        or type(family_id) is not str
        or not family_id
    ):
        return None
    role_records: dict[str, Mapping[str, Any]] = {}
    for record in resolved:
        if type(record) is not dict or type(record.get("role")) is not str:
            return None
        role = record["role"]
        if role in role_records:
            return None
        role_records[role] = record
    observed = set(role_records) & _V4_INTERBANK_PROVISION_ROLES
    if observed != role_set & _V4_INTERBANK_PROVISION_ROLES:
        return None
    if not observed:
        return "NONE", [], {}, ()
    population = _candidate_population_signature(dict(candidate))
    population_lanes = population.get("numeric_lanes") if type(population) is dict else None
    if type(population_lanes) is not list or not population_lanes:
        return None
    expected_column_ordinals = [lane.get("column_ordinal") for lane in population_lanes]

    equations = closure.get("equations")
    global_equations = equations.get("global") if type(equations) is dict else None
    if type(global_equations) is not list:
        return None
    claimed_exact_equations = [
        equation
        for equation in global_equations
        if type(equation) is dict and equation.get("status") in _V4_EXACT_EQUATION_STATUSES
    ]
    if not claimed_exact_equations or any(
        not _v4_exact_equation_holds(equation, role_records, expected_column_ordinals)
        for equation in claimed_exact_equations
    ):
        return None

    def exact_group_reconciliation(result_role: str, required_component_roles: set[str]) -> bool:
        matches = []
        for equation in global_equations:
            component_roles = (
                equation.get("component_roles_present") if type(equation) is dict else None
            )
            if (
                type(equation) is dict
                and equation.get("result_role") == result_role
                and equation.get("status")
                in {
                    "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM",
                    "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
                }
                and type(component_roles) is list
                and all(type(role) is str and role for role in component_roles)
                and len(component_roles) == len(set(component_roles))
                and required_component_roles <= set(component_roles)
                and _v4_exact_equation_holds(equation, role_records, expected_column_ordinals)
            ):
                matches.append(equation)
        return len(matches) == 1

    if observed == {_V4_COARSE_INTERBANK_PROVISION_ROLE}:
        exact = _v4_exact_visible_role_axis(
            role_records[_V4_COARSE_INTERBANK_PROVISION_ROLE],
            authenticated_axes,
            expected_parent_role=family_id,
        )
        if (
            exact is None
            or family_id not in role_records
            or not exact_group_reconciliation(
                family_id,
                {
                    "INTERBANK_DEPOSIT_GROUP",
                    "INTERBANK_LOAN_GROUP",
                    _V4_COARSE_INTERBANK_PROVISION_ROLE,
                },
            )
        ):
            return None
        canonical = _v4_canonical_exact_sum_axis([exact[0]])
        if (
            canonical is None
            or [lane["column_ordinal"] for lane in canonical] != expected_column_ordinals
        ):
            return None
        return (
            "COARSE",
            canonical,
            {_V4_COARSE_INTERBANK_PROVISION_ROLE: exact[0]},
            (exact[1],),
        )

    split_roles = set(_V4_SPLIT_INTERBANK_PROVISION_PARENT_ROLES)
    if observed != split_roles or any(
        parent not in role_records for parent in _V4_SPLIT_INTERBANK_PROVISION_PARENT_ROLES.values()
    ):
        return None
    if any(
        not exact_group_reconciliation(parent, {role})
        for role, parent in _V4_SPLIT_INTERBANK_PROVISION_PARENT_ROLES.items()
    ) or not exact_group_reconciliation(
        family_id, set(_V4_SPLIT_INTERBANK_PROVISION_PARENT_ROLES.values())
    ):
        return None
    exact_split = {
        role: _v4_exact_visible_role_axis(
            record,
            authenticated_axes,
            expected_parent_role=parent,
        )
        for role, parent in _V4_SPLIT_INTERBANK_PROVISION_PARENT_ROLES.items()
        for record in [role_records[role]]
    }
    if any(value is None for value in exact_split.values()):
        return None
    if len({value[1] for value in exact_split.values() if value is not None}) != len(exact_split):
        return None
    split_axes = {role: value[0] for role, value in exact_split.items() if value is not None}
    canonical = _v4_canonical_exact_sum_axis(
        [split_axes[role] for role in _V4_SPLIT_INTERBANK_PROVISION_PARENT_ROLES]
    )
    return (
        (
            "SPLIT",
            canonical,
            split_axes,
            tuple(value[1] for value in exact_split.values() if value is not None),
        )
        if canonical is not None
        and [lane["column_ordinal"] for lane in canonical] == expected_column_ordinals
        else None
    )


def _v4_strict_role_richness_subset(
    candidate: Mapping[str, Any],
    other: Mapping[str, Any],
    candidate_roles: set[str],
    other_roles: set[str],
) -> bool:
    """Compare V4 role richness with one exact provision presentation equivalence."""

    if not ((candidate_roles | other_roles) & _V4_INTERBANK_PROVISION_ROLES):
        return candidate_roles < other_roles
    if _V4_INTERBANK_PROVISION_CONTRIBUTION_TOKEN in candidate_roles | other_roles:
        return False
    candidate_projection = _v4_interbank_provision_projection(candidate, candidate_roles)
    other_projection = _v4_interbank_provision_projection(other, other_roles)
    if (
        candidate_projection is None
        or other_projection is None
        or candidate_projection[0] == "NONE"
        or other_projection[0] == "NONE"
        or not same_typed_json_v1(candidate_projection[1], other_projection[1])
    ):
        return False
    candidate_occurrences = candidate_projection[3]
    other_occurrences = other_projection[3]
    if (
        len(candidate_occurrences) != len(set(candidate_occurrences))
        or len(other_occurrences) != len(set(other_occurrences))
        or set(candidate_occurrences) & set(other_occurrences)
    ):
        return False
    if candidate_projection[0] == other_projection[0] == "SPLIT" and not same_typed_json_v1(
        candidate_projection[2], other_projection[2]
    ):
        return False

    def normalized(roles: set[str], projection_kind: str) -> set[str]:
        normalized_roles = set(roles)
        if projection_kind == "COARSE":
            normalized_roles.remove(_V4_COARSE_INTERBANK_PROVISION_ROLE)
        normalized_roles.add(_V4_INTERBANK_PROVISION_CONTRIBUTION_TOKEN)
        return normalized_roles

    return normalized(candidate_roles, candidate_projection[0]) < normalized(
        other_roles, other_projection[0]
    )


def _candidate_role_richness_set(
    candidate: Mapping[str, Any], *, canonicalize_all_presentations: bool = False
) -> set[str] | None:
    """Return semantic roles after policy-scoped presentation canonicalization."""

    closure = candidate.get("additive_closure")
    resolved = closure.get("resolved_roles") if type(closure) is dict else None
    if type(resolved) is not list:
        return None if canonicalize_all_presentations else set()
    if canonicalize_all_presentations and (
        any(
            type(record) is not dict or type(record.get("role")) is not str or not record["role"]
            for record in resolved
        )
        or len([record["role"] for record in resolved])
        != len({record["role"] for record in resolved})
    ):
        return None
    roles = {
        record["role"]
        for record in resolved
        if type(record) is dict and type(record.get("role")) is str
    }
    family_id = closure.get("family_id")
    equations = closure.get("equations")
    global_equations = equations.get("global") if type(equations) is dict else None
    if type(family_id) is not str or type(global_equations) is not list:
        return None if canonicalize_all_presentations else roles
    if canonicalize_all_presentations:
        if not global_equations or any(type(equation) is not dict for equation in global_equations):
            return None
        result_roles = [equation.get("result_role") for equation in global_equations]
        if any(type(role) is not str or not role for role in result_roles) or len(
            result_roles
        ) != len(set(result_roles)):
            return None
        presentation_aliases: list[str] = []
        alias_results: dict[str, str] = {}
        for equation in global_equations:
            visible_roles = equation.get("visible_result_roles")
            if (
                type(visible_roles) is not list
                or any(type(role) is not str or not role for role in visible_roles)
                or len(visible_roles) != len(set(visible_roles))
            ):
                return None
            for role in visible_roles:
                if role != equation["result_role"]:
                    presentation_aliases.append(role)
                    alias_results[role] = equation["result_role"]
        if (
            len(presentation_aliases) != len(set(presentation_aliases))
            or set(presentation_aliases) & set(result_roles)
            or any(
                alias in roles and result_role not in roles
                for alias, result_role in alias_results.items()
            )
        ):
            return None
        return roles - set(presentation_aliases)
    root_equations = [
        equation
        for equation in global_equations
        if type(equation) is dict and equation.get("result_role") == family_id
    ]
    if len(root_equations) != 1 or type(root_equations[0].get("visible_result_roles")) is not list:
        return roles
    presentation_aliases = {
        role
        for role in root_equations[0]["visible_result_roles"]
        if type(role) is str and role != family_id
    }
    return roles - presentation_aliases


def _v4_ready_exact_component_detail_supersedes_visible_summary(
    summary: Mapping[str, Any],
    detail: Mapping[str, Any],
    summary_roles: set[str],
    detail_roles: set[str],
) -> bool:
    """Prove one READY detail is the authenticated expansion of a summary.

    A visible summary root is useful source authority, while a detailed note
    may derive that root from an exhaustive hierarchy.  A matching arithmetic
    total is not enough to choose the note: every terminal money row must be a
    sealed occurrence owned by the exact typed parent declared by the detail's
    equation graph.  This keeps identically named rows under different parents
    incomparable.
    """

    if (
        summary.get("reasons") != []
        or detail.get("reasons") != []
        or type(summary.get("candidate_ordinal")) is not int
        or type(detail.get("candidate_ordinal")) is not int
        or summary["candidate_ordinal"] == detail["candidate_ordinal"]
        or not summary_roles < detail_roles
        or (summary_roles | detail_roles) & _V4_INTERBANK_PROVISION_ROLES
    ):
        return False
    summary_axes = _v4_authenticated_candidate_axes(summary)
    detail_axes = _v4_authenticated_candidate_axes(detail)
    if summary_axes is None or detail_axes is None:
        return False
    summary_closure = summary_axes["closure"]
    detail_closure = detail_axes["closure"]
    family_id = summary_closure.get("family_id")
    if (
        type(family_id) is not str
        or not family_id
        or detail_closure.get("family_id") != family_id
        or summary_axes.get("root_occurrence_id") == detail_axes.get("root_occurrence_id")
    ):
        return False

    def unique_role_records(closure: Mapping[str, Any]) -> dict[str, Mapping[str, Any]] | None:
        records = closure.get("resolved_roles")
        if type(records) is not list or not records:
            return None
        result: dict[str, Mapping[str, Any]] = {}
        for record in records:
            role = record.get("role") if type(record) is dict else None
            if type(role) is not str or not role or role in result:
                return None
            result[role] = record
        return result

    def unique_global_equations(
        closure: Mapping[str, Any],
    ) -> dict[str, Mapping[str, Any]] | None:
        equations = closure.get("equations")
        global_equations = equations.get("global") if type(equations) is dict else None
        if type(global_equations) is not list or not global_equations:
            return None
        result: dict[str, Mapping[str, Any]] = {}
        for equation in global_equations:
            role = equation.get("result_role") if type(equation) is dict else None
            if type(role) is not str or not role or role in result:
                return None
            result[role] = equation
        return result

    summary_records = unique_role_records(summary_closure)
    detail_records = unique_role_records(detail_closure)
    summary_equations = unique_global_equations(summary_closure)
    detail_equations = unique_global_equations(detail_closure)
    summary_signature = _candidate_population_signature(dict(summary))
    if (
        summary_records is None
        or detail_records is None
        or summary_equations is None
        or detail_equations is None
        or summary_signature is None
    ):
        return False
    summary_root = summary_records.get(family_id)
    detail_root = detail_records.get(family_id)
    summary_root_equation = summary_equations.get(family_id)
    detail_root_equation = detail_equations.get(family_id)
    component_roles = (
        summary_root_equation.get("component_roles_present")
        if type(summary_root_equation) is dict
        else None
    )
    if (
        type(summary_root) is not dict
        or summary_root.get("resolution_kind") != "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS"
        or type(detail_root) is not dict
        or detail_root.get("resolution_kind") != "DERIVED_EXACT_COMPONENT_SUM"
        or type(component_roles) is not list
        or len(component_roles) < 2
        or any(type(role) is not str or not role for role in component_roles)
        or len(component_roles) != len(set(component_roles))
        or summary_root_equation.get("status")
        != "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
        or detail_root_equation is None
        or detail_root_equation.get("status") != "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM"
        or detail_root_equation.get("component_roles_present") != component_roles
        or not _v4_exact_equation_holds(
            summary_root_equation,
            summary_records,
            [lane["column_ordinal"] for lane in summary_signature["numeric_lanes"]],
        )
        or not _v4_exact_equation_holds(
            detail_root_equation,
            detail_records,
            [lane["column_ordinal"] for lane in summary_signature["numeric_lanes"]],
        )
        or not same_typed_json_v1(
            _v4_resolved_number_axis(detail_root), summary_signature["numeric_lanes"]
        )
    ):
        return False

    # Compare the detail's independently parsed period/unit header against the
    # summary without treating the detail's derived root as source authority.
    synthetic_detail = copy.deepcopy(dict(detail))
    synthetic_closure = synthetic_detail.get("additive_closure")
    synthetic_records = (
        synthetic_closure.get("resolved_roles") if type(synthetic_closure) is dict else None
    )
    if type(synthetic_records) is not list:
        return False
    synthetic_closure["resolved_roles"] = [
        record for record in synthetic_records if record.get("role") != family_id
    ] + [canonical_clone_v1(summary_root)]
    if not same_typed_json_v1(_candidate_population_signature(synthetic_detail), summary_signature):
        return False

    summary_occurrences: set[str] = set()
    for role in component_roles:
        summary_record = summary_records.get(role)
        detail_record = detail_records.get(role)
        if type(summary_record) is not dict or type(detail_record) is not dict:
            return False
        exact_summary = _v4_exact_visible_role_axis(
            summary_record,
            summary_axes,
            expected_parent_role=family_id,
            expected_role_kind="STRUCTURAL_GROUP",
            allow_family_root_scope_without_binding=True,
        )
        if exact_summary is None or not same_typed_json_v1(
            exact_summary[0], _v4_resolved_number_axis(detail_record)
        ):
            return False
        summary_occurrences.add(exact_summary[1])
    if len(summary_occurrences) != len(component_roles):
        return False

    expected_ordinals = [lane["column_ordinal"] for lane in summary_signature["numeric_lanes"]]
    tree_roles: set[str] = set()
    terminal_occurrences: dict[str, str] = {}
    active: set[str] = set()
    has_nested_terminal = False

    def authenticate_tree(role: str, parent_role: str | None) -> bool:
        nonlocal has_nested_terminal
        if role in active:
            return False
        record = detail_records.get(role)
        if type(record) is not dict:
            return False
        tree_roles.add(role)
        equation = detail_equations.get(role)
        components = equation.get("component_roles_present") if equation is not None else None
        if (
            type(equation) is dict
            and equation.get("status") in _V4_EXACT_EQUATION_STATUSES
            and type(components) is list
            and components
        ):
            if (
                any(type(component) is not str or not component for component in components)
                or len(components) != len(set(components))
                or role in components
                or not _v4_exact_equation_holds(equation, detail_records, expected_ordinals)
            ):
                return False
            active.add(role)
            accepted = all(authenticate_tree(component, role) for component in components)
            active.remove(role)
            return accepted
        if parent_role is None:
            return False
        exact_leaf = _v4_exact_visible_role_axis(
            record,
            detail_axes,
            expected_parent_role=parent_role,
        )
        if (
            exact_leaf is None
            or role in terminal_occurrences
            or exact_leaf[1] in set(terminal_occurrences.values())
        ):
            return False
        terminal_occurrences[role] = exact_leaf[1]
        has_nested_terminal = has_nested_terminal or parent_role != family_id
        return True

    if (
        not authenticate_tree(family_id, None)
        or not summary_roles < tree_roles
        or not tree_roles <= detail_roles
        or len(terminal_occurrences) < len(component_roles) + 1
        or not has_nested_terminal
        or summary_occurrences & set(terminal_occurrences.values())
    ):
        return False

    # Every resolved record outside the exhaustive additive tree must itself
    # have a narrow authenticated meaning.  This prevents an unrelated or
    # wrongly parented additive row from manufacturing role richness.  The only
    # admitted extras are a sealed nonadditive child of an already authenticated
    # terminal leaf, or a sealed visible presentation alias declared once by an
    # equation whose result is already in the tree.
    alias_results: dict[str, str] = {}
    for equation in detail_equations.values():
        result_role = equation.get("result_role")
        visible_roles = equation.get("visible_result_roles")
        if type(result_role) is not str or not result_role or type(visible_roles) is not list:
            return False
        for alias in visible_roles:
            if type(alias) is not str or not alias:
                return False
            if alias == result_role:
                continue
            if alias in alias_results:
                return False
            alias_results[alias] = result_role
    if detail_roles != set(detail_records) - set(alias_results):
        return False
    admitted_extra_occurrences: set[str] = set()
    for extra_role in set(detail_records) - tree_roles:
        extra_record = detail_records[extra_role]
        source = extra_record.get("source")
        source_record = source.get("record") if type(source) is dict else None
        label = source_record.get("label_match") if type(source_record) is dict else None
        role_kind = source_record.get("role_kind") if type(source_record) is dict else None
        exact_extra: tuple[list[dict[str, Any]], str] | None = None
        if role_kind == "NONADDITIVE_CHILD":
            parent_role = label.get("scope_owner_role") if type(label) is dict else None
            parent_occurrence_id = terminal_occurrences.get(parent_role)
            parent_occurrence = (
                detail_axes["occurrence_by_id"].get(parent_occurrence_id)
                if type(parent_occurrence_id) is str
                else None
            )
            if detail_equations.get(extra_role) is not None or type(parent_occurrence) is not dict:
                return False
            exact_extra = _v4_exact_visible_role_axis(
                extra_record,
                detail_axes,
                expected_parent_role=parent_role,
                expected_role_kind="NONADDITIVE_CHILD",
                expected_parent_role_kind=parent_occurrence.get("role_kind"),
                expected_parent_occurrence_id=parent_occurrence_id,
            )
        elif extra_role in alias_results:
            result_role = alias_results[extra_role]
            result_record = detail_records.get(result_role)
            if result_role not in tree_roles or role_kind not in {"STRUCTURAL_GROUP", "TOTAL"}:
                return False
            exact_extra = _v4_exact_visible_role_axis(
                extra_record,
                detail_axes,
                expected_parent_role=family_id,
                expected_role_kind=role_kind,
                allow_family_root_scope_without_binding=True,
            )
            if exact_extra is not None and not same_typed_json_v1(
                exact_extra[0], _v4_resolved_number_axis(result_record or {})
            ):
                return False
        if (
            exact_extra is None
            or exact_extra[1] in admitted_extra_occurrences
            or exact_extra[1] in terminal_occurrences.values()
            or exact_extra[1] in summary_occurrences
        ):
            return False
        admitted_extra_occurrences.add(exact_extra[1])
    return True


def _v4_ready_visible_correlated_detail_supersedes_visible_summary(
    summary: Mapping[str, Any],
    detail: Mapping[str, Any],
    summary_roles: set[str],
    detail_roles: set[str],
) -> bool:
    """Prove a visible-total detail is one exact expansion of a summary.

    This is intentionally independent of role-count and provision-presentation
    equivalence.  Both candidates retain visible root authority, while the
    detail must authenticate every recursive direct-frontier row, presentation
    total, and nonadditive memo row against its sealed occurrence axis.  A
    source parent plus one of its descendants can therefore never appear in the
    same additive frontier merely because the arithmetic happens to close.
    """

    if (
        summary.get("reasons") != []
        or detail.get("reasons") != []
        or type(summary.get("candidate_ordinal")) is not int
        or type(detail.get("candidate_ordinal")) is not int
        or summary["candidate_ordinal"] == detail["candidate_ordinal"]
        or not summary_roles < detail_roles
    ):
        return False
    summary_axes = _v4_authenticated_candidate_axes(summary)
    detail_axes = _v4_authenticated_candidate_axes(detail)
    if summary_axes is None or detail_axes is None:
        return False

    def unique_role_records(
        closure: Mapping[str, Any],
    ) -> dict[str, Mapping[str, Any]] | None:
        records = closure.get("resolved_roles")
        if type(records) is not list or not records:
            return None
        result: dict[str, Mapping[str, Any]] = {}
        for record in records:
            role = record.get("role") if type(record) is dict else None
            if type(role) is not str or not role or role in result:
                return None
            result[role] = record
        return result

    def unique_global_equations(
        closure: Mapping[str, Any],
    ) -> dict[str, Mapping[str, Any]] | None:
        equations = closure.get("equations")
        global_equations = equations.get("global") if type(equations) is dict else None
        if type(global_equations) is not list or not global_equations:
            return None
        result: dict[str, Mapping[str, Any]] = {}
        for equation in global_equations:
            role = equation.get("result_role") if type(equation) is dict else None
            if type(role) is not str or not role or role in result:
                return None
            result[role] = equation
        return result

    summary_closure = summary_axes["closure"]
    detail_closure = detail_axes["closure"]
    family_id = summary_closure.get("family_id")
    summary_records = unique_role_records(summary_closure)
    detail_records = unique_role_records(detail_closure)
    summary_equations = unique_global_equations(summary_closure)
    detail_equations = unique_global_equations(detail_closure)
    summary_signature = _candidate_population_signature(dict(summary))
    detail_signature = _candidate_population_signature(dict(detail))
    if (
        type(family_id) is not str
        or not family_id
        or detail_closure.get("family_id") != family_id
        or summary_axes.get("root_occurrence_id") == detail_axes.get("root_occurrence_id")
        or summary_records is None
        or detail_records is None
        or summary_equations is None
        or detail_equations is None
        or summary_signature is None
        or detail_signature is None
        or not same_typed_json_v1(summary_signature, detail_signature)
    ):
        return False
    expected_ordinals = [lane["column_ordinal"] for lane in summary_signature["numeric_lanes"]]

    summary_root_equation = summary_equations.get(family_id)
    detail_root_equation = detail_equations.get(family_id)
    top_roles = (
        summary_root_equation.get("component_roles_present")
        if type(summary_root_equation) is dict
        else None
    )
    if (
        type(top_roles) is not list
        or len(top_roles) < 2
        or any(type(role) is not str or not role for role in top_roles)
        or len(top_roles) != len(set(top_roles))
        or summary_roles != {family_id, *top_roles}
        or type(detail_root_equation) is not dict
        or detail_root_equation.get("component_roles_present") != top_roles
        or summary_root_equation.get("status") not in _V4_EXACT_VISIBLE_EQUATION_STATUSES
        or detail_root_equation.get("status") not in _V4_EXACT_VISIBLE_EQUATION_STATUSES
        or not _v4_exact_equation_holds(
            summary_root_equation,
            summary_records,
            expected_ordinals,
        )
        or not _v4_exact_equation_holds(
            detail_root_equation,
            detail_records,
            expected_ordinals,
        )
    ):
        return False
    if any(
        role not in detail_records
        or not same_typed_json_v1(
            _v4_resolved_number_axis(summary_records[role]),
            _v4_resolved_number_axis(detail_records[role]),
        )
        for role in summary_roles
    ):
        return False

    def declared_aliases(
        equations: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, str] | None:
        result: dict[str, str] = {}
        for result_role, equation in equations.items():
            visible_roles = equation.get("visible_result_roles")
            if (
                type(visible_roles) is not list
                or any(type(role) is not str or not role for role in visible_roles)
                or len(visible_roles) != len(set(visible_roles))
            ):
                return None
            for alias in visible_roles:
                if alias == result_role:
                    continue
                if alias in result:
                    return None
                result[alias] = result_role
        return result

    summary_aliases = declared_aliases(summary_equations)
    detail_aliases = declared_aliases(detail_equations)
    if summary_aliases is None or detail_aliases is None:
        return False

    def authenticate_correlated_result(
        *,
        role: str,
        parent_role: str | None,
        records: Mapping[str, Mapping[str, Any]],
        equations: Mapping[str, Mapping[str, Any]],
        aliases: Mapping[str, str],
        axes: Mapping[str, Any],
        consumed_occurrences: set[str],
        consumed_alias_roles: set[str],
    ) -> bool:
        record = records.get(role)
        equation = equations.get(role)
        source = record.get("source") if type(record) is dict else None
        source_record = source.get("record") if type(source) is dict else None
        source_role = source_record.get("role") if type(source_record) is dict else None
        if (
            type(record) is not dict
            or record.get("resolution_kind") != "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS"
            or type(equation) is not dict
            or equation.get("status") not in _V4_EXACT_VISIBLE_EQUATION_STATUSES
            or type(source_role) is not str
            or not source_role
        ):
            return False

        if source_role == role:
            expected_parent = family_id if parent_role is None else parent_role
            expected_kind = source_record.get("role_kind")
            visible_record = {
                "component_roles": [],
                "resolution_kind": "VISIBLE_SOURCE_ROLE",
                "role": role,
                "source": canonical_clone_v1(source),
                "values": canonical_clone_v1(record.get("values")),
            }
        else:
            if aliases.get(source_role) != role:
                return False
            visible_record = records.get(source_role)
            expected_parent = family_id if role == family_id else role
            if type(visible_record) is dict:
                expected_kind = visible_record.get("source", {}).get("record", {}).get("role_kind")
                if not same_typed_json_v1(record.get("source"), visible_record.get("source")):
                    return False
                consumed_alias_roles.add(source_role)
            else:
                # Closure may retain the exact visible presentation row only
                # as the corroborated structural result's source instead of
                # emitting a second resolved-role alias.  Authenticate that
                # row directly; never manufacture another accounting value.
                expected_kind = source_record.get("role_kind")
                visible_record = {
                    "component_roles": [],
                    "resolution_kind": "VISIBLE_SOURCE_ROLE",
                    "role": source_role,
                    "source": canonical_clone_v1(source),
                    "values": canonical_clone_v1(record.get("values")),
                }
        if expected_kind not in {"STRUCTURAL_GROUP", "TOTAL"}:
            return False
        exact = _v4_exact_visible_role_axis(
            visible_record,
            axes,
            expected_parent_role=expected_parent,
            expected_role_kind=expected_kind,
            allow_family_root_scope_without_binding=expected_parent == family_id,
        )
        if (
            exact is None
            and source_role == role
            and parent_role is not None
            and expected_kind == "STRUCTURAL_GROUP"
        ):
            # Some printed subgroup subtotals remain root-owned in the public
            # topology even though their own children are exact-owned and the
            # compiled equation places the subgroup under a preceding direct
            # parent.  Associate only for this selector proof: the parent row
            # must already be authenticated, the subgroup must lie on the same
            # page/root strictly after it and before the next visible sibling
            # in the parent's own direct frontier.  No occurrence is reparented.
            parent_record = records.get(parent_role)
            parent_source = parent_record.get("source") if type(parent_record) is dict else None
            parent_source_record = (
                parent_source.get("record") if type(parent_source) is dict else None
            )
            parent_label = (
                parent_source_record.get("label_match")
                if type(parent_source_record) is dict
                else None
            )
            child_label = source_record.get("label_match")
            parent_occurrence_id = (
                parent_label.get("occurrence_id") if type(parent_label) is dict else None
            )
            owner_equations = [
                candidate
                for candidate in equations.values()
                if type(candidate.get("component_roles_present")) is list
                and parent_role in candidate["component_roles_present"]
            ]
            sibling_labels = []
            if len(owner_equations) == 1:
                for sibling_role in owner_equations[0]["component_roles_present"]:
                    if sibling_role == parent_role:
                        continue
                    sibling = records.get(sibling_role)
                    sibling_source = sibling.get("source") if type(sibling) is dict else None
                    sibling_record = (
                        sibling_source.get("record") if type(sibling_source) is dict else None
                    )
                    sibling_label = (
                        sibling_record.get("label_match") if type(sibling_record) is dict else None
                    )
                    if type(sibling_label) is dict:
                        sibling_labels.append(sibling_label)
            later_sibling_lines = [
                sibling_label["document_line_ordinal"]
                for sibling_label in sibling_labels
                if type(parent_label) is dict
                and type(sibling_label.get("document_line_ordinal")) is int
                and sibling_label.get("page_sequence") == parent_label.get("page_sequence")
                and sibling_label["document_line_ordinal"]
                > parent_label.get("document_line_ordinal", sibling_label["document_line_ordinal"])
            ]
            if (
                type(parent_label) is dict
                and type(child_label) is dict
                and type(parent_occurrence_id) is str
                and parent_occurrence_id in consumed_occurrences
                and parent_source_record.get("role") == parent_role
                and parent_source_record.get("role_kind") == "STRUCTURAL_GROUP"
                and parent_label.get("scope_owner_role") is None
                and child_label.get("scope_owner_role") is None
                and parent_label.get("scope_owner_occurrence_id")
                == child_label.get("scope_owner_occurrence_id")
                and parent_label.get("page_sequence") == child_label.get("page_sequence")
                and type(parent_label.get("end_document_line_ordinal")) is int
                and type(child_label.get("document_line_ordinal")) is int
                and parent_label["end_document_line_ordinal"] < child_label["document_line_ordinal"]
                and later_sibling_lines
                and child_label["document_line_ordinal"] < min(later_sibling_lines)
            ):
                exact = _v4_exact_visible_role_axis(
                    visible_record,
                    axes,
                    expected_parent_role=family_id,
                    expected_role_kind=expected_kind,
                    allow_family_root_scope_without_binding=True,
                )
        if (
            exact is None
            or not same_typed_json_v1(exact[0], _v4_resolved_number_axis(record))
            or exact[1] in consumed_occurrences
        ):
            return False
        consumed_occurrences.add(exact[1])
        return True

    summary_consumed: set[str] = set()
    summary_consumed_aliases: set[str] = set()
    if not authenticate_correlated_result(
        role=family_id,
        parent_role=None,
        records=summary_records,
        equations=summary_equations,
        aliases=summary_aliases,
        axes=summary_axes,
        consumed_occurrences=summary_consumed,
        consumed_alias_roles=summary_consumed_aliases,
    ):
        return False
    for role in top_roles:
        source = summary_records[role].get("source")
        source_record = source.get("record") if type(source) is dict else None
        direct_role_kind = source_record.get("role_kind") if type(source_record) is dict else None
        if direct_role_kind not in {"ADDITIVE_CHILD", "STRUCTURAL_GROUP"}:
            return False
        exact = _v4_exact_visible_role_axis(
            summary_records[role],
            summary_axes,
            expected_parent_role=family_id,
            expected_role_kind=direct_role_kind,
            allow_family_root_scope_without_binding=True,
        )
        if exact is None or exact[1] in summary_consumed:
            return False
        summary_consumed.add(exact[1])

    detail_consumed: set[str] = set()
    detail_consumed_trailing: set[int] = set()
    detail_consumed_aliases: set[str] = set()
    terminal_occurrences: dict[str, str] = {}
    tree_roles: set[str] = set()
    internal_roles: set[str] = set()
    active: set[str] = set()

    def authenticate_tree(role: str, parent_role: str | None) -> bool:
        if role in active or role in tree_roles:
            return False
        record = detail_records.get(role)
        if type(record) is not dict:
            return False
        tree_roles.add(role)
        equation = detail_equations.get(role)
        components = equation.get("component_roles_present") if equation is not None else None
        if type(equation) is dict:
            if (
                equation.get("status") not in _V4_EXACT_EQUATION_STATUSES
                or type(components) is not list
                or not components
                or any(type(component) is not str or not component for component in components)
                or len(components) != len(set(components))
                or role in components
                or not _v4_exact_equation_holds(equation, detail_records, expected_ordinals)
            ):
                return False
            internal_roles.add(role)
            resolution_kind = record.get("resolution_kind")
            if resolution_kind == "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS":
                if not authenticate_correlated_result(
                    role=role,
                    parent_role=parent_role,
                    records=detail_records,
                    equations=detail_equations,
                    aliases=detail_aliases,
                    axes=detail_axes,
                    consumed_occurrences=detail_consumed,
                    consumed_alias_roles=detail_consumed_aliases,
                ):
                    return False
            elif resolution_kind == "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS":
                exact_trailing = _v4_exact_visible_trailing_result_axis(
                    record,
                    equation,
                    detail_axes,
                )
                if (
                    role != family_id
                    or parent_role is not None
                    or exact_trailing is None
                    or exact_trailing[1] in detail_consumed_trailing
                ):
                    return False
                detail_consumed_trailing.add(exact_trailing[1])
            elif (
                resolution_kind != "DERIVED_EXACT_COMPONENT_SUM" or record.get("source") is not None
            ):
                return False
            active.add(role)
            accepted = all(authenticate_tree(component, role) for component in components)
            active.remove(role)
            return accepted
        if parent_role is None or record.get("resolution_kind") != "VISIBLE_SOURCE_ROLE":
            return False
        exact = _v4_exact_visible_role_axis(
            record,
            detail_axes,
            expected_parent_role=parent_role,
            allow_family_root_scope_without_binding=parent_role == family_id,
        )
        if exact is None or exact[1] in detail_consumed:
            return False
        detail_consumed.add(exact[1])
        terminal_occurrences[role] = exact[1]
        return True

    if (
        not authenticate_tree(family_id, None)
        or set(detail_equations) != internal_roles
        or not summary_roles < tree_roles
        or not tree_roles <= detail_roles
    ):
        return False

    nonadditive_roles: set[str] = set()
    for extra_role in set(detail_records) - tree_roles - detail_consumed_aliases:
        extra_record = detail_records[extra_role]
        source = extra_record.get("source")
        source_record = source.get("record") if type(source) is dict else None
        label = source_record.get("label_match") if type(source_record) is dict else None
        parent_role = label.get("scope_owner_role") if type(label) is dict else None
        parent_occurrence_id = terminal_occurrences.get(parent_role)
        parent_occurrence = (
            detail_axes["occurrence_by_id"].get(parent_occurrence_id)
            if type(parent_occurrence_id) is str
            else None
        )
        if (
            source_record.get("role_kind") if type(source_record) is dict else None
        ) != "NONADDITIVE_CHILD" or type(parent_occurrence) is not dict:
            return False
        if detail_equations.get(extra_role) is not None:
            return False
        exact = _v4_exact_visible_role_axis(
            extra_record,
            detail_axes,
            expected_parent_role=parent_role,
            expected_role_kind="NONADDITIVE_CHILD",
            expected_parent_role_kind=parent_occurrence.get("role_kind"),
            expected_parent_occurrence_id=parent_occurrence_id,
        )
        if exact is None or exact[1] in detail_consumed:
            return False
        detail_consumed.add(exact[1])
        nonadditive_roles.add(extra_role)

    if (
        detail_roles != tree_roles | nonadditive_roles
        or set(summary_records) != summary_roles | summary_consumed_aliases
        or set(detail_records) != tree_roles | detail_consumed_aliases | nonadditive_roles
    ):
        return False

    def has_authenticated_numeric_sample_partition(axes: Mapping[str, Any]) -> bool:
        """Replay every row, subtotal, and non-accounting sample owner."""

        closure = axes["closure"]
        occurrence_binding = closure.get("occurrence_axis_binding")
        topology_candidates_id = (
            occurrence_binding.get("topology_candidates_id")
            if type(occurrence_binding) is dict
            else None
        )
        if type(topology_candidates_id) is not str:
            return False
        numeric_projection = dict(closure)
        numeric_projection["topology_candidates_id"] = topology_candidates_id
        try:
            occurrence_row_v2._validate_numeric_sample_universe(  # noqa: SLF001
                numeric_projection,
                axes["row_axis"],
                axes["occurrence_by_id"],
            )
            scoped_v2._validate_unlabeled_exact_subtotal_receipts(closure)  # noqa: SLF001
            scoped_v2._validate_numeric_sample_coverage(closure)  # noqa: SLF001
        except (AttributeError, IndexError, KeyError, RuntimeError, TypeError, ValueError):
            return False
        return True

    if not has_authenticated_numeric_sample_partition(
        summary_axes
    ) or not has_authenticated_numeric_sample_partition(detail_axes):
        return False

    def every_bound_row_consumed_once(
        axes: Mapping[str, Any],
        consumed_occurrences: set[str],
        consumed_trailing: set[int],
    ) -> bool:
        rows = axes["row_axis"].get("rows")
        trailing_rows = axes["row_axis"].get("trailing_value_rows")
        if type(rows) is not list or type(trailing_rows) is not list:
            return False
        row_occurrences = []
        sample_ids = []
        for row in rows:
            label = row.get("label_match") if type(row) is dict else None
            values = row.get("values") if type(row) is dict else None
            occurrence_id = label.get("occurrence_id") if type(label) is dict else None
            if (
                type(occurrence_id) is not str
                or not occurrence_id
                or type(values) is not list
                or any(
                    type(value) is not dict
                    or type(value.get("sample_id")) is not str
                    or not value["sample_id"]
                    for value in values
                )
            ):
                return False
            row_occurrences.append(occurrence_id)
            sample_ids.extend(value["sample_id"] for value in values)
        trailing_ordinals = []
        for row in trailing_rows:
            values = row.get("values") if type(row) is dict else None
            candidate_ordinal = row.get("candidate_ordinal") if type(row) is dict else None
            if (
                type(candidate_ordinal) is not int
                or candidate_ordinal < 0
                or type(values) is not list
                or any(
                    type(value) is not dict
                    or type(value.get("sample_id")) is not str
                    or not value["sample_id"]
                    for value in values
                )
            ):
                return False
            trailing_ordinals.append(candidate_ordinal)
            sample_ids.extend(value["sample_id"] for value in values)
        return (
            len(row_occurrences) == len(set(row_occurrences))
            and set(row_occurrences) == consumed_occurrences
            and set(axes["coverage_by_occurrence"]) == consumed_occurrences
            and len(trailing_ordinals) == len(set(trailing_ordinals))
            and set(trailing_ordinals) == consumed_trailing
            and len(sample_ids) == len(set(sample_ids))
            and set(sample_ids) <= set(axes["sample_by_id"])
        )

    return every_bound_row_consumed_once(
        summary_axes,
        summary_consumed,
        set(),
    ) and every_bound_row_consumed_once(
        detail_axes,
        detail_consumed,
        detail_consumed_trailing,
    )


def _threat_matches_ready_component_population(
    ready: Mapping[str, Any], threat: Mapping[str, Any]
) -> bool:
    """Directional same-population proof used only to preserve a veto.

    A detailed candidate with a schema-gap can lose its family root while
    still resolving the exact top-level deposit and loan populations printed
    by a READY summary.  Those exact component lanes may block laundering, but
    they never authorize the threat candidate itself.
    """

    ready_closure = ready.get("additive_closure")
    threat_closure = threat.get("additive_closure")
    if type(ready_closure) is not dict or type(threat_closure) is not dict:
        return False
    family_id = ready_closure.get("family_id")
    if type(family_id) is not str or threat_closure.get("family_id") != family_id:
        return False
    equations = ready_closure.get("equations")
    global_equations = equations.get("global") if type(equations) is dict else None
    family_equations = (
        [
            equation
            for equation in global_equations
            if type(equation) is dict and equation.get("result_role") == family_id
        ]
        if type(global_equations) is list
        else []
    )
    if len(family_equations) != 1:
        return False
    component_roles = family_equations[0].get("component_roles_present")
    if (
        type(component_roles) is not list
        or len(component_roles) < 2
        or any(type(role) is not str or not role for role in component_roles)
        or len(component_roles) != len(set(component_roles))
    ):
        return False

    def resolved_by_role(candidate_closure: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
        records = candidate_closure.get("resolved_roles")
        if type(records) is not list:
            return {}
        result = {
            record["role"]: record
            for record in records
            if type(record) is dict and type(record.get("role")) is str
        }
        return result if len(result) == len(records) else {}

    def value_axis(record: Mapping[str, Any] | None) -> list[dict[str, Any]] | None:
        values = record.get("values") if type(record) is dict else None
        if type(values) is not list or not values:
            return None
        try:
            axis = sorted(
                (
                    {
                        "column_ordinal": value["column_ordinal"],
                        "number": canonical_clone_v1(value["number"]),
                    }
                    for value in values
                ),
                key=lambda item: item["column_ordinal"],
            )
        except (KeyError, TypeError):
            return None
        ordinals = [item["column_ordinal"] for item in axis]
        return axis if ordinals == sorted(set(ordinals)) else None

    def source_row_value_axis(record: Mapping[str, Any]) -> list[dict[str, Any]] | None:
        values = record.get("values")
        if type(values) is not list or not values:
            return None
        try:
            axis = sorted(
                (
                    {
                        "column_ordinal": value["column_ordinal"],
                        "number": {
                            "coefficient": value["parsed_token"]["coefficient"],
                            "percentage_mark_present": value["parsed_token"][
                                "percentage_mark_present"
                            ],
                            "scale": value["parsed_token"]["scale"],
                        },
                    }
                    for value in values
                    if value["parsed_token"]["classification"] == "SIGNED_NUMBER"
                ),
                key=lambda item: item["column_ordinal"],
            )
        except (KeyError, TypeError):
            return None
        ordinals = [item["column_ordinal"] for item in axis]
        return (
            axis
            if len(axis) == len(values)
            and ordinals == list(range(len(axis)))
            and all(
                type(item["number"]["coefficient"]) is int
                and type(item["number"]["scale"]) is int
                and item["number"]["scale"] >= 0
                and item["number"]["percentage_mark_present"] is False
                for item in axis
            )
            else None
        )

    def exact_component_sum_matches_root(
        component_axes: Sequence[Sequence[Mapping[str, Any]]],
        root_axis: Sequence[Mapping[str, Any]],
    ) -> bool:
        if not component_axes or any(len(axis) != len(root_axis) for axis in component_axes):
            return False
        for lane, root_value in enumerate(root_axis):
            numbers = [axis[lane]["number"] for axis in component_axes]
            root_number = root_value["number"]
            if (
                any(
                    axis[lane]["column_ordinal"] != root_value["column_ordinal"]
                    for axis in component_axes
                )
                or any(number.get("percentage_mark_present") is not False for number in numbers)
                or root_number.get("percentage_mark_present") is not False
                or any(type(number.get("coefficient")) is not int for number in numbers)
                or any(
                    type(number.get("scale")) is not int or number["scale"] < 0
                    for number in numbers
                )
                or type(root_number.get("coefficient")) is not int
                or type(root_number.get("scale")) is not int
                or root_number["scale"] < 0
            ):
                return False
            common_scale = max(root_number["scale"], *(number["scale"] for number in numbers))
            component_sum = sum(
                number["coefficient"] * 10 ** (common_scale - number["scale"]) for number in numbers
            )
            printed_root = root_number["coefficient"] * 10 ** (common_scale - root_number["scale"])
            if component_sum != printed_root:
                return False
        return True

    ready_resolved = resolved_by_role(ready_closure)
    threat_resolved = resolved_by_role(threat_closure)
    ready_signature = _candidate_population_signature(dict(ready))
    if ready_signature is None:
        return False
    threat_context = dict(threat)
    synthetic_threat = copy.deepcopy(threat_context)
    # Reuse the closed period/unit parser without letting a missing threat root
    # become authorization: temporarily compare against the READY visible root.
    threat_records = synthetic_threat["additive_closure"].get("resolved_roles")
    ready_root = ready_resolved.get(family_id)
    if type(threat_records) is not list or type(ready_root) is not dict:
        return False
    synthetic_threat["additive_closure"]["resolved_roles"] = [
        record for record in threat_records if record.get("role") != family_id
    ] + [canonical_clone_v1(ready_root)]
    threat_signature = _candidate_population_signature(synthetic_threat)
    if threat_signature is None or not same_typed_json_v1(ready_signature, threat_signature):
        return False
    ready_component_axes = {role: value_axis(ready_resolved.get(role)) for role in component_roles}
    if any(axis is None for axis in ready_component_axes.values()):
        return False
    matched_roles = {
        role
        for role, ready_values in ready_component_axes.items()
        if (threat_values := value_axis(threat_resolved.get(role))) is not None
        and same_typed_json_v1(ready_values, threat_values)
    }
    unmatched_roles = [role for role in component_roles if role not in matched_roles]
    selected_component_axes = {role: ready_component_axes[role] for role in matched_roles}
    if unmatched_roles:
        # A schema-gap can make exactly one detailed top-level group unresolved
        # while its complete printed subtotal remains as one unowned trailing
        # row.  Use that row only as a directional population witness: one
        # other top-level role must already match, the row must uniquely match
        # the missing READY component, and it must not be the family root.
        row_axis = threat.get("row_axis")
        trailing_rows = row_axis.get("trailing_value_rows") if type(row_axis) is dict else None
        if (
            len(unmatched_roles) != 1
            or not matched_roles
            or type(trailing_rows) is not list
            or len(trailing_rows) != 1
            or trailing_rows[0].get("status") != "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
            or trailing_rows[0].get("missing_column_ordinals") != []
        ):
            return False
        trailing_axis = source_row_value_axis(trailing_rows[0])
        missing_role = unmatched_roles[0]
        if (
            trailing_axis is None
            or same_typed_json_v1(trailing_axis, ready_signature["numeric_lanes"])
            or not same_typed_json_v1(trailing_axis, ready_component_axes[missing_role])
        ):
            return False
        selected_component_axes[missing_role] = trailing_axis
    if set(selected_component_axes) != set(component_roles):
        return False
    if exact_component_sum_matches_root(
        [selected_component_axes[role] for role in component_roles],
        ready_signature["numeric_lanes"],
    ):
        return True
    return (
        family_equations[0].get("status")
        in {
            "VISIBLE_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
            "VISIBLE_TRAILING_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
        }
        and type(family_equations[0].get("rounding_evidence")) is list
        and any(
            type(evidence) is dict
            and evidence.get("status") == "ROUNDING_BOUND_SATISFIED_ALL_LANES"
            for evidence in family_equations[0]["rounding_evidence"]
        )
    )


def _select_candidate_evidence(
    candidate_evidence: list[dict[str, Any]], evaluation_spec: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    ready = [candidate for candidate in candidate_evidence if not candidate["reasons"]]
    canonicalize_all_presentations = _is_scoped_evaluation_policy(evaluation_spec)
    if (
        ready
        and _is_scoped_evaluation_policy(evaluation_spec)
        and evaluation_spec.get("candidate_selection_policy")
        == "SAME_POPULATION_STRICT_ROLE_SUPERSET_WITH_EXACT_PERIOD_UNIT_ROOT_TOTAL"
    ):
        source_gap_tokens = {
            "OFF_LANE_NUMERIC_SOURCE_ONLY_VETO",
            "ONE_EDIT_COEXTENSIVE_SOURCE_OR_OWNER_SCHEMA_INELIGIBLE",
            "ONE_EDIT_ROLE_OR_SCOPE_MATCH_SCHEMA_INELIGIBLE",
            "SOURCE_ONLY_AMBIGUOUS_TOUCHING_WRAPPED_LABEL",
            "SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO",
            "SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE",
        }

        def pages(candidate: Mapping[str, Any]) -> str:
            row_axis = candidate.get("row_axis")
            rows = row_axis.get("rows") if type(row_axis) is dict else None
            page_axis = (
                sorted(
                    {
                        row.get("label_match", {}).get("page_sequence")
                        for row in rows
                        if type(row) is dict
                        and type(row.get("label_match", {}).get("page_sequence")) is int
                    }
                )
                if type(rows) is list
                else []
            )
            return ",".join(map(str, page_axis)) if page_axis else "UNKNOWN"

        blockers = []
        for threat in candidate_evidence:
            gap_reasons = [
                reason
                for reason in threat["reasons"]
                if any(token in reason for token in source_gap_tokens)
            ]
            margin_render_reasons = [
                reason
                for reason in threat["reasons"]
                if re.fullmatch(
                    re.escape(occurrence_row_v2._EXTREME_MARGIN_RENDER_REASON_PREFIX)
                    + r"[1-9][0-9]{0,8}",
                    reason,
                )
            ]
            threat_signature = _candidate_population_signature(threat)
            if not gap_reasons:
                continue
            threat_roles = _candidate_role_richness_set(
                threat,
                canonicalize_all_presentations=canonicalize_all_presentations,
            )
            if threat_roles is None:
                matching_ready = [
                    admitted
                    for admitted in ready
                    if (
                        (
                            threat_signature is not None
                            and (admitted_signature := _candidate_population_signature(admitted))
                            is not None
                            and same_typed_json_v1(admitted_signature, threat_signature)
                        )
                        or _threat_matches_ready_component_population(admitted, threat)
                    )
                ]
                blockers.extend(
                    "COMPATIBLE_CANDIDATE_NUMERIC_SCHEMA_GAP_VETO:"
                    f"READY_CANDIDATE_{admitted['candidate_ordinal'] + 1}:"
                    f"THREAT_CANDIDATE_{threat['candidate_ordinal'] + 1}:"
                    f"THREAT_PAGES_{pages(threat)}:{reason}"
                    for admitted in matching_ready
                    for reason in gap_reasons
                )
                if matching_ready:
                    blockers.extend(
                        f"CANDIDATE_{threat['candidate_ordinal'] + 1}:{reason}"
                        for reason in margin_render_reasons
                    )
                continue
            matched_threat = False
            for admitted in ready:
                admitted_signature = _candidate_population_signature(admitted)
                admitted_roles = _candidate_role_richness_set(
                    admitted,
                    canonicalize_all_presentations=canonicalize_all_presentations,
                )
                full_root_population_match = (
                    threat_signature is not None
                    and admitted_signature is not None
                    and admitted_roles is not None
                    and threat_roles is not None
                    and admitted_roles <= threat_roles
                    and same_typed_json_v1(admitted_signature, threat_signature)
                )
                if not full_root_population_match and not (
                    admitted_signature is not None
                    and _threat_matches_ready_component_population(admitted, threat)
                ):
                    continue
                if admitted_signature is None:
                    # Defensive clarity: both compatibility routes require one
                    # authenticated visible READY root population.
                    continue
                matched_threat = True
                blockers.extend(
                    "COMPATIBLE_CANDIDATE_NUMERIC_SCHEMA_GAP_VETO:"
                    f"READY_CANDIDATE_{admitted['candidate_ordinal'] + 1}:"
                    f"THREAT_CANDIDATE_{threat['candidate_ordinal'] + 1}:"
                    f"THREAT_PAGES_{pages(threat)}:{reason}"
                    for reason in gap_reasons
                )
            if matched_threat:
                blockers.extend(
                    f"CANDIDATE_{threat['candidate_ordinal'] + 1}:{reason}"
                    for reason in margin_render_reasons
                )
        if blockers:
            return None, list(dict.fromkeys(blockers))
    if len(ready) > 1 and evaluation_spec["closure_policy"] in {
        "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE",
        "SCOPED_HIERARCHICAL_EXHAUSTIVE_CORROBORATE_OR_DERIVE",
    }:
        if evaluation_spec.get("candidate_selection_policy") == (
            "SAME_POPULATION_STRICT_ROLE_SUPERSET_WITH_EXACT_PERIOD_UNIT_ROOT_TOTAL"
        ):
            role_sets = [
                _candidate_role_richness_set(
                    candidate,
                    canonicalize_all_presentations=canonicalize_all_presentations,
                )
                for candidate in ready
            ]
            population_signatures = [
                _candidate_population_signature(candidate) for candidate in ready
            ]
            ready = [
                candidate
                for index, candidate in enumerate(ready)
                if not any(
                    other_index != index
                    and role_sets[index] is not None
                    and other is not None
                    and (
                        (
                            canonicalize_all_presentations
                            and _v4_ready_visible_correlated_detail_supersedes_visible_summary(
                                candidate,
                                ready[other_index],
                                role_sets[index],
                                other,
                            )
                        )
                        or (
                            (
                                (
                                    population_signatures[index] is not None
                                    and population_signatures[other_index] is not None
                                    and same_typed_json_v1(
                                        population_signatures[index],
                                        population_signatures[other_index],
                                    )
                                )
                                or (
                                    canonicalize_all_presentations
                                    and population_signatures[index] is not None
                                    and population_signatures[other_index] is None
                                    and _v4_ready_exact_component_detail_supersedes_visible_summary(
                                        candidate,
                                        ready[other_index],
                                        role_sets[index],
                                        other,
                                    )
                                )
                            )
                            and (
                                _v4_strict_role_richness_subset(
                                    candidate,
                                    ready[other_index],
                                    role_sets[index],
                                    other,
                                )
                                if canonicalize_all_presentations
                                else role_sets[index] < other
                            )
                        )
                    )
                    for other_index, other in enumerate(role_sets)
                )
            ]
        else:
            role_sets = [
                {record["role"] for record in candidate["additive_closure"]["resolved_roles"]}
                for candidate in ready
            ]
            ready = [
                candidate
                for index, candidate in enumerate(ready)
                if not any(role_sets[index] < other for other in role_sets)
            ]
    if len(ready) == 1:
        return ready[0], []
    if len(candidate_evidence) == 1:
        selected = candidate_evidence[0]
        return selected, selected["reasons"]
    return None, (
        ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]
        if ready
        else [
            f"CANDIDATE_{candidate['candidate_ordinal'] + 1}:{reason}"
            for candidate in candidate_evidence
            for reason in candidate["reasons"]
        ]
    )


def _one_edit_authority_pages_v1(
    joined_pages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Expose both OCR channels on the identical selected full-page line axis."""

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
        for page in joined_pages
    ]


def _selected_one_edit_public_replay_input_v1(
    *,
    authority_pages_sha256: str,
    evaluation_spec: Any,
    family_spec: Any,
    receipt: Mapping[str, Any],
    selected: Mapping[str, Any],
    selected_topology_region: Mapping[str, Any],
) -> dict[str, str]:
    visible_dash_rescues = selected.get("column_context_visible_dash_rescues", ())
    if type(visible_dash_rescues) is not tuple:
        raise _error("selected V4 public replay lost its dash-rescue tuple")
    return {
        "additive_closure_sha256": canonical_json_sha256_v1(selected.get("additive_closure")),
        "authority_pages_sha256": authority_pages_sha256,
        "column_context_sha256": canonical_json_sha256_v1(selected.get("column_context")),
        "evaluation_spec_sha256": canonical_json_sha256_v1(evaluation_spec),
        "family_spec_sha256": canonical_json_sha256_v1(family_spec),
        "receipt_sha256": canonical_json_sha256_v1(receipt),
        "row_axis_sha256": canonical_json_sha256_v1(selected.get("row_axis")),
        "selected_topology_region_sha256": canonical_json_sha256_v1(selected_topology_region),
        "visible_dash_rescues_sha256": one_edit_v1._visible_dash_rescues_sha256_v1(  # noqa: SLF001
            visible_dash_rescues
        ),
    }


def _retain_selected_one_edit_public_replay_handoff_v1(
    prepared_public_replay_cache: dict[str, Any] | None,
    *,
    candidate: Mapping[str, Any],
    joined_pages: list[dict[str, Any]],
    family_spec: dict[str, Any],
    evaluation_spec: dict[str, Any],
    selected_topology_region: Mapping[str, Any],
) -> None:
    """Retain one projection that just ran on exact same-turn authorities."""

    if prepared_public_replay_cache is None:
        return
    if type(prepared_public_replay_cache) is not dict:
        raise _error("selected V4 public-replay handoff cache shape drifted")
    persisted = candidate.get("one_edit_exact_source_structural_proofs")
    try:
        receipt = one_edit_v1.validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(
            persisted
        )
    except one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error as exc:
        raise _error("selected V4 public-replay handoff receipt drifted") from exc
    authority_pages = _one_edit_authority_pages_v1(joined_pages)
    authority_pages_sha256 = canonical_json_sha256_v1(authority_pages)
    if (
        receipt["family_id"] != family_spec["family_id"]
        or receipt["input_binding"]["document_pages_sha256"] != authority_pages_sha256
        or receipt["input_binding"]["family_spec_sha256"] != canonical_json_sha256_v1(family_spec)
        or receipt["input_binding"]["selected_topology_region_sha256"]
        != canonical_json_sha256_v1(selected_topology_region)
    ):
        raise _error("selected V4 public-replay handoff input binding drifted")
    input_sha256 = canonical_json_sha256_v1(
        _selected_one_edit_public_replay_input_v1(
            authority_pages_sha256=authority_pages_sha256,
            evaluation_spec=evaluation_spec,
            family_spec=family_spec,
            receipt=receipt,
            selected=candidate,
            selected_topology_region=selected_topology_region,
        )
    )
    receipt_sha256 = canonical_json_sha256_v1(receipt)
    existing = prepared_public_replay_cache.get(input_sha256)
    if existing is not None:
        if (
            type(existing) is not _PreparedSelectedOneEditPublicReplayV1
            or existing.seal is not _PREPARED_SELECTED_ONE_EDIT_PUBLIC_REPLAY_SEAL
            or existing.input_sha256 != input_sha256
            or existing.receipt_sha256 != receipt_sha256
        ):
            raise _error("selected V4 public-replay handoff cache binding drifted")
        return
    prepared_public_replay_cache[input_sha256] = _PreparedSelectedOneEditPublicReplayV1(
        input_sha256=input_sha256,
        receipt_sha256=receipt_sha256,
        seal=_PREPARED_SELECTED_ONE_EDIT_PUBLIC_REPLAY_SEAL,
    )


def _selected_v4_one_edit_authority_v1(
    selected: dict[str, Any] | None,
    *,
    joined_pages: list[dict[str, Any]],
    family_spec: dict[str, Any],
    topology_candidates: dict[str, Any] | None,
    evaluation_spec: dict[str, Any] | None = None,
    prepared_source_exact_axis_cache: dict[tuple[str, str], Any] | None = None,
    prepared_public_replay_cache: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Gate only the downstream-selected V4 candidate, never a discarded one."""

    if selected is None or topology_candidates is None or selected.get("row_axis") is None:
        return None, []
    ordinal = selected.get("candidate_ordinal")
    if type(ordinal) is not int or not 0 <= ordinal < len(topology_candidates["regions"]):
        raise _error("selected V4 candidate lost its pre-pruning topology identity")
    persisted = selected.get("one_edit_exact_source_structural_proofs")
    if type(persisted) is not dict:
        raise _error("selected V4 candidate lost its occurrence exact-source proof")
    try:
        receipt = one_edit_v1.validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(
            persisted
        )
    except one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error as exc:
        raise _error("selected V4 one-edit exact authority drifted") from exc
    selected_topology_region = topology_candidates["regions"][ordinal]
    authority_pages = _one_edit_authority_pages_v1(joined_pages)
    authority_pages_sha256 = canonical_json_sha256_v1(authority_pages)
    if (
        receipt["family_id"] != family_spec["family_id"]
        or receipt["input_binding"]["document_pages_sha256"] != authority_pages_sha256
        or receipt["input_binding"]["family_spec_sha256"] != canonical_json_sha256_v1(family_spec)
        or receipt["input_binding"]["selected_topology_region_sha256"]
        != canonical_json_sha256_v1(selected_topology_region)
    ):
        raise _error("selected V4 one-edit exact authority input binding drifted")
    public_replay_input_sha256 = canonical_json_sha256_v1(
        _selected_one_edit_public_replay_input_v1(
            authority_pages_sha256=authority_pages_sha256,
            evaluation_spec=evaluation_spec,
            family_spec=family_spec,
            receipt=receipt,
            selected=selected,
            selected_topology_region=selected_topology_region,
        )
    )
    receipt_sha256 = canonical_json_sha256_v1(receipt)
    if prepared_public_replay_cache is not None:
        if type(prepared_public_replay_cache) is not dict:
            raise _error("selected V4 public-replay cache shape drifted")
        prepared_replay = prepared_public_replay_cache.get(public_replay_input_sha256)
        if prepared_replay is not None:
            if (
                type(prepared_replay) is not _PreparedSelectedOneEditPublicReplayV1
                or prepared_replay.seal is not _PREPARED_SELECTED_ONE_EDIT_PUBLIC_REPLAY_SEAL
                or prepared_replay.input_sha256 != public_replay_input_sha256
                or prepared_replay.receipt_sha256 != receipt_sha256
            ):
                raise _error("selected V4 public-replay cache binding drifted")
            return canonical_clone_v1(receipt), canonical_clone_v1(receipt["unresolved_reasons"])
    try:
        canonical_expanded = one_edit_v1._canonical_expanded_occurrence_region_v1(  # noqa: SLF001
            one_edit_v1._pages_with_occurrence_geometry_v1(authority_pages),  # noqa: SLF001
            family_spec,
            selected_topology_region,
        )
        rebuilt_source = one_edit_v1.build_accounting_family_one_edit_exact_authority_v1(
            authority_pages,
            family_spec,
            selected_topology_region,
            canonical_expanded,
            _prepared_source_exact_axis_cache=prepared_source_exact_axis_cache,
        )
        if receipt["format_version"] in {
            one_edit_v1.PARENT_FRONTIER_FORMAT_VERSION,
            one_edit_v1.HIERARCHY_FRONTIER_FORMAT_VERSION,
            one_edit_v1.RECURSIVE_HIERARCHY_FRONTIER_FORMAT_VERSION,
        }:
            closure = selected.get("additive_closure")
            column_context = selected.get("column_context")
            visible_dash_rescues = selected.get("column_context_visible_dash_rescues", ())
            if (
                type(closure) is not dict
                or type(column_context) is not dict
                or type(evaluation_spec) is not dict
                or type(visible_dash_rescues) is not tuple
            ):
                raise _error("selected V4 parent-frontier authority lost structural evidence")
            selected_lane_unit_kinds = _resolved_lane_unit_kinds(evaluation_spec, column_context)
            structural_evidence = {
                "authenticated_extreme_margin_furniture_evidence": closure[
                    "authenticated_extreme_margin_furniture_evidence"
                ],
                "internal_unassigned_numeric_clusters": closure[
                    "internal_unassigned_numeric_clusters"
                ],
                "numeric_sample_universe": closure["numeric_sample_universe"],
                "role_occurrences": closure["role_occurrences"],
                "row_axis": selected["row_axis"],
            }
            if receipt["format_version"] == one_edit_v1.PARENT_FRONTIER_FORMAT_VERSION:
                rebuilt = (
                    one_edit_v1.project_accounting_family_one_edit_parent_frontier_authority_v1(
                        rebuilt_source,
                        structural_evidence,
                        column_context,
                        authority_pages,
                        family_spec,
                        selected_topology_region,
                        column_context_document_pages=joined_pages,
                        period_semantics=evaluation_spec.get("period_semantics"),
                        expected_lane_unit_kinds=selected_lane_unit_kinds,
                        visible_dash_rescues=visible_dash_rescues,
                    )
                )
            else:
                rebuilt = (
                    one_edit_v1.project_accounting_family_one_edit_hierarchy_frontier_authority_v1(
                        rebuilt_source,
                        structural_evidence,
                        column_context,
                        authority_pages,
                        family_spec,
                        selected_topology_region,
                        evaluation_spec.get("hierarchical_closure_spec"),
                        column_context_document_pages=joined_pages,
                        period_semantics=evaluation_spec.get("period_semantics"),
                        expected_lane_unit_kinds=selected_lane_unit_kinds,
                        visible_dash_rescues=visible_dash_rescues,
                    )
                )
        else:
            rebuilt = rebuilt_source
    except one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error as exc:
        raise _error(f"selected V4 one-edit exact authority replay failed:{exc}") from exc
    if not same_typed_json_v1(receipt, rebuilt):
        raise _error("selected V4 one-edit exact authority differs from occurrence proof")
    if prepared_public_replay_cache is not None:
        prepared_public_replay_cache[public_replay_input_sha256] = (
            _PreparedSelectedOneEditPublicReplayV1(
                input_sha256=public_replay_input_sha256,
                receipt_sha256=receipt_sha256,
                seal=_PREPARED_SELECTED_ONE_EDIT_PUBLIC_REPLAY_SEAL,
            )
        )
    return rebuilt, canonical_clone_v1(rebuilt["unresolved_reasons"])


def _build_column_context_for_evaluation_v1(
    row_axis: dict[str, Any],
    joined_pages: list[dict[str, Any]],
    family_spec: dict[str, Any],
    evaluation_spec: dict[str, Any],
    *,
    visible_dash_rescues: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], list[str]]:
    """Resolve exactly one declared lane layout without family/layout routing."""

    if evaluation_spec["format_version"] != EVALUATION_SPEC_FORMAT_V5:
        lane_unit_kinds = evaluation_spec["expected_lane_unit_kinds"]
        context = column_context_v1._build_accounting_family_column_context_from_authenticated_row_axis_v1(
            row_axis,
            joined_pages,
            family_spec,
            period_semantics=evaluation_spec["period_semantics"],
            expected_lane_unit_kinds=lane_unit_kinds,
            visible_dash_rescues=visible_dash_rescues,
        )
        return context, canonical_clone_v1(lane_unit_kinds)

    resolved_contexts = []
    for lane_unit_kinds in _lane_unit_kind_alternatives(evaluation_spec):
        proposed_context = column_context_multilevel_v2._build_accounting_family_column_context_multilevel_from_authenticated_row_axis_v2(
            row_axis,
            joined_pages,
            family_spec,
            period_semantics=evaluation_spec["period_semantics"],
            expected_lane_unit_kinds=lane_unit_kinds,
            visible_dash_rescues=visible_dash_rescues,
        )
        if proposed_context["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY":
            resolved_contexts.append((proposed_context, lane_unit_kinds))
    if len(resolved_contexts) != 1:
        raise _error("exactly one declared lane-unit alternative must resolve per candidate")
    context, lane_unit_kinds = resolved_contexts[0]
    return context, canonical_clone_v1(lane_unit_kinds)


def _candidate_local_render_snapshots_v1(
    joined_pages: list[dict[str, Any]],
    topology_region: Mapping[str, Any],
    render_snapshots: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    candidate_pages = _selected_topology_pages_v1(
        joined_pages,
        {"regions": [topology_region]},
    )
    return tuple(
        render for render in render_snapshots if render.get("physical_page") in candidate_pages
    )


def _candidate_occurrence_axis_cache_input_v1(
    *,
    joined_pages: list[dict[str, Any]],
    family_spec: dict[str, Any],
    topology_scan: dict[str, Any],
    topology_region: Mapping[str, Any],
    occurrence_row_axis_policy: Mapping[str, Any],
    topology_candidates: Mapping[str, Any],
    prepared_topology_binding: Any,
    selected_snapshot: Mapping[str, Any] | None,
    prepared_snapshot: Any,
    render_snapshots: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    render_axis = []
    for render in render_snapshots:
        if (
            type(render) is not dict
            or type(render.get("physical_page")) is not int
            or type(render.get("render_id")) is not str
            or type(render.get("render_ref")) is not dict
        ):
            raise _error("candidate occurrence cache render binding drifted")
        render_axis.append(
            {
                "physical_page": render["physical_page"],
                "render_id": render["render_id"],
                "render_ref": render["render_ref"],
            }
        )
    return {
        "document_pages_sha256": canonical_json_sha256_v1(joined_pages),
        "family_spec_sha256": canonical_json_sha256_v1(family_spec),
        "occurrence_row_axis_policy_sha256": canonical_json_sha256_v1(occurrence_row_axis_policy),
        "prepared_snapshot_context_sha256": getattr(
            prepared_snapshot,
            "prepared_context_sha256",
            None,
        ),
        "prepared_topology_binding_sha256": getattr(
            prepared_topology_binding,
            "prepared_context_sha256",
            None,
        ),
        "render_axis": render_axis,
        "selected_snapshot_id": (
            selected_snapshot.get("snapshot_id") if type(selected_snapshot) is dict else None
        ),
        "topology_candidates_id": topology_candidates.get("result_id"),
        "topology_region_sha256": canonical_json_sha256_v1(topology_region),
        "topology_scan_id": topology_scan.get("scan_id"),
    }


def _build_or_reopen_candidate_occurrence_axis_v1(
    *,
    joined_pages: list[dict[str, Any]],
    family_spec: dict[str, Any],
    topology_scan: dict[str, Any],
    topology_region: dict[str, Any],
    occurrence_row_axis_policy: dict[str, Any],
    topology_candidates: dict[str, Any],
    prepared_topology_binding: Any,
    selected_snapshot: dict[str, Any] | None,
    prepared_snapshot: Any,
    prepared_source_exact_axis_cache: dict[tuple[str, str], Any] | None,
    render_snapshots: tuple[dict[str, Any], ...],
    prepared_candidate_occurrence_axis_cache: dict[str, Any] | None,
) -> dict[str, Any]:
    if prepared_candidate_occurrence_axis_cache is None:
        return occurrence_row_v2._build_accounting_family_occurrence_row_axis_from_authenticated_topology_scan_v2(
            joined_pages,
            family_spec,
            topology_scan,
            topology_region,
            occurrence_row_axis_policy,
            topology_candidates=topology_candidates,
            prepared_topology_binding=prepared_topology_binding,
            selected_snapshot=selected_snapshot,
            prepared_snapshot=prepared_snapshot,
            prepared_source_exact_axis_cache=prepared_source_exact_axis_cache,
            render_snapshots=render_snapshots,
        )
    if type(prepared_candidate_occurrence_axis_cache) is not dict:
        raise _error("candidate occurrence-axis cache shape drifted")
    input_sha256 = canonical_json_sha256_v1(
        _candidate_occurrence_axis_cache_input_v1(
            joined_pages=joined_pages,
            family_spec=family_spec,
            topology_scan=topology_scan,
            topology_region=topology_region,
            occurrence_row_axis_policy=occurrence_row_axis_policy,
            topology_candidates=topology_candidates,
            prepared_topology_binding=prepared_topology_binding,
            selected_snapshot=selected_snapshot,
            prepared_snapshot=prepared_snapshot,
            render_snapshots=render_snapshots,
        )
    )
    prepared_axis = prepared_candidate_occurrence_axis_cache.get(input_sha256)
    if prepared_axis is not None:
        if (
            type(prepared_axis) is not _PreparedV4CandidateOccurrenceAxisV1
            or prepared_axis.seal is not _PREPARED_V4_CANDIDATE_OCCURRENCE_AXIS_SEAL
            or prepared_axis.input_sha256 != input_sha256
            or type(prepared_axis.payload) is not bytes
        ):
            raise _error("candidate occurrence-axis cache identity drifted")
        try:
            parsed_axis = json.loads(prepared_axis.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("candidate occurrence-axis cache payload drifted") from exc
        if (
            type(parsed_axis) is not dict
            or canonical_json_bytes_v1(parsed_axis) != prepared_axis.payload
            or canonical_json_sha256_v1(parsed_axis) != prepared_axis.occurrence_axis_sha256
            or parsed_axis.get("occurrence_axis_id") != prepared_axis.occurrence_axis_id
        ):
            raise _error("candidate occurrence-axis cache content drifted")
        try:
            return occurrence_row_v2._validate_result(parsed_axis)  # noqa: SLF001
        except ValueError as exc:
            raise _error("candidate occurrence-axis cache replay drifted") from exc
    occurrence_axis = occurrence_row_v2._build_accounting_family_occurrence_row_axis_from_authenticated_topology_scan_v2(
        joined_pages,
        family_spec,
        topology_scan,
        topology_region,
        occurrence_row_axis_policy,
        topology_candidates=topology_candidates,
        prepared_topology_binding=prepared_topology_binding,
        selected_snapshot=selected_snapshot,
        prepared_snapshot=prepared_snapshot,
        prepared_source_exact_axis_cache=prepared_source_exact_axis_cache,
        render_snapshots=render_snapshots,
    )
    payload = canonical_json_bytes_v1(occurrence_axis)
    prepared_candidate_occurrence_axis_cache[input_sha256] = _PreparedV4CandidateOccurrenceAxisV1(
        input_sha256=input_sha256,
        occurrence_axis_id=occurrence_axis["occurrence_axis_id"],
        occurrence_axis_sha256=canonical_json_sha256_v1(occurrence_axis),
        payload=payload,
        seal=_PREPARED_V4_CANDIDATE_OCCURRENCE_AXIS_SEAL,
    )
    return occurrence_axis


def _candidate_evidence_from_joined_pages(
    *,
    joined_pages: list[dict[str, Any]],
    topology_scan: dict[str, Any],
    family_spec: dict[str, Any],
    evaluation_spec: dict[str, Any],
    render_snapshots: tuple[dict[str, Any], ...],
    selected_snapshot: dict[str, Any] | None = None,
    topology_candidates: dict[str, Any] | None = None,
    prepared_topology_bindings: tuple[Any, ...] = (),
    prepared_snapshot: Any = None,
    prepared_source_exact_axis_cache: dict[tuple[str, str], Any] | None = None,
    prepared_candidate_occurrence_axis_cache: dict[str, Any] | None = None,
    prepared_public_replay_cache: dict[str, Any] | None = None,
    runtime_telemetry: dict[str, int | float] | None = None,
) -> list[dict[str, Any]]:
    is_v4 = _is_scoped_evaluation_policy(evaluation_spec)
    if is_v4:
        topology_pages = row_axis_v1._topology_pages(joined_pages)
        if prepared_topology_bindings:
            if topology_candidates is None:
                raise _error("prepared candidate bindings lost their V2 topology envelope")
        elif topology_candidates is None:
            topology_candidates = (
                topology_candidates_v2.build_accounting_family_topology_candidates_v2(
                    topology_pages,
                    family_spec,
                )
            )
        else:
            topology_candidates = (
                topology_candidates_v2.validate_accounting_family_topology_candidates_replay_v2(
                    topology_candidates,
                    topology_pages,
                    family_spec,
                )
            )
        if (
            topology_candidates["input_binding"]["legacy_topology_scan_id"]
            != topology_scan["scan_id"]
        ):
            raise _error("V4 topology candidates differ from their legacy scan binding")
        topology_regions = topology_candidates["regions"]
        if prepared_topology_bindings and len(prepared_topology_bindings) != len(topology_regions):
            raise _error("prepared candidate binding axis differs from the V2 regions")
    else:
        if topology_candidates is not None or prepared_topology_bindings or prepared_snapshot:
            raise _error("pre-pruning topology candidates require evaluation V4")
        topology_regions = topology_scan["regions"]
    candidate_evidence = []
    _telemetry_add(runtime_telemetry, "candidate_count", len(topology_regions))
    for candidate_ordinal, topology_region in enumerate(topology_regions):
        one_edit_frontier_projection_performed = False
        candidate_render_snapshots = _candidate_local_render_snapshots_v1(
            joined_pages,
            topology_region,
            render_snapshots,
        )
        prepared_binding = (
            prepared_topology_bindings[candidate_ordinal] if prepared_topology_bindings else None
        )
        try:
            if is_v4:
                base_occurrence_axis = _build_or_reopen_candidate_occurrence_axis_v1(
                    joined_pages=joined_pages,
                    family_spec=family_spec,
                    topology_scan=topology_scan,
                    topology_region=topology_region,
                    occurrence_row_axis_policy=evaluation_spec["occurrence_row_axis_policy"],
                    topology_candidates=topology_candidates,
                    prepared_topology_binding=prepared_binding,
                    selected_snapshot=selected_snapshot,
                    prepared_snapshot=prepared_snapshot,
                    prepared_source_exact_axis_cache=prepared_source_exact_axis_cache,
                    render_snapshots=candidate_render_snapshots,
                    prepared_candidate_occurrence_axis_cache=(
                        prepared_candidate_occurrence_axis_cache
                    ),
                )
                _telemetry_add(runtime_telemetry, "occurrence_axis_build_count", 1)
                base_row_axis = base_occurrence_axis["row_axis"]
            else:
                base_row_axis = row_axis_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
                    joined_pages,
                    family_spec,
                    topology_scan,
                    topology_region,
                )
            dash_rescues = _visible_dash_rescue_inputs(
                joined_pages=joined_pages,
                row_axis=base_row_axis,
                render_snapshots=candidate_render_snapshots,
                require_unique_role_page_owner=is_v4,
            )
            if is_v4:
                if dash_rescues:
                    occurrence_axis = occurrence_row_v2._build_accounting_family_occurrence_row_axis_from_authenticated_topology_scan_v2(
                        joined_pages,
                        family_spec,
                        topology_scan,
                        topology_region,
                        evaluation_spec["occurrence_row_axis_policy"],
                        topology_candidates=topology_candidates,
                        prepared_topology_binding=prepared_binding,
                        selected_snapshot=selected_snapshot,
                        prepared_snapshot=prepared_snapshot,
                        prepared_source_exact_axis_cache=prepared_source_exact_axis_cache,
                        render_snapshots=candidate_render_snapshots,
                        visible_dash_rescues=dash_rescues,
                    )
                    _telemetry_add(runtime_telemetry, "occurrence_axis_build_count", 1)
                else:
                    occurrence_axis = base_occurrence_axis
                    _telemetry_add(runtime_telemetry, "occurrence_base_reuse_count", 1)
                row_axis = occurrence_axis["row_axis"]
                one_edit_exact_source_structural_proofs = occurrence_axis[
                    "one_edit_exact_source_structural_proofs"
                ]
            else:
                occurrence_axis = None
                one_edit_exact_source_structural_proofs = None
                row_axis = (
                    row_axis_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
                        joined_pages,
                        family_spec,
                        topology_scan,
                        topology_region,
                        visible_dash_rescues=dash_rescues,
                    )
                    if dash_rescues
                    else base_row_axis
                )
        except ValueError as exc:
            candidate_evidence.append(
                {
                    "additive_closure": None,
                    "candidate_ordinal": candidate_ordinal,
                    "column_context": None,
                    "reasons": [f"ROW_AXIS_ERROR:{type(exc).__name__}:{exc}"],
                    "row_axis": None,
                }
            )
            continue
        try:
            column_context, selected_lane_unit_kinds = _build_column_context_for_evaluation_v1(
                row_axis,
                joined_pages,
                family_spec,
                evaluation_spec,
                visible_dash_rescues=dash_rescues,
            )
        except ValueError as exc:
            candidate_evidence.append(
                {
                    "additive_closure": None,
                    "candidate_ordinal": candidate_ordinal,
                    "column_context": None,
                    "reasons": [f"COLUMN_CONTEXT_ERROR:{type(exc).__name__}:{exc}"],
                    "row_axis": row_axis,
                    "one_edit_exact_source_structural_proofs": (
                        one_edit_exact_source_structural_proofs
                    ),
                }
            )
            continue
        try:
            parent_frontier_projection_required = any(
                type(check) is dict
                and check.get("match_scope") == "FAMILY_PARENT"
                and check.get("status") not in occurrence_row_v2._ONE_EDIT_AUTHORITY_BOUND_STATUSES  # noqa: SLF001
                for check in (
                    one_edit_exact_source_structural_proofs.get("checks", [])
                    if type(one_edit_exact_source_structural_proofs) is dict
                    else []
                )
            )
            if occurrence_axis is not None and parent_frontier_projection_required:
                occurrence_axis = occurrence_row_v2.project_accounting_family_one_edit_parent_frontier_authority_v2(
                    occurrence_axis,
                    column_context,
                    joined_pages,
                    family_spec,
                    topology_region,
                    period_semantics=evaluation_spec["period_semantics"],
                    expected_lane_unit_kinds=selected_lane_unit_kinds,
                    visible_dash_rescues=dash_rescues,
                )
                one_edit_frontier_projection_performed = True
                one_edit_exact_source_structural_proofs = occurrence_axis[
                    "one_edit_exact_source_structural_proofs"
                ]
            hierarchy_frontier_projection_required = (
                occurrence_axis is not None
                and one_edit_exact_source_structural_proofs.get("format_version")
                == one_edit_v1.FORMAT_VERSION
                and len(
                    [
                        check
                        for check in one_edit_exact_source_structural_proofs.get("checks", [])
                        if check.get("status")
                        not in occurrence_row_v2._ONE_EDIT_AUTHORITY_BOUND_STATUSES  # noqa: SLF001
                    ]
                )
                == 1
            )
            if hierarchy_frontier_projection_required:
                occurrence_axis = occurrence_row_v2.project_accounting_family_one_edit_hierarchy_frontier_authority_v2(
                    occurrence_axis,
                    column_context,
                    joined_pages,
                    family_spec,
                    topology_region,
                    evaluation_spec["hierarchical_closure_spec"],
                    period_semantics=evaluation_spec["period_semantics"],
                    expected_lane_unit_kinds=selected_lane_unit_kinds,
                    visible_dash_rescues=dash_rescues,
                )
                one_edit_frontier_projection_performed = True
                one_edit_exact_source_structural_proofs = occurrence_axis[
                    "one_edit_exact_source_structural_proofs"
                ]
        except ValueError as exc:
            candidate_evidence.append(
                {
                    "additive_closure": None,
                    "candidate_ordinal": candidate_ordinal,
                    "column_context": column_context,
                    "reasons": [f"ONE_EDIT_PARENT_FRONTIER_ERROR:{type(exc).__name__}:{exc}"],
                    "row_axis": row_axis,
                    "one_edit_exact_source_structural_proofs": (
                        one_edit_exact_source_structural_proofs
                    ),
                }
            )
            continue
        try:
            if evaluation_spec["closure_policy"] == (
                "SCOPED_HIERARCHICAL_EXHAUSTIVE_CORROBORATE_OR_DERIVE"
            ):
                if occurrence_axis is None:
                    raise _error("scoped hierarchical closure lost its occurrence row axis")
                closure = scoped_v2._build_accounting_scoped_hierarchical_table_closure_from_authenticated_axis_v2(
                    occurrence_axis,
                    family_spec,
                    evaluation_spec["hierarchical_closure_spec"],
                )
            elif (
                evaluation_spec["closure_policy"] == "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE"
            ):
                closure = hierarchical_v1._build_accounting_hierarchical_table_closure_from_authenticated_row_axis_v1(
                    row_axis,
                    joined_pages,
                    family_spec,
                    evaluation_spec["hierarchical_closure_spec"],
                    visible_dash_rescues=dash_rescues,
                )
            else:
                closure = additive_v1._build_accounting_additive_table_closure_from_authenticated_row_axis_v1(
                    row_axis,
                    joined_pages,
                    family_spec,
                    source_group_equivalences=evaluation_spec.get("source_group_equivalences", []),
                    visible_dash_rescues=dash_rescues,
                )
        except ValueError as exc:
            candidate_evidence.append(
                {
                    "additive_closure": None,
                    "candidate_ordinal": candidate_ordinal,
                    "column_context": column_context,
                    "reasons": [f"ACCOUNTING_CLOSURE_ERROR:{type(exc).__name__}:{exc}"],
                    "row_axis": row_axis,
                    "one_edit_exact_source_structural_proofs": (
                        one_edit_exact_source_structural_proofs
                    ),
                }
            )
            continue
        reasons = _unresolved_reasons(row_axis, column_context, closure, evaluation_spec)
        reasons.extend(
            _mixed_separator_consensus_reasons(
                row_axis=row_axis,
                column_context=column_context,
                closure=closure,
                joined_pages=joined_pages,
            )
        )
        reasons.extend(
            _degraded_dash_consensus_reasons(
                row_axis=row_axis,
                closure=closure,
            )
        )
        if occurrence_axis is not None:
            reasons.extend(
                reason
                for reason in occurrence_axis["unresolved_reasons"]
                if reason.startswith(occurrence_row_v2._EXTREME_MARGIN_RENDER_REASON_PREFIX)
            )
        candidate = {
            "additive_closure": closure,
            "candidate_ordinal": candidate_ordinal,
            "column_context": column_context,
            "reasons": list(dict.fromkeys(reasons)),
            "row_axis": row_axis,
            "one_edit_exact_source_structural_proofs": (one_edit_exact_source_structural_proofs),
            "column_context_visible_dash_rescues": dash_rescues,
        }
        if one_edit_frontier_projection_performed:
            _retain_selected_one_edit_public_replay_handoff_v1(
                prepared_public_replay_cache,
                candidate=candidate,
                joined_pages=joined_pages,
                family_spec=family_spec,
                evaluation_spec=evaluation_spec,
                selected_topology_region=topology_region,
            )
        candidate_evidence.append(candidate)
    return candidate_evidence


def _trial(
    document: dict[str, Any],
    topology_scan: dict[str, Any],
    family_spec: dict[str, Any],
    evaluation_spec: dict[str, Any],
    *,
    numeric_document: dict[str, Any] | None,
    render_snapshots: tuple[dict[str, Any], ...],
    topology_candidates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if _is_scoped_evaluation_policy(evaluation_spec):
        if topology_candidates is None:
            topology_scan, topology_candidates = _v4_topology_authority(
                _blind_pages(document),
                family_spec,
                expected_legacy_scan=topology_scan,
            )
        else:
            topology_candidates = (
                topology_candidates_v2.validate_accounting_family_topology_candidates_replay_v2(
                    topology_candidates,
                    _blind_pages(document),
                    family_spec,
                )
            )
            if (
                topology_candidates["input_binding"]["legacy_topology_scan_id"]
                != topology_scan["scan_id"]
            ):
                raise _error("V4 trial topology candidate authority differs from its legacy scan")
        topology_status = topology_candidates["status"]
    else:
        if topology_candidates is not None:
            raise _error("pre-pruning topology candidates require evaluation V4")
        topology_status = topology_scan["status"]
    base = {
        "document_ordinal": document["document_ordinal"],
        "private_provenance": canonical_clone_v1(document["private_provenance"]),
        "source_pdf_ref": canonical_clone_v1(document["source_pdf_ref"]),
        "topology_scan": topology_scan,
    }
    if _is_scoped_evaluation_policy(evaluation_spec):
        base["one_edit_exact_authority_receipt"] = None
    if topology_status == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY":
        return {
            **base,
            "additive_closure": None,
            "column_context": None,
            "document_axis_binding": None,
            "evidence_status": "NOT_OBSERVED_PROPOSAL_ONLY",
            "row_axis": None,
            "unresolved_reasons": [],
        }
    candidate_topology_statuses = {
        "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
        "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    }
    if topology_status not in candidate_topology_statuses:
        return {
            **base,
            "additive_closure": None,
            "column_context": None,
            "document_axis_binding": None,
            "evidence_status": "UNRESOLVED_NO_UNIQUE_COMPLETE_TOPOLOGY",
            "row_axis": None,
            "unresolved_reasons": [topology_status],
        }
    if numeric_document is None or not render_snapshots:
        raise _error("unique topology trial lacks its authenticated batch snapshots")
    document_axis = build_accounting_family_document_axis_join_v1(
        document,
        numeric_document,
        selected_page_render_snapshots=render_snapshots,
    )
    joined_pages = project_accounting_family_document_pages_v1(document_axis)
    source_exact_axis_cache: dict[tuple[str, str], Any] = {}
    candidate_evidence = _candidate_evidence_from_joined_pages(
        joined_pages=joined_pages,
        topology_scan=topology_scan,
        family_spec=family_spec,
        evaluation_spec=evaluation_spec,
        render_snapshots=render_snapshots,
        topology_candidates=topology_candidates,
        prepared_source_exact_axis_cache=source_exact_axis_cache,
    )
    selected, reasons = _select_candidate_evidence(candidate_evidence, evaluation_spec)
    one_edit_receipt = None
    if _is_scoped_evaluation_policy(evaluation_spec):
        one_edit_receipt, one_edit_reasons = _selected_v4_one_edit_authority_v1(
            selected,
            joined_pages=joined_pages,
            family_spec=family_spec,
            topology_candidates=topology_candidates,
            evaluation_spec=evaluation_spec,
            prepared_source_exact_axis_cache=source_exact_axis_cache,
        )
        reasons = list(dict.fromkeys([*reasons, *one_edit_reasons]))
    return {
        **base,
        "additive_closure": selected["additive_closure"] if selected is not None else None,
        "column_context": selected["column_context"] if selected is not None else None,
        "document_axis_binding": _axis_binding(document_axis),
        "evidence_status": (
            "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
            if not reasons
            else "UNRESOLVED_EVIDENCE_GATES"
        ),
        **(
            {"one_edit_exact_authority_receipt": one_edit_receipt}
            if _is_scoped_evaluation_policy(evaluation_spec)
            else {}
        ),
        "row_axis": selected["row_axis"] if selected is not None else None,
        "unresolved_reasons": reasons,
    }


def rebuild_family_first_accounting_trial_from_document_snapshot_v1(
    baseline_trial: Any,
    document_snapshot: Any,
    family_spec: Any,
    evaluation_spec: Any,
) -> dict[str, Any]:
    """Recompute one affected trial from an authenticated document snapshot.

    This bounded seam is for family/parser edits that do not alter upstream
    OCR, geometry, or topology. It deliberately cannot reconstruct omitted
    dash cells because that requires authenticated render bytes; such a trial
    must use the full live builder instead.
    """

    try:
        compiled = topology_v1._spec(family_spec)
    except (ValueError, RuntimeError) as exc:
        raise _error("family topology specification drifted") from exc
    policy = _evaluation_spec(evaluation_spec, compiled, raw_family_spec=family_spec)
    expected_trial_fields = (
        _TRIAL_FIELDS_V4 if _is_scoped_evaluation_policy(policy) else _TRIAL_FIELDS
    )
    if (
        type(baseline_trial) is not dict
        or set(baseline_trial) != expected_trial_fields
        or type(document_snapshot) is not dict
        or set(document_snapshot)
        != {
            "document_packet",
            "joined_pages",
            "manifest_id",
            "selected_page_dimensions",
            "snapshot_id",
        }
        or type(document_snapshot["snapshot_id"]) is not str
        or not document_snapshot["snapshot_id"].startswith("ffdesv1:snapshot:")
    ):
        raise _error("bounded document trial refresh input shape drifted")
    snapshot_material = canonical_clone_v1(document_snapshot)
    snapshot_id = snapshot_material.pop("snapshot_id")
    if snapshot_id != "ffdesv1:snapshot:" + canonical_json_sha256_v1(snapshot_material):
        raise _error("bounded document evidence snapshot identity drifted")
    packet = document_snapshot["document_packet"]
    provenance = baseline_trial["private_provenance"]
    topology_scan = baseline_trial["topology_scan"]
    if (
        packet["document_ordinal"] != baseline_trial["document_ordinal"]
        or not same_typed_json_v1(packet["source_pdf_ref"], baseline_trial["source_pdf_ref"])
        or packet["bank_provenance"] != provenance.get("bank")
        or packet["year"] != provenance.get("year")
        or packet["period"] != provenance.get("period")
        or packet["scope"] != provenance.get("scope")
        or topology_scan.get("family_id") != compiled["family_id"]
        or topology_scan.get("status")
        not in {
            "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
            "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
        }
        or baseline_trial["document_axis_binding"] is None
    ):
        raise _error("bounded document snapshot belongs to another family trial")
    joined_pages = document_snapshot["joined_pages"]
    if (
        type(joined_pages) is not list
        or len(joined_pages) != packet["page_count"]
        or sum(len(page.get("lines", [])) for page in joined_pages) != packet["line_count"]
    ):
        raise _error("bounded document snapshot denominator drifted")
    if _is_scoped_evaluation_policy(policy):
        _rebuilt_scan, topology_candidates = _v4_topology_authority(
            row_axis_v1._topology_pages(joined_pages),
            family_spec,
            expected_legacy_scan=topology_scan,
        )
        region_authority = topology_candidates
    else:
        topology_candidates = None
        region_authority = topology_scan
    expected_selected_pages: set[int] = set()
    for region in region_authority["regions"]:
        start = region["cluster_start_document_line_ordinal"]
        stop = region["cluster_end_document_line_ordinal_exclusive"]
        offset = 0
        for page in joined_pages:
            page_stop = offset + len(page["lines"])
            if offset < stop and page_stop > start:
                expected_selected_pages.add(page["page_sequence"])
            offset = page_stop
    selected_dimensions = document_snapshot["selected_page_dimensions"]
    if (
        type(selected_dimensions) is not list
        or {item.get("physical_page") for item in selected_dimensions} != expected_selected_pages
        or any(
            page["page_width"]
            != (
                next(
                    item["pixel_width"]
                    for item in selected_dimensions
                    if item["physical_page"] == page["page_sequence"]
                )
                if page["page_sequence"] in expected_selected_pages
                else None
            )
            for page in joined_pages
        )
    ):
        raise _error("bounded document snapshot selected-page axis drifted")
    source_exact_axis_cache: dict[tuple[str, str], Any] = {}
    candidate_evidence = _candidate_evidence_from_joined_pages(
        joined_pages=joined_pages,
        topology_scan=topology_scan,
        family_spec=family_spec,
        evaluation_spec=policy,
        render_snapshots=(),
        topology_candidates=topology_candidates,
        prepared_source_exact_axis_cache=source_exact_axis_cache,
    )
    selected, reasons = _select_candidate_evidence(candidate_evidence, policy)
    one_edit_receipt = None
    if _is_scoped_evaluation_policy(policy):
        one_edit_receipt, one_edit_reasons = _selected_v4_one_edit_authority_v1(
            selected,
            joined_pages=joined_pages,
            family_spec=family_spec,
            topology_candidates=topology_candidates,
            evaluation_spec=policy,
            prepared_source_exact_axis_cache=source_exact_axis_cache,
        )
        reasons = list(dict.fromkeys([*reasons, *one_edit_reasons]))
    return canonical_clone_v1(
        {
            "additive_closure": (selected["additive_closure"] if selected is not None else None),
            "column_context": selected["column_context"] if selected is not None else None,
            "document_axis_binding": baseline_trial["document_axis_binding"],
            "document_ordinal": baseline_trial["document_ordinal"],
            "evidence_status": (
                "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
                if not reasons
                else "UNRESOLVED_EVIDENCE_GATES"
            ),
            "private_provenance": baseline_trial["private_provenance"],
            **(
                {"one_edit_exact_authority_receipt": one_edit_receipt}
                if _is_scoped_evaluation_policy(policy)
                else {}
            ),
            "row_axis": selected["row_axis"] if selected is not None else None,
            "source_pdf_ref": baseline_trial["source_pdf_ref"],
            "topology_scan": topology_scan,
            "unresolved_reasons": reasons,
        }
    )


def _topology_pages_from_document_snapshot_v1(
    joined_pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
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
        for page in joined_pages
    ]


def _selected_topology_pages_v1(
    joined_pages: list[dict[str, Any]], topology_scan: dict[str, Any]
) -> set[int]:
    selected: set[int] = set()
    offset = 0
    for page in joined_pages:
        stop = offset + len(page["lines"])
        if any(
            offset < region["cluster_end_document_line_ordinal_exclusive"]
            and stop > region["cluster_start_document_line_ordinal"]
            for region in topology_scan["regions"]
        ):
            selected.add(page["page_sequence"])
        offset = stop
    return selected


def _v4_candidate_scoped_missing_dimension_render_pages(
    trial: Mapping[str, Any],
    joined_pages: list[dict[str, Any]],
    topology_candidates: Mapping[str, Any] | None,
) -> tuple[int, ...]:
    """Bind one exact missing-render error to one pre-pruning candidate page."""

    reasons = trial.get("unresolved_reasons")
    regions = topology_candidates.get("regions") if type(topology_candidates) is dict else None
    if type(reasons) is not list or type(regions) is not list:
        return ()
    pattern = re.compile(
        r"^CANDIDATE_([1-9][0-9]{0,8}):"
        r"ROW_AXIS_ERROR:FamilyFirstAccountingEvidenceSweepV1Error:"
        r"missing-lane page lacks authenticated render dimensions$"
    )
    requested_pages = []
    for reason in reasons:
        match = pattern.fullmatch(reason) if type(reason) is str else None
        if match is None:
            continue
        candidate_number = int(match.group(1))
        if candidate_number > len(regions):
            continue
        region = regions[candidate_number - 1]
        if (
            type(region) is not dict
            or type(region.get("cluster_start_document_line_ordinal")) is not int
            or type(region.get("cluster_end_document_line_ordinal_exclusive")) is not int
            or region["cluster_start_document_line_ordinal"]
            >= region["cluster_end_document_line_ordinal_exclusive"]
        ):
            continue
        candidate_pages = _selected_topology_pages_v1(
            joined_pages,
            {"regions": [region]},
        )
        if len(candidate_pages) == 1:
            requested_pages.append(next(iter(candidate_pages)))
    return (requested_pages[0],) if len(requested_pages) == 1 else ()


def _canonical_authenticated_render_snapshot_order_v1(
    *groups: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Merge already authenticated page renders onto one unique page axis."""

    by_page: dict[int, Mapping[str, Any]] = {}
    for snapshot in (snapshot for group in groups for snapshot in group):
        physical_page = snapshot.get("physical_page") if type(snapshot) is dict else None
        render_id = snapshot.get("render_id") if type(snapshot) is dict else None
        if (
            type(physical_page) is not int
            or physical_page <= 0
            or type(render_id) is not str
            or not render_id
        ):
            raise _error("authenticated page-render merge axis drifted")
        previous = by_page.get(physical_page)
        if previous is not None:
            if previous.get("render_id") != render_id or previous != snapshot:
                raise _error("authenticated page-render merge repeats a conflicting page")
            continue
        by_page[physical_page] = snapshot
    return tuple(dict(by_page[page]) for page in sorted(by_page))


def _v4_prepruning_candidate_render_pages_v1(
    joined_pages: list[dict[str, Any]],
    topology_candidates: Mapping[str, Any],
) -> tuple[int, ...]:
    """Project a private page reservoir admitted by complete V2 candidates.

    This is deliberately a topology-only preflight.  It may neither inspect a
    downstream trial nor route on bank, period, filename, or page number.  A
    page enters the parent-owned reservoir only when it intersects one
    authenticated complete pre-pruning candidate.  The union is not itself
    downstream render authority: a later exact reveal step must retain the
    existing bounded ordinary/candidate-scoped semantics before any pixels are
    exposed to a final trial.
    """

    regions = topology_candidates.get("regions")
    if type(regions) is not list:
        raise _error("V4 render preflight lost its topology candidate axis")
    selected: set[int] = set()
    for region in regions:
        if type(region) is not dict:
            raise _error("V4 render preflight candidate shape drifted")
        candidate_pages = _selected_topology_pages_v1(
            joined_pages,
            {"regions": [region]},
        )
        if not candidate_pages:
            raise _error("V4 render preflight candidate retained no source page")
        selected.update(candidate_pages)
    return tuple(sorted(selected))


def _v4_document_store_render_preflight_material_v1(
    *,
    document_ordinal: int,
    packet_id: str,
    render_pages: tuple[int, ...],
    reservoir_pages: tuple[int, ...],
    snapshot_id: str,
    topology_candidates_id: str,
    topology_scan_id: str,
) -> dict[str, Any]:
    return {
        "document_ordinal": document_ordinal,
        "format_version": _V4_RENDER_PREFLIGHT_FORMAT_VERSION,
        "packet_id": packet_id,
        "render_pages": list(render_pages),
        "reservoir_pages": list(reservoir_pages),
        "snapshot_id": snapshot_id,
        "topology_candidates_id": topology_candidates_id,
        "topology_scan_id": topology_scan_id,
    }


def _missing_render_pages_for_document_store_trial_v1(
    trial: dict[str, Any],
    topology_scan: dict[str, Any],
    joined_pages: list[dict[str, Any]],
    *,
    evaluation_spec: dict[str, Any] | None = None,
    topology_candidates: dict[str, Any] | None = None,
) -> tuple[int, ...]:
    """Select only pages whose missing lanes can benefit from pixel replay.

    A unique candidate retains its row axis, so its missing-row pages are
    explicit.  With multiple topology candidates, downstream selection can
    temporarily return no row axis even though one candidate would become
    complete after the ordinary dash-pixel pass.  In that case render only the
    pages intersecting those candidates, and only when the recorded candidate
    reasons actually include incomplete visible lanes.  Period/accounting-only
    ambiguity therefore does not trigger an unnecessary PDF render.
    """

    is_v4 = evaluation_spec is not None and _is_scoped_evaluation_policy(evaluation_spec)
    if topology_candidates is not None and not is_v4:
        raise _error("pre-pruning render-page candidates require evaluation V4")

    # The row-axis builder can fail before it has a public row projection when
    # the one page containing an otherwise accepted candidate has not been
    # rendered yet.  The candidate-scoped helper is also reused after the first
    # ordinary render pass, because only then can a different candidate expose
    # this exact error.
    if is_v4 and (
        missing_dimension_pages := _v4_candidate_scoped_missing_dimension_render_pages(
            trial,
            joined_pages,
            topology_candidates,
        )
    ):
        return missing_dimension_pages

    margin_render_pages: set[int] = set()
    margin_pattern = re.compile(
        r"^(?:CANDIDATE_([1-9][0-9]{0,8}):)?"
        + re.escape(occurrence_row_v2._EXTREME_MARGIN_RENDER_REASON_PREFIX)
        + r"([1-9][0-9]{0,8})$"
    )
    for reason in trial["unresolved_reasons"] if is_v4 else ():
        match = margin_pattern.fullmatch(reason)
        if match is None:
            continue
        candidate_number = int(match.group(1)) if match.group(1) is not None else None
        page_sequence = int(match.group(2))
        authority = topology_candidates if topology_candidates is not None else topology_scan
        regions = authority["regions"]
        if candidate_number is None:
            if len(regions) != 1:
                continue
            region = regions[0]
        else:
            if topology_candidates is None or candidate_number > len(regions):
                continue
            region = regions[candidate_number - 1]
        admitted_pages = _selected_topology_pages_v1(
            joined_pages,
            {"regions": [region]},
        )
        if page_sequence in admitted_pages:
            margin_render_pages.add(page_sequence)
    row_axis = trial["row_axis"]
    if margin_render_pages:
        if row_axis is not None:
            margin_render_pages.update(
                row["label_match"]["page_sequence"]
                for row in row_axis["rows"]
                if row["missing_column_ordinals"]
            )
            margin_render_pages.update(
                trailing["page_sequence"]
                for trailing in row_axis["trailing_value_rows"]
                if trailing["missing_column_ordinals"]
            )
        return tuple(sorted(margin_render_pages))
    if row_axis is not None:
        if is_v4 and topology_candidates is not None and len(topology_candidates["regions"]) > 1:
            # Candidate selection intentionally returns only the winning row
            # axis.  A complete summary can therefore hide a richer detail
            # candidate whose existing DASH cells still need pixel replay.
            # Render the bounded union before final V4 selection; otherwise
            # the discarded detail reasons can never schedule their own page.
            return tuple(
                sorted(
                    _selected_topology_pages_v1(joined_pages, topology_candidates)
                    | margin_render_pages
                )
            )
        missing_pages = {
            row["label_match"]["page_sequence"]
            for row in row_axis["rows"]
            if row["missing_column_ordinals"]
        }
        if evaluation_spec is not None and _is_scoped_evaluation_policy(evaluation_spec):
            missing_pages.update(
                trailing["page_sequence"]
                for trailing in row_axis["trailing_value_rows"]
                if trailing["missing_column_ordinals"]
            )
        if missing_pages:
            return tuple(sorted(missing_pages | margin_render_pages))
        if row_axis["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY":
            return tuple(sorted(margin_render_pages))
        return tuple(sorted(margin_render_pages))
    region_authority = topology_candidates if topology_candidates is not None else topology_scan
    if region_authority["status"] == ("UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS") and any(
        "VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE" in reason
        or "VISIBLE_ROLE_OCCURRENCE_ROW_LANES_NOT_COMPLETE" in reason
        for reason in trial["unresolved_reasons"]
    ):
        return tuple(
            sorted(
                _selected_topology_pages_v1(joined_pages, region_authority) | margin_render_pages
            )
        )
    return tuple(sorted(margin_render_pages))


def _prepare_v4_candidate_render_schedule_v1(
    candidates: list[dict[str, Any]],
    *,
    topology_scan: dict[str, Any],
    topology_candidates: dict[str, Any],
    joined_pages: list[dict[str, Any]],
    evaluation_spec: dict[str, Any],
) -> _PreparedV4CandidateRenderScheduleV1:
    regions = topology_candidates.get("regions")
    if type(regions) is not list or len(regions) != len(candidates):
        raise _error("candidate render schedule lost its pre-pruning region axis")
    exact_missing_dimension_reason = (
        "ROW_AXIS_ERROR:FamilyFirstAccountingEvidenceSweepV1Error:"
        "missing-lane page lacks authenticated render dimensions"
    )
    render_pages: set[int] = set()
    candidate_axis = []
    for candidate_ordinal, (candidate, region) in enumerate(zip(candidates, regions, strict=True)):
        if (
            type(candidate) is not dict
            or candidate.get("candidate_ordinal") != candidate_ordinal
            or type(candidate.get("reasons")) is not list
            or type(region) is not dict
        ):
            raise _error("candidate render schedule evidence axis drifted")
        reasons = [
            f"CANDIDATE_1:{reason}" if reason == exact_missing_dimension_reason else reason
            for reason in candidate["reasons"]
        ]
        candidate_topology = {
            "regions": [region],
            "status": topology_candidates["status"],
        }
        candidate_trial = {
            "row_axis": candidate.get("row_axis"),
            "unresolved_reasons": reasons,
        }
        candidate_pages = _missing_render_pages_for_document_store_trial_v1(
            candidate_trial,
            topology_scan,
            joined_pages,
            evaluation_spec=evaluation_spec,
            topology_candidates=candidate_topology,
        )
        admitted_pages = _selected_topology_pages_v1(
            joined_pages,
            candidate_topology,
        )
        if not set(candidate_pages) <= admitted_pages:
            raise _error("candidate render schedule escaped its topology region")
        render_pages.update(candidate_pages)
        row_axis = candidate.get("row_axis")
        candidate_axis.append(
            {
                "candidate_ordinal": candidate_ordinal,
                "reasons_sha256": canonical_json_sha256_v1(candidate["reasons"]),
                "row_axis_id": (row_axis.get("row_axis_id") if type(row_axis) is dict else None),
                "topology_region_sha256": canonical_json_sha256_v1(region),
            }
        )
    candidate_axis_sha256 = canonical_json_sha256_v1(candidate_axis)
    pages = tuple(sorted(render_pages))
    material = {
        "candidate_axis_sha256": candidate_axis_sha256,
        "render_pages": list(pages),
        "topology_candidates_id": topology_candidates["result_id"],
        "topology_scan_id": topology_scan["scan_id"],
    }
    return _PreparedV4CandidateRenderScheduleV1(
        candidate_axis_sha256=candidate_axis_sha256,
        render_pages=pages,
        schedule_sha256=canonical_json_sha256_v1(material),
        topology_candidates_id=topology_candidates["result_id"],
        topology_scan_id=topology_scan["scan_id"],
        seal=_PREPARED_V4_CANDIDATE_RENDER_SCHEDULE_SEAL,
    )


def _open_prepared_v4_candidate_render_schedule_v1(
    value: Any,
    *,
    topology_scan: Mapping[str, Any],
    topology_candidates: Mapping[str, Any],
    joined_pages: list[dict[str, Any]],
) -> tuple[int, ...]:
    if (
        type(value) is not _PreparedV4CandidateRenderScheduleV1
        or value.seal is not _PREPARED_V4_CANDIDATE_RENDER_SCHEDULE_SEAL
        or value.topology_scan_id != topology_scan.get("scan_id")
        or value.topology_candidates_id != topology_candidates.get("result_id")
        or type(value.render_pages) is not tuple
        or any(type(page) is not int or page <= 0 for page in value.render_pages)
        or tuple(sorted(set(value.render_pages))) != value.render_pages
    ):
        raise _error("prepared candidate render schedule identity drifted")
    material = {
        "candidate_axis_sha256": value.candidate_axis_sha256,
        "render_pages": list(value.render_pages),
        "topology_candidates_id": value.topology_candidates_id,
        "topology_scan_id": value.topology_scan_id,
    }
    admitted_pages = _selected_topology_pages_v1(joined_pages, topology_candidates)
    if (
        value.schedule_sha256 != canonical_json_sha256_v1(material)
        or not set(value.render_pages) <= admitted_pages
    ):
        raise _error("prepared candidate render schedule binding drifted")
    return value.render_pages


def _document_store_axis_binding_v1(
    packet: dict[str, Any], selected_pages: set[int]
) -> dict[str, Any]:
    provenance = {
        "bank": packet["bank_provenance"],
        "period": packet["period"],
        "scope": packet["scope"],
        "year": packet["year"],
    }
    source_binding = canonical_json_sha256_v1(
        {
            "document_id": packet["document_id"],
            "private_provenance": provenance,
            "source_pdf_ref": packet["source_pdf_ref"],
        }
    )
    metrics = {
        "line_count": packet["line_count"],
        "page_count": packet["page_count"],
        "page_count_with_authenticated_dimensions": len(selected_pages),
    }
    material = {
        "document_packet_id": packet["packet_id"],
        "metrics": metrics,
        "selected_pages": sorted(selected_pages),
        "source_binding_sha256": source_binding,
    }
    return {
        "document_axis_id": "ffdesv1:accounting-axis:" + canonical_json_sha256_v1(material),
        "metrics": metrics,
        "source_binding_sha256": source_binding,
    }


def _validate_v4_document_store_selected_snapshot_v1(
    snapshot: Any,
    *,
    expected_packet: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], Any]:
    """Require the public authenticated full-page snapshot contract for V4.

    V4's occurrence axis authenticates existing textual dashes against exact
    page pixels. The legacy five-field document snapshot is not that public
    contract and can omit pages with zero recognized lines, so it must never
    be upgraded locally by fabricating the two missing identity fields.
    """

    try:
        prepared_snapshot = occurrence_row_v2._prepare_authenticated_snapshot_projection_v2(
            snapshot
        )
        typed_snapshot, projection = (
            occurrence_row_v2._prepared_authenticated_snapshot_projection_authority_v2(
                prepared_snapshot
            )
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("V4 document-store selected snapshot contract drifted") from exc
    packet = typed_snapshot["document_packet"]
    selected_pages = list(range(1, packet["page_count"] + 1))
    selected_line_count = sum(len(page["lines"]) for page in typed_snapshot["joined_pages"])
    source = projection["source_binding"]
    if (
        (expected_packet is not None and not same_typed_json_v1(packet, expected_packet))
        or source["document_ordinal"] != packet["document_ordinal"]
        or source["document_packet_id"] != packet["packet_id"]
        or source["selected_pages"] != selected_pages
        or selected_line_count != packet["line_count"]
        or [page["page_sequence"] for page in typed_snapshot["joined_pages"]] != selected_pages
        or [dimension["physical_page"] for dimension in typed_snapshot["selected_page_dimensions"]]
        != selected_pages
    ):
        raise _error("V4 document-store selected snapshot packet or full-page axis drifted")
    return typed_snapshot, projection, prepared_snapshot


def _prepare_v4_document_store_context_v1(
    snapshot: dict[str, Any],
    family_spec: dict[str, Any],
    evaluation_spec: dict[str, Any],
    *,
    expected_packet: dict[str, Any] | None,
    runtime_telemetry: dict[str, int | float] | None,
) -> _PreparedV4DocumentStoreContextV1:
    snapshot_started = perf_counter()
    selected_snapshot, _projection, prepared_snapshot = (
        _validate_v4_document_store_selected_snapshot_v1(
            snapshot,
            expected_packet=expected_packet,
        )
    )
    _telemetry_add(runtime_telemetry, "snapshot_prepare_count", 1)
    _telemetry_add(
        runtime_telemetry,
        "snapshot_prepare_seconds",
        perf_counter() - snapshot_started,
    )
    topology_started = perf_counter()
    prepared_topology = topology_candidates_v2._prepare_accounting_family_topology_candidates_v2(
        row_axis_v1._topology_pages(selected_snapshot["joined_pages"]),
        family_spec,
    )
    _telemetry_add(runtime_telemetry, "topology_prepare_count", 1)
    _telemetry_add(
        runtime_telemetry,
        "topology_prepare_seconds",
        perf_counter() - topology_started,
    )
    caller_snapshot_sha256 = canonical_json_sha256_v1(snapshot)
    evaluation_spec_sha256 = canonical_json_sha256_v1(evaluation_spec)
    family_spec_sha256 = canonical_json_sha256_v1(family_spec)
    material = _prepared_v4_document_context_material_v1(
        caller_snapshot_sha256=caller_snapshot_sha256,
        evaluation_spec_sha256=evaluation_spec_sha256,
        family_spec_sha256=family_spec_sha256,
        prepared_snapshot=prepared_snapshot,
        prepared_topology=prepared_topology,
    )
    return _PreparedV4DocumentStoreContextV1(
        caller_snapshot_sha256=caller_snapshot_sha256,
        evaluation_spec_sha256=evaluation_spec_sha256,
        family_spec_sha256=family_spec_sha256,
        prepared_context_sha256=canonical_json_sha256_v1(material),
        prepared_snapshot=prepared_snapshot,
        prepared_topology=prepared_topology,
        seal=_PREPARED_V4_DOCUMENT_CONTEXT_SEAL,
    )


def _open_prepared_v4_document_store_context_v1(
    value: Any,
    snapshot: dict[str, Any],
    family_spec: dict[str, Any],
    evaluation_spec: dict[str, Any],
    *,
    expected_packet: dict[str, Any] | None,
    expected_legacy_scan: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], tuple[Any, ...]]:
    """Reopen both exact inner authorities before every trial or retry."""

    if (
        type(value) is not _PreparedV4DocumentStoreContextV1
        or value.seal is not _PREPARED_V4_DOCUMENT_CONTEXT_SEAL
        or value.caller_snapshot_sha256 != canonical_json_sha256_v1(snapshot)
        or value.family_spec_sha256 != canonical_json_sha256_v1(family_spec)
        or value.evaluation_spec_sha256 != canonical_json_sha256_v1(evaluation_spec)
    ):
        raise _error("prepared V4 document-store context differs from its source")
    material = _prepared_v4_document_context_material_v1(
        caller_snapshot_sha256=value.caller_snapshot_sha256,
        evaluation_spec_sha256=value.evaluation_spec_sha256,
        family_spec_sha256=value.family_spec_sha256,
        prepared_snapshot=value.prepared_snapshot,
        prepared_topology=value.prepared_topology,
    )
    if value.prepared_context_sha256 != canonical_json_sha256_v1(material):
        raise _error("prepared V4 document-store context binding drifted")
    try:
        selected_snapshot, _projection = (
            occurrence_row_v2._prepared_authenticated_snapshot_projection_authority_v2(
                value.prepared_snapshot
            )
        )
        topology_scan, topology_candidates, candidate_bindings = (
            topology_candidates_v2._prepared_accounting_family_topology_authority_v2(
                value.prepared_topology
            )
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("prepared V4 document-store inner authority drifted") from exc
    if (
        (
            expected_packet is not None
            and not same_typed_json_v1(
                selected_snapshot["document_packet"],
                expected_packet,
            )
        )
        or (
            expected_legacy_scan is not None
            and not same_typed_json_v1(topology_scan, expected_legacy_scan)
        )
        or topology_candidates["input_binding"]["legacy_topology_scan_id"]
        != topology_scan["scan_id"]
    ):
        raise _error("prepared V4 document-store inner source binding drifted")
    return selected_snapshot, topology_scan, topology_candidates, candidate_bindings


def _open_prepared_v4_render_topology_handoff_v1(
    prepared_context: Any,
    handoff: Any,
    *,
    expected_legacy_scan: Mapping[str, Any],
) -> dict[str, Any]:
    """Reopen only the small topology authority after a full exact trial open."""

    if (
        type(prepared_context) is not _PreparedV4DocumentStoreContextV1
        or prepared_context.seal is not _PREPARED_V4_DOCUMENT_CONTEXT_SEAL
        or type(handoff) is not _PreparedV4RenderTopologyHandoffV1
        or handoff.seal is not _PREPARED_V4_RENDER_TOPOLOGY_HANDOFF_SEAL
        or handoff.prepared_context_sha256 != prepared_context.prepared_context_sha256
    ):
        raise _error("prepared V4 render-topology handoff identity drifted")
    material = _prepared_v4_document_context_material_v1(
        caller_snapshot_sha256=prepared_context.caller_snapshot_sha256,
        evaluation_spec_sha256=prepared_context.evaluation_spec_sha256,
        family_spec_sha256=prepared_context.family_spec_sha256,
        prepared_snapshot=prepared_context.prepared_snapshot,
        prepared_topology=prepared_context.prepared_topology,
    )
    if prepared_context.prepared_context_sha256 != canonical_json_sha256_v1(material):
        raise _error("prepared V4 render-topology context binding drifted")
    try:
        topology_scan, topology_candidates, _candidate_bindings = (
            topology_candidates_v2._prepared_accounting_family_topology_authority_v2(
                prepared_context.prepared_topology
            )
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("prepared V4 render-topology inner authority drifted") from exc
    if (
        handoff.legacy_topology_scan_id != topology_scan["scan_id"]
        or handoff.topology_candidates_id != topology_candidates["result_id"]
        or not same_typed_json_v1(topology_scan, expected_legacy_scan)
    ):
        raise _error("prepared V4 render-topology source binding drifted")
    return topology_candidates


def _selected_v4_one_edit_authority_or_defer_for_render_v1(
    selected: dict[str, Any] | None,
    *,
    joined_pages: list[dict[str, Any]],
    family_spec: dict[str, Any],
    topology_candidates: dict[str, Any],
    evaluation_spec: dict[str, Any],
    prepared_source_exact_axis_cache: dict[tuple[str, str], Any],
    prepared_public_replay_cache: dict[str, Any],
    pending_render_pages: tuple[int, ...],
    defer_for_render: bool,
) -> tuple[dict[str, Any] | None, list[str], bool]:
    """Skip a public replay only while another exact render pass is mandatory."""

    if defer_for_render and pending_render_pages:
        return None, [_SELECTED_PUBLIC_REPLAY_DEFERRED_FOR_RENDER_REASON], True
    receipt, replay_reasons = _selected_v4_one_edit_authority_v1(
        selected,
        joined_pages=joined_pages,
        family_spec=family_spec,
        topology_candidates=topology_candidates,
        evaluation_spec=evaluation_spec,
        prepared_source_exact_axis_cache=prepared_source_exact_axis_cache,
        prepared_public_replay_cache=prepared_public_replay_cache,
    )
    return receipt, replay_reasons, False


def _trial_from_document_store_snapshot_v1(
    snapshot: dict[str, Any],
    family_spec: dict[str, Any],
    evaluation_spec: dict[str, Any],
    *,
    render_snapshots: tuple[dict[str, Any], ...] = (),
    topology_scan: dict[str, Any] | None = None,
    expected_packet: dict[str, Any] | None = None,
    _v4_runtime_context: dict[str, Any] | None = None,
    _defer_selected_public_replay_for_render: bool = False,
    runtime_telemetry: dict[str, int | float] | None = None,
) -> dict[str, Any]:
    if type(_defer_selected_public_replay_for_render) is not bool or (
        _defer_selected_public_replay_for_render
        and (not _is_scoped_evaluation_policy(evaluation_spec) or _v4_runtime_context is None)
    ):
        raise _error("selected public-replay render deferral contract drifted")
    if _is_scoped_evaluation_policy(evaluation_spec):
        prepared_context = (
            _v4_runtime_context.get("prepared_context") if _v4_runtime_context is not None else None
        )
        if prepared_context is None:
            prepared_context = _prepare_v4_document_store_context_v1(
                snapshot,
                family_spec,
                evaluation_spec,
                expected_packet=expected_packet,
                runtime_telemetry=runtime_telemetry,
            )
            if _v4_runtime_context is not None:
                _v4_runtime_context["prepared_context"] = prepared_context
        snapshot, topology_scan, topology_candidates, candidate_bindings = (
            _open_prepared_v4_document_store_context_v1(
                prepared_context,
                snapshot,
                family_spec,
                evaluation_spec,
                expected_packet=expected_packet,
                expected_legacy_scan=topology_scan,
            )
        )
        if _v4_runtime_context is not None:
            _v4_runtime_context["render_topology_handoff"] = _PreparedV4RenderTopologyHandoffV1(
                legacy_topology_scan_id=topology_scan["scan_id"],
                prepared_context_sha256=prepared_context.prepared_context_sha256,
                topology_candidates_id=topology_candidates["result_id"],
                seal=_PREPARED_V4_RENDER_TOPOLOGY_HANDOFF_SEAL,
            )
        topology_status = topology_candidates["status"]
        region_authority = topology_candidates
    elif topology_scan is None:
        prepared_context = None
        candidate_bindings = ()
        topology_candidates = None
        packet = snapshot["document_packet"]
        joined_pages = snapshot["joined_pages"]
        topology_scan = topology_v1.build_accounting_family_topology_scan_v1(
            _topology_pages_from_document_snapshot_v1(joined_pages), family_spec
        )
        topology_status = topology_scan["status"]
        region_authority = topology_scan
    else:
        prepared_context = None
        candidate_bindings = ()
        topology_candidates = None
        topology_status = topology_scan["status"]
        region_authority = topology_scan
    packet = snapshot["document_packet"]
    joined_pages = snapshot["joined_pages"]
    base = {
        "document_ordinal": packet["document_ordinal"],
        "private_provenance": {
            "bank": packet["bank_provenance"],
            "period": packet["period"],
            "scope": packet["scope"],
            "year": packet["year"],
        },
        "source_pdf_ref": canonical_clone_v1(packet["source_pdf_ref"]),
        "topology_scan": topology_scan,
    }
    if _is_scoped_evaluation_policy(evaluation_spec):
        base["one_edit_exact_authority_receipt"] = None
    if topology_status == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY":
        return {
            **base,
            "additive_closure": None,
            "column_context": None,
            "document_axis_binding": None,
            "evidence_status": "NOT_OBSERVED_PROPOSAL_ONLY",
            "row_axis": None,
            "unresolved_reasons": [],
        }
    if topology_status not in {
        "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
        "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    }:
        return {
            **base,
            "additive_closure": None,
            "column_context": None,
            "document_axis_binding": None,
            "evidence_status": "UNRESOLVED_NO_UNIQUE_COMPLETE_TOPOLOGY",
            "row_axis": None,
            "unresolved_reasons": [topology_status],
        }
    selected_pages = _selected_topology_pages_v1(joined_pages, region_authority)
    if not selected_pages:
        raise _error("document-store topology selected no physical page")
    projected_pages = [
        {
            "lines": page["lines"],
            "page_sequence": page["page_sequence"],
            "page_width": page["page_width"] if page["page_sequence"] in selected_pages else None,
        }
        for page in joined_pages
    ]
    if _v4_runtime_context is None:
        source_exact_axis_cache: dict[tuple[str, str], Any] = {}
        selected_public_replay_cache: dict[str, Any] = {}
        candidate_occurrence_axis_cache: dict[str, Any] = {}
    else:
        source_exact_axis_cache = _v4_runtime_context.setdefault(
            "source_exact_axis_cache",
            {},
        )
        if type(source_exact_axis_cache) is not dict:
            raise _error("V4 runtime one-edit source-axis cache shape drifted")
        selected_public_replay_cache = _v4_runtime_context.setdefault(
            "selected_public_replay_cache",
            {},
        )
        if type(selected_public_replay_cache) is not dict:
            raise _error("V4 runtime selected public-replay cache shape drifted")
        candidate_occurrence_axis_cache = _v4_runtime_context.setdefault(
            "candidate_occurrence_axis_cache",
            {},
        )
        if type(candidate_occurrence_axis_cache) is not dict:
            raise _error("V4 runtime candidate occurrence-axis cache shape drifted")
    candidates = _candidate_evidence_from_joined_pages(
        joined_pages=projected_pages,
        topology_scan=topology_scan,
        family_spec=family_spec,
        evaluation_spec=evaluation_spec,
        render_snapshots=render_snapshots,
        selected_snapshot=snapshot,
        topology_candidates=topology_candidates,
        prepared_topology_bindings=candidate_bindings,
        prepared_snapshot=(
            prepared_context.prepared_snapshot if prepared_context is not None else None
        ),
        prepared_source_exact_axis_cache=source_exact_axis_cache,
        prepared_candidate_occurrence_axis_cache=candidate_occurrence_axis_cache,
        prepared_public_replay_cache=selected_public_replay_cache,
        runtime_telemetry=runtime_telemetry,
    )
    selected, reasons = _select_candidate_evidence(candidates, evaluation_spec)
    if _is_scoped_evaluation_policy(evaluation_spec):
        prepared_render_schedule = _prepare_v4_candidate_render_schedule_v1(
            candidates,
            topology_scan=topology_scan,
            topology_candidates=topology_candidates,
            joined_pages=projected_pages,
            evaluation_spec=evaluation_spec,
        )
        if _v4_runtime_context is not None:
            _v4_runtime_context["candidate_render_schedule"] = prepared_render_schedule
        if render_snapshots:
            rendered_pages = {render["physical_page"] for render in render_snapshots}
            transient_trial = {
                "row_axis": selected["row_axis"] if selected is not None else None,
                "unresolved_reasons": reasons,
            }
            pending_render_pages = tuple(
                page
                for page in _v4_candidate_scoped_missing_dimension_render_pages(
                    transient_trial,
                    projected_pages,
                    topology_candidates,
                )
                if page not in rendered_pages
            )
        else:
            pending_render_pages = prepared_render_schedule.render_pages
    else:
        pending_render_pages = ()
    one_edit_receipt = None
    if _is_scoped_evaluation_policy(evaluation_spec):
        one_edit_receipt, one_edit_reasons, _deferred_for_render = (
            _selected_v4_one_edit_authority_or_defer_for_render_v1(
                selected,
                joined_pages=projected_pages,
                family_spec=family_spec,
                topology_candidates=topology_candidates,
                evaluation_spec=evaluation_spec,
                prepared_source_exact_axis_cache=source_exact_axis_cache,
                prepared_public_replay_cache=selected_public_replay_cache,
                pending_render_pages=pending_render_pages,
                defer_for_render=_defer_selected_public_replay_for_render,
            )
        )
        reasons = list(dict.fromkeys([*reasons, *one_edit_reasons]))
    return {
        **base,
        "additive_closure": selected["additive_closure"] if selected is not None else None,
        "column_context": selected["column_context"] if selected is not None else None,
        "document_axis_binding": _document_store_axis_binding_v1(packet, selected_pages),
        "evidence_status": (
            "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
            if not reasons
            else "UNRESOLVED_EVIDENCE_GATES"
        ),
        **(
            {"one_edit_exact_authority_receipt": one_edit_receipt}
            if _is_scoped_evaluation_policy(evaluation_spec)
            else {}
        ),
        "row_axis": selected["row_axis"] if selected is not None else None,
        "unresolved_reasons": reasons,
    }


def _document_store_trial_with_render_rescue_v1(
    document_store_capability: document_store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    *,
    packet: dict[str, Any],
    snapshot: dict[str, Any],
    family_spec: dict[str, Any],
    policy: dict[str, Any],
    topology_scan: dict[str, Any] | None,
    runtime_telemetry: dict[str, int | float] | None = None,
) -> dict[str, Any]:
    is_v4 = _is_scoped_evaluation_policy(policy)
    runtime_context: dict[str, Any] = {}
    trial = _trial_from_document_store_snapshot_v1(
        snapshot,
        family_spec,
        policy,
        topology_scan=topology_scan,
        expected_packet=packet if is_v4 else None,
        _v4_runtime_context=runtime_context if is_v4 else None,
        _defer_selected_public_replay_for_render=is_v4,
        runtime_telemetry=runtime_telemetry,
    )
    if is_v4:
        prepared_context = runtime_context.get("prepared_context")
        render_topology_handoff = runtime_context.get("render_topology_handoff")
        if type(prepared_context) is _PreparedV4DocumentStoreContextV1:
            render_topology_candidates = _open_prepared_v4_render_topology_handoff_v1(
                prepared_context,
                render_topology_handoff,
                expected_legacy_scan=trial["topology_scan"],
            )
        else:
            _render_scan, render_topology_candidates = _v4_topology_authority(
                row_axis_v1._topology_pages(snapshot["joined_pages"]),
                family_spec,
                expected_legacy_scan=trial["topology_scan"],
            )
    else:
        render_topology_candidates = None
    if is_v4 and (render_schedule := runtime_context.get("candidate_render_schedule")) is not None:
        missing_pages = _open_prepared_v4_candidate_render_schedule_v1(
            render_schedule,
            topology_scan=trial["topology_scan"],
            topology_candidates=render_topology_candidates,
            joined_pages=snapshot["joined_pages"],
        )
    else:
        missing_pages = _missing_render_pages_for_document_store_trial_v1(
            trial,
            trial["topology_scan"],
            snapshot["joined_pages"],
            evaluation_spec=policy,
            topology_candidates=render_topology_candidates,
        )
    if missing_pages:
        _telemetry_add(runtime_telemetry, "render_retry_count", 1)
        _telemetry_add(runtime_telemetry, "render_page_count", len(missing_pages))
        renders = document_store_v1.read_authenticated_family_first_document_page_renders_v1(
            document_store_capability,
            document_ordinal=packet["document_ordinal"],
            physical_pages=missing_pages,
        )
        trial = _trial_from_document_store_snapshot_v1(
            snapshot,
            family_spec,
            policy,
            render_snapshots=renders,
            topology_scan=trial["topology_scan"] if is_v4 else topology_scan,
            expected_packet=packet if is_v4 else None,
            _v4_runtime_context=runtime_context if is_v4 else None,
            _defer_selected_public_replay_for_render=is_v4,
            runtime_telemetry=runtime_telemetry,
        )
        if is_v4:
            candidate_scoped_pages = tuple(
                page
                for page in _v4_candidate_scoped_missing_dimension_render_pages(
                    trial,
                    snapshot["joined_pages"],
                    render_topology_candidates,
                )
                if page not in set(missing_pages)
            )
            if candidate_scoped_pages:
                _telemetry_add(runtime_telemetry, "render_retry_count", 1)
                _telemetry_add(
                    runtime_telemetry,
                    "render_page_count",
                    len(candidate_scoped_pages),
                )
                candidate_renders = (
                    document_store_v1.read_authenticated_family_first_document_page_renders_v1(
                        document_store_capability,
                        document_ordinal=packet["document_ordinal"],
                        physical_pages=candidate_scoped_pages,
                    )
                )
                trial = _trial_from_document_store_snapshot_v1(
                    snapshot,
                    family_spec,
                    policy,
                    render_snapshots=_canonical_authenticated_render_snapshot_order_v1(
                        renders,
                        candidate_renders,
                    ),
                    topology_scan=trial["topology_scan"],
                    expected_packet=packet,
                    _v4_runtime_context=runtime_context,
                    _defer_selected_public_replay_for_render=True,
                    runtime_telemetry=runtime_telemetry,
                )
    return trial


def _v4_document_store_render_preflight_worker_v1(
    request: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
) -> dict[str, Any]:
    """Project candidate-bound render pages without building a family trial."""

    if type(request) is not tuple or len(request) != 4:
        raise _error("V4 document-store render preflight request shape drifted")
    packet, snapshot, family_spec, policy = request
    if (
        type(packet) is not dict
        or type(snapshot) is not dict
        or type(family_spec) is not dict
        or type(policy) is not dict
        or not _is_scoped_evaluation_policy(policy)
    ):
        raise _error("V4 document-store render preflight request binding drifted")
    if _V4_RENDER_PREFLIGHT_CONTEXT_CACHE:
        raise _error("V4 render preflight worker retained an unfinished context")
    prepared_context = _prepare_v4_document_store_context_v1(
        snapshot,
        family_spec,
        policy,
        expected_packet=packet,
        runtime_telemetry=None,
    )
    selected_snapshot, topology_scan, topology_candidates, _candidate_bindings = (
        _open_prepared_v4_document_store_context_v1(
            prepared_context,
            snapshot,
            family_spec,
            policy,
            expected_packet=packet,
            expected_legacy_scan=None,
        )
    )
    # Candidate pages remain a private reservoir.  The only authority to
    # reveal an ordinary first-pass render is the unchanged no-render trial's
    # exact missing-page receipt below; projecting pages directly from every
    # pre-pruning occurrence would complete threat regions that the sequential
    # scheduler never opened.
    render_pages: tuple[int, ...] = ()
    reservoir_pages = _v4_prepruning_candidate_render_pages_v1(
        selected_snapshot["joined_pages"],
        topology_candidates,
    )
    if not set(render_pages) <= set(reservoir_pages):
        raise _error("V4 render preflight pages escape their private reservoir")
    completed_result: dict[str, Any] | None = None
    if not render_pages:
        runtime_context = {"prepared_context": prepared_context}
        trial = _trial_from_document_store_snapshot_v1(
            snapshot,
            family_spec,
            policy,
            render_snapshots=(),
            topology_scan=topology_scan,
            expected_packet=packet,
            _v4_runtime_context=runtime_context,
            _defer_selected_public_replay_for_render=True,
        )
        render_schedule = runtime_context.get("candidate_render_schedule")
        if render_schedule is not None:
            render_pages = _open_prepared_v4_candidate_render_schedule_v1(
                render_schedule,
                topology_scan=trial["topology_scan"],
                topology_candidates=topology_candidates,
                joined_pages=selected_snapshot["joined_pages"],
            )
        else:
            render_pages = _missing_render_pages_for_document_store_trial_v1(
                trial,
                trial["topology_scan"],
                selected_snapshot["joined_pages"],
                evaluation_spec=policy,
                topology_candidates=topology_candidates,
            )
        if not set(render_pages) <= set(reservoir_pages):
            raise _error("V4 render preflight base trial escaped its private reservoir")
        if not render_pages:
            completed_result = {
                "document_ordinal": packet["document_ordinal"],
                "missing_render_pages": (),
                "packet_id": packet["packet_id"],
                "snapshot_id": snapshot["snapshot_id"],
                "trial": trial,
            }
    material = _v4_document_store_render_preflight_material_v1(
        document_ordinal=packet["document_ordinal"],
        packet_id=packet["packet_id"],
        render_pages=render_pages,
        reservoir_pages=reservoir_pages,
        snapshot_id=snapshot["snapshot_id"],
        topology_candidates_id=topology_candidates["result_id"],
        topology_scan_id=topology_scan["scan_id"],
    )
    preflight = {
        **material,
        "completed_result": completed_result,
        "preflight_id": "ffdrpv1:preflight:" + canonical_json_sha256_v1(material),
        "render_pages": render_pages,
        "reservoir_pages": reservoir_pages,
    }
    if completed_result is None:
        _V4_RENDER_PREFLIGHT_CONTEXT_CACHE[preflight["preflight_id"]] = {
            "family_spec_sha256": canonical_json_sha256_v1(family_spec),
            "packet_id": packet["packet_id"],
            "policy_sha256": canonical_json_sha256_v1(policy),
            "prepared_context": prepared_context,
            "snapshot_id": snapshot["snapshot_id"],
            "topology_candidates_id": topology_candidates["result_id"],
            "topology_scan_id": topology_scan["scan_id"],
        }
    return preflight


def _validated_v4_document_store_render_preflight_v1(
    value: Any,
    *,
    packet: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebind one topology/occurrence preflight to parent-owned source."""

    fields = {
        "completed_result",
        "document_ordinal",
        "format_version",
        "packet_id",
        "preflight_id",
        "render_pages",
        "reservoir_pages",
        "snapshot_id",
        "topology_candidates_id",
        "topology_scan_id",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or (
            value.get("completed_result") is not None
            and type(value["completed_result"]) is not dict
        )
        or (value.get("completed_result") is not None and value.get("render_pages") != ())
        or value.get("document_ordinal") != packet.get("document_ordinal")
        or value.get("format_version") != _V4_RENDER_PREFLIGHT_FORMAT_VERSION
        or value.get("packet_id") != packet.get("packet_id")
        or value.get("snapshot_id") != snapshot.get("snapshot_id")
        or type(value.get("topology_candidates_id")) is not str
        or not value["topology_candidates_id"].startswith("aftcv2:result:")
        or type(value.get("topology_scan_id")) is not str
        or not value["topology_scan_id"].startswith("aftv1:scan:")
        or type(value.get("render_pages")) is not tuple
        or any(type(page) is not int or page <= 0 for page in value["render_pages"])
        or tuple(sorted(value["render_pages"])) != value["render_pages"]
        or len(value["render_pages"]) != len(set(value["render_pages"]))
        or any(page > packet.get("page_count", 0) for page in value["render_pages"])
        or type(value.get("reservoir_pages")) is not tuple
        or any(type(page) is not int or page <= 0 for page in value["reservoir_pages"])
        or tuple(sorted(value["reservoir_pages"])) != value["reservoir_pages"]
        or len(value["reservoir_pages"]) != len(set(value["reservoir_pages"]))
        or any(page > packet.get("page_count", 0) for page in value["reservoir_pages"])
        or not set(value["render_pages"]) <= set(value["reservoir_pages"])
    ):
        raise _error("V4 document-store render preflight differs from its parent source")
    material = _v4_document_store_render_preflight_material_v1(
        document_ordinal=value["document_ordinal"],
        packet_id=value["packet_id"],
        render_pages=value["render_pages"],
        reservoir_pages=value["reservoir_pages"],
        snapshot_id=value["snapshot_id"],
        topology_candidates_id=value["topology_candidates_id"],
        topology_scan_id=value["topology_scan_id"],
    )
    if value.get("preflight_id") != "ffdrpv1:preflight:" + canonical_json_sha256_v1(material):
        raise _error("V4 document-store render preflight identity drifted")
    return dict(value)


def _v4_document_store_preflight_bound_trial_worker_v1(
    request: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        tuple[dict[str, Any], ...],
        dict[str, Any],
    ],
) -> dict[str, Any]:
    """Recompute one final trial with exactly its preflight-authorized pixels."""

    if type(request) is not tuple or len(request) != 6:
        raise _error("V4 preflight-bound trial worker request shape drifted")
    packet, snapshot, family_spec, policy, render_snapshots, raw_preflight = request
    if (
        type(packet) is not dict
        or type(snapshot) is not dict
        or type(family_spec) is not dict
        or type(policy) is not dict
        or not _is_scoped_evaluation_policy(policy)
        or type(render_snapshots) is not tuple
        or any(type(render) is not dict for render in render_snapshots)
    ):
        raise _error("V4 preflight-bound trial worker request binding drifted")
    preflight = _validated_v4_document_store_render_preflight_v1(
        raw_preflight,
        packet=packet,
        snapshot=snapshot,
    )
    if preflight["completed_result"] is not None:
        raise _error("V4 preflight-bound trial received an already complete result")
    cached_context = _V4_RENDER_PREFLIGHT_CONTEXT_CACHE.pop(preflight["preflight_id"], None)
    if (
        type(cached_context) is not dict
        or set(cached_context)
        != {
            "family_spec_sha256",
            "packet_id",
            "policy_sha256",
            "prepared_context",
            "snapshot_id",
            "topology_candidates_id",
            "topology_scan_id",
        }
        or cached_context.get("packet_id") != packet["packet_id"]
        or cached_context.get("snapshot_id") != snapshot["snapshot_id"]
        or cached_context.get("family_spec_sha256") != canonical_json_sha256_v1(family_spec)
        or cached_context.get("policy_sha256") != canonical_json_sha256_v1(policy)
        or cached_context.get("topology_candidates_id") != preflight["topology_candidates_id"]
        or cached_context.get("topology_scan_id") != preflight["topology_scan_id"]
    ):
        raise _error("V4 preflight-bound trial lost its worker-affine context")
    reservoir = _canonical_authenticated_render_snapshot_order_v1(render_snapshots)
    if (
        not same_typed_json_v1(reservoir, render_snapshots)
        or tuple(render["physical_page"] for render in reservoir) != preflight["reservoir_pages"]
    ):
        raise _error("V4 preflight-bound trial received a different private reservoir")
    prepared_context = cached_context["prepared_context"]
    selected_snapshot, topology_scan, topology_candidates, _candidate_bindings = (
        _open_prepared_v4_document_store_context_v1(
            prepared_context,
            snapshot,
            family_spec,
            policy,
            expected_packet=packet,
            expected_legacy_scan=None,
        )
    )
    if (
        preflight["topology_scan_id"] != topology_scan["scan_id"]
        or preflight["topology_candidates_id"] != topology_candidates["result_id"]
        or not set(preflight["reservoir_pages"])
        <= set(
            _v4_prepruning_candidate_render_pages_v1(
                selected_snapshot["joined_pages"], topology_candidates
            )
        )
    ):
        raise _error("V4 preflight-bound trial topology authority drifted")
    try:
        occurrence_row_v2._validate_snapshot_and_renders(
            selected_snapshot["joined_pages"],
            selected_snapshot,
            reservoir,
            prepared_snapshot=prepared_context.prepared_snapshot,
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("V4 preflight-bound trial render authority drifted") from exc
    reservoir_by_page = {render["physical_page"]: render for render in reservoir}
    revealed_pages = set(preflight["render_pages"])

    def revealed_renders() -> tuple[dict[str, Any], ...]:
        return tuple(reservoir_by_page[page] for page in sorted(revealed_pages))

    runtime_context = {"prepared_context": prepared_context}

    def build_trial() -> dict[str, Any]:
        return _trial_from_document_store_snapshot_v1(
            snapshot,
            family_spec,
            policy,
            render_snapshots=revealed_renders(),
            topology_scan=topology_scan,
            expected_packet=packet,
            _v4_runtime_context=runtime_context,
            _defer_selected_public_replay_for_render=True,
        )

    trial = build_trial()
    # The occurrence-only preflight replaces the ordinary base pass.  Pixels
    # outside ``render_pages`` remain a private reservoir and cannot affect a
    # row, closure, or selector until the unchanged downstream trial requests
    # one exact candidate-scoped page.  If the preflight found no ordinary
    # page, retain the existing FULL -> CANDIDATE_SCOPED two-step axis.
    retry_modes = (
        ("CANDIDATE_SCOPED",) if preflight["render_pages"] else ("FULL", "CANDIDATE_SCOPED")
    )
    for retry_mode in retry_modes:
        if retry_mode == "FULL":
            requested_pages = _missing_render_pages_for_document_store_trial_v1(
                trial,
                trial["topology_scan"],
                selected_snapshot["joined_pages"],
                evaluation_spec=policy,
                topology_candidates=topology_candidates,
            )
        else:
            requested_pages = _v4_candidate_scoped_missing_dimension_render_pages(
                trial,
                selected_snapshot["joined_pages"],
                topology_candidates,
            )
        requested_pages = tuple(page for page in requested_pages if page not in revealed_pages)
        if not requested_pages:
            continue
        if not set(requested_pages) <= set(preflight["reservoir_pages"]):
            raise _error("V4 final trial requested pixels outside its private reservoir")
        revealed_pages.update(requested_pages)
        trial = build_trial()
    remaining_pages = tuple(
        page
        for page in _v4_candidate_scoped_missing_dimension_render_pages(
            trial,
            selected_snapshot["joined_pages"],
            topology_candidates,
        )
        if page not in revealed_pages
    )
    if remaining_pages:
        raise _error("V4 preflight-bound trial exceeded its exact reveal axis")
    return {
        "document_ordinal": packet["document_ordinal"],
        "missing_render_pages": (),
        "packet_id": packet["packet_id"],
        "snapshot_id": snapshot["snapshot_id"],
        "trial": trial,
    }


def _v4_document_store_trial_worker_v1(
    request: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        tuple[dict[str, Any], ...],
        dict[str, Any] | None,
        str,
    ],
) -> dict[str, Any]:
    """Build one source-bound V4 trial in an isolated worker process.

    The authenticated store capability never crosses the process boundary.
    The parent reads one exact packet/snapshot (and, on retry, exact renders),
    while this worker revalidates the complete selected-snapshot contract and
    rebuilds every topology/row/closure/public-replay receipt from those bytes.
    """

    if type(request) is not tuple or len(request) != 7:
        raise _error("V4 document-store worker request shape drifted")
    packet, snapshot, family_spec, policy, render_snapshots, topology_scan, missing_page_mode = (
        request
    )
    if (
        type(packet) is not dict
        or type(snapshot) is not dict
        or type(family_spec) is not dict
        or type(policy) is not dict
        or not _is_scoped_evaluation_policy(policy)
        or type(render_snapshots) is not tuple
        or any(type(render) is not dict for render in render_snapshots)
        or (topology_scan is not None and type(topology_scan) is not dict)
        or missing_page_mode not in _V4_WORKER_MISSING_PAGE_MODES
        or (missing_page_mode == "FULL" and (render_snapshots or topology_scan is not None))
        or (
            missing_page_mode == "CANDIDATE_SCOPED"
            and (not render_snapshots or topology_scan is None)
        )
    ):
        raise _error("V4 document-store worker request binding drifted")
    runtime_context: dict[str, Any] = {}
    trial = _trial_from_document_store_snapshot_v1(
        snapshot,
        family_spec,
        policy,
        render_snapshots=render_snapshots,
        topology_scan=topology_scan,
        expected_packet=packet,
        _v4_runtime_context=runtime_context,
        _defer_selected_public_replay_for_render=True,
    )
    missing_pages: tuple[int, ...] = ()
    if missing_page_mode != "NONE":
        prepared_context = runtime_context.get("prepared_context")
        if type(prepared_context) is not _PreparedV4DocumentStoreContextV1:
            raise _error("V4 document-store worker lost its prepared context")
        _selected, _scan, topology_candidates, _bindings = (
            _open_prepared_v4_document_store_context_v1(
                prepared_context,
                snapshot,
                family_spec,
                policy,
                expected_packet=packet,
                expected_legacy_scan=trial["topology_scan"],
            )
        )
        if missing_page_mode == "FULL":
            render_schedule = runtime_context.get("candidate_render_schedule")
            if render_schedule is not None:
                missing_pages = _open_prepared_v4_candidate_render_schedule_v1(
                    render_schedule,
                    topology_scan=trial["topology_scan"],
                    topology_candidates=topology_candidates,
                    joined_pages=snapshot["joined_pages"],
                )
            else:
                missing_pages = _missing_render_pages_for_document_store_trial_v1(
                    trial,
                    trial["topology_scan"],
                    snapshot["joined_pages"],
                    evaluation_spec=policy,
                    topology_candidates=topology_candidates,
                )
        else:
            rendered_pages = {render["physical_page"] for render in render_snapshots}
            missing_pages = tuple(
                page
                for page in _v4_candidate_scoped_missing_dimension_render_pages(
                    trial,
                    snapshot["joined_pages"],
                    topology_candidates,
                )
                if page not in rendered_pages
            )
    return {
        "document_ordinal": packet["document_ordinal"],
        "missing_render_pages": missing_pages,
        "packet_id": packet["packet_id"],
        "snapshot_id": snapshot["snapshot_id"],
        "trial": trial,
    }


def _validated_v4_document_store_worker_result_v1(
    value: Any,
    *,
    packet: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[int, ...]]:
    """Rebind one worker result to the exact parent-owned packet/snapshot."""

    if (
        type(value) is not dict
        or set(value)
        != {
            "document_ordinal",
            "missing_render_pages",
            "packet_id",
            "snapshot_id",
            "trial",
        }
        or value["document_ordinal"] != packet.get("document_ordinal")
        or value["packet_id"] != packet.get("packet_id")
        or value["snapshot_id"] != snapshot.get("snapshot_id")
        or type(value["trial"]) is not dict
        or value["trial"].get("document_ordinal") != packet.get("document_ordinal")
        or type(value["missing_render_pages"]) is not tuple
        or any(type(page) is not int or page <= 0 for page in value["missing_render_pages"])
        or len(value["missing_render_pages"]) != len(set(value["missing_render_pages"]))
        or tuple(sorted(value["missing_render_pages"])) != value["missing_render_pages"]
        or any(page > packet.get("page_count", 0) for page in value["missing_render_pages"])
    ):
        raise _error("V4 document-store worker result differs from its parent source")
    return value["trial"], value["missing_render_pages"]


def _v4_trial_checkpoint_context_v1(
    document_store_capability: document_store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    family_spec: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    state = document_store_v1._live_store(document_store_capability)
    git_head = document_store_v1._clean_head(state.root)
    family_spec_sha256 = canonical_json_sha256_v1(family_spec)
    policy_sha256 = canonical_json_sha256_v1(policy)
    directory = (
        state.root
        / "data/local/family_first_accounting_trial_checkpoints_v1"
        / f"{git_head}-{family_spec_sha256}-{policy_sha256}"
    )
    return {
        "directory": directory,
        "family_spec_sha256": family_spec_sha256,
        "git_head": git_head,
        "manifest_id": state.manifest["manifest_id"],
        "policy_sha256": policy_sha256,
    }


def _v4_trial_checkpoint_material_v1(
    *,
    binding: Mapping[str, Any],
    packet: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    worker_result: Mapping[str, Any],
) -> dict[str, Any]:
    serialized_result = dict(worker_result)
    if type(serialized_result.get("missing_render_pages")) is not tuple:
        raise _error("V4 document trial checkpoint received a non-runtime worker result")
    serialized_result["missing_render_pages"] = list(serialized_result["missing_render_pages"])
    return {
        "document_ordinal": packet["document_ordinal"],
        "family_spec_sha256": binding["family_spec_sha256"],
        "format_version": _V4_TRIAL_CHECKPOINT_FORMAT_VERSION,
        "git_head": binding["git_head"],
        "manifest_id": binding["manifest_id"],
        "packet_id": packet["packet_id"],
        "policy_sha256": binding["policy_sha256"],
        "snapshot_id": snapshot["snapshot_id"],
        "worker_result": canonical_clone_v1(serialized_result),
        "worker_result_sha256": canonical_json_sha256_v1(serialized_result),
    }


def _v4_trial_checkpoint_bytes_v1(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )


def _read_v4_trial_checkpoint_v1(
    *,
    binding: Mapping[str, Any],
    packet: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> dict[str, Any] | None:
    path = binding["directory"] / f"document-{packet['document_ordinal']:03d}.json"
    if not path.exists():
        return None
    try:
        payload = path.read_bytes()
        value = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _error("V4 document trial checkpoint cannot be read exactly") from exc
    if type(value) is not dict or payload != _v4_trial_checkpoint_bytes_v1(value):
        raise _error("V4 document trial checkpoint is not canonical JSON")
    fields = {
        "checkpoint_id",
        "document_ordinal",
        "family_spec_sha256",
        "format_version",
        "git_head",
        "manifest_id",
        "packet_id",
        "policy_sha256",
        "snapshot_id",
        "worker_result",
        "worker_result_sha256",
    }
    if (
        set(value) != fields
        or value.get("format_version") != _V4_TRIAL_CHECKPOINT_FORMAT_VERSION
        or value.get("document_ordinal") != packet.get("document_ordinal")
        or value.get("packet_id") != packet.get("packet_id")
        or value.get("snapshot_id") != snapshot.get("snapshot_id")
        or value.get("git_head") != binding.get("git_head")
        or value.get("manifest_id") != binding.get("manifest_id")
        or value.get("family_spec_sha256") != binding.get("family_spec_sha256")
        or value.get("policy_sha256") != binding.get("policy_sha256")
        or type(value.get("worker_result")) is not dict
        or value.get("worker_result_sha256") != canonical_json_sha256_v1(value["worker_result"])
    ):
        raise _error("V4 document trial checkpoint binding drifted")
    material = dict(value)
    checkpoint_id = material.pop("checkpoint_id")
    if checkpoint_id != "ffdtcv1:checkpoint:" + canonical_json_sha256_v1(material):
        raise _error("V4 document trial checkpoint identity drifted")
    runtime_result = canonical_clone_v1(value["worker_result"])
    if type(runtime_result.get("missing_render_pages")) is not list:
        raise _error("V4 document trial checkpoint render axis drifted")
    runtime_result["missing_render_pages"] = tuple(runtime_result["missing_render_pages"])
    _trial, missing_pages = _validated_v4_document_store_worker_result_v1(
        runtime_result,
        packet=packet,
        snapshot=snapshot,
    )
    if missing_pages:
        raise _error("V4 document trial checkpoint retained a render request")
    return runtime_result


def _write_v4_trial_checkpoint_v1(
    *,
    binding: Mapping[str, Any],
    packet: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    worker_result: Mapping[str, Any],
) -> None:
    material = _v4_trial_checkpoint_material_v1(
        binding=binding,
        packet=packet,
        snapshot=snapshot,
        worker_result=worker_result,
    )
    value = {
        **material,
        "checkpoint_id": "ffdtcv1:checkpoint:" + canonical_json_sha256_v1(material),
    }
    payload = _v4_trial_checkpoint_bytes_v1(value)
    directory: Path = binding["directory"]
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"document-{packet['document_ordinal']:03d}.json"
    if path.exists():
        observed = _read_v4_trial_checkpoint_v1(
            binding=binding,
            packet=packet,
            snapshot=snapshot,
        )
        if not same_typed_json_v1(observed, worker_result):
            raise _error("V4 document trial checkpoint conflicts with fresh evidence")
        return
    temporary = directory / f".{path.name}.{os.getpid()}.tmp"
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            remaining = memoryview(payload)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError("document trial checkpoint write made no progress")
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, path)
        path.chmod(0o444)
    except OSError as exc:
        raise _error("V4 document trial checkpoint cannot be published atomically") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _parallel_v4_document_store_trials_v1(
    document_store_capability: document_store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    *,
    packets: tuple[dict[str, Any], ...],
    selections: tuple[tuple[int, tuple[int, ...]], ...],
    family_spec: dict[str, Any],
    policy: dict[str, Any],
    jobs: int,
) -> list[dict[str, Any]]:
    """Run bounded document trials in source order with parent-owned I/O."""

    final_trials: list[dict[str, Any] | None] = [None] * len(packets)
    checkpoint_binding = _v4_trial_checkpoint_context_v1(
        document_store_capability,
        family_spec,
        policy,
    )
    try:
        # Spawn is a security boundary, not a portability preference.  Fork
        # would inherit the parent module's opaque authenticated-store handle
        # registry even though the capability is intentionally absent from
        # every worker request.
        with ExitStack() as executor_stack:
            executors = tuple(
                executor_stack.enter_context(
                    ProcessPoolExecutor(
                        max_workers=1,
                        mp_context=get_context("spawn"),
                    )
                )
                for _ in range(jobs)
            )
            active_snapshots: dict[int, dict[str, Any]] = {}
            ready_source_indices: list[int] = []
            free_lanes = list(range(jobs))
            pending: dict[Any, tuple[int, str, int]] = {}
            next_source_index = 0

            def submit_preflight(index: int, lane: int) -> None:
                packet = packets[index]
                future = executors[lane].submit(
                    _v4_document_store_render_preflight_worker_v1,
                    (packet, active_snapshots[index], family_spec, policy),
                )
                pending[future] = (index, "PREFLIGHT", lane)

            def hydrate_next_batch() -> None:
                nonlocal next_source_index
                requested = selections[
                    next_source_index : next_source_index + _DOCUMENT_STORE_SELECTED_PAGE_BATCH_SIZE
                ]
                if not requested:
                    return
                snapshots = (
                    document_store_v1.read_authenticated_family_first_documents_selected_pages_v1(
                        document_store_capability,
                        document_page_selections=requested,
                    )
                )
                if type(snapshots) is not tuple or len(snapshots) != len(requested):
                    raise _error("V4 document-store selected snapshot batch axis drifted")
                for offset, snapshot in enumerate(snapshots):
                    index = next_source_index + offset
                    active_snapshots[index] = snapshot
                    cached_result = _read_v4_trial_checkpoint_v1(
                        binding=checkpoint_binding,
                        packet=packets[index],
                        snapshot=snapshot,
                    )
                    if cached_result is not None:
                        cached_trial, _missing_pages = (
                            _validated_v4_document_store_worker_result_v1(
                                cached_result,
                                packet=packets[index],
                                snapshot=snapshot,
                            )
                        )
                        final_trials[index] = cached_trial
                        del active_snapshots[index]
                        continue
                    ready_source_indices.append(index)
                next_source_index += len(snapshots)

            def dispatch_free_lanes() -> None:
                while free_lanes and not ready_source_indices and next_source_index < len(packets):
                    hydrate_next_batch()
                while free_lanes and ready_source_indices:
                    lane = free_lanes.pop(0)
                    index = ready_source_indices.pop(0)
                    submit_preflight(index, lane)

            dispatch_free_lanes()
            while pending:
                completed, _remaining = wait(
                    tuple(pending),
                    return_when=FIRST_COMPLETED,
                )
                for future in sorted(completed, key=lambda item: pending[item]):
                    index, stage, lane = pending.pop(future)
                    packet = packets[index]
                    snapshot = active_snapshots[index]
                    if stage == "PREFLIGHT":
                        preflight = _validated_v4_document_store_render_preflight_v1(
                            future.result(),
                            packet=packet,
                            snapshot=snapshot,
                        )
                        completed_result = preflight.get("completed_result")
                        if completed_result is not None:
                            trial, missing_pages = _validated_v4_document_store_worker_result_v1(
                                completed_result,
                                packet=packet,
                                snapshot=snapshot,
                            )
                            if missing_pages:
                                raise _error("V4 completed preflight retained a render request")
                            final_trials[index] = trial
                            _write_v4_trial_checkpoint_v1(
                                binding=checkpoint_binding,
                                packet=packet,
                                snapshot=snapshot,
                                worker_result=completed_result,
                            )
                            del active_snapshots[index]
                            free_lanes.append(lane)
                            continue
                        reservoir = (
                            document_store_v1.read_authenticated_family_first_document_page_renders_v1(
                                document_store_capability,
                                document_ordinal=packet["document_ordinal"],
                                physical_pages=preflight["reservoir_pages"],
                            )
                            if preflight["reservoir_pages"]
                            else ()
                        )
                        final_future = executors[lane].submit(
                            _v4_document_store_preflight_bound_trial_worker_v1,
                            (
                                packet,
                                snapshot,
                                family_spec,
                                policy,
                                reservoir,
                                preflight,
                            ),
                        )
                        pending[final_future] = (index, "FINAL", lane)
                        continue
                    if stage != "FINAL":
                        raise _error("V4 document-store worker stage drifted")
                    final_result = future.result()
                    trial, missing_pages = _validated_v4_document_store_worker_result_v1(
                        final_result,
                        packet=packet,
                        snapshot=snapshot,
                    )
                    if missing_pages:
                        raise _error("V4 preflight-bound final trial retained a render request")
                    final_trials[index] = trial
                    _write_v4_trial_checkpoint_v1(
                        binding=checkpoint_binding,
                        packet=packet,
                        snapshot=snapshot,
                        worker_result=final_result,
                    )
                    del active_snapshots[index]
                    free_lanes.append(lane)
                free_lanes.sort()
                dispatch_free_lanes()
            if next_source_index != len(packets) or active_snapshots or ready_source_indices:
                raise _error("V4 document-store worker window lost its source axis")
            if any(trial is None for trial in final_trials):
                raise _error("V4 document-store worker batch lost a source trial")
    except FamilyFirstAccountingEvidenceSweepV1Error:
        raise
    except Exception as exc:
        raise _error("V4 document-store worker execution failed") from exc
    return [trial for trial in final_trials if trial is not None]


def build_authenticated_family_first_accounting_evidence_sweep_from_document_store_v1(
    document_store_capability: document_store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    family_spec: Any,
    evaluation_spec: Any,
    *,
    jobs: int = 1,
) -> dict[str, Any]:
    """Build one family from root-checked document packets without replaying OCR.

    Every document packet is independently recomputed from the registered
    SQLite evidence store. The complete document text/geometry/numeric axis is
    still scanned, but unchanged PDF extraction and model inference are never
    repeated. Render-only dash rescue remains deliberately out of scope and
    such a row stays unresolved for a later page-local refresh.
    """

    try:
        compiled = topology_v1._spec(family_spec)
    except (ValueError, RuntimeError) as exc:
        raise _error("family topology specification drifted") from exc
    policy = _evaluation_spec(evaluation_spec, compiled, raw_family_spec=family_spec)
    projection = document_store_v1.project_authenticated_family_first_document_evidence_store_v1(
        document_store_capability
    )
    document_count = projection["metrics"]["document_count"]
    if type(jobs) is not int or not 1 <= jobs <= _MAX_DOCUMENT_STORE_V4_JOBS:
        raise _error("document-store worker count must be an integer from 1 to 16")
    if jobs != 1 and not _is_scoped_evaluation_policy(policy):
        raise _error("parallel document-store trials require evaluation V4")
    if _is_scoped_evaluation_policy(policy):
        topology_scans = None
    else:
        topology_scans = document_store_v1.read_authenticated_family_first_topology_scans_v1(
            document_store_capability,
            family_spec,
        )
        if len(topology_scans) != document_count:
            raise _error("document-store topology denominator differs from its packet axis")
    trials = []
    if _is_scoped_evaluation_policy(policy):
        packets = tuple(
            document_store_v1.read_authenticated_family_first_document_packet_v1(
                document_store_capability,
                document_ordinal=ordinal,
            )
            for ordinal in range(1, document_count + 1)
        )
        if [packet.get("document_ordinal") for packet in packets] != list(
            range(1, document_count + 1)
        ):
            raise _error("V4 document-store packet source order drifted")
        selections = tuple(
            (
                packet["document_ordinal"],
                tuple(range(1, packet["page_count"] + 1)),
            )
            for packet in packets
        )
        if jobs == 1:
            for start in range(0, document_count, _DOCUMENT_STORE_SELECTED_PAGE_BATCH_SIZE):
                requested = selections[start : start + _DOCUMENT_STORE_SELECTED_PAGE_BATCH_SIZE]
                snapshots = (
                    document_store_v1.read_authenticated_family_first_documents_selected_pages_v1(
                        document_store_capability,
                        document_page_selections=requested,
                    )
                )
                if type(snapshots) is not tuple or len(snapshots) != len(requested):
                    raise _error("V4 document-store selected snapshot batch axis drifted")
                for offset, snapshot in enumerate(snapshots):
                    packet = packets[start + offset]
                    trials.append(
                        _document_store_trial_with_render_rescue_v1(
                            document_store_capability,
                            packet=packet,
                            snapshot=snapshot,
                            family_spec=family_spec,
                            policy=policy,
                            topology_scan=None,
                        )
                    )
        else:
            trials = _parallel_v4_document_store_trials_v1(
                document_store_capability,
                packets=packets,
                selections=selections,
                family_spec=family_spec,
                policy=policy,
                jobs=jobs,
            )
    else:
        for ordinal in range(1, document_count + 1):
            packet = document_store_v1.read_authenticated_family_first_document_packet_v1(
                document_store_capability,
                document_ordinal=ordinal,
            )
            snapshot = (
                document_store_v1.read_authenticated_family_first_document_evidence_snapshot_v1(
                    document_store_capability,
                    document_ordinal=ordinal,
                    selected_pages=tuple(range(1, packet["page_count"] + 1)),
                )
            )
            trials.append(
                _document_store_trial_with_render_rescue_v1(
                    document_store_capability,
                    packet=packet,
                    snapshot=snapshot,
                    family_spec=family_spec,
                    policy=policy,
                    topology_scan=topology_scans[ordinal - 1],
                )
            )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "evaluation_spec": {
            "sha256": canonical_json_sha256_v1(policy),
            "value": canonical_clone_v1(policy),
        },
        "family_id": compiled["family_id"],
        "family_spec": {
            "sha256": canonical_json_sha256_v1(family_spec),
            "value": canonical_clone_v1(family_spec),
        },
        "format_version": FORMAT_VERSION,
        "input_indices": {
            "numeric_receipt_id": projection["input_indices"]["numeric_receipt_id"],
            "semantic_index_id": projection["input_indices"]["semantic_index_id"],
        },
        "metrics": _metrics(trials),
        "state": "ALL_FILING_ACCOUNTING_EVIDENCE_SWEEP_COMPLETE_PROPOSAL_ONLY",
        "trials": trials,
    }
    return _validate(
        {**material, "sweep_id": "ffaesv1:sweep:" + canonical_json_sha256_v1(material)}
    )


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    ready = sum(
        trial["evidence_status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
        for trial in trials
    )
    unique = sum(
        trial["topology_scan"]["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL" for trial in trials
    )
    not_observed = sum(trial["evidence_status"] == "NOT_OBSERVED_PROPOSAL_ONLY" for trial in trials)
    return {
        "document_count": len(trials),
        "evidence_ready_for_schema_review_count": ready,
        "mapping_verified_count": 0,
        "not_observed_count": not_observed,
        "unique_topology_document_count": unique,
        "unresolved_document_count": len(trials) - ready - not_observed,
    }


def _validate(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "ALL_FILING_ACCOUNTING_EVIDENCE_SWEEP_COMPLETE_PROPOSAL_ONLY"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["family_spec"]) is not dict
        or set(value["family_spec"]) != {"sha256", "value"}
        or value["family_spec"]["sha256"] != canonical_json_sha256_v1(value["family_spec"]["value"])
        or type(value["evaluation_spec"]) is not dict
        or set(value["evaluation_spec"]) != {"sha256", "value"}
        or value["evaluation_spec"]["sha256"]
        != canonical_json_sha256_v1(value["evaluation_spec"]["value"])
        or type(value["input_indices"]) is not dict
        or set(value["input_indices"]) != _INDEX_FIELDS
        or any(type(item) is not str or not item for item in value["input_indices"].values())
        or not value["input_indices"]["numeric_receipt_id"].startswith("ffpniv3:receipt:")
        or not value["input_indices"]["semantic_index_id"].startswith("ffsiv1:index:")
        or type(value["trials"]) is not list
    ):
        raise _error("family-first accounting evidence sweep shape drifted")
    evaluation_format = value["evaluation_spec"]["value"].get("format_version")
    expected_trial_fields = (
        _TRIAL_FIELDS_V4 if _is_scoped_evaluation_format(evaluation_format) else _TRIAL_FIELDS
    )
    for ordinal, trial in enumerate(value["trials"], 1):
        if (
            type(trial) is not dict
            or set(trial) != expected_trial_fields
            or trial["document_ordinal"] != ordinal
            or type(trial["private_provenance"]) is not dict
            or type(trial["source_pdf_ref"]) is not dict
            or type(trial["topology_scan"]) is not dict
            or type(trial["evidence_status"]) is not str
            or type(trial["unresolved_reasons"]) is not list
            or any(type(reason) is not str or not reason for reason in trial["unresolved_reasons"])
        ):
            raise _error("family-first accounting evidence trial axis drifted")
        if trial["document_axis_binding"] is not None and (
            type(trial["document_axis_binding"]) is not dict
            or set(trial["document_axis_binding"]) != _BINDING_FIELDS
        ):
            raise _error("family-first document-axis binding drifted")
        if _is_scoped_evaluation_format(evaluation_format):
            receipt = trial["one_edit_exact_authority_receipt"]
            if (
                trial["evidence_status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
                and receipt is None
            ):
                raise _error("family-first V4 ready trial lacks one-edit authority receipt")
            if receipt is not None:
                try:
                    receipt = one_edit_v1.validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(
                        receipt
                    )
                except one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error as exc:
                    raise _error("family-first V4 one-edit authority receipt drifted") from exc
                if (
                    receipt["family_id"] != value["family_id"]
                    or receipt["input_binding"]["family_spec_sha256"]
                    != value["family_spec"]["sha256"]
                    or trial["evidence_status"]
                    not in {
                        "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
                        "UNRESOLVED_EVIDENCE_GATES",
                    }
                    or any(
                        reason not in trial["unresolved_reasons"]
                        for reason in receipt["unresolved_reasons"]
                    )
                    or (
                        receipt["unresolved_reasons"]
                        and trial["evidence_status"] != "UNRESOLVED_EVIDENCE_GATES"
                    )
                ):
                    raise _error("family-first V4 one-edit authority status binding drifted")
                closure_proofs = (
                    trial["additive_closure"].get("one_edit_exact_source_structural_proofs")
                    if type(trial["additive_closure"]) is dict
                    else None
                )
                if closure_proofs is not None and not same_typed_json_v1(
                    closure_proofs,
                    receipt,
                ):
                    raise _error(
                        "family-first V4 selected one-edit receipt differs from closure proof"
                    )
    if (
        type(value["metrics"]) is not dict
        or set(value["metrics"]) != _METRIC_FIELDS
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("family-first accounting evidence sweep metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("sweep_id")
    if identity != "ffaesv1:sweep:" + canonical_json_sha256_v1(material):
        raise _error("family-first accounting evidence sweep identity drifted")
    return canonical_clone_v1(value)


def build_authenticated_family_first_accounting_evidence_sweep_v1(
    semantic_index_capability: semantic_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    numeric_index_capability: numeric_v3.AuthenticatedFamilyFirstPPocrV6NumericIndexV3,
    family_spec: Any,
    evaluation_spec: Any,
) -> dict[str, Any]:
    """Apply one generic family policy to every authenticated filing."""

    try:
        compiled = topology_v1._spec(family_spec)
    except (ValueError, RuntimeError) as exc:
        raise _error("family topology specification drifted") from exc
    policy = _evaluation_spec(evaluation_spec, compiled, raw_family_spec=family_spec)
    if _is_scoped_evaluation_policy(policy):
        raise _error("V4_REQUIRES_AUTHENTICATED_DOCUMENT_STORE_SELECTED_SNAPSHOT")
    try:
        semantic_projection = semantic_v1.project_authenticated_family_first_semantic_index_v1(
            semantic_index_capability
        )
        numeric_projection = numeric_v3.project_authenticated_family_first_ppocrv6_numeric_index_v3(
            numeric_index_capability
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("family-first accounting sweep inputs are not authenticated") from exc
    semantic_metrics = semantic_projection["metrics"]
    numeric_metrics = numeric_projection["metrics"]
    for key in ("document_count", "page_count", "sample_count"):
        if (
            type(semantic_metrics[key]) is not int
            or type(numeric_metrics[key]) is not int
            or semantic_metrics[key] != numeric_metrics[key]
        ):
            raise _error("semantic and numeric index denominators differ")
    semantic_documents = snapshot_v1.read_authenticated_family_first_semantic_documents_snapshot_v1(
        semantic_index_capability,
        document_ordinals=tuple(range(1, semantic_metrics["document_count"] + 1)),
    )
    prepared = []
    for document in semantic_documents:
        topology_pages = _blind_pages(document)
        if _is_scoped_evaluation_policy(policy):
            topology_scan, topology_candidates = _v4_topology_authority(
                topology_pages,
                family_spec,
            )
        else:
            topology_scan = topology_v1.build_accounting_family_topology_scan_v1(
                topology_pages,
                family_spec,
            )
            topology_candidates = None
        prepared.append((document, topology_scan, topology_candidates))

    accepted = [
        (document, topology_scan, topology_candidates)
        for document, topology_scan, topology_candidates in prepared
        if (topology_candidates or topology_scan)["status"]
        in {
            "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
            "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
        }
    ]
    numeric_by_document = {}
    renders_by_document: dict[int, list[dict[str, Any]]] = {}
    if accepted:
        ordinals = tuple(document["document_ordinal"] for document, _scan, _candidates in accepted)
        numeric_documents = (
            snapshot_v1.read_authenticated_family_first_numeric_documents_snapshot_v1(
                numeric_index_capability, document_ordinals=ordinals
            )
        )
        numeric_by_document = {
            document["document_ordinal"]: document for document in numeric_documents
        }
        selections = tuple(
            {
                "document_ordinal": document_ordinal,
                "physical_page": physical_page,
            }
            for document_ordinal, physical_page in sorted(
                {
                    (document["document_ordinal"], page)
                    for document, topology_scan, topology_candidates in accepted
                    for region in (topology_candidates or topology_scan)["regions"]
                    for page in _region_pages(document, region)
                }
            )
        )
        render_snapshots = render_v1.read_authenticated_family_first_page_renders_v1(
            semantic_index_capability, selections=selections
        )
        for snapshot in render_snapshots:
            renders_by_document.setdefault(snapshot["document_ordinal"], []).append(snapshot)

    trials = [
        _trial(
            document,
            topology_scan,
            family_spec,
            policy,
            numeric_document=numeric_by_document.get(document["document_ordinal"]),
            render_snapshots=tuple(renders_by_document.get(document["document_ordinal"], [])),
            topology_candidates=topology_candidates,
        )
        for document, topology_scan, topology_candidates in prepared
    ]
    snapshot_v1.validate_authenticated_family_first_semantic_documents_snapshot_v1(
        semantic_index_capability, semantic_documents
    )
    final_semantic_projection = semantic_v1.project_authenticated_family_first_semantic_index_v1(
        semantic_index_capability
    )
    final_numeric_projection = (
        numeric_v3.project_authenticated_family_first_ppocrv6_numeric_index_v3(
            numeric_index_capability
        )
    )
    if not same_typed_json_v1(
        final_semantic_projection, semantic_projection
    ) or not same_typed_json_v1(final_numeric_projection, numeric_projection):
        raise _error("family-first accounting sweep inputs changed during batch construction")
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "evaluation_spec": {
            "sha256": canonical_json_sha256_v1(policy),
            "value": policy,
        },
        "family_id": compiled["family_id"],
        "family_spec": {
            "sha256": canonical_json_sha256_v1(family_spec),
            "value": canonical_clone_v1(family_spec),
        },
        "format_version": FORMAT_VERSION,
        "input_indices": {
            "numeric_receipt_id": numeric_projection["receipt_id"],
            "semantic_index_id": semantic_projection["index_id"],
        },
        "metrics": _metrics(trials),
        "state": "ALL_FILING_ACCOUNTING_EVIDENCE_SWEEP_COMPLETE_PROPOSAL_ONLY",
        "trials": trials,
    }
    return _validate(
        {**material, "sweep_id": "ffaesv1:sweep:" + canonical_json_sha256_v1(material)}
    )


def validate_authenticated_family_first_accounting_evidence_sweep_replay_v1(
    value: Any,
    semantic_index_capability: semantic_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    numeric_index_capability: numeric_v3.AuthenticatedFamilyFirstPPocrV6NumericIndexV3,
    family_spec: Any,
    evaluation_spec: Any,
) -> dict[str, Any]:
    """Exact-rebuild the persisted all-filing evidence proposal."""

    persisted = _validate(value)
    expected = build_authenticated_family_first_accounting_evidence_sweep_v1(
        semantic_index_capability,
        numeric_index_capability,
        family_spec,
        evaluation_spec,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("family-first accounting evidence sweep does not replay exactly")
    return persisted
