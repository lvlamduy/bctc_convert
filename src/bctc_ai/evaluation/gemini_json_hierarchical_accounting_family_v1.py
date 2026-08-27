"""Recursive accounting closure over manifest-selected Gemini page JSON.

This module deliberately has no PDF/OCR/geometry dependency.  Gemini's exact
row labels, hierarchy paths, columns and raw cell strings are the source axis;
the declarative topology/equation/schema specs are the only semantic axis.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1

FORMAT_VERSION = "GEMINI_JSON_HIERARCHICAL_ACCOUNTING_FAMILY_SWEEP_V3"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_TWO_THEN_THREE_ANCHOR_"
    "EXACT_HIERARCHY_PATH_PERIOD_UNIT_ALL_LANE_RECURSIVE_DIRECT_FRONTIER_"
    "ACCOUNTING_CLOSURE_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_GEOMETRY_PPOCR_"
    "VIETOCR_BANK_FILE_PAGE_NOTE_ROUTING_BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)
_EVALUATION_FORMAT = "ACCOUNTING_FAMILY_EVALUATION_SPEC_V4"
_SCHEMA_FORMAT = "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V5"
_ROOT_ROLE_KINDS = {"ADDITIVE_CHILD", "STRUCTURAL_GROUP"}
_DASHES = {"-", "–", "—", "_"}


def _error(message: str) -> ValueError:
    from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
        GeminiJsonFlatAccountingFamilyV1Error,
    )

    return GeminiJsonFlatAccountingFamilyV1Error(message)


def _normalized(value: Any) -> str:
    return normalize_vietnamese_anchor_v1(value) if type(value) is str else ""


def _without_leading_ordinal(folded: str) -> str:
    prefix, separator, remainder = folded.partition(" ")
    if separator and (
        prefix.isdigit()
        or prefix
        in {
            "i",
            "ii",
            "iii",
            "iv",
            "v",
            "vi",
            "vii",
            "viii",
            "ix",
            "x",
            "xi",
            "xii",
            "xiii",
            "xiv",
            "xv",
        }
    ):
        return remainder
    return folded


def _matches(value: Any, alias: str) -> bool:
    folded = _normalized(value)
    forms = {folded, _without_leading_ordinal(folded)}
    if alias in forms:
        return True
    suffixes = {form.removeprefix(alias).strip() for form in forms if form.startswith(alias + " ")}
    return bool(suffixes) and suffixes <= {
        "1",
        "2",
        "3",
        "4",
        "5",
        "i",
        "ii",
        "iii",
        "iv",
        "v",
    }


def _path_value_matches_alias(folded: str, alias: str, label: str) -> bool:
    stripped = _without_leading_ordinal(folded)
    middle = (
        stripped[len(alias) : len(stripped) - len(label)].strip()
        if label and stripped.startswith(alias + " ") and stripped.endswith(" " + label)
        else None
    )
    return _matches(stripped, alias) or (middle is not None and middle not in {"va", "and"})


def _path_has_role(
    path: Any,
    *,
    aliases: list[str],
    label_exact: Any,
) -> bool:
    if type(path) is not list:
        return False
    label = _normalized(label_exact)
    for value in path:
        folded = _normalized(value)
        if not folded or folded == label:
            continue
        if any(_path_value_matches_alias(folded, alias, label) for alias in aliases):
            return True
    return False


def _path_role_position(path: Any, *, aliases: list[str], label_exact: Any) -> int:
    if type(path) is not list:
        return -1
    label = _normalized(label_exact)
    positions = []
    for position, value in enumerate(path):
        folded = _normalized(value)
        if (
            folded
            and folded != label
            and any(_path_value_matches_alias(folded, alias, label) for alias in aliases)
        ):
            positions.append(position)
    return max(positions, default=-1)


def _money(value: Any) -> dict[str, Any]:
    if value is None:
        return {
            "coefficient": 0,
            "source_text": None,
            "state": "BLANK_ZERO_IF_EQUATION_EXACT",
        }
    if type(value) is not str or not value.strip():
        raise _error("Gemini JSON hierarchy money cell is invalid")
    body = value.strip()
    if body in _DASHES:
        return {"coefficient": 0, "source_text": value, "state": "DASH_ZERO"}
    negative = body.startswith("(") and body.endswith(")")
    body = body[1:-1].strip() if negative else body
    if body.startswith("-"):
        if negative:
            raise _error("Gemini JSON hierarchy money sign is contradictory")
        negative = True
        body = body[1:].strip()
    digits = body.replace(".", "").replace(",", "").replace(" ", "")
    if not digits.isdigit():
        raise _error("Gemini JSON hierarchy money cell is not an exact integer")
    coefficient = int(digits)
    return {
        "coefficient": -coefficient if negative else coefficient,
        "source_text": value,
        "state": "RAW_SIGNED_INTEGER",
    }


def _compile_specs(topology_spec: Any, evaluation_spec: Any, schema_spec: Any) -> dict[str, Any]:
    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("Gemini JSON hierarchy topology spec is invalid") from exc
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec)
        != {
            "candidate_selection_policy",
            "closure_policy",
            "expected_lane_unit_kinds",
            "family_id",
            "format_version",
            "hierarchical_closure_spec",
            "occurrence_row_axis_policy",
            "period_semantics",
        }
        or evaluation_spec.get("format_version") != _EVALUATION_FORMAT
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("expected_lane_unit_kinds") != ["MONEY", "MONEY"]
    ):
        raise _error("Gemini JSON hierarchy evaluation spec is invalid or unsupported")
    hierarchy = evaluation_spec["hierarchical_closure_spec"]
    if (
        type(hierarchy) is not dict
        or hierarchy.get("family_id") != topology["family_id"]
        or type(hierarchy.get("equations")) is not list
        or not hierarchy["equations"]
    ):
        raise _error("Gemini JSON hierarchy equation spec is invalid")
    children_by_role = {child["role"]: child for child in topology["children"]}
    known_roles = set(children_by_role) | {topology["parent"]["role"]}
    equations: list[dict[str, Any]] = []
    result_roles: set[str] = set()
    for equation in hierarchy["equations"]:
        result = equation.get("result_role") if type(equation) is dict else None
        alternatives = (
            equation.get("component_role_alternatives") if type(equation) is dict else None
        )
        if (
            result not in known_roles
            or result in result_roles
            or type(alternatives) is not list
            or not alternatives
        ):
            raise _error("Gemini JSON hierarchy equation result is invalid")
        checked_alternatives = []
        for alternative in alternatives:
            roles = alternative.get("component_roles") if type(alternative) is dict else None
            if (
                type(roles) is not list
                or not roles
                or len(roles) != len(set(roles))
                or result in roles
                or any(role not in known_roles for role in roles)
                or alternative.get("coverage_policy") != "EXHAUSTIVE_COMPONENT_SET"
                or alternative.get("derivation_policy")
                not in {
                    "ALLOW_DERIVATION_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS",
                    "VISIBLE_RESULT_CORROBORATION_ONLY",
                }
            ):
                raise _error("Gemini JSON hierarchy equation alternative is invalid")
            checked_alternatives.append(canonical_clone_v1(alternative))
        visible_roles = equation.get("visible_result_roles")
        if (
            type(visible_roles) is not list
            or not visible_roles
            or any(role not in known_roles for role in visible_roles)
        ):
            raise _error("Gemini JSON hierarchy visible result roles are invalid")
        equations.append(
            {**canonical_clone_v1(equation), "component_role_alternatives": checked_alternatives}
        )
        result_roles.add(result)
    available_results: set[str] = set()
    pending = list(equations)
    ordered: list[dict[str, Any]] = []
    while pending:
        progressed = False
        for equation in list(pending):
            dependencies = {
                role
                for alternative in equation["component_role_alternatives"]
                for role in alternative["component_roles"]
                if role in result_roles
            }
            if dependencies <= available_results:
                ordered.append(equation)
                available_results.add(equation["result_role"])
                pending.remove(equation)
                progressed = True
        if not progressed:
            raise _error("Gemini JSON hierarchy equation graph is cyclic")
    if topology["parent"]["role"] not in result_roles:
        raise _error("Gemini JSON hierarchy has no family-root equation")

    if (
        type(schema_spec) is not dict
        or set(schema_spec)
        != {
            "family_id",
            "family_report_norm_id",
            "family_root_mapping_policy",
            "format_version",
            "ignored_roles",
            "role_bindings",
        }
        or schema_spec.get("format_version") != _SCHEMA_FORMAT
        or schema_spec.get("family_id") != topology["family_id"]
        or type(schema_spec.get("family_report_norm_id")) is not int
        or type(schema_spec.get("ignored_roles")) is not list
        or type(schema_spec.get("role_bindings")) is not list
    ):
        raise _error("Gemini JSON hierarchy schema binding spec is invalid")
    bindings: dict[str, int] = {}
    for binding in schema_spec["role_bindings"]:
        if (
            type(binding) is not dict
            or type(binding.get("role")) is not str
            or binding["role"] not in children_by_role
            or binding["role"] in bindings
            or type(binding.get("report_norm_id")) is not int
            or binding["report_norm_id"] <= 0
        ):
            raise _error("Gemini JSON hierarchy role binding is invalid")
        bindings[binding["role"]] = binding["report_norm_id"]
    ignored = set(schema_spec["ignored_roles"])
    if set(bindings) | ignored != set(children_by_role) or set(bindings) & ignored:
        raise _error("Gemini JSON hierarchy schema frontier is incomplete")

    aliases_by_role = {
        child["role"]: sorted(
            {alias for matcher in child["matchers"] for alias in matcher["aliases"]}
        )
        for child in topology["children"]
    }
    anchor_groups = []
    for combination in topology["required_role_combinations"]:
        if len(combination) not in {2, 3}:
            raise _error("Gemini JSON hierarchy anchor combination is invalid")
        anchor_groups.append([aliases_by_role[role] for role in combination])
    return {
        "aliases_by_role": aliases_by_role,
        "anchor_alias_groups": anchor_groups,
        "bindings": bindings,
        "claim_boundary": CLAIM_BOUNDARY,
        "engine_format_version": FORMAT_VERSION,
        "equations": ordered,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "ignored_roles": sorted(ignored),
        "schema": canonical_clone_v1(schema_spec),
        "topology": topology,
    }


def compile_gemini_json_hierarchical_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile one V4/V5 accounting family for JSON-only evaluation."""

    return _compile_specs(topology_spec, evaluation_spec, schema_binding_spec)


def _row_roles(
    row: dict[str, Any],
    *,
    topology: dict[str, Any],
    aliases_by_role: dict[str, list[str]],
) -> list[str]:
    scoped: list[str] = []
    unscoped: list[str] = []
    for child in topology["children"]:
        role = child["role"]
        for matcher in child["matchers"]:
            if not any(_matches(row.get("label_exact"), alias) for alias in matcher["aliases"]):
                continue
            within = matcher["within_role"]
            if within is None:
                unscoped.append(role)
            elif _path_has_role(
                row.get("hierarchy_path_exact"),
                aliases=aliases_by_role[within],
                label_exact=row.get("label_exact"),
            ):
                scoped.append(role)
    matches = sorted(set(scoped or unscoped))
    if len(matches) <= 1:
        return matches
    kinds = {
        role: next(c["role_kind"] for c in topology["children"] if c["role"] == role)
        for role in matches
    }
    # One printed compound row may be both a structural subtotal and its sole
    # typed child.  It is safe only because the equation must corroborate the
    # same values and the root frontier consumes the structural role, not both.
    if set(kinds.values()) == {"STRUCTURAL_GROUP", "ADDITIVE_CHILD"}:
        return matches
    raise _error("Gemini JSON hierarchy row matches multiple incompatible roles")


def _nearest_owner(
    row: dict[str, Any],
    *,
    structural_roles: set[str],
    aliases_by_role: dict[str, list[str]],
    own_roles: set[str],
) -> str | None:
    matches: list[tuple[int, int, str]] = []
    for role in structural_roles - own_roles:
        position = _path_role_position(
            row.get("hierarchy_path_exact"),
            aliases=aliases_by_role[role],
            label_exact=row.get("label_exact"),
        )
        if position >= 0:
            matches.append((position, max(map(len, aliases_by_role[role])), role))
    if not matches:
        return None
    nearest = max(position for position, _length, _role in matches)
    longest = max(length for position, length, _role in matches if position == nearest)
    roles = {
        role for position, length, role in matches if position == nearest and length == longest
    }
    if len(roles) != 1:
        raise _error("Gemini JSON hierarchy row owner is ambiguous")
    return next(iter(roles))


def _coefficients(record: dict[str, Any]) -> list[int]:
    return [cell["coefficient"] for cell in record["cells"]]


def _sum(records: list[dict[str, Any]], lane_count: int) -> list[int]:
    return [sum(_coefficients(record)[lane] for record in records) for lane in range(lane_count)]


def _solve(
    *,
    base_by_role: dict[str, dict[str, Any]],
    anonymous: list[dict[str, Any]],
    compiled: dict[str, Any],
    ambiguous_provision_target: str | None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[str], set[str]]:
    topology = compiled["topology"]
    parent_role = topology["parent"]["role"]
    resolved = dict(base_by_role)
    used_anonymous: set[str] = set()
    equations_receipt: list[dict[str, Any]] = []
    reasons: list[str] = []
    component_parents: dict[str, set[str]] = defaultdict(set)
    for equation in compiled["equations"]:
        for alternative in equation["component_role_alternatives"]:
            for role in alternative["component_roles"]:
                component_parents[role].add(equation["result_role"])
    if "INTERBANK_PROVISION_AMBIGUOUS" in resolved:
        ambiguous = resolved.pop("INTERBANK_PROVISION_AMBIGUOUS")
        if ambiguous_provision_target is None or ambiguous_provision_target in resolved:
            reasons.append("AMBIGUOUS_PROVISION_HAS_NO_UNIQUE_EQUATION_ROLE")
        else:
            target_parents = component_parents[ambiguous_provision_target]
            source_owner = ambiguous.get("owner_role")
            inferred_owner = (
                source_owner
                if source_owner in target_parents
                else next(iter(target_parents))
                if len(target_parents) == 1
                else None
            )
            resolved[ambiguous_provision_target] = {
                **ambiguous,
                "inferred_from_role": "INTERBANK_PROVISION_AMBIGUOUS",
                "owner_role": inferred_owner,
                "role": ambiguous_provision_target,
            }

    for equation in compiled["equations"]:
        result_role = equation["result_role"]
        component_universe = {
            role
            for alternative in equation["component_role_alternatives"]
            for role in alternative["component_roles"]
        }
        direct_visible = set()
        for role in component_universe & set(resolved):
            record = resolved[role]
            owner = record.get("owner_role")
            allowed_parents = component_parents[role]
            if owner is not None and owner in allowed_parents and owner != result_role:
                continue
            if owner is not None and result_role in allowed_parents and owner != result_role:
                continue
            direct_visible.add(role)
        existing = resolved.get(result_role)
        if not direct_visible:
            if existing is not None:
                equations_receipt.append(
                    {
                        "component_roles": [],
                        "mode": "VISIBLE_SOURCE_ONLY_NO_DECLARED_COMPONENT_VISIBLE",
                        "result_coefficients": _coefficients(existing),
                        "result_role": result_role,
                        "result_row_id": existing["row_id"],
                    }
                )
            continue
        eligible = [
            alternative
            for alternative in equation["component_role_alternatives"]
            if set(alternative["component_roles"]) == direct_visible
        ]
        if not eligible:
            reasons.append(f"NO_EXHAUSTIVE_DIRECT_FRONTIER:{result_role}")
            continue
        alternatives = []
        for alternative in eligible:
            components = [resolved[role] for role in alternative["component_roles"]]
            sums = _sum(components, 2)
            carriers: list[dict[str, Any]] = []
            authoritative_visible = False
            if existing is not None and _coefficients(existing) == sums:
                carriers.append(existing)
            if existing is not None:
                authoritative_visible = True
            visible_roles = set(equation["visible_result_roles"])
            for role in visible_roles - {result_role}:
                record = resolved.get(role)
                if record is not None and _coefficients(record) == sums:
                    carriers.append(record)
                if record is not None:
                    authoritative_visible = True
            maximum_component_ordinal = max(component["ordinal"] for component in components)
            for record in anonymous:
                if record.get("owner_role") == result_role and "allowed_result_roles" not in record:
                    authoritative_visible = True
                if (
                    record["row_id"] not in used_anonymous
                    and record["ordinal"] > maximum_component_ordinal
                    and _coefficients(record) == sums
                    and result_role in record.get("allowed_result_roles", {result_role})
                    and (
                        record.get("owner_role") in {None, result_role}
                        or result_role == parent_role
                    )
                ):
                    carriers.append(record)
            unique_carriers = {carrier["row_id"]: carrier for carrier in carriers}
            if len(unique_carriers) == 1:
                alternatives.append(
                    (alternative, components, sums, next(iter(unique_carriers.values())))
                )
            elif (
                not unique_carriers
                and not authoritative_visible
                and alternative["derivation_policy"]
                == "ALLOW_DERIVATION_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"
            ):
                alternatives.append((alternative, components, sums, None))
        if len(alternatives) != 1:
            reasons.append(
                f"EXACT_DIRECT_FRONTIER_SOLUTION_COUNT_NOT_ONE:{result_role}:{len(alternatives)}"
            )
            continue
        alternative, components, sums, carrier = alternatives[0]
        if carrier is None:
            result = {
                "cells": [
                    {
                        "coefficient": coefficient,
                        "source_text": None,
                        "state": "DERIVED_EXACT_RECURSIVE_DIRECT_FRONTIER",
                    }
                    for coefficient in sums
                ],
                "derived_from_roles": list(alternative["component_roles"]),
                "derived_from_row_ids": [component["row_id"] for component in components],
                "label_exact": result_role,
                "ordinal": max(component["ordinal"] for component in components),
                "owner_role": None,
                "path": [],
                "role": result_role,
                "row_id": "derived:" + result_role,
            }
            mode = "DERIVED_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"
        else:
            result = {**carrier, "owner_role": None, "role": result_role}
            if carrier["row_id"].startswith("r") and carrier not in base_by_role.values():
                used_anonymous.add(carrier["row_id"])
            mode = "VISIBLE_RESULT_EXACTLY_CORROBORATED"
        resolved[result_role] = result
        equations_receipt.append(
            {
                "component_roles": list(alternative["component_roles"]),
                "component_row_ids": [component["row_id"] for component in components],
                "lane_component_sums": sums,
                "mode": mode,
                "result_coefficients": _coefficients(result),
                "result_role": result_role,
                "result_row_id": result["row_id"],
            }
        )
    if ambiguous_provision_target is not None:
        use_count = sum(
            ambiguous_provision_target in receipt.get("component_roles", [])
            for receipt in equations_receipt
        )
        if use_count != 1:
            reasons.append(f"INFERRED_AMBIGUOUS_PROVISION_USE_COUNT_NOT_ONE:{use_count}")
    if parent_role not in resolved:
        reasons.append("FAMILY_ROOT_IS_NOT_HIERARCHICALLY_RESOLVED")
    return resolved, equations_receipt, reasons, used_anonymous


def evaluate_gemini_json_hierarchical_family_table_v1(
    *,
    page_json: Any,
    page_json_version_id: str,
    physical_page: int,
    section_id: str,
    table_id: str,
    compiled_specs: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate one local Gemini table with an exact recursive equation DAG."""

    from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import _candidate_result

    topology = compiled_specs["topology"]
    reasons: list[str] = []
    if type(page_json) is not dict or type(page_json.get("sections")) is not list:
        raise _error("Gemini JSON hierarchy page is invalid")
    try:
        section = page_json["sections"][int(section_id[1:]) - 1]
        table = section["tables"][int(table_id[1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("Gemini JSON hierarchy table identity is invalid") from exc
    title = " ".join(
        value
        for value in (section.get("title_exact"), table.get("title_exact"))
        if type(value) is str and value
    )
    title_folded = _normalized(title)
    parent_in_title = any(alias in title_folded for alias in topology["parent"]["aliases"])
    columns = table.get("columns")
    money_indices = (
        [index for index, column in enumerate(columns) if column.get("value_kind") == "MONEY"]
        if type(columns) is list
        else []
    )
    money_columns = [columns[index] for index in money_indices] if type(columns) is list else []
    unit_is_declared = (
        type(table.get("unit_exact")) is str and bool(table["unit_exact"].strip())
    ) or (
        len(money_columns) == 2
        and all(
            "trieu" in _normalized(" ".join(map(str, column.get("header_path_exact", []))))
            for column in money_columns
        )
    )
    if (
        type(columns) is not list
        or len(money_columns) != 2
        or any(
            type(column.get("header_path_exact")) is not list or not column["header_path_exact"]
            for column in money_columns
        )
        or not unit_is_declared
    ):
        reasons.append("PERIOD_UNIT_OR_MONEY_COLUMN_AXIS_IS_NOT_EXACT")
    source_rows = table.get("rows")
    if type(source_rows) is not list or not source_rows:
        raise _error("Gemini JSON hierarchy row axis is empty")
    parent_row_ordinals = [
        ordinal
        for ordinal, row in enumerate(source_rows, start=1)
        if any(_matches(row.get("label_exact"), alias) for alias in topology["parent"]["aliases"])
    ]
    if not parent_in_title and len(parent_row_ordinals) != 1:
        reasons.append("FAMILY_PARENT_NOT_VISIBLE_IN_SECTION_TABLE_OR_UNIQUE_ROW")
    if not parent_in_title and len(parent_row_ordinals) == 1:
        parent_ordinal = parent_row_ordinals[0]
        rows = [
            (ordinal, row)
            for ordinal, row in enumerate(source_rows, start=1)
            if ordinal == parent_ordinal
            or _path_has_role(
                row.get("hierarchy_path_exact"),
                aliases=topology["parent"]["aliases"],
                label_exact=row.get("label_exact"),
            )
        ]
    else:
        rows = list(enumerate(source_rows, start=1))
    structural_roles = {
        child["role"] for child in topology["children"] if child["role_kind"] == "STRUCTURAL_GROUP"
    }
    records_by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    anonymous: list[dict[str, Any]] = []
    unmatched_numeric: list[int] = []
    for ordinal, row in rows:
        source_values = row.get("values_exact")
        if type(source_values) is not list or len(source_values) != len(columns or []):
            reasons.append(f"ROW_VALUE_VECTOR_DOES_NOT_MATCH_COLUMN_AXIS:{ordinal}")
            continue
        values = [source_values[index] for index in money_indices]
        try:
            cells = [_money(value) for value in values]
        except ValueError:
            reasons.append(f"ROW_MONEY_CELL_IS_NOT_EXACT_INTEGER:{ordinal}")
            continue
        roles = _row_roles(
            row, topology=topology, aliases_by_role=compiled_specs["aliases_by_role"]
        )
        owner = _nearest_owner(
            row,
            structural_roles=structural_roles,
            aliases_by_role=compiled_specs["aliases_by_role"],
            own_roles=set(roles),
        )
        if owner is None and _path_has_role(
            row.get("hierarchy_path_exact"),
            aliases=topology["parent"]["aliases"],
            label_exact=row.get("label_exact"),
        ):
            owner = topology["parent"]["role"]
        record = {
            "cells": cells,
            "label_exact": row.get("label_exact"),
            "ordinal": ordinal,
            "owner_role": owner,
            "path": canonical_clone_v1(row.get("hierarchy_path_exact")),
            "row_id": f"r{ordinal}",
        }
        if roles and any(value is not None for value in values):
            structural_matches = [
                role
                for role in roles
                if next(
                    child["role_kind"] for child in topology["children"] if child["role"] == role
                )
                == "STRUCTURAL_GROUP"
            ]
            additive_matches = [role for role in roles if role not in structural_matches]
            if len(structural_matches) == 1 and additive_matches:
                record["owner_role"] = structural_matches[0]
            for role in additive_matches or structural_matches:
                records_by_role[role].append({**record, "role": role})
            if structural_matches and additive_matches:
                anonymous.append(
                    {
                        **record,
                        "allowed_result_roles": set(structural_matches),
                    }
                )
        elif roles:
            # A null structural header authenticates hierarchy but is not a
            # zero-valued accounting result.  Its children/subtotal decide it.
            continue
        elif row.get("row_kind") in {"SUBTOTAL", "TOTAL"}:
            anonymous.append(record)
        elif all(value is None for value in values):
            continue
        else:
            unmatched_numeric.append(ordinal)
    for role, records in records_by_role.items():
        if len(records) > 1:
            reasons.append(f"ROLE_OCCURRENCE_COUNT_ABOVE_ONE:{role}:{len(records)}")
    base = {role: records[0] for role, records in records_by_role.items() if len(records) == 1}
    ambiguous = "INTERBANK_PROVISION_AMBIGUOUS" in base
    targets = [None]
    if ambiguous:
        targets = [
            role
            for role in (
                "INTERBANK_DEPOSIT_PROVISION",
                "INTERBANK_LOAN_PROVISION",
                "TOTAL_INTERBANK_PROVISION",
            )
            if role in compiled_specs["aliases_by_role"] and role not in base
        ]
        source_owner = base["INTERBANK_PROVISION_AMBIGUOUS"].get("owner_role")
        if source_owner is not None:
            result_parent: dict[str, set[str]] = defaultdict(set)
            target_parents: dict[str, set[str]] = defaultdict(set)
            for equation in compiled_specs["equations"]:
                result_role = equation["result_role"]
                for alternative in equation["component_role_alternatives"]:
                    for component_role in alternative["component_roles"]:
                        result_parent[component_role].add(result_role)
                        if component_role in targets:
                            target_parents[component_role].add(result_role)

            def distance_to_parent(parent: str) -> int | None:
                frontier = {source_owner}
                seen = set()
                for distance in range(len(compiled_specs["equations"]) + 2):
                    if parent in frontier:
                        return distance
                    seen.update(frontier)
                    frontier = {
                        ancestor
                        for role in frontier
                        for ancestor in result_parent.get(role, set())
                        if ancestor not in seen
                    }
                return None

            distances = {
                role: min(
                    (
                        distance
                        for parent in target_parents[role]
                        if (distance := distance_to_parent(parent)) is not None
                    ),
                    default=None,
                )
                for role in targets
            }
            finite = [distance for distance in distances.values() if distance is not None]
            if finite:
                nearest = min(finite)
                targets = [role for role in targets if distances[role] == nearest]
                exact_scope_targets = [
                    role for role in targets if target_parents[role] == {source_owner}
                ]
                if len(exact_scope_targets) == 1:
                    targets = exact_scope_targets
    solutions = []
    for target in targets:
        resolved, receipts, local_reasons, used = _solve(
            base_by_role=base,
            anonymous=anonymous,
            compiled=compiled_specs,
            ambiguous_provision_target=target,
        )
        if not local_reasons:
            solutions.append((resolved, receipts, used, target))
    if len(solutions) != 1:
        reasons.append(f"HIERARCHICAL_SOLUTION_COUNT_NOT_ONE:{len(solutions)}")
    if unmatched_numeric:
        reasons.append("UNBOUND_VISIBLE_NUMERIC_ROWS:" + ",".join(map(str, unmatched_numeric)))
    result = _candidate_result(
        topology=topology,
        page_json_version_id=page_json_version_id,
        physical_page=physical_page,
        section_id=section_id,
        table_id=table_id,
        reasons=reasons,
    )
    if reasons:
        return result
    resolved, receipts, used_anonymous, inferred_target = solutions[0]
    root_role = topology["parent"]["role"]
    mapping_roles = [root_role] + [
        child["role"]
        for child in topology["children"]
        if child["role"] in compiled_specs["bindings"]
    ]
    mappings = []
    for role in mapping_roles:
        record = resolved.get(role)
        if record is None:
            continue
        mapping = {
            "columns": canonical_clone_v1(money_columns),
            "hierarchy_path_exact": canonical_clone_v1(record["path"]),
            "label_exact": record["label_exact"],
            "report_norm_id": (
                compiled_specs["schema"]["family_report_norm_id"]
                if role == root_role
                else compiled_specs["bindings"][role]
            ),
            "role": role,
            "row_id": record["row_id"],
            "values": canonical_clone_v1(record["cells"]),
        }
        if "derived_from_roles" in record:
            mapping["derived_from_roles"] = canonical_clone_v1(record["derived_from_roles"])
            mapping["derived_from_row_ids"] = canonical_clone_v1(record["derived_from_row_ids"])
        if "inferred_from_role" in record:
            mapping["inferred_from_role"] = record["inferred_from_role"]
        mappings.append(mapping)
    result["mappings"] = mappings
    result["closure_receipt"] = {
        "equations": receipts,
        "inferred_ambiguous_provision_role": inferred_target,
        "rule": "EXACT_EXHAUSTIVE_GEMINI_JSON_RECURSIVE_DIRECT_FRONTIER_ALL_LANES",
        "used_anonymous_result_row_ids": sorted(used_anonymous),
    }
    return result
