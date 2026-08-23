"""Family-12 region graph for loan analysis by enterprise legal form.

This wrapper is intentionally narrow.  It first locates a Family-12 heading,
then resolves the closest preceding context event inside a two-page budget.
Only an explicit RNID-716 owner opens a candidate region; deposit, related-
party, and structural-reset contexts close it.  Row text is matched accented
exact, accentless exact, and finally by the shared one-base-character matcher
only when every exact candidate missed.

The result is a structural proposal.  Adaptive geometry v2 and the generic
scoped-table graph are retained as replay receipts, but no number is parsed and
no text or geometry proposal grants schema-mapping authority.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any

from bctc_ai.evaluation.accounting_scoped_table_graph_v1 import (
    SPEC_FORMAT_VERSION as SCOPED_SPEC_FORMAT_VERSION,
)
from bctc_ai.evaluation.accounting_scoped_table_graph_v1 import (
    AccountingScopedTableGraphV1Error,
    build_accounting_scoped_table_graph_v1,
)
from bctc_ai.evaluation.accounting_table_axes_v1 import is_accounting_value_surface_v1
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    match_vietnamese_anchor_alias_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v2 import (
    resolve_accounting_table_geometry_v2,
)
from bctc_ai.evaluation.loan_enterprise_family12_spec_v1 import (
    FAMILY_ID,
    PARENT_REPORT_NORM_ID,
    REPORT_NORM_ID,
    build_loan_enterprise_family12_spec_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "LoanEnterpriseFamily12GraphV1Error",
    "build_loan_enterprise_family12_graph_v1",
    "validate_loan_enterprise_family12_graph_replay_v1",
]


FORMAT_VERSION = "LOAN_ENTERPRISE_FAMILY12_GRAPH_V1"
CLAIM_BOUNDARY = (
    "RNID766_INSIDE_EXPLICIT_RNID716_BOUNDED_REGION_TEXT_AND_GEOMETRY_GRAPH_"
    "PROPOSAL_ONLY_NO_NUMERIC_SCHEMA_MAPPING_GEMMA_ROUTING_OR_EXPORT_AUTHORITY"
)
_TIER_ORDER = {
    "EXACT_ACCENTED_ALIAS": 0,
    "EXACT_ACCENTLESS_ALIAS": 1,
    "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES": 2,
}
_FOREIGN_COMPONENT = re.compile(r"\bchi nhanh\b.*\b(?:ngan hang con|cong ty con)\b.*\bnuoc ngoai\b")
_ENUMERATION_PREFIX = re.compile(
    r"^\s*(?:(?:\d+(?:\.\d+)*|[a-z]|[ivxlcdm]+)[.)])\s*", re.IGNORECASE
)


class LoanEnterpriseFamily12GraphV1Error(ValueError):
    """Family-12 input, graph identity, or exact replay drifted."""


def _error(message: str) -> LoanEnterpriseFamily12GraphV1Error:
    return LoanEnterpriseFamily12GraphV1Error(message)


def _nfc(value: Any, label: str, *, nonempty: bool = True) -> str:
    if type(value) is not str or (nonempty and not value.strip()):
        raise _error(f"{label} must be one {'nonempty ' if nonempty else ''}exact string")
    if value != unicodedata.normalize("NFC", value):
        raise _error(f"{label} must already be NFC-normalized")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be one nonnegative exact integer")
    return value


def _bbox(value: Any, *, width: int, height: int) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
        or value[2] > width
        or value[3] > height
    ):
        raise _error("Family-12 line bbox drifted")
    return list(value)


def _visual(lines: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(line) for line in lines),
        key=lambda line: (
            line["bbox"][1],
            line["bbox"][0],
            line["bbox"][3],
            line["bbox"][2],
            line["source_line_index"],
        ),
    )


def _pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise _error("Family-12 graph requires one exact region-page sequence")
    pages: list[dict[str, Any]] = []
    seen_pages: set[int] = set()
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_height",
            "page_sequence",
            "page_width",
        }:
            raise _error("Family-12 page fields drifted")
        page_sequence = _positive_int(raw_page["page_sequence"], "page sequence")
        width = _positive_int(raw_page["page_width"], "page width")
        height = _positive_int(raw_page["page_height"], "page height")
        if page_sequence in seen_pages:
            raise _error("Family-12 page sequence repeats")
        if type(raw_page["lines"]) is not list or not raw_page["lines"]:
            raise _error("Family-12 page needs a nonempty line axis")
        seen_pages.add(page_sequence)
        lines = []
        seen_indices: set[int] = set()
        for raw_line in raw_page["lines"]:
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("Family-12 line fields drifted")
            source_index = _nonnegative_int(raw_line["source_line_index"], "source line index")
            if source_index in seen_indices:
                raise _error("Family-12 source line index repeats on one page")
            seen_indices.add(source_index)
            source_text = raw_line["source_text"]
            if source_text is not None:
                source_text = _nfc(source_text, "source text", nonempty=False)
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"], width=width, height=height),
                    "source_line_index": source_index,
                    "source_text": source_text,
                    "vietocr_text": _nfc(raw_line["vietocr_text"], "VietOCR text", nonempty=False),
                }
            )
        pages.append(
            {
                "lines": _visual(lines),
                "page_height": height,
                "page_sequence": page_sequence,
                "page_width": width,
            }
        )
    return sorted(pages, key=lambda page: page["page_sequence"])


@lru_cache(maxsize=4_096)
def _accented(value: str) -> str:
    value = _ENUMERATION_PREFIX.sub("", value)
    value = unicodedata.normalize("NFC", value.casefold())
    normalized = " ".join(re.sub(r"[^0-9a-zà-ỹđ%]+", " ", value).split())
    return re.sub(r"^(?:[0-9]+\s+)+", "", normalized)


@lru_cache(maxsize=4_096)
def _accentless(value: str) -> str:
    value = _ENUMERATION_PREFIX.sub("", value)
    normalized = normalize_vietnamese_anchor_v1(value)
    return re.sub(r"^(?:[0-9]+\s+)+", "", normalized)


def _joined(lines: Sequence[Mapping[str, Any]]) -> str:
    return " ".join(line["vietocr_text"].strip() for line in lines).strip()


def _line_evidence(line: Mapping[str, Any], *, page_sequence: int) -> dict[str, Any]:
    return {
        "bbox": canonical_clone_v1(line["bbox"]),
        "page_sequence": page_sequence,
        "source_line_index": line["source_line_index"],
        "source_text": line["source_text"],
        "vietocr_accentless_surface": _accentless(line["vietocr_text"]),
        "vietocr_raw_nfc_surface": line["vietocr_text"],
    }


def _exact_matches(surface: str, aliases: Sequence[str]) -> tuple[str | None, list[str]]:
    accented = _accented(surface)
    matches = [alias for alias in aliases if accented == _accented(alias)]
    if matches:
        return "EXACT_ACCENTED_ALIAS", matches
    accentless = _accentless(surface)
    matches = [alias for alias in aliases if accentless == _accentless(alias)]
    if matches:
        return "EXACT_ACCENTLESS_ALIAS", matches
    return None, []


def _bounded_matches(surface: str, aliases: Sequence[str]) -> tuple[list[str], int]:
    normalized_surface = _accentless(surface)
    matches = []
    comparisons = 0
    for alias in aliases:
        if abs(len(normalized_surface) - len(_accentless(alias))) > 1:
            continue
        comparisons += 1
        kind = match_vietnamese_anchor_alias_v1(surface, [alias])
        if kind == "ONE_EDIT_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY":
            matches.append(alias)
    return matches, comparisons


def _best_alias_match(
    surfaces: Sequence[str], aliases: Sequence[str], *, allow_bounded: bool
) -> tuple[str | None, str | None, list[str], int]:
    exact = []
    for span, surface in enumerate(surfaces, start=1):
        tier, matches = _exact_matches(surface, aliases)
        if tier is not None:
            exact.append((tier, -span, surface, matches))
    if exact:
        tier, negative_span, surface, matches = min(
            exact, key=lambda item: (_TIER_ORDER[item[0]], item[1], item[2])
        )
        return tier, surface, matches, 0
    if not allow_bounded:
        return None, None, [], 0
    approximate_comparisons = 0
    bounded = []
    for span, surface in enumerate(surfaces, start=1):
        matches, comparisons = _bounded_matches(surface, aliases)
        approximate_comparisons += comparisons
        if matches:
            bounded.append((-span, surface, matches))
    if not bounded:
        return None, None, [], approximate_comparisons
    _, surface, matches = min(bounded, key=lambda item: (item[0], item[1]))
    return (
        "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
        surface,
        matches,
        approximate_comparisons,
    )


def _branch_candidates(
    pages: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], int]:
    candidates = []
    approximate_comparisons = 0
    maximum_span = spec["limits"]["branch_line_span"]
    for page_ordinal, page in enumerate(pages):
        lines = page["lines"]
        for start in range(len(lines)):
            surfaces = [
                _joined(lines[start : start + span])
                for span in range(1, maximum_span + 1)
                if start + span <= len(lines)
            ]
            tier, surface, aliases, comparisons = _best_alias_match(
                surfaces, spec["branch_aliases"], allow_bounded=True
            )
            approximate_comparisons += comparisons
            if tier is None or surface is None:
                continue
            span = next(
                value for value in range(len(surfaces), 0, -1) if surfaces[value - 1] == surface
            )
            material = {
                "evidence": [
                    _line_evidence(line, page_sequence=page["page_sequence"])
                    for line in lines[start : start + span]
                ],
                "matched_aliases": sorted(aliases),
                "match_tier": tier,
                "page_sequence": page["page_sequence"],
                "surface": surface,
            }
            candidates.append(
                {
                    **material,
                    "branch_id": "lef12v1:branch:" + canonical_json_sha256_v1(material),
                    "page_ordinal": page_ordinal,
                    "start": start,
                    "stop": start + span,
                }
            )
    selected = []
    occupied: dict[int, set[int]] = {}
    for item in sorted(
        candidates,
        key=lambda candidate: (
            candidate["page_ordinal"],
            candidate["start"],
            _TIER_ORDER[candidate["match_tier"]],
            candidate["start"] - candidate["stop"],
            candidate["branch_id"],
        ),
    ):
        covered = set(range(item["start"], item["stop"]))
        if covered & occupied.setdefault(item["page_ordinal"], set()):
            continue
        occupied[item["page_ordinal"]].update(covered)
        selected.append(item)
    return selected, approximate_comparisons


def _context_class(
    surface: str, spec: Mapping[str, Any], *, allow_bounded: bool
) -> tuple[dict[str, Any] | None, int]:
    exact = []
    for record in spec["context_classes"]:
        tier, aliases = _exact_matches(surface, record["aliases"])
        if tier is not None:
            exact.append((tier, record, aliases))
    if exact:
        best_tier = min(_TIER_ORDER[item[0]] for item in exact)
        winners = [item for item in exact if _TIER_ORDER[item[0]] == best_tier]
        dispositions = {item[1]["disposition"] for item in winners}
        if len(winners) != 1 or len(dispositions) != 1:
            return {
                "context_id": "AMBIGUOUS_CONTEXT_EVENT",
                "disposition": "HARD_VETO",
                "match_tier": winners[0][0],
                "matched_aliases": sorted({alias for item in winners for alias in item[2]}),
                "report_norm_ids": sorted(
                    {rnid for item in winners for rnid in item[1]["report_norm_ids"]}
                ),
            }, 0
        tier, record, aliases = winners[0]
        return {**canonical_clone_v1(record), "match_tier": tier, "matched_aliases": aliases}, 0
    reset_tier, reset_aliases = _exact_matches(surface, spec["structural_reset_aliases"])
    if reset_tier is not None:
        return {
            "context_id": "STRUCTURAL_RESET",
            "disposition": "HARD_VETO",
            "match_tier": reset_tier,
            "matched_aliases": reset_aliases,
            "report_norm_ids": [],
        }, 0
    if not allow_bounded:
        return None, 0
    comparisons = 0
    bounded = []
    for record in spec["context_classes"]:
        aliases, count = _bounded_matches(surface, record["aliases"])
        comparisons += count
        if aliases:
            bounded.append((record, aliases))
    reset_aliases, count = _bounded_matches(surface, spec["structural_reset_aliases"])
    comparisons += count
    if reset_aliases:
        bounded.append(
            (
                {
                    "context_id": "STRUCTURAL_RESET",
                    "disposition": "HARD_VETO",
                    "report_norm_ids": [],
                },
                reset_aliases,
            )
        )
    if len(bounded) != 1:
        if bounded:
            return {
                "context_id": "AMBIGUOUS_CONTEXT_EVENT",
                "disposition": "HARD_VETO",
                "match_tier": "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
                "matched_aliases": sorted({alias for _, aliases in bounded for alias in aliases}),
                "report_norm_ids": sorted(
                    {rnid for record, _ in bounded for rnid in record["report_norm_ids"]}
                ),
            }, comparisons
        return None, comparisons
    record, aliases = bounded[0]
    return {
        **canonical_clone_v1(record),
        "match_tier": "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
        "matched_aliases": aliases,
    }, comparisons


def _owner_context(
    branch: Mapping[str, Any], pages: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> tuple[dict[str, Any], int]:
    page_ordinal = branch["page_ordinal"]
    branch_page_sequence = branch["page_sequence"]
    first_page = max(0, page_ordinal - spec["limits"]["context_page_budget"])
    events = []
    comparisons = 0
    for candidate_page_ordinal in range(first_page, page_ordinal + 1):
        page = pages[candidate_page_ordinal]
        page_distance = branch_page_sequence - page["page_sequence"]
        if not 0 <= page_distance <= spec["limits"]["context_page_budget"]:
            continue
        stop = branch["start"] if candidate_page_ordinal == page_ordinal else len(page["lines"])
        for line_ordinal, line in enumerate(page["lines"][:stop]):
            event, count = _context_class(line["vietocr_text"], spec, allow_bounded=True)
            comparisons += count
            if event is None:
                continue
            events.append(
                {
                    **event,
                    "evidence": _line_evidence(line, page_sequence=page["page_sequence"]),
                    "line_ordinal": line_ordinal,
                    "page_distance": page_distance,
                    "page_ordinal": candidate_page_ordinal,
                }
            )
    if not events:
        return {
            "disposition": "OWNER_REQUIRED_FAIL_CLOSED",
            "reason": "EXPLICIT_OWNER_716_NOT_FOUND_WITHIN_TWO_PRECEDING_PAGES",
        }, comparisons
    closest = max(events, key=lambda item: (item["page_ordinal"], item["line_ordinal"]))
    if closest["disposition"] != "REQUIRED_OWNER" or closest["context_id"] != "OWNER_716":
        return {
            "closest_context_event": closest,
            "disposition": "OWNER_REQUIRED_FAIL_CLOSED",
            "reason": "CLOSEST_CONTEXT_IS_HARD_VETO_OR_STRUCTURAL_RESET",
        }, comparisons
    observed_page_sequences = {page["page_sequence"] for page in pages}
    owner_page_sequence = closest["evidence"]["page_sequence"]
    if any(
        sequence not in observed_page_sequences
        for sequence in range(owner_page_sequence + 1, branch_page_sequence)
    ):
        return {
            "closest_context_event": closest,
            "disposition": "OWNER_REQUIRED_FAIL_CLOSED",
            "reason": "OWNER_CARRY_HAS_UNOBSERVED_INTERVENING_PAGE",
        }, comparisons
    return {
        "context_id": "OWNER_716",
        "disposition": "EXPLICIT_OWNER_CONTEXT_ACCEPTED_FOR_PROPOSAL",
        "evidence": closest["evidence"],
        "match_tier": closest["match_tier"],
        "mode": (
            "SAME_PAGE"
            if closest["page_distance"] == 0
            else f"CARRIED_FROM_PREVIOUS_PAGE_{closest['page_distance']}"
        ),
        "page_distance": closest["page_distance"],
        "report_norm_id": PARENT_REPORT_NORM_ID,
    }, comparisons


def _is_boundary(surface: str, spec: Mapping[str, Any]) -> tuple[bool, int]:
    event, comparisons = _context_class(surface, spec, allow_bounded=True)
    if event is not None:
        return True, comparisons
    tier, _, _, branch_comparisons = _best_alias_match(
        [surface], spec["branch_aliases"], allow_bounded=True
    )
    return tier is not None, comparisons + branch_comparisons


def _row_match(
    surfaces: Sequence[str], spec: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, int]:
    exact_candidates = []
    for child in spec["children"]:
        for surface in surfaces:
            tier, aliases = _exact_matches(surface, child["aliases"])
            if tier is not None:
                exact_candidates.append((tier, surface, child, aliases))
    exact_ambiguities = []
    for ambiguity in spec["source_only_ambiguities"]:
        for surface in surfaces:
            tier, aliases = _exact_matches(surface, ambiguity["aliases"])
            if tier is not None:
                exact_ambiguities.append((tier, surface, ambiguity, aliases))
    if exact_candidates or exact_ambiguities:
        best_tier = min(_TIER_ORDER[item[0]] for item in [*exact_candidates, *exact_ambiguities])
        candidates = [item for item in exact_candidates if _TIER_ORDER[item[0]] == best_tier]
        ambiguities = [item for item in exact_ambiguities if _TIER_ORDER[item[0]] == best_tier]
        if ambiguities or len({item[2]["report_norm_id"] for item in candidates}) != 1:
            candidate_ids = {item[2]["report_norm_id"] for item in candidates}
            candidate_ids.update(
                rnid for item in ambiguities for rnid in item[2]["candidate_report_norm_ids"]
            )
            return {
                "candidate_report_norm_ids": sorted(candidate_ids),
                "matched_aliases": sorted(
                    {alias for item in [*candidates, *ambiguities] for alias in item[3]}
                ),
                "match_tier": [*candidates, *ambiguities][0][0],
                "reason": (
                    ambiguities[0][2]["reason"]
                    if len(ambiguities) == 1
                    else "MULTIPLE_EXACT_SCHEMA_ROW_CANDIDATES"
                ),
                "report_norm_id": None,
                "surface": [*candidates, *ambiguities][0][1],
            }, 0
        tier, surface, child, aliases = candidates[0]
        return {
            "binding_class": child["binding_class"],
            "candidate_report_norm_ids": [child["report_norm_id"]],
            "matched_aliases": aliases,
            "match_tier": tier,
            "reason": "UNIQUE_EXACT_SCHEMA_ROW_CANDIDATE",
            "report_norm_id": child["report_norm_id"],
            "surface": surface,
        }, 0

    comparisons = 0
    bounded_candidates = []
    for child in spec["children"]:
        if not child["bounded_edit_on_exact_miss"]:
            continue
        for surface in surfaces:
            aliases, count = _bounded_matches(surface, child["aliases"])
            comparisons += count
            if aliases:
                bounded_candidates.append((surface, child, aliases))
    bounded_ambiguities = []
    for ambiguity in spec["source_only_ambiguities"]:
        for surface in surfaces:
            aliases, count = _bounded_matches(surface, ambiguity["aliases"])
            comparisons += count
            if aliases:
                bounded_ambiguities.append((surface, ambiguity, aliases))
    candidate_ids = {item[1]["report_norm_id"] for item in bounded_candidates}
    candidate_ids.update(
        rnid for item in bounded_ambiguities for rnid in item[1]["candidate_report_norm_ids"]
    )
    if not candidate_ids:
        return None, comparisons
    if len(candidate_ids) != 1 or bounded_ambiguities:
        return {
            "candidate_report_norm_ids": sorted(candidate_ids),
            "matched_aliases": sorted(
                {
                    alias
                    for _, _, aliases in [*bounded_candidates, *bounded_ambiguities]
                    for alias in aliases
                }
            ),
            "match_tier": "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
            "reason": "BOUNDED_EDIT_HAS_MULTIPLE_OR_SOURCE_ONLY_CANDIDATES",
            "report_norm_id": None,
            "surface": [*bounded_candidates, *bounded_ambiguities][0][0],
        }, comparisons
    surface, child, aliases = bounded_candidates[0]
    return {
        "binding_class": child["binding_class"],
        "candidate_report_norm_ids": [child["report_norm_id"]],
        "matched_aliases": aliases,
        "match_tier": "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
        "reason": "UNIQUE_ONE_EDIT_SCHEMA_ROW_CANDIDATE_AFTER_ALL_EXACT_MISSES",
        "report_norm_id": child["report_norm_id"],
        "surface": surface,
    }, comparisons


def _can_join_wrapped_label(
    current: tuple[int, Mapping[str, Any]],
    following: tuple[int, Mapping[str, Any]],
    body: Sequence[Mapping[str, Any]],
) -> bool:
    """Require one tight, value-free join before composing two label lines."""

    current_index, current_line = current
    following_index, following_line = following
    if any(_is_value(line) for line in body[current_index + 1 : following_index]):
        return False
    current_height = current_line["bbox"][3] - current_line["bbox"][1]
    following_height = following_line["bbox"][3] - following_line["bbox"][1]
    gap = following_line["bbox"][1] - current_line["bbox"][3]
    maximum_gap = max(4, min(current_height, following_height) // 2)
    maximum_indent = max(current_height, following_height) * 3
    return (
        gap <= maximum_gap
        and abs(following_line["bbox"][0] - current_line["bbox"][0]) <= maximum_indent
    )


def _body_and_rows(
    branch: Mapping[str, Any], page: Mapping[str, Any], spec: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    body = []
    comparisons = 0
    maximum = spec["limits"]["maximum_body_lines_per_page"]
    for line in page["lines"][branch["stop"] : branch["stop"] + maximum]:
        boundary, count = _is_boundary(line["vietocr_text"], spec)
        comparisons += count
        if boundary:
            break
        body.append(line)
    semantic = [(index, line) for index, line in enumerate(body) if not _is_value(line)]
    candidates = []
    for ordinal, (_body_index, line) in enumerate(semantic):
        windows = [[line]]
        if ordinal + 1 < len(semantic) and _can_join_wrapped_label(
            semantic[ordinal], semantic[ordinal + 1], body
        ):
            windows.append([line, semantic[ordinal + 1][1]])
        surfaces = [_joined(window) for window in windows]
        matched, count = _row_match(surfaces, spec)
        comparisons += count
        if matched is None:
            continue
        span = next(
            value
            for value in range(len(surfaces), 0, -1)
            if surfaces[value - 1] == matched["surface"]
        )
        selected = semantic[ordinal : ordinal + span]
        material = {
            **matched,
            "evidence": [
                _line_evidence(item, page_sequence=page["page_sequence"]) for _, item in selected
            ],
            "page_sequence": page["page_sequence"],
        }
        candidates.append(
            {
                **material,
                "body_indices": [index for index, _ in selected],
                "proposal_id": "lef12v1:row:" + canonical_json_sha256_v1(material),
                "semantic_start": ordinal,
                "semantic_stop": ordinal + span,
            }
        )
    proposals = []
    occupied: set[int] = set()
    for item in sorted(
        candidates,
        key=lambda candidate: (
            candidate["semantic_start"],
            _TIER_ORDER[candidate["match_tier"]],
            candidate["semantic_start"] - candidate["semantic_stop"],
            candidate["proposal_id"],
        ),
    ):
        covered = set(range(item["semantic_start"], item["semantic_stop"]))
        if covered & occupied:
            continue
        occupied.update(covered)
        proposals.append(item)
    return body, proposals, comparisons


def _is_value(line: Mapping[str, Any]) -> bool:
    return is_accounting_value_surface_v1(line["vietocr_text"]) or (
        type(line["source_text"]) is str and is_accounting_value_surface_v1(line["source_text"])
    )


def _union(boxes: Sequence[Sequence[int]]) -> list[int]:
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _geometry(
    branch: Mapping[str, Any],
    body: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    branch_lines = page["lines"][branch["start"] : branch["stop"]]
    candidate_lines = [*branch_lines, *body]
    label_indices = {index for row in rows for index in row["body_indices"]}
    atoms = []
    for ordinal, line in enumerate(candidate_lines):
        body_index = ordinal - len(branch_lines)
        kind = "LABEL" if body_index in label_indices else "VALUE" if _is_value(line) else "OTHER"
        atoms.append(
            {
                "atom_id": f"p{page['page_sequence']}:l{line['source_line_index']}",
                "bbox": canonical_clone_v1(line["bbox"]),
                "kind": kind,
            }
        )
    return resolve_accounting_table_geometry_v2(
        atoms,
        page_width=page["page_width"],
        page_height=page["page_height"],
        region_bbox=_union([line["bbox"] for line in candidate_lines]),
    )


def _geometry_support(rows: list[dict[str, Any]], geometry: Mapping[str, Any]) -> None:
    assigned_rows = {
        item["row_ordinal"]
        for item in geometry["assignments"]
        if item["status"] == "ASSIGNED_TO_UNIQUE_ROW_LANE"
    }
    row_by_atom = {
        atom_id: band["row_ordinal"]
        for band in geometry["row_bands"]
        for atom_id in band["atom_ids"]
    }
    for row in rows:
        atom_ids = {
            f"p{evidence['page_sequence']}:l{evidence['source_line_index']}"
            for evidence in row["evidence"]
        }
        ordinals = sorted({row_by_atom[item] for item in atom_ids if item in row_by_atom})
        supported = sorted(set(ordinals) & assigned_rows)
        row["geometry_support"] = {
            "assigned_value_row_ordinals": supported,
            "label_row_ordinals": ordinals,
            "visible_unique_value_lane_required": True,
        }
        if row["report_norm_id"] is None:
            row["status"] = "SOURCE_ONLY_AMBIGUOUS"
        elif supported:
            row["status"] = "SCHEMA_ROW_TEXT_AND_GEOMETRY_PROPOSAL_REQUIRES_REPLAY"
        else:
            row["status"] = "TEXT_ROLE_PROPOSAL_MISSING_ROW_VALUE_GEOMETRY"


def _foreign_component(row: Mapping[str, Any]) -> bool:
    return bool(_FOREIGN_COMPONENT.search(_accentless(row["surface"])))


def _unique_bindings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible = [
        row
        for row in rows
        if row["report_norm_id"] is not None
        and row["status"] == "SCHEMA_ROW_TEXT_AND_GEOMETRY_PROPOSAL_REQUIRES_REPLAY"
    ]
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in eligible:
        grouped.setdefault(row["report_norm_id"], []).append(row)
    bindings = []
    for report_norm_id in sorted(grouped):
        candidates = grouped[report_norm_id]
        if len(candidates) == 1:
            selected = candidates[0]
        elif report_norm_id == 782 and sum(_foreign_component(row) for row in candidates) == 1:
            selected = next(row for row in candidates if _foreign_component(row))
        else:
            selected = None
        for row in candidates:
            if row is selected:
                continue
            row["candidate_report_norm_ids"] = [report_norm_id]
            row["report_norm_id"] = None
            row["reason"] = "DUPLICATE_SCHEMA_ROLE_FAIL_CLOSED"
            row["status"] = "DUPLICATE_SCHEMA_ROLE_SOURCE_ONLY_AMBIGUOUS"
        if selected is None:
            continue
        material = {
            "evidence_proposal_id": selected["proposal_id"],
            "foreign_branch_or_subsidiary_component": _foreign_component(selected),
            "report_norm_id": report_norm_id,
            "status": "UNIQUE_SCHEMA_BINDING_PROPOSAL_NO_MAPPING_AUTHORITY",
        }
        bindings.append(
            {**material, "binding_id": "lef12v1:binding:" + canonical_json_sha256_v1(material)}
        )
    return bindings


def _shared_scoped_receipt(
    *,
    branch: Mapping[str, Any],
    bindings: Sequence[Mapping[str, Any]],
    owner: Mapping[str, Any],
    page: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    if owner["mode"] != "SAME_PAGE":
        return {
            "reason": "GENERIC_SCOPED_V1_REQUIRES_SAME_PAGE_OWNER_EVIDENCE",
            "status": "NOT_APPLICABLE_TO_EXPLICIT_CROSS_PAGE_OWNER_CARRY_RECEIPT",
        }
    if len(bindings) < 2:
        return {
            "reason": "AT_LEAST_TWO_UNIQUE_ROLE_BINDINGS_REQUIRED",
            "status": "NOT_RUN_INSUFFICIENT_ROLE_TOPOLOGY",
        }
    bound_ids = {item["evidence_proposal_id"] for item in bindings}
    bound_rows = [row for row in rows if row["proposal_id"] in bound_ids]
    scoped_spec = {
        "continuation_aliases": ["Tiếp theo"],
        "family_id": FAMILY_ID,
        "format_version": SCOPED_SPEC_FORMAT_VERSION,
        "layout_modes": ["ROLES_AS_ROWS"],
        "limits": {
            "axis_tolerance_ppm": 120_000,
            "continuation_page_budget": 0,
            "max_owner_distance_lines": 96,
            "max_role_gap_lines": 32,
            "max_wrap_lines": 3,
            "minimum_cell_row_overlap_ppm": 400_000,
            "unlabeled_total_gap_jitter_ppm": 100_000,
            "unlabeled_total_max_gap_lines": 4,
            "unlabeled_total_max_numeric_columns": 16,
            "unlabeled_total_min_numeric_columns": 2,
        },
        "owner_aliases": [owner["evidence"]["vietocr_raw_nfc_surface"]],
        "require_trailing_total_for_roles_as_columns": False,
        "role_axis": [
            {
                "aliases": [row["surface"]],
                "role": f"RNID_{row['report_norm_id']}",
            }
            for row in bound_rows
        ],
        "scope_axis": [
            {
                "aliases": [branch["surface"]],
                "disposition": "TARGET",
                "scope_id": FAMILY_ID,
            },
            {
                "aliases": ["Giao dịch với các bên liên quan", "Tiền gửi của khách hàng"],
                "disposition": "HARD_VETO_MIXED",
                "scope_id": "NON_LOAN_ENTERPRISE_SCOPE",
            },
        ],
        "structural_reset_aliases": spec["structural_reset_aliases"],
        "target_scope_id": FAMILY_ID,
        "trailing_total_aliases": [],
    }
    try:
        result = build_accounting_scoped_table_graph_v1([page], scoped_spec)
    except AccountingScopedTableGraphV1Error:
        return {
            "reason": "GENERIC_SCOPED_TABLE_REPLAY_REJECTED_DYNAMIC_EXACT_SPEC",
            "status": "SHARED_SCOPED_TABLE_FAIL_CLOSED",
        }
    return {
        "result": result,
        "spec_id": "lef12v1:scoped_spec:" + canonical_json_sha256_v1(scoped_spec),
        "status": "SHARED_SCOPED_TABLE_PROPOSAL_RETAINED_NO_MAPPING_AUTHORITY",
    }


def _near_region(
    branch: Mapping[str, Any],
    owner: Mapping[str, Any],
    reason: str,
    *,
    geometry: Mapping[str, Any] | None = None,
    rows: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    material = {
        "branch": {
            key: canonical_clone_v1(branch[key])
            for key in (
                "branch_id",
                "evidence",
                "matched_aliases",
                "match_tier",
                "page_sequence",
                "surface",
            )
        },
        "owner_context": canonical_clone_v1(owner),
        "reason": reason,
        "source_only_geometry_proposal": (
            canonical_clone_v1(geometry) if geometry is not None else None
        ),
        "source_only_row_proposals": [
            {
                key: canonical_clone_v1(value)
                for key, value in row.items()
                if key not in {"body_indices", "semantic_start", "semantic_stop"}
            }
            for row in rows
        ],
        "status": "SOURCE_ONLY_NEAR_REGION_FAIL_CLOSED",
    }
    return {**material, "near_region_id": "lef12v1:near:" + canonical_json_sha256_v1(material)}


def _build(region_pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    pages = _pages(region_pages)
    spec = build_loan_enterprise_family12_spec_v1()
    branches, comparisons = _branch_candidates(pages, spec)
    regions = []
    near_regions = []
    for branch in branches:
        owner, count = _owner_context(branch, pages, spec)
        comparisons += count
        if owner["disposition"] != "EXPLICIT_OWNER_CONTEXT_ACCEPTED_FOR_PROPOSAL":
            near_regions.append(_near_region(branch, owner, owner["reason"]))
            continue
        page = pages[branch["page_ordinal"]]
        body, rows, count = _body_and_rows(branch, page, spec)
        comparisons += count
        if not body:
            near_regions.append(_near_region(branch, owner, "BRANCH_HAS_NO_BOUNDED_BODY"))
            continue
        geometry = _geometry(branch, body, page, rows)
        _geometry_support(rows, geometry)
        bindings = _unique_bindings(rows)
        if not bindings:
            near_regions.append(
                _near_region(
                    branch,
                    owner,
                    "NO_UNIQUE_SCHEMA_ROW_WITH_VALUE_GEOMETRY",
                    geometry=geometry,
                    rows=rows,
                )
            )
            continue
        shared = _shared_scoped_receipt(
            branch=branch,
            bindings=bindings,
            owner=owner,
            page=page,
            rows=rows,
            spec=spec,
        )
        material = {
            "adaptive_geometry_v2": geometry,
            "binding_proposals": bindings,
            "branch": {
                key: canonical_clone_v1(branch[key])
                for key in (
                    "branch_id",
                    "evidence",
                    "matched_aliases",
                    "match_tier",
                    "page_sequence",
                    "surface",
                )
            },
            "owner_context": owner,
            "row_proposals": [
                {
                    key: canonical_clone_v1(value)
                    for key, value in row.items()
                    if key not in {"body_indices", "semantic_start", "semantic_stop"}
                }
                for row in rows
            ],
            "shared_scoped_table_v1": shared,
            "status": "FAMILY12_STRUCTURAL_PROPOSAL_REQUIRES_NUMERIC_AND_SCHEMA_REPLAY",
        }
        regions.append(
            {**material, "region_id": "lef12v1:region:" + canonical_json_sha256_v1(material)}
        )
    bounded_absences = []
    if not branches:
        bounded_absences.append(
            {
                "page_sequences": [page["page_sequence"] for page in pages],
                "reason": "NO_FAMILY12_BRANCH_IN_CALLER_BOUNDED_PAGES",
                "status": "BOUNDED_ABSENCE_NO_GLOBAL_CORPUS_CLAIM",
            }
        )
    bounded_absences.extend(
        {
            "near_region_id": item["near_region_id"],
            "reason": item["reason"],
            "status": "BOUNDED_ABSENCE_FROM_ACCEPTED_FAMILY12_REGION",
        }
        for item in near_regions
    )
    metrics = {
        "approximate_alias_comparison_count": comparisons,
        "bounded_absence_count": len(bounded_absences),
        "branch_candidate_count": len(branches),
        "cross_page_owner_region_count": sum(
            item["owner_context"]["page_distance"] > 0 for item in regions
        ),
        "region_count": len(regions),
        "source_only_ambiguous_row_count": sum(
            row["status"].endswith("AMBIGUOUS")
            for region in regions
            for row in region["row_proposals"]
        )
        + sum(
            row["status"].endswith("AMBIGUOUS")
            for near in near_regions
            for row in near["source_only_row_proposals"]
        ),
        "unique_binding_proposal_count": sum(
            len(region["binding_proposals"]) for region in regions
        ),
    }
    safety = canonical_clone_v1(spec["safety"])
    safety.update(
        {
            "authenticated_store_or_full_corpus_used": False,
            "gemma_or_other_model_authority": False,
            "shared_geometry_or_scoped_graph_grants_mapping_authority": False,
            "two_role_table_without_owner_716_can_accept": False,
        }
    )
    material = {
        "bounded_absences": bounded_absences,
        "claim_boundary": CLAIM_BOUNDARY,
        "evidence_binding": {
            "canonical_page_evidence_sha256": canonical_json_sha256_v1(pages),
            "family_spec_id": "lef12v1:spec:" + canonical_json_sha256_v1(spec),
        },
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "historical_evidence_summary": spec["historical_evidence_summary"],
        "metrics": metrics,
        "near_regions": near_regions,
        "parent_report_norm_id": PARENT_REPORT_NORM_ID,
        "regions": sorted(
            regions,
            key=lambda item: (
                item["branch"]["page_sequence"],
                item["branch"]["evidence"][0]["bbox"][1],
                item["region_id"],
            ),
        ),
        "report_norm_id": REPORT_NORM_ID,
        "safety": safety,
        "status": (
            "FAMILY12_PROPOSAL_ENUMERATION_WITH_UNRESOLVED_NEAR_REGIONS"
            if near_regions
            else "FAMILY12_PROPOSAL_ENUMERATION"
        ),
    }
    return {**material, "result_id": "lef12v1:result:" + canonical_json_sha256_v1(material)}


def build_loan_enterprise_family12_graph_v1(
    region_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Enumerate Family-12 structural proposals in caller-bounded pages."""

    return _build(region_pages)


def validate_loan_enterprise_family12_graph_replay_v1(
    value: Any, region_pages: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Rebuild all text/context/geometry receipts and identities exactly."""

    if type(value) is not dict or value.get("format_version") != FORMAT_VERSION:
        raise _error("Family-12 graph result identity drifted")
    identity = value.get("result_id")
    if type(identity) is not str:
        raise _error("Family-12 graph result ID drifted")
    material = canonical_clone_v1(value)
    material.pop("result_id", None)
    if identity != "lef12v1:result:" + canonical_json_sha256_v1(material):
        raise _error("Family-12 graph content identity drifted")
    rebuilt = _build(region_pages)
    if not same_typed_json_v1(value, rebuilt):
        raise _error("Family-12 graph does not replay exactly")
    return rebuilt
