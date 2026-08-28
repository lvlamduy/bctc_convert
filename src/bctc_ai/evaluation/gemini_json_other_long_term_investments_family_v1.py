"""Other-long-term-investment closure over selected Gemini page JSON.

Gemini remains a source reader.  The resolver inventories every declared-role
table in one document, binds one owner/reset fence, normalizes ordinary and
repeated-period layouts, and closes child/detail/provision/net equations in
deterministic code.  It contains no bank, filename, note-number, page, value or
prompt routing.
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
from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    _compile_units,
    _document_unit_context_axis,
    _money,
    _semantic_period_roles,
    _source_table,
    _two_period_axis,
    _unit_axis,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _header_dates,
    _header_text,
    _normalized,
    _period_signature,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_OTHER_LONG_TERM_INVESTMENTS_ACCOUNTING_FAMILY_V1"
INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = (
    "GEMINI_JSON_INDEXED_OTHER_LONG_TERM_INVESTMENTS_QUERY_EVIDENCE_V1"
)
EVALUATION_FORMAT_VERSION = "ACCOUNTING_OTHER_LONG_TERM_INVESTMENTS_FAMILY_EVALUATION_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_OTHER_LONG_TERM_INVESTMENTS_SCHEMA_BINDING_SPEC_V1"
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_OTHER_LONG_TERM_INVESTMENT_"
    "OWNER_OPTIONAL_CHILD_DETAIL_SUBTOTAL_PROVISION_NET_RESET_FENCE_EXACT_"
    "PERIOD_UNIT_ALL_LANE_CLOSURE_CONDITIONAL_BLANK_ZERO_SCHEMA_MAPPING_"
    "PROPOSAL_ONLY_NO_GEOMETRY_OCR_BANK_FILE_PAGE_NOTE_VALUE_PROMPT_ROUTING_"
    "BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")

_OUTPUT_ROLES = {
    "ASSOCIATE",
    "INVESTMENT_FUND",
    "JOINT_VENTURE",
    "ORGANIZATION_PROJECT",
    "OTHER_LONG_TERM",
    "PROVISION",
}
_TOP_LEVEL_ROLES = {"ASSOCIATE", "JOINT_VENTURE", "OTHER_LONG_TERM", "PROVISION"}
_DETAIL_ROLES = {"ASSOCIATE", "INVESTMENT_FUND", "JOINT_VENTURE", "ORGANIZATION_PROJECT"}
_MOVEMENT_TOKENS = (
    "so du dau nam",
    "so du dau ky",
    "tai ngay 1 thang 1",
    "trich lap trong nam",
    "hoan nhap trong nam",
    "bien dong khac",
    "so du cuoi nam",
)
_CARRYING_METRIC_TOKENS = (
    "gia tri ghi so",
    "gia tri hien tai",
    "gia tri rong cua khoan dau tu",
    "gia tri rong",
)
_FOLDED_VIETNAMESE_DATE = re.compile(
    r"(?<!\d)(?:tai\s+)?ngay\s*([0-3]?\d)\s*thang\s*([01]?\d)\s*nam\s*((?:19|20)\d{2})(?!\d)"
)


class GeminiJsonOtherLongTermInvestmentsFamilyV1Error(ValueError):
    """Selected JSON, declarative specs, or accounting closure drifted."""


def _error(message: str) -> GeminiJsonOtherLongTermInvestmentsFamilyV1Error:
    return GeminiJsonOtherLongTermInvestmentsFamilyV1Error(message)


def _aliases(child: Mapping[str, Any]) -> list[str]:
    return sorted({alias for matcher in child["matchers"] for alias in matcher["aliases"]})


def compile_gemini_json_other_long_term_investments_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile the data-only Family 17 topology/evaluation/schema triplet."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("other-long-term-investment topology spec is invalid") from exc
    evaluation_fields = {
        "blank_zero_policy",
        "closure_policy",
        "component_policy",
        "family_id",
        "format_version",
        "layout_policy",
        "money_unit_bindings",
        "period_semantics",
        "typed_control_exclusions",
    }
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec) != evaluation_fields
        or evaluation_spec.get("format_version") != EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("blank_zero_policy") != "ZERO_ONLY_AFTER_COMPLETE_EQUATION_EXACT"
        or evaluation_spec.get("closure_policy")
        != "EXACT_OPTIONAL_CHILD_DETAIL_SUBTOTAL_PROVISION_AND_NET_ALL_LANES"
        or evaluation_spec.get("component_policy")
        != "ONE_OWNER_RESET_FENCE_WITH_MAIN_TABLE_AND_OPTIONAL_DETAIL_OR_CONTINUATION_TABLES"
        or evaluation_spec.get("layout_policy")
        != "TWO_PERIOD_COLUMNS_OR_TWO_ORDERED_PERIOD_TABLES_WITH_EXACT_CARRYING_VALUE_LANE"
        or evaluation_spec.get("period_semantics") != "CURRENT_AND_COMPARATIVE_SNAPSHOT"
        or evaluation_spec.get("typed_control_exclusions")
        != [
            "PRIMARY_FINANCIAL_STATEMENT_SUMMARY",
            "PROVISION_MOVEMENT",
            "FAIR_VALUE_OR_FINANCIAL_INSTRUMENT_VIEW",
            "PERCENTAGE_ONLY_VIEW",
            "OPERATING_EXPENSE_OR_INCOME_VIEW",
            "RELATED_PARTY_TRANSACTION_OR_BALANCE_VIEW",
        ]
    ):
        raise _error("other-long-term-investment evaluation spec is invalid")
    try:
        unit_bindings, unit_binding_by_alias = _compile_units(
            evaluation_spec["money_unit_bindings"]
        )
    except ValueError as exc:
        raise _error("other-long-term-investment unit bindings are invalid") from exc

    child_by_role = {child["role"]: child for child in topology["children"]}
    if set(child_by_role) != _OUTPUT_ROLES:
        raise _error("other-long-term-investment role frontier is incomplete")
    matchers_by_role = {
        role: canonical_clone_v1(child["matchers"]) for role, child in child_by_role.items()
    }
    aliases_by_role = {role: _aliases(child) for role, child in child_by_role.items()}

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
        or schema_binding_spec.get("family_root_report_norm_id") != 862
        or schema_binding_spec.get("root_mapping_policy") != "SOURCE_VISIBLE_NET_TOTAL"
        or schema_binding_spec.get("schema_period_type") != "SNAPSHOT"
        or type(schema_binding_spec.get("role_bindings")) is not list
    ):
        raise _error("other-long-term-investment schema binding spec is invalid")
    bindings: dict[str, int] = {}
    identities = {862}
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
            raise _error("other-long-term-investment schema role binding is invalid")
        bindings[raw["role"]] = raw["report_norm_id"]
        identities.add(raw["report_norm_id"])
    if set(bindings) != _OUTPUT_ROLES:
        raise _error("other-long-term-investment schema binding frontier is incomplete")
    query_policy = {
        "hard_negative_aliases": canonical_clone_v1(topology["hard_negative_aliases"]),
        "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
        "reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
    }
    return {
        "aliases_by_role": aliases_by_role,
        "bindings": bindings,
        "claim_boundary": CLAIM_BOUNDARY,
        "child_by_role": child_by_role,
        "currency_aliases": {},
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "matchers_by_role": matchers_by_role,
        "output_role_order": [item["role"] for item in schema_binding_spec["role_bindings"]],
        "query_policy": query_policy,
        "schema": canonical_clone_v1(schema_binding_spec),
        "topology": topology,
        "unit_binding_by_alias": unit_binding_by_alias,
        "unit_bindings": unit_bindings,
    }


def _contains_alias(value: Any, alias: str) -> bool:
    text = _normalized(value)
    return bool(text and (text == alias or f" {alias} " in f" {text} "))


def _surface_dates(value: Any) -> set[date]:
    if type(value) is not str:
        return set()
    parsed = set(_header_dates(value))
    for match in _FOLDED_VIETNAMESE_DATE.finditer(_normalized(value)):
        try:
            parsed.add(date(int(match.group(3)), int(match.group(2)), int(match.group(1))))
        except ValueError:
            continue
    return parsed


def _period_heading_dates(value: Any) -> list[str]:
    folded = _normalized(value)
    if not folded.startswith("tai ngay"):
        return []
    return sorted((item.isoformat() for item in _surface_dates(value)), reverse=True)


def _matches_alias(value: Any, alias: str) -> bool:
    text = _normalized(value)
    if not text:
        return False
    if text == alias or text.startswith(alias + " "):
        return True
    tokens = text.split()
    while len(tokens) > 1 and (
        tokens[0].isdigit()
        or (len(tokens[0]) == 1 and tokens[0].isalpha())
        or tokens[0] in {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
        or tokens[0] in {"less", "tru"}
    ):
        tokens.pop(0)
    stripped = " ".join(tokens)
    return stripped == alias or stripped.startswith(alias + " ")


def _surface_axis(section: Mapping[str, Any], table: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = [section.get("title_exact"), table.get("title_exact")]
    narratives = section.get("narratives_exact")
    if type(narratives) is list:
        values.extend(narratives)
    return values


def _role_context_surface_axis(section: Mapping[str, Any], table: Mapping[str, Any]) -> list[Any]:
    """Return only surfaces that authoritatively own one table population.

    Narratives are useful owner/reset evidence, but they can contain a running
    header or prose about the preceding population.  Treating those mentions as
    the role of the current table can silently relabel a continuation.  Section
    and table titles are the bounded population context; row labels provide the
    remaining role evidence below.
    """

    return [section.get("title_exact"), table.get("title_exact")]


def _owner_visible(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> bool:
    return any(
        _contains_alias(value, alias)
        for value in _surface_axis(section, table)
        for alias in compiled_specs["query_policy"]["owner_aliases"]
    )


def _path_has_role(
    path: Any, role: str, *, label_exact: Any, compiled_specs: Mapping[str, Any]
) -> bool:
    if type(path) is not list:
        return False
    label = _normalized(label_exact)
    ancestors = [value for value in path if type(value) is str and _normalized(value) != label]
    return any(
        _matches_alias(value, alias)
        for value in ancestors
        for alias in compiled_specs["aliases_by_role"][role]
    )


def _role_match_score(
    row: Mapping[str, Any], role: str, *, compiled_specs: Mapping[str, Any]
) -> int | None:
    scores = []
    for matcher in compiled_specs["matchers_by_role"][role]:
        aliases = [
            alias for alias in matcher["aliases"] if _matches_alias(row.get("label_exact"), alias)
        ]
        if not aliases:
            continue
        within = matcher["within_role"]
        if within is None or _path_has_role(
            row.get("hierarchy_path_exact"),
            within,
            label_exact=row.get("label_exact"),
            compiled_specs=compiled_specs,
        ):
            scores.extend(len(_normalized(alias)) for alias in aliases)
    return max(scores) if scores else None


def _typed_control_disposition(
    page_json: Mapping[str, Any], section: Mapping[str, Any], table: Mapping[str, Any]
) -> str | None:
    title = " ".join(
        value
        for value in (section.get("title_exact"), table.get("title_exact"))
        if type(value) is str
    )
    folded = _normalized(title)
    rows = [row for row in table.get("rows") or [] if type(row) is dict]
    labels = [_normalized(row.get("label_exact")) for row in rows]
    columns = table.get("columns")
    if page_json.get("status") == "PRIMARY_FINANCIAL_STATEMENT" or (
        section.get("content_kind") == "PRIMARY_STATEMENT"
        and section.get("statement_type") == "BALANCE_SHEET"
    ):
        return "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
    if any(token in " ".join(labels) for token in _MOVEMENT_TOKENS):
        return "PROVISION_MOVEMENT"
    if (
        "gia tri hop ly" in folded
        or "phan loai tai san tai chinh" in folded
        or "cong cu tai chinh" in folded
    ):
        return "FAIR_VALUE_OR_FINANCIAL_INSTRUMENT_VIEW"
    if "chi phi hoat dong" in folded or "thu nhap" in folded:
        return "OPERATING_EXPENSE_OR_INCOME_VIEW"
    if "ben lien quan" in folded:
        return "RELATED_PARTY_TRANSACTION_OR_BALANCE_VIEW"
    if (
        type(columns) is list
        and not any(
            type(column) is dict and column.get("value_kind") == "MONEY" for column in columns
        )
        and any(
            type(column) is dict and column.get("value_kind") == "PERCENT" for column in columns
        )
    ):
        return "PERCENTAGE_ONLY_VIEW"
    return None


def _explicit_table_context_role(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> str | None:
    surfaces = _role_context_surface_axis(section, table)
    matched = {
        role
        for role in _DETAIL_ROLES | {"OTHER_LONG_TERM"}
        if any(
            _contains_alias(value, alias)
            for value in surfaces
            for alias in compiled_specs["aliases_by_role"][role]
        )
    }
    if len(matched) == 1:
        return next(iter(matched))
    return None


def _table_context_role(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> str | None:
    explicit = _explicit_table_context_role(section, table, compiled_specs=compiled_specs)
    if explicit is not None:
        return explicit
    rows = [row for row in table.get("rows") or [] if type(row) is dict]
    item_labels = [
        _normalized(row.get("label_exact"))
        for row in rows
        if row.get("row_kind") not in {"GROUP", "SUBTOTAL", "TOTAL"}
        and _normalized(row.get("label_exact"))
    ]
    if item_labels and any("cong ty lien doanh" in label for label in item_labels):
        return "JOINT_VENTURE"
    return None


def _table_has_period_evidence(table: Mapping[str, Any]) -> bool:
    surfaces = [table.get("title_exact")]
    columns = table.get("columns")
    if type(columns) is list:
        surfaces.extend(
            _header_text(column)
            for column in columns
            if type(column) is dict and column.get("value_kind") == "MONEY"
        )
    return any(
        type(value) is str and (bool(_surface_dates(value)) or _period_signature(value) is not None)
        for value in surfaces
    )


def _section_table_has_period_evidence(
    section: Mapping[str, Any], table: Mapping[str, Any]
) -> bool:
    if _table_has_period_evidence(table):
        return True
    narratives = section.get("narratives_exact")
    return type(narratives) is list and any(_period_heading_dates(value) for value in narratives)


def _effective_table_context_role(
    section: Mapping[str, Any],
    table_ordinal: int,
    *,
    compiled_specs: Mapping[str, Any],
) -> str | None:
    tables = section.get("tables")
    if type(tables) is not list or not 1 <= table_ordinal <= len(tables):
        return None
    active = None
    for ordinal, table in enumerate(tables[:table_ordinal], start=1):
        if type(table) is not dict:
            continue
        explicit = _explicit_table_context_role(section, table, compiled_specs=compiled_specs)
        if explicit is not None:
            active = explicit
        elif active is None:
            active = _table_context_role(section, table, compiled_specs=compiled_specs)
        elif ordinal == table_ordinal and not _table_has_period_evidence(table):
            return None
    return active


def _with_effective_table_context_role(
    classification: Mapping[str, Any],
    section: Mapping[str, Any],
    table_ordinal: int,
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    effective = _effective_table_context_role(section, table_ordinal, compiled_specs=compiled_specs)
    if effective is None or effective == classification["table_context_role"]:
        return canonical_clone_v1(classification)
    material = {
        key: canonical_clone_v1(value)
        for key, value in classification.items()
        if key != "classification_id"
    }
    material["table_context_role"] = effective
    material["table_context_role_source"] = "PRIOR_EXPLICIT_SIBLING_PERIOD_TABLE"
    return {
        **material,
        "classification_id": "gjfolticv1:classification:" + canonical_json_sha256_v1(material),
    }


def classify_gemini_json_other_long_term_investments_table_v1(
    page_json: Any,
    section: Any,
    table: Any,
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Inventory one table without assigning document-level ownership."""

    if type(page_json) is not dict or type(section) is not dict or type(table) is not dict:
        raise _error("other-long-term-investment source table is invalid")
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        raise _error("other-long-term-investment table axes are invalid")
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    role_hits = []
    ambiguous_rows = []
    anonymous_totals = []
    contextual_short_provision_rows = []
    unbound_money_rows = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict or type(row.get("values_exact")) is not list:
            continue
        values = row["values_exact"]
        visible = any(
            ordinal <= len(values) and values[ordinal - 1] is not None for ordinal in money_ordinals
        )
        scored = [
            (role, score)
            for role in _OUTPUT_ROLES
            if (score := _role_match_score(row, role, compiled_specs=compiled_specs)) is not None
        ]
        maximum = max((score for _role, score in scored), default=None)
        matched = sorted(role for role, score in scored if score == maximum)
        if len(matched) > 1:
            ambiguous_rows.append({"matched_roles": matched, "row_ordinal": row_ordinal})
        elif matched:
            role_hits.append(
                {
                    "role": matched[0],
                    "row_ordinal": row_ordinal,
                    "row_kind": row.get("row_kind"),
                    "source_order": row_ordinal,
                }
            )
        elif money_ordinals and _normalized(row.get("label_exact")) == "du phong giam gia":
            contextual_short_provision_rows.append(
                {
                    "role": "PROVISION",
                    "row_ordinal": row_ordinal,
                    "row_kind": row.get("row_kind"),
                    "source_order": row_ordinal,
                }
            )
            unbound_money_rows.append(row_ordinal)
        elif visible and row.get("row_kind") in {"SUBTOTAL", "TOTAL"}:
            anonymous_totals.append(
                {
                    "row_ordinal": row_ordinal,
                    "row_kind": row.get("row_kind"),
                    "source_order": row_ordinal,
                }
            )
        elif visible and money_ordinals:
            unbound_money_rows.append(row_ordinal)
    # A few ordinary family summaries shorten the provision label to only
    # "Dự phòng giảm giá".  That phrase is unsafe as a document-wide alias,
    # but it is an exact sibling role when the same table also declares the
    # other-long-term-investment population.  Keep this contextual rule local
    # to the sealed owner/table instead of routing by document identity.
    if any(hit["role"] == "OTHER_LONG_TERM" for hit in role_hits):
        role_hits.extend(contextual_short_provision_rows)
        short_ordinals = {item["row_ordinal"] for item in contextual_short_provision_rows}
        unbound_money_rows = [
            ordinal for ordinal in unbound_money_rows if ordinal not in short_ordinals
        ]
    typed_control = _typed_control_disposition(page_json, section, table)
    role_axis = {item["role"] for item in role_hits}
    title_axis = " ".join(
        _normalized(value)
        for value in (section.get("title_exact"), table.get("title_exact"))
        if type(value) is str
    )
    if (
        typed_control is None
        and "du phong" in title_axis
        and "PROVISION" in role_axis
        and role_axis <= {"PROVISION", "OTHER_LONG_TERM"}
    ):
        typed_control = "PROVISION_MOVEMENT"
    context_role = _table_context_role(section, table, compiled_specs=compiled_specs)
    if len(role_axis) >= 2:
        context_role = None
    material = {
        "ambiguous_rows": ambiguous_rows,
        "anonymous_totals": anonymous_totals,
        "money_column_ordinals": money_ordinals,
        "owner_visible": _owner_visible(section, table, compiled_specs=compiled_specs),
        "role_hits": role_hits,
        "table_context_role": context_role,
        "typed_control_disposition": typed_control,
        "unbound_money_row_ordinals": unbound_money_rows,
    }
    return {
        **material,
        "classification_id": "gjfolticv1:classification:" + canonical_json_sha256_v1(material),
    }


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
        raise _error("other-long-term-investment selected page records are absent")
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
            raise _error("other-long-term-investment selected page record is invalid")
        current_identity = tuple(
            raw[key]
            for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (raw["selected_page_ordinal"], raw["physical_page"])
        if identity is None:
            identity = current_identity
        elif identity != current_identity:
            raise _error("other-long-term-investment selected pages cross document identity")
        if prior is not None and position <= prior:
            raise _error("other-long-term-investment selected pages are not in source order")
        prior = position
        checked.append(canonical_clone_v1(raw))
    return checked


def _marker_matches(value: Any, aliases: Sequence[str]) -> str | None:
    matches = [alias for alias in aliases if _contains_alias(value, alias)]
    if not matches:
        return None
    maximum = max(map(len, matches))
    winners = sorted(alias for alias in matches if len(alias) == maximum)
    return winners[0] if len(winners) == 1 else None


def _heading_marker_matches(value: Any, aliases: Sequence[str]) -> str | None:
    """Match a narrative only when it is itself a structural heading."""

    matches = [alias for alias in aliases if _matches_alias(value, alias)]
    if not matches:
        return None
    maximum = max(map(len, matches))
    winners = sorted(alias for alias in matches if len(alias) == maximum)
    return winners[0] if len(winners) == 1 else None


def _region(item: Mapping[str, Any], fragment_ordinal: int) -> dict[str, Any]:
    record = item["record"]
    roles = sorted(
        {
            *(hit["role"] for hit in item["classification"]["role_hits"]),
            *(
                []
                if item["classification"]["table_context_role"] is None
                else [item["classification"]["table_context_role"]]
            ),
        }
    )
    return {
        "component_roles": roles,
        "document_id": record["document_id"],
        "document_ordinal": record["document_ordinal"],
        "fragment_ordinal": fragment_ordinal,
        "page_json_version_id": record["page_json_version_id"],
        "physical_page": record["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": record["selected_page_ordinal"],
        "source_logical_name": record["source_logical_name"],
        "source_sha256": record["source_sha256"],
        "table_id": item["table_id"],
    }


def coalesce_gemini_json_other_long_term_investments_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select exactly one exhaustive owner/reset-fenced Family 17 cluster."""

    pages = _page_record_axis(page_records)
    inventory = []
    owner_markers = []
    reset_markers = []
    boundary_aliases = sorted(
        {
            *compiled_specs["query_policy"]["reset_aliases"],
            *compiled_specs["query_policy"]["hard_negative_aliases"],
        }
    )
    for record in pages:
        page_json = record["page_json"]
        primary = page_json.get("status") == "PRIMARY_FINANCIAL_STATEMENT"
        continuation_context_role = None
        for section_ordinal, section in enumerate(page_json["sections"], start=1):
            if type(section) is not dict:
                continue
            section_id = f"s{section_ordinal}"
            position = [record["selected_page_ordinal"], section_ordinal, 0]
            for value in [section.get("title_exact")]:
                if (
                    not primary
                    and (
                        alias := _marker_matches(
                            value, compiled_specs["query_policy"]["owner_aliases"]
                        )
                    )
                    is not None
                ):
                    owner_markers.append(
                        {"alias": alias, "position": position, "source_exact": value}
                    )
                if (alias := _marker_matches(value, boundary_aliases)) is not None:
                    reset_markers.append(
                        {"alias": alias, "position": position, "source_exact": value}
                    )
            narratives = section.get("narratives_exact")
            if type(narratives) is list:
                for value in narratives:
                    if (
                        not primary
                        and (
                            alias := _heading_marker_matches(
                                value, compiled_specs["query_policy"]["owner_aliases"]
                            )
                        )
                        is not None
                    ):
                        owner_markers.append(
                            {"alias": alias, "position": position, "source_exact": value}
                        )
                    if (alias := _heading_marker_matches(value, boundary_aliases)) is not None:
                        reset_markers.append(
                            {"alias": alias, "position": position, "source_exact": value}
                        )
            section_boundary_visible = _marker_matches(
                section.get("title_exact"), boundary_aliases
            ) is not None or (
                type(narratives) is list
                and any(
                    _heading_marker_matches(value, boundary_aliases) is not None
                    for value in narratives
                )
            )
            if section_boundary_visible:
                continuation_context_role = None
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, table in enumerate(tables, start=1):
                if type(table) is not dict:
                    continue
                table_id = f"t{table_ordinal}"
                position = [record["selected_page_ordinal"], section_ordinal, table_ordinal]
                classification = classify_gemini_json_other_long_term_investments_table_v1(
                    page_json, section, table, compiled_specs=compiled_specs
                )
                classification = _with_effective_table_context_role(
                    classification,
                    section,
                    table_ordinal,
                    compiled_specs=compiled_specs,
                )
                if (
                    not classification["role_hits"]
                    and classification["table_context_role"] is None
                    and continuation_context_role is not None
                    and section.get("title_exact") is None
                    and _section_table_has_period_evidence(section, table)
                ):
                    material = {
                        key: canonical_clone_v1(value)
                        for key, value in classification.items()
                        if key != "classification_id"
                    }
                    material["table_context_role"] = continuation_context_role
                    material["table_context_role_source"] = (
                        "PRIOR_SECTION_EXPLICIT_ROLE_PERIOD_CONTINUATION"
                    )
                    classification = {
                        **material,
                        "classification_id": "gjfolticv1:classification:"
                        + canonical_json_sha256_v1(material),
                    }
                if classification["table_context_role"] is not None:
                    continuation_context_role = classification["table_context_role"]
                if classification["typed_control_disposition"] is None:
                    for value in (table.get("title_exact"),):
                        if (
                            alias := _marker_matches(
                                value, compiled_specs["query_policy"]["owner_aliases"]
                            )
                        ) is not None:
                            owner_markers.append(
                                {"alias": alias, "position": position, "source_exact": value}
                            )
                        if (alias := _marker_matches(value, boundary_aliases)) is not None:
                            reset_markers.append(
                                {"alias": alias, "position": position, "source_exact": value}
                            )
                if (
                    classification["role_hits"]
                    or classification["table_context_role"] is not None
                    or (classification["owner_visible"] and classification["anonymous_totals"])
                ):
                    inventory.append(
                        {
                            "classification": classification,
                            "position": position,
                            "record": record,
                            "section_id": section_id,
                            "table_id": table_id,
                        }
                    )

    groups: dict[tuple[int, int, int], dict[str, Any]] = {}
    for item in inventory:
        classification = item["classification"]
        if classification["typed_control_disposition"] is not None:
            continue
        prior_resets = [marker for marker in reset_markers if marker["position"] < item["position"]]
        latest_reset = (
            max(prior_resets, key=lambda marker: marker["position"]) if prior_resets else None
        )
        owners = [
            marker
            for marker in owner_markers
            if marker["position"] <= item["position"]
            and (latest_reset is None or latest_reset["position"] < marker["position"])
        ]
        if not owners:
            continue
        # Repeated running headers and per-period tables may restate the same
        # family owner.  Inside one reset-free interval those are continuation
        # evidence, not new populations.  Bind the interval to its first owner;
        # a typed reset starts a new interval and therefore a new key.
        owner = min(owners, key=lambda marker: marker["position"])
        key = tuple(owner["position"])
        groups.setdefault(key, {"items": [], "owner": owner})["items"].append(item)

    complete_groups = []
    for group in groups.values():
        items = sorted(group["items"], key=lambda item: item["position"])
        roles = {
            *(hit["role"] for item in items for hit in item["classification"]["role_hits"]),
            *(
                role
                for item in items
                if (role := item["classification"]["table_context_role"]) is not None
            ),
        }
        complete = any(
            set(combination) <= roles
            for combination in compiled_specs["topology"]["required_role_combinations"]
        )
        span = items[-1]["position"][0] - items[0]["position"][0]
        if complete and span <= compiled_specs["topology"]["limits"]["max_continuation_pages"]:
            complete_groups.append({**group, "items": items, "roles": sorted(roles)})

    reasons = []
    if len(complete_groups) > 1:
        reasons.append("MULTIPLE_COMPLETE_OWNER_CLUSTERS")
    selected = complete_groups[0] if len(complete_groups) == 1 else None
    if inventory and selected is None and not reasons:
        reasons.append("COMPLETE_OWNER_CLUSTER_NOT_RESOLVED")
    selected_keys = (
        {
            (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
            for item in selected["items"]
        }
        if selected is not None
        else set()
    )
    declared_inventory = []
    for item in inventory:
        key = (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
        if key in selected_keys:
            disposition = "SELECTED_FAMILY_COMPONENT"
        elif item["classification"]["typed_control_disposition"] is not None:
            disposition = "EXCLUDED_TYPED_CONTROL"
        else:
            disposition = "OUTSIDE_SELECTED_OWNER_FENCE_OR_INCOMPLETE_CLUSTER"
        declared_inventory.append(
            {
                "classification": canonical_clone_v1(item["classification"]),
                "disposition": disposition,
                "page_json_version_id": item["record"]["page_json_version_id"],
                "physical_page": item["record"]["physical_page"],
                "position": item["position"],
                "section_id": item["section_id"],
                "table_id": item["table_id"],
            }
        )
    regions = (
        [_region(item, ordinal) for ordinal, item in enumerate(selected["items"], start=1)]
        if selected is not None
        else []
    )
    status = READY if regions and not reasons else UNRESOLVED if inventory else NOT_OBSERVED
    material = {
        "component_regions": regions if status == READY else [],
        "declared_role_table_inventory": declared_inventory,
        "document_id": pages[0]["document_id"],
        "document_ordinal": pages[0]["document_ordinal"],
        "owner_receipt": None if selected is None else selected["owner"],
        "reasons": sorted(set(reasons)),
        "source_logical_name": pages[0]["source_logical_name"],
        "source_sha256": pages[0]["source_sha256"],
        "status": status,
    }
    return {
        **material,
        "cluster_id": "gjfoltifcv1:cluster:" + canonical_json_sha256_v1(material),
    }


def _region_axis(regions: Any) -> list[dict[str, Any]]:
    fields = {
        "component_roles",
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
    if type(regions) not in {list, tuple} or not 1 <= len(regions) <= 16:
        raise _error("other-long-term-investment region axis cardinality is invalid")
    checked = []
    identity = None
    prior = None
    for ordinal, raw in enumerate(regions, start=1):
        if (
            type(raw) is not dict
            or set(raw) != fields
            or type(raw.get("component_roles")) is not list
            or raw["component_roles"] != sorted(set(raw["component_roles"]))
            or not set(raw["component_roles"]) <= _OUTPUT_ROLES
            or _DOCUMENT_ID.fullmatch(raw.get("document_id", "")) is None
            or type(raw.get("document_ordinal")) is not int
            or raw["document_ordinal"] <= 0
            or raw.get("fragment_ordinal") != ordinal
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
            raise _error("other-long-term-investment region is invalid")
        current_identity = tuple(
            raw[key]
            for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (
            raw["selected_page_ordinal"],
            int(raw["section_id"][1:]),
            int(raw["table_id"][1:]),
        )
        if identity is None:
            identity = current_identity
        elif identity != current_identity:
            raise _error("other-long-term-investment regions cross document identity")
        if prior is not None and position <= prior:
            raise _error("other-long-term-investment regions are not in source order")
        prior = position
        checked.append(canonical_clone_v1(raw))
    return checked


def build_gemini_json_other_long_term_investments_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    checked = _region_axis(regions)
    material = {
        "component_role_axis": [item["component_roles"] for item in checked],
        "exact_fragment_axis_sha256": canonical_json_sha256_v1(checked),
        "exact_fragment_count": len(checked),
        "format_version": ("GEMINI_JSON_OTHER_LONG_TERM_INVESTMENTS_REGION_QUERY_RECEIPT_V1"),
    }
    return {
        **material,
        "query_receipt_id": "gjfoltirqrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _source_ref(
    region: Mapping[str, Any],
    row_ordinal: int,
    row: Mapping[str, Any],
    *,
    money_column_ordinals: Sequence[int],
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
        "label_exact": row.get("label_exact"),
        "locator": canonical_clone_v1(region),
        "money_column_ordinals": list(money_column_ordinals),
        "row_id": f"r{row_ordinal}",
        "row_kind": row.get("row_kind"),
        "row_ordinal": row_ordinal,
    }


def _source_money(value: Any) -> dict[str, Any]:
    try:
        return _money(value)
    except ValueError:
        if type(value) is not str:
            raise
        body = value.strip()
        if body and all(character in "-–—−_:|·." or character.isspace() for character in body):
            return {
                "coefficient": 0,
                "source_text": value,
                "state": "PUNCTUATION_PLACEHOLDER_ZERO_IF_EQUATION_EXACT",
            }
        raise


def _metric_kind(column: Mapping[str, Any]) -> str:
    header = _normalized(_header_text(column))
    if any(token in header for token in _CARRYING_METRIC_TOKENS):
        return "CARRYING_VALUE"
    if "gia goc quy doi" in header:
        return "REPORTING_CURRENCY_COST"
    if any(token in header for token in ("gia goc", "nguyen gia", "cost")):
        return "COST"
    return "GENERIC_AMOUNT"


def _select_metric_column(
    ordinals: Sequence[int], columns: Sequence[Mapping[str, Any]]
) -> tuple[int | None, list[str]]:
    carrying = [
        ordinal for ordinal in ordinals if _metric_kind(columns[ordinal - 1]) == "CARRYING_VALUE"
    ]
    if len(carrying) == 1:
        return carrying[0], []
    if len(carrying) > 1:
        return None, ["MULTIPLE_CARRYING_VALUE_COLUMNS_IN_ONE_PERIOD_LANE"]
    reporting_currency = [
        ordinal
        for ordinal in ordinals
        if _metric_kind(columns[ordinal - 1]) == "REPORTING_CURRENCY_COST"
    ]
    if len(reporting_currency) == 1:
        return reporting_currency[0], []
    if len(reporting_currency) > 1:
        return None, ["MULTIPLE_REPORTING_CURRENCY_COLUMNS_IN_ONE_PERIOD_LANE"]
    if len(ordinals) == 1:
        return ordinals[0], []
    return None, ["CARRYING_VALUE_COLUMN_NOT_UNIQUELY_RESOLVED"]


def _one_period_surface_signature(
    section: Mapping[str, Any], table: Mapping[str, Any]
) -> tuple[list[str] | None, list[str]]:
    for source_kind, value in (
        ("TABLE_TITLE", table.get("title_exact")),
        ("SECTION_TITLE", section.get("title_exact")),
    ):
        if type(value) is not str or not value.strip():
            continue
        dates = sorted(item.isoformat() for item in _surface_dates(value))
        if len(dates) > 1:
            return None, [f"MULTIPLE_PERIOD_DATES_IN_{source_kind}"]
        if len(dates) == 1:
            return ["DATE", dates[0]], []
        signature = _period_signature(value)
        if signature is not None:
            return list(signature), []
    narratives = section.get("narratives_exact")
    tables = section.get("tables")
    table_ordinal = next(
        (ordinal for ordinal, candidate in enumerate(tables or [], start=1) if candidate is table),
        None,
    )
    headings = [
        dates
        for value in (narratives if type(narratives) is list else [])
        if len(dates := _period_heading_dates(value)) == 1
    ]
    if len(headings) == 1 and type(tables) is list and len(tables) == 1:
        return ["DATE", headings[0][0]], []
    if (
        type(tables) is list
        and table_ordinal is not None
        and len(headings) == len(tables)
        and len({dates[0] for dates in headings}) == len(headings)
    ):
        return ["DATE", headings[table_ordinal - 1][0]], []
    return None, ["ONE_PERIOD_TABLE_SIGNATURE_NOT_RESOLVED"]


def _table_lane_axis(section: Mapping[str, Any], table: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve carrying-value columns for row, metric, or repeated-table layouts."""

    columns = table.get("columns")
    if type(columns) is not list:
        return {
            "complete": False,
            "lane_keys": [],
            "money_column_ordinals": [],
            "reasons": ["COLUMN_AXIS_INVALID"],
        }
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if not money_ordinals:
        return {
            "complete": False,
            "lane_keys": [],
            "money_column_ordinals": [],
            "reasons": ["MONEY_COLUMN_AXIS_EMPTY"],
        }
    ordinary = _two_period_axis(table)
    if ordinary["complete"]:
        return {
            "complete": True,
            "lane_keys": canonical_clone_v1(ordinary["signatures"]),
            "layout_kind": "TWO_PERIOD_MONEY_COLUMNS",
            "money_column_ordinals": ordinary["money_column_ordinals"],
            "reasons": [],
            "selected_metric_kinds": [
                _metric_kind(columns[ordinal - 1]) for ordinal in ordinary["money_column_ordinals"]
            ],
            "source_period_axis": ordinary,
        }

    signatures_by_ordinal: dict[int, list[str] | None] = {}
    semantic_roles_by_ordinal: dict[int, list[str]] = {}
    reasons = []
    for ordinal in money_ordinals:
        header = _header_text(columns[ordinal - 1])
        dates = sorted(item.isoformat() for item in _surface_dates(header))
        semantic_roles = _semantic_period_roles(header)
        semantic_roles_by_ordinal[ordinal] = semantic_roles
        if len(dates) > 1:
            reasons.append(f"MULTIPLE_PERIOD_DATES_IN_MONEY_COLUMN:c{ordinal}")
            signatures_by_ordinal[ordinal] = None
        elif len(semantic_roles) > 1:
            reasons.append(f"MULTIPLE_SEMANTIC_PERIOD_ROLES_IN_MONEY_COLUMN:c{ordinal}")
            signatures_by_ordinal[ordinal] = None
        elif len(dates) == 1:
            signatures_by_ordinal[ordinal] = ["DATE", dates[0]]
        else:
            signatures_by_ordinal[ordinal] = (
                None if not semantic_roles else ["SEMANTIC_ALIAS", semantic_roles[0]]
            )
    present = [signature for signature in signatures_by_ordinal.values() if signature is not None]
    identities = {tuple(signature) for signature in present}
    if not reasons and len(present) == len(money_ordinals) and len(identities) == 1:
        signature = next(iter(identities))
        selected, selection_reasons = _select_metric_column(money_ordinals, columns)
        if selected is not None and not selection_reasons:
            return {
                "complete": True,
                "lane_keys": [list(signature)],
                "layout_kind": "ONE_PERIOD_MULTI_METRIC_COLUMNS",
                "money_column_ordinals": [selected],
                "reasons": [],
                "selected_metric_kinds": [_metric_kind(columns[selected - 1])],
                "source_period_axis": {
                    "signatures_by_money_column": {
                        f"c{ordinal}": value for ordinal, value in signatures_by_ordinal.items()
                    }
                },
            }
    if not reasons and len(present) == len(money_ordinals) and len(identities) == 2:
        if all(signature[0] == "DATE" for signature in identities):
            ordered = sorted(identities, key=lambda item: date.fromisoformat(item[1]), reverse=True)
            expected_role_by_signature = {
                ordered[0]: "CURRENT_PERIOD",
                ordered[1]: "COMPARATIVE_PERIOD",
            }
            for ordinal, signature in signatures_by_ordinal.items():
                if signature is None:
                    continue
                semantic_roles = semantic_roles_by_ordinal[ordinal]
                if (
                    len(semantic_roles) == 1
                    and semantic_roles[0] != expected_role_by_signature[tuple(signature)]
                ):
                    reasons.append(f"DATE_AND_SEMANTIC_PERIOD_EVIDENCE_CONFLICT:c{ordinal}")
        elif identities == {
            ("SEMANTIC_ALIAS", "CURRENT_PERIOD"),
            ("SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"),
        }:
            ordered = [
                ("SEMANTIC_ALIAS", "CURRENT_PERIOD"),
                ("SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"),
            ]
        else:
            ordered = []
            reasons.append("PERIOD_SIGNATURE_KINDS_OR_ROLES_CONFLICT")
        selected = []
        for signature in ordered:
            ordinals = [
                ordinal
                for ordinal, value in signatures_by_ordinal.items()
                if value is not None and tuple(value) == signature
            ]
            chosen, selection_reasons = _select_metric_column(ordinals, columns)
            reasons.extend(selection_reasons)
            if chosen is not None:
                selected.append(chosen)
        if not reasons and len(selected) == 2:
            return {
                "complete": True,
                "lane_keys": [list(value) for value in ordered],
                "layout_kind": "TWO_PERIOD_MULTI_METRIC_COLUMNS",
                "money_column_ordinals": selected,
                "reasons": [],
                "selected_metric_kinds": [
                    _metric_kind(columns[ordinal - 1]) for ordinal in selected
                ],
                "source_period_axis": {
                    "signatures_by_money_column": {
                        f"c{ordinal}": value for ordinal, value in signatures_by_ordinal.items()
                    }
                },
            }
    shared_period_pairs = set()
    narratives = section.get("narratives_exact")
    if type(narratives) is list:
        for value in narratives:
            if type(value) is not str:
                continue
            folded = _normalized(value)
            narrative_dates = sorted(
                (item.isoformat() for item in _surface_dates(value)),
                key=date.fromisoformat,
                reverse=True,
            )
            if len(narrative_dates) == 2 and (" va " in f" {folded} " or " and " in f" {folded} "):
                shared_period_pairs.add(tuple(narrative_dates))
    shared_column, shared_reasons = _select_metric_column(money_ordinals, columns)
    if len(shared_period_pairs) == 1 and shared_column is not None and not shared_reasons:
        pair = next(iter(shared_period_pairs))
        return {
            "complete": True,
            "lane_keys": [["DATE", pair[0]], ["DATE", pair[1]]],
            "layout_kind": "ONE_SHARED_VALUE_FOR_TWO_EXPLICIT_PERIODS",
            "money_column_ordinals": [shared_column, shared_column],
            "reasons": [],
            "selected_metric_kinds": [
                _metric_kind(columns[shared_column - 1]),
                _metric_kind(columns[shared_column - 1]),
            ],
            "source_period_axis": {
                "shared_value_period_pair": list(pair),
                "source": "SECTION_NARRATIVE_EXPLICIT_TWO_PERIODS",
            },
        }
    if len(shared_period_pairs) > 1:
        reasons.append("MULTIPLE_SHARED_VALUE_PERIOD_PAIRS_IN_SECTION")
    signature, signature_reasons = _one_period_surface_signature(section, table)
    selected, selection_reasons = _select_metric_column(money_ordinals, columns)
    reasons.extend(signature_reasons)
    reasons.extend(selection_reasons)
    if signature is not None and selected is not None and not reasons:
        return {
            "complete": True,
            "lane_keys": [signature],
            "layout_kind": "ONE_PERIOD_CARRYING_VALUE_TABLE",
            "money_column_ordinals": [selected],
            "reasons": [],
            "selected_metric_kinds": [_metric_kind(columns[selected - 1])],
            "source_period_axis": {"signature": signature},
        }
    return {
        "complete": False,
        "lane_keys": [],
        "layout_kind": None,
        "money_column_ordinals": money_ordinals,
        "reasons": sorted(set(reasons or ordinary.get("reasons", []))),
        "source_period_axis": ordinary,
    }


def _local_record(
    role: str,
    cells: Sequence[Mapping[str, Any]],
    lane_keys: Sequence[Sequence[str]],
    source_refs: Sequence[Mapping[str, Any]],
    state: str,
    valuation_basis: str = "GENERIC_AMOUNT",
) -> dict[str, Any]:
    return {
        "cells": canonical_clone_v1(cells),
        "lane_keys": canonical_clone_v1(lane_keys),
        "role": role,
        "source_refs": canonical_clone_v1(source_refs),
        "state": state,
        "valuation_basis": valuation_basis,
    }


def _local_coefficients(record: Mapping[str, Any]) -> list[int]:
    return [cell["coefficient"] for cell in record["cells"]]


def _local_equation(
    *,
    equation_kind: str,
    components: Sequence[Mapping[str, Any]],
    result: Mapping[str, Any],
    multipliers: Sequence[int] | None = None,
) -> dict[str, Any]:
    weights = list(multipliers) if multipliers is not None else [1] * len(components)
    result_values = _local_coefficients(result)
    sums = [
        sum(
            weight * record["cells"][lane]["coefficient"]
            for record, weight in zip(components, weights, strict=True)
        )
        for lane in range(len(result_values))
    ]
    material = {
        "component_roles": [record["role"] for record in components],
        "component_source_refs": [
            canonical_clone_v1(record["source_refs"]) for record in components
        ],
        "component_sums": sums,
        "equation_kind": equation_kind,
        "lane_keys": canonical_clone_v1(result["lane_keys"]),
        "multipliers": weights,
        "result_coefficients": result_values,
        "result_role": result["role"],
        "result_source_refs": canonical_clone_v1(result["source_refs"]),
        "status": "EXACT" if sums == result_values else "MISMATCH",
    }
    return {
        **material,
        "equation_id": "gjfoltiev1:equation:" + canonical_json_sha256_v1(material),
    }


def _row_local_record(
    role: str,
    row_ordinal: int,
    row: Mapping[str, Any],
    *,
    region: Mapping[str, Any],
    lane_axis: Mapping[str, Any],
    state: str,
) -> dict[str, Any] | None:
    values = row.get("values_exact")
    if type(values) is not list:
        return None
    ordinals = lane_axis["money_column_ordinals"]
    if any(ordinal > len(values) for ordinal in ordinals):
        return None
    cells = [_source_money(values[ordinal - 1]) for ordinal in ordinals]
    metric_kinds = lane_axis.get("selected_metric_kinds", [])
    label = _normalized(row.get("label_exact"))
    if metric_kinds and all(kind == "CARRYING_VALUE" for kind in metric_kinds):
        valuation_basis = "CARRYING_VALUE"
    elif metric_kinds and all(kind == "REPORTING_CURRENCY_COST" for kind in metric_kinds):
        valuation_basis = "REPORTING_CURRENCY_COST"
    elif "gia goc" in label or (metric_kinds and all(kind == "COST" for kind in metric_kinds)):
        valuation_basis = "COST"
    else:
        valuation_basis = "GENERIC_AMOUNT"
    return _local_record(
        role,
        cells,
        lane_axis["lane_keys"],
        [
            _source_ref(
                region,
                row_ordinal,
                row,
                money_column_ordinals=ordinals,
            )
        ],
        state,
        valuation_basis,
    )


def _same_local_lane_axis(records: Sequence[Mapping[str, Any]]) -> bool:
    return bool(records) and all(
        records[0]["lane_keys"] == record["lane_keys"] for record in records
    )


def _exact_total_matches(
    components: Sequence[Mapping[str, Any]],
    totals: Sequence[Mapping[str, Any]],
    *,
    equation_kind: str,
    multipliers: Sequence[int] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    if not components or not _same_local_lane_axis(components):
        return []
    matches = []
    for total in totals:
        if total["lane_keys"] != components[0]["lane_keys"]:
            continue
        equation = _local_equation(
            equation_kind=equation_kind,
            components=components,
            result=total,
            multipliers=multipliers,
        )
        if equation["status"] == "EXACT":
            matches.append((canonical_clone_v1(total), equation))
    return matches


def _extract_table_local_records(
    *,
    page_json: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any],
) -> dict[str, Any]:
    classification = classify_gemini_json_other_long_term_investments_table_v1(
        page_json, section, table, compiled_specs=compiled_specs
    )
    classification = _with_effective_table_context_role(
        classification,
        section,
        int(region["table_id"][1:]),
        compiled_specs=compiled_specs,
    )
    if (
        not classification["role_hits"]
        and classification["table_context_role"] is None
        and len(region["component_roles"]) == 1
        and region["component_roles"][0] in _DETAIL_ROLES | {"OTHER_LONG_TERM"}
        and section.get("title_exact") is None
        and _section_table_has_period_evidence(section, table)
    ):
        material = {
            key: canonical_clone_v1(value)
            for key, value in classification.items()
            if key != "classification_id"
        }
        material["table_context_role"] = region["component_roles"][0]
        material["table_context_role_source"] = (
            "QUERY_SEALED_PRIOR_SECTION_EXPLICIT_ROLE_PERIOD_CONTINUATION"
        )
        classification = {
            **material,
            "classification_id": "gjfolticv1:classification:" + canonical_json_sha256_v1(material),
        }
    expected_roles = sorted(
        {
            *(hit["role"] for hit in classification["role_hits"]),
            *(
                []
                if classification["table_context_role"] is None
                else [classification["table_context_role"]]
            ),
        }
    )
    if expected_roles != region["component_roles"]:
        raise _error("other-long-term-investment fragment classification drifted")
    lane_axis = _table_lane_axis(section, table)
    unit_table = canonical_clone_v1(table)
    if lane_axis["complete"]:
        columns = table.get("columns")
        assert type(columns) is list
        selected_columns = []
        for ordinal in lane_axis["money_column_ordinals"]:
            column = canonical_clone_v1(columns[ordinal - 1])
            column["header_path_exact"] = [_header_text(column)]
            selected_columns.append(column)
        unit_table["columns"] = selected_columns
    unit_axis = _unit_axis(
        unit_table,
        compiled_specs=compiled_specs,
        document_unit_context=document_unit_context,
    )
    receipt = {
        "classification": classification,
        "lane_axis": lane_axis,
        "region": canonical_clone_v1(region),
        "unit_axis": unit_axis,
    }
    if not lane_axis["complete"] or not unit_axis["complete"]:
        return {
            "equations": [],
            "local_records": [],
            "receipt": receipt,
            "unconsumed_reason": (
                "FRAGMENT_PERIOD_OR_UNIT_AXIS_NOT_LOCALLY_USABLE_AS_MAPPING_EVIDENCE"
            ),
        }
    rows = table.get("rows")
    assert type(rows) is list
    hit_by_row = {hit["row_ordinal"]: hit["role"] for hit in classification["role_hits"]}
    row_records: dict[int, dict[str, Any]] = {}
    parse_reasons = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        try:
            record = _row_local_record(
                "SOURCE_ROW",
                row_ordinal,
                row,
                region=region,
                lane_axis=lane_axis,
                state="SOURCE_OBSERVED_ROW",
            )
        except ValueError:
            parse_reasons.append(f"MONEY_CELL_NOT_EXACT_INTEGER:r{row_ordinal}")
            continue
        if record is not None:
            row_records[row_ordinal] = record
    if parse_reasons:
        receipt["parse_reasons"] = sorted(set(parse_reasons))

    local_records = []
    blank_group_hits = []
    for row_ordinal, role in hit_by_row.items():
        record = row_records.get(row_ordinal)
        if record is None:
            continue
        if (
            all(cell["source_text"] is None for cell in record["cells"])
            and rows[row_ordinal - 1].get("row_kind") == "GROUP"
        ):
            blank_group_hits.append((row_ordinal, role))
            continue
        local_records.append(
            _local_record(
                role,
                record["cells"],
                record["lane_keys"],
                record["source_refs"],
                "SOURCE_OBSERVED_ROLE_ROW",
                record["valuation_basis"],
            )
        )

    anonymous_totals = []
    for item in classification["anonymous_totals"]:
        row_ordinal = item["row_ordinal"]
        record = row_records.get(row_ordinal)
        if record is not None and not all(cell["source_text"] is None for cell in record["cells"]):
            anonymous_totals.append(record)
    used_total_rows: set[int] = set()
    equations = []
    proven_roles: set[str] = set()

    all_visible_item_rows = [
        record
        for ordinal, record in row_records.items()
        if rows[ordinal - 1].get("row_kind") == "ITEM"
        and any(cell["source_text"] is not None for cell in record["cells"])
    ]
    all_item_matches = _exact_total_matches(
        all_visible_item_rows,
        anonymous_totals,
        equation_kind="EXACT_VISIBLE_ALL_ITEM_ROWS_EQUAL_TABLE_TOTAL_CONTROL",
    )
    if len(all_item_matches) == 1:
        _control_total, control_equation = all_item_matches[0]
        equations.append(control_equation)
        proven_roles.update(role for ordinal, role in hit_by_row.items() if ordinal in row_records)

    for group_ordinal, role in blank_group_hits:
        following_group = next(
            (
                ordinal
                for ordinal in range(group_ordinal + 1, len(rows) + 1)
                if type(rows[ordinal - 1]) is dict and rows[ordinal - 1].get("row_kind") == "GROUP"
            ),
            len(rows) + 1,
        )
        components = [
            record
            for ordinal, record in row_records.items()
            if group_ordinal < ordinal < following_group
            and rows[ordinal - 1].get("row_kind") == "ITEM"
            and ordinal not in hit_by_row
            and any(cell["source_text"] is not None for cell in record["cells"])
        ]
        totals = [
            record
            for record in anonymous_totals
            if group_ordinal < record["source_refs"][0]["row_ordinal"] < following_group
        ]
        matches = _exact_total_matches(
            components,
            totals,
            equation_kind="EXACT_VISIBLE_GROUP_ITEMS_EQUAL_TRAILING_SUBTOTAL",
        )
        if len(matches) == 1:
            total, equation = matches[0]
            total_row = total["source_refs"][0]["row_ordinal"]
            used_total_rows.add(total_row)
            local_records.append(
                _local_record(
                    role,
                    total["cells"],
                    total["lane_keys"],
                    total["source_refs"],
                    "SOURCE_TRAILING_TOTAL_PROVEN_AS_BLANK_GROUP_ROLE",
                    total["valuation_basis"],
                )
            )
            equations.append(equation)
            proven_roles.add(role)

    roles_present = {record["role"] for record in local_records}
    context_role = classification["table_context_role"]
    nested_records = [
        record
        for record in local_records
        if record["role"] in {"ORGANIZATION_PROJECT", "INVESTMENT_FUND"}
    ]
    inferred_context_role = context_role
    if inferred_context_role is None and nested_records:
        inferred_context_role = "OTHER_LONG_TERM"
    if inferred_context_role is not None and inferred_context_role not in roles_present:
        unbound_items = [
            record
            for ordinal, record in row_records.items()
            if rows[ordinal - 1].get("row_kind") == "ITEM"
            and ordinal not in hit_by_row
            and any(cell["source_text"] is not None for cell in record["cells"])
        ]
        component_variants = []
        if unbound_items:
            component_variants.append(("UNBOUND_DETAIL_ITEMS", unbound_items))
        if nested_records:
            component_variants.append(("DECLARED_NESTED_ROLES", nested_records))
        context_matches = []
        for kind, components in component_variants:
            totals = [
                record
                for record in anonymous_totals
                if record["source_refs"][0]["row_ordinal"] not in used_total_rows
            ]
            for total, equation in _exact_total_matches(
                components,
                totals,
                equation_kind=f"EXACT_{kind}_EQUAL_CONTEXT_ROLE_TOTAL",
            ):
                context_matches.append((total, equation))
        unique_matches = {
            (
                match[0]["source_refs"][0]["row_ordinal"],
                tuple(_local_coefficients(match[0])),
            ): match
            for match in context_matches
        }
        if len(unique_matches) == 1:
            total, equation = next(iter(unique_matches.values()))
            used_total_rows.add(total["source_refs"][0]["row_ordinal"])
            local_records.append(
                _local_record(
                    inferred_context_role,
                    total["cells"],
                    total["lane_keys"],
                    total["source_refs"],
                    "SOURCE_TOTAL_PROVEN_AS_CONTEXT_ROLE",
                    total["valuation_basis"],
                )
            )
            equations.append(equation)
            proven_roles.update({inferred_context_role, *equation["component_roles"]})

    top_records_by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in local_records:
        if record["role"] in _TOP_LEVEL_ROLES:
            top_records_by_role[record["role"]].append(record)
    top_records = [values[0] for values in top_records_by_role.values() if len(values) == 1]
    non_provision = [record for record in top_records if record["role"] != "PROVISION"]
    remaining_totals = [
        record
        for record in anonymous_totals
        if record["source_refs"][0]["row_ordinal"] not in used_total_rows
    ]
    if non_provision and remaining_totals:
        gross_variants = [
            ("EXACT_VISIBLE_FAMILY_GROSS_TOTAL", non_provision, [1] * len(non_provision))
        ]
        net_variants = []
        provision = next((record for record in top_records if record["role"] == "PROVISION"), None)
        if provision is not None:
            net_variants.extend(
                [
                    (
                        "EXACT_VISIBLE_FAMILY_NET_WITH_SOURCE_SIGNED_PROVISION",
                        [*non_provision, provision],
                        [*([1] * len(non_provision)), 1],
                    ),
                    (
                        "EXACT_VISIBLE_FAMILY_NET_LESS_POSITIVE_PROVISION",
                        [*non_provision, provision],
                        [*([1] * len(non_provision)), -1],
                    ),
                ]
            )
        gross_matches = []
        for kind, components, multipliers in gross_variants:
            for total, equation in _exact_total_matches(
                components,
                remaining_totals,
                equation_kind=kind,
                multipliers=multipliers,
            ):
                gross_matches.append((total, equation))
        net_matches = []
        provision_row_ordinal = (
            None if provision is None else provision["source_refs"][0]["row_ordinal"]
        )
        for kind, components, multipliers in net_variants:
            for total, equation in _exact_total_matches(
                components,
                remaining_totals,
                equation_kind=kind,
                multipliers=multipliers,
            ):
                if (
                    provision_row_ordinal is not None
                    and total["source_refs"][0]["row_ordinal"] > provision_row_ordinal
                ):
                    net_matches.append((total, equation))
        # A table may expose both a gross subtotal and a final net total.  Once
        # a provision row exists, only the provision-inclusive equation is an
        # authoritative root mapping; the gross subtotal remains a control and
        # must not make the net row ambiguous.
        matches = net_matches if provision is not None else gross_matches
        unique_matches = {
            (
                match[0]["source_refs"][0]["row_ordinal"],
                tuple(_local_coefficients(match[0])),
            ): match
            for match in matches
        }
        if len(unique_matches) == 1:
            total, equation = next(iter(unique_matches.values()))
            local_records.append(
                _local_record(
                    "NET_TOTAL",
                    total["cells"],
                    total["lane_keys"],
                    total["source_refs"],
                    "SOURCE_VISIBLE_FAMILY_TOTAL_PROVEN_BY_EXACT_EQUATION",
                    total["valuation_basis"],
                )
            )
            equations.append(equation)
            proven_roles.update({"NET_TOTAL", *equation["component_roles"]})

    return {
        "equations": equations,
        "local_records": local_records,
        "proven_roles": sorted(proven_roles),
        "receipt": receipt,
        "unconsumed_reason": None,
    }


def _canonical_lane_role(lane_key: Sequence[str], *, ordered_dates: Sequence[str]) -> str | None:
    if list(lane_key) == ["SEMANTIC_ALIAS", "CURRENT_PERIOD"]:
        return "CURRENT_PERIOD"
    if list(lane_key) == ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"]:
        return "COMPARATIVE_PERIOD"
    if len(lane_key) == 2 and lane_key[0] == "DATE":
        if ordered_dates and lane_key[1] == ordered_dates[0]:
            return "CURRENT_PERIOD"
        if len(ordered_dates) == 2 and lane_key[1] == ordered_dates[1]:
            return "COMPARATIVE_PERIOD"
    return None


def _observation_priority(item: Mapping[str, Any]) -> tuple[int, int, int]:
    basis_priority = {
        "COST": 0,
        "REPORTING_CURRENCY_COST": 1,
        "GENERIC_AMOUNT": 2,
        "CARRYING_VALUE": 3,
    }
    state = item["state"]
    identity_priority = {
        "SOURCE_TOTAL_PROVEN_AS_CONTEXT_ROLE": 1,
        "SOURCE_TRAILING_TOTAL_PROVEN_AS_BLANK_GROUP_ROLE": 2,
        "SOURCE_OBSERVED_ROLE_ROW": 3,
    }.get(state, 0)
    return (
        identity_priority,
        basis_priority[item["valuation_basis"]],
        int("PROVEN" in state or "CORROBORATED" in state),
    )


def _global_records(
    local_records: Sequence[Mapping[str, Any]], *, proven_roles: set[str]
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[str]]:
    dates = sorted(
        {
            lane_key[1]
            for record in local_records
            for lane_key in record["lane_keys"]
            if lane_key[0] == "DATE"
        },
        key=date.fromisoformat,
        reverse=True,
    )
    reasons = []
    if len(dates) > 2:
        reasons.append("DOCUMENT_MAPPING_PERIOD_AXIS_HAS_MORE_THAN_TWO_DATES")
    observations: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for record in local_records:
        for lane_key, cell in zip(record["lane_keys"], record["cells"], strict=True):
            lane_role = _canonical_lane_role(lane_key, ordered_dates=dates)
            if lane_role is None:
                continue
            observations[record["role"]][lane_role].append(
                {
                    "cell": canonical_clone_v1(cell),
                    "source_refs": canonical_clone_v1(record["source_refs"]),
                    "state": record["state"],
                    "valuation_basis": record["valuation_basis"],
                }
            )
    records = {}
    partial = []
    for role, by_lane in observations.items():
        cells = []
        source_refs = []
        states = []
        missing = []
        for lane_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
            values = by_lane.get(lane_role, [])
            if not values:
                missing.append(lane_role)
                continue
            coefficients = {item["cell"]["coefficient"] for item in values}
            if len(coefficients) > 1 and role == "PROVISION":
                absolute = {abs(value) for value in coefficients}
                negative = [item for item in values if item["cell"]["coefficient"] < 0]
                if len(absolute) == 1 and negative:
                    selected = negative[0]
                else:
                    reasons.append(f"CONFLICTING_SOURCE_VALUES_FOR_ROLE_LANE:{role}:{lane_role}")
                    continue
            elif len(coefficients) == 1:
                selected = values[0]
            else:
                maximum = max(_observation_priority(item) for item in values)
                preferred = [item for item in values if _observation_priority(item) == maximum]
                preferred_coefficients = {item["cell"]["coefficient"] for item in preferred}
                if len(preferred_coefficients) == 1:
                    selected = preferred[0]
                else:
                    reasons.append(f"CONFLICTING_SOURCE_VALUES_FOR_ROLE_LANE:{role}:{lane_role}")
                    continue
            cells.append(canonical_clone_v1(selected["cell"]))
            states.append(selected["state"])
            for item in values:
                if item["cell"]["coefficient"] == selected["cell"]["coefficient"]:
                    source_refs.extend(canonical_clone_v1(item["source_refs"]))
        if missing:
            partial.append({"missing_lanes": missing, "role": role})
            continue
        if len(cells) != 2:
            continue
        if any(cell["state"].endswith("ZERO_IF_EQUATION_EXACT") for cell in cells):
            if role not in proven_roles:
                reasons.append(f"UNPROVEN_BLANK_ZERO_IN_MAPPING_ROLE:{role}")
            else:
                for cell in cells:
                    if cell["state"].endswith("ZERO_IF_EQUATION_EXACT"):
                        cell["state"] = "INFERRED_" + cell["state"]
        state = states[0] if len(set(states)) == 1 else "CORROBORATED_MULTI_SOURCE_PRESENTATIONS"
        records[role] = {
            "cells": cells,
            "role": role,
            "source_refs": source_refs,
            "state": state,
        }
    return records, partial, sorted(set(reasons))


def evaluate_gemini_json_other_long_term_investments_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one owner-bound optional-child/detail/net Family 17 cluster."""

    region_axis = _region_axis(regions)
    expected_receipt = build_gemini_json_other_long_term_investments_region_query_receipt_v1(
        region_axis
    )
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected_receipt):
        raise _error("other-long-term-investment query receipt does not bind exact fragments")
    document_unit_context = _document_unit_context_axis(
        page_json_by_version, compiled_specs=compiled_specs
    )
    local_records = []
    equations = []
    proven_roles: set[str] = set()
    table_receipts = []
    unused_fragments = []
    for region in region_axis:
        page_json = page_json_by_version.get(region["page_json_version_id"])
        if type(page_json) is not dict:
            raise _error("other-long-term-investment selected page JSON is absent")
        section, table = _source_table(
            page_json, section_id=region["section_id"], table_id=region["table_id"]
        )
        extracted = _extract_table_local_records(
            page_json=page_json,
            section=section,
            table=table,
            region=region,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
        local_records.extend(extracted["local_records"])
        equations.extend(extracted["equations"])
        proven_roles.update(extracted.get("proven_roles", []))
        table_receipts.append(extracted["receipt"])
        if extracted["unconsumed_reason"] is not None:
            unused_fragments.append(
                {
                    "reason": extracted["unconsumed_reason"],
                    "region": canonical_clone_v1(region),
                }
            )
    records, partial_roles, reasons = _global_records(local_records, proven_roles=proven_roles)
    reasons.extend(item["reason"] for item in unused_fragments)
    if not any(role in records for role in _OUTPUT_ROLES):
        reasons.append("MAPPABLE_CHILD_ROLE_FRONTIER_IS_EMPTY")
    mappings = []
    if not reasons:
        for role in [*compiled_specs["output_role_order"], "NET_TOTAL"]:
            record = records.get(role)
            if record is None:
                continue
            report_norm_id = (
                compiled_specs["schema"]["family_root_report_norm_id"]
                if role == "NET_TOTAL"
                else compiled_specs["bindings"][role]
            )
            material = {
                "report_norm_id": report_norm_id,
                "role": role,
                "row_id": (
                    record["source_refs"][0]["row_id"]
                    if len(record["source_refs"]) == 1
                    else "corroborated:" + role
                ),
                "source_refs": canonical_clone_v1(record["source_refs"]),
                "state": record["state"],
                "unit": "MILLION_VND",
                "values": canonical_clone_v1(record["cells"]),
            }
            mappings.append(
                {
                    **material,
                    "item_mapping_id": "gjfoltimv1:item:" + canonical_json_sha256_v1(material),
                }
            )
    first = region_axis[0]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": {
            "document_unit_context": document_unit_context,
            "equations": equations,
            "partial_role_observations": partial_roles,
            "query_receipt": canonical_clone_v1(expected_receipt),
            "rule": "EXACT_OPTIONAL_CHILD_DETAIL_SUBTOTAL_PROVISION_AND_NET_ALL_LANES",
            "structural_root_receipt": {
                "emitted_mapping": "NET_TOTAL" in records and not reasons,
                "mapping_policy": compiled_specs["schema"]["root_mapping_policy"],
                "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
                "role": compiled_specs["topology"]["parent"]["role"],
            },
            "table_receipts": table_receipts,
            "unused_typed_fragments": unused_fragments,
        },
        "component_regions": region_axis,
        "document_id": first["document_id"],
        "family_id": compiled_specs["topology"]["family_id"],
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": sorted(set(reasons)),
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": READY if mappings and not reasons else UNRESOLVED,
        "table_id": first["table_id"],
    }
    return {
        "candidate_id": "gjfolticv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_other_long_term_investments_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    rebuilt = evaluate_gemini_json_other_long_term_investments_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, rebuilt):
        raise _error("other-long-term-investment candidate does not replay exactly")
    return rebuilt


def build_gemini_json_indexed_other_long_term_investments_query_evidence_v1(
    *,
    selected_document_axis: Sequence[dict[str, Any]],
    selected_page_axis: Sequence[dict[str, Any]],
    document_clusters: Sequence[dict[str, Any]],
    query_policy_sha256: str,
) -> dict[str, Any]:
    """Seal the exhaustive selected-frontier Family 17 query projection."""

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
    accepted = [cluster for cluster in clusters if cluster.get("status") == READY]
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
        "query_evidence_id": "gjfoltieqv1:evidence:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_indexed_other_long_term_investments_query_evidence_v1(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the complete indexed document/page/disposition closure."""

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
        raise _error("indexed other-long-term-investment query evidence is invalid")
    documents = value["selected_document_axis"]
    pages = value["selected_page_axis"]
    dispositions = value["candidate_dispositions"]
    document_fields = {
        "document_id",
        "document_ordinal",
        "source_logical_name",
        "source_sha256",
    }
    if not documents or len(documents) != len(dispositions):
        raise _error("indexed other-long-term-investment document axis is incomplete")
    by_ordinal = {}
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
            raise _error("indexed other-long-term-investment document axis is invalid")
        by_ordinal[ordinal] = document
    page_fields = document_fields | {
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
    }
    per_document = defaultdict(int)
    page_versions = []
    prior_document = 0
    for page in pages:
        document = by_ordinal.get(page.get("document_ordinal")) if type(page) is dict else None
        if (
            type(page) is not dict
            or set(page) != page_fields
            or document is None
            or any(page.get(field) != document[field] for field in document_fields)
            or _PAGE_VERSION.fullmatch(page.get("page_json_version_id", "")) is None
            or type(page.get("physical_page")) is not int
            or page["physical_page"] <= 0
            or page["document_ordinal"] < prior_document
        ):
            raise _error("indexed other-long-term-investment page axis is invalid")
        prior_document = page["document_ordinal"]
        per_document[page["document_ordinal"]] += 1
        if page.get("selected_page_ordinal") != per_document[page["document_ordinal"]]:
            raise _error("indexed other-long-term-investment page order is incomplete")
        page_versions.append(page["page_json_version_id"])
    if len(page_versions) != len(set(page_versions)) or set(per_document) != set(by_ordinal):
        raise _error("indexed other-long-term-investment page frontier is incomplete")
    accepted = []
    for ordinal, (document, disposition) in enumerate(
        zip(documents, dispositions, strict=True), start=1
    ):
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
            != "gjfoltifcv1:cluster:"
            + canonical_json_sha256_v1(
                {key: item for key, item in cluster.items() if key != "cluster_id"}
            )
        ):
            raise _error("indexed other-long-term-investment cluster binding drifted")
        regions = cluster.get("component_regions")
        reasons = cluster.get("reasons")
        if (
            type(reasons) is not list
            or reasons != sorted(set(reasons))
            or (cluster["status"] == READY and (not regions or reasons))
            or (cluster["status"] == NOT_OBSERVED and regions)
            or (cluster["status"] == UNRESOLVED and (not reasons or regions))
        ):
            raise _error("indexed other-long-term-investment disposition drifted")
        if cluster["status"] == READY:
            _region_axis(regions)
            accepted.append(cluster)
    if not same_typed_json_v1(value["accepted_clusters"], accepted):
        raise _error("indexed other-long-term-investment accepted projection drifted")
    expected_receipt = {
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(accepted),
        "accepted_cluster_count": len(accepted),
        "accepted_fragment_count": sum(len(item["component_regions"]) for item in accepted),
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
    if not same_typed_json_v1(value["query_receipt"], expected_receipt):
        raise _error("indexed other-long-term-investment query receipt drifted")
    material = {key: canonical_clone_v1(value[key]) for key in fields - {"query_evidence_id"}}
    if value["query_evidence_id"] != "gjfoltieqv1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("indexed other-long-term-investment evidence identity drifted")
    return canonical_clone_v1(value)


def validate_gemini_json_other_long_term_investments_sweep_query_bindings_v1(
    *, trials: Any, indexed_query_evidence: Any, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Bind every sweep trial to its exhaustive query disposition."""

    evidence = validate_gemini_json_indexed_other_long_term_investments_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    documents = evidence["selected_document_axis"]
    if type(trials) is not list or len(trials) != len(documents):
        raise _error("other-long-term-investment sweep trial axis is incomplete")
    accepted = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
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
            raise _error("other-long-term-investment sweep trial identity drifted")
        if disposition["disposition"] == READY:
            if len(trial["candidates"]) != 1:
                raise _error("accepted other-long-term-investment needs one candidate")
            candidate = trial["candidates"][0]
            if not same_typed_json_v1(
                candidate.get("component_regions"), accepted[ordinal]["component_regions"]
            ):
                raise _error("other-long-term-investment candidate regions drifted")
            if candidate.get("status") == READY:
                if (
                    trial.get("status") != READY
                    or trial.get("selected_candidate_id") != candidate.get("candidate_id")
                    or not same_typed_json_v1(trial.get("mappings"), candidate.get("mappings"))
                    or trial.get("reasons")
                ):
                    raise _error("other-long-term-investment READY trial drifted")
            elif (
                trial.get("status") != UNRESOLVED
                or trial.get("selected_candidate_id") is not None
                or trial.get("mappings")
                or trial.get("reasons") != candidate.get("reasons")
            ):
                raise _error("other-long-term-investment unresolved candidate drifted")
        elif disposition["disposition"] == NOT_OBSERVED:
            if (
                trial.get("status") != NOT_OBSERVED
                or trial["candidates"]
                or trial.get("mappings")
                or trial.get("reasons")
                or trial.get("selected_candidate_id") is not None
            ):
                raise _error("other-long-term-investment not-observed trial drifted")
        elif (
            trial.get("status") != UNRESOLVED
            or trial["candidates"]
            or trial.get("mappings")
            or trial.get("selected_candidate_id") is not None
            or trial.get("reasons") != disposition["cluster"]["reasons"]
        ):
            raise _error("other-long-term-investment unresolved disposition drifted")
    return canonical_clone_v1(trials)
