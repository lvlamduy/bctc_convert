"""Generic all-filing evidence sweep after family topology discovery.

One declarative family topology and one small evaluation policy are applied to
every authenticated filing.  Complete-document VietOCR text is scanned before
provenance is exposed.  Numeric proposals and page renders are opened only for
documents with one unique complete topology region.  No trial is mapped here;
the strongest output is a replayable schema-review readiness proposal.
"""

from __future__ import annotations

from typing import Any

from bctc_ai.evaluation import accounting_additive_table_closure_v1 as additive_v1
from bctc_ai.evaluation import accounting_family_column_context_v1 as column_context_v1
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_axis_v1
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import accounting_hierarchical_table_closure_v1 as hierarchical_v1
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


def _evaluation_spec(
    value: Any,
    family_spec: dict[str, Any],
    *,
    raw_family_spec: Any = None,
) -> dict[str, Any]:
    is_v2 = type(value) is dict and value.get("format_version") == EVALUATION_SPEC_FORMAT_V2
    is_v3 = type(value) is dict and value.get("format_version") == EVALUATION_SPEC_FORMAT_V3
    if (
        type(value) is not dict
        or set(value) != (_SPEC_FIELDS_V3 if is_v3 else _SPEC_FIELDS_V2 if is_v2 else _SPEC_FIELDS)
        or value["format_version"]
        not in {
            EVALUATION_SPEC_FORMAT,
            EVALUATION_SPEC_FORMAT_V2,
            EVALUATION_SPEC_FORMAT_V3,
        }
        or value["family_id"] != family_spec["family_id"]
        or value["period_semantics"] not in {"BALANCE_COMPARATIVE", "CURRENT_ROLLFORWARD"}
        or value["closure_policy"]
        not in {
            "CORROBORATE_IF_VISIBLE",
            "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE",
            "REQUIRE_EXACT_UNIQUE_VISIBLE_TRAILING_TOTAL",
        }
        or type(value["expected_lane_unit_kinds"]) is not list
        or not value["expected_lane_unit_kinds"]
        or any(item not in {"MONEY", "PERCENT"} for item in value["expected_lane_unit_kinds"])
    ):
        raise _error("family evaluation specification drifted")
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
    rescues = []
    for row in row_axis["rows"]:
        if not row["missing_column_ordinals"]:
            continue
        match = row["label_match"]
        page_sequence = match["page_sequence"]
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
    if policy["closure_policy"] == "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE":
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
    *, role: str | None, sample_id: str, closure: dict[str, Any]
) -> bool:
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
            and (peer_role is not None or value["sample_id"] in exact_total_samples)
            and value["parsed_token"]["classification"] in {"DASH_ZERO", "SIGNED_NUMBER"}
        ]
        if len(peers) < 2 or any(
            peer["scale"] != 0 or peer["percentage_mark_present"] is not False for peer in peers
        ):
            reasons.append(reason_prefix + ":SCALE_ZERO_LANE_PEERS_NOT_ESTABLISHED:" + sample_id)
        if not _mixed_candidate_has_accounting_corroboration(
            role=role,
            sample_id=sample_id,
            closure=closure,
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


def _select_candidate_evidence(
    candidate_evidence: list[dict[str, Any]], evaluation_spec: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    ready = [candidate for candidate in candidate_evidence if not candidate["reasons"]]
    if (
        len(ready) > 1
        and evaluation_spec["closure_policy"] == "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE"
    ):
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


def _candidate_evidence_from_joined_pages(
    *,
    joined_pages: list[dict[str, Any]],
    topology_scan: dict[str, Any],
    family_spec: dict[str, Any],
    evaluation_spec: dict[str, Any],
    render_snapshots: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    candidate_evidence = []
    for candidate_ordinal, topology_region in enumerate(topology_scan["regions"]):
        try:
            base_row_axis = (
                row_axis_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
                    joined_pages,
                    family_spec,
                    topology_scan,
                    topology_region,
                )
            )
            dash_rescues = _visible_dash_rescue_inputs(
                joined_pages=joined_pages,
                row_axis=base_row_axis,
                render_snapshots=render_snapshots,
            )
            row_axis = (
                row_axis_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
                    joined_pages,
                    family_spec,
                    topology_scan,
                    topology_region,
                    visible_dash_rescues=dash_rescues,
                )
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
            column_context = column_context_v1._build_accounting_family_column_context_from_authenticated_row_axis_v1(
                row_axis,
                joined_pages,
                family_spec,
                period_semantics=evaluation_spec["period_semantics"],
                expected_lane_unit_kinds=evaluation_spec["expected_lane_unit_kinds"],
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
                }
            )
            continue
        try:
            if evaluation_spec["closure_policy"] == "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE":
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
        candidate_evidence.append(
            {
                "additive_closure": closure,
                "candidate_ordinal": candidate_ordinal,
                "column_context": column_context,
                "reasons": list(dict.fromkeys(reasons)),
                "row_axis": row_axis,
            }
        )
    return candidate_evidence


def _trial(
    document: dict[str, Any],
    topology_scan: dict[str, Any],
    family_spec: dict[str, Any],
    evaluation_spec: dict[str, Any],
    *,
    numeric_document: dict[str, Any] | None,
    render_snapshots: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    base = {
        "document_ordinal": document["document_ordinal"],
        "private_provenance": canonical_clone_v1(document["private_provenance"]),
        "source_pdf_ref": canonical_clone_v1(document["source_pdf_ref"]),
        "topology_scan": topology_scan,
    }
    if topology_scan["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY":
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
    if topology_scan["status"] not in candidate_topology_statuses:
        return {
            **base,
            "additive_closure": None,
            "column_context": None,
            "document_axis_binding": None,
            "evidence_status": "UNRESOLVED_NO_UNIQUE_COMPLETE_TOPOLOGY",
            "row_axis": None,
            "unresolved_reasons": [topology_scan["status"]],
        }
    if numeric_document is None or not render_snapshots:
        raise _error("unique topology trial lacks its authenticated batch snapshots")
    document_axis = build_accounting_family_document_axis_join_v1(
        document,
        numeric_document,
        selected_page_render_snapshots=render_snapshots,
    )
    joined_pages = project_accounting_family_document_pages_v1(document_axis)
    candidate_evidence = _candidate_evidence_from_joined_pages(
        joined_pages=joined_pages,
        topology_scan=topology_scan,
        family_spec=family_spec,
        evaluation_spec=evaluation_spec,
        render_snapshots=render_snapshots,
    )
    selected, reasons = _select_candidate_evidence(candidate_evidence, evaluation_spec)
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
    if (
        type(baseline_trial) is not dict
        or set(baseline_trial) != _TRIAL_FIELDS
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
    expected_selected_pages: set[int] = set()
    for region in topology_scan["regions"]:
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
    candidate_evidence = _candidate_evidence_from_joined_pages(
        joined_pages=joined_pages,
        topology_scan=topology_scan,
        family_spec=family_spec,
        evaluation_spec=policy,
        render_snapshots=(),
    )
    selected, reasons = _select_candidate_evidence(candidate_evidence, policy)
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


def _missing_render_pages_for_document_store_trial_v1(
    trial: dict[str, Any],
    topology_scan: dict[str, Any],
    joined_pages: list[dict[str, Any]],
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

    row_axis = trial["row_axis"]
    if row_axis is not None:
        if row_axis["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY":
            return ()
        return tuple(
            sorted(
                {
                    row["label_match"]["page_sequence"]
                    for row in row_axis["rows"]
                    if row["missing_column_ordinals"]
                }
            )
        )
    if topology_scan["status"] == "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS" and any(
        "VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE" in reason for reason in trial["unresolved_reasons"]
    ):
        return tuple(sorted(_selected_topology_pages_v1(joined_pages, topology_scan)))
    return ()


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


def _trial_from_document_store_snapshot_v1(
    snapshot: dict[str, Any],
    family_spec: dict[str, Any],
    evaluation_spec: dict[str, Any],
    *,
    render_snapshots: tuple[dict[str, Any], ...] = (),
    topology_scan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet = snapshot["document_packet"]
    joined_pages = snapshot["joined_pages"]
    if topology_scan is None:
        topology_scan = topology_v1.build_accounting_family_topology_scan_v1(
            _topology_pages_from_document_snapshot_v1(joined_pages), family_spec
        )
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
    if topology_scan["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY":
        return {
            **base,
            "additive_closure": None,
            "column_context": None,
            "document_axis_binding": None,
            "evidence_status": "NOT_OBSERVED_PROPOSAL_ONLY",
            "row_axis": None,
            "unresolved_reasons": [],
        }
    if topology_scan["status"] not in {
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
            "unresolved_reasons": [topology_scan["status"]],
        }
    selected_pages = _selected_topology_pages_v1(joined_pages, topology_scan)
    if not selected_pages:
        raise _error("document-store topology selected no physical page")
    projected_pages = [
        {
            **canonical_clone_v1(page),
            "page_width": page["page_width"] if page["page_sequence"] in selected_pages else None,
        }
        for page in joined_pages
    ]
    candidates = _candidate_evidence_from_joined_pages(
        joined_pages=projected_pages,
        topology_scan=topology_scan,
        family_spec=family_spec,
        evaluation_spec=evaluation_spec,
        render_snapshots=render_snapshots,
    )
    selected, reasons = _select_candidate_evidence(candidates, evaluation_spec)
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
        "row_axis": selected["row_axis"] if selected is not None else None,
        "unresolved_reasons": reasons,
    }


def build_authenticated_family_first_accounting_evidence_sweep_from_document_store_v1(
    document_store_capability: document_store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    family_spec: Any,
    evaluation_spec: Any,
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
    topology_scans = document_store_v1.read_authenticated_family_first_topology_scans_v1(
        document_store_capability,
        family_spec,
    )
    if len(topology_scans) != document_count:
        raise _error("document-store topology denominator differs from its packet axis")
    trials = []
    for ordinal in range(1, document_count + 1):
        packet = document_store_v1.read_authenticated_family_first_document_packet_v1(
            document_store_capability, document_ordinal=ordinal
        )
        snapshot = document_store_v1.read_authenticated_family_first_document_evidence_snapshot_v1(
            document_store_capability,
            document_ordinal=ordinal,
            selected_pages=tuple(range(1, packet["page_count"] + 1)),
        )
        trial = _trial_from_document_store_snapshot_v1(
            snapshot,
            family_spec,
            policy,
            topology_scan=topology_scans[ordinal - 1],
        )
        missing_pages = _missing_render_pages_for_document_store_trial_v1(
            trial, topology_scans[ordinal - 1], snapshot["joined_pages"]
        )
        if missing_pages:
            renders = document_store_v1.read_authenticated_family_first_document_page_renders_v1(
                document_store_capability,
                document_ordinal=ordinal,
                physical_pages=missing_pages,
            )
            trial = _trial_from_document_store_snapshot_v1(
                snapshot,
                family_spec,
                policy,
                render_snapshots=renders,
                topology_scan=topology_scans[ordinal - 1],
            )
        trials.append(trial)
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
    for ordinal, trial in enumerate(value["trials"], 1):
        if (
            type(trial) is not dict
            or set(trial) != _TRIAL_FIELDS
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
        topology_scan = topology_v1.build_accounting_family_topology_scan_v1(
            _blind_pages(document), family_spec
        )
        prepared.append((document, topology_scan))

    accepted = [
        (document, topology_scan)
        for document, topology_scan in prepared
        if topology_scan["status"]
        in {
            "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
            "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
        }
    ]
    numeric_by_document = {}
    renders_by_document: dict[int, list[dict[str, Any]]] = {}
    if accepted:
        ordinals = tuple(document["document_ordinal"] for document, _scan in accepted)
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
                    for document, topology_scan in accepted
                    for region in topology_scan["regions"]
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
        )
        for document, topology_scan in prepared
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
