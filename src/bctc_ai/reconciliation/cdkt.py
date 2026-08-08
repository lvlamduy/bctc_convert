from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import cv2
import numpy as np

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.text import parse_financial_number, retrieval_key


class CDKTReconciliationError(ValueError):
    pass


_SHA256 = re.compile(r"[0-9a-f]{64}")
_POSITIVE_GROUPED_INTEGER = re.compile(r"(?:0|[1-9]\d*|[1-9]\d{0,2}(?:[.,]\d{3})+)")
_SELECTED_MAPPING_STATUSES = frozenset({"RESOLVED_ANCHOR", "RESOLVED_PATH"})
_SKIPPED_SCHEMA_STATUS = "UNMATCHED_SCHEMA_NODE_WITH_SKIPPED_CANDIDATES"


@dataclass(frozen=True, slots=True)
class HierarchicalAbsenceResolution:
    report_norm_id: int
    root_report_norm_id: int
    status: str
    candidate_row_ids: tuple[str, ...]
    mapped_sibling_report_norm_ids: tuple[int, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class TargetedNumericReread:
    raw_text: str
    crop_sha256: str
    reader_model_sha256: str
    reading_pass_id: str


@dataclass(frozen=True, slots=True)
class NumericDisagreementResolution:
    verification_status: str
    selected_raw_value: str | None
    normalized_numeric_value: str | None
    decision: str
    pixel_glyph_pattern: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VisibleScopeBinding:
    scope: str
    status: str
    evidence_keys: tuple[str, ...]
    reason: str


def _dict_index(
    records: Sequence[Mapping[str, Any]], key: str, *, name: str
) -> dict[Any, Mapping[str, Any]]:
    result: dict[Any, Mapping[str, Any]] = {}
    for record in records:
        value = record.get(key)
        if value is None or value in result:
            raise CDKTReconciliationError(f"{name} has a missing or duplicate {key}")
        result[value] = record
    return result


def _node_tokens(node: Mapping[str, Any]) -> frozenset[str]:
    display_name = node.get("display_name")
    if not isinstance(display_name, str) or not display_name:
        raise CDKTReconciliationError("schema node has no display name")
    return frozenset(retrieval_key(display_name).split())


def _subtype_tokens(node: Mapping[str, Any], parent: Mapping[str, Any]) -> frozenset[str]:
    return _node_tokens(node) - _node_tokens(parent)


def _row_semantic_keys(row: Mapping[str, Any]) -> tuple[frozenset[str], ...]:
    proposals = row.get("semantic_proposals")
    if not isinstance(proposals, Mapping) or not proposals:
        raise CDKTReconciliationError("source row has no semantic proposals")
    keys = []
    for value in proposals.values():
        if not isinstance(value, str):
            raise CDKTReconciliationError("source semantic proposal is not text")
        key = frozenset(retrieval_key(value).split())
        if key:
            keys.append(key)
    if not keys:
        raise CDKTReconciliationError("source row has no non-empty semantic proposal")
    return tuple(keys)


def _descendant_ids(root_id: int, nodes_by_id: Mapping[int, Mapping[str, Any]]) -> tuple[int, ...]:
    result: list[int] = []
    pending = [root_id]
    seen: set[int] = set()
    while pending:
        report_norm_id = pending.pop()
        if report_norm_id in seen:
            raise CDKTReconciliationError("schema hierarchy contains a cycle")
        seen.add(report_norm_id)
        result.append(report_norm_id)
        children = nodes_by_id[report_norm_id].get("child_report_norm_ids")
        if not isinstance(children, list) or any(type(value) is not int for value in children):
            raise CDKTReconciliationError("schema child identities are invalid")
        if any(value not in nodes_by_id for value in children):
            raise CDKTReconciliationError("schema child is absent from the projection")
        pending.extend(reversed(children))
    return tuple(result)


def resolve_closed_subtype_absences(
    *,
    schema_nodes: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    row_mappings: Sequence[Mapping[str, Any]],
    schema_dispositions: Sequence[Mapping[str, Any]],
    source_row_denominator_complete: bool,
) -> tuple[HierarchicalAbsenceResolution, ...]:
    """Resolve false subtype ambiguity only inside a closed visible child set.

    A skipped target is absent only when its mapped schema parent has a complete
    direct-source-child denominator, every direct child is already mapped to a
    different direct schema child, the skipped candidate set is exactly that
    visible denominator, and visible subtype tokens corroborate each selected
    sibling while excluding the target subtype. Descendants inherit absence.
    """

    if not source_row_denominator_complete:
        return ()
    nodes_by_id = _dict_index(schema_nodes, "report_norm_id", name="schema projection")
    rows_by_id = _dict_index(source_rows, "row_id", name="source rows")
    dispositions_by_id = _dict_index(
        schema_dispositions, "report_norm_id", name="schema dispositions"
    )
    if set(nodes_by_id) != set(dispositions_by_id):
        raise CDKTReconciliationError("schema projection/disposition denominator differs")

    selected_by_row: dict[str, int] = {}
    row_by_schema: dict[int, str] = {}
    for mapping in row_mappings:
        if mapping.get("status") not in _SELECTED_MAPPING_STATUSES:
            continue
        row_id = mapping.get("row_id")
        report_norm_id = mapping.get("selected_report_norm_id")
        if (
            not isinstance(row_id, str)
            or row_id not in rows_by_id
            or type(report_norm_id) is not int
            or report_norm_id not in nodes_by_id
            or row_id in selected_by_row
            or report_norm_id in row_by_schema
        ):
            raise CDKTReconciliationError("selected row/schema mapping is invalid or duplicate")
        selected_by_row[row_id] = report_norm_id
        row_by_schema[report_norm_id] = row_id

    roots: list[tuple[int, tuple[int, ...]]] = []
    for disposition in schema_dispositions:
        if disposition.get("status") != _SKIPPED_SCHEMA_STATUS:
            continue
        target_id = disposition.get("report_norm_id")
        candidate_rows_raw = disposition.get("candidate_row_ids")
        if type(target_id) is not int or not isinstance(candidate_rows_raw, list):
            raise CDKTReconciliationError("skipped schema disposition is malformed")
        if not candidate_rows_raw or any(
            not isinstance(value, str) for value in candidate_rows_raw
        ):
            continue
        target = nodes_by_id[target_id]
        parent_id = target.get("parent_report_norm_id")
        if type(parent_id) is not int or parent_id not in row_by_schema:
            continue
        parent_source_row_id = row_by_schema[parent_id]
        direct_source_rows = []
        for source_row in source_rows:
            structure = source_row.get("source_structure")
            if not isinstance(structure, Mapping):
                raise CDKTReconciliationError("source row structure is absent")
            if structure.get("physical_parent_row_id") == parent_source_row_id:
                direct_source_rows.append(str(source_row["row_id"]))
        if not direct_source_rows or set(candidate_rows_raw) != set(direct_source_rows):
            continue
        if any(row_id not in selected_by_row for row_id in direct_source_rows):
            continue

        parent = nodes_by_id[parent_id]
        schema_siblings_raw = parent.get("child_report_norm_ids")
        if not isinstance(schema_siblings_raw, list) or target_id not in schema_siblings_raw:
            raise CDKTReconciliationError("schema parent/child relation is inconsistent")
        sibling_ids = set(schema_siblings_raw)
        selected_siblings = tuple(selected_by_row[row_id] for row_id in direct_source_rows)
        if (
            target_id in selected_siblings
            or len(set(selected_siblings)) != len(selected_siblings)
            or any(report_norm_id not in sibling_ids for report_norm_id in selected_siblings)
        ):
            continue

        target_subtype = _subtype_tokens(target, parent)
        if not target_subtype:
            continue
        target_token_seen = False
        sibling_tokens_verified = True
        for row_id, selected_id in zip(direct_source_rows, selected_siblings, strict=True):
            semantic_keys = _row_semantic_keys(rows_by_id[row_id])
            selected_subtype = _subtype_tokens(nodes_by_id[selected_id], parent)
            if not selected_subtype or not any(
                selected_subtype <= proposal for proposal in semantic_keys
            ):
                sibling_tokens_verified = False
                break
            if any(target_subtype <= proposal for proposal in semantic_keys):
                target_token_seen = True
                break
        if not sibling_tokens_verified or target_token_seen:
            continue

        descendants = _descendant_ids(target_id, nodes_by_id)
        if any(
            report_norm_id in row_by_schema
            or dispositions_by_id[report_norm_id].get("status") == "MAPPED"
            for report_norm_id in descendants
        ):
            continue
        roots.append((target_id, tuple(sorted(set(selected_siblings)))))

    resolved: dict[int, HierarchicalAbsenceResolution] = {}
    for root_id, mapped_sibling_ids in roots:
        for report_norm_id in _descendant_ids(root_id, nodes_by_id):
            disposition = dispositions_by_id[report_norm_id]
            raw_candidates = disposition.get("candidate_row_ids", [])
            if not isinstance(raw_candidates, list) or any(
                not isinstance(value, str) for value in raw_candidates
            ):
                raise CDKTReconciliationError("schema candidate-row identities are invalid")
            resolved[report_norm_id] = HierarchicalAbsenceResolution(
                report_norm_id=report_norm_id,
                root_report_norm_id=root_id,
                status="NOT_OBSERVED_IN_THIS_PDF",
                candidate_row_ids=tuple(raw_candidates),
                mapped_sibling_report_norm_ids=mapped_sibling_ids,
                reason=(
                    "closed visible subtype family contains only decisively mapped siblings"
                    if report_norm_id == root_id
                    else f"schema ancestor {root_id} is not observed in the closed subtype family"
                ),
            )
    return tuple(
        sorted(
            resolved.values(),
            key=lambda item: int(nodes_by_id[item.report_norm_id]["display_order"]),
        )
    )


def _is_subsequence(candidate: str, source: str) -> bool:
    position = 0
    for character in source:
        if position < len(candidate) and candidate[position] == character:
            position += 1
    return position == len(candidate)


def _pixel_glyph_pattern(crop_bytes: bytes) -> tuple[str, ...]:
    image = cv2.imdecode(np.frombuffer(crop_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if image is None or image.ndim != 2 or min(image.shape) < 8:
        return ()
    _threshold, mask = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, 8)
    height, width = image.shape
    components: list[tuple[int, int, int, int, int]] = []
    for index in range(1, count):
        x, y, component_width, component_height, area = (int(value) for value in stats[index])
        touches_border = (
            x == 0 or y == 0 or x + component_width >= width or y + component_height >= height
        )
        is_table_rule = touches_border and (
            component_height >= 0.5 * height or component_width >= 0.8 * width
        )
        if area >= 4 and not is_table_rule:
            components.append((x, y, component_width, component_height, area))
    if not components:
        return ()
    max_height = max(component[3] for component in components)
    max_area = max(component[4] for component in components)
    meaningful = [component for component in components if component[4] >= 0.04 * max_area]
    digits = [
        component
        for component in meaningful
        if component[3] >= 0.65 * max_height and component[4] >= 0.25 * max_area
    ]
    if not digits:
        return ()
    digit_top = min(component[1] for component in digits)
    punctuation = [
        component
        for component in meaningful
        if component not in digits
        and 0.1 * max_height <= component[3] <= 0.4 * max_height
        and component[1] >= digit_top + 0.5 * max_height
    ]
    if len(digits) + len(punctuation) != len(meaningful):
        return ()
    classified = [(component[0], "DIGIT") for component in digits]
    classified.extend((component[0], "SEPARATOR") for component in punctuation)
    return tuple(kind for _x, kind in sorted(classified))


def _unresolved_numeric(
    reason: str, pattern: tuple[str, ...] = ()
) -> NumericDisagreementResolution:
    return NumericDisagreementResolution(
        verification_status="UNRESOLVED_READER_DISAGREEMENT",
        selected_raw_value=None,
        normalized_numeric_value=None,
        decision=reason,
        pixel_glyph_pattern=pattern,
    )


def resolve_invalid_numeric_challenger(
    numeric_evidence: Mapping[str, Any],
    *,
    crop_bytes: bytes,
    targeted_rereads: Sequence[TargetedNumericReread],
    primary_reading_pass_id: str,
) -> NumericDisagreementResolution:
    """Accept a primary grouped integer only after a crop reread and glyph audit.

    This deliberately does not resolve two valid, conflicting numeric values.
    It only handles an invalid challenger that is a character-deletion
    subsequence of a strict positive primary token. Reader scores are ignored.
    """

    crop_digest = numeric_evidence.get("crop_sha256")
    if (
        not isinstance(crop_digest, str)
        or _SHA256.fullmatch(crop_digest) is None
        or hashlib.sha256(crop_bytes).hexdigest() != crop_digest
    ):
        raise CDKTReconciliationError("numeric crop identity differs from sealed evidence")
    if numeric_evidence.get("verification_status") != "UNRESOLVED_READER_DISAGREEMENT":
        return _unresolved_numeric("numeric evidence is not an eligible reader disagreement")
    primary = numeric_evidence.get("primary")
    challenger = numeric_evidence.get("challenger")
    if not isinstance(primary, Mapping) or not isinstance(challenger, Mapping):
        raise CDKTReconciliationError("numeric reader evidence is malformed")
    primary_raw = primary.get("raw_text")
    challenger_raw = challenger.get("raw_text")
    if not isinstance(primary_raw, str) or not isinstance(challenger_raw, str):
        raise CDKTReconciliationError("numeric reader raw text is absent")
    compact_primary = primary_raw.replace(" ", "")
    compact_challenger = challenger_raw.replace(" ", "")
    if _POSITIVE_GROUPED_INTEGER.fullmatch(compact_primary) is None:
        return _unresolved_numeric("primary token is outside the narrow grouped-integer fallback")
    parsed_primary = parse_financial_number(compact_primary)
    parsed_challenger = parse_financial_number(compact_challenger)
    if (
        parsed_primary.observation not in {ObservationKind.VALUE, ObservationKind.ZERO}
        or parsed_primary.value is None
        or parsed_challenger.observation is not ObservationKind.INVALID
        or challenger.get("parsed_observation") != "INVALID"
        or challenger.get("parsed_value") is not None
        or not _is_subsequence(compact_challenger, compact_primary)
    ):
        return _unresolved_numeric("challenger is not a deletion-only invalid proposal")
    primary_value = primary.get("value")
    if not isinstance(primary_value, str) or Decimal(primary_value) != parsed_primary.value:
        raise CDKTReconciliationError("primary raw and normalized numeric evidence differs")
    if not targeted_rereads:
        return _unresolved_numeric("no exact-cell targeted reread is available")
    for reread in targeted_rereads:
        if (
            _SHA256.fullmatch(reread.crop_sha256) is None
            or reread.crop_sha256 != crop_digest
            or _SHA256.fullmatch(reread.reader_model_sha256) is None
            or not reread.reading_pass_id
            or reread.reading_pass_id == primary_reading_pass_id
            or reread.raw_text.replace(" ", "") != compact_primary
        ):
            return _unresolved_numeric("targeted reread identity or exact text does not agree")
    pixel_pattern = _pixel_glyph_pattern(crop_bytes)
    primary_pattern = tuple(
        "DIGIT" if character.isdigit() else "SEPARATOR" for character in compact_primary
    )
    if pixel_pattern != primary_pattern:
        return _unresolved_numeric(
            "pixel component order does not corroborate every primary glyph", pixel_pattern
        )
    challenger_pattern = tuple(
        "DIGIT" if character.isdigit() else "SEPARATOR" for character in compact_challenger
    )
    if pixel_pattern == challenger_pattern:
        return _unresolved_numeric("pixel components do not discriminate the two proposals")
    return NumericDisagreementResolution(
        verification_status="VERIFIED_OBSERVED_VALUE",
        selected_raw_value=primary_raw,
        normalized_numeric_value=format(parsed_primary.value, "f"),
        decision="ACCEPT_EXACT_TARGETED_REREAD_AND_PIXEL_GLYPH_ORDER",
        pixel_glyph_pattern=pixel_pattern,
    )


def bind_visible_report_scope(
    title_texts: Sequence[str], *, current_scope: str = "UNKNOWN"
) -> VisibleScopeBinding:
    """Bind consolidated/separate scope from title-region text only.

    The sole tolerated fuzzy consolidated form is PP-OCR's one-character
    deletion ``hp nhat`` under the full financial-position-statement title.
    Filenames, values, schema candidates, and history are not inputs.
    """

    if current_scope not in {"UNKNOWN", "CONSOLIDATED", "SEPARATE"}:
        raise CDKTReconciliationError("current report scope is invalid")
    evidence_keys = []
    scopes: set[str] = set()
    title_anchor = "bao cao tinh hinh tai chinh"
    for text in title_texts:
        if not isinstance(text, str):
            raise CDKTReconciliationError("visible title evidence must be text")
        key = retrieval_key(text)
        if not key or title_anchor not in key:
            continue
        consolidated = re.search(r"\b(?:hop|hp) nhat\b", key) is not None
        separate = re.search(r"\brieng(?: le)?\b", key) is not None
        if consolidated:
            scopes.add("CONSOLIDATED")
            evidence_keys.append(key)
        if separate:
            scopes.add("SEPARATE")
            evidence_keys.append(key)
    unique_evidence = tuple(dict.fromkeys(evidence_keys))
    if len(scopes) != 1:
        return VisibleScopeBinding(
            scope="UNKNOWN",
            status="UNRESOLVED_VISIBLE_TITLE_SCOPE",
            evidence_keys=unique_evidence,
            reason=(
                "visible title contains conflicting scope markers"
                if len(scopes) > 1
                else "visible title contains no admissible scope marker"
            ),
        )
    visible_scope = next(iter(scopes))
    if current_scope != "UNKNOWN" and current_scope != visible_scope:
        return VisibleScopeBinding(
            scope="UNKNOWN",
            status="CONFLICTING_EXISTING_AND_VISIBLE_SCOPE",
            evidence_keys=unique_evidence,
            reason="existing scope conflicts with the visible title",
        )
    return VisibleScopeBinding(
        scope=visible_scope,
        status="BOUND_FROM_VISIBLE_TITLE",
        evidence_keys=unique_evidence,
        reason="scope marker is visibly contained in the statement title region",
    )
