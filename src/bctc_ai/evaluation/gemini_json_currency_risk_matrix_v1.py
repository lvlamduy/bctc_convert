"""Currency-axis accounting closure over selected Gemini JSON matrices.

Gemini remains a structure reader.  This module resolves exact declared
currency columns and accounting-core rows, retains unsupported currencies as
source-only evidence, closes declarative row equations, and only then projects
visible/zero-proven cells to schema IDs.  It has no OCR, geometry, bank, file,
page, note-number, or expected-value routing behavior.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _money,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

CURRENCY_RISK_CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_CURRENCY_RISK_MATRIX_EXPLICIT_OWNER_"
    "RESET_FENCE_EXHAUSTIVE_MAPPED_AND_SOURCE_ONLY_CURRENCY_COLUMNS_EXACT_"
    "DECLARATIVE_ASSET_LIABILITY_AND_INTERNAL_EXTERNAL_STATE_EQUATIONS_"
    "MINIMUM_EXACT_CURRENCY_COVERAGE_NONCLOSING_RAW_SOURCE_RETENTION_TYPED_"
    "PERIOD_UNIT_CONDITIONAL_BLANK_ZERO_STRUCTURAL_SCHEMA_CONTEXT_ONLY_NO_OCR_"
    "GEOMETRY_BANK_FILE_PAGE_NOTE_VALUE_ROUTING_BACKSOLVE_OR_EXPORT_AUTHORITY"
)
MATRIX_KIND = "CURRENCY_RISK_CLASSIFICATION"


class GeminiJsonCurrencyRiskMatrixV1Error(ValueError):
    """The currency matrix policy, source graph, equation, or replay drifted."""


def _error(message: str) -> GeminiJsonCurrencyRiskMatrixV1Error:
    return GeminiJsonCurrencyRiskMatrixV1Error(message)


def _engine() -> Any:
    # Lazy import avoids a module cycle: the shared matrix engine dispatches
    # here only after its own module initialization is complete.
    from bctc_ai.evaluation import gemini_json_equity_matrix_accounting_family_v1

    return gemini_json_equity_matrix_accounting_family_v1


def compile_gemini_json_currency_risk_matrix_specs_v1(
    *, topology: Mapping[str, Any], evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile one strict declarative currency-risk matrix triplet."""

    engine = _engine()
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec)
        != {
            "blank_zero_policy",
            "closure_policy",
            "family_id",
            "format_version",
            "matrix_policy",
        }
        or evaluation_spec.get("format_version") != engine.EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("blank_zero_policy")
        != "ZERO_ONLY_AFTER_ONE_UNKNOWN_DECLARED_EQUATION_EQUALS_ZERO"
        or evaluation_spec.get("closure_policy")
        != "EXACT_REQUIRED_EQUATION_COVERAGE_WITH_NONCLOSING_SOURCE_RETENTION"
    ):
        raise _error("currency-risk matrix evaluation spec is invalid")
    policy = evaluation_spec.get("matrix_policy")
    policy_fields = {
        "accepted_orientations",
        "currency_role_aliases",
        "grand_total_role",
        "matrix_kind",
        "max_continuation_pages",
        "minimum_mapped_currency_roles",
        "required_row_roles",
        "source_only_currency_aliases",
        "state_equations",
        "unit_bindings",
    }
    if (
        type(policy) is not dict
        or set(policy) != policy_fields
        or policy.get("matrix_kind") != MATRIX_KIND
        or policy.get("accepted_orientations") != ["CORE_ROWS_CURRENCY_COLUMNS"]
        or policy.get("grand_total_role") not in policy.get("currency_role_aliases", {})
        or policy.get("max_continuation_pages") != 1
        or type(policy.get("minimum_mapped_currency_roles")) is not int
        or policy["minimum_mapped_currency_roles"] < 2
    ):
        raise _error("currency-risk matrix policy is invalid")
    row_aliases = engine._aliases_by_role(topology)
    currency_aliases = engine._compile_alias_map(
        policy["currency_role_aliases"], label="currency role"
    )
    source_only_aliases = engine._compile_alias_map(
        policy["source_only_currency_aliases"], label="source-only currency"
    )
    mapped_surfaces = {
        engine._normalized(alias) for aliases in currency_aliases.values() for alias in aliases
    }
    source_only_surfaces = {
        engine._normalized(alias) for aliases in source_only_aliases.values() for alias in aliases
    }
    if mapped_surfaces & source_only_surfaces:
        raise _error("mapped and source-only currency aliases collide")
    required_rows = policy.get("required_row_roles")
    if (
        type(required_rows) is not list
        or not required_rows
        or len(required_rows) != len(set(required_rows))
        or not set(required_rows) <= set(row_aliases)
    ):
        raise _error("currency-risk required row roles are invalid")
    equations = policy.get("state_equations")
    compiled_equations = []
    if type(equations) is not list or not equations:
        raise _error("currency-risk equation declarations are absent")
    for raw in equations:
        if (
            type(raw) is not dict
            or set(raw) != {"required", "result_role", "term_multipliers"}
            or type(raw.get("required")) is not bool
            or raw.get("result_role") not in row_aliases
            or type(raw.get("term_multipliers")) is not dict
            or not raw["term_multipliers"]
            or any(
                role not in row_aliases or type(multiplier) is not int or multiplier == 0
                for role, multiplier in raw["term_multipliers"].items()
            )
            or raw["result_role"] in raw["term_multipliers"]
        ):
            raise _error("currency-risk equation declaration is invalid")
        compiled_equations.append(canonical_clone_v1(raw))
    if len({item["result_role"] for item in compiled_equations}) != len(compiled_equations):
        raise _error("currency-risk equation results collide")
    if not set(required_rows) <= {
        role
        for item in compiled_equations
        for role in [item["result_role"], *item["term_multipliers"]]
    }:
        raise _error("currency-risk required row roles are not equation-bound")
    units, unit_by_alias = engine._compile_units(policy["unit_bindings"])

    schema_fields = {
        "cell_role_bindings",
        "currency_branch_bindings",
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
    ):
        raise _error("currency-risk schema binding spec is invalid")
    branch_axis = schema_binding_spec["currency_branch_bindings"]
    branch_fields = {"currency_role", "report_norm_id"}
    if type(branch_axis) is not list or len(branch_axis) != len(currency_aliases):
        raise _error("currency-risk schema branch axis is incomplete")
    branch_ids: dict[str, int] = {}
    for raw in branch_axis:
        if (
            type(raw) is not dict
            or set(raw) != branch_fields
            or raw.get("currency_role") not in currency_aliases
            or raw["currency_role"] in branch_ids
            or type(raw.get("report_norm_id")) is not int
            or raw["report_norm_id"] <= 0
        ):
            raise _error("currency-risk schema branch binding is invalid")
        branch_ids[raw["currency_role"]] = raw["report_norm_id"]
    cell_axis = schema_binding_spec["cell_role_bindings"]
    cell_fields = {"currency_role", "report_norm_id", "row_role"}
    allowed_pairs = {
        (currency_role, row_role) for currency_role in currency_aliases for row_role in row_aliases
    }
    required_pairs = {
        (currency_role, row_role)
        for currency_role in currency_aliases
        for row_role in required_rows
    }
    if type(cell_axis) is not list:
        raise _error("currency-risk schema cell axis is invalid")
    cell_ids: dict[tuple[str, str], int] = {}
    for raw in cell_axis:
        key = (
            raw.get("currency_role") if type(raw) is dict else None,
            raw.get("row_role") if type(raw) is dict else None,
        )
        if (
            type(raw) is not dict
            or set(raw) != cell_fields
            or key not in allowed_pairs
            or key in cell_ids
            or type(raw.get("report_norm_id")) is not int
            or raw["report_norm_id"] <= 0
        ):
            raise _error("currency-risk schema cell binding is invalid")
        cell_ids[key] = raw["report_norm_id"]
    if not required_pairs <= set(cell_ids):
        raise _error("currency-risk schema required cell axis is incomplete")
    report_norm_ids = {
        schema_binding_spec["family_root_report_norm_id"],
        *branch_ids.values(),
        *cell_ids.values(),
    }
    expected_id_count = 1 + len(branch_ids) + len(cell_ids)
    if len(report_norm_ids) != expected_id_count:
        raise _error("currency-risk schema report norm IDs collide")
    query_policy = {
        "hard_negative_aliases": canonical_clone_v1(topology["hard_negative_aliases"]),
        "matrix_kind": MATRIX_KIND,
        "max_continuation_pages": 1,
        "minimum_mapped_currency_roles": policy["minimum_mapped_currency_roles"],
        "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
        "reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
    }
    return {
        "aliases_by_role": row_aliases,
        "claim_boundary": CURRENCY_RISK_CLAIM_BOUNDARY,
        "currency_branch_report_norm_id_by_role": branch_ids,
        "currency_cell_report_norm_id_by_pair": cell_ids,
        "currency_risk_mode": True,
        "grand_total_currency_role": policy["grand_total_role"],
        "currency_role_aliases_by_role": currency_aliases,
        "engine_format_version": engine.ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "family_id": topology["family_id"],
        "family_root_report_norm_id": schema_binding_spec["family_root_report_norm_id"],
        "query_policy": query_policy,
        "required_currency_row_roles": canonical_clone_v1(required_rows),
        "schema": canonical_clone_v1(schema_binding_spec),
        "source_only_currency_aliases_by_role": source_only_aliases,
        "state_equations": compiled_equations,
        "topology": canonical_clone_v1(topology),
        "unit_binding_by_alias": unit_by_alias,
        "unit_bindings": units,
    }


def _label_role(
    value: Any, *, aliases_by_role: Mapping[str, Sequence[str]]
) -> tuple[str | None, list[str]]:
    engine = _engine()
    folded_tokens = engine._normalized(value).split()
    while folded_tokens and folded_tokens[-1].isdigit():
        folded_tokens.pop()
    normalized_without_formula_suffix = " ".join(folded_tokens)
    matches = [
        (role, alias)
        for role, aliases in aliases_by_role.items()
        for alias in engine._valuation_label_matches_v1(normalized_without_formula_suffix, aliases)
    ]
    if not matches:
        return None, []
    longest = max(len(engine._normalized(alias)) for _role, alias in matches)
    roles = sorted({role for role, alias in matches if len(engine._normalized(alias)) == longest})
    return (roles[0] if len(roles) == 1 else None), roles


def _column_role(
    column: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[str | None, str | None, list[str]]:
    if compiled_specs.get("liquidity_risk_mode") is True:
        from bctc_ai.evaluation.gemini_json_liquidity_risk_matrix_v1 import (
            classify_liquidity_column_role_v1,
        )

        return classify_liquidity_column_role_v1(column, compiled_specs=compiled_specs)
    if compiled_specs.get("interest_rate_risk_mode") is True:
        from bctc_ai.evaluation.gemini_json_interest_rate_risk_matrix_v1 import (
            classify_interest_rate_column_role_v1,
        )

        return classify_interest_rate_column_role_v1(column, compiled_specs=compiled_specs)
    engine = _engine()
    members = engine._header_members(column)
    unit_aliases = sorted(compiled_specs["unit_binding_by_alias"], key=len, reverse=True)
    folded_members = []
    for member in members:
        folded = engine._normalized(member)
        for alias in unit_aliases:
            folded = re.sub(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", " ", folded)
        folded = " ".join(folded.split())
        if folded:
            folded_members.append(folded)
    all_aliases = {
        **compiled_specs["currency_role_aliases_by_role"],
        **compiled_specs["source_only_currency_aliases_by_role"],
    }
    candidates = []
    for role, aliases in all_aliases.items():
        for member in folded_members:
            for alias in aliases:
                folded_alias = engine._normalized(alias)
                if (
                    member == folded_alias
                    or member.startswith(folded_alias + " ")
                    or member.endswith(" " + folded_alias)
                ):
                    candidates.append((role, folded_alias))
    if not candidates:
        return None, None, []
    longest = max(len(alias) for _role, alias in candidates)
    roles = sorted({role for role, alias in candidates if len(alias) == longest})
    if len(roles) != 1:
        return None, None, roles
    role = roles[0]
    kind = (
        "MAPPED_CURRENCY"
        if role in compiled_specs["currency_role_aliases_by_role"]
        else "SOURCE_ONLY_CURRENCY"
    )
    return role, kind, roles


def classify_gemini_json_currency_risk_matrix_table_v1(
    table: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Inventory both axes, including partial/unmapped declared evidence."""

    engine = _engine()
    rows = table.get("rows") if type(table) is dict else None
    columns = table.get("columns") if type(table) is dict else None
    if type(rows) is not list or type(columns) is not list or not rows or not columns:
        raise _error("currency-risk table axes are invalid")
    if any(
        type(row) is not dict
        or type(row.get("values_exact")) is not list
        or len(row["values_exact"]) != len(columns)
        or type(row.get("hierarchy_path_exact")) is not list
        for row in rows
    ) or any(type(column) is not dict for column in columns):
        raise _error("currency-risk row or column vectors are invalid")
    reasons = []
    column_axis = []
    for ordinal, column in enumerate(columns, start=1):
        role, kind, matches = _column_role(column, compiled_specs=compiled_specs)
        active = any(
            row["values_exact"][ordinal - 1] is not None
            and (
                type(row["values_exact"][ordinal - 1]) is not str
                or bool(row["values_exact"][ordinal - 1].strip())
            )
            for row in rows
        )
        if len(matches) > 1:
            reasons.append("CURRENCY_COLUMN_MATCHES_MULTIPLE_DECLARED_ROLES")
        if column.get("value_kind") == "MONEY" and active and role is None:
            reasons.append("ACTIVE_MONEY_COLUMN_HAS_NO_DECLARED_CURRENCY_ROLE")
        column_axis.append(
            {
                "column_id": f"c{ordinal}",
                "header_path_exact": canonical_clone_v1(engine._header_members(column)),
                "kind": kind or "UNCLASSIFIED_COLUMN",
                "role": role,
                "role_matches": matches,
                "source_order": ordinal,
                "value_kind": column.get("value_kind"),
            }
        )
    declared_columns = [item for item in column_axis if item["role"] is not None]
    mapped_columns = [
        item
        for item in declared_columns
        if item["kind"] == "MAPPED_CURRENCY"
        and item["role"] != compiled_specs["grand_total_currency_role"]
    ]
    if (
        len({item["role"] for item in mapped_columns})
        < compiled_specs["query_policy"]["minimum_mapped_currency_roles"]
    ):
        reasons.append("MAPPED_CURRENCY_COLUMN_AXIS_INCOMPLETE")
    if len({item["role"] for item in declared_columns}) != len(declared_columns):
        reasons.append("DUPLICATE_DECLARED_CURRENCY_COLUMN_ROLE")

    row_axis = []
    for ordinal, row in enumerate(rows, start=1):
        if compiled_specs.get("liquidity_risk_mode") is True:
            from bctc_ai.evaluation.gemini_json_liquidity_risk_matrix_v1 import (
                classify_liquidity_row_role_v1,
            )

            role, matches = classify_liquidity_row_role_v1(
                row.get("label_exact"),
                aliases_by_role=compiled_specs["aliases_by_role"],
            )
        elif compiled_specs.get("interest_rate_risk_mode") is True:
            from bctc_ai.evaluation.gemini_json_interest_rate_risk_matrix_v1 import (
                classify_interest_rate_row_role_v1,
            )

            role, matches = classify_interest_rate_row_role_v1(
                row.get("label_exact"),
                aliases_by_role=compiled_specs["aliases_by_role"],
            )
        else:
            role, matches = _label_role(
                row.get("label_exact"),
                aliases_by_role=compiled_specs["aliases_by_role"],
            )
        active = any(
            value is not None and (type(value) is not str or bool(value.strip()))
            for value in row["values_exact"]
        )
        if len(matches) > 1:
            reasons.append("CORE_ROW_MATCHES_MULTIPLE_DECLARED_ROLES")
        row_axis.append(
            {
                "kind": "CORE_ROW" if role is not None else "SOURCE_ONLY_ROW",
                "label_exact": row.get("label_exact"),
                "role": role,
                "role_matches": matches,
                "row_id": f"r{ordinal}",
                "row_kind": row.get("row_kind"),
                "source_active": active,
                "source_order": ordinal,
            }
        )
    if compiled_specs.get("interest_rate_risk_mode") is True:
        from bctc_ai.evaluation.gemini_json_interest_rate_risk_matrix_v1 import (
            resolve_interest_rate_row_axis_v1,
        )

        row_axis = resolve_interest_rate_row_axis_v1(
            row_axis, aliases_by_role=compiled_specs["aliases_by_role"]
        )
    duplicate_roles = {
        item["role"]
        for item in row_axis
        if item["role"] is not None and sum(other["role"] == item["role"] for other in row_axis) > 1
    }
    for role in sorted(duplicate_roles):
        occurrences = [item for item in row_axis if item["role"] == role]
        active = [item for item in occurrences if item["source_active"]]
        if len(active) == 1:
            for item in occurrences:
                if item is active[0]:
                    continue
                item["kind"] = "DECLARED_INACTIVE_ROW_HEADING"
                item["role"] = None
        else:
            reasons.append("DUPLICATE_DECLARED_CURRENCY_CORE_ROW")
    mapped_rows = [item["role"] for item in row_axis if item["kind"] == "CORE_ROW"]
    missing = sorted(set(compiled_specs["required_currency_row_roles"]) - set(mapped_rows))
    reasons.extend(f"REQUIRED_CURRENCY_CORE_ROW_MISSING:{role}" for role in missing)
    status = "MATRIX_FRAGMENT" if declared_columns and mapped_rows and not reasons else "NOT_MATRIX"
    result = {
        "column_axis": column_axis,
        "column_declared_component_roles": sorted({item["role"] for item in declared_columns}),
        "component_axis": row_axis,
        "component_axis_sha256": canonical_json_sha256_v1(row_axis),
        "mapped_component_roles": sorted(set(mapped_rows)),
        "matrix_kind": MATRIX_KIND,
        "orientation": "CORE_ROWS_CURRENCY_COLUMNS" if status == "MATRIX_FRAGMENT" else None,
        "reasons": sorted(set(reasons)),
        "row_declared_component_roles": sorted(set(mapped_rows)),
        "status": status,
    }
    if compiled_specs.get("liquidity_risk_mode") is True and set(
        compiled_specs["required_currency_row_roles"]
    ) <= set(result["mapped_component_roles"]):
        from bctc_ai.evaluation.gemini_json_liquidity_risk_matrix_v1 import (
            build_liquidity_row_alignment_receipt_v1,
            validate_liquidity_row_alignment_receipt_v1,
        )

        result["liquidity_row_alignment_receipt"] = build_liquidity_row_alignment_receipt_v1(
            table, classification=result
        )
        validate_liquidity_row_alignment_receipt_v1(result["liquidity_row_alignment_receipt"])
    return result


def _row_signature(
    classification: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> list[Any]:
    required = set(compiled_specs["required_currency_row_roles"])
    return [
        [item["kind"], item["role"]]
        for item in classification["component_axis"]
        if item["kind"] == "CORE_ROW" and item["role"] in required
    ]


def _currency_forward_table_marker_v1(value: Any) -> bool:
    folded = _engine()._normalized(value)
    return bool(
        re.search(r"\bnhu sau\b", folded)
        and (
            (
                re.search(r"\bgia tri ghi so\b", folded)
                and re.search(r"\btai san\b", folded)
                and re.search(r"\b(?:ngoai te|loai tien te)\b", folded)
            )
            or (
                re.search(r"\bphan loai\b", folded)
                and re.search(r"\btai san\b", folded)
                and re.search(r"\b(?:ngoai te|loai tien te)\b", folded)
            )
        )
    )


def _period_date_from_currency_table_v1(
    *,
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    table_ordinal: int,
) -> tuple[str | None, list[dict[str, Any]], list[str]]:
    """Resolve the narrowest unique date without a broad title overriding it."""

    engine = _engine()
    header_surfaces = [
        member
        for column in table.get("columns", [])
        if type(column) is dict
        for member in engine._header_members(column)
    ]
    axes = [
        ("CURRENCY_COLUMN_HEADERS", header_surfaces),
        ("TABLE_TITLE", [table.get("title_exact")]),
    ]
    if table_ordinal == 1:
        axes.append(
            (
                "CURRENCY_TABLE_INTRO_NARRATIVE",
                [
                    surface
                    for surface in section.get("narratives_exact", [])
                    if _currency_forward_table_marker_v1(surface)
                ],
            )
        )
    evidence = []
    for source_kind, surfaces in axes:
        dates = sorted(
            {
                item.isoformat()
                for surface in surfaces
                for item in engine._header_dates(surface or "")
            }
        )
        evidence.append(
            {
                "dates": dates,
                "source_exact_axis": canonical_clone_v1(surfaces),
                "source_kind": source_kind,
            }
        )
        if len(dates) > 1:
            return None, evidence, [f"{source_kind}_PERIOD_DATE_NOT_UNIQUE"]
        if len(dates) == 1:
            return dates[0], evidence, []
    return None, evidence, []


def _currency_document_reporting_date_receipt_v1(
    pages: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Select the latest typed statement date and its latest explicit comparator."""

    if compiled_specs is not None and (
        compiled_specs.get("interest_rate_risk_mode") is True
        or compiled_specs.get("liquidity_risk_mode") is True
    ):
        from bctc_ai.evaluation.gemini_json_interest_rate_risk_matrix_v1 import (
            interest_rate_document_reporting_date_receipt_v1,
        )

        return interest_rate_document_reporting_date_receipt_v1(list(pages))
    base = _engine()._valuation_document_reporting_date_receipt_v1(pages)
    evidence = base.get("evidence") if type(base) is dict else None
    evidence = evidence if type(evidence) is list else []
    current_candidates = sorted(
        {
            item.get("current_date")
            for item in evidence
            if type(item) is dict and type(item.get("current_date")) is str
        }
    )
    current_date = current_candidates[-1] if current_candidates else None
    comparative_candidates = sorted(
        {
            item.get("comparative_date")
            for item in evidence
            if type(item) is dict
            and type(item.get("comparative_date")) is str
            and type(current_date) is str
            and item["comparative_date"] < current_date
        }
    )
    comparative_date = comparative_candidates[-1] if comparative_candidates else None
    material = {
        "base_receipt": canonical_clone_v1(base),
        "comparative_date": comparative_date,
        "current_date": current_date,
        "rule": "LATEST_TYPED_PRIMARY_STATEMENT_DATE_AND_LATEST_EXPLICIT_COMPARATOR",
        "status": "UNIQUE_LATEST_TYPED_DOCUMENT_REPORTING_DATE" if current_date else "NOT_UNIQUE",
    }
    return {**material, "receipt_sha256": canonical_json_sha256_v1(material)}


def coalesce_gemini_json_currency_risk_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select one current/comparative matrix cluster under an exact owner."""

    engine = _engine()
    pages = engine._selected_page_record_axis(page_records)
    inventory = []
    owner_markers = []
    continuation_markers = []
    reset_markers = []
    period_markers = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if type(section) is not dict:
                continue
            section_id = f"s{section_ordinal}"
            surfaces = [section.get("title_exact"), *(section.get("narratives_exact") or [])]
            title_dates = sorted(
                item.isoformat() for item in engine._header_dates(section.get("title_exact") or "")
            )
            title_folded = engine._normalized(section.get("title_exact"))
            if len(title_dates) == 1 and any(
                marker in title_folded
                for marker in ("tai ngay", "ket thuc ngay", "ket thuc cung ngay")
            ):
                period_markers.append(
                    {
                        "period_date": title_dates[0],
                        "position": [record["selected_page_ordinal"], section_ordinal, 0, 0],
                        "source_exact": section.get("title_exact"),
                        "source_kind": "BOUNDED_REPORT_SECTION_TITLE",
                    }
                )
            for surface_ordinal, source_exact in enumerate(surfaces):
                position = [
                    record["selected_page_ordinal"],
                    section_ordinal,
                    0,
                    surface_ordinal,
                ]
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
                    owner_markers.append(
                        {"alias": owner, "position": position, "source_exact": source_exact}
                    )
                if engine._valuation_forward_table_marker_v1(
                    source_exact
                ) or _currency_forward_table_marker_v1(source_exact):
                    continuation_markers.append(
                        {
                            "position": position,
                            "source_exact": source_exact,
                            "source_kind": "EXPLICIT_FORWARD_TABLE_NARRATIVE",
                        }
                    )
                if reset is not None:
                    reset_markers.append(
                        {"alias": reset, "position": position, "source_exact": source_exact}
                    )
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, table in enumerate(tables, start=1):
                if type(table) is not dict:
                    continue
                position = [
                    record["selected_page_ordinal"],
                    section_ordinal,
                    1,
                    table_ordinal,
                ]
                for source_exact in (table.get("title_exact"),):
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
                        owner_markers.append(
                            {"alias": owner, "position": position, "source_exact": source_exact}
                        )
                    if reset is not None:
                        reset_markers.append(
                            {"alias": reset, "position": position, "source_exact": source_exact}
                        )
                classification = classify_gemini_json_currency_risk_matrix_table_v1(
                    table, compiled_specs=compiled_specs
                )
                declared_rows = classification["row_declared_component_roles"]
                non_total_column_axis = [
                    column
                    for column in classification["column_axis"]
                    if column["role"] is not None
                    and column["role"] != compiled_specs["grand_total_currency_role"]
                ]
                strong_declared_columns = [
                    column
                    for column in non_total_column_axis
                    if column["role"] != "OTHER"
                    or any(
                        re.search(r"\b(?:ngoai te|tien te|dong tien)\b", engine._normalized(member))
                        for member in column["header_path_exact"]
                    )
                ]
                # Any table carrying both declared axes is inventoried.  A
                # partial table can therefore never disappear as a negative.
                # The single bare alias "Khác" is deliberately weak because
                # it is also a ubiquitous business-segment column; an exact
                # currency token or explicit currency phrase remains strong.
                if strong_declared_columns and declared_rows:
                    local_date, period_evidence, period_reasons = (
                        _period_date_from_currency_table_v1(
                            section=section,
                            table=table,
                            table_ordinal=table_ordinal,
                        )
                    )
                    inventory.append(
                        {
                            "classification": classification,
                            "continuation": table.get("continuation"),
                            "local_period_date": local_date,
                            "period_evidence": period_evidence,
                            "period_reasons": period_reasons,
                            "position": position,
                            "record": record,
                            "section_id": section_id,
                            "table_id": f"t{table_ordinal}",
                        }
                    )
    selected = [item for item in inventory if item["classification"]["status"] == "MATRIX_FRAGMENT"]
    reasons = [
        reason
        for item in inventory
        if item["classification"]["status"] != "MATRIX_FRAGMENT"
        for reason in item["classification"]["reasons"]
    ]
    if inventory and len(selected) != len(inventory):
        reasons.append("INCOMPLETE_DECLARED_CURRENCY_RISK_TABLE_PRESENT")
    if len(selected) not in {0, 1, 2}:
        reasons.append("MORE_THAN_TWO_CURRENCY_RISK_PERIOD_TABLES_UNDER_DOCUMENT_OWNER")
    if len(selected) == 2 and not same_typed_json_v1(
        _row_signature(selected[0]["classification"], compiled_specs=compiled_specs),
        _row_signature(selected[1]["classification"], compiled_specs=compiled_specs),
    ):
        reasons.append("CURRENCY_RISK_PERIOD_TABLE_ROW_POPULATIONS_DIFFER")

    reporting_date_receipt = _currency_document_reporting_date_receipt_v1(
        pages, compiled_specs=compiled_specs
    )
    period_assignments = []
    for item in selected:
        reasons.extend(item["period_reasons"])
        period_date = item["local_period_date"]
        source = "LOCAL_TABLE_OR_SECTION_DATE"
        if period_date is None and len(selected) == 1:
            prior = [
                marker
                for marker in period_markers
                if marker["position"] <= item["position"]
                and item["position"][0] - marker["position"][0]
                <= compiled_specs["query_policy"]["max_continuation_pages"]
            ]
            if prior:
                marker = max(prior, key=lambda value: value["position"])
                period_date = marker["period_date"]
                source = "BOUNDED_PRECEDING_REPORT_HEADING"
                item["period_evidence"].append(canonical_clone_v1(marker))
        period_assignments.append(
            {
                "page_json_version_id": item["record"]["page_json_version_id"],
                "period_date": period_date,
                "period_evidence": canonical_clone_v1(item["period_evidence"]),
                "section_id": item["section_id"],
                "source": source,
                "table_id": item["table_id"],
            }
        )
    if (
        selected
        and reporting_date_receipt.get("status") == "UNIQUE_LATEST_TYPED_DOCUMENT_REPORTING_DATE"
    ):
        expected_document_dates = (
            [reporting_date_receipt.get("current_date")]
            if len(selected) == 1
            else [
                reporting_date_receipt.get("current_date"),
                reporting_date_receipt.get("comparative_date"),
            ]
        )
        for assignment, expected_date in zip(
            period_assignments, expected_document_dates, strict=True
        ):
            if assignment["period_date"] is None and type(expected_date) is str:
                assignment["period_date"] = expected_date
                assignment["source"] = "TYPED_DOCUMENT_REPORTING_DATE_AXIS"
                assignment["period_evidence"].append(
                    {
                        "period_date": expected_date,
                        "reporting_date_receipt": canonical_clone_v1(reporting_date_receipt),
                        "source_kind": "TYPED_DOCUMENT_REPORTING_DATE_AXIS",
                    }
                )
            elif (
                type(assignment["period_date"]) is str
                and type(expected_date) is str
                and assignment["period_date"] != expected_date
            ):
                reasons.append("CURRENCY_RISK_LOCAL_PERIOD_CONFLICTS_DOCUMENT_REPORTING_AXIS")
    if any(item["period_date"] is None for item in period_assignments):
        reasons.append("CURRENCY_RISK_PERIOD_DATE_UNRESOLVED")
    distinct_dates = {item["period_date"] for item in period_assignments if item["period_date"]}
    if len(selected) == 2 and len(distinct_dates) != 2:
        reasons.append("TWO_CURRENCY_RISK_TABLE_PERIOD_DATES_NOT_DISTINCT")
    if selected and len(distinct_dates) == len(selected):
        ordered = sorted(distinct_dates, reverse=True)
        roles = {
            value: "CURRENT_PERIOD" if ordinal == 0 else "COMPARATIVE_PERIOD"
            for ordinal, value in enumerate(ordered)
        }
        for assignment in period_assignments:
            assignment["period_role"] = roles[assignment["period_date"]]

    owner_receipt = None
    if selected:
        first_position = min(item["position"] for item in selected)
        last_position = max(item["position"] for item in selected)
        first_selected = min(selected, key=lambda item: item["position"])
        prior_owners = [
            marker
            for marker in owner_markers
            if marker["position"] <= first_position
            and first_position[0] - marker["position"][0]
            <= compiled_specs["query_policy"]["max_continuation_pages"]
            and (
                marker["position"][0] == first_position[0]
                or first_selected["continuation"] == "CONTINUES_FROM_PREVIOUS_PAGE"
                or any(
                    marker["position"] <= continuation["position"] < first_position
                    for continuation in continuation_markers
                )
                or (
                    (
                        compiled_specs.get("interest_rate_risk_mode") is True
                        or compiled_specs.get("liquidity_risk_mode") is True
                    )
                    and first_position[0] - marker["position"][0] == 1
                    and not any(
                        marker["position"] < reset["position"] < first_position
                        for reset in reset_markers
                    )
                )
            )
        ]
        if not prior_owners:
            reasons.append("EXPLICIT_BOUNDED_CURRENCY_RISK_OWNER_NOT_VISIBLE")
        else:
            owner = max(prior_owners, key=lambda item: item["position"])
            fenced_resets = [
                marker
                for marker in reset_markers
                if owner["position"] <= marker["position"] <= last_position
            ]
            if fenced_resets:
                reasons.append("OWNER_TO_CURRENCY_RISK_MATRIX_INTERVAL_CONTAINS_RESET")
            continuation_evidence = None
            if owner["position"][0] != first_position[0]:
                narrative_markers = [
                    marker
                    for marker in continuation_markers
                    if owner["position"] <= marker["position"] < first_position
                ]
                if narrative_markers:
                    continuation_evidence = max(
                        narrative_markers, key=lambda item: item["position"]
                    )
                elif first_selected["continuation"] == "CONTINUES_FROM_PREVIOUS_PAGE":
                    continuation_evidence = {
                        "position": first_selected["position"],
                        "source_exact": first_selected["continuation"],
                        "source_kind": "STRUCTURED_TABLE_CONTINUATION",
                    }
                elif (
                    compiled_specs.get("interest_rate_risk_mode") is True
                    or compiled_specs.get("liquidity_risk_mode") is True
                ) and first_position[0] - owner["position"][0] == 1:
                    continuation_evidence = {
                        "position": first_selected["position"],
                        "source_exact": owner["source_exact"],
                        "source_kind": (
                            "BOUNDED_ADJACENT_INTEREST_OWNER_INTRO_AND_RESET_FREE_TABLE"
                        ),
                    }
            owner_receipt = {
                "continuation_evidence": continuation_evidence,
                "document_reporting_date_receipt": reporting_date_receipt,
                "owner_alias": owner["alias"],
                "owner_position": owner["position"],
                "owner_source_exact": owner["source_exact"],
                "period_assignments": period_assignments,
                "reset_fence_axis": fenced_resets,
                "rule": "LATEST_EXPLICIT_OWNER_WITHIN_ONE_PAGE_RESET_FREE_INTERVAL",
            }
    regions = [
        engine._matrix_region(item, fragment_ordinal=ordinal)
        for ordinal, item in enumerate(selected, start=1)
    ]
    if regions:
        try:
            engine._checked_region_axis(regions)
        except ValueError:
            reasons.append("CURRENCY_RISK_REGION_AXIS_IS_NOT_ONE_OR_TWO_ADJACENT_FRAGMENTS")
    inventory_receipt = [
        {
            "classification": canonical_clone_v1(item["classification"]),
            "continuation": item["continuation"],
            "disposition": (
                "SELECTED_CURRENCY_RISK_FRAGMENT"
                if item in selected
                else "UNSELECTED_DECLARED_CURRENCY_RISK_TABLE"
            ),
            "local_period_date": item["local_period_date"],
            "page_json_version_id": item["record"]["page_json_version_id"],
            "period_evidence": canonical_clone_v1(item["period_evidence"]),
            "physical_page": item["record"]["physical_page"],
            "position": item["position"],
            "section_id": item["section_id"],
            "table_id": item["table_id"],
        }
        for item in inventory
    ]
    unit_context = engine._document_unit_context_v1(pages, compiled_specs=compiled_specs)
    first = pages[0]
    status = (
        engine.NOT_OBSERVED
        if not inventory
        else engine.READY
        if selected and not reasons and owner_receipt is not None
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


def _cell(
    *,
    value: Any,
    region: Mapping[str, Any],
    row_id: str,
    column_id: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    ref = {
        "column_id": column_id,
        "locator": canonical_clone_v1(region),
        "row_id": row_id,
    }
    source_text = value
    normalization_state = None
    if (
        compiled_specs.get("interest_rate_risk_mode") is True
        or compiled_specs.get("liquidity_risk_mode") is True
    ):
        from bctc_ai.evaluation.gemini_json_interest_rate_risk_matrix_v1 import (
            normalize_interest_rate_money_cell_v1,
        )

        value, normalization_state = normalize_interest_rate_money_cell_v1(value)
    if value is None or type(value) is str and not value.strip():
        return {
            "cell_ref": ref,
            "coefficient": None,
            "source_text": source_text,
            "state": normalization_state or "BLANK",
        }
    if type(value) is not str:
        return {
            "cell_ref": ref,
            "coefficient": None,
            "source_text": source_text,
            "state": "INVALID_NON_STRING_SOURCE_CELL",
        }
    try:
        parsed = _money(value)
    except ValueError:
        parsed = None
    if parsed is None:
        return {
            "cell_ref": ref,
            "coefficient": None,
            "source_text": source_text,
            "state": "INVALID_SOURCE_CELL",
        }
    return {
        **parsed,
        "cell_ref": ref,
        "source_text": source_text,
        "state": normalization_state or parsed["state"],
    }


def _equation(
    *,
    declaration: Mapping[str, Any],
    cells_by_role: dict[str, dict[str, Any]],
    currency_role: str,
) -> tuple[dict[str, Any], list[str]]:
    roles = [*declaration["term_multipliers"], declaration["result_role"]]
    cells = {
        role: cells_by_role.get(
            role,
            {
                "cell_ref": None,
                "coefficient": None,
                "source_text": None,
                "state": "ABSENT_SOURCE_ROW",
            },
        )
        for role in roles
    }
    unknown = [role for role, cell in cells.items() if cell["coefficient"] is None]
    reasons = []
    derived_role = None
    if (
        len(unknown) == 1
        and cells[unknown[0]]["state"] in {"BLANK", "NORMALIZED_TEXT_NULL_BLANK"}
        and not any(cell["state"] == "ABSENT_SOURCE_ROW" for cell in cells.values())
    ):
        role = unknown[0]
        if role == declaration["result_role"]:
            solution = sum(
                cells[term]["coefficient"] * multiplier
                for term, multiplier in declaration["term_multipliers"].items()
                if cells[term]["coefficient"] is not None
            )
        else:
            multiplier = declaration["term_multipliers"][role]
            known_terms = sum(
                cells[term]["coefficient"] * term_multiplier
                for term, term_multiplier in declaration["term_multipliers"].items()
                if term != role and cells[term]["coefficient"] is not None
            )
            result = cells[declaration["result_role"]]["coefficient"]
            solution = (result - known_terms) // multiplier if result is not None else None
            if result is not None and (result - known_terms) % multiplier:
                solution = None
        if solution == 0:
            cells_by_role[role] = {**canonical_clone_v1(cells_by_role[role])}
            cells_by_role[role]["coefficient"] = 0
            cells_by_role[role]["state"] = "BLANK_ZERO_AFTER_ONE_UNKNOWN_EQUATION_EXACT"
            cells[role] = cells_by_role[role]
            unknown = []
            derived_role = role
    status = "NOT_TESTABLE"
    computed = None
    if not unknown:
        computed = sum(
            cells[term]["coefficient"] * multiplier
            for term, multiplier in declaration["term_multipliers"].items()
        )
        status = (
            "EXACT" if computed == cells[declaration["result_role"]]["coefficient"] else "MISMATCH"
        )
        if status == "MISMATCH":
            reasons.append(f"CURRENCY_CORE_EQUATION_MISMATCH:{currency_role}")
    return (
        {
            "computed_value": computed,
            "currency_role": currency_role,
            "derived_zero_role": derived_role,
            "equation_kind": (
                "+".join(
                    f"{multiplier}*{role}"
                    for role, multiplier in declaration["term_multipliers"].items()
                )
                + "="
                + declaration["result_role"]
            ),
            "required": declaration["required"],
            "result_cell": canonical_clone_v1(cells[declaration["result_role"]]),
            "result_role": declaration["result_role"],
            "status": status,
            "term_cells": [
                {
                    "cell": canonical_clone_v1(cells[role]),
                    "multiplier": multiplier,
                    "role": role,
                }
                for role, multiplier in declaration["term_multipliers"].items()
            ],
        },
        reasons,
    )


def _mapping_value(
    *, cell: Mapping[str, Any], currency_role: str, period: Mapping[str, Any], row_role: str
) -> dict[str, Any]:
    return {
        "axis_role": currency_role,
        "cell_ref": canonical_clone_v1(cell["cell_ref"]),
        "coefficient": cell["coefficient"],
        "period_date": period["period_date"],
        "period_role": period["period_role"],
        "row_role": row_role,
        "source_text": cell["source_text"],
        "state": cell["state"],
    }


def _nonclosing_currency_frontier_v1(
    *,
    cells_by_role: Mapping[str, Mapping[str, Any]],
    column_axis: Mapping[str, Any],
    declaration: Mapping[str, Any],
    equation: Mapping[str, Any],
    period_assignment: Mapping[str, Any],
    region: Mapping[str, Any],
    required_row_roles: Sequence[str],
) -> dict[str, Any] | None:
    """Retain a visible non-closing source axis without changing its values."""

    status = equation["status"]
    if status == "EXACT":
        return None
    declaration_roles = {*declaration["term_multipliers"], declaration["result_role"]}
    optional_surface_roles = sorted(declaration_roles - set(required_row_roles))
    visible_optional_roles = [
        role
        for role in optional_surface_roles
        if type(cells_by_role.get(role)) is dict and cells_by_role[role].get("cell_ref") is not None
    ]
    if not declaration["required"] and status == "NOT_TESTABLE" and not visible_optional_roles:
        return None
    return {
        "column_id": column_axis["column_id"],
        "currency_kind": column_axis["kind"],
        "currency_role": column_axis["role"],
        "equation_kind": equation["equation_kind"],
        "equation_required": declaration["required"],
        "equation_result_role": declaration["result_role"],
        "equation_status": status,
        "period_date": period_assignment["period_date"],
        "period_role": period_assignment["period_role"],
        "region": canonical_clone_v1(region),
        "source_evidence_roles": visible_optional_roles,
    }


def build_currency_risk_mappings_v1(
    *,
    compiled_specs: Mapping[str, Any],
    canonical_unit: str,
    period_assignments: Sequence[Mapping[str, Any]],
    cells_by_period_currency_row: Mapping[tuple[str, str, str], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Project only schema-supported visible or equation-proven cells."""

    periods = {item["period_role"]: item for item in period_assignments}
    if set(periods) not in ({"CURRENT_PERIOD"}, {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}):
        raise _error("currency-risk mapping period axis is incomplete")
    mappings = []
    for role, report_norm_id in [
        ("FAMILY", compiled_specs["family_root_report_norm_id"]),
        *[
            (f"CURRENCY_BRANCH:{currency_role}", report_norm_id)
            for currency_role, report_norm_id in compiled_specs[
                "currency_branch_report_norm_id_by_role"
            ].items()
        ],
    ]:
        mapping = {
            "item_mapping_id": "gjeqmfv1:item:pending",
            "report_norm_id": report_norm_id,
            "role": role,
            "row_id": f"structural:{role}",
            "unit": None,
            "values": [],
        }
        mapping["item_mapping_id"] = "gjeqmfv1:item:" + canonical_json_sha256_v1(
            {key: value for key, value in mapping.items() if key != "item_mapping_id"}
        )
        mappings.append(mapping)
    for (currency_role, row_role), report_norm_id in compiled_specs[
        "currency_cell_report_norm_id_by_pair"
    ].items():
        values = []
        for period_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
            period = periods.get(period_role)
            if period is None:
                continue
            cell = cells_by_period_currency_row.get((period_role, currency_role, row_role))
            if cell is not None and type(cell.get("coefficient")) is int:
                values.append(
                    _mapping_value(
                        cell=cell,
                        currency_role=currency_role,
                        period=period,
                        row_role=row_role,
                    )
                )
        if not values:
            continue
        role = f"{currency_role}:{row_role}"
        mapping = {
            "item_mapping_id": "gjeqmfv1:item:pending",
            "report_norm_id": report_norm_id,
            "role": role,
            "row_id": f"currency:{currency_role}:{row_role}",
            "unit": canonical_unit,
            "values": values,
        }
        mapping["item_mapping_id"] = "gjeqmfv1:item:" + canonical_json_sha256_v1(
            {key: value for key, value in mapping.items() if key != "item_mapping_id"}
        )
        mappings.append(mapping)
    return mappings


def evaluate_gemini_json_currency_risk_cluster_v1(
    *,
    regions: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    document_unit_context_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Close all source currency rows before emitting schema mappings."""

    engine = _engine()
    checked_regions = engine._checked_region_axis(regions)
    expected_query = engine.build_gemini_json_equity_matrix_region_query_receipt_v1(
        checked_regions, owner_receipt=query_receipt.get("owner_receipt", {})
    )
    if not same_typed_json_v1(expected_query, query_receipt):
        raise _error("currency-risk query receipt drifted")
    periods = query_receipt.get("owner_receipt", {}).get("period_assignments")
    if type(periods) is not list or len(periods) != len(checked_regions):
        raise _error("currency-risk period assignment axis is incomplete")
    assignment_by_key = {
        (item.get("page_json_version_id"), item.get("section_id"), item.get("table_id")): item
        for item in periods
        if type(item) is dict
    }
    reasons = []
    tables = []
    table_receipts = []
    all_equations = []
    all_nonclosing_frontiers = []
    cells_by_period_currency_row: dict[tuple[str, str, str], dict[str, Any]] = {}
    for region in checked_regions:
        page = page_json_by_version.get(region["page_json_version_id"])
        if type(page) is not dict:
            raise _error("currency-risk selected canonical page is absent")
        _section, table = engine._source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        tables.append(table)
        classification = classify_gemini_json_currency_risk_matrix_table_v1(
            table, compiled_specs=compiled_specs
        )
        reasons.extend(classification["reasons"])
        effective_values_by_row_id = {}
        if compiled_specs.get("liquidity_risk_mode") is True:
            alignment = classification.get("liquidity_row_alignment_receipt")
            if type(alignment) is not dict or type(alignment.get("effective_rows")) is not list:
                reasons.append("LIQUIDITY_RISK_ROW_ALIGNMENT_RECEIPT_MISSING")
            else:
                effective_values_by_row_id = {
                    item["row_id"]: item["effective_values_exact"]
                    for item in alignment["effective_rows"]
                }
        assignment = assignment_by_key.get(
            (region["page_json_version_id"], region["section_id"], region["table_id"])
        )
        if (
            type(assignment) is not dict
            or assignment.get("period_role") not in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
            or type(assignment.get("period_date")) is not str
        ):
            reasons.append("CURRENCY_RISK_FRAGMENT_PERIOD_ASSIGNMENT_MISSING")
            continue
        row_by_id = {f"r{ordinal}": row for ordinal, row in enumerate(table["rows"], start=1)}
        resolved_columns = []
        exact_required_currency_roles = set()
        for column_axis in classification["column_axis"]:
            if column_axis["role"] is None:
                continue
            currency_role = column_axis["role"]
            column_index = column_axis["source_order"] - 1
            cells_by_role = {}
            for row_axis in classification["component_axis"]:
                if row_axis["kind"] != "CORE_ROW":
                    continue
                source_values = effective_values_by_row_id.get(
                    row_axis["row_id"], row_by_id[row_axis["row_id"]]["values_exact"]
                )
                cell = _cell(
                    value=source_values[column_index],
                    region=region,
                    row_id=row_axis["row_id"],
                    column_id=column_axis["column_id"],
                    compiled_specs=compiled_specs,
                )
                if cell["state"].startswith("INVALID"):
                    reasons.append(
                        f"INVALID_CURRENCY_RISK_CORE_CELL:{currency_role}:{row_axis['role']}"
                    )
                cells_by_role[row_axis["role"]] = cell
            equations = []
            nonclosing_frontiers = []
            for declaration in compiled_specs["state_equations"]:
                equation, _equation_reasons = _equation(
                    declaration=declaration,
                    cells_by_role=cells_by_role,
                    currency_role=currency_role,
                )
                equations.append(equation)
                frontier = _nonclosing_currency_frontier_v1(
                    cells_by_role=cells_by_role,
                    column_axis=column_axis,
                    declaration=declaration,
                    equation=equation,
                    period_assignment=assignment,
                    region=region,
                    required_row_roles=compiled_specs["required_currency_row_roles"],
                )
                if frontier is not None:
                    nonclosing_frontiers.append(frontier)
            required_equations_exact = all(
                equation["status"] == "EXACT"
                for declaration, equation in zip(
                    compiled_specs["state_equations"], equations, strict=True
                )
                if declaration["required"]
            )
            if column_axis["kind"] == "MAPPED_CURRENCY" and required_equations_exact:
                exact_required_currency_roles.add(currency_role)
            all_equations.extend(canonical_clone_v1(equations))
            all_nonclosing_frontiers.extend(canonical_clone_v1(nonclosing_frontiers))
            resolved_columns.append(
                {
                    "column_axis": canonical_clone_v1(column_axis),
                    "core_cells_by_role": canonical_clone_v1(cells_by_role),
                    "equations": equations,
                    "nonclosing_frontiers": nonclosing_frontiers,
                }
            )
            if column_axis["kind"] == "MAPPED_CURRENCY" and (
                compiled_specs.get("liquidity_risk_mode") is not True or required_equations_exact
            ):
                for row_role, cell in cells_by_role.items():
                    if type(cell.get("coefficient")) is int:
                        cells_by_period_currency_row[
                            (assignment["period_role"], currency_role, row_role)
                        ] = cell
        if (
            compiled_specs.get("liquidity_risk_mode") is True
            and (
                len(exact_required_currency_roles)
                < compiled_specs["query_policy"]["minimum_mapped_currency_roles"]
                or compiled_specs["grand_total_currency_role"] not in exact_required_currency_roles
            )
        ) or (
            compiled_specs.get("liquidity_risk_mode") is not True
            and len(exact_required_currency_roles)
            < compiled_specs["query_policy"]["minimum_mapped_currency_roles"]
        ):
            reasons.append("CURRENCY_RISK_REQUIRED_EQUATION_COVERAGE_INCOMPLETE")
        table_receipts.append(
            {
                "classification": classification,
                "period_assignment": canonical_clone_v1(assignment),
                "region": canonical_clone_v1(region),
                "resolved_columns": resolved_columns,
            }
        )
    unit_receipt, unit_reasons = engine._resolve_cluster_unit(
        tables=tables,
        compiled_specs=compiled_specs,
        document_unit_context_evidence=document_unit_context_evidence,
    )
    reasons.extend(unit_reasons)
    reasons = sorted(set(reasons))
    mappings = []
    if not reasons and unit_receipt["canonical_unit"] is not None:
        mappings = build_currency_risk_mappings_v1(
            compiled_specs=compiled_specs,
            canonical_unit=unit_receipt["canonical_unit"],
            period_assignments=periods,
            cells_by_period_currency_row=cells_by_period_currency_row,
        )
        if len(mappings) <= 1 + len(compiled_specs["currency_branch_report_norm_id_by_role"]):
            reasons.append("CURRENCY_RISK_SCHEMA_CELL_MAPPING_AXIS_EMPTY")
            mappings = []
    first = checked_regions[0]
    closure = {
        "equations": all_equations,
        "matrix_kind": MATRIX_KIND,
        "nonclosing_currency_frontiers": all_nonclosing_frontiers,
        "period_assignments": canonical_clone_v1(periods),
        "query_receipt": canonical_clone_v1(query_receipt),
        "rule": (
            "DECLARED_CURRENCY_CORE_ROWS_MINIMUM_EXACT_REQUIRED_EQUATION_COVERAGE_"
            "WITH_RAW_NONCLOSING_SOURCE_RETENTION"
        ),
        "table_receipts": table_receipts,
        "unit_receipt": unit_receipt,
    }
    material = {
        "claim_boundary": (
            compiled_specs["claim_boundary"]
            if compiled_specs.get("liquidity_risk_mode") is True
            else CURRENCY_RISK_CLAIM_BOUNDARY
        ),
        "closure_receipt": closure,
        "component_regions": canonical_clone_v1(checked_regions),
        "document_id": first["document_id"],
        "family_id": compiled_specs["family_id"],
        "mappings": mappings if not reasons else [],
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": engine.READY if not reasons else engine.UNRESOLVED,
        "table_id": first["table_id"],
    }
    return {
        "candidate_id": "gjeqmfv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_currency_risk_candidate_binding_v1(
    candidate: Any,
    *,
    document: Mapping[str, Any],
    cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal the self-contained currency graph before SQLite source replay."""

    engine = _engine()
    candidate_fields = {
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
        "equations",
        "matrix_kind",
        "nonclosing_currency_frontiers",
        "period_assignments",
        "query_receipt",
        "rule",
        "table_receipts",
        "unit_receipt",
    }
    regions = cluster["component_regions"]
    first = regions[0]
    closure = candidate.get("closure_receipt") if type(candidate) is dict else None
    if (
        type(candidate) is not dict
        or set(candidate) != candidate_fields
        or candidate.get("claim_boundary")
        != (
            compiled_specs["claim_boundary"]
            if compiled_specs.get("liquidity_risk_mode") is True
            else CURRENCY_RISK_CLAIM_BOUNDARY
        )
        or candidate.get("family_id") != compiled_specs["family_id"]
        or candidate.get("document_id") != first["document_id"]
        or candidate.get("page_json_version_id") != first["page_json_version_id"]
        or candidate.get("physical_page") != first["physical_page"]
        or candidate.get("section_id") != first["section_id"]
        or candidate.get("table_id") != first["table_id"]
        or candidate.get("source_logical_name") != document["source_logical_name"]
        or candidate.get("source_sha256") != document["source_sha256"]
        or not same_typed_json_v1(candidate.get("component_regions"), regions)
        or candidate.get("status") not in {engine.READY, engine.UNRESOLVED}
        or type(candidate.get("reasons")) is not list
        or candidate["reasons"] != sorted(set(candidate["reasons"]))
        or type(candidate.get("mappings")) is not list
        or type(closure) is not dict
        or set(closure) != closure_fields
        or closure.get("matrix_kind") != MATRIX_KIND
        or closure.get("rule")
        != (
            "DECLARED_CURRENCY_CORE_ROWS_MINIMUM_EXACT_REQUIRED_EQUATION_COVERAGE_"
            "WITH_RAW_NONCLOSING_SOURCE_RETENTION"
        )
        or type(closure.get("equations")) is not list
        or type(closure.get("nonclosing_currency_frontiers")) is not list
        or type(closure.get("period_assignments")) is not list
        or type(closure.get("table_receipts")) is not list
        or type(closure.get("unit_receipt")) is not dict
    ):
        raise _error("currency-risk candidate structure drifted")
    expected_query = engine.build_gemini_json_equity_matrix_region_query_receipt_v1(
        regions, owner_receipt=cluster["owner_receipt"]
    )
    if not same_typed_json_v1(closure["query_receipt"], expected_query):
        raise _error("currency-risk candidate query receipt drifted")
    expected_periods = cluster["owner_receipt"].get("period_assignments")
    if not same_typed_json_v1(closure["period_assignments"], expected_periods):
        raise _error("currency-risk candidate period axis drifted")
    unit = closure["unit_receipt"]
    if (
        set(unit)
        != {
            "canonical_unit",
            "document_unit_context_evidence",
            "fragment_unit_axes",
            "source",
        }
        or not same_typed_json_v1(
            unit["document_unit_context_evidence"],
            cluster["document_unit_context_evidence"],
        )
        or type(unit.get("fragment_unit_axes")) is not list
    ):
        raise _error("currency-risk candidate unit receipt drifted")
    inventory_by_key = {
        (item["page_json_version_id"], item["section_id"], item["table_id"]): item
        for item in cluster["declared_table_inventory"]
        if item.get("disposition") == "SELECTED_CURRENCY_RISK_FRAGMENT"
    }
    cells: dict[tuple[str, str, str], dict[str, Any]] = {}
    rebuilt_equations = []
    rebuilt_nonclosing_frontiers = []
    coverage_incomplete = False
    period_by_key = {
        (item["page_json_version_id"], item["section_id"], item["table_id"]): item
        for item in closure["period_assignments"]
        if type(item) is dict and set(item) >= {"page_json_version_id", "section_id", "table_id"}
    }
    if len(period_by_key) != len(closure["period_assignments"]):
        raise _error("currency-risk period assignment identity axis drifted")
    if len(closure["table_receipts"]) != len(regions):
        raise _error("currency-risk table receipt axis is incomplete")
    for receipt in closure["table_receipts"]:
        exact_required_currency_roles = set()
        if (
            type(receipt) is not dict
            or set(receipt) != {"classification", "period_assignment", "region", "resolved_columns"}
            or type(receipt.get("resolved_columns")) is not list
        ):
            raise _error("currency-risk table receipt is invalid")
        region = receipt["region"]
        key = (region.get("page_json_version_id"), region.get("section_id"), region.get("table_id"))
        inventory = inventory_by_key.get(key)
        expected_period = period_by_key.get(key)
        if (
            inventory is None
            or expected_period is None
            or not same_typed_json_v1(receipt["classification"], inventory["classification"])
            or not same_typed_json_v1(receipt["period_assignment"], expected_period)
        ):
            raise _error("currency-risk indexed table projection drifted")
        expected_liquidity_values_by_row_id = {}
        row_id_by_role = {}
        if compiled_specs.get("liquidity_risk_mode") is True:
            from bctc_ai.evaluation.gemini_json_liquidity_risk_matrix_v1 import (
                validate_liquidity_row_alignment_receipt_v1,
            )

            alignment = validate_liquidity_row_alignment_receipt_v1(
                receipt["classification"].get("liquidity_row_alignment_receipt")
            )
            expected_liquidity_values_by_row_id = {
                item["row_id"]: item["effective_values_exact"]
                for item in alignment["effective_rows"]
            }
            row_id_by_role = {
                item["role"]: item["row_id"]
                for item in receipt["classification"]["component_axis"]
                if item["kind"] == "CORE_ROW"
            }
        for resolved in receipt["resolved_columns"]:
            if (
                type(resolved) is not dict
                or set(resolved)
                != {
                    "column_axis",
                    "core_cells_by_role",
                    "equations",
                    "nonclosing_frontiers",
                }
                or type(resolved.get("core_cells_by_role")) is not dict
                or type(resolved.get("equations")) is not list
                or type(resolved.get("nonclosing_frontiers")) is not list
            ):
                raise _error("currency-risk resolved column is invalid")
            column_axis = resolved["column_axis"]
            currency_role = column_axis.get("role")
            replay_cells = canonical_clone_v1(resolved["core_cells_by_role"])
            for cell in replay_cells.values():
                if (
                    type(cell) is dict
                    and cell.get("state") == "BLANK_ZERO_AFTER_ONE_UNKNOWN_EQUATION_EXACT"
                    and cell.get("coefficient") == 0
                ):
                    cell["coefficient"] = None
                    cell["state"] = "BLANK"
            if compiled_specs.get("liquidity_risk_mode") is True:
                column_index = column_axis.get("source_order", 0) - 1
                for row_role, replay_cell in replay_cells.items():
                    row_id = row_id_by_role.get(row_role)
                    values = expected_liquidity_values_by_row_id.get(row_id)
                    if (
                        type(values) is not list
                        or not 0 <= column_index < len(values)
                        or not same_typed_json_v1(
                            replay_cell,
                            _cell(
                                value=values[column_index],
                                region=region,
                                row_id=row_id,
                                column_id=column_axis["column_id"],
                                compiled_specs=compiled_specs,
                            ),
                        )
                    ):
                        raise _error("liquidity resolved cell is not bound to aligned source")
            replay_equations = []
            replay_nonclosing_frontiers = []
            for declaration in compiled_specs["state_equations"]:
                equation, _equation_reasons = _equation(
                    declaration=declaration,
                    cells_by_role=replay_cells,
                    currency_role=currency_role,
                )
                replay_equations.append(equation)
                frontier = _nonclosing_currency_frontier_v1(
                    cells_by_role=replay_cells,
                    column_axis=column_axis,
                    declaration=declaration,
                    equation=equation,
                    period_assignment=receipt["period_assignment"],
                    region=region,
                    required_row_roles=compiled_specs["required_currency_row_roles"],
                )
                if frontier is not None:
                    replay_nonclosing_frontiers.append(frontier)
            if not same_typed_json_v1(resolved["core_cells_by_role"], replay_cells):
                raise _error("currency-risk resolved cell projection drifted")
            if not same_typed_json_v1(resolved["equations"], replay_equations):
                raise _error("currency-risk equation projection drifted")
            if not same_typed_json_v1(
                resolved["nonclosing_frontiers"], replay_nonclosing_frontiers
            ):
                raise _error("currency-risk non-closing projection drifted")
            rebuilt_equations.extend(canonical_clone_v1(replay_equations))
            rebuilt_nonclosing_frontiers.extend(canonical_clone_v1(replay_nonclosing_frontiers))
            if column_axis.get("kind") == "MAPPED_CURRENCY" and all(
                equation["status"] == "EXACT"
                for declaration, equation in zip(
                    compiled_specs["state_equations"], replay_equations, strict=True
                )
                if declaration["required"]
            ):
                exact_required_currency_roles.add(currency_role)
            required_equations_exact = all(
                equation["status"] == "EXACT"
                for declaration, equation in zip(
                    compiled_specs["state_equations"], replay_equations, strict=True
                )
                if declaration["required"]
            )
            if column_axis.get("kind") == "MAPPED_CURRENCY" and (
                compiled_specs.get("liquidity_risk_mode") is not True or required_equations_exact
            ):
                for row_role, cell in replay_cells.items():
                    if type(cell.get("coefficient")) is int:
                        cells[
                            (receipt["period_assignment"]["period_role"], currency_role, row_role)
                        ] = cell
        if (
            compiled_specs.get("liquidity_risk_mode") is True
            and (
                len(exact_required_currency_roles)
                < compiled_specs["query_policy"]["minimum_mapped_currency_roles"]
                or compiled_specs["grand_total_currency_role"] not in exact_required_currency_roles
            )
        ) or (
            compiled_specs.get("liquidity_risk_mode") is not True
            and len(exact_required_currency_roles)
            < compiled_specs["query_policy"]["minimum_mapped_currency_roles"]
        ):
            coverage_incomplete = True
    if not same_typed_json_v1(closure["equations"], rebuilt_equations):
        raise _error("currency-risk closure equation axis drifted")
    if not same_typed_json_v1(
        closure["nonclosing_currency_frontiers"], rebuilt_nonclosing_frontiers
    ):
        raise _error("currency-risk closure non-closing axis drifted")
    if coverage_incomplete != (
        "CURRENCY_RISK_REQUIRED_EQUATION_COVERAGE_INCOMPLETE" in candidate["reasons"]
    ):
        raise _error("currency-risk required equation coverage disposition drifted")
    material = {key: value for key, value in candidate.items() if key != "candidate_id"}
    if candidate["candidate_id"] != "gjeqmfv1:candidate:" + canonical_json_sha256_v1(material):
        raise _error("currency-risk candidate identity drifted")
    if candidate["status"] == engine.READY:
        if candidate["reasons"] or unit["canonical_unit"] is None:
            raise _error("currency-risk READY candidate is incomplete")
        expected_mappings = build_currency_risk_mappings_v1(
            compiled_specs=compiled_specs,
            canonical_unit=unit["canonical_unit"],
            period_assignments=closure["period_assignments"],
            cells_by_period_currency_row=cells,
        )
        if not same_typed_json_v1(candidate["mappings"], expected_mappings):
            raise _error("currency-risk schema mapping axis drifted")
    elif candidate["mappings"] or not candidate["reasons"]:
        raise _error("currency-risk unresolved semantics drifted")
    return canonical_clone_v1(candidate)
