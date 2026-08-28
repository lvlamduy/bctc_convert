"""Investment-securities multi-component closure over selected Gemini JSON.

Gemini remains a source reader.  This engine inventories the selected page
frontier, binds AFS/HTM/quality/VAMC source fragments through declarative
aliases and hierarchy paths, and performs period, unit, subtotal, provision
and total closure locally.  It contains no bank, filename, note-number or page
routing.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    _compile_units,
    _document_unit_context_axis,
    _money,
    _source_table,
    _two_period_axis,
    _unit_axis,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _normalized,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_INVESTMENT_SECURITIES_ACCOUNTING_FAMILY_V1"
INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = (
    "GEMINI_JSON_INDEXED_INVESTMENT_SECURITIES_QUERY_EVIDENCE_V1"
)
EVALUATION_FORMAT_VERSION = "ACCOUNTING_INVESTMENT_SECURITIES_FAMILY_EVALUATION_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_INVESTMENT_SECURITIES_SCHEMA_BINDING_SPEC_V1"
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_INVESTMENT_SECURITIES_"
    "MULTI_COMPONENT_AFS_REQUIRED_HTM_QUALITY_VAMC_OPTIONAL_OWNER_RESET_FENCE_"
    "EXACT_PERIOD_UNIT_HIERARCHY_PARENT_CHILD_PROVISION_TOTAL_ALL_LANE_CLOSURE_"
    "CONDITIONAL_BLANK_ZERO_STRUCTURAL_ROOT_SCHEMA_MAPPING_PROPOSAL_ONLY_NO_"
    "GEOMETRY_OCR_BANK_FILE_PAGE_NOTE_ROUTING_BACKSOLVE_CANONICAL_OR_EXPORT_AUTHORITY"
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")

_STRUCTURAL_ROLES = {"AFS_BRANCH", "HTM_BRANCH", "QUALITY_BRANCH", "VAMC_BRANCH"}
_SOURCE_CONTROL_ROLES = {
    "QUALITY_TOTAL_CONTROL",
    "UNSCOPED_TOTAL_CONTROL",
    "VAMC_NET_TOTAL_CONTROL",
}
_UNMAPPED_SOURCE_ROLES = {
    "HTM_DEBT_GOVERNMENT_GUARANTEED",
    *_SOURCE_CONTROL_ROLES,
}
_GROUP_ROLES = {
    "AFS_DEBT",
    "AFS_EQUITY",
    "AFS_OTHER",
    "AFS_PROVISION",
    "HTM_DEBT",
    "HTM_EQUITY",
    "HTM_OTHER",
    "HTM_PROVISION",
}
_NONADDITIVE_SUBSET_ROLES = {
    "AFS_DEBT_GOVERNMENT_GUARANTEED",
    "HTM_DEBT_GOVERNMENT_GUARANTEED",
}
_OPTIONAL_DIRECT_VIEW_PREFIXES = ("QUALITY_", "VAMC_")
_ACTIVITY_TOKENS = (
    "lai thuan tu mua ban",
    "lo lai thuan tu mua ban",
    "lai lo thuan tu mua ban",
    "bien dong du phong",
    "bien dong trong nam cua du phong",
    "so du dau nam",
    "so du dau ky",
    "hoan nhap trong nam",
    "trich lap trong nam",
    "chi phi du phong",
    "hoan nhap du phong",
    "trich lap du phong",
)


class GeminiJsonInvestmentSecuritiesFamilyV1Error(ValueError):
    """Selected JSON, declarative specs, or investment closure drifted."""


def _error(message: str) -> GeminiJsonInvestmentSecuritiesFamilyV1Error:
    return GeminiJsonInvestmentSecuritiesFamilyV1Error(message)


def _aliases(child: Mapping[str, Any]) -> list[str]:
    return sorted({alias for matcher in child["matchers"] for alias in matcher["aliases"]})


def compile_gemini_json_investment_securities_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile the data-only investment-securities triplet."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("investment-securities topology spec is invalid") from exc
    evaluation_fields = {
        "blank_zero_policy",
        "closure_policy",
        "component_policy",
        "family_id",
        "format_version",
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
        != "EXACT_MULTI_COMPONENT_HIERARCHY_AND_TOTAL_ALL_LANES"
        or evaluation_spec.get("component_policy")
        != "AFS_REQUIRED_HTM_QUALITY_VAMC_OPTIONAL_WITHIN_ONE_OWNER_RESET_FENCE"
        or evaluation_spec.get("period_semantics") != "CURRENT_AND_COMPARATIVE_SNAPSHOT"
        or evaluation_spec.get("typed_control_exclusions")
        != [
            "PRIMARY_FINANCIAL_STATEMENT_SUMMARY",
            "LISTING_STATUS_VIEW",
            "NON_SNAPSHOT_MULTI_MONEY_AXIS_VIEW",
            "PROVISION_MOVEMENT",
            "INVESTMENT_SECURITIES_TRADING_ACTIVITY",
            "INTEREST_RATE_OR_PERCENTAGE_VIEW",
        ]
    ):
        raise _error("investment-securities evaluation spec is invalid")
    try:
        unit_bindings, unit_binding_by_alias = _compile_units(
            evaluation_spec["money_unit_bindings"]
        )
    except ValueError as exc:
        raise _error("investment-securities unit bindings are invalid") from exc

    child_by_role = {child["role"]: child for child in topology["children"]}
    required_structural = _STRUCTURAL_ROLES | _GROUP_ROLES
    if not required_structural <= set(child_by_role):
        raise _error("investment-securities structural role frontier is incomplete")
    matchers_by_role = {
        role: canonical_clone_v1(child["matchers"]) for role, child in child_by_role.items()
    }
    aliases_by_role = {role: _aliases(child) for role, child in child_by_role.items()}

    def structural_ancestors(role: str, seen: frozenset[str] = frozenset()) -> set[str]:
        if role in seen:
            raise _error("investment-securities role ancestry contains a cycle")
        if role in _STRUCTURAL_ROLES:
            return {role}
        result: set[str] = set()
        for matcher in matchers_by_role[role]:
            within = matcher["within_role"]
            if within is not None:
                result.update(structural_ancestors(within, seen | {role}))
        return result

    structural_ancestors_by_role = {
        role: sorted(structural_ancestors(role)) for role in child_by_role
    }

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
        or schema_binding_spec.get("family_root_report_norm_id") != 804
        or schema_binding_spec.get("root_mapping_policy") != "STRUCTURAL_CONTEXT_ONLY"
        or schema_binding_spec.get("schema_period_type") != "SNAPSHOT"
        or type(schema_binding_spec.get("role_bindings")) is not list
    ):
        raise _error("investment-securities schema binding spec is invalid")
    output_roles = set(child_by_role) - _STRUCTURAL_ROLES - _UNMAPPED_SOURCE_ROLES
    bindings: dict[str, int] = {}
    identities = {804}
    for raw in schema_binding_spec["role_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != {"report_norm_id", "role"}
            or raw.get("role") not in output_roles
            or raw["role"] in bindings
            or type(raw.get("report_norm_id")) is not int
            or raw["report_norm_id"] <= 0
            or raw["report_norm_id"] in identities
        ):
            raise _error("investment-securities schema role binding is invalid")
        bindings[raw["role"]] = raw["report_norm_id"]
        identities.add(raw["report_norm_id"])
    if set(bindings) != output_roles:
        raise _error("investment-securities schema binding frontier is incomplete")
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
        # Investment-securities columns are period lanes, not stacked currency
        # lanes.  The shared unit parser still accepts this explicit empty axis
        # so it can apply the same table/column/document unit inventory without
        # assuming a currency label prefix.
        "currency_aliases": {},
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "matchers_by_role": matchers_by_role,
        "output_role_order": [item["role"] for item in schema_binding_spec["role_bindings"]],
        "query_policy": query_policy,
        "schema": canonical_clone_v1(schema_binding_spec),
        "structural_ancestors_by_role": structural_ancestors_by_role,
        "topology": topology,
        "unit_binding_by_alias": unit_binding_by_alias,
        "unit_bindings": unit_bindings,
    }


def _contains_alias(value: Any, alias: str) -> bool:
    text = _normalized(value)
    return bool(text and (text == alias or f" {alias} " in f" {text} "))


def _matches_alias(value: Any, alias: str) -> bool:
    text = _normalized(value)
    if not text:
        return False
    if text == alias or text.startswith(alias + " "):
        return True
    tokens = text.split()
    if tokens[:2] == ["trong", "do"]:
        tokens = tokens[2:]
    while len(tokens) > 1 and (
        tokens[0].isdigit()
        or tokens[0] in {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "a", "b"}
    ):
        tokens.pop(0)
    stripped = " ".join(tokens)
    return stripped == alias or stripped.startswith(alias + " ")


def _surface_axis(section: Mapping[str, Any], table: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = [section.get("title_exact"), table.get("title_exact")]
    narratives = section.get("narratives_exact")
    if type(narratives) is list:
        values.extend(narratives)
    for row in table.get("rows") or []:
        if type(row) is not dict:
            continue
        values.extend(row.get("hierarchy_path_exact") or [])
    return values


def _context_roles(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> set[str]:
    roles: set[str] = set()
    for value in _surface_axis(section, table):
        folded = _normalized(value)
        for role in _STRUCTURAL_ROLES:
            for alias in compiled_specs["aliases_by_role"][role]:
                if not _contains_alias(value, alias):
                    continue
                if role == "VAMC_BRANCH" and "khong bao gom" in folded:
                    continue
                roles.add(role)
    return roles


def _structural_context_supports_role(role: str, contexts: set[str]) -> bool:
    """Return whether a table context binds one structural role unambiguously."""

    if role not in _STRUCTURAL_ROLES or role not in contexts:
        return False
    # AFS and HTM labels often reuse identical child surfaces, so a table that
    # visibly contains both requires row hierarchy evidence.  QUALITY and VAMC
    # are orthogonal typed subviews and can legitimately coexist with their
    # owning AFS/HTM branch in the same section title.
    return (
        role not in {"AFS_BRANCH", "HTM_BRANCH"}
        or not {
            "AFS_BRANCH",
            "HTM_BRANCH",
        }
        <= contexts
    )


def _path_has_role(
    path: Any,
    role: str,
    *,
    compiled_specs: Mapping[str, Any],
    label_exact: Any,
    table_context_roles: set[str],
) -> bool:
    if type(path) is not list:
        return False
    label = _normalized(label_exact)
    ancestors = [value for value in path if type(value) is str and _normalized(value) != label]

    def matches_at(position: int, expected_role: str, seen: frozenset[str]) -> bool:
        if expected_role in seen:
            return False
        value = ancestors[position]
        for matcher in compiled_specs["matchers_by_role"][expected_role]:
            if not any(_matches_alias(value, alias) for alias in matcher["aliases"]):
                continue
            within = matcher["within_role"]
            if within is None:
                return True
            if any(matches_at(prior, within, seen | {expected_role}) for prior in range(position)):
                return True
            # A table-local structural title is sufficient only when it names
            # exactly one family branch.  This preserves flattened tables while
            # preventing identical labels such as "Chứng khoán nợ" from being
            # rebound across AFS and HTM in a combined table.
            if _structural_context_supports_role(within, table_context_roles):
                return True
            # A group surface can carry its own structural branch qualifier
            # even when Gemini omits that branch from hierarchy_path_exact.
            # Example: "Dự phòng ... giữ đến ngày đáo hạn" is intrinsically
            # HTM.  Require an exact declared branch alias on the same surface;
            # never infer this from a generic provision label.
            if within in _STRUCTURAL_ROLES and any(
                _contains_alias(value, alias) for alias in compiled_specs["aliases_by_role"][within]
            ):
                return True
        return False

    return any(matches_at(position, role, frozenset()) for position in range(len(ancestors)))


def _role_match_score(
    row: Mapping[str, Any],
    role: str,
    *,
    table_context_roles: set[str],
    compiled_specs: Mapping[str, Any],
) -> int | None:
    label = row.get("label_exact")
    path = row.get("hierarchy_path_exact")
    scores = []
    for matcher in compiled_specs["matchers_by_role"][role]:
        aliases = [alias for alias in matcher["aliases"] if _matches_alias(label, alias)]
        if not aliases:
            continue
        within = matcher["within_role"]
        if within is None:
            scores.extend(len(_normalized(alias)) for alias in aliases)
            continue
        bound = _path_has_role(
            path,
            within,
            compiled_specs=compiled_specs,
            label_exact=label,
            table_context_roles=table_context_roles,
        ) or _structural_context_supports_role(within, table_context_roles)
        # Some source tables flatten an intermediate group row.  Authenticate
        # that abbreviated lineage generically when the already-matched child
        # alias is under exactly one declared structural branch.  Ambiguous
        # aliases such as a bare "Khác" still match several group roles and are
        # rejected by the row ambiguity gate; branch evidence only prevents an
        # otherwise identical child label from crossing AFS and HTM.
        if not bound and within in _GROUP_ROLES:
            parent_branches = set(compiled_specs["structural_ancestors_by_role"][within])
            branch_visible = len(parent_branches) == 1 and any(
                _path_has_role(
                    path,
                    branch,
                    compiled_specs=compiled_specs,
                    label_exact=label,
                    table_context_roles=table_context_roles,
                )
                or _structural_context_supports_role(branch, table_context_roles)
                for branch in parent_branches
            )
            bound = branch_visible
        branches = set(compiled_specs["structural_ancestors_by_role"][role])
        if len(branches) == 1:
            branch = next(iter(branches))
            branch_visible_in_label = any(
                _contains_alias(label, alias) for alias in compiled_specs["aliases_by_role"][branch]
            )
            if table_context_roles == {branch} or branch_visible_in_label:
                bound = True
        if bound:
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
    if page_json.get("status") == "PRIMARY_FINANCIAL_STATEMENT":
        return "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
    if "tinh trang niem yet" in folded or "thuyet minh ve tinh trang niem yet" in folded:
        return "LISTING_STATUS_VIEW"
    row_labels = [
        _normalized(row.get("label_exact")) for row in table.get("rows") or [] if type(row) is dict
    ]
    activity_surface = " ".join([folded, *row_labels])
    if any(token in activity_surface for token in _ACTIVITY_TOKENS):
        return (
            "INVESTMENT_SECURITIES_TRADING_ACTIVITY"
            if "mua ban" in activity_surface
            else "PROVISION_MOVEMENT"
        )
    if any("chua niem yet" in label for label in row_labels) and any(
        "niem yet" in label and "chua niem yet" not in label for label in row_labels
    ):
        return "LISTING_STATUS_VIEW"
    columns = table.get("columns")
    if (
        type(columns) is list
        and sum(type(column) is dict and column.get("value_kind") == "MONEY" for column in columns)
        > 2
    ):
        return "NON_SNAPSHOT_MULTI_MONEY_AXIS_VIEW"
    if (
        type(columns) is list
        and sum(
            type(column) is dict and column.get("value_kind") == "PERCENT" for column in columns
        )
        > 2
    ):
        return "INTEREST_RATE_OR_PERCENTAGE_VIEW"
    if (
        type(columns) is list
        and not any(
            type(column) is dict and column.get("value_kind") == "MONEY" for column in columns
        )
        and any(
            type(column) is dict and column.get("value_kind") == "PERCENT" for column in columns
        )
    ):
        return "INTEREST_RATE_OR_PERCENTAGE_VIEW"
    return None


def classify_gemini_json_investment_securities_table_v1(
    page_json: Any,
    section: Any,
    table: Any,
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Inventory one table without assigning document-level ownership."""

    if type(page_json) is not dict or type(section) is not dict or type(table) is not dict:
        raise _error("investment-securities source table is invalid")
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        raise _error("investment-securities table axes are invalid")
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    contexts = _context_roles(section, table, compiled_specs=compiled_specs)
    heading = _normalized(
        " ".join(
            value
            for value in (section.get("title_exact"), table.get("title_exact"))
            if type(value) is str
        )
    )
    provision_section = "du phong" in heading and "chung khoan dau tu" in heading
    role_hits = []
    ambiguous_rows = []
    unbound_total_rows: list[tuple[int, Mapping[str, Any]]] = []
    unbound_money_row_ordinals = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        values = row.get("values_exact")
        has_selected_axis = type(values) is list and all(
            1 <= ordinal <= len(values) for ordinal in money_ordinals
        )
        if not has_selected_axis:
            continue
        has_selected_value = any(values[ordinal - 1] is not None for ordinal in money_ordinals)
        scored = [
            (role, score)
            for role in compiled_specs["bindings"]
            if (
                score := _role_match_score(
                    row,
                    role,
                    table_context_roles=contexts,
                    compiled_specs=compiled_specs,
                )
            )
            is not None
        ]
        maximum = max((score for _role, score in scored), default=None)
        matched = [role for role, score in scored if score == maximum]
        if (
            not has_selected_value
            and matched
            and all(
                compiled_specs["child_by_role"][role]["role_kind"]
                not in {"ADDITIVE_CHILD", "NONADDITIVE_CHILD"}
                for role in matched
            )
        ):
            # A blank GROUP/TOTAL row is a structural heading, not a numeric
            # zero observation.  Blank additive/non-additive leaves remain in
            # the inventory and still require an exact equation before zero is
            # emitted.
            continue
        # A declared role with two source-visible blank cells is still part of
        # the family inventory.  It can become zero only after an exact visible
        # equation proves both lanes.  Unlabelled/unmatched all-blank rows carry
        # no numeric family evidence and remain outside the candidate.
        if not matched and not has_selected_value:
            continue
        if not matched:
            if row.get("row_kind") in {"GROUP", "SUBTOTAL", "TOTAL"}:
                unbound_total_rows.append((row_ordinal, row))
            else:
                unbound_money_row_ordinals.append(row_ordinal)
        if len(matched) > 1:
            ambiguous_rows.append(row_ordinal)
        elif matched:
            role = matched[0]
            if provision_section and role in {"AFS_TOTAL", "HTM_TOTAL"}:
                role = role.removesuffix("_TOTAL") + "_PROVISION"
            role_hits.append({"role": role, "row_ordinal": row_ordinal})

    # Gemini sometimes resets hierarchy_path_exact to a generic "Trong đó"
    # node while preserving the immediately preceding typed parent row.  Bind
    # an otherwise-unmatched child only to that nearest source-visible group,
    # never across an intervening subtotal/total boundary.  The child alias and
    # its declared within_role must both agree with the parent.
    recovered_ordinals = []
    total_boundaries = {ordinal for ordinal, _row in unbound_total_rows}
    for row_ordinal in unbound_money_row_ordinals:
        prior_groups = [
            hit
            for hit in role_hits
            if hit["row_ordinal"] < row_ordinal and hit["role"] in _GROUP_ROLES
        ]
        if not prior_groups:
            continue
        parent_hit = max(prior_groups, key=lambda item: item["row_ordinal"])
        if any(parent_hit["row_ordinal"] < ordinal < row_ordinal for ordinal in total_boundaries):
            continue
        row = rows[row_ordinal - 1]
        label = row.get("label_exact")
        scored = []
        for role in compiled_specs["bindings"]:
            aliases = [
                alias
                for matcher in compiled_specs["matchers_by_role"][role]
                if matcher["within_role"] == parent_hit["role"]
                for alias in matcher["aliases"]
                if _matches_alias(label, alias)
            ]
            if aliases:
                scored.append((role, max(map(len, aliases))))
        maximum = max((score for _role, score in scored), default=None)
        matched = [role for role, score in scored if score == maximum]
        if len(matched) == 1:
            role_hits.append({"role": matched[0], "row_ordinal": row_ordinal})
            recovered_ordinals.append(row_ordinal)
        elif len(matched) > 1:
            ambiguous_rows.append(row_ordinal)
            recovered_ordinals.append(row_ordinal)
    if recovered_ordinals:
        recovered = set(recovered_ordinals)
        unbound_money_row_ordinals = [
            ordinal for ordinal in unbound_money_row_ordinals if ordinal not in recovered
        ]
    core_branches = {
        prefix
        for prefix in ("AFS", "HTM")
        if any(
            hit["role"].startswith(prefix + "_")
            and not hit["role"].startswith(prefix + "_PROVISION")
            for hit in role_hits
        )
    }
    for row_ordinal, row in unbound_total_rows:
        # Prefer the nearest typed group visible in the source hierarchy.  A
        # blank-labelled subtotal under DEBT/EQUITY/OTHER/PROVISION is that
        # group's source total, not the whole AFS/HTM branch total.  Only fall
        # back to the branch total when no unique group frontier is visible.
        group_candidates = {
            role
            for role in _GROUP_ROLES
            if _path_has_role(
                row.get("hierarchy_path_exact"),
                role,
                compiled_specs=compiled_specs,
                label_exact=row.get("label_exact"),
                table_context_roles=contexts,
            )
        }
        # An anonymous subtotal nested below a provision label is ambiguous at
        # the source-reader boundary: it may be the provision subtotal, but it
        # is also the conventional presentation of the branch carrying amount
        # after provision.  Keep it as a branch/control total and let the exact
        # equations below decide.  A labelled provision row remains the typed
        # provision parent.
        if len(group_candidates) == 1 and not (
            not _normalized(row.get("label_exact"))
            and next(iter(group_candidates)).endswith("_PROVISION")
        ):
            role_hits.append({"role": next(iter(group_candidates)), "row_ordinal": row_ordinal})
            continue
        path_branches = {
            prefix
            for prefix in ("AFS", "HTM")
            if _path_has_role(
                row.get("hierarchy_path_exact"),
                prefix + "_BRANCH",
                compiled_specs=compiled_specs,
                label_exact=row.get("label_exact"),
                table_context_roles=contexts,
            )
        }
        candidates = path_branches or core_branches
        if len(candidates) == 1:
            role_hits.append(
                {"role": next(iter(candidates)) + "_TOTAL", "row_ordinal": row_ordinal}
            )
            continue
        current_roles = {hit["role"] for hit in role_hits}
        if "QUALITY_BRANCH" in contexts and any(
            role.startswith("QUALITY_") for role in current_roles
        ):
            role_hits.append({"role": "QUALITY_TOTAL_CONTROL", "row_ordinal": row_ordinal})
        elif (
            "VAMC_BRANCH" in contexts
            and any(role.startswith("VAMC_") for role in current_roles)
            and not any(role.startswith(("AFS_", "HTM_")) for role in current_roles)
        ):
            role_hits.append({"role": "VAMC_NET_TOTAL_CONTROL", "row_ordinal": row_ordinal})
        elif role_hits:
            role_hits.append({"role": "UNSCOPED_TOTAL_CONTROL", "row_ordinal": row_ordinal})
    hit_roles = {hit["role"] for hit in role_hits}
    component_roles = sorted(
        {"AFS" for role in hit_roles if role.startswith("AFS_")}
        | {"HTM" for role in hit_roles if role.startswith("HTM_")}
        | {"QUALITY" for role in hit_roles if role.startswith("QUALITY_")}
        | {"VAMC" for role in hit_roles if role.startswith("VAMC_")}
    )
    control = _typed_control_disposition(page_json, section, table)
    reasons = []
    if len(money_ordinals) != 2 and role_hits:
        reasons.append("SNAPSHOT_COMPONENT_REQUIRES_EXACTLY_TWO_MONEY_COLUMNS")
    if ambiguous_rows:
        reasons.append("SOURCE_ROW_ROLE_MATCH_IS_AMBIGUOUS")
    if unbound_money_row_ordinals:
        reasons.append("UNBOUND_MONEY_ROW_IN_DECLARED_FAMILY_TABLE")
    detail_roles = {
        role for role in hit_roles if role not in {"AFS_TOTAL", "HTM_TOTAL", *_SOURCE_CONTROL_ROLES}
    }
    summary_only = bool(hit_roles) and not detail_roles
    if control is not None:
        disposition = "EXCLUDED_TYPED_CONTROL:" + control
    elif role_hits and len(money_ordinals) == 2 and not reasons and not summary_only:
        disposition = "ACTIVE_SNAPSHOT_COMPONENT"
    elif role_hits and summary_only:
        disposition = "EXCLUDED_SUMMARY_ONLY_CONTROL"
    elif role_hits:
        disposition = "DECLARED_ROLE_TABLE_NOT_USABLE"
    else:
        disposition = "NO_DECLARED_ROLE_POPULATION"
    return {
        "ambiguous_row_ordinals": ambiguous_rows,
        "component_roles": component_roles,
        "contexts": sorted(contexts),
        "disposition": disposition,
        "money_column_ordinals": money_ordinals,
        "reasons": sorted(set(reasons)),
        "role_hits": role_hits,
        "unbound_money_row_ordinals": unbound_money_row_ordinals,
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
        raise _error("investment-securities selected page records are absent")
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
            raise _error("investment-securities selected page record is invalid")
        current_identity = tuple(
            raw[key]
            for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (raw["selected_page_ordinal"], raw["physical_page"])
        if identity is None:
            identity = current_identity
        elif identity != current_identity:
            raise _error("investment-securities selected pages cross document identity")
        if prior is not None and position <= prior:
            raise _error("investment-securities selected pages are not in source order")
        prior = position
        checked.append(canonical_clone_v1(raw))
    return checked


def _region(item: Mapping[str, Any], fragment_ordinal: int) -> dict[str, Any]:
    record = item["record"]
    return {
        "component_roles": canonical_clone_v1(item["classification"]["component_roles"]),
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


def _marker_matches(value: Any, aliases: Sequence[str]) -> str | None:
    matches = [alias for alias in aliases if _contains_alias(value, alias)]
    if not matches:
        return None
    maximum = max(map(len, matches))
    winners = sorted(alias for alias in matches if len(alias) == maximum)
    return winners[0] if len(winners) == 1 else None


def coalesce_gemini_json_investment_securities_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select every usable component in one generic owner/reset interval."""

    pages = _page_record_axis(page_records)
    inventory = []
    reset_markers = []
    owner_markers = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if type(section) is not dict:
                continue
            section_id = f"s{section_ordinal}"
            section_values = [section.get("title_exact")]
            narratives = section.get("narratives_exact")
            if type(narratives) is list:
                section_values.extend(narratives)
            for value in section_values:
                owner = _marker_matches(value, compiled_specs["query_policy"]["owner_aliases"])
                reset = _marker_matches(value, compiled_specs["query_policy"]["reset_aliases"])
                position = [record["selected_page_ordinal"], section_ordinal, 0]
                if owner is not None:
                    owner_markers.append(
                        {"alias": owner, "position": position, "source_exact": value}
                    )
                if reset is not None:
                    reset_markers.append(
                        {"alias": reset, "position": position, "source_exact": value}
                    )
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, table in enumerate(tables, start=1):
                if type(table) is not dict:
                    continue
                table_id = f"t{table_ordinal}"
                position = [record["selected_page_ordinal"], section_ordinal, table_ordinal]
                for value in (table.get("title_exact"),):
                    owner = _marker_matches(value, compiled_specs["query_policy"]["owner_aliases"])
                    reset = _marker_matches(value, compiled_specs["query_policy"]["reset_aliases"])
                    if owner is not None:
                        owner_markers.append(
                            {"alias": owner, "position": position, "source_exact": value}
                        )
                    if reset is not None:
                        reset_markers.append(
                            {"alias": reset, "position": position, "source_exact": value}
                        )
                classification = classify_gemini_json_investment_securities_table_v1(
                    record["page_json"], section, table, compiled_specs=compiled_specs
                )
                if classification["role_hits"]:
                    inventory.append(
                        {
                            "classification": classification,
                            "position": position,
                            "record": record,
                            "section_id": section_id,
                            "table_id": table_id,
                        }
                    )
    active = [
        item
        for item in inventory
        if item["classification"]["disposition"] == "ACTIVE_SNAPSHOT_COMPONENT"
    ]
    reasons = []
    afs_core = [
        item
        for item in active
        if any(
            hit["role"].startswith("AFS_")
            and hit["role"]
            not in {
                "AFS_PROVISION",
                "AFS_PROVISION_PRICE",
                "AFS_PROVISION_GENERAL",
                "AFS_PROVISION_SPECIFIC",
            }
            for hit in item["classification"]["role_hits"]
        )
    ]
    if not afs_core:
        if inventory:
            reasons.append("AFS_DETAIL_COMPONENT_NOT_RESOLVED")
    if active:
        first = min(item["position"] for item in active)
        last = max(item["position"] for item in active)
        if last[0] - first[0] > 5:
            reasons.append("INVESTMENT_SECURITIES_COMPONENT_SPAN_EXCEEDS_DECLARED_BOUND")
        for item in active:
            prior_resets = [
                marker for marker in reset_markers if marker["position"] < item["position"]
            ]
            if not prior_resets:
                continue
            latest_reset = max(prior_resets, key=lambda marker: marker["position"])
            local_owners = [
                marker
                for marker in owner_markers
                if latest_reset["position"] < marker["position"] <= item["position"]
            ]
            if not local_owners:
                reasons.append("COMPONENT_CROSSES_RESET_WITHOUT_LOCAL_OWNER")
    selected_keys = {
        (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
        for item in active
    }
    declared_inventory = []
    for item in inventory:
        key = (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
        disposition = item["classification"]["disposition"]
        if key in selected_keys:
            disposition = "SELECTED_FAMILY_COMPONENT"
        elif disposition == "DECLARED_ROLE_TABLE_NOT_USABLE":
            reasons.append("UNUSABLE_DECLARED_ROLE_TABLE_IN_SELECTED_DOCUMENT")
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
    regions = [_region(item, ordinal) for ordinal, item in enumerate(active, start=1)]
    owner = None
    if active:
        prior = [marker for marker in owner_markers if marker["position"] <= active[0]["position"]]
        owner = (
            max(prior, key=lambda item: item["position"])
            if prior
            else {
                "alias": None,
                "position": active[0]["position"],
                "source_exact": None,
                "source_kind": "UNIQUE_AFS_COMPONENT_IMPLIED_OWNER",
            }
        )
    status = (
        READY if regions and afs_core and not reasons else UNRESOLVED if inventory else NOT_OBSERVED
    )
    material = {
        "component_regions": regions if status == READY else [],
        "declared_role_table_inventory": declared_inventory,
        "document_id": pages[0]["document_id"],
        "document_ordinal": pages[0]["document_ordinal"],
        "owner_receipt": owner,
        "reasons": sorted(set(reasons)),
        "source_logical_name": pages[0]["source_logical_name"],
        "source_sha256": pages[0]["source_sha256"],
        "status": status,
    }
    return {
        **material,
        "cluster_id": "gjfisfcv1:cluster:" + canonical_json_sha256_v1(material),
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
        raise _error("investment-securities region axis cardinality is invalid")
    checked = []
    identity = None
    prior = None
    for ordinal, raw in enumerate(regions, start=1):
        if (
            type(raw) is not dict
            or set(raw) != fields
            or type(raw.get("component_roles")) is not list
            or not raw["component_roles"]
            or raw["component_roles"] != sorted(set(raw["component_roles"]))
            or any(role not in {"AFS", "HTM", "QUALITY", "VAMC"} for role in raw["component_roles"])
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
            raise _error("investment-securities region is invalid")
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
            raise _error("investment-securities regions cross document identity")
        if prior is not None and position <= prior:
            raise _error("investment-securities regions are not in source order")
        prior = position
        checked.append(canonical_clone_v1(raw))
    return checked


def build_gemini_json_investment_securities_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    checked = _region_axis(regions)
    return {
        "component_role_axis": [item["component_roles"] for item in checked],
        "exact_fragment_axis_sha256": canonical_json_sha256_v1(checked),
        "exact_fragment_count": len(checked),
        "format_version": "GEMINI_JSON_INVESTMENT_SECURITIES_REGION_QUERY_RECEIPT_V1",
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


def _source_money(value: Any) -> dict[str, Any]:
    try:
        return _money(value)
    except ValueError:
        if type(value) is not str:
            raise
        body = value.strip()
        dashes = "-–—−"
        # Some sealed Gemini pages attach a non-Latin continuation annotation
        # between two visible dash glyphs (for example ``-接着-``).  Preserve
        # that raw evidence as a conditional zero; it becomes usable only when
        # an independent complete accounting equation proves the lane exactly.
        if (
            len(body) >= 2
            and body[0] in dashes
            and body[-1] in dashes
            and not any(character.isdigit() for character in body)
            and not re.search(r"[A-Za-zÀ-ỹ]", body)
        ):
            return {
                "coefficient": 0,
                "source_text": value,
                "state": "ANNOTATED_DASH_ZERO_IF_EQUATION_EXACT",
            }
        if body and all(character in "-–—−_:|·." or character.isspace() for character in body):
            return {
                "coefficient": 0,
                "source_text": value,
                "state": "PUNCTUATION_PLACEHOLDER_ZERO_IF_EQUATION_EXACT",
            }
        raise


def _record(
    role: str, cells: list[dict[str, Any]], source_refs: list[dict[str, Any]], state: str
) -> dict[str, Any]:
    return {
        "cells": canonical_clone_v1(cells),
        "role": role,
        "source_refs": canonical_clone_v1(source_refs),
        "state": state,
    }


def _aggregate(role: str, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return _record(
        role,
        [
            {
                "coefficient": sum(record["cells"][lane]["coefficient"] for record in records),
                "source_text": None,
                "state": "DERIVED_EXACT_SUM_OF_SOURCE_ROWS",
            }
            for lane in range(2)
        ],
        [ref for record in records for ref in record["source_refs"]],
        "DERIVED_EXACT_SUM_OF_SOURCE_ROWS",
    )


def _corroborate_identical(
    role: str, records: Sequence[Mapping[str, Any]]
) -> dict[str, Any] | None:
    if not records:
        return None
    coefficient_axis = {tuple(_coefficients(record)) for record in records}
    state = "CORROBORATED_IDENTICAL_SOURCE_ROWS"
    if len(coefficient_axis) == 1:
        selected = records[0]
    elif (
        "PROVISION" in role
        and len({tuple(abs(value) for value in _coefficients(record)) for record in records}) == 1
    ):
        # Provision schedules often print the same balance as a positive
        # absolute amount while the carrying-value table prints it in
        # parentheses.  Absolute equality on every lane proves that these are
        # corroborating presentations, not two additive populations.  Prefer
        # the source-signed observation so downstream gross/net equations keep
        # their accounting sign.
        signed = [
            record
            for record in records
            if all(value <= 0 for value in _coefficients(record))
            and any(value < 0 for value in _coefficients(record))
        ]
        if not signed or len({tuple(_coefficients(record)) for record in signed}) != 1:
            return None
        selected = signed[0]
        state = "CORROBORATED_ABSOLUTE_AND_SOURCE_SIGNED_PROVISION_ROWS"
    else:
        return None
    if len(records) == 1:
        return canonical_clone_v1(records[0])
    return _record(
        role,
        canonical_clone_v1(selected["cells"]),
        [ref for record in records for ref in record["source_refs"]],
        state,
    )


def _coefficients(record: Mapping[str, Any]) -> list[int]:
    return [cell["coefficient"] for cell in record["cells"]]


def _equation(
    *,
    equation_kind: str,
    components: Sequence[Mapping[str, Any]],
    result: Mapping[str, Any],
    multipliers: Sequence[int] | None = None,
) -> dict[str, Any]:
    weights = list(multipliers) if multipliers is not None else [1] * len(components)
    sums = [
        sum(
            weight * record["cells"][lane]["coefficient"]
            for record, weight in zip(components, weights, strict=True)
        )
        for lane in range(2)
    ]
    result_values = _coefficients(result)
    material = {
        "component_roles": [record["role"] for record in components],
        "component_source_refs": [
            canonical_clone_v1(record["source_refs"]) for record in components
        ],
        "component_sums": sums,
        "equation_kind": equation_kind,
        "multipliers": weights,
        "result_coefficients": result_values,
        "result_role": result["role"],
        "result_source_refs": canonical_clone_v1(result["source_refs"]),
        "status": "EXACT" if sums == result_values else "MISMATCH",
    }
    return {**material, "equation_id": "gjfisev1:equation:" + canonical_json_sha256_v1(material)}


def _parent_children(role: str) -> list[str]:
    declared = {
        "AFS_DEBT": [
            "AFS_DEBT_GOVERNMENT",
            "AFS_DEBT_CREDIT_INSTITUTIONS",
            "AFS_DEBT_DOMESTIC_ECONOMIC_ORGANIZATIONS",
            "AFS_DEBT_FOREIGN_ECONOMIC_ORGANIZATIONS",
            "AFS_DEBT_OTHER",
        ],
        "AFS_EQUITY": [
            "AFS_EQUITY_GOVERNMENT",
            "AFS_EQUITY_CREDIT_INSTITUTIONS",
            "AFS_EQUITY_DOMESTIC_ECONOMIC_ORGANIZATIONS",
            "AFS_EQUITY_FOREIGN_ECONOMIC_ORGANIZATIONS",
            "AFS_EQUITY_OTHER",
        ],
        "AFS_OTHER": [
            "AFS_OTHER_GOVERNMENT",
            "AFS_OTHER_CREDIT_INSTITUTIONS",
            "AFS_OTHER_DOMESTIC_ECONOMIC_ORGANIZATIONS",
            "AFS_OTHER_FOREIGN_ECONOMIC_ORGANIZATIONS",
            "AFS_OTHER_OTHER",
        ],
        "AFS_PROVISION": [
            "AFS_PROVISION_PRICE",
            "AFS_PROVISION_GENERAL",
            "AFS_PROVISION_SPECIFIC",
        ],
        "HTM_DEBT": [
            "HTM_DEBT_GOVERNMENT",
            "HTM_DEBT_CREDIT_INSTITUTIONS",
            "HTM_DEBT_DOMESTIC_ECONOMIC_ORGANIZATIONS",
            "HTM_DEBT_FOREIGN_ECONOMIC_ORGANIZATIONS",
            "HTM_DEBT_OTHER",
        ],
        "HTM_EQUITY": [
            "HTM_EQUITY_GOVERNMENT",
            "HTM_EQUITY_CREDIT_INSTITUTIONS",
            "HTM_EQUITY_DOMESTIC_ECONOMIC_ORGANIZATIONS",
            "HTM_EQUITY_FOREIGN_ECONOMIC_ORGANIZATIONS",
            "HTM_EQUITY_OTHER",
        ],
        "HTM_OTHER": [
            "HTM_OTHER_GOVERNMENT",
            "HTM_OTHER_CREDIT_INSTITUTIONS",
            "HTM_OTHER_DOMESTIC_ECONOMIC_ORGANIZATIONS",
            "HTM_OTHER_FOREIGN_ECONOMIC_ORGANIZATIONS",
            "HTM_OTHER_OTHER",
        ],
        "HTM_PROVISION": [
            "HTM_PROVISION_PRICE",
            "HTM_PROVISION_GENERAL",
            "HTM_PROVISION_SPECIFIC",
        ],
    }
    return declared[role]


def _record_is_within_role(
    record: Mapping[str, Any], role: str, *, compiled_specs: Mapping[str, Any]
) -> bool:
    contexts = set(compiled_specs["structural_ancestors_by_role"][role])
    if role in {"HTM_DEBT", "HTM_PROVISION"} and any(
        "HTM" in ref["locator"].get("component_roles", [])
        and "AFS" not in ref["locator"].get("component_roles", [])
        for ref in record["source_refs"]
    ):
        # A standalone HTM table may flatten VAMC face/provision rows without
        # an intermediate HTM hierarchy node.  The exact selected fragment is
        # nevertheless typed HTM+VAMC and cannot cross-bind to AFS.  Combined
        # AFS/HTM tables still require their row hierarchy below.
        return True
    return any(
        _path_has_role(
            ref.get("hierarchy_path_exact"),
            role,
            compiled_specs=compiled_specs,
            label_exact=ref.get("label_exact"),
            table_context_roles=contexts,
        )
        for ref in record["source_refs"]
    )


def _child_records(
    parent: str,
    records: Mapping[str, dict[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    children = [records[role] for role in _parent_children(parent) if role in records]
    if parent == "AFS_DEBT" and "AFS_DEBT_GOVERNMENT_GUARANTEED" in records:
        guaranteed = records["AFS_DEBT_GOVERNMENT_GUARANTEED"]
        subset_visible = any(
            "trong do" in _normalized(value)
            for ref in guaranteed["source_refs"]
            for value in [ref.get("label_exact"), *(ref.get("hierarchy_path_exact") or [])]
            if type(value) is str
        )
        if not subset_visible:
            children.append(guaranteed)
    for cross_role in (
        ["VAMC_FACE_VALUE"]
        if parent == "HTM_DEBT"
        else ["VAMC_PROVISION"]
        if parent == "HTM_PROVISION"
        else []
    ):
        if cross_role in records and _record_is_within_role(
            records[cross_role], parent, compiled_specs=compiled_specs
        ):
            children.append(records[cross_role])
    return children


def _top_component_records(
    prefix: str,
    records: Mapping[str, dict[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    selected = []
    for parent in (f"{prefix}_DEBT", f"{prefix}_EQUITY", f"{prefix}_OTHER"):
        if parent in records:
            selected.append(records[parent])
        else:
            selected.extend(_child_records(parent, records, compiled_specs=compiled_specs))
    return selected


def evaluate_gemini_json_investment_securities_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one exact multi-table investment-securities cluster."""

    region_axis = _region_axis(regions)
    expected_receipt = build_gemini_json_investment_securities_region_query_receipt_v1(region_axis)
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected_receipt):
        raise _error("investment-securities query receipt does not bind exact fragments")
    document_unit_context = _document_unit_context_axis(
        page_json_by_version, compiled_specs=compiled_specs
    )
    raw_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    table_receipts = []
    reasons = []
    period_signatures = []
    units = []
    for region in region_axis:
        page_json = page_json_by_version.get(region["page_json_version_id"])
        if type(page_json) is not dict:
            raise _error("investment-securities selected page JSON is absent")
        section, table = _source_table(
            page_json, section_id=region["section_id"], table_id=region["table_id"]
        )
        classification = classify_gemini_json_investment_securities_table_v1(
            page_json, section, table, compiled_specs=compiled_specs
        )
        if (
            classification["disposition"] != "ACTIVE_SNAPSHOT_COMPONENT"
            or classification["component_roles"] != region["component_roles"]
            or classification["reasons"]
        ):
            raise _error("investment-securities source fragment classification drifted")
        period_axis = _two_period_axis(table)
        unit_axis = _unit_axis(
            table,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
        if not period_axis["complete"]:
            reasons.extend(period_axis["reasons"])
        else:
            period_signatures.append(period_axis["signatures"])
        if not unit_axis["complete"]:
            reasons.extend(unit_axis["reasons"])
        else:
            units.append(unit_axis["canonical_unit"])
        money_ordinals = classification["money_column_ordinals"]
        for hit in classification["role_hits"]:
            row = table["rows"][hit["row_ordinal"] - 1]
            values = row.get("values_exact")
            if type(values) is not list:
                reasons.append(f"ROLE_VALUE_AXIS_IS_INVALID:{hit['role']}")
                continue
            try:
                cells = [_source_money(values[ordinal - 1]) for ordinal in money_ordinals]
            except ValueError:
                reasons.append(f"ROLE_MONEY_CELL_IS_INVALID:{hit['role']}")
                continue
            raw_records[hit["role"]].append(
                _record(
                    hit["role"],
                    cells,
                    [_source_ref(region, hit["row_ordinal"], row)],
                    "SOURCE_OBSERVED_ROW",
                )
            )
        table_receipts.append(
            {
                "classification": classification,
                "period_axis": period_axis,
                "region": canonical_clone_v1(region),
                "unit_axis": unit_axis,
            }
        )
    if (
        period_signatures
        and len({canonical_json_sha256_v1(item) for item in period_signatures}) != 1
    ):
        reasons.append("COMPONENT_PERIOD_AXES_DIFFER")
    if units and set(units) != {"MILLION_VND"}:
        reasons.append("COMPONENT_MONEY_UNITS_DIFFER_OR_ARE_NOT_MILLION_VND")
    raw_total_records = {role: raw_records.pop(role, []) for role in ("AFS_TOTAL", "HTM_TOTAL")}
    raw_control_records = {
        role: raw_records.pop(role, []) for role in sorted(_SOURCE_CONTROL_ROLES)
    }
    records = {}
    for role, values in raw_records.items():
        # A source may print the same semantic group both as a labelled group
        # row and as an immediately following blank-labelled subtotal.  Equal
        # observations corroborate one value; distinct rows remain additive
        # populations.  Never double-count byte-distinct source receipts merely
        # because Gemini preserved both structural rows.
        corroborated = _corroborate_identical(role, values)
        records[role] = corroborated if corroborated is not None else _aggregate(role, values)
    equations = []
    proven_roles: set[str] = set()

    quality_records = [
        records[role]
        for role in (
            "QUALITY_STANDARD",
            "QUALITY_WATCH",
            "QUALITY_SUBSTANDARD",
            "QUALITY_DOUBTFUL",
            "QUALITY_LOSS",
        )
        if role in records
    ]
    for control in raw_control_records["QUALITY_TOTAL_CONTROL"]:
        equation = _equation(
            equation_kind="EXACT_VISIBLE_QUALITY_ROWS_EQUAL_SOURCE_TOTAL",
            components=quality_records,
            result=control,
        )
        equations.append(equation)
        if equation["status"] == "EXACT":
            proven_roles.update(record["role"] for record in quality_records)
        else:
            reasons.append("QUALITY_VISIBLE_TOTAL_DOES_NOT_CLOSE_ROLE_FRONTIER")

    vamc_records = [
        records[role] for role in ("VAMC_FACE_VALUE", "VAMC_PROVISION") if role in records
    ]
    for control in raw_control_records["VAMC_NET_TOTAL_CONTROL"]:
        variants = [
            _equation(
                equation_kind="EXACT_VISIBLE_VAMC_NET_WITH_SOURCE_SIGNED_PROVISION",
                components=vamc_records,
                result=control,
            )
        ]
        if len(vamc_records) == 2:
            variants.append(
                _equation(
                    equation_kind="EXACT_VISIBLE_VAMC_NET_LESS_POSITIVE_PROVISION",
                    components=vamc_records,
                    result=control,
                    multipliers=[1, -1],
                )
            )
        exact_variants = [item for item in variants if item["status"] == "EXACT"]
        equations.append(exact_variants[0] if exact_variants else variants[0])
        if exact_variants:
            proven_roles.update(record["role"] for record in vamc_records)
        else:
            reasons.append("VAMC_VISIBLE_NET_TOTAL_DOES_NOT_CLOSE_ROLE_FRONTIER")
    for parent in sorted(_GROUP_ROLES - {"AFS_PROVISION", "HTM_PROVISION"}):
        if parent in records:
            continue
        children = _child_records(parent, records, compiled_specs=compiled_specs)
        if len(children) < 3:
            continue
        aggregate_candidates = []
        for candidate in children:
            if len(candidate["source_refs"]) != 1:
                continue
            candidate_ref = candidate["source_refs"][0]
            locator = candidate_ref["locator"]
            others = [record for record in children if record is not candidate]
            other_refs = [ref for record in others for ref in record["source_refs"]]
            if (
                not other_refs
                or any(
                    tuple(
                        ref["locator"][key]
                        for key in ("page_json_version_id", "section_id", "table_id")
                    )
                    != tuple(
                        locator[key] for key in ("page_json_version_id", "section_id", "table_id")
                    )
                    for ref in other_refs
                )
                or candidate_ref["row_ordinal"] <= max(ref["row_ordinal"] for ref in other_refs)
            ):
                continue
            equation = _equation(
                equation_kind="EXACT_TRAILING_SOURCE_ROW_IS_SIBLING_GROUP_AGGREGATE",
                components=others,
                result=candidate,
            )
            if equation["status"] == "EXACT":
                aggregate_candidates.append((candidate, others))
        if len(aggregate_candidates) == 1:
            candidate, _others = aggregate_candidates[0]
            del records[candidate["role"]]
            records[parent] = _record(
                parent,
                candidate["cells"],
                candidate["source_refs"],
                "SOURCE_ROW_RECLASSIFIED_AS_EXACT_TRAILING_GROUP_AGGREGATE",
            )
    for parent in sorted(_GROUP_ROLES):
        children = _child_records(parent, records, compiled_specs=compiled_specs)
        if not children:
            continue
        if parent not in records and parent.endswith("_PROVISION"):
            records[parent] = _aggregate(parent, children)
            equation = _equation(
                equation_kind="DERIVED_PROVISION_PARENT_EQUALS_EXHAUSTIVE_VISIBLE_CHILDREN",
                components=children,
                result=records[parent],
            )
            equations.append(equation)
            proven_roles.update({parent, *(record["role"] for record in children)})
            continue
        if parent not in records:
            continue
        variants = [
            _equation(
                equation_kind="EXACT_VISIBLE_PARENT_EQUALS_EXHAUSTIVE_ADDITIVE_CHILDREN",
                components=children,
                result=records[parent],
            )
        ]
        if parent.endswith("_PROVISION"):
            variants.append(
                _equation(
                    equation_kind="EXACT_SIGNED_PROVISION_PARENT_EQUALS_NEGATED_DETAIL_CHILDREN",
                    components=children,
                    result=records[parent],
                    multipliers=[-1] * len(children),
                )
            )
        exact_variants = [equation for equation in variants if equation["status"] == "EXACT"]
        if exact_variants:
            equation = exact_variants[0]
            equations.append(equation)
            proven_roles.update({parent, *(record["role"] for record in children)})
        else:
            equations.append(variants[0])
            reasons.append(f"PARENT_CHILD_EQUATION_MISMATCH:{parent}")
    for prefix in ("AFS", "HTM"):
        total_role = f"{prefix}_TOTAL"
        component_records = _top_component_records(prefix, records, compiled_specs=compiled_specs)
        if not component_records:
            if prefix == "AFS":
                reasons.append("AFS_DIRECT_COMPONENT_FRONTIER_IS_EMPTY")
            continue
        total_candidates = raw_total_records[total_role]
        provision_role = f"{prefix}_PROVISION"
        gross_matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
        net_matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
        all_candidate_equations = []
        for total in total_candidates:
            gross = _equation(
                equation_kind="EXACT_VISIBLE_GROSS_COMPONENT_TOTAL",
                components=component_records,
                result=total,
            )
            all_candidate_equations.append(gross)
            if gross["status"] == "EXACT":
                gross_matches.append((total, gross))
            if provision_role not in records:
                continue
            provision = records[provision_role]
            for kind, weight in (
                ("EXACT_VISIBLE_NET_TOTAL_WITH_SOURCE_SIGNED_PROVISION", 1),
                ("EXACT_VISIBLE_NET_TOTAL_LESS_POSITIVE_PROVISION", -1),
            ):
                net = _equation(
                    equation_kind=kind,
                    components=[*component_records, provision],
                    result=total,
                    multipliers=[*([1] * len(component_records)), weight],
                )
                all_candidate_equations.append(net)
                if net["status"] == "EXACT":
                    net_matches.append((total, net))

        gross_record = _corroborate_identical(
            total_role, [record for record, _equation_receipt in gross_matches]
        )
        if gross_matches and gross_record is None:
            reasons.append(f"{prefix}_MULTIPLE_DISTINCT_VISIBLE_GROSS_TOTALS")
        elif gross_record is not None:
            records[total_role] = gross_record
            gross_equation = _equation(
                equation_kind="EXACT_VISIBLE_GROSS_COMPONENT_TOTAL",
                components=component_records,
                result=gross_record,
            )
            equations.append(gross_equation)
            proven_roles.update({total_role, *(record["role"] for record in component_records)})
            # Some sources flatten the only visible DEBT/EQUITY/OTHER group and
            # print just its children followed by the branch total.  When the
            # complete gross frontier is exactly the complete child frontier
            # of one and only one missing group, that visible total proves the
            # group parent as well.  This is an equation-derived structural
            # projection, not a label or document-specific fallback.
            missing_group_frontiers = []
            component_role_axis = {record["role"] for record in component_records}
            for group_role in (
                f"{prefix}_DEBT",
                f"{prefix}_EQUITY",
                f"{prefix}_OTHER",
            ):
                if group_role in records:
                    continue
                children = _child_records(group_role, records, compiled_specs=compiled_specs)
                if (
                    len(children) >= 2
                    and {record["role"] for record in children} == component_role_axis
                ):
                    missing_group_frontiers.append((group_role, children))
            if len(missing_group_frontiers) == 1:
                group_role, children = missing_group_frontiers[0]
                records[group_role] = _record(
                    group_role,
                    gross_record["cells"],
                    gross_record["source_refs"],
                    "DERIVED_EXACT_SINGLE_GROUP_PARENT_FROM_VISIBLE_BRANCH_TOTAL",
                )
                group_equation = _equation(
                    equation_kind=("DERIVED_EXACT_SINGLE_GROUP_PARENT_FROM_VISIBLE_BRANCH_TOTAL"),
                    components=children,
                    result=records[group_role],
                )
                equations.append(group_equation)
                proven_roles.update({group_role, *(record["role"] for record in children)})
        elif len(component_records) == 1:
            singleton = component_records[0]
            records[total_role] = _record(
                total_role,
                singleton["cells"],
                singleton["source_refs"],
                "DERIVED_EXACT_SINGLETON_COMPONENT_TOTAL",
            )
            singleton_equation = _equation(
                equation_kind="DERIVED_EXACT_SINGLETON_COMPONENT_TOTAL",
                components=[singleton],
                result=records[total_role],
            )
            equations.append(singleton_equation)
            proven_roles.update({total_role, singleton["role"]})

        if net_matches:
            net_records = [record for record, _equation_receipt in net_matches]
            net_record = _corroborate_identical(total_role, net_records)
            if net_record is None:
                reasons.append(f"{prefix}_MULTIPLE_DISTINCT_VISIBLE_NET_TOTALS")
            else:
                matching = next(
                    equation_receipt
                    for record, equation_receipt in net_matches
                    if _coefficients(record) == _coefficients(net_record)
                )
                equations.append(matching)
                proven_roles.update(record["role"] for record in component_records)
                proven_roles.add(provision_role)
        if total_candidates and not gross_matches and not net_matches:
            reasons.append(f"{prefix}_VISIBLE_TOTAL_DOES_NOT_CLOSE_GROSS_OR_NET_FRONTIER")
            equations.append(all_candidate_equations[0])

    def total_frontiers(prefix: str) -> list[tuple[str, list[dict[str, Any]], list[int]]]:
        components = _top_component_records(prefix, records, compiled_specs=compiled_specs)
        if not components:
            return []
        variants = [(f"{prefix}_GROSS", components, [1] * len(components))]
        provision = records.get(f"{prefix}_PROVISION")
        if provision is not None:
            variants.extend(
                (
                    kind,
                    [*components, provision],
                    [*([1] * len(components)), weight],
                )
                for kind, weight in (
                    (f"{prefix}_NET_WITH_SOURCE_SIGNED_PROVISION", 1),
                    (f"{prefix}_NET_LESS_POSITIVE_PROVISION", -1),
                )
            )
        return variants

    afs_frontiers = total_frontiers("AFS")
    htm_frontiers = total_frontiers("HTM")
    vamc_frontiers = []
    if "VAMC_FACE_VALUE" in records:
        vamc_face = records["VAMC_FACE_VALUE"]
        vamc_frontiers.append(("VAMC_GROSS", [vamc_face], [1]))
        if "VAMC_PROVISION" in records:
            vamc_provision = records["VAMC_PROVISION"]
            vamc_frontiers.extend(
                (
                    kind,
                    [vamc_face, vamc_provision],
                    [1, weight],
                )
                for kind, weight in (
                    ("VAMC_NET_WITH_SOURCE_SIGNED_PROVISION", 1),
                    ("VAMC_NET_LESS_POSITIVE_PROVISION", -1),
                )
            )
    unscoped_frontiers = [*afs_frontiers, *htm_frontiers, *vamc_frontiers]
    provision_frontiers = [
        (
            f"{prefix}_PROVISION_SOURCE_SIGNED",
            [records[f"{prefix}_PROVISION"]],
            [1],
        )
        for prefix in ("AFS", "HTM")
        if f"{prefix}_PROVISION" in records
    ]
    provision_frontiers.extend(
        (
            f"{prefix}_PROVISION_ABSOLUTE_PRESENTATION",
            [records[f"{prefix}_PROVISION"]],
            [-1],
        )
        for prefix in ("AFS", "HTM")
        if f"{prefix}_PROVISION" in records
    )
    unscoped_frontiers.extend(provision_frontiers)
    if "AFS_PROVISION" in records and "HTM_PROVISION" in records:
        unscoped_frontiers.append(
            (
                "COMBINED_AFS_HTM_PROVISIONS_SOURCE_SIGNED",
                [records["AFS_PROVISION"], records["HTM_PROVISION"]],
                [1, 1],
            )
        )
        if "VAMC_PROVISION" in records:
            unscoped_frontiers.extend(
                (
                    kind,
                    [
                        records["AFS_PROVISION"],
                        records["HTM_PROVISION"],
                        records["VAMC_PROVISION"],
                    ],
                    [weight, weight, weight],
                )
                for kind, weight in (
                    ("COMBINED_AFS_HTM_VAMC_PROVISIONS_SOURCE_SIGNED", 1),
                    ("COMBINED_AFS_HTM_VAMC_PROVISIONS_ABSOLUTE_PRESENTATION", -1),
                )
            )
        unscoped_frontiers.append(
            (
                "COMBINED_AFS_HTM_PROVISIONS_ABSOLUTE_PRESENTATION",
                [records["AFS_PROVISION"], records["HTM_PROVISION"]],
                [-1, -1],
            )
        )
    unscoped_frontiers.extend(
        (
            f"COMBINED_{afs_kind}_{htm_kind}",
            [*afs_components, *htm_components],
            [*afs_weights, *htm_weights],
        )
        for afs_kind, afs_components, afs_weights in afs_frontiers
        for htm_kind, htm_components, htm_weights in htm_frontiers
    )
    unscoped_frontiers.extend(
        (
            f"COMBINED_{afs_kind}_{htm_kind}_{vamc_kind}",
            [*afs_components, *htm_components, *vamc_components],
            [*afs_weights, *htm_weights, *vamc_weights],
        )
        for afs_kind, afs_components, afs_weights in afs_frontiers
        for htm_kind, htm_components, htm_weights in htm_frontiers
        for vamc_kind, vamc_components, vamc_weights in vamc_frontiers
    )
    for control in raw_control_records["UNSCOPED_TOTAL_CONTROL"]:
        variants = [
            _equation(
                equation_kind="EXACT_UNSCOPED_SOURCE_TOTAL_" + kind,
                components=components,
                result=control,
                multipliers=weights,
            )
            for kind, components, weights in unscoped_frontiers
        ]
        exact_variants = [item for item in variants if item["status"] == "EXACT"]
        if exact_variants:
            selected = exact_variants[0]
            equations.append(selected)
            proven_roles.update(selected["component_roles"])
        else:
            reasons.append("UNSCOPED_VISIBLE_TOTAL_DOES_NOT_CLOSE_ANY_FAMILY_FRONTIER")
            if variants:
                equations.append(variants[0])
    optional_omissions = []
    for role, record in list(records.items()):
        blank_lanes = [
            lane
            for lane, cell in enumerate(record["cells"], start=1)
            if cell["state"].endswith("ZERO_IF_EQUATION_EXACT")
        ]
        if not blank_lanes:
            continue
        if role in proven_roles:
            for cell in record["cells"]:
                if cell["state"].endswith("ZERO_IF_EQUATION_EXACT"):
                    cell["state"] = "INFERRED_" + cell["state"]
            continue
        if role.startswith(_OPTIONAL_DIRECT_VIEW_PREFIXES):
            optional_omissions.append({"blank_lanes": blank_lanes, "role": role})
            del records[role]
        else:
            reasons.append(f"UNPROVEN_BLANK_ZERO_IN_MAPPING_ROLE:{role}")
    reasons = sorted(set(reasons))
    exact = not reasons and all(equation["status"] == "EXACT" for equation in equations)
    mappings = []
    if exact:
        for role in compiled_specs["output_role_order"]:
            record = records.get(role)
            if record is None:
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
                "unit": "MILLION_VND",
                "values": canonical_clone_v1(record["cells"]),
            }
            mappings.append(
                {
                    **material,
                    "item_mapping_id": "gjfismv1:item:" + canonical_json_sha256_v1(material),
                }
            )
    first = region_axis[0]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": {
            "document_unit_context": document_unit_context,
            "equations": equations,
            "optional_direct_view_omissions": optional_omissions,
            "query_receipt": canonical_clone_v1(expected_receipt),
            "rule": "EXACT_MULTI_COMPONENT_HIERARCHY_AND_TOTAL_ALL_LANES",
            "structural_root_receipt": {
                "emitted_mapping": False,
                "mapping_policy": "STRUCTURAL_CONTEXT_ONLY",
                "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
                "role": compiled_specs["topology"]["parent"]["role"],
            },
            "table_receipts": table_receipts,
        },
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
        "candidate_id": "gjfiscv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_investment_securities_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    rebuilt = evaluate_gemini_json_investment_securities_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, rebuilt):
        raise _error("investment-securities candidate does not replay exactly")
    return rebuilt


def build_gemini_json_indexed_investment_securities_query_evidence_v1(
    *,
    selected_document_axis: Sequence[dict[str, Any]],
    selected_page_axis: Sequence[dict[str, Any]],
    document_clusters: Sequence[dict[str, Any]],
    query_policy_sha256: str,
) -> dict[str, Any]:
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
        "query_evidence_id": "gjfiseqv1:evidence:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_indexed_investment_securities_query_evidence_v1(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
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
        raise _error("indexed investment-securities query evidence is invalid")
    documents = value["selected_document_axis"]
    pages = value["selected_page_axis"]
    dispositions = value["candidate_dispositions"]
    document_fields = {"document_id", "document_ordinal", "source_logical_name", "source_sha256"}
    if not documents or len(documents) != len(dispositions):
        raise _error("indexed investment-securities document axis is incomplete")
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
            raise _error("indexed investment-securities selected document axis is invalid")
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
            raise _error("indexed investment-securities selected page axis is invalid")
        prior_document = page["document_ordinal"]
        per_document[page["document_ordinal"]] += 1
        if page.get("selected_page_ordinal") != per_document[page["document_ordinal"]]:
            raise _error("indexed investment-securities selected page order is incomplete")
        page_versions.append(page["page_json_version_id"])
    if len(page_versions) != len(set(page_versions)) or set(per_document) != set(by_ordinal):
        raise _error("indexed investment-securities page frontier is duplicate or incomplete")
    accepted = []
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
            != "gjfisfcv1:cluster:"
            + canonical_json_sha256_v1(
                {key: item for key, item in cluster.items() if key != "cluster_id"}
            )
        ):
            raise _error("indexed investment-securities cluster binding drifted")
        regions = cluster.get("component_regions")
        reasons = cluster.get("reasons")
        if (
            type(reasons) is not list
            or reasons != sorted(set(reasons))
            or (cluster["status"] == READY and (not regions or reasons))
            or (cluster["status"] == NOT_OBSERVED and regions)
            or (cluster["status"] == UNRESOLVED and (not reasons or regions))
        ):
            raise _error("indexed investment-securities disposition semantics drifted")
        if cluster["status"] == READY:
            _region_axis(regions)
            accepted.append(cluster)
    if not same_typed_json_v1(value["accepted_clusters"], accepted):
        raise _error("indexed investment-securities accepted projection drifted")
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
        raise _error("indexed investment-securities query receipt drifted")
    material = {key: canonical_clone_v1(value[key]) for key in fields - {"query_evidence_id"}}
    if value["query_evidence_id"] != "gjfiseqv1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("indexed investment-securities query evidence identity drifted")
    return canonical_clone_v1(value)


def validate_gemini_json_investment_securities_sweep_query_bindings_v1(
    *, trials: Any, indexed_query_evidence: Any, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    evidence = validate_gemini_json_indexed_investment_securities_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    documents = evidence["selected_document_axis"]
    if type(trials) is not list or len(trials) != len(documents):
        raise _error("investment-securities sweep trial axis is incomplete")
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
            raise _error("investment-securities sweep trial identity drifted")
        if disposition["disposition"] == READY:
            if len(trial["candidates"]) != 1:
                raise _error("investment-securities accepted document needs exactly one candidate")
            candidate = trial["candidates"][0]
            if not same_typed_json_v1(
                candidate.get("component_regions"), accepted[ordinal]["component_regions"]
            ):
                raise _error("investment-securities candidate region binding drifted")
            if candidate.get("status") == READY:
                if (
                    trial.get("status") != READY
                    or trial.get("selected_candidate_id") != candidate.get("candidate_id")
                    or not same_typed_json_v1(trial.get("mappings"), candidate.get("mappings"))
                    or trial.get("reasons")
                ):
                    raise _error("investment-securities READY trial binding drifted")
            elif (
                trial.get("status") != UNRESOLVED
                or trial.get("selected_candidate_id") is not None
                or trial.get("mappings")
                or trial.get("reasons") != candidate.get("reasons")
            ):
                raise _error("investment-securities unresolved candidate binding drifted")
        elif disposition["disposition"] == NOT_OBSERVED:
            if (
                trial.get("status") != NOT_OBSERVED
                or trial["candidates"]
                or trial.get("mappings")
                or trial.get("reasons")
                or trial.get("selected_candidate_id") is not None
            ):
                raise _error("investment-securities not-observed trial binding drifted")
        elif (
            trial.get("status") != UNRESOLVED
            or trial["candidates"]
            or trial.get("mappings")
            or trial.get("selected_candidate_id") is not None
            or trial.get("reasons") != disposition["cluster"]["reasons"]
        ):
            raise _error("investment-securities unresolved query disposition binding drifted")
    return canonical_clone_v1(trials)
