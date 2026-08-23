"""Project repeated accounting rows onto period groups and semantic lane axes.

The primitive is deliberately family-agnostic.  A declarative layout spec
names meaningful lane roles and visible header aliases; the complete-document
topology engine supplies the selected owner/child boundary.  The same live
geometry-bound PP-OCRv6 row evidence is then reused for every repeated role.

No bank, filename, page, note number, reporting year or schema identifier is
accepted.  Sparse rows remain sparse: a missing asset/liability cell is not a
zero unless a later independent pixel gate proves a visible dash.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from datetime import date
from statistics import median
from typing import Any

from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_axis_v1
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation.accounting_table_axes_v1 import (
    extract_period_observations_v1,
)
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
    "LAYOUT_SPEC_FORMAT_VERSION",
    "AccountingStackedPeriodLaneAxisV1Error",
    "build_accounting_stacked_period_lane_axis_v1",
    "validate_accounting_stacked_period_lane_axis_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_STACKED_PERIOD_LANE_AXIS_V1"
LAYOUT_SPEC_FORMAT_VERSION = "ACCOUNTING_STACKED_PERIOD_LANE_LAYOUT_SPEC_V1"
CLAIM_BOUNDARY = (
    "COMPLETE_DOCUMENT_EXACT_TOPOLOGY_REPEATED_ROLE_STACKED_OR_HORIZONTAL_PERIOD_"
    "GROUP_MULTI_LEVEL_"
    "HEADER_TO_BODY_GEOMETRY_LANE_PROPOSAL_ONLY_NO_BLANK_TO_ZERO_NUMERIC_"
    "ACCOUNTING_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_file_note_page_year_used_for_routing": False,
    "blank_or_missing_cell_interpreted_as_zero": False,
    "body_geometry_required_for_lane_binding": True,
    "mapping_authority": False,
    "multi_level_headers_supported": True,
    "numeric_authority": False,
    "period_axis_proposal_only": True,
    "raw_record_self_authenticating": False,
    "repeated_role_occurrences_retained": True,
    "schema_authority": False,
    "stacked_and_horizontal_period_groups_supported": True,
    "text_similarity_alone_can_accept": False,
}
_SPEC_FIELDS = {
    "allowed_lane_role_sequences",
    "conditional_lane_aliases",
    "family_id",
    "format_version",
    "lane_roles",
    "max_header_line_span",
    "max_period_blocks",
    "minimum_distinct_valued_roles",
    "minimum_period_blocks",
    "orientation",
}
_LANE_FIELDS = {"aliases", "mapping_eligible", "role", "unit_kind"}
_CONDITIONAL_ALIAS_FIELDS = {"aliases", "role", "when_roles_absent"}
_RESULT_FIELDS = {
    "axis_id",
    "blocks",
    "claim_boundary",
    "family_id",
    "format_version",
    "lane_axis",
    "metrics",
    "orientation",
    "safety",
    "status",
    "topology_region",
    "topology_scan_id",
    "unresolved_reasons",
}


class AccountingStackedPeriodLaneAxisV1Error(ValueError):
    """The topology, period block, header lane or exact replay drifted."""


def _error(message: str) -> AccountingStackedPeriodLaneAxisV1Error:
    return AccountingStackedPeriodLaneAxisV1Error(message)


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _nonempty_string(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise _error(f"{label} must be one nonempty string")
    return value


def _layout_spec(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _SPEC_FIELDS:
        raise _error("stacked-period lane layout spec fields drifted")
    if value["format_version"] != LAYOUT_SPEC_FORMAT_VERSION or value["orientation"] not in {
        "STACKED_PERIOD_BLOCKS",
        "STACKED_OR_HORIZONTAL_PERIOD_GROUPS",
    }:
        raise _error("stacked-period lane layout identity drifted")
    family_id = _nonempty_string(value["family_id"], "layout family ID")
    raw_roles = value["lane_roles"]
    if type(raw_roles) is not list or not raw_roles:
        raise _error("stacked-period layout needs semantic lane roles")
    roles: list[dict[str, Any]] = []
    role_names: set[str] = set()
    for raw in raw_roles:
        if type(raw) is not dict or set(raw) != _LANE_FIELDS:
            raise _error("stacked-period semantic lane fields drifted")
        role = _nonempty_string(raw["role"], "semantic lane role")
        aliases = raw["aliases"]
        if (
            role in role_names
            or type(aliases) is not list
            or not aliases
            or any(type(alias) is not str or not alias.strip() for alias in aliases)
            or type(raw["mapping_eligible"]) is not bool
            or raw["unit_kind"] not in {"MONEY", "PERCENT"}
        ):
            raise _error("stacked-period semantic lane declaration drifted")
        normalized = [normalize_vietnamese_anchor_v1(alias) for alias in aliases]
        if any(not alias for alias in normalized) or len(normalized) != len(set(normalized)):
            raise _error("stacked-period lane aliases normalize ambiguously")
        role_names.add(role)
        roles.append(
            {
                "aliases": normalized,
                "mapping_eligible": raw["mapping_eligible"],
                "role": role,
                "unit_kind": raw["unit_kind"],
            }
        )
    raw_sequences = value["allowed_lane_role_sequences"]
    if type(raw_sequences) is not list or not raw_sequences:
        raise _error("stacked-period layout needs allowed lane sequences")
    sequences: list[list[str]] = []
    for raw in raw_sequences:
        if (
            type(raw) is not list
            or not 1 <= len(raw) <= 8
            or any(type(role) is not str or role not in role_names for role in raw)
            or len(raw) != len(set(raw))
            or raw in sequences
        ):
            raise _error("stacked-period allowed lane sequence drifted")
        sequences.append(list(raw))
    raw_conditional_aliases = value["conditional_lane_aliases"]
    if type(raw_conditional_aliases) is not list:
        raise _error("conditional stacked-period lane aliases must be one list")
    conditional_aliases = []
    for raw in raw_conditional_aliases:
        if (
            type(raw) is not dict
            or set(raw) != _CONDITIONAL_ALIAS_FIELDS
            or raw["role"] not in role_names
            or type(raw["aliases"]) is not list
            or not raw["aliases"]
            or any(type(alias) is not str or not alias.strip() for alias in raw["aliases"])
            or type(raw["when_roles_absent"]) is not list
            or not raw["when_roles_absent"]
            or any(role not in role_names for role in raw["when_roles_absent"])
            or raw["role"] in raw["when_roles_absent"]
            or len(raw["when_roles_absent"]) != len(set(raw["when_roles_absent"]))
        ):
            raise _error("conditional stacked-period lane alias declaration drifted")
        aliases = [normalize_vietnamese_anchor_v1(alias) for alias in raw["aliases"]]
        if any(not alias for alias in aliases) or len(aliases) != len(set(aliases)):
            raise _error("conditional stacked-period aliases normalize ambiguously")
        conditional_aliases.append(
            {
                "aliases": aliases,
                "role": raw["role"],
                "when_roles_absent": list(raw["when_roles_absent"]),
            }
        )
    minimum_blocks = _positive_int(value["minimum_period_blocks"], "minimum period blocks")
    maximum_blocks = _positive_int(value["max_period_blocks"], "maximum period blocks")
    if minimum_blocks > maximum_blocks or maximum_blocks > 4:
        raise _error("stacked-period block bounds drifted")
    return {
        "allowed_lane_role_sequences": sequences,
        "conditional_lane_aliases": conditional_aliases,
        "family_id": family_id,
        "lane_roles": roles,
        "max_header_line_span": _positive_int(
            value["max_header_line_span"], "maximum header line span"
        ),
        "max_period_blocks": maximum_blocks,
        "minimum_distinct_valued_roles": _positive_int(
            value["minimum_distinct_valued_roles"], "minimum distinct valued roles"
        ),
        "minimum_period_blocks": minimum_blocks,
        "orientation": value["orientation"],
    }


def _live_topology(
    parsed_pages: Sequence[Mapping[str, Any]], family_spec: Any, selected_region: Any
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    try:
        top_pages = topology_v1._pages(row_axis_v1._topology_pages(parsed_pages))
        compiled = topology_v1._spec(family_spec)
        prepared_hits = topology_v1._document_hits(top_pages, compiled)
        scan = topology_v1._build_validated_scan(top_pages, compiled, prepared_hits=prepared_hits)
    except topology_v1.AccountingFamilyTopologyV1Error as exc:
        raise _error("stacked-period live topology input drifted") from exc
    if type(selected_region) is not dict:
        raise _error("stacked-period selected topology region must be one exact object")
    selected = [region for region in scan["regions"] if same_typed_json_v1(region, selected_region)]
    if len(selected) != 1:
        raise _error("stacked-period region is not one exact complete live topology")
    region = selected[0]
    hits = prepared_hits[0]
    occurrences = topology_v1._child_records_in_range(
        hits["children"],
        compiled,
        retain_all_occurrences=True,
        start=region["cluster_start_document_line_ordinal"],
        stop=region["cluster_end_document_line_ordinal_exclusive"],
    )
    return scan, region, occurrences


def _axis_line(page_sequence: int, line: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bbox": canonical_clone_v1(line["bbox"]),
        "numeric_score": line["numeric_recognition"]["reader_score"],
        "numeric_text": line["numeric_recognition"]["raw_prediction"],
        "page_sequence": page_sequence,
        "source_line_index": line["line_ordinal"],
        "vietocr_text": line["vietocr_text"],
    }


def _region_lines(
    pages: Sequence[Mapping[str, Any]], region: Mapping[str, Any]
) -> list[dict[str, Any]]:
    start = region["cluster_start_document_line_ordinal"]
    stop = region["cluster_end_document_line_ordinal_exclusive"]
    offset = 0
    result: list[dict[str, Any]] = []
    for page in pages:
        for line in page["lines"]:
            document_ordinal = offset + line["line_ordinal"]
            if start <= document_ordinal < stop:
                result.append(
                    {
                        **_axis_line(page["page_sequence"], line),
                        "document_line_ordinal": document_ordinal,
                    }
                )
        offset += len(page["lines"])
    return result


def _parse_period_key(value: str) -> tuple[int, int, int] | None:
    if value in {"CURRENT_PERIOD_END", "COMPARATIVE_PERIOD_START"}:
        return None
    try:
        day, month, year = (int(item) for item in value.split("/"))
        date(year, month, day)
    except (TypeError, ValueError):
        return None
    return year, month, day


def _period_blocks(
    region_lines: Sequence[Mapping[str, Any]], occurrences: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    observations: list[dict[str, Any]] = []
    for page_sequence in sorted({line["page_sequence"] for line in region_lines}):
        page_lines = [line for line in region_lines if line["page_sequence"] == page_sequence]
        for item in extract_period_observations_v1(page_lines):
            source = next(
                line
                for line in page_lines
                if line["source_line_index"] == item["source_line_index"]
            )
            observations.append(
                {
                    **item,
                    "document_line_ordinal": source["document_line_ordinal"],
                    "page_sequence": page_sequence,
                }
            )
    observations.sort(key=lambda item: item["document_line_ordinal"])
    # Header prose often repeats the same date in both the group heading and a
    # subordinate carrying-value heading.  Consecutive equal observations
    # before the next semantic row belong to one block, not two periods.
    block_observations: list[dict[str, Any]] = []
    prior_occurrence_ordinal = -1
    for observation in observations:
        occurrence_count = sum(
            item["document_line_ordinal"] < observation["document_line_ordinal"]
            for item in occurrences
        )
        if (
            block_observations
            and observation["period"] == block_observations[-1]["period"]
            and occurrence_count == prior_occurrence_ordinal
        ):
            block_observations[-1]["evidence_source_line_indices"] = sorted(
                {
                    *block_observations[-1]["evidence_source_line_indices"],
                    *observation["evidence_source_line_indices"],
                }
            )
            continue
        block_observations.append(observation)
        prior_occurrence_ordinal = occurrence_count
    raw_blocks: list[dict[str, Any]] = []
    for ordinal, observation in enumerate(block_observations):
        start = observation["document_line_ordinal"]
        stop = (
            block_observations[ordinal + 1]["document_line_ordinal"]
            if ordinal + 1 < len(block_observations)
            else max(item["document_line_ordinal"] for item in region_lines) + 1
        )
        selected = [item for item in occurrences if start < item["document_line_ordinal"] < stop]
        if not selected:
            continue
        raw_blocks.append(
            {
                "first_role_document_line_ordinal": min(
                    item["document_line_ordinal"] for item in selected
                ),
                "header_start_document_line_ordinal": start,
                "period_evidence": canonical_clone_v1(observation),
                "resolved_period": observation["period"],
                "role_occurrences": canonical_clone_v1(selected),
                "stop_document_line_ordinal_exclusive": stop,
            }
        )
    # Narrative dates after the final family row can remain inside a broad
    # continuation bound, but they must not participate in period ranking.
    # Rank only observations that actually own at least one semantic family
    # occurrence.
    explicit_keys = {
        item["resolved_period"]: _parse_period_key(item["resolved_period"]) for item in raw_blocks
    }
    valid_explicit = {key: value for key, value in explicit_keys.items() if value is not None}
    ordered_explicit = sorted(valid_explicit, key=lambda item: valid_explicit[item], reverse=True)
    roles = {
        period: "CURRENT_PERIOD" if ordinal == 0 else "COMPARATIVE_PERIOD"
        for ordinal, period in enumerate(ordered_explicit[:2])
    }
    roles.update(
        {
            "CURRENT_PERIOD_END": "CURRENT_PERIOD",
            "COMPARATIVE_PERIOD_START": "COMPARATIVE_PERIOD",
        }
    )
    blocks: list[dict[str, Any]] = []
    reasons: list[str] = []
    for raw in raw_blocks:
        period_role = roles.get(raw["resolved_period"])
        if period_role is None:
            reasons.append("PERIOD_BLOCK_ROLE_UNRESOLVED")
        blocks.append(
            {
                "block_ordinal": len(blocks),
                **raw,
                "period_role": period_role,
            }
        )
    if len({block["period_role"] for block in blocks if block["period_role"] is not None}) != len(
        blocks
    ):
        reasons.append("PERIOD_BLOCK_ROLES_REPEAT_OR_ARE_NOT_UNIQUE")
    return blocks, sorted(set(reasons))


def _horizontal_period_blocks(
    region_lines: Sequence[Mapping[str, Any]],
    occurrences: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Resolve exactly two period groups repeated across numeric columns.

    This path is deliberately structural.  Both visible periods must occur
    before the first family role, on the same page as the role rows, and at
    two distinct horizontal centers.  It therefore cannot reinterpret two
    narrative dates or the ordinary vertically repeated layout as horizontal
    period groups.
    """

    if not region_lines or not occurrences:
        return [], ["HORIZONTAL_PERIOD_GROUPS_LACK_VISIBLE_ROLE_ROWS"]
    first_role_ordinal = min(item["document_line_ordinal"] for item in occurrences)
    role_pages = {item["page_sequence"] for item in occurrences}
    if len(role_pages) != 1:
        return [], ["HORIZONTAL_PERIOD_GROUPS_SPAN_MULTIPLE_PAGES"]
    role_page = next(iter(role_pages))
    observations: list[dict[str, Any]] = []
    page_lines = [line for line in region_lines if line["page_sequence"] == role_page]
    by_source_index = {line["source_line_index"]: line for line in page_lines}
    for item in extract_period_observations_v1(page_lines):
        source = by_source_index[item["source_line_index"]]
        if source["document_line_ordinal"] >= first_role_ordinal:
            continue
        observations.append(
            {
                **item,
                "document_line_ordinal": source["document_line_ordinal"],
                "page_sequence": role_page,
            }
        )
    by_period: dict[str, list[dict[str, Any]]] = {}
    for observation in observations:
        by_period.setdefault(observation["period"], []).append(observation)
    if len(by_period) != 2:
        return [], ["HORIZONTAL_PERIOD_GROUPS_REQUIRE_TWO_DISTINCT_VISIBLE_PERIODS"]
    collapsed: list[dict[str, Any]] = []
    for period, items in by_period.items():
        centers = {item["x_center_x2"] for item in items}
        if len(centers) != 1:
            return [], ["HORIZONTAL_PERIOD_HEADER_CENTER_REPEATS_AMBIGUOUSLY"]
        template = canonical_clone_v1(items[0])
        template["evidence_source_line_indices"] = sorted(
            {
                source_index
                for item in items
                for source_index in item["evidence_source_line_indices"]
            }
        )
        template["document_line_ordinal"] = min(item["document_line_ordinal"] for item in items)
        template["period"] = period
        collapsed.append(template)
    if len({item["x_center_x2"] for item in collapsed}) != 2:
        return [], ["HORIZONTAL_PERIOD_HEADERS_LACK_DISTINCT_X_CENTERS"]
    explicit = {item["period"]: _parse_period_key(item["period"]) for item in collapsed}
    valid_explicit = {period: key for period, key in explicit.items() if key is not None}
    if len(valid_explicit) == 2:
        ordered_periods = sorted(
            valid_explicit, key=lambda item: valid_explicit[item], reverse=True
        )
        roles = {
            ordered_periods[0]: "CURRENT_PERIOD",
            ordered_periods[1]: "COMPARATIVE_PERIOD",
        }
    elif set(explicit) == {"CURRENT_PERIOD_END", "COMPARATIVE_PERIOD_START"}:
        roles = {
            "CURRENT_PERIOD_END": "CURRENT_PERIOD",
            "COMPARATIVE_PERIOD_START": "COMPARATIVE_PERIOD",
        }
    else:
        return [], ["HORIZONTAL_PERIOD_ROLES_ARE_NOT_EXACTLY_RESOLVED"]
    by_role = {roles[item["period"]]: item for item in collapsed}
    blocks = []
    for block_ordinal, period_role in enumerate(("CURRENT_PERIOD", "COMPARATIVE_PERIOD")):
        observation = by_role[period_role]
        blocks.append(
            {
                "block_ordinal": block_ordinal,
                "first_role_document_line_ordinal": first_role_ordinal,
                "header_start_document_line_ordinal": observation["document_line_ordinal"],
                "period_evidence": canonical_clone_v1(observation),
                "period_role": period_role,
                "resolved_period": observation["period"],
                "role_occurrences": canonical_clone_v1(occurrences),
                "stop_document_line_ordinal_exclusive": max(
                    item["document_line_ordinal"] for item in region_lines
                )
                + 1,
            }
        )
    return blocks, []


def _bounded_edit_distance(left: str, right: str, limit: int) -> int | None:
    """Return a small exact edit distance, abandoning work beyond ``limit``."""

    if abs(len(left) - len(right)) > limit:
        return None
    prior = list(range(len(right) + 1))
    for left_ordinal, left_character in enumerate(left, 1):
        current = [left_ordinal]
        row_minimum = left_ordinal
        for right_ordinal, right_character in enumerate(right, 1):
            value = min(
                current[-1] + 1,
                prior[right_ordinal] + 1,
                prior[right_ordinal - 1] + (left_character != right_character),
            )
            current.append(value)
            row_minimum = min(row_minimum, value)
        if row_minimum > limit:
            return None
        prior = current
    return prior[-1] if prior[-1] <= limit else None


def _header_alias_match(surface: str, aliases: Sequence[str]) -> tuple[str, int] | None:
    exact = [alias for alias in aliases if alias in surface]
    if exact:
        return max(exact, key=len), 0
    surface_tokens = surface.split()
    proposals: list[tuple[int, int, str]] = []
    for alias in aliases:
        alias_tokens = alias.split()
        # Fuzzy matching is a rescue only for descriptive multi-token
        # headers.  Short anchors such as "Tài sản" remain exact so text
        # similarity cannot invent a semantic lane.
        if len(alias_tokens) < 3 or len(alias) < 12:
            continue
        limit = 1 if len(alias) <= 32 else 2
        for width in range(max(1, len(alias_tokens) - 1), len(alias_tokens) + 2):
            for start in range(0, len(surface_tokens) - width + 1):
                candidate = " ".join(surface_tokens[start : start + width])
                distance = _bounded_edit_distance(alias, candidate, limit)
                if distance is not None:
                    proposals.append((distance, -len(alias), alias))
    if not proposals:
        return None
    distance, _negative_length, alias = min(proposals)
    return alias, distance


def _header_match(
    lines: Sequence[Mapping[str, Any]], aliases: Sequence[str], max_span: int
) -> dict[str, Any] | None:
    if not lines:
        return None
    candidates: list[dict[str, Any]] = []
    header_scale = median(line["bbox"][3] - line["bbox"][1] for line in lines)
    for start in range(len(lines)):
        for span in range(1, min(max_span, len(lines) - start) + 1):
            selected = lines[start : start + span]
            if span > 1:
                centers = [(line["bbox"][0] + line["bbox"][2]) / 2 for line in selected]
                if max(centers) - min(centers) > max(60.0, header_scale * 2.5):
                    continue
            surface = normalize_vietnamese_anchor_v1(
                " ".join(line["vietocr_text"] for line in selected)
            )
            matched = _header_alias_match(surface, aliases)
            if matched is None:
                continue
            matched_alias, edit_distance = matched
            candidates.append(
                {
                    "bbox": [
                        min(line["bbox"][0] for line in selected),
                        min(line["bbox"][1] for line in selected),
                        max(line["bbox"][2] for line in selected),
                        max(line["bbox"][3] for line in selected),
                    ],
                    "edit_distance": edit_distance,
                    "match_kind": (
                        "EXACT_ACCENTLESS_HEADER_ALIAS"
                        if edit_distance == 0
                        else "BOUNDED_EDIT_RESCUED_HEADER_ALIAS"
                    ),
                    "matched_alias": matched_alias,
                    "source_line_indices": [line["source_line_index"] for line in selected],
                    "surface": " ".join(line["vietocr_text"] for line in selected),
                    "token_count": len(surface.split()),
                }
            )
    # PP-OCR commonly interleaves the leaf headers of adjacent columns in its
    # source-line order.  A vertically split label such as ``Giá trị`` /\
    # ``thuần`` can therefore have other-column headers between its two
    # fragments.  Join only short, vertically ordered, horizontally
    # co-linear fragments inside the already bounded local header band.
    for span in range(2, min(max_span, len(lines)) + 1):
        for selected_tuple in itertools.combinations(lines, span):
            selected = sorted(selected_tuple, key=lambda line: (line["bbox"][1], line["bbox"][0]))
            if len({line["page_sequence"] for line in selected}) != 1:
                continue
            centers = [(line["bbox"][0] + line["bbox"][2]) / 2 for line in selected]
            if max(centers) - min(centers) > max(60.0, header_scale * 2.5) or any(
                right["bbox"][1] - left["bbox"][3] > header_scale * 4.0
                for left, right in zip(selected, selected[1:], strict=False)
            ):
                continue
            surface = normalize_vietnamese_anchor_v1(
                " ".join(line["vietocr_text"] for line in selected)
            )
            matched = _header_alias_match(surface, aliases)
            if matched is None:
                continue
            matched_alias, edit_distance = matched
            candidates.append(
                {
                    "bbox": [
                        min(line["bbox"][0] for line in selected),
                        min(line["bbox"][1] for line in selected),
                        max(line["bbox"][2] for line in selected),
                        max(line["bbox"][3] for line in selected),
                    ],
                    "edit_distance": edit_distance,
                    "match_kind": (
                        "EXACT_ACCENTLESS_HEADER_ALIAS"
                        if edit_distance == 0
                        else "BOUNDED_EDIT_RESCUED_HEADER_ALIAS"
                    ),
                    "matched_alias": matched_alias,
                    "source_line_indices": sorted(line["source_line_index"] for line in selected),
                    "surface": " ".join(line["vietocr_text"] for line in selected),
                    "token_count": len(surface.split()),
                }
            )
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda item: (
            item["edit_distance"],
            item["token_count"],
            len(item["source_line_indices"]),
            -max(item["source_line_indices"]),
        ),
    )


def _disambiguate_combined_lane_matches(
    matches: dict[str, dict[str, Any] | None],
) -> None:
    """Prefer an explicit total over its contained carrying-value phrase."""

    signed = matches.get("SIGNED_CARRYING_VALUE")
    net = matches.get("NET_VALUE")
    if (
        signed is not None
        and net is not None
        and set(signed["source_line_indices"]).issubset(net["source_line_indices"])
        and normalize_vietnamese_anchor_v1(signed["surface"]).startswith("tong ")
        and normalize_vietnamese_anchor_v1(net["matched_alias"]).startswith("tong ")
    ):
        matches["SIGNED_CARRYING_VALUE"] = None


def _lane_axis(
    region_lines: Sequence[Mapping[str, Any]],
    blocks: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    region: Mapping[str, Any],
    spec: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    lane_count = (
        max(
            (
                lane
                for row in rows
                for lane in (
                    [value["column_ordinal"] for value in row["values"]]
                    + list(row["missing_column_ordinals"])
                )
            ),
            default=-1,
        )
        + 1
    )
    if lane_count <= 0:
        return [], ["BODY_DERIVED_LANE_AXIS_UNRESOLVED"]
    header_lines = [
        line
        for line in region_lines
        if region["parent_match"]["end_document_line_ordinal"]
        < line["document_line_ordinal"]
        < min(
            (block["header_start_document_line_ordinal"] for block in blocks),
            default=region["cluster_end_document_line_ordinal_exclusive"],
        )
    ]
    for block in blocks:
        header_lines.extend(
            line
            for line in region_lines
            if block["header_start_document_line_ordinal"]
            <= line["document_line_ordinal"]
            < block["first_role_document_line_ordinal"]
        )
    matches = {
        lane["role"]: _header_match(header_lines, lane["aliases"], spec["max_header_line_span"])
        for lane in spec["lane_roles"]
    }
    for conditional in spec["conditional_lane_aliases"]:
        if matches[conditional["role"]] is None and all(
            matches[role] is None for role in conditional["when_roles_absent"]
        ):
            matches[conditional["role"]] = _header_match(
                header_lines,
                conditional["aliases"],
                spec["max_header_line_span"],
            )
    _disambiguate_combined_lane_matches(matches)
    candidates = [
        sequence
        for sequence in spec["allowed_lane_role_sequences"]
        if len(sequence) == lane_count and all(matches[role] is not None for role in sequence)
    ]
    body_centers = []
    for ordinal in range(lane_count):
        observed = {
            value["column_center"]
            for row in rows
            for value in row["values"]
            if value["column_ordinal"] == ordinal
        }
        if len(observed) != 1:
            return [], ["BODY_LANE_CENTER_IS_ABSENT_OR_INCONSISTENT"]
        body_centers.append(next(iter(observed)))
    if len(candidates) > 1:
        scores = {
            tuple(sequence): sum(
                abs(
                    body_centers[ordinal]
                    - (matches[role]["bbox"][0] + matches[role]["bbox"][2]) / 2
                )
                for ordinal, role in enumerate(sequence)
            )
            for sequence in candidates
        }
        minimum = min(scores.values())
        candidates = [sequence for sequence in candidates if scores[tuple(sequence)] == minimum]
    if len(candidates) != 1:
        return [], ["VISIBLE_HEADER_TO_BODY_LANE_SEQUENCE_NOT_UNIQUE"]
    sequence = candidates[0]
    header_centers = [
        (matches[role]["bbox"][0] + matches[role]["bbox"][2]) / 2 for role in sequence
    ]
    header_order_valid = True
    for left_role, right_role, left_center, right_center in zip(
        sequence,
        sequence[1:],
        header_centers,
        header_centers[1:],
        strict=False,
    ):
        if left_center < right_center:
            continue
        left_match = matches[left_role]
        right_match = matches[right_role]
        shared_lines = set(left_match["source_line_indices"]) & set(
            right_match["source_line_indices"]
        )
        shared_surface = normalize_vietnamese_anchor_v1(left_match["surface"])
        if (
            not shared_lines
            or shared_surface != normalize_vietnamese_anchor_v1(right_match["surface"])
            or shared_surface.find(left_match["matched_alias"])
            >= shared_surface.find(right_match["matched_alias"])
        ):
            header_order_valid = False
            break
    if not header_order_valid:
        return [], ["VISIBLE_HEADER_LANE_ORDER_DIFFERS_FROM_BODY_ORDER"]
    lane_specs = {lane["role"]: lane for lane in spec["lane_roles"]}
    result = []
    for ordinal, role in enumerate(sequence):
        result.append(
            {
                "block_ordinal": None,
                "column_center": body_centers[ordinal],
                "column_ordinal": ordinal,
                "header_match": canonical_clone_v1(matches[role]),
                "mapping_eligible": lane_specs[role]["mapping_eligible"],
                "period_role": None,
                "role": role,
                "unit_kind": lane_specs[role]["unit_kind"],
            }
        )
    return result, []


def _horizontal_lane_axis(
    region_lines: Sequence[Mapping[str, Any]],
    blocks: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    column_grids: Sequence[Mapping[str, Any]],
    region: Mapping[str, Any],
    spec: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Bind one repeated local lane sequence inside each horizontal period."""

    pages = {row["label_match"]["page_sequence"] for row in rows}
    if len(pages) != 1 or len(blocks) != 2:
        return [], ["HORIZONTAL_PERIOD_BODY_GRID_IS_NOT_ONE_EXACT_PAGE"]
    page_sequence = next(iter(pages))
    grid = next(
        (item for item in column_grids if item["page_sequence"] == page_sequence),
        None,
    )
    if grid is None or len(grid["column_centers"]) < 2:
        return [], ["HORIZONTAL_PERIOD_BODY_GRID_IS_ABSENT"]
    period_centers = {
        block["block_ordinal"]: block["period_evidence"]["x_center_x2"] / 2 for block in blocks
    }
    if len(set(period_centers.values())) != 2:
        return [], ["HORIZONTAL_PERIOD_HEADERS_LACK_DISTINCT_X_CENTERS"]
    global_columns_by_block = {block["block_ordinal"]: [] for block in blocks}
    for column_ordinal, center in enumerate(grid["column_centers"]):
        distances = sorted(
            (abs(center - period_center), block_ordinal)
            for block_ordinal, period_center in period_centers.items()
        )
        if len(distances) != 2 or distances[0][0] == distances[1][0]:
            return [], ["HORIZONTAL_BODY_COLUMN_TO_PERIOD_IS_NOT_UNIQUE"]
        global_columns_by_block[distances[0][1]].append(column_ordinal)
    group_sizes = {len(columns) for columns in global_columns_by_block.values()}
    if len(group_sizes) != 1 or not next(iter(group_sizes)):
        return [], ["HORIZONTAL_PERIOD_GROUP_LANE_COUNTS_DIFFER"]
    first_role_ordinal = min(block["first_role_document_line_ordinal"] for block in blocks)
    header_lines = [
        line
        for line in region_lines
        if line["page_sequence"] == page_sequence
        and region["parent_match"]["end_document_line_ordinal"]
        < line["document_line_ordinal"]
        < first_role_ordinal
    ]
    lane_specs = {lane["role"]: lane for lane in spec["lane_roles"]}
    block_matches: dict[int, tuple[list[str], dict[str, dict[str, Any]]]] = {}
    for block in blocks:
        block_ordinal = block["block_ordinal"]
        period_center = period_centers[block_ordinal]
        local_headers = [
            line
            for line in header_lines
            if min(
                (abs((line["bbox"][0] + line["bbox"][2]) / 2 - center), ordinal)
                for ordinal, center in period_centers.items()
            )[1]
            == block_ordinal
        ]
        matches = {
            lane["role"]: _header_match(
                local_headers, lane["aliases"], spec["max_header_line_span"]
            )
            for lane in spec["lane_roles"]
        }
        for conditional in spec["conditional_lane_aliases"]:
            if matches[conditional["role"]] is None and all(
                matches[role] is None for role in conditional["when_roles_absent"]
            ):
                matches[conditional["role"]] = _header_match(
                    local_headers,
                    conditional["aliases"],
                    spec["max_header_line_span"],
                )
        _disambiguate_combined_lane_matches(matches)
        # A printed combined header such as ``Tài sản/(Công nợ)`` describes
        # one signed carrying-value column.  The same surface naturally also
        # contains the atomic words ``Tài sản`` and ``Công nợ``; retaining all
        # three interpretations would manufacture a second two-lane layout.
        # Suppress an atomic interpretation only when it is backed by the
        # exact same header source lines as the explicit combined role.
        combined = matches.get("SIGNED_CARRYING_VALUE")
        if combined is not None:
            combined_lines = set(combined["source_line_indices"])
            for atomic_role in ("ASSET_CARRYING_VALUE", "LIABILITY_CARRYING_VALUE"):
                atomic = matches.get(atomic_role)
                if atomic is not None and set(atomic["source_line_indices"]) == combined_lines:
                    matches[atomic_role] = None
        columns = global_columns_by_block[block_ordinal]
        candidates = [
            sequence
            for sequence in spec["allowed_lane_role_sequences"]
            if len(sequence) == len(columns) and all(matches[role] is not None for role in sequence)
        ]
        if len(candidates) > 1:
            scores = {
                tuple(sequence): sum(
                    abs(
                        grid["column_centers"][column_ordinal]
                        - (matches[role]["bbox"][0] + matches[role]["bbox"][2]) / 2
                    )
                    for role, column_ordinal in zip(sequence, columns, strict=True)
                )
                for sequence in candidates
            }
            minimum = min(scores.values())
            candidates = [sequence for sequence in candidates if scores[tuple(sequence)] == minimum]
        if len(candidates) != 1:
            return [], ["HORIZONTAL_VISIBLE_HEADER_TO_LANE_SEQUENCE_NOT_UNIQUE"]
        sequence = candidates[0]
        header_centers = [
            (matches[role]["bbox"][0] + matches[role]["bbox"][2]) / 2 for role in sequence
        ]
        if any(
            left >= right for left, right in zip(header_centers, header_centers[1:], strict=False)
        ):
            return [], ["HORIZONTAL_VISIBLE_HEADER_LANE_ORDER_DIFFERS_FROM_BODY_ORDER"]
        # The local header must actually occupy its period half; a distant
        # narrative alias may not name a body lane merely by text.
        if any(
            abs(header_center - period_center)
            > max(
                60.0,
                max(abs(grid["column_centers"][column] - period_center) for column in columns)
                * 1.75,
            )
            for header_center in header_centers
        ):
            return [], ["HORIZONTAL_HEADER_GEOMETRY_IS_OUTSIDE_PERIOD_GROUP"]
        block_matches[block_ordinal] = (sequence, matches)
    sequences = {tuple(item[0]) for item in block_matches.values()}
    if len(sequences) != 1:
        return [], ["HORIZONTAL_PERIOD_GROUP_LANE_SEQUENCES_DIFFER"]
    result = []
    for block in blocks:
        block_ordinal = block["block_ordinal"]
        sequence, matches = block_matches[block_ordinal]
        columns = global_columns_by_block[block_ordinal]
        for role, column_ordinal in zip(sequence, columns, strict=True):
            result.append(
                {
                    "block_ordinal": block_ordinal,
                    "column_center": grid["column_centers"][column_ordinal],
                    "column_ordinal": column_ordinal,
                    "header_match": canonical_clone_v1(matches[role]),
                    "mapping_eligible": lane_specs[role]["mapping_eligible"],
                    "period_role": block["period_role"],
                    "role": role,
                    "unit_kind": lane_specs[role]["unit_kind"],
                }
            )
    return result, []


def _project_blocks(
    blocks: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    lane_axis: Sequence[Mapping[str, Any]],
    *,
    orientation: str,
) -> list[dict[str, Any]]:
    result = []
    for block in blocks:
        local_axis = [
            item for item in lane_axis if item["block_ordinal"] in {None, block["block_ordinal"]}
        ]
        role_by_lane = {item["column_ordinal"]: item["role"] for item in local_axis}
        block_rows = []
        for row in rows:
            label = row["label_match"]
            if orientation == "STACKED_PERIOD_BLOCKS" and not (
                block["header_start_document_line_ordinal"]
                < label["document_line_ordinal"]
                < block["stop_document_line_ordinal_exclusive"]
            ):
                continue
            block_rows.append(
                {
                    "label_match": canonical_clone_v1(label),
                    "missing_lane_roles": [
                        role_by_lane[lane]
                        for lane in row["missing_column_ordinals"]
                        if lane in role_by_lane
                    ],
                    "role": row["role"],
                    "role_occurrence_ordinal": label["role_occurrence_ordinal"],
                    "values": [
                        {
                            **canonical_clone_v1(value),
                            "lane_role": role_by_lane[value["column_ordinal"]],
                        }
                        for value in row["values"]
                        if value["column_ordinal"] in role_by_lane
                    ],
                }
            )
        result.append(
            {
                key: canonical_clone_v1(value)
                for key, value in block.items()
                if key != "role_occurrences"
            }
            | {"rows": block_rows}
        )
    return result


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["blocks"]) is not list
        or type(value["lane_axis"]) is not list
        or type(value["unresolved_reasons"]) is not list
        or any(type(item) is not str or not item for item in value["unresolved_reasons"])
    ):
        raise _error("stacked-period lane-axis result contract drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("axis_id")
    if identity != "asplav1:axis:" + canonical_json_sha256_v1(material):
        raise _error("stacked-period lane-axis identity drifted")
    return canonical_clone_v1(value)


def build_accounting_stacked_period_lane_axis_v1(
    pages: Any,
    family_topology_spec: Any,
    topology_region: Any,
    layout_spec: Any,
) -> dict[str, Any]:
    """Build one exact stacked-period semantic lane proposal."""

    try:
        parsed_pages = row_axis_v1._pages(pages)
    except row_axis_v1.AccountingFamilyRowAxisV1Error as exc:
        raise _error("stacked-period geometry/numeric pages drifted") from exc
    compiled_layout = _layout_spec(layout_spec)
    scan, region, occurrences = _live_topology(parsed_pages, family_topology_spec, topology_region)
    if scan["family_id"] != compiled_layout["family_id"]:
        raise _error("stacked-period topology/layout family identity differs")
    expanded_region = canonical_clone_v1(region)
    expanded_region["child_matches"] = canonical_clone_v1(occurrences)
    region_lines = _region_lines(parsed_pages, region)
    try:
        rows, column_grids = row_axis_v1._rows(parsed_pages, expanded_region)
    except row_axis_v1.AccountingFamilyRowAxisV1Error as exc:
        raise _error("stacked-period visible row geometry drifted") from exc
    blocks, period_reasons = _period_blocks(region_lines, occurrences)
    orientation = "STACKED_PERIOD_BLOCKS"
    if (
        not (
            compiled_layout["minimum_period_blocks"]
            <= len(blocks)
            <= compiled_layout["max_period_blocks"]
        )
        and compiled_layout["orientation"] == "STACKED_OR_HORIZONTAL_PERIOD_GROUPS"
    ):
        horizontal_blocks, horizontal_reasons = _horizontal_period_blocks(region_lines, occurrences)
        if not horizontal_reasons:
            blocks = horizontal_blocks
            period_reasons = []
            orientation = "HORIZONTAL_PERIOD_GROUPS"
        else:
            period_reasons = [*period_reasons, *horizontal_reasons]
    if orientation == "HORIZONTAL_PERIOD_GROUPS":
        lane_axis, lane_reasons = _horizontal_lane_axis(
            region_lines,
            blocks,
            rows,
            column_grids,
            region,
            compiled_layout,
        )
    else:
        lane_axis, lane_reasons = _lane_axis(region_lines, blocks, rows, region, compiled_layout)
    reasons = [*period_reasons, *lane_reasons]
    if not (
        compiled_layout["minimum_period_blocks"]
        <= len(blocks)
        <= compiled_layout["max_period_blocks"]
    ):
        reasons.append("VISIBLE_PERIOD_BLOCK_COUNT_OUTSIDE_DECLARED_BOUNDS")
    valued_roles = {row["role"] for row in rows if row["values"]}
    if len(valued_roles) < compiled_layout["minimum_distinct_valued_roles"]:
        reasons.append("TOO_FEW_DISTINCT_SEMANTIC_ROLES_WITH_VISIBLE_VALUES")
    projected_blocks = (
        _project_blocks(blocks, rows, lane_axis, orientation=orientation) if lane_axis else []
    )
    reasons = sorted(set(reasons))
    material = {
        "blocks": projected_blocks,
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": scan["family_id"],
        "format_version": FORMAT_VERSION,
        "lane_axis": lane_axis,
        "metrics": {
            "block_count": len(projected_blocks),
            "lane_count": len(lane_axis),
            "role_occurrence_count": len(occurrences),
            "valued_row_count": len(rows),
        },
        "orientation": orientation,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "STACKED_PERIOD_LANE_AXIS_BOUND_PROPOSAL_ONLY"
            if not reasons
            else "UNRESOLVED_STACKED_PERIOD_OR_LANE_AXIS"
        ),
        "topology_region": canonical_clone_v1(region),
        "topology_scan_id": scan["scan_id"],
        "unresolved_reasons": reasons,
    }
    return _validate_result(
        {**material, "axis_id": "asplav1:axis:" + canonical_json_sha256_v1(material)}
    )


def validate_accounting_stacked_period_lane_axis_replay_v1(
    value: Any,
    pages: Any,
    family_topology_spec: Any,
    layout_spec: Any,
) -> dict[str, Any]:
    """Reject any mutation through exact complete-input reconstruction."""

    persisted = _validate_result(value)
    expected = build_accounting_stacked_period_lane_axis_v1(
        pages,
        family_topology_spec,
        persisted["topology_region"],
        layout_spec,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("stacked-period lane axis does not replay exactly")
    return persisted
