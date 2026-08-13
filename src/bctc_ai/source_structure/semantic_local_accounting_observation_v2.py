"""Assemble source-bound semantic accounting observation candidates.

VietOCR Transformer is the only text source for owner, branch, row and unit
identity.  The authenticated PP-OCR V3 projection contributes only date,
numeric and geometry evidence.  Accentless keys are a comparison layer: a
unique key is promoted only when one complete, independent local topology also
passes value-lane alignment and additive closure.

The result is deliberately a graph-v2 *readiness candidate*.  It neither
changes Local Accounting Graph v1 nor claims accounting/schema acceptance.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.contracts_v2 import validate_source_evidence_projection_v2
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    FamilySpecV1,
    local_accounting_family_spec_sha256_v1,
    parse_local_accounting_period_v1,
    parse_local_accounting_unit_v1,
)
from bctc_ai.source_structure.vietnamese_semantic_surface_v1 import (
    CompiledVietnameseFamilyAliasIndexV1,
    VietnameseAliasCandidateV1,
    compile_vietnamese_family_alias_index_v1,
    propose_vietnamese_semantic_surface_v1,
)
from bctc_ai.source_structure.vietocr_semantic_receipt_v2 import (
    validate_vietocr_semantic_page_binding_v2,
)

__all__ = [
    "CLAIM_BOUNDARY",
    "FORMAT_VERSION",
    "SAFETY",
    "SemanticLocalAccountingObservationV2Error",
    "build_semantic_local_accounting_observation_candidate_v2",
    "validate_semantic_local_accounting_observation_candidate_v2",
]


FORMAT_VERSION = "BANK_CORPUS_SEMANTIC_LOCAL_ACCOUNTING_OBSERVATION_CANDIDATE_V2"
CLAIM_BOUNDARY = (
    "REPLAY_AUTHENTICATED_TRANSFORMER_SEMANTIC_AND_PPOCR_NUMERIC_GEOMETRY_"
    "OBSERVATION_CANDIDATE_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE_ONLY_"
    "NO_FAMILY_REGISTRY_OR_PAGE_FAMILY_EXHAUSTIVENESS_NO_GRAPH_V1_ACCEPTANCE_"
    "NO_SCHEMA_AUTHORITY"
)
SAFETY: dict[str, bool] = {
    "reader_v3_mutated": False,
    "ppocr_transcript_used_for_semantic_identity": False,
    "ppocr_used_for_date_and_numeric_text_only": True,
    "vietocr_transformer_used_for_semantic_text": True,
    "vietocr_used_for_numeric_value": False,
    "accentless_key_retains_original_utf8_transcript": True,
    "accentless_key_alone_can_accept": False,
    "accentless_promotion_requires_collision_free_complete_topology": True,
    "supplied_family_collision_scope_only": True,
    "family_registry_exhaustiveness_claimed": False,
    "page_family_exhaustiveness_claimed": False,
    "fuzzy_edit_matching_used": False,
    "automatic_spelling_repair_used": False,
    "output_is_accepted_graph": False,
    "schema_mapping_authority": False,
}


class SemanticLocalAccountingObservationV2Error(ValueError):
    """The source/reader split or candidate replay contract was crossed."""


_PLAIN_INTEGER_RE = re.compile(r"[0-9]+")
_GROUPED_INTEGER_RE = re.compile(r"[0-9]{1,3}(?:[.,][0-9]{3})+")


def _error(message: str) -> SemanticLocalAccountingObservationV2Error:
    return SemanticLocalAccountingObservationV2Error(message)


def _center_x(bbox: Sequence[int]) -> float:
    return (bbox[0] + bbox[2]) / 2


def _center_y(bbox: Sequence[int]) -> float:
    return (bbox[1] + bbox[3]) / 2


def _overlaps(first: Sequence[int], second: Sequence[int], axis: int) -> bool:
    return min(first[axis + 2], second[axis + 2]) > max(first[axis], second[axis])


def _union_box(boxes: Sequence[Sequence[int]]) -> list[int]:
    if not boxes:
        raise _error("cannot union an empty geometry set")
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _nfc(value: str) -> str:
    if type(value) is not str:
        raise _error("Transformer transcript is not one string")
    result = unicodedata.normalize("NFC", value)
    try:
        result.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise _error("Transformer transcript is not valid UTF-8") from exc
    return result


def _parse_financial_integer(value: str) -> Decimal | None:
    if type(value) is not str:
        return None
    text = value.strip().replace("\u00a0", "").replace("\u202f", "").replace(" ", "")
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    if text.startswith(("+", "-")):
        negative = text[0] == "-"
        text = text[1:]
    if _PLAIN_INTEGER_RE.fullmatch(text) is not None:
        digits = text
    elif _GROUPED_INTEGER_RE.fullmatch(text) is not None:
        separators = {character for character in text if character in ".,"}
        if len(separators) != 1:
            return None
        digits = text.replace(next(iter(separators)), "")
    else:
        return None
    try:
        result = Decimal(digits)
    except InvalidOperation:
        return None
    return -result if negative else result


def _semantic_identities(
    candidates: Sequence[VietnameseAliasCandidateV1],
) -> set[tuple[str, str]]:
    # Repeated family membership for the same generic role is not a semantic
    # collision (for example CUSTOMER_LOANS owner in two family specs).
    return {(candidate.role_kind, candidate.role) for candidate in candidates}


def _target_direct_match(
    text: str,
    alias_index: CompiledVietnameseFamilyAliasIndexV1,
    family_id: str,
    role_kind: str,
    role: str,
) -> tuple[dict[str, Any] | None, bool]:
    proposal = propose_vietnamese_semantic_surface_v1(text, alias_index)
    target = [
        candidate
        for candidate in proposal.candidates
        if candidate.family_id == family_id
        and candidate.role_kind == role_kind
        and candidate.role == role
    ]
    if not target:
        return None, False
    identities = _semantic_identities(proposal.candidates)
    if len(identities) != 1:
        return None, True
    exact = all(candidate.match_kind == "EXACT_VIETNAMESE_SURFACE" for candidate in target)
    return (
        {
            "accentless_comparison_key": proposal.accentless_comparison_key,
            "match_kind": ("EXACT_VIETNAMESE_SURFACE" if exact else "ACCENTLESS_ALIAS"),
            "presentation_normalization": target[0].presentation_normalization,
        },
        False,
    )


def _target_branch_match(
    text: str,
    alias_index: CompiledVietnameseFamilyAliasIndexV1,
    family_id: str,
) -> tuple[dict[str, Any] | None, bool]:
    direct, collision = _target_direct_match(text, alias_index, family_id, "BRANCH", "BRANCH")
    if direct is not None or collision:
        return direct, collision
    full = propose_vietnamese_semantic_surface_v1(text, alias_index)
    tokens = full.accentless_comparison_key.split()
    target_matches: list[tuple[int, VietnameseAliasCandidateV1]] = []
    relevant_candidates: list[VietnameseAliasCandidateV1] = []
    for stop in range(1, len(tokens)):
        prefix = " ".join(tokens[:stop])
        proposal = propose_vietnamese_semantic_surface_v1(prefix, alias_index)
        branch_candidates = [
            candidate for candidate in proposal.candidates if candidate.role_kind == "BRANCH"
        ]
        if any(candidate.family_id == family_id for candidate in branch_candidates):
            relevant_candidates.extend(branch_candidates)
            target_matches.extend(
                (stop, candidate)
                for candidate in branch_candidates
                if candidate.family_id == family_id and candidate.role == "BRANCH"
            )
    if not target_matches:
        return None, False
    if len(_semantic_identities(relevant_candidates)) != 1:
        return None, True
    stop, _candidate = max(target_matches, key=lambda item: item[0])
    return (
        {
            "accentless_comparison_key": full.accentless_comparison_key,
            "matched_alias_prefix_key": " ".join(tokens[:stop]),
            "match_kind": "ACCENTLESS_PREFIX_ALIAS",
            "presentation_normalization": "BRANCH_TRAILING_MODIFIER",
        },
        False,
    )


def _bound_line(sample: Mapping[str, Any], role: str, match: Mapping[str, Any]) -> dict[str, Any]:
    atom = sample["source_atom"]
    result = {
        "role": role,
        "transformer_text_nfc": _nfc(sample["normalized_prediction"]),
        "accentless_comparison_key": match["accentless_comparison_key"],
        "match_kind": match["match_kind"],
        "presentation_normalization": match["presentation_normalization"],
        "promotion_status": "PENDING_COMPLETE_TOPOLOGY",
        "semantic_text_source": "VIETOCR_VGG_TRANSFORMER_0_3_13",
        "source_line_index": sample["source_line_index"],
        "source_atom_id": atom["source_atom_id"],
        "raw_pixel_bbox": list(sample["source_bbox_raw_pixels"]),
        "canonical_bbox_mpt": list(atom["canonical_bbox_mpt"]),
    }
    if "matched_alias_prefix_key" in match:
        result["matched_alias_prefix_key"] = match["matched_alias_prefix_key"]
    return result


def _ppocr_span(sample: Mapping[str, Any], raw_text: str, *, kind: str) -> dict[str, Any]:
    atom = sample["source_atom"]
    return {
        "raw_text": raw_text,
        "text_source": f"PPOCRV6_{kind}_ONLY",
        "source_line_index": sample["source_line_index"],
        "source_atom_id": atom["source_atom_id"],
        "raw_pixel_bbox": list(sample["source_bbox_raw_pixels"]),
        "canonical_bbox_mpt": list(atom["canonical_bbox_mpt"]),
    }


def _unit_span(sample: Mapping[str, Any], unit: Mapping[str, Any], key: str) -> dict[str, Any]:
    atom = sample["source_atom"]
    return {
        "transformer_text_nfc": _nfc(sample["normalized_prediction"]),
        "accentless_comparison_key": key,
        "semantic_text_source": "VIETOCR_VGG_TRANSFORMER_0_3_13",
        "unit": canonical_clone_v1(unit),
        "source_line_index": sample["source_line_index"],
        "source_atom_id": atom["source_atom_id"],
        "raw_pixel_bbox": list(sample["source_bbox_raw_pixels"]),
        "canonical_bbox_mpt": list(atom["canonical_bbox_mpt"]),
    }


def _aligned_to_lanes(samples: Sequence[Mapping[str, Any]], lanes: Sequence[float]) -> bool:
    if len(samples) != len(lanes):
        return False
    ordered = sorted(samples, key=lambda sample: _center_x(sample["source_bbox_raw_pixels"]))
    centers = [_center_x(sample["source_bbox_raw_pixels"]) for sample in ordered]
    if centers != sorted(centers) or len(set(centers)) != len(centers):
        return False
    return all(
        abs(center - lane) <= 0.25 * max(1.0, abs(lanes[-1] - lanes[0]))
        for center, lane in zip(centers, lanes, strict=True)
    )


def _row_values(
    label: Mapping[str, Any],
    numeric: Sequence[tuple[Mapping[str, Any], str, Decimal]],
    lanes: Sequence[float],
) -> list[tuple[Mapping[str, Any], str, Decimal]] | None:
    bbox = label["raw_pixel_bbox"]
    matches = [item for item in numeric if _overlaps(bbox, item[0]["source_bbox_raw_pixels"], 1)]
    if len(matches) != len(lanes) or not _aligned_to_lanes([item[0] for item in matches], lanes):
        return None
    return sorted(matches, key=lambda item: _center_x(item[0]["source_bbox_raw_pixels"]))


def _value_position(
    item: tuple[Mapping[str, Any], str, Decimal], axis_index: int
) -> dict[str, Any]:
    sample, raw_text, value = item
    result = _ppocr_span(sample, raw_text, kind="NUMERIC")
    result.update(
        {
            "axis_index": axis_index,
            "normalized_decimal": str(value),
            "state": "OBSERVED_ZERO" if value == 0 else "OBSERVED_VALUE",
        }
    )
    return result


def _candidate_payload(
    source: Mapping[str, Any],
    binding: Mapping[str, Any],
    spec: FamilySpecV1,
    alias_index: CompiledVietnameseFamilyAliasIndexV1,
) -> dict[str, Any]:
    samples = binding["samples"]
    lines = source.get("page_result", {}).get("lines")
    if type(samples) is not list or type(lines) is not list or len(samples) != len(lines):
        raise _error("page binding and PP-OCR LINE axes are not coextensive")
    for index, (sample, line) in enumerate(zip(samples, lines, strict=True)):
        if (
            type(sample) is not dict
            or sample.get("source_line_index") != index
            or type(line) is not dict
            or type(line.get("raw_text")) is not str
        ):
            raise _error("bound LINE axis or PP-OCR numeric/date source drifted")

    family_id = spec.family_id
    reasons: set[str] = set()
    collision = False
    owners: list[dict[str, Any]] = []
    branches: list[dict[str, Any]] = []
    row_matches: dict[str, list[dict[str, Any]]] = {
        item.role: [] for item in spec.ordered_children + spec.optional_children
    }
    for sample in samples:
        text = sample["normalized_prediction"]
        match, collided = _target_direct_match(text, alias_index, family_id, "OWNER", "OWNER")
        collision |= collided
        if match is not None:
            owners.append(_bound_line(sample, "OWNER", match))
        match, collided = _target_branch_match(text, alias_index, family_id)
        collision |= collided
        if match is not None:
            branches.append(_bound_line(sample, "BRANCH", match))
        for child in spec.ordered_children + spec.optional_children:
            match, collided = _target_direct_match(
                text,
                alias_index,
                family_id,
                "ORDERED_CHILD" if child in spec.ordered_children else "OPTIONAL_CHILD",
                child.role,
            )
            collision |= collided
            if match is not None:
                row_matches[child.role].append(_bound_line(sample, child.role, match))

    if collision:
        reasons.add("SEMANTIC_ALIAS_COLLISION")
    if len(owners) != 1:
        reasons.add("OWNER_NOT_RESOLVED_FROM_TRANSFORMER")
    if len(branches) != 1:
        reasons.add("BRANCH_NOT_RESOLVED_FROM_TRANSFORMER")
    required_roles = [item.role for item in spec.ordered_children]
    if any(len(row_matches[role]) != 1 for role in required_roles):
        reasons.add("ORDERED_CHILDREN_NOT_RESOLVED_FROM_TRANSFORMER")
    if any(row_matches[item.role] for item in spec.optional_children):
        reasons.add("OPTIONAL_CHILD_TOPOLOGY_NOT_IMPLEMENTED")
    if reasons:
        return _final_payload(source, binding, spec, alias_index, [], reasons)

    owner = owners[0]
    branch = branches[0]
    required_labels = [row_matches[role][0] for role in required_roles]
    owner_y = _center_y(owner["raw_pixel_bbox"])
    branch_y = _center_y(branch["raw_pixel_bbox"])
    row_y = [_center_y(label["raw_pixel_bbox"]) for label in required_labels]
    if not (owner_y < branch_y < row_y[0] and row_y == sorted(row_y)):
        reasons.add("OWNER_BRANCH_ORDERED_SIBLING_TOPOLOGY_NOT_RESOLVED")

    first_row_y = row_y[0]
    periods: list[tuple[Mapping[str, Any], str, str]] = []
    units: list[tuple[Mapping[str, Any], dict[str, Any], str]] = []
    numeric: list[tuple[Mapping[str, Any], str, Decimal]] = []
    for sample, line in zip(samples, lines, strict=True):
        ppocr_text = line["raw_text"]
        y = _center_y(sample["source_bbox_raw_pixels"])
        period = parse_local_accounting_period_v1(ppocr_text)
        if period is not None and branch_y < y < first_row_y:
            periods.append((sample, ppocr_text, period))
        value = _parse_financial_integer(ppocr_text)
        if value is not None and period is None:
            numeric.append((sample, ppocr_text, value))
        transformer_text = sample["normalized_prediction"]
        unit = parse_local_accounting_unit_v1(transformer_text)
        if unit is not None and branch_y < y < first_row_y:
            key = propose_vietnamese_semantic_surface_v1(
                transformer_text, alias_index
            ).accentless_comparison_key
            units.append((sample, unit, key))

    axis_count = spec.axis_layout.comparative_monetary_period_count
    periods.sort(key=lambda item: _center_x(item[0]["source_bbox_raw_pixels"]))
    if (
        len(periods) != axis_count
        or len({item[2] for item in periods}) != axis_count
        or axis_count != 2
    ):
        reasons.add("TWO_COMPARATIVE_PERIOD_AXES_NOT_RESOLVED")
        lanes: list[float] = []
    else:
        lanes = [_center_x(item[0]["source_bbox_raw_pixels"]) for item in periods]

    units.sort(key=lambda item: _center_x(item[0]["source_bbox_raw_pixels"]))
    if (
        len(units) != axis_count
        or len({canonical_json_sha256_v1(item[1]) for item in units}) != 1
        or not lanes
        or not _aligned_to_lanes([item[0] for item in units], lanes)
    ):
        reasons.add("PER_AXIS_UNIT_SCOPE_NOT_RESOLVED")

    built_rows: list[dict[str, Any]] = []
    row_value_items: dict[str, list[tuple[Mapping[str, Any], str, Decimal]]] = {}
    if lanes:
        for role, label in zip(required_roles, required_labels, strict=True):
            values = _row_values(label, numeric, lanes)
            if values is None:
                reasons.add("ROW_VALUE_AXIS_ASSIGNMENT_NOT_RESOLVED")
                continue
            row_value_items[role] = values
            built_rows.append(
                {
                    "role": role,
                    "label": label,
                    "value_positions": [
                        _value_position(item, axis_index) for axis_index, item in enumerate(values)
                    ],
                }
            )

    total_values: list[tuple[Mapping[str, Any], str, Decimal]] | None = None
    if len(built_rows) == len(required_roles):
        last_label = required_labels[-1]
        last_values = row_value_items[required_roles[-1]]
        previous_index = max(
            last_label["source_line_index"],
            *(item[0]["source_line_index"] for item in last_values),
        )
        by_index = {item[0]["source_line_index"]: item for item in numeric}
        following = [by_index.get(previous_index + offset) for offset in range(1, axis_count + 1)]
        if all(item is not None for item in following):
            narrowed = [item for item in following if item is not None]
            if _aligned_to_lanes([item[0] for item in narrowed], lanes) and all(
                _overlaps(
                    narrowed[0][0]["source_bbox_raw_pixels"],
                    item[0]["source_bbox_raw_pixels"],
                    1,
                )
                for item in narrowed[1:]
            ):
                total_values = sorted(
                    narrowed, key=lambda item: _center_x(item[0]["source_bbox_raw_pixels"])
                )
        if total_values is None:
            reasons.add("IMMEDIATE_UNLABELED_TOTAL_NOT_RESOLVED")

    arithmetic = {"status": "NOT_EVALUABLE", "evaluated_axis_indexes": []}
    if total_values is not None and all(role in row_value_items for role in required_roles):
        evaluated: list[int] = []
        mismatch: list[int] = []
        for axis_index in range(axis_count):
            expected = sum(
                (row_value_items[role][axis_index][2] for role in spec.closure_child_roles),
                Decimal(),
            )
            observed = total_values[axis_index][2]
            evaluated.append(axis_index)
            if expected != observed:
                mismatch.append(axis_index)
        arithmetic = {
            "status": "VETOED" if mismatch else "CORROBORATED",
            "evaluated_axis_indexes": evaluated,
        }
        if mismatch:
            reasons.add("ARITHMETIC_CLOSURE_VETO")

    if reasons:
        return _final_payload(source, binding, spec, alias_index, [], reasons)

    for label in (owner, branch, *required_labels):
        label["promotion_status"] = (
            "PROMOTED_BY_UNIQUE_COMPLETE_TOPOLOGY"
            if label["match_kind"].startswith("ACCENTLESS")
            else "EXACT_SURFACE_IN_COMPLETE_TOPOLOGY"
        )
    built_rows.append(
        {
            "role": "TOTAL",
            "label": None,
            "total_resolution": "IMMEDIATE_UNLABELED_NUMERIC_ROW",
            "value_positions": [
                _value_position(item, axis_index)
                for axis_index, item in enumerate(total_values or [])
            ],
        }
    )
    axes = []
    for axis_index, (sample, raw_text, period) in enumerate(periods):
        span = _ppocr_span(sample, raw_text, kind="DATE")
        span.update({"axis_index": axis_index, "period": period})
        axes.append(span)
    unit_labels = [_unit_span(sample, unit, key) for sample, unit, key in units]
    all_boxes = [
        owner["canonical_bbox_mpt"],
        branch["canonical_bbox_mpt"],
        *(axis["canonical_bbox_mpt"] for axis in axes),
        *(unit["canonical_bbox_mpt"] for unit in unit_labels),
        *(value["canonical_bbox_mpt"] for row in built_rows for value in row["value_positions"]),
        *(label["canonical_bbox_mpt"] for label in required_labels),
    ]
    region = {
        "canonical_bbox_mpt": _union_box(all_boxes),
        "owner_label": owner,
        "branch_label": branch,
        "axes": axes,
        "local_unit_labels": unit_labels,
        "rows": built_rows,
        "arithmetic": arithmetic,
        "topology": {
            "owner_resolution": True,
            "parent_child_edge": True,
            "ordered_sibling_set": True,
            "comparative_period_axis": True,
            "unit_scope_edge": True,
            "total_subtotal": True,
            "internal_additive_closure": True,
            "same_population_claimed": False,
            "row_frontier": True,
        },
    }
    return _final_payload(source, binding, spec, alias_index, [region], set())


def _final_payload(
    source: Mapping[str, Any],
    binding: Mapping[str, Any],
    spec: FamilySpecV1,
    alias_index: CompiledVietnameseFamilyAliasIndexV1,
    regions: list[dict[str, Any]],
    reasons: set[str],
) -> dict[str, Any]:
    complete_count = len(regions)
    ready = complete_count == 1 and not reasons
    accentless_promoted = ready and any(
        label is not None and label["match_kind"].startswith("ACCENTLESS")
        for region in regions
        for label in (
            region["owner_label"],
            region["branch_label"],
            *(row["label"] for row in region["rows"]),
        )
    )
    return {
        "format_version": FORMAT_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_local_page_id": source["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(source),
        "semantic_page_binding_sha256": canonical_json_sha256_v1(binding),
        "family_id": spec.family_id,
        "family_spec_sha256": local_accounting_family_spec_sha256_v1(spec),
        "supplied_family_collision_scope_spec_sha256_by_id": dict(
            alias_index.family_spec_sha256_by_id
        ),
        "status": "READY_FOR_GRAPH_V2" if ready else "UNRESOLVED",
        "candidate_regions": canonical_clone_v1(regions),
        "unresolved_reasons": sorted(reasons),
        "readiness": {
            "complete_topology_count": complete_count,
            "unique_complete_topology": ready,
            "accentless_candidates_promoted_by_topology": accentless_promoted,
            "ready_within_supplied_family_collision_scope": ready,
            "globally_collision_free_claimed": False,
            "graph_v1_accepted": False,
        },
        "safety": canonical_clone_v1(SAFETY),
    }


def build_semantic_local_accounting_observation_candidate_v2(
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: Sequence[FamilySpecV1],
) -> dict[str, Any]:
    """Build one replay-bound candidate without accepting a graph."""

    if type(family_spec) is not FamilySpecV1:
        raise _error("family spec must be one exact FamilySpecV1")
    if (
        isinstance(family_specs_for_collision_scope, (str, bytes, bytearray))
        or not isinstance(family_specs_for_collision_scope, Sequence)
        or not family_specs_for_collision_scope
        or any(type(spec) is not FamilySpecV1 for spec in family_specs_for_collision_scope)
    ):
        raise _error("collision scope must be a non-empty exact FamilySpecV1 sequence")
    try:
        semantic_alias_index = compile_vietnamese_family_alias_index_v1(
            family_specs_for_collision_scope
        )
    except (TypeError, ValueError) as exc:
        raise _error("collision-scope family specs failed semantic compilation") from exc
    digest = local_accounting_family_spec_sha256_v1(family_spec)
    if semantic_alias_index.family_spec_sha256_by_id.get(family_spec.family_id) != digest:
        raise _error("semantic alias index is not bound to the requested family spec")
    try:
        source = validate_source_evidence_projection_v2(source_projection_v2)
        binding = validate_vietocr_semantic_page_binding_v2(
            semantic_page_binding_v2,
            source_projection_v2,
            authenticated_transformer_receipt_v2,
        )
    except ValueError as exc:
        raise _error("source projection or Transformer page binding is not authenticated") from exc
    return _candidate_payload(source, binding, family_spec, semantic_alias_index)


def validate_semantic_local_accounting_observation_candidate_v2(
    value: Any,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: Sequence[FamilySpecV1],
) -> dict[str, Any]:
    """Replay one candidate from its authenticated source and reader inputs."""

    rebuilt = build_semantic_local_accounting_observation_candidate_v2(
        source_projection_v2,
        semantic_page_binding_v2,
        authenticated_transformer_receipt_v2,
        family_spec,
        family_specs_for_collision_scope,
    )
    if type(value) is not dict or not same_typed_json_v1(value, rebuilt):
        raise _error("semantic observation candidate does not replay exactly")
    return canonical_clone_v1(rebuilt)
