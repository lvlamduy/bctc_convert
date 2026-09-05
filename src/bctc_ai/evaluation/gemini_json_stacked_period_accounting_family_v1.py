"""Schema-blind stacked-period accounting closure over Gemini page JSON.

This primitive consumes only Gemini's ordered section/table/column/row JSON
and three declarative family specifications.  It does not import or call the
legacy OCR, geometry, detector, crop, or document-layout paths.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from typing import Any, NamedTuple

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_STACKED_PERIOD_ACCOUNTING_FAMILY_V1"
EVALUATION_FORMAT_VERSION = "ACCOUNTING_STACKED_PERIOD_FAMILY_EVALUATION_SPEC_V1"
LAYOUT_FORMAT_VERSION = "ACCOUNTING_STACKED_PERIOD_LANE_LAYOUT_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_STACKED_PERIOD_SCHEMA_BINDING_SPEC_V1"
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_PARENT_CHILD_ANCHORS_"
    "ORDERED_PERIOD_LANE_HEADER_PATH_EXACT_VISIBLE_RECURSIVE_DIRECT_FRONTIER_"
    "SCHEMA_MAPPING_PROPOSAL_ONLY_NO_GEOMETRY_PPOCR_VIETOCR_BANK_FILE_PAGE_"
    "NOTE_ROUTING_BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)

_DATE_DMY = re.compile(r"(?<!\d)([0-3]?\d)(?:[./-]|\s+)([01]?\d)(?:[./-]|\s+)(20\d{2})(?!\d)")
_DATE_WORDS = re.compile(r"ngay\s+([0-3]?\d)\s+thang\s+([01]?\d)\s+nam\s+(20\d{2})")
_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_DIGITS = re.compile(r"^\d+$")
_GROUPED = re.compile(r"^\d{1,3}(?:[., ]\d{3})+$")
_PERIOD_ROLES = ("CURRENT_PERIOD", "COMPARATIVE_PERIOD")
_ROLE_KINDS = {"ADDITIVE_CHILD", "STRUCTURAL_GROUP"}
_RELATIVE_PERIOD_RESTATEMENT_SUFFIXES = {
    "",
    "nay",
    "da duoc trinh bay lai",
    "da trinh bay lai",
    "duoc trinh bay lai",
    "trinh bay lai",
}


class _PeriodToken(NamedTuple):
    """One exact visible period carrier without inventing a cutoff date."""

    period_end: date | None
    role_hint: str | None
    period_year: int | None
    label: str


class GeminiJsonStackedPeriodAccountingFamilyV1Error(ValueError):
    """The Gemini table, declarative spec, or accounting frontier drifted."""


def _error(message: str) -> GeminiJsonStackedPeriodAccountingFamilyV1Error:
    return GeminiJsonStackedPeriodAccountingFamilyV1Error(message)


def _normalized(value: Any) -> str:
    return normalize_vietnamese_anchor_v1(value) if type(value) is str else ""


def _matches(value: Any, aliases: Sequence[str]) -> bool:
    folded = _normalized(value)
    if not folded:
        return False
    forms = {folded}
    forms.add(
        re.sub(
            r"^(?:[-–—•]+|[ivxlcdm]+[.)]|\d+(?:[.)]|\s*[-–—]))\s*",
            "",
            folded,
        )
    )
    forms.add(re.sub(r"^\d+\s+", "", folded))
    return any(form == alias or form.startswith(alias + " ") for form in forms for alias in aliases)


def _compile_layout(value: Any, *, family_id: str) -> dict[str, Any]:
    fields = {
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
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != LAYOUT_FORMAT_VERSION
        or value["family_id"] != family_id
        or value["orientation"] != "STACKED_OR_HORIZONTAL_PERIOD_GROUPS"
        or type(value["lane_roles"]) is not list
        or not value["lane_roles"]
        or type(value["allowed_lane_role_sequences"]) is not list
        or not value["allowed_lane_role_sequences"]
        or type(value["conditional_lane_aliases"]) is not list
        or value["minimum_period_blocks"] != 2
        or value["max_period_blocks"] != 2
    ):
        raise _error("Gemini JSON stacked-period layout spec is invalid")
    roles: list[dict[str, Any]] = []
    role_names: set[str] = set()
    for raw in value["lane_roles"]:
        if (
            type(raw) is not dict
            or set(raw) != {"aliases", "mapping_eligible", "role", "unit_kind"}
            or type(raw["role"]) is not str
            or not raw["role"]
            or raw["role"] in role_names
            or type(raw["aliases"]) is not list
            or not raw["aliases"]
            or any(type(alias) is not str or not alias.strip() for alias in raw["aliases"])
            or type(raw["mapping_eligible"]) is not bool
            or raw["unit_kind"] != "MONEY"
        ):
            raise _error("Gemini JSON stacked-period lane declaration is invalid")
        aliases = [_normalized(alias) for alias in raw["aliases"]]
        if len(set(aliases)) != len(aliases) or any(not alias for alias in aliases):
            raise _error("Gemini JSON stacked-period lane aliases collide")
        role_names.add(raw["role"])
        roles.append({**raw, "aliases": aliases})
    sequences = []
    for raw in value["allowed_lane_role_sequences"]:
        if (
            type(raw) is not list
            or not raw
            or len(raw) != len(set(raw))
            or any(role not in role_names for role in raw)
            or raw in sequences
        ):
            raise _error("Gemini JSON stacked-period lane sequence is invalid")
        sequences.append(list(raw))
    conditional = []
    for raw in value["conditional_lane_aliases"]:
        if (
            type(raw) is not dict
            or set(raw) != {"aliases", "role", "when_roles_absent"}
            or raw["role"] not in role_names
            or type(raw["aliases"]) is not list
            or not raw["aliases"]
            or type(raw["when_roles_absent"]) is not list
            or not raw["when_roles_absent"]
            or any(role not in role_names for role in raw["when_roles_absent"])
        ):
            raise _error("Gemini JSON conditional lane declaration is invalid")
        conditional.append(
            {
                "aliases": [_normalized(alias) for alias in raw["aliases"]],
                "role": raw["role"],
                "when_roles_absent": list(raw["when_roles_absent"]),
            }
        )
    return {
        "allowed_lane_role_sequences": sequences,
        "conditional_lane_aliases": conditional,
        "family_id": family_id,
        "lane_roles": roles,
        "minimum_distinct_valued_roles": value["minimum_distinct_valued_roles"],
    }


def _compile_schema(value: Any, *, family_id: str, lane_roles: set[str]) -> dict[str, Any]:
    fields = {
        "accounting_equations",
        "family_id",
        "family_root_report_norm_id",
        "format_version",
        "mapping_bindings",
        "mixed_grouped_integer_policy",
        "schema_period_type",
        "signed_carrying_lane_policy",
        "sole_net_carrying_lane_policy",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != SCHEMA_FORMAT_VERSION
        or value["family_id"] != family_id
        or type(value["family_root_report_norm_id"]) is not int
        or value["family_root_report_norm_id"] <= 0
        or value["schema_period_type"] != "SNAPSHOT"
        or value["signed_carrying_lane_policy"]
        != "POSITIVE_TO_ASSET_NEGATIVE_TO_LIABILITY_ZERO_UNRESOLVED"
        or value["sole_net_carrying_lane_policy"]
        != "WHEN_NO_ATOMIC_CARRYING_LANES_POSITIVE_TO_ASSET_NEGATIVE_TO_LIABILITY_ZERO_UNRESOLVED"
    ):
        raise _error("Gemini JSON stacked-period schema spec is invalid")
    bindings: dict[tuple[str, str], dict[str, int]] = {}
    identities: set[int] = {value["family_root_report_norm_id"]}
    for raw in value["mapping_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != {"lane_role", "period_role", "report_norm_id_by_source_role"}
            or raw["period_role"] not in _PERIOD_ROLES
            or raw["lane_role"] not in lane_roles
            or type(raw["report_norm_id_by_source_role"]) is not dict
            or not raw["report_norm_id_by_source_role"]
        ):
            raise _error("Gemini JSON stacked-period mapping binding is invalid")
        key = (raw["period_role"], raw["lane_role"])
        role_map = raw["report_norm_id_by_source_role"]
        if (
            key in bindings
            or any(type(role) is not str or not role for role in role_map)
            or any(type(identity) is not int or identity <= 0 for identity in role_map.values())
            or identities.intersection(role_map.values())
        ):
            raise _error("Gemini JSON stacked-period mapping identity repeats")
        identities.update(role_map.values())
        bindings[key] = canonical_clone_v1(role_map)
    equations = []
    for raw in value["accounting_equations"]:
        if (
            type(raw) is not dict
            or set(raw) != {"component_lane_roles", "component_multipliers", "result_lane_role"}
            or type(raw["component_lane_roles"]) is not list
            or len(raw["component_lane_roles"]) < 2
            or len(raw["component_lane_roles"]) != len(raw["component_multipliers"])
            or any(role not in lane_roles for role in raw["component_lane_roles"])
            or raw["result_lane_role"] not in lane_roles
            or any(multiplier not in {-1, 1} for multiplier in raw["component_multipliers"])
        ):
            raise _error("Gemini JSON stacked-period accounting equation is invalid")
        equations.append(canonical_clone_v1(raw))
    return {
        "accounting_equations": equations,
        "bindings": bindings,
        "family_report_norm_id": value["family_root_report_norm_id"],
        "family_root_report_norm_id": value["family_root_report_norm_id"],
        "format_version": value["format_version"],
        "signed_carrying_lane_policy": value["signed_carrying_lane_policy"],
        "sole_net_carrying_lane_policy": value["sole_net_carrying_lane_policy"],
    }


def compile_gemini_json_stacked_period_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile the declarative topology, period/lane layout, and schema binding."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("Gemini JSON stacked-period topology spec is invalid") from exc
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec)
        != {
            "closure_policy",
            "family_id",
            "format_version",
            "layout_spec",
            "period_semantics",
        }
        or evaluation_spec["format_version"] != EVALUATION_FORMAT_VERSION
        or evaluation_spec["family_id"] != topology["family_id"]
        or evaluation_spec["closure_policy"]
        != "REQUIRE_EXACT_VISIBLE_PERIOD_LANE_AND_RECURSIVE_DIRECT_FRONTIER"
        or evaluation_spec["period_semantics"] != "BALANCE_COMPARATIVE"
    ):
        raise _error("Gemini JSON stacked-period evaluation spec is invalid")
    layout = _compile_layout(evaluation_spec["layout_spec"], family_id=topology["family_id"])
    schema = _compile_schema(
        schema_binding_spec,
        family_id=topology["family_id"],
        lane_roles={role["role"] for role in layout["lane_roles"]},
    )
    children_by_role = {child["role"]: child for child in topology["children"]}
    aliases_by_role = {
        child["role"]: sorted(
            {_normalized(alias) for matcher in child["matchers"] for alias in matcher["aliases"]}
        )
        for child in topology["children"]
    }
    anchor_groups = []
    query_anchor_groups = []
    raw_children_by_role = {child["role"]: child for child in topology_spec["children"]}
    raw_aliases_by_role = {
        role: sorted({alias for matcher in child["matchers"] for alias in matcher["aliases"]})
        for role, child in raw_children_by_role.items()
    }
    raw_parent_aliases = list(topology_spec["parent"]["aliases"])
    for combination in topology["required_role_combinations"]:
        if len(combination) == 1:
            role = combination[0]
            owners = {
                matcher["within_role"]
                for matcher in children_by_role[role]["matchers"]
                if matcher["within_role"] is not None
            }
            if len(owners) == 1:
                owner = next(iter(owners))
                anchor_groups.append([aliases_by_role[owner], aliases_by_role[role]])
                query_anchor_groups.append([raw_aliases_by_role[owner], raw_aliases_by_role[role]])
            anchor_groups.append([topology["parent"]["aliases"], aliases_by_role[role]])
            query_anchor_groups.append([raw_parent_aliases, raw_aliases_by_role[role]])
        elif len(combination) in {2, 3}:
            anchor_groups.append([aliases_by_role[role] for role in combination])
            query_anchor_groups.append([raw_aliases_by_role[role] for role in combination])
        else:
            raise _error("Gemini JSON stacked-period anchor combination is invalid")
    if not anchor_groups:
        raise _error("Gemini JSON stacked-period family has no bounded anchors")
    bound_roles = {role for role_map in schema["bindings"].values() for role in role_map}
    if not bound_roles <= set(children_by_role):
        raise _error("Gemini JSON stacked-period schema binds an undeclared source role")
    return {
        "aliases_by_role": aliases_by_role,
        "anchor_alias_groups": anchor_groups,
        "bindings": schema["bindings"],
        "claim_boundary": CLAIM_BOUNDARY,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "layout": layout,
        "query_anchor_alias_groups": query_anchor_groups,
        "query_parent_aliases": raw_parent_aliases,
        "schema": schema,
        "topology": topology,
    }


def _relative_period_role(value: str) -> str | None:
    matches = []
    for prefixes, role in (
        (
            (
                "tai ngay cuoi ky",
                "tai ngay cuoi quy",
                "tai ngay cuoi nam",
                "so du cuoi ky",
                "so du cuoi quy",
                "so du cuoi nam",
                "so cuoi ky",
                "so cuoi quy",
                "so cuoi nam",
                "cuoi ky",
                "cuoi quy",
                "cuoi nam",
            ),
            "CURRENT_PERIOD",
        ),
        (
            (
                "tai ngay dau ky",
                "tai ngay dau quy",
                "tai ngay dau nam",
                "so du dau ky",
                "so du dau quy",
                "so du dau nam",
                "so dau ky",
                "so dau quy",
                "so dau nam",
                "dau ky",
                "dau quy",
                "dau nam",
            ),
            "COMPARATIVE_PERIOD",
        ),
    ):
        for prefix in prefixes:
            if value == prefix:
                matches.append(role)
                break
            if not value.startswith(prefix + " "):
                continue
            suffix = value[len(prefix) + 1 :]
            if (
                suffix in _RELATIVE_PERIOD_RESTATEMENT_SUFFIXES
                or _DATE_DMY.fullmatch(suffix) is not None
                or _DATE_WORDS.fullmatch(suffix) is not None
                or _YEAR.fullmatch(suffix) is not None
            ):
                matches.append(role)
                break
    return matches[0] if len(set(matches)) == 1 else None


def _date_token(value: Any) -> _PeriodToken | None:
    folded = _normalized(value)
    if not folded:
        return None
    # A bounded visible list marker (``1 Tại ngày cuối kỳ``) is presentation,
    # not part of the period phrase. Keep the original surface for the
    # receipt while classifying the exact text after that marker.
    relative_surface = re.sub(
        r"^(?:[ivxlcdm]+[.)]|\d+(?:[.)]|\s*[-–—])?)\s+",
        "",
        folded,
    )
    role_hint = _relative_period_role(relative_surface)
    match = _DATE_DMY.search(folded) or _DATE_WORDS.search(folded)
    if match is not None:
        try:
            parsed = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            return None
        return _PeriodToken(parsed, role_hint, parsed.year, match.group(0))
    years = _YEAR.findall(folded)
    if len(set(years)) == 1:
        year = int(years[0])
        return _PeriodToken(None, role_hint, year, folded if role_hint else years[0])
    if role_hint is not None:
        return _PeriodToken(None, role_hint, None, folded)
    return None


def _period_identity(token: _PeriodToken) -> tuple[str, str]:
    if token.period_end is not None:
        return "DATE", token.period_end.isoformat()
    if token.role_hint is not None:
        return "ROLE", token.role_hint
    if token.period_year is not None:
        return "YEAR", str(token.period_year)
    raise _error("Gemini JSON stacked-period period token has no identity")


def _merged_period_token(tokens: Sequence[_PeriodToken]) -> _PeriodToken | None:
    if not tokens:
        return None
    dates = {token.period_end for token in tokens if token.period_end is not None}
    roles = {token.role_hint for token in tokens if token.role_hint is not None}
    years = {token.period_year for token in tokens if token.period_year is not None}
    if len(dates) > 1 or len(roles) > 1 or len(years) > 1:
        return None
    period_end = next(iter(dates), None)
    role_hint = next(iter(roles), None)
    period_year = next(iter(years), None)
    if period_end is not None:
        if period_year is not None and period_year != period_end.year:
            return None
        period_year = period_end.year
    labels = sorted({token.label for token in tokens})
    return _PeriodToken(period_end, role_hint, period_year, " / ".join(labels))


def _money(value: Any) -> dict[str, Any]:
    if value is None:
        return {"coefficient": 0, "source_text": None, "state": "BLANK_ZERO_IF_EQUATION_EXACT"}
    if type(value) is not str or not value.strip():
        raise _error("Gemini JSON stacked-period money cell is invalid")
    source_text = value
    # Surrounding whitespace is presentation, not a digit or sign.  Preserve
    # it in source_text while parsing the same exact visible numeric token.
    value = value.strip()
    if value in {"-", "–", "—", "_"}:
        return {"coefficient": 0, "source_text": source_text, "state": "DASH_ZERO"}
    negative = value.startswith("(") and value.endswith(")")
    body = value[1:-1] if negative else value
    if body.startswith("-"):
        if negative:
            raise _error("Gemini JSON stacked-period money sign is contradictory")
        negative = True
        body = body[1:]
    if not (_DIGITS.fullmatch(body) or _GROUPED.fullmatch(body)):
        raise _error("Gemini JSON stacked-period money grouping is invalid")
    coefficient = int(body.replace(".", "").replace(",", "").replace(" ", ""))
    return {
        "coefficient": -coefficient if negative else coefficient,
        "source_text": source_text,
        "state": "RAW_SIGNED_INTEGER",
    }


def _infer_ordered_structural_owners_v1(
    records_by_period: dict[str, list[dict[str, Any]]],
    *,
    topology: dict[str, Any],
    role_kinds: dict[str, str],
) -> None:
    """Recover a declared owner from an exact local row order.

    Gemini sometimes keeps the right labels and row order but flattens the
    hierarchy path or joins parent/child text into one noisy string.  This
    fallback never invents a relationship: the child role must explicitly
    declare the nearest preceding structural role as an allowed owner.
    """

    declared_owners: dict[str, set[str]] = defaultdict(set)
    for child in topology["children"]:
        for matcher in child["matchers"]:
            if matcher["within_role"] is not None:
                declared_owners[child["role"]].add(matcher["within_role"])
    for records in records_by_period.values():
        by_table: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            by_table[(record["section_id"], record["table_id"])].append(record)
        for table_records in by_table.values():
            current_structural_role = None
            for record in sorted(table_records, key=lambda item: item["row_ordinal"]):
                role = record["role"]
                if role_kinds.get(role) == "STRUCTURAL_GROUP":
                    current_structural_role = role
                    continue
                if record["owner_role"] is not None:
                    continue
                allowed = declared_owners.get(role, set())
                if current_structural_role in allowed:
                    record["owner_role"] = current_structural_role
                    record["owner_binding_kind"] = (
                        "ORDERED_NEAREST_PRECEDING_DECLARED_STRUCTURAL_GROUP"
                    )
                elif allowed:
                    # A child with a declared owner cannot leak through an
                    # incompatible structural group to an older group.
                    current_structural_role = None


def _column_lane_roles(
    columns: list[dict[str, Any]],
    layout: dict[str, Any],
    *,
    column_period_tokens: Sequence[_PeriodToken | None],
) -> list[str]:
    declared = {item["role"]: item for item in layout["lane_roles"]}
    primary: list[str | None] = []
    for column in columns:
        if type(column) is not dict or type(column.get("header_path_exact")) is not list:
            raise _error("Gemini JSON stacked-period column header path is invalid")
        if column.get("value_kind") != "MONEY":
            raise _error("Gemini JSON stacked-period candidate has a non-money lane")
        path = [_normalized(value) for value in column["header_path_exact"] if value]
        matches = []
        for path_ordinal, header in enumerate(path):
            for role, spec in declared.items():
                for alias in spec["aliases"]:
                    if header == alias or header.startswith(alias + " ") or alias in header:
                        matches.append((path_ordinal, len(alias), role))
        if matches:
            nearest = max(path_ordinal for path_ordinal, _length, _role in matches)
            longest = max(
                length for path_ordinal, length, _role in matches if path_ordinal == nearest
            )
            roles = {
                role
                for path_ordinal, length, role in matches
                if path_ordinal == nearest and length == longest
            }
            primary.append(next(iter(roles)) if len(roles) == 1 else None)
        else:
            primary.append(None)
    visible = {role for role in primary if role is not None}
    result = list(primary)
    for index, role in enumerate(result):
        if role is not None:
            continue
        header = _normalized(
            " ".join(str(value) for value in columns[index]["header_path_exact"] if value)
        )
        conditional_roles = []
        for conditional in layout["conditional_lane_aliases"]:
            if all(absent not in visible for absent in conditional["when_roles_absent"]) and any(
                alias in header for alias in conditional["aliases"]
            ):
                conditional_roles.append(conditional["role"])
        if len(set(conditional_roles)) == 1:
            result[index] = conditional_roles[0]
    if all(role is None for role in result):
        identities = [
            _period_identity(token) if token is not None else None for token in column_period_tokens
        ]
        unique_identities = {identity for identity in identities if identity is not None}
        singleton_sequences = [
            sequence for sequence in layout["allowed_lane_role_sequences"] if len(sequence) == 1
        ]
        if (
            len(unique_identities) == 2
            and all(identity is not None for identity in identities)
            and all(identities.count(identity) == 1 for identity in unique_identities)
            and len(singleton_sequences) == 1
        ):
            result = [singleton_sequences[0][0] for _column in columns]
    if any(role is None for role in result):
        raise _error("Gemini JSON stacked-period column lane is unresolved")
    resolved = [str(role) for role in result]
    allowed = layout["allowed_lane_role_sequences"]
    identities = [
        _period_identity(token) if token is not None else None for token in column_period_tokens
    ]
    unique_identities = {identity for identity in identities if identity is not None}
    if len(unique_identities) == 2 and all(identity is not None for identity in identities):
        compressed = [
            identity
            for index, identity in enumerate(identities)
            if index == 0 or identity != identities[index - 1]
        ]
        if len(compressed) != 2 or set(compressed) != unique_identities:
            raise _error("Gemini JSON stacked-period horizontal period groups are not contiguous")
        sequences = [
            [role for role, found in zip(resolved, identities, strict=True) if found == identity]
            for identity in compressed
        ]
    else:
        sequences = [resolved]
    if any(sequence not in allowed for sequence in sequences):
        raise _error("Gemini JSON stacked-period lane sequence is not declared")
    return resolved


def _semantic_money_table_axes(
    columns: list[dict[str, Any]], rows: list[dict[str, Any]]
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[int],
    list[tuple[int, dict[str, Any]]],
]:
    """Remove one exact row-ordinal control column from the money frontier."""

    non_money = [
        index for index, column in enumerate(columns) if column.get("value_kind") != "MONEY"
    ]
    if not non_money:
        return columns, rows, list(range(1, len(columns) + 1)), []
    if len(non_money) != 1:
        raise _error("Gemini JSON stacked-period candidate has a non-money lane")
    control_index = non_money[0]
    control_column = columns[control_index]
    header = _normalized(
        " ".join(
            str(value) for value in control_column.get("header_path_exact", []) if value is not None
        )
    )
    if header not in {"", "stt", "so thu tu"}:
        raise _error("Gemini JSON stacked-period candidate has a non-money lane")
    filtered_rows = []
    for row in rows:
        values = row.get("values_exact")
        if type(values) is not list or len(values) != len(columns):
            raise _error("Gemini JSON stacked-period row value axis is invalid")
        marker = values[control_index]
        if marker is not None and str(marker).strip() not in {"", "-", "–", "—", "_"}:
            # ``row_kind`` is advisory model interpretation.  Some banks put
            # a visible list number on a structural parent but Gemini calls
            # that row ITEM.  A blank/STT column whose populated surface is
            # itself only a bounded Arabic/Roman ordinal remains exact
            # presentation control evidence regardless of that advisory kind.
            if re.fullmatch(r"(?:\d{1,2}|[ivxlcdm]+)", _normalized(marker)) is None:
                raise _error("Gemini JSON stacked-period non-money lane is not an ordinal control")
        filtered_rows.append(
            {
                **row,
                "values_exact": [
                    value for index, value in enumerate(values) if index != control_index
                ],
            }
        )
    return (
        [column for index, column in enumerate(columns) if index != control_index],
        filtered_rows,
        [index + 1 for index in range(len(columns)) if index != control_index],
        [(control_index + 1, control_column)],
    )


def _row_role(
    row: dict[str, Any], *, topology: dict[str, Any], aliases_by_role: dict[str, list[str]]
) -> tuple[str | None, str | None]:
    scoped: list[tuple[str, str]] = []
    unscoped: list[tuple[str, str | None]] = []
    path = row.get("hierarchy_path_exact")
    if type(path) is not list:
        raise _error("Gemini JSON stacked-period hierarchy path is invalid")
    for child in topology["children"]:
        role = child["role"]
        for matcher in child["matchers"]:
            aliases = [_normalized(alias) for alias in matcher["aliases"]]
            if not _matches(row.get("label_exact"), aliases):
                continue
            within = matcher["within_role"]
            if within is None:
                unscoped.append((role, None))
                continue
            if any(
                _matches(value, aliases_by_role[within])
                for value in path[:-1]
                if type(value) is str
            ):
                scoped.append((role, within))
    matches = scoped or unscoped
    roles = {role for role, _owner in matches}
    if not roles:
        return None, None
    if len(roles) != 1:
        raise _error("Gemini JSON stacked-period row matches multiple source roles")
    role = next(iter(roles))
    owners = {owner for found_role, owner in matches if found_role == role and owner is not None}
    if len(owners) > 1:
        raise _error("Gemini JSON stacked-period row has multiple structural owners")
    return role, next(iter(owners)) if owners else None


def _table_periods(
    table: dict[str, Any],
    columns: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    *,
    section_context: Sequence[Any],
    table_period_fallback: _PeriodToken | None = None,
) -> tuple[list[_PeriodToken | None], list[_PeriodToken | None]]:
    column_dates: list[_PeriodToken | None] = []
    for column in columns:
        tokens = [
            token
            for value in column["header_path_exact"]
            if (token := _date_token(value)) is not None
        ]
        column_dates.append(_merged_period_token(tokens))
    title_token = _date_token(table.get("title_exact"))
    section_tokens = [
        token for value in section_context if (token := _date_token(value)) is not None
    ]
    # A date printed on the table is more local than the reporting-period text
    # in a broader section title.  The latter is only a fallback when the table
    # itself has no exact period carrier.
    table_token = title_token
    if table_token is None:
        table_token = _merged_period_token(section_tokens) or table_period_fallback
    unique_column_dates = {_period_identity(token) for token in column_dates if token is not None}
    if len(unique_column_dates) == 1:
        representative = next(token for token in column_dates if token is not None)
        column_dates = [token or representative for token in column_dates]
    row_dates = []
    preceding_row_token = None
    for row in rows:
        row_surfaces = list(row.get("hierarchy_path_exact", []))
        if row.get("label_exact") not in row_surfaces:
            row_surfaces.append(row.get("label_exact"))
        tokens = [token for value in row_surfaces if (token := _date_token(value)) is not None]
        explicit = _merged_period_token(tokens)
        if explicit is not None:
            preceding_row_token = explicit
        row_dates.append(explicit or preceding_row_token)
    has_row_period_axis = (
        len({_period_identity(token) for token in row_dates if token is not None}) >= 2
    )
    if has_row_period_axis:
        # Stacked row-period blocks are the local carrier.  Discard a broader
        # section/reporting date so it cannot create a third false period.
        column_dates = [None for _column in columns]
    if table_token is not None and not has_row_period_axis:
        column_dates = [token or table_token for token in column_dates]
    return column_dates, row_dates


def _period_roles(tokens: set[_PeriodToken]) -> dict[_PeriodToken, tuple[str, str]]:
    if not tokens:
        raise _error("Gemini JSON stacked-period region does not expose exactly two periods")
    token_roles: dict[_PeriodToken, str] = {}
    dates = sorted(
        {token.period_end for token in tokens if token.period_end is not None}, reverse=True
    )
    years = sorted(
        {token.period_year for token in tokens if token.period_year is not None}, reverse=True
    )
    if len(dates) == 2:
        role_by_date = {dates[0]: "CURRENT_PERIOD", dates[1]: "COMPARATIVE_PERIOD"}
        for token in tokens:
            role = role_by_date.get(token.period_end)
            if role is None and token.role_hint is not None:
                role = token.role_hint
            elif role is None and token.period_year is not None:
                matching = {
                    found_role
                    for found_date, found_role in role_by_date.items()
                    if found_date.year == token.period_year
                }
                role = next(iter(matching)) if len(matching) == 1 else None
            if role is None or (token.role_hint is not None and token.role_hint != role):
                raise _error("Gemini JSON stacked-period period evidence conflicts")
            token_roles[token] = role
    elif len(dates) > 2:
        raise _error("Gemini JSON stacked-period region does not expose exactly two periods")
    elif len(years) == 2:
        role_by_year = {years[0]: "CURRENT_PERIOD", years[1]: "COMPARATIVE_PERIOD"}
        for token in tokens:
            role = role_by_year.get(token.period_year)
            if role is None and token.role_hint is not None:
                role = token.role_hint
            if role is None or (token.role_hint is not None and token.role_hint != role):
                raise _error("Gemini JSON stacked-period period evidence conflicts")
            token_roles[token] = role
    elif {token.role_hint for token in tokens if token.role_hint is not None} == set(_PERIOD_ROLES):
        if any(token.role_hint is None for token in tokens):
            raise _error("Gemini JSON stacked-period period evidence conflicts")
        token_roles = {token: str(token.role_hint) for token in tokens}
    else:
        raise _error("Gemini JSON stacked-period region does not expose exactly two periods")
    if set(token_roles.values()) != set(_PERIOD_ROLES):
        raise _error("Gemini JSON stacked-period region does not expose exactly two periods")
    labels_by_role = {
        role: sorted(
            (token for token, found_role in token_roles.items() if found_role == role),
            key=lambda token: (
                token.period_end is None,
                token.period_year is None,
                token.label,
            ),
        )[0].label
        for role in _PERIOD_ROLES
    }
    return {token: (role, labels_by_role[role]) for token, role in token_roles.items()}


def _sum(records: Sequence[dict[str, Any]], lane_roles: Sequence[str]) -> dict[str, int]:
    return {
        lane: sum(
            record["values_by_lane"].get(lane, {"coefficient": 0})["coefficient"]
            for record in records
        )
        for lane in lane_roles
    }


def _visible_lane_equation_receipt(
    record: dict[str, Any], *, equations: Sequence[dict[str, Any]]
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate one visible row-local result lane without deriving any source cell."""

    cells = record["values_by_lane"]
    applicable = [
        equation
        for equation in equations
        if equation["result_lane_role"] in cells
        and cells[equation["result_lane_role"]]["source_text"] is not None
        and set(equation["component_lane_roles"]) <= set(cells)
    ]
    if not applicable:
        return None, None
    exact = []
    for equation in applicable:
        computed = sum(
            cells[role]["coefficient"] * multiplier
            for role, multiplier in zip(
                equation["component_lane_roles"],
                equation["component_multipliers"],
                strict=True,
            )
        )
        if computed == cells[equation["result_lane_role"]]["coefficient"]:
            exact.append(
                {
                    "component_lane_roles": equation["component_lane_roles"],
                    "component_multipliers": equation["component_multipliers"],
                    "result_lane_role": equation["result_lane_role"],
                }
            )
    if not exact:
        return None, (f"VISIBLE_LANE_EQUATION_NOT_EXACT:{record['period_role']}:{record['row_id']}")
    # More than one declared alternative can be equivalent when a component
    # is exact zero.  Persist all matching alternatives instead of choosing by
    # declaration order.
    return {
        "equation_kind": "VISIBLE_ROW_LOCAL_LANE_EQUATION",
        "matching_alternatives": exact,
        "period_role": record["period_role"],
        "result_lane_role": exact[0]["result_lane_role"],
        "row_id": record["row_id"],
        "source_role": record["role"],
    }, None


def _presentation_net_equation_receipt_v1(
    presentation: dict[str, Any],
    *,
    total_by_lane: dict[str, int],
    equations: Sequence[dict[str, Any]],
) -> dict[str, Any] | None:
    """Bind a printed net either to its signed lane or its asset/liability side.

    Some statements print a net magnitude under the asset column when positive
    and under the liability column when negative.  That is a presentation
    variant, not a new numeric component and not an OCR sign inference.
    """

    visible = [
        (lane, cell)
        for lane, cell in presentation["values_by_lane"].items()
        if cell["source_text"] is not None
    ]
    if len(visible) != 1:
        return None
    visible_lane, visible_cell = visible[0]
    exact = []
    for equation in equations:
        component_roles = equation["component_lane_roles"]
        if not set(component_roles) <= set(total_by_lane):
            continue
        computed = sum(
            total_by_lane[role] * multiplier
            for role, multiplier in zip(
                component_roles,
                equation["component_multipliers"],
                strict=True,
            )
        )
        binding_kind = None
        if visible_lane == equation["result_lane_role"] and visible_cell["coefficient"] == computed:
            binding_kind = "SIGNED_RESULT_LANE"
        elif equation["result_lane_role"] == "NET_VALUE":
            if (
                computed > 0
                and visible_lane == "ASSET_CARRYING_VALUE"
                and visible_cell["coefficient"] == computed
            ) or (
                computed < 0
                and visible_lane == "LIABILITY_CARRYING_VALUE"
                and visible_cell["coefficient"] == -computed
            ):
                binding_kind = "ASSET_LIABILITY_SIDE_PLACED_MAGNITUDE"
            elif (
                computed < 0
                and visible_lane == "LIABILITY_CARRYING_VALUE"
                and visible_cell["coefficient"] == computed
            ):
                binding_kind = "ASSET_LIABILITY_SIDE_PLACED_SIGNED_VALUE"
        if binding_kind is not None:
            exact.append(
                {
                    "binding_kind": binding_kind,
                    "component_lane_roles": component_roles,
                    "component_multipliers": equation["component_multipliers"],
                    "computed_signed_value": computed,
                    "result_lane_role": equation["result_lane_role"],
                    "visible_coefficient": visible_cell["coefficient"],
                    "visible_lane_role": visible_lane,
                }
            )
    if not exact:
        return None
    result = {
        "equation_kind": "VISIBLE_NET_PRESENTATION_EQUATION",
        "period_role": presentation["period_role"],
        "row_id": presentation["row_id"],
    }
    if len(exact) == 1:
        result["matching_alternative"] = exact[0]
        return result
    # A zero component can make the declared + and - alternatives identical.
    # This is not a choice between different values: retain every exact
    # alternative only when their visible and computed outcomes are identical.
    outcome_keys = {
        (
            alternative["binding_kind"],
            alternative["computed_signed_value"],
            alternative["result_lane_role"],
            alternative["visible_coefficient"],
            alternative["visible_lane_role"],
        )
        for alternative in exact
    }
    if len(outcome_keys) != 1:
        return None
    result["matching_alternatives"] = exact
    return result


def _candidate_id_material(candidate: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in candidate.items() if key != "candidate_id"}


def evaluate_gemini_json_stacked_period_family_region_v1(
    *,
    page_json: dict[str, Any],
    page_json_version_id: str,
    physical_page: int,
    table_refs: Sequence[tuple[str, str]],
    compiled_specs: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate all family tables on one page as one exact period frontier."""

    sections = page_json.get("sections")
    if (
        type(sections) is not list
        or type(table_refs) not in {list, tuple}
        or not table_refs
        or len(set(table_refs)) != len(table_refs)
    ):
        raise _error("Gemini JSON stacked-period table frontier is invalid")
    selected_tables = []
    for section_id, table_id in sorted(
        table_refs, key=lambda value: (int(value[0][1:]), int(value[1][1:]))
    ):
        try:
            section = sections[int(section_id[1:]) - 1]
            tables = section["tables"]
            table = tables[int(table_id[1:]) - 1]
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise _error("Gemini JSON stacked-period table is absent") from exc
        selected_tables.append((section_id, table_id, section, table))
    topology = compiled_specs["topology"]
    aliases_by_role = compiled_specs["aliases_by_role"]
    layout = compiled_specs["layout"]
    role_kinds = {child["role"]: child["role_kind"] for child in topology["children"]}
    raw_tables = []
    tokens: set[_PeriodToken] = set()
    reasons: list[str] = []
    period_fallback_by_ref: dict[tuple[str, str], _PeriodToken] = {}
    selected_by_section: dict[str, list[tuple[str, dict[str, Any], dict[str, Any]]]] = defaultdict(
        list
    )
    for section_id, table_id, section, table in selected_tables:
        selected_by_section[section_id].append((table_id, section, table))
    for section_id, tables_in_section in selected_by_section.items():
        section = tables_in_section[0][1]
        ordered_tokens = []
        for value in section.get("narratives_exact", []):
            if "chi tiet" not in _normalized(value) or "tai ngay" not in _normalized(value):
                continue
            token = _date_token(value)
            if token is not None and _period_identity(token) not in {
                _period_identity(item) for item in ordered_tokens
            }:
                ordered_tokens.append(token)
        if len(tables_in_section) == len(ordered_tokens) and len(ordered_tokens) in {1, 2}:
            for (table_id, _section, _table), token in zip(
                tables_in_section, ordered_tokens, strict=True
            ):
                period_fallback_by_ref[(section_id, table_id)] = token
    for section_id, table_id, section, table in selected_tables:
        columns = table.get("columns")
        rows = table.get("rows")
        if type(columns) is not list or not columns or type(rows) is not list or not rows:
            reasons.append(f"TABLE_AXIS_INCOMPLETE:{section_id}:{table_id}")
            continue
        try:
            columns, rows, source_column_ordinals, control_columns = _semantic_money_table_axes(
                columns, rows
            )
            column_dates, row_dates = _table_periods(
                table,
                columns,
                rows,
                section_context=[section.get("title_exact")],
                table_period_fallback=period_fallback_by_ref.get((section_id, table_id)),
            )
            lane_roles = _column_lane_roles(
                columns,
                layout,
                column_period_tokens=column_dates,
            )
        except GeminiJsonStackedPeriodAccountingFamilyV1Error as exc:
            reasons.append(f"TABLE_AXIS_ERROR:{section_id}:{table_id}:{exc}")
            continue
        tokens.update(token for token in column_dates + row_dates if token is not None)
        raw_tables.append(
            (
                section_id,
                table_id,
                table,
                columns,
                rows,
                lane_roles,
                column_dates,
                row_dates,
                source_column_ordinals,
                control_columns,
            )
        )
    try:
        period_by_date = _period_roles(tokens)
    except GeminiJsonStackedPeriodAccountingFamilyV1Error as exc:
        reasons.append(str(exc))
        period_by_date = {}
    records_by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
    totals_by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
    presentations_by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
    column_receipts = []
    for (
        section_id,
        table_id,
        _table,
        columns,
        rows,
        lane_roles,
        column_dates,
        row_dates,
        source_column_ordinals,
        control_columns,
    ) in raw_tables:
        for ordinal, control_column in control_columns:
            column_receipts.append(
                {
                    "column_ordinal": ordinal,
                    "header_path_exact": canonical_clone_v1(control_column["header_path_exact"]),
                    "lane_role": "SOURCE_ONLY_CONTROL",
                    "period_role": None,
                    "section_id": section_id,
                    "table_id": table_id,
                }
            )
        for column, lane_role, token, ordinal in zip(
            columns,
            lane_roles,
            column_dates,
            source_column_ordinals,
            strict=True,
        ):
            column_receipts.append(
                {
                    "column_ordinal": ordinal,
                    "header_path_exact": canonical_clone_v1(column["header_path_exact"]),
                    "lane_role": lane_role,
                    "period_role": period_by_date.get(token, (None, None))[0] if token else None,
                    "section_id": section_id,
                    "table_id": table_id,
                }
            )
        for row_ordinal, row in enumerate(rows, start=1):
            values = row.get("values_exact")
            if type(values) is not list or len(values) != len(columns):
                reasons.append(f"ROW_VALUE_AXIS_INCOMPLETE:{section_id}:{table_id}:{row_ordinal}")
                continue
            row_token = row_dates[row_ordinal - 1]
            role, owner = _row_role(row, topology=topology, aliases_by_role=aliases_by_role)
            values_by_period_lane: dict[tuple[str, str], dict[str, Any]] = {}
            try:
                for source, lane_role, column_token, column_ordinal in zip(
                    values,
                    lane_roles,
                    column_dates,
                    source_column_ordinals,
                    strict=True,
                ):
                    # A visible row-period group is more local than a table or
                    # section date.  Horizontal tables have no row token and
                    # therefore continue to use their per-column dates.
                    token = row_token or column_token
                    if token is None or token not in period_by_date:
                        raise _error("one valued row has no exact period carrier")
                    period_role, resolved_period = period_by_date[token]
                    cell = {
                        **_money(source),
                        "column_ordinal": column_ordinal,
                        "lane_role": lane_role,
                        "period_role": period_role,
                        "resolved_period": resolved_period,
                    }
                    key = (period_role, lane_role)
                    if key in values_by_period_lane:
                        raise _error("one row repeats a period/lane cell")
                    values_by_period_lane[key] = cell
            except GeminiJsonStackedPeriodAccountingFamilyV1Error as exc:
                reasons.append(f"ROW_CELL_ERROR:{section_id}:{table_id}:{row_ordinal}:{exc}")
                continue
            periods = sorted({period for period, _lane in values_by_period_lane})
            for period_role in periods:
                values_by_lane = {
                    lane: cell
                    for (period, lane), cell in values_by_period_lane.items()
                    if period == period_role
                }
                record = {
                    "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
                    "label_exact": row.get("label_exact"),
                    "owner_binding_kind": (
                        "EXPLICIT_HIERARCHY_PATH" if owner is not None else "UNBOUND"
                    ),
                    "owner_role": owner,
                    "period_role": period_role,
                    "role": role,
                    "row_id": f"{section_id}:{table_id}:r{row_ordinal}",
                    "row_kind": row.get("row_kind"),
                    "row_ordinal": row_ordinal,
                    "section_id": section_id,
                    "table_id": table_id,
                    "values_by_lane": values_by_lane,
                }
                has_value = any(
                    cell["source_text"] is not None and cell["state"] != "DASH_ZERO"
                    for cell in values_by_lane.values()
                )
                normalized_label = _normalized(row.get("label_exact"))
                is_net_presentation = normalized_label in {
                    "gia tri rong",
                    "gia tri thuan",
                    "so thuan",
                }
                is_labeled_period_total = (
                    row_token is not None
                    and _date_token(row.get("label_exact")) is not None
                    and row.get("row_kind") in {"SUBTOTAL", "TOTAL"}
                )
                if role is not None:
                    records_by_period[period_role].append(record)
                elif row.get("row_kind") in {"SUBTOTAL", "TOTAL"} and is_net_presentation:
                    presentations_by_period[period_role].append(record)
                elif (
                    row.get("row_kind") == "TOTAL"
                    or (
                        row.get("row_kind") == "SUBTOTAL"
                        and (
                            row.get("label_exact") is None
                            or normalized_label in {"tong", "tong cong"}
                        )
                    )
                    or is_labeled_period_total
                ):
                    if is_labeled_period_total and any(
                        cell["source_text"] is None for cell in values_by_lane.values()
                    ):
                        record["total_binding_kind"] = "LABELED_PERIOD_PARTIAL_LANE_TOTAL"
                    totals_by_period[period_role].append(record)
                elif has_value and row.get("row_kind") not in {"GROUP", "HEADER"}:
                    reasons.append(
                        f"UNMATCHED_VISIBLE_NUMERIC_ROW:{section_id}:{table_id}:{row_ordinal}"
                    )
    _infer_ordered_structural_owners_v1(
        records_by_period,
        topology=topology,
        role_kinds=role_kinds,
    )
    mappings = []
    equation_receipts = []
    population_signatures = []
    bindings = compiled_specs["bindings"]
    for period_role in _PERIOD_ROLES:
        records = records_by_period.get(period_role, [])
        if not records:
            reasons.append(f"PERIOD_HAS_NO_DECLARED_ROLE:{period_role}")
            continue
        by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            by_role[record["role"]].append(record)
        repeated = sorted(role for role, occurrences in by_role.items() if len(occurrences) > 1)
        if repeated:
            reasons.extend(
                f"ROLE_OCCURRENCE_COUNT_ABOVE_ONE:{period_role}:{role}" for role in repeated
            )
            continue
        one = {role: occurrences[0] for role, occurrences in by_role.items()}
        lanes = sorted({lane for record in records for lane in record["values_by_lane"]})
        if len(lanes) < layout["minimum_distinct_valued_roles"] and lanes != [
            "SIGNED_CARRYING_VALUE"
        ]:
            reasons.append(f"PERIOD_LANE_FRONTIER_TOO_SMALL:{period_role}")
            continue
        for record in records:
            receipt, reason = _visible_lane_equation_receipt(
                record,
                equations=compiled_specs["schema"]["accounting_equations"],
            )
            if receipt is not None:
                equation_receipts.append(receipt)
            if reason is not None:
                reasons.append(reason)
        consumed_children: set[str] = set()
        direct_records: list[dict[str, Any]] = []
        for role, record in sorted(one.items(), key=lambda item: item[1]["row_id"]):
            if role_kinds.get(role) == "STRUCTURAL_GROUP":
                children = [
                    child
                    for child_role, child in one.items()
                    if child["owner_role"] == role and child_role != role
                ]
                visible = any(
                    cell["source_text"] is not None for cell in record["values_by_lane"].values()
                )
                if children and visible:
                    child_sum = _sum(children, lanes)
                    result = {
                        lane: record["values_by_lane"].get(lane, {"coefficient": 0})["coefficient"]
                        for lane in lanes
                    }
                    if child_sum != result:
                        reasons.append(f"STRUCTURAL_SUBTOTAL_NOT_EXACT:{period_role}:{role}")
                    else:
                        consumed_children.update(child["role"] for child in children)
                        equation_receipts.append(
                            {
                                "component_bindings": [
                                    {
                                        "owner_binding_kind": child["owner_binding_kind"],
                                        "owner_role": child["owner_role"],
                                        "role": child["role"],
                                        "row_id": child["row_id"],
                                    }
                                    for child in children
                                ],
                                "component_roles": [child["role"] for child in children],
                                "period_role": period_role,
                                "result_row_id": record["row_id"],
                                "result_role": role,
                                "values_by_lane": result,
                            }
                        )
                        direct_records.append(record)
                elif visible:
                    direct_records.append(record)
                elif children:
                    direct_records.extend(children)
                    consumed_children.update(child["role"] for child in children)
            elif record["owner_role"] is None:
                direct_records.append(record)
        direct_records.extend(
            record
            for role, record in one.items()
            if record["owner_role"] is not None
            and role not in consumed_children
            and record["owner_role"] not in one
        )
        unique_direct = {record["role"]: record for record in direct_records}
        if len(unique_direct) != len(direct_records):
            reasons.append(f"DIRECT_FRONTIER_REUSES_ROLE:{period_role}")
            continue
        totals = totals_by_period.get(period_role, [])
        if len(totals) > 1:
            reasons.append(f"VISIBLE_FAMILY_TOTAL_COUNT_NOT_ONE:{period_role}:{len(totals)}")
            continue
        direct_sum = _sum(list(unique_direct.values()), lanes)
        if totals:
            if totals[0].get("total_binding_kind") == "LABELED_PERIOD_PARTIAL_LANE_TOTAL":
                visible_lanes = sorted(
                    lane
                    for lane, cell in totals[0]["values_by_lane"].items()
                    if cell["source_text"] is not None
                )
                if not visible_lanes or any(
                    totals[0]["values_by_lane"][lane]["coefficient"] != direct_sum[lane]
                    for lane in visible_lanes
                ):
                    reasons.append(
                        "VISIBLE_PARTIAL_PERIOD_TOTAL_NOT_EXACT_DIRECT_FRONTIER:"
                        f"{period_role}:{totals[0]['row_id']}"
                    )
                    continue
                equation_receipts.append(
                    {
                        "equation_kind": "VISIBLE_PARTIAL_PERIOD_LANE_TOTAL",
                        "period_role": period_role,
                        "result_carrier": totals[0]["row_id"],
                        "values_by_lane": {lane: direct_sum[lane] for lane in visible_lanes},
                        "visible_lane_roles": visible_lanes,
                    }
                )
                total = direct_sum
                result_carrier = "NOT_PRINTED_EXHAUSTIVE_VISIBLE_DIRECT_FRONTIER"
            else:
                total = {
                    lane: totals[0]["values_by_lane"].get(lane, {"coefficient": 0})["coefficient"]
                    for lane in lanes
                }
                total_record = {
                    **totals[0],
                    "role": topology["parent"]["role"],
                }
                receipt, reason = _visible_lane_equation_receipt(
                    total_record,
                    equations=compiled_specs["schema"]["accounting_equations"],
                )
                if receipt is not None:
                    equation_receipts.append(receipt)
                if reason is not None:
                    reasons.append(reason)
                if direct_sum != total:
                    reasons.append(
                        "VISIBLE_FAMILY_TOTAL_NOT_EXACT_DIRECT_FRONTIER:"
                        f"{period_role}:{totals[0]['row_id']}"
                    )
                    continue
                result_carrier = totals[0]["row_id"]
        else:
            total = direct_sum
            result_carrier = "NOT_PRINTED_EXHAUSTIVE_VISIBLE_DIRECT_FRONTIER"
        equation_receipts.append(
            {
                "component_bindings": [
                    {
                        "owner_binding_kind": record["owner_binding_kind"],
                        "owner_role": record["owner_role"],
                        "role": record["role"],
                        "row_id": record["row_id"],
                    }
                    for record in sorted(unique_direct.values(), key=lambda item: item["row_id"])
                ],
                "component_roles": sorted(unique_direct),
                "period_role": period_role,
                "result_carrier": result_carrier,
                "result_role": topology["parent"]["role"],
                "values_by_lane": total,
            }
        )
        # Optional separately printed net row must be an exact lane equation;
        # it is presentation evidence, never another family component.
        for presentation in presentations_by_period.get(period_role, []):
            presentation_receipt = _presentation_net_equation_receipt_v1(
                presentation,
                total_by_lane=total,
                equations=compiled_specs["schema"]["accounting_equations"],
            )
            if presentation_receipt is None:
                reasons.append(
                    "PRESENTATION_NET_ROW_NOT_ONE_EXACT_LANE_EQUATION:"
                    f"{period_role}:{presentation['row_id']}"
                )
            else:
                equation_receipts.append(presentation_receipt)
        for role, record in sorted(one.items()):
            for lane_role, cell in sorted(record["values_by_lane"].items()):
                effective_lane = lane_role
                mapping_kind = "DECLARATIVE_PERIOD_LANE_TO_SCHEMA_PROPOSAL"
                if lane_role == "SIGNED_CARRYING_VALUE" or (
                    lane_role == "NET_VALUE"
                    and not {
                        "ASSET_CARRYING_VALUE",
                        "LIABILITY_CARRYING_VALUE",
                        "SIGNED_CARRYING_VALUE",
                    }
                    & set(lanes)
                ):
                    if cell["coefficient"] == 0:
                        continue
                    effective_lane = (
                        "ASSET_CARRYING_VALUE"
                        if cell["coefficient"] > 0
                        else "LIABILITY_CARRYING_VALUE"
                    )
                    mapping_kind = "DECLARATIVE_EXACT_SIGN_SPLIT_PERIOD_LANE_TO_SCHEMA_PROPOSAL"
                role_map = bindings.get((period_role, effective_lane), {})
                report_norm_id = role_map.get(role)
                if report_norm_id is None or cell["source_text"] is None:
                    continue
                material = {
                    "columns": [
                        {
                            "header_path_exact": next(
                                receipt["header_path_exact"]
                                for receipt in column_receipts
                                if receipt["section_id"] == record["section_id"]
                                and receipt["table_id"] == record["table_id"]
                                and receipt["column_ordinal"] == cell["column_ordinal"]
                            ),
                            "lane_role": lane_role,
                            "period_role": period_role,
                        }
                    ],
                    "mapping_kind": mapping_kind,
                    "period_role": period_role,
                    "report_norm_id": report_norm_id,
                    "role": role,
                    "row_id": record["row_id"],
                    "source_lane_role": lane_role,
                    "source_row": {
                        "hierarchy_path_exact": record["hierarchy_path_exact"],
                        "label_exact": record["label_exact"],
                        "owner_binding_kind": record["owner_binding_kind"],
                        "owner_role": record["owner_role"],
                        "row_id": record["row_id"],
                    },
                    "values": [canonical_clone_v1(cell)],
                }
                mappings.append(
                    {
                        **material,
                        "item_mapping_id": "gjfspmv1:item:" + canonical_json_sha256_v1(material),
                    }
                )
        population_signatures.append(
            {
                "direct_roles": sorted(unique_direct),
                "period_role": period_role,
                "total_by_lane": total,
            }
        )
    reasons = sorted(set(reasons))
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": {
            "column_axis": column_receipts,
            "equations": equation_receipts,
            "population_signature": population_signatures,
            "rule": "EXACT_TWO_PERIOD_VISIBLE_RECURSIVE_DIRECT_FRONTIER",
        },
        "component_table_refs": [
            {"section_id": component_section_id, "table_id": table_id}
            for component_section_id, table_id, _section, _table in selected_tables
        ],
        "family_id": topology["family_id"],
        "mappings": [] if reasons else mappings,
        "page_json_version_id": page_json_version_id,
        "physical_page": physical_page,
        "reasons": reasons,
        "section_id": selected_tables[0][0],
        "status": UNRESOLVED if reasons else READY,
        "table_id": selected_tables[0][1],
    }
    return {
        "candidate_id": "gjfafcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def select_gemini_json_stacked_period_ready_candidate_v1(
    ready: Sequence[dict[str, Any]], *, compiled_specs: dict[str, Any]
) -> dict[str, Any] | None:
    """Select one exact candidate, or a unique strict role-rich equivalent."""

    if not ready:
        return None
    if len(ready) == 1:
        return ready[0]
    signatures = [candidate["closure_receipt"]["population_signature"] for candidate in ready]
    exact = {canonical_json_sha256_v1(signature) for signature in signatures}
    if len(exact) == 1:
        mapping_roles = [
            {
                (mapping["period_role"], mapping["role"], mapping["source_lane_role"])
                for mapping in candidate["mappings"]
            }
            for candidate in ready
        ]
        maximum = max(map(len, mapping_roles))
        winners = [index for index, roles in enumerate(mapping_roles) if len(roles) == maximum]
        if len(winners) == 1 and all(roles <= mapping_roles[winners[0]] for roles in mapping_roles):
            return ready[winners[0]]
    return None
