"""Persistable, replay-authenticated Semantic Local Accounting Graph v2.

This graph is downstream of the immutable V2 projection and the authenticated
VietOCR Transformer page binding.  Acceptance is deliberately bounded to the
exact family-spec collision scope supplied by the caller.  It is not a global
family-registry claim, a same-population claim, or schema/canonical/export
authority.
"""

from __future__ import annotations

import re
from collections import Counter, deque
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    FamilySpecV1,
    local_accounting_family_spec_sha256_v1,
    parse_local_accounting_period_v1,
    parse_local_accounting_unit_v1,
)
from bctc_ai.source_structure.semantic_local_accounting_observation_v2 import (
    build_semantic_local_accounting_observation_candidate_v2,
)
from bctc_ai.source_structure.vietnamese_semantic_surface_v1 import (
    compile_vietnamese_family_alias_index_v1,
    propose_vietnamese_semantic_surface_v1,
)

__all__ = [
    "CLAIM_BOUNDARY",
    "FORMAT_VERSION",
    "SAFETY",
    "SemanticLocalAccountingGraphV2Error",
    "build_semantic_local_accounting_graph_v2",
    "validate_semantic_local_accounting_graph_replay_v2",
]


FORMAT_VERSION = "BANK_CORPUS_SEMANTIC_LOCAL_ACCOUNTING_GRAPH_V2"
CLAIM_BOUNDARY = (
    "SOURCE_BOUND_SEMANTIC_LOCAL_ACCOUNTING_GRAPH_ACCEPTED_WITHIN_EXACT_SUPPLIED_"
    "FAMILY_COLLISION_SCOPE_ONLY_NO_REGISTRY_OR_PAGE_FAMILY_EXHAUSTIVENESS_"
    "INTERNAL_ADDITIVE_CLOSURE_ONLY_NO_SAME_POPULATION_CANONICAL_SCHEMA_OR_EXPORT_AUTHORITY"
)
ACCEPTED_STATUS = "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE"
UNRESOLVED_STATUS = "UNRESOLVED"
_SAFETY_POLICY_ITEMS: tuple[tuple[str, bool], ...] = (
    ("downstream_overlay_only", True),
    ("reader_v3_mutated", False),
    ("ppocr_transcript_used_for_semantic_identity", False),
    ("ppocr_used_for_date_and_numeric_text_only", True),
    ("vietocr_transformer_used_for_label_and_unit_identity", True),
    ("vietocr_used_for_numeric_value", False),
    ("supplied_family_collision_scope_only", True),
    ("globally_collision_free_claimed", False),
    ("family_registry_exhaustiveness_claimed", False),
    ("page_family_exhaustiveness_claimed", False),
    ("target_family_evaluated_only", True),
    ("non_target_supplied_families_used_for_collision_only", True),
    ("non_target_supplied_family_dispositions_claimed", False),
    ("internal_additive_closure_only", True),
    ("same_population_claimed", False),
    ("canonicalization_authority", False),
    ("schema_mapping_authority", False),
    ("export_authority", False),
    ("graph_v1_mutated", False),
)
SAFETY: Mapping[str, bool] = MappingProxyType(dict(_SAFETY_POLICY_ITEMS))


def _fixed_safety_payload() -> dict[str, bool]:
    """Return policy bytes without consulting the exported read-only view."""

    return dict(_SAFETY_POLICY_ITEMS)


_TOP_FIELDS = {
    "format_version",
    "claim_boundary",
    "graph_id",
    "status",
    "source_local_page_id",
    "source_projection_sha256",
    "semantic_page_binding_sha256",
    "observation_candidate_sha256",
    "family_id",
    "family_spec_sha256",
    "supplied_family_collision_scope_spec_sha256_by_id",
    "supplied_family_evaluation_partition",
    "acceptance_scope",
    "nodes",
    "edges",
    "arithmetic",
    "unresolved_reasons",
    "metrics",
    "safety",
}
_NODE_FIELDS = {"node_id", "kind", "status", "source_ref", "attributes"}
_SOURCE_REF_FIELDS = {
    "source_local_page_id",
    "source_projection_sha256",
    "canonical_bbox_mpt",
    "source_atom_ids",
}
_EDGE_FIELDS = {
    "edge_id",
    "kind",
    "from_node_id",
    "to_node_id",
    "evidence_node_ids",
}
_METRIC_FIELDS = {
    "accepted_region_count",
    "node_count",
    "edge_count",
    "evidence_node_count",
    "orphan_node_count",
    "orphan_evidence_count",
    "invalid_edge_count",
    "disconnected_node_count",
    "accepted_counts",
}
_NODE_KINDS = {
    "TABLE",
    "ACCOUNTING_ROLE",
    "AXIS",
    "UNIT_SCOPE",
    "LOGICAL_ROW",
    "VALUE_POSITION",
    "EVIDENCE",
}
_EDGE_KINDS = {
    "CONTAINS",
    "OWNS",
    "PARENT_OF",
    "NEXT_SIBLING",
    "ALIGNED_TO_AXIS",
    "SCOPED_BY_UNIT",
    "TOTAL_OF",
    "SUPPORTED_BY",
}
_STRUCTURAL_ATTRIBUTE_FIELDS = {
    "TABLE": {
        "family_id",
        "family_spec_sha256",
        "acceptance_scope",
        "internal_additive_closure_only",
        "same_population_claimed",
    },
    "ACCOUNTING_ROLE": {"accounting_role", "family_id"},
    "AXIS": {"axis_index", "period"},
    "UNIT_SCOPE": {"axis_index", "unit"},
    "LOGICAL_ROW": {"row_role", "ordinal", "total_resolution"},
    "VALUE_POSITION": {
        "row_role",
        "row_ordinal",
        "axis_index",
        "raw_text",
        "normalized_decimal",
        "state",
    },
    "EVIDENCE": {
        "evidence_role",
        "raw_text_utf8",
        "text_source",
        "semantic_identity_authority",
        "unit_identity_authority",
        "numeric_authority",
        "period_authority",
        "geometry_authority",
        "source_line_index",
    },
}
_SEMANTIC_EVIDENCE_ROLES = {"OWNER_LABEL", "BRANCH_LABEL", "ROW_LABEL", "UNIT_LABEL"}
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class SemanticLocalAccountingGraphV2Error(ValueError):
    """The closed graph, authority split, or exact replay binding drifted."""


def _error(message: str) -> SemanticLocalAccountingGraphV2Error:
    return SemanticLocalAccountingGraphV2Error(message)


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise _error(f"{label} is not a lowercase SHA-256")
    return value


def _bbox(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(coordinate) is not int for coordinate in value)
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise _error(f"{label} is not one non-empty canonical bbox")
    return list(value)


def _union_box(boxes: Sequence[Sequence[int]]) -> list[int]:
    if not boxes:
        raise _error("graph cannot union an empty bbox sequence")
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _source_ref(
    observation: Mapping[str, Any], spans: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if not spans:
        raise _error("every accepted source ref requires observed spans")
    atom_ids = [span["source_atom_id"] for span in spans]
    if any(type(atom_id) is not str for atom_id in atom_ids):
        raise _error("accepted span lacks one source atom identity")
    return {
        "source_local_page_id": observation["source_local_page_id"],
        "source_projection_sha256": observation["source_projection_sha256"],
        "canonical_bbox_mpt": _union_box([span["canonical_bbox_mpt"] for span in spans]),
        "source_atom_ids": sorted(set(atom_ids)),
    }


def _node(
    kind: str,
    status: str,
    source_ref: Mapping[str, Any],
    attributes: Mapping[str, Any],
) -> dict[str, Any]:
    value = {
        "kind": kind,
        "status": status,
        "source_ref": canonical_clone_v1(source_ref),
        "attributes": canonical_clone_v1(attributes),
    }
    value["node_id"] = f"slagv2:node:{canonical_json_sha256_v1(value)}"
    return value


def _edge(
    kind: str,
    from_node_id: str,
    to_node_id: str,
    evidence_node_ids: Sequence[str],
) -> dict[str, Any]:
    value = {
        "kind": kind,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "evidence_node_ids": sorted(set(evidence_node_ids)),
    }
    if not value["evidence_node_ids"]:
        raise _error("every accepted edge requires source evidence")
    value["edge_id"] = f"slagv2:edge:{canonical_json_sha256_v1(value)}"
    return value


def _evidence_attributes(span: Mapping[str, Any], evidence_role: str) -> dict[str, Any]:
    semantic = evidence_role in _SEMANTIC_EVIDENCE_ROLES
    unit = evidence_role == "UNIT_LABEL"
    numeric = evidence_role == "VALUE_NUMERIC"
    period = evidence_role == "AXIS_DATE"
    if not (semantic or numeric or period):
        raise _error("unsupported graph evidence role")
    text_field = "transformer_text_nfc" if semantic else "raw_text"
    expected_source = (
        "VIETOCR_VGG_TRANSFORMER_0_3_13"
        if semantic
        else "PPOCRV6_NUMERIC_ONLY"
        if numeric
        else "PPOCRV6_DATE_ONLY"
    )
    if span.get("semantic_text_source" if semantic else "text_source") != expected_source:
        raise _error("observation text authority differs from graph evidence role")
    return {
        "evidence_role": evidence_role,
        "raw_text_utf8": span[text_field],
        "text_source": expected_source,
        "semantic_identity_authority": semantic,
        "unit_identity_authority": unit,
        "numeric_authority": numeric,
        "period_authority": period,
        "geometry_authority": "AUTHENTICATED_V3_LINE_GEOMETRY",
        "source_line_index": span["source_line_index"],
    }


def _decimal(value: Any) -> Decimal:
    if type(value) is not str:
        raise _error("value position lacks one normalized decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise _error("value position normalized decimal is invalid") from exc
    if not parsed.is_finite() or str(parsed) != value:
        raise _error("value position normalized decimal is not canonical")
    return parsed


def _raw_financial_decimal(value: Any) -> Decimal:
    if type(value) is not str:
        raise _error("PP numeric evidence lacks one raw string")
    text = value.strip().replace("\u00a0", "").replace("\u202f", "").replace(" ", "")
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    if text.startswith(("+", "-")):
        negative = text[0] == "-"
        text = text[1:]
    if re.fullmatch(r"[0-9]+", text) is not None:
        digits = text
    elif re.fullmatch(r"[0-9]{1,3}(?:[.,][0-9]{3})+", text) is not None:
        separators = {character for character in text if character in ".,"}
        if len(separators) != 1:
            raise _error("PP numeric evidence has ambiguous grouping")
        digits = text.replace(next(iter(separators)), "")
    else:
        raise _error("PP numeric evidence is not one strict financial integer")
    parsed = Decimal(digits)
    return -parsed if negative else parsed


def _accepted_graph_parts(
    observation: Mapping[str, Any],
    region: Mapping[str, Any],
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: Sequence[FamilySpecV1],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    required_roles = [item.role for item in family_spec.ordered_children]
    observed_rows = region.get("rows")
    if type(observed_rows) is not list:
        raise _error("observation rows are not one ordered row sequence")
    row_roles = [row.get("role") if type(row) is dict else None for row in observed_rows]
    if row_roles != [*required_roles, "TOTAL"]:
        raise _error("observation rows differ from exact target FamilySpec ordered topology")
    if tuple(required_roles) != family_spec.closure_child_roles:
        raise _error("graph v2 currently requires exact required-child additive closure roles")
    required_rows = observed_rows[:-1]
    total_row = observed_rows[-1]
    for row in required_rows:
        label = row.get("label")
        if (
            type(label) is not dict
            or type(label.get("transformer_text_nfc")) is not str
            or not label["transformer_text_nfc"].strip()
            or label.get("semantic_text_source") != "VIETOCR_VGG_TRANSFORMER_0_3_13"
            or type(label.get("source_atom_id")) is not str
            or row.get("total_resolution") is not None
        ):
            raise _error("required child row lacks one exact Transformer semantic label")
    if (
        total_row.get("label") is not None
        or total_row.get("total_resolution") != "IMMEDIATE_UNLABELED_NUMERIC_ROW"
    ):
        raise _error("TOTAL row is not the exact immediate unlabeled numeric row")
    alias_index = compile_vietnamese_family_alias_index_v1(family_specs_for_collision_scope)

    def semantic_matches(span: Any, role_kind: str, role: str) -> bool:
        if type(span) is not dict:
            return False
        proposal = propose_vietnamese_semantic_surface_v1(
            span.get("transformer_text_nfc"), alias_index
        )
        target = [
            candidate
            for candidate in proposal.candidates
            if candidate.family_id == family_spec.family_id
            and candidate.role_kind == role_kind
            and candidate.role == role
        ]
        identities = {(candidate.role_kind, candidate.role) for candidate in proposal.candidates}
        return bool(target) and len(identities) == 1

    if not semantic_matches(region.get("owner_label"), "OWNER", "OWNER"):
        raise _error("Transformer owner text does not reproduce the target family role")
    branch_span = region.get("branch_label")
    branch_key = (
        propose_vietnamese_semantic_surface_v1(
            branch_span.get("transformer_text_nfc"), alias_index
        ).accentless_comparison_key
        if type(branch_span) is dict
        else None
    )
    branch_alias_keys = {
        propose_vietnamese_semantic_surface_v1(alias, alias_index).accentless_comparison_key
        for alias in family_spec.branch_aliases
    }
    if not semantic_matches(branch_span, "BRANCH", "BRANCH") and (
        type(branch_key) is not str
        or not any(
            branch_key == key or branch_key.startswith(key + " ") for key in branch_alias_keys
        )
    ):
        raise _error("Transformer branch text does not reproduce the target family role")
    for child, row in zip(family_spec.ordered_children, region["rows"][:-1], strict=True):
        if not semantic_matches(row.get("label"), "ORDERED_CHILD", child.role):
            raise _error("Transformer row text does not reproduce the target family role")
    axes = region.get("axes")
    units_input = region.get("local_unit_labels")
    if (
        type(axes) is not list
        or type(units_input) is not list
        or len(axes) != 2
        or len(units_input) != 2
    ):
        raise _error("observation does not contain exact two-axis/two-unit topology")
    if [axis.get("axis_index") for axis in axes] != [0, 1] or len(
        {axis.get("period") for axis in axes}
    ) != 2:
        raise _error("observation comparative period axes are not distinct and ordered")
    if any(
        parse_local_accounting_period_v1(axis.get("raw_text")) != axis.get("period")
        for axis in axes
    ):
        raise _error("PP date evidence does not reproduce the declared period axes")
    if any(
        parse_local_accounting_unit_v1(unit.get("transformer_text_nfc")) != unit.get("unit")
        for unit in units_input
    ):
        raise _error("Transformer unit text does not reproduce the declared unit scope")
    for row in region["rows"]:
        values = row.get("value_positions")
        if type(values) is not list or [value.get("axis_index") for value in values] != [0, 1]:
            raise _error("observation row does not have exact ordered two-axis values")
        for value in values:
            parsed = _raw_financial_decimal(value.get("raw_text"))
            normalized = _decimal(value.get("normalized_decimal"))
            expected_state = "OBSERVED_ZERO" if parsed == 0 else "OBSERVED_VALUE"
            if parsed != normalized or value.get("state") != expected_state:
                raise _error("PP numeric text does not reproduce normalized value/state")
    semantic_spans = [region.get("owner_label"), region.get("branch_label")]
    semantic_spans.extend(
        row.get("label") for row in region["rows"] if row.get("label") is not None
    )
    semantic_spans.extend(units_input)
    date_spans = list(axes)
    value_spans = [value for row in region["rows"] for value in row.get("value_positions", [])]
    for label, spans in (
        ("semantic/unit", semantic_spans),
        ("date", date_spans),
        ("numeric value", value_spans),
    ):
        atom_ids = [span.get("source_atom_id") if type(span) is dict else None for span in spans]
        if any(type(atom_id) is not str for atom_id in atom_ids) or len(atom_ids) != len(
            set(atom_ids)
        ):
            raise _error(f"observation reuses one source LINE across {label} slots")
    all_slot_ids = [span["source_atom_id"] for span in [*semantic_spans, *date_spans, *value_spans]]
    if len(all_slot_ids) != len(set(all_slot_ids)):
        raise _error("observation reuses one source LINE across distinct authority/structure slots")
    rows_by_role = {row["role"]: row for row in region["rows"]}
    for axis_index in (0, 1):
        child_sum = sum(
            (
                _decimal(rows_by_role[role]["value_positions"][axis_index]["normalized_decimal"])
                for role in family_spec.closure_child_roles
            ),
            Decimal(),
        )
        total = _decimal(rows_by_role["TOTAL"]["value_positions"][axis_index]["normalized_decimal"])
        if child_sum != total:
            raise _error(
                "observation arithmetic flag is not supported by recomputed Decimal closure"
            )
    evidence_nodes: list[dict[str, Any]] = []
    evidence_by_atom: dict[str, dict[str, Any]] = {}

    def evidence(span: Mapping[str, Any], role: str) -> dict[str, Any]:
        atom_id = span["source_atom_id"]
        attributes = _evidence_attributes(span, role)
        existing = evidence_by_atom.get(atom_id)
        if existing is not None:
            if existing["attributes"] != attributes:
                raise _error("one source atom was assigned conflicting graph evidence roles")
            return existing
        node = _node(
            "EVIDENCE",
            "BOUND_SOURCE_EVIDENCE",
            _source_ref(observation, [span]),
            attributes,
        )
        evidence_by_atom[atom_id] = node
        evidence_nodes.append(node)
        return node

    owner_span = region["owner_label"]
    branch_span = region["branch_label"]
    owner_evidence = evidence(owner_span, "OWNER_LABEL")
    branch_evidence = evidence(branch_span, "BRANCH_LABEL")
    axis_evidence = [evidence(axis, "AXIS_DATE") for axis in region["axes"]]
    unit_evidence = [evidence(unit, "UNIT_LABEL") for unit in region["local_unit_labels"]]
    row_evidence: list[list[dict[str, Any]]] = []
    value_evidence: list[list[dict[str, Any]]] = []
    all_spans: list[Mapping[str, Any]] = [
        owner_span,
        branch_span,
        *region["axes"],
        *region["local_unit_labels"],
    ]
    for row in region["rows"]:
        values = row["value_positions"]
        observed = [evidence(value, "VALUE_NUMERIC") for value in values]
        value_evidence.append(observed)
        if row["label"] is None:
            row_evidence.append(observed)
        else:
            row_evidence.append([evidence(row["label"], "ROW_LABEL")])
            all_spans.append(row["label"])
        all_spans.extend(values)

    scope = _acceptance_scope(True)
    table = _node(
        "TABLE",
        "ACCEPTED_SOURCE_STRUCTURE",
        _source_ref(observation, all_spans),
        {
            "family_id": observation["family_id"],
            "family_spec_sha256": observation["family_spec_sha256"],
            "acceptance_scope": scope,
            "internal_additive_closure_only": True,
            "same_population_claimed": False,
        },
    )
    owner = _node(
        "ACCOUNTING_ROLE",
        "ACCEPTED_SOURCE_STRUCTURE",
        _source_ref(observation, [owner_span]),
        {"accounting_role": "OWNER_LABEL", "family_id": observation["family_id"]},
    )
    branch = _node(
        "ACCOUNTING_ROLE",
        "ACCEPTED_SOURCE_STRUCTURE",
        _source_ref(observation, [branch_span]),
        {"accounting_role": "BRANCH_LABEL", "family_id": observation["family_id"]},
    )
    axis_nodes = [
        _node(
            "AXIS",
            "ACCEPTED_SOURCE_STRUCTURE",
            _source_ref(observation, [axis]),
            {"axis_index": axis["axis_index"], "period": axis["period"]},
        )
        for axis in region["axes"]
    ]
    units = [
        _node(
            "UNIT_SCOPE",
            "ACCEPTED_SOURCE_STRUCTURE",
            _source_ref(observation, [unit]),
            {"axis_index": axis_index, "unit": unit["unit"]},
        )
        for axis_index, unit in enumerate(region["local_unit_labels"])
    ]
    rows = []
    values_by_row: list[list[dict[str, Any]]] = []
    for ordinal, row in enumerate(region["rows"]):
        row_spans = [row["label"]] if row["label"] is not None else row["value_positions"]
        rows.append(
            _node(
                "LOGICAL_ROW",
                "ACCEPTED_SOURCE_STRUCTURE",
                _source_ref(observation, row_spans),
                {
                    "row_role": row["role"],
                    "ordinal": ordinal,
                    "total_resolution": row.get("total_resolution"),
                },
            )
        )
        values_by_row.append(
            [
                _node(
                    "VALUE_POSITION",
                    "ACCEPTED_SOURCE_STRUCTURE",
                    _source_ref(observation, [value]),
                    {
                        "row_role": row["role"],
                        "row_ordinal": ordinal,
                        "axis_index": value["axis_index"],
                        "raw_text": value["raw_text"],
                        "normalized_decimal": value["normalized_decimal"],
                        "state": value["state"],
                    },
                )
                for value in row["value_positions"]
            ]
        )

    structural_nodes = [table, owner, branch, *axis_nodes, *units, *rows]
    structural_nodes.extend(value for row_values in values_by_row for value in row_values)
    edges: list[dict[str, Any]] = []

    def add(kind: str, source: dict, target: dict, support: Sequence[dict]) -> None:
        edges.append(
            _edge(
                kind,
                source["node_id"],
                target["node_id"],
                [item["node_id"] for item in support],
            )
        )

    add("OWNS", owner, table, [owner_evidence])
    add("PARENT_OF", owner, branch, [owner_evidence, branch_evidence])
    for node, support in (
        (branch, [branch_evidence]),
        *((axis, [support]) for axis, support in zip(axis_nodes, axis_evidence, strict=True)),
        *((unit, [support]) for unit, support in zip(units, unit_evidence, strict=True)),
        *((row, support) for row, support in zip(rows, row_evidence, strict=True)),
    ):
        add("CONTAINS", table, node, support)
    for row, support in zip(rows, row_evidence, strict=True):
        add("PARENT_OF", branch, row, [branch_evidence, *support])
    for first_index in range(len(rows) - 1):
        add(
            "NEXT_SIBLING",
            rows[first_index],
            rows[first_index + 1],
            [*row_evidence[first_index], *row_evidence[first_index + 1]],
        )
    for row_index, (row, values) in enumerate(zip(rows, values_by_row, strict=True)):
        for value, support in zip(values, value_evidence[row_index], strict=True):
            axis_index = value["attributes"]["axis_index"]
            add("CONTAINS", row, value, [*row_evidence[row_index], support])
            add(
                "ALIGNED_TO_AXIS",
                value,
                axis_nodes[axis_index],
                [support, axis_evidence[axis_index]],
            )
            add("SCOPED_BY_UNIT", value, units[axis_index], [support, unit_evidence[axis_index]])
    total = rows[-1]
    row_node_by_role = {row["attributes"]["row_role"]: row for row in rows}
    row_index_by_role = {
        row["attributes"]["row_role"]: row["attributes"]["ordinal"] for row in rows
    }
    for role in family_spec.closure_child_roles:
        child_index = row_index_by_role[role]
        add(
            "TOTAL_OF",
            total,
            row_node_by_role[role],
            [*row_evidence[-1], *row_evidence[child_index]],
        )

    support_by_node = {
        table["node_id"]: list(evidence_nodes),
        owner["node_id"]: [owner_evidence],
        branch["node_id"]: [branch_evidence],
        **{axis["node_id"]: [item] for axis, item in zip(axis_nodes, axis_evidence, strict=True)},
        **{unit["node_id"]: [item] for unit, item in zip(units, unit_evidence, strict=True)},
        **{row["node_id"]: support for row, support in zip(rows, row_evidence, strict=True)},
    }
    for row_index, values in enumerate(values_by_row):
        support_by_node.update(
            {
                value["node_id"]: [item]
                for value, item in zip(values, value_evidence[row_index], strict=True)
            }
        )
    by_evidence_id = {node["node_id"]: node for node in evidence_nodes}
    for node_id, support in support_by_node.items():
        for evidence_node in support:
            edges.append(
                _edge(
                    "SUPPORTED_BY",
                    node_id,
                    evidence_node["node_id"],
                    [evidence_node["node_id"]],
                )
            )
            if evidence_node["node_id"] not in by_evidence_id:
                raise _error("support edge references an unbound evidence node")
    return [*structural_nodes, *evidence_nodes], edges


def _acceptance_scope(accepted: bool) -> dict[str, bool]:
    return {
        "supplied_family_collision_scope_only": True,
        "ready_within_supplied_family_collision_scope": accepted,
        "globally_collision_free_claimed": False,
        "family_registry_exhaustiveness_claimed": False,
        "page_family_exhaustiveness_claimed": False,
        "target_family_evaluated_only": True,
        "non_target_supplied_families_used_for_collision_only": True,
        "non_target_supplied_family_dispositions_claimed": False,
    }


def _evaluation_partition(
    family_id: str, scope_specs: Mapping[str, str], accepted: bool
) -> dict[str, dict[str, str]]:
    return {
        supplied_family_id: (
            {
                "use": "TARGET_FAMILY_EVALUATED",
                "disposition": ACCEPTED_STATUS if accepted else UNRESOLVED_STATUS,
            }
            if supplied_family_id == family_id
            else {"use": "COLLISION_SCOPE_ONLY", "disposition": "NOT_EVALUATED"}
        )
        for supplied_family_id in sorted(scope_specs)
    }


def _graph_without_id(graph: Mapping[str, Any]) -> dict[str, Any]:
    return {key: canonical_clone_v1(value) for key, value in graph.items() if key != "graph_id"}


def _metrics(
    nodes: Sequence[Mapping[str, Any]], edges: Sequence[Mapping[str, Any]], accepted: bool
) -> dict[str, Any]:
    node_ids = {node["node_id"] for node in nodes}
    evidence_ids = {node["node_id"] for node in nodes if node["kind"] == "EVIDENCE"}
    invalid = sum(
        edge["from_node_id"] not in node_ids
        or edge["to_node_id"] not in node_ids
        or not set(edge["evidence_node_ids"]) <= evidence_ids
        for edge in edges
    )
    degree = Counter()
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for edge in edges:
        if edge["from_node_id"] in node_ids and edge["to_node_id"] in node_ids:
            degree[edge["from_node_id"]] += 1
            degree[edge["to_node_id"]] += 1
            adjacency[edge["from_node_id"]].add(edge["to_node_id"])
            adjacency[edge["to_node_id"]].add(edge["from_node_id"])
    supported = {edge["to_node_id"] for edge in edges if edge["kind"] == "SUPPORTED_BY"}
    visited: set[str] = set()
    tables = [node["node_id"] for node in nodes if node["kind"] == "TABLE"]
    if tables:
        queue = deque([tables[0]])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            queue.extend(adjacency[current] - visited)
    return {
        "accepted_region_count": int(accepted),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "evidence_node_count": len(evidence_ids),
        "orphan_node_count": sum(degree[node_id] == 0 for node_id in node_ids),
        "orphan_evidence_count": len(evidence_ids - supported),
        "invalid_edge_count": invalid,
        "disconnected_node_count": len(node_ids - visited) if nodes else 0,
        "accepted_counts": {
            "TABLE": sum(node["kind"] == "TABLE" for node in nodes),
            "LOGICAL_ROW": sum(node["kind"] == "LOGICAL_ROW" for node in nodes),
            "VALUE_POSITION": sum(node["kind"] == "VALUE_POSITION" for node in nodes),
            "AXIS": sum(node["kind"] == "AXIS" for node in nodes),
            "HIERARCHY": sum(
                edge["kind"] in {"OWNS", "PARENT_OF", "NEXT_SIBLING", "TOTAL_OF"} for edge in edges
            ),
        },
    }


def _validate_source_ref(source_ref: Any, graph: Mapping[str, Any], label: str) -> dict[str, Any]:
    if type(source_ref) is not dict or set(source_ref) != _SOURCE_REF_FIELDS:
        raise _error(f"{label} source-ref fields drifted")
    if (
        source_ref["source_local_page_id"] != graph["source_local_page_id"]
        or source_ref["source_projection_sha256"] != graph["source_projection_sha256"]
    ):
        raise _error(f"{label} source-ref page binding drifted")
    _bbox(source_ref["canonical_bbox_mpt"], f"{label} canonical bbox")
    atom_ids = source_ref["source_atom_ids"]
    if (
        type(atom_ids) is not list
        or not atom_ids
        or atom_ids != sorted(set(atom_ids))
        or any(
            type(atom_id) is not str or not atom_id.startswith("ssv1:atom:") for atom_id in atom_ids
        )
    ):
        raise _error(f"{label} source atom identities drifted")
    return source_ref


def _validate_evidence_authority(node: Mapping[str, Any]) -> None:
    attributes = node["attributes"]
    role = attributes["evidence_role"]
    semantic = role in _SEMANTIC_EVIDENCE_ROLES
    numeric = role == "VALUE_NUMERIC"
    period = role == "AXIS_DATE"
    if not (semantic or numeric or period):
        raise _error("persisted evidence role is unsupported")
    expected_source = (
        "VIETOCR_VGG_TRANSFORMER_0_3_13"
        if semantic
        else "PPOCRV6_NUMERIC_ONLY"
        if numeric
        else "PPOCRV6_DATE_ONLY"
    )
    if attributes != {
        **attributes,
        "text_source": expected_source,
        "semantic_identity_authority": semantic,
        "unit_identity_authority": role == "UNIT_LABEL",
        "numeric_authority": numeric,
        "period_authority": period,
        "geometry_authority": "AUTHENTICATED_V3_LINE_GEOMETRY",
    }:
        raise _error("persisted evidence crosses the Transformer/PP authority split")
    if len(node["source_ref"]["source_atom_ids"]) != 1:
        raise _error("one evidence node must bind exactly one source LINE atom")


def _relation_set(edges: Sequence[Mapping[str, Any]], kind: str) -> set[tuple[str, str]]:
    return {(edge["from_node_id"], edge["to_node_id"]) for edge in edges if edge["kind"] == kind}


def _validate_accepted_topology(
    graph: Mapping[str, Any], nodes: Sequence[Mapping[str, Any]], edges: Sequence[Mapping[str, Any]]
) -> None:
    by_kind: dict[str, list[Mapping[str, Any]]] = {
        kind: [node for node in nodes if node["kind"] == kind] for kind in _NODE_KINDS
    }
    if len(by_kind["TABLE"]) != 1 or len(by_kind["ACCOUNTING_ROLE"]) != 2:
        raise _error("accepted graph lacks one table and exact owner/branch roles")
    table = by_kind["TABLE"][0]
    roles = {node["attributes"]["accounting_role"]: node for node in by_kind["ACCOUNTING_ROLE"]}
    if set(roles) != {"OWNER_LABEL", "BRANCH_LABEL"}:
        raise _error("accepted graph owner/branch roles drifted")
    axes = sorted(by_kind["AXIS"], key=lambda node: node["attributes"]["axis_index"])
    units = sorted(by_kind["UNIT_SCOPE"], key=lambda node: node["attributes"]["axis_index"])
    rows = sorted(by_kind["LOGICAL_ROW"], key=lambda node: node["attributes"]["ordinal"])
    if (
        [node["attributes"]["axis_index"] for node in axes] != [0, 1]
        or [node["attributes"]["axis_index"] for node in units] != [0, 1]
        or len({canonical_json_sha256_v1(node["attributes"]["unit"]) for node in units}) != 1
        or not rows
        or [node["attributes"]["ordinal"] for node in rows] != list(range(len(rows)))
        or rows[-1]["attributes"]["row_role"] != "TOTAL"
    ):
        raise _error("accepted graph comparative axes, units, or row frontier drifted")
    values = by_kind["VALUE_POSITION"]
    values_by_row = {
        row["attributes"]["ordinal"]: sorted(
            [
                value
                for value in values
                if value["attributes"]["row_ordinal"] == row["attributes"]["ordinal"]
            ],
            key=lambda value: value["attributes"]["axis_index"],
        )
        for row in rows
    }
    if any(
        [value["attributes"]["axis_index"] for value in row_values] != [0, 1]
        or any(
            value["attributes"]["row_role"] != row["attributes"]["row_role"] for value in row_values
        )
        for row, row_values in zip(rows, values_by_row.values(), strict=True)
    ):
        raise _error("accepted graph row/value axis topology drifted")

    owns = _relation_set(edges, "OWNS")
    contains = _relation_set(edges, "CONTAINS")
    parents = _relation_set(edges, "PARENT_OF")
    siblings = _relation_set(edges, "NEXT_SIBLING")
    aligned = _relation_set(edges, "ALIGNED_TO_AXIS")
    scoped = _relation_set(edges, "SCOPED_BY_UNIT")
    totals = _relation_set(edges, "TOTAL_OF")
    if owns != {(roles["OWNER_LABEL"]["node_id"], table["node_id"])}:
        raise _error("accepted graph owner edge drifted")
    expected_table_contains = {
        (table["node_id"], node["node_id"])
        for node in [roles["BRANCH_LABEL"], *axes, *units, *rows]
    }
    expected_row_contains = {
        (row["node_id"], value["node_id"])
        for row in rows
        for value in values_by_row[row["attributes"]["ordinal"]]
    }
    if contains != expected_table_contains | expected_row_contains:
        raise _error("accepted graph containment topology drifted")
    if parents != {
        (roles["OWNER_LABEL"]["node_id"], roles["BRANCH_LABEL"]["node_id"]),
        *((roles["BRANCH_LABEL"]["node_id"], row["node_id"]) for row in rows),
    }:
        raise _error("accepted graph branch/row topology drifted")
    if siblings != {
        (rows[index]["node_id"], rows[index + 1]["node_id"]) for index in range(len(rows) - 1)
    }:
        raise _error("accepted graph ordered sibling topology drifted")
    if aligned != {
        (
            value["node_id"],
            axes[value["attributes"]["axis_index"]]["node_id"],
        )
        for value in values
    } or scoped != {
        (
            value["node_id"],
            units[value["attributes"]["axis_index"]]["node_id"],
        )
        for value in values
    }:
        raise _error("accepted graph value alignment/unit scope topology drifted")
    if totals != {(rows[-1]["node_id"], row["node_id"]) for row in rows[:-1]}:
        raise _error("accepted graph internal total topology drifted")


def _validate_graph_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _TOP_FIELDS:
        raise _error("semantic graph top-level fields drifted")
    graph = canonical_clone_v1(value)
    if graph["format_version"] != FORMAT_VERSION or graph["claim_boundary"] != CLAIM_BOUNDARY:
        raise _error("semantic graph identity/claim boundary drifted")
    if graph["status"] not in {ACCEPTED_STATUS, UNRESOLVED_STATUS}:
        raise _error("semantic graph status drifted")
    if type(graph["source_local_page_id"]) is not str or not graph[
        "source_local_page_id"
    ].startswith("ssv2:page:"):
        raise _error("semantic graph source page identity drifted")
    for field in (
        "source_projection_sha256",
        "semantic_page_binding_sha256",
        "observation_candidate_sha256",
        "family_spec_sha256",
    ):
        _sha(graph[field], field)
    scope_specs = graph["supplied_family_collision_scope_spec_sha256_by_id"]
    if (
        type(scope_specs) is not dict
        or not scope_specs
        or any(
            type(family_id) is not str or not family_id or _SHA_RE.fullmatch(digest) is None
            for family_id, digest in scope_specs.items()
        )
    ):
        raise _error("semantic graph supplied family collision scope drifted")
    if (
        graph["family_id"] not in scope_specs
        or scope_specs[graph["family_id"]] != graph["family_spec_sha256"]
    ):
        raise _error("semantic graph target family is not exactly bound inside collision scope")
    accepted = graph["status"] == ACCEPTED_STATUS
    if not same_typed_json_v1(graph["acceptance_scope"], _acceptance_scope(accepted)):
        raise _error("semantic graph bounded acceptance scope drifted")
    if not same_typed_json_v1(
        graph["supplied_family_evaluation_partition"],
        _evaluation_partition(graph["family_id"], scope_specs, accepted),
    ):
        raise _error("semantic graph target/collision-only family partition drifted")
    if not same_typed_json_v1(graph["safety"], _fixed_safety_payload()):
        raise _error("semantic graph safety boundary drifted")
    if type(graph["nodes"]) is not list or type(graph["edges"]) is not list:
        raise _error("semantic graph node/edge axes drifted")

    node_ids: set[str] = set()
    evidence_ids: set[str] = set()
    for index, node in enumerate(graph["nodes"]):
        if type(node) is not dict or set(node) != _NODE_FIELDS or node["kind"] not in _NODE_KINDS:
            raise _error(f"semantic graph node {index} fields/kind drifted")
        if (
            type(node["attributes"]) is not dict
            or set(node["attributes"]) != (_STRUCTURAL_ATTRIBUTE_FIELDS[node["kind"]])
        ):
            raise _error(f"semantic graph node {index} attributes drifted")
        _validate_source_ref(node["source_ref"], graph, f"node {index}")
        expected_id = _node(node["kind"], node["status"], node["source_ref"], node["attributes"])[
            "node_id"
        ]
        if node["node_id"] != expected_id or node["node_id"] in node_ids:
            raise _error(f"semantic graph node {index} identity drifted")
        node_ids.add(node["node_id"])
        if node["kind"] == "EVIDENCE":
            evidence_ids.add(node["node_id"])
            _validate_evidence_authority(node)
        elif node["status"] != "ACCEPTED_SOURCE_STRUCTURE":
            raise _error("non-evidence node is not accepted source structure")
    edge_ids: set[str] = set()
    for index, edge in enumerate(graph["edges"]):
        if type(edge) is not dict or set(edge) != _EDGE_FIELDS or edge["kind"] not in _EDGE_KINDS:
            raise _error(f"semantic graph edge {index} fields/kind drifted")
        if (
            edge["from_node_id"] not in node_ids
            or edge["to_node_id"] not in node_ids
            or type(edge["evidence_node_ids"]) is not list
            or not edge["evidence_node_ids"]
            or edge["evidence_node_ids"] != sorted(set(edge["evidence_node_ids"]))
            or not set(edge["evidence_node_ids"]) <= evidence_ids
        ):
            raise _error(f"semantic graph edge {index} has orphan endpoint/evidence")
        expected_id = _edge(
            edge["kind"],
            edge["from_node_id"],
            edge["to_node_id"],
            edge["evidence_node_ids"],
        )["edge_id"]
        if edge["edge_id"] != expected_id or edge["edge_id"] in edge_ids:
            raise _error(f"semantic graph edge {index} identity drifted")
        edge_ids.add(edge["edge_id"])
        if edge["kind"] == "SUPPORTED_BY":
            if edge["from_node_id"] in evidence_ids or edge["to_node_id"] not in evidence_ids:
                raise _error("SUPPORTED_BY edge direction drifted")
        elif edge["from_node_id"] in evidence_ids or edge["to_node_id"] in evidence_ids:
            raise _error("evidence node participates in a non-support topology edge")

    expected_metrics = _metrics(graph["nodes"], graph["edges"], accepted)
    if (
        type(graph["metrics"]) is not dict
        or set(graph["metrics"]) != _METRIC_FIELDS
        or not same_typed_json_v1(graph["metrics"], expected_metrics)
        or any(
            graph["metrics"][field] != 0
            for field in (
                "orphan_node_count",
                "orphan_evidence_count",
                "invalid_edge_count",
                "disconnected_node_count",
            )
        )
    ):
        raise _error("semantic graph closure metrics drifted")
    if accepted:
        expected_arithmetic = {
            "status": "CORROBORATED",
            "evaluated_axis_indexes": [0, 1],
            "internal_additive_closure_only": True,
            "same_population_claimed": False,
        }
        if graph["unresolved_reasons"] != [] or not same_typed_json_v1(
            graph["arithmetic"], expected_arithmetic
        ):
            raise _error("accepted graph arithmetic/decision boundary drifted")
        _validate_accepted_topology(graph, graph["nodes"], graph["edges"])
        supported = {
            edge["to_node_id"] for edge in graph["edges"] if edge["kind"] == "SUPPORTED_BY"
        }
        if supported != evidence_ids:
            raise _error("accepted graph has orphan source evidence")
        table_id = next(node["node_id"] for node in graph["nodes"] if node["kind"] == "TABLE")
        table_support = [
            edge
            for edge in graph["edges"]
            if edge["kind"] == "SUPPORTED_BY" and edge["from_node_id"] == table_id
        ]
        if (
            len(table_support) != len(evidence_ids)
            or {edge["to_node_id"] for edge in table_support} != evidence_ids
        ):
            raise _error("accepted table does not bind every accepted evidence node")
    elif (
        graph["nodes"]
        or graph["edges"]
        or graph["arithmetic"] is not None
        or type(graph["unresolved_reasons"]) is not list
        or not graph["unresolved_reasons"]
    ):
        raise _error("unresolved graph persisted accepted topology")
    expected_graph_id = f"slagv2:graph:{canonical_json_sha256_v1(_graph_without_id(graph))}"
    if graph["graph_id"] != expected_graph_id:
        raise _error("semantic graph identity drifted")
    return graph


def _build_from_observation(
    observation: Mapping[str, Any],
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: Sequence[FamilySpecV1],
) -> dict[str, Any]:
    if type(observation) is not dict:
        raise _error("semantic observation candidate is not a dictionary")
    ready = (
        observation.get("status") == "READY_FOR_GRAPH_V2"
        and observation.get("readiness", {}).get("ready_within_supplied_family_collision_scope")
        is True
        and observation.get("readiness", {}).get("globally_collision_free_claimed") is False
        and observation.get("readiness", {}).get("complete_topology_count") == 1
        and type(observation.get("candidate_regions")) is list
        and len(observation["candidate_regions"]) == 1
    )
    if observation.get("status") not in {"READY_FOR_GRAPH_V2", "UNRESOLVED"}:
        raise _error("semantic observation readiness status drifted")
    if ready:
        region = observation["candidate_regions"][0]
        if (
            region.get("topology", {}).get("internal_additive_closure") is not True
            or region.get("topology", {}).get("same_population_claimed") is not False
            or region.get("arithmetic")
            != {"status": "CORROBORATED", "evaluated_axis_indexes": [0, 1]}
        ):
            raise _error("semantic observation cannot support the graph-v2 closure boundary")
        nodes, edges = _accepted_graph_parts(
            observation, region, family_spec, family_specs_for_collision_scope
        )
        status = ACCEPTED_STATUS
        arithmetic = {
            "status": "CORROBORATED",
            "evaluated_axis_indexes": [0, 1],
            "internal_additive_closure_only": True,
            "same_population_claimed": False,
        }
        unresolved_reasons: list[str] = []
    else:
        if observation.get("status") != "UNRESOLVED":
            raise _error("incomplete observation cannot be persisted as accepted graph")
        nodes = []
        edges = []
        status = UNRESOLVED_STATUS
        arithmetic = None
        unresolved_reasons = sorted(set(observation.get("unresolved_reasons", [])))
        if not unresolved_reasons:
            raise _error("unresolved observation lacks explicit reasons")
    accepted = status == ACCEPTED_STATUS
    graph = {
        "format_version": FORMAT_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "status": status,
        "source_local_page_id": observation["source_local_page_id"],
        "source_projection_sha256": observation["source_projection_sha256"],
        "semantic_page_binding_sha256": observation["semantic_page_binding_sha256"],
        "observation_candidate_sha256": canonical_json_sha256_v1(observation),
        "family_id": observation["family_id"],
        "family_spec_sha256": observation["family_spec_sha256"],
        "supplied_family_collision_scope_spec_sha256_by_id": canonical_clone_v1(
            observation["supplied_family_collision_scope_spec_sha256_by_id"]
        ),
        "supplied_family_evaluation_partition": _evaluation_partition(
            observation["family_id"],
            observation["supplied_family_collision_scope_spec_sha256_by_id"],
            accepted,
        ),
        "acceptance_scope": _acceptance_scope(accepted),
        "nodes": nodes,
        "edges": edges,
        "arithmetic": arithmetic,
        "unresolved_reasons": unresolved_reasons,
        "metrics": _metrics(nodes, edges, accepted),
        "safety": _fixed_safety_payload(),
    }
    graph["graph_id"] = f"slagv2:graph:{canonical_json_sha256_v1(graph)}"
    return _validate_graph_shape(graph)


def build_semantic_local_accounting_graph_v2(
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: Sequence[FamilySpecV1],
) -> dict[str, Any]:
    """Build one persistable graph or an explicit zero-accepted unresolved result."""

    if type(family_spec) is not FamilySpecV1:
        raise _error("graph target family spec must be one exact FamilySpecV1")
    if (
        isinstance(family_specs_for_collision_scope, (str, bytes, bytearray))
        or not isinstance(family_specs_for_collision_scope, Sequence)
        or not family_specs_for_collision_scope
        or any(type(spec) is not FamilySpecV1 for spec in family_specs_for_collision_scope)
    ):
        raise _error("graph collision scope must be a non-empty exact FamilySpecV1 sequence")
    scope_ids = [spec.family_id for spec in family_specs_for_collision_scope]
    if len(scope_ids) != len(set(scope_ids)):
        raise _error("graph collision scope contains duplicate family identities")
    if family_spec.family_id not in scope_ids:
        raise _error("graph target family is absent from supplied collision scope")
    try:
        observation = build_semantic_local_accounting_observation_candidate_v2(
            source_projection_v2,
            semantic_page_binding_v2,
            authenticated_transformer_receipt_v2,
            family_spec,
            family_specs_for_collision_scope,
        )
    except ValueError as exc:
        raise _error("semantic observation replay failed before graph construction") from exc
    return _build_from_observation(observation, family_spec, family_specs_for_collision_scope)


def validate_semantic_local_accounting_graph_replay_v2(
    value: Any,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: Sequence[FamilySpecV1],
) -> dict[str, Any]:
    """Validate shape, reconstruct from exact authenticated inputs, and compare."""

    persisted = _validate_graph_shape(value)
    if (
        type(family_spec) is not FamilySpecV1
        or persisted["family_id"] != family_spec.family_id
        or persisted["family_spec_sha256"] != local_accounting_family_spec_sha256_v1(family_spec)
    ):
        raise _error("replay target family/spec differs from persisted graph")
    rebuilt = build_semantic_local_accounting_graph_v2(
        source_projection_v2,
        semantic_page_binding_v2,
        authenticated_transformer_receipt_v2,
        family_spec,
        family_specs_for_collision_scope,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("persisted semantic graph does not replay from exact authenticated inputs")
    return canonical_clone_v1(rebuilt)
