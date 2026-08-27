"""Generic two-period accounting roll-forward over selected Gemini JSON.

The primitive is deliberately layout-neutral.  It normalizes three equivalent
presentations into one ``period -> lane -> movement`` graph:

* one table containing two ordered period blocks;
* two period tables whose columns are accounting lanes; and
* two lane tables whose columns are periods.

Only exact Gemini JSON strings and declarative specifications are consumed.
There is no PDF geometry, OCR fallback, bank/file/page route, or numeric
backsolve across unrelated rows.  A blank is an unknown, not zero.  One blank
may be solved only by one full-rank lane equation; two blanks always remain
unresolved and identify a bounded row/table repair frontier.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

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

ENGINE_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_ACCOUNTING_FAMILY_V1"
EVALUATION_FORMAT_VERSION = "ACCOUNTING_ROLLFORWARD_FAMILY_EVALUATION_SPEC_V1"
LAYOUT_FORMAT_VERSION = "ACCOUNTING_ROLLFORWARD_LAYOUT_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_ROLLFORWARD_SCHEMA_BINDING_SPEC_V1"
QUERY_RECEIPT_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_REGION_QUERY_RECEIPT_V1"
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_OWNER_RESET_POPULATION_"
    "TWO_PERIOD_LANE_MOVEMENT_TRANSPOSE_EXACT_SIGNED_ROLLFORWARD_ONE_UNKNOWN_"
    "FULL_RANK_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_GEOMETRY_PPOCR_VIETOCR_BANK_"
    "FILE_PAGE_NOTE_ROUTING_MULTI_UNKNOWN_ZERO_COERCION_OR_EXPORT_AUTHORITY"
)

_ORIENTATIONS = {
    "LANE_TABLES_PERIOD_COLUMNS",
    "PERIOD_TABLES_LANE_COLUMNS",
    "STACKED_PERIOD_BLOCKS",
}
_MOVEMENT_KINDS = {
    "CLOSING",
    "DECREASE",
    "FOREIGN_EXCHANGE",
    "OPENING",
    "OTHER",
    "PROVISION_OR_REVERSAL",
    "USE",
}
_DATE_DMY = re.compile(
    r"(?<!\d)([0-3]?\d)(?:[./-]|\s+(?:thang\s+)?)"
    r"([01]?\d)(?:[./-]|\s+(?:nam\s+)?)((?:19|20)\d{2})(?!\d)"
)
_DATE_WORDS = re.compile(
    r"(?:tai\s+)?(?:ngay\s+)?([0-3]?\d)\s+thang\s+([01]?\d)\s+nam\s+"
    r"((?:19|20)\d{2})"
)
_YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
_DIGITS = re.compile(r"^\d+$")
_GROUPED = re.compile(r"^\d{1,3}(?:[., ]\d{3})+$")
_DASHES = {"-", "–", "—", "_"}


class GeminiJsonRollforwardAccountingFamilyV1Error(ValueError):
    """The roll-forward spec, source region, or exact arithmetic drifted."""


def _error(message: str) -> GeminiJsonRollforwardAccountingFamilyV1Error:
    return GeminiJsonRollforwardAccountingFamilyV1Error(message)


def _normalized(value: Any) -> str:
    if type(value) is not str:
        return ""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", normalize_vietnamese_anchor_v1(value)).split())


def _normalized_aliases(values: Any, *, label: str) -> list[str]:
    if (
        type(values) is not list
        or not values
        or any(type(value) is not str or not value.strip() for value in values)
    ):
        raise _error(f"roll-forward {label} aliases are invalid")
    aliases = [_normalized(value) for value in values]
    if any(not value for value in aliases) or len(aliases) != len(set(aliases)):
        raise _error(f"roll-forward {label} aliases collide")
    return aliases


def _aliases_by_role(topology: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        child["role"]: sorted(
            {_normalized(alias) for matcher in child["matchers"] for alias in matcher["aliases"]}
        )
        for child in topology["children"]
    }


def _compile_layout(value: Any, *, family_id: str, topology_roles: set[str]) -> dict[str, Any]:
    fields = {
        "allowed_orientations",
        "family_id",
        "format_version",
        "lane_roles",
        "max_component_tables",
        "max_page_span",
        "minimum_required_lanes",
        "movement_roles",
        "population_policy",
        "unit_aliases",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != LAYOUT_FORMAT_VERSION
        or value["family_id"] != family_id
        or type(value["allowed_orientations"]) is not list
        or set(value["allowed_orientations"]) != _ORIENTATIONS
        or value["max_component_tables"] != 2
        or value["max_page_span"] != 1
        or value["minimum_required_lanes"] != 2
    ):
        raise _error("roll-forward layout identity is invalid")

    lane_roles = []
    lane_names: set[str] = set()
    for raw in value["lane_roles"]:
        if (
            type(raw) is not dict
            or set(raw) != {"aliases", "optional", "role"}
            or type(raw["role"]) is not str
            or raw["role"] not in topology_roles
            or raw["role"] in lane_names
            or type(raw["optional"]) is not bool
        ):
            raise _error("roll-forward lane declaration is invalid")
        lane_names.add(raw["role"])
        lane_roles.append(
            {
                **raw,
                "aliases": _normalized_aliases(raw["aliases"], label=raw["role"]),
            }
        )
    if len(lane_roles) < 2 or sum(not role["optional"] for role in lane_roles) != 2:
        raise _error("roll-forward requires exactly two non-optional lanes")

    movement_roles = []
    movement_names: set[str] = set()
    kinds: set[str] = set()
    for raw in value["movement_roles"]:
        if (
            type(raw) is not dict
            or set(raw)
            != {
                "allow_one_unknown_inference",
                "equation_coefficient",
                "kind",
                "required",
                "role",
            }
            or type(raw["role"]) is not str
            or raw["role"] not in topology_roles
            or raw["role"] in movement_names
            or raw["kind"] not in _MOVEMENT_KINDS
            or raw["kind"] in kinds
            or type(raw["required"]) is not bool
            or type(raw["allow_one_unknown_inference"]) is not bool
            or raw["equation_coefficient"] not in {-1, 1}
        ):
            raise _error("roll-forward movement declaration is invalid")
        movement_names.add(raw["role"])
        kinds.add(raw["kind"])
        movement_roles.append(canonical_clone_v1(raw))
    if not {"OPENING", "PROVISION_OR_REVERSAL", "CLOSING"} <= kinds:
        raise _error("roll-forward endpoint/provision movement roles are incomplete")
    required_kinds = {item["kind"] for item in movement_roles if item["required"]}
    if required_kinds != {"OPENING", "PROVISION_OR_REVERSAL", "CLOSING"}:
        raise _error("roll-forward required movement roles drifted")
    coefficient_by_kind = {item["kind"]: item["equation_coefficient"] for item in movement_roles}
    if coefficient_by_kind["OPENING"] != 1 or coefficient_by_kind["CLOSING"] != -1:
        raise _error("roll-forward endpoint coefficients drifted")

    population = value["population_policy"]
    if (
        type(population) is not dict
        or set(population)
        != {
            "hard_negative_aliases",
            "owner_aliases",
            "owner_page_radius",
            "reset_aliases",
        }
        or population["owner_page_radius"] != 2
    ):
        raise _error("roll-forward population policy is invalid")
    checked_population = {
        "hard_negative_aliases": _normalized_aliases(
            population["hard_negative_aliases"], label="hard-negative"
        ),
        "owner_aliases": _normalized_aliases(population["owner_aliases"], label="owner"),
        "owner_page_radius": 2,
        "reset_aliases": _normalized_aliases(population["reset_aliases"], label="reset"),
    }
    return {
        "allowed_orientations": list(value["allowed_orientations"]),
        "lane_roles": lane_roles,
        "max_component_tables": 2,
        "max_page_span": 1,
        "minimum_required_lanes": 2,
        "movement_roles": movement_roles,
        "population_policy": checked_population,
        "unit_aliases": _normalized_aliases(value["unit_aliases"], label="unit"),
    }


def _compile_schema(
    value: Any,
    *,
    family_id: str,
    lane_roles: set[str],
    movement_roles: set[str],
) -> dict[str, Any]:
    fields = {
        "context_only_report_norm_ids",
        "family_id",
        "family_root_report_norm_id",
        "format_version",
        "mapping_bindings",
        "schema_period_role",
        "unknown_inference_policy",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != SCHEMA_FORMAT_VERSION
        or value["family_id"] != family_id
        or type(value["family_root_report_norm_id"]) is not int
        or value["family_root_report_norm_id"] <= 0
        or value["schema_period_role"] != "CURRENT_PERIOD"
        or value["unknown_inference_policy"] != "ONE_UNKNOWN_ONE_FULL_RANK_LANE_EQUATION_ONLY"
        or type(value["context_only_report_norm_ids"]) is not list
        or value["family_root_report_norm_id"] not in value["context_only_report_norm_ids"]
        or any(
            type(identity) is not int or identity <= 0
            for identity in value["context_only_report_norm_ids"]
        )
        or len(value["context_only_report_norm_ids"])
        != len(set(value["context_only_report_norm_ids"]))
    ):
        raise _error("roll-forward schema identity is invalid")
    bindings: dict[tuple[str, str], int] = {}
    identities = set(value["context_only_report_norm_ids"])
    for raw in value["mapping_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != {"lane_role", "movement_role", "report_norm_id"}
            or raw["lane_role"] not in lane_roles
            or raw["movement_role"] not in movement_roles
            or type(raw["report_norm_id"]) is not int
            or raw["report_norm_id"] <= 0
            or (raw["lane_role"], raw["movement_role"]) in bindings
            or raw["report_norm_id"] in identities
        ):
            raise _error("roll-forward schema binding is invalid or duplicate")
        bindings[(raw["lane_role"], raw["movement_role"])] = raw["report_norm_id"]
        identities.add(raw["report_norm_id"])
    return {
        "bindings": bindings,
        "context_only_report_norm_ids": list(value["context_only_report_norm_ids"]),
        "family_root_report_norm_id": value["family_root_report_norm_id"],
        "schema_period_role": "CURRENT_PERIOD",
        "unknown_inference_policy": value["unknown_inference_policy"],
    }


def compile_gemini_json_rollforward_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile one bank-blind lane/movement roll-forward contract."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("roll-forward topology spec is invalid") from exc
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
        or evaluation_spec["closure_policy"] != "EXACT_SIGNED_ROLLFORWARD_ONE_UNKNOWN_FULL_RANK"
        or evaluation_spec["period_semantics"] != "CURRENT_AND_COMPARATIVE_MOVEMENT"
    ):
        raise _error("roll-forward evaluation spec is invalid")
    topology_roles = {topology["parent"]["role"], *(c["role"] for c in topology["children"])}
    layout = _compile_layout(
        evaluation_spec["layout_spec"],
        family_id=topology["family_id"],
        topology_roles=topology_roles,
    )
    schema = _compile_schema(
        schema_binding_spec,
        family_id=topology["family_id"],
        lane_roles={item["role"] for item in layout["lane_roles"]},
        movement_roles={item["role"] for item in layout["movement_roles"]},
    )
    aliases_by_role = _aliases_by_role(topology)
    return {
        "aliases_by_role": aliases_by_role,
        "anchor_alias_groups": [
            [
                aliases_by_role[
                    next(item["role"] for item in layout["movement_roles"] if item["kind"] == kind)
                ]
                for kind in ("OPENING", "PROVISION_OR_REVERSAL", "CLOSING")
            ]
        ],
        "claim_boundary": CLAIM_BOUNDARY,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "layout": layout,
        "query_anchor_alias_groups": [
            [
                aliases_by_role[
                    next(item["role"] for item in layout["movement_roles"] if item["kind"] == kind)
                ]
                for kind in ("OPENING", "PROVISION_OR_REVERSAL", "CLOSING")
            ]
        ],
        "query_parent_aliases": canonical_clone_v1(topology_spec["parent"]["aliases"]),
        "rollforward_projection_policy": canonical_clone_v1(layout),
        "schema": schema,
        "topology": topology,
    }


def _date_tokens(value: Any) -> list[tuple[date, str]]:
    folded = _normalized(value)
    if not folded:
        return []
    matches = [*_DATE_DMY.finditer(folded), *_DATE_WORDS.finditer(folded)]
    result = []
    for match in sorted(matches, key=lambda item: item.start()):
        try:
            token = (
                date(int(match.group(3)), int(match.group(2)), int(match.group(1))),
                match.group(0),
            )
        except ValueError:
            continue
        if token not in result:
            result.append(token)
    if result:
        return result
    years = set(_YEAR.findall(folded))
    if len(years) == 1:
        year = int(next(iter(years)))
        return [(date(year, 12, 31), str(year))]
    return []


def _date_token(value: Any) -> tuple[date, str] | None:
    tokens = _date_tokens(value)
    return tokens[-1] if tokens else None


def _money(value: Any) -> dict[str, Any]:
    if value is None:
        return {"coefficient": None, "source_text": None, "state": "UNKNOWN_BLANK"}
    if type(value) is not str or not value.strip():
        raise _error("roll-forward money cell is not one exact string/null")
    source = value
    token = value.strip()
    if token in _DASHES:
        return {"coefficient": 0, "source_text": source, "state": "DASH_ZERO"}
    negative = token.startswith("(") and token.endswith(")")
    body = token[1:-1].strip() if negative else token
    if body.startswith("-"):
        if negative:
            raise _error("roll-forward money sign is contradictory")
        negative = True
        body = body[1:].strip()
    if not (_DIGITS.fullmatch(body) or _GROUPED.fullmatch(body)):
        raise _error("roll-forward money grouping is invalid")
    coefficient = int(body.replace(".", "").replace(",", "").replace(" ", ""))
    return {
        "coefficient": -coefficient if negative else coefficient,
        "source_text": source,
        "state": "RAW_SIGNED_INTEGER",
    }


def solve_one_unknown_rollforward_lane_v1(
    cells_by_role: Mapping[str, Mapping[str, Any]],
    *,
    movement_specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Solve or corroborate one exact scalar lane equation.

    Roles absent from ``cells_by_role`` are not printed movement rows and do
    not enter the equation.  A present null cell is one unknown.  This
    distinction is what prevents two omitted values from silently becoming
    two zeros.
    """

    specs = {item["role"]: item for item in movement_specs}
    if not cells_by_role or any(role not in specs for role in cells_by_role):
        raise _error("roll-forward lane contains an undeclared movement role")
    unknown = [
        role
        for role, cell in cells_by_role.items()
        if cell.get("state") == "UNKNOWN_BLANK" and cell.get("coefficient") is None
    ]
    known_sum = sum(
        int(cell["coefficient"]) * int(specs[role]["equation_coefficient"])
        for role, cell in cells_by_role.items()
        if role not in unknown
    )
    if not unknown:
        return {
            "equation_rank": 1,
            "inferred_role": None,
            "residual": known_sum,
            "status": "EXACT" if known_sum == 0 else "MISMATCH",
        }
    if len(unknown) != 1:
        return {
            "equation_rank": 1,
            "inferred_role": None,
            "residual": None,
            "status": "RANK_DEFICIENT_MULTIPLE_UNKNOWNS",
            "unknown_roles": sorted(unknown),
        }
    role = unknown[0]
    spec = specs[role]
    if not spec["allow_one_unknown_inference"]:
        return {
            "equation_rank": 1,
            "inferred_role": None,
            "residual": None,
            "status": "UNKNOWN_ROLE_INFERENCE_FORBIDDEN",
            "unknown_roles": [role],
        }
    coefficient = int(spec["equation_coefficient"])
    inferred = -known_sum * coefficient
    return {
        "equation_rank": 1,
        "inferred_coefficient": inferred,
        "inferred_role": role,
        "residual": 0,
        "status": "EXACT_ONE_UNKNOWN_INFERRED",
        "unknown_roles": [role],
    }


def _node(identifier: str, *, prefix: str, values: list[Any]) -> Any:
    if type(identifier) is not str or not identifier.startswith(prefix):
        raise _error("roll-forward source node identity is invalid")
    suffix = identifier.removeprefix(prefix)
    if not suffix.isdigit() or suffix.startswith("0"):
        raise _error("roll-forward source node identity is invalid")
    index = int(suffix) - 1
    if not 0 <= index < len(values):
        raise _error("roll-forward source node identity is out of range")
    return values[index]


def _source_table(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("roll-forward page section axis is invalid")
    section = _node(section_id, prefix="s", values=sections)
    tables = section.get("tables") if isinstance(section, Mapping) else None
    if type(tables) is not list:
        raise _error("roll-forward section table axis is invalid")
    table = _node(table_id, prefix="t", values=tables)
    if not isinstance(table, Mapping):
        raise _error("roll-forward table is invalid")
    return section, table


def _matches_alias(value: Any, aliases: Sequence[str]) -> bool:
    folded = _normalized(value)
    if not folded:
        return False
    forms = {folded, re.sub(r"^(?:\d+|[ivxlcdm]+)\s+", "", folded)}
    return any(
        form == alias or form.startswith(alias + " ") or f" {alias} " in f" {form} "
        for form in forms
        for alias in aliases
    )


def _role_for_row(row: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]) -> str | None:
    movement_roles = {item["role"] for item in compiled_specs["layout"]["movement_roles"]}
    matched = {
        role
        for role in movement_roles
        if _matches_alias(row.get("label_exact"), compiled_specs["aliases_by_role"][role])
    }
    if len(matched) > 1:
        raise _error("roll-forward row matches multiple movement roles")
    if matched:
        return next(iter(matched))
    period = _date_token(row.get("label_exact"))
    folded = _normalized(row.get("label_exact"))
    if period is None or not (
        folded.startswith("tai ngay ")
        or folded.startswith("tai ")
        or folded.startswith("ngay ")
        or "so du" in folded
    ):
        return None
    if (period[0].month, period[0].day) != (1, 1):
        return None
    kind = "OPENING"
    return next(
        item["role"] for item in compiled_specs["layout"]["movement_roles"] if item["kind"] == kind
    )


def _lane_for_surface(value: Any, *, compiled_specs: Mapping[str, Any]) -> str | None:
    matched = {
        item["role"]
        for item in compiled_specs["layout"]["lane_roles"]
        if _matches_alias(value, compiled_specs["aliases_by_role"][item["role"]])
    }
    if len(matched) > 1:
        raise _error("roll-forward surface matches multiple lane roles")
    return next(iter(matched)) if matched else None


def _lane_from_header(path: Any, *, compiled_specs: Mapping[str, Any]) -> str | None:
    if type(path) is not list or any(
        value is not None and type(value) is not str for value in path
    ):
        raise _error("roll-forward column header path is invalid")
    joined = " ".join(value for value in path if type(value) is str)
    if _matches_alias(
        joined,
        compiled_specs["layout"]["population_policy"]["hard_negative_aliases"],
    ):
        return None
    for value in reversed(path):
        if (role := _lane_for_surface(value, compiled_specs=compiled_specs)) is not None:
            return role
    return None


def _lane_from_table_context(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> str | None:
    return _lane_context_evidence(
        section,
        table,
        compiled_specs=compiled_specs,
    )["explicit_lane_role"]


def _lane_context_evidence(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Return candidate-local lane evidence without unioning nearby prose.

    A table title is the narrowest source, followed by the section title.  A
    single narrative role may bind directly.  Multiple narrative roles remain
    an ordered candidate axis for a later local one-to-one table assignment;
    they are never collapsed into an arbitrary set choice here.
    """

    narratives = section.get("narratives_exact", [])
    if type(narratives) is not list or any(
        value is not None and type(value) is not str for value in narratives
    ):
        raise _error("roll-forward section narrative axis is invalid")
    policy = compiled_specs["layout"]["population_policy"]
    structural_surfaces = [
        table.get("title_exact"),
        section.get("title_exact"),
        *narratives,
    ]
    hard_negative_visible = any(
        _matches_alias(surface, policy["hard_negative_aliases"])
        for surface in structural_surfaces
        if type(surface) is str
    )
    reset_visible = any(
        _matches_alias(surface, policy["reset_aliases"])
        for surface in narratives
        if type(surface) is str
    )
    title_role = _lane_for_surface(table.get("title_exact"), compiled_specs=compiled_specs)
    section_role = _lane_for_surface(section.get("title_exact"), compiled_specs=compiled_specs)
    narrative_evidence = [
        {"narrative_ordinal": ordinal, "role": role, "text_exact": value}
        for ordinal, value in enumerate(narratives, start=1)
        if type(value) is str
        and (role := _lane_for_surface(value, compiled_specs=compiled_specs)) is not None
    ]
    narrative_roles = [item["role"] for item in narrative_evidence]
    if len(narrative_roles) != len(set(narrative_roles)):
        raise _error("roll-forward narrative lane role repeats in one local section")
    explicit_role = title_role or section_role
    explicit_source = "TABLE_TITLE" if title_role is not None else "SECTION_TITLE"
    if title_role is not None and section_role is not None and title_role != section_role:
        raise _error("roll-forward table and section lane roles conflict")
    if explicit_role is None and len(narrative_roles) == 1:
        explicit_role = narrative_roles[0]
        explicit_source = "SINGLE_NARRATIVE"
    if hard_negative_visible:
        explicit_role = None
        explicit_source = None
    return {
        "explicit_lane_role": explicit_role,
        "explicit_source_kind": explicit_source if explicit_role is not None else None,
        "hard_negative_visible": hard_negative_visible,
        "narrative_lane_evidence": narrative_evidence,
        "narrative_lane_roles": narrative_roles,
        "reset_visible": reset_visible,
    }


def _bound_unit(table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]) -> str | None:
    surfaces = [table.get("unit_exact")]
    for column in table.get("columns", []):
        surfaces.extend(column.get("header_path_exact", []))
    aliases = compiled_specs["layout"]["unit_aliases"]
    matched = {
        alias
        for surface in surfaces
        if type(surface) is str
        for alias in aliases
        if alias == _normalized(surface) or _normalized(surface).endswith(" " + alias)
    }
    if not matched:
        return None
    selected = max(matched, key=lambda item: (len(item.split()), len(item), item))
    if any(selected != alias and not selected.endswith(" " + alias) for alias in matched):
        raise _error("roll-forward table binds multiple money units")
    return selected


def _unit_visible(table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]) -> bool:
    return _bound_unit(table, compiled_specs=compiled_specs) is not None


def _checked_row_values(rows: Sequence[Mapping[str, Any]], *, column_count: int) -> None:
    if any(
        type(row.get("values_exact")) is not list or len(row["values_exact"]) != column_count
        for row in rows
    ):
        raise _error("roll-forward row value vector does not match the column axis")


def _period_from_surfaces(values: Sequence[Any]) -> tuple[date, str] | None:
    tokens = [token for value in values for token in _date_tokens(value)]
    if not tokens:
        return None
    dates = {token[0] for token in tokens}
    if len(dates) == 1:
        return tokens[-1]
    years = {value.year for value in dates}
    if len(years) == 1:
        selected_date = max(dates)
        return next(token for token in reversed(tokens) if token[0] == selected_date)
    return None


def classify_gemini_json_rollforward_table_v1(
    *,
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify one decoded candidate table without granting numeric authority.

    The result is used by the selected-frontier storage query after indexed
    endpoint rows have reduced the search space.  Population qualifiers are
    evaluated per column so a customer-loan block can coexist with an LC block
    in the same table without admitting the LC columns.
    """

    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or not columns or type(rows) is not list or not rows:
        raise _error("roll-forward candidate table axes are incomplete")
    try:
        blocks = _row_blocks(rows, compiled_specs=compiled_specs)
    except GeminiJsonRollforwardAccountingFamilyV1Error:
        blocks = []
    movement_roles = [item["movement_role"] for block in blocks for item in block]
    core_roles = {
        item["role"] for item in compiled_specs["layout"]["movement_roles"] if item["required"]
    }
    lane_by_column = [
        _lane_from_header(column.get("header_path_exact"), compiled_specs=compiled_specs)
        for column in columns
    ]
    column_lanes = {role for role in lane_by_column if role is not None}
    context = _lane_context_evidence(
        section,
        table,
        compiled_specs=compiled_specs,
    )
    context_lane = context["explicit_lane_role"]
    if len(column_lanes) >= compiled_specs["layout"]["minimum_required_lanes"]:
        orientation = "LANE_COLUMNS"
    elif context_lane is not None or context["narrative_lane_roles"]:
        orientation = "PERIOD_COLUMNS"
    else:
        orientation = None
    structural_surfaces = [
        section.get("title_exact"),
        *section.get("narratives_exact", []),
        table.get("title_exact"),
    ]
    structural_text = " ".join(value for value in structural_surfaces if type(value) is str)
    accepted_header_text = " ".join(
        value
        for column, lane_role in zip(columns, lane_by_column, strict=True)
        if lane_role is not None
        for value in column.get("header_path_exact", [])
        if type(value) is str
    )
    population_policy = compiled_specs["layout"]["population_policy"]
    local_owner_visible = _matches_alias(
        " ".join((structural_text, accepted_header_text)),
        population_policy["owner_aliases"],
    )
    structural_hard_negative_visible = context["hard_negative_visible"] or _matches_alias(
        structural_text, population_policy["hard_negative_aliases"]
    )
    reasons = []
    if not core_roles <= set(movement_roles):
        reasons.append("ROLLFORWARD_CORE_MOVEMENT_ROLES_INCOMPLETE")
    if orientation is None:
        reasons.append("ROLLFORWARD_LANE_OR_PERIOD_AXIS_NOT_CLASSIFIED")
    if structural_hard_negative_visible:
        reasons.append("ROLLFORWARD_STRUCTURAL_HARD_NEGATIVE_VISIBLE")
    return {
        "column_lane_roles": lane_by_column,
        "context_lane_assignment_source_kind": context["explicit_source_kind"],
        "context_lane_candidates_in_source_order": context["narrative_lane_roles"],
        "context_lane_evidence": context["narrative_lane_evidence"],
        "context_lane_role": context_lane,
        "context_reset_visible": context["reset_visible"],
        "local_owner_visible": local_owner_visible,
        "movement_roles_in_source_order": movement_roles,
        "orientation": orientation,
        "reasons": reasons,
        "structural_hard_negative_visible": structural_hard_negative_visible,
    }


def _row_blocks(
    rows: list[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[list[dict[str, Any]]]:
    """Return explicit blocks plus a bounded shared-closing/opening block.

    A common accounting presentation prints ``O, movements, C(previous),
    movements, C(current)``.  The first closing is also the second period's
    opening even though its visible label remains ``closing``.  This is the
    only implicit endpoint admitted: it must follow one completed block and
    must itself terminate at the next visible closing.
    """

    role_specs = {item["role"]: item for item in compiled_specs["layout"]["movement_roles"]}
    opening = next(role for role, item in role_specs.items() if item["kind"] == "OPENING")
    closing = next(role for role, item in role_specs.items() if item["kind"] == "CLOSING")
    required = {role for role, item in role_specs.items() if item["required"]}
    blocks: list[list[dict[str, Any]]] = []
    active: list[dict[str, Any]] | None = None
    previous_closing: dict[str, Any] | None = None

    def source_entry(
        index: int,
        role: str,
        *,
        assignment_kind: str = "DECLARED_SURFACE_ROLE",
        source_movement_role: str | None = None,
        source_block_ordinal: int | None = None,
    ) -> dict[str, Any]:
        token = _date_token(rows[index].get("label_exact"))
        return {
            "assignment_kind": assignment_kind,
            "endpoint_date": token[0].isoformat() if token is not None else None,
            "movement_role": role,
            "row_index": index,
            "source_block_ordinal": source_block_ordinal,
            "source_movement_role": source_movement_role or role,
        }

    def is_ordered_date_endpoint(index: int) -> bool:
        folded = _normalized(rows[index].get("label_exact"))
        return _date_token(rows[index].get("label_exact")) is not None and (
            folded.startswith("tai ngay ")
            or folded.startswith("tai ")
            or folded.startswith("ngay ")
            or folded.startswith("so du tai ngay ")
        )

    def close_active(entry: dict[str, Any]) -> None:
        nonlocal active, previous_closing
        if active is None:
            raise _error("roll-forward closing endpoint has no opening endpoint")
        active.append(entry)
        roles = [item["movement_role"] for item in active]
        if len(roles) != len(set(roles)):
            raise _error("roll-forward period block repeats one movement role")
        if not required <= set(roles) or roles[0] != opening or roles[-1] != closing:
            raise _error("roll-forward period block has incomplete endpoint topology")
        opening_date = active[0]["endpoint_date"]
        closing_date = active[-1]["endpoint_date"]
        if active[0]["assignment_kind"] == "ORDERED_DATE_ENDPOINT_AS_OPENING" and (
            opening_date is None or closing_date is None or opening_date >= closing_date
        ):
            raise _error("roll-forward ordered date endpoint continuity is invalid")
        blocks.append(active)
        previous_closing = active[-1]
        active = None

    for index, row in enumerate(rows):
        role = _role_for_row(row, compiled_specs=compiled_specs)
        if role is None:
            folded = _normalized(row.get("label_exact"))
            endpoint_period = _date_token(row.get("label_exact"))
            if endpoint_period is not None and (
                folded.startswith("tai ngay ")
                or folded.startswith("tai ")
                or folded.startswith("ngay ")
                or "so du" in folded
            ):
                role = opening if active is None else closing
        if role is None:
            continue
        if role == opening:
            if active is not None:
                raise _error("roll-forward opening endpoint repeats before closing")
            active = [source_entry(index, role)]
            continue
        if role == closing:
            if active is None and previous_closing is None and is_ordered_date_endpoint(index):
                active = [
                    source_entry(
                        index,
                        opening,
                        assignment_kind="ORDERED_DATE_ENDPOINT_AS_OPENING",
                        source_movement_role=closing,
                    )
                ]
                continue
            close_active(source_entry(index, role))
            continue
        if active is None:
            if previous_closing is None:
                raise _error("roll-forward movement row has no opening endpoint")
            active = [
                source_entry(
                    previous_closing["row_index"],
                    opening,
                    assignment_kind="SHARED_PREVIOUS_CLOSING_AS_OPENING",
                    source_movement_role=closing,
                    source_block_ordinal=len(blocks),
                )
            ]
        if role in {item["movement_role"] for item in active}:
            raise _error("roll-forward period block repeats one movement role")
        active.append(source_entry(index, role))
    if active is not None:
        raise _error("roll-forward period block has no closing endpoint")
    return blocks


def _period_lane_cells_from_lane_columns(
    *,
    locator: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or not columns or type(rows) is not list or not rows:
        raise _error("roll-forward table row/column axis is incomplete")
    _checked_row_values(rows, column_count=len(columns))
    lane_by_column = [
        _lane_from_header(column.get("header_path_exact"), compiled_specs=compiled_specs)
        for column in columns
    ]
    if len({role for role in lane_by_column if role is not None}) < 2:
        return []
    blocks = _row_blocks(rows, compiled_specs=compiled_specs)
    if len(blocks) not in {1, 2}:
        raise _error("roll-forward lane-column table must expose one or two endpoint blocks")
    result = []
    for block_ordinal, block in enumerate(blocks, start=1):
        block_rows = [rows[item["row_index"]] for item in block]
        closing_row = block_rows[-1]
        period = (
            _period_from_surfaces([closing_row.get("label_exact")])
            or _period_from_surfaces([table.get("title_exact")])
            or _period_from_surfaces(
                [
                    *section.get("narratives_exact", []),
                    section.get("title_exact"),
                ]
            )
        )
        result.append(
            {
                "block_ordinal": block_ordinal,
                "bound_unit": _bound_unit(table, compiled_specs=compiled_specs),
                "cells": [
                    {
                        "assignment_kind": entry["assignment_kind"],
                        "cell": _money(rows[entry["row_index"]].get("values_exact")[column_index]),
                        "column_ordinal": column_index + 1,
                        "endpoint_date": entry["endpoint_date"],
                        "lane_role": lane_role,
                        "movement_role": entry["movement_role"],
                        "row_id": f"r{entry['row_index'] + 1}",
                        "source_block_ordinal": entry["source_block_ordinal"],
                        "source_movement_role": entry["source_movement_role"],
                    }
                    for entry in block
                    for column_index, lane_role in enumerate(lane_by_column)
                    if lane_role is not None
                ],
                "locator": canonical_clone_v1(locator),
                "period": period,
            }
        )
    return result


def _period_lane_cells_from_period_columns(
    *,
    locator: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    lane_role_override: str | None = None,
) -> list[dict[str, Any]]:
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or not columns or type(rows) is not list or not rows:
        raise _error("roll-forward lane table row/column axis is incomplete")
    _checked_row_values(rows, column_count=len(columns))
    lane_role = lane_role_override or _lane_from_table_context(
        section, table, compiled_specs=compiled_specs
    )
    if lane_role is None:
        return []
    periods = [_period_from_surfaces(column.get("header_path_exact", [])) for column in columns]
    if (
        any(period is None for period in periods)
        or len({period[0] for period in periods if period}) != 2
    ):
        raise _error("roll-forward lane table must expose exactly two period columns")
    blocks = _row_blocks(rows, compiled_specs=compiled_specs)
    if len(blocks) != 1:
        raise _error("roll-forward lane table must expose one endpoint block")
    block = blocks[0]
    result = []
    for column_index, period in enumerate(periods):
        result.append(
            {
                "block_ordinal": column_index + 1,
                "bound_unit": _bound_unit(table, compiled_specs=compiled_specs),
                "cells": [
                    {
                        "assignment_kind": entry["assignment_kind"],
                        "cell": _money(rows[entry["row_index"]].get("values_exact")[column_index]),
                        "column_ordinal": column_index + 1,
                        "endpoint_date": entry["endpoint_date"],
                        "lane_role": lane_role,
                        "movement_role": entry["movement_role"],
                        "row_id": f"r{entry['row_index'] + 1}",
                        "source_block_ordinal": entry["source_block_ordinal"],
                        "source_movement_role": entry["source_movement_role"],
                    }
                    for entry in block
                ],
                "locator": canonical_clone_v1(locator),
                "period": period,
            }
        )
    return result


def _assign_period_column_lane_roles(
    records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[int, str], list[dict[str, Any]], list[str]]:
    """Bind lane tables through one local, ordered, one-to-one assignment."""

    if not records:
        return {}, [], []
    declared_order = [item["role"] for item in compiled_specs["layout"]["lane_roles"]]
    candidates = []
    for ordinal, record in enumerate(records):
        classification = record["classification"]
        explicit = classification["context_lane_role"]
        axis = (
            [explicit]
            if explicit is not None
            else list(classification["context_lane_candidates_in_source_order"])
        )
        if (
            not axis
            or classification["context_reset_visible"]
            or classification["structural_hard_negative_visible"]
        ):
            return {}, [], ["ROLLFORWARD_LOCAL_LANE_ASSIGNMENT_EVIDENCE_INCOMPLETE"]
        candidates.append((ordinal, axis))

    assignments: list[dict[int, str]] = []

    def assign(index: int, used: frozenset[str], current: dict[int, str]) -> None:
        if index == len(candidates):
            assignments.append(dict(current))
            return
        ordinal, roles = candidates[index]
        for role in roles:
            if role not in used:
                current[ordinal] = role
                assign(index + 1, used | {role}, current)
                current.pop(ordinal)

    assign(0, frozenset(), {})
    assignment_kind = "UNIQUE_LOCAL_CANDIDATE_ASSIGNMENT"
    selected: dict[int, str] | None = assignments[0] if len(assignments) == 1 else None
    if selected is None and all(
        record["classification"]["context_lane_role"] is None for record in records
    ):
        axes = [roles for _ordinal, roles in candidates]
        same_local_section = (
            len(
                {
                    (
                        record["locator"]["page_json_version_id"],
                        record["locator"]["section_id"],
                    )
                    for record in records
                }
            )
            == 1
        )
        expected_order = sorted(axes[0], key=declared_order.index) if axes else []
        if (
            same_local_section
            and all(axis == axes[0] for axis in axes)
            and len(axes[0]) == len(records)
            and len(axes[0]) == len(set(axes[0]))
            and axes[0] == expected_order
        ):
            selected = dict(enumerate(axes[0]))
            assignment_kind = "ORDERED_LOCAL_NARRATIVE_TO_TABLE_ASSIGNMENT"
    if selected is None:
        return {}, [], ["ROLLFORWARD_LOCAL_LANE_ASSIGNMENT_NOT_UNIQUE"]
    receipts = [
        {
            "assignment_kind": assignment_kind,
            "assigned_lane_role": selected[ordinal],
            "candidate_lane_roles_in_source_order": list(candidates[ordinal][1]),
            "locator": canonical_clone_v1(records[ordinal]["locator"]),
        }
        for ordinal in range(len(records))
    ]
    return selected, receipts, []


def _region_axis(regions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    fields = {
        "page_json_version_id",
        "physical_page",
        "section_id",
        "table_id",
    }
    result = []
    for region in regions:
        if type(region) is not dict or set(region) != fields:
            raise _error("roll-forward component region locator is invalid")
        if (
            type(region["page_json_version_id"]) is not str
            or not region["page_json_version_id"].startswith("gfpstorev1:json:")
            or type(region["physical_page"]) is not int
            or region["physical_page"] <= 0
        ):
            raise _error("roll-forward component region identity is invalid")
        result.append(canonical_clone_v1(region))
    ordered = sorted(
        result,
        key=lambda item: (
            item["physical_page"],
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
            item["page_json_version_id"],
        ),
    )
    if ordered != result or len({canonical_json_sha256_v1(item) for item in result}) != len(result):
        raise _error("roll-forward component region axis is unordered or duplicate")
    if len(result) not in {1, 2} or result[-1]["physical_page"] - result[0]["physical_page"] > 1:
        raise _error("roll-forward component region span is out of bounds")
    return result


def evaluate_gemini_json_rollforward_family_cluster_v1(
    *,
    regions: Sequence[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one ordered one/two-table two-period roll-forward cluster."""

    region_axis = _region_axis(regions)
    if (
        type(query_receipt) is not dict
        or query_receipt.get("format_version") != QUERY_RECEIPT_FORMAT_VERSION
        or query_receipt.get("exact_region_count") < len(region_axis)
    ):
        raise _error("roll-forward query receipt is invalid")
    fragments = []
    period_column_records = []
    unit_visibility = []
    reasons = []
    for locator in region_axis:
        page_json = page_json_by_version.get(locator["page_json_version_id"])
        if type(page_json) is not dict:
            raise _error("roll-forward selected page JSON is absent")
        section, table = _source_table(
            page_json,
            section_id=locator["section_id"],
            table_id=locator["table_id"],
        )
        unit_visibility.append(_unit_visible(table, compiled_specs=compiled_specs))
        try:
            lane_columns = _period_lane_cells_from_lane_columns(
                locator=locator,
                section=section,
                table=table,
                compiled_specs=compiled_specs,
            )
        except GeminiJsonRollforwardAccountingFamilyV1Error:
            reasons.append("ROLLFORWARD_COMPONENT_TABLE_STRUCTURE_INVALID")
            continue
        if lane_columns:
            fragments.extend(lane_columns)
            continue
        classification = classify_gemini_json_rollforward_table_v1(
            section=section,
            table=table,
            compiled_specs=compiled_specs,
        )
        period_column_records.append(
            {
                "classification": classification,
                "locator": locator,
                "section": section,
                "table": table,
            }
        )
    lane_assignments, lane_assignment_receipts, assignment_reasons = (
        _assign_period_column_lane_roles(
            period_column_records,
            compiled_specs=compiled_specs,
        )
    )
    reasons.extend(assignment_reasons)
    for ordinal, record in enumerate(period_column_records):
        lane_role = lane_assignments.get(ordinal)
        if lane_role is None:
            continue
        try:
            fragments.extend(
                _period_lane_cells_from_period_columns(
                    locator=record["locator"],
                    section=record["section"],
                    table=record["table"],
                    compiled_specs=compiled_specs,
                    lane_role_override=lane_role,
                )
            )
        except GeminiJsonRollforwardAccountingFamilyV1Error:
            reasons.append("ROLLFORWARD_COMPONENT_TABLE_STRUCTURE_INVALID")
    if not any(unit_visibility):
        reasons.append("ROLLFORWARD_MONEY_UNIT_NOT_VISIBLE")
    dated = [fragment for fragment in fragments if fragment["period"] is not None]
    dates = sorted({fragment["period"][0] for fragment in dated}, reverse=True)
    if len(dates) != 2 or len(dated) != len(fragments):
        reasons.append("ROLLFORWARD_EXACT_TWO_PERIOD_AXIS_NOT_RESOLVED")
    period_role_by_date = {
        period: "CURRENT_PERIOD" if ordinal == 0 else "COMPARATIVE_PERIOD"
        for ordinal, period in enumerate(dates)
    }
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    duplicate_receipts = []
    for fragment in fragments:
        if fragment["period"] is None or fragment["period"][0] not in period_role_by_date:
            continue
        period_role = period_role_by_date[fragment["period"][0]]
        for item in fragment["cells"]:
            key = (period_role, item["lane_role"], item["movement_role"])
            record = {
                **canonical_clone_v1(item),
                "block_ordinal": fragment["block_ordinal"],
                "bound_unit": fragment["bound_unit"],
                "locator": canonical_clone_v1(fragment["locator"]),
                "period_role": period_role,
                "resolved_period": fragment["period"][1],
            }
            previous = merged.get(key)
            if previous is None:
                merged[key] = record
                continue
            same_cell = (
                previous["cell"] == record["cell"]
                and previous["resolved_period"] == record["resolved_period"]
            )
            if not same_cell:
                reasons.append("ROLLFORWARD_DUPLICATE_ROLE_PERIOD_LANE_CONFLICT:" + ":".join(key))
                continue
            duplicate_receipts.append(
                {
                    "corroborated_key": list(key),
                    "first_locator": previous["locator"],
                    "second_locator": record["locator"],
                }
            )

    required_lanes = {
        item["role"] for item in compiled_specs["layout"]["lane_roles"] if not item["optional"]
    }
    movement_specs = compiled_specs["layout"]["movement_roles"]
    required_movements = {item["role"] for item in movement_specs if item["required"]}
    current_lanes = {lane for period, lane, _movement in merged if period == "CURRENT_PERIOD"}
    if not required_lanes <= current_lanes:
        reasons.append("ROLLFORWARD_REQUIRED_CURRENT_LANES_INCOMPLETE")
    equations = []
    role_vectors = []
    potential_mappings = []
    unresolved_frontiers = []
    bindings = compiled_specs["schema"]["bindings"]
    for lane_role in sorted(current_lanes):
        cells = {
            movement: canonical_clone_v1(record["cell"])
            for (period, lane, movement), record in merged.items()
            if period == "CURRENT_PERIOD" and lane == lane_role
        }
        if not required_movements <= set(cells):
            reasons.append(f"ROLLFORWARD_REQUIRED_MOVEMENTS_INCOMPLETE:{lane_role}")
            continue
        solution = solve_one_unknown_rollforward_lane_v1(
            cells,
            movement_specs=movement_specs,
        )
        if solution["status"] == "EXACT_ONE_UNKNOWN_INFERRED":
            role = solution["inferred_role"]
            cells[role] = {
                **cells[role],
                "coefficient": solution["inferred_coefficient"],
                "state": "INFERRED_ONE_UNKNOWN_FULL_RANK",
            }
        if solution["status"] not in {"EXACT", "EXACT_ONE_UNKNOWN_INFERRED"}:
            reason = f"ROLLFORWARD_LANE_EQUATION_{solution['status']}:{lane_role}"
            reasons.append(reason)
            unresolved_frontiers.append(
                {
                    "lane_role": lane_role,
                    "reason": reason,
                    "unknown_roles": solution.get("unknown_roles", []),
                    "source_records": [
                        {
                            "locator": record["locator"],
                            "movement_role": movement,
                            "row_id": record["row_id"],
                        }
                        for (period, lane, movement), record in sorted(merged.items())
                        if period == "CURRENT_PERIOD" and lane == lane_role
                    ],
                }
            )
        else:
            equations.append(
                {
                    "equation_rank": 1,
                    "inferred_coefficient": solution.get("inferred_coefficient"),
                    "inferred_role": solution.get("inferred_role"),
                    "lane_role": lane_role,
                    "period_role": "CURRENT_PERIOD",
                    "role_coefficients": [
                        {
                            "coefficient": cells[item["role"]]["coefficient"],
                            "equation_coefficient": item["equation_coefficient"],
                            "role": item["role"],
                            "state": cells[item["role"]]["state"],
                        }
                        for item in movement_specs
                        if item["role"] in cells
                    ],
                    "status": solution["status"],
                }
            )
        for movement_role, cell in sorted(cells.items()):
            record = merged[("CURRENT_PERIOD", lane_role, movement_role)]
            vector = {
                "cell": cell,
                "lane_role": lane_role,
                "locator": record["locator"],
                "movement_role": movement_role,
                "period_role": "CURRENT_PERIOD",
                "resolved_period": record["resolved_period"],
                "row_id": record["row_id"],
            }
            role_vectors.append(vector)
            report_norm_id = bindings.get((lane_role, movement_role))
            if report_norm_id is None or cell["coefficient"] is None:
                continue
            material = {
                **canonical_clone_v1(vector),
                "mapping_kind": (
                    "DECLARATIVE_ONE_UNKNOWN_FULL_RANK_ROLLFORWARD_INFERENCE_PROPOSAL"
                    if cell["state"] == "INFERRED_ONE_UNKNOWN_FULL_RANK"
                    else "DECLARATIVE_VISIBLE_ROLLFORWARD_CELL_PROPOSAL"
                ),
                "report_norm_id": report_norm_id,
            }
            potential_mappings.append(
                {
                    **material,
                    "item_mapping_id": "gjfrfmv1:item:" + canonical_json_sha256_v1(material),
                }
            )
    reasons = sorted(set(reasons))
    orientation = (
        "STACKED_PERIOD_BLOCKS"
        if len(region_axis) == 1 and len(fragments) == 2
        else "PERIOD_TABLES_LANE_COLUMNS"
        if all(
            len({item["lane_role"] for item in fragment["cells"]}) >= 2 for fragment in fragments
        )
        else "LANE_TABLES_PERIOD_COLUMNS"
    )
    if orientation not in compiled_specs["layout"]["allowed_orientations"]:
        reasons.append("ROLLFORWARD_LAYOUT_ORIENTATION_NOT_DECLARED")
    mappings = [] if reasons else potential_mappings
    first = region_axis[0]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": {
            "component_region_axis_sha256": canonical_json_sha256_v1(region_axis),
            "duplicate_corroborations": duplicate_receipts,
            "equations": equations,
            "orientation": orientation,
            "potential_mapping_count": len(potential_mappings),
            "query_receipt": canonical_clone_v1(query_receipt),
            "role_vectors": role_vectors,
            "rule": "EXACT_SIGNED_ROLLFORWARD_ONE_UNKNOWN_FULL_RANK",
            "unresolved_frontiers": unresolved_frontiers,
        },
        "component_regions": region_axis,
        "component_table_refs": [
            {"section_id": item["section_id"], "table_id": item["table_id"]}
            for item in region_axis
            if item["page_json_version_id"] == first["page_json_version_id"]
        ],
        "family_id": compiled_specs["topology"]["family_id"],
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "status": UNRESOLVED if reasons else READY,
        "table_id": first["table_id"],
    }
    return {
        "candidate_id": "gjfafcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }
