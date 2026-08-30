"""Generic categorical-row by period-column matrices from Gemini page JSON.

Gemini remains a structure reader.  This primitive owns the deterministic
category vocabulary, exhaustive population census, period/date resolution,
rate-denominator interpretation and numeric projection.  It is intentionally
free of bank, filename, page, note-number and expected-value routing.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

MATRIX_KIND = "CATEGORICAL_PERIOD_MATRIX"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_EXPLICIT_OWNER_RESET_FENCED_EXHAUSTIVE_"
    "CATEGORICAL_ROWS_TWO_PERIOD_COLUMNS_DECLARATIVE_MAPPED_AND_SOURCE_ONLY_"
    "CATEGORY_INVENTORY_TYPED_DATE_OR_DOCUMENT_BOUND_RELATIVE_PERIODS_LOCAL_"
    "RATE_DENOMINATOR_AND_DECIMAL_NORMALIZATION_STRUCTURAL_ROOT_SCHEMA_MAPPING_"
    "PROPOSAL_ONLY_NO_PROMPT_MAPPING_OCR_GEOMETRY_BANK_FILE_PAGE_NOTE_VALUE_"
    "ROUTING_EQUATION_BACKSOLVE_OR_EXPORT_AUTHORITY"
)
CANONICAL_RATE_UNIT = "VND_HUNDREDTHS_PER_FOREIGN_CURRENCY_UNIT"
_DATE_ROLES = {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}


class GeminiJsonCategoricalPeriodMatrixV1Error(ValueError):
    """The declarative policy or categorical source graph drifted."""


def _error(message: str) -> GeminiJsonCategoricalPeriodMatrixV1Error:
    return GeminiJsonCategoricalPeriodMatrixV1Error(message)


def _engine() -> Any:
    from bctc_ai.evaluation import gemini_json_equity_matrix_accounting_family_v1

    return gemini_json_equity_matrix_accounting_family_v1


def _compile_alias_map(value: Any, *, label: str) -> dict[str, list[str]]:
    engine = _engine()
    if type(value) is not dict or not value:
        raise _error(f"categorical-period {label} aliases are absent")
    result: dict[str, list[str]] = {}
    seen = set()
    for role, aliases in value.items():
        if (
            type(role) is not str
            or not role
            or type(aliases) is not list
            or not aliases
            or any(type(alias) is not str or not alias.strip() for alias in aliases)
        ):
            raise _error(f"categorical-period {label} alias declaration is invalid")
        normalized = [engine._normalized(alias) for alias in aliases]
        if any(not alias or alias in seen for alias in normalized):
            raise _error(f"categorical-period {label} aliases collide")
        seen.update(normalized)
        result[role] = canonical_clone_v1(aliases)
    return result


def compile_gemini_json_categorical_period_matrix_specs_v1(
    *, topology: Mapping[str, Any], evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile one strict categorical-row/two-period-column family."""

    engine = _engine()
    expected_evaluation_fields = {
        "blank_zero_policy",
        "closure_policy",
        "family_id",
        "format_version",
        "matrix_policy",
    }
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec) != expected_evaluation_fields
        or evaluation_spec.get("format_version") != engine.EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("blank_zero_policy") != "NO_BLANK_OR_DERIVED_RATE_VALUES"
        or evaluation_spec.get("closure_policy")
        != "EXHAUSTIVE_CATEGORY_ROWS_EXACT_TWO_PERIOD_VALUE_COVERAGE"
    ):
        raise _error("categorical-period evaluation spec is invalid")
    policy = evaluation_spec["matrix_policy"]
    policy_fields = {
        "accepted_orientations",
        "accepted_value_kinds",
        "canonical_rate_unit",
        "comparative_period_aliases",
        "current_period_aliases",
        "incidental_amount_scale_aliases",
        "matrix_kind",
        "max_continuation_pages",
        "minimum_mapped_category_roles",
        "numeric_scale_power10",
        "source_only_category_aliases",
    }
    if (
        type(policy) is not dict
        or set(policy) != policy_fields
        or policy.get("matrix_kind") != MATRIX_KIND
        or policy.get("accepted_orientations") != ["CATEGORY_ROWS_PERIOD_COLUMNS"]
        or policy.get("canonical_rate_unit") != CANONICAL_RATE_UNIT
        or policy.get("max_continuation_pages") not in {0, 1}
        or type(policy.get("minimum_mapped_category_roles")) is not int
        or policy["minimum_mapped_category_roles"] < 2
        or policy.get("numeric_scale_power10") != 2
        or type(policy.get("accepted_value_kinds")) is not list
        or not policy["accepted_value_kinds"]
        or set(policy["accepted_value_kinds"]) - {"MONEY", "COUNT", "UNKNOWN"}
    ):
        raise _error("categorical-period matrix policy is invalid")
    mapped_aliases = engine._aliases_by_role(topology)
    source_only_aliases = _compile_alias_map(
        policy["source_only_category_aliases"], label="source-only category"
    )
    current_aliases = policy["current_period_aliases"]
    comparative_aliases = policy["comparative_period_aliases"]
    incidental_aliases = policy["incidental_amount_scale_aliases"]
    for label, aliases in (
        ("current period", current_aliases),
        ("comparative period", comparative_aliases),
        ("incidental amount scale", incidental_aliases),
    ):
        if (
            type(aliases) is not list
            or not aliases
            or any(type(alias) is not str or not alias.strip() for alias in aliases)
            or len({engine._normalized(alias) for alias in aliases}) != len(aliases)
        ):
            raise _error(f"categorical-period {label} aliases are invalid")
    mapped_tokens = {
        engine._normalized(alias) for aliases in mapped_aliases.values() for alias in aliases
    }
    source_tokens = {
        engine._normalized(alias) for aliases in source_only_aliases.values() for alias in aliases
    }
    if mapped_tokens & source_tokens:
        raise _error("mapped and source-only categorical aliases collide")

    schema_fields = {
        "category_role_bindings",
        "family_id",
        "family_root_report_norm_id",
        "format_version",
    }
    if (
        type(schema_binding_spec) is not dict
        or set(schema_binding_spec) != schema_fields
        or schema_binding_spec.get("format_version") != engine.SCHEMA_FORMAT_VERSION
        or schema_binding_spec.get("family_id") != topology["family_id"]
        or type(schema_binding_spec.get("family_root_report_norm_id")) is not int
        or schema_binding_spec["family_root_report_norm_id"] <= 0
        or type(schema_binding_spec.get("category_role_bindings")) is not list
        or len(schema_binding_spec["category_role_bindings"]) != len(mapped_aliases)
    ):
        raise _error("categorical-period schema binding spec is invalid")
    bindings: dict[str, int] = {}
    report_norm_ids = {schema_binding_spec["family_root_report_norm_id"]}
    for item in schema_binding_spec["category_role_bindings"]:
        if (
            type(item) is not dict
            or set(item) != {"report_norm_id", "role"}
            or item.get("role") not in mapped_aliases
            or item["role"] in bindings
            or type(item.get("report_norm_id")) is not int
            or item["report_norm_id"] <= 0
            or item["report_norm_id"] in report_norm_ids
        ):
            raise _error("categorical-period category binding is invalid")
        bindings[item["role"]] = item["report_norm_id"]
        report_norm_ids.add(item["report_norm_id"])
    if set(bindings) != set(mapped_aliases):
        raise _error("categorical-period category binding axis is incomplete")
    query_policy = {
        "hard_negative_aliases": canonical_clone_v1(topology["hard_negative_aliases"]),
        "matrix_kind": MATRIX_KIND,
        "max_continuation_pages": policy["max_continuation_pages"],
        "minimum_mapped_category_roles": policy["minimum_mapped_category_roles"],
        "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
        "reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
    }
    return {
        "aliases_by_role": mapped_aliases,
        "canonical_rate_unit": CANONICAL_RATE_UNIT,
        "category_report_norm_id_by_role": bindings,
        "claim_boundary": CLAIM_BOUNDARY,
        "comparative_period_aliases": canonical_clone_v1(comparative_aliases),
        "current_period_aliases": canonical_clone_v1(current_aliases),
        "engine_format_version": engine.ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "family_id": topology["family_id"],
        "family_root_report_norm_id": schema_binding_spec["family_root_report_norm_id"],
        "incidental_amount_scale_aliases": canonical_clone_v1(incidental_aliases),
        "query_policy": query_policy,
        "schema": canonical_clone_v1(schema_binding_spec),
        "source_only_aliases_by_role": source_only_aliases,
        "topology": canonical_clone_v1(topology),
        "exchange_rate_mode": True,
    }


def _alias_matches(surface: Any, aliases_by_role: Mapping[str, Sequence[str]]) -> list[str]:
    engine = _engine()
    folded = engine._normalized(surface)
    if not folded:
        return []
    matches = []
    for role, aliases in aliases_by_role.items():
        if any(
            re.search(
                rf"(?<![a-z0-9]){re.escape(engine._normalized(alias))}(?![a-z0-9])",
                folded,
            )
            for alias in aliases
        ):
            matches.append(role)
    return sorted(matches)


def _period_alias_matches(surface: str, *, compiled_specs: Mapping[str, Any]) -> list[str]:
    engine = _engine()
    folded = engine._normalized(surface)
    result = []
    if any(
        re.search(rf"(?<![a-z0-9]){re.escape(engine._normalized(alias))}(?![a-z0-9])", folded)
        for alias in compiled_specs["current_period_aliases"]
    ):
        result.append("CURRENT_PERIOD")
    if any(
        re.search(rf"(?<![a-z0-9]){re.escape(engine._normalized(alias))}(?![a-z0-9])", folded)
        for alias in compiled_specs["comparative_period_aliases"]
    ):
        result.append("COMPARATIVE_PERIOD")
    return result


def classify_gemini_json_categorical_period_matrix_table_v1(
    table: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Inventory every category and period marker without using value routing."""

    engine = _engine()
    rows = table.get("rows") if type(table) is dict else None
    columns = table.get("columns") if type(table) is dict else None
    if type(rows) is not list or type(columns) is not list or not rows or not columns:
        raise _error("categorical-period table axes are invalid")
    if any(
        type(row) is not dict
        or type(row.get("values_exact")) is not list
        or len(row["values_exact"]) != len(columns)
        or type(row.get("hierarchy_path_exact")) is not list
        for row in rows
    ) or any(type(column) is not dict for column in columns):
        raise _error("categorical-period source vectors are invalid")
    reasons = []
    column_axis = []
    for ordinal, column in enumerate(columns, start=1):
        members = engine._header_members(column)
        dates = sorted(
            {item.isoformat() for member in members for item in engine._header_dates(member)}
        )
        semantic_roles = sorted(
            {
                role
                for member in members
                for role in _period_alias_matches(member, compiled_specs=compiled_specs)
            }
        )
        if len(dates) > 1:
            reasons.append("PERIOD_COLUMN_HAS_MULTIPLE_VISIBLE_DATES")
        if len(semantic_roles) > 1:
            reasons.append("PERIOD_COLUMN_HAS_CONFLICTING_SEMANTIC_ROLES")
        if (
            column.get("value_kind")
            not in compiled_specs["evaluation"]["matrix_policy"]["accepted_value_kinds"]
        ):
            reasons.append("PERIOD_COLUMN_VALUE_KIND_NOT_RATE_COMPATIBLE")
        column_axis.append(
            {
                "column_id": f"c{ordinal}",
                "date_axis": dates,
                "header_path_exact": canonical_clone_v1(members),
                "semantic_role_matches": semantic_roles,
                "source_order": ordinal,
                "value_kind": column.get("value_kind"),
            }
        )
    if len(columns) != 2:
        reasons.append("CATEGORICAL_PERIOD_MATRIX_REQUIRES_EXACTLY_TWO_COLUMNS")

    row_axis = []
    mapped_roles = []
    source_only_roles = []
    for ordinal, row in enumerate(rows, start=1):
        mapped_matches = _alias_matches(row.get("label_exact"), compiled_specs["aliases_by_role"])
        source_matches = _alias_matches(
            row.get("label_exact"), compiled_specs["source_only_aliases_by_role"]
        )
        matches = [
            *(f"MAPPED:{role}" for role in mapped_matches),
            *(f"SOURCE_ONLY:{role}" for role in source_matches),
        ]
        if len(matches) > 1:
            reasons.append("CATEGORY_ROW_MATCHES_MULTIPLE_DECLARED_ROLES")
        if len(matches) == 1:
            kind, role = matches[0].split(":", 1)
            kind = "MAPPED_CATEGORY" if kind == "MAPPED" else "SOURCE_ONLY_CATEGORY"
            (mapped_roles if kind == "MAPPED_CATEGORY" else source_only_roles).append(role)
        elif row.get("row_kind") == "GROUP" and all(
            value is None or (type(value) is str and not value.strip())
            for value in row["values_exact"]
        ):
            kind, role = "STRUCTURAL_CONTEXT_ROW", None
        else:
            kind, role = "FOREIGN_CATEGORY_ROW", None
            reasons.append("FOREIGN_ROW_INSIDE_DECLARED_CATEGORY_POPULATION")
        row_axis.append(
            {
                "kind": kind,
                "label_exact": row.get("label_exact"),
                "role": role,
                "role_matches": matches,
                "row_id": f"r{ordinal}",
                "row_kind": row.get("row_kind"),
                "source_order": ordinal,
            }
        )
    if len(set(mapped_roles)) != len(mapped_roles) or len(set(source_only_roles)) != len(
        source_only_roles
    ):
        reasons.append("DUPLICATE_DECLARED_CATEGORY_ROLE")
    if len(set(mapped_roles)) < compiled_specs["query_policy"]["minimum_mapped_category_roles"]:
        reasons.append("MAPPED_CATEGORY_POPULATION_INCOMPLETE")
    if not source_only_roles and len(mapped_roles) != len(rows):
        reasons.append("CATEGORY_POPULATION_NOT_EXHAUSTIVELY_DECLARED")
    status = "MATRIX_FRAGMENT" if not reasons else "NOT_MATRIX"
    return {
        "column_axis": column_axis,
        "column_declared_component_roles": sorted(
            {role for item in column_axis for role in item["semantic_role_matches"]}
        ),
        "component_axis": row_axis,
        "component_axis_sha256": canonical_json_sha256_v1(row_axis),
        "mapped_component_roles": sorted(set(mapped_roles)),
        "matrix_kind": MATRIX_KIND,
        "orientation": "CATEGORY_ROWS_PERIOD_COLUMNS" if status == "MATRIX_FRAGMENT" else None,
        "reasons": sorted(set(reasons)),
        "row_declared_component_roles": sorted(set([*mapped_roles, *source_only_roles])),
        "status": status,
    }


def _reporting_date_receipt(
    pages: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    from bctc_ai.evaluation.gemini_json_interest_rate_risk_matrix_v1 import (
        interest_rate_document_reporting_date_receipt_v1,
    )

    engine = _engine()
    base = interest_rate_document_reporting_date_receipt_v1(list(pages))
    evidence = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "BALANCE_SHEET"
                or type(section.get("tables")) is not list
            ):
                continue
            for table_ordinal, table in enumerate(section["tables"], start=1):
                if type(table) is not dict or type(table.get("columns")) is not list:
                    continue
                dates = sorted(
                    {
                        item.isoformat()
                        for column in table["columns"]
                        if type(column) is dict and column.get("value_kind") == "MONEY"
                        for member in engine._header_members(column)
                        for item in engine._header_dates(member)
                    },
                    reverse=True,
                )
                if len(dates) != 2 or dates[0] <= dates[1]:
                    continue
                evidence.append(
                    {
                        "comparative_date": dates[1],
                        "current_date": dates[0],
                        "page_json_version_id": record["page_json_version_id"],
                        "physical_page": record["physical_page"],
                        "section_id": f"s{section_ordinal}",
                        "source_kind": "TYPED_PRIMARY_BALANCE_SHEET_TWO_DATE_COLUMN_AXIS",
                        "table_id": f"t{table_ordinal}",
                    }
                )
    base_current = base.get("current_date")
    compatible = [
        item for item in evidence if base_current is None or item["current_date"] == base_current
    ]
    pair_axis = {(item["current_date"], item["comparative_date"]) for item in compatible}
    if len(pair_axis) == 1:
        current_date, comparative_date = next(iter(pair_axis))
        status = "UNIQUE_TYPED_DOCUMENT_CURRENT_AND_COMPARATIVE_DATE_AXIS"
    elif len(pair_axis) > 1:
        current_date = base_current
        comparative_date = None
        status = "CONFLICTING_TYPED_DOCUMENT_CURRENT_AND_COMPARATIVE_DATE_AXIS"
    else:
        current_date = base_current
        comparative_date = base.get("comparative_date")
        status = base.get("status")
    material = {
        "base_receipt": canonical_clone_v1(base),
        "comparative_date": comparative_date,
        "current_date": current_date,
        "evidence": canonical_clone_v1(evidence),
        "rule": ("TYPED_REPORTING_DATE_WITH_UNIQUE_PRIMARY_BALANCE_SHEET_TWO_DATE_COLUMN_AXIS"),
        "status": status,
    }
    return {**material, "receipt_sha256": canonical_json_sha256_v1(material)}


def _resolve_period_assignments(
    classification: Mapping[str, Any],
    *,
    reporting_date_receipt: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    reasons = []
    columns = classification["column_axis"]
    explicit_dates = [
        item["date_axis"][0] if len(item["date_axis"]) == 1 else None for item in columns
    ]
    if any(item is None for item in explicit_dates) and reporting_date_receipt.get(
        "status"
    ) not in {
        "UNIQUE_LATEST_TYPED_DOCUMENT_REPORTING_DATE",
        "UNIQUE_TYPED_DOCUMENT_CURRENT_AND_COMPARATIVE_DATE_AXIS",
    }:
        reasons.append("RELATIVE_PERIOD_REQUIRES_UNIQUE_TYPED_DOCUMENT_DATE_AXIS")
    if any(len(item["date_axis"]) > 1 for item in columns):
        reasons.append("EXCHANGE_RATE_PERIOD_DATE_AXIS_CONFLICTING")
    distinct = {item for item in explicit_dates if item is not None}
    if len(distinct) != sum(item is not None for item in explicit_dates):
        reasons.append("EXCHANGE_RATE_PERIOD_DATES_NOT_DISTINCT")
    date_roles = {}
    if len(distinct) == 2:
        ordered = sorted(distinct, reverse=True)
        date_roles = {ordered[0]: "CURRENT_PERIOD", ordered[1]: "COMPARATIVE_PERIOD"}
    current_date = reporting_date_receipt.get("current_date")
    comparative_date = reporting_date_receipt.get("comparative_date")
    if type(current_date) is str and comparative_date is None:
        try:
            current_point = date.fromisoformat(current_date)
        except ValueError:
            current_point = None
        if current_point is not None and (current_point.month, current_point.day) in {
            (3, 31),
            (6, 30),
            (9, 30),
            (12, 31),
        }:
            comparative_date = date(current_point.year - 1, 12, 31).isoformat()
    assignments = []
    seen_roles = set()
    for column, explicit_date in zip(columns, explicit_dates, strict=True):
        semantic = (
            column["semantic_role_matches"][0]
            if len(column["semantic_role_matches"]) == 1
            else None
        )
        period_role = date_roles.get(explicit_date) if explicit_date is not None else semantic
        period_date = explicit_date
        source = "EXPLICIT_COLUMN_DATE"
        if period_role is None and explicit_date is not None and len(distinct) == 1:
            if explicit_date == current_date:
                period_role = "CURRENT_PERIOD"
            elif explicit_date == comparative_date:
                period_role = "COMPARATIVE_PERIOD"
        if period_role is None and semantic is not None:
            period_role = semantic
        if period_date is None and period_role == "CURRENT_PERIOD":
            period_date = current_date
            source = "TYPED_DOCUMENT_REPORTING_DATE_AXIS"
        elif period_date is None and period_role == "COMPARATIVE_PERIOD":
            period_date = comparative_date
            source = (
                "TYPED_DOCUMENT_REPORTING_DATE_AXIS"
                if reporting_date_receipt.get("comparative_date") is not None
                else "VISIBLE_BEGINNING_PERIOD_CALENDAR_YEAR_BOUNDARY"
            )
        if semantic is not None and period_role is not None and semantic != period_role:
            reasons.append("COLUMN_DATE_CONFLICTS_VISIBLE_PERIOD_SEMANTIC_ROLE")
        if (
            period_role == "CURRENT_PERIOD"
            and type(current_date) is str
            and period_date != current_date
        ):
            reasons.append("CURRENT_RATE_DATE_CONFLICTS_DOCUMENT_REPORTING_DATE")
        if (
            period_role == "COMPARATIVE_PERIOD"
            and type(comparative_date) is str
            and period_date != comparative_date
        ):
            reasons.append("COMPARATIVE_RATE_DATE_CONFLICTS_DOCUMENT_REPORTING_DATE")
        if period_role not in _DATE_ROLES or type(period_date) is not str:
            reasons.append("EXCHANGE_RATE_PERIOD_ASSIGNMENT_UNRESOLVED")
        elif period_role in seen_roles:
            reasons.append("DUPLICATE_EXCHANGE_RATE_PERIOD_ROLE")
        else:
            seen_roles.add(period_role)
        assignments.append(
            {
                "column_id": column["column_id"],
                "header_path_exact": canonical_clone_v1(column["header_path_exact"]),
                "period_date": period_date,
                "period_role": period_role,
                "source": source,
                "source_order": column["source_order"],
            }
        )
    if seen_roles != _DATE_ROLES:
        reasons.append("EXCHANGE_RATE_TWO_PERIOD_AXIS_INCOMPLETE")
    return assignments, sorted(set(reasons))


def _rate_denominator_receipt(
    *,
    owner_source_exact: str,
    table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    document_reporting_currency_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    engine = _engine()
    surfaces = [
        {"source_exact": owner_source_exact, "source_kind": "OWNER"},
        {"source_exact": table.get("unit_exact"), "source_kind": "TABLE_UNIT"},
        *(
            {
                "source_exact": member,
                "source_kind": f"COLUMN_{ordinal}_HEADER",
            }
            for ordinal, column in enumerate(table.get("columns", []), start=1)
            for member in engine._header_members(column)
        ),
    ]
    owner_folded = engine._normalized(owner_source_exact)
    explicit_owner = bool(re.search(r"\bso voi (?:vnd|dong viet nam)\b", owner_folded))
    raw_vnd_evidence = [
        item
        for item in surfaces
        if re.search(r"\b(?:vnd|dong)\b", engine._normalized(item["source_exact"]))
    ]
    incidental = [
        item
        for item in surfaces
        if any(
            re.search(
                rf"(?<![a-z0-9]){re.escape(engine._normalized(alias))}(?![a-z0-9])",
                engine._normalized(item["source_exact"]),
            )
            for alias in compiled_specs["incidental_amount_scale_aliases"]
        )
    ]
    incidental_keys = {(item["source_kind"], item["source_exact"]) for item in incidental}
    vnd_evidence = [
        item
        for item in raw_vnd_evidence
        if (item["source_kind"], item["source_exact"]) not in incidental_keys
    ]
    if explicit_owner:
        source = "EXPLICIT_OWNER_RATE_DENOMINATOR_VND"
    elif vnd_evidence:
        source = "LOCAL_TABLE_OR_COLUMN_RATE_DENOMINATOR_VND"
    elif document_reporting_currency_receipt.get("status") == "UNIQUE_VND_REPORTING_CURRENCY":
        source = "TYPED_DOCUMENT_REPORTING_CURRENCY_VND"
    else:
        source = None
    material = {
        "canonical_rate_unit": compiled_specs["canonical_rate_unit"],
        "document_reporting_currency_receipt": canonical_clone_v1(
            document_reporting_currency_receipt
        ),
        "incidental_amount_scale_evidence": canonical_clone_v1(incidental),
        "owner_source_exact": owner_source_exact,
        "rule": (
            "EXPLICIT_EXCHANGE_RATE_OWNER_WITH_VND_DENOMINATOR_OR_LOCAL_VND_"
            "CARRIER_ELSE_TYPED_DOCUMENT_REPORTING_CURRENCY_EVIDENCE"
        ),
        "source": source,
        "vnd_evidence": canonical_clone_v1(vnd_evidence),
    }
    return {
        **material,
        "receipt_sha256": canonical_json_sha256_v1(material),
    }, [] if source is not None else ["RATE_DENOMINATOR_VND_NOT_SOURCE_AUTHENTICATED"]


def _document_reporting_currency_receipt(
    pages: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind the document currency only from typed primary balance-sheet carriers."""

    engine = _engine()
    evidence = []
    currencies = set()
    foreign_codes = sorted(
        {
            *compiled_specs["aliases_by_role"],
            *(
                role.removeprefix("SOURCE_")
                for role in compiled_specs["source_only_aliases_by_role"]
            ),
        }
        - {"VND"}
    )
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "BALANCE_SHEET"
                or type(section.get("tables")) is not list
            ):
                continue
            for table_ordinal, table in enumerate(section["tables"], start=1):
                if type(table) is not dict or type(table.get("columns")) is not list:
                    continue
                surfaces = [
                    ("TABLE_UNIT", table.get("unit_exact")),
                    *(
                        (f"COLUMN_{column_ordinal}_HEADER", member)
                        for column_ordinal, column in enumerate(table["columns"], start=1)
                        if type(column) is dict and column.get("value_kind") == "MONEY"
                        for member in engine._header_members(column)
                    ),
                ]
                for source_kind, source_exact in surfaces:
                    folded = engine._normalized(source_exact)
                    matches = []
                    if re.search(r"\b(?:vnd|dong)\b", folded):
                        matches.append("VND")
                    matches.extend(
                        code
                        for code in foreign_codes
                        if re.search(
                            rf"(?<![a-z0-9]){re.escape(engine._normalized(code))}(?![a-z0-9])",
                            folded,
                        )
                    )
                    if not matches:
                        continue
                    currencies.update(matches)
                    evidence.append(
                        {
                            "currency_matches": sorted(set(matches)),
                            "page_json_version_id": record["page_json_version_id"],
                            "physical_page": record["physical_page"],
                            "section_id": f"s{section_ordinal}",
                            "source_exact": source_exact,
                            "source_kind": source_kind,
                            "table_id": f"t{table_ordinal}",
                        }
                    )
    if currencies == {"VND"} and evidence:
        status = "UNIQUE_VND_REPORTING_CURRENCY"
    elif currencies:
        status = "CONFLICTING_DOCUMENT_REPORTING_CURRENCY"
    else:
        status = "DOCUMENT_REPORTING_CURRENCY_NOT_OBSERVED"
    material = {
        "currency_axis": sorted(currencies),
        "evidence": evidence,
        "rule": (
            "UNIQUE_CURRENCY_FROM_TYPED_PRIMARY_BALANCE_SHEET_TABLE_UNIT_OR_MONEY_COLUMN_"
            "HEADER_ONLY"
        ),
        "status": status,
    }
    return {**material, "receipt_sha256": canonical_json_sha256_v1(material)}


def coalesce_gemini_json_categorical_period_matrix_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select exactly one complete owner-scoped categorical period matrix."""

    engine = _engine()
    pages = engine._selected_page_record_axis(page_records)
    owners = []
    resets = []
    table_axis = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if type(section) is not dict:
                continue
            surfaces = [section.get("title_exact"), *(section.get("narratives_exact") or [])]
            for surface_ordinal, source_exact in enumerate(surfaces):
                position = [record["selected_page_ordinal"], section_ordinal, 0, surface_ordinal]
                owner = engine._contained_declared_alias(
                    source_exact, compiled_specs["query_policy"]["owner_aliases"]
                )
                reset = engine._contained_declared_alias(
                    source_exact,
                    [
                        *compiled_specs["query_policy"]["reset_aliases"],
                        *compiled_specs["query_policy"]["hard_negative_aliases"],
                    ],
                )
                if owner is not None:
                    owners.append(
                        {"alias": owner, "position": position, "source_exact": source_exact}
                    )
                if reset is not None:
                    resets.append(
                        {"alias": reset, "position": position, "source_exact": source_exact}
                    )
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                position = [record["selected_page_ordinal"], section_ordinal, 1, table_ordinal]
                title_owner = engine._contained_declared_alias(
                    table.get("title_exact"), compiled_specs["query_policy"]["owner_aliases"]
                )
                if title_owner is not None:
                    owners.append(
                        {
                            "alias": title_owner,
                            "position": position,
                            "source_exact": table.get("title_exact"),
                        }
                    )
                classification = classify_gemini_json_categorical_period_matrix_table_v1(
                    table, compiled_specs=compiled_specs
                )
                if classification["row_declared_component_roles"]:
                    table_axis.append(
                        {
                            "classification": classification,
                            "continuation": table.get("continuation"),
                            "position": position,
                            "record": record,
                            "section_id": f"s{section_ordinal}",
                            "table": table,
                            "table_id": f"t{table_ordinal}",
                        }
                    )
    inventory = []
    reasons = []
    for item in table_axis:
        prior = [
            owner
            for owner in owners
            if owner["position"] <= item["position"]
            and item["position"][0] - owner["position"][0]
            <= compiled_specs["query_policy"]["max_continuation_pages"]
        ]
        if not prior:
            continue
        owner = max(prior, key=lambda value: value["position"])
        fenced = [
            reset for reset in resets if owner["position"] <= reset["position"] <= item["position"]
        ]
        if fenced:
            continue
        inventory.append({**item, "owner": owner, "reset_fence_axis": fenced})
    selected = [item for item in inventory if item["classification"]["status"] == "MATRIX_FRAGMENT"]
    reasons.extend(
        reason
        for item in inventory
        if item["classification"]["status"] != "MATRIX_FRAGMENT"
        for reason in item["classification"]["reasons"]
    )
    if inventory and len(selected) != len(inventory):
        reasons.append("INCOMPLETE_DECLARED_CATEGORICAL_PERIOD_TABLE_PRESENT")
    if len(selected) > 1:
        reasons.append("MULTIPLE_CATEGORICAL_PERIOD_MATRICES_UNDER_DOCUMENT_OWNER")
    reporting = _reporting_date_receipt(pages, compiled_specs=compiled_specs)
    reporting_currency = _document_reporting_currency_receipt(pages, compiled_specs=compiled_specs)
    assignments = []
    denominator = None
    owner_receipt = None
    if len(selected) == 1:
        item = selected[0]
        assignments, period_reasons = _resolve_period_assignments(
            item["classification"], reporting_date_receipt=reporting
        )
        reasons.extend(period_reasons)
        denominator, denominator_reasons = _rate_denominator_receipt(
            owner_source_exact=item["owner"]["source_exact"],
            table=item["table"],
            compiled_specs=compiled_specs,
            document_reporting_currency_receipt=reporting_currency,
        )
        reasons.extend(denominator_reasons)
        owner_receipt = {
            "continuation_evidence": None,
            "document_reporting_date_receipt": reporting,
            "owner_alias": item["owner"]["alias"],
            "owner_position": item["owner"]["position"],
            "owner_source_exact": item["owner"]["source_exact"],
            "period_assignments": assignments,
            "rate_denominator_receipt": denominator,
            "reset_fence_axis": item["reset_fence_axis"],
            "rule": "LATEST_EXPLICIT_OWNER_SAME_OR_ADJACENT_PAGE_RESET_FREE_INTERVAL",
        }
    regions = [
        engine._matrix_region(item, fragment_ordinal=ordinal)
        for ordinal, item in enumerate(selected, start=1)
    ]
    inventory_receipt = [
        {
            "classification": canonical_clone_v1(item["classification"]),
            "continuation": item["continuation"],
            "disposition": (
                "SELECTED_CATEGORICAL_PERIOD_FRAGMENT"
                if item in selected
                else "UNSELECTED_DECLARED_CATEGORICAL_PERIOD_TABLE"
            ),
            "page_json_version_id": item["record"]["page_json_version_id"],
            "physical_page": item["record"]["physical_page"],
            "position": item["position"],
            "section_id": item["section_id"],
            "table_id": item["table_id"],
        }
        for item in inventory
    ]
    unit_context_material = {
        "canonical_rate_unit": compiled_specs["canonical_rate_unit"],
        "evidence": [],
        "rule": "RATE_DENOMINATOR_IS_RESOLVED_IN_OWNER_SCOPED_MATRIX_NOT_MONEY_SCALE",
        "status": "NOT_APPLICABLE_RATE_DENOMINATOR_RESOLVED_LOCALLY",
    }
    unit_context = {
        **unit_context_material,
        "document_unit_context_sha256": canonical_json_sha256_v1(unit_context_material),
    }
    first = pages[0]
    status = (
        engine.NOT_OBSERVED
        if not inventory
        else engine.READY
        if len(selected) == 1 and not reasons and owner_receipt is not None
        else engine.UNRESOLVED
    )
    material = {
        "component_regions": regions if status == engine.READY else [],
        "declared_table_inventory": inventory_receipt,
        "document_id": first["document_id"],
        "document_ordinal": first["document_ordinal"],
        "document_unit_context_evidence": unit_context,
        "owner_receipt": owner_receipt,
        "reasons": sorted(set(reasons)),
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": status,
    }
    return {
        "cluster_id": "gjeqmfv1:cluster:" + canonical_json_sha256_v1(material),
        **material,
    }


def _decimal_hundredths(value: Any) -> tuple[int | None, str | None, str]:
    """Parse one nonnegative visible rate using deterministic separator grammar."""

    if type(value) is not str or not value.strip():
        return None, None, "INVALID_ABSENT_RATE"
    source = value.strip().replace("\u00a0", "").replace(" ", "")
    if source.startswith("(") or source.startswith(("-", "+")):
        return None, None, "INVALID_SIGNED_RATE"
    if re.fullmatch(r"[0-9][0-9.,]*", source) is None:
        return None, None, "INVALID_RATE_TOKEN"
    separators = [(index, char) for index, char in enumerate(source) if char in ".,"]
    decimal_index = None
    if separators:
        last_index, last_char = separators[-1]
        tail = source[last_index + 1 :]
        other_char = "," if last_char == "." else "."
        if len(tail) in {1, 2}:
            decimal_index = last_index
        elif other_char in source and len(tail) != 3:
            return None, None, "INVALID_RATE_SEPARATOR_GRAMMAR"
    if decimal_index is None:
        groups = re.split(r"[.,]", source)
        if len(groups) > 1 and any(len(group) != 3 for group in groups[1:]):
            return None, None, "INVALID_RATE_GROUPING"
        integer_text = "".join(groups)
        fraction_text = "00"
    else:
        integer_surface = source[:decimal_index]
        fraction_surface = source[decimal_index + 1 :]
        groups = re.split(r"[.,]", integer_surface)
        if len(groups) > 1 and any(len(group) != 3 for group in groups[1:]):
            return None, None, "INVALID_RATE_GROUPING"
        integer_text = "".join(groups)
        fraction_text = fraction_surface.ljust(2, "0")
    if not integer_text.isdigit() or not fraction_text.isdigit():
        return None, None, "INVALID_RATE_TOKEN"
    coefficient = int(integer_text) * 100 + int(fraction_text)
    if coefficient <= 0 or coefficient > 10**12:
        return None, None, "INVALID_RATE_RANGE"
    normalized = f"{int(integer_text)}.{fraction_text}"
    if Decimal(normalized) * 100 != coefficient:
        raise _error("categorical-period decimal normalization drifted")
    return coefficient, normalized, "RAW_RATE_DECIMAL_SCALED_HUNDREDTHS"


def _cell(*, value: Any, region: Mapping[str, Any], row_id: str, column_id: str) -> dict[str, Any]:
    coefficient, normalized, state = _decimal_hundredths(value)
    return {
        "cell_ref": {
            "column_id": column_id,
            "locator": canonical_clone_v1(region),
            "row_id": row_id,
        },
        "coefficient": coefficient,
        "normalized_decimal": normalized,
        "source_text": value if type(value) is str else None,
        "state": state,
    }


def _mapping_value(*, cell: Mapping[str, Any], assignment: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "axis_role": assignment["period_role"],
        "cell_ref": canonical_clone_v1(cell["cell_ref"]),
        "coefficient": cell["coefficient"],
        "normalized_decimal": cell["normalized_decimal"],
        "period_date": assignment["period_date"],
        "period_role": assignment["period_role"],
        "source_text": cell["source_text"],
        "state": cell["state"],
    }


def _build_mappings(
    *,
    compiled_specs: Mapping[str, Any],
    resolved_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    mappings = []
    root = {
        "item_mapping_id": "gjeqmfv1:item:pending",
        "report_norm_id": compiled_specs["family_root_report_norm_id"],
        "role": "FAMILY",
        "row_id": "structural:FAMILY",
        "unit": None,
        "values": [],
    }
    root["item_mapping_id"] = "gjeqmfv1:item:" + canonical_json_sha256_v1(
        {key: value for key, value in root.items() if key != "item_mapping_id"}
    )
    mappings.append(root)
    for row in resolved_rows:
        if row["kind"] != "MAPPED_CATEGORY":
            continue
        role = row["role"]
        mapping = {
            "item_mapping_id": "gjeqmfv1:item:pending",
            "report_norm_id": compiled_specs["category_report_norm_id_by_role"][role],
            "role": role,
            "row_id": f"category:{role}",
            "unit": compiled_specs["canonical_rate_unit"],
            "values": canonical_clone_v1(row["values"]),
        }
        mapping["item_mapping_id"] = "gjeqmfv1:item:" + canonical_json_sha256_v1(
            {key: value for key, value in mapping.items() if key != "item_mapping_id"}
        )
        mappings.append(mapping)
    return mappings


def evaluate_gemini_json_categorical_period_matrix_cluster_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    document_unit_context_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Map supported categories only after exhaustive two-period closure."""

    engine = _engine()
    checked_regions = engine._checked_region_axis(regions)
    expected_query = engine.build_gemini_json_equity_matrix_region_query_receipt_v1(
        checked_regions, owner_receipt=query_receipt.get("owner_receipt", {})
    )
    if not same_typed_json_v1(expected_query, query_receipt):
        raise _error("categorical-period query receipt drifted")
    if len(checked_regions) != 1:
        raise _error("categorical-period candidate requires exactly one table")
    assignment_axis = query_receipt.get("owner_receipt", {}).get("period_assignments")
    denominator = query_receipt.get("owner_receipt", {}).get("rate_denominator_receipt")
    if (
        type(assignment_axis) is not list
        or len(assignment_axis) != 2
        or {item.get("period_role") for item in assignment_axis if type(item) is dict}
        != _DATE_ROLES
        or type(denominator) is not dict
        or denominator.get("canonical_rate_unit") != compiled_specs["canonical_rate_unit"]
    ):
        raise _error("categorical-period owner period or denominator receipt drifted")
    region = checked_regions[0]
    page = page_json_by_version.get(region["page_json_version_id"])
    if type(page) is not dict:
        raise _error("categorical-period canonical page is absent")
    _section, table = engine._source_table(
        page, section_id=region["section_id"], table_id=region["table_id"]
    )
    classification = classify_gemini_json_categorical_period_matrix_table_v1(
        table, compiled_specs=compiled_specs
    )
    reasons = list(classification["reasons"])
    assignment_by_column = {item["column_id"]: item for item in assignment_axis}
    resolved_rows = []
    for row_axis in classification["component_axis"]:
        row = table["rows"][row_axis["source_order"] - 1]
        values = []
        cells = []
        for column_axis in classification["column_axis"]:
            assignment = assignment_by_column.get(column_axis["column_id"])
            if assignment is None:
                reasons.append("CATEGORY_VALUE_PERIOD_ASSIGNMENT_MISSING")
                continue
            cell = _cell(
                value=row["values_exact"][column_axis["source_order"] - 1],
                region=region,
                row_id=row_axis["row_id"],
                column_id=column_axis["column_id"],
            )
            cells.append(cell)
            if row_axis["kind"] == "MAPPED_CATEGORY" and type(cell["coefficient"]) is not int:
                reasons.append(f"INVALID_CATEGORY_RATE_CELL:{row_axis['role']}")
            elif type(cell["coefficient"]) is int:
                values.append(_mapping_value(cell=cell, assignment=assignment))
        resolved_rows.append({**canonical_clone_v1(row_axis), "cells": cells, "values": values})
    mapped_roles = {
        row["role"]
        for row in resolved_rows
        if row["kind"] == "MAPPED_CATEGORY" and len(row["values"]) == 2
    }
    if len(mapped_roles) < compiled_specs["query_policy"]["minimum_mapped_category_roles"]:
        reasons.append("MAPPED_CATEGORY_TWO_PERIOD_VALUE_COVERAGE_INCOMPLETE")
    reasons = sorted(set(reasons))
    mappings = _build_mappings(compiled_specs=compiled_specs, resolved_rows=resolved_rows)
    if reasons:
        mappings = []
    closure = {
        "category_axis": canonical_clone_v1(classification["component_axis"]),
        "matrix_kind": MATRIX_KIND,
        "period_assignments": canonical_clone_v1(assignment_axis),
        "query_receipt": canonical_clone_v1(query_receipt),
        "rate_denominator_receipt": canonical_clone_v1(denominator),
        "resolved_rows": resolved_rows,
        "rule": "EXHAUSTIVE_DECLARED_CATEGORY_ROWS_WITH_EXACT_TWO_PERIOD_RATE_VALUES",
        "source_only_category_axis": [
            canonical_clone_v1(item)
            for item in resolved_rows
            if item["kind"] == "SOURCE_ONLY_CATEGORY"
        ],
    }
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": closure,
        "component_regions": canonical_clone_v1(checked_regions),
        "document_id": region["document_id"],
        "family_id": compiled_specs["family_id"],
        "mappings": mappings,
        "page_json_version_id": region["page_json_version_id"],
        "physical_page": region["physical_page"],
        "reasons": reasons,
        "section_id": region["section_id"],
        "source_logical_name": region["source_logical_name"],
        "source_sha256": region["source_sha256"],
        "status": engine.READY if mappings and not reasons else engine.UNRESOLVED,
        "table_id": region["table_id"],
    }
    return {
        "candidate_id": "gjeqmfv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_categorical_period_matrix_candidate_binding_v1(
    candidate: Any,
    *,
    document: Mapping[str, Any],
    cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal internal categorical graph coherence before SQLite source replay."""

    engine = _engine()
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
    closure_fields = {
        "category_axis",
        "matrix_kind",
        "period_assignments",
        "query_receipt",
        "rate_denominator_receipt",
        "resolved_rows",
        "rule",
        "source_only_category_axis",
    }
    regions = cluster["component_regions"]
    first = regions[0]
    closure = candidate.get("closure_receipt") if type(candidate) is dict else None
    if (
        type(candidate) is not dict
        or set(candidate) != fields
        or candidate.get("claim_boundary") != CLAIM_BOUNDARY
        or candidate.get("family_id") != compiled_specs["family_id"]
        or candidate.get("document_id") != first["document_id"]
        or candidate.get("page_json_version_id") != first["page_json_version_id"]
        or candidate.get("physical_page") != first["physical_page"]
        or candidate.get("section_id") != first["section_id"]
        or candidate.get("table_id") != first["table_id"]
        or candidate.get("source_logical_name") != document["source_logical_name"]
        or candidate.get("source_sha256") != document["source_sha256"]
        or not same_typed_json_v1(candidate.get("component_regions"), regions)
        or type(closure) is not dict
        or set(closure) != closure_fields
        or closure.get("matrix_kind") != MATRIX_KIND
        or type(closure.get("resolved_rows")) is not list
        or type(candidate.get("mappings")) is not list
        or type(candidate.get("reasons")) is not list
        or candidate["reasons"] != sorted(set(candidate["reasons"]))
    ):
        raise _error("categorical-period candidate structure drifted")
    expected_query = engine.build_gemini_json_equity_matrix_region_query_receipt_v1(
        regions, owner_receipt=cluster["owner_receipt"]
    )
    if not same_typed_json_v1(closure["query_receipt"], expected_query):
        raise _error("categorical-period candidate query receipt drifted")
    if not same_typed_json_v1(
        closure["period_assignments"], cluster["owner_receipt"]["period_assignments"]
    ) or not same_typed_json_v1(
        closure["rate_denominator_receipt"],
        cluster["owner_receipt"]["rate_denominator_receipt"],
    ):
        raise _error("categorical-period period or denominator receipt drifted")
    inventory = cluster["declared_table_inventory"]
    if len(inventory) != 1 or not same_typed_json_v1(
        closure["category_axis"], inventory[0]["classification"]["component_axis"]
    ):
        raise _error("categorical-period category inventory drifted")
    if closure.get("rule") != (
        "EXHAUSTIVE_DECLARED_CATEGORY_ROWS_WITH_EXACT_TWO_PERIOD_RATE_VALUES"
    ):
        raise _error("categorical-period closure rule drifted")
    denominator = closure["rate_denominator_receipt"]
    denominator_material = {
        key: value for key, value in denominator.items() if key != "receipt_sha256"
    }
    if denominator.get("receipt_sha256") != canonical_json_sha256_v1(denominator_material):
        raise _error("categorical-period denominator receipt identity drifted")
    assignments = {item["column_id"]: item for item in closure["period_assignments"]}
    if (
        len(assignments) != 2
        or {item.get("period_role") for item in assignments.values()} != _DATE_ROLES
        or len(closure["resolved_rows"]) != len(closure["category_axis"])
    ):
        raise _error("categorical-period resolved axis cardinality drifted")
    axis_fields = {
        "kind",
        "label_exact",
        "role",
        "role_matches",
        "row_id",
        "row_kind",
        "source_order",
    }
    cell_fields = {
        "cell_ref",
        "coefficient",
        "normalized_decimal",
        "source_text",
        "state",
    }
    value_fields = {
        "axis_role",
        "cell_ref",
        "coefficient",
        "normalized_decimal",
        "period_date",
        "period_role",
        "source_text",
        "state",
    }
    for source_axis, resolved in zip(
        closure["category_axis"], closure["resolved_rows"], strict=True
    ):
        if (
            type(resolved) is not dict
            or set(resolved) != axis_fields | {"cells", "values"}
            or not same_typed_json_v1({key: resolved[key] for key in axis_fields}, source_axis)
            or type(resolved["cells"]) is not list
            or len(resolved["cells"]) != 2
            or type(resolved["values"]) is not list
        ):
            raise _error("categorical-period resolved row projection drifted")
        expected_values = []
        for cell in resolved["cells"]:
            ref = cell.get("cell_ref") if type(cell) is dict else None
            assignment = assignments.get(ref.get("column_id")) if type(ref) is dict else None
            if (
                type(cell) is not dict
                or set(cell) != cell_fields
                or type(ref) is not dict
                or set(ref) != {"column_id", "locator", "row_id"}
                or ref.get("row_id") != resolved["row_id"]
                or not same_typed_json_v1(ref.get("locator"), first)
                or assignment is None
            ):
                raise _error("categorical-period resolved cell provenance drifted")
            coefficient, normalized, state = _decimal_hundredths(cell.get("source_text"))
            if (
                cell.get("coefficient") != coefficient
                or cell.get("normalized_decimal") != normalized
                or cell.get("state") != state
            ):
                raise _error("categorical-period resolved cell normalization drifted")
            if type(coefficient) is int:
                expected_values.append(_mapping_value(cell=cell, assignment=assignment))
        if any(type(item) is not dict or set(item) != value_fields for item in resolved["values"]):
            raise _error("categorical-period resolved mapping value shape drifted")
        if not same_typed_json_v1(resolved["values"], expected_values):
            raise _error("categorical-period resolved mapping value projection drifted")
        if resolved["kind"] == "MAPPED_CATEGORY" and len(expected_values) != 2:
            raise _error("categorical-period mapped row coverage drifted")
    expected_source_only = [
        canonical_clone_v1(item)
        for item in closure["resolved_rows"]
        if item.get("kind") == "SOURCE_ONLY_CATEGORY"
    ]
    if not same_typed_json_v1(closure["source_only_category_axis"], expected_source_only):
        raise _error("categorical-period source-only projection drifted")
    expected_mappings = _build_mappings(
        compiled_specs=compiled_specs, resolved_rows=closure["resolved_rows"]
    )
    if candidate.get("status") == engine.READY:
        if candidate["reasons"] or not same_typed_json_v1(candidate["mappings"], expected_mappings):
            raise _error("categorical-period READY mapping axis drifted")
    elif candidate.get("status") == engine.UNRESOLVED:
        if candidate["mappings"] or not candidate["reasons"]:
            raise _error("categorical-period unresolved semantics drifted")
    else:
        raise _error("categorical-period candidate status drifted")
    material = {key: value for key, value in candidate.items() if key != "candidate_id"}
    if candidate["candidate_id"] != "gjeqmfv1:candidate:" + canonical_json_sha256_v1(material):
        raise _error("categorical-period candidate identity drifted")
    return canonical_clone_v1(candidate)
