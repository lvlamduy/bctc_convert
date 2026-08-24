"""Generic graph builder for scoped, region-local accounting tables.

The builder is deliberately family-blind.  A caller supplies Vietnamese owner,
scope, role, continuation, reset, and trailing-total aliases in one declarative
specification.  The shared implementation then:

* preserves the exact NFC VietOCR surface and a separate accentless shortlist
  surface;
* resolves wrapped labels and body/header geometry in visual order, independent
  of provider serialization order;
* supports roles printed as rows or as columns;
* keeps source role/column ordinals separate from logical reporting-period
  lanes; and
* groups complete repeated period segments or a narrowly proved adjacent-page
  role-deficit completion.

Every text match is a proposal.  Values remain unparsed source surfaces, a
missing detector cell remains a pixel-region proposal, and neither accounting,
schema mapping, nor export authority is granted here.
"""

from __future__ import annotations

import re
import unicodedata
from bisect import bisect_right
from collections import Counter, OrderedDict
from collections.abc import Mapping, Sequence
from contextvars import ContextVar
from datetime import datetime
from functools import lru_cache
from itertools import product
from statistics import median
from threading import RLock
from typing import Any

from bctc_ai.evaluation.accounting_table_axes_v1 import (
    accounting_unit_surface_v1,
    extract_period_observations_v1,
    is_accounting_value_surface_v1,
    is_number_like_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    match_vietnamese_anchor_alias_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    AdaptiveAccountingTableGeometryV1Error,
    assign_value_row_lanes_v1,
    build_multilevel_header_graph_v1,
    cluster_numeric_rows_v1,
    infer_numeric_column_centers_v1,
    median_text_height_v1,
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.source_structure.adjacent_page_table_geometry_relations_v1 import (
    ADJACENT_PAGE_TABLE_GEOMETRY_FORMAT_VERSION_V1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "SPEC_FORMAT_VERSION",
    "AccountingScopedTableGraphV1Error",
    "build_accounting_scoped_table_graph_v1",
    "validate_accounting_scoped_table_graph_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_SCOPED_TABLE_GRAPH_V1"
SPEC_FORMAT_VERSION = "ACCOUNTING_SCOPED_TABLE_FAMILY_SPEC_V1"
CLAIM_BOUNDARY = (
    "REGION_LOCAL_DECLARATIVE_VIETNAMESE_OWNER_SCOPE_ROLE_VISUAL_GEOMETRY_"
    "PERIOD_SEGMENT_AND_BOUNDED_ADJACENT_ROLE_DEFICIT_GRAPH_PROPOSAL_ONLY_"
    "NO_NUMERIC_ACCOUNTING_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "accentless_or_approximate_text_alone_can_accept": False,
    "accounting_authority": False,
    "adjacent_page_geometry_authority_claimed": False,
    "adjacent_partial_merge_requires_shared_geometry_replay_before_mapping": True,
    "bank_filename_note_page_year_or_schema_used_for_routing": False,
    "blank_or_detector_hole_synthesized_as_zero": False,
    "broad_or_mixed_scope_can_be_narrowed_by_values": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "period_lane_derived_from_role_or_source_column_ordinal": False,
    "provider_line_order_used_as_visual_order": False,
    "raw_nfc_and_accentless_evidence_retained_separately": True,
    "schema_authority": False,
    "structural_reset_can_be_crossed": False,
    "text_match_is_shortlist_only": True,
}
_ROLE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_ID = re.compile(r"^[A-Z][A-Z0-9_]*$")
_INLINE_VALUE = re.compile(r"\s+(?:[-\u2013\u2014\u2212]|\(?[+-]?\d[\d.,\u00a0\u202f ]*%?\)?)\s*$")
_LAYOUTS = {"ROLES_AS_ROWS", "ROLES_AS_COLUMNS"}
_DISPOSITIONS = {"TARGET", "HARD_VETO_BROAD", "HARD_VETO_MIXED"}
_ENGINE_CACHE_REVISION = "ACCOUNTING_SCOPED_TABLE_GRAPH_REGION_FIRST_CACHE_V2"
_MATCHER_METRICS_FORMAT_VERSION = "ACCOUNTING_SCOPED_TABLE_MATCHER_METRICS_V2"
_SURFACE_CACHE_MAXSIZE = 8_192
_BUILD_CACHE_MAXSIZE = 8
_BUILD_CACHE_MAX_BYTES = 4 * 1024 * 1024
_FEATURE_CACHE_MAXSIZE = 2_048
_FEATURE_CACHE_MAX_TEXT_CHARS = 512
_QGRAM_CACHE_MAXSIZE = 512
_QGRAM_CACHE_MAX_TEXT_CHARS = 256
_BUILD_CACHE: OrderedDict[tuple[bytes, bytes, tuple[Any, ...]], tuple[bytes, bytes, int]] = (
    OrderedDict()
)
_BUILD_CACHE_LOCK = RLock()
_BUILD_CACHE_BYTES = 0
_BUILD_CACHE_BYPASSES = 0
_BUILD_CACHE_EVICTIONS = 0
_BUILD_CACHE_HITS = 0
_BUILD_CACHE_MISSES = 0
_LAST_BUILD_TELEMETRY: ContextVar[dict[str, Any] | None] = ContextVar(
    "accounting_scoped_table_graph_v1_last_build_telemetry",
    default=None,
)


class AccountingScopedTableGraphV1Error(ValueError):
    """A scoped-table spec, region, graph identity, or replay drifted."""


def _error(message: str) -> AccountingScopedTableGraphV1Error:
    return AccountingScopedTableGraphV1Error(message)


def _nfc(value: Any, label: str, *, nonempty: bool = True) -> str:
    if type(value) is not str or (nonempty and not value.strip()):
        raise _error(f"{label} must be one {'nonempty ' if nonempty else ''}exact string")
    if value != unicodedata.normalize("NFC", value):
        raise _error(f"{label} must already be NFC-normalized")
    return value


def _accented_surface_uncached(value: str) -> str:
    value = unicodedata.normalize("NFC", value.casefold())
    return " ".join(re.sub(r"[^0-9a-zà-ỹđ%]+", " ", value).split())


@lru_cache(maxsize=_FEATURE_CACHE_MAXSIZE)
def _accented_surface_cached(value: str) -> str:
    return _accented_surface_uncached(value)


def _accented_surface(value: str) -> str:
    if len(value) > _FEATURE_CACHE_MAX_TEXT_CHARS:
        return _accented_surface_uncached(value)
    return _accented_surface_cached(value)


@lru_cache(maxsize=_FEATURE_CACHE_MAXSIZE)
def _accentless_surface_cached(value: str, normalizer: Any) -> str:
    """Cache the pure semantic normalization shared by overlapping windows."""

    return normalizer(value)


def _accentless_surface(value: str) -> str:
    if len(value) > _FEATURE_CACHE_MAX_TEXT_CHARS:
        return normalize_vietnamese_anchor_v1(value)
    return _accentless_surface_cached(value, normalize_vietnamese_anchor_v1)


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be one nonnegative exact integer")
    return value


def _aliases(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if type(value) is not list or (not allow_empty and not value):
        raise _error(f"{label} must be one {'possibly empty' if allow_empty else 'nonempty'} list")
    result = [_nfc(item, f"{label} alias") for item in value]
    normalized = [_accentless_surface(item) for item in result]
    if any(not item for item in normalized) or len(set(normalized)) != len(normalized):
        raise _error(f"{label} aliases must be unique after accentless normalization")
    return result


def _component_groups(value: Any, label: str) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise _error(f"{label} component groups must be one list")
    result = []
    seen_ids: set[str] = set()
    seen_aliases: set[str] = set()
    for raw in value:
        if type(raw) is not dict or set(raw) != {"aliases", "component_id"}:
            raise _error(f"{label} component group fields drifted")
        component_id = _nfc(raw["component_id"], f"{label} component ID")
        if _ID.fullmatch(component_id) is None or component_id in seen_ids:
            raise _error(f"{label} component identity repeats or drifted")
        aliases = _aliases(raw["aliases"], f"{label} {component_id}")
        normalized = {_accentless_surface(item) for item in aliases}
        if normalized & seen_aliases:
            raise _error(f"{label} component aliases overlap across required groups")
        seen_ids.add(component_id)
        seen_aliases.update(normalized)
        result.append({"aliases": aliases, "component_id": component_id})
    if result and len(result) < 2:
        raise _error(f"{label} component composition requires at least two groups")
    return result


def _lane_component_groups(value: Any, label: str) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise _error(f"{label} lane component groups must be one list")
    result = []
    seen_ids: set[str] = set()
    for raw in value:
        if type(raw) is not dict or set(raw) != {"aliases", "component_id", "source"}:
            raise _error(f"{label} lane component group fields drifted")
        component_id = _nfc(raw["component_id"], f"{label} lane component ID")
        if (
            _ID.fullmatch(component_id) is None
            or component_id in seen_ids
            or raw["source"] not in {"LEAF", "PATH"}
        ):
            raise _error(f"{label} lane component identity/source repeats or drifted")
        seen_ids.add(component_id)
        result.append(
            {
                "aliases": _aliases(raw["aliases"], f"{label} lane {component_id}"),
                "component_id": component_id,
                "source": raw["source"],
            }
        )
    if result and len(result) < 2:
        raise _error(f"{label} lane component composition requires at least two groups")
    return result


def _spec(value: Any) -> dict[str, Any]:
    expected = {
        "continuation_aliases",
        "family_id",
        "format_version",
        "layout_modes",
        "limits",
        "owner_aliases",
        "require_trailing_total_for_roles_as_columns",
        "role_axis",
        "scope_axis",
        "structural_reset_aliases",
        "target_scope_id",
        "trailing_total_aliases",
    }
    optional = {"owner_component_groups"}
    if type(value) is not dict or not expected <= set(value) <= expected | optional:
        raise _error("scoped-table family spec fields drifted")
    family_id = _nfc(value["family_id"], "family ID")
    if value["format_version"] != SPEC_FORMAT_VERSION or _ID.fullmatch(family_id) is None:
        raise _error("scoped-table family spec identity drifted")
    layouts = value["layout_modes"]
    if (
        type(layouts) is not list
        or not layouts
        or layouts != sorted(set(layouts))
        or any(item not in _LAYOUTS for item in layouts)
    ):
        raise _error("scoped-table layout modes drifted")
    raw_roles = value["role_axis"]
    if type(raw_roles) is not list or len(raw_roles) < 2:
        raise _error("scoped-table role axis requires at least two roles")
    roles: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    for raw in raw_roles:
        if type(raw) is not dict or set(raw) != {"aliases", "role"}:
            raise _error("scoped-table role fields drifted")
        role = _nfc(raw["role"], "scoped-table role")
        if _ROLE.fullmatch(role) is None or role in seen_roles:
            raise _error("scoped-table role identity repeats or drifted")
        seen_roles.add(role)
        roles.append({"aliases": _aliases(raw["aliases"], role), "role": role})
    raw_scopes = value["scope_axis"]
    if type(raw_scopes) is not list or len(raw_scopes) < 2:
        raise _error("scoped-table scope axis requires target and hard-veto classes")
    scopes: list[dict[str, Any]] = []
    seen_scopes: set[str] = set()
    for raw in raw_scopes:
        base_fields = {"aliases", "disposition", "scope_id"}
        if type(raw) is not dict or not base_fields <= set(raw) <= base_fields | {
            "lane_component_groups",
            "required_component_groups",
        }:
            raise _error("scoped-table scope fields drifted")
        scope_id = _nfc(raw["scope_id"], "scope ID")
        if (
            _ID.fullmatch(scope_id) is None
            or scope_id in seen_scopes
            or raw["disposition"] not in _DISPOSITIONS
        ):
            raise _error("scoped-table scope identity/disposition drifted")
        seen_scopes.add(scope_id)
        scopes.append(
            {
                "aliases": _aliases(raw["aliases"], scope_id),
                "disposition": raw["disposition"],
                "lane_component_groups": _lane_component_groups(
                    raw.get("lane_component_groups", []), scope_id
                ),
                "required_component_groups": _component_groups(
                    raw.get("required_component_groups", []), scope_id
                ),
                "scope_id": scope_id,
            }
        )
    target = _nfc(value["target_scope_id"], "target scope ID")
    target_records = [item for item in scopes if item["scope_id"] == target]
    if len(target_records) != 1 or target_records[0]["disposition"] != "TARGET":
        raise _error("target scope must name exactly one TARGET scope class")
    if sum(item["disposition"] == "TARGET" for item in scopes) != 1:
        raise _error("scoped-table spec must contain exactly one target scope")
    limits = value["limits"]
    if type(limits) is not dict or set(limits) != {
        "axis_tolerance_ppm",
        "continuation_page_budget",
        "max_owner_distance_lines",
        "max_role_gap_lines",
        "max_wrap_lines",
        "minimum_cell_row_overlap_ppm",
        "unlabeled_total_gap_jitter_ppm",
        "unlabeled_total_max_gap_lines",
        "unlabeled_total_max_numeric_columns",
        "unlabeled_total_min_numeric_columns",
    }:
        raise _error("scoped-table structural limits drifted")
    parsed_limits = {
        "axis_tolerance_ppm": _positive_int(limits["axis_tolerance_ppm"], "axis tolerance"),
        "continuation_page_budget": _nonnegative_int(
            limits["continuation_page_budget"], "continuation page budget"
        ),
        "max_owner_distance_lines": _positive_int(
            limits["max_owner_distance_lines"], "owner distance"
        ),
        "max_role_gap_lines": _positive_int(limits["max_role_gap_lines"], "role gap"),
        "max_wrap_lines": _positive_int(limits["max_wrap_lines"], "wrap limit"),
        "minimum_cell_row_overlap_ppm": _positive_int(
            limits["minimum_cell_row_overlap_ppm"], "cell row overlap"
        ),
        "unlabeled_total_gap_jitter_ppm": _nonnegative_int(
            limits["unlabeled_total_gap_jitter_ppm"],
            "unlabeled total gap jitter",
        ),
        "unlabeled_total_max_gap_lines": _positive_int(
            limits["unlabeled_total_max_gap_lines"], "unlabeled total row gap"
        ),
        "unlabeled_total_max_numeric_columns": _positive_int(
            limits["unlabeled_total_max_numeric_columns"],
            "unlabeled total maximum numeric columns",
        ),
        "unlabeled_total_min_numeric_columns": _positive_int(
            limits["unlabeled_total_min_numeric_columns"],
            "unlabeled total minimum numeric columns",
        ),
    }
    if (
        parsed_limits["axis_tolerance_ppm"] > 1_000_000
        or parsed_limits["minimum_cell_row_overlap_ppm"] > 1_000_000
        or parsed_limits["unlabeled_total_gap_jitter_ppm"] > 500_000
        or parsed_limits["max_wrap_lines"] > 6
        or parsed_limits["unlabeled_total_min_numeric_columns"] < 2
        or parsed_limits["unlabeled_total_max_numeric_columns"] > 32
        or parsed_limits["unlabeled_total_min_numeric_columns"]
        > parsed_limits["unlabeled_total_max_numeric_columns"]
        or parsed_limits["unlabeled_total_max_gap_lines"] > parsed_limits["max_role_gap_lines"]
    ):
        raise _error("scoped-table structural limits exceed closed bounds")
    require_total = value["require_trailing_total_for_roles_as_columns"]
    if type(require_total) is not bool:
        raise _error("trailing-total requirement must be one exact bool")
    trailing = _aliases(value["trailing_total_aliases"], "trailing total", allow_empty=True)
    if require_total and not trailing:
        raise _error("required transposed trailing total needs declarative aliases")
    return {
        "continuation_aliases": _aliases(
            value["continuation_aliases"], "continuation", allow_empty=True
        ),
        "family_id": family_id,
        "format_version": SPEC_FORMAT_VERSION,
        "layout_modes": list(layouts),
        "limits": parsed_limits,
        "owner_aliases": _aliases(value["owner_aliases"], "owner"),
        "owner_component_groups": _component_groups(
            value.get("owner_component_groups", []), "owner"
        ),
        "require_trailing_total_for_roles_as_columns": require_total,
        "role_axis": roles,
        "scope_axis": scopes,
        "structural_reset_aliases": _aliases(
            value["structural_reset_aliases"], "structural reset", allow_empty=True
        ),
        "target_scope_id": target,
        "trailing_total_aliases": trailing,
    }


def _bbox(value: Any, *, page_width: int, page_height: int) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
        or value[2] > page_width
        or value[3] > page_height
    ):
        raise _error("scoped-table line bbox drifted")
    return list(value)


def _pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise _error("scoped-table graph requires one region-page sequence")
    pages: list[dict[str, Any]] = []
    sequences: list[int] = []
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_height",
            "page_sequence",
            "page_width",
        }:
            raise _error("scoped-table page fields drifted")
        page_sequence = _positive_int(raw_page["page_sequence"], "page sequence")
        page_width = _positive_int(raw_page["page_width"], "page width")
        page_height = _positive_int(raw_page["page_height"], "page height")
        if type(raw_page["lines"]) is not list or not raw_page["lines"]:
            raise _error("scoped-table page needs a nonempty line axis")
        lines: list[dict[str, Any]] = []
        source_indices: set[int] = set()
        for raw_line in raw_page["lines"]:
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("scoped-table line fields drifted")
            source_index = _nonnegative_int(raw_line["source_line_index"], "source line index")
            if source_index in source_indices:
                raise _error("scoped-table source line index repeats on one page")
            source_indices.add(source_index)
            source_text = raw_line["source_text"]
            if source_text is not None:
                source_text = _nfc(source_text, "bound source text", nonempty=False)
            text = _nfc(raw_line["vietocr_text"], "VietOCR surface", nonempty=False)
            box = _bbox(raw_line["bbox"], page_width=page_width, page_height=page_height)
            lines.append(
                {
                    "bbox": box,
                    "page_sequence": page_sequence,
                    "source_line_index": source_index,
                    "source_text": source_text,
                    "vietocr_text": text,
                }
            )
        pages.append(
            {
                "lines": lines,
                "page_height": page_height,
                "page_sequence": page_sequence,
                "page_width": page_width,
            }
        )
        sequences.append(page_sequence)
    if sequences != sorted(set(sequences)):
        raise _error("scoped-table page sequences must be unique and ordered")
    return pages


def _visual(lines: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        lines,
        key=lambda line: (
            line["bbox"][1],
            line["bbox"][0],
            line["bbox"][3],
            line["bbox"][2],
            line["source_line_index"],
        ),
    )


def _union(lines: Sequence[Mapping[str, Any]]) -> list[int]:
    return [
        min(line["bbox"][0] for line in lines),
        min(line["bbox"][1] for line in lines),
        max(line["bbox"][2] for line in lines),
        max(line["bbox"][3] for line in lines),
    ]


def _line_evidence(line: Mapping[str, Any]) -> dict[str, Any]:
    raw = line["vietocr_text"]
    return {
        "bbox": canonical_clone_v1(line["bbox"]),
        "page_sequence": line["page_sequence"],
        "source_line_index": line["source_line_index"],
        "source_text": line["source_text"],
        "vietocr_accentless_surface": _accentless_surface(raw),
        "vietocr_raw_nfc_surface": raw,
    }


def _semantic_prefix_uncached(value: str) -> str:
    return _INLINE_VALUE.sub("", value).strip()


@lru_cache(maxsize=_FEATURE_CACHE_MAXSIZE)
def _semantic_prefix_cached(value: str) -> str:
    return _semantic_prefix_uncached(value)


def _semantic_prefix(value: str) -> str:
    if len(value) > _FEATURE_CACHE_MAX_TEXT_CHARS:
        return _semantic_prefix_uncached(value)
    return _semantic_prefix_cached(value)


def _qgrams_uncached(value: str) -> frozenset[str]:
    padded = f"^{value}$"
    return frozenset(padded[index : index + 2] for index in range(len(padded) - 1))


@lru_cache(maxsize=_QGRAM_CACHE_MAXSIZE)
def _qgrams_cached(value: str) -> frozenset[str]:
    return _qgrams_uncached(value)


def _qgrams(value: str) -> frozenset[str]:
    if len(value) > _QGRAM_CACHE_MAX_TEXT_CHARS:
        return _qgrams_uncached(value)
    return _qgrams_cached(value)


def _compiled_alias_index(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Compile all semantic aliases once for exact and bounded-edit lookup."""

    entries: list[dict[str, Any]] = []

    def add(
        semantic_id: str,
        aliases: Sequence[str],
        *,
        category: str,
        phrase: bool,
        component_parent_semantic_id: str | None = None,
        component_source: str | None = None,
        scope_disposition: str | None = None,
    ) -> None:
        for alias in aliases:
            accentless = _accentless_surface(alias)
            material = {
                "alias_accented": _accented_surface(alias),
                "alias_accentless": accentless,
                "alias_raw_nfc": alias,
                "category": category,
                "phrase": phrase,
                "scope_disposition": scope_disposition,
                "semantic_id": semantic_id,
            }
            if component_parent_semantic_id is not None:
                material["component_parent_semantic_id"] = component_parent_semantic_id
            if component_source is not None:
                material["component_source"] = component_source
            entries.append(
                {
                    **material,
                    "alias_id": "astgv1:alias:" + canonical_json_sha256_v1(material),
                    "char_count": len(accentless),
                    "qgrams": _qgrams(accentless),
                    "token_count": len(accentless.split()),
                }
            )

    add("OWNER", spec["owner_aliases"], category="OWNER", phrase=True)
    for component in spec["owner_component_groups"]:
        add(
            component["component_id"],
            component["aliases"],
            category="OWNER_COMPONENT",
            component_parent_semantic_id="OWNER",
            phrase=True,
        )
    for role in spec["role_axis"]:
        add(role["role"], role["aliases"], category="ROLE", phrase=False)
    for scope in spec["scope_axis"]:
        add(
            scope["scope_id"],
            scope["aliases"],
            category="SCOPE",
            phrase=True,
            scope_disposition=scope["disposition"],
        )
        for component in scope["required_component_groups"]:
            add(
                component["component_id"],
                component["aliases"],
                category="SCOPE_COMPONENT",
                component_parent_semantic_id=scope["scope_id"],
                phrase=True,
                scope_disposition=scope["disposition"],
            )
        for component in scope["lane_component_groups"]:
            add(
                component["component_id"],
                component["aliases"],
                category="SCOPE_LANE_COMPONENT",
                component_parent_semantic_id=scope["scope_id"],
                component_source=component["source"],
                phrase=True,
                scope_disposition=scope["disposition"],
            )
    add("CONTINUATION", spec["continuation_aliases"], category="CONTINUATION", phrase=True)
    add(
        "STRUCTURAL_RESET",
        spec["structural_reset_aliases"],
        category="STRUCTURAL_RESET",
        phrase=True,
    )
    add(
        "TRAILING_TOTAL",
        spec["trailing_total_aliases"],
        category="TRAILING_TOTAL",
        phrase=False,
    )
    by_accented: dict[tuple[int, str], list[dict[str, Any]]] = {}
    by_accentless: dict[tuple[int, str], list[dict[str, Any]]] = {}
    edit_buckets: dict[tuple[int, int], list[dict[str, Any]]] = {}
    compact_candidates: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        by_accented.setdefault((entry["token_count"], entry["alias_accented"]), []).append(entry)
        by_accentless.setdefault((entry["token_count"], entry["alias_accentless"]), []).append(
            entry
        )
        edit_buckets.setdefault((entry["token_count"], entry["char_count"]), []).append(entry)
        compact = entry["alias_accentless"].replace(" ", "")
        if entry["token_count"] >= 2 and len(compact) >= 7:
            compact_candidates.setdefault(compact, []).append(entry)
    # A whitespace-only recovery is deliberately unavailable when removing
    # spaces makes two declarative aliases collide.  Text cannot decide which
    # semantic role owns that compact surface.
    compact_unique = {
        compact: candidates
        for compact, candidates in compact_candidates.items()
        if len(candidates) == 1
    }
    coarse_categories = {
        "OWNER",
        "OWNER_COMPONENT",
        "ROLE",
        "SCOPE",
        "SCOPE_COMPONENT",
        "SCOPE_LANE_COMPONENT",
        "STRUCTURAL_RESET",
    }
    coarse_entries = [entry for entry in entries if entry["category"] in coarse_categories]
    coarse_alias_offsets_by_token: dict[str, dict[str, set[int]]] = {}
    coarse_single_token_deletion_index: dict[str, set[str]] = {}
    coarse_single_token_observed_lengths: set[int] = set()
    for entry in coarse_entries:
        alias_tokens = entry["alias_accentless"].split()
        for offset, token in enumerate(alias_tokens):
            coarse_alias_offsets_by_token.setdefault(token, {}).setdefault(
                entry["alias_id"], set()
            ).add(offset)
        if len(alias_tokens) == 1:
            token = alias_tokens[0]
            coarse_single_token_observed_lengths.update(
                range(max(1, len(token) - 1), len(token) + 2)
            )
            for signature in _deletion_signatures(token):
                coarse_single_token_deletion_index.setdefault(signature, set()).add(
                    entry["alias_id"]
                )
    compact_two_token_alias_ids = {
        compact: frozenset(entry["alias_id"] for entry in candidates)
        for compact, candidates in compact_unique.items()
        if candidates[0]["token_count"] == 2
    }
    return {
        "by_accented": by_accented,
        "by_accentless": by_accentless,
        "edit_buckets": edit_buckets,
        "compact_unique": compact_unique,
        "compact_alias_ids": frozenset(
            entry["alias_id"] for candidates in compact_unique.values() for entry in candidates
        ),
        "coarse_alias_offsets_by_token": {
            token: {alias_id: frozenset(offsets) for alias_id, offsets in by_alias_id.items()}
            for token, by_alias_id in coarse_alias_offsets_by_token.items()
        },
        "coarse_compact_two_token_alias_ids": compact_two_token_alias_ids,
        "coarse_entries_by_alias_id": {entry["alias_id"]: entry for entry in coarse_entries},
        "coarse_single_token_deletion_index": {
            signature: frozenset(alias_ids)
            for signature, alias_ids in coarse_single_token_deletion_index.items()
        },
        "coarse_single_token_observed_lengths": frozenset(coarse_single_token_observed_lengths),
        "entries": entries,
        "maximum_alias_token_count": max(entry["token_count"] for entry in entries),
        # The values are read-only match proposals tied to this exact compiled
        # spec.  Keeping the cache build-local prevents one family spec from
        # lending semantic entries to another while bounding worker memory.
        "surface_cache": OrderedDict(),
        "surface_cache_hit_count": 0,
        "surface_cache_miss_count": 0,
        "token_counts": sorted({entry["token_count"] for entry in entries}),
        "maximum_wrap_lines": spec["limits"]["max_wrap_lines"],
        "owner_component_ids": frozenset(
            component["component_id"] for component in spec["owner_component_groups"]
        ),
        "scope_component_quorums": tuple(
            {
                "lane": frozenset(
                    component["component_id"] for component in scope["lane_component_groups"]
                ),
                "required": frozenset(
                    component["component_id"] for component in scope["required_component_groups"]
                ),
                "scope_id": scope["scope_id"],
            }
            for scope in spec["scope_axis"]
        ),
    }


def _deletion_signatures(value: str) -> frozenset[str]:
    """Return a compact superset key for one insertion/deletion/substitution."""

    return frozenset({value, *(value[:index] + value[index + 1 :] for index in range(len(value)))})


def _counter_covers(available: Counter[str], required: Counter[str]) -> bool:
    return all(available[token] >= count for token, count in required.items())


def _edit_distance_at_most_one(left: str, right: str) -> bool:
    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) > len(right):
        left, right = right, left
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right, strict=True)) <= 1
    left_index = 0
    right_index = 0
    differences = 0
    while left_index < len(left) and right_index < len(right):
        if left[left_index] == right[right_index]:
            left_index += 1
        else:
            differences += 1
            if differences > 1:
                return False
        right_index += 1
    return True


def _coarse_alias_possible(
    entry: Mapping[str, Any],
    token_counts: Counter[str],
    tokens_by_length: Mapping[int, set[str]],
    *,
    compact_alias_ids: frozenset[str],
) -> bool:
    """Overinclude every exact, one-edit, or one-whitespace alias channel."""

    alias_tokens = entry["alias_accentless"].split()
    required = Counter(alias_tokens)
    if _counter_covers(token_counts, required):
        return True

    # The bounded edit matcher requires the same token count.  Therefore one
    # character edit can affect at most one token; every other token remains
    # available verbatim.  The loose token q-gram gate deliberately admits
    # false positives but cannot reject a true one-edit span.
    for alias_token in alias_tokens:
        remainder = Counter(alias_tokens)
        remainder[alias_token] -= 1
        if remainder[alias_token] == 0:
            del remainder[alias_token]
        if not _counter_covers(token_counts, remainder):
            continue
        for length in range(max(1, len(alias_token) - 1), len(alias_token) + 2):
            if any(
                len(_qgrams(candidate) ^ _qgrams(alias_token)) <= 6
                and _edit_distance_at_most_one(candidate, alias_token)
                for candidate in tokens_by_length.get(length, set())
            ):
                return True

    if entry["alias_id"] not in compact_alias_ids:
        return False
    # The compact matcher changes exactly one whitespace: either two adjacent
    # alias tokens fuse, or one alias token splits.  Check those two channels
    # explicitly against the page multiset without constructing visual paths.
    for ordinal in range(len(alias_tokens) - 1):
        fused = alias_tokens[ordinal] + alias_tokens[ordinal + 1]
        compact_required = Counter(alias_tokens[:ordinal] + alias_tokens[ordinal + 2 :])
        compact_required[fused] += 1
        if _counter_covers(token_counts, compact_required):
            return True
    for ordinal, alias_token in enumerate(alias_tokens):
        for split in range(1, len(alias_token)):
            compact_required = Counter(alias_tokens[:ordinal] + alias_tokens[ordinal + 1 :])
            compact_required[alias_token[:split]] += 1
            compact_required[alias_token[split:]] += 1
            if _counter_covers(token_counts, compact_required):
                return True
    return False


def _coarse_ordered_alias_possible(
    tokens: Sequence[str],
    entry: Mapping[str, Any],
    *,
    candidate_starts: set[int],
    compact_alias_ids: frozenset[str],
) -> bool:
    """Apply exact necessary text channels without the full matcher records."""

    alias = entry["alias_accentless"]
    alias_token_count = entry["token_count"]
    raw_starts = candidate_starts
    exact_starts = {start for start in raw_starts if 0 <= start <= len(tokens) - alias_token_count}
    for start in exact_starts:
        candidate = " ".join(tokens[start : start + alias_token_count])
        if _edit_distance_at_most_one(candidate, alias):
            return True
    if entry["alias_id"] not in compact_alias_ids:
        return False
    compact = alias.replace(" ", "")
    for observed_token_count in (alias_token_count - 1, alias_token_count + 1):
        if observed_token_count < 1:
            continue
        compact_starts = {
            start + shift
            for start in raw_starts
            for shift in (-1, 0, 1)
            if 0 <= start + shift <= len(tokens) - observed_token_count
        }
        for start in compact_starts:
            if "".join(tokens[start : start + observed_token_count]) == compact:
                return True
    return False


def _coarse_token_alias_index(
    tokens: Sequence[str], alias_index: Mapping[str, Any]
) -> dict[str, dict[str, frozenset[int]]]:
    """Map observed tokens to the only aliases a bounded channel can reach."""

    result: dict[str, dict[str, frozenset[int]]] = {}
    for token in set(tokens):
        alias_offsets = {
            alias_id: set(offsets)
            for alias_id, offsets in alias_index["coarse_alias_offsets_by_token"]
            .get(token, {})
            .items()
        }
        for alias_id in alias_index["coarse_compact_two_token_alias_ids"].get(token, ()):
            alias_offsets.setdefault(alias_id, set()).add(0)
        if len(token) in alias_index["coarse_single_token_observed_lengths"]:
            for signature in _deletion_signatures(token):
                for alias_id in alias_index["coarse_single_token_deletion_index"].get(
                    signature, ()
                ):
                    alias_offsets.setdefault(alias_id, set()).add(0)
        result[token] = {
            alias_id: frozenset(offsets) for alias_id, offsets in alias_offsets.items()
        }
    return result


def _coarse_possible_evidence(
    token_counts: Counter[str] | None,
    token_alias_ids: Mapping[str, Mapping[str, frozenset[int]]],
    alias_index: Mapping[str, Any],
    *,
    eligible_categories: frozenset[str] | None = None,
    ordered_tokens: Sequence[str] | None = None,
) -> set[tuple[str, str]]:
    if ordered_tokens is not None:
        candidate_alias_starts: dict[str, set[int]] = {}
        for position, token in enumerate(ordered_tokens):
            for alias_id, offsets in token_alias_ids[token].items():
                if (
                    eligible_categories is not None
                    and alias_index["coarse_entries_by_alias_id"][alias_id]["category"]
                    not in eligible_categories
                ):
                    continue
                candidate_alias_starts.setdefault(alias_id, set()).update(
                    position - offset for offset in offsets
                )
        return {
            (entry["category"], entry["semantic_id"])
            for alias_id, starts in candidate_alias_starts.items()
            for entry in [alias_index["coarse_entries_by_alias_id"][alias_id]]
            if _coarse_ordered_alias_possible(
                ordered_tokens,
                entry,
                candidate_starts=starts,
                compact_alias_ids=alias_index["compact_alias_ids"],
            )
        }
    if token_counts is None:
        raise AssertionError("unordered coarse evidence requires token counts")
    candidate_alias_ids = {
        alias_id for token in token_counts for alias_id in token_alias_ids[token]
    }
    if not candidate_alias_ids:
        return set()
    tokens_by_length: dict[int, set[str]] = {}
    for token in token_counts:
        tokens_by_length.setdefault(len(token), set()).add(token)
    return {
        (entry["category"], entry["semantic_id"])
        for alias_id in sorted(candidate_alias_ids)
        for entry in [alias_index["coarse_entries_by_alias_id"][alias_id]]
        if _coarse_alias_possible(
            entry,
            token_counts,
            tokens_by_length,
            compact_alias_ids=alias_index["compact_alias_ids"],
        )
    }


def _coarse_candidate_possible(
    evidence: set[tuple[str, str]],
    alias_index: Mapping[str, Any],
    *,
    owner_components_complete: bool,
    required_scope_ids: set[str],
) -> bool:
    owner_possible = ("OWNER", "OWNER") in evidence or owner_components_complete
    distinct_role_ids = {semantic_id for category, semantic_id in evidence if category == "ROLE"}
    direct_scope_ids = {semantic_id for category, semantic_id in evidence if category == "SCOPE"}
    lane_component_ids = {
        semantic_id for category, semantic_id in evidence if category == "SCOPE_LANE_COMPONENT"
    }
    lane_scope_ids = {
        quorum["scope_id"]
        for quorum in alias_index["scope_component_quorums"]
        if quorum["lane"] and quorum["lane"].issubset(lane_component_ids)
    }
    scope_possible = bool(direct_scope_ids | required_scope_ids | lane_scope_ids)
    return (
        owner_possible
        and bool(distinct_role_ids)
        and (scope_possible or len(distinct_role_ids) >= 2)
    )


def _coarse_page_category_index(
    page: Mapping[str, Any], alias_index: Mapping[str, Any]
) -> dict[str, Any]:
    """Use a page quorum, then prove every alias inside a local wrap band."""

    line_tokens = {
        line["source_line_index"]: tuple(_accentless_surface(line["vietocr_text"]).split())
        for line in page["lines"]
    }
    page_tokens = [token for tokens in line_tokens.values() for token in tokens]
    token_alias_ids = _coarse_token_alias_index(page_tokens, alias_index)
    page_evidence = _coarse_possible_evidence(Counter(page_tokens), token_alias_ids, alias_index)
    page_owner_components = {
        semantic_id for category, semantic_id in page_evidence if category == "OWNER_COMPONENT"
    }
    page_required_scope_ids = {
        quorum["scope_id"]
        for quorum in alias_index["scope_component_quorums"]
        if quorum["required"]
        and quorum["required"].issubset(
            {
                semantic_id
                for category, semantic_id in page_evidence
                if category == "SCOPE_COMPONENT"
            }
        )
    }
    page_candidate = _coarse_candidate_possible(
        page_evidence,
        alias_index,
        owner_components_complete=bool(alias_index["owner_component_ids"])
        and alias_index["owner_component_ids"].issubset(page_owner_components),
        required_scope_ids=page_required_scope_ids,
    )
    if not page_candidate:
        return {
            "candidate_possible": False,
            "reset_possible": ("STRUCTURAL_RESET", "STRUCTURAL_RESET") in page_evidence,
            "window_band_count": 0,
        }

    windows = _windows(page, alias_index["maximum_wrap_lines"])
    owner_categories = frozenset({"OWNER", "OWNER_COMPONENT"})
    ordered_tokens_by_ordinal: dict[int, list[str]] = {}
    owner_evidence: set[tuple[str, str]] = set()
    owner_components_complete = False
    owner_scan_count = 0
    for ordinal, block in enumerate(windows):
        owner_scan_count = ordinal + 1
        ordered_tokens = ordered_tokens_by_ordinal.get(ordinal)
        if ordered_tokens is None:
            ordered_tokens = [
                token
                # ``_windows`` starts in visual order and every edge strictly
                # increases center-y, so a path is already provider-order free.
                for line in block
                for token in line_tokens[line["source_line_index"]]
            ]
            ordered_tokens_by_ordinal[ordinal] = ordered_tokens
        band_owner_evidence = _coarse_possible_evidence(
            None,
            token_alias_ids,
            alias_index,
            eligible_categories=owner_categories,
            ordered_tokens=ordered_tokens,
        )
        band_owner_components = {
            semantic_id
            for category, semantic_id in band_owner_evidence
            if category == "OWNER_COMPONENT"
        }
        owner_components_complete = bool(alias_index["owner_component_ids"]) and alias_index[
            "owner_component_ids"
        ].issubset(band_owner_components)
        if ("OWNER", "OWNER") in band_owner_evidence or owner_components_complete:
            owner_evidence = band_owner_evidence
            break
    else:
        return {
            "candidate_possible": False,
            "reset_possible": ("STRUCTURAL_RESET", "STRUCTURAL_RESET") in page_evidence,
            "window_band_count": len(windows),
        }

    # Owner is only a page-level necessary condition here.  Collect all other
    # semantic evidence independently of visual order: the authoritative
    # geometry decides whether the proved axes form a physical table.
    evidence = set(owner_evidence)
    required_scope_ids: set[str] = set()
    for ordinal, block in enumerate(windows):
        ordered_tokens = ordered_tokens_by_ordinal.get(ordinal)
        if ordered_tokens is None:
            ordered_tokens = [
                token for line in block for token in line_tokens[line["source_line_index"]]
            ]
        band_evidence = _coarse_possible_evidence(
            None,
            token_alias_ids,
            alias_index,
            ordered_tokens=ordered_tokens,
        )
        evidence.update(band_evidence)
        band_scope_components = {
            semantic_id for category, semantic_id in band_evidence if category == "SCOPE_COMPONENT"
        }
        required_scope_ids.update(
            quorum["scope_id"]
            for quorum in alias_index["scope_component_quorums"]
            if quorum["required"] and quorum["required"].issubset(band_scope_components)
        )
        if _coarse_candidate_possible(
            evidence,
            alias_index,
            owner_components_complete=owner_components_complete,
            required_scope_ids=required_scope_ids,
        ):
            return {
                "candidate_possible": True,
                "reset_possible": ("STRUCTURAL_RESET", "STRUCTURAL_RESET") in page_evidence,
                "window_band_count": max(owner_scan_count, ordinal + 1),
            }
    return {
        "candidate_possible": False,
        "reset_possible": ("STRUCTURAL_RESET", "STRUCTURAL_RESET") in page_evidence,
        "window_band_count": len(windows),
    }


def _candidate_match(
    entry: Mapping[str, Any],
    *,
    candidate: str,
    edit_bound: int,
    line_count: int,
    match_kind: str,
    window_token_count: int,
) -> dict[str, Any]:
    candidate_qgrams = _qgrams(candidate)
    alias_qgrams = entry["qgrams"]
    return {
        "alias_id": entry["alias_id"],
        "alias_accentless": entry["alias_accentless"],
        "alias_raw_nfc": entry["alias_raw_nfc"],
        "candidate_feature_vector": {
            "alias_char_count": entry["char_count"],
            "alias_token_count": entry["token_count"],
            "candidate_char_count": len(candidate),
            "candidate_token_count": len(candidate.split()),
            "length_delta": abs(len(candidate) - entry["char_count"]),
            "qgram_intersection_count": len(candidate_qgrams & alias_qgrams),
            "qgram_union_count": len(candidate_qgrams | alias_qgrams),
            "window_token_count": window_token_count,
        },
        "context_gates": {
            "complete_geometry_required": True,
            "phrase_window_allowed": entry["phrase"],
            "source_window_line_count": line_count,
        },
        "edit_bound": edit_bound,
        "match_kind": match_kind,
        "text_authority": "SHORTLIST_ONLY_REQUIRES_COMPLETE_GEOMETRY",
    }


def _required_component_group_match(
    matches: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
    groups: Sequence[Mapping[str, Any]],
    *,
    line_count: int,
    parent_semantic_id: str,
) -> dict[str, Any] | None:
    if not groups:
        return None
    selected = []
    for group in groups:
        candidates = [
            (entry, match)
            for entry, match in matches
            if entry.get("component_parent_semantic_id") == parent_semantic_id
            and entry["semantic_id"] == group["component_id"]
        ]
        if not candidates:
            return None
        entry, match = candidates[0]
        selected.append(
            {
                "component_id": group["component_id"],
                **(
                    {"component_source": entry["component_source"]}
                    if type(entry.get("component_source")) is str
                    else {}
                ),
                "match": canonical_clone_v1(match),
                "shared_alias_id": entry["alias_id"],
            }
        )
    material = {
        "component_matches": selected,
        "parent_semantic_id": parent_semantic_id,
    }
    aliases = [item["match"]["alias_accentless"] for item in selected]
    return {
        "alias_accentless": " | ".join(aliases),
        "alias_id": "astgv1:component-composition:" + canonical_json_sha256_v1(material),
        "alias_raw_nfc": " | ".join(item["match"]["alias_raw_nfc"] for item in selected),
        "candidate_feature_vector": {
            "component_count": len(selected),
            "component_ids": [item["component_id"] for item in selected],
            "maximum_component_edit_bound": max(item["match"]["edit_bound"] for item in selected),
            "source_window_line_count": line_count,
        },
        "component_matches": selected,
        "context_gates": {
            "all_required_component_groups_matched": True,
            "complete_geometry_required": True,
            "source_window_line_count": line_count,
        },
        "edit_bound": max(item["match"]["edit_bound"] for item in selected),
        "match_kind": "DECLARATIVE_REQUIRED_COMPONENT_GROUPS_IN_BOUNDED_VISUAL_WINDOW",
        "text_authority": "SHORTLIST_ONLY_REQUIRES_COMPLETE_GEOMETRY",
    }


def _surface_matches(
    surface: str, index: Mapping[str, Any], *, line_count: int
) -> tuple[list[tuple[Mapping[str, Any], dict[str, Any]]], int]:
    """Look up one visual window without scanning every alias."""

    cache_key = (surface, line_count)
    cache = index["surface_cache"]
    cached = cache.pop(cache_key, None)
    if cached is not None:
        cache[cache_key] = cached
        index["surface_cache_hit_count"] += 1
        return list(cached[0]), cached[1]
    index["surface_cache_miss_count"] += 1
    candidate = _semantic_prefix(surface)
    accented_tokens = _accented_surface(candidate).split()
    accentless_tokens = _accentless_surface(candidate).split()
    if len(accented_tokens) != len(accentless_tokens):
        result: list[tuple[Mapping[str, Any], dict[str, Any]]] = []
        cache[cache_key] = (tuple(result), 0)
        if len(cache) > _SURFACE_CACHE_MAXSIZE:
            cache.popitem(last=False)
        return result, 0
    selected: dict[str, tuple[int, Mapping[str, Any], dict[str, Any]]] = {}
    approximate_comparisons = 0
    for token_count in index["token_counts"]:
        if token_count > len(accentless_tokens):
            continue
        for start in range(len(accentless_tokens) - token_count + 1):
            stop = start + token_count
            accentless_span = " ".join(accentless_tokens[start:stop])
            accented_span = " ".join(accented_tokens[start:stop])
            whole = start == 0 and stop == len(accentless_tokens)
            exact_ids: set[str] = set()
            for entry in index["by_accented"].get((token_count, accented_span), []):
                if not whole and not entry["phrase"]:
                    continue
                kind = (
                    "EXACT_ACCENTED_NORMALIZED_ALIAS"
                    if whole
                    else "ACCENTED_NORMALIZED_PHRASE_IN_WRAPPED_OR_MERGED_SURFACE"
                )
                match = _candidate_match(
                    entry,
                    candidate=accentless_span,
                    edit_bound=0,
                    line_count=line_count,
                    match_kind=kind,
                    window_token_count=len(accentless_tokens),
                )
                selected[entry["alias_id"]] = (0 if whole else 1, entry, match)
                exact_ids.add(entry["alias_id"])
            for entry in index["by_accentless"].get((token_count, accentless_span), []):
                if entry["alias_id"] in exact_ids or (not whole and not entry["phrase"]):
                    continue
                kind = (
                    "EXACT_ACCENTLESS_ALIAS"
                    if whole
                    else "ACCENTLESS_PHRASE_IN_WRAPPED_OR_MERGED_SURFACE"
                )
                match = _candidate_match(
                    entry,
                    candidate=accentless_span,
                    edit_bound=0,
                    line_count=line_count,
                    match_kind=kind,
                    window_token_count=len(accentless_tokens),
                )
                selected[entry["alias_id"]] = (2 if whole else 3, entry, match)
                exact_ids.add(entry["alias_id"])
            span_qgrams = _qgrams(accentless_span)
            for length in range(max(1, len(accentless_span) - 1), len(accentless_span) + 2):
                for entry in index["edit_buckets"].get((token_count, length), []):
                    if entry["alias_id"] in exact_ids or (not whole and not entry["phrase"]):
                        continue
                    # One insertion/deletion/substitution can change at most a
                    # bounded neighborhood of padded character bigrams.
                    if len(span_qgrams ^ entry["qgrams"]) > 6:
                        continue
                    approximate_comparisons += 1
                    if (
                        match_vietnamese_anchor_alias_v1(accentless_span, [entry["alias_raw_nfc"]])
                        != "ONE_EDIT_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY"
                    ):
                        continue
                    match = _candidate_match(
                        entry,
                        candidate=accentless_span,
                        edit_bound=1,
                        line_count=line_count,
                        match_kind="ONE_EDIT_ACCENTLESS_TEXT_SHORTLIST",
                        window_token_count=len(accentless_tokens),
                    )
                    selected.setdefault(entry["alias_id"], (4, entry, match))
    # Exact compact lookup is a bounded whitespace channel, not general edit
    # distance.  It recovers one fused/split token (for example ``chovay``)
    # only when the compact form names one unique long multiword alias.
    maximum_span = min(len(accentless_tokens), index["maximum_alias_token_count"] + 1)
    for start in range(len(accentless_tokens)):
        for stop in range(start + 1, min(len(accentless_tokens), start + maximum_span) + 1):
            accentless_span = " ".join(accentless_tokens[start:stop])
            candidates = index["compact_unique"].get(accentless_span.replace(" ", ""), [])
            if not candidates:
                continue
            entry = candidates[0]
            whole = start == 0 and stop == len(accentless_tokens)
            if (
                entry["alias_id"] in selected
                or (not whole and not entry["phrase"])
                or abs(entry["token_count"] - len(accentless_span.split())) != 1
                or abs(entry["alias_accentless"].count(" ") - accentless_span.count(" ")) != 1
            ):
                continue
            match = _candidate_match(
                entry,
                candidate=accentless_span,
                edit_bound=1,
                line_count=line_count,
                match_kind="EXACT_ONE_WHITESPACE_FUSION_OR_SPLIT_ALIAS",
                window_token_count=len(accentless_tokens),
            )
            selected[entry["alias_id"]] = (4, entry, match)
    result = [
        (entry, match)
        for _rank, entry, match in sorted(
            selected.values(),
            key=lambda item: (item[0], -item[1]["char_count"], item[1]["alias_id"]),
        )
    ]
    cache[cache_key] = (tuple(result), approximate_comparisons)
    if len(cache) > _SURFACE_CACHE_MAXSIZE:
        cache.popitem(last=False)
    return result, approximate_comparisons


def _can_wrap(left: Mapping[str, Any], right: Mapping[str, Any], *, scale: float) -> bool:
    left_box = left["bbox"]
    right_box = right["bbox"]
    left_center_y = (left_box[1] + left_box[3]) / 2
    right_center_y = (right_box[1] + right_box[3]) / 2
    if right_center_y - left_center_y < scale * 0.28:
        return False
    if right_box[1] - left_box[3] > scale * 1.55:
        return False
    overlap = max(0, min(left_box[2], right_box[2]) - max(left_box[0], right_box[0]))
    minimum_width = max(1, min(left_box[2] - left_box[0], right_box[2] - right_box[0]))
    return overlap / minimum_width >= 0.18 or abs(left_box[0] - right_box[0]) <= scale * 2.2


def _wrap_adjacency(
    page: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], dict[int, tuple[Mapping[str, Any], ...]]]:
    """Build the exact bounded forward geometry shared by gate and matcher."""

    visual = [line for line in _visual(page["lines"]) if line["vietocr_text"].strip()]
    scale = median_text_height_v1(visual)
    # Followers depend only on the last line, not on the path used to reach
    # it: every edge strictly increases center-y, so a prior path member can
    # never be a follower again.  The former DFS rescanned every page line for
    # every emitted window (O(window_count * line_count)).  Precompute the
    # exact same ordered, six-wide adjacency once.  ``_can_wrap`` proves that
    # a follower starting below this y fence cannot qualify, so bisecting the
    # visual y-order is an exact bounded sweep rather than a loose heuristic.
    tops = [line["bbox"][1] for line in visual]
    followers_by_source_index: dict[int, tuple[Mapping[str, Any], ...]] = {}
    for left in visual:
        left_center_y = (left["bbox"][1] + left["bbox"][3]) / 2
        upper = bisect_right(tops, left["bbox"][3] + scale * 1.55)
        followers = [
            candidate
            for candidate in visual[:upper]
            if (candidate["bbox"][1] + candidate["bbox"][3]) / 2 > left_center_y
            and _can_wrap(left, candidate, scale=scale)
        ]
        followers.sort(
            key=lambda item: (
                item["bbox"][1] - left["bbox"][3],
                abs(item["bbox"][0] - left["bbox"][0]),
                item["bbox"][0],
            )
        )
        followers_by_source_index[left["source_line_index"]] = tuple(followers[:6])
    return visual, followers_by_source_index


def _windows(page: Mapping[str, Any], max_lines: int) -> list[list[Mapping[str, Any]]]:
    visual, followers_by_source_index = _wrap_adjacency(page)
    result: list[list[Mapping[str, Any]]] = []
    for line in visual:
        stack = [[line]]
        while stack:
            block = stack.pop()
            result.append(block)
            if len(block) >= max_lines:
                continue
            last = block[-1]
            # Branch over the same small geometric neighborhood and preserve
            # the prior stack/reversal order byte-for-byte.
            followers = followers_by_source_index[last["source_line_index"]]
            stack.extend([*block, follower] for follower in reversed(followers))
    return result


def _prepare_semantic_windows(
    page: Mapping[str, Any],
    spec: Mapping[str, Any],
    alias_index: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one content-feature pass before any accounting geometry.

    This pass retains the exhaustive match/count semantics, but records only
    immutable line references and text proposals.  A page cannot produce a
    physical segment or partial fragment unless it has both local owner and
    role evidence; scope is recorded separately so owner+role branchless pages
    remain a fail-closed rescue candidate rather than an absence claim.
    """

    prepared = []
    categories: set[str] = set()
    distinct_role_ids: set[str] = set()
    approximate_comparisons = 0
    windows = _windows(page, spec["limits"]["max_wrap_lines"])
    for block in windows:
        ordered = _visual(block)
        surface = " ".join(line["vietocr_text"].strip() for line in ordered).strip()
        matches, comparisons = _surface_matches(
            surface,
            alias_index,
            line_count=len(block),
        )
        approximate_comparisons += comparisons
        categories.update(entry["category"] for entry, _match in matches)
        distinct_role_ids.update(
            entry["semantic_id"] for entry, _match in matches if entry["category"] == "ROLE"
        )
        prepared.append((block, matches, comparisons))
    owner_possible = bool(categories & {"OWNER", "OWNER_COMPONENT"})
    role_possible = "ROLE" in categories
    scope_possible = bool(
        categories
        & {
            "SCOPE",
            "SCOPE_COMPONENT",
            "SCOPE_LANE_COMPONENT",
        }
    )
    return {
        "approximate_alias_comparison_count": approximate_comparisons,
        "has_reset": "STRUCTURAL_RESET" in categories,
        "owner_possible": owner_possible,
        "primary_candidate": owner_possible and role_possible and scope_possible,
        "rescue_candidate": (owner_possible and len(distinct_role_ids) >= 2 and not scope_possible),
        "role_possible": role_possible,
        "scope_possible": scope_possible,
        "visual_window_count": len(windows),
        "windows": prepared,
    }


def _empty_semantic_matches(spec: Mapping[str, Any], prepared: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact unused-page shape without invoking geometry."""

    return {
        "continuations": [],
        "matcher_metrics": {
            "approximate_alias_comparison_count": prepared["approximate_alias_comparison_count"],
            "visual_window_count": prepared["visual_window_count"],
        },
        "owners": [],
        "resets": [],
        "roles": {item["role"]: [] for item in spec["role_axis"]},
        "scopes": [],
        "trailing_totals": [],
    }


def _match_record(
    lines: Sequence[Mapping[str, Any]], match: Mapping[str, Any], semantic_id: str
) -> dict[str, Any]:
    ordered = _visual(lines)
    surface = " ".join(line["vietocr_text"].strip() for line in ordered).strip()
    material = {
        "bbox": _union(ordered),
        "line_evidence": [_line_evidence(line) for line in ordered],
        "match": canonical_clone_v1(match),
        "page_sequence": ordered[0]["page_sequence"],
        "semantic_id": semantic_id,
        "source_line_indices_in_visual_order": [line["source_line_index"] for line in ordered],
        "surface_accentless": _accentless_surface(surface),
        "surface_raw_nfc": surface,
    }
    return {**material, "match_id": "astgv1:match:" + canonical_json_sha256_v1(material)}


def _deduplicate_matches(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rank = {
        "EXACT_ACCENTED_NORMALIZED_ALIAS": 0,
        "ACCENTED_NORMALIZED_PHRASE_IN_WRAPPED_OR_MERGED_SURFACE": 1,
        "EXACT_ACCENTLESS_ALIAS": 2,
        "ACCENTLESS_PHRASE_IN_WRAPPED_OR_MERGED_SURFACE": 3,
        "ONE_EDIT_ACCENTLESS_TEXT_SHORTLIST": 4,
        "EXACT_ONE_WHITESPACE_FUSION_OR_SPLIT_ALIAS": 4,
        "DECLARATIVE_REQUIRED_COMPONENT_GROUPS_IN_BOUNDED_VISUAL_WINDOW": 5,
    }
    selected: dict[tuple[int, str, int, int, int, int], Mapping[str, Any]] = {}
    for record in records:
        key = (
            record["page_sequence"],
            record["semantic_id"],
            record["bbox"][1],
            record["bbox"][3],
            record["bbox"][0],
            record["bbox"][2],
        )
        prior = selected.get(key)
        current_key = (
            rank[record["match"]["match_kind"]],
            -len(record["match"]["alias_accentless"]),
            len(record["source_line_indices_in_visual_order"]),
            record["bbox"][0],
        )
        if prior is None:
            selected[key] = record
            continue
        prior_key = (
            rank[prior["match"]["match_kind"]],
            -len(prior["match"]["alias_accentless"]),
            len(prior["source_line_indices_in_visual_order"]),
            prior["bbox"][0],
        )
        if current_key < prior_key:
            selected[key] = record
    return [
        canonical_clone_v1(item)
        for item in sorted(
            selected.values(),
            key=lambda item: (
                item["page_sequence"],
                item["bbox"][1],
                item["bbox"][0],
                item["semantic_id"],
            ),
        )
    ]


def _collapse_axis_matches(
    records: Sequence[Mapping[str, Any]], *, scale: float
) -> list[dict[str, Any]]:
    """Collapse redundant wrapped windows which describe one visual label."""

    selected: list[dict[str, Any]] = []
    for record in sorted(
        records,
        key=lambda item: (
            len(item["source_line_indices_in_visual_order"]),
            -len(item["match"]["alias_accentless"]),
            item["bbox"][1],
        ),
    ):
        if any(
            record["semantic_id"] == prior["semantic_id"]
            and abs(_center_x(record) - _center_x(prior)) <= scale
            and max(record["bbox"][1], prior["bbox"][1])
            <= min(record["bbox"][3], prior["bbox"][3]) + scale * 1.2
            for prior in selected
        ):
            continue
        selected.append(canonical_clone_v1(record))
    return sorted(
        selected,
        key=lambda item: (item["page_sequence"], item["bbox"][1], item["bbox"][0]),
    )


def _minimal_line_axis_matches(
    records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Discard phrase matches padded with unrelated neighboring lines."""

    return [
        canonical_clone_v1(record)
        for record in records
        if not any(
            other["semantic_id"] == record["semantic_id"]
            and set(other["source_line_indices_in_visual_order"]).issubset(
                record["source_line_indices_in_visual_order"]
            )
            and set(other["source_line_indices_in_visual_order"])
            != set(record["source_line_indices_in_visual_order"])
            for other in records
        )
    ]


def _row_has_visible_accounting_value(
    page: Mapping[str, Any],
    label: Mapping[str, Any],
    *,
    later_wrapped_lines: Sequence[Mapping[str, Any]],
    visible_value_lines: Sequence[Mapping[str, Any]] | None = None,
) -> bool:
    """Prove that a value closes ``label`` rather than its continuation."""

    candidates = (
        visible_value_lines
        if visible_value_lines is not None
        else [line for line in page["lines"] if _is_value(line)]
    )
    for line in candidates:
        if line["bbox"][0] < label["bbox"][2]:
            continue
        label_overlap = _overlap_ppm(line["bbox"], label["bbox"])
        later_overlap = max(
            (
                _overlap_ppm(line["bbox"], later["bbox"])
                for later in later_wrapped_lines
                if not _is_value(later)
            ),
            default=0,
        )
        if label_overlap >= 250_000 and label_overlap > later_overlap:
            return True
    return False


def _semantic_matches(
    page: Mapping[str, Any],
    spec: Mapping[str, Any],
    alias_index: Mapping[str, Any],
    *,
    prepared: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    prepared = _prepare_semantic_windows(page, spec, alias_index) if prepared is None else prepared
    scale = median_text_height_v1(page["lines"])
    by_category: dict[str, list[dict[str, Any]]] = {
        "CONTINUATION": [],
        "OWNER": [],
        "ROLE": [],
        "STRUCTURAL_RESET": [],
        "TRAILING_TOTAL": [],
    }
    raw_scopes: list[dict[str, Any]] = []
    approximate_comparisons = 0
    visible_value_lines = [line for line in page["lines"] if _is_value(line)]
    for block, matches, comparisons in prepared["windows"]:
        approximate_comparisons += comparisons
        scope_matches = [(entry, match) for entry, match in matches if entry["category"] == "SCOPE"]
        for scope in spec["scope_axis"]:
            component_match = _required_component_group_match(
                [item for item in matches if item[0]["category"] == "SCOPE_COMPONENT"],
                scope["required_component_groups"],
                line_count=len(block),
                parent_semantic_id=scope["scope_id"],
            )
            if component_match is not None:
                scope_matches.append(
                    (
                        {
                            "scope_disposition": scope["disposition"],
                            "semantic_id": scope["scope_id"],
                        },
                        component_match,
                    )
                )
        ordered_block = _visual(block)
        if len(ordered_block) > 1 and any(
            _row_has_visible_accounting_value(
                page,
                line,
                later_wrapped_lines=ordered_block[index + 1 :],
                visible_value_lines=visible_value_lines,
            )
            for index, line in enumerate(ordered_block[:-1])
        ):
            # Two vertically adjacent body rows are not one wrapped population
            # label when the earlier row already closes with visible values.
            scope_matches = []
        # Any visibly broader/mixed phrase is terminal.  A target phrase
        # nested inside that same merged surface may not narrow it.
        if scope_matches:
            scope_entry, scope_match = min(
                scope_matches,
                key=lambda item: (
                    0
                    if item[0]["scope_disposition"] == "HARD_VETO_MIXED"
                    else 1
                    if item[0]["scope_disposition"] == "TARGET"
                    else 2,
                    -len(item[1]["alias_accentless"]),
                ),
            )
            record = _match_record(block, scope_match, scope_entry["semantic_id"])
            record.update(
                {
                    "scope_disposition": scope_entry["scope_disposition"],
                    "scope_id": scope_entry["semantic_id"],
                }
            )
            raw_scopes.append(record)
        owner_component_match = _required_component_group_match(
            [item for item in matches if item[0]["category"] == "OWNER_COMPONENT"],
            spec["owner_component_groups"],
            line_count=len(block),
            parent_semantic_id="OWNER",
        )
        if owner_component_match is not None:
            by_category["OWNER"].append(_match_record(block, owner_component_match, "OWNER"))
        for entry, match in matches:
            if entry["category"] in {
                "OWNER_COMPONENT",
                "SCOPE",
                "SCOPE_COMPONENT",
                "SCOPE_LANE_COMPONENT",
            }:
                continue
            by_category[entry["category"]].append(_match_record(block, match, entry["semantic_id"]))
    owners = _collapse_axis_matches(
        _minimal_line_axis_matches(_deduplicate_matches(by_category["OWNER"])), scale=scale
    )
    roles = {
        item["role"]: _deduplicate_matches(
            [record for record in by_category["ROLE"] if record["semantic_id"] == item["role"]]
        )
        for item in spec["role_axis"]
    }
    deduplicated_scopes = _minimal_line_axis_matches(_deduplicate_matches(raw_scopes))
    # A wrapped population label is classified only after its maximal visible
    # phrase closes.  Thus ``Cho vay khách hàng,`` cannot be accepted from the
    # first line when following lines complete a visibly mixed population.
    scope_priority = {"HARD_VETO_BROAD": 0, "TARGET": 1, "HARD_VETO_MIXED": 2}
    closed_scopes = [
        item
        for item in deduplicated_scopes
        if not any(
            scope_priority[veto["scope_disposition"]] > scope_priority[item["scope_disposition"]]
            and set(item["source_line_indices_in_visual_order"]).issubset(
                veto["source_line_indices_in_visual_order"]
            )
            and set(item["source_line_indices_in_visual_order"])
            != set(veto["source_line_indices_in_visual_order"])
            for veto in deduplicated_scopes
        )
    ]
    scopes = _collapse_axis_matches(closed_scopes, scale=scale)
    # An owner phrase printed inside a longer population/scope heading is not
    # independent owner evidence.  Without this fence, the nested phrase is
    # visually closer to the roles than the real preceding owner and shadows
    # it; scope resolution then fails because that synthetic owner overlaps
    # its own scope.  A combined heading with no prior owner remains ownerless.
    scope_line_sets = [set(item["source_line_indices_in_visual_order"]) for item in scopes]
    owners = [
        owner
        for owner in owners
        if not any(
            set(owner["source_line_indices_in_visual_order"]).issubset(scope_lines)
            for scope_lines in scope_line_sets
        )
    ]
    continuations = _minimal_line_axis_matches(_deduplicate_matches(by_category["CONTINUATION"]))
    resets = _minimal_line_axis_matches(_deduplicate_matches(by_category["STRUCTURAL_RESET"]))
    totals = _collapse_axis_matches(
        _deduplicate_matches(by_category["TRAILING_TOTAL"]), scale=scale
    )
    return {
        "continuations": continuations,
        "matcher_metrics": {
            "approximate_alias_comparison_count": approximate_comparisons,
            "visual_window_count": prepared["visual_window_count"],
        },
        "owners": owners,
        "resets": resets,
        "roles": roles,
        "scopes": scopes,
        "trailing_totals": totals,
    }


def _center_x(record: Mapping[str, Any]) -> float:
    return (record["bbox"][0] + record["bbox"][2]) / 2


def _center_y(record: Mapping[str, Any]) -> float:
    return (record["bbox"][1] + record["bbox"][3]) / 2


def _owner_for(
    owners: Sequence[Mapping[str, Any]], *, top: int, scale: float, maximum_lines: int
) -> dict[str, Any] | None:
    eligible = [
        owner
        for owner in owners
        if owner["bbox"][3] <= top + scale * 0.2 and top - owner["bbox"][3] <= scale * maximum_lines
    ]
    return canonical_clone_v1(max(eligible, key=lambda item: item["bbox"][3])) if eligible else None


def _role_groups(
    page: Mapping[str, Any], semantic: Mapping[str, Any], spec: Mapping[str, Any], layout: str
) -> list[list[dict[str, Any]]]:
    role_order = [item["role"] for item in spec["role_axis"]]
    axes = [semantic["roles"][role] for role in role_order]
    if any(not items for items in axes):
        return []
    scale = median_text_height_v1(page["lines"])
    groups: list[list[dict[str, Any]]] = []
    for combination in product(*axes):
        if len({item["match_id"] for item in combination}) != len(combination):
            continue
        top = min(item["bbox"][1] for item in combination)
        bottom = max(item["bbox"][3] for item in combination)
        if bottom - top > scale * spec["limits"]["max_role_gap_lines"]:
            continue
        if layout == "ROLES_AS_COLUMNS":
            if (
                max(_center_y(item) for item in combination)
                - min(_center_y(item) for item in combination)
                > scale * 0.78
            ):
                continue
            if len({_center_x(item) for item in combination}) != len(combination):
                continue
        else:
            if len({_center_y(item) for item in combination}) != len(combination):
                continue
            ordered_y = sorted(_center_y(item) for item in combination)
            if any(
                right - left > scale * spec["limits"]["max_role_gap_lines"]
                for left, right in zip(ordered_y, ordered_y[1:], strict=False)
            ):
                continue
        groups.append([canonical_clone_v1(item) for item in combination])
    unique: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for group in groups:
        key = tuple(sorted(item["match_id"] for item in group))
        unique[key] = group
    ordered = sorted(
        unique.values(),
        key=lambda group: (
            min(item["bbox"][1] for item in group),
            min(item["bbox"][0] for item in group),
        ),
    )
    # Greedy visual exclusivity prevents one role label from joining two
    # neighboring physical blocks.
    selected: list[list[dict[str, Any]]] = []
    used: set[str] = set()
    for group in ordered:
        ids = {item["match_id"] for item in group}
        if ids & used:
            continue
        used.update(ids)
        selected.append(group)
    return selected


def _scope_candidates(
    scopes: Sequence[Mapping[str, Any]],
    role_group: Sequence[Mapping[str, Any]],
    owner: Mapping[str, Any],
    layout: str,
    *,
    lower_bound: int,
    upper_bound: int | None = None,
) -> list[dict[str, Any]]:
    role_top = min(item["bbox"][1] for item in role_group)
    role_bottom = max(item["bbox"][3] for item in role_group)
    if layout == "ROLES_AS_ROWS":
        candidates = [
            item
            for item in scopes
            if max(lower_bound, owner["bbox"][3]) <= item["bbox"][1] and item["bbox"][3] <= role_top
        ]
        # A prose introduction or merged ancestor may span several eventual
        # population columns and contain the same loan phrase as a deeper leaf
        # header.  Resolve the visually deepest non-overlapping leaves before
        # deriving value lanes; otherwise one narrative line becomes a second
        # synthetic population column.
        leaves: list[dict[str, Any]] = []
        leaf_priority = {"HARD_VETO_MIXED": 0, "TARGET": 1, "HARD_VETO_BROAD": 2}
        for candidate in sorted(
            candidates,
            key=lambda item: (
                -item["bbox"][3],
                leaf_priority[item["scope_disposition"]],
                _scope_interval(item)[1] - _scope_interval(item)[0],
                _scope_interval(item)[0],
            ),
        ):
            left, right = _scope_interval(candidate)
            width = right - left
            if any(
                selected["bbox"][3] >= candidate["bbox"][3]
                and max(
                    0,
                    min(right, _scope_interval(selected)[1])
                    - max(left, _scope_interval(selected)[0]),
                )
                >= min(width, _scope_interval(selected)[1] - _scope_interval(selected)[0]) * 0.45
                for selected in leaves
            ):
                continue
            leaves.append(candidate)
        candidates = leaves
    else:
        minimum_role_center = min(_center_x(item) for item in role_group)
        candidates = [
            item
            for item in scopes
            if item["bbox"][1] >= role_bottom
            and (upper_bound is None or item["bbox"][1] < upper_bound)
            and _center_x(item) < minimum_role_center
        ]
    return sorted(candidates, key=lambda item: (item["bbox"][1], _scope_center(item)))


def _scope_center(scope: Mapping[str, Any]) -> float:
    center_x2 = scope.get("lane_axis_center_x2")
    return center_x2 / 2 if type(center_x2) is int else _center_x(scope)


def _scope_interval(scope: Mapping[str, Any]) -> tuple[float, float]:
    bounds = scope.get("lane_axis_pixel_bounds")
    if (
        type(bounds) is list
        and len(bounds) == 2
        and all(type(item) is int for item in bounds)
        and bounds[0] < bounds[1]
    ):
        return float(bounds[0]), float(bounds[1])
    return float(scope["bbox"][0]), float(scope["bbox"][2])


def _has_resolved_column_span(cell: Mapping[str, Any], *, column_count: int) -> bool:
    """Return whether one header cell owns a complete, usable column span."""

    start = cell.get("column_start")
    stop = cell.get("column_stop")
    return (
        type(column_count) is int
        and column_count > 0
        and type(start) is int
        and type(stop) is int
        and 0 <= start < stop <= column_count
        and cell.get("geometry_status") != "STUB_HEADER_OUTSIDE_NUMERIC_COLUMNS"
    )


def _lane_scope_candidates(
    page: Mapping[str, Any],
    spec: Mapping[str, Any],
    alias_index: Mapping[str, Any],
    role_group: Sequence[Mapping[str, Any]],
    owner: Mapping[str, Any],
    *,
    lower_bound: int,
) -> tuple[list[dict[str, Any]], int]:
    lane_scopes = [item for item in spec["scope_axis"] if item["lane_component_groups"]]
    if not lane_scopes:
        return [], 0
    top = max(lower_bound, owner["bbox"][3])
    bottom = min(item["bbox"][1] for item in role_group)
    header_lines = [
        line
        for line in page["lines"]
        if line["bbox"][1] >= top and line["bbox"][3] <= bottom and not _is_value(line)
    ]
    unit_lines = [
        line
        for line in header_lines
        if accounting_unit_surface_v1(line["vietocr_text"]) is not None
    ]
    centers = sorted({(line["bbox"][0] + line["bbox"][2]) / 2 for line in unit_lines})
    if not centers:
        return [], 0
    try:
        graph = build_multilevel_header_graph_v1(
            [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "source_line_index": line["source_line_index"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in header_lines
            ],
            column_centers=centers,
            page_width=page["page_width"],
        )
    except AdaptiveAccountingTableGeometryV1Error:
        return [], 0
    source_lines = {line["source_line_index"]: line for line in header_lines}
    unit_ids = {line["source_line_index"] for line in unit_lines}
    bounds = _axis_bounds(centers, left=0.0, right=float(page["page_width"]))
    result = []
    approximate_comparisons = 0
    for lane_ordinal, center in enumerate(centers):
        cells = [
            cell
            for cell in graph.get("cells", [])
            if _has_resolved_column_span(cell, column_count=len(centers))
            and cell["column_start"] <= lane_ordinal < cell["column_stop"]
            and cell.get("source_line_index") in source_lines
            and cell["source_line_index"] not in unit_ids
        ]
        if not cells:
            continue
        deepest = max(cell["level_start"] for cell in cells)
        leaf_cells = [cell for cell in cells if cell["level_start"] == deepest]
        leaf_ids = {cell["source_line_index"] for cell in leaf_cells}
        path_ids = {cell["source_line_index"] for cell in cells}
        leaf_lines = _visual([source_lines[index] for index in leaf_ids])
        path_lines = _visual([source_lines[index] for index in path_ids])
        for scope in lane_scopes:
            matches = []
            evidence_ids: set[int] = set()
            for group in scope["lane_component_groups"]:
                source_cells = leaf_cells if group["source"] == "LEAF" else cells
                ordered_cells = sorted(
                    source_cells,
                    key=lambda item: (
                        -item["level_start"],
                        item["bbox"][1],
                        item["bbox"][0],
                    ),
                )
                selected = None
                for cell in ordered_cells:
                    line = source_lines[cell["source_line_index"]]
                    candidates, comparisons = _surface_matches(
                        line["vietocr_text"], alias_index, line_count=1
                    )
                    approximate_comparisons += comparisons
                    selected = next(
                        (
                            (entry, match, {line["source_line_index"]})
                            for entry, match in candidates
                            if entry["category"] == "SCOPE_LANE_COMPONENT"
                            and entry.get("component_source") == group["source"]
                            and entry["semantic_id"] == group["component_id"]
                            and entry.get("component_parent_semantic_id") == scope["scope_id"]
                        ),
                        None,
                    )
                    if selected is not None:
                        break
                if selected is None:
                    source_lines_for_group = leaf_lines if group["source"] == "LEAF" else path_lines
                    surface = " ".join(
                        line["vietocr_text"].strip() for line in source_lines_for_group
                    ).strip()
                    candidates, comparisons = _surface_matches(
                        surface, alias_index, line_count=len(source_lines_for_group)
                    )
                    approximate_comparisons += comparisons
                    selected = next(
                        (
                            (
                                entry,
                                match,
                                {line["source_line_index"] for line in source_lines_for_group},
                            )
                            for entry, match in candidates
                            if entry["category"] == "SCOPE_LANE_COMPONENT"
                            and entry.get("component_source") == group["source"]
                            and entry["semantic_id"] == group["component_id"]
                            and entry.get("component_parent_semantic_id") == scope["scope_id"]
                        ),
                        None,
                    )
                if selected is None:
                    matches = []
                    break
                entry, match, selected_ids = selected
                matches.append((entry, match))
                evidence_ids.update(selected_ids)
            composite = _required_component_group_match(
                matches,
                scope["lane_component_groups"],
                line_count=len(path_lines),
                parent_semantic_id=scope["scope_id"],
            )
            if composite is None:
                continue
            evidence_lines = _visual([source_lines[index] for index in evidence_ids])
            record = _match_record(evidence_lines, composite, scope["scope_id"])
            record.pop("match_id")
            record.update(
                {
                    "header_leaf_source_line_indices": sorted(leaf_ids),
                    "header_path_source_line_indices": sorted(path_ids),
                    "lane_axis_center_x2": int(round(center * 2)),
                    "lane_axis_pixel_bounds": canonical_clone_v1(bounds[lane_ordinal]),
                    "scope_disposition": scope["disposition"],
                    "scope_id": scope["scope_id"],
                    "scope_resolution": "MULTILEVEL_HEADER_GRAPH_ANCESTOR_PATH_AND_DEEPEST_LANE_LEAF",
                }
            )
            result.append(
                {**record, "match_id": "astgv1:match:" + canonical_json_sha256_v1(record)}
            )
    unique = {item["match_id"]: item for item in result}
    return (
        sorted(unique.values(), key=lambda item: (item["bbox"][1], _scope_center(item))),
        approximate_comparisons,
    )


def _axis_bounds(centers: Sequence[float], *, left: float, right: float) -> list[list[int]]:
    if not centers or centers != sorted(set(centers)) or not left < right:
        raise _error("scoped-table body axis drifted")
    if len(centers) == 1:
        half = max(1.0, min(centers[0] - left, right - centers[0]))
        return [[int(round(centers[0] - half)), int(round(centers[0] + half))]]
    boundaries = [max(left, centers[0] - (centers[1] - centers[0]) / 2)]
    boundaries.extend((a + b) / 2 for a, b in zip(centers, centers[1:], strict=False))
    boundaries.append(min(right, centers[-1] + (centers[-1] - centers[-2]) / 2))
    return [
        [int(round(boundaries[index])), int(round(boundaries[index + 1]))]
        for index in range(len(centers))
    ]


def _overlap_ppm(cell: Sequence[int], row: Sequence[int]) -> int:
    overlap = max(0, min(cell[3], row[3]) - max(cell[1], row[1]))
    denominator = max(1, min(cell[3] - cell[1], row[3] - row[1]))
    return overlap * 1_000_000 // denominator


@lru_cache(maxsize=_FEATURE_CACHE_MAXSIZE)
def _is_value_surfaces_cached(
    vietocr_text: str,
    source_text: str | None,
    classifier: Any,
) -> bool:
    return classifier(vietocr_text) or (type(source_text) is str and classifier(source_text))


def _is_value(line: Mapping[str, Any]) -> bool:
    if len(line["vietocr_text"]) + len(line["source_text"] or "") > (_FEATURE_CACHE_MAX_TEXT_CHARS):
        return is_accounting_value_surface_v1(line["vietocr_text"]) or (
            type(line["source_text"]) is str and is_accounting_value_surface_v1(line["source_text"])
        )
    return _is_value_surfaces_cached(
        line["vietocr_text"],
        line["source_text"],
        is_accounting_value_surface_v1,
    )


def _is_printed_number(line: Mapping[str, Any]) -> bool:
    """Require a visible number, excluding dash and blank cell proposals."""

    return is_number_like_v1(line["vietocr_text"]) or (
        type(line["source_text"]) is str and is_number_like_v1(line["source_text"])
    )


def _is_empty_visual_decoration(line: Mapping[str, Any]) -> bool:
    """Return whether an OCR box carries no visible surface in either channel."""

    return not line["vietocr_text"].strip() and (
        line["source_text"] is None or not line["source_text"].strip()
    )


def _header_context(
    page: Mapping[str, Any], *, start: int, stop: int, centers: Sequence[float]
) -> dict[str, Any]:
    lines = [
        line
        for line in page["lines"]
        if line["bbox"][1] >= start and line["bbox"][3] <= stop and not _is_value(line)
    ]
    periods = extract_period_observations_v1(lines)
    unit_records = []
    for line in lines:
        parsed = accounting_unit_surface_v1(line["vietocr_text"])
        if parsed is not None:
            unit_records.append({**parsed, "evidence": _line_evidence(line)})
    unit_keys = {
        (item["unit_kind"], item["currency"], item["magnitude_power10"]) for item in unit_records
    }
    unit = None
    if len(unit_keys) == 1:
        unit_kind, currency, magnitude = next(iter(unit_keys))
        unit = {
            "currency": currency,
            "magnitude_power10": magnitude,
            "unit_kind": unit_kind,
        }
    header_graph: dict[str, Any] | None = None
    if lines and centers:
        graph_lines = [
            {
                "bbox": canonical_clone_v1(line["bbox"]),
                "source_line_index": line["source_line_index"],
                "vietocr_text": line["vietocr_text"],
            }
            for line in lines
        ]
        try:
            header_graph = build_multilevel_header_graph_v1(
                graph_lines,
                column_centers=list(centers),
                page_width=page["page_width"],
            )
        except AdaptiveAccountingTableGeometryV1Error:
            header_graph = {
                "format_version": "ADAPTIVE_ACCOUNTING_MULTILEVEL_HEADER_GRAPH_V1",
                "status": "UNRESOLVED_HEADER_GEOMETRY",
            }
    return {
        "header_geometry": header_graph,
        "period_observations": periods,
        "unit_evidence": unit_records,
        "unit_resolution": unit,
    }


def _period_resolution(context: Mapping[str, Any]) -> dict[str, Any]:
    unique = sorted({item["period"] for item in context["period_observations"]})
    return {
        "period_key": unique[0] if len(unique) == 1 else None,
        "period_resolution": "ONE_LOCAL_PERIOD_OBSERVATION" if len(unique) == 1 else "UNRESOLVED",
    }


def _cell_record(
    *,
    assigned: Mapping[str, Any] | None,
    expected_bounds: Sequence[int],
    expected_center: float,
    page_sequence: int,
    period_lane_index: int | None,
    role: str,
    source_role_ordinal: int,
    source_value_column_ordinal: int,
    row_bbox: Sequence[int],
    minimum_overlap_ppm: int,
    missing_proposal: Mapping[str, Any] | None,
) -> dict[str, Any]:
    line = assigned["line"] if assigned is not None else None
    overlap = _overlap_ppm(line["bbox"], row_bbox) if line is not None else 0
    if line is not None and overlap < minimum_overlap_ppm:
        line = None
        assigned = None
        overlap = 0
    material = {
        "bbox": canonical_clone_v1(line["bbox"]) if line is not None else None,
        "expected_pixel_bbox": [
            int(expected_bounds[0]),
            int(row_bbox[1]),
            int(expected_bounds[1]),
            int(row_bbox[3]),
        ],
        "missing_detector_region_proposal": (
            canonical_clone_v1(missing_proposal) if line is None and missing_proposal else None
        ),
        "page_sequence": page_sequence,
        "period_lane_index": period_lane_index,
        "role": role,
        "row_overlap_ppm": overlap,
        "source_line_index": line["source_line_index"] if line is not None else None,
        "source_role_ordinal": source_role_ordinal,
        "source_text": line["source_text"] if line is not None else None,
        "source_value_column_ordinal": source_value_column_ordinal,
        "status": (
            "VISIBLE_ACCOUNTING_SURFACE_NO_NUMERIC_AUTHORITY"
            if line is not None
            else "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_REPLAY"
        ),
        "value_axis_center_x2": int(round(expected_center * 2)),
        "vietocr_accentless_surface": (
            _accentless_surface(line["vietocr_text"]) if line is not None else None
        ),
        "vietocr_raw_nfc_surface": line["vietocr_text"] if line is not None else None,
    }
    return {**material, "cell_id": "astgv1:cell:" + canonical_json_sha256_v1(material)}


def _row_cells(
    page: Mapping[str, Any],
    *,
    centers: Sequence[float],
    bounds: Sequence[Sequence[int]],
    roles: Sequence[Mapping[str, Any]],
    scope_ordinal: int,
    minimum_overlap_ppm: int,
) -> list[dict[str, Any]]:
    result = []
    center_tuple = tuple(float(item) for item in centers)
    for source_role_ordinal, role in enumerate(roles):
        label_boxes = [item["bbox"] for item in role["line_evidence"]]
        assigned = assign_value_row_lanes_v1(
            page["lines"],
            label_boxes=label_boxes,
            is_numeric=_is_value,
            page_width=page["page_width"],
            resolved_column_centers=center_tuple,
        )
        by_lane = {item["column_ordinal"]: item for item in assigned}
        visible = tuple(
            {"bbox": item["line"]["bbox"], "column_ordinal": item["column_ordinal"]}
            for item in assigned
            if _overlap_ppm(item["line"]["bbox"], role["bbox"]) >= minimum_overlap_ppm
        )
        proposals = propose_missing_value_lane_regions_v1(
            page["lines"],
            label_boxes=label_boxes,
            is_numeric=_is_value,
            page_width=page["page_width"],
            page_height=page["page_height"],
            resolved_column_centers=center_tuple,
            resolved_visible_value_cells=visible,
        )
        proposal_by_lane = {item["column_ordinal"]: item for item in proposals}
        result.append(
            _cell_record(
                assigned=by_lane.get(scope_ordinal),
                expected_bounds=bounds[scope_ordinal],
                expected_center=centers[scope_ordinal],
                page_sequence=page["page_sequence"],
                period_lane_index=None,
                role=role["semantic_id"],
                source_role_ordinal=source_role_ordinal,
                source_value_column_ordinal=scope_ordinal,
                row_bbox=role["bbox"],
                minimum_overlap_ppm=minimum_overlap_ppm,
                missing_proposal=proposal_by_lane.get(scope_ordinal),
            )
        )
    return result


def _column_cells(
    page: Mapping[str, Any],
    *,
    bounds: Sequence[Sequence[int]],
    centers: Sequence[float],
    roles: Sequence[Mapping[str, Any]],
    scope: Mapping[str, Any],
    minimum_overlap_ppm: int,
) -> list[dict[str, Any]]:
    center_tuple = tuple(float(item) for item in centers)
    label_boxes = [item["bbox"] for item in scope["line_evidence"]]
    assigned = assign_value_row_lanes_v1(
        page["lines"],
        label_boxes=label_boxes,
        is_numeric=_is_value,
        page_width=page["page_width"],
        resolved_column_centers=center_tuple,
    )
    by_lane = {item["column_ordinal"]: item for item in assigned}
    visible = tuple(
        {"bbox": item["line"]["bbox"], "column_ordinal": item["column_ordinal"]}
        for item in assigned
        if _overlap_ppm(item["line"]["bbox"], scope["bbox"]) >= minimum_overlap_ppm
    )
    proposals = propose_missing_value_lane_regions_v1(
        page["lines"],
        label_boxes=label_boxes,
        is_numeric=_is_value,
        page_width=page["page_width"],
        page_height=page["page_height"],
        resolved_column_centers=center_tuple,
        resolved_visible_value_cells=visible,
    )
    proposal_by_lane = {item["column_ordinal"]: item for item in proposals}
    return [
        _cell_record(
            assigned=by_lane.get(ordinal),
            expected_bounds=bounds[ordinal],
            expected_center=centers[ordinal],
            page_sequence=page["page_sequence"],
            period_lane_index=None,
            role=role["semantic_id"],
            source_role_ordinal=ordinal,
            source_value_column_ordinal=ordinal,
            row_bbox=scope["bbox"],
            minimum_overlap_ppm=minimum_overlap_ppm,
            missing_proposal=proposal_by_lane.get(ordinal),
        )
        for ordinal, role in enumerate(roles)
    ]


def _trailing_total(
    semantic: Mapping[str, Any], roles: Sequence[Mapping[str, Any]], *, scale: float
) -> Mapping[str, Any] | None:
    role_y = median(_center_y(item) for item in roles)
    last_center = max(_center_x(item) for item in roles)
    candidates = [
        item
        for item in semantic["trailing_totals"]
        if _center_x(item) > last_center and abs(_center_y(item) - role_y) <= scale * 0.9
    ]
    return min(candidates, key=_center_x) if candidates else None


def _trailing_total_row(
    semantic: Mapping[str, Any],
    roles: Sequence[Mapping[str, Any]],
    *,
    maximum_gap_lines: int,
    scale: float,
    stop_before: int | None = None,
) -> Mapping[str, Any] | None:
    role_bottom = max(item["bbox"][3] for item in roles)
    candidates = [
        item
        for item in semantic["trailing_totals"]
        if item["bbox"][1] >= role_bottom - scale * 0.2
        and item["bbox"][1] - role_bottom <= scale * maximum_gap_lines
        and (stop_before is None or item["bbox"][1] < stop_before)
    ]
    return (
        min(candidates, key=lambda item: (item["bbox"][1], item["bbox"][0])) if candidates else None
    )


def _unlabeled_trailing_total_row(
    page: Mapping[str, Any],
    roles: Sequence[Mapping[str, Any]],
    *,
    role_cells: Sequence[Mapping[str, Any]],
    bounds: Sequence[Sequence[int]],
    scope_ordinal: int,
    minimum_overlap_ppm: int,
    maximum_gap_lines: int,
    gap_jitter_ppm: int,
    maximum_numeric_columns: int,
    minimum_numeric_columns: int,
    scale: float,
    stop_before: int | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Bind one printed numeric-only total row without inventing a label.

    This is the region-local counterpart of the shared family row-axis
    trailing-value-row geometry.  Candidate discovery reuses the adaptive
    numeric row/column primitives, but visually reindexes the bounded lines so
    provider ordinals never become ordering authority.  No candidate value is
    parsed, summed, or selected by an accounting equation here.
    """

    lines_by_source = {line["source_line_index"]: line for line in page["lines"]}
    role_label_boxes = []
    role_label_source_indices: set[int] = set()
    for role in roles:
        label_lines = [
            lines_by_source[item["source_line_index"]]
            for item in role["line_evidence"]
            if item["source_line_index"] in lines_by_source
            and not _is_value(lines_by_source[item["source_line_index"]])
        ]
        if not label_lines:
            return None, []
        role_label_boxes.append(_union(label_lines))
        role_label_source_indices.update(line["source_line_index"] for line in label_lines)
    label_role_bottom = max(box[3] for box in role_label_boxes)
    role_right = max(box[2] for box in role_label_boxes)
    left_ratio = min(0.98, max(0.0, (role_right + scale * 0.25) / page["page_width"]))
    maximum_ratio = 0.995
    if left_ratio >= maximum_ratio:
        return None, []
    body_values = [
        line
        for line in page["lines"]
        if _is_printed_number(line)
        and line["bbox"][0] > page["page_width"] * left_ratio
        and max(_overlap_ppm(line["bbox"], box) for box in role_label_boxes) >= minimum_overlap_ppm
    ]
    if len(body_values) < minimum_numeric_columns:
        return None, []
    scale_x2 = int(round(scale * 2))
    body_label_jitter_numerator = scale_x2 * gap_jitter_ppm
    body_label_jitter_pixels = (body_label_jitter_numerator + 2_000_000 - 1) // 2_000_000
    body_role_bottom = max(line["bbox"][3] for line in body_values)
    if body_role_bottom - label_role_bottom > body_label_jitter_pixels:
        return None, []
    effective_role_bottom = max(label_role_bottom, body_role_bottom)
    body_value_source_indices = {line["source_line_index"] for line in body_values}
    body_centers = infer_numeric_column_centers_v1(
        body_values,
        is_numeric=_is_printed_number,
        page_width=page["page_width"],
        minimum_x_ratio=left_ratio,
        maximum_x_ratio=maximum_ratio,
        retain_singleton_columns=True,
    )
    if not minimum_numeric_columns <= len(body_centers) <= maximum_numeric_columns:
        return None, []
    body_tolerance = max(scale * 1.35, page["page_width"] * 0.012)
    body_lane_support: list[list[Mapping[str, Any]]] = [[] for _center in body_centers]
    for line in body_values:
        distances = [abs(_center_x(line) - center) for center in body_centers]
        nearest = min(distances)
        lanes = [index for index, distance in enumerate(distances) if distance == nearest]
        if nearest <= body_tolerance and len(lanes) == 1:
            body_lane_support[lanes[0]].append(line)
    if any(not support for support in body_lane_support):
        return None, []

    start_y = label_role_bottom - scale * 0.2
    # OCR bbox bottoms can drift by a small declarative fraction of one text
    # line.  Apply that tolerance only to the local role-gap ceiling: a proven
    # following scope/owner/period/unit/reset boundary remains an exact fence.
    gap_distance_numerator = scale_x2 * (maximum_gap_lines * 1_000_000 + gap_jitter_ppm)
    gap_distance_pixels = (gap_distance_numerator + 2_000_000 - 1) // 2_000_000
    gap_stop = effective_role_bottom + gap_distance_pixels
    stop_y = min(
        float(page["page_height"]),
        gap_stop,
        float(stop_before) if stop_before is not None else float(page["page_height"]),
    )
    bounded = [
        line
        for line in _visual(page["lines"])
        if line["bbox"][1] >= start_y
        and line["bbox"][3] <= stop_y
        and line["bbox"][0] > page["page_width"] * left_ratio
    ]
    if not bounded:
        return None, []
    # The adaptive row clusterer consumes a source-index interval.  Feed it a
    # visual-only temporary axis and restore every immutable source locator in
    # the emitted evidence below.
    visual_lines = []
    original_by_visual: dict[int, Mapping[str, Any]] = {}
    for visual_ordinal, line in enumerate(bounded):
        original_by_visual[visual_ordinal] = line
        visual_lines.append({**line, "source_line_index": visual_ordinal})
    clusters = cluster_numeric_rows_v1(
        visual_lines,
        is_numeric=_is_printed_number,
        start_index=-1,
        stop_index=len(visual_lines),
        page_width=page["page_width"],
        minimum_x_ratio=left_ratio,
        maximum_x_ratio=maximum_ratio,
    )
    tolerance = body_tolerance
    complete: list[tuple[list[Mapping[str, Any]], dict[int, Mapping[str, Any]]]] = []
    for raw_cluster in clusters:
        cluster = [original_by_visual[item["source_line_index"]] for item in raw_cluster]
        if not minimum_numeric_columns <= len(cluster) <= maximum_numeric_columns:
            continue
        by_lane: dict[int, Mapping[str, Any]] = {}
        for line in cluster:
            line_center = _center_x(line)
            distances = [abs(line_center - center) for center in body_centers]
            nearest = min(distances)
            nearest_lanes = [
                index for index, distance in enumerate(distances) if distance == nearest
            ]
            if nearest > tolerance or len(nearest_lanes) != 1 or nearest_lanes[0] in by_lane:
                by_lane = {}
                break
            by_lane[nearest_lanes[0]] = line
        if set(by_lane) != set(range(len(body_centers))):
            continue
        ordered_cluster = _visual(cluster)
        row_bbox = _union(ordered_cluster)
        candidate_source_indices = {line["source_line_index"] for line in ordered_cluster}
        proven_source_indices = (
            role_label_source_indices | body_value_source_indices | candidate_source_indices
        )
        if any(
            line["source_line_index"] not in proven_source_indices
            and line["bbox"][3] > label_role_bottom
            and line["bbox"][1] < row_bbox[3]
            and not _is_empty_visual_decoration(line)
            for line in page["lines"]
        ):
            # A numeric-only total must be the first visible row band after the
            # required role axis.  Crossing an unclassified header would borrow
            # a complete row from an unrelated following table.
            continue
        if any(
            not _is_value(line)
            and line not in ordered_cluster
            and _overlap_ppm(line["bbox"], row_bbox) >= minimum_overlap_ppm
            for line in page["lines"]
        ):
            continue
        complete.append((ordered_cluster, by_lane))
    if len(complete) != 1:
        return None, []

    # The target is the axis persisted on every required role cell, never a
    # broad semantic header bbox that could span several accounting columns.
    role_axis_centers_x2 = {item["value_axis_center_x2"] for item in role_cells}
    if len(role_cells) != len(roles) or len(role_axis_centers_x2) != 1:
        return None, []
    target_axis_center_x2 = next(iter(role_axis_centers_x2))
    target_center = target_axis_center_x2 / 2
    target_distances = [abs(target_center - center) for center in body_centers]
    target_distance = min(target_distances)
    target_lanes = [
        index for index, distance in enumerate(target_distances) if distance == target_distance
    ]
    if target_distance > tolerance or len(target_lanes) != 1:
        return None, []
    target_lane = target_lanes[0]
    cluster, by_lane = complete[0]
    target_line = by_lane[target_lane]
    row_bbox = _union(cluster)
    cell = _cell_record(
        assigned={"line": target_line},
        expected_bounds=bounds[scope_ordinal],
        expected_center=target_center,
        page_sequence=page["page_sequence"],
        period_lane_index=None,
        role="TRAILING_TOTAL",
        source_role_ordinal=0,
        source_value_column_ordinal=scope_ordinal,
        row_bbox=row_bbox,
        minimum_overlap_ppm=minimum_overlap_ppm,
        missing_proposal=None,
    )
    resolution_material = {
        "body_axis_centers_x2": [int(round(center * 2)) for center in body_centers],
        "body_axis_support_counts": [len(support) for support in body_lane_support],
        "body_axis_support_evidence": [
            {
                "axis_center_x2": int(round(body_centers[axis_ordinal] * 2)),
                "axis_ordinal": axis_ordinal,
                "support_line_evidence": [_line_evidence(line) for line in _visual(support)],
                "support_line_ids": [
                    f"line:{line['page_sequence']}:{line['source_line_index']}"
                    for line in _visual(support)
                ],
            }
            for axis_ordinal, support in enumerate(body_lane_support)
        ],
        "mode": "UNLABELED_COMPLETE_NUMERIC_TOTAL_ROW",
        "page_sequence": page["page_sequence"],
        "role_row_bottom_evidence": {
            "body_numeric_bottom": body_role_bottom,
            "body_support_line_ids": [
                f"line:{line['page_sequence']}:{line['source_line_index']}"
                for line in _visual(body_values)
            ],
            "effective_bottom": effective_role_bottom,
            "jitter_cap_pixels": body_label_jitter_pixels,
            "label_bottom": label_role_bottom,
            "label_support_line_ids": [
                f"line:{line['page_sequence']}:{line['source_line_index']}"
                for line in _visual(
                    [lines_by_source[source_index] for source_index in role_label_source_indices]
                )
            ],
        },
        "row_bbox": row_bbox,
        "row_evidence": [_line_evidence(line) for line in cluster],
        "target_body_axis_ordinal": target_lane,
        "target_role_cell_axis_center_x2": target_axis_center_x2,
        "target_role_cell_source_ordinals": sorted(
            item["source_role_ordinal"] for item in role_cells
        ),
    }
    resolution = {
        **resolution_material,
        "resolution_id": "astgv1:trailing-total-resolution:"
        + canonical_json_sha256_v1(resolution_material),
    }
    return resolution, [cell]


def _period_resolution_for_lane(
    context: Mapping[str, Any],
    *,
    lane_bounds: Sequence[int],
    lane_ordinal: int,
    lane_center: float,
) -> dict[str, Any]:
    """Bind one visible period observation to one body-derived value lane."""

    observations = context["period_observations"]
    graph = context["header_geometry"]
    graph_column_centers = graph.get("column_centers") if type(graph) is dict else None
    column_count = len(graph_column_centers) if type(graph_column_centers) is list else 0
    by_line = (
        {
            cell["source_line_index"]: cell
            for cell in graph.get("cells", [])
            if type(cell.get("source_line_index")) is int
        }
        if type(graph) is dict
        else {}
    )
    spanning = []
    for observation in observations:
        cells = [
            by_line[index]
            for index in observation["evidence_source_line_indices"]
            if index in by_line
        ]
        spatially_bound = any(
            max(
                0,
                min(cell["bbox"][2], lane_bounds[1]) - max(cell["bbox"][0], lane_bounds[0]),
            )
            >= max(
                1,
                min(
                    cell["bbox"][2] - cell["bbox"][0],
                    lane_bounds[1] - lane_bounds[0],
                )
                * 0.15,
            )
            for cell in cells
        )
        if (
            cells
            and spatially_bound
            and any(
                _has_resolved_column_span(cell, column_count=column_count)
                and cell["column_start"] <= lane_ordinal < cell["column_stop"]
                for cell in cells
            )
        ):
            spanning.append(observation)
    unique = {item["period"]: item for item in spanning}
    if len(unique) == 1:
        return {
            "period_key": next(iter(unique)),
            "period_resolution": "LOCAL_PERIOD_HEADER_SPAN_BOUND_TO_VALUE_LANE",
        }
    # Some OCR boxes stop just short of a body-derived lane boundary.  The
    # nearest-center fallback is accepted only when it is uniquely closer than
    # every other visible period heading.
    ranked = sorted(
        ((abs(item["x_center_x2"] / 2 - lane_center), item) for item in observations),
        key=lambda item: (item[0], item[1]["period"]),
    )
    lane_width = lane_bounds[1] - lane_bounds[0]
    nearest_center = ranked[0][1]["x_center_x2"] / 2 if ranked else None
    if (
        ranked
        and lane_width > 0
        and lane_bounds[0] - lane_width * 0.1 <= nearest_center <= lane_bounds[1] + lane_width * 0.1
        and ranked[0][0] <= lane_width
        and (len(ranked) == 1 or ranked[0][0] < ranked[1][0])
    ):
        return {
            "period_key": ranked[0][1]["period"],
            "period_resolution": "LOCAL_PERIOD_HEADER_UNIQUE_NEAREST_VALUE_LANE",
        }
    # A repeated vertical period block can print its sole date as a left-stub
    # caption (for example, ``Tại ngày ...``) rather than above the numeric
    # value lane.  The caller has already bounded ``context`` to this one role
    # block.  Accept the caption only when there is one distinct local period
    # and its visible box ends close to the lane domain.  This preserves the
    # lane binding while rejecting a page-wide narrative date far to the left.
    unique_observations = {item["period"]: item for item in observations}
    if len(unique_observations) == 1 and lane_width > 0:
        observation = next(iter(unique_observations.values()))
        evidence_cells = [
            by_line[index]
            for index in observation["evidence_source_line_indices"]
            if index in by_line
        ]
        if evidence_cells:
            caption_left = min(cell["bbox"][0] for cell in evidence_cells)
            caption_right = max(cell["bbox"][2] for cell in evidence_cells)
            if (
                caption_left <= lane_bounds[1]
                and caption_right >= lane_bounds[0] - lane_width * 0.55
            ):
                return {
                    "period_key": observation["period"],
                    "period_resolution": (
                        "LOCAL_SINGLE_PERIOD_TABLE_BLOCK_CAPTION_BOUND_TO_LANE_DOMAIN"
                    ),
                }
        unit_boxes = [
            item["evidence"]["bbox"]
            for item in context["unit_evidence"]
            if type(item.get("evidence")) is dict and type(item["evidence"].get("bbox")) is list
        ]
        if evidence_cells and unit_boxes and context["unit_resolution"] is not None:
            caption_left = min(cell["bbox"][0] for cell in evidence_cells)
            caption_right = max(cell["bbox"][2] for cell in evidence_cells)
            if any(max(caption_left, box[0]) < min(caption_right, box[2]) for box in unit_boxes):
                return {
                    "period_key": observation["period"],
                    "period_resolution": (
                        "LOCAL_SINGLE_PERIOD_TABLE_BLOCK_CAPTION_BOUND_TO_UNIT_DOMAIN"
                    ),
                }
    return {"period_key": None, "period_resolution": "UNRESOLVED"}


def _rehash_cell(cell: Mapping[str, Any]) -> dict[str, Any]:
    material = canonical_clone_v1(cell)
    material.pop("cell_id", None)
    return {**material, "cell_id": "astgv1:cell:" + canonical_json_sha256_v1(material)}


def _exclusive_visible_cells(cells: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Consume every detected value line globally and exclusively per segment."""

    by_source: dict[tuple[int, int], list[int]] = {}
    result = [canonical_clone_v1(item) for item in cells]
    for index, cell in enumerate(result):
        source = cell["source_line_index"]
        if type(source) is int:
            by_source.setdefault((cell["page_sequence"], source), []).append(index)
    for indices in by_source.values():
        if len(indices) == 1:
            continue
        maximum = max(result[index]["row_overlap_ppm"] for index in indices)
        winners = [index for index in indices if result[index]["row_overlap_ppm"] == maximum]
        retained = winners[0] if len(winners) == 1 else None
        for index in indices:
            if index == retained:
                continue
            cell = result[index]
            cell.update(
                {
                    "bbox": None,
                    "row_overlap_ppm": 0,
                    "source_line_index": None,
                    "source_text": None,
                    "status": "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_REPLAY",
                    "vietocr_accentless_surface": None,
                    "vietocr_raw_nfc_surface": None,
                }
            )
            result[index] = _rehash_cell(cell)
    return result


def _segment(
    page: Mapping[str, Any],
    semantic: Mapping[str, Any],
    spec: Mapping[str, Any],
    role_group: Sequence[Mapping[str, Any]],
    scope: Mapping[str, Any],
    owner: Mapping[str, Any],
    layout: str,
    *,
    lower_bound: int,
    upper_bound: int | None,
) -> dict[str, Any]:
    scale = median_text_height_v1(page["lines"])
    minimum_overlap = spec["limits"]["minimum_cell_row_overlap_ppm"]
    trailing_total = None
    trailing_total_cells: list[dict[str, Any]] = []
    trailing_total_resolution = None
    if layout == "ROLES_AS_ROWS":
        all_scopes = _scope_candidates(
            semantic["scopes"], role_group, owner, layout, lower_bound=lower_bound
        )
        centers = sorted({_scope_center(item) for item in all_scopes})
        scope_center = _scope_center(scope)
        scope_ordinal = centers.index(scope_center)
        target_scope_centers = {
            _scope_center(item) for item in all_scopes if item["scope_disposition"] == "TARGET"
        }
        bounds = _axis_bounds(centers, left=0.0, right=float(page["page_width"]))
        cells = _row_cells(
            page,
            centers=centers,
            bounds=bounds,
            roles=role_group,
            scope_ordinal=scope_ordinal,
            minimum_overlap_ppm=minimum_overlap,
        )
        role_bottom = max(item["bbox"][3] for item in role_group)
        row_stop_candidates = [
            reset["bbox"][1] for reset in semantic["resets"] if reset["bbox"][1] >= role_bottom
        ]
        header_search_stop = min(
            upper_bound if upper_bound is not None else page["page_height"],
            int(round(role_bottom + scale * spec["limits"]["max_role_gap_lines"])),
        )
        row_stop_candidates.extend(
            match["bbox"][1]
            for category in (semantic["scopes"], semantic["owners"])
            for match in category
            if role_bottom < match["bbox"][1] < header_search_stop
        )
        # A following repeated period block can print its total-column header
        # a few pixels before its population label because OCR boxes jitter
        # vertically.  Period, unit, owner, scope and reset evidence all close
        # the current row block before either labeled or unlabeled total-row
        # discovery.  Captions above the current roles remain outside the band.
        next_header_lines = [
            line
            for line in page["lines"]
            if line["bbox"][1] >= role_bottom
            and line["bbox"][3] <= header_search_stop
            and not _is_value(line)
        ]
        next_periods = extract_period_observations_v1(next_header_lines)
        line_tops = {line["source_line_index"]: line["bbox"][1] for line in next_header_lines}
        period_caption_tops: dict[str, int] = {}
        for observation in next_periods:
            evidence_tops = [
                line_tops[index]
                for index in observation["evidence_source_line_indices"]
                if index in line_tops
            ]
            if evidence_tops:
                period_caption_tops[observation["period"]] = min(
                    min(evidence_tops),
                    period_caption_tops.get(observation["period"], header_search_stop),
                )
        row_stop_candidates.extend(period_caption_tops.values())
        row_stop_candidates.extend(
            line["bbox"][1]
            for line in next_header_lines
            if accounting_unit_surface_v1(line["vietocr_text"]) is not None
        )
        if upper_bound is not None:
            row_stop_candidates.append(upper_bound)
        row_stop = min(row_stop_candidates, default=None)
        trailing_total = _trailing_total_row(
            semantic,
            role_group,
            maximum_gap_lines=spec["limits"]["max_role_gap_lines"],
            scale=scale,
            stop_before=row_stop,
        )
        if trailing_total is not None:
            trailing_total_cells = _row_cells(
                page,
                centers=centers,
                bounds=bounds,
                roles=[trailing_total],
                scope_ordinal=scope_ordinal,
                minimum_overlap_ppm=minimum_overlap,
            )
        elif scope["scope_disposition"] == "TARGET" and target_scope_centers == {scope_center}:
            trailing_total_resolution, trailing_total_cells = _unlabeled_trailing_total_row(
                page,
                role_group,
                role_cells=cells,
                bounds=bounds,
                scope_ordinal=scope_ordinal,
                minimum_overlap_ppm=minimum_overlap,
                maximum_gap_lines=spec["limits"]["unlabeled_total_max_gap_lines"],
                gap_jitter_ppm=spec["limits"]["unlabeled_total_gap_jitter_ppm"],
                maximum_numeric_columns=spec["limits"]["unlabeled_total_max_numeric_columns"],
                minimum_numeric_columns=spec["limits"]["unlabeled_total_min_numeric_columns"],
                scale=scale,
                stop_before=row_stop,
            )
        header_stop = min(item["bbox"][1] for item in role_group)
    else:
        ordered_roles = sorted(role_group, key=_center_x)
        centers = [_center_x(item) for item in ordered_roles]
        trailing_total = _trailing_total(semantic, ordered_roles, scale=scale)
        target_requires_total = (
            scope["scope_disposition"] == "TARGET"
            and spec["require_trailing_total_for_roles_as_columns"]
        )
        if target_requires_total and trailing_total is None:
            bounds = _axis_bounds(
                centers,
                left=max(0.0, centers[0] - max(scale * 2, 1)),
                right=min(float(page["page_width"]), centers[-1] + max(scale * 2, 1)),
            )
            cells = []
        else:
            extended_roles = [*ordered_roles]
            extended_centers = [*centers]
            if trailing_total is not None:
                extended_roles.append(trailing_total)
                extended_centers.append(_center_x(trailing_total))
            right = min(
                float(page["page_width"]),
                extended_centers[-1] + (extended_centers[-1] - extended_centers[-2]) / 2,
            )
            extended_bounds = _axis_bounds(
                extended_centers,
                left=max(0.0, centers[0] - (centers[1] - centers[0]) / 2),
                right=right,
            )
            all_cells = _column_cells(
                page,
                bounds=extended_bounds,
                centers=extended_centers,
                roles=extended_roles,
                scope=scope,
                minimum_overlap_ppm=minimum_overlap,
            )
            cells = all_cells[: len(ordered_roles)]
            trailing_total_cells = all_cells[len(ordered_roles) :]
            bounds = extended_bounds[: len(ordered_roles)]
        # Some complete transposed tables print unit and one table-period
        # caption immediately below the geography column labels.  The bounded
        # local header band therefore closes at the selected population row,
        # not at the role-label baseline.
        header_stop = scope["bbox"][1]
    header_start = max(lower_bound, owner["bbox"][3])
    context = _header_context(page, start=header_start, stop=header_stop, centers=centers)
    period = (
        _period_resolution_for_lane(
            context,
            lane_bounds=bounds[scope_ordinal],
            lane_ordinal=scope_ordinal,
            lane_center=scope_center,
        )
        if layout == "ROLES_AS_ROWS" and context["period_observations"]
        else _period_resolution(context)
    )
    combined_cells = _exclusive_visible_cells([*cells, *trailing_total_cells])
    cells = combined_cells[: len(cells)]
    trailing_total_cells = combined_cells[len(cells) :]
    unresolved = []
    if not cells and scope["scope_disposition"] == "TARGET":
        unresolved.append("TRANSPOSED_TRAILING_TOTAL_HEADER_NOT_RESOLVED")
    material = {
        "axis_centers_x2": [int(round(center * 2)) for center in centers],
        "axis_pixel_bounds": bounds,
        "header_context": context,
        "layout_mode": layout,
        "owner": canonical_clone_v1(owner),
        "page_sequences": [page["page_sequence"]],
        **period,
        "population_scope": {
            "disposition": scope["scope_disposition"],
            "match": canonical_clone_v1(scope),
            "scope_id": scope["scope_id"],
        },
        "role_cells": cells,
        "role_matches": [canonical_clone_v1(item) for item in role_group],
        "segment_status": (
            "COMPLETE_TARGET_SCOPE_STRUCTURE_NO_NUMERIC_AUTHORITY"
            if scope["scope_disposition"] == "TARGET" and not unresolved
            else "HARD_VETO_SCOPE_BOUNDED_ABSENCE"
            if scope["scope_disposition"].startswith("HARD_VETO") and not unresolved
            else "UNRESOLVED_PHYSICAL_SEGMENT"
        ),
        "trailing_total_cells": trailing_total_cells,
        "trailing_total_match": canonical_clone_v1(trailing_total),
        "trailing_total_resolution": canonical_clone_v1(trailing_total_resolution),
        "unresolved_reasons": sorted(unresolved),
    }
    return {**material, "segment_id": "astgv1:segment:" + canonical_json_sha256_v1(material)}


def _same_page_repeated_block_owner(
    page: Mapping[str, Any],
    semantic: Mapping[str, Any],
    spec: Mapping[str, Any],
    previous_group: Sequence[Mapping[str, Any]],
    current_group: Sequence[Mapping[str, Any]],
    previous_owner: Mapping[str, Any],
    *,
    lower_bound: int,
    layout: str,
) -> dict[str, Any] | None:
    """Carry one proven owner into the immediately repeated period block."""

    if layout != "ROLES_AS_ROWS" or [item["semantic_id"] for item in previous_group] != [
        item["semantic_id"] for item in current_group
    ]:
        return None
    scale = median_text_height_v1(page["lines"])
    current_top = min(item["bbox"][1] for item in current_group)
    previous_bottom = max(item["bbox"][3] for item in previous_group)
    if (
        lower_bound != previous_bottom
        or previous_bottom >= current_top
        or current_top - previous_bottom > scale * spec["limits"]["max_owner_distance_lines"]
    ):
        return None
    tolerance = spec["limits"]["axis_tolerance_ppm"]
    if any(
        abs(_center_x(left) - _center_x(right)) * 1_000_000 > page["page_width"] * tolerance
        for left, right in zip(previous_group, current_group, strict=True)
    ):
        return None
    if any(
        reset["bbox"][1] < current_top and reset["bbox"][3] > previous_bottom
        for reset in semantic["resets"]
    ) or any(
        owner["match_id"] != previous_owner["match_id"]
        and owner["bbox"][1] < current_top
        and owner["bbox"][3] > previous_bottom
        for owner in semantic["owners"]
    ):
        return None
    block_scopes = [
        scope
        for scope in semantic["scopes"]
        if scope["bbox"][1] >= previous_bottom and scope["bbox"][3] <= current_top
    ]
    context = _header_context(
        page,
        start=previous_bottom,
        stop=current_top,
        centers=[],
    )
    if (
        not block_scopes
        or context["unit_resolution"] is None
        or len({item["period"] for item in context["period_observations"]}) != 1
    ):
        return None
    return canonical_clone_v1(previous_owner)


def _page_segments(
    page: Mapping[str, Any],
    semantic: Mapping[str, Any],
    spec: Mapping[str, Any],
    alias_index: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    result = []
    approximate_comparisons = 0
    for layout in spec["layout_modes"]:
        groups = _role_groups(page, semantic, spec, layout)
        lower_bound = 0
        previous_group: list[dict[str, Any]] | None = None
        previous_owner: dict[str, Any] | None = None
        for group_ordinal, group in enumerate(groups):
            top = min(item["bbox"][1] for item in group)
            following_group_tops = [
                min(item["bbox"][1] for item in following)
                for following in groups[group_ordinal + 1 :]
                if min(item["bbox"][1] for item in following) > top
            ]
            upper_bound = min(following_group_tops) if following_group_tops else None
            owner = _owner_for(
                semantic["owners"],
                top=top,
                scale=median_text_height_v1(page["lines"]),
                maximum_lines=spec["limits"]["max_owner_distance_lines"],
            )
            if owner is None and previous_group is not None and previous_owner is not None:
                owner = _same_page_repeated_block_owner(
                    page,
                    semantic,
                    spec,
                    previous_group,
                    group,
                    previous_owner,
                    lower_bound=lower_bound,
                    layout=layout,
                )
            if owner is None:
                previous_group = None
                previous_owner = None
                lower_bound = max(item["bbox"][3] for item in group)
                continue
            result_start = len(result)
            group_semantic = canonical_clone_v1(semantic)
            if layout == "ROLES_AS_ROWS":
                lane_scopes, lane_comparisons = _lane_scope_candidates(
                    page,
                    spec,
                    alias_index,
                    group,
                    owner,
                    lower_bound=lower_bound,
                )
                approximate_comparisons += lane_comparisons
            else:
                lane_scopes = []
            combined_scopes = [*semantic["scopes"], *lane_scopes]
            selected_scopes: list[dict[str, Any]] = []
            for candidate in sorted(
                combined_scopes,
                key=lambda item: (
                    0 if type(item.get("lane_axis_center_x2")) is int else 1,
                    item["bbox"][1],
                    _scope_center(item),
                ),
            ):
                if any(
                    candidate["scope_id"] == selected["scope_id"]
                    and abs(_scope_center(candidate) - _scope_center(selected))
                    <= median_text_height_v1(page["lines"]) * 1.5
                    and set(candidate["source_line_indices_in_visual_order"])
                    & set(selected["source_line_indices_in_visual_order"])
                    for selected in selected_scopes
                ):
                    continue
                selected_scopes.append(candidate)
            group_semantic["scopes"] = selected_scopes
            scopes = _scope_candidates(
                group_semantic["scopes"],
                group,
                owner,
                layout,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
            )
            for scope in scopes:
                region_bottom = max(scope["bbox"][3], max(item["bbox"][3] for item in group))
                if any(
                    owner["bbox"][3] < reset["bbox"][1] < region_bottom
                    for reset in semantic["resets"]
                ):
                    continue
                result.append(
                    _segment(
                        page,
                        group_semantic,
                        spec,
                        group,
                        scope,
                        owner,
                        layout,
                        lower_bound=lower_bound,
                        upper_bound=upper_bound,
                    )
                )
            if len(result) > result_start:
                previous_group = canonical_clone_v1(group)
                previous_owner = canonical_clone_v1(owner)
            else:
                previous_group = None
                previous_owner = None
            lower_bound = max(item["bbox"][3] for item in group)
    unique = {item["segment_id"]: item for item in result}
    return (
        sorted(
            unique.values(),
            key=lambda item: (
                item["page_sequences"],
                item["population_scope"]["match"]["bbox"][1],
                item["layout_mode"],
            ),
        ),
        approximate_comparisons,
    )


def _unit_key(segment: Mapping[str, Any]) -> tuple[Any, ...] | None:
    unit = segment["header_context"]["unit_resolution"]
    if unit is None:
        return None
    return (unit["unit_kind"], unit["currency"], unit["magnitude_power10"])


def _normalized_axis(
    segment: Mapping[str, Any], pages: Mapping[int, Mapping[str, Any]]
) -> list[int]:
    page = pages[segment["page_sequences"][0]]
    return [center * 500_000 // page["page_width"] for center in segment["axis_centers_x2"]]


def _axes_compatible(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    pages: Mapping[int, Mapping[str, Any]],
    tolerance: int,
) -> bool:
    left_axis = _normalized_axis(left, pages)
    right_axis = _normalized_axis(right, pages)
    return len(left_axis) == len(right_axis) and all(
        abs(a - b) <= tolerance for a, b in zip(left_axis, right_axis, strict=True)
    )


def _compatible_complete(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    pages: Mapping[int, Mapping[str, Any]],
    spec: Mapping[str, Any],
    semantic_by_page: Mapping[int, Mapping[str, Any]],
) -> bool:
    left_page = left["page_sequences"][-1]
    right_page = right["page_sequences"][0]
    if right_page != left_page + 1:
        return False
    right_bottom = max(
        [item["bbox"][3] for item in right["role_matches"]]
        + [right["population_scope"]["match"]["bbox"][3]]
    )
    if any(reset["bbox"][1] <= right_bottom for reset in semantic_by_page[right_page]["resets"]):
        return False
    left_unit = _unit_key(left)
    right_unit = _unit_key(right)
    if (
        left["segment_status"] != "COMPLETE_TARGET_SCOPE_STRUCTURE_NO_NUMERIC_AUTHORITY"
        or right["segment_status"] != left["segment_status"]
        or left["layout_mode"] != right["layout_mode"]
        or left["population_scope"]["scope_id"] != right["population_scope"]["scope_id"]
        or left["period_key"] is None
        or right["period_key"] is None
        or left["period_key"] == right["period_key"]
        or left_unit is None
        or left_unit != right_unit
    ):
        return False
    return _axes_compatible(left, right, pages, spec["limits"]["axis_tolerance_ppm"])


def _compatible_same_page_period_lane(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    pages: Mapping[int, Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> bool:
    """Prove two row-layout scope columns are period lanes of one table."""

    return (
        left["segment_status"] == "COMPLETE_TARGET_SCOPE_STRUCTURE_NO_NUMERIC_AUTHORITY"
        and right["segment_status"] == left["segment_status"]
        and left["layout_mode"] == right["layout_mode"] == "ROLES_AS_ROWS"
        and left["page_sequences"] == right["page_sequences"]
        and left["owner"]["match_id"] == right["owner"]["match_id"]
        and [item["match_id"] for item in left["role_matches"]]
        == [item["match_id"] for item in right["role_matches"]]
        and left["population_scope"]["scope_id"] == right["population_scope"]["scope_id"]
        and left["period_key"] is not None
        and right["period_key"] is not None
        and left["period_key"] != right["period_key"]
        and _unit_key(left) is not None
        and _unit_key(left) == _unit_key(right)
        and _axes_compatible(left, right, pages, spec["limits"]["axis_tolerance_ppm"])
    )


def _segment_body_vertical_bounds(segment: Mapping[str, Any]) -> tuple[int, int]:
    records = [segment["population_scope"]["match"], *segment["role_matches"]]
    if segment["trailing_total_match"] is not None:
        records.append(segment["trailing_total_match"])
    return min(item["bbox"][1] for item in records), max(item["bbox"][3] for item in records)


def _compatible_same_page_repeated_full_block(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    pages: Mapping[int, Mapping[str, Any]],
    spec: Mapping[str, Any],
    semantic_by_page: Mapping[int, Mapping[str, Any]],
) -> bool:
    if (
        left["segment_status"] != "COMPLETE_TARGET_SCOPE_STRUCTURE_NO_NUMERIC_AUTHORITY"
        or right["segment_status"] != left["segment_status"]
        or left["page_sequences"] != right["page_sequences"]
        or len(left["page_sequences"]) != 1
        or left["layout_mode"] != right["layout_mode"]
        or left["owner"]["match_id"] != right["owner"]["match_id"]
        or left["population_scope"]["scope_id"] != right["population_scope"]["scope_id"]
        or left["period_key"] is None
        or right["period_key"] is None
        or left["period_key"] == right["period_key"]
        or _unit_key(left) is None
        or _unit_key(left) != _unit_key(right)
        or [item["semantic_id"] for item in left["role_matches"]]
        != [item["semantic_id"] for item in right["role_matches"]]
        or {item["match_id"] for item in left["role_matches"]}
        & {item["match_id"] for item in right["role_matches"]}
        or not _axes_compatible(left, right, pages, spec["limits"]["axis_tolerance_ppm"])
    ):
        return False
    first, second = sorted((left, right), key=_segment_body_vertical_bounds)
    first_top, first_bottom = _segment_body_vertical_bounds(first)
    second_top, second_bottom = _segment_body_vertical_bounds(second)
    page_sequence = first["page_sequences"][0]
    scale = median_text_height_v1(pages[page_sequence]["lines"])
    if (
        first_top >= second_top
        or first_bottom > second_top + scale * 0.2
        or second_bottom - first_top > scale * spec["limits"]["max_owner_distance_lines"] * 2
    ):
        return False
    return not any(
        first_bottom < reset["bbox"][1] < second_top
        for reset in semantic_by_page[page_sequence]["resets"]
    )


def _compatible_same_page_complete(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    pages: Mapping[int, Mapping[str, Any]],
    spec: Mapping[str, Any],
    semantic_by_page: Mapping[int, Mapping[str, Any]],
) -> bool:
    return _compatible_same_page_period_lane(left, right, pages, spec) or (
        _compatible_same_page_repeated_full_block(left, right, pages, spec, semantic_by_page)
    )


def _bind_period_lanes(segments: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    def period_order(value: str) -> tuple[int, Any]:
        try:
            return 1, datetime.strptime(value, "%d/%m/%Y").date().toordinal()
        except ValueError:
            return 0, value

    periods = sorted(
        {item["period_key"] for item in segments if item["period_key"] is not None},
        key=period_order,
        reverse=True,
    )
    lane_by_period = {period: ordinal for ordinal, period in enumerate(periods)}
    result = []
    for source_segment_ordinal, raw in enumerate(segments):
        segment = canonical_clone_v1(raw)
        source_segment_id = segment.pop("segment_id")
        period_lane = lane_by_period.get(segment["period_key"])
        if period_lane is None and len(segments) == 1:
            period_lane = 0
        cells = []
        for raw_cell in segment["role_cells"]:
            cell = canonical_clone_v1(raw_cell)
            cell.pop("cell_id")
            cell["period_lane_index"] = period_lane
            cells.append({**cell, "cell_id": "astgv1:cell:" + canonical_json_sha256_v1(cell)})
        segment.update(
            {
                "period_lane_index": period_lane,
                "role_cells": cells,
                "source_physical_segment_id": source_segment_id,
                "source_segment_ordinal": source_segment_ordinal,
            }
        )
        total_cells = []
        for raw_cell in segment["trailing_total_cells"]:
            cell = canonical_clone_v1(raw_cell)
            cell.pop("cell_id")
            cell["period_lane_index"] = period_lane
            total_cells.append({**cell, "cell_id": "astgv1:cell:" + canonical_json_sha256_v1(cell)})
        segment["trailing_total_cells"] = total_cells
        result.append(
            {**segment, "segment_id": "astgv1:segment:" + canonical_json_sha256_v1(segment)}
        )
    return result


def _logical_graph(segments: Sequence[Mapping[str, Any]], mode: str) -> dict[str, Any]:
    bound = _bind_period_lanes(segments)
    material = {
        "continuation": {
            "adjacent_geometry_relation_replay": "NOT_REQUIRED_COMPLETE_PHYSICAL_SEGMENTS",
            "mode": mode,
            "page_sequences": sorted(
                {page for segment in bound for page in segment["page_sequences"]}
            ),
            "partial_table_completion": mode == "ADJACENT_PARTIAL_ROLE_DEFICIT_COMPLETION",
        },
        "segments": bound,
        "status": "STRUCTURALLY_ACCEPTED_NO_NUMERIC_OR_MAPPING_AUTHORITY",
    }
    return {**material, "graph_id": "astgv1:graph:" + canonical_json_sha256_v1(material)}


def _group_complete_segments(
    segments: Sequence[Mapping[str, Any]],
    pages: Mapping[int, Mapping[str, Any]],
    spec: Mapping[str, Any],
    semantic_by_page: Mapping[int, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    exact = [
        item
        for item in segments
        if item["segment_status"] == "COMPLETE_TARGET_SCOPE_STRUCTURE_NO_NUMERIC_AUTHORITY"
    ]
    # First close repeated target scope columns on one page into a multi-period
    # physical table.  A duplicate/unresolved period remains separate so
    # document-level uniqueness fails closed.
    bundles: list[list[Mapping[str, Any]]] = []
    bundled: set[str] = set()
    for segment in exact:
        if segment["segment_id"] in bundled:
            continue
        candidates = [
            item
            for item in exact
            if item["segment_id"] not in bundled
            and _compatible_same_page_complete(segment, item, pages, spec, semantic_by_page)
        ]
        proposed = [segment, *candidates]
        periods = [item["period_key"] for item in proposed]
        if (
            len(proposed) > 1
            and len(periods) == len(set(periods))
            and all(
                _compatible_same_page_complete(left, right, pages, spec, semantic_by_page)
                for left in proposed
                for right in proposed
                if left is not right
            )
        ):
            bundle = proposed
        else:
            bundle = [segment]
        bundled.update(item["segment_id"] for item in bundle)
        bundles.append(bundle)
    bundles.sort(
        key=lambda group: (
            group[0]["page_sequences"][0],
            group[0]["population_scope"]["match"]["bbox"][1],
            group[0]["population_scope"]["match"]["bbox"][0],
        )
    )

    graphs = []
    unresolved_chains = []
    used_bundles: set[int] = set()
    for index, bundle in enumerate(bundles):
        if index in used_bundles:
            continue
        group = list(bundle)
        used_bundles.add(index)
        # Repeated full one-period pages may form an arbitrary-length adjacent
        # chain.  Compatibility is replayed at every edge and a reset ends it.
        if len(bundle) == 1:
            cursor = index
            while cursor + 1 < len(bundles) and len(bundles[cursor + 1]) == 1:
                candidate = bundles[cursor + 1][0]
                if not _compatible_complete(
                    group[-1], candidate, pages, spec, semantic_by_page
                ) or candidate["period_key"] in {item["period_key"] for item in group}:
                    break
                group.append(candidate)
                cursor += 1
                used_bundles.add(cursor)
        edge_count = len({item["page_sequences"][0] for item in group}) - 1
        if edge_count > spec["limits"]["continuation_page_budget"]:
            material = {
                "continuation_page_budget": spec["limits"]["continuation_page_budget"],
                "page_sequences": [item["page_sequences"][0] for item in group],
                "physical_segment_ids": [item["segment_id"] for item in group],
                "unresolved_reason": "ADJACENT_REPEATED_FULL_SEGMENT_CHAIN_BUDGET_EXHAUSTED",
            }
            unresolved_chains.append(
                {
                    **material,
                    "unresolved_chain_id": "astgv1:unresolved-chain:"
                    + canonical_json_sha256_v1(material),
                }
            )
            continue
        mode = (
            "ADJACENT_REPEATED_FULL_SEGMENTS_PERIOD_COMPLEMENT"
            if len({item["page_sequences"][0] for item in group}) > 1
            else "SINGLE_PAGE_MULTI_PERIOD_COMPLETE_SEGMENTS"
            if len(group) > 1
            else "SINGLE_PAGE_COMPLETE_SEGMENTS"
        )
        graphs.append(_logical_graph(group, mode))
    return graphs, unresolved_chains


def _partial_role_groups(
    page: Mapping[str, Any],
    semantic: Mapping[str, Any],
    spec: Mapping[str, Any],
    layout: str,
    complete_role_ids: set[str],
) -> list[list[dict[str, Any]]]:
    candidates = [
        match
        for role in spec["role_axis"]
        for match in semantic["roles"][role["role"]]
        if match["match_id"] not in complete_role_ids
    ]
    scale = median_text_height_v1(page["lines"])
    maximum_span = scale * spec["limits"]["max_role_gap_lines"]
    role_order = {item["role"]: ordinal for ordinal, item in enumerate(spec["role_axis"])}
    selected: list[list[dict[str, Any]]] = []
    used: set[str] = set()
    for seed in sorted(candidates, key=lambda item: (item["bbox"][1], item["bbox"][0])):
        if seed["match_id"] in used:
            continue
        compatible = []
        for candidate in candidates:
            if candidate["match_id"] in used:
                continue
            if layout == "ROLES_AS_COLUMNS":
                fits = abs(_center_y(candidate) - _center_y(seed)) <= scale * 0.78
            else:
                fits = abs(_center_y(candidate) - _center_y(seed)) <= maximum_span
            if fits:
                compatible.append(candidate)
        by_role: dict[str, dict[str, Any]] = {}
        for candidate in sorted(
            compatible,
            key=lambda item: (
                abs(_center_y(item) - _center_y(seed)),
                abs(_center_x(item) - _center_x(seed)),
            ),
        ):
            by_role.setdefault(candidate["semantic_id"], candidate)
        group = sorted(by_role.values(), key=lambda item: role_order[item["semantic_id"]])
        if not group or len(group) == len(spec["role_axis"]):
            continue
        used.update(item["match_id"] for item in group)
        selected.append([canonical_clone_v1(item) for item in group])
    return selected


def _partial_fragments(
    page: Mapping[str, Any], semantic: Mapping[str, Any], spec: Mapping[str, Any]
) -> list[dict[str, Any]]:
    complete_role_ids = {
        match["match_id"]
        for layout in spec["layout_modes"]
        for group in _role_groups(page, semantic, spec, layout)
        for match in group
    }
    target_scopes = [
        item for item in semantic["scopes"] if item["scope_id"] == spec["target_scope_id"]
    ]
    result = []
    scale = median_text_height_v1(page["lines"])
    for layout in spec["layout_modes"]:
        for role_group in _partial_role_groups(page, semantic, spec, layout, complete_role_ids):
            group_top = min(item["bbox"][1] for item in role_group)
            group_bottom = max(item["bbox"][3] for item in role_group)
            owner = _owner_for(
                semantic["owners"],
                top=group_top,
                scale=scale,
                maximum_lines=spec["limits"]["max_owner_distance_lines"],
            )
            if owner is None:
                continue
            compatible_scopes = [
                scope
                for scope in target_scopes
                if (
                    scope["bbox"][3] <= group_top
                    if layout == "ROLES_AS_ROWS"
                    else scope["bbox"][1] >= group_bottom
                )
            ]
            if not compatible_scopes:
                continue
            scope = min(
                compatible_scopes,
                key=lambda item: abs(
                    _center_y(item) - median(_center_y(role) for role in role_group)
                ),
            )
            centers = (
                [_center_x(scope)]
                if layout == "ROLES_AS_ROWS"
                else [_center_x(match) for match in role_group]
            )
            axis_signature = (
                {"TARGET_SCOPE": int(round(centers[0] * 1_000_000 / page["page_width"]))}
                if layout == "ROLES_AS_ROWS"
                else {
                    match["semantic_id"]: int(
                        round(_center_x(match) * 1_000_000 / page["page_width"])
                    )
                    for match in role_group
                }
            )
            start = owner["bbox"][3]
            stop = min(group_top, scope["bbox"][1])
            context = _header_context(page, start=start, stop=max(start + 1, stop), centers=centers)
            period = _period_resolution(context)
            material = {
                "axis_signature_ppm": axis_signature,
                "header_context": context,
                "layout_mode": layout,
                "observed_roles": [item["semantic_id"] for item in role_group],
                "owner": owner,
                "page_sequence": page["page_sequence"],
                **period,
                "role_matches": role_group,
                "scope_match": scope,
            }
            result.append(
                {
                    **material,
                    "partial_fragment_id": "astgv1:partial:" + canonical_json_sha256_v1(material),
                }
            )
    unique = {item["partial_fragment_id"]: item for item in result}
    return sorted(unique.values(), key=lambda item: (item["page_sequence"], item["layout_mode"]))


def _merge_partials(
    partials: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
    semantic_by_page: Mapping[int, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    graphs = []
    unresolved = []
    used: set[str] = set()
    required_roles = {item["role"] for item in spec["role_axis"]}
    budget = spec["limits"]["continuation_page_budget"]
    for left in partials:
        if left["partial_fragment_id"] in used:
            continue
        candidates = [
            right
            for right in partials
            if right["page_sequence"] > left["page_sequence"]
            and right["page_sequence"] - left["page_sequence"] <= budget
            and right["layout_mode"] == left["layout_mode"]
        ]
        merged = None
        reason = "CONTINUATION_BUDGET_EXHAUSTED_OR_NO_COMPATIBLE_ADJACENT_FRAGMENT"
        for right in candidates:
            if right["page_sequence"] != left["page_sequence"] + 1:
                continue
            right_semantic = semantic_by_page[right["page_sequence"]]
            right_bottom = max(
                [item["bbox"][3] for item in right["role_matches"]]
                + [right["scope_match"]["bbox"][3]]
            )
            if any(reset["bbox"][1] <= right_bottom for reset in right_semantic["resets"]):
                reason = "STRUCTURAL_RESET_BLOCKED_ADJACENT_COMPLETION"
                continue
            if (
                left["period_key"] is None
                or left["period_key"] != right["period_key"]
                or _unit_key({"header_context": left["header_context"]}) is None
                or _unit_key({"header_context": left["header_context"]})
                != _unit_key({"header_context": right["header_context"]})
            ):
                reason = "INCOMPATIBLE_PERIOD_OR_UNIT_BLOCKED_ADJACENT_COMPLETION"
                continue
            shared_axes = set(left["axis_signature_ppm"]) & set(right["axis_signature_ppm"])
            if not shared_axes or any(
                abs(left["axis_signature_ppm"][axis] - right["axis_signature_ppm"][axis])
                > spec["limits"]["axis_tolerance_ppm"]
                for axis in shared_axes
            ):
                reason = "INCOMPATIBLE_AXIS_BLOCKED_ADJACENT_COMPLETION"
                continue
            combined_roles = set(left["observed_roles"]) | set(right["observed_roles"])
            if combined_roles != required_roles or set(left["observed_roles"]) & set(
                right["observed_roles"]
            ):
                reason = "ROLE_DEFICIT_NOT_EXACTLY_FILLED"
                continue
            repeated_header = bool(right_semantic["continuations"] or right_semantic["owners"])
            if not repeated_header:
                reason = "NO_REPEATED_OR_CONTINUATION_HEADER"
                continue
            merged = right
            break
        if merged is None:
            record = {**canonical_clone_v1(left), "unresolved_reason": reason}
            unresolved.append(record)
            continue
        used.update({left["partial_fragment_id"], merged["partial_fragment_id"]})
        material = {
            "continuation": {
                "adjacent_geometry_relation_replay": (
                    "REQUIRED_BEFORE_MAPPING_OR_EXPORT_"
                    + ADJACENT_PAGE_TABLE_GEOMETRY_FORMAT_VERSION_V1
                ),
                "mode": "ADJACENT_PARTIAL_ROLE_DEFICIT_COMPLETION",
                "page_sequences": [left["page_sequence"], merged["page_sequence"]],
                "partial_table_completion": True,
            },
            "partial_fragments": [canonical_clone_v1(left), canonical_clone_v1(merged)],
            "period_lane_index": 0,
            "resolved_period": left["period_key"],
            "status": "SEMANTIC_AXIS_CANDIDATE_REQUIRES_SHARED_ADJACENT_GEOMETRY_REPLAY",
        }
        graphs.append(
            {**material, "graph_id": "astgv1:graph:" + canonical_json_sha256_v1(material)}
        )
    for item in partials:
        if item["partial_fragment_id"] not in used and not any(
            record["partial_fragment_id"] == item["partial_fragment_id"] for record in unresolved
        ):
            unresolved.append(
                {
                    **canonical_clone_v1(item),
                    "unresolved_reason": (
                        "CONTINUATION_BUDGET_EXHAUSTED_OR_NO_COMPATIBLE_ADJACENT_FRAGMENT"
                    ),
                }
            )
    return graphs, unresolved, used


def _candidate_region_sequences(
    pages: Sequence[Mapping[str, Any]],
    prepared_by_page: Mapping[int, Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> tuple[set[int], set[int]]:
    """Expand proved owner+role pages through bounded, reset-fenced neighbors."""

    seeds = {
        sequence
        for sequence, prepared in prepared_by_page.items()
        if prepared["primary_candidate"] or prepared["rescue_candidate"]
    }
    candidates = set(seeds)
    page_sequences = {page["page_sequence"] for page in pages}
    budget = spec["limits"]["continuation_page_budget"]
    for seed in seeds:
        for direction in (-1, 1):
            for distance in range(1, budget + 1):
                sequence = seed + direction * distance
                if sequence not in page_sequences:
                    break
                candidates.add(sequence)
                if prepared_by_page[sequence]["has_reset"]:
                    break
    return candidates, seeds


def _semantic_region_index(
    pages: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
    alias_index: Mapping[str, Any],
    *,
    region_first: bool,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    """Index semantic text everywhere and run geometry only in proved regions."""

    if not region_first:
        semantic = {}
        primary_count = 0
        rescue_count = 0
        visual_window_count = 0
        for page in pages:
            prepared = _prepare_semantic_windows(page, spec, alias_index)
            primary_count += prepared["primary_candidate"]
            rescue_count += prepared["rescue_candidate"]
            visual_window_count += prepared["visual_window_count"]
            semantic[page["page_sequence"]] = _semantic_matches(
                page,
                spec,
                alias_index,
                prepared=prepared,
            )
        return semantic, {
            "candidate_line_count": sum(len(page["lines"]) for page in pages),
            "candidate_page_count": len(pages),
            "coarse_index_page_count": len(pages),
            "coarse_skipped_page_count": 0,
            "coarse_window_band_count": 0,
            "geometry_page_count": len(pages),
            "neighbor_page_count": 0,
            "primary_candidate_page_count": primary_count,
            "rescue_candidate_page_count": rescue_count,
            "source_line_count": sum(len(page["lines"]) for page in pages),
            "source_page_count": len(pages),
            "visual_window_count": visual_window_count,
            "wrapped_match_page_count": len(pages),
        }

    coarse_by_page = {
        page["page_sequence"]: _coarse_page_category_index(page, alias_index) for page in pages
    }
    coarse_candidate_sequences = {
        sequence for sequence, coarse in coarse_by_page.items() if coarse["candidate_possible"]
    }
    prepared_by_page: dict[int, dict[str, Any]] = {
        page["page_sequence"]: {
            "approximate_alias_comparison_count": 0,
            "has_reset": False,
            "owner_possible": False,
            "primary_candidate": False,
            "rescue_candidate": False,
            "role_possible": False,
            "scope_possible": False,
            "visual_window_count": 0,
        }
        for page in pages
    }
    retained_prepared: dict[int, dict[str, Any]] = {}
    pages_by_sequence = {page["page_sequence"]: page for page in pages}
    for sequence in sorted(coarse_candidate_sequences):
        page = pages_by_sequence[sequence]
        prepared = _prepare_semantic_windows(page, spec, alias_index)
        prepared_by_page[sequence] = {
            key: value for key, value in prepared.items() if key != "windows"
        }
        if prepared["primary_candidate"] or prepared["rescue_candidate"]:
            retained_prepared[sequence] = prepared
    # Reset-like footers are common and cannot make a page a global matcher
    # candidate.  Probe a reset only while walking the declared continuation
    # radius from one exact owner/role seed, and stop that walk at a proved
    # reset.  This retains the reset fence without scanning unrelated pages.
    wrapped_match_sequences = set(coarse_candidate_sequences)
    page_sequences = set(pages_by_sequence)
    budget = spec["limits"]["continuation_page_budget"]
    for seed in sorted(retained_prepared):
        for direction in (-1, 1):
            for distance in range(1, budget + 1):
                sequence = seed + direction * distance
                if sequence not in page_sequences:
                    break
                if (
                    coarse_by_page[sequence]["reset_possible"]
                    and sequence not in wrapped_match_sequences
                ):
                    prepared = _prepare_semantic_windows(
                        pages_by_sequence[sequence],
                        spec,
                        alias_index,
                    )
                    prepared_by_page[sequence] = {
                        key: value for key, value in prepared.items() if key != "windows"
                    }
                    wrapped_match_sequences.add(sequence)
                if prepared_by_page[sequence]["has_reset"]:
                    break
    candidate_sequences, seed_sequences = _candidate_region_sequences(
        pages,
        prepared_by_page,
        spec,
    )
    semantic: dict[int, dict[str, Any]] = {}
    for page in pages:
        sequence = page["page_sequence"]
        # Neighbor/reset pages remain in the bounded source region, but a page
        # without its own owner+role proof cannot produce this engine's local
        # segment or partial fragment.  Keep its exact matcher counts and skip
        # all match-record hashing and geometry.
        if sequence not in seed_sequences:
            semantic[sequence] = _empty_semantic_matches(spec, prepared_by_page[sequence])
            continue
        prepared = retained_prepared.get(sequence)
        if prepared is None:
            prepared = _prepare_semantic_windows(page, spec, alias_index)
        semantic[sequence] = _semantic_matches(
            page,
            spec,
            alias_index,
            prepared=prepared,
        )
    return semantic, {
        "candidate_line_count": sum(
            len(page["lines"]) for page in pages if page["page_sequence"] in candidate_sequences
        ),
        "candidate_page_count": len(candidate_sequences),
        "coarse_index_page_count": len(pages),
        "coarse_skipped_page_count": len(pages) - len(wrapped_match_sequences),
        "coarse_window_band_count": sum(
            coarse["window_band_count"] for coarse in coarse_by_page.values()
        ),
        "geometry_page_count": len(seed_sequences),
        "neighbor_page_count": len(candidate_sequences - seed_sequences),
        "primary_candidate_page_count": sum(
            prepared["primary_candidate"] for prepared in prepared_by_page.values()
        ),
        "rescue_candidate_page_count": sum(
            prepared["rescue_candidate"] for prepared in prepared_by_page.values()
        ),
        "source_line_count": sum(len(page["lines"]) for page in pages),
        "source_page_count": len(pages),
        "visual_window_count": sum(
            prepared["visual_window_count"] for prepared in prepared_by_page.values()
        ),
        "wrapped_match_page_count": len(wrapped_match_sequences),
    }


def _build_parsed(
    pages: list[dict[str, Any]],
    spec: dict[str, Any],
    *,
    region_first: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    alias_index = _compiled_alias_index(spec)
    by_page = {page["page_sequence"]: page for page in pages}
    semantic, telemetry = _semantic_region_index(
        pages,
        spec,
        alias_index,
        region_first=region_first,
    )
    segments = []
    lane_approximate_comparisons = 0
    for page in pages:
        page_segments, page_lane_comparisons = _page_segments(
            page,
            semantic[page["page_sequence"]],
            spec,
            alias_index,
        )
        segments.extend(page_segments)
        lane_approximate_comparisons += page_lane_comparisons
    graphs, unresolved_complete_chains = _group_complete_segments(segments, by_page, spec, semantic)
    partials = [
        fragment
        for page in pages
        for fragment in _partial_fragments(page, semantic[page["page_sequence"]], spec)
    ]
    partial_graphs, unresolved, _used = _merge_partials(partials, spec, semantic)
    graphs.extend(partial_graphs)
    segment_pages = {item["page_sequences"][0] for item in segments}
    partial_pages = {item["page_sequence"] for item in partials}
    branchless_candidates = []
    branchless_unresolved = []
    for page in pages:
        page_semantic = semantic[page["page_sequence"]]
        role_matches = [
            match
            for role_id, matches in page_semantic["roles"].items()
            for match in matches
            if role_id == match["semantic_id"]
        ]
        distinct_role_ids = {match["semantic_id"] for match in role_matches}
        if not page_semantic["owners"] or len(distinct_role_ids) < 2 or page_semantic["scopes"]:
            continue
        branchless_candidates.append(page["page_sequence"])
        # A branchless page may still resolve a safe lane-derived scope inside
        # `_page_segments`.  Persist fail-closed evidence only when neither
        # physical geometry nor a partial fragment consumed the page.
        if page["page_sequence"] in segment_pages or page["page_sequence"] in partial_pages:
            continue
        branchless_material = {
            "owner_matches": canonical_clone_v1(page_semantic["owners"]),
            "page_sequence": page["page_sequence"],
            "role_matches": canonical_clone_v1(
                sorted(
                    role_matches,
                    key=lambda item: (
                        item["semantic_id"],
                        item["bbox"][1],
                        item["bbox"][0],
                        item["match_id"],
                    ),
                )
            ),
            "unresolved_reason": "BRANCHLESS_OWNER_MULTIROLE_SCOPE_MISSING",
        }
        branchless_unresolved.append(
            {
                **branchless_material,
                "unresolved_fragment_id": "astgv1:unresolved:"
                + canonical_json_sha256_v1(branchless_material),
            }
        )
    telemetry["rescue_candidate_page_count"] = len(branchless_candidates)
    bounded_absences = [
        item for item in segments if item["segment_status"] == "HARD_VETO_SCOPE_BOUNDED_ABSENCE"
    ]
    unresolved_segments = [
        item for item in segments if item["segment_status"] == "UNRESOLVED_PHYSICAL_SEGMENT"
    ]
    metrics = {
        "bounded_absence_count": len(bounded_absences),
        "complete_graph_count": len(graphs),
        "page_count": len(pages),
        "partial_completion_graph_count": sum(
            graph["continuation"]["partial_table_completion"] for graph in graphs
        ),
        "physical_segment_count": len(segments),
        "repeated_full_period_complement_graph_count": sum(
            graph["continuation"]["mode"] == "ADJACENT_REPEATED_FULL_SEGMENTS_PERIOD_COMPLEMENT"
            for graph in graphs
        ),
        "unresolved_fragment_count": (
            len(unresolved)
            + len(unresolved_segments)
            + len(unresolved_complete_chains)
            + len(branchless_unresolved)
        ),
    }
    material = {
        "bounded_absences": bounded_absences,
        "claim_boundary": CLAIM_BOUNDARY,
        "evidence_binding": {
            "page_evidence_sha256": canonical_json_sha256_v1(pages),
            "spec_id": "astgv1:spec:" + canonical_json_sha256_v1(spec),
        },
        "family_id": spec["family_id"],
        "format_version": FORMAT_VERSION,
        "graphs": sorted(graphs, key=lambda item: item["graph_id"]),
        "matcher_metrics": {
            "approximate_alias_comparison_count": (
                sum(
                    item["matcher_metrics"]["approximate_alias_comparison_count"]
                    for item in semantic.values()
                )
                + lane_approximate_comparisons
            ),
            "coarse_index_page_count": telemetry["coarse_index_page_count"],
            "coarse_skipped_page_count": telemetry["coarse_skipped_page_count"],
            "compiled_alias_count": len(alias_index["entries"]),
            "evaluation_format_version": _MATCHER_METRICS_FORMAT_VERSION,
            "lane_approximate_alias_comparison_count": lane_approximate_comparisons,
            "visual_window_count": sum(
                item["matcher_metrics"]["visual_window_count"] for item in semantic.values()
            ),
            "wrapped_match_page_count": telemetry["wrapped_match_page_count"],
        },
        "metrics": metrics,
        "physical_segments": segments,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "COMPLETE_REGION_GRAPH_ENUMERATION"
            if not unresolved
            and not unresolved_segments
            and not unresolved_complete_chains
            and not branchless_unresolved
            else "UNRESOLVED_REGION_GRAPH_ENUMERATION"
        ),
        "unresolved_fragments": [
            *unresolved,
            *unresolved_segments,
            *unresolved_complete_chains,
            *branchless_unresolved,
        ],
    }
    telemetry.update(
        {
            "build_cache_engine_revision": _ENGINE_CACHE_REVISION,
            "region_first": region_first,
            "surface_cache_hit_count": alias_index["surface_cache_hit_count"],
            "surface_cache_miss_count": alias_index["surface_cache_miss_count"],
        }
    )
    return (
        {**material, "result_id": "astgv1:result:" + canonical_json_sha256_v1(material)},
        telemetry,
    )


def _engine_trust_closure() -> tuple[Any, ...]:
    """Bind hot results to every replaceable shared dependency in this process."""

    return (
        _ENGINE_CACHE_REVISION,
        _build_parsed,
        _compiled_alias_index,
        _deletion_signatures,
        _edit_distance_at_most_one,
        _coarse_alias_possible,
        _coarse_ordered_alias_possible,
        _coarse_token_alias_index,
        _coarse_possible_evidence,
        _coarse_candidate_possible,
        _coarse_page_category_index,
        _semantic_region_index,
        _candidate_region_sequences,
        _surface_matches,
        _wrap_adjacency,
        _windows,
        _semantic_matches,
        _page_segments,
        _segment,
        _header_context,
        accounting_unit_surface_v1,
        extract_period_observations_v1,
        is_accounting_value_surface_v1,
        is_number_like_v1,
        build_multilevel_header_graph_v1,
        assign_value_row_lanes_v1,
        cluster_numeric_rows_v1,
        infer_numeric_column_centers_v1,
        propose_missing_value_lane_regions_v1,
        match_vietnamese_anchor_alias_v1,
        normalize_vietnamese_anchor_v1,
    )


def _cached_build_payload(
    pages_payload: bytes,
    spec_payload: bytes,
    engine_trust_closure: tuple[Any, ...],
) -> tuple[bytes, bytes, dict[str, Any]]:
    """Serialize cache decisions so hit attribution is exact under threads."""

    global _BUILD_CACHE_BYTES, _BUILD_CACHE_BYPASSES, _BUILD_CACHE_EVICTIONS
    global _BUILD_CACHE_HITS, _BUILD_CACHE_MISSES
    if not engine_trust_closure or engine_trust_closure[0] != _ENGINE_CACHE_REVISION:
        raise _error("scoped-table graph cache engine trust closure drifted")
    key = (pages_payload, spec_payload, engine_trust_closure)
    with _BUILD_CACHE_LOCK:
        cached = _BUILD_CACHE.pop(key, None)
        if cached is not None:
            _BUILD_CACHE[key] = cached
            _BUILD_CACHE_HITS += 1
            return (
                cached[0],
                cached[1],
                {
                    "admitted_this_call": False,
                    "bypassed_oversized": False,
                    "entry_payload_bytes": cached[2],
                    "entry_resident": True,
                    "evictions": _BUILD_CACHE_EVICTIONS,
                    "hit": True,
                    "hits": _BUILD_CACHE_HITS,
                    "misses": _BUILD_CACHE_MISSES,
                    "oversized_bypasses": _BUILD_CACHE_BYPASSES,
                    "retained_payload_bytes": _BUILD_CACHE_BYTES,
                    "size": len(_BUILD_CACHE),
                },
            )
        pages = decode_canonical_json_bytes_v1(pages_payload)
        spec = decode_canonical_json_bytes_v1(spec_payload)
        result, telemetry = _build_parsed(pages, spec, region_first=True)
        result_payload = canonical_json_bytes_v1(result)
        telemetry_payload = canonical_json_bytes_v1(telemetry)
        entry_payload_bytes = (
            len(pages_payload) + len(spec_payload) + len(result_payload) + len(telemetry_payload)
        )
        _BUILD_CACHE_MISSES += 1
        admitted = entry_payload_bytes <= _BUILD_CACHE_MAX_BYTES
        if admitted:
            while _BUILD_CACHE and (
                len(_BUILD_CACHE) >= _BUILD_CACHE_MAXSIZE
                or _BUILD_CACHE_BYTES + entry_payload_bytes > _BUILD_CACHE_MAX_BYTES
            ):
                _evicted_key, evicted = _BUILD_CACHE.popitem(last=False)
                _BUILD_CACHE_BYTES -= evicted[2]
                _BUILD_CACHE_EVICTIONS += 1
            cached = (result_payload, telemetry_payload, entry_payload_bytes)
            _BUILD_CACHE[key] = cached
            _BUILD_CACHE_BYTES += entry_payload_bytes
        else:
            _BUILD_CACHE_BYPASSES += 1
        return (
            result_payload,
            telemetry_payload,
            {
                "admitted_this_call": admitted,
                "bypassed_oversized": not admitted,
                "entry_payload_bytes": entry_payload_bytes,
                "entry_resident": admitted,
                "evictions": _BUILD_CACHE_EVICTIONS,
                "hit": False,
                "hits": _BUILD_CACHE_HITS,
                "misses": _BUILD_CACHE_MISSES,
                "oversized_bypasses": _BUILD_CACHE_BYPASSES,
                "retained_payload_bytes": _BUILD_CACHE_BYTES,
                "size": len(_BUILD_CACHE),
            },
        )


def _build(region_pages: Any, family_spec: Any) -> dict[str, Any]:
    pages = _pages(region_pages)
    spec = _spec(family_spec)
    pages_payload = canonical_json_bytes_v1(pages)
    spec_payload = canonical_json_bytes_v1(spec)
    result_payload, telemetry_payload, cache = _cached_build_payload(
        pages_payload,
        spec_payload,
        _engine_trust_closure(),
    )
    telemetry = decode_canonical_json_bytes_v1(telemetry_payload)
    telemetry.update(
        {
            "authoritative_replay_rebuilt": False,
            "build_cache_admitted_this_call": cache["admitted_this_call"],
            "build_cache_bypassed_authoritative_replay": False,
            "build_cache_bypassed_oversized": cache["bypassed_oversized"],
            "build_cache_entry_payload_bytes": cache["entry_payload_bytes"],
            "build_cache_entry_resident": cache["entry_resident"],
            "build_cache_evictions": cache["evictions"],
            "build_cache_hit": cache["hit"],
            "build_cache_hits": cache["hits"],
            "build_cache_max_bytes": _BUILD_CACHE_MAX_BYTES,
            "build_cache_maxsize": _BUILD_CACHE_MAXSIZE,
            "build_cache_misses": cache["misses"],
            "build_cache_oversized_bypasses": cache["oversized_bypasses"],
            "build_cache_retained_payload_bytes": cache["retained_payload_bytes"],
            "build_cache_size": cache["size"],
        }
    )
    _LAST_BUILD_TELEMETRY.set(telemetry)
    return decode_canonical_json_bytes_v1(result_payload)


def _build_exhaustive_for_test(region_pages: Any, family_spec: Any) -> dict[str, Any]:
    """Reference path for byte-equivalence falsifiers; never a public authority."""

    result, _telemetry = _build_parsed(
        _pages(region_pages),
        _spec(family_spec),
        region_first=False,
    )
    return result


def _accounting_scoped_table_graph_last_telemetry_v1() -> dict[str, Any]:
    value = _LAST_BUILD_TELEMETRY.get()
    return canonical_clone_v1(value) if value is not None else {}


def _clear_accounting_scoped_table_graph_caches_v1() -> None:
    """Bounded test/benchmark reset; it changes no source or public result."""

    global _BUILD_CACHE_BYTES, _BUILD_CACHE_BYPASSES, _BUILD_CACHE_EVICTIONS
    global _BUILD_CACHE_HITS, _BUILD_CACHE_MISSES
    with _BUILD_CACHE_LOCK:
        _BUILD_CACHE.clear()
        _BUILD_CACHE_BYTES = 0
        _BUILD_CACHE_BYPASSES = 0
        _BUILD_CACHE_EVICTIONS = 0
        _BUILD_CACHE_HITS = 0
        _BUILD_CACHE_MISSES = 0
    _accented_surface_cached.cache_clear()
    _accentless_surface_cached.cache_clear()
    _semantic_prefix_cached.cache_clear()
    _qgrams_cached.cache_clear()
    _is_value_surfaces_cached.cache_clear()
    _LAST_BUILD_TELEMETRY.set(None)


def build_accounting_scoped_table_graph_v1(
    region_pages: Sequence[Mapping[str, Any]], family_spec: Mapping[str, Any]
) -> dict[str, Any]:
    """Build a schema-neutral scoped-table graph from bounded page regions."""

    return _build(region_pages, family_spec)


def validate_accounting_scoped_table_graph_replay_v1(
    value: Any,
    region_pages: Sequence[Mapping[str, Any]],
    family_spec: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild every match, geometry proposal, grouping, and identity exactly."""

    if type(value) is not dict or value.get("format_version") != FORMAT_VERSION:
        raise _error("scoped-table graph result identity drifted")
    identity = value.get("result_id")
    if type(identity) is not str:
        raise _error("scoped-table graph result ID drifted")
    material = canonical_clone_v1(value)
    material.pop("result_id", None)
    if identity != "astgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("scoped-table graph content identity drifted")
    rebuilt, telemetry = _build_parsed(
        _pages(region_pages),
        _spec(family_spec),
        region_first=True,
    )
    with _BUILD_CACHE_LOCK:
        cache_snapshot = {
            "evictions": _BUILD_CACHE_EVICTIONS,
            "hits": _BUILD_CACHE_HITS,
            "misses": _BUILD_CACHE_MISSES,
            "oversized_bypasses": _BUILD_CACHE_BYPASSES,
            "retained_payload_bytes": _BUILD_CACHE_BYTES,
            "size": len(_BUILD_CACHE),
        }
    telemetry.update(
        {
            "authoritative_replay_rebuilt": True,
            "build_cache_admitted_this_call": False,
            "build_cache_bypassed_authoritative_replay": True,
            "build_cache_bypassed_oversized": False,
            "build_cache_entry_payload_bytes": 0,
            "build_cache_entry_resident": False,
            "build_cache_evictions": cache_snapshot["evictions"],
            "build_cache_hit": False,
            "build_cache_hits": cache_snapshot["hits"],
            "build_cache_max_bytes": _BUILD_CACHE_MAX_BYTES,
            "build_cache_maxsize": _BUILD_CACHE_MAXSIZE,
            "build_cache_misses": cache_snapshot["misses"],
            "build_cache_oversized_bypasses": cache_snapshot["oversized_bypasses"],
            "build_cache_retained_payload_bytes": cache_snapshot["retained_payload_bytes"],
            "build_cache_size": cache_snapshot["size"],
        }
    )
    _LAST_BUILD_TELEMETRY.set(telemetry)
    if not same_typed_json_v1(value, rebuilt):
        raise _error("scoped-table graph does not replay exactly")
    return rebuilt
