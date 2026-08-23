"""Declarative schema proposals for repeated-role, stacked-period tables.

The primitive consumes one exact live-replayed stacked-period lane axis.  It
does not route by bank, file, page, note number, year, or schema wording.  A
family configuration binds source roles to tracked schema identities for each
period/lane pair, while row equations provide independent corroboration or a
veto.  Equations never repair OCR digits.

PP-OCRv6 remains the primary numeric proposal.  VietOCR is reread from the
same bound sample as an independent surface.  A separately tracked hosted
Gemma full-page observation may be supplied as a third challenger.  It can
corroborate either primary reader, or join VietOCR to rescue a malformed
PP-OCRv6 token, but it is never sufficient by itself.  A mixed-separator
candidate is eligible only when two readers encode the same integer, a peer in
the same lane uses an ordinary grouped-integer form, and every available
visible row equation containing that cell closes.  Missing or blank cells
remain unresolved.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation import accounting_stacked_period_lane_axis_v1 as lane_axis_v1
from bctc_ai.evaluation.family_first_numeric_cell_evidence_v1 import (
    parse_visible_financial_numeric_token_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "SPEC_FORMAT_VERSION",
    "AccountingStackedPeriodSchemaMappingV1Error",
    "build_accounting_stacked_period_schema_mapping_v1",
    "validate_accounting_stacked_period_schema_mapping_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_STACKED_PERIOD_SCHEMA_MAPPING_V1"
SPEC_FORMAT_VERSION = "ACCOUNTING_STACKED_PERIOD_SCHEMA_BINDING_SPEC_V1"
CLAIM_BOUNDARY = (
    "EXACT_REPLAYED_STACKED_PERIOD_LANE_AXIS_SAME_CROP_PPOCRVIET_RECOGNITION_"
    "DECLARATIVE_ACCOUNTING_VETO_AND_TRACKED_SCHEMA_BINDING_PROPOSAL_ONLY_"
    "REQUIRES_LATER_SOURCE_SCOPE_UNIT_AND_FORMAL_FAMILY_REPLAY_BEFORE_VERIFICATION"
)
_SAFETY = {
    "accounting_closure_changes_digits": False,
    "bank_file_note_page_year_used_for_routing": False,
    "blank_or_missing_cell_interpreted_as_zero": False,
    "mapping_authority": False,
    "gemma4_challenger_can_act_as_sole_numeric_reader": False,
    "gemma4_challenger_requires_exact_sample_crop_binding": True,
    "mixed_separator_requires_independent_agreement_peer_and_available_equation": True,
    "numeric_authority": False,
    "raw_record_self_authenticating": False,
    "schema_binding_declarative": True,
    "schema_creation_authority": False,
    "same_crop_semantic_group_separator_variants_compare_digits_only": True,
    "two_reader_exact_numeric_consensus_required_without_accounting": True,
    "signed_combined_carrying_lane_split_only_by_exact_numeric_sign": True,
    "sole_net_carrying_lane_split_only_when_atomic_lanes_absent": True,
    "scope_and_unit_gate_completed": False,
    "text_similarity_alone_can_map": False,
}
_SPEC_FIELDS = {
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
_EQUATION_FIELDS = {"component_lane_roles", "component_multipliers", "result_lane_role"}
_BINDING_FIELDS = {"lane_role", "period_role", "report_norm_id_by_source_role"}
_RESULT_FIELDS = {
    "accounting_checks",
    "axis_id",
    "claim_boundary",
    "family_id",
    "format_version",
    "mapping_id",
    "mapping_proposals",
    "metrics",
    "numeric_challenger_observations",
    "safety",
    "schema_binding_spec",
    "schema_graph_ref",
    "status",
    "unresolved_cells",
}
_CHALLENGER_FORMAT_VERSION = "HOSTED_GEMMA4_FULL_PAGE_NUMERIC_CHALLENGER_OBSERVATION_V1"
_CHALLENGER_FIELDS = {
    "crop_ref",
    "extracted_numeric_surface",
    "extraction_json_path",
    "format_version",
    "full_page_render_ref",
    "inference",
    "model",
    "prompt_sha256",
    "response_ref",
    "sample_id",
    "state",
}
_CHALLENGER_RENDER_FIELDS = {"dpi", "pixel_height", "pixel_width", "sha256", "size_bytes"}
_CHALLENGER_INFERENCE = {
    "fresh_context": True,
    "max_output_tokens": 32768,
    "temperature": 0,
    "thinking_level": "MINIMAL",
}
_REF_FIELDS = {"path", "sha256", "size_bytes"}
_DIGEST_REF_FIELDS = {"sha256", "size_bytes"}
_SHA256 = re.compile(r"[0-9a-f]{64}")
_MIXED_POLICY = (
    "REQUIRE_SAME_CROP_SEMANTIC_AGREEMENT_AND_PEER_GROUPING_WITH_ACCOUNTING_IF_AVAILABLE"
)
_SIGNED_CARRYING_POLICY = "POSITIVE_TO_ASSET_NEGATIVE_TO_LIABILITY_ZERO_UNRESOLVED"
_SOLE_NET_POLICY = (
    "WHEN_NO_ATOMIC_CARRYING_LANES_POSITIVE_TO_ASSET_NEGATIVE_TO_LIABILITY_ZERO_UNRESOLVED"
)
_PERIOD_ROLES = {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
_PARSED_CLASSES = {
    "DASH_ZERO",
    "MIXED_GROUPED_INTEGER_CANDIDATE",
    "SIGNED_NUMBER",
}
_ORDINARY_GROUPINGS = {
    "GROUPED_INTEGER_COMMA",
    "GROUPED_INTEGER_POINT",
    "GROUPED_INTEGER_SPACE",
    "NONE",
}


class AccountingStackedPeriodSchemaMappingV1Error(ValueError):
    """The stacked axis, numeric agreement, equation, schema, or replay drifted."""


def _error(message: str) -> AccountingStackedPeriodSchemaMappingV1Error:
    return AccountingStackedPeriodSchemaMappingV1Error(message)


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise _error(f"{label} must be one nonempty string")
    return value


def _spec(value: Any, axis: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _SPEC_FIELDS:
        raise _error("stacked-period schema-binding spec fields drifted")
    if (
        value["format_version"] != SPEC_FORMAT_VERSION
        or value["family_id"] != axis["family_id"]
        or type(value["family_root_report_norm_id"]) is not int
        or value["family_root_report_norm_id"] <= 0
        or value["mixed_grouped_integer_policy"] != _MIXED_POLICY
        or value["schema_period_type"] != "SNAPSHOT"
        or value["signed_carrying_lane_policy"] != _SIGNED_CARRYING_POLICY
        or value["sole_net_carrying_lane_policy"] != _SOLE_NET_POLICY
    ):
        raise _error("stacked-period schema-binding identity drifted")
    lane_roles = {item["role"] for item in axis["lane_axis"]}
    equations = value["accounting_equations"]
    if type(equations) is not list or not equations:
        raise _error("stacked-period schema binding needs accounting alternatives")
    compiled_equations = []
    for raw in equations:
        if (
            type(raw) is not dict
            or set(raw) != _EQUATION_FIELDS
            or type(raw["component_lane_roles"]) is not list
            or len(raw["component_lane_roles"]) < 2
            or any(type(role) is not str or not role for role in raw["component_lane_roles"])
            or len(raw["component_lane_roles"]) != len(set(raw["component_lane_roles"]))
            or type(raw["component_multipliers"]) is not list
            or len(raw["component_multipliers"]) != len(raw["component_lane_roles"])
            or any(
                type(multiplier) is not int or multiplier not in {-1, 1}
                for multiplier in raw["component_multipliers"]
            )
            or type(raw["result_lane_role"]) is not str
            or not raw["result_lane_role"]
            or raw["result_lane_role"] in raw["component_lane_roles"]
        ):
            raise _error("stacked-period accounting equation drifted")
        compiled_equations.append(canonical_clone_v1(raw))
    bindings = value["mapping_bindings"]
    if type(bindings) is not list or not bindings:
        raise _error("stacked-period schema binding needs mapping declarations")
    compiled_bindings = []
    binding_keys: set[tuple[str, str]] = set()
    target_ids: set[int] = set()
    for raw in bindings:
        if (
            type(raw) is not dict
            or set(raw) != _BINDING_FIELDS
            or raw["period_role"] not in _PERIOD_ROLES
            or type(raw["lane_role"]) is not str
            or not raw["lane_role"]
            or type(raw["report_norm_id_by_source_role"]) is not dict
            or not raw["report_norm_id_by_source_role"]
        ):
            raise _error("stacked-period mapping declaration drifted")
        key = (raw["period_role"], raw["lane_role"])
        role_map = raw["report_norm_id_by_source_role"]
        if (
            key in binding_keys
            or any(type(role) is not str or not role for role in role_map)
            or any(type(identity) is not int or identity <= 0 for identity in role_map.values())
            or len(set(role_map.values())) != len(role_map)
            or target_ids.intersection(role_map.values())
        ):
            raise _error("stacked-period mapping key or schema identity repeats")
        binding_keys.add(key)
        target_ids.update(role_map.values())
        compiled_bindings.append(canonical_clone_v1(raw))
    if any(binding["lane_role"] not in lane_roles for binding in compiled_bindings):
        # A filing may omit a configured lane, so compare with the declared
        # layout through mapping eligibility at use time rather than requiring
        # every configured lane to be visible in this particular axis.
        visible_mapping_roles = {
            item["role"] for item in axis["lane_axis"] if item["mapping_eligible"]
        }
        if any(
            binding["lane_role"] in lane_roles and binding["lane_role"] not in visible_mapping_roles
            for binding in compiled_bindings
        ):
            raise _error("configured mapping lane is not mapping-eligible")
    return {
        "accounting_equations": compiled_equations,
        "family_id": value["family_id"],
        "family_root_report_norm_id": value["family_root_report_norm_id"],
        "mapping_bindings": compiled_bindings,
        "schema_period_type": value["schema_period_type"],
        "signed_carrying_lane_policy": value["signed_carrying_lane_policy"],
        "sole_net_carrying_lane_policy": value["sole_net_carrying_lane_policy"],
    }


def _schema(
    value: Any, compiled: Mapping[str, Any]
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    if type(value) not in {list, tuple} or not value:
        raise _error("tracked schema graph must be one nonempty node sequence")
    nodes: dict[int, dict[str, Any]] = {}
    for raw in value:
        if (
            type(raw) is not dict
            or type(raw.get("schema_id")) is not int
            or raw["schema_id"] <= 0
            or type(raw.get("canonical_name")) is not str
            or not raw["canonical_name"]
            or raw.get("parent_id") is not None
            and type(raw["parent_id"]) is not int
            or type(raw.get("allowed_period_type")) is not list
            or type(raw.get("allowed_sign")) is not list
            or type(raw.get("scope")) is not list
            or raw["schema_id"] in nodes
        ):
            raise _error("tracked schema node contract drifted")
        nodes[raw["schema_id"]] = canonical_clone_v1(raw)
    root = compiled["family_root_report_norm_id"]
    if root not in nodes:
        raise _error("stacked-period family root is absent from tracked schema")
    referenced = {
        identity
        for binding in compiled["mapping_bindings"]
        for identity in binding["report_norm_id_by_source_role"].values()
    }
    if any(identity not in nodes for identity in referenced):
        raise _error("stacked-period mapping identity is absent from tracked schema")

    def descends(identity: int) -> bool:
        seen = set()
        while identity not in seen:
            if identity == root:
                return True
            seen.add(identity)
            node = nodes.get(identity)
            if node is None or node["parent_id"] is None:
                return False
            identity = node["parent_id"]
        return False

    for identity in referenced:
        node = nodes[identity]
        if (
            not descends(identity)
            or compiled["schema_period_type"] not in node["allowed_period_type"]
            or not {"CONSOLIDATED", "SEPARATE"}.intersection(node["scope"])
        ):
            raise _error("stacked-period target is incompatible with tracked schema")
    selected = [nodes[identity] for identity in sorted({root, *referenced})]
    return nodes, {
        "node_count": len(selected),
        "sha256": canonical_json_sha256_v1(selected),
    }


def _digest_ref(value: Any, *, fields: set[str], label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != fields
        or type(value["sha256"]) is not str
        or _SHA256.fullmatch(value["sha256"]) is None
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"{label} reference drifted")
    if "path" in fields and (type(value["path"]) is not str or not value["path"]):
        raise _error(f"{label} path drifted")
    return canonical_clone_v1(value)


def _challengers(
    value: Any, source_lines: Mapping[str, Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    if value is None:
        value = ()
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise _error("numeric challenger observations must be one exact sequence")
    result: dict[str, dict[str, Any]] = {}
    for raw in value:
        if type(raw) is not dict or set(raw) != _CHALLENGER_FIELDS:
            raise _error("numeric challenger observation fields drifted")
        sample_id = raw["sample_id"]
        source = source_lines.get(sample_id) if type(sample_id) is str else None
        crop_ref = _digest_ref(raw["crop_ref"], fields=_REF_FIELDS, label="challenger crop")
        render = _digest_ref(
            raw["full_page_render_ref"],
            fields=_CHALLENGER_RENDER_FIELDS,
            label="challenger full-page render",
        )
        response = _digest_ref(
            raw["response_ref"], fields=_DIGEST_REF_FIELDS, label="challenger response"
        )
        if (
            raw["format_version"] != _CHALLENGER_FORMAT_VERSION
            or raw["state"] != "COMPLETED_STATELESS_FULL_PAGE_JSON_CHALLENGE"
            or raw["model"] != "gemma-4-26b-a4b-it"
            or not same_typed_json_v1(raw["inference"], _CHALLENGER_INFERENCE)
            or type(raw["prompt_sha256"]) is not str
            or _SHA256.fullmatch(raw["prompt_sha256"]) is None
            or type(raw["extracted_numeric_surface"]) is not str
            or not raw["extracted_numeric_surface"].strip()
            or type(raw["extraction_json_path"]) is not list
            or not raw["extraction_json_path"]
            or any(type(item) not in {str, int} for item in raw["extraction_json_path"])
            or source is None
            or not same_typed_json_v1(crop_ref, source["crop_ref"])
            or sample_id in result
            or type(render["dpi"]) is not int
            or render["dpi"] != 200
            or type(render["pixel_width"]) is not int
            or render["pixel_width"] <= 0
            or type(render["pixel_height"]) is not int
            or render["pixel_height"] <= 0
        ):
            raise _error("numeric challenger identity or exact input binding drifted")
        challenger = parse_visible_financial_numeric_token_v1(raw["extracted_numeric_surface"])
        if challenger["classification"] not in _PARSED_CLASSES:
            raise _error("numeric challenger did not extract one exact financial number")
        result[sample_id] = {
            **canonical_clone_v1(raw),
            "crop_ref": crop_ref,
            "full_page_render_ref": render,
            "response_ref": response,
            "parsed_token": challenger,
        }
    return result


def _line_by_sample(pages: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for page in pages:
        for line in page["lines"]:
            sample_id = line["sample_id"]
            if sample_id in result:
                raise _error("stacked-period source sample identity repeats")
            result[sample_id] = line
    return result


def _same_number(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    exact = (
        left.get("classification") in _PARSED_CLASSES
        and right.get("classification") in _PARSED_CLASSES
        and type(left.get("coefficient")) is int
        and type(right.get("coefficient")) is int
        and type(left.get("scale")) is int
        and type(right.get("scale")) is int
        and left["coefficient"] == right["coefficient"]
        and left["scale"] == right["scale"]
        and left.get("percentage_mark_present") is right.get("percentage_mark_present")
    )
    if exact:
        return True
    surface = right.get("normalized_token")
    if type(surface) is str and re.fullmatch(r"[0-9sS.:,()\-\s]+", surface):
        repaired_surface = surface.replace("s", "5").replace("S", "5").replace(":", ".")
        if repaired_surface != surface:
            repaired = parse_visible_financial_numeric_token_v1(repaired_surface)
            if (
                repaired["classification"] in _PARSED_CLASSES
                and left.get("classification") in _PARSED_CLASSES
                and repaired["coefficient"] == left.get("coefficient")
                and repaired["scale"] == left.get("scale")
                and repaired["percentage_mark_present"] is left.get("percentage_mark_present")
            ):
                return True
    # VietOCR sometimes preserves every glyph but emits one thousands mark as
    # whitespace (``163.623 724``).  This is not promoted into general numeric
    # authority.  It can only corroborate an already parsed integer from the
    # same crop when one punctuation kind plus whitespace separates complete
    # three-digit groups and the independently read digit/sign sequence is
    # exact.  Mixed dot+comma tokens remain under the stricter accounting gate.
    if (
        left.get("classification") not in _PARSED_CLASSES
        or left.get("scale") != 0
        or left.get("percentage_mark_present") is not False
        or type(left.get("coefficient")) is not int
    ):
        return False
    if type(surface) is not str or not any(character.isspace() for character in surface):
        return False
    token = surface.strip()
    negative = token.startswith("(") and token.endswith(")")
    if negative:
        token = token[1:-1].strip()
    elif token.startswith("-"):
        negative = True
        token = token[1:].strip()
    punctuation = {character for character in token if character in ".,"}
    if len(punctuation) > 1 or not punctuation:
        return False
    groups = re.split(r"[.,\s]+", token)
    if (
        len(groups) < 3
        or not 1 <= len(groups[0]) <= 3
        or any(not group.isdigit() for group in groups)
        or any(len(group) != 3 for group in groups[1:])
    ):
        return False
    coefficient = int("".join(groups))
    if negative and coefficient:
        coefficient = -coefficient
    return coefficient == left["coefficient"]


def _number(value: Mapping[str, Any]) -> tuple[int, int] | None:
    token = value.get("selected_token", value["primary_token"])
    if (
        token["classification"] not in _PARSED_CLASSES
        or type(token["coefficient"]) is not int
        or type(token["scale"]) is not int
    ):
        return None
    return token["coefficient"], token["scale"]


def _sum_equal(
    components: Sequence[tuple[int, int]],
    multipliers: Sequence[int],
    result: tuple[int, int],
) -> bool:
    scale = max([item[1] for item in components], default=result[1])
    scale = max(scale, result[1])
    left = sum(
        multiplier * coefficient * (10 ** (scale - item_scale))
        for multiplier, (coefficient, item_scale) in zip(multipliers, components, strict=True)
    )
    right = result[0] * (10 ** (scale - result[1]))
    return left == right


def _cell_records(
    axis: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    challenger_observations: Any,
) -> tuple[dict[tuple[int, int, str, str], dict[str, Any]], list[dict[str, Any]]]:
    source_lines = _line_by_sample(pages)
    challengers = _challengers(challenger_observations, source_lines)
    cells: dict[tuple[int, int, str, str], dict[str, Any]] = {}
    unresolved = []
    for block in axis["blocks"]:
        for row in block["rows"]:
            for value in row["values"]:
                sample_id = value["sample_id"]
                source = source_lines.get(sample_id)
                if source is None or not same_typed_json_v1(source["crop_ref"], value["crop_ref"]):
                    raise _error("stacked-period mapped cell lost its exact source sample")
                semantic = parse_visible_financial_numeric_token_v1(source["vietocr_text"])
                primary = value["parsed_token"]
                challenger_record = challengers.get(sample_id)
                challenger = (
                    challenger_record["parsed_token"] if challenger_record is not None else None
                )
                primary_semantic_agreement = _same_number(primary, semantic)
                primary_challenger_agreement = challenger is not None and _same_number(
                    primary, challenger
                )
                semantic_challenger_agreement = challenger is not None and _same_number(
                    semantic, challenger
                )
                selected = primary
                selected_surface = value["raw_prediction"]
                consensus = (
                    "PPOCRVIET_EXACT_OR_BOUNDED_GLYPH_AGREEMENT"
                    if primary_semantic_agreement
                    else "PPOCR_GEMMA4_EXACT_AGREEMENT"
                    if primary_challenger_agreement
                    else "VIETOCR_GEMMA4_EXACT_AGREEMENT_PRIMARY_NONINTEGER_OR_INVALID"
                    if (
                        primary["classification"] not in _PARSED_CLASSES
                        or primary.get("scale") != 0
                        or primary.get("percentage_mark_present") is not False
                    )
                    and semantic_challenger_agreement
                    else "NO_TWO_READER_NUMERIC_CONSENSUS"
                )
                if consensus == "VIETOCR_GEMMA4_EXACT_AGREEMENT_PRIMARY_NONINTEGER_OR_INVALID":
                    selected = semantic
                    selected_surface = source["vietocr_text"]
                independent_agreement = consensus != "NO_TWO_READER_NUMERIC_CONSENSUS"
                key = (
                    block["block_ordinal"],
                    row["role_occurrence_ordinal"],
                    row["role"],
                    value["lane_role"],
                )
                if key in cells:
                    raise _error("stacked-period source role/lane cell repeats")
                record = {
                    "bbox": canonical_clone_v1(value["bbox"]),
                    "crop_ref": canonical_clone_v1(value["crop_ref"]),
                    "lane_role": value["lane_role"],
                    "page_sequence": value["page_sequence"],
                    "primary_raw_prediction": value["raw_prediction"],
                    "primary_token": canonical_clone_v1(primary),
                    "role": row["role"],
                    "role_occurrence_ordinal": row["role_occurrence_ordinal"],
                    "independent_numeric_agreement": independent_agreement,
                    "numeric_challenger_observation": (
                        None
                        if challenger_record is None
                        else {
                            key: canonical_clone_v1(item)
                            for key, item in challenger_record.items()
                            if key != "parsed_token"
                        }
                    ),
                    "numeric_consensus_status": consensus,
                    "same_crop_semantic_agreement": primary_semantic_agreement,
                    "sample_id": sample_id,
                    "selected_raw_prediction": selected_surface,
                    "selected_token": canonical_clone_v1(selected),
                    "semantic_raw_prediction": source["vietocr_text"],
                    "semantic_token": semantic,
                }
                cells[key] = record
    return cells, unresolved


def _checks(
    axis: Mapping[str, Any],
    cells: Mapping[tuple[int, int, str, str], Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    checks = []
    for block in axis["blocks"]:
        for row in block["rows"]:
            for equation in equations:
                roles = [*equation["component_lane_roles"], equation["result_lane_role"]]
                selected = [
                    cells.get(
                        (
                            block["block_ordinal"],
                            row["role_occurrence_ordinal"],
                            row["role"],
                            lane_role,
                        )
                    )
                    for lane_role in roles
                ]
                if any(item is None for item in selected):
                    continue
                numbers = [_number(item) for item in selected]
                exact = all(number is not None for number in numbers)
                exact = exact and _sum_equal(
                    numbers[:-1], equation["component_multipliers"], numbers[-1]
                )
                checks.append(
                    {
                        "_exact": exact,
                        "all_same_crop_semantic_agreement": all(
                            item["same_crop_semantic_agreement"] for item in selected
                        ),
                        "all_two_reader_numeric_consensus": all(
                            item["independent_numeric_agreement"] for item in selected
                        ),
                        "block_ordinal": block["block_ordinal"],
                        "component_lane_roles": list(equation["component_lane_roles"]),
                        "component_multipliers": list(equation["component_multipliers"]),
                        "period_role": block["period_role"],
                        "result_lane_role": equation["result_lane_role"],
                        "role": row["role"],
                        "role_occurrence_ordinal": row["role_occurrence_ordinal"],
                        "sample_ids": [item["sample_id"] for item in selected],
                    }
                )
    group_has_exact: dict[tuple[Any, ...], bool] = {}
    for check in checks:
        group = (
            check["block_ordinal"],
            check["role_occurrence_ordinal"],
            check["role"],
            tuple(check["component_lane_roles"]),
            check["result_lane_role"],
        )
        group_has_exact[group] = group_has_exact.get(group, False) or check["_exact"]
    for check in checks:
        group = (
            check["block_ordinal"],
            check["role_occurrence_ordinal"],
            check["role"],
            tuple(check["component_lane_roles"]),
            check["result_lane_role"],
        )
        exact = check.pop("_exact")
        check["status"] = (
            "CORROBORATED_EXACT_VISIBLE_ROW_EQUATION"
            if exact
            else "REJECTED_VISIBLE_ROW_EQUATION_ALTERNATIVE"
            if group_has_exact[group]
            else "VETOED_VISIBLE_ROW_EQUATION_MISMATCH"
        )
    return checks


def _peer_grouping(
    target: Mapping[str, Any], cells: Mapping[Any, Mapping[str, Any]], block_ordinal: int
) -> bool:
    return any(
        other["sample_id"] != target["sample_id"]
        and key[0] == block_ordinal
        and other["lane_role"] == target["lane_role"]
        and other["primary_token"]["classification"] == "SIGNED_NUMBER"
        and other["primary_token"]["scale"] == 0
        and other["primary_token"]["separator_interpretation"] in _ORDINARY_GROUPINGS
        for key, other in cells.items()
    )


def _mapped_cell(
    cell: Mapping[str, Any], node: Mapping[str, Any], *, mixed_rescued: bool
) -> dict[str, Any]:
    token = cell["selected_token"]
    sign = (
        "ZERO"
        if token["coefficient"] == 0
        else "POSITIVE"
        if token["coefficient"] > 0
        else "NEGATIVE"
    )
    if sign not in node["allowed_sign"]:
        raise _error("stacked-period mapped numeric sign is not schema-compatible")
    return {
        "bbox": canonical_clone_v1(cell["bbox"]),
        "crop_ref": canonical_clone_v1(cell["crop_ref"]),
        "mixed_separator_rescued": mixed_rescued,
        "numeric_value": {"coefficient": token["coefficient"], "scale": token["scale"]},
        "numeric_challenger_observation": canonical_clone_v1(
            cell["numeric_challenger_observation"]
        ),
        "numeric_consensus_status": cell["numeric_consensus_status"],
        "page_sequence": cell["page_sequence"],
        "primary_raw_prediction": cell["primary_raw_prediction"],
        "sample_id": cell["sample_id"],
        "selected_numeric_raw_prediction": cell["selected_raw_prediction"],
        "semantic_raw_prediction": cell["semantic_raw_prediction"],
        "source_zero_kind": "VISIBLE_DASH" if token["classification"] == "DASH_ZERO" else None,
    }


def _effective_mapping_lane(
    cell: Mapping[str, Any],
    compiled: Mapping[str, Any],
    visible_lane_roles: set[str],
) -> tuple[str | None, str | None]:
    source_lane = cell["lane_role"]
    sign_split = source_lane == "SIGNED_CARRYING_VALUE"
    if source_lane == "NET_VALUE" and not {
        "ASSET_CARRYING_VALUE",
        "LIABILITY_CARRYING_VALUE",
        "SIGNED_CARRYING_VALUE",
    }.intersection(visible_lane_roles):
        if compiled["sole_net_carrying_lane_policy"] != _SOLE_NET_POLICY:
            raise _error("sole net carrying-value lane policy drifted")
        sign_split = True
    if not sign_split:
        return source_lane, None
    if (
        source_lane == "SIGNED_CARRYING_VALUE"
        and compiled["signed_carrying_lane_policy"] != _SIGNED_CARRYING_POLICY
    ):
        raise _error("signed carrying-value lane policy drifted")
    number = _number(cell)
    if number is None:
        return None, "SIGN_SPLIT_CARRYING_VALUE_IS_NOT_ONE_EXACT_NUMBER"
    coefficient, _scale = number
    if coefficient > 0:
        return "ASSET_CARRYING_VALUE", None
    if coefficient < 0:
        return "LIABILITY_CARRYING_VALUE", None
    return None, "ZERO_SIGN_SPLIT_CARRYING_VALUE_CANNOT_CHOOSE_ASSET_OR_LIABILITY"


def _mappings(
    axis: Mapping[str, Any],
    cells: Mapping[tuple[int, int, str, str], Mapping[str, Any]],
    checks: Sequence[Mapping[str, Any]],
    compiled: Mapping[str, Any],
    nodes: Mapping[int, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bindings = {
        (item["period_role"], item["lane_role"]): item["report_norm_id_by_source_role"]
        for item in compiled["mapping_bindings"]
    }
    checks_by_sample: dict[str, list[Mapping[str, Any]]] = {}
    for check in checks:
        for sample_id in check["sample_ids"]:
            checks_by_sample.setdefault(sample_id, []).append(check)
    proposals = []
    unresolved = []
    visible_lane_roles = {item["role"] for item in axis["lane_axis"]}
    for block in axis["blocks"]:
        for row in block["rows"]:
            for value in row["values"]:
                key = (
                    block["block_ordinal"],
                    row["role_occurrence_ordinal"],
                    row["role"],
                    value["lane_role"],
                )
                cell = cells[key]
                effective_lane, signed_lane_reason = _effective_mapping_lane(
                    cell, compiled, visible_lane_roles
                )
                if signed_lane_reason is not None:
                    unresolved.append(
                        {
                            "lane_role": value["lane_role"],
                            "period_role": block["period_role"],
                            "reason": signed_lane_reason,
                            "role": row["role"],
                            "sample_id": cell["sample_id"],
                        }
                    )
                    continue
                role_map = bindings.get((block["period_role"], effective_lane))
                identity = role_map.get(row["role"]) if role_map is not None else None
                if identity is None:
                    continue
                reasons = []
                related = checks_by_sample.get(cell["sample_id"], [])
                corroborated = any(check["status"].startswith("CORROBORATED") for check in related)
                vetoed = any(check["status"].startswith("VETOED") for check in related)
                if not cell["independent_numeric_agreement"] and not (
                    corroborated and cell["selected_token"]["classification"] == "SIGNED_NUMBER"
                ):
                    reasons.append("SAME_CROP_NUMERIC_READERS_DISAGREE_OR_ARE_UNRESOLVED")
                if vetoed:
                    reasons.append("VISIBLE_ACCOUNTING_EQUATION_VETOED_CELL")
                mixed = cell["primary_token"]["classification"] == "MIXED_GROUPED_INTEGER_CANDIDATE"
                if mixed and not (
                    cell["independent_numeric_agreement"]
                    and _peer_grouping(cell, cells, block["block_ordinal"])
                    and (not related or corroborated)
                ):
                    reasons.append(
                        "MIXED_SEPARATOR_LACKS_AGREEMENT_PEER_OR_AVAILABLE_EXACT_EQUATION"
                    )
                if reasons:
                    unresolved.append(
                        {
                            "lane_role": value["lane_role"],
                            "period_role": block["period_role"],
                            "reason": "+".join(sorted(set(reasons))),
                            "role": row["role"],
                            "sample_id": cell["sample_id"],
                        }
                    )
                    continue
                node = nodes[identity]
                material = {
                    "canonical_name": node["canonical_name"],
                    "lane_role": effective_lane,
                    "mapping_kind": (
                        "DECLARATIVE_PERIOD_ROLE_SIGN_SPLIT_LANE_TO_TRACKED_SCHEMA_PROPOSAL"
                        if value["lane_role"] != effective_lane
                        else "DECLARATIVE_STACKED_PERIOD_ROLE_LANE_TO_TRACKED_SCHEMA_PROPOSAL"
                    ),
                    "numeric_cell": _mapped_cell(cell, node, mixed_rescued=mixed),
                    "period_role": block["period_role"],
                    "report_norm_id": identity,
                    "resolved_period": block["resolved_period"],
                    "role": row["role"],
                    "source_lane_role": value["lane_role"],
                    "source_surface": row["label_match"]["surface"],
                }
                proposals.append(
                    {
                        **material,
                        "item_mapping_id": "aspsmv1:item:" + canonical_json_sha256_v1(material),
                    }
                )
    return proposals, unresolved


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["accounting_checks"]) is not list
        or type(value["mapping_proposals"]) is not list
        or type(value["unresolved_cells"]) is not list
    ):
        raise _error("stacked-period schema-mapping result contract drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("mapping_id")
    if identity != "aspsmv1:mapping:" + canonical_json_sha256_v1(material):
        raise _error("stacked-period schema-mapping identity drifted")
    return canonical_clone_v1(value)


def build_accounting_stacked_period_schema_mapping_v1(
    pages: Any,
    family_topology_spec: Any,
    layout_spec: Any,
    lane_axis: Any,
    schema_binding_spec: Any,
    schema_graph: Any,
    numeric_challenger_observations: Any = (),
) -> dict[str, Any]:
    """Build one exact, source-bound stacked-period schema proposal."""

    axis = lane_axis_v1.validate_accounting_stacked_period_lane_axis_replay_v1(
        lane_axis, pages, family_topology_spec, layout_spec
    )
    parsed_pages = lane_axis_v1.row_axis_v1._pages(pages)
    compiled = _spec(schema_binding_spec, axis)
    nodes, graph_ref = _schema(schema_graph, compiled)
    cells, unresolved = _cell_records(axis, parsed_pages, numeric_challenger_observations)
    checks = _checks(axis, cells, compiled["accounting_equations"])
    proposals, mapping_unresolved = _mappings(axis, cells, checks, compiled, nodes)
    unresolved.extend(mapping_unresolved)
    unique_unresolved = []
    seen_unresolved = set()
    for item in unresolved:
        key = canonical_json_sha256_v1(item)
        if key not in seen_unresolved:
            seen_unresolved.add(key)
            unique_unresolved.append(item)
    material = {
        "accounting_checks": checks,
        "axis_id": axis["axis_id"],
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": axis["family_id"],
        "format_version": FORMAT_VERSION,
        "mapping_proposals": proposals,
        "metrics": {
            "accounting_check_count": len(checks),
            "corroborated_check_count": sum(
                check["status"].startswith("CORROBORATED") for check in checks
            ),
            "mapping_proposal_count": len(proposals),
            "numeric_challenger_rescue_count": len(
                {
                    item["numeric_cell"]["sample_id"]
                    for item in proposals
                    if item["numeric_cell"]["numeric_challenger_observation"] is not None
                    and item["numeric_cell"]["numeric_consensus_status"]
                    in {
                        "PPOCR_GEMMA4_EXACT_AGREEMENT",
                        "VIETOCR_GEMMA4_EXACT_AGREEMENT_PRIMARY_NONINTEGER_OR_INVALID",
                    }
                }
            ),
            "unresolved_cell_count": len(unique_unresolved),
            "vetoed_check_count": sum(check["status"].startswith("VETOED") for check in checks),
        },
        "safety": canonical_clone_v1(_SAFETY),
        "numeric_challenger_observations": canonical_clone_v1(
            list(numeric_challenger_observations or ())
        ),
        "schema_binding_spec": canonical_clone_v1(schema_binding_spec),
        "schema_graph_ref": graph_ref,
        "status": (
            "READY_FOR_SCOPE_UNIT_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
            if proposals
            else "UNRESOLVED_NO_SCHEMA_MAPPING_PROPOSAL"
        ),
        "unresolved_cells": unique_unresolved,
    }
    return _validate_result(
        {**material, "mapping_id": "aspsmv1:mapping:" + canonical_json_sha256_v1(material)}
    )


def validate_accounting_stacked_period_schema_mapping_replay_v1(
    value: Any,
    pages: Any,
    family_topology_spec: Any,
    layout_spec: Any,
    lane_axis: Any,
    schema_binding_spec: Any,
    schema_graph: Any,
    numeric_challenger_observations: Any = (),
) -> dict[str, Any]:
    """Reject coordinated record mutation through complete live rebuilding."""

    persisted = _validate_result(value)
    expected = build_accounting_stacked_period_schema_mapping_v1(
        pages,
        family_topology_spec,
        layout_spec,
        lane_axis,
        schema_binding_spec,
        schema_graph,
        numeric_challenger_observations,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("stacked-period schema mapping does not replay exactly")
    return persisted
