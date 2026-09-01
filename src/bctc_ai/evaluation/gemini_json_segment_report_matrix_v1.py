"""Generic consolidated segment-report matrices over selected Gemini JSON.

Gemini remains a source transcription layer.  This module derives period,
unit, branch, segment and metric graphs from the selected canonical JSON and
emits schema proposals only for exact visible intersections.  It contains no
bank, filename, page, note-number, value or OCR routing rules.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import _money
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_EQUITY_MATRIX_ACCOUNTING_FAMILY_V1"
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_CONSOLIDATED_SEGMENT_REPORT_MATRIX_"
    "EXPLICIT_OWNER_AND_SCOPE_RESET_FENCE_EXHAUSTIVE_VISIBLE_SEGMENT_AXIS_"
    "SOURCE_ONLY_AXES_CONSUMED_VISIBLE_TOTALS_VALIDATED_SOURCE_BLANKS_PRESERVED_"
    "STRUCTURAL_BRANCH_ROOT_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_OCR_GEOMETRY_BANK_"
    "FILE_PAGE_NOTE_VALUE_ROUTING_BACKSOLVE_OR_EXPORT_AUTHORITY"
)

_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_ROW_ID = re.compile(r"r[1-9][0-9]*\Z")
_COLUMN_ID = re.compile(r"c[1-9][0-9]*\Z")
_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_DATE_DMY = re.compile(r"(?<!\d)([0-3]?\d)[./-]([01]?\d)[./-]((?:19|20)\d{2})(?!\d)")
_DATE_WORDS = re.compile(r"(?<!\d)([0-3]?\d)\s+thang\s+([01]?\d)\s+nam\s+((?:19|20)\d{2})(?!\d)")
_ORDINAL = re.compile(r"^\s*(?:\(?[0-9ivxlcdm]+(?:\.[0-9ivxlcdm]+)*\)?(?:[.)-]\s*|\s+))", re.I)
_ORDINAL_ONLY = re.compile(r"^\s*\(?[0-9ivxlcdm]+(?:\.[0-9ivxlcdm]+)*\)?[.)-]?\s*$", re.I)
_TRAILING_FOOTNOTE = re.compile(
    r"\s*(?:\([0-9a-z*]+\)|\[[0-9a-z*]+\]|[\u00b9\u00b2\u00b3\u2070-\u2079]+)\s*$",
    re.I,
)
_TRAILING_NUMERIC_SUPERSCRIPT = re.compile(r"[¹²³⁰-⁹]+\s*$")
_UNICODE_ACCOUNTING_SIGNS = str.maketrans(
    {
        "−": "-",
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "﹣": "-",
        "－": "-",
    }
)
_GROUPED_INTEGER = re.compile(r"[0-9]{1,3}([., ])[0-9]{3}(?:\1[0-9]{3})*\Z")
_GENERIC_TOTAL_LABELS = {"", "cong", "subtotal", "tong", "tong cong"}


class GeminiJsonSegmentReportMatrixV1Error(ValueError):
    """The declarative segment graph or its replay drifted."""


def _error(message: str) -> GeminiJsonSegmentReportMatrixV1Error:
    return GeminiJsonSegmentReportMatrixV1Error(message)


def _norm(value: Any) -> str:
    return (
        normalize_vietnamese_anchor_v1(unicodedata.normalize("NFKC", value))
        if type(value) is str
        else ""
    )


def _norm_without_trailing_footnote(value: Any) -> str:
    if type(value) is not str:
        return ""
    return _norm(unicodedata.normalize("NFKC", _TRAILING_FOOTNOTE.sub("", value)))


def _norm_semantic_label(value: Any) -> str:
    if type(value) is not str:
        return ""
    without_footnote = _TRAILING_FOOTNOTE.sub("", value)
    normalized = unicodedata.normalize("NFKC", without_footnote)
    return _norm(_ORDINAL.sub("", normalized)).strip()


def _is_generic_total_label(value: Any) -> bool:
    folded = _norm_semantic_label(value)
    folded = re.sub(r"\bnam\s+20\d{2}\b|\b20\d{2}\b", " ", folded)
    return " ".join(folded.split()) in _GENERIC_TOTAL_LABELS


def _alias_match(value: Any, aliases: Sequence[str]) -> bool:
    folded = _norm_semantic_label(value)
    folded = re.sub(r"\s+(?:\*|[a-z])$", "", folded).strip()
    folded = re.sub(r"\bnam\s+20\d{2}\b|\b20\d{2}\b", " ", folded)
    folded = " ".join(folded.split())
    return folded in aliases


def _alias_map(value: Any, *, label: str) -> dict[str, list[str]]:
    if type(value) is not dict or not value:
        raise _error(f"segment-report {label} aliases are absent")
    result: dict[str, list[str]] = {}
    for role, raw in value.items():
        if (
            type(role) is not str
            or not role
            or type(raw) is not list
            or not raw
            or any(type(item) is not str or not item.strip() for item in raw)
        ):
            raise _error(f"segment-report {label} aliases are invalid")
        aliases = sorted({_norm(item) for item in raw})
        if not aliases:
            raise _error(f"segment-report {label} aliases normalize empty")
        result[role] = aliases
    owner_by_alias: dict[str, str] = {}
    for role, aliases in result.items():
        for alias in aliases:
            prior = owner_by_alias.setdefault(alias, role)
            if prior != role:
                raise _error(f"segment-report {label} alias is assigned to multiple roles")
    return result


def compile_gemini_json_segment_report_matrix_specs_v1(
    *, topology: Mapping[str, Any], evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile the strict, declarative segment-report triplet."""

    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec)
        != {"blank_zero_policy", "closure_policy", "family_id", "format_version", "matrix_policy"}
        or evaluation_spec.get("family_id") != topology.get("family_id")
        or evaluation_spec.get("blank_zero_policy") != "PRESERVE_SOURCE_BLANK_WITHOUT_BACKSOLVE"
        or evaluation_spec.get("closure_policy")
        != "MAP_EXACT_AXIS_METRIC_INTERSECTIONS_AND_VALIDATE_VISIBLE_TOTALS"
    ):
        raise _error("segment-report evaluation spec is invalid")
    policy = evaluation_spec["matrix_policy"]
    policy_fields = {
        "accepted_orientations",
        "branch_aliases",
        "business_axis_aliases",
        "consolidated_scope_aliases",
        "geographic_axis_aliases",
        "matrix_kind",
        "max_continuation_pages",
        "minimum_mapped_axis_roles",
        "separate_scope_aliases",
        "source_only_axis_aliases",
        "unit_bindings",
    }
    if (
        type(policy) is not dict
        or set(policy) != policy_fields
        or policy.get("matrix_kind") != "SEGMENT_REPORT_MATRIX"
        or policy.get("accepted_orientations") != ["METRIC_ROWS", "METRIC_COLUMNS"]
        or type(policy.get("max_continuation_pages")) is not int
        or not 1 <= policy["max_continuation_pages"] <= 24
        or type(policy.get("minimum_mapped_axis_roles")) is not int
        or policy["minimum_mapped_axis_roles"] < 1
    ):
        raise _error("segment-report matrix policy is invalid")
    normalized_scope_axes: dict[str, list[str]] = {}
    for field in ("consolidated_scope_aliases", "separate_scope_aliases"):
        raw_scope_aliases = policy.get(field)
        if (
            type(raw_scope_aliases) is not list
            or not raw_scope_aliases
            or any(type(item) is not str or not item.strip() for item in raw_scope_aliases)
        ):
            raise _error("segment-report scope aliases are invalid")
        normalized = [_norm(item) for item in raw_scope_aliases]
        if any(not item for item in normalized) or len(normalized) != len(set(normalized)):
            raise _error("segment-report scope aliases are duplicate or empty")
        normalized_scope_axes[field] = sorted(normalized)
    if set(normalized_scope_axes["consolidated_scope_aliases"]) & set(
        normalized_scope_axes["separate_scope_aliases"]
    ):
        raise _error("segment-report consolidated and separate scope aliases overlap")
    branch_aliases = _alias_map(policy["branch_aliases"], label="branch")
    business_axes = _alias_map(policy["business_axis_aliases"], label="business axis")
    geographic_axes = _alias_map(policy["geographic_axis_aliases"], label="geographic axis")
    cross_branch_axis_owner: dict[str, str] = {}
    for aliases_by_role in (business_axes, geographic_axes):
        for role, aliases in aliases_by_role.items():
            for alias in aliases:
                prior = cross_branch_axis_owner.setdefault(alias, role)
                if prior != role:
                    raise _error("segment-report axis alias changes role across branch projections")
    metric_aliases = {
        child["role"]: sorted(
            {
                _norm(alias)
                for matcher in child["matchers"]
                for alias in matcher["aliases"]
                if matcher["within_role"] is None
            }
        )
        for child in topology["children"]
    }
    if any(not aliases for aliases in metric_aliases.values()):
        raise _error("segment-report metric aliases are incomplete")
    metric_alias_owner: dict[str, str] = {}
    for role, aliases in metric_aliases.items():
        for alias in aliases:
            prior = metric_alias_owner.setdefault(alias, role)
            if prior != role:
                raise _error("segment-report metric alias is assigned to multiple roles")
    required_role_combinations = topology.get("required_role_combinations")
    if (
        type(required_role_combinations) is not list
        or not required_role_combinations
        or any(
            type(combo) is not list
            or not combo
            or len(combo) != len(set(combo))
            or any(role not in metric_aliases for role in combo)
            for combo in required_role_combinations
        )
    ):
        raise _error("segment-report required metric combinations are invalid")
    if (
        type(schema_binding_spec) is not dict
        or set(schema_binding_spec)
        != {
            "branch_bindings",
            "family_id",
            "family_root_report_norm_id",
            "format_version",
            "metric_offsets",
        }
        or schema_binding_spec.get("family_id") != topology.get("family_id")
        or type(schema_binding_spec.get("family_root_report_norm_id")) is not int
        or schema_binding_spec["family_root_report_norm_id"] <= 0
    ):
        raise _error("segment-report schema binding spec is invalid")
    offsets = schema_binding_spec["metric_offsets"]
    if (
        type(offsets) is not list
        or {item.get("role") for item in offsets if type(item) is dict} != set(metric_aliases)
        or any(
            type(item) is not dict
            or set(item) != {"offset", "role"}
            or type(item.get("offset")) is not int
            or item["offset"] <= 0
            for item in offsets
        )
        or len({item["offset"] for item in offsets}) != len(offsets)
    ):
        raise _error("segment-report metric offsets are invalid")
    metric_offset = {item["role"]: item["offset"] for item in offsets}
    branch_bindings: dict[str, dict[str, Any]] = {}
    for branch in schema_binding_spec["branch_bindings"]:
        if (
            type(branch) is not dict
            or set(branch) != {"axis_bindings", "branch_report_norm_id", "role"}
            or branch.get("role") not in branch_aliases
            or type(branch.get("branch_report_norm_id")) is not int
            or branch["branch_report_norm_id"] <= 0
            or type(branch.get("axis_bindings")) is not list
        ):
            raise _error("segment-report branch binding is invalid")
        if branch["role"] in branch_bindings:
            raise _error("segment-report branch binding is duplicate")
        expected_roles = set(business_axes if branch["role"] == "BUSINESS" else geographic_axes)
        axes = {}
        for item in branch["axis_bindings"]:
            if (
                type(item) is not dict
                or set(item) != {"parent_report_norm_id", "role"}
                or item.get("role") not in expected_roles
                or type(item.get("parent_report_norm_id")) is not int
                or item["parent_report_norm_id"] <= 0
                or item["role"] in axes
            ):
                raise _error("segment-report axis binding is invalid")
            axes[item["role"]] = item["parent_report_norm_id"]
        if set(axes) != expected_roles:
            raise _error("segment-report axis binding is incomplete")
        branch_bindings[branch["role"]] = {
            "axis_parent_report_norm_id_by_role": axes,
            "branch_report_norm_id": branch["branch_report_norm_id"],
        }
    if set(branch_bindings) != set(branch_aliases):
        raise _error("segment-report branch binding axis is incomplete")
    units = policy["unit_bindings"]
    if (
        type(units) is not list
        or not units
        or any(
            type(item) is not dict
            or set(item) != {"accepted", "aliases", "canonical_unit", "magnitude_power10"}
            or type(item.get("accepted")) is not bool
            or type(item.get("aliases")) is not list
            or not item["aliases"]
            or type(item.get("canonical_unit")) is not str
            or not item["canonical_unit"].strip()
            or type(item.get("magnitude_power10")) is not int
            or item["magnitude_power10"] < 0
            for item in units
        )
        or sum(item["accepted"] for item in units) != 1
    ):
        raise _error("segment-report unit bindings are invalid")
    canonical_unit_identities: dict[str, tuple[int, bool]] = {}
    unit_by_alias: dict[str, dict[str, Any]] = {}
    for item in units:
        canonical_unit = item["canonical_unit"].strip()
        identity = (item["magnitude_power10"], item["accepted"])
        prior_identity = canonical_unit_identities.get(canonical_unit)
        if prior_identity is not None:
            if prior_identity[0] != identity[0]:
                raise _error("segment-report canonical unit magnitude is ambiguous")
            if prior_identity[1] != identity[1]:
                raise _error("segment-report canonical unit acceptance is ambiguous")
            raise _error("segment-report canonical unit identity is duplicate")
        canonical_unit_identities[canonical_unit] = identity
        for raw_alias in item["aliases"]:
            alias = _norm(raw_alias)
            if not alias or alias in unit_by_alias:
                raise _error("segment-report unit alias is duplicate or empty")
            unit_by_alias[alias] = canonical_clone_v1(item)
    source_only = policy["source_only_axis_aliases"]
    if type(source_only) is not list or any(type(item) is not str for item in source_only):
        raise _error("segment-report source-only aliases are invalid")
    normalized_source_only = [_norm(item) for item in source_only]
    axis_alias_branches: dict[str, set[str]] = {}
    for branch, aliases_by_role in (
        ("BUSINESS", business_axes),
        ("GEOGRAPHIC", geographic_axes),
    ):
        for aliases in aliases_by_role.values():
            for alias in aliases:
                axis_alias_branches.setdefault(alias, set()).add(branch)
    if (
        any(not alias for alias in normalized_source_only)
        or len(normalized_source_only) != len(set(normalized_source_only))
        or any(len(axis_alias_branches.get(alias, set())) > 1 for alias in normalized_source_only)
    ):
        raise _error("segment-report source-only alias axis is ambiguous")
    schema_node_ids = [
        schema_binding_spec["family_root_report_norm_id"],
        *(branch["branch_report_norm_id"] for branch in branch_bindings.values()),
        *(
            parent
            for branch in branch_bindings.values()
            for parent in branch["axis_parent_report_norm_id_by_role"].values()
        ),
        *(
            parent + offset
            for branch in branch_bindings.values()
            for parent in branch["axis_parent_report_norm_id_by_role"].values()
            for offset in metric_offset.values()
        ),
    ]
    if len(schema_node_ids) != len(set(schema_node_ids)):
        raise _error("segment-report schema graph contains an RNID collision")
    query_policy = {
        "anchor_roles": sorted(metric_aliases),
        "branch_aliases": canonical_clone_v1(branch_aliases),
        "consolidated_scope_aliases": normalized_scope_axes["consolidated_scope_aliases"],
        "hard_negative_aliases": sorted({_norm(x) for x in topology["hard_negative_aliases"]}),
        "max_continuation_pages": policy["max_continuation_pages"],
        "owner_aliases": sorted({_norm(x) for x in topology["parent"]["aliases"]}),
        "separate_scope_aliases": normalized_scope_axes["separate_scope_aliases"],
        "structural_reset_aliases": sorted(
            {_norm(x) for x in topology["structural_reset_aliases"]}
        ),
    }
    return {
        "branch_aliases_by_role": branch_aliases,
        "branch_bindings_by_role": branch_bindings,
        "business_axis_aliases_by_role": business_axes,
        "claim_boundary": CLAIM_BOUNDARY,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "family_id": topology["family_id"],
        "family_root_report_norm_id": schema_binding_spec["family_root_report_norm_id"],
        "geographic_axis_aliases_by_role": geographic_axes,
        "metric_aliases_by_role": metric_aliases,
        "metric_offset_by_role": metric_offset,
        "minimum_mapped_axis_roles": policy["minimum_mapped_axis_roles"],
        "required_role_combinations": canonical_clone_v1(required_role_combinations),
        "query_policy": query_policy,
        "schema": canonical_clone_v1(schema_binding_spec),
        "segment_report_mode": True,
        "source_only_axis_aliases": sorted(normalized_source_only),
        "topology": canonical_clone_v1(topology),
        "unit_binding_by_alias": unit_by_alias,
        "unit_bindings": canonical_clone_v1(units),
    }


_REGION_FIELDS = {
    "document_id",
    "document_ordinal",
    "page_json_version_id",
    "physical_page",
    "selected_page_ordinal",
    "section_id",
    "source_logical_name",
    "source_sha256",
    "table_id",
}


def checked_segment_report_region_axis_v1(
    regions: Sequence[Mapping[str, Any]], *, max_regions: int = 128
) -> list[dict[str, Any]]:
    if type(regions) not in {list, tuple} or not 1 <= len(regions) <= max_regions:
        raise _error("segment-report region axis is absent or unbounded")
    result = []
    identity = None
    prior = None
    for region in regions:
        if (
            type(region) is not dict
            or set(region) != _REGION_FIELDS
            or _DOCUMENT_ID.fullmatch(region.get("document_id", "")) is None
            or _PAGE_VERSION.fullmatch(region.get("page_json_version_id", "")) is None
            or _SHA256.fullmatch(region.get("source_sha256", "")) is None
            or _SECTION_ID.fullmatch(region.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(region.get("table_id", "")) is None
            or any(
                type(region.get(k)) is not int or region[k] <= 0
                for k in ("document_ordinal", "physical_page", "selected_page_ordinal")
            )
            or type(region.get("source_logical_name")) is not str
            or not region["source_logical_name"]
        ):
            raise _error("segment-report source region is invalid")
        current_identity = tuple(
            region[k]
            for k in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        key = (
            region["selected_page_ordinal"],
            int(region["section_id"][1:]),
            int(region["table_id"][1:]),
        )
        if identity is None:
            identity = current_identity
        elif identity != current_identity:
            raise _error("segment-report regions cross document identity")
        if prior is not None and key <= prior:
            raise _error("segment-report regions are duplicate or unordered")
        prior = key
        result.append(canonical_clone_v1(region))
    return result


def build_segment_report_region_query_receipt_v1(
    regions: Sequence[Mapping[str, Any]], *, owner_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    checked = checked_segment_report_region_axis_v1(regions)
    if (
        type(owner_receipt) is not dict
        or owner_receipt.get("rule")
        != "EXPLICIT_CONSOLIDATED_SEGMENT_OWNER_RESET_FREE_MULTI_TABLE_INTERVAL"
    ):
        raise _error("segment-report owner receipt is invalid")
    payload = {
        "component_region_axis_sha256": canonical_json_sha256_v1(checked),
        "component_regions": checked,
        "owner_receipt": canonical_clone_v1(owner_receipt),
        "rule": "EXACT_SELECTED_SEGMENT_REPORT_FRAGMENTS_UNDER_ONE_RESET_FENCED_OWNER",
    }
    return {**payload, "query_receipt_sha256": canonical_json_sha256_v1(payload)}


def _surfaces(section: Mapping[str, Any], table: Mapping[str, Any] | None = None) -> list[str]:
    values = [section.get("title_exact")]
    narratives = section.get("narratives_exact")
    if type(narratives) is list:
        values.extend(narratives)
    if table is not None:
        values.extend([table.get("title_exact"), table.get("unit_exact")])
    return [value for value in values if type(value) is str and value.strip()]


def _contains(surface: Any, aliases: Sequence[str]) -> bool:
    folded = _norm(surface)
    return any(alias == folded or f" {alias} " in f" {folded} " for alias in aliases)


def _scope_states_from_surface_v1(
    surface: Any,
    *,
    consolidated_aliases: Sequence[str],
    separate_aliases: Sequence[str],
) -> list[str]:
    folded = _norm(surface)
    states = {
        state
        for state, aliases in (
            ("CONSOLIDATED", consolidated_aliases),
            ("SEPARATE_OR_PARENT", separate_aliases),
        )
        if _contains(surface, aliases)
    }
    # Canonical JSON often preserves the visible qualifier but varies the
    # formal title ("riêng", "riêng giữa niên độ", "công ty mẹ", ...).
    # Classify that bounded financial-statement grammar locally instead of
    # requiring Gemini to choose one exact configured spelling.
    financial_report = "bao cao" in folded and any(
        token in folded
        for token in (
            "tai chinh",
            "tinh hinh tai chinh",
            "ket qua hoat dong kinh doanh",
            "luu chuyen tien te",
        )
    )
    if financial_report and "hop nhat" in folded:
        states.add("CONSOLIDATED")
    if financial_report and (re.search(r"\brieng(?: le)?\b", folded) or "cong ty me" in folded):
        states.add("SEPARATE_OR_PARENT")
    return sorted(states)


def _statement_temporal_class_v1(statement_type: Any) -> str:
    folded = _norm(statement_type)
    if folded in {"balance sheet", "bao cao tinh hinh tai chinh"}:
        return "STOCK"
    if folded in {
        "cash flow",
        "cash flow statement",
        "income statement",
        "bao cao ket qua hoat dong kinh doanh",
        "bao cao luu chuyen tien te",
    }:
        return "FLOW"
    return "GENERAL"


def _metric_temporal_class_v1(metric_role: Any) -> str | None:
    if metric_role in {"ASSETS", "FIXED_ASSETS", "LIABILITIES"}:
        return "STOCK"
    if metric_role in {"REVENUE", "EXPENSE", "PROFIT_BEFORE_TAX"}:
        return "FLOW"
    return None


def _branch_and_axis_counts(
    table: Mapping[str, Any], section: Mapping[str, Any], compiled: Mapping[str, Any]
) -> tuple[list[str], dict[str, int]]:
    narratives = section.get("narratives_exact")
    surface_tiers = [
        [table.get("title_exact")],
        [section.get("title_exact")],
        narratives if type(narratives) is list else [],
    ]
    branches: list[str] = []
    for surfaces in surface_tiers:
        branches = [
            role
            for role, aliases in compiled["branch_aliases_by_role"].items()
            if any(_contains(surface, aliases) for surface in surfaces)
        ]
        if branches:
            break
    counts = {"BUSINESS": 0, "GEOGRAPHIC": 0}
    columns = table.get("columns") if type(table.get("columns")) is list else []
    rows = table.get("rows") if type(table.get("rows")) is list else []
    axis_surfaces = [
        member
        for column in columns
        for member in (column.get("header_path_exact") or [])
        if type(member) is str
    ] + [
        surface
        for row in rows
        for surface in [
            row.get("label_exact"),
            *(
                row.get("hierarchy_path_exact")
                if type(row.get("hierarchy_path_exact")) is list
                else []
            ),
        ]
        if type(surface) is str
    ]
    for branch, key in (
        ("BUSINESS", "business_axis_aliases_by_role"),
        ("GEOGRAPHIC", "geographic_axis_aliases_by_role"),
    ):
        counts[branch] = sum(bool(_axis_role(surface, compiled[key])) for surface in axis_surfaces)
    if not branches:
        best = max(counts.values())
        branches = [branch for branch, count in counts.items() if count == best and best > 0]
    return sorted(set(branches)), counts


def _branch_axis_evidence_v1(
    table: Mapping[str, Any], compiled: Mapping[str, Any]
) -> dict[str, Any]:
    columns = table.get("columns") if type(table.get("columns")) is list else []
    rows = table.get("rows") if type(table.get("rows")) is list else []
    surfaces = [
        member
        for column in columns
        for member in (column.get("header_path_exact") or [])
        if type(member) is str
    ] + [
        surface
        for row in rows
        for surface in [
            row.get("label_exact"),
            *(
                row.get("hierarchy_path_exact")
                if type(row.get("hierarchy_path_exact")) is list
                else []
            ),
        ]
        if type(surface) is str
    ]
    shared_axis: list[dict[str, Any]] = []
    exclusive_axis = {"BUSINESS": [], "GEOGRAPHIC": []}
    cross_branch_conflict: list[dict[str, Any]] = []
    for surface in surfaces:
        business_role = _axis_role(surface, compiled["business_axis_aliases_by_role"])
        geographic_role = _axis_role(surface, compiled["geographic_axis_aliases_by_role"])
        if business_role is not None and geographic_role is not None:
            item = {
                "business_role": business_role,
                "geographic_role": geographic_role,
                "source_exact": surface,
            }
            if business_role == geographic_role:
                shared_axis.append(item)
            else:
                cross_branch_conflict.append(item)
        elif business_role is not None:
            exclusive_axis["BUSINESS"].append({"axis_role": business_role, "source_exact": surface})
        elif geographic_role is not None:
            exclusive_axis["GEOGRAPHIC"].append(
                {"axis_role": geographic_role, "source_exact": surface}
            )
    return {
        "cross_branch_conflict_axis": cross_branch_conflict,
        "exclusive_axis_by_branch": exclusive_axis,
        "shared_axis": shared_axis,
    }


def _branch_authority_can_resolve_table_v1(
    *, branch_role: str, branches: Sequence[str], evidence: Mapping[str, Any]
) -> bool:
    if branch_role not in branches or len(branches) < 2:
        return False
    opposite = "GEOGRAPHIC" if branch_role == "BUSINESS" else "BUSINESS"
    exclusive = evidence.get("exclusive_axis_by_branch")
    return (
        type(exclusive) is dict
        and not exclusive.get(opposite)
        and not evidence.get("cross_branch_conflict_axis")
        and bool(evidence.get("shared_axis"))
    )


def _table_has_metric(table: Mapping[str, Any], compiled: Mapping[str, Any]) -> bool:
    rows = table.get("rows") if type(table.get("rows")) is list else []
    columns = table.get("columns") if type(table.get("columns")) is list else []
    surfaces = (
        [row.get("label_exact") for row in rows]
        + [
            member
            for row in rows
            for member in (
                row.get("hierarchy_path_exact")
                if type(row.get("hierarchy_path_exact")) is list
                else []
            )
        ]
        + [member for column in columns for member in (column.get("header_path_exact") or [])]
    )
    return any(
        _alias_match(surface, aliases)
        for surface in surfaces
        for aliases in compiled["metric_aliases_by_role"].values()
    )


def _selected_pages(value: Any) -> list[dict[str, Any]]:
    required = {
        "document_id",
        "document_ordinal",
        "page_json",
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
        "source_logical_name",
        "source_sha256",
    }
    if type(value) not in {list, tuple} or not value:
        raise _error("segment-report selected pages are absent")
    result = []
    identity = None
    prior = None
    for item in value:
        if (
            type(item) is not dict
            or set(item) != required
            or type(item.get("page_json")) is not dict
            or type(item["page_json"].get("sections")) is not list
        ):
            raise _error("segment-report selected page is invalid")
        current_identity = tuple(
            item[k]
            for k in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (item["selected_page_ordinal"], item["physical_page"])
        if identity is None:
            identity = current_identity
        elif identity != current_identity:
            raise _error("segment-report pages cross document")
        if prior is not None and position <= prior:
            raise _error("segment-report pages are unordered")
        identity, prior = current_identity, position
        result.append(canonical_clone_v1(item))
    return result


def coalesce_gemini_json_segment_report_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    pages = _selected_pages(page_records)
    first = pages[0]
    owner_aliases = compiled_specs["query_policy"]["owner_aliases"]
    scope_aliases = compiled_specs["query_policy"]["consolidated_scope_aliases"]
    separate_scope_aliases = compiled_specs["query_policy"]["separate_scope_aliases"]
    reset_aliases = compiled_specs["query_policy"]["structural_reset_aliases"]
    hard_aliases = compiled_specs["query_policy"]["hard_negative_aliases"]
    owners: list[dict[str, Any]] = []
    fallback_owners: list[dict[str, Any]] = []
    scopes: list[dict[str, Any]] = []
    scope_mentions: list[dict[str, Any]] = []
    branch_markers: list[dict[str, Any]] = []
    fences: list[dict[str, Any]] = []
    reporting_year_evidence: list[dict[str, Any]] = []
    reporting_period_evidence: list[dict[str, Any]] = []
    unit_context_inventory: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    page_completion_by_ordinal: dict[int, bool] = {}
    for page in pages:
        sections = page["page_json"]["sections"]
        completion = page["page_json"].get("completion")
        page_complete = (
            page["page_json"].get("status") != "UNRESOLVED_PAGE"
            and type(completion) is dict
            and completion.get("all_relevant_content_transcribed") is True
            and completion.get("uncertainty_exact") == []
        )
        page_completion_by_ordinal[page["selected_page_ordinal"]] = page_complete
        if page["page_json"].get("status") == "PRIMARY_FINANCIAL_STATEMENT":
            for section_ordinal, section in enumerate(sections, start=1):
                if type(section) is not dict:
                    continue
                section_id = f"s{section_ordinal}"
                primary_surfaces = [
                    {
                        "carrier_kind": "SECTION_TITLE",
                        "column_id": None,
                        "source_exact": section.get("title_exact"),
                        "table_id": None,
                        "table_ordinal": 0,
                    }
                ]
                for table_ordinal, table in enumerate(section.get("tables", []), start=1):
                    if type(table) is not dict:
                        continue
                    table_id = f"t{table_ordinal}"
                    primary_surfaces.append(
                        {
                            "carrier_kind": "TABLE_TITLE",
                            "column_id": None,
                            "source_exact": table.get("title_exact"),
                            "table_id": table_id,
                            "table_ordinal": table_ordinal,
                        }
                    )
                    for column_ordinal, column in enumerate(table.get("columns", []), start=1):
                        if type(column) is not dict:
                            continue
                        header_path = column.get("header_path_exact")
                        if type(header_path) is not list:
                            continue
                        members = [member for member in header_path if type(member) is str]
                        for source_exact in [*members, " ".join(members)]:
                            primary_surfaces.append(
                                {
                                    "carrier_kind": "COLUMN_HEADER_PATH",
                                    "column_id": f"c{column_ordinal}",
                                    "source_exact": source_exact,
                                    "table_id": table_id,
                                    "table_ordinal": table_ordinal,
                                }
                            )
                for carrier in primary_surfaces:
                    surface = carrier["source_exact"]
                    for year in _years([surface]):
                        reporting_year_evidence.append(
                            {
                                "physical_page": page["physical_page"],
                                "selected_page_ordinal": page["selected_page_ordinal"],
                                "section_id": section_id,
                                "source_exact": surface,
                                "table_ordinal": carrier["table_ordinal"],
                                "year": year,
                            }
                        )
                    for period_end in _period_ends(surface):
                        reporting_period_evidence.append(
                            {
                                **carrier,
                                "page_json_version_id": page["page_json_version_id"],
                                "period_end": period_end,
                                "physical_page": page["physical_page"],
                                "selected_page_ordinal": page["selected_page_ordinal"],
                                "section_id": section_id,
                                "statement_type": section.get("statement_type"),
                            }
                        )
        for section_ordinal, section in enumerate(sections, start=1):
            if type(section) is not dict:
                continue
            section_id = f"s{section_ordinal}"
            section_surfaces = [("SECTION_TITLE", section.get("title_exact"))]
            section_title = section.get("title_exact")
            section_context_authoritative = type(section_title) is str and (
                _contains(section_title, owner_aliases) or _contains(section_title, scope_aliases)
            )
            narratives = section.get("narratives_exact")
            if type(narratives) is list:
                section_surfaces.extend(("NARRATIVE", surface) for surface in narratives)
            for carrier_kind, surface in section_surfaces:
                if type(surface) is not str or not surface.strip():
                    continue
                marker = {
                    "carrier_kind": carrier_kind,
                    "content_kind": section.get("content_kind"),
                    "page_status": page["page_json"].get("status"),
                    "physical_page": page["physical_page"],
                    "section_id": section_id,
                    "selected_page_ordinal": page["selected_page_ordinal"],
                    "source_exact": surface,
                    "statement_type": section.get("statement_type"),
                    "table_ordinal": 0,
                }
                for unit_binding in (
                    _governed_context_unit_matches(
                        surface, compiled_specs, carrier_kind=carrier_kind
                    )
                    if section_context_authoritative
                    else []
                ):
                    unit_context_inventory.append(
                        {
                            "accepted": unit_binding["accepted"],
                            "canonical_unit": unit_binding["canonical_unit"],
                            "carrier_kind": carrier_kind,
                            "magnitude_power10": unit_binding["magnitude_power10"],
                            "page_json_version_id": page["page_json_version_id"],
                            "physical_page": page["physical_page"],
                            "section_id": section_id,
                            "selected_page_ordinal": page["selected_page_ordinal"],
                            "source_exact": surface,
                            "table_ordinal": 0,
                        }
                    )
                if _contains(surface, owner_aliases):
                    owners.append(marker)
                for branch_role, aliases in compiled_specs["branch_aliases_by_role"].items():
                    if _contains(surface, aliases):
                        branch_markers.append({**marker, "branch_role": branch_role})
                scope_states = _scope_states_from_surface_v1(
                    surface,
                    consolidated_aliases=scope_aliases,
                    separate_aliases=separate_scope_aliases,
                )
                for scope_state in scope_states:
                    scope_marker = {
                        **marker,
                        "carrier_kind": carrier_kind,
                        "scope_state": scope_state,
                    }
                    if carrier_kind == "SECTION_TITLE":
                        scopes.append(scope_marker)
                    else:
                        scope_mentions.append(scope_marker)
                if _contains(surface, reset_aliases + hard_aliases):
                    fences.append(marker)
            tables = section.get("tables") if type(section.get("tables")) is list else []
            for table_ordinal, table in enumerate(tables, start=1):
                if type(table) is not dict:
                    continue
                table_id = f"t{table_ordinal}"
                context_surfaces = _surfaces(section, table)
                table_surfaces = [
                    table["title_exact"]
                    for _ in (0,)
                    if type(table.get("title_exact")) is str and table["title_exact"].strip()
                ]
                marker = {
                    "carrier_kind": "TABLE_TITLE",
                    "content_kind": section.get("content_kind"),
                    "page_status": page["page_json"].get("status"),
                    "physical_page": page["physical_page"],
                    "section_id": section_id,
                    "selected_page_ordinal": page["selected_page_ordinal"],
                    "source_exact": table.get("title_exact"),
                    "statement_type": section.get("statement_type"),
                    "table_ordinal": table_ordinal,
                }
                table_branch_marker = any(
                    _contains(surface, aliases)
                    for surface in table_surfaces
                    for aliases in compiled_specs["branch_aliases_by_role"].values()
                )
                if (
                    any(_contains(s, owner_aliases) for s in table_surfaces)
                    and not table_branch_marker
                ):
                    owners.append(marker)
                elif table_branch_marker:
                    fallback_owners.append(marker)
                for scope_state in {
                    state
                    for surface in table_surfaces
                    for state in _scope_states_from_surface_v1(
                        surface,
                        consolidated_aliases=scope_aliases,
                        separate_aliases=separate_scope_aliases,
                    )
                }:
                    if table_surfaces:
                        scopes.append(
                            {
                                **marker,
                                "carrier_kind": "TABLE_TITLE",
                                "scope_state": scope_state,
                            }
                        )
                if any(_contains(s, reset_aliases + hard_aliases) for s in table_surfaces):
                    fences.append(marker)
                branches, counts = _branch_and_axis_counts(table, section, compiled_specs)
                branch_axis_evidence = _branch_axis_evidence_v1(table, compiled_specs)
                metric = _table_has_metric(table, compiled_specs)
                explicit_segment_context = any(
                    _contains(surface, owner_aliases)
                    or any(
                        _contains(surface, aliases)
                        for aliases in compiled_specs["branch_aliases_by_role"].values()
                    )
                    for surface in context_surfaces
                )
                inventory.append(
                    {
                        "axis_role_counts": counts,
                        "branch_axis_evidence": branch_axis_evidence,
                        "branch_candidates": branches,
                        "continuation": table.get("continuation"),
                        "document_id": page["document_id"],
                        "document_ordinal": page["document_ordinal"],
                        "page_json_version_id": page["page_json_version_id"],
                        "page_evidence_complete": page_complete,
                        "page_status": page["page_json"].get("status"),
                        "physical_page": page["physical_page"],
                        "explicit_segment_context": explicit_segment_context,
                        "metric_bearing": metric,
                        "role_bearing": False,
                        "section_id": section_id,
                        "selected_page_ordinal": page["selected_page_ordinal"],
                        "source_logical_name": page["source_logical_name"],
                        "source_sha256": page["source_sha256"],
                        "table_id": table_id,
                    }
                )
    strong_owner_axis = [
        item for item in owners if item.get("carrier_kind") != "NARRATIVE"
    ] + fallback_owners
    weak_owner_axis = [item for item in owners if item.get("carrier_kind") == "NARRATIVE"]
    explicit_pages = [
        item["selected_page_ordinal"]
        for item in inventory
        if item["metric_bearing"] and item["explicit_segment_context"]
    ]
    explicit_start = min(explicit_pages) if explicit_pages else None
    explicit_end = max(explicit_pages) if explicit_pages else None

    def source_position(item: Mapping[str, Any]) -> tuple[int, int, int]:
        table_id = item.get("table_id")
        return (
            item["selected_page_ordinal"],
            int(item["section_id"][1:]),
            item.get(
                "table_ordinal",
                int(table_id[1:]) if type(table_id) is str and table_id.startswith("t") else 0,
            ),
        )

    def scope_state_at(item: Mapping[str, Any]) -> str:
        preceding = [scope for scope in scopes if source_position(scope) <= source_position(item)]
        latest = max((source_position(scope) for scope in preceding), default=None)
        states = {scope["scope_state"] for scope in preceding if source_position(scope) == latest}
        return next(iter(states)) if len(states) == 1 else "AMBIGUOUS_OR_ABSENT"

    owner_continuation_by_inventory_id: dict[int, dict[str, Any]] = {}
    owner_branch_binding_by_inventory_id: dict[int, dict[str, Any]] = {}
    owner_branch_unresolved_by_inventory_id: dict[int, dict[str, Any]] = {}
    for item in sorted(inventory, key=source_position):
        if (
            item.get("continuation") not in {"CONTINUES_FROM_PREVIOUS_PAGE", "BOTH"}
            or not item["metric_bearing"]
            or max(item["axis_role_counts"].values()) < 2
            or scope_state_at(item) != "CONSOLIDATED"
        ):
            continue
        direct_owners = [
            owner
            for owner in strong_owner_axis
            if owner["selected_page_ordinal"] + 1 == item["selected_page_ordinal"]
            and owner["physical_page"] + 1 == item["physical_page"]
            and not any(
                source_position(owner) < source_position(fence) <= source_position(item)
                for fence in fences
            )
        ]
        latest_direct_position = max(
            (source_position(owner) for owner in direct_owners), default=None
        )
        direct_owner_axis = [
            owner for owner in direct_owners if source_position(owner) == latest_direct_position
        ]
        prior_chain = [
            candidate
            for candidate in inventory
            if id(candidate) in owner_continuation_by_inventory_id
            and candidate["selected_page_ordinal"] + 1 == item["selected_page_ordinal"]
            and candidate["physical_page"] + 1 == item["physical_page"]
            and not any(
                source_position(candidate) < source_position(marker) <= source_position(item)
                for marker in [*strong_owner_axis, *branch_markers, *fences]
            )
        ]
        inherited_axis = [
            {
                "branch_marker_axis": canonical_clone_v1(
                    owner_branch_binding_by_inventory_id.get(id(candidate), {}).get(
                        "branch_marker_axis", []
                    )
                ),
                "branch_role": candidate["branch_candidates"][0],
                "owner_marker": owner_continuation_by_inventory_id[id(candidate)],
            }
            for candidate in prior_chain
            if len(candidate["branch_candidates"]) == 1
        ]
        inherited_axis = list(
            {canonical_json_sha256_v1(binding): binding for binding in inherited_axis}.values()
        )
        owner_marker = direct_owner_axis[0] if len(direct_owner_axis) == 1 else None
        branch_marker_axis: list[dict[str, Any]] = []
        inherited_branch_role = None
        if owner_marker is not None:
            branch_marker_axis = [
                marker
                for marker in branch_markers
                if marker["selected_page_ordinal"] == owner_marker["selected_page_ordinal"]
                and marker["physical_page"] == owner_marker["physical_page"]
                and marker["section_id"] == owner_marker["section_id"]
            ]
        elif not direct_owner_axis and len(inherited_axis) == 1:
            inherited = inherited_axis[0]
            owner_marker = inherited["owner_marker"]
            branch_marker_axis = inherited["branch_marker_axis"]
            inherited_branch_role = inherited["branch_role"]
        if owner_marker is None:
            continue
        marker_roles = {marker["branch_role"] for marker in branch_marker_axis}
        marker_branch_role = next(iter(marker_roles)) if len(marker_roles) == 1 else None
        authority_branch_role = inherited_branch_role or marker_branch_role
        visible_branches = item["branch_candidates"]
        if len(visible_branches) == 1:
            branch_role = visible_branches[0]
            if authority_branch_role is not None and authority_branch_role != branch_role:
                continue
        elif authority_branch_role is not None and _branch_authority_can_resolve_table_v1(
            branch_role=authority_branch_role,
            branches=visible_branches,
            evidence=item["branch_axis_evidence"],
        ):
            branch_role = authority_branch_role
        else:
            owner_branch_unresolved_by_inventory_id[id(item)] = {
                "branch_marker_axis": canonical_clone_v1(branch_marker_axis),
                "owner_marker": canonical_clone_v1(owner_marker),
                "region": {key: item[key] for key in _REGION_FIELDS},
                "visible_branch_candidates": canonical_clone_v1(visible_branches),
            }
            continue
        owner_continuation_by_inventory_id[id(item)] = owner_marker
        if branch_marker_axis:
            owner_branch_binding_by_inventory_id[id(item)] = {
                "branch_marker_axis": canonical_clone_v1(branch_marker_axis),
                "branch_role": branch_role,
                "owner_marker": canonical_clone_v1(owner_marker),
                "region": {key: item[key] for key in _REGION_FIELDS},
                "rule": (
                    "COLOCATED_EXPLICIT_OWNER_BRANCH_MARKER_CARRIED_ACROSS_"
                    "PHYSICALLY_ADJACENT_CONTINUATION_CHAIN"
                ),
            }
        if visible_branches != [branch_role]:
            item["visible_branch_candidates"] = canonical_clone_v1(visible_branches)
            item["branch_candidates"] = [branch_role]

    incomplete_owner_markers = [
        item
        for item in [*strong_owner_axis, *weak_owner_axis]
        if not page_completion_by_ordinal.get(item["selected_page_ordinal"], False)
        and scope_state_at(item) != "SEPARATE_OR_PARENT"
    ]

    for item in inventory:
        preceding_item_scopes = [
            scope for scope in scopes if source_position(scope) <= source_position(item)
        ]
        item_scope_position = max(
            (source_position(scope) for scope in preceding_item_scopes), default=None
        )
        item_scope_axis = [
            scope
            for scope in preceding_item_scopes
            if source_position(scope) == item_scope_position
        ]
        item_scope_states = {scope["scope_state"] for scope in item_scope_axis}
        item["document_scope_carrier_axis"] = canonical_clone_v1(item_scope_axis)
        item["document_scope_state"] = (
            next(iter(item_scope_states)) if len(item_scope_states) == 1 else "AMBIGUOUS_OR_ABSENT"
        )
        same_page_owner = any(
            owner["selected_page_ordinal"] == item["selected_page_ordinal"]
            and source_position(owner) <= source_position(item)
            for owner in [*strong_owner_axis, *weak_owner_axis]
        )
        inside_explicit_segment_interval = (
            explicit_start is not None
            and explicit_end is not None
            and explicit_start <= item["selected_page_ordinal"] <= explicit_end
        )
        inside_owner_continuation = id(item) in owner_continuation_by_inventory_id
        semantic_role_bearing = item["metric_bearing"] and (
            item["explicit_segment_context"]
            or max(item["axis_role_counts"].values()) >= 2
            and (same_page_owner or inside_explicit_segment_interval or inside_owner_continuation)
        )
        item["role_bearing"] = (
            semantic_role_bearing and item["document_scope_state"] == "CONSOLIDATED"
        )
        item["scope_ambiguous_role_bearing"] = (
            semantic_role_bearing and item["document_scope_state"] == "AMBIGUOUS_OR_ABSENT"
        )
    selected_inventory = [item for item in inventory if item["role_bearing"]]
    incomplete_family_inventory = [
        item
        for item in inventory
        if not item["page_evidence_complete"]
        and item["document_scope_state"] != "SEPARATE_OR_PARENT"
        and (item["explicit_segment_context"] or max(item["axis_role_counts"].values()) >= 2)
    ]
    ambiguous_scope_inventory = [item for item in inventory if item["scope_ambiguous_role_bearing"]]
    owner_branch_unresolved_inventory = [
        item for item in inventory if id(item) in owner_branch_unresolved_by_inventory_id
    ]
    position_inventory = [
        *selected_inventory,
        *incomplete_family_inventory,
        *ambiguous_scope_inventory,
        *owner_branch_unresolved_inventory,
        *incomplete_owner_markers,
    ]
    reasons = []
    first_selected_position = (
        min(source_position(item) for item in position_inventory) if position_inventory else None
    )
    last_selected_position = (
        max(source_position(item) for item in position_inventory) if position_inventory else None
    )
    preceding_strong_owners = (
        [item for item in strong_owner_axis if source_position(item) <= first_selected_position]
        if first_selected_position is not None
        else []
    )
    preceding_weak_owners = (
        [item for item in weak_owner_axis if source_position(item) <= first_selected_position]
        if first_selected_position is not None
        else []
    )
    preceding_owners = preceding_strong_owners or preceding_weak_owners
    owner_start_position = max((source_position(item) for item in preceding_owners), default=None)
    if selected_inventory and not preceding_owners:
        reasons.append("EXPLICIT_SEGMENT_REPORT_OWNER_NOT_VISIBLE")
    preceding_scope_states = (
        [item for item in scopes if source_position(item) <= first_selected_position]
        if first_selected_position is not None
        else []
    )
    latest_scope_position = max(
        (source_position(item) for item in preceding_scope_states), default=None
    )
    active_scope_axis = [
        item for item in preceding_scope_states if source_position(item) == latest_scope_position
    ]
    active_scope_states = {item["scope_state"] for item in active_scope_axis}
    scope_state_conflict = len(active_scope_states) > 1
    if scope_state_conflict:
        reasons.append("SEGMENT_DOCUMENT_SCOPE_STATE_CONFLICT")
    if ambiguous_scope_inventory:
        reasons.append("SEGMENT_DOCUMENT_SCOPE_STATE_CONFLICT")
    if owner_branch_unresolved_inventory:
        reasons.append("SEGMENT_OWNER_BRANCH_AUTHORITY_CONTRADICTS_VISIBLE_TABLE_AXIS")
    preceding_scopes = [item for item in active_scope_axis if item["scope_state"] == "CONSOLIDATED"]
    outside_consolidated_scope = bool(
        position_inventory and active_scope_states != {"CONSOLIDATED"}
    )
    incomplete_control_scope = any(
        not page_completion_by_ordinal.get(item["selected_page_ordinal"], False)
        for item in active_scope_axis
    )
    incomplete_relevant_evidence = bool(
        incomplete_family_inventory or incomplete_owner_markers or incomplete_control_scope
    )
    if incomplete_family_inventory or incomplete_owner_markers or incomplete_control_scope:
        reasons.append("SELECTED_SEGMENT_PAGE_NOT_CANONICALLY_COMPLETE")
    if selected_inventory and any(
        len(item["branch_candidates"]) != 1 for item in selected_inventory
    ):
        reasons.append("SEGMENT_BRANCH_AMBIGUOUS")
    continuation_advisory_axis: list[dict[str, Any]] = []
    owner_continuation_axis = [
        {
            "owner_marker": canonical_clone_v1(owner_continuation_by_inventory_id[id(item)]),
            "region": {key: item[key] for key in _REGION_FIELDS},
            "rule": "PHYSICALLY_ADJACENT_FROM_PREVIOUS_TABLE_UNDER_OPEN_SEGMENT_OWNER",
        }
        for item in selected_inventory
        if id(item) in owner_continuation_by_inventory_id
    ]
    owner_branch_binding_axis = [
        canonical_clone_v1(owner_branch_binding_by_inventory_id[id(item)])
        for item in selected_inventory
        if id(item) in owner_branch_binding_by_inventory_id
    ]
    for item in selected_inventory:
        continuation = item.get("continuation")
        if continuation not in {
            "NONE",
            "CONTINUES_FROM_PREVIOUS_PAGE",
            "CONTINUES_ON_NEXT_PAGE",
            "BOTH",
        }:
            reasons.append("SEGMENT_TABLE_CONTINUATION_STATE_UNRESOLVED")
            continue
        if continuation in {"CONTINUES_FROM_PREVIOUS_PAGE", "BOTH"}:
            declared_prior_matches = [
                candidate
                for candidate in selected_inventory
                if candidate["selected_page_ordinal"] + 1 == item["selected_page_ordinal"]
                and candidate.get("continuation") in {"CONTINUES_ON_NEXT_PAGE", "BOTH"}
                and candidate.get("branch_candidates") == item.get("branch_candidates")
            ]
            physical_prior_matches = [
                candidate
                for candidate in declared_prior_matches
                if candidate["physical_page"] + 1 == item["physical_page"]
            ]
            if declared_prior_matches and (
                len(declared_prior_matches) != 1 or len(physical_prior_matches) != 1
            ):
                reasons.append("SEGMENT_TABLE_CONTINUATION_PREDECESSOR_MISSING")
            continuation_advisory_axis.append(
                {
                    "declared_direction": "FROM_PREVIOUS_PAGE",
                    "reciprocal_regions": [
                        {key: candidate[key] for key in _REGION_FIELDS}
                        for candidate in physical_prior_matches
                    ],
                    "region": {key: item[key] for key in _REGION_FIELDS},
                    "resolution": (
                        "RECIPROCAL_PHYSICALLY_ADJACENT_FRAGMENT"
                        if len(physical_prior_matches) == 1
                        else "UNPAIRED_DIRECTIONAL_ADVISORY_LOCAL_SEMANTIC_GATES_REQUIRED"
                        if not declared_prior_matches
                        else "DECLARED_PAIR_IS_NOT_UNIQUELY_PHYSICALLY_ADJACENT"
                    ),
                }
            )
        if continuation in {"CONTINUES_ON_NEXT_PAGE", "BOTH"}:
            declared_next_matches = [
                candidate
                for candidate in selected_inventory
                if item["selected_page_ordinal"] + 1 == candidate["selected_page_ordinal"]
                and candidate.get("continuation") in {"CONTINUES_FROM_PREVIOUS_PAGE", "BOTH"}
                and candidate.get("branch_candidates") == item.get("branch_candidates")
            ]
            physical_next_matches = [
                candidate
                for candidate in declared_next_matches
                if item["physical_page"] + 1 == candidate["physical_page"]
            ]
            if declared_next_matches and (
                len(declared_next_matches) != 1 or len(physical_next_matches) != 1
            ):
                reasons.append("SEGMENT_TABLE_CONTINUATION_SUCCESSOR_MISSING")
            continuation_advisory_axis.append(
                {
                    "declared_direction": "TO_NEXT_PAGE",
                    "reciprocal_regions": [
                        {key: candidate[key] for key in _REGION_FIELDS}
                        for candidate in physical_next_matches
                    ],
                    "region": {key: item[key] for key in _REGION_FIELDS},
                    "resolution": (
                        "RECIPROCAL_PHYSICALLY_ADJACENT_FRAGMENT"
                        if len(physical_next_matches) == 1
                        else "UNPAIRED_DIRECTIONAL_ADVISORY_LOCAL_SEMANTIC_GATES_REQUIRED"
                        if not declared_next_matches
                        else "DECLARED_PAIR_IS_NOT_UNIQUELY_PHYSICALLY_ADJACENT"
                    ),
                }
            )
    if selected_inventory:
        start = min(item["selected_page_ordinal"] for item in selected_inventory)
        end = max(item["selected_page_ordinal"] for item in selected_inventory)
        if any(
            not complete
            for ordinal, complete in page_completion_by_ordinal.items()
            if start <= ordinal <= end
        ):
            reasons.append("SELECTED_SEGMENT_PAGE_INTERVAL_NOT_CANONICALLY_COMPLETE")
            incomplete_relevant_evidence = True
        if end - start + 1 > compiled_specs["query_policy"]["max_continuation_pages"]:
            reasons.append("SEGMENT_REPORT_PAGE_SPAN_EXCEEDS_POLICY")
        owner_start = owner_start_position[0] if owner_start_position is not None else None
        if owner_start is None:
            reasons.append("OWNER_DOES_NOT_PRECEDE_SEGMENT_TABLES")
        elif any(
            owner_start_position <= source_position(item) <= last_selected_position
            for item in fences
        ):
            reasons.append("RESET_OR_HARD_NEGATIVE_INSIDE_OWNER_INTERVAL")
    else:
        owner_start_position = None
        owner_start = None
    scope_context_starts = [
        position
        for position in (owner_start_position, latest_scope_position)
        if position is not None
    ]
    scope_context_start = min(scope_context_starts) if scope_context_starts else None
    opposite_scope_mentions = [
        item
        for item in scope_mentions
        if item.get("scope_state") == "SEPARATE_OR_PARENT"
        and scope_context_start is not None
        and last_selected_position is not None
        and scope_context_start <= source_position(item) <= last_selected_position
        and _contains(item.get("source_exact"), owner_aliases)
    ]
    if selected_inventory and opposite_scope_mentions:
        reasons.append("SEGMENT_OPPOSITE_SCOPE_NARRATIVE_INSIDE_OWNER_INTERVAL")
    owner_receipt = None
    if preceding_owners and preceding_scopes and selected_inventory and owner_start is not None:
        owner_source_axis = strong_owner_axis if preceding_strong_owners else weak_owner_axis
        relevant_owners = [
            item
            for item in owner_source_axis
            if owner_start_position <= source_position(item) <= last_selected_position
        ]
        latest_scope_position = max(
            (source_position(item) for item in preceding_scopes), default=None
        )
        relevant_scopes = [
            item for item in preceding_scopes if source_position(item) == latest_scope_position
        ]
        relevant_fences = [
            item
            for item in fences
            if owner_start_position <= source_position(item) <= last_selected_position
        ]
        preceding_reporting_year_evidence = [
            item
            for item in reporting_year_evidence
            if source_position(item) <= first_selected_position
        ]
        complete_reporting_year_evidence = [
            item
            for item in preceding_reporting_year_evidence
            if page_completion_by_ordinal.get(item["selected_page_ordinal"], False)
        ]
        relevant_reporting_year_evidence = sorted(
            {
                canonical_json_sha256_v1(item): item for item in complete_reporting_year_evidence
            }.values(),
            key=canonical_json_sha256_v1,
        )
        preceding_reporting_period_evidence = [
            item
            for item in reporting_period_evidence
            if source_position(item) <= first_selected_position
        ]
        relevant_reporting_period_evidence = sorted(
            {
                canonical_json_sha256_v1(item): item
                for item in preceding_reporting_period_evidence
                if page_completion_by_ordinal.get(item["selected_page_ordinal"], False)
            }.values(),
            key=canonical_json_sha256_v1,
        )
        if (preceding_reporting_year_evidence or preceding_reporting_period_evidence) and not (
            relevant_reporting_year_evidence or relevant_reporting_period_evidence
        ):
            reasons.append("SELECTED_SEGMENT_PAGE_NOT_CANONICALLY_COMPLETE")
            incomplete_relevant_evidence = True
        primary_year_axis = sorted(
            {item["year"] for item in relevant_reporting_year_evidence}, reverse=True
        )
        reporting_period_axis: list[dict[str, Any]] = []
        visible_period_ends = sorted(
            {item["period_end"] for item in relevant_reporting_period_evidence},
            reverse=True,
        )
        if visible_period_ends:
            current_period_end = visible_period_ends[0]
            primary_current_year = date.fromisoformat(current_period_end).year
            evidence_by_temporal_class: dict[str, list[dict[str, Any]]] = {}
            for item in relevant_reporting_period_evidence:
                temporal_class = _statement_temporal_class_v1(item.get("statement_type"))
                evidence_by_temporal_class.setdefault(temporal_class, []).append(item)
            for period_role_name, period_year in (
                ("CURRENT_PERIOD", primary_current_year),
                ("COMPARATIVE_PERIOD", primary_current_year - 1),
            ):
                for temporal_class in ("STOCK", "FLOW", "GENERAL"):
                    class_evidence = evidence_by_temporal_class.get(temporal_class, [])
                    class_period_ends = {
                        item["period_end"]
                        for item in class_evidence
                        if date.fromisoformat(item["period_end"]).year == period_year
                    }
                    if len(class_period_ends) > 1:
                        reasons.append("SEGMENT_REPORTING_PERIOD_CONTEXT_CONFLICT")
                        continue
                    if len(class_period_ends) != 1:
                        continue
                    period_end = next(iter(class_period_ends))
                    reporting_period_axis.append(
                        {
                            "authority_class": "TYPED_PRIMARY_REPORTING_PERIOD_END",
                            "carrier_axis": [
                                canonical_clone_v1(item)
                                for item in class_evidence
                                if item["period_end"] == period_end
                            ],
                            "period_end": period_end,
                            "period_role": period_role_name,
                            "period_year": period_year,
                            "temporal_class": temporal_class,
                        }
                    )
        scope_year_axis = sorted(
            {year for item in relevant_scopes for year in _years([item.get("source_exact")])},
            reverse=True,
        )
        reporting_year_axis: list[int] = []
        if reporting_period_axis:
            primary_current_year = reporting_period_axis[0]["period_year"]
            reporting_year_axis = [primary_current_year]
            if any(
                year not in {primary_current_year, primary_current_year - 1}
                for year in [*primary_year_axis, *scope_year_axis]
            ):
                reasons.append("SEGMENT_REPORTING_YEAR_CONTEXT_CONFLICT")
        elif primary_year_axis:
            primary_current_year = primary_year_axis[0]
            if len(primary_year_axis) > 2 or any(
                year not in {primary_current_year, primary_current_year - 1}
                for year in primary_year_axis
            ):
                reasons.append("SEGMENT_REPORTING_YEAR_CONTEXT_CONFLICT")
            reporting_year_axis = [primary_current_year]
            if any(
                year not in {primary_current_year, primary_current_year - 1}
                for year in scope_year_axis
            ):
                reasons.append("SEGMENT_REPORTING_YEAR_CONTEXT_CONFLICT")
        elif len(scope_year_axis) == 1:
            reporting_year_axis = scope_year_axis
        elif len(scope_year_axis) == 2 and scope_year_axis[0] - scope_year_axis[1] == 1:
            # A note heading commonly prints the current/comparative pair.
            # It authenticates the current year as the later member; it is not
            # a conflict and does not force Gemini to repeat the year per cell.
            reporting_year_axis = [scope_year_axis[0]]
        elif len(scope_year_axis) > 1:
            reasons.append("SEGMENT_REPORTING_YEAR_CONTEXT_CONFLICT")
        owner_receipt = {
            "consolidated_scope_axis": canonical_clone_v1(relevant_scopes),
            "continuation_advisory_axis": canonical_clone_v1(continuation_advisory_axis),
            "document_scope_state_axis": canonical_clone_v1(active_scope_axis),
            "owner_branch_binding_axis": canonical_clone_v1(owner_branch_binding_axis),
            "owner_continuation_axis": canonical_clone_v1(owner_continuation_axis),
            "owner_marker_axis": canonical_clone_v1(relevant_owners),
            "reset_fence_axis": canonical_clone_v1(relevant_fences),
            "reporting_period_axis": reporting_period_axis,
            "reporting_year_axis": reporting_year_axis,
            "reporting_year_evidence": canonical_clone_v1(relevant_reporting_year_evidence),
            "scope_mention_axis": canonical_clone_v1(
                [
                    item
                    for item in scope_mentions
                    if source_position(item) <= first_selected_position
                ]
            ),
            "rule": "EXPLICIT_CONSOLIDATED_SEGMENT_OWNER_RESET_FREE_MULTI_TABLE_INTERVAL",
            "selected_interval": {
                "first_selected_page_ordinal": min(
                    item["selected_page_ordinal"] for item in selected_inventory
                ),
                "last_selected_page_ordinal": max(
                    item["selected_page_ordinal"] for item in selected_inventory
                ),
                "owner_start_selected_page_ordinal": owner_start,
                "first_selected_position": list(first_selected_position),
                "last_selected_position": list(last_selected_position),
                "owner_start_position": list(owner_start_position),
            },
        }
    status = (
        NOT_OBSERVED
        if not position_inventory
        else UNRESOLVED
        if incomplete_relevant_evidence or scope_state_conflict or ambiguous_scope_inventory
        else NOT_OBSERVED
        if outside_consolidated_scope
        else UNRESOLVED
        if reasons or not selected_inventory
        else READY
    )
    regions = (
        [{key: item[key] for key in _REGION_FIELDS} for item in selected_inventory]
        if status == READY
        else []
    )
    bounded_unit_evidence: list[dict[str, Any]] = []
    if selected_inventory and last_selected_position is not None:
        context_starts = [
            position
            for position in (owner_start_position, latest_scope_position)
            if position is not None
        ]
        context_start = min(context_starts) if context_starts else first_selected_position
        bounded_unit_evidence = sorted(
            {
                canonical_json_sha256_v1(item): canonical_clone_v1(item)
                for item in unit_context_inventory
                if context_start is not None
                and context_start <= source_position(item) <= last_selected_position
            }.values(),
            key=canonical_json_sha256_v1,
        )
    unit_identities = {
        (item["canonical_unit"], item["magnitude_power10"], item["accepted"])
        for item in bounded_unit_evidence
    }
    unit_context_status = (
        "NO_BOUNDED_UNIT_EVIDENCE"
        if not unit_identities
        else "UNIQUE_BOUNDED_SEGMENT_UNIT"
        if len(unit_identities) == 1 and next(iter(unit_identities))[2]
        else "REJECTED_BOUNDED_SEGMENT_UNIT"
        if len(unit_identities) == 1
        else "CONFLICTING_BOUNDED_SEGMENT_UNIT"
    )
    unit_context_material = {
        "canonical_unit": (
            next(iter(unit_identities))[0]
            if unit_context_status == "UNIQUE_BOUNDED_SEGMENT_UNIT"
            else None
        ),
        "evidence_axis": bounded_unit_evidence,
        "evidence_axis_sha256": canonical_json_sha256_v1(bounded_unit_evidence),
        "rule": "UNIQUE_TYPED_UNIT_IN_SELECTED_SEGMENT_OWNER_SCOPE_INTERVAL",
        "status": unit_context_status,
    }
    unit_context = {
        **unit_context_material,
        "document_unit_context_sha256": canonical_json_sha256_v1(unit_context_material),
    }
    material = {
        "component_regions": regions,
        "declared_table_inventory": inventory,
        "document_id": first["document_id"],
        "document_ordinal": first["document_ordinal"],
        "document_unit_context_evidence": unit_context,
        "owner_receipt": owner_receipt,
        "reasons": sorted(set(reasons)),
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": status,
    }
    return {"cluster_id": "gjeqmfv1:cluster:" + canonical_json_sha256_v1(material), **material}


def _table_from_region(
    region: Mapping[str, Any], pages: Mapping[str, Mapping[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    page = pages.get(region["page_json_version_id"])
    if type(page) is not dict or type(page.get("sections")) is not list:
        raise _error("segment-report selected canonical page is absent")
    si, ti = int(region["section_id"][1:]) - 1, int(region["table_id"][1:]) - 1
    try:
        section = page["sections"][si]
        table = section["tables"][ti]
    except (IndexError, KeyError, TypeError) as exc:
        raise _error("segment-report region does not resolve") from exc
    if type(section) is not dict or type(table) is not dict:
        raise _error("segment-report region is not a table")
    return section, table


def _checked_owner_branch_binding_axis_v1(
    *,
    owner_receipt: Mapping[str, Any],
    regions: Sequence[Mapping[str, Any]],
    compiled: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    raw_axis = owner_receipt.get("owner_branch_binding_axis", [])
    if type(raw_axis) is not list:
        raise _error("segment-report owner branch binding axis is invalid")
    region_by_id = {canonical_json_sha256_v1(region): region for region in regions}
    continuation_axis = owner_receipt.get("owner_continuation_axis", [])
    if type(continuation_axis) is not list:
        raise _error("segment-report owner continuation axis is invalid")
    continuation_by_region = {
        canonical_json_sha256_v1(item.get("region")): item
        for item in continuation_axis
        if type(item) is dict and type(item.get("region")) is dict
    }
    checked: dict[str, dict[str, Any]] = {}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    expected_fields = {
        "branch_marker_axis",
        "branch_role",
        "owner_marker",
        "region",
        "rule",
    }
    expected_rule = (
        "COLOCATED_EXPLICIT_OWNER_BRANCH_MARKER_CARRIED_ACROSS_"
        "PHYSICALLY_ADJACENT_CONTINUATION_CHAIN"
    )
    for item in raw_axis:
        if (
            type(item) is not dict
            or set(item) != expected_fields
            or item.get("rule") != expected_rule
        ):
            raise _error("segment-report owner branch binding is invalid")
        region = item.get("region")
        region_id = canonical_json_sha256_v1(region)
        if region_id not in region_by_id or not same_typed_json_v1(region, region_by_id[region_id]):
            raise _error("segment-report owner branch target drifted")
        if region_id in checked:
            raise _error("segment-report owner branch target is duplicated")
        branch_role = item.get("branch_role")
        if branch_role not in compiled["branch_aliases_by_role"]:
            raise _error("segment-report owner branch role is invalid")
        owner_marker = item.get("owner_marker")
        branch_marker_axis = item.get("branch_marker_axis")
        if (
            type(owner_marker) is not dict
            or type(branch_marker_axis) is not list
            or not branch_marker_axis
            or not _contains(
                owner_marker.get("source_exact"), compiled["query_policy"]["owner_aliases"]
            )
        ):
            raise _error("segment-report owner branch carrier is invalid")
        for marker in branch_marker_axis:
            if (
                type(marker) is not dict
                or marker.get("branch_role") != branch_role
                or not _contains(
                    marker.get("source_exact"), compiled["branch_aliases_by_role"][branch_role]
                )
                or any(
                    marker.get(key) != owner_marker.get(key)
                    for key in ("physical_page", "selected_page_ordinal", "section_id")
                )
            ):
                raise _error("segment-report owner branch marker contradicts its role")
        continuation = continuation_by_region.get(region_id)
        if type(continuation) is not dict or not same_typed_json_v1(
            continuation.get("owner_marker"), owner_marker
        ):
            raise _error("segment-report owner branch continuation binding drifted")
        body = canonical_clone_v1(item)
        checked[region_id] = body
        grouped.setdefault((canonical_json_sha256_v1(owner_marker), branch_role), []).append(body)
    for items in grouped.values():
        items.sort(
            key=lambda item: (
                item["region"]["selected_page_ordinal"],
                item["region"]["physical_page"],
            )
        )
        owner = items[0]["owner_marker"]
        prior_selected = owner.get("selected_page_ordinal")
        prior_physical = owner.get("physical_page")
        for item in items:
            region = item["region"]
            if (
                type(prior_selected) is not int
                or type(prior_physical) is not int
                or region["selected_page_ordinal"] != prior_selected + 1
                or region["physical_page"] != prior_physical + 1
            ):
                raise _error("segment-report owner branch chain is not physically adjacent")
            prior_selected = region["selected_page_ordinal"]
            prior_physical = region["physical_page"]
    return checked


def _unit_matches(surface: Any, compiled: Mapping[str, Any]) -> list[dict[str, Any]]:
    folded = _norm(surface)
    matches = []
    for alias, binding in compiled["unit_binding_by_alias"].items():
        if alias == folded or f" {alias} " in f" {folded} ":
            matches.append(binding)
    # Prefer maximal aliases only when they resolve to the same unit.  A second
    # visible magnitude remains an explicit conflict.
    unique = {(item["canonical_unit"], item["magnitude_power10"]): item for item in matches}
    return list(unique.values())


def _governed_context_unit_matches(
    surface: Any, compiled: Mapping[str, Any], *, carrier_kind: str | None = None
) -> list[dict[str, Any]]:
    folded = _norm(surface)
    if not folded:
        return []
    declared_aliases = set(compiled["unit_binding_by_alias"])
    explicit_declaration = (
        folded in declared_aliases
        or re.search(r"\bdon vi(?: tinh)?\b", folded) is not None
        or (
            carrier_kind == "NARRATIVE"
            and re.search(r"\bso lieu\b.*\b(?:trinh bay|tinh)\s+bang\b", folded) is not None
        )
    )
    if carrier_kind == "TABLE_TITLE" and type(surface) is str:
        trailing_parenthetical = re.search(r"\(([^()]*)\)\s*$", surface)
        explicit_declaration = explicit_declaration or bool(
            trailing_parenthetical and _unit_matches(trailing_parenthetical.group(1), compiled)
        )
    if not explicit_declaration:
        return []
    return _unit_matches(surface, compiled)


def _checked_document_unit_context_v1(value: Any, *, compiled: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "canonical_unit",
        "document_unit_context_sha256",
        "evidence_axis",
        "evidence_axis_sha256",
        "rule",
        "status",
    }
    evidence_fields = {
        "accepted",
        "canonical_unit",
        "carrier_kind",
        "magnitude_power10",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "selected_page_ordinal",
        "source_exact",
        "table_ordinal",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("rule") != "UNIQUE_TYPED_UNIT_IN_SELECTED_SEGMENT_OWNER_SCOPE_INTERVAL"
        or type(value.get("evidence_axis")) is not list
    ):
        raise _error("segment-report document unit context is invalid")
    evidence = value["evidence_axis"]
    if any(
        type(item) is not dict
        or set(item) != evidence_fields
        or type(item.get("accepted")) is not bool
        or type(item.get("canonical_unit")) is not str
        or type(item.get("magnitude_power10")) is not int
        or item.get("carrier_kind") not in {"SECTION_TITLE", "NARRATIVE"}
        or _PAGE_VERSION.fullmatch(item.get("page_json_version_id", "")) is None
        or _SECTION_ID.fullmatch(item.get("section_id", "")) is None
        or any(
            type(item.get(key)) is not int or item[key] < (0 if key == "table_ordinal" else 1)
            for key in (
                "physical_page",
                "selected_page_ordinal",
                "table_ordinal",
            )
        )
        or type(item.get("source_exact")) is not str
        or not item["source_exact"].strip()
        for item in evidence
    ):
        raise _error("segment-report document unit evidence is invalid")
    expected_evidence = sorted(
        {canonical_json_sha256_v1(item): item for item in evidence}.values(),
        key=canonical_json_sha256_v1,
    )
    if not same_typed_json_v1(evidence, expected_evidence):
        raise _error("segment-report document unit evidence is duplicate or unordered")
    for item in evidence:
        visible_identities = {
            (match["canonical_unit"], match["magnitude_power10"], match["accepted"])
            for match in _governed_context_unit_matches(
                item["source_exact"], compiled, carrier_kind=item["carrier_kind"]
            )
        }
        declared_identity = (
            item["canonical_unit"],
            item["magnitude_power10"],
            item["accepted"],
        )
        if declared_identity not in visible_identities:
            raise _error("segment-report document unit evidence contradicts source text")
    identities = {
        (item["canonical_unit"], item["magnitude_power10"], item["accepted"]) for item in evidence
    }
    expected_status = (
        "NO_BOUNDED_UNIT_EVIDENCE"
        if not identities
        else "UNIQUE_BOUNDED_SEGMENT_UNIT"
        if len(identities) == 1 and next(iter(identities))[2]
        else "REJECTED_BOUNDED_SEGMENT_UNIT"
        if len(identities) == 1
        else "CONFLICTING_BOUNDED_SEGMENT_UNIT"
    )
    expected_unit = (
        next(iter(identities))[0] if expected_status == "UNIQUE_BOUNDED_SEGMENT_UNIT" else None
    )
    material = {
        "canonical_unit": expected_unit,
        "evidence_axis": evidence,
        "evidence_axis_sha256": canonical_json_sha256_v1(evidence),
        "rule": value["rule"],
        "status": expected_status,
    }
    if (
        value.get("canonical_unit") != expected_unit
        or value.get("status") != expected_status
        or value.get("evidence_axis_sha256") != material["evidence_axis_sha256"]
        or value.get("document_unit_context_sha256") != canonical_json_sha256_v1(material)
    ):
        raise _error("segment-report document unit context drifted")
    return canonical_clone_v1(value)


def _resolve_segment_table_units_v1(
    table_receipts: Sequence[Mapping[str, Any]],
    *,
    unit_context: Mapping[str, Any],
    compiled: Mapping[str, Any],
) -> dict[str, Any]:
    context = _checked_document_unit_context_v1(unit_context, compiled=compiled)
    reasons: set[str] = set()
    assignments: list[dict[str, Any]] = []
    explicit_units = sorted(
        {receipt.get("unit") for receipt in table_receipts if receipt.get("unit") is not None}
    )
    if len(explicit_units) > 1:
        reasons.add("SEGMENT_DOCUMENT_UNIT_CONFLICT")
    for receipt in table_receipts:
        region = receipt.get("region")
        local_unit = receipt.get("unit")
        assigned_unit = local_unit
        source = "EXPLICIT_SELECTED_TABLE_UNIT" if local_unit is not None else None
        carrier_regions: list[dict[str, Any]] = []
        if local_unit is None and type(region) is dict:
            siblings = [
                sibling
                for sibling in table_receipts
                if sibling is not receipt
                and sibling.get("unit") is not None
                and type(sibling.get("region")) is dict
                and sibling["region"].get("page_json_version_id")
                == region.get("page_json_version_id")
                and sibling["region"].get("section_id") == region.get("section_id")
            ]
            sibling_units = {sibling["unit"] for sibling in siblings}
            if len(sibling_units) == 1:
                assigned_unit = next(iter(sibling_units))
                source = "SAME_PAGE_SECTION_EXPLICIT_SIBLING_UNIT"
                carrier_regions = sorted(
                    [canonical_clone_v1(sibling["region"]) for sibling in siblings],
                    key=canonical_json_sha256_v1,
                )
                if context["status"] in {
                    "CONFLICTING_BOUNDED_SEGMENT_UNIT",
                    "REJECTED_BOUNDED_SEGMENT_UNIT",
                } or (
                    context["canonical_unit"] is not None
                    and context["canonical_unit"] != assigned_unit
                ):
                    reasons.add("SEGMENT_DOCUMENT_UNIT_CONFLICT")
            elif len(sibling_units) > 1:
                reasons.add("SEGMENT_DOCUMENT_UNIT_CONFLICT")
            elif context["canonical_unit"] is not None:
                assigned_unit = context["canonical_unit"]
                source = "UNIQUE_BOUNDED_SEGMENT_CONTEXT_UNIT"
            else:
                if context["status"] in {
                    "CONFLICTING_BOUNDED_SEGMENT_UNIT",
                    "REJECTED_BOUNDED_SEGMENT_UNIT",
                }:
                    reasons.add("SEGMENT_DOCUMENT_UNIT_CONFLICT")
                reasons.add("SEGMENT_MONEY_UNIT_NOT_RESOLVED")
        assignments.append(
            {
                "canonical_unit": assigned_unit,
                "carrier_regions": carrier_regions,
                "local_unit": local_unit,
                "region": canonical_clone_v1(region),
                "source": source,
            }
        )
    assigned_units = {
        item["canonical_unit"] for item in assignments if item["canonical_unit"] is not None
    }
    if len(assigned_units) > 1:
        reasons.add("SEGMENT_DOCUMENT_UNIT_CONFLICT")
    if any(item["canonical_unit"] is None for item in assignments):
        reasons.add("SEGMENT_MONEY_UNIT_NOT_RESOLVED")
    return {
        "canonical_unit": next(iter(assigned_units)) if len(assigned_units) == 1 else None,
        "explicit_unit_axis": explicit_units,
        "reasons": sorted(reasons),
        "source": "TABLE_SCOPED_UNIT_ASSIGNMENT_AXIS",
        "table_unit_assignment_axis": assignments,
    }


def _segment_table_period_shape_v1(receipt: Mapping[str, Any]) -> dict[str, Any]:
    cells = receipt.get("cell_axis", [])
    metrics = sorted(
        {cell.get("metric_role") for cell in cells if type(cell.get("metric_role")) is str}
    )
    return {
        "metric_cell_counts": [
            {
                "cell_count": sum(cell.get("metric_role") == metric for cell in cells),
                "metric_role": metric,
                "total_count": sum(
                    cell.get("metric_role") == metric and cell.get("axis_role") == "TOTAL"
                    for cell in cells
                ),
            }
            for metric in metrics
        ],
        "orientation": receipt.get("orientation"),
    }


def _segment_declared_metric_signature_v1(
    receipt: Mapping[str, Any], compiled: Mapping[str, Any]
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                cell.get("metric_role")
                for cell in receipt.get("cell_axis", [])
                if cell.get("metric_role") in compiled["metric_offset_by_role"]
            }
        )
    )


def _segment_declared_table_shape_v1(
    receipt: Mapping[str, Any], compiled: Mapping[str, Any]
) -> dict[str, Any]:
    cells = [
        cell
        for cell in receipt.get("cell_axis", [])
        if cell.get("metric_role") in compiled["metric_offset_by_role"]
    ]
    metrics = _segment_declared_metric_signature_v1(receipt, compiled)
    return {
        "metric_cell_counts": [
            {
                "cell_count": sum(cell.get("metric_role") == metric for cell in cells),
                "metric_role": metric,
                "total_count": sum(
                    cell.get("metric_role") == metric and cell.get("axis_role") == "TOTAL"
                    for cell in cells
                ),
            }
            for metric in metrics
        ],
        "orientation": receipt.get("orientation"),
        "ordered_cell_role_axis": [
            {
                "axis_role": cell.get("axis_role"),
                "metric_role": cell.get("metric_role"),
            }
            for cell in receipt.get("cell_axis", [])
        ],
    }


def _segment_declared_metric_layout_v1(
    receipt: Mapping[str, Any], compiled: Mapping[str, Any]
) -> dict[str, list[str]]:
    return {
        metric: [
            cell["axis_role"]
            for cell in receipt.get("cell_axis", [])
            if cell.get("metric_role") == metric
        ]
        for metric in _segment_declared_metric_signature_v1(receipt, compiled)
    }


def _segment_regions_are_corresponding_adjacent_pages_v1(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> bool:
    return (
        first.get("selected_page_ordinal") + 1 == second.get("selected_page_ordinal")
        and first.get("physical_page") + 1 == second.get("physical_page")
        and first.get("section_id") == second.get("section_id")
        and first.get("table_id") == second.get("table_id")
    )


def _segment_repeated_block_geometry_v1(
    regions: Sequence[Mapping[str, Any]],
) -> str | None:
    """Seal one of the two supported four-table repeated-block layouts."""

    if len(regions) != 4:
        return None
    if all(
        _segment_regions_are_corresponding_adjacent_pages_v1(first, second)
        for first, second in zip(regions[:-1], regions[1:], strict=True)
    ):
        return "FOUR_CORRESPONDING_ADJACENT_PAGES"

    first_left, first_right, second_left, second_right = regions

    def same_page_pair(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        try:
            left_table = int(str(left.get("table_id"))[1:])
            right_table = int(str(right.get("table_id"))[1:])
        except ValueError:
            return False
        return (
            left.get("selected_page_ordinal") == right.get("selected_page_ordinal")
            and left.get("physical_page") == right.get("physical_page")
            and left.get("section_id") == right.get("section_id")
            and right_table == left_table + 1
        )

    if not same_page_pair(first_left, first_right) or not same_page_pair(second_left, second_right):
        return None
    if first_left.get("selected_page_ordinal") + 1 != second_left.get(
        "selected_page_ordinal"
    ) or first_left.get("physical_page") + 1 != second_left.get("physical_page"):
        return None
    first_ordinals = tuple(int(str(region.get("table_id"))[1:]) for region in regions[:2])
    second_ordinals = tuple(int(str(region.get("table_id"))[1:]) for region in regions[2:])
    if first_ordinals != second_ordinals:
        return None
    return "TWO_ADJACENT_PAGE_SAME_SECTION_TABLE_PAIRS"


def _segment_owner_period_authority_for_signature_v1(
    *,
    owner_receipt: Mapping[str, Any],
    role: str,
    signature: Sequence[str],
) -> list[dict[str, Any]] | None:
    owner_axis = owner_receipt.get("reporting_period_axis", [])
    if type(owner_axis) is not list:
        return None
    needed_classes = {
        temporal_class
        for metric in signature
        if (temporal_class := _metric_temporal_class_v1(metric)) is not None
    }
    authority: list[dict[str, Any]] = []
    for temporal_class in sorted(needed_classes):
        matches = [
            item
            for item in owner_axis
            if item.get("period_role") == role and item.get("temporal_class") == temporal_class
        ]
        if not matches:
            matches = [
                item
                for item in owner_axis
                if item.get("period_role") == role and item.get("temporal_class") == "GENERAL"
            ]
        if len({item.get("period_end") for item in matches}) != 1:
            return None
        authority.extend(matches)
    return sorted(
        {canonical_json_sha256_v1(item): canonical_clone_v1(item) for item in authority}.values(),
        key=canonical_json_sha256_v1,
    )


def _segment_period_pair_geometry_v1(
    receipts: Sequence[Mapping[str, Any]],
) -> tuple[int, int, str, tuple[int, int]] | None:
    if len(receipts) != 2:
        return None
    regions = [receipt.get("region") for receipt in receipts]
    if any(type(region) is not dict for region in regions):
        return None
    first, second = regions
    if (
        first["selected_page_ordinal"] != second["selected_page_ordinal"]
        or first["physical_page"] != second["physical_page"]
        or first["section_id"] != second["section_id"]
    ):
        return None
    table_ordinals = (int(first["table_id"][1:]), int(second["table_id"][1:]))
    if table_ordinals[1] != table_ordinals[0] + 1:
        return None
    return (
        first["selected_page_ordinal"],
        first["physical_page"],
        first["section_id"],
        table_ordinals,
    )


def _segment_period_pair_binding_mode_v1(
    target: tuple[int, int, str, tuple[int, int]],
    carrier: tuple[int, int, str, tuple[int, int]],
) -> str | None:
    if target[3] != carrier[3]:
        return None
    target_section = int(target[2][1:])
    carrier_section = int(carrier[2][1:])
    if (
        target[0] == carrier[0]
        and target[1] == carrier[1]
        and abs(target_section - carrier_section) == 1
    ):
        return "SAME_PAGE_ADJACENT_SECTIONS"
    if (
        abs(target[0] - carrier[0]) == 1
        and abs(target[1] - carrier[1]) == 1
        and target_section == carrier_section
    ):
        return "ADJACENT_PAGE_CORRESPONDING_SECTION"
    return None


def _segment_cross_branch_total_period_candidates_v1(
    table_receipts: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
    owner_receipt: Mapping[str, Any],
    period_role_by_year: Mapping[int, str],
    unit_by_region: Mapping[str, str | None],
) -> list[dict[str, Any]]:
    """Find uniquely reconciled partial two-period stock pairs.

    This does not calculate or residualize a value.  It accepts only a
    one-to-one equality receipt over at least two source-visible declared
    TOTAL cells and uses an independently dated cross-branch pair to bind the
    missing role.
    """

    def direct_role(receipt: Mapping[str, Any]) -> str | None:
        roles = {
            period_role_by_year[cell.get("period_year")]
            for cell in receipt.get("cell_axis", [])
            if cell.get("metric_role") in compiled_specs["metric_offset_by_role"]
            and cell.get("period_year") in period_role_by_year
        }
        return next(iter(roles)) if len(roles) == 1 else None

    def total_cells(receipt: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
        grouped: dict[str, list[Mapping[str, Any]]] = {}
        for cell in receipt.get("cell_axis", []):
            metric = cell.get("metric_role")
            if (
                metric in compiled_specs["metric_offset_by_role"]
                and cell.get("axis_role") == "TOTAL"
                and cell.get("coefficient") is not None
            ):
                grouped.setdefault(metric, []).append(cell)
        return {metric: cells[0] for metric, cells in grouped.items() if len(cells) == 1}

    def binding_mode(
        targets: Sequence[Mapping[str, Any]], carriers: Sequence[Mapping[str, Any]]
    ) -> str | None:
        target_regions = [receipt.get("region", {}) for receipt in targets]
        carrier_geometry = _segment_period_pair_geometry_v1(carriers)
        if carrier_geometry is None:
            return None
        first, second = target_regions
        if (
            first.get("selected_page_ordinal") + 1 != second.get("selected_page_ordinal")
            or first.get("physical_page") + 1 != second.get("physical_page")
            or first.get("table_id") != second.get("table_id")
        ):
            return None
        carrier_region = carriers[0].get("region", {})
        if (
            second.get("selected_page_ordinal") + 1 == carrier_region.get("selected_page_ordinal")
            and second.get("physical_page") + 1 == carrier_region.get("physical_page")
            and second.get("table_id") == carrier_region.get("table_id")
        ):
            return "TWO_ADJACENT_TARGET_PAGES_THEN_SAME_PAGE_CARRIER_PAIR"
        if (
            carrier_region.get("selected_page_ordinal") + 1 == first.get("selected_page_ordinal")
            and carrier_region.get("physical_page") + 1 == first.get("physical_page")
            and first.get("table_id") == carrier_region.get("table_id")
        ):
            return "SAME_PAGE_CARRIER_PAIR_THEN_TWO_ADJACENT_TARGET_PAGES"
        return None

    grouped: dict[tuple[str, tuple[str, ...]], list[Mapping[str, Any]]] = {}
    for receipt in table_receipts:
        branch = receipt.get("branch")
        signature = _segment_declared_metric_signature_v1(receipt, compiled_specs)
        if branch and signature:
            grouped.setdefault((branch, signature), []).append(receipt)
    for receipts in grouped.values():
        receipts.sort(
            key=lambda receipt: (
                receipt["region"]["selected_page_ordinal"],
                int(receipt["region"]["section_id"][1:]),
                int(receipt["region"]["table_id"][1:]),
            )
        )

    output: list[dict[str, Any]] = []
    for (target_branch, target_signature), targets in grouped.items():
        target_roles = [direct_role(receipt) for receipt in targets]
        if len(targets) != 2 or target_roles.count(None) != 1:
            continue
        dated_role = next(role for role in target_roles if role is not None)
        undated_index = target_roles.index(None)
        existing_evidence = targets[undated_index].get("period_assignment_evidence")
        if (
            existing_evidence is not None
            and existing_evidence.get("rule")
            != "UNIQUE_CROSS_BRANCH_TWO_PERIOD_DECLARED_TOTAL_CORRESPONDENCE"
        ):
            continue
        target_role = "COMPARATIVE_PERIOD" if dated_role == "CURRENT_PERIOD" else "CURRENT_PERIOD"
        owner_authority = _segment_owner_period_authority_for_signature_v1(
            owner_receipt=owner_receipt,
            role=target_role,
            signature=target_signature,
        )
        if not owner_authority:
            continue
        target_totals = [total_cells(receipt) for receipt in targets]
        compatible: list[dict[str, Any]] = []
        for (carrier_branch, carrier_signature), carriers in grouped.items():
            if carrier_branch == target_branch or len(carriers) != 2:
                continue
            carrier_roles = [direct_role(receipt) for receipt in carriers]
            if set(carrier_roles) != {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}:
                continue
            mode = binding_mode(targets, carriers)
            if mode is None:
                continue
            units = {
                unit_by_region.get(canonical_json_sha256_v1(receipt["region"]))
                for receipt in (*targets, *carriers)
            }
            orientations = {receipt.get("orientation") for receipt in (*targets, *carriers)}
            if len(units) != 1 or None in units or len(orientations) != 1:
                continue
            carrier_totals = [total_cells(receipt) for receipt in carriers]
            common_metrics = sorted(
                set(target_signature)
                & set(carrier_signature)
                & set(target_totals[0])
                & set(target_totals[1])
                & set(carrier_totals[0])
                & set(carrier_totals[1])
            )
            if len(common_metrics) < 2:
                continue
            matches: list[list[int]] = []
            for target_index in range(2):
                matches.append(
                    [
                        carrier_index
                        for carrier_index in range(2)
                        if all(
                            target_totals[target_index][metric].get("coefficient")
                            == carrier_totals[carrier_index][metric].get("coefficient")
                            for metric in common_metrics
                        )
                    ]
                )
            if any(len(item) != 1 for item in matches) or len({item[0] for item in matches}) != 2:
                continue
            if any(
                target_roles[index] is not None
                and target_roles[index] != carrier_roles[matches[index][0]]
                for index in range(2)
            ):
                continue
            correspondence_axis = []
            for target_index, match in enumerate(matches):
                carrier_index = match[0]
                correspondence_axis.append(
                    {
                        "carrier_region": canonical_clone_v1(carriers[carrier_index]["region"]),
                        "metric_axis": [
                            {
                                "carrier_cell_ref": canonical_clone_v1(
                                    carrier_totals[carrier_index][metric]["cell_ref"]
                                ),
                                "coefficient": target_totals[target_index][metric]["coefficient"],
                                "metric_role": metric,
                                "target_cell_ref": canonical_clone_v1(
                                    target_totals[target_index][metric]["cell_ref"]
                                ),
                            }
                            for metric in common_metrics
                        ],
                        "period_role": carrier_roles[carrier_index],
                        "target_region": canonical_clone_v1(targets[target_index]["region"]),
                    }
                )
            compatible.append(
                {
                    "binding_mode": mode,
                    "branch": target_branch,
                    "carrier_branch": carrier_branch,
                    "carrier_regions": [
                        canonical_clone_v1(receipt["region"]) for receipt in carriers
                    ],
                    "common_total_metric_roles": common_metrics,
                    "orientation": next(iter(orientations)),
                    "owner_period_authority_axis": owner_authority,
                    "target_pair_regions": [
                        canonical_clone_v1(receipt["region"]) for receipt in targets
                    ],
                    "target_role": target_role,
                    "total_correspondence_axis": correspondence_axis,
                    "unit": next(iter(units)),
                }
            )
        if len(compatible) != 1:
            continue
        evidence = {
            **compatible[0],
            "rule": "UNIQUE_CROSS_BRANCH_TWO_PERIOD_DECLARED_TOTAL_CORRESPONDENCE",
            "target_regions": [canonical_clone_v1(targets[undated_index]["region"])],
        }
        output.append({"evidence": evidence, "target_receipt": targets[undated_index]})
    return output


def _validate_segment_period_assignment_evidence_v1(
    table_receipts: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
    owner_receipt: Mapping[str, Any],
    period_role_by_year: Mapping[int, str],
    unit_receipt: Mapping[str, Any],
) -> None:
    """Validate structural period carriers from the sealed typed receipt graph."""

    receipt_by_region = {
        canonical_json_sha256_v1(receipt.get("region")): receipt for receipt in table_receipts
    }
    evidence_groups: dict[str, tuple[Mapping[str, Any], list[Mapping[str, Any]]]] = {}
    sibling_evidence: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    metric_context_evidence: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    section_context_evidence: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    repeated_block_groups: dict[str, tuple[Mapping[str, Any], list[Mapping[str, Any]]]] = {}
    split_combined_evidence: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    total_correspondence_evidence: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    for receipt in table_receipts:
        evidence = receipt.get("period_assignment_evidence")
        if evidence is None:
            continue
        if (
            type(evidence) is dict
            and evidence.get("rule") == "UNIQUE_EXPLICIT_PERIOD_ROLE_WITHIN_SAME_PAGE_SECTION"
        ):
            sibling_evidence.append((evidence, receipt))
            continue
        if (
            type(evidence) is dict
            and evidence.get("rule") == "UNIQUE_VISIBLE_PERIOD_ROLE_WITHIN_SAME_TABLE"
        ):
            metric_context_evidence.append((evidence, receipt))
            continue
        if (
            type(evidence) is dict
            and evidence.get("rule") == "UNIQUE_SECTION_PERIOD_ROLE_FOR_UNDATED_TABLE"
        ):
            section_context_evidence.append((evidence, receipt))
            continue
        if (
            type(evidence) is dict
            and evidence.get("rule") == "UNIQUE_ROLE_WITHIN_REPEATED_ADJACENT_METRIC_BLOCK"
        ):
            key = canonical_json_sha256_v1(evidence)
            repeated_block_groups.setdefault(key, (evidence, []))[1].append(receipt)
            continue
        if (
            type(evidence) is dict
            and evidence.get("rule")
            == "UNIQUE_COMPLEMENT_ROLE_FROM_ADJACENT_SPLIT_COMBINED_METRIC_BLOCK"
        ):
            split_combined_evidence.append((evidence, receipt))
            continue
        if (
            type(evidence) is dict
            and evidence.get("rule")
            == "UNIQUE_CROSS_BRANCH_TWO_PERIOD_DECLARED_TOTAL_CORRESPONDENCE"
        ):
            total_correspondence_evidence.append((evidence, receipt))
            continue
        if (
            type(evidence) is not dict
            or set(evidence) != {"carrier", "rule", "target_regions"}
            or evidence.get("rule")
            != (
                "UNIQUE_EXPLICIT_TWO_PERIOD_CROSS_BRANCH_PAIR_WITH_EXACT_"
                "METRIC_ORIENTATION_AND_CELL_COUNT_SIGNATURE"
            )
            or type(evidence.get("carrier")) is not dict
            or type(evidence.get("target_regions")) is not list
        ):
            raise _error("segment-report structural period evidence is invalid")
        key = canonical_json_sha256_v1(evidence)
        evidence_groups.setdefault(key, (evidence, []))[1].append(receipt)

    def visible_declared_roles(receipt: Mapping[str, Any]) -> set[str]:
        return {
            period_role_by_year[cell.get("period_year")]
            for cell in receipt.get("cell_axis", [])
            if cell.get("metric_role") in compiled_specs["metric_offset_by_role"]
            and cell.get("period_year") in period_role_by_year
        }

    def visible_roles_for_metric(receipt: Mapping[str, Any], metric: str) -> set[str]:
        return {
            period_role_by_year[cell.get("period_year")]
            for cell in receipt.get("cell_axis", [])
            if cell.get("metric_role") == metric and cell.get("period_year") in period_role_by_year
        }

    def independently_resolved_role(receipt: Mapping[str, Any]) -> str | None:
        roles = visible_declared_roles(receipt)
        if len(roles) == 1:
            return next(iter(roles))
        evidence = receipt.get("period_assignment_evidence")
        if (
            not roles
            and type(evidence) is dict
            and evidence.get("rule") != "UNIQUE_ROLE_WITHIN_REPEATED_ADJACENT_METRIC_BLOCK"
            and receipt.get("period_role") in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
        ):
            return receipt["period_role"]
        return None

    table_unit_axis = unit_receipt.get("table_unit_assignment_axis", [])
    if type(table_unit_axis) is not list:
        raise _error("segment-report table unit assignment receipt is invalid")
    unit_by_region = {
        canonical_json_sha256_v1(item.get("region")): item.get("canonical_unit")
        for item in table_unit_axis
        if type(item) is dict
    }

    expected_total_candidates = _segment_cross_branch_total_period_candidates_v1(
        table_receipts,
        compiled_specs=compiled_specs,
        owner_receipt=owner_receipt,
        period_role_by_year=period_role_by_year,
        unit_by_region=unit_by_region,
    )
    expected_total_by_target = {
        canonical_json_sha256_v1(item["target_receipt"]["region"]): item["evidence"]
        for item in expected_total_candidates
    }
    if len(total_correspondence_evidence) != len(expected_total_by_target):
        raise _error("segment-report total correspondence period evidence is incomplete")
    for evidence, target_receipt in total_correspondence_evidence:
        target_key = canonical_json_sha256_v1(target_receipt.get("region"))
        expected = expected_total_by_target.get(target_key)
        if (
            expected is None
            or not same_typed_json_v1(evidence, expected)
            or target_receipt.get("period_role") != evidence.get("target_role")
            or target_receipt.get("period_assignment_rule")
            != "MISSING_PERIOD_FROM_CROSS_BRANCH_DECLARED_TOTAL_CORRESPONDENCE"
        ):
            raise _error("segment-report total correspondence period binding drifted")

    for evidence, receipt in metric_context_evidence:
        if set(evidence) != {
            "carrier_metric_roles",
            "period_role",
            "rule",
            "target_metric_roles",
            "target_regions",
        } or not same_typed_json_v1(evidence.get("target_regions"), [receipt.get("region")]):
            raise _error("segment-report table metric period evidence is invalid")
        role = evidence.get("period_role")
        mapped_metrics = sorted(
            {
                cell.get("metric_role")
                for cell in receipt.get("cell_axis", [])
                if cell.get("metric_role") in compiled_specs["metric_offset_by_role"]
            }
        )
        equation_metrics = {
            equation.get("metric_role") for equation in receipt.get("equations", [])
        }
        carrier_metrics = [
            metric
            for metric in mapped_metrics
            if visible_roles_for_metric(receipt, metric) == {role}
        ]
        target_metrics = [
            metric
            for metric in mapped_metrics
            if metric in equation_metrics
            and not visible_roles_for_metric(receipt, metric)
            and all(
                cell.get("period_year") is None
                for cell in receipt.get("cell_axis", [])
                if cell.get("metric_role") == metric
            )
        ]
        if (
            role not in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
            or not carrier_metrics
            or not target_metrics
            or evidence.get("carrier_metric_roles") != carrier_metrics
            or evidence.get("target_metric_roles") != target_metrics
            or receipt.get("period_role_by_metric") != {metric: role for metric in target_metrics}
        ):
            raise _error("segment-report table metric period binding drifted")

    for evidence, receipt in section_context_evidence:
        if set(evidence) != {
            "period_role",
            "rule",
            "section_period_end_axis",
            "target_metric_signature",
            "target_regions",
        } or not same_typed_json_v1(evidence.get("target_regions"), [receipt.get("region")]):
            raise _error("segment-report section period evidence is invalid")
        role = evidence.get("period_role")
        signature = _segment_declared_metric_signature_v1(receipt, compiled_specs)
        branch_receipts = [
            candidate
            for candidate in table_receipts
            if candidate.get("branch") == receipt.get("branch")
        ]
        section_axis = [
            item
            for item in receipt.get("local_period_end_axis", [])
            if item.get("carrier_kind") == "SECTION_TITLE"
            and period_role_by_year.get(item.get("period_year")) == role
        ]
        if (
            role not in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
            or not signature
            or any(
                cell.get("metric_role") in compiled_specs["metric_offset_by_role"]
                and cell.get("period_year") is not None
                for cell in receipt.get("cell_axis", [])
            )
            or sum(
                _segment_declared_metric_signature_v1(candidate, compiled_specs) == signature
                for candidate in branch_receipts
            )
            != 1
            or receipt.get("period_role") != role
            or evidence.get("target_metric_signature") != list(signature)
            or not section_axis
            or not same_typed_json_v1(evidence.get("section_period_end_axis"), section_axis)
        ):
            raise _error("segment-report section period binding drifted")

    for evidence, target_receipts in repeated_block_groups.values():
        if set(evidence) != {
            "binding_mode",
            "block_axis",
            "branch",
            "carrier_regions",
            "orientation",
            "owner_period_authority_axis",
            "rule",
            "shape_axis",
            "target_regions",
            "unit",
        }:
            raise _error("segment-report repeated metric block evidence is invalid")
        block_axis = evidence.get("block_axis")
        carrier_regions = evidence.get("carrier_regions")
        target_regions = evidence.get("target_regions")
        if (
            type(block_axis) is not list
            or len(block_axis) != 2
            or type(carrier_regions) is not list
            or type(target_regions) is not list
            or not same_typed_json_v1(
                target_regions, [receipt.get("region") for receipt in target_receipts]
            )
        ):
            raise _error("segment-report repeated metric block binding is incomplete")
        block_regions = [region for block in block_axis for region in block.get("regions", [])]
        block_receipts = [
            receipt_by_region.get(canonical_json_sha256_v1(region)) for region in block_regions
        ]
        if len(block_receipts) != 4 or any(receipt is None for receipt in block_receipts):
            raise _error("segment-report repeated metric block regions are invalid")
        regions = [receipt["region"] for receipt in block_receipts]
        signatures = [
            _segment_declared_metric_signature_v1(receipt, compiled_specs)
            for receipt in block_receipts
        ]
        shapes = [
            _segment_declared_table_shape_v1(receipt, compiled_specs) for receipt in block_receipts
        ]
        binding_mode = _segment_repeated_block_geometry_v1(regions)
        canonical_units = {
            unit_by_region.get(canonical_json_sha256_v1(receipt["region"]))
            for receipt in block_receipts
        }
        if (
            not signatures[0]
            or signatures[0] != signatures[2]
            or signatures[1] != signatures[3]
            or signatures[0] == signatures[1]
            or not set(signatures[0]).isdisjoint(signatures[1])
            or binding_mode is None
            or evidence.get("binding_mode") != binding_mode
            or {receipt.get("branch") for receipt in block_receipts} != {evidence.get("branch")}
            or canonical_units != {evidence.get("unit")}
            or evidence.get("unit") is None
            or {receipt.get("orientation") for receipt in block_receipts}
            != {evidence.get("orientation")}
            or shapes[0] != shapes[2]
            or shapes[1] != shapes[3]
            or not same_typed_json_v1(evidence.get("shape_axis"), shapes)
        ):
            raise _error("segment-report repeated metric block semantics drifted")
        expected_blocks = []
        expected_carrier_regions = []
        expected_target_regions = []
        pairs = (block_receipts[:2], block_receipts[2:])
        independent_roles: list[str | None] = []
        for pair in pairs:
            carriers = [receipt for receipt in pair if independently_resolved_role(receipt)]
            roles = {independently_resolved_role(receipt) for receipt in carriers}
            if len(roles) > 1:
                raise _error("segment-report repeated metric block role is not independently bound")
            independent_roles.append(next(iter(roles)) if roles else None)
        if independent_roles[0] is None and independent_roles[1] is None:
            raise _error("segment-report repeated metric block has no independent role")
        expected_roles = list(independent_roles)
        if expected_roles[0] is None:
            expected_roles[0] = (
                "COMPARATIVE_PERIOD" if expected_roles[1] == "CURRENT_PERIOD" else "CURRENT_PERIOD"
            )
        if expected_roles[1] is None:
            expected_roles[1] = (
                "COMPARATIVE_PERIOD" if expected_roles[0] == "CURRENT_PERIOD" else "CURRENT_PERIOD"
            )
        if set(expected_roles) != {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}:
            raise _error("segment-report repeated metric block roles are not complementary")
        expected_owner_authority: list[dict[str, Any]] = []
        for pair, role in zip(pairs, expected_roles, strict=True):
            carriers = [receipt for receipt in pair if independently_resolved_role(receipt)]
            targets = [receipt for receipt in pair if receipt in target_receipts]
            if len(carriers) + len(targets) != len(pair) or not targets and not carriers:
                raise _error("segment-report repeated metric block target set drifted")
            if any(
                visible_declared_roles(receipt)
                or receipt.get("period_role") != role
                or receipt.get("period_assignment_rule")
                != "MISSING_PERIOD_FROM_REPEATED_ADJACENT_METRIC_BLOCK_ROLE"
                for receipt in targets
            ):
                raise _error("segment-report repeated metric block target role drifted")
            for receipt in targets:
                authority = _segment_owner_period_authority_for_signature_v1(
                    owner_receipt=owner_receipt,
                    role=role,
                    signature=_segment_declared_metric_signature_v1(receipt, compiled_specs),
                )
                if not authority:
                    raise _error("segment-report repeated metric block endpoint is unauthenticated")
                expected_owner_authority.extend(authority)
            expected_carrier_regions.extend(receipt["region"] for receipt in carriers)
            expected_target_regions.extend(receipt["region"] for receipt in targets)
            expected_blocks.append(
                {
                    "period_role": role,
                    "regions": [receipt["region"] for receipt in pair],
                    "slot_metric_signatures": [
                        list(_segment_declared_metric_signature_v1(receipt, compiled_specs))
                        for receipt in pair
                    ],
                }
            )
        expected_owner_authority = sorted(
            {
                canonical_json_sha256_v1(item): canonical_clone_v1(item)
                for item in expected_owner_authority
            }.values(),
            key=canonical_json_sha256_v1,
        )
        if (
            {block["period_role"] for block in expected_blocks}
            != {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
            or not same_typed_json_v1(block_axis, expected_blocks)
            or not same_typed_json_v1(carrier_regions, expected_carrier_regions)
            or not same_typed_json_v1(target_regions, expected_target_regions)
            or not same_typed_json_v1(
                evidence.get("owner_period_authority_axis"), expected_owner_authority
            )
        ):
            raise _error("segment-report repeated metric block receipt drifted")

    for evidence, target_receipt in split_combined_evidence:
        if set(evidence) != {
            "binding_mode",
            "branch",
            "carrier_regions",
            "carrier_role",
            "metric_layout_by_role",
            "orientation",
            "owner_period_authority_axis",
            "rule",
            "target_metric_signature",
            "target_regions",
            "target_role",
            "unit",
        } or not same_typed_json_v1(evidence.get("target_regions"), [target_receipt.get("region")]):
            raise _error("segment-report split-combined period evidence is invalid")
        carrier_regions = evidence.get("carrier_regions")
        if type(carrier_regions) is not list or len(carrier_regions) != 2:
            raise _error("segment-report split-combined carrier pair is absent")
        carrier_receipts = [
            receipt_by_region.get(canonical_json_sha256_v1(region)) for region in carrier_regions
        ]
        if any(receipt is None for receipt in carrier_receipts):
            raise _error("segment-report split-combined carrier is outside receipt axis")
        first, second = carrier_receipts
        target_region = target_receipt["region"]
        carrier_region = first["region"]
        carrier_geometry = _segment_period_pair_geometry_v1(carrier_receipts)
        expected_binding_mode = (
            "SPLIT_THEN_COMBINED"
            if carrier_region["selected_page_ordinal"] + 1 == target_region["selected_page_ordinal"]
            and carrier_region["physical_page"] + 1 == target_region["physical_page"]
            else "COMBINED_THEN_SPLIT"
            if target_region["selected_page_ordinal"] + 1 == carrier_region["selected_page_ordinal"]
            and target_region["physical_page"] + 1 == carrier_region["physical_page"]
            else None
        )
        first_signature = _segment_declared_metric_signature_v1(first, compiled_specs)
        second_signature = _segment_declared_metric_signature_v1(second, compiled_specs)
        target_signature = _segment_declared_metric_signature_v1(target_receipt, compiled_specs)
        carrier_roles = {independently_resolved_role(first), independently_resolved_role(second)}
        carrier_role = next(iter(carrier_roles)) if len(carrier_roles) == 1 else None
        target_role = (
            "COMPARATIVE_PERIOD"
            if carrier_role == "CURRENT_PERIOD"
            else "CURRENT_PERIOD"
            if carrier_role == "COMPARATIVE_PERIOD"
            else None
        )
        carrier_layout = {
            **_segment_declared_metric_layout_v1(first, compiled_specs),
            **_segment_declared_metric_layout_v1(second, compiled_specs),
        }
        target_layout = _segment_declared_metric_layout_v1(target_receipt, compiled_specs)
        owner_axis = owner_receipt.get("reporting_period_axis", [])
        expected_owner_authority: list[dict[str, Any]] = []
        valid_owner = type(owner_axis) is list and target_role is not None
        for temporal_class in sorted(
            {
                temporal_class
                for metric in target_signature
                if (temporal_class := _metric_temporal_class_v1(metric)) is not None
            }
        ):
            matches = (
                [
                    item
                    for item in owner_axis
                    if item.get("period_role") == target_role
                    and item.get("temporal_class") == temporal_class
                ]
                if type(owner_axis) is list
                else []
            )
            if not matches and type(owner_axis) is list:
                matches = [
                    item
                    for item in owner_axis
                    if item.get("period_role") == target_role
                    and item.get("temporal_class") == "GENERAL"
                ]
            if len({item.get("period_end") for item in matches}) != 1:
                valid_owner = False
            expected_owner_authority.extend(matches)
        expected_owner_authority = sorted(
            {
                canonical_json_sha256_v1(item): canonical_clone_v1(item)
                for item in expected_owner_authority
            }.values(),
            key=canonical_json_sha256_v1,
        )
        local_section_roles = {
            period_role_by_year[item.get("period_year")]
            for item in target_receipt.get("local_period_end_axis", [])
            if item.get("carrier_kind") == "SECTION_TITLE"
            and item.get("period_year") in period_role_by_year
        }
        if (
            carrier_geometry is None
            or expected_binding_mode is None
            or target_region["section_id"] != carrier_region["section_id"]
            or int(target_region["table_id"][1:]) != carrier_geometry[3][0]
            or not first_signature
            or not second_signature
            or not set(first_signature).isdisjoint(second_signature)
            or tuple(sorted((*first_signature, *second_signature))) != target_signature
            or carrier_role is None
            or target_role is None
            or visible_declared_roles(target_receipt)
            or target_receipt.get("period_role") != target_role
            or target_receipt.get("period_assignment_rule")
            != "MISSING_PERIOD_FROM_ADJACENT_SPLIT_COMBINED_METRIC_BLOCK_COMPLEMENT"
            or local_section_roles
            and local_section_roles != {target_role}
            or {first.get("branch"), second.get("branch"), target_receipt.get("branch")}
            != {evidence.get("branch")}
            or {first.get("unit"), second.get("unit"), target_receipt.get("unit")}
            != {evidence.get("unit")}
            or evidence.get("unit") is None
            or {
                first.get("orientation"),
                second.get("orientation"),
                target_receipt.get("orientation"),
            }
            != {evidence.get("orientation")}
            or target_layout != carrier_layout
            or not valid_owner
            or evidence.get("binding_mode") != expected_binding_mode
            or evidence.get("carrier_role") != carrier_role
            or evidence.get("target_role") != target_role
            or evidence.get("target_metric_signature") != list(target_signature)
            or not same_typed_json_v1(evidence.get("metric_layout_by_role"), target_layout)
            or not same_typed_json_v1(
                evidence.get("owner_period_authority_axis"), expected_owner_authority
            )
        ):
            raise _error("segment-report split-combined period binding drifted")

    for evidence, target_receipt in sibling_evidence:
        if set(evidence) != {
            "carrier_metric_signatures",
            "carrier_regions",
            "period_role",
            "rule",
            "target_metric_signature",
            "target_regions",
        }:
            raise _error("segment-report sibling period evidence is invalid")
        target_region = target_receipt.get("region")
        if not same_typed_json_v1(evidence.get("target_regions"), [target_region]):
            raise _error("segment-report sibling period target binding drifted")
        target_signature = _segment_declared_metric_signature_v1(target_receipt, compiled_specs)
        if (
            not target_signature
            or evidence.get("target_metric_signature") != list(target_signature)
            or visible_declared_roles(target_receipt)
            or target_receipt.get("period_role") != evidence.get("period_role")
        ):
            raise _error("segment-report sibling period target semantics drifted")
        carrier_regions = evidence.get("carrier_regions")
        if type(carrier_regions) is not list or not carrier_regions:
            raise _error("segment-report sibling period carriers are absent")
        carrier_receipts = [
            receipt_by_region.get(canonical_json_sha256_v1(region)) for region in carrier_regions
        ]
        if any(receipt is None for receipt in carrier_receipts):
            raise _error("segment-report sibling period carrier is outside receipt axis")
        block_receipts = [
            receipt
            for receipt in table_receipts
            if receipt.get("branch") == target_receipt.get("branch")
            and all(
                receipt.get("region", {}).get(key) == target_region.get(key)
                for key in ("selected_page_ordinal", "physical_page", "section_id")
            )
        ]
        if (
            sum(
                _segment_declared_metric_signature_v1(receipt, compiled_specs) == target_signature
                for receipt in block_receipts
            )
            != 1
        ):
            raise _error("segment-report sibling period target signature is not unique")
        expected_carriers = [
            receipt
            for receipt in block_receipts
            if receipt is not target_receipt
            and visible_declared_roles(receipt) == {evidence.get("period_role")}
            and set(_segment_declared_metric_signature_v1(receipt, compiled_specs)).isdisjoint(
                target_signature
            )
        ]
        if (
            not expected_carriers
            or [receipt["region"] for receipt in expected_carriers] != carrier_regions
            or evidence.get("carrier_metric_signatures")
            != [
                list(_segment_declared_metric_signature_v1(receipt, compiled_specs))
                for receipt in expected_carriers
            ]
        ):
            raise _error("segment-report sibling period carrier binding drifted")

    for evidence, target_receipts in evidence_groups.values():
        if len(target_receipts) != 2 or not same_typed_json_v1(
            evidence["target_regions"],
            [receipt["region"] for receipt in target_receipts],
        ):
            raise _error("segment-report structural period target binding drifted")
        carrier = evidence["carrier"]
        if (
            set(carrier)
            != {
                "branch",
                "carrier_regions",
                "metric_signature",
                "order",
                "pair_binding_mode",
                "shape_axis",
            }
            or type(carrier.get("carrier_regions")) is not list
        ):
            raise _error("segment-report structural period carrier is invalid")
        carrier_receipts = [
            receipt_by_region.get(canonical_json_sha256_v1(region))
            for region in carrier["carrier_regions"]
        ]
        if len(carrier_receipts) != 2 or any(receipt is None for receipt in carrier_receipts):
            raise _error("segment-report structural period carrier is outside receipt axis")
        target_branches = {receipt.get("branch") for receipt in target_receipts}
        carrier_branches = {receipt.get("branch") for receipt in carrier_receipts}
        if (
            len(target_branches) != 1
            or len(carrier_branches) != 1
            or target_branches == carrier_branches
        ):
            raise _error("segment-report structural period branches are invalid")
        target_signatures = {
            _segment_declared_metric_signature_v1(receipt, compiled_specs)
            for receipt in target_receipts
        }
        carrier_signatures = {
            _segment_declared_metric_signature_v1(receipt, compiled_specs)
            for receipt in carrier_receipts
        }
        if (
            len(target_signatures) != 1
            or target_signatures != carrier_signatures
            or not next(iter(target_signatures))
        ):
            raise _error("segment-report structural period metric signature drifted")
        target_signature = next(iter(target_signatures))
        carrier_roles = []
        for receipt in carrier_receipts:
            visible_roles = {
                period_role_by_year.get(cell.get("period_year"))
                for cell in receipt.get("cell_axis", [])
                if cell.get("period_year") is not None
            }
            visible_roles.discard(None)
            carrier_roles.append(next(iter(visible_roles)) if len(visible_roles) == 1 else None)
        expected_order = (
            "CURRENT_FIRST"
            if carrier_roles == ["CURRENT_PERIOD", "COMPARATIVE_PERIOD"]
            else "COMPARATIVE_FIRST"
            if carrier_roles == ["COMPARATIVE_PERIOD", "CURRENT_PERIOD"]
            else None
        )
        target_roles = [receipt.get("period_role") for receipt in target_receipts]
        expected_target_roles = (
            ["CURRENT_PERIOD", "COMPARATIVE_PERIOD"]
            if expected_order == "CURRENT_FIRST"
            else ["COMPARATIVE_PERIOD", "CURRENT_PERIOD"]
            if expected_order == "COMPARATIVE_FIRST"
            else None
        )
        target_geometry = _segment_period_pair_geometry_v1(target_receipts)
        carrier_geometry = _segment_period_pair_geometry_v1(carrier_receipts)
        pair_binding_mode = (
            _segment_period_pair_binding_mode_v1(target_geometry, carrier_geometry)
            if target_geometry is not None and carrier_geometry is not None
            else None
        )
        expected_carrier = {
            "branch": next(iter(carrier_branches)),
            "carrier_regions": [receipt["region"] for receipt in carrier_receipts],
            "metric_signature": list(target_signature),
            "order": expected_order,
            "pair_binding_mode": pair_binding_mode,
            "shape_axis": [_segment_table_period_shape_v1(receipt) for receipt in carrier_receipts],
        }
        if (
            expected_order is None
            or expected_target_roles != target_roles
            or any(
                cell.get("period_year") is not None
                for receipt in target_receipts
                for cell in receipt.get("cell_axis", [])
            )
            or [_segment_table_period_shape_v1(receipt) for receipt in target_receipts]
            != expected_carrier["shape_axis"]
            or target_geometry is None
            or carrier_geometry is None
            or pair_binding_mode is None
            or not same_typed_json_v1(carrier, expected_carrier)
        ):
            raise _error("segment-report structural period carrier binding drifted")


def _resolve_segment_period_end_assignments_v1(
    table_receipts: Sequence[Mapping[str, Any]],
    *,
    owner_receipt: Mapping[str, Any],
    period_role_by_year: Mapping[int, str],
) -> dict[str, Any]:
    """Bind source-visible endpoints to source cells after period roles resolve."""

    owner_axis = owner_receipt.get("reporting_period_axis", [])
    if type(owner_axis) is not list:
        raise _error("segment-report owner period axis is invalid")
    owner_by_role_and_class: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in owner_axis:
        if (
            type(item) is not dict
            or item.get("period_role") not in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
            or type(item.get("period_end")) is not str
            or type(item.get("period_year")) is not int
            or type(item.get("carrier_axis")) is not list
            or item.get("temporal_class") not in {"STOCK", "FLOW", "GENERAL"}
        ):
            raise _error("segment-report owner period authority is invalid")
        try:
            parsed = date.fromisoformat(item["period_end"])
        except ValueError as exc:
            raise _error("segment-report owner period endpoint is invalid") from exc
        if parsed.year != item["period_year"]:
            raise _error("segment-report owner period year disagrees with endpoint")
        owner_by_role_and_class.setdefault(
            (item["period_role"], item["temporal_class"]), []
        ).append(item)

    def cell_role(receipt: Mapping[str, Any], cell: Mapping[str, Any]) -> str | None:
        metric_roles = receipt.get("period_role_by_metric", {})
        assigned = metric_roles.get(cell.get("metric_role")) or receipt.get("period_role")
        visible = period_role_by_year.get(cell.get("period_year"))
        if assigned is not None and visible is not None and assigned != visible:
            raise _error("segment-report assigned period contradicts visible period")
        return assigned or visible

    reasons: set[str] = set()
    local_assignments: dict[tuple[str, str], dict[str, Any]] = {}
    receipt_by_region: dict[str, Mapping[str, Any]] = {}
    for receipt in table_receipts:
        region = receipt.get("region")
        region_key = canonical_json_sha256_v1(region)
        receipt_by_region[region_key] = receipt
        evidence = receipt.get("local_period_end_axis")
        if type(evidence) is not list:
            raise _error("segment-report local period endpoint axis is absent")
        for item in evidence:
            if (
                type(item) is not dict
                or set(item)
                != {
                    "carrier_kind",
                    "column_id",
                    "period_end",
                    "period_year",
                    "row_id",
                    "source_exact",
                }
                or item.get("carrier_kind")
                not in {
                    "COLUMN_HEADER_PATH",
                    "ROW_HEADER_PATH",
                    "SECTION_TITLE",
                    "TABLE_TITLE",
                }
                or type(item.get("period_end")) is not str
                or type(item.get("period_year")) is not int
                or type(item.get("source_exact")) is not str
                or item["period_end"] not in _period_ends(item["source_exact"])
                or date.fromisoformat(item["period_end"]).year != item["period_year"]
            ):
                raise _error("segment-report local period endpoint evidence is invalid")
        for cell in receipt.get("cell_axis", []):
            role = cell_role(receipt, cell)
            if role is None:
                continue
            cell_ref = cell.get("cell_ref")
            if type(cell_ref) is not dict:
                raise _error("segment-report period cell reference is invalid")
            applicable = [
                item
                for item in evidence
                if (
                    item["column_id"] == cell_ref.get("column_id")
                    or item["row_id"] == cell_ref.get("row_id")
                )
                and (
                    cell.get("period_year") is None
                    or item["period_year"] == cell.get("period_year")
                )
            ]
            if not applicable:
                applicable = [
                    item
                    for item in evidence
                    if item["carrier_kind"] == "TABLE_TITLE"
                    and (
                        cell.get("period_year") is None
                        or item["period_year"] == cell.get("period_year")
                    )
                ]
            if not applicable:
                applicable = [
                    item
                    for item in evidence
                    if item["carrier_kind"] == "SECTION_TITLE"
                    and (
                        cell.get("period_year") is None
                        or item["period_year"] == cell.get("period_year")
                    )
                ]
            applicable = [
                item
                for item in applicable
                if period_role_by_year.get(item["period_year"], role) == role
            ]
            dates = {item["period_end"] for item in applicable}
            if len(dates) > 1:
                reasons.add("SEGMENT_CELL_PERIOD_END_CONFLICT")
                continue
            if len(dates) == 1:
                cell_key = canonical_json_sha256_v1(cell_ref)
                local_assignments[(region_key, cell_key)] = {
                    "authority_axis": canonical_clone_v1(applicable),
                    "authority_class": "LOCAL_EXPLICIT_PERIOD_END",
                    "carrier_cell_ref": canonical_clone_v1(cell_ref),
                    "carrier_region": canonical_clone_v1(region),
                    "period_end": next(iter(dates)),
                    "period_role": role,
                }

    # Gemini frequently attaches one merged period header only to the first
    # physical column in a block.  A unique explicit endpoint may therefore
    # propagate across the same table/period role; two distinct endpoints do
    # not propagate and will fail the equation/duplicate consistency gates.
    for region_key, receipt in receipt_by_region.items():
        cells_by_role: dict[str, list[Mapping[str, Any]]] = {}
        for cell in receipt["cell_axis"]:
            role = cell_role(receipt, cell)
            if role is not None:
                cells_by_role.setdefault(role, []).append(cell)
        for role, role_cells in cells_by_role.items():
            carriers = [
                local_assignments[(region_key, canonical_json_sha256_v1(cell["cell_ref"]))]
                for cell in role_cells
                if (region_key, canonical_json_sha256_v1(cell["cell_ref"])) in local_assignments
            ]
            carrier_dates = {item["period_end"] for item in carriers}
            if len(carrier_dates) != 1:
                continue
            for cell in role_cells:
                cell_key = canonical_json_sha256_v1(cell["cell_ref"])
                if (region_key, cell_key) in local_assignments:
                    continue
                local_assignments[(region_key, cell_key)] = {
                    "authority_axis": canonical_clone_v1(carriers),
                    "authority_class": "UNIQUE_LOCAL_MERGED_PERIOD_END_PROPAGATION",
                    "carrier_cell_ref": None,
                    "carrier_region": canonical_clone_v1(receipt["region"]),
                    "period_end": next(iter(carrier_dates)),
                    "period_role": role,
                }

    assignments: list[dict[str, Any]] = []
    for receipt in table_receipts:
        region = receipt["region"]
        region_key = canonical_json_sha256_v1(region)
        cross_evidence = receipt.get("period_assignment_evidence")
        carrier_regions = []
        if type(cross_evidence) is dict:
            carrier_regions = cross_evidence.get("carrier", {}).get("carrier_regions", [])
        carrier_region_keys = {canonical_json_sha256_v1(item) for item in carrier_regions}
        for cell in receipt["cell_axis"]:
            role = cell_role(receipt, cell)
            if role is None:
                continue
            cell_ref = cell["cell_ref"]
            cell_key = canonical_json_sha256_v1(cell_ref)
            resolved = local_assignments.get((region_key, cell_key))
            if resolved is None and carrier_region_keys:
                carrier_matches = [
                    assignment
                    for (
                        candidate_region_key,
                        candidate_cell_key,
                    ), assignment in local_assignments.items()
                    if candidate_region_key in carrier_region_keys
                    and assignment["period_role"] == role
                    and any(
                        canonical_json_sha256_v1(candidate["cell_ref"]) == candidate_cell_key
                        and candidate.get("metric_role") == cell.get("metric_role")
                        for candidate_receipt_key, candidate_receipt in receipt_by_region.items()
                        if candidate_receipt_key == candidate_region_key
                        for candidate in candidate_receipt["cell_axis"]
                    )
                ]
                carrier_dates = {item["period_end"] for item in carrier_matches}
                if len(carrier_dates) > 1:
                    reasons.add("SEGMENT_STRUCTURAL_PERIOD_END_CARRIER_CONFLICT")
                elif len(carrier_dates) == 1:
                    resolved = {
                        "authority_axis": canonical_clone_v1(carrier_matches),
                        "authority_class": "STRUCTURAL_CROSS_BRANCH_PERIOD_PAIR",
                        "period_end": next(iter(carrier_dates)),
                        "period_role": role,
                    }
            if resolved is None:
                temporal_class = _metric_temporal_class_v1(cell.get("metric_role"))
                owner_matches = (
                    owner_by_role_and_class.get((role, temporal_class), [])
                    if temporal_class is not None
                    else []
                )
                if not owner_matches:
                    owner_matches = owner_by_role_and_class.get((role, "GENERAL"), [])
                owner_dates = {item["period_end"] for item in owner_matches}
                if len(owner_dates) == 1:
                    resolved = {
                        "authority_axis": canonical_clone_v1(owner_matches),
                        "authority_class": "TYPED_PRIMARY_PERIOD_END",
                        "period_end": next(iter(owner_dates)),
                        "period_role": role,
                    }
                elif len(owner_dates) > 1:
                    reasons.add("SEGMENT_OWNER_PERIOD_END_CONFLICT")
            body = {
                "authority_axis": [] if resolved is None else resolved["authority_axis"],
                "authority_class": (
                    "NO_EXACT_PERIOD_END" if resolved is None else resolved["authority_class"]
                ),
                "cell_ref": canonical_clone_v1(cell_ref),
                "period_end": None if resolved is None else resolved["period_end"],
                "period_role": role,
                "region": canonical_clone_v1(region),
            }
            assignments.append(
                {
                    "period_assignment_id": "gjsrmv1:period:" + canonical_json_sha256_v1(body),
                    **body,
                }
            )
    assignments.sort(key=lambda item: canonical_json_sha256_v1(item["cell_ref"]))
    return {
        "period_assignment_axis": assignments,
        "reasons": sorted(reasons),
        "rule": "SOURCE_VISIBLE_LOCAL_THEN_BOUND_STRUCTURAL_OR_TYPED_PRIMARY_PERIOD_END",
    }


def _axis_role(surface: Any, aliases_by_role: Mapping[str, Sequence[str]]) -> list[str]:
    folded = _norm_semantic_label(surface)
    folded = re.sub(r"\s+(?:\*|[a-z])$", "", folded).strip()
    folded = re.sub(
        r"\b(?:don vi(?: tinh)? )?(?:nghin|trieu|ty)\s+(?:vnd|dong)\b",
        " ",
        folded,
    )
    folded = re.sub(r"\bnam\s+20\d{2}\b|\b20\d{2}\b", " ", folded)
    folded = " ".join(folded.split())
    return sorted(role for role, aliases in aliases_by_role.items() if folded in aliases)


def _role_from_authoritative_surfaces(
    surfaces: Sequence[Any], aliases_by_role: Mapping[str, Sequence[str]]
) -> list[str]:
    """Resolve the deepest visible graph label without unioning its ancestors.

    Gemini may repeat an ancestor and a leaf in ``hierarchy_path_exact`` or a
    column header path.  The leaf is the authoritative label; combining every
    path member would turn e.g. ``Tài sản / TSCĐ`` into two conflicting
    metrics.  A conflict at the same deepest surface remains ambiguous.
    """

    for surface in reversed(list(surfaces)):
        roles = _axis_role(surface, aliases_by_role)
        if roles:
            return roles
    return []


def _metric_roles_for_row(row: Mapping[str, Any], compiled: Mapping[str, Any]) -> list[str]:
    label = row.get("label_exact")
    path = row.get("hierarchy_path_exact")
    path_roles = _role_from_authoritative_surfaces(
        path if type(path) is list else [], compiled["metric_aliases_by_role"]
    )
    if type(label) is str and label.strip():
        roles = _role_from_authoritative_surfaces([label], compiled["metric_aliases_by_role"])
        if roles:
            return sorted(set(roles) | set(path_roles))
        if _is_generic_total_label(label):
            return path_roles
        if _ORDINAL_ONLY.fullmatch(unicodedata.normalize("NFKC", label)) is None:
            return roles
    return path_roles


def _axis_roles_for_row(
    row: Mapping[str, Any], aliases_by_role: Mapping[str, Sequence[str]]
) -> list[str]:
    label = row.get("label_exact")
    path = row.get("hierarchy_path_exact")
    path_roles = _role_from_authoritative_surfaces(
        path if type(path) is list else [], aliases_by_role
    )
    if type(label) is str and label.strip():
        roles = _role_from_authoritative_surfaces([label], aliases_by_role)
        if roles:
            return sorted(set(roles) | set(path_roles))
        if _ORDINAL_ONLY.fullmatch(unicodedata.normalize("NFKC", label)) is None:
            return roles
    return path_roles


def _years(surfaces: Sequence[Any]) -> set[int]:
    return {
        int(year)
        for surface in surfaces
        if type(surface) is str
        for year in _YEAR.findall(unicodedata.normalize("NFKC", surface))
    }


def _period_ends(surface: Any) -> set[str]:
    """Parse source-visible reporting endpoints without deriving one from a bare year.

    A bare year never acquires ``12-31``.  It may be joined to a separately
    authenticated full-date carrier later, but it is not itself a date.
    For an explicit ``from ... to ...`` range, only the later visible endpoint
    is returned.
    """

    if type(surface) is not str or not surface.strip():
        return set()
    normalized = unicodedata.normalize("NFKC", surface)
    folded = "".join(
        character
        for character in unicodedata.normalize("NFD", normalized.lower())
        if unicodedata.category(character) != "Mn"
    ).translate(str.maketrans({"đ": "d"}))

    def parsed_dates(source: str) -> list[date]:
        result: list[date] = []
        for pattern in (_DATE_DMY, _DATE_WORDS):
            for match in pattern.finditer(source):
                try:
                    result.append(
                        date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
                    )
                except ValueError:
                    continue
        return result

    if re.search(r"\b(?:tu|giai doan)\b", folded) is not None:
        range_ends: list[date] = []
        for marker in re.finditer(r"\bden\b", folded):
            tail = folded[marker.end() :]
            candidates: list[tuple[int, date]] = []
            for pattern in (_DATE_DMY, _DATE_WORDS):
                match = pattern.search(tail)
                if match is None:
                    continue
                try:
                    candidates.append(
                        (
                            match.start(),
                            date(
                                int(match.group(3)),
                                int(match.group(2)),
                                int(match.group(1)),
                            ),
                        )
                    )
                except ValueError:
                    continue
            if candidates:
                range_ends.append(min(candidates, key=lambda item: item[0])[1])
        if range_ends:
            return {item.isoformat() for item in range_ends}
    unique_dates = sorted(set(parsed_dates(folded)))
    return {item.isoformat() for item in unique_dates}


def _years_from_authoritative_surfaces(surfaces: Sequence[Any]) -> set[int]:
    """Resolve local period leaves while retaining contradictory leaf years."""

    parsed = [_years([surface]) for surface in surfaces]
    singleton_years = {next(iter(years)) for years in parsed if len(years) == 1}
    if singleton_years:
        return singleton_years
    for years in reversed(parsed):
        if years:
            return years
    return set()


def _source_axis_label(
    surfaces: Sequence[Any], *, fallback: str, compiled: Mapping[str, Any]
) -> str:
    for surface in reversed(surfaces):
        folded = _norm_semantic_label(surface)
        if not folded:
            continue
        for alias in sorted(compiled["unit_binding_by_alias"], key=len, reverse=True):
            folded = folded.replace(alias, " ")
        folded = re.sub(r"\bnam\s+20\d{2}\b|\b20\d{2}\b", " ", folded)
        folded = " ".join(folded.split())
        if folded:
            return folded
    return fallback


def _is_declared_source_only_axis(label: str, compiled: Mapping[str, Any]) -> bool:
    declared = set(compiled["source_only_axis_aliases"])
    if label in declared:
        return True
    remaining = f" {label} "
    matched = 0
    for alias in sorted(declared, key=len, reverse=True):
        token = f" {alias} "
        while token in remaining:
            remaining = remaining.replace(token, " ", 1)
            matched += 1
    residual_tokens = remaining.split()
    return matched > 1 and set(residual_tokens) <= {"hoac", "va"}


def _valid_integer_money_surface(value: Any) -> bool:
    if type(value) is not str or not value.strip():
        return False
    body = value.strip()
    if all(character in {"-", "_"} for character in body):
        return True
    if body.startswith("(") or body.endswith(")"):
        if not (body.startswith("(") and body.endswith(")")):
            return False
        body = body[1:-1].strip()
    if body.startswith("-"):
        body = body[1:].strip()
    return body.isdigit() or _GROUPED_INTEGER.fullmatch(body) is not None


def _cell(value: Any, *, region: Mapping[str, Any], row_id: str, column_id: str) -> dict[str, Any]:
    ref = {
        "column_id": column_id,
        "page_json_version_id": region["page_json_version_id"],
        "physical_page": region["physical_page"],
        "row_id": row_id,
        "section_id": region["section_id"],
        "table_id": region["table_id"],
    }
    if value is None:
        return {"cell_ref": ref, "coefficient": None, "source_text": None, "state": "SOURCE_BLANK"}
    stripped_numeric_footnote = (
        _TRAILING_NUMERIC_SUPERSCRIPT.sub("", value) if type(value) is str else value
    )
    normalized = (
        unicodedata.normalize("NFKC", stripped_numeric_footnote).translate(
            _UNICODE_ACCOUNTING_SIGNS
        )
        if type(stripped_numeric_footnote) is str
        else stripped_numeric_footnote
    )
    try:
        if not _valid_integer_money_surface(normalized):
            raise ValueError("money surface grouping is invalid")
        parsed = _money(normalized)
    except ValueError:
        if (
            type(normalized) is str
            and normalized.strip().endswith(")")
            and not normalized.strip().startswith("(")
        ):
            unsigned = normalized.strip()[:-1].strip()
            if unsigned.replace(".", "").replace(",", "").replace(" ", "").isdigit():
                magnitude = int(unsigned.replace(".", "").replace(",", "").replace(" ", ""))
                return {
                    "cell_ref": ref,
                    "coefficient": None,
                    "coefficient_candidates": [-magnitude, magnitude],
                    "source_text": value,
                    "state": "AMBIGUOUS_UNBALANCED_CLOSING_PARENTHESIS",
                }
        return {
            "cell_ref": ref,
            "coefficient": None,
            "source_text": value,
            "state": "INVALID_MONEY_SOURCE",
        }
    parsed["source_text"] = value
    if stripped_numeric_footnote != value:
        parsed["state"] = "NORMALIZED_TRAILING_FOOTNOTE_INTEGER"
    elif normalized != value and parsed["state"] == "RAW_SIGNED_INTEGER":
        parsed["state"] = "NORMALIZED_UNICODE_ACCOUNTING_INTEGER"
    return {"cell_ref": ref, **parsed}


def _parse_table(
    region: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    compiled: Mapping[str, Any],
    *,
    branch_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    reasons = []
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or not columns or type(rows) is not list or not rows:
        return {
            "cells": [],
            "equations": [],
            "period_year": None,
            "reasons": ["SEGMENT_TABLE_SHAPE_INVALID"],
            "receipt": {},
        }
    if any(
        type(row) is not dict
        or type(row.get("values_exact")) is not list
        or len(row["values_exact"]) != len(columns)
        for row in rows
    ):
        return {
            "cells": [],
            "equations": [],
            "period_year": None,
            "reasons": ["SEGMENT_TABLE_ROW_WIDTH_MISMATCH"],
            "receipt": {},
        }
    money_positions = [
        index
        for index, column in enumerate(columns)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if not money_positions:
        return {
            "cells": [],
            "equations": [],
            "period_year": None,
            "reasons": ["SEGMENT_TABLE_HAS_NO_MONEY_COLUMNS"],
            "receipt": {},
        }
    money_header_paths = [
        columns[position].get("header_path_exact") or [] for position in money_positions
    ]
    common_header_surfaces = (
        set.intersection(
            *(
                {unicodedata.normalize("NFKC", surface) for surface in path if type(surface) is str}
                for path in money_header_paths
            )
        )
        if money_header_paths
        else set()
    )
    common_multi_year_surfaces = {
        surface for surface in common_header_surfaces if len(_years([surface])) > 1
    }
    local_column_year_axis = [
        _years_from_authoritative_surfaces(
            [
                surface
                for surface in path
                if type(surface) is not str
                or unicodedata.normalize("NFKC", surface) not in common_multi_year_surfaces
            ]
        )
        for path in money_header_paths
    ]
    distinct_explicit_years = {
        next(iter(years)) for years in local_column_year_axis if len(years) == 1
    }
    column_labels = [
        _source_axis_label(
            columns[position].get("header_path_exact") or [],
            fallback=f"c{position + 1}",
            compiled=compiled,
        )
        for position in money_positions
    ]
    if (
        any(not years for years in local_column_year_axis)
        and len(distinct_explicit_years) == 2
        and all(len(years) <= 1 for years in local_column_year_axis)
        and len(local_column_year_axis) % 2 == 0
    ):
        block_width = len(local_column_year_axis) // 2
        if column_labels[:block_width] == column_labels[block_width:]:
            block_year_axes = [
                set().union(*local_column_year_axis[start : start + block_width])
                for start in (0, block_width)
            ]
            if all(len(years) == 1 for years in block_year_axes) and (
                block_year_axes[0] != block_year_axes[1]
            ):
                for block_index, years in enumerate(block_year_axes):
                    block_year = next(iter(years))
                    start = block_index * block_width
                    for index in range(start, start + block_width):
                        if not local_column_year_axis[index]:
                            local_column_year_axis[index] = {block_year}
        # A merged graph may instead repeat each semantic column adjacently:
        # [axis-current, axis-comparative, next-current, next-comparative].
        # One or more explicit pairs authenticate the shared order; every
        # remaining pair must be completely undated and structurally identical.
        if any(not years for years in local_column_year_axis):
            adjacent_pairs = [
                (index, index + 1) for index in range(0, len(local_column_year_axis), 2)
            ]
            if all(column_labels[left] == column_labels[right] for left, right in adjacent_pairs):
                explicit_orders = {
                    (
                        next(iter(local_column_year_axis[left])),
                        next(iter(local_column_year_axis[right])),
                    )
                    for left, right in adjacent_pairs
                    if len(local_column_year_axis[left]) == 1
                    and len(local_column_year_axis[right]) == 1
                }
                partially_dated_pair = any(
                    bool(local_column_year_axis[left]) != bool(local_column_year_axis[right])
                    for left, right in adjacent_pairs
                )
                if (
                    len(explicit_orders) == 1
                    and not partially_dated_pair
                    and set(next(iter(explicit_orders))) == distinct_explicit_years
                ):
                    first_year, second_year = next(iter(explicit_orders))
                    for left, right in adjacent_pairs:
                        if not local_column_year_axis[left]:
                            local_column_year_axis[left] = {first_year}
                            local_column_year_axis[right] = {second_year}
    column_years = set().union(*local_column_year_axis)
    title_years = _years([table.get("title_exact")])
    if column_years:
        default_year = next(iter(column_years)) if len(column_years) == 1 else None
    elif title_years:
        default_year = next(iter(title_years)) if len(title_years) == 1 else None
    else:
        default_year = None
    branches, _ = _branch_and_axis_counts(table, section, compiled)
    authority_branch = (
        branch_authority.get("branch_role") if type(branch_authority) is dict else None
    )
    branch_axis_evidence = _branch_axis_evidence_v1(table, compiled)
    if len(branches) == 1 and (authority_branch is None or authority_branch == branches[0]):
        branch = branches[0]
    elif authority_branch is not None and _branch_authority_can_resolve_table_v1(
        branch_role=authority_branch,
        branches=branches,
        evidence=branch_axis_evidence,
    ):
        branch = authority_branch
    else:
        reasons.append("SEGMENT_BRANCH_AMBIGUOUS")
        branch = None
    alias_key = (
        "business_axis_aliases_by_role"
        if branch == "BUSINESS"
        else "geographic_axis_aliases_by_role"
    )
    axis_aliases = compiled.get(alias_key, {})
    opposite_axis_aliases = compiled.get(
        "geographic_axis_aliases_by_role"
        if branch == "BUSINESS"
        else "business_axis_aliases_by_role",
        {},
    )
    column_axes: list[dict[str, Any]] = []
    for position, local_years in zip(money_positions, local_column_year_axis, strict=True):
        index = position + 1
        column = columns[position]
        path = column.get("header_path_exact") if type(column) is dict else None
        surfaces = path if type(path) is list else []
        if len(local_years) > 1:
            reasons.append("SEGMENT_COLUMN_PERIOD_AMBIGUOUS")
        column_period_year = (
            next(iter(local_years))
            if len(local_years) == 1
            else default_year
            if not local_years and len(column_years) <= 1
            else None
        )
        roles = _role_from_authoritative_surfaces(surfaces, axis_aliases)
        if len(roles) > 1:
            reasons.append("SEGMENT_COLUMN_AXIS_AMBIGUOUS")
        role = roles[0] if len(roles) == 1 else None
        declared_source_only = None
        if role is None:
            source_label = _source_axis_label(surfaces, fallback=f"c{index}", compiled=compiled)
            declared_source_only = _is_declared_source_only_axis(source_label, compiled)
            if (
                _role_from_authoritative_surfaces(surfaces, opposite_axis_aliases)
                and not declared_source_only
            ):
                reasons.append("SEGMENT_AXIS_CONTRADICTS_SELECTED_BRANCH")
            role = f"SOURCE_ONLY:c{index}:" + source_label
        column_axes.append(
            {
                "axis_role": role,
                "column_id": f"c{index}",
                "declared_source_only": declared_source_only,
                "period_year": column_period_year,
                "source_path": canonical_clone_v1(surfaces),
            }
        )
    row_metric_roles = []
    row_metric_labels = []
    for row in rows:
        label = row.get("label_exact")
        path = (
            row.get("hierarchy_path_exact") if type(row.get("hierarchy_path_exact")) is list else []
        )
        surfaces = [label] if type(label) is str and label.strip() else path
        roles = _metric_roles_for_row(row, compiled)
        row_metric_roles.append(roles)
        row_metric_labels.append(
            _source_axis_label(
                surfaces,
                fallback=f"r{len(row_metric_labels) + 1}",
                compiled=compiled,
            )
        )
    metric_rows = sum(len(x) == 1 for x in row_metric_roles)
    # The usual form is metric rows x segment columns.  The transpose is
    # admitted only when row labels form the segment axis and column headers
    # form the metric axis uniquely.
    orientation = "METRIC_ROWS"
    cells = []
    equations = []
    if metric_rows:
        active_year = default_year
        axis_groups: dict[int | None, list[int]] = {}
        for index, item in enumerate(column_axes):
            axis_groups.setdefault(item["period_year"], []).append(index)
        if len(column_years) > 1 and None in axis_groups:
            reasons.append("SEGMENT_COLUMN_PERIOD_AMBIGUOUS")
        for positions in axis_groups.values():
            roles = [column_axes[index]["axis_role"] for index in positions]
            if len(roles) != len(set(roles)):
                reasons.append("DUPLICATE_SEGMENT_AXIS")
            if sum(role == "TOTAL" for role in roles) != 1:
                reasons.append("EXACTLY_ONE_VISIBLE_SEGMENT_TOTAL_REQUIRED")
        derived_roles: dict[int, str] = {}
        structural_group_rows: set[int] = {
            index
            for index, row in enumerate(rows)
            if row.get("row_kind") == "GROUP"
            and len(row_metric_roles[index]) == 1
            and all(row["values_exact"][position] is None for position in money_positions)
        }
        for index, row in enumerate(rows[:-1]):
            if len(row_metric_roles[index]) != 1:
                continue
            group_role = row_metric_roles[index][0]
            following = rows[index + 1]
            following_path = (
                following.get("hierarchy_path_exact")
                if type(following.get("hierarchy_path_exact")) is list
                else []
            )
            following_ancestor_roles = _role_from_authoritative_surfaces(
                [surface for surface in following_path if not _is_generic_total_label(surface)],
                compiled["metric_aliases_by_role"],
            )
            if (
                group_role
                and all(row["values_exact"][position] is None for position in money_positions)
                and _is_generic_total_label(following.get("label_exact"))
            ):
                if following_ancestor_roles and following_ancestor_roles != [group_role]:
                    reasons.append("SEGMENT_METRIC_GROUP_TOTAL_HIERARCHY_CONFLICT")
                    continue
                derived_roles[index + 1] = group_role
                structural_group_rows.add(index)
        for row_index, (row, roles, source_metric_label) in enumerate(
            zip(rows, row_metric_roles, row_metric_labels, strict=True), start=1
        ):
            row_label = row.get("label_exact")
            row_years = _years_from_authoritative_surfaces(
                [row_label]
                if type(row_label) is str and row_label.strip()
                else row.get("hierarchy_path_exact")
                if type(row.get("hierarchy_path_exact")) is list
                else []
            )
            if len(row_years) > 1:
                reasons.append("SEGMENT_ROW_PERIOD_AMBIGUOUS")
            elif len(row_years) == 1:
                active_year = next(iter(row_years))
            if len(roles) > 1:
                reasons.append("SEGMENT_METRIC_ROW_AMBIGUOUS")
                continue
            if row_index - 1 in structural_group_rows:
                continue
            role = roles[0] if len(roles) == 1 else derived_roles.get(row_index - 1)
            if role is None:
                if all(row["values_exact"][position] is None for position in money_positions):
                    continue
                role = f"SOURCE_ONLY_METRIC:r{row_index}:" + source_metric_label
            row_cells = [
                _cell(
                    row["values_exact"][position],
                    region=region,
                    row_id=f"r{row_index}",
                    column_id=f"c{position + 1}",
                )
                for position in money_positions
            ]
            mapped_metric = role in compiled["metric_offset_by_role"]
            if mapped_metric and any(cell["state"] == "INVALID_MONEY_SOURCE" for cell in row_cells):
                reasons.append("SEGMENT_MONEY_CELL_INVALID")
            for column_period, positions in axis_groups.items():
                resolved_period = (
                    column_period
                    if len(column_years) > 1 and column_period is not None
                    else active_year
                    if active_year is not None
                    else column_period
                )
                if (
                    len(column_years) > 1
                    and len(row_years) == 1
                    and column_period is not None
                    and active_year != column_period
                ):
                    reasons.append("SEGMENT_CELL_PERIOD_CONFLICT")
                total_positions = [
                    index for index in positions if column_axes[index]["axis_role"] == "TOTAL"
                ]
                if len(total_positions) != 1:
                    continue
                total = row_cells[total_positions[0]]
                terms = [row_cells[index] for index in positions if index != total_positions[0]]
                if mapped_metric and any(
                    "coefficient_candidates" in cell for cell in [total, *terms]
                ):
                    reasons.append("SEGMENT_MONEY_CELL_AMBIGUOUS")
                status = (
                    "NOT_TESTABLE_SOURCE_BLANK"
                    if total["coefficient"] is None
                    or any(cell["coefficient"] is None for cell in terms)
                    else "EXACT"
                    if sum(cell["coefficient"] for cell in terms) == total["coefficient"]
                    else "EXACT_ROUNDING_RESIDUAL"
                    if abs(sum(cell["coefficient"] for cell in terms) - total["coefficient"])
                    <= max(1, len(terms) // 2)
                    else "MISMATCH"
                )
                equations.append(
                    {
                        "branch": branch,
                        "computed_value": None
                        if status == "NOT_TESTABLE_SOURCE_BLANK"
                        else sum(cell["coefficient"] for cell in terms),
                        "metric_role": role,
                        "period_year": resolved_period,
                        "result_cell": total,
                        "status": status,
                        "term_cells": terms,
                    }
                )
                if mapped_metric and status == "MISMATCH":
                    reasons.append("VISIBLE_SEGMENT_TOTAL_MISMATCH")
            for axis, cell in zip(column_axes, row_cells, strict=True):
                resolved_period = (
                    axis["period_year"]
                    if len(column_years) > 1 and axis["period_year"] is not None
                    else active_year
                    if active_year is not None
                    else axis["period_year"]
                )
                cells.append(
                    {
                        "axis_role": axis["axis_role"],
                        "branch": branch,
                        "metric_role": role,
                        "period_year": resolved_period,
                        **cell,
                    }
                )
    else:
        orientation = "METRIC_COLUMNS"
        active_year = default_year
        metric_columns_axis: list[dict[str, Any]] = []
        for position, period_axis in zip(money_positions, column_axes, strict=True):
            index = position + 1
            column = columns[position]
            surfaces = column.get("header_path_exact") if type(column) is dict else []
            roles = _role_from_authoritative_surfaces(
                surfaces if type(surfaces) is list else [],
                compiled["metric_aliases_by_role"],
            )
            if len(roles) > 1:
                reasons.append("SEGMENT_METRIC_COLUMN_AMBIGUOUS")
            metric_role = roles[0] if len(roles) == 1 else None
            if metric_role is None:
                metric_role = f"SOURCE_ONLY_METRIC:c{index}:" + _source_axis_label(
                    surfaces, fallback=f"c{index}", compiled=compiled
                )
            metric_columns_axis.append(
                {
                    "column_id": f"c{index}",
                    "mapped_metric": len(roles) == 1,
                    "metric_role": metric_role,
                    "period_year": period_axis["period_year"],
                    "position": position,
                }
            )
        recognized_metrics = [
            item["metric_role"] for item in metric_columns_axis if item["mapped_metric"]
        ]
        if not recognized_metrics:
            reasons.append("SEGMENT_ORIENTATION_NOT_RESOLVED")
        recognized_keys = [
            (item["period_year"], item["metric_role"])
            for item in metric_columns_axis
            if item["mapped_metric"]
        ]
        if len(recognized_keys) != len(set(recognized_keys)):
            reasons.append("DUPLICATE_SEGMENT_METRIC_COLUMN")
        transpose_cells: list[dict[str, Any]] = []
        for row_index, row in enumerate(rows, start=1):
            row_label = row.get("label_exact")
            row_years = _years_from_authoritative_surfaces(
                [row_label]
                if type(row_label) is str and row_label.strip()
                else row.get("hierarchy_path_exact")
                if type(row.get("hierarchy_path_exact")) is list
                else []
            )
            if len(row_years) > 1:
                reasons.append("SEGMENT_ROW_PERIOD_AMBIGUOUS")
            elif len(row_years) == 1:
                active_year = next(iter(row_years))
            roles = _axis_roles_for_row(row, axis_aliases)
            if len(roles) > 1:
                reasons.append("SEGMENT_ROW_AXIS_AMBIGUOUS")
                continue
            if len(roles) == 1:
                axis_role = roles[0]
            else:
                label = row.get("label_exact")
                path = (
                    row.get("hierarchy_path_exact")
                    if type(row.get("hierarchy_path_exact")) is list
                    else []
                )
                source_surfaces = (
                    [label]
                    if type(label) is str
                    and label.strip()
                    and _ORDINAL_ONLY.fullmatch(unicodedata.normalize("NFKC", label)) is None
                    else path
                )
                if not source_surfaces:
                    continue
                source_label = _source_axis_label(
                    source_surfaces, fallback=f"r{row_index}", compiled=compiled
                )
                if _role_from_authoritative_surfaces(
                    source_surfaces, opposite_axis_aliases
                ) and not _is_declared_source_only_axis(source_label, compiled):
                    reasons.append("SEGMENT_AXIS_CONTRADICTS_SELECTED_BRANCH")
                axis_role = f"SOURCE_ONLY:r{row_index}:" + source_label
            for item in metric_columns_axis:
                metric_role = item["metric_role"]
                parsed_cell = _cell(
                    row["values_exact"][item["position"]],
                    region=region,
                    row_id=f"r{row_index}",
                    column_id=item["column_id"],
                )
                if (
                    not metric_role.startswith("SOURCE_ONLY_METRIC:")
                    and parsed_cell["state"] == "INVALID_MONEY_SOURCE"
                ):
                    reasons.append("SEGMENT_MONEY_CELL_INVALID")
                column_period = item["period_year"]
                if (
                    len(column_years) > 1
                    and len(row_years) == 1
                    and column_period is not None
                    and active_year != column_period
                ):
                    reasons.append("SEGMENT_CELL_PERIOD_CONFLICT")
                transpose_cells.append(
                    {
                        "axis_role": axis_role,
                        "branch": branch,
                        "metric_role": metric_role,
                        "period_year": column_period
                        if len(column_years) > 1 and column_period is not None
                        else active_year
                        if active_year is not None
                        else column_period,
                        **parsed_cell,
                    }
                )
        cell_keys = [
            (item["period_year"], item["axis_role"], item["metric_role"])
            for item in transpose_cells
        ]
        if len(cell_keys) != len(set(cell_keys)):
            reasons.append("DUPLICATE_SEGMENT_AXIS")
        transpose_groups: dict[tuple[int | None, str], list[dict[str, Any]]] = {}
        for item in transpose_cells:
            transpose_groups.setdefault((item["period_year"], item["metric_role"]), []).append(item)
        for (period, metric_role), group_cells in transpose_groups.items():
            totals = [item for item in group_cells if item["axis_role"] == "TOTAL"]
            if len(totals) != 1:
                reasons.append("EXACTLY_ONE_VISIBLE_SEGMENT_TOTAL_REQUIRED")
                continue
            total_source = totals[0]
            term_sources = [item for item in group_cells if item["axis_role"] != "TOTAL"]
            if not term_sources:
                reasons.append("SEGMENT_TRANSPOSE_TOTAL_FRONTIER_INCOMPLETE")
                continue
            total = {
                key: value
                for key, value in total_source.items()
                if key not in {"axis_role", "branch", "metric_role", "period_year"}
            }
            terms = [
                {
                    key: value
                    for key, value in item.items()
                    if key not in {"axis_role", "branch", "metric_role", "period_year"}
                }
                for item in term_sources
            ]
            mapped_metric = metric_role in compiled["metric_offset_by_role"]
            if mapped_metric and any("coefficient_candidates" in cell for cell in [total, *terms]):
                reasons.append("SEGMENT_MONEY_CELL_AMBIGUOUS")
            status = (
                "NOT_TESTABLE_SOURCE_BLANK"
                if total["coefficient"] is None
                or any(cell["coefficient"] is None for cell in terms)
                else "EXACT"
                if sum(cell["coefficient"] for cell in terms) == total["coefficient"]
                else "EXACT_ROUNDING_RESIDUAL"
                if abs(sum(cell["coefficient"] for cell in terms) - total["coefficient"])
                <= max(1, len(terms) // 2)
                else "MISMATCH"
            )
            equations.append(
                {
                    "branch": branch,
                    "computed_value": None
                    if status == "NOT_TESTABLE_SOURCE_BLANK"
                    else sum(cell["coefficient"] for cell in terms),
                    "metric_role": metric_role,
                    "period_year": period,
                    "result_cell": total,
                    "status": status,
                    "term_cells": terms,
                }
            )
            if mapped_metric and status == "MISMATCH":
                reasons.append("VISIBLE_SEGMENT_TOTAL_MISMATCH")
        cells.extend(transpose_cells)
    cell_years = {cell["period_year"] for cell in cells if cell["period_year"] is not None}
    if len(column_years) > 1 and any(cell["period_year"] is None for cell in cells):
        reasons.append("SEGMENT_COLUMN_PERIOD_AMBIGUOUS")
    if len(title_years) > 1 and any(cell["period_year"] is None for cell in cells):
        reasons.append("SEGMENT_TABLE_TITLE_PERIOD_AMBIGUOUS")
    period_year = next(iter(cell_years)) if len(cell_years) == 1 else None
    local_period_end_evidence: list[dict[str, Any]] = []

    def add_period_end_evidence(
        *, carrier_kind: str, source_exact: Any, column_id: str | None, row_id: str | None
    ) -> None:
        for period_end in _period_ends(source_exact):
            local_period_end_evidence.append(
                {
                    "carrier_kind": carrier_kind,
                    "column_id": column_id,
                    "period_end": period_end,
                    "period_year": date.fromisoformat(period_end).year,
                    "row_id": row_id,
                    "source_exact": source_exact,
                }
            )

    add_period_end_evidence(
        carrier_kind="TABLE_TITLE",
        source_exact=table.get("title_exact"),
        column_id=None,
        row_id=None,
    )
    add_period_end_evidence(
        carrier_kind="SECTION_TITLE",
        source_exact=section.get("title_exact"),
        column_id=None,
        row_id=None,
    )
    for position in money_positions:
        path = columns[position].get("header_path_exact") or []
        members = [member for member in path if type(member) is str]
        for source_exact in [*members, " ".join(members)]:
            add_period_end_evidence(
                carrier_kind="COLUMN_HEADER_PATH",
                source_exact=source_exact,
                column_id=f"c{position + 1}",
                row_id=None,
            )
    for row_ordinal, row in enumerate(rows, start=1):
        path = row.get("hierarchy_path_exact")
        members = [member for member in (path if type(path) is list else []) if type(member) is str]
        for source_exact in [row.get("label_exact"), *members, " ".join(members)]:
            add_period_end_evidence(
                carrier_kind="ROW_HEADER_PATH",
                source_exact=source_exact,
                column_id=None,
                row_id=f"r{row_ordinal}",
            )
    local_period_end_evidence = sorted(
        {canonical_json_sha256_v1(item): item for item in local_period_end_evidence}.values(),
        key=canonical_json_sha256_v1,
    )
    governed_unit_surfaces = [
        ("TABLE_TITLE", table.get("title_exact")),
        ("SECTION_TITLE", section.get("title_exact")),
    ]
    narratives = section.get("narratives_exact")
    if type(narratives) is list:
        governed_unit_surfaces.extend(("NARRATIVE", narrative) for narrative in narratives)
    header_unit_surfaces = [
        member
        for column in (columns[position] for position in money_positions)
        if type(column) is dict
        for member in (column.get("header_path_exact") or [])
    ]
    unit_matches = {
        (item["canonical_unit"], item["magnitude_power10"], item["accepted"])
        for item in [
            *_unit_matches(table.get("unit_exact"), compiled),
            *(
                match
                for surface in header_unit_surfaces
                for match in _unit_matches(surface, compiled)
            ),
            *(
                match
                for carrier_kind, surface in governed_unit_surfaces
                for match in _governed_context_unit_matches(
                    surface, compiled, carrier_kind=carrier_kind
                )
            ),
        ]
    }
    if len(unit_matches) > 1:
        reasons.append("SEGMENT_TABLE_UNIT_CONFLICT")
    unit = (
        next(iter(unit_matches))[0]
        if len(unit_matches) == 1 and next(iter(unit_matches))[2]
        else None
    )
    if len(unit_matches) == 1 and not next(iter(unit_matches))[2]:
        reasons.append("SEGMENT_TABLE_UNIT_NOT_ACCEPTED")
    receipt = {
        "branch": branch,
        "branch_authority": (
            canonical_clone_v1(branch_authority) if branch_authority is not None else None
        ),
        "cell_axis": cells,
        "equations": equations,
        "local_period_end_axis": local_period_end_evidence,
        "orientation": orientation,
        "period_year": period_year,
        "region": canonical_clone_v1(region),
        "unit": unit,
    }
    return {
        "cells": cells,
        "equations": equations,
        "period_year": period_year,
        "reasons": sorted(set(reasons)),
        "receipt": receipt,
    }


def _mapping(
    *,
    branch: str,
    axis_role: str,
    metric_role: str,
    unit: str,
    values: list[dict[str, Any]],
    compiled: Mapping[str, Any],
) -> dict[str, Any]:
    parent = compiled["branch_bindings_by_role"][branch]["axis_parent_report_norm_id_by_role"][
        axis_role
    ]
    role = f"{branch}:{axis_role}:{metric_role}"
    body = {
        "report_norm_id": parent + compiled["metric_offset_by_role"][metric_role],
        "role": role,
        "row_id": values[0]["cell_ref"]["row_id"],
        "unit": unit,
        "values": values,
    }
    return {"item_mapping_id": "gjsrmv1:item:" + canonical_json_sha256_v1(body), **body}


def _is_declared_segment_mapping_cell_v1(
    cell: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> bool:
    """Return whether a nonblank source cell is eligible for a declared mapping."""

    branch = cell.get("branch")
    axis_role = cell.get("axis_role")
    metric_role = cell.get("metric_role")
    return (
        cell.get("coefficient") is not None
        and branch in compiled_specs["branch_bindings_by_role"]
        and metric_role in compiled_specs["metric_offset_by_role"]
        and axis_role
        in compiled_specs["branch_bindings_by_role"][branch]["axis_parent_report_norm_id_by_role"]
    )


def evaluate_gemini_json_segment_report_cluster_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    document_unit_context_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    checked = checked_segment_report_region_axis_v1(regions)
    expected_query = build_segment_report_region_query_receipt_v1(
        checked, owner_receipt=query_receipt.get("owner_receipt", {})
    )
    if not same_typed_json_v1(query_receipt, expected_query):
        raise _error("segment-report query receipt drifted")
    owner_branch_binding_by_region = _checked_owner_branch_binding_axis_v1(
        owner_receipt=query_receipt["owner_receipt"],
        regions=checked,
        compiled=compiled_specs,
    )
    parsed = []
    reasons = []
    for region in checked:
        section, table = _table_from_region(region, page_json_by_version)
        item = _parse_table(
            region,
            section,
            table,
            compiled_specs,
            branch_authority=owner_branch_binding_by_region.get(canonical_json_sha256_v1(region)),
        )
        parsed.append(item)
        reasons.extend(item["reasons"])
    checked_unit_context = _checked_document_unit_context_v1(
        document_unit_context_evidence, compiled=compiled_specs
    )
    unit_resolution = _resolve_segment_table_units_v1(
        [item["receipt"] for item in parsed],
        unit_context=checked_unit_context,
        compiled=compiled_specs,
    )
    reasons.extend(unit_resolution["reasons"])
    unit = unit_resolution["canonical_unit"]
    visible_years = {
        cell["period_year"]
        for item in parsed
        for cell in item["cells"]
        if cell["period_year"] is not None
    }
    owner_years = query_receipt["owner_receipt"].get("reporting_year_axis", [])
    if type(owner_years) is not list or any(type(year) is not int for year in owner_years):
        raise _error("segment-report reporting year receipt is invalid")
    owner_current_year = owner_years[0] if owner_years else None
    if owner_current_year is not None:
        unexpected_years = visible_years - {owner_current_year, owner_current_year - 1}
        if unexpected_years:
            reasons.append("SEGMENT_PERIOD_OUTSIDE_AUTHENTICATED_REPORTING_WINDOW")
        explicit_years = [
            year
            for year in (owner_current_year, owner_current_year - 1)
            if year == owner_current_year or year in visible_years
        ]
    else:
        explicit_years = sorted(visible_years, reverse=True)
        if len(explicit_years) == 1:
            reasons.append("SEGMENT_CURRENT_PERIOD_CONTEXT_NOT_AUTHENTICATED")
            explicit_years = []
        elif len(explicit_years) == 2 and explicit_years[0] - explicit_years[1] != 1:
            reasons.append("SEGMENT_PERIOD_AXIS_IS_NOT_A_CONSECUTIVE_PAIR")
    if len(explicit_years) > 2:
        reasons.append("SEGMENT_PERIOD_AXIS_EXCEEDS_TWO_PERIODS")
    current_year = owner_current_year or (explicit_years[0] if explicit_years else None)
    comparative_year = explicit_years[1] if len(explicit_years) > 1 else None
    period_role = {current_year: "CURRENT_PERIOD"} if current_year is not None else {}
    if comparative_year is not None:
        period_role[comparative_year] = "COMPARATIVE_PERIOD"
    assigned_table_role: dict[int, str] = {}
    assigned_metric_role: dict[tuple[int, str], str] = {}
    grouped_tables: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = {}
    for item in parsed:
        branch = item["receipt"].get("branch")
        signature = _segment_declared_metric_signature_v1(item["receipt"], compiled_specs)
        if branch and signature:
            grouped_tables.setdefault((branch, signature), []).append(item)

    def item_years(item: Mapping[str, Any], metric: str | None = None) -> set[int]:
        return {
            cell["period_year"]
            for cell in item["cells"]
            if cell["period_year"] and (metric is None or cell["metric_role"] == metric)
        }

    def visible_role(years: set[int]) -> str | None:
        return period_role.get(next(iter(years))) if len(years) == 1 else None

    grouped_metrics: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in parsed:
        branch = item["receipt"].get("branch")
        for metric in _segment_declared_metric_signature_v1(item["receipt"], compiled_specs):
            if branch:
                grouped_metrics.setdefault((branch, metric), []).append(item)

    table_order_carriers: list[dict[str, Any]] = []
    for (branch, signature), items in grouped_tables.items():
        if len(items) != 2:
            continue
        roles = [visible_role(item_years(item)) for item in items]
        if roles == ["CURRENT_PERIOD", "COMPARATIVE_PERIOD"]:
            order = "CURRENT_FIRST"
        elif roles == ["COMPARATIVE_PERIOD", "CURRENT_PERIOD"]:
            order = "COMPARATIVE_FIRST"
        else:
            continue
        table_order_carriers.append(
            {
                "branch": branch,
                "carrier_regions": [
                    canonical_clone_v1(item["receipt"]["region"]) for item in items
                ],
                "metric_signature": list(signature),
                "order": order,
                "shape_axis": [_segment_table_period_shape_v1(item["receipt"]) for item in items],
            }
        )

    def paired_roles(
        *, first_years: set[int], second_years: set[int], structural_order: str | None
    ) -> tuple[str | None, str | None]:
        roles = [visible_role(first_years), visible_role(second_years)]
        if roles[0] is not None and roles[1] is not None:
            return None, None
        # A single dated fragment plus an undated sibling does not authenticate
        # the sibling's role.  Structural order is usable only for a completely
        # undated pair bound to one exact, independently dated carrier pair.
        if not first_years and not second_years:
            if structural_order == "CURRENT_FIRST":
                return "CURRENT_PERIOD", "COMPARATIVE_PERIOD"
            if structural_order == "COMPARATIVE_FIRST":
                return "COMPARATIVE_PERIOD", "CURRENT_PERIOD"
        return None, None

    unit_by_region = {
        canonical_json_sha256_v1(item["region"]): item["canonical_unit"]
        for item in unit_resolution["table_unit_assignment_axis"]
    }

    def direct_declared_role(item: Mapping[str, Any]) -> str | None:
        roles = {
            period_role[cell.get("period_year")]
            for cell in item["cells"]
            if cell.get("metric_role") in compiled_specs["metric_offset_by_role"]
            and cell.get("period_year") in period_role
        }
        return next(iter(roles)) if len(roles) == 1 else None

    def resolved_declared_role(item: Mapping[str, Any]) -> str | None:
        roles = {
            role
            for role in (
                direct_declared_role(item),
                assigned_table_role.get(id(item)),
            )
            if role is not None
        }
        return next(iter(roles)) if len(roles) == 1 else None

    for item in parsed:
        receipt = item["receipt"]
        mapped_metrics = sorted(
            {
                cell.get("metric_role")
                for cell in item["cells"]
                if cell.get("metric_role") in compiled_specs["metric_offset_by_role"]
            }
        )
        roles_by_metric = {
            metric: {
                period_role[cell.get("period_year")]
                for cell in item["cells"]
                if cell.get("metric_role") == metric and cell.get("period_year") in period_role
            }
            for metric in mapped_metrics
        }
        visible_roles = set().union(*roles_by_metric.values()) if roles_by_metric else set()
        if len(visible_roles) != 1:
            continue
        unique_visible_role = next(iter(visible_roles))
        equation_metrics = {equation.get("metric_role") for equation in item.get("equations", [])}
        target_metrics = [
            metric
            for metric in mapped_metrics
            if metric in equation_metrics
            and not roles_by_metric[metric]
            and all(
                cell.get("period_year") is None
                for cell in item["cells"]
                if cell.get("metric_role") == metric
            )
        ]
        carrier_metrics = [
            metric for metric in mapped_metrics if roles_by_metric[metric] == {unique_visible_role}
        ]
        if not target_metrics or not carrier_metrics:
            continue
        for metric in target_metrics:
            assigned_metric_role[(id(item), metric)] = unique_visible_role
        receipt["period_assignment_rule"] = (
            "MISSING_METRIC_PERIOD_FROM_UNIQUE_VISIBLE_ROLE_IN_SAME_TABLE"
        )
        receipt["period_role_by_metric"] = {
            metric: unique_visible_role for metric in target_metrics
        }
        receipt["period_assignment_evidence"] = {
            "carrier_metric_roles": carrier_metrics,
            "period_role": unique_visible_role,
            "rule": "UNIQUE_VISIBLE_PERIOD_ROLE_WITHIN_SAME_TABLE",
            "target_metric_roles": target_metrics,
            "target_regions": [canonical_clone_v1(receipt["region"])],
        }

    same_section_blocks: dict[tuple[int, int, str, str], list[dict[str, Any]]] = {}
    for item in parsed:
        region = item["receipt"]["region"]
        same_section_blocks.setdefault(
            (
                region["selected_page_ordinal"],
                region["physical_page"],
                region["section_id"],
                item["receipt"]["branch"],
            ),
            [],
        ).append(item)
    for block_items in same_section_blocks.values():
        block_roles = {
            role for item in block_items if (role := direct_declared_role(item)) is not None
        }
        if len(block_roles) != 1:
            continue
        block_role = next(iter(block_roles))
        for target in block_items:
            target_signature = _segment_declared_metric_signature_v1(
                target["receipt"], compiled_specs
            )
            if not target_signature or direct_declared_role(target) is not None:
                continue
            if (
                sum(
                    _segment_declared_metric_signature_v1(item["receipt"], compiled_specs)
                    == target_signature
                    for item in block_items
                )
                != 1
            ):
                continue
            carriers = [
                item
                for item in block_items
                if item is not target
                and direct_declared_role(item) == block_role
                and set(
                    _segment_declared_metric_signature_v1(item["receipt"], compiled_specs)
                ).isdisjoint(target_signature)
            ]
            if not carriers:
                continue
            assigned_table_role[id(target)] = block_role
            target["receipt"]["period_assignment_rule"] = (
                "MISSING_PERIOD_FROM_UNIQUE_EXPLICIT_SAME_SECTION_METRIC_SIBLING"
            )
            target["receipt"]["period_role"] = block_role
            target["receipt"]["period_assignment_evidence"] = {
                "carrier_metric_signatures": [
                    list(_segment_declared_metric_signature_v1(item["receipt"], compiled_specs))
                    for item in carriers
                ],
                "carrier_regions": [
                    canonical_clone_v1(item["receipt"]["region"]) for item in carriers
                ],
                "period_role": block_role,
                "rule": "UNIQUE_EXPLICIT_PERIOD_ROLE_WITHIN_SAME_PAGE_SECTION",
                "target_metric_signature": list(target_signature),
                "target_regions": [canonical_clone_v1(target["receipt"]["region"])],
            }

    for block_items in same_section_blocks.values():
        for target in block_items:
            receipt = target["receipt"]
            if id(target) in assigned_table_role or receipt.get("period_assignment_evidence"):
                continue
            target_signature = _segment_declared_metric_signature_v1(receipt, compiled_specs)
            if (
                not target_signature
                or any(
                    cell.get("metric_role") in compiled_specs["metric_offset_by_role"]
                    and cell.get("period_year") is not None
                    for cell in target["cells"]
                )
                or sum(
                    _segment_declared_metric_signature_v1(item["receipt"], compiled_specs)
                    == target_signature
                    and item["receipt"].get("branch") == receipt.get("branch")
                    for item in parsed
                )
                != 1
            ):
                continue
            section_period_axis = [
                evidence
                for evidence in receipt["local_period_end_axis"]
                if evidence["carrier_kind"] == "SECTION_TITLE"
                and evidence["period_year"] in period_role
            ]
            section_roles = {
                period_role[evidence["period_year"]] for evidence in section_period_axis
            }
            if len(section_roles) != 1 or not section_period_axis:
                continue
            section_role = next(iter(section_roles))
            assigned_table_role[id(target)] = section_role
            receipt["period_assignment_rule"] = (
                "MISSING_PERIOD_FROM_UNIQUE_EXPLICIT_SECTION_PERIOD_END"
            )
            receipt["period_role"] = section_role
            receipt["period_assignment_evidence"] = {
                "period_role": section_role,
                "rule": "UNIQUE_SECTION_PERIOD_ROLE_FOR_UNDATED_TABLE",
                "section_period_end_axis": canonical_clone_v1(section_period_axis),
                "target_metric_signature": list(target_signature),
                "target_regions": [canonical_clone_v1(receipt["region"])],
            }

    for candidate in _segment_cross_branch_total_period_candidates_v1(
        [item["receipt"] for item in parsed],
        compiled_specs=compiled_specs,
        owner_receipt=query_receipt["owner_receipt"],
        period_role_by_year=period_role,
        unit_by_region=unit_by_region,
    ):
        target_receipt = candidate["target_receipt"]
        target = next(item for item in parsed if item["receipt"] is target_receipt)
        if id(target) in assigned_table_role or target_receipt.get("period_assignment_evidence"):
            continue
        evidence = candidate["evidence"]
        assigned_table_role[id(target)] = evidence["target_role"]
        target_receipt["period_assignment_rule"] = (
            "MISSING_PERIOD_FROM_CROSS_BRANCH_DECLARED_TOTAL_CORRESPONDENCE"
        )
        target_receipt["period_role"] = evidence["target_role"]
        target_receipt["period_assignment_evidence"] = canonical_clone_v1(evidence)

    repeated_block_candidates: list[dict[str, Any]] = []
    items_by_branch: dict[str, list[dict[str, Any]]] = {}
    for item in parsed:
        branch = item["receipt"].get("branch")
        if branch is not None:
            items_by_branch.setdefault(branch, []).append(item)
    for branch, branch_items in items_by_branch.items():
        branch_items.sort(
            key=lambda item: (
                item["receipt"]["region"]["selected_page_ordinal"],
                int(item["receipt"]["region"]["section_id"][1:]),
                int(item["receipt"]["region"]["table_id"][1:]),
            )
        )
        signatures = sorted(
            {
                _segment_declared_metric_signature_v1(item["receipt"], compiled_specs)
                for item in branch_items
                if _segment_declared_metric_signature_v1(item["receipt"], compiled_specs)
            }
        )
        for left_index, left_signature in enumerate(signatures):
            for right_signature in signatures[left_index + 1 :]:
                if not set(left_signature).isdisjoint(right_signature):
                    continue
                block_items = [
                    item
                    for item in branch_items
                    if _segment_declared_metric_signature_v1(item["receipt"], compiled_specs)
                    in {left_signature, right_signature}
                ]
                if len(block_items) != 4:
                    continue
                block_signatures = [
                    _segment_declared_metric_signature_v1(item["receipt"], compiled_specs)
                    for item in block_items
                ]
                if block_signatures != [
                    left_signature,
                    right_signature,
                    left_signature,
                    right_signature,
                ] and block_signatures != [
                    right_signature,
                    left_signature,
                    right_signature,
                    left_signature,
                ]:
                    continue
                regions = [item["receipt"]["region"] for item in block_items]
                binding_mode = _segment_repeated_block_geometry_v1(regions)
                if binding_mode is None:
                    continue
                units = {
                    unit_by_region.get(canonical_json_sha256_v1(item["receipt"]["region"]))
                    for item in block_items
                }
                orientations = {item["receipt"].get("orientation") for item in block_items}
                shapes = [
                    _segment_declared_table_shape_v1(item["receipt"], compiled_specs)
                    for item in block_items
                ]
                if (
                    len(units) != 1
                    or None in units
                    or len(orientations) != 1
                    or shapes[0] != shapes[2]
                    or shapes[1] != shapes[3]
                ):
                    continue
                blocks = (block_items[:2], block_items[2:])
                block_roles = []
                carrier_items: list[dict[str, Any]] = []
                target_items: list[dict[str, Any]] = []
                valid = True
                for block in blocks:
                    resolved = [item for item in block if resolved_declared_role(item) is not None]
                    roles = {resolved_declared_role(item) for item in resolved}
                    if len(roles) > 1:
                        valid = False
                        break
                    role = next(iter(roles)) if roles else None
                    block_roles.append(role)
                    carrier_items.extend(resolved)
                    target_items.extend(
                        item for item in block if resolved_declared_role(item) is None
                    )
                if not valid or block_roles == [None, None]:
                    continue
                if block_roles[0] is None:
                    block_roles[0] = (
                        "COMPARATIVE_PERIOD"
                        if block_roles[1] == "CURRENT_PERIOD"
                        else "CURRENT_PERIOD"
                    )
                if block_roles[1] is None:
                    block_roles[1] = (
                        "COMPARATIVE_PERIOD"
                        if block_roles[0] == "CURRENT_PERIOD"
                        else "CURRENT_PERIOD"
                    )
                if set(block_roles) != {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}:
                    continue
                if not target_items:
                    continue
                owner_authority: list[dict[str, Any]] = []
                for block, role in zip(blocks, block_roles, strict=True):
                    for target in block:
                        if target not in target_items:
                            continue
                        authority = _segment_owner_period_authority_for_signature_v1(
                            owner_receipt=query_receipt["owner_receipt"],
                            role=role,
                            signature=_segment_declared_metric_signature_v1(
                                target["receipt"], compiled_specs
                            ),
                        )
                        if not authority:
                            valid = False
                            break
                        owner_authority.extend(authority)
                    if not valid:
                        break
                if not valid:
                    continue
                owner_authority = sorted(
                    {
                        canonical_json_sha256_v1(item): canonical_clone_v1(item)
                        for item in owner_authority
                    }.values(),
                    key=canonical_json_sha256_v1,
                )
                evidence = {
                    "binding_mode": binding_mode,
                    "block_axis": [
                        {
                            "period_role": role,
                            "regions": [
                                canonical_clone_v1(item["receipt"]["region"]) for item in block
                            ],
                            "slot_metric_signatures": [
                                list(
                                    _segment_declared_metric_signature_v1(
                                        item["receipt"], compiled_specs
                                    )
                                )
                                for item in block
                            ],
                        }
                        for block, role in zip(blocks, block_roles, strict=True)
                    ],
                    "branch": branch,
                    "carrier_regions": [
                        canonical_clone_v1(item["receipt"]["region"]) for item in carrier_items
                    ],
                    "orientation": next(iter(orientations)),
                    "owner_period_authority_axis": owner_authority,
                    "rule": "UNIQUE_ROLE_WITHIN_REPEATED_ADJACENT_METRIC_BLOCK",
                    "shape_axis": shapes,
                    "target_regions": [
                        canonical_clone_v1(item["receipt"]["region"]) for item in target_items
                    ],
                    "unit": next(iter(units)),
                }
                repeated_block_candidates.append(
                    {
                        "block_roles": block_roles,
                        "evidence": evidence,
                        "items": block_items,
                        "targets": target_items,
                    }
                )
    target_candidate_counts: dict[int, int] = {}
    for candidate in repeated_block_candidates:
        for target in candidate["targets"]:
            target_candidate_counts[id(target)] = target_candidate_counts.get(id(target), 0) + 1
    for candidate in repeated_block_candidates:
        if any(target_candidate_counts[id(target)] != 1 for target in candidate["targets"]):
            continue
        for block, role in zip(
            (candidate["items"][:2], candidate["items"][2:]),
            candidate["block_roles"],
            strict=True,
        ):
            for target in block:
                if target not in candidate["targets"]:
                    continue
                assigned_table_role[id(target)] = role
                target["receipt"]["period_assignment_rule"] = (
                    "MISSING_PERIOD_FROM_REPEATED_ADJACENT_METRIC_BLOCK_ROLE"
                )
                target["receipt"]["period_role"] = role
                target["receipt"]["period_assignment_evidence"] = canonical_clone_v1(
                    candidate["evidence"]
                )

    def owner_period_authority_for_signature(
        *, role: str, signature: tuple[str, ...]
    ) -> list[dict[str, Any]] | None:
        owner_axis = query_receipt["owner_receipt"].get("reporting_period_axis", [])
        if type(owner_axis) is not list:
            return None
        needed_classes = {
            temporal_class
            for metric in signature
            if (temporal_class := _metric_temporal_class_v1(metric)) is not None
        }
        authority: list[dict[str, Any]] = []
        for temporal_class in sorted(needed_classes):
            matches = [
                item
                for item in owner_axis
                if item.get("period_role") == role and item.get("temporal_class") == temporal_class
            ]
            if not matches:
                matches = [
                    item
                    for item in owner_axis
                    if item.get("period_role") == role and item.get("temporal_class") == "GENERAL"
                ]
            if len({item.get("period_end") for item in matches}) != 1:
                return None
            authority.extend(matches)
        return sorted(
            {
                canonical_json_sha256_v1(item): canonical_clone_v1(item) for item in authority
            }.values(),
            key=canonical_json_sha256_v1,
        )

    split_combined_candidates: list[dict[str, Any]] = []
    for target in parsed:
        target_receipt = target["receipt"]
        target_signature = _segment_declared_metric_signature_v1(target_receipt, compiled_specs)
        if (
            len(target_signature) < 2
            or resolved_declared_role(target) is not None
            or target_receipt.get("period_assignment_evidence")
            or any(
                cell.get("metric_role") in compiled_specs["metric_offset_by_role"]
                and cell.get("period_year") is not None
                for cell in target["cells"]
            )
        ):
            continue
        target_region = target_receipt["region"]
        candidates = []
        for first_index, first in enumerate(parsed):
            for second in parsed[first_index + 1 :]:
                first_receipt = first["receipt"]
                second_receipt = second["receipt"]
                first_signature = _segment_declared_metric_signature_v1(
                    first_receipt, compiled_specs
                )
                second_signature = _segment_declared_metric_signature_v1(
                    second_receipt, compiled_specs
                )
                if (
                    first_receipt.get("branch") != target_receipt.get("branch")
                    or second_receipt.get("branch") != target_receipt.get("branch")
                    or not first_signature
                    or not second_signature
                    or not set(first_signature).isdisjoint(second_signature)
                    or tuple(sorted((*first_signature, *second_signature))) != target_signature
                ):
                    continue
                carrier_geometry = _segment_period_pair_geometry_v1([first_receipt, second_receipt])
                if carrier_geometry is None:
                    continue
                carrier_region = first_receipt["region"]
                binding_mode = (
                    "SPLIT_THEN_COMBINED"
                    if carrier_region["selected_page_ordinal"] + 1
                    == target_region["selected_page_ordinal"]
                    and carrier_region["physical_page"] + 1 == target_region["physical_page"]
                    else "COMBINED_THEN_SPLIT"
                    if target_region["selected_page_ordinal"] + 1
                    == carrier_region["selected_page_ordinal"]
                    and target_region["physical_page"] + 1 == carrier_region["physical_page"]
                    else None
                )
                carrier_roles = {resolved_declared_role(first), resolved_declared_role(second)}
                if (
                    binding_mode is None
                    or target_region["section_id"] != carrier_region["section_id"]
                    or int(target_region["table_id"][1:]) != carrier_geometry[3][0]
                    or None in carrier_roles
                    or len(carrier_roles) != 1
                    or {first_receipt.get("unit"), second_receipt.get("unit")}
                    != {target_receipt.get("unit")}
                    or target_receipt.get("unit") is None
                    or {first_receipt.get("orientation"), second_receipt.get("orientation")}
                    != {target_receipt.get("orientation")}
                ):
                    continue
                target_layout = _segment_declared_metric_layout_v1(target_receipt, compiled_specs)
                carrier_layout = {
                    **_segment_declared_metric_layout_v1(first_receipt, compiled_specs),
                    **_segment_declared_metric_layout_v1(second_receipt, compiled_specs),
                }
                if target_layout != carrier_layout:
                    continue
                carrier_role = next(iter(carrier_roles))
                target_role = (
                    "COMPARATIVE_PERIOD" if carrier_role == "CURRENT_PERIOD" else "CURRENT_PERIOD"
                )
                owner_authority = owner_period_authority_for_signature(
                    role=target_role, signature=target_signature
                )
                local_section_roles = {
                    period_role[evidence["period_year"]]
                    for evidence in target_receipt["local_period_end_axis"]
                    if evidence.get("carrier_kind") == "SECTION_TITLE"
                    and evidence.get("period_year") in period_role
                }
                if (
                    not owner_authority
                    or local_section_roles
                    and local_section_roles != {target_role}
                ):
                    continue
                candidates.append(
                    {
                        "binding_mode": binding_mode,
                        "carrier_regions": [
                            canonical_clone_v1(first_receipt["region"]),
                            canonical_clone_v1(second_receipt["region"]),
                        ],
                        "carrier_role": carrier_role,
                        "metric_layout_by_role": target_layout,
                        "owner_period_authority_axis": owner_authority,
                        "target_role": target_role,
                    }
                )
        if len(candidates) == 1:
            split_combined_candidates.append({"candidate": candidates[0], "target": target})
    for item in split_combined_candidates:
        target = item["target"]
        carrier = item["candidate"]
        target_receipt = target["receipt"]
        evidence = {
            **carrier,
            "branch": target_receipt["branch"],
            "orientation": target_receipt["orientation"],
            "rule": "UNIQUE_COMPLEMENT_ROLE_FROM_ADJACENT_SPLIT_COMBINED_METRIC_BLOCK",
            "target_metric_signature": list(
                _segment_declared_metric_signature_v1(target_receipt, compiled_specs)
            ),
            "target_regions": [canonical_clone_v1(target_receipt["region"])],
            "unit": target_receipt["unit"],
        }
        assigned_table_role[id(target)] = carrier["target_role"]
        target_receipt["period_assignment_rule"] = (
            "MISSING_PERIOD_FROM_ADJACENT_SPLIT_COMBINED_METRIC_BLOCK_COMPLEMENT"
        )
        target_receipt["period_role"] = carrier["target_role"]
        target_receipt["period_assignment_evidence"] = evidence

    def exact_structural_carrier(
        *, branch: str, signature: tuple[str, ...], items: Sequence[Mapping[str, Any]]
    ) -> dict[str, Any] | None:
        target_geometry = _segment_period_pair_geometry_v1([item["receipt"] for item in items])
        if target_geometry is None:
            return None
        target_units = {
            unit_by_region.get(canonical_json_sha256_v1(item["receipt"]["region"]))
            for item in items
        }
        target_shape_axis = [_segment_table_period_shape_v1(item["receipt"]) for item in items]
        compatible = []
        for carrier in table_order_carriers:
            if (
                carrier["branch"] == branch
                or carrier["metric_signature"] != list(signature)
                or carrier["shape_axis"] != target_shape_axis
            ):
                continue
            carrier_items = [
                candidate
                for candidate in parsed
                if candidate["receipt"]["region"] in carrier["carrier_regions"]
            ]
            carrier_geometry = _segment_period_pair_geometry_v1(
                [item["receipt"] for item in carrier_items]
            )
            if carrier_geometry is None:
                continue
            pair_binding_mode = _segment_period_pair_binding_mode_v1(
                target_geometry, carrier_geometry
            )
            carrier_units = {
                unit_by_region.get(canonical_json_sha256_v1(item["receipt"]["region"]))
                for item in carrier_items
            }
            if (
                target_units != carrier_units
                or len(target_units) != 1
                or None in target_units
                or pair_binding_mode is None
            ):
                continue
            compatible.append({**carrier, "pair_binding_mode": pair_binding_mode})
        return compatible[0] if len(compatible) == 1 else None

    for (branch, signature), items in grouped_tables.items():
        if len(items) == 1 and current_year is not None:
            if id(items[0]) in assigned_table_role:
                continue
            visible = item_years(items[0])
            # An explicit source year always outranks document-level
            # inheritance.  Only a truly undated singleton inherits CURRENT.
            if not visible and all(
                len(grouped_metrics.get((branch, metric), [])) == 1 for metric in signature
            ):
                assigned_table_role[id(items[0])] = "CURRENT_PERIOD"
                items[0]["receipt"]["period_assignment_rule"] = (
                    "SINGLE_UNDATED_SEGMENT_FRAGMENT_UNDER_AUTHENTICATED_REPORTING_YEAR"
                )
                items[0]["receipt"]["period_role"] = "CURRENT_PERIOD"
            continue
        if len(items) != 2:
            continue
        if any(id(item) in assigned_table_role for item in items):
            continue
        structural_carrier = exact_structural_carrier(
            branch=branch, signature=signature, items=items
        )
        roles = paired_roles(
            first_years=item_years(items[0]),
            second_years=item_years(items[1]),
            structural_order=(structural_carrier["order"] if structural_carrier else None),
        )
        for item, role in zip(items, roles, strict=True):
            if role is not None:
                assigned_table_role[id(item)] = role
                item["receipt"]["period_assignment_rule"] = (
                    "MISSING_PERIOD_FROM_MATCHED_SEGMENT_FRAGMENT_PAIR_AND_AUTHENTICATED_ORDER"
                )
                item["receipt"]["period_role"] = role
                if structural_carrier is not None:
                    item["receipt"]["period_assignment_evidence"] = {
                        "carrier": canonical_clone_v1(structural_carrier),
                        "rule": (
                            "UNIQUE_EXPLICIT_TWO_PERIOD_CROSS_BRANCH_PAIR_WITH_EXACT_"
                            "METRIC_ORIENTATION_AND_CELL_COUNT_SIGNATURE"
                        ),
                        "target_regions": [
                            canonical_clone_v1(target["receipt"]["region"]) for target in items
                        ],
                    }
    period_end_resolution = _resolve_segment_period_end_assignments_v1(
        [item["receipt"] for item in parsed],
        owner_receipt=query_receipt["owner_receipt"],
        period_role_by_year=period_role,
    )
    reasons.extend(period_end_resolution["reasons"])
    period_assignment_by_cell_ref = {
        canonical_json_sha256_v1(item["cell_ref"]): item
        for item in period_end_resolution["period_assignment_axis"]
    }
    for branch in sorted(
        {
            cell["branch"]
            for item in parsed
            for cell in item["cells"]
            if cell.get("branch") is not None
        }
    ):
        mapped_axis_roles = {
            cell["axis_role"]
            for item in parsed
            for cell in item["cells"]
            if cell.get("branch") == branch
            and cell.get("coefficient") is not None
            and cell.get("metric_role") in compiled_specs["metric_offset_by_role"]
            and cell["axis_role"] != "TOTAL"
            and not cell["axis_role"].startswith("SOURCE_ONLY:")
            and cell["axis_role"]
            in compiled_specs["branch_bindings_by_role"][branch][
                "axis_parent_report_norm_id_by_role"
            ]
        }
        if len(mapped_axis_roles) < compiled_specs["minimum_mapped_axis_roles"]:
            reasons.append("INSUFFICIENT_DECLARED_SEGMENT_AXIS_COVERAGE")
        visible_metric_roles = {
            cell["metric_role"]
            for item in parsed
            for cell in item["cells"]
            if cell.get("branch") == branch
            and cell.get("metric_role") in compiled_specs["metric_offset_by_role"]
        }
        if not any(
            set(combination) <= visible_metric_roles
            for combination in compiled_specs["required_role_combinations"]
        ):
            reasons.append("REQUIRED_SEGMENT_METRIC_COMBINATION_NOT_VISIBLE")
    keyed: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    semantic_cells: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    duplicate_equivalent_cells: list[dict[str, Any]] = []
    blanks = []
    all_equations = []
    equation_signatures: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in parsed:
        cell_by_ref = {canonical_json_sha256_v1(cell["cell_ref"]): cell for cell in item["cells"]}
        for equation in item["equations"]:
            mapped_metric = equation["metric_role"] in compiled_specs["metric_offset_by_role"]
            axis_period = (
                period_role.get(equation.get("period_year"))
                or assigned_metric_role.get((id(item), equation["metric_role"]))
                or assigned_table_role.get(id(item))
            )
            if axis_period is None:
                if mapped_metric:
                    reasons.append("SEGMENT_PERIOD_NOT_RESOLVED")
                continue
            equation_period_assignments = [
                period_assignment_by_cell_ref.get(canonical_json_sha256_v1(cell["cell_ref"]))
                for cell in [equation["result_cell"], *equation["term_cells"]]
            ]
            equation_period_ends = {
                assignment.get("period_end") if assignment is not None else None
                for assignment in equation_period_assignments
            }
            if mapped_metric and len(equation_period_ends) > 1:
                reasons.append("SEGMENT_EQUATION_PERIOD_END_CONFLICT")
            equation_key = (equation["branch"], equation["metric_role"], axis_period)
            result_period_assignment = equation_period_assignments[0]
            semantic_signature = {
                "computed_value": equation["computed_value"],
                "period_end": (
                    result_period_assignment.get("period_end")
                    if result_period_assignment is not None
                    else None
                ),
                "result_coefficient": equation["result_cell"]["coefficient"],
                "status": equation["status"],
                "term_axis": sorted(
                    [
                        {
                            "axis_role": cell_by_ref[canonical_json_sha256_v1(cell["cell_ref"])][
                                "axis_role"
                            ],
                            "coefficient": cell["coefficient"],
                        }
                        for cell in equation["term_cells"]
                    ],
                    key=canonical_json_sha256_v1,
                ),
            }
            prior_signature = equation_signatures.get(equation_key)
            if prior_signature is not None:
                if mapped_metric and prior_signature != semantic_signature:
                    reasons.append("CONFLICTING_DUPLICATE_SEGMENT_EQUATION")
                continue
            equation_signatures[equation_key] = semantic_signature
            equation_period_assignment = period_assignment_by_cell_ref.get(
                canonical_json_sha256_v1(equation["result_cell"]["cell_ref"])
            )
            all_equations.append(
                {
                    "axis_role": axis_period,
                    "period_assignment_id": (
                        equation_period_assignment["period_assignment_id"]
                        if equation_period_assignment is not None
                        else None
                    ),
                    "period_end": (
                        equation_period_assignment["period_end"]
                        if equation_period_assignment is not None
                        else None
                    ),
                    **canonical_clone_v1(equation),
                }
            )
        for cell in item["cells"]:
            mapped_metric = cell["metric_role"] in compiled_specs["metric_offset_by_role"]
            axis_period = (
                period_role.get(cell.get("period_year"))
                or assigned_metric_role.get((id(item), cell["metric_role"]))
                or assigned_table_role.get(id(item))
            )
            if axis_period is None:
                if mapped_metric:
                    reasons.append("SEGMENT_PERIOD_NOT_RESOLVED")
                continue
            semantic_key = (
                cell["branch"],
                cell["axis_role"],
                cell["metric_role"],
                axis_period,
            )
            prior_cell = semantic_cells.get(semantic_key)
            if prior_cell is not None:
                prior_period_assignment = period_assignment_by_cell_ref.get(
                    canonical_json_sha256_v1(prior_cell["cell_ref"])
                )
                current_period_assignment = period_assignment_by_cell_ref.get(
                    canonical_json_sha256_v1(cell["cell_ref"])
                )
                same_value_and_endpoint = prior_cell.get("coefficient") == cell.get(
                    "coefficient"
                ) and (
                    prior_period_assignment.get("period_end")
                    if prior_period_assignment is not None
                    else None
                ) == (
                    current_period_assignment.get("period_end")
                    if current_period_assignment is not None
                    else None
                )
                if not same_value_and_endpoint and mapped_metric:
                    reasons.append("CONFLICTING_DUPLICATE_SEGMENT_AXIS_METRIC_PERIOD_CELL")
                elif same_value_and_endpoint:
                    duplicate_equivalent_cells.append(
                        {
                            "axis_key": {
                                "axis_role": cell["axis_role"],
                                "branch": cell["branch"],
                                "metric_role": cell["metric_role"],
                                "period_role": axis_period,
                            },
                            "canonical_cell_ref": canonical_clone_v1(prior_cell["cell_ref"]),
                            "coefficient": cell.get("coefficient"),
                            "duplicate_cell_ref": canonical_clone_v1(cell["cell_ref"]),
                            "period_end": (
                                current_period_assignment.get("period_end")
                                if current_period_assignment is not None
                                else None
                            ),
                            "rule": "SEMANTICALLY_EQUIVALENT_DUPLICATE_SOURCE_CELL_COLLAPSED",
                        }
                    )
                continue
            semantic_cells[semantic_key] = cell
            cell_period_assignment = period_assignment_by_cell_ref.get(
                canonical_json_sha256_v1(cell["cell_ref"])
            )
            if _is_declared_segment_mapping_cell_v1(cell, compiled_specs=compiled_specs) and (
                cell_period_assignment is None or cell_period_assignment.get("period_end") is None
            ):
                reasons.append("SEGMENT_PERIOD_END_NOT_RESOLVED")
            if cell["coefficient"] is None:
                if cell.get("state") == "SOURCE_BLANK":
                    blanks.append(
                        {
                            "axis_role": axis_period,
                            "period_assignment_id": (
                                cell_period_assignment["period_assignment_id"]
                                if cell_period_assignment is not None
                                else None
                            ),
                            "period_end": (
                                cell_period_assignment["period_end"]
                                if cell_period_assignment is not None
                                else None
                            ),
                            **canonical_clone_v1(cell),
                        }
                    )
                continue
            if cell["axis_role"].startswith("SOURCE_ONLY:"):
                continue
            branch = cell["branch"]
            if (
                branch is None
                or cell["metric_role"] not in compiled_specs["metric_offset_by_role"]
                or cell["axis_role"]
                not in compiled_specs["branch_bindings_by_role"][branch][
                    "axis_parent_report_norm_id_by_role"
                ]
            ):
                continue
            keyed[semantic_key] = cell
    mappings = []
    if not reasons and unit is not None:
        grouping: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for (branch, axis, metric, axis_period), cell in keyed.items():
            cell_period_assignment = period_assignment_by_cell_ref[
                canonical_json_sha256_v1(cell["cell_ref"])
            ]
            grouping.setdefault((branch, axis, metric), []).append(
                {
                    "axis_role": axis_period,
                    "cell_ref": canonical_clone_v1(cell["cell_ref"]),
                    "coefficient": cell["coefficient"],
                    "equation_multiplier": 1,
                    "period_assignment_id": cell_period_assignment["period_assignment_id"],
                    "period_end": cell_period_assignment["period_end"],
                    "source_text": cell["source_text"],
                    "state": cell["state"],
                }
            )
        for (branch, axis, metric), values in sorted(grouping.items()):
            values.sort(
                key=lambda x: (
                    x["axis_role"] != "CURRENT_PERIOD",
                    canonical_json_sha256_v1(x["cell_ref"]),
                )
            )
            mappings.append(
                _mapping(
                    branch=branch,
                    axis_role=axis,
                    metric_role=metric,
                    unit=unit,
                    values=values,
                    compiled=compiled_specs,
                )
            )
    if not mappings and not reasons:
        reasons.append("NO_EXACT_VISIBLE_SEGMENT_MAPPING")
    reasons = sorted(set(reasons))
    status = READY if not reasons else UNRESOLVED
    if status != READY:
        mappings = []
    closure = {
        "blank_cell_axis": blanks,
        "duplicate_equivalent_cell_axis": duplicate_equivalent_cells,
        "equations": all_equations,
        "mapping_axis": canonical_clone_v1(mappings),
        "period_receipt": {
            "period_assignment_axis": period_end_resolution["period_assignment_axis"],
            "rule": period_end_resolution["rule"],
        },
        "query_receipt": canonical_clone_v1(query_receipt),
        "rule": "MAP_VISIBLE_SEGMENT_INTERSECTIONS_AFTER_PERIOD_UNIT_BRANCH_AND_TOTAL_VALIDATION",
        "table_receipts": [canonical_clone_v1(item["receipt"]) for item in parsed],
        "unit_receipt": {
            "canonical_unit": unit,
            "document_unit_context_evidence": checked_unit_context,
            "explicit_unit_axis": unit_resolution["explicit_unit_axis"],
            "source": unit_resolution["source"],
            "table_unit_assignment_axis": unit_resolution["table_unit_assignment_axis"],
        },
    }
    first = checked[0]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": closure,
        "component_regions": checked,
        "document_id": first["document_id"],
        "family_id": compiled_specs["family_id"],
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": status,
        "table_id": first["table_id"],
    }
    return {"candidate_id": "gjeqmfv1:candidate:" + canonical_json_sha256_v1(material), **material}


def _rebuild_segment_report_closure_axes_v1(
    *,
    closure: Mapping[str, Any],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    status: str,
) -> dict[str, Any]:
    """Rebuild redundant candidate axes from typed table receipts.

    This proves internal coherence without claiming source authenticity.  The
    public SQLite candidate replay remains the source-authentic boundary.
    """

    table_receipts = closure.get("table_receipts")
    if type(table_receipts) is not list or len(table_receipts) != len(regions):
        raise _error("segment-report table receipt axis is incomplete")
    base_fields = {
        "branch",
        "branch_authority",
        "cell_axis",
        "equations",
        "local_period_end_axis",
        "orientation",
        "period_year",
        "region",
        "unit",
    }
    branch_binding_by_region = _checked_owner_branch_binding_axis_v1(
        owner_receipt=closure.get("query_receipt", {}).get("owner_receipt", {}),
        regions=regions,
        compiled=compiled_specs,
    )
    optional_fields = {
        "period_assignment_evidence",
        "period_assignment_rule",
        "period_role",
        "period_role_by_metric",
    }
    visible_years: set[int] = set()
    for receipt, region in zip(table_receipts, regions, strict=True):
        if (
            type(receipt) is not dict
            or not base_fields <= set(receipt) <= base_fields | optional_fields
            or not same_typed_json_v1(receipt.get("region"), region)
            or receipt.get("orientation") not in {"METRIC_ROWS", "METRIC_COLUMNS"}
            or receipt.get("branch") not in compiled_specs["branch_bindings_by_role"]
            or type(receipt.get("cell_axis")) is not list
            or type(receipt.get("equations")) is not list
            or type(receipt.get("local_period_end_axis")) is not list
            or not same_typed_json_v1(
                receipt.get("branch_authority"),
                branch_binding_by_region.get(canonical_json_sha256_v1(region)),
            )
        ):
            raise _error("segment-report table receipt binding drifted")
        table_role = receipt.get("period_role")
        if table_role is not None and table_role not in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}:
            raise _error("segment-report table period role is invalid")
        metric_roles = receipt.get("period_role_by_metric", {})
        if type(metric_roles) is not dict or any(
            type(metric) is not str or role not in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
            for metric, role in metric_roles.items()
        ):
            raise _error("segment-report metric period role is invalid")
        for cell in receipt["cell_axis"]:
            if type(cell) is not dict:
                raise _error("segment-report table cell receipt is invalid")
            year = cell.get("period_year")
            if year is not None:
                if type(year) is not int:
                    raise _error("segment-report table cell period is invalid")
                visible_years.add(year)
    owner_years = (
        closure.get("query_receipt", {}).get("owner_receipt", {}).get("reporting_year_axis", [])
    )
    if type(owner_years) is not list or any(type(year) is not int for year in owner_years):
        raise _error("segment-report closure reporting year axis is invalid")
    owner_current_year = owner_years[0] if owner_years else None
    if owner_current_year is not None:
        explicit_years = [
            year
            for year in (owner_current_year, owner_current_year - 1)
            if year == owner_current_year or year in visible_years
        ]
    else:
        explicit_years = sorted(visible_years, reverse=True)
        if len(explicit_years) == 1:
            explicit_years = []
        elif len(explicit_years) == 2 and explicit_years[0] - explicit_years[1] != 1:
            explicit_years = []
    period_role_by_year: dict[int, str] = {}
    if explicit_years:
        period_role_by_year[explicit_years[0]] = "CURRENT_PERIOD"
    if len(explicit_years) > 1:
        period_role_by_year[explicit_years[1]] = "COMPARATIVE_PERIOD"

    _validate_segment_period_assignment_evidence_v1(
        table_receipts,
        compiled_specs=compiled_specs,
        owner_receipt=closure.get("query_receipt", {}).get("owner_receipt", {}),
        period_role_by_year=period_role_by_year,
        unit_receipt=closure.get("unit_receipt", {}),
    )

    def receipt_period_role(
        receipt: Mapping[str, Any], *, metric_role: Any, period_year: Any
    ) -> str | None:
        metric_roles = receipt.get("period_role_by_metric", {})
        assigned = metric_roles.get(metric_role) or receipt.get("period_role")
        visible = period_role_by_year.get(period_year)
        if assigned is not None and visible is not None and assigned != visible:
            raise _error("segment-report period receipt contradicts visible source year")
        return assigned or visible

    period_end_resolution = _resolve_segment_period_end_assignments_v1(
        table_receipts,
        owner_receipt=closure.get("query_receipt", {}).get("owner_receipt", {}),
        period_role_by_year=period_role_by_year,
    )
    period_assignment_by_cell_ref = {
        canonical_json_sha256_v1(item["cell_ref"]): item
        for item in period_end_resolution["period_assignment_axis"]
    }

    blanks: list[dict[str, Any]] = []
    equations: list[dict[str, Any]] = []
    keyed: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    semantic_cells: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    duplicate_equivalent_cells: list[dict[str, Any]] = []
    equation_signatures: dict[tuple[str, str, str], dict[str, Any]] = {}
    derived_reasons: set[str] = set(period_end_resolution["reasons"])
    for receipt in table_receipts:
        cell_by_ref: dict[str, dict[str, Any]] = {}
        for cell in receipt["cell_axis"]:
            cell_ref = cell.get("cell_ref") if type(cell) is dict else None
            if type(cell_ref) is not dict:
                raise _error("segment-report table cell locator is invalid")
            ref_key = canonical_json_sha256_v1(cell_ref)
            if ref_key in cell_by_ref:
                raise _error("segment-report table cell locator is duplicate")
            cell_by_ref[ref_key] = cell
            if cell.get("metric_role") in compiled_specs["metric_offset_by_role"]:
                if cell.get("state") == "INVALID_MONEY_SOURCE":
                    derived_reasons.add("SEGMENT_MONEY_CELL_INVALID")
                if "coefficient_candidates" in cell:
                    derived_reasons.add("SEGMENT_MONEY_CELL_AMBIGUOUS")
        for equation in receipt["equations"]:
            if (
                type(equation) is not dict
                or set(equation)
                != {
                    "branch",
                    "computed_value",
                    "metric_role",
                    "period_year",
                    "result_cell",
                    "status",
                    "term_cells",
                }
                or type(equation.get("result_cell")) is not dict
                or type(equation.get("term_cells")) is not list
            ):
                raise _error("segment-report equation receipt is invalid")
            equation_cells = [equation["result_cell"], *equation["term_cells"]]
            resolved_cells = []
            for equation_cell in equation_cells:
                cell_ref = equation_cell.get("cell_ref") if type(equation_cell) is dict else None
                source_cell = (
                    cell_by_ref.get(canonical_json_sha256_v1(cell_ref))
                    if type(cell_ref) is dict
                    else None
                )
                if source_cell is None:
                    raise _error("segment-report equation cell is outside table cell axis")
                source_projection = {
                    key: source_cell[key]
                    for key in source_cell
                    if key not in {"axis_role", "branch", "metric_role", "period_year"}
                }
                if not same_typed_json_v1(equation_cell, source_projection):
                    raise _error("segment-report equation cell drifted from table cell axis")
                resolved_cells.append(source_cell)
            result_source, *term_sources = resolved_cells
            if (
                result_source.get("axis_role") != "TOTAL"
                or any(cell.get("axis_role") == "TOTAL" for cell in term_sources)
                or any(
                    cell.get("branch") != equation.get("branch")
                    or cell.get("metric_role") != equation.get("metric_role")
                    or cell.get("period_year") != equation.get("period_year")
                    for cell in resolved_cells
                )
            ):
                raise _error("segment-report equation semantic axis drifted")
            expected_term_sources = [
                cell
                for cell in receipt["cell_axis"]
                if cell.get("branch") == equation.get("branch")
                and cell.get("metric_role") == equation.get("metric_role")
                and cell.get("period_year") == equation.get("period_year")
                and cell.get("axis_role") != "TOTAL"
                and (
                    cell.get("cell_ref", {}).get("row_id")
                    == result_source.get("cell_ref", {}).get("row_id")
                    if receipt["orientation"] == "METRIC_ROWS"
                    else cell.get("cell_ref", {}).get("column_id")
                    == result_source.get("cell_ref", {}).get("column_id")
                )
            ]
            if [cell["cell_ref"] for cell in term_sources] != [
                cell["cell_ref"] for cell in expected_term_sources
            ]:
                raise _error("segment-report equation frontier is not exhaustive")
            coefficients = [cell.get("coefficient") for cell in resolved_cells]
            expected_status = (
                "NOT_TESTABLE_SOURCE_BLANK"
                if any(coefficient is None for coefficient in coefficients)
                else "EXACT"
                if sum(coefficients[1:]) == coefficients[0]
                else "EXACT_ROUNDING_RESIDUAL"
                if abs(sum(coefficients[1:]) - coefficients[0])
                <= max(1, len(coefficients[1:]) // 2)
                else "MISMATCH"
            )
            expected_computed = (
                None if expected_status == "NOT_TESTABLE_SOURCE_BLANK" else sum(coefficients[1:])
            )
            if (
                equation.get("status") != expected_status
                or equation.get("computed_value") != expected_computed
            ):
                raise _error("segment-report equation result drifted")
            if (
                expected_status == "MISMATCH"
                and equation.get("metric_role") in compiled_specs["metric_offset_by_role"]
            ):
                derived_reasons.add("VISIBLE_SEGMENT_TOTAL_MISMATCH")
            axis_period = receipt_period_role(
                receipt,
                metric_role=equation.get("metric_role"),
                period_year=equation.get("period_year"),
            )
            if axis_period is not None:
                mapped_metric = (
                    equation.get("metric_role") in compiled_specs["metric_offset_by_role"]
                )
                equation_period_assignments = [
                    period_assignment_by_cell_ref.get(canonical_json_sha256_v1(cell["cell_ref"]))
                    for cell in resolved_cells
                ]
                equation_period_ends = {
                    assignment.get("period_end") if assignment is not None else None
                    for assignment in equation_period_assignments
                }
                if mapped_metric and len(equation_period_ends) > 1:
                    derived_reasons.add("SEGMENT_EQUATION_PERIOD_END_CONFLICT")
                equation_key = (
                    equation["branch"],
                    equation["metric_role"],
                    axis_period,
                )
                semantic_signature = {
                    "computed_value": expected_computed,
                    "period_end": (
                        equation_period_assignments[0].get("period_end")
                        if equation_period_assignments[0] is not None
                        else None
                    ),
                    "result_coefficient": result_source.get("coefficient"),
                    "status": expected_status,
                    "term_axis": sorted(
                        [
                            {
                                "axis_role": cell.get("axis_role"),
                                "coefficient": cell.get("coefficient"),
                            }
                            for cell in term_sources
                        ],
                        key=canonical_json_sha256_v1,
                    ),
                }
                prior_signature = equation_signatures.get(equation_key)
                if prior_signature is not None:
                    if mapped_metric and prior_signature != semantic_signature:
                        derived_reasons.add("CONFLICTING_DUPLICATE_SEGMENT_EQUATION")
                    continue
                equation_signatures[equation_key] = semantic_signature
                equation_period_assignment = period_assignment_by_cell_ref.get(
                    canonical_json_sha256_v1(result_source["cell_ref"])
                )
                equations.append(
                    {
                        "axis_role": axis_period,
                        "period_assignment_id": (
                            equation_period_assignment["period_assignment_id"]
                            if equation_period_assignment is not None
                            else None
                        ),
                        "period_end": (
                            equation_period_assignment["period_end"]
                            if equation_period_assignment is not None
                            else None
                        ),
                        **canonical_clone_v1(equation),
                    }
                )
        for cell in receipt["cell_axis"]:
            axis_period = receipt_period_role(
                receipt,
                metric_role=cell.get("metric_role"),
                period_year=cell.get("period_year"),
            )
            if axis_period is None:
                continue
            axis = cell.get("axis_role")
            branch = cell.get("branch")
            metric = cell.get("metric_role")
            mapped_metric = metric in compiled_specs["metric_offset_by_role"]
            semantic_key = (branch, axis, metric, axis_period)
            prior_cell = semantic_cells.get(semantic_key)
            if prior_cell is not None:
                prior_period_assignment = period_assignment_by_cell_ref.get(
                    canonical_json_sha256_v1(prior_cell["cell_ref"])
                )
                current_period_assignment = period_assignment_by_cell_ref.get(
                    canonical_json_sha256_v1(cell["cell_ref"])
                )
                same_endpoint = (
                    prior_period_assignment.get("period_end")
                    if prior_period_assignment is not None
                    else None
                ) == (
                    current_period_assignment.get("period_end")
                    if current_period_assignment is not None
                    else None
                )
                same_value_and_endpoint = (
                    prior_cell.get("coefficient") == cell.get("coefficient") and same_endpoint
                )
                if same_value_and_endpoint:
                    duplicate_equivalent_cells.append(
                        {
                            "axis_key": {
                                "axis_role": axis,
                                "branch": branch,
                                "metric_role": metric,
                                "period_role": axis_period,
                            },
                            "canonical_cell_ref": canonical_clone_v1(prior_cell["cell_ref"]),
                            "coefficient": cell.get("coefficient"),
                            "duplicate_cell_ref": canonical_clone_v1(cell["cell_ref"]),
                            "period_end": (
                                current_period_assignment.get("period_end")
                                if current_period_assignment is not None
                                else None
                            ),
                            "rule": "SEMANTICALLY_EQUIVALENT_DUPLICATE_SOURCE_CELL_COLLAPSED",
                        }
                    )
                elif mapped_metric:
                    derived_reasons.add("CONFLICTING_DUPLICATE_SEGMENT_AXIS_METRIC_PERIOD_CELL")
                continue
            semantic_cells[semantic_key] = cell
            cell_period_assignment = period_assignment_by_cell_ref.get(
                canonical_json_sha256_v1(cell["cell_ref"])
            )
            if _is_declared_segment_mapping_cell_v1(cell, compiled_specs=compiled_specs) and (
                cell_period_assignment is None or cell_period_assignment.get("period_end") is None
            ):
                derived_reasons.add("SEGMENT_PERIOD_END_NOT_RESOLVED")
            if cell.get("coefficient") is None:
                if cell.get("state") == "SOURCE_BLANK":
                    blanks.append(
                        {
                            "axis_role": axis_period,
                            "period_assignment_id": (
                                cell_period_assignment["period_assignment_id"]
                                if cell_period_assignment is not None
                                else None
                            ),
                            "period_end": (
                                cell_period_assignment["period_end"]
                                if cell_period_assignment is not None
                                else None
                            ),
                            **canonical_clone_v1(cell),
                        }
                    )
                continue
            if type(axis) is not str or axis.startswith("SOURCE_ONLY:"):
                continue
            if (
                branch not in compiled_specs["branch_bindings_by_role"]
                or metric not in compiled_specs["metric_offset_by_role"]
                or axis
                not in compiled_specs["branch_bindings_by_role"][branch][
                    "axis_parent_report_norm_id_by_role"
                ]
            ):
                continue
            keyed[semantic_key] = cell
    mappings: list[dict[str, Any]] = []
    unit_receipt = closure.get("unit_receipt")
    if (
        type(unit_receipt) is not dict
        or set(unit_receipt)
        != {
            "canonical_unit",
            "document_unit_context_evidence",
            "explicit_unit_axis",
            "source",
            "table_unit_assignment_axis",
        }
        or type(unit_receipt.get("explicit_unit_axis")) is not list
    ):
        raise _error("segment-report unit receipt is invalid")
    checked_unit_context = _checked_document_unit_context_v1(
        unit_receipt.get("document_unit_context_evidence"), compiled=compiled_specs
    )
    expected_unit_resolution = _resolve_segment_table_units_v1(
        table_receipts, unit_context=checked_unit_context, compiled=compiled_specs
    )
    unit = unit_receipt.get("canonical_unit")
    accepted_units = {
        item["canonical_unit"] for item in compiled_specs["unit_bindings"] if item["accepted"]
    }
    if (
        unit != expected_unit_resolution["canonical_unit"]
        or unit_receipt.get("source") != expected_unit_resolution["source"]
        or not same_typed_json_v1(
            unit_receipt.get("explicit_unit_axis"),
            expected_unit_resolution["explicit_unit_axis"],
        )
        or not same_typed_json_v1(
            unit_receipt.get("table_unit_assignment_axis"),
            expected_unit_resolution["table_unit_assignment_axis"],
        )
        or (status == READY and expected_unit_resolution["reasons"])
        or (unit is not None and unit not in accepted_units)
    ):
        raise _error("segment-report canonical unit drifted from explicit table evidence")
    if status == READY:
        if type(unit) is not str or not unit:
            raise _error("segment-report READY unit is absent")
        grouping: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for (branch, axis, metric, axis_period), cell in keyed.items():
            cell_period_assignment = period_assignment_by_cell_ref[
                canonical_json_sha256_v1(cell["cell_ref"])
            ]
            grouping.setdefault((branch, axis, metric), []).append(
                {
                    "axis_role": axis_period,
                    "cell_ref": canonical_clone_v1(cell["cell_ref"]),
                    "coefficient": cell["coefficient"],
                    "equation_multiplier": 1,
                    "period_assignment_id": cell_period_assignment["period_assignment_id"],
                    "period_end": cell_period_assignment["period_end"],
                    "source_text": cell["source_text"],
                    "state": cell["state"],
                }
            )
        for (branch, axis, metric), values in sorted(grouping.items()):
            values.sort(
                key=lambda item: (
                    item["axis_role"] != "CURRENT_PERIOD",
                    canonical_json_sha256_v1(item["cell_ref"]),
                )
            )
            mappings.append(
                _mapping(
                    branch=branch,
                    axis_role=axis,
                    metric_role=metric,
                    unit=unit,
                    values=values,
                    compiled=compiled_specs,
                )
            )
    return {
        "blank_cell_axis": blanks,
        "derived_reasons": sorted(derived_reasons),
        "duplicate_equivalent_cell_axis": duplicate_equivalent_cells,
        "equations": equations,
        "mapping_axis": mappings,
        "period_receipt": {
            "period_assignment_axis": period_end_resolution["period_assignment_axis"],
            "rule": period_end_resolution["rule"],
        },
    }


def validate_gemini_json_segment_report_candidate_binding_v1(
    value: Any,
    *,
    document: Mapping[str, Any],
    cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    fields = {
        "candidate_id",
        "claim_boundary",
        "closure_receipt",
        "component_regions",
        "document_id",
        "family_id",
        "mappings",
        "page_json_version_id",
        "physical_page",
        "reasons",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "status",
        "table_id",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("segment-report candidate shape is invalid")
    regions = checked_segment_report_region_axis_v1(cluster.get("component_regions", []))
    first = regions[0]
    closure = value.get("closure_receipt")
    if (
        value.get("claim_boundary") != CLAIM_BOUNDARY
        or value.get("family_id") != compiled_specs["family_id"]
        or not same_typed_json_v1(value.get("component_regions"), regions)
        or any(
            value.get(key) != first[key]
            for key in (
                "document_id",
                "page_json_version_id",
                "physical_page",
                "section_id",
                "table_id",
                "source_logical_name",
                "source_sha256",
            )
        )
        or any(value.get(key) != document[key] for key in ("source_logical_name", "source_sha256"))
        or type(value.get("reasons")) is not list
        or value["reasons"] != sorted(set(value["reasons"]))
        or value.get("status") not in {READY, UNRESOLVED}
        or type(closure) is not dict
        or set(closure)
        != {
            "blank_cell_axis",
            "duplicate_equivalent_cell_axis",
            "equations",
            "mapping_axis",
            "period_receipt",
            "query_receipt",
            "rule",
            "table_receipts",
            "unit_receipt",
        }
        or closure.get("rule")
        != "MAP_VISIBLE_SEGMENT_INTERSECTIONS_AFTER_PERIOD_UNIT_BRANCH_AND_TOTAL_VALIDATION"
        or not same_typed_json_v1(closure.get("mapping_axis"), value.get("mappings"))
    ):
        raise _error("segment-report candidate binding drifted")
    expected_query = build_segment_report_region_query_receipt_v1(
        regions, owner_receipt=cluster.get("owner_receipt", {})
    )
    if not same_typed_json_v1(closure["query_receipt"], expected_query):
        raise _error("segment-report candidate query receipt drifted")
    if not same_typed_json_v1(
        closure["unit_receipt"].get("document_unit_context_evidence"),
        cluster.get("document_unit_context_evidence"),
    ):
        raise _error("segment-report candidate document unit context drifted")
    rebuilt_axes = _rebuild_segment_report_closure_axes_v1(
        closure=closure,
        regions=regions,
        compiled_specs=compiled_specs,
        status=value["status"],
    )
    if any(
        not same_typed_json_v1(closure[name], rebuilt_axes[name])
        for name in (
            "blank_cell_axis",
            "duplicate_equivalent_cell_axis",
            "equations",
            "mapping_axis",
            "period_receipt",
        )
    ):
        raise _error("segment-report candidate closure axes drifted")
    if any(reason not in value["reasons"] for reason in rebuilt_axes["derived_reasons"]):
        raise _error("segment-report candidate derived reasons are incomplete")
    expected_id = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {k: v for k, v in value.items() if k != "candidate_id"}
    )
    if value.get("candidate_id") != expected_id:
        raise _error("segment-report candidate identity drifted")
    if value["status"] == READY:
        if value["reasons"] or not value["mappings"]:
            raise _error("segment-report READY candidate is incomplete")
    elif value["mappings"] or not value["reasons"]:
        raise _error("segment-report unresolved candidate semantics drifted")
    return canonical_clone_v1(value)
