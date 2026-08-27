"""Generic two-period accounting roll-forward over selected Gemini JSON.

The primitive is deliberately layout-neutral.  It normalizes three equivalent
presentations into one ``period -> lane -> movement`` graph:

* one table containing two ordered period blocks;
* two period tables whose columns are accounting lanes; and
* two lane tables whose columns are periods.

Only exact Gemini JSON strings, one content-addressed same-document region
receipt, and declarative specifications are consumed.  There is no PDF
geometry, OCR fallback, bank/file/page route, or numeric backsolve across
unrelated rows.  A blank is an unknown, not zero.  One blank may be solved only
by one full-rank lane equation; two blanks always remain unresolved and
identify a bounded row/table repair frontier.  Both periods must close their
equations and every comparative closing endpoint must equal the current
opening endpoint in the same lane and unit.
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
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_ACCOUNTING_FAMILY_V1"
EVALUATION_FORMAT_VERSION = "ACCOUNTING_ROLLFORWARD_FAMILY_EVALUATION_SPEC_V1"
LAYOUT_FORMAT_VERSION = "ACCOUNTING_ROLLFORWARD_LAYOUT_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_ROLLFORWARD_SCHEMA_BINDING_SPEC_V1"
QUERY_RECEIPT_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_REGION_QUERY_RECEIPT_V1"
QUERY_RECEIPT_AUTHENTICATION_KIND = (
    "CONTENT_ADDRESSED_EXACT_DOCUMENT_SOURCE_VERSION_ORDERED_REGION_BINDING"
)
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_CONTENT_ADDRESSED_DOCUMENT_SOURCE_VERSION_"
    "ORDERED_REGION_RECEIPT_DECLARATIVE_OWNER_EXPLICIT_DIRECTIONAL_CONTINUATION_"
    "FULL_SECTION_TABLE_ROW_RESET_POPULATION_TWO_PERIOD_LANE_MOVEMENT_TRANSPOSE_"
    "ENDPOINT_CONTINUITY_EXACT_"
    "SIGNED_ROLLFORWARD_ONE_UNKNOWN_FULL_RANK_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_"
    "GEOMETRY_PPOCR_VIETOCR_BANK_FILE_PAGE_NOTE_ROUTING_MULTI_UNKNOWN_ZERO_"
    "COERCION_OR_EXPORT_AUTHORITY_CANONICAL_SQLITE_SELECTED_QUERY_AND_CANDIDATE_"
    "REPLAY_REQUIRED_FOR_PERSISTENCE"
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
_PAGE_JSON_VERSION_ID = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_SOURCE_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CONTINUATION_NEGATION_TOKENS = frozenset(
    {
        "chang",
        "chua",
        "isn",
        "isnt",
        "khong",
        "neither",
        "never",
        "no",
        "nor",
        "not",
        "without",
    }
)
_ENGLISH_CONTINUATION_DETERMINERS = frozenset({"a", "an", "the"})
_ENGLISH_CONTINUATION_MODIFIERS = frozenset({"directly", "immediately", "just"})
_ENGLISH_PREVIOUS_TOKENS = frozenset({"preceding", "previous", "prior"})
_ENGLISH_OUTGOING_PREPOSITIONS = frozenset({"on", "onto", "to"})
_ENGLISH_NEXT_TOKENS = frozenset({"following", "next", "subsequent"})
_CONTINUES_FROM_PREVIOUS = {"BOTH", "CONTINUES_FROM_PREVIOUS_PAGE"}
_CONTINUATION_KINDS = {
    "BOTH",
    "CONTINUES_FROM_PREVIOUS_PAGE",
    "CONTINUES_ON_NEXT_PAGE",
    "NONE",
    "UNKNOWN",
}
_CONTINUATION_FROM_PREVIOUS = "FROM_PREVIOUS_PAGE"
_CONTINUATION_TO_NEXT = "TO_NEXT_PAGE"
_CONTINUATION_NEGATED = "NEGATED"
_CONTINUATION_AMBIGUOUS = "AMBIGUOUS"
_CONTINUATION_CONFLICT = "CONFLICT"
_CONTINUATION_NONE = "NONE"


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
        "aggregate_population_aliases",
        "allowed_orientations",
        "family_id",
        "format_version",
        "lane_roles",
        "max_component_tables",
        "max_page_span",
        "minimum_required_lanes",
        "movement_roles",
        "period_movement_context_aliases",
        "population_policy",
        "unit_aliases",
        "unit_bindings",
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
    if type(value["unit_bindings"]) is not list or not value["unit_bindings"]:
        raise _error("roll-forward money-unit bindings are invalid")
    unit_bindings = []
    canonical_units: set[str] = set()
    for raw in value["unit_bindings"]:
        if (
            type(raw) is not dict
            or set(raw)
            != {
                "aliases",
                "canonical_unit",
                "currency",
                "document_consensus_eligible",
                "magnitude_power10",
            }
            or type(raw["canonical_unit"]) is not str
            or not raw["canonical_unit"]
            or raw["canonical_unit"] in canonical_units
            or raw["currency"] != "VND"
            or type(raw["document_consensus_eligible"]) is not bool
            or raw["magnitude_power10"] not in {0, 3, 6, 9}
            or raw["document_consensus_eligible"] != (raw["magnitude_power10"] > 0)
        ):
            raise _error("roll-forward money-unit binding is invalid")
        canonical_units.add(raw["canonical_unit"])
        unit_bindings.append(
            {
                **canonical_clone_v1(raw),
                "aliases": _normalized_aliases(
                    raw["aliases"], label=f"unit-{raw['canonical_unit']}"
                ),
            }
        )
    return {
        "aggregate_population_aliases": _normalized_aliases(
            value["aggregate_population_aliases"], label="aggregate-population"
        ),
        "allowed_orientations": list(value["allowed_orientations"]),
        "lane_roles": lane_roles,
        "max_component_tables": 2,
        "max_page_span": 1,
        "minimum_required_lanes": 2,
        "movement_roles": movement_roles,
        "period_movement_context_aliases": _normalized_aliases(
            value["period_movement_context_aliases"], label="period-movement-context"
        ),
        "population_policy": checked_population,
        "unit_aliases": _normalized_aliases(value["unit_aliases"], label="unit"),
        "unit_bindings": unit_bindings,
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


def _rebuild_rollforward_equations_from_role_vectors_v1(
    role_vectors: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Replay the persisted equation axis from its canonical solved role vectors."""

    movement_specs = compiled_specs["layout"]["movement_roles"]
    required_movements = {item["role"] for item in movement_specs if item["required"]}
    by_lane: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for vector in role_vectors:
        key = (vector.get("period_role"), vector.get("lane_role"))
        movement_role = vector.get("movement_role")
        if (
            key[0] not in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
            or type(key[1]) is not str
            or type(movement_role) is not str
            or type(vector.get("cell")) is not dict
            or movement_role in by_lane.setdefault(key, {})
        ):
            raise _error("roll-forward role-vector equation axis is invalid")
        by_lane[key][movement_role] = canonical_clone_v1(vector["cell"])
    equations = []
    for period_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
        for lane_role in sorted(lane for period, lane in by_lane if period == period_role):
            cells = by_lane[(period_role, lane_role)]
            if not required_movements <= set(cells):
                continue
            inferred_roles = [
                role
                for role, cell in cells.items()
                if cell.get("state") == "INFERRED_ONE_UNKNOWN_FULL_RANK"
            ]
            if len(inferred_roles) > 1:
                raise _error("roll-forward role-vector inference axis is invalid")
            solver_cells = canonical_clone_v1(cells)
            if inferred_roles:
                inferred_role = inferred_roles[0]
                solver_cells[inferred_role] = {
                    **solver_cells[inferred_role],
                    "coefficient": None,
                    "state": "UNKNOWN_BLANK",
                }
            solution = solve_one_unknown_rollforward_lane_v1(
                solver_cells,
                movement_specs=movement_specs,
            )
            if inferred_roles and (
                solution["status"] != "EXACT_ONE_UNKNOWN_INFERRED"
                or solution["inferred_role"] != inferred_roles[0]
                or solution["inferred_coefficient"] != cells[inferred_roles[0]].get("coefficient")
            ):
                raise _error("roll-forward inferred role vector does not replay")
            equations.append(
                {
                    "equation_rank": 1,
                    "inferred_coefficient": solution.get("inferred_coefficient"),
                    "inferred_role": solution.get("inferred_role"),
                    "lane_role": lane_role,
                    "period_role": period_role,
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
    return equations


def _rebuild_rollforward_potential_mappings_from_role_vectors_v1(
    role_vectors: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Replay the exact schema-bound current-period mapping projection."""

    bindings = compiled_specs["schema"]["bindings"]
    mappings = []
    for vector in role_vectors:
        if vector.get("period_role") != "CURRENT_PERIOD":
            continue
        report_norm_id = bindings.get((vector.get("lane_role"), vector.get("movement_role")))
        cell = vector.get("cell")
        if report_norm_id is None or type(cell) is not dict or cell.get("coefficient") is None:
            continue
        material = {
            **canonical_clone_v1(vector),
            "mapping_kind": (
                "DECLARATIVE_ONE_UNKNOWN_FULL_RANK_ROLLFORWARD_INFERENCE_PROPOSAL"
                if cell.get("state") == "INFERRED_ONE_UNKNOWN_FULL_RANK"
                else "DECLARATIVE_VISIBLE_ROLLFORWARD_CELL_PROPOSAL"
            ),
            "report_norm_id": report_norm_id,
        }
        mappings.append(
            {
                **material,
                "item_mapping_id": "gjfrfmv1:item:" + canonical_json_sha256_v1(material),
            }
        )
    return mappings


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


def _projected_lane_columns_v1(
    columns: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[list[str | None], dict[str, Any]]:
    """Select one declared aggregate population when lane columns repeat.

    Some schedules present geographic or branch sub-populations beside one
    aggregate block.  A repeated lane remains ambiguous unless exactly one
    candidate carries a declaratively named aggregate ancestor.  This does
    not merge, sum, or prefer columns by position.
    """

    lane_by_column = [
        _lane_from_header(column.get("header_path_exact"), compiled_specs=compiled_specs)
        for column in columns
    ]
    projected = list(lane_by_column)
    decisions = []
    unresolved = []
    aliases = compiled_specs["layout"]["aggregate_population_aliases"]

    def duplicate_source_cell_receipts(indexes: Sequence[int]) -> list[dict[str, Any]]:
        if rows is None:
            return []
        result = []
        for block_ordinal, block in enumerate(
            _row_blocks(list(rows), compiled_specs=compiled_specs),
            start=1,
        ):
            for entry in block:
                row_index = entry["row_index"]
                values = rows[row_index].get("values_exact")
                if type(values) is not list or len(values) != len(columns):
                    raise _error("roll-forward duplicate population row axis is invalid")
                result.append(
                    {
                        "block_ordinal": block_ordinal,
                        "candidate_cells": [_money(values[index]) for index in indexes],
                        "movement_role": entry["movement_role"],
                        "row_id": f"r{row_index + 1}",
                    }
                )
        return result

    for lane_role in sorted({role for role in lane_by_column if role is not None}):
        indexes = [index for index, role in enumerate(lane_by_column) if role == lane_role]
        if len(indexes) == 1:
            continue
        aggregate_matches_by_index = {
            index: [
                _normalized(surface)
                for surface in columns[index].get("header_path_exact", [])
                if _normalized(surface) in aliases
            ]
            for index in indexes
        }
        aggregate_indexes = [index for index in indexes if aggregate_matches_by_index[index]]
        if len(aggregate_indexes) != 1:
            unresolved.append(
                {
                    "aggregate_candidate_column_ordinals": [
                        index + 1 for index in aggregate_indexes
                    ],
                    "candidate_column_ordinals": [index + 1 for index in indexes],
                    "duplicate_source_cell_receipts": duplicate_source_cell_receipts(indexes),
                    "lane_role": lane_role,
                }
            )
            continue
        selected = aggregate_indexes[0]
        identities = aggregate_matches_by_index[selected]
        if len(set(identities)) != 1:
            unresolved.append(
                {
                    "aggregate_candidate_column_ordinals": [selected + 1],
                    "candidate_column_ordinals": [index + 1 for index in indexes],
                    "duplicate_source_cell_receipts": duplicate_source_cell_receipts(indexes),
                    "lane_role": lane_role,
                    "reason": "AGGREGATE_HEADER_IDENTITY_AMBIGUOUS",
                }
            )
            continue
        row_sum_receipts = []
        if rows is not None:
            for row_index, row in enumerate(rows):
                if _role_for_row(row, compiled_specs=compiled_specs) is None:
                    continue
                values = row.get("values_exact")
                if type(values) is not list or len(values) != len(columns):
                    raise _error("roll-forward aggregate population row axis is invalid")
                cells = [_money(values[index]) for index in indexes]
                if any(cell["coefficient"] is None for cell in cells):
                    row_sum_receipts.append(
                        {
                            "candidate_coefficients": [cell["coefficient"] for cell in cells],
                            "row_id": f"r{row_index + 1}",
                            "status": "UNKNOWN_SIBLING_OR_AGGREGATE_CELL",
                        }
                    )
                    continue
                selected_offset = indexes.index(selected)
                selected_coefficient = cells[selected_offset]["coefficient"]
                sibling_sum = sum(
                    cell["coefficient"]
                    for offset, cell in enumerate(cells)
                    if offset != selected_offset
                )
                row_sum_receipts.append(
                    {
                        "candidate_coefficients": [cell["coefficient"] for cell in cells],
                        "row_id": f"r{row_index + 1}",
                        "selected_coefficient": selected_coefficient,
                        "sibling_sum": sibling_sum,
                        "status": (
                            "EXACT_HORIZONTAL_AGGREGATE"
                            if selected_coefficient == sibling_sum
                            else "HORIZONTAL_AGGREGATE_MISMATCH"
                        ),
                    }
                )
        if rows is not None and (
            not any(item["status"] == "EXACT_HORIZONTAL_AGGREGATE" for item in row_sum_receipts)
            or any(item["status"] == "HORIZONTAL_AGGREGATE_MISMATCH" for item in row_sum_receipts)
        ):
            unresolved.append(
                {
                    "aggregate_candidate_column_ordinals": [selected + 1],
                    "candidate_column_ordinals": [index + 1 for index in indexes],
                    "duplicate_source_cell_receipts": duplicate_source_cell_receipts(indexes),
                    "lane_role": lane_role,
                    "reason": "AGGREGATE_ROW_SUM_NOT_EXACT",
                    "row_sum_receipts": row_sum_receipts,
                }
            )
            continue
        for index in indexes:
            if index != selected:
                projected[index] = None
        decisions.append(
            {
                "aggregate_header_path_exact": canonical_clone_v1(
                    columns[selected].get("header_path_exact")
                ),
                "aggregate_identity_normalized": identities[0],
                "candidate_column_ordinals": [index + 1 for index in indexes],
                "lane_role": lane_role,
                "row_sum_receipts": row_sum_receipts,
                "selected_column_ordinal": selected + 1,
            }
        )
    return projected, {
        "aggregate_population_aliases": list(aliases),
        "decisions": decisions,
        "raw_lane_roles_by_column": lane_by_column,
        "rule": (
            "REPEATED_LANE_REQUIRES_EXACTLY_ONE_DECLARED_AGGREGATE_ANCESTOR_"
            "OTHERWISE_REMAINS_AMBIGUOUS"
        ),
        "status": (
            "DUPLICATE_POPULATION_NOT_UNIQUELY_AGGREGATED"
            if unresolved
            else "UNIQUE_AGGREGATE_POPULATION_SELECTED"
            if decisions
            else "DIRECT_UNIQUE_LANE_COLUMNS"
        ),
        "unresolved_duplicate_lanes": unresolved,
    }


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


def _sequence_positions(tokens: Sequence[str], sequence: Sequence[str]) -> list[int]:
    width = len(sequence)
    return [
        index
        for index in range(len(tokens) - width + 1)
        if tuple(tokens[index : index + width]) == tuple(sequence)
    ]


def _english_from_previous_page_grammar(tokens: Sequence[str]) -> bool:
    """Accept only bounded ``from`` + explicit prior-page token productions."""

    if not tokens or tokens[0] != "from":
        return False
    tail = list(tokens[1:8])
    if tail and tail[0] in _ENGLISH_CONTINUATION_DETERMINERS:
        tail.pop(0)
    if not tail:
        return False

    # adjective-first: ``from the immediately preceding page``
    adjective_first = list(tail)
    if adjective_first and adjective_first[0] in _ENGLISH_CONTINUATION_MODIFIERS:
        adjective_first.pop(0)
    if adjective_first and adjective_first[0] in _ENGLISH_PREVIOUS_TOKENS:
        adjective_first.pop(0)
        if adjective_first and adjective_first[0] in _ENGLISH_CONTINUATION_MODIFIERS:
            adjective_first.pop(0)
        if adjective_first and adjective_first[0] == "page":
            return True

    # noun-first: ``from the page immediately preceding this one``
    noun_first = list(tail)
    if not noun_first or noun_first.pop(0) != "page":
        return False
    if noun_first and noun_first[0] in _ENGLISH_CONTINUATION_MODIFIERS:
        noun_first.pop(0)
    if not noun_first or noun_first.pop(0) not in _ENGLISH_PREVIOUS_TOKENS:
        return False
    # The optional deictic tail is deliberately closed: an arbitrary noun such
    # as ``note`` or ``accounting period`` must not inherit the preceding-page
    # meaning merely because ``page`` and ``prior`` both appeared earlier.
    return tuple(noun_first) in {(), ("this", "one"), ("to", "this", "one")}


def _continuation_surface_direction(value: Any) -> str:
    """Parse one English/Vietnamese continuation marker fail-closed."""

    tokens = tuple(_normalized(value).split())
    if not tokens:
        return _CONTINUATION_NONE
    markers = [
        *(("ENGLISH", index) for index, token in enumerate(tokens) if token == "continued"),
        *(
            ("VIETNAMESE", index + 1)
            for sequence in (("con", "tiep"), ("tiep", "theo"), ("tiep", "tuc"))
            for index in _sequence_positions(tokens, sequence)
        ),
    ]
    if not markers:
        return _CONTINUATION_NONE
    if any(token in _CONTINUATION_NEGATION_TOKENS for token in tokens):
        return _CONTINUATION_NEGATED

    incoming = False
    outgoing = False
    for language, marker in markers:
        suffix = tokens[marker + 1 :]
        if language == "ENGLISH":
            incoming = incoming or _english_from_previous_page_grammar(suffix)
            outgoing = (
                outgoing
                or "overleaf" in suffix
                or any(
                    token in _ENGLISH_OUTGOING_PREPOSITIONS
                    and (
                        "page" in suffix[index + 1 : index + 5]
                        or any(
                            candidate in _ENGLISH_NEXT_TOKENS
                            for candidate in suffix[index + 1 : index + 4]
                        )
                    )
                    for index, token in enumerate(suffix)
                )
            )
            outgoing = outgoing or (
                "page" in suffix and any(token in _ENGLISH_NEXT_TOKENS for token in suffix)
            )
            continue

        page_positions = [index for index, token in enumerate(suffix) if token == "trang"]
        for page_index in page_positions:
            direction = suffix[page_index + 1 : page_index + 4]
            incoming = incoming or "truoc" in direction
            outgoing = outgoing or "sau" in direction
            outgoing = outgoing or (
                len(direction) >= 2 and direction[0] == "ke" and direction[1] == "tiep"
            )
            outgoing = outgoing or (
                len(direction) >= 2 and direction[0] == "tiep" and direction[1] == "theo"
            )
    if incoming and not outgoing:
        return _CONTINUATION_FROM_PREVIOUS
    if outgoing and not incoming:
        return _CONTINUATION_TO_NEXT
    if incoming and outgoing:
        return _CONTINUATION_CONFLICT
    return _CONTINUATION_AMBIGUOUS


def _explicit_continuation_evidence(
    section: Mapping[str, Any], table: Mapping[str, Any]
) -> list[dict[str, Any]]:
    continuation = table.get("continuation")
    if continuation not in _CONTINUATION_KINDS:
        raise _error("roll-forward table continuation kind is invalid")
    narratives = section.get("narratives_exact")
    if type(narratives) is not list:
        raise _error("roll-forward continuation narrative axis is invalid")
    surfaces = [
        ("TABLE_TITLE", table.get("title_exact")),
        ("SECTION_TITLE", section.get("title_exact")),
        *(("SECTION_NARRATIVE", value) for value in narratives),
    ]
    directional_surfaces = [
        {
            "direction": direction,
            "source_exact": value,
            "source_kind": source_kind,
        }
        for source_kind, value in surfaces
        if (direction := _continuation_surface_direction(value)) != _CONTINUATION_NONE
    ]
    # A forward-only marker belongs to the page that precedes a continuation;
    # it can never authenticate that this table continues from an owner above.
    if continuation == "CONTINUES_ON_NEXT_PAGE":
        return []
    contradictory = {
        _CONTINUATION_CONFLICT,
        _CONTINUATION_NEGATED,
        _CONTINUATION_TO_NEXT,
    }
    if continuation == "CONTINUES_FROM_PREVIOUS_PAGE" and any(
        item["direction"] in contradictory for item in directional_surfaces
    ):
        raise _error("roll-forward continuation directions conflict")
    if continuation == "BOTH" and any(
        item["direction"] in {_CONTINUATION_CONFLICT, _CONTINUATION_NEGATED}
        for item in directional_surfaces
    ):
        raise _error("roll-forward continuation directions conflict")
    evidence = (
        [
            {
                "source_exact": continuation,
                "source_kind": "TABLE_CONTINUATION_KIND",
            }
        ]
        if continuation in _CONTINUES_FROM_PREVIOUS
        else []
    )
    evidence.extend(
        {
            "source_exact": item["source_exact"],
            "source_kind": item["source_kind"],
        }
        for item in directional_surfaces
        if item["direction"] == _CONTINUATION_FROM_PREVIOUS
    )
    if continuation not in _CONTINUES_FROM_PREVIOUS and any(
        item["direction"] in contradictory for item in directional_surfaces
    ):
        return []
    return evidence


def _canonical_money_units_from_surface_v1(
    value: Any,
    *,
    compiled_specs: Mapping[str, Any],
    document_consensus_only: bool = False,
) -> set[str]:
    folded = _normalized(value)
    if not folded or "ty gia" in folded or "exchange rate" in folded:
        return set()
    matched = []
    for binding in compiled_specs["layout"]["unit_bindings"]:
        if document_consensus_only and not binding["document_consensus_eligible"]:
            continue
        if any(_matches_alias(value, [alias]) for alias in binding["aliases"]):
            matched.append(binding)
    magnitude_matches = [item for item in matched if item["magnitude_power10"] > 0]
    selected = magnitude_matches or matched
    return {item["canonical_unit"] for item in selected}


def _bound_unit(table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]) -> str | None:
    table_units = _canonical_money_units_from_surface_v1(
        table.get("unit_exact"),
        compiled_specs=compiled_specs,
    )
    if len(table_units) > 1:
        return None
    money_column_units = []
    for column in table.get("columns", []):
        if column.get("value_kind") != "MONEY":
            continue
        column_units = {
            unit
            for surface in column.get("header_path_exact", [])
            for unit in _canonical_money_units_from_surface_v1(
                surface,
                compiled_specs=compiled_specs,
            )
        }
        money_column_units.append(column_units)
    if table_units:
        table_unit = next(iter(table_units))
        if any(len(units) > 1 or (units and units != {table_unit}) for units in money_column_units):
            return None
        return table_unit
    if not money_column_units or any(len(units) != 1 for units in money_column_units):
        return None
    uniform_units = {next(iter(units)) for units in money_column_units}
    return next(iter(uniform_units)) if len(uniform_units) == 1 else None


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


def _period_semantics_evidence_v1(
    period: tuple[date, str] | None,
    *,
    source_kind: str | None,
    date_source_surfaces: Sequence[Any],
    local_context_surfaces: Sequence[Any],
    document_fiscal_close_year_binding_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    if period is None or source_kind is None:
        return None
    date_source_exact_axis = []
    for value in date_source_surfaces:
        tokens = _date_tokens(value)
        document_year_bound = (
            document_fiscal_close_year_binding_receipt is not None
            and type(value) is str
            and not (_DATE_DMY.search(_normalized(value)) or _DATE_WORDS.search(_normalized(value)))
            and any(token[0].year == period[0].year for token in tokens)
        )
        if (
            type(value) is str
            and value
            and (any(token[0] == period[0] for token in tokens) or document_year_bound)
            and value not in date_source_exact_axis
        ):
            date_source_exact_axis.append(value)
    if not date_source_exact_axis:
        raise _error("roll-forward period evidence has no exact date source")
    local_context_exact_axis = []
    for value in local_context_surfaces:
        if type(value) is str and value and value not in local_context_exact_axis:
            local_context_exact_axis.append(value)
    return {
        "document_fiscal_close_year_binding_receipt": (
            canonical_clone_v1(document_fiscal_close_year_binding_receipt)
            if document_fiscal_close_year_binding_receipt is not None
            else None
        ),
        "date_source_exact_axis": date_source_exact_axis,
        "local_context_exact_axis": local_context_exact_axis,
        "period_date": period[0].isoformat(),
        "source_kind": source_kind,
    }


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
    lane_by_column, lane_population_assignment_receipt = _projected_lane_columns_v1(
        columns,
        compiled_specs=compiled_specs,
        rows=rows,
    )
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
    period_context_owner_visible = _matches_alias(
        " ".join(
            value
            for value in [section.get("title_exact"), *section.get("narratives_exact", [])]
            if type(value) is str
        ),
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
        "continuation_evidence": _explicit_continuation_evidence(section, table),
        "context_lane_assignment_source_kind": context["explicit_source_kind"],
        "context_lane_candidates_in_source_order": context["narrative_lane_roles"],
        "context_lane_evidence": context["narrative_lane_evidence"],
        "context_lane_role": context_lane,
        "context_reset_visible": context["reset_visible"],
        "local_owner_visible": local_owner_visible,
        "lane_population_assignment_receipt": lane_population_assignment_receipt,
        "movement_roles_in_source_order": movement_roles,
        "orientation": orientation,
        "period_context_owner_visible": period_context_owner_visible,
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
        hierarchy_path_exact = rows[index].get("hierarchy_path_exact")
        if type(hierarchy_path_exact) is not list:
            raise _error("roll-forward source row hierarchy is invalid")
        return {
            "assignment_kind": assignment_kind,
            "endpoint_date": token[0].isoformat() if token is not None else None,
            "movement_role": role,
            "row_hierarchy_path_exact": canonical_clone_v1(hierarchy_path_exact),
            "row_index": index,
            "row_label_exact": rows[index].get("label_exact"),
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
        if (
            opening_date is not None and closing_date is not None and opening_date >= closing_date
        ) or (
            active[0]["assignment_kind"] == "ORDERED_DATE_ENDPOINT_AS_OPENING"
            and (opening_date is None or closing_date is None)
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
    lane_by_column, lane_population_assignment_receipt = _projected_lane_columns_v1(
        columns,
        compiled_specs=compiled_specs,
        rows=rows,
    )
    if len({role for role in lane_by_column if role is not None}) < 2:
        return []
    blocks = _row_blocks(rows, compiled_specs=compiled_specs)
    if len(blocks) not in {1, 2}:
        raise _error("roll-forward lane-column table must expose one or two endpoint blocks")
    result = []
    for block_ordinal, block in enumerate(blocks, start=1):
        block_rows = [rows[item["row_index"]] for item in block]
        closing_row = block_rows[-1]
        closing_period = _period_from_surfaces([closing_row.get("label_exact")])
        table_period = _period_from_surfaces([table.get("title_exact")])
        section_period = _period_from_surfaces(
            [*section.get("narratives_exact", []), section.get("title_exact")]
        )
        period = closing_period or table_period or section_period
        period_assignment_source_kind = (
            "CLOSING_ROW_LABEL"
            if closing_period is not None
            else "TABLE_TITLE"
            if table_period is not None
            else "SELECTED_SECTION_CONTEXT"
            if section_period is not None
            else None
        )
        section_period_surfaces = [
            *section.get("narratives_exact", []),
            section.get("title_exact"),
        ]
        period_date_source_surfaces = (
            [closing_row.get("label_exact")]
            if closing_period is not None
            else [table.get("title_exact")]
            if table_period is not None
            else section_period_surfaces
        )
        local_period_context_surfaces = [
            *section_period_surfaces,
            table.get("title_exact"),
            *(value for column in columns for value in column.get("header_path_exact", [])),
        ]
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
                        "row_hierarchy_path_exact": entry["row_hierarchy_path_exact"],
                        "row_id": f"r{entry['row_index'] + 1}",
                        "row_label_exact": entry["row_label_exact"],
                        "source_block_ordinal": entry["source_block_ordinal"],
                        "source_movement_role": entry["source_movement_role"],
                    }
                    for entry in block
                    for column_index, lane_role in enumerate(lane_by_column)
                    if lane_role is not None
                ],
                "locator": canonical_clone_v1(locator),
                "lane_population_assignment_receipt": canonical_clone_v1(
                    lane_population_assignment_receipt
                ),
                "period": period,
                "period_assignment_source_kind": period_assignment_source_kind,
                "period_semantics_evidence": _period_semantics_evidence_v1(
                    period,
                    source_kind=period_assignment_source_kind,
                    date_source_surfaces=period_date_source_surfaces,
                    local_context_surfaces=local_period_context_surfaces,
                ),
                "period_role_hint": None,
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
    period_surfaces = [column.get("header_path_exact", []) for column in columns]
    periods = [_period_from_surfaces(surfaces) for surfaces in period_surfaces]
    bare_year_columns = []
    for column_index, (surfaces, period) in enumerate(zip(period_surfaces, periods, strict=True)):
        if period is None:
            continue
        full_date_visible = any(
            (_DATE_DMY.search(_normalized(surface)) or _DATE_WORDS.search(_normalized(surface)))
            for surface in surfaces
            if type(surface) is str
        )
        if not full_date_visible:
            bare_year_columns.append(column_index)
    if bare_year_columns:
        years = {periods[index][0].year for index in bare_year_columns if periods[index]}
        if len(bare_year_columns) != len(columns) or len(years) != 2:
            raise _error("roll-forward mixed bare-year/full-date period columns are ambiguous")
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
        local_period_context_surfaces = [
            section.get("title_exact"),
            *section.get("narratives_exact", []),
            table.get("title_exact"),
            *columns[column_index].get("header_path_exact", []),
        ]
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
                        "row_hierarchy_path_exact": entry["row_hierarchy_path_exact"],
                        "row_id": f"r{entry['row_index'] + 1}",
                        "row_label_exact": entry["row_label_exact"],
                        "source_block_ordinal": entry["source_block_ordinal"],
                        "source_movement_role": entry["source_movement_role"],
                    }
                    for entry in block
                ],
                "locator": canonical_clone_v1(locator),
                "lane_population_assignment_receipt": None,
                "period": period,
                "period_assignment_source_kind": "COLUMN_HEADER_PATH",
                "period_semantics_evidence": _period_semantics_evidence_v1(
                    period,
                    source_kind="COLUMN_HEADER_PATH",
                    date_source_surfaces=columns[column_index].get("header_path_exact", []),
                    local_context_surfaces=local_period_context_surfaces,
                ),
                "period_role_hint": None,
            }
        )
    return result


def _fragments_have_same_full_rank_topology_v1(
    fragments: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> bool:
    if len(fragments) != 2:
        return False
    fingerprints = []
    movement_specs = compiled_specs["layout"]["movement_roles"]
    required_lanes = {
        item["role"] for item in compiled_specs["layout"]["lane_roles"] if not item["optional"]
    }
    for fragment in fragments:
        cells_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
        for item in fragment["cells"]:
            key = (item["lane_role"], item["movement_role"])
            if key in cells_by_key:
                return False
            cells_by_key[key] = item["cell"]
        lanes = {lane for lane, _movement in cells_by_key}
        if not required_lanes <= lanes:
            return False
        for lane_role in lanes:
            solution = solve_one_unknown_rollforward_lane_v1(
                {
                    movement: cell
                    for (lane, movement), cell in cells_by_key.items()
                    if lane == lane_role
                },
                movement_specs=movement_specs,
            )
            if solution["status"] not in {"EXACT", "EXACT_ONE_UNKNOWN_INFERRED"}:
                return False
        fingerprints.append(sorted([list(key) for key in cells_by_key]))
    return fingerprints[0] == fingerprints[1]


def _adjacent_distinct_component_tables_v1(fragments: Sequence[Mapping[str, Any]]) -> bool:
    if len(fragments) != 2:
        return False
    first, second = (item["locator"] for item in fragments)
    return (
        first["page_json_version_id"] == second["page_json_version_id"]
        and first["section_id"] == second["section_id"]
        and int(second["table_id"][1:]) == int(first["table_id"][1:]) + 1
        and first["table_id"] != second["table_id"]
    )


def _resolve_ordered_period_components_v1(
    fragments: Sequence[dict[str, Any]],
    *,
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    document_fiscal_close_context_evidence: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Bind two adjacent period tables from exact ordered local context.

    Two dated movement narratives form an order-preserving bijection.  With
    only one current date, the second table remains explicitly symbolic; no
    calendar date is fabricated.  That weaker assignment is admitted only
    when both adjacent tables expose the same independently closing topology.
    """

    result = [dict(fragment) for fragment in fragments]
    base_receipt = {
        "assignments": [],
        "movement_context_evidence": [],
        "rule": (
            "ORDERED_DISTINCT_MOVEMENT_DATES_TO_ADJACENT_COMPONENTS_OR_"
            "ONE_CURRENT_DATE_PLUS_SYMBOLIC_COMPARATIVE"
        ),
        "status": "NOT_APPLICABLE",
    }
    if not _adjacent_distinct_component_tables_v1(result):
        return result, base_receipt
    locators = [fragment["locator"] for fragment in result]
    version_id = locators[0]["page_json_version_id"]
    page_json = page_json_by_version.get(version_id)
    if not isinstance(page_json, Mapping):
        raise _error("roll-forward period context page is absent")
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("roll-forward period context section axis is invalid")
    section_ordinal = int(locators[0]["section_id"][1:])
    section = sections[section_ordinal - 1]
    if not isinstance(section, Mapping):
        raise _error("roll-forward period context section is invalid")
    narratives = section.get("narratives_exact")
    if type(narratives) is not list:
        raise _error("roll-forward period context narrative axis is invalid")
    movement_aliases = compiled_specs["layout"]["period_movement_context_aliases"]
    owner_text = " ".join(
        value for value in [section.get("title_exact"), *narratives] if type(value) is str
    )
    if not _matches_alias(
        owner_text,
        compiled_specs["layout"]["population_policy"]["owner_aliases"],
    ):
        return result, {**base_receipt, "status": "LOCAL_OWNER_SCOPE_NOT_VISIBLE"}
    movement_evidence = []

    def period_context_record(
        *,
        source_exact: Any,
        source_kind: str,
        narrative_ordinal: int | None,
    ) -> dict[str, Any] | None:
        tokens = _date_tokens(source_exact)
        unique_dates = {token[0] for token in tokens}
        base = {
            "date": None,
            "date_token": None,
            "document_fiscal_close_year_binding_receipt": None,
            "narrative_ordinal": narrative_ordinal,
            "source_exact": source_exact,
            "source_kind": source_kind,
            "year": None,
        }
        if len(unique_dates) != 1:
            return (
                {
                    **base,
                    "status": "AMBIGUOUS_MULTIPLE_DATES",
                }
                if unique_dates
                else None
            )
        selected_token = tokens[-1]
        selected_date = selected_token[0]
        folded = _normalized(source_exact)
        full_date_visible = bool(
            folded and (_DATE_DMY.search(folded) or _DATE_WORDS.search(folded))
        )
        if full_date_visible:
            return {
                **base,
                "date": selected_date.isoformat(),
                "date_token": selected_token[1],
                "status": "EXACT_ONE_DATE",
                "year": selected_date.year,
            }
        binding = _document_fiscal_close_year_binding_receipt_v1(
            document_fiscal_close_context_evidence,
            year=selected_date.year,
        )
        if binding is None:
            return {
                **base,
                "date_token": selected_token[1],
                "status": "EXACT_ONE_YEAR_UNBOUND",
                "year": selected_date.year,
            }
        year_context = binding["year_context"]
        bound_date = date(selected_date.year, year_context["month"], year_context["day"])
        return {
            **base,
            "date": bound_date.isoformat(),
            "date_token": selected_token[1],
            "document_fiscal_close_year_binding_receipt": binding,
            "status": "EXACT_ONE_YEAR_BOUND_TO_DOCUMENT_FISCAL_CLOSE_CONTEXT",
            "year": selected_date.year,
        }

    for narrative_ordinal, source_exact in enumerate(narratives, start=1):
        if not _matches_alias(source_exact, movement_aliases):
            continue
        record = period_context_record(
            source_exact=source_exact,
            source_kind="SELECTED_SECTION_MOVEMENT_NARRATIVE",
            narrative_ordinal=narrative_ordinal,
        )
        if record is not None:
            movement_evidence.append(record)
    exact_statuses = {
        "EXACT_ONE_DATE",
        "EXACT_ONE_YEAR_BOUND_TO_DOCUMENT_FISCAL_CLOSE_CONTEXT",
    }
    exact_movement = [item for item in movement_evidence if item["status"] in exact_statuses]
    if not exact_movement:
        context_surfaces = [("SELECTED_SECTION_TITLE", section.get("title_exact"))]
        if section_ordinal > 1:
            previous = sections[section_ordinal - 2]
            if isinstance(previous, Mapping):
                context_surfaces.insert(
                    0,
                    ("IMMEDIATELY_PRECEDING_SECTION_TITLE", previous.get("title_exact")),
                )
        for source_kind, source_exact in context_surfaces:
            record = period_context_record(
                source_exact=source_exact,
                source_kind=source_kind,
                narrative_ordinal=None,
            )
            if record is not None and record["status"] in exact_statuses:
                exact_movement.append(record)
                movement_evidence.append(record)
    receipt = {**base_receipt, "movement_context_evidence": movement_evidence}
    if len(exact_movement) == 2 and len(movement_evidence) == 2:
        dates = [date.fromisoformat(item["date"]) for item in exact_movement]
        if dates[0] <= dates[1] or len(set(dates)) != 2:
            return result, {**receipt, "status": "AMBIGUOUS_OR_REVERSED_CONTEXT_DATES"}
        assignments = []
        for ordinal, (fragment, period_date, evidence) in enumerate(
            zip(result, dates, exact_movement, strict=True)
        ):
            if fragment["period"] is not None and fragment["period"][0] != period_date:
                return result, {**receipt, "status": "CONFLICTING_TABLE_PERIOD_EVIDENCE"}
            fragment["period"] = (period_date, evidence["date_token"])
            fragment["period_semantics_evidence"] = _period_semantics_evidence_v1(
                fragment["period"],
                source_kind=evidence["source_kind"],
                date_source_surfaces=[evidence["source_exact"]],
                local_context_surfaces=[evidence["source_exact"]],
                document_fiscal_close_year_binding_receipt=evidence[
                    "document_fiscal_close_year_binding_receipt"
                ],
            )
            fragment["period_role_hint"] = (
                "CURRENT_PERIOD" if ordinal == 0 else "COMPARATIVE_PERIOD"
            )
            assignments.append(
                {
                    "assignment_kind": "ORDERED_MOVEMENT_NARRATIVE_TO_COMPONENT",
                    "date": period_date.isoformat(),
                    "document_fiscal_close_year_binding_receipt": canonical_clone_v1(
                        evidence["document_fiscal_close_year_binding_receipt"]
                    ),
                    "locator": canonical_clone_v1(fragment["locator"]),
                    "narrative_ordinal": evidence["narrative_ordinal"],
                    "period_role": fragment["period_role_hint"],
                    "source_exact": evidence["source_exact"],
                    "source_kind": evidence["source_kind"],
                }
            )
        return result, {
            **receipt,
            "assignments": assignments,
            "status": "ORDERED_TWO_DATE_CONTEXT_BOUND",
        }
    if len(exact_movement) != 1 or len(movement_evidence) > 1:
        return result, {**receipt, "status": "CONTEXT_DATE_AXIS_NOT_UNIQUE"}
    if (
        not _fragments_have_same_full_rank_topology_v1(result, compiled_specs=compiled_specs)
        or len({fragment["bound_unit"] for fragment in result}) != 1
    ):
        return result, {**receipt, "status": "SYMBOLIC_COMPARATIVE_PRECONDITIONS_FAILED"}
    current_date = date.fromisoformat(exact_movement[0]["date"])
    if result[0]["period"] is not None and result[0]["period"][0] != current_date:
        return result, {**receipt, "status": "CONFLICTING_TABLE_PERIOD_EVIDENCE"}
    if result[1]["period"] is not None and not (
        result[1]["period"][0] == current_date
        and result[1]["period_assignment_source_kind"] == "SELECTED_SECTION_CONTEXT"
    ):
        return result, {**receipt, "status": "UNEXPECTED_SECOND_TABLE_PERIOD_EVIDENCE"}
    result[0]["period"] = (current_date, exact_movement[0]["date_token"])
    result[0]["period_semantics_evidence"] = _period_semantics_evidence_v1(
        result[0]["period"],
        source_kind=exact_movement[0]["source_kind"],
        date_source_surfaces=[exact_movement[0]["source_exact"]],
        local_context_surfaces=[exact_movement[0]["source_exact"]],
        document_fiscal_close_year_binding_receipt=exact_movement[0][
            "document_fiscal_close_year_binding_receipt"
        ],
    )
    result[0]["period_role_hint"] = "CURRENT_PERIOD"
    result[1]["period"] = None
    result[1]["period_semantics_evidence"] = None
    result[1]["period_role_hint"] = "COMPARATIVE_PERIOD"
    assignments = [
        {
            "assignment_kind": "VISIBLE_CURRENT_CONTEXT_TO_FIRST_COMPONENT",
            "date": current_date.isoformat(),
            "document_fiscal_close_year_binding_receipt": canonical_clone_v1(
                exact_movement[0]["document_fiscal_close_year_binding_receipt"]
            ),
            "locator": canonical_clone_v1(result[0]["locator"]),
            "narrative_ordinal": exact_movement[0]["narrative_ordinal"],
            "period_role": "CURRENT_PERIOD",
            "source_exact": exact_movement[0]["source_exact"],
            "source_kind": exact_movement[0]["source_kind"],
        },
        {
            "assignment_kind": "SYMBOLIC_UNDATED_COMPARATIVE_SECOND_COMPONENT",
            "date": None,
            "document_fiscal_close_year_binding_receipt": None,
            "locator": canonical_clone_v1(result[1]["locator"]),
            "narrative_ordinal": None,
            "period_role": "COMPARATIVE_PERIOD",
            "source_exact": None,
            "source_kind": "ORDERED_ADJACENT_COMPONENT_TOPOLOGY",
        },
    ]
    return result, {
        **receipt,
        "assignments": assignments,
        "status": "CURRENT_PLUS_SYMBOLIC_COMPARATIVE_BOUND",
    }


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
        "document_id",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "table_id",
    }
    result = []
    for region in regions:
        if type(region) is not dict or set(region) != fields:
            raise _error("roll-forward component region locator is invalid")
        if (
            type(region["document_id"]) is not str
            or _DOCUMENT_ID.fullmatch(region["document_id"]) is None
            or type(region["source_logical_name"]) is not str
            or not region["source_logical_name"].strip()
            or type(region["source_sha256"]) is not str
            or _SOURCE_SHA256.fullmatch(region["source_sha256"]) is None
            or type(region["page_json_version_id"]) is not str
            or _PAGE_JSON_VERSION_ID.fullmatch(region["page_json_version_id"]) is None
            or type(region["physical_page"]) is not int
            or region["physical_page"] <= 0
            or type(region["section_id"]) is not str
            or re.fullmatch(r"s[1-9][0-9]*", region["section_id"]) is None
            or type(region["table_id"]) is not str
            or re.fullmatch(r"t[1-9][0-9]*", region["table_id"]) is None
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
    source_axis = {
        (
            item["document_id"],
            item["source_logical_name"],
            item["source_sha256"],
        )
        for item in result
    }
    if len(source_axis) != 1:
        raise _error("roll-forward component regions cross one immutable document source")
    version_by_page: dict[int, str] = {}
    for item in result:
        previous = version_by_page.setdefault(item["physical_page"], item["page_json_version_id"])
        if previous != item["page_json_version_id"]:
            raise _error("roll-forward component page selects multiple JSON versions")
    return result


def _ordered_page_version_axis(
    region_axis: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    seen: set[int] = set()
    for item in region_axis:
        if item["physical_page"] in seen:
            continue
        seen.add(item["physical_page"])
        result.append(
            {
                "page_json_version_id": item["page_json_version_id"],
                "physical_page": item["physical_page"],
            }
        )
    return result


def build_gemini_json_rollforward_region_query_receipt_v1(
    regions: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Bind one query result to one immutable source and exact ordered regions."""

    region_axis = _region_axis(regions)
    first = region_axis[0]
    material = {
        "authentication_kind": QUERY_RECEIPT_AUTHENTICATION_KIND,
        "document_id": first["document_id"],
        "exact_region_count": len(region_axis),
        "format_version": QUERY_RECEIPT_FORMAT_VERSION,
        "ordered_page_json_version_axis_sha256": canonical_json_sha256_v1(
            _ordered_page_version_axis(region_axis)
        ),
        "ordered_region_axis_sha256": canonical_json_sha256_v1(region_axis),
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
    }
    return {
        **material,
        "query_receipt_id": "gjfrqrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _validated_region_query_receipt_v1(
    value: Any, *, region_axis: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    expected = build_gemini_json_rollforward_region_query_receipt_v1(
        [canonical_clone_v1(item) for item in region_axis]
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("roll-forward query receipt does not authenticate exact regions")
    return canonical_clone_v1(expected)


def _validated_document_unit_context_evidence_v1(
    value: Any,
    *,
    document_id: str,
    source_logical_name: str,
    source_sha256: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    if value is None:
        return None
    fields = {
        "canonical_unit",
        "canonical_units",
        "distinct_page_count",
        "document_id",
        "document_ordinal",
        "evidence",
        "evidence_axis_sha256",
        "minimum_distinct_page_count",
        "rule",
        "source_logical_name",
        "source_sha256",
        "status",
    }
    evidence_fields = {
        "canonical_unit",
        "column_id",
        "currency",
        "magnitude_power10",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "selected_page_ordinal",
        "source_kind",
        "table_id",
        "text_exact",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("document_id") != document_id
        or value.get("source_logical_name") != source_logical_name
        or value.get("source_sha256") != source_sha256
        or type(value.get("document_ordinal")) is not int
        or value["document_ordinal"] <= 0
        or type(value.get("evidence")) is not list
        or value.get("minimum_distinct_page_count") != 2
        or value.get("rule")
        != (
            "SELECTED_PAGE_VERSION_ONLY_EXPLICIT_TABLE_UNIT_MAGNITUDE_AND_"
            "CURRENCY_TWO_PAGE_UNIQUE_CANONICAL_MONEY_UNIT_CONSENSUS"
        )
    ):
        raise _error("roll-forward document-unit context identity is invalid")
    binding_by_unit = {
        item["canonical_unit"]: item for item in compiled_specs["layout"]["unit_bindings"]
    }
    evidence = value["evidence"]
    expected_order = sorted(
        evidence,
        key=lambda item: (
            item.get("selected_page_ordinal", 0),
            int(item.get("section_id", "s0")[1:]),
            int(item.get("table_id", "t0")[1:]),
            item.get("source_kind", ""),
            item.get("column_id") or "",
            item.get("text_exact", ""),
            item.get("canonical_unit", ""),
        ),
    )
    if expected_order != evidence or len(
        {canonical_json_sha256_v1(item) for item in evidence}
    ) != len(evidence):
        raise _error("roll-forward document-unit evidence axis is unordered")
    for item in evidence:
        binding = binding_by_unit.get(item.get("canonical_unit"))
        if (
            type(item) is not dict
            or set(item) != evidence_fields
            or binding is None
            or not binding["document_consensus_eligible"]
            or item.get("currency") != binding["currency"]
            or item.get("magnitude_power10") != binding["magnitude_power10"]
            or type(item.get("page_json_version_id")) is not str
            or _PAGE_JSON_VERSION_ID.fullmatch(item["page_json_version_id"]) is None
            or type(item.get("physical_page")) is not int
            or item["physical_page"] <= 0
            or type(item.get("section_id")) is not str
            or not re.fullmatch(r"s[1-9][0-9]*", item["section_id"])
            or type(item.get("table_id")) is not str
            or not re.fullmatch(r"t[1-9][0-9]*", item["table_id"])
            or item.get("source_kind") != "TABLE_UNIT"
            or item.get("column_id") is not None
            or type(item.get("text_exact")) is not str
            or not item["text_exact"]
            or item["canonical_unit"]
            not in _canonical_money_units_from_surface_v1(
                item["text_exact"],
                compiled_specs=compiled_specs,
                document_consensus_only=True,
            )
        ):
            raise _error("roll-forward document-unit evidence is invalid")
    canonical_units = sorted({item["canonical_unit"] for item in evidence})
    distinct_page_count = len(
        {(item["physical_page"], item["page_json_version_id"]) for item in evidence}
    )
    status = (
        "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
        if len(canonical_units) == 1 and distinct_page_count >= 2
        else "CONFLICTING_AUTHENTICATED_DOCUMENT_MONEY_UNIT_EVIDENCE"
        if len(canonical_units) > 1
        else "INSUFFICIENT_AUTHENTICATED_DOCUMENT_MONEY_UNIT_EVIDENCE"
    )
    if (
        value.get("canonical_units") != canonical_units
        or value.get("canonical_unit")
        != (canonical_units[0] if status.startswith("UNIQUE_") else None)
        or value.get("distinct_page_count") != distinct_page_count
        or value.get("status") != status
        or value.get("evidence_axis_sha256") != canonical_json_sha256_v1(evidence)
    ):
        raise _error("roll-forward document-unit consensus receipt drifted")
    return canonical_clone_v1(value)


def _validated_document_fiscal_close_context_evidence_v1(
    value: Any,
    *,
    document_id: str,
    source_logical_name: str,
    source_sha256: str,
) -> dict[str, Any] | None:
    """Validate exact-year fiscal-close carriers projected from selected JSON versions."""

    if value is None:
        return None
    fields = {
        "document_id",
        "document_ordinal",
        "rule",
        "source_logical_name",
        "source_sha256",
        "year_context_axis_sha256",
        "year_contexts",
    }
    year_fields = {
        "day",
        "distinct_page_count",
        "evidence",
        "evidence_axis_sha256",
        "minimum_distinct_page_count",
        "month",
        "month_day_axis",
        "status",
        "year",
    }
    evidence_fields = {
        "column_id",
        "date",
        "day",
        "month",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "selected_page_ordinal",
        "source_kind",
        "table_id",
        "text_exact",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("document_id") != document_id
        or value.get("source_logical_name") != source_logical_name
        or value.get("source_sha256") != source_sha256
        or type(value.get("document_ordinal")) is not int
        or value["document_ordinal"] <= 0
        or value.get("rule")
        != (
            "SELECTED_PAGE_VERSION_ONLY_ANNUAL_REPORTING_TITLE_OR_BALANCE_"
            "SHEET_COMPARATIVE_DATE_EXACT_YEAR_TWO_PAGE_UNIQUE_FISCAL_"
            "CLOSE_MONTH_DAY_CONSENSUS"
        )
        or type(value.get("year_contexts")) is not list
    ):
        raise _error("roll-forward document fiscal-close context identity is invalid")
    year_contexts = value["year_contexts"]
    if any(
        type(item) is not dict or type(item.get("year")) is not int for item in year_contexts
    ) or [item["year"] for item in year_contexts] != sorted(
        {item["year"] for item in year_contexts}
    ):
        raise _error("roll-forward document fiscal-close year axis is unordered")

    def annual_reporting_surface(surface: str) -> bool:
        folded = _normalized(surface)
        annual = bool(
            ("nam tai chinh" in folded and "ket thuc" in folded)
            or re.search(r"\bnam (?:duoc )?ket thuc\b", folded)
            or "financial year ended" in folded
            or "year ended" in folded
        )
        reporting = any(
            marker in folded
            for marker in ("bao cao tai chinh", "thuyet minh bao cao", "financial statement")
        )
        return annual and (reporting or "nam tai chinh" in folded)

    def annual_reporting_dates(surface: str) -> set[date]:
        folded = _normalized(surface)
        if not annual_reporting_surface(surface):
            return set()
        grammar = re.compile(
            r"(?:nam tai chinh|nam(?: duoc)?|financial year|year)\s+"
            r"(?:duoc\s+)?(?:ket thuc(?:\s+vao)?(?:\s+ngay)?|ended(?:\s+on)?)\s*$"
        )
        governed = set()
        for match in [*_DATE_DMY.finditer(folded), *_DATE_WORDS.finditer(folded)]:
            if grammar.search(folded[: match.start()]) is None:
                continue
            try:
                governed.add(date(int(match.group(3)), int(match.group(2)), int(match.group(1))))
            except ValueError:
                continue
        return governed

    for year_context in year_contexts:
        if (
            type(year_context) is not dict
            or set(year_context) != year_fields
            or type(year_context.get("year")) is not int
            or year_context["year"] < 1900
            or type(year_context.get("evidence")) is not list
            or year_context.get("minimum_distinct_page_count") != 2
            or type(year_context.get("month_day_axis")) is not list
        ):
            raise _error("roll-forward document fiscal-close year context is invalid")
        evidence = year_context["evidence"]
        expected_order = sorted(
            evidence,
            key=lambda item: (
                item.get("selected_page_ordinal", 0),
                int(item.get("section_id", "s0")[1:]),
                int(item.get("table_id", "t0")[1:]) if item.get("table_id") else 0,
                item.get("column_id") or "",
                item.get("source_kind", ""),
                item.get("date", ""),
                item.get("text_exact", ""),
            ),
        )
        if expected_order != evidence or len(
            {canonical_json_sha256_v1(item) for item in evidence}
        ) != len(evidence):
            raise _error("roll-forward document fiscal-close evidence axis is unordered")
        for item in evidence:
            if (
                type(item) is not dict
                or set(item) != evidence_fields
                or type(item.get("page_json_version_id")) is not str
                or _PAGE_JSON_VERSION_ID.fullmatch(item["page_json_version_id"]) is None
                or type(item.get("physical_page")) is not int
                or item["physical_page"] <= 0
                or type(item.get("section_id")) is not str
                or re.fullmatch(r"s[1-9][0-9]*", item["section_id"]) is None
                or type(item.get("selected_page_ordinal")) is not int
                or item["selected_page_ordinal"] <= 0
                or type(item.get("text_exact")) is not str
                or not item["text_exact"]
                or item.get("source_kind")
                not in {
                    "ANNUAL_REPORTING_SECTION_TITLE",
                    "BALANCE_SHEET_COMPARATIVE_DATE_COLUMN",
                }
            ):
                raise _error("roll-forward document fiscal-close evidence is invalid")
            try:
                parsed = date.fromisoformat(item["date"])
            except (KeyError, TypeError, ValueError) as exc:
                raise _error("roll-forward document fiscal-close date is invalid") from exc
            folded = _normalized(item["text_exact"])
            exact_full_dates = {
                token[0]
                for token in _date_tokens(item["text_exact"])
                if _DATE_DMY.search(folded) or _DATE_WORDS.search(folded)
            }
            if (
                parsed.year != year_context["year"]
                or item.get("month") != parsed.month
                or item.get("day") != parsed.day
                or parsed not in exact_full_dates
                or (
                    item["source_kind"] == "ANNUAL_REPORTING_SECTION_TITLE"
                    and (
                        item.get("table_id") is not None
                        or item.get("column_id") is not None
                        or parsed not in annual_reporting_dates(item["text_exact"])
                    )
                )
                or (
                    item["source_kind"] == "BALANCE_SHEET_COMPARATIVE_DATE_COLUMN"
                    and (
                        type(item.get("table_id")) is not str
                        or re.fullmatch(r"t[1-9][0-9]*", item["table_id"]) is None
                        or type(item.get("column_id")) is not str
                        or re.fullmatch(r"c[1-9][0-9]*", item["column_id"]) is None
                    )
                )
            ):
                raise _error("roll-forward document fiscal-close carrier is invalid")
        month_day_axis = sorted({(item["month"], item["day"]) for item in evidence})
        distinct_page_count = len(
            {(item["physical_page"], item["page_json_version_id"]) for item in evidence}
        )
        status = (
            "UNIQUE_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_CONSENSUS"
            if len(month_day_axis) == 1 and distinct_page_count >= 2
            else "CONFLICTING_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_EVIDENCE"
            if len(month_day_axis) > 1
            else "INSUFFICIENT_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_EVIDENCE"
        )
        if (
            year_context.get("month_day_axis")
            != [{"day": day, "month": month} for month, day in month_day_axis]
            or year_context.get("month")
            != (month_day_axis[0][0] if status.startswith("UNIQUE_") else None)
            or year_context.get("day")
            != (month_day_axis[0][1] if status.startswith("UNIQUE_") else None)
            or year_context.get("distinct_page_count") != distinct_page_count
            or year_context.get("status") != status
            or year_context.get("evidence_axis_sha256") != canonical_json_sha256_v1(evidence)
        ):
            raise _error("roll-forward document fiscal-close year receipt drifted")
    if value.get("year_context_axis_sha256") != canonical_json_sha256_v1(year_contexts):
        raise _error("roll-forward document fiscal-close context receipt drifted")
    return canonical_clone_v1(value)


def _document_fiscal_close_year_binding_receipt_v1(
    context: Mapping[str, Any] | None, *, year: int
) -> dict[str, Any] | None:
    if context is None:
        return None
    year_contexts = [item for item in context["year_contexts"] if item["year"] == year]
    if (
        len(year_contexts) != 1
        or year_contexts[0]["status"] != "UNIQUE_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_CONSENSUS"
    ):
        return None
    return {
        "context_rule": context["rule"],
        "document_id": context["document_id"],
        "document_ordinal": context["document_ordinal"],
        "rule": (
            "EXACT_BARE_PERIOD_YEAR_BOUND_TO_AUTHENTICATED_SELECTED_VERSION_"
            "DOCUMENT_FISCAL_CLOSE_YEAR_CONTEXT"
        ),
        "source_logical_name": context["source_logical_name"],
        "source_sha256": context["source_sha256"],
        "year_context": canonical_clone_v1(year_contexts[0]),
    }


def _endpoint_source_receipt(item: Mapping[str, Any]) -> dict[str, Any]:
    """Keep one endpoint's exact source and solved-cell provenance."""

    return canonical_clone_v1(
        {
            key: item[key]
            for key in (
                "assignment_kind",
                "block_ordinal",
                "bound_unit",
                "cell",
                "column_ordinal",
                "endpoint_date",
                "locator",
                "movement_role",
                "period_date",
                "period_semantics_evidence",
                "period_role",
                "row_hierarchy_path_exact",
                "row_id",
                "row_label_exact",
                "source_block_ordinal",
                "source_movement_role",
            )
        }
    )


def _two_period_endpoint_continuity_v1(
    role_vectors: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate chained or parallel two-period endpoint semantics per lane."""

    movement_by_kind = {
        item["kind"]: item["role"] for item in compiled_specs["layout"]["movement_roles"]
    }
    opening_role = movement_by_kind["OPENING"]
    closing_role = movement_by_kind["CLOSING"]
    by_key: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for vector in role_vectors:
        by_key.setdefault(
            (vector["period_role"], vector["lane_role"], vector["movement_role"]), []
        ).append(vector)
    lanes = sorted({vector["lane_role"] for vector in role_vectors})
    receipts: list[dict[str, Any]] = []
    reasons: list[str] = []
    for lane_role in lanes:
        keys = (
            ("COMPARATIVE_PERIOD", lane_role, opening_role),
            ("COMPARATIVE_PERIOD", lane_role, closing_role),
            ("CURRENT_PERIOD", lane_role, opening_role),
            ("CURRENT_PERIOD", lane_role, closing_role),
        )
        if any(len(by_key.get(key, [])) != 1 for key in keys):
            reasons.append(f"ROLLFORWARD_ENDPOINT_CONTINUITY_INCOMPLETE:{lane_role}")
            continue
        previous_opening, previous_closing, next_opening, following_closing = (
            by_key[key][0] for key in keys
        )
        try:
            previous_period = (
                date.fromisoformat(previous_closing["period_date"])
                if previous_closing["period_date"] is not None
                else None
            )
            following_period = date.fromisoformat(following_closing["period_date"])
        except (TypeError, ValueError):
            reasons.append(f"ROLLFORWARD_ENDPOINT_PERIOD_DATE_INVALID:{lane_role}")
            continue
        if following_period is None:
            reasons.append(f"ROLLFORWARD_ENDPOINT_PERIOD_DATE_INVALID:{lane_role}")
            continue
        valid = True
        endpoints = (
            (previous_opening, previous_closing, previous_period),
            (next_opening, following_closing, following_period),
        )
        parsed_endpoint_dates: list[tuple[date | None, date | None]] = []
        for opening, closing, period in endpoints:
            try:
                opening_date = (
                    date.fromisoformat(opening["endpoint_date"])
                    if opening["endpoint_date"] is not None
                    else None
                )
                closing_date = (
                    date.fromisoformat(closing["endpoint_date"])
                    if closing["endpoint_date"] is not None
                    else None
                )
            except (TypeError, ValueError):
                opening_date = closing_date = None
                valid = False
            parsed_endpoint_dates.append((opening_date, closing_date))
            if period is not None:
                if opening_date is not None and opening_date >= period:
                    valid = False
                if closing_date is not None and closing_date != period:
                    valid = False
            if (
                opening_date is not None
                and closing_date is not None
                and opening_date >= closing_date
            ):
                valid = False
        (
            (previous_open_date, previous_close_date),
            (
                next_open_date,
                following_close_date,
            ),
        ) = parsed_endpoint_dates
        endpoint_date_alignment_receipt = None

        def aligned_one_year(previous: date | None, following: date | None) -> bool:
            return (
                previous is not None
                and following is not None
                and following.year == previous.year + 1
                and (following.month, following.day) == (previous.month, previous.day)
            )

        period_windows_aligned = previous_period is not None and aligned_one_year(
            previous_period, following_period
        )
        # A closing movement row is already bound to its exact period date.
        # When the row label itself omits a date, that authenticated period
        # assignment is the closing endpoint; no date is fabricated for an
        # opening row.
        effective_previous_close_date = previous_close_date or previous_period
        effective_following_close_date = following_close_date or following_period
        closing_endpoints_aligned = aligned_one_year(
            effective_previous_close_date,
            effective_following_close_date,
        )
        opening_endpoints_aligned = aligned_one_year(previous_open_date, next_open_date)

        def annual_or_fiscal_surface(value: Any) -> bool:
            folded = _normalized(value)
            return bool(
                folded
                and (
                    "nam tai chinh" in folded
                    or re.search(r"\bnam (?:duoc )?ket thuc\b", folded)
                    or "trong nam" in folded
                    or "dau nam" in folded
                    or "cuoi nam" in folded
                    or "financial year" in folded
                    or "year ended" in folded
                    or "during the year" in folded
                    or "beginning of the year" in folded
                    or "end of the year" in folded
                    or re.search(r"\bannual\b", folded)
                )
            )

        def valid_document_fiscal_close_year_binding(
            evidence: Mapping[str, Any], expected: date
        ) -> bool:
            receipt = evidence.get("document_fiscal_close_year_binding_receipt")
            if receipt is None:
                return False
            if (
                type(receipt) is not dict
                or set(receipt)
                != {
                    "context_rule",
                    "document_id",
                    "document_ordinal",
                    "rule",
                    "source_logical_name",
                    "source_sha256",
                    "year_context",
                }
                or receipt.get("rule")
                != (
                    "EXACT_BARE_PERIOD_YEAR_BOUND_TO_AUTHENTICATED_SELECTED_VERSION_"
                    "DOCUMENT_FISCAL_CLOSE_YEAR_CONTEXT"
                )
                or type(receipt.get("year_context")) is not dict
            ):
                return False
            year_context = receipt["year_context"]
            if (
                year_context.get("year") != expected.year
                or year_context.get("status")
                != "UNIQUE_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_CONSENSUS"
                or type(year_context.get("month")) is not int
                or type(year_context.get("day")) is not int
                or type(year_context.get("evidence")) is not list
                or not year_context["evidence"]
                or year_context.get("evidence_axis_sha256")
                != canonical_json_sha256_v1(year_context["evidence"])
                or year_context.get("distinct_page_count", 0) < 2
            ):
                return False
            try:
                if (
                    date(
                        expected.year,
                        year_context["month"],
                        year_context["day"],
                    )
                    != expected
                ):
                    return False
            except ValueError:
                return False
            observed_month_days = set()
            observed_pages = set()
            for item in year_context["evidence"]:
                if type(item) is not dict or type(item.get("text_exact")) is not str:
                    return False
                folded = _normalized(item["text_exact"])
                if not (_DATE_DMY.search(folded) or _DATE_WORDS.search(folded)):
                    return False
                try:
                    parsed = date.fromisoformat(item["date"])
                except (KeyError, TypeError, ValueError):
                    return False
                if parsed.year != expected.year or not any(
                    token[0] == parsed for token in _date_tokens(item["text_exact"])
                ):
                    return False
                observed_month_days.add((parsed.month, parsed.day))
                observed_pages.add((item.get("physical_page"), item.get("page_json_version_id")))
            return (
                observed_month_days == {(year_context["month"], year_context["day"])}
                and len(observed_pages) == year_context["distinct_page_count"]
                and len(observed_pages) >= 2
            )

        def exact_period_source_visible(item: Mapping[str, Any], expected: date) -> bool:
            evidence = item.get("period_semantics_evidence")
            if (
                type(evidence) is not dict
                or set(evidence)
                != {
                    "date_source_exact_axis",
                    "document_fiscal_close_year_binding_receipt",
                    "local_context_exact_axis",
                    "period_date",
                    "source_kind",
                }
                or evidence.get("period_date") != expected.isoformat()
                or type(evidence.get("date_source_exact_axis")) is not list
                or not evidence["date_source_exact_axis"]
                or type(evidence.get("local_context_exact_axis")) is not list
                or type(evidence.get("source_kind")) is not str
                or not evidence["source_kind"]
            ):
                return False
            document_year_bound = valid_document_fiscal_close_year_binding(evidence, expected)
            return all(
                type(source) is str
                and bool(source)
                and (
                    any(token[0] == expected for token in _date_tokens(source))
                    or (
                        document_year_bound
                        and not (
                            _DATE_DMY.search(_normalized(source))
                            or _DATE_WORDS.search(_normalized(source))
                        )
                        and any(token[0].year == expected.year for token in _date_tokens(source))
                    )
                )
                for source in evidence["date_source_exact_axis"]
            )

        def authoritative_period_source_visible(item: Mapping[str, Any], expected: date) -> bool:
            if not exact_period_source_visible(item, expected):
                return False
            evidence = item["period_semantics_evidence"]
            date_sources = evidence["date_source_exact_axis"]
            has_full_date = any(
                _DATE_DMY.search(_normalized(source)) or _DATE_WORDS.search(_normalized(source))
                for source in date_sources
            )
            return bool(
                has_full_date or valid_document_fiscal_close_year_binding(evidence, expected)
            )

        def explicit_row_role_visible(item: Mapping[str, Any], role: str) -> bool:
            hierarchy = item.get("row_hierarchy_path_exact")
            return (
                type(item.get("row_label_exact")) is str
                and type(hierarchy) is list
                and bool(hierarchy)
                and _matches_alias(
                    item["row_label_exact"],
                    compiled_specs["aliases_by_role"][role],
                )
            )

        def fiscal_year_end_semantics(
            opening: Mapping[str, Any],
            closing: Mapping[str, Any],
            period: date,
        ) -> dict[str, Any] | None:
            evidence = closing.get("period_semantics_evidence")
            if (
                not authoritative_period_source_visible(closing, period)
                or type(evidence) is not dict
            ):
                return None
            exact_surfaces = [
                *evidence["date_source_exact_axis"],
                *evidence["local_context_exact_axis"],
            ]
            matched_surfaces = []
            for surface in exact_surfaces:
                if annual_or_fiscal_surface(surface):
                    matched_surfaces.append(surface)
            if not matched_surfaces:
                return None
            return {
                "classification": "SOURCE_VISIBLE_ANNUAL_OR_FISCAL_YEAR_END",
                "matched_source_exact_axis": list(dict.fromkeys(matched_surfaces)),
                "period_date": period.isoformat(),
                "period_semantics_evidence": canonical_clone_v1(evidence),
            }

        def next_fiscal_anniversary(period: date) -> date:
            try:
                return period.replace(year=period.year + 1)
            except ValueError:
                # A 29-Feb close has a 28-Feb anniversary in a non-leap fiscal cycle.
                return date(period.year + 1, period.month, period.day - 1)

        previous_fiscal_semantics = (
            fiscal_year_end_semantics(previous_opening, previous_closing, previous_period)
            if previous_period is not None
            else None
        )
        fiscal_cycle_anniversary = (
            next_fiscal_anniversary(previous_period) if previous_period is not None else None
        )
        fiscal_boundary_context = (
            previous_period is not None
            and previous_fiscal_semantics is not None
            and fiscal_cycle_anniversary is not None
            and previous_period < following_period
            and following_period <= fiscal_cycle_anniversary
            and previous_close_date is None
            and next_open_date is None
            and exact_period_source_visible(following_closing, following_period)
            and explicit_row_role_visible(previous_opening, opening_role)
            and explicit_row_role_visible(previous_closing, closing_role)
            and explicit_row_role_visible(next_opening, opening_role)
            and explicit_row_role_visible(following_closing, closing_role)
        )

        shared_opening = next_opening["assignment_kind"] == "SHARED_PREVIOUS_CLOSING_AS_OPENING"
        previous_coefficient = previous_closing["cell"]["coefficient"]
        next_coefficient = next_opening["cell"]["coefficient"]
        chain_gap = (
            (next_open_date - previous_close_date).days
            if next_open_date is not None and previous_close_date is not None
            else None
        )
        if previous_period is None:
            continuity_kind = (
                "PARALLEL_SYMBOLIC_COMPARATIVE_WINDOW"
                if previous_closing["resolved_period"] == "COMPARATIVE_UNDATED"
                else None
            )
        elif shared_opening or chain_gap in {0, 1}:
            continuity_kind = "CHAINED_PRIOR_CLOSE_TO_CURRENT_OPEN"
        elif fiscal_boundary_context:
            continuity_kind = "CHAINED_FISCAL_BOUNDARY_CONTEXT_PRIOR_CLOSE_TO_CURRENT_OPEN"
        elif (
            period_windows_aligned
            and closing_endpoints_aligned
            and authoritative_period_source_visible(previous_closing, previous_period)
            and authoritative_period_source_visible(following_closing, following_period)
        ):
            continuity_kind = "PARALLEL_PERIOD_WINDOWS_NO_CROSS_VALUE_EQUALITY"
        else:
            continuity_kind = None
        valid = valid and continuity_kind is not None

        if (
            previous_coefficient is None
            or next_coefficient is None
            or previous_closing["bound_unit"] is None
            or previous_closing["bound_unit"] != next_opening["bound_unit"]
        ):
            valid = False
        if continuity_kind in {
            "CHAINED_PRIOR_CLOSE_TO_CURRENT_OPEN",
            "CHAINED_FISCAL_BOUNDARY_CONTEXT_PRIOR_CLOSE_TO_CURRENT_OPEN",
        }:
            if previous_coefficient != next_coefficient:
                valid = False
            if continuity_kind == "CHAINED_PRIOR_CLOSE_TO_CURRENT_OPEN":
                if previous_close_date is None or next_open_date is None:
                    valid = False
                if chain_gap not in {0, 1}:
                    valid = False
                if shared_opening and chain_gap != 0:
                    valid = False
        elif continuity_kind == "PARALLEL_PERIOD_WINDOWS_NO_CROSS_VALUE_EQUALITY":
            if not (
                period_windows_aligned
                and closing_endpoints_aligned
                and authoritative_period_source_visible(previous_closing, previous_period)
                and authoritative_period_source_visible(following_closing, following_period)
            ):
                valid = False
            elif not opening_endpoints_aligned:
                # Parallel disclosure windows need not start on aligned dates.
                # Preserve the source-visible mismatch as diagnostic evidence
                # only after the final relation is known to be parallel.
                endpoint_date_alignment_receipt = {
                    "derivation_kind": ("PARALLEL_PERIOD_OPENING_WINDOW_MISMATCH_SOURCE_VISIBLE"),
                    "following_opening": _endpoint_source_receipt(next_opening),
                    "previous_opening": _endpoint_source_receipt(previous_opening),
                }
        if shared_opening and (
            continuity_kind != "CHAINED_PRIOR_CLOSE_TO_CURRENT_OPEN"
            or next_opening["locator"] != previous_closing["locator"]
            or next_opening["row_id"] != previous_closing["row_id"]
            or next_opening["column_ordinal"] != previous_closing["column_ordinal"]
            or next_opening["source_movement_role"] != closing_role
            or next_opening["source_block_ordinal"] != previous_closing["block_ordinal"]
            or next_opening["cell"] != previous_closing["cell"]
        ):
            valid = False
        if not valid:
            reasons.append(f"ROLLFORWARD_ENDPOINT_CONTINUITY_INVALID:{lane_role}")
            continue
        boundary_semantics_receipt = (
            {
                "current_period_evidence": canonical_clone_v1(
                    following_closing["period_semantics_evidence"]
                ),
                "current_reporting_end": following_period.isoformat(),
                "fiscal_cycle_anniversary": fiscal_cycle_anniversary.isoformat(),
                "previous_fiscal_close": previous_period.isoformat(),
                "previous_fiscal_year_end_semantics": canonical_clone_v1(previous_fiscal_semantics),
                "rule": (
                    "SOURCE_VISIBLE_ANNUAL_OR_FISCAL_YEAR_END_TO_REPORTING_END_"
                    "WITHIN_IMMEDIATELY_FOLLOWING_FISCAL_CYCLE_AND_EXPLICIT_"
                    "OPEN_CLOSE_ROWS"
                ),
            }
            if continuity_kind == "CHAINED_FISCAL_BOUNDARY_CONTEXT_PRIOR_CLOSE_TO_CURRENT_OPEN"
            else None
        )
        receipts.append(
            {
                "boundary_semantics_receipt": boundary_semantics_receipt,
                "following_closing": _endpoint_source_receipt(following_closing),
                "following_period": following_period.isoformat(),
                "continuity_kind": continuity_kind,
                "endpoint_date_alignment_receipt": endpoint_date_alignment_receipt,
                "lane_role": lane_role,
                "next_opening": _endpoint_source_receipt(next_opening),
                "previous_closing": _endpoint_source_receipt(previous_closing),
                "previous_opening": _endpoint_source_receipt(previous_opening),
                "previous_period": (
                    previous_period.isoformat() if previous_period is not None else None
                ),
                "rule": (
                    "SAME_DOCUMENT_LANE_UNIT_EXACT_ENDPOINT_DIRECTION_CHAINED_OR_"
                    "PARALLEL_PERIOD_WINDOW_SEMANTICS"
                ),
            }
        )
    return receipts, reasons


def _bounded_population_reset_fence_v1(
    region_axis: Sequence[Mapping[str, Any]],
    *,
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    include_intervening_surfaces: bool,
) -> dict[str, Any]:
    """Scan selected components and only the structural interval between them.

    A containing section can hold unrelated schedules before or after the
    selected roll-forward.  Those sibling tables are not part of a one-table
    population interval.  Conversely, every table/section strictly between
    two selected components remains a reset fence, including all of its row
    labels and hierarchy paths.
    """

    first_page = region_axis[0]["physical_page"]
    last_page = region_axis[-1]["physical_page"]
    lower_section = int(region_axis[0]["section_id"][1:])
    upper_section = int(region_axis[-1]["section_id"][1:])
    selected_table_keys = {
        (
            item["physical_page"],
            item["page_json_version_id"],
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
        )
        for item in region_axis
    }
    aliases = sorted(
        {
            *compiled_specs["layout"]["population_policy"]["reset_aliases"],
            *compiled_specs["layout"]["population_policy"]["hard_negative_aliases"],
        }
    )
    hits: list[dict[str, Any]] = []
    checked_pages = []
    seen_pages: set[tuple[int, str]] = set()
    for locator in region_axis:
        key = (locator["physical_page"], locator["page_json_version_id"])
        if key in seen_pages:
            continue
        seen_pages.add(key)
        physical_page, version_id = key
        page_json = page_json_by_version[version_id]
        sections = page_json.get("sections")
        if type(sections) is not list:
            raise _error("roll-forward page section axis is invalid")
        selected_by_section: dict[int, list[int]] = {}
        for item in region_axis:
            if (
                item["physical_page"] == physical_page
                and item["page_json_version_id"] == version_id
            ):
                selected_by_section.setdefault(int(item["section_id"][1:]), []).append(
                    int(item["table_id"][1:])
                )
        if include_intervening_surfaces:
            start = lower_section if physical_page == first_page else 1
            stop = upper_section if physical_page == last_page else len(sections)
            section_ordinals = list(range(start, stop + 1))
        else:
            section_ordinals = sorted(selected_by_section)
            start = section_ordinals[0]
            stop = section_ordinals[-1]
        if not section_ordinals or not 1 <= start <= stop <= len(sections):
            raise _error("roll-forward reset-fence section interval is invalid")
        checked_section_table_intervals = []
        for section_ordinal in section_ordinals:
            section = sections[section_ordinal - 1]
            if not isinstance(section, Mapping):
                raise _error("roll-forward reset-fence section is invalid")
            narratives = section.get("narratives_exact")
            tables = section.get("tables")
            if type(narratives) is not list or type(tables) is not list:
                raise _error("roll-forward reset-fence section axes are invalid")
            if include_intervening_surfaces:
                is_first_boundary = physical_page == first_page and section_ordinal == lower_section
                is_last_boundary = physical_page == last_page and section_ordinal == upper_section
                first_table = int(region_axis[0]["table_id"][1:]) if is_first_boundary else 1
                last_table = (
                    int(region_axis[-1]["table_id"][1:]) if is_last_boundary else len(tables)
                )
                table_intervals = [(first_table, last_table)]
                if not 1 <= first_table <= last_table <= len(tables):
                    # A strictly intervening prose-only section still forms a
                    # reset fence even though it contributes no table surfaces.
                    if tables or is_first_boundary or is_last_boundary:
                        raise _error("roll-forward reset-fence table interval is invalid")
                    table_intervals = []
            else:
                table_intervals = [
                    (table_ordinal, table_ordinal)
                    for table_ordinal in sorted(selected_by_section[section_ordinal])
                ]
                if any(
                    not 1 <= first_table <= last_table <= len(tables)
                    for first_table, last_table in table_intervals
                ):
                    raise _error("roll-forward reset-fence table interval is invalid")
            checked_section_table_intervals.extend(
                {
                    "first_table_ordinal": first_table,
                    "last_table_ordinal": last_table,
                    "section_ordinal": section_ordinal,
                }
                for first_table, last_table in table_intervals
            )
            surfaces = [
                ("SECTION_TITLE", section.get("title_exact")),
                *(("SECTION_NARRATIVE", narrative) for narrative in narratives),
            ]
            for first_table, last_table in table_intervals:
                for table_ordinal in range(first_table, last_table + 1):
                    table = tables[table_ordinal - 1]
                    if not isinstance(table, Mapping):
                        raise _error("roll-forward reset-fence table is invalid")
                    surfaces.append(("TABLE_TITLE", table.get("title_exact")))
                    columns = table.get("columns")
                    rows = table.get("rows")
                    if type(columns) is not list or type(rows) is not list:
                        raise _error("roll-forward reset-fence table axes are invalid")
                    is_selected_table = (
                        physical_page,
                        version_id,
                        section_ordinal,
                        table_ordinal,
                    ) in selected_table_keys
                    lane_by_column = (
                        _projected_lane_columns_v1(
                            columns,
                            compiled_specs=compiled_specs,
                        )[0]
                        if is_selected_table
                        else []
                    )
                    project_selected_lanes = (
                        len({role for role in lane_by_column if role is not None})
                        >= compiled_specs["layout"]["minimum_required_lanes"]
                    )
                    for column_ordinal, column in enumerate(columns):
                        if not isinstance(column, Mapping):
                            raise _error("roll-forward reset-fence column is invalid")
                        header_path = column.get("header_path_exact")
                        if type(header_path) is not list:
                            raise _error("roll-forward reset-fence header path is invalid")
                        if project_selected_lanes and lane_by_column[column_ordinal] is None:
                            continue
                        surfaces.extend(("COLUMN_HEADER", value) for value in header_path)
                    for row in rows:
                        if not isinstance(row, Mapping):
                            raise _error("roll-forward reset-fence row is invalid")
                        hierarchy = row.get("hierarchy_path_exact")
                        if type(hierarchy) is not list:
                            raise _error("roll-forward reset-fence row hierarchy is invalid")
                        surfaces.append(("ROW_LABEL", row.get("label_exact")))
                        surfaces.extend(("ROW_HIERARCHY", value) for value in hierarchy)
            hits.extend(
                {
                    "page_json_version_id": version_id,
                    "physical_page": physical_page,
                    "section_ordinal": section_ordinal,
                    "source_kind": source_kind,
                    "text_exact": value,
                }
                for source_kind, value in surfaces
                if type(value) is str and _matches_alias(value, aliases)
            )
        checked_pages.append(
            {
                "first_section_ordinal": start,
                "last_section_ordinal": stop,
                "page_json_version_id": version_id,
                "physical_page": physical_page,
                "section_table_intervals": checked_section_table_intervals,
            }
        )
    return {
        "checked_page_intervals": checked_pages,
        "scope_kind": (
            "SELECTED_COMPONENTS_AND_STRICTLY_INTERVENING_SURFACES"
            if include_intervening_surfaces
            else "INDEPENDENT_LOCAL_OWNER_SELECTED_COMPONENTS_ONLY"
        ),
        "reset_hits": hits,
        "status": "RESET_FENCE_CLEAR" if not hits else "RESET_FENCE_VIOLATED",
    }


def evaluate_gemini_json_rollforward_family_cluster_v1(
    *,
    regions: Sequence[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    document_fiscal_close_context_evidence: Mapping[str, Any] | None = None,
    document_unit_context_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one ordered one/two-table two-period roll-forward cluster."""

    region_axis = _region_axis(regions)
    checked_query_receipt = _validated_region_query_receipt_v1(
        query_receipt,
        region_axis=region_axis,
    )
    first_region = region_axis[0]
    checked_document_unit_context = _validated_document_unit_context_evidence_v1(
        document_unit_context_evidence,
        document_id=first_region["document_id"],
        source_logical_name=first_region["source_logical_name"],
        source_sha256=first_region["source_sha256"],
        compiled_specs=compiled_specs,
    )
    checked_document_fiscal_close_context = _validated_document_fiscal_close_context_evidence_v1(
        document_fiscal_close_context_evidence,
        document_id=first_region["document_id"],
        source_logical_name=first_region["source_logical_name"],
        source_sha256=first_region["source_sha256"],
    )
    fragments = []
    period_column_records = []
    component_classifications = []
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
        try:
            classification = classify_gemini_json_rollforward_table_v1(
                section=section,
                table=table,
                compiled_specs=compiled_specs,
            )
            component_classifications.append(
                {
                    "bound_unit": _bound_unit(table, compiled_specs=compiled_specs),
                    **canonical_clone_v1(classification),
                    "locator": canonical_clone_v1(locator),
                }
            )
            if (
                classification["context_reset_visible"]
                or classification["structural_hard_negative_visible"]
            ):
                reasons.append("ROLLFORWARD_LOCAL_POPULATION_RESET_OR_HARD_NEGATIVE")
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
    fragments, period_assignment_receipt = _resolve_ordered_period_components_v1(
        fragments,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        document_fiscal_close_context_evidence=(checked_document_fiscal_close_context),
    )
    for fragment in fragments:
        period = fragment.get("period")
        evidence = fragment.get("period_semantics_evidence")
        if period is None or type(evidence) is not dict:
            continue
        date_sources = evidence.get("date_source_exact_axis")
        if type(date_sources) is not list:
            continue
        has_full_date = any(
            type(source) is str
            and (_DATE_DMY.search(_normalized(source)) or _DATE_WORDS.search(_normalized(source)))
            for source in date_sources
        )
        if has_full_date:
            continue
        year_binding = _document_fiscal_close_year_binding_receipt_v1(
            checked_document_fiscal_close_context,
            year=period[0].year,
        )
        if year_binding is None:
            continue
        year_context = year_binding["year_context"]
        try:
            bound_period = date(period[0].year, year_context["month"], year_context["day"])
        except (TypeError, ValueError):
            continue
        fragment["period"] = (bound_period, period[1])
        evidence["period_date"] = bound_period.isoformat()
        evidence["document_fiscal_close_year_binding_receipt"] = year_binding
    aggregate_population_axis = []
    for fragment in fragments:
        receipt = fragment["lane_population_assignment_receipt"]
        if receipt is None:
            continue
        decision_by_lane = {item["lane_role"]: item for item in receipt["decisions"]}
        for lane_role in sorted(
            {role for role in receipt["raw_lane_roles_by_column"] if role is not None}
        ):
            if receipt["raw_lane_roles_by_column"].count(lane_role) < 2:
                continue
            decision = decision_by_lane.get(lane_role)
            aggregate_population_axis.append(
                {
                    "aggregate_identity_normalized": (
                        decision["aggregate_identity_normalized"] if decision else None
                    ),
                    "block_ordinal": fragment["block_ordinal"],
                    "lane_role": lane_role,
                    "locator": canonical_clone_v1(fragment["locator"]),
                    "status": "UNIQUE_EXACT_HORIZONTAL_AGGREGATE" if decision else "UNRESOLVED",
                }
            )
    for lane_role in sorted({item["lane_role"] for item in aggregate_population_axis}):
        identities = {
            item["aggregate_identity_normalized"]
            for item in aggregate_population_axis
            if item["lane_role"] == lane_role and item["aggregate_identity_normalized"] is not None
        }
        if len(identities) > 1:
            reasons.append(f"ROLLFORWARD_AGGREGATE_POPULATION_MISMATCH:{lane_role}")
    owner_components = [item for item in component_classifications if item["local_owner_visible"]]
    continuation_components = [
        item for item in component_classifications if not item["local_owner_visible"]
    ]
    if not owner_components:
        reasons.append("ROLLFORWARD_LOCAL_POPULATION_OWNER_NOT_VISIBLE")

    def locator_order(item: Mapping[str, Any]) -> tuple[int, int, int]:
        return (
            item["locator"]["physical_page"],
            int(item["locator"]["section_id"][1:]),
            int(item["locator"]["table_id"][1:]),
        )

    unbound_continuations = [
        item
        for item in continuation_components
        if not any(locator_order(owner) < locator_order(item) for owner in owner_components)
    ]
    if unbound_continuations:
        reasons.append("ROLLFORWARD_BOUNDED_OWNER_CONTINUATION_DIRECTION_INVALID")
    if any(not item["continuation_evidence"] for item in continuation_components):
        reasons.append("ROLLFORWARD_EXPLICIT_CONTINUATION_EVIDENCE_NOT_VISIBLE")
    reset_fence_receipt = _bounded_population_reset_fence_v1(
        region_axis,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        include_intervening_surfaces=bool(continuation_components),
    )
    if reset_fence_receipt["reset_hits"]:
        reasons.append("ROLLFORWARD_SELECTED_INTERVAL_POPULATION_RESET_OR_HARD_NEGATIVE_VISIBLE")
        if continuation_components:
            reasons.append("ROLLFORWARD_BOUNDED_OWNER_CONTINUATION_RESET_FENCE_VIOLATED")
    population_receipt = {
        "binding_kind": (
            "ALL_COMPONENTS_EXPLICIT_LOCAL_OWNER"
            if owner_components and not continuation_components
            else "BOUNDED_SELECTED_COMPONENT_OWNER_CONTINUATION"
            if owner_components
            else "UNRESOLVED_NO_LOCAL_OWNER"
        ),
        "continuation_component_locators": [item["locator"] for item in continuation_components],
        "continuation_evidence_receipts": [
            {
                "evidence": item["continuation_evidence"],
                "locator": item["locator"],
            }
            for item in continuation_components
        ],
        "max_physical_page_span": (
            region_axis[-1]["physical_page"] - region_axis[0]["physical_page"]
        ),
        "owner_component_locators": [item["locator"] for item in owner_components],
        "reset_fence_receipt": reset_fence_receipt,
        "reset_or_hard_negative_visible": bool(reset_fence_receipt["reset_hits"])
        or any(
            item["context_reset_visible"] or item["structural_hard_negative_visible"]
            for item in component_classifications
        ),
        "rule": (
            "AT_LEAST_ONE_SELECTED_COMPONENT_LOCAL_OWNER_OTHER_COMPONENTS_ONLY_"
            "WITHIN_ORDERED_ONE_PAGE_RESET_FENCED_CLUSTER"
        ),
        "unbound_continuation_locators": [item["locator"] for item in unbound_continuations],
    }
    local_unit_axis = [
        {
            "block_ordinal": fragment["block_ordinal"],
            "bound_unit": fragment["bound_unit"],
            "locator": canonical_clone_v1(fragment["locator"]),
        }
        for fragment in fragments
    ]
    local_units = [fragment["bound_unit"] for fragment in fragments]
    if local_units and all(unit is None for unit in local_units):
        if (
            checked_document_unit_context is not None
            and checked_document_unit_context["status"]
            == "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
        ):
            for fragment in fragments:
                fragment["bound_unit"] = checked_document_unit_context["canonical_unit"]
            unit_assignment_kind = "AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS_INHERITED"
        else:
            unit_assignment_kind = "UNRESOLVED_NO_LOCAL_OR_DOCUMENT_UNIT_CONSENSUS"
            reasons.append("ROLLFORWARD_MONEY_UNIT_NOT_VISIBLE")
    elif local_units and all(unit is not None for unit in local_units):
        unit_assignment_kind = "ALL_COMPONENTS_EXPLICIT_LOCAL_CANONICAL_UNIT"
    else:
        unit_assignment_kind = "MIXED_LOCAL_VISIBLE_AND_MISSING_UNIT_NOT_INHERITED"
        reasons.append("ROLLFORWARD_MONEY_UNIT_NOT_VISIBLE")
    bound_units = [fragment["bound_unit"] for fragment in fragments]
    if not bound_units:
        reasons.append("ROLLFORWARD_MONEY_UNIT_NOT_VISIBLE")
    if len({unit for unit in bound_units if unit is not None}) > 1:
        reasons.append("ROLLFORWARD_MONEY_UNIT_MISMATCH_ACROSS_PERIODS_OR_COMPONENTS")
    # Document-wide evidence is authority-bearing only when it actually closes
    # a locally unit-less component set.  Keeping irrelevant context out of a
    # locally explicit candidate also makes replay invariant to unrelated unit
    # surfaces elsewhere in the same selected document frontier.
    receipt_document_unit_context = (
        checked_document_unit_context
        if unit_assignment_kind
        in {
            "AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS_INHERITED",
            "UNRESOLVED_NO_LOCAL_OR_DOCUMENT_UNIT_CONSENSUS",
        }
        else None
    )
    unit_provenance_receipt = {
        "assignment_kind": unit_assignment_kind,
        "document_unit_context_evidence": receipt_document_unit_context,
        "local_unit_axis": local_unit_axis,
        "resolved_canonical_unit": (
            next(iter({unit for unit in bound_units if unit is not None}))
            if len({unit for unit in bound_units if unit is not None}) == 1
            else None
        ),
        "rule": (
            "LOCAL_CANONICAL_UNIT_OR_SELECTED_VERSION_DOCUMENT_TWO_PAGE_"
            "UNIQUE_MAGNITUDE_CURRENCY_CONSENSUS_NO_SCALE_CONVERSION"
        ),
    }
    period_roles = ("CURRENT_PERIOD", "COMPARATIVE_PERIOD")
    hinted_roles = [fragment["period_role_hint"] for fragment in fragments]
    hint_axis_resolved = (
        bool(fragments)
        and all(role in period_roles for role in hinted_roles)
        and set(hinted_roles) == set(period_roles)
    )
    dated = [fragment for fragment in fragments if fragment["period"] is not None]
    dates = sorted({fragment["period"][0] for fragment in dated}, reverse=True)
    date_axis_resolved = len(dates) == 2 and len(dated) == len(fragments)
    if not hint_axis_resolved and not date_axis_resolved:
        reasons.append("ROLLFORWARD_EXACT_TWO_PERIOD_AXIS_NOT_RESOLVED")
    period_role_by_date = {
        period: "CURRENT_PERIOD" if ordinal == 0 else "COMPARATIVE_PERIOD"
        for ordinal, period in enumerate(dates)
    }
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    duplicate_source_ambiguities = []
    for fragment in fragments:
        if hint_axis_resolved:
            period_role = fragment["period_role_hint"]
        else:
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
                "period_date": (
                    fragment["period"][0].isoformat() if fragment["period"] is not None else None
                ),
                "period_semantics_evidence": canonical_clone_v1(
                    fragment["period_semantics_evidence"]
                ),
                "period_role": period_role,
                "resolved_period": (
                    fragment["period"][1]
                    if fragment["period"] is not None
                    else "COMPARATIVE_UNDATED"
                ),
            }
            previous = merged.get(key)
            if previous is None:
                merged[key] = record
                continue
            same_cell = (
                previous["cell"] == record["cell"]
                and previous["resolved_period"] == record["resolved_period"]
                and previous["bound_unit"] == record["bound_unit"]
            )
            reasons.append("ROLLFORWARD_DUPLICATE_ROLE_PERIOD_LANE_AMBIGUOUS:" + ":".join(key))
            duplicate_source_ambiguities.append(
                {
                    "corroborated_key": list(key),
                    "disposition": (
                        "IDENTICAL_DUPLICATE_SOURCE_AMBIGUOUS"
                        if same_cell
                        else "CONFLICTING_DUPLICATE_SOURCE_AMBIGUOUS"
                    ),
                    "first_column_ordinal": previous["column_ordinal"],
                    "first_locator": previous["locator"],
                    "second_column_ordinal": record["column_ordinal"],
                    "second_locator": record["locator"],
                }
            )

    required_lanes = {
        item["role"] for item in compiled_specs["layout"]["lane_roles"] if not item["optional"]
    }
    movement_specs = compiled_specs["layout"]["movement_roles"]
    required_movements = {item["role"] for item in movement_specs if item["required"]}
    lanes_by_period = {
        period_role: {lane for period, lane, _movement in merged if period == period_role}
        for period_role in period_roles
    }
    for period_role in period_roles:
        if required_lanes <= lanes_by_period[period_role]:
            continue
        reasons.append(
            "ROLLFORWARD_REQUIRED_CURRENT_LANES_INCOMPLETE"
            if period_role == "CURRENT_PERIOD"
            else "ROLLFORWARD_REQUIRED_COMPARATIVE_LANES_INCOMPLETE"
        )
    if lanes_by_period["CURRENT_PERIOD"] != lanes_by_period["COMPARATIVE_PERIOD"]:
        reasons.append("ROLLFORWARD_LANE_POPULATION_MISMATCH_ACROSS_PERIODS")
    equations = []
    role_vectors = []
    potential_mappings = []
    unresolved_frontiers = []
    bindings = compiled_specs["schema"]["bindings"]
    for period_role in period_roles:
        for lane_role in sorted(lanes_by_period[period_role]):
            cells = {
                movement: canonical_clone_v1(record["cell"])
                for (period, lane, movement), record in merged.items()
                if period == period_role and lane == lane_role
            }
            scope = lane_role if period_role == "CURRENT_PERIOD" else f"{period_role}:{lane_role}"
            solution: dict[str, Any] | None = None
            if not required_movements <= set(cells):
                reasons.append(f"ROLLFORWARD_REQUIRED_MOVEMENTS_INCOMPLETE:{scope}")
            else:
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
                equation = {
                    "equation_rank": 1,
                    "inferred_coefficient": solution.get("inferred_coefficient"),
                    "inferred_role": solution.get("inferred_role"),
                    "lane_role": lane_role,
                    "period_role": period_role,
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
                equations.append(equation)
                if solution["status"] not in {"EXACT", "EXACT_ONE_UNKNOWN_INFERRED"}:
                    reason = f"ROLLFORWARD_LANE_EQUATION_{solution['status']}:{scope}"
                    reasons.append(reason)
                    unresolved_frontiers.append(
                        {
                            "lane_role": lane_role,
                            "period_role": period_role,
                            "reason": reason,
                            "unknown_roles": solution.get("unknown_roles", []),
                            "source_records": [
                                {
                                    "locator": record["locator"],
                                    "movement_role": movement,
                                    "row_id": record["row_id"],
                                }
                                for (period, lane, movement), record in sorted(merged.items())
                                if period == period_role and lane == lane_role
                            ],
                        }
                    )
            for movement_role, cell in sorted(cells.items()):
                record = merged[(period_role, lane_role, movement_role)]
                vector = {
                    "assignment_kind": record["assignment_kind"],
                    "block_ordinal": record["block_ordinal"],
                    "bound_unit": record["bound_unit"],
                    "cell": cell,
                    "column_ordinal": record["column_ordinal"],
                    "endpoint_date": record["endpoint_date"],
                    "lane_role": lane_role,
                    "locator": record["locator"],
                    "movement_role": movement_role,
                    "period_date": record["period_date"],
                    "period_role": period_role,
                    "period_semantics_evidence": record["period_semantics_evidence"],
                    "resolved_period": record["resolved_period"],
                    "row_hierarchy_path_exact": record["row_hierarchy_path_exact"],
                    "row_id": record["row_id"],
                    "row_label_exact": record["row_label_exact"],
                    "source_block_ordinal": record["source_block_ordinal"],
                    "source_movement_role": record["source_movement_role"],
                }
                role_vectors.append(vector)
                if period_role != "CURRENT_PERIOD":
                    continue
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
    endpoint_continuity_receipts, endpoint_reasons = _two_period_endpoint_continuity_v1(
        role_vectors,
        compiled_specs=compiled_specs,
    )
    reasons.extend(endpoint_reasons)
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
            "bound_unit": (
                next(iter({unit for unit in bound_units if unit is not None}))
                if len({unit for unit in bound_units if unit is not None}) == 1
                else None
            ),
            "component_classifications": component_classifications,
            "component_region_axis_sha256": canonical_json_sha256_v1(region_axis),
            "duplicate_source_ambiguities": duplicate_source_ambiguities,
            "endpoint_continuity_receipts": endpoint_continuity_receipts,
            "equations": equations,
            "lane_assignment_receipts": lane_assignment_receipts,
            "lane_population_assignment_receipts": [
                {
                    "block_ordinal": fragment["block_ordinal"],
                    "locator": canonical_clone_v1(fragment["locator"]),
                    "receipt": canonical_clone_v1(fragment["lane_population_assignment_receipt"]),
                }
                for fragment in fragments
                if fragment["lane_population_assignment_receipt"] is not None
            ],
            "lane_population_continuity_receipt": {
                "aggregate_population_axis": aggregate_population_axis,
                "rule": "SAME_EXACT_DECLARED_AGGREGATE_IDENTITY_ACROSS_PERIOD_COMPONENTS",
            },
            "orientation": orientation,
            "period_assignment_receipt": period_assignment_receipt,
            "period_lane_populations": {
                period_role: sorted(lanes_by_period[period_role]) for period_role in period_roles
            },
            "population_receipt": population_receipt,
            "potential_mapping_count": len(potential_mappings),
            "query_receipt": checked_query_receipt,
            "role_vectors": role_vectors,
            "rule": "EXACT_SIGNED_ROLLFORWARD_ONE_UNKNOWN_FULL_RANK",
            "unresolved_frontiers": unresolved_frontiers,
            "unit_provenance_receipt": unit_provenance_receipt,
        },
        "component_regions": region_axis,
        "component_table_refs": [
            {"section_id": item["section_id"], "table_id": item["table_id"]}
            for item in region_axis
            if item["page_json_version_id"] == first["page_json_version_id"]
        ],
        "document_id": first["document_id"],
        "family_id": compiled_specs["topology"]["family_id"],
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": UNRESOLVED if reasons else READY,
        "table_id": first["table_id"],
    }
    return {
        "candidate_id": "gjfafcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_rollforward_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Sequence[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    document_fiscal_close_context_evidence: Mapping[str, Any] | None = None,
    document_unit_context_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild and exact-compare one candidate, including every provenance receipt."""

    rebuilt = evaluate_gemini_json_rollforward_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
        document_fiscal_close_context_evidence=(document_fiscal_close_context_evidence),
        document_unit_context_evidence=document_unit_context_evidence,
    )
    if type(value) is not dict or not same_typed_json_v1(value, rebuilt):
        raise _error("roll-forward family candidate does not replay exactly")
    return rebuilt
