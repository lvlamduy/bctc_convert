"""Add-only local multi-level header wrapper over sealed column V1.

V1 remains byte-for-byte sealed.  This wrapper always builds V1 first and
returns that exact result unless all of the following hold: V1 is unresolved,
the caller declared ``BALANCE_COMPARATIVE``, the lane kinds are mixed, and one
header band after the active explicit parent, or after one exact contextual
subgroup on the same/immediately following page, and before the first body row
is fully proved by the shared multi-level leaf projector.

The projected V2 context keeps the V1 consumer field shape.  Currency and
magnitude still come from V1's existing local/document unit gate; the leaf
projector supplies only period-parent propagation and visible lane kinds.
"""

from __future__ import annotations

import hashlib
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import accounting_family_column_context_v1 as column_v1
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_axis_v1
from bctc_ai.evaluation import accounting_multilevel_header_leaf_axis_v1 as leaf_axis_v1
from bctc_ai.evaluation.accounting_table_axes_v1 import accounting_unit_surface_v1
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "PINNED_IMPLEMENTATION_REFS",
    "AccountingFamilyColumnContextMultilevelV2Error",
    "build_accounting_family_column_context_multilevel_v2",
    "validate_accounting_family_column_context_multilevel_replay_v2",
]


FORMAT_VERSION = "ACCOUNTING_FAMILY_COLUMN_CONTEXT_MULTILEVEL_V2"
CLAIM_BOUNDARY = (
    "EXACT_V1_FIRST_THEN_ACTIVE_PARENT_OR_EXACT_CONTEXTUAL_SAME_OR_NEXT_PAGE_RESET_"
    "FENCED_TWO_PERIOD_MULTI_LEVEL_MIXED_OR_CONTEXTUAL_MONEY_HEADER_LEAF_"
    "PROJECTION_WITH_EXISTING_V1_UNIT_GATE_"
    "PROPOSAL_ONLY_NO_NUMERIC_ACCOUNTING_POPULATION_SCHEMA_MAPPING_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "active_explicit_parent_and_cluster_fence_required": True,
    "bank_file_note_page_or_fixed_year_used_for_routing": False,
    "baseline_local_unit_axis_reused_without_active_fence": False,
    "cross_page_continuation_fallback_allowed": True,
    "currency_or_magnitude_inferred_from_money_leaf_kind": False,
    "mapping_authority": False,
    "mixed_or_contextual_money_balance_comparative_fallback_only": True,
    "numeric_authority": False,
    "prior_table_or_reset_header_can_supply_projector_evidence": False,
    "schema_authority": False,
    "sealed_v1_non_axis_failure_can_be_erased": False,
    "sealed_v1_built_before_fallback": True,
}
_FALLBACK_ELIGIBLE_V1_REASONS = {
    "PERIOD_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN",
    "UNIT_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN",
}
_CONTEXTUAL_NEXT_PAGE_ELIGIBLE_V1_REASONS = {
    *_FALLBACK_ELIGIBLE_V1_REASONS,
    "CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN",
    "LOCAL_HEADER_REGION_UNRESOLVED",
}
_CONTEXTUAL_SAME_PAGE_ELIGIBLE_V1_REASONS = {
    *_FALLBACK_ELIGIBLE_V1_REASONS,
    # The sealed V1 receipt conservatively treats the outer topology region as
    # cross-page even when one exact contextual owner and every valued row are
    # confined to the local header page.  The V2 projector independently
    # proves that exact owner and all-row ownership before consulting this
    # allow-set, so the outer sibling-table continuation cannot supply period
    # or unit evidence to the local table.
    "CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN",
    "LOCAL_HEADER_REGION_UNRESOLVED",
}
PINNED_IMPLEMENTATION_REFS = {
    "sealed_column_context_v1": {
        "path": "src/bctc_ai/evaluation/accounting_family_column_context_v1.py",
        "sha256": "0f7f9acb36f75afe8eb7d377ab6c14d8a8186c6eac3da55a9dce7dcc76439a22",
        "size_bytes": 55_297,
    },
    "multilevel_header_leaf_axis_v1": {
        "path": "src/bctc_ai/evaluation/accounting_multilevel_header_leaf_axis_v1.py",
        "sha256": "35e21f567ab220ea1293033a9fff0053a0e2a46f8b2587e160721039481598c2",
        "size_bytes": 40_483,
    },
}
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class AccountingFamilyColumnContextMultilevelV2Error(ValueError):
    """The pinned engines, V2 context, identity, or exact replay drifted."""


def _error(message: str) -> AccountingFamilyColumnContextMultilevelV2Error:
    return AccountingFamilyColumnContextMultilevelV2Error(message)


def _stable_ref(path: Path) -> dict[str, Any]:
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error("multilevel column-context engine is not one regular nofollow file")
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise _error("multilevel column-context engine cannot be read stably") from exc
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
    )
    if before_identity != after_identity or len(payload) != before.st_size:
        raise _error("multilevel column-context engine changed during stable read")
    return {
        "path": path.relative_to(_PROJECT_ROOT).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _validate_pinned_implementation_refs() -> None:
    observed = {
        key: _stable_ref(_PROJECT_ROOT / reference["path"])
        for key, reference in PINNED_IMPLEMENTATION_REFS.items()
    }
    if not same_typed_json_v1(observed, PINNED_IMPLEMENTATION_REFS):
        raise _error("multilevel column-context pinned implementation reference drifted")


def _surface_hits_alias(surface: str, aliases: Sequence[str]) -> bool:
    normalized = normalize_vietnamese_anchor_v1(surface)
    return any(normalized == alias or normalized.startswith(alias + " ") for alias in aliases)


def _contains_parent_or_reset_fence(
    lines: Sequence[Mapping[str, Any]], family_topology_spec: Mapping[str, Any]
) -> bool:
    raw_parent = family_topology_spec.get("parent")
    raw_resets = family_topology_spec.get("structural_reset_aliases")
    limits = family_topology_spec.get("limits")
    if (
        type(raw_parent) is not dict
        or type(raw_parent.get("aliases")) is not list
        or type(raw_resets) is not list
        or type(limits) is not dict
        or type(limits.get("max_label_line_span")) is not int
    ):
        raise _error("multilevel column-context topology fence declaration drifted")
    aliases = [
        normalize_vietnamese_anchor_v1(alias)
        for alias in [*raw_parent["aliases"], *raw_resets]
        if type(alias) is str and alias.strip()
    ]
    max_span = limits["max_label_line_span"]
    if not aliases or max_span <= 0:
        return False
    ordered = sorted(lines, key=lambda line: line["source_line_index"])
    for start in range(len(ordered)):
        for width in range(1, min(max_span, len(ordered) - start) + 1):
            selected = ordered[start : start + width]
            if any(
                right["source_line_index"] != left["source_line_index"] + 1
                for left, right in zip(selected, selected[1:], strict=False)
            ):
                continue
            surface = " ".join(line["vietocr_text"] for line in selected)
            if _surface_hits_alias(surface, aliases):
                return True
    return False


def _fenced_header_lines(
    axis: Mapping[str, Any],
    parsed_pages: Sequence[Mapping[str, Any]],
    family_topology_spec: Mapping[str, Any],
    centers: Sequence[float],
) -> tuple[list[dict[str, Any]], int] | None:
    """Return only evidence inside the active explicit-parent table header."""

    region = axis["topology_region"]
    value_rows = [row for row in axis["rows"] if row["values"]]
    if (
        type(region) is not dict
        or region.get("parent_resolution") != "EXPLICIT_PARENT"
        or type(region.get("parent_match")) is not dict
        or not value_rows
        or not centers
    ):
        return None
    parent = region["parent_match"]
    first_body = min(
        (row["label_match"] for row in value_rows),
        key=lambda match: column_v1._visual_match_key(parsed_pages, match),
    )
    header_owner = _active_header_owner(region, parent, first_body)
    if header_owner is None:
        return None
    header_page = first_body["page_sequence"]
    contextual_owner = header_owner is not parent
    if contextual_owner and not _contextual_header_owner_covers_value_rows(
        header_owner,
        value_rows,
        header_page,
    ):
        return None
    if parent["page_sequence"] != header_page and (
        not contextual_owner or region["continuation_page_count"] != 1
    ):
        return None
    start = max(
        region["cluster_start_document_line_ordinal"],
        header_owner["end_document_line_ordinal"] + 1,
    )
    stop = min(
        first_body["document_line_ordinal"],
        region["cluster_end_document_line_ordinal_exclusive"],
    )
    offset = 0
    selected = []
    if start < stop:
        for page in parsed_pages:
            for line in page["lines"]:
                document_ordinal = offset + line["line_ordinal"]
                if (
                    page["page_sequence"] == header_page
                    and start <= document_ordinal < stop
                    and line["vietocr_text"].strip()
                ):
                    selected.append(_header_line_record(line))
            offset += len(page["lines"])
        if selected and not _contains_parent_or_reset_fence(selected, family_topology_spec):
            return selected, header_page

    # Some tables print the complete period/unit leaf header immediately above
    # the explicit owner, followed directly by the first body row.  Admit only
    # the body-column band in a DPI-relative visual lookback.  The downstream
    # leaf projector must still prove the complete mixed lane axis from this
    # band alone; a prior table that exposes only dates/global unit remains U.
    page = next(item for item in parsed_pages if item["page_sequence"] == header_page)
    owner_lines = column_v1._match_geometry(parsed_pages, header_owner)
    if not owner_lines:
        return None
    owner_top = min(line["bbox"][1] for line in owner_lines)
    scale = row_axis_v1.median_text_height_v1(page["lines"])
    lane_gap = (
        min(right - left for left, right in zip(centers, centers[1:], strict=False))
        if len(centers) > 1
        else scale * 8.0
    )
    band_left = centers[0] - lane_gap * 0.5
    band_right = centers[-1] + lane_gap * 0.5
    lookback_top = owner_top - scale * 10.0
    selected = [
        _header_line_record(line)
        for line in page["lines"]
        if line["vietocr_text"].strip()
        and line["bbox"][1] < owner_top
        and line["bbox"][3] >= lookback_top
        and line["bbox"][2] >= band_left
        and line["bbox"][0] <= band_right
    ]
    if not selected or _contains_parent_or_reset_fence(selected, family_topology_spec):
        return None
    return selected, header_page


def _contextual_header_owner_covers_value_rows(
    owner: Mapping[str, Any],
    value_rows: Sequence[Mapping[str, Any]],
    header_page: int,
) -> bool:
    """Require every valued row to replay under one exact local subgroup."""

    role = owner.get("role")
    if type(role) is not str or not role:
        return False
    occurrence_id = owner.get("occurrence_id")
    for row in value_rows:
        label = row["label_match"]
        if label.get("page_sequence") != header_page or label.get("matched_within_role") != role:
            return False
        scope_owner_id = label.get("scope_owner_occurrence_id")
        if scope_owner_id is not None and (
            type(scope_owner_id) is not str
            or not scope_owner_id
            or type(occurrence_id) is not str
            or occurrence_id != scope_owner_id
        ):
            return False
    return True


def _active_header_owner(
    region: Mapping[str, Any],
    parent: Mapping[str, Any],
    first_body: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    """Bind the header fence to the first valued row's exact structural owner.

    A loan-note parent can contain several sibling tables before the requested
    family branch.  Contextual topology already seals the structural owner of
    each child row; use that owner as the local header fence instead of
    importing every header beneath the outer note parent.  Non-contextual
    layouts retain the existing explicit-parent fence.
    """

    within_role = first_body.get("matched_within_role")
    if within_role is None:
        return parent
    if type(within_role) is not str or not within_role:
        return None
    candidates = [
        match
        for match in region["child_matches"]
        if match.get("role") == within_role and match.get("role_kind") == "STRUCTURAL_GROUP"
    ]
    if len(candidates) != 1:
        return None
    owner = candidates[0]
    if (
        type(owner.get("match_kind")) is not str
        or not owner["match_kind"].startswith("EXACT_")
        or owner.get("page_sequence") != first_body.get("page_sequence")
        or type(owner.get("document_line_ordinal")) is not int
        or type(owner.get("end_document_line_ordinal")) is not int
        or owner["document_line_ordinal"] <= parent["end_document_line_ordinal"]
        or owner["end_document_line_ordinal"] >= first_body["document_line_ordinal"]
    ):
        return None
    occurrence_id = owner.get("occurrence_id")
    scope_owner_id = first_body.get("scope_owner_occurrence_id")
    if scope_owner_id is not None and (
        type(scope_owner_id) is not str
        or not scope_owner_id
        or type(occurrence_id) is not str
        or occurrence_id != scope_owner_id
    ):
        return None
    if any(
        match is not owner
        and match.get("role_kind") == "STRUCTURAL_GROUP"
        and match.get("page_sequence") == owner["page_sequence"]
        and type(match.get("document_line_ordinal")) is int
        and owner["end_document_line_ordinal"]
        < match["document_line_ordinal"]
        < first_body["document_line_ordinal"]
        for match in region["child_matches"]
    ):
        return None
    return owner


def _header_line_record(line: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bbox": canonical_clone_v1(line["bbox"]),
        "numeric_score": line["numeric_recognition"]["reader_score"],
        "numeric_text": line["numeric_recognition"]["raw_prediction"],
        "source_line_index": line["line_ordinal"],
        "vietocr_text": line["vietocr_text"],
    }


def _shared_unit_axis(
    header_lines: Sequence[Mapping[str, Any]],
    header_page: int,
    centers: Sequence[float],
    expected_kinds: Sequence[str],
    document_unit_context: Mapping[str, Any],
    leaves: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if len(leaves) != len(centers) or [leaf["lane_kind"] for leaf in leaves] != list(
        expected_kinds
    ):
        return []
    leaf_indices = {
        index for leaf in leaves for index in leaf["header_evidence_source_line_indices"]
    }
    shared_money = column_v1._unit_axis(
        [line for line in header_lines if line["source_line_index"] not in leaf_indices],
        header_page,
        centers,
        ["MONEY"] * len(centers),
        document_unit_context,
    )
    shared_money_available = len(shared_money) == len(centers)
    explicit_money_by_lane = {
        leaf["column_ordinal"]: accounting_unit_surface_v1(leaf["header_surface"])
        for leaf in leaves
        if leaf["lane_kind"] == "MONEY"
    }
    if not shared_money_available:
        if not explicit_money_by_lane or any(
            unit is None or unit["unit_kind"] != "MONEY" for unit in explicit_money_by_lane.values()
        ):
            return []
        explicit_signatures = {
            (unit["unit_kind"], unit["currency"], unit["magnitude_power10"])
            for unit in explicit_money_by_lane.values()
            if unit is not None
        }
        if len(explicit_signatures) != 1:
            return []
        remaining_explicit_units = [
            unit
            for line in header_lines
            if line["source_line_index"] not in leaf_indices
            and (unit := accounting_unit_surface_v1(line["vietocr_text"])) is not None
        ]
        if remaining_explicit_units and any(
            (unit["unit_kind"], unit["currency"], unit["magnitude_power10"])
            not in explicit_signatures
            for unit in remaining_explicit_units
        ):
            return []
    result = []
    for leaf in leaves:
        lane = leaf["column_ordinal"]
        if leaf["lane_kind"] == "PERCENT":
            result.append(
                {
                    "column_center": leaf["column_center"],
                    "column_ordinal": lane,
                    "currency": None,
                    "evidence_locations": [
                        {"page_sequence": header_page, "source_line_index": index}
                        for index in leaf["header_evidence_source_line_indices"]
                    ],
                    "magnitude_power10": None,
                    "projection_status": (
                        "LOCAL_ACTIVE_PARENT_FENCED_MULTILEVEL_PERCENT_LEAF_"
                        "PROJECTED_TO_BODY_COLUMN"
                    ),
                    "unit_kind": "PERCENT",
                }
            )
            continue
        explicit = accounting_unit_surface_v1(leaf["header_surface"])
        if not shared_money_available:
            if explicit is None:
                return []
            record = {
                "column_center": leaf["column_center"],
                "column_ordinal": lane,
                "currency": explicit["currency"],
                "evidence_locations": [
                    {"page_sequence": header_page, "source_line_index": index}
                    for index in leaf["header_evidence_source_line_indices"]
                ],
                "magnitude_power10": explicit["magnitude_power10"],
                "projection_status": "LOCAL_EXPLICIT_MULTILEVEL_MONEY_LEAF_UNIT",
                "unit_kind": explicit["unit_kind"],
            }
            record["projection_status"] += "_FOR_ACTIVE_PARENT_FENCED_MULTILEVEL_MONEY_LEAF"
            result.append(record)
            continue
        record = canonical_clone_v1(shared_money[lane])
        if explicit is not None:
            explicit_signature = (
                explicit["unit_kind"],
                explicit["currency"],
                explicit["magnitude_power10"],
            )
            shared_signature = (
                record["unit_kind"],
                record["currency"],
                record["magnitude_power10"],
            )
            if record["projection_status"].startswith("LOCAL_EXPLICIT_"):
                if explicit_signature != shared_signature:
                    return []
                record["evidence_locations"] = sorted(
                    {
                        (item["page_sequence"], item["source_line_index"]): item
                        for item in [
                            *record["evidence_locations"],
                            *(
                                {"page_sequence": header_page, "source_line_index": index}
                                for index in leaf["header_evidence_source_line_indices"]
                            ),
                        ]
                    }.values(),
                    key=lambda item: (item["page_sequence"], item["source_line_index"]),
                )
                record["projection_status"] += "_WITH_CONSISTENT_EXPLICIT_MONEY_LEAF"
            else:
                record = {
                    "column_center": leaf["column_center"],
                    "column_ordinal": lane,
                    "currency": explicit["currency"],
                    "evidence_locations": [
                        {"page_sequence": header_page, "source_line_index": index}
                        for index in leaf["header_evidence_source_line_indices"]
                    ],
                    "magnitude_power10": explicit["magnitude_power10"],
                    "projection_status": "LOCAL_EXPLICIT_MULTILEVEL_MONEY_LEAF_UNIT",
                    "unit_kind": explicit["unit_kind"],
                }
        record["projection_status"] += "_FOR_ACTIVE_PARENT_FENCED_MULTILEVEL_MONEY_LEAF"
        result.append(record)
    allowed_locations = {(header_page, line["source_line_index"]) for line in header_lines}
    if any(
        (location["page_sequence"], location["source_line_index"]) not in allowed_locations
        for record in result
        for location in record["evidence_locations"]
    ):
        return []
    return result


def _validate_v2_context(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != column_v1._RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or value["status"] != "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
        or value["unresolved_reasons"]
    ):
        raise _error("multilevel V2 compatible context contract drifted")
    pseudo_v1 = canonical_clone_v1(value)
    pseudo_v1["format_version"] = column_v1.FORMAT_VERSION
    pseudo_v1["claim_boundary"] = column_v1.CLAIM_BOUNDARY
    pseudo_v1["safety"] = canonical_clone_v1(column_v1._SAFETY)
    pseudo_material = canonical_clone_v1(pseudo_v1)
    pseudo_material.pop("column_context_id")
    pseudo_v1["column_context_id"] = "afccv1:context:" + canonical_json_sha256_v1(pseudo_material)
    column_v1._validate_result(pseudo_v1)
    material = canonical_clone_v1(value)
    identity = material.pop("column_context_id")
    if identity != "afccmlv2:context:" + canonical_json_sha256_v1(material):
        raise _error("multilevel V2 compatible context identity drifted")
    return canonical_clone_v1(value)


def _project_v2_context(
    baseline: Mapping[str, Any],
    leaves: Sequence[Mapping[str, Any]],
    period_mode: str,
    header_page: int,
    unit_axis: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    period_axis = [
        {
            "column_center": leaf["column_center"],
            "column_ordinal": leaf["column_ordinal"],
            "evidence_locations": [
                {"page_sequence": header_page, "source_line_index": index}
                for index in leaf["period_evidence_source_line_indices"]
            ],
            "projection_status": (
                period_mode + "_ACTIVE_PARENT_RESET_FENCED_MULTILEVEL_PERIOD_PARENT_"
                "PROPAGATED_TO_HEADER_LEAF"
            ),
            "resolved_period": leaf["resolved_period"],
        }
        for leaf in leaves
    ]
    material = {
        key: canonical_clone_v1(item)
        for key, item in baseline.items()
        if key != "column_context_id"
    }
    material.update(
        {
            "claim_boundary": CLAIM_BOUNDARY,
            "format_version": FORMAT_VERSION,
            "metrics": {
                "column_count": len(leaves),
                "period_column_count": len(period_axis),
                "unit_column_count": len(unit_axis),
            },
            "period_axis": period_axis,
            "safety": canonical_clone_v1(_SAFETY),
            "status": "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY",
            "unit_axis": canonical_clone_v1(unit_axis),
            "unresolved_reasons": [],
        }
    )
    return _validate_v2_context(
        {
            **material,
            "column_context_id": "afccmlv2:context:" + canonical_json_sha256_v1(material),
        }
    )


def build_accounting_family_column_context_multilevel_v2(
    row_axis: Any,
    pages: Any,
    family_topology_spec: Any,
    *,
    period_semantics: str,
    expected_lane_unit_kinds: Any,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Build sealed V1 first, then attempt one mixed balance-header fallback."""

    return _build_accounting_family_column_context_multilevel_v2(
        row_axis,
        pages,
        family_topology_spec,
        period_semantics=period_semantics,
        expected_lane_unit_kinds=expected_lane_unit_kinds,
        visible_dash_rescues=visible_dash_rescues,
        replay_row_axis=True,
    )


def _build_accounting_family_column_context_multilevel_from_authenticated_row_axis_v2(
    row_axis: Any,
    pages: Any,
    family_topology_spec: Any,
    *,
    period_semantics: str,
    expected_lane_unit_kinds: Any,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Build V2 from one already authenticated occurrence/row-axis handoff."""

    return _build_accounting_family_column_context_multilevel_v2(
        row_axis,
        pages,
        family_topology_spec,
        period_semantics=period_semantics,
        expected_lane_unit_kinds=expected_lane_unit_kinds,
        visible_dash_rescues=visible_dash_rescues,
        replay_row_axis=False,
    )


def _build_accounting_family_column_context_multilevel_v2(
    row_axis: Any,
    pages: Any,
    family_topology_spec: Any,
    *,
    period_semantics: str,
    expected_lane_unit_kinds: Any,
    visible_dash_rescues: Any,
    replay_row_axis: bool,
) -> dict[str, Any]:
    """Share one fallback implementation across public and trusted handoffs."""

    baseline_builder = (
        column_v1.build_accounting_family_column_context_v1
        if replay_row_axis
        else column_v1._build_accounting_family_column_context_from_authenticated_row_axis_v1
    )
    baseline = baseline_builder(
        row_axis,
        pages,
        family_topology_spec,
        period_semantics=period_semantics,
        expected_lane_unit_kinds=expected_lane_unit_kinds,
        visible_dash_rescues=visible_dash_rescues,
    )
    if (
        baseline["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
        or period_semantics != "BALANCE_COMPARATIVE"
        or type(expected_lane_unit_kinds) is not list
        or not expected_lane_unit_kinds
        or not set(expected_lane_unit_kinds) <= {"MONEY", "PERCENT"}
        or not baseline["unresolved_reasons"]
    ):
        return baseline
    _validate_pinned_implementation_refs()
    try:
        axis = row_axis_v1._validate_result(row_axis)
        parsed_pages = row_axis_v1._pages(pages)
    except row_axis_v1.AccountingFamilyRowAxisV1Error as exc:
        raise _error("multilevel V2 row-axis handoff drifted after V1 replay") from exc
    region = axis["topology_region"]
    if type(region) is not dict or region["continuation_page_count"] not in {0, 1}:
        return baseline
    centers = column_v1._lane_centers(axis)
    if centers is None or len(centers) != len(expected_lane_unit_kinds):
        return baseline
    header = _fenced_header_lines(axis, parsed_pages, family_topology_spec, centers)
    if header is None:
        return baseline
    header_lines, header_page = header
    parent = region["parent_match"]
    parent_page = parent["page_sequence"]
    contextual_next_page = parent_page != header_page
    value_rows = [row for row in axis["rows"] if row["values"]]
    first_body = min(
        (row["label_match"] for row in value_rows),
        key=lambda match: column_v1._visual_match_key(parsed_pages, match),
    )
    header_owner = _active_header_owner(region, parent, first_body)
    contextual_owner = (
        header_owner is not None
        and header_owner is not parent
        and _contextual_header_owner_covers_value_rows(
            header_owner,
            value_rows,
            header_page,
        )
    )
    if (not contextual_owner and set(expected_lane_unit_kinds) != {"MONEY", "PERCENT"}) or (
        contextual_owner and set(expected_lane_unit_kinds) not in ({"MONEY"}, {"MONEY", "PERCENT"})
    ):
        return baseline
    eligible_reasons = (
        _CONTEXTUAL_NEXT_PAGE_ELIGIBLE_V1_REASONS
        if contextual_next_page
        else (
            _CONTEXTUAL_SAME_PAGE_ELIGIBLE_V1_REASONS
            if contextual_owner
            else _FALLBACK_ELIGIBLE_V1_REASONS
        )
    )
    if not set(baseline["unresolved_reasons"]).issubset(eligible_reasons):
        return baseline
    page_width = next(
        page["page_width"] for page in parsed_pages if page["page_sequence"] == header_page
    )
    if type(page_width) is not int:
        return baseline
    try:
        projected = leaf_axis_v1.build_accounting_multilevel_header_leaf_axis_v1(
            header_lines,
            column_centers=centers,
            page_width=page_width,
            document_period_context=baseline["document_period_context"],
            period_semantics=period_semantics,
            expected_lane_kinds=expected_lane_unit_kinds,
        )
    except leaf_axis_v1.AccountingMultilevelHeaderLeafAxisV1Error:
        return baseline
    if projected["status"] != "MULTILEVEL_HEADER_LEAF_AXIS_BOUND_PROPOSAL_ONLY":
        return baseline
    unit_axis = _shared_unit_axis(
        header_lines,
        header_page,
        centers,
        expected_lane_unit_kinds,
        baseline["document_unit_context"],
        projected["leaf_axis"],
    )
    if (
        len(unit_axis) != len(centers)
        or [item["unit_kind"] for item in unit_axis] != expected_lane_unit_kinds
    ):
        return baseline
    return _project_v2_context(
        baseline,
        projected["leaf_axis"],
        projected["period_resolution_mode"],
        header_page,
        unit_axis,
    )


def _validate_context_receipt_v2(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise _error("multilevel column context must be one exact object")
    if value.get("format_version") == column_v1.FORMAT_VERSION:
        return column_v1._validate_result(value)
    if value.get("format_version") == FORMAT_VERSION:
        return _validate_v2_context(value)
    raise _error("multilevel column-context format version drifted")


def _validate_accounting_family_column_context_multilevel_from_authenticated_row_axis_v2(
    value: Any,
    row_axis: Any,
    pages: Any,
    family_topology_spec: Any,
    *,
    period_semantics: str,
    expected_lane_unit_kinds: Any,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Replay V1/V2 context without revalidating an authenticated row-axis handoff."""

    persisted = _validate_context_receipt_v2(value)
    expected = _build_accounting_family_column_context_multilevel_from_authenticated_row_axis_v2(
        row_axis,
        pages,
        family_topology_spec,
        period_semantics=period_semantics,
        expected_lane_unit_kinds=expected_lane_unit_kinds,
        visible_dash_rescues=visible_dash_rescues,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("multilevel authenticated column context does not replay exactly")
    return persisted


def validate_accounting_family_column_context_multilevel_replay_v2(
    value: Any,
    row_axis: Any,
    pages: Any,
    family_topology_spec: Any,
    *,
    period_semantics: str,
    expected_lane_unit_kinds: Any,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Reject V1 or projected-V2 mutation through complete reconstruction."""

    persisted = _validate_context_receipt_v2(value)
    expected = build_accounting_family_column_context_multilevel_v2(
        row_axis,
        pages,
        family_topology_spec,
        period_semantics=period_semantics,
        expected_lane_unit_kinds=expected_lane_unit_kinds,
        visible_dash_rescues=visible_dash_rescues,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("multilevel column context does not replay exactly")
    return persisted
