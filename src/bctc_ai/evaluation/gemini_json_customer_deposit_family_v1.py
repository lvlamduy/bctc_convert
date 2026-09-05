"""Customer-deposit multi-view accounting closure over selected Gemini JSON.

The engine is bank/file/page blind.  It accepts the two source presentations
observed in the corpus (one row-oriented two-period table, or two stacked
period tables with VND/foreign/total columns), optionally joins a customer-type
view inside the same owner/reset fence, and derives all schema mappings from
source rows plus exact accounting closure.  Gemini is not asked to construct
roles, equations, or a graph.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _COMPARATIVE_PERIOD_ALIASES,
    _CURRENT_PERIOD_ALIASES,
    _header_dates,
    _header_text,
    _money,
)
from bctc_ai.evaluation.source_observation_lane_math_v1 import (
    additive_source_lane_receipts_v1,
    observed_source_coefficient_v1,
    partial_source_mapping_values_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_CUSTOMER_DEPOSIT_ACCOUNTING_FAMILY_V1"
INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = "GEMINI_JSON_INDEXED_CUSTOMER_DEPOSIT_QUERY_EVIDENCE_V1"
EVALUATION_FORMAT_VERSION = "ACCOUNTING_CUSTOMER_DEPOSIT_FAMILY_EVALUATION_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_CUSTOMER_DEPOSIT_SCHEMA_BINDING_SPEC_V1"
SOURCE_REPAIR_FORMAT_VERSION = (
    "GEMINI_JSON_CUSTOMER_DEPOSIT_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
)
SOURCE_REPAIR_ADAPTER_FORMAT_VERSION = (
    "GEMINI_JSON_CUSTOMER_DEPOSIT_SOURCE_REPAIR_ADAPTER_V1"
)
FAMILY_ID = "CUSTOMER_DEPOSIT_CLASSIFICATION"
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_CUSTOMER_DEPOSIT_OWNER_RESET_"
    "FENCE_ROW_PERIOD_OR_STACKED_PERIOD_CURRENCY_LAYOUT_OPTIONAL_CUSTOMER_VIEW_"
    "EXACT_PERIOD_UNIT_HIERARCHY_TOTAL_AND_CHILD_CLOSURE_OR_DISCLOSED_BOUNDED_"
    "MILLION_VND_ROUNDING_OBSERVED_LANES_ONLY_BLANK_SOURCE_LANES_PRESERVED_"
    "STRUCTURAL_ROOT_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_GEOMETRY_OCR_BANK_FILE_PAGE_"
    "NOTE_ROUTING_BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")

_TYPE_SOURCE_ROLES = (
    "NO_TERM",
    "TERM",
    "SAVINGS_COMBINED",
    "SAVINGS_NO_TERM",
    "SAVINGS_TERM",
    "ESCROW",
    "DEDICATED",
    "OTHER_PAYMENT_GUARANTEE",
)
_BASE_TYPE_ROLES = (
    "NO_TERM",
    "TERM",
    "ESCROW",
    "DEDICATED",
    "OTHER_PAYMENT_GUARANTEE",
)
_DISTINCTIVE_TYPE_ROLES = {
    "SAVINGS_COMBINED",
    "SAVINGS_NO_TERM",
    "SAVINGS_TERM",
    "ESCROW",
    "DEDICATED",
    "OTHER_PAYMENT_GUARANTEE",
}
_CUSTOMER_SOURCE_ROLES = (
    "CUSTOMER_TCKT",
    "STATE_COMPANY",
    "TNHH",
    "STATE_100_TNHH",
    "STATE_OVER_50_ONE_MEMBER_TNHH",
    "STATE_OVER_50_MULTI_MEMBER_TNHH",
    "OTHER_TNHH",
    "STATE_OVER_50_JSC",
    "OTHER_JSC",
    "PRIVATE_ENTERPRISE",
    "COMBINED_COMPANY",
    "COOPERATIVE",
    "JOINT_VENTURE_COOPERATIVE",
    "PARTNERSHIP",
    "FOREIGN_INVESTED",
    "HOUSEHOLD_INDIVIDUAL",
    "ADMIN_ASSOCIATION",
    "OTHER_CUSTOMER",
)
_CUSTOMER_TCKT_CHILD_ROLES = {
    "STATE_COMPANY",
    "TNHH",
    "STATE_100_TNHH",
    "STATE_OVER_50_ONE_MEMBER_TNHH",
    "STATE_OVER_50_MULTI_MEMBER_TNHH",
    "OTHER_TNHH",
    "STATE_OVER_50_JSC",
    "OTHER_JSC",
    "PRIVATE_ENTERPRISE",
    "COMBINED_COMPANY",
    "COOPERATIVE",
    "JOINT_VENTURE_COOPERATIVE",
    "PARTNERSHIP",
    "FOREIGN_INVESTED",
}
_TYPE_OUTPUT_ROLES = (
    "NO_TERM",
    "NO_TERM_VND",
    "NO_TERM_FOREIGN",
    "TERM",
    "TERM_VND",
    "TERM_FOREIGN",
    "SAVINGS",
    "SAVINGS_VND",
    "SAVINGS_FOREIGN",
    "ESCROW",
    "ESCROW_VND",
    "ESCROW_FOREIGN",
    "DEDICATED",
    "DEDICATED_VND",
    "DEDICATED_FOREIGN",
    "OTHER_PAYMENT_GUARANTEE",
    "OTHER_PAYMENT_GUARANTEE_VND",
    "OTHER_PAYMENT_GUARANTEE_FOREIGN",
)
_CUSTOMER_OUTPUT_ROLES = tuple(
    role for role in _CUSTOMER_SOURCE_ROLES if role != "STATE_OVER_50_MULTI_MEMBER_TNHH"
)
_OUTPUT_ROLES = {*_TYPE_OUTPUT_ROLES, *_CUSTOMER_OUTPUT_ROLES}


class GeminiJsonCustomerDepositFamilyV1Error(ValueError):
    """The selected source, declarative triplet, or closure drifted."""


def _error(message: str) -> GeminiJsonCustomerDepositFamilyV1Error:
    return GeminiJsonCustomerDepositFamilyV1Error(message)


def _validate_source_repairs(value: Any) -> list[dict[str, Any]]:
    render_contract = {
        "alpha": False,
        "colorspace": "RGB",
        "format": "PNG",
        "render_dpi": 300,
        "renderer": "BCTC_AI_FULL_PDF_PAGE_RENDER_V1_PYMUPDF",
    }
    if (
        type(value) is not dict
        or set(value)
        != {
            "family_id",
            "format_version",
            "policy",
            "render_contract",
            "repair_axis_sha256",
            "repairs",
        }
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != SOURCE_REPAIR_FORMAT_VERSION
        or value.get("policy")
        != "ONLY_PDF_VISIBLE_ACCOUNTING_DASH_MISSING_AS_NULL_NO_BLANK_ZERO_INFERENCE"
        or value.get("render_contract") != render_contract
        or type(value.get("repairs")) is not list
    ):
        raise _error("customer-deposit authenticated source-repair spec is invalid")
    checked = []
    identities = set()
    for repair in value["repairs"]:
        locator = repair.get("locator") if type(repair) is dict else None
        source = repair.get("source") if type(repair) is dict else None
        render = repair.get("render") if type(repair) is dict else None
        crop = repair.get("crop_evidence") if type(repair) is dict else None
        bbox = crop.get("bbox_pixels_xyxy") if type(crop) is dict else None
        if (
            type(repair) is not dict
            or set(repair)
            != {
                "after_exact",
                "before_exact",
                "crop_evidence",
                "locator",
                "observed_pdf_glyph",
                "repair_id",
                "repair_kind",
                "render",
                "source",
            }
            or repair.get("repair_kind") != "MONEY_CELL_VISIBLE_DASH"
            or repair.get("before_exact") is not None
            or repair.get("after_exact") != "-"
            or repair.get("observed_pdf_glyph") != "-"
            or type(locator) is not dict
            or set(locator)
            != {
                "column_ordinal",
                "page_json_version_id",
                "physical_page",
                "row_ordinal",
                "section_id",
                "table_id",
            }
            or _PAGE_VERSION.fullmatch(locator.get("page_json_version_id", "")) is None
            or type(locator.get("physical_page")) is not int
            or locator["physical_page"] <= 0
            or type(locator.get("row_ordinal")) is not int
            or locator["row_ordinal"] <= 0
            or type(locator.get("column_ordinal")) is not int
            or locator["column_ordinal"] <= 0
            or _SECTION_ID.fullmatch(locator.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(locator.get("table_id", "")) is None
            or type(source) is not dict
            or set(source)
            != {"source_logical_name", "source_sha256", "source_size_bytes"}
            or type(source.get("source_logical_name")) is not str
            or not source["source_logical_name"]
            or source["source_logical_name"].startswith("/")
            or ".." in source["source_logical_name"].split("/")
            or _SHA256.fullmatch(source.get("source_sha256", "")) is None
            or type(source.get("source_size_bytes")) is not int
            or source["source_size_bytes"] <= 0
            or type(render) is not dict
            or set(render)
            != {
                "image_sha256",
                "image_size_bytes",
                "media_type",
                "physical_page",
                "pixel_height",
                "pixel_width",
                "render_dpi",
                "render_receipt_sha256",
            }
            or render.get("physical_page") != locator["physical_page"]
            or render.get("render_dpi") != 300
            or render.get("media_type") != "image/png"
            or _SHA256.fullmatch(render.get("image_sha256", "")) is None
            or _SHA256.fullmatch(render.get("render_receipt_sha256", "")) is None
            or any(
                type(render.get(field)) is not int or render[field] <= 0
                for field in ("image_size_bytes", "pixel_height", "pixel_width")
            )
            or type(crop) is not dict
            or set(crop)
            != {
                "bbox_pixels_xyxy",
                "pixel_height",
                "pixel_width",
                "rgb_sha256",
            }
            or type(bbox) is not list
            or len(bbox) != 4
            or any(type(item) is not int for item in bbox)
            or not (0 <= bbox[0] < bbox[2] <= render["pixel_width"])
            or not (0 <= bbox[1] < bbox[3] <= render["pixel_height"])
            or crop.get("pixel_width") != bbox[2] - bbox[0]
            or crop.get("pixel_height") != bbox[3] - bbox[1]
            or _SHA256.fullmatch(crop.get("rgb_sha256", "")) is None
        ):
            raise _error("customer-deposit authenticated source repair is invalid")
        material = {
            key: canonical_clone_v1(item)
            for key, item in repair.items()
            if key != "repair_id"
        }
        if repair.get("repair_id") != (
            "gjfcdav1:source-repair:" + canonical_json_sha256_v1(material)
        ):
            raise _error("customer-deposit source-repair identity drifted")
        identity = (
            source["source_sha256"],
            locator["page_json_version_id"],
            locator["section_id"],
            locator["table_id"],
            locator["row_ordinal"],
            locator["column_ordinal"],
        )
        if identity in identities:
            raise _error("customer-deposit source-repair cell axis is duplicate")
        identities.add(identity)
        checked.append(canonical_clone_v1(repair))
    if value.get("repair_axis_sha256") != canonical_json_sha256_v1(checked):
        raise _error("customer-deposit source-repair axis seal drifted")
    return checked


def _normalized(value: Any) -> str:
    return normalize_vietnamese_anchor_v1(value) if type(value) is str else ""


def _compile_units(value: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Compile an exact, collision-free money-unit policy.

    This low-level helper is also used by the generic hierarchical evaluator,
    whose families can intentionally accept a different unit frontier.  The
    customer-deposit-specific accepted-unit invariant is therefore enforced
    by its compiler after this structural validation.
    """

    if type(value) is not list or not value:
        raise _error("customer-deposit money-unit bindings are absent")
    checked: list[dict[str, Any]] = []
    by_alias: dict[str, dict[str, Any]] = {}
    canonical_units: set[str] = set()
    for raw in value:
        if (
            type(raw) is not dict
            or set(raw) != {"accepted", "aliases", "canonical_unit", "magnitude_power10"}
            or type(raw.get("accepted")) is not bool
            or type(raw.get("aliases")) is not list
            or not raw["aliases"]
            or any(type(alias) is not str or not alias.strip() for alias in raw["aliases"])
            or type(raw.get("canonical_unit")) is not str
            or not raw["canonical_unit"]
            or raw["canonical_unit"] in canonical_units
            or type(raw.get("magnitude_power10")) is not int
            or raw["magnitude_power10"] < 0
        ):
            raise _error("customer-deposit money-unit binding is invalid")
        aliases = [_normalized(alias) for alias in raw["aliases"]]
        if any(not alias or alias in by_alias for alias in aliases):
            raise _error("customer-deposit money-unit aliases collide")
        canonical_units.add(raw["canonical_unit"])
        binding = {**canonical_clone_v1(raw), "aliases": aliases}
        for alias in aliases:
            by_alias[alias] = binding
        checked.append(binding)
    if not any(item["accepted"] for item in checked):
        raise _error("money-unit policy has no accepted unit")
    return checked, by_alias


def compile_gemini_json_customer_deposit_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile a data-only customer-deposit topology/evaluation/schema triplet."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("customer-deposit topology spec is invalid") from exc
    evaluation_fields = {
        "blank_zero_policy",
        "closure_policy",
        "customer_view_policy",
        "family_id",
        "format_version",
        "layout_policy",
        "money_unit_bindings",
        "period_semantics",
        "stacked_currency_aliases",
        "type_direct_roles",
        "type_parent_shorthand_aliases",
        "type_savings_source_roles",
    }
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec) != evaluation_fields
        or evaluation_spec.get("format_version") != EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("blank_zero_policy")
        != "PRESERVE_BLANK_SOURCE_CELLS_AND_OMIT_ALL_BLANK_ROLES"
        or evaluation_spec.get("closure_policy")
        != (
            "EXACT_OR_BOUNDED_MILLION_VND_ROUNDING_TYPE_CURRENCY_AND_OPTIONAL_"
            "CUSTOMER_VIEW_ALL_LANES"
        )
        or evaluation_spec.get("customer_view_policy")
        != "OPTIONAL_ONLY_WITHIN_SAME_OWNER_OR_EXPLICIT_CONTINUATION_FENCE"
        or evaluation_spec.get("layout_policy")
        != "ONE_TWO_PERIOD_TABLE_OR_TWO_STACKED_PERIOD_CURRENCY_TABLES"
        or evaluation_spec.get("period_semantics") != "CURRENT_AND_COMPARATIVE_SNAPSHOT"
        or evaluation_spec.get("type_direct_roles") != list(_BASE_TYPE_ROLES)
        or evaluation_spec.get("type_savings_source_roles")
        != ["SAVINGS_COMBINED", "SAVINGS_NO_TERM", "SAVINGS_TERM"]
    ):
        raise _error("customer-deposit evaluation spec is invalid")
    aliases_by_source_role: dict[str, list[str]] = {}
    for child in topology["children"]:
        aliases = sorted(
            {
                alias
                for matcher in child["matchers"]
                if matcher["within_role"] is None
                for alias in matcher["aliases"]
            }
        )
        if not aliases:
            raise _error("customer-deposit source role has no root alias")
        aliases_by_source_role[child["role"]] = aliases
    expected_source_roles = {*_TYPE_SOURCE_ROLES, *_CUSTOMER_SOURCE_ROLES}
    if set(aliases_by_source_role) != expected_source_roles:
        raise _error("customer-deposit source-role frontier is incomplete")
    currency_aliases = evaluation_spec["stacked_currency_aliases"]
    if type(currency_aliases) is not dict or set(currency_aliases) != {"VND", "FOREIGN", "TOTAL"}:
        raise _error("customer-deposit stacked currency axis is invalid")
    compiled_currency_aliases = {}
    for role, aliases in currency_aliases.items():
        if (
            type(aliases) is not list
            or not aliases
            or any(type(alias) is not str or not alias.strip() for alias in aliases)
        ):
            raise _error("customer-deposit stacked currency aliases are invalid")
        folded = [_normalized(alias) for alias in aliases]
        if len(folded) != len(set(folded)):
            raise _error("customer-deposit stacked currency aliases collide")
        compiled_currency_aliases[role] = folded
    shorthand = evaluation_spec["type_parent_shorthand_aliases"]
    if type(shorthand) is not dict or set(shorthand) != {"NO_TERM", "TERM"}:
        raise _error("customer-deposit parent shorthand declarations are invalid")
    compiled_shorthand = {}
    for role, aliases in shorthand.items():
        if type(aliases) is not list or not aliases:
            raise _error("customer-deposit parent shorthand declarations are invalid")
        compiled_shorthand[role] = [_normalized(alias) for alias in aliases]
    units, units_by_alias = _compile_units(evaluation_spec["money_unit_bindings"])
    if {item["canonical_unit"] for item in units if item["accepted"]} != {
        "MILLION_VND",
        "VND",
    }:
        raise _error("customer-deposit accepted money-unit axis is invalid")
    schema_fields = {
        "family_id",
        "family_root_report_norm_id",
        "format_version",
        "role_bindings",
        "root_mapping_policy",
        "schema_period_type",
    }
    if (
        type(schema_binding_spec) is not dict
        or set(schema_binding_spec) != schema_fields
        or schema_binding_spec.get("format_version") != SCHEMA_FORMAT_VERSION
        or schema_binding_spec.get("family_id") != topology["family_id"]
        or type(schema_binding_spec.get("family_root_report_norm_id")) is not int
        or schema_binding_spec["family_root_report_norm_id"] <= 0
        or schema_binding_spec.get("root_mapping_policy") != "STRUCTURAL_CONTEXT_ONLY"
        or schema_binding_spec.get("schema_period_type") != "SNAPSHOT"
        or type(schema_binding_spec.get("role_bindings")) is not list
    ):
        raise _error("customer-deposit schema binding spec is invalid")
    bindings: dict[str, int] = {}
    identities = {schema_binding_spec["family_root_report_norm_id"]}
    for raw in schema_binding_spec["role_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != {"report_norm_id", "role"}
            or raw.get("role") not in _OUTPUT_ROLES
            or raw["role"] in bindings
            or type(raw.get("report_norm_id")) is not int
            or raw["report_norm_id"] <= 0
            or raw["report_norm_id"] in identities
        ):
            raise _error("customer-deposit schema role binding is invalid")
        bindings[raw["role"]] = raw["report_norm_id"]
        identities.add(raw["report_norm_id"])
    if set(bindings) != _OUTPUT_ROLES:
        raise _error("customer-deposit schema binding frontier is incomplete")
    return {
        "aliases_by_source_role": aliases_by_source_role,
        "anchor_alias_groups": [
            [aliases_by_source_role[role] for role in ("NO_TERM", "TERM", "DEDICATED")],
            [aliases_by_source_role[role] for role in ("NO_TERM", "TERM", "ESCROW")],
        ],
        "bindings": bindings,
        "claim_boundary": CLAIM_BOUNDARY,
        "currency_aliases": compiled_currency_aliases,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "parent_shorthand_aliases": compiled_shorthand,
        "query_policy": {
            "hard_negative_aliases": canonical_clone_v1(topology["hard_negative_aliases"]),
            "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
            "reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
        },
        "schema": canonical_clone_v1(schema_binding_spec),
        "topology": topology,
        "unit_binding_by_alias": units_by_alias,
        "unit_bindings": units,
    }


def bind_gemini_json_customer_deposit_source_repairs_v1(
    compiled_specs: Any,
    source_repair_spec: Any,
) -> dict[str, Any]:
    """Bind exact PDF dash observations to one compiled Family-15 frontier."""

    if type(compiled_specs) is not dict:
        raise _error("customer-deposit compiled family frontier is invalid")
    compiled = canonical_clone_v1(compiled_specs)
    if (
        compiled.get("topology", {}).get("family_id") != FAMILY_ID
        or compiled.get("schema", {}).get("family_id") != FAMILY_ID
        or compiled.get("evaluation", {}).get("family_id") != FAMILY_ID
        or compiled.get("engine_format_version") != ENGINE_FORMAT_VERSION
        or set(compiled.get("bindings", {})) != _OUTPUT_ROLES
        or {
            item["canonical_unit"]
            for item in compiled.get("unit_bindings", [])
            if item.get("accepted") is True
        }
        != {"MILLION_VND", "VND"}
    ):
        raise _error("customer-deposit declarative family frontier is invalid")
    compiled["customer_deposit_source_repairs"] = _validate_source_repairs(
        source_repair_spec
    )
    compiled["customer_deposit_source_repair_spec_sha256"] = (
        canonical_json_sha256_v1(source_repair_spec)
    )
    compiled["customer_deposit_source_repair_adapter_format_version"] = (
        SOURCE_REPAIR_ADAPTER_FORMAT_VERSION
    )
    return compiled


def _match_alias(text: str, alias: str) -> bool:
    if text == alias or text.startswith(alias + " "):
        return True
    return len(alias.split()) >= 3 and f" {alias} " in f" {text} "


def _source_roles_for_text(
    value: Any, *, roles: Sequence[str], compiled_specs: Mapping[str, Any]
) -> list[str]:
    folded = _normalized(value)
    matches = [
        (alias, role)
        for role in roles
        for alias in compiled_specs["aliases_by_source_role"][role]
        if _match_alias(folded, alias)
    ]
    if not matches:
        return []
    maximal = [
        (alias, role)
        for alias, role in matches
        if not any(
            alias != other_alias and f" {alias} " in f" {other_alias} "
            for other_alias, _other_role in matches
        )
    ]
    return sorted({role for _alias, role in maximal})


def _currency_role_for_text(value: Any) -> str | None:
    folded = _normalized(value)
    if "ngoai te" in folded or "ngoai hoi" in folded or "vang ngoai te" in folded:
        return "FOREIGN"
    if any(
        phrase in folded
        for phrase in ("bang vnd", "bang dong viet nam", "bang tien dong", "bang dong")
    ):
        return "VND"
    return None


def _parent_role_for_currency_row(
    row: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    active_parent_role: str | None = None,
) -> tuple[str | None, bool]:
    path = row.get("hierarchy_path_exact")
    label = row.get("label_exact")
    label_folded = _normalized(label)
    # Gemini normally emits a root-to-leaf hierarchy path.  Resolve the
    # nearest explicit typed ancestor first instead of unioning the full path:
    # a child such as "tiền gửi tiết kiệm ... bằng VND" can legitimately sit
    # below a broader NO_TERM/TERM group and the union is then ambiguous.
    if type(path) is list:
        for item in reversed(path):
            folded = _normalized(item)
            if not folded or folded == label_folded:
                continue
            candidates = set(
                _source_roles_for_text(
                    folded, roles=_TYPE_SOURCE_ROLES, compiled_specs=compiled_specs
                )
            )
            if len(candidates) == 1:
                return next(iter(candidates)), False
            if len(candidates) > 1:
                if active_parent_role in candidates:
                    return active_parent_role, False
                return None, True
    if active_parent_role in _TYPE_SOURCE_ROLES:
        return active_parent_role, False
    candidates = set(
        _source_roles_for_text(label, roles=_TYPE_SOURCE_ROLES, compiled_specs=compiled_specs)
    )
    for role, aliases in compiled_specs["parent_shorthand_aliases"].items():
        if any(
            re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", label_folded)
            for alias in aliases
        ):
            candidates.add(role)
    return (next(iter(candidates)), False) if len(candidates) == 1 else (None, len(candidates) > 1)


def classify_gemini_json_customer_deposit_table_v1(
    table: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Classify one table from declared role population and typed columns."""

    if type(table) is not dict:
        raise _error("customer-deposit table is invalid")
    rows = table.get("rows")
    columns = table.get("columns")
    if type(rows) is not list or type(columns) is not list:
        raise _error("customer-deposit table axes are invalid")
    money_columns = [
        index
        for index, column in enumerate(columns)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    percent_columns = [
        index
        for index, column in enumerate(columns)
        if type(column) is dict and column.get("value_kind") == "PERCENT"
    ]
    type_hits: list[dict[str, Any]] = []
    customer_hits: list[dict[str, Any]] = []
    ambiguous_rows: list[int] = []
    root_total_ordinals: list[int] = []
    for ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        label = row.get("label_exact")
        type_roles = _source_roles_for_text(
            label, roles=_TYPE_SOURCE_ROLES, compiled_specs=compiled_specs
        )
        customer_roles = _source_roles_for_text(
            label, roles=_CUSTOMER_SOURCE_ROLES, compiled_specs=compiled_specs
        )
        if row.get("row_kind") == "TOTAL" and not type_roles and not customer_roles:
            root_total_ordinals.append(ordinal)
        if len(type_roles) > 1 or len(customer_roles) > 1:
            ambiguous_rows.append(ordinal)
        for role in type_roles:
            type_hits.append({"role": role, "row_ordinal": ordinal})
        for role in customer_roles:
            customer_hits.append({"role": role, "row_ordinal": ordinal})
    type_roles = {item["role"] for item in type_hits}
    customer_roles = {item["role"] for item in customer_hits}
    reasons = []
    component_role = None
    if ambiguous_rows:
        reasons.append("SOURCE_ROW_ROLE_MATCH_IS_AMBIGUOUS")
    if (
        {"NO_TERM", "TERM"} <= type_roles
        and type_roles & _DISTINCTIVE_TYPE_ROLES
        and len(money_columns) in {2, 3}
        and len(root_total_ordinals) == 1
    ):
        component_role = "TYPE_CURRENCY"
    elif (
        {"NO_TERM", "TERM"} <= type_roles
        and type_roles & _DISTINCTIVE_TYPE_ROLES
        and not money_columns
        and percent_columns
    ):
        component_role = "INTEREST_RATE_CONTROL"
    if (
        len(customer_roles) >= 2
        and len(money_columns) == 2
        and len(percent_columns) in {0, 2}
        and len(root_total_ordinals) == 1
    ):
        if component_role is not None:
            reasons.append("TABLE_MATCHES_MULTIPLE_CUSTOMER_DEPOSIT_COMPONENTS")
        else:
            component_role = "CUSTOMER_TYPE"
    return {
        "ambiguous_row_ordinals": ambiguous_rows,
        "component_role": component_role,
        "customer_role_hits": customer_hits,
        "money_column_ordinals": [index + 1 for index in money_columns],
        "percent_column_ordinals": [index + 1 for index in percent_columns],
        "reasons": sorted(set(reasons)),
        "root_total_ordinals": root_total_ordinals,
        "type_role_hits": type_hits,
    }


def _has_explicit_percentage_evidence(table: Mapping[str, Any]) -> bool:
    surfaces = [table.get("unit_exact")]
    columns = table.get("columns")
    if type(columns) is list:
        for column in columns:
            if type(column) is not dict:
                continue
            path = column.get("header_path_exact")
            if type(path) is list:
                surfaces.extend(path)
    rows = table.get("rows")
    value_surfaces = [
        value
        for row in (rows if type(rows) is list else [])
        if type(row) is dict
        for value in (row.get("values_exact") if type(row.get("values_exact")) is list else [])
        if value is not None
    ]
    all_values_are_percentages = bool(value_surfaces) and all(
        type(value) is str and "%" in value for value in value_surfaces
    )
    return (
        any(
            type(surface) is str and ("%" in surface or "phan tram" in _normalized(surface))
            for surface in surfaces
        )
        or all_values_are_percentages
    )


_BOUNDED_RATE_VALUE = re.compile(r"^\s*(\d{1,3}(?:[.,]\d+)?)\s*(?:-\s*(\d{1,3}(?:[.,]\d+)?))?\s*$")


def _bounded_interest_rate_range_evidence(table: Mapping[str, Any]) -> dict[str, Any] | None:
    """Recognise a rate table only when every visible cell is bounded.

    Some audited reports omit the visible interest-rate narrative from JSON
    and label the two rate columns as ``TEXT/Triệu đồng``.  A source string
    range cannot be one monetary cell, so at least one range plus an entirely
    bounded 0..100 value axis is intrinsic, fail-closed non-money evidence.
    """

    rows = table.get("rows")
    if type(rows) is not list:
        return None
    values = [
        value.strip()
        for row in rows
        if type(row) is dict
        for value in (row.get("values_exact") if type(row.get("values_exact")) is list else [])
        if type(value) is str and value.strip()
    ]
    if not values:
        return None
    saw_range = False
    range_cell_count = 0
    for value in values:
        match = _BOUNDED_RATE_VALUE.fullmatch(value)
        if match is None:
            return None
        numbers = [float(item.replace(",", ".")) for item in match.groups() if item is not None]
        if not numbers or any(number < 0 or number > 100 for number in numbers):
            return None
        saw_range = saw_range or match.group(2) is not None
        range_cell_count += int(match.group(2) is not None)
    if not saw_range:
        return None
    return {
        "range_cell_count": range_cell_count,
        "rule": "ALL_VISIBLE_TEXT_VALUES_BOUNDED_0_TO_100_WITH_AT_LEAST_ONE_RANGE",
        "value_axis_sha256": canonical_json_sha256_v1(values),
        "visible_value_count": len(values),
    }


def _surface_matches(value: Any, aliases: Sequence[str]) -> str | None:
    folded = _normalized(value)
    matches = [alias for alias in aliases if _match_alias(folded, alias)]
    if not matches:
        return None
    longest = max(map(len, matches))
    selected = sorted(alias for alias in matches if len(alias) == longest)
    return selected[0] if len(selected) == 1 else None


def _is_blank_structural_owner_row(
    row: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> bool:
    """Recognise an owner heading embedded by Gemini inside a money table.

    Some notes repeat ``18. Tiền gửi của khách hàng`` as the first table
    row.  It is structural only when every value is absent and the label,
    after removing a bounded numeric note prefix, equals a declared owner
    alias.  A valued row can therefore never disappear through this rule.
    """

    values = row.get("values_exact")
    if type(values) is not list or any(value is not None for value in values):
        return False
    folded = _normalized(row.get("label_exact"))
    without_note_prefix = re.sub(r"^[0-9]+(?:\s+[0-9]+){0,2}\s+", "", folded)
    owner_aliases = compiled_specs["query_policy"]["owner_aliases"]
    return any(without_note_prefix == alias for alias in owner_aliases)


def _page_record_axis(page_records: Any) -> list[dict[str, Any]]:
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
    if type(page_records) not in {list, tuple} or not page_records:
        raise _error("customer-deposit selected page records are absent")
    checked = []
    identity = None
    prior = None
    for raw in page_records:
        if (
            type(raw) is not dict
            or set(raw) != required
            or _DOCUMENT_ID.fullmatch(raw.get("document_id", "")) is None
            or type(raw.get("document_ordinal")) is not int
            or raw["document_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(raw.get("page_json_version_id", "")) is None
            or type(raw.get("physical_page")) is not int
            or raw["physical_page"] <= 0
            or type(raw.get("selected_page_ordinal")) is not int
            or raw["selected_page_ordinal"] <= 0
            or type(raw.get("source_logical_name")) is not str
            or not raw["source_logical_name"]
            or _SHA256.fullmatch(raw.get("source_sha256", "")) is None
            or type(raw.get("page_json")) is not dict
            or type(raw["page_json"].get("sections")) is not list
        ):
            raise _error("customer-deposit selected page record is invalid")
        current_identity = tuple(
            raw[key]
            for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (raw["selected_page_ordinal"], raw["physical_page"])
        if identity is None:
            identity = current_identity
        elif identity != current_identity:
            raise _error("customer-deposit selected pages cross document identity")
        if prior is not None and position <= prior:
            raise _error("customer-deposit selected pages are not in source order")
        prior = position
        checked.append(canonical_clone_v1(raw))
    return checked


def _region(
    record: Mapping[str, Any],
    section_id: str,
    table_id: str,
    component_role: str,
    fragment_ordinal: int,
    *,
    row_start_ordinal: int | None = None,
    row_end_ordinal: int | None = None,
    fragment_layout: str | None = None,
) -> dict[str, Any]:
    material = {
        "component_role": component_role,
        "document_id": record["document_id"],
        "document_ordinal": record["document_ordinal"],
        "fragment_ordinal": fragment_ordinal,
        "page_json_version_id": record["page_json_version_id"],
        "physical_page": record["physical_page"],
        "section_id": section_id,
        "selected_page_ordinal": record["selected_page_ordinal"],
        "source_logical_name": record["source_logical_name"],
        "source_sha256": record["source_sha256"],
        "table_id": table_id,
    }
    if row_start_ordinal is not None or row_end_ordinal is not None or fragment_layout is not None:
        material.update(
            {
                "fragment_layout": fragment_layout,
                "row_end_ordinal": row_end_ordinal,
                "row_start_ordinal": row_start_ordinal,
            }
        )
    return material


def _table_fragment(
    item: Mapping[str, Any],
    *,
    row_start_ordinal: int,
    row_end_ordinal: int,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    table = item["table"]
    rows = table.get("rows")
    if type(rows) is not list or not 1 <= row_start_ordinal <= row_end_ordinal <= len(rows):
        raise _error("customer-deposit table fragment boundary is invalid")
    sliced = canonical_clone_v1(table)
    sliced["rows"] = canonical_clone_v1(rows[row_start_ordinal - 1 : row_end_ordinal])
    return {
        **{key: item[key] for key in ("position", "record", "section_id", "table_id")},
        "classification": classify_gemini_json_customer_deposit_table_v1(
            sliced, compiled_specs=compiled_specs
        ),
        "full_table": row_start_ordinal == 1 and row_end_ordinal == len(rows),
        "row_end_ordinal": row_end_ordinal,
        "row_start_ordinal": row_start_ordinal,
        "table": sliced,
    }


def _logical_fragments_for_table(
    item: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Return full table or exact TOTAL-bounded slices for mixed presentations."""

    rows = item["table"].get("rows")
    if type(rows) is not list or not rows:
        return []
    classification = item["classification"]
    if classification["component_role"] is not None:
        return [
            _table_fragment(
                item,
                row_start_ordinal=1,
                row_end_ordinal=len(rows),
                compiled_specs=compiled_specs,
            )
        ]
    total_ordinals = [
        ordinal
        for ordinal, row in enumerate(rows, start=1)
        if type(row) is dict and row.get("row_kind") == "TOTAL"
    ]
    if len(total_ordinals) <= 1:
        return [
            _table_fragment(
                item,
                row_start_ordinal=1,
                row_end_ordinal=len(rows),
                compiled_specs=compiled_specs,
            )
        ]
    fragments = []
    start = 1
    for end in total_ordinals:
        fragment = _table_fragment(
            item,
            row_start_ordinal=start,
            row_end_ordinal=end,
            compiled_specs=compiled_specs,
        )
        if (
            fragment["classification"]["type_role_hits"]
            or fragment["classification"]["customer_role_hits"]
        ):
            fragments.append(fragment)
        start = end + 1
    if start <= len(rows):
        fragment = _table_fragment(
            item,
            row_start_ordinal=start,
            row_end_ordinal=len(rows),
            compiled_specs=compiled_specs,
        )
        if (
            fragment["classification"]["type_role_hits"]
            or fragment["classification"]["customer_role_hits"]
        ):
            fragments.append(fragment)
    return fragments


def _merge_row_fragments(fragments: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not fragments:
        raise _error("customer-deposit logical row fragment axis is empty")
    first = fragments[0]["table"]
    merged = canonical_clone_v1(first)
    merged["rows"] = [
        canonical_clone_v1(row)
        for fragment in fragments
        for row in fragment["table"].get("rows", [])
    ]
    # Continuation pages commonly omit repeated headers/units.  The first
    # explicit surface is inherited only inside the authenticated fragment
    # group; conflicting explicit evidence is rejected by the join helper.
    for field in ("columns", "unit_exact"):
        if field == "columns":
            continue
        if merged.get(field) is None:
            merged[field] = next(
                (
                    fragment["table"].get(field)
                    for fragment in fragments
                    if fragment["table"].get(field) is not None
                ),
                None,
            )
    merged["continuation"] = "NONE"
    return merged


def _fragment_join_is_authenticated(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
    *,
    markers: Sequence[Mapping[str, Any]],
) -> bool:
    same_table = (
        first["record"]["page_json_version_id"] == second["record"]["page_json_version_id"]
        and first["section_id"] == second["section_id"]
        and first["table_id"] == second["table_id"]
    )
    if same_table:
        return first["row_end_ordinal"] + 1 == second["row_start_ordinal"]
    next_page = (
        second["record"]["selected_page_ordinal"] == first["record"]["selected_page_ordinal"] + 1
        and second["record"]["physical_page"] == first["record"]["physical_page"] + 1
    )
    explicit_continuation = (
        first["table"].get("continuation") == "CONTINUES_ON_NEXT_PAGE"
        or second["table"].get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
    )
    if not next_page or not explicit_continuation:
        return False
    if any(
        marker["kind"] in {"RESET", "HARD_NEGATIVE"}
        and first["position"] < marker["position"] < second["position"]
        for marker in markers
    ):
        return False
    first_columns = first["classification"]["money_column_ordinals"]
    second_columns = second["classification"]["money_column_ordinals"]
    if len(first_columns) != 2 or len(second_columns) != 2:
        return False
    first_period = _two_period_axis(first["table"])
    second_period = _two_period_axis(second["table"])
    if not first_period["reasons"] and not second_period["reasons"]:
        if first_period.get("signatures") != second_period.get("signatures"):
            return False
    elif not first_period["reasons"] and second_period.get("signatures") not in (
        None,
        [None, None],
    ):
        # An incomplete continuation is allowed only when it carries no
        # competing period assertion at all.
        return False
    first_unit = _normalized(first["table"].get("unit_exact"))
    second_unit = _normalized(second["table"].get("unit_exact"))
    return not (first_unit and second_unit and first_unit != second_unit)


def _component_candidate(
    fragments: Sequence[Mapping[str, Any]],
    *,
    component_role: str,
    compiled_specs: Mapping[str, Any],
    fragment_layout: str,
) -> dict[str, Any] | None:
    merged = _merge_row_fragments(fragments)
    classification = classify_gemini_json_customer_deposit_table_v1(
        merged, compiled_specs=compiled_specs
    )
    if classification["component_role"] != component_role:
        return None
    if component_role == "TYPE_CURRENCY" and any(
        fragment["classification"]["customer_role_hits"] for fragment in fragments
    ):
        return None
    if component_role == "CUSTOMER_TYPE" and any(
        fragment["classification"]["type_role_hits"] for fragment in fragments
    ):
        return None
    return {
        "classification": classification,
        "fragment_layout": fragment_layout,
        "fragments": list(fragments),
        "position": fragments[0]["position"],
        "end_position": fragments[-1]["position"],
        "record": fragments[0]["record"],
        "section_id": fragments[0]["section_id"],
        "table": merged,
        "table_id": fragments[0]["table_id"],
    }


def coalesce_gemini_json_customer_deposit_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select one exhaustive type cluster and optional owner-bound customer view."""

    pages = _page_record_axis(page_records)
    raw_tables: list[dict[str, Any]] = []
    declared_role_tables: list[dict[str, Any]] = []
    markers: list[dict[str, Any]] = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if type(section) is not dict:
                continue
            section_id = f"s{section_ordinal}"
            section_surfaces = [("SECTION_TITLE", section.get("title_exact"))]
            narratives = section.get("narratives_exact")
            if type(narratives) is list:
                section_surfaces.extend(
                    (f"SECTION_NARRATIVE:{ordinal}", value)
                    for ordinal, value in enumerate(narratives, start=1)
                )
            for source_kind, value in section_surfaces:
                for marker_kind, aliases in (
                    ("OWNER", compiled_specs["query_policy"]["owner_aliases"]),
                    ("RESET", compiled_specs["query_policy"]["reset_aliases"]),
                    ("HARD_NEGATIVE", compiled_specs["query_policy"]["hard_negative_aliases"]),
                ):
                    alias = _surface_matches(value, aliases)
                    if alias is not None:
                        markers.append(
                            {
                                "alias": alias,
                                "kind": marker_kind,
                                "position": [record["selected_page_ordinal"], section_ordinal, 0],
                                "section_id": section_id,
                                "source_exact": value,
                                "source_kind": source_kind,
                                "table_id": None,
                            }
                        )
            section_tables = section.get("tables")
            if type(section_tables) is not list:
                continue
            for table_ordinal, table in enumerate(section_tables, start=1):
                if type(table) is not dict:
                    continue
                table_id = f"t{table_ordinal}"
                classification = classify_gemini_json_customer_deposit_table_v1(
                    table, compiled_specs=compiled_specs
                )
                position = [record["selected_page_ordinal"], section_ordinal, table_ordinal]
                title = table.get("title_exact")
                for marker_kind, aliases in (
                    ("OWNER", compiled_specs["query_policy"]["owner_aliases"]),
                    ("RESET", compiled_specs["query_policy"]["reset_aliases"]),
                    ("HARD_NEGATIVE", compiled_specs["query_policy"]["hard_negative_aliases"]),
                ):
                    alias = _surface_matches(title, aliases)
                    if alias is not None:
                        markers.append(
                            {
                                "alias": alias,
                                "kind": marker_kind,
                                "position": position,
                                "section_id": section_id,
                                "source_exact": title,
                                "source_kind": "TABLE_TITLE",
                                "table_id": table_id,
                            }
                        )
                item = {
                    "classification": classification,
                    "position": position,
                    "record": record,
                    "section_id": section_id,
                    "table": table,
                    "table_id": table_id,
                }
                raw_tables.append(item)
                if classification["type_role_hits"] or classification["customer_role_hits"]:
                    declared_role_tables.append(item)

    fragment_source_tables = [
        item
        for item in raw_tables
        if item["classification"]["type_role_hits"]
        or item["classification"]["customer_role_hits"]
        or (
            item["table"].get("continuation")
            in {"CONTINUES_ON_NEXT_PAGE", "CONTINUES_FROM_PREVIOUS_PAGE"}
            and len(item["classification"]["money_column_ordinals"]) == 2
        )
    ]
    logical_fragments = [
        fragment
        for item in fragment_source_tables
        for fragment in _logical_fragments_for_table(item, compiled_specs=compiled_specs)
    ]

    def order_key(fragment: Mapping[str, Any]) -> tuple[int, int, int, int]:
        return (*fragment["position"], fragment["row_start_ordinal"])

    def nearest_boundary(position: Sequence[int]) -> dict[str, Any] | None:
        prior = [
            marker
            for marker in markers
            if marker["position"] <= list(position)
            and marker["kind"] in {"OWNER", "RESET", "HARD_NEGATIVE"}
        ]
        local_structural_owners = [
            marker
            for marker in prior
            if marker["kind"] == "OWNER"
            and marker["position"][:2] == list(position)[:2]
            and marker["source_kind"] in {"SECTION_TITLE", "TABLE_TITLE"}
        ]
        if (
            local_structural_owners
            and prior
            and prior[-1]["kind"] == "HARD_NEGATIVE"
            and _normalized(prior[-1]["alias"]).startswith("muc lai suat")
        ):
            return local_structural_owners[-1]
        return prior[-1] if prior else None

    def embedded_owner(fragment: Mapping[str, Any]) -> dict[str, Any] | None:
        for row_offset, row in enumerate(fragment["table"].get("rows", [])):
            if type(row) is not dict:
                continue
            alias = _surface_matches(
                row.get("label_exact"), compiled_specs["query_policy"]["owner_aliases"]
            )
            if alias is not None:
                return {
                    "alias": alias,
                    "kind": "OWNER",
                    "position": [*fragment["position"], fragment["row_start_ordinal"] + row_offset],
                    "section_id": fragment["section_id"],
                    "source_exact": row.get("label_exact"),
                    "source_kind": "TABLE_ROW_LABEL",
                    "table_id": fragment["table_id"],
                }
        return None

    def candidate_owner(candidate: Mapping[str, Any]) -> dict[str, Any] | None:
        return next(
            (
                receipt
                for fragment in candidate["fragments"]
                if (receipt := embedded_owner(fragment)) is not None
            ),
            nearest_boundary(candidate["position"]),
        )

    def prune_strict_subsets(candidates: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        axes = [
            {
                (
                    fragment["record"]["page_json_version_id"],
                    fragment["section_id"],
                    fragment["table_id"],
                    fragment["row_start_ordinal"],
                    fragment["row_end_ordinal"],
                )
                for fragment in candidate["fragments"]
            }
            for candidate in candidates
        ]
        return [
            candidate
            for ordinal, candidate in enumerate(candidates)
            if not any(
                axes[ordinal] < other for index, other in enumerate(axes) if index != ordinal
            )
        ]

    type_candidates: list[dict[str, Any]] = []
    for fragment in logical_fragments:
        if (
            fragment["classification"]["component_role"] == "TYPE_CURRENCY"
            and len(fragment["classification"]["money_column_ordinals"]) == 2
        ):
            candidate = _component_candidate(
                [fragment],
                component_role="TYPE_CURRENCY",
                compiled_specs=compiled_specs,
                fragment_layout=("LEGACY" if fragment["full_table"] else "ROW_CONTINUATION"),
            )
            if candidate is not None:
                type_candidates.append(candidate)
    for first, second in zip(logical_fragments, logical_fragments[1:], strict=False):
        if not _fragment_join_is_authenticated(first, second, markers=markers):
            continue
        candidate = _component_candidate(
            [first, second],
            component_role="TYPE_CURRENCY",
            compiled_specs=compiled_specs,
            fragment_layout="ROW_CONTINUATION",
        )
        if candidate is not None:
            type_candidates.append(candidate)

    stacked_fragments = [
        fragment
        for fragment in logical_fragments
        if fragment["full_table"]
        and fragment["classification"]["component_role"] == "TYPE_CURRENCY"
        and len(fragment["classification"]["money_column_ordinals"]) == 3
    ]
    if len(stacked_fragments) == 2:
        first, second = stacked_fragments
        same_page_section = (
            first["record"]["page_json_version_id"] == second["record"]["page_json_version_id"]
            and first["section_id"] == second["section_id"]
        )
        adjacent_continuation = (
            second["record"]["selected_page_ordinal"]
            == first["record"]["selected_page_ordinal"] + 1
            and second["record"]["physical_page"] == first["record"]["physical_page"] + 1
            and second["table"].get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
            and not any(
                marker["kind"] in {"RESET", "HARD_NEGATIVE"}
                and first["position"] < marker["position"] < second["position"]
                for marker in markers
            )
        )
        same_role_population = {
            hit["role"] for hit in first["classification"]["type_role_hits"]
        } == {hit["role"] for hit in second["classification"]["type_role_hits"]}
        if (same_page_section or adjacent_continuation) and same_role_population:
            type_candidates.append(
                {
                    "classification": {"reasons": []},
                    "end_position": second["position"],
                    "fragment_layout": "STACKED_PERIOD",
                    "fragments": [first, second],
                    "position": first["position"],
                    "record": first["record"],
                    "section_id": first["section_id"],
                    "table": None,
                    "table_id": first["table_id"],
                }
            )

    # Deduplicate the one-fragment and composed candidate projections.
    candidate_by_axis = {}
    for candidate in type_candidates:
        key = tuple(
            (
                fragment["record"]["page_json_version_id"],
                fragment["section_id"],
                fragment["table_id"],
                fragment["row_start_ordinal"],
                fragment["row_end_ordinal"],
            )
            for fragment in candidate["fragments"]
        )
        candidate_by_axis[key] = candidate
    type_candidates = prune_strict_subsets(list(candidate_by_axis.values()))

    reasons: list[str] = []
    explicit_owner_candidates = [
        candidate
        for candidate in type_candidates
        if (candidate_owner(candidate) or {}).get("kind") == "OWNER"
    ]
    eligible_candidates = explicit_owner_candidates or type_candidates
    selected_type = eligible_candidates[0] if len(eligible_candidates) == 1 else None
    owner_bound_type_fragment = any(
        fragment["classification"]["type_role_hits"]
        and (
            embedded_owner(fragment) is not None
            or (nearest_boundary(fragment["position"]) or {}).get("kind") == "OWNER"
        )
        for fragment in logical_fragments
    )
    if selected_type is None:
        if eligible_candidates:
            reasons.append("TYPE_CURRENCY_COMPONENT_NOT_EXACTLY_ONE_LAYOUT_CLUSTER")
        elif owner_bound_type_fragment:
            reasons.append("OWNER_BOUND_TYPE_COMPONENT_INCOMPLETE")
        else:
            reasons.append("NO_DISTINCTIVE_TYPE_CURRENCY_COMPONENT")

    owner = None
    if selected_type:
        first_position = selected_type["position"]
        boundary = candidate_owner(selected_type)
        if boundary is not None and boundary["kind"] == "OWNER":
            owner = boundary
        elif boundary is not None:
            reasons.append("IMPLIED_OWNER_BLOCKED_BY_RESET_OR_HARD_NEGATIVE")
        else:
            owner = {
                "alias": None,
                "kind": "IMPLIED_OWNER",
                "position": first_position,
                "section_id": selected_type["section_id"],
                "source_exact": None,
                "source_kind": "UNIQUE_DISTINCTIVE_TYPE_ROLE_POPULATION",
                "table_id": selected_type["table_id"],
            }

    customer_candidates: list[dict[str, Any]] = []
    for fragment in logical_fragments:
        if fragment["classification"]["component_role"] == "CUSTOMER_TYPE":
            candidate = _component_candidate(
                [fragment],
                component_role="CUSTOMER_TYPE",
                compiled_specs=compiled_specs,
                fragment_layout=("LEGACY" if fragment["full_table"] else "ROW_CONTINUATION"),
            )
            if candidate is not None:
                customer_candidates.append(candidate)
    for first, second in zip(logical_fragments, logical_fragments[1:], strict=False):
        if not _fragment_join_is_authenticated(first, second, markers=markers):
            continue
        candidate = _component_candidate(
            [first, second],
            component_role="CUSTOMER_TYPE",
            compiled_specs=compiled_specs,
            fragment_layout="ROW_CONTINUATION",
        )
        if candidate is not None:
            customer_candidates.append(candidate)
    customer_by_axis = {}
    for candidate in customer_candidates:
        key = tuple(
            (
                fragment["record"]["page_json_version_id"],
                fragment["section_id"],
                fragment["table_id"],
                fragment["row_start_ordinal"],
                fragment["row_end_ordinal"],
            )
            for fragment in candidate["fragments"]
        )
        customer_by_axis[key] = candidate
    customer_candidates = prune_strict_subsets(list(customer_by_axis.values()))

    selected_customer = None
    if selected_type:
        last_type = selected_type["fragments"][-1]
        attachable = []
        last_key = order_key(last_type)
        for item in customer_candidates:
            first_customer = item["fragments"][0]
            same_page_after = (
                first_customer["record"]["page_json_version_id"]
                == last_type["record"]["page_json_version_id"]
                and order_key(first_customer) > last_key
            )
            next_page = (
                first_customer["record"]["physical_page"]
                == last_type["record"]["physical_page"] + 1
            )
            explicit_customer_continuation = (
                first_customer["table"].get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
                or last_type["table"].get("continuation") == "CONTINUES_ON_NEXT_PAGE"
                or (nearest_boundary(first_customer["position"]) or {}).get("kind") == "OWNER"
            )
            if same_page_after or (next_page and explicit_customer_continuation):
                intervening = [
                    marker
                    for marker in markers
                    if last_type["position"] < marker["position"] < first_customer["position"]
                    and marker["kind"] in {"RESET", "HARD_NEGATIVE"}
                ]
                if not intervening:
                    attachable.append(item)
        if len(attachable) == 1:
            selected_customer = attachable[0]
        elif len(attachable) > 1:
            reasons.append("CUSTOMER_TYPE_VIEW_NOT_UNIQUE_WITHIN_OWNER_FENCE")
    selected_components = [
        *([] if selected_type is None else [selected_type]),
        *([] if selected_customer is None else [selected_customer]),
    ]
    selected_classification_reasons = sorted(
        {reason for item in selected_components for reason in item["classification"]["reasons"]}
    )
    if selected_classification_reasons:
        # The evaluator deliberately rejects any fragment whose row-role
        # classification is ambiguous.  Preserve that same gate here so the
        # indexed query emits an UNRESOLVED disposition instead of advertising
        # a READY cluster that can only crash during candidate construction.
        reasons.extend(selected_classification_reasons)
        reasons.append("SELECTED_COMPONENT_CLASSIFICATION_UNRESOLVED")
    regions = []
    if selected_type is not None:
        for ordinal, item in enumerate(selected_type["fragments"], start=1):
            extended = selected_type["fragment_layout"] == "ROW_CONTINUATION"
            regions.append(
                _region(
                    item["record"],
                    item["section_id"],
                    item["table_id"],
                    "TYPE_CURRENCY",
                    ordinal,
                    row_start_ordinal=item["row_start_ordinal"] if extended else None,
                    row_end_ordinal=item["row_end_ordinal"] if extended else None,
                    fragment_layout="ROW_CONTINUATION" if extended else None,
                )
            )
    if selected_customer is not None:
        for ordinal, item in enumerate(selected_customer["fragments"], start=1):
            extended = selected_customer["fragment_layout"] == "ROW_CONTINUATION"
            regions.append(
                _region(
                    item["record"],
                    item["section_id"],
                    item["table_id"],
                    "CUSTOMER_TYPE",
                    ordinal,
                    row_start_ordinal=item["row_start_ordinal"] if extended else None,
                    row_end_ordinal=item["row_end_ordinal"] if extended else None,
                    fragment_layout="ROW_CONTINUATION" if extended else None,
                )
            )
    selected_table_keys = {
        (
            fragment["record"]["page_json_version_id"],
            fragment["section_id"],
            fragment["table_id"],
        )
        for item in selected_components
        for fragment in item["fragments"]
    }
    selected_problem_table_keys = {
        (
            fragment["record"]["page_json_version_id"],
            fragment["section_id"],
            fragment["table_id"],
        )
        for item in selected_components
        if item["classification"]["reasons"]
        for fragment in item["fragments"]
    }
    fence_start = (
        owner["position"]
        if owner is not None
        else selected_type["position"]
        if selected_type
        else None
    )
    fence_end = None
    if selected_type:
        last_selected = (
            selected_customer["fragments"][-1]
            if selected_customer is not None
            else selected_type["fragments"][-1]
        )
        boundary_markers = [
            marker
            for marker in markers
            if marker["position"] > last_selected["position"]
            and marker["kind"] in {"OWNER", "RESET", "HARD_NEGATIVE"}
        ]
        if boundary_markers:
            fence_end = min(marker["position"] for marker in boundary_markers)

    def explicit_interest_rate_marker(item: Mapping[str, Any]) -> dict[str, Any] | None:
        if (
            item["classification"]["money_column_ordinals"]
            or item["classification"]["percent_column_ordinals"]
        ):
            return None
        candidates = [
            marker
            for marker in markers
            if marker["kind"] == "HARD_NEGATIVE"
            and _normalized(marker["alias"]).startswith("muc lai suat")
            and marker["section_id"] == item["section_id"]
            and marker["position"] <= item["position"]
            and (marker["table_id"] is None or marker["table_id"] == item["table_id"])
        ]
        return max(candidates, key=lambda marker: marker["position"]) if candidates else None

    declared_role_inventory = []
    for item in declared_role_tables:
        key = (
            item["record"]["page_json_version_id"],
            item["section_id"],
            item["table_id"],
        )
        inside_fence = (
            fence_start is not None
            and item["position"] >= fence_start
            and (fence_end is None or item["position"] < fence_end)
            and item["record"]["selected_page_ordinal"]
            <= (
                selected_customer["fragments"][-1]["record"]["selected_page_ordinal"]
                if selected_customer is not None
                else selected_type["fragments"][-1]["record"]["selected_page_ordinal"] + 1
                if selected_type is not None
                else 0
            )
        )
        rate_range_evidence = (
            None
            if item["classification"]["money_column_ordinals"]
            or item["classification"]["percent_column_ordinals"]
            else _bounded_interest_rate_range_evidence(item["table"])
        )
        rate_marker = explicit_interest_rate_marker(item)
        exclusion_evidence = None
        if key in selected_problem_table_keys:
            disposition = "SELECTED_COMPONENT_CLASSIFICATION_UNRESOLVED"
        elif key in selected_table_keys:
            disposition = "SELECTED_FAMILY_COMPONENT"
        elif (
            item["classification"]["component_role"] == "INTEREST_RATE_CONTROL"
            or (
                not item["classification"]["money_column_ordinals"]
                and item["classification"]["percent_column_ordinals"]
            )
            or _has_explicit_percentage_evidence(item["table"])
            or rate_range_evidence is not None
        ):
            disposition = "EXCLUDED_TYPED_NON_MONEY_CONTROL"
            if rate_range_evidence is not None:
                exclusion_evidence = {
                    "rate_range_evidence": rate_range_evidence,
                    "rule": "TEXT_COLUMNS_WITH_INTRINSIC_BOUNDED_RATE_RANGE_VALUES",
                }
                if rate_marker is not None:
                    exclusion_evidence["interest_rate_marker"] = canonical_clone_v1(rate_marker)
        elif inside_fence:
            disposition = "UNCONSUMED_DECLARED_ROLE_TABLE_WITHIN_OWNER_FENCE"
            reasons.append(disposition)
        else:
            disposition = "OUTSIDE_SELECTED_OWNER_FENCE"
        inventory_item = {
            "classification": item["classification"],
            "disposition": disposition,
            "page_json_version_id": item["record"]["page_json_version_id"],
            "physical_page": item["record"]["physical_page"],
            "position": item["position"],
            "section_id": item["section_id"],
            "table_id": item["table_id"],
        }
        if exclusion_evidence is not None:
            inventory_item["exclusion_evidence"] = exclusion_evidence
        declared_role_inventory.append(inventory_item)
    material = {
        "component_regions": regions if not reasons else [],
        "declared_role_table_inventory": declared_role_inventory,
        "document_id": pages[0]["document_id"],
        "document_ordinal": pages[0]["document_ordinal"],
        "owner_receipt": owner,
        "reasons": sorted(set(reasons)),
        "source_logical_name": pages[0]["source_logical_name"],
        "source_sha256": pages[0]["source_sha256"],
        "status": READY
        if regions and not reasons
        else (UNRESOLVED if type_candidates or owner_bound_type_fragment else NOT_OBSERVED),
    }
    return {
        **material,
        "cluster_id": "gjfcdfcv1:cluster:" + canonical_json_sha256_v1(material),
    }


def _source_table(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("customer-deposit page has no section axis")
    if _SECTION_ID.fullmatch(section_id) is None:
        raise _error("customer-deposit section identity is invalid")
    section_index = int(section_id[1:]) - 1
    if not 0 <= section_index < len(sections) or type(sections[section_index]) is not dict:
        raise _error("customer-deposit section identity is out of range")
    section = sections[section_index]
    tables = section.get("tables")
    if type(tables) is not list or _TABLE_ID.fullmatch(table_id) is None:
        raise _error("customer-deposit table axis is invalid")
    table_index = int(table_id[1:]) - 1
    if not 0 <= table_index < len(tables) or type(tables[table_index]) is not dict:
        raise _error("customer-deposit table identity is out of range")
    return section, tables[table_index]


def _source_table_for_region(
    page_json: Mapping[str, Any], *, region: Mapping[str, Any]
) -> dict[str, Any]:
    _section, table = _source_table(
        page_json,
        section_id=region["section_id"],
        table_id=region["table_id"],
    )
    if "fragment_layout" not in region:
        return table
    rows = table.get("rows")
    start = region["row_start_ordinal"]
    end = region["row_end_ordinal"]
    if type(rows) is not list or not 1 <= start <= end <= len(rows):
        raise _error("customer-deposit bound row fragment is outside the source table")
    fragment = canonical_clone_v1(table)
    fragment["rows"] = canonical_clone_v1(rows[start - 1 : end])
    return fragment


def _repair_is_inside_region(
    repair: Mapping[str, Any], region: Mapping[str, Any]
) -> bool:
    locator = repair["locator"]
    if not all(
        region.get(field) == locator[field]
        for field in (
            "page_json_version_id",
            "physical_page",
            "section_id",
            "table_id",
        )
    ):
        return False
    return (
        "fragment_layout" not in region
        or region["row_start_ordinal"]
        <= locator["row_ordinal"]
        <= region["row_end_ordinal"]
    )


def _apply_authenticated_source_repairs(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Overlay only registered null cells whose selected component contains them."""

    pages = {
        page_json_version_id: canonical_clone_v1(page_json)
        for page_json_version_id, page_json in page_json_by_version.items()
    }
    if not regions:
        return pages, []
    identities = {
        (region.get("source_logical_name"), region.get("source_sha256"))
        for region in regions
    }
    if len(identities) != 1:
        raise _error("customer-deposit repair candidate source identity is ambiguous")
    source_logical_name, source_sha256 = next(iter(identities))
    applicable = [
        canonical_clone_v1(repair)
        for repair in compiled_specs.get("customer_deposit_source_repairs", [])
        if repair["source"]["source_sha256"] == source_sha256
        and any(_repair_is_inside_region(repair, region) for region in regions)
    ]
    for repair in applicable:
        source = repair["source"]
        locator = repair["locator"]
        if source["source_logical_name"] != source_logical_name:
            raise _error("customer-deposit repair logical source identity drifted")
        matching_regions = [
            region
            for region in regions
            if _repair_is_inside_region(repair, region)
        ]
        if len(matching_regions) != 1:
            raise _error("customer-deposit repair is outside one selected component fragment")
        page = pages.get(locator["page_json_version_id"])
        if page is None:
            raise _error("customer-deposit repair page is outside the selected document")
        _section, table = _source_table(
            page,
            section_id=locator["section_id"],
            table_id=locator["table_id"],
        )
        rows = table.get("rows")
        if type(rows) is not list or locator["row_ordinal"] > len(rows):
            raise _error("customer-deposit repair row is outside its selected table")
        row = rows[locator["row_ordinal"] - 1]
        values = row.get("values_exact") if type(row) is dict else None
        if (
            type(values) is not list
            or locator["column_ordinal"] > len(values)
            or values[locator["column_ordinal"] - 1] is not repair["before_exact"]
        ):
            raise _error("customer-deposit repair cell before-image drifted")
        values[locator["column_ordinal"] - 1] = repair["after_exact"]
    return pages, applicable


def _fragment_row_source_axis(
    tables: Sequence[Mapping[str, Any]], regions: Sequence[Mapping[str, Any]]
) -> list[tuple[Mapping[str, Any], int]]:
    if len(tables) != len(regions):
        raise _error("customer-deposit fragment/source axes differ")
    return [
        (region, region.get("row_start_ordinal", 1) + local_ordinal - 1)
        for table, region in zip(tables, regions, strict=True)
        for local_ordinal, _row in enumerate(table.get("rows", []), start=1)
    ]


def _region_axis(regions: Any) -> list[dict[str, Any]]:
    base_fields = {
        "component_role",
        "document_id",
        "document_ordinal",
        "fragment_ordinal",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "selected_page_ordinal",
        "source_logical_name",
        "source_sha256",
        "table_id",
    }
    continuation_fields = base_fields | {
        "fragment_layout",
        "row_end_ordinal",
        "row_start_ordinal",
    }
    if type(regions) not in {list, tuple} or not 1 <= len(regions) <= 4:
        raise _error("customer-deposit region axis cardinality is invalid")
    checked = []
    identity = None
    prior = None
    type_fragments = 0
    customer_fragments = 0
    for raw in regions:
        if (
            type(raw) is not dict
            or frozenset(raw) not in {frozenset(base_fields), frozenset(continuation_fields)}
            or raw.get("component_role") not in {"TYPE_CURRENCY", "CUSTOMER_TYPE"}
            or _DOCUMENT_ID.fullmatch(raw.get("document_id", "")) is None
            or type(raw.get("document_ordinal")) is not int
            or raw["document_ordinal"] <= 0
            or type(raw.get("fragment_ordinal")) is not int
            or raw["fragment_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(raw.get("page_json_version_id", "")) is None
            or type(raw.get("physical_page")) is not int
            or raw["physical_page"] <= 0
            or type(raw.get("selected_page_ordinal")) is not int
            or raw["selected_page_ordinal"] <= 0
            or _SECTION_ID.fullmatch(raw.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(raw.get("table_id", "")) is None
            or type(raw.get("source_logical_name")) is not str
            or not raw["source_logical_name"]
            or _SHA256.fullmatch(raw.get("source_sha256", "")) is None
        ):
            raise _error("customer-deposit region is invalid")
        extended = set(raw) == continuation_fields
        if extended and (
            raw.get("fragment_layout") != "ROW_CONTINUATION"
            or type(raw.get("row_start_ordinal")) is not int
            or type(raw.get("row_end_ordinal")) is not int
            or not 1 <= raw["row_start_ordinal"] <= raw["row_end_ordinal"]
        ):
            raise _error("customer-deposit row-continuation region is invalid")
        current_identity = tuple(
            raw[key]
            for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (
            raw["selected_page_ordinal"],
            int(raw["section_id"][1:]),
            int(raw["table_id"][1:]),
            raw.get("row_start_ordinal", 0),
        )
        if identity is None:
            identity = current_identity
        elif identity != current_identity:
            raise _error("customer-deposit regions cross document identity")
        if prior is not None and position <= prior:
            raise _error("customer-deposit regions are not in source order")
        prior = position
        if raw["component_role"] == "TYPE_CURRENCY":
            type_fragments += 1
            if raw["fragment_ordinal"] != type_fragments or customer_fragments:
                raise _error("customer-deposit type fragment axis is invalid")
        else:
            customer_fragments += 1
            if raw["fragment_ordinal"] != customer_fragments or customer_fragments > 2:
                raise _error("customer-deposit customer-view axis is invalid")
        checked.append(canonical_clone_v1(raw))
    if type_fragments not in {1, 2}:
        raise _error("customer-deposit type layout needs one or two fragments")
    type_axis = [item for item in checked if item["component_role"] == "TYPE_CURRENCY"]
    if any("fragment_layout" in item for item in type_axis) and not all(
        item.get("fragment_layout") == "ROW_CONTINUATION" for item in type_axis
    ):
        raise _error("customer-deposit type fragment layouts are mixed")
    customer_axis = [item for item in checked if item["component_role"] == "CUSTOMER_TYPE"]
    if any("fragment_layout" in item for item in customer_axis) and not all(
        item.get("fragment_layout") == "ROW_CONTINUATION" for item in customer_axis
    ):
        raise _error("customer-deposit customer fragment layouts are mixed")
    return checked


def build_gemini_json_customer_deposit_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    checked = _region_axis(regions)
    first = checked[0]
    material = {
        "document_id": first["document_id"],
        "exact_fragment_count": len(checked),
        "format_version": "GEMINI_JSON_CUSTOMER_DEPOSIT_REGION_QUERY_RECEIPT_V1",
        "ordered_fragment_axis_sha256": canonical_json_sha256_v1(checked),
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
    }
    return {
        **material,
        "query_receipt_id": "gjfcdrqrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _semantic_period_roles(value: str) -> list[str]:
    folded = _normalized(value)
    roles = []
    if " so du cuoi quy " in f" {folded} " or any(
        alias == folded or f" {alias} " in f" {folded} " for alias in _CURRENT_PERIOD_ALIASES
    ):
        roles.append("CURRENT_PERIOD")
    if any(
        alias == folded or f" {alias} " in f" {folded} " for alias in _COMPARATIVE_PERIOD_ALIASES
    ):
        roles.append("COMPARATIVE_PERIOD")
    return roles


def _two_period_axis(table: Mapping[str, Any]) -> dict[str, Any]:
    columns = table.get("columns")
    if type(columns) is not list:
        return {"complete": False, "reasons": ["COLUMN_AXIS_INVALID"]}
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if len(money_ordinals) != 2:
        return {
            "complete": False,
            "money_column_ordinals": money_ordinals,
            "reasons": ["EXACTLY_TWO_MONEY_COLUMNS_REQUIRED"],
        }
    headers = [_header_text(columns[ordinal - 1]) for ordinal in money_ordinals]
    dates = [sorted(item.isoformat() for item in _header_dates(header)) for header in headers]
    semantics = [_semantic_period_roles(header) for header in headers]
    signatures: list[list[str] | None] = []
    reasons = []
    expected = ("CURRENT_PERIOD", "COMPARATIVE_PERIOD")
    for lane, (date_axis, semantic_axis) in enumerate(zip(dates, semantics, strict=True), start=1):
        if len(date_axis) > 1:
            reasons.append(
                f"MULTIPLE_DISTINCT_DATES_IN_ONE_PERIOD_HEADER:c{money_ordinals[lane - 1]}"
            )
        if len(semantic_axis) > 1:
            reasons.append(
                f"MULTIPLE_SEMANTIC_PERIOD_ROLES_IN_ONE_HEADER:c{money_ordinals[lane - 1]}"
            )
        if (
            len(date_axis) == 1
            and len(semantic_axis) == 1
            and semantic_axis[0] != expected[lane - 1]
        ):
            reasons.append(
                f"DATE_AND_SEMANTIC_PERIOD_EVIDENCE_CONFLICT:c{money_ordinals[lane - 1]}"
            )
        if len(date_axis) == 1 and len(semantic_axis) <= 1:
            signatures.append(["DATE", date_axis[0]])
        elif not date_axis and len(semantic_axis) == 1:
            signatures.append(["SEMANTIC_ALIAS", semantic_axis[0]])
        else:
            signatures.append(None)
    if all(signature is not None for signature in signatures):
        first, second = signatures
        assert first is not None and second is not None
        if first[0] != second[0]:
            reasons.append("PERIOD_SIGNATURE_KINDS_DIFFER")
        elif first[0] == "DATE" and not date.fromisoformat(first[1]) > date.fromisoformat(
            second[1]
        ):
            reasons.append("DATE_PERIOD_AXIS_IS_NOT_STRICT_CURRENT_THEN_COMPARATIVE")
        elif first != ["SEMANTIC_ALIAS", "CURRENT_PERIOD"] and first[0] == "SEMANTIC_ALIAS":
            reasons.append("SEMANTIC_PERIOD_AXIS_IS_NOT_CURRENT_COMPARATIVE")
    else:
        reasons.append("TWO_PERIOD_AXIS_INCOMPLETE")
    return {
        "complete": not reasons,
        "date_evidence_by_lane": dates,
        "headers_exact": headers,
        "money_column_ordinals": money_ordinals,
        "reasons": sorted(set(reasons)),
        "semantic_roles_by_lane": semantics,
        "signatures": signatures,
        "source": "LOCAL_MONEY_COLUMN_HEADERS",
    }


def _alias_occurrences(text: str, aliases: Sequence[str]) -> list[str]:
    occurrences = [
        (match.start(), match.end(), alias)
        for alias in aliases
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text)
    ]
    return sorted(
        {
            alias
            for start, end, alias in occurrences
            if not any(
                other_start <= start and end <= other_end and other_end - other_start > end - start
                for other_start, other_end, _other_alias in occurrences
            )
        }
    )


def _column_unit_surfaces(
    column: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> list[str]:
    """Return unit-bearing header segments after removing currency-role prefixes."""

    path = column.get("header_path_exact")
    values = [item for item in path if type(item) is str] if type(path) is list else []
    currency_aliases = sorted(
        {alias for aliases in compiled_specs["currency_aliases"].values() for alias in aliases},
        key=len,
        reverse=True,
    )
    surfaces = []
    for value in values:
        for line in value.splitlines() or [value]:
            folded = _normalized(line)
            if not folded:
                continue
            for alias in currency_aliases:
                if folded == alias:
                    folded = ""
                    break
                if folded.startswith(alias + " "):
                    folded = folded[len(alias) :].strip()
                    break
            if folded:
                surfaces.append(folded)
    return surfaces


def _document_unit_context_axis(
    page_json_by_version: Mapping[str, dict[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Build exact document-unit evidence and owner-row corroboration.

    A document may legitimately mix VND and million-VND tables, so a bare
    document majority is never enough.  In addition to the strict all-page
    consensus, retain explicit-unit rows whose label is the declared customer
    deposit owner; an otherwise unitless detail table may inherit that unit
    only when its two-period visible total and period axis match exactly.
    """

    accepted_aliases = [
        alias
        for alias, binding in compiled_specs["unit_binding_by_alias"].items()
        if binding["accepted"]
    ]
    evidence = []
    conflicts = []
    owner_row_evidence = []
    table_axis = []
    for selected_page_ordinal, (page_json_version_id, page_json) in enumerate(
        page_json_by_version.items(), start=1
    ):
        if _PAGE_VERSION.fullmatch(page_json_version_id) is None or type(page_json) is not dict:
            raise _error("customer-deposit document unit context page is invalid")
        sections = page_json.get("sections")
        if type(sections) is not list:
            raise _error("customer-deposit document unit context section axis is invalid")
        for section_ordinal, section in enumerate(sections, start=1):
            if type(section) is not dict or type(section.get("tables")) is not list:
                continue
            for table_ordinal, table in enumerate(section["tables"], start=1):
                if type(table) is not dict:
                    continue
                locator = {
                    "page_json_version_id": page_json_version_id,
                    "section_id": f"s{section_ordinal}",
                    "table_id": f"t{table_ordinal}",
                }
                period_axis = _two_period_axis(table)
                local_unit_axis = _unit_axis(
                    table,
                    compiled_specs=compiled_specs,
                    document_unit_context=None,
                )
                table_axis.append(
                    {
                        "column_count": len(table.get("columns", [])),
                        "local_unit_axis": local_unit_axis,
                        "locator": locator,
                        "money_column_ordinals": canonical_clone_v1(
                            period_axis.get("money_column_ordinals", [])
                        ),
                        "page_status": page_json.get("status"),
                        "period_axis": period_axis,
                        "selected_page_ordinal": selected_page_ordinal,
                        "table": table,
                    }
                )
                unit_exact = table.get("unit_exact")
                if type(unit_exact) is not str or not unit_exact.strip():
                    continue
                matches = _alias_occurrences(_normalized(unit_exact), accepted_aliases)
                if not matches:
                    continue
                bindings = [compiled_specs["unit_binding_by_alias"][alias] for alias in matches]
                identities = {
                    (binding["canonical_unit"], binding["magnitude_power10"])
                    for binding in bindings
                }
                if len(identities) != 1:
                    conflicts.append({**locator, "source_exact": unit_exact})
                    continue
                binding = bindings[0]
                evidence.append(
                    {
                        **locator,
                        "accepted": binding["accepted"],
                        "canonical_unit": binding["canonical_unit"],
                        "magnitude_power10": binding["magnitude_power10"],
                        "matched_aliases": matches,
                        "source_exact": unit_exact,
                        "source_kind": "TABLE_UNIT",
                    }
                )
                if binding["accepted"]:
                    money_columns = period_axis.get("money_column_ordinals", [])
                    for row_ordinal, row in enumerate(table.get("rows", []), start=1):
                        if (
                            type(row) is not dict
                            or _surface_matches(
                                row.get("label_exact"),
                                compiled_specs["query_policy"]["owner_aliases"],
                            )
                            is None
                            or not period_axis.get("complete")
                        ):
                            continue
                        try:
                            cells = _parse_cells(row, money_columns)
                        except GeminiJsonCustomerDepositFamilyV1Error:
                            continue
                        owner_row_evidence.append(
                            {
                                **locator,
                                "canonical_unit": binding["canonical_unit"],
                                "coefficients": [cell["coefficient"] for cell in cells],
                                "magnitude_power10": binding["magnitude_power10"],
                                "period_axis_complete": True,
                                "period_signatures": canonical_clone_v1(period_axis["signatures"]),
                                "row_ordinal": row_ordinal,
                                "source_exact": unit_exact,
                                "source_kind": "EXPLICIT_UNIT_CUSTOMER_DEPOSIT_OWNER_ROW",
                            }
                        )
    direct_owner_refs = {
        (
            item["page_json_version_id"],
            item["section_id"],
            item["table_id"],
            item["row_ordinal"],
        )
        for item in owner_row_evidence
    }
    for item in table_axis:
        table = item["table"]
        period_axis = item["period_axis"]
        local_unit_axis = item["local_unit_axis"]
        if not period_axis.get("complete"):
            continue
        owner_rows = [
            (row_ordinal, row)
            for row_ordinal, row in enumerate(table.get("rows", []), start=1)
            if type(row) is dict
            and _surface_matches(
                row.get("label_exact"), compiled_specs["query_policy"]["owner_aliases"]
            )
            is not None
        ]
        if not owner_rows:
            continue
        unit_source = None
        unit_carrier_locator = None
        unit_carrier_selected_page_ordinal = None
        source_kind = None
        if local_unit_axis.get("complete"):
            unit_source = local_unit_axis
            source_kind = "LOCAL_EXPLICIT_UNIT_CUSTOMER_DEPOSIT_OWNER_ROW"
        elif item["page_status"] == "PRIMARY_FINANCIAL_STATEMENT":
            carriers = [
                candidate
                for candidate in table_axis
                if candidate["selected_page_ordinal"] == item["selected_page_ordinal"] - 1
                and candidate["page_status"] == "PRIMARY_FINANCIAL_STATEMENT"
                and candidate["local_unit_axis"].get("complete")
                and len(candidate["money_column_ordinals"])
                == len(item["money_column_ordinals"])
                == 2
                and candidate["period_axis"].get("complete")
                and candidate["period_axis"].get("signatures") == period_axis.get("signatures")
            ]
            carrier_units = {
                candidate["local_unit_axis"]["canonical_unit"] for candidate in carriers
            }
            if len(carrier_units) == 1:
                unit_source = carriers[-1]["local_unit_axis"]
                unit_carrier_locator = canonical_clone_v1(carriers[-1]["locator"])
                unit_carrier_selected_page_ordinal = carriers[-1]["selected_page_ordinal"]
                source_kind = (
                    "ADJACENT_PRIMARY_STATEMENT_CONTINUATION_UNIT_CUSTOMER_DEPOSIT_OWNER_ROW"
                )
        if unit_source is None:
            continue
        canonical_unit = unit_source["canonical_unit"]
        magnitude_powers = {
            binding["magnitude_power10"]
            for binding in compiled_specs["unit_binding_by_alias"].values()
            if binding["accepted"] and binding["canonical_unit"] == canonical_unit
        }
        if len(magnitude_powers) != 1:
            continue
        for row_ordinal, row in owner_rows:
            direct_ref = (
                item["locator"]["page_json_version_id"],
                item["locator"]["section_id"],
                item["locator"]["table_id"],
                row_ordinal,
            )
            if direct_ref in direct_owner_refs:
                continue
            try:
                cells = _parse_cells(row, period_axis["money_column_ordinals"])
            except GeminiJsonCustomerDepositFamilyV1Error:
                continue
            owner_row_evidence.append(
                {
                    **item["locator"],
                    "canonical_unit": canonical_unit,
                    "coefficients": [cell["coefficient"] for cell in cells],
                    "magnitude_power10": next(iter(magnitude_powers)),
                    "period_axis_complete": True,
                    "period_signatures": canonical_clone_v1(period_axis["signatures"]),
                    "row_ordinal": row_ordinal,
                    "source_exact": canonical_clone_v1(unit_source.get("evidence", [])),
                    "source_kind": source_kind,
                    **(
                        {
                            "unit_carrier_locator": unit_carrier_locator,
                            "unit_carrier_selected_page_ordinal": (
                                unit_carrier_selected_page_ordinal
                            ),
                        }
                        if unit_carrier_locator is not None
                        else {}
                    ),
                }
            )
    identities = {
        (item["canonical_unit"], item["magnitude_power10"], item["accepted"]) for item in evidence
    }
    distinct_pages = {item["page_json_version_id"] for item in evidence}
    unique = (
        not conflicts
        and len(identities) == 1
        and len(distinct_pages) >= 2
        and next(iter(identities))[2]
    )
    canonical_unit = next(iter(identities))[0] if unique else None
    return {
        "canonical_unit": canonical_unit,
        "conflicts": conflicts,
        "distinct_page_version_count": len(distinct_pages),
        "evidence": evidence,
        "evidence_axis_sha256": canonical_json_sha256_v1(evidence),
        "owner_row_evidence": owner_row_evidence,
        "owner_row_evidence_axis_sha256": canonical_json_sha256_v1(owner_row_evidence),
        "rule": "EXPLICIT_SCALED_TABLE_UNIT_UNIQUE_ACROSS_AT_LEAST_TWO_SELECTED_PAGES",
        "status": "UNIQUE" if unique else "NOT_UNIQUE",
    }


def _unit_axis(
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    columns = table.get("columns")
    if type(columns) is not list:
        return {
            "canonical_unit": None,
            "complete": False,
            "evidence": [],
            "reasons": ["COLUMN_AXIS_INVALID"],
        }
    money_columns = [
        column for column in columns if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    aliases = list(compiled_specs["unit_binding_by_alias"])
    evidence = []
    conflicts = []
    undeclared = []

    def classify(source_kind: str, source_exact: Any, explicit: bool) -> dict[str, Any] | None:
        folded = _normalized(source_exact)
        matches = _alias_occurrences(folded, aliases)
        if matches:
            records = []
            for alias in matches:
                binding = compiled_specs["unit_binding_by_alias"][alias]
                records.append(
                    {
                        "accepted": binding["accepted"],
                        "canonical_unit": binding["canonical_unit"],
                        "matched_alias": alias,
                        "magnitude_power10": binding["magnitude_power10"],
                        "source_exact": source_exact,
                        "source_kind": source_kind,
                    }
                )
            evidence.extend(records)
            identities = {(item["canonical_unit"], item["magnitude_power10"]) for item in records}
            if len(identities) != 1:
                conflicts.append({"source_exact": source_exact, "source_kind": source_kind})
                return None
            return records[0]
        if explicit or re.search(r"\b(?:dong|vnd|usd|trieu|nghin|ty)\b", folded):
            undeclared.append({"source_exact": source_exact, "source_kind": source_kind})
        return None

    table_record = None
    if type(table.get("unit_exact")) is str and table["unit_exact"].strip():
        table_record = classify("TABLE_UNIT", table["unit_exact"], True)
    column_records = []
    for ordinal, column in enumerate(money_columns, start=1):
        surface_records = [
            classify(f"MONEY_COLUMN_HEADER:{ordinal}:{surface_ordinal}", surface, False)
            for surface_ordinal, surface in enumerate(
                _column_unit_surfaces(column, compiled_specs=compiled_specs), start=1
            )
        ]
        present = [record for record in surface_records if record is not None]
        identities = {(record["canonical_unit"], record["magnitude_power10"]) for record in present}
        if len(identities) > 1:
            conflicts.append(
                {"source_exact": _header_text(column), "source_kind": f"MONEY_COLUMN:{ordinal}"}
            )
            column_records.append(None)
        elif present:
            column_records.append(present[0])
        else:
            column_records.append(None)
    reasons = []
    if conflicts:
        reasons.append("MULTIPLE_CONFLICTING_DECLARED_MONEY_UNITS_ON_ONE_SURFACE")
    if undeclared:
        reasons.append("UNDECLARED_EXPLICIT_MONEY_UNIT")
    if any(item is not None and not item["accepted"] for item in [table_record, *column_records]):
        reasons.append("EXPLICIT_MONEY_UNIT_IS_NOT_ACCEPTED")
    canonical_unit = None
    source = None
    if table_record is not None and table_record["accepted"]:
        canonical_unit = table_record["canonical_unit"]
        source = "LOCAL_TABLE_UNIT"
        if any(
            item is not None and item["canonical_unit"] != canonical_unit for item in column_records
        ):
            reasons.append("CONFLICTING_EXPLICIT_MONEY_UNITS")
    elif column_records and all(item is not None and item["accepted"] for item in column_records):
        units = {item["canonical_unit"] for item in column_records if item is not None}
        if len(units) == 1:
            canonical_unit = next(iter(units))
            source = "LOCAL_UNIFORM_ALL_MONEY_COLUMN_UNITS"
        else:
            reasons.append("CONFLICTING_EXPLICIT_MONEY_UNITS")
    else:
        reasons.append("MONEY_UNIT_NOT_EXACTLY_RESOLVED")
    inherited_context = None
    if (
        canonical_unit is None
        and reasons == ["MONEY_UNIT_NOT_EXACTLY_RESOLVED"]
        and not evidence
        and not undeclared
        and not conflicts
        and type(document_unit_context) is dict
    ):
        period_axis = _two_period_axis(table)
        totals = [
            row
            for row in table.get("rows", [])
            if type(row) is dict and row.get("row_kind") == "TOTAL"
        ]
        target_coefficients = None
        if period_axis.get("complete") and len(totals) == 1:
            try:
                target_coefficients = [
                    cell["coefficient"]
                    for cell in _parse_cells(
                        totals[0], period_axis.get("money_column_ordinals", [])
                    )
                ]
            except GeminiJsonCustomerDepositFamilyV1Error:
                target_coefficients = None
        matches = [
            item
            for item in document_unit_context.get("owner_row_evidence", [])
            if target_coefficients is not None
            and item.get("coefficients") == target_coefficients
            and item.get("period_axis_complete") is True
        ]
        matched_units = {item["canonical_unit"] for item in matches}
        if len(matched_units) == 1:
            canonical_unit = next(iter(matched_units))
            source = "DOCUMENT_OWNER_ROW_EXACT_VALUE_PERIOD_UNIT_CORROBORATION"
            inherited_context = {
                "evidence": canonical_clone_v1(matches),
                "evidence_axis_sha256": canonical_json_sha256_v1(matches),
                "rule": (
                    "EXPLICIT_UNIT_CUSTOMER_DEPOSIT_OWNER_ROW_EQUALS_UNIT_LESS_"
                    "DETAIL_VISIBLE_TOTAL_WITH_BOTH_AXES_EXACT_CURRENT_COMPARATIVE"
                ),
                "status": "UNIQUE",
            }
            reasons = []
    if (
        canonical_unit is None
        and reasons == ["MONEY_UNIT_NOT_EXACTLY_RESOLVED"]
        and not evidence
        and not undeclared
        and not conflicts
        and type(document_unit_context) is dict
        and document_unit_context.get("status") == "UNIQUE"
        and type(document_unit_context.get("canonical_unit")) is str
    ):
        canonical_unit = document_unit_context["canonical_unit"]
        source = "DOCUMENT_EXPLICIT_TABLE_UNIT_CONSENSUS"
        inherited_context = canonical_clone_v1(document_unit_context)
        reasons = []
    return {
        "canonical_unit": canonical_unit,
        "complete": canonical_unit is not None and not reasons,
        "document_unit_context_evidence": inherited_context,
        "evidence": evidence,
        "reasons": sorted(set(reasons)),
        "source": source,
        "undeclared_evidence": undeclared,
    }


def _stacked_currency_axis(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    columns = table.get("columns")
    if (
        type(columns) is not list
        or len(columns) != 3
        or any(
            type(column) is not dict or column.get("value_kind") != "MONEY" for column in columns
        )
    ):
        return {
            "complete": False,
            "reasons": ["STACKED_LAYOUT_REQUIRES_EXACTLY_THREE_MONEY_COLUMNS"],
        }
    by_role: dict[str, int] = {}
    reasons = []
    headers = [_header_text(column) for column in columns]
    for ordinal, (column, _header) in enumerate(zip(columns, headers, strict=True), start=1):
        path = column.get("header_path_exact")
        path_values = [value for value in path if type(value) is str] if type(path) is list else []
        matched_roles = []
        for role, aliases in compiled_specs["currency_aliases"].items():
            if any(
                (
                    len(alias.split()) == 1
                    and any(_normalized(value) == alias for value in path_values)
                )
                or (
                    len(alias.split()) > 1
                    and any(_match_alias(_normalized(value), alias) for value in path_values)
                )
                for alias in aliases
            ):
                matched_roles.append(role)
        if len(matched_roles) != 1:
            reasons.append(f"STACKED_CURRENCY_COLUMN_ROLE_NOT_UNIQUE:c{ordinal}")
        elif matched_roles[0] in by_role:
            reasons.append(f"STACKED_CURRENCY_ROLE_DUPLICATED:{matched_roles[0]}")
        else:
            by_role[matched_roles[0]] = ordinal
    if set(by_role) != {"VND", "FOREIGN", "TOTAL"}:
        reasons.append("STACKED_CURRENCY_AXIS_INCOMPLETE")
    return {
        "column_ordinal_by_role": by_role,
        "complete": not reasons,
        "headers_exact": headers,
        "reasons": sorted(set(reasons)),
    }


def _stacked_period_signature(table: Mapping[str, Any]) -> dict[str, Any]:
    surfaces = [table.get("title_exact")]
    columns = table.get("columns")
    if type(columns) is list:
        surfaces.extend(_header_text(column) for column in columns if type(column) is dict)
    dates = sorted(
        {
            item.isoformat()
            for surface in surfaces
            if type(surface) is str
            for item in _header_dates(surface)
        }
    )
    semantics = sorted(
        {
            role
            for surface in surfaces
            if type(surface) is str
            for role in _semantic_period_roles(surface)
        }
    )
    reasons = []
    if len(dates) > 1:
        reasons.append("STACKED_FRAGMENT_MULTIPLE_DISTINCT_DATES")
    if len(semantics) > 1:
        reasons.append("STACKED_FRAGMENT_MULTIPLE_SEMANTIC_PERIOD_ROLES")
    if len(dates) == 1 and len(semantics) == 1:
        # A dated fragment may also say current/comparative, but this is only
        # accepted after the two-fragment ordering check below.
        signature = ["DATE", dates[0]]
    elif len(dates) == 1:
        signature = ["DATE", dates[0]]
    elif len(semantics) == 1:
        signature = ["SEMANTIC_ALIAS", semantics[0]]
    else:
        signature = None
        reasons.append("STACKED_FRAGMENT_PERIOD_SIGNATURE_ABSENT")
    return {
        "complete": signature is not None and not reasons,
        "dates": dates,
        "reasons": sorted(set(reasons)),
        "semantic_roles": semantics,
        "signature": signature,
        "surfaces_exact": surfaces,
    }


def _parse_cells(row: Mapping[str, Any], column_ordinals: Sequence[int]) -> list[dict[str, Any]]:
    values = row.get("values_exact")
    if type(values) is not list or any(
        not 1 <= ordinal <= len(values) for ordinal in column_ordinals
    ):
        raise _error("customer-deposit row value vector does not bind the selected columns")
    try:
        return [_money(values[ordinal - 1]) for ordinal in column_ordinals]
    except ValueError as exc:
        raise _error("customer-deposit money cell is invalid") from exc


def _parse_customer_cells(
    row: Mapping[str, Any], column_ordinals: Sequence[int]
) -> list[dict[str, Any]]:
    """Retain a trailing-dash magnitude only for later exact child closure.

    A trailing dash can mean a negative number, an OCR artefact, or a stray
    table rule, so this parser never accepts it by itself.  ``_customer_view``
    may upgrade the provisional magnitude only when ordinary child cells prove
    it through an exact parent-equals-children equation.
    """

    values = row.get("values_exact")
    if type(values) is not list or any(
        not 1 <= ordinal <= len(values) for ordinal in column_ordinals
    ):
        raise _error("customer-deposit row value vector does not bind the selected columns")
    cells = []
    for ordinal in column_ordinals:
        value = values[ordinal - 1]
        try:
            cells.append(_money(value))
            continue
        except ValueError:
            pass
        if type(value) is not str:
            raise _error("customer-deposit money cell is invalid")
        body = value.strip()
        unsigned = body[:-1].strip() if body.endswith("-") else ""
        digits = unsigned.replace(".", "").replace(",", "").replace(" ", "")
        if not unsigned or not digits.isdigit():
            raise _error("customer-deposit money cell is invalid")
        cells.append(
            {
                "coefficient": int(digits),
                "source_text": value,
                "state": "TRAILING_DASH_POSITIVE_IF_EXACT_CHILD_CLOSURE",
            }
        )
    return cells


def _derived_cells(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        raise _error("customer-deposit derived cell axis is empty")
    width = len(records[0]["cells"])
    if width != 2 or any(len(record["cells"]) != width for record in records):
        raise _error("customer-deposit derived cell vectors do not align")
    cells = []
    for lane in range(width):
        coefficients = [
            observed_source_coefficient_v1(record["cells"][lane]) for record in records
        ]
        if any(coefficient is None for coefficient in coefficients):
            cells.append(
                {
                    "coefficient": None,
                    "source_text": None,
                    "state": "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
                }
            )
            continue
        cells.append(
            {
                "coefficient": sum(
                    coefficient for coefficient in coefficients if coefficient is not None
                ),
                "source_text": None,
                "state": "DERIVED_EXACT_SUM_OF_SOURCE_ROWS",
            }
        )
    return cells


def _coefficients(record: Mapping[str, Any]) -> list[int | None]:
    return [observed_source_coefficient_v1(cell) for cell in record["cells"]]


def _equation(
    *,
    equation_kind: str,
    component_records: Sequence[Mapping[str, Any]],
    result_record: Mapping[str, Any],
    result_role: str,
    unit_axis: Mapping[str, Any],
) -> dict[str, Any]:
    rounding_bound = (len(component_records) + 1) // 2
    maximum_absolute_residual = (
        rounding_bound if unit_axis.get("canonical_unit") == "MILLION_VND" else 0
    )
    lane_receipts = additive_source_lane_receipts_v1(
        result_cells=result_record["cells"],
        component_cell_vectors=[record["cells"] for record in component_records],
        maximum_absolute_residual=maximum_absolute_residual,
    )
    complete_statuses = {
        "EXACT_OBSERVED_SOURCE_LANE",
        "BOUNDED_DISPLAY_ROUNDING_SOURCE_LANE",
    }
    observed_receipts = [
        receipt for receipt in lane_receipts if receipt["status"] in complete_statuses
    ]
    any_unobserved = len(observed_receipts) != len(lane_receipts)
    any_conflict = any(
        receipt["status"] == "SOURCE_LANE_EQUATION_CONFLICT"
        for receipt in lane_receipts
    )
    any_rounding = any(
        receipt["status"] == "BOUNDED_DISPLAY_ROUNDING_SOURCE_LANE"
        for receipt in lane_receipts
    )
    if any_conflict:
        status = "MISMATCH"
    elif not observed_receipts:
        status = "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
    elif any_unobserved:
        status = (
            "PARTIAL_OBSERVED_LANES_BOUNDED_MILLION_VND_ROUNDING"
            if any_rounding
            else "PARTIAL_OBSERVED_LANES_EXACT"
        )
    else:
        status = "BOUNDED_MILLION_VND_ROUNDING" if any_rounding else "EXACT"
    component_sums = [receipt["component_sum"] for receipt in lane_receipts]
    result = [receipt["result_coefficient"] for receipt in lane_receipts]
    deltas = [
        -receipt["residual"] if type(receipt["residual"]) is int else None
        for receipt in lane_receipts
    ]
    material = {
        "component_roles": [record["role"] for record in component_records],
        "component_source_refs": [
            canonical_clone_v1(record["source_refs"]) for record in component_records
        ],
        "component_sums": component_sums,
        "equation_kind": equation_kind,
        "lane_receipts": lane_receipts,
        "result_coefficients": result,
        "result_role": result_role,
        "result_source_refs": canonical_clone_v1(result_record["source_refs"]),
        "rounding_receipt": {
            "accepted_only_for_unit": "MILLION_VND",
            "component_count": len(component_records),
            "maximum_absolute_delta": rounding_bound,
            "observed_deltas": deltas,
            "rule": "SUM_OF_N_INDEPENDENTLY_ROUNDED_COMPONENTS_VS_ONE_ROUNDED_TOTAL",
        },
        "status": status,
    }
    return {
        **material,
        "equation_id": "gjfcdev1:equation:" + canonical_json_sha256_v1(material),
    }


def _equation_closes(equation: Mapping[str, Any]) -> bool:
    return equation.get("status") in {
        "EXACT",
        "BOUNDED_MILLION_VND_ROUNDING",
        "PARTIAL_OBSERVED_LANES_EXACT",
        "PARTIAL_OBSERVED_LANES_BOUNDED_MILLION_VND_ROUNDING",
    }


def _source_ref(
    region: Mapping[str, Any], row_ordinal: int, row: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
        "label_exact": row.get("label_exact"),
        "locator": canonical_clone_v1(region),
        "row_id": f"r{row_ordinal}",
        "row_kind": row.get("row_kind"),
        "row_ordinal": row_ordinal,
    }


def _record(
    *, role: str, cells: list[dict[str, Any]], source_refs: list[dict[str, Any]], state: str
) -> dict[str, Any]:
    return {
        "cells": canonical_clone_v1(cells),
        "role": role,
        "source_refs": canonical_clone_v1(source_refs),
        "state": state,
    }


def _aggregate_records(role: str, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return _record(
        role=role,
        cells=_derived_cells(records),
        source_refs=[ref for record in records for ref in record["source_refs"]],
        state="DERIVED_EXACT_SUM_OF_SOURCE_ROWS",
    )


def _ordinary_type_view(
    *,
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any] | None,
    row_source_axis: Sequence[tuple[Mapping[str, Any], int]] | None = None,
    layout: str = "ROW_ROLES_X_TWO_PERIOD_COLUMNS",
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[str]]:
    period_axis = _two_period_axis(table)
    unit_axis = _unit_axis(
        table,
        compiled_specs=compiled_specs,
        document_unit_context=document_unit_context,
    )
    reasons = [*period_axis["reasons"], *unit_axis["reasons"]]
    money_columns = period_axis.get("money_column_ordinals", [])
    rows = table.get("rows")
    if type(rows) is not list:
        raise _error("customer-deposit ordinary type row axis is invalid")
    if row_source_axis is not None and len(row_source_axis) != len(rows):
        raise _error("customer-deposit ordinary type source-row axis is invalid")
    direct: dict[str, list[dict[str, Any]]] = defaultdict(list)
    children: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    savings_children: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    totals: list[dict[str, Any]] = []
    inventory = []
    active_parent_role: str | None = None
    for ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            reasons.append("SOURCE_ROW_AXIS_INVALID")
            continue
        source_region, source_row_ordinal = (
            row_source_axis[ordinal - 1] if row_source_axis is not None else (region, ordinal)
        )
        ref = _source_ref(source_region, source_row_ordinal, row)
        label = row.get("label_exact")
        currency_role = _currency_role_for_text(label)
        matched_roles = _source_roles_for_text(
            label, roles=_TYPE_SOURCE_ROLES, compiled_specs=compiled_specs
        )
        if row.get("row_kind") == "TOTAL" and not matched_roles:
            try:
                cells = _parse_cells(row, money_columns)
            except GeminiJsonCustomerDepositFamilyV1Error:
                reasons.append("TYPE_VISIBLE_TOTAL_MONEY_VECTOR_INVALID")
                cells = []
            totals.append(
                _record(
                    role="TYPE_VISIBLE_TOTAL",
                    cells=cells,
                    source_refs=[ref],
                    state="SOURCE_VISIBLE",
                )
            )
            inventory.append({**ref, "disposition": "TYPE_VISIBLE_TOTAL", "matched_roles": []})
            active_parent_role = None
            continue
        disposition = "UNCLASSIFIED_TYPE_ROW"
        structural_typed_parent = (
            row.get("row_kind") in {"GROUP", "SUBTOTAL"}
            and len(matched_roles) == 1
            and not any(value is not None for value in row.get("values_exact", []))
        )
        if (currency_role is None or structural_typed_parent) and len(matched_roles) == 1:
            role = matched_roles[0]
            try:
                cells = _parse_cells(row, money_columns)
            except GeminiJsonCustomerDepositFamilyV1Error:
                reasons.append(f"TYPE_DIRECT_ROLE_MONEY_VECTOR_INVALID:{role}")
                cells = []
            direct[role].append(
                _record(role=role, cells=cells, source_refs=[ref], state="SOURCE_VISIBLE")
            )
            disposition = "TYPE_DIRECT_ROLE"
            active_parent_role = role
        elif currency_role is not None:
            parent_role, parent_ambiguous = _parent_role_for_currency_row(
                row,
                compiled_specs=compiled_specs,
                active_parent_role=active_parent_role,
            )
            if parent_ambiguous:
                reasons.append(f"TYPE_CURRENCY_PARENT_AMBIGUOUS:r{ordinal}")
            elif parent_role is None:
                reasons.append(f"TYPE_CURRENCY_PARENT_ABSENT:r{ordinal}")
            else:
                try:
                    cells = _parse_cells(row, money_columns)
                except GeminiJsonCustomerDepositFamilyV1Error:
                    reasons.append(f"TYPE_CURRENCY_ROLE_MONEY_VECTOR_INVALID:r{ordinal}")
                    cells = []
                child = _record(
                    role=f"{parent_role}_{currency_role}",
                    cells=cells,
                    source_refs=[ref],
                    state="SOURCE_VISIBLE",
                )
                if cells and all(
                    observed_source_coefficient_v1(cell) is None for cell in cells
                ):
                    # A labelled currency subtype with no observed lane is an
                    # omission.  It cannot become an equation operand or a
                    # derived numeric zero merely because the visible sibling
                    # rows happen to close the printed parent.
                    disposition = "TYPE_CURRENCY_CHILD_ALL_LANES_BLANK_OMITTED"
                else:
                    children[(parent_role, currency_role)].append(child)
                    savings_role_hits = [
                        role
                        for role in matched_roles
                        if role in {"SAVINGS_NO_TERM", "SAVINGS_TERM"}
                    ]
                    if len(savings_role_hits) == 1:
                        savings_children[(savings_role_hits[0], currency_role)].append(
                            child
                        )
                    disposition = "TYPE_CURRENCY_CHILD"
        elif _is_blank_structural_owner_row(row, compiled_specs=compiled_specs):
            disposition = "EXCLUDED_EXACT_STRUCTURAL_CUSTOMER_DEPOSIT_OWNER"
        elif (
            row.get("row_kind") == "GROUP"
            and _normalized(label).lstrip("- ") == "thuyet minh theo loai tien gui"
            and not any(value is not None for value in row.get("values_exact", []))
        ):
            # A source-visible section caption embedded as a GROUP row is not
            # a monetary family item.  This exact structural label is narrow;
            # unknown valued rows remain fail-closed below.
            disposition = "EXCLUDED_EXACT_TYPE_VIEW_CAPTION"
        elif row.get("label_exact") is None and not any(
            value is not None for value in row.get("values_exact", [])
        ):
            disposition = "EXCLUDED_BLANK_STRUCTURAL_ROW"
        elif row.get("row_kind") in {"GROUP", "SUBTOTAL"}:
            active_parent_role = None
        if disposition == "UNCLASSIFIED_TYPE_ROW":
            reasons.append(f"UNCONSUMED_TYPE_SOURCE_ROW:r{ordinal}")
        inventory.append(
            {
                **ref,
                "currency_role": currency_role,
                "disposition": disposition,
                "matched_roles": matched_roles,
            }
        )
    if len(totals) != 1 or not totals[0]["cells"]:
        reasons.append("TYPE_VISIBLE_TOTAL_COUNT_NOT_ONE")
    for role, records in direct.items():
        if len(records) > 1:
            reasons.append(f"DUPLICATE_TYPE_DIRECT_ROLE:{role}")
    source_parent_records: dict[str, dict[str, Any]] = {}
    equations: list[dict[str, Any]] = []
    output: dict[str, dict[str, Any]] = {}
    for role in (item for item in _TYPE_SOURCE_ROLES if item != "SAVINGS_COMBINED"):
        direct_record = direct.get(role, [None])[0] if len(direct.get(role, [])) == 1 else None
        child_records = [
            child
            for currency_role in ("VND", "FOREIGN")
            for child in children.get((role, currency_role), [])
        ]
        if direct_record is None and not child_records:
            continue
        child_sum = _aggregate_records(role, child_records) if child_records else None
        direct_visible = direct_record is not None and any(
            cell["source_text"] is not None for cell in direct_record["cells"]
        )
        if direct_visible:
            parent_record = direct_record
            if child_sum is not None:
                equation = _equation(
                    equation_kind="TYPE_PARENT_EQUALS_CURRENCY_CHILDREN",
                    component_records=child_records,
                    result_record=direct_record,
                    result_role=role,
                    unit_axis=unit_axis,
                )
                equations.append(equation)
                if not _equation_closes(equation):
                    reasons.append(f"TYPE_PARENT_CURRENCY_EQUATION_MISMATCH:{role}")
        elif child_sum is not None:
            parent_record = child_sum
        elif direct_record is not None and all(
            observed_source_coefficient_v1(cell) is None
            for cell in direct_record["cells"]
        ):
            # A labelled optional row that is blank in every lane is an
            # omission, not a numeric zero and not an equation operand.
            continue
        else:
            reasons.append(f"TYPE_PARENT_BLANK_WITHOUT_CHILD_FRONTIER:{role}")
            continue
        source_parent_records[role] = parent_record
        if role in _BASE_TYPE_ROLES:
            output[role] = _record(
                role=role,
                cells=parent_record["cells"],
                source_refs=parent_record["source_refs"],
                state=parent_record["state"],
            )
            for currency_role in ("VND", "FOREIGN"):
                records = children.get((role, currency_role), [])
                if records:
                    output_role = f"{role}_{currency_role}"
                    output[output_role] = _aggregate_records(output_role, records)
    savings_source_records = [
        source_parent_records[role]
        for role in ("SAVINGS_NO_TERM", "SAVINGS_TERM")
        if role in source_parent_records
    ]
    combined_direct = (
        direct.get("SAVINGS_COMBINED", [None])[0]
        if len(direct.get("SAVINGS_COMBINED", [])) == 1
        else None
    )
    combined_children = [
        child
        for currency_role in ("VND", "FOREIGN")
        for child in children.get(("SAVINGS_COMBINED", currency_role), [])
    ]
    combined_child_sum = (
        _aggregate_records("SAVINGS_COMBINED", combined_children) if combined_children else None
    )
    combined_direct_visible = combined_direct is not None and any(
        cell["source_text"] is not None for cell in combined_direct["cells"]
    )
    specific_sum = (
        _aggregate_records("SAVINGS_COMBINED", savings_source_records)
        if savings_source_records
        else None
    )
    combined_record = None
    if combined_direct_visible:
        combined_record = combined_direct
        comparison_records = combined_children or savings_source_records
        if comparison_records:
            equation = _equation(
                equation_kind="SAVINGS_COMBINED_EQUALS_SOURCE_COMPONENTS",
                component_records=comparison_records,
                result_record=combined_direct,
                result_role="SAVINGS_COMBINED",
                unit_axis=unit_axis,
            )
            equations.append(equation)
            if not _equation_closes(equation):
                reasons.append("SAVINGS_COMBINED_SOURCE_COMPONENT_EQUATION_MISMATCH")
    elif combined_child_sum is not None:
        combined_record = combined_child_sum
    elif specific_sum is not None:
        combined_record = specific_sum
    elif combined_direct is not None and all(
        observed_source_coefficient_v1(cell) is None
        for cell in combined_direct["cells"]
    ):
        combined_record = None
    if combined_record is not None:
        source_parent_records["SAVINGS_COMBINED"] = combined_record
        output["SAVINGS"] = _record(
            role="SAVINGS",
            cells=combined_record["cells"],
            source_refs=combined_record["source_refs"],
            state=combined_record["state"],
        )
    elif savings_source_records:
        output["SAVINGS"] = _aggregate_records("SAVINGS", savings_source_records)
    for currency_role in ("VND", "FOREIGN"):
        records = list(children.get(("SAVINGS_COMBINED", currency_role), []))
        if not records:
            records = [
                child
                for source_role in ("SAVINGS_NO_TERM", "SAVINGS_TERM")
                for child in savings_children.get((source_role, currency_role), [])
            ]
        if records:
            output_role = f"SAVINGS_{currency_role}"
            output[output_role] = _aggregate_records(output_role, records)
    if "SAVINGS" not in output:
        savings_currency_records = [
            output[role] for role in ("SAVINGS_VND", "SAVINGS_FOREIGN") if role in output
        ]
        if savings_currency_records:
            output["SAVINGS"] = _aggregate_records("SAVINGS", savings_currency_records)
    present_base_roles = [role for role in _BASE_TYPE_ROLES if role in source_parent_records]
    additive_roles = list(present_base_roles)
    savings_structural_records = []
    if "SAVINGS_COMBINED" in source_parent_records:
        if combined_direct is not None or combined_children:
            structural_record = (
                combined_direct
                if combined_direct is not None
                else source_parent_records["SAVINGS_COMBINED"]
            )
            savings_structural_records.append(("SAVINGS_COMBINED", structural_record))
        else:
            for source_role in ("SAVINGS_NO_TERM", "SAVINGS_TERM"):
                record = source_parent_records.get(source_role)
                if record is None:
                    continue
                direct_structural_records = direct.get(source_role, [])
                savings_structural_records.append(
                    (
                        source_role,
                        direct_structural_records[0]
                        if len(direct_structural_records) == 1
                        else record,
                    )
                )
    if savings_structural_records and all(
        not {
            ancestor_role
            for value in ref.get("hierarchy_path_exact", [])[:-1]
            for ancestor_role in _source_roles_for_text(
                value,
                roles=_TYPE_SOURCE_ROLES,
                compiled_specs=compiled_specs,
            )
            if ancestor_role != source_role
        }
        for source_role, record in savings_structural_records
        for ref in record["source_refs"]
    ):
        additive_roles.append("SAVINGS_COMBINED")
    if not any(
        set(required_roles) <= set(present_base_roles)
        for required_roles in compiled_specs["topology"]["required_role_combinations"]
    ):
        reasons.append("TYPE_ROOT_DIRECT_FRONTIER_INCOMPLETE")
    elif len(totals) == 1 and totals[0]["cells"]:
        equation = _equation(
            equation_kind="TYPE_ROOT_EQUALS_DIRECT_PARENT_FRONTIER",
            component_records=[source_parent_records[role] for role in additive_roles],
            result_record=totals[0],
            result_role="TYPE_VISIBLE_TOTAL",
            unit_axis=unit_axis,
        )
        equations.append(equation)
        if not _equation_closes(equation):
            reasons.append("TYPE_ROOT_TOTAL_EQUATION_MISMATCH")
    return (
        output,
        equations,
        {
            "layout": layout,
            "period_axis": period_axis,
            "source_inventory": inventory,
            "unit_axis": unit_axis,
        },
        sorted(set(reasons)),
    )


def _stacked_type_view(
    *,
    tables: Sequence[Mapping[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[str]]:
    if len(tables) != 2 or len(regions) != 2:
        raise _error("customer-deposit stacked type layout needs two fragments")
    period_receipts = [_stacked_period_signature(table) for table in tables]
    currency_receipts = [
        _stacked_currency_axis(table, compiled_specs=compiled_specs) for table in tables
    ]
    unit_receipts = [
        _unit_axis(
            table,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
        for table in tables
    ]
    reasons = [
        *(
            f"STACKED_FRAGMENT_{ordinal}:{reason}"
            for ordinal, receipt in enumerate(period_receipts, 1)
            for reason in receipt["reasons"]
        ),
        *(
            f"STACKED_FRAGMENT_{ordinal}:{reason}"
            for ordinal, receipt in enumerate(currency_receipts, 1)
            for reason in receipt["reasons"]
        ),
        *(
            f"STACKED_FRAGMENT_{ordinal}:{reason}"
            for ordinal, receipt in enumerate(unit_receipts, 1)
            for reason in receipt["reasons"]
        ),
    ]
    signatures = [receipt.get("signature") for receipt in period_receipts]
    for ordinal, (receipt, expected_role) in enumerate(
        zip(period_receipts, ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"), strict=True),
        start=1,
    ):
        semantic_roles = receipt.get("semantic_roles", [])
        if len(semantic_roles) == 1 and semantic_roles[0] != expected_role:
            reasons.append(f"STACKED_DATE_AND_SEMANTIC_PERIOD_EVIDENCE_CONFLICT:fragment_{ordinal}")
    if all(signature is not None for signature in signatures):
        first, second = signatures
        assert first is not None and second is not None
        if first[0] != second[0]:
            reasons.append("STACKED_PERIOD_SIGNATURE_KINDS_DIFFER")
        elif first[0] == "DATE" and not date.fromisoformat(first[1]) > date.fromisoformat(
            second[1]
        ):
            reasons.append("STACKED_PERIOD_AXIS_IS_NOT_STRICT_CURRENT_THEN_COMPARATIVE")
        elif first[0] == "SEMANTIC_ALIAS" and [first[1], second[1]] != [
            "CURRENT_PERIOD",
            "COMPARATIVE_PERIOD",
        ]:
            reasons.append("STACKED_SEMANTIC_PERIOD_AXIS_IS_NOT_CURRENT_COMPARATIVE")
    if any(
        receipt.get("canonical_unit") != unit_receipts[0].get("canonical_unit")
        for receipt in unit_receipts[1:]
    ):
        reasons.append("STACKED_FRAGMENT_UNITS_DIFFER")
    fragment_rows: list[dict[str, dict[str, dict[str, Any]]]] = []
    fragment_totals: list[dict[str, dict[str, Any]]] = []
    inventory = []
    for table, region, currency_axis in zip(tables, regions, currency_receipts, strict=True):
        rows = table.get("rows")
        if type(rows) is not list:
            raise _error("customer-deposit stacked row axis is invalid")
        by_role: dict[str, dict[str, dict[str, Any]]] = {}
        total_by_currency: dict[str, dict[str, Any]] = {}
        for ordinal, row in enumerate(rows, start=1):
            if type(row) is not dict:
                reasons.append("STACKED_SOURCE_ROW_INVALID")
                continue
            ref = _source_ref(region, ordinal, row)
            role = None
            disposition = "UNCLASSIFIED_STACKED_TYPE_ROW"
            matched = _source_roles_for_text(
                row.get("label_exact"), roles=_TYPE_SOURCE_ROLES, compiled_specs=compiled_specs
            )
            if row.get("row_kind") == "TOTAL" and not matched:
                disposition = "TYPE_VISIBLE_TOTAL"
                for currency_role, column_ordinal in currency_axis.get(
                    "column_ordinal_by_role", {}
                ).items():
                    total_by_currency[currency_role] = _record(
                        role=f"TYPE_VISIBLE_TOTAL_{currency_role}",
                        cells=[_parse_cells(row, [column_ordinal])[0]],
                        source_refs=[ref],
                        state="SOURCE_VISIBLE",
                    )
            else:
                if len(matched) == 1:
                    role = matched[0]
                    disposition = "STACKED_TYPE_ROLE"
                    if role in by_role:
                        reasons.append(f"STACKED_DUPLICATE_TYPE_ROLE:{role}")
                    records = {}
                    for currency_role, column_ordinal in currency_axis.get(
                        "column_ordinal_by_role", {}
                    ).items():
                        records[currency_role] = _record(
                            role=f"{role}_{currency_role}",
                            cells=[_parse_cells(row, [column_ordinal])[0]],
                            source_refs=[ref],
                            state="SOURCE_VISIBLE",
                        )
                    by_role[role] = records
                else:
                    reasons.append(f"STACKED_UNCONSUMED_OR_AMBIGUOUS_TYPE_ROW:r{ordinal}")
            inventory.append(
                {
                    **ref,
                    "disposition": disposition,
                    "matched_role": role,
                }
            )
        if set(total_by_currency) != {"VND", "FOREIGN", "TOTAL"}:
            reasons.append("STACKED_VISIBLE_TOTAL_CURRENCY_AXIS_INCOMPLETE")
        fragment_rows.append(by_role)
        fragment_totals.append(total_by_currency)
    role_sets = [set(item) for item in fragment_rows]
    if role_sets[0] != role_sets[1]:
        reasons.append("STACKED_PERIOD_ROLE_POPULATIONS_DIFFER")
    source_period_records: dict[str, dict[str, dict[str, Any]]] = {}
    equations: list[dict[str, Any]] = []
    output: dict[str, dict[str, Any]] = {}
    for role in sorted(role_sets[0] & role_sets[1], key=_TYPE_SOURCE_ROLES.index):
        records_by_currency = {}
        for currency_role in ("VND", "FOREIGN", "TOTAL"):
            lane_records = [fragment_rows[lane][role][currency_role] for lane in range(2)]
            records_by_currency[currency_role] = _record(
                role=f"{role}_{currency_role}",
                cells=[record["cells"][0] for record in lane_records],
                source_refs=[ref for record in lane_records for ref in record["source_refs"]],
                state="SOURCE_VISIBLE_STACKED_PERIOD_AXIS",
            )
        source_period_records[role] = records_by_currency
        equation = _equation(
            equation_kind="STACKED_ROLE_TOTAL_EQUALS_CURRENCY_COMPONENTS",
            component_records=[records_by_currency["VND"], records_by_currency["FOREIGN"]],
            result_record=records_by_currency["TOTAL"],
            result_role=role,
            unit_axis=unit_receipts[0],
        )
        equations.append(equation)
        if not _equation_closes(equation):
            reasons.append(f"STACKED_ROLE_CURRENCY_EQUATION_MISMATCH:{role}")
        if role in _BASE_TYPE_ROLES:
            output[role] = _record(
                role=role,
                cells=records_by_currency["TOTAL"]["cells"],
                source_refs=records_by_currency["TOTAL"]["source_refs"],
                state=records_by_currency["TOTAL"]["state"],
            )
            for currency_role in ("VND", "FOREIGN"):
                output_role = f"{role}_{currency_role}"
                output[output_role] = _record(
                    role=output_role,
                    cells=records_by_currency[currency_role]["cells"],
                    source_refs=records_by_currency[currency_role]["source_refs"],
                    state=records_by_currency[currency_role]["state"],
                )
    savings_roles = (
        ["SAVINGS_COMBINED"]
        if "SAVINGS_COMBINED" in source_period_records
        else [role for role in ("SAVINGS_NO_TERM", "SAVINGS_TERM") if role in source_period_records]
    )
    if savings_roles:
        for output_role, currency_role in (
            ("SAVINGS", "TOTAL"),
            ("SAVINGS_VND", "VND"),
            ("SAVINGS_FOREIGN", "FOREIGN"),
        ):
            output[output_role] = _aggregate_records(
                output_role, [source_period_records[role][currency_role] for role in savings_roles]
            )
    present_base_roles = [role for role in _BASE_TYPE_ROLES if role in source_period_records]
    additive_roles = list(present_base_roles)
    for role in savings_roles:
        if role not in source_period_records:
            continue
        refs = source_period_records[role]["TOTAL"]["source_refs"]
        if all(
            type(ref.get("hierarchy_path_exact")) is list
            and bool(ref["hierarchy_path_exact"])
            and _source_roles_for_text(
                ref["hierarchy_path_exact"][0],
                roles=_TYPE_SOURCE_ROLES,
                compiled_specs=compiled_specs,
            )
            == [role]
            for ref in refs
        ):
            additive_roles.append(role)
    if not any(
        set(required_roles) <= set(present_base_roles)
        for required_roles in compiled_specs["topology"]["required_role_combinations"]
    ):
        reasons.append("STACKED_TYPE_ROOT_DIRECT_FRONTIER_INCOMPLETE")
    else:
        total_records = {}
        for currency_role in ("VND", "FOREIGN", "TOTAL"):
            lane_records = [fragment_totals[lane].get(currency_role) for lane in range(2)]
            if any(record is None for record in lane_records):
                continue
            records = [record for record in lane_records if record is not None]
            total_records[currency_role] = _record(
                role=f"TYPE_VISIBLE_TOTAL_{currency_role}",
                cells=[record["cells"][0] for record in records],
                source_refs=[ref for record in records for ref in record["source_refs"]],
                state="SOURCE_VISIBLE_STACKED_PERIOD_AXIS",
            )
        for currency_role in ("VND", "FOREIGN", "TOTAL"):
            if currency_role not in total_records:
                continue
            equation = _equation(
                equation_kind=f"STACKED_TYPE_ROOT_{currency_role}_FRONTIER",
                component_records=[
                    source_period_records[role][currency_role] for role in additive_roles
                ],
                result_record=total_records[currency_role],
                result_role=f"TYPE_VISIBLE_TOTAL_{currency_role}",
                unit_axis=unit_receipts[0],
            )
            equations.append(equation)
            if not _equation_closes(equation):
                reasons.append(f"STACKED_TYPE_ROOT_EQUATION_MISMATCH:{currency_role}")
    return (
        output,
        equations,
        {
            "currency_axes": currency_receipts,
            "layout": "TWO_STACKED_PERIOD_TABLES_X_CURRENCY_COLUMNS",
            "period_axes": period_receipts,
            "source_inventory": inventory,
            "unit_axes": unit_receipts,
        },
        sorted(set(reasons)),
    )


def _customer_view(
    *,
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any] | None,
    row_source_axis: Sequence[tuple[Mapping[str, Any], int]] | None = None,
    layout: str = "CUSTOMER_ROWS_X_MONEY_AND_OPTIONAL_PERCENT_COLUMNS",
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[str]]:
    period_axis = _two_period_axis(table)
    unit_axis = _unit_axis(
        table,
        compiled_specs=compiled_specs,
        document_unit_context=document_unit_context,
    )
    reasons = [*period_axis["reasons"], *unit_axis["reasons"]]
    money_columns = period_axis.get("money_column_ordinals", [])
    rows = table.get("rows")
    if type(rows) is not list:
        raise _error("customer-deposit customer-view row axis is invalid")
    if row_source_axis is not None and len(row_source_axis) != len(rows):
        raise _error("customer-deposit customer-view source-row axis is invalid")
    by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    structural_by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    parent_role_by_source_ref: dict[str, str | None] = {}
    totals = []
    inventory = []
    active_customer_parent_role: str | None = None
    for ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            reasons.append("CUSTOMER_SOURCE_ROW_INVALID")
            continue
        source_region, source_row_ordinal = (
            row_source_axis[ordinal - 1] if row_source_axis is not None else (region, ordinal)
        )
        ref = _source_ref(source_region, source_row_ordinal, row)
        ref_key = canonical_json_sha256_v1(
            {"locator": ref["locator"], "row_ordinal": ref["row_ordinal"]}
        )
        if row.get("row_kind") == "TOTAL":
            try:
                cells = _parse_cells(row, money_columns)
            except GeminiJsonCustomerDepositFamilyV1Error:
                reasons.append("CUSTOMER_VISIBLE_TOTAL_MONEY_VECTOR_INVALID")
                cells = []
            totals.append(
                _record(
                    role="CUSTOMER_VISIBLE_TOTAL",
                    cells=cells,
                    source_refs=[ref],
                    state="SOURCE_VISIBLE",
                )
            )
            inventory.append({**ref, "disposition": "CUSTOMER_VISIBLE_TOTAL", "matched_roles": []})
            active_customer_parent_role = None
            continue
        normalized_label = _normalized(row.get("label_exact")).lstrip("- ")
        if (
            row.get("row_kind") == "GROUP"
            and any(
                normalized_label.startswith(prefix)
                for prefix in (
                    "thuyet minh theo doi tuong khach hang",
                    "thuyet minh theo loai hinh doanh nghiep",
                )
            )
            and not any(value is not None for value in row.get("values_exact", []))
        ):
            inventory.append(
                {
                    **ref,
                    "disposition": "EXCLUDED_EXACT_CUSTOMER_VIEW_CAPTION",
                    "matched_roles": [],
                }
            )
            continue
        if _is_blank_structural_owner_row(row, compiled_specs=compiled_specs):
            inventory.append(
                {
                    **ref,
                    "disposition": "EXCLUDED_EXACT_STRUCTURAL_CUSTOMER_DEPOSIT_OWNER",
                    "matched_roles": [],
                }
            )
            continue
        matched = _source_roles_for_text(
            row.get("label_exact"), roles=_CUSTOMER_SOURCE_ROLES, compiled_specs=compiled_specs
        )
        if not matched and row.get("row_kind") == "SUBTOTAL" and row.get("label_exact") is None:
            hierarchy_path = row.get("hierarchy_path_exact")
            hierarchy_roles = {
                role
                for value in (hierarchy_path if type(hierarchy_path) is list else [])
                for role in _source_roles_for_text(
                    value,
                    roles=_CUSTOMER_SOURCE_ROLES,
                    compiled_specs=compiled_specs,
                )
            }
            if len(hierarchy_roles) == 1:
                matched = sorted(hierarchy_roles)
        if len(matched) != 1:
            reasons.append(f"CUSTOMER_SOURCE_ROW_UNCONSUMED_OR_AMBIGUOUS:r{ordinal}")
            inventory.append(
                {**ref, "disposition": "UNCONSUMED_OR_AMBIGUOUS", "matched_roles": matched}
            )
            continue
        role = matched[0]
        cells_valid = True
        try:
            cells = _parse_customer_cells(row, money_columns)
        except GeminiJsonCustomerDepositFamilyV1Error:
            reasons.append(f"CUSTOMER_ROLE_MONEY_VECTOR_INVALID:{role}:r{ordinal}")
            cells = []
            cells_valid = False
        record = _record(role=role, cells=cells, source_refs=[ref], state="SOURCE_VISIBLE")
        source_visible = any(cell["source_text"] is not None for cell in cells)
        if source_visible or not cells_valid:
            by_role[role].append(record)
        ancestors: list[str] = []
        path = row.get("hierarchy_path_exact")
        label_folded = _normalized(row.get("label_exact"))
        if type(path) is list:
            for value in reversed(path):
                if _normalized(value) == label_folded:
                    continue
                path_roles = set(
                    _source_roles_for_text(
                        value,
                        roles=_CUSTOMER_SOURCE_ROLES,
                        compiled_specs=compiled_specs,
                    )
                )
                path_roles.discard(role)
                if len(path_roles) == 1:
                    ancestors = sorted(path_roles)
                    break
                if len(path_roles) > 1:
                    ancestors = sorted(path_roles)
                    break
        parent_role_by_source_ref[ref_key] = ancestors[0] if len(ancestors) == 1 else None
        if len(ancestors) > 1:
            reasons.append(f"CUSTOMER_HIERARCHY_PARENT_AMBIGUOUS:r{ordinal}")
        if (
            not ancestors
            and active_customer_parent_role == "CUSTOMER_TCKT"
            and role in _CUSTOMER_TCKT_CHILD_ROLES
        ):
            parent_role_by_source_ref[ref_key] = "CUSTOMER_TCKT"
        if not source_visible and cells_valid and row.get("row_kind") in {"GROUP", "SUBTOTAL"}:
            structural_by_role[role].append(record)
        if role == "CUSTOMER_TCKT":
            active_customer_parent_role = (
                None if row.get("row_kind") == "SUBTOTAL" else "CUSTOMER_TCKT"
            )
        elif role not in _CUSTOMER_TCKT_CHILD_ROLES:
            active_customer_parent_role = None
        inventory_item = {
            **ref,
            "disposition": (
                "SOURCE_ONLY_NO_EQUIVALENT_CUSTOMER_DEPOSIT_SCHEMA_ID"
                if cells and source_visible and role not in compiled_specs["bindings"]
                else "MAPPED_CUSTOMER_ROLE"
                if cells and source_visible
                else "STRUCTURAL_CUSTOMER_ROLE_WITHOUT_VISIBLE_VALUE"
                if cells
                else "UNRESOLVED_INVALID_CUSTOMER_MONEY_VECTOR"
            ),
            "matched_roles": matched,
            "parent_role": parent_role_by_source_ref[ref_key],
        }
        conditional_lanes = [
            lane
            for lane, cell in enumerate(cells, start=1)
            if cell["state"] == "TRAILING_DASH_POSITIVE_IF_EXACT_CHILD_CLOSURE"
        ]
        if conditional_lanes:
            inventory_item["conditional_money_lanes"] = conditional_lanes
            inventory_item["disposition"] = "PROVISIONAL_TRAILING_DASH_CUSTOMER_MONEY"
        inventory.append(inventory_item)
    if len(totals) != 1 or not totals[0]["cells"]:
        reasons.append("CUSTOMER_VISIBLE_TOTAL_COUNT_NOT_ONE")
    complete_by_role = {
        role: records
        for role, records in by_role.items()
        if records and all(len(record["cells"]) == 2 for record in records)
    }
    for role in sorted(set(by_role) - set(complete_by_role)):
        reasons.append(f"CUSTOMER_ROLE_CELL_VECTOR_INCOMPLETE:{role}")
    derived_structural_roles: set[str] = set()
    for role, structural_records in structural_by_role.items():
        if role in complete_by_role:
            continue
        if len(structural_records) != 1:
            reasons.append(f"CUSTOMER_STRUCTURAL_PARENT_COUNT_NOT_ONE:{role}")
            continue
        child_records = [
            record
            for child_role, records in complete_by_role.items()
            if child_role != role
            for record in records
            if any(
                parent_role_by_source_ref.get(
                    canonical_json_sha256_v1(
                        {"locator": ref["locator"], "row_ordinal": ref["row_ordinal"]}
                    )
                )
                == role
                for ref in record["source_refs"]
            )
        ]
        if not child_records:
            continue
        derived = _aggregate_records(role, child_records)
        derived["source_refs"] = [
            *canonical_clone_v1(structural_records[0]["source_refs"]),
            *derived["source_refs"],
        ]
        derived["state"] = "DERIVED_EXACT_COMPLETE_STRUCTURAL_CHILD_FRONTIER"
        complete_by_role[role] = [derived]
        derived_structural_roles.add(role)
        structural_ref = structural_records[0]["source_refs"][0]
        for item in inventory:
            if item["row_ordinal"] == structural_ref["row_ordinal"] and same_typed_json_v1(
                item["locator"], structural_ref["locator"]
            ):
                item["disposition"] = "DERIVED_FROM_COMPLETE_HIERARCHY_CHILD_FRONTIER"
    output = {role: _aggregate_records(role, records) for role, records in complete_by_role.items()}
    equations = []
    conditional_money_recoveries = []
    authenticated_conditional_cells: set[tuple[str, str, int]] = set()
    for parent_role in complete_by_role:
        child_records = [
            record
            for role, records in complete_by_role.items()
            if role != parent_role
            for record in records
            if any(
                parent_role_by_source_ref.get(
                    canonical_json_sha256_v1(
                        {"locator": ref["locator"], "row_ordinal": ref["row_ordinal"]}
                    )
                )
                == parent_role
                for ref in record["source_refs"]
            )
        ]
        if not child_records:
            continue
        equation = _equation(
            equation_kind="CUSTOMER_GROUP_EQUALS_HIERARCHY_CHILDREN",
            component_records=child_records,
            result_record=output[parent_role],
            result_role=parent_role,
            unit_axis=unit_axis,
        )
        equations.append(equation)
        if not _equation_closes(equation):
            reasons.append(f"CUSTOMER_HIERARCHY_EQUATION_MISMATCH:{parent_role}")
        parent_records = complete_by_role[parent_role]
        if equation["status"] == "EXACT" and len(parent_records) == 1:
            parent_record = parent_records[0]
            parent_ref = parent_record["source_refs"][0]
            for lane, cell in enumerate(parent_record["cells"], start=1):
                if cell["state"] != "TRAILING_DASH_POSITIVE_IF_EXACT_CHILD_CLOSURE":
                    continue
                if any(
                    record["cells"][lane - 1]["state"]
                    == "TRAILING_DASH_POSITIVE_IF_EXACT_CHILD_CLOSURE"
                    for record in child_records
                ):
                    continue
                authenticated_conditional_cells.add(
                    (
                        parent_role,
                        canonical_json_sha256_v1(
                            {
                                "locator": parent_ref["locator"],
                                "row_ordinal": parent_ref["row_ordinal"],
                            }
                        ),
                        lane,
                    )
                )
                recovered = output[parent_role]["cells"][lane - 1]
                recovered["source_text"] = cell["source_text"]
                recovered["state"] = "INFERRED_TRAILING_DASH_POSITIVE_EXACT_CHILD_CLOSURE"
                output[parent_role]["state"] = (
                    "DERIVED_WITH_TRAILING_DASH_POSITIVE_EXACT_CHILD_CLOSURE"
                )
                conditional_money_recoveries.append(
                    {
                        "equation_id": equation["equation_id"],
                        "lane": lane,
                        "role": parent_role,
                        "source_ref": canonical_clone_v1(parent_ref),
                        "source_text": cell["source_text"],
                        "state": "INFERRED_TRAILING_DASH_POSITIVE_EXACT_CHILD_CLOSURE",
                    }
                )
    for role, records in complete_by_role.items():
        for record in records:
            ref = record["source_refs"][0]
            for lane, cell in enumerate(record["cells"], start=1):
                if (
                    cell["state"] == "TRAILING_DASH_POSITIVE_IF_EXACT_CHILD_CLOSURE"
                    and (
                        role,
                        canonical_json_sha256_v1(
                            {"locator": ref["locator"], "row_ordinal": ref["row_ordinal"]}
                        ),
                        lane,
                    )
                    not in authenticated_conditional_cells
                ):
                    reasons.append(
                        f"CUSTOMER_TRAILING_DASH_NOT_EXACT_CHILD_CLOSURE:{role}:"
                        f"r{ref['row_ordinal']}:lane{lane}"
                    )
    for item in inventory:
        recoveries = [
            recovery
            for recovery in conditional_money_recoveries
            if recovery["source_ref"]["row_ordinal"] == item["row_ordinal"]
            and same_typed_json_v1(recovery["source_ref"]["locator"], item["locator"])
        ]
        if recoveries:
            item["conditional_money_recoveries"] = canonical_clone_v1(recoveries)
            item["disposition"] = "MAPPED_AFTER_EXACT_CHILD_CLOSURE"
    root_records = []
    for role, records in complete_by_role.items():
        if role in derived_structural_roles:
            root_records.append(output[role])
            continue
        top_level_records = [
            record
            for record in records
            if all(
                parent_role_by_source_ref.get(
                    canonical_json_sha256_v1(
                        {"locator": ref["locator"], "row_ordinal": ref["row_ordinal"]}
                    )
                )
                is None
                for ref in record["source_refs"]
            )
        ]
        if top_level_records:
            root_records.append(_aggregate_records(role, top_level_records))
    if len(totals) == 1 and totals[0]["cells"] and root_records:
        equation = _equation(
            equation_kind="CUSTOMER_VISIBLE_TOTAL_EQUALS_TOP_LEVEL_FRONTIER",
            component_records=root_records,
            result_record=totals[0],
            result_role="CUSTOMER_VISIBLE_TOTAL",
            unit_axis=unit_axis,
        )
        equations.append(equation)
        if not _equation_closes(equation):
            reasons.append("CUSTOMER_ROOT_TOTAL_EQUATION_MISMATCH")
    else:
        reasons.append("CUSTOMER_ROOT_FRONTIER_INCOMPLETE")
    receipt = {
        "layout": layout,
        "period_axis": period_axis,
        "source_only_schema_roles": sorted(
            role for role in complete_by_role if role not in compiled_specs["bindings"]
        ),
        "source_inventory": inventory,
        "unit_axis": unit_axis,
    }
    if conditional_money_recoveries:
        receipt["conditional_money_recoveries"] = conditional_money_recoveries
    return (
        output,
        equations,
        receipt,
        sorted(set(reasons)),
    )


def _partial_direct_customer_output(
    *,
    proposed_output: Mapping[str, Mapping[str, Any]],
    receipt: Mapping[str, Any],
    rejection_reasons: Sequence[str],
) -> dict[str, dict[str, Any]]:
    """Retain individually exact customer rows while disclosing residuals.

    The customer-classification table is an optional second view.  One
    source-only compound row must not erase other directly printed rows that
    have a unique schema identity, exact two-period columns, and an accepted
    unit.  Derived/blank/conditional/duplicate roles remain excluded until a
    complete equation closes.
    """

    if (
        not receipt.get("period_axis", {}).get("complete")
        or not receipt.get("unit_axis", {}).get("complete")
        or any(
            reason
            in {
                "CUSTOMER_AND_TYPE_PERIOD_AXES_DIFFER",
                "CUSTOMER_AND_TYPE_UNITS_DIFFER",
            }
            or "MONEY_VECTOR_INVALID" in reason
            for reason in rejection_reasons
        )
    ):
        return {}
    inventory_by_ref = {
        canonical_json_sha256_v1(
            {"locator": item["locator"], "row_ordinal": item["row_ordinal"]}
        ): item
        for item in receipt.get("source_inventory", [])
        if type(item) is dict and "locator" in item and "row_ordinal" in item
    }
    output = {}
    for role, record in proposed_output.items():
        refs = record.get("source_refs")
        if type(refs) is not list or len(refs) != 1:
            continue
        source_item = inventory_by_ref.get(
            canonical_json_sha256_v1(
                {"locator": refs[0]["locator"], "row_ordinal": refs[0]["row_ordinal"]}
            )
        )
        if source_item is None or source_item.get("disposition") != "MAPPED_CUSTOMER_ROLE":
            continue
        selected = canonical_clone_v1(record)
        selected["state"] = "SOURCE_VISIBLE_DIRECT_PARTIAL_OPTIONAL_CUSTOMER_VIEW"
        for cell in selected["cells"]:
            cell["state"] = "SOURCE_VISIBLE_DIRECT_PARTIAL_OPTIONAL_CUSTOMER_VIEW"
        output[role] = selected
    return output


def evaluate_gemini_json_customer_deposit_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one exact type/currency cluster and optional customer view."""

    region_axis = _region_axis(regions)
    expected_receipt = build_gemini_json_customer_deposit_region_query_receipt_v1(region_axis)
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected_receipt):
        raise _error("customer-deposit query receipt does not bind the exact fragments")
    source_pages, authenticated_source_repairs = _apply_authenticated_source_repairs(
        regions=region_axis,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    document_unit_context = _document_unit_context_axis(
        source_pages, compiled_specs=compiled_specs
    )
    type_regions = [item for item in region_axis if item["component_role"] == "TYPE_CURRENCY"]
    customer_regions = [item for item in region_axis if item["component_role"] == "CUSTOMER_TYPE"]
    tables = []
    for region in region_axis:
        page_json = source_pages.get(region["page_json_version_id"])
        if type(page_json) is not dict:
            raise _error("customer-deposit selected page JSON is absent")
        tables.append(_source_table_for_region(page_json, region=region))
    table_by_region = dict(
        zip((canonical_json_sha256_v1(item) for item in region_axis), tables, strict=True)
    )
    type_tables = [table_by_region[canonical_json_sha256_v1(item)] for item in type_regions]
    row_continuation_type = all(
        item.get("fragment_layout") == "ROW_CONTINUATION" for item in type_regions
    )
    if row_continuation_type:
        merged_type_table = _merge_row_fragments([{"table": table} for table in type_tables])
        classification = classify_gemini_json_customer_deposit_table_v1(
            merged_type_table, compiled_specs=compiled_specs
        )
        if classification["component_role"] != "TYPE_CURRENCY" or classification["reasons"]:
            raise _error("customer-deposit source fragment classification drifted")
        type_output, type_equations, type_receipt, reasons = _ordinary_type_view(
            table=merged_type_table,
            region=type_regions[0],
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
            row_source_axis=_fragment_row_source_axis(type_tables, type_regions),
            layout="ROW_CONTINUATION_FRAGMENTS_X_TWO_PERIOD_COLUMNS",
        )
    elif len(type_regions) == 1:
        classification = classify_gemini_json_customer_deposit_table_v1(
            type_tables[0], compiled_specs=compiled_specs
        )
        if classification["component_role"] != "TYPE_CURRENCY" or classification["reasons"]:
            raise _error("customer-deposit source fragment classification drifted")
        type_output, type_equations, type_receipt, reasons = _ordinary_type_view(
            table=type_tables[0],
            region=type_regions[0],
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
    else:
        if any(
            (
                classification := classify_gemini_json_customer_deposit_table_v1(
                    table, compiled_specs=compiled_specs
                )
            )["component_role"]
            != "TYPE_CURRENCY"
            or classification["reasons"]
            for table in type_tables
        ):
            raise _error("customer-deposit source fragment classification drifted")
        type_output, type_equations, type_receipt, reasons = _stacked_type_view(
            tables=type_tables,
            regions=type_regions,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
    type_units = (
        [type_receipt["unit_axis"].get("canonical_unit")]
        if "unit_axis" in type_receipt
        else [receipt.get("canonical_unit") for receipt in type_receipt["unit_axes"]]
    )
    mapping_unit = next(iter(set(type_units))) if len(set(type_units)) == 1 else None
    if mapping_unit not in {"MILLION_VND", "VND"}:
        reasons.append("TYPE_MAPPING_UNIT_AXIS_NOT_EXACTLY_ONE_ACCEPTED_UNIT")
    customer_output: dict[str, dict[str, Any]] = {}
    customer_equations: list[dict[str, Any]] = []
    customer_receipt = None
    if customer_regions:
        customer_tables = [
            table_by_region[canonical_json_sha256_v1(item)] for item in customer_regions
        ]
        row_continuation_customer = all(
            item.get("fragment_layout") == "ROW_CONTINUATION" for item in customer_regions
        )
        customer_table = (
            _merge_row_fragments([{"table": table} for table in customer_tables])
            if row_continuation_customer
            else customer_tables[0]
        )
        classification = classify_gemini_json_customer_deposit_table_v1(
            customer_table, compiled_specs=compiled_specs
        )
        if classification["component_role"] != "CUSTOMER_TYPE" or classification["reasons"]:
            raise _error("customer-deposit source fragment classification drifted")
        (
            proposed_customer_output,
            proposed_customer_equations,
            proposed_customer_receipt,
            customer_reasons,
        ) = _customer_view(
            table=customer_table,
            region=customer_regions[0],
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
            row_source_axis=(
                _fragment_row_source_axis(customer_tables, customer_regions)
                if row_continuation_customer
                else None
            ),
            layout=(
                "CUSTOMER_ROW_CONTINUATION_FRAGMENTS_X_TWO_PERIOD_COLUMNS"
                if row_continuation_customer
                else "CUSTOMER_ROWS_X_MONEY_AND_OPTIONAL_PERCENT_COLUMNS"
            ),
        )
        type_period = (
            type_receipt["period_axis"]["signatures"]
            if "period_axis" in type_receipt
            else [receipt["signature"] for receipt in type_receipt["period_axes"]]
        )
        if proposed_customer_receipt["period_axis"].get("signatures") != type_period:
            customer_reasons.append("CUSTOMER_AND_TYPE_PERIOD_AXES_DIFFER")
        if any(
            unit != proposed_customer_receipt["unit_axis"].get("canonical_unit")
            for unit in type_units
        ):
            customer_reasons.append("CUSTOMER_AND_TYPE_UNITS_DIFFER")
        customer_reasons = sorted(set(customer_reasons))
        if not customer_reasons and all(
            _equation_closes(equation) for equation in proposed_customer_equations
        ):
            customer_output = proposed_customer_output
            customer_equations = proposed_customer_equations
            customer_receipt = {
                **proposed_customer_receipt,
                "disposition": "INCLUDED_EXACT_OPTIONAL_CUSTOMER_VIEW",
                "rejection_reasons": [],
            }
        else:
            partial_customer_output = _partial_direct_customer_output(
                proposed_output=proposed_customer_output,
                receipt=proposed_customer_receipt,
                rejection_reasons=customer_reasons,
            )
            customer_output = partial_customer_output
            customer_receipt = {
                **proposed_customer_receipt,
                "disposition": (
                    "INCLUDED_PARTIAL_DIRECT_CUSTOMER_VIEW_WITH_SOURCE_ONLY_RESIDUAL"
                    if partial_customer_output
                    else "EXCLUDED_NONEXACT_OPTIONAL_CUSTOMER_VIEW"
                ),
                "partial_direct_roles": sorted(partial_customer_output),
                "rejection_reasons": customer_reasons,
            }
    all_output = {**type_output, **customer_output}
    duplicate_roles = set(type_output) & set(customer_output)
    if duplicate_roles:
        reasons.append("TYPE_AND_CUSTOMER_OUTPUT_ROLE_AXES_OVERLAP")
    reasons = sorted(set(reasons))
    equations = [*type_equations, *customer_equations]
    exact = (
        bool(all_output)
        and not reasons
        and all(_equation_closes(equation) for equation in equations)
    )
    mappings = []
    if exact:
        role_order = [item["role"] for item in compiled_specs["schema"]["role_bindings"]]
        for role in role_order:
            record = all_output.get(role)
            if record is None:
                continue
            mapping_values = partial_source_mapping_values_v1(record["cells"])
            if mapping_values is None:
                continue
            material = {
                "report_norm_id": compiled_specs["bindings"][role],
                "role": role,
                "row_id": (
                    record["source_refs"][0]["row_id"]
                    if len(record["source_refs"]) == 1
                    else "aggregate:" + role
                ),
                "source_refs": canonical_clone_v1(record["source_refs"]),
                "state": record["state"],
                "unit": mapping_unit,
                "values": mapping_values,
            }
            mappings.append(
                {
                    **material,
                    "item_mapping_id": "gjfcdmv1:item:" + canonical_json_sha256_v1(material),
                }
            )
    first = region_axis[0]
    structural_root_receipt = {
        "emitted_mapping": False,
        "mapping_policy": "STRUCTURAL_CONTEXT_ONLY",
        "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
        "role": compiled_specs["topology"]["parent"]["role"],
    }
    closure_receipt = {
        "customer_view": customer_receipt,
        "equations": equations,
        "query_receipt": canonical_clone_v1(expected_receipt),
        "rule": "OBSERVED_LANES_EXACT_OR_BOUNDED_BLANK_SOURCE_LANES_OMITTED_FROM_MATH",
        "structural_root_receipt": structural_root_receipt,
        "type_currency_view": type_receipt,
    }
    if "customer_deposit_source_repairs" in compiled_specs:
        repair_material = {
            "adapter_format_version": SOURCE_REPAIR_ADAPTER_FORMAT_VERSION,
            "authenticated_source_repairs": canonical_clone_v1(
                authenticated_source_repairs
            ),
            "source_repair_spec_sha256": compiled_specs.get(
                "customer_deposit_source_repair_spec_sha256"
            ),
        }
        closure_receipt["customer_deposit_source_repair_receipt"] = {
            **repair_material,
            "source_repair_receipt_id": (
                "gjfcdav1:source-repair-receipt:"
                + canonical_json_sha256_v1(repair_material)
            ),
        }
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": closure_receipt,
        "component_regions": region_axis,
        "document_id": first["document_id"],
        "family_id": compiled_specs["topology"]["family_id"],
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": READY if exact else UNRESOLVED,
        "table_id": first["table_id"],
    }
    return {
        "candidate_id": "gjfcdcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_customer_deposit_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Exact-rebuild a customer-deposit candidate from selected source JSON."""

    rebuilt = evaluate_gemini_json_customer_deposit_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, rebuilt):
        raise _error("customer-deposit candidate does not replay exactly")
    return rebuilt


def build_gemini_json_indexed_customer_deposit_query_evidence_v1(
    *,
    selected_document_axis: Sequence[dict[str, Any]],
    selected_page_axis: Sequence[dict[str, Any]],
    document_clusters: Sequence[dict[str, Any]],
    query_policy_sha256: str,
) -> dict[str, Any]:
    """Seal the complete selected document/page axis and one disposition per document."""

    documents = canonical_clone_v1(list(selected_document_axis))
    pages = canonical_clone_v1(list(selected_page_axis))
    clusters = canonical_clone_v1(list(document_clusters))
    dispositions = [
        {
            "cluster": canonical_clone_v1(cluster),
            "disposition": cluster.get("status"),
            "document_id": cluster.get("document_id"),
            "document_ordinal": cluster.get("document_ordinal"),
            "source_logical_name": cluster.get("source_logical_name"),
            "source_sha256": cluster.get("source_sha256"),
        }
        for cluster in clusters
    ]
    accepted = [
        canonical_clone_v1(cluster) for cluster in clusters if cluster.get("status") == READY
    ]
    receipt = {
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(accepted),
        "accepted_cluster_count": len(accepted),
        "accepted_fragment_count": sum(len(item.get("component_regions", [])) for item in accepted),
        "candidate_disposition_axis_sha256": canonical_json_sha256_v1(dispositions),
        "candidate_disposition_count": len(dispositions),
        "disposition_counts": {
            status: sum(item.get("disposition") == status for item in dispositions)
            for status in (READY, NOT_OBSERVED, UNRESOLVED)
        },
        "query_policy_sha256": query_policy_sha256,
        "selected_document_axis_sha256": canonical_json_sha256_v1(documents),
        "selected_document_count": len(documents),
        "selected_page_axis_sha256": canonical_json_sha256_v1(pages),
        "selected_page_count": len(pages),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            [item.get("page_json_version_id") for item in pages]
        ),
    }
    material = {
        "accepted_clusters": accepted,
        "candidate_dispositions": dispositions,
        "format_version": INDEXED_QUERY_EVIDENCE_FORMAT_VERSION,
        "query_receipt": receipt,
        "selected_document_axis": documents,
        "selected_page_axis": pages,
    }
    return {
        **material,
        "query_evidence_id": "gjficdqev1:evidence:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_indexed_customer_deposit_query_evidence_v1(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate every internal axis/hash in customer-deposit indexed evidence."""

    fields = {
        "accepted_clusters",
        "candidate_dispositions",
        "format_version",
        "query_evidence_id",
        "query_receipt",
        "selected_document_axis",
        "selected_page_axis",
    }
    if (
        compiled_specs.get("engine_format_version") != ENGINE_FORMAT_VERSION
        or type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != INDEXED_QUERY_EVIDENCE_FORMAT_VERSION
        or any(
            type(value.get(field)) is not list
            for field in (
                "accepted_clusters",
                "candidate_dispositions",
                "selected_document_axis",
                "selected_page_axis",
            )
        )
        or type(value.get("query_receipt")) is not dict
    ):
        raise _error("indexed customer-deposit query evidence is invalid")
    documents = value["selected_document_axis"]
    dispositions = value["candidate_dispositions"]
    pages = value["selected_page_axis"]
    document_fields = {
        "document_id",
        "document_ordinal",
        "source_logical_name",
        "source_sha256",
    }
    if not documents or len(documents) != len(dispositions):
        raise _error("indexed customer-deposit document disposition axis is incomplete")
    document_by_ordinal = {}
    for ordinal, document in enumerate(documents, start=1):
        if (
            type(document) is not dict
            or set(document) != document_fields
            or document.get("document_ordinal") != ordinal
            or _DOCUMENT_ID.fullmatch(document.get("document_id", "")) is None
            or type(document.get("source_logical_name")) is not str
            or not document["source_logical_name"]
            or _SHA256.fullmatch(document.get("source_sha256", "")) is None
        ):
            raise _error("indexed customer-deposit selected document axis is invalid")
        document_by_ordinal[ordinal] = document
    page_fields = document_fields | {
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
    }
    prior_document_ordinal = 0
    per_document_page_ordinal: dict[int, int] = defaultdict(int)
    page_versions = []
    for page in pages:
        document = (
            document_by_ordinal.get(page.get("document_ordinal")) if type(page) is dict else None
        )
        if (
            type(page) is not dict
            or set(page) != page_fields
            or document is None
            or any(page.get(field) != document[field] for field in document_fields)
            or _PAGE_VERSION.fullmatch(page.get("page_json_version_id", "")) is None
            or type(page.get("physical_page")) is not int
            or page["physical_page"] <= 0
            or type(page.get("selected_page_ordinal")) is not int
            or page["selected_page_ordinal"] <= 0
            or page["document_ordinal"] < prior_document_ordinal
        ):
            raise _error("indexed customer-deposit selected page axis is invalid")
        prior_document_ordinal = page["document_ordinal"]
        per_document_page_ordinal[page["document_ordinal"]] += 1
        if page["selected_page_ordinal"] != per_document_page_ordinal[page["document_ordinal"]]:
            raise _error("indexed customer-deposit selected page order is incomplete")
        page_versions.append(page["page_json_version_id"])
    if len(page_versions) != len(set(page_versions)) or set(per_document_page_ordinal) != set(
        document_by_ordinal
    ):
        raise _error("indexed customer-deposit selected page frontier is duplicate or incomplete")
    accepted_projection = []
    for ordinal, (document, disposition) in enumerate(zip(documents, dispositions, strict=True), 1):
        cluster = disposition.get("cluster") if type(disposition) is dict else None
        if (
            type(disposition) is not dict
            or set(disposition) != document_fields | {"cluster", "disposition"}
            or any(disposition.get(field) != document[field] for field in document_fields)
            or disposition.get("disposition") not in {READY, NOT_OBSERVED, UNRESOLVED}
            or type(cluster) is not dict
            or cluster.get("document_ordinal") != ordinal
            or any(cluster.get(field) != document[field] for field in document_fields)
            or cluster.get("status") != disposition["disposition"]
            or cluster.get("cluster_id")
            != "gjfcdfcv1:cluster:"
            + canonical_json_sha256_v1(
                {
                    key: canonical_clone_v1(item)
                    for key, item in cluster.items()
                    if key != "cluster_id"
                }
            )
        ):
            raise _error("indexed customer-deposit disposition cluster binding drifted")
        regions = cluster.get("component_regions")
        reasons = cluster.get("reasons")
        if (
            type(reasons) is not list
            or reasons != sorted(set(reasons))
            or any(type(reason) is not str or not reason for reason in reasons)
            or (cluster["status"] == READY and (not regions or reasons))
            or (cluster["status"] == NOT_OBSERVED and regions)
            or (cluster["status"] == UNRESOLVED and (not reasons or regions))
        ):
            raise _error("indexed customer-deposit disposition semantics drifted")
        if cluster["status"] == READY:
            checked_regions = _region_axis(regions)
            if any(
                region["document_ordinal"] != ordinal
                or region["document_id"] != document["document_id"]
                or region["source_logical_name"] != document["source_logical_name"]
                or region["source_sha256"] != document["source_sha256"]
                for region in checked_regions
            ):
                raise _error("indexed customer-deposit accepted region identity drifted")
            accepted_projection.append(cluster)
    if not same_typed_json_v1(value["accepted_clusters"], accepted_projection):
        raise _error("indexed customer-deposit accepted cluster projection drifted")
    receipt = value["query_receipt"]
    expected_receipt = {
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(accepted_projection),
        "accepted_cluster_count": len(accepted_projection),
        "accepted_fragment_count": sum(
            len(item["component_regions"]) for item in accepted_projection
        ),
        "candidate_disposition_axis_sha256": canonical_json_sha256_v1(dispositions),
        "candidate_disposition_count": len(dispositions),
        "disposition_counts": {
            status: sum(item["disposition"] == status for item in dispositions)
            for status in (READY, NOT_OBSERVED, UNRESOLVED)
        },
        "query_policy_sha256": canonical_json_sha256_v1(compiled_specs["query_policy"]),
        "selected_document_axis_sha256": canonical_json_sha256_v1(documents),
        "selected_document_count": len(documents),
        "selected_page_axis_sha256": canonical_json_sha256_v1(pages),
        "selected_page_count": len(pages),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(page_versions),
    }
    if not same_typed_json_v1(receipt, expected_receipt):
        raise _error("indexed customer-deposit query receipt drifted")
    material = {key: canonical_clone_v1(value[key]) for key in fields - {"query_evidence_id"}}
    if value["query_evidence_id"] != "gjficdqev1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("indexed customer-deposit query evidence identity drifted")
    return canonical_clone_v1(value)


def validate_gemini_json_customer_deposit_sweep_query_bindings_v1(
    *, trials: Any, indexed_query_evidence: Any, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Bind every trial and candidate to its exhaustive selected-document disposition."""

    evidence = validate_gemini_json_indexed_customer_deposit_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    documents = evidence["selected_document_axis"]
    if type(trials) is not list or len(trials) != len(documents):
        raise _error("customer-deposit sweep trial axis is incomplete")
    accepted_by_ordinal = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    for ordinal, (trial, document, disposition) in enumerate(
        zip(trials, documents, evidence["candidate_dispositions"], strict=True), start=1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("source_logical_name") != document["source_logical_name"]
            or trial.get("source_sha256") != document["source_sha256"]
            or type(trial.get("candidates")) is not list
            or trial.get("candidate_count") != len(trial["candidates"])
        ):
            raise _error("customer-deposit sweep trial identity drifted")
        if disposition["disposition"] == READY:
            cluster = accepted_by_ordinal[ordinal]
            if len(trial["candidates"]) != 1:
                raise _error("customer-deposit accepted document needs exactly one candidate")
            candidate = trial["candidates"][0]
            if not same_typed_json_v1(
                candidate.get("component_regions"), cluster["component_regions"]
            ):
                raise _error("customer-deposit candidate region binding drifted")
            if candidate.get("status") == READY:
                if (
                    trial.get("status") != READY
                    or trial.get("selected_candidate_id") != candidate.get("candidate_id")
                    or not same_typed_json_v1(trial.get("mappings"), candidate.get("mappings"))
                    or trial.get("reasons")
                ):
                    raise _error("customer-deposit READY trial binding drifted")
            elif (
                trial.get("status") != UNRESOLVED
                or trial.get("selected_candidate_id") is not None
                or trial.get("mappings")
                or trial.get("reasons") != candidate.get("reasons")
            ):
                raise _error("customer-deposit unresolved candidate binding drifted")
        elif disposition["disposition"] == NOT_OBSERVED:
            if (
                trial.get("status") != NOT_OBSERVED
                or trial["candidates"]
                or trial.get("mappings")
                or trial.get("reasons")
                or trial.get("selected_candidate_id") is not None
            ):
                raise _error("customer-deposit not-observed trial binding drifted")
        elif (
            trial.get("status") != UNRESOLVED
            or trial["candidates"]
            or trial.get("mappings")
            or trial.get("selected_candidate_id") is not None
            or trial.get("reasons") != disposition["cluster"]["reasons"]
        ):
            raise _error("customer-deposit unresolved query disposition binding drifted")
    return canonical_clone_v1(trials)
